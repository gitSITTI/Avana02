#!/usr/bin/env python3
"""Map the colours seen in a picture onto the colours a target design already has, and say plainly where there is no good match.

    python3 conform.py --source palette.json --target TARGET [--out conform.json]
    python3 conform.py --source built_tokens.json --target TARGET --strict        check a page you BUILT

  --source   what palette_from_image.py wrote (format reqin-palette/1), or what target_tokens.py wrote for the page you BUILT (reqin-target-tokens/1), to check that
             the new page uses only the target's colours
  --target   what target_tokens.py wrote (reqin-target-tokens/1), or a CSS file that declares custom properties with colours (for example design/tokens.css)

The rule is the one a design system uses: a colour in the picture is the target's colour if it is close enough (OKLab distance x 100):
    up to 6        use    the target's colour; the picture's is the same colour for every purpose a design cares about
    6 up to 12     review it looks like the target's colour but a person should decide
    over 12        none   the target has nothing like it; do not force a match. Either the picture comes from another design, or the new screen needs a new token
Colours read off a picture are a few steps off (compression, anti-aliasing), so 6 is the right allowance there. A page you built writes its colours exactly, so for
that check use --strict: use up to 2.5, review up to 6. A colour that is 4 steps from a token is a different colour, and in a page you wrote it is a defect.

A match is only offered between colours that do the same job (text with text, a surface with a surface, a border with a border, a status colour with the same
status), taken from how the target uses its colours or, for a CSS file, from the name. A colour that is close but does another job is listed as 'wrong job'.

This is a suggestion from colour distance. It does not know where the colour sits in the picture: look at the picture before replacing anything.
Standard library only (plus colour.py next to this file).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colour as C  # noqa: E402

USE, REVIEW = 6.0, 12.0
STRICT_USE, STRICT_REVIEW = 2.5, 6.0

TEXT_WORDS = ("text", "ink", "slate", "muted", "body", "secondary", "strong", "label", "on-dark", "faint", "mono")
BORDER_WORDS = ("border", "line", "hair", "divider", "edge", "rule", "outline", "stroke")
FILL_WORDS = ("canvas", "paper", "band", "surface", "sunken", "hover", "selected", "fill", "bg", "background", "track", "placeholder", "card", "panel")
ACCENT_WORDS = ("accent", "brand", "primary")

# which roles in the target a source colour's role hint may be matched with
JOBS = {"background": {"background"}, "surface": {"background"}, "text": {"text"}, "control edge or muted text": {"border", "text"},
        "line (border or divider)": {"border"}, "accent": {"background", "text", "border", "icon", "outline"}}


def roles_from_name(name: str) -> set:
    n = name.lower().lstrip("-")
    out = set()
    if any(w in n for w in TEXT_WORDS) and not n.endswith("-fill"):
        out.add("text")
    if any(w in n for w in BORDER_WORDS):
        out.add("border")
    if any(w in n for w in FILL_WORDS):
        out.add("background")
    if any(w in n for w in ACCENT_WORDS):
        out |= {"background", "text", "border", "icon"}
    if "chart" in n:
        out = {"icon"}                                     # a mark in a chart is not a border or a text colour of the interface
    return out


def load_target(path: str) -> list:
    """[{hex, names, roles, count}] from a target-tokens JSON or from a CSS file."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    rows: dict = {}
    if path.lower().endswith(".json"):
        data = json.loads(text)
        if data.get("format") != "reqin-target-tokens/1":
            raise SystemExit("%s is not a reqin-target-tokens/1 file" % os.path.basename(path))
        for c in data["colours"]:
            roles = {k for k, v in c["uses"].items() if v}
            for n in c["names"]:
                roles |= roles_from_name(n)
            rows[c["hex"]] = {"hex": c["hex"], "names": list(c["names"]), "roles": roles, "count": c["count"]}
        for d in data["declared_vars"]:                     # a colour the page declares but does not paint with on this screen is still the design's colour
            p = C.parse_css(d["resolved"] or d["value"])
            if p and p[1] == 1.0:
                r = rows.setdefault(p[0], {"hex": p[0], "names": [], "roles": set(), "count": 0})
                if d["name"] not in r["names"]:
                    r["names"].append(d["name"])
                r["roles"] |= roles_from_name(d["name"])
    else:
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for name, value in re.findall(r"(--[\w-]+)\s*:\s*([^;{}]+)", text):
            p = C.parse_css(value.strip())
            if p and p[1] == 1.0:
                r = rows.setdefault(p[0], {"hex": p[0], "names": [], "roles": set(), "count": 0})
                if name not in r["names"]:
                    r["names"].append(name)
                r["roles"] |= roles_from_name(name)
    if not rows:
        raise SystemExit("no colours found in " + os.path.basename(path))
    return list(rows.values())


def compatible(src: dict, tgt: dict) -> bool:
    role = src["role_hint"]
    if role in JOBS:
        if role == "accent" and not C.lch(tgt["hex"])[1] >= 0.06:
            return False
        return bool(JOBS[role] & tgt["roles"]) or not tgt["roles"]
    for status in ("danger", "warn", "ok", "info"):
        if role == status or role == status + "-fill":
            return C.status_group(tgt["hex"]) == status and ((C.lch(tgt["hex"])[0] >= 0.88) == (role.endswith("-fill")) or role == status)
    return True


def decide(d: float, use: float = USE, review: float = REVIEW) -> str:
    return "use" if d <= use else "review" if d <= review else "none"


def palette_from_tokens(data: dict) -> dict:
    """A page's computed colours, shaped like a picture's palette. The job of a colour is the one it is used for most: text, a surface, or a border or line."""
    total = sum(c["count"] for c in data["colours"]) or 1
    job = {"text": "text", "background": "surface", "border": "line (border or divider)", "outline": "line (border or divider)", "icon": "other"}
    cols = []
    for c in data["colours"]:
        main = max(c["uses"], key=lambda k: c["uses"][k])
        cols.append({"hex": c["hex"], "share": round(c["count"] / total, 5), "role_hint": job[main]})
    return {"format": "reqin-palette/1", "image": data.get("source"), "colours": cols}


def conform(palette: dict, target: list, use: float = USE, review: float = REVIEW) -> dict:
    if palette.get("format") == "reqin-target-tokens/1":
        palette = palette_from_tokens(palette)
    if palette.get("format") != "reqin-palette/1":
        raise SystemExit("--source must be a reqin-palette/1 file (palette_from_image.py) or a reqin-target-tokens/1 file (target_tokens.py)")
    out, covered = [], {"use": 0.0, "review": 0.0, "none": 0.0}
    for src in palette["colours"]:
        ranked = sorted(((C.delta_e(src["hex"], t["hex"]), t) for t in target), key=lambda p: p[0])
        ok = [(d, t) for d, t in ranked if compatible(src, t)]
        best = ok[0] if ok else None
        wrong_job = None
        if ranked[0][0] <= use and (best is None or best[0] > use):
            wrong_job = {"hex": ranked[0][1]["hex"], "names": ranked[0][1]["names"], "delta_e": round(ranked[0][0], 2)}
        decision = decide(best[0], use, review) if best else "none"
        item = {"source_hex": src["hex"], "share": src["share"], "role_hint": src["role_hint"], "decision": decision}
        if best and decision != "none":
            d, t = best
            item["match"] = {"hex": t["hex"], "names": t["names"], "delta_e": round(d, 2)}
            item["replace_with"] = "var(%s)" % t["names"][0] if t["names"] else t["hex"]
        else:
            item["match"] = None
            item["replace_with"] = None
            near = [{"hex": t["hex"], "names": t["names"], "delta_e": round(d, 2)} for d, t in (ok or ranked)[:2]]
            item["nearest"] = near
        if wrong_job:
            item["wrong_job"] = wrong_job
        covered[decision] += src["share"]
        out.append(item)
    used = {i["match"]["hex"] for i in out if i["match"]}
    return {"format": "reqin-conform/1", "source": palette.get("image"), "thresholds": {"use": use, "review": review},
            "share_of_picture": {k: round(v, 4) for k, v in covered.items()}, "colours": out,
            "target_colours_not_seen_in_picture": [t["hex"] for t in target if t["hex"] not in used],
            "notes": ["a match is a suggestion from colour distance between colours that do the same job; it cannot see where the colour sits in the picture",
                      "'none' is an answer: the target has no such colour. Do not pick the nearest one to make the report look complete"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", metavar="FILE")
    ap.add_argument("--strict", action="store_true", help="for a page you built: use up to %.1f, review up to %.1f" % (STRICT_USE, STRICT_REVIEW))
    a = ap.parse_args(argv)
    with open(a.source, encoding="utf-8") as f:
        pal = json.load(f)
    res = conform(pal, load_target(a.target), *( (STRICT_USE, STRICT_REVIEW) if a.strict else (USE, REVIEW) ))
    print("%s against %s" % (res["source"], os.path.basename(a.target)))
    sh = res["share_of_picture"]
    print("  of the picture's pixels: %.1f%% use, %.1f%% review, %.1f%% no match" % (100 * sh["use"], 100 * sh["review"], 100 * sh["none"]))
    for i in res["colours"]:
        m = i["match"]
        tail = "%s %s (distance %.1f)" % (m["hex"], ",".join(m["names"]) or "unnamed", m["delta_e"]) if m else "nearest %s" % ", ".join("%s (%.1f)" % (n["hex"], n["delta_e"]) for n in i.get("nearest", []))
        extra = "   [a colour of another job is close: %s]" % i["wrong_job"]["hex"] if i.get("wrong_job") else ""
        print("  %s  %5.2f%%  %-22s %-7s %s%s" % (i["source_hex"], 100 * i["share"], i["role_hint"][:22], i["decision"], tail, extra))
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
