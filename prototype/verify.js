const fs = require('fs');
const html = fs.readFileSync(process.argv[2] || 'project/Main.dc.html', 'utf8');
const sm = html.match(/<script type="text\/x-dc" data-dc-script[^>]*>([\s\S]*?)<\/script>/);
const code = sm[1];
const tm = html.match(/<x-dc>([\s\S]*)<\/x-dc>/)[1].replace(/<helmet>[\s\S]*?<\/helmet>/, '').replace(/<!--[\s\S]*?-->/g, '');
/* ---- parse template ---- */
function parse(src) {
  const root = { t: 'root', kids: [] }, stack = [root];
  const re = /<sc-for\s+([^>]*)>|<\/sc-for>|<sc-if\s+([^>]*)>|<\/sc-if>|\{\{\s*([^}]*?)\s*\}\}|<([a-zA-Z][\w-]*)((?:\s+[\w:-]+(?:="[^"]*")?)*)\s*\/?>/g;
  let m, last = 0;
  const top = () => stack[stack.length - 1];
  while ((m = re.exec(src))) {
    if (m[1] !== undefined) { const list = /list="\{\{\s*([^}]*?)\s*\}\}"/.exec(m[1])[1], as = /as="([^"]+)"/.exec(m[1])[1]; const n = { t: 'for', list, as, kids: [] }; top().kids.push(n); stack.push(n); }
    else if (m[0] === '</sc-for>' || m[0] === '</sc-if>') stack.pop();
    else if (m[2] !== undefined) { const v = /value="\{\{\s*([^}]*?)\s*\}\}"/.exec(m[2])[1]; const n = { t: 'if', v, kids: [] }; top().kids.push(n); stack.push(n); }
    else if (m[3] !== undefined) top().kids.push({ t: 'hole', path: m[3], kind: 'text' });
    else if (m[4]) {
      const attrs = m[5] || '', ar = /([\w:-]+)="([^"]*)"/g; let a;
      while ((a = ar.exec(attrs))) { if (/^hint-placeholder/.test(a[1])) continue; const hm = a[2].match(/\{\{\s*([^}]*?)\s*\}\}/g); if (hm) hm.forEach((h) => top().kids.push({ t: 'hole', path: h.replace(/[{}\s]/g, ''), kind: /^on[A-Z]/.test(a[1]) ? 'fn' : 'attr', attr: a[1] })); }
    }
  }
  return root;
}
const tree = parse(tm);
/* ---- component ---- */
class DCLogic { constructor() { this.state = {}; this.props = { accent: '#1A4DB5', showHints: true }; } setState(o) { Object.assign(this.state, typeof o === 'function' ? o(this.state) : o); } }
const Component = new Function('DCLogic', code + '\nreturn {Component, CLUSTERS, CL_BY, statusOf, DEFAULTS, ORDER, decOf, SEED, PEOPLE, STRATS, REQS, universe, ALLOCS, required, resultsOf, dispositionsOf, veeOf, veeGlyph, VREQ, VLEVELS, VMETHODS, GOLD_REL, GOLD_BY, GOLD_SIZE, GOLD_CUTS, GOLD_GROUPS, goldPop, goldPlan, goldReset, goldNearText, goldNearKw, goldModel, goldTextScore, goldKeywordScore, goldFinal, goldUsable, goldEstimate, goldCellEstimate, goldMeasure, goldOutside, goldNaming, goldAgreement, goldDisputes, goldQueue, goldWants, goldSampleLabels, goldTruth, goldFile, goldWilson, goldKey, REQ_BY, REQ_IX, rdList, rdNear, rdGuards, rdRequired, rdStatus, rdAlone, quantities, negOf, membersOf, trOf, trRemovals, trRowsOf, trImpactOne, trImpactLines, trFile, trCsv, trCell, TR_ITEMS, TR_ITEM_BY, TR_PARENT, TR_CHILD, TR_BL, TR_CSV, TR_TABS, trBase, aiMarkLevel, aiGroupLevel, aiSheetProblems, aiGate, aiDecide, aiReviewed, aiCl, aiGateOf, aiCounts, aiMarkOf, aiMarkCountsOnce, aiSheetFp, aiFromEvents, aiSheetOk, aiUseFile, aiDiff, aiDraftOf, aiSheetFromDraft, aiProblemsOf, aiHeldText, AI_MARKS, AI_PROBLEM, AI_HELD, AI_SHOW, chainCheck, persistCheck, persistFile, persistPick, persistCounts, persistSaid, persistHasWork, persistFingerprint, persistRead, persistWrite, persistClear, persistStore, PERSIST_FORMAT, PERSIST_STORE, PERSIST_KEYS, PERSIST_BY_CLUSTER, PERSIST_BY_REQ, PERSIST_MAX, EV_SEED, RD_BY, SLOT_KEYS, h32};')(DCLogic);
const { CLUSTERS, CL_BY, statusOf, DEFAULTS, ORDER, SEED, PEOPLE, REQS, ALLOCS } = Component;
const issues = new Map(), ifSeen = new Map(), ifTrue = new Map();
let scen = '';
function get(path, scope, fix) {
  const seg = path.split('.');
  let cur;
  if (Object.prototype.hasOwnProperty.call(scope, seg[0])) cur = scope[seg[0]]; else return undefined;
  for (let i = 1; i < seg.length; i++) { if (cur === null || cur === undefined) return undefined; cur = cur[seg[i]]; }
  return cur;
}
function flag(msg) { if (!issues.has(msg)) issues.set(msg, scen); }
function walk(nodes, scope) {
  for (const n of nodes) {
    if (n.t === 'hole') {
      const v = get(n.path, scope);
      if (v === undefined) flag('UNDEFINED ' + n.path);
      else if (n.kind === 'fn' && typeof v !== 'function') flag('NOT FN ' + n.path + ' (' + typeof v + ')');
      else if (n.kind !== 'fn' && (typeof v === 'function' || (typeof v === 'object' && v !== null))) flag('OBJECT/FN IN TEXT ' + n.path + ' [' + n.attr + ']');
    } else if (n.t === 'if') {
      const v = get(n.v, scope);
      if (v === undefined) flag('UNDEFINED(if) ' + n.v);
      ifSeen.set(n.v + '@' + n.kids.length, n);
      if (v) { ifTrue.set(n.v + '@' + n.kids.length, 1); walk(n.kids, scope); }
    } else if (n.t === 'for') {
      const l = get(n.list, scope);
      if (!Array.isArray(l)) { flag('LIST NOT ARRAY ' + n.list); continue; }
      l.forEach((it, i) => { if (i < 12) walk(n.kids, Object.assign({}, scope, { [n.as]: it })); });
    } else walk(n.kids || [], scope);
  }
}
function run(name, setup) {
  scen = name;
  const c = new Component.Component();
  try { setup(c); const v = c.renderVals(); walk(tree.kids, v); return { c, v }; } catch (e) { flag('THROW in ' + name + ': ' + e.message + '\n' + e.stack.split('\n').slice(0, 4).join('\n')); return null; }
}
const find = (pred) => ORDER.find(pred);
const ids = {};
module.exports = { run, find, Component, issues, ifSeen, ifTrue, walk, tree };
if (require.main === module) {
  const base = (c, o) => c.setState(Object.assign({ view: 'overview' }, o || {}));
  run('open', (c) => c.setState({ view: 'open' }));
  run('import-all', (c) => c.setState({ view: 'import' }));
  run('import-pilot', (c) => c.setState({ view: 'import', scopeChoice: 'pilot' }));
  // input layer: every source, every step, every control state
  ['sample', 'sysml', 'reqif', 'table', 'sql', 'doc'].forEach((k) => run('import-' + k, (c) => c.setState({ view: 'import', source: k, impStep: 'map' })));
  run('open drop sample', (c) => c.setState({ view: 'open', drop: 'reqs.reqif' }));
  run('open drop mdzip', (c) => c.setState({ view: 'open', drop: 'project.mdzip', openNote: 'mdzip' }));
  run('verify step', (c) => c.setState({ view: 'import', source: 'doc', impStep: 'verify' }));
  run('verify progress', (c) => c.setState({ view: 'import', source: 'doc', impStep: 'verify', docSel: { 0: true, 3: true }, docVer: { 0: true, 1: true }, docIds: { 3: 'REQ-FCS-0104' }, docFocus: 3 }));
  run('doc map all verified', (c) => c.setState({ view: 'import', source: 'doc', impStep: 'map', docVer: { 0: true, 1: true, 2: true, 3: true, 4: true, 5: true, 6: true, 7: true }, docIds: { 3: 'REQ-FCS-0104' } }));
  run('change editing + yaml', (c) => c.setState({ view: 'import', source: 'table', impStep: 'map', mapEdit: 'baseline', yamlOpen: true, mapOver: { 'table:text': '', 'table:owner': 'IPT' } }));
  run('reqif without allocation', (c) => c.setState({ view: 'import', source: 'reqif', impStep: 'map', yamlOpen: true }));
  run('all mapped, all verified', (c) => c.setState({ view: 'import', source: 'table', impStep: 'map', mapOver: { 'table:baseline': 'IPT' } }));
  PEOPLE.forEach((p) => { ['home', 'overview', 'vee', 'results', 'review', 'explorer', 'methods', 'gold', 'audit', 'policy', 'ai', 'export'].forEach((v) => run(v + '-' + p.k, (c) => base(c, { view: v, person: p.k, chatOpen: v === 'review', glossary: v === 'overview' }))); });
  run('audit-chain', (c) => base(c, { view: 'audit', logTab: 'chain', tamper: true, verified: 'fail:2' }));
  run('audit-chain-ok', (c) => base(c, { view: 'audit', logTab: 'chain', verified: 'ok' }));
  run('home kept restored', (c) => base(c, { view: 'home', keepRestored: { at: '2026-10-14T12:00:00.000Z', counts: { decisions: 1, signoffs: 0, handoffs: 0, labels: 0, events: 0 } }, keepStatus: 'saved', keepAt: '2026-10-14T12:01:02.000Z' }));
  run('home kept off with a bad message', (c) => base(c, { view: 'home', keepStatus: 'off', keepMsg: { bad: true, text: 'x.json was not loaded. It is not a saved project.', notes: ['one', 'two'] } }));
  run('home kept full with a good message', (c) => base(c, { view: 'home', keepStatus: 'full', keepMsg: { bad: false, text: 'Loaded x.json.', notes: ['one'] } }));
  run('home changed in another tab', (c) => base(c, { view: 'home', keepStatus: 'other' }));
  run('home ask to start over', (c) => base(c, { view: 'home', keepAsk: 'start' }));
  run('home ask to load', (c) => base(c, { view: 'home', keepAsk: 'load', keepSummary: ['x.json, saved 2026-10-14 12:00', '2 decisions, 1 sign-off, 0 hand-offs, 0 labels, 3 events', 'The record of events is intact (6 entries).'] }));
  // AI use: every state of the switch and the data sheet, the form, and the review page with a group held back
  { const DS = DEFAULTS.aiSheet, SH = (o) => Object.assign({}, DS, o), ev = (t) => ({ seq: 99, type: 'human', actor: 'Morgan Hale · SE', text: t, target: 'AI use', time: '10:00:00', prev: '', hash: '', payload: '' });
    run('ai off', (c) => base(c, { view: 'ai', aiOn: false, person: 'morgan' }));
    run('ai sheet not reviewed', (c) => base(c, { view: 'ai', aiSheet: SH({ reviewed_by: '', reviewed_at: '' }), person: 'morgan' }));
    run('ai sheet contradicts itself', (c) => base(c, { view: 'ai', aiSheet: SH({ model: ' ', where: 'vendor', leaves: false, log: 'service', days: 0, approved: 'exp' }), person: 'morgan' }));
    run('ai approves CUI', (c) => base(c, { view: 'ai', aiSheet: SH({ approved: 'cui' }), person: 'sam' }));
    run('ai approves export controlled, no marking read as none', (c) => base(c, { view: 'ai', aiSheet: SH({ approved: 'exp', unstated: 'none' }), person: 'lee' }));
    run('ai changing the sheet', (c) => base(c, { view: 'ai', person: 'morgan', aiEdit: Component.aiDraftOf(DS) }));
    run('ai changing the sheet, nothing filled in', (c) => base(c, { view: 'ai', person: 'morgan', aiEdit: Object.assign(Component.aiDraftOf(DS), { model: '', reviewed_by: '', days: 'x', log: 'service', where: 'vendor', approved: 'exp' }) }));
    run('ai with a message and a history', (c) => base(c, { view: 'ai', person: 'morgan', aiMsg: { bad: false, text: 'AI is switched off for the whole project.' }, events: [ev('AI use switched off for the whole project'), ev('AI use switched on for the whole project')] }));
    run('review a group held for CUI', (c) => base(c, { view: 'review', selected: 'CL-025', chatOpen: true }));
    run('review a group held for export control as a reviewer', (c) => base(c, { view: 'review', selected: 'CL-037', chatOpen: true, person: 'priya' }));
    run('review a group with an unknown marking', (c) => base(c, { view: 'review', selected: 'CL-016', chatOpen: true, person: 'casey' }));
    run('review a group with no marking recorded', (c) => base(c, { view: 'review', selected: 'CL-056', person: 'lee' }));
    run('review with AI off', (c) => base(c, { view: 'review', selected: 'CL-001', aiOn: false, chatOpen: true }));
    run('review with AI off, an earlier AI wording chosen', (c) => base(c, { view: 'review', selected: 'CL-001', aiOn: false, res: { 'CL-001': { strat: 'ai', aiText: 'The system shall do something.' } } }));
    run('home with AI off', (c) => base(c, { view: 'home', aiOn: false }));
    run('home with the AI sheet not reviewed', (c) => base(c, { view: 'home', aiSheet: SH({ reviewed_by: '', reviewed_at: '' }) }));
    run('methods with AI off', (c) => base(c, { view: 'methods', aiOn: false }));
  }
  run('explorer-pick', (c) => base(c, { view: 'explorer', xPick: 'REQ-FCS-0312', xFilter: 'open', xAlloc: 'Flight Control' }));
  // every status, every lens preview
  const byStatus = {};
  const S0 = new Component.Component();
  ORDER.forEach((cl) => { const st = statusOf(Object.assign({}, DEFAULTS), cl); (byStatus[st] = byStatus[st] || []).push(cl.id); });
  console.log('status sample ids', JSON.stringify(Object.fromEntries(Object.entries(byStatus).map(([k, v]) => [k, v.slice(0, 3).concat([v.length])]))));
  const probe = ['CL-001', 'CL-042', 'CL-050', 'CL-117', 'CL-201', 'CL-023'].concat(Object.values(byStatus).map((v) => v[0])).concat(Object.values(byStatus).map((v) => v[v.length - 1]));
  [...new Set(probe)].forEach((id) => {
    ['sam', 'priya', 'jordan', 'casey', 'morgan', 'lee'].forEach((p) => run('review ' + id + ' ' + p, (c) => base(c, { view: 'review', selected: id, person: p, chatOpen: p === 'sam', qTab: 'all' })));
    ['SE', 'PE', 'UX', 'NU'].forEach((l) => run('preview ' + id + ' ' + l, (c) => base(c, { view: 'review', selected: id, person: 'morgan', preview: l, qTab: 'all' })));
  });
  // all strategies and outcomes on CL-050 / CL-001 / CL-042
  ['CL-050', 'CL-001', 'CL-042', 'CL-005'].forEach((id) => {
    ['stringent', 'least', 'median', 'member', 'own', 'ai'].forEach((st) => run('strat ' + id + ' ' + st, (c) => base(c, { view: 'review', selected: id, qTab: 'all', res: { [id]: { outcome: 'merge', strat: st, reason: 'R-EQ', note: 'x', ack: true, own: 'The X shall do 5 s.', ownSeed: '', member: CL_BY[id].members[1].id, side: 'looser' } } })));
    ['link', 'escalate', 'reject', 'supersede'].forEach((o) => run('outcome ' + id + ' ' + o, (c) => base(c, { view: 'review', selected: id, qTab: 'all', res: { [id]: { outcome: o } } })));
  });
  // simulations
  run('sim claim', (c) => { base(c, { view: 'review', selected: 'CL-001', qTab: 'all' }); c.setState({ claims: { 'CL-001': { by: 'Priya Raman', lens: 'PE', mins: 3 } } }); });
  run('sim changed', (c) => { base(c, { view: 'review', selected: 'CL-001', qTab: 'all', liveVer: { 'CL-001': 1 }, openVer: { 'CL-001': 0 } }); });
  // hand-offs: every side of every request, and the send form
  const decId = byStatus.decided[0], reviewId = byStatus.review[0];
  const H = (o) => Object.assign({ from: 'sam', to: 'priya', ask: 'check', note: 'Please look at the unit on M2.', at: '10 Oct', status: 'waiting', reply: '', draft: 'Merge into one · reason R-STR' }, o || {});
  ['check', 'decide'].forEach((ask) => ['sam', 'priya', 'jordan', 'lee', 'morgan'].forEach((who) => run('hand waiting ' + ask + ' ' + who, (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: who, hand: { 'CL-001': H({ ask }) } }))));
  ['sam', 'priya', 'jordan'].forEach((who) => run('hand review waiting ' + who, (c) => base(c, { view: 'review', selected: decId, qTab: 'all', person: who, hand: { [decId]: H({ ask: 'review', draft: 'Merged · reason R-STR' }) } })));
  ['agreed', 'returned'].forEach((status) => ['sam', 'priya', 'jordan'].forEach((who) => run('hand ' + status + ' ' + who, (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: who, hand: { 'CL-001': H({ status, reply: 'Looks right to me, the unit is milliseconds.' }) } }))));
  run('hand agreed review', (c) => base(c, { view: 'review', selected: reviewId, qTab: 'all', person: 'sam', hand: { [reviewId]: H({ ask: 'review', status: 'agreed', reply: 'Reviewed.' }) } }));
  run('hand closed', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', hand: { 'CL-001': H({ status: 'closed' }) } }));
  run('hand typed reply', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: 'priya', hand: { 'CL-001': H() }, replyNote: { 'CL-001': 'I would keep the 0.2 second wording.' } }));
  run('send form open undecided', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', sendF: { 'CL-001': { open: true, to: 'jordan', ask: 'decide', note: 'Please decide this one for me.' } } }));
  run('send form open decided', (c) => base(c, { view: 'review', selected: decId, qTab: 'all', sendF: { [decId]: { open: true, to: '', ask: 'check', note: '' } } }));
  run('send form on stale/dispute', (c) => base(c, { view: 'review', selected: byStatus.dispute[0], qTab: 'all', sendF: { [byStatus.dispute[0]]: { open: true } } }));
  // results: nothing decided, everything perfect, a loosening merge that caps the letter, and each person and scope
  const nulls = (keys) => Object.fromEntries(keys.map((k) => [k, null]));
  const clear = nulls(ORDER.map((cl) => cl.id));
  const fullSign = Object.assign({}, SEED.sign['CL-045'], { UX: SEED.sign['CL-014'].UX, NU: SEED.sign['CL-014'].NU });
  const perfect = {}, perfectSign = {};
  ORDER.forEach((cl) => { perfect[cl.id] = Object.assign({}, SEED.dec['CL-045'], { member: cl.members[0].id }); perfectSign[cl.id] = fullSign; });
  const cleanMerges = Object.keys(SEED.dec).filter((k) => SEED.dec[k].outcome === 'merge' && !SEED.dec[k].weakening && k !== 'CL-014').slice(0, 20);
  cleanMerges.forEach((k) => { perfect[k] = Object.assign({}, SEED.dec[k], { note: 'Same obligation, checked against the strictest member.' }); });
  const loose = Object.assign({}, perfect, { 'CL-014': Object.assign({}, SEED.dec['CL-014'], { weakening: true, note: 'Looser on purpose, owners asked.' }) });
  const looseSign = Object.assign({}, perfectSign, { 'CL-014': { SE: SEED.sign['CL-014'].SE, UX: SEED.sign['CL-014'].UX, NU: SEED.sign['CL-014'].NU } });
  const settled = { stale: clear, objections: clear, claims: clear, sib: clear };
  run('results nothing decided', (c) => base(c, { view: 'results', dec: nulls(Object.keys(SEED.dec)) }));
  run('results perfect', (c) => base(c, Object.assign({ view: 'results', dec: perfect, sign: perfectSign }, settled)));
  run('results capped', (c) => base(c, Object.assign({ view: 'results', dec: loose, sign: looseSign }, settled)));
  ['Data Recorder', 'Mission Computer'].forEach((sc) => run('results pilot ' + sc, (c) => base(c, { view: 'results', scope: sc })));
  PEOPLE.forEach((p) => run('results hand ' + p.k, (c) => base(c, { view: 'results', person: p.k, hand: { 'CL-001': H() } })));
  // the grade itself: the rule must give the answers the page promises
  const grade = (st, alloc) => { const c = new Component.Component(); c.setState(Object.assign({ view: 'results' }, st)); return Component.resultsOf(c.S, c.allInfos(c.S), alloc || ''); };
  const gate = (ok, msg) => { if (!ok) flag('GRADE: ' + msg); };
  const g0 = grade({}), gNone = grade({ dec: nulls(Object.keys(SEED.dec)) }), gPerfect = grade(Object.assign({ dec: perfect, sign: perfectSign }, settled)), gLoose = grade(Object.assign({ dec: loose, sign: looseSign }, settled));
  [g0, gNone, gPerfect, gLoose].forEach((g, i) => { const sum = Object.values(g.kinds).reduce((x, y) => x + y, 0); gate(sum === g.n, 'destinations add up to the originals in state ' + i + ' (' + sum + ' of ' + g.n + ')'); gate(g.score >= 0 && g.score <= 100, 'score within 0 to 100 in state ' + i); });
  gate(g0.decided === byStatus.decided.length + byStatus.review.length + byStatus.approved.length + byStatus.siblings.length, 'only decisions that are not stale or disputed count (' + g0.decided + ')');
  gate(!gNone.graded, 'nothing decided means nothing graded');
  gate(gPerfect.letter === 'A' && Math.abs(gPerfect.score - 100) < 1e-9 && !gPerfect.provisional, 'a fully decided, fully signed, fully explained set gets 100 and an A, not provisional');
  gate(gLoose.unprotected === 1 && gLoose.score >= 90 && gLoose.capped && gLoose.letter === 'C', 'one unprotected loosening merge holds an otherwise A set at C (got ' + gLoose.letter + ' ' + gLoose.score.toFixed(1) + ')');
  gate(g0.projected <= g0.after && g0.after <= g0.n, 'projected <= after so far <= original');
  const split = ALLOCS.map((a) => grade({}, a.k));
  gate(split.reduce((x, g) => x + g.n, 0) === g0.n, 'allocations add up to the whole project');
  // the 20% sample for the other lenses: it must pick about a fifth, the same ones every time, and a sampled cluster must be asked for the lens
  const djb = (str) => { let h = 5381; for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0; return ('00000000' + (h >>> 0).toString(16)).slice(-8); };
  const pickedBy = (c, k) => parseInt(djb(c.id + k), 16) % 5 === 0;
  [['A', 'PE'], ['B', 'NU']].forEach(([lane, lens]) => {
    const pool = CLUSTERS.filter((c) => c.lane === lane && !c.baselined);
    const want = pool.filter((c) => pickedBy(c, lens)), got = pool.filter((c) => Component.required(c, null, false)[lens] === 'sample');
    gate(pool.length >= 30 && want.length / pool.length > 0.1 && want.length / pool.length < 0.3, 'sampling: about a fifth of lane ' + lane + ' is picked for ' + lens + ' (' + want.length + ' of ' + pool.length + ')');
    gate(want.length === got.length && want.every((c) => got.indexOf(c) >= 0), 'sampling: the app picks exactly the clusters whose ID hashes to the sample for ' + lens + ' (' + got.length + ' vs ' + want.length + ')');
    gate(pool.filter((c) => !pickedBy(c, lens)).every((c) => Component.required(c, null, false)[lens] === 'none'), 'sampling: a cluster that is not picked is not asked for ' + lens);
    gate(pool.every((c) => Component.required(c, { newWording: true }, false)[lens] === 'req'), 'sampling: new wording asks every cluster for ' + lens + ', sampled or not');
    gate(want.filter((c) => SEED.cat[c.id] === 'approved').every((c) => SEED.sign[c.id][lens]), 'sampling: a seeded approved cluster that was sampled carries the ' + lens + ' signature, so it stays approved');
  });
  // the V: every number on it must agree with the Results page, nothing may be lost, and the rules about levels must hold
  const vg = (ok, msg) => { if (!ok) flag('V: ' + msg); };
  const vmethodsN = (l) => Object.values(l.methods).reduce((x, y) => x + y, 0);
  const vee = (st) => { const c = new Component.Component(); c.setState(Object.assign({ view: 'vee' }, st)); return { V: Component.veeOf(c.S, c.allInfos(c.S)), R: Component.resultsOf(c.S, c.allInfos(c.S), '') }; };
  // A state where every cluster is decided the way the V cares about: merge into the first wording, or supersede when the wordings sit at different levels.
  const mkDec = (cl, o) => Object.assign({ outcome: 'merge', strategy: 'member', member: cl.members[0].id, text: cl.members[0].text, newWording: false, weakening: false, covers: cl.members.map((m) => m.id), kept: [], reason: 'R-STR', note: 'Same obligation, checked against the strictest member.', by: 'Sam Okafor', lens: 'SE', at: '6 Oct', rev: 'R3', vs: '', share: null, revs: [] }, o || {});
  const vAll = {}; CLUSTERS.forEach((cl) => { vAll[cl.id] = cl.crossLevel ? mkDec(cl, { outcome: 'supersede', strategy: '', text: '', covers: [] }) : mkDec(cl); });
  const newWordCl = CLUSTERS.find((cl) => !cl.crossLevel && cl.members.length >= 3);
  const vNew = Object.assign({}, vAll, { [newWordCl.id]: mkDec(newWordCl, { strategy: 'ai', member: '', text: 'The system shall do the new thing.', newWording: true }) });
  const vstates = { 'as seeded': {}, 'nothing decided': { dec: nulls(Object.keys(SEED.dec)) }, 'all decided and signed': Object.assign({ dec: vAll, sign: perfectSign }, settled), 'one new wording': Object.assign({ dec: vNew, sign: perfectSign }, settled), 'a loosening merge': Object.assign({ dec: loose, sign: looseSign }, settled) };
  const vres = {};
  Object.keys(vstates).forEach((name) => {
    const { V, R } = vee(vstates[name]); vres[name] = { V, R };
    vg(V.reqs === R.n && V.reqs === REQS.length, name + ': requirements on the V (' + V.reqs + ') equal the originals (' + R.n + ', ' + REQS.length + ')');
    vg(V.after === R.after, name + ': requirements after merges on the V (' + V.after + ') equal Results (' + R.after + ')');
    vg(V.decided === R.decided && V.decided + V.open === V.clusters && V.clusters === R.clusters, name + ': decided and open clusters on the V (' + V.decided + ' + ' + V.open + ') equal Results (' + R.decided + ' of ' + R.clusters + ')');
    vg(V.levels.reduce((x, l) => x + l.mergedAway, 0) === R.kinds.merged, name + ': merged-away requirements on the V equal the merged destinations on Results');
    vg(V.levels.reduce((x, l) => x + l.reqs, 0) === V.reqs && V.levels.every((l) => l.after === l.reqs - l.mergedAway - l.superseded + l.added && l.after >= 0), name + ': levels add up to the whole and never go negative');
    vg(V.levels.every((l) => vmethodsN(l) === l.reqs), name + ': at each level the methods (including none) add up to the requirements');
    vg(V.levels.every((l) => l.traced + l.gaps === l.reqs && l.noMethod <= l.gaps && l.noItem <= l.gaps), name + ': traced plus gaps equals the requirements at each level');
    vg(V.repoint <= V.items && V.methodShift <= V.levels.reduce((x, l) => x + l.mergedAway, 0), name + ': items to re-point are a part of the items, and method shifts are a part of the merges');
    vg(V.levels.every((l) => l.decided + l.open === l.clusters), name + ': decided plus open equals the clusters at each level');
    const g = Component.veeGlyph(V);
    vg(g.left.length === 4 && g.right.length === 4 && /Left leg/.test(g.aria) && /Right leg/.test(g.aria) && V.levels.every((l) => g.aria.indexOf(l.short) >= 0), name + ': the glyph has four circles, four squares and a spoken description of every level');
  });
  const vN = vres['nothing decided'].V, vP = vres['all decided and signed'].V, v0 = vres['as seeded'].V;
  vg(vN.repoint === 0 && vN.methodShift === 0 && vN.after === vN.reqs && vN.decided === 0 && vN.levels.every((l) => l.state === 'open' || l.clusters === 0), 'nothing decided: nothing to re-point, no requirement removed, every level says it is still being consolidated');
  vg(vN.items === v0.items && vN.items === vP.items && vN.gaps === v0.gaps && vN.traced === v0.traced, 'verification items and gaps depend on the requirements, not on decisions');
  vg(vN.items === REQS.reduce((x, r) => x + Component.VREQ[r.id].vi, 0), 'items on the V equal the items given to the requirements (none lost, none invented)');
  vg(vP.after < vP.reqs && vP.repoint > 0 && vP.decided === vP.clusters && vP.open === 0, 'all decided: requirements fall, items must move, nothing is open');
  const vW = vres['one new wording'].V;
  const itemsOf = (ms) => ms.reduce((x, m) => x + Component.VREQ[m.id].vi, 0);
  const flat = CLUSTERS.filter((cl) => !cl.crossLevel), cross = CLUSTERS.filter((cl) => cl.crossLevel);
  const expMerged = flat.reduce((x, cl) => x + cl.members.length - 1, 0), expSuper = cross.reduce((x, cl) => x + cl.members.length - 1, 0);
  const expItems = flat.reduce((x, cl) => x + itemsOf(cl.members.slice(1)), 0), crossItems = cross.reduce((x, cl) => x + itemsOf(cl.members), 0);
  vg(vP.mergedAway === expMerged && vP.superseded === expSuper && vP.after === vP.reqs - expMerged - expSuper, 'all decided: requirements removed equal what the clusters say (' + vP.mergedAway + ' merged, ' + vP.superseded + ' superseded, expected ' + expMerged + ' and ' + expSuper + ')');
  vg(vP.repoint >= expItems && vP.repoint <= expItems + crossItems, 'all decided: items to move are the items of every merged-away wording (' + vP.repoint + ', expected at least ' + expItems + ')');
  vg(vW.added === 1 && vW.after === vP.after && vW.repoint === vP.repoint + Component.VREQ[newWordCl.members[0].id].vi, 'one new wording: it adds one requirement, and the first wording\u2019s items move too (' + vW.repoint + ' vs ' + vP.repoint + ')');
  vg(v0.repoint > 0 && v0.repoint < vP.repoint, 'as seeded: some but not all items move (' + v0.repoint + ' of at most ' + vP.repoint + ')');
  vg([vN, v0, vP].every((v) => v.reqs - v.after === v.mergedAway + v.superseded - v.added && v.levelShift <= v.repoint && v.methodShift <= v.mergedAway + v.superseded), 'requirements removed equal merged plus superseded minus new wordings, and shifts are a part of the items moved');
  vg(vres['as seeded'].R.kinds.superseded === v0.superseded && vP.superseded === vres['all decided and signed'].R.kinds.superseded, 'superseded requirements on the V equal Results');
  const lvlOk = REQS.every((r) => { const v = Component.VREQ[r.id]; return v && v.lvl >= 1 && v.lvl <= 4 && (v.vm === '' || Component.VMETHODS.indexOf(v.vm) >= 0) && v.vi >= 0 && v.vi <= 3; });
  const tracedOracle = REQS.filter((r) => Component.VREQ[r.id].vm && Component.VREQ[r.id].vi > 0).length;
  vg(v0.traced === tracedOracle && v0.gaps === REQS.length - tracedOracle && v0.noMethod === REQS.filter((r) => !Component.VREQ[r.id].vm).length && v0.noItem === REQS.filter((r) => Component.VREQ[r.id].vi === 0).length, 'a requirement is traced only when it has both a verification method and at least one item (' + v0.traced + ' traced, expected ' + tracedOracle + ')');
  vg(lvlOk, 'every requirement has a level from 1 to 4, a known method or none, and 0 to 3 verification items');
  vg(v0.levels.every((l) => l.reqs > 0 && l.clusters > 0), 'every level has requirements and clusters, so the V is never lopsided to the point of a blank level');
  vg(CLUSTERS.every((c) => c.crossLevel === (c.lvls[0] !== c.lvls[1]) && c.lvls[0] >= 1 && c.lvls[1] <= 4 && c.lvls[0] <= c.lvls[1]), 'a cluster is cross-level exactly when its members sit at different levels');
  vg(CLUSTERS.filter((c) => c.crossLevel).every((c) => !c.actions.some((a) => a[0] === 'merge') && c.actions.some((a) => a[0] === 'link')), 'a cluster that mixes levels never offers merge, and does offer link');
  vg(CLUSTERS.filter((c) => !c.crossLevel).every((c) => c.members.every((m) => m.lvl === c.lvls[0])), 'a cluster inside one level has all its members at that level');
  vg(v0.cross === CLUSTERS.filter((c) => c.crossLevel).length, 'the cross-level count on the V equals the clusters that mix levels');
  // "Review the open ones" on the V must open the queue on exactly the clusters the V called open, in each state
  Object.keys(vstates).forEach((name) => [1, 2, 3, 4].forEach((k) => {
    const c = new Component.Component(); c.setState(Object.assign({ view: 'review', qTab: 'all', qStatus: 'undecided', qLvl: String(k) }, vstates[name]));
    const n = c.renderVals().qInfo.match(/of (\d+)$/); const got = n ? +n[1] : 0;
    vg(got === vres[name].V.levels[k - 1].open, name + ': the queue filter "still to decide" at level ' + k + ' lists ' + got + ' clusters, the V says ' + vres[name].V.levels[k - 1].open + ' are open');
  }));
  // scopes: the V follows the scope the way Results does
  ['Data Recorder', 'Mission Computer'].forEach((sc) => { const c = new Component.Component(); c.setState({ view: 'vee', scope: sc }); const V = Component.veeOf(c.S, c.allInfos(c.S)), R = Component.resultsOf(c.S, c.allInfos(c.S), ''); vg(V.reqs === R.n && V.after === R.after && V.reqs < REQS.length, 'scope ' + sc + ': the V covers the same requirements as Results (' + V.reqs + ' of ' + REQS.length + ')'); });
  // screens that carry the V
  PEOPLE.forEach((p) => run('vee strip home ' + p.k, (c) => base(c, { view: 'home', person: p.k })));
  const crossCl = CLUSTERS.find((c) => c.crossLevel);
  run('vee strip cross-level cluster', (c) => base(c, { view: 'review', selected: crossCl.id, qTab: 'all' }));
  run('vee strip one-level cluster', (c) => base(c, { view: 'review', selected: CLUSTERS.find((c) => !c.crossLevel).id, qTab: 'all' }));
  [1, 2, 3, 4].forEach((k) => { run('queue level ' + k, (c) => base(c, { view: 'review', qTab: 'all', qLvl: String(k) })); run('explorer level ' + k, (c) => base(c, { view: 'explorer', xLvl: k })); run('explorer level ' + k + ' gaps', (c) => base(c, { view: 'explorer', xLvl: k, xGap: true })); });
  run('explorer gaps all levels', (c) => base(c, { view: 'explorer', xGap: true }));
  run('queue level none match', (c) => base(c, { view: 'review', qTab: 'all', qLvl: '1', qSearch: 'zzzzzz' }));
  run('export with V line', (c) => base(c, { view: 'export' }));
  run('vee nothing decided', (c) => base(c, { view: 'vee', dec: nulls(Object.keys(SEED.dec)) }));
  run('vee all decided', (c) => base(c, Object.assign({ view: 'vee', dec: perfect, sign: perfectSign }, settled)));
  const noDraft = find((cl) => !cl.aiDraft && cl.actions.some((a) => a[0] === 'merge'));
  if (noDraft) run('ai declined to draft', (c) => base(c, { view: 'review', selected: noDraft.id, qTab: 'all' }));
  run('blind off/on', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: 'casey', blind: true }));
  run('blind done', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: 'casey', blindDone: { 'CL-001': 'Variant' } }));
  run('chat msgs', (c) => { base(c, { view: 'review', selected: 'CL-042', qTab: 'all', chatOpen: true }); c.setState({ chat: {} }); const v0 = c.renderVals(); v0.chips[0].onClick(); v0.chips[2].onClick(); v0.chips[3].onClick(); });
  run('chat msgs2', (c) => { base(c, { view: 'review', selected: 'CL-042', qTab: 'all', chatOpen: true, person: 'sam' }); for (let i = 0; i < 6; i++) { const v0 = c.renderVals(); v0.chips[i].onClick(); } c.setState({ chatInput: 'what is the weather' }); c.renderVals().sendChat(); });
  run('export w/ ready', (c) => base(c, { view: 'export', published: true }));
  // filters
  run('queue filters', (c) => base(c, { view: 'review', qTab: 'all', qLane: 'B', qStatus: 'open', qAlloc: 'Flight Control', qSearch: 'retention' }));
  run('queue empty', (c) => base(c, { view: 'review', qTab: 'all', qSearch: 'zzzzzz' }));
  run('pilot scope', (c) => base(c, { view: 'review', scope: 'Mission Computer', qTab: 'all' }));
  run('compare aligned', (c) => base(c, { view: 'review', selected: 'CL-050', qTab: 'all', alignOpen: true }));
  run('compare ref M6 aligned', (c) => base(c, { view: 'review', selected: 'CL-050', qTab: 'all', alignOpen: true, ref: { 'CL-050': 'x' } }));
  run('compare peeled', (c) => base(c, { view: 'review', selected: 'CL-050', qTab: 'all', peeled: { 'CL-050': ['y'] } }));
  ['after', 'before'].forEach((arm) => ['gain', 'with', 'without'].forEach((srt) => [false, true].forEach((tb) => run('metrics ' + arm + ' ' + srt + (tb ? ' table' : ''), (c) => base(c, { view: 'methods', metArm: arm, metSort: srt, metTable: tb })))));
  run('home all open', (c) => base(c, { view: 'home', homeOpen: { 0: true, 1: true, 2: true }, navClosed: { prog: true, out: true } }));
  run('home pilot', (c) => base(c, { view: 'home', scope: 'Data Recorder', person: 'lee' }));
  run('home done', (c) => { base(c, { view: 'home' }); c.setState({ search: 1 }); });
  run('pilot overview', (c) => base(c, { view: 'overview', scope: 'Data Recorder' }));
  // ---- the gold set: pages in every state, then the rules it promises ----
  {
    const items = Component.goldPlan().items, sampleLab = Component.goldSampleLabels();
    const withLabels = (labels, more) => ({ gold: Object.assign({}, DEFAULTS.gold, { labels }, more || {}) });
    const allBy = (who, v) => { const o = {}; items.forEach((it) => { o[it.key] = { [who]: { v: v || 'equiv', note: '', t: '10 Oct' } }; }); return o; };
    run('gold empty', (c) => base(c, { view: 'gold' }));
    run('gold sample', (c) => base(c, Object.assign({ view: 'gold' }, withLabels(sampleLab))));
    PEOPLE.forEach((p) => run('gold sample ' + p.k, (c) => base(c, Object.assign({ view: 'gold', person: p.k }, withLabels(sampleLab)))));
    run('gold lens preview', (c) => base(c, Object.assign({ view: 'gold', person: 'morgan', preview: 'PE' }, withLabels(sampleLab))));
    run('gold everything labelled', (c) => base(c, Object.assign({ view: 'gold' }, withLabels(allBy('sam', 'none')))));
    run('gold everything labelled, two people', (c) => base(c, Object.assign({ view: 'gold' }, withLabels(Object.fromEntries(items.map((it, i) => [it.key, { sam: { v: 'equiv', note: '', t: 'x' }, priya: { v: i % 2 ? 'none' : 'variant', note: '', t: 'x' } }]))))));
    run('gold redo', (c) => base(c, Object.assign({ view: 'gold' }, withLabels(sampleLab, { redo: items[3].key, note: 'a note', status: 'Saved it.' }))));
    run('gold with AI off', (c) => base(c, Object.assign({ view: 'gold', aiOn: false }, withLabels(sampleLab))));
    run('gold no highlight', (c) => base(c, Object.assign({ view: 'gold' }, withLabels({}, { diff: false }))));
    run('gold settled', (c) => base(c, Object.assign({ view: 'gold', person: 'morgan' }, withLabels(sampleLab, { adj: Object.fromEntries(Component.goldDisputes(Object.assign({}, DEFAULTS, withLabels(sampleLab))).slice(0, 2).map((it) => [it.key, { v: 'none', by: 'Morgan Hale', note: '' }])) }))));
    run('methods no labels', (c) => base(c, { view: 'methods' }));
    run('methods sample labels', (c) => base(c, Object.assign({ view: 'methods' }, withLabels(sampleLab))));
    Component.GOLD_CUTS.forEach((cut) => run('methods cut ' + cut, (c) => base(c, Object.assign({ view: 'methods' }, withLabels(sampleLab, { cut })))));
    run('methods labels in one group only', (c) => base(c, Object.assign({ view: 'methods' }, withLabels(Object.fromEntries(items.filter((it) => it.h === 'A').slice(0, 20).map((it) => [it.key, { sam: { v: 'equiv', note: '', t: 'x' } }]))))));
    run('methods all labelled', (c) => base(c, Object.assign({ view: 'methods' }, withLabels(allBy('sam', 'variant')))));

    const gg = (ok, msg) => { if (!ok) flag('GOLD: ' + msg); };
    const Pp = Component.goldPop(), Pl = Component.goldPlan(), n = REQS.length;
    // the plan
    gg(Pl.items.length === 160 && new Set(Pl.items.map((x) => x.key)).size === 160, 'the plan has 160 different pairs');
    gg(Component.GOLD_GROUPS.every((h) => Pl.items.filter((x) => x.h === h).length === Component.GOLD_SIZE[h]), 'the plan draws the planned number from each group');
    const sameAl = (a, b) => a.alloc === b.alloc, sameCl = (a, b) => !!a.cid && a.cid === b.cid;
    gg(Pl.items.every((x) => x.a.id < x.b.id && x.key === x.a.id + '|' + x.b.id), 'every pair is written in id order');
    gg(Pl.items.every((x) => (x.h === 'A') === sameCl(x.a, x.b)), 'group A is exactly the pairs in one cluster');
    gg(Pl.items.every((x) => (x.h === 'C') === !sameAl(x.a, x.b)), 'group C is exactly the pairs from different allocations');
    gg(Pl.items.every((x) => x.h !== 'B1' || (!sameCl(x.a, x.b) && sameAl(x.a, x.b) && (x.t >= 0.6 || x.k >= 0.6))), 'group B1 is same allocation, not clustered, reading alike');
    gg(Pl.items.every((x) => x.h !== 'B2' || (!sameCl(x.a, x.b) && sameAl(x.a, x.b) && x.t < 0.6 && x.k < 0.6)), 'group B2 is same allocation, not clustered, not reading alike');
    // a fair mix in any prefix: no group is ever more than two pairs behind its share
    let ok = true; const seen = { A: 0, B1: 0, B2: 0, C: 0 };
    Pl.items.forEach((x, i) => { seen[x.h]++; Component.GOLD_GROUPS.forEach((h) => { const want = (i + 1) * Component.GOLD_SIZE[h] / 160; if (Math.abs(seen[h] - want) > 2.5) ok = false; }); });
    gg(ok, 'any prefix of the plan is a fair mix of the four groups');
    // the population, recounted with separate code
    const norm = (t) => t.toLowerCase().replace(/[.,;:]+$/, '');
    const tk = REQS.map((r) => r.text.split(/\s+/).filter(Boolean).map(norm));
    const dfm = {}; tk.forEach((a) => new Set(a).forEach((w) => { dfm[w] = (dfm[w] || 0) + 1; }));
    const wv = tk.map((a) => { const tf = {}; a.forEach((w) => { tf[w] = (tf[w] || 0) + 1; }); const o = {}; let nn = 0; Object.keys(tf).forEach((w) => { o[w] = tf[w] * (Math.log((n + 1) / (dfm[w] + 1)) + 1); nn += o[w] * o[w]; }); return { o, nn: Math.sqrt(nn) }; });
    const dist = (A, B) => { const D = []; for (let i = 0; i <= A.length; i++) { D.push([]); for (let j = 0; j <= B.length; j++) D[i].push(i === 0 ? j : j === 0 ? i : 0); } for (let i = 1; i <= A.length; i++) for (let j = 1; j <= B.length; j++) D[i][j] = Math.min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (A[i - 1] === B[j - 1] ? 0 : 1)); return D[A.length][B.length]; };
    const cosine = (a, b) => { let x = 0; Object.keys(a.o).forEach((w) => { if (b.o[w]) x += a.o[w] * b.o[w]; }); return x / (a.nn * b.nn); };
    const cuts = Component.GOLD_CUTS, zero = () => cuts.map(() => 0);
    const R2 = { N: { A: 0, B1: 0, B2: 0, C: 0 }, cnt: { A: { text: zero(), kw: zero() }, B1: { text: zero(), kw: zero() } } };
    const truth = {};
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      if (REQS[i].alloc !== REQS[j].alloc) { R2.N.C++; continue; }
      const t = 1 - dist(tk[i], tk[j]) / Math.max(tk[i].length, tk[j].length), k = cosine(wv[i], wv[j]);
      const h = sameCl(REQS[i], REQS[j]) ? 'A' : (t >= 0.6 || k >= 0.6) ? 'B1' : 'B2';
      R2.N[h]++;
      if (h !== 'B2') { cuts.forEach((c, q) => { if (t >= c) R2.cnt[h].text[q]++; if (k >= c) R2.cnt[h].kw[q]++; }); truth[i + '|' + j] = { key: i + '|' + j, h, t, k, rel: Component.goldTruth(REQS[i], REQS[j]) !== 'none' }; }
    }
    gg(JSON.stringify(R2.N) === JSON.stringify(Pp.N), 'the number of pairs each group stands for matches a separate recount: ' + JSON.stringify(R2.N) + ' against ' + JSON.stringify(Pp.N));
    gg(Pp.N.A + Pp.N.B1 + Pp.N.B2 + Pp.N.C === n * (n - 1) / 2, 'the four groups add up to every pair');
    gg(Pp.N.A === CLUSTERS.reduce((s, c) => s + c.members.length * (c.members.length - 1) / 2, 0), 'group A is every pair inside a cluster');
    gg(JSON.stringify(R2.cnt) === JSON.stringify(Pp.cnt), 'the pairs each score flags, at each cut-off, match a separate recount');
    // the estimate, against a census: label every pair in A and B1 with the demonstration truth and the estimate must equal the exact answer
    const exact = (flag) => { let tp = 0, fl = 0, rel = 0; Object.values(truth).forEach((x) => { if (x.rel) rel++; if (flag(x)) { fl++; if (x.rel) tp++; } }); return { p: tp / fl, r: tp / rel, fl, tp, rel }; };
    const cellsOf = (flag, pick) => { const cells = {}; ['A', 'B1'].forEach((h) => [1, 0].forEach((f) => { cells[h + ':' + f] = { h, f, N: 0, n: 0, k: 0 }; })); Object.values(truth).forEach((x) => { const c = cells[x.h + ':' + (flag(x) ? 1 : 0)]; c.N++; if (pick(x, c)) { c.n++; if (x.rel) c.k++; } }); return cells; };
    const methods = { clusters: (x) => x.h === 'A', text8: (x) => x.t >= 0.8, kw6: (x) => x.k >= 0.6, text6: (x) => x.t >= 0.6 };
    Object.keys(methods).forEach((m) => {
      const ex = exact(methods[m]), est = Component.goldCellEstimate(cellsOf(methods[m], () => true));
      gg(Math.abs(est.p - ex.p) < 1e-12 && Math.abs(est.r - ex.r) < 1e-12 && est.flagged === ex.fl, 'a census gives the exact precision and recall for ' + m + ' (' + est.p + ' / ' + est.r + ' against ' + ex.p + ' / ' + ex.r + ')');
    });
    // and a sample of the size we plan to draw gives a range that holds the exact answer, in 95 or more of 100 different samples
    const rngS = (seed) => { let a = seed; return () => { a = (a * 1664525 + 1013904223) % 4294967296; return a / 4294967296; }; };
    Object.keys(methods).forEach((m) => {
      const ex = exact(methods[m]); let hitP = 0, hitR = 0, tries = 0;
      for (let seed = 1; seed <= 100; seed++) {
        const R = rngS(seed * 7919), want = { A: 50, B1: 60 };
        const chosen = new Set(); ['A', 'B1'].forEach((h) => { const ks = Object.keys(truth).filter((k) => truth[k].h === h); for (let i = ks.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); const t = ks[i]; ks[i] = ks[j]; ks[j] = t; } ks.slice(0, want[h]).forEach((k) => chosen.add(k)); });
        const est = Component.goldCellEstimate(cellsOf(methods[m], (x) => chosen.has(x.key)));
        tries++; if (est.p !== null && est.pLo <= ex.p + 1e-12 && ex.p <= est.pHi + 1e-12) hitP++; if (est.r !== null && est.rLo <= ex.r + 1e-12 && ex.r <= est.rHi + 1e-12) hitR++;
      }
      if (process.env.GOLD_DEBUG) console.log('gold coverage', m, 'exact', ex.p.toFixed(3), ex.r.toFixed(3), 'hits', hitP, hitR);
      gg(hitP >= 95 && hitR >= 95, 'the range holds the exact answer for ' + m + ' in 95 of 100 samples (precision ' + hitP + ', recall ' + hitR + ')');
    });

    // the fast way of finding the pairs that read alike must find exactly the pairs a full comparison finds: made-up requirements
    // with a tiny vocabulary (so ties, repeats, blanks, and copies are everywhere), many different sizes, one to four allocations
    {
      const keep = REQS.slice(), cutsS = Component.GOLD_CUTS;
      const plainDist = (A, B) => { const D = []; for (let i = 0; i <= A.length; i++) { D.push([]); for (let j = 0; j <= B.length; j++) D[i].push(i === 0 ? j : j === 0 ? i : 0); } for (let i = 1; i <= A.length; i++) for (let j = 1; j <= B.length; j++) D[i][j] = Math.min(D[i - 1][j] + 1, D[i][j - 1] + 1, D[i - 1][j - 1] + (A[i - 1] === B[j - 1] ? 0 : 1)); return D[A.length][B.length]; };
      let worst = '', checked = 0, pairsSeen = 0, b1Seen = 0, textOnly = 0, kwOnly = 0, blanks = 0;
      const SEEDS = 60, EXHAUSTIVE = [[3, 5, 0], [4, 4, 0], [2, 7, 0], [3, 5, 1], [2, 6, 1]];   // and every wording up to a length over a small set of words (the last two give each wording its own rare word, so most pairs read alike by text match and not by keywords)
      try {
        for (let seed = 1; seed <= SEEDS + 3 + EXHAUSTIVE.length && !worst; seed++) {
          const R = rngS(seed * 104729), pick = (a) => a[Math.floor(R() * a.length)], boundary = seed > SEEDS && seed <= SEEDS + 3, every = seed > SEEDS + 3, rare = !boundary && !every && seed % 2 === 0;
          REQS.length = 0;
          if (every) {
            const [nw, ml, tagged] = EXHAUSTIVE[seed - SEEDS - 4], make = (pre, d) => { REQS.push({ id: 'Z' + String(REQS.length).padStart(5, '0'), text: pre.concat(tagged ? ['z' + REQS.length] : []).join(' '), alloc: 'AL0', cid: null }); if (d < ml) for (let w = 0; w < nw; w++) make(pre.concat(['w' + w]), d + 1); };
            make([], 0);
          } else if (boundary) {
            // wordings of 3k and 5k words where the longer is the shorter plus 2k words nobody else uses: a text match of exactly 0.6 and a weak keyword overlap
            const common = ['alpha', 'beta', 'gamma', 'delta'];
            const add = (text, alloc) => REQS.push({ id: 'Z' + String(REQS.length).padStart(4, '0'), text, alloc, cid: null });
            for (let f = 0; f < 40; f++) add([pick(common), pick(common), pick(common), pick(common)].join(' '), 'AL0');
            for (let k = 1; k <= 6; k++) for (let v = 0; v < 3; v++) {
              const x = []; for (let w = 0; w < 3 * k; w++) x.push(pick(common));
              const tail = []; for (let w = 0; w < 2 * k; w++) tail.push('u' + seed + '_' + k + '_' + v + '_' + w);
              add(x.join(' '), 'AL0'); add(x.concat(tail).join(' '), 'AL0');
              if (v === 1) add(tail.slice(0, k).concat(x).concat(tail.slice(k)).join(' '), 'AL0');          // the extra words in the middle
            }
          } else {
            const pool = ['shall', 'the', 'system', 'provide', 'a', 'within', '5', '10', 'ms', 'seconds', 'of', 'data', 'link', 'fault', 'log', 'and', 'report', 'power', 'bus', 'on', 'startup', 'x'];
            const words = pool.slice(0, 6 + Math.floor(R() * 16)), nAl = 1 + Math.floor(R() * 4), size = 25 + Math.floor(R() * 110), bases = [];
            for (let b = 0; b < 4 + Math.floor(R() * 5); b++) { const t = []; for (let w = 0, len = Math.floor(R() * 15); w < len; w++) t.push(pick(words)); bases.push(t); }
            for (let i = 0; i < size; i++) {
              let t = pick(bases).slice();
              for (let e = 0, edits = Math.floor(R() * 4); e < edits; e++) {
                const at = Math.floor(R() * (t.length + 1)), kind = R();
                if (kind < 0.3) t.splice(at, 0, pick(words)); else if (kind < 0.5) t.splice(at, 1); else if (kind < 0.65 && at < t.length) t[at] = pick(words);
                else if (rare && at < t.length) t[at] = 'q' + Math.floor(R() * 60);                                  // a word hardly anyone else uses
                else if (at < t.length) t.splice(at, 0, t[at]);                                                          // a repeated word
              }
              if (R() < 0.05) t = [];
              let text = t.join(R() < 0.1 ? '  ' : ' ') + (R() < 0.1 ? '.' : '');
              if (!t.length && R() < 0.6) text = ' '.repeat(Math.floor(R() * 3));                                     // empty, or only spaces
              REQS.push({ id: 'Z' + String(i).padStart(4, '0'), text, alloc: 'AL' + Math.floor(R() * nAl), cid: R() < 0.3 ? 'C' + Math.floor(R() * 12) : null });
            }
          }
          Component.goldReset();
          const P = Component.goldPop(), want = { A: [], B1: [], B2: [] }, cnt = { A: { text: cutsS.map(() => 0), kw: cutsS.map(() => 0) }, B1: { text: cutsS.map(() => 0), kw: cutsS.map(() => 0) } };
          const tokS = REQS.map((r) => r.text.split(/\s+/).filter(Boolean).map((w) => w.toLowerCase().replace(/[.,;:]+$/, '')));
          blanks += tokS.filter((a) => !a.length).length;
          const grouped = {}; REQS.forEach((r, i) => { (grouped[r.alloc] = grouped[r.alloc] || []).push(i); });
          const allPairs = []; Object.keys(grouped).forEach((al) => { const G = grouped[al]; for (let x = 0; x < G.length; x++) for (let y = x + 1; y < G.length; y++) allPairs.push([G[x], G[y]]); });   // allocation by allocation
          // each of the two indexes on its own must offer every pair it is meant to find (the pairs found by the other index must not hide a gap)
          const offered = { text: new Set(), kw: new Set() };
          Object.keys(grouped).forEach((al) => { const G = grouped[al]; ['text', 'kw'].forEach((w) => (w === 'text' ? Component.goldNearText : Component.goldNearKw)(G, (p, q) => { offered[w].add(Math.min(G[p], G[q]) + '|' + Math.max(G[p], G[q])); })); });
          for (const [i, j] of allPairs) {
            const t = Component.goldTextScore(i, j), k = Component.goldKeywordScore(i, j);
            if (!worst && t >= 0.6 && !offered.text.has(i + '|' + j)) worst = 'seed ' + seed + ': the index on text match misses ' + i + ',' + j + ' (match ' + t + ')';
            if (!worst && k >= 0.6 && !offered.kw.has(i + '|' + j)) worst = 'seed ' + seed + ': the index on keywords misses ' + i + ',' + j + ' (overlap ' + k + ')';
            const top = Math.max(tokS[i].length, tokS[j].length), t2 = top ? 1 - plainDist(tokS[i], tokS[j]) / top : 1;
            if (Math.abs(t - t2) > 1e-12) { worst = 'seed ' + seed + ': text match of ' + i + ',' + j + ' is ' + t + ' but a plain comparison says ' + t2; break; }
            const h = REQS[i].cid && REQS[i].cid === REQS[j].cid ? 'A' : (t >= 0.6 || k >= 0.6) ? 'B1' : 'B2';
            want[h].push([i, j]); pairsSeen++;
            if (h === 'B1') { if (k < 0.6) textOnly++; if (t < 0.6) kwOnly++; }
            if (h !== 'B2') cutsS.forEach((c, q) => { if (t >= c) cnt[h].text[q]++; if (k >= c) cnt[h].kw[q]++; });
          }
          if (worst) break;
          b1Seen += want.B1.length;
          ['A', 'B1', 'B2'].forEach((h) => { if (!worst && JSON.stringify(P.list(h)) !== JSON.stringify(want[h])) worst = 'seed ' + seed + ': group ' + h + ' differs (' + P.list(h).length + ' pairs against ' + want[h].length + ')'; });
          if (!worst && JSON.stringify(P.cnt) !== JSON.stringify(cnt)) worst = 'seed ' + seed + ': the counts at each cut-off differ';
          if (!worst && P.N.A + P.N.B1 + P.N.B2 + P.N.C !== REQS.length * (REQS.length - 1) / 2) worst = 'seed ' + seed + ': the groups do not add up';
          // a draw from each group lands only in that group, never twice
          Component.goldReset();
          const Pl = Component.goldPlan(), inGroup = { A: new Set(want.A.map((x) => x.join('|'))), B1: new Set(want.B1.map((x) => x.join('|'))), B2: new Set(want.B2.map((x) => x.join('|'))) };
          Pl.items.forEach((x) => { if (!worst && x.h !== 'C' && !inGroup[x.h].has(x.i + '|' + x.j)) worst = 'seed ' + seed + ': a pair drawn for group ' + x.h + ' is not in it'; });
          if (!worst && new Set(Pl.items.map((x) => x.key)).size !== Pl.items.length) worst = 'seed ' + seed + ': a pair was drawn twice';
          checked++;
        }
      } finally { REQS.length = 0; keep.forEach((r) => REQS.push(r)); Component.goldReset(); }
      gg(!worst, 'the fast search for pairs that read alike matches a full comparison: ' + worst);
      gg(checked === SEEDS + 3 + EXHAUSTIVE.length && pairsSeen > 20000 && b1Seen > 500 && textOnly > 300 && kwOnly > 300 && blanks > 20, 'the comparison ran on enough made-up requirements (' + checked + ' sets, ' + pairsSeen + ' pairs, ' + b1Seen + ' that read alike, ' + textOnly + ' by text match only, ' + kwOnly + ' by keywords only, ' + blanks + ' empty)');
      gg(JSON.stringify(Component.goldPop().N) === JSON.stringify(Pp.N) && Component.goldPlan().items.map((x) => x.key).join() === Pl.items.map((x) => x.key).join(), 'the real project comes back the same after the made-up ones');
    }

    // what a pair counts as, from who said what
    const st = (labels, adj) => Object.assign({}, DEFAULTS, { gold: Object.assign({}, DEFAULTS.gold, { labels, adj: adj || {} }) });
    const L = (o) => Object.fromEntries(Object.entries(o).map(([w, v]) => [w, { v, note: '', t: 'x' }]));
    const fin = (o, adj) => Component.goldFinal(st({ K: L(o) }, adj ? { K: adj } : {}), 'K');
    gg(Component.goldFinal(st({}), 'K') === null, 'a pair nobody labelled has no label');
    gg(fin({ a: 'equiv' }).co === 'rel' && fin({ a: 'equiv' }).how === 'one', 'one label stands');
    gg(fin({ a: 'none' }).co === 'none', 'different things counts as not related');
    gg(fin({ a: 'equiv', b: 'equiv' }).how === 'agreed' && fin({ a: 'equiv', b: 'equiv' }).v === 'equiv', 'two people who agree');
    gg(fin({ a: 'equiv', b: 'variant' }).how === 'disputed' && fin({ a: 'equiv', b: 'variant' }).v === null && fin({ a: 'equiv', b: 'variant' }).co === 'rel', 'two related labels that name different relations are a dispute but still related');
    gg(fin({ a: 'equiv', b: 'none' }).how === 'disputed' && fin({ a: 'equiv', b: 'none' }).co === null, 'related against not related is left out of the numbers');
    gg(fin({ a: 'unsure' }).how === 'unsure' && fin({ a: 'unsure' }).co === null, 'cannot tell is left out');
    gg(fin({ a: 'unsure', b: 'variant' }).v === 'variant' && fin({ a: 'unsure', b: 'variant' }).how === 'one', 'cannot tell does not outvote a real label');
    gg(fin({ a: 'equiv', b: 'none' }, { v: 'none', by: 'x' }).co === 'none' && fin({ a: 'equiv', b: 'none' }, { v: 'none', by: 'x' }).how === 'settled', 'a settled pair takes the settled label');
    // agreement
    const agr = (a, b) => { const lab = {}; a.forEach((v, i) => { lab['P' + i] = { x: { v: a[i], note: '', t: 'x' }, y: { v: b[i], note: '', t: 'x' } }; }); return Component.goldAgreement(st(lab)); };
    const A1 = ['equiv', 'equiv', 'equiv', 'equiv', 'equiv', 'none', 'none', 'none', 'none', 'none'], B1x = ['equiv', 'equiv', 'equiv', 'equiv', 'variant', 'none', 'none', 'none', 'none', 'none'];
    const ag1 = agr(A1, B1x);
    gg(ag1.n === 10 && ag1.agree === 9, 'agreement counts the pairs two people both labelled');
    gg(Math.abs(ag1.kappa - (0.9 - (0.5 * 0.4 + 0 + 0.5 * 0.5)) / (1 - (0.5 * 0.4 + 0.5 * 0.5))) < 1e-12, 'kappa is observed agreement beyond chance (' + ag1.kappa + ')');
    gg(Math.abs(agr(A1, A1).kappa - 1) < 1e-12, 'kappa is 1 when two people always agree');
    gg(agr(['equiv', 'equiv'], ['equiv', 'equiv']).kappa === null, 'kappa is not defined when everyone gave one label');
    gg(Component.goldAgreement(st({ K: L({ a: 'equiv' }) })) === null, 'agreement needs two people on one pair');
    // the queue
    const q0 = Component.goldQueue(st({}), 'sam');
    gg(q0.length === 160 && q0[0].key === items[0].key, 'everyone starts with the whole plan, in order');
    const q1 = Component.goldQueue(st({ [items[0].key]: L({ sam: 'equiv' }) }), 'sam');
    gg(q1.length === 159 && q1.every((x) => x.key !== items[0].key), 'a person never sees a pair they have labelled');
    const dbl = items.filter((x) => Component.goldWants(x.key) === 2);
    gg(dbl.length >= 20 && dbl.length <= 45, 'about one pair in five goes to a second person (' + dbl.length + ' of 160)');
    const one = items.find((x) => Component.goldWants(x.key) === 1), two = dbl[0];
    gg(!Component.goldQueue(st({ [one.key]: L({ priya: 'equiv' }) }), 'sam').some((x) => x.key === one.key), 'a pair that wants one label and has it is not offered again');
    gg(Component.goldQueue(st({ [two.key]: L({ priya: 'equiv' }) }), 'sam').some((x) => x.key === two.key), 'a pair that wants two labels is offered to a second person');
    gg(!Component.goldQueue(st({ [two.key]: L({ sam: 'equiv' }) }), 'sam').some((x) => x.key === two.key), 'a pair that wants two labels is not offered again to the person who already labelled it');
    gg(!Component.goldQueue(st({ [two.key]: L({ priya: 'equiv', morgan: 'equiv' }) }), 'sam').some((x) => x.key === two.key), 'a pair with two real labels is not offered');
    gg(Component.goldQueue(st({ [one.key]: L({ priya: 'unsure' }) }), 'sam').some((x) => x.key === one.key), 'a pair someone could not tell is offered to someone else');
    const sk = Object.assign({}, st({}), { gold: Object.assign({}, DEFAULTS.gold, { skip: { sam: [items[0].key] } }) });
    const qs = Component.goldQueue(sk, 'sam');
    gg(qs.length === 160 && qs[0].key === items[1].key && qs[159].key === items[0].key, 'a skipped pair comes back last');
    // the demonstration's labels
    const keys = Object.keys(sampleLab);
    gg(keys.length === 100 && keys.every((k) => Pl.by[k]) && keys.every((k) => sampleLab[k].priya && sampleLab[k].priya.sample), 'sample labels cover the first 100 pairs and say they are samples');
    gg(keys.every((k) => (!!sampleLab[k].morgan) === (Component.goldWants(k) === 2)) && Object.values(sampleLab).every((o) => !o.morgan || o.morgan.sample), 'the second sample labeller covers the pairs that want two');
    gg(Object.values(sampleLab).every((o) => Object.values(o).every((l) => Component.GOLD_BY[l.v])), 'every sample label is a real label');
    // blind: nothing about the app's cluster, scores or AI is on the labelling page
    const blindOf = (pairKey) => { const c = new Component.Component(); c.setState({ view: 'gold', gold: Object.assign({}, DEFAULTS.gold, { redo: pairKey, labels: { [pairKey]: { sam: { v: 'equiv', note: '', t: 'x' } } } }) }); return c.valsGold(c.S); };
    items.filter((x) => x.h === 'A').slice(0, 6).forEach((it) => {
      const v = blindOf(it.key);
      const text = JSON.stringify(v, (k, x) => (typeof x === 'function' ? undefined : x));
      gg(!/CL-\d{3}/.test(text), 'the labelling page does not name the cluster of ' + it.key);
      gg(!/clustered|cluster of|the app (suggest|thought)|\bAI (said|thinks|judged)/i.test(JSON.stringify([v.gPairTitle, v.gA, v.gB, v.gOpts.map((o) => o.help + o.name)])), 'the pair card does not say what the app or the AI thought of ' + it.key);
    });
    // the page and the table agree with the rules
    {
      const c = new Component.Component(); c.setState({ view: 'methods', gold: Object.assign({}, DEFAULTS.gold, { labels: sampleLab }) });
      const v = c.renderVals(), M = Component.goldMeasure(c.S), U = Component.goldUsable(c.S);
      gg(v.gmHas && !v.gmEmpty && v.gmRows.length === 3, 'the measured table has three rows once there are labels');
      gg(v.gmRows.every((r, i) => (M.rows[i].est.p === null ? r.p === '—' : r.p === M.rows[i].est.p.toFixed(2))), 'the table shows the estimated precision');
      gg(v.gmRows.every((r, i) => (M.rows[i].est.r === null ? r.r === '—' : r.r === M.rows[i].est.r.toFixed(2) && r.rRange === M.rows[i].est.rLo.toFixed(2) + ' to ' + M.rows[i].est.rHi.toFixed(2))), 'the table shows the estimated recall and its range');
      gg(v.gmHead.indexOf(String(U.usable)) >= 0 && /made up/.test(v.gmHead) && v.gmSample, 'the heading says how many pairs were used and that some labels are made up');
      const c0 = new Component.Component(); c0.setState({ view: 'methods' }); const v0 = c0.renderVals();
      gg(v0.gmEmpty && !v0.gmHas, 'with no labels the table says nothing is measured');
      // labels in one group only: the precision can be measured, the recall cannot, and the page says what is missing
      const lab = Object.fromEntries(items.filter((x) => x.h === 'A').slice(0, 20).map((x) => [x.key, { sam: { v: 'equiv', note: '', t: 'x' } }]));
      const cA = new Component.Component(); cA.setState({ view: 'methods', gold: Object.assign({}, DEFAULTS.gold, { labels: lab }) });
      const vA = cA.renderVals(), r0 = vA.gmRows[0];
      gg(r0.hasP && !r0.hasR && r0.r === '—' && r0.needs && /Read alike/.test(r0.needText), 'with labels only in group A the recall is not shown and the page says which group needs labels');
      // the cut-off changes the two scores and not the clusters
      const cc = (cut) => { const k = new Component.Component(); k.setState({ view: 'methods', gold: Object.assign({}, DEFAULTS.gold, { labels: sampleLab, cut }) }); return k.renderVals().gmRows; };
      const r6 = cc(0.6), r9 = cc(0.9);
      gg(r6[0].p === r9[0].p && r6[0].r === r9[0].r && r6[1].flagged !== r9[1].flagged && r6[2].flagged !== r9[2].flagged, 'the cut-off moves the two scores and leaves the app’s clusters where they were');
      gg(Number(r9[1].flagged.replace(/,/g, '')) < Number(r6[1].flagged.replace(/,/g, '')), 'a higher cut-off flags fewer pairs');
    }
    // handlers
    {
      const c = new Component.Component(); c.setState({ view: 'gold' });
      const vs = c.renderVals(); const first = vs.gA.id + '|' + vs.gB.id;
      vs.gOpts[0].pick();
      const s1 = c.S, lab1 = s1.gold.labels[first];
      gg(lab1 && lab1.sam && lab1.sam.v === 'equiv' && s1.gold.last.sam === first && /Saved/.test(s1.gold.status), 'choosing a label records it under the person and says so');
      const v2 = c.renderVals();
      gg(v2.gA.id + '|' + v2.gB.id !== first && v2.gMineN === 1 && v2.gOffered === 160, 'the next pair is shown and progress counts one');
      v2.gUndo(); const s2 = c.S;
      gg(!s2.gold.labels[first] && c.renderVals().gA.id + '|' + c.renderVals().gB.id === first, 'undo removes the label and brings the pair back');
      c.renderVals().gSkip();
      gg(c.renderVals().gA.id + '|' + c.renderVals().gB.id !== first && c.S.gold.skip.sam.length === 1, 'skip moves on and remembers it');
      // observers and lens previews cannot label
      const o = new Component.Component(); o.setState({ view: 'gold', person: 'lee' }); const vo = o.renderVals(); vo.gOpts[0].pick();
      gg(vo.gReadOnly && vo.gOpts.every((x) => x.off) && Object.keys(o.S.gold.labels).length === 0, 'an observer cannot label');
      const pv = new Component.Component(); pv.setState({ view: 'gold', person: 'morgan', preview: 'PE' }); pv.renderVals().gOpts[0].pick();
      gg(Object.keys(pv.S.gold.labels).length === 0, 'previewing another lens switches labelling off');
      // keys 1 to 6, and not while typing a note
      const k = new Component.Component(); k.setState({ view: 'gold' });
      const ev = (key, tag) => ({ key, target: { tagName: tag || 'BUTTON' }, preventDefault() {} });
      k.renderVals().gOnKey(ev('5')); const n5 = Object.values(k.S.gold.labels)[0];
      gg(n5 && n5.sam.v === 'none', 'key 5 chooses Different things');
      k.renderVals().gOnKey(ev('1', 'INPUT')); gg(Object.keys(k.S.gold.labels).length === 1, 'a key typed in the note box is not a shortcut');
      k.renderVals().gOnKey(ev('9')); gg(Object.keys(k.S.gold.labels).length === 1, 'a key that is not a label does nothing');
      // a note travels with the label; the sample can be added and removed; settling needs the lead
      const m = new Component.Component(); m.setState({ view: 'gold', gold: Object.assign({}, DEFAULTS.gold, { note: ' because units ' }) });
      m.renderVals().gOpts[1].pick(); const lbl = Object.values(m.S.gold.labels)[0].sam;
      gg(lbl.v === 'variant' && lbl.note === 'because units' && m.S.gold.note === '', 'the note is kept with the label and the box is cleared');
      const sm = new Component.Component(); sm.setState({ view: 'gold' }); sm.renderVals().gLoadSample();
      gg(Object.keys(sm.S.gold.labels).length === 100 && sm.S.events.length === 1, 'loading the sample adds 100 pairs and leaves a note in the event chain');
      const d0 = Component.goldDisputes(sm.S);
      gg(d0.length >= 1, 'the sample has a disagreement to settle');
      const vSam = sm.renderVals(); gg(vSam.gDisputes.every((d) => !d.canSettle), 'only the lead can settle');
      sm.setState({ person: 'morgan' }); const vLead = sm.renderVals(); gg(vLead.gDisputes.length === d0.length && vLead.gDisputes.every((d) => d.canSettle && d.opts.length >= 1), 'the lead sees how to settle each');
      vLead.gDisputes[0].opts[0].pick();
      gg(Component.goldDisputes(sm.S).length === d0.length - 1 && sm.S.events.length === 2 && Object.keys(sm.S.gold.adj).length === 1, 'settling removes one disagreement and records it');
      sm.renderVals().gRemoveSample(); gg(Object.keys(sm.S.gold.labels).length === 0 && Object.keys(sm.S.gold.adj).length === 0, 'removing the sample leaves nothing and drops what was settled on it');
      const mine = new Component.Component(); mine.setState({ view: 'gold', gold: Object.assign({}, DEFAULTS.gold, { labels: { [items[0].key]: { sam: { v: 'equiv', note: '', t: 'x' }, priya: { v: 'equiv', note: '', t: 'x' } } } }) });
      mine.renderVals().gClearMine(); gg(Object.keys(mine.S.gold.labels[items[0].key]).join() === 'priya', 'removing my labels keeps everyone else’s');
    }
    // the file
    {
      const F = Component.goldFile(st(sampleLab));
      gg(F.format === 'reqin-gold-set/1' && F.pairs.length === 100, 'the file holds every labelled pair');
      gg(JSON.stringify(F.groups) === JSON.stringify(Object.fromEntries(Component.GOLD_GROUPS.map((h) => [h, { name: F.groups[h].name, group_pairs: Pp.N[h], drawn: Pl.size[h], labelled_and_counted: Component.goldUsable(st(sampleLab)).by[h].n }]))), 'the file says how many pairs each group stands for');
      gg(F.pairs.every((x) => Pl.by[x.pair] && x.group === Pl.by[x.pair].h && x.a_text && x.b_text && x.labelled_by.length >= 1), 'every pair in the file says how it was drawn and who labelled it');
      gg(F.pairs.every((x) => x.labelled_by.every((w) => /\(sample\)$/.test(w))), 'labels made up for the demonstration are marked in the file');
      gg(JSON.parse(JSON.stringify(F)).pairs.length === F.pairs.length, 'the file is plain JSON');
    }
  }
  // ---- one requirement at a time ----
  {
    const sg2 = (ok, msg) => { if (!ok) flag('SINGLE: ' + msg); };
    const { VREQ, VLEVELS, REQ_BY } = Component, { quantities, negOf } = Component;
    const lones = REQS.filter((r) => !r.cid);
    const djb2 = (str) => { let h = 5381; for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0; return ('00000000' + (h >>> 0).toString(16)).slice(-8); };
    const sampledPE = (id) => parseInt(djb2(id + 'PE'), 16) % 5 === 0;
    const withItems = lones.filter((r) => VREQ[r.id].vi > 0 && !sampledPE(r.id));
    const [rKeep, rReword, rDrop, rNot, rAsk] = [0, 1, 2, 3, 4].map((i) => withItems[i * 5]);
    const mkD = (r, kind, o) => Object.assign({ outcome: kind, reason: { keep: 'S-OK', reword: 'S-NUM', drop: 'S-OBS', notreq: 'S-DEF', ask: '' }[kind], note: 'Checked against the interface control document.', text: kind === 'reword' ? r.text.replace(/\bshall\b/, 'shall promptly') : '', cover: '', q: kind === 'ask' ? 'Is this still needed?' : '', to: r.owner, newWording: kind === 'reword', weakening: kind === 'drop' || kind === 'notreq', by: 'Sam Okafor', lens: 'SE', at: '6 Oct', rev: 'S1', asked: null }, o || {});
    const res = (st) => { const c = new Component.Component(); c.setState(Object.assign({ view: 'results' }, st)); return { R: Component.resultsOf(c.S, c.allInfos(c.S), ''), V: Component.veeOf(c.S, c.allInfos(c.S)), c }; };
    const R0 = res({}), five = { [rKeep.id]: mkD(rKeep, 'keep'), [rReword.id]: mkD(rReword, 'reword'), [rDrop.id]: mkD(rDrop, 'drop'), [rNot.id]: mkD(rNot, 'notreq'), [rAsk.id]: mkD(rAsk, 'ask') };
    sg2(withItems.length >= 25 && lones.length >= 100, 'the sample has enough standalone requirements to test with (' + lones.length + ')');
    // what is shown: every kind of panel, for every person
    run('single none', (c) => base(c, { view: 'explorer', xPick: rKeep.id }));
    const rSamp = lones.find((r) => sampledPE(r.id));
    run('single observer sees a requirement', (c) => base(c, { view: 'explorer', xPick: rKeep.id, person: 'lee' }));
    run('single preview', (c) => base(c, { view: 'explorer', xPick: rKeep.id, person: 'morgan', preview: 'PE' }));
    run('single sampled lens', (c) => base(c, { view: 'explorer', xPick: rSamp.id, person: 'priya', rdec: { [rSamp.id]: mkD(rSamp, 'keep') } }));
    run('single near and beside', (c) => base(c, { view: 'explorer', xPick: rKeep.id, rcmp: Component.rdNear(rKeep.id, 5)[1].id }));
    run('single choosing second', (c) => base(c, { view: 'explorer', xPick: rKeep.id, rpick: true }));
    ['keep', 'reword', 'drop', 'notreq', 'ask'].forEach((k) => {
      const r = { keep: rKeep, reword: rReword, drop: rDrop, notreq: rNot, ask: rAsk }[k];
      run('single form ' + k, (c) => base(c, { view: 'explorer', xPick: r.id, rform: { [r.id]: { kind: k, reason: k === 'ask' ? '' : mkD(r, k).reason, text: mkD(r, k).text || r.text, note: 'Checked against the interface control document.', q: 'Is this still needed?', edit: true } } }));
      run('single form empty ' + k, (c) => base(c, { view: 'explorer', xPick: r.id, rform: { [r.id]: { kind: k, edit: true } } }));
      ['sam', 'priya', 'jordan', 'casey', 'morgan', 'lee'].forEach((who) => run('single decided ' + k + ' ' + who, (c) => base(c, { view: 'explorer', xPick: r.id, person: who, rdec: { [r.id]: mkD(r, k) }, sign: k === 'ask' ? {} : { [r.id]: { SE: { by: 'Morgan Hale', at: '7 Oct', rev: 'S1' } } } })));
    });
    run('single drop covered', (c) => base(c, { view: 'explorer', xPick: rDrop.id, rcmp: rKeep.id, rform: { [rDrop.id]: { kind: 'drop', reason: 'S-COV', note: 'Covered by the other one.', edit: true } } }));
    run('single reword with changes', (c) => base(c, { view: 'explorer', xPick: rReword.id, rform: { [rReword.id]: { kind: 'reword', reason: 'S-NUM', text: rReword.text.replace(/\bshall\b/, 'should'), note: '', edit: true } } }));
    run('single changing a decision', (c) => base(c, { view: 'explorer', xPick: rKeep.id, rdec: { [rKeep.id]: mkD(rKeep, 'keep') }, rform: { [rKeep.id]: { kind: 'reword', reason: '', text: rKeep.text, edit: true } } }));
    const openBig = CLUSTERS.find((c) => c.members.length > 2 && statusOf(Object.assign({}, DEFAULTS), c) === 'open'), decidedCl = CLUSTERS.find((c) => SEED.dec[c.id] && c.members.length > 2), pair = CLUSTERS.find((c) => c.members.length === 2 && statusOf(Object.assign({}, DEFAULTS), c) === 'open');
    [openBig, decidedCl, pair].forEach((cl, i) => run('single member of cluster ' + i, (c) => base(c, { view: 'explorer', xPick: cl.members[0].id })));
    run('single peeled', (c) => base(c, { view: 'explorer', xPick: openBig.members[0].id, peeled: { [openBig.id]: [openBig.members[0].id] } }));
    run('results with singles', (c) => base(c, { view: 'results', rdec: five }));
    run('vee with singles', (c) => base(c, { view: 'vee', rdec: five }));
    run('home with singles', (c) => base(c, { view: 'home', rdec: five }));
    run('audit with singles', (c) => base(c, { view: 'audit', rdec: five }));
    run('export with singles', (c) => base(c, { view: 'export', rdec: five }));

    // the counts: a separate recount of what each decision does
    const R1 = res({ rdec: five });
    const rm = [rDrop, rNot], kept = [rKeep, rReword, rAsk];
    sg2(R1.R.kinds.asis === R0.R.kinds.asis - 5 && R1.R.kinds.kept1 === 1 && R1.R.kinds.reworded === 1 && R1.R.kinds.dropped === 1 && R1.R.kinds.notreq === 1 && R1.R.kinds.escalated === R0.R.kinds.escalated + 1, 'each decision moves one requirement out of “stays as it is” into its own destination');
    sg2(Object.values(R1.R.kinds).reduce((x, y) => x + y, 0) === R1.R.n && R1.R.n === REQS.length, 'every original requirement still has exactly one destination (' + Object.values(R1.R.kinds).reduce((x, y) => x + y, 0) + ' of ' + R1.R.n + ')');
    sg2(R1.R.after === R0.R.after - rm.length && R1.R.projected === R0.R.projected - rm.length, 'dropping a requirement or calling it not a requirement takes one off the count; keep, new wording and ask leave it');
    sg2(R1.V.after === R1.R.after && R1.V.reqs === R1.R.n, 'the V agrees with Results after single decisions (' + R1.V.after + ' and ' + R1.R.after + ')');
    sg2(R1.V.dropped === 2 && R1.V.levels.reduce((x, l) => x + l.dropped, 0) === 2 && R1.V.reworded === 1, 'the V counts the dropped and the reworded');
    sg2(R1.V.repoint === R0.V.repoint + VREQ[rDrop.id].vi + VREQ[rNot.id].vi && R1.V.recheck === VREQ[rReword.id].vi, 'verification items on a removed requirement are to re-point, and on a reworded one to read again (' + R1.V.repoint + ' vs ' + (R0.V.repoint + VREQ[rDrop.id].vi + VREQ[rNot.id].vi) + ')');
    sg2(R1.V.levels.every((l) => l.after === l.reqs - l.mergedAway - l.superseded - l.dropped + l.added && l.after >= 0), 'at every level the requirements after decisions add up with the dropped ones taken off');
    const lvOf = (r) => VREQ[r.id].lvl;
    sg2(R1.V.levels[lvOf(rDrop) - 1].dropped >= 1 && R1.V.levels[lvOf(rNot) - 1].dropped >= 1, 'a dropped requirement is taken off its own level');
    const Rask = res({ rdec: { [rAsk.id]: mkD(rAsk, 'ask') } });
    sg2(Rask.R.after === R0.R.after && Math.abs(Rask.R.score - R0.R.score) < 1e-9 && Rask.R.kinds.escalated === R0.R.kinds.escalated + 1 && Rask.R.singleN === 0, 'asking the owner changes no count and no score; the requirement waits as it is');
    sg2(Rask.R.n === R0.R.n && Rask.V.after === R0.V.after, 'asking the owner leaves the V alone');
    // grade: a removal without the owners and the process engineer is unprotected, with them it is not
    const Rd0 = res({ rdec: { [rDrop.id]: mkD(rDrop, 'drop') } }), sgn = (o) => ({ [rDrop.id]: o });
    sg2(Rd0.R.unprotected === R0.R.unprotected + 1 && Rd0.R.looseN === 1 && Rd0.R.singleN === 1, 'a drop with no sign-off is an unprotected removal');
    const prot = { SE: { by: 'Morgan Hale', at: '7 Oct', rev: 'S1' }, PE: { by: 'Priya Raman', at: '7 Oct', rev: 'S1' }, OWN: { by: 'Morgan Hale', at: '7 Oct', rev: 'S1' } };
    const Rd1 = res({ rdec: { [rDrop.id]: mkD(rDrop, 'drop') }, sign: sgn(prot) });
    sg2(Rd1.R.unprotected === R0.R.unprotected && Rd1.R.looseN === 1 && Rd1.R.signDone === R0.R.signDone + 1, 'a drop signed by the owners and the process engineer is protected');
    const Rd2 = res({ rdec: { [rDrop.id]: mkD(rDrop, 'drop') }, sign: sgn({ SE: prot.SE, OWN: prot.OWN }) });
    sg2(Rd2.R.unprotected === R0.R.unprotected + 1, 'owners without the process engineer is still unprotected');
    sg2(Rd0.R.signN === R0.R.signN + 1 && Rd0.R.why === R0.R.why + 1 && Rd0.R.noSecond === R0.R.noSecond + 1, 'a recorded single decision joins the sign-off, note and second-pair-of-eyes counts');
    const noNote = res({ rdec: { [rKeep.id]: mkD(rKeep, 'keep', { note: 'ok' }) } });
    sg2(noNote.R.noWhy === R0.R.noWhy + 1, 'a note shorter than twelve characters is not a written reason');
    // a requirement in a cluster is decided with the cluster: a decision stored on it does not count until it is taken out
    const mem = openBig.members[0];
    const Rm = res({ rdec: { [mem.id]: mkD(mem, 'drop') } });
    sg2(Rm.R.after === R0.R.after && Rm.R.kinds.dropped === 0, 'a decision on a requirement still inside its cluster is ignored');
    const Rp = res({ rdec: { [mem.id]: mkD(mem, 'drop') }, peeled: { [openBig.id]: [mem.id] } });
    sg2(Rp.R.kinds.dropped === 1, 'once it is taken out of the cluster the decision counts');
    // scope
    const other = ['Mission Computer', 'Data Recorder'].find((a) => a !== rKeep.alloc), here = rKeep.alloc;
    const Rs = res({ scope: other, rdec: { [rKeep.id]: mkD(rKeep, 'keep') } }), Rs0 = res({ scope: other });
    sg2(Rs.R.kinds.kept1 === 0 && Rs.R.n === Rs0.R.n && Rs.R.kinds.asis === Rs0.R.kinds.asis, 'a decision outside the chosen scope is not counted in it');
    const Rh = res({ scope: here, rdec: { [rKeep.id]: mkD(rKeep, 'keep') } });
    sg2(Rh.R.kinds.kept1 === 1, 'and it is counted inside it');
    // who signs
    const rq = (r, k, o) => Component.rdRequired(r, mkD(r, k, o));
    const slotsOf = (q) => Object.keys(q).filter((x) => q[x] !== 'none').sort().join();
    sg2(slotsOf(rq(rKeep, 'keep')) === 'SE', 'keep as written needs the systems engineer (and the process engineer only on the sample)');
    sg2(slotsOf(rq(rReword, 'reword', { weakening: false })).split(',').filter((x) => x !== 'NU' || true).join() === 'NU,PE,SE,UX', 'new wording needs the systems, process, UI and new-user lenses');
    sg2(['OWN', 'PE', 'SE'].every((x) => slotsOf(rq(rDrop, 'drop')).split(',').indexOf(x) >= 0) && ['OWN', 'PE', 'SE'].every((x) => slotsOf(rq(rNot, 'notreq')).split(',').indexOf(x) >= 0), 'dropping and “not a requirement” need the owners and the process engineer');
    sg2(slotsOf(rq(rAsk, 'ask')) === '', 'asking the owner needs no sign-off');
    sg2(slotsOf(rq(rReword, 'reword', { weakening: true })).indexOf('OWN') >= 0, 'new wording that loosens needs the owners');
    // the checks on new wording
    const G = (r, t) => Component.rdGuards(r, t);
    const rs = REQS.find((r) => /\bshall\b/.test(r.text) && quantities(r.text).length > 0 && !negOf(r.text) && !/\b(upon|when|if|while|unless|where|after|before|during)\b/i.test(r.text)), q0 = quantities(rs.text)[0];
    sg2(G(rs, rs.text + ' ').same && G(rs, rs.text).blocks === 1, 'the same wording is blocked');
    sg2(G(rs, '').blocks === 1, 'empty wording is blocked');
    sg2(G(rs, rs.text.replace(q0.raw, 'a short time')).blocks === 1, 'wording that loses its number is blocked');
    sg2(G(rs, rs.text.replace(/\bshall\b/, 'will')).weakening === true && G(rs, rs.text.replace(/\bshall\b/, 'will')).blocks === 0, 'shall to will is allowed but needs the owners');
    sg2(G(rs, rs.text.replace(/\bshall\b/, 'shall not')).blocks >= 1, 'a flipped not is blocked');
    sg2(G(rs, rs.text.replace(/\bshall\b/, 'is expected to')).blocks === 1, 'losing the modal verb is blocked');
    sg2(G(rs, rs.text.replace(q0.raw, (q0.n + 1) + ' ' + q0.unit)).weakening === true, 'a changed number needs the owners');
    sg2(G(rs, rs.text.replace(/\bshall\b/, 'shall clearly')).blocks === 0 && G(rs, rs.text.replace(/\bshall\b/, 'shall clearly')).weakening === false, 'a plain rewording that keeps the number and the shall is clean');
    sg2(G(rs, 'When armed, ' + rs.text.charAt(0).toLowerCase() + rs.text.slice(1)).weakening === true, 'adding a condition needs the owners');
    // the nearest requirements, recounted with the scores themselves
    [rKeep, rReword, rDrop].forEach((r) => {
      const i = Component.REQ_IX[r.id], all = REQS.map((o, j) => ({ id: o.id, j })).filter((o) => o.id !== r.id && REQ_BY[o.id].alloc === r.alloc).map((o) => { const lo = Math.min(i, o.j), hi = Math.max(i, o.j); return { id: o.id, s: Math.max(Component.goldTextScore(lo, hi), Component.goldKeywordScore(lo, hi)) }; }).sort((a, b) => b.s - a.s || (a.id < b.id ? -1 : 1)).slice(0, 5).map((x) => x.id);
      sg2(JSON.stringify(Component.rdNear(r.id, 5).map((x) => x.id)) === JSON.stringify(all), 'the five nearest to ' + r.id + ' are the five with the best scores in its allocation');
    });
    // the screen: states and handlers
    const drive = (st, who) => { const c = new Component.Component(); c.setState(Object.assign({ view: 'explorer', person: who || 'sam' }, st)); return c; };
    {
      const id = rKeep.id, c = drive({ xPick: id });
      let v = c.renderVals();
      sg2(v.sp.canDecide && !v.sp.hasDec && v.sp.showForm && v.sp.problems[0].t === 'Choose what to do with this requirement.' && v.sp.noRecord, 'before anything is chosen the form says what to do and cannot be recorded');
      sg2(v.sp.near.length === 5 && !v.sp.hasCmp, 'five requirements are offered to put beside it');
      v.sp.kinds[0].pick(); v = c.renderVals();
      sg2(v.sp.kind === 'keep' && v.sp.hasReason && v.sp.problems[0].t === 'Choose the reason.', 'choosing keep asks for the reason next');
      v.sp.onReason({ target: { value: 'S-OK' } }); v = c.renderVals();
      sg2(!v.sp.hasProblems && !v.sp.noRecord && v.sp.hasWillSign, 'with a reason, keep can be recorded and says who has to sign');
      v.sp.record(); v = c.renderVals();
      const d = c.S.rdec[id];
      sg2(d && d.outcome === 'keep' && d.reason === 'S-OK' && d.by === 'Sam Okafor' && d.lens === 'SE', 'recording keeps the decision with who, which lens and the reason');
      sg2(c.S.events[c.S.events.length - 1].text.indexOf(id) >= 0 && /Keep as written/.test(c.S.events[c.S.events.length - 1].text), 'recording writes to the audit log');
      sg2(v.sp.hasDec && v.sp.d.status === 'Decided' && !v.sp.showForm && v.sp.d.selfNote && !v.sp.d.canSign, 'the person who decided is told a colleague signs, and cannot sign their own');
      sg2(v.xp.stateLabel.indexOf('collecting') >= 0, 'the requirement is shown as decided, collecting sign-offs, on the map');
      // a colleague signs
      const c2 = drive({ xPick: id, rdec: c.S.rdec }, 'morgan'); let v2 = c2.renderVals();
      sg2(v2.sp.d.canSign && v2.sp.d.hasSlots, 'a colleague with the lens can sign');
      v2.sp.d.doSign(); v2 = c2.renderVals();
      sg2(Component.rdStatus(c2.S, rKeep) === 'approved' && v2.sp.d.status === 'Approved', 'with every lens the policy asks for, the decision is approved');
      sg2(c2.S.sign[id].SE && c2.S.sign[id].SE.by === 'Morgan Hale', 'the sign-off is recorded under the person');
      v2.sp.d.doWithdrawSign(); sg2(!Object.keys(c2.S.sign[id]).length, 'a person can withdraw their sign-off');
      // changing the decision clears the sign-offs
      const c3 = drive({ xPick: id, rdec: { [id]: mkD(rKeep, 'keep') }, sign: { [id]: { SE: prot.SE } } }); let v3 = c3.renderVals();
      v3.sp.d.change(); v3 = c3.renderVals(); v3.sp.kinds[2].pick(); v3 = c3.renderVals(); v3.sp.onReason({ target: { value: 'S-OBS' } }); v3 = c3.renderVals(); v3.sp.onNote({ target: { value: 'No longer applies after the change request.' } }); v3 = c3.renderVals(); v3.sp.record();
      sg2(c3.S.rdec[id].outcome === 'drop' && !Object.keys(c3.S.sign[id]).length && c3.S.rdec[id].rev === 'S2', 'recording a new decision clears the old sign-offs and moves the revision on');
      const c4 = drive({ xPick: id, rdec: { [id]: mkD(rKeep, 'keep') } }); const v4 = c4.renderVals(); v4.sp.d.withdraw();
      sg2(!c4.S.rdec[id] && Component.rdList(c4.S, '').length === 0, 'withdrawing removes the decision from the counts');
    }
    {
      // drop covered by another: needs the other put beside it, and the other must not be removed itself
      const c = drive({ xPick: rDrop.id, rform: { [rDrop.id]: { kind: 'drop', reason: 'S-COV', note: 'Covered by the other one.', edit: true } } }); let v = c.renderVals();
      sg2(v.sp.hasProblems && /beside/.test(v.sp.problems[0].t) && v.sp.noRecord, 'dropping because another covers it needs the other put beside it');
      const near = Component.rdNear(rDrop.id, 5)[0].id; v.sp.near[0].pick(); v = c.renderVals();
      sg2(c.S.rcmp === near && v.sp.hasCmp && v.sp.cmp.id === near && !v.sp.hasProblems, 'putting the nearest beside it makes the drop recordable');
      v.sp.record(); sg2(c.S.rdec[rDrop.id].cover === near, 'the covering requirement is kept on the decision');
      const bad = drive({ xPick: rDrop.id, rcmp: rNot.id, rdec: { [rNot.id]: mkD(rNot, 'notreq') }, rform: { [rDrop.id]: { kind: 'drop', reason: 'S-COV', note: 'Covered by the other one.', edit: true } } }); const vb = bad.renderVals();
      sg2(vb.sp.hasProblems && /itself being removed/.test(vb.sp.problems[0].t), 'a requirement that is itself being removed cannot cover another');
      // choosing the second one from the list or the map
      const pk = drive({ xPick: rKeep.id }); let vp = pk.renderVals(); vp.sp.pickToggle(); vp = pk.renderVals();
      sg2(vp.sp.picking && /Click a square/.test(vp.sp.pickHelp), 'choosing another says how');
      const target = REQS.find((r) => r.alloc === rKeep.alloc && r.id !== rKeep.id).id;
      vp.xRows[0].pick(); vp = pk.renderVals();
      sg2(pk.S.rcmp === vp.xRows[0].id && pk.S.xPick === rKeep.id && !pk.S.rpick, 'while choosing, a click on the list puts that requirement beside the first without losing it');
      const mp = drive({ xPick: rKeep.id, rpick: true }); const vm = mp.renderVals(); vm.groups[0].cells[1].pick();
      sg2(mp.S.rcmp && mp.S.xPick === rKeep.id, 'while choosing, a click on the map does the same');
      // the diff between them is shown with the same words highlighted as in a cluster
      const cm = drive({ xPick: rKeep.id, rcmp: Component.rdNear(rKeep.id, 5)[0].id }); const vc = cm.renderVals();
      sg2(vc.sp.cmp.a.map((x) => x.t).join(' ') === rKeep.text && vc.sp.cmp.b.map((x) => x.t).join(' ') === REQ_BY[vc.sp.cmp.id].text && vc.sp.cmp.facts.length === 6, 'both wordings are shown word for word, with six facts side by side');
      vc.sp.cmp.swap(); sg2(cm.S.xPick === vc.sp.cmp.id && cm.S.rcmp === rKeep.id, 'the two can be swapped');
      vc.sp.cmp.clear;
      // ask the owner
      const ca = drive({ xPick: rAsk.id }); let va = ca.renderVals(); va.sp.kinds[4].pick(); va = ca.renderVals();
      sg2(va.sp.isAsk && !va.sp.hasReason && !va.sp.showNote && /Write the question/.test(va.sp.problems[0].t), 'asking the owner needs a question and no reason');
      va.sp.onQ({ target: { value: 'Is the 5 second limit still the one in the ICD?' } }); va = ca.renderVals(); va.sp.record();
      sg2(ca.S.rdec[rAsk.id].outcome === 'ask' && ca.S.rdec[rAsk.id].to === rAsk.owner && Component.rdStatus(ca.S, rAsk) === 'asked', 'the question is kept with the owner it was sent to');
      // the owner answers: a person records the answer as a normal decision, and the question stays on it
      let va2 = ca.renderVals(); va2.sp.d.change(); va2 = ca.renderVals(); va2.sp.kinds[0].pick(); va2 = ca.renderVals(); va2.sp.onReason({ target: { value: 'S-OK' } }); va2 = ca.renderVals(); va2.sp.record();
      sg2(ca.S.rdec[rAsk.id].outcome === 'keep' && ca.S.rdec[rAsk.id].asked && /5 second/.test(ca.S.rdec[rAsk.id].asked.q), 'the owner’s answer becomes a decision that keeps the question');
      // observers and previews cannot decide
      const ob = drive({ xPick: rKeep.id, rform: { [rKeep.id]: { kind: 'keep', reason: 'S-OK', edit: true } } }, 'lee'); const vo = ob.renderVals();
      vo.sp.record(); sg2(!ob.S.rdec[rKeep.id] && vo.sp.noRecord && vo.sp.showFormLocked, 'an observer can look and compare but not decide');
      const pv = drive({ xPick: rKeep.id, person: 'morgan', preview: 'PE', rform: { [rKeep.id]: { kind: 'keep', reason: 'S-OK', edit: true } } }); pv.renderVals().sp.record();
      sg2(!pv.S.rdec[rKeep.id], 'previewing another lens switches deciding off');
      // taking a requirement out of its cluster
      const cp = drive({ xPick: openBig.members[0].id }); let vq = cp.renderVals();
      sg2(vq.sp.notAlone && !vq.sp.canDecide && !vq.sp.peel.no, 'a member of an undecided cluster offers to be taken out');
      vq.sp.peel.doIt(); vq = cp.renderVals();
      sg2(cp.S.peeled[openBig.id].indexOf(openBig.members[0].id) >= 0 && vq.sp.canDecide && !vq.sp.notAlone, 'once taken out it can be decided on its own');
      const cd = drive({ xPick: decidedCl.members[0].id }); const vd = cd.renderVals();
      sg2(vd.sp.notAlone && vd.sp.peel.no, 'a member of a decided cluster cannot be taken out without reopening it');
      const c2m = drive({ xPick: pair.members[0].id }); sg2(c2m.renderVals().sp.peel.no, 'one of only two cannot be taken out');
    }
    // the map and the list show the state, and still add up
    {
      const c = drive({ rdec: { [rKeep.id]: mkD(rKeep, 'keep') }, sign: { [rKeep.id]: { SE: prot.SE } } }), v = c.renderVals();
      sg2(v.legend.reduce((x, l) => x + l.n, 0) === REQS.length, 'the five states on All requirements add up to every requirement');
      sg2(c.reqState(c.S, rKeep) === 'approved' && c.reqState(c.S, rReword) === 'alone', 'a requirement decided on its own is shown by how far its decision has got');
    }
  }
  // ---- the trace map: what a decision moves outside the requirement list ----
  {
    const tg = (ok, msg) => { if (!ok) flag('TRACE: ' + msg); };
    const { VREQ, REQ_BY, TR_ITEMS, TR_ITEM_BY, TR_PARENT, TR_CHILD, TR_BL, TR_CSV, TR_TABS } = Component;
    const mk = (st) => { const c = new Component.Component(); c.setState(Object.assign({ view: 'export' }, st || {})); return c; };
    const look = (st, only) => { const c = mk(st), infos = c.allInfos(c.S); return { c, infos, V: Component.veeOf(c.S, infos), R: Component.resultsOf(c.S, infos, ''), T: Component.trOf(c.S, infos, only || '') }; };
    const lones = REQS.filter((r) => !r.cid);
    const djb2 = (str) => { let h = 5381; for (let i = 0; i < str.length; i++) h = ((h << 5) + h + str.charCodeAt(i)) | 0; return ('00000000' + (h >>> 0).toString(16)).slice(-8); };
    const sampledPE = (id) => parseInt(djb2(id + 'PE'), 16) % 5 === 0;

    // ---- the sample map itself ----
    const allItems = REQS.reduce((a, r) => a.concat(TR_ITEMS[r.id]), []);
    tg(new Set(allItems.map((x) => x.id)).size === allItems.length && allItems.length === REQS.reduce((a, r) => a + VREQ[r.id].vi, 0), 'every verification item has its own ID and a requirement has as many as the V says (' + allItems.length + ')');
    tg(allItems.every((x) => TR_ITEM_BY[x.id] === x && VREQ[x.req].lvl === x.lvl && (x.method ? /^(TC|AN|IN|DM)-\d+$/.test(x.id) : /^VI-\d+$/.test(x.id))), 'an item belongs to one requirement, sits at its level, and its ID says the method');
    tg(look().V.items === allItems.length, 'the V and the map count the same number of items');
    tg(REQS.every((r) => { const l = VREQ[r.id].lvl, p = TR_PARENT[r.id]; return l === 1 ? p === '' : !!p && VREQ[p] && VREQ[p].lvl === l - 1; }), 'every requirement below the top level has a parent exactly one level up, and the top level has none');
    tg(Object.keys(TR_CHILD).every((p) => TR_CHILD[p].every((k) => TR_PARENT[k] === p)) && Object.keys(TR_CHILD).reduce((a, p) => a + TR_CHILD[p].length, 0) === REQS.filter((r) => TR_PARENT[r.id]).length, 'the children are the parents turned round');
    tg(CLUSTERS.filter((c) => c.rel === 'SUBSUMES').every((c) => c.members.every((m, i) => i === 0 || VREQ[m.id].lvl <= VREQ[c.members[0].id].lvl || TR_PARENT[m.id] === c.members[0].id)), 'in a cluster where one contains the other, the stricter wording sits under the general one');
    {
      const same = []; CLUSTERS.forEach((c) => { if (c.rel === 'SUBSUMES' || !TR_PARENT[c.members[0].id]) return; c.members.slice(1).forEach((m) => same.push(TR_PARENT[m.id] === TR_PARENT[c.members[0].id])); });
      const share = same.filter(Boolean).length / same.length;
      tg(same.length > 100 && share > 0.6 && share < 0.85, 'wordings in a cluster mostly, but not always, share a parent (' + Math.round(share * 100) + '% of ' + same.length + ')');
    }
    tg(REQS.filter((r) => r.cid).every((r) => { const c = CL_BY[r.cid], m = c.members.find((x) => x.id === r.id); return !!TR_BL[r.id] === /^Baselined/.test(m.base || ''); }) && Object.keys(TR_BL).filter((id) => REQ_BY[id].cid).every((id) => TR_BL[id].cr === CL_BY[REQ_BY[id].cid].cr), 'a wording in a cluster is baselined exactly when the data says so, with the cluster’s change request');
    const loneBl = lones.filter((r) => TR_BL[r.id]).length;
    tg(loneBl / lones.length > 0.03 && loneBl / lones.length < 0.15, 'about one in twelve requirements that stand alone is baselined (' + loneBl + ' of ' + lones.length + ')');

    // ---- the map agrees with the V and with Results, in many states ----
    const cl3 = CLUSTERS.filter((c) => c.members.length > 2 && !SEED.dec[c.id]);
    const withKids = lones.filter((r) => VREQ[r.id].vi > 0 && (TR_CHILD[r.id] || []).length > 0 && !sampledPE(r.id) && !TR_BL[r.id]);
    const onlyChild = lones.filter((r) => TR_PARENT[r.id] && TR_CHILD[TR_PARENT[r.id]].length === 1 && VREQ[r.id].vi > 0 && !TR_BL[r.id]);
    const plain = lones.filter((r) => VREQ[r.id].vi > 1 && !TR_BL[r.id] && !(TR_CHILD[r.id] || []).length);
    const rParent = withKids[0], rBare = onlyChild[0], rCover = plain[0], rNo = plain[1], rReword = plain[2], rTo = plain[3], rChainA = plain[4], rChainB = plain[5], rChainC = plain[6], rBl = lones.find((r) => TR_BL[r.id] && VREQ[r.id].vi > 0);
    tg(!!(rParent && rBare && rCover && rNo && rReword && rBl), 'the sample has requirements to test with: one with children, one that is its parent’s only child, plain ones with items, and a baselined one');
    const mkD = (r, kind, o) => Object.assign({ outcome: kind, reason: { keep: 'S-OK', reword: 'S-NUM', drop: 'S-OBS', notreq: 'S-DEF', ask: '' }[kind], note: 'Checked against the interface control document.', text: kind === 'reword' ? r.text.replace(/\bshall\b/, 'shall promptly') : '', cover: '', q: '', to: r.owner, cr: '', newWording: kind === 'reword', weakening: kind === 'drop' || kind === 'notreq', by: 'Sam Okafor', lens: 'SE', at: '7 Oct', rev: 'S1', asked: null }, o || {});
    const sign = (o) => ({ SE: { by: 'Morgan Hale', at: '7 Oct', rev: 'S1' }, PE: { by: 'Priya Raman', at: '7 Oct', rev: 'S1' }, OWN: { by: 'Morgan Hale', at: '7 Oct', rev: 'S1' } });
    const states = {
      'seed': {},
      'a drop with a cover, a drop without, a not-a-requirement, a reword': { rdec: { [rCover.id]: mkD(rCover, 'drop', { reason: 'S-COV', cover: rTo.id }), [rNo.id]: mkD(rNo, 'drop'), [rParent.id]: mkD(rParent, 'notreq'), [rReword.id]: mkD(rReword, 'reword') } },
      'a covering requirement that is itself dropped': { rdec: { [rChainA.id]: mkD(rChainA, 'drop', { reason: 'S-COV', cover: rChainB.id }), [rChainB.id]: mkD(rChainB, 'drop', { reason: 'S-COV', cover: rChainC.id }) } },
      'a covering requirement dropped with nothing covering it': { rdec: { [rChainA.id]: mkD(rChainA, 'drop', { reason: 'S-COV', cover: rChainB.id }), [rChainB.id]: mkD(rChainB, 'drop') } },
      'two drops that cover each other': { rdec: { [rChainA.id]: mkD(rChainA, 'drop', { reason: 'S-COV', cover: rChainB.id }), [rChainB.id]: mkD(rChainB, 'drop', { reason: 'S-COV', cover: rChainA.id }) } },
      'the only child of its parent is dropped': { rdec: { [rBare.id]: mkD(rBare, 'drop') } },
      'signed drops': { rdec: { [rCover.id]: mkD(rCover, 'drop'), [rParent.id]: mkD(rParent, 'drop') }, sign: { [rCover.id]: sign(), [rParent.id]: sign() } },
      'one allocation': { scope: rParent.alloc, rdec: { [rParent.id]: mkD(rParent, 'drop'), [rReword.id]: mkD(rReword, 'reword') } },
      'a baselined drop': { rdec: { [rBl.id]: mkD(rBl, 'drop', { cr: 'CR-2200' }) } }
    };
    Object.keys(states).forEach((name) => {
      const { c, infos, V, R, T } = look(states[name]), lab = ' [' + name + ']';
      tg(T.n.moves + T.n.choose === V.repoint, 'verification item rows equal the V’s “to carry over” (' + (T.n.moves + T.n.choose) + ' and ' + V.repoint + ')' + lab);
      tg(T.n.reread === V.recheck, 'items to read again equal the V’s number (' + T.n.reread + ' and ' + V.recheck + ')' + lab);
      tg(T.n.aliases === V.mergedAway + V.superseded + V.dropped, 'old IDs equal the requirements that leave the left leg (' + T.n.aliases + ' and ' + (V.mergedAway + V.superseded + V.dropped) + ')' + lab);
      tg(T.n.aliases === R.kinds.merged + R.kinds.superseded + R.kinds.dropped + R.kinds.notreq, 'old IDs equal what Results counts as merged, superseded, dropped and not a requirement' + lab);
      tg(T.n.methodShift === V.methodShift && T.n.levelShift === V.levelShift, 'the cases verified a different way, and the items landing on another level, equal the V’s numbers' + lab);
      const gone = {}; T.aliases.forEach((a) => { gone[a.old] = a; });
      tg(Object.keys(gone).length === T.aliases.length, 'an ID retires once' + lab);
      tg(T.aliases.every((a) => !a.now || (/^NEW:/.test(a.now) ? !!CL_BY[a.now.slice(4)] : !gone[a.now] && REQ_BY[a.now])), 'what takes the place of an old ID exists and is not itself leaving' + lab);
      tg(T.aliases.filter((a) => a.srcKind === 'cluster').every((a) => /^NEW:/.test(a.now) ? a.now === 'NEW:' + a.src : !!a.now && CL_BY[a.src].members.some((m) => m.id === a.now)), 'a merged or superseded wording is replaced by one in its own cluster, or by new wording for that cluster' + lab);
      const follow = (id) => { const seen = {}; let x = c.S.rdec[id] && c.S.rdec[id].cover; while (x && !seen[x]) { seen[x] = 1; if (!gone[x]) return x; x = c.S.rdec[x] && c.S.rdec[x].cover; } return ''; };
      tg(T.aliases.filter((a) => a.srcKind === 'single').every((a) => a.src === a.old && a.now === follow(a.old)), 'a dropped requirement is replaced only by the covering requirement that was named, or the one that finally stays if that one leaves too' + lab);
      tg(T.aliases.filter((a) => a.srcKind === 'cluster' && !/^NEW:/.test(a.now)).every((a) => { const cl = CL_BY[a.src], ms = Component.membersOf(c.S, cl), d = Component.dispositionsOf(c.S, cl, ms, {}, {}, c.S.dec[cl.id] !== undefined ? c.S.dec[cl.id] : SEED.dec[cl.id]); return d.by[a.now] && d.by[a.now].kind === 'keep' && (d.by[a.old].kind === 'merged' || d.by[a.old].kind === 'superseded'); }), 'a merged or superseded wording is replaced by the one the decision keeps' + lab);
      tg(T.links.every((x) => x.kind === 'parent_bare' || x.req !== x.to), 'no requirement is moved under itself' + lab);
      // items: each leaving requirement’s items are all there, and none are made up
      const itemsOfGone = T.items.filter((x) => x.action !== 'reread');
      tg(itemsOfGone.every((x) => gone[x.from] && TR_ITEM_BY[x.item] && TR_ITEM_BY[x.item].req === x.from) && Object.keys(gone).every((id) => itemsOfGone.filter((x) => x.from === id).length === VREQ[id].vi), 'every item of a requirement that leaves is listed once and belongs to it' + lab);
      tg(T.items.filter((x) => x.action === 'move').every((x) => x.to && !gone[x.to]), 'an item moves to a requirement that stays' + lab);
      tg(T.items.filter((x) => x.action === 'choose').every((x) => !x.to && gone[x.from].srcKind === 'single'), 'only an item of a requirement dropped with nothing covering it has nowhere to go' + lab);
      tg(T.items.filter((x) => x.action === 'reread').every((x) => !gone[x.from] && c.S.rdec && c.S.rdec[x.from] && c.S.rdec[x.from].outcome === 'reword'), 'an item is read again only when its requirement has new wording' + lab);
      // links: recounted from the children’s side
      const kids = REQS.filter((r) => !gone[r.id] && gone[TR_PARENT[r.id]]).map((r) => r.id).sort().join();
      tg(T.links.filter((x) => x.kind !== 'parent_bare').map((x) => x.req).sort().join() === kids, 'every requirement under one that leaves is listed once (' + kids.split(',').filter(Boolean).length + ')' + lab);
      tg(T.links.filter((x) => x.kind !== 'parent_bare').every((x) => x.from === TR_PARENT[x.req] && (x.kind === 'child_moves') === !!x.to), 'a child says which parent it was under, and whether a new one was found' + lab);
      const bare = REQS.filter((p) => !gone[p.id] && (TR_CHILD[p.id] || []).length > 0 && TR_CHILD[p.id].every((k) => gone[k])).map((p) => p.id).sort().join();
      tg(T.links.filter((x) => x.kind === 'parent_bare').map((x) => x.req).sort().join() === bare, 'a parent is left with nothing below it exactly when all its children leave' + lab);
      tg(T.n.kidsMoved + T.n.kidsLost === kids.split(',').filter(Boolean).length && T.n.bare === bare.split(',').filter(Boolean).length, 'the counts of moved children, children needing a parent and bare parents match' + lab);
      // baselines: exactly the baselined requirements that leave or get new wording
      const bl = Object.keys(gone).filter((id) => TR_BL[id]).concat(T.items.filter((x) => x.action === 'reread').map((x) => x.from).filter((id, i, a) => a.indexOf(id) === i && TR_BL[id]));
      tg(T.bases.map((b) => b.req).sort().join() === bl.sort().join(), 'a baselined requirement appears on the baselines table exactly when it leaves or has new wording' + lab);
      tg(T.bases.every((b) => b.bl === TR_BL[b.req].bl && (REQ_BY[b.req].cid ? b.cr === TR_BL[b.req].cr : b.cr === (c.S.rdec[b.req].cr || ''))), 'each baselined row carries its baseline and the change request that covers it' + lab);
      // the approved-only map is the approved part of the whole one
      const A = Component.trOf(c.S, infos, 'approved');
      const key = (x) => x.old || x.item + '|' + x.action || x.req;
      tg(A.aliases.every((a) => a.status === 'approved') && A.aliases.length === T.aliases.filter((a) => a.status === 'approved').length, 'approved only keeps exactly the approved old IDs' + lab);
      tg(A.items.length === T.items.filter((x) => x.status === 'approved').length && A.bases.length === T.bases.filter((b) => b.status === 'approved').length, 'approved only keeps exactly the approved items and baselines' + lab);
      tg(A.aliases.every((a) => (a.srcKind === 'cluster' ? statusOf(c.S, CL_BY[a.src]) === 'approved' : Component.rdStatus(c.S, REQ_BY[a.old]) === 'approved')), 'an approved row comes from a decision every required lens has signed' + lab);
      tg(A.links.every((x) => x.status === 'approved') && A.n.aliases <= T.n.aliases, 'approved only never shows a change that waits for sign-off' + lab);
    });
    {
      const s0 = look(states.seed), sNW = Object.keys(SEED.dec).filter((id) => SEED.dec[id].newWording);
      tg(sNW.length > 0 && s0.T.aliases.some((a) => /^NEW:/.test(a.now)), 'new wording from a cluster shows as “NEW:” with that cluster, because its ID is given on export');
      tg(s0.T.n.aliases > 20 && s0.T.n.moves > 10 && s0.T.n.kidsMoved > 0, 'the seeded project already moves items and children (' + s0.T.n.aliases + ' IDs, ' + s0.T.n.moves + ' items, ' + s0.T.n.kidsMoved + ' children)');
      const sB = look(states['the only child of its parent is dropped']);
      tg(sB.T.links.some((x) => x.kind === 'parent_bare' && x.req === TR_PARENT[rBare.id]) && sB.T.n.bare >= 1, 'dropping the only child leaves its parent with nothing below');
      const sC = look(states['a drop with a cover, a drop without, a not-a-requirement, a reword']);
      tg(sC.T.items.filter((x) => x.from === rCover.id).length > 0 && sC.T.items.filter((x) => x.from === rCover.id).every((x) => x.action === 'move' && x.to === rTo.id) && sC.T.items.filter((x) => x.from === rParent.id).every((x) => x.action === 'choose'), 'a drop with a covering requirement moves its items there; one without leaves them with nowhere to go');
      tg(sC.T.links.filter((x) => x.from === rParent.id).length === TR_CHILD[rParent.id].length && sC.T.links.filter((x) => x.from === rParent.id).every((x) => x.kind === 'child_needs_parent'), 'children of a requirement removed with nothing covering it need a new parent');
      const sCh = look(states['a covering requirement that is itself dropped']), sCh2 = look(states['a covering requirement dropped with nothing covering it']), sCh3 = look(states['two drops that cover each other']);
      tg(sCh.T.items.filter((x) => x.from === rChainA.id).length > 0 && sCh.T.items.filter((x) => x.from === rChainA.id || x.from === rChainB.id).every((x) => x.action === 'move' && x.to === rChainC.id) && sCh.T.aliases.find((a) => a.old === rChainA.id).now === rChainC.id, 'when a covering requirement is itself dropped, the items follow the chain to the requirement that stays');
      tg(sCh2.T.items.filter((x) => x.from === rChainA.id).every((x) => x.action === 'choose' && !x.to) && sCh2.T.n.choose === VREQ[rChainA.id].vi + VREQ[rChainB.id].vi, 'if the chain ends with nothing covering it, the items have nowhere to go');
      tg(sCh3.T.items.filter((x) => x.from === rChainA.id || x.from === rChainB.id).every((x) => x.action === 'choose') && sCh3.T.n.choose === VREQ[rChainA.id].vi + VREQ[rChainB.id].vi, 'two drops that cover each other end with nowhere to go, not in a loop');
      tg(sC.T.items.filter((x) => x.action === 'reread').length === VREQ[rReword.id].vi && sC.T.items.filter((x) => x.action === 'reread').every((x) => x.from === rReword.id), 'new wording lists its items to read again and moves nothing');
    }
    // the same project twice gives the same map
    tg(JSON.stringify(look(states.seed).T.items) === JSON.stringify(look(states.seed).T.items) && JSON.stringify(Component.trOf(look().c.S, look().infos, '').aliases) === JSON.stringify(look().T.aliases), 'the map is the same every time');

    // ---- the files ----
    {
      const { c, T, infos } = look(states['a drop with a cover, a drop without, a not-a-requirement, a reword']);
      const F = Component.trFile(c.S, T, '');
      tg(F.format === 'reqin-trace-map/1' && F.sample_data === true && /sample values/.test(F.sample_note), 'the file is named, versioned and says its data is sample data');
      tg(F.old_ids.length === T.aliases.length && F.verification_items.length === T.items.length && F.parent_child_links.length === T.links.length && F.baselines.length === T.bases.length && JSON.stringify(F.counts) === JSON.stringify(T.n), 'the file holds every row and the counts');
      tg(JSON.stringify(JSON.parse(JSON.stringify(F))) === JSON.stringify(F), 'the file is plain JSON');
      tg(F.verification_items.every((x) => (x.action === 'move') === (x.move_to !== null)), 'only an item that moves says where to');
      // csv: read it back with separate code
      const parse = (text) => { const rows = []; let row = [], cell = '', q = false; for (let i = 0; i < text.length; i++) { const ch = text[i]; if (q) { if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else q = false; } else cell += ch; } else if (ch === '"') q = true; else if (ch === ',') { row.push(cell); cell = ''; } else if (ch === '\r') { /* skip */ } else if (ch === '\n') { row.push(cell); rows.push(row); row = []; cell = ''; } else cell += ch; } return rows; };
      TR_TABS.forEach((t) => {
        const rows = parse(Component.trCsv(T, t.k));
        tg(rows.length === T[t.k].length + 1 && rows[0].join() === TR_CSV[t.k].head.join() && rows.every((r) => r.length === TR_CSV[t.k].head.length), 'the CSV for “' + t.name + '” has a header and one row per row, all the same width (' + (rows.length - 1) + ')');
      });
      tg(parse(Component.trCsv(T, 'items')).slice(1).map((r) => r[0]).join() === T.items.map((x) => x.item).join(), 'the CSV rows come in the same order as the table');
      tg(Component.trCell('=1+1') === "'=1+1" && Component.trCell('@x') === "'@x" && Component.trCell('-5') === "'-5" && Component.trCell('a,b') === '"a,b"' && Component.trCell('say "hi"') === '"say ""hi"""' && Component.trCell('a\nb') === '"a\nb"' && Component.trCell(null) === '' && Component.trCell('plain') === 'plain', 'a cell that would run as a formula is marked as text, and commas, quotes and line breaks are quoted');
      const ex = new Component.Component(); ex.setState({ view: 'export' });
      ['sphinx', 'strictdoc', 'docx', 'reqif'].forEach((f) => { const cc = mk({ fmt: f }); tg(/trace-map\.json/.test(cc.valsExport(cc.S).packageFiles) && /alias-map\.csv/.test(cc.valsExport(cc.S).packageFiles), 'the package for ' + f + ' lists the alias map and the trace map'); });
    }

    // ---- the screens ----
    const five = states['a drop with a cover, a drop without, a not-a-requirement, a reword'];
    TR_TABS.forEach((t) => {
      run('export trace ' + t.k, (c) => base(c, Object.assign({ view: 'export', trTab: t.k }, five)));
      run('export trace all ' + t.k, (c) => base(c, Object.assign({ view: 'export', trTab: t.k, trOnly: 'all' }, five)));
    });
    {
      const rB = lones.find((r) => TR_BL[r.id] && VREQ[r.id].vi > 0);
      run('single baselined drop form', (c) => base(c, { view: 'explorer', xPick: rB.id, rform: { [rB.id]: { kind: 'drop', reason: 'S-OBS', note: 'No longer applies after the redesign.', cr: '', edit: true } } }));
      run('single baselined reword form', (c) => base(c, { view: 'explorer', xPick: rB.id, rform: { [rB.id]: { kind: 'reword', reason: 'S-NUM', text: rB.text.replace(/\bshall\b/, 'shall promptly'), note: 'Clarified.', cr: 'CR-2041', edit: true } } }));
      run('single baselined decided', (c) => base(c, { view: 'explorer', xPick: rB.id, rdec: { [rB.id]: mkD(rB, 'drop', { cr: 'CR-2041' }) } }));
    }
    run('export trace empty', (c) => base(c, { view: 'export', rdec: {}, dec: Object.fromEntries(Object.keys(SEED.dec).map((id) => [id, null])), trOnly: 'approved' }));
    run('export trace message', (c) => base(c, { view: 'export', trMsg: 'Prepared trace-map.json with 12 rows (approved changes only).' }));
    {
      const dcl = CLUSTERS.find((c) => SEED.dec[c.id] && c.members.length > 2 && look().T.aliases.some((a) => a.src === c.id));
      run('review a decided cluster with moves', (c) => base(c, { view: 'review', selected: dcl.id }));
      const bcl = CLUSTERS.find((c) => c.baselined);
      run('review a baselined cluster', (c) => base(c, { view: 'review', selected: bcl.id }));
      // the cluster panel says the same as the map
      const cc = mk({ view: 'review', selected: dcl.id }), vv = cc.renderVals(), txt = vv.d.vee.lines.map((l) => l.t).join(' | '), T = Component.trOf(cc.S, cc.allInfos(cc.S), ''), mine = T.aliases.filter((a) => a.src === dcl.id), mvs = T.items.filter((x) => x.src === dcl.id && x.action === 'move').length;
      tg(mine.length > 0 && new RegExp('This decision: ' + mine.length + ' requirement' + (mine.length === 1 ? ' leaves' : 's leave') + ', ' + mvs + ' verification item').test(txt), 'a decided cluster says how many requirements leave and how many items move, the same as the map (' + txt.slice(-160) + ')');
      const bc = mk({ view: 'review', selected: bcl.id }).renderVals().d.vee.lines.map((l) => l.t).join(' | ');
      tg(new RegExp('baseline BL-\\d+').test(bc) && bc.indexOf(bcl.cr) >= 0, 'a cluster with a baselined wording names the baseline and its change request');
      const ocl = CLUSTERS.find((c) => c.members.length > 1 && !SEED.dec[c.id] && TR_CHILD[c.members[0].id] && TR_CHILD[c.members[0].id].length);
      const oc = mk({ view: 'review', selected: ocl.id }).renderVals().d.vee.lines.map((l) => l.t).join(' | ');
      tg(/requirements? sits? below them/.test(oc) && !/This decision/.test(oc), 'an undecided cluster says what sits below it and does not claim a decision');
    }

    // ---- handlers on the Export page ----
    {
      const c = mk(five); let v = c.renderVals();
      tg(v.trOnlyApproved && !v.trOnlyAll && v.trTabs.length === 4 && v.trTabs[0].pressed === 'true' && v.trTabs.every((t, i) => i === 0 || t.pressed === 'false'), 'it opens on approved changes and the first table');
      const nApproved = v.trRows.length;
      v.trPickAll(); v = c.renderVals();
      tg(c.S.trOnly === 'all' && v.trOnlyAll && !v.trOnlyApproved, 'showing every decided change switches the scope');
      v.trTabs[1].pick(); v = c.renderVals();
      tg(c.S.trTab === 'items' && v.trTabs[1].pressed === 'true' && v.trCols[0].h === 'Item' && v.trRows.length === Math.min(12, c.traceShown(c.S).items.length), 'choosing a table shows its columns and at most twelve rows');
      tg(v.trHasMore === (c.traceShown(c.S).items.length > 12) && (!v.trHasMore || /more in the file/.test(v.trMore)), 'rows past the twelfth are counted, not listed');
      const before = c.S.events.length;
      v.trJson(); v = c.renderVals();
      tg(/^Prepared trace-map\.json with \d+ rows? \(every decided change\)\.$/.test(c.S.trMsg) && c.S.events.length === before + 1 && /Downloaded trace-map\.json/.test(c.S.events[c.S.events.length - 1].text), 'the JSON download says what it made and writes to the audit log');
      v.trCsv(); v = c.renderVals();
      tg(/verification-items\.csv/.test(c.S.trMsg) && /Downloaded verification-items\.csv/.test(c.S.events[c.S.events.length - 1].text), 'the CSV download is named for the table shown');
      const e = mk({ rdec: {}, dec: Object.fromEntries(Object.keys(SEED.dec).map((id) => [id, null])) }).renderVals();
      tg(e.trEmpty && e.trNoFile === true && e.trNoFileCsv === true && /No approved change/.test(e.trEmptyText), 'with nothing approved the downloads are off and the page says why');
    }

    // ---- baselines and the change request on a single decision ----
    {
      const id = rBl.id, form = (o) => ({ [id]: Object.assign({ edit: true, kind: 'drop', reason: 'S-OBS', note: 'No longer applies after the redesign.', cr: '' }, o) });
      const probs = (o) => mk({ view: 'explorer', xPick: id, rform: form(o) }).renderVals().sp.problems.map((p) => p.t).join(' | ');
      tg(/baseline BL-\d+/.test(probs({})) && /change request/i.test(probs({})), 'dropping a baselined requirement asks for the change request');
      tg(/change request/i.test(probs({ cr: 'CR-1' })) && /change request/i.test(probs({ cr: 'ticket 2041' })), 'a change request has to look like one: CR-, then three to six digits');
      tg(probs({ cr: 'CR-2041' }) === '' && probs({ cr: ' cr-2041 ' }) === '', 'a valid change request clears the problem, whatever the case or spaces');
      tg(/change request/i.test(probs({ kind: 'reword', reason: 'S-NUM', text: REQ_BY[id].text.replace(/\bshall\b/, 'shall promptly') })) , 'new wording on a baselined requirement asks for it too');
      tg(!/change request/i.test(probs({ kind: 'keep', reason: 'S-OK', note: '' })) && !/change request/i.test(probs({ kind: 'ask', reason: '', q: 'Still needed?' })), 'keeping or asking does not');
      const free = lones.find((r) => !TR_BL[r.id]);
      tg(!/change request/i.test(mk({ view: 'explorer', xPick: free.id, rform: { [free.id]: { edit: true, kind: 'drop', reason: 'S-OBS', note: 'No longer applies after the redesign.' } } }).renderVals().sp.problems.map((p) => p.t).join(' | ')), 'a requirement outside any baseline does not');
      const c = mk({ view: 'explorer', xPick: id, rform: form({ cr: ' cr-2041 ' }) }); let v = c.renderVals();
      tg(v.sp.needCr && v.sp.crV === ' cr-2041 ' && !v.sp.noRecord, 'the form shows the change request field and can be recorded');
      v.sp.record();
      tg(c.S.rdec[id] && c.S.rdec[id].cr === 'CR-2041' && /change request CR-2041/.test(c.S.events[c.S.events.length - 1].text), 'recording keeps the change request, tidied, and writes it to the log');
      v = c.renderVals();
      tg(v.sp.d.lines.some((l) => l.k === 'Change request' && /CR-2041/.test(l.v)), 'the decision on record shows the change request');
      const T = Component.trOf(c.S, c.allInfos(c.S), '');
      tg(T.bases.some((b) => b.req === id && b.cr === 'CR-2041' && b.change === 'Dropped'), 'and the baselines table carries it');
      const f2 = mk({ view: 'explorer', xPick: free.id, rform: { [free.id]: { edit: true, kind: 'drop', reason: 'S-OBS', note: 'No longer applies after the redesign.', cr: 'CR-9999' } } }); f2.renderVals().sp.record();
      tg(f2.S.rdec[free.id] && f2.S.rdec[free.id].cr === '', 'a change request typed for a requirement outside any baseline is not kept');
    }

    // ---- what the single-requirement panel says it will move ----
    {
      const imp = (r, kind, cover) => Component.trImpactLines(mk().S, r, kind, cover), txt = (o) => o.lines.map((l) => l.k + ': ' + l.v).join(' | ');
      tg(imp(rParent, 'keep').lines.length === 1 && /Nothing/.test(txt(imp(rParent, 'keep'))) && !imp(rParent, 'ask').on, 'keeping moves nothing and asking says nothing');
      const nk = (TR_CHILD[rParent.id] || []).length, ni = VREQ[rParent.id].vi;
      const d1 = imp(rParent, 'drop', ''), d2 = imp(rParent, 'drop', rTo.id);
      tg(new RegExp(ni + ' items? (has|have) no requirement to point at').test(txt(d1)) && new RegExp(nk + ' requirements? needs? a new parent').test(txt(d1)), 'a drop with nothing covering it says how many items and children have nowhere to go (' + txt(d1).slice(0, 200) + ')');
      tg(new RegExp(ni + ' items? moves? to ' + rTo.id).test(txt(d2)) && new RegExp(nk + ' requirements? moves? under ' + rTo.id).test(txt(d2)), 'with a covering requirement it says they move there');
      tg(/left with nothing below it/.test(txt(imp(rBare, 'drop', ''))) && /keeps its other requirements/.test(txt(imp(rParent, 'drop', ''))) === !!(TR_PARENT[rParent.id] && TR_CHILD[TR_PARENT[rParent.id]].length > 1), 'it says when the parent would be left with nothing below it');
      tg(new RegExp(VREQ[rReword.id].vi + ' items? (is|are) to be read again').test(txt(imp(rReword, 'reword'))), 'new wording says how many items are to be read again');
      tg(/In baseline BL-\d+\. This change needs a change request/.test(txt(imp(rBl, 'drop', ''))) && /Not in a baseline/.test(txt(imp(rParent, 'drop', ''))), 'and whether a baseline is involved');
      // the numbers in the sentences are the numbers in the map once the decision is recorded
      const c = mk({ view: 'explorer', xPick: rParent.id, rdec: { [rParent.id]: mkD(rParent, 'drop') } }), T = Component.trOf(c.S, c.allInfos(c.S), ''), w = Component.trImpactOne(c.S, rParent, 'drop', '');
      tg(w.items.length === T.items.filter((x) => x.from === rParent.id).length && w.kids.length === T.links.filter((x) => x.from === rParent.id && x.kind !== 'parent_bare').length, 'the panel’s numbers are the map’s numbers for the same requirement');
      tg(txt(c.renderVals().sp.d.imp) === txt(imp(rParent, 'drop', '')), 'the recorded decision shows the same lines the form showed');
    }
  }

  // ---- keeping the work: what is kept, what a file may bring back, and what is refused ----
  {
    const kg = (ok, msg) => { if (!ok) flag('KEEP: ' + msg); };
    const C = Component, { persistCheck, persistFile, persistPick, persistCounts, persistSaid, persistHasWork, chainCheck, PERSIST_KEYS, PERSIST_BY_CLUSTER, PERSIST_BY_REQ, PERSIST_FORMAT, PERSIST_STORE, PERSIST_MAX, EV_SEED, REQ_BY } = C;
    const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const mkc = (st) => { const c = new C.Component(); c.setState(Object.assign({ view: 'home' }, st || {})); return c; };
    const lonesK = REQS.filter((r) => !r.cid && C.VREQ[r.id].vi > 0);
    const cl = CLUSTERS.find((c) => c.members.length > 1 && !SEED.dec[c.id]), cl2 = CLUSTERS.find((c) => c.members.length > 1 && !SEED.dec[c.id] && c !== cl);
    const mkDec = (c, o) => Object.assign({ outcome: 'merge', strategy: 'member', member: c.members[0].id, text: c.members[0].text, newWording: false, weakening: false, covers: c.members.map((m) => m.id), kept: [], reason: 'R-STR', note: 'Same obligation, checked against the strictest member.', by: 'Sam Okafor', lens: 'SE', at: '6 Oct', rev: 'R3', vs: '', share: null, revs: [] }, o || {});
    const mkRd = (r, kind) => ({ outcome: kind, reason: 'S-OK', note: 'Checked.', text: '', cover: '', q: '', to: r.owner, newWording: false, weakening: false, by: 'Sam Okafor', lens: 'SE', at: '6 Oct', rev: 'S1', asked: null });
    const rd1 = lonesK[0];
    const goldKey = C.goldPlan().items[0].key;
    // a state with something of every kind in it, built through the same calls the page makes
    const seed = mkc();
    let ev = seed.mk([], 'human', 'Sam Okafor · SE', 'Decided ' + cl.id, cl.id);
    ev = seed.mk(ev, 'human', 'Priya Raman · PE', 'Signed ' + cl.id, cl.id);
    const rich = Object.assign({}, C.DEFAULTS, {
      person: 'priya', dec: { [cl.id]: mkDec(cl) }, sign: { [cl.id]: { SE: { by: 'Morgan Hale', at: '8 Oct', rev: 'R3' }, PE: { by: 'Priya Raman', at: '9 Oct', rev: 'R3' } } }, rdec: { [rd1.id]: mkRd(rd1, 'keep') },
      hand: { [cl2.id]: { from: 'sam', to: 'priya', ask: 'check', note: 'Look at M2.', at: '10 Oct', status: 'waiting', reply: '', draft: '' } },
      gold: Object.assign({}, C.DEFAULTS.gold, { labels: { [goldKey]: { sam: { v: 'equiv', note: 'same duty', t: '10 Oct' } } } }), events: ev, liveVer: { [cl.id]: 2 }
    });

    // ---- what is kept ----
    kg(PERSIST_KEYS.every((k) => C.DEFAULTS[k] !== undefined) && new Set(PERSIST_KEYS).size === PERSIST_KEYS.length, 'every kept key has a default, once');
    kg(PERSIST_BY_CLUSTER.concat(PERSIST_BY_REQ).every((k) => PERSIST_KEYS.indexOf(k) >= 0), 'the maps that are checked entry by entry are kept maps');
    kg(['view', 'selected', 'preview', 'qTab', 'qSearch', 'xPick', 'chatOpen', 'chatInput', 'verified', 'tamper', 'keepMsg', 'keepAsk', 'trMsg', 'drop', 'docSel', 'openVer'].every((k) => PERSIST_KEYS.indexOf(k) < 0), 'which screen is open, filters and half-typed boxes are not kept');
    kg(['dec', 'sign', 'res', 'hand', 'rdec', 'gold', 'events', 'claims', 'peeled', 'objections', 'adjud', 'why', 'ref'].every((k) => PERSIST_KEYS.indexOf(k) >= 0), 'decisions, sign-offs, hand-offs, labels and the record are kept');
    kg(!persistHasWork(Object.assign({}, C.DEFAULTS)) && !persistHasWork(Object.assign({}, C.DEFAULTS, { person: 'priya', fmt: 'docx' })), 'a fresh page, or only a change of person or format, is not work worth keeping');
    kg(persistHasWork(rich) && [{ dec: rich.dec }, { rdec: rich.rdec }, { hand: rich.hand }, { events: ev }, { gold: rich.gold }, { sign: rich.sign }].every((o) => persistHasWork(Object.assign({}, C.DEFAULTS, o))), 'each kind of work on its own counts as work');
    kg(persistKindOk(rich), 'every kept key has the type its default has');
    function persistKindOk(S) { return PERSIST_KEYS.every((k) => Array.isArray(S[k]) === Array.isArray(C.DEFAULTS[k]) && (S[k] === null) === (C.DEFAULTS[k] === null) && typeof S[k] === typeof C.DEFAULTS[k]); }

    // ---- the file and the round trip ----
    const file = JSON.parse(JSON.stringify(persistFile(rich, '2026-10-14T12:00:00.000Z')));
    kg(file.format === PERSIST_FORMAT && file.project.fingerprint === C.persistFingerprint() && file.saved === '2026-10-14T12:00:00.000Z', 'the file says what it is, which project it belongs to and when it was saved');
    kg(eq(file.state, persistPick(rich)) && !('view' in file.state) && !('keepMsg' in file.state), 'the file holds the kept keys and nothing else');
    kg(eq(file.counts, persistCounts(rich)) && file.counts.decisions === 2 && file.counts.signoffs === 2 && file.counts.handoffs === 1 && file.counts.labels === 1 && file.counts.events === 2, 'the file’s counts are what the work has in it');
    kg(persistSaid({ decisions: 1, signoffs: 0, handoffs: 1, labels: 2, events: 1 }, ['decisions', 'signoffs', 'handoffs', 'labels', 'events']) === '1 decision, 0 sign-offs, 1 hand-off, 2 labels, 1 event' && persistSaid({ decisions: 2, signoffs: 1 }, ['decisions', 'signoffs']) === '2 decisions, 1 sign-off', 'the counts are said in the singular where the number is one');
    const back = persistCheck(file);
    kg(back.ok && back.dropped === 0 && back.problems.length === 0 && eq(back.state, persistPick(rich)) && eq(back.counts, persistCounts(rich)), 'a file the page wrote is accepted whole and gives back exactly what went in');
    kg(back.ok && back.notes.some((n) => /record of events is intact \(5 entries\)/.test(n)), 'the check says the record of events is intact and how many entries it has');
    kg(mkc().keepProbe(back.state) === '', 'every screen can be drawn with what the file brings back');
    kg(eq(persistCheck(JSON.parse(JSON.stringify(persistFile(Object.assign({}, C.DEFAULTS), 'x')))).state, persistPick(Object.assign({}, C.DEFAULTS))) && persistCheck(JSON.parse(JSON.stringify(persistFile(Object.assign({}, C.DEFAULTS), 'x')))).ok, 'an empty project round-trips too');

    // ---- what is refused, and why ----
    const clone = () => JSON.parse(JSON.stringify(file));
    const refused = (name, f, re) => { const r = persistCheck(f); kg(!r.ok && r.problems.length > 0 && Object.keys(r.state).length === 0 && (!re || re.test(r.problems[0])), name + ' is refused' + (r.ok ? ' (it was accepted)' : ' with the wrong reason: ' + r.problems[0])); };
    [[null, 'null'], [[], 'a list'], ['text', 'text'], [7, 'a number'], [{}, 'an empty object']].forEach(([v, n]) => refused(n, v));
    { const f = clone(); f.format = 'reqin-project-state/2'; refused('a newer format', f, /format/i); }
    { const f = clone(); delete f.format; refused('a file with no format', f, /missing|not a saved project/i); }
    { const f = clone(); delete f.state; refused('a file with no work in it', f, /no saved work/i); }
    { const f = clone(); f.project.fingerprint = 'abc123'; refused('work from another project', f, /different project/i); }
    { const f = clone(); delete f.project; refused('a file that does not say which project', f, /different project/i); }
    { const f = clone(); f.state.dec = []; refused('a map that is a list', f, /dec/); }
    { const f = clone(); f.state.events = {}; refused('events that are not a list', f, /events/); }
    { const f = clone(); f.state.person = 'nobody'; refused('a person the project does not have', f, /not one of the people/i); }
    { const f = clone(); f.state.events[0].text = 'Changed after the fact'; const r = persistCheck(f); kg(!r.ok && /changed/i.test(r.problems[0]) && /entry 4/.test(r.problems[0]), 'an edited entry in the record is refused and the entry is named (' + r.problems[0] + ')'); }
    { const f = clone(); f.state.events.reverse(); refused('events in another order', f, /changed|shape/i); }
    { const f = clone(); f.state.events = f.state.events.slice(1); refused('a record with its first entry removed', f, /changed/i); }
    { const f = clone(); delete f.state.events[0].hash; refused('an event with a missing field', f, /record of events/i); }
    { const f = clone(); f.state.events[1].time = { x: 1 }; refused('an event whose time is not text (the one field the fingerprint does not cover)', f, /not in the shape/i); }
    { const f = clone(); f.state.events[1].seq = '5'; refused('an event whose number is text', f, /record of events/i); }
    { const f = clone(); f.state.events = new Array(20001).fill(f.state.events[0]); refused('a record longer than the page ever writes', f, /not in the shape/i); }
    { const f = clone(); f.state.gold = { labels: [] }; refused('labels in another shape', f, /labels/i); }
    { const f = clone(); f.state.gold.cut = 7; refused('a cut-off outside 0 to 1', f, /labels/i); }
    // entries that point at nothing are left out, counted and said
    {
      const f = clone();
      f.state.dec['CL-9999'] = mkDec(cl); f.state.sign['CL-9999'] = { SE: { by: 'x' } }; f.state.rdec['REQ-NOPE-1'] = mkRd(rd1, 'keep'); f.state.hand['CL-0001'] = { status: 'waiting' };
      f.state.dec[cl2.id] = 'not a decision'; f.state.rdec[REQS[3].id] = { outcome: 'bogus', by: 'x', rev: 'S1' }; f.state.sign[cl2.id] = { LAW: { by: 'x' } };
      f.state.gold.labels['no-such-pair'] = { sam: { v: 'equiv' } }; f.state.gold.labels[goldKey].sam.v = 'maybe';
      const r = persistCheck(f);
      kg(r.ok && r.dropped === 9 && r.notes.some((n) => /9 entries pointed/.test(n)), 'entries for something the project does not have, or in the wrong shape, are left out and counted (' + r.dropped + ')');
      kg(r.ok && eq(Object.keys(r.state.dec), [cl.id]) && eq(Object.keys(r.state.rdec), [rd1.id]) && eq(Object.keys(r.state.sign), [cl.id]) && Object.keys(r.state.hand).length === 1 && Object.keys(r.state.gold.labels).length === 0, 'what stays is exactly the entries that make sense');
    }
    // keys that are not the page's, and names that would reach into the object itself
    {
      const f = JSON.parse(JSON.stringify(file).replace('"state":{', '"state":{"__proto__":{"polluted":1},"view":"gold","evil":{"x":1},'));
      const r = persistCheck(f);
      kg(r.ok && !('view' in r.state) && !('evil' in r.state) && !Object.prototype.hasOwnProperty.call(r.state, '__proto__') && ({}).polluted === undefined && r.notes.filter((n) => /Ignored/.test(n)).length === 3, 'keys that are not the page’s are ignored and said, and nothing reaches the object’s prototype');
      const g = JSON.parse(JSON.stringify(file).replace('"dec":{', '"dec":{"__proto__":{"outcome":"merge"},'));
      const r2 = persistCheck(g);
      kg(r2.ok && !Object.prototype.hasOwnProperty.call(r2.state.dec, '__proto__') && r2.dropped === 1 && ({}).outcome === undefined, 'a decision named like the object’s prototype is dropped');
    }
    {
      // names every object has are not names the project has
      const f = clone();
      ['constructor', 'toString', 'hasOwnProperty', 'valueOf'].forEach((n) => { f.state.dec[n] = mkDec(cl); f.state.hand[n + ':x'] = null; f.state.rdec[n] = mkRd(rd1, 'keep'); });
      f.state.rdec[REQS[5].id] = mkRd(rd1, 'constructor'); f.state.gold.labels[goldKey].sam.v = 'toString'; f.state.gold.labels.constructor = { sam: { v: 'equiv' } };
      const r = persistCheck(f);
      kg(r.ok && eq(Object.keys(r.state.dec), [cl.id]) && eq(Object.keys(r.state.rdec), [rd1.id]) && Object.keys(r.state.hand).length === 1 && Object.keys(r.state.gold.labels).length === 0, 'names every object has (constructor, toString) are not taken for clusters, requirements, outcomes or labels');
    }
    {
      const good = mkDec(cl), bad = (o) => Object.assign({}, good, o);
      const cases = [
        ['an outcome the page does not have', bad({ outcome: 'bogus' })], ['a cover that is not a requirement of the project', bad({ covers: ['REQ-NOPE'] })], ['a list of kept wordings that is not a list', bad({ kept: 'x' })],
        ['no list of revisions', (() => { const d = bad({}); delete d.revs; return d; })()], ['no author', bad({ by: 5 })], ['a flag that is text', bad({ newWording: 'yes' })], ['a share that is a number', bad({ share: 5 })],
        ['revisions that are not objects', bad({ revs: [1] })], ['text that is a list', bad({ text: [] })]
      ];
      cases.forEach(([n, d]) => { const f = clone(); f.state.dec[cl2.id] = d; const r = persistCheck(f); kg(r.ok && r.dropped === 1 && !(cl2.id in r.state.dec) && cl.id in r.state.dec, 'a decision with ' + n + ' is left out and counted'); });
      [['a share that is empty', bad({ share: null })], ['a share with numbers', bad({ share: { a: 1 } })], ['a note about where the wording came from', bad({ ownFrom: 'assistant' })], ['an empty list of kept wordings', bad({ kept: [] })], ['a withdrawn decision', null]].forEach(([n, d]) => { const f = clone(); f.state.dec[cl2.id] = d; const r = persistCheck(f); kg(r.ok && r.dropped === 0 && cl2.id in r.state.dec, 'a decision with ' + n + ' is kept'); });
      const rd = mkRd(rd1, 'keep'), badR = (o) => Object.assign({}, rd, o);
      [['a note that is a number', badR({ note: 5 })], ['no reviewer', badR({ by: undefined })], ['a flag that is text', badR({ weakening: 'no' })], ['an "asked" that is a number', badR({ asked: 5 })]].forEach(([n, d]) => { const f = clone(); f.state.rdec[REQS[7].id] = d; const r = persistCheck(f); kg(r.ok && r.dropped === 1 && !(REQS[7].id in r.state.rdec), 'a requirement decision with ' + n + ' is left out'); });
      [['a waiting hand-off to someone not in the project', { from: 'sam', to: 'zed', status: 'waiting' }], ['a hand-off in a state the page does not have', { from: 'sam', to: 'priya', status: 'sulking' }], ['a hand-off with a note that is a list', { from: 'sam', to: 'priya', status: 'waiting', note: [] }]].forEach(([n, h]) => { const f = clone(); f.state.hand[cl.id] = h; const r = persistCheck(f); kg(r.ok && r.dropped === 1 && !(cl.id in r.state.hand), n + ' is left out'); });
      { const f = clone(); f.state.sign[cl2.id] = { SE: { by: 'x', at: 5 } }; const r = persistCheck(f); kg(r.ok && r.dropped === 1, 'a sign-off with a date that is a number is left out'); }
      { const f = clone(); f.state.claims = { [cl.id]: { by: 5 }, [cl2.id]: { by: 'Priya Raman', lens: 'PE', mins: 3 } }; const r = persistCheck(f); kg(r.ok && r.dropped === 1 && cl2.id in r.state.claims, 'a claim by something that is not a name is left out and a real one stays'); }
      { const f = clone(); f.state.sib = { [cl.id]: [], [cl2.id]: [{ rev: 'R1', text: 'a' }, { rev: 'R2', text: 'b' }] }; const r = persistCheck(f); kg(r.ok && r.dropped === 1 && cl2.id in r.state.sib, 'two versions of a decision are kept only when there are two'); }
      { const f = clone(); f.state.chat = { [cl.id]: 'hello' }; f.state.why = { [cl.id]: 'yes' }; f.state.liveVer = { [cl.id]: '3' }; const r = persistCheck(f); kg(r.ok && r.dropped === 3, 'a chat that is text, a flag that is text and a version that is text are left out'); }
    }
    { const f = clone(); f.state.scope = 'Nowhere'; const r = persistCheck(f); kg(r.ok && !('scope' in r.state) && r.notes.some((n) => /allocation is not in this project/.test(n)), 'an allocation the project does not have falls back to the whole project, and says so'); }
    kg(chainCheck(EV_SEED) === 'ok' && chainCheck(EV_SEED.concat(ev)) === 'ok' && chainCheck(EV_SEED.concat(ev.slice(1))) === 'fail:5' && chainCheck(EV_SEED.concat([Object.assign({}, ev[0], { actor: 'Someone else' })])) === 'fail:4', 'the chain check passes a real chain and fails at the first entry that does not follow');

    // ---- the browser's store, with a stand-in that can be told to fail ----
    {
      const timers = new Map(); let tid = 0; const realST = global.setTimeout, realCT = global.clearTimeout;
      global.setTimeout = (fn) => { timers.set(++tid, fn); return tid; }; global.clearTimeout = (n) => { timers.delete(n); };
      const flush = () => { const t = [...timers.values()]; timers.clear(); t.forEach((fn) => fn()); };
      const store = (opts) => { const d = {}, o = opts || {}; return { d, sets: 0, getItem(k) { return k in d ? d[k] : null; }, setItem(k, v) { if (o.dead || (o.full && k === PERSIST_STORE)) throw new Error('blocked'); this.sets++; d[k] = String(v); }, removeItem(k) { delete d[k]; } }; };
      const withStore = (st, fn) => { global.window = { localStorage: st }; try { return fn(); } finally { delete global.window; } };
      try {
        // autosave: nothing before there is work, then the work, once, and only when it changed
        const st = store();
        withStore(st, () => {
          const c = new C.Component(); c.setState({ view: 'home' }); flush();
          kg(!(PERSIST_STORE in st.d), 'a page with no work writes nothing');
          c.setState({ dec: Object.assign({}, c.S.dec, { [cl.id]: mkDec(cl) }), liveVer: { [cl.id]: 2 } }); kg(timers.size === 1, 'a change schedules one save');
          c.setState({ person: 'priya' }); kg(timers.size === 1, 'a second change before it fires replaces it, so two quick changes make one save');
          flush();
          kg(PERSIST_STORE in st.d && c.state.keepStatus === 'saved' && !!c.state.keepAt, 'the work is written once the pause is over, and the page knows it was kept');
          const n = st.sets; c.setState({ qTab: 'all' }); flush();
          kg(st.sets === n, 'a change to what is not kept (a filter) does not write again');
          const raw = JSON.parse(st.d[PERSIST_STORE]);
          kg(raw.format === PERSIST_FORMAT && raw.opened === true && raw.state.dec[cl.id].rev === 'R3' && raw.state.person === 'priya', 'what is written is the same file format, marked as opened');
        });
        // restore: a new page picks up where the old one stopped, at Home, with nothing marked as changed behind the person's back
        withStore(st, () => {
          const c2 = new C.Component(), S = c2.S;
          kg(S.dec[cl.id] && S.dec[cl.id].rev === 'R3' && S.person === 'priya' && S.view === 'home' && !!S.keepRestored && S.keepStatus === 'saved', 'a new page restores the work, signs in the same person and opens at Home');
          const v = c2.renderVals();
          kg(v.kRestored && /Picked up where you left off/.test(v.kRestoredText) && v.kHead === 'Your work' && !v.kStartDisabled, 'Home says it picked up where the person left off, and Start over is available');
          kg(eq(c2.S.liveVer, { [cl.id]: 2 }) && eq(c2.S.openVer, c2.S.liveVer), 'nothing restored reads as changed after it was opened');
        });
        // an unfinished import is restored at the start, not in the middle
        { const s2 = store(); withStore(s2, () => { const c = new C.Component(); c.setState({ view: 'open', dec: { [cl.id]: mkDec(cl) } }); flush(); kg(JSON.parse(s2.d[PERSIST_STORE]).opened === false, 'work saved before the project was opened is marked so'); kg(new C.Component().S.view === 'open', 'and the next page starts at Open'); }); }
        // a store holding something that is not this app's work is removed, not trusted
        { const bad = store(); bad.d[PERSIST_STORE] = '{not json'; withStore(bad, () => { const c = new C.Component(); kg(!(PERSIST_STORE in bad.d) && c.S.view === 'open' && !c.S.keepRestored, 'unreadable saved work is removed and the page starts clean'); }); }
        { const bad = store(), f = clone(); f.state.events[0].text = 'edited'; bad.d[PERSIST_STORE] = JSON.stringify(f); withStore(bad, () => { const c = new C.Component(); kg(!(PERSIST_STORE in bad.d) && !c.S.keepRestored && c.S.keepMsg && c.S.keepMsg.bad && /changed/.test(c.S.keepMsg.text) && Object.keys(c.S.dec).length === 0, 'saved work whose record was changed is removed, nothing from it is used and the page says why'); }); }
        { const big = store(); big.d[PERSIST_STORE] = JSON.stringify(file) + ' '.repeat(PERSIST_MAX); withStore(big, () => { const c = new C.Component(); kg(!(PERSIST_STORE in big.d) && !c.S.keepRestored, 'saved work larger than the page ever writes is removed unread, even when it is otherwise a good file'); }); }
        // storage that does not work: said plainly, and the page works
        { const dead = store({ dead: true }); withStore(dead, () => { const c = new C.Component(); c.setState({ view: 'home', dec: { [cl.id]: mkDec(cl) } }); flush(); const v = c.renderVals(); kg(c.S.keepStatus === 'off' && v.kWarn && /not being kept/.test(v.kHead) && /Save a file/.test(v.kLine), 'storage that is blocked is said plainly, with what to do'); }); }
        { const full = store({ full: true }); withStore(full, () => { const c = new C.Component(); c.setState({ view: 'home', dec: { [cl.id]: mkDec(cl) } }); flush(); const v = c.renderVals(); kg(c.S.keepStatus === 'full' && v.kWarn && /too large/.test(v.kHead), 'storage that is full is said plainly, with what to do'); }); }
        { const c = new C.Component(); c.setState({ dec: { [cl.id]: mkDec(cl) } }); flush(); kg(c.S.keepStatus === 'off' || c.S.keepStatus === 'ready', 'with no browser storage at all, the page still works (' + c.S.keepStatus + ')'); }
        // load a file: nothing changes until the person says so
        withStore(store(), () => {
          const c = mkc({ person: 'sam' }), before = JSON.stringify(c.S);
          c.keepRead(JSON.stringify(file), 'work.json');
          kg(c.S.keepAsk === 'load' && !!c._pending && c.S.keepSummary.length >= 2 && /work\.json/.test(c.S.keepSummary[0]) && JSON.stringify(Object.assign({}, c.S, { keepAsk: '', keepSummary: [] })) === JSON.stringify(Object.assign(JSON.parse(before), {})), 'a good file is checked and a summary is shown, and nothing is replaced yet');
          const v = c.renderVals(); v.kCancel(); kg(c.S.keepAsk === '' && !c._pending && Object.keys(c.S.dec).length === 0, 'cancelling leaves the work as it was');
          c.keepRead(JSON.stringify(file), 'work.json'); c.renderVals().kDoLoad();
          kg(eq(c.S.dec, rich.dec) && eq(c.S.rdec, rich.rdec) && c.S.view === 'home' && c.S.keepAsk === '' && c.S.person === 'priya', 'loading replaces the work with the file’s');
          const last = c.S.events[c.S.events.length - 1];
          kg(c.S.events.length === ev.length + 1 && /Loaded saved work from work\.json/.test(last.text) && chainCheck(EV_SEED.concat(c.S.events)) === 'ok' && eq(c.S.events.slice(0, ev.length), ev), 'loading adds one entry to the record, the chain still holds and the earlier entries are untouched');
          kg(eq(c.S.openVer, c.S.liveVer), 'what is loaded does not read as changed behind the person’s back');
          const bad = (txt, re, why) => { const k = mkc(), b = JSON.stringify(k.S); k.keepRead(txt, 'x.json'); kg(!k._pending && k.S.keepMsg && k.S.keepMsg.bad && re.test(k.S.keepMsg.text) && JSON.stringify(Object.assign({}, k.S, { keepMsg: null })) === JSON.stringify(Object.assign(JSON.parse(b), {})), why + ' leaves the work as it was and says why'); };
          bad('{nope', /not valid JSON/, 'text that is not JSON');
          bad('[]', /not a saved project/, 'a list');
          { const f = clone(); f.project.fingerprint = 'zz'; bad(JSON.stringify(f), /different project/, 'work from another project'); }
          { const f = clone(); f.state.events[1].text = 'x'; bad(JSON.stringify(f), /changed/, 'a changed record'); }
          // a file that passes every check and still cannot be drawn is refused too
          { const proto = C.Component.prototype, orig = proto.renderVals; proto.renderVals = function () { if (this._dry && this.state.view === 'audit') throw new Error('boom'); return orig.call(this); };
            try { bad(JSON.stringify(file), /audit screen could not be drawn: boom/, 'a file the screens cannot draw'); } finally { proto.renderVals = orig; } }
        });
        // start over
        withStore(store(), () => {
          const c = new C.Component(); c.setState({ dec: { [cl.id]: mkDec(cl) }, rdec: { [rd1.id]: mkRd(rd1, 'keep') }, person: 'priya', view: 'home' }); flush();
          const v1 = c.renderVals(); v1.kStart(); kg(c.S.keepAsk === 'start' && Object.keys(c.S.dec).length === 1, 'Start over asks first and removes nothing yet');
          c.renderVals().kCancel(); kg(c.S.keepAsk === '' && Object.keys(c.S.dec).length === 1, 'and cancelling keeps the work');
          c.renderVals().kStart(); c.renderVals().kDoStart();
          kg(PERSIST_KEYS.every((k) => eq(c.S[k], C.DEFAULTS[k])) && c.S.view === 'open' && !(PERSIST_STORE in global.window.localStorage.d) && !c.S.keepRestored && c.valsKeep(c.S).kStartDisabled, 'Start over puts every kept key back to its default, removes what the browser held and goes to Open');
          flush(); kg(!(PERSIST_STORE in global.window.localStorage.d), 'and the empty page does not write itself back');
        });
        // two tabs of one browser: the second to write is told, and nothing is overwritten until the person says whose work stands
        {
          const st2 = store(), ls = {}; const win = { localStorage: st2, addEventListener(t, f) { (ls[t] = ls[t] || []).push(f); }, removeEventListener(t, f) { ls[t] = (ls[t] || []).filter((x) => x !== f); } };
          const fire = (e) => (ls.storage || []).slice().forEach((f) => f(e));
          global.window = win;
          try {
            const A = new C.Component(), B = new C.Component();
            A.componentDidMount(); B.componentDidMount();
            kg((ls.storage || []).length === 2, 'each tab listens for the other tab’s writes');
            A.setState({ view: 'home', dec: { [cl.id]: mkDec(cl) } }); flush();
            fire({ key: 'something-else', storageArea: st2 });
            kg(B.S.keepStatus !== 'other' && !B._keepHold, 'a write to some other key of the same browser is not this store’s business');
            fire({ key: PERSIST_STORE, storageArea: st2 });
            kg(B.S.keepStatus === 'other' && B._keepHold, 'a tab that is told another tab wrote stops saving');
            const n = st2.sets; B.setState({ view: 'home', rdec: { [rd1.id]: mkRd(rd1, 'keep') } }); flush();
            kg(st2.sets === n && Object.keys(JSON.parse(st2.d[PERSIST_STORE]).state.rdec || {}).length === 0, 'and does not write over it');
            const v = B.renderVals();
            kg(v.kOther && v.kWarn && /Another tab changed/.test(v.kHead) && /Choose whose work stands/.test(v.kLine), 'Home says so and asks whose work stands');
            B.renderVals().kTake();
            kg(eq(B.S.dec, { [cl.id]: mkDec(cl) }) && Object.keys(B.S.rdec).length === 0 && B.S.keepStatus === 'saved' && !B._keepHold && B.S.keepMsg && /dropped/.test(B.S.keepMsg.text), 'taking the other tab’s work shows it and drops this tab’s changes');
            B.setState({ rdec: { [rd1.id]: mkRd(rd1, 'keep') } }); flush();
            kg(Object.keys(JSON.parse(st2.d[PERSIST_STORE]).state.rdec).length === 1, 'after that this tab saves again');
            fire({ key: null, storageArea: st2 });
            kg(A.S.keepStatus === 'other', 'the other tab clearing the whole store counts too');
            A.renderVals().kMine();
            kg(Object.keys(JSON.parse(st2.d[PERSIST_STORE]).state.dec).length === 1 && !A._keepHold && /saved over/.test(A.S.keepMsg.text), 'keeping this tab’s work writes it over the other tab’s, and says so');
            fire({ key: PERSIST_STORE, storageArea: {} });
            kg(A.S.keepStatus === 'saved', 'a write in some other kind of storage is not this store’s business');
            A.componentWillUnmount(); kg((ls.storage || []).length === 1, 'a tab that is closed stops listening');
            // the other tab removed everything and this tab has nothing to take
            st2.removeItem(PERSIST_STORE); B.keepOther(); B.renderVals().kTake();
            kg(!B._keepHold && /no saved work now/.test(B.S.keepMsg.text), 'taking the other tab’s work when it has none keeps this tab’s own');
          } finally { delete global.window; }
        }
        // closing or hiding the tab writes the last change at once
        {
          const s3 = store(), ls3 = {};
          global.window = { localStorage: s3, addEventListener(t, f) { (ls3[t] = ls3[t] || []).push(f); }, removeEventListener(t, f) { ls3[t] = (ls3[t] || []).filter((x) => x !== f); } };
          try {
            const c = new C.Component(); c.componentDidMount();
            c.setState({ view: 'home', dec: { [cl.id]: mkDec(cl) } });
            kg(!(PERSIST_STORE in s3.d), 'a change is not written until the pause is over');
            (ls3.pagehide || []).forEach((f) => f());
            kg(PERSIST_STORE in s3.d && JSON.parse(s3.d[PERSIST_STORE]).state.dec[cl.id].rev === 'R3', 'closing the tab writes the last change at once, without waiting for the pause');
            const n = s3.sets; (ls3.pagehide || []).forEach((f) => f()); kg(s3.sets === n, 'and writes nothing again when nothing changed');
            c.componentWillUnmount();
            kg((ls3.pagehide || []).length === 0 && (ls3.storage || []).length === 0, 'a tab that goes away takes its listeners with it');
          } finally { delete global.window; }
        }
        // a probe instance does not write or schedule anything
        withStore(store(), () => { const c = mkc(); const n = timers.size; c.keepProbe(back.state); kg(timers.size === n, 'drawing every screen to check a file schedules nothing'); });
        // the Home card
        withStore(store(), () => { const c = mkc(), v = c.renderVals(); kg(v.kStartDisabled && !v.kRestored && !v.kAskStart && !v.kAskLoad && !v.kHasMsg, 'Home with no work: Start over is off and there is nothing to confirm'); kg(/it is kept here by itself/.test(v.kLine), 'and the line says what happens once there is work'); kg(/not encrypted/.test(v.kScope) && /server/.test(v.kScope), 'the card says it stays in this browser, is not encrypted and is not shared'); });
      } finally { global.setTimeout = realST; global.clearTimeout = realCT; delete global.window; }
    }
  }
  // ---- AI use: the rules (the table the Python library is tested against too), the sample's markings, what the page does with a group that is held back, and what is kept ----
  {
    const ag = (ok, msg) => { if (!ok) flag('AI: ' + msg); };
    const C = Component, path = require('path');
    const eq = (a, b) => JSON.stringify(a) === JSON.stringify(b);
    const T = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'docs', 'ai_gate_cases.json'), 'utf8'));
    const REV = { reviewed_by: 'A. Lead', reviewed_at: '1 Oct' }, UNREV = { reviewed_by: '', reviewed_at: '' };
    // the same cases the Python library is tested against
    T.marking_cases.forEach(([t, want]) => ag(C.aiMarkLevel(t) === want, 'the marking ' + JSON.stringify(t) + ' reads as ' + want + ', not ' + C.aiMarkLevel(t)));
    T.group_cases.forEach(([ls, pol, want]) => ag(C.aiGroupLevel(ls, pol) === want, 'a group of ' + JSON.stringify(ls) + ' with “' + pol + '” reads as ' + want + ', not ' + C.aiGroupLevel(ls, pol)));
    T.sheet_cases.forEach(([name, d, want]) => ag(eq(C.aiSheetProblems(d), want), 'the sheet “' + name + '” has the problems ' + JSON.stringify(want) + ', not ' + JSON.stringify(C.aiSheetProblems(d))));
    T.gate_cases.forEach((g) => { const r = C.aiGate(Object.assign({}, T.sheets[g.sheet], g.reviewed ? REV : UNREV), g.on, g.marks); ag(r.open === g.open && r.code === g.code, 'gate case “' + g.name + '” says ' + r.code + ' and wanted ' + g.code); });
    ag(eq([...new Set(T.gate_cases.map((g) => g.code))].sort(), ['classified', 'marking', 'off', 'open', 'sheet', 'unknown', 'unreviewed', 'unstated']), 'the table covers every answer the gate can give');
    ag(eq([...new Set(T.sheet_cases.reduce((a, c) => a.concat(c[2]), []))].sort(), ['days', 'exp_where', 'leaves_marked', 'log_marked', 'model', 'values', 'vendor_leaves']), 'the table covers every problem a sheet can have');
    ag(Object.keys(C.AI_PROBLEM).sort().join() === 'days,exp_where,leaves_marked,log_marked,model,values,vendor_leaves' && ['off', 'unreviewed', 'sheet', 'classified', 'unknown', 'unstated', 'marking'].every((k) => C.AI_HELD[k]), 'every problem and every hold has words the page can show');
    ag(!C.aiGate(T.sheets['ours-none'], true, ['No marking']).open && C.aiGate(Object.assign({}, T.sheets['ours-none'], REV), true, ['No marking']).open, 'a sheet with no reviewer opens nothing, with one it opens');
    ag(C.aiReviewed(Object.assign({}, T.sheets['ours-none'], { reviewed_by: 'A', reviewed_at: '' })) === false && C.aiReviewed(Object.assign({}, T.sheets['ours-none'], { reviewed_by: ' ', reviewed_at: '1 Oct' })) === false, 'a reviewer without a date, or a date without a name, is not a review');

    // ---- the sample's markings ----
    const CL = C.CL_BY, DS = C.DEFAULTS.aiSheet, SH = (o) => Object.assign({}, DS, o || {});
    const mkc = (st) => { const c = new C.Component(); c.setState(Object.assign({ view: 'review' }, st || {})); return c; };
    const lead = (st) => mkc(Object.assign({ view: 'ai', person: 'morgan' }, st || {}));
    const code = (S, id) => C.aiGateOf(S, CL[id]).code;
    const S0 = mkc().S;
    ag(DS.approved === 'none' && DS.where === 'ours' && DS.leaves === false && C.aiReviewed(DS) && C.aiSheetProblems(DS).length === 0 && Object.isFrozen(DS), 'the sample project starts with a reviewed, consistent sheet that approves no marking, and nothing can change it in place');
    const mkn = C.aiMarkCountsOnce();
    ag(mkn.total === REQS.length && mkn.none + mkn.cui + mkn.exp + mkn.classified + mkn.unknown + mkn.unstated === mkn.total && mkn.cui > 0 && mkn.exp > 0 && mkn.unknown > 0 && mkn.unstated > 0 && mkn.classified === 0, 'every requirement has a marking, and the sample has some of every kind but classified');
    ag(['CL-001', 'CL-002', 'CL-003', 'CL-005', 'CL-014', 'CL-023', 'CL-038', 'CL-042', 'CL-045', 'CL-050', 'CL-062', 'CL-115', 'CL-117', 'CL-201'].every((id) => code(S0, id) === 'open'), 'the clusters the rest of the page is shown with stay open to the AI');
    ag(code(S0, 'CL-025') === 'marking' && C.aiGateOf(S0, CL['CL-025']).level === 'cui' && code(S0, 'CL-037') === 'marking' && C.aiGateOf(S0, CL['CL-037']).level === 'exp' && code(S0, 'CL-016') === 'unknown' && code(S0, 'CL-056') === 'unstated', 'each kind of hold can be seen in the sample');
    const k0 = C.aiCounts(S0, CLUSTERS);
    ag(k0.total === CLUSTERS.length && k0.open + k0.held === k0.total && Object.values(k0.by).reduce((a, b) => a + b, 0) === k0.held && k0.cui + k0.exp === k0.by.marking && k0.open > k0.held * 3 && k0.held >= 20 && k0.held <= 70, 'about one group in five is held back, and the reasons add up (' + JSON.stringify(k0) + ')');
    ag(HAND_IDS_OK(), 'the hand-written reference clusters carry no marking');
    function HAND_IDS_OK() { return ['CL-001', 'CL-002', 'CL-003', 'CL-004', 'CL-005', 'CL-006', 'CL-007', 'CL-042', 'CL-050'].every((id) => CL[id].members.every((m) => C.aiMarkOf(m.id) === 'No marking')); }
    ag(['CL-025', 'CL-037', 'CL-016', 'CL-056'].every((id) => CL[id].members.filter((m) => C.aiMarkOf(m.id) !== 'No marking').length === 1), 'each fixed cluster has exactly one marked requirement');
    ag(C.aiMarkOf('nope') === '' && C.aiMarkOf('constructor') === '' && C.aiMarkOf(undefined) === '', 'a marking asked for by an ID the project does not have is blank, not an inherited property');

    // ---- a group held back: the cluster as the AI may be used on it ----
    const c9 = CL['CL-025'], h9 = C.aiCl(S0, c9);
    ag(c9.ai.mode !== 'none' && h9 !== c9 && h9.ai.mode === 'none' && h9.aiDraft === '' && h9.aiHeld.code === 'marking' && /CUI/i.test(h9.aiHeld.text) && /no marking only/.test(h9.aiHeld.text) && h9.members === c9.members && h9.id === c9.id, 'a held group is the same group with the AI answer taken out and the reason given');
    ag(C.aiCl(S0, c9) === h9 && C.aiCl(S0, CL['CL-001']) === CL['CL-001'], 'an open group is itself, and a held group is built once');
    ag(c9.ai.mode !== 'none' && (c9.aiDraft || c9.ai.verdict), 'and the group itself is not changed (the record of what was once run stays whole)');
    // review page
    const vOpen = mkc({ selected: 'CL-001', person: 'sam' }).renderVals(), vHeld = mkc({ selected: 'CL-025', person: 'sam' }).renderVals();
    const titles = (v) => v.banners.map((b) => b.title);
    ag(!titles(vOpen).some((t) => /No AI answer/.test(t)) && !vOpen.rp.aiStrat.disabled, 'an open group shows its AI answer and the AI wording choice');
    ag(titles(vHeld).some((t) => /No AI answer is shown/.test(t)) && vHeld.rp.aiStrat.disabled && /CUI/i.test(vHeld.rp.aiStrat.why) && vHeld.d.prov.some((p) => /Held back from the AI/.test(p.label)) && !vHeld.d.prov.some((p) => /AI judge|AI wording draft/.test(p.label)), 'a held group says so, offers no AI wording, and does not claim the AI judged it');
    ag(/held back from the AI/.test(vHeld.rp.aiAfter) && /mechanical methods decided/.test(vHeld.rp.aiAfter), 'and its text on the AI’s part says the mechanical methods decided the suggestion');
    const bAct = vHeld.banners.find((b) => /No AI answer/.test(b.title)).actions[0];
    { const c = mkc({ selected: 'CL-025' }); c.renderVals().banners.find((b) => /No AI answer/.test(b.title)).actions[0].onClick(); ag(c.S.view === 'ai', 'the banner opens the AI use page'); }
    ag(bAct.label === 'Open AI use', 'the banner button says where it goes');
    // an AI wording kept from before the group was held back cannot be recorded
    { const c = mkc({ selected: 'CL-025', person: 'sam', res: { 'CL-025': { outcome: 'merge', strat: 'ai', aiText: 'The system shall do something specific.', reason: 'R-STR', note: 'A note of more than twelve characters.', ack: true } } });
      const v = c.renderVals(); ag(v.rp.recordDisabled && /not used on this group/i.test(v.rp.recordWhy), 'an AI wording typed or kept before the group was held back cannot be recorded (' + v.rp.recordWhy + ')'); v.rp.record && v.rp.record(); ag(!c.S.dec['CL-025'], 'and recording does nothing'); }
    // the same group, not held: the same wording can be recorded
    { const c = mkc({ selected: 'CL-001', person: 'sam', res: { 'CL-001': { outcome: 'merge', strat: 'ai', aiText: '', reason: 'R-STR', note: 'A note of more than twelve characters.', ack: true } } });
      const v = c.renderVals(); ag(!/not used on this group/i.test(v.rp.recordWhy || ''), 'in an open group an AI wording is not refused for being AI'); }
    // the assistant
    { const c = mkc({ selected: 'CL-025', chatOpen: true, person: 'sam' }), v = c.renderVals();
      ag(v.aHeld && /^Not used on this group/.test(v.aHeldNote) && v.chips.every((x) => x.off) && v.sendDisabled === true, 'the assistant is switched off for a held group and says why');
      v.chips[0].onClick(); const log = c.S.chat['CL-025'] || []; ag(log.length === 2 && /I am not used on this group, and I have not read it/.test(log[1].text) && !log[1].draft && !(log[1].quotes || []).length, 'and if it is asked anyway it answers with nothing from the group');
      const o = mkc({ selected: 'CL-001', chatOpen: true, person: 'sam' }).renderVals(); ag(!o.aHeld && o.chips.every((x) => !x.off) && o.aHeldNote === '', 'for an open group the assistant works as before'); }
    // a model name or a reviewer made only of an odd space is blank, the same as in the pipeline (reqin/tests/test_aigate_page.py compares the two on thousands of inputs)
    { const R = (by, at) => C.aiReviewed({ reviewed_by: by, reviewed_at: at }), M = (m) => C.aiSheetProblems(Object.assign({}, DS, { model: m })).indexOf('model') >= 0;
      ag(!R('\u00a0', 'x') && !R('\u0085', 'x') && !R('\u2003\x1c', 'x') && !R('x', '\u2028') && R('A. Reviewer', '1 Oct'), 'a reviewer or a date made only of spaces of any kind is not a review');
      ag(R('\ufeff', 'x'), 'a byte order mark is not a space, so a name made of one is a name (the pipeline reads it the same way)');
      ag(M('\u0085') && M('\u00a0 ') && M('') && !M('M') && !M('\ufeff'), 'a model name made only of spaces of any kind is blank'); }
    // the question box: with something typed it is off for a held group and on for an open one; with nothing typed it is off for both
    { const box = (cid, text) => mkc({ selected: cid, chatOpen: true, person: 'sam', chatInput: text }).renderVals().sendDisabled;
      ag(box('CL-025', 'Why were these grouped?') === true, 'the question box stays off for a held group even with a question typed');
      ag(box('CL-001', 'Why were these grouped?') === false, 'the question box is on for an open group with a question typed');
      ag(box('CL-001', '   ') === true && box('CL-001', '') === true, 'and off when nothing, or only spaces, is typed'); }
    // a typed sheet: days are only kept when prompts are kept
    { const D = (o) => Object.assign({ model: 'M', where: 'ours', leaves: false, log: 'local', days: '30', approved: 'none', unstated: 'withhold' }, o);
      const g = C.aiSheetFromDraft;
      ag(g(D({ log: 'none', days: '30' })).days === 0 && g(D({ log: 'none', days: '' })).days === 0 && g(D({ log: 'none', days: 'abc' })).days === 0, 'a sheet where nothing is kept has no days, whatever was typed in the days box');
      ag(g(D({ log: 'local', days: '30' })).days === 30 && g(D({ log: 'service', days: ' 365 ' })).days === 365, 'a sheet where prompts are kept has the days that were typed');
      ag(isNaN(g(D({ log: 'local', days: '' })).days) && isNaN(g(D({ log: 'local', days: '1.5' })).days) && isNaN(g(D({ log: 'local', days: '-3' })).days) && isNaN(g(D({ log: 'local', days: '123456' })).days), 'and a missing, fractional, negative or enormous number of days is not a number (the sheet check then refuses it)');
      ag(C.aiSheetProblems(g(D({ log: 'local', days: '0' }))).indexOf('days') >= 0 && C.aiSheetProblems(g(D({ log: 'none', days: '0' }))).indexOf('days') < 0, 'zero days with prompts kept is a problem, zero days with nothing kept is not'); }

    // ---- the switch ----
    PEOPLE.forEach((p) => { const v = lead({ person: p.k }).renderVals(); ag(v.auCan === (p.k === 'morgan') && v.auCanNot === (p.k !== 'morgan') && (p.k === 'morgan' ? v.auWhy === '' : /Only the lead/.test(v.auWhy)), 'only the lead can change AI use (' + p.k + ')'); });
    PEOPLE.filter((p) => p.k !== 'morgan').forEach((p) => { const c = lead({ person: p.k }); const n = c.S.events.length; c.renderVals().auSwitch(); c.renderVals().auBegin(); c.renderVals().auWithdraw(); ag(c.S.aiOn === true && !c.S.aiEdit && aiOkSheet(c.S) && c.S.events.length === n, 'nobody but the lead changes the switch or the sheet (' + p.k + ')'); });
    function aiOkSheet(S) { return C.aiReviewed(S.aiSheet); }
    { const c = lead({ preview: 'PE' }), n = c.S.events.length; const v = c.renderVals(); c.renderVals().auSwitch(); ag(!v.auCan && /Leave the lens preview/.test(v.auWhy) && c.S.aiOn === true && c.S.events.length === n, 'the lead in a lens preview changes nothing'); }
    { const c = lead(), v0 = c.renderVals();
      ag(/AI is on/.test(v0.auHead) && v0.auHead === 'AI is on' && v0.auSwitchLabel === 'Switch AI off for the whole project' && v0.auSt.isPass && /groups can go to the model/.test(v0.auLine), 'the page starts by saying AI is on, and how many groups it can see');
      v0.auSwitch(); const S1 = c.S, v1 = c.renderVals();
      ag(S1.aiOn === false && S1.events.length === 1 && S1.events[0].target === 'AI use' && S1.events[0].text === 'AI use switched off for the whole project' && /Morgan Hale/.test(S1.events[0].actor) && chainOk(S1.events), 'switching off is recorded in the event chain');
      ag(v1.auHead === 'AI is switched off' && v1.auSwitchLabel === 'Switch AI on for the whole project' && v1.auSt.isInfo && /every earlier AI answer is hidden/.test(v1.auLine) && /switched off/.test(v1.auMsg), 'and the page says so');
      ag(CLUSTERS.every((cl) => code(S1, cl.id) === 'off') && C.aiCounts(S1, CLUSTERS).open === 0 && C.aiCounts(S1, CLUSTERS).by.off === CLUSTERS.length, 'with the switch off every group is held back, whatever it is marked');
      ag(C.aiCl(S1, CL['CL-001']).aiHeld.code === 'off' && /switched off/.test(C.aiCl(S1, CL['CL-001']).aiHeld.text), 'and even a clean group says why');
      const vr = mkc({ selected: 'CL-001', aiOn: false, person: 'sam' }).renderVals(); ag(titles(vr).some((t) => /No AI answer/.test(t)) && vr.rp.aiStrat.disabled && vr.rp.aiStrat.why === 'AI is switched off for this project.', 'the review page of a clean group says AI is off');
      c.renderVals().auSwitch(); const S2 = c.S;
      ag(S2.aiOn === true && S2.events.length === 2 && S2.events[1].text === 'AI use switched on for the whole project' && chainOk(S2.events) && C.aiFromEvents(S2.events).on === true && /groups can go to the model/.test(S2.aiMsg.text), 'switching on again is recorded too'); }
    function chainOk(evs) { return C.chainCheck(C.EV_SEED.concat(evs)) === 'ok'; }

    // ---- the data sheet: changing it, what stops a save, what a save writes ----
    { const c = lead(), v0 = c.renderVals();
      ag(v0.auShowEditBtn && v0.auShowWithdraw && !v0.auEditing && v0.auSheetRows.length === 7 && v0.auSheetRows[0].v === 'Local model v1' && /A\. Moreno/.test(v0.auSheetRows[6].v), 'the lead sees the saved sheet and can change or withdraw it');
      v0.auBegin(); const S1 = c.S, v1 = c.renderVals();
      ag(eq(S1.aiEdit, Object.assign(C.aiDraftOf(DS))) && S1.aiEdit.reviewed_by === '' && S1.aiEdit.days === '90' && v1.auEditing && !v1.auShowEditBtn && v1.auSaveDisabled && v1.auHasDraftProblems && v1.auDraftProblems.length === 1 && /Write who reviewed/.test(v1.auDraftProblems[0].t), 'changing the sheet starts from the saved one and asks for a reviewer before it can be saved');
      ag(v1.auGroups.length === 5 && v1.auGroups.every((g) => g.items.filter((i) => i.pressed === 'true').length === 1), 'each question has exactly one answer chosen');
      const n = c.S.events.length; v1.auSave(); ag(c.S.aiEdit && c.S.events.length === n && eq(c.S.aiSheet, DS), 'a sheet with no reviewer cannot be saved');
      v1.auOnReviewer({ target: { value: '  B. Chen, export office  ' } }); const v2 = c.renderVals();
      ag(!v2.auSaveDisabled && !v2.auHasDraftProblems && /Saving marks the sheet reviewed/.test(v2.auDraftLine), 'a reviewer’s name is enough when the rest is consistent');
      v2.auGroups[3].items.find((i) => /CUI/.test(i.label) && !/export/.test(i.label)).pick(); ag(c.S.aiEdit.approved === 'cui', 'choosing an answer changes the draft');
      ag(eq(c.S.aiSheet, DS) && code(c.S, 'CL-025') === 'marking', 'and nothing has changed until it is saved');
      c.renderVals().auSave(); const S3 = c.S, e3 = S3.events[S3.events.length - 1];
      ag(!S3.aiEdit && S3.aiSheet.approved === 'cui' && S3.aiSheet.reviewed_by === 'B. Chen, export office' && S3.aiSheet.reviewed_at === '10 Oct' && S3.aiSheet.entered_by === 'Morgan Hale' && S3.aiSheet.days === 90 && S3.aiSheet.model === 'Local model v1', 'a save writes the sheet with the reviewer, the date and who entered it');
      ag(e3.target === 'AI use' && /^AI data sheet changed \(highest marking approved: no marking only → CUI\) and marked reviewed by B\. Chen, export office \[sheet [0-9a-f]{8}\]$/.test(e3.text) && chainOk(S3.events) && C.aiFromEvents(S3.events).fp === C.aiSheetFp(S3.aiSheet), 'the record says what changed, who reviewed, and carries the sheet’s fingerprint');
      ag(code(S3, 'CL-025') === 'open' && code(S3, 'CL-037') === 'marking' && C.aiCounts(S3, CLUSTERS).held < k0.held && C.aiCounts(S3, CLUSTERS).cui === 0 && C.aiCounts(S3, CLUSTERS).exp === k0.exp, 'approving CUI opens the CUI groups and leaves the export-controlled ones held');
      const v3 = c.renderVals(); ag(/marked reviewed by B\. Chen/.test(v3.auMsg) && v3.auHist.length === 1 && v3.auHasHist && /changed/.test(v3.auHist[0].what), 'the page confirms and lists the change');
      const vr = mkc({ selected: 'CL-025', aiSheet: S3.aiSheet }).renderVals(); ag(!titles(vr).some((t) => /No AI answer/.test(t)) && !vr.rp.aiStrat.disabled, 'a group that is now open shows its AI answer again'); }
    // inconsistent answers stop a save, each with its words
    { const mk2 = (patch) => { const c = lead({ aiEdit: Object.assign(C.aiDraftOf(DS), { reviewed_by: 'B. Chen' }, patch) }); const v = c.renderVals(); return { c, v, t: v.auDraftProblems.map((p) => p.t).join(' | ') }; };
      let r = mk2({}); ag(!r.v.auSaveDisabled, 'an unchanged sheet with a reviewer can be saved');
      r = mk2({ model: '   ' }); ag(r.v.auSaveDisabled && r.t === C.AI_PROBLEM.model, 'no model name stops a save');
      r = mk2({ where: 'vendor' }); ag(r.v.auSaveDisabled && r.t === C.AI_PROBLEM.vendor_leaves, 'a vendor service with text that does not leave stops a save');
      r = mk2({ where: 'vendor', leaves: true, approved: 'cui' }); ag(r.t === C.AI_PROBLEM.leaves_marked, 'text that leaves cannot be approved for marked requirements');
      r = mk2({ log: 'service', approved: 'cui', days: '30' }); ag(r.t === C.AI_PROBLEM.log_marked, 'a provider that keeps prompts cannot be approved for marked requirements');
      r = mk2({ where: 'tenant', approved: 'exp' }); ag(r.t === C.AI_PROBLEM.exp_where, 'export-controlled text cannot be approved for a cloud tenant');
      ['', 'abc', '0', '3651', '-5', '1.5', '12345678'].forEach((d) => { r = mk2({ days: d }); ag(r.t === C.AI_PROBLEM.days && r.v.auSaveDisabled, 'days kept “' + d + '” stops a save'); });
      ['1', '30', '3650', ' 45 '].forEach((d) => { r = mk2({ days: d }); ag(!r.v.auSaveDisabled, 'days kept “' + d + '” is accepted'); });
      r = mk2({ log: 'none', days: 'whatever' }); ag(!r.v.auSaveDisabled, 'days are not asked for when prompts are not kept');
      r = mk2({ model: '', where: 'vendor', approved: 'exp', reviewed_by: '' }); ag(r.v.auDraftProblems.length >= 4 && r.v.auSaveDisabled, 'several problems are all listed');
      const c = lead({ aiEdit: Object.assign(C.aiDraftOf(DS), { reviewed_by: 'B', where: 'tenant', approved: 'exp' }) }); const n = c.S.events.length; c.renderVals().auSave(); ag(c.S.aiEdit && eq(c.S.aiSheet, DS) && c.S.events.length === n, 'a save that the form refuses does nothing even if asked'); }
    // cancelling, withdrawing
    { const c = lead({ aiEdit: Object.assign(C.aiDraftOf(DS), { reviewed_by: 'B', approved: 'exp' }) }), n = c.S.events.length; c.renderVals().auCancel(); ag(!c.S.aiEdit && eq(c.S.aiSheet, DS) && c.S.events.length === n && c.S.aiMsg.text === 'Nothing was changed.', 'cancelling changes nothing and records nothing'); }
    { const c = lead(); c.renderVals().auWithdraw(); const S = c.S, v = c.renderVals();
      ag(!C.aiReviewed(S.aiSheet) && S.aiSheet.model === DS.model && S.aiSheet.approved === DS.approved && /approval withdrawn/.test(S.events[0].text) && /\[sheet [0-9a-f]{8}\]$/.test(S.events[0].text) && chainOk(S.events) && C.aiFromEvents(S.events).fp === C.aiSheetFp(S.aiSheet), 'withdrawing approval clears the reviewer and keeps the rest, and is recorded');
      ag(CLUSTERS.every((cl) => code(S, cl.id) === 'unreviewed') && v.auHead === 'AI is on, but nothing is sent' && v.auSt.isWarn && /has not been reviewed/.test(v.auLine) && !v.auShowWithdraw && v.auShowEditBtn, 'with no review nothing goes, and the page says so');
      ag(/AI is on, but nothing goes to a model until the AI data sheet is reviewed/.test(mkc({ view: 'home', aiSheet: S.aiSheet }).renderVals().secLine), 'Home says the same');
      // reviewing again
      const v2 = c.renderVals(); v2.auBegin(); c.renderVals().auOnReviewer({ target: { value: 'C. Diaz, security office' } }); c.renderVals().auSave();
      ag(C.aiReviewed(c.S.aiSheet) && c.S.aiSheet.reviewed_by === 'C. Diaz, security office' && /confirmed unchanged and marked reviewed by C\. Diaz/.test(c.S.events[c.S.events.length - 1].text) && code(c.S, 'CL-001') === 'open', 'reviewing again with nothing changed says so, and opens the gate'); }
    // sheets that contradict themselves, however they got there
    { const bad = SH({ where: 'vendor', leaves: false }), S = mkc({ aiSheet: bad }).S, v = lead({ aiSheet: bad }).renderVals();
      ag(CLUSTERS.every((cl) => code(S, cl.id) === 'sheet') && v.auHead === 'AI is on, but nothing is sent' && /1 problem/.test(v.auLine) && v.auHasSheetProblems && v.auSheetProblems[0].t === C.AI_PROBLEM.vendor_leaves, 'a saved sheet that contradicts itself opens nothing and lists what is wrong');
      ag(/made consistent/.test(mkc({ view: 'home', aiSheet: bad }).renderVals().secLine), 'and Home says it');
      ag(C.aiCl(S, CL['CL-001']).aiHeld.text === C.AI_HELD.sheet, 'and the review page says it'); }
    // no marking recorded
    { const c = mkc({ aiSheet: SH({ unstated: 'none' }) }); ag(code(c.S, 'CL-056') === 'open' && code(c.S, 'CL-016') === 'unknown', 'when the sheet reads an empty marking as none, that group opens, and an unknown marking still does not'); }
    { const S = mkc({ aiSheet: SH({ approved: 'exp', unstated: 'none' }) }).S; ag(code(S, 'CL-037') === 'open' && code(S, 'CL-025') === 'open' && code(S, 'CL-016') === 'unknown', 'approving export-controlled text opens those groups and nothing else changes'); }
    ag(mkc().S.aiSheet.entered_by === 'Morgan Hale', 'the sample sheet says who entered it');

    // ---- Home, Methods, Gold ----
    { const home = (st) => mkc(Object.assign({ view: 'home' }, st)).renderVals();
      ag(new RegExp('AI can see ' + k0.open + ' of ' + k0.total + ' groups\\. ' + k0.held + ' are held back').test(home().secLine), 'Home says how many groups the AI can see');
      ag(/AI is switched off for the whole project\./.test(home({ aiOn: false }).secLine), 'Home says when AI is off');
      { const c = mkc({ view: 'home' }); c.renderVals().secAiOpen(); ag(c.S.view === 'ai', 'Home links to the AI use page'); }
      const m0 = mkc({ view: 'methods' }).renderVals(), m1 = mkc({ view: 'methods', aiOn: false }).renderVals();
      ag(/held back from the AI by the data sheet/.test(m0.mtAiNote) && /do not change with the data sheet/.test(m0.mtAiNote) && /AI is switched off/.test(m1.mtAiNote) && /do not change with the switch/.test(m1.mtAiNote), 'Methods says that the scores come from a trial run and do not move with the switch or the sheet');
      ag(/groups are held back/.test(mkc({ view: 'methods', aiSheet: SH({ approved: 'exp', unstated: 'none' }) }).renderVals().mtAiNote), 'Methods still says groups are held back when only unknown markings are'); }
    { const sl = C.goldSampleLabels(), g = Object.assign({}, DEFAULTS.gold, { labels: sl }), a = C.goldNaming(Object.assign({}, S0, { gold: g })), b = C.goldNaming(Object.assign({}, S0, { gold: g, aiOn: false }));
      ag(a.held > 0 && a.n > 0 && b.n === 0 && b.k === 0 && b.held === a.n + a.held, 'the AI-against-people comparison leaves out groups the AI was not used on (' + a.n + ' counted, ' + a.held + ' left out; off: ' + b.n + ' counted, ' + b.held + ' left out)');
      const line = mkc({ view: 'methods', gold: g }).renderVals().gmNamingLine, off = mkc({ view: 'methods', gold: g, aiOn: false }).renderVals();
      ag(/ of 21 pairs/.test(line) && / 4 pairs are left out because the AI was not used on its group\./.test(line) && off.gmNaming === false, 'and Methods says how many it left out, and shows no comparison when it has nothing to compare'); }

    // ---- ai-use.json ----
    { const c = lead({ aiSheet: SH({ approved: 'cui', reviewed_by: 'B. Chen', reviewed_at: '3 Oct' }) }), S = c.S, f = C.aiUseFile(S, '2026-10-14T00:00:00.000Z');
      const txt = JSON.stringify(f);
      ag(f.format === 'reqin-ai-use/1' && f.switch === 'on' && f.reviewed === true && eq(f.sheet_problems, []) && f.sheet.approved === 'cui' && f.groups.total === CLUSTERS.length && f.groups.held === f.held.length && f.groups.open + f.groups.held === f.groups.total, 'ai-use.json holds the switch, the sheet and the numbers');
      ag(f.held.every((h) => h.cluster && h.code && ['marking', 'unknown', 'unstated'].indexOf(h.code) >= 0) && f.held.some((h) => h.code === 'marking' && h.level === 'exp') && f.requirements_by_marking.none + f.requirements_by_marking.cui + f.requirements_by_marking.exp + f.requirements_by_marking.unknown + f.requirements_by_marking.unstated + f.requirements_by_marking.classified === REQS.length, 'and each held group with its reason, and the requirements by marking');
      ag(REQS.filter((r, i) => i % 3 === 0).every((r) => txt.indexOf(r.text) < 0) && CLUSTERS.every((cl) => !cl.aiDraft || txt.indexOf(cl.aiDraft) < 0), 'it holds no requirement text and no AI wording');
      ag(JSON.parse(txt).saved === '2026-10-14T00:00:00.000Z' && f.project.fingerprint === C.persistFingerprint(), 'it names the project it belongs to');
      c.renderVals().auDownload(); const e = c.S.events[c.S.events.length - 1];
      ag(e.target === 'AI use' && /^Downloaded ai-use\.json \(\d+ of 252 groups held back\)$/.test(e.text) && /Prepared ai-use\.json/.test(c.S.aiMsg.text) && !/requirement text and/.test(c.S.aiMsg.text) && /holds no requirement text/.test(c.S.aiMsg.text), 'downloading it is recorded'); }

    // ---- keeping it: the switch and the sheet are saved, and a file that disagrees with its own record is refused ----
    { ag(C.PERSIST_KEYS.indexOf('aiOn') >= 0 && C.PERSIST_KEYS.indexOf('aiSheet') >= 0, 'the switch and the sheet are kept');
      const c = lead(); c.renderVals().auBegin(); c.renderVals().auOnReviewer({ target: { value: 'B. Chen' } }); c.renderVals().auGroups[3].items.find((i) => /CUI/.test(i.label) && !/export/.test(i.label)).pick(); c.renderVals().auSave(); c.renderVals().auSwitch();
      const S = c.S, f = C.persistFile(S), r = C.persistCheck(JSON.parse(JSON.stringify(f)));
      ag(S.aiOn === false && S.aiSheet.approved === 'cui' && r.ok && r.state.aiOn === false && eq(r.state.aiSheet, S.aiSheet), 'a saved project with the switch off and a changed sheet comes back as it was (' + r.problems.join(' ') + ')');
      const bad = (mut, want, label) => { const g = JSON.parse(JSON.stringify(f)); mut(g); const q = C.persistCheck(g); ag(!q.ok && want.test(q.problems.join(' ')), label + ' (' + (q.ok ? 'accepted' : q.problems.join(' ')) + ')'); };
      bad((g) => { g.state.aiSheet.approved = 'exp'; }, /does not match the record of events/, 'a sheet edited by hand after it was saved is refused');
      bad((g) => { g.state.aiOn = true; }, /does not match the record of events/, 'a switch put back on by hand is refused');
      bad((g) => { delete g.state.aiSheet; }, /does not match the record of events/, 'a sheet taken out while its changes are on record is refused');
      bad((g) => { g.state.aiSheet.days = '90'; }, /not in the shape/, 'a sheet with a number written as text is refused');
      bad((g) => { g.state.aiSheet.where = 'elsewhere'; }, /not in the shape/, 'a sheet with a place this page does not know is refused');
      [1.5, -1, 3651, null, NaN].forEach((d) => bad((g) => { g.state.aiSheet.days = d; }, /not in the shape/, 'a sheet that keeps prompts for ' + d + ' days is refused'));
      bad((g) => { g.state.aiSheet.extra = 1; g.state.aiSheet.reviewed_by = 5; }, /not in the shape/, 'a sheet with a reviewer that is not text is refused');
      { const alt = { model: 'Another model', where: 'tenant', leaves: true, log: 'service', days: 91, approved: 'exp', unstated: 'none', reviewed_by: 'Someone Else', reviewed_at: '11 Oct', entered_by: 'Priya Raman' };
        Object.keys(alt).forEach((fld) => bad((g) => { g.state.aiSheet[fld] = alt[fld]; }, /does not match the record of events/, 'a sheet whose “' + fld + '” was changed by hand is refused')); }
      bad((g) => { g.state.aiSheet = null; }, /should be object and is null/, 'a missing sheet is refused');
      bad((g) => { g.state.aiOn = 'yes'; }, /should be boolean/, 'a switch that is not on or off is refused');
      bad((g) => { g.state.events = g.state.events.slice(0, 1); }, /does not match the record of events|no longer matches/, 'taking the record of the change out is refused');
      // an older save, from before this existed, still loads and means the sample's own sheet with the switch on
      const old = JSON.parse(JSON.stringify(C.persistFile(Object.assign({}, S0, { dec: { 'CL-020': undefined } })))); delete old.state.aiOn; delete old.state.aiSheet;
      const ro = C.persistCheck(old); ag(ro.ok, 'a save from before AI use existed still loads (' + ro.problems.join(' ') + ')');
      // restored from the browser's own store
      const mem = {}, win = { localStorage: { getItem: (k) => (k in mem ? mem[k] : null), setItem: (k, v) => { mem[k] = String(v); }, removeItem: (k) => { delete mem[k]; } } };
      global.window = win; try { C.persistWrite(S, true); const rd = C.persistRead(); ag(rd.status === 'saved' && rd.state.aiOn === false && rd.state.aiSheet.approved === 'cui', 'the browser’s copy brings the switch and the sheet back');
        const raw = JSON.parse(mem[C.PERSIST_STORE]); raw.state.aiSheet.approved = 'exp'; mem[C.PERSIST_STORE] = JSON.stringify(raw); const rd2 = C.persistRead(); ag(rd2.state === null && /record of events/.test(rd2.refused || ''), 'a browser copy whose sheet was edited outside the page is refused and removed'); } finally { delete global.window; }
      // what Home says before a file is loaded
      const said = new C.Component().aiSaid(f.state); ag(/^AI use: switched off; Local model v1 on our own servers, approves CUI; sheet reviewed by B\. Chen$/.test(said), 'before a file replaces anything, Home says what AI use it would put in place (' + said + ')');
      ag(/^AI use: on; Local model v1 on our own servers, approves no marking only; sheet reviewed by A\. Moreno/.test(new C.Component().aiSaid({})), 'and a file with nothing about it means the sample’s own');
      ag(/sheet not reviewed/.test(new C.Component().aiSaid({ aiSheet: SH({ reviewed_by: '', reviewed_at: '' }) })), 'including a sheet nobody reviewed');
      // and the same line is in the summary shown on Home before anything is replaced
      { const c = new C.Component(); c.setState({ view: 'home', person: 'sam' }); c.keepRead(JSON.stringify(f), 'ai-off.json');
        ag(c.S.keepAsk === 'load' && c.S.keepSummary.some((t) => /^AI use: switched off; Local model v1 on our own servers, approves CUI; sheet reviewed by B\. Chen$/.test(t)), 'the summary shown before a file is loaded says what AI use the file would put in place (' + JSON.stringify(c.S.keepSummary) + ')'); }
    }
  }
  console.log('ISSUES', issues.size);
  issues.forEach((s, m) => console.log(' -', m, ' @', s));
  process.exitCode = issues.size ? 1 : 0;
  const never = []; ifSeen.forEach((n, k) => { if (!ifTrue.has(k)) never.push(k.split('@')[0]); });
  console.log('sc-if never true:', [...new Set(never)].join(', '));
}
