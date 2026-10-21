"""What the connected page needs from the reference server: lead-only settings, labels that are the labeller's own, a seeded demo project, the page served from
the same origin, and the demo command. Real HTTP on a loopback port and a real SQLite file, as in test_server.py."""
from __future__ import annotations

import http.client
import json
import os
from pathlib import Path

import pytest

from reqin.server import ServerError, Store
from reqin.server.demo import SEED_FORMAT, load_seed, make_demo
from reqin.server.http import make_server, serve_in_thread

PEOPLE = [
    {"key": "sam", "name": "Sam Okafor", "role": "reviewer", "lens": "SE"},
    {"key": "priya", "name": "Priya Raman", "role": "reviewer", "lens": "PE"},
    {"key": "morgan", "name": "Morgan Hale", "role": "lead", "lens": "SE"},
    {"key": "lee", "name": "Lee Park", "role": "observer", "lens": ""},
]


@pytest.fixture()
def world(tmp_path: Path):
    st = Store(tmp_path / "s.db")
    tokens = st.init_project("demo", PEOPLE)
    yield st, {k: st.who(t) for k, t in tokens.items()}, tokens, tmp_path
    st.close()


def err(fn, *a, **kw) -> ServerError:
    with pytest.raises(ServerError) as e:
        fn(*a, **kw)
    return e.value


# ---------------------------------------------------------------- lead-only documents
@pytest.mark.parametrize("doc", ["proj/ai", "adj/CL-001", "gadj/REQ-A/REQ-B"])
def test_project_settings_and_rulings_are_for_a_lead(world, doc):
    st, who, *_ = world
    for k in ("sam", "priya"):
        assert err(st.put, who[k], doc, {"on": True}, 0).code == "lead_only"
    assert err(st.put, who["lee"], doc, {"on": True}, 0).code == "observer"
    status, r = st.put(who["morgan"], doc, {"on": True}, 0)
    assert status == 201 and r["rev"] == 1
    assert err(st.put, who["sam"], doc, None, 1).code == "lead_only", "a reviewer cannot withdraw it either"
    assert st.put(who["morgan"], doc, {"on": False}, 1)[1]["rev"] == 2


def test_anyone_with_a_lens_can_raise_an_objection_and_only_a_lead_closes_it(world):
    st, who, *_ = world
    assert st.put(who["priya"], "obj/CL-001", {"by": "Priya Raman", "note": "the value is looser"}, 0)[1]["rev"] == 1
    assert err(st.put, who["lee"], "obj/CL-002", {"note": "x"}, 0).code == "observer"
    assert err(st.put, who["priya"], "obj/CL-001", None, 1).code == "lead_only", "the person who raised it cannot close it"
    assert err(st.put, who["sam"], "obj/CL-001", None, 1).code == "lead_only"
    assert st.put(who["morgan"], "obj/CL-001", None, 1)[1]["rev"] == 2


def test_a_label_can_only_be_written_under_the_labellers_own_key(world):
    st, who, *_ = world
    mine, theirs = "label/REQ-A/REQ-B/sam", "label/REQ-A/REQ-B/priya"
    assert st.put(who["sam"], mine, {"v": "dup"}, 0)[1]["rev"] == 1
    e = err(st.put, who["sam"], theirs, {"v": "dup"}, 0)
    assert (e.status, e.code) == (403, "not_yours")
    assert err(st.put, who["sam"], theirs, None, 0).code == "not_yours"
    assert err(st.put, who["morgan"], mine, {"v": "dup"}, 1).code == "not_yours", "not even a lead writes another person's label"
    assert err(st.put, who["sam"], "label/REQ-A/sam", {"v": "dup"}, 0).code == "bad_label_id"
    assert err(st.put, who["sam"], "label/REQ-A/REQ-B", {"v": "dup"}, 0).code == "bad_label_id", "a kind and two requirement ids is one part short"
    assert st.put(who["sam"], mine, {"v": "diff", "note": "n"}, 1)[1]["rev"] == 2
    assert st.put(who["sam"], mine, None, 2)[1]["rev"] == 3


# ---------------------------------------------------------------- the seed
def _seed_docs():
    return [
        {"id": "dec/CL-001", "by": "sam", "body": {"outcome": "merge", "by": "Sam Okafor"}},
        {"id": "sign/CL-001/PE", "by": "priya", "body": {"by": "Priya Raman", "rev": 1, "page_rev": "R3"}},
        {"id": "proj/ai", "by": "morgan", "body": {"on": False}},
    ]


def test_a_seeded_project_looks_worked_on_and_its_record_checks_out(world):
    st, who, *_ = world
    assert st.seed("demo", _seed_docs()) == 3
    d = st.get(who["lee"], "dec/CL-001")
    assert (d["rev"], d["by"], d["lens"], d["body"]["outcome"]) == (1, "sam", "SE", "merge")
    assert st.get(who["sam"], "sign/CL-001/PE")["by"] == "priya"
    ev = [e for e in st.events(who["sam"])["events"] if e["type"] == "doc"]
    assert [e["target"] for e in ev] == ["dec/CL-001", "sign/CL-001/PE", "proj/ai"] and ev[0]["text"] == "Sample activity: dec/CL-001" and ev[0]["actor"] == "sam"
    assert st.verify("demo")["ok"] is True


def test_a_seeded_document_is_changed_by_the_ordinary_rules(world):
    st, who, *_ = world
    st.seed("demo", _seed_docs())
    assert err(st.put, who["sam"], "dec/CL-001", {"outcome": "link"}, 0).code == "conflict"
    status, r = st.put(who["sam"], "dec/CL-001", {"outcome": "link"}, 1)
    assert status == 201 and r["rev"] == 2 and r["cleared"] == ["sign/CL-001/PE"], "a new revision of a decision clears the seeded sign-off on the old one"
    assert st.get(who["sam"], "sign/CL-001/PE")["body"] is None
    assert err(st.put, who["priya"], "sign/CL-001/PE", {"by": "Priya Raman", "rev": 1}, 2).code == "stale_signoff", "and a sign-off must name the new revision"
    assert st.put(who["priya"], "sign/CL-001/PE", {"by": "Priya Raman", "rev": 2}, 2)[0] == 201
    assert st.verify("demo")["ok"]


def test_a_seed_is_refused_where_it_could_overwrite_or_confuse(world):
    st, who, tokens, tmp = world
    assert err(st.seed, "nope", _seed_docs()).code == "no_project"
    for bad in ([{"id": "dec/CL-001", "by": "lee", "body": {}}],                      # an observer cannot have written it
                [{"id": "dec/CL-001", "by": "ghost", "body": {}}],                    # not in the project
                [{"id": "dec/CL-001", "by": ["sam"], "body": {}}],                    # not even a name
                [{"id": "dec/CL-001", "by": "sam", "body": None}],                    # a seed holds documents, not withdrawals
                [{"id": "dec/CL-001", "by": "sam", "body": []}],
                [{"id": "Dec/CL-001", "by": "sam", "body": {}}],                      # a document id that is not one
                [{"id": 5, "by": "sam", "body": {}}],
                [{"id": "dec/CL-001", "by": "sam", "body": {}, "rev": 9}],            # a field the seed does not have
                [{"id": "dec/CL-001", "by": "sam", "body": {}}, {"id": "dec/CL-001", "by": "sam", "body": {}}],
                "not a list"):
        e = err(st.seed, "demo", bad)
        assert e.code in ("bad_seed", "bad_doc_id"), bad
    assert st.list(who["sam"])["docs"] == [] and st.verify("demo")["entries"] == 1, "a refused seed leaves nothing behind, not even the documents before the bad one"
    big = [{"id": "dec/CL-001", "by": "sam", "body": {"t": "x" * 70000}}]
    assert err(st.seed, "demo", big).code == "too_large"
    assert st.seed("demo", _seed_docs()) == 3
    assert err(st.seed, "demo", _seed_docs()).code == "not_empty", "a project with documents is never seeded again"
    assert st.verify("demo")["ok"]


def test_a_seed_never_reaches_another_project(world):
    st, who, *_ = world
    other = st.init_project("other", [{"key": "sam", "name": "Sam", "role": "lead", "lens": "SE"}])
    st.seed("demo", _seed_docs())
    assert st.list(st.who(other["sam"]))["docs"] == []


# ---------------------------------------------------------------- the demo files
def _seed_file(tmp: Path, **over) -> Path:
    seed = {"format": SEED_FORMAT, "project": "demo", "people": PEOPLE, "docs": _seed_docs()}
    seed.update(over)
    p = tmp / "seed.json"
    p.write_text(json.dumps(seed))
    return p


def test_a_seed_file_is_checked_before_anything_is_made(tmp_path):
    assert load_seed(_seed_file(tmp_path))["project"] == "demo"
    assert err(load_seed, tmp_path / "missing.json").code == "bad_seed"
    for over in ({"format": "other/1"}, {"project": "Bad Id"}, {"people": "sam"}, {"docs": {}}):
        assert err(load_seed, _seed_file(tmp_path, **over)).code == "bad_seed", over
    junk = tmp_path / "junk.json"; junk.write_text("{not json")
    assert err(load_seed, junk).code == "bad_seed"
    st = Store(tmp_path / "x.db")
    project, tokens, n = make_demo(st, _seed_file(tmp_path))
    assert (project, set(tokens), n) == ("demo", {p["key"] for p in PEOPLE}, 3)
    st.close()


def test_the_demo_command_makes_the_project_and_will_not_reuse_a_database(tmp_path, capsys, monkeypatch):
    from reqin.server import __main__ as m
    app = tmp_path / "app"; app.mkdir(); (app / "Main.dc.html").write_text("<html>page</html>")
    db = str(tmp_path / "demo.db")
    started = {}

    class Stop(Exception):
        pass

    real = m.make_server

    def fake(st, host, port, allow_remote, log=None, app_dir=None):
        srv = real(st, host, 0, allow_remote, log, app_dir)
        started["srv"] = srv
        srv.serve_forever = lambda: (_ for _ in ()).throw(KeyboardInterrupt())   # stand in for Ctrl-C
        return srv

    monkeypatch.setattr(m, "make_server", fake)
    assert m.main(["demo", "--db", db, "--seed", str(_seed_file(tmp_path)), "--app", str(app)]) == 0
    out = capsys.readouterr().out
    tok = tmp_path / "demo.db.tokens.json"
    assert "3 sample documents" in out and "/app/" in out and oct(tok.stat().st_mode & 0o777) == "0o600"
    tokens = json.loads(tok.read_text())
    assert all(t not in out for t in tokens.values()), "tokens go to the file and never to the screen"
    st = Store(db)
    assert st.who(tokens["sam"]).key == "sam" and st.verify("demo")["ok"]
    st.close()
    assert m.main(["demo", "--db", db, "--seed", str(_seed_file(tmp_path)), "--app", str(app)]) == 2, "an existing database is never reused"
    assert "already exists" in capsys.readouterr().err
    # a wrong folder, a bad seed: nothing is left behind
    db2 = str(tmp_path / "d2.db")
    assert m.main(["demo", "--db", db2, "--seed", str(_seed_file(tmp_path)), "--app", str(tmp_path / "nowhere")]) == 2
    assert not os.path.exists(db2) and not os.path.exists(db2 + ".tokens.json")
    assert m.main(["demo", "--db", db2, "--seed", str(tmp_path / "nope.json"), "--app", str(app)]) == 2
    assert not os.path.exists(db2) and not os.path.exists(db2 + ".tokens.json")


def test_init_can_seed_a_new_project(tmp_path, capsys):
    from reqin.server.__main__ import main
    people = tmp_path / "people.json"; people.write_text(json.dumps(PEOPLE))
    db = str(tmp_path / "i.db")
    assert main(["init", "--db", db, "--project", "demo", "--people", str(people), "--seed", str(_seed_file(tmp_path)), "--tokens-out", str(tmp_path / "t.json")]) == 0
    st = Store(db)
    assert st.verify("demo")["entries"] == 1 + 3
    st.close()


# ---------------------------------------------------------------- the page, served from the same origin
@pytest.fixture()
def served(world):
    st, who, tokens, tmp = world
    app = tmp / "app"
    (app / "fonts").mkdir(parents=True)
    (app / "Main.dc.html").write_text("<!doctype html><title>page</title>")
    (app / "support.js").write_text("window.x=1")
    (app / "fonts" / "a.woff2").write_bytes(b"wOF2")
    (app / ".env").write_text("SECRET=1")
    (app / ".keys.js").write_text("SECRET=1")                       # a dot file with a type that would otherwise be served
    (app / ".hidden").mkdir(); (app / ".hidden" / "x.js").write_text("SECRET=1")
    (app / "notes.py").write_text("print(1)")
    (app / "noext").write_text("x")
    (tmp / "outside.js").write_text("secret()")
    (tmp / "outdir").mkdir(); (tmp / "outdir" / "x.js").write_text("secret()")
    (app / "link.js").symlink_to(tmp / "outside.js")
    (app / "linkdir").symlink_to(tmp / "outdir")
    srv = make_server(st, port=0, app_dir=app)
    serve_in_thread(srv)
    port = srv.server_address[1]

    def call(method, url, token=None, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        h = dict(headers or {})
        if token:
            h["Authorization"] = "Bearer " + token
        c.request(method, url, body=body, headers=h)
        r = c.getresponse()
        data = r.read()
        c.close()
        return r.status, data, r

    yield call, tokens, st
    srv.shutdown(); srv.server_close()


def test_the_page_is_served_read_only_from_the_app_folder(served):
    call, tokens, _ = served
    s, data, r = call("GET", "/app/")
    assert s == 200 and data.startswith(b"<!doctype html>") and r.getheader("Content-Type") == "text/html; charset=utf-8"
    assert r.getheader("X-Content-Type-Options") == "nosniff" and r.getheader("Cache-Control") == "no-cache" and r.getheader("Referrer-Policy") == "no-referrer"
    assert call("GET", "/app/Main.dc.html")[1] == data
    assert call("GET", "/app/support.js")[2].getheader("Content-Type").startswith("text/javascript")
    assert call("GET", "/app/fonts/a.woff2")[0] == 200
    s, _, r = call("GET", "/")
    assert s == 302 and r.getheader("Location") == "/app/"
    assert call("GET", "/app")[2].getheader("Location") == "/app/"
    s, body, r = call("HEAD", "/app/support.js")
    assert s == 200 and body == b"" and r.getheader("Content-Length") == str(len("window.x=1"))
    assert call("GET", "/app/Main.dc.html", token="not even looked at")[0] == 200, "the page holds no project data, so it asks for no token"


@pytest.mark.parametrize("path", ["/app/.env", "/app/.keys.js", "/app/notes.py", "/app/noext", "/app/missing.js", "/app/../outside.js", "/app/%2e%2e/outside.js", "/app/..%2foutside.js",
                                  "/app/fonts/../../outside.js", "/app/fonts/", "/app/fonts", "/app//Main.dc.html", "/app/link.js", "/app/linkdir/x.js", "/app/%00.js", "/app/a%5cb.js", "/app/.hidden/x.js"])
def test_nothing_else_leaves_the_app_folder(served, path):
    call, *_ = served
    s, data, _ = call("GET", path)
    assert s in (404, 400) and b"secret" not in data and b"SECRET" not in data and b"print(1)" not in data


def test_the_page_cannot_be_changed_through_the_server(served):
    call, *_ = served
    for m in ("PUT", "POST", "DELETE", "PATCH"):
        assert call(m, "/app/Main.dc.html", body=b"x")[0] == 405


def test_the_api_still_works_beside_the_page_and_still_needs_a_token(served):
    call, tokens, _ = served
    assert call("GET", "/v1/health")[0] == 200
    assert call("GET", "/v1/me")[0] == 401
    s, data, _ = call("GET", "/v1/me", tokens["sam"])
    assert s == 200 and json.loads(data)["key"] == "sam"


def test_without_an_app_folder_there_is_no_page(world):
    st, *_ = world
    srv = make_server(st, port=0)
    serve_in_thread(srv)
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    for path in ("/", "/app/", "/app/Main.dc.html"):
        c.request("GET", path)
        r = c.getresponse(); r.read()
        assert r.status == 404
    c.close(); srv.shutdown(); srv.server_close()


def test_an_app_folder_without_the_page_is_refused(world, tmp_path):
    st, *_ = world
    empty = tmp_path / "empty"; empty.mkdir()
    assert err(make_server, st, port=0, app_dir=empty).code == "bad_app_dir"
    assert err(make_server, st, port=0, app_dir=tmp_path / "nowhere").code == "bad_app_dir"


def test_a_refused_request_does_not_let_its_body_pass_for_the_next_request(world):
    """The body of a refused request is never read, so the connection is closed: otherwise a body that looks like a request line would be answered."""
    import socket
    st, *_ = world
    srv = make_server(st, port=0)
    serve_in_thread(srv)
    smuggled = b"GET /v1/health HTTP/1.1\r\nHost: x\r\n\r\n"
    raw = b"PUT /v1/health HTTP/1.1\r\nHost: x\r\nContent-Length: " + str(len(smuggled)).encode() + b"\r\n\r\n" + smuggled
    with socket.create_connection(("127.0.0.1", srv.server_address[1]), timeout=5) as c:
        c.sendall(raw)
        got = b""
        while True:
            chunk = c.recv(4096)
            if not chunk:
                break
            got += chunk
    assert got.count(b"HTTP/1.1 ") == 1 and got.startswith(b"HTTP/1.1 405") and b"Connection: close" in got, got
    srv.shutdown(); srv.server_close()


def test_the_server_runs_with_only_the_standard_library(tmp_path):
    """`python -S -I` hides every installed package, so this fails if the server ever imports one (or runs reqin's own __init__)."""
    import subprocess
    import sys
    script = Path(__file__).resolve().parents[1] / "serve_standalone.py"
    people = tmp_path / "people.json"; people.write_text(json.dumps(PEOPLE))
    db = str(tmp_path / "bare.db")
    run = lambda *a: subprocess.run([sys.executable, "-S", "-I", str(script), *a], capture_output=True, text=True, timeout=60)
    r = run("init", "--db", db, "--project", "demo", "--people", str(people), "--tokens-out", str(tmp_path / "t.json"))
    assert r.returncode == 0, r.stderr
    r = run("verify", "--db", db, "--project", "demo")
    assert r.returncode == 0 and json.loads(r.stdout)["ok"] is True, r.stderr
