/* ---------- seeded team activity: who decided what before you opened the project ---------- */
const NOTE_BANK = [
  'Owner confirmed the strictest value in the review thread.', 'The parent requirement sets this value; the others are older copies.',
  'Checked against the interface control document. The longer period is the one tested.', 'The two owners agreed on one value in the weekly sync.',
  'Kept separate: the conditions differ and should not be folded together.', 'Strictest value satisfies every other member, so nothing is lost.'
];
const SEED = (function () {
  const R = rng(777);
  const ri = (a, b) => a + Math.floor(R() * (b - a + 1));
  const pk = (a) => a[Math.floor(R() * a.length)];
  const out = { dec: {}, sign: {}, claims: {}, stale: {}, dispute: {}, sibs: {}, rerun: {}, cat: {} };
  const S0 = Object.assign({}, DEFAULTS);
  const DATES = ['2 Oct', '3 Oct', '5 Oct', '6 Oct', '7 Oct', '8 Oct', '9 Oct'];
  const WHO = { SE: ['Sam Okafor', 'Morgan Hale'], PE: ['Priya Raman'], UX: ['Jordan Ellis'], NU: ['Casey Whitfield'], OWN: ['Morgan Hale'], ADJ: ['Morgan Hale'] };
  const REASON_FOR = { stringent: 'R-STR', least: 'R-OWN', median: 'R-OWN', member: 'R-PAR', own: 'R-OTH', ai: 'R-STR' };
  const handIds = HAND.map((c) => c.id);
  const gen = CLUSTERS.filter((c) => handIds.indexOf(c.id) < 0);
  const decided = [];
  gen.forEach((c) => {
    const r = R();
    const cat = r < 0.18 ? 'approved' : r < 0.32 ? 'review' : r < 0.39 ? 'decided' : 'open';
    if (cat === 'open') return;
    if (c.members.length > 12) return;
    const ms = c.members;
    const z = R();
    let outcome = 'link', strategy = '';
    if (c.kind === 'equiv') { outcome = z < 0.92 ? 'merge' : 'reject'; const y = R(); strategy = y < 0.6 ? 'stringent' : y < 0.8 ? 'member' : 'ai'; }
    else if (c.kind === 'varV') { outcome = z < 0.5 ? 'merge' : z < 0.78 ? 'link' : 'escalate'; const y = R(); strategy = y < 0.6 ? 'stringent' : y < 0.75 ? 'member' : y < 0.85 ? 'ai' : y < 0.93 ? 'median' : 'least'; }
    else if (c.kind === 'modal') { outcome = z < 0.4 ? 'merge' : z < 0.7 ? 'link' : 'escalate'; strategy = 'stringent'; }
    else if (c.kind === 'subs') { outcome = z < 0.6 ? 'link' : 'supersede'; }
    else if (c.kind === 'cond') { outcome = 'link'; }
    else { outcome = z < 0.9 ? 'escalate' : 'reject'; }
    const res = { outcome, strat: strategy || 'stringent', member: ms[ri(0, ms.length - 1)].id, side: 'upper', own: '', aiText: '' };
    let ev = evaluate(S0, c, ms, res);
    if (outcome === 'merge' && (ev.err || ev.blocks)) { res.outcome = outcome = c.kind === 'equiv' ? 'reject' : 'link'; ev = evaluate(S0, c, ms, res); }
    const by = pk(WHO.SE), at = pk(DATES);
    let text = outcome === 'merge' ? ev.text : '';
    const revs = [];
    let share = null;
    if (outcome === 'merge' && strategy === 'ai') {
      revs.push({ rev: 'R2', how: 'ai', text: c.aiDraft, by: 'AI draft', at });
      if (R() < 0.5) {
        const ed = text.replace(' at least ', ' a minimum of ').replace(' within ', ' in ');
        if (ed !== text) { text = ed; }
      }
      share = aiShare(c.aiDraft, text);
    }
    const dec = { outcome, strategy: outcome === 'merge' ? strategy : '', member: res.member, text, newWording: outcome === 'merge' && ev.newWording, weakening: outcome === 'merge' && ev.weakening, covers: outcome === 'merge' ? ev.covers : [], kept: outcome === 'merge' ? ev.kept : [], reason: outcome === 'merge' ? REASON_FOR[strategy] : outcome === 'reject' ? 'R-NOT' : outcome === 'link' ? 'R-SEP' : 'R-OWN', note: '', by, lens: 'SE', at, rev: 'R3', vs: vsAI(c, res), share, revs: revs.concat([{ rev: 'R3', how: 'human', text, by, at, note: '' }]) };
    if (R() < 0.4 || dec.weakening || ev.noteWhy) { dec.note = pk(NOTE_BANK); dec.revs[dec.revs.length - 1].note = dec.note; }
    if (dec.reason === 'R-OTH' && !dec.note) dec.note = pk(NOTE_BANK);
    out.dec[c.id] = dec;
    out.cat[c.id] = cat;
    decided.push(c);
    const req = required(c, dec);
    const slots = SLOT_KEYS.filter((k) => req[k] === 'req');
    const picked = SLOT_KEYS.filter((k) => req[k] === 'sample'); /* slots the 20% sample asks for: signed below in approved clusters without drawing random numbers, so the seeded data stays as it was */
    const sg = {};
    let take = cat === 'approved' ? slots : cat === 'review' ? slots.slice(0, Math.max(1, Math.min(slots.length - 1, ri(1, slots.length - 1)))) : [];
    if (cat === 'review' && slots.length < 2) take = [];
    take.forEach((k) => { let who = pk(WHO[k]); if (['SE', 'PE', 'UX', 'NU'].indexOf(k) >= 0 && who === by) who = WHO.SE.find((x) => x !== by); sg[k] = { by: who, at: pk(DATES), rev: 'R3' }; });
    if (cat === 'approved') picked.forEach((k, i) => { sg[k] = { by: WHO[k][0], at: DATES[(i + 3) % DATES.length], rev: 'R3' }; });
    out.sign[c.id] = sg;
    if (cat === 'review' && !take.length) out.cat[c.id] = 'decided';
  });
  const inReview = decided.filter((c) => out.cat[c.id] === 'review');
  const inDone = decided.filter((c) => out.cat[c.id] === 'approved' || out.cat[c.id] === 'review');
  const merged = decided.filter((c) => out.dec[c.id].outcome === 'merge');
  const used = {};
  const take = (arr, idxs, fn) => idxs.forEach((i) => { const c = arr[i % Math.max(arr.length, 1)]; if (c && !used[c.id]) { used[c.id] = 1; fn(c); } });
  const DNOTES = [
    'This keeps a looser value than the one the owner confirmed in the thread. I do not think it is defensible as written.',
    'The change request is not linked to the record. I cannot sign until it is.',
    'Two requirements that look alike carry different verification methods, and the merge drops one of them.'
  ];
  take(inReview, [1, 5, 9], (c) => { out.dispute[c.id] = { by: 'Priya Raman', lens: 'PE', at: '9 Oct', note: DNOTES[Object.keys(out.dispute).length % 3] }; });
  take(inDone, [3, 8, 14, 20, 26], (c) => { out.stale[c.id] = { req: c.members[0].id, when: '9 Oct', what: 'The source text of ' + c.members[0].id + ' changed in the model after this decision was made.', hash: h32(c.id + 'stale') }; });
  take(merged, [4, 11], (c) => {
    const d = out.dec[c.id];
    const alt = c.members.find((m) => m.text !== d.text) || c.members[0];
    out.sibs[c.id] = [
      { rev: 'R3a', by: 'Sam Okafor', lens: 'SE', at: '9 Oct', text: d.text },
      { rev: 'R3b', by: 'Morgan Hale', lens: 'SE', at: '9 Oct', text: c.aiDraft && c.aiDraft !== d.text ? c.aiDraft : alt.text }
    ];
  });
  const approvedAI = decided.filter((c) => out.cat[c.id] === 'approved' && out.dec[c.id].outcome === 'merge');
  take(approvedAI, [2, 7], (c) => { out.rerun[c.id] = { rev: 'R5-ai', at: '9 Oct', text: c.aiDraft || c.members[c.members.length - 1].text, note: 'A later AI run suggested a different wording. It was not applied because a person already decided.' }; });
  // soft claims on open clusters near the top of the queue
  const openOrder = ORDER.filter((c) => !out.dec[c.id] && c.members.length <= 12);
  [3, 7, 12, 20, 33, 47].forEach((i, k) => { const c = openOrder[i]; if (c) out.claims[c.id] = { by: ['Priya Raman', 'Jordan Ellis', 'Casey Whitfield', 'Priya Raman', 'Jordan Ellis', 'Casey Whitfield'][k], lens: ['PE', 'UX', 'NU', 'PE', 'UX', 'NU'][k], mins: [6, 2, 11, 4, 9, 1][k] }; });
  return out;
})();

/* ---------- revision chain and per-requirement history ---------- */
function chainOf(S, c) {
  const dec = decOf(S, c.id);
  const L = [];
  L.push({ rev: 'R0', kind: 'src', title: 'Source wordings imported', by: 'Import from the model', at: '2 Oct', detail: c.members.length + ' wordings, content hash ' + h32(c.members.map((m) => m.text).join('|')), text: '' });
  L.push({ rev: 'R1', kind: 'mech', title: 'Grouped by the mechanical methods', by: 'Pipeline', at: '2 Oct', detail: 'Combined score ' + c.m.p.toFixed(2) + '. Relationship: ' + REL_LABEL[c.rel].toLowerCase() + '.', text: '' });
  if (c.ai.mode !== 'none') L.push({ rev: 'R2', kind: 'ai', title: c.ai.mode === 'draft' ? 'AI drafted merged wording' : 'AI judged the group', by: 'AI record AIR-' + h32(c.id).slice(0, 4).toUpperCase() + ' (written once, never edited)', at: '2 Oct', detail: c.ai.mode === 'draft' ? '' : c.ai.verdict + ' · ' + c.ai.conf + '% · ' + c.ai.votes, text: c.ai.mode === 'draft' ? c.aiDraft : '' });
  if (dec) {
    dec.revs.forEach((r) => {
      if (r.rev === 'R2' && c.ai.mode === 'draft') return;
      L.push({ rev: r.rev, kind: r.how === 'ai' ? 'ai' : 'human', title: r.how === 'ai' ? 'AI draft taken into the decision' : describeDec(dec) + (dec.outcome === 'merge' && dec.newWording ? ' · new wording' : ''), by: r.by, at: r.at, detail: r.note ? 'Reason: ' + (REASON_NAME[dec.reason] || dec.reason) + '. Note: ' + r.note : 'Reason: ' + (REASON_NAME[dec.reason] || dec.reason) + '.', text: r.text });
    });
  }
  return L;
}
const MARK = {
  src: ['Source', 'width:10px;height:10px;border:2px solid #4F5B66;box-sizing:border-box;display:inline-block', 'background:#F4F6F8;color:#2F3B46;'],
  mech: ['Mechanical', 'width:9px;height:9px;background:#34424F;display:inline-block', 'background:#E4E9ED;color:#2F3B46;'],
  ai: ['AI', 'width:9px;height:9px;background:#8B1F6B;transform:rotate(45deg);display:inline-block', 'background:#F6E4EF;color:#6A1650;'],
  human: ['Person', 'width:10px;height:10px;border-radius:50%;background:#1B6B3A;display:inline-block', 'background:#E1F2E7;color:#14502B;'],
  bot: ['Assistant', 'width:12px;height:10px;border-radius:5px 5px 5px 1px;background:#0B6E99;display:inline-block', 'background:#E3F4FB;color:#0B4F6E;']
};
function reqHistory(S, id) {
  const r = REQ_BY[id];
  const h = [{ when: '2 Oct', text: 'Imported from the model (R0, hash ' + h32(r.text) + ').' }];
  if (!r.cid) { h.push({ when: '2 Oct', text: 'Compared with all others in its allocation by four methods. Nothing similar found.' }); return h; }
  const c = CL_BY[r.cid];
  h.push({ when: '2 Oct', text: 'Placed in ' + c.id + ' by the methods (group score ' + c.m.p.toFixed(2) + ').' });
  const dec = decOf(S, c.id);
  if (c.ai.mode !== 'none') h.push({ when: '2 Oct', text: c.ai.mode === 'draft' ? 'AI drafted merged wording.' : 'AI judged the group: ' + c.ai.verdict + '.' });
  if (dec) h.push({ when: dec.at, text: dec.by + ' decided: ' + describeDec(dec).toLowerCase() + (dec.covers.indexOf(id) >= 0 ? '. This requirement is covered by the result.' : dec.kept.indexOf(id) >= 0 ? '. This requirement was kept separate.' : '.') });
  const st = staleOf(S, c.id);
  if (st) h.push({ when: st.when, text: 'Source changed for ' + st.req + '. The decision is stale.' });
  return h;
}

/* ---------- decision ledger rows ---------- */
function ledgerRows(S, universe) {
  const rows = [];
  universe.forEach((c) => {
    const dec = decOf(S, c.id);
    if (!dec) return;
    const day = parseInt(dec.at, 10) || 10;
    rows.push({ cid: c.id, title: c.title, when: dec.at, day, decision: describeDec(dec), reason: REASON_NAME[dec.reason] || dec.reason, by: dec.by, vs: dec.vs, state: STATUS_LABEL[statusOf(S, c)], note: dec.note, share: dec.share ? dec.share.bucket : '' });
  });
  // requirements decided on their own sit in the same ledger, under their own ID
  rdList(S, '').forEach((x) => {
    const d = x.dec, day = parseInt(d.at, 10) || 10;
    rows.push({ cid: x.r.id, title: x.r.text.length > 70 ? x.r.text.slice(0, 67) + '…' : x.r.text, when: d.at, day, decision: RD_BY[d.outcome].name + (d.cover ? ' (covered by ' + d.cover + ')' : ''), reason: d.outcome === 'ask' ? 'Question for ' + d.to + ': ' + d.q : (RD_REASON_NAME[d.reason] || d.reason), by: d.by, vs: 'One requirement, decided on its own', state: RD_STATUS_LABEL[x.status], note: d.note, share: '' });
  });
  rows.sort((a, b) => b.day - a.day || (a.cid < b.cid ? -1 : 1));
  return rows;
}

/* ---------- the assistant (scripted in this prototype) ---------- */
function groupValues(c, ms) {
  const by = {};
  ms.forEach((m, i) => { const k = m.v === null || m.v === undefined ? (m.cond ? m.cond : 'no number') : fmtVal(c, m.v); (by[k] = by[k] || []).push('M' + (i + 1)); });
  return Object.keys(by).map((k) => k + ' (' + by[k].join(', ') + ')');
}
function assistReply(S, c, ms, intent, blindHidden) {
  const idx = (m) => 'M' + (ms.indexOf(m) + 1);
  const rk = rankedOf(S, c, ms);
  const refs = [c.id].concat(ms.slice(0, 4).map((m) => m.id));
  if (c.aiHeld) return { text: 'I am not used on this group, and I have not read it. ' + c.aiHeld.text + ' Review it from the mechanical results, or ask a teammate.', refs: [c.id] };
  if (intent === 'explain') {
    const vals = groupValues(c, ms);
    const nr = ms.length - rk.length;
    return { text: 'This group has ' + ms.length + ' requirements about ' + c.param.toLowerCase() + ', allocated to ' + c.alloc + '. ' + (c.kind === 'modal' || c.kind === 'subs' || c.kind === 'cond' || c.kind.indexOf('conf') === 0 ? REL_PLAIN[c.rel] : 'The values are ' + joinOr(vals) + '.') + (nr && rk.length ? ' ' + nr + ' of them cannot be ranked because they carry a different condition or no number.' : '') + ' The mechanical methods put them together with a combined score of ' + c.m.p.toFixed(2) + '. Owners involved: ' + joinOr(ms.map((m) => m.owner).filter((x, i, a) => a.indexOf(x) === i)) + '.', refs };
  }
  if (intent === 'why') {
    const bad = c.guards.split('').map((g, i) => (g !== 'p' ? GUARDS[i] + (c.gNotes[i] ? ' (' + c.gNotes[i] + ')' : '') : '')).filter(Boolean);
    const mech = 'It is in ' + LANE_NAME[c.lane] + ' because ' + (c.lane === 'A' ? 'every method agrees and no guard objects.' : c.lane === 'B' ? 'the methods agree on topic but a value, owner or modal verb differs.' : 'the contradiction score is high (' + c.m.contra.toFixed(2) + ').') + (bad.length ? ' Guards that did not pass: ' + bad.join('; ') + '.' : ' Every guard passed.');
    if (blindHidden) return { text: mech + ' You are in blind-first mode, so I am holding back what the AI judged until you record your own first read.', refs };
    return { text: mech + (c.ai.mode === 'none' ? ' No AI was used on this group.' : c.ai.mode === 'draft' ? ' The AI only drafted merged wording.' : ' The AI judged it ' + c.ai.verdict + ' at ' + c.ai.conf + '% (' + c.ai.votes + ').'), refs };
  }
  if (intent === 'prior') {
    const same = CLUSTERS.filter((x) => x.id !== c.id && x.famKey === c.famKey && decOf(S, x.id)).slice(0, 3);
    const lines = same.map((x) => { const d = decOf(S, x.id); return x.id + ' (' + x.title + '): ' + d.by + ' on ' + d.at + ' chose ' + describeDec(d).toLowerCase() + '. Reason: ' + (REASON_NAME[d.reason] || d.reason) + '.'; });
    const dirLine = c.dir === 'lower' || c.dir === 'higher' ? ' For this parameter the stricter direction is "' + (dirEff(S, c) === 'higher' ? 'higher' : 'lower') + ' is stricter", set by Morgan Hale.' : '';
    return { text: lines.length ? 'Earlier decisions on the same parameter: ' + lines.join(' ') + dirLine : 'I found no earlier decision on this parameter.' + dirLine, refs: refs.concat(same.map((x) => x.id)) };
  }
  if (intent === 'compare') {
    if (rk.length < 2) return { text: 'Fewer than two members can be ranked, so there is no strictest and weakest to compare. I can still show how the wordings differ in the Compare cards above.', refs };
    const a = rk[0].m, b = rk[rk.length - 1].m;
    return { text: idx(a) + ' (' + a.id + ', ' + a.owner + ') is the strictest and ' + idx(b) + ' (' + b.id + ', ' + b.owner + ') the weakest. ' + (a.v !== null && b.v !== null && a.v !== b.v ? 'The difference is the value: ' + fmtVal(c, a.v) + ' against ' + fmtVal(c, b.v) + '.' : 'The difference is in the wording, not the value.'), quotes: [[idx(a), a.text], [idx(b), b.text]], refs: [a.id, b.id] };
  }
  if (intent === 'draft') {
    if (!rk.length || !c.aiDraft) return { text: 'I cannot draft one wording for this group. ' + (rk.length ? '' : 'No member can be ranked, and I will not merge different conditions on my own. ') + 'You can write your own wording in the Resolve panel.', refs };
    const s = rk[0].m;
    return { text: 'Here is a draft built from the strictest member (' + idx(s) + '). It is only a draft. Nothing is saved until you choose it and record the decision.', draft: c.aiDraft, refs: [s.id] };
  }
  const mm = c.m;
  return { text: 'The mechanical result rests on four readings: character match ' + mm.fuzzy.toFixed(2) + ', keyword overlap ' + mm.tfidf.toFixed(2) + ', meaning ' + mm.embed.toFixed(2) + ' and a cross-check of ' + mm.cross.toFixed(2) + '. The direction of implication is ' + mm.eAB.toFixed(2) + ' one way and ' + mm.eBA.toFixed(2) + ' the other, with a contradiction score of ' + mm.contra.toFixed(2) + '. ' + c.mNote + ' What it cannot see: scores are uncalibrated until a gold set exists, and a high score does not prove two requirements mean the same thing.', refs };
}
const CHIPS = [['explain', 'Explain this group'], ['why', 'Why was it flagged?'], ['prior', 'Any earlier decisions?'], ['compare', 'Compare strictest and weakest'], ['draft', 'Draft a wording'], ['defend', 'Defend the mechanical result']];
function intentOf(t) {
  t = t.toLowerCase();
  if (/draft|write|author|word/.test(t)) return 'draft';
  if (/prior|earlier|before|history|previous/.test(t)) return 'prior';
  if (/compare|differ|strict|diff/.test(t)) return 'compare';
  if (/why|flag|lane|guard/.test(t)) return 'why';
  if (/defend|mechanic|score|method/.test(t)) return 'defend';
  if (/explain|what|about|summar|group/.test(t)) return 'explain';
  return '';
}
