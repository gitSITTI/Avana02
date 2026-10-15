"""Mutation run for the prototype: The gold set: the estimator (weights, ranges, recall), what a pair counts as, the queue, blind labelling.

Usage: python3 tools/mutation/gold.py [part of a name ...]     (--list shows the names). See README.md in this folder."""
import sys
from common import main

G='parts/gold.js'; C4='parts/c4.js'
muts = [
 ('weights use the sample size, not the group size', G, "return s + c.N * (side === 'mid'", "return s + c.n * (side === 'mid'"),
 ('recall ignores the pairs the method did not flag', G, "const fn = sum(0, 'mid'), fnLo = sum(0, 'lo'), fnHi = sum(0, 'hi');", "const fn = 0, fnLo = 0, fnHi = 0;"),
 ('no range, the best guess is the range', G, "res.pLo = lo / flagged; res.pHi = Math.min(1, hi / flagged);", "res.pLo = tp / flagged; res.pHi = tp / flagged;"),
 ('plain normal range instead of Wilson', G, "return [Math.max(0, (c - w) / d), Math.min(1, (c + w) / d)];", "{ const s = z * Math.sqrt(p * (1 - p) / n); return [Math.max(0, p - s), Math.min(1, p + s)]; }"),
 ('near misses folded into the unrelated group', G, "B2: nSame - ex.length };", "B2: nSame - sA.length };"),
 ('cannot tell counted as a vote', G, "const conc = who.map((w) => L[w].v).filter((v) => v !== 'unsure');", "const conc = who.map((w) => L[w].v);"),
 ('related against not related counts as related', G, "u.every((v) => !GOLD_BY[v].rel) ? 'none' : null;", "u.every((v) => !GOLD_BY[v].rel) ? 'none' : 'rel';"),
 ('the lead’s settled label is ignored', G, "if (adj) return {", "if (false) return {"),
 ('no pair is ever sent to a second person', G, "GOLD_DOUBLE === 0 ? 2 : 1", "GOLD_DOUBLE === 0 ? 1 : 1"),
 ('a labelled pair is offered again', G, "    if (L[who]) return;\n", "    if (false) return;\n"),
 ('sample labels no longer say they are samples', G, "out[it.key] = { priya: { v, note: '', sample: true } };", "out[it.key] = { priya: { v, note: '' } };"),
 ('kappa is plain agreement', G, "const kappa = pe >= 1 ? null : (ag / n - pe) / (1 - pe);", "const kappa = ag / n;"),
 ('best case reported as the precision', G, "res.p = tp / flagged; res.pLo", "res.p = hi / flagged; res.pLo"),
 ('the cluster is shown on the labelling card', C4, "gWho: act ? 'Labelling as ' + P.name : 'Not labelling',", "gWho: (act ? 'Labelling as ' + P.name : 'Not labelling') + (it && it.a.cid ? ' ' + it.a.cid : ''),"),
 ('an observer can label', C4, "act = this.canAct(S);", "act = true;"),
]

EQUIVALENT = {}

if __name__ == '__main__':
    sys.exit(main(muts, EQUIVALENT))
