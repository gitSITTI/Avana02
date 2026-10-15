"""Mutation run for the prototype: the engineering V (the counts of requirements, traced and gaps, and what a decision does to each level).

Usage: python3 tools/mutation/vee.py [part of a name ...]     (--list shows the names). See README.md in this folder."""
import sys
from common import main

L3='parts/logic3.js'
muts = [
 ('stale decisions counted by the V', L3, "(x.dec && COUNTED.indexOf(x.st) >= 0 ? x.dec : null)", "(x.dec || null)"),
 ('superseded not counted as removed', L3, "l.after = l.reqs - l.mergedAway - l.superseded - l.dropped + l.added;", "l.after = l.reqs - l.mergedAway - l.dropped + l.added;"),
 ('dropped not counted as removed', L3, "l.after = l.reqs - l.mergedAway - l.superseded - l.dropped + l.added;", "l.after = l.reqs - l.mergedAway - l.superseded + l.added;"),
 ('new wording not added', L3, "if (d.newWording) L[c.lvls[0] - 1].added++;", ""),
 ('items lost when merged', L3, "lv.repoint += v.vi;", "lv.repoint += Math.min(v.vi, 1);"),
 ('items counted from the survivor too', L3, "if (kind !== 'merged' && kind !== 'superseded') return;", "if (kind !== 'merged' && kind !== 'superseded' && kind !== 'keep') return;"),
 ('level assigned past 4', L3, "return x < 4 ? 1 : x < 38 ? 2 : x < 88 ? 3 : 4; }", "return x < 4 ? 1 : x < 38 ? 2 : x < 88 ? 3 : 5; }"),
 ('traced counts items only', L3, "if (v.vm && v.vi > 0) l.traced++; else l.gaps++;", "if (v.vi > 0) l.traced++; else l.gaps++;"),
 ('method none not counted', L3, "l.reqs++; l.items += v.vi; l.methods[v.vm || 'none']++;", "l.reqs++; l.items += v.vi; if (v.vm) l.methods[v.vm]++;"),
 ('level shift ignored vs repoint', L3, "if (keep && keep.lvl !== v.lvl) lv.levelShift += v.vi;", "if (keep) lv.levelShift += v.vi + 1;"),
]

EQUIVALENT = {}

if __name__ == '__main__':
    sys.exit(main(muts, EQUIVALENT, width=40, what_counts=lambda l: l.startswith(' - V:') or 'THROW' in l))
