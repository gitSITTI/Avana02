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
import re
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


def part(pg, locator, name, width=1440):
    """A picture of one section of a page. The window is made as tall as the page and the page is at the top, so the sticky top bar
    stays where it belongs and does not lie across the section the way it does in an element screenshot taken after scrolling."""
    p = OUT / name
    pg.evaluate("window.scrollTo(0, 0)")
    pg.set_viewport_size({"width": width, "height": max(900, pg.evaluate("document.documentElement.scrollHeight"))}); settle(pg, 250)
    box = locator.bounding_box()
    pg.screenshot(path=str(p), full_page=True, clip={"x": box["x"], "y": box["y"], "width": box["width"], "height": box["height"]})
    pg.set_viewport_size({"width": width, "height": 900})
    shrink(p, width); print(f"{name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")


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
    nav(pg, "The V")
    shot(pg, "20_the_v.png", full=True)
    pg.fill("#top-search", "CL-038"); settle(pg)                       # a cluster that mixes two levels: the strip says to link, not merge
    pg.get_by_role("button", name="CL-038").first.click(); settle(pg, 600)
    p = OUT / "21_cluster_in_the_v.png"
    pg.locator('[role="group"][aria-label="Where this cluster sits in the V"]').screenshot(path=str(p))
    shrink(p, 1440); print(f"{p.name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")
    nav(pg, "Results and grade")
    shot(pg, "17_results_and_grade.png", full=True)
    pg.fill("#top-search", "CL-001"); settle(pg)                       # a cluster sent to a teammate, waiting for the answer
    pg.get_by_role("button", name="CL-001").first.click(); settle(pg)
    pg.locator("#snd-toggle").click(); settle(pg, 200)
    pg.fill("#snd-note", "Please check the unit on M2."); settle(pg, 200)
    pg.locator("#snd-send").click(); settle(pg, 500)
    shot(pg, "18_hand_off_waiting.png", full=True)
    # the gold set: label pairs without being told what the app thought
    nav(pg, "Label pairs")
    shot(pg, "23_label_pairs.png", full=True)
    # one requirement at a time: a requirement with no similar one, kept with a reason and waiting for a colleague's sign-off
    nav(pg, "All requirements")
    pg.get_by_role("button", name=re.compile(r"^Alone\b")).first.click(); settle(pg)
    pg.locator('button[aria-pressed]:has(span:text-matches("^REQ-"))').nth(2).click(); settle(pg)
    one = pg.locator('aside[aria-label="One requirement"]')
    one.get_by_role("button", name="Keep as written").first.click(); settle(pg, 150)
    pg.select_option("#xp-reason", "S-OK"); settle(pg, 150)
    one.get_by_role("button", name="Record this decision").first.click(); settle(pg, 400)
    shot(pg, "24_one_requirement.png", full=True)
    # what a decision moves outside the requirement list
    nav(pg, "Export to documents")
    part(pg, pg.locator('section[aria-labelledby="tr-h"]'), "25_trace_map.png")
    # the work is kept in this browser
    nav(pg, "Home")
    part(pg, pg.locator('section[aria-labelledby="home-keep"]'), "26_your_work.png")
    # a group the AI data sheet holds back from the AI, in review
    pg.fill("#top-search", "CL-025"); settle(pg)
    pg.get_by_role("button", name="CL-025").first.click(); settle(pg, 600)
    shot(pg, "28_held_group_review.png", full=True)
    # AI use, as the lead: the switch, the data sheet and what the gate does with each group
    pg.get_by_role("button", name=re.compile(r"^Morgan\b")).first.click(); settle(pg)
    nav(pg, "AI use")
    shot(pg, "27_ai_use.png", full=True)
    print("console problems:", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- the first Tab stop: a link that skips the menu (a picture of the top of the page with the link showing)
h.PORT += 1
with session(1440, 900) as (pg, errs):
    pg.get_by_role("button", name="Open the sample project").click(); settle(pg)
    pg.get_by_role("button", name="Confirm mapping and import").click(); settle(pg, 600)
    pg.evaluate("document.activeElement && document.activeElement.blur()"); pg.keyboard.press("Tab"); settle(pg, 300)
    p = OUT / "29_skip_link.png"
    pg.screenshot(path=str(p), clip={"x": 0, "y": 0, "width": 1440, "height": 220})
    shrink(p, 1440); print(f"{p.name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")

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
    pg.locator(".nav-btn", has_text="Results and grade").first.click(); settle(pg, 500)
    p = OUT / "19_phone_results.png"                       # the grade card: the letter, the bands and the five parts
    pg.locator('section[aria-labelledby="rs-grade"]').screenshot(path=str(p))
    shrink(p, 390); print(f"{p.name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")
    pg.locator(".nav-btn", has_text="The V").first.click(); settle(pg, 500)
    pg.set_viewport_size({"width": 390, "height": 1500}); settle(pg, 300)     # the page is long; the picture is the top of it: the V, the three numbers and the first level
    pg.evaluate("document.querySelector('h1').scrollIntoView()"); settle(pg, 200)
    p = OUT / "22_phone_the_v.png"
    pg.screenshot(path=str(p)); shrink(p, 390); print(f"{p.name:34} {Image.open(p).size}  {os.path.getsize(p) // 1024} KB")
    pg.set_viewport_size({"width": 390, "height": 844})
    print("console problems (phone):", [e for e in errs if "ERR_FAILED" not in e] or "none")

# ---- record which version of the page these pictures show; tools/test_previews_fresh.py compares it with the page
page = Path(__file__).resolve().parent / "project" / "Main.dc.html"
(OUT / "manifest.json").write_text(json.dumps({"prototype_page": hashlib.sha256(page.read_bytes()).hexdigest(),
                                                "screens": sorted(p.name for p in OUT.glob("*.png"))}, indent=2) + "\n", encoding="utf-8")
