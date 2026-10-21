#!/usr/bin/env python3
"""Fail if the repository contains something that looks like real program data.

    python tools/check_no_real_data.py                 # checks tracked files (git ls-files), or every file if not in git
    python tools/check_no_real_data.py --terms-file F  # also scan text files for the regexes in F (one per line)

What it checks (structure first, because that is what can be checked honestly):
  1. File types that requirement exports usually arrive in (.reqif, .mdzip, .sysml, .kpar, .xlsx, .csv, .docx, .pdf, .db ...)
     are refused anywhere except reqin/tests/fixtures_approved/.
  2. Folders named data/, private/, exports/ are refused.
  3. Files in fixtures_approved/ must each be named in fixtures_approved/APPROVALS.md (who approved, when, ticket).
  4. Any file over 3 MB is refused (database dumps, bundles, node_modules by accident).
  5. ALLOW_FILES: a short list of exact paths that are CODE with a blocked extension (today the DOORS export script,
     reqin/connectors/doors9/export_requirements.dxl, and the two Enterprise Architect query files, reqin/connectors/ea/requirements.sql
     and links.sql: SELECT statements over table names, no data). Only those exact paths are exempt from check 1; the size and term
     checks still apply to them, and a .dxl or .sql anywhere else is still refused.
  6. OPTIONAL: your own list of terms (program code names, part-number patterns, document-number prefixes) as regexes.
     Keep that list OUT of the repo: pass it as a masked CI variable FORBIDDEN_TERMS (newline-separated) or a local
     file that is git-ignored. If neither is given the script says so; it does not pretend to have scanned for terms.

This is a tripwire for honest mistakes. It cannot tell whether a file is sensitive; a person decides that, and records it in APPROVALS.md.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOW_DIR = "reqin/tests/fixtures_approved/"
APPROVALS = ALLOW_DIR + "APPROVALS.md"
BLOCKED_EXT = {
    ".reqif", ".reqifz", ".mdzip", ".kpar", ".sysml", ".xmi", ".uml", ".emx", ".dxl", ".rif",
    ".xlsx", ".xlsm", ".xls", ".csv", ".tsv", ".docx", ".doc", ".pdf", ".pptx",
    ".db", ".sqlite", ".sqlite3", ".mdb", ".accdb", ".sql", ".dump", ".bak", ".zip", ".7z", ".tar", ".gz",
}
# Reviewed code files that happen to carry a blocked extension. Exact repo-relative paths only; never a folder, never a pattern.
# Adding a path here is a code-review decision: the file must contain a script, not requirements.
ALLOW_FILES = {"reqin/connectors/doors9/export_requirements.dxl", "reqin/connectors/ea/requirements.sql", "reqin/connectors/ea/links.sql"}
BLOCKED_DIRS = {"data", "private", "exports"}
# The private-term lists (tools/denylist_check.py, and the regex list above) hold exactly the names they exist to hide, so they must never be tracked.
TERM_LIST_FILES = {".denylist", ".forbidden-terms"}
MAX_BYTES = 3 * 1024 * 1024
SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__", ".pytest_cache", ".cache"}
TEXT_EXT = {".md", ".txt", ".py", ".js", ".ts", ".tsx", ".json", ".yaml", ".yml", ".toml", ".html", ".css", ".excalidraw", ".sh", ".cfg", ".ini", ".xml"}


def list_files(root: Path) -> list[str]:
    # Tracked AND untracked-but-not-ignored files: a file you have not `git add`ed yet is exactly the one to catch before you do.
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, check=True).stdout
        files = [f for f in out.decode().split("\0") if f]
        if files:
            return files
    except (OSError, subprocess.CalledProcessError):
        pass
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            found.append(os.path.relpath(os.path.join(dirpath, fn), root).replace(os.sep, "/"))
    return sorted(found)


def load_terms(terms_file: str | None) -> list[re.Pattern]:
    lines: list[str] = []
    if terms_file:
        lines += Path(terms_file).read_text(encoding="utf-8").splitlines()
    lines += os.environ.get("FORBIDDEN_TERMS", "").splitlines()
    return [re.compile(x.strip(), re.I) for x in lines if x.strip() and not x.lstrip().startswith("#")]


def scan(root: Path, files: list[str], terms: list[re.Pattern]) -> list[str]:
    problems: list[str] = []
    approvals_text = ""
    ap = root / APPROVALS
    if ap.exists():
        approvals_text = ap.read_text(encoding="utf-8", errors="replace")
    for rel in files:
        p = root / rel
        if not p.is_file():
            continue
        parts = rel.split("/")
        in_allow = rel.startswith(ALLOW_DIR)
        ext = p.suffix.lower()
        if in_allow:
            name = parts[-1]
            if name not in ("README.md", "APPROVALS.md") and name not in approvals_text:
                problems.append(f"{rel}: not listed in {APPROVALS} (who approved it, when, under what ticket)")
        else:
            if ext in BLOCKED_EXT and rel not in ALLOW_FILES:
                problems.append(f"{rel}: file type {ext} may hold real requirements; only {ALLOW_DIR} may contain these, with an entry in APPROVALS.md")
            bad = BLOCKED_DIRS.intersection(parts[:-1])
            if bad:
                problems.append(f"{rel}: lives under a folder named {sorted(bad)[0]}/, which is reserved for real data and must not be committed")
        if parts[-1] in TERM_LIST_FILES:
            problems.append(f"{rel}: this is a private-term list; it names the things it hides, so it must stay outside the repository (see SECURITY.md)")
        size = p.stat().st_size
        if size > MAX_BYTES:
            problems.append(f"{rel}: {size / 1e6:.1f} MB is over the {MAX_BYTES // (1024 * 1024)} MB limit (database dump? bundle? build output?)")
        if terms and (ext in TEXT_EXT or rel in ALLOW_FILES) and size <= MAX_BYTES:
            text = p.read_text(encoding="utf-8", errors="replace")
            for t in terms:
                m = t.search(text)
                if m:
                    line = text.count("\n", 0, m.start()) + 1
                    problems.append(f"{rel}:{line}: matches a forbidden-term pattern (pattern text is not echoed on purpose)")
                    break
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--terms-file")
    a = ap.parse_args(argv)
    root = Path(a.root)
    files = list_files(root)
    terms = load_terms(a.terms_file)
    problems = scan(root, files, terms)
    print(f"checked {len(files)} files; term patterns loaded: {len(terms)}" + ("" if terms else "  (structure checks only: no FORBIDDEN_TERMS variable and no --terms-file)"))
    for x in problems:
        print("FAIL", x)
    if problems:
        print(f"{len(problems)} problem(s). If a file is genuinely approved, move it to {ALLOW_DIR} and record the approval in {APPROVALS}.")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
