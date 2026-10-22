#!/usr/bin/env python3
"""Draw the frames of our screens: one full-screen picture per screen, and where each frame sits in it.

    python3 scripts/make_frames.py              draw every screen from the running prototype and write docs/images/frames/*.png and docs/images/frames/frames.json
    python3 scripts/make_frames.py --check      no browser: does frames_spec.json agree with the screens and the data map, and are the pictures of the current page?
    python3 scripts/make_frames.py --probe      no pictures: print, per screen, what every frame in frames_spec.json found (its box and the start of its text)

A frame is a box of a screen, found by the path in frames_spec.json (from the content area, go down while there is exactly one visible child, then take the
i-th visible child for each number in the path). It is a section of the page, not a pixel rectangle chosen by hand, so it follows the page when the page changes.
`starts` is what its text must begin with: if the prototype is changed so that a path lands on something else, drawing stops and says which frame and what it
found, instead of cutting the wrong box.

The pictures are the prototype in our own colours, with made-up data. They show what is ON a screen, not what a person's data would look like there:
every number, name and date in them is sample content. Run this again after the prototype page changes, look at the pictures, then commit them with the change
(tools/test_previews_fresh.py compares the page's hash with the one written in frames.json).

`reach(pg, screen_id)` and `fresh(pg)` are used by the other scripts that need the running prototype in a given screen (the themed frames, scripts/frames_theme.py).
Drawing needs Playwright, Pillow and a Chromium (see prototype/h.py); the checks need only the standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT, REPO, read_json, write_json  # noqa: E402

SPEC = KIT / "frames_spec.json"
OUT = REPO / "docs" / "images" / "frames"        # pictures live in docs/images, the one place the repository keeps .png files
INDEX = OUT / "frames.json"
PROTOTYPE = REPO / "prototype"
PAGE = PROTOTYPE / "project" / "Main.dc.html"
WIDTH = 1440
SCALE_NOTE = "pixels of the picture; the picture is %d px wide, the width the prototype was drawn at" % WIDTH


def page_hash() -> str:
    return hashlib.sha256(PAGE.read_bytes()).hexdigest()


def load_spec() -> dict:
    return read_json(SPEC)


# ------------------------------------------------------------------------------------------------ the checks that need no browser
def spec_problems(spec: dict | None = None) -> list:
    """What is wrong with frames_spec.json against the navigation map and the data map. An empty list means it agrees with both."""
    import catalog as CAT

    spec = spec or load_spec()
    nav = read_json(REPO / "design" / "navigation.json")
    screens = CAT.screens(nav, (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8"))
    errs = []
    known = {s["screen"]: s for s in screens}
    for sid in known:
        if sid not in spec["screens"]:
            errs.append("screen %s has no frames in frames_spec.json" % sid)
    for sid, frames in spec["screens"].items():
        if sid not in known:
            errs.append("frames_spec.json has frames for %r, which is not a screen in design/navigation.json" % sid)
            continue
        if not frames:
            errs.append("screen %s has an empty frame list" % sid)
        nrows = len(known[sid]["rows"])
        seen_ids, seen_rows = set(), {}
        for f in frames:
            w = "%s/%s" % (sid, f.get("id"))
            for k in ("id", "label", "path", "starts", "rows"):
                if k not in f:
                    errs.append("%s: %s is missing" % (w, k))
            if "id" not in f:
                continue
            if f["id"] in seen_ids:
                errs.append("%s: the frame id is used twice on this screen" % w)
            seen_ids.add(f["id"])
            if not f.get("path") or not all(isinstance(i, int) and i >= 0 for i in f["path"]):
                errs.append("%s: path must be a list of indexes" % w)
            if not f.get("starts", "").strip():
                errs.append("%s: starts is empty, so a wrong box could not be told from the right one" % w)
            for r in f.get("rows", []):
                m = re.fullmatch(r"r(\d+)", r)
                if not m or not 1 <= int(m.group(1)) <= nrows:
                    errs.append("%s: row %r is not one of the %d pieces the data map lists for this screen" % (w, r, nrows))
                else:
                    seen_rows.setdefault(r, []).append(f["id"])      # a piece may be drawn across several frames
    return errs


def index_problems() -> list:
    """What is wrong with frames/frames.json: missing, drawn from another page, or not matching the spec."""
    if not INDEX.is_file():
        return ["docs/images/frames/frames.json does not exist: run design/adopt_design/scripts/make_frames.py"]
    idx = read_json(INDEX)
    errs = []
    if idx.get("prototype_page") != page_hash():
        errs.append("the frame pictures were drawn from another version of prototype/project/Main.dc.html: run scripts/make_frames.py")
    spec = load_spec()
    for sid, frames in spec["screens"].items():
        got = idx.get("screens", {}).get(sid)
        if not got:
            errs.append("screen %s is not in frames.json" % sid)
            continue
        if [f["id"] for f in got["frames"]] != [f["id"] for f in frames]:
            errs.append("screen %s: the frames in frames.json are not the frames in frames_spec.json" % sid)
        if not (OUT / got["image"]).is_file():
            errs.append("screen %s: picture %s is missing" % (sid, got["image"]))
        for f in got["frames"]:
            b = f["box"]
            if b["x"] < 0 or b["y"] < 0 or b["w"] <= 0 or b["h"] <= 0 or b["x"] + b["w"] > got["width"] + 1 or b["y"] + b["h"] > got["height"] + 1:
                errs.append("screen %s, frame %s: its box is outside the picture" % (sid, f["id"]))
    return errs


# ------------------------------------------------------------------------------------------------ the running prototype
def settle(pg, ms: int = 400) -> None:
    pg.wait_for_timeout(ms)


def fresh(pg) -> None:
    """The prototype as a person sees it the first time: what it keeps in the browser is cleared and the page is loaded again."""
    pg.evaluate("localStorage.clear(); sessionStorage.clear()")
    pg.reload()
    pg.wait_for_timeout(1800)
    pg.set_viewport_size({"width": WIDTH, "height": 900})


def _click(pg, name: str) -> None:
    pg.get_by_role("button", name=name).first.click()
    settle(pg, 600)


def reach(pg, screen_id: str) -> None:
    """From a freshly loaded prototype (see fresh), go to one of our screens by the same clicks a person makes.

    The first two screens come before the workspace, so `open` is where the page starts and `import` is one click away. Every other screen is reached through
    the sample project and its side menu, and the lead's screens are reached as the lead (the sample's lead, Morgan)."""
    nav = read_json(REPO / "design" / "navigation.json")
    by_id = {s["id"]: s for s in nav["screens"]}
    if screen_id not in by_id:
        raise KeyError("no screen %r in design/navigation.json" % screen_id)
    if screen_id == "open":
        return
    _click(pg, "Open the sample project")
    if screen_id == "import":
        return
    _click(pg, "Confirm mapping and import")
    if screen_id == "ai":
        pg.get_by_role("button", name=re.compile(r"^Morgan\b")).first.click()
        settle(pg)
    pg.locator(".nav-btn", has_text=by_id[screen_id]["title"]).first.click()
    settle(pg)


def tall(pg, width: int = WIDTH) -> int:
    """Make the window as tall as the page, so the sticky side bar covers the whole picture and nothing is cut. Returns the page height."""
    pg.evaluate("window.scrollTo(0, 0)")
    height = 900
    for _ in range(2):
        height = max(900, pg.evaluate("document.documentElement.scrollHeight"))
        pg.set_viewport_size({"width": width, "height": height})
        settle(pg, 250)
    return height


FINDER_JS = r"""(paths) => {
  const vis = c => { const r = c.getBoundingClientRect(); return r.width > 30 && r.height > 12 && getComputedStyle(c).display !== 'none'; };
  const kids = el => [...el.children].filter(vis);
  let wrap = document.querySelector('#main-content') || document.querySelector('main');
  let guard = 0;
  while (wrap && kids(wrap).length === 1 && guard++ < 6) wrap = kids(wrap)[0];
  return paths.map(path => {
    let e = wrap;
    for (const i of path) { e = e ? kids(e)[i] : null; }
    if (!e) return null;
    const r = e.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height, text: e.innerText.trim().replace(/\s+/g, ' ').slice(0, 200) };
  });
}"""


def find_frames(pg, frames: list) -> list:
    """The box and the start of the text of each frame in the list, on the screen the page is showing now."""
    return pg.evaluate(FINDER_JS, [f["path"] for f in frames])


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def drift(sid: str, frames: list, found: list) -> list:
    """Frames whose path now lands on nothing, or on text that does not start the way the spec says."""
    out = []
    for f, got in zip(frames, found):
        if got is None:
            out.append("%s/%s: path %s lands on nothing" % (sid, f["id"], f["path"]))
        elif not norm(got["text"]).startswith(norm(f["starts"])):
            out.append("%s/%s: path %s lands on text that starts %r, not %r" % (sid, f["id"], f["path"], norm(got["text"])[:60], f["starts"]))
    return out


# ------------------------------------------------------------------------------------------------ drawing
def _shrink(path: Path) -> None:
    """These are flat UI screens: an adaptive 256-colour PNG is a fraction of the size and looks the same."""
    from PIL import Image

    im = Image.open(path).convert("RGB")
    im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


def draw(probe: bool = False) -> int:
    sys.path.insert(0, str(PROTOTYPE))
    from h import session  # noqa: E402

    spec = load_spec()
    problems = spec_problems(spec)
    if problems:
        print("frames_spec.json does not agree with the screens and the data map:\n  " + "\n  ".join(problems))
        return 1
    if not probe:
        OUT.mkdir(parents=True, exist_ok=True)
    index = {"format": "reqin-frames/1", "prototype_page": page_hash(), "viewport_width": WIDTH, "box_units": SCALE_NOTE, "screens": {}}
    bad = []
    with session(WIDTH, 900) as (pg, errs):
        first = True
        for sid, frames in spec["screens"].items():
            if not first:
                fresh(pg)
            first = False
            reach(pg, sid)
            height = tall(pg)
            found = find_frames(pg, frames)
            bad += drift(sid, frames, found)
            if probe:
                print("\n== %s (page height %d)" % (sid, height))
                for f, g in zip(frames, found):
                    print("  %-22s %s" % (f["id"], "NONE" if g is None else "x%d y%d %dx%d :: %s" % (g["x"], g["y"], g["w"], g["h"], g["text"][:70])))
                continue
            png = OUT / (sid + ".png")
            pg.screenshot(path=str(png), full_page=True)
            _shrink(png)
            index["screens"][sid] = {"image": png.name, "width": WIDTH, "height": height, "frames": [
                {"id": f["id"], "label": f["label"], "rows": f["rows"], "box": None if g is None else {k: round(g[k]) for k in ("x", "y", "w", "h")}}
                for f, g in zip(frames, found)]}
        real = [e for e in errs if "ERR_FAILED" not in e]
    if bad:
        print("the prototype no longer matches frames_spec.json; nothing was written:\n  " + "\n  ".join(bad))
        return 1
    if real:
        print("the page reported problems while it was drawn (nothing was written):\n  " + "\n  ".join(real[:10]))
        return 1
    if not probe:
        write_json(INDEX, index)
        print("wrote %d pictures and %s" % (len(index["screens"]), INDEX.relative_to(REPO)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="no browser: the spec against the screens and the data map, and the pictures against the page")
    ap.add_argument("--probe", action="store_true", help="no pictures: print what every frame in the spec finds")
    a = ap.parse_args(argv)
    if a.check:
        errs = spec_problems() + index_problems()
        print("\n".join(errs) if errs else "frames_spec.json and the frame pictures agree with the screens, the data map and the page")
        return 1 if errs else 0
    return draw(probe=a.probe)


if __name__ == "__main__":
    sys.exit(main())
