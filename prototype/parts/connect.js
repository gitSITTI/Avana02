/* ---------- the shared project: what the page sends to the reference server and what it takes back ----------
   Without a server the page works on its own copy, kept in this browser (persist.js). Signed in to the reference server (reqin/src/reqin/server) the
   decisions, sign-offs, hand-offs, objections, claims, labels and the AI switch and data sheet are ONE copy on the server, and this page is a window on it.

   How it works, in the order it happens:
     sign in   the person pastes their token (kept in this page's memory only: not in storage, not in the address, gone when the tab is closed). The
               server says who it is for, and that decides the person, the lens and the role here. Everything the server holds is read, checked
               by the same checks a saved file gets (persistCheck), and put in place of what the page showed before.
     change    every change is compared with the last thing the server agreed to and sent as a document that names the revision it was made against
               (if_rev). If somebody else got there first, the server refuses with what is there now: this page shows that and the change is not
               made, it is never written over theirs. A change the server's rules refuse (not your lens, not a lead, a sign-off on a decision that
               moved) is taken back and the reason is shown. A change that cannot be sent (no network) stays waiting and is sent again.
     others    every few seconds the page asks for what was recorded since it last looked, reads the documents that changed and puts them in place.
               A document the person is changing at that moment is left alone: their change is sent, the server refuses it, and they see what the
               other person did.
     check     the person can ask the server to recompute its record (a SHA-256 chain) and the page says whether it came out whole.

   What this does not do: it does not decide who may do what (the server does, from the token), it does not keep a copy in the browser while connected, and
   the record the page keeps for itself (the 32-bit chain in the audit log) is still only a local record: the shared one is the server's. A person who can
   run script in this page can read the token, as in any web page; serve the page and its libraries from the server itself.

   Everything here that does not touch the browser or the network is a plain function and is tested under node against the real server
   (tools/test_connect_engine.py) as well as in verify.js. */
const CONN_POLL_MS = 4000;
const CONN_MAX_PER_POLL = 40;       // more documents than this changed at once: read everything again instead of one by one
const CONN_EVENT_LIMIT = 500;       // the server's page size for the record
const CONN_SEG = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$/;
const connSeg = (s) => typeof s === 'string' && CONN_SEG.test(s);

/* what is shared, and under which kind of document. `seed` is what the sample starts with for it, which a shared project must not show (it starts from
   what the server holds). `empty` is what "nothing here" is in the page's own map: null where the page says null, {} for the sign-offs, and missing
   where the page has no baseline. */
const CONN_KINDS = [
  { key: 'dec', kind: 'dec', seed: () => SEED.dec, empty: null, order: 0 },
  { key: 'rdec', kind: 'rdec', seed: () => ({}), empty: undefined, order: 0 },
  { key: 'hand', kind: 'hand', seed: () => ({}), empty: undefined, order: 1 },
  { key: 'objections', kind: 'obj', seed: () => SEED.dispute, empty: null, order: 1 },
  { key: 'adjud', kind: 'adj', seed: () => ({}), empty: undefined, order: 1 },
  { key: 'claims', kind: 'claim', seed: () => SEED.claims, empty: null, order: 1 },
  { key: 'stale', kind: 'stale', seed: () => SEED.stale, empty: null, order: 1 },
  { key: 'sib', kind: 'sib', seed: () => SEED.sibs, empty: null, order: 1, wrap: true },
  { key: 'peeled', kind: 'peel', seed: () => ({}), empty: undefined, order: 1, wrap: true },
  { key: 'sign', kind: 'sign', seed: () => SEED.sign, empty: {}, order: 2, nested: true }
];
const CONN_BY_KIND = {}; CONN_KINDS.forEach((k) => { CONN_BY_KIND[k.kind] = k; });
/* the keys of the page's state that are shared, for putting back what was there before signing in */
/* A shared project whose server holds no AI document is CLOSED: the switch is off and the data sheet is empty and unreviewed. That is what the AI gateway reads from the same
   server (reqin.gateway: "no_sheet"), so the page and the gateway cannot disagree about a project nobody has set up. The stand-alone sample starts with the switch on and a
   made-up reviewed sheet (DEFAULTS); a shared project gets those only when a lead writes them (the demo seed does, by Morgan). */
const CONN_NO_AI = { on: false, sheet: { model: '', where: 'ours', leaves: false, log: 'none', days: 0, approved: 'none', unstated: 'withhold', reviewed_by: '', reviewed_at: '', entered_by: '' } };
const CONN_STATE_KEYS = CONN_KINDS.map((k) => k.key).concat(['gold', 'aiOn', 'aiSheet']);
/* what a person types and tries on the way to a decision, and the page's own record of what was done in it. These are not shared, and they are put back when the person signs out,
   so that nothing typed while signed in to a shared project is left in this browser, and the record here still describes the work here. */
const CONN_DRAFT_KEYS = ['res', 'why', 'ref', 'sendF', 'replyNote', 'chat', 'adjNote', 'sibNote', 'lensNote', 'rform', 'blind', 'blindDone', 'liveVer', 'events', 'person'];

/* the same JSON with the keys in order, so that two bodies are equal when they say the same thing */
function connCanon(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v === undefined ? null : v);
  if (Array.isArray(v)) return '[' + v.map(connCanon).join(',') + ']';
  return '{' + Object.keys(v).sort().filter((k) => v[k] !== undefined).map((k) => JSON.stringify(k) + ':' + connCanon(v[k])).join(',') + '}';
}
const connSame = (a, b) => connCanon(a) === connCanon(b);

/* where a document lives in the page's state, or null for a document this page does not keep */
function connPlace(id) {
  const p = String(id).split('/');
  if (p[0] === 'proj') return p.length === 2 && p[1] === 'ai' ? { top: 'ai', path: [] } : null;
  if (p[0] === 'label') return p.length === 4 && p.slice(1).every(connSeg) ? { top: 'gold', path: ['labels', p[1] + '|' + p[2], p[3]] } : null;
  if (p[0] === 'gadj') return p.length === 3 && p.slice(1).every(connSeg) ? { top: 'gold', path: ['adj', p[1] + '|' + p[2]] } : null;
  const k = CONN_BY_KIND[p[0]];
  if (!k) return null;
  if (k.nested) return p.length === 3 && connSeg(p[1]) && SLOT_KEYS.indexOf(p[2]) >= 0 ? { top: k.key, path: [p[1], p[2]], k } : null;
  return p.length === 2 && connSeg(p[1]) ? { top: k.key, path: [p[1]], k } : null;
}

/* the page's state as documents: { id: body }, only what is there (a decision that was taken back is not a document) */
function connDocsOf(S) {
  const out = {};
  CONN_KINDS.forEach((k) => {
    const m = S[k.key] || {};
    Object.keys(m).forEach((id) => {
      const v = m[id];
      if (v === null || v === undefined || !connSeg(id)) return;
      if (k.nested) { Object.keys(v).forEach((slot) => { if (v[slot] && SLOT_KEYS.indexOf(slot) >= 0) out[k.kind + '/' + id + '/' + slot] = v[slot]; }); }
      else if (k.wrap) { if (Array.isArray(v) && v.length) out[k.kind + '/' + id] = { v }; }
      else if (persistPlain(v)) out[k.kind + '/' + id] = v;
    });
  });
  const g = S.gold || {};
  Object.keys(g.labels || {}).forEach((key) => {
    const pr = key.split('|');
    if (pr.length !== 2 || !pr.every(connSeg)) return;
    Object.keys(g.labels[key] || {}).forEach((w) => { if (connSeg(w) && persistPlain(g.labels[key][w])) out['label/' + pr[0] + '/' + pr[1] + '/' + w] = g.labels[key][w]; });
  });
  Object.keys(g.adj || {}).forEach((key) => {
    const pr = key.split('|');
    if (pr.length === 2 && pr.every(connSeg) && persistPlain(g.adj[key])) out['gadj/' + pr[0] + '/' + pr[1]] = g.adj[key];
  });
  const sh = S.aiSheet || DEFAULTS.aiSheet, on = S.aiOn === undefined ? DEFAULTS.aiOn : S.aiOn;
  if (on !== CONN_NO_AI.on || aiSheetFp(sh) !== aiSheetFp(CONN_NO_AI.sheet)) out['proj/ai'] = { on, sheet: sh };
  return out;
}

/* put changes ([{ id, body }], body null = nothing there) into the page's state. Returns only what changed in the state, every map copied, none written to. */
function connApply(S, changes) {
  const patch = {};
  const mine = (top) => {
    if (patch[top] !== undefined) return patch[top];
    if (top === 'gold') { const g = S.gold || DEFAULTS.gold; return (patch.gold = Object.assign({}, g, { labels: Object.assign({}, g.labels), adj: Object.assign({}, g.adj) })); }
    return (patch[top] = Object.assign({}, S[top]));
  };
  changes.forEach((c) => {
    const pl = connPlace(c.id), body = c.body;
    if (!pl) return;
    if (pl.top === 'ai') { patch.aiOn = body ? body.on : CONN_NO_AI.on; patch.aiSheet = body ? body.sheet : CONN_NO_AI.sheet; return; }
    const m = mine(pl.top);
    if (pl.top === 'gold') {
      if (pl.path[0] === 'labels') {
        const L = Object.assign({}, m.labels[pl.path[1]]);
        if (body) L[pl.path[2]] = body; else delete L[pl.path[2]];
        if (Object.keys(L).length) m.labels[pl.path[1]] = L; else delete m.labels[pl.path[1]];
      } else if (body) m.adj[pl.path[1]] = body; else delete m.adj[pl.path[1]];
      return;
    }
    const k = pl.k;
    if (k.nested) { const sg = Object.assign({}, m[pl.path[0]]); if (body) sg[pl.path[1]] = body; else delete sg[pl.path[1]]; m[pl.path[0]] = sg; }
    else if (body) m[pl.path[0]] = k.wrap ? body.v : body;
    else if (k.empty === undefined) delete m[pl.path[0]];
    else m[pl.path[0]] = k.empty;
  });
  return patch;
}

/* the state a shared project starts from: the sample's own activity cleared out of every shared map, the person's own gold-set settings kept */
function connSkeleton(S) {
  const sk = {};
  CONN_KINDS.forEach((k) => {
    const m = {};
    if (k.empty !== undefined) Object.keys(k.seed()).forEach((id) => { m[id] = k.empty; });
    sk[k.key] = m;
  });
  const g = S.gold || DEFAULTS.gold;
  sk.gold = Object.assign({}, g, { labels: {}, adj: {} });
  sk.aiOn = CONN_NO_AI.on; sk.aiSheet = CONN_NO_AI.sheet;
  return sk;
}

/* does this document, as the server sent it, fit this project? '' if it does, otherwise why not. The same checks a saved file gets. */
function connCheck(id, body) {
  const pl = connPlace(id);
  if (!pl) return 'it is not a kind of document this page keeps';
  if (body === null) return '';
  if (!persistPlain(body)) return 'it is not an object';
  if (pl.top === 'ai') return typeof body.on === 'boolean' && aiSheetOk(body.sheet) ? '' : 'the AI settings are not in the shape this page reads';
  if (pl.k && pl.k.wrap && !Array.isArray(body.v)) return 'it is not a list';
  const patch = connApply(DEFAULTS, [{ id, body }]), state = {};
  Object.keys(patch).forEach((k) => { state[k] = patch[k]; });
  const r = persistCheck({ format: PERSIST_FORMAT, project: persistProject(), state });
  return r.ok && r.dropped === 0 ? '' : (r.problems[0] || 'its contents do not fit this project');
}

/* the whole shared state from every document the server holds: { patch, bad } where bad lists the documents left out and why */
function connBuild(S, docs) {
  let changes = Object.keys(docs).map((id) => ({ id, body: docs[id] })).filter((c) => c.body !== null);
  const bad = [];
  const make = (list) => { const sk = connSkeleton(S); return Object.assign({}, sk, connApply(sk, list)); };
  const whole = (list) => {
    const out = make(list), state = {};
    Object.keys(out).forEach((k) => { if (k !== 'aiOn' && k !== 'aiSheet') state[k] = out[k]; });
    return { out, r: persistCheck({ format: PERSIST_FORMAT, project: persistProject(), state }) };
  };
  const ai = changes.find((c) => c.id === 'proj/ai');
  if (ai && connCheck(ai.id, ai.body)) { bad.push({ id: ai.id, why: connCheck(ai.id, ai.body) }); changes = changes.filter((c) => c !== ai); }   // an AI setting that cannot be read is not guessed at: the AI stays off
  let w = whole(changes);
  if (!w.r.ok || w.r.dropped > 0) {
    changes = changes.filter((c) => { const why = c.id === 'proj/ai' ? '' : connCheck(c.id, c.body); if (why) bad.push({ id: c.id, why }); return !why; });
    w = whole(changes);
  }
  const out = w.out;
  if (ai && bad.some((b) => b.id === 'proj/ai')) { out.aiOn = CONN_NO_AI.on; out.aiSheet = CONN_NO_AI.sheet; }
  return { patch: out, bad };
}

/* the changes between what the server last agreed to (base) and what the page shows (local): [{ id, body }], a decision or a ruling first and the
   sign-offs that depend on it last. body null means the document is to be taken back. */
function connDiff(base, local) {
  const out = [];
  Object.keys(local).forEach((id) => { if (!(id in base) || !connSame(base[id], local[id])) out.push({ id, body: local[id] }); });
  Object.keys(base).forEach((id) => { if (!(id in local)) out.push({ id, body: null }); });
  const ord = (id) => { const p = connPlace(id); return p && p.k ? p.k.order : 1; };
  return out.sort((a, b) => ord(a.id) - ord(b.id) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/* a sign-off carries the server's revision of the decision it binds to, and keeps the page's own revision label beside it */
function connWire(ctx, id, body) {
  if (id.slice(0, 5) !== 'sign/') return body;
  const target = id.split('/')[1], dr = ctx.revs['dec/' + target] || ctx.revs['rdec/' + target] || 0;
  return Object.assign({}, body, { page_rev: typeof body.rev === 'string' ? body.rev : '', rev: dr });
}
function connUnwire(id, body) {
  if (id.slice(0, 5) !== 'sign/' || !body) return body;
  const o = Object.assign({}, body, { rev: typeof body.page_rev === 'string' ? body.page_rev : '' });
  delete o.page_rev;
  return o;
}

/* words for the person */
const CONN_WHAT = { dec: 'the decision on', rdec: 'the decision on', sign: 'the sign-off on', hand: 'the hand-off on', obj: 'the objection on', adj: 'the ruling on', claim: 'the claim on', stale: 'the “source changed” flag on', sib: 'the two versions of', peel: 'the members taken out of', label: 'your label on', gadj: 'the ruling on the pair' };
function connName(id) {
  const p = String(id).split('/');
  if (id === 'proj/ai') return 'the AI switch and data sheet';
  if (p[0] === 'sign') return 'the ' + p[2] + ' sign-off on ' + p[1];
  if (p[0] === 'label' || p[0] === 'gadj') return (CONN_WHAT[p[0]] || 'the') + ' ' + p[1] + ' and ' + p[2];
  return (CONN_WHAT[p[0]] || 'the document') + ' ' + p.slice(1).join(' ');
}
function connSay(id, body) {
  if (!body) return 'nothing';
  const p = String(id).split('/');
  if (p[0] === 'dec' || p[0] === 'rdec') return (body.outcome || 'a decision') + (body.text ? ' “' + String(body.text).slice(0, 80) + '”' : '');
  if (p[0] === 'sign') return 'signed by ' + (body.by || 'someone');
  if (p[0] === 'hand') return 'a hand-off from ' + ((PEOPLE.find((x) => x.k === body.from) || {}).name || 'someone') + ' (' + (body.status || 'open') + ')';
  if (p[0] === 'label') return '“' + (body.v || 'a label') + '”';
  if (p[0] === 'obj') return 'an objection by ' + (body.by || 'someone');
  if (id === 'proj/ai') return 'AI ' + (body.on ? 'on' : 'off') + ', ' + (body.sheet && aiReviewed(body.sheet) ? 'sheet reviewed' : 'sheet not reviewed');
  return 'a change';
}
const connWho = (key) => { const p = PEOPLE.find((x) => x.k === key); return p ? p.name : key || 'someone'; };

/* ---------- the network: one small wrapper, so the rest can be tested without one ---------- */
function connApi(fetchFn, root, token) {
  const enc = (id) => String(id).split('/').map(encodeURIComponent).join('/');
  const proj = (p) => '/v1/projects/' + encodeURIComponent(p);
  const call = async (method, path, body, headers) => {
    let res, timer = null;
    try {
      const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null;
      if (ctl) timer = setTimeout(() => ctl.abort(), 10000);
      const h = Object.assign({ Authorization: 'Bearer ' + token }, body !== undefined ? { 'Content-Type': 'application/json' } : {}, headers || {});
      res = await fetchFn(root + path, { method, headers: h, body: body !== undefined ? JSON.stringify(body) : undefined, cache: 'no-store', credentials: 'omit', redirect: 'error', signal: ctl ? ctl.signal : undefined });
    } catch (x) { return { status: 0, body: null }; } finally { if (timer) clearTimeout(timer); }
    let data = null;
    try { data = await res.json(); } catch (x) { data = null; }
    return { status: res.status, body: data };
  };
  return {
    me: () => call('GET', '/v1/me'),
    people: (p) => call('GET', proj(p) + '/people'),
    list: (p, after) => call('GET', proj(p) + '/docs?withdrawn=1&limit=1000&after=' + encodeURIComponent(after || '')),
    get: (p, id) => call('GET', proj(p) + '/docs/' + enc(id)),
    put: (p, id, body, rev, key) => call('PUT', proj(p) + '/docs/' + enc(id), { body, if_rev: rev }, { 'Idempotency-Key': key }),
    events: (p, after) => call('GET', proj(p) + '/events?limit=' + CONN_EVENT_LIMIT + '&after=' + after),
    verify: (p, head) => call('GET', proj(p) + '/verify' + (head ? '?expect_head=' + encodeURIComponent(head) : ''))
  };
}

/* ---------- the engine ----------
   ctx = { api, project, me, base, revs, seq, head, idem, bad, busy, again, hooks }
   hooks: getS() the page's state now; swapPeople(list) and replace(patch, me) for signing in; apply(changes) put changes in the state (each may say who made it);
          notice(n); status(s, pending); activity(events) */
function connNew(api, project, me, hooks) {
  return { api, project, me, base: {}, revs: {}, seq: 0, head: { seq: 0, hash: '' }, idem: {}, bad: {}, busy: false, again: false, hooks };   // head: the end of the record as last seen
}
const connLocal = (ctx) => connDocsOf(ctx.hooks.getS());
/* what the server holds for a request that did not work, in words */
function connFailText(r, doing) {
  if (r.status === 0) return 'Could not reach the server to ' + doing + '.';
  const m = r.body && r.body.error && r.body.error.message;
  return (m ? m + ' ' : '') + '(' + doing + ': ' + r.status + ')';
}
/* after putting changes in the state, what the state really holds is what counts as agreed: it is never different from it, so no change is made up from it */
function connSet(ctx, changes) {
  ctx.hooks.apply(changes);
  const now = connLocal(ctx);
  changes.forEach((c) => {
    if (c.rev !== undefined) ctx.revs[c.id] = c.rev;
    if (c.id in now) ctx.base[c.id] = now[c.id]; else delete ctx.base[c.id];
  });
}

/* read everything the server holds and make it the page's state. Returns { ok, problem, bad }. */
async function connLoad(ctx) {
  const h = await ctx.api.events(ctx.project, 2147483647);   // asked for nothing after the end: only to learn where the record ends
  if (h.status !== 200) return { ok: false, problem: connFailText(h, 'read the record') };
  const docs = {}, meta = {};
  let after = '';
  for (let page = 0; page < 1000; page++) {
    const r = await ctx.api.list(ctx.project, after);
    if (r.status !== 200 || !r.body || !Array.isArray(r.body.docs)) return { ok: false, problem: connFailText(r, 'read the project') };
    r.body.docs.forEach((d) => { docs[d.id] = d.body === null ? null : connUnwire(d.id, d.body); meta[d.id] = d.rev; });
    if (!r.body.next) break;
    after = r.body.next;
  }
  if (ctx.hooks.swapPeople && ctx.people) ctx.hooks.swapPeople(ctx.people);   // the checks below know only the people of this project, so they come first; nothing is drawn between this and replace()
  const built = connBuild(ctx.hooks.getS(), docs);
  ctx.revs = meta; ctx.bad = {}; built.bad.forEach((b) => { ctx.bad[b.id] = true; });
  ctx.seq = h.body.head.seq; ctx.head = h.body.head;
  ctx.hooks.replace(built.patch, ctx.me);
  ctx.base = connLocal(ctx);
  return { ok: true, bad: built.bad };
}

/* send what the page changed, one document at a time, in an order that lets a decision go before the sign-offs on it */
async function connFlush(ctx) {
  if (ctx.busy) { ctx.again = true; return; }
  ctx.busy = true;
  try {
    do {
      ctx.again = false;
      for (let n = 0; n < 2000; n++) {
        const ch = connDiff(ctx.base, connLocal(ctx));
        if (!ch.length) break;
        if (await connSend(ctx, ch[0]) === 'stop') return;
      }
    } while (ctx.again);
    ctx.hooks.status('live', 0);
  } finally { ctx.busy = false; }
}

async function connSend(ctx, ch) {
  const rev = ctx.revs[ch.id] || 0, wire = ch.body === null ? null : connWire(ctx, ch.id, ch.body);
  const ck = ch.id + '@' + rev + '@' + connCanon(wire);
  const key = ctx.idem[ck] || (ctx.idem[ck] = 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10));   // the same request sent again after a lost answer does not happen twice
  const r = await ctx.api.put(ctx.project, ch.id, wire, rev, key);
  if (r.status === 0 || r.status === 429 || r.status >= 500) { ctx.hooks.status('offline', connDiff(ctx.base, connLocal(ctx)).length); return 'stop'; }
  if (r.status === 401) { ctx.hooks.status('denied', 0); return 'stop'; }
  delete ctx.idem[ck];
  if (r.status === 201) {
    ctx.revs[ch.id] = r.body.rev;
    if (ch.body === null) delete ctx.base[ch.id]; else ctx.base[ch.id] = ch.body;
    (r.body.cleared || []).forEach((cid) => {
      ctx.revs[cid] = (ctx.revs[cid] || 0) + 1;
      if (connLocal(ctx)[cid] !== undefined) { connSet(ctx, [{ id: cid, body: null }]); ctx.hooks.notice({ kind: 'cleared', id: cid, text: 'The sign-off on ' + cid.split('/')[1] + ' (' + cid.split('/')[2] + ') was cleared because the decision changed.' }); }
      delete ctx.base[cid];
    });
    return 'ok';
  }
  const e = (r.body && r.body.error) || {};
  const what = connName(ch.id);
  if (r.status === 409 && e.code === 'conflict') {
    const cur = e.current || null, theirs = cur && cur.body !== null ? connUnwire(ch.id, cur.body) : null;
    connSet(ctx, [{ id: ch.id, body: theirs, rev: typeof e.rev === 'number' ? e.rev : rev }]);
    if (!connSame(theirs, ch.body)) ctx.hooks.notice({ kind: 'conflict', id: ch.id, text: connWho(cur && cur.by) + ' changed ' + what + ' first' + (cur && cur.at ? ' (' + String(cur.at).replace('T', ' ').slice(0, 19) + ')' : '') + '. Your change was not made.', mine: connSay(ch.id, ch.body), theirs: theirs ? connSay(ch.id, theirs) : 'it was taken back' });
    return 'ok';
  }
  if (r.status === 409 && e.code === 'stale_signoff') {
    const target = ch.id.split('/')[1], dk = (target.slice(0, 3) === 'CL-' ? 'dec/' : 'rdec/') + target;
    const d = await ctx.api.get(ctx.project, dk);
    if (d.status === 200) connSet(ctx, [{ id: dk, body: d.body.body === null ? null : d.body.body, rev: d.body.rev }]);
    connSet(ctx, [{ id: ch.id, body: ctx.base[ch.id] || null }]);
    ctx.hooks.notice({ kind: 'conflict', id: ch.id, text: 'The decision moved on before your sign-off arrived, so the sign-off was not made. Read the decision as it is now and sign again if you still agree.', mine: connSay(ch.id, ch.body), theirs: 'the decision is now at revision ' + (e.decision_rev || '?') });
    return 'ok';
  }
  // refused by a rule, or the request was not acceptable: take the change back and say why, in the server's words
  connSet(ctx, [{ id: ch.id, body: ctx.base[ch.id] || null }]);
  ctx.hooks.notice({ kind: 'refused', id: ch.id, text: 'The server did not accept your change to ' + what + ': ' + (e.message || 'status ' + r.status) });
  return 'ok';
}

/* look for what others did since last time and put it in place */
async function connPoll(ctx) {
  const r = await ctx.api.events(ctx.project, ctx.seq);
  if (r.status === 401) { ctx.hooks.status('denied', 0); return 'denied'; }
  if (r.status !== 200 || !r.body) { ctx.hooks.status('offline', connDiff(ctx.base, connLocal(ctx)).length); return 'offline'; }
  const evs = r.body.events, head = r.body.head;
  if (head.seq < ctx.head.seq || (head.seq === ctx.head.seq && ctx.head.hash && head.hash !== ctx.head.hash)) { ctx.hooks.status('rolledback', 0); return 'rolledback'; }   // the record went backwards or was rewritten under us
  ctx.head = head;
  if (!evs.length) { ctx.hooks.status('live', connDiff(ctx.base, connLocal(ctx)).length); return 'quiet'; }
  ctx.seq = evs[evs.length - 1].seq;
  ctx.hooks.activity(evs);
  const ids = [];
  evs.forEach((e) => { if (e.type === 'doc' && e.rev > (ctx.revs[e.target] || 0) && ids.indexOf(e.target) < 0) ids.push(e.target); });
  if (evs.length >= CONN_EVENT_LIMIT || ids.length > CONN_MAX_PER_POLL) return connReload(ctx);
  const changes = [];
  for (const id of ids) {
    const d = await ctx.api.get(ctx.project, id);
    if (d.status === 0) { ctx.hooks.status('offline', 0); ctx.seq = Math.min(ctx.seq, evs[0].seq - 1); return 'offline'; }
    if (d.status !== 200) continue;
    changes.push({ id, rev: d.body.rev, body: d.body.body === null ? null : connUnwire(id, d.body.body), by: d.body.by });
  }
  connTake(ctx, changes);
  ctx.hooks.status('live', connDiff(ctx.base, connLocal(ctx)).length);
  return 'changed';
}

/* put changes that came from the server in place, except where the person has a change of their own waiting on the same document */
function connTake(ctx, changes) {
  const local = connLocal(ctx), ok = [];
  changes.forEach((c) => {
    if (c.rev <= (ctx.revs[c.id] || 0)) return;
    if (!connSame(local[c.id], ctx.base[c.id])) return;      // theirs and a change of yours are both waiting: sending yours will be refused, and then you see theirs
    const why = connCheck(c.id, c.body);
    if (why) { ctx.revs[c.id] = c.rev; ctx.bad[c.id] = true; ctx.hooks.notice({ kind: 'ignored', id: c.id, text: 'A change by ' + connWho(c.by) + ' to ' + connName(c.id) + ' was left out because ' + why + '.' }); return; }
    ok.push(c);
  });
  if (ok.length) connSet(ctx, ok.map((c) => ({ id: c.id, body: c.body, rev: c.rev, by: c.by })));
}

/* too much changed to read one by one: read everything again and put the differences in place */
async function connReload(ctx) {
  const docs = {};
  let after = '';
  for (let page = 0; page < 1000; page++) {
    const r = await ctx.api.list(ctx.project, after);
    if (r.status !== 200 || !r.body || !Array.isArray(r.body.docs)) { ctx.hooks.status(r.status === 401 ? 'denied' : 'offline', 0); return 'offline'; }
    r.body.docs.forEach((d) => { docs[d.id] = d; });
    if (!r.body.next) break;
    after = r.body.next;
  }
  const changes = [];
  Object.keys(docs).forEach((id) => {
    const d = docs[id], body = d.body === null ? null : connUnwire(id, d.body);
    if (d.rev > (ctx.revs[id] || 0)) changes.push({ id, rev: d.rev, body, by: d.by });
  });
  Object.keys(ctx.base).forEach((id) => { if (!(id in docs)) changes.push({ id, rev: (ctx.revs[id] || 0) + 1, body: null }); });
  connTake(ctx, changes);
  ctx.hooks.status('live', connDiff(ctx.base, connLocal(ctx)).length);
  return 'changed';
}

/* ask the server to recompute its record, against the newest entry it reports a moment before, so a record rewritten while it is being checked is noticed. A record that has become shorter or different from the one this page saw is noticed by the poll (it stops everything: status 'rolledback'). */
async function connCheckRecord(ctx) {
  for (let tries = 0; tries < 3; tries++) {
    const e = await ctx.api.events(ctx.project, 2147483647);
    if (e.status !== 200) return { ok: false, text: connFailText(e, 'read the end of the record') };
    const v = await ctx.api.verify(ctx.project, e.body.head.hash);
    if (v.status !== 200 || !v.body) return { ok: false, text: connFailText(v, 'check the record') };
    if (v.body.ok) return { ok: true, entries: v.body.entries, head: v.body.head, text: 'The shared record was checked just now: ' + v.body.entries + ' entries, each one follows from the one before, and every document matches the fingerprint in the record. The newest entry’s fingerprint starts ' + v.body.head.slice(0, 12) + '.' };
    if (/^the newest entry/.test(v.body.why) && tries < 2) continue;   // somebody wrote between the two questions: ask again
    return { ok: false, at: v.body.at, text: 'The shared record does not check out at entry ' + v.body.at + ': ' + v.body.why + '. Do not rely on it until the person who runs the server has looked.' };
  }
  return { ok: false, text: 'The record kept changing while it was checked. Try again.' };
}
