const DEFAULTS = {
  view: 'open', source: 'sample', scope: 'all', person: 'sam', preview: '', hint: true, glossary: false, navClosed: {}, homeOpen: { 0: true },
  selected: 'CL-001', blind: null, blindDone: {}, events: [], verified: '', fmt: 'sphinx', tamper: false, published: false, baseId: 'DRAFT-0001',
  dec: {}, sign: {}, objections: {}, adjud: {}, res: {}, why: {}, ref: {}, alignOpen: false, hand: {}, sendF: {}, replyNote: {}, metArm: 'after', metSort: 'gain', metTable: false, peeled: {}, claims: {}, openVer: {}, liveVer: {}, dirs: {}, stale: {}, sib: {},
  qTab: 'me', qLane: '', qStatus: '', qAlloc: '', qLvl: '', qSearch: '', qPage: 0,
  xFilter: 'all', xAlloc: '', xLvl: 0, xGap: false, xPick: '', xPage: 0, lpage: 0, lfilter: '', logTab: 'ledger',
  chatOpen: false, chat: {}, chatInput: '', lensNote: {}, polLane: 'B', polNew: false, polCross: false, polBase: false, scopeChoice: 'all', pilotAlloc: 'Mission Computer', just: '', adjNote: {}, sibNote: {},
  gold: { labels: {}, adj: {}, skip: {}, last: {}, cut: 0.8, diff: true, note: '', all: false, settleNote: {} },
  rdec: {}, rcmp: '', rpick: false, rform: {},   /* single-requirement decisions, the requirement put beside the picked one, and the unsaved form for each */
  trTab: 'aliases', trOnly: 'approved', trMsg: '',   /* the trace map in Export: which table is shown, approved changes only or every decided change, and the last thing it did */
  keepAt: '', keepStatus: 'ready', keepRestored: null, keepMsg: null, keepAsk: '', keepSummary: [],   /* what Home says about the saved work: when it was last kept, whether the browser allows it, and a pending file load */
  aiOn: true, aiSheet: { model: 'Local model v1', where: 'ours', leaves: false, log: 'local', days: 90, approved: 'none', unstated: 'withhold', reviewed_by: 'A. Moreno, security office', reviewed_at: '2 Oct', entered_by: 'Morgan Hale' },   /* AI use: the project-wide switch and the data sheet the gate reads (aigate.js) */
  aiEdit: null, aiMsg: null, aiTab: 'groups',   /* the sheet being changed (nothing is kept until it is saved), the last thing the AI page did, and which list it shows */
  drop: '', openNote: '', impStep: 'verify', mapOver: {}, mapEdit: '', yamlOpen: false, docSel: {}, docVer: {}, docIds: {}, docFocus: 0
};

/* ---------- Input layer: what the Open and Import screens show. Counts, labels and locators below are the real output of the reqin
   reference code run on its synthetic fixtures (reqin/tests/make_fixtures.py), except the 'sample' source, which is illustrative. ---------- */
const TRUST = {
  Structured: { style: 'background:#E1F2E7;color:#14502B;border:1px solid #1B6B3A;', means: 'stable IDs and links' },
  Tabular: { style: 'background:#E8F0FD;color:#10337F;border:1px solid #1C5CAB;', means: 'rows you map' },
  Parsed: { style: 'background:#FFF0D2;color:#6B3D00;border:1px solid #A15C00;', means: 'a light read of model text' },
  Extracted: { style: 'background:#FDE3E0;color:#7A1510;border:1px solid #A6261E;', means: 'found in prose, you verify each' },
  Later: { style: 'background:#F1F3F5;color:#3C4852;border:1px dashed #6B7782;', means: 'not read directly yet' }
};
const SOURCES = [
  { k: 'sysml', title: 'SysML v2 model', tier: 'Structured or Parsed', trust: 'Structured', body: 'Systems Modeling API address (Structured), KPAR package, or a .sysml text file (Parsed).', note: 'For MSOSA releases that use SysML v2.' },
  { k: 'reqif', title: 'ReqIF export', tier: 'Structured', trust: 'Structured', body: 'From MSOSA, DOORS or DOORS Next. The most reliable file route.', note: 'MSOSA: Cameo Requirements Modeler export.' },
  { k: 'table', title: 'Spreadsheet or CSV', tier: 'Tabular', trust: 'Tabular', body: 'One requirement per row. You confirm which column is which.', note: 'Also DOORS CSV exports.' },
  { k: 'sql', title: 'Database (SQL)', tier: 'Tabular', trust: 'Tabular', body: 'You give a read-only query. Nothing is ever written to the database.', note: 'Anything but SELECT is refused.' },
  { k: 'doc', title: 'Word or PDF document', tier: 'Extracted', trust: 'Extracted', body: 'Statements are found in the text. You verify every one against the page.', note: 'The least certain route: use it when nothing else exists.' },
  { k: 'mdzip', title: 'MSOSA project file (.mdzip)', tier: 'Not read directly yet', trust: 'Later', body: 'Export ReqIF from MSOSA and open that instead.', note: 'Reading .mdzip directly is planned, not built.', later: true }
];
const RECENTS = [ { name: 'systems v2', src: 'SysML v2 model', k: 'sample' }, { name: 'MSoSA', src: 'ReqIF export', k: 'reqif' } ];
/* sample files offered in the drop zone: the app names what it recognised before you go on */
const FILES = [
  { f: 'reqs.reqif', src: 'reqif', trust: 'Structured', rec: 'ReqIF · reqs.reqif · 9 objects (8 requirements, 1 heading)' },
  { f: 'reqs.xlsx', src: 'table', trust: 'Tabular', rec: 'Excel · reqs.xlsx · 3 sheets: "Requirements" read; "Cover" and a hidden sheet skipped' },
  { f: 'model.sysml', src: 'sysml', trust: 'Parsed', rec: 'SysML v2 text · model.sysml · 9 requirement declarations (8 definitions read, 1 usage skipped)' },
  { f: 'reqs.db', src: 'sql', trust: 'Tabular', rec: 'SQLite database · reqs.db · table "reqs" · a read-only query is needed next' },
  { f: 'srs.pdf', src: 'doc', trust: 'Extracted', rec: 'PDF · srs.pdf · 1 page, 1 ruled table · statements will be found in the text' },
  { f: 'project.mdzip', src: 'mdzip', trust: 'Later', rec: 'MSOSA project (.mdzip) · recognised, but not read directly yet' }
];
const SLOTS = [
  ['uid', 'Requirement ID', 'ID, shown on every screen'],
  ['text', 'Statement', 'Requirement statement'],
  ['rationale', 'Rationale', 'Rationale panel'],
  ['verification', 'Verification', 'Verification: T, A, I or D'],
  ['allocation', 'Allocated to', 'Blocks the comparison'],
  ['owner', 'Owner', 'Blocks cross-owner merges'],
  ['baseline', 'Baseline', 'Baseline badge']
];
const T1 = 'The Flight Control Subsystem shall transmit a status message to the ground station within 200 ms of a mode change.';
const T2 = 'The Flight Control Subsystem shall transmit a status message to the ground station within 0.2 seconds of a mode change.';
const T3 = 'The Flight Control Subsystem shall retain at least 30 days of fault records.';
const FCS = 'Flight Control Subsystem';
const IMPORTS = {
  sample: {
    title: 'SysML v2 model', file: 'Reference air vehicle', where: 'Systems Modeling API · project "systems v2"', profile: 'sysml-v2-api', adapter: 'sysml_api', ns: 'DEMO-SYSML', fidelity: 'Structured',
    containers: '[requirement def]', illustrative: true,
    note: 'Illustrative only: this prototype has no server behind it, and the field names of the Systems Modeling API route are assumed in the reference code and not yet tested against a real server.',
    cols: ['shortName', 'declaredName', 'documentation', 'rationale (annotation)', 'verificationMethod (metadata)', 'satisfy … by (relationship)', 'owningPackage', 'commit tag'],
    rows: [['REQ-FCS-0101', 'StatusLatency', T1, 'Bounds ground-station loop latency', 'Test', FCS, 'FCS team', '—'], ['REQ-FCS-0102', 'StatusLatencySeconds', T2, '', 'Test', FCS, 'FCS team', '—'], ['REQ-FCS-0103', 'FaultRetention', T3, 'Maintenance planning', 'Inspection', FCS, 'FCS team', '—']].map((r) => [r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]]),
    map: { uid: ['shortName', 'Exact'], text: ['documentation', 'Exact'], rationale: ['rationale (annotation)', 'High'], verification: ['verificationMethod (metadata)', 'High'], allocation: ['satisfy … by (relationship)', 'Medium'], owner: ['owningPackage', 'Medium'], baseline: ['commit tag', 'Medium'] },
    safe: 'Read-only requests only: the app never writes to the model.'
  },
  sysml: {
    title: 'SysML v2 model', file: 'model.sysml', where: 'SysML v2 text file · requirement definitions', profile: 'proposed-model', adapter: 'sysml_text', ns: 'DEMO-MODEL', fidelity: 'Parsed',
    containers: '[requirement def]', counts: { read: 9, kept: 8, rej: 0, filt: 1, why: 'a requirement usage has no text of its own' },
    note: 'A .sysml text file is read by a light scanner (Parsed). The Systems Modeling API route gives Structured trust and is reached the same way.',
    cols: ['shortName', 'name', 'doc', 'typedBy'],
    rows: [['REQ-FCS-0101', 'StatusLatency', T1, ''], ['REQ-FCS-0102', 'StatusLatencySeconds', T2, ''], ['REQ-FCS-0103', 'FaultRetention', T3, '']],
    map: { uid: ['shortName', 'High'], text: ['doc', 'High'], rationale: [null, 'Low'], verification: [null, 'Low'], allocation: [null, 'Low'], owner: [null, 'Low'], baseline: [null, 'Low'] },
    safe: 'Source file not modified (hash unchanged).'
  },
  reqif: {
    title: 'ReqIF export', file: 'reqs.reqif', where: 'specification "Subsystem requirements" · object type Requirement (headings skipped)', profile: 'msosa-reqif', adapter: 'reqif', ns: 'DEMO-MSOSA', fidelity: 'Structured',
    containers: '[Requirement]', counts: { read: 9, kept: 8, rej: 0, filt: 1, why: 'the heading object is not a requirement' },
    note: 'Attribute names differ between exports. If your file calls them something else, change the field here: the change is saved in the profile.',
    cols: ['ReqIF.ForeignID', 'ReqIF.Text', 'Rationale', 'Verification Method'], strip: ['ReqIF.Text'],
    rows: [['REQ-FCS-0101', '<div><p>' + T1 + '</p></div>', 'Bounds ground-station loop latency', 'Test'], ['REQ-FCS-0102', '<div>' + T2 + '</div>', '', 'Test'], ['REQ-FCS-0103', '<div><p>' + T3 + '</p></div>', 'Maintenance planning', 'Inspection']],
    map: { uid: ['ReqIF.ForeignID', 'High'], text: ['ReqIF.Text', 'High'], rationale: ['Rationale', 'Medium'], verification: ['Verification Method', 'High'], allocation: [null, 'Low'], owner: [null, 'Low'], baseline: [null, 'Low'] },
    safe: 'Source file not modified (hash unchanged).'
  },
  table: {
    title: 'Spreadsheet or CSV', file: 'reqs.xlsx', where: 'sheet "Requirements" (the "Cover" sheet and a hidden sheet are skipped)', profile: 'xlsx-srs', adapter: 'tabular', ns: 'DEMO-SRS', fidelity: 'Tabular',
    containers: '[Requirements]', counts: { read: 9, kept: 8, rej: 0, filt: 1, why: 'the "Cover" sheet is not requirements' },
    note: 'Three title rows sit above the header. The app found the header row on its own.',
    cols: ['Req #', 'Requirement Text', 'Why', 'V Method', 'Subsystem', 'IPT'], vmap: { 'V Method': { T: 'Test', A: 'Analysis', I: 'Inspection', D: 'Demonstration' } },
    rows: [['REQ-FCS-0101', T1, 'Bounds ground-station loop latency', 'T', FCS, 'FCS team'], ['REQ-FCS-0102', T2, '', 'T', FCS, 'FCS team'], ['REQ-FCS-0103', T3, 'Maintenance planning', 'I', FCS, 'FCS team']],
    map: { uid: ['Req #', 'High'], text: ['Requirement Text', 'High'], rationale: ['Why', 'Medium'], verification: ['V Method', 'High'], allocation: ['Subsystem', 'Medium'], owner: ['IPT', 'Medium'], baseline: [null, 'Low'] },
    safe: 'Source file not modified (hash unchanged).'
  },
  sql: {
    title: 'Database (SQL)', file: 'reqs.db', where: 'read-only query', profile: 'proposed-sql', adapter: 'sql', ns: 'DEMO-DB', fidelity: 'Tabular',
    containers: '[query]', counts: { read: 8, kept: 8, rej: 0, filt: 0, why: '' },
    query: 'SELECT req_uid, statement, rationale, verif, alloc, owner FROM reqs WHERE active = 1',
    note: 'The app checks the query is a single SELECT before it runs, and opens the database read-only. Credentials stay in your environment, not in the profile.',
    cols: ['req_uid', 'statement', 'rationale', 'verif', 'alloc', 'owner'],
    rows: [['REQ-FCS-0101', T1, 'Bounds ground-station loop latency', 'Test', FCS, 'FCS team'], ['REQ-FCS-0102', T2, '', 'Test', FCS, 'FCS team'], ['REQ-FCS-0103', T3, 'Maintenance planning', 'Inspection', FCS, 'FCS team']],
    map: { uid: ['req_uid', 'High'], text: ['statement', 'High'], rationale: ['rationale', 'Medium'], verification: ['verif', 'High'], allocation: ['alloc', 'Medium'], owner: ['owner', 'Medium'], baseline: [null, 'Low'] },
    safe: 'Query accepted as read-only (one SELECT). Nothing is written to the database.'
  },
  doc: {
    title: 'Word or PDF document', file: 'srs.pdf', where: 'page 1 · prose and 1 ruled table', profile: 'proposed-pdf', adapter: 'pdf', ns: 'DEMO-PDF', fidelity: 'Extracted',
    containers: '[prose, p1-table1]', counts: { read: 8, kept: 8, rej: 0, filt: 0, why: '' },
    note: 'Sentences with shall, must, should or will became candidate statements. Table rows were read as rows, not as prose.',
    cols: ['text / Requirement', 'lead_id / ID', 'section', 'Verification'],
    rows: [[T1, 'REQ-FCS-0101', '3 Performance requirements', ''], [T2, 'REQ-FCS-0102', '3 Performance requirements', ''], [T3, 'REQ-FCS-0103', '3 Performance requirements', '']],
    map: { uid: ['lead_id / ID', 'High'], text: ['text / Requirement', 'High'], rationale: [null, 'Low'], verification: ['Verification', 'High'], allocation: [null, 'Low'], owner: [null, 'Low'], baseline: [null, 'Low'] },
    safe: 'Source file not modified (hash unchanged).'
  }
};
/* The eight statements reqin finds in srs.pdf (real output). `loc` is the human form of the locator: p1:blk2 is "p1 ¶3". */
const DOC_ITEMS = [
  { uid: 'REQ-FCS-0101', loc: 'p1 ¶3', raw: 'p1:blk2', text: T1 },
  { uid: 'REQ-FCS-0102', loc: 'p1 ¶4', raw: 'p1:blk3', text: T2 },
  { uid: 'REQ-FCS-0103', loc: 'p1 ¶5, first sentence', raw: 'p1:blk4.1', text: T3 },
  { uid: 'pdf:prose:p1:blk4.2', invented: true, loc: 'p1 ¶5, second sentence', raw: 'p1:blk4.2', text: 'The Flight Control Subsystem should retain at least 14 days of fault records.' },
  { uid: 'REQ-PWR-0201', loc: 'table 1, row 2', raw: 'p1:t1!R2', text: 'The Power Subsystem shall not exceed a mass of 12 kg.' },
  { uid: 'REQ-PWR-0202', loc: 'table 1, row 3', raw: 'p1:t1!R3', text: 'The Power Subsystem shall provide 28 VDC to the Mission Computer.' },
  { uid: 'REQ-MC-0301', loc: 'table 1, row 4', raw: 'p1:t1!R4', text: 'The Mission Computer shall log each operator command with a timestamp.' },
  { uid: 'REQ-MC-0302', loc: 'table 1, row 5', raw: 'p1:t1!R5', text: 'The Mission Computer shall log every operator command together with the time it was received.' }
];
/* the page those statements came from: blocks of spans; `it` is an index into DOC_ITEMS, or -1 for text that is not a statement */
const DOC_PAGE = [
  { kind: 'h', spans: [{ t: '3 Performance requirements', it: -1 }] },
  { kind: 'p', spans: [{ t: 'This section describes the performance expectations in plain language and contains no obligations.', it: -1 }] },
  { kind: 'p', spans: [{ t: 'REQ-FCS-0101: ', it: -1 }, { t: T1, it: 0 }] },
  { kind: 'p', spans: [{ t: 'REQ-FCS-0102: ', it: -1 }, { t: T2, it: 1 }] },
  { kind: 'p', spans: [{ t: 'REQ-FCS-0103: ', it: -1 }, { t: T3, it: 2 }, { t: ' ', it: -1 }, { t: DOC_ITEMS[3].text, it: 3 }] },
  { kind: 'h', spans: [{ t: '4 Power and computing', it: -1 }] },
  { kind: 'row', head: true, spans: [{ t: 'ID', it: -1 }, { t: 'Requirement', it: -1 }, { t: 'Verification', it: -1 }] },
  { kind: 'row', spans: [{ t: 'REQ-PWR-0201', it: -1 }, { t: DOC_ITEMS[4].text, it: 4 }, { t: 'Analysis', it: -1 }] },
  { kind: 'row', spans: [{ t: 'REQ-PWR-0202', it: -1 }, { t: DOC_ITEMS[5].text, it: 5 }, { t: 'Test', it: -1 }] },
  { kind: 'row', spans: [{ t: 'REQ-MC-0301', it: -1 }, { t: DOC_ITEMS[6].text, it: 6 }, { t: 'Demonstration', it: -1 }] },
  { kind: 'row', spans: [{ t: 'REQ-MC-0302', it: -1 }, { t: DOC_ITEMS[7].text, it: 7 }, { t: 'Demonstration', it: -1 }] }
];
const LENSES = [
  { k: 'SE', name: 'Systems engineer', short: 'SE' }, { k: 'PE', name: 'Process engineer', short: 'PE' },
  { k: 'UX', name: 'UI/UX engineer', short: 'UX' }, { k: 'NU', name: 'New user', short: 'NU' }
];
const SLOT_NAME = { SE: 'Systems engineer', PE: 'Process engineer', UX: 'UI/UX engineer', NU: 'New user', OWN: 'Owners', ADJ: 'Adjudicator' };
const LENS_Q = {
  SE: 'Is the technical content right, and is anything lost?',
  PE: 'Can this change be processed, traced and defended under our process?',
  UX: 'Will the people who read this wording understand it, and is it consistent?',
  NU: 'Can someone new understand this without insider help?'
};
const LENS_MEANS = {
  SE: 'The technical meaning is preserved, nothing is lost, and any conflict was raised as a conflict.',
  PE: 'This change can be processed under our change and trace process, and the record of how it was decided is complete.',
  UX: 'The wording matches the project\'s terms and reads clearly to the people who use it.',
  NU: 'A newcomer can read this, say what it means, and tell what would show it is met.'
};
const LENS_LOOK = {
  SE: 'Parameters side by side, trace links and verification method.',
  PE: 'Baseline, owners, change requests, the AI record and the rule check.',
  UX: 'Term use across the project, readability and one-thought wording.',
  NU: 'Only the wording first. The source, owners and AI answer open after your own read.'
};
const PEOPLE = [
  { k: 'sam', name: 'Sam Okafor', lens: 'SE', role: 'reviewer' },
  { k: 'priya', name: 'Priya Raman', lens: 'PE', role: 'reviewer' },
  { k: 'jordan', name: 'Jordan Ellis', lens: 'UX', role: 'reviewer' },
  { k: 'casey', name: 'Casey Whitfield', lens: 'NU', role: 'reviewer' },
  { k: 'morgan', name: 'Morgan Hale', lens: 'SE', role: 'lead' },
  { k: 'lee', name: 'Lee Park', lens: '', role: 'observer' }
];
const ROLE_NAME = { reviewer: 'Reviewer', lead: 'Lead (adjudicator)', observer: 'Observer · read only' };
const GUARDS = [
  'Cited requirement IDs exist', 'Quoted evidence is verbatim', 'Numbers preserved', 'Units compatible', 'Shall / should / will preserved',
  'Negation preserved', 'Conditions kept', 'Actors, acronyms and part numbers match', 'No invented content', 'Round-trip entailment holds'
];
const REL_LABEL = { EQUIVALENT: 'Equivalent', VARIANT: 'Variant', SUBSUMES: 'Subsumes', CONFLICT: 'Conflict', COMPLEMENTARY: 'Complementary' };
const REL_PLAIN = {
  EQUIVALENT: 'Same obligation, worded differently.',
  VARIANT: 'Same subject, but a value, unit, modal verb or condition differs.',
  SUBSUMES: 'One requirement contains the other and adds more.',
  CONFLICT: 'Both cannot be true at once.',
  COMPLEMENTARY: 'Two halves of one behaviour.'
};
const REL_STYLE = {
  EQUIVALENT: 'background:#E1F2E7;color:#14502B;', VARIANT: 'background:#FFF0D2;color:#6B3D00;', SUBSUMES: 'background:#E4ECFB;color:#123C8C;',
  CONFLICT: 'background:#FDE3E0;color:#7A1510;', COMPLEMENTARY: 'background:#EDE8F8;color:#3A2A80;'
};
const LANE_NAME = { A: 'Lane A · low risk', B: 'Lane B · needs evidence', C: 'Lane C · conflict' };
const ACTION_LABEL = { merge: 'Merged into one requirement', reject: 'Rejected', link: 'Kept and linked', escalate: 'Escalated to owners', supersede: 'Older requirement superseded' };
const STRATS = [
  { k: 'stringent', short: 'most stringent', name: 'Most stringent', sub: 'Computed. The strictest ranked value wins.', mark: 'sq' },
  { k: 'least', short: 'least stringent', name: 'Least stringent', sub: 'Computed. Weakens the requirement: flagged, needs owner, PE and a note.', mark: 'sq' },
  { k: 'median', short: 'median', name: 'Median', sub: 'Computed. Needs at least three ranked members; gated.', mark: 'sq' },
  { k: 'member', short: 'one member\'s wording', name: 'One member\'s wording', sub: 'You pick a member. Its wording is kept word for word.', mark: 'sq' },
  { k: 'own', short: 'own wording', name: 'My own wording', sub: 'You write it. Guards still run. A note is required.', mark: 'ci' },
  { k: 'ai', short: 'AI proposal', name: 'Ask the AI to propose', sub: 'A draft only. Nothing saves until you record the decision.', mark: 'di' }
];
const REASONS = [
  ['R-STR', 'Strictest satisfies all ranked members'],
  ['R-PAR', 'Parent requires this value'],
  ['R-OWN', 'Owner confirmed (comment linked)'],
  ['R-SEP', 'Different condition: kept separate'],
  ['R-NOT', 'Not a duplicate: different function'],
  ['R-AIW', 'AI was wrong about: unit, scope, number or other'],
  ['R-SRC', 'Source changed: decided again'],
  ['R-OTH', 'Other (a note is required)']
];
const REASON_NAME = Object.fromEntries(REASONS);
const BLIND_STYLE = 'min-height:44px;padding:0 14px;background:#FFFFFF;border:1px solid #7A8793;border-radius:6px;cursor:pointer';

/* ---------- small helpers ---------- */
function rng(seed) { let a = seed >>> 0; return function () { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
function h32(str) { let h = 5381; for (let i = 0; i < str.length; i++) { h = ((h << 5) + h + str.charCodeAt(i)) | 0; } return ('00000000' + (h >>> 0).toString(16)).slice(-8); }
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
function T(v, uv) {
  if (v >= 1000 && v % 1000 === 0 && uv === 0) { const s = v / 1000; return s + (s === 1 ? ' second' : ' seconds'); }
  return v + (uv === 1 ? ' ms' : ' milliseconds');
}
const UNIT_RE = /(\d[\d,]*(?:\.\d+)?)\s*(milliseconds?|ms|seconds?|s|days?|hz|percent|%|kg|kilograms?|meters?|m|degrees?|fault\s+records?|records?|vdc)\b/gi;
function quantities(text) {
  const out = []; let m; UNIT_RE.lastIndex = 0;
  while ((m = UNIT_RE.exec(text))) { const n = parseFloat(m[1].replace(/,/g, '')); const u = m[2].toLowerCase(); out.push({ raw: m[0], n: /^s(econds?)?$/.test(u) ? n * 1000 : n, unit: u }); }
  return out;
}
function joinOr(a) { return a.length < 2 ? a.join('') : a.slice(0, -1).join(', ') + ' or ' + a[a.length - 1]; }
function modalOf(text) { const m = /\b(shall|should|will|may|must)\b/i.exec(text); return m ? m[1].toLowerCase() : ''; }
function negOf(text) { return /\b(shall|should|will)\s+not\b|\bnever\b|\bwithout\b/i.test(text); }
const MODAL_RANK = { shall: 3, must: 3, will: 2, should: 1, may: 0, '': 0 };
function fmtVal(c, v) {
  if (v === null || v === undefined) return '—';
  if (c.time) return v >= 1000 && v % 1000 === 0 ? (v / 1000) + ' s' : v + ' ms';
  return v + ' ' + c.unit;
}
