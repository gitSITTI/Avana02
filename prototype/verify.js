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
const Component = new Function('DCLogic', code + '\nreturn {Component, CLUSTERS, CL_BY, statusOf, DEFAULTS, ORDER, decOf, SEED, PEOPLE, STRATS, REQS, universe, ALLOCS, required};')(DCLogic);
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
  PEOPLE.forEach((p) => { ['overview', 'review', 'explorer', 'methods', 'audit', 'policy', 'export'].forEach((v) => run(v + '-' + p.k, (c) => base(c, { view: v, person: p.k, chatOpen: v === 'review', glossary: v === 'overview' }))); });
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
  run('blind off/on', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: 'casey', blind: true }));
  run('blind done', (c) => base(c, { view: 'review', selected: 'CL-001', qTab: 'all', person: 'casey', blindDone: { 'CL-001': 'Variant' } }));
  run('chat msgs', (c) => { base(c, { view: 'review', selected: 'CL-042', qTab: 'all', chatOpen: true }); c.setState({ chat: {} }); const v0 = c.renderVals(); v0.chips[0].onClick(); v0.chips[2].onClick(); v0.chips[3].onClick(); });
  run('chat msgs2', (c) => { base(c, { view: 'review', selected: 'CL-042', qTab: 'all', chatOpen: true, person: 'sam' }); for (let i = 0; i < 6; i++) { const v0 = c.renderVals(); v0.chips[i].onClick(); } c.setState({ chatInput: 'what is the weather' }); c.renderVals().sendChat(); });
  run('export w/ ready', (c) => base(c, { view: 'export', published: true }));
  // filters
  run('queue filters', (c) => base(c, { view: 'review', qTab: 'all', qLane: 'B', qStatus: 'open', qAlloc: 'Flight Control', qSearch: 'retention' }));
  run('queue empty', (c) => base(c, { view: 'review', qTab: 'all', qSearch: 'zzzzzz' }));
  run('pilot scope', (c) => base(c, { view: 'review', scope: 'Mission Computer', qTab: 'all' }));
  run('pilot overview', (c) => base(c, { view: 'overview', scope: 'Data Recorder' }));
  console.log('ISSUES', issues.size);
  issues.forEach((s, m) => console.log(' -', m, ' @', s));
  process.exitCode = issues.size ? 1 : 0;
  const never = []; ifSeen.forEach((n, k) => { if (!ifTrue.has(k)) never.push(k.split('@')[0]); });
  console.log('sc-if never true:', [...new Set(never)].join(', '));
}
