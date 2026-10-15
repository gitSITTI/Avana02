#!/usr/bin/env python3
"""Run gitleaks (secret scanning) at one pinned version, installing it with a checksum if needed.

    python tools/run_gitleaks.py install    download the pinned release into .cache/bin and verify its SHA-256
    python tools/run_gitleaks.py staged     scan what is staged for commit (the pre-commit hook). Never downloads.
    python tools/run_gitleaks.py history    scan every commit on every branch (CI, `make secrets`). Installs first if needed.
    python tools/run_gitleaks.py find       print the path of the gitleaks it would use, or exit 1

Which gitleaks: the file named by GITLEAKS_BIN, if set; else .cache/bin/gitleaks (this script's own pinned copy); else one on PATH.
The pinned release is checked against the SHA-256 values below, which come from the release's own gitleaks_<version>_checksums.txt.
To upgrade: change VERSION, replace the five hashes from that file, run the tests.
Behind a firewall: mirror the release archives and set GITLEAKS_BASE_URL to the folder that holds them. The checksum is still checked.

The rules are in .gitleaks.toml (gitleaks' own rules plus a short allowlist). It reads the repository only; nothing is sent anywhere.
"""
from __future__ import annotations

import hashlib
import io
import os
import platform
import stat
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

VERSION = "8.30.1"
SHA256 = {
    "linux_x64": "551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb",
    "linux_arm64": "e4a487ee7ccd7d3a7f7ec08657610aa3606637dab924210b3aee62570fb4b080",
    "darwin_x64": "dfe101a4db2255fc85120ac7f3d25e4342c3c20cf749f2c20a18081af1952709",
    "darwin_arm64": "b40ab0ae55c505963e365f271a8d3846efbc170aa17f2607f13df610a9aeb6a5",
    "windows_x64": "d29144deff3a68aa93ced33dddf84b7fdc26070add4aa0f4513094c8332afc4e",
}
BASE_URL = os.environ.get("GITLEAKS_BASE_URL", f"https://github.com/gitleaks/gitleaks/releases/download/v{VERSION}").rstrip("/")

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / ".gitleaks.toml"
BIN_DIR = REPO / ".cache" / "bin"


def platform_key() -> str:
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else machine
    system = {"linux": "linux", "darwin": "darwin", "win32": "windows"}.get(sys.platform, sys.platform)
    key = f"{system}_{arch}"
    if key not in SHA256:
        raise SystemExit(f"gitleaks: no pinned release for {key}. Install gitleaks yourself (https://github.com/gitleaks/gitleaks) and put it on PATH.")
    return key


def exe_name() -> str:
    return "gitleaks.exe" if sys.platform == "win32" else "gitleaks"


def find() -> str | None:
    pinned = os.environ.get("GITLEAKS_BIN", "")
    if pinned and Path(pinned).is_file():
        return pinned
    own = BIN_DIR / exe_name()
    if own.is_file():
        return str(own)
    from shutil import which
    return which("gitleaks")


def install() -> str:
    key = platform_key()
    ext = "zip" if key.startswith("windows") else "tar.gz"
    name = f"gitleaks_{VERSION}_{key}.{ext}"
    print(f"gitleaks: downloading {name} from {BASE_URL}", file=sys.stderr)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/{name}", timeout=120) as response:
            blob = response.read()
    except OSError as error:
        raise SystemExit(f"gitleaks: could not download {name}: {error}. Install gitleaks yourself, or set GITLEAKS_BASE_URL to a mirror.")
    digest = hashlib.sha256(blob).hexdigest()
    if digest != SHA256[key]:
        raise SystemExit(f"gitleaks: the download does not match the pinned checksum for {name} (got {digest[:12]}..., want {SHA256[key][:12]}...). Nothing was installed.")
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    target = BIN_DIR / exe_name()
    if ext == "zip":
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            data = archive.read(exe_name())
    else:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as archive:
            member = archive.extractfile("gitleaks")
            if member is None:
                raise SystemExit("gitleaks: the archive has no gitleaks binary")
            data = member.read()
    target.write_bytes(data)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"gitleaks: installed {target} (checksum verified)", file=sys.stderr)
    return str(target)


def run(binary: str, args: list[str]) -> int:
    return subprocess.run([binary, *args, "--redact", "--verbose", "--no-banner", "--config", str(CONFIG)]).returncode


def main(argv: list[str]) -> int:
    mode = argv[0] if argv else ""
    if mode == "install":
        install()
        return 0
    if mode == "find":
        found = find()
        print(found or "gitleaks: not installed", file=sys.stderr if not found else sys.stdout)
        return 0 if found else 1
    if mode == "staged":
        binary = find()
        if not binary:
            print("gitleaks is not installed, so this commit was blocked.", file=sys.stderr)
            print("Install the pinned copy with:  python tools/run_gitleaks.py install", file=sys.stderr)
            return 1
        return run(binary, ["git", "--pre-commit", "--staged"])
    if mode == "history":
        return run(find() or install(), ["git"])
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
