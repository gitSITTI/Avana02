/* ---------- allocations and requirement families ---------- */
const ALLOCS = [
  { k: 'Flight Control', pre: 'FCS', owner: 'FCS team', sub: 'Flight Control Subsystem', w: 22 },
  { k: 'Ground Station', pre: 'GCS', owner: 'Ground team', sub: 'Ground Station', w: 14 },
  { k: 'Data Recorder', pre: 'SYS', owner: 'Data team', sub: 'Data Recorder', w: 12 },
  { k: 'Power Subsystem', pre: 'PWR', owner: 'Power team', sub: 'Power Subsystem', w: 10 },
  { k: 'Data Link', pre: 'LNK', owner: 'Link team', sub: 'Data Link', w: 12 },
  { k: 'Navigation', pre: 'NAV', owner: 'Nav team', sub: 'Navigation Subsystem', w: 12 },
  { k: 'Mission Computer', pre: 'MSN', owner: 'Mission team', sub: 'Mission Computer', w: 10 },
  { k: 'Thermal Control', pre: 'THM', owner: 'Thermal team', sub: 'Thermal Control Subsystem', w: 8 }
];
const ALLOC_BY = Object.fromEntries(ALLOCS.map((a) => [a.k, a]));
const VERIFS = ['Test', 'Analysis', 'Inspection', 'Demonstration'];
const FAMS = [
  { k: 'resp', name: 'Response time', dir: 'lower', time: true, vals: [50, 100, 150, 200, 250, 500, 1000, 2000], things: ['status request', 'mode command', 'configuration request', 'fault query'],
    mk: (S, v, st, x, uv) => [`The ${S} shall respond to a ${x} within ${T(v, uv)}.`, `The ${S} shall complete its response to a ${x} in ${T(v, uv)} or less.`, `Upon receipt of a ${x}, the ${S} shall respond within ${T(v, uv)}.`][st % 3] },
  { k: 'hb', name: 'Heartbeat interval', dir: 'lower', time: true, vals: [500, 1000, 2000, 5000, 10000, 30000], things: ['heartbeat message', 'keep-alive message', 'status beacon'],
    mk: (S, v, st, x, uv) => [`The ${S} shall transmit a ${x} every ${T(v, uv)}.`, `A ${x} shall be sent by the ${S} at intervals of ${T(v, uv)}.`, `The ${S} shall emit a ${x} once every ${T(v, uv)}.`][st % 3] },
  { k: 'boot', name: 'Start-up time', dir: 'lower', time: true, vals: [5000, 10000, 15000, 30000, 60000, 90000], things: ['power application'],
    mk: (S, v, st, x, uv) => [`The ${S} shall be operational within ${T(v, uv)} of power application.`, `Time from power application to operational state of the ${S} shall be at most ${T(v, uv)}.`, `After power-up, the ${S} shall reach operational state within ${T(v, uv)}.`][st % 3] },
  { k: 'ret', name: 'Data retention', dir: 'higher', unit: 'days', vals: [7, 14, 30, 60, 90, 180, 365], things: ['fault events', 'mode changes', 'health records', 'command logs', 'calibration records'],
    mk: (S, v, st, x) => [`The ${S} shall retain ${x} for at least ${v} days.`, `The ${S} shall store ${x} for a minimum of ${v} days.`, `${cap(x)} shall be kept by the ${S} for ${v} days or longer.`][st % 3] },
  { k: 'rate', name: 'Update rate', dir: 'higher', unit: 'Hz', vals: [1, 2, 5, 10, 20, 50], things: ['position data', 'attitude data', 'health status', 'bus voltage'],
    mk: (S, v, st, x) => [`The ${S} shall update ${x} at a rate of at least ${v} Hz.`, `${cap(x)} shall be refreshed by the ${S} at a minimum rate of ${v} Hz.`, `The ${S} shall publish ${x} at ${v} Hz or faster.`][st % 3] },
  { k: 'avail', name: 'Availability', dir: 'higher', unit: 'percent', vals: [99, 99.5, 99.9, 99.95], things: ['mission time'],
    mk: (S, v, st) => [`The ${S} shall achieve an availability of at least ${v} percent.`, `The ${S} shall provide a minimum availability of ${v} percent.`, `The ${S} shall be available for at least ${v} percent of mission time.`][st % 3] },
  { k: 'mass', name: 'Mass limit', dir: 'lower', unit: 'kg', vals: [2.5, 5, 8, 12, 20, 35], things: ['mass'],
    mk: (S, v, st) => [`The ${S} shall have a mass of at most ${v} kg.`, `The ${S} shall have a maximum mass of ${v} kilograms.`, `The mass of the ${S} shall be ${v} kg or less.`][st % 3] },
  { k: 'acc', name: 'Position accuracy', dir: 'lower', unit: 'm', vals: [1, 2, 5, 10, 25], things: ['position'],
    mk: (S, v, st) => [`The ${S} shall report position to within ${v} meters.`, `The ${S} shall determine position with an error of at most ${v} meters.`, `Reported position error of the ${S} shall be ${v} m or less.`][st % 3] },
  { k: 'temp', name: 'Operating temperature', dir: 'higher', unit: 'degrees', vals: [50, 55, 60, 70, 85], things: ['ambient temperature'],
    mk: (S, v, st) => [`The ${S} shall operate at ambient temperatures up to ${v} degrees Celsius.`, `Operation of the ${S} shall be supported at ambient temperatures of up to ${v} degrees Celsius.`, `The ${S} shall remain operational at ${v} degrees Celsius or higher.`][st % 3] },
  { k: 'cap', name: 'Storage capacity', dir: 'higher', unit: 'records', vals: [1000, 5000, 10000, 50000], things: ['fault records'],
    mk: (S, v, st) => [`The ${S} shall store at least ${v} fault records.`, `Storage for a minimum of ${v} fault records shall be provided by the ${S}.`, `The ${S} shall hold ${v} fault records or more.`][st % 3] }
];
const FAM_BY = Object.fromEntries(FAMS.map((f) => [f.k, f]));
const MODAL_THINGS = ['display the aircraft health status', 'log every commanded mode change', 'indicate link quality to the operator', 'acknowledge each uplinked command', 'report battery state to the operator'];
const NEG_THINGS = ['encrypt downlinked telemetry', 'log rejected commands', 'broadcast its position', 'accept commands during initialization', 'overwrite the oldest records'];
const SUBS_THINGS = ['all faults', 'all mode changes', 'all rejected commands'];
const SUBS_EXTRA = ['with a UTC timestamp and a fault code', 'with the source identifier and a sequence number', 'with a UTC timestamp'];
const COND_THINGS = ['report degraded status', 'limit transmit power', 'inhibit mode changes', 'record every command'];
const CONDS = ['when airborne', 'on the ground', 'in maintenance mode', 'during start-up'];

/* ---------- the nine hand-written clusters ---------- */
function mem(id, owner, alloc, verif, base, text, extra) {
  return Object.assign({ id, owner, alloc, level: 'System', verif, base, text, v: null, cond: '', rankable: true, xr: 0, alts: [] }, extra || {});
}
const HAND = [
  {
    id: 'CL-001', lane: 'A', rel: 'EQUIVALENT', kind: 'equiv', title: 'Health message timing, two wordings', famKey: 'resp', param: 'State-change message latency', dir: 'lower', time: true, unit: 'ms', alloc: 'Flight Control',
    members: [
      mem('REQ-FCS-0212', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'The Flight Control Subsystem shall transmit a health status message to the Ground Station within 5 seconds of a state change.', { v: 5000 }),
      mem('REQ-GCS-0087', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'Upon a state change, the Flight Control Subsystem shall send a health status message to the Ground Station within 5000 milliseconds.', { v: 5000 })
    ],
    m: { fuzzy: 0.58, tfidf: 0.51, embed: 0.93, cross: 0.90, eAB: 0.96, eBA: 0.95, contra: 0.01, p: 0.97 },
    mNote: 'Character-level scores are low because the wording differs, but meaning and values match.',
    ai: { mode: 'draft', proposal: 'Upon a state change, the Flight Control Subsystem shall transmit a health status message to the Ground Station within 5 seconds.', verdict: '', conf: 0, votes: '', why: 'The AI only drafted merged wording here. The mechanical methods already agree.', quotes: [] },
    aiDraft: 'Upon a state change, the Flight Control Subsystem shall transmit a health status message to the Ground Station within 5 seconds.',
    guards: 'pppppppppp', gNotes: { 3: '5 seconds = 5000 ms after unit conversion' },
    actions: [['merge', 'Merge into one'], ['reject', 'Not a duplicate']]
  },
  {
    id: 'CL-002', lane: 'A', rel: 'EQUIVALENT', kind: 'equiv', title: 'Fault record retention', famKey: 'ret', param: 'Fault record retention', dir: 'higher', unit: 'days', alloc: 'Data Recorder',
    members: [
      mem('REQ-SYS-0140', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall store all fault events for at least 30 days.', { v: 30 }),
      mem('REQ-SYS-0391', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall store all fault events for a minimum of 30 days.', { v: 30 })
    ],
    m: { fuzzy: 0.82, tfidf: 0.71, embed: 0.96, cross: 0.95, eAB: 0.97, eBA: 0.96, contra: 0.01, p: 0.98 },
    mNote: '"At least" and "a minimum of" point the same direction, so the limit is the same.',
    ai: { mode: 'draft', proposal: 'The Data Recorder shall store all fault events for at least 30 days.', verdict: '', conf: 0, votes: '', why: 'The AI only drafted merged wording here. It reused the wording of REQ-SYS-0140.', quotes: [] },
    aiDraft: 'The Data Recorder shall store all fault events for at least 30 days.',
    guards: 'pppppppppp', gNotes: { 3: '30 days = 30 days' },
    actions: [['merge', 'Merge into one'], ['reject', 'Not a duplicate']]
  },
  {
    id: 'CL-003', lane: 'B', rel: 'VARIANT', kind: 'varV', title: 'Heartbeat rate: 1 s or 10 s?', famKey: 'hb', param: 'Heartbeat interval', dir: 'lower', time: true, unit: 'ms', alloc: 'Flight Control',
    members: [
      mem('REQ-FCS-0215', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'The Flight Control Subsystem shall transmit a heartbeat message to the Ground Station every 1 second.', { v: 1000 }),
      mem('REQ-GCS-0102', 'Ground team', 'Ground Station', 'Test', 'Pre-baseline', 'The Flight Control Subsystem shall transmit a heartbeat message to the Ground Station every 10 seconds.', { v: 10000 })
    ],
    m: { fuzzy: 0.96, tfidf: 0.86, embed: 0.97, cross: 0.93, eAB: 0.81, eBA: 0.79, contra: 0.05, p: 0.71 },
    mNote: 'Every similarity score is high, yet the interval differs tenfold. Similarity cannot see this; the number guard can.',
    ai: { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: 88, votes: '3 of 3 runs agree', why: 'Same actor, action and object. The interval differs (1 s against 10 s) and the two owners differ, so neither wording can replace the other.', quotes: [['A', 'every 1 second'], ['B', 'every 10 seconds']], action: 'Keep both and ask the two owners which interval applies.' },
    aiDraft: 'The Flight Control Subsystem shall transmit a heartbeat message to the Ground Station every 1 second.',
    guards: 'ppfppppppp', gNotes: { 2: '1 second ≠ 10 seconds' },
    actions: [['merge', 'Merge into one'], ['link', 'Keep both and link'], ['escalate', 'Ask the owners'], ['reject', 'Reject suggestion']]
  },
  {
    id: 'CL-004', lane: 'B', rel: 'SUBSUMES', kind: 'subs', title: 'Fault logging: plain or with timestamp', famKey: 'clauses', param: 'Logged content', dir: 'more', unit: 'clauses', alloc: 'Data Recorder',
    members: [
      mem('REQ-SYS-0158', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The system shall log all faults.', { xr: 0 }),
      mem('REQ-SYS-0402', 'Data team', 'Data Recorder', 'Test', 'Pre-baseline', 'The system shall log all faults with a UTC timestamp and a fault code.', { xr: 2 })
    ],
    m: { fuzzy: 0.64, tfidf: 0.58, embed: 0.86, cross: 0.80, eAB: 0.12, eBA: 0.94, contra: 0.02, p: 0.22 },
    mNote: 'B entails A (0.94) but A does not entail B (0.12): B is the stricter requirement.',
    ai: { mode: 'judge', proposal: 'Keep REQ-SYS-0402. Link REQ-SYS-0158 as its parent and keep the stricter verification method (Test).', verdict: 'SUBSUMES (B stricter)', conf: 81, votes: '3 of 3 runs agree', why: 'B contains everything A requires and adds a UTC timestamp and a fault code. Verification methods differ (Inspection against Test), so the survivor keeps Test.', quotes: [['B', 'with a UTC timestamp and a fault code']], action: 'Link A as parent of B; do not delete A.' },
    aiDraft: 'The system shall log all faults with a UTC timestamp and a fault code.',
    guards: 'ppppppppwp', gNotes: { 8: 'Merged wording would add "UTC timestamp", which A does not contain' },
    actions: [['link', 'Link parent and child'], ['supersede', 'Supersede the older'], ['reject', 'Reject suggestion']]
  },
  {
    id: 'CL-005', lane: 'B', rel: 'VARIANT', kind: 'modal', title: 'Health display: shall or should?', famKey: 'modal', param: 'Obligation level', dir: 'modal', unit: '', alloc: 'Ground Station',
    members: [
      mem('REQ-GCS-0044', 'Ground team', 'Ground Station', 'Demonstration', 'Pre-baseline', 'The Ground Station shall display the aircraft health status.'),
      mem('REQ-GCS-0231', 'Ground team', 'Ground Station', 'Demonstration', 'Pre-baseline', 'The Ground Station should display the aircraft health status.')
    ],
    m: { fuzzy: 0.97, tfidf: 0.88, embed: 0.98, cross: 0.95, eAB: 0.90, eBA: 0.88, contra: 0.03, p: 0.64 },
    mNote: 'Only one word differs, and it changes the obligation: "shall" is mandatory, "should" is a goal.',
    ai: { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: 79, votes: '2 of 3 runs agree', why: 'Only the modal verb differs. They are not the same obligation. One run called them equivalent, which the modal guard overrode.', quotes: [['A', 'shall display'], ['B', 'should display']], action: 'Keep both until the owner decides whether this is mandatory.' },
    aiDraft: 'The Ground Station shall display the aircraft health status.',
    guards: 'ppppfppppp', gNotes: { 4: '"shall" in A, "should" in B' },
    actions: [['merge', 'Merge into one'], ['link', 'Keep both and link'], ['escalate', 'Ask the owner'], ['reject', 'Reject suggestion']]
  },
  {
    id: 'CL-006', lane: 'C', rel: 'CONFLICT', kind: 'confV', title: 'Bus voltage: 28 VDC or 270 VDC?', famKey: 'bus', param: 'Nominal bus voltage', dir: 'none', unit: 'VDC', alloc: 'Power Subsystem',
    members: [
      mem('REQ-PWR-0010', 'Power team', 'Power Subsystem', 'Test', 'Pre-baseline', 'The Power Subsystem shall provide a 28 VDC nominal bus voltage.', { v: 28 }),
      mem('REQ-AVI-0077', 'Avionics team', 'Power Subsystem', 'Test', 'Pre-baseline', 'The Power Subsystem shall provide a 270 VDC nominal bus voltage.', { v: 270 })
    ],
    m: { fuzzy: 0.93, tfidf: 0.84, embed: 0.95, cross: 0.71, eAB: 0.08, eBA: 0.07, contra: 0.88, p: 0.12 },
    mNote: 'High text similarity, but the NLI model sees a contradiction (0.88).',
    ai: { mode: 'judge', proposal: '', verdict: 'CONFLICT', conf: 91, votes: '3 of 3 runs agree', why: 'One bus cannot have two different nominal voltages. This needs a decision from both owners, not a merge.', quotes: [['A', '28 VDC'], ['B', '270 VDC']], action: 'Escalate to Power team and Avionics team.' },
    aiDraft: '',
    guards: 'ppfppppppf', gNotes: { 2: '28 VDC ≠ 270 VDC', 9: 'Any merged wording would contradict one source' },
    actions: [['escalate', 'Escalate to owners'], ['reject', 'Not a conflict']]
  },
  {
    id: 'CL-007', lane: 'C', rel: 'CONFLICT', kind: 'confN', title: 'Telemetry encryption: on or off?', famKey: 'neg', param: 'Telemetry encryption', dir: 'none', unit: '', alloc: 'Data Link',
    members: [
      mem('REQ-LNK-0301', 'Link team', 'Data Link', 'Analysis', 'Pre-baseline', 'The Data Link shall encrypt all downlinked telemetry.'),
      mem('REQ-LNK-0355', 'Link team', 'Data Link', 'Analysis', 'Pre-baseline', 'The Data Link shall not encrypt downlinked telemetry.')
    ],
    m: { fuzzy: 0.98, tfidf: 0.90, embed: 0.97, cross: 0.55, eAB: 0.02, eBA: 0.03, contra: 0.97, p: 0.05 },
    mNote: 'A keyword "token set" score would call these identical (100). The word "not" is invisible to it.',
    ai: { mode: 'none', proposal: '', verdict: '', conf: 0, votes: '', why: 'No AI needed. The NLI contradiction score (0.97) and the negation guard already decide this.', quotes: [] },
    aiDraft: '',
    guards: 'pppppfpppf', gNotes: { 5: '"not" appears in B only', 9: 'No wording satisfies both sources' },
    actions: [['escalate', 'Open conflict record'], ['reject', 'Not a conflict']]
  },
  {
    id: 'CL-042', lane: 'A', rel: 'EQUIVALENT', kind: 'equiv', title: 'Health message timing, three wordings', famKey: 'hb', param: 'Heartbeat interval', dir: 'lower', time: true, unit: 'ms', alloc: 'Flight Control',
    members: [
      mem('REQ-FCS-0312', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'The Flight Control Subsystem shall transmit a health status message every 1 second.', { v: 1000 }),
      mem('REQ-FCS-0318', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'The FCS shall send a heartbeat to the Mission Computer at 1 Hz.', { v: 1000, alts: [1] }),
      mem('REQ-FCS-0324', 'FCS team', 'Flight Control', 'Test', 'Pre-baseline', 'The Flight Control Subsystem shall transmit a heartbeat message every second.', { v: 1000 })
    ],
    m: { fuzzy: 0.52, tfidf: 0.47, embed: 0.91, cross: 0.88, eAB: 0.93, eBA: 0.91, contra: 0.02, p: 0.94 },
    mNote: '"1 Hz", "every 1 second" and "every second" are the same rate. Only B names the receiver (the Mission Computer).',
    ai: { mode: 'draft', proposal: 'The Flight Control Subsystem shall transmit a heartbeat message to the Mission Computer every 1 second.', verdict: '', conf: 0, votes: '', why: 'The AI drafted one wording that names the receiver. New wording means all four lenses must sign.', quotes: [] },
    aiDraft: 'The Flight Control Subsystem shall transmit a heartbeat message to the Mission Computer every 1 second.',
    guards: 'pppppppwpp', gNotes: { 7: 'Receiver "Mission Computer" appears in B only; A and C do not name one' },
    actions: [['merge', 'Merge into one'], ['reject', 'Not a duplicate']]
  },
  {
    id: 'CL-050', lane: 'B', rel: 'VARIANT', kind: 'varV', title: 'Fault event retention: six wordings', famKey: 'ret', param: 'Fault event retention', dir: 'higher', unit: 'days', alloc: 'Data Recorder',
    members: [
      mem('REQ-SYS-0412', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall retain fault events for at least 30 days.', { v: 30 }),
      mem('REQ-SYS-0418', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall store fault events for a minimum of 60 days.', { v: 60 }),
      mem('REQ-GCS-0233', 'Ground team', 'Data Recorder', 'Test', 'Pre-baseline', 'Fault events shall be kept by the Data Recorder for 90 days or longer.', { v: 90 }),
      mem('REQ-SYS-0431', 'Safety team', 'Data Recorder', 'Analysis', 'Pre-baseline', 'The Data Recorder shall retain fault events for at least 365 days.', { v: 365 }),
      mem('REQ-SYS-0447', 'Data team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall retain fault events for at least 30 days after landing.', { v: 30, cond: 'after landing', rankable: false }),
      mem('REQ-MSN-0129', 'Mission team', 'Data Recorder', 'Inspection', 'Pre-baseline', 'The Data Recorder shall retain fault events until the next maintenance cycle.', { v: null, cond: 'until the next maintenance cycle', rankable: false })
    ],
    m: { fuzzy: 0.84, tfidf: 0.77, embed: 0.95, cross: 0.88, eAB: 0.78, eBA: 0.74, contra: 0.05, p: 0.62 },
    mNote: 'Four members are the same requirement with different minimums. Two cannot be ranked: one adds a condition, one has no number.',
    ai: { mode: 'judge', proposal: '', verdict: 'VARIANT', conf: 84, votes: '3 of 3 runs agree', why: 'Same function with four different minimum retention periods, and three owners. Two members use a different condition or no number, so they cannot be compared with the rest.', quotes: [['M1', 'at least 30 days'], ['M4', 'at least 365 days']], action: 'Ask the owners which period applies; keep the two non-rankable members separate.' },
    aiDraft: 'The Data Recorder shall retain fault events for at least 365 days.',
    guards: 'ppfpppwppp', gNotes: { 2: '30, 60, 90 and 365 days all appear', 6: 'Two members carry a different condition or no number' },
    actions: [['merge', 'Merge into one'], ['link', 'Keep separate and link'], ['escalate', 'Ask the owners'], ['reject', 'Reject suggestion']]
  }
];
const HAND_IDS = HAND.reduce((a, c) => a.concat(c.members.map((m) => m.id)), []);
