
/* ---------- results: the consolidated set set against the original, and a grade ----------
   Everything here is computed from the decisions in the project (the seeded ones from teammates, which are sample data, and yours).
   The grading rule is a proposal for the team to agree, not a standard. The weights and bands are written out on the page. */
const GRADE_PARTS = [
  { k: 'cover', name: 'Accounted for', weight: 20, plain: 'Every original requirement is kept, merged into a named survivor, or has a recorded reason. Requirements in clusters nobody has decided yet are not accounted for.' },
  { k: 'oblig', name: 'Obligations preserved', weight: 30, plain: 'No merge, drop or rewording loosens a number, unit, shall or condition unless the owners and the process engineer have signed it.' },
  { k: 'sign', name: 'Signed off', weight: 20, plain: 'Every lens the sign-off policy requires has signed the decision.' },
  { k: 'why', name: 'The why is written down', weight: 15, plain: 'The decision carries a note saying why, as well as a reason code.' },
  { k: 'second', name: 'A second pair of eyes', weight: 15, plain: 'Someone other than the person who decided has signed, checked or reviewed it.' }
];
const GRADE_BANDS = [[90, 'A'], [80, 'B'], [70, 'C'], [60, 'D'], [0, 'F']];
const GRADE_ORDER = ['A', 'B', 'C', 'D', 'F'];
function letterOf(score) { return GRADE_BANDS.find((b) => score >= b[0])[1]; }
const COUNTED = ['decided', 'review', 'approved', 'siblings'];   // a decision under dispute or gone stale does not count until it is settled
const standingDec = (x) => (x.dec && COUNTED.indexOf(x.st) >= 0 ? x.dec : null);   // the one rule for "this cluster has a decision that counts": Results, the V and the queue all use it
/* alloc: '' for everything in scope, or one allocation name */
function resultsOf(S, infos, alloc) {
  const U = universe(S);
  const reqs = U.reqs.filter((r) => !alloc || r.alloc === alloc);
  const sel = infos.filter((x) => !alloc || x.c.alloc === alloc);
  const R = { n: reqs.length, clusters: sel.length, decided: 0, kinds: { asis: 0, kept1: 0, reworded: 0, dropped: 0, notreq: 0, keep: 0, merged: 0, separate: 0, linked: 0, escalated: 0, superseded: 0, waiting: 0 }, singleN: 0, single: { keep: 0, reword: 0, drop: 0, notreq: 0, ask: 0 }, looseN: 0, after: 0, projected: 0, newWord: 0, mergeN: 0, unprotected: 0, signN: 0, signDone: 0, why: 0, second: 0, waitingClusters: 0, noWhy: 0, noSecond: 0, notSigned: 0, cuts: [], ids: { cover: [], oblig: [], sign: [], why: [], second: [] } };
  let inCl = 0, peeledN = 0;
  sel.forEach((x) => {
    const c = x.c, ms = membersOf(S, c);
    inCl += c.members.length; peeledN += c.members.length - ms.length;
    const dec = standingDec(x);
    if (dec) {
      const d = dispositionsOf(S, c, ms, {}, {}, dec);
      ms.forEach((m) => { const k = d.by[m.id].kind; R.kinds[k === 'pending' ? 'waiting' : k]++; });
      R.after += d.remain; R.projected += d.remain; R.decided++; if (d.newWording) R.newWord++;
      if (dec.outcome === 'merge') { R.mergeN++; if (dec.weakening && !(x.q.sg.OWN && x.q.sg.PE)) { R.unprotected++; R.ids.oblig.push(c.id); } }
      R.signN++; if (x.q.done) R.signDone++; else { R.notSigned++; R.ids.sign.push(c.id); }
      if (dec.note && dec.note.trim().length >= 12) R.why++; else { R.noWhy++; R.ids.why.push(c.id); }
      const others = Object.keys(x.q.sg).filter((k) => x.q.sg[k] && x.q.sg[k].by !== dec.by);
      if (others.length || dec.checkedBy || (dec.reviewedBy && dec.reviewedBy.length)) R.second++; else { R.noSecond++; R.ids.second.push(c.id); }
      if (d.kinds.merged > 0) R.cuts.push({ id: c.id, title: c.title, from: ms.length, to: d.remain, text: dec.text || (ms.find((m) => m.id === d.survivor) || ms[0]).text, gone: d.kinds.merged });
    } else {
      R.kinds.waiting += ms.length; R.after += ms.length; R.waitingClusters++; R.ids.cover.push(c.id);
      const res = resOf(S, c), ev = evaluate(S, c, ms, res), d = dispositionsOf(S, c, ms, res, ev, null);
      R.projected += d.remain;
    }
  });
  R.kinds.asis = R.n - inCl + peeledN; R.after += R.kinds.asis; R.projected += R.kinds.asis;
  // requirements decided on their own (see single.js): each moves out of "stays as it is" into its own destination
  rdList(S, alloc).forEach((x) => {
    const o = x.dec.outcome;
    R.kinds.asis--; R.kinds[x.kind]++; R.single[o]++;
    if (RD_REMOVES(o)) { R.after--; R.projected--; }
    if (o === 'ask') return;
    R.singleN++;
    if (RD_REMOVES(o) || x.dec.weakening) { R.looseN++; if (!(x.q.sg.OWN && x.q.sg.PE)) { R.unprotected++; R.ids.oblig.push(x.r.id); } }
    R.signN++; if (x.q.done) R.signDone++; else { R.notSigned++; R.ids.sign.push(x.r.id); }
    if (x.dec.note && x.dec.note.trim().length >= 12) R.why++; else { R.noWhy++; R.ids.why.push(x.r.id); }
    const others = Object.keys(x.q.sg).filter((k) => x.q.sg[k] && x.q.sg[k].by !== x.dec.by);
    if (others.length) R.second++; else { R.noSecond++; R.ids.second.push(x.r.id); }
  });
  const D = R.decided + R.singleN;
  const val = {
    cover: R.n ? (R.n - R.kinds.waiting) / R.n : 0,
    oblig: R.mergeN + R.looseN ? 1 - R.unprotected / (R.mergeN + R.looseN) : 1,
    sign: D ? R.signDone / R.signN : 0,
    why: D ? R.why / D : 0,
    second: D ? R.second / D : 0
  };
  const nf = (x) => x.toLocaleString('en-US');
  const detail = {
    cover: nf(R.n - R.kinds.waiting) + ' of ' + nf(R.n) + ' requirements accounted for',
    oblig: R.mergeN + R.looseN ? (R.mergeN + R.looseN - R.unprotected) + ' of ' + (R.mergeN + R.looseN) + (R.looseN ? ' merges and removals' : ' merges') + ' keep every obligation' : 'No merge recorded yet',
    sign: R.signDone + ' of ' + R.signN + ' decisions fully signed',
    why: R.why + ' of ' + D + ' decisions have a note',
    second: R.second + ' of ' + D + ' had another person’s eyes on them'
  };
  const parts = GRADE_PARTS.map((p) => ({ k: p.k, name: p.name, weight: p.weight, plain: p.plain, v: val[p.k], pts: p.weight * val[p.k], gap: p.weight * (1 - val[p.k]), detail: detail[p.k] }));
  const score = parts.reduce((s, p) => s + p.pts, 0);
  let letter = letterOf(score), capped = false;
  if (R.unprotected > 0 && GRADE_ORDER.indexOf(letter) < GRADE_ORDER.indexOf('C')) { letter = 'C'; capped = true; }
  R.parts = parts; R.score = score; R.letter = letter; R.capped = capped; R.graded = D > 0;
  R.provisional = R.clusters ? R.decided / R.clusters < 0.9 : true;
  return R;
}

/* ---------- the engineering V ----------
   The left leg is what we require, level by level. The right leg is how each level is shown to be met.
   Merging requirements changes the left leg; this section works out what that does to the right leg.
   The sample data has no level, no verification method on every requirement and no verification items, so each requirement is given
   them here from a hash of its ID (the same every run, and without touching the random numbers that built the clusters).
   A real import reads the level from a field or from the parent links, and the items from verify links (see reqin: `reqin vee`). */
const VLEVELS = [
  { k: 1, name: 'Stakeholder needs', short: 'Needs', ver: 'Validation', how: 'Shown against what the stakeholders need, in acceptance or operational use.' },
  { k: 2, name: 'System requirements', short: 'System', ver: 'System verification', how: 'Shown on the whole system.' },
  { k: 3, name: 'Subsystem requirements', short: 'Subsystem', ver: 'Subsystem verification', how: 'Shown on each subsystem, once its parts are integrated.' },
  { k: 4, name: 'Component requirements', short: 'Component', ver: 'Component verification', how: 'Shown on each component, on the bench.' }
];
const VMETHODS = ['Test', 'Analysis', 'Inspection', 'Demonstration'];
const vHash = (id, salt, mod) => parseInt(h32(id + ':' + salt).slice(0, 6), 16) % mod;
function vLevelFor(id) { const x = vHash(id, 'lvl', 100); return x < 4 ? 1 : x < 38 ? 2 : x < 88 ? 3 : 4; }
function vItemsFor(id) { const x = vHash(id, 'vi', 100); return x < 12 ? 0 : x < 55 ? 1 : x < 85 ? 2 : 3; }
const VREQ = {};
CLUSTERS.forEach((c) => {
  c.lvl = vLevelFor(c.id);
  c.members.forEach((m, i) => {
    // In a "subsumes" cluster the first wording is the general one, which sits a level above the stricter one.
    m.lvl = c.rel === 'SUBSUMES' && i === 0 ? Math.max(1, c.lvl - 1) : c.lvl;
    VREQ[m.id] = { lvl: m.lvl, vm: m.verif, vi: vItemsFor(m.id) };
  });
  c.lvls = [Math.min.apply(null, c.members.map((m) => m.lvl)), Math.max.apply(null, c.members.map((m) => m.lvl))];
  c.crossLevel = c.lvls[0] !== c.lvls[1];
});
GEN.lone.forEach((r) => { VREQ[r.id] = { lvl: vLevelFor(r.id), vm: vHash(r.id, 'vm', 100) < 14 ? '' : VERIFS[vHash(r.id, 'vk', 4)], vi: vItemsFor(r.id) }; });

/* One pass over the project: per level, what is on the left leg and what is on the right. infos come from Component.allInfos(S). */
function veeOf(S, infos) {
  const U = universe(S);
  const L = VLEVELS.map((l) => ({
    ...l, reqs: 0, clusters: 0, decided: 0, open: 0, cross: 0, mergedAway: 0, superseded: 0, dropped: 0, reworded: 0, recheck: 0, added: 0, after: 0,
    methods: { Test: 0, Analysis: 0, Inspection: 0, Demonstration: 0, none: 0 }, items: 0, traced: 0, gaps: 0, noMethod: 0, noItem: 0, repoint: 0, methodShift: 0, levelShift: 0
  }));
  U.reqs.forEach((r) => {
    const v = VREQ[r.id], l = L[v.lvl - 1];
    l.reqs++; l.items += v.vi; l.methods[v.vm || 'none']++;
    if (!v.vm) l.noMethod++;
    if (v.vi === 0) l.noItem++;
    if (v.vm && v.vi > 0) l.traced++; else l.gaps++;
  });
  let held = 0;
  infos.forEach((x) => {
    const c = x.c, l = L[c.lvls[1] - 1];
    l.clusters++;
    if (c.crossLevel) l.cross++;
    const dec = standingDec(x);
    if (x.dec && !dec) held++;
    if (!dec) { l.open++; return; }
    l.decided++;
    const ms = membersOf(S, c), d = dispositionsOf(S, c, ms, {}, {}, dec), kid = d.survivor || (d.newWording ? '' : ((ms.find((m) => d.by[m.id].kind === 'keep') || {}).id || '')), keep = kid ? VREQ[kid] : null;
    // A requirement leaves the left leg when it is merged away or marked superseded (the same rule Results uses). A new wording adds one.
    // Its verification items have to be pointed at whatever takes its place.
    ms.forEach((m) => {
      const kind = d.by[m.id].kind;
      if (kind !== 'merged' && kind !== 'superseded') return;
      const v = VREQ[m.id], lv = L[v.lvl - 1];
      if (kind === 'merged') lv.mergedAway++; else lv.superseded++;
      lv.repoint += v.vi;
      if (keep && v.vm && keep.vm && v.vm !== keep.vm) lv.methodShift++;
      if (keep && keep.lvl !== v.lvl) lv.levelShift += v.vi;
    });
    if (d.newWording) L[c.lvls[0] - 1].added++;
  });
  // requirements decided on their own: dropping one, or calling it not a requirement, takes it off the left leg and leaves its verification items to re-point;
  // new wording leaves the count alone, but its items should be read again against the new text
  rdList(S, '').forEach((x) => {
    const v = VREQ[x.r.id], lv = L[v.lvl - 1], o = x.dec.outcome;
    if (RD_REMOVES(o)) { lv.dropped++; lv.repoint += v.vi; }
    if (o === 'reword') { lv.reworded++; lv.recheck += v.vi; }
  });
  const sum = (f) => L.reduce((s, l) => s + f(l), 0);
  L.forEach((l) => {
    l.after = l.reqs - l.mergedAway - l.superseded - l.dropped + l.added; l.gone = l.reqs - l.after;
    l.decShare = l.clusters ? l.decided / l.clusters : 1;
    l.traceShare = l.reqs ? l.traced / l.reqs : 1;
    l.state = l.open > 0 ? 'open' : l.repoint > 0 || l.gaps > 0 ? 'attn' : 'ok';
  });
  return {
    levels: L, reqs: sum((l) => l.reqs), after: sum((l) => l.after), clusters: sum((l) => l.clusters), decided: sum((l) => l.decided), open: sum((l) => l.open),
    gaps: sum((l) => l.gaps), noMethod: sum((l) => l.noMethod), noItem: sum((l) => l.noItem), items: sum((l) => l.items), repoint: sum((l) => l.repoint),
    methodShift: sum((l) => l.methodShift), levelShift: sum((l) => l.levelShift), mergedAway: sum((l) => l.mergedAway), superseded: sum((l) => l.superseded), dropped: sum((l) => l.dropped), reworded: sum((l) => l.reworded), recheck: sum((l) => l.recheck), added: sum((l) => l.added),
    cross: sum((l) => l.cross), traced: sum((l) => l.traced), held
  };
}
/* The small V: four circles down the left leg (how much is decided), four squares up the right leg (how much is traced), a vertex for the build.
   hi lists the levels to ring (the cluster you are looking at). Colour is never the only carrier: shape tells the legs apart, and the numbers sit beside it. */
function veeGlyph(V, hi, nums) {
  hi = hi || [];
  const at = (k) => ({ lx: 8 + 9 * (k - 1), rx: 80 - 9 * (k - 1), y: 6 + 8 * (k - 1) });
  const box = (cx, cy, size, fill, stroke, sw, round, ink) => 'position:absolute;box-sizing:border-box;left:' + (cx - size / 2) + 'px;top:' + (cy - size / 2) + 'px;width:' + size + 'px;height:' + size + 'px;border-radius:' + (round ? '50%' : '1px') + ';background:' + fill + ';border:' + sw + 'px solid ' + stroke + ';display:flex;align-items:center;justify-content:center;font:700 5.4px/1 var(--sans);color:' + ink;
  const left = V.levels.map((l) => {
    const p = at(l.k), on = hi.indexOf(l.k) >= 0, s = l.decShare;
    return { n: nums ? String(l.k) : '', style: box(p.lx, p.y, on ? 10 : nums ? 9.6 : 8.4, s >= 0.9 ? '#1C5CAB' : s >= 0.5 ? '#7FB0EE' : '#FFFFFF', on ? '#10202E' : '#1C5CAB', on ? 2.4 : 1.5, true, s >= 0.9 ? '#FFFFFF' : '#10202E') };
  });
  const right = V.levels.map((l) => {
    const p = at(l.k), on = hi.indexOf(l.k) >= 0, s = l.traceShare;
    return { n: nums ? String(l.k) : '', style: box(p.rx, p.y, on ? 9.4 : nums ? 9 : 7.6, s >= 0.9 ? '#1B6B3A' : s >= 0.75 ? '#8FCBA6' : '#FFD9A8', on ? '#10202E' : s >= 0.75 ? '#1B6B3A' : '#B35A00', on ? 2.4 : 1.5, false, s >= 0.9 ? '#FFFFFF' : '#10202E') };
  });
  const aria = 'The V. Left leg, decided clusters: ' + V.levels.map((l) => l.short + ' ' + l.decided + ' of ' + l.clusters).join(', ') +
    '. Right leg, requirements with a verification method and item: ' + V.levels.map((l) => l.short + ' ' + l.traced + ' of ' + l.reqs).join(', ') + '.';
  return { aria, left, right };
}
