/* ---------- wording tokens (diff and highlight) ---------- */
const SLOT_STYLE = {
  num: 'background:#FFE0AD;color:#3F2400;box-shadow:inset 0 -2px 0 #B35A00;',
  unit: 'background:#FFE0AD;color:#3F2400;box-shadow:inset 0 -2px 0 #B35A00;',
  modal: 'background:#D5E3FF;color:#0B2A6B;outline:1px solid #6F96E3;',
  neg: 'background:#FFD3CE;color:#6E100A;font-weight:700;',
  cond: 'background:#E8DEFF;color:#341C85;border-bottom:2px dotted #341C85;'
};
function normTok(t) { return t.toLowerCase().replace(/[.,;:]+$/, ''); }
function kindOf(t, prev) {
  const w = normTok(t);
  if (/^(shall|should|will|may|must)$/.test(w)) return 'modal';
  if (/^(not|never|without)$/.test(w)) return 'neg';
  if (/^(upon|when|if|while|unless|where|after|before|during)$/.test(w)) return 'cond';
  if (/^[≥≤<>]?\d[\d,.]*$/.test(w)) return 'num';
  if (prev === 'num' && /^(s|sec|seconds?|ms|milliseconds?|vdc|v|hz|days?|%|percent|kg|kilograms?|m|meters?|degrees?|fault|records?)$/.test(w)) return 'unit';
  return null;
}
function diffTokens(textA, textB) {
  const A = textA.split(' ').filter(Boolean), B = textB.split(' ').filter(Boolean);
  const n = A.length, m = B.length;
  const L = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--) for (let j = m - 1; j >= 0; j--) L[i][j] = normTok(A[i]) === normTok(B[j]) ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
  const keepA = new Set(), keepB = new Set();
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (normTok(A[i]) === normTok(B[j])) { keepA.add(i); keepB.add(j); i++; j++; }
    else if (L[i + 1][j] >= L[i][j + 1]) i++; else j++;
  }
  const paint = (T, keep) => { let prev = null; return T.map((t, k) => { const kind = kindOf(t, prev); prev = kind; const changed = kind && !keep.has(k); return { t, kind: kind || '', style: 'padding:1px 3px;border-radius:3px;' + (kind ? SLOT_STYLE[kind] : '') + (changed ? 'text-decoration:underline;text-decoration-thickness:2px;text-underline-offset:3px;' : '') }; }); };
  return { a: paint(A, keepA), b: paint(B, keepB) };
}
function paintOnly(text) {
  let prev = null;
  return text.split(' ').filter(Boolean).map((t) => { const kind = kindOf(t, prev); prev = kind; return { t, style: 'padding:1px 3px;border-radius:3px;' + (kind ? SLOT_STYLE[kind] : '') }; });
}
function editRatio(a, b) {
  const A = a.split(/\s+/).filter(Boolean), B = b.split(/\s+/).filter(Boolean);
  const n = A.length, m = B.length;
  const D = Array.from({ length: n + 1 }, (_, i) => [i].concat(new Array(m).fill(0)));
  for (let j = 0; j <= m; j++) D[0][j] = j;
  for (let i = 1; i <= n; i++) for (let j = 1; j <= m; j++) D[i][j] = Math.min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (normTok(A[i - 1]) === normTok(B[j - 1]) ? 0 : 1));
  return D[n][m] / Math.max(n, m, 1);
}
function aiShare(aiText, finalText) {
  const r = editRatio(aiText, finalText);
  const bucket = r === 0 ? 'as-is' : r <= 0.15 ? 'light edit' : r <= 0.4 ? 'heavy edit' : 'rewritten';
  return { r, pct: Math.round(r * 100), bucket };
}

/* ---------- policy ---------- */
const sampled = (cid, k) => h32(cid + k) % 5 === 0;
function required(c, dec, forecastNew) {
  const nw = dec ? !!dec.newWording : !!forecastNew;
  const out = { SE: 'none', PE: 'none', UX: 'none', NU: 'none', OWN: 'none', ADJ: 'none' };
  if (c.lane === 'A') {
    out.SE = 'req';
    if (nw) { out.PE = 'req'; out.UX = 'req'; out.NU = 'req'; } else if (sampled(c.id, 'PE')) out.PE = 'sample';
  } else if (c.lane === 'B') {
    out.SE = 'req'; out.PE = 'req';
    if (nw) { out.UX = 'req'; out.NU = 'req'; } else if (sampled(c.id, 'NU')) out.NU = 'sample';
    if (c.crossOwner) out.OWN = 'req';
  } else { out.SE = 'req'; out.PE = 'req'; out.OWN = 'req'; out.ADJ = 'req'; }
  if (c.baselined) out.PE = 'req';
  if (dec && dec.weakening) { out.OWN = 'req'; out.PE = 'req'; }
  return out;
}
const SLOT_KEYS = ['SE', 'PE', 'UX', 'NU', 'OWN', 'ADJ'];

/* ---------- state getters (seed first, your changes on top) ---------- */
function decOf(S, cid) { return S.dec[cid] !== undefined ? S.dec[cid] : (SEED.dec[cid] || null); }
function signOf(S, cid) { return S.sign[cid] !== undefined ? S.sign[cid] : (SEED.sign[cid] || {}); }
function claimOf(S, cid) { return S.claims[cid] !== undefined ? S.claims[cid] : (SEED.claims[cid] || null); }
function staleOf(S, cid) { return S.stale[cid] !== undefined ? S.stale[cid] : (SEED.stale[cid] || null); }
function disputeOf(S, cid) { return S.objections[cid] !== undefined ? S.objections[cid] : (SEED.dispute[cid] || null); }
function sibsOf(S, cid) { return S.sib[cid] !== undefined ? S.sib[cid] : (SEED.sibs[cid] || null); }
function membersOf(S, c) { const p = S.peeled[c.id] || []; return p.length ? c.members.filter((m) => p.indexOf(m.id) < 0) : c.members; }
function dirEff(S, c) { return S.dirs[c.famKey] || c.dir; }
function resOf(S, c) { return Object.assign({ outcome: c.actions[0][0], strat: 'stringent', member: '', side: '', own: '', aiText: '', reason: '', note: '', ack: false, reopen: '' }, S.res[c.id] || {}); }
function signState(S, c, dec) {
  const req = required(c, dec);
  const sg = signOf(S, c.id);
  const slots = SLOT_KEYS.filter((k) => req[k] !== 'none');
  const have = slots.filter((k) => sg[k]);
  return { req, sg, slots, have, missing: slots.filter((k) => !sg[k]), done: slots.length > 0 && have.length === slots.length };
}
function statusOf(S, c) {
  if (staleOf(S, c.id)) return 'stale';
  if (disputeOf(S, c.id)) return 'dispute';
  if (sibsOf(S, c.id)) return 'siblings';
  const dec = decOf(S, c.id);
  if (dec) { const q = signState(S, c, dec); return q.done ? 'approved' : q.have.length > 0 ? 'review' : 'decided'; }
  if (membersOf(S, c).length > 12) return 'oversized';
  if (claimOf(S, c.id)) return 'claimed';
  return 'open';
}
const STATUS_LABEL = { open: 'Suggested', claimed: 'Claimed', decided: 'Decided', review: 'In review', approved: 'Approved', dispute: 'Disagreement', stale: 'Stale', siblings: 'Two versions', oversized: 'Too big' };
const STATUS_STYLE = {
  open: 'background:#FFFFFF;color:#2F3B46;border:1px dashed #6B7782;', claimed: 'background:#EDE8F8;color:#3A2A80;', decided: 'background:#E8F0FD;color:#123C8C;', review: 'background:#E8F0FD;color:#123C8C;',
  approved: 'background:#E1F2E7;color:#14502B;', dispute: 'background:#FDE3E0;color:#7A1510;', stale: 'background:#FFF0D2;color:#6B3D00;', siblings: 'background:#EDE8F8;color:#3A2A80;', oversized: 'background:#FDE3E0;color:#7A1510;'
};
const CHIP = 'font-size:12px;font-weight:600;padding:2px 8px;border-radius:4px;white-space:nowrap;';
function attention(st) { return st === 'dispute' || st === 'stale' || st === 'siblings' || st === 'oversized'; }

/* ---------- ranking and the six strategies ---------- */
function rankOf(S, c, m) {
  if (c.kind === 'modal') return MODAL_RANK[modalOf(m.text)];
  if (c.kind === 'subs') return m.xr;
  if (m.v === null || m.v === undefined || !m.rankable) return null;
  if (c.dir === 'none') return null;
  return dirEff(S, c) === 'higher' ? m.v : -m.v;
}
function rankedOf(S, c, ms) { return ms.map((m) => ({ m, r: rankOf(S, c, m) })).filter((x) => x.r !== null).sort((a, b) => b.r - a.r); }
function unitCat(u) {
  u = u.toLowerCase();
  if (/^(ms|milliseconds?|s|seconds?)$/.test(u)) return 'time';
  if (/^days?$/.test(u)) return 'days';
  if (/^(kg|kilograms?)$/.test(u)) return 'mass';
  if (/^(m|meters?)$/.test(u)) return 'length';
  if (/records?$/.test(u)) return 'records';
  return u;
}
function strategyAvail(S, c, ms, rk) {
  const none = rk.length === 0;
  return {
    stringent: none ? 'No member can be ranked.' : '',
    least: none ? 'No member can be ranked.' : rk.length < 2 || rk[0].r === rk[rk.length - 1].r ? 'All ranked members are equal, so there is nothing to weaken.' : '',
    median: rk.length < 3 ? 'Needs at least three ranked members. This group has ' + rk.length + '.' : '',
    member: '',
    own: '',
    ai: c.aiDraft ? '' : 'The AI declined to draft wording for this group.'
  };
}
function evaluate(S, c, ms, res) {
  const rk = rankedOf(S, c, ms);
  const maxR = rk.length ? rk[0].r : null;
  const out = { text: '', chosen: null, err: '', guards: [], covers: [], kept: [], newWording: false, weakening: false, blocks: 0, warns: 0, rk, noteWhy: '', strictId: rk.length ? rk[0].m.id : '', sideOpts: [] };
  const add = (name, st, note) => { out.guards.push({ name, st, note }); if (st === 'block') out.blocks++; if (st === 'warn') out.warns++; };
  const merging = res.outcome === 'merge';
  if (ms.length > 12) add('Group size', 'block', ms.length + ' members is too many to resolve as one group. Peel members out until 12 or fewer remain.');
  const owners = []; ms.forEach((m) => { if (owners.indexOf(m.owner) < 0) owners.push(m.owner); });
  if (owners.length > 1) add('Owners', 'warn', owners.join(', ') + ' all own members. Their approval is added to sign-off.'); else add('Owners', 'pass', 'One owner (' + owners[0] + ').');
  if (c.baselined) add('Baseline', c.cr ? 'warn' : 'block', c.cr ? 'A member is baselined. Change request ' + c.cr + ' is linked and the PE must sign.' : 'A member is baselined and no change request is linked.');
  if (!merging) {
    add('Wording', 'info', 'This outcome changes no wording, so the number, unit, shall and not checks do not apply.');
    const ovr = overrodeAI(c, res);
    if (res.outcome === 'reject' && c.lane !== 'A') out.noteWhy = 'you are rejecting a suggestion in lane ' + c.lane;
    else if (ovr) out.noteWhy = ovr;
    return out;
  }
  // choose the surviving wording
  let sel = null;
  const sorted = rk;
  if (res.strat === 'stringent') sel = sorted.length ? { m: sorted[0].m } : { err: 'No member can be ranked, so there is no strictest wording. Use your own wording or keep them separate.' };
  else if (res.strat === 'least') sel = sorted.length ? { m: sorted[sorted.length - 1].m } : { err: 'No member can be ranked.' };
  else if (res.strat === 'median') {
    const k = sorted.length;
    if (k < 3) sel = { err: 'Median needs at least three ranked members. This group has ' + k + '.' };
    else if (k % 2) sel = { m: sorted[(k - 1) / 2].m };
    else {
      out.sideOpts = [{ k: 'upper', m: sorted[k / 2 - 1].m, label: 'Stricter middle' }, { k: 'lower', m: sorted[k / 2].m, label: 'Looser middle' }];
      const pick = out.sideOpts.find((o) => o.k === res.side);
      sel = pick ? { m: pick.m } : { err: 'There is an even number of ranked members, so no single middle exists. Pick the stricter or the looser middle member.' };
    }
  } else if (res.strat === 'member') {
    const m = ms.find((x) => x.id === res.member);
    sel = m ? { m } : { err: 'Pick the member whose wording survives.' };
  } else if (res.strat === 'own') {
    sel = res.own.trim() ? { text: res.own.trim() } : { err: 'Write the wording you want to keep.' };
  } else {
    const t = (res.aiText || c.aiDraft || '').trim();
    sel = t ? { text: t } : { err: 'The AI declined to draft wording for this group.' };
  }
  if (sel.err) { out.err = sel.err; add('Wording', 'block', sel.err); return out; }
  out.chosen = sel.m || null;
  out.text = sel.m ? sel.m.text : sel.text;
  out.newWording = res.strat === 'own' || res.strat === 'ai';
  const text = out.text;
  // numbers and units
  const known = []; ms.forEach((m) => { if (m.v !== null && m.v !== undefined) known.push(m.v); (m.alts || []).forEach((a) => known.push(a)); });
  const qs = quantities(text);
  const memberHasQ = ms.some((m) => quantities(m.text).length > 0);
  if (!out.newWording) add('Numbers preserved', 'pass', qs.length ? qs.map((q) => q.raw).join(', ') + ' comes word for word from ' + (out.chosen ? out.chosen.id : 'a member') + '.' : 'No numbers involved.');
  else if (memberHasQ && !qs.length) add('Numbers preserved', 'block', 'Your wording has no number, but the members carry ' + joinOr(known.filter((x, i) => known.indexOf(x) === i).map((x) => fmtVal(c, x))) + '.');
  else {
    const bad = qs.filter((q) => !known.some((k) => Math.abs(k - q.n) < 1e-9));
    if (bad.length) add('Numbers preserved', 'warn', bad.map((q) => q.raw).join(', ') + ' appears in no member. Needs a note and the owner\'s confirmation.');
    else add('Numbers preserved', 'pass', qs.length ? qs.map((q) => q.raw).join(', ') + ' matches a member value.' : 'No numbers involved.');
    if (bad.length) out.numberWarn = true;
  }
  const cats = []; ms.forEach((m) => quantities(m.text).forEach((q) => { const u = unitCat(q.unit); if (cats.indexOf(u) < 0) cats.push(u); }));
  const tcats = []; qs.forEach((q) => { const u = unitCat(q.unit); if (tcats.indexOf(u) < 0) tcats.push(u); });
  if (cats.length > 1) add('Units compatible', 'block', 'Members use different kinds of unit (' + cats.join(' and ') + '). A person must convert them first.');
  else if (tcats.some((u) => cats.length && cats.indexOf(u) < 0)) add('Units compatible', 'block', 'Your wording uses ' + tcats.join(', ') + ', the members use ' + cats.join(', ') + '.');
  else add('Units compatible', 'pass', cats.length ? 'All in ' + cats[0] + (ms.some((m) => /second/.test(m.text)) && ms.some((m) => /millisecond|\bms\b/.test(m.text)) ? '. Seconds and milliseconds convert exactly.' : '.') : 'No units involved.');
  // modal and negation
  const mx = Math.max.apply(null, ms.map((m) => MODAL_RANK[modalOf(m.text)]));
  const mc = modalOf(text);
  if (!mc) add('Shall / should / will', 'block', 'The wording has no shall, should or will.');
  else if (MODAL_RANK[mc] < mx) add('Shall / should / will', 'warn', 'Weakening: "' + mc + '" replaces a stronger "shall" in at least one member.');
  else add('Shall / should / will', 'pass', 'Keeps "' + mc + '".');
  const negs = ms.map((m) => negOf(m.text));
  if (negs.some((x) => x !== negs[0])) add('Negation preserved', 'block', 'Members disagree on "not". That is a conflict, not a wording choice.');
  else if (negOf(text) !== negs[0]) add('Negation preserved', 'block', 'Your wording ' + (negOf(text) ? 'adds' : 'drops') + ' a "not" that the members ' + (negs[0] ? 'contain' : 'do not contain') + '.');
  else add('Negation preserved', 'pass', 'Same polarity as every member.');
  // conditions
  const conds = ms.filter((m) => m.cond).map((m) => m.cond);
  const nonRank = ms.filter((m) => !rk.some((x) => x.m.id === m.id));
  if (rk.length === 0 && conds.length) {
    const miss = conds.filter((cd) => text.toLowerCase().indexOf(cd.toLowerCase()) < 0);
    if (miss.length) add('Conditions kept', 'block', 'Your wording leaves out: ' + miss.join('; ') + '.'); else add('Conditions kept', 'pass', 'Names all ' + conds.length + ' conditions.');
  } else if (nonRank.length) add('Conditions kept', 'info', nonRank.length + ' member' + (nonRank.length > 1 ? 's' : '') + ' cannot be ranked (' + nonRank.map((m) => m.id).join(', ') + '). They stay separate and are linked as related.');
  else add('Conditions kept', 'pass', 'No member carries a different condition.');
  // weakening
  let rText = null;
  if (out.newWording) {
    if (c.kind === 'modal') rText = MODAL_RANK[mc];
    else if (c.kind !== 'subs' && qs.length && known.length && c.dir !== 'none') rText = dirEff(S, c) === 'higher' ? qs[0].n : -qs[0].n;
  } else if (out.chosen) rText = rankOf(S, c, out.chosen);
  out.weakening = rText !== null && maxR !== null && rText < maxR - 1e-9;
  const strict = rk.length ? rk[0].m : null;
  add('Weakening', out.weakening ? 'warn' : 'pass', out.weakening ? 'Looser than ' + (strict ? strict.id : 'the strictest member') + (strict && strict.v !== null ? ' (' + fmtVal(c, strict.v) + ')' : '') + '. Needs the owners, the PE and a note.' : 'Not looser than any ranked member.');
  if (out.newWording) {
    const shalls = (text.match(/\bshall\b/gi) || []).length;
    if (shalls > 1) add('One thought', 'warn', 'The wording has ' + shalls + ' "shall"s. One requirement should state one thing.');
    const known2 = new Set(); ms.forEach((m) => m.text.toLowerCase().split(/[^a-z0-9]+/).forEach((w) => known2.add(w)));
    const novel = text.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 3 && !known2.has(w) && !/^\d/.test(w));
    if (novel.length >= 2) add('No invented content', 'warn', 'Words in no member: ' + novel.slice(0, 5).join(', ') + '. Check they are intended.'); else add('No invented content', 'pass', 'Every term appears in a member.');
  }
  out.covers = rk.length ? rk.map((x) => x.m.id) : ms.map((m) => m.id);
  out.kept = ms.filter((m) => out.covers.indexOf(m.id) < 0).map((m) => m.id);
  const ovr = overrodeAI(c, res);
  if (res.strat === 'least' || res.strat === 'median' || res.strat === 'own') out.noteWhy = 'you chose ' + STRATS.find((s) => s.k === res.strat).short;
  else if (out.weakening) out.noteWhy = 'this choice weakens the requirement';
  else if (out.numberWarn) out.noteWhy = 'a number in your wording is in no member';
  else if (ovr) out.noteWhy = ovr;
  return out;
}
function overrodeAI(c, res) {
  const a = c.ai;
  if (a.mode === 'judge' && /^(VARIANT|CONFLICT)/.test(a.verdict) && res.outcome === 'merge') return 'the AI judged these a ' + a.verdict.toLowerCase() + ' and you are merging them';
  if (a.mode === 'judge' && /^SUBSUMES/.test(a.verdict) && res.outcome === 'reject') return 'you are rejecting a subsumption the AI found';
  if (a.mode === 'draft' && res.outcome === 'reject') return 'you are rejecting a merge the AI drafted';
  return '';
}
function vsAI(c, res) {
  if (c.ai.mode === 'none') return 'No AI';
  return overrodeAI(c, res) ? 'Overrode AI' : 'Agreed with AI';
}
function canRecord(S, c, ev, res, st, person, blindPending) {
  if (person.role === 'observer') return 'Observers can read but not decide.';
  if (S.preview) return 'You are previewing another lens. Switch back to decide.';
  if ((S.liveVer[c.id] || 0) > (S.openVer[c.id] || 0)) return 'This cluster changed after you opened it. Reload it first so you decide on what is current.';
  if (st === 'stale') return 'The source changed after the last decision. Reopen it first.';
  if (st === 'dispute') return 'A lens has objected. The adjudicator must resolve that first.';
  if (st === 'siblings') return 'Two edits were made at once. Pick one version first.';
  if (decOf(S, c.id)) return 'Already decided. Reopen it to change it.';
  if (blindPending) return 'Blind-first is on. Record your own first impression above before you decide.';
  if (ev.blocks) return 'A guard blocks this choice: ' + ev.guards.filter((g) => g.st === 'block')[0].note;
  if (c.lane !== 'A' && !res.ack) return 'Tick the box to confirm you read the wordings and the guard results.';
  if (!res.reason) return 'Choose a reason code.';
  if (ev.noteWhy && res.note.trim().length < 12) return 'A note of at least 12 characters is required because ' + ev.noteWhy + '.';
  if (res.reason === 'R-OTH' && res.note.trim().length < 12) return 'The reason "Other" needs a note of at least 12 characters.';
  return '';
}
function describeDec(dec) {
  if (!dec) return '';
  const base = ACTION_LABEL[dec.outcome] || dec.outcome;
  if (dec.outcome === 'merge' && dec.strategy) return 'Merged · ' + STRATS.find((s) => s.k === dec.strategy).short;
  return base;
}
