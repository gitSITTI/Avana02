/* ---------- one requirement at a time ----------
   Most of the project is decided cluster by cluster. This part is for a requirement that stands alone: nothing similar was found, or a person
   took it out of its cluster. A person looks at it (and at any other requirement they choose to put beside it) and records one of five things:
   keep it as written, keep it with new wording, drop it, say it is not a requirement, or ask the owner.

   The rules in this file are the only place these decisions are counted. Results, the V, the review lists and the export read them from here;
   nothing counts a single decision a second way.
     - A decision counts as soon as it is recorded. Whether it is signed off is a separate question, answered by the same sign-off policy as a cluster.
     - Dropping a requirement or calling it "not a requirement" removes it from the set, so it always needs the owners and the process engineer.
     - New wording that changes a number, or weakens shall to should, needs the owners as well; a flipped "not" or a lost shall is blocked.
     - "Ask the owner" changes nothing in the counts: the requirement stays as it is until the answer is recorded.
     - A requirement that is in a baseline needs a change request number for new wording, a drop or "not a requirement" (trace.js knows which are baselined). */
const RD_KINDS = [
  { k: 'keep', name: 'Keep as written', help: 'It is a real requirement and the wording is fine.' },
  { k: 'reword', name: 'Keep, with new wording', help: 'It is a real requirement. The wording needs to change.' },
  { k: 'drop', name: 'Drop it', help: 'It no longer applies, or another requirement covers it. It leaves the set.' },
  { k: 'notreq', name: 'Not a requirement', help: 'A definition, a note or a rationale. It leaves the set and stays in the document.' },
  { k: 'ask', name: 'Ask the owner', help: 'You cannot tell. Nothing changes until they answer.' }
];
const RD_BY = Object.fromEntries(RD_KINDS.map((r) => [r.k, r]));
const RD_OTHER = ['S-OTH', 'Other (the note says why)'];
const RD_REASONS = {
  keep: [['S-OK', 'Checked: still needed as written'], ['S-ONLY', 'Nothing else in the project says this']],
  reword: [['S-CLR', 'Unclear or open to two readings'], ['S-VER', 'Cannot be verified as written'], ['S-NUM', 'A number, unit or condition needs fixing'], RD_OTHER],
  drop: [['S-OBS', 'No longer applies'], ['S-COV', 'Another requirement in this project covers it'], ['S-OUT', 'Covered outside this project'], RD_OTHER],
  notreq: [['S-DEF', 'A definition or glossary entry'], ['S-RAT', 'A rationale or a note'], ['S-BKG', 'Background information'], RD_OTHER],
  ask: []
};
const RD_REASON_NAME = {}; Object.keys(RD_REASONS).forEach((k) => RD_REASONS[k].forEach(([c, n]) => { RD_REASON_NAME[c] = n; }));
/* where a decided requirement goes in the Results table */
const RD_DEST = { keep: 'kept1', reword: 'reworded', drop: 'dropped', notreq: 'notreq', ask: 'escalated' };
const RD_REMOVES = (k) => k === 'drop' || k === 'notreq';
const REQ_IX = {}; REQS.forEach((r, i) => { REQ_IX[r.id] = i; });
const RD_NOTE_MIN = 12, RD_ASK_MIN = 8, RD_NU_MIN = 20;

/* a requirement can be decided on its own when it is in no cluster, or a person took it out of its cluster */
function rdAlone(S, r) { return !r.cid || (S.peeled[r.cid] || []).indexOf(r.id) >= 0; }
function rdDec(S, id) { return (S.rdec && S.rdec[id]) || null; }
/* the decision that counts: the requirement stands alone and has one */
function rdStand(S, r) { return r && rdAlone(S, r) ? rdDec(S, r.id) : null; }
function rdNorm(t) { return t.toLowerCase().replace(/\s+/g, ' ').replace(/[.,;:]+$/, '').trim(); }

/* the same checks a cluster's own wording gets, for one requirement against its old wording */
function rdGuards(r, text) {
  const out = { items: [], blocks: 0, warns: 0, weakening: false, same: false, changes: [] };
  const add = (name, st, note) => { out.items.push({ name, st, note }); if (st === 'block') out.blocks++; if (st === 'warn') out.warns++; };
  const was = r.text, t = (text || '').trim();
  if (!t) { add('Wording', 'block', 'Write the new wording.'); return out; }
  if (rdNorm(t) === rdNorm(was)) { out.same = true; add('Wording', 'block', 'This is the same wording. Choose “Keep as written” instead.'); return out; }
  const q0 = quantities(was), q1 = quantities(t);
  const key = (q) => q.n + '|' + unitCat(q.unit), s0 = q0.map(key).sort().join(','), s1 = q1.map(key).sort().join(',');
  if (q0.length && !q1.length) add('Numbers preserved', 'block', 'The old wording has ' + q0.map((q) => q.raw).join(', ') + ' and the new wording has no number.');
  else if (s0 !== s1) { add('Numbers preserved', 'warn', 'The numbers change from ' + (q0.map((q) => q.raw).join(', ') || 'none') + ' to ' + (q1.map((q) => q.raw).join(', ') || 'none') + '. The owners have to confirm.'); out.weakening = true; }
  else add('Numbers preserved', 'pass', q0.length ? q0.map((q) => q.raw).join(', ') + ' stays the same.' : 'No numbers involved.');
  const c0 = q0.map((q) => unitCat(q.unit)).filter((x, i, a) => a.indexOf(x) === i), c1 = q1.map((q) => unitCat(q.unit)).filter((x, i, a) => a.indexOf(x) === i);
  if (c1.some((u) => c0.length && c0.indexOf(u) < 0)) add('Units compatible', 'block', 'The new wording uses ' + c1.join(', ') + '; the old one used ' + c0.join(', ') + '. A person has to convert them first.');
  else add('Units compatible', 'pass', c0.length ? 'Same kind of unit.' : 'No units involved.');
  const m0 = modalOf(was), m1 = modalOf(t);
  if (!m1) add('Shall / should / will', 'block', 'The new wording has no shall, should or will.');
  else if (MODAL_RANK[m1] < MODAL_RANK[m0]) { add('Shall / should / will', 'warn', 'Weakening: “' + m1 + '” replaces “' + m0 + '”. The owners have to confirm.'); out.weakening = true; }
  else add('Shall / should / will', 'pass', 'Keeps “' + m1 + '”' + (MODAL_RANK[m1] > MODAL_RANK[m0] ? ' (stronger than before).' : '.'));
  if (negOf(was) !== negOf(t)) add('Negation preserved', 'block', 'The new wording ' + (negOf(t) ? 'adds' : 'drops') + ' a “not”.');
  else add('Negation preserved', 'pass', 'Same polarity.');
  const cw = (x) => kindsOfTokens(x.split(' ').filter(Boolean)).map((k, i) => (k === 'cond' ? normTok(x.split(' ').filter(Boolean)[i]) : null)).filter(Boolean);
  const k0 = cw(was), k1 = cw(t), added = k1.filter((w) => k0.indexOf(w) < 0), gone = k0.filter((w) => k1.indexOf(w) < 0);
  if (added.length) { add('Conditions kept', 'warn', 'A condition is added (' + added.join(', ') + '): the requirement now applies in fewer cases. The owners have to confirm.'); out.weakening = true; }
  else if (gone.length) add('Conditions kept', 'warn', 'A condition is removed (' + gone.join(', ') + '): the requirement now applies in more cases.');
  else add('Conditions kept', 'pass', k0.length ? 'The conditions are the same.' : 'No conditions involved.');
  out.changes = compareRows(was, [t])[0].changes;
  return out;
}

/* who has to sign: the cluster policy, with the requirement standing in for a cluster */
function rdRequired(r, dec) {
  if (dec.outcome === 'ask') return { SE: 'none', PE: 'none', UX: 'none', NU: 'none', OWN: 'none', ADJ: 'none' };
  return required({ id: r.id, lane: dec.outcome === 'keep' ? 'A' : 'B', crossOwner: false, baselined: false }, { newWording: dec.outcome === 'reword', weakening: !!dec.weakening || RD_REMOVES(dec.outcome) });
}
function rdSignState(S, r, dec) {
  const req = rdRequired(r, dec), sg = signOf(S, r.id);
  const slots = SLOT_KEYS.filter((k) => req[k] !== 'none'), have = slots.filter((k) => sg[k]);
  return { req, sg, slots, have, missing: slots.filter((k) => !sg[k]), done: slots.length > 0 && have.length === slots.length };
}
/* 'asked' | 'decided' | 'review' | 'approved' | null */
function rdStatus(S, r) {
  const d = rdStand(S, r); if (!d) return null;
  if (d.outcome === 'ask') return 'asked';
  const q = rdSignState(S, r, d);
  return q.done ? 'approved' : q.have.length ? 'review' : 'decided';
}
const RD_STATUS_LABEL = { asked: 'Waiting for the owner', decided: 'Decided', review: 'In review', approved: 'Approved' };
/* every counted single decision in the current scope (and one allocation when alloc is given) */
function rdList(S, alloc) {
  const out = [];
  Object.keys(S.rdec || {}).sort().forEach((id) => {
    const r = REQ_BY[id], dec = S.rdec[id];
    if (!r || !dec || !rdAlone(S, r)) return;
    if (S.scope !== 'all' && r.alloc !== S.scope) return;
    if (alloc && r.alloc !== alloc) return;
    out.push({ r, dec, kind: RD_DEST[dec.outcome], q: dec.outcome === 'ask' ? null : rdSignState(S, r, dec), status: rdStatus(S, r) });
  });
  return out;
}
/* the other requirements that read most like this one (same allocation), best first */
const RD_NEAR_CACHE = {};
function rdNear(id, n) {
  const key = id + '|' + n;
  if (RD_NEAR_CACHE[key]) return RD_NEAR_CACHE[key];
  const r = REQ_BY[id], i = REQ_IX[id], out = [];
  REQS.forEach((o, j) => {
    if (j === i || o.alloc !== r.alloc) return;
    const t = goldTextScore(Math.min(i, j), Math.max(i, j)), k = goldKeywordScore(Math.min(i, j), Math.max(i, j));
    out.push({ id: o.id, t, k, s: Math.max(t, k) });
  });
  out.sort((a, b) => b.s - a.s || (a.id < b.id ? -1 : 1));
  return (RD_NEAR_CACHE[key] = out.slice(0, n));
}
/* what is wrong with the form, in the order a person would fix it; empty means it can be recorded */
function rdProblems(S, r, f) {
  const out = [], kind = f.kind;
  if (!kind) { out.push('Choose what to do with this requirement.'); return out; }
  const note = (f.note || '').trim();
  if (kind !== 'ask' && !f.reason) out.push('Choose the reason.');
  if (kind === 'reword') { const g = rdGuards(r, f.text); if (g.blocks) out.push(g.items.find((x) => x.st === 'block').note); }
  if (kind === 'drop' && f.reason === 'S-COV') {
    const o = S.rcmp && REQ_BY[S.rcmp];
    if (!o || o.id === r.id) out.push('Put the covering requirement beside this one with “Compare with”, then record.');
    else { const od = rdStand(S, o); if (od && RD_REMOVES(od.outcome)) out.push(o.id + ' is itself being removed, so it cannot cover this one.'); }
  }
  const bl = trBase(r.id);
  if (bl && (kind === 'reword' || RD_REMOVES(kind)) && !TR_CR_RE.test(trCrNorm(f.cr))) out.push('This requirement is in baseline ' + bl.bl + '. Write the change request number that covers the change (like CR-2041).');
  if ((kind === 'reword' || kind === 'drop' || kind === 'notreq' || f.reason === 'S-OTH') && note.length < RD_NOTE_MIN) out.push('Write why, in at least ' + RD_NOTE_MIN + ' characters.');
  if (kind === 'ask' && (f.q || '').trim().length < RD_ASK_MIN) out.push('Write the question for the owner.');
  return out;
}
