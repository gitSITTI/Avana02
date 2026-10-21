"""The command line end to end (real HTTP to a local server for the live connectors) and the watch-folder mode."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from live_cases import SYSML_GOLD, sysml_server
from reqin.cli import main
from reqin.watch import Watcher, WatchError, load_rules

ROOT = Path(__file__).parent.parent


# ---- serve an in-memory fake over real HTTP so the CLI uses the real transport ------------------------------------------
def serve(fake):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):  # noqa: N802
            r = fake.get(f"http://{self.headers['Host']}{self.path}", {k: v for k, v in self.headers.items()})
            self.send_response(r.status)
            for k, v in r.headers.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(r.body)))
            self.end_headers()
            self.wfile.write(r.body)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def sysml_http(monkeypatch):
    monkeypatch.setenv("TWC_TOKEN", "cli-token-value")
    holder = {}

    def start():
        srv = serve(holder["fake"])
        holder["srv"] = srv
        return f"http://127.0.0.1:{srv.server_port}/sysmlv2-api"
    # the fake needs the final base URL for its Link headers, which needs the port: bind first, then build the fake
    probe = ThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    port = probe.server_port
    probe.server_close()
    base = f"http://127.0.0.1:{port}/sysmlv2-api"
    holder["fake"] = sysml_server(base=base)
    srv = ThreadingHTTPServer(("127.0.0.1", port), serve(holder["fake"]).RequestHandlerClass)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield base, holder["fake"]
    srv.shutdown()


def test_cli_sample_shows_what_the_connector_sees_and_only_gets(sysml_http, capsys, tmp_path):
    base, fake = sysml_http
    audit = tmp_path / "audit.jsonl"
    rc = main(["sample", "sysml+" + base, "--opt", "project_name=Fictional Widget Controller", "--opt", "token_env=TWC_TOKEN",
               "--opt", "page_size=4", "-n", "2", "--audit", str(audit)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "adapter: sysml_api" in out and "fake-server-tested" in out and "PEEK" in out and "all GET" in out
    assert "cli-token-value" not in out
    lines = [json.loads(l) for l in audit.read_text().splitlines()]
    assert lines and all(l["method"] == "GET" for l in lines) and "cli-token-value" not in audit.read_text()
    assert sum(1 for r in fake.requests if r.path.endswith("/elements")) == 1            # peek: ONE page, not the whole project


def test_cli_import_reads_everything_over_real_http_and_writes_jsonl(sysml_http, capsys, tmp_path):
    base, fake = sysml_http
    out_file = tmp_path / "reqs.jsonl"
    rc = main(["import", "sysml+" + base, "--opt", "project_name=Fictional Widget Controller", "--opt", "token_env=TWC_TOKEN", "--opt", "page_size=4",
               "--profile", str(ROOT / "profiles/sysml_api.yaml"), "--out", str(out_file)])
    report = json.loads(capsys.readouterr().out)
    assert rc == 0 and report["requirements"] == 4 and report["rejected"] == 1 and report["invariant_ok"]
    got = {json.loads(l)["uid"]: json.loads(l)["text"] for l in out_file.read_text().splitlines()}
    assert got == SYSML_GOLD


def test_cli_reports_a_connector_error_without_a_traceback_or_secret(sysml_http, capsys, monkeypatch):
    base, _ = sysml_http
    rc = main(["import", "sysml+" + base, "--opt", "project_name=Nope", "--opt", "token_env=TWC_TOKEN"])
    err = capsys.readouterr().err
    assert rc == 1 and "connector error" in err and "Another Fictional Model" in err and "cli-token-value" not in err
    monkeypatch.delenv("TWC_TOKEN")
    assert main(["sample", "sysml+" + base, "--opt", "project_name=x", "--opt", "token_env=TWC_TOKEN"]) == 1
    assert "TWC_TOKEN is not set" in capsys.readouterr().err


def test_cli_connectors_lists_every_adapter_and_is_honest_about_maturity(capsys):
    assert main(["connectors"]) == 0
    out = capsys.readouterr().out
    for name in ("tabular", "reqif", "sysml_text", "sysml_api", "oslc_rm", "agility", "sql", "docx", "pdf", "sysml1_xmi"):
        assert name in out
    assert out.count("fake-server-tested") >= 3 and "nobody has" in out
    rows = {line.split()[0]: line for line in out.splitlines()[1:] if line.strip() and line.split()[0] in ("sysml1_xmi", "agility", "oslc_rm", "sysml_api", "reqif")}
    assert "fixture-tested" in rows["sysml1_xmi"] and "live-verified" not in "".join(rows.values())


def test_an_empty_source_is_warned_about_not_silently_zero(tmp_path):
    from reqin import Source, ingest
    p = tmp_path / "empty.csv"
    p.write_text("Req ID,Requirement Text\n", encoding="utf-8")
    r = ingest(Source(str(p)))
    assert r.report["requirements"] == 0 and any("NO records" in w for w in r.report["warnings"])


# ---- watch ----------------------------------------------------------------------------------------------------
def tree_hash(d: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(d.rglob("*")):
        h.update(str(p.relative_to(d)).encode())
        if p.is_file():
            h.update(p.read_bytes())
            h.update(str(p.stat().st_mtime_ns).encode())
    return h.hexdigest()


CSV_HEAD = "Req ID,Requirement Text,Rationale\n"
ROWS = ['R-1,"The unit shall start within 5 s.",speed\n', 'R-2,"The unit shall log faults.",audit\n', 'R-3,"The unit shall weigh under 2 kg.",mass\n']


def setup_watch(tmp_path, **kw):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    inbox.mkdir()
    now = [1_000_000.0]
    w = Watcher(inbox, out, clock=lambda: now[0], **kw)
    return inbox, out, w, now


def put(inbox: Path, name: str, text: str, age: float, now) -> Path:
    p = inbox / name
    p.write_text(text, encoding="utf-8")
    os.utime(p, (now[0] - age, now[0] - age))
    return p


def kinds(events):
    return [(e.event, e.file) for e in events]


def test_watch_ingests_once_then_is_quiet_then_reports_exactly_what_changed(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    f = put(inbox, "nightly.csv", CSV_HEAD + "".join(ROWS), 60, now)
    e1 = w.run_once()
    assert kinds(e1) == [("ingested", "nightly.csv")] and e1[0].detail["requirements"] == 3 and e1[0].detail["first_time"]
    assert kinds(w.run_once()) == [("unchanged", "nightly.csv")]                     # same bytes: nothing re-done
    # edit one requirement, add one, remove one
    f.write_text(CSV_HEAD + ROWS[0].replace("5 s", "3 s") + ROWS[1] + 'R-4,"The unit shall self-test.",safety\n', encoding="utf-8")
    os.utime(f, (now[0] - 60, now[0] - 60))
    e2 = w.run_once()
    d = e2[0].detail
    assert e2[0].event == "ingested" and (d["added"], d["removed"], d["changed"]) == (1, 1, 1)
    latest = json.loads((out / "nightly.csv" / "latest.json").read_text())
    rep = json.loads((out / "nightly.csv" / latest["report"]).read_text())
    assert rep["diff_since_previous"] == {"added": 1, "removed": 1, "changed": 1, "unchanged": 1}
    assert len((out / "nightly.csv" / latest["requirements"]).read_text().splitlines()) == 3


def test_watch_never_writes_into_the_watched_folder(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    put(inbox, "a.csv", CSV_HEAD + "".join(ROWS), 60, now)
    before = tree_hash(inbox)
    w.run_once(); w.run_once()
    assert tree_hash(inbox) == before and (out / ".reqin-watch" / "state.json").exists()


def test_watch_refuses_outputs_inside_the_watched_folder(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    with pytest.raises(WatchError, match="inside the watched folder"):
        Watcher(inbox, inbox / "out")
    with pytest.raises(WatchError, match="inside the watched folder"):
        Watcher(inbox, tmp_path / "out", state_dir=inbox / "state")


def test_watch_waits_for_a_file_to_go_quiet(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path, settle=10)
    put(inbox, "half.csv", CSV_HEAD + ROWS[0], 2, now)                   # modified 2 s ago: may still be copying
    assert kinds(w.run_once()) == [("deferred", "half.csv")]
    now[0] += 30
    assert kinds(w.run_once()) == [("ingested", "half.csv")]


def test_watch_ignores_lock_hidden_temp_symlink_and_unlisted_types(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    put(inbox, "~$locked.xlsx", "x", 60, now); put(inbox, ".hidden.csv", CSV_HEAD, 60, now); put(inbox, "x.csv.part", "x", 60, now)
    put(inbox, "notes.txt", "x", 60, now); put(inbox, "spec.pdf", "x", 60, now); put(inbox, "spec.docx", "x", 60, now)
    real = put(tmp_path, "outside.csv", CSV_HEAD + ROWS[0], 60, now)
    (inbox / "link.csv").symlink_to(real)
    assert w.run_once() == []


def test_watch_needs_an_explicit_rule_for_prose_formats(tmp_path, fx):
    inbox, out, _, now = setup_watch(tmp_path)
    shutil.copy(fx["pdf"], inbox / "srs.pdf")
    os.utime(inbox / "srs.pdf", (now[0] - 60, now[0] - 60))
    rules = tmp_path / "rules.yaml"
    rules.write_text("rules:\n  - match: '*.pdf'\n    namespace: SRS-PDF\n")
    w = Watcher(inbox, out, rules=load_rules(rules), clock=lambda: now[0])
    ev = w.run_once()
    assert kinds(ev) == [("ingested", "srs.pdf")] and ev[0].detail["requirements"] > 0
    rep = json.loads((out / "srs.pdf" / json.loads((out / "srs.pdf" / "latest.json").read_text())["report"]).read_text())
    assert any("EXTRACTED" in w for w in rep["report"]["warnings"])        # the pipeline still tells the reader a person must verify


def test_watch_rule_applies_profile_options_and_a_stable_namespace(tmp_path, fx):
    inbox, out, _, now = setup_watch(tmp_path)
    shutil.copy(fx["xlsx"], inbox / "srs.xlsx")
    os.utime(inbox / "srs.xlsx", (now[0] - 60, now[0] - 60))
    rules = tmp_path / "rules.yaml"
    prof = ROOT / "profiles/xlsx_srs.yaml"
    rules.write_text(f"rules:\n  - match: 'srs.xlsx'\n    profile: {prof}\n")
    ev = Watcher(inbox, out, rules=load_rules(rules), clock=lambda: now[0]).run_once()
    assert ev[0].event == "ingested" and ev[0].detail["profile_proposed"] is False
    rows = [json.loads(l) for l in (out / "srs.xlsx" / json.loads((out / "srs.xlsx" / "latest.json").read_text())["requirements"]).read_text().splitlines()]
    assert rows and all(r["fields"].get("allocation") for r in rows[:1]) and rows[0]["uid"].startswith(("SRS", "REQ", "R"))


def test_watch_a_bad_file_is_reported_not_retried_and_does_not_stop_the_others(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    put(inbox, "a_good.csv", CSV_HEAD + "".join(ROWS), 60, now)
    bad = inbox / "b_bad.xlsx"
    bad.write_bytes(b"this is not a zip")
    os.utime(bad, (now[0] - 60, now[0] - 60))
    ev = w.run_once()
    assert kinds(ev) == [("ingested", "a_good.csv"), ("error", "b_bad.xlsx")]
    assert kinds(w.run_once()) == [("unchanged", "a_good.csv"), ("unchanged", "b_bad.xlsx")]         # no hot retry loop
    bad.write_bytes(b"still not a zip, but different")
    os.utime(bad, (now[0] - 60, now[0] - 60))
    assert kinds(w.run_once())[1] == ("error", "b_bad.xlsx")                                          # changed content => tried again


def test_watch_files_that_disappear_are_noted_and_their_outputs_kept(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    f = put(inbox, "a.csv", CSV_HEAD + ROWS[0], 60, now)
    w.run_once()
    f.unlink()
    assert kinds(w.run_once()) == [("gone", "a.csv")] and (out / "a.csv" / "latest.json").exists() and w.run_once() == []


def test_watch_a_damaged_state_file_stops_loudly_instead_of_forgetting_history(tmp_path):
    inbox, out, w, now = setup_watch(tmp_path)
    put(inbox, "a.csv", CSV_HEAD + ROWS[0], 60, now)
    w.run_once()
    (out / ".reqin-watch" / "state.json").write_text("{ not json")
    with pytest.raises(WatchError, match="Move it aside"):
        Watcher(inbox, out)


def test_watch_recursive_and_cli_once_exit_codes(tmp_path, capsys):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    (inbox / "sub").mkdir(parents=True)
    for rel in ("top.csv", "sub/deep.csv"):
        p = inbox / rel
        p.write_text(CSV_HEAD + ROWS[0], encoding="utf-8")
        os.utime(p, (1, 1))
    assert main(["watch", str(inbox), "--out", str(out), "--once"]) == 0
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert [l["file"] for l in lines] == ["top.csv"]                                      # not recursive by default
    assert main(["watch", str(inbox), "--out", str(out), "--once", "--recursive"]) == 0
    lines = [json.loads(l) for l in capsys.readouterr().out.splitlines()]
    assert {(l["event"], l["file"]) for l in lines} == {("unchanged", "top.csv"), ("ingested", "sub/deep.csv")}
    (inbox / "bad.xlsx").write_bytes(b"nope")
    os.utime(inbox / "bad.xlsx", (1, 1))
    assert main(["watch", str(inbox), "--out", str(out), "--once"]) == 1
    capsys.readouterr()
    assert main(["watch", str(inbox), "--out", str(inbox / "o"), "--once"]) == 2
    assert "inside the watched folder" in capsys.readouterr().err
