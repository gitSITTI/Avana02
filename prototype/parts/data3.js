/* ---------- generator: 243 more clusters, then lone requirements up to the project total ---------- */
const TOTAL_REQS = 1248;
const NUMW = { 2: 'two', 3: 'three', 4: 'four', 5: 'five', 6: 'six', 7: 'seven', 8: 'eight' };
function genAll() {
  const R = rng(20261010);
  const ri = (a, b) => a + Math.floor(R() * (b - a + 1));
  const pk = (a) => a[Math.floor(R() * a.length)];
  const shuffle = (a) => { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); const t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
  const wpk = (items) => { const tot = items.reduce((s, x) => s + x.w, 0); let r = R() * tot; for (const x of items) { r -= x.w; if (r <= 0) return x; } return items[items.length - 1]; };
  const jit = (a, b) => +(a + (b - a) * R()).toFixed(2);
  const used = new Set(HAND_IDS), counters = {};
  const newId = (al) => { let n = counters[al.pre] || ri(5, 40); let id; do { n += ri(1, 5); id = 'REQ-' + al.pre + '-' + String(n).padStart(4, '0'); } while (used.has(id)); counters[al.pre] = n; used.add(id); return id; };
  const kinds = [];
  const add = (k, n) => { for (let i = 0; i < n; i++) kinds.push(k); };
  add('equiv', 110); add('varV', 72); add('modal', 14); add('subs', 17); add('confN', 8); add('confV', 10); add('cond', 12);
  shuffle(kinds);
  const OVER = { 'CL-117': 13, 'CL-201': 14 };
  const BASELINED = { 'CL-023': 'CR-2041', 'CL-088': 'CR-2057', 'CL-140': 'CR-2063', 'CL-176': 'CR-2078', 'CL-230': 'CR-2090' };
  const out = [];
  let ki = 0;
  for (let n = 8; n <= 252; n++) {
    const id = 'CL-' + String(n).padStart(3, '0');
    if (id === 'CL-042' || id === 'CL-050') continue;
    let kind = OVER[id] ? 'varV' : kinds[ki++];
    if (BASELINED[id] && (kind === 'confN' || kind === 'confV')) kind = 'equiv';
    let al = wpk(ALLOCS);
    if (kind === 'confV') al = ALLOC_BY['Power Subsystem'];
    const S = al.sub;
    const otherOwner = () => pk(ALLOCS.filter((a) => a.k !== al.k)).owner;
    const baseV = pk(VERIFS);
    const mkMember = (text, extra, crossP) => {
      const o = R() < crossP ? otherOwner() : al.owner;
      const vf = R() < 0.12 ? pk(VERIFS) : baseV;
      return mem(newId(R() < 0.8 ? al : pk(ALLOCS)), o, al.k, vf, 'Pre-baseline', text, extra);
    };
    const c = { id, alloc: al.k, sub: S, kind };
    if (kind === 'equiv' || kind === 'varV') {
      const fam = pk(FAMS), thing = pk(fam.things);
      const size = OVER[id] || (kind === 'equiv' ? (R() < 0.65 ? 2 : R() < 0.8 ? 3 : 4) : [3, 3, 3, 4, 4, 5, 5, 6, 7, 8][ri(0, 9)]);
      let vals;
      if (kind === 'equiv') { const v = pk(fam.vals); vals = new Array(size).fill(v); }
      else {
        const pool = shuffle(fam.vals.slice()).slice(0, Math.min(fam.vals.length, ri(3, 5)));
        vals = []; for (let i = 0; i < size; i++) vals.push(i < pool.length ? pool[i] : pk(pool));
        shuffle(vals);
      }
      const s0 = ri(0, 2), crossP = kind === 'equiv' ? 0.06 : 0.3;
      c.members = vals.map((v, i) => mkMember(fam.mk(S, v, s0 + i, thing, fam.time ? pk([0, 0, 1, 2]) : 0), { v }, crossP));
      if (kind === 'varV' && size >= 4 && R() < 0.3) {
        const last = c.members[c.members.length - 1], cd = pk(['on the ground', 'in maintenance mode', 'during start-up']);
        last.text = last.text.replace(/\.$/, '') + ' while ' + cd + '.'; last.cond = cd; last.rankable = false;
      }
      Object.assign(c, { famKey: fam.k, dir: fam.dir, time: !!fam.time, unit: fam.time ? 'ms' : fam.unit });
      const th = { ret: cap(thing) + ' retention', rate: cap(thing) + ' update rate', resp: cap(thing) + ' response time', hb: cap(thing) + ' interval' }[fam.k] || fam.name;
      c.param = th;
      const rk = c.members.filter((x) => x.rankable);
      if (kind === 'equiv') c.title = th + ', ' + NUMW[size] + ' wordings';
      else {
        const dv = []; rk.forEach((x) => { if (dv.indexOf(x.v) < 0) dv.push(x.v); });
        dv.sort((a, b) => a - b);
        c.title = th + ': ' + (dv.length > 3 ? dv.slice(0, 3).map((x) => fmtVal(c, x)).join(', ') + ' or more' : joinOr(dv.map((x) => fmtVal(c, x)))) + '?';
      }
      const best = c.dir === 'lower' ? Math.min.apply(null, rk.map((x) => x.v)) : Math.max.apply(null, rk.map((x) => x.v));
      c.aiDraft = fam.mk(S, best, 0, thing, 0);
    } else if (kind === 'modal') {
      const thing = pk(MODAL_THINGS), size = R() < 0.7 ? 2 : 3;
      const mods = ['shall', 'should', 'shall'].slice(0, size);
      c.members = mods.map((md) => mkMember(`The ${S} ${md} ${thing}.`, {}, 0.1));
      Object.assign(c, { famKey: 'modal', dir: 'modal', unit: '', param: 'Obligation level', title: cap(thing.split(' ').slice(0, 4).join(' ')) + ': shall or should?', aiDraft: `The ${S} shall ${thing}.` });
    } else if (kind === 'subs') {
      const thing = pk(SUBS_THINGS), ex = pk(SUBS_EXTRA);
      c.members = [mkMember(`The system shall log ${thing}.`, { xr: 0 }, 0.05), mkMember(`The system shall log ${thing} ${ex}.`, { xr: 1 + ex.split(' and ').length }, 0.05)];
      Object.assign(c, { famKey: 'clauses', dir: 'more', unit: 'clauses', param: 'Logged content', title: cap(thing) + ' logging: plain or with detail', aiDraft: `The system shall log ${thing} ${ex}.` });
    } else if (kind === 'confN') {
      const thing = pk(NEG_THINGS);
      c.members = [mkMember(`The ${S} shall ${thing}.`, {}, 0.05), mkMember(`The ${S} shall not ${thing}.`, {}, 0.05)];
      Object.assign(c, { famKey: 'neg', dir: 'none', unit: '', param: cap(thing.split(' ').slice(0, 3).join(' ')), title: cap(thing.split(' ').slice(0, 3).join(' ')) + ': required or prohibited?', aiDraft: '' });
    } else if (kind === 'confV') {
      const pair = shuffle([28, 115, 270]).slice(0, 2);
      c.members = pair.map((v) => mkMember(`The ${S} shall provide a ${v} VDC nominal bus voltage.`, { v }, 0.5));
      Object.assign(c, { famKey: 'bus', dir: 'none', unit: 'VDC', param: 'Nominal bus voltage', title: 'Bus voltage: ' + pair[0] + ' VDC or ' + pair[1] + ' VDC?', aiDraft: '' });
    } else {
      const thing = pk(COND_THINGS), cds = shuffle(CONDS.slice()).slice(0, 3);
      c.members = cds.map((cd) => mkMember(`The ${S} shall ${thing} ${cd}.`, { cond: cd, rankable: false }, 0.1));
      Object.assign(c, { famKey: 'cond', dir: 'none', unit: '', param: cap(thing), title: cap(thing) + ': which condition applies?', aiDraft: '' });
    }
    if (BASELINED[id]) { c.members[0].base = 'Baselined (BL-2)'; c.cr = BASELINED[id]; }
    // lane, relationship, scores, AI, guards
    const crossOwner = new Set(c.members.map((x) => x.owner)).size > 1;
    const rkv = c.members.filter((x) => x.v !== null && x.rankable).map((x) => x.v);
    const dv = rkv.filter((x, i) => rkv.indexOf(x) === i);
    const q = (x) => { const qs = quantities(x.text); return qs.length ? qs[0].raw : ''; };
    const firstLast = () => [['M1', q(c.members[0])], ['M' + c.members.length, q(c.members[c.members.length - 1])]].filter((x) => x[1]);
    const votes = () => (R() < 0.75 ? '3 of 3 runs agree' : '2 of 3 runs agree');
    if (kind === 'equiv') {
      c.lane = crossOwner ? 'B' : 'A'; c.rel = 'EQUIVALENT';
      c.m = { fuzzy: jit(0.5, 0.88), tfidf: jit(0.45, 0.78), embed: jit(0.9, 0.97), cross: jit(0.87, 0.96), eAB: jit(0.93, 0.98), eBA: jit(0.92, 0.97), contra: jit(0.01, 0.04), p: jit(crossOwner ? 0.82 : 0.9, 0.98) };
      c.mNote = 'The wording differs, but meaning and values match in every pair.';
      if (R() < 0.8) c.ai = { mode: 'draft', proposal: c.aiDraft, verdict: '', conf: 0, votes: '', why: 'The AI only drafted merged wording here. The mechanical methods already agree.', quotes: [] };
      else c.ai = { mode: 'none', proposal: '', verdict: '', conf: 0, votes: '', why: 'No AI needed. The combined score is high and every guard passes.', quotes: [] };
      c.guards = crossOwner ? 'ppppppppwp' : 'pppppppppp'; c.gNotes = crossOwner ? { 8: 'Owners differ; the merged wording needs both to confirm' } : {};
      c.actions = [['merge', 'Merge into one'], ['reject', 'Not a duplicate']];
    } else if (kind === 'varV') {
      c.lane = 'B'; c.rel = 'VARIANT';
      c.m = { fuzzy: jit(0.8, 0.97), tfidf: jit(0.7, 0.9), embed: jit(0.94, 0.98), cross: jit(0.86, 0.95), eAB: jit(0.72, 0.86), eBA: jit(0.7, 0.84), contra: jit(0.03, 0.09), p: jit(0.5, 0.76) };
      c.mNote = 'Every similarity score is high, yet the values differ. Similarity cannot see this; the number guard can.';
      c.ai = { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: ri(72, 92), votes: votes(), why: 'Same subject and action. The values differ (' + dv.slice(0, 4).map((x) => fmtVal(c, x)).join(', ') + (dv.length > 4 ? ', …' : '') + ')' + (crossOwner ? ' and the owners differ' : '') + ', so no single value is safe without a decision.', quotes: firstLast(), action: crossOwner ? 'Ask the owners which value applies, or keep the strictest if they agree.' : 'Keep the strictest value if the owner agrees.' };
      c.guards = 'ppfppppppp'; c.gNotes = { 2: dv.slice(0, 4).map((x) => fmtVal(c, x)).join(', ') + ' all appear' };
      c.actions = [['merge', 'Merge into one'], ['link', 'Keep both and link'], ['escalate', 'Ask the owners'], ['reject', 'Reject suggestion']];
    } else if (kind === 'modal') {
      c.lane = 'B'; c.rel = 'VARIANT';
      c.m = { fuzzy: jit(0.94, 0.98), tfidf: jit(0.84, 0.9), embed: jit(0.96, 0.99), cross: jit(0.92, 0.96), eAB: jit(0.86, 0.92), eBA: jit(0.84, 0.9), contra: jit(0.02, 0.05), p: jit(0.55, 0.7) };
      c.mNote = 'Only one word differs, and it changes the obligation: "shall" is mandatory, "should" is a goal.';
      c.ai = { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: ri(74, 88), votes: votes(), why: 'Only the modal verb differs. They are not the same obligation.', quotes: [['M1', 'shall ' + c.members[0].text.split(' shall ')[1].split(' ').slice(0, 1).join(' ')], ['M2', 'should ' + c.members[1].text.split(' should ')[1].split(' ').slice(0, 1).join(' ')]], action: 'Keep both until the owner decides whether this is mandatory.' };
      c.guards = 'ppppfppppp'; c.gNotes = { 4: '"shall" in M1, "should" in M2' };
      c.actions = [['merge', 'Merge into one'], ['link', 'Keep both and link'], ['escalate', 'Ask the owner'], ['reject', 'Reject suggestion']];
    } else if (kind === 'subs') {
      c.lane = 'B'; c.rel = 'SUBSUMES';
      c.m = { fuzzy: jit(0.6, 0.7), tfidf: jit(0.55, 0.65), embed: jit(0.82, 0.9), cross: jit(0.76, 0.84), eAB: jit(0.08, 0.2), eBA: jit(0.9, 0.96), contra: jit(0.01, 0.04), p: jit(0.18, 0.3) };
      c.mNote = 'M2 entails M1 but M1 does not entail M2: M2 is the stricter requirement.';
      c.ai = { mode: 'judge', proposal: 'Keep M2. Link M1 as its parent.', verdict: 'SUBSUMES (M2 stricter)', conf: ri(76, 88), votes: votes(), why: 'M2 contains everything M1 requires and adds more detail.', quotes: [['M2', c.members[1].text.split(' log ')[1].split(' ').slice(2).join(' ').replace(/\.$/, '')]], action: 'Link M1 as parent of M2; do not delete M1.' };
      c.guards = 'ppppppppwp'; c.gNotes = { 8: 'Merged wording would add detail that M1 does not contain' };
      c.actions = [['link', 'Link parent and child'], ['supersede', 'Supersede the older'], ['reject', 'Reject suggestion']];
    } else if (kind === 'confN') {
      c.lane = 'C'; c.rel = 'CONFLICT';
      c.m = { fuzzy: jit(0.94, 0.99), tfidf: jit(0.86, 0.92), embed: jit(0.94, 0.98), cross: jit(0.5, 0.65), eAB: jit(0.01, 0.05), eBA: jit(0.01, 0.05), contra: jit(0.92, 0.98), p: jit(0.03, 0.09) };
      c.mNote = 'A keyword "token set" score would call these identical. The word "not" is invisible to it.';
      c.ai = { mode: 'none', proposal: '', verdict: '', conf: 0, votes: '', why: 'No AI needed. The NLI contradiction score and the negation guard already decide this.', quotes: [] };
      c.guards = 'pppppfpppf'; c.gNotes = { 5: '"not" appears in M2 only', 9: 'No wording satisfies both sources' };
      c.actions = [['escalate', 'Open conflict record'], ['reject', 'Not a conflict']];
    } else if (kind === 'confV') {
      c.lane = 'C'; c.rel = 'CONFLICT';
      c.m = { fuzzy: jit(0.9, 0.95), tfidf: jit(0.8, 0.88), embed: jit(0.93, 0.97), cross: jit(0.65, 0.75), eAB: jit(0.05, 0.12), eBA: jit(0.05, 0.12), contra: jit(0.84, 0.92), p: jit(0.08, 0.15) };
      c.mNote = 'High text similarity, but the NLI model sees a contradiction.';
      c.ai = { mode: 'judge', proposal: '', verdict: 'CONFLICT', conf: ri(86, 95), votes: votes(), why: 'One bus cannot have two different nominal voltages. This needs a decision from the owners, not a merge.', quotes: firstLast(), action: 'Escalate to both owners.' };
      c.guards = 'ppfppppppf'; c.gNotes = { 2: c.members[0].v + ' VDC ≠ ' + c.members[1].v + ' VDC', 9: 'Any merged wording would contradict one source' };
      c.actions = [['escalate', 'Escalate to owners'], ['reject', 'Not a conflict']];
    } else {
      c.lane = 'B'; c.rel = 'VARIANT';
      c.m = { fuzzy: jit(0.86, 0.94), tfidf: jit(0.78, 0.86), embed: jit(0.92, 0.97), cross: jit(0.82, 0.9), eAB: jit(0.55, 0.7), eBA: jit(0.52, 0.68), contra: jit(0.04, 0.1), p: jit(0.4, 0.6) };
      c.mNote = 'The wording is nearly identical, but each member applies under a different condition.';
      c.ai = { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: ri(70, 84), votes: votes(), why: 'Same action under different conditions. They are three requirements, not one. The AI will not merge conditions.', quotes: c.members.slice(0, 2).map((x, i) => ['M' + (i + 1), x.cond]), action: 'Keep separate and link, or write one wording that names every condition.' };
      c.guards = 'pppppp' + 'w' + 'ppp'; c.gNotes = { 6: 'Conditions differ: ' + c.members.map((x) => x.cond).join('; ') };
      c.actions = [['merge', 'Merge into one'], ['link', 'Keep separate and link'], ['escalate', 'Ask the owner'], ['reject', 'Reject suggestion']];
    }
    out.push(c);
  }
  // lone requirements up to the project total
  const lone = [];
  const nMembers = out.reduce((s, c) => s + c.members.length, 0) + HAND.reduce((s, c) => s + c.members.length, 0);
  for (let i = nMembers; i < TOTAL_REQS; i++) {
    const al = wpk(ALLOCS), fam = pk(FAMS), thing = pk(fam.things);
    lone.push({ id: newId(al), alloc: al.k, owner: al.owner, text: fam.mk(al.sub, pk(fam.vals), ri(0, 2), thing, pk([0, 1, 2])), cid: null });
  }
  return { out, lone };
}

function finishCluster(c) {
  c.crossOwner = new Set(c.members.map((m) => m.owner)).size > 1;
  c.baselined = c.members.some((m) => /^Baselined/.test(m.base));
  c.p = c.m.p;
  c.n = c.members.length;
  c.ai.quotes = c.ai.quotes.map(([w, t]) => [w === 'A' ? 'M1' : w === 'B' ? 'M2' : w, t]);
  if (!c.cr && c.baselined) c.cr = 'CR-2000';
  return c;
}
const GEN = genAll();
const CLUSTERS = HAND.concat(GEN.out).map(finishCluster).sort((a, b) => (a.id < b.id ? -1 : 1));
const CL_BY = Object.fromEntries(CLUSTERS.map((c) => [c.id, c]));
const ORDER = CLUSTERS.slice().sort((a, b) => a.lane.localeCompare(b.lane) || b.p - a.p || (a.id < b.id ? -1 : 1));
const REQS = (() => {
  const list = [];
  CLUSTERS.forEach((c) => c.members.forEach((m) => list.push({ id: m.id, alloc: c.alloc, owner: m.owner, text: m.text, cid: c.id })));
  GEN.lone.forEach((r) => list.push(r));
  list.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
  return list;
})();
const REQ_BY = Object.fromEntries(REQS.map((r) => [r.id, r]));
