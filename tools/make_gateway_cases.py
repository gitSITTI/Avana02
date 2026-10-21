#!/usr/bin/env python3
"""Writes docs/gateway_cases.json: the language-neutral test vectors for the AI gateway's decision core (docs/GATEWAY_SPEC.md).

The inputs are written here by hand, one case for each rule and each way a port has been found to go wrong; the expected answers are what the reference implementation
(reqin/src/reqin/gateway) says. A port in another language is correct when it gives the same answers: it never needs this script or Python.

    python3 tools/make_gateway_cases.py            # rewrite docs/gateway_cases.json
    python3 tools/make_gateway_cases.py --check    # fail if the committed file is not what this would write (reqin/tests/test_gateway_cases.py runs this)

All text in the cases is made up.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))

from reqin.gateway.audit import GENESIS, FIELDS, _canon, verify_log                         # noqa: E402
from reqin.gateway.core import MARKINGS_FORMAT, Markings, decide, fingerprints, prompt_text, route_mismatch, sheet_from_doc, words   # noqa: E402
import tempfile                                                                             # noqa: E402

OUT = REPO / "docs" / "gateway_cases.json"
GATE = json.loads((REPO / "docs" / "ai_gate_cases.json").read_text(encoding="utf-8"))
SHEETS = GATE["sheets"]
REVIEW = {"reviewed_by": "A. Reviewer", "reviewed_at": "2026-01-02", "entered_by": "morgan"}

# ---------------------------------------------------------------------------------------------------------------------------------------- words
WORDS = [
    "The pump SHALL start within 5 s.",
    "",
    "   ---  ,, ",
    "ＳＨＡＬＬ　ｓｔａｒｔ",                      # full-width letters and an ideographic space: NFKC makes them plain
    "pump_shall_start",                              # an underscore is not part of a word
    "ﬁre ﬂow",                                       # ligatures: NFKC
    "İstanbul",                                      # U+0130: full lower-casing is "i" + U+0307, and U+0307 is a mark, not a letter, so it splits the word
    "ΟΔΥΣΣΕΥΣ",                                      # a final capital sigma lower-cases to the final form
    "STRASSE Straße",
    "٣٤ cm",                                         # Arabic-Indic digits are digits
    "起動から5秒以内",                                  # no spaces: one word
    "école",                                   # a letter and a combining accent: NFKC joins them
    "x² ½ s",                                        # NFKC: superscript two becomes a 2; one half becomes 1, a fraction slash, 2
    "CUI//SP-EXPT",
    "pump 🚀 start",                                  # a symbol is not part of a word
    "हिन्दी भाषा",                                    # vowel signs are marks, so they split a word in two
    "àb",                                      # a letter, a combining grave, a letter: NFKC joins the first two
    "don't use 3.5 mm",
    "tab\tand\nnewline\r\nand nbsp",
    "ǅ and ẞ",                                       # a titlecase digraph and a capital sharp s
    "𝐏𝐮𝐦𝐩 𠀀",                                        # mathematical bold letters (NFKC makes them plain) and a character outside the first plane
    "Ⅻ and ⑫",                                       # Roman numeral twelve and a circled twelve: NFKC spells them out
    "a​b a­b",                             # a zero-width space and a soft hyphen are not letters, so they split
]

# ----------------------------------------------------------------------------------------------------------------------------- fingerprints
FINGERPRINTS = [
    "short one two",
    "the pump shall start within five seconds",
    "The pump shall start within five seconds",
    "the pump shall start within five seconds of the command",
    "the pump shall start within five seconds of the command and keep running",
    "the pump, the pump; the pump! the pump? the pump... the pump",
    "go go go go go go go go go go go go",
    "ＴＨＥ PUMP_shall start:within five, seconds",
    "one two three four",
    "one two three four five six",
    "one two three four five six seven",
    "",
]

# ----------------------------------------------------------------------------------------------------------------------------- undeclared
REQS = [
    {"id": "REQ-1", "marking": "No marking", "text": "The pump shall start within five seconds of receiving the start command."},
    {"id": "REQ-2", "marking": "CUI", "text": "The controller shall log every fault with the time it occurred and the unit that raised it."},
    {"id": "REQ-3", "marking": "ITAR", "text": "The valve shall close within two seconds of receiving the shutdown command."},
    {"id": "REQ-4", "marking": "No marking", "text": "The valve shall close within two seconds of receiving the start command."},
    {"id": "REQ-5", "marking": "No marking", "text": "Report fault codes."},
    {"id": "REQ-6", "marking": "No marking", "text": "Log every fault now please."},
    {"id": "REQ-7", "marking": "No marking", "text": "Log every fault now."},
]


def _file(reqs):
    return Markings.build((r["id"], r["marking"], r["text"]) for r in reqs)


UNDECLARED = [
    ("nothing from any requirement", "Compare the two documents and say which is longer.", [], 2),
    ("a requirement pasted in whole and not declared", "Please check this: The pump shall start within five seconds of receiving the start command. Thanks.", [], 2),
    ("the same, and declared", "Please check this: The pump shall start within five seconds of receiving the start command. Thanks.", ["REQ-1"], 2),
    ("pasted with other capitals, punctuation and glue", "THE_PUMP shall, start; within FIVE seconds of receiving the start command!!", [], 2),
    ("pasted in full-width letters", "ＴＨＥ ＰＵＭＰ ＳＨＡＬＬ ＳＴＡＲＴ ＷＩＴＨＩＮ ＦＩＶＥ ＳＥＣＯＮＤＳ ＯＦ ＲＥＣＥＩＶＩＮＧ", [], 2),
    ("only one six-word run of a longer requirement", "He said the pump shall start within five and then stopped.", [], 2),
    ("two runs", "He said the pump shall start within five seconds and then stopped.", [], 2),
    ("two runs, but the limit is raised to three", "He said the pump shall start within five seconds and then stopped.", [], 3),
    ("one run is enough when the limit is one", "He said the pump shall start within five and then stopped.", [], 1),
    ("a paraphrase", "Within five seconds of the start command, the pump must begin running.", [], 2),
    ("wording shared by a declared requirement is not a leak", "The valve shall close within two seconds of receiving the start command.", ["REQ-3"], 2),
    ("the same wording, declared requirement is the other one", "The valve shall close within two seconds of receiving the start command.", ["REQ-4"], 2),
    ("nothing declared: both requirements that share it are found", "The valve shall close within two seconds of receiving the start command.", [], 2),
    ("a requirement of fewer than four words cannot be recognised", "Report fault codes. Report fault codes.", [], 2),
    ("a four-word requirement is recognised whole", "please: log every fault now - thanks", [], 2),
    ("a five-word requirement is recognised whole", "ok. Log every fault now please. Done", [], 2),
    ("a five-word requirement is not recognised in part", "ok. Log every fault. Done", [], 2),
    ("two undeclared requirements, listed in order of id", "The controller shall log every fault with the time it occurred and the unit that raised it. The pump shall start within five seconds of receiving the start command.", [], 2),
    ("a declared requirement alongside an undeclared one", "The controller shall log every fault with the time it occurred and the unit that raised it. The pump shall start within five seconds of receiving the start command.", ["REQ-2"], 2),
    ("a prompt of fewer words than any run", "pump", [], 2),
    ("an empty prompt", "", [], 2),
    ("text split by line breaks and tabs", "The pump\nshall\tstart within\n\nfive seconds of\r\nreceiving the start command", [], 2),
    ("the wording with a soft hyphen inside a word", "The pump shall start within five seconds of receiving the start comm­and.", [], 2),
]

# ------------------------------------------------------------------------------------------------------------------------------ route / sheet
ROUTE = {"model": "Local model v1", "where": "ours", "leaves": False, "log": "local", "days": 90}
SHEET = {**SHEETS["ours-none"], **REVIEW}
ROUTES = [
    ("the same", SHEET, ROUTE),
    ("another model", {**SHEET, "model": "Local model v2"}, ROUTE),
    ("another place", {**SHEET, "where": "tenant"}, ROUTE),
    ("text leaves on one side only", {**SHEET, "leaves": True}, ROUTE),
    ("another way of keeping prompts", {**SHEET, "log": "none"}, ROUTE),
    ("another number of days", {**SHEET, "days": 30}, ROUTE),
    ("days do not matter when neither keeps anything", {**SHEET, "log": "none", "days": 5}, {**ROUTE, "log": "none", "days": 0}),
    ("days matter when only the route keeps something", {**SHEET, "log": "none", "days": 90}, ROUTE),
    ("several at once, in the order model, where, leaves, log, days", {"model": "x", "where": "vendor", "leaves": True, "log": "service", "days": 1, "approved": "none", "unstated": "withhold"}, ROUTE),
    ("days of 90.0 and 90 are the same number", {**SHEET, "days": 90.0}, ROUTE),
]

DOCS = [
    ("a good document", {"on": True, "sheet": SHEET}),
    ("the switch off", {"on": False, "sheet": SHEET}),
    ("a sheet with only some entries (the rest take their defaults)", {"on": True, "sheet": {"model": "m", "reviewed_by": "a", "reviewed_at": "b"}}),
    ("an empty sheet", {"on": True, "sheet": {}}),
    ("not an object", None),
    ("a list", [1]),
    ("an entry that is not known, at the top", {"on": True, "sheet": SHEET, "extra": 1}),
    ("an entry that is not known, in the sheet", {"on": True, "sheet": {**SHEET, "surprise": 1}}),
    ("the switch is 1", {"on": 1, "sheet": SHEET}),
    ("the switch is the text true", {"on": "true", "sheet": SHEET}),
    ("no switch", {"sheet": SHEET}),
    ("no sheet", {"on": True}),
    ("the sheet is text", {"on": True, "sheet": "x"}),
    ("a reviewer's name that is a number", {"on": True, "sheet": {**SHEET, "reviewed_by": 5}}),
    ("a model that is null", {"on": True, "sheet": {**SHEET, "model": None}}),
    ("leaves is 0", {"on": True, "sheet": {**SHEET, "leaves": 0}}),
    ("leaves is the text false", {"on": True, "sheet": {**SHEET, "leaves": "false"}}),
    ("days that are text are left to the gate", {"on": True, "sheet": {**SHEET, "days": "90"}}),
]

# -------------------------------------------------------------------------------------------------------------------------------- prompt_text
BODIES = [
    {"messages": [{"role": "user", "content": "hello"}]},
    {"messages": [{"role": "user", "content": ["a", {"text": "b"}]}], "k-ey": {"n": ["c"]}},
    {"model": "x", "temperature": 0.2, "stream": False, "n": 1, "stop": None, "messages": []},
    {"tools": [{"function": {"name": "f", "description": "wording in a tool description"}}]},
    {"a": "one", "b": "two", "c": "three"},
    {"é": "ü", "日本": ["語"]},
]

HEADERS = [
    "REQ-1,REQ-2",
    " REQ-1 , REQ-2 ,, ",
    "REQ-1,REQ-1,REQ-2",
    "",
    "REQ 1",
    "REQ-1,bad id,REQ-2",
    "-REQ",
    "R" * 200,
    "R" * 201,
    "a.b_c:d-e",
    "REQ-é",
    "req-1,REQ-1",
]

# ------------------------------------------------------------------------------------------------------------------------------ the decision
BASE_MARKS = _file([
    {"id": "A", "marking": "No marking", "text": "The pump shall start within five seconds of receiving the start command."},
    {"id": "B", "marking": "No marking", "text": "The controller shall log every fault with the time it occurred and the unit that raised it."},
    {"id": "C", "marking": "CUI", "text": "The valve shall close within two seconds of receiving the shutdown command."},
    {"id": "X", "marking": "ITAR", "text": "The seeker shall report its range within ten milliseconds of each scan."},
    {"id": "S", "marking": "SECRET", "text": "Another wording that nobody would paste by accident into a prompt."},
    {"id": "U", "marking": "Company confidential", "text": "A wording with a marking the table does not know about, of some length."},
    {"id": "N", "marking": None, "text": "A wording with no marking recorded at all, of some length as well."},
])
DEC_PROMPT = "Compare the wording of these requirements and say which is clearer."


def _dec(name, **kw):
    base = dict(role="reviewer", ids=["A"], markings=BASE_MARKS, ai_doc={"on": True, "sheet": SHEET}, ai_present=True, route=ROUTE, prompt=DEC_PROMPT, max_requirements=200, min_windows=2)
    base.update(kw)
    return name, base


DECIDE = [
    _dec("everything in order, no marking"),
    _dec("everything in order, CUI approved", ids=["C"], ai_doc={"on": True, "sheet": {**SHEET, "approved": "cui"}}),
    _dec("export controlled approved on our own server", ids=["A", "C", "X"], ai_doc={"on": True, "sheet": {**SHEET, "approved": "exp"}}),
    _dec("an observer", role="observer"),
    _dec("an observer is refused before anything else", role="observer", ids=[], ai_present=False),
    _dec("an owner is not refused", role="owner"),
    _dec("no ids", ids=[]),
    _dec("too many ids", ids=["A", "B", "C"], max_requirements=2),
    _dec("exactly as many ids as allowed", ids=["A", "B"], max_requirements=2),
    _dec("an id the gateway does not know", ids=["A", "Z"]),
    _dec("seven unknown ids, only the first twenty are listed", ids=[f"Q{i}" for i in range(25)]),
    _dec("unknown id wins over the switch being off", ids=["Z"], ai_doc={"on": False, "sheet": SHEET}),
    _dec("no AI document", ai_present=False, ai_doc=None),
    _dec("no AI document wins over a bad sheet", ai_present=False, ai_doc={"x": 1}),
    _dec("an AI document the gateway cannot read", ai_doc={"on": "yes", "sheet": SHEET}),
    _dec("the switch is off", ai_doc={"on": False, "sheet": SHEET}),
    _dec("the sheet has no reviewer", ai_doc={"on": True, "sheet": {**SHEET, "reviewed_by": ""}}),
    _dec("the sheet has a reviewer and no date", ai_doc={"on": True, "sheet": {**SHEET, "reviewed_at": " "}}),
    _dec("the sheet contradicts itself (vendor that says nothing leaves, and a model with no name)", ai_doc={"on": True, "sheet": {**SHEET, "model": "", "where": "vendor", "leaves": False}}, route={**ROUTE, "model": ""}),
    _dec("a classified requirement", ids=["A", "S"], ai_doc={"on": True, "sheet": {**SHEET, "approved": "exp"}}),
    _dec("a marking the table does not know", ids=["U"], ai_doc={"on": True, "sheet": {**SHEET, "approved": "exp"}}),
    _dec("no marking recorded, and the sheet says to withhold", ids=["N"]),
    _dec("no marking recorded, and the sheet says treat it as none", ids=["N"], ai_doc={"on": True, "sheet": {**SHEET, "unstated": "none"}}),
    _dec("a CUI requirement and the sheet approves none", ids=["C"]),
    _dec("an export controlled requirement and the sheet approves CUI", ids=["X"], ai_doc={"on": True, "sheet": {**SHEET, "approved": "cui"}}),
    _dec("the route is another model", route={**ROUTE, "model": "Other"}),
    _dec("the route is somewhere else and keeps prompts for longer", route={**ROUTE, "where": "tenant", "days": 365}),
    _dec("the marking rules win over the route", ids=["C"], route={**ROUTE, "model": "Other"}),
    _dec("an undeclared requirement in the prompt", prompt="Also consider: The controller shall log every fault with the time it occurred and the unit that raised it. Thanks."),
    _dec("an undeclared requirement in the prompt, declared", ids=["A", "B"], prompt="Also consider: The controller shall log every fault with the time it occurred and the unit that raised it. Thanks."),
    _dec("the route wins over an undeclared requirement", route={**ROUTE, "model": "Other"}, prompt="The controller shall log every fault with the time it occurred and the unit that raised it."),
    _dec("an undeclared requirement and the leak limit raised past what it has", prompt="The controller shall log every fault with the time it occurred and the unit that raised it.", min_windows=50),
    _dec("two undeclared requirements are listed in order of id", prompt="The valve shall close within two seconds of receiving the shutdown command. The controller shall log every fault with the time it occurred and the unit that raised it."),
]

# ------------------------------------------------------------------------------------------------------------------------------- the audit chain
AUDIT_ROWS = [
    {"at": "2026-03-04T05:06:07Z", "project": "PROJ-A", "person": "sam", "requirements": ["REQ-1", "REQ-2"], "code": "open", "level": "none", "ok": True, "upstream": 200, "prompt_bytes": 1234},
    {"at": "2026-03-04T05:06:09Z", "project": "PROJ-A", "person": "priya \"the lead\"", "requirements": [], "code": "no_requirements", "level": "", "ok": False, "upstream": None, "prompt_bytes": 0},
    {"at": "2026-03-04T05:07:00Z", "project": "PROJ-Ä", "person": "ünïcode\n名前", "requirements": ["R-é", "R-日本"], "code": "marking", "level": "cui", "ok": False, "upstream": None, "prompt_bytes": 99999},
]


def _chain(rows):
    out, prev = [], GENESIS
    for i, r in enumerate(rows, 1):
        row = {"seq": i, **r, "prev": prev}
        pre = prev + "|" + _canon({k: v for k, v in row.items() if k != "hash"})
        row["hash"] = hashlib.sha256(pre.encode("utf-8")).hexdigest()
        out.append({"row": {k: row[k] for k in row if k != "hash"}, "preimage": pre, "hash": row["hash"], "line": _canon(row)})
        prev = row["hash"]
    return out


def _verify_cases():
    chain = _chain(AUDIT_ROWS)
    lines = [c["line"] for c in chain]
    cases = [("a good record", lines, None), ("an empty record", [], None)]

    def bad(name, ls):
        cases.append((name, ls, None))
    row = lambda i: json.loads(lines[i])         # noqa: E731
    edit = json.loads(lines[1]); edit["person"] = "someone else"
    bad("a line edited", [lines[0], _canon(edit), lines[2]])
    bad("a line removed from the middle", [lines[0], lines[2]])
    bad("two lines swapped", [lines[1], lines[0], lines[2]])
    bad("the last line removed is a shorter good record", lines[:2])
    rehash = json.loads(lines[1]); rehash["person"] = "someone else"
    rehash["hash"] = hashlib.sha256((rehash["prev"] + "|" + _canon({k: v for k, v in rehash.items() if k != "hash"})).encode("utf-8")).hexdigest()
    bad("a line edited and its own hash recomputed (the next line no longer follows)", [lines[0], _canon(rehash), lines[2]])
    extra = row(0); extra["more"] = 1
    bad("a line with an entry that does not belong", [_canon(extra)])
    missing = row(0); del missing["code"]
    bad("a line with an entry missing", [_canon(missing)])
    bad("a line that is not JSON", [lines[0], "not json"])
    bad("a line that is JSON but not an object", ["[1]"])
    first = row(0); first["seq"] = 2
    bad("the first line is numbered 2", [_canon(first)])
    out = []
    for name, ls, _ in cases:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.jsonl"
            p.write_text("".join(x + "\n" for x in ls), encoding="utf-8")
            res = verify_log(p)
        exp = {"ok": True, "entries": res["entries"], "head": res["head"]} if res["ok"] else {"ok": False, "at": res["at"]}
        out.append({"name": name, "lines": ls, "expect": exp})
    return out


def build() -> dict:
    cases = {
        "format": "reqin-gateway-cases/1",
        "about": ("Test vectors for the AI gateway's decision core. See docs/GATEWAY_SPEC.md for what each section means. A port is correct when it gives these answers. "
                  "Written by tools/make_gateway_cases.py from the reference implementation (reqin/src/reqin/gateway); all text is made up."),
        "markings_format": MARKINGS_FORMAT,
        "words": [{"text": t, "words": words(t)} for t in WORDS],
        "fingerprints": [{"text": t, "fp": fingerprints(t)} for t in FINGERPRINTS],
        "requirements": REQS,
        "markings_file": _file(REQS),
        "undeclared": [],
        "route_mismatch": [{"name": n, "sheet": s, "route": r, "expect": [m.split(":")[0] for m in route_mismatch(__import__("reqin.aigate", fromlist=["Sheet"]).Sheet(**s), r)]} for n, s, r in ROUTES],
        "sheet_from_doc": [],
        "prompt_text": [],
        "requirement_headers": [],
        "markings_file_errors": [],
        "decide_markings": BASE_MARKS,
        "decide": [],
        "audit_chain": _chain(AUDIT_ROWS),
        "audit_genesis": GENESIS,
        "audit_fields": list(FIELDS),
        "verify_log": _verify_cases(),
    }
    mk = Markings.from_file(cases["markings_file"])
    for name, prompt, declared, minw in UNDECLARED:
        cases["undeclared"].append({"name": name, "prompt": prompt, "declared": declared, "min_windows": minw, "expect": mk.undeclared(prompt, set(declared), minw)})
    for name, doc in DOCS:
        r = sheet_from_doc(doc)
        cases["sheet_from_doc"].append({"name": name, "doc": doc, "expect": None if r is None else {"sheet": {k: v for k, v in r[0].__dict__.items()}, "on": r[1]}})
    for b in BODIES:
        cases["prompt_text"].append({"body": b, "expect": prompt_text(b)})
    deep: object = "bottom"
    for _ in range(41):
        deep = {"k": deep}
    cases["prompt_text"].append({"name": "nested 42 deep is refused", "body": deep, "expect": None})
    deep = "bottom"
    for _ in range(39):
        deep = [deep]
    cases["prompt_text"].append({"name": "nested 40 deep is fine", "body": deep, "expect": "bottom"})
    from reqin.gateway.core import ID_RE
    for h in HEADERS:
        ids = []
        for x in h.split(","):
            x = x.strip()
            if x and x not in ids:
                ids.append(x)
        cases["requirement_headers"].append({"header": h, "ids": ids, "bad": [x for x in ids if not ID_RE.fullmatch(x)]})
    for name, f in [
        ("a good file", _file(REQS)),
        ("another format", {**_file(REQS), "format": "reqin-markings/2"}),
        ("no requirements", {"format": MARKINGS_FORMAT}),
        ("requirements that are a list", {"format": MARKINGS_FORMAT, "requirements": []}),
        ("an id with a space", {"format": MARKINGS_FORMAT, "requirements": {"R 1": {"marking": None, "fp": []}}}),
        ("an entry that is not an object", {"format": MARKINGS_FORMAT, "requirements": {"R1": "x"}}),
        ("an entry with another key", {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": None, "fp": [], "text": "no"}}}),
        ("a marking that is a number", {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": 5, "fp": []}}}),
        ("a fingerprint of the wrong length", {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": None, "fp": ["abc"]}}}),
        ("a fingerprint in capitals", {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": None, "fp": ["ABCDEF0123456789"]}}}),
        ("an entry with no marking and no fingerprints", {"format": MARKINGS_FORMAT, "requirements": {"R1": {}}}),
        ("an id that starts with a dot", {"format": MARKINGS_FORMAT, "requirements": {".R1": {"marking": None, "fp": []}}}),
    ]:
        try:
            Markings.from_file(f)
            ok = True
        except ValueError:
            ok = False
        cases["markings_file_errors"].append({"name": name, "file": f, "ok": ok})
    for name, kw in DECIDE:
        mk2 = Markings.from_file(kw["markings"])
        v = decide(**{**kw, "markings": mk2})
        detail = v.detail
        if v.code == "sheet_mismatch":
            detail = [d.split(":")[0] for d in detail]
        cases["decide"].append({"name": name, **{k: x for k, x in kw.items() if k != "markings"}, "expect": {"ok": v.ok, "status": v.status, "code": v.code, "level": v.level, "detail": detail}})
    return cases


def text() -> str:
    return json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=False) + "\n"


def main(argv: list[str]) -> int:
    t = text()
    if argv == ["--check"]:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != t:
            print(f"{OUT.relative_to(REPO)} is not what tools/make_gateway_cases.py writes; run it and look at the difference")
            return 1
        return 0
    OUT.write_text(t, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(t)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
