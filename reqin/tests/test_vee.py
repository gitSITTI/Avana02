"""The engineering V of a dataset (reqin vee): levels from the parent tree or from a field, verification methods read from the field text,
verify links counted for the right end, and every number adding up. The rules are the ones written at the top of reqin/vee.py."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from reqin.cli import main as cli
from reqin.contract_datasets import SPECS, build_all
from reqin.dataset import load_dataset
from reqin.vee import METHODS, level_in, methods_in, render, vee_report

ROOT = Path(__file__).parent.parent


def req(mid, parent=None, verification=None, **extra):
    fields = {"verification": verification} if verification is not None else {}
    return {"mid": mid, "uid": mid, "parent_mid": parent, "fields": fields, "extra": extra}


def verify(source, target, kind="verify"):
    return {"source_uid": source or "OUT", "target_uid": target or "OUT", "kind": kind, "source_mid": source, "target_mid": target}


def ds(reqs, links=()):
    return {"requirements": list(reqs), "links": list(links), "rejected": [], "report": None}


def by_level(rep):
    return {r["level"]: r for r in rep["levels"]}


# ---------------------------------------------------------------------------------------------- reading the text
@pytest.mark.parametrize("text,expected", [
    ("Test", ["Test"]), ("test", ["Test"]), ("Testing", ["Test"]), ("Analysis", ["Analysis"]), ("analyse", ["Analysis"]), ("Analyze", ["Analysis"]),
    ("Inspection", ["Inspection"]), ("Demonstration", ["Demonstration"]), ("Demo", ["Demonstration"]),
    ("Test, Analysis", ["Test", "Analysis"]), ("Analysis / Test", ["Test", "Analysis"]), ("Test and Demonstration", ["Test", "Demonstration"]),
    ("T", ["Test"]), ("A", ["Analysis"]), ("I", ["Inspection"]), ("D", ["Demonstration"]), ("T, A", ["Test", "Analysis"]),
    ("TBD", ["other"]), ("by review board", ["other"]), ("N/A", ["other"]),
    ("", []), ("   ", []), (None, []),
])
def test_methods_are_read_from_the_text(text, expected):
    assert methods_in(text) == expected


def test_a_word_that_merely_contains_a_method_is_not_a_method():
    assert methods_in("contest") == ["other"]
    assert methods_in("detailed design") == ["other"]
    assert methods_in("latest") == ["other"]


@pytest.mark.parametrize("text,expected", [
    ("1", 1), ("2", 2), ("3", 3), ("4", 4), ("L1", 1), ("l4", 4), ("level 3", 3), ("Level2", 2), ("LVL 3", 3),
    ("Stakeholder need", 1), ("User needs", 1), ("System", 2), ("System requirement", 2), ("Subsystem", 3), ("sub-system", 3), ("Segment", 3),
    ("Component", 4), ("Unit", 4), ("Module", 4),
    ("5", None), ("0", None), ("level 9", None), ("", None), (None, None), ("misc", None),
])
def test_levels_are_read_from_the_text(text, expected):
    assert level_in(text) == expected


def test_subsystem_is_not_mistaken_for_system():
    assert level_in("Subsystem requirement") == 3 and level_in("System requirement") == 2


# ---------------------------------------------------------------------------------------------- levels from the tree
def tree():
    r = [req("a"), req("b", "a"), req("c", "a"), req("d", "b"), req("e", "b"), req("f", "d"), req("g", "f"), req("h", "g")]
    return r


def test_depth_gives_the_level_and_deep_chains_fold_into_level_four():
    rep = vee_report(ds(tree()))
    lv = by_level(rep)
    assert [lv[k]["requirements"] for k in (1, 2, 3, 4)] == [1, 2, 2, 3 ]       # a / b c / d e / f g h (g and h are deeper than 4)
    assert rep["total"]["folded_into_level_4"] == 2 and any("deeper than level 4" in n for n in rep["notes"])
    assert rep["hierarchy"] is True and rep["total"]["unplaced"] == 0


def test_with_no_parent_at_all_depth_places_nobody_and_says_what_to_do():
    rep = vee_report(ds([req("a"), req("b"), req("c")]))
    assert all(r["requirements"] == 0 for r in rep["levels"])
    assert rep["unplaced"]["requirements"] == 3 and rep["hierarchy"] is False
    assert any("--by field" in n for n in rep["notes"])


def test_a_parent_outside_the_import_does_not_break_depth():
    rep = vee_report(ds([req("a", "not-imported"), req("b", "a")]))
    assert by_level(rep)[1]["requirements"] + by_level(rep)[2]["requirements"] == 2


def test_a_loop_in_the_parent_links_does_not_hang_or_lose_anyone():
    rep = vee_report(ds([req("a", "b"), req("b", "a"), req("c", "a")]))
    assert sum(r["requirements"] for r in rep["levels"]) + rep["unplaced"]["requirements"] == 3


# ---------------------------------------------------------------------------------------------- levels from a field
def test_levels_from_a_field_any_spelling_and_the_rest_is_unplaced():
    reqs = [req("a", Level="Stakeholder"), req("b", Level="System"), req("c", Level="L3"), req("d", Level="4"), req("e", Level="weird"), req("f")]
    rep = vee_report(ds(reqs), by="field", level_field="level")
    assert [r["requirements"] for r in rep["levels"]] == [1, 1, 1, 1]
    assert rep["unplaced"]["requirements"] == 2 and any("could not be placed" in n for n in rep["notes"])


def test_the_field_is_found_in_the_canonical_fields_too_and_ignores_case():
    r = {"mid": "x", "uid": "x", "parent_mid": None, "fields": {"allocation": "Subsystem"}, "extra": {}}
    assert by_level(vee_report(ds([r]), by="field", level_field="ALLOCATION"))[3]["requirements"] == 1


def test_asking_for_a_field_without_naming_it_is_an_error():
    with pytest.raises(ValueError):
        vee_report(ds([req("a")]), by="field")
    with pytest.raises(ValueError):
        vee_report(ds([req("a")]), by="sideways")


# ---------------------------------------------------------------------------------------------- the right leg
def test_traced_needs_both_a_method_and_an_item():
    reqs = [req("both", None, "Test"), req("method only", None, "Test"), req("item only", None, None), req("neither", None, None)]
    links = [verify("TC-1", "both"), verify("TC-2", "item only")]
    rep = vee_report(ds(reqs, links), by="field", level_field="none")
    t = rep["total"]
    assert t["traced"] == 1 and t["gaps"] == 3 and t["items"] == 2
    row = rep["unplaced"]
    assert row["traced"] == 1 and row["gaps"] == 3


def test_a_verify_link_counts_for_its_target_and_for_the_source_only_when_the_target_is_outside():
    reqs = [req("a", None, "Test"), req("b", "a", "Test"), req("c", "a", "Test")]
    links = [verify("TC-1", "a"),                 # a test outside the import verifies a
             verify("b", None),                   # exported the other way round: b is verified by something outside
             verify("c", "a"),                    # both ends are requirements: counts for the target, a
             verify(None, None),                  # neither end is here: counts for no one
             verify("a", "b", kind="satisfy")]    # not a verify link at all
    rep = vee_report(ds(reqs, links))
    lv = by_level(rep)
    assert lv[1]["items"] == 2 and lv[2]["items"] == 1
    assert rep["total"]["items"] == 3 and rep["total"]["verify_links_counted_for_no_one"] == 1
    assert any("neither end" in n for n in rep["notes"])


def test_two_methods_in_one_field_count_under_each_and_the_requirement_counts_once():
    rep = vee_report(ds([req("a", None, "Test, Analysis", Level="1")], [verify("TC", "a")]), by="field", level_field="Level")
    row = by_level(rep)[1]
    assert row["methods"]["Test"] == 1 and row["methods"]["Analysis"] == 1 and row["with_method"] == 1 and row["traced"] == 1
    assert rep["total"]["with_more_than_one_method"] == 1


def test_text_that_is_not_a_method_is_other_and_still_counts_as_having_one():
    rep = vee_report(ds([req("a", None, "by review board", Level="1")], [verify("TC", "a")]), by="field", level_field="Level")
    row = by_level(rep)[1]
    assert row["methods"]["other"] == 1 and row["no_method"] == 0 and row["traced"] == 1


# ---------------------------------------------------------------------------------------------- everything adds up
def check_adds_up(rep, n_reqs):
    lv = rep["levels"]
    assert sum(r["requirements"] for r in lv) + rep["unplaced"]["requirements"] == n_reqs == rep["total"]["requirements"]
    for r in lv:
        assert r["traced"] + r["gaps"] == r["requirements"], r
        assert r["with_method"] + r["no_method"] == r["requirements"] and r["with_item"] + r["no_item"] == r["requirements"]
        assert r["gaps"] >= max(r["no_method"], r["no_item"]) and r["traced"] <= min(r["with_method"], r["with_item"])
        assert sum(r["methods"].values()) >= r["with_method"]
    u = rep["unplaced"]
    assert rep["total"]["traced"] == sum(r["traced"] for r in lv) + u["traced"]
    assert rep["total"]["gaps"] == sum(r["gaps"] for r in lv) + u["gaps"]
    assert rep["total"]["traced"] + rep["total"]["gaps"] == n_reqs
    assert rep["total"]["items"] == sum(r["items"] for r in lv) + u["items"]


def test_every_contract_dataset_adds_up_both_ways(tmp_path):
    index = build_all(tmp_path, None, 300)
    assert len(index) == len(SPECS)
    for entry in index:
        for folder in entry["folders"]:
            data, problems = load_dataset(tmp_path / folder)
            assert not problems, (folder, problems)
            n = len(data["requirements"])
            check_adds_up(vee_report(data), n)
            check_adds_up(vee_report(data, by="field", level_field="allocation"), n)
            assert vee_report(data) == vee_report(data), "the same dataset must give the same report"


def test_the_four_level_dataset_gives_the_numbers_its_builder_wrote_down(tmp_path):
    build_all(tmp_path, ["F2"], 300)
    data, _ = load_dataset(next(p for p in tmp_path.iterdir() if p.is_dir()))
    rep = vee_report(data)
    assert [r["requirements"] for r in rep["levels"]] == [1, 3, 9, 18]
    assert rep["total"]["items"] == 2 and by_level(rep)[4]["items"] == 2 and rep["total"]["traced"] == 2
    assert rep["total"]["gaps"] == 29 and rep["unplaced"]["requirements"] == 0


def test_no_method_name_is_missing_from_a_report():
    rep = vee_report(ds([req("a")]), by="field", level_field="x")
    assert all(set(r["methods"]) == set(METHODS) | {"other"} for r in rep["levels"])


def test_the_table_names_every_level_and_the_check_that_matches_it():
    text = render(vee_report(ds(tree())))
    for name in ("Stakeholder needs", "System requirements", "Subsystem requirements", "Component requirements", "Validation",
                 "System verification", "Subsystem verification", "Component verification", "All requirements"):
        assert name in text
    assert "Note: 2 requirement(s) sit deeper than level 4" in text


# ---------------------------------------------------------------------------------------------- the command
def make_f2(tmp_path):
    build_all(tmp_path, ["F2"], 300)
    return next(p for p in tmp_path.iterdir() if p.is_dir())


def test_cli_prints_the_table_and_json(tmp_path, capsys):
    folder = make_f2(tmp_path)
    assert cli(["vee", str(folder)]) == 0
    out = capsys.readouterr().out
    assert "Component requirements" in out and "All requirements" in out and "levels from the parent tree" in out
    assert cli(["vee", str(folder), "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert [r["requirements"] for r in rep["levels"]] == [1, 3, 9, 18] and rep["total"]["traced"] == 2


def test_cli_max_gaps_is_a_gate_for_ci(tmp_path, capsys):
    folder = make_f2(tmp_path)
    assert cli(["vee", str(folder), "--max-gaps", "29"]) == 0
    capsys.readouterr()
    assert cli(["vee", str(folder), "--max-gaps", "28"]) == 1
    assert "29 requirement(s) have no verification method or item, more than the 28 allowed" in capsys.readouterr().err


def test_cli_refuses_a_broken_dataset_and_a_missing_field_name(tmp_path, capsys):
    folder = make_f2(tmp_path)
    assert cli(["vee", str(folder), "--by", "field"]) == 2
    assert "--by field needs --level-field" in capsys.readouterr().err
    (folder / "requirements.jsonl").write_text("not json\n", encoding="utf-8")
    assert cli(["vee", str(folder)]) == 1
    assert "NOT a valid dataset" in capsys.readouterr().err
    assert cli(["vee", str(tmp_path / "nothing-here")]) == 1


def test_the_guide_for_screens_describes_the_vee_command():
    guide = (ROOT / "GUI_CONTRACT.md").read_text(encoding="utf-8")
    assert "reqin vee" in guide, "GUI_CONTRACT.md must say how a screen gets the V"
