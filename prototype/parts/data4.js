
/* ---------- sample scores for the Methods and metrics page ----------
   There is no gold set of human-labelled pairs yet, so EVERY number in this file is a made-up placeholder that shows the layout and the
   questions the page will answer once real labels exist. Nothing here is measured. The page says so.
   CAT_SCORES rows: [category key (a cluster's famKey), name, gold pairs, then [precision, recall] for four ways of working:
   mechanical only, mechanical then AI, AI then mechanical, AI only]. */
const CAT_SCORES = [
  ['resp', 'Response time', 142, [0.92, 0.88], [0.94, 0.88], [0.91, 0.90], [0.86, 0.89]],
  ['hb', 'Heartbeat interval', 118, [0.93, 0.89], [0.95, 0.89], [0.92, 0.91], [0.88, 0.90]],
  ['boot', 'Start-up time', 96, [0.90, 0.86], [0.93, 0.86], [0.90, 0.88], [0.84, 0.87]],
  ['ret', 'Data retention', 131, [0.91, 0.85], [0.94, 0.86], [0.90, 0.88], [0.85, 0.88]],
  ['rate', 'Update rate', 109, [0.92, 0.87], [0.94, 0.87], [0.91, 0.89], [0.86, 0.88]],
  ['avail', 'Availability', 74, [0.89, 0.82], [0.92, 0.83], [0.86, 0.85], [0.78, 0.86]],
  ['mass', 'Mass limit', 158, [0.95, 0.90], [0.96, 0.90], [0.94, 0.91], [0.90, 0.91]],
  ['acc', 'Position accuracy', 88, [0.91, 0.84], [0.92, 0.84], [0.89, 0.86], [0.82, 0.87]],
  ['temp', 'Operating temperature', 103, [0.90, 0.85], [0.92, 0.85], [0.88, 0.88], [0.83, 0.88]],
  ['cap', 'Storage capacity', 117, [0.92, 0.86], [0.94, 0.87], [0.91, 0.88], [0.86, 0.88]],
  ['modal', 'Shall or should', 64, [0.74, 0.66], [0.88, 0.72], [0.84, 0.78], [0.80, 0.80]],
  ['clauses', 'One contains the other', 79, [0.68, 0.52], [0.81, 0.74], [0.78, 0.76], [0.72, 0.80]],
  ['cond', 'Different conditions', 58, [0.70, 0.60], [0.84, 0.72], [0.79, 0.74], [0.73, 0.77]],
  ['neg', 'Required or prohibited', 41, [0.88, 0.70], [0.90, 0.80], [0.80, 0.84], [0.66, 0.85]],
  ['bus', 'Conflicting values', 49, [0.90, 0.84], [0.90, 0.84], [0.81, 0.86], [0.70, 0.84]]
];
const ARM_KEYS = ['mech', 'after', 'before', 'ai'];
const ARM_COL = { mech: 3, after: 4, before: 5, ai: 6 };
const ARM_INFO = {
  mech: { name: 'Mechanical only', sub: 'Text, keyword and meaning scores, combined. No AI.', mark: 'mech' },
  after: { name: 'Mechanical, then AI', sub: 'The AI re-reads only what the mechanical steps flagged.', mark: 'ai' },
  before: { name: 'AI, then mechanical', sub: 'The AI proposes pairs first; the mechanical steps check them.', mark: 'ai' },
  ai: { name: 'AI only', sub: 'No mechanical steps. Shown for comparison; the app does not work this way.', mark: 'ai' }
};
/* effort and cost are sample figures too: reviewer minutes per cluster, AI calls (three runs per item), AI compute minutes on the local model */
const ARM_OPS = { mech: { mins: 4.6, calls: 0, aiMin: 0 }, after: { mins: 3.9, calls: 663, aiMin: 22 }, before: { mins: 4.4, calls: 11712, aiMin: 410 }, ai: { mins: 5.3, calls: 11712, aiMin: 410 } };
/* the mechanical methods one at a time: [name, precision, recall, [precision, recall] with AI after, [precision, recall] with AI before, pairs scored]
   The last row is the combined score, which is the "Mechanical only" way of working above (its numbers are taken from the table of categories). */
const LADDER = [
  ['Text match (fuzzy)', 0.61, 0.48, [0.79, 0.49], [0.66, 0.61], 3904],
  ['Keyword overlap (TF-IDF)', 0.58, 0.52, [0.77, 0.53], [0.64, 0.63], 3904],
  ['Embedding model A', 0.71, 0.84, [0.86, 0.84], [0.74, 0.86], 1126],
  ['Embedding model B', 0.69, 0.81, [0.85, 0.81], [0.72, 0.84], 1126],
  ['Cross-encoder re-score', 0.78, 0.76, [0.88, 0.76], [0.80, 0.80], 1126]
];
