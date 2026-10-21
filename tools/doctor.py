#!/usr/bin/env python3
"""Check a checkout without printing environment values or contacting a service."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def inspect(profile="core", *, version=None, installed=None, which=None, env=None, root=ROOT):
    version = version or sys.version_info[:2]
    which = which or shutil.which
    env = os.environ if env is None else env
    def available(name):
        if installed is not None:
            return name in installed
        try:
            importlib.metadata.version(name)
            return True
        except importlib.metadata.PackageNotFoundError:
            return False
    checks = []
    def add(name, ok, required, remedy):
        checks.append(dict(name=name, ok=bool(ok), required=required, remedy="" if ok else remedy))
    add("Python 3.11+", tuple(version) >= (3, 11), True, "Use Python 3.11 or newer.")
    metadata = tomllib.loads((root / "reqin/pyproject.toml").read_text())
    for spec in metadata["project"]["dependencies"] + metadata["project"]["optional-dependencies"]["test"]:
        import re
        name = re.split(r"[<>=!~\[]", spec)[0]
        add("package: " + name, available(name), True, 'Run pip install -e "reqin[test]".')
    add("Node.js", which("node"), True, "Install Node.js to run the prototype checks.")
    add("Playwright", available("playwright"), profile == "browser", "Run pip install -r prototype/requirements-test.txt, then python -m playwright install chromium firefox.")
    add("Container engine", which("podman") or which("docker"), False, "Install Podman or Docker to verify the container image.")
    configured = bool(env.get("DENYLIST_TERMS", "").strip() or env.get("DENYLIST_FILE") and Path(env["DENYLIST_FILE"]).is_file() or (root / ".denylist").is_file())
    add("Private-term list configured locally", configured, profile == "release", "Set DENYLIST_TERMS or DENYLIST_FILE securely. GitHub CI separately needs the DENYLIST repository secret.")
    add("Git", which("git"), profile == "release", "Install Git for guards and history scanning.")
    if profile == "release" and which("git"):
        r = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=root, capture_output=True, text=True)
        add("Complete Git history", r.returncode == 0 and r.stdout.strip() == "false", True, "Use a full checkout before scanning history.")
    return {"profile": profile, "ready": all(c["ok"] for c in checks if c["required"]), "checks": checks,
            "not_checked": ["No external credentials, CI secrets, services, browser launch, or container daemon were tested."]}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", choices=("core", "browser", "release"), default="core")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    result = inspect(a.profile)
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        for c in result["checks"]:
            print(("OK" if c["ok"] else "MISSING" if c["required"] else "OPTIONAL") + ": " + c["name"])
            if c["remedy"]:
                print("  " + c["remedy"])
        print("Ready for " + a.profile + " checks: " + str(result["ready"]))
        print(result["not_checked"][0])
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
