"""Proof of the point of all this: code written against the canonical model works on ANY source, and across sources."""
from __future__ import annotations

import re

from reqin import Source, ingest
from reqin.model import Requirement

from test_conformance import CASES, src_for


def slot_key(q: Requirement) -> tuple:
    s = q.slots
    return (s.modal in ("shall", "must"), s.negated, tuple((x["dimension"] or x["unit"], x["comparator"], round(x["base_value"] if x["base_value"] is not None else x["value"], 6)) for x in s.quantities))


def jaccard(a: str, b: str) -> float:
    A, B = set(re.findall(r"\w+", a.lower())), set(re.findall(r"\w+", b.lower()))
    return len(A & B) / len(A | B) if A | B else 0.0


def near_duplicates(reqs: list[Requirement], thr: float = 0.7) -> set[frozenset[str]]:
    """A deliberately tiny stand-in for the real comparison stage. It sees ONLY the canonical model."""
    out = set()
    for i, a in enumerate(reqs):
        for b in reqs[i + 1:]:
            if a.uid != b.uid and slot_key(a) == slot_key(b) and jaccard(a.norm_text, b.norm_text) >= thr:
                out.add(frozenset((a.uid, b.uid)))
    return out


def test_same_downstream_code_finds_the_same_pair_in_every_format(fx):
    target = frozenset(("REQ-FCS-0101", "REQ-FCS-0102"))      # 200 ms vs 0.2 seconds
    for key in CASES:
        res = ingest(src_for(key, fx))
        pairs = near_duplicates(res.requirements)
        assert target in pairs, (key, pairs)


def test_pairs_are_also_found_across_two_different_sources(fx):
    a = ingest(src_for("csv", fx)).requirements
    b = ingest(src_for("reqif", fx)).requirements
    renamed = [r for r in b]
    for r in renamed:
        r.uid = "RQ:" + r.uid                                # pretend the second system numbers things differently
    pairs = near_duplicates(a + renamed)
    assert frozenset(("REQ-FCS-0101", "RQ:REQ-FCS-0101")) in pairs      # identical statement in two systems
    assert frozenset(("REQ-FCS-0101", "RQ:REQ-FCS-0102")) in pairs      # same obligation, different unit, other system
