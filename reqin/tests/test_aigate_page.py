"""The AI gate is written twice: in Python for the pipeline (reqin/src/reqin/aigate.py) and in JavaScript for the prototype page (prototype/parts/aigate.js).
Both are run against the one table of cases in docs/ai_gate_cases.json, but a table only covers what someone thought of. This test feeds both the same thousands of
generated inputs (markings with odd spaces, letters from other alphabets, control characters, upper and lower case, slashes; sheets with every combination of answers;
groups of markings) and requires the same answer from each. It needs Node.js and the repository's prototype/ folder; without them it is skipped, and the log says so.
"""
from __future__ import annotations

import itertools
import json
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from reqin.aigate import Sheet, gate, group_level, marking_level

REPO = Path(__file__).resolve().parents[2]
PAGE_JS = REPO / "prototype" / "parts" / "aigate.js"
CASES = REPO / "docs" / "ai_gate_cases.json"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(not NODE or not PAGE_JS.is_file() or not CASES.is_file(), reason="needs Node.js and the repository's prototype/ and docs/ folders")

RUNNER = r"""
const fs = require('fs'), vm = require('vm');
const src = fs.readFileSync(process.argv[1], 'utf8');
const core = src.slice(0, src.indexOf('/* ---- the words the page uses ---- */'));
const ctx = vm.createContext({});
vm.runInContext(core + '\nthis.api = { aiMarkLevel, aiGroupLevel, aiGate, aiSheetProblems };', ctx);
const input = JSON.parse(fs.readFileSync(0, 'utf8')), api = ctx.api;
const out = {
  markings: input.markings.map((m) => api.aiMarkLevel(m)),
  groups: input.groups.map((g) => api.aiGroupLevel(g.levels, g.unstated)),
  gates: input.gates.map((g) => { const d = api.aiGate(g.sheet, g.on, g.markings); return [d.open, d.code, d.level, d.detail]; }),
};
process.stdout.write(JSON.stringify(out));
"""

ODD = ["", " ", "  ", "\t", "\n", "\r\n", " ", " ", " ", "​", "﻿", "\x85", "\x1c", "\x0b", "\x0c", "᠎", "/", "//", " / ", "-", "_", ".", ",", ":", "(", ")",
       "é", "ß", "ſ", "İ", "ı", "K", "K", "ǅ", "Σ", "ς", "я", "日", "٣", "²", "́", "\U0001f600", "\u0000"]
WORDS = ["cui", "CUI", "Cui", "ITAR", "itar", "EAR99", "ear", "ear99x", "EXPT", "export", "Export controlled", "secret", "SECRET", "Top Secret", "TS//SCI", "classified", "sci", "SCI",
         "none", "None", "no marking", "No marking", "unmarked", "public", "Public", "Unclassified", "Proprietary", "Controlled Unclassified Information", "CUI//SP-EXPT", "FOUO", "earé", ""]


def corpus(seed: int = 7) -> list:
    rnd = random.Random(seed)
    table = json.loads(CASES.read_text(encoding="utf-8"))
    out: list = [c[0] if isinstance(c, list) else c.get("text", c.get("marking")) for c in table["marking_cases"]]
    out += [None, 5, 5.5, True, False, [], {}, "", " ", " "]
    for w in WORDS:
        for a, b in itertools.product(ODD, ODD):
            out.append(a + w + b)
    for _ in range(4000):
        w = rnd.choice(WORDS)
        mid = rnd.choice(ODD)
        cut = rnd.randrange(len(w) + 1)
        s = w[:cut] + mid + w[cut:]
        out.append(rnd.choice(ODD) + (s.swapcase() if rnd.random() < 0.3 else s) + rnd.choice(ODD))
    return out


def run_page(payload: dict, js: Path = PAGE_JS) -> dict:
    r = subprocess.run([NODE, "-e", RUNNER, str(js)], input=json.dumps(payload), capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


LEVELS = ["none", "cui", "exp", "classified", "unknown", "unstated"]


def sheets() -> list[dict]:
    base = {"model": "M", "reviewed_by": "A. Reviewer", "reviewed_at": "1 Oct"}
    out = []
    for where, leaves, log, approved, unstated in itertools.product(["ours", "tenant", "vendor", "elsewhere"], [False, True], ["none", "local", "service", "weird"], ["none", "cui", "exp", "top"], ["none", "withhold", "x"]):
        for days in ([0] if log == "none" else [0, 1, 90, 3650, 3651, 1.5, -1]):
            out.append(dict(base, where=where, leaves=leaves, log=log, approved=approved, unstated=unstated, days=days))
    for blank in ["", "  ", "\t", "\u00a0", "\u2003", "\x85", "\x1c", "\u2028", "\ufeff", "\u200b", "\u180e", "x"]:
        for field in ("model", "reviewed_by", "reviewed_at"):
            out.append(dict(base, **{field: blank}, where="ours", leaves=False, log="none", approved="none", unstated="none", days=0))
    return out


def test_both_read_every_marking_the_same_way():
    marks = corpus()
    page = run_page({"markings": marks, "groups": [], "gates": []})["markings"]
    mine = [marking_level(m) for m in marks]
    differ = [(m, a, b) for m, a, b in zip(marks, mine, page) if a != b]
    assert not differ, f"{len(differ)} of {len(marks)} markings are read differently by the pipeline and the page; first: {[(repr(m), 'python ' + a, 'page ' + b) for m, a, b in differ[:5]]}"


def test_both_find_the_same_level_for_every_group():
    rnd = random.Random(11)
    groups = [{"levels": [rnd.choice(LEVELS + ["bogus", "constructor", "__proto__"]) for _ in range(rnd.randrange(0, 5))], "unstated": rnd.choice(["none", "withhold", "x"])} for _ in range(3000)]
    page = run_page({"markings": [], "groups": groups, "gates": []})["groups"]
    mine = [group_level(g["levels"], g["unstated"]) for g in groups]
    differ = [(g, a, b) for g, a, b in zip(groups, mine, page) if a != b]
    assert not differ, f"{len(differ)} groups differ; first: {differ[:3]}"


def test_both_make_the_same_decision_for_every_sheet_and_group():
    rnd = random.Random(13)
    marks = corpus()
    pool = [m for m in marks if isinstance(m, str)]
    gates = []
    for sh in sheets():
        for on in (True, False):
            for _ in range(3):
                gates.append({"sheet": sh, "on": on, "markings": [rnd.choice(pool + [None]) for _ in range(rnd.randrange(0, 4))]})
    page = run_page({"markings": [], "groups": [], "gates": gates})["gates"]
    differ = []
    for g, p in zip(gates, page):
        sh = g["sheet"]
        d = gate(Sheet(**{k: sh[k] for k in ("model", "where", "leaves", "log", "days", "approved", "unstated", "reviewed_by", "reviewed_at")}), g["on"], g["markings"])
        mine = [d.open, d.code, d.level, list(d.detail)]
        if mine != p:
            differ.append((g, mine, p))
    assert not differ, f"{len(differ)} of {len(gates)} decisions differ; first: {differ[:2]}"


def test_the_comparison_can_fail():
    """Change the page's rule in a copy and the comparison must say so; otherwise it proves nothing."""
    src = PAGE_JS.read_text(encoding="utf-8")
    broken = src.replace("const AI_NONE = ['no marking', 'none', 'unmarked', 'public'];", "const AI_NONE = ['no marking', 'none', 'unmarked'];", 1)
    assert broken != src
    marks = ["public", "CUI", "none"]
    with tempfile.TemporaryDirectory() as d:
        copy = Path(d) / "aigate.js"
        copy.write_text(broken, encoding="utf-8")
        page = run_page({"markings": marks, "groups": [], "gates": []}, copy)["markings"]
    assert [marking_level(m) for m in marks] != page
