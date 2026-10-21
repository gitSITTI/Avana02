"""docs/SCREEN_DATA_MAP.md names fields and code. Every name in it is looked up here, in what reqin really writes and in the prototype's source.

This proves the names exist. It does not prove a screen built from the page is right.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import datapaths  # noqa: E402

DOC = (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8")
PREFIX = "|".join(datapaths.PREFIXES)
LOOKS_LIKE_PATH = re.compile(rf"^({PREFIX})[.\[]")
IS_PATH = re.compile(rf"^({PREFIX})(\.[A-Za-z_]\w*|\[\])+$")
STATUS_WORDS = ("dataset only", "needs comparison output", "needs saved work", "partly without a producer")


@pytest.fixture(scope="module")
def generated(tmp_path_factory):
    pytest.importorskip("yaml", reason="reqin needs pyyaml; the guard job installs only pytest, so these tests run where reqin is installed")
    return datapaths.generate(tmp_path_factory.mktemp("map"))


@pytest.fixture(scope="module")
def found(generated):
    return datapaths.collect(generated)


def backticked():
    return re.findall(r"`([^`\n]+)`", DOC)


def test_every_field_the_page_names_occurs_in_real_output(found):
    names = [t for t in backticked() if IS_PATH.match(t)]
    assert len(names) >= 120, f"only {len(names)} field names were found in the page; the check would be nearly empty"
    missing = [n for n in names if n not in found[re.match(rf"^({PREFIX})", n).group(1)]]
    assert not missing, "named in SCREEN_DATA_MAP.md but never written by reqin: " + ", ".join(sorted(set(missing)))


def test_nothing_that_looks_like_a_field_name_is_written_in_a_form_the_check_cannot_read():
    bad = [t for t in backticked() if LOOKS_LIKE_PATH.match(t) and not IS_PATH.match(t)]
    assert not bad, "a field name the test cannot check (spaces, angle brackets or a trailing dot): " + ", ".join(bad)


def test_every_prototype_screen_has_a_section_and_a_status():
    head = "".join(p.read_text(encoding="utf-8") for p in sorted((REPO / "prototype" / "parts" / "m").glob("*.html")))
    screens = re.findall(r"<!-- =+ ?([A-Z][^=]*?) ?=+ -->", head)
    sections = re.findall(r"^### 4\.(\d+) (.+?)  ·  status: (.+)$", DOC, re.M)
    assert len(screens) == len(sections), (
        f"the prototype has {len(screens)} screens ({screens}) but the page has {len(sections)} sections: add or remove a section")
    for num, title, status in sections:
        assert any(w in status for w in STATUS_WORDS), f"4.{num} {title}: status {status!r} uses none of {STATUS_WORDS}"


def test_the_code_the_page_names_exists_in_the_prototype():
    src = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "prototype" / "parts").glob("*.js"))
    section6 = DOC[DOC.index("## 6."):DOC.index("## 7.")]
    names = set(re.findall(r"`([A-Za-z_]\w+)`", section6)) | {"GRADE_PARTS", "GRADE_BANDS"}
    names -= {"aigate"}  # a file, not a definition
    assert len(names) >= 15
    for n in sorted(names):
        assert re.search(rf"(function|const|let|var|class)\s+{n}\b", src), f"{n} is named in SCREEN_DATA_MAP.md but defined nowhere in prototype/parts"


def test_the_grade_really_exists_only_in_the_prototype():
    hits = [p for p in (REPO / "reqin" / "src").rglob("*.py") if re.search(r"\bgrade", p.read_text(encoding="utf-8"), re.I)]
    assert not hits, "the page says no code in reqin/src computes the grade, but %s mentions it; update 4.6, 4.11 and section 5" % hits


def test_a_dataset_with_no_allocation_has_no_allocation_coverage_and_a_flat_one_places_nobody(generated):
    import json
    f1 = generated["F1"]["folders"][0]
    cov = json.loads((f1 / "report.json").read_text(encoding="utf-8"))["coverage"]
    assert "allocation" not in cov, "4.3 says the scope choices are absent when RPT.coverage has no allocation"
    vee = generated["F1"]["vee"]
    assert vee["hierarchy"] is False and vee["level_field"] is None, "4.10 says a flat source with no level field places nobody"
    assert vee["unplaced"]["requirements"] == vee["total"]["requirements"] > 0, "every requirement of a flat source should be unplaced"


def test_a_requirement_alone_is_in_no_cluster_and_no_pair(generated):
    """4.9 defines 'alone' with the engine's mids. This proves only that the mids the engine names are the dataset's (so the join works), not that the definition is the right one."""
    import json
    g = generated["F2"]
    c = g["compare"]
    assert c is not None
    mids = {json.loads(l)["mid"] for l in (g["folders"][0] / "requirements.jsonl").read_text(encoding="utf-8").splitlines() if l}
    in_cluster = {m["mid"] for l in (c / "clusters.jsonl").read_text(encoding="utf-8").splitlines() if l for m in json.loads(l)["members"]}
    in_pair = set()
    for l in (c / "pairs.jsonl").read_text(encoding="utf-8").splitlines():
        if l:
            p = json.loads(l)
            in_pair |= set(p["a"]["mids"]) | set(p["b"]["mids"])
    assert in_cluster <= mids and in_pair <= mids, "the engine named a mid that is not in the dataset"
