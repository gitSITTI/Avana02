#!/usr/bin/env node
/* Scale test: does the page stay usable with tens of thousands of requirements?

   It builds a test page with K times as many requirements and clusters as the sample (REQIN_SCALE, see build.py; the shipped page is never touched), loads it the
   way verify.js does, and times what a person waits for:
     - the first and the repeat drawing of every page
     - the one-off counting of pairs for the gold set (the work that was once quadratic and took 204 s at 25,000 requirements)
     - the project file, loading it back with its checks, and the trace map file
   It also checks that the counts are still true at that size, and that memory stays within bounds.

   usage:  node scale.js [K] [shape]  K defaults to 20, which is 24,960 requirements and 5,040 clusters
           shape is "sample" (the default: the sample repeated K times) or "varied" (the same size with a different shape: mostly different wordings of different lengths,
           three in ten requirements in one allocation, and a few clusters of 40 to 200 members; see build.py). Both are made up. They tell how fast, not how well.
   env:    SCALE_SLACK=2              multiplies every limit (a slow machine); PYTHON=python3; REQIN_SHAPE=varied (the same as the second argument)
   Exit status 1 when any limit is passed. The limits are about three times what a laptop needs (for each shape), so they fail on a real slowdown and not on noise.
   The limits grow in proportion to K, and the pair counting grows faster than that on the varied shape (about 9 s at K = 20 and 42 s at K = 40 here), so K above 20 is for looking, not a promise. */
const { spawnSync } = require('child_process');
const fs = require('fs'), os = require('os'), path = require('path');

const K = parseInt(process.argv[2] || process.env.REQIN_SCALE || '20', 10);
const SHAPE = process.argv[3] || process.env.REQIN_SHAPE || 'sample';
if (SHAPE !== 'sample' && SHAPE !== 'varied') { console.error('the shape is "sample" or "varied", not "' + SHAPE + '"'); process.exit(2); }
const SLACK = parseFloat(process.env.SCALE_SLACK || '1');
const LIMIT = {                                   // milliseconds, at K = 20; they grow in proportion to K / 20
  first: 4000,                                    // the first drawing of a page
  repeat: 1500,                                   // drawing it again after a change
  pairs: SHAPE === 'varied' ? 30000 : 15000,      // counting every group of pairs for the gold set, once; the varied shape needs about 6 times what the repeated sample does (9 s against 1.5 s here)
  file: 8000,                                     // writing, or reading back and checking, the project file; writing the trace map
  heapMB: 1500                                    // memory in use at the end
};
const grow = Math.max(1, K / 20) * SLACK;

const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'reqin-scale-'));
const page = path.join(dir, 'Main.dc.html');
const built = spawnSync(process.env.PYTHON || 'python3', [path.join(__dirname, 'build.py'), page], { cwd: __dirname, env: Object.assign({}, process.env, { REQIN_SCALE: String(K), REQIN_SHAPE: SHAPE }), encoding: 'utf8' });
if (built.status !== 0) { console.error('the scaled build failed:\n' + built.stderr); process.exit(2); }

process.chdir(__dirname);
process.argv[2] = page;
const V = require('./verify.js'), C = V.Component;
const REQS = C.REQS, CLUSTERS = C.CLUSTERS;
const fails = [], rows = [];
const check = (ok, msg) => { if (!ok) fails.push(msg); };
const limit = (name, ms, max) => { const lim = Math.round(max * grow); rows.push([name, ms, lim]); check(ms <= lim, name + ' took ' + ms + ' ms, the limit is ' + lim + ' ms'); };
const time = (f) => { const t = Date.now(); const out = f(); return [Date.now() - t, out]; };

console.log('scale ' + K + ', shape ' + SHAPE + ': ' + REQS.length + ' requirements, ' + CLUSTERS.length + ' clusters, limits x' + grow.toFixed(2));
check(REQS.length >= 1248 * K && CLUSTERS.length >= 252 * K - 8 * K, 'the scaled project is not as large as asked (' + REQS.length + ' requirements)');

// ---- what shape it is: printed, and for "varied" checked, so that the test cannot quietly become the repeated sample again ----
const SHAPEINFO = (() => {
  const texts = new Set(REQS.map((r) => r.text)), byAl = {};
  REQS.forEach((r) => { byAl[r.alloc] = (byAl[r.alloc] || 0) + 1; });
  const lens = REQS.map((r) => r.text.split(/\s+/).length).sort((a, b) => a - b);
  const sizes = CLUSTERS.map((c) => c.members.length).sort((a, b) => b - a);
  return { distinct: texts.size / REQS.length, topAlloc: Math.max.apply(null, Object.values(byAl)) / REQS.length, wMin: lens[0], wMed: lens[lens.length >> 1], wMax: lens[lens.length - 1], bigCl: sizes[0], over39: sizes.filter((x) => x >= 40).length };
})();
console.log('shape: ' + (SHAPEINFO.distinct * 100).toFixed(0) + '% of wordings are different, the largest allocation holds ' + (SHAPEINFO.topAlloc * 100).toFixed(0) + '% of the requirements, ' +
  SHAPEINFO.wMin + ' to ' + SHAPEINFO.wMax + ' words a requirement (median ' + SHAPEINFO.wMed + '), the largest cluster has ' + SHAPEINFO.bigCl + ' members, ' + SHAPEINFO.over39 + ' clusters have 40 or more');
if (SHAPE === 'varied') {
  check(SHAPEINFO.distinct >= 0.75, 'the varied project is not varied: only ' + (SHAPEINFO.distinct * 100).toFixed(0) + '% of its wordings are different');
  check(SHAPEINFO.topAlloc >= 0.25, 'the varied project has no large allocation (the largest holds ' + (SHAPEINFO.topAlloc * 100).toFixed(0) + '%)');
  check(SHAPEINFO.bigCl >= 100 && SHAPEINFO.over39 >= 2, 'the varied project has no very large cluster');
  check(SHAPEINFO.wMax - SHAPEINFO.wMin >= 10, 'the wordings of the varied project are all about the same length');
} else {
  check(SHAPEINFO.bigCl <= 20, 'the sample has a cluster of ' + SHAPEINFO.bigCl + ' members');
}

// ---- every page, first drawing then a repeat ----
const VIEWS = ['open', 'import', 'home', 'review', 'explorer', 'overview', 'vee', 'results', 'methods', 'gold', 'audit', 'policy', 'ai', 'export'];
const SHOW = { review: { selected: 'CL-050', qTab: 'all' }, explorer: { xPick: REQS[Math.floor(REQS.length / 2)].id } };
const comp = new C.Component();
VIEWS.forEach((v) => {
  const pairs = v === 'methods' || v === 'gold';       // these two need the pair counts, which are worked out the first time and then kept
  const st = Object.assign({ view: v, person: 'morgan' }, SHOW[v] || {});
  comp.setState(st);
  const [first] = time(() => comp.renderVals());
  const [again] = time(() => comp.renderVals());
  if (pairs) { limit(v + ': first drawing, with the pair counts', first, LIMIT.pairs + LIMIT.first); } else limit(v + ': first drawing', first, LIMIT.first);
  limit(v + ': drawing again', again, LIMIT.repeat);
});

// ---- the largest cluster in the review page (a person opening the biggest cluster there is) ----
{
  const big = CLUSTERS.reduce((a, c) => (c.members.length > a.members.length ? c : a), CLUSTERS[0]);
  const c2 = new C.Component();
  c2.setState({ view: 'review', person: 'morgan', selected: big.id, qTab: 'all' });
  const [first] = time(() => c2.renderVals());
  const [again] = time(() => c2.renderVals());
  limit('review, the largest cluster (' + big.members.length + ' members): first drawing', first, LIMIT.first);
  limit('review, the largest cluster: drawing again', again, LIMIT.repeat);
}

// ---- the pair counts, the way they are checked in verify.js, at this size ----
{
  const P = C.goldPop(), Pl = C.goldPlan(), n = REQS.length;
  check(P.N.A + P.N.B1 + P.N.B2 + P.N.C === n * (n - 1) / 2, 'the four groups of pairs do not add up to every pair');
  check(P.N.A === CLUSTERS.reduce((s, c) => s + c.members.length * (c.members.length - 1) / 2, 0), 'group A is not every pair inside a cluster');
  check(Pl.items.length === 160 && new Set(Pl.items.map((x) => x.key)).size === 160, 'the plan does not hold 160 different pairs');
  check(C.GOLD_GROUPS.every((h) => Pl.items.filter((x) => x.h === h).length === C.GOLD_SIZE[h]), 'the plan does not draw the planned number from each group');
  check(Pl.items.every((x) => x.h !== 'B1' || (x.t >= 0.6 || x.k >= 0.6)) && Pl.items.every((x) => x.h !== 'B2' || (x.t < 0.6 && x.k < 0.6)), 'a pair is in the wrong group');
  // the sample drawn from B2 must be spread over the whole group and not bunched at its start
  const places = Pl.items.filter((x) => x.h === 'B2').map((x) => x.i);
  check(Math.max.apply(null, places) - Math.min.apply(null, places) > n / 4, 'the pairs drawn from group B2 are bunched together');
  rows.push(['pairs: A ' + P.N.A + ', B1 ' + P.N.B1 + ', B2 ' + P.N.B2 + ', C ' + P.N.C, 0, 0]);
}

// ---- the files ----
{
  const S0 = Object.assign({}, C.DEFAULTS, { gold: Object.assign({}, C.DEFAULTS.gold, { labels: C.goldSampleLabels() }) });
  const [tFile, text] = time(() => JSON.stringify(C.persistFile(S0, '2026-10-14T12:00:00.000Z')));
  limit('project file: write', tFile, LIMIT.file);
  const [tBack, back] = time(() => C.persistCheck(JSON.parse(text)));
  limit('project file: read back and check', tBack, LIMIT.file);
  check(back.ok, 'the project file did not load back: ' + back.problems.join(' '));
  rows.push(['project file size ' + Math.round(text.length / 1024) + ' KB', 0, 0]);
  const c = new C.Component(), infos = c.allInfos(c.S);
  const [tMap, map] = time(() => { const T = C.trOf(c.S, infos, ''); return JSON.stringify(C.trFile(c.S, T, '')) + C.TR_TABS.map((t) => C.trCsv(T, t.k)).join(''); });
  limit('trace map files: write', tMap, LIMIT.file);
  rows.push(['trace map files size ' + Math.round(map.length / 1024) + ' KB', 0, 0]);
}

const heap = Math.round(process.memoryUsage().heapUsed / 1e6);
rows.push(['memory in use (MB)', heap, Math.round(LIMIT.heapMB * Math.max(1, K / 20) * SLACK)]);
check(heap <= LIMIT.heapMB * Math.max(1, K / 20) * SLACK, 'memory in use is ' + heap + ' MB, the limit is ' + Math.round(LIMIT.heapMB * Math.max(1, K / 20) * SLACK) + ' MB');

console.log('what'.padEnd(52) + 'ms'.padStart(8) + 'limit'.padStart(8));
rows.forEach((r) => console.log(r[0].padEnd(52) + (r[2] ? String(r[1]).padStart(8) + String(r[2]).padStart(8) : '')));
fs.rmSync(dir, { recursive: true, force: true });
if (fails.length) { console.log('\nSCALE FAILED'); fails.forEach((f) => console.log(' - ' + f)); process.exit(1); }
console.log('\nSCALE OK');
