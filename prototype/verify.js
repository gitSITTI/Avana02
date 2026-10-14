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
const Component = new Function('DCLogic', code + '\nreturn {Component, CLUSTERS, CL_BY, statusOf, DEFAULTS, ORDER, decOf, SEED, PEOPLE, STRATS, REQS, universe, ALLOCS, required, resultsOf, dispositionsOf};')(DCLogic);
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
  PEOPLE.forEach((p) => { ['home', 'overview', 'results', 'review', 'explorer', 'methods', 'audit', 'policy', 'export'].forEach((v) => run(v + '-' + p.k, (c) => base(c, { view: v, person: p.k, chatOpen: v === 'review', glossary: v === 'overview' }))); });
  run('audit-chain', (c) => base(c, { view: 'audit', logTab: 'chain', tamper: true, verified: 'fail:2' }));
  run('audit-chain-ok', (c) => base(c, { view: 'audit', logTab: 'chain', verified: 'ok' }));
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
  console.log('ISSUES', issues.size);
  issues.forEach((s, m) => console.log(' -', m, ' @', s));
  process.exitCode = issues.size ? 1 : 0;
  const never = []; ifSeen.forEach((n, k) => { if (!ifTrue.has(k)) never.push(k.split('@')[0]); });
  console.log('sc-if never true:', [...new Set(never)].join(', '));
}
