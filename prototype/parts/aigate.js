/* ---------- AI use: may the text of these requirements go to an AI model at all ----------
   The rules are written in docs/AI_DATA_HANDLING.md and live twice: here, and in reqin/src/reqin/aigate.py for the pipeline. docs/ai_gate_cases.json is
   the one table both are tested against (verify.js runs it here, pytest runs it there), so the two cannot drift apart without a test failing.

   What the gate is: a check that stops this application from sending text the data sheet does not cover, and that refuses everything while the sheet is
   unreviewed, inconsistent or the switch is off. What it is not: a decision about what is allowed (the security and export-control reviewers make that
   and write it into the sheet), and not a wall (the wall is the network rule at the gateway: no route from the model host to the internet, no logging at
   the model host). In this prototype the sample AI answers already exist; the gate hides them for groups held back. In the pipeline the gate runs
   before the call, so no answer is made for those groups. */
const AI_LEVELS = ['none', 'cui', 'exp'];
const AI_RANK = { none: 0, cui: 1, exp: 2 };
const AI_WHERE = ['ours', 'tenant', 'vendor'], AI_LOG = ['none', 'local', 'service'], AI_UNSTATED = ['none', 'withhold'];
const AI_NONE = ['no marking', 'none', 'unmarked', 'public'];
/* The two languages must read a marking the same way, so what counts as a space and as part of a word is written out here and in reqin/src/reqin/aigate.py rather than
   left to each language's own idea of it (they differ: JavaScript's word boundary knows only ASCII letters, Python's knows every alphabet; their spaces differ too).
   A space is any Unicode space, including the non-breaking one and the control characters 1C to 1F and 85. Part of a word is any letter or digit of any alphabet, or _ .
   So a letter from another alphabet stuck to a marking word ("cuié") makes it a word this table does not know, and an unknown marking is never sent.
   tests/test_aigate_page.py in reqin feeds both languages many thousands of odd markings and requires the same answer. */
const AI_SP = '\\t-\\r\\x1c-\\x1f \\x85\\xa0\\u1680\\u2000-\\u200a\\u2028\\u2029\\u202f\\u205f\\u3000';
const AI_RE_SP_ENDS = new RegExp('^[' + AI_SP + ']+|[' + AI_SP + ']+$', 'g'), AI_RE_SP_RUN = new RegExp('[' + AI_SP + ']+', 'g');
const aiWords = (alts) => new RegExp('(?:^|[^\\p{L}\\p{N}_])(?:' + alts + ')(?![\\p{L}\\p{N}_])', 'u');
const AI_RE_CLASSIFIED = aiWords('top secret|secret|classified|sci'), AI_RE_EXPORT = aiWords('itar|ear\\p{Nd}*|expt|export'), AI_RE_CUI = aiWords('cui|controlled unclassified');
const aiTrim = (x) => String(x).replace(AI_RE_SP_ENDS, '');   // the same ends-of-text rule as a marking, so a model name or a reviewer made only of an odd space is blank in both languages
const aiOwn = (o, k) => typeof k === 'string' && Object.prototype.hasOwnProperty.call(o, k);

/* what a marking says: none, cui, exp, classified, unknown (words this table does not know), unstated (nothing recorded). Not recognised means unknown, and unknown is never sent. */
function aiMarkLevel(text) {
  if (text === null || text === undefined) return 'unstated';
  if (typeof text !== 'string') return 'unknown';
  const t = text.replace(AI_RE_SP_ENDS, '').toLowerCase().replace(/^[\/ ]+/, '').replace(AI_RE_SP_RUN, ' ');
  if (!t) return 'unstated';
  if (AI_RE_CLASSIFIED.test(t)) return 'classified';
  if (AI_RE_EXPORT.test(t)) return 'exp';
  if (AI_RE_CUI.test(t)) return 'cui';
  if (AI_NONE.indexOf(t) >= 0) return 'none';
  return 'unknown';
}
/* the marking of a group is the most restrictive marking of its members */
function aiGroupLevel(levels, unstated) {
  if (!levels.length) return unstated === 'withhold' ? 'unstated' : 'none';
  for (const bad of ['classified', 'unknown']) if (levels.indexOf(bad) >= 0) return bad;
  if (levels.indexOf('unstated') >= 0 && unstated === 'withhold') return 'unstated';
  const known = levels.filter((x) => aiOwn(AI_RANK, x)).map((x) => AI_RANK[x]);
  return known.length ? AI_LEVELS[Math.max.apply(null, known)] : 'none';
}
/* codes, in a fixed order; a sheet with any problem opens nothing and nothing is capped quietly */
function aiSheetProblems(sh) {
  const out = [];
  if (!aiTrim(sh.model)) out.push('model');
  if (AI_WHERE.indexOf(sh.where) < 0 || AI_LOG.indexOf(sh.log) < 0 || AI_LEVELS.indexOf(sh.approved) < 0 || AI_UNSTATED.indexOf(sh.unstated) < 0) out.push('values');
  if (sh.where === 'vendor' && !sh.leaves) out.push('vendor_leaves');
  if (sh.leaves && sh.approved !== 'none') out.push('leaves_marked');
  if (sh.log === 'service' && sh.approved !== 'none') out.push('log_marked');
  if (sh.approved === 'exp' && sh.where !== 'ours') out.push('exp_where');
  if (sh.log !== 'none' && !(typeof sh.days === 'number' && Number.isInteger(sh.days) && sh.days >= 1 && sh.days <= 3650)) out.push('days');
  return out;
}
const aiReviewed = (sh) => !!(aiTrim(sh.reviewed_by || '') && aiTrim(sh.reviewed_at || ''));
const AI_PROBLEM_MEMO = new WeakMap();
const aiProblemsOf = (sh) => { let p = AI_PROBLEM_MEMO.get(sh); if (!p) { p = aiSheetProblems(sh); AI_PROBLEM_MEMO.set(sh, p); } return p; };
const AI_OFF = Object.freeze({ open: false, code: 'off', level: '', detail: [] }), AI_UNREV = Object.freeze({ open: false, code: 'unreviewed', level: '', detail: [] });
/* the first rule that says no wins; levelFn is asked only when the earlier rules have not already said no */
function aiDecide(sh, on, levelFn) {
  if (!on) return AI_OFF;
  if (!aiReviewed(sh)) return AI_UNREV;
  const p = aiProblemsOf(sh);
  if (p.length) return { open: false, code: 'sheet', level: '', detail: p };
  const lvl = levelFn();
  if (lvl === 'classified' || lvl === 'unknown' || lvl === 'unstated') return { open: false, code: lvl, level: lvl, detail: [] };
  if (AI_RANK[lvl] > AI_RANK[sh.approved]) return { open: false, code: 'marking', level: lvl, detail: [] };
  return { open: true, code: 'open', level: lvl, detail: [] };
}
const aiGate = (sh, on, markings) => aiDecide(sh, on, () => aiGroupLevel(markings.map(aiMarkLevel), sh.unstated));

/* ---- the words the page uses ---- */
const AI_WHERE_NAME = { ours: 'On our own servers', tenant: 'In our organisation’s cloud tenant', vendor: 'A vendor’s shared service' };
const AI_LOG_NAME = { none: 'Not kept', local: 'Kept on our servers', service: 'Kept by the service provider' };
const AI_LEVEL_NAME = { none: 'Requirements with no marking only', cui: 'No marking and CUI', exp: 'No marking, CUI and export controlled' };
const AI_LEVEL_SHORT = { none: 'no marking only', cui: 'CUI', exp: 'export controlled' };
const AI_MARK_NAME = { none: 'No marking', cui: 'CUI', exp: 'Export controlled', classified: 'Classified', unknown: 'Marking not recognised', unstated: 'No marking recorded' };
const AI_UNSTATED_NAME = { withhold: 'Keep the group from the AI', none: 'Treat it as no marking' };
const AI_PROBLEM = {
  model: 'Name the model and its version.',
  values: 'One of the answers is not one this page knows. Choose from the lists.',
  vendor_leaves: 'A vendor’s shared service means the text leaves your network. Answer yes to “does text leave your network”.',
  leaves_marked: 'The text leaves your network, so no marked requirement may be approved. Set the highest marking to “no marking only”.',
  log_marked: 'The service provider keeps prompts and answers, so no marked requirement may be approved. Set the highest marking to “no marking only”.',
  exp_where: 'Export-controlled text may only go to a model on your own servers.',
  days: 'Say how many days prompts and answers are kept (1 to 3650).'
};
const AI_HELD = {
  off: 'AI is switched off for this project.',
  unreviewed: 'The AI data sheet has not been reviewed.',
  sheet: 'The AI data sheet has a problem, so nothing goes to the AI until it is fixed.',
  classified: 'A requirement in this group carries a classified marking. It never goes to the AI.',
  unknown: 'A marking in this group is not one this page recognises, so the group is held back until someone sorts it out at the source.',
  unstated: 'A requirement in this group has no marking recorded, and the data sheet says to keep those from the AI.',
  marking: (lvl, sh) => 'This group is marked ' + (lvl === 'cui' ? 'CUI' : AI_MARK_NAME[lvl].toLowerCase()) + ', which is above what the data sheet approves (' + AI_LEVEL_SHORT[sh.approved] + ').'
};
const aiHeldText = (g, sh) => (g.code === 'marking' ? AI_HELD.marking(g.level, sh) : AI_HELD[g.code]);

/* the sheet the sample project starts with: a model on our own servers, nothing leaves, nothing but unmarked requirements approved */
const AI_SHEET_DEFAULT = Object.freeze(DEFAULTS.aiSheet);

/* ---- markings on the sample requirements ----
   The sample has no real markings, so they are made up, the same way every time: most requirements carry none, a few are CUI, fewer export controlled, a
   handful are in words the table does not know, and a few have nothing recorded. The reference clusters the rest of the page is shown with stay unmarked,
   and four clusters are fixed so each kind of hold can be seen. */
const AI_SHOW = { 'CL-025': [1, 'CUI // Basic'], 'CL-037': [0, 'CUI // export controlled'], 'CL-016': [1, 'Company confidential'], 'CL-056': [0, ''] };
const AI_SALT = 'mk6';
const AI_MARKS = (() => {
  const keep = new Set(HAND_IDS), fix = {}, out = {}, shown = new Set(Object.keys(AI_SHOW));
  Object.keys(AI_SHOW).forEach((cid) => { const c = CL_BY[cid]; if (c && c.members[AI_SHOW[cid][0]]) fix[c.members[AI_SHOW[cid][0]].id] = AI_SHOW[cid][1]; });
  const WORDS = { exp: ['CUI // export controlled', 'ITAR', 'EAR99'], cui: ['CUI', 'CUI // Basic'], unknown: ['Company confidential', 'Proprietary'], unstated: [''] };
  REQS.forEach((r) => {
    let t = 'No marking';
    if (aiOwn(fix, r.id)) t = fix[r.id];
    else if (!keep.has(r.id) && !shown.has(r.cid)) {
      /* in a cluster: about one cluster in five has one marked requirement; alone: about one in twenty */
      const c = r.cid ? CL_BY[r.cid] : null, h = trH(c ? c.id : r.id, AI_SALT, 1000);
      const kind = c ? (h < 30 ? 'exp' : h < 150 ? 'cui' : h < 165 ? 'unknown' : h < 172 ? 'unstated' : '') : (h < 8 ? 'exp' : h < 40 ? 'cui' : h < 46 ? 'unknown' : h < 49 ? 'unstated' : '');
      if (kind && (!c || c.members[trH(c.id, AI_SALT + 'w', c.members.length)].id === r.id)) t = WORDS[kind][trH(r.id, AI_SALT + 'x', WORDS[kind].length)];
    }
    out[r.id] = t;
  });
  return out;
})();
const aiMarkOf = (id) => (aiOwn(AI_MARKS, id) ? AI_MARKS[id] : '');
const AI_LV_CACHE = {};
/* the level of a whole cluster (members as the pipeline grouped them, peeled out or not), for each way of reading an empty marking */
function aiClusterLevel(c, unstated) {
  const k = c.id + '|' + unstated;
  if (!aiOwn(AI_LV_CACHE, k)) AI_LV_CACHE[k] = aiGroupLevel(c.members.map((m) => aiMarkLevel(aiMarkOf(m.id))), unstated);
  return AI_LV_CACHE[k];
}
const AI_HELD_CACHE = {};
/* what the gate says about this cluster under the project's switch and data sheet */
const aiGateOf = (S, c) => aiDecide(S.aiSheet, S.aiOn, () => aiClusterLevel(c, S.aiSheet.unstated));
/* the cluster as the AI may be used on it: itself, or itself with every AI answer taken out and the reason given */
function aiCl(S, c) {
  const g = aiGateOf(S, c);
  if (g.open) return c;
  const text = aiHeldText(g, S.aiSheet), k = c.id + '|' + g.code + '|' + g.level + '|' + text;
  if (!aiOwn(AI_HELD_CACHE, k)) AI_HELD_CACHE[k] = Object.assign({}, c, { ai: { mode: 'none', proposal: '', verdict: '', conf: 0, votes: '', why: text, quotes: [] }, aiDraft: '', aiHeld: { code: g.code, level: g.level, text } });
  return AI_HELD_CACHE[k];
}
/* how many groups the gate lets through and how many it holds back, and why */
function aiCounts(S, list) {
  const out = { total: list.length, open: 0, held: 0, by: { off: 0, unreviewed: 0, sheet: 0, classified: 0, unknown: 0, unstated: 0, marking: 0 }, cui: 0, exp: 0 };
  list.forEach((c) => { const g = aiGateOf(S, c); if (g.open) out.open++; else { out.held++; out.by[g.code]++; if (g.code === 'marking') out[g.level]++; } });
  return out;
}
/* requirements by what their marking says */
function aiMarkCounts() {
  const out = { none: 0, cui: 0, exp: 0, classified: 0, unknown: 0, unstated: 0, total: 0 };
  REQS.forEach((r) => { out[aiMarkLevel(aiMarkOf(r.id))]++; out.total++; });
  return out;
}
const AI_COUNT_CACHE = { mk: null };
const aiMarkCountsOnce = () => AI_COUNT_CACHE.mk || (AI_COUNT_CACHE.mk = aiMarkCounts());

/* ---- the sheet as the page edits it, and how a typed sheet is checked ---- */
const aiDraftOf = (sh) => ({ model: sh.model, where: sh.where, leaves: !!sh.leaves, log: sh.log, days: String(sh.days), approved: sh.approved, unstated: sh.unstated, reviewed_by: '' });
function aiSheetFromDraft(d) {
  const n = String(d.days).trim();
  return { model: String(d.model).trim(), where: d.where, leaves: !!d.leaves, log: d.log, days: d.log === 'none' ? 0 : /^\d{1,5}$/.test(n) ? Number(n) : NaN, approved: d.approved, unstated: d.unstated };
}
/* what changed between two sheets, in words, for the record of events */
function aiDiff(a, b) {
  const nm = (f, v) => (f === 'where' ? AI_WHERE_NAME[v] : f === 'log' ? AI_LOG_NAME[v] : f === 'approved' ? AI_LEVEL_SHORT[v] : f === 'unstated' ? AI_UNSTATED_NAME[v] : f === 'leaves' ? (v ? 'yes' : 'no') : String(v));
  return [['model', 'model'], ['where', 'where it runs'], ['leaves', 'text leaves the network'], ['log', 'prompts and answers'], ['days', 'days kept'], ['approved', 'highest marking approved'], ['unstated', 'no marking recorded']]
    .filter(([f]) => a[f] !== b[f]).map(([f, label]) => label + ': ' + nm(f, a[f]) + ' → ' + nm(f, b[f]));
}
/* a short fingerprint of the sheet, written into the record of events with every change, so a saved project whose sheet does not match its record is noticed */
const aiSheetFp = (sh) => h32([sh.model, sh.where, sh.leaves, sh.log, sh.days, sh.approved, sh.unstated, sh.reviewed_by, sh.reviewed_at, sh.entered_by || ''].join('|'));
/* the switch and the sheet as the record of events says they stand (the sample's own sheet and the switch on, until an entry says otherwise) */
function aiFromEvents(events) {
  let on = true, fp = aiSheetFp(DEFAULTS.aiSheet);
  events.forEach((e) => {
    if (e.target !== 'AI use' || typeof e.text !== 'string') return;
    const sw = /^AI use switched (on|off) for the whole project/.exec(e.text); if (sw) on = sw[1] === 'on';
    const f = /\[sheet ([0-9a-f]{8})\]$/.exec(e.text); if (f) fp = f[1];
  });
  return { on, fp };
}
/* a sheet read from a file or from the browser's store: the shape this page writes, or nothing */
function aiSheetOk(sh) {
  return persistPlain(sh) && typeof sh.model === 'string' && sh.model.length <= 120 && AI_WHERE.indexOf(sh.where) >= 0 && typeof sh.leaves === 'boolean' && AI_LOG.indexOf(sh.log) >= 0
    && typeof sh.days === 'number' && Number.isInteger(sh.days) && sh.days >= 0 && sh.days <= 3650 && AI_LEVELS.indexOf(sh.approved) >= 0 && AI_UNSTATED.indexOf(sh.unstated) >= 0
    && ['reviewed_by', 'reviewed_at', 'entered_by'].every((f) => typeof sh[f] === 'string' && sh[f].length <= 120);
}
/* the file the page can write about its AI use: the switch, the sheet, what the gate does, and which groups are held and why. No requirement text. */
function aiUseFile(S, at) {
  const list = CLUSTERS, cnt = aiCounts(S, list), sh = S.aiSheet;
  return {
    format: 'reqin-ai-use/1', saved: at || new Date().toISOString(), project: persistProject(), switch: S.aiOn ? 'on' : 'off',
    sheet: { model: sh.model, where: sh.where, leaves: sh.leaves, log: sh.log, days: sh.days, approved: sh.approved, unstated: sh.unstated, reviewed_by: sh.reviewed_by, reviewed_at: sh.reviewed_at, entered_by: sh.entered_by || '' },
    sheet_problems: aiProblemsOf(sh), reviewed: aiReviewed(sh),
    groups: { total: cnt.total, open: cnt.open, held: cnt.held, held_by: cnt.by },
    requirements_by_marking: (({ total, ...rest }) => rest)(aiMarkCountsOnce()),
    held: list.map((c) => ({ c, g: aiGateOf(S, c) })).filter((x) => !x.g.open).map((x) => ({ cluster: x.c.id, code: x.g.code, level: x.g.level }))
  };
}
