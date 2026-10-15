/* ---------- the gold set: pairs people have labelled, and the precision and recall that make real ----------
   A gold set is a list of requirement pairs that people have looked at and labelled: the same requirement, same topic with a different value,
   one contains the other, they contradict, or different things. With it, "precision" and "recall" stop being placeholders and become counts.

   WHICH PAIRS GET LABELLED. Not a plain random sample: nearly every random pair is unrelated, so a plain sample would hold almost no duplicates.
   The sample is drawn on purpose from four groups and every group is weighted by how many pairs it stands for:
     A   pairs the app put in the same cluster (its suggestions)
     B1  pairs in the same allocation that read alike (text match or keyword overlap of 0.6 or more) but are NOT in the same cluster: the near misses
     B2  the rest of the pairs inside one allocation
     C   pairs from different allocations (the app never compares these)
   Each group is a simple random sample, so stopping at any point still gives a fair sample of it. Every fifth pair is offered to a second person
   (nobody sees another person's label), which is what makes "how much do two people agree" measurable.

   WHAT IS COUNTED. A pair is "related" when its label is any of the four relations, "not related" when it is "Different things". "Cannot tell"
   and pairs two people disagree about are left out of the numbers until someone settles them.
     Precision of a method = of the pairs it flagged, the share that are related. Recall = of the related pairs among those clustered or reading alike
     (groups A and B1), the share it flagged. Both are estimated group by group and scaled up to the pairs each group stands for.
   RANGES. Each group's share is given a Wilson 95 percent interval, and the ends are combined so the range is the lowest and highest value those
   intervals allow. It is a range to read, not a point to quote: with the demonstration world fully labelled it held the true value in 96 to 100 of
   100 random samples of the planned size (verify.js), so treat it as about 95 percent and no better.
   Groups B2 and C are not in the recall: they are reported on their own as "how many related pairs could be hiding there".

   Everything here is pure: the same labels always give the same numbers. The sample labels that can be loaded for the demonstration are made up
   by goldTruth() and goldSampleLabels() below; they are not used for anything else. */
const GOLD_REL = [
  { k: 'equiv', name: 'Same requirement', help: 'They say the same thing with the same values. One of them is redundant.', ai: 'EQUIVALENT', rel: true },
  { k: 'variant', name: 'Same topic, different value', help: 'They set a different number, limit or condition for the same thing.', ai: 'VARIANT', rel: true },
  { k: 'contains', name: 'One contains the other', help: 'One says everything the other says, and more.', ai: 'SUBSUMES', rel: true },
  { k: 'conflict', name: 'They contradict', help: 'Both cannot be true at once.', ai: 'CONFLICT', rel: true },
  { k: 'none', name: 'Different things', help: 'Nothing to merge, link or compare.', ai: '', rel: false },
  { k: 'unsure', name: 'Cannot tell', help: 'You need the owner or more context. Left out of the numbers.', ai: '', rel: false }
];
const GOLD_BY = Object.fromEntries(GOLD_REL.map((r) => [r.k, r]));
const GOLD_SIZE = { A: 50, B1: 60, B2: 25, C: 25 };      // pairs in the sample, per group
const GOLD_GROUPS = ['A', 'B1', 'B2', 'C'];
const GOLD_GROUP_NAME = { A: 'Put in a cluster by the app', B1: 'Read alike, not clustered', B2: 'Same allocation, not alike', C: 'Different allocations' };
const GOLD_CUTS = [0.6, 0.7, 0.8, 0.9];                   // cut-offs a person can pick for the score-only methods (never below the "reads alike" band)
const GOLD_BAND = 0.6;                                    // a pair "reads alike" at or above this text match or keyword overlap
const GOLD_SEED = 20261014;
const GOLD_DOUBLE = 5;                                    // one pair in five is offered to a second person
const GOLD_ENOUGH = 10;                                   // labelled pairs a group needs before its numbers are shown without a warning

function goldKey(a, b) { return a.id < b.id ? a.id + '|' + b.id : b.id + '|' + a.id; }
function goldWilson(k, n, z) {
  z = z || 1.96;
  if (!n) return [0, 1];
  const p = k / n, z2 = z * z, d = 1 + z2 / n, c = p + z2 / (2 * n), w = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n));
  return [Math.max(0, (c - w) / d), Math.min(1, (c + w) / d)];
}

/* ----- the two scores, worked out the same way for every pair ----- */
let GOLD_MODEL = null;
function goldModel() {
  if (GOLD_MODEL) return GOLD_MODEL;
  const N = REQS.length, vocab = new Map(), df = new Map();
  const ids = REQS.map((r) => r.text.split(/\s+/).filter(Boolean).map((w) => { const t = normTok(w); let i = vocab.get(t); if (i === undefined) { i = vocab.size; vocab.set(t, i); } return i; }));
  ids.forEach((a) => new Set(a).forEach((w) => df.set(w, (df.get(w) || 0) + 1)));
  const vec = ids.map((a) => {
    const tf = new Map(); a.forEach((w) => tf.set(w, (tf.get(w) || 0) + 1));
    const m = new Map(); let nn = 0;
    tf.forEach((c, w) => { const x = c * (Math.log((N + 1) / (df.get(w) + 1)) + 1); m.set(w, x); nn += x * x; });
    nn = Math.sqrt(nn) || 1; m.forEach((x, w) => m.set(w, x / nn));
    return m;
  });
  const idx = {}; REQS.forEach((r, i) => { idx[r.id] = i; });
  GOLD_MODEL = { ids, vec, idx, V: vocab.size, sorted: ids.map((a) => Int32Array.from(a).sort()) };
  return GOLD_MODEL;
}
/* text match: 1 minus the word-by-word edit distance divided by the longer wording (1 = the same words in the same order) */
function goldTextScore(i, j) {
  const A = goldModel().ids[i], B = goldModel().ids[j];
  let n = A.length, m = B.length;
  if (!n && !m) return 1;
  const top = Math.max(n, m);
  // words that start or end both wordings the same way cost nothing, so only the part in the middle is worked out (the distance is unchanged)
  let a0 = 0, b0 = 0;
  while (n > 0 && m > 0 && A[a0] === B[b0]) { a0++; b0++; n--; m--; }
  while (n > 0 && m > 0 && A[a0 + n - 1] === B[b0 + m - 1]) { n--; m--; }
  if (!n || !m) return 1 - (n + m) / top;
  if (m > n) return goldTextScoreMid(B, b0, m, A, a0, n, top);
  return goldTextScoreMid(A, a0, n, B, b0, m, top);
}
/* the edit distance of the middle parts, with the longer one (n words from a0) down the side and the shorter one (m words from b0) along the top */
function goldTextScoreMid(A, a0, n, B, b0, m, top) {
  let prev = new Int32Array(m + 1), cur = new Int32Array(m + 1);
  for (let q = 0; q <= m; q++) prev[q] = q;
  for (let a = 1; a <= n; a++) {
    cur[0] = a;
    const x = A[a0 + a - 1];
    for (let b = 1; b <= m; b++) {
      let v = prev[b - 1] + (x === B[b0 + b - 1] ? 0 : 1);
      const u = prev[b] + 1, w = cur[b - 1] + 1;
      if (u < v) v = u;
      if (w < v) v = w;
      cur[b] = v;
    }
    const t = prev; prev = cur; cur = t;
  }
  return 1 - prev[m] / top;
}
/* keyword overlap: cosine of the TF-IDF vectors of the two wordings (words that few requirements use count for more) */
function goldKeywordScore(i, j) {
  const a = goldModel().vec[i], b = goldModel().vec[j];
  const s = a.size <= b.size ? a : b, l = a.size <= b.size ? b : a;
  let x = 0; s.forEach((w, k) => { const y = l.get(k); if (y) x += w * y; });
  return Math.min(1, x);
}

/* ----- the population: how many pairs each group stands for -----
   Every pair inside one allocation has one fixed place in a single order: allocation by allocation, then the first requirement, then the second.
   The groups are worked out without ever listing all the pairs, so the work stays small when a project has tens of thousands of requirements:
     A   comes from the clusters (the pairs inside each one)
     B1  is found with an index over the rare words, then confirmed with the exact scores. Any pair at 0.6 or more must share some of its rarest words
         (text match) or some heavy words (keyword overlap), so nothing that reads alike is missed (verify.js checks this against every pair)
     B2  is what is left in each allocation: counted by subtraction and drawn from by position, never listed
   The numbers are the same as comparing every pair, only reached without doing so. */
let GOLD_POP = null;
/* pairs of positions (p before q) in one allocation whose word-by-word text match can reach the band: the length test, then a prefix filter. Two wordings
   with a match of 0.6 or more line up at least 0.6 of their longer wording, so they share that many words; the rarest 40 percent of a wording plus one
   word must meet one of the other's. Candidates only: the caller checks the real score. */
function goldNearText(L, emit) {
  const M = goldModel(), V = M.V, s = L.length, el = new Array(s), freq = new Map();
  for (let p = 0; p < s; p++) {
    const ids = M.ids[L[p]], nth = new Map(), e = new Array(ids.length);
    for (let q = 0; q < ids.length; q++) { const o = nth.get(ids[q]) || 0; nth.set(ids[q], o + 1); e[q] = ids[q] + o * V; }
    el[p] = e;
    for (let q = 0; q < e.length; q++) freq.set(e[q], (freq.get(e[q]) || 0) + 1);
  }
  const post = new Map(), stamp = new Int32Array(s).fill(-1), blank = [];
  for (let p = 0; p < s; p++) {
    const e = el[p], len = e.length;
    if (!len) { blank.forEach((q) => emit(q, p)); blank.push(p); continue; }
    e.sort((u, v) => freq.get(u) - freq.get(v) || u - v);
    const pre = len - Math.ceil(GOLD_BAND * len - 1e-9) + 1;
    for (let q = 0; q < pre; q++) {
      const lst = post.get(e[q]);
      if (!lst) continue;
      for (let z = 0; z < lst.length; z++) {
        const o = lst[z];
        if (stamp[o] === p) continue;
        stamp[o] = p;
        const lo = el[o].length;
        if (Math.min(len, lo) < GOLD_BAND * Math.max(len, lo) - 1e-9) continue;
        emit(o, p);
      }
    }
    for (let q = 0; q < pre; q++) { let lst = post.get(e[q]); if (!lst) post.set(e[q], lst = []); lst.push(p); }
  }
}
/* the same for keyword overlap: a requirement skips the words that cannot carry a score of 0.6 on their own (even if the other had the most weight anyone
   gives them), and is indexed by the rest; every pair at 0.6 or more shares at least one indexed word of the earlier one. */
function goldNearKw(L, emit) {
  const M = goldModel(), s = L.length, th = GOLD_BAND - 1e-9, maxw = new Map(), df = new Map();
  for (let p = 0; p < s; p++) M.vec[L[p]].forEach((w, t) => { if (w > (maxw.get(t) || 0)) maxw.set(t, w); df.set(t, (df.get(t) || 0) + 1); });
  const post = new Map(), stamp = new Int32Array(s).fill(-1);
  for (let p = 0; p < s; p++) {
    const f = Array.from(M.vec[L[p]]);
    f.sort((a, b) => df.get(b[0]) - df.get(a[0]) || a[0] - b[0]);
    for (let x = 0; x < f.length; x++) {
      const lst = post.get(f[x][0]);
      if (!lst) continue;
      for (let z = 0; z < lst.length; z++) { const o = lst[z]; if (stamp[o] !== p) { stamp[o] = p; emit(o, p); } }
    }
    let b = 0, q = 0;
    while (q < f.length && b + f[q][1] * maxw.get(f[q][0]) < th) { b += f[q][1] * maxw.get(f[q][0]); q++; }
    for (; q < f.length; q++) { let lst = post.get(f[q][0]); if (!lst) post.set(f[q][0], lst = []); lst.push(p); }
  }
}
/* can two wordings reach a text match of the band? They must line up at least that share of the longer one, so they must have that many words in common */
function goldCanText(M, i, j) {
  const A = M.sorted[i], B = M.sorted[j], n = A.length, m = B.length;
  if (Math.min(n, m) < GOLD_BAND * Math.max(n, m) - 1e-9) return false;
  const need = Math.ceil(GOLD_BAND * Math.max(n, m) - 1e-9);
  let x = 0, y = 0, same = 0;
  while (x < n && y < m) {
    if (A[x] === B[y]) { same++; x++; y++; if (same >= need) return true; }
    else if (A[x] < B[y]) x++; else y++;
  }
  return same >= need;
}
function goldPop() {
  if (GOLD_POP) return GOLD_POP;
  const n = REQS.length, byAl = {}, M = goldModel();
  REQS.forEach((r, i) => { (byAl[r.alloc] = byAl[r.alloc] || []).push(i); });
  const als = Object.keys(byAl).map((k) => byAl[k]), base = [];
  let nSame = 0;
  als.forEach((L) => { base.push(nSame); nSame += L.length * (L.length - 1) / 2; });
  const start = (s, x) => x * (2 * s - x - 1) / 2;
  const rank = (a, x, y) => base[a] + start(als[a].length, x) + (y - x - 1);
  const pairOf = (r) => {
    let lo = 0, hi = als.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (base[mid] <= r) lo = mid; else hi = mid - 1; }
    const L = als[lo], s = L.length, q = r - base[lo];
    let x = Math.max(0, Math.floor(((2 * s - 1) - Math.sqrt(Math.max(0, (2 * s - 1) * (2 * s - 1) - 8 * q))) / 2));
    while (x > 0 && start(s, x) > q) x--;
    while (x < s - 2 && start(s, x + 1) <= q) x++;
    return [L[x], L[q - start(s, x) + x + 1]];
  };
  const zero = () => GOLD_CUTS.map(() => 0);
  const cnt = { A: { text: zero(), kw: zero() }, B1: { text: zero(), kw: zero() } };
  const tally = (h, t, k, times) => GOLD_CUTS.forEach((c, q) => { if (t >= c) cnt[h].text[q] += times; if (k >= c) cnt[h].kw[q] += times; });
  const sameCl = (i, j) => !!REQS[i].cid && REQS[i].cid === REQS[j].cid;
  const grow = () => { let buf = new Float64Array(1024), len = 0; return { push: (v) => { if (len === buf.length) { const b = new Float64Array(len * 2); b.set(buf); buf = b; } buf[len++] = v; }, done: () => buf.slice(0, len) }; };
  // A: the pairs inside each cluster
  const rA = grow();
  als.forEach((L, a) => {
    const by = new Map();
    L.forEach((i, x) => { const c = REQS[i].cid; if (c) { let g = by.get(c); if (!g) by.set(c, g = []); g.push(x); } });
    by.forEach((g) => { for (let u = 0; u < g.length; u++) for (let v = u + 1; v < g.length; v++) { rA.push(rank(a, g[u], g[v])); tally('A', goldTextScore(L[g[u]], L[g[v]]), goldKeywordScore(L[g[u]], L[g[v]]), 1); } });
  });
  // B1: wordings are compared once per different text (the same words in two requirements score the same), candidates come from the two indexes,
  // and the exact scores confirm them; then every pair of requirements behind the two texts is counted
  const rB = grow();
  als.forEach((L, a) => {
    const s = L.length;
    if (s < 2) return;
    const grp = new Map();
    L.forEach((i, x) => { const t = REQS[i].text; let g = grp.get(t); if (!g) grp.set(t, g = []); g.push(x); });
    const pos = Array.from(grp.values()), U = pos.length, rep = pos.map((g) => L[g[0]]);
    const both = (g, h, t, k) => {        // every pair between two texts (or inside one) that is not a cluster pair
      for (let u = 0; u < g.length; u++) for (let v = h === g ? u + 1 : 0; v < h.length; v++) {
        const px = g[u], py = h[v];
        if (sameCl(L[px], L[py])) continue;
        rB.push(px < py ? rank(a, px, py) : rank(a, py, px)); tally('B1', t, k, 1);
      }
    };
    pos.forEach((g) => { if (g.length > 1) both(g, g, goldTextScore(L[g[0]], L[g[1]]), goldKeywordScore(L[g[0]], L[g[1]])); });
    if (U < 2) return;
    const cand = new Set(), emit = (p, q) => { cand.add(p < q ? p * U + q : q * U + p); };
    goldNearText(rep, emit); goldNearKw(rep, emit);
    cand.forEach((key) => {
      const p = Math.floor(key / U), q = key - p * U, i = rep[p], j = rep[q];
      const k = goldKeywordScore(i, j), t = goldCanText(M, i, j) ? goldTextScore(i, j) : 0;
      if (t >= GOLD_BAND || k >= GOLD_BAND) both(pos[p], pos[q], t, k);
    });
  });
  const sA = rA.done().sort(), sB = rB.done().sort(), ex = new Float64Array(sA.length + sB.length);
  ex.set(sA); ex.set(sB, sA.length); ex.sort();
  // the p-th pair (counting from 0) of an allocation that is in neither A nor B1: the answer is p plus the number of left-out pairs before it
  const nthFree = (p) => { let lo = 0, hi = ex.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (ex[mid] - mid <= p) lo = mid + 1; else hi = mid; } return p + lo; };
  const size = { A: sA.length, B1: sB.length, B2: nSame - ex.length };
  const at = { A: (p) => sA[p], B1: (p) => sB[p], B2: nthFree };
  const total = n * (n - 1) / 2;
  GOLD_POP = {
    cnt, total, N: { A: size.A, B1: size.B1, B2: size.B2, C: total - nSame }, pairOf,
    /* the pair standing in place p of group h (A, B1 or B2), in the fixed order */
    at: (h, p) => pairOf(at[h](p)), place: at,
    /* every pair of a group, for tests only (this lists them all) */
    list: (h) => { const out = []; for (let p = 0; p < size[h]; p++) out.push(pairOf(at[h](p))); return out; }
  };
  return GOLD_POP;
}
/* forget what was worked out from the requirements (after they change, and in tests) */
function goldReset() { GOLD_MODEL = null; GOLD_POP = null; GOLD_PLAN = null; }

/* ----- the plan: which pairs are offered, in which order ----- */
let GOLD_PLAN = null;
function goldPlan() {
  if (GOLD_PLAN) return GOLD_PLAN;
  const P = goldPop(), R = rng(GOLD_SEED);
  // a draw without replacement from a group of known size, listing nothing: a shuffle of places in which only the places that moved are remembered
  const draw = (h, n) => {
    const size = P.N[h], moved = new Map(), at = (p) => moved.has(p) ? moved.get(p) : P.place[h](p), out = [];
    n = Math.min(n, size);
    for (let t = 0; t < n; t++) { const j = t + Math.floor(R() * (size - t)), vt = at(t), vj = at(j); moved.set(t, vj); moved.set(j, vt); out.push(vj); }
    return out.map((r) => P.pairOf(r));
  };
  const pick = {};
  GOLD_GROUPS.slice(0, 3).forEach((h) => { pick[h] = draw(h, GOLD_SIZE[h]); });
  pick.C = [];
  const seen = new Set(), n = REQS.length;
  while (pick.C.length < Math.min(GOLD_SIZE.C, P.N.C)) {
    let i = Math.floor(R() * n), j = Math.floor(R() * n);
    if (i === j || REQS[i].alloc === REQS[j].alloc) continue;
    if (i > j) { const t = i; i = j; j = t; }
    const k = i * n + j; if (seen.has(k)) continue;
    seen.add(k); pick.C.push([i, j]);
  }
  // offered in a mixed order: always from the group that is furthest behind its share, so any prefix is a fair mix
  const taken = { A: 0, B1: 0, B2: 0, C: 0 }, items = [];
  const total = GOLD_GROUPS.reduce((s, h) => s + pick[h].length, 0);
  while (items.length < total) {
    let best = null;
    GOLD_GROUPS.forEach((h) => { if (taken[h] < pick[h].length && (best === null || taken[h] / pick[h].length < taken[best] / pick[best].length)) best = h; });
    const [i, j] = pick[best][taken[best]++];
    items.push({ key: goldKey(REQS[i], REQS[j]), a: REQS[i], b: REQS[j], i, j, h: best, t: goldTextScore(i, j), k: goldKeywordScore(i, j) });
  }
  GOLD_PLAN = { items, by: Object.fromEntries(items.map((x, q) => [x.key, x])), size: Object.fromEntries(GOLD_GROUPS.map((h) => [h, pick[h].length])) };
  return GOLD_PLAN;
}

/* ----- labels: who said what, and what the pair counts as ----- */
function goldLabelsOf(S, key) { return (S.gold && S.gold.labels[key]) || {}; }
/* the settled value of one pair: { v: relation or null, how: 'one' | 'agreed' | 'settled' | 'disputed' | 'unsure', co: 'rel' | 'none' | null } */
function goldFinal(S, key) {
  const L = goldLabelsOf(S, key), who = Object.keys(L), adj = S.gold && S.gold.adj[key];
  if (adj) return { v: adj.v, how: 'settled', co: adj.v === 'unsure' ? null : GOLD_BY[adj.v].rel ? 'rel' : 'none', n: who.length };
  if (!who.length) return null;
  const conc = who.map((w) => L[w].v).filter((v) => v !== 'unsure');
  if (!conc.length) return { v: 'unsure', how: 'unsure', co: null, n: who.length };
  const u = conc.filter((v, i) => conc.indexOf(v) === i);
  if (u.length === 1) return { v: u[0], how: conc.length > 1 ? 'agreed' : 'one', co: GOLD_BY[u[0]].rel ? 'rel' : 'none', n: who.length };
  const co = u.every((v) => GOLD_BY[v].rel) ? 'rel' : u.every((v) => !GOLD_BY[v].rel) ? 'none' : null;
  return { v: null, how: 'disputed', co, n: who.length };
}
/* how many of the labels are the demonstration's own, and how many pairs are usable, left out or in dispute */
function goldUsable(S) {
  const plan = goldPlan(), by = { A: { n: 0, k: 0 }, B1: { n: 0, k: 0 }, B2: { n: 0, k: 0 }, C: { n: 0, k: 0 } };
  const out = { by, labelled: 0, usable: 0, unsure: 0, disputed: 0, fineDisputed: 0, sample: 0, mine: 0, co: {} };
  plan.items.forEach((it) => {
    const L = goldLabelsOf(S, it.key), who = Object.keys(L);
    if (!who.length) return;
    out.labelled++;
    out.sample += who.filter((w) => L[w].sample).length;
    const f = goldFinal(S, it.key);
    if (f.how === 'disputed') { out.fineDisputed++; if (!f.co) { out.disputed++; return; } }
    if (f.how === 'unsure') { out.unsure++; return; }
    if (!f.co) { out.unsure++; return; }
    out.usable++; by[it.h].n++; if (f.co === 'rel') by[it.h].k++; out.co[it.key] = f.co;
  });
  return out;
}

/* ----- the estimate for one method ----- */
/* cells: for each group A and B1, the pairs the method flags (f 1) and the pairs it does not (f 0); each cell holds the pairs it stands for (N), the
   labelled pairs drawn from it (n) and how many of them are related (k). Pure arithmetic on the cells, so it can be checked against a census. */
function goldCellEstimate(cells) {
  const keys = Object.keys(cells);
  const missing = keys.filter((q) => cells[q].N > 0 && cells[q].n === 0);
  const sum = (fl, side) => keys.filter((q) => cells[q].f === fl && cells[q].N > 0 && cells[q].n > 0).reduce((s, q) => {
    const c = cells[q], w = goldWilson(c.k, c.n);
    return s + c.N * (side === 'mid' ? c.k / c.n : side === 'lo' ? w[0] : w[1]);
  }, 0);
  const flagged = keys.filter((q) => cells[q].f === 1).reduce((s, q) => s + cells[q].N, 0);
  const needP = missing.filter((q) => cells[q].f === 1);
  const res = { cells, flagged, missing, p: null, pLo: null, pHi: null, r: null, rLo: null, rHi: null, tp: null, fn: null, related: null };
  if (flagged > 0 && !needP.length) {
    const tp = sum(1, 'mid'), lo = sum(1, 'lo'), hi = sum(1, 'hi');
    res.p = tp / flagged; res.pLo = lo / flagged; res.pHi = Math.min(1, hi / flagged); res.tp = tp;
    if (!missing.length) {
      const fn = sum(0, 'mid'), fnLo = sum(0, 'lo'), fnHi = sum(0, 'hi');
      res.fn = fn; res.related = tp + fn;
      if (tp + fn > 0) { res.r = tp / (tp + fn); res.rLo = lo + fnHi > 0 ? lo / (lo + fnHi) : 0; res.rHi = hi + fnLo > 0 ? hi / (hi + fnLo) : 0; }
    }
  }
  return res;
}
/* flag(it) says whether the method flags a sampled pair; nFlag gives the number of flagged pairs in each group, counted exactly over every pair in it */
function goldEstimate(S, flag, nFlag) {
  const P = goldPop(), plan = goldPlan(), U = goldUsable(S), cells = {};
  ['A', 'B1'].forEach((h) => {
    cells[h + ':1'] = { h, f: 1, N: nFlag[h], n: 0, k: 0 };
    cells[h + ':0'] = { h, f: 0, N: P.N[h] - nFlag[h], n: 0, k: 0 };
  });
  plan.items.forEach((it) => {
    const co = U.co[it.key]; if (!co || (it.h !== 'A' && it.h !== 'B1')) return;
    const c = cells[it.h + ':' + (flag(it) ? 1 : 0)];
    c.n++; if (co === 'rel') c.k++;
  });
  return goldCellEstimate(cells);
}
/* the rows of the "measured from labels" table: the app's clusters, then the two scores at the chosen cut-off */
function goldMeasure(S) {
  const P = goldPop(), q = Math.max(0, GOLD_CUTS.indexOf(S.gold.cut)), cut = GOLD_CUTS[q];
  const rows = [
    { k: 'clusters', name: 'The app’s clusters', sub: 'Pairs the mechanical steps put in the same cluster.', est: goldEstimate(S, (it) => it.h === 'A', { A: P.N.A, B1: 0 }) },
    { k: 'text', name: 'Text match, ' + cut.toFixed(1) + ' or more', sub: 'Word by word: how many edits turn one wording into the other.', est: goldEstimate(S, (it) => it.t >= cut, { A: P.cnt.A.text[q], B1: P.cnt.B1.text[q] }) },
    { k: 'kw', name: 'Keyword overlap, ' + cut.toFixed(1) + ' or more', sub: 'Words that few requirements use count for more.', est: goldEstimate(S, (it) => it.k >= cut, { A: P.cnt.A.kw[q], B1: P.cnt.B1.kw[q] }) }
  ];
  return { cut, rows };
}
/* the groups the recall does not cover: how many related pairs could be hiding there */
function goldOutside(S) {
  const P = goldPop(), U = goldUsable(S);
  return ['B2', 'C'].map((h) => {
    const c = U.by[h], w = goldWilson(c.k, c.n);
    return { h, name: GOLD_GROUP_NAME[h], N: P.N[h], n: c.n, k: c.k, hi: c.n ? w[1] : null, pairsHi: c.n ? Math.round(P.N[h] * w[1]) : null };
  });
}
/* does the AI name the relation the way people labelled it? Only among pairs the app clustered that people call related. */
function goldAiRel(c) {
  const v = (c.ai && c.ai.verdict) || '';
  if (/^SUBSUMES/.test(v)) return 'SUBSUMES';
  if (v) return v;
  return c.ai && c.ai.mode === 'draft' ? 'EQUIVALENT' : c.rel;
}
function goldNaming(S) {
  const plan = goldPlan(); let n = 0, k = 0, held = 0; const miss = [];
  plan.items.forEach((it) => {
    if (it.h !== 'A') return;
    const f = goldFinal(S, it.key);
    if (!f || !f.v || f.v === 'none' || f.v === 'unsure') return;
    const c = CL_BY[it.a.cid];
    if (!aiGateOf(S, c).open) { held++; return; }   // the AI was not used on this group, so it has no answer to compare
    n++;
    const ai = goldAiRel(c);
    if (ai === GOLD_BY[f.v].ai) k++; else miss.push({ key: it.key, cid: c.id, ai, label: GOLD_BY[f.v].name });
  });
  const w = goldWilson(k, n);
  return { n, k, held, p: n ? k / n : null, lo: n ? w[0] : null, hi: n ? w[1] : null, miss };
}

/* ----- agreement between two people ----- */
function goldAgreement(S) {
  const tab = {};
  Object.keys(S.gold.labels).forEach((key) => {
    const L = S.gold.labels[key], who = Object.keys(L).filter((w) => L[w].v !== 'unsure').sort();
    for (let x = 0; x < who.length; x++) for (let y = x + 1; y < who.length; y++) (tab[who[x] + '|' + who[y]] = tab[who[x] + '|' + who[y]] || []).push([L[who[x]].v, L[who[y]].v]);
  });
  const names = Object.keys(tab).sort((a, b) => tab[b].length - tab[a].length || (a < b ? -1 : 1));
  if (!names.length) return null;
  const pairs = tab[names[0]], n = pairs.length, [p1, p2] = names[0].split('|');
  const ag = pairs.filter((x) => x[0] === x[1]).length;
  const ks = GOLD_REL.filter((r) => r.k !== 'unsure').map((r) => r.k);
  const pe = ks.reduce((s, c) => s + (pairs.filter((x) => x[0] === c).length / n) * (pairs.filter((x) => x[1] === c).length / n), 0);
  const kappa = pe >= 1 ? null : (ag / n - pe) / (1 - pe);
  return { a: p1, b: p2, n, agree: ag, pct: ag / n, kappa };
}
function goldDisputes(S) {
  return goldPlan().items.filter((it) => { const f = goldFinal(S, it.key); return f && f.how === 'disputed'; });
}

/* ----- the queue a person sees ----- */
const goldHash = (s) => parseInt(h32(s), 16);
const goldWants = (key) => (goldHash('dbl' + key) % GOLD_DOUBLE === 0 ? 2 : 1);
function goldQueue(S, who) {
  const plan = goldPlan(), skip = (S.gold.skip && S.gold.skip[who]) || [], now = [], later = [];
  plan.items.forEach((it) => {
    const L = goldLabelsOf(S, it.key);
    if (L[who]) return;
    const concrete = Object.keys(L).filter((w) => L[w].v !== 'unsure').length;
    if (concrete >= goldWants(it.key)) return;
    (skip.indexOf(it.key) >= 0 ? later : now).push(it);
  });
  return now.concat(later);
}

/* ----- the demonstration's labels (never used for anything but the demonstration) ----- */
function goldTruth(a, b) {
  const mem = (r) => (r.cid ? CL_BY[r.cid].members.find((m) => m.id === r.id) : null);
  const sigOf = (r) => r.sig || (r.cid && CL_BY[r.cid].sig) || '';
  const valOf = (r) => (r.cid ? (mem(r) ? mem(r).v : undefined) : r.val);
  if (a.cid && a.cid === b.cid) {
    const c = CL_BY[a.cid], va = valOf(a), vb = valOf(b);
    if (c.sig && va !== undefined && vb !== undefined && va !== null && vb !== null) return va === vb ? 'equiv' : 'variant';
    return { EQUIVALENT: 'equiv', VARIANT: 'variant', SUBSUMES: 'contains', CONFLICT: 'conflict' }[c.rel] || 'variant';
  }
  const sa = sigOf(a), sb = sigOf(b);
  if (sa && sa === sb) { const va = valOf(a), vb = valOf(b); if (va !== undefined && va === vb) return 'equiv'; }   // outside a cluster only a real duplicate counts: the app missed it
  return 'none';
}
function goldSampleLabels() {
  const plan = goldPlan(), out = {};
  const near = { equiv: 'variant', variant: 'equiv', contains: 'variant', conflict: 'variant', none: 'variant' };
  plan.items.slice(0, 100).forEach((it) => {
    const t = goldTruth(it.a, it.b), x = goldHash('lab' + it.key) % 100;
    let v = t;
    if (t !== 'none' && x < 7) v = 'none';                      // a suggestion that is not really related
    else if (x >= 7 && x < 13 && t !== 'none') v = near[t];      // the neighbouring relation
    else if (t === 'none' && x < 3) v = 'variant';
    out[it.key] = { priya: { v, note: '', sample: true } };
    if (goldWants(it.key) === 2) {
      const y = goldHash('two' + it.key) % 100;
      out[it.key].morgan = { v: y < 14 ? near[v] || 'variant' : v, note: '', sample: true };
    }
  });
  return out;
}

/* ----- the file ----- */
function goldFile(S) {
  const P = goldPop(), plan = goldPlan(), U = goldUsable(S);
  const pairs = plan.items.map((it) => {
    const f = goldFinal(S, it.key); if (!f) return null;
    const L = goldLabelsOf(S, it.key);
    return { pair: it.key, a: it.a.id, b: it.b.id, a_text: it.a.text, b_text: it.b.text, group: it.h, label: f.v, status: f.how, counts_as: f.co === 'rel' ? 'related' : f.co === 'none' ? 'not related' : 'left out',
      labelled_by: Object.keys(L).sort().map((w) => w + (L[w].sample ? ' (sample)' : '')), notes: Object.keys(L).filter((w) => L[w].note).map((w) => w + ': ' + L[w].note) };
  }).filter(Boolean);
  return {
    format: 'reqin-gold-set/1',
    about: 'Pairs of requirements labelled by people. Each pair says how it was drawn (group). Each group says how many pairs it stands for (group_pairs), which is what turns the labels into precision and recall. A label from a labeller marked (sample) is made up for the demonstration.',
    groups: Object.fromEntries(GOLD_GROUPS.map((h) => [h, { name: GOLD_GROUP_NAME[h], group_pairs: P.N[h], drawn: plan.size[h], labelled_and_counted: U.by[h].n }])),
    pairs
  };
}
