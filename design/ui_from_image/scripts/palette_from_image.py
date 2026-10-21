#!/usr/bin/env python3
"""Pull the colour palette out of a screenshot, with a guess at what each colour is for.

    python3 palette_from_image.py shot.png                       print the palette
    python3 palette_from_image.py shot.png --json palette.json   also write it (format reqin-palette/1)
    python3 palette_from_image.py shot.png --swatches sw.png     also draw a sheet of the colours with their hex codes and shares, to look at

How it works: every distinct colour in the picture is counted exactly (a screenshot is mostly flat fills), then colours that differ by less than
--merge (OKLab distance x 100, default 2.5: anti-aliasing and compression noise) are merged into the most frequent one. Nothing is guessed about shapes.

The role hints are heuristics, written down in role_hints() below, so a person can read them: they say what a colour *probably* is for, never what it is.
Needs Pillow and numpy:  pip install pillow numpy
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colour as C  # noqa: E402

try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("palette_from_image.py needs Pillow and numpy: pip install pillow numpy")

MAX_PIXELS = 1_500_000


def load_rgb(path: str) -> "Image.Image":
    im = Image.open(path)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        base = Image.new("RGBA", im.size, (255, 255, 255, 255))
        base.alpha_composite(im)
        im = base
    im = im.convert("RGB")
    if im.width * im.height > MAX_PIXELS:
        f = (MAX_PIXELS / (im.width * im.height)) ** 0.5
        im = im.resize((max(1, int(im.width * f)), max(1, int(im.height * f))), Image.NEAREST)
    return im


def _oklab_array(rgb: "np.ndarray") -> "np.ndarray":
    c = rgb.astype(np.float64) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = c[:, 0], c[:, 1], c[:, 2]
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], axis=1)


def clusters(im: "Image.Image", merge: float = 2.5, max_colours: int = 40, min_share: float = 0.0005):
    """([(hex, pixel count, fill ratio)], total pixels), most frequent first. A cluster's colour is its most frequent exact colour.

    The fill ratio is the share of a cluster's pixels whose four neighbours are in the same cluster: near 1 for a flat area (a panel, a band, a button),
    near 0 for text and thin lines, which are made of edges. It is what tells a dark panel from dark text."""
    h, w = im.height, im.width
    a = np.asarray(im).reshape(-1, 3)
    total = len(a)
    packed = (a[:, 0].astype(np.uint32) << 16) | (a[:, 1].astype(np.uint32) << 8) | a[:, 2].astype(np.uint32)
    uniq, inv, counts = np.unique(packed, return_inverse=True, return_counts=True)
    order = np.argsort(-counts, kind="stable")
    rank = np.empty_like(order)
    rank[order] = np.arange(len(order))
    uniq, counts = uniq[order], counts[order]
    rgb = np.stack([(uniq >> 16) & 255, (uniq >> 8) & 255, uniq & 255], axis=1)
    lab = _oklab_array(rgb)
    free = np.ones(len(uniq), dtype=bool)
    assign = np.full(len(uniq), -1, dtype=np.int32)
    found = []
    while free.any() and len(found) < max_colours:
        i = int(np.argmax(free))                      # the most frequent colour not yet taken (the array is sorted by count)
        d = 100 * np.sqrt(((lab - lab[i]) ** 2).sum(axis=1))
        take = free & (d <= merge)
        n = int(counts[take].sum())
        if n / total < min_share and found:
            break
        assign[take] = len(found)
        found.append((C.rgb_to_hex(*rgb[i]), n))
        free &= ~take
    labels = assign[rank[inv]].reshape(h, w)
    out = []
    for k, (hx, n) in enumerate(found):
        m = labels == k
        if h > 2 and w > 2:
            inner = m[1:-1, 1:-1] & m[:-2, 1:-1] & m[2:, 1:-1] & m[1:-1, :-2] & m[1:-1, 2:]
            fill = float(inner.sum()) / max(1, n)
        else:
            fill = 1.0
        out.append((hx, n, fill))
    return out, total


def role_hints(entries: list[dict]) -> None:
    """Add 'role_hint' to each entry (a list of dicts with hex, share, contrast_vs_background, group, lightness). The rules, in order:

    background     the colour with the largest share
    surface        a neutral colour that is mostly flat area (fill ratio at least 0.5) and has at least 0.5% of the picture: cards, panels, bars, a dark band
    text           a neutral colour made of edges (fill ratio under 0.5) with contrast of at least 4.5 to the background
    line           a neutral colour made of edges with contrast under 3 to the background: a border or a divider
    control edge   a neutral colour made of edges with contrast from 3 to 4.5: the edge of a button or an input, or a muted label
    accent         the most saturated non-neutral colour, if it has at least 0.05% of the picture and chroma of at least 0.1
    <status>-fill  a pale (lightness at least 0.88) tint whose hue reads as red, amber, green or blue
    <status>       a stronger colour of the same reading (danger, warn, ok, info)
    A saturated colour that is also mostly flat area and over 1% of the picture is a coloured surface, not an accent.
    other          anything else
    """
    if not entries:
        return
    bg = entries[0]
    bg["role_hint"] = "background"
    best_accent = None
    for e in entries[1:]:
        if e["group"] == "neutral":
            if e["fill_ratio"] >= 0.5 and e["share"] >= 0.005:
                e["role_hint"] = "surface"
            elif e["contrast_vs_background"] >= 4.5:
                e["role_hint"] = "text"
            elif e["contrast_vs_background"] >= 3.0:
                e["role_hint"] = "control edge or muted text"
            else:
                e["role_hint"] = "line (border or divider)"
        else:
            e["role_hint"] = "other"
            if e["chroma"] >= 0.1 and e["share"] >= 0.0005 and not (e["fill_ratio"] >= 0.5 and e["share"] >= 0.01) and (best_accent is None or e["chroma"] > best_accent["chroma"]):
                best_accent = e
    for e in entries[1:]:
        if e["group"] != "neutral":
            st = e["status"]
            if st != "other":
                e["role_hint"] = st + ("-fill" if e["lightness"] >= 0.88 else "")
    if best_accent is not None:
        best_accent["role_hint"] = "accent"


def palette(path: str, merge: float = 2.5, max_colours: int = 40) -> dict:
    im = load_rgb(path)
    found, total = clusters(im, merge, max_colours)
    entries = []
    bg_hex = found[0][0]
    for hx, n, fill in found:
        L, Ch, H = C.lch(hx)
        entries.append({"hex": hx, "share": round(n / total, 5), "pixels": n, "fill_ratio": round(fill, 3), "lightness": round(L, 3), "chroma": round(Ch, 3), "hue": round(H, 1),
                        "group": "neutral" if C.is_neutral(hx) else "tinted", "hue_name": C.hue_name(hx), "status": C.status_group(hx),
                        "contrast_vs_background": round(C.contrast(hx, bg_hex), 2)})
    role_hints(entries)
    for e in entries:
        e.pop("group", None)
    covered = sum(e["share"] for e in entries)
    return {"format": "reqin-palette/1", "image": os.path.basename(path), "size": [im.width, im.height], "merge_delta_e": merge,
            "colours": entries, "share_covered": round(covered, 4),
            "notes": ["role_hint is a heuristic (see role_hints in palette_from_image.py): check it against the picture before relying on it",
                      "a colour used only in a thin line or small icon can have a share under 0.05% and be missing: lower --min-share or crop the picture to the part you care about"]}


def swatches(pal: dict, out: str) -> None:
    cols = pal["colours"]
    row_h, w = 34, 520
    im = Image.new("RGB", (w, row_h * len(cols) + 8), "white")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.load_default()
    except Exception:  # pragma: no cover
        font = None
    for i, e in enumerate(cols):
        y = 4 + i * row_h
        d.rectangle([8, y, 64, y + row_h - 6], fill=e["hex"], outline="#888888")
        d.text((76, y + 4), "%s   %5.2f%%   %s" % (e["hex"], 100 * e["share"], e["role_hint"]), fill="black", font=font)
        d.text((76, y + 16), "contrast with background %.1f:1" % e["contrast_vs_background"], fill="#555555", font=font)
    im.save(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--swatches", metavar="PNG")
    ap.add_argument("--merge", type=float, default=2.5, help="colours closer than this (OKLab x 100) are one colour")
    ap.add_argument("--max", type=int, default=40, help="most colours to report")
    a = ap.parse_args(argv)
    pal = palette(a.image, a.merge, a.max)
    print("%s: %d x %d, %d colours cover %.1f%% of the pixels" % (pal["image"], pal["size"][0], pal["size"][1], len(pal["colours"]), 100 * pal["share_covered"]))
    for e in pal["colours"]:
        print("  %s  %6.2f%%  flat %.2f  contrast %5.1f  %-8s %s" % (e["hex"], 100 * e["share"], e["fill_ratio"], e["contrast_vs_background"], e["hue_name"], e["role_hint"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(pal, f, indent=2)
            f.write("\n")
    if a.swatches:
        swatches(pal, a.swatches)
    return 0


if __name__ == "__main__":
    sys.exit(main())
