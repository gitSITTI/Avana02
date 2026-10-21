"""The two comparison docs must say what the code does: the rules table in docs/COMPARE_FORMAT.md is generated from `RULES`, and docs/COMPARE_RESULTS.md is generated from a run of the
engine. `tools/make_compare_docs.py` writes both; these tests fail when either file was edited by hand or the engine changed without the files being regenerated.

They live here and not in reqin/tests because they read docs/, which the reqin container image does not copy."""
from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "tools" / "make_compare_docs.py"
FORMAT_MD = REPO / "docs" / "COMPARE_FORMAT.md"
RESULTS_MD = REPO / "docs" / "COMPARE_RESULTS.md"
# a rule that existed once, was found never to fire, and is named in the results page for that reason only
REMOVED_RULES = {"Q-OVERLAP"}


@pytest.fixture(scope="module")
def gen():
    spec = importlib.util.spec_from_file_location("make_compare_docs", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_both_docs_are_what_the_generator_writes_now():
    r = subprocess.run([sys.executable, str(SCRIPT), "--check"], capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_staleness_check_can_fail(gen, tmp_path, monkeypatch, capsys):
    """Change one number in a copy of each file and the check must say it is out of date; otherwise it proves nothing."""
    f, r = tmp_path / "F.md", tmp_path / "R.md"
    f.write_text(FORMAT_MD.read_text(encoding="utf-8"), encoding="utf-8")
    r.write_text(RESULTS_MD.read_text(encoding="utf-8").replace("precision", "Precision", 1), encoding="utf-8")
    monkeypatch.setattr(gen, "FORMAT_MD", f)
    monkeypatch.setattr(gen, "RESULTS_MD", r)
    assert gen.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "R.md" in out and "F.md" not in out, out          # it names the file that is stale, and only that one
    r.write_text(RESULTS_MD.read_text(encoding="utf-8"), encoding="utf-8")
    f.write_text(FORMAT_MD.read_text(encoding="utf-8").replace("| `EQ-DIGEST` |", "| `EQ-DIGEST!` |", 1), encoding="utf-8")
    assert gen.main(["--check"]) == 1
    out = capsys.readouterr().out
    assert "F.md" in out and "R.md" not in out, out


def test_every_rule_says_where_it_came_from_and_nothing_else_does(gen):
    from reqin.compare import RULES
    assert set(gen.SOURCE) == set(RULES), f"rules without a source line: {sorted(set(RULES) - set(gen.SOURCE))}; source lines for rules that do not exist: {sorted(set(gen.SOURCE) - set(RULES))}"
    assert {v[0] for v in gen.SOURCE.values()} <= {"research", "adapted", "made up"}
    assert {m[1] for m in gen.MACHINERY} <= {"research", "adapted", "made up"}


def test_every_rule_named_in_the_docs_exists(gen):
    from reqin.compare import RULES
    named = set()
    for p in (FORMAT_MD, RESULTS_MD):
        named |= set(re.findall(r"`([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)`", p.read_text(encoding="utf-8")))
    unknown = named - set(RULES) - REMOVED_RULES
    assert not unknown, f"the docs name rules that do not exist: {sorted(unknown)}"
    for rid in REMOVED_RULES:
        assert rid not in RULES
        assert rid not in FORMAT_MD.read_text(encoding="utf-8"), f"{rid} was removed from the engine and must not be in the format doc"


def test_every_disagreement_in_the_labelled_sets_has_a_cause_that_exists(gen):
    """The results page explains each pair the engine disagreed with. A cause for a pair that no longer disagrees, or a cause with no text, would mislead."""
    import compare_blind as cb
    held = cb.score(cb.load("compare_blind_heldout.json"))
    seen = cb.score(cb.load("compare_blind_seen.json"))
    wrong_surface = {"held": {w["id"] for w in held["wrong"] if w["kind"] != "meaning"}, "seen": {w["id"] for w in seen["wrong"] if w["kind"] != "meaning"}}
    assert set(gen.HELDOUT_CAUSE) == wrong_surface["held"], "HELDOUT_CAUSE and the pairs the engine disagrees with differ"
    assert set(gen.SEEN_CAUSE) == wrong_surface["seen"], "SEEN_CAUSE and the pairs the engine disagrees with differ"
    for c in set(gen.HELDOUT_CAUSE.values()) | set(gen.SEEN_CAUSE.values()):
        assert c in gen.CAUSES, c
    for c in set(gen.HELDOUT_CAUSE.values()):
        if c != "needs-meaning":
            assert c in gen.GAP_LABEL, f"cause {c} has no line in 'Known gaps'"


def test_the_results_page_leads_with_what_it_does_not_show():
    text = RESULTS_MD.read_text(encoding="utf-8")
    head = text[: text.index("## 1.")]
    assert "never been run on a real requirements set" in head
    assert "language model" in head
    assert "## 8. Not checked" in text
