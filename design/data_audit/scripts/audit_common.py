"""Shared by the scripts in this folder: where things are, the session folder, the findings every check writes, and the append-only minutes. Standard library only."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import shlex
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
REPO = KIT.parent.parent
FORMAT = "reqin-audit/1"
FINDING_FORMAT = "reqin-audit-finding/1"
SEVERITIES = ("high", "medium", "low", "info")
CMD = "python3 " + shlex.quote(str(Path(__file__).resolve().parent / "audit.py"))


def q(arg) -> str:
    """One argument of a command as it can be copied: quoted if it needs it, left alone if the caller already wrapped it in quotes (a placeholder such as "WHAT THEY SAID")."""
    a = str(arg)
    if len(a) >= 2 and a[0] == a[-1] and a[0] in "\"'":
        return a
    return shlex.quote(a)


def cmd(verb: str, *args: str) -> str:
    """The command as it can be copied. Relative to where the audit was started when that is shorter."""
    try:
        base = str(Path(__file__).resolve().parent.relative_to(Path.cwd().resolve()) / "audit.py")
    except ValueError:
        base = str(Path(__file__).resolve().parent / "audit.py")
    return " ".join(["python3", shlex.quote(base), verb, *[q(a) for a in args]])


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def skills() -> dict:
    return {s["id"]: s for s in read_json(KIT / "skills.json")["skills"]}


def hats() -> dict:
    return {h["id"]: h for h in read_json(KIT / "hats.json")["hats"]}


def hat_order() -> list:
    return read_json(KIT / "hats.json")["order"]


# ------------------------------------------------------------------------------------------------ the session folder
def sess_path(session: str) -> Path:
    return Path(session)


def inside_a_git_tree(path: Path) -> Path | None:
    """The folder holding a .git above (or at) this path, or None. A session holds the person's data and must not sit in a repository."""
    p = path.resolve()
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return d
    return None


def load_session(session: str) -> dict:
    f = sess_path(session) / "session.json"
    if not f.is_file():
        raise SystemExit("no audit session here: %s (start one with: %s)" % (session, cmd("init", session, "--page", "URL")))
    return read_json(f)


def save_session(session: str, s: dict) -> None:
    write_json(sess_path(session) / "session.json", s)


_held: dict = {}


@contextlib.contextmanager
def locked(session: str, wait: float = 30.0):
    """One command at a time writes to a session folder: several agents (one per hat) can share it. A folder `.lock` is made for as long as the block runs; one older than a
    minute is taken to be left by a command that died. Re-entrant."""
    key = (str(Path(session).resolve()), threading.get_ident())      # held by this thread: a second request from the same thread passes, another thread waits
    if _held.get(key):
        _held[key] += 1
        try:
            yield
        finally:
            _held[key] -= 1
        return
    d = sess_path(session)
    d.mkdir(parents=True, exist_ok=True)
    lock = d / ".lock"
    t0 = time.monotonic()
    while True:
        try:
            os.mkdir(lock)
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 60:
                    os.rmdir(lock)
                    continue
            except OSError:
                pass
            if time.monotonic() - t0 > wait:
                raise SystemExit("another audit command has been using this session folder for more than %d seconds (%s). If none is running, delete the folder %s." % (wait, d, lock))
            time.sleep(0.05)
    _held[key] = 1
    try:
        yield
    finally:
        _held.pop(key, None)
        try:
            os.rmdir(lock)
        except OSError:
            pass


def update_session(session: str, change) -> dict:
    """Read the session, let `change(session_dict)` alter it, write it back, all while no other command writes."""
    with locked(session):
        s = load_session(session)
        change(s)
        save_session(session, s)
        return s


# ------------------------------------------------------------------------------------------------ findings
def finding(fid: str, severity: str, where: str, what: str, evidence: str = "", next_step: str = "") -> dict:
    """One thing a check found. `where` says where on the screen or in the data; `evidence` is what was seen, short; `next_step` is what a person or an agent can do about it."""
    if severity not in SEVERITIES:
        raise ValueError("severity must be one of %s, not %r" % (", ".join(SEVERITIES), severity))
    return {"id": fid, "severity": severity, "where": where, "what": what, "evidence": evidence, "next_step": next_step}


def verdict_of(findings: list, ran: bool = True) -> str:
    """not-run, problem (something high), attention (anything else that is not just information), clear (only information, or nothing)."""
    if not ran:
        return "not-run"
    sev = {f["severity"] for f in findings}
    if "high" in sev:
        return "problem"
    if sev & {"medium", "low"}:
        return "attention"
    return "clear"


def result(skill: str, hat: str, summary: str, findings: list, counts: dict | None = None, not_checked: list | None = None, files: list | None = None, verdict: str | None = None) -> dict:
    return {"format": FINDING_FORMAT, "skill": skill, "hat": hat, "ran_at": now(), "verdict": verdict or verdict_of(findings), "summary": summary,
            "findings": findings, "counts": counts or {}, "not_checked": not_checked or [], "files": files or []}


def save_result(session: str, res: dict) -> Path:
    p = sess_path(session) / "findings" / (res["skill"] + ".json")
    with locked(session):
        write_json(p, res)

        def note(s):
            s.setdefault("runs", {})[res["skill"]] = {"hat": res["hat"], "at": res["ran_at"], "verdict": res["verdict"]}
            s.get("skipped", {}).pop(res["skill"], None)
        update_session(session, note)
    return p


def load_results(session: str) -> dict:
    out = {}
    d = sess_path(session) / "findings"
    if d.is_dir():
        for p in sorted(d.glob("*.json")):
            out[p.stem] = read_json(p)
    return out


# ------------------------------------------------------------------------------------------------ the minutes (add only)
def _entry_hash(prev: str, body: dict) -> str:
    return hashlib.sha256((prev + json.dumps(body, sort_keys=True, ensure_ascii=False)).encode("utf-8")).hexdigest()[:16]


def minutes_entries(session: str) -> list:
    p = sess_path(session) / "minutes.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()] if p.is_file() else []


def add_minute(session: str, hat: str, kind: str, text: str, said_by: str = "") -> dict:
    """Append one entry. Each carries the fingerprint of the one before, so a changed or removed entry shows. The number and fingerprint of the last entry are also kept in
    minutes_head.json, so entries cut off the end show too (a person who can change both files can still change both: this shows a slip, it does not stop a person)."""
    with locked(session):
        entries = minutes_entries(session)
        prev = entries[-1]["hash"] if entries else ""
        body = {"n": len(entries) + 1, "at": now(), "hat": hat, "kind": kind, "text": text.strip(), "said_by": said_by.strip()}
        entry = {**body, "prev": prev, "hash": _entry_hash(prev, body)}
        p = sess_path(session) / "minutes.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        write_json(sess_path(session) / "minutes_head.json", {"n": entry["n"], "hash": entry["hash"]})
        write_minutes_md(session)
        return entry


def minutes_chain_problems(session: str) -> list:
    """Entries whose fingerprint or numbering is not what the one before gives: a changed, removed or reordered entry."""
    bad, prev = [], ""
    for i, e in enumerate(minutes_entries(session), 1):
        body = {k: e[k] for k in ("n", "at", "hat", "kind", "text", "said_by")}
        if e.get("prev") != prev or e.get("hash") != _entry_hash(prev, body) or e["n"] != i:
            bad.append("entry %d does not follow from the one before it" % i)
        prev = e.get("hash", "")
    f = sess_path(session) / "minutes_head.json"
    head = read_json(f) if f.is_file() else None
    if head:
        entries = minutes_entries(session)
        if len(entries) < head["n"]:
            bad.append("the minutes end at entry %d but minutes_head.json says there were %d: the last %d entr%s gone" % (len(entries), head["n"], head["n"] - len(entries), "y is" if head["n"] - len(entries) == 1 else "ies are"))
        elif len(entries) >= head["n"] and entries[head["n"] - 1].get("hash") != head["hash"]:
            bad.append("entry %d is not the one minutes_head.json recorded" % head["n"])
    return bad


def write_minutes_md(session: str) -> None:
    L = ["# Minutes", "", "Entries are only added, never changed. Each carries the fingerprint of the one before.", ""]
    for e in minutes_entries(session):
        who = (" · " + e["said_by"]) if e.get("said_by") else ""
        L.append("%d. %s · %s · %s%s: %s" % (e["n"], e["at"], e["hat"], e["kind"], who, e["text"]))
    (sess_path(session) / "MINUTES.md").write_text("\n".join(L) + "\n", encoding="utf-8")


def short(s: str, n: int = 140) -> str:
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def die(msg: str):
    raise SystemExit(msg)
