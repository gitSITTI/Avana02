"""The private-term check must never print a term, even when the term is part of a location it has to name.

`tools/denylist_check.py` prints the place of each hit (file and line, or commit and file) and promises never to print a term or the text around one. A file or a branch whose NAME holds
a term is a place that has to be named, so the matched part is printed as [term]. This test plants a made-up term in a file name and a directory name and checks that nothing the tool
prints contains it, and that on CI (GITHUB_ACTIONS set) not even a location is printed.

What this proves: in temporary repositories, the term is absent from everything printed by `tree`, `history` and `staged`, and the masked location is still useful. What it does not prove:
that the real list is complete. Standard library only, so it runs in every job.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOOL = REPO / "tools" / "denylist_check.py"
TERM = "zorbl-quux-7"          # made up, used only here


def sh(*args, cwd, env=None):
    e = {k: v for k, v in os.environ.items() if not k.startswith(("GITHUB_ACTIONS", "GITLAB_CI", "DENYLIST"))}
    e.update(env or {})
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, env=e)


def planted(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    for c in (["init", "-q", "-b", "main"], ["config", "user.email", "dev@example.com"], ["config", "user.name", "Dev"]):
        sh("git", *c, cwd=r)
    (r / f"{TERM}-dir").mkdir()
    (r / f"{TERM}-dir" / "inside.txt").write_text("plain\n")
    (r / f"{TERM}.md").write_text("plain\n")
    sh("git", "add", "-A", cwd=r)
    return r


def test_a_term_in_a_file_name_is_masked_in_every_mode(tmp_path):
    r = planted(tmp_path)
    env = {"DENYLIST_TERMS": TERM}
    sh("git", "commit", "-qm", "files with odd names", cwd=r)
    for mode in ("tree", "history", "ci"):
        done = sh(sys.executable, str(TOOL), mode, cwd=r, env=env)
        out = done.stdout + done.stderr
        assert done.returncode == 1, mode
        assert TERM not in out, f"`{mode}` printed the term: {out!r}"
        assert "[term]" in out, f"`{mode}` should still say where, with the term masked"


def test_staged_names_are_masked_too(tmp_path):
    r = planted(tmp_path)
    done = sh(sys.executable, str(TOOL), "staged", cwd=r, env={"DENYLIST_TERMS": TERM})
    out = done.stdout + done.stderr
    assert done.returncode == 1 and TERM not in out and "[term]" in out


def test_on_ci_not_even_a_location_is_printed(tmp_path):
    r = planted(tmp_path)
    done = sh(sys.executable, str(TOOL), "tree", cwd=r, env={"DENYLIST_TERMS": TERM, "GITHUB_ACTIONS": "true"})
    out = done.stdout + done.stderr
    assert done.returncode == 1 and "found" in out and "inside.txt" not in out and "[term]" not in out and TERM not in out
