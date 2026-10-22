"""The data-binding audit (design/data_audit), the parts that need no browser: what counts as a value, how a value on a screen is traced to what a page loaded, how invented and empty
data are made, the checks that read files (the person's own records, the source, two copies of the data), the findings, the minutes, the brief, the hats, and the command line.

What must hold:
  - the list of checks and the list of hats agree (every hat runs only checks that exist, every check has one hat that owns it) and say what they cannot find;
  - a value is bound to the data, worked out from it (a count or a sum), typed into the page, or unexplained, and the answer does not change with spacing, case or thousands separators;
  - invented data keeps joins (the same text becomes the same invented text), names the field it replaced, and leaves URLs and ISO dates alone; empty data keeps the shape;
  - `known` finds a record's ID on the screen, and says so when a column shows another field or a text from another record; `diff` reports added, removed and changed records and
    anything outside what was meant to change, and writes nothing but its own report into the session folder;
  - the minutes only grow, and a changed, removed or reordered entry is found; a decision needs a name;
  - a hat cannot run another hat's check; a session cannot be started inside a git repository; a check that was not run is never reported as clear;
  - the brief always says what "clear" does not mean, lists what was not run, and groups findings by kind.
What it does not prove: that any check finds a fault in a real page (tools/test_data_audit_browser.py runs them on made-up pages with planted faults, and skips without a browser), or that a
small model can drive the command line (nothing here is a model). Standard library and pytest only.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "data_audit"
sys.path.insert(0, str(KIT / "scripts"))

import audit  # noqa: E402
import audit_checks as CK  # noqa: E402
import audit_common as C  # noqa: E402
import audit_files as FI  # noqa: E402
import audit_net as NET  # noqa: E402
import audit_report as RP  # noqa: E402
import audit_values as V  # noqa: E402

SKILL_MD = KIT / "SKILL.md"
AI_NAMES = ["claude", "anthropic", "chatgpt", "openai", "gpt-", "gemini", "copilot", "codex", "cursor", "aider", "llama", "mistral", "deepseek", "grok", "excalidraw", "figma"]
RECORDS = json.loads((KIT / "examples" / "records" / "requirements.json").read_text(encoding="utf-8"))


def words_of(*paths) -> str:
    return "\n".join(Path(p).read_text(encoding="utf-8") for p in paths if Path(p).is_file()).lower()


def make_session(tmp_path, name="s", page="http://127.0.0.1:1/", **inputs):
    """A session folder outside any repository (tmp_path is not inside one), made by the command itself."""
    sp = tmp_path / name
    argv = ["init", str(sp), "--page", page]
    for k, v in inputs.items():
        argv += ["--" + k.replace("_", "-"), str(v)]
    assert audit.main(argv) == 0
    return str(sp)


def item(text, *, testid="", head="", anc=None, tag="td"):
    return {"text": text, "kind": "text", "tag": tag, "testid": testid, "head": head, "anc": anc or [1, 2, 3], "mark": None, "source": "", "state": ""}


# ------------------------------------------------------------------------------------------------ the lists
def test_skills_and_hats_agree():
    skills, hats = C.skills(), C.hats()
    assert len(skills) == len(C.read_json(KIT / "skills.json")["skills"]), "a skill id appears twice"
    assert set(C.hat_order()) == set(hats), "the order must list every hat once"
    for sid, s in skills.items():
        assert s["default_hat"] in hats, sid
        assert sid in hats[s["default_hat"]]["skills"], "the default hat of %s does not list it" % sid
        assert s["kind"] in ("check", "record", "merge", "admin"), sid
        assert s["does"].strip(), sid
        assert "SESSION" in s["command"], sid
        if s["kind"] == "check":
            assert s["finds"], "%s says what it finds" % sid
            assert s["cannot_find"], "%s says what it cannot find" % sid
    for hid, h in hats.items():
        for sid in h["skills"]:
            assert sid in skills, "%s lists %s, which is not a skill" % (hid, sid)
        for k in ("purpose", "asks_the_person", "looks_for", "hands_to"):
            assert h[k], (hid, k)
        for target in h["hands_to"]:
            assert target in hats, "%s hands to %s" % (hid, target)
    assert [s for s in RP.ORDER if skills[s]["kind"] != "check"] == [], "the order of checks holds only checks"
    assert {s for s, v in skills.items() if v["kind"] == "check"} == set(RP.ORDER)


def test_each_check_has_exactly_the_hats_it_should():
    """The scribe and the chief of staff run no check; every check can be run by its own hat."""
    hats, skills = C.hats(), C.skills()
    for sid in RP.ORDER:
        assert any(sid in hats[h]["skills"] for h in hats if h not in ("scribe", "chief-of-staff")), sid
    assert hats["scribe"]["skills"] == ["minutes"]
    assert set(hats["chief-of-staff"]["skills"]) == {"brief", "skip", "minutes"}


def test_the_lists_use_no_product_names():
    text = words_of(KIT / "skills.json", KIT / "hats.json", SKILL_MD)
    for name in AI_NAMES + ["sketch"]:
        assert re.search(r"(?<![a-z])%s" % re.escape(name), text) is None, "found %r" % name


# ------------------------------------------------------------------------------------------------ values
def test_atoms_find_ids_numbers_dates_and_statements_and_leave_small_numbers():
    got = {(a["kind"], a["value"]) for a in V.atoms("LMP-0042 The lamp shall switch off after 1,248 ms on 2026-10-21 at 09:15, in 3 of 84% cases, v7, page 2")}
    assert ("id", "lmp-0042") in got
    assert ("number", "1248") in got and ("number", "84%") in got
    assert ("date", "2026-10-21") in got and ("time", "09:15") in got
    assert not any(k == "number" and v in ("3", "7", "2") for k, v in got), "single digits are list and page numbers"
    assert any(k == "statement" for k, v in got)
    assert V.atoms("Showing requirements") == []
    assert V.atoms("in 2024") == [], "a year is not a count"


def test_a_number_is_the_same_number_however_it_is_written():
    assert V.canon_number("1,248") == V.canon_number("1248") == "1248"
    assert V.canon_number("7.50") == "7.5" and V.canon_number("84%") == "84%"
    assert V.norm("  The LAMP   shall ") == "the lamp shall"


def test_a_single_digit_is_a_value_only_where_the_page_marks_a_count():
    assert V.item_atoms({"text": "8", "testid": "count-total"}) and V.item_atoms({"text": "8", "testid": "count-total"})[0]["value"] == "8"
    assert V.item_atoms({"text": "8", "testid": ""}) == []
    assert V.item_atoms({"text": "0", "testid": "count-total"}) == [], "zero says nothing about where a number came from"


RESP = [{"type": "fetch", "json": True, "url": "/api/r", "content_type": "application/json", "body": json.dumps(RECORDS)},
        {"type": "document", "json": False, "url": "/", "content_type": "text/html", "body": "<span>214</span> <b>LMP-0042</b> The lamp shall switch off when the cover is opened for more than 30 seconds."},
        {"type": "script", "json": False, "url": "/app.js", "content_type": "text/javascript", "body": "const N = 1,300; // a typed value"}]


def test_loaded_tells_bound_from_typed_from_worked_out():
    L = V.Loaded(RESP)
    assert L.has_in_data({"kind": "id", "value": "lmp-0003"})
    assert not L.has_in_data({"kind": "id", "value": "lmp-0042"}) and L.has_in_code({"kind": "id", "value": "lmp-0042"})
    assert L.explain({"kind": "number", "value": "8"})["kind"] == "count", "eight records"
    assert L.explain({"kind": "number", "value": "3"})["kind"] == "count", "three different owners... or the count of one"
    assert L.explain({"kind": "number", "value": "214"}) is None and L.has_in_code({"kind": "number", "value": "214"})
    assert L.has_in_code({"kind": "number", "value": "1300"}), "1,300 and 1300 are one number"
    text = RECORDS[0]["text"]
    assert L.has_in_data({"kind": "statement", "value": V.norm("LMP-0001 " + text)}), "an ID in front of a sentence does not hide it"
    assert not L.has_in_data({"kind": "statement", "value": V.norm("The lamp shall explode when the cover is shut for more than a day, always.")})


def test_a_sum_is_worked_out_and_is_not_a_count():
    L = V.Loaded([{"type": "fetch", "json": True, "url": "/a", "body": json.dumps([{"uid": "A-1", "w": 12}, {"uid": "A-2", "w": 30}])}])
    assert L.explain({"kind": "number", "value": "42"})["kind"] == "sum"
    assert L.explain({"kind": "number", "value": "2"})["kind"] == "count"


def test_canary_keeps_joins_names_the_field_and_leaves_urls_and_dates():
    c = V.Canary()
    doc = {"rows": [{"uid": "A-1", "owner": "Ana", "reviewer": "Ana", "url": "https://x.test/a", "at": "2026-10-21T10:00:00Z", "n": 5, "tags": ["x", "x"]}, {"uid": "A-2", "owner": "Ben", "n": 7}]}
    out = c.apply(doc)
    r0 = out["rows"][0]
    assert r0["owner"] == r0["reviewer"] and r0["owner"].startswith("CANARY-OWNER-")
    assert out["rows"][0]["uid"].startswith("CANARY-UID-") and out["rows"][1]["owner"] != r0["owner"]
    assert r0["url"] == "https://x.test/a" and r0["at"] == "2026-10-21T10:00:00Z"
    assert r0["n"] != 5 and out["rows"][1]["n"] != 7 and r0["n"] >= 7000000
    assert r0["tags"][0] == r0["tags"][1]
    assert set(c.fields[r0["owner"]]) == {"owner", "reviewer"}
    assert "Ana" not in json.dumps(out)
    assert doc["rows"][0]["owner"] == "Ana", "the original is not changed"


def test_emptied_keeps_the_shape():
    out = V.emptied({"a": [{"x": 1}], "b": "text", "c": 7, "d": None, "e": True, "f": {"g": [1, 2]}})
    assert out == {"a": [], "b": "", "c": 0, "d": None, "e": True, "f": {"g": []}}


# ------------------------------------------------------------------------------------------------ classify
def test_classify_names_where_each_value_came_from():
    items = [item("LMP-0001"), item("214", testid="count-total"), item("LMP-0042", tag="b"), item("8", testid="count-total"), item("12:41"), item("LMP-7777")]
    cls = {c["atom"]["raw"]: c["class"] for c in CK.classify(items, V.Loaded(RESP))}
    assert cls["LMP-0001"] == "bound" and cls["214"] == "typed" and cls["LMP-0042"] == "typed"
    assert cls["8"] == "derived" and cls["12:41"] == "clock" and cls["LMP-7777"] == "unexplained"


def test_numbers_inside_a_sentence_belong_to_the_sentence():
    cls = CK.classify([item("The lamp shall switch off when the cover is opened for more than 30 seconds.")], V.Loaded(RESP))
    assert [c["atom"]["kind"] for c in cls] == ["statement"]


# ------------------------------------------------------------------------------------------------ findings and verdicts
def test_a_finding_needs_a_known_severity_and_a_verdict_never_says_clear_for_what_did_not_run():
    with pytest.raises(ValueError):
        C.finding("x", "huge", "w", "what")
    f_high, f_low, f_info = C.finding("a", "high", "w", "w"), C.finding("b", "low", "w", "w"), C.finding("c", "info", "w", "w")
    assert C.verdict_of([f_high, f_low]) == "problem" and C.verdict_of([f_low, f_info]) == "attention"
    assert C.verdict_of([f_info]) == "clear" and C.verdict_of([]) == "clear" and C.verdict_of([], ran=False) == "not-run"
    assert CK.not_run("trace", "data-analyst", "no browser")["verdict"] == "not-run"


# ------------------------------------------------------------------------------------------------ minutes
def test_minutes_only_grow_and_a_changed_removed_or_reordered_entry_is_found(tmp_path):
    s = make_session(tmp_path)
    audit.main(["minutes", s, "--kind", "decision", "--said-by", "A. Person", "--text", "Fix the count first."])
    audit.main(["minutes", s, "--kind", "note", "--text", "Waiting on the data file."])
    assert C.minutes_chain_problems(s) == []
    p = Path(s) / "minutes.jsonl"
    orig = p.read_text(encoding="utf-8")
    lines = orig.splitlines()
    changed = json.loads(lines[1]); changed["text"] = "Fix nothing."
    for label, text in (("changed", "\n".join([lines[0], json.dumps(changed)] + lines[2:])), ("removed", "\n".join(lines[:1] + lines[2:])), ("reordered", "\n".join([lines[1], lines[0]] + lines[2:]))):
        p.write_text(text + "\n", encoding="utf-8")
        assert C.minutes_chain_problems(s), label
        assert audit.main(["minutes", s, "--verify"]) == 1, label
        assert audit.main(["verify", s]) == 1, label
    p.write_text(orig, encoding="utf-8")
    assert C.minutes_chain_problems(s) == [] and audit.main(["verify", s]) == 0


def test_an_entry_rewritten_with_its_own_fingerprint_redone_is_still_found_because_each_fingerprint_holds_the_one_before(tmp_path):
    s = make_session(tmp_path)
    audit.main(["minutes", s, "--kind", "decision", "--said-by", "A. Person", "--text", "Fix the count first."])
    audit.main(["minutes", s, "--kind", "note", "--text", "Waiting on the data file."])
    audit.main(["minutes", s, "--kind", "note", "--text", "Data file arrived."])
    p = Path(s) / "minutes.jsonl"
    lines = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()]
    a, b = lines[-2], lines[-1]
    a["text"] = "Fix nothing."                                                   # a careful rewrite of the second-to-last entry...
    a["hash"] = C._entry_hash(a["prev"], {k: a[k] for k in ("n", "at", "hat", "kind", "text", "said_by")})
    b["prev"] = a["hash"]                                                         # ...and the last entry made to point at it, but its own fingerprint is left as it was
    p.write_text("\n".join(json.dumps(x) for x in lines[:-2] + [a, b]) + "\n", encoding="utf-8")
    assert C.minutes_chain_problems(s) == ["entry %d does not follow from the one before it" % b["n"]], "the last entry's fingerprint was made from the old one before it"


def test_a_decision_needs_a_name_and_only_the_scribe_and_chief_of_staff_write_minutes(tmp_path):
    s = make_session(tmp_path)
    with pytest.raises(SystemExit) as e:
        audit.main(["minutes", s, "--kind", "decision", "--text", "Ship it."])
    assert "said-by" in str(e.value)
    with pytest.raises(SystemExit) as e:
        audit.main(["minutes", s, "--hat", "data-analyst", "--kind", "note", "--text", "x y z"])
    assert "may not run minutes" in str(e.value)
    with pytest.raises(SystemExit):
        audit.main(["minutes", s, "--kind", "ran", "--text", "pretend a check ran"])      # the audit writes 'ran' itself
    assert audit.main(["minutes", s, "--hat", "chief-of-staff", "--kind", "said", "--said-by", "A. Person", "--text", "It is not ready."]) == 0
    kinds = [e["kind"] for e in C.minutes_entries(s)]
    assert kinds == ["started", "said"]


# ------------------------------------------------------------------------------------------------ the command
def test_a_session_cannot_start_inside_a_git_repository(tmp_path):
    (tmp_path / "work" / ".git").mkdir(parents=True)
    with pytest.raises(SystemExit) as e:
        audit.main(["init", str(tmp_path / "work" / "sess"), "--page", "http://127.0.0.1:1/"])
    assert "git repository" in str(e.value) and not (tmp_path / "work" / "sess").exists()


def test_a_session_does_not_start_twice_and_the_page_must_exist(tmp_path):
    s = make_session(tmp_path)
    with pytest.raises(SystemExit):
        audit.main(["init", s, "--page", "http://127.0.0.1:1/"])
    with pytest.raises(SystemExit):
        audit.main(["init", str(tmp_path / "t"), "--page", str(tmp_path / "nowhere.html")])


def test_a_hat_cannot_run_another_hats_check(tmp_path, capsys):
    s = make_session(tmp_path)
    for hat, sid in (("scribe", "trace"), ("ui-ux", "scan"), ("data-analyst", "marks"), ("chief-of-staff", "canary")):
        with pytest.raises(SystemExit) as e:
            audit.main(["run", s, sid, "--hat", hat])
        assert "may not run" in str(e.value), (hat, sid)
    with pytest.raises(SystemExit):
        audit.main(["run", s, "minutes"])                         # not a check
    with pytest.raises(SystemExit):
        audit.main(["run", s, "known"])                           # no data given


def test_next_walks_the_checks_in_order_and_asks_for_what_it_needs(tmp_path, capsys):
    s = make_session(tmp_path)
    seen = []
    for _ in range(len(RP.ORDER)):
        capsys.readouterr()
        audit.main(["next", s])
        out = capsys.readouterr().out
        m = re.match(r"Next: (\w+) ", out)
        assert m, out
        seen.append(m.group(1))
        if m.group(1) in ("known", "scan", "diff"):
            assert "needs from the person" in out and "skip" in out
        audit.main(["skip", s, m.group(1), "--because", "not part of this test"])
    assert seen == list(RP.ORDER)
    capsys.readouterr()
    audit.main(["next", s])
    assert "brief" in capsys.readouterr().out
    audit.main(["brief", s])
    capsys.readouterr()
    audit.main(["next", s])
    assert "up to date" in capsys.readouterr().out


def test_a_skip_needs_a_reason_and_only_a_check_can_be_skipped(tmp_path):
    s = make_session(tmp_path)
    with pytest.raises(SystemExit):
        audit.main(["skip", s, "trace", "--because", "no"])
    with pytest.raises(SystemExit):
        audit.main(["skip", s, "minutes", "--because", "not needed here"])
    with pytest.raises(SystemExit):
        audit.main(["skip", s, "trace", "--because", "not needed here", "--hat", "ui-ux"])
    assert audit.main(["skip", s, "trace", "--because", "the page needs a sign-in we do not have"]) == 0
    assert C.load_session(s)["skipped"]["trace"].startswith("the page needs")


def test_the_hat_command_gives_a_whole_brief_and_only_that_hats_checks(tmp_path, capsys):
    s = make_session(tmp_path, data=KIT / "examples" / "records" / "requirements.json")
    audit.main(["hat", s, "ui-ux"])
    out = capsys.readouterr().out
    assert "You are wearing the UI/UX engineer hat" in out and "Never:" in out and "marks" in out and "states" in out and "outage" in out
    assert "run SESSION trace" not in out and " trace [" not in out
    assert "Ask the person" in out and "Hand to" in out
    with pytest.raises(SystemExit):
        audit.main(["hat", s, "intern"])
    assert "hat" in [e["kind"] for e in C.minutes_entries(s)]


# ------------------------------------------------------------------------------------------------ reading the person's files
def test_records_load_from_json_lines_and_csv(tmp_path):
    (tmp_path / "a.json").write_text(json.dumps(RECORDS), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"requirements": RECORDS}), encoding="utf-8")
    (tmp_path / "c.jsonl").write_text("\n".join(json.dumps(r) for r in RECORDS), encoding="utf-8")
    (tmp_path / "d.csv").write_text("uid,text,owner\nA-1,Hello there,Ana\nA-2,\"Quoted, text\",Ben\n", encoding="utf-8-sig")
    assert FI.load_records(tmp_path / "a.json") == RECORDS == FI.load_records(tmp_path / "b.json") == FI.load_records(tmp_path / "c.jsonl")
    csv_rows = FI.load_records(tmp_path / "d.csv")
    assert csv_rows[1]["text"] == "Quoted, text" and csv_rows[0]["uid"] == "A-1"
    (tmp_path / "e.json").write_text('{"a": 1}', encoding="utf-8")
    with pytest.raises(SystemExit):
        FI.load_records(tmp_path / "e.json")
    with pytest.raises(SystemExit):
        FI.load_records(tmp_path / "missing.json")


def test_the_id_and_text_fields_are_guessed_and_a_sample_is_spread_and_includes_odd_records():
    assert FI.guess_id_field(RECORDS) == "uid" and FI.guess_text_field(RECORDS, "uid") == "text"
    assert FI.guess_id_field([{"a": "x"}, {"a": "x"}]) is None, "an ID is unique"
    recs = copy.deepcopy(RECORDS)
    recs[4]["text"] = 'A < B & "C" must hold, always, in all of the cases that are described here.'
    picks = FI.pick_sample(recs, "text", 5)
    why = {w: i for w, i in picks}
    assert len(picks) == 5 and why["the first record"] == 0 and why["the last record"] == len(recs) - 1
    assert any("unusual" in w and i == 4 for w, i in picks) or any(i == 4 for _, i in picks)
    assert len({i for _, i in picks}) == 5


def screen_for(rows, head=("ID", "Requirement", "Owner", "Status"), swap_status_for_owner=False, other_text_for=None):
    """The items a table screen would give, one row at a time (each cell has its own ancestors, the row is shared)."""
    items, n = [], 10
    for r_i, r in enumerate(rows):
        row_id, cells = 100 + r_i, [r["uid"], r["text"], r["owner"], r["owner"] if swap_status_for_owner else r["status"]]
        if other_text_for and r["uid"] == other_text_for[0]:
            cells[1] = other_text_for[1]
        for c_i, (h, v) in enumerate(zip(head, cells)):
            items.append(item(v, head=h, anc=[n + c_i, row_id, 99, 98]))
        n += 10
    return items


def visit_of(items, text=""):
    v = NET.Visit(mode="record", url="http://127.0.0.1:1/")
    v.items, v.text = items, text or " ".join(i["text"] for i in items)
    return v


def test_known_finds_the_records_and_checks_the_columns(tmp_path):
    data = tmp_path / "d.json"
    data.write_text(json.dumps(RECORDS), encoding="utf-8")
    s = make_session(tmp_path)
    ok = FI.known(Path(s), "systems-requirements", visit_of(screen_for(RECORDS)), data)
    assert ok["verdict"] == "clear" and ok["counts"]["on_screen"] == ok["counts"]["picked"] == 5 and ok["counts"]["different"] == 0
    sheet = (Path(s) / "known_values.md").read_text(encoding="utf-8")
    assert RECORDS[0]["uid"] in sheet and "- [ ] the text is the same, word for word" in sheet and "holds your data" in sheet
    bad = FI.known(Path(s), "systems-requirements", visit_of(screen_for(RECORDS, swap_status_for_owner=True)), data)
    assert bad["verdict"] == "problem" and any(f["id"].startswith("known.field.") and "'Status'" in f["where"] for f in bad["findings"])
    first_uid = RECORDS[0]["uid"]
    mixed = FI.known(Path(s), "systems-requirements", visit_of(screen_for(RECORDS, other_text_for=(first_uid, "The lamp controller shall do something quite different from the record's own text."))), data)
    assert any(f["id"].startswith("known.text.") and first_uid in f["where"] for f in mixed["findings"])
    short = FI.known(Path(s), "systems-requirements", visit_of(screen_for(RECORDS[:4])), data)
    assert any(f["id"].startswith("known.missing.") for f in short["findings"]) and short["counts"]["on_screen"] < short["counts"]["picked"]


def test_known_does_not_run_on_a_page_that_did_not_open(tmp_path):
    data = tmp_path / "d.json"
    data.write_text(json.dumps(RECORDS), encoding="utf-8")
    v = visit_of([])
    v.ok, v.error = False, "net::ERR_CONNECTION_REFUSED"
    res = FI.known(tmp_path, "systems-requirements", v, data)
    assert res["verdict"] == "not-run"


# ------------------------------------------------------------------------------------------------ scan and diff
def test_scan_reports_data_written_into_source_and_not_design_rules(tmp_path):
    src = tmp_path / "app"
    src.mkdir()
    (src / "app.js").write_text('const rows = [{uid: "LMP-0101", text: "The lamp shall do a thing under all conditions."}];\nlocalStorage.setItem("k", 1);\ndocument.body.style.color = "#123456";\n', encoding="utf-8")
    (src / "index.html").write_text('<p data-testid="count-total">214</p>', encoding="utf-8")
    res = FI.scan(tmp_path, "configuration-management", src)
    rules = {f["id"].split(".")[1] for f in res["findings"]}
    assert {"typed-in-id", "typed-in-record", "typed-in-requirement", "typed-in-count", "storage"} <= rules
    assert "literal-colour" not in rules and res["verdict"] == "problem"
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "app.js").write_text("fetch('/api/x').then(r => r.json());\n", encoding="utf-8")
    assert FI.scan(tmp_path, "configuration-management", clean)["verdict"] == "clear"
    with pytest.raises(SystemExit):
        FI.scan(tmp_path, "configuration-management", tmp_path / "missing")


def write_copies(tmp_path, mutate):
    after = copy.deepcopy(RECORDS)
    mutate(after)
    (tmp_path / "before.json").write_text(json.dumps(RECORDS), encoding="utf-8")
    (tmp_path / "after.json").write_text(json.dumps(after), encoding="utf-8")
    return tmp_path / "before.json", tmp_path / "after.json"


def test_diff_lists_what_changed_and_what_was_not_meant_to(tmp_path):
    def mutate(a):
        a[2]["status"] = "approved"
        a[3]["owner"] = "Zed"
        del a[5]
        a.append({"uid": "LMP-0009", "text": "x", "owner": "Ana", "status": "open", "level": "system"})
    b, a = write_copies(tmp_path, mutate)
    sess = tmp_path / "sess"
    sess.mkdir()
    before_bytes = (b.read_bytes(), a.read_bytes())
    res = FI.diff(sess, "configuration-management", b, a, "uid", allowed_fields=["status"])
    ids = {f["id"] for f in res["findings"]}
    assert {"diff.removed", "diff.added", "diff.outside.owner"} <= ids and res["verdict"] == "problem"
    assert res["counts"] == {"before": 8, "after": 8, "changed": 2, "removed": 1, "added": 1, "outside_scope": 1}
    assert (b.read_bytes(), a.read_bytes()) == before_bytes, "the copies were only read"
    assert sorted(p.name for p in sess.iterdir()) == ["diff.md"], "nothing was written but the report"
    report = (sess / "diff.md").read_text(encoding="utf-8")
    assert "LMP-0006" in report and "| LMP-0003 | status | draft | approved |" in report
    meant = FI.diff(sess, "configuration-management", b, a, "uid", allowed_fields=["status", "owner"], expect_keys=["LMP-0003", "LMP-0004", "LMP-0006", "LMP-0009"])
    assert not any(f["id"] in ("diff.outside.owner", "diff.stray") for f in meant["findings"])
    stray = FI.diff(sess, "configuration-management", b, a, "uid", expect_keys=["LMP-0003"])
    assert any(f["id"] == "diff.stray" and f["severity"] == "high" for f in stray["findings"])


def test_diff_notices_a_field_changed_everywhere_and_spacing_only_changes_and_bad_keys(tmp_path):
    def mutate(a):
        for r in a:
            r["status"] = "approved"
        a[0]["owner"] = " Ana "
        a[1]["uid"] = a[2]["uid"]                               # a duplicate key
    b, a = write_copies(tmp_path, mutate)
    res = FI.diff(tmp_path, "configuration-management", b, a, "uid")
    ids = {f["id"] for f in res["findings"]}
    assert "diff.bulk.status" in ids and any(i.startswith("diff.key.after") for i in ids) and "diff.whitespace" in ids
    nothing = FI.diff(tmp_path, "configuration-management", b, b, "uid")
    assert nothing["verdict"] == "clear" and nothing["counts"]["changed"] == 0


# ------------------------------------------------------------------------------------------------ the brief
def put_result(s, skill, hat, findings, verdict=None, **kw):
    C.save_result(s, C.result(skill, hat, kw.pop("summary", "summary of " + skill), findings, not_checked=["a thing it cannot see"], verdict=verdict, **kw))


def test_the_brief_always_says_what_clear_does_not_mean_and_lists_what_did_not_run(tmp_path):
    s = make_session(tmp_path)
    put_result(s, "trace", "data-analyst", [C.finding("trace.typed.1", "high", "the count", "A number is typed in.", "214", "Read it from the data.")])
    put_result(s, "marks", "ui-ux", [])
    audit.main(["skip", s, "scan", "--because", "no source was given"])
    path, rep = RP.write(s)
    text = path.read_text(encoding="utf-8")
    assert rep["state"] == "blocked" and "does not mean the screen is right" in text
    assert "## In short" in text and "Values written into the page" in text
    assert "Fix first (1)" in text and "A number is typed in." in text
    assert re.search(r"\*\*canary\*\* \(data-analyst hat\): not run yet", text) and "scan**: skipped. Reason given: no source was given" in text
    assert "nothing was looked at by scan (skipped" in text and "a thing it cannot see" in text
    assert "Which screen shows the data you know best" in text and "Can you tell, looking at this screen" in text
    assert "Which two copies of the data" not in text, "questions are for the hats that ran"


def test_readiness_is_blocked_open_attention_or_clear(tmp_path):
    s = make_session(tmp_path)
    sess = C.load_session(s)
    assert RP.readiness(sess, {})[0] == "open"
    ok = {sid: C.result(sid, C.skills()[sid]["default_hat"], "x", []) for sid in RP.ORDER}
    assert RP.readiness(sess, ok)[0] == "clear"
    assert RP.readiness(sess, {**ok, "trace": C.result("trace", "data-analyst", "x", [C.finding("a", "medium", "w", "w")])})[0] == "attention"
    assert RP.readiness(sess, {**ok, "trace": C.result("trace", "data-analyst", "x", [C.finding("a", "info", "w", "w")])})[0] == "clear"
    assert RP.readiness(sess, {**ok, "trace": C.result("trace", "data-analyst", "x", [C.finding("a", "high", "w", "w")])})[0] == "blocked"
    assert RP.readiness(sess, {**ok, "trace": CK.not_run("trace", "data-analyst", "no browser")})[0] == "open"
    # a check skipped with a reason is written down as skipped, and it still keeps the top line from saying clear
    sess["skipped"] = {"trace": "not given"}
    state, reasons = RP.readiness(sess, {k: v for k, v in ok.items() if k != "trace"})
    assert state == "open" and any("trace was skipped" in r and "not given" in r for r in reasons), (state, reasons)
    sess["skipped"] = {k: "no reason that matters" for k in RP.ORDER}
    assert RP.readiness(sess, {})[0] == "open", "eight skipped checks must not read as clear"
    assert RP.readiness({**sess, "skipped": {}}, ok)[0] == "clear"


def test_themes_group_findings_by_kind_of_fault():
    fs = [{**C.finding(i, sev, "w", "w"), "skill": sk} for i, sev, sk in (("trace.typed.1", "high", "trace"), ("canary.stayed.2", "medium", "canary"), ("scan.typed-in-id.1", "high", "scan"),
                                                                          ("outage.error-warm.stale", "high", "outage"), ("marks.none", "medium", "marks"), ("trace.derived", "info", "trace"))]
    t = {x["id"]: x for x in RP.themes(fs)}
    assert t["typed"]["count"] == 3 and t["typed"]["worst"] == "high" and t["typed"]["checks"] == ["canary", "scan", "trace"]
    assert t["fallback"]["count"] == 1 and t["silent"]["count"] == 1 and "wrong-field" not in t


# ------------------------------------------------------------------------------------------------ the whole thing without a browser
def test_scan_and_diff_run_through_the_command_and_a_brief_follows(tmp_path, capsys):
    src = tmp_path / "app"
    src.mkdir()
    (src / "app.js").write_text('const SAMPLE = [{uid: "LMP-0101", text: "The lamp shall dim to the saved level within 3 seconds of power-up."}];\n', encoding="utf-8")
    b, a = write_copies(tmp_path, lambda x: x.pop())
    s = make_session(tmp_path, "sess", source=src, before=b, after=a, key="uid")
    assert audit.main(["run", s, "scan"]) == 0
    assert audit.main(["run", s, "diff", "--strict"]) == 1, "--strict exits 1 on a problem (a record was removed)"
    out = capsys.readouterr().out
    assert "typed-in-id" in out and "removed" in out.lower()
    assert audit.main(["brief", s]) == 0
    rep = C.read_json(Path(s) / "report.json")
    assert rep["state"] == "blocked" and rep["format"] == RP.REPORT_FORMAT
    assert {n["skill"] for n in rep["not_run"]} == {"trace", "canary", "outage", "marks", "states", "known"}
    assert audit.main(["verify", s]) == 0
    audit.main(["status", s])
    assert "Where this stands: blocked" in capsys.readouterr().out


def test_the_session_folder_is_the_only_place_anything_is_written(tmp_path):
    before = {p for p in REPO.rglob("*") if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts and ".cache" not in p.parts and "__pycache__" not in p.parts and ".claude" not in p.parts}
    b, a = write_copies(tmp_path, lambda x: x.pop())
    s = make_session(tmp_path, "sess", before=b, after=a, key="uid")
    audit.main(["run", s, "diff"])
    audit.main(["brief", s])
    after = {p for p in REPO.rglob("*") if p.is_file() and ".git" not in p.parts and "node_modules" not in p.parts and ".cache" not in p.parts and "__pycache__" not in p.parts and ".claude" not in p.parts}
    assert after == before, "files appeared in the repository: %s" % sorted(map(str, after - before))[:3]


def test_the_command_runs_from_the_top_folder_in_its_own_process(tmp_path):
    out = subprocess.run([sys.executable, "design/data_audit/scripts/audit.py", "list"], cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0 and "trace" in out.stdout and "Chief of staff" in out.stdout
    s = tmp_path / "sess"
    r = subprocess.run([sys.executable, "design/data_audit/scripts/audit.py", "init", str(s), "--page", "http://127.0.0.1:1/"], cwd=REPO, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    m = re.search(r"^Next: (python3 .*)$", r.stdout, flags=re.M)
    assert m, r.stdout
    nxt = subprocess.run(m.group(1), shell=True, cwd=REPO, capture_output=True, text=True)
    assert nxt.returncode == 0 and "Next: trace" in nxt.stdout, nxt.stderr


# ------------------------------------------------------------------------------------------------ the skill document
def test_skill_md_names_every_check_every_hat_and_every_command_it_prints():
    assert SKILL_MD.is_file(), "design/data_audit/SKILL.md is missing"
    text = SKILL_MD.read_text(encoding="utf-8")
    assert text.startswith("---\nname: audit-data-binding\n")
    for sid in RP.ORDER:
        assert "`%s`" % sid in text, sid
    for hid, h in C.hats().items():
        assert h["name"] in text, hid
    parser_verbs = set(audit.build_parser()._subparsers._group_actions[0].choices)
    for verb in re.findall(r"audit\.py (\w+) ", text):
        assert verb in parser_verbs, "SKILL.md uses `audit.py %s`, which is not a command" % verb
    for must in ("sends no write that it can see", "not been tried with a small model", "does not mean the screen is right"):
        assert must in text, must


# ------------------------------------------------------------------------------------------------ after the independent review: what each fix must keep true
SENTENCE = "The pump shall stop when the tank level is below 10 percent of capacity."


def test_a_sentence_is_found_with_an_id_and_an_owner_around_it_and_not_with_a_number_changed_inside_it():
    hay = V.norm(SENTENCE + " " + "The pump shall start when the tank level is above 40 percent of capacity.")
    assert V.statement_in(V.norm("PMP-0001 " + SENTENCE + " (Ana, approved)"), hay), "an ID in front and an owner behind do not hide it"
    assert V.statement_in(V.norm("The pump shall stop when the tank level is below 10 percent of cap…"), hay), "a cut-off ending with an ellipsis is still it"
    assert not V.statement_in(V.norm(SENTENCE.replace("10 percent", "15 percent")), hay), "a changed number is not the same sentence"
    assert not V.statement_in(V.norm("PMP-0001 " + SENTENCE.replace("10 percent", "15 percent") + " (Ana)"), hay)
    assert not V.statement_in(V.norm("The valve shall close"), hay)
    long_hay = V.norm("The controller shall log every start and stop event for at least 90 days and shall keep the log until the next scheduled service visit by a technician.")
    changed = V.norm("The controller shall log every start and stop event for at least 30 days and shall keep the log until the next scheduled service visit by a technician.")
    assert not V.statement_in(changed, long_hay), "a number in the middle of a long sentence"


def test_an_id_with_an_underscore_and_a_shorter_sentence_are_values_and_a_lowercase_id_is_not():
    got = {(a["kind"], a["value"]) for a in V.atoms("SYS_REQ_7 and PMP-0012: the pump shall stop now.")}
    assert ("id", "sys_req_7") in got and ("id", "pmp-0012") in got and any(k == "statement" for k, _ in got)
    assert V.atoms("pmp-0012 and R-4") == [], "lowercase and one-letter prefixes are not recognised, and SKILL.md says so"
    assert "pmp-0012" in SKILL_MD.read_text(encoding="utf-8") and "R-4" in SKILL_MD.read_text(encoding="utf-8")


def test_a_class_or_an_id_can_mark_a_single_digit_count_as_the_skill_says():
    assert V.item_atoms({"text": "7", "testid": "", "hook": "total-count"})[0]["value"] == "7"
    assert V.item_atoms({"text": "7", "testid": "", "hook": "intro"}) == []
    assert "class" in SKILL_MD.read_text(encoding="utf-8")


def test_records_held_by_id_are_found_in_the_data_and_changed_by_the_canary():
    doc = {"byId": {"PMP-0012": {"owner": "Ana"}, "PMP-0013": {"owner": "Ben"}}, "order": ["PMP-0012", "PMP-0013"], "42": {"owner": "Cy"}}
    L = V.Loaded([{"type": "fetch", "json": True, "url": "/api", "content_type": "application/json", "body": json.dumps(doc)}])
    assert L.has_in_data({"kind": "id", "value": "pmp-0012"}) and L.has_in_data({"kind": "number", "value": "42"})
    can = V.Canary()
    out = can.apply(doc)
    assert "PMP-0012" not in json.dumps(out) and "PMP-0013" not in json.dumps(out), "keys that are IDs are invented too"
    assert set(out["byId"]) == set(out["order"]), "the same ID becomes the same invented ID, so the page's lookups still join"
    assert "byId" in out and "owner" in out["byId"][out["order"][0]], "other keys are left alone"


def test_a_number_inside_a_long_text_is_not_a_number_of_the_data_and_markup_is_read_as_the_page_shows_it():
    doc = [{"text": "The log shall be kept for at least 90 days after every start.", "kg": "12 kg", "note": "<b>The valve shall close within 5 seconds of a trip.</b> &amp; stay closed"}]
    L = V.Loaded([{"type": "fetch", "json": True, "url": "/api", "content_type": "application/json", "body": json.dumps(doc)}])
    assert not L.has_in_data({"kind": "number", "value": "90"}), "a static '90' on the screen must not be excused by a sentence in the data"
    assert L.has_in_data({"kind": "number", "value": "12"}), "a number in a short text is a number of the data"
    assert L.has_in_data({"kind": "statement", "value": V.norm("The valve shall close within 5 seconds of a trip.")})


def test_the_words_on_a_mark_are_read_as_the_state_and_not_live_is_not_live():
    ok = CK._label_matches
    assert ok("live", "Live from the server") and ok("live", "Up to date") and ok("error", "Could not load requirements") and ok("cached", "Saved copy from 10:00")
    assert not ok("live", "Not synced") and not ok("live", "Not live") and not ok("live", "No longer current")
    assert not ok("live", "Known issues"), "'now' inside 'known' is not the word now"
    assert not ok("error", "Live from the server") and ok("empty", "No requirements returned")


def make_visit(texts, marks=None, body_state=""):
    v = visit_of([item(t) for t in texts])
    v.marks, v.body_state = marks or [], body_state
    return v


def test_a_sign_about_the_data_must_be_new_and_readable():
    normal = make_visit(["Requirements", "You cannot edit a requirement on this screen.", "Error log"])
    same = make_visit(["Requirements", "You cannot edit a requirement on this screen.", "Error log"])
    assert not CK.indicator(same, None, normal), "words the normal screen has too say nothing about the data"
    assert CK.indicator(make_visit(["Requirements", "Could not load requirements, try again."]), None, normal)
    hidden = {"source": "r", "state": "error", "label": "Could not load", "label_visible": False, "shown": True, "asof": ""}
    shown = {**hidden, "label_visible": True}
    assert not CK.indicator(make_visit(["Requirements"], marks=[hidden]), None, normal), "words no one can see are not a sign"
    assert CK.indicator(make_visit(["Requirements"], marks=[shown]), None, normal)
    assert not CK.indicator(make_visit(["Requirements"], body_state="error"), None, normal), "an attribute on the body is not something a person sees"


def test_the_audits_own_refusals_are_not_the_pages_errors():
    assert CK.own_errors(["TypeError: x", "NotSupportedError: the audit does not allow Worker"]) == ["TypeError: x"]


class Fake:
    """Stands in for a net.Runner: counts the visits it is asked for."""
    origin = "http://127.0.0.1:1"

    def __init__(self, ok=True):
        self.n, self.ok = 0, ok

    def visit(self, mode, warm_state=None, shot=None, want_storage=False):
        self.n += 1
        v = NET.Visit(mode=mode, url="http://127.0.0.1:1/", ok=self.ok, error="" if self.ok else "x")
        return v, None


def test_a_visit_where_the_page_did_not_open_is_tried_again_not_reused(tmp_path):
    bad = Fake(ok=False)
    NET.get_visit(bad, tmp_path, "record")
    assert bad.n == 1 and NET.load_visit(tmp_path, "record").ok is False
    good = Fake(ok=True)
    assert NET.get_visit(good, tmp_path, "record").ok and good.n == 1, "the failed visit was reused instead of opening the page again"
    NET.get_visit(good, tmp_path, "record")
    assert good.n == 1, "a visit that opened is reused"


def test_next_offers_a_check_that_could_not_run_again_and_a_skip_is_allowed_for_it_only(tmp_path, capsys):
    s = make_session(tmp_path)
    C.save_result(s, CK.not_run("trace", "data-analyst", "the page did not open: refused"))
    capsys.readouterr()
    audit.main(["next", s])
    out = capsys.readouterr().out
    assert out.startswith("Next: trace") and "could not run" in out and "the page did not open: refused" in out and "--hat data-analyst" in out and " skip " in out
    assert audit.main(["skip", s, "trace", "--because", "the address is wrong"]) == 0, "a check that could not run may be skipped"
    assert audit.main(["verify", s]) == 0, "skipped after it could not run is not 'both skipped and run'"
    state, reasons = RP.readiness(C.load_session(s), C.load_results(s))
    assert state == "open" and any("trace was skipped" in r for r in reasons)
    C.save_result(s, C.result("canary", "data-analyst", "x", []))
    with pytest.raises(SystemExit) as e:
        audit.main(["skip", s, "canary", "--because", "I do not like it"])
    assert "already run" in str(e.value)


def test_every_hat_brief_prints_commands_that_the_parser_accepts_and_that_name_the_hat(tmp_path, capsys):
    import shlex
    s = make_session(tmp_path, "my session")                     # a space in the path: the printed command must still be one command
    parser = audit.build_parser()
    for hid in C.hat_order():
        capsys.readouterr()
        audit.main(["hat", s, hid])
        out = capsys.readouterr().out
        cmds = [l.split("run: ", 1)[1].split("   (needs")[0] for l in out.splitlines() if "run: " in l]
        assert cmds, hid
        for c in cmds:
            argv = shlex.split(c)
            assert argv[0] == "python3" and argv[1].endswith("audit.py"), c
            ns = parser.parse_args(argv[2:])
            if ns.verb == "run":
                assert ns.hat == hid and ns.session == s, c
            if ns.verb == "minutes":
                assert ns.hat == hid and ns.session == s, c
        assert not any(re.search(r"audit\.py run \S+ (minutes|brief|skip)\b", c) for c in cmds), "a hat was told to `run` a skill that is not a check: %s" % cmds


def test_printed_commands_survive_a_path_with_a_space(tmp_path, capsys):
    import shlex
    s = make_session(tmp_path, "a session")
    capsys.readouterr()
    audit.main(["next", s])
    line = next(l for l in capsys.readouterr().out.splitlines() if l.strip().startswith("Run:"))
    argv = shlex.split(line.split("Run:", 1)[1])
    assert s in argv, argv


def test_minutes_cut_off_the_end_are_found_and_so_are_ones_added_by_hand_without_the_head(tmp_path):
    s = make_session(tmp_path)
    for i in range(3):
        audit.main(["minutes", s, "--kind", "note", "--text", "note number %d" % i])
    p = Path(s) / "minutes.jsonl"
    lines = p.read_text(encoding="utf-8").splitlines()
    p.write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")                 # the last two entries removed: the chain before them still holds
    bad = C.minutes_chain_problems(s)
    assert bad and "the last 2 entries are gone" in bad[0], bad
    assert audit.main(["verify", s]) == 1


def test_several_commands_at_once_leave_the_minutes_whole(tmp_path):
    s = make_session(tmp_path)
    procs = [subprocess.Popen([sys.executable, "design/data_audit/scripts/audit.py", "minutes", s, "--kind", "note", "--text", "note from process %d" % i], cwd=REPO,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for i in range(8)]
    outs = [p.communicate(timeout=120) for p in procs]
    assert all(p.returncode == 0 for p in procs), outs
    entries = C.minutes_entries(s)
    assert [e["n"] for e in entries] == list(range(1, 10)), "one entry for every command, numbered once each"
    assert C.minutes_chain_problems(s) == []
    assert not (Path(s) / ".lock").exists(), "the lock was left behind"


def test_a_session_cannot_start_in_a_folder_not_made_yet_inside_a_repository(tmp_path):
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    with pytest.raises(SystemExit) as e:
        audit.main(["init", str(tmp_path / "repo" / "a" / "b" / "sess"), "--page", "http://127.0.0.1:1/"])
    assert "git repository" in str(e.value) and not (tmp_path / "repo" / "a").exists()


def test_records_are_found_at_any_depth_and_the_check_says_when_it_cannot_choose(tmp_path):
    nested = tmp_path / "nested.json"
    nested.write_text(json.dumps({"data": {"items": RECORDS}, "meta": {"total": len(RECORDS)}}), encoding="utf-8")
    assert len(FI.load_records(nested)) == len(RECORDS)
    two = tmp_path / "two.json"
    two.write_text(json.dumps({"a": RECORDS[:3], "b": RECORDS[3:6]}), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        FI.load_records(two)
    assert "more than one list" in str(e.value)
    longer = tmp_path / "longer.json"
    longer.write_text(json.dumps({"a": RECORDS[:2], "b": RECORDS}), encoding="utf-8")
    recs, note = FI.load_records_noted(longer)
    assert len(recs) == len(RECORDS) and "longest" in note
    none = tmp_path / "none.json"
    none.write_text(json.dumps({"a": 1}), encoding="utf-8")
    with pytest.raises(SystemExit):
        FI.load_records(none)


def test_a_data_file_that_is_not_utf8_is_read_as_windows_1252_and_says_so(tmp_path):
    p = tmp_path / "export.csv"
    p.write_bytes("uid,text\nLMP-0001,The café lamp shall switch off\n".encode("cp1252"))
    recs, note = FI.load_records_noted(p)
    assert recs[0]["text"] == "The café lamp shall switch off" and "Windows-1252" in note
    q = tmp_path / "utf8.csv"
    q.write_text("uid,text\nLMP-0001,The café lamp shall switch off\n", encoding="utf-8")
    assert FI.load_records_noted(q)[1] is None


def test_known_says_when_ids_are_not_unique_and_when_the_file_was_not_utf8(tmp_path):
    recs = copy.deepcopy(RECORDS)
    recs[1]["uid"] = recs[0]["uid"]
    data = tmp_path / "d.json"
    data.write_text(json.dumps(recs), encoding="utf-8")
    res = FI.known(tmp_path, "systems-requirements", visit_of(screen_for(RECORDS)), data, id_field="uid")
    assert any(f["id"] == "known.duplicate-ids" and f["severity"] == "medium" for f in res["findings"])


def test_scan_lists_what_it_did_not_read(tmp_path):
    app = tmp_path / "app"
    (app / "data").mkdir(parents=True)
    (app / "dist").mkdir()
    (app / "app.js").write_text("fetch('/api/x').then(r => r.json());\n", encoding="utf-8")
    (app / "data" / "seed.json").write_text('[{"uid": "LMP-0001"}]', encoding="utf-8")
    (app / "server.py").write_text("RECORDS = []\n", encoding="utf-8")
    (app / "dist" / "bundle.js").write_text("var x = 'LMP-0042';\n", encoding="utf-8")
    (app / "package.json").write_text("{}", encoding="utf-8")
    res = FI.scan(tmp_path, "configuration-management", app)
    by = {f["id"]: f for f in res["findings"]}
    assert by["scan.unread-data"]["severity"] == "medium" and "1 .json" in by["scan.unread-data"]["what"], by.keys()
    assert "scan.unread-code" in by and "1 .py" in by["scan.unread-code"]["what"]
    assert "scan.skipped-folders" in by and "dist (1 files)" in by["scan.skipped-folders"]["what"]
    assert res["verdict"] == "attention", "a scan that could not read a fixture folder is not clear"
    assert res["counts"]["files_read"] == 1


def test_the_unread_files_and_the_words_the_checks_use_are_in_the_lists_of_what_they_cannot_find():
    sk = C.skills()
    assert any("JSON" in x and "does not read" in x for x in sk["scan"]["cannot_find"])
    assert any("plain words" in x for x in sk["trace"]["cannot_find"]) and any("server writes" in x for x in sk["trace"]["cannot_find"])
    assert any("English" in x or "list of English words" in x for x in sk["marks"]["cannot_find"])


def test_only_one_command_at_a_time_writes_to_a_session_and_a_lock_left_by_a_dead_one_is_taken_over(tmp_path):
    import os
    import threading
    import time
    s = make_session(tmp_path)
    inside, overlaps = [], []

    def one():
        with C.locked(s):
            inside.append(1)
            if len(inside) > 1:
                overlaps.append(len(inside))
            time.sleep(0.03)
            inside.pop()
    threads = [threading.Thread(target=one) for _ in range(6)]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    assert not overlaps, "two commands were inside the lock at once"

    def bump(sess):
        sess["counter"] = sess.get("counter", 0) + 1

    def many():
        for _ in range(15):
            C.update_session(s, bump)
    threads = [threading.Thread(target=many) for _ in range(4)]
    [t.start() for t in threads]
    [t.join(60) for t in threads]
    assert C.load_session(s)["counter"] == 60, "updates were lost: %s" % C.load_session(s).get("counter")
    with C.locked(s):                                                    # the same thread asking again passes
        with C.locked(s):
            pass
    assert not (Path(s) / ".lock").exists()
    old = Path(s) / ".lock"
    old.mkdir()
    os.utime(old, (time.time() - 120, time.time() - 120))                # left by a command that died two minutes ago
    with C.locked(s, wait=2):
        pass
    fresh = Path(s) / ".lock"
    fresh.mkdir()
    with pytest.raises(SystemExit) as e:
        with C.locked(s, wait=0.3):
            pass
    assert "more than 0 seconds" in str(e.value) or "another audit command" in str(e.value)
    fresh.rmdir()
