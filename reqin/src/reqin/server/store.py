"""The shared store behind the reference server: documents with revisions, who may change what, and a hash-chained record of every change.

Everything here is tested in tests/test_server.py. What the store promises:

* One copy. A document (a cluster decision, a sign-off, a hand-off, a label) lives once per project. Every change makes a new revision; the old
  ones stay and can be read (`history`).
* No silent overwrite. A write must say which revision it was made against (`if_rev`, 0 for a new document). If someone else got there first,
  the write is refused with 409 and the current revision is returned, so the second person sees what changed before deciding again.
* Who may change what is decided here, from the token, never from what the request claims: observers cannot write; a sign-off must be in the
  signer's own lens slot (OWN and ADJ are for leads); nobody signs a decision they made; a sign-off names the revision it binds to, and a new
  revision of a decision clears the sign-offs on the old one; project settings (`proj/...`) and rulings (`adj/...`, `gadj/...`) are for a lead, and so is resolving an objection (`obj/...`: anyone with a lens can raise one); a
  label (`label/<req>/<req>/<person>`) can only be written by the person it names.
* A repeated request does not repeat its effect (`idempotency_key`).
* The record is a SHA-256 chain: each entry's hash covers the one before it and the fingerprint of the document revision it describes.
  `verify` recomputes all of it from the stored documents and says where the first break is.

What it does not do (see SERVER.md): it does not know the sign-off policy (which lenses a given decision needs: that stays in the client), it
does not encrypt anything on disk, it does not speak TLS, and the chain proves the record was not edited in place, not who held the pen: removing
the newest entries is only noticed if you kept the head hash (`verify(expect_head=...)`).
"""
from __future__ import annotations

import hashlib
import json
import re
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA_VERSION = 1
GENESIS = "0" * 64
LENS_SLOTS = ("SE", "PE", "UX", "NU")
LEAD_SLOTS = ("OWN", "ADJ")
LEAD_ONLY_KINDS = ("proj", "adj", "gadj")   # project settings (the AI switch and data sheet), a lead's ruling on a cluster, a lead's ruling on a labelled pair
MAX_SEED_DOCS = 20000
ROLES = ("lead", "reviewer", "observer")
MAX_BODY_BYTES = 64 * 1024
MAX_DOC_ID = 200
MAX_TEXT = 300
DOC_ID = re.compile(r"[a-z][a-z0-9_-]{0,30}(/[A-Za-z0-9][A-Za-z0-9._:-]{0,79}){1,3}")   # matched whole: "$" would let a trailing newline through
PROJECT_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
PERSON_KEY = re.compile(r"[a-z][a-z0-9_-]{0,31}")
IDEM_KEY = re.compile(r"[A-Za-z0-9._:-]{1,64}")


class ServerError(Exception):
    """An error the caller can be told about: an HTTP status, a short code, a sentence, and (for 409) the current document."""

    def __init__(self, status: int, code: str, message: str, **extra: Any):
        super().__init__(message)
        self.status, self.code, self.message, self.extra = status, code, message, extra


@dataclass(frozen=True)
class Person:
    project: str
    key: str
    name: str
    role: str
    lens: str


def canon(obj: Any) -> str:
    """The one way a value is turned into bytes before it is hashed: sorted keys, no spaces, no surprises."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def token_hash(token: str) -> str:
    return sha256("reqin-token|" + token)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS people (
  project TEXT NOT NULL REFERENCES projects(id), key TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, lens TEXT NOT NULL, token_hash TEXT NOT NULL UNIQUE,
  PRIMARY KEY (project, key));
CREATE TABLE IF NOT EXISTS revs (
  project TEXT NOT NULL, doc_id TEXT NOT NULL, rev INTEGER NOT NULL, body TEXT NOT NULL, body_hash TEXT NOT NULL, by_person TEXT NOT NULL, lens TEXT NOT NULL, at TEXT NOT NULL, event_seq INTEGER NOT NULL,
  PRIMARY KEY (project, doc_id, rev));
CREATE TABLE IF NOT EXISTS events (
  project TEXT NOT NULL, seq INTEGER NOT NULL, type TEXT NOT NULL, actor TEXT NOT NULL, target TEXT NOT NULL, rev INTEGER NOT NULL, body_hash TEXT NOT NULL, text TEXT NOT NULL, at TEXT NOT NULL,
  prev TEXT NOT NULL, hash TEXT NOT NULL, PRIMARY KEY (project, seq));
CREATE TABLE IF NOT EXISTS idem (
  project TEXT NOT NULL, person TEXT NOT NULL, k TEXT NOT NULL, request_hash TEXT NOT NULL, status INTEGER NOT NULL, response TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (project, person, k));
"""


class Store:
    """One SQLite file, one writer at a time. Safe to share between the threads of the HTTP server."""

    def __init__(self, path: str | Path, clock: Callable[[], str] = _utc_now):
        self.path, self.clock = str(path), clock
        self._lock = threading.RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(_SCHEMA)
        self.db.execute("INSERT OR IGNORE INTO meta (k, v) VALUES ('schema', ?)", (str(SCHEMA_VERSION),))
        v = self.db.execute("SELECT v FROM meta WHERE k='schema'").fetchone()["v"]
        if v != str(SCHEMA_VERSION):
            raise ServerError(500, "schema", f"this database is schema {v} and this server reads {SCHEMA_VERSION}")

    def close(self) -> None:
        with self._lock:
            self.db.close()

    # ------------------------------------------------------------------ projects and people
    def init_project(self, project: str, people: list[dict[str, str]]) -> dict[str, str]:
        """Create a project and return {person key: token}. Tokens are shown once; only their hashes are stored."""
        if not PROJECT_ID.fullmatch(project or ""):
            raise ServerError(400, "bad_project", "A project id is 1 to 64 lowercase letters, digits, - or _.")
        if not people:
            raise ServerError(400, "no_people", "A project needs at least one person.")
        seen: set[str] = set()
        for p in people:
            if not PERSON_KEY.fullmatch(str(p.get("key", ""))) or p["key"] in seen:
                raise ServerError(400, "bad_person", f"Person keys are lowercase letters, digits, - or _, and each is used once ({p.get('key')!r}).")
            seen.add(p["key"])
            if p.get("role") not in ROLES:
                raise ServerError(400, "bad_role", f"{p['key']}: role must be one of {', '.join(ROLES)}.")
            lens = p.get("lens", "")
            if p["role"] == "observer" and lens:
                raise ServerError(400, "bad_lens", f"{p['key']}: an observer has no lens.")
            if p["role"] != "observer" and lens not in LENS_SLOTS:
                raise ServerError(400, "bad_lens", f"{p['key']}: a lens is one of {', '.join(LENS_SLOTS)}.")
            if not str(p.get("name", "")).strip() or len(p["name"]) > 80:
                raise ServerError(400, "bad_name", f"{p['key']}: a name is 1 to 80 characters.")
        tokens: dict[str, str] = {}
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if self.db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise ServerError(409, "project_exists", f"The project {project!r} already exists. Use rotate_token to replace a lost token.")
                self.db.execute("INSERT INTO projects (id, created) VALUES (?, ?)", (project, self.clock()))
                for p in people:
                    tok = secrets.token_urlsafe(32)
                    tokens[p["key"]] = tok
                    self.db.execute("INSERT INTO people (project, key, name, role, lens, token_hash) VALUES (?,?,?,?,?,?)",
                                    (project, p["key"], p["name"].strip(), p["role"], p.get("lens", ""), token_hash(tok)))
                self._append(project, "system", "server", project, 0, sha256(""), f"Project {project} created with {len(people)} people")
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return tokens

    def rotate_token(self, project: str, person: str) -> str:
        tok = secrets.token_urlsafe(32)
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                n = self.db.execute("UPDATE people SET token_hash=? WHERE project=? AND key=?", (token_hash(tok), project, person)).rowcount
                if not n:
                    raise ServerError(404, "no_person", f"{person!r} is not in {project!r}.")
                self._append(project, "system", "server", person, 0, sha256(""), f"Token replaced for {person}")
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return tok

    def who(self, token: str | None) -> Person:
        if not token:
            raise ServerError(401, "no_token", "Send the token as: Authorization: Bearer <token>.")
        with self._lock:
            r = self.db.execute("SELECT project, key, name, role, lens FROM people WHERE token_hash=?", (token_hash(token),)).fetchone()
        if not r:
            raise ServerError(401, "bad_token", "That token is not recognised.")
        return Person(r["project"], r["key"], r["name"], r["role"], r["lens"])

    def people(self, who: Person) -> list[dict[str, str]]:
        with self._lock:
            rows = self.db.execute("SELECT key, name, role, lens FROM people WHERE project=? ORDER BY key", (who.project,)).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------ reading
    def _latest(self, project: str, doc_id: str) -> sqlite3.Row | None:
        return self.db.execute("SELECT * FROM revs WHERE project=? AND doc_id=? ORDER BY rev DESC LIMIT 1", (project, doc_id)).fetchone()

    @staticmethod
    def _doc(r: sqlite3.Row) -> dict[str, Any]:
        return {"id": r["doc_id"], "rev": r["rev"], "body": json.loads(r["body"]), "by": r["by_person"], "lens": r["lens"], "at": r["at"], "event": r["event_seq"], "body_hash": r["body_hash"]}

    def get(self, who: Person, doc_id: str) -> dict[str, Any]:
        _check_doc_id(doc_id)
        with self._lock:
            r = self._latest(who.project, doc_id)
        if not r:
            raise ServerError(404, "no_doc", f"There is no document {doc_id}.")
        return self._doc(r)

    def history(self, who: Person, doc_id: str) -> list[dict[str, Any]]:
        _check_doc_id(doc_id)
        with self._lock:
            rows = self.db.execute("SELECT * FROM revs WHERE project=? AND doc_id=? ORDER BY rev", (who.project, doc_id)).fetchall()
        if not rows:
            raise ServerError(404, "no_doc", f"There is no document {doc_id}.")
        return [self._doc(r) for r in rows]

    def list(self, who: Person, prefix: str = "", after: str = "", limit: int = 200, include_withdrawn: bool = False) -> dict[str, Any]:
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self.db.execute(
                "SELECT r.* FROM revs r JOIN (SELECT doc_id, MAX(rev) m FROM revs WHERE project=? AND doc_id LIKE ? ESCAPE '\\' AND doc_id > ? GROUP BY doc_id) x ON r.doc_id=x.doc_id AND r.rev=x.m "
                "WHERE r.project=? ORDER BY r.doc_id LIMIT ?", (who.project, _like(prefix), after, who.project, limit + 1)).fetchall()
        docs = [self._doc(r) for r in rows]
        more = len(docs) > limit
        docs = docs[:limit]
        nxt = docs[-1]["id"] if more else ""
        if not include_withdrawn:
            docs = [d for d in docs if d["body"] is not None]
        return {"docs": docs, "next": nxt}

    def events(self, who: Person, after: int = 0, limit: int = 500) -> dict[str, Any]:
        limit = max(1, min(int(limit), 1000))
        with self._lock:
            rows = self.db.execute("SELECT * FROM events WHERE project=? AND seq>? ORDER BY seq LIMIT ?", (who.project, int(after), limit)).fetchall()
            head = self.db.execute("SELECT seq, hash FROM events WHERE project=? ORDER BY seq DESC LIMIT 1", (who.project,)).fetchone()
        return {"events": [dict(r) for r in rows], "head": {"seq": head["seq"], "hash": head["hash"]} if head else {"seq": 0, "hash": GENESIS}}

    # ------------------------------------------------------------------ writing
    def put(self, who: Person, doc_id: str, body: Any, if_rev: Any, idempotency_key: str = "") -> tuple[int, dict[str, Any]]:
        """Write a new revision. Returns (status, response); 201 for the new revision. Raises ServerError for everything else."""
        _check_doc_id(doc_id)
        if idempotency_key and not IDEM_KEY.fullmatch(idempotency_key):
            raise ServerError(400, "bad_idempotency_key", "An idempotency key is 1 to 64 letters, digits, . _ : or -.")
        if who.role == "observer":
            raise ServerError(403, "observer", "Observers can read but not change anything.")
        if isinstance(if_rev, bool) or not isinstance(if_rev, int) or if_rev < 0:
            raise ServerError(400, "if_rev_required", "Say which revision you are changing: if_rev is the revision you read, or 0 for a new document.")
        if body is not None and not isinstance(body, dict):
            raise ServerError(400, "bad_body", "A document is a JSON object, or null to withdraw it.")
        text = canon(body)
        if len(text.encode("utf-8")) > MAX_BODY_BYTES:
            raise ServerError(413, "too_large", f"A document is at most {MAX_BODY_BYTES // 1024} KB.")
        req_hash = sha256(canon([doc_id, if_rev, body]))
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if idempotency_key:
                    old = self.db.execute("SELECT * FROM idem WHERE project=? AND person=? AND k=?", (who.project, who.key, idempotency_key)).fetchone()
                    if old:
                        if old["request_hash"] != req_hash:
                            raise ServerError(422, "idempotency_reuse", "That idempotency key was already used for a different request.")
                        self.db.execute("ROLLBACK")
                        return old["status"], dict(json.loads(old["response"]), replay=True)
                cur = self._latest(who.project, doc_id)
                have = cur["rev"] if cur else 0
                if if_rev != have:
                    raise ServerError(409, "conflict", f"{doc_id} is at revision {have}, not {if_rev}. Read it again before changing it.", current=self._doc(cur) if cur else None, rev=have)
                self._rules(who, doc_id, body)
                rev = have + 1
                seq = self._next_seq(who.project)
                bh = sha256(text)
                what = "Withdrew" if body is None else ("Created" if rev == 1 else "Changed")
                ev = self._append(who.project, "doc", who.key, doc_id, rev, bh, f"{what} {doc_id} (revision {rev})", seq=seq)
                at = ev["at"]
                self.db.execute("INSERT INTO revs (project, doc_id, rev, body, body_hash, by_person, lens, at, event_seq) VALUES (?,?,?,?,?,?,?,?,?)", (who.project, doc_id, rev, text, bh, who.key, who.lens, at, seq))
                cleared = self._clear_signoffs(who, doc_id) if doc_id.split("/")[0] in ("dec", "rdec") else []
                resp = {"id": doc_id, "rev": rev, "event": seq, "at": at, "body_hash": bh, "cleared": cleared}
                if idempotency_key:
                    self.db.execute("INSERT INTO idem (project, person, k, request_hash, status, response, at) VALUES (?,?,?,?,?,?,?)", (who.project, who.key, idempotency_key, req_hash, 201, canon(resp), at))
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
        return 201, resp

    def _rules(self, who: Person, doc_id: str, body: Any) -> None:
        """The few rules the server can enforce without knowing the sign-off policy."""
        parts = doc_id.split("/")
        if parts[0] in LEAD_ONLY_KINDS:
            if who.role != "lead":
                raise ServerError(403, "lead_only", "Project settings and rulings are for a lead.")
            return
        if parts[0] == "obj" and body is None and who.role != "lead":
            raise ServerError(403, "lead_only", "Only a lead can resolve an objection: anyone can raise one, and the adjudicator closes it.")
        if parts[0] == "label":
            if len(parts) != 4:
                raise ServerError(400, "bad_label_id", "A label is label/<requirement>/<requirement>/<person>.")
            if parts[3] != who.key:
                raise ServerError(403, "not_yours", "A label is its labeller's own: you can only write labels under your own key.")
            return
        if parts[0] != "sign":
            return
        if len(parts) != 3:
            raise ServerError(400, "bad_sign_id", "A sign-off is sign/<cluster or requirement>/<slot>.")
        target, slot = parts[1], parts[2]
        if slot not in LENS_SLOTS + LEAD_SLOTS:
            raise ServerError(400, "bad_slot", f"A sign-off slot is one of {', '.join(LENS_SLOTS + LEAD_SLOTS)}.")
        if body is None:
            return   # withdrawing a sign-off: the revision check above already stops two people withdrawing over each other
        if slot in LEAD_SLOTS and who.role != "lead":
            raise ServerError(403, "lead_only", f"The {slot} slot is for a lead.")
        if slot in LENS_SLOTS and who.lens != slot:
            raise ServerError(403, "wrong_lens", f"You review as {who.lens or 'an observer'}; the {slot} slot is for the {slot} lens.")
        dec_id = ("rdec/" if not target.startswith("CL-") else "dec/") + target
        dec = self._latest(who.project, dec_id)
        if not dec or json.loads(dec["body"]) is None:
            raise ServerError(409, "nothing_to_sign", f"There is no decision on {target} to sign.")
        if dec["by_person"] == who.key:
            raise ServerError(403, "self_sign", "You made this decision, so someone else has to sign it.")
        if not isinstance(body, dict) or body.get("rev") != dec["rev"]:
            raise ServerError(409, "stale_signoff", f"The decision on {target} is at revision {dec['rev']}. A sign-off names the revision it binds to: send rev={dec['rev']}.", decision_rev=dec["rev"])

    def _clear_signoffs(self, who: Person, doc_id: str) -> list[str]:
        """A new revision of a decision clears the sign-offs on the old one, in the same step."""
        target = doc_id.split("/", 1)[1]
        rows = self.db.execute("SELECT doc_id FROM (SELECT doc_id, MAX(rev) m FROM revs WHERE project=? AND doc_id LIKE ? ESCAPE '\\' GROUP BY doc_id) ORDER BY doc_id", (who.project, _like(f"sign/{target}/"))).fetchall()
        cleared = []
        for r in rows:
            cur = self._latest(who.project, r["doc_id"])
            if json.loads(cur["body"]) is None:
                continue
            seq = self._next_seq(who.project)
            bh = sha256(canon(None))
            ev = self._append(who.project, "doc", "server", r["doc_id"], cur["rev"] + 1, bh, f"Cleared {r['doc_id']}: {doc_id} changed", seq=seq)
            self.db.execute("INSERT INTO revs (project, doc_id, rev, body, body_hash, by_person, lens, at, event_seq) VALUES (?,?,?,?,?,?,?,?,?)", (who.project, r["doc_id"], cur["rev"] + 1, canon(None), bh, "server", "", ev["at"], seq))
            cleared.append(r["doc_id"])
        return cleared

    def seed(self, project: str, docs: list[dict[str, Any]]) -> int:
        """Put sample activity into a new project: documents that look as if people had already worked, each at revision 1 under the person it names.

        Used for the demo only. Nothing is checked against the rules above (that is the point: a seed can hold a sign-off made before the policy was
        set), but every document is a valid one, every author is a person of the project who can write, and each document is in the record like any
        other, so `verify` passes. A project that already has documents is refused, so a seed can never overwrite real work."""
        if not isinstance(docs, list) or len(docs) > MAX_SEED_DOCS:
            raise ServerError(400, "bad_seed", f"A seed is a list of at most {MAX_SEED_DOCS} documents.")
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                if not self.db.execute("SELECT 1 FROM projects WHERE id=?", (project,)).fetchone():
                    raise ServerError(404, "no_project", f"There is no project {project!r}.")
                if self.db.execute("SELECT 1 FROM revs WHERE project=? LIMIT 1", (project,)).fetchone():
                    raise ServerError(409, "not_empty", f"{project!r} already has documents, so it is not seeded.")
                people = {r["key"]: r for r in self.db.execute("SELECT key, role, lens FROM people WHERE project=?", (project,)).fetchall()}
                seen: set[str] = set()
                for d in docs:
                    if not isinstance(d, dict) or set(d) - {"id", "body", "by"} or not isinstance(d.get("body"), dict):
                        raise ServerError(400, "bad_seed", 'Each seeded document is {"id": ..., "body": {...}, "by": <person key>}.')
                    doc_id, by = d.get("id"), d.get("by")
                    _check_doc_id(doc_id)
                    if doc_id in seen:
                        raise ServerError(400, "bad_seed", f"{doc_id} appears twice in the seed.")
                    seen.add(doc_id)
                    if not isinstance(by, str) or by not in people or people[by]["role"] == "observer":
                        raise ServerError(400, "bad_seed", f"{doc_id}: {by!r} is not a person in {project!r} who can write.")
                    text = canon(d["body"])
                    if len(text.encode("utf-8")) > MAX_BODY_BYTES:
                        raise ServerError(413, "too_large", f"{doc_id}: a document is at most {MAX_BODY_BYTES // 1024} KB.")
                    seq = self._next_seq(project)
                    bh = sha256(text)
                    ev = self._append(project, "doc", by, doc_id, 1, bh, f"Sample activity: {doc_id}", seq=seq)
                    self.db.execute("INSERT INTO revs (project, doc_id, rev, body, body_hash, by_person, lens, at, event_seq) VALUES (?,?,?,?,?,?,?,?,?)", (project, doc_id, 1, text, bh, by, people[by]["lens"], ev["at"], seq))
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                raise
        return len(docs)

    # ------------------------------------------------------------------ the record
    def _next_seq(self, project: str) -> int:
        r = self.db.execute("SELECT MAX(seq) m FROM events WHERE project=?", (project,)).fetchone()
        return (r["m"] or 0) + 1

    @staticmethod
    def _entry_hash(prev: str, e: dict[str, Any]) -> str:
        return sha256(prev + "|" + canon({k: e[k] for k in ("seq", "type", "actor", "target", "rev", "body_hash", "text", "at")}))

    def _append(self, project: str, type_: str, actor: str, target: str, rev: int, body_hash: str, text: str, seq: int | None = None) -> dict[str, Any]:
        seq = seq or self._next_seq(project)
        last = self.db.execute("SELECT hash FROM events WHERE project=? ORDER BY seq DESC LIMIT 1", (project,)).fetchone()
        prev = last["hash"] if last else GENESIS
        e = {"seq": seq, "type": type_, "actor": actor, "target": target, "rev": rev, "body_hash": body_hash, "text": text[:MAX_TEXT], "at": self.clock()}
        e["prev"], e["hash"] = prev, self._entry_hash(prev, e)
        self.db.execute("INSERT INTO events (project, seq, type, actor, target, rev, body_hash, text, at, prev, hash) VALUES (:project,:seq,:type,:actor,:target,:rev,:body_hash,:text,:at,:prev,:hash)", dict(e, project=project))
        return e

    def verify(self, project: str, expect_head: str = "") -> dict[str, Any]:
        """Recompute the whole record from what is stored. ok is False at the first thing that does not follow, and `at` names it."""
        with self._lock:
            ev = self.db.execute("SELECT * FROM events WHERE project=? ORDER BY seq", (project,)).fetchall()
            revs = {(r["doc_id"], r["rev"]): r for r in self.db.execute("SELECT * FROM revs WHERE project=?", (project,)).fetchall()}
        prev, n = GENESIS, 0
        used: set[tuple[str, int]] = set()

        def bad(seq: int, why: str) -> dict[str, Any]:
            return {"ok": False, "entries": len(ev), "at": seq, "why": why, "head": ev[-1]["hash"] if ev else GENESIS}

        for e in ev:
            n += 1
            if e["seq"] != n:
                return bad(n, "an entry is missing or out of order")
            d = dict(e)
            if e["prev"] != prev:
                return bad(e["seq"], "does not follow the entry before it")
            if self._entry_hash(prev, d) != e["hash"]:
                return bad(e["seq"], "its contents no longer match its fingerprint")
            if e["type"] == "doc":
                r = revs.get((e["target"], e["rev"]))
                if not r or r["event_seq"] != e["seq"]:
                    return bad(e["seq"], "the document revision it describes is missing")
                if r["by_person"] != e["actor"] or r["at"] != e["at"]:
                    return bad(e["seq"], "who changed the document, or when, no longer matches the record")
                if sha256(r["body"]) != e["body_hash"] or r["body_hash"] != e["body_hash"]:
                    return bad(e["seq"], "the stored document no longer matches the fingerprint in the record")
                used.add((e["target"], e["rev"]))
            prev = e["hash"]
        extra = sorted(set(revs) - used)
        if extra:
            return bad(revs[extra[0]]["event_seq"], f"{extra[0][0]} revision {extra[0][1]} is stored but not in the record")
        if expect_head and expect_head != prev:
            return {"ok": False, "entries": len(ev), "at": len(ev), "why": "the newest entry is not the one you expected: entries may have been removed", "head": prev}
        return {"ok": True, "entries": len(ev), "at": 0, "why": "", "head": prev}


def _check_doc_id(doc_id: str) -> None:
    if not isinstance(doc_id, str) or len(doc_id) > MAX_DOC_ID or not DOC_ID.fullmatch(doc_id) or ".." in doc_id:
        raise ServerError(400, "bad_doc_id", "A document id looks like dec/CL-014 or sign/CL-014/SE: a kind, then one to three names of letters, digits, . _ : or -.")


def _like(prefix: str) -> str:
    return prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
