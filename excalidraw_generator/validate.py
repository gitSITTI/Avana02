#!/usr/bin/env python3
"""Structural checks for .excalidraw files:  python validate.py board.excalidraw [...]

Catches the mistakes a generator makes silently: duplicate ids, bound text / arrows pointing at ids that do not exist,
children listed before their frame (Excalidraw then draws them hidden), and children that overflow their frame.
Exit code 1 if anything is structurally wrong (overflow is reported but does not fail the run)."""
from __future__ import annotations

import json
import sys


def check(path: str, verbose: bool = True) -> dict:
    d = json.load(open(path))
    els = d["elements"]
    ids = [e["id"] for e in els]
    idx = {e["id"]: i for i, e in enumerate(els)}
    byid = {e["id"]: e for e in els}
    dup = len(ids) - len(set(ids))
    dang = 0
    for e in els:
        if e.get("containerId") and e["containerId"] not in byid:
            dang += 1
        for b in e.get("boundElements") or []:
            if b["id"] not in byid:
                dang += 1
        for k in ("startBinding", "endBinding"):
            if e.get(k) and e[k]["elementId"] not in byid:
                dang += 1
        if e.get("frameId") and e["frameId"] not in byid:
            dang += 1
    frames = {e["id"]: e for e in els if e["type"] == "frame"}
    order = outside = nof = 0
    for e in els:
        fid = e.get("frameId")
        if not fid:
            nof += e["type"] != "frame"
            continue
        fr = frames[fid]
        order += idx[fid] < idx[e["id"]]
        x0, y0, x1, y1 = fr["x"], fr["y"], fr["x"] + fr["width"], fr["y"] + fr["height"]
        ex0, ey0, ex1, ey1 = e["x"], e["y"], e["x"] + e.get("width", 0), e["y"] + e.get("height", 0)
        if e["type"] in ("arrow", "line"):
            xs = [ex0 + p[0] for p in e["points"]]
            ys = [ey0 + p[1] for p in e["points"]]
            ex0, ex1, ey0, ey1 = min(xs), max(xs), min(ys), max(ys)
        if ex0 < x0 - 2 or ey0 < y0 - 2 or ex1 > x1 + 2 or ey1 > y1 + 2:
            outside += 1
            if verbose and outside <= 3:
                print("   outside:", e["type"], (e.get("text", "")[:40] if e["type"] == "text" else ""), round(ex0), round(ey0), round(ex1), round(ey1), "frame", fr.get("name", "")[:30])
    empty = sum(1 for e in els if e["type"] == "text" and not e.get("text"))
    return {"ok": not (dup or dang or order), "elements": len(els), "frames": len(frames), "dup": dup, "dangling": dang,
            "order": order, "outside": outside, "not_in_frame": nof, "empty_text": empty}


if __name__ == "__main__":
    bad = 0
    for f in sys.argv[1:]:
        r = check(f)
        print(f"{f}: {r['elements']} elements, {r['frames']} frames | dup ids {r['dup']} | dangling {r['dangling']} | frame-order {r['order']} | "
              f"outside frame {r['outside']} | not in frame {r['not_in_frame']} | empty text {r['empty_text']}")
        bad += not r["ok"]
    sys.exit(1 if bad else 0)
