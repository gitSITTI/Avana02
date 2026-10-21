"""The AI gate rules, checked against the table the prototype page is checked against (docs/ai_gate_cases.json)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reqin.aigate import AiBlocked, Sheet, ensure, gate, group_level, marking_level

CASES = json.loads((Path(__file__).resolve().parents[2] / "docs" / "ai_gate_cases.json").read_text(encoding="utf-8"))


def sheet(d: dict, reviewed: bool = True) -> Sheet:
    return Sheet(model=d["model"], where=d["where"], leaves=d["leaves"], log=d["log"], days=d["days"], approved=d["approved"], unstated=d["unstated"],
                 reviewed_by="A. Lead" if reviewed else "", reviewed_at="1 Oct" if reviewed else "")


@pytest.mark.parametrize("text,level", CASES["marking_cases"])
def test_a_marking_means_what_the_table_says(text, level):
    assert marking_level(text) == level


@pytest.mark.parametrize("levels,policy,want", CASES["group_cases"])
def test_a_group_takes_its_most_restrictive_member(levels, policy, want):
    assert group_level(levels, policy) == want


@pytest.mark.parametrize("by,at,want", CASES["reviewed_cases"], ids=[f"{i}" for i in range(len(CASES["reviewed_cases"]))])
def test_reviewing_needs_both_a_name_and_a_date_that_are_not_blank(by, at, want):
    d = CASES["sheets"]["ours-none"]
    assert Sheet(model=d["model"], where=d["where"], leaves=d["leaves"], log=d["log"], days=d["days"], approved=d["approved"], unstated=d["unstated"], reviewed_by=by, reviewed_at=at).reviewed is want


@pytest.mark.parametrize("name,d,want", CASES["sheet_cases"], ids=[c[0] for c in CASES["sheet_cases"]])
def test_a_sheet_says_what_is_wrong_with_it(name, d, want):
    assert sheet(d).problems() == want


@pytest.mark.parametrize("c", CASES["gate_cases"], ids=[c["name"] for c in CASES["gate_cases"]])
def test_the_gate_decides_as_the_table_says(c):
    d = gate(sheet(CASES["sheets"][c["sheet"]], c["reviewed"]), c["on"], c["marks"])
    assert (d.open, d.code) == (c["open"], c["code"])
    if c["code"] == "sheet":
        assert d.detail == sheet(CASES["sheets"][c["sheet"]]).problems()


def test_ensure_stops_the_prompt_from_being_built():
    s = sheet(CASES["sheets"]["ours-none"])
    assert ensure(s, True, ["No marking"]).open
    with pytest.raises(AiBlocked) as e:
        ensure(s, True, ["CUI"])
    assert e.value.decision.code == "marking" and "marking" in str(e.value)
    with pytest.raises(AiBlocked):
        ensure(s, False, ["No marking"])


def test_the_table_covers_every_decision_code_and_every_sheet_problem():
    assert {c["code"] for c in CASES["gate_cases"]} == {"open", "off", "unreviewed", "sheet", "marking", "classified", "unknown", "unstated"}
    assert {p for c in CASES["sheet_cases"] for p in c[2]} == {"model", "values", "vendor_leaves", "leaves_marked", "log_marked", "exp_where", "days"}
    assert {c[1] for c in CASES["marking_cases"]} == {"none", "cui", "exp", "classified", "unknown", "unstated"}


def test_reviewing_needs_a_name_and_a_date():
    d = CASES["sheets"]["ours-none"]
    assert sheet(d).reviewed and not sheet(d, reviewed=False).reviewed
    assert not Sheet(**{**{k: d[k] for k in ("model", "where", "leaves", "log", "days", "approved", "unstated")}, "reviewed_by": "A. Lead"}).reviewed


def test_a_file_from_the_page_is_read_and_anything_else_is_refused():
    import json, pytest
    from reqin.aigate import load_use_file
    ok = {"format": "reqin-ai-use/1", "switch": "on", "sheet": {**CASES["sheets"]["ours-cui"], "reviewed_by": "A. Lead", "reviewed_at": "1 Oct", "entered_by": "M. Hale"}}
    sh, on = load_use_file(json.loads(json.dumps(ok)))
    assert on is True and sh.approved == "cui" and sh.reviewed and sh.entered_by == "M. Hale" and not sh.problems()
    assert load_use_file({**ok, "switch": "off"})[1] is False
    for bad in (None, [], {}, {**ok, "format": "reqin-ai-use/2"}, {**ok, "switch": "maybe"}, {**ok, "sheet": None}, {**ok, "sheet": {**ok["sheet"], "approved_everything": True}}):
        with pytest.raises(ValueError):
            load_use_file(bad)
    # a file whose sheet is odd is still read; the gate then refuses to open anything under it
    odd, on = load_use_file({**ok, "sheet": {**ok["sheet"], "where": "elsewhere"}})
    assert odd.problems() == ["values"] and not gate(odd, on, ["No marking"]).open
