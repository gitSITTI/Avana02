"""The canonical dataset on disk (GUI_CONTRACT.md): real importers produce valid ones, the fourteen test datasets are valid and different
in the ways they claim, and the checker catches every way a dataset can be wrong."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from reqin import Source, ingest
from reqin.cli import main as cli
from reqin.contract_datasets import SPECS, build_all, validate_all
from reqin.dataset import (DatasetError, FILES, MANIFEST, check_records, describe, load_dataset, summarise, validate_dataset,
                           validate_result, write_dataset, write_dataset_dicts)
from reqin.watch import Watcher

from test_conformance import CASES, src_for

ROOT = Path(__file__).parent.parent
GUIDE = (ROOT / "GUI_CONTRACT.md").read_text(encoding="utf-8")


def tree_bytes(folder: Path) -> dict[str, bytes]:
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


# ---------------------------------------------------------------------------------------------- real importers
@pytest.mark.parametrize("key", CASES)
def test_every_importer_writes_a_dataset_that_follows_the_contract(key, fx, tmp_path):
    res = ingest(src_for(key, fx))
    folder = write_dataset(res, tmp_path / key)
    assert validate_dataset(folder) == [], validate_dataset(folder)
    assert validate_result(res) == []
    assert {p.name for p in folder.iterdir()} == set(FILES.values()) | {MANIFEST}
    again = write_dataset(res, tmp_path / (key + "2"))
    assert tree_bytes(folder) == tree_bytes(again), "the same import must give byte-identical files"


def test_the_report_the_pipeline_writes_agrees_with_the_recomputed_summary(fx):
    for key in CASES:
        res = ingest(src_for(key, fx))
        from dataclasses import asdict
        from reqin.dataset import plain
        s = summarise([plain(asdict(q)) for q in res.requirements])
        assert res.report["coverage"] == s["coverage"] and res.report["confidence"] == s["confidence"], key


def test_the_dataset_keeps_what_the_screen_needs_from_a_real_import(fx, tmp_path):
    folder = write_dataset(ingest(src_for("doors_csv", fx)), tmp_path / "d")
    ds, problems = load_dataset(folder)
    assert not problems and ds["manifest"]["counts"] == {"requirements": 6, "links": 0, "rejected": 2}
    assert all(x["reason"] for x in ds["rejected"]) and ds["report"]["rejected"] == 2
    assert {s["uri"] for s in ds["manifest"]["sources"]} and describe(ds)["rejected"] == 2


def test_links_and_hierarchy_reach_the_dataset(fx, tmp_path):
    ds, problems = load_dataset(write_dataset(ingest(src_for("sysml", fx)), tmp_path / "s"))
    d = describe(ds)
    assert not problems and d["links"] > 0 and d["hierarchy"] and d["max_depth"] >= 2 and d["fidelities"] == ["parsed"]


# ---------------------------------------------------------------------------------------------- the 14 datasets
@pytest.fixture(scope="module")
def sets(tmp_path_factory):
    out = tmp_path_factory.mktemp("sets")
    return out, {e["id"]: e for e in build_all(out, size=400)}


def test_there_are_fourteen_and_every_one_follows_the_contract(sets):
    out, idx = sets
    assert list(idx) == [f"F{i}" for i in range(1, 15)]
    assert {f: p for f, p in validate_all(out).items() if p} == {}


def test_building_twice_gives_identical_bytes(sets, tmp_path):
    out, _ = sets
    build_all(tmp_path / "again", size=400)
    assert tree_bytes(out) == tree_bytes(tmp_path / "again")


def test_the_default_size_of_the_large_dataset_is_fifty_thousand():
    import inspect
    assert inspect.signature(build_all).parameters["size"].default == 50_000


def test_each_dataset_removes_the_assumption_it_claims_to(sets):
    _, idx = sets
    e = {k: v["expect"] for k, v in idx.items()}
    assert e["F1"]["requirements"] == 5 and not e["F1"]["hierarchy"] and not e["F1"]["links"] and not e["F1"]["fields_present"] and e["F1"]["extra_keys"] == 0
    assert e["F2"]["max_depth"] == 4 and e["F2"]["link_kinds"] == ["contain", "derive", "refine", "satisfy", "trace", "verify"]
    assert e["F2"]["fields_present"] == ["allocation", "baseline", "owner", "rationale", "status", "verification"]
    assert e["F2"]["extra_keys"] == 10 and e["F2"]["links_with_an_end_outside_the_import"] >= 2
    assert e["F3"]["synthetic_uids"] == e["F3"]["requirements"] > 0
    assert e["F4"]["links"] > 0 and not e["F4"]["hierarchy"]
    assert e["F5"]["hierarchy"] and e["F5"]["max_depth"] == 4 and e["F5"]["links"] == 0
    assert e["F6"]["fidelities"] == ["extracted"] and 0 < e["F6"]["synthetic_uids"] < e["F6"]["requirements"] and e["F6"]["fields_below_high_confidence"] > 0
    assert e["F7"]["duplicate_uids"] == 2 and e["F7"]["links_with_an_end_outside_the_import"] == 2 and e["F7"]["warnings"] >= 2
    assert (e["F8"]["requirements"], e["F8"]["rejected"], e["F8"]["filtered"], e["F8"]["raw_records"]) == (28, 12, 6, 46)
    assert e["F9"]["requirements"] == 400 and e["F9"]["hierarchy"] and e["F9"]["links"] > 100
    assert e["F10"]["requirements"] == 12
    assert e["F11"]["sources"] == ["legacy_spec.xlsx", "model_export.reqif"] and e["F11"]["fidelities"] == ["structured", "tabular"] and e["F11"]["requirements"] == 20
    assert e["F12"]["requirements"] == 0 and e["F12"]["warnings"] == 1 and e["F12"]["max_depth"] == 0
    assert e["F13"]["extra_keys"] == 30 and {"priority", "safety_class"} <= set(e["F13"]["fields_present"])
    assert {"allocates", "x-custom", "Is Derived From"} <= set(e["F14"]["link_kinds"])


def test_the_awkward_text_really_is_awkward_and_kept_verbatim(sets):
    out, idx = sets
    ds, _ = load_dataset(out / idx["F10"]["folders"][0])
    texts = [r["text"] for r in ds["requirements"]]
    assert max(map(len, texts)) > 5000 and any("\n" in t for t in texts) and any("\t" in t for t in texts)
    assert any("日本語" in t for t in texts) and any("نظام" in t for t in texts) and any("X" * 300 in t for t in texts) and any("<b>shall</b>" in t for t in texts)


def test_the_guide_table_and_the_generator_list_the_same_fourteen(sets):
    _, idx = sets
    rows = re.findall(r"^\| (F\d+) \| ([^|]+?) \|", GUIDE, flags=re.M)
    assert [(i, n) for i, n in rows] == [(e["id"], e["name"]) for e in idx.values()], "GUI_CONTRACT.md section 6 and contract_datasets.py disagree"


def test_the_guide_names_the_commands_that_exist():
    for needle in ("reqin make-datasets", "reqin check-dataset", "--out-dir", "dataset.json", "requirements.jsonl", "links.jsonl", "rejected.jsonl", "report.json"):
        assert needle in GUIDE, needle


# ---------------------------------------------------------------------------------------------- the checker bites
@pytest.fixture
def good(sets, tmp_path):
    out, idx = sets
    ds, problems = load_dataset(out / idx["F2"]["folders"][0])
    assert not problems
    return ds


def problems_after(ds, tmp_path, edit):
    d = copy.deepcopy(ds)
    edit(d)
    folder = write_dataset_dicts(d["requirements"], d["links"], d["rejected"], d["report"], tmp_path / "x")
    return validate_dataset(folder)


BREAKS = {
    "an unknown parent": (lambda d: d["requirements"][5].update(parent_mid="m_nope"), "parent_mid"),
    "its own parent": (lambda d: d["requirements"][5].update(parent_mid=d["requirements"][5]["mid"]), "own parent"),
    "a hierarchy loop": (lambda d: (d["requirements"][0].update(parent_mid=d["requirements"][1]["mid"]),), "loops"),
    "a repeated mid": (lambda d: d["requirements"][3].update(mid=d["requirements"][2]["mid"]), "already used"),
    "empty text": (lambda d: d["requirements"][1].update(text="  "), "text"),
    "an invented fidelity": (lambda d: d["requirements"][1].update(fidelity="guessed"), "fidelity"),
    "a bad confidence label": (lambda d: d["requirements"][1]["conf"].update(text="Certain"), "conf"),
    "no source locator": (lambda d: d["requirements"][1]["ref"].update(locator=""), "locator"),
    "a null field value": (lambda d: d["requirements"][1]["fields"].update(owner=None), "fields values"),
    "a link to an unknown requirement": (lambda d: d["links"][0].update(target_mid="m_nope"), "target_mid"),
    "a link whose uid disagrees with its mid": (lambda d: d["links"][0].update(source_uid="WRONG-1"), "disagrees"),
    "a link with no kind": (lambda d: d["links"][0].update(kind=""), "kind"),
    "a missing key": (lambda d: d["requirements"][1].pop("slots"), "missing slots"),
    "a count that lies": (lambda d: d["report"].update(requirements=d["report"]["requirements"] + 1), "requirements"),
    "records that went missing": (lambda d: d["report"].update(raw_records=d["report"]["raw_records"] + 3), "raw_records"),
    "invariant_ok false": (lambda d: d["report"].update(invariant_ok=False), "invariant_ok"),
    "coverage that lies": (lambda d: d["report"]["coverage"].update(owner=999), "coverage"),
    "confidence that lies": (lambda d: d["report"]["confidence"].update(text={"High": 1}), "confidence"),
    "a rejection with no reason": (lambda d: d["rejected"].append({"ref": d["requirements"][0]["ref"], "reason": "", "fields": {}}), "reason"),
}


@pytest.mark.parametrize("name", BREAKS)
def test_the_checker_catches(name, good, tmp_path):
    edit, needle = BREAKS[name]
    problems = problems_after(good, tmp_path, edit)
    assert problems and any(needle in p for p in problems), (name, problems)


def test_a_clean_copy_of_the_same_edit_path_is_valid(good, tmp_path):
    assert problems_after(good, tmp_path, lambda d: None) == []


def test_duplicate_ids_must_be_announced(sets, tmp_path):
    out, idx = sets
    ds, _ = load_dataset(out / idx["F7"]["folders"][0])
    assert problems_after(ds, tmp_path, lambda d: None) == []
    assert any("no warning says so" in p for p in problems_after(ds, tmp_path, lambda d: d["report"].update(warnings=[])))


def test_an_empty_dataset_must_say_why(sets, tmp_path):
    out, idx = sets
    ds, _ = load_dataset(out / idx["F12"]["folders"][0])
    assert problems_after(ds, tmp_path, lambda d: None) == []
    assert any("empty dataset" in p for p in problems_after(ds, tmp_path, lambda d: d["report"].update(warnings=[])))


def test_extra_keys_are_allowed_so_the_contract_can_grow(good, tmp_path):
    def add(d):
        d["requirements"][0]["new_thing"] = 1
        d["report"]["new_thing"] = 1
    assert problems_after(good, tmp_path, add) == []


def test_a_truncated_or_edited_file_is_noticed_by_the_manifest(sets, tmp_path):
    out, idx = sets
    folder = tmp_path / "t"
    shutil.copytree(out / idx["F2"]["folders"][0], folder)
    f = folder / "requirements.jsonl"
    f.write_bytes(f.read_bytes()[:-400])
    problems = validate_dataset(folder)
    assert any("checksum" in p for p in problems) and any("not valid JSON" in p or "has" in p for p in problems), problems


def test_a_missing_manifest_means_an_unfinished_write(sets, tmp_path):
    out, idx = sets
    folder = tmp_path / "m"
    shutil.copytree(out / idx["F1"]["folders"][0], folder)
    (folder / MANIFEST).unlink()
    assert any(MANIFEST in p and "missing" in p for p in validate_dataset(folder))
    assert validate_dataset(tmp_path / "nothing-here")


def test_writing_never_touches_unrelated_files(tmp_path, fx):
    res = ingest(src_for("csv", fx))
    folder = tmp_path / "keep"
    folder.mkdir()
    (folder / "notes.txt").write_text("mine")
    with pytest.raises(DatasetError, match="other files"):
        write_dataset(res, folder)
    assert (folder / "notes.txt").read_text() == "mine" and not (folder / "requirements.jsonl").exists()
    write_dataset(res, tmp_path / "fresh")
    write_dataset(res, tmp_path / "fresh")                       # an old dataset folder may be overwritten
    assert validate_dataset(tmp_path / "fresh") == []


def test_a_colliding_mid_from_a_real_import_is_flagged_not_hidden(tmp_path):
    csv = tmp_path / "dup.csv"
    csv.write_text('Req ID,Requirement Text\nA-1,"The unit shall start."\nA-1,"The unit shall stop."\n', encoding="utf-8")
    res = ingest(Source(str(csv)))
    problems = validate_dataset(write_dataset(res, tmp_path / "d"))
    assert any("already used" in p for p in problems) and any("duplicate" in w.lower() for w in res.report["warnings"])


# ---------------------------------------------------------------------------------------------- command line and watch
def test_cli_import_out_dir_check_and_describe(fx, tmp_path, capsys):
    src = str(fx["doors_csv"])
    assert cli(["import", src, "--out-dir", str(tmp_path / "ds")]) == 0
    assert "follows the contract" in capsys.readouterr().err
    assert cli(["check-dataset", str(tmp_path / "ds")]) == 0
    out = capsys.readouterr().out
    assert out.startswith("ok:") and "requirements" in out and "hierarchy" in out
    assert cli(["check-dataset", str(tmp_path / "ds"), "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["valid"] and j["problems"] == [] and j["describe"]["requirements"] == 6 and j["describe"]["rejected"] == 2


def test_cli_refuses_a_folder_with_other_files_and_reports_a_broken_dataset(fx, tmp_path, capsys):
    (tmp_path / "busy").mkdir()
    (tmp_path / "busy" / "x.txt").write_text("x")
    assert cli(["import", str(fx["csv"]), "--out-dir", str(tmp_path / "busy")]) == 2
    assert "other files" in capsys.readouterr().err
    cli(["import", str(fx["csv"]), "--out-dir", str(tmp_path / "ok")])
    capsys.readouterr()
    f = tmp_path / "ok" / "links.jsonl"
    f.write_text('{"nope": 1}\n')
    assert cli(["check-dataset", str(tmp_path / "ok")]) == 1
    out = capsys.readouterr().out
    assert out.startswith("NOT a valid dataset") and "checksum" in out


def test_cli_make_datasets(tmp_path, capsys):
    assert cli(["make-datasets", str(tmp_path / "s"), "--only", "F1,F12,f6", "--size", "10"]) == 0
    out = capsys.readouterr().out
    assert "F12" in out and "every one passes" in out and (tmp_path / "s" / "index.json").exists()
    assert cli(["make-datasets", str(tmp_path / "s2"), "--only", "F99"]) == 2
    assert "unknown dataset id" in capsys.readouterr().err


def test_watch_writes_a_complete_dataset_for_every_ingest(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    inbox.mkdir()
    f = inbox / "nightly.csv"
    f.write_text('Req ID,Requirement Text,Rationale\nR-1,"The unit shall start within 5 s.",speed\nR-2,"The unit shall log faults.",audit\n', encoding="utf-8")
    os.utime(f, (940_000.0, 940_000.0))
    w = Watcher(inbox, out, clock=lambda: 1_000_000.0)
    ev = w.run_once()
    assert ev[0].event == "ingested" and "contract_problems" not in ev[0].detail
    latest = json.loads((out / "nightly.csv" / "latest.json").read_text())
    ds = out / "nightly.csv" / latest["dataset"]
    assert validate_dataset(ds) == [] and latest["requirements"] == f"{latest['dataset']}/requirements.jsonl"
    assert (out / "nightly.csv" / latest["report"]).exists()


def test_cli_import_exits_1_and_says_so_when_the_dataset_would_break_the_contract(tmp_path, capsys):
    csv = tmp_path / "dup.csv"
    csv.write_text('Req ID,Requirement Text\nA-1,"The unit shall start."\nA-1,"The unit shall stop."\n', encoding="utf-8")
    assert cli(["import", str(csv), "--out-dir", str(tmp_path / "ds")]) == 1
    err = capsys.readouterr().err
    assert "DOES NOT FOLLOW THE CONTRACT" in err and "already used" in err
    assert (tmp_path / "ds" / "dataset.json").exists()                      # written anyway, so a person can look at it


def test_an_interrupted_write_leaves_no_manifest_so_it_is_never_mistaken_for_complete(tmp_path, fx, monkeypatch):
    import reqin.dataset as d
    real, calls = d._atomic, []

    def flaky(path, data):
        calls.append(path.name)
        if len(calls) == 3:
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(d, "_atomic", flaky)
    with pytest.raises(OSError):
        write_dataset(ingest(src_for("csv", fx)), tmp_path / "half")
    assert not (tmp_path / "half" / MANIFEST).exists()
    assert any(MANIFEST in p and "missing" in p for p in validate_dataset(tmp_path / "half"))
