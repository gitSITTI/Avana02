"""The data-binding audit (design/data_audit) in a real browser, on made-up pages with faults planted in them.

Skipped when Playwright, Pillow or Chromium is not installed (the continuous-integration job installs none of them). What this proves, on design/data_audit/examples/:
  - nothing the audit does writes: a page that posts on load, one that sends PUT, PATCH and DELETE, and one that submits a form never reach the server, and the requests are listed;
  - `bad_app`, which has a typed-in count, a pinned requirement typed into the markup, a sample shown when the source fails, a browser copy shown with no label, a column that shows the
    wrong field and a write on load, gets each of those named by the check that is meant to find it;
  - `good_app`, which reads everything from the data and says what state it is in, gets no finding above information from any check;
  - twelve deliberate breaks of `good_app`, one at a time, each turn the check that is meant to notice from clear to a finding (so a check that never fails would be caught);
  - a driver that only copies the commands the scripts print can run the whole audit and get a brief;
  - a saved visit is reused and `--fresh` opens the page again; `--allow-post` lets a POST through only where the person named it; setup steps reach data behind a click.
What it does not prove: that a real page behaves like these (nothing here was run on a real system), that the pictures are good to look at (a person has to look), or any browser but Chromium.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
pytest.importorskip("PIL")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "data_audit"
EXAMPLES = KIT / "examples"
sys.path.insert(0, str(KIT / "scripts"))

import audit  # noqa: E402
import audit_checks as CK  # noqa: E402
import audit_common as C  # noqa: E402
import audit_net as NET  # noqa: E402

_spec = importlib.util.spec_from_file_location("data_audit_example_server", EXAMPLES / "server.py")
SRV = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SRV)


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

BROWSER_CHECKS = ("trace", "canary", "outage", "marks", "states")


class Served:
    def __init__(self, app_dir, data=SRV.DATA):
        self.httpd, self.log = SRV.make_server(app_dir, data)
        SRV.serve_in_thread(self.httpd)
        self.url = "http://127.0.0.1:%d/" % self.httpd.server_address[1]

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def serve():
    started = []

    def make(app_dir, data=SRV.DATA):
        s = Served(app_dir, data)
        started.append(s)
        return s
    yield make
    for s in started:
        s.close()


def run_checks(url, sess, names=BROWSER_CHECKS, **kw):
    out = {}
    with NET.Runner(url, **kw) as r:
        for n in names:
            out[n] = getattr(CK, n)(Path(sess), r, C.skills()[n]["default_hat"])
    return out


def ids(res):
    return [f["id"] for f in res["findings"]]


def high(res):
    return [f for f in res["findings"] if f["severity"] == "high"]


def above_info(res):
    return [f for f in res["findings"] if f["severity"] != "info"]


# ------------------------------------------------------------------------------------------------ the planted faults, found
@pytest.fixture(scope="module")
def bad_run(tmp_path_factory):
    s = Served(EXAMPLES / "bad_app")
    sess = tmp_path_factory.mktemp("bad") / "sess"
    try:
        res = run_checks(s.url, sess)
        res["known"] = __import__("audit_files").known(sess, "systems-requirements", NET.load_visit(sess, "record"), SRV.DATA)
        res["scan"] = __import__("audit_files").scan(sess, "configuration-management", EXAMPLES / "bad_app")
        yield res, s.log, sess
    finally:
        s.close()


def test_the_page_that_posts_on_load_cannot_write(bad_run):
    res, log, _ = bad_run
    assert log["writes"] == [], "the audit sent a write: %s" % log["writes"]
    assert any(f["id"] == "trace.write.1" and "POST /api/visit" in f["what"] for f in res["trace"]["findings"])


def test_trace_finds_what_is_typed_into_the_page(bad_run):
    res, _, _ = bad_run
    t = res["trace"]
    typed = [f for f in t["findings"] if f["id"].startswith("trace.typed.")]
    seen = " ".join(f["evidence"] for f in typed)
    assert "214" in seen and "LMP-0042" in seen and "09:15" in seen and "The lamp shall switch off" in seen
    assert t["verdict"] == "problem" and t["counts"]["typed"] == 4 and t["counts"]["bound"] >= 16


def test_canary_finds_what_stays_when_the_data_changes_and_a_column_that_shows_the_wrong_field(bad_run):
    c = bad_run[0]["canary"]
    stayed = " ".join(f["evidence"] for f in c["findings"] if f["id"].startswith("canary.stayed."))
    assert "214" in stayed and "LMP-0042" in stayed
    wrong = [f for f in c["findings"] if f["id"].startswith("canary.wrong-field.")]
    assert len(wrong) == 1 and "'Status'" in wrong[0]["where"] and "'owner'" in wrong[0]["what"] and wrong[0]["severity"] == "high"
    assert c["counts"]["followed"] >= 16 and c["counts"]["responses_changed"] == 1


def test_outage_finds_the_sample_shown_on_failure_and_the_unlabelled_copy(bad_run):
    o = bad_run[0]["outage"]
    for tag in ("error", "disconnect"):
        f = next(x for x in o["findings"] if x["id"] == "outage.%s.appeared" % tag)
        assert f["severity"] == "high" and "LMP-0101" in f["evidence"]
    for tag in ("error-warm", "disconnect-warm"):
        assert any(x["id"] == "outage.%s.stale" % tag and x["severity"] == "high" for x in o["findings"]), tag
    assert "outage.empty.silent" in ids(o)


def test_marks_and_states_say_the_screen_does_not_tell_a_person(bad_run):
    res = bad_run[0]
    assert "marks.none" in ids(res["marks"])
    assert {"states.empty.quiet", "states.error.quiet", "states.disconnect.quiet"} <= set(ids(res["states"]))
    png = Path(res["states"]["files"][0])
    assert png.name == "states.png" and png.stat().st_size > 5000


def test_known_and_scan_find_the_wrong_column_and_the_data_in_the_source(bad_run):
    res = bad_run[0]
    assert any(i.startswith("known.field.") and i.endswith(".status") for i in ids(res["known"]))
    assert res["known"]["verdict"] == "problem"
    rules = {i.split(".")[1] for i in ids(res["scan"])}
    assert {"typed-in-id", "typed-in-record", "typed-in-requirement", "typed-in-count", "storage"} <= rules


# ------------------------------------------------------------------------------------------------ the good page, left alone
@pytest.fixture(scope="module")
def good_run(tmp_path_factory):
    s = Served(EXAMPLES / "good_app")
    sess = tmp_path_factory.mktemp("good") / "sess"
    try:
        res = run_checks(s.url, sess)
        res["known"] = __import__("audit_files").known(sess, "systems-requirements", NET.load_visit(sess, "record"), SRV.DATA)
        yield res, s.log, sess
    finally:
        s.close()


def test_the_good_page_gets_no_finding_above_information_from_any_check(good_run):
    res, log, _ = good_run
    for name, r in res.items():
        assert r["verdict"] == "clear", (name, [(f["id"], f["what"]) for f in above_info(r)])
        assert not above_info(r), name
    assert log["writes"] == []


def test_the_good_page_still_shows_what_was_asked_of_it(good_run):
    """A check that finds nothing because it saw nothing would pass the test above, so say what it did see."""
    res, _, sess = good_run
    assert res["trace"]["counts"]["bound"] >= 16 and res["trace"]["counts"]["typed"] == 0 and res["trace"]["counts"]["data_responses"] == 1
    assert res["canary"]["counts"]["stayed"] == 0 and res["canary"]["counts"]["followed"] >= 16 and res["canary"]["counts"]["canary_items_on_screen"] >= 16
    assert res["outage"]["counts"]["replays"] == 5
    saved = [f for f in res["outage"]["findings"] if f["id"].endswith("-warm.saved-copy")]
    assert len(saved) == 2 and all(f["severity"] == "info" for f in saved), "the saved copy is shown and says it is one"
    assert res["marks"]["counts"]["marks"] == 1
    assert res["known"]["counts"]["on_screen"] == 5 and res["known"]["counts"]["different"] == 0
    rec = NET.load_visit(sess, "record")
    assert rec.marks[0]["state"] == "live" and rec.marks[0]["label"] == "Live from the server"
    warm = NET.load_visit(sess, "disconnect-warm")
    assert warm.marks[0]["state"] == "cached" and "Saved copy" in warm.marks[0]["label"]
    err = NET.load_visit(sess, "error")
    assert err.marks[0]["state"] == "error" and err.body_state == "error"
    assert NET.load_visit(sess, "empty").marks[0]["state"] == "empty"


# ------------------------------------------------------------------------------------------------ deliberate breaks of the good page
APP = "app.js"
BREAKS = [
    ("a count typed in at the true value", APP, 'document.getElementById("count").textContent = String(rows.length);', 'document.getElementById("count").textContent = "8";',
     ("outage",), lambda r: any(f["id"].startswith("outage.empty.left") and f["severity"] == "high" for f in r["outage"]["findings"])),
    ("the Status column shows the owner", APP, "[r.uid, r.text, r.owner, r.status]", "[r.uid, r.text, r.owner, r.owner]",
     ("canary",), lambda r: any(f["id"].startswith("canary.wrong-field") and "'Status'" in f["where"] for f in r["canary"]["findings"])),
    ("a sample shown when the source fails", APP, 'else show("error", []);',
     'else show("error", [{uid: "LMP-0101", text: "The lamp shall dim to the saved level within 3 seconds of power-up.", owner: "Eli", status: "approved"}]);',
     ("outage",), lambda r: any(f["id"] == "outage.error.appeared" and f["severity"] == "high" for f in r["outage"]["findings"])),
    ("the mark says live while the source fails", APP, 'else show("error", []);', 'else show("live", []);',
     ("marks",), lambda r: any(f["id"].startswith("marks.error.state") and f["severity"] == "high" for f in r["marks"]["findings"])),
    ("a browser copy is shown as if it were live", APP, 'show("cached", kept.rows, kept.at)', 'show("live", kept.rows, kept.at)',
     ("outage",), lambda r: any(f["id"] == "outage.disconnect-warm.stale" and f["severity"] == "high" for f in r["outage"]["findings"])),
    ("the page writes when it opens", APP, "load();\n", 'fetch("/api/visit", {method: "POST", body: "{}"}).catch(() => {});\nload();\n',
     ("trace",), lambda r: any(f["id"] == "trace.write.1" for f in r["trace"]["findings"])),
    ("a requirement typed into the markup", "index.html", "<main>", "<aside><b>LMP-0042</b></aside><main>",
     ("trace", "canary"), lambda r: any(f["id"].startswith("trace.typed") and "LMP-0042" in f["evidence"] for f in r["trace"]["findings"]) and any(f["id"].startswith("canary.stayed") for f in r["canary"]["findings"])),
    ("the page shows its own rows and ignores the data", APP, "const rows = await r.json();",
     'await r.json(); const rows = [{uid: "LMP-0101", text: "The lamp shall dim to the saved level within 3 seconds of power-up.", owner: "Eli", status: "approved"}];',
     ("canary", "trace"), lambda r: r["canary"]["verdict"] == "problem" and any(f["id"] == "canary.none-reached" for f in r["canary"]["findings"])),
    ("an error looks like an empty source", APP, 'error: "Could not load requirements, try again"', 'error: "The server returned no requirements"',
     ("states",), lambda r: "states.empty-is-error" in ids(r["states"])),
    ("a blank screen when the source fails", APP, 'else show("error", []);', 'else document.body.innerHTML = "<p>\\u00a0</p>";',
     ("outage",), lambda r: any(f["id"] == "outage.error.silent" for f in r["outage"]["findings"])),
    ("the marks are taken off", "index.html", ' data-source="requirements" data-source-state="loading"', "",
     ("marks",), lambda r: "marks.none" in ids(r["marks"])),
    ("the words on the mark say live while the state says error", APP, 'error: "Could not load requirements, try again"', 'error: "Live from the server"',
     ("marks",), lambda r: any(f["id"].startswith("marks.error.words") and f["severity"] == "high" for f in r["marks"]["findings"])),
]


@pytest.mark.parametrize("name,fname,old,new,checks,expect", BREAKS, ids=[b[0] for b in BREAKS])
def test_a_deliberate_break_is_noticed(tmp_path, serve, name, fname, old, new, checks, expect):
    app = tmp_path / "app"
    shutil.copytree(EXAMPLES / "good_app", app)
    text = (app / fname).read_text(encoding="utf-8")
    assert text.count(old) == 1, "the break %r no longer matches %s" % (name, fname)
    (app / fname).write_text(text.replace(old, new), encoding="utf-8")
    s = serve(app)
    res = run_checks(s.url, tmp_path / "sess", names=checks)
    assert expect(res), "%s was not noticed: %s" % (name, {k: [(f["severity"], f["id"]) for f in v["findings"]] for k, v in res.items()})


# ------------------------------------------------------------------------------------------------ nothing it does can write
WRITER = """<!doctype html><html><head><meta charset="utf-8"><title>writer</title></head><body>
<p>Writer</p>
<form id="f" method="post" action="/api/form"><input name="a" value="1"></form>
<script>
fetch("/api/put", {method: "PUT", body: "{}"}).catch(() => {});
fetch("/api/patch", {method: "PATCH", body: "{}"}).catch(() => {});
fetch("/api/delete", {method: "DELETE"}).catch(() => {});
navigator.sendBeacon && navigator.sendBeacon("/api/beacon", "x");
setTimeout(() => document.getElementById("f").submit(), 300);
</script></body></html>
"""


def test_no_request_that_writes_gets_through_in_any_mode(tmp_path, serve):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text(WRITER, encoding="utf-8")
    s = serve(app)
    with NET.Runner(s.url) as r:
        seen = {}
        for mode in NET.MODES:
            v, _ = r.visit(mode)
            seen[mode] = {(b["method"], b["url"].rsplit("/", 1)[-1]) for b in v.blocked}
    assert s.log["writes"] == [], "the server received: %s" % s.log["writes"]
    assert {("PUT", "put"), ("PATCH", "patch"), ("DELETE", "delete"), ("POST", "form")} <= seen["record"], seen["record"]


def test_a_post_is_let_through_only_where_the_person_named_it(tmp_path, serve):
    s = serve(EXAMPLES / "bad_app")
    with NET.Runner(s.url, allow_post=r"/api/visit$") as r:
        v, _ = r.visit("record")
    assert v.ok and v.blocked == [] and s.log["writes"] == ["POST /api/visit"]
    s2 = serve(EXAMPLES / "bad_app")
    with NET.Runner(s2.url, allow_post=r"/api/somewhere-else$") as r:
        v, _ = r.visit("record")
    assert [b["method"] for b in v.blocked] == ["POST"] and s2.log["writes"] == []


def test_the_answer_to_an_allowed_post_is_read_in_every_mode_and_never_waits_forever(tmp_path, serve):
    """The example server answers every write with Cache-Control: no-store. Asking the browser for such a body after the page loaded waits forever (found by this test), so a hang here is turned into a crash."""
    import faulthandler
    faulthandler.dump_traceback_later(150, exit=True)
    try:
        s = serve(EXAMPLES / "bad_app")
        with NET.Runner(s.url, allow_post=r"/api/visit$") as r:
            got = {mode: r.visit(mode)[0] for mode in NET.MODES}
    finally:
        faulthandler.cancel_dump_traceback_later()
    posts = [e for e in got["record"].responses if e["method"] == "POST"]
    assert len(posts) == 1 and posts[0]["body"] == "{}" and posts[0]["status"] == 200, posts
    assert all(v.ok for v in got.values()), {m: v.error for m, v in got.items()}
    assert s.log["writes"].count("POST /api/visit") >= 1


# ------------------------------------------------------------------------------------------------ saved visits, setup steps
def test_a_saved_visit_is_reused_and_fresh_opens_the_page_again(tmp_path, serve):
    s = serve(EXAMPLES / "good_app")
    sess = tmp_path / "sess"
    n = lambda: sum(1 for r in s.log["reads"] if r.endswith("/api/requirements"))          # noqa: E731
    with NET.Runner(s.url) as r:
        CK.trace(sess, r, "data-analyst")
        assert n() == 1
        CK.trace(sess, r, "data-analyst")
        assert n() == 1, "the saved visit was not reused"
        saved = NET.visit_path(sess, "record")
        stamp = saved.stat().st_mtime_ns
        CK.marks(sess, r, "ui-ux")                                   # starts from the same record visit and must not open the page again for it
        assert saved.stat().st_mtime_ns == stamp, "another check opened the record visit again"
        before = n()
        CK.trace(sess, r, "data-analyst", fresh=True)
        assert n() == before + 1, "--fresh did not open the page again"


def test_setup_steps_reach_data_behind_a_click(tmp_path, serve):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"><title>t</title></head><body><button id="b">Load data</button><table id="t"></table>'
                                    '<script>document.getElementById("b").onclick = async () => { const rows = await (await fetch("/api/requirements")).json(); '
                                    'document.getElementById("t").innerHTML = rows.map(r => "<tr><td></td></tr>").join(""); rows.forEach((r, i) => { document.getElementById("t").rows[i].cells[0].textContent = r.uid; }); };</script></body></html>', encoding="utf-8")
    s = serve(app)
    plain = run_checks(s.url, tmp_path / "a", names=("trace",))["trace"]
    assert "trace.no-data-requests" in ids(plain) and plain["counts"]["values"] == 0
    reached = run_checks(s.url, tmp_path / "b", names=("trace",), setup=["click:Load data"])["trace"]
    assert reached["counts"]["data_responses"] == 1 and reached["counts"]["bound"] == 8 and "trace.no-data-requests" not in ids(reached)


def test_a_page_that_asks_for_no_data_is_said_to_have_none(tmp_path, serve):
    app = tmp_path / "app"
    app.mkdir()
    (app / "index.html").write_text('<!doctype html><html><head><meta charset="utf-8"><title>t</title></head><body><p>LMP-0001 The lamp shall report its voltage every 30 seconds always.</p></body></html>', encoding="utf-8")
    s = serve(app)
    res = run_checks(s.url, tmp_path / "sess", names=("trace", "canary", "outage"))
    assert res["trace"]["verdict"] == "problem" and "trace.no-data-requests" in ids(res["trace"])
    assert res["canary"]["verdict"] == "not-run" and res["outage"]["verdict"] == "not-run", "a check with nothing to change must not say clear"


def test_a_page_that_does_not_open_is_not_clear(tmp_path):
    with NET.Runner("http://127.0.0.1:9/", timeout_ms=3000) as r:
        res = CK.trace(tmp_path / "sess", r, "data-analyst")
    assert res["verdict"] == "not-run" and "did not open" in res["summary"]


# ------------------------------------------------------------------------------------------------ a driver that only copies what is printed
def drive(session, cwd, limit=24):
    """Run `next`, then exactly the command it prints, until it says every check has run and the brief is up to date. Nothing else."""
    log = []
    for _ in range(limit):
        out = subprocess.run([sys.executable, "design/data_audit/scripts/audit.py", "next", session], cwd=cwd, capture_output=True, text=True)
        assert out.returncode == 0, out.stderr
        text = out.stdout
        if "up to date" in text:
            return log
        m = re.search(r"^  Run:  (python3 .*)$", text, flags=re.M)
        if "needs from the person" in text:
            m = re.search(r"^\s+(python3 .* skip .*)$", text, flags=re.M)
        assert m, text
        cmd = m.group(1)
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        assert r.returncode == 0, (cmd, r.stderr, r.stdout[-400:])
        log.append(cmd.split("audit.py")[1].split()[0])
    raise AssertionError("did not finish: %s" % log)


def test_a_driver_that_only_copies_the_printed_commands_gets_a_brief(tmp_path, serve):
    s = serve(EXAMPLES / "bad_app")
    sess = tmp_path / "sess"
    init = subprocess.run([sys.executable, "design/data_audit/scripts/audit.py", "init", str(sess), "--page", s.url, "--data", str(SRV.DATA), "--source", str(EXAMPLES / "bad_app")],
                          cwd=REPO, capture_output=True, text=True)
    assert init.returncode == 0, init.stderr
    before = {p: p.stat().st_mtime_ns for p in KIT.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    log = drive(str(sess), REPO)
    assert log == ["run"] * 7 + ["skip", "brief"], log
    brief = (sess / "BRIEF.md").read_text(encoding="utf-8")
    assert "BLOCKED" in brief and "Values written into the page" in brief and "does not mean the screen is right" in brief
    assert "**diff**: skipped" in brief
    assert s.log["writes"] == []
    ver = subprocess.run([sys.executable, "design/data_audit/scripts/audit.py", "verify", str(sess)], cwd=REPO, capture_output=True, text=True)
    assert ver.returncode == 0, ver.stdout
    minutes = (sess / "MINUTES.md").read_text(encoding="utf-8")
    assert "ran: Ran trace" in minutes and "brief: Brief written: blocked" in minutes
    after = {p: p.stat().st_mtime_ns for p in KIT.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    assert after == before, "the audit changed a file of the kit: %s" % sorted(str(p) for p in set(before) ^ set(after) | {p for p in before if before[p] != after.get(p)})
    assert REPO not in sess.resolve().parents, "the session folder sits inside the repository"


# ------------------------------------------------------------------------------------------------ after the independent review: the ways a page can still write or hang the audit
import http.server  # noqa: E402
import socket  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402


class Listener:
    """A raw TCP port that only counts who connects. A WebSocket the audit let through would show up here."""

    def __init__(self):
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(8)
        self.port = self.sock.getsockname()[1]
        self.connections = 0
        self._t = threading.Thread(target=self._run, daemon=True)
        self._t.start()

    def _run(self):
        while True:
            try:
                c, _ = self.sock.accept()
            except OSError:
                return
            self.connections += 1
            c.close()

    def close(self):
        self.sock.close()


class Site:
    """A server for one test page: `pages` maps a path to (content type, body). It records every request by its method as sent (so `patch` stays lower case), answers every
    write with 200 and `Cache-Control: no-store`, and keeps /events open as an event stream until it is closed."""

    def __init__(self, pages, port=0):
        self.log = {"reads": [], "writes": []}
        self.stop = threading.Event()
        site = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a, **k):
                pass

            def _send(self, status, ctype, body):
                self.send_response(status)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                site.log["reads"].append("GET " + self.path)
                path = self.path.split("?")[0]
                if path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    try:
                        self.wfile.write(b"data: LMP-0042 The lamp shall switch off within 2 seconds of a trip.\n\n")
                        self.wfile.flush()
                        while not site.stop.wait(0.2):
                            self.wfile.write(b": still here\n\n")
                            self.wfile.flush()
                    except OSError:
                        pass
                    return
                if path in site.pages:
                    ctype, body = site.pages[path]
                    self._send(200, ctype, body if isinstance(body, bytes) else body.encode("utf-8"))
                else:
                    self._send(404, "text/plain", b"not found")

            def _write(self):
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    self.rfile.read(n)
                site.log["writes"].append("%s %s" % (self.command, self.path))
                self._send(200, "application/json", b"{}")

            def __getattr__(self, name):                                  # any other method, in any case: it is a write
                if name.startswith("do_"):
                    return self._write
                raise AttributeError(name)

        self.pages = dict(pages)
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.port = self.httpd.server_address[1]
        self.url = "http://127.0.0.1:%d/" % self.port

    def close(self):
        self.stop.set()
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def site():
    made = []

    def make(pages, port=0):
        s = Site(pages, port)
        made.append(s)
        return s
    yield make
    for s in made:
        s.close()


@pytest.fixture
def listener():
    made = []

    def make():
        l = Listener()
        made.append(l)
        return l
    yield make
    for l in made:
        l.close()


HTML = "text/html; charset=utf-8"
JSON = "application/json"
DATA_BYTES = SRV.DATA.read_bytes()


def page(body, script=""):
    return '<!doctype html><html><head><meta charset="utf-8"><title>t</title></head><body>%s<script>%s</script></body></html>' % (body, script)


def test_a_socket_a_worker_a_service_worker_a_form_in_a_frame_and_a_lower_case_method_cannot_write(site, listener, tmp_path):
    raw = listener()
    script = """
try { const ws = new WebSocket("ws://127.0.0.1:%(port)d/ws"); ws.onopen = () => ws.send("write"); } catch (e) {}
try { new Worker(URL.createObjectURL(new Blob(['const s = new WebSocket("ws://127.0.0.1:%(port)d/w"); s.onopen = () => s.send("x"); fetch("/api/from-worker", {method: "POST", body: "{}"});'], {type: "text/javascript"}))); } catch (e) {}
if (navigator.serviceWorker) navigator.serviceWorker.register("/sw.js").catch(() => {});
fetch("/api/patch", {method: "patch", body: "{}"}).catch(() => {});
setTimeout(() => document.getElementById("f").submit(), 200);
""" % {"port": raw.port}
    body = '<p>Channels</p><iframe name="fr" style="width:10px;height:10px"></iframe><form id="f" method="post" action="/api/form" target="fr"><input name="a" value="1"></form>'
    s = site({"/": (HTML, page(body, script)),
              "/sw.js": ("text/javascript", "self.addEventListener('install', () => fetch('/api/from-sw', {method: 'POST', body: 'x'}));")})
    res = run_checks(s.url, tmp_path / "sess", names=("trace",))["trace"]
    time.sleep(0.5)
    assert s.log["writes"] == [], "the server received: %s" % s.log["writes"]
    assert raw.connections == 0, "something connected to the socket's address"
    rec = NET.load_visit(tmp_path / "sess", "record")
    assert rec.ok and len(rec.sockets) >= 1 and rec.sockets[0].endswith("/ws"), rec.sockets
    assert rec.refused_features == ["web worker"], rec.refused_features
    assert {"trace.socket.1", "trace.refused.1"} <= set(ids(res)), ids(res)
    assert {b["method"] for b in rec.blocked} >= {"PATCH", "POST"} or any(b["method"].upper() == "PATCH" for b in rec.blocked), rec.blocked


def test_a_request_nobody_reads_and_an_event_stream_do_not_hang_the_audit(site, tmp_path):
    """Found by the reviewer: a no-store answer that the page never reads, and a stream that never ends, kept the audit waiting for ever."""
    import faulthandler
    faulthandler.dump_traceback_later(150, exit=True)
    try:
        s = site({"/": (HTML, page('<p id="o">waiting</p>', 'fetch("/api/requirements"); const es = new EventSource("/events"); es.onmessage = e => { document.getElementById("o").textContent = e.data; };')),
                  "/api/requirements": (JSON, DATA_BYTES)})
        t0 = time.monotonic()
        with NET.Runner(s.url) as r:
            v, _ = r.visit("record")
        took = time.monotonic() - t0
    finally:
        faulthandler.cancel_dump_traceback_later()
    assert v.ok, v.error
    assert took < 40, "took %.0f s" % took
    data = v.data_responses()
    assert len(data) == 1 and "LMP-0001" in data[0]["body"], "the answer nobody read was still kept"
    assert any(r["type"] == "eventsource" for r in v.responses)


@pytest.mark.parametrize("name,body,script", [
    ("an event stream", '<p id="o">waiting</p>', 'new EventSource("/events").onmessage = e => { document.getElementById("o").textContent = e.data; };'),
    ("a web socket", "<p>LMP-0042 The lamp shall switch off within 2 seconds of a trip.</p>", 'try { new WebSocket("ws://127.0.0.1:9/feed"); } catch (e) {}'),
])
def test_a_page_that_gets_its_data_over_a_stream_is_told_apart_from_one_that_gets_none(site, tmp_path, name, body, script):
    s = site({"/": (HTML, page(body, script))})
    res = run_checks(s.url, tmp_path / "sess", names=("trace",))["trace"]
    assert "trace.stream-only" in ids(res) and "trace.no-data-requests" not in ids(res), (name, ids(res))
    assert next(f for f in res["findings"] if f["id"] == "trace.stream-only")["severity"] == "medium"


def test_a_footer_that_says_error_log_is_not_a_sign_about_the_data(tmp_path, serve):
    app = tmp_path / "app"
    shutil.copytree(EXAMPLES / "bad_app", app)
    index = (app / "index.html").read_text(encoding="utf-8")
    (app / "index.html").write_text(index.replace("</body>", '<footer><a href="#">Error log</a> <a href="#">Network error history</a> <a href="#">Offline help</a></footer></body>'), encoding="utf-8")
    s = serve(app)
    o = run_checks(s.url, tmp_path / "sess", names=("outage",))["outage"]
    assert any(f["id"].endswith("-warm.stale") and f["severity"] == "high" for f in o["findings"]), [(f["severity"], f["id"]) for f in o["findings"]]


def test_a_screen_in_a_closed_shadow_root_is_said_not_to_have_been_seen(site, tmp_path):
    body = '<div id="h"></div>'
    script = 'fetch("/api/requirements"); const r = document.getElementById("h").attachShadow({mode: "closed"}); r.innerHTML = "<p>LMP-0042 The lamp shall switch off within 2 seconds of a trip.</p>";'
    s = site({"/": (HTML, page(body, script)), "/api/requirements": (JSON, DATA_BYTES)})
    res = run_checks(s.url, tmp_path / "sess", names=("trace", "canary", "outage"))
    assert "trace.nothing-seen" in ids(res["trace"]) and next(f for f in res["trace"]["findings"] if f["id"] == "trace.nothing-seen")["severity"] == "medium"
    assert res["canary"]["verdict"] == "not-run" and res["outage"]["verdict"] == "not-run"
    assert res["trace"]["verdict"] != "clear"


def test_what_is_inside_a_frame_is_read(site, tmp_path):
    frame = page('<p id="p"></p>', 'fetch("/api/requirements").then(r => r.json()).then(rows => { document.getElementById("p").textContent = rows[0].uid; });')
    s = site({"/": (HTML, page('<iframe src="/frame.html" style="width:400px;height:100px"></iframe>')), "/frame.html": (HTML, frame), "/api/requirements": (JSON, DATA_BYTES)})
    res = run_checks(s.url, tmp_path / "sess", names=("trace",))["trace"]
    assert "trace.nothing-seen" not in ids(res) and res["counts"]["bound"] >= 1 and res["counts"]["typed"] == 0, res["counts"]


def test_a_response_bigger_than_the_audit_keeps_is_said_not_to_have_been_searched(tmp_path, serve, monkeypatch):
    monkeypatch.setattr(NET, "BODY_CAP", 200)
    s = serve(EXAMPLES / "good_app")
    res = run_checks(s.url, tmp_path / "sess", names=("trace",))["trace"]
    assert "trace.too-big" in ids(res) and res["verdict"] != "clear"
    assert NET.load_visit(tmp_path / "sess", "record").truncated


def test_data_drawn_late_is_seen_only_when_the_audit_is_told_to_wait(site, tmp_path):
    late = page('<p id="o"></p>', 'setTimeout(() => fetch("/api/requirements").then(r => r.json()).then(rows => { document.getElementById("o").textContent = rows[0].uid; }), 2500);')
    s = site({"/": (HTML, late), "/api/requirements": (JSON, DATA_BYTES)})
    quick = run_checks(s.url, tmp_path / "a", names=("trace",))["trace"]
    assert quick["counts"]["data_responses"] == 0, "the default wait is 0.8 s"
    patient = run_checks(s.url, tmp_path / "b", names=("trace",), settle_ms=3500)["trace"]
    assert patient["counts"]["data_responses"] == 1 and patient["counts"]["bound"] >= 1 and patient["counts"]["typed"] == 0, patient["counts"]


KEYED = {"byId": {"PMP-0012": {"text": "The pump shall stop when the tank level is below 10 percent of capacity.", "owner": "Ana"},
                  "PMP-0013": {"text": "The pump shall start when the tank level is above 40 percent of capacity.", "owner": "Ben"},
                  "PMP-0014": {"text": "The valve shall close within 5 seconds of a pump trip.", "owner": "Cy"}},
         "order": ["PMP-0012", "PMP-0013", "PMP-0014"]}


def test_records_held_by_id_in_the_data_are_not_called_typed_in_or_stuck(site, tmp_path):
    script = """fetch("/api/requirements").then(r => r.json()).then(d => { const t = document.getElementById("t");
      for (const id of d.order) { const tr = t.insertRow(); for (const v of [id, d.byId[id].text, d.byId[id].owner]) tr.insertCell().textContent = v; } });"""
    s = site({"/": (HTML, page('<table id="t"></table>', script)), "/api/requirements": (JSON, json.dumps(KEYED))})
    res = run_checks(s.url, tmp_path / "sess", names=("trace", "canary"))
    assert not [f for f in res["trace"]["findings"] if f["id"].startswith("trace.typed")], res["trace"]["findings"]
    assert res["canary"]["counts"]["stayed"] == 0 and res["canary"]["counts"]["followed"] >= 3 and res["canary"]["verdict"] == "clear", (res["canary"]["counts"], ids(res["canary"]))


def test_a_page_that_turns_the_numbers_into_its_own_words_is_not_called_connected(site, tmp_path):
    data = json.dumps([{"uid": "LMP-0001", "pct": 12}, {"uid": "LMP-0002", "pct": 35}, {"uid": "LMP-0003", "pct": 58}, {"uid": "LMP-0004", "pct": 71}])
    script = """fetch("/api/requirements").then(r => r.json()).then(rows => { const t = document.getElementById("t");
      for (const r of rows) t.insertRow().insertCell().textContent = r.pct > 100 ? "n/a" : String(r.pct); });"""
    s = site({"/": (HTML, page('<table id="t"></table>', script)), "/api/requirements": (JSON, data)})
    c = run_checks(s.url, tmp_path / "sess", names=("canary",))["canary"]
    none = [f for f in c["findings"] if f["id"] == "canary.none-reached"]
    assert none and none[0]["severity"] == "medium", (ids(c), c["counts"])


def test_a_page_that_sends_the_browser_to_a_refused_address_is_not_clear(site, tmp_path):
    s = site({"/": (HTML, page('<p>Please wait</p><form id="f" method="post" action="/api/form"><input name="a" value="1"></form>', 'document.getElementById("f").submit();'))})
    with NET.Runner(s.url) as r:
        res = CK.trace(tmp_path / "sess", r, "data-analyst")
    assert s.log["writes"] == []
    assert res["verdict"] == "not-run" and "left for an address" in res["summary"], res["summary"]


def test_a_stored_sign_in_is_private_and_a_visit_that_failed_is_tried_again(site, tmp_path):
    first = site({"/": (HTML, page("<p>x</p>"))})
    port = first.port
    first.close()
    sess = tmp_path / "sess"
    with NET.Runner("http://127.0.0.1:%d/" % port, timeout_ms=3000) as r:
        down = CK.trace(sess, r, "data-analyst")
    assert down["verdict"] == "not-run" and NET.load_visit(sess, "record").ok is False
    again = site({"/": (HTML, page('<p id="o"></p>', 'fetch("/api/requirements").then(r => r.json()).then(rows => { document.getElementById("o").textContent = rows[0].uid; });')),
                  "/api/requirements": (JSON, DATA_BYTES)}, port=port)
    with NET.Runner(again.url) as r:
        up = CK.trace(sess, r, "data-analyst")
    assert up["verdict"] != "not-run" and NET.load_visit(sess, "record").ok, "the failed visit was reused"
    mode = (sess / "visits" / "storage.json").stat().st_mode & 0o777
    assert mode == 0o600, oct(mode)
