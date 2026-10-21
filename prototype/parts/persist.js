/* ---------- keeping the work ----------
   The page keeps what people decided, signed, wrote and labelled, and the record of it, in this browser, and can write it to a file and read it back.
   Which screen is open, the filters and half-typed boxes are not kept. Reading a file back is checked before anything is replaced: the format, the
   project it belongs to, the shape of every entry, the entries that point at nothing, and the event chain. A file that fails any of these is refused
   and the work in the browser is left as it was.

   What this is not: a shared store. Two people in two browsers each have their own copy. The reference server in reqin/src/reqin/server is the
   shared one (one copy, who may change what, no silent overwrites); the page is not connected to it yet. */
const PERSIST_FORMAT = 'reqin-project-state/1';
const PERSIST_STORE = 'reqin-prototype-state/1';
const PERSIST_MAX = 4 * 1024 * 1024;
const PERSIST_PROBE = 12;   // how many clusters and how many requirements are drawn in full when a file is checked
const PERSIST_KEYS = ['source', 'scope', 'person', 'blind', 'blindDone', 'events', 'fmt', 'published', 'baseId', 'dec', 'sign', 'objections', 'adjud', 'res', 'why', 'ref', 'hand', 'sendF', 'replyNote',
  'peeled', 'claims', 'liveVer', 'dirs', 'stale', 'sib', 'lensNote', 'chat', 'polLane', 'polNew', 'polCross', 'polBase', 'scopeChoice', 'pilotAlloc', 'adjNote', 'sibNote', 'gold', 'rdec', 'rform', 'mapOver', 'aiOn', 'aiSheet'];
/* maps whose keys are cluster IDs (a key like "CL-014:nu" counts by what is in front of the colon) and those whose keys are requirement IDs */
const PERSIST_BY_CLUSTER = ['dec', 'sign', 'objections', 'adjud', 'res', 'why', 'ref', 'hand', 'sendF', 'replyNote', 'peeled', 'claims', 'liveVer', 'stale', 'sib', 'chat', 'adjNote', 'sibNote', 'blindDone'];
const PERSIST_BY_REQ = ['rdec', 'rform'];
/* what each entry of those maps is, as the page writes it; an entry of any other kind is left out */
const PERSIST_VALUE = { dec: 'null|object', sign: 'object', objections: 'null|object', adjud: 'null|object', res: 'null|object', why: 'boolean', ref: 'null|string', hand: 'null|object', sendF: 'object', replyNote: 'string',
  peeled: 'array', claims: 'null|object', liveVer: 'number', stale: 'null|object', sib: 'null|array', chat: 'array', adjNote: 'string', sibNote: 'boolean', blindDone: 'string|boolean', rdec: 'object', rform: 'object' };
const PERSIST_DEC_OUT = ['merge', 'link', 'escalate', 'reject', 'supersede'], PERSIST_HAND_STATUS = ['waiting', 'agreed', 'returned', 'closed'];
const persistStr = (v) => v === undefined || typeof v === 'string';
const persistBool = (v) => v === undefined || typeof v === 'boolean';
const persistReqIds = (a) => Array.isArray(a) && a.every((id) => persistHas(REQ_BY, id));
/* a cluster decision as the page writes it: every list is a list, every ID is a requirement this project has */
const persistDecOk = (d) => persistPlain(d) && PERSIST_DEC_OUT.indexOf(d.outcome) >= 0 && ['by', 'lens', 'at', 'rev'].every((f) => typeof d[f] === 'string') && ['strategy', 'member', 'text', 'reason', 'note', 'vs', 'ownFrom'].every((f) => persistStr(d[f])) &&
  persistBool(d.newWording) && persistBool(d.weakening) && persistReqIds(d.covers) && persistReqIds(d.kept) && Array.isArray(d.revs) && d.revs.every(persistPlain) && (d.share === undefined || d.share === null || persistPlain(d.share));
const persistRdOk = (d) => persistPlain(d) && persistHas(RD_BY, d.outcome) && ['by', 'rev'].every((f) => typeof d[f] === 'string') && ['reason', 'note', 'text', 'cover', 'q', 'to', 'lens', 'at'].every((f) => persistStr(d[f])) && persistBool(d.newWording) && persistBool(d.weakening) && (d.asked === undefined || d.asked === null || persistPlain(d.asked));
const persistKindIn = (v, want) => want.split('|').indexOf(persistKind(v)) >= 0;
const persistKind = (v) => (v === null ? 'null' : Array.isArray(v) ? 'array' : typeof v);
const persistPlain = (v) => persistKind(v) === 'object';
/* a key the map really has: not one every object has ("constructor", "toString", "__proto__") */
const persistHas = (o, k) => typeof k === 'string' && Object.prototype.hasOwnProperty.call(o, k);
let persistFpMemo = '';   // the requirements and clusters never change while the page is open, and a shared project checks a document at a time
const persistFingerprint = () => persistFpMemo || (persistFpMemo = trMix(REQS.map((r) => r.id).join(',') + '|' + CLUSTERS.map((c) => c.id).join(',')).toString(16));
const persistProject = () => ({ name: 'Reference air vehicle', source: 'sample', requirements: REQS.length, clusters: CLUSTERS.length, fingerprint: persistFingerprint() });

/* the one place the event chain is checked: 'ok', or 'fail:<seq>' at the first entry that does not follow from the one before */
function chainCheck(list) {
  let prev = '00000000';
  for (const e of list) {
    const payload = [e.seq, e.type, e.actor, e.text, e.target].join('|');
    if (e.prev !== prev || h32(e.prev + payload) !== e.hash) return 'fail:' + e.seq;
    prev = e.hash;
  }
  return 'ok';
}
function persistPick(S) { const o = {}; PERSIST_KEYS.forEach((k) => { if (S[k] !== undefined) o[k] = S[k]; }); return o; }
/* is there anything worth keeping */
function persistHasWork(S) {
  return S.events.length > 0 || ['dec', 'sign', 'res', 'hand', 'claims', 'rdec', 'peeled', 'objections', 'stale', 'sib'].some((k) => Object.keys(S[k] || {}).length > 0) || Object.keys((S.gold && S.gold.labels) || {}).length > 0;
}
function persistCounts(S) {
  const n = (o) => Object.keys(o || {}).filter((k) => o[k] !== undefined && o[k] !== null).length;
  return {
    decisions: n(S.dec) + n(S.rdec), signoffs: Object.keys(S.sign || {}).reduce((a, k) => a + Object.keys(S.sign[k] || {}).length, 0), handoffs: n(S.hand),
    labels: Object.keys((S.gold && S.gold.labels) || {}).reduce((a, k) => a + Object.keys(S.gold.labels[k]).length, 0), events: (S.events || []).length
  };
}
/* "1 decision, 0 sign-offs": the counts in words, with the singular where the number is one */
function persistSaid(c, keys) {
  const W = { decisions: ['decision', 'decisions'], signoffs: ['sign-off', 'sign-offs'], handoffs: ['hand-off', 'hand-offs'], labels: ['label', 'labels'], events: ['event', 'events'] };
  return keys.map((k) => c[k] + ' ' + W[k][c[k] === 1 ? 0 : 1]).join(', ');
}
function persistFile(S, at) {
  return { format: PERSIST_FORMAT, saved: at || new Date().toISOString(), app: 'reqin prototype', project: persistProject(), counts: persistCounts(S), state: persistPick(S) };
}

/* Check something that claims to be saved work. Returns { ok, problems, state, dropped, notes } where state holds only the kept keys, with the entries
   that point at nothing taken out. Nothing here touches the page. */
function persistCheck(file) {
  const out = { ok: false, problems: [], state: {}, dropped: 0, notes: [], counts: null, saved: '' };
  const bad = (t) => { out.problems.push(t); return out; };
  if (!persistPlain(file)) return bad('This is not a saved project: the file does not hold a JSON object.');
  if (file.format !== PERSIST_FORMAT) return bad('This is not a saved project from this app. Its format is ' + (typeof file.format === 'string' ? '“' + file.format.slice(0, 40) + '”' : 'missing') + ' and this app reads ' + PERSIST_FORMAT + '.');
  if (!persistPlain(file.state)) return bad('The file has no saved work in it.');
  const pj = persistProject(), fp = file.project;
  if (!persistPlain(fp) || fp.fingerprint !== pj.fingerprint) return bad('This work belongs to a different project' + (persistPlain(fp) && typeof fp.name === 'string' ? ' (' + fp.name.slice(0, 60) + ')' : '') + '. Its requirements and clusters are not the ones open here, so it was not loaded.');
  out.saved = typeof file.saved === 'string' ? file.saved.slice(0, 40) : '';
  const st = file.state, ok = {};
  Object.keys(st).forEach((k) => {
    if (PERSIST_KEYS.indexOf(k) < 0) { out.notes.push('Ignored “' + String(k).slice(0, 30) + '”: not something this app keeps.'); return; }
    const d = DEFAULTS[k], v = st[k], want = persistKind(d), got = persistKind(v);
    if (want !== got && !(k === 'blind' && (got === 'boolean' || got === 'null'))) { out.problems.push('“' + k + '” should be ' + want + ' and is ' + got + '.'); return; }
    ok[k] = v;
  });
  if (out.problems.length) return out;
  // entries that point at a cluster or a requirement this project does not have, or that are not shaped like what they claim to be
  let dropped = 0;
  const known = (id) => persistHas(CL_BY, String(id).split(':')[0]) || persistHas(REQ_BY, String(id).split(':')[0]);
  PERSIST_BY_CLUSTER.forEach((k) => {
    if (!ok[k]) return;
    const keep = {};
    Object.keys(ok[k]).forEach((id) => { if (!known(id) || !persistKindIn(ok[k][id], PERSIST_VALUE[k])) { dropped++; return; } keep[id] = ok[k][id]; });
    ok[k] = keep;
  });
  PERSIST_BY_REQ.forEach((k) => {
    if (!ok[k]) return;
    const keep = {};
    Object.keys(ok[k]).forEach((id) => { if (!persistHas(REQ_BY, id) || !persistPlain(ok[k][id])) { dropped++; return; } keep[id] = ok[k][id]; });
    ok[k] = keep;
  });
  if (ok.dec) Object.keys(ok.dec).forEach((id) => { const d = ok.dec[id]; if (d !== null && !persistDecOk(d)) { delete ok.dec[id]; dropped++; } });
  if (ok.rdec) Object.keys(ok.rdec).forEach((id) => { if (!persistRdOk(ok.rdec[id])) { delete ok.rdec[id]; dropped++; } });
  if (ok.sign) Object.keys(ok.sign).forEach((id) => { const g = ok.sign[id]; if (!Object.keys(g).every((s) => SLOT_KEYS.indexOf(s) >= 0 && persistPlain(g[s]) && typeof g[s].by === 'string' && persistStr(g[s].at) && persistStr(g[s].rev))) { delete ok.sign[id]; dropped++; } });
  if (ok.hand) Object.keys(ok.hand).forEach((id) => { const h = ok.hand[id]; if (h !== null && !(persistPlain(h) && PERSIST_HAND_STATUS.indexOf(h.status) >= 0 && PEOPLE.some((p) => p.k === h.from) && PEOPLE.some((p) => p.k === h.to) && ['ask', 'note', 'at', 'reply', 'draft'].every((f) => persistStr(h[f])))) { delete ok.hand[id]; dropped++; } });
  if (ok.sib) Object.keys(ok.sib).forEach((id) => { const b = ok.sib[id]; if (b !== null && !(b.length === 2 && b.every((x) => persistPlain(x) && typeof x.rev === 'string' && persistStr(x.text)))) { delete ok.sib[id]; dropped++; } });
  if (ok.claims) Object.keys(ok.claims).forEach((id) => { const c = ok.claims[id]; if (c !== null && !(persistPlain(c) && typeof c.by === 'string' && persistStr(c.lens) && (c.mins === undefined || typeof c.mins === 'number'))) { delete ok.claims[id]; dropped++; } });
  if (ok.person && !PEOPLE.some((p) => p.k === ok.person)) { out.problems.push('The person “' + String(ok.person).slice(0, 30) + '” is not one of the people in this project.'); return out; }
  if (ok.scope && ok.scope !== 'all' && !ALLOCS.some((a) => a.k === ok.scope)) { delete ok.scope; out.notes.push('The saved allocation is not in this project, so the whole project is shown.'); }
  if (ok.gold) {
    const g = ok.gold;
    if (!persistPlain(g.labels) || !persistPlain(g.adj) || !persistPlain(g.skip) || !persistPlain(g.last) || typeof g.cut !== 'number' || !(g.cut >= 0 && g.cut <= 1)) { out.problems.push('The saved labels are not in the shape this app writes.'); return out; }
    const by = goldPlan().by, keepL = {};
    Object.keys(g.labels).forEach((key) => { const L = g.labels[key]; if (persistHas(by, key) && persistPlain(L) && Object.keys(L).length && Object.keys(L).every((w) => PEOPLE.some((p) => p.k === w) && persistPlain(L[w]) && persistHas(GOLD_BY, L[w].v) && (L[w].note === undefined || typeof L[w].note === 'string'))) keepL[key] = L; else dropped++; });
    ok.gold = Object.assign({}, g, { labels: keepL });
  }
  if (ok.events) {
    if (ok.events.length > 20000 || !ok.events.every((e) => persistPlain(e) && typeof e.seq === 'number' && ['type', 'actor', 'text', 'target', 'time', 'prev', 'hash', 'payload'].every((f) => typeof e[f] === 'string'))) { out.problems.push('The record of events is not in the shape this app writes.'); return out; }
    const r = chainCheck(EV_SEED.concat(ok.events));
    if (r !== 'ok') { out.problems.push('The record of events has been changed: entry ' + r.slice(5) + ' no longer matches its fingerprint. The file was not loaded.'); return out; }
    out.notes.push('The record of events is intact (' + (ok.events.length + EV_SEED.length) + ' entries).');
  }
  // the AI switch and data sheet decide what may leave for a model, so they must be the shape this app writes and agree with the record of events
  if (ok.aiSheet !== undefined && !aiSheetOk(ok.aiSheet)) { out.problems.push('The saved AI data sheet is not in the shape this app writes, so the file was not loaded.'); return out; }
  { const want = aiFromEvents(ok.events || []), sheet = ok.aiSheet || DEFAULTS.aiSheet, on = ok.aiOn === undefined ? DEFAULTS.aiOn : ok.aiOn;
    if (aiSheetFp(sheet) !== want.fp || on !== want.on) { out.problems.push('The AI switch or the AI data sheet in this file does not match the record of events, so the file was not loaded.'); return out; } }
  out.dropped = dropped; out.state = ok; out.counts = persistCounts(Object.assign({}, DEFAULTS, ok)); out.ok = true;
  if (dropped) out.notes.push(dropped + (dropped === 1 ? ' entry pointed' : ' entries pointed') + ' at something this project does not have, or was not in the right shape, and was left out.');
  return out;
}

/* ---------- the browser's store; every call may fail (private windows, blocked storage, full) and the page works without it ---------- */
function persistStore() { try { const s = typeof window !== 'undefined' ? window.localStorage : null; if (!s) return null; s.setItem('reqin-probe', '1'); s.removeItem('reqin-probe'); return s; } catch (x) { return null; } }
function persistRead() {
  const s = persistStore();
  if (!s) return { status: 'off', state: null };
  try {
    const raw = s.getItem(PERSIST_STORE);
    if (!raw) return { status: 'ready', state: null };
    if (raw.length > PERSIST_MAX) { s.removeItem(PERSIST_STORE); return { status: 'ready', state: null }; }
    const file = JSON.parse(raw), r = persistCheck(file);
    if (!r.ok) { s.removeItem(PERSIST_STORE); return { status: 'ready', state: null, refused: r.problems[0] }; }
    return { status: 'saved', state: r.state, saved: r.saved, opened: file.opened === true, counts: r.counts };
  } catch (x) { try { s.removeItem(PERSIST_STORE); } catch (y) { /* nothing more to do */ } return { status: 'ready', state: null, refused: 'It was not readable.' }; }
}
function persistWrite(S, opened) {
  const s = persistStore();
  if (!s) return 'off';
  try {
    const f = persistFile(S); f.opened = !!opened;
    const raw = JSON.stringify(f);
    if (raw.length > PERSIST_MAX) return 'full';
    s.setItem(PERSIST_STORE, raw);
    return 'saved';
  } catch (x) { return 'full'; }
}
function persistClear() { const s = persistStore(); try { if (s) s.removeItem(PERSIST_STORE); } catch (x) { /* nothing to clear */ } }
