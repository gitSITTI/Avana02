"""Name what a design says in the shared vocabulary (roles.json), for our design and for the page being adopted into.

    read_ours(css_text)  every role's value in this product's design/tokens.css, exactly as written there
    read_mine(index)     every role's value in the page that was indexed (index_page.py), with how it was read and how sure that is

Each role in the result is {"value": ..., "how": "...", "confidence": "read" | "guess" | "missing"}.
  read     taken from the computed style of the element that plays that part (the main button's own background, the body's own text colour)
  guess    worked out from counts or from a neighbouring role; the person is asked to confirm it
  missing  the page has nothing that plays that part; the result will use ours unless the person says a value (adopt.py set)

Nothing here looks at a picture. The numbers are what the browser computed. What it cannot know: which element the designer meant as the "main" button when a page
has several, and anything that only shows after a click or a sign-in.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import C, KIT, css_vars, first_family, fmt_px, px, read_json  # noqa: E402

ROLES = read_json(KIT / "roles.json")
ROLE_IDS = [r["id"] for r in ROLES["roles"]]
BY_ID = {r["id"]: r for r in ROLES["roles"]}
AREA_OF = {r["id"]: r["area"] for r in ROLES["roles"]}


def _hex(css: str | None, opaque_only: bool = True):
    """A computed colour as #RRGGBB, or None (transparent, partly see-through when opaque_only, or not a colour this reads)."""
    p = C.parse_css(css or "")
    if not p or (opaque_only and p[1] < 0.99):
        return None
    return p[0]


def _role(value, how, confidence):
    return {"value": value, "how": how, "confidence": confidence}


MISSING = lambda why: _role(None, why, "missing")  # noqa: E731


def read_ours(css_text: str) -> dict:
    """Our design's value for every role: the first token the role drives."""
    v = css_vars(css_text)
    out = {}
    for r in ROLES["roles"]:
        tok = r["ours"][0]
        out[r["id"]] = _role(v[tok], "design/tokens.css %s" % tok, "read") if tok in v else MISSING("no %s in the tokens" % tok)
    return out


def _comps(ix: dict, kind: str) -> list:
    return sorted((c for c in ix.get("components", []) if c.get("kind") == kind and not c.get("style", {}).get("disabled")), key=lambda c: -c.get("count", 0))


def _bg(c):
    return _hex((c.get("style") or {}).get("backgroundColor"))


def read_mine(ix: dict) -> dict:
    body = ix.get("body") or {}
    out: dict = {}
    page = _hex(body.get("backgroundColor")) or _hex(body.get("htmlBackground"))
    if page:
        out["page"] = _role(page, "the page's own background", "read")
    else:
        page = "#FFFFFF"
        out["page"] = _role(page, "the page sets no background, so the browser draws white", "read")

    ink = _hex(body.get("color"))
    out["ink"] = _role(ink, "the text colour of the page body", "read") if ink else MISSING("the body has no readable text colour")

    # the main action colour: the filled button with a colour (not a grey) that the page uses most; else the most used filled button; else links
    buttons = _comps(ix, "button")
    filled = [c for c in buttons if _bg(c) and _bg(c) != page]
    coloured = [c for c in filled if not C.is_neutral(_bg(c))]
    main_button = None
    if coloured:
        main_button = coloured[0]
        out["accent"] = _role(_bg(main_button), "the background of the main button (%r, %d on the page)" % (main_button.get("text", "")[:24], main_button.get("count", 0)), "read")
    elif filled:
        main_button = max(filled, key=lambda c: (c.get("count", 0), C.contrast(_bg(c), page)))
        out["accent"] = _role(_bg(main_button), "the most used filled button, which is grey or black: there is no coloured button", "guess")
    else:
        links = [c for c in _comps(ix, "link") if _hex(c["style"].get("color")) and not C.is_neutral(_hex(c["style"]["color"]))]
        cols = [c for c in ix.get("colours", []) if not C.is_neutral(c["hex"]) and c["hex"] != page]
        if links:
            out["accent"] = _role(_hex(links[0]["style"]["color"]), "the colour of links: the page has no filled button", "guess")
        elif cols:
            out["accent"] = _role(cols[0]["hex"], "the most used colour that is not a grey: the page has no filled button and no coloured link", "guess")
        else:
            out["accent"] = MISSING("the page uses no colour that is not a grey")
    if main_button is not None and _hex(main_button["style"].get("color")):
        out["accent-text"] = _role(_hex(main_button["style"]["color"]), "the text colour of that button", "read")
    elif out["accent"]["value"]:
        a = out["accent"]["value"]
        out["accent-text"] = _role("#FFFFFF" if C.contrast(a, "#FFFFFF") >= C.contrast(a, "#000000") else "#000000", "white or black, whichever reads better on the main colour", "guess")
    else:
        out["accent-text"] = MISSING("no main colour to put text on")

    cards = [c for c in _comps(ix, "card") if _bg(c)]
    if cards:
        out["surface"] = _role(_bg(cards[0]), "the background of the commonest card", "read")
    else:
        others = [c for c in ix.get("colours", []) if c["uses"].get("background", 0) > 0 and c["hex"] != page]
        out["surface"] = _role(others[0]["hex"], "the most used background that is not the page's", "guess") if others else _role(page, "no card or panel looks different from the page", "guess")

    muted = [c for c in ix.get("colours", []) if c["uses"].get("text", 0) > 0 and c["hex"] not in (ink, out["accent"]["value"], out["accent-text"]["value"], page) and C.contrast(c["hex"], page) >= 3.0]
    muted.sort(key=lambda c: -c["uses"]["text"])
    out["ink-muted"] = _role(muted[0]["hex"], "the second most used text colour with enough contrast", "guess") if muted else MISSING("the page uses one text colour")

    if cards and _hex(cards[0]["style"].get("borderTopColor")) and (px(cards[0]["style"].get("borderTopWidth")) or 0) > 0:
        out["border"] = _role(_hex(cards[0]["style"]["borderTopColor"]), "the border of the commonest card", "read")
    else:
        b = [c for c in ix.get("colours", []) if c["uses"].get("border", 0) > 0]
        out["border"] = _role(b[0]["hex"], "the most used border colour", "guess") if b else MISSING("nothing on the page has a border")
    inputs = [c for c in _comps(ix, "input") if (px(c["style"].get("borderTopWidth")) or 0) > 0 and _hex(c["style"].get("borderTopColor"))]
    if inputs:
        out["border-control"] = _role(_hex(inputs[0]["style"]["borderTopColor"]), "the outline of the commonest text box", "read")
    else:
        bb = [c for c in buttons if (px(c["style"].get("borderTopWidth")) or 0) > 0 and _hex(c["style"].get("borderTopColor"))]
        out["border-control"] = _role(_hex(bb[0]["style"]["borderTopColor"]), "the outline of the commonest button: the page has no outlined text box", "guess") if bb else MISSING("no text box or button has an outline")

    hover = None
    for c in _comps(ix, "nav_item") + buttons:
        h = ((c.get("states") or {}).get("hover") or {}).get("backgroundColor")
        if h and _hex(h[1]) and _hex(h[1]) != _bg(c):
            hover = _hex(h[1])
            break
    out["hover"] = _role(hover, "the background a menu item or button takes under the pointer", "read") if hover else MISSING("no menu item or button changes its background under the pointer")
    sel = [s for s in (ix.get("extra") or {}).get("selectedBackgrounds", []) if _hex(s["value"])]
    out["selected"] = _role(_hex(sel[0]["value"]), "the background of the element marked as current or selected", "read") if sel else MISSING("nothing on the page is marked current or selected with a background")

    fam = body.get("fontFamily")
    out["font-body"] = _role(fam, "the font of the page body", "read") if fam else MISSING("no body font")
    code = [f for f in (ix.get("extra") or {}).get("codeFonts", []) if f]
    out["font-mono"] = _role(code[0], "the font of code elements", "read") if code else MISSING("the page shows no code")
    out["font-statement"] = _role(fam, "the body font: requirement wording would follow the body text", "guess") if fam else MISSING("no body font")

    bs = px(body.get("fontSize"))
    out["size-body"] = _role(fmt_px(bs), "the font size of the page body", "read") if bs else MISSING("no body font size")
    styles = (ix.get("type") or {}).get("styles", [])
    total = sum(s["characters"] for s in styles) or 1
    sizes: dict = {}
    for s in styles:
        n = px(s["size"])
        if n:
            sizes[n] = sizes.get(n, 0) + s["characters"]
    acc, small = 0, None
    for n in sorted(sizes):
        acc += sizes[n]
        if n >= 10 and acc / total >= 0.03:
            small = n
            break
    out["size-small"] = _role(fmt_px(small), "the smallest text size that carries 3 % of the characters", "guess") if small else MISSING("no text size to read")
    h1 = [c for c in _comps(ix, "heading") if c.get("tag") == "h1" and px(c["style"].get("fontSize"))]
    heads = [c for c in _comps(ix, "heading") if px(c["style"].get("fontSize"))]
    if h1:
        out["size-title"] = _role(fmt_px(px(h1[0]["style"]["fontSize"])), "the size of the page's h1", "read")
    elif heads:
        out["size-title"] = _role(fmt_px(max(px(c["style"]["fontSize"]) for c in heads)), "the largest heading: the page has no h1", "guess")
    else:
        out["size-title"] = MISSING("the page has no heading")

    def radius(comp, how):
        v = (comp["style"].get("borderTopLeftRadius") or "").split()
        return px(v[0]) if v else None

    rc = radius(main_button, "") if main_button is not None else None
    if rc is not None:
        out["radius-control"] = _role(fmt_px(rc), "the corner of the main button", "read")
    elif inputs and radius(inputs[0], "") is not None:
        out["radius-control"] = _role(fmt_px(radius(inputs[0], "")), "the corner of the commonest text box: no filled button", "guess")
    else:
        out["radius-control"] = MISSING("no button or text box to read")
    out["radius-panel"] = _role(fmt_px(radius(cards[0], "") or 0), "the corner of the commonest card", "read") if cards else MISSING("no card on the page")
    badges = _comps(ix, "badge")
    out["radius-chip"] = _role(fmt_px(radius(badges[0], "") or 0), "the corner of the commonest badge or chip", "read") if badges else MISSING("no badge or chip on the page")
    out["shadow-card"] = _role(cards[0]["style"].get("boxShadow") or "none", "the shadow of the commonest card", "read") if cards else MISSING("no card on the page")

    heights = [(c.get("count", 0), c.get("height")) for c in buttons + _comps(ix, "input") if c.get("height")]
    if heights:
        tally: dict = {}
        for n, h in heights:
            tally[h] = tally.get(h, 0) + n
        out["control-height"] = _role(fmt_px(max(tally, key=lambda h: (tally[h], h))), "the height most buttons and text boxes have", "read")
    else:
        out["control-height"] = MISSING("no button or text box to measure")
    return out


def same(role_id: str, a, b) -> bool:
    """Do two values of one role look the same to a person? Colours within 2 (OKLab x 100), lengths within a pixel, fonts by their first family, anything else by its text."""
    if a is None or b is None:
        return a == b
    kind = BY_ID[role_id]["kind"]
    if kind == "colour":
        ha, hb = _hex(a), _hex(b)
        return ha is not None and hb is not None and C.delta_e(ha, hb) <= 2.0
    if kind == "length":
        pa, pb = px(a), px(b)
        return pa is not None and pb is not None and abs(pa - pb) <= 1.0
    if kind == "font":
        return first_family(a).lower() == first_family(b).lower()
    return " ".join(str(a).split()) == " ".join(str(b).split())


def tokens_for(values: dict, ours_vars: dict | None = None) -> dict:
    """The design tokens (--names) a set of role values drives: each role sets every token it lists in roles.json, and the control height also sets the three sizes derived from it.
    Roles whose value is None are left out, so a token nobody chose keeps the value it has in design/tokens.css. When ours_vars (design/tokens.css as written) is given and a role's
    value is exactly ours, each of its tokens keeps its own value there instead of all taking the first one (so --text-faint stays lighter than --text-muted)."""
    out: dict = {}
    for r in ROLES["roles"]:
        v = values.get(r["id"])
        if v is None:
            continue
        for t in r["ours"]:
            out[t] = ours_vars[t] if ours_vars and t in ours_vars and v == ours_vars.get(r["ours"][0]) else v
        n = px(v) if r.get("derive") else None
        if n is not None:
            for t, d in r["derive"].items():
                out[t] = fmt_px(n + d)
    return out


def roles_of_area(area: str) -> list:
    return [r["id"] for r in ROLES["roles"] if r["area"] == area]


def value_name(role_id: str, v) -> str:
    """A value as a person would say it: a colour as its hex, a font as its first family, a length as it is, a shadow in short."""
    if v is None:
        return "nothing"
    kind = BY_ID[role_id]["kind"]
    if kind == "font":
        return first_family(v)
    if kind == "shadow":
        return "none" if v == "none" else "a shadow"
    if kind == "colour":
        return _hex(v) or str(v)
    return str(v)


def value_text(role_id: str, v) -> str:
    """A value as it is written in CSS (a colour as #RRGGBB, everything else as it is), for tables that need the exact text."""
    if v is None:
        return "not found"
    return (_hex(v) or str(v)) if BY_ID[role_id]["kind"] == "colour" else str(v)


def identical(role_id: str, a, b) -> bool:
    """Exactly the same value (a colour to the digit, a length to the hundredth of a pixel, a font by its whole stack), unlike same(), which forgives what a person cannot see."""
    if a is None or b is None:
        return a == b
    kind = BY_ID[role_id]["kind"]
    if kind == "colour":
        return _hex(a) is not None and _hex(a) == _hex(b)
    if kind == "length":
        return px(a) is not None and px(a) == px(b)
    return " ".join(str(a).split()) == " ".join(str(b).split())


PAIRS = [("ink", "page", 4.5, "main text on the page background"), ("ink", "surface", 4.5, "main text on cards and panels"), ("ink-muted", "page", 4.5, "quiet text on the page background"),
         ("ink-muted", "surface", 4.5, "quiet text on cards and panels"), ("accent-text", "accent", 4.5, "the words on the main button"), ("accent", "surface", 3.0, "the main colour against cards and panels (for a button's edge or an icon)")]


def contrast_findings(values: dict) -> list:
    """[(what, ratio, needed, ok)] for the pairs a person has to read or see: the WCAG 2.x contrast ratio as colour.py works it out, against 4.5 for text and 3 for a coloured control.
    Only pairs whose two colours are known. It does not look at every pairing on a screen: a part drawn in a colour nobody listed here is not checked."""
    out = []
    for fg, bg, need, what in PAIRS:
        a, b = _hex(values.get(fg)), _hex(values.get(bg))
        if a and b:
            r = C.contrast(a, b)
            out.append((what, round(r, 2), need, r >= need))
    return out
