#!/usr/bin/env python3
"""Keep an approved screen from drifting: take a screenshot, have a person approve it, then fail any later change to it until a person approves the new look.

    python3 tools/gui_checks/golden.py shot --app my_app/ --datasets DIR --dataset F02_everything --width 1440 --out shots/home-1440.png
    python3 tools/gui_checks/golden.py approve home-1440 shots/home-1440.png        a person has looked at the picture and said yes
    python3 tools/gui_checks/golden.py compare home-1440 shots/home-1440.png [--tolerance 0.01] [--diff diff.png]
    python3 tools/gui_checks/golden.py compare-all --shots shots/ [--goldens design/golden] [--tolerance 0.01]

Why it exists: the probe (probe.py) shows that a screen is bound to its data and uses the design tokens. It cannot see that a screen has quietly grown a panel, lost a column or
moved its layout while an agent was making it show some data. A picture a person approved, compared with a picture of the change, can. A drawing or a wireframe cannot play
this part: it is not made of the same pixels as a built screen. So the first built version of a screen is shown to the owner, and the owner's approval is the reference.

What it does:
  shot         opens the app in Chromium (through serve.py), waits for body[data-state] to settle and for the fonts, stops animations, and saves one picture of the window at a given
               width. Same app, same dataset, same width, same machine gives the same picture; it checks that by taking two (tools/test_golden_browser.py).
  approve      copies a picture into the goldens folder under a screen name. It is the one step a person takes. An agent never approves its own work.
  compare      reports the share of pixels that changed. A pixel counts as changed when any colour channel moves by more than 24 of 255 (anti-aliasing and compression noise stay
               under that). Fails above --tolerance (default 1 %), when the sizes differ, or when the picture or the golden is missing. --diff writes a picture with the changes in red.
  compare-all  compares every golden with the picture of the same file name in --shots. A golden with no picture FAILS: a screen that was not photographed was not checked.
               A picture with no golden is listed as not yet approved. With no goldens at all it says that nothing was compared and exits 0.

Exit status: 0 passed, 1 drifted (or a picture is missing in compare-all), 2 something to compare was missing or not an image.

What it does not do: judge whether a screen is good, clear or accessible; it only says whether it still looks like what a person approved. Goldens depend on the machine's fonts
and renderer, so they are made and checked in the same place (a container, or one machine), and they are not committed here: a picture made on one machine will differ on another.
It compares the window, not the whole page, and only the states and widths you photographed. Chromium only. Needs Pillow; `shot` also needs Playwright and Chromium
(design/ui_from_image/requirements.txt).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

NOISE = 24                      # a pixel whose channels all moved by this much or less counts as unchanged
DEFAULT_GOLDENS = REPO / "design" / "golden"
DEFAULT_TOLERANCE = 0.01


def _pil():
    try:
        from PIL import Image, ImageChops
    except ImportError:
        raise SystemExit("golden.py needs Pillow: pip install -r design/ui_from_image/requirements.txt")
    return Image, ImageChops


def changed_ratio(a, b):
    """(share of pixels that changed, a mask of them). Both images must be the same size."""
    _, chops = _pil()
    diff = chops.difference(a.convert("RGB"), b.convert("RGB"))
    r, g, bl = diff.split()
    peak = chops.lighter(chops.lighter(r, g), bl)
    mask = peak.point(lambda v: 255 if v > NOISE else 0)
    return mask.histogram()[255] / float(mask.size[0] * mask.size[1]), mask


def write_diff(base, mask, out: Path) -> None:
    Image, _ = _pil()
    dim = Image.blend(base.convert("RGB"), Image.new("RGB", base.size, "white"), 0.7)
    dim.paste(Image.new("RGB", base.size, (226, 75, 74)), mask=mask)
    out.parent.mkdir(parents=True, exist_ok=True)
    dim.save(out)


def _open(path: Path):
    Image, _ = _pil()
    try:
        im = Image.open(path)
        im.load()
        return im
    except Exception as e:
        print("%s is not a readable image: %s" % (path, e), file=sys.stderr)
        return None


def compare(golden: Path, shot: Path, tolerance: float = DEFAULT_TOLERANCE, diff_out: Path | None = None) -> int:
    name = golden.stem
    if not golden.exists():
        print("NO GOLDEN %s: nobody has approved a first version. Show %s to the owner, then: golden.py approve %s %s" % (name, shot, name, shot), file=sys.stderr)
        return 2
    if not shot.exists():
        print("NO PICTURE for %s: %s does not exist, so this screen was not checked" % (name, shot), file=sys.stderr)
        return 2
    a, b = _open(golden), _open(shot)
    if a is None or b is None:
        return 2
    if a.size != b.size:
        print("FAIL %s: the picture is %dx%d and the approved one is %dx%d" % (name, b.size[0], b.size[1], a.size[0], a.size[1]))
        return 1
    ratio, mask = changed_ratio(a, b)
    ok = ratio <= tolerance
    print("%s %s: %.2f%% of pixels changed (limit %.2f%%)" % ("PASS" if ok else "FAIL", name, ratio * 100, tolerance * 100))
    if not ok:
        if diff_out:
            write_diff(a, mask, diff_out)
            print("  the changes are in red in %s" % diff_out)
        print("  If the change is wanted, the owner has to approve the new look: golden.py approve %s %s" % (name, shot))
        return 1
    return 0


def approve(screen: str, png: Path, goldens: Path) -> int:
    if not png.exists():
        print("%s does not exist" % png, file=sys.stderr)
        return 2
    if _open(png) is None:
        return 2
    dst = goldens / ("%s.png" % screen)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(png, dst)
    print("approved %s -> %s" % (screen, dst))
    return 0


def compare_all(shots: Path, goldens: Path, tolerance: float, diff_dir: Path | None) -> int:
    approved = sorted(goldens.glob("*.png")) if goldens.is_dir() else []
    if not approved:
        print("NOTHING WAS COMPARED: there is no approved picture in %s. This check proves nothing until the owner has approved a first version of each screen." % goldens)
        return 0
    worst = 0
    for g in approved:
        shot = shots / g.name
        if not shot.exists():
            print("FAIL %s: no picture of it in %s, so it was not checked" % (g.stem, shots))
            worst = max(worst, 1)
            continue
        worst = max(worst, compare(g, shot, tolerance, (diff_dir / g.name) if diff_dir else None))
    new = sorted(p.stem for p in shots.glob("*.png") if not (goldens / p.name).exists()) if shots.is_dir() else []
    if new:
        print("not yet approved (no golden, so not compared): %s" % ", ".join(new))
    return worst


def shot(app: str, datasets: str | None, dataset: str | None, width: int, height: int, out: Path) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit("`shot` needs Playwright and Chromium: pip install -r design/ui_from_image/requirements.txt && playwright install chromium")
    import serve
    with serve.serving(app, datasets) as base:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            try:
                ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1, reduced_motion="reduce",
                                          color_scheme="light", locale="en-US", timezone_id="UTC")
                pg = ctx.new_page()
                pg.goto(base + "/" + ("?dataset=datasets/%s" % dataset if dataset else ""))
                pg.wait_for_function("['idle','ready','empty','error'].includes(document.body.getAttribute('data-state'))", timeout=60000)
                pg.add_style_tag(content="*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}")
                pg.evaluate("async () => { await document.fonts.ready; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); await document.fonts.ready; }")
                out.parent.mkdir(parents=True, exist_ok=True)
                pg.screenshot(path=str(out), full_page=False)
            finally:
                browser.close()
    print("wrote %s (%dx%d window, state %s)" % (out, width, height, "dataset " + dataset if dataset else "no dataset"))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shot")
    s.add_argument("--app", required=True)
    s.add_argument("--datasets")
    s.add_argument("--dataset", help="a folder name inside --datasets, for example F02_everything; leave out for the screen before a dataset is chosen")
    s.add_argument("--width", type=int, default=1440)
    s.add_argument("--height", type=int, default=900)
    s.add_argument("--out", required=True)
    for name in ("approve", "compare"):
        p = sub.add_parser(name)
        p.add_argument("screen")
        p.add_argument("png")
        p.add_argument("--goldens", default=str(DEFAULT_GOLDENS))
        if name == "compare":
            p.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
            p.add_argument("--diff")
    c = sub.add_parser("compare-all")
    c.add_argument("--shots", required=True)
    c.add_argument("--goldens", default=str(DEFAULT_GOLDENS))
    c.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    c.add_argument("--diff-dir")
    a = ap.parse_args(argv)

    if a.cmd == "shot":
        return shot(a.app, a.datasets, a.dataset, a.width, a.height, Path(a.out))
    if a.cmd == "approve":
        return approve(a.screen, Path(a.png), Path(a.goldens))
    if a.cmd == "compare":
        return compare(Path(a.goldens) / ("%s.png" % a.screen), Path(a.png), a.tolerance, Path(a.diff) if a.diff else None)
    return compare_all(Path(a.shots), Path(a.goldens), a.tolerance, Path(a.diff_dir) if a.diff_dir else None)


if __name__ == "__main__":
    sys.exit(main())
