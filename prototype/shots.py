#!/usr/bin/env python3
"""Capture the prototype's screens as PNG files for the README gallery.

    python3 shots.py [OUT_DIR]          default OUT_DIR: ../docs/images/prototype

Uses the same harness as the browser tests (h.py): a local copy of React from `vendor/node_modules` (run `npm ci` in
`vendor/` once) and a headless Chromium (set CHROMIUM_PATH if it is not found). Everything on screen is synthetic.
The fonts (Public Sans, Source Serif 4, JetBrains Mono) are files in project/fonts/, so the pictures show the real typefaces without any network.
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
    """Workspace screens have a sticky side bar that is as tall as the window, so for a full-page picture the window is first
    made as tall as the page; otherwise the bar would stop partway down the picture."""
    p = OUT / name
    pg.evaluate("window.scrollTo(0, 0)")
    if full:
        height = pg.evaluate("document.documentElement.scrollHeight")
        pg.set_viewport_size({"width": width, "height": max(900, height)})
        settle(pg, 250)
        height = pg.evaluate("document.documentElement.scrollHeight")
        pg.set_viewport_size({"width": width, "height": max(900, height)})
        settle(pg, 250)
    pg.screenshot(path=str(p), full_page=full)
    if full:
        pg.set_viewport_size({"width": width, "height": 900 if width > 500 else 844})
    shrink(p, width)
    print(f"{name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")


# ---- desktop, 1440 px wide
with session(1440, 900) as (pg, errs):
    shot(pg, "01_open.png", full=True)
    pg.get_by_role("button", name="Open the sample project").click(); settle(pg)
    shot(pg, "02_import_check_the_mapping.png", full=True)
    pg.get_by_role("button", name="Confirm mapping and import").click(); settle(pg, 600)
    shot(pg, "03_home.png", full=True)
    labels = [x.strip().split("\n")[0] for x in pg.locator(".nav-btn").all_inner_texts()]
    print("sidebar:", labels)
    nav(pg, "Overview")
    shot(pg, "04_overview.png", full=True)
    nav(pg, "Review queue")
    shot(pg, "05_review_queue.png", full=True)
    nav(pg, "Overview")
    pg.get_by_role("button", name="Start with the safest cluster").click(); settle(pg, 600)
    shot(pg, "06_cluster_review_low_risk.png", full=True)
    nav(pg, "Overview")
    pg.get_by_role("button", name="Open CL-050").click(); settle(pg, 600)
    shot(pg, "07_cluster_review_six_wordings.png", full=True)
    pg.get_by_role("button", name="Line up the words").click()
    pg.set_viewport_size({"width": 1440, "height": 1040}); settle(pg, 500)     # tall enough for all six rows
    shot(pg, "08_wordings_lined_up.png")
    pg.keyboard.press("Escape"); pg.set_viewport_size({"width": 1440, "height": 900}); settle(pg)
    for label, name in (("All requirements", "09_all_requirements.png"), ("Methods and metrics", "10_methods_and_metrics.png"),
                        ("Decisions and audit", "11_decisions_and_audit.png"), ("Sign-off policy", "12_sign_off_policy.png"),
                        ("Export to documents", "13_export_to_documents.png")):
        nav(pg, label)
        shot(pg, name, full=True)
    print("console problems:", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- phone, 390 px wide
h.PORT += 1          # the first session's server socket is still bound in this process
with session(390, 844) as (pg, errs):
    shot(pg, "14_phone_open.png", full=True, width=390)
    pg.get_by_role("button", name="Open the sample project").click(); settle(pg)
    pg.get_by_role("button", name="Confirm mapping and import").click(); settle(pg, 600)
    shot(pg, "15_phone_home.png", full=True, width=390)
    pg.locator(".nav-btn", has_text="Overview").first.click(); settle(pg)
    pg.get_by_role("button", name="Open CL-050").click(); settle(pg, 600)
    p = OUT / "16_phone_six_wordings.png"                  # the whole page is the queue first; this one picture is just the group card
    pg.locator('section[aria-labelledby="grp-h"]').screenshot(path=str(p))
    shrink(p, 390); print(f"{p.name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")
    print("console problems (phone):", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- record which version of the page these pictures show; tools/test_previews_fresh.py compares it with the page
page = Path(__file__).resolve().parent / "project" / "Main.dc.html"
(OUT / "manifest.json").write_text(json.dumps({"prototype_page": hashlib.sha256(page.read_bytes()).hexdigest(),
                                                "screens": sorted(p.name for p in OUT.glob("*.png"))}, indent=2) + "\n", encoding="utf-8")
