#!/usr/bin/env node
/* The sync engine of the connected page (parts/connect.js) against the REAL reference server, with several people at once.
   Run by reqin/tests/test_connect_engine.py, which starts the server and hands over its port and the demo tokens:
     node conn_test.js <page.html> <port> <tokens.json>
   Prints one PASS or FAIL line per check; exit status 1 if any failed. */
const fs = require('fs');
const [pageFile, port, tokenFile] = process.argv.slice(2);
const tokens = JSON.parse(fs.readFileSync(tokenFile, 'utf8'));
const html = fs.readFileSync(pageFile, 'utf8');
const code = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/)[1];
class DCLogic { constructor() { this.state = {}; this.props = {}; } setState() { } }
const E = new Function('DCLogic', code + '\nreturn { connNew, connLoad, connFlush, connPoll, connApi, connApply, connDocsOf, connDiff, connCheck, connCheckRecord, connBuild, connTake, connSkeleton, connPlace, connCanon, connSame, connUnwire, connWire, connWho, CONN_KINDS, DEFAULTS, SEED, PEOPLE, CLUSTERS, REQS, goldPlan, aiFromEvents, aiSheetFp, persistCheck, persistFile, PERSIST_KEYS, SLOT_KEYS };')(DCLogic);
const ORIGIN = 'http://127.0.0.1:' + port;
let failed = 0;
const check = (ok, msg, extra) => { console.log((ok ? 'PASS ' : 'FAIL ') + msg + (ok || extra === undefined ? '' : ' -> ' + (typeof extra === 'string' ? extra : JSON.stringify(extra)))); if (!ok) failed++; };
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* one person's page: its state, the hooks the component would give, and what it was told */
function actor(key, opts) {
  opts = opts || {};
  const a = { key, S: Object.assign({}, E.DEFAULTS, { person: 'x' }), notices: [], statuses: [], activity: [], swapped: null, liveBy: {}, calls: [] };
  const realFetch = (u, o) => { a.calls.push(o.method + ' ' + u.replace(ORIGIN, '')); return fetch(u, o); };
  a.fetch = opts.fetch || realFetch;
  a.api = E.connApi((u, o) => a.fetch(u, o), ORIGIN, tokens[key]);
  a.hooks = {
    getS: () => a.S,
    swapPeople: () => { a.swapped = true; },
    replace: (patch, me) => { Object.assign(a.S, patch, { person: me.key }); },
    apply: (changes) => { Object.assign(a.S, E.connApply(a.S, changes)); },
    notice: (n) => a.notices.push(n),
    status: (s, pending) => a.statuses.push([s, pending]),
    activity: (evs) => { a.activity = a.activity.concat(evs); }
  };
  return a;
}
async function signIn(key, opts) {
  const a = actor(key, opts);
  const me = await a.api.me();
  a.me = me.body;
  a.ctx = E.connNew(a.api, me.body.project, me.body, a.hooks);
  a.ctx.people = (await a.api.people(me.body.project)).body.people;
  a.load = await E.connLoad(a.ctx);
  return a;
}
const docsOf = (a) => E.connDocsOf(a.S);
const freeCluster = (n) => E.CLUSTERS.filter((c) => !E.SEED.dec[c.id])[n];
const decFor = (cl, by, text, outcome) => Object.assign({}, JSON.parse(JSON.stringify(Object.values(E.SEED.dec)[0])), { by: by.name, lens: by.lens, text: text || 'The system shall respond within 250 ms.', outcome: outcome || 'merge', rev: 'R1', at: '12 Oct' });
const sign = (a, cid, slot, rev) => { const cur = Object.assign({}, a.S.sign[cid]); cur[slot] = { by: a.me.name, at: '12 Oct', rev: rev || 'R1' }; a.S.sign = Object.assign({}, a.S.sign, { [cid]: cur }); };
const person = (k) => E.PEOPLE.find((p) => p.k === k);

(async () => {
  // ---- 1. signing in reads the whole project and every document passes the page's own checks
  const sam = await signIn('sam');
  check(sam.load.ok && sam.load.bad.length === 0, 'sam signs in and every document the server holds passes the page\'s checks', sam.load);
  check(sam.me.key === 'sam' && sam.swapped === true && sam.S.person === 'sam', 'the token decides who it is, and the project\'s people are put in place');
  const seedDecided = Object.keys(E.SEED.dec).length;
  check(Object.values(sam.S.dec).filter((d) => d).length === seedDecided, 'the sample\'s decisions came from the server (' + seedDecided + ')');
  check(Object.keys(docsOf(sam)).length === Object.keys(sam.ctx.base).length && E.connDiff(sam.ctx.base, docsOf(sam)).length === 0, 'right after signing in nothing is waiting to be sent');
  check(Object.keys(sam.S.stale).every((k) => sam.S.stale[k] === null || E.SEED.stale[k]) && Object.keys(E.SEED.claims).every((k) => sam.S.claims[k] !== undefined), 'the sample\'s own baseline is overridden everywhere (no map is left to fall back to it)');
  const priya = await signIn('priya');
  check(priya.load.ok && connSameDocs(docsOf(sam), docsOf(priya)), 'a second person sees exactly the same documents');
  function connSameDocs(x, y) { return E.connCanon(x) === E.connCanon(y); }

  // ---- 2. a decision goes to the server and the other person gets it
  const c1 = freeCluster(0).id, c2 = freeCluster(1).id, c3 = freeCluster(2).id;
  sam.S.dec = Object.assign({}, sam.S.dec, { [c1]: decFor(c1, person('sam')) });
  await E.connFlush(sam.ctx);
  const got = await sam.api.get('demo', 'dec/' + c1);
  check(got.status === 200 && got.body.rev === 1 && got.body.by === 'sam' && got.body.body.text.indexOf('250 ms') > 0, 'sam\'s decision is on the server at revision 1, under sam');
  check(sam.statuses.length && sam.statuses[sam.statuses.length - 1][0] === 'live' && E.connDiff(sam.ctx.base, docsOf(sam)).length === 0, 'and nothing is left waiting');
  await E.connPoll(priya.ctx);
  check(priya.S.dec[c1] && priya.S.dec[c1].text.indexOf('250 ms') > 0, 'priya\'s page shows sam\'s decision after her next look');
  check(priya.activity.some((e) => e.target === 'dec/' + c1), 'and the record says who did it');

  // ---- 3. a sign-off binds to the revision of the decision it signs
  sign(priya, c1, 'PE');
  await E.connFlush(priya.ctx);
  const sg = await priya.api.get('demo', 'sign/' + c1 + '/PE');
  check(sg.status === 200 && sg.body.body.rev === 1 && sg.body.body.page_rev === 'R1' && sg.body.by === 'priya', 'priya\'s sign-off is stored against decision revision 1 and keeps the page\'s own label', sg.body);
  await E.connPoll(sam.ctx);
  check(sam.S.sign[c1] && sam.S.sign[c1].PE && sam.S.sign[c1].PE.rev === 'R1' && sam.S.sign[c1].PE.by === 'Priya Raman', 'sam sees it, in the page\'s own form');

  // ---- 4. two people change the same thing: the second is refused and sees what the first did
  sam.S.dec = Object.assign({}, sam.S.dec, { [c2]: decFor(c2, person('sam'), 'The system shall respond within 100 ms.') });
  priya.S.dec = Object.assign({}, priya.S.dec, { [c2]: decFor(c2, person('priya'), 'The system shall respond within 500 ms.') });
  await E.connFlush(sam.ctx);
  await E.connFlush(priya.ctx);
  const conf = priya.notices.filter((n) => n.kind === 'conflict');
  check(conf.length === 1 && conf[0].text.indexOf('Sam Okafor changed the decision on ' + c2) === 0 && /Your change was not made/.test(conf[0].text), 'priya is told that sam got there first and that hers was not made', priya.notices);
  check(priya.S.dec[c2].text.indexOf('100 ms') > 0, 'and her page now shows sam\'s decision, not her own');
  check((await sam.api.get('demo', 'dec/' + c2)).body.body.text.indexOf('100 ms') > 0, 'the server still holds sam\'s: it was not written over');
  check(E.connDiff(priya.ctx.base, docsOf(priya)).length === 0, 'and she has nothing left waiting that would send hers again');

  // ---- 5. a new revision of a decision clears the sign-offs on the old one, here and there
  const jo = await signIn('jordan');          // jordan opens the project now and has not looked since
  sam.S.dec = Object.assign({}, sam.S.dec, { [c1]: Object.assign({}, sam.S.dec[c1], { text: 'The system shall respond within 200 ms.', rev: 'R2' }) });
  sam.S.sign = Object.assign({}, sam.S.sign, { [c1]: {} });      // as the page does when a decision is changed
  await E.connFlush(sam.ctx);
  const sg2 = await sam.api.get('demo', 'sign/' + c1 + '/PE');
  check(sg2.status === 200 && sg2.body.body === null && sg2.body.rev === 2, 'the server took the old sign-off back when the decision changed', sg2.body);
  check(E.connDiff(sam.ctx.base, docsOf(sam)).length === 0, 'sam has nothing waiting: the sign-off going away was already part of it');
  await E.connPoll(priya.ctx);
  check(!(priya.S.sign[c1] && priya.S.sign[c1].PE) && E.connDiff(priya.ctx.base, docsOf(priya)).length === 0, 'priya\'s page lets go of her sign-off too, and does not send it again');
  sign(jo, c1, 'UX');                          // jordan signs the decision as he last saw it: the old wording
  await E.connFlush(jo.ctx);
  const stale = jo.notices.filter((n) => n.kind === 'conflict' && n.id === 'sign/' + c1 + '/UX');
  check(stale.length === 1 && /moved on before your sign-off arrived/.test(stale[0].text), 'a sign-off on the old wording is refused with the reason', jo.notices);
  check(!(jo.S.sign[c1] && jo.S.sign[c1].UX) && jo.S.dec[c1].text.indexOf('200 ms') > 0, 'his page shows the new wording and no sign-off of his');
  sign(jo, c1, 'UX', 'R2');
  await E.connFlush(jo.ctx);
  const sg3 = await sam.api.get('demo', 'sign/' + c1 + '/UX');
  check(sg3.status === 200 && sg3.body.body.rev === 2 && sg3.body.body.page_rev === 'R2', 'and signing again, on what he can now see, works: it names revision 2', sg3.body);

  // ---- 5b. a sign-off the page still shows when the server takes it back is taken back here too, and said: it is not sent again and refused
  const c9 = freeCluster(8).id;
  sam.S.dec = Object.assign({}, sam.S.dec, { [c9]: decFor(c9, person('sam'), 'The system shall log within 5 s.') });
  await E.connFlush(sam.ctx);
  await E.connPoll(priya.ctx);
  sign(priya, c9, 'PE'); await E.connFlush(priya.ctx);
  await E.connPoll(sam.ctx);
  check(sam.S.sign[c9] && sam.S.sign[c9].PE, 'sam sees priya\'s sign-off on the new decision');
  sam.S.dec = Object.assign({}, sam.S.dec, { [c9]: Object.assign({}, sam.S.dec[c9], { text: 'The system shall log within 6 s.', rev: 'R2' }) });     // changed, and the sign-off still on his screen
  await E.connFlush(sam.ctx);
  check(!(sam.S.sign[c9] && sam.S.sign[c9].PE) && sam.notices.some((n) => n.kind === 'cleared' && n.id === 'sign/' + c9 + '/PE') && !sam.notices.some((n) => n.id === 'sign/' + c9 + '/PE' && n.kind !== 'cleared') && E.connDiff(sam.ctx.base, docsOf(sam)).length === 0,
    'the sign-off the server cleared is gone from his page and he is told, and it is not sent again', sam.notices.map((n) => n.kind + ' ' + n.id));
  // what the engine decides, without a network
  const before = sam.S.dec[c1].text;
  E.connTake(sam.ctx, [{ id: 'dec/' + c1, rev: sam.ctx.revs['dec/' + c1], body: decFor(c1, person('priya'), 'An older version that must not come back.') }]);
  check(sam.S.dec[c1].text === before, 'news of a revision the page already has (or an older one) is not taken as new');
  const rq = E.REQS[0].id;
  const ord = E.connDiff({}, { ['sign/' + c1 + '/PE']: { by: 'x', rev: 'R1' }, ['hand/' + c1]: { from: 'sam' }, ['rdec/' + rq]: { outcome: 'keep' }, ['dec/' + c1]: decFor(c1, person('sam')) }).map((c) => c.id.split('/')[0]);
  check(ord.join() === 'dec,rdec,hand,sign', 'when several things are waiting the decisions go first, then the rest, and the sign-offs on a decision go last (not just in alphabetical order)', ord);
  const blank = E.connBuild(Object.assign({}, E.DEFAULTS, { dec: E.SEED.dec, sign: E.SEED.sign, claims: E.SEED.claims, objections: E.SEED.dispute, stale: E.SEED.stale }), {});
  const kinds = E.CONN_KINDS.filter((k) => k.empty !== undefined), left = [];
  kinds.forEach((k) => Object.keys(k.seed()).forEach((id) => { if (E.connCanon(blank.patch[k.key][id]) !== E.connCanon(k.empty)) left.push(k.key + '/' + id); }));
  check(kinds.length >= 5 && Object.keys(E.SEED.dec).length > 0 && !left.length, 'a project that holds nothing shows nothing: every decision, sign-off, claim and flag the sample starts with is cleared, not left to show through', left.slice(0, 3));
  const ai = E.connBuild(E.DEFAULTS, { 'proj/ai': { on: 'yes', sheet: 7 } });
  check(ai.patch.aiOn === false && ai.bad.some((b) => b.id === 'proj/ai'), 'an AI setting the page cannot read is reported and AI stays off, it is not guessed at', ai.bad);
  const none = E.connBuild(E.DEFAULTS, {});
  check(none.patch.aiOn === false && none.patch.aiSheet.model === '' && none.patch.aiSheet.reviewed_by === '' && none.patch.aiSheet.reviewed_at === '', 'a shared project whose server holds no AI document is closed: the switch is off and the sheet is empty and unreviewed, not the stand-alone sample\'s made-up one');
  check(!('proj/ai' in E.connDocsOf(E.connSkeleton(E.DEFAULTS))) && 'proj/ai' in E.connDocsOf(E.DEFAULTS), 'a closed project writes no AI document of its own; the sample\'s (switch on, reviewed sheet) is a document a lead has to write');

  // ---- 6. the server's rules refuse what the page should not have done, and the change is taken back
  sign(sam, c1, 'SE');            // sam made this decision: nobody signs their own
  await E.connFlush(sam.ctx);
  const selfN = sam.notices.filter((n) => n.kind === 'refused' && n.id === 'sign/' + c1 + '/SE');
  check(selfN.length === 1 && /made this decision/.test(selfN[0].text) && !(sam.S.sign[c1] && sam.S.sign[c1].SE), 'a sign-off by the person who decided is refused, with the server\'s words, and taken back', sam.notices);
  sam.S.aiOn = false;
  await E.connFlush(sam.ctx);
  check(sam.notices.some((n) => n.kind === 'refused' && n.id === 'proj/ai' && /lead/i.test(n.text)) && sam.S.aiOn === true, 'a reviewer cannot switch AI off for the project: refused, and the switch is back on');
  const morgan = await signIn('morgan');
  morgan.S.aiOn = false;
  await E.connFlush(morgan.ctx);
  check(morgan.notices.length === 0 && (await morgan.api.get('demo', 'proj/ai')).body.body.on === false, 'a lead can');
  await E.connPoll(sam.ctx);
  check(sam.S.aiOn === false, 'and sam\'s page follows');
  const aiNow = (await morgan.api.get('demo', 'proj/ai')).body;
  morgan.S.aiOn = true;
  await E.connFlush(morgan.ctx);
  await E.connPoll(sam.ctx);
  check(sam.S.aiOn === true && sam.S.aiSheet.reviewed_by !== '', 'the lead switches it on again and sam\'s page follows, with the lead\'s sheet');
  const wd = await morgan.api.put('demo', 'proj/ai', null, (await morgan.api.get('demo', 'proj/ai')).body.rev, 'k-withdraw-ai');
  await E.connPoll(sam.ctx);
  check(wd.status < 300 && sam.S.aiOn === false && sam.S.aiSheet.reviewed_by === '' && sam.S.aiSheet.model === '', 'the lead withdraws the AI document and sam\'s page goes back to closed with an empty sheet (what the gateway reads: no sheet)', [wd.status, sam.S.aiOn, sam.S.aiSheet]);
  check(aiNow.rev >= 2, 'the AI document has been through revisions on the server', aiNow.rev);
  const lee = await signIn('lee');
  lee.S.dec = Object.assign({}, lee.S.dec, { [c3]: decFor(c3, person('lee')) });
  await E.connFlush(lee.ctx);
  check(lee.notices.some((n) => n.kind === 'refused' && /read but not change/.test(n.text)) && !lee.S.dec[c3], 'an observer\'s change is refused and taken back');
  const labKey = Object.keys(E.goldPlan().by)[0], labPath = 'label/' + labKey.split('|').join('/') + '/sam';
  sam.S.gold = Object.assign({}, sam.S.gold, { labels: { [labKey]: { sam: { v: 'equiv', note: '' }, priya: { v: 'equiv', note: '' } } } });
  await E.connFlush(sam.ctx);
  const own = await sam.api.get('demo', labPath);
  check(own.status === 200 && sam.notices.some((n) => n.kind === 'refused' && /own/.test(n.text)) && !(sam.S.gold.labels[labKey] || {}).priya, 'a label is its labeller\'s own: sam\'s is kept, the one he wrote as priya is refused', sam.notices.map((n) => n.text));

  // ---- 7. objections: anyone can raise one, only a lead closes it
  const c4 = freeCluster(3).id;
  sam.S.dec = Object.assign({}, sam.S.dec, { [c4]: decFor(c4, person('sam')) });
  await E.connFlush(sam.ctx);
  await E.connPoll(priya.ctx);
  priya.S.objections = Object.assign({}, priya.S.objections, { [c4]: { by: 'Priya Raman', lens: 'PE', at: '12 Oct', note: 'The value is looser than the one in the thread.' } });
  await E.connFlush(priya.ctx);
  check((await priya.api.get('demo', 'obj/' + c4)).status === 200, 'priya raised an objection');
  priya.S.objections = Object.assign({}, priya.S.objections, { [c4]: null });
  await E.connFlush(priya.ctx);
  check(priya.notices.some((n) => n.kind === 'refused' && n.id === 'obj/' + c4 && /lead/.test(n.text)) && priya.S.objections[c4], 'she cannot close it herself: refused, and it is back');
  await E.connPoll(morgan.ctx);
  morgan.S.objections = Object.assign({}, morgan.S.objections, { [c4]: null });
  await E.connFlush(morgan.ctx);
  check((await morgan.api.get('demo', 'obj/' + c4)).body.body === null, 'the lead closes it');

  // ---- 8. a change made while the server is out of reach waits, and is sent once when it is back, even if the answer was lost
  let mode = 'up', reached = 0;
  const puts = [];     // every PUT that reached the wire: the key it carried, the mode, and whether the server said it was a repeat
  const flaky = (u, o) => {
    if (mode === 'down') return Promise.reject(new Error('network down'));
    const key = o.method === 'PUT' ? o.headers['Idempotency-Key'] : null;
    if (mode === 'lost') { reached++; if (key) puts.push({ key, mode }); return fetch(u, o).then(() => { throw new Error('answer lost'); }); }
    return fetch(u, o).then(async (r) => { if (key) puts.push({ key, mode, replay: (await r.clone().json()).replay === true }); return r; });
  };
  const jordan = await signIn('jordan', { fetch: flaky });
  const c5 = freeCluster(4).id;
  mode = 'down';
  jordan.S.dec = Object.assign({}, jordan.S.dec, { [c5]: decFor(c5, person('jordan')) });
  await E.connFlush(jordan.ctx);
  check(jordan.statuses.slice(-1)[0][0] === 'offline' && jordan.statuses.slice(-1)[0][1] === 1 && E.connDiff(jordan.ctx.base, docsOf(jordan)).length === 1, 'with the network down the change stays waiting and the page says so');
  mode = 'lost';
  await E.connFlush(jordan.ctx);
  check(reached === 1 && jordan.statuses.slice(-1)[0][0] === 'offline', 'the server got the request but the answer was lost: still waiting');
  mode = 'up';
  await E.connFlush(jordan.ctx);
  const dj = await jordan.api.get('demo', 'dec/' + c5);
  check(dj.status === 200 && dj.body.rev === 1 && jordan.notices.length === 0 && jordan.statuses.slice(-1)[0][0] === 'live', 'sent again with the same key it is one revision, not two, and nothing is reported as a conflict', dj.body);
  const pl = puts.find((p) => p.mode === 'lost'), pu = puts.find((p) => p.mode === 'up');
  check(pl && pu && pl.key === pu.key && pu.replay === true, 'the second try carries the first try\'s key, and the server answers it as a repeat, not as a new request', puts);

  // ---- 9. someone else is changing the same thing: the other's change is not read over the top of a waiting one
  const c6 = freeCluster(5).id;
  sam.S.dec = Object.assign({}, sam.S.dec, { [c6]: decFor(c6, person('sam'), 'The system shall respond within 10 ms.') });
  await E.connFlush(sam.ctx);
  await E.connPoll(priya.ctx);
  priya.S.dec = Object.assign({}, priya.S.dec, { [c6]: Object.assign({}, priya.S.dec[c6], { text: 'The system shall respond within 20 ms.', rev: 'R2' }) });   // waiting, not sent yet
  sam.S.dec = Object.assign({}, sam.S.dec, { [c6]: Object.assign({}, sam.S.dec[c6], { text: 'The system shall respond within 30 ms.', rev: 'R2' }) });
  await E.connFlush(sam.ctx);
  await E.connPoll(priya.ctx);
  check(priya.S.dec[c6].text.indexOf('20 ms') > 0, 'priya\'s own unsent change is not overwritten by what she reads');
  await E.connFlush(priya.ctx);
  check(priya.notices.some((n) => n.kind === 'conflict' && n.id === 'dec/' + c6) && priya.S.dec[c6].text.indexOf('30 ms') > 0, 'when it is sent, the server refuses it and she sees sam\'s');

  // ---- 10. something on the server this page cannot read is left out and said so, not shown
  const raw = actor('morgan');
  await raw.api.put('demo', 'dec/' + freeCluster(6).id, { outcome: 'bogus', by: 7 }, 0, 'k-bad-1');
  await raw.api.put('demo', 'dec/CL-9999', { outcome: 'merge' }, 0, 'k-bad-2');     // a cluster this project does not have
  await E.connPoll(priya.ctx);
  check(priya.notices.filter((n) => n.kind === 'ignored').length === 2 && !priya.S.dec[freeCluster(6).id] && !priya.S.dec['CL-9999'], 'two documents that do not fit this project are left out and reported', priya.notices.map((n) => n.text));
  check(E.connDiff(priya.ctx.base, docsOf(priya)).length === 0, 'and the page does not try to take them back');
  const late = await signIn('casey');
  check(late.load.ok && late.load.bad.length === 2, 'a person signing in later gets the project without them, and is told', late.load.bad);

  // ---- 11. a burst of changes is read again as a whole
  const unclaimed = E.CLUSTERS.filter((c) => !E.SEED.claims[c.id]).slice(10, 55);
  for (let i = 0; i < 45; i++) { const id = unclaimed[i].id; await raw.api.put('demo', 'claim/' + id, { by: 'Morgan Hale', lens: 'SE', mins: i }, 0, 'k-claim-' + i); }
  const callsBefore = sam.calls.length;
  await E.connPoll(sam.ctx);
  check(Object.keys(sam.S.claims).filter((k) => sam.S.claims[k] && sam.S.claims[k].by === 'Morgan Hale').length >= 45, 'forty-five documents changed at once and sam has all of them');
  check(sam.calls.slice(callsBefore).filter((c) => c.indexOf('GET /v1/projects/demo/docs/') === 0).length === 0, 'by reading the list again, not one request each');

  // ---- 12. the record
  const chk = await E.connCheckRecord(sam.ctx);
  check(chk.ok && chk.entries > 250 && /intact|follows from the one before/.test(chk.text) && /\b[0-9a-f]{12}\b/.test(chk.text), 'the record checks out and says how many entries', chk);
  const liar = actor('sam', { fetch: (u, o) => /\/verify/.test(u) ? Promise.resolve({ status: 200, json: async () => ({ ok: false, entries: 9, at: 4, why: 'its contents no longer match its fingerprint', head: 'ab' }) }) : fetch(u, o) });
  liar.ctx = sam.ctx; liar.ctx.api = liar.api;
  const bad = await E.connCheckRecord(liar.ctx);
  liar.ctx.api = sam.api;
  check(!bad.ok && /entry 4/.test(bad.text) && /Do not rely/.test(bad.text), 'a record that does not check out is said not to be relied on, at the entry that broke');

  // ---- 13. the record going backwards is noticed
  const back = actor('sam', { fetch: async (u, o) => { const r = await fetch(u, o); if (/\/events/.test(u)) { const j = await r.json(); j.head = { seq: Math.max(0, j.head.seq - 3), hash: j.head.hash }; j.events = []; return { status: 200, json: async () => j }; } return r; } });
  back.ctx = sam.ctx; const savedApi = sam.ctx.api; back.ctx.api = back.api; back.ctx.hooks = back.hooks;
  const rb = await E.connPoll(back.ctx);
  check(rb === 'rolledback' && back.statuses.slice(-1)[0][0] === 'rolledback', 'a record that is shorter than the one seen a moment ago stops everything');
  const same = actor('sam', { fetch: async (u, o) => { const r = await fetch(u, o); if (/\/events/.test(u)) { const j = await r.json(); j.head = { seq: j.head.seq, hash: 'f'.repeat(64) }; return { status: 200, json: async () => j }; } return r; } });
  back.ctx.api = same.api; back.ctx.hooks = same.hooks; sam.ctx.head = Object.assign({}, sam.ctx.head, { hash: sam.ctx.head.hash || 'a'.repeat(64) });
  const rw = await E.connPoll(back.ctx);
  check(rw === 'rolledback' && same.statuses.slice(-1)[0][0] === 'rolledback', 'a record that ends at the same entry but with a different fingerprint (rewritten) stops everything too');
  sam.ctx.api = savedApi; sam.ctx.hooks = sam.hooks;

  // ---- 14. a token the server no longer knows
  await sam.api.me();
  const old = tokens.priya;
  const dead = actor('priya', { fetch: (u, o) => fetch(u, Object.assign({}, o, { headers: Object.assign({}, o.headers, { Authorization: 'Bearer ' + 'x'.repeat(43) }) })) });
  dead.ctx = priya.ctx; dead.ctx.api = dead.api; dead.ctx.hooks = dead.hooks;
  priya.S.dec = Object.assign({}, priya.S.dec, { [freeCluster(7).id]: decFor(null, person('priya')) });
  dead.S = priya.S;
  await E.connFlush(dead.ctx);
  check(dead.statuses.slice(-1)[0][0] === 'denied', 'a token the server has stopped accepting ends it: nothing more is sent');

  console.log(failed ? '\n' + failed + ' failed' : '\nall passed');
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.log('FAIL the test itself broke: ' + (e && e.stack || e)); process.exit(1); });
