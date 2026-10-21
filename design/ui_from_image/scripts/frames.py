#!/usr/bin/env python3
"""Cut a screenshot into component frames, and make the coordinates readable.

    python3 frames.py grid   shot.png grid.png [--step 100]                draw a labelled grid, so you can read pixel positions off the picture
    python3 frames.py detect shot.png out/ [--region X,Y,W,H] [--min-gap 12] [--level N]
                                                                           propose blocks; writes out/candidates.json (a tree) and out/overview.png
    python3 frames.py crop   shot.png out/ --box button=40,120,160,44 ...  cut named boxes (x,y,width,height) into out/<name>.png and out/frames.json

Why this exists: a model that is asked "where is the button?" in a picture is often a few dozen pixels off. Draw the grid, look at the picture, read the numbers
off it, crop, then LOOK at the crop. If the crop is not the component, the box was wrong; try again before building anything from it.

`detect` is a plain recursive split of the picture. A region is cut where
  1. a band of at least --min-gap pixels has nothing in it (no colour change at all), or
  2. a long straight colour change crosses at least --rule (default 0.97) of the region: the border of a panel, the edge of a bar, a divider.
It finds blocks. It does not know what a button is, and two buttons 8 pixels apart stay one block at the default gap: to split a block further, run `detect`
again on it with --region and a smaller --min-gap. (Every colour change is marked one pixel to each side, so a band has to be --min-gap pixels empty after that:
two lines of text drawn 7 px apart count as 5 px apart.) Treat the boxes as candidates to accept, merge or throw away after looking at overview.png.
Needs Pillow and numpy:  pip install pillow numpy
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("frames.py needs Pillow and numpy: pip install pillow numpy")


def _open(path: str) -> "Image.Image":
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        base = Image.new("RGBA", im.size, (255, 255, 255, 255))
        base.alpha_composite(im)
        im = base
    return im.convert("RGB")


def grid(src: str, out: str, step: int = 100) -> None:
    im = _open(src)
    d = ImageDraw.Draw(im, "RGBA")
    font = ImageFont.load_default()
    for x in range(0, im.width, step):
        d.line([(x, 0), (x, im.height)], fill=(220, 30, 30, 90), width=1)
        d.text((x + 2, 2), str(x), fill=(200, 0, 0, 255), font=font)
    for y in range(0, im.height, step):
        d.line([(0, y), (im.width, y)], fill=(30, 30, 220, 90), width=1)
        d.text((2, y + 2), str(y), fill=(0, 0, 200, 255), font=font)
    im.save(out)


# ---------------------------------------------------------------- the splitter

def edge_maps(im: "Image.Image", tol: int = 24):
    """(H, V): H is True where a pixel differs from the pixel above or below it (a horizontal edge passes through), V where it differs from the pixel to its left or
    right. 'Differs' is a summed channel difference over tol, so a flat fill of any colour has no edges and a white card on a grey page is found by its border."""
    a = np.asarray(im).astype(np.int16)
    h, w = a.shape[:2]
    hm = np.zeros((h, w), dtype=bool)
    vm = np.zeros((h, w), dtype=bool)
    d = np.abs(a[1:] - a[:-1]).sum(axis=2) > tol
    hm[:-1] |= d
    hm[1:] |= d
    d = np.abs(a[:, 1:] - a[:, :-1]).sum(axis=2) > tol
    vm[:, :-1] |= d
    vm[:, 1:] |= d
    return hm, vm


LONG = 64     # a straight change is only a border if the line it crosses is at least this long
CORNER = 16   # pixels at each end of a line that are not counted when asking how much of a region a straight change crosses: rounded corners must not lower it


def _span(n: int) -> slice:
    return slice(CORNER, n - CORNER) if n > 4 * CORNER else slice(0, n)


def row_cover(a: "np.ndarray") -> "np.ndarray":
    """Share of each row's width (corners left out) that a horizontal edge crosses."""
    return a[:, _span(a.shape[1])].mean(axis=1)


def col_cover(a: "np.ndarray") -> "np.ndarray":
    return a[_span(a.shape[0]), :].mean(axis=0)


def _runs(mask: "np.ndarray"):
    """[(first, last)] of each run of True in a 1-D boolean array (last is inclusive)."""
    out, i, n = [], 0, len(mask)
    while i < n:
        if mask[i]:
            j = i
            while j + 1 < n and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def _pieces_from_cuts(n: int, cuts: list) -> list:
    """Half-open ranges between cut positions: cuts [m1, m2] on length n gives [(0, m1), (m1, m2), (m2, n)]."""
    edges = [0] + sorted(cuts) + [n]
    return [(a, b) for a, b in zip(edges[:-1], edges[1:]) if b > a]


def _gap_pieces(has_edge: "np.ndarray", min_gap: int):
    """Pieces separated by interior runs of at least min_gap rows (or columns) with nothing in them, or None if there is no such run."""
    n = len(has_edge)
    bands = [(a, b) for a, b in _runs(~has_edge) if b - a + 1 >= min_gap and a > 0 and b < n - 1]
    if not bands:
        return None
    pieces, start = [], 0
    for a, b in bands:
        pieces.append((start, a))
        start = b + 1
    pieces.append((start, n))
    return [(a, b) for a, b in pieces if b > a]


def _rule_cuts(cover: "np.ndarray", rule: float):
    """(cut positions, best coverage) for the rows (or columns) that a long straight colour change crosses, or None. A change between pixel k and k+1 marks both
    pixels, so a run of marked rows is one border: it is cut through the middle of the run. Runs touching the region's own edge are its border, not a cut."""
    n = len(cover)
    runs = [(a, b) for a, b in _runs(cover >= rule) if a >= 2 and b <= n - 3]
    if not runs:
        return None
    return [(a + b + 1) // 2 for a, b in runs], max(float(cover[a:b + 1].max()) for a, b in runs)


def border_core(hm, vm, region, rule: float, cap: int = 5, allowed=(True, True, True, True)):
    """The region without its own border lines (a card's outline, a bar's edge): ((x0, y0, x1, y1), [top, bottom, left, right] -> was there a border on that side).
    A border is a row or column that a straight colour change crosses along at least `rule` of the region, at most `cap` pixels deep on each side; `allowed` says which
    sides may be stripped (top, bottom, left, right).
    Without this a card's own side borders mark every row and no empty band could ever be found inside it."""
    x0, y0, x1, y1 = region
    sides, depth = [False] * 4, [0] * 4
    while True:
        moved = False
        if allowed[0] and y1 - y0 > 2 and depth[0] < cap and row_cover(hm[y0:y0 + 1, x0:x1])[0] >= rule:
            y0, depth[0], sides[0], moved = y0 + 1, depth[0] + 1, True, True
        if allowed[1] and y1 - y0 > 2 and depth[1] < cap and row_cover(hm[y1 - 1:y1, x0:x1])[0] >= rule:
            y1, depth[1], sides[1], moved = y1 - 1, depth[1] + 1, True, True
        if allowed[2] and x1 - x0 > 2 and depth[2] < cap and col_cover(vm[y0:y1, x0:x0 + 1])[0] >= rule:
            x0, depth[2], sides[2], moved = x0 + 1, depth[2] + 1, True, True
        if allowed[3] and x1 - x0 > 2 and depth[3] < cap and col_cover(vm[y0:y1, x1 - 1:x1])[0] >= rule:
            x1, depth[3], sides[3], moved = x1 - 1, depth[3] + 1, True, True
        if not moved:
            return (x0, y0, x1, y1), sides


def clear_corner_arcs(em, hm, vm, core, sides, size: int = CORNER + 2) -> None:
    """Forget the marks of a rounded corner, in place, so the first and last block inside a card do not stretch out to the card's edge. Only marks that touch the
    stripped border and lie in the corner square are forgotten: they belong to the border, not to what it holds."""
    x0, y0, x1, y1 = core
    for top, left, hit in ((True, True, sides[0] and sides[2]), (True, False, sides[0] and sides[3]),
                           (False, True, sides[1] and sides[2]), (False, False, sides[1] and sides[3])):
        if not hit:
            continue
        sy0, sy1 = (y0, min(y1, y0 + size)) if top else (max(y0, y1 - size), y1)
        sx0, sx1 = (x0, min(x1, x0 + size)) if left else (max(x0, x1 - size), x1)
        sq = em[sy0:sy1, sx0:sx1]
        seed = np.zeros_like(sq)
        seed[0 if top else -1, :] = sq[0 if top else -1, :]
        seed[:, 0 if left else -1] |= sq[:, 0 if left else -1]
        grown = seed
        for _ in range(size):
            p = np.pad(grown, 1)
            nxt = (p[:-2, 1:-1] | p[2:, 1:-1] | p[1:-1, :-2] | p[1:-1, 2:] | p[:-2, :-2] | p[:-2, 2:] | p[2:, :-2] | p[2:, 2:] | grown) & sq
            if (nxt == grown).all():
                break
            grown = nxt
        em[sy0:sy1, sx0:sx1] &= ~grown
        hm[sy0:sy1, sx0:sx1] &= ~grown
        vm[sy0:sy1, sx0:sx1] &= ~grown


def detect_tree(im: "Image.Image", region=None, min_gap: int = 12, min_size: int = 10, tol: int = 24, rule: float = 0.97, max_depth: int = 14):
    """The tree of blocks. Each node: {n, box [x, y, w, h], depth, parent, leaf, cut}. 'cut' says how the node was split ('empty rows', 'empty columns', 'rule rows',
    'rule columns', 'inside border') or is None for a leaf. Boxes are trimmed to what is inside them.

    Which lines a region ignores when it looks for cuts inside itself: the line a border cut left on its edge (it belongs to the neighbour), and, when the region is a panel
    (a long line on three or four of its sides), its own border. The top and bottom lines of a column of cards are not stripped: they are the first card's top and the last
    card's bottom."""
    hm, vm = edge_maps(im, tol)
    em = hm | vm
    nodes: list = []
    rx, ry, rw, rh = region if region else (0, 0, im.width, im.height)
    NONE = (False, False, False, False)

    def trim(x0, y0, x1, y1):
        reg = em[y0:y1, x0:x1]
        rows = np.where(reg.any(axis=1))[0]
        cols = np.where(reg.any(axis=0))[0]
        if len(rows) == 0:
            return None
        t = (x0 + int(cols[0]), y0 + int(rows[0]), x0 + int(cols[-1]) + 1, y0 + int(rows[-1]) + 1)
        return t if (t[2] - t[0] >= min_size and t[3] - t[1] >= min_size) else None

    def stripped(region, depth, shared):
        """(core, sides): the region without the lines it should not look at, and which sides lost one."""
        _, raw_sides = border_core(hm, vm, region, rule)
        panel = depth == 0 or sum(raw_sides) >= 3
        allowed = tuple(bool(raw_sides[i] and (panel or shared[i])) for i in range(4))
        if not any(allowed):
            return region, list(NONE)
        return border_core(hm, vm, region, rule, allowed=allowed)

    def split(x0, y0, x1, y1, depth, shared):
        """(how, [(sub-region, which of its edges lie on a border cut)]) or None."""
        (x0, y0, x1, y1), _ = stripped((x0, y0, x1, y1), depth, shared)
        reg_e = em[y0:y1, x0:x1]
        w, h = x1 - x0, y1 - y0
        p = _gap_pieces(reg_e.any(axis=1), min_gap)
        if p:
            return "empty rows", [((x0, y0 + a, x1, y0 + b), NONE) for a, b in p]
        p = _gap_pieces(reg_e.any(axis=0), min_gap)
        if p:
            return "empty columns", [((x0 + a, y0, x0 + b, y1), NONE) for a, b in p]
        # a border is only a border if the line it crosses is long: a tall letter stem crosses nearly all of a short line of text
        rr = _rule_cuts(row_cover(hm[y0:y1, x0:x1]), rule) if w >= LONG and h >= 2 * CORNER else None
        rc = _rule_cuts(col_cover(vm[y0:y1, x0:x1]), rule) if h >= LONG and w >= 2 * CORNER else None
        if rr and (not rc or rr[1] >= rc[1]):
            ps = _pieces_from_cuts(h, rr[0])
            return "rule rows", [((x0, y0 + a, x1, y0 + b), (i > 0, i < len(ps) - 1, False, False)) for i, (a, b) in enumerate(ps)]
        if rc:
            ps = _pieces_from_cuts(w, rc[0])
            return "rule columns", [((x0 + a, y0, x0 + b, y1), (False, False, i > 0, i < len(ps) - 1)) for i, (a, b) in enumerate(ps)]
        return None

    def rec(x0, y0, x1, y1, depth, parent, shared=NONE):
        t = trim(x0, y0, x1, y1)
        if t is None:
            return
        # a shared line is still on this region's edge only if trimming did not move that edge away
        shared = (shared[0] and t[1] - y0 <= 3, shared[1] and y1 - t[3] <= 3, shared[2] and t[0] - x0 <= 3, shared[3] and x1 - t[2] <= 3)
        raw, raw_sides = border_core(hm, vm, t, rule)
        core, sides = stripped(t, depth, shared)
        clear_corner_arcs(em, hm, vm, core, sides)
        if not em[raw[1]:raw[3], raw[0]:raw[2]].any() and not all(raw_sides):
            return                      # nothing inside and not closed on every side: a strip between two panels, or a lone line, not a block
        node = {"n": len(nodes) + 1, "box": [t[0], t[1], t[2] - t[0], t[3] - t[1]], "depth": depth, "parent": parent, "leaf": True, "cut": None}
        nodes.append(node)
        cur, cur_shared = t, shared
        panel = sum(sides) >= 3

        def inside_border():
            """A panel whose content does not split any further still shows that content as a block of its own (a card holding one chip, one paragraph)."""
            c = trim(*core)
            if panel and cur == t and c is not None and max(abs(c[0] - t[0]), abs(c[1] - t[1]), abs(c[2] - t[2]), abs(c[3] - t[3])) >= 4:
                node["leaf"], node["cut"] = False, "inside border"
                rec(*c, depth + 1, node["n"])
                return True
            return False

        while depth < max_depth:
            s = split(*cur, depth, cur_shared)
            if s is None:
                inside_border()
                return
            how, subs = s
            live = [(sr, sh) for sr, sh in subs if trim(*sr) is not None]
            if len(live) < 2:
                if not live:
                    return
                if inside_border():
                    return
                cur, cur_shared = live[0]          # only one piece has anything: same block, look inside it
                continue
            node["leaf"], node["cut"] = False, how
            for sr, sh in live:
                rec(*sr, depth + 1, node["n"], sh)
            return

    rec(rx, ry, rx + rw, ry + rh, 0, None)
    return nodes


def detect_boxes(im: "Image.Image", min_gap: int = 12, min_size: int = 10, tol: int = 24, rule: float = 0.97, region=None):
    """The leaf blocks as (x, y, w, h) tuples."""
    return [tuple(n["box"]) for n in detect_tree(im, region, min_gap, min_size, tol, rule) if n["leaf"]]


def shown(nodes: list, level):
    """Which nodes the overview draws: the leaves (level None), or the nodes at depth `level` plus any leaf above it."""
    if level is None:
        return [n for n in nodes if n["leaf"]]
    return [n for n in nodes if n["depth"] == level or (n["leaf"] and n["depth"] < level)]


def crop(src: str, out_dir: str, boxes: dict) -> list:
    im = _open(src)
    os.makedirs(out_dir, exist_ok=True)
    frames = []
    for name, (x, y, w, h) in boxes.items():
        if w <= 0 or h <= 0 or x < 0 or y < 0 or x + w > im.width or y + h > im.height:
            raise SystemExit(f"box {name}={x},{y},{w},{h} is outside the picture ({im.width} x {im.height})")
        path = os.path.join(out_dir, f"{name}.png")
        im.crop((x, y, x + w, y + h)).save(path)
        with open(path, "rb") as f:
            sha = hashlib.sha256(f.read()).hexdigest()
        frames.append({"name": name, "box": [x, y, w, h], "file": f"{name}.png", "sha256": sha, "source": os.path.basename(src)})
    with open(os.path.join(out_dir, "frames.json"), "w", encoding="utf-8") as f:
        json.dump({"format": "reqin-frames/1", "source": os.path.basename(src), "size": [im.width, im.height], "frames": frames}, f, indent=2)
        f.write("\n")
    return frames


def _numbers(spec: str, what: str) -> tuple:
    parts = spec.split(",")
    if len(parts) != 4 or not all(p.strip().lstrip("-").isdigit() for p in parts):
        raise SystemExit(f"{what} wants X,Y,W,H with whole numbers, got {spec!r}")
    return tuple(int(p) for p in parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid")
    g.add_argument("image")
    g.add_argument("out")
    g.add_argument("--step", type=int, default=100)
    d = sub.add_parser("detect")
    d.add_argument("image")
    d.add_argument("out_dir")
    d.add_argument("--region", metavar="X,Y,W,H", help="look only inside this box (full-picture coordinates)")
    d.add_argument("--min-gap", type=int, default=12, help="an empty band at least this wide is a cut")
    d.add_argument("--min-size", type=int, default=10, help="drop blocks smaller than this in either direction (specks and hairlines)")
    d.add_argument("--tol", type=int, default=24, help="summed channel difference that counts as a colour change")
    d.add_argument("--rule", type=float, default=0.97, help="share of a region a straight colour change must cross to be a cut")
    d.add_argument("--level", type=int, default=None, help="draw the blocks at this depth of the tree instead of the leaves")
    c = sub.add_parser("crop")
    c.add_argument("image")
    c.add_argument("out_dir")
    c.add_argument("--box", action="append", required=True, metavar="NAME=X,Y,W,H")
    a = ap.parse_args(argv)
    if a.cmd == "grid":
        grid(a.image, a.out, a.step)
        print("wrote", a.out)
    elif a.cmd == "detect":
        im = _open(a.image)
        region = _numbers(a.region, "--region") if a.region else None
        if region and (region[0] < 0 or region[1] < 0 or region[2] <= 0 or region[3] <= 0 or region[0] + region[2] > im.width or region[1] + region[3] > im.height):
            raise SystemExit(f"--region {a.region} is outside the picture ({im.width} x {im.height})")
        nodes = detect_tree(im, region, a.min_gap, a.min_size, a.tol, a.rule)
        os.makedirs(a.out_dir, exist_ok=True)
        ov = im.copy()
        dr = ImageDraw.Draw(ov, "RGBA")
        font = ImageFont.load_default()
        for n in shown(nodes, a.level):
            x, y, w, h = n["box"]
            dr.rectangle([x, y, x + w - 1, y + h - 1], outline=(220, 30, 30, 255), width=2)
            lab = str(n["n"])
            ty = y - 13 if y >= 13 else y          # the tag sits above the box, so it never covers what the box holds
            dr.rectangle([x, ty, x + 6 * len(lab) + 6, ty + 12], fill=(220, 30, 30, 255))
            dr.text((x + 3, ty + 1), lab, fill="white", font=font)
        ov.save(os.path.join(a.out_dir, "overview.png"))
        with open(os.path.join(a.out_dir, "candidates.json"), "w", encoding="utf-8") as f:
            json.dump({"format": "reqin-candidates/2", "source": os.path.basename(a.image), "size": [im.width, im.height], "region": list(region) if region else None,
                       "settings": {"min_gap": a.min_gap, "min_size": a.min_size, "tol": a.tol, "rule": a.rule}, "nodes": nodes,
                       "note": "a tree of blocks found by splitting along empty bands and long straight borders; look at overview.png, then accept, merge or drop each one"}, f, indent=2)
            f.write("\n")
        leaves = sum(1 for n in nodes if n["leaf"])
        print(f"{len(nodes)} blocks ({leaves} leaves); look at {os.path.join(a.out_dir, 'overview.png')}")
    else:
        boxes = {}
        for spec in a.box:
            name, _, nums = spec.partition("=")
            if not name:
                raise SystemExit(f"--box wants NAME=X,Y,W,H, got {spec!r}")
            boxes[name] = _numbers(nums, "--box")
        for fr in crop(a.image, a.out_dir, boxes):
            print("wrote", os.path.join(a.out_dir, fr["file"]), fr["box"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
