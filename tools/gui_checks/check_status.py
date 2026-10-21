#!/usr/bin/env python3
"""Check an agent's status file, the way a finished piece of work is handed back when several agents work on one task.

    python3 tools/gui_checks/check_status.py status.json [--root DIR]

Format reqin-agent-status/1 (JSON):

    {"format": "reqin-agent-status/1",
     "agent": "who or what role",
     "task": "one sentence",
     "state": "done" | "partial" | "blocked",
     "files": ["paths of the files this agent wrote or changed"],
     "ran": [{"command": "python3 tools/gui_checks/probe.py ...", "exit_code": 0}, {"command": "...", "exit_code": 1, "expected_exit_code": 1}],
     "not_checked": ["what was not looked at or not run"],
     "blocked_on": "what stopped it, or null"}

What is refused, and why: "done" with no command run (a claim with no check behind it); "done" while a command did not exit as expected (`expected_exit_code`, default 0,
is there for the deliberate break that must fail); "done" with an empty `not_checked` (nothing is checked completely: say what was left); "blocked" with no reason;
a file listed that does not exist under --root. The check is about the form of the report. It cannot tell whether the commands listed were really run or whether the
files are good: that is what the merge gate (`hardcode_scan.py` and `probe.py`, run by whoever merges) is for. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

FORMAT = "reqin-agent-status/1"
STATES = ("done", "partial", "blocked")


def check(status, root: Path | None = None) -> list[str]:
    if not isinstance(status, dict):
        return ["the status file must be a JSON object"]
    errs: list[str] = []
    if status.get("format") != FORMAT:
        errs.append("format must be %r" % FORMAT)
    for k in ("agent", "task"):
        if not isinstance(status.get(k), str) or not status[k].strip():
            errs.append("%s must be a sentence" % k)
    state = status.get("state")
    if state not in STATES:
        errs.append("state must be one of %s" % ", ".join(STATES))
    files = status.get("files")
    if not isinstance(files, list) or not all(isinstance(f, str) and f for f in files):
        errs.append("files must be a list of paths (it may be empty)")
        files = []
    ran = status.get("ran")
    if not isinstance(ran, list):
        errs.append("ran must be a list")
        ran = []
    for i, r in enumerate(ran):
        if not (isinstance(r, dict) and isinstance(r.get("command"), str) and r["command"].strip() and isinstance(r.get("exit_code"), int) and not isinstance(r.get("exit_code"), bool)):
            errs.append("ran[%d] needs a command and an integer exit_code" % i)
        elif "expected_exit_code" in r and (not isinstance(r["expected_exit_code"], int) or isinstance(r["expected_exit_code"], bool)):
            errs.append("ran[%d].expected_exit_code must be an integer" % i)
    nc = status.get("not_checked")
    if not isinstance(nc, list) or not all(isinstance(x, str) and x.strip() for x in nc):
        errs.append("not_checked must be a list of sentences")
        nc = []
    if state == "done":
        if not ran:
            errs.append("state is done but no command was run: a claim needs a check behind it")
        for i, r in enumerate(ran):
            if isinstance(r, dict) and isinstance(r.get("exit_code"), int) and r["exit_code"] != r.get("expected_exit_code", 0):
                errs.append("state is done but ran[%d] exited %d, not %d: %s" % (i, r["exit_code"], r.get("expected_exit_code", 0), r["command"][:80]))
        if not nc:
            errs.append("state is done but not_checked is empty: nothing is checked completely, say what was left")
        if status.get("blocked_on"):
            errs.append("state is done but blocked_on is set")
    if state == "blocked" and not (isinstance(status.get("blocked_on"), str) and status["blocked_on"].strip()):
        errs.append("state is blocked but blocked_on does not say what stopped it")
    if root is not None:
        for f in files:
            p = (root / f).resolve()
            if root.resolve() not in p.parents and p != root.resolve():
                errs.append("file %s is outside the project folder" % f)
            elif not p.exists():
                errs.append("file %s does not exist" % f)
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("status")
    ap.add_argument("--root", help="the project folder; every file listed must exist under it")
    a = ap.parse_args(argv)
    try:
        data = json.loads(Path(a.status).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("cannot read %s: %s" % (a.status, e))
        return 1
    errs = check(data, Path(a.root) if a.root else None)
    for e in errs:
        print("  " + e)
    print("%s: %s" % (a.status, "ok" if not errs else "%d problem%s" % (len(errs), "" if len(errs) == 1 else "s")))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
