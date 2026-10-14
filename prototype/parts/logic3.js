
/* ---------- results: the consolidated set set against the original, and a grade ----------
   Everything here is computed from the decisions in the project (the seeded ones from teammates, which are sample data, and yours).
   The grading rule is a proposal for the team to agree, not a standard. The weights and bands are written out on the page. */
const GRADE_PARTS = [
  { k: 'cover', name: 'Accounted for', weight: 20, plain: 'Every original requirement is kept, merged into a named survivor, or has a recorded reason. Requirements in clusters nobody has decided yet are not accounted for.' },
  { k: 'oblig', name: 'Obligations preserved', weight: 30, plain: 'No merge loosens a number, unit, shall or condition unless the owners and the process engineer have signed it.' },
  { k: 'sign', name: 'Signed off', weight: 20, plain: 'Every lens the sign-off policy requires has signed the decision.' },
  { k: 'why', name: 'The why is written down', weight: 15, plain: 'The decision carries a note saying why, as well as a reason code.' },
  { k: 'second', name: 'A second pair of eyes', weight: 15, plain: 'Someone other than the person who decided has signed, checked or reviewed it.' }
];
const GRADE_BANDS = [[90, 'A'], [80, 'B'], [70, 'C'], [60, 'D'], [0, 'F']];
const GRADE_ORDER = ['A', 'B', 'C', 'D', 'F'];
function letterOf(score) { return GRADE_BANDS.find((b) => score >= b[0])[1]; }
const COUNTED = ['decided', 'review', 'approved', 'siblings'];   // a decision under dispute or gone stale does not count until it is settled
/* alloc: '' for everything in scope, or one allocation name */
function resultsOf(S, infos, alloc) {
  const U = universe(S);
  const reqs = U.reqs.filter((r) => !alloc || r.alloc === alloc);
  const sel = infos.filter((x) => !alloc || x.c.alloc === alloc);
  const R = { n: reqs.length, clusters: sel.length, decided: 0, kinds: { asis: 0, keep: 0, merged: 0, separate: 0, linked: 0, escalated: 0, superseded: 0, waiting: 0 }, after: 0, projected: 0, newWord: 0, mergeN: 0, unprotected: 0, signN: 0, signDone: 0, why: 0, second: 0, waitingClusters: 0, noWhy: 0, noSecond: 0, notSigned: 0, cuts: [], ids: { cover: [], oblig: [], sign: [], why: [], second: [] } };
  let inCl = 0, peeledN = 0;
  sel.forEach((x) => {
    const c = x.c, ms = membersOf(S, c);
    inCl += c.members.length; peeledN += c.members.length - ms.length;
    const dec = x.dec && COUNTED.indexOf(x.st) >= 0 ? x.dec : null;
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
  const val = {
    cover: R.n ? (R.n - R.kinds.waiting) / R.n : 0,
    oblig: R.mergeN ? 1 - R.unprotected / R.mergeN : 1,
    sign: R.decided ? R.signDone / R.signN : 0,
    why: R.decided ? R.why / R.decided : 0,
    second: R.decided ? R.second / R.decided : 0
  };
  const nf = (x) => x.toLocaleString('en-US');
  const detail = {
    cover: nf(R.n - R.kinds.waiting) + ' of ' + nf(R.n) + ' requirements accounted for',
    oblig: R.mergeN ? (R.mergeN - R.unprotected) + ' of ' + R.mergeN + ' merges keep every obligation' : 'No merge recorded yet',
    sign: R.signDone + ' of ' + R.signN + ' decisions fully signed',
    why: R.why + ' of ' + R.decided + ' decisions have a note',
    second: R.second + ' of ' + R.decided + ' had another person’s eyes on them'
  };
  const parts = GRADE_PARTS.map((p) => ({ k: p.k, name: p.name, weight: p.weight, plain: p.plain, v: val[p.k], pts: p.weight * val[p.k], gap: p.weight * (1 - val[p.k]), detail: detail[p.k] }));
  const score = parts.reduce((s, p) => s + p.pts, 0);
  let letter = letterOf(score), capped = false;
  if (R.unprotected > 0 && GRADE_ORDER.indexOf(letter) < GRADE_ORDER.indexOf('C')) { letter = 'C'; capped = true; }
  R.parts = parts; R.score = score; R.letter = letter; R.capped = capped; R.graded = R.decided > 0;
  R.provisional = R.clusters ? R.decided / R.clusters < 0.9 : true;
  return R;
}
