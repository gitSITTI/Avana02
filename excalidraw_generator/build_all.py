#!/usr/bin/env python3
"""Rebuild every board:   python build_all.py [--out out] [--only 02,05] [--check]

Deterministic: the same code always writes the same bytes (element ids come from a seeded RNG).
--check rebuilds into a temp folder and compares with --out, so an agent can prove it did not change boards it should not touch."""
from __future__ import annotations

import argparse
import filecmp
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import boards_05_09, build_wf, flows, kit, sb  # noqa: E402
from validate import check  # noqa: E402

BUILDERS = {
    "01_storyboard": sb.build,
    "02_wireframes": build_wf.build,
    "03_system_flows": flows.build,
    "04_ui_kit_and_IA": kit.build,
    **{name: (lambda path, n=name: boards_05_09.build_board(n, path)) for name in boards_05_09.BOARDS},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--only", help="comma list of board numbers, e.g. 02,05")
    ap.add_argument("--check", action="store_true", help="compare a fresh build with --out instead of overwriting it")
    a = ap.parse_args()
    want = set(a.only.split(",")) if a.only else None
    out = Path(a.out)
    target = Path(tempfile.mkdtemp()) if a.check else out
    target.mkdir(parents=True, exist_ok=True)
    bad = 0
    for name, fn in BUILDERS.items():
        if want and name[:2] not in want:
            continue
        p = target / f"{name}.excalidraw"
        fn(str(p))
        r = check(str(p))
        flag = "ok" if r["ok"] else "PROBLEMS"
        line = f"{name:28s} {r['elements']:6d} elements  {r['frames']:3d} frames  dup={r['dup']} dangling={r['dangling']} order={r['order']} outside={r['outside']}  {flag}"
        if a.check:
            same = (out / p.name).exists() and filecmp.cmp(p, out / p.name, shallow=False)
            line += "  identical" if same else "  DIFFERS from " + str(out / p.name)
            bad += 0 if same else 1
        print(line)
        bad += 0 if r["ok"] else 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
