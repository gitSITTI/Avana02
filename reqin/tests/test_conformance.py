"""THE ADAPTER CONFORMANCE SUITE.

Every adapter, present or future, must pass the same checks on a fixture of its format. A new adapter is
'done' when it is added to CASES and this file is green. An AI agent writing an adapter uses this as its
definition of done.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from make_fixtures import COUNT, REQS
from reqin import Source, ingest, propose_profile, sniff_all
from reqin.adapter import load_adapters, pick_adapter
from reqin.normalise import normalise_text

Q = {"query": "SELECT req_uid, statement, rationale, verif, alloc, owner FROM reqs WHERE active=1"}
CASES = {
    #  key        adapter       expected requirements, expected rejected
    "csv":       ("tabular",    COUNT, 0),
    "xlsx":      ("tabular",    COUNT, 0),
    "doors_csv": ("tabular",    6,     2),     # 2 heading rows have no text: rejected WITH a reason, never dropped silently
    "reqif":     ("reqif",      COUNT, 0),
    "sysml":     ("sysml_text", COUNT, 0),
    "sqlite":    ("sql",        COUNT, 0),
    "docx":      ("docx",       COUNT, 0),
    "pdf":       ("pdf",        COUNT, 0),
}


def src_for(key: str, fx: dict[str, Path]) -> Source:
    assert key in fx, f"fixture {key} was not built"   # never skip: a skipped format is a hole that looks like a pass
    return Source("sqlite:///" + str(fx[key]), Q) if key == "sqlite" else Source(str(fx[key]))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("key", CASES)
def test_sniff_picks_the_right_adapter(key, fx):
    ranked = sniff_all(src_for(key, fx))
    assert ranked and ranked[0][1] == CASES[key][0], ranked


@pytest.mark.parametrize("key", CASES)
def test_discover_describes_content(key, fx):
    src = src_for(key, fx)
    disc = pick_adapter(src).discover(src)
    assert disc.containers and all(c.fields for c in disc.containers)
    assert any(f.samples for c in disc.containers for f in c.fields)


@pytest.mark.parametrize("key", CASES)
def test_counts_and_no_silent_drops(key, fx):
    _, want_ok, want_rej = CASES[key]
    r = ingest(src_for(key, fx))
    assert r.report["invariant_ok"], r.report            # raw == requirements + rejected + filtered
    assert len(r.requirements) == want_ok, r.report
    assert len(r.rejected) == want_rej
    assert all(x.reason for x in r.rejected)


@pytest.mark.parametrize("key", CASES)
def test_statement_text_is_verbatim_after_normalisation(key, fx):
    r = ingest(src_for(key, fx))
    gold = {x[0]: normalise_text(x[1]) for x in REQS}
    by_uid = {q.uid: q for q in r.requirements if not q.uid_synthetic}
    assert by_uid, "no requirement kept a real UID"
    for uid, q in by_uid.items():
        assert q.norm_text == gold[uid], (uid, q.norm_text)


@pytest.mark.parametrize("key", CASES)
def test_identity_and_provenance(key, fx):
    r = ingest(src_for(key, fx))
    assert len({q.mid for q in r.requirements}) == len(r.requirements), "MID collision"
    for q in r.requirements:
        assert q.ref.locator and q.ref.adapter and q.text.strip()
        assert q.fidelity.value in ("structured", "tabular", "parsed", "extracted")
        assert "text" in q.conf and "uid" in q.conf


@pytest.mark.parametrize("key", CASES)
def test_deterministic(key, fx):
    a, b = ingest(src_for(key, fx)), ingest(src_for(key, fx))
    assert [(q.mid, q.fingerprint) for q in a.requirements] == [(q.mid, q.fingerprint) for q in b.requirements]


@pytest.mark.parametrize("key", CASES)
def test_source_is_never_modified(key, fx):
    p = fx[key]
    before = sha(p)
    ingest(src_for(key, fx))
    assert sha(p) == before


@pytest.mark.parametrize("key", CASES)
def test_nothing_in_the_source_is_lost(key, fx):
    """Every non-empty raw field is either claimed by the profile or preserved in `extra`."""
    src = src_for(key, fx)
    ad = pick_adapter(src)
    prof = propose_profile(ad.discover(src), ad.name)
    claimed = {k for r in prof.fields.values() for k in r.src + r.join}
    r = ingest(src)
    by_loc = {(q.ref.container, q.ref.locator): q for q in r.requirements}
    checked = 0
    for raw in ad.read(src):
        q = by_loc.get((getattr(raw, "ref").container, getattr(raw, "ref").locator))
        if q is None or not hasattr(raw, "fields"):
            continue
        for k, v in raw.fields.items():
            if str(v).strip():
                assert k in claimed or k in q.extra, (key, q.uid, k)
        checked += 1
    assert checked == len(r.requirements)


def test_every_registered_adapter_has_a_case_or_is_declared_unimplemented():
    for name, cls in load_adapters().items():
        covered = name in {c[0] for c in CASES.values()}
        live = cls.maturity == "fake-server-tested" or not cls.__module__.startswith("reqin.adapters.")   # live + plugins: their own tests
        assert covered or getattr(cls, "implemented", True) is False or live, f"adapter {name} has no conformance case"
