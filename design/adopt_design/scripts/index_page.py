#!/usr/bin/env python3
"""Take a page or an app apart and write down what it is made of: its theme, its components, its menus, and the role each colour, font and corner plays.

    python3 scripts/index_page.py PAGE --out mine/ [--width 1440] [--height 900] [--setup "click:Open the sample project"] [--max-per-kind 6]

PAGE is a URL (http, https) or an HTML file on disk. The page is opened in a real browser (Chromium through Playwright) and what is read is what the browser computed.
--setup gets an app to the state you want indexed (the same steps tools/gui_checks/site_map.py takes: "click:Label", "fill:Label=text", "wait:500", "goto:URL"); repeat it.

It writes, into the --out folder:
  index.json   format reqin-page-index/1: declared --variables, every colour and what it is used for, fonts (and whether each rendered or fell back), radii, shadows, spacing,
               breakpoints, each kind of component with its distinct looks (and a selector that finds them again), the menus and headings the page shows, whether menu items
               and buttons carry icons, and the roles (roles.json) with how each was read
  INDEX.md     the same, in words, for a person to read and correct
  regions/     a picture of each big part of the page (header, side menu, main area, ...)
  shots/       a picture of each sampled component

Not read: anything that only shows after a click, a hover or a sign-in that --setup did not do; styles inside cross-origin stylesheets or shadow roots; gradients and images; a
second theme (dark mode) the page has but is not showing; what the designer meant. Everything that is a guess says so in the roles table.
Needs Playwright with a Chromium browser:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import C, REPO, write_json  # noqa: E402
import roles as R  # noqa: E402
import target_tokens as TT  # noqa: E402
import site_map as SM  # noqa: E402

FORMAT = "reqin-page-index/1"
GENERIC_FAMILIES = {"sans-serif", "serif", "monospace", "system-ui", "cursive", "fantasy", "ui-sans-serif", "ui-serif", "ui-monospace", "ui-rounded"}
KEYS = ["color", "backgroundColor", "borderTopColor", "borderTopWidth", "borderTopStyle", "borderTopLeftRadius", "paddingTop", "paddingRight", "fontFamily", "fontSize", "fontWeight",
        "lineHeight", "letterSpacing", "textTransform", "textDecorationLine", "boxShadow", "height", "minHeight"]     # the same keys target_tokens.py reads, so the two can be matched

EXTRA = r"""
(spec) => {
  const KINDS = spec.kinds, KEYS = spec.keys;
  const alphaOf = v => { const m = v.match(/^rgba?\(([^)]*)\)/); if (!m) return 1; const p = m[1].split(/[ ,\/]+/).filter(Boolean); return p.length > 3 ? parseFloat(p[3]) : 1; };
  const shown = el => { const r = el.getBoundingClientRect(); const cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const isCard = (el, cs, r) => r.width >= 200 && r.height >= 60 && alphaOf(cs.backgroundColor) > 0 && parseFloat(cs.borderTopLeftRadius) > 0 && (parseFloat(cs.borderTopWidth) > 0 || cs.boxShadow !== 'none');
  const out = {body: {}, codeFonts: [], selectedBackgrounds: [], icons: {}, breakpoints: [], selectors: {}, regions: []};
  const bs = getComputedStyle(document.body), hs = getComputedStyle(document.documentElement);
  out.body = {color: bs.color, backgroundColor: bs.backgroundColor, htmlBackground: hs.backgroundColor, fontFamily: bs.fontFamily, fontSize: bs.fontSize, lineHeight: bs.lineHeight};
  const fams = new Map();
  for (const el of document.body.querySelectorAll('code, pre, kbd, samp, tt')) if (shown(el)) fams.set(getComputedStyle(el).fontFamily, (fams.get(getComputedStyle(el).fontFamily) || 0) + 1);
  out.codeFonts = [...fams.entries()].sort((a, b) => b[1] - a[1]).map(e => e[0]);
  const sel = new Map();
  for (const el of document.body.querySelectorAll('[aria-current]:not([aria-current=false]), [aria-selected=true], .active, .selected, .current')) {
    if (!shown(el)) continue; const cs = getComputedStyle(el);
    if (alphaOf(cs.backgroundColor) > 0.99) sel.set(cs.backgroundColor, (sel.get(cs.backgroundColor) || 0) + 1);
  }
  out.selectedBackgrounds = [...sel.entries()].sort((a, b) => b[1] - a[1]).map(e => ({value: e[0], count: e[1]}));
  const iconIn = el => !!el.querySelector('svg, img, i[class], [class*=icon]');
  const navItems = [...document.body.querySelectorAll('nav a, nav button, [role=navigation] a, [role=navigation] button, [role=menuitem], [role=tab]')].filter(shown);
  const btns = [...document.body.querySelectorAll('button, [role=button], input[type=button], input[type=submit]')].filter(shown).filter(b => (b.innerText || b.value || '').trim());
  out.icons = {nav_items: navItems.length, nav_items_with_icon: navItems.filter(iconIn).length, buttons: btns.length, buttons_with_icon: btns.filter(iconIn).length};
  const bp = new Set();
  const walk = rules => { for (const r of rules) { if (r.media) { for (const m of r.media.mediaText.matchAll(/\((?:min|max)-width:\s*([0-9.]+)px\)/g)) bp.add(parseFloat(m[1])); } if (r.cssRules) walk(r.cssRules); } };
  for (const sheet of document.styleSheets) { try { walk(sheet.cssRules); } catch (e) {} }
  out.breakpoints = [...bp].sort((a, b) => a - b);
  const bestSelector = (els) => {
    const set = new Set(els), cands = new Set();
    for (const el of els.slice(0, 12)) {
      const tag = el.tagName.toLowerCase(); cands.add(tag);
      for (const c of el.classList) { if (!/^[A-Za-z_-][\w-]*$/.test(c)) continue; cands.add('.' + c); cands.add(tag + '.' + c); }
    }
    let best = null;
    for (const s of cands) {
      let m; try { m = [...document.querySelectorAll(s)].filter(shown); } catch (e) { continue; }
      const inter = m.filter(x => set.has(x)).length, union = new Set([...m, ...els]).size, j = inter / union;
      if (!best || j > best.jaccard + 1e-9 || (Math.abs(j - best.jaccard) < 1e-9 && s.length < best.selector.length)) best = {selector: s, jaccard: Math.round(j * 100) / 100, matches: m.length, group: els.length};
    }
    return best;
  };
  for (const [kind, q] of Object.entries(KINDS)) {
    const groups = new Map();
    for (const el of document.body.querySelectorAll(q)) {
      if (!shown(el)) continue;
      const cs = getComputedStyle(el), r = el.getBoundingClientRect();
      if (kind === 'card' && !isCard(el, cs, r)) continue;
      const style = {}; for (const k of KEYS) style[k] = cs[k];
      style.disabled = !!el.disabled;
      const sig = JSON.stringify(style);
      (groups.get(sig) || groups.set(sig, []).get(sig)).push(el);
    }
    for (const [sig, els] of groups) out.selectors[kind + '|' + sig] = bestSelector(els);
  }
  const regionQ = 'header, nav, main, aside, footer, [role=banner], [role=navigation], [role=main], [role=complementary], [role=contentinfo]';
  let n = 0;
  for (const el of document.body.querySelectorAll(regionQ)) {
    if (!shown(el) || n >= 8) continue; const r = el.getBoundingClientRect();
    if (r.width < 80 || r.height < 40) continue;
    el.setAttribute('data-adopt-region', String(++n));
    const role = el.getAttribute('role') || ({HEADER: 'banner', NAV: 'navigation', MAIN: 'main', ASIDE: 'complementary', FOOTER: 'contentinfo'}[el.tagName]) || el.tagName.toLowerCase();
    out.regions.push({n, role, label: el.getAttribute('aria-label') || '', tag: el.tagName.toLowerCase(), box: [Math.round(r.x), Math.round(r.y + scrollY), Math.round(r.width), Math.round(r.height)], selector: (bestSelector([el]) || {}).selector || el.tagName.toLowerCase()});
  }
  return out;
}
"""

KINDS = {
    "button": "button, [role=button], input[type=button], input[type=submit], a[class*=btn], a[class*=button]",
    "link": "a[href]",
    "input": "input:not([type=checkbox]):not([type=radio]):not([type=button]):not([type=submit]):not([type=hidden]), textarea, select",
    "heading": "h1, h2, h3, h4, h5, h6",
    "table_cell": "th, td",
    "badge": "[class*=badge], [class*=chip], [class*=pill], [class*=tag], [class*=status]",
    "nav_item": "nav a, [role=navigation] a, [role=tab], [role=menuitem]",
    "card": "*",
}


def _relativise(obj, prefix: str):
    """Write addresses of a page opened from disk without the folder it was opened from, so an index can be shared or kept in a repository without a machine's path in it."""
    if isinstance(obj, str):
        return obj.replace(prefix, "")
    if isinstance(obj, list):
        return [_relativise(x, prefix) for x in obj]
    if isinstance(obj, dict):
        return {k: _relativise(v, prefix) for k, v in obj.items()}
    return obj


def _sig(style: dict) -> str:
    return json.dumps(style, separators=(",", ":"), ensure_ascii=False)


def run(page_arg: str, out_dir: str, width: int = 1440, height: int = 900, setup: list | None = None, max_per_kind: int = 6) -> dict:
    from playwright.sync_api import sync_playwright
    if urlparse(page_arg).scheme in ("http", "https"):
        url, source = page_arg, urlparse(page_arg)._replace(query="", fragment="").geturl()
    else:
        path = os.path.abspath(page_arg)
        if not os.path.isfile(path):
            raise SystemExit("no such file: " + page_arg)
        url, source = "file://" + path, os.path.basename(path)
    out = Path(out_dir)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    (out / "regions").mkdir(parents=True, exist_ok=True)
    notes: list = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": width, "height": height})
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=30000)
            page.evaluate("document.fonts.ready.then(() => true)")
            if setup:
                SM.run_setup(page, setup)
                page.evaluate("document.fonts.ready.then(() => true)")
            raw = page.evaluate(TT.COLLECT)
            extra_decl, unfetched = TT.declared_in_unreadable(ctx, page, raw["unreadable"])
            raw["declared"] += extra_decl
            samples = page.evaluate(TT.SAMPLES, max_per_kind)
            cdp = ctx.new_cdp_session(page)
            rendered, rendered_note = TT.rendered_fonts(cdp, page, samples)
            TT.read_states(page, samples, str(out / "shots"))
            extra = page.evaluate(EXTRA, {"kinds": KINDS, "keys": KEYS})
            for r in extra["regions"]:
                try:
                    page.locator('[data-adopt-region="%d"]' % r["n"]).first.screenshot(path=str(out / "regions" / ("%02d_%s.png" % (r["n"], r["role"]))), timeout=4000)
                    r["picture"] = "regions/%02d_%s.png" % (r["n"], r["role"])
                except Exception as e:                                          # a region too tall, hidden by a transform...
                    r["picture"] = None
                    notes.append("could not take a picture of the %s region: %s" % (r["role"], str(e).split("\n")[0][:80]))
            try:
                structure = SM.read_site_map(page, visit=False)
                if url.startswith("file://"):
                    structure = _relativise(structure, url.rsplit("/", 1)[0] + "/")
            except Exception as e:
                structure = None
                notes.append("could not read the menus: %s" % str(e).split("\n")[0][:100])
        finally:
            browser.close()
    cols, translucent, unparsed = TT.aggregate_colours(raw["uses"], raw["declared"])
    declared = [{"name": d["name"], "value": d["value"], "resolved": d.get("resolved", ""), "kind": TT.kind_of(d.get("resolved") or d["value"]), "selector": d["selector"], "context": d["context"]} for d in raw["declared"]]
    fonts = TT.type_summary(raw["type"], raw["faces"])
    fonts["rendered"] = rendered
    by_sig = {k.split("|", 1)[1] + "|" + k.split("|", 1)[0]: v for k, v in extra["selectors"].items()}
    unmatched = 0
    for c in samples:
        sel = by_sig.get(_sig(c["style"]) + "|" + c["kind"])
        if sel:
            c["selector"] = sel
        else:
            unmatched += 1
    if unmatched:
        notes.append("%d sampled component looks could not be matched to a selector" % unmatched)
    if unfetched:
        notes.append("stylesheets that could not be read: %s; their custom properties are missing from declared_vars" % ", ".join(TT.short(h) for h in unfetched))
    if rendered_note:
        notes.append(rendered_note)
    if not declared:
        notes.append("the page declares no CSS custom properties: the adopted theme cannot be bridged to your variables, only to your selectors")
    notes.append("what this browser drew at %dx%d%s; a second theme, an open menu or anything behind a click or sign-in that was not set up is not read" % (width, height, " after the setup steps" if setup else ""))
    ix = {"format": FORMAT, "source": source, "taken": {"width": width, "height": height, "setup": setup or []},
          "page": {"title": raw["title"], "lang": raw["lang"], "root_font_size": raw["rootFont"], "elements_read": raw["elements"]},
          "body": extra["body"], "declared_vars": declared, "colours": cols, "translucent_colours": translucent, "unparsed_colours": unparsed, "type": fonts,
          "radii": TT.top(raw["radii"]), "shadows": TT.top(raw["shadows"]), "padding": TT.top(raw["padding"]), "gap": TT.top(raw["gap"]),
          "components": samples,
          "extra": {"codeFonts": extra["codeFonts"], "selectedBackgrounds": extra["selectedBackgrounds"], "icons": extra["icons"], "breakpoints": extra["breakpoints"]},
          "regions": extra["regions"], "structure": structure, "notes": notes}
    ix["roles"] = R.read_mine(ix)
    return ix


# ------------------------------------------------------------------------------------------------ the page for people
def _swatch(v):
    return "`%s`" % v if v else "-"


def render_md(ix: dict) -> str:
    L = []
    w = L.append
    ics = ix["extra"]["icons"]
    w("# What was read from %s" % ix["source"])
    w("")
    w("Read with a real browser at %d x %d%s. Everything below is what the browser computed. **Roles marked guess or missing are for you to confirm or correct.**" % (
        ix["taken"]["width"], ix["taken"]["height"], " after: " + "; ".join(ix["taken"]["setup"]) if ix["taken"]["setup"] else ""))
    w("")
    w("## 1. The roles (the short list that is compared with our design)")
    w("")
    w("| Role | Value | How it was read | Sure? |")
    w("|---|---|---|---|")
    for r in R.ROLES["roles"]:
        v = ix["roles"].get(r["id"], {})
        w("| %s (%s) | %s | %s | %s |" % (r["label"], r["plain"], _swatch(v.get("value")) if v.get("value") else "not found", v.get("how", ""), v.get("confidence", "missing")))
    w("")
    w("## 2. Fonts")
    w("")
    fam = ix["type"]["families"]
    w("In use, most text first: %s." % (", ".join("%s (%d characters)" % (f["family"], f["characters"]) for f in fam[:5]) or "none read"))
    seen: dict = {}
    for r in ix["type"].get("rendered", []):
        seen.setdefault(r.get("asked_for_first"), (r.get("asked_for_font_was_used"), (r.get("drawn_with") or [{}])[0].get("family", "?")))
    for name, (used, drawn) in seen.items():
        if name in GENERIC_FAMILIES:
            w("- %s: a generic family, so each machine picks the font; this one drew it in %s" % (name, drawn))
        elif used:
            w("- %s: drawn in the font it asks for" % name)
        else:
            w("- %s: asked for, but this machine does not have it, so it was drawn in %s. A picture made here will use that stand-in" % (name, drawn))
    w("")
    w("## 3. Palette")
    w("")
    w("| Colour | Text | Background | Border | Icon | Your variable names for it |")
    w("|---|---|---|---|---|---|")
    for c in ix["colours"][:16]:
        w("| `%s` | %d | %d | %d | %d | %s |" % (c["hex"], c["uses"]["text"], c["uses"]["background"], c["uses"]["border"], c["uses"]["icon"], ", ".join("`%s`" % n for n in c["names"]) or "none"))
    w("")
    w("Radii: %s. Shadows: %s. Padding values: %s. Breakpoints: %s." % (
        ", ".join("%s (%d)" % (x["value"], x["count"]) for x in ix["radii"][:5]) or "none", "; ".join("%s (%d)" % (x["value"], x["count"]) for x in ix["shadows"][:3]) or "none",
        ", ".join("%s" % x["value"] for x in ix["padding"][:6]) or "none", ", ".join("%gpx" % b for b in ix["extra"]["breakpoints"]) or "none declared"))
    w("")
    w("## 4. Components (distinct looks, commonest first)")
    w("")
    w("| Kind | Looks like | On the page | Found again with | Picture |")
    w("|---|---|---|---|---|")
    for c in ix["components"]:
        st = c["style"]
        look = "%s on %s, %s text, corner %s%s" % (st.get("color"), st.get("backgroundColor"), st.get("fontSize"), (st.get("borderTopLeftRadius") or "0").split()[0], "" if st.get("boxShadow") in (None, "none") else ", shadow")
        sel = c.get("selector")
        found = ("`%s` (%d%% exact)" % (sel["selector"], round(sel["jaccard"] * 100))) if sel else "no selector"
        w("| %s | %s | %d (%r) | %s | %s |" % (c["kind"], look, c["count"], c.get("text", "")[:24], found, ("shots/" + c["screenshot"]) if c.get("screenshot") else "-"))
    w("")
    w("## 5. Menus and structure")
    w("")
    st = ix.get("structure")
    if st:
        for lm in st["landmarks"]:
            w("- **%s**: %s" % (lm["name"] or "(unnamed navigation)", "; ".join("%s: %s" % (g["heading"] or "(no heading)", ", ".join(i["label"] for i in g["items"][:12])) for g in lm["groups"]) or "no items"))
        w("- Headings in the main area: %s" % (", ".join(st["main"]["headings"]) or "none"))
    else:
        w("- The menus could not be read (see the notes).")
    w("- Icons: %d of %d menu items carry one; %d of %d buttons carry one." % (ics["nav_items_with_icon"], ics["nav_items"], ics["buttons_with_icon"], ics["buttons"]))
    for r in ix["regions"]:
        w("- Region %d, %s%s: %s (%s)" % (r["n"], r["role"], " \"%s\"" % r["label"] if r["label"] else "", "%d x %d" % (r["box"][2], r["box"][3]), r.get("picture") or "no picture"))
    w("")
    w("## 6. Not read")
    w("")
    for n in ix["notes"]:
        w("- " + n)
    w("- Which element you meant as the main button when there are several: the one the page uses most with a colour is taken. Correct it if that is wrong.")
    w("")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="a URL or an HTML file")
    ap.add_argument("--out", required=True, metavar="DIR")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--setup", action="append", default=[], metavar="STEP", help='a step to take before reading, for example "click:Open the sample project"; repeat for more')
    ap.add_argument("--max-per-kind", type=int, default=6)
    a = ap.parse_args(argv)
    ix = run(a.page, a.out, a.width, a.height, a.setup, a.max_per_kind)
    write_json(Path(a.out) / "index.json", ix)
    (Path(a.out) / "INDEX.md").write_text(render_md(ix), encoding="utf-8")
    conf = {}
    for v in ix["roles"].values():
        conf[v["confidence"]] = conf.get(v["confidence"], 0) + 1
    print("%s: %d colours, %d component looks, %d roles (%s)" % (ix["source"], len(ix["colours"]), len(ix["components"]), len(ix["roles"]), ", ".join("%d %s" % (n, k) for k, n in sorted(conf.items()))))
    print("wrote %s and %s" % (Path(a.out) / "index.json", Path(a.out) / "INDEX.md"))
    for n in ix["notes"]:
        print("  note:", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
