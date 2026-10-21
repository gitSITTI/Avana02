"""The reference server: what it promises is what these tests make it do. Real HTTP on a loopback port, a real SQLite file, no mocks."""
from __future__ import annotations

import http.client
import json
import sqlite3
import threading
from pathlib import Path

import pytest

from reqin.server import ServerError, Store
from reqin.server.http import is_loopback, make_server, serve_in_thread
from reqin.server.store import GENESIS, canon, sha256

PEOPLE = [
    {"key": "sam", "name": "Sam Okafor", "role": "reviewer", "lens": "SE"},
    {"key": "priya", "name": "Priya Raman", "role": "reviewer", "lens": "PE"},
    {"key": "jordan", "name": "Jordan Ellis", "role": "reviewer", "lens": "UX"},
    {"key": "morgan", "name": "Morgan Hale", "role": "lead", "lens": "SE"},
    {"key": "lee", "name": "Lee Park", "role": "observer", "lens": ""},
]
DEC = {"outcome": "merge", "text": "The system shall record the event within 0.2 s."}


@pytest.fixture()
def world(tmp_path: Path):
    st = Store(tmp_path / "shared.db")
    tokens = st.init_project("demo", PEOPLE)
    who = {k: st.who(t) for k, t in tokens.items()}
    yield st, tokens, who, tmp_path / "shared.db"
    st.close()


@pytest.fixture()
def live(world):
    st, tokens, who, path = world
    srv = make_server(st, port=0)
    serve_in_thread(srv)
    port = srv.server_address[1]

    def call(method, url, token=None, body=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        h = dict(headers or {})
        if token:
            h["Authorization"] = "Bearer " + token
        data = raw if raw is not None else (json.dumps(body) if body is not None else None)
        if data is not None and "Content-Type" not in h:
            h["Content-Type"] = "application/json"
        c.request(method, url, body=data, headers=h)
        r = c.getresponse()
        text = r.read().decode("utf-8")
        c.close()
        return r.status, (json.loads(text) if text else None), r

    yield call, tokens, st
    srv.shutdown()
    srv.server_close()


def put(st, who, doc, body, rev, **kw):
    return st.put(who, doc, body, rev, **kw)


def err(fn, *a, **kw) -> ServerError:
    with pytest.raises(ServerError) as e:
        fn(*a, **kw)
    return e.value


# ---------------------------------------------------------------- people and tokens
def test_tokens_are_shown_once_and_only_their_hashes_are_stored(world):
    st, tokens, who, path = world
    assert set(tokens) == {p["key"] for p in PEOPLE} and len(set(tokens.values())) == len(tokens)
    assert all(len(t) >= 40 for t in tokens.values())
    st.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    blob = path.read_bytes() + (Path(str(path) + "-wal").read_bytes() if Path(str(path) + "-wal").exists() else b"")
    assert all(t.encode() not in blob for t in tokens.values()), "a token was written to disk in the clear"


def test_a_token_names_a_person_and_nothing_else_does(world):
    st, tokens, who, _ = world
    assert (who["sam"].key, who["sam"].role, who["sam"].lens, who["sam"].project) == ("sam", "reviewer", "SE", "demo")
    assert err(st.who, None).status == 401 and err(st.who, "").status == 401
    assert err(st.who, "not-a-token").code == "bad_token"
    assert err(st.who, tokens["sam"] + "x").status == 401


def test_a_replaced_token_stops_the_old_one(world):
    st, tokens, who, _ = world
    new = st.rotate_token("demo", "sam")
    assert st.who(new).key == "sam" and err(st.who, tokens["sam"]).status == 401
    assert err(st.rotate_token, "demo", "nobody").status == 404
    assert any("Token replaced for sam" in e["text"] for e in st.events(who["morgan"])["events"])


@pytest.mark.parametrize("people,code", [
    ([], "no_people"), ([{"key": "A", "name": "x", "role": "lead", "lens": "SE"}], "bad_person"),
    ([{"key": "a", "name": "x", "role": "boss", "lens": "SE"}], "bad_role"), ([{"key": "a", "name": "x", "role": "reviewer", "lens": "QA"}], "bad_lens"),
    ([{"key": "a", "name": "x", "role": "observer", "lens": "SE"}], "bad_lens"), ([{"key": "a", "name": " ", "role": "lead", "lens": "SE"}], "bad_name"),
    ([{"key": "a", "name": "x", "role": "lead", "lens": "SE"}, {"key": "a", "name": "y", "role": "lead", "lens": "PE"}], "bad_person"),
])
def test_a_project_is_refused_when_its_people_make_no_sense(tmp_path, people, code):
    st = Store(tmp_path / "x.db")
    assert err(st.init_project, "p1", people).code == code
    assert st.db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 0


def test_a_project_is_created_once(world):
    st, *_ = world
    assert err(st.init_project, "demo", PEOPLE).code == "project_exists"
    assert err(st.init_project, "Demo!", PEOPLE).code == "bad_project"


def test_projects_do_not_see_each_other(world):
    st, tokens, who, _ = world
    other = st.init_project("other", [{"key": "sam", "name": "Sam", "role": "lead", "lens": "SE"}])
    o = st.who(other["sam"])
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert err(st.get, o, "dec/CL-001").status == 404 and st.list(o)["docs"] == []
    put(st, o, "dec/CL-001", {"outcome": "link"}, 0)
    assert st.get(who["sam"], "dec/CL-001")["body"] == DEC
    assert all(e["target"] != "dec/CL-001" for e in st.events(o)["events"][:1])
    assert st.verify("demo")["ok"] and st.verify("other")["ok"]


# ---------------------------------------------------------------- revisions: no silent overwrite
def test_a_new_document_needs_revision_zero_and_the_next_needs_the_one_you_read(world):
    st, _, who, _ = world
    s, r = put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert (s, r["rev"]) == (201, 1)
    c = err(put, st, who["priya"], "dec/CL-001", {"outcome": "link"}, 0)
    assert c.status == 409 and c.code == "conflict" and c.extra["current"]["rev"] == 1 and c.extra["current"]["body"] == DEC and c.extra["current"]["by"] == "sam"
    assert put(st, who["priya"], "dec/CL-001", {"outcome": "link"}, 1)[1]["rev"] == 2
    assert err(put, st, who["sam"], "dec/CL-001", DEC, 1).status == 409, "a write against an old revision must be refused"
    assert st.get(who["sam"], "dec/CL-001")["body"] == {"outcome": "link"}


@pytest.mark.parametrize("bad", [None, "1", -1, 1.5, True, [], {}])
def test_a_write_must_say_which_revision(world, bad):
    st, _, who, _ = world
    assert err(put, st, who["sam"], "dec/CL-001", DEC, bad).code == "if_rev_required"
    assert err(st.get, who["sam"], "dec/CL-001").status == 404, "nothing may be written by a request without a revision"


def test_every_revision_is_kept_and_can_be_read(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", {"v": 1}, 0); put(st, who["priya"], "dec/CL-001", {"v": 2}, 1); put(st, who["sam"], "dec/CL-001", None, 2)
    h = st.history(who["lee"], "dec/CL-001")
    assert [(r["rev"], r["body"], r["by"]) for r in h] == [(1, {"v": 1}, "sam"), (2, {"v": 2}, "priya"), (3, None, "sam")]
    assert st.get(who["lee"], "dec/CL-001")["body"] is None, "a withdrawn document reads as withdrawn, and keeps its revision number"
    assert [d["id"] for d in st.list(who["lee"])["docs"]] == [] and [d["id"] for d in st.list(who["lee"], include_withdrawn=True)["docs"]] == ["dec/CL-001"]
    assert put(st, who["priya"], "dec/CL-001", {"v": 4}, 3)[1]["rev"] == 4


def test_twenty_people_writing_at_once_get_one_winner_and_nobody_is_lost(world):
    st, _, who, _ = world
    results, lock = [], threading.Lock()

    def go(i):
        try:
            r = ("ok", put(st, who["sam"], "dec/CL-009", {"n": i}, 0)[1])
        except ServerError as e:
            r = ("err", e.status)
        with lock:
            results.append(r)

    ts = [threading.Thread(target=go, args=(i,)) for i in range(20)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert [r[0] for r in results].count("ok") == 1 and all(r[1] == 409 for r in results if r[0] == "err")
    assert st.get(who["sam"], "dec/CL-009")["rev"] == 1 and st.verify("demo")["ok"]


def test_many_writers_on_different_documents_all_land_in_one_unbroken_record(world):
    st, _, who, _ = world

    def go(i):
        put(st, who["sam"], f"dec/CL-{i:03d}", {"n": i}, 0)

    ts = [threading.Thread(target=go, args=(i,)) for i in range(40)]
    [t.start() for t in ts]; [t.join() for t in ts]
    ev = st.events(who["sam"], 0, 1000)["events"]
    assert [e["seq"] for e in ev] == list(range(1, 42)) and st.verify("demo")["ok"] and len(st.list(who["sam"])["docs"]) == 40


# ---------------------------------------------------------------- who may change what
def test_the_author_is_the_token_not_the_body(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", {"outcome": "merge", "by": "morgan", "actor": "morgan", "lens": "PE"}, 0)
    d = st.get(who["sam"], "dec/CL-001")
    assert (d["by"], d["lens"]) == ("sam", "SE") and st.events(who["sam"])["events"][-1]["actor"] == "sam"
    assert err(put, st, who["sam"], "sign/CL-001/SE", {"rev": 1, "by": "priya"}, 0).code == "self_sign", "claiming to be someone else in the body does not get round the rule"


def test_an_observer_reads_and_cannot_change_anything(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert err(put, st, who["lee"], "dec/CL-002", DEC, 0).status == 403 and err(put, st, who["lee"], "dec/CL-001", None, 1).code == "observer"
    assert st.get(who["lee"], "dec/CL-001")["rev"] == 1 and st.events(who["lee"])["events"] and st.verify("demo")["ok"]


def test_a_sign_off_must_be_in_the_signers_own_lens(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert err(put, st, who["priya"], "sign/CL-001/SE", {"rev": 1}, 0).code == "wrong_lens"
    assert err(put, st, who["jordan"], "sign/CL-001/PE", {"rev": 1}, 0).code == "wrong_lens"
    assert put(st, who["priya"], "sign/CL-001/PE", {"rev": 1}, 0)[0] == 201
    got = st.get(who["sam"], "sign/CL-001/PE")
    assert got["by"] == "priya" and got["lens"] == "PE", "who signed comes from the token, not from the request"


def test_the_owner_and_adjudicator_slots_are_for_leads(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert err(put, st, who["priya"], "sign/CL-001/OWN", {"rev": 1}, 0).code == "lead_only" and err(put, st, who["priya"], "sign/CL-001/ADJ", {"rev": 1}, 0).status == 403
    assert put(st, who["morgan"], "sign/CL-001/OWN", {"rev": 1}, 0)[0] == 201 and put(st, who["morgan"], "sign/CL-001/ADJ", {"rev": 1}, 0)[0] == 201


def test_nobody_signs_a_decision_they_made(world):
    st, _, who, _ = world
    put(st, who["priya"], "dec/CL-001", DEC, 0)
    assert err(put, st, who["priya"], "sign/CL-001/PE", {"rev": 1}, 0).code == "self_sign"
    put(st, who["morgan"], "dec/CL-002", DEC, 0)
    assert err(put, st, who["morgan"], "sign/CL-002/OWN", {"rev": 1}, 0).code == "self_sign", "a lead may not sign their own decision either"
    assert put(st, who["sam"], "sign/CL-001/SE", {"rev": 1}, 0)[0] == 201


def test_a_sign_off_needs_a_decision_and_names_its_revision(world):
    st, _, who, _ = world
    assert err(put, st, who["sam"], "sign/CL-001/SE", {"rev": 1}, 0).code == "nothing_to_sign"
    put(st, who["priya"], "dec/CL-001", DEC, 0); put(st, who["priya"], "dec/CL-001", {"outcome": "link"}, 1)
    s = err(put, st, who["sam"], "sign/CL-001/SE", {"rev": 1}, 0)
    assert s.code == "stale_signoff" and s.extra["decision_rev"] == 2
    assert err(put, st, who["sam"], "sign/CL-001/SE", {}, 0).code == "stale_signoff" and err(put, st, who["sam"], "sign/CL-001/SE", {"rev": "2"}, 0).code == "stale_signoff"
    assert put(st, who["sam"], "sign/CL-001/SE", {"rev": 2}, 0)[0] == 201


def test_a_decision_made_on_a_withdrawn_decision_cannot_be_signed(world):
    st, _, who, _ = world
    put(st, who["priya"], "dec/CL-001", DEC, 0); put(st, who["priya"], "dec/CL-001", None, 1)
    assert err(put, st, who["sam"], "sign/CL-001/SE", {"rev": 2}, 0).code == "nothing_to_sign"


def test_a_new_revision_of_a_decision_clears_the_sign_offs_on_the_old_one(world):
    st, _, who, _ = world
    put(st, who["priya"], "dec/CL-001", DEC, 0)
    put(st, who["sam"], "sign/CL-001/SE", {"rev": 1}, 0); put(st, who["jordan"], "sign/CL-001/UX", {"rev": 1}, 0)
    put(st, who["priya"], "dec/CL-002", DEC, 0); put(st, who["sam"], "sign/CL-002/SE", {"rev": 1}, 0)
    s, r = put(st, who["priya"], "dec/CL-001", {"outcome": "link"}, 1)
    assert r["cleared"] == ["sign/CL-001/SE", "sign/CL-001/UX"]
    assert st.get(who["sam"], "sign/CL-001/SE")["body"] is None and st.get(who["sam"], "sign/CL-001/UX")["body"] is None
    assert st.get(who["sam"], "sign/CL-002/SE")["body"] == {"rev": 1}, "another decision's sign-offs are left alone"
    assert [d["id"] for d in st.list(who["sam"], "sign/")["docs"]] == ["sign/CL-002/SE"]
    assert put(st, who["sam"], "sign/CL-001/SE", {"rev": 2}, 2)[0] == 201, "the cleared slot can be signed again, against the new revision"
    assert any(e["actor"] == "server" and "Cleared sign/CL-001/SE" in e["text"] for e in st.events(who["sam"])["events"]) and st.verify("demo")["ok"]


def test_requirement_decisions_work_the_same_way(world):
    st, _, who, _ = world
    put(st, who["sam"], "rdec/REQ-FCS-0312", {"outcome": "keep"}, 0)
    assert err(put, st, who["sam"], "sign/REQ-FCS-0312/SE", {"rev": 1}, 0).code == "self_sign"
    assert put(st, who["priya"], "sign/REQ-FCS-0312/PE", {"rev": 1}, 0)[0] == 201
    put(st, who["sam"], "rdec/REQ-FCS-0312", {"outcome": "drop"}, 1)
    assert st.get(who["sam"], "sign/REQ-FCS-0312/PE")["body"] is None


def test_a_sign_off_can_be_withdrawn_by_its_signer_at_the_current_revision(world):
    st, _, who, _ = world
    put(st, who["priya"], "dec/CL-001", DEC, 0); put(st, who["sam"], "sign/CL-001/SE", {"rev": 1}, 0)
    assert put(st, who["sam"], "sign/CL-001/SE", None, 1)[0] == 201 and st.get(who["sam"], "sign/CL-001/SE")["body"] is None
    assert err(put, st, who["sam"], "sign/CL-001/SE", None, 1).status == 409


@pytest.mark.parametrize("slot,signer,attacker,code", [
    ("PE", "priya", "sam", "wrong_lens"),
    ("OWN", "morgan", "sam", "lead_only"),
    ("ADJ", "morgan", "priya", "lead_only"),
    ("SE", "morgan", "sam", "not_yours"),
])
def test_withdrawing_a_sign_off_requires_its_slot_and_its_signer(world, slot, signer, attacker, code):
    st, _, who, _ = world
    put(st, who["jordan"], "dec/CL-001", DEC, 0)
    doc = "sign/CL-001/" + slot
    put(st, who[signer], doc, {"rev": 1}, 0)
    head = st.events(who[signer])["head"]
    assert err(put, st, who[attacker], doc, None, 1).code == code
    assert st.get(who[signer], doc)["body"] == {"rev": 1}
    assert st.events(who[signer])["head"] == head, "a refused withdrawal leaves no event or revision"
    assert put(st, who[signer], doc, None, 1)[0] == 201


# ---------------------------------------------------------------- a repeated request does not repeat its effect
def test_the_same_request_with_the_same_key_is_done_once(world):
    st, _, who, _ = world
    a = put(st, who["sam"], "dec/CL-001", DEC, 0, idempotency_key="k-1")
    b = put(st, who["sam"], "dec/CL-001", DEC, 0, idempotency_key="k-1")
    assert a[0] == b[0] == 201 and b[1]["replay"] is True and b[1]["rev"] == 1 and {**b[1], "replay": None} == {**a[1], "replay": None}
    assert st.get(who["sam"], "dec/CL-001")["rev"] == 1 and len(st.events(who["sam"])["events"]) == 2
    assert err(put, st, who["sam"], "dec/CL-001", {"other": 1}, 0, idempotency_key="k-1").code == "idempotency_reuse"
    assert err(put, st, who["sam"], "dec/CL-001", DEC, 0).status == 409, "without the key the same request is a conflict, as it should be"
    assert put(st, who["priya"], "dec/CL-005", DEC, 0, idempotency_key="k-1")[1].get("replay") is None, "a key belongs to the person who used it"
    assert err(put, st, who["sam"], "dec/CL-006", DEC, 0, idempotency_key="bad key!").code == "bad_idempotency_key"


def test_a_refused_request_is_not_remembered_under_its_key(world):
    st, _, who, _ = world
    err(put, st, who["priya"], "sign/CL-001/PE", {"rev": 1}, 0, idempotency_key="k-2")
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    assert put(st, who["priya"], "sign/CL-001/PE", {"rev": 1}, 0, idempotency_key="k-2")[0] == 201


# ---------------------------------------------------------------- the record
def test_the_record_follows_every_change_and_polling_shows_only_what_is_new(world):
    st, _, who, _ = world
    base = st.events(who["lee"])
    assert [e["seq"] for e in base["events"]] == [1] and base["head"]["seq"] == 1
    put(st, who["sam"], "dec/CL-001", DEC, 0); put(st, who["priya"], "dec/CL-001", {"outcome": "link"}, 1)
    new = st.events(who["lee"], after=1)
    assert [e["seq"] for e in new["events"]] == [2, 3] and [e["actor"] for e in new["events"]] == ["sam", "priya"] and new["head"]["seq"] == 3
    assert st.events(who["lee"], after=3)["events"] == [] and len(st.events(who["lee"], limit=1)["events"]) == 1
    e = new["events"][0]
    assert e["body_hash"] == sha256(canon(DEC)) and e["prev"] == base["events"][0]["hash"] and e["target"] == "dec/CL-001" and e["rev"] == 1


def test_a_refused_write_leaves_no_trace(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    before = (st.events(who["sam"]), st.db.execute("SELECT COUNT(*) FROM revs").fetchone()[0])
    for fn in (lambda: put(st, who["priya"], "dec/CL-001", DEC, 0), lambda: put(st, who["lee"], "dec/CL-002", DEC, 0), lambda: put(st, who["priya"], "sign/CL-001/SE", {"rev": 1}, 0), lambda: put(st, who["sam"], "dec/CL-002", "text", 0)):
        err(fn)
    assert (st.events(who["sam"]), st.db.execute("SELECT COUNT(*) FROM revs").fetchone()[0]) == before


def test_the_record_verifies_and_every_kind_of_edit_is_found(world):
    st, _, who, path = world
    put(st, who["sam"], "dec/CL-001", DEC, 0); put(st, who["priya"], "dec/CL-001", {"outcome": "link"}, 1); put(st, who["sam"], "dec/CL-002", DEC, 0)
    v = st.verify("demo")
    assert v["ok"] and v["entries"] == 4 and v["head"] == st.events(who["sam"])["head"]["hash"]
    head = v["head"]

    def broken(sql, args=(), why=None, at=None):
        st.db.execute("BEGIN"); st.db.execute(sql, args)
        try:
            r = st.verify("demo")
        finally:
            st.db.execute("ROLLBACK")
        assert not r["ok"], sql
        if at is not None:
            assert r["at"] == at, (sql, r)
        if why:
            assert why in r["why"], (sql, r)

    broken("UPDATE events SET text='Something else' WHERE seq=3", at=3, why="fingerprint")
    broken("UPDATE events SET actor='morgan' WHERE seq=3", at=3, why="fingerprint")
    broken("UPDATE events SET hash='00' WHERE seq=2", at=2)
    broken("DELETE FROM events WHERE seq=2", at=2, why="missing")
    broken("UPDATE revs SET body='{\"outcome\":\"reject\"}' WHERE doc_id='dec/CL-001' AND rev=2", at=3, why="no longer matches")
    broken("UPDATE revs SET by_person='morgan' WHERE doc_id='dec/CL-001' AND rev=2", at=3, why="who changed")
    broken("DELETE FROM revs WHERE doc_id='dec/CL-002'", at=4, why="missing")
    broken("INSERT INTO revs VALUES ('demo','dec/CL-077',1,'{}','x','sam','SE','2026-01-01',9)", why="not in the record")
    broken("UPDATE events SET prev='11' WHERE seq=3", at=3, why="follow")
    # taking away the newest entries leaves a chain that still adds up; only a remembered head notices
    st.db.execute("BEGIN"); st.db.execute("DELETE FROM events WHERE seq=4"); st.db.execute("DELETE FROM revs WHERE doc_id='dec/CL-002'")
    try:
        assert st.verify("demo")["ok"], "by itself a shorter chain is a valid chain"
        r = st.verify("demo", expect_head=head)
        assert not r["ok"] and "removed" in r["why"]
    finally:
        st.db.execute("ROLLBACK")
    assert st.verify("demo", expect_head=head)["ok"] and not st.verify("demo", expect_head="ab" * 32)["ok"]


def test_the_chain_is_sha256_over_the_entry_before_and_nothing_a_client_can_set(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", DEC, 0)
    e = st.events(who["sam"])["events"]
    assert e[0]["prev"] == GENESIS and e[1]["prev"] == e[0]["hash"] and len(e[1]["hash"]) == 64
    fields = {k: e[1][k] for k in ("seq", "type", "actor", "target", "rev", "body_hash", "text", "at")}
    assert e[1]["hash"] == sha256(e[0]["hash"] + "|" + canon(fields))
    assert e[1]["actor"] == "sam", "the actor is the person the token names"


# ---------------------------------------------------------------- what is accepted
@pytest.mark.parametrize("doc", ["dec", "dec/", "Dec/CL-1", "dec/../x", "dec/CL 1", "dec/CL-1/a/b/c", "dec/" + "x" * 90, "x" * 201, "dec//x", "/dec/CL-1", "dec/CL-1\n", "dec/%2e%2e", "1dec/x", ""])
def test_ids_are_a_kind_and_one_to_three_plain_names(world, doc):
    st, _, who, _ = world
    assert err(put, st, who["sam"], doc, DEC, 0).code == "bad_doc_id" and err(st.get, who["sam"], doc).status == 400


@pytest.mark.parametrize("body", ["x", 5, [1], True])
def test_a_document_is_an_object_or_null(world, body):
    st, _, who, _ = world
    assert err(put, st, who["sam"], "dec/CL-001", body, 0).code == "bad_body"


def test_a_document_has_a_size_limit_and_no_non_finite_numbers(world):
    st, _, who, _ = world
    assert err(put, st, who["sam"], "dec/CL-001", {"t": "x" * 70_000}, 0).status == 413
    assert put(st, who["sam"], "dec/CL-001", {"t": "x" * 60_000}, 0)[0] == 201
    with pytest.raises(ValueError):
        put(st, who["sam"], "dec/CL-002", {"n": float("nan")}, 0)


def test_unicode_survives_and_listing_pages_through_everything(world):
    st, _, who, _ = world
    put(st, who["sam"], "dec/CL-001", {"text": "Le système doit répondre en moins de 0,2 s — «ok» ✓"}, 0)
    assert st.get(who["sam"], "dec/CL-001")["body"]["text"].endswith("✓")
    for i in range(2, 8):
        put(st, who["sam"], f"dec/CL-{i:03d}", {"n": i}, 0)
    put(st, who["sam"], "rdec/REQ-1", {"n": 1}, 0); put(st, who["sam"], "dec_x/CL-1", {"n": 1}, 0)
    seen, after = [], ""
    while True:
        page = st.list(who["lee"], "dec/", after, limit=3)
        seen += [d["id"] for d in page["docs"]]
        if not page["next"]:
            break
        after = page["next"]
    assert seen == sorted(seen) and len(seen) == 7 and "rdec/REQ-1" not in seen and "dec_x/CL-1" not in seen, "a prefix is a prefix, and _ is not a wildcard"
    assert len(st.list(who["lee"], "dec%")["docs"]) == 0


def test_a_database_from_another_version_is_refused(tmp_path):
    p = tmp_path / "old.db"
    Store(p).close()
    db = sqlite3.connect(p); db.execute("UPDATE meta SET v='99' WHERE k='schema'"); db.commit(); db.close()
    assert err(Store, p).code == "schema"


# ---------------------------------------------------------------- over HTTP
def test_health_needs_no_token_and_everything_else_does(live):
    call, tokens, st = live
    assert call("GET", "/v1/health")[:2] == (200, {"ok": True, "version": "0.1"})
    for url in ("/v1/me", "/v1/projects/demo/docs", "/v1/projects/demo/events", "/v1/projects/demo/verify", "/v1/projects/demo/people"):
        s, b, r = call("GET", url)
        assert s == 401 and b["error"]["code"] == "no_token" and r.getheader("WWW-Authenticate", "").startswith("Bearer"), url
    assert call("GET", "/v1/me", token="x" * 43)[0] == 401
    assert call("GET", "/v1/me", headers={"Authorization": "Basic abc"})[0] == 401
    assert call("GET", "/v1/me", token=tokens["priya"])[1]["lens"] == "PE"


def test_a_token_works_only_in_its_own_project(live):
    call, tokens, st = live
    st.init_project("other", [{"key": "a", "name": "A", "role": "lead", "lens": "SE"}])
    s, b, _ = call("GET", "/v1/projects/other/docs", token=tokens["sam"])
    assert s == 403 and b["error"]["code"] == "other_project"
    assert call("GET", "/v1/projects/nope/docs", token=tokens["sam"])[0] == 403, "a missing project and a forbidden one look the same"


def test_the_whole_working_day_over_http(live):
    call, t, st = live
    base = "/v1/projects/demo"
    s, b, _ = call("PUT", f"{base}/docs/dec/CL-014", t["priya"], {"body": DEC, "if_rev": 0})
    assert s == 201 and b["rev"] == 1
    s, b, _ = call("PUT", f"{base}/docs/dec/CL-014", t["sam"], {"body": {"outcome": "link"}, "if_rev": 0})
    assert s == 409 and b["error"]["code"] == "conflict" and b["error"]["current"]["by"] == "priya" and b["error"]["current"]["body"] == DEC
    assert call("PUT", f"{base}/docs/sign/CL-014/SE", t["sam"], {"body": {"rev": 1}, "if_rev": 0})[0] == 201
    assert call("PUT", f"{base}/docs/sign/CL-014/SE", t["priya"], {"body": {"rev": 1}, "if_rev": 1})[0] == 403
    assert call("PUT", f"{base}/docs/dec/CL-014", t["lee"], {"body": DEC, "if_rev": 1})[0] == 403
    s, b, _ = call("GET", f"{base}/docs?prefix=sign/", t["lee"])
    assert s == 200 and [d["id"] for d in b["docs"]] == ["sign/CL-014/SE"] and b["docs"][0]["by"] == "sam"
    s, b, _ = call("GET", f"{base}/history/dec/CL-014", t["lee"])
    assert s == 200 and len(b["revisions"]) == 1
    s, b, _ = call("GET", f"{base}/events?after=2", t["lee"])
    assert s == 200 and [e["seq"] for e in b["events"]] == [3] and b["head"]["seq"] == 3
    s, b, _ = call("GET", f"{base}/verify?expect_head={b['head']['hash']}", t["lee"])
    assert s == 200 and b["ok"] and b["entries"] == 3
    assert call("GET", f"{base}/people", t["lee"])[1]["people"][0].keys() == {"key", "name", "role", "lens"}
    assert call("GET", f"{base}/docs/dec/CL-404", t["lee"])[0] == 404


def test_a_repeated_put_over_http_is_flagged_as_a_replay(live):
    call, t, _ = live
    h = {"Idempotency-Key": "once-1"}
    a = call("PUT", "/v1/projects/demo/docs/dec/CL-001", t["sam"], {"body": DEC, "if_rev": 0}, headers=h)
    b = call("PUT", "/v1/projects/demo/docs/dec/CL-001", t["sam"], {"body": DEC, "if_rev": 0}, headers=h)
    assert a[0] == b[0] == 201 and a[2].getheader("Idempotent-Replay") is None and b[2].getheader("Idempotent-Replay") == "true" and b[1]["rev"] == 1


@pytest.mark.parametrize("kw,status,code", [
    (dict(raw="{not json"), 400, "bad_json"), (dict(raw="[1]"), 400, "bad_request"), (dict(body={"body": DEC}), 400, "if_rev_required"), (dict(body={"if_rev": 0}), 400, "bad_request"),
    (dict(body={"body": DEC, "if_rev": 0, "by": "morgan"}), 400, "bad_request"), (dict(raw='{"body": {"n": NaN}, "if_rev": 0}'), 400, "bad_json"),
    (dict(raw="{}", headers={"Content-Type": "text/plain"}), 415, "json_only"), (dict(body={"body": {"t": "x" * 70_000}, "if_rev": 0}), 413, "too_large"),
    (dict(raw="x" * (1024 * 1024 + 1)), 413, "too_large"),
])
def test_a_bad_request_gets_a_plain_answer_and_changes_nothing(live, kw, status, code):
    call, t, st = live
    s, b, _ = call("PUT", "/v1/projects/demo/docs/dec/CL-001", t["sam"], **kw)
    assert (s, b["error"]["code"]) == (status, code)
    assert st.db.execute("SELECT COUNT(*) FROM revs").fetchone()[0] == 0


def test_a_too_large_request_is_answered_every_time_not_sometimes_reset(live):
    """The server refuses on the Content-Length without reading the body. If it then closed at once, the unread data would turn the close into a reset and the caller would
    sometimes see 'connection reset' instead of 413 (about one run in five before the server read and discarded a bounded part of the body)."""
    call, t, _ = live
    for _ in range(25):
        s, b, _r = call("PUT", "/v1/projects/demo/docs/dec/CL-001", t["sam"], raw="x" * (1024 * 1024 + 1))
        assert (s, b["error"]["code"]) == (413, "too_large")


def test_odd_urls_and_methods_are_refused_without_a_stack_trace(live):
    call, t, _ = live
    for url in ("/", "/v1", "/v1/projects/demo", "/v1/projects/demo/docs/", "/v1/projects/demo/docs/../../etc/passwd", "/v1/projects/demo/docs/dec/%2e%2e/x", "/v1/projects/DEMO/docs"):
        s, b, _ = call("GET", url, t["sam"])
        assert s in (400, 403, 404) and "Traceback" not in json.dumps(b), url
    for method in ("POST", "DELETE", "PATCH", "OPTIONS"):
        s, b, _ = call(method, "/v1/projects/demo/docs/dec/CL-001", t["sam"], raw="{}")
        assert s == 405, method
    assert call("GET", "/v1/projects/demo/events?after=abc", t["sam"])[1]["error"]["code"] == "bad_number"
    assert call("HEAD", "/v1/health")[0] == 405, "only the listed methods are answered"


def test_replies_are_not_cached_sniffed_or_offered_to_other_websites(live):
    call, t, _ = live
    for url, tok in (("/v1/health", None), ("/v1/me", t["sam"]), ("/v1/me", None)):
        _, _, r = call("GET", url, tok)
        assert r.getheader("Cache-Control") == "no-store" and r.getheader("X-Content-Type-Options") == "nosniff"
        assert r.getheader("Access-Control-Allow-Origin") is None, "no CORS: a page from another origin cannot call this"
        assert "Python" not in (r.getheader("Server") or ""), "no version banner"


def test_nothing_a_caller_sends_reaches_the_log(world, capsys):
    st, tokens, who, _ = world
    lines = []
    srv = make_server(st, port=0, log=lines.append)
    serve_in_thread(srv)
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=10)
    c.request("PUT", "/v1/projects/demo/docs/dec/CL-001?secret=1", body=json.dumps({"body": {"text": "SECRET-WORDING"}, "if_rev": 0}), headers={"Authorization": "Bearer " + tokens["sam"], "Content-Type": "application/json"})
    c.getresponse().read(); c.close()
    srv.shutdown(); srv.server_close()
    out = " ".join(lines) + capsys.readouterr().err + capsys.readouterr().out
    assert lines == ["PUT /v1/projects/demo/docs/dec/CL-001 201"] and tokens["sam"] not in out and "SECRET-WORDING" not in out


def test_an_unexpected_failure_is_a_plain_500_that_says_nothing_about_the_cause(live, monkeypatch):
    call, t, st = live

    def boom(*a, **k):
        raise RuntimeError("secret internals: /srv/data/shared.db token=abc")

    monkeypatch.setattr(st, "list", boom)
    s, b, _ = call("GET", "/v1/projects/demo/docs", t["sam"])
    assert s == 500 and b == {"error": {"code": "server_error", "message": "The server could not do that."}}
    assert call("GET", "/v1/me", t["sam"])[0] == 200, "the server is still up afterwards"


def test_the_server_binds_to_this_machine_unless_told_otherwise(world):
    st, *_ = world
    assert is_loopback("127.0.0.1") and is_loopback("::1") and is_loopback("localhost") and not is_loopback("0.0.0.0") and not is_loopback("192.168.1.5") and not is_loopback("example.org")
    for host in ("0.0.0.0", "192.168.1.5", "example.org"):
        assert err(make_server, st, host, 0).code == "remote_refused"
    srv = make_server(st, "0.0.0.0", 0, allow_remote=True)
    srv.server_close()


# ---------------------------------------------------------------- the command line
def test_the_command_line_makes_a_project_serves_and_checks_it(tmp_path, capsys):
    from reqin.server.__main__ import main
    people = tmp_path / "people.json"; people.write_text(json.dumps(PEOPLE))
    db, out = str(tmp_path / "cli.db"), tmp_path / "tokens.json"
    assert main(["init", "--db", db, "--project", "demo", "--people", str(people), "--tokens-out", str(out)]) == 0
    assert oct(out.stat().st_mode & 0o777) == "0o600" and set(json.loads(out.read_text())) == {p["key"] for p in PEOPLE}
    assert main(["init", "--db", db, "--project", "demo", "--people", str(people), "--tokens-out", str(tmp_path / "t2.json")]) == 2, "a second init is refused"
    assert main(["init", "--db", db, "--project", "demo2", "--people", str(people), "--tokens-out", str(out)]) == 2, "tokens are never written over an existing file"
    capsys.readouterr()
    assert main(["verify", "--db", db, "--project", "demo"]) == 0
    head = json.loads(capsys.readouterr().out)["head"]
    assert main(["verify", "--db", db, "--project", "demo", "--expect-head", head]) == 0
    assert main(["verify", "--db", db, "--project", "demo", "--expect-head", "ab" * 32]) == 1
    capsys.readouterr()
    assert main(["rotate-token", "--db", db, "--project", "demo", "--person", "sam"]) == 0
    new = capsys.readouterr().out.strip()
    assert new != json.loads(out.read_text())["sam"] and len(new) >= 40
    assert main(["serve", "--db", db, "--host", "0.0.0.0"]) == 2
    db2 = sqlite3.connect(db); db2.execute("UPDATE events SET text='edited' WHERE seq=1"); db2.commit(); db2.close()
    assert main(["verify", "--db", db, "--project", "demo"]) == 1


# ---------------------------------------------------------------- the guide matches the code
GUIDE = (Path(__file__).parent.parent / "SERVER.md").read_text(encoding="utf-8")


def test_the_guide_names_every_route_and_every_error_code():
    import re
    from reqin.server import http as h, store as s
    for method, rx, name in h.ROUTES:
        shown = rx.pattern.replace(h._P.join(["(", ")"]), "<p>").replace("(.+)", "<id>")
        assert "(" not in shown and f"{method} {shown}" in GUIDE, f"SERVER.md does not show {method} {shown}"
    src = (Path(s.__file__).read_text() + Path(h.__file__).read_text())
    codes = set(re.findall(r'ServerError\(\d{3}, "([a-z_]+)"', src))
    missing = sorted(c for c in codes if c not in GUIDE and c not in {"bad_project", "no_people", "bad_person", "bad_role", "bad_lens", "bad_name", "project_exists", "no_person", "schema", "remote_refused", "bad_idempotency_key", "bad_sign_id", "bad_slot", "bad_number", "bad_body", "too_large", "bad_doc_id"})
    assert not missing, f"SERVER.md never mentions these error codes: {missing}"


def test_the_guide_keeps_its_honesty_caveats():
    low = GUIDE.lower()
    for phrase in ("is not connected to it", "keeps its own copy", "never been run with real program data", "no tls", "not encrypted", "stays in the page", "head", "has never", "no push", "not moved to the server"):
        assert phrase in low, f"SERVER.md lost the statement: {phrase!r}"
