#!/usr/bin/env python3
"""Generate the newcomer capability table from its single JSON source."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def render():
    data = json.loads((ROOT / "docs/capabilities.json").read_text())
    assert data["format"] == "reqin-capabilities/1"
    rows = ["# Capabilities", "", "Generated from [capabilities.json](capabilities.json) by `python3 tools/capabilities.py`; do not edit this table by hand.", "", "Implemented means code exists with the referenced checks. It does not certify a deployment or a real requirements set.", "", "| Capability | State | Code | Checks | Limit |", "|---|---|---|---|---|"]
    for c in data["capabilities"]:
        assert c["state"] in ("implemented", "partial", "planned")
        for key in ("code", "evidence"):
            assert not c[key] or (ROOT / c[key]).exists(), c[key]
        link = lambda p: "[" + p + "](../" + p + ")" if p else "None"
        rows.append("| " + " | ".join([c["name"], c["state"], link(c["code"]), link(c["evidence"]), c["limit"]]) + " |")
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    path = ROOT / "docs/CAPABILITIES.md"
    text = render()
    if a.check:
        if not path.exists() or path.read_text() != text:
            raise SystemExit("Capabilities table is stale: run python3 tools/capabilities.py")
        print("Capabilities table matches its source.")
    else:
        path.write_text(text)
