#!/usr/bin/env python3
"""Check a component spec file (format reqin-components/1) before anything is built from it.

    python3 check_component_specs.py SPEC.json --tokens design/tokens.css [--paths paths.json] [--navigation design/navigation.json] [--json report.json]

--tokens   a CSS file that declares the design's custom properties, or a target_tokens.py result: the names a component may use
--paths    {"DS": ["DS.mid", ...], "CL": [...]} every field path that really occurs in what the app reads (python3 tools/gui_checks/datapaths.py --json paths.json).
           Without it a binding is checked for its form only, and the report says so.
--navigation design/navigation.json: the map of the product's screens and menus. A component that leads somewhere (a menu item, a tab, a link) must say where, in `goes_to`:
           a screen id from the map, `sheet:ID`, `overlay:ID`, `external: WHAT`, `none: WHY` (it leads nowhere, and why), or `unknown: WHAT IS NEEDED` (not confirmed yet: reported,
           never passed over). With the map, the ids are looked up and a menu item, tab or link with no `goes_to` is an error. Without it only the form is checked and the report
           says that where it leads was not checked. A picture shows the words in a menu and not where they lead: this is how that gap is closed.

What it enforces, because each of these is how a rebuilt screen went wrong:
  - a component's colours, radii, fonts, spacing and shadows are TOKEN NAMES (--accent), never a literal (#1A4DB5, 8px). A literal is how a rebuilt page ends up a
    few shades off. (Two exceptions: a font weight written as 100 to 900, and a unitless line height such as 1.5: they are steps on a scale, not measurements.) If the design really needs a value it has no token for, the spec adds it under new_tokens with a reason, and the report lists it for a person.
  - every component says where its content comes from: STATIC (text that is part of the design), NONE (decoration), or a field path that exists in real output.
    A component that shows a number or a name and says STATIC is a hard-coded screen; the check cannot tell, so the report lists every STATIC slot to be looked at.
  - names are unique, kinds and states are from a fixed list, a frame (where the component was found in the picture) is a sane box.
Exit status 1 when there is any error. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

KINDS = ("button", "link", "input", "select", "checkbox", "radio", "badge", "chip", "card", "panel", "banner", "nav-item", "nav", "table", "table-row", "list-item",
         "heading", "text", "icon", "chart", "avatar", "tab", "toast", "dialog", "progress", "other")
STATES = ("default", "hover", "focus-visible", "active", "disabled", "selected", "checked", "error", "loading", "empty", "read-only")
STYLE_KEYS = ("color", "background", "border", "border-color", "radius", "font", "font-size", "font-weight", "line-height", "padding", "gap", "shadow", "outline", "height", "width")
KEEP = {"none", "0", "inherit", "currentcolor", "auto", "initial"}
LITERAL = re.compile(r"(#[0-9a-fA-F]{3,8}\b|\b(rgb|rgba|hsl|hsla|oklch|oklab)\(|-?\d*\.?\d+(px|rem|em|pt|%|vh|vw|ms|s)\b|\b\d{3}\b)")
TOKEN = re.compile(r"^--[a-z0-9][a-z0-9-]*$")
NAME = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
PATH = re.compile(r"^(DS|LK|RJ|RPT|MAN|CL|PR|SL|CMP|VEE|WORK)(\.[A-Za-z_]\w*|\[\])+$")
GOES_TO = re.compile(r"^(?:(?P<screen>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)|(?P<kind>sheet|overlay):(?P<id>[a-z][a-z0-9]*(?:-[a-z0-9]+)*)|(?P<free>none|external|unknown):\s*(?P<why>\S.*))$")
LEADS = ("nav-item", "tab", "link")                  # kinds that exist to lead somewhere
PREFIXES_WITHOUT_PRODUCER = ("WORK",)      # saved work state: a path form is checked, existence is not (it is written by the page, not by reqin)


def token_names(path: str) -> set:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if path.lower().endswith(".json"):
        data = json.loads(text)
        if data.get("format") == "reqin-target-tokens/1":
            return {d["name"] for d in data["declared_vars"]}
        raise SystemExit("%s: a JSON token file must be a reqin-target-tokens/1 result" % os.path.basename(path))
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    return set(re.findall(r"(--[\w-]+)\s*:", text))


def as_list(v):
    return v if isinstance(v, list) else [v]


def nav_ids(navigation: dict | None) -> dict | None:
    if navigation is None:
        return None
    return {"screen": {x.get("id") for x in navigation.get("screens", []) if isinstance(x, dict)},
            "sheet": {x.get("id") for x in navigation.get("sheets", []) if isinstance(x, dict)},
            "overlay": {x.get("id") for x in navigation.get("overlays", []) if isinstance(x, dict)}}


def check(spec: dict, tokens: set, paths: dict | None = None, navigation: dict | None = None) -> dict:
    errors, warnings, statics, new_used = [], [], [], set()
    ids = nav_ids(navigation)
    unknown_goes = []
    if spec.get("format") != "reqin-components/1":
        errors.append("format must be 'reqin-components/1'")
    comps = spec.get("components")
    if not isinstance(comps, list) or not comps:
        errors.append("components must be a non-empty list")
        comps = []
    new_tokens = {}
    for i, nt in enumerate(spec.get("new_tokens", [])):
        where = "new_tokens[%d]" % i
        name = nt.get("name", "") if isinstance(nt, dict) else ""
        if not TOKEN.match(name):
            errors.append("%s: name %r is not a CSS custom property name like --status-new" % (where, name))
            continue
        if name in tokens:
            errors.append("%s: %s already exists in the design's tokens: use it, do not redefine it" % (where, name))
        if not nt.get("value"):
            errors.append("%s: %s has no value" % (where, name))
        if not str(nt.get("reason", "")).strip():
            errors.append("%s: %s has no reason: say why no existing token will do" % (where, name))
        new_tokens[name] = nt
    seen = set()
    for c in comps:
        n = c.get("name", "?") if isinstance(c, dict) else "?"
        w = "component %s" % n
        if not isinstance(c, dict) or not NAME.match(str(c.get("name", ""))):
            errors.append("component %r: name must be lower-case words joined by hyphens" % n)
            continue
        if n in seen:
            errors.append("%s: the name is used twice" % w)
        seen.add(n)
        if c.get("kind") not in KINDS:
            errors.append("%s: kind %r is not one of %s" % (w, c.get("kind"), ", ".join(KINDS)))
        states = c.get("states")
        if not isinstance(states, list) or "default" not in states:
            errors.append("%s: states must be a list that includes 'default'" % w)
            states = ["default"]
        for s in states:
            if s not in STATES:
                errors.append("%s: state %r is not one of %s" % (w, s, ", ".join(STATES)))
        fr = c.get("frame")
        if fr is not None:
            b = fr.get("box") if isinstance(fr, dict) else None
            if not (isinstance(b, list) and len(b) == 4 and all(isinstance(v, int) and not isinstance(v, bool) for v in b) and b[2] > 0 and b[3] > 0 and b[0] >= 0 and b[1] >= 0):
                errors.append("%s: frame.box must be [x, y, width, height], whole numbers, width and height above 0" % w)
        blocks = [("style", c.get("style"))] + [("state_style.%s" % k, v) for k, v in (c.get("state_style") or {}).items()]
        for k in (c.get("state_style") or {}):
            if k not in states:
                errors.append("%s: state_style has %r but states does not list it" % (w, k))
        if c.get("style") is None:
            errors.append("%s: style is missing (use {} for a component that adds no style of its own)" % w)
        for label, block in blocks:
            if not isinstance(block, dict):
                continue
            for key, val in block.items():
                if key not in STYLE_KEYS:
                    errors.append("%s: %s.%s is not a style key (%s)" % (w, label, key, ", ".join(STYLE_KEYS)))
                    continue
                for part in str(val).replace(",", " ").split():
                    low = part.lower()
                    if low in KEEP:
                        continue
                    if key == "font-weight" and part.isdigit() and 100 <= int(part) <= 900 and int(part) % 100 == 0:
                        continue                                    # a weight is a step on a scale, not a measurement that can drift
                    if key == "line-height" and re.fullmatch(r"\d(\.\d+)?", part):
                        continue                                    # a unitless ratio
                    if part.startswith("--"):
                        if part in tokens or part in new_tokens:
                            if part in new_tokens:
                                new_used.add(part)
                        else:
                            errors.append("%s: %s.%s uses %s, which is neither in the design's tokens nor declared under new_tokens" % (w, label, key, part))
                    elif LITERAL.search(part):
                        errors.append("%s: %s.%s is the literal %r where a token name is wanted: use a token, or add one under new_tokens with a reason" % (w, label, key, part))
                    else:
                        errors.append("%s: %s.%s has %r, which is neither a token name (--x) nor one of %s" % (w, label, key, part, ", ".join(sorted(KEEP))))
        gt = c.get("goes_to")
        if gt is not None:
            m = GOES_TO.match(gt) if isinstance(gt, str) else None
            if not m:
                errors.append("%s: goes_to %r is not a screen id, sheet:ID, overlay:ID, external: WHAT, none: WHY or unknown: WHAT IS NEEDED" % (w, gt))
            elif ids is not None and m.group("screen") and m.group("screen") not in ids["screen"]:
                errors.append("%s: goes_to %r is not a screen in the navigation map (screens: %s)" % (w, gt, ", ".join(sorted(ids["screen"]))))
            elif ids is not None and m.group("kind") and m.group("id") not in ids[m.group("kind")]:
                errors.append("%s: goes_to %r is not %s %s in the navigation map (%ss: %s)" % (w, gt, "an" if m.group("kind") == "overlay" else "a", m.group("kind"), m.group("kind"), ", ".join(sorted(ids[m.group("kind")])) or "none"))
            elif m and m.group("free") == "unknown":
                unknown_goes.append("%s (%s)" % (n, m.group("why").strip()))
        elif c.get("kind") in LEADS:
            if ids is not None:
                errors.append("%s: a %s must say where it leads (goes_to): a screen id from the navigation map, sheet:ID, overlay:ID, external: WHAT, none: WHY, or unknown: WHAT IS NEEDED" % (w, c.get("kind")))
            else:
                unknown_goes.append("%s (no goes_to)" % n)
        elif c.get("kind") == "button" and ids is not None:
            warnings.append("%s: a button with no goes_to: say where it leads, or none: what it does instead" % w)
        data = c.get("data")
        if not isinstance(data, dict):
            errors.append("%s: data is missing. Say where each slot's content comes from: STATIC, NONE or a field path (use {} for a component with no slots)" % w)
            continue
        for slot, src in data.items():
            for s in as_list(src):
                if s == "STATIC":
                    statics.append("%s.%s" % (n, slot))
                elif s == "NONE":
                    continue
                elif not isinstance(s, str) or not PATH.match(s):
                    errors.append("%s: data.%s = %r is not STATIC, NONE or a field path like CL.members[].uid" % (w, slot, s))
                elif paths is not None and not s.startswith(PREFIXES_WITHOUT_PRODUCER):
                    if s not in set(paths.get(s.split(".")[0].split("[")[0], [])):
                        errors.append("%s: data.%s = %s does not occur in anything the app reads: check the path against docs/SCREEN_DATA_MAP.md" % (w, slot, s))
    for name in new_tokens:
        if name not in new_used:
            warnings.append("new token %s is declared but no component uses it" % name)
    if paths is None:
        warnings.append("field paths were checked for their form only (no --paths file): that they exist was not checked")
    if navigation is None and any(isinstance(c, dict) and c.get("kind") in LEADS for c in comps):
        warnings.append("where a menu item, tab or link leads was checked for its form only (no --navigation file): that the screen exists was not checked")
    if unknown_goes:
        warnings.append("where these lead is not confirmed: " + ", ".join(unknown_goes))
    if statics:
        warnings.append("STATIC slots, to look at by eye (a slot that holds a number, a name or a status must not be static): " + ", ".join(statics))
    return {"format": "reqin-components-report/1", "components": len(comps), "errors": errors, "warnings": warnings, "new_tokens": sorted(new_tokens), "static_slots": statics,
            "paths_checked": paths is not None, "navigation_checked": navigation is not None, "ok": not errors}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--paths", metavar="FILE")
    ap.add_argument("--navigation", metavar="FILE", help="design/navigation.json: look up where each menu item, tab or link leads")
    ap.add_argument("--json", metavar="FILE", help="also write the report here")
    a = ap.parse_args(argv)
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    paths = None
    if a.paths:
        with open(a.paths, encoding="utf-8") as f:
            paths = json.load(f)
    nav = None
    if a.navigation:
        with open(a.navigation, encoding="utf-8") as f:
            nav = json.load(f)
    rep = check(spec, token_names(a.tokens), paths, nav)
    for e in rep["errors"]:
        print("ERROR  ", e)
    for w in rep["warnings"]:
        print("warning", w)
    print("%d components, %d errors, %d warnings: %s" % (rep["components"], len(rep["errors"]), len(rep["warnings"]), "OK" if rep["ok"] else "NOT OK"))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
            f.write("\n")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
