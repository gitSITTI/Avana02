#!/usr/bin/env python3
"""Turn on this repository's git hooks for your clone, and install the pinned gitleaks they need.

    python tools/setup_hooks.py          (or: make hooks)

It sets `core.hooksPath` to .githooks for THIS clone only, downloads gitleaks with a checksum check unless one is already installed,
and says whether a private-term list was found. It does not create the list: you keep that yourself, outside the repository
(see SECURITY.md, "Keeping private names out").
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import denylist_check  # noqa: E402
import run_gitleaks  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    subprocess.run(["git", "-C", str(REPO), "config", "core.hooksPath", ".githooks"], check=True)
    for hook in (REPO / ".githooks").iterdir():
        hook.chmod(hook.stat().st_mode | 0o111)
    print("Hooks on: commits in this clone are checked by .githooks/pre-commit and .githooks/commit-msg.")
    if run_gitleaks.find():
        print(f"gitleaks: found {run_gitleaks.find()}")
    else:
        run_gitleaks.install()
    os.chdir(REPO)
    terms = denylist_check.load_terms()
    if terms:
        print(f"Private-term list: {terms.count} term(s) from {terms.source}.")
    else:
        print("Private-term list: none found. Secrets are still checked. To also block private names, create a file named .denylist")
        print("in the repository root (it is git-ignored), one term per line, or point DENYLIST_FILE at your master copy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
