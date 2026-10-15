"""Mutation run for the prototype: how the gold set counts and draws pairs (the indexes that find pairs that read alike, the exact counts, the sample drawn from a group).

The counting is fast because it skips most pairs without looking at them; each mutant here breaks one of the shortcuts. verify.js compares the counts with a count of
every pair in several hundred random and boundary-case sets of requirements, so each broken shortcut should be noticed.

Usage: python3 tools/mutation/population.py [part of a name ...]     (--list shows the names). See README.md in this folder."""
import sys
from common import main

G = 'parts/gold.js'
muts = [
 ("prefix one word short", G, "const pre = len - Math.ceil(GOLD_BAND * len - 1e-9) + 1;", "const pre = len - Math.ceil(GOLD_BAND * len - 1e-9);"),
 ("length test too strict", G, "if (Math.min(len, lo) < GOLD_BAND * Math.max(len, lo) - 1e-9) continue;", "if (Math.min(len, lo) < GOLD_BAND * Math.max(len, lo) + 0.5) continue;"),
 ("keywords skipped too eagerly", G, "const M = goldModel(), s = L.length, th = GOLD_BAND - 1e-9,", "const M = goldModel(), s = L.length, th = GOLD_BAND + 0.2,"),
 ("shared-word test one too many", G, "const need = Math.ceil(GOLD_BAND * Math.max(n, m) - 1e-9);", "const need = Math.ceil(GOLD_BAND * Math.max(n, m) - 1e-9) + 1;"),
 ("shared-word test counts once", G, "if (A[x] === B[y]) { same++; x++; y++; if (same >= need) return true; }", "if (A[x] === B[y]) { same++; x++; if (same >= need) return true; }"),
 ("end trim off by one", G, "while (n > 0 && m > 0 && A[a0 + n - 1] === B[b0 + m - 1]) { n--; m--; }", "while (n > 0 && m > 0 && A[a0 + n - 1] === B[b0 + m - 2]) { n--; m--; }"),
 ("start trim ignores the end", G, "if (!n || !m) return 1 - (n + m) / top;", "if (!n || !m) return 1 - Math.max(n, m) / top;"),
 ("left-out count off", G, "if (ex[mid] - mid <= p) lo = mid + 1;", "if (ex[mid] - mid < p) lo = mid + 1;"),
 ("cluster pairs counted as reading alike", G, "if (sameCl(L[px], L[py])) continue;", "if (false) continue;"),
 ("copies of one text not paired", G, "if (g.length > 1) both(", "if (g.length > 2) both("),
 ("pair place off by one", G, "const rank = (a, x, y) => base[a] + start(als[a].length, x) + (y - x - 1);", "const rank = (a, x, y) => base[a] + start(als[a].length, x) + (y - x);"),
 ("draw forgets the swap", G, "moved.set(t, vj); moved.set(j, vt);", "moved.set(t, vj);"),
 ("draw can repeat a pair", G, "const j = t + Math.floor(R() * (size - t)), vt = at(t), vj = at(j);", "const j = Math.floor(R() * size), vt = at(t), vj = at(j);"),
 ("keyword index misses the earlier one", G, "for (; q < f.length; q++) { let lst = post.get(f[q][0]);", "for (q++; q < f.length; q++) { let lst = post.get(f[q][0]);"),
 ("text index skips the rarest word", G, "for (let q = 0; q < pre; q++) { let lst = post.get(e[q]); if (!lst) post.set(e[q], lst = []); lst.push(p); }", "for (let q = 1; q < pre; q++) { let lst = post.get(e[q]); if (!lst) post.set(e[q], lst = []); lst.push(p); }"),
 ("repeated words counted as one", G, "e[q] = ids[q] + o * V;", "e[q] = ids[q];"),
 ("blank wordings not paired", G, "if (!len) { blank.forEach((q) => emit(q, p)); blank.push(p); continue; }", "if (!len) { blank.push(p); continue; }"),
]

EQUIVALENT = {
    'shared-word test counts once': 'it only lets more pairs through a cheap pre-check; every pair still gets its exact score, so the answers are the same',
    'start trim ignores the end': 'when one side is empty n + m and max(n, m) are the same number',
    'repeated words counted as one': 'numbering repeated words only makes the filter tighter; without it the filter stays complete and the counts are identical (also at 24,960 requirements)',
}

if __name__ == '__main__':
    sys.exit(main(muts, EQUIVALENT, width=45))
