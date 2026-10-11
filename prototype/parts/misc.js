const TODAY = '10 Oct';
const SCOPE_CACHE = {};
function universe(S) {
  const k = S.scope;
  if (!SCOPE_CACHE[k]) {
    SCOPE_CACHE[k] = {
      cl: k === 'all' ? CLUSTERS : CLUSTERS.filter((c) => c.alloc === k),
      order: ORDER.filter((c) => k === 'all' || c.alloc === k),
      reqs: k === 'all' ? REQS : REQS.filter((r) => r.alloc === k)
    };
  }
  return SCOPE_CACHE[k];
}
const EV_SEED = (() => {
  const nJ = CLUSTERS.filter((c) => c.ai.mode === 'judge').length, nD = CLUSTERS.filter((c) => c.ai.mode === 'draft').length;
  const rows = [
    ['mechanical', 'Pipeline', 'Read and normalised ' + TOTAL_REQS.toLocaleString('en-US') + ' requirements', 'whole project', '09:02:11'],
    ['mechanical', 'Pipeline', 'Blocked by allocation; built 1,126 candidate pairs and ' + CLUSTERS.length + ' clusters', 'CL-001 to CL-252', '09:03:48'],
    ['ai', 'AI judge', 'Judged ' + nJ + ' clusters and drafted wording for ' + nD + '; ten guards run on every proposal', 'CL-001 to CL-252', '09:07:30']
  ];
  let prev = '00000000';
  return rows.map((r, i) => { const payload = [i + 1, r[0], r[1], r[2], r[3]].join('|'); const hash = h32(prev + payload); const e = { seq: i + 1, type: r[0], actor: r[1], text: r[2], target: r[3], time: r[4], prev, hash, payload }; prev = hash; return e; });
})();
function spreadOf(c, ms) {
  if (c.kind === 'modal') return 'shall / should';
  if (c.kind === 'subs') return 'plain / detailed';
  if (c.kind === 'cond') return 'conditions differ';
  if (c.kind === 'confN') return 'required / prohibited';
  const rk = ms.filter((m) => m.rankable && m.v !== null && m.v !== undefined).map((m) => m.v);
  if (!rk.length) return '';
  const lo = Math.min.apply(null, rk), hi = Math.max.apply(null, rk);
  return lo === hi ? 'same value' : fmtVal(c, lo) + ' to ' + fmtVal(c, hi);
}
function dirWords(S, c) {
  if (c.kind === 'modal') return '"shall" is stricter than "should"';
  if (c.kind === 'subs') return 'more required content is stricter';
  const d = dirEff(S, c);
  if (d === 'higher') return 'a higher value is stricter';
  if (d === 'lower') return 'a lower value is stricter';
  return 'not ranked (a conflict is not a ranking question)';
}
const TERMS = {
  FCS: 'Flight Control Subsystem', VDC: 'volts, direct current', Hz: 'times per second', 'heartbeat': 'a regular "I am alive" message', 'telemetry': 'measurements sent down from the vehicle', 'downlinked': 'sent from the vehicle to the ground',
  'NLI': 'a model that says whether one sentence implies another', 'uplinked': 'sent from the ground to the vehicle', 'beacon': 'a regular status message', 'keep-alive': 'a regular "I am alive" message'
};
