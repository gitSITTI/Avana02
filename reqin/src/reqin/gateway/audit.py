"""The gateway's own record of what it was asked and what it did: one JSON line per request, each carrying the SHA-256 of the one before, so a line that is edited or
removed from the middle is noticed. It holds who asked, which requirements were named, the gate's answer and the model's status: never a prompt, never an answer."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64
FIELDS = ("seq", "at", "project", "person", "requirements", "code", "level", "ok", "upstream", "prompt_bytes", "prev")


def _canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(row: dict[str, Any]) -> str:
    return hashlib.sha256((row["prev"] + "|" + _canon({k: v for k, v in row.items() if k != "hash"})).encode("utf-8")).hexdigest()


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock = threading.Lock()
        self.seq, self.prev = 0, GENESIS
        if self.path.exists():
            res = verify_log(self.path)
            if not res["ok"]:
                raise ValueError(f"{self.path} does not check out ({res['why']}); it is not appended to")
            self.seq, self.prev = res["entries"], res["head"]

    def add(self, *, project: str, person: str, requirements: list[str], code: str, level: str, ok: bool, upstream: int | None, prompt_bytes: int) -> dict[str, Any]:
        with self.lock:
            row = {"seq": self.seq + 1, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "project": project, "person": person, "requirements": requirements,
                   "code": code, "level": level, "ok": ok, "upstream": upstream, "prompt_bytes": prompt_bytes, "prev": self.prev}
            row["hash"] = _hash(row)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(_canon(row) + "\n")
                f.flush()
                os.fsync(f.fileno())
            self.seq, self.prev = row["seq"], row["hash"]
            return row


def verify_log(path: str | Path, expect_head: str = "") -> dict[str, Any]:
    """Recompute the chain. {ok, entries, head} or {ok: False, at: line number, why}."""
    prev, n = GENESIS, 0
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError as e:
        return {"ok": False, "at": 0, "why": f"cannot read the file: {e.strerror or e}"}
    for i, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except ValueError:
            return {"ok": False, "at": i, "why": "the line is not JSON"}
        if not isinstance(row, dict) or set(row) != set(FIELDS) | {"hash"}:
            return {"ok": False, "at": i, "why": "the line does not have the entries of this record"}
        if row["seq"] != i:
            return {"ok": False, "at": i, "why": f"the entries are out of order or one is missing (expected {i}, found {row['seq']})"}
        if row["prev"] != prev:
            return {"ok": False, "at": i, "why": "it does not follow the entry before it"}
        if _hash(row) != row["hash"]:
            return {"ok": False, "at": i, "why": "its contents no longer match its fingerprint"}
        prev, n = row["hash"], i
    if expect_head and prev != expect_head:
        return {"ok": False, "at": n, "why": "the newest entry is not the one written down last time: the record was cut short or rewritten"}
    return {"ok": True, "entries": n, "head": prev}
