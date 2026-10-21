"""docs/gateway_cases.json: the language-neutral test vectors for the gateway's decision core (docs/GATEWAY_SPEC.md).

Two jobs. First, the committed file must be what tools/make_gateway_cases.py writes, and the reference implementation must give every answer in it: that keeps the file honest.
Second, the parts that are easy to get wrong in another language (what a word is, what a fingerprint is) are worked out again here by a different route, so a vector is not
simply the reference implementation agreeing with itself.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

from reqin.aigate import Sheet
from reqin.gateway.audit import verify_log
from reqin.gateway.core import ID_RE, WORDS, Markings, decide, fingerprints, prompt_text, route_mismatch, sheet_from_doc, words

REPO = Path(__file__).resolve().parents[2]
CASES = REPO / "docs" / "gateway_cases.json"
pytestmark = pytest.mark.skipif(not CASES.exists(), reason="docs/gateway_cases.json is not here (a test stage that copies only reqin/)")


@pytest.fixture(scope="module")
def cases() -> dict:
    return json.loads(CASES.read_text(encoding="utf-8"))


def test_the_committed_file_is_what_the_generator_writes():
    gen = REPO / "tools" / "make_gateway_cases.py"
    if not gen.exists():
        pytest.skip("tools/ is not here")
    r = subprocess.run([sys.executable, str(gen), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_word_vector(cases):
    for c in cases["words"]:
        assert words(c["text"]) == c["words"], c["text"]


def test_words_worked_out_another_way_agree(cases):
    """A word is a run of letters and digits (Unicode categories L and N) after NFKC and full lower-casing. This uses findall, where the reference splits."""
    for c in cases["words"]:
        assert re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", c["text"]).lower()) == c["words"], c["text"]
    for c in cases["words"]:
        for w in c["words"]:
            assert all(unicodedata.category(ch)[0] in "LN" for ch in w), (c["text"], w)


def test_fingerprints_worked_out_another_way_agree(cases):
    for c in cases["fingerprints"]:
        w = re.findall(r"[^\W_]+", unicodedata.normalize("NFKC", c["text"]).lower())
        runs = [] if len(w) < 4 else [w] if len(w) <= 6 else [w[i:i + 6] for i in range(len(w) - 5)]
        want = sorted({hashlib.sha256(" ".join(r).encode("utf-8")).hexdigest()[:16] for r in runs})
        assert c["fp"] == want == fingerprints(c["text"]), c["text"]


@pytest.mark.skipif(not shutil.which("sha256sum"), reason="no sha256sum on this machine")
def test_a_fingerprint_agrees_with_the_systems_own_sha256sum(cases):
    c = next(x for x in cases["fingerprints"] if x["text"] == "one two three four")
    out = subprocess.run(["sha256sum"], input=b"one two three four", capture_output=True).stdout.decode()
    assert c["fp"] == [out[:16]]


def test_the_markings_file_in_the_cases_is_what_building_it_gives(cases):
    built = Markings.build((r["id"], r["marking"], r["text"]) for r in cases["requirements"])
    assert built == cases["markings_file"]
    assert built["format"] == cases["markings_format"] and built["window"] == 6


def test_every_undeclared_vector(cases):
    mk = Markings.from_file(cases["markings_file"])
    for c in cases["undeclared"]:
        assert mk.undeclared(c["prompt"], set(c["declared"]), c["min_windows"]) == c["expect"], c["name"]
    assert any(c["expect"] for c in cases["undeclared"]) and any(not c["expect"] for c in cases["undeclared"]), "the cases must reach both answers"


def test_every_route_vector(cases):
    for c in cases["route_mismatch"]:
        assert [m.split(":")[0] for m in route_mismatch(Sheet(**c["sheet"]), c["route"])] == c["expect"], c["name"]


def test_every_sheet_vector(cases):
    for c in cases["sheet_from_doc"]:
        got = sheet_from_doc(c["doc"])
        if c["expect"] is None:
            assert got is None, c["name"]
        else:
            assert got is not None and {"sheet": dict(got[0].__dict__), "on": got[1]} == c["expect"], c["name"]


def test_every_prompt_text_vector(cases):
    for c in cases["prompt_text"]:
        if c["expect"] is None:
            with pytest.raises(ValueError):
                prompt_text(c["body"])
        else:
            assert prompt_text(c["body"]) == c["expect"], c.get("name", c["body"])


def test_every_header_vector(cases):
    for c in cases["requirement_headers"]:
        ids: list[str] = []
        for x in c["header"].split(","):
            x = x.strip()
            if x and x not in ids:
                ids.append(x)
        assert ids == c["ids"] and [x for x in ids if not ID_RE.fullmatch(x)] == c["bad"], c["header"][:40]


def test_every_markings_file_vector(cases):
    for c in cases["markings_file_errors"]:
        try:
            Markings.from_file(c["file"])
            ok = True
        except ValueError:
            ok = False
        assert ok == c["ok"], c["name"]
    assert any(c["ok"] for c in cases["markings_file_errors"]) and any(not c["ok"] for c in cases["markings_file_errors"])


def test_every_decision_vector_and_every_code_is_covered(cases):
    mk = Markings.from_file(cases["decide_markings"])
    seen = set()
    for c in cases["decide"]:
        kw = {k: v for k, v in c.items() if k not in ("name", "expect")}
        v = decide(**kw, markings=mk)
        got = {"ok": v.ok, "status": v.status, "code": v.code, "level": v.level, "detail": [d.split(":")[0] for d in v.detail] if v.code == "sheet_mismatch" else v.detail}
        assert got == c["expect"], c["name"]
        seen.add(v.code)
    every = set(WORDS) | {"open", "no_requirements", "too_many", "unknown_requirement"}
    assert seen == every, f"codes with no vector: {sorted(every - seen)}; vectors for codes that do not exist: {sorted(seen - every)}"


def test_the_decisions_come_in_the_documented_order(cases):
    """The first 'no' wins: each vector that stacks two reasons must answer with the earlier one."""
    by = {c["name"]: c["expect"]["code"] for c in cases["decide"]}
    assert by["an observer is refused before anything else"] == "observer"
    assert by["unknown id wins over the switch being off"] == "unknown_requirement"
    assert by["no AI document wins over a bad sheet"] == "no_sheet"
    assert by["the marking rules win over the route"] == "marking"
    assert by["the route wins over an undeclared requirement"] == "sheet_mismatch"


def test_the_audit_chain_vectors_are_what_the_rule_says(cases):
    prev = cases["audit_genesis"]
    assert prev == "0" * 64
    for i, c in enumerate(cases["audit_chain"], 1):
        row = dict(c["row"])
        assert row["seq"] == i and row["prev"] == prev and set(row) == set(cases["audit_fields"])
        body = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert c["preimage"] == prev + "|" + body
        assert c["hash"] == hashlib.sha256(c["preimage"].encode("utf-8")).hexdigest()
        assert json.loads(c["line"]) == {**row, "hash": c["hash"]}
        prev = c["hash"]


def test_every_log_verification_vector(cases, tmp_path):
    for c in cases["verify_log"]:
        p = tmp_path / "log.jsonl"
        p.write_text("".join(x + "\n" for x in c["lines"]), encoding="utf-8")
        res = verify_log(p)
        got = {"ok": True, "entries": res["entries"], "head": res["head"]} if res["ok"] else {"ok": False, "at": res["at"]}
        assert got == c["expect"], c["name"]
    assert any(c["expect"]["ok"] for c in cases["verify_log"]) and any(not c["expect"]["ok"] for c in cases["verify_log"])


def test_the_cases_hold_no_text_that_looks_real(cases):
    text = json.dumps(cases, ensure_ascii=False).lower()
    for word in ("password", "secret key", "api_key", "bearer "):
        assert word not in text
