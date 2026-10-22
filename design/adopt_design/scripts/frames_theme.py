#!/usr/bin/env python3
"""Draw the frames of our screens in THE PERSON'S theme: the same pictures as make_frames.py, with the running prototype re-coloured, re-typed and re-cornered.

    python3 design/adopt_design/scripts/frames_theme.py SESSION [--screens a,b]        read the theme the session has decided (adopt.py's Model.theme_values()) and write
                                                                                      SESSION/pictures/frames/<screen>.png and SESSION/pictures/frames/frames_theme.json
    python3 design/adopt_design/scripts/frames_theme.py --theme FILE.json OUT_DIR [--screens a,b]
                                                                                      the same from a plain {"role": "value"} file (a role it does not name keeps ours)
    ... --dry-run                                                                      no browser: check the theme and say which roles differ from ours and which screens would be drawn

FILE.json looks like {"accent": "#0F766E", "radius-control": "20px", "font-body": "Inter, sans-serif"}; the roles and what each value looks like are in roles.json. A role that is not in
roles.json, or a value that is not a colour / a length in pixels / a plain font stack / a plain shadow, is refused before anything is drawn, with a message that says which.

What it draws: for each screen, the running prototype (made-up sample data, reached by the same clicks as make_frames.reach), re-themed in the page itself, then a full-page picture and the
box of every frame in frames_spec.json measured AFTER the re-theme (a bigger font makes a taller page, so boxes from frames.json would cut the wrong place). If the prototype no longer
matches frames_spec.json (make_frames.drift), drawing stops, names the frame, and writes nothing.

How the re-theme works (and why it is not just CSS variables). The prototype page mixes design tokens (var(--accent), about 250 uses) with hundreds of literal values in rules and inline
styles (the literal white about 290 times, a quiet grey about 150), so overriding :root custom properties alone would leave most of the page in our colours. remap_page(pg, ours, theirs)
does both, in this order, on the live page:
  1. READ: walk every visible element and read the computed value of each property a role can own. A value is "ours" when it equals a value of ours for a role that may own that property.
  2. TOKENS: write the person's value of every changed role over the tokens roles.json says the role drives (R.tokens_for), on :root, on any element whose style attribute declares the token
     (the prototype sets --accent on a wrapper, so :root alone would not reach it) and in any stylesheet rule that declares it. Things that are derived from a token, such as
     color-mix(in srgb, var(--accent) 10%, #fff), follow by themselves. This is the "followed" count in the report.
  3. APPLY: on every element that was read as ours, style.setProperty(property, theirs, 'important'). Reading happens BEFORE anything is written, so a value that became the person's can never
     be mistaken for one of ours (their accent that happens to equal our ink is not turned into their ink).
A role whose value equals ours is not touched at all, so drawing with theirs == ours changes nothing (tools/test_frames_theme.py compares every picture with docs/images/frames/ pixel by pixel).

Which role owns a value. A value of ours is every value roles.json names for the role in design/tokens.css (all four border tokens, all five quiet-text tokens ...), not only the first,
except a colour that a token outside every role also has (--surface-selected-2 and --info-fill are the same #E8F0FD, and the info colour is meaning, not theme: it is left alone). Exact
equality only; a near miss is a different colour (the explorer's "alone" grey is one digit away from the input outline and is a status colour, so it must stay).
  property                          roles it may belong to, in the order tried                      rule
  color                             ink, ink-muted, accent, accent-text                             accent-text only on an element whose effective background is our accent
                                                                                                   (nearest ancestor-or-self with a background that is at least half opaque). The same
                                                                                                   white is also our surface, but as a text colour it is accent-text or nothing: white on
                                                                                                   the dark band or on a green chip is left alone and reported.
  background-color                  accent, surface, hover, selected, page                          the page and the sheet behind it (body) try page first; everything else tries page last.
                                                                                                   White is surface, never accent-text. A background that is at least half opaque keeps its
                                                                                                   opacity ("rgba(255,255,255,.94)" is surface at .94); a fainter one is left alone.
  border-*-color                    border, border-control, accent, surface                         only a side that has a width and a style. surface catches the white ring that separates things.
  outline-color                     accent, border-control, border                                  only where an outline is drawn.
  fill, stroke (SVG)                accent, accent-text, ink, ink-muted, surface, border ...        accent-text only on our accent; the same white elsewhere is surface.
  font-family                       font-body, font-statement, font-mono                            by the first family of the stack ("Public Sans" is our body font).
  font-size                         size-body, size-small, size-title                               by value; size-title only on an h1 (a 30px figure that is not a page title keeps its size).
  border-*-radius                   radius-control, radius-panel, radius-chip                       by the ELEMENT first: button, input, select, textarea are controls and take radius-control
                                                                                                   when their corner is one of our control or chip corners (a 6px button is still a button);
                                                                                                   a control with one of our panel corners (a card that is a button) is a panel. Every other
                                                                                                   element is a chip when its corner is one of our chip corners (6px, 4px) and a panel when it is
                                                                                                   our panel corner (12px, 14px) or our control corner (8px on a div is a card, not a button).
                                                                                                   Pills (999px), circles (50%) and the 2px squares of the map are shape, not theme: left alone.
  min-height (controls only)        control-height                                                  our control height and the three sizes roles.json derives from it (+4, -4, -8) keep their
                                                                                                   distance from the person's value. height is not touched: it is the used height, not a choice.
  box-shadow                        shadow-card                                                     the whole shadow list, compared as the browser writes it. Our screens draw no shadow on a card
                                                                                                   at rest (only on hover), so this role usually changes nothing; the report says so.
When two roles of ours share a value and the rules above do not tell them apart, the role earlier in the list wins.

What it leaves alone, on purpose, and reports (report["unmapped"], grouped by property and value with a count and one example): colours that mean something (the green, amber and red of
the guards and status chips, the lens colours, the chart colours), the dark band, text on those, sizes that are not on the type ladder (12px captions, 15px, 16px ...), pills and circles,
and fonts the page never set. It does not scale those sizes with the person's body size, so a much bigger body next to 12px captions will look out of proportion: that is what the theme says,
not a promise of how the person's own screens will scale.

A dark theme shows a limit of the roles, not of this file: our screens also use pale greys that no role names (the quiet panel and label fills, the pale grey outlines of a quiet control),
so they stay pale on a dark page. When the page or surface is dark, the report gets a note with how many elements that is. Naming those greys in roles.json would fix it; this file
does not guess them (it matches by exact value only).

What it does not draw: hover, focus and pressed states, pseudo-elements (::before, ::after, ::placeholder), background images and gradients, anything behind a click the reach() steps do not
make, and fixed-height icon buttons (their height is a declared height, not a min-height). Fonts that are not installed on the machine that draws are shown in a stand-in (the next
installed family of the stack, else the browser's own sans-serif, serif or monospace) and the report says so.

Needs Playwright, Pillow and a Chromium (see prototype/h.py), but only to draw: importing this file needs the standard library only, so tools/test_frames_theme.py runs where nothing else is
installed. This file only reads the prototype and the kit and writes only into the folder it is given.
"""
from __future__ import annotations

import argparse
import colorsys
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import REPO, TOKENS_CSS, css_vars, digest, first_family, px, read_json, write_json  # noqa: E402
import make_frames as MF  # noqa: E402
import roles as R  # noqa: E402

FORMAT = "reqin-frames-theme/1"
INDEX_NAME = "frames_theme.json"
ALPHA_MIN = 0.5            # a colour fainter than this is an overlay or a tint, not a surface: it is left alone
GENERIC_FAMILIES = {"sans-serif", "serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "cursive", "fantasy", "math", "emoji", "fangsong"}
ROLE_GENERIC = {"font-body": "sans-serif", "font-statement": "serif", "font-mono": "monospace"}
FONT_ROLES = tuple(ROLE_GENERIC)

# ---------------------------------------------------------------------------------------------------------------- colours (pure)
_NAMED = """aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff beige f5f5dc bisque ffe4c4 black 000000 blanchedalmond ffebcd blue 0000ff blueviolet 8a2be2
brown a52a2a burlywood deb887 cadetblue 5f9ea0 chartreuse 7fff00 chocolate d2691e coral ff7f50 cornflowerblue 6495ed cornsilk fff8dc crimson dc143c cyan 00ffff darkblue 00008b
darkcyan 008b8b darkgoldenrod b8860b darkgray a9a9a9 darkgreen 006400 darkgrey a9a9a9 darkkhaki bdb76b darkmagenta 8b008b darkolivegreen 556b2f darkorange ff8c00 darkorchid 9932cc
darkred 8b0000 darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b darkslategray 2f4f4f darkslategrey 2f4f4f darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493
deepskyblue 00bfff dimgray 696969 dimgrey 696969 dodgerblue 1e90ff firebrick b22222 floralwhite fffaf0 forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc ghostwhite f8f8ff gold ffd700
goldenrod daa520 gray 808080 green 008000 greenyellow adff2f grey 808080 honeydew f0fff0 hotpink ff69b4 indianred cd5c5c indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa
lavenderblush fff0f5 lawngreen 7cfc00 lemonchiffon fffacd lightblue add8e6 lightcoral f08080 lightcyan e0ffff lightgoldenrodyellow fafad2 lightgray d3d3d3 lightgreen 90ee90
lightgrey d3d3d3 lightpink ffb6c1 lightsalmon ffa07a lightseagreen 20b2aa lightskyblue 87cefa lightslategray 778899 lightslategrey 778899 lightsteelblue b0c4de lightyellow ffffe0
lime 00ff00 limegreen 32cd32 linen faf0e6 magenta ff00ff maroon 800000 mediumaquamarine 66cdaa mediumblue 0000cd mediumorchid ba55d3 mediumpurple 9370db mediumseagreen 3cb371
mediumslateblue 7b68ee mediumspringgreen 00fa9a mediumturquoise 48d1cc mediumvioletred c71585 midnightblue 191970 mintcream f5fffa mistyrose ffe4e1 moccasin ffe4b5 navajowhite ffdead
navy 000080 oldlace fdf5e6 olive 808000 olivedrab 6b8e23 orange ffa500 orangered ff4500 orchid da70d6 palegoldenrod eee8aa palegreen 98fb98 paleturquoise afeeee palevioletred db7093
papayawhip ffefd5 peachpuff ffdab9 peru cd853f pink ffc0cb plum dda0dd powderblue b0e0e6 purple 800080 rebeccapurple 663399 red ff0000 rosybrown bc8f8f royalblue 4169e1
saddlebrown 8b4513 salmon fa8072 sandybrown f4a460 seagreen 2e8b57 seashell fff5ee sienna a0522d silver c0c0c0 skyblue 87ceeb slateblue 6a5acd slategray 708090 slategrey 708090
snow fffafa springgreen 00ff7f steelblue 4682b4 tan d2b48c teal 008080 thistle d8bfd8 tomato ff6347 turquoise 40e0d0 violet ee82ee wheat f5deb3 white ffffff whitesmoke f5f5f5
yellow ffff00 yellowgreen 9acd32"""
NAMED = {n: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for n, h in zip(_NAMED.split()[0::2], _NAMED.split()[1::2])}


def _byte(x: float) -> int:
    return max(0, min(255, int(x + 0.5)))


def _channel(tok: str, scale: float):
    """One channel of rgb(): a number of 0..255, or a percentage. None when it is neither."""
    m = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(%?)", tok)
    return None if not m else _byte(float(m.group(1)) * (2.55 if m.group(2) else 1.0) * scale)


def _alpha(tok):
    if tok is None:
        return 1.0
    m = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(%?)", tok)
    return None if not m else max(0.0, min(1.0, float(m.group(1)) / (100.0 if m.group(2) else 1.0)))


def parse_colour(text):
    """A CSS colour as (r, g, b, alpha) with r, g, b in 0..255 and alpha in 0..1, or None when it is not a colour this reads.
    Reads #rgb, #rgba, #rrggbb, #rrggbbaa, rgb()/rgba() (commas or spaces, a "/" alpha, percentages), hsl()/hsla(), color(srgb r g b / a), the 148 named colours and transparent."""
    if not isinstance(text, str):
        return None
    t = text.strip().lower()
    if t == "transparent":
        return (0, 0, 0, 0.0)
    if t in NAMED:
        return NAMED[t] + (1.0,)
    m = re.fullmatch(r"#([0-9a-f]{3,8})", t)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(ch * 2 for ch in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(a, 4))
    m = re.fullmatch(r"(rgba?|hsla?|color)\(\s*(.*?)\s*\)", t)
    if not m:
        return None
    fn, inner = m.group(1), m.group(2)
    parts = [p for p in re.split(r"\s*[,/]\s*|\s+", inner) if p]
    if fn == "color":                                    # color(srgb 0.91 0.93 0.97 / 0.5): channels are 0..1 (or percentages); the browser writes a color-mix() result this way
        if not parts or parts[0] != "srgb" or len(parts) not in (4, 5):
            return None
        ch = []
        for p in parts[1:4]:
            m = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(%?)", p)
            ch.append(None if not m else _byte(float(m.group(1)) * (2.55 if m.group(2) else 255.0)))
        al = _alpha(parts[4] if len(parts) == 5 else None)
        return None if None in ch or al is None else (ch[0], ch[1], ch[2], al)
    if len(parts) not in (3, 4):
        return None
    al = _alpha(parts[3] if len(parts) == 4 else None)
    if al is None:
        return None
    if fn.startswith("rgb"):
        ch = [_channel(p, 1.0) for p in parts[:3]]
        return None if None in ch else (ch[0], ch[1], ch[2], al)
    mh = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(deg)?", parts[0])
    ms, ml = (re.fullmatch(r"([0-9]*\.?[0-9]+)%", p) for p in parts[1:3])
    if not (mh and ms and ml):
        return None
    r, g, b = colorsys.hls_to_rgb((float(mh.group(1)) % 360) / 360.0, min(100.0, float(ml.group(1))) / 100.0, min(100.0, float(ms.group(1))) / 100.0)
    return (_byte(r * 255), _byte(g * 255), _byte(b * 255), al)


def norm_colour(text):
    """The colour as the browser writes a computed one: "rgb(26, 77, 181)", or "rgba(255, 255, 255, 0.94)" when it is not opaque. None when it is not a colour."""
    p = parse_colour(text)
    if p is None:
        return None
    r, g, b, a = p
    return "rgb(%d, %d, %d)" % (r, g, b) if a >= 0.9995 else "rgba(%d, %d, %d, %s)" % (r, g, b, ("%.3f" % a).rstrip("0").rstrip("."))


def hex_colour(text):
    p = parse_colour(text)
    return None if p is None or p[3] < 0.9995 else "#%02X%02X%02X" % p[:3]


def with_alpha(colour: str, alpha: float) -> str:
    """The colour (any form) with this opacity, as rgb()/rgba(); the colour's own opacity is multiplied in."""
    r, g, b, a = parse_colour(colour)
    return norm_colour("rgba(%d, %d, %d, %s)" % (r, g, b, repr(round(a * alpha, 4))))


# ---------------------------------------------------------------------------------------------------------------- values of the theme (pure)
PLAIN_BAD = re.compile(r"[;{}<>]|url\(|expression|@import|\\")


def check_value(role: str, raw) -> str:
    """A value for a role in the form it is written down in: a colour as #RRGGBB (or rgba() when it is not opaque), a length as 12px, a font stack or a shadow as plain CSS.
    ValueError with a message that names the role when it is none of those."""
    if role not in R.BY_ID:
        raise ValueError("%r is not a role. The roles are: %s" % (role, ", ".join(R.ROLE_IDS)))
    kind = R.BY_ID[role]["kind"]
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("%s: the value must be text, for example %s" % (role, {"colour": '"#1A4DB5"', "length": '"14px"', "font": '"Inter, sans-serif"', "shadow": '"none"'}[kind]))
    s = raw.strip()
    if PLAIN_BAD.search(s):
        raise ValueError("%s: %r is not a plain value (no ; { } < > url() or backslash)" % (role, s))
    if kind == "colour":
        p = parse_colour(s)
        if p is None:
            raise ValueError("%s: %r is not a colour. Write it as #RRGGBB" % (role, s))
        return hex_colour(s) or norm_colour(s)
    if kind == "length":
        n = px(s)
        if n is None or n < 0:
            raise ValueError("%s: %r is not a length. Write it in pixels, for example 14px" % (role, s))
        return ("%g" % round(n, 2)) + "px"
    if kind == "shadow":
        if s.lower() != "none" and not re.search(r"\d", s):
            raise ValueError("%s: %r is not a shadow. Write none, or for example 0 1px 3px rgba(0,0,0,.2)" % (role, s))
        return " ".join(s.split())
    if not re.search(r"[A-Za-z]", s):
        raise ValueError("%s: %r is not a font stack. Write a family name, for example Inter, sans-serif" % (role, s))
    return " ".join(s.split())


def flat_roles(values: dict) -> dict:
    """{role: value} from {role: value} or from adopt.py's {role: {"value": value, ...}}; roles with no value are left out."""
    out = {}
    for k, v in values.items():
        v = v.get("value") if isinstance(v, dict) else v
        if v is not None:
            out[k] = v
    return out


def default_ours() -> dict:
    return flat_roles(R.read_ours(TOKENS_CSS.read_text(encoding="utf-8")))


def complete_theme(theirs: dict, ours: dict) -> dict:
    """Every role's value for the picture: the person's (checked and written down in its usual form) and, for a role they do not name, ours."""
    for k in theirs:
        if k not in R.BY_ID:
            raise ValueError("%r is not a role. The roles are: %s" % (k, ", ".join(R.ROLE_IDS)))
    return {r: check_value(r, theirs[r] if theirs.get(r) is not None else ours[r]) for r in R.ROLE_IDS}


def same_value(role: str, a, b) -> bool:
    """Do these two values draw the same? Colours by their digits (opacity too), lengths by their pixels, fonts by their whole stack's first family, shadows by their text without spaces."""
    kind = R.BY_ID[role]["kind"]
    if kind == "colour":
        return parse_colour(a) is not None and parse_colour(a) == parse_colour(b)
    if kind == "length":
        return px(a) is not None and px(a) == px(b)
    if kind == "font":
        return first_family(a).lower() == first_family(b).lower()
    return re.sub(r"\s+", "", str(a)).lower() == re.sub(r"\s+", "", str(b)).lower()


def font_stack(role: str, value: str) -> str:
    """The stack the picture really sets: the person's, ended by a generic family so that a font this machine lacks falls back to a font of the same kind and not to the browser's serif."""
    fams = [f.strip().strip("\"'").lower() for f in value.split(",")]
    return value if any(f in GENERIC_FAMILIES for f in fams) else value + ", " + ROLE_GENERIC[role]


# ---------------------------------------------------------------------------------------------------------------- tables (pure)
SIZE_ROLES = ("size-body", "size-small", "size-title")
RADIUS_KINDS = {"control": "radius-control", "panel": "radius-panel", "chip": "radius-chip"}
COLOUR_ROLES = {
    "color": ("ink", "ink-muted", "accent", "accent-text"),
    "background-color": ("accent", "surface", "hover", "selected", "page"),
    "border-color": ("border", "border-control", "accent", "surface"),
    "outline-color": ("accent", "border-control", "border"),
    "fill": ("accent", "accent-text", "ink", "ink-muted", "surface", "hover", "selected", "border", "border-control", "page"),
    "stroke": ("accent", "accent-text", "ink", "ink-muted", "border", "border-control", "surface"),
}
ON_ACCENT_ONLY = ("accent-text",)
ROOT_FIRST = ("page",)


def family(prop: str) -> str:
    """The four sides of a border are one property for a person, and so are the four corners."""
    if re.fullmatch(r"border-(top|right|bottom|left)-color", prop):
        return "border-color"
    if re.fullmatch(r"border-(top|bottom)-(left|right)-radius", prop):
        return "border-radius"
    return prop


def _role_values(role: str, ours: dict, ours_vars: dict) -> list:
    """Every value of ours for a role: the one the caller gave first, then what design/tokens.css has for each token the role drives (and, for the control height, its derived sizes)."""
    r = R.BY_ID[role]
    vals = [ours[role]]
    for t in r["ours"]:
        if t in ours_vars:
            vals.append(ours_vars[t])
    return vals


def build_tables(ours: dict, theirs: dict, ours_vars: dict | None = None) -> dict:
    """Everything decide() needs, from plain dicts. ours and theirs map role -> value for every role (theirs may leave roles out: they keep ours). No browser.
    tables["changed"]  the roles whose value is not ours (only these are written); tables["target"] the value each is written as; tables["dropped"] colours a role names that are left alone
    because a token outside every role has the same value."""
    ours = flat_roles(ours)
    ours_vars = css_vars(TOKENS_CSS.read_text(encoding="utf-8")) if ours_vars is None else ours_vars
    theirs = {r: (theirs.get(r) if theirs.get(r) is not None else ours[r]) for r in R.ROLE_IDS}
    changed = [r for r in R.ROLE_IDS if not same_value(r, ours[r], theirs[r])]
    role_tokens = {t for r in R.ROLES["roles"] for t in list(r["ours"]) + list(r.get("derive", {}))}
    outside = {norm_colour(v) for t, v in ours_vars.items() if t not in role_tokens and norm_colour(v)}
    colour, dropped = {}, []
    for r in R.ROLE_IDS:
        if R.BY_ID[r]["kind"] != "colour":
            continue
        for i, v in enumerate(_role_values(r, ours, ours_vars)):
            n = parse_colour(v)
            if n is None or n[3] < ALPHA_MIN:
                continue
            if i > 0 and norm_colour(v) in outside and norm_colour(v) != norm_colour(ours[r]):
                dropped.append((r, norm_colour(v)))
                continue
            if r not in colour.setdefault(n[:3], []):
                colour[n[:3]].append(r)
    font = {}
    for r in FONT_ROLES:
        for v in _role_values(r, ours, ours_vars):
            font.setdefault(first_family(v).lower(), r)
    size = {}
    for r in SIZE_ROLES:
        for v in _role_values(r, ours, ours_vars):
            if px(v) is not None:
                size.setdefault(round(px(v), 2), r)
    radius = {k: {round(px(v), 2) for v in _role_values(r, ours, ours_vars) if px(v) is not None} for k, r in RADIUS_KINDS.items()}
    height = {}
    base = px(ours["control-height"])
    for t, d in [("--target-control", 0)] + list(R.BY_ID["control-height"].get("derive", {}).items()):
        height.setdefault(round(base + d, 2), d)
    target = {}
    for r in changed:
        kind = R.BY_ID[r]["kind"]
        if kind == "font":
            target[r] = font_stack(r, theirs[r])
        elif kind == "colour":
            target[r] = hex_colour(theirs[r]) or norm_colour(theirs[r])
        elif kind == "length":
            target[r] = ("%g" % round(px(theirs[r]), 2)) + "px"
        else:
            target[r] = " ".join(str(theirs[r]).split())
    accent_rgb = sorted({norm_colour("rgb(%d, %d, %d)" % k) for k, roles in colour.items() if "accent" in roles})
    return {"ours": ours, "theirs": theirs, "changed": changed, "target": target, "colour": colour, "font": font, "size": size, "radius": radius, "height": height,
            "shadow": " ".join(str(ours["shadow-card"]).split()).lower(), "accent_rgb": accent_rgb, "dropped": dropped}


class Decision(tuple):
    """(role, value, why): role is the role that owns the value (None when no role of ours does), value is what to write (None when the role is not changed) and why says,
    when a value is left alone although it looks like one of ours, what made it not a role's."""
    __slots__ = ()

    def __new__(cls, role=None, value=None, why=None):
        return tuple.__new__(cls, (role, value, why))

    role = property(lambda s: s[0])
    value = property(lambda s: s[1])
    why = property(lambda s: s[2])


def _write(tables: dict, role: str, value=None):
    return Decision(role, value if role in tables["changed"] else None)


def _decide_colour(fam: str, value: str, facts: dict, tables: dict) -> Decision:
    c = parse_colour(value)
    if c is None or c[3] < ALPHA_MIN:
        return Decision()
    roles = tables["colour"].get(c[:3], [])
    order = COLOUR_ROLES[fam]
    if fam == "background-color" and facts.get("root"):
        order = ROOT_FIRST + tuple(o for o in order if o not in ROOT_FIRST)
    why = None
    for role in order:
        if role not in roles:
            continue
        if role in ON_ACCENT_ONLY and not facts.get("on_accent"):
            why = "text on a background that is not our main action colour"
            continue
        target = tables["target"].get(role)
        return _write(tables, role, None if target is None else (target if c[3] >= 0.9995 else with_alpha(target, c[3])))
    return Decision(None, None, why)


def decide(prop: str, value: str, facts: dict, tables: dict) -> Decision:
    """Which role of ours owns this computed value on an element like this, and what it is to be written as. Pure: no browser.
    facts: {"control": button/input/select/textarea, "h1": a page title, "root": body or html, "on_accent": the element's effective background is our accent}."""
    fam = family(prop)
    if fam in COLOUR_ROLES:
        return _decide_colour(fam, value, facts, tables)
    if prop == "font-family":
        role = tables["font"].get(first_family(value).lower())
        return _write(tables, role, tables["target"].get(role)) if role else Decision()
    if prop == "font-size":
        n = px(value)
        role = tables["size"].get(round(n, 2)) if n is not None else None
        if role is None:
            return Decision()
        if role == "size-title" and not facts.get("h1"):
            return Decision(None, None, "the size of our page title on something that is not a page title")
        return _write(tables, role, tables["target"].get(role))
    if fam == "border-radius":
        n = px(value)
        if n is None or n <= 0:
            return Decision()
        n, rad, ctl = round(n, 2), tables["radius"], facts.get("control")
        if ctl:
            role = "radius-control" if n in rad["control"] or n in rad["chip"] else "radius-panel" if n in rad["panel"] else None
        else:
            role = "radius-chip" if n in rad["chip"] else "radius-panel" if (n in rad["panel"] or n in rad["control"]) else None
        return _write(tables, role, tables["target"].get(role)) if role else Decision()
    if prop == "min-height":
        n = px(value)
        if not facts.get("control") or n is None or round(n, 2) not in tables["height"]:
            return Decision()
        d = tables["height"][round(n, 2)]
        return _write(tables, "control-height", ("%g" % round(px(tables["theirs"]["control-height"]) + d, 2)) + "px")
    if prop == "box-shadow":
        if " ".join(str(value).split()).lower() == tables.get("shadow_computed", tables["shadow"]):
            return _write(tables, "shadow-card", tables["target"].get("shadow-card"))
        return Decision()
    return Decision()


# ---------------------------------------------------------------------------------------------------------------- the report (pure)
def is_noise(fam: str, value: str) -> bool:
    """Values that are not a choice and would only make the report long: no colour at all, no shadow, no rounding."""
    v = str(value).strip().lower()
    if fam in COLOUR_ROLES:
        c = parse_colour(v)
        return c is None and v in ("none", "") or (c is not None and c[3] == 0)
    if fam == "box-shadow":
        return v in ("none", "")
    if fam == "border-radius":
        return px(v) == 0
    return False


def light_neutral(value) -> bool:
    """A pale grey (every channel 215 or more, no more than 12 apart): the quiet panel and label fills of our screens, which no role names."""
    c = parse_colour(value)
    return c is not None and c[3] >= 0.9995 and min(c[:3]) >= 215 and max(c[:3]) - min(c[:3]) <= 12


def dark_theme_note(unmapped: list, theirs: dict):
    """When the person's page or surface is dark: how many elements are drawn on pale greys that stay pale (nothing names them), as a sentence for the report; None when it does not apply."""
    dark = [r for r in ("page", "surface") if parse_colour(theirs.get(r)) is not None and _luminance(theirs[r]) < 0.2]
    n = sum(u["count"] for u in unmapped if u["property"] == "background-color" and light_neutral(u["value"]))
    if not dark or not n:
        return None
    return ("%d element(s) are drawn on pale greys that no role names (our quiet panel and label fills), so they stay pale on this dark %s; text on them may be hard to read"
            % (n, " and ".join({"page": "page", "surface": "surface"}[r] for r in dark)))


def _luminance(value) -> float:
    """Relative luminance (WCAG) of an opaque colour."""
    def lin(x):
        x /= 255.0
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = parse_colour(value)[:3]
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def group_unmapped(cases: list) -> list:
    """The short list for the person: [{"property", "value", "count", "example"}] by property and value (the four sides of a border are one property, and so are the four corners),
    most used first. cases are {"prop", "value", "n_own", "example", "why"}; n_own counts the elements that have the value of their own, not by inheriting it. count is a number of
    elements: for a border or a corner it is the most any one side has (an element with the same colour on four sides is one element). A value that is no choice (transparent, no shadow,
    square corners) is left out."""
    groups: dict = {}
    for c in cases:
        fam = family(c["prop"])
        if c.get("n_own", 0) <= 0 or is_noise(fam, c["value"]):
            continue
        value = (norm_colour(c["value"]) or c["value"]) if fam in COLOUR_ROLES else " ".join(str(c["value"]).split())
        g = groups.setdefault((fam, value), {"property": fam, "value": value, "count": 0, "example": c.get("example", ""), "_sides": {}})
        g["_sides"][c["prop"]] = g["_sides"].get(c["prop"], 0) + c["n_own"]
        if c.get("why") and "why" not in g:
            g["why"] = c["why"]
    for g in groups.values():
        g["count"] = max(g.pop("_sides").values())
    return sorted(groups.values(), key=lambda g: (-g["count"], g["property"], g["value"]))


# ---------------------------------------------------------------------------------------------------------------- in the page
COLLECT_JS = r"""(cfg) => {
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE', 'HEAD', 'META', 'LINK', 'TITLE']);
  const CTL = new Set(['BUTTON', 'INPUT', 'SELECT', 'TEXTAREA']);
  const accent = new Set(cfg.accent);
  const els = [...document.querySelectorAll('body, body *')].filter(e => !SKIP.has(e.tagName));
  const sty = new Map();
  const cs = e => { let c = sty.get(e); if (!c) { c = getComputedStyle(e); sty.set(e, c); } return c; };
  const alphaOf = s => {
    s = (s || '').trim();
    if (s === 'transparent') return 0;
    let m = s.match(/^rgba\(\s*[^,]+,[^,]+,[^,]+,\s*([0-9.]+)\s*\)$/);
    if (m) return parseFloat(m[1]);
    m = s.match(/^(?:rgb|color)\(.*\/\s*([0-9.]+%?)\s*\)$/);
    if (m) return m[1].endsWith('%') ? parseFloat(m[1]) / 100 : parseFloat(m[1]);
    return 1;
  };
  const eff = new Map();
  const effBg = e => {
    if (eff.has(e)) return eff.get(e);
    const b = cs(e).backgroundColor;
    const v = alphaOf(b) >= 0.5 ? b : (e.parentElement ? effBg(e.parentElement) : null);
    eff.set(e, v);
    return v;
  };
  const ownText = e => { for (const n of e.childNodes) if (n.nodeType === 3 && n.nodeValue.trim()) return true; return false; };
  const label = e => {
    let s = e.tagName.toLowerCase();
    if (e.id) s += '#' + e.id;
    if (typeof e.className === 'string' && e.className.trim()) s += '.' + e.className.trim().split(/\s+/).slice(0, 2).join('.');
    const t = [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue).join(' ').trim().replace(/\s+/g, ' ');
    return t ? s + ' "' + t.slice(0, 28) + '"' : s;
  };
  const cases = new Map(), list = [];
  const SIDES = ['top', 'right', 'bottom', 'left'], CORNERS = ['top-left', 'top-right', 'bottom-right', 'bottom-left'];
  els.forEach((e, i) => {
    const c = cs(e);
    if (c.display === 'none') return;
    const tag = e.tagName.toLowerCase(), svg = e instanceof SVGElement, par = e.parentElement ? cs(e.parentElement) : null;
    const textual = ownText(e) || CTL.has(e.tagName) || tag === 'svg';
    const facts = {control: CTL.has(e.tagName), h1: tag === 'h1', root: tag === 'body' || tag === 'html', on_accent: accent.has(effBg(e)), tag: tag};
    const add = (prop, value, inherited, reportable) => {
      if (!value) return;
      const key = [prop, value, facts.control ? 1 : 0, facts.h1 ? 1 : 0, facts.root ? 1 : 0, facts.on_accent ? 1 : 0].join('|');
      let k = cases.get(key);
      if (!k) { k = {key: key, prop: prop, value: value, control: facts.control, h1: facts.h1, root: facts.root, on_accent: facts.on_accent, tag: tag, n: 0, n_own: 0, example: '', idx: []}; cases.set(key, k); list.push(k); }
      k.n++; k.idx.push(i);
      const own = reportable && !(inherited && par && par.getPropertyValue(prop) === value);
      if (own) { k.n_own++; if (!k.example) k.example = label(e); }
    };
    const clear = v => v === 'rgba(0, 0, 0, 0)' || v === 'transparent';
    if (!clear(c.color)) add('color', c.color, true, textual);
    if (!clear(c.backgroundColor)) add('background-color', c.backgroundColor, false, true);
    for (const s of SIDES) {
      if (parseFloat(c.getPropertyValue('border-' + s + '-width')) > 0 && !['none', 'hidden'].includes(c.getPropertyValue('border-' + s + '-style')) && !clear(c.getPropertyValue('border-' + s + '-color')))
        add('border-' + s + '-color', c.getPropertyValue('border-' + s + '-color'), false, true);
    }
    if (c.outlineStyle !== 'none' && parseFloat(c.outlineWidth) > 0 && !clear(c.outlineColor)) add('outline-color', c.outlineColor, false, true);
    if (svg) {
      if (c.fill !== 'none' && !clear(c.fill)) add('fill', c.fill, true, true);
      if (c.stroke !== 'none' && !clear(c.stroke)) add('stroke', c.stroke, true, true);
    }
    add('font-family', c.fontFamily, true, textual);
    add('font-size', c.fontSize, true, textual);
    for (const k of CORNERS) { const v = c.getPropertyValue('border-' + k + '-radius'); if (v !== '0px') add('border-' + k + '-radius', v, false, true); }
    if (c.boxShadow !== 'none') add('box-shadow', c.boxShadow, false, true);
    if (facts.control && /^[0-9.]+px$/.test(c.minHeight)) add('min-height', c.minHeight, false, true);
  });
  window.__frames_theme = {els: els, cases: new Map(list.map(k => [k.key, k]))};
  return list.map(k => ({key: k.key, prop: k.prop, value: k.value, control: k.control, h1: k.h1, root: k.root, on_accent: k.on_accent, tag: k.tag, n: k.n, n_own: k.n_own, example: k.example}));
}"""

APPLY_JS = r"""(plan) => {
  const S = window.__frames_theme, out = {changed: {}, rejected: [], followed: {}, followed_own: {}, rules: 0};
  if (!S) return out;
  const root = document.documentElement;
  const rules = (list, fn) => { for (const r of list || []) { if (r.style) fn(r); if (r.cssRules) rules(r.cssRules, fn); } };
  for (const t of Object.keys(plan.tokens)) {
    const v = plan.tokens[t];
    root.style.setProperty(t, v, 'important');
    for (const e of document.querySelectorAll('[style*="' + t + '"]')) { if (e.style.getPropertyValue(t)) e.style.setProperty(t, v, 'important'); }
    for (const sh of document.styleSheets) {
      let list = null;
      try { list = sh.cssRules; } catch (x) { continue; }
      rules(list, r => { if (r.style.getPropertyValue(t)) { r.style.setProperty(t, v, 'important'); out.rules++; } });
    }
  }
  const seen = {};
  for (const d of plan.decisions) {
    const k = S.cases.get(d.key);
    if (!k) continue;
    if (!CSS.supports(d.prop, d.value)) { out.rejected.push({property: d.prop, value: d.value}); continue; }     // a value the browser does not take would leave the old one in place
    for (const i of k.idx) {
      const e = S.els[i];
      e.style.setProperty(d.prop, d.value, 'important');
      (seen[d.role] || (seen[d.role] = new Set())).add(i);
    }
  }
  for (const r of Object.keys(seen)) out.changed[r] = seen[r].size;
  if (Object.keys(plan.tokens).length || plan.decisions.length) {
    const mapped = new Set(plan.mapped);
    for (const k of S.cases.values()) {
      if (mapped.has(k.key)) continue;
      let moved = 0, own = 0;
      k.idx.forEach((i, j) => { if (getComputedStyle(S.els[i]).getPropertyValue(k.prop) !== k.value) moved++; });
      if (moved) {
        own = Math.round(k.n_own * moved / k.n);
        out.followed[k.prop] = (out.followed[k.prop] || 0) + moved;
        out.followed_own[k.key] = own;
      }
    }
  }
  delete window.__frames_theme;
  return out;
}"""

CANON_SHADOW_JS = r"""(v) => { const e = document.createElement('div'); e.style.boxShadow = v; document.body.appendChild(e); const s = getComputedStyle(e).boxShadow; e.remove(); return s; }"""


def installed_fonts(pg, families: list) -> dict:
    """{family: is it installed here} by the same probe render.py uses (a font counts as installed when text in it measures differently from the generic fonts)."""
    import render as RD
    fams = sorted({f for f in families if f and f.lower() not in GENERIC_FAMILIES})
    return pg.evaluate(RD.FONT_PROBE, fams) if fams else {}


def font_report(pg, tables: dict) -> dict:
    """For each font role the person changed: what they asked for, what this machine draws it with, and whether that is a stand-in."""
    asked = {r: tables["theirs"][r] for r in FONT_ROLES if r in tables["changed"]}
    fams = {r: [f.strip().strip("\"'") for f in v.split(",")] for r, v in asked.items()}
    have = installed_fonts(pg, [f for fl in fams.values() for f in fl]) if asked else {}
    out = {}
    for r, fl in fams.items():
        first_ok = fl[0].lower() in GENERIC_FAMILIES or have.get(fl[0], False)
        drawn = next((f for f in fl if f.lower() in GENERIC_FAMILIES or have.get(f, False)), ROLE_GENERIC[r])
        out[r] = {"asked": asked[r], "drawn_with": drawn, "stand_in": not first_ok}
    return out


def remap_page(pg, ours: dict, theirs: dict, ours_vars: dict | None = None) -> dict:
    """Re-theme the running page in place (after reach() and tall()). ours and theirs map role -> value (or role -> {"value": value}); a role theirs leaves out keeps ours.
    Returns {"changed": {role: elements}, "unmapped": [{"property", "value", "count", "example"}], "followed": {property: elements}, "font": {role: {"asked", "drawn_with", "stand_in"}},
    "tokens": {token: value}, "notes": [...]}. See the top of this file for what is read, what is written and what is left alone."""
    ours_vars = css_vars(TOKENS_CSS.read_text(encoding="utf-8")) if ours_vars is None else ours_vars
    ours = flat_roles(ours)
    theirs = complete_theme(flat_roles(theirs), ours)
    tables = build_tables(ours, theirs, ours_vars)
    tables["shadow_computed"] = " ".join(pg.evaluate(CANON_SHADOW_JS, tables["ours"]["shadow-card"]).split()).lower()
    cases = pg.evaluate(COLLECT_JS, {"accent": tables["accent_rgb"]})
    decisions, mapped, left = [], [], []
    for c in cases:
        d = decide(c["prop"], c["value"], c, tables)
        if d.role:
            mapped.append(c["key"])
            if d.value is not None:
                decisions.append({"key": c["key"], "prop": c["prop"], "value": d.value, "role": d.role})
        else:
            left.append({**c, "why": d.why})
    fonts = font_report(pg, tables)
    tokens = R.tokens_for(dict(tables["target"]), ours_vars)
    res = pg.evaluate(APPLY_JS, {"tokens": tokens, "decisions": decisions, "mapped": mapped})
    for c in left:
        c["n_own"] = max(0, c["n_own"] - res["followed_own"].get(c["key"], 0))
    changed = {r: res["changed"].get(r, 0) for r in tables["changed"]}
    notes = []
    for r in tables["changed"]:
        if not changed[r] and r not in FONT_ROLES:
            notes.append("%s is different from ours, but nothing on this screen is drawn with our value, so the picture shows no change for it" % R.BY_ID[r]["label"].lower())
    for r, f in fonts.items():
        if f["stand_in"]:
            notes.append("this machine has no %s, so the picture draws the %s in %s; the real result will use the font" % (first_family(f["asked"]), R.BY_ID[r]["label"].lower(), f["drawn_with"]))
    if res["rejected"]:
        notes.append("the browser refused %d value(s), which stay as drawn: %s" % (len(res["rejected"]), "; ".join("%s: %s" % (x["property"], x["value"]) for x in res["rejected"][:5])))
    unmapped = group_unmapped(left)
    grey = dark_theme_note(unmapped, theirs)
    if grey:
        notes.append(grey)
    return {"changed": changed, "unmapped": unmapped, "followed": res["followed"], "font": fonts, "tokens": tokens, "notes": notes, "rejected": res["rejected"]}


# ---------------------------------------------------------------------------------------------------------------- drawing
def _frames_out(spec_frames: list, found: list) -> list:
    return [{"id": f["id"], "label": f["label"], "rows": f["rows"], "box": None if g is None else {k: round(g[k]) for k in ("x", "y", "w", "h")}} for f, g in zip(spec_frames, found)]


def draw_themed(theirs: dict, out_dir, screens=None, ours: dict | None = None, spec: dict | None = None) -> dict:
    """Draw our screens in the person's theme into out_dir: <screen>.png for each screen and frames_theme.json. theirs is role -> value (a role it leaves out keeps ours), screens a list of
    screen ids (default: every screen in frames_spec.json), ours defaults to the values in design/tokens.css, spec to frames_spec.json.
    Returns {"ok", "problems", "out_dir", "files", "index"}. Nothing is written unless ok. Not ok means the prototype no longer matches frames_spec.json (the frame and what it found are named),
    the page reported errors, or a screen is not one we have; ValueError means the theme is not valid."""
    ours = default_ours() if ours is None else flat_roles(ours)
    theirs = complete_theme(flat_roles(theirs), ours)
    spec = spec if spec is not None else MF.load_spec()
    out = Path(out_dir)
    ids = list(spec["screens"]) if not screens else list(screens)
    unknown = [s for s in ids if s not in spec["screens"]]
    if unknown:
        return {"ok": False, "problems": ["no frames for screen %s in frames_spec.json (the screens are: %s)" % (", ".join(map(repr, unknown)), ", ".join(spec["screens"]))], "out_dir": str(out), "files": [], "index": None}
    problems = MF.spec_problems(spec)
    if problems:
        return {"ok": False, "problems": ["frames_spec.json does not agree with the screens and the data map: " + p for p in problems], "out_dir": str(out), "files": [], "index": None}
    sys.path.insert(0, str(REPO / "prototype"))
    from h import session  # noqa: E402

    index = {"format": FORMAT, "prototype_page": MF.page_hash(), "theme": digest(theirs), "viewport_width": MF.WIDTH, "box_units": MF.SCALE_NOTE, "screens": {}}
    with tempfile.TemporaryDirectory() as scratch, session(MF.WIDTH, 900) as (pg, errs):
        first = True
        for sid in ids:
            frames = spec["screens"][sid]
            if not first:
                MF.fresh(pg)
            first = False
            MF.reach(pg, sid)
            MF.tall(pg)
            bad = MF.drift(sid, frames, MF.find_frames(pg, frames))
            if bad:
                return {"ok": False, "problems": ["the prototype no longer matches frames_spec.json; nothing was written: " + b for b in bad], "out_dir": str(out), "files": [], "index": None}
            report = remap_page(pg, ours, theirs)
            pg.evaluate("document.fonts.ready.then(() => true)")
            MF.settle(pg, 250)
            height = MF.tall(pg)
            found = MF.find_frames(pg, frames)                              # measured again: the re-theme moved things
            bad = MF.drift(sid, frames, found)
            if bad:
                return {"ok": False, "problems": ["after the theme was applied the frames moved to other text; nothing was written: " + b for b in bad], "out_dir": str(out), "files": [], "index": None}
            png = Path(scratch) / (sid + ".png")
            pg.screenshot(path=str(png), full_page=True)
            MF._shrink(png)
            index["screens"][sid] = {"image": sid + ".png", "width": MF.WIDTH, "height": height, "frames": _frames_out(frames, found), "report": report}
        real = [e for e in errs if "ERR_FAILED" not in e]
        if real:
            return {"ok": False, "problems": ["the page reported problems while it was drawn (nothing was written): " + e for e in real[:10]], "out_dir": str(out), "files": [], "index": None}
        out.mkdir(parents=True, exist_ok=True)
        index = _merge_previous(out, index, list(spec["screens"]))
        for sid in index["screens"]:
            if (Path(scratch) / (sid + ".png")).is_file():
                shutil.copyfile(Path(scratch) / (sid + ".png"), out / (sid + ".png"))
    write_json(out / INDEX_NAME, index)
    return {"ok": True, "problems": [], "out_dir": str(out), "files": [str(out / (s + ".png")) for s in ids] + [str(out / INDEX_NAME)], "index": index}


def _merge_previous(out: Path, index: dict, order: list) -> dict:
    """Drawing some screens into a folder that already holds pictures of the same theme and page keeps the others; pictures of another theme or page are removed, so the index never
    names a picture that was drawn differently."""
    old = out / INDEX_NAME
    if not old.is_file():
        return index
    try:
        prev = read_json(old)
    except ValueError:
        prev = {"screens": {}}
    keep = prev.get("theme") == index["theme"] and prev.get("prototype_page") == index["prototype_page"] and prev.get("format") == FORMAT
    for sid, s in (prev.get("screens") or {}).items():
        if keep and sid not in index["screens"] and (out / s.get("image", "")).is_file():
            index["screens"][sid] = s
        elif not keep and sid not in index["screens"]:
            (out / s.get("image", "x.png")).unlink(missing_ok=True)
    index["screens"] = {k: index["screens"][k] for k in sorted(index["screens"], key=lambda k: order.index(k) if k in order else len(order))}
    return index


# ---------------------------------------------------------------------------------------------------------------- the command line
def colours_shown(session_dir, theirs: dict, ours: dict | None = None) -> str:
    """Which colours a person was shown our screens in, for the words in PREVIEW.md and REPORT.md. "yours": SESSION/pictures/frames/frames_theme.json says pictures were drawn for exactly this
    theme and exactly this version of the prototype. "ours-chosen": their theme is ours, so the pictures in docs/images/frames/ are already in it. "ours": their theme differs from ours and
    no picture in it was drawn, so what they saw was ours."""
    ours = default_ours() if ours is None else flat_roles(ours)
    try:
        theirs = complete_theme(flat_roles(theirs), ours)
    except ValueError:
        return "ours"
    if all(same_value(r, ours[r], theirs[r]) for r in R.ROLE_IDS):
        return "ours-chosen"
    f = Path(session_dir) / "pictures" / "frames" / INDEX_NAME
    if not f.is_file():
        return "ours"
    try:
        idx = read_json(f)
    except ValueError:
        return "ours"
    ok = idx.get("format") == FORMAT and idx.get("theme") == digest(theirs) and idx.get("prototype_page") == MF.page_hash() and bool(idx.get("screens"))
    return "yours" if ok else "ours"


def screens_sentence(shown: str) -> str:
    """The one sentence that says what the person saw of our screens, in the words both PREVIEW.md and REPORT.md use."""
    return {"yours": "you saw our frames drawn in your theme (your colours, fonts and corners as decided) with made-up content; they were not drawn on your data",
            "ours-chosen": "you saw our frames in our colours, which are the colours you chose, with made-up content; they were not drawn on your data",
            "ours": "you saw our frames in our colours with made-up content; they were not drawn in your theme or on your data"}[shown]


def load_theme_file(path: str) -> dict:
    """The {role: value} in a theme file, checked. ValueError (one clear message) when it is not a JSON object, names a role that does not exist, or holds a value that is not one of its kind."""
    p = Path(path)
    if not p.is_file():
        raise ValueError("no theme file here: %s" % path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError("%s is not JSON: %s" % (path, e))
    if not isinstance(data, dict):
        raise ValueError('%s must hold one JSON object that maps roles to values, for example {"accent": "#0F766E"}' % path)
    return {k: check_value(k, v) for k, v in data.items()}


def load_session_theme(session: str) -> tuple:
    """(theirs, ours) for an adoption session folder, the way adopt.py reads it: Model.theme_values() and Model.ours_value()."""
    d = Path(session)
    if not (d / "session.json").is_file():
        raise ValueError("no session here: %s (start one with adopt.py init)" % session)
    if not (d / "mine" / "index.json").is_file():
        raise ValueError("%s has no mine/index.json: the session was not started with adopt.py init" % session)
    import adopt
    s, m = adopt.model_of(session)
    return m.theme_values(), {r: m.ours_value(r) for r in R.ROLE_IDS}


def summary_lines(result: dict) -> list:
    lines = []
    for sid, s in result["index"]["screens"].items():
        rep = s["report"]
        ch = ", ".join("%s %d" % (r, n) for r, n in rep["changed"].items() if n) or "nothing changed"
        lines.append("%-9s %dx%d  re-themed: %s" % (sid, s["width"], s["height"], ch))
        for n in rep["notes"]:
            lines.append("          note: " + n)
        meaning = [u for u in rep["unmapped"] if u["property"] in ("color", "background-color", "border-color")][:4]
        if meaning:
            lines.append("          left as drawn (meaning, not theme): " + "; ".join("%s %s x%d" % (u["property"], u["value"], u["count"]) for u in meaning))
    return lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Draw the frames of our screens in the person's theme.", epilog=__doc__.split("\n\n")[0])
    ap.add_argument("path", help="an adoption session folder (pictures go to SESSION/pictures/frames/), or with --theme the folder to write into")
    ap.add_argument("--theme", metavar="FILE.json", help="a plain {role: value} file instead of a session")
    ap.add_argument("--screens", help="comma-separated screen ids (default: every screen in frames_spec.json)")
    ap.add_argument("--dry-run", action="store_true", help="no browser: check the theme and say what would be drawn")
    a = ap.parse_args(argv)
    try:
        if a.theme:
            theirs, ours, out = load_theme_file(a.theme), default_ours(), Path(a.path)
        else:
            theirs, ours = load_session_theme(a.path)
            out = Path(a.path) / "pictures" / "frames"
        theirs = complete_theme(theirs, ours)
        spec = MF.load_spec()
        ids = [s.strip() for s in a.screens.split(",") if s.strip()] if a.screens else list(spec["screens"])
        bad = [s for s in ids if s not in spec["screens"]]
        if bad:
            raise ValueError("no screen %s in frames_spec.json (the screens are: %s)" % (", ".join(map(repr, bad)), ", ".join(spec["screens"])))
    except ValueError as e:
        print("not drawn: %s" % e, file=sys.stderr)
        return 2
    diff = [r for r in R.ROLE_IDS if not same_value(r, ours[r], theirs[r])]
    if a.dry_run:
        print("theme ok. %d of %d roles differ from ours: %s" % (len(diff), len(R.ROLE_IDS), ", ".join(diff) or "none (the pictures would be ours)"))
        print("would draw %d screen(s) into %s: %s" % (len(ids), out, ", ".join(ids)))
        return 0
    res = draw_themed(theirs, out, ids, ours, spec)
    if not res["ok"]:
        print("not drawn:\n  " + "\n  ".join(res["problems"]), file=sys.stderr)
        return 1
    print("wrote %d pictures and %s into %s" % (len(ids), INDEX_NAME, out))
    print("\n".join(summary_lines(res)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
