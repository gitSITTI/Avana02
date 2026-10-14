#!/usr/bin/env python3
"""Capture the prototype's screens as PNG files for the README gallery.

    python3 shots.py [OUT_DIR]          default OUT_DIR: ../docs/images/prototype

Uses the same harness as the browser tests (h.py): a local copy of React from `vendor/node_modules` (run `npm ci` in
`vendor/` once) and a headless Chromium (set CHROMIUM_PATH if it is not found). Everything on screen is synthetic.
The harness blocks the Google Fonts request, so the pictures show the browser's fallback fonts, not IBM Plex.
Run it again after changing a screen, look at the pictures, then commit them with the change.

The list below is the whole gallery: add a row to add a screenshot. Each step is a plain button label from the page.
It also writes manifest.json (a hash of project/Main.dc.html) so a test can tell when the pictures are stale.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from PIL import Image

import h
from h import session

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "docs" / "images" / "prototype"
OUT.mkdir(parents=True, exist_ok=True)


def settle(pg, ms=400):
    pg.wait_for_timeout(ms)


def shrink(path: Path, max_w: int) -> None:
    """Keep files small: cap the width, then store as an adaptive 256-colour PNG (these are flat UI screens)."""
    im = Image.open(path).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def nav(pg, label: str):
    pg.locator(".nav-btn", has_text=label).first.click()
    settle(pg)


def shot(pg, name: str, full=False, width=1440):
    p = OUT / name
    pg.screenshot(path=str(p), full_page=full)
    shrink(p, width)
    print(f"{name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")


# ---- desktop, 1440 px wide
with session(1440, 900) as (pg, errs):
    shot(pg, "01_open.png", full=True)
    pg.get_by_role("button", name="Open the sample project").click(); settle(pg)
    shot(pg, "02_import_check_the_mapping.png", full=True)
    pg.get_by_role("button", name="Confirm mapping and import").click(); settle(pg, 600)
    shot(pg, "03_overview.png")
    labels = [x.strip().split("\n")[0] for x in pg.locator(".nav-btn").all_inner_texts()]
    print("sidebar:", labels)
    nav(pg, "Review queue")
    shot(pg, "04_review_queue.png")
    nav(pg, "Overview")
    pg.get_by_role("button", name="Start with the safest cluster").click(); settle(pg, 600)
    shot(pg, "05_cluster_review_low_risk.png", full=True)
    nav(pg, "Overview")
    pg.get_by_role("button", name="Open CL-050").click(); settle(pg, 600)
    shot(pg, "06_cluster_review_conflict.png", full=True)
    for label, name in (("All requirements", "07_all_requirements.png"), ("Methods and metrics", "08_methods_and_metrics.png"),
                        ("Decisions and audit", "09_decisions_and_audit.png"), ("Sign-off policy", "10_sign_off_policy.png"),
                        ("Export to documents", "11_export_to_documents.png")):
        nav(pg, label)
        shot(pg, name)
    print("console problems:", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- phone, 390 px wide
h.PORT += 1          # the first session's server socket is still bound in this process
with session(390, 844) as (pg, errs):
    shot(pg, "12_phone_open.png", full=True, width=390)
    pg.get_by_role("button", name="Open the sample project").click(); settle(pg)
    pg.get_by_role("button", name="Confirm mapping and import").click(); settle(pg, 600)
    shot(pg, "13_phone_overview.png", full=True, width=390)
    print("console problems (phone):", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- record which version of the page these pictures show; tools/test_previews_fresh.py compares it with the page
page = Path(__file__).resolve().parent / "project" / "Main.dc.html"
(OUT / "manifest.json").write_text(json.dumps({"prototype_page": hashlib.sha256(page.read_bytes()).hexdigest(),
                                                "screens": sorted(p.name for p in OUT.glob("*.png"))}, indent=2) + "\n", encoding="utf-8")
