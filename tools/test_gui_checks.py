"""tools/gui_checks (serve, hardcode_scan, the probe's reading of the files) and docs/GUI_TEST_HOOKS.md, checked without a browser.

What this proves: the server refuses paths that leave its folders; each scan rule fires on a plain example and stays quiet on a near miss; the reference viewer scans
clean; the probe reads the datasets the way index.json describes them; the canary dataset is a valid dataset; every mark the probe reads is documented and every
documented mark exists in the reference viewer. What it does not prove: that any screen works. That is tools/test_gui_checks_browser.py, which needs Chromium.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
sys.path.insert(0, str(REPO / "design" / "ui_from_image" / "scripts"))
import hardcode_scan as hs  # noqa: E402
import serve  # noqa: E402

VIEWER = REPO / "design" / "reference_viewer"
DOC = (REPO / "docs" / "GUI_TEST_HOOKS.md").read_text(encoding="utf-8")


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status, r.read(), r.headers
    except urllib.error.HTTPError as e:
        return e.code, b"", e.headers


# ------------------------------------------------------------------------------------------------ serve.py
def test_the_server_serves_the_app_the_datasets_tokens_and_fonts(tmp_path):
    (tmp_path / "F1").mkdir()
    (tmp_path / "F1" / "requirements.jsonl").write_text('{"a":1}\n', encoding="utf-8")
    with serve.serving(VIEWER, tmp_path) as base:
        s, body, h = get(base + "/")
        assert s == 200 and b"Dataset viewer" in body and "text/html" in h["Content-Type"]
        s, body, h = get(base + "/datasets/F1/requirements.jsonl")
        assert s == 200 and body == b'{"a":1}\n' and "ndjson" in h["Content-Type"]
        s, body, _ = get(base + "/tokens.css")
        assert s == 200 and body == (REPO / "design" / "tokens.css").read_bytes(), "the viewer folder has no tokens.css of its own, so the design's is served"
        s, body, h = get(base + "/fonts/public-sans-latin-400-normal.woff2")
        assert s == 200 and h["Content-Type"] == "font/woff2" and body[:4] == b"wOF2"
        assert get(base + "/nope.html")[0] == 404
        assert h["Cache-Control" if "Cache-Control" in h else "Content-Type"]


def test_the_server_refuses_paths_that_leave_its_folders(tmp_path):
    (tmp_path / "secret.txt").write_text("no", encoding="utf-8")
    ds = tmp_path / "ds"
    ds.mkdir()
    (ds / "ok.txt").write_text("fine", encoding="utf-8")
    with serve.serving(VIEWER, ds) as base:
        assert get(base + "/datasets/ok.txt")[0] == 200
        for bad in ("/datasets/../secret.txt", "/datasets/%2e%2e/secret.txt", "/%2e%2e/%2e%2e/etc/passwd", "/../../etc/passwd", "/fonts/../../../etc/passwd", "/datasets/%00"):
            code = get(base + bad)[0]
            assert code in (400, 404), (bad, code)
    assert serve.resolve("/datasets/../secret.txt", VIEWER, ds) is None
    assert serve.resolve("/\x00", VIEWER, None) is None


def test_a_symlink_that_leaves_the_folder_is_not_followed(tmp_path):
    ds = tmp_path / "ds"
    ds.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    (ds / "link.txt").symlink_to(outside)
    assert serve.resolve("/datasets/link.txt", VIEWER, ds) is None


def test_the_apps_own_tokens_win_over_the_design_kit_copy(tmp_path):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text("<p>hi</p>", encoding="utf-8")
    (app / "tokens.css").write_text(":root{--x:1}", encoding="utf-8")
    assert serve.resolve("/tokens.css", app, None) == (app / "tokens.css").resolve()
    assert serve.resolve("/", app, None) == (app / "index.html").resolve()


# ------------------------------------------------------------------------------------------------ hardcode_scan.py
def rules(text, suffix=".html"):
    return sorted({f["rule"] for f in hs.scan_text(text, suffix, "x" + suffix)})


@pytest.mark.parametrize("text,suffix,rule", [
    ('<li>The pump shall start within 2 s of power on.</li>', ".html", "typed-in-requirement"),
    ('const t = "The pump shall start within 2 s of power on.";', ".js", "typed-in-requirement"),
    ('<td>SYS-0042</td>', ".html", "typed-in-id"),
    ('rows = [{uid: "SYS-1", text: "x"}]', ".js", "typed-in-record"),
    ('<b data-testid="count-kept">42</b>', ".html", "typed-in-count"),
    ('<b data-testid="row-total">1,204</b>', ".html", "typed-in-count"),
    ('a{color:#1A4DB5}', ".css", "literal-colour"),
    ('a{background:rgb(1,2,3)}', ".css", "literal-colour"),
    ('a{border:1px solid red}', ".css", "literal-colour"),
    ('el.style.color = "#fff"', ".js", "literal-colour"),
    ('<div style="background:#eee">', ".html", "literal-colour"),
    ('a{font-family:Inter, sans-serif}', ".css", "literal-font"),
    ('el.style.fontFamily = "Inter"', ".js", "literal-font"),
    ('x.innerHTML = r.text', ".js", "html-injection"),
    ('document.write(r.text)', ".js", "html-injection"),
    ('eval(s)', ".js", "dynamic-code"),
    ('fetch("https://example.org/data")', ".js", "outside-data"),
    ('<script src="https://cdn.example.org/x.js"></script>', ".html", "outside-data"),
    ('@import url("https://fonts.example.org/x.css");', ".css", "outside-data"),
    ('localStorage.setItem("a", "b")', ".js", "storage"),
])
def test_each_rule_fires_on_a_plain_example(text, suffix, rule):
    assert rule in rules(text, suffix), (rule, text)


@pytest.mark.parametrize("text,suffix", [
    ('a{color:var(--ink);background:var(--paper);font-family:var(--sans)}', ".css"),
    ('a{font-family:inherit}', ".css"),
    ('<a href="#main">skip</a>', ".html"),
    ('<a href="#add">add</a>', ".html"),
    ('<!-- a{color:#fff} The pump shall start within 2 s. -->', ".html"),
    ('/* color:#fff */ a{margin:0}', ".css"),
    ('// x.innerHTML = 1\nvar a = 1;', ".js"),
    ('var d = crypto.subtle.digest("SHA-256", b);', ".js"),
    ('var u = new TextDecoder("UTF-8");', ".js"),
    ('el.textContent = r.text;', ".js"),
    ('<b data-testid="count-kept" id="c-kept"></b>', ".html"),
    ('<p>Choose a dataset, or open this page with ?dataset=FOLDER in the address.</p>', ".html"),
    ('var s = "http://x" // a comment', ".js"),
])
def test_each_rule_stays_quiet_on_a_near_miss(text, suffix):
    assert rules(text, suffix) == [], hs.scan_text(text, suffix, "x" + suffix)


def test_a_finding_names_the_line_and_comments_do_not_shift_it():
    text = "/* one\n two */\nvar ok = 1;\nel.innerHTML = r.text;\n"
    f = hs.scan_text(text, ".js", "a.js")
    assert [(x["file"], x["line"], x["rule"]) for x in f] == [("a.js", 4, "html-injection")]


def test_the_reference_viewer_scans_clean():
    found = hs.scan(VIEWER)
    assert found == [], found


def test_a_requirement_typed_into_a_copy_of_the_viewer_is_found(tmp_path):
    import shutil
    app = tmp_path / "app"
    shutil.copytree(VIEWER, app)
    p = app / "index.html"
    p.write_text(p.read_text(encoding="utf-8").replace("<ul id=\"problems\"></ul>", "<ul id=\"problems\"><li>SYS-0001 The unit shall start within 2 s of power on.</li></ul>"), encoding="utf-8")
    found = hs.scan(app)
    assert {f["rule"] for f in found} >= {"typed-in-requirement", "typed-in-id"} and all(f["file"] == "index.html" for f in found)


def test_tokens_css_and_font_folders_are_not_scanned(tmp_path):
    (tmp_path / "tokens.css").write_text("a{color:#123456}", encoding="utf-8")
    (tmp_path / "fonts").mkdir()
    (tmp_path / "fonts" / "x.css").write_text("a{color:#123456}", encoding="utf-8")
    (tmp_path / "app.css").write_text("a{color:#123456}", encoding="utf-8")
    assert [f["file"] for f in hs.scan(tmp_path)] == ["app.css"]


def test_strict_counts_warnings_and_the_exit_status_follows(tmp_path, capsys):
    (tmp_path / "a.js").write_text('localStorage.setItem("filter", "x")\n', encoding="utf-8")
    assert hs.main([str(tmp_path)]) == 0
    assert hs.main([str(tmp_path), "--strict"]) == 1
    out = tmp_path / "f.json"
    hs.main([str(tmp_path), "--json", str(out)])
    assert json.loads(out.read_text(encoding="utf-8"))["findings"][0]["rule"] == "storage"


# ------------------------------------------------------------------------------------------------ the probe's reading of the files
@pytest.fixture(scope="module")
def datasets(tmp_path_factory):
    pytest.importorskip("yaml", reason="reqin needs pyyaml; the guard job installs only pytest, so these tests run where reqin is installed")
    from reqin.cli import main
    d = tmp_path_factory.mktemp("probe") / "ds"
    assert main(["make-datasets", str(d), "--size", "400"]) == 0
    return d


def test_the_probe_reads_every_dataset_as_index_json_describes_it(datasets):
    import probe
    index = json.loads((datasets / "index.json").read_text(encoding="utf-8"))
    for e in index["datasets"]:
        o = probe.oracle([datasets / f for f in e["folders"]])
        ex = e["expect"]
        mine = {"requirements": len(o["reqs"]), "links": len(o["links"]), "rejected": len(o["rejected"]), "filtered": sum(o["filtered"].values()), "raw_records": o["read"],
                "warnings": len(o["warnings"]), "hierarchy": o["hierarchy"], "max_depth": o["max_depth"], "synthetic_uids": o["synthetic"], "duplicate_uids": o["duplicates"],
                "fidelities": o["fidelities"], "sources": o["sources"], "link_kinds": sorted(o["link_kinds"]), "fields_present": o["fields_present"],
                "links_with_an_end_outside_the_import": o["outside"], "fields_below_high_confidence": o["low_conf"]}
        for k, v in mine.items():
            assert ex[k] == (sorted(v) if k == "fields_present" else v), (e["id"], k, ex[k], v)


def test_the_canary_dataset_is_a_valid_dataset_and_is_new_every_time(datasets, tmp_path):
    import probe
    from reqin.dataset import check_dataset
    template = probe.read_jsonl(datasets / "F01_minimal" / "requirements.jsonl")[0]
    probe.make_canary(tmp_path / "a", "aaaaaa", template)
    probe.make_canary(tmp_path / "b", "bbbbbb", template)
    ds, problems = check_dataset(tmp_path / "a")
    assert problems == [] and len(ds["requirements"]) == 3 and len(ds["links"]) == 1 and len(ds["rejected"]) == 1
    assert check_dataset(tmp_path / "b")[1] == []
    ua = {r["uid"] for r in probe.read_jsonl(tmp_path / "a" / "requirements.jsonl")}
    ub = {r["uid"] for r in probe.read_jsonl(tmp_path / "b" / "requirements.jsonl")}
    assert not ua & ub
    assert not any(r["text"] in [x["text"] for x in probe.read_jsonl(datasets / "F01_minimal" / "requirements.jsonl")] for r in probe.read_jsonl(tmp_path / "a" / "requirements.jsonl"))


# ------------------------------------------------------------------------------------------------ the hooks document
def probe_marks():
    src = (REPO / "tools" / "gui_checks" / "probe.py").read_text(encoding="utf-8")
    names = set(re.findall(r'(?:tid|P\.q|Q\.q|P\.count|Q\.count|P\.text|Q\.text|P\.texts|Q\.texts|P\.visible|Q\.visible|in_panel)\("([a-z][a-z0-9-]*)"\)', src))
    names |= set(re.findall(r"data-testid=\\?[\"']([a-z][a-z0-9-]*)", src))
    names |= set(re.findall(r'\("(count-[a-z]+)"', src))
    return names


def doc_marks():
    return set(re.findall(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+|list|tree|detail|warning|fact|row|link)`", DOC)) & set(re.findall(r"`([^`]+)`", DOC))


def viewer_marks():
    src = (VIEWER / "index.html").read_text(encoding="utf-8") + (VIEWER / "viewer.js").read_text(encoding="utf-8")
    return set(re.findall(r'data-testid=\\?"([a-z][a-z0-9-]*)', src)) | set(re.findall(r', "([a-z][a-z0-9-]*)"\)', src)) | set(re.findall(r'"([a-z][a-z0-9-]*)"\);?\s*$', src, flags=re.M))


def test_every_mark_the_probe_reads_is_in_the_hooks_document():
    docnames = set()
    for cell in re.findall(r"\|\s*((?:`[^`]+`(?:,\s*|\s+and\s+|\s*)?)+)\s*\|", DOC):
        docnames |= set(re.findall(r"`([a-z][a-z0-9-]*)`", cell))
    missing = sorted(m for m in probe_marks() if m not in docnames)
    assert not missing, "the probe reads marks the document does not define: %s" % missing


def test_every_mark_in_the_hooks_document_exists_in_the_reference_viewer():
    docnames = set()
    for cell in re.findall(r"^\|\s*((?:`[^`]+`(?:,\s*|\s+and\s+|\s*)?)+)\s*\|", DOC, flags=re.M):
        docnames |= set(re.findall(r"`([a-z][a-z0-9-]*)`", cell))
    docnames -= {"loads"}
    vm = viewer_marks()
    assert len(docnames) > 40
    missing = sorted(m for m in docnames if m not in vm)
    assert not missing, "marks in the document that the reference viewer does not carry: %s" % missing


def test_the_hooks_document_says_what_it_does_not_prove():
    assert "does not" in DOC and "one browser" in DOC


# ------------------------------------------------------------------------------------------------ check_status.py
GOOD_STATUS = {"format": "reqin-agent-status/1", "agent": "component agent", "task": "Build the counts card", "state": "done", "files": [],
               "ran": [{"command": "python3 tools/gui_checks/probe.py --datasets DIR", "exit_code": 0},
                       {"command": "probe against a broken copy", "exit_code": 1, "expected_exit_code": 1}],
               "not_checked": ["Browsers other than Chromium"], "blocked_on": None}


def test_a_complete_status_is_accepted():
    import check_status as cs
    assert cs.check(GOOD_STATUS) == []


@pytest.mark.parametrize("change,needle", [
    ({"format": "x"}, "format must be"),
    ({"agent": ""}, "agent must be"),
    ({"state": "finished"}, "state must be"),
    ({"ran": []}, "no command was run"),
    ({"ran": [{"command": "probe", "exit_code": 1}]}, "exited 1, not 0"),
    ({"ran": [{"command": "probe", "exit_code": "0"}]}, "needs a command and an integer exit_code"),
    ({"ran": [{"command": "probe", "exit_code": True}]}, "needs a command and an integer exit_code"),
    ({"not_checked": []}, "not_checked is empty"),
    ({"not_checked": ["  "]}, "not_checked must be"),
    ({"blocked_on": "waiting for another agent"}, "blocked_on is set"),
    ({"state": "blocked", "blocked_on": None}, "does not say what stopped it"),
    ({"files": "a.js"}, "files must be a list"),
])
def test_each_way_a_status_can_be_wrong_is_refused(change, needle):
    import check_status as cs
    errs = cs.check({**GOOD_STATUS, **change})
    assert any(needle in e for e in errs), (change, errs)


def test_a_partial_or_blocked_status_may_have_a_failing_command_and_a_reason():
    import check_status as cs
    assert cs.check({**GOOD_STATUS, "state": "partial", "ran": [{"command": "probe", "exit_code": 1}]}) == []
    assert cs.check({**GOOD_STATUS, "state": "blocked", "ran": [], "blocked_on": "the contract file does not say who owns the list"}) == []


def test_listed_files_must_exist_under_the_root(tmp_path):
    import check_status as cs
    (tmp_path / "a.js").write_text("x", encoding="utf-8")
    assert cs.check({**GOOD_STATUS, "files": ["a.js"]}, tmp_path) == []
    assert any("does not exist" in e for e in cs.check({**GOOD_STATUS, "files": ["b.js"]}, tmp_path))
    assert any("outside" in e for e in cs.check({**GOOD_STATUS, "files": ["../a.js"]}, tmp_path))


def test_the_status_command_line_exits_1_on_a_bad_file(tmp_path, capsys):
    import check_status as cs
    good, bad = tmp_path / "g.json", tmp_path / "b.json"
    good.write_text(json.dumps(GOOD_STATUS), encoding="utf-8")
    bad.write_text(json.dumps({**GOOD_STATUS, "ran": []}), encoding="utf-8")
    assert cs.main([str(good)]) == 0
    assert cs.main([str(bad)]) == 1 and "no command was run" in capsys.readouterr().out
    assert cs.main([str(tmp_path / "missing.json")]) == 1
