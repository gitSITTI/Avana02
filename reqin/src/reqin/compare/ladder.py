"""The similarity ladder: four increasingly loose comparisons of two wordings, kept as *features* so a person can see why a pair was suggested. None of them decides a type.

1. exact:     the same words, ignoring case, spacing and punctuation
2. masked:    the same words once every number-with-unit is replaced by a placeholder (so '5 s' and '50 s' are a match here and the rules then catch the difference), plus a fuzzy ratio
3. overlap:   the share of words two wordings have in common, each word weighted by how rare it is in this dataset (a shared rare word counts for more than 'system')
4. canonical: the same share after the vocabulary, so that 'msg' and 'message' count as one word

Standard library only (difflib for the fuzzy ratio).
"""
from __future__ import annotations

import math
from collections import Counter
from difflib import SequenceMatcher
from typing import Iterable

from .slots import Slots


def idf_table(docs: Iterable[Iterable[str]]) -> tuple[dict[str, float], float]:
    """Weight of each token: ln(1 + N/df). Returns the table and the weight for a token the table has not seen."""
    df: Counter[str] = Counter()
    n = 0
    for d in docs:
        n += 1
        df.update(set(d))
    return ({t: math.log(1 + n / c) for t, c in df.items()}, math.log(1 + n))


def weighted_jaccard(a: frozenset[str] | set[str], b: frozenset[str] | set[str], idf: dict[str, float], default: float) -> float:
    if not a and not b:
        return 1.0
    inter = sum(idf.get(t, default) for t in a & b)
    union = sum(idf.get(t, default) for t in a | b)
    return inter / union if union else 0.0


# SequenceMatcher takes time in proportion to (words in A) x (words in B). Past this many cells the ratio is the share of words the two have in common instead (same scale, 0 to 1, a little more
# generous because it ignores order). It is a feature shown to a person, never what decides a type.
_MAX_CELLS = 250_000


def _ratio(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    if len(a) * len(b) <= _MAX_CELLS:
        return SequenceMatcher(None, a, b, autojunk=False).ratio()
    common = sum((Counter(a) & Counter(b)).values())
    return 2.0 * common / (len(a) + len(b)) if a or b else 1.0


def features(a: Slots, b: Slots, idf_raw: dict[str, float], idf_raw_default: float, idf_canon: dict[str, float], idf_canon_default: float) -> dict[str, object]:
    exact = a.exact == b.exact
    masked_equal = a.masked == b.masked
    ratio = 1.0 if masked_equal else _ratio(a.masked, b.masked)
    return {
        "exact": exact,
        "masked_equal": masked_equal,
        "masked_ratio": round(ratio, 4),
        "overlap": round(weighted_jaccard(a.raw_tokens, b.raw_tokens, idf_raw, idf_raw_default), 4),
        "canonical_overlap": round(weighted_jaccard(a.canon_tokens(), b.canon_tokens(), idf_canon, idf_canon_default), 4),
    }


def rung(f: dict[str, object]) -> str:
    """The strictest comparison at which the two matched."""
    if f["exact"]:
        return "exact"
    if f["masked_equal"]:
        return "masked"
    if f["canonical_overlap"] == 1.0:
        return "canonical"
    return "overlap"
