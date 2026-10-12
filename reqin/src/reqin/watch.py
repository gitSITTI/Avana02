"""Watch a folder of exports and re-ingest what changed.  `reqin watch DIR --out OUT`

For teams whose real route is "someone drops the nightly export into a folder" (DOORS export, MSOSA ReqIF, an Agility xlsx).

Guarantees (each is tested in tests/test_watch.py):
* The watched folder is NEVER written to: outputs and state live elsewhere, and the command refuses an --out inside it.
* A file is read only after it has been quiet for `settle` seconds, so a half-copied export is never ingested.
* A file is re-ingested only when its content hash changed. A file that failed is not retried until it changes (no hot loop).
* Every run says what changed since the last one: requirements added / removed / changed (by stable MID and fingerprint).
* Prose formats (docx, pdf) are never picked up by accident: they need an explicit rule, because their records must be verified by a person.
* Symlinks, hidden files and editor/office lock files (~$x.xlsx, .x.swp) are ignored.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

import yaml

from .adapter import Source, pick_adapter
from .ingest import ingest
from .mapping import Profile

DEFAULT_INCLUDE = ["*.csv", "*.xlsx", "*.xlsm", "*.reqif", "*.reqifz", "*.sysml"]
IGNORE_SUFFIXES = (".tmp", ".part", ".crdownload", ".swp", ".swx", ".bak")
STATE_VERSION = 1


class WatchError(RuntimeError):
    pass


@dataclass
class Rule:
    match: str                                  # glob against the path relative to the watched folder
    adapter: str | None = None
    profile: str | None = None                  # path, relative to the rules file
    options: dict[str, Any] = field(default_factory=dict)
    namespace: str | None = None


def load_rules(path: Path) -> list[Rule]:
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = []
    for r in d.get("rules", []):
        prof = r.get("profile")
        out.append(Rule(match=r["match"], adapter=r.get("adapter"), profile=str((path.parent / prof).resolve()) if prof else None,
                        options=r.get("options") or {}, namespace=r.get("namespace")))
    return out


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe(rel: str) -> str:
    return rel.replace("\\", "/").replace("/", "__").replace("..", "_")


@dataclass
class Event:
    event: str                                  # ingested | unchanged | deferred | skipped | error
    file: str
    detail: dict[str, Any] = field(default_factory=dict)

    def line(self) -> str:
        return json.dumps({"event": self.event, "file": self.file, **self.detail}, default=str, sort_keys=True)


class Watcher:
    def __init__(self, watch_dir: Path, out_dir: Path, state_dir: Path | None = None, rules: list[Rule] | None = None,
                 settle: float = 10.0, recursive: bool = False, include: list[str] | None = None, max_mb: int = 500,
                 clock: Callable[[], float] = time.time) -> None:
        self.dir, self.out = watch_dir.resolve(), out_dir.resolve()
        self.state_dir = (state_dir or (self.out / ".reqin-watch")).resolve()
        for label, p in (("--out", self.out), ("--state-dir", self.state_dir)):
            if p == self.dir or self.dir in p.parents:
                raise WatchError(f"{label} {p} is inside the watched folder {self.dir}. Outputs must go elsewhere: "
                                 "the watched folder is never written to.")
        self.rules, self.settle, self.recursive, self.max_bytes, self.clock = rules or [], settle, recursive, max_mb * 1024 * 1024, clock
        self.include = include or DEFAULT_INCLUDE
        self.state_path = self.state_dir / "state.json"
        self.state = self._load_state()

    # ---- state ------------------------------------------------------------------------------------
    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"version": STATE_VERSION, "files": {}}
        try:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
            assert st.get("version") == STATE_VERSION and isinstance(st.get("files"), dict)
            return st
        except (ValueError, AssertionError):
            raise WatchError(f"{self.state_path} is unreadable or from another version. Move it aside to start over "
                             "(everything will be re-ingested once); it is not deleted automatically so no history is lost silently.") from None

    def _save_state(self) -> None:
        _atomic_write(self.state_path, json.dumps(self.state, indent=1, sort_keys=True))

    def _snap_path(self, rel: str) -> Path:
        return self.state_dir / "snap" / (hashlib.sha1(rel.encode()).hexdigest() + ".json")

    # ---- what to look at ------------------------------------------------------------------------------
    def _rule_for(self, rel: str) -> Rule | None:
        for r in self.rules:
            if fnmatch.fnmatch(rel, r.match) or fnmatch.fnmatch(Path(rel).name, r.match):
                return r
        return None

    def _candidates(self) -> Iterator[tuple[str, Path]]:
        walker = os.walk(self.dir, followlinks=False) if self.recursive else [(str(self.dir), [], os.listdir(self.dir))]
        for root, dirs, files in walker:
            dirs[:] = sorted(d for d in dirs if not d.startswith(".") and not os.path.islink(os.path.join(root, d)))
            for name in sorted(files):
                p = Path(root) / name
                rel = p.relative_to(self.dir).as_posix()
                if name.startswith((".", "~$")) or name.endswith(IGNORE_SUFFIXES) or p.is_symlink() or not p.is_file():
                    continue
                rule = self._rule_for(rel)
                if rule is None and (self.rules or not any(fnmatch.fnmatch(name.lower(), g) for g in self.include)):
                    continue                    # with rules, only matching files; without, only the default structured/tabular types
                yield rel, p

    # ---- one pass ----------------------------------------------------------------------------------------
    def run_once(self) -> list[Event]:
        events: list[Event] = []
        present = set()
        for rel, p in self._candidates():
            present.add(rel)
            try:
                events.append(self._handle(rel, p))
            except Exception as e:  # one bad file must never stop the others
                events.append(self._fail(rel, p, e))
        for rel in sorted(set(self.state["files"]) - present):
            if self.state["files"][rel].get("status") != "gone":
                self.state["files"][rel]["status"] = "gone"
                events.append(Event("gone", rel, {"note": "no longer in the folder; earlier outputs are kept"}))
        self._save_state()
        return events

    def _handle(self, rel: str, p: Path) -> Event:
        st = p.stat()
        if st.st_size > self.max_bytes:
            return Event("skipped", rel, {"reason": f"larger than {self.max_bytes // (1024 * 1024)} MB"})
        age = self.clock() - st.st_mtime
        if age < self.settle:
            return Event("deferred", rel, {"reason": f"modified {age:.0f}s ago; waiting for {self.settle:.0f}s of quiet"})
        sha = file_sha(p)
        prev = self.state["files"].get(rel)
        if prev and prev.get("sha") == sha and prev.get("status") in ("ok", "failed", "skipped"):
            return Event("unchanged", rel, {"sha": sha[:12], "status": prev["status"]})
        rule = self._rule_for(rel) or Rule(match=rel)
        src = Source(str(p), dict(rule.options))
        adapter = pick_adapter(src, rule.adapter)
        profile = Profile.from_yaml(Path(rule.profile).read_text(encoding="utf-8")) if rule.profile else None
        res = ingest(src, profile=profile, adapter=adapter, namespace=rule.namespace)
        now = {q.mid: q.fingerprint for q in res.requirements}
        sp = self._snap_path(rel)
        old = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else None
        diff = None if old is None else {"added": len(now.keys() - old.keys()), "removed": len(old.keys() - now.keys()),
                                          "changed": sum(1 for m in now.keys() & old.keys() if now[m] != old[m]),
                                          "unchanged": sum(1 for m in now.keys() & old.keys() if now[m] == old[m])}
        folder = self.out / _safe(rel)
        jl = "".join(json.dumps(asdict(q), default=str, sort_keys=True) + "\n" for q in res.requirements)
        report = {"file": rel, "sha256": sha, "adapter": adapter.name, "ingested_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.clock())),
                  "diff_since_previous": diff, "report": res.report}
        _atomic_write(folder / f"{sha[:12]}.jsonl", jl)
        _atomic_write(folder / f"{sha[:12]}.report.json", json.dumps(report, indent=1, default=str, sort_keys=True))
        _atomic_write(folder / "latest.json", json.dumps({"sha256": sha, "requirements": f"{sha[:12]}.jsonl", "report": f"{sha[:12]}.report.json"}, indent=1))
        _atomic_write(sp, json.dumps(now, sort_keys=True))
        self.state["files"][rel] = {"sha": sha, "size": st.st_size, "status": "ok", "requirements": len(res.requirements),
                                    "rejected": len(res.rejected), "ingested_at": report["ingested_at"]}
        detail = {"sha": sha[:12], "adapter": adapter.name, "requirements": len(res.requirements), "rejected": len(res.rejected),
                  "profile_proposed": res.report["profile_proposed"], "warnings": len(res.report["warnings"])}
        if diff:
            detail.update({k: diff[k] for k in ("added", "removed", "changed")})
        else:
            detail["first_time"] = True
        return Event("ingested", rel, detail)

    def _fail(self, rel: str, p: Path, e: Exception) -> Event:
        try:
            sha = file_sha(p)
        except OSError:
            sha = ""
        msg = f"{type(e).__name__}: {e}"
        # A file we were asked to read (by extension or by rule) that cannot be read is an ERROR, never a quiet skip.
        self.state["files"][rel] = {"sha": sha, "status": "failed", "error": msg[:500]}
        return Event("error", rel, {"error": msg[:300], "sha": sha[:12]})

    def run_forever(self, interval: float, emit: Callable[[Event], None], stop: Callable[[], bool] = lambda: False,
                    sleep: Callable[[float], None] = time.sleep) -> None:
        while not stop():
            for ev in self.run_once():
                if ev.event not in ("unchanged",):
                    emit(ev)
            sleep(interval)
