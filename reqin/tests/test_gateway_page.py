"""The page and the gateway must say the same thing about every group of the sample project.

The page (prototype/parts/aigate.js) shows a person which groups the AI may be used on; the gateway (reqin.gateway) is what actually lets a prompt through. They read the
same switch and the same data sheet, and the same rules are written twice (docs/ai_gate_cases.json is the table both are tested against). This test goes one step further:
for every one of the sample's 252 groups, under every sheet in that table, reviewed and not, switch on and off, the page's answer and the gateway's must be the same, code
and level. It also builds the gateway's markings file from what the page exports, so the demo gateway is made from the same sample the page shows.

Needs Node.js and the repository's prototype/ folder with its built page; without them it is skipped, and the log says so."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from reqin.gateway import Markings, decide

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / "prototype" / "project" / "Main.dc.html"
EXPORT = REPO / "prototype" / "export_ai_groups.js"
CASES = REPO / "docs" / "ai_gate_cases.json"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(not NODE or not PAGE.is_file() or not EXPORT.is_file() or not CASES.is_file(), reason="needs Node.js and the repository's prototype/ and docs/ folders")


def page_says(configs: list[dict]) -> dict:
    r = subprocess.run([NODE, str(EXPORT), str(PAGE)], input=json.dumps({"configs": configs}), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def configs() -> list[dict]:
    sheets = json.loads(CASES.read_text(encoding="utf-8"))["sheets"]
    out = []
    for name, sh in sheets.items():
        for reviewed in (True, False):
            for on in (True, False):
                full = {**sh, "reviewed_by": "A. Moreno" if reviewed else "", "reviewed_at": "2 Oct" if reviewed else "", "entered_by": "Morgan Hale"}
                out.append({"name": f"{name}{'' if reviewed else ' unreviewed'}{'' if on else ' off'}", "on": on, "sheet": full})
    return out


@pytest.fixture(scope="module")
def world():
    cfgs = configs()
    data = page_says([{"on": c["on"], "sheet": c["sheet"]} for c in cfgs])
    rows = [(r["id"], r["marking"], r["text"]) for r in data["requirements"]]
    mk = Markings.from_file(json.loads(json.dumps(Markings.build(rows))))
    return cfgs, data, mk


def route_of(sheet: dict) -> dict:
    return {k: sheet[k] for k in ("model", "where", "leaves", "log", "days")}


def test_the_sample_has_what_the_comparison_needs(world):
    cfgs, data, mk = world
    assert len(data["clusters"]) == 252 and len(data["requirements"]) == 1248 and len(cfgs) >= 20
    levels = {r["marking"] for r in data["requirements"]}
    assert {"No marking", "CUI", "ITAR", "Proprietary", ""} <= levels, "the sample must hold every kind of hold the page shows, or the comparison proves little"
    assert all(len(v) >= 1 for v in data["clusters"].values())
    assert set(mk.marks) == {r["id"] for r in data["requirements"]}


def test_every_group_gets_the_same_answer_from_the_page_and_the_gateway(world):
    cfgs, data, mk = world
    differ, seen = [], set()
    for cfg, page in zip(cfgs, data["decisions"]):
        for cid, members in data["clusters"].items():
            v = decide(role="reviewer", ids=members, markings=mk, ai_doc={"on": cfg["on"], "sheet": cfg["sheet"]}, ai_present=True, route=route_of(cfg["sheet"]), prompt="")
            code, level = page[cid]
            seen.add(code)
            if (v.code, v.level) != (code, level):
                differ.append((cfg["name"], cid, "page", code, level, "gateway", v.code, v.level))
    assert not differ, f"{len(differ)} differences, the first few: {differ[:5]}"
    assert {"open", "off", "unreviewed", "sheet", "marking", "unknown", "unstated"} <= seen, f"the comparison saw only {sorted(seen)}"


def test_a_project_that_has_no_sheet_yet_is_closed_for_the_page_and_the_gateway(world):
    """The connected page starts a shared project closed (switch off, empty unreviewed sheet) and the gateway answers no_sheet: both are 'nothing goes'."""
    cfgs, data, mk = world
    blank = {"model": "", "where": "ours", "leaves": False, "log": "none", "days": 0, "approved": "none", "unstated": "withhold", "reviewed_by": "", "reviewed_at": "", "entered_by": ""}
    page = page_says([{"on": False, "sheet": blank}])["decisions"][0]
    assert {c for c, _ in page.values()} == {"off"}
    for cid, members in list(data["clusters"].items())[:20]:
        v = decide(role="reviewer", ids=members, markings=mk, ai_doc=None, ai_present=False, route=route_of(blank), prompt="")
        assert v.ok is False and v.code == "no_sheet"


def test_the_gateways_markings_file_is_made_from_the_sample_and_holds_no_wording(world):
    cfgs, data, mk = world
    rows = [(r["id"], r["marking"], r["text"]) for r in data["requirements"]]
    blob = json.dumps(Markings.build(rows))
    some = [r["text"] for r in data["requirements"] if len(r["text"].split()) > 8][:20]
    assert some and not any(t[:30] in blob for t in some)
    assert sum(1 for r in mk.marks.values() if r is None or r == "") == 3
