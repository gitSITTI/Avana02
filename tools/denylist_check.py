#!/usr/bin/env python3
"""Fail when a term from a private list shows up in this repository.

The list is the names you never want published or committed: a program name, a person, an employer, a host, a part-number prefix.
It is NOT stored in the repository, because that would publish the very names it hides.

    Where the list comes from (first one that exists):
      DENYLIST_TERMS   the terms themselves, one per line, in an environment variable (a CI secret)
      DENYLIST_FILE    path to a file of terms (a GitLab "File" variable, or a master copy kept outside the clone)
      .denylist        an untracked file in the repository root (git-ignored)

    Format: one term per line. Blank lines and lines starting with # are ignored.
      plain term     matched case-insensitively, anywhere in the text (it also matches inside longer words).
      ~term          separator-insensitive: "~acme42" matches "ACME-42", "Acme 42", "acme_42" and "ACME42s" but not "pacme42" or "acme421".
                     It must start where a word starts, and must not run on into more characters of the same kind
                     (a term ending in a digit is not followed by a digit, one ending in a letter is not followed by a letter).

    Modes:
      status               say how many terms were loaded (never the terms) and from where
      staged               staged files, their names, and a tracked copy of the list itself (the pre-commit hook)
      message FILE         a commit message file, and the author and committer identity git is about to use (commit-msg hook)
      tree                 every tracked and not-yet-ignored file and file name in the working tree
      history [REV...]     author, committer and message of every commit, every added or removed line, every file name
                           and every branch and tag name (default: all refs)
      ci                   tree + history; fails when there is no list, unless DENYLIST_OPTIONAL=1 (pull requests from forks)

What it prints: file and line locations, with any part of a location that matches a term (a file or branch name) replaced by [term]. Never a term and never the text around one. On GitHub Actions and GitLab CI the log
may be public, so there it prints only a count. Run `tree` and `history` locally to find the places.

It catches the terms you listed. It does not know what you forgot, and it skips binary files (images, PDFs, archives).
If a term already reached a public repository, treat it as exposed: rewriting the latest commit does not remove it from history.

Exit codes: 0 clean (or no list, locally), 1 found something (or no list in `ci`), 2 bad usage.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

LIST_NAME = ".denylist"
SEP = r"[\s._\-]*"
MAX_SHOWN = 60


class Terms:
    def __init__(self, patterns: list[str], source: str) -> None:
        self.count = len(patterns)
        self.source = source
        self.rx = re.compile("|".join(patterns), re.I) if patterns else None

    def hit(self, text: str) -> bool:
        return bool(self.rx and self.rx.search(text))

    def mask(self, text: str) -> str:
        """The text with every match replaced, so a location that contains a term (a file name, a branch) never prints it."""
        return self.rx.sub("[term]", text) if self.rx else text


def pattern_for(line: str) -> str | None:
    t = line.strip()
    if not t or t.startswith("#"):
        return None
    if t.startswith("~"):
        chars = [c for c in t[1:] if c not in " \t._-"]
        if not chars:
            return None
        tail = r"(?![0-9])" if chars[-1].isdigit() else r"(?![A-Za-z])"
        return r"(?<![A-Za-z0-9])" + SEP.join(re.escape(c) for c in chars) + tail
    return re.escape(t)


def load_terms() -> Terms | None:
    text, source = os.environ.get("DENYLIST_TERMS", ""), "DENYLIST_TERMS"
    if not text.strip():
        for label, path in (("DENYLIST_FILE", os.environ.get("DENYLIST_FILE", "")), (LIST_NAME, str(root() / LIST_NAME))):
            if path and Path(path).is_file():
                text, source = Path(path).read_text(encoding="utf-8", errors="replace"), label
                break
        else:
            return None
    patterns = [p for p in (pattern_for(line) for line in text.replace("\r", "").split("\n")) if p]
    return Terms(patterns, source) if patterns else None


def git(*args: str, check: bool = True) -> bytes:
    done = subprocess.run(["git", *args], capture_output=True)
    if check and done.returncode != 0:
        raise SystemExit(f"denylist: git {args[0]} failed: {done.stderr.decode(errors='replace').strip()[:200]}")
    return done.stdout


def root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True)
    return Path(out.stdout.decode().strip()) if out.returncode == 0 else Path.cwd()


def is_binary(data: bytes) -> bool:
    return b"\0" in data[:8000]


class Notes:
    def __init__(self, terms: Terms | None = None) -> None:
        self.items: list[str] = []
        self.terms = terms

    def add(self, where: str) -> None:
        self.items.append(self.terms.mask(where) if self.terms else where)

    def text(self, terms: Terms, label: str, data: bytes) -> None:
        if is_binary(data):
            return
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            if terms.hit(line):
                self.add(f"{label}:{number}")

    def name(self, terms: Terms, path: str) -> None:
        if terms.hit(path):
            self.add(f"{path} (file name)")
        if path == LIST_NAME or path.endswith("/" + LIST_NAME):
            self.add(f"{path} (the term list itself must never be tracked)")


def check_staged(terms: Terms, notes: Notes) -> None:
    names = [n for n in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode("utf-8", "replace").split("\0") if n]
    for path in names:
        notes.name(terms, path)
        notes.text(terms, path, git("show", f":{path}", check=False))


def check_message(terms: Terms, notes: Notes, message_file: str) -> None:
    if terms.hit(Path(message_file).read_text(encoding="utf-8", errors="replace")):
        notes.add("commit message")
    for label, var in (("author identity", "GIT_AUTHOR_IDENT"), ("committer identity", "GIT_COMMITTER_IDENT")):
        if terms.hit(git("var", var, check=False).decode("utf-8", "replace")):
            notes.add(label + " (git config user.name / user.email)")


def check_tree(terms: Terms, notes: Notes) -> None:
    top = root()
    listing = git("ls-files", "-z", "--cached", "--others", "--exclude-standard").decode("utf-8", "replace")
    for path in [n for n in listing.split("\0") if n]:
        notes.name(terms, path)
        file = top / path
        if file.is_file() and not file.is_symlink():
            notes.text(terms, path, file.read_bytes())


def check_history(terms: Terms, notes: Notes, revs: list[str]) -> None:
    span = revs or ["--all"]
    meta = git("log", *span, "--format=%H%x00%an%x00%ae%x00%cn%x00%ce%x00%B%x01", check=False).decode("utf-8", "replace")
    for record in meta.split("\x01"):
        fields = record.strip("\n").split("\x00")
        if len(fields) == 6 and terms.hit(" ".join(fields[1:])):
            notes.add(f"commit {fields[0][:8]} (author, committer or message)")
    refs = git("for-each-ref", "--format=%(refname) %(taggername) %(taggeremail) %(contents)", check=False).decode("utf-8", "replace")
    for line in refs.split("\n"):
        if terms.hit(line):
            notes.add("a branch or tag (name, tagger or tag message)")
    # Every added or removed line of every commit, streamed: a term deleted in a later commit is still in history.
    proc = subprocess.Popen(["git", "log", *span, "-p", "-U0", "--no-color", "--no-ext-diff", "--no-renames", "--format=%x01%H"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    sha, path, seen = "", "", set()
    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.decode("utf-8", "replace")
        if line.startswith("\x01"):
            sha, path = line[1:].strip()[:8], ""
        elif line.startswith("diff --git "):
            path = line.rstrip("\n").split(" b/", 1)[-1]
            if terms.hit(path) and (sha, path, "name") not in seen:
                seen.add((sha, path, "name"))
                notes.add(f"commit {sha} {path} (file name)")
        elif line[:1] in ("+", "-") and not line.startswith(("+++", "---")) and terms.hit(line):
            if (sha, path) not in seen:
                seen.add((sha, path))
                notes.add(f"commit {sha} {path}")
    proc.wait()


def report(notes: Notes) -> int:
    count = len(notes.items)
    if count == 0:
        return 0
    if os.environ.get("GITHUB_ACTIONS") or os.environ.get("GITLAB_CI"):
        print(f"denylist: found {count} place(s) containing a term from the private list.", file=sys.stderr)
        print("denylist: locations are hidden because a CI log can be public. Run `python tools/denylist_check.py tree` and `... history` locally.", file=sys.stderr)
    else:
        print(f"denylist: found {count} place(s) containing a term from your private list:", file=sys.stderr)
        shown = sorted(set(notes.items))
        for place in shown[:MAX_SHOWN]:
            print("  " + place, file=sys.stderr)
        if len(shown) > MAX_SHOWN:
            print(f"  ...and {len(shown) - MAX_SHOWN} more", file=sys.stderr)
        print("denylist: the matched text is not shown on purpose. Open each place and remove it.", file=sys.stderr)
    return 1


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else ""
    if mode not in {"status", "staged", "message", "tree", "history", "ci"}:
        print(__doc__, file=sys.stderr)
        return 2
    terms = load_terms()
    if mode == "status":
        print(f"denylist: {terms.count} term(s) loaded from {terms.source}" if terms else "denylist: no term list found (looked for DENYLIST_TERMS, DENYLIST_FILE, ./.denylist)")
        return 0 if terms else 1
    if terms is None:
        if mode == "ci" and not os.environ.get("DENYLIST_OPTIONAL"):
            print("denylist: no term list is set, so the private-term check could not run.", file=sys.stderr)
            print("denylist: add the repository secret DENYLIST (GitLab: a File variable named DENYLIST_FILE). See SECURITY.md.", file=sys.stderr)
            return 1
        if mode == "ci" and os.environ.get("GITHUB_ACTIONS"):
            print("::warning::The private-term list is not available to this run (a pull request from a fork gets no secrets). The denylist check did not run.")
        else:
            print("denylist: no term list found (DENYLIST_TERMS, DENYLIST_FILE or ./.denylist), so the private-term check did not run.", file=sys.stderr)
        return 0
    notes = Notes(terms)
    if mode == "staged":
        check_staged(terms, notes)
    elif mode == "message":
        if len(argv) < 2:
            print("usage: denylist_check.py message <commit-message-file>", file=sys.stderr)
            return 2
        check_message(terms, notes, argv[1])
    elif mode == "tree":
        check_tree(terms, notes)
    elif mode == "history":
        check_history(terms, notes, argv[1:])
    else:
        check_tree(terms, notes)
        check_history(terms, notes, [])
    return report(notes)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
