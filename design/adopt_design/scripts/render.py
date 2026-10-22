"""Draw pictures of design decisions, so a person can look before anything is written into their app.

Four kinds of picture:
  theme sheet   your values and ours side by side, role by role (colours, type, corners, shadow, control height)
  part picture  one of our parts (menu, top bar, buttons, ...) drawn with the colours, fonts and corners that are chosen
  option strip  the same part drawn once per option, side by side, for a question
  page preview  your own page opened in a browser, with the chosen colours, corners and fonts applied to your own elements and our menu / top bar drawn over yours

What is real and what is not: part pictures are drawn from the specimens in specimens/ with the stylesheet rules the prototype and the design kit really use. A specimen is a
drawing made for this kit, not the prototype's own markup. The page preview restyles your page by the selectors the index found, so it shows the decision, not the code that will be
written. Fonts that are not installed on the machine that draws are shown in a stand-in, and the picture's note says which.

The pure builders (those that return HTML text) need nothing but the standard library; drawing needs Playwright with Chromium.
"""
from __future__ import annotations

import html as H
import http.server
import re
import socketserver
import tempfile
import threading
from pathlib import Path
from urllib.parse import urlparse

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT, REPO, TOKENS_CSS, css_vars, first_family, px, read_json  # noqa: E402
import catalog as CAT  # noqa: E402
import roles as R  # noqa: E402

FONT_DIR = REPO / "prototype" / "project" / "fonts"     # where the files design/tokens.css names as ./fonts/... are kept
GENERIC = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy", "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded", "inherit", "initial"}
AREA_SAMPLE = ["buttons", "form-input", "card", "source-chip"]       # what an area question draws: the smallest set that shows colour, corner, type, shadow and height
CHROME = (".cap{font:12px/1.45 system-ui,Segoe UI,sans-serif;color:#3b4652;margin:0 0 8px}.cap b{color:#111}"
          "body{margin:0;padding:16px;background:#e9ecef;font-family:system-ui,Segoe UI,sans-serif}"
          ".strip{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}.strip figure{margin:0}"
          ".cell{background:var(--canvas);color:var(--ink);font-family:var(--sans);font-size:var(--size-body);padding:16px;border:1px solid #c5ccd3;display:flex;flex-direction:column;gap:14px;"
          "align-items:flex-start;min-width:200px}.cell .item{max-width:100%}.note{font:12px/1.45 system-ui,sans-serif;color:#6a4b00;background:#fff4d6;border:1px solid #e8d08a;"
          "padding:6px 10px;margin:10px 0 0}")


# ------------------------------------------------------------------------------------------------ small pure helpers
def font_faces(base: str) -> str:
    """The @font-face blocks of design/tokens.css with their files pointed at base + '/fonts/' (served from prototype/project/fonts, where the files are)."""
    text = TOKENS_CSS.read_text(encoding="utf-8")
    return "\n".join(re.sub(r"url\(\./fonts/", "url(%s/fonts/" % base, b) for b in re.findall(r"@font-face\{[^}]*\}", text))


def ours_root() -> str:
    return ":root{%s}" % ";".join("%s:%s" % kv for kv in css_vars(TOKENS_CSS.read_text(encoding="utf-8")).items())


def style_attr(tokens: dict) -> str:
    return H.escape(";".join("%s:%s" % (k, v) for k, v in sorted(tokens.items())), quote=True)


def prefix_css(css: str, prefix: str) -> str:
    """Put prefix in front of every selector of every rule in css (used to make a rule apply inside one picture only)."""
    out = []
    for prelude, body in CAT._blocks(CAT._strip_comments(css)):
        if prelude.startswith("@"):
            out.append("%s{%s}" % (prelude, prefix_css(body, prefix)))
        else:
            out.append("%s{%s}" % (",".join(prefix + s for s in CAT._split_selectors(prelude)), body))
    return "\n".join(out)


def parts_by_id() -> dict:
    return {p["id"]: p for p in CAT.all_parts()}


def parts_css(part_ids: list, icons_off: dict | None = None, tokens: dict | None = None) -> str:
    """The stylesheet for a picture that draws these parts: each part's rules (literals named by tokens), its stage rules, and for a part whose icons are off, the rule that hides them
    when the picture's cell carries the class off-<part id>."""
    bp = parts_by_id()
    seen, out = set(), []
    for pid in part_ids:
        if pid in seen:
            continue
        seen.add(pid)
        p = bp[pid]
        css, _ = CAT.part_css(p, tokens)
        out.append(css)
        if p.get("stage_css"):
            out.append(p["stage_css"])
        if p.get("icons"):
            out.append(prefix_css(p["icons"]["css"], ".cell.off-%s " % pid))
    return "\n".join(out)


def cell_html(label: str, tokens: dict, part_ids: list, icons_off=(), note: str = "", specimens: dict | None = None) -> str:
    """One labelled picture of some parts drawn with these tokens. specimens maps a part id to replacement markup (the page preview uses it to put the person's own menu items in our menu)."""
    bp = parts_by_id()
    off = " ".join("off-" + p for p in part_ids if p in set(icons_off))
    items = []
    for pid in part_ids:
        spec = (specimens or {}).get(pid) or (KIT / bp[pid]["specimen"]).read_text(encoding="utf-8")
        items.append('<div class="item" data-part="%s">%s</div>' % (pid, spec))
    return ('<figure><p class="cap"><b>%s</b>%s</p><div class="cell %s" style="%s">%s</div></figure>'
            % (H.escape(label), (" " + H.escape(note)) if note else "", off, style_attr(tokens), "".join(items)))


def page_html(body: str, css: str, base: str, notes: list | None = None, title: str = "") -> str:
    ns = "".join('<p class="note">%s</p>' % H.escape(n) for n in (notes or []))
    return ('<!doctype html><meta charset="utf-8"><title>%s</title><style>%s</style><style>%s</style><style>%s</style><style>%s</style><div class="strip">%s</div>%s'
            % (H.escape(title), font_faces(base), ours_root(), CHROME, css, body, ns))


def strip_html(cells: list, part_ids: list, base: str, icons_off=(), notes=None, title="") -> str:
    """cells: [(label, tokens, note)] -> one page that draws the same parts once per cell."""
    body = "".join(cell_html(lb, tk, part_ids, icons_off, nt) for lb, tk, nt in cells)
    return page_html(body, parts_css(part_ids, tokens=None), base, notes, title)


_SW = ("body{margin:0;padding:16px;background:#e9ecef;font:13px/1.4 system-ui,Segoe UI,sans-serif;color:#1b2733}.cols{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}"
       ".col{background:#fff;border:1px solid #c5ccd3;padding:14px 16px;width:300px}.col h2{font:600 15px system-ui;margin:0 0 2px}.col .sub{color:#56626d;margin:0 0 10px;font-size:12px}"
       ".col h3{font:600 12px system-ui;color:#56626d;margin:14px 0 6px;text-transform:none}.sw{display:flex;gap:8px;align-items:center;margin:3px 0}"
       ".sw i{display:inline-block;width:26px;height:26px;border:1px solid #9aa5b1;flex:none}.sw i.none{background:repeating-linear-gradient(45deg,#fff 0 4px,#e3e7eb 4px 8px)}"
       ".sw span{flex:1}.sw small{color:#6b7782}.row{display:flex;gap:10px;align-items:center;margin:6px 0;flex-wrap:wrap}.tag{font-size:11px;color:#6b7782;margin-top:2px}")


def theme_sheet_html(columns: list, base: str, notes: list | None = None) -> str:
    """columns: [{'title','sub','values': role -> value or None,'conf': role -> 'read'|'guess'|'missing' (optional)}]. Each column shows every role drawn in its own value."""
    out = []
    for col in columns:
        v = col["values"]
        conf = col.get("conf") or {}

        def val(role, default=None):
            return v.get(role) if v.get(role) is not None else default

        sw = []
        for r in R.ROLES["roles"]:
            if r["area"] != "palette":
                continue
            x = val(r["id"])
            mark = {"guess": " (a guess)", "missing": ""}.get(conf.get(r["id"], ""), "")
            sw.append('<div class="sw"><i %s></i><span>%s</span><small>%s%s</small></div>' % (
                ('style="background:%s"' % H.escape(R._hex(x) or x, quote=True)) if x else 'class="none"', H.escape(r["label"]), H.escape(R.value_name(r["id"], x) if x else "not found"), mark))
        fb, fs, fm = val("font-body", "sans-serif"), val("font-statement", "serif"), val("font-mono", "monospace")
        sb, sm, st = val("size-body", "14px"), val("size-small", "12px"), val("size-title", "26px")
        rc, rp, rch = val("radius-control", "0px"), val("radius-panel", "0px"), val("radius-chip", "0px")
        h = val("control-height", "36px")
        sh = val("shadow-card", "none")
        acc, acct = R._hex(val("accent")) or "#555555", R._hex(val("accent-text")) or "#ffffff"
        pg, srf, ink = R._hex(val("page")) or "#f4f4f4", R._hex(val("surface")) or "#ffffff", R._hex(val("ink")) or "#111111"
        brd = R._hex(val("border")) or "#cccccc"
        bc = R._hex(val("border-control")) or "#888888"
        out.append(
            '<div class="col"><h2>%s</h2><p class="sub">%s</p><h3>Colours</h3>%s<h3>Type</h3>'
            '<div style="font-family:%s;font-size:%s;color:%s">Text: the wording of a requirement, in %s at %s</div>'
            '<div style="font-family:%s;font-size:%s;font-weight:600;margin:4px 0">Page title in %s</div>'
            '<div style="font-family:%s;font-size:%s;color:%s">Small text: a caption or a chip, %s</div>'
            '<div style="font-family:%s;font-size:%s">REQ-0042  code in %s</div>'
            '<h3>Corners, shadow and height</h3><div class="row" style="background:%s;padding:12px">'
            '<span style="background:%s;color:%s;border-radius:%s;height:%s;line-height:%s;padding:0 14px;display:inline-block;font-family:%s;font-size:%s">Button</span>'
            '<span style="border:1px solid %s;background:#fff;border-radius:%s;height:%s;line-height:%s;padding:0 12px;display:inline-block;color:#444;font-family:%s;font-size:%s">Text box</span>'
            '<span style="background:%s;border:1px solid %s;border-radius:%s;padding:2px 10px;font-family:%s;font-size:%s;color:%s">chip</span>'
            '<div style="background:%s;border:1px solid %s;border-radius:%s;box-shadow:%s;padding:14px 16px;width:100%%;box-sizing:border-box;color:%s;font-family:%s;font-size:%s">A card: panel corner %s, control height %s</div></div></div>'
            % (H.escape(col["title"]), H.escape(col.get("sub", "")), "".join(sw),
               H.escape(fb), H.escape(sb), ink, H.escape(R.first_family(fb) or "the page font"), H.escape(sb),
               H.escape(fb), H.escape(st), H.escape(st),
               H.escape(fb), H.escape(sm), ink, H.escape(sm),
               H.escape(fm), H.escape(sm), H.escape(R.first_family(fm)),
               pg, acc, acct, H.escape(rc), H.escape(h), H.escape(h), H.escape(fb), H.escape(sb),
               bc, H.escape(rc), H.escape(h), H.escape(h), H.escape(fb), H.escape(sb),
               srf, brd, H.escape(rch), H.escape(fb), H.escape(sm), ink,
               srf, brd, H.escape(rp), H.escape(sh), ink, H.escape(fb), H.escape(sb), H.escape(rp), H.escape(h)))
    ns = "".join('<p class="note">%s</p>' % H.escape(n) for n in (notes or []))
    return '<!doctype html><meta charset="utf-8"><title>theme</title><style>%s</style><style>%s</style><style>%s</style><div class="cols">%s</div>%s' % (
        font_faces(base), ours_root(), _SW + CHROME, "".join(out), ns)


def sample_html(role: str, value) -> str:
    """A small drawing of one role's value, for a person to check a guess against what they see on their own page."""
    r = R.BY_ID[role]
    v = value
    e = lambda x: H.escape(str(x), quote=True)  # noqa: E731
    if v is None:
        return "not found"
    if r["kind"] == "colour":
        hx = R._hex(v) or str(v)
        return ('<span style="display:inline-block;width:64px;height:28px;background:%s;border:1px solid #9aa5b1;vertical-align:middle"></span> '
                '<span style="color:%s;background:#fff;padding:4px 8px;border:1px solid #dde2e6;font:13px system-ui">Sample text in this colour</span>' % (e(hx), e(hx)))
    if r["kind"] == "font":
        return '<span style="font-family:%s;font-size:18px">The quick brown fox jumps over the lazy dog</span>' % e(v)
    if r["kind"] == "shadow":
        return '<span style="display:inline-block;width:120px;height:36px;background:#fff;box-shadow:%s"></span>' % e(v)
    if role.startswith("radius"):
        return '<span style="display:inline-block;width:120px;height:36px;background:#e9edf1;border:1px solid #9aa5b1;border-radius:%s"></span>' % e(v)
    if role.startswith("size"):
        return '<span style="font:%s system-ui">Sample text at this size</span>' % e(v)
    return '<span style="display:inline-block;width:120px;height:%s;line-height:%s;background:#e9edf1;border:1px solid #9aa5b1;text-align:center;font:13px system-ui">%s</span>' % (e(v), e(v), e(v))


def samples_html(items: list, base: str, notes=None) -> str:
    """items: [(role id, value)]: a page of drawn samples, one per role, each with the value in words."""
    rows = "".join('<tr><td>%s<br><small>%s</small></td><td>%s</td></tr>' % (H.escape(R.BY_ID[ro]["label"]), H.escape(R.value_name(ro, v)), sample_html(ro, v)) for ro, v in items)
    css = _SW + CHROME + "table{border-collapse:collapse;background:#fff;border:1px solid #c5ccd3}td{padding:8px 14px;border-bottom:1px solid #e3e7eb;vertical-align:middle}small{color:#6b7782}"
    ns = "".join('<p class="note">%s</p>' % H.escape(n) for n in (notes or []))
    return '<!doctype html><meta charset="utf-8"><title>samples</title><style>%s</style><style>%s</style><style>%s</style><table>%s</table>%s' % (font_faces(base), ours_root(), css, rows, ns)


# ------------------------------------------------------------------------------------------------ your menu, drawn in our menu design
def side_bar_from_structure(structure: dict | None, fallback: str) -> tuple:
    """Our menu markup holding the person's own menu items (their groups, their labels, their counts, their current item). (markup, note). Without a menu to read: the specimen and a note."""
    lms = (structure or {}).get("landmarks") or []
    lm = max(lms, key=lambda m: sum(len(g["items"]) for g in m["groups"]), default=None)
    if not lm or not any(g["items"] for g in lm["groups"]):
        return fallback, "your page's menu could not be read, so our menu is drawn with our own items"
    glyph = '<svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><rect x="3" y="3" width="12" height="12" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'
    arrow = '<svg width="14" height="14" viewBox="0 0 14 14" aria-hidden="true"><path d="M5 3l4 4-4 4" fill="none" stroke="currentColor" stroke-width="1.6"/></svg>'

    def item(it):
        cur = ' aria-current="page"' if it.get("current") else ""
        cnt = '<span class="nav-count">%s</span>' % H.escape(str(it["count"])) if it.get("count") else ""
        return '<button class="nav-btn"%s>%s<span>%s</span>%s</button>' % (cur, glyph, H.escape(it["label"]), cnt)

    body = []
    for g in lm["groups"]:
        if not g["items"]:
            continue
        if g.get("heading"):
            body.append('<div class="nav-group"><button class="nav-ghead" aria-expanded="true">%s<span>%s</span></button><div class="nav-kids" data-open="true">%s</div></div>'
                        % (arrow, H.escape(g["heading"]), "".join(item(i) for i in g["items"])))
        else:
            body.append("".join(item(i) for i in g["items"]))
    return '<nav class="ws-nav" aria-label="Main"><div class="ws-navlist">%s</div></nav>' % "".join(body), "the items are yours; the little square in front of each is a stand-in, not your icon"


def top_bar_from_page(fallback: str, title: str, heading: str) -> str:
    """Our top bar with the person's page title and first heading where our made-up project and screen names are, and without our made-up scope and baseline chips."""
    out = fallback
    for chip in ("All requirements", "Pre-baseline"):             # our made-up scope and baseline chips are not the person's
        out = re.sub(r'<span style="[^"]*border-radius:999px[^"]*">%s</span>\s*' % re.escape(chip), "", out, count=1)
    out = out.replace('placeholder="Search requirements" aria-label="Search requirements"', 'placeholder="Search" aria-label="Search"', 1)
    if title:
        out = out.replace(">Alpha project<", ">%s<" % H.escape(title[:40]), 1)
    else:
        out = out.replace(">Alpha project<", ">Your app<", 1)
    if heading and heading.strip() != title.strip():
        out = out.replace(">Review queue<", ">%s<" % H.escape(heading[:40]), 1)
    else:                                              # nothing of the person's to put after the slash: take our made-up screen name and the slash out
        out = re.sub(r'\s*<span aria-hidden="true"[^>]*>/</span>\s*<span[^>]*>Review queue</span>', "", out, count=1)
    return out


# ------------------------------------------------------------------------------------------------ your page, restyled by the decision
RESTYLE = [  # role, which elements, css property
    ("page", "page", "background-color"), ("ink", "page", "color"), ("font-body", "page", "font-family"), ("size-body", "page", "font-size"),
    ("accent", "main_button", "background-color"), ("accent-text", "main_button", "color"),
    ("radius-control", "button", "border-radius"), ("control-height", "button", "min-height"),
    ("border-control", "input", "border-color"), ("radius-control", "input", "border-radius"), ("control-height", "input", "min-height"),
    ("surface", "card", "background-color"), ("border", "card", "border-color"), ("radius-panel", "card", "border-radius"), ("shadow-card", "card", "box-shadow"),
    ("radius-chip", "badge", "border-radius"), ("size-title", "h1", "font-size"), ("selected", "current", "background-color"), ("font-mono", "code", "font-family"),
]
FIXED = {"page": "html, body", "h1": "h1", "current": "[aria-current]:not([aria-current=false]), [aria-selected=true]", "code": "code, pre, kbd, samp"}
FALLBACK = {"button": "button, [role=button]", "input": "input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]):not([type=hidden]), textarea, select"}


def selectors_by_kind(ix: dict, mine: dict) -> dict:
    """{kind: selector list} the preview restyles, from what the index matched. A selector that finds only part of its group (below 50 %) is not used, so the preview does not restyle the world."""
    out: dict = {"button": [], "input": [], "card": [], "badge": [], "main_button": []}
    accent = R._hex((mine.get("accent") or {}).get("value"))
    for c in ix.get("components", []):
        sel = c.get("selector")
        if not sel or sel["jaccard"] < 0.5 or c["kind"] not in out:
            continue
        out[c["kind"]].append(sel["selector"])
        if c["kind"] == "button" and accent and R._hex((c.get("style") or {}).get("backgroundColor")) == accent:
            out["main_button"].append(sel["selector"])
    for k in ("button", "input"):
        if not out[k]:
            out[k] = [FALLBACK[k]]
    return {k: sorted(set(v)) for k, v in out.items()}


PART_KINDS = {"buttons": ["main_button", "button"], "form-input": ["input"], "card": ["card"], "source-chip": ["badge"], "change-chip": ["badge"]}   # which of your elements a component part restyles


def restyle_css(ix: dict, mine: dict, result: dict, kinds: list | None = None) -> tuple:
    """(css, drawn, not_drawn): rules that give your own elements the result's values where they differ from yours. mine is role -> {'value'}, result is role -> value.
    kinds limits it to some kinds of element (a component part restyles only the elements it stands for)."""
    sels = selectors_by_kind(ix, mine)
    css, drawn, missing = [], [], []
    for role, kind, prop in RESTYLE:
        if kinds is not None and kind not in kinds:
            continue
        val = result.get(role)
        if val is None or R.same(role, (mine.get(role) or {}).get("value"), val):
            continue
        group = FIXED.get(kind) or ", ".join(sels.get(kind, []))
        if not group:
            missing.append("%s: your page has no %s that the index could find again, so this is not shown" % (R.BY_ID[role]["label"], kind.replace("_", " ")))
            continue
        css.append("%s{%s:%s !important}" % (group, prop, val))
        drawn.append("%s on your %s" % (R.BY_ID[role]["label"].lower(), kind.replace("_", " ")))
    return "\n".join(css), drawn, missing


# ------------------------------------------------------------------------------------------------ drawing
def available() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
        return True
    except ImportError:
        return False


class _Handler(http.server.SimpleHTTPRequestHandler):
    stage = "."

    def translate_path(self, path):
        p = urlparse(path).path
        base, rel = (FONT_DIR, p[len("/fonts/"):]) if p.startswith("/fonts/") else (Path(self.stage), p.lstrip("/"))
        full = (base / rel).resolve()
        return str(full) if str(full).startswith(str(base.resolve())) else str(base / "__nothing__")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *a):
        pass


FONT_PROBE = """async (families) => {
  const c = document.createElement('canvas').getContext('2d'), t = 'mmmmmmmmmmlliWWW0123456789', out = {};
  const w = (f, s) => { c.font = f; return c.measureText(s).width; };
  for (const f of families) {
    try { await document.fonts.load('16px "' + f + '"', t); } catch (e) {}
    out[f] = ['monospace', 'serif', 'sans-serif'].some(b => w('16px "' + f + '", ' + b, t) !== w('16px ' + b, t));
  }
  return out;
}"""


class Renderer:
    """Draws HTML (or a page with changes) to PNG files. Use as a context manager. Serves the font files and a scratch folder on 127.0.0.1 so the fonts load."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.n = 0

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        _Handler.stage = self._tmp.name
        self._srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
        self._srv.daemon_threads = True
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        self.base = "http://127.0.0.1:%d" % self._srv.server_address[1]
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        return self

    def __exit__(self, *a):
        try:
            self.browser.close()
            self._pw.stop()
        finally:
            self._srv.shutdown()
            self._srv.server_close()
            self._tmp.cleanup()

    def stand_ins(self, families: list, page) -> list:
        fams = sorted({first_family(f) for f in families if f and first_family(f).lower() not in GENERIC})
        if not fams:
            return []
        have = page.evaluate(FONT_PROBE, fams)
        return [f for f in fams if not have.get(f)]

    def draw(self, html: str, out_png, fonts: list | None = None, width: int = 1000) -> dict:
        """Write html to a scratch page, open it, take a picture of the whole page. Returns {'file', 'stand_in': fonts that are not installed here}."""
        self.n += 1
        name = "p%d.html" % self.n
        (Path(self._tmp.name) / name).write_text(html, encoding="utf-8")
        page = self.browser.new_page(viewport={"width": width, "height": 600})
        try:
            page.goto("%s/%s" % (self.base, name), wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            stand = self.stand_ins(fonts or [], page)
            Path(out_png).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_png), full_page=True)
        finally:
            page.close()
        return {"file": str(out_png), "stand_in": stand}

    def draw_page(self, url: str, setup: list, out_png, prepare=None, width: int = 1440, height: int = 900) -> dict:
        """Open the person's page (after the setup steps that got it to the state that was indexed), let prepare(page) change it, take a picture of what is on screen."""
        import site_map as SM
        page = self.browser.new_page(viewport={"width": width, "height": height})
        try:
            page.goto(url, wait_until="load", timeout=30000)
            page.evaluate("document.fonts.ready.then(() => true)")
            if setup:
                SM.run_setup(page, setup)
            result = prepare(page) if prepare else {}
            page.evaluate("document.fonts.ready.then(() => true)")
            Path(out_png).parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(out_png))
        finally:
            page.close()
        return {"file": str(out_png), **(result or {})}


OVERLAY = """([host, regionBox, markup, css, tokens]) => {
  const near = (a, b) => Math.abs(a - b) <= 3;
  const els = [...document.querySelectorAll(host)].filter(e => { const r = e.getBoundingClientRect(); return near(r.x, regionBox[0]) && near(r.y + scrollY, regionBox[1]) && near(r.width, regionBox[2]) && near(r.height, regionBox[3]); });
  if (!els.length) return false;
  const el = els[0], r = el.getBoundingClientRect();
  el.style.setProperty('visibility', 'hidden', 'important');
  const h = document.createElement('div');
  h.setAttribute('data-adopt-overlay', '1');
  h.style.cssText = 'position:absolute;z-index:2147483000;left:' + (r.x + scrollX) + 'px;top:' + (r.y + scrollY) + 'px;width:' + r.width + 'px;height:' + r.height + 'px;overflow:hidden;' + tokens;
  const s = h.attachShadow({mode: 'open'});
  s.innerHTML = '<style>' + css + '</style><div style="height:100%;' + tokens + '">' + markup + '</div>';
  document.body.appendChild(h);
  return true;
}"""


def overlay_region(structure_ix: dict, part_id: str):
    """The region of the person's page our part would replace: a menu is the left-most tall navigation, a top bar the banner."""
    regs = structure_ix.get("regions", [])
    if part_id == "side-bar":
        cand = [r for r in regs if r["role"] in ("navigation", "complementary") and r["box"][3] > r["box"][2] and r["box"][0] < 400]
        return min(cand, key=lambda r: r["box"][0], default=None)
    if part_id == "top-bar":
        cand = [r for r in regs if r["role"] == "banner" and r["box"][2] > r["box"][3]]
        return min(cand, key=lambda r: r["box"][1], default=None)
    return None


def part_stylesheet(pid: str, icons_off: bool = False, tokens: dict | None = None) -> str:
    """One part's stylesheet for use inside the page preview (no picture cell around it): its rules, stage rules that make it fill its box, and the rule that hides its icons when they are off."""
    p = parts_by_id()[pid]
    css, _ = CAT.part_css(p, tokens)
    fill = {"side-bar": ".ws-nav{height:100% !important;width:100% !important;box-sizing:border-box}", "top-bar": ".topbar{width:100% !important;box-sizing:border-box;height:100%}"}.get(pid, "")
    return "\n".join([css, p.get("stage_css", ""), fill, p["icons"]["css"] if icons_off and p.get("icons") else ""])


def preview_page(r: Renderer, url: str, setup: list, ix: dict, mine: dict, result: dict, part_values: dict, part_tokens: dict, icons_off, out_dir) -> dict:
    """Two pictures of the person's own page: as it is, and with the decisions applied. mine is the index's roles, result is role -> value for the theme, part_values and part_tokens map each
    chosen part id to its own role values and tokens. The menu and top bar are drawn over yours; component parts restyle your own buttons, text boxes, cards and chips."""
    out_dir = Path(out_dir)
    picks = list(part_values)
    css, drawn, not_drawn = restyle_css(ix, mine, result)
    for pid in picks:
        if pid in PART_KINDS:
            c, d, n = restyle_css(ix, mine, part_values[pid], PART_KINDS[pid])
            css += "\n" + c
            drawn += ["%s (%s)" % (x, parts_by_id()[pid]["name"].lower()) for x in d if x not in drawn and ("%s (" % x) not in " ".join(drawn)]
            not_drawn += [x for x in n if x not in not_drawn]
    before = r.draw_page(url, setup, out_dir / "page-before.png")
    heading = (((ix.get("structure") or {}).get("main") or {}).get("headings") or [""])[0]
    notes = []

    def prepare(page):
        page.add_style_tag(content=font_faces(r.base) + "\n" + css)
        got = {"overlays": [], "not_overlaid": []}
        for pid in [p for p in picks if p in ("side-bar", "top-bar")]:
            reg = overlay_region(ix, pid)
            name = parts_by_id()[pid]["name"].lower()
            if not reg:
                got["not_overlaid"].append("the %s: your page has no %s that could be found, so it is not drawn over your page" % (name, "side menu" if pid == "side-bar" else "top bar"))
                continue
            spec = (KIT / parts_by_id()[pid]["specimen"]).read_text(encoding="utf-8")
            if pid == "side-bar":
                markup, note = side_bar_from_structure(ix.get("structure"), spec)
            else:
                markup, note = top_bar_from_page(spec, (ix.get("page") or {}).get("title", ""), heading), "the project and screen names are taken from your page's title and first heading"
            ok = page.evaluate(OVERLAY, [reg["selector"], reg["box"], markup, part_stylesheet(pid, pid in set(icons_off), part_tokens[pid]),
                                         ";".join("%s:%s" % kv for kv in sorted(part_tokens[pid].items()))])
            if ok:
                got["overlays"].append("our %s drawn over yours (%s)" % (name, note))
            else:
                got["not_overlaid"].append("the %s: the region found at index time was not found again at the same place" % name)
        return got

    after = r.draw_page(url, setup, out_dir / "page-after.png", prepare)
    notes += after.pop("not_overlaid", [])
    drawn += after.pop("overlays", [])
    return {"before": before["file"], "after": after["file"], "drawn": drawn, "not_drawn": not_drawn + notes,
            "caveat": "This is your own page opened now, with the decisions applied to it for the picture. It shows the decision; it is not the code that will be written, and anything behind a click that was not set up is not shown."}
