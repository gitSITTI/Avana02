/* ---------- what a decision moves outside the requirement list: verification items, parent and child links, baselines ----------
   Removing a requirement is never only a change to the list. Three other things hang on it:
     - its verification items (the tests, analyses, inspections and demonstrations that prove it), which have to be pointed at whatever takes its place;
     - the requirements below it, which have to be re-parented, and the requirement above it, which can be left with no child;
     - its baseline, when it is baselined: the change needs a change request.
   The trace map lists every one of these, row by row, so the tools that hold those links can be brought into step. It is built from the same
   decisions the Results page and the V count, and the checks in verify.js make the two agree: the item rows equal the V's "to carry over" number,
   the re-read rows equal its "to read again" number, and the old IDs equal the requirements that leave the left leg.

   The sample data has no verification items, parent links or baselines for requirements that stand alone, so they are given here from a hash of the
   ID (the same every run). A real import reads them from the model: verify links, parent links and baseline membership. The file says so. */
/* A hash with a final mix, so each choice is spread evenly and does not line up with the level, the method or the item count that vHash gives the same requirement. */
function trMix(str) { let h = 2166136261; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 16777619); } h ^= h >>> 16; h = Math.imul(h, 0x85ebca6b); h ^= h >>> 13; h = Math.imul(h, 0xc2b2ae35); h ^= h >>> 16; return h >>> 0; }
const trH = (id, salt, mod) => trMix(salt + '|' + id) % mod;
const TR_PFX = { Test: 'TC', Analysis: 'AN', Inspection: 'IN', Demonstration: 'DM' };
const TR_ITEMS = {}, TR_ITEM_BY = {}, TR_PARENT = {}, TR_CHILD = {};
REQS.forEach((r, i) => {
  const v = VREQ[r.id], list = [];
  // 1000 + 4 * position + k is unique by construction: a requirement has at most three items
  for (let k = 0; k < v.vi; k++) { const it = { id: (TR_PFX[v.vm] || 'VI') + '-' + (1000 + i * 4 + k), method: v.vm || '', lvl: v.lvl, req: r.id }; list.push(it); TR_ITEM_BY[it.id] = it; }
  TR_ITEMS[r.id] = list;
});
/* Each requirement below the top level traces to one requirement one level up, in the same allocation when there is one. Wordings in a cluster mostly
   share a parent (seven in ten), and in a "contains" cluster the stricter wording sits under the general one. */
(function () {
  const pool = {};
  const put = (k, id) => { (pool[k] = pool[k] || []).push(id); };
  REQS.forEach((r) => { const l = VREQ[r.id].lvl; put(r.alloc + '|' + l, r.id); put('*|' + l, r.id); });
  const pick = (r) => { const l = VREQ[r.id].lvl; if (l <= 1) return ''; const a = pool[r.alloc + '|' + (l - 1)] || pool['*|' + (l - 1)] || []; return a.length ? a[trH(r.id, 'par', a.length)] : ''; };
  CLUSTERS.forEach((c) => {
    const first = c.members[0];
    c.members.forEach((m, i) => {
      if (i === 0) TR_PARENT[m.id] = pick(REQ_BY[m.id]);
      else if (c.rel === 'SUBSUMES' && VREQ[m.id].lvl > VREQ[first.id].lvl) TR_PARENT[m.id] = first.id;
      else if (trH(m.id, 'sp', 100) < 70) TR_PARENT[m.id] = TR_PARENT[first.id];
      else TR_PARENT[m.id] = pick(REQ_BY[m.id]);
    });
  });
  REQS.forEach((r) => { if (TR_PARENT[r.id] === undefined) TR_PARENT[r.id] = pick(r); });
  REQS.forEach((r) => { const p = TR_PARENT[r.id]; if (p) (TR_CHILD[p] = TR_CHILD[p] || []).push(r.id); });
})();
/* Baselines: in a cluster, the wording marked baselined in the data (its change request is linked to the cluster); for a requirement that stands alone, about
   one in twelve, and the change request has to be written when the decision is recorded. */
const TR_BL = {};
REQS.forEach((r) => {
  if (r.cid) { const c = CL_BY[r.cid], m = c.members.find((x) => x.id === r.id); if (m && /^Baselined/.test(m.base || '')) TR_BL[r.id] = { bl: (/BL-\d+/.exec(m.base) || ['BL-2'])[0], cr: c.cr || '' }; }
  else if (trH(r.id, 'bl', 100) < 8) TR_BL[r.id] = { bl: 'BL-' + (1 + trH(r.id, 'bn', 2)), cr: '' };
});
const trBase = (id) => TR_BL[id] || null;
const TR_CR_RE = /^CR-\d{3,6}$/;
const trCrNorm = (t) => (t || '').trim().toUpperCase();
const trIsNew = (to) => to.slice(0, 4) === 'NEW:';
const trLvlOf = (id) => (id && !trIsNew(id) && VREQ[id] ? VREQ[id].lvl : trIsNew(id) && CL_BY[id.slice(4)] ? CL_BY[id.slice(4)].lvls[0] : 0);
const TR_WHAT = { merged: 'Merged into another wording', superseded: 'Marked superseded', dropped: 'Dropped', notreq: 'Taken out: not a requirement' };
const TR_STATUS = { approved: 'Approved', pending: 'Waiting for sign-off' };

/* every requirement a counted decision takes off the left leg, and where its items and children go.
   to: the requirement that takes its place; 'NEW:<cluster>' when new wording replaces it; '' when nothing does */
function trRemovals(S, infos) {
  const out = [];
  infos.forEach((x) => {
    const dec = standingDec(x); if (!dec) return;
    const c = x.c, ms = membersOf(S, c), d = dispositionsOf(S, c, ms, {}, {}, dec);
    const kept = d.survivor || (d.newWording ? '' : ((ms.find((m) => d.by[m.id].kind === 'keep') || {}).id || ''));
    const to = d.newWording ? 'NEW:' + c.id : kept;
    ms.forEach((m) => {
      const kind = d.by[m.id].kind; if (kind !== 'merged' && kind !== 'superseded') return;
      out.push({ id: m.id, kind, to, src: c.id, srcKind: 'cluster', status: x.st === 'approved' ? 'approved' : 'pending', cr: c.baselined ? c.cr || '' : '' });
    });
  });
  rdList(S, '').forEach((x) => {
    const o = x.dec.outcome; if (!RD_REMOVES(o)) return;
    out.push({ id: x.r.id, kind: o === 'drop' ? 'dropped' : 'notreq', to: x.dec.cover || '', src: x.r.id, srcKind: 'single', status: x.status === 'approved' ? 'approved' : 'pending', cr: x.dec.cr || '' });
  });
  return out;
}

/* the rows one removal produces. gone is every requirement that leaves, so a child that is itself leaving is not re-parented */
function trRowsOf(r, gone) {
  const v = VREQ[r.id], toLvl = trLvlOf(r.to), tv = r.to && !trIsNew(r.to) ? VREQ[r.to] : null;
  const methodChange = !!(tv && v.vm && tv.vm && v.vm !== tv.vm);
  const base = { src: r.src, srcKind: r.srcKind, status: r.status };
  const alias = Object.assign({ old: r.id, kind: r.kind, now: r.to, lvl: v.lvl, alloc: REQ_BY[r.id].alloc, methodChange }, base);
  const items = TR_ITEMS[r.id].map((it) => Object.assign({ item: it.id, method: it.method, from: r.id, to: r.to, fromLvl: v.lvl, toLvl, levelChange: !!(tv && tv.lvl !== v.lvl), methodChange, action: r.to ? 'move' : 'choose' }, base));
  const links = (TR_CHILD[r.id] || []).filter((c) => !gone[c]).map((c) => {
    // the wording that is kept can itself be a child of the one it replaces; it then takes that one's place in the hierarchy
    const now = c === r.to ? TR_PARENT[r.id] || '' : r.to;
    return Object.assign({ req: c, kind: now ? 'child_moves' : 'child_needs_parent', from: r.id, to: now, levelChange: !!(now && !trIsNew(now) && VREQ[now] && VREQ[c].lvl !== VREQ[now].lvl + 1) }, base);
  });
  const b = trBase(r.id);
  const bases = b ? [Object.assign({ req: r.id, bl: b.bl, cr: r.cr || b.cr || '', change: TR_WHAT[r.kind] }, base)] : [];
  return { alias, items, links, bases };
}

/* The whole trace map. only: 'approved' keeps the decisions every required lens has signed, which is what the package contains. */
function trOf(S, infos, only) {
  let rem = trRemovals(S, infos);
  if (only === 'approved') rem = rem.filter((r) => r.status === 'approved');
  const gone = {}; rem.forEach((r) => { gone[r.id] = r; });
  // a covering requirement can itself leave later; the items then follow the chain to whatever finally stays (or to nowhere, if nothing does)
  const settle = (to) => { const seen = {}; while (to && !trIsNew(to) && gone[to] && !seen[to]) { seen[to] = 1; to = gone[to].to; } return to && !trIsNew(to) && gone[to] ? '' : to; };
  rem.forEach((r) => { r.to = settle(r.to); });
  const T = { removals: rem, gone, aliases: [], items: [], links: [], bases: [] };
  rem.forEach((r) => { const w = trRowsOf(r, gone); T.aliases.push(w.alias); w.items.forEach((x) => T.items.push(x)); w.links.forEach((x) => T.links.push(x)); w.bases.forEach((x) => T.bases.push(x)); });
  // new wording on a requirement that stays: its items are read again against the new text
  rdList(S, '').forEach((x) => {
    if (x.dec.outcome !== 'reword' || (only === 'approved' && x.status !== 'approved')) return;
    const st = x.status === 'approved' ? 'approved' : 'pending', v = VREQ[x.r.id];
    TR_ITEMS[x.r.id].forEach((it) => T.items.push({ item: it.id, method: it.method, from: x.r.id, to: x.r.id, fromLvl: v.lvl, toLvl: v.lvl, levelChange: false, methodChange: false, action: 'reread', src: x.r.id, srcKind: 'single', status: st }));
    const b = trBase(x.r.id);
    if (b) T.bases.push({ req: x.r.id, bl: b.bl, cr: x.dec.cr || b.cr || '', change: 'New wording', src: x.r.id, srcKind: 'single', status: st });
  });
  // a requirement above one that leaves is left with no child when every child it had is leaving
  const lost = {};
  rem.forEach((r) => { const p = TR_PARENT[r.id]; if (p && !gone[p]) (lost[p] = lost[p] || []).push(r); });
  Object.keys(lost).sort().forEach((p) => {
    if ((TR_CHILD[p] || []).every((k) => gone[k])) T.links.push({ req: p, kind: 'parent_bare', from: lost[p].map((r) => r.id).join(' '), to: '', levelChange: false, src: lost[p][0].src, srcKind: lost[p][0].srcKind, status: lost[p].every((r) => r.status === 'approved') ? 'approved' : 'pending' });
  });
  const byA = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  T.aliases.sort((a, b) => byA(a.old, b.old));
  T.items.sort((a, b) => byA(a.item, b.item) || byA(a.action, b.action));
  const LK = { child_moves: 0, child_needs_parent: 1, parent_bare: 2 };
  T.links.sort((a, b) => LK[a.kind] - LK[b.kind] || byA(a.req, b.req));
  T.bases.sort((a, b) => byA(a.req, b.req));
  const cnt = (list, f) => list.filter(f).length;
  T.n = {
    aliases: T.aliases.length, targets: T.aliases.map((a) => a.now).filter((x, i, a) => x && a.indexOf(x) === i).length,
    moves: cnt(T.items, (x) => x.action === 'move'), choose: cnt(T.items, (x) => x.action === 'choose'), reread: cnt(T.items, (x) => x.action === 'reread'),
    methodShift: cnt(T.aliases, (a) => a.methodChange && a.srcKind === 'cluster'), levelShift: cnt(T.items, (x) => x.levelChange && x.srcKind === 'cluster'),
    kidsMoved: cnt(T.links, (x) => x.kind === 'child_moves'), kidsLost: cnt(T.links, (x) => x.kind === 'child_needs_parent'), bare: cnt(T.links, (x) => x.kind === 'parent_bare'),
    bases: T.bases.length, baseNoCr: cnt(T.bases, (b) => !b.cr)
  };
  T.empty = T.aliases.length + T.items.length + T.links.length + T.bases.length === 0;
  return T;
}

/* What one requirement leaving would move, before and after the decision is recorded. kind: 'drop', 'notreq' or 'reword'. cover: the covering requirement for a drop. */
function trImpactOne(S, r, kind, cover) {
  const out = { items: [], rereads: [], kids: [], parent: TR_PARENT[r.id] || '', bare: false, base: trBase(r.id), nothing: true };
  if (kind === 'reword') { out.rereads = TR_ITEMS[r.id].map((it) => it.id); out.nothing = out.rereads.length === 0 && !out.base; return out; }
  if (!RD_REMOVES(kind)) return out;
  const to = cover || '', gone = {}; gone[r.id] = true;
  const w = trRowsOf({ id: r.id, kind: kind === 'drop' ? 'dropped' : 'notreq', to, src: r.id, srcKind: 'single', status: 'pending', cr: '' }, gone);
  out.items = w.items; out.kids = w.links; out.to = to;
  const p = out.parent;
  out.bare = !!p && (TR_CHILD[p] || []).every((k) => k === r.id);
  out.nothing = false;
  return out;
}

/* ---------- the files ---------- */
const TR_CSV = {
  aliases: { file: 'alias-map.csv', head: ['old_id', 'becomes', 'what_happened', 'level', 'allocation', 'decided_in', 'status'], row: (a) => [a.old, trNowTxt(a.now, true), a.kind, 'L' + a.lvl, a.alloc, a.src, a.status] },
  items: { file: 'verification-items.csv', head: ['item_id', 'method', 'was_on', 'action', 'move_to', 'level_change', 'method_change', 'decided_in', 'status'], row: (x) => [x.item, x.method || 'none', x.from, x.action, x.action === 'move' ? trNowTxt(x.to, true) : '', x.levelChange ? 'yes' : 'no', x.methodChange ? 'yes' : 'no', x.src, x.status] },
  links: { file: 'parent-child-links.csv', head: ['requirement', 'what_changes', 'was', 'now', 'level_change', 'decided_in', 'status'], row: (x) => [x.req, x.kind, x.from, x.kind === 'parent_bare' ? '' : trNowTxt(x.to, true), x.levelChange ? 'yes' : 'no', x.src, x.status] },
  bases: { file: 'baselines.csv', head: ['requirement', 'baseline', 'change_request', 'what_changes', 'decided_in', 'status'], row: (b) => [b.req, b.bl, b.cr || 'missing', b.change, b.src, b.status] }
};
function trNowTxt(to, raw) {
  if (!to) return raw ? '' : 'Nothing takes its place';
  return trIsNew(to) ? (raw ? to : 'New requirement from ' + to.slice(4)) : to;
}
/* a cell that starts with = + - or @ would run as a formula when the file is opened in a spreadsheet, so it is marked as text */
function trCell(v) {
  let t = v === null || v === undefined ? '' : String(v);
  if (/^[=+\-@\t\r]/.test(t)) t = "'" + t;
  return /[",\n\r]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
}
function trCsv(T, tab) {
  const d = TR_CSV[tab], rows = T[tab];
  return [d.head.join(',')].concat(rows.map((x) => d.row(x).map(trCell).join(','))).join('\r\n') + '\r\n';
}
function trFile(S, T, only) {
  return {
    format: 'reqin-trace-map/1', baseline: S.baseId, scope: S.scope === 'all' ? 'all allocations' : S.scope,
    changes: only === 'approved' ? 'approved only' : 'every decided change, including changes still waiting for sign-off',
    sample_data: true,
    sample_note: 'Verification items, levels, parent links and baselines are sample values given to each requirement in this demonstration. A real import reads them from the model.',
    counts: T.n,
    old_ids: T.aliases.map((a) => ({ old_id: a.old, becomes: a.now || null, what_happened: a.kind, level: a.lvl, allocation: a.alloc, decided_in: a.src, status: a.status })),
    verification_items: T.items.map((x) => ({ item_id: x.item, method: x.method || null, was_on: x.from, action: x.action, move_to: x.action === 'move' ? x.to : null, level_change: x.levelChange, method_change: x.methodChange, decided_in: x.src, status: x.status })),
    parent_child_links: T.links.map((x) => ({ requirement: x.req, what_changes: x.kind, was: x.from, now: x.kind === 'parent_bare' ? null : x.to || null, level_change: x.levelChange, decided_in: x.src, status: x.status })),
    baselines: T.bases.map((b) => ({ requirement: b.req, baseline: b.bl, change_request: b.cr || null, what_changes: b.change, decided_in: b.src, status: b.status }))
  };
}

/* ---------- the same facts as sentences, for the panels ---------- */
const trPl = (n, a, b) => n + ' ' + (n === 1 ? a : b || a + 's');
const trIds = (a, n) => a.slice(0, n).join(', ') + (a.length > n ? ' and ' + (a.length - n) + ' more' : '');
/* kind: 'keep', 'reword', 'drop' or 'notreq' for a requirement that stands alone */
function trImpactLines(S, r, kind, cover) {
  if (!kind || kind === 'ask') return { on: false, head: '', lines: [] };
  const w = trImpactOne(S, r, kind, cover), lines = [];
  const head = 'What this moves';
  if (kind === 'keep') return { on: true, head, lines: [{ k: 'Nothing', v: 'Its verification items, its parent and its baseline stay as they are.' }] };
  const v = VREQ[r.id];
  if (kind === 'reword') {
    lines.push({ k: 'Verification', v: w.rereads.length ? trPl(w.rereads.length, 'item is', 'items are') + ' to be read again against the new wording (' + trIds(w.rereads, 4) + '). They stay on this requirement.' : 'No verification item is linked to it yet, so it shows as a gap on the V.' });
    lines.push({ k: 'Links', v: 'It keeps its place under its parent' + (w.parent ? ' (' + w.parent + ')' : '') + ' and the requirements below it.' });
  } else {
    const n = w.items.length;
    lines.push({ k: 'Verification', v: !n ? 'No verification item is linked to it.' : cover ? trPl(n, 'item moves', 'items move') + ' to ' + cover + ' (' + trIds(w.items.map((x) => x.item), 4) + ').' : trPl(n, 'item has', 'items have') + ' no requirement to point at (' + trIds(w.items.map((x) => x.item), 4) + '). Choose a covering requirement, or have a verifier retire them.' });
    const k = w.kids.length;
    lines.push({ k: 'Below it', v: !k ? 'No requirement traces to it.' : cover ? trPl(k, 'requirement moves', 'requirements move') + ' under ' + cover + ' (' + trIds(w.kids.map((x) => x.req), 4) + ').' : trPl(k, 'requirement needs', 'requirements need') + ' a new parent (' + trIds(w.kids.map((x) => x.req), 4) + ').' });
    lines.push({ k: 'Above it', v: w.parent ? (w.bare ? w.parent + ' is left with nothing below it.' : w.parent + ' keeps its other requirements below it.') : 'It is at level ' + v.lvl + ' and has no parent.' });
  }
  const b = w.base;
  lines.push({ k: 'Baseline', v: b ? 'In baseline ' + b.bl + '. This change needs a change request.' : 'Not in a baseline.' });
  return { on: true, head, lines };
}

const TR_TABS = [
  { k: 'aliases', name: 'Old and new IDs' },
  { k: 'items', name: 'Verification items' },
  { k: 'links', name: 'Parent and child links' },
  { k: 'bases', name: 'Baselines' }
];
/* hands a text file to the browser; a page with no document (the checks run without one) just skips it */
function trSave(name, text, type) {
  try {
    const b = new Blob([text], { type }), a = document.createElement('a');
    a.href = URL.createObjectURL(b); a.download = name; document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  } catch (x) { /* no DOM */ }
}
