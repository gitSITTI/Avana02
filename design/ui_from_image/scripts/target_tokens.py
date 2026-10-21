#!/usr/bin/env python3
"""Read the real design language of a page that is already running: its colours, type, radii, shadows, spacing, buttons, inputs, cards, and what hover and focus do.

    python3 target_tokens.py PAGE --out target_tokens.json [--shots DIR] [--width 1440] [--height 900] [--max-per-kind 6]

PAGE is a URL (http, https) or an HTML file on disk. The page is opened in a real browser (Chromium through Playwright), so what is read is what the browser computed,
not what a picture suggests: a colour read off a screenshot can be a few steps off, a computed colour is exact.

What it writes (format reqin-target-tokens/1):
  declared_vars   every CSS custom property (--name) the page's stylesheets declare, with the value the browser resolved at :root
  colours         every colour the page paints text, backgrounds, borders and icons with, how often, and which declared names resolve to it
  type            font families, the sizes and weights in use, the web fonts declared and whether each loaded, and which font each sample really RENDERED in
  radii, shadows, padding, gap   what is in use, most common first
  components      for buttons, links, inputs, headings, table cells, badges, nav items and cards: each distinct look (count, text sample, computed style, a cropped
                  screenshot) and what hover and keyboard focus change

It does not read: styles inside cross-origin stylesheets or shadow roots it cannot reach (they are listed under notes), gradients and images, anything that only
appears after a click, or any state the page cannot reach without signing in.
Needs Playwright with a Chromium browser:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colour as C  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sys.exit("target_tokens.py needs Playwright: pip install playwright && playwright install chromium")

# Read once, in the page. Everything is counted here so little data crosses back.
COLLECT = r"""
() => {
  const R = {declared: [], unreadable: [], uses: {}, type: {}, radii: {}, shadows: {}, padding: {}, gap: {}, faces: [], elements: 0};
  const bump = (m, k, n = 1) => { m[k] = (m[k] || 0) + n; };
  const walk = (rules, ctx) => {
    for (const r of rules) {
      if (r.style) for (let i = 0; i < r.style.length; i++) {
        const n = r.style[i];
        if (n.startsWith('--')) R.declared.push({name: n, value: r.style.getPropertyValue(n).trim(), selector: r.selectorText || '', context: ctx});
      }
      if (r.cssRules) walk(r.cssRules, r.conditionText || r.name || ctx);
    }
  };
  for (const sheet of document.styleSheets) {
    let rules = null;
    try { rules = sheet.cssRules; } catch (e) { R.unreadable.push(sheet.href || 'inline'); continue; }
    walk(rules, '');
  }
  const root = getComputedStyle(document.documentElement);
  const seen = new Set();
  R.declared = R.declared.filter(d => { const k = d.name + '|' + d.value + '|' + d.selector; if (seen.has(k)) return false; seen.add(k); return true; });
  for (const d of R.declared) d.resolved = root.getPropertyValue(d.name).trim();
  for (const f of document.fonts) R.faces.push({family: f.family.replace(/^["']|["']$/g, ''), weight: f.weight, style: f.style, status: f.status});
  const alphaOf = v => { const m = v.match(/^rgba?\(([^)]*)\)/); if (!m) return 1; const p = m[1].split(/[ ,\/]+/).filter(Boolean); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const shown = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const use = (value, kind, n = 1) => { if (!value) return; bump(R.uses, kind + '|' + value, n); };
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE'].includes(el.tagName) || !shown(el)) continue;
    R.elements++;
    const cs = getComputedStyle(el), r = el.getBoundingClientRect();
    const ownText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
    if (ownText) {
      use(cs.color, 'text');
      const t = [cs.fontFamily, cs.fontSize, cs.fontWeight, cs.lineHeight, cs.letterSpacing, cs.textTransform].join('|');
      bump(R.type, t + '|' + el.tagName.toLowerCase(), [...el.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent.trim().length).reduce((a, b) => a + b, 0));
    }
    const hasBg = alphaOf(cs.backgroundColor) > 0;
    if (hasBg) use(cs.backgroundColor, 'background', 1);
    let border = false;
    for (const s of ['Top', 'Right', 'Bottom', 'Left']) {
      if (parseFloat(cs['border' + s + 'Width']) > 0 && cs['border' + s + 'Style'] !== 'none' && alphaOf(cs['border' + s + 'Color']) > 0) { use(cs['border' + s + 'Color'], 'border'); border = true; }
    }
    if (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) use(cs.outlineColor, 'outline');
    if (el instanceof SVGElement && !(el instanceof SVGSVGElement)) {
      if (cs.fill && cs.fill !== 'none' && cs.fill.startsWith('rgb')) use(cs.fill, 'icon');
      if (cs.stroke && cs.stroke !== 'none' && cs.stroke.startsWith('rgb')) use(cs.stroke, 'icon');
    }
    if (hasBg || border) {
      const q = ['TopLeft', 'TopRight', 'BottomRight', 'BottomLeft'].map(c => cs['border' + c + 'Radius']);
      const rad = q.every(v => v === q[0]) ? q[0] : q.join(' ');
      if (rad !== '0px') bump(R.radii, rad);
      for (const p of ['Top', 'Right', 'Bottom', 'Left']) { const v = cs['padding' + p]; if (v !== '0px') bump(R.padding, v); }
    }
    if (cs.boxShadow !== 'none') bump(R.shadows, cs.boxShadow);
    if ((cs.display === 'flex' || cs.display === 'grid' || cs.display === 'inline-flex') && cs.rowGap !== 'normal' && cs.rowGap !== '0px') bump(R.gap, cs.rowGap === cs.columnGap ? cs.rowGap : cs.rowGap + ' ' + cs.columnGap);
  }
  R.title = document.title; R.lang = document.documentElement.lang || '';
  R.viewport = [innerWidth, innerHeight];
  R.rootFont = root.fontSize;
  return R;
}
"""

SAMPLES = r"""
(maxPerKind) => {
  const KINDS = {
    button: 'button, [role=button], input[type=button], input[type=submit], a[class*=btn], a[class*=button]',
    link: 'a[href]',
    input: 'input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]):not([type=hidden]), textarea, select',
    heading: 'h1, h2, h3, h4, h5, h6',
    table_cell: 'th, td',
    badge: '[class*=badge], [class*=chip], [class*=pill], [class*=tag], [class*=status]',
    nav_item: 'nav a, [role=navigation] a, [role=tab], [role=menuitem]',
    card: '*',
  };
  const KEYS = ['color', 'backgroundColor', 'borderTopColor', 'borderTopWidth', 'borderTopStyle', 'borderTopLeftRadius', 'paddingTop', 'paddingRight', 'fontFamily', 'fontSize', 'fontWeight',
                'lineHeight', 'letterSpacing', 'textTransform', 'textDecorationLine', 'boxShadow', 'height', 'minHeight'];
  const alphaOf = v => { const m = v.match(/^rgba?\(([^)]*)\)/); if (!m) return 1; const p = m[1].split(/[ ,\/]+/).filter(Boolean); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const shown = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const isCard = (el, cs, r) => r.width >= 200 && r.height >= 60 && alphaOf(cs.backgroundColor) > 0 && parseFloat(cs.borderTopLeftRadius) > 0 && (parseFloat(cs.borderTopWidth) > 0 || cs.boxShadow !== 'none');
  const out = [];
  let id = 0;
  for (const [kind, sel] of Object.entries(KINDS)) {
    const groups = new Map();
    for (const el of document.body.querySelectorAll(sel)) {
      if (!shown(el)) continue;
      const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      if (kind === 'card' && !isCard(el, cs, r)) continue;
      const style = {}; for (const k of KEYS) style[k] = cs[k];
      style.disabled = !!el.disabled;
      const sig = JSON.stringify(style);
      const g = groups.get(sig) || {count: 0, el, style, text: (el.innerText || el.value || el.placeholder || '').trim().slice(0, 60), w: Math.round(r.width), h: Math.round(r.height)};
      g.count++; groups.set(sig, g);
    }
    [...groups.values()].sort((a, b) => b.count - a.count).slice(0, maxPerKind).forEach(g => {
      g.el.setAttribute('data-reqin-sample', String(++id));
      out.push({id, kind, count: g.count, text: g.text, tag: g.el.tagName.toLowerCase(), width: g.w, height: g.h, style: g.style});
    });
  }
  return out;
}
"""

READ_STATE = r"""
(id) => {
  const el = document.querySelector('[data-reqin-sample="' + id + '"]'); if (!el) return null;
  const cs = getComputedStyle(el); const o = {};
  for (const k of ['color', 'backgroundColor', 'borderTopColor', 'borderTopWidth', 'boxShadow', 'outlineStyle', 'outlineWidth', 'outlineColor', 'outlineOffset', 'textDecorationLine', 'opacity', 'transform', 'cursor']) o[k] = cs[k];
  return o;
}
"""

COLOUR_KINDS = ("text", "background", "border", "outline", "icon")
STATE_KINDS = ("button", "link", "input", "nav_item")


def hexify(value: str):
    """(hex, alpha) for a computed colour, or None."""
    return C.parse_css(value)


def aggregate_colours(uses: dict, declared: list):
    names: dict = {}
    for d in declared:
        p = hexify(d.get("resolved") or d["value"])
        if p and p[1] == 1.0:
            names.setdefault(p[0], []).append(d["name"])
    table: dict = {}
    translucent: dict = {}
    unparsed: dict = {}
    for key, n in uses.items():
        kind, _, value = key.partition("|")
        p = hexify(value)
        if p is None:
            unparsed[value] = unparsed.get(value, 0) + n
        elif p[1] < 1.0:
            translucent[value] = translucent.get(value, 0) + n
        else:
            row = table.setdefault(p[0], {"hex": p[0], "uses": {k: 0 for k in COLOUR_KINDS}, "count": 0, "names": sorted(set(names.get(p[0], [])))})
            row["uses"][kind] += n
            row["count"] += n
    cols = sorted(table.values(), key=lambda r: -r["count"])
    return (cols, [{"value": k, "count": v} for k, v in sorted(translucent.items(), key=lambda kv: -kv[1])],
            [{"value": k, "count": v} for k, v in sorted(unparsed.items(), key=lambda kv: -kv[1])])


def kind_of(value: str) -> str:
    v = value.strip()
    if C.parse_css(v):
        return "colour"
    if v.endswith(("px", "rem", "em", "%")) or v.replace(".", "", 1).isdigit():
        return "length"
    if "," in v and any(ch.isalpha() for ch in v) and ("serif" in v or "sans" in v or "mono" in v or '"' in v or "'" in v):
        return "font"
    return "other"


def type_summary(raw: dict, faces: list):
    rows = []
    fams: dict = {}
    for key, n in raw.items():
        fam, size, weight, lh, ls, tt, tag = key.split("|")
        rows.append({"family": fam, "size": size, "weight": weight, "line_height": lh, "letter_spacing": ls, "text_transform": tt, "tag": tag, "characters": n})
        first = fam.split(",")[0].strip().strip("\"'")
        fams[first] = fams.get(first, 0) + n
    rows.sort(key=lambda r: -r["characters"])
    seen = {(f["family"], f["weight"], f["style"], f["status"]) for f in faces}
    return {"families": [{"family": k, "characters": v} for k, v in sorted(fams.items(), key=lambda kv: -kv[1])],
            "styles": rows[:40], "web_fonts_declared": [dict(family=a, weight=b, style=c, status=d) for a, b, c, d in sorted(seen)]}


def top(m: dict, n: int = 12):
    return [{"value": k, "count": v} for k, v in sorted(m.items(), key=lambda kv: -kv[1])[:n]]


DECL = re.compile(r"(?:^|[;{\s])(--[\w-]+)\s*:\s*([^;{}]+)")
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def short(href: str) -> str:
    """A stylesheet's address without its folder on this machine and without any query string."""
    u = urlparse(href)
    return os.path.basename(unquote(u.path)) if u.scheme == "file" else u._replace(query="", fragment="").geturl()


def declared_in_unreadable(ctx, page, hrefs: list):
    """Custom properties declared in stylesheets a script may not read (another origin, or a file on disk). The text is fetched the way the browser fetched it
    and read with a plain pattern, so a declaration inside an unusual construct can be missed; the resolved value comes from the browser either way."""
    found, failed = [], []
    for href in sorted(set(h for h in hrefs if h != "inline")):
        try:
            u = urlparse(href)
            if u.scheme == "file":
                with open(unquote(u.path), encoding="utf-8") as f:
                    text = f.read()
            else:
                r = ctx.request.get(href, timeout=8000)
                if not r.ok:
                    raise RuntimeError("HTTP %d" % r.status)
                text = r.text()
        except Exception:
            failed.append(short(href))
            continue
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
        for sel, body in RULE.findall(text):
            for name, value in DECL.findall(body):
                found.append({"name": name, "value": value.strip(), "selector": " ".join(sel.split())[:80], "context": "", "from": short(href)})
    if found:
        resolved = page.evaluate("(names) => { const s = getComputedStyle(document.documentElement); return names.map(n => s.getPropertyValue(n).trim()); }", [f["name"] for f in found])
        for f, r in zip(found, resolved):
            f["resolved"] = r
    return found, failed


def rendered_fonts(cdp, page, samples):
    """Which font each sample really drew its glyphs with. If the first family the page asked for is not the one used, the page fell back, and a rebuilt page that
    copies the CSS but not the font file will look different from the original."""
    out = []
    try:
        cdp.send("DOM.enable")
        cdp.send("CSS.enable")
        root = cdp.send("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
    except Exception as e:  # pragma: no cover
        return [], "the browser would not report rendered fonts: %s" % str(e)[:80]
    seen = set()
    for s in samples:
        fam = s["style"]["fontFamily"].split(",")[0].strip().strip("\"'")
        if (fam, s["kind"]) in seen:
            continue
        seen.add((fam, s["kind"]))
        try:
            nid = cdp.send("DOM.querySelector", {"nodeId": root, "selector": '[data-reqin-sample="%d"]' % s["id"]})["nodeId"]
            if not nid:
                continue
            fonts = cdp.send("CSS.getPlatformFontsForNode", {"nodeId": nid}).get("fonts", [])
        except Exception:
            continue
        used = [{"family": f.get("familyName", ""), "custom_font": bool(f.get("isCustomFont")), "glyphs": f.get("glyphCount", 0)} for f in fonts]
        want = fam.lower()
        ok = any(u["family"].lower() == want or want in u["family"].lower() for u in used) if used else None
        out.append({"kind": s["kind"], "asked_for_first": fam, "drawn_with": used, "asked_for_font_was_used": ok})
    return out, None


def read_states(page, samples, shots_dir):
    for s in samples:
        loc = page.locator('[data-reqin-sample="%d"]' % s["id"]).first
        try:
            loc.scroll_into_view_if_needed(timeout=2000)
            base = page.evaluate("(id) => (" + READ_STATE.strip() + ")(id)", s["id"])
            if shots_dir and s["id"] <= 60:
                path = os.path.join(shots_dir, "%02d_%s.png" % (s["id"], s["kind"]))
                loc.screenshot(path=path, timeout=3000)
                s["screenshot"] = os.path.basename(path)
            if s["kind"] in STATE_KINDS and base is not None and not s["style"].get("disabled"):
                states = {}
                loc.hover(timeout=1500)
                hov = page.evaluate("(id) => (" + READ_STATE.strip() + ")(id)", s["id"])
                states["hover"] = {k: [base[k], hov[k]] for k in base if base[k] != hov[k]}
                page.mouse.move(0, 0)
                page.keyboard.press("Shift")      # a key press first, so the browser treats the focus that follows as keyboard focus (:focus-visible)
                loc.evaluate("el => el.focus()")
                foc = page.evaluate("(id) => (" + READ_STATE.strip() + ")(id)", s["id"])
                states["keyboard_focus"] = {k: [base[k], foc[k]] for k in base if base[k] != foc[k]}
                loc.evaluate("el => el.blur()")
                s["states"] = states
        except Exception as e:
            s["note"] = "could not measure: " + str(e).split("\n")[0][:100]


def run(page_arg: str, width: int = 1440, height: int = 900, max_per_kind: int = 6, shots_dir: str | None = None) -> dict:
    if urlparse(page_arg).scheme in ("http", "https"):
        url, source = page_arg, urlparse(page_arg)._replace(query="", fragment="").geturl()
    else:
        path = os.path.abspath(page_arg)
        if not os.path.isfile(path):
            raise SystemExit("no such file: " + page_arg)
        url, source = "file://" + path, os.path.basename(path)
    if shots_dir:
        os.makedirs(shots_dir, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=30000)
            page.evaluate("document.fonts.ready.then(() => true)")
            raw = page.evaluate(COLLECT)
            extra, unfetched = declared_in_unreadable(ctx, page, raw["unreadable"])
            raw["declared"] += extra
            samples = page.evaluate(SAMPLES, max_per_kind)
            cdp = ctx.new_cdp_session(page)
            rendered, rendered_note = rendered_fonts(cdp, page, samples)
            read_states(page, samples, shots_dir)
        finally:
            browser.close()
    cols, translucent, unparsed = aggregate_colours(raw["uses"], raw["declared"])
    declared = [{"name": d["name"], "value": d["value"], "resolved": d.get("resolved", ""), "kind": kind_of(d.get("resolved") or d["value"]), "selector": d["selector"], "context": d["context"], **({"from": d["from"]} if d.get("from") else {})}
                for d in raw["declared"]]
    notes = []
    if unfetched:
        notes.append("stylesheets a script may not read and that could not be fetched either: %s; their custom properties are missing from declared_vars, but their effect is in the computed colours" % ", ".join(unfetched))
    if not declared:
        notes.append("the page declares no CSS custom properties: use the computed values below and name them yourself in the new design's tokens")
    notes.append("computed values are what this browser drew at %dx%d with no sign-in and no clicks; states other than hover and keyboard focus are not measured" % (width, height))
    fonts = type_summary(raw["type"], raw["faces"])
    fonts["rendered"] = rendered
    if rendered_note:
        notes.append(rendered_note)
    return {"format": "reqin-target-tokens/1", "source": source, "page": {"title": raw["title"], "lang": raw["lang"], "viewport": [width, height], "root_font_size": raw["rootFont"], "elements_read": raw["elements"]},
            "declared_vars": declared, "colours": cols, "translucent_colours": translucent, "unparsed_colours": unparsed, "type": fonts,
            "radii": top(raw["radii"]), "shadows": top(raw["shadows"]), "padding": top(raw["padding"]), "gap": top(raw["gap"]),
            "components": samples, "notes": notes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="a URL or an HTML file")
    ap.add_argument("--out", required=True, metavar="FILE")
    ap.add_argument("--shots", metavar="DIR", help="save a cropped screenshot of each sampled component here")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--max-per-kind", type=int, default=6, help="most distinct looks to keep for each kind of component")
    a = ap.parse_args(argv)
    res = run(a.page, a.width, a.height, a.max_per_kind, a.shots)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
        f.write("\n")
    fell = [r for r in res["type"]["rendered"] if r["asked_for_font_was_used"] is False]
    print("%s: %d colours, %d declared variables, %d component looks, %d font checks (%d fell back to another font)" % (
        res["source"], len(res["colours"]), len(res["declared_vars"]), len(res["components"]), len(res["type"]["rendered"]), len(fell)))
    for n in res["notes"]:
        print("  note:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
