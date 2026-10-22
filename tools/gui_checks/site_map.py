#!/usr/bin/env python3
"""Read the navigation of a page that is running: its menus, their groups and order, which item is current, the breadcrumb, the skip link, the search box, and,
by clicking each menu item once, which screen each one leads to.

    python3 tools/gui_checks/site_map.py PAGE --out site_map.json [--setup STEP ...] [--against design/navigation.json]
                                          [--no-visit] [--also LABEL ...] [--skip REGEX] [--width 1440] [--settle 400]

PAGE is a URL or an HTML file. The page is opened in a real browser (Chromium through Playwright), so what is read is what the page really holds, not what a picture of it
suggests: a picture shows the words in a menu and not where they lead.

--setup STEP    something to do before reading, in order, to get past a start screen: `click:Open the sample project` (the one button, link or text with that name; an exact match is tried first, then a name that contains it),
                `wait:500` (milliseconds), `goto:URL`. Repeat the option for more steps.
--against FILE  design/navigation.json: report every way the running page differs from the map (the menu's groups, labels and order; the title each item leads to; which item
                is current). Exit status 1 when there is any.
--no-visit      read only; click nothing.
--also LABEL    follow a menu item that is skipped by default.
--skip REGEX    skip menu items whose name matches (added to the default: delete, remove, reset, clear, sign out, log out, close project, start over, discard, erase, submit,
                send, pay, buy, confirm, publish, deploy, approve, reject). A skipped item is listed with the reason, never silently left out.

What it writes (format reqin-site-map/1): the document title, the navigation landmarks (nav, role=navigation, menubar, tablist) each with its groups (a heading that folds, or a
run of ungrouped items) and items (label, count badge, href, aria-current, disabled), the main region's headings, the breadcrumb, the skip link, the search box, the live
regions, and for each item followed: the address, document title, main heading, breadcrumb text and current item after the click.

What it does not do: it follows menu items only, once each, and no control inside a screen (a button on one screen that opens another is in the navigation map, written by a
person from the source or by looking); it does not sign in; it does not see an item that only appears after hover, after a role change or at another width; a group nested in a
group is read as an item of the outer one; and an item that opens a panel and not a screen shows as "no visible change" when the title, heading, breadcrumb and current item stay the same (the address is reported separately).
Needs Playwright with a Chromium browser:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import urlparse

DEFAULT_SKIP = r"\b(delete|remove|reset|clear|sign[ -]?out|log[ -]?out|close project|start over|discard|erase|submit|send|pay|buy|purchase|confirm|publish|deploy|approve|reject)\b"
FORMAT = "reqin-site-map/1"

# Everything that can be read without clicking, in one go. Run again after each click.
READ = r"""
() => {
  const INTERACTIVE = 'a[href], button, [role="menuitem"], [role="tab"], [role="link"], summary';
  const LANDMARKS = 'nav, [role="navigation"], [role="menubar"], [role="tablist"]';
  const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
  const shown = (el) => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const nameOf = (el) => {
    const a = el.getAttribute('aria-label'); if (a && norm(a)) return norm(a);
    const lb = el.getAttribute('aria-labelledby');
    if (lb) { const t = lb.split(/\s+/).map((i) => document.getElementById(i)).filter(Boolean).map((x) => x.textContent).join(' '); if (norm(t)) return norm(t); }
    return '';
  };
  const BADGE = '[class*="count" i], [class*="badge" i]';
  const textOf = (el) => {
    const c = el.cloneNode(true);
    c.querySelectorAll(BADGE + ', svg, [aria-hidden="true"]').forEach((x) => x.remove());
    return norm(c.textContent);
  };
  const itemOf = (e) => {
    const b = e.querySelector(BADGE);
    const cur = e.getAttribute('aria-current');
    return {
      label: textOf(e) || nameOf(e) || norm(e.getAttribute('title')),
      accessible_name: nameOf(e),
      badge: b ? norm(b.textContent) : '',
      tag: e.tagName.toLowerCase(),
      role: e.getAttribute('role') || '',
      href: e.getAttribute('href'),
      current: cur && cur !== 'false' ? cur : '',
      selected: e.getAttribute('aria-selected') === 'true',
      disabled: !!e.disabled || e.getAttribute('aria-disabled') === 'true'
    };
  };
  const readLandmark = (L) => {
    const els = [...L.querySelectorAll(INTERACTIVE)].filter(shown);
    const isExp = (e) => e.hasAttribute('aria-expanded');
    const exps = els.filter(isExp);
    const cont = new Map();
    for (const E of exps) { const id = E.getAttribute('aria-controls'); cont.set(E, (id && document.getElementById(id)) || E.parentElement); }
    const owner = new Map();
    [...exps].sort((a, b) => cont.get(a).querySelectorAll('*').length - cont.get(b).querySelectorAll('*').length).forEach((E) => {
      cont.get(E).querySelectorAll(INTERACTIVE).forEach((x) => { if (x !== E && !isExp(x) && !owner.has(x)) owner.set(x, E); });
    });
    const groups = [], groupFor = new Map();
    let cur = null;
    for (const e of els) {
      if (isExp(e)) {
        const g = {heading: textOf(e) || nameOf(e), expandable: true, expanded: e.getAttribute('aria-expanded') === 'true', items: []};
        groups.push(g); groupFor.set(e, g); cur = null; continue;
      }
      const o = owner.get(e);
      if (o && groupFor.has(o)) { groupFor.get(o).items.push(itemOf(e)); cur = null; continue; }
      if (!cur) { cur = {heading: null, expandable: false, items: []}; groups.push(cur); }
      cur.items.push(itemOf(e));
    }
    return {name: nameOf(L) || '', tag: L.tagName.toLowerCase(), role: L.getAttribute('role') || '', groups};
  };
  const lms = [...document.querySelectorAll(LANDMARKS)].filter(shown);
  const main = document.querySelector('main, [role="main"]');
  const scope = main || document;
  const heads = [...scope.querySelectorAll('h1, h2')].filter(shown).map((h) => norm(h.textContent)).slice(0, 4);
  const bc = [...document.querySelectorAll('nav[aria-label*="readcrumb" i], [aria-label="breadcrumb" i], .breadcrumb, [class*="crumb" i]')].filter(shown)[0];
  const skip = [...document.querySelectorAll('a[href^="#"]')].find((a) => /skip/i.test(a.textContent));
  const search = document.querySelector('input[type="search"], [role="search"] input, input[aria-label*="earch" i]');
  const live = [...document.querySelectorAll('[role="status"], [aria-live]')].map((x) => norm(x.textContent)).filter(Boolean);
  const cur = [];
  lms.forEach((L) => L.querySelectorAll(INTERACTIVE).forEach((e) => { const c = e.getAttribute('aria-current'); if ((c && c !== 'false') || e.getAttribute('aria-selected') === 'true') cur.push(textOf(e) || nameOf(e)); }));
  return {
    title: document.title, url: location.href, landmarks: lms.map(readLandmark),
    main: {present: !!main, id: main ? main.id : '', headings: heads, interactive: scope.querySelectorAll(INTERACTIVE).length},
    breadcrumb: bc ? norm(bc.textContent) : '',
    skip_link: skip ? {text: norm(skip.textContent), target: skip.getAttribute('href'), target_exists: !!document.getElementById((skip.getAttribute('href') || '').slice(1))} : null,
    search: search ? {label: nameOf(search) || search.getAttribute('placeholder') || '', type: search.type} : null,
    live, current: cur
  };
}
"""

# the k-th interactive element, not a folding heading, that is shown inside the i-th landmark, found again from the page each time (a page may redraw)
NTH = r"""
([i, k]) => {
  const INTERACTIVE = 'a[href], button, [role="menuitem"], [role="tab"], [role="link"], summary';
  const shown = (el) => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const L = [...document.querySelectorAll('nav, [role="navigation"], [role="menubar"], [role="tablist"]')].filter(shown)[i];
  if (!L) return null;
  return [...L.querySelectorAll(INTERACTIVE)].filter(shown).filter((e) => !e.hasAttribute('aria-expanded'))[k] || null;
}
"""

# open every folded group in every landmark; returns how many were opened
EXPAND = r"""
() => {
  const shown = (el) => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  let n = 0;
  document.querySelectorAll('nav, [role="navigation"], [role="menubar"], [role="tablist"]').forEach((L) => {
    if (!shown(L)) return;
    L.querySelectorAll('[aria-expanded="false"]').forEach((e) => { if (shown(e)) { e.click(); n++; } });
  });
  return n;
}
"""


def run_setup(page, steps: list[str], settle: int = 400) -> None:
    for step in steps or []:
        kind, _, arg = step.partition(":")
        if kind == "wait":
            page.wait_for_timeout(int(arg))
        elif kind == "goto":
            page.goto(arg, wait_until="load")
        elif kind == "click":
            for loc in (page.get_by_role("button", name=arg, exact=True), page.get_by_role("link", name=arg, exact=True), page.get_by_text(arg, exact=True),
                        page.get_by_role("button", name=arg), page.get_by_role("link", name=arg)):
                if loc.count() == 1:
                    loc.first.click()
                    break
            else:
                raise SystemExit("setup step %r: no single button, link or text on the page has that name (exactly, or as part of its name)" % step)
            page.wait_for_timeout(settle)
        else:
            raise SystemExit("setup step %r: say click:NAME, wait:MS or goto:URL" % step)


def _path(url: str) -> str:
    u = urlparse(url)
    return u._replace(fragment="").geturl()


def _state(snap: dict) -> dict:
    return {"url": snap["url"], "title": snap["title"], "heading": (snap["main"]["headings"] or [""])[0], "breadcrumb": snap["breadcrumb"], "current": snap["current"],
            "live": snap["live"][:2], "interactive_in_main": snap["main"]["interactive"]}


def read_site_map(page, setup: list[str] | None = None, visit: bool = True, skip: str = DEFAULT_SKIP, also: tuple = (), settle: int = 400, max_items: int = 80,
                  start_url: str | None = None, ignore: str = "") -> dict:
    """Read the navigation of the page as it is now (after `setup`, if it was not run yet), and follow each menu item once. `page` is an open Playwright page."""
    if setup:
        run_setup(page, setup, settle)
    start_url = start_url or page.url
    opened = page.evaluate(EXPAND)
    if opened:
        page.wait_for_timeout(150)
    base = page.evaluate(READ)
    notes = []
    if opened:
        notes.append("opened %d folded group(s) to read their items; they were folded when the page was opened" % opened)
    skip_re = re.compile(skip, re.I)
    ignore_re = re.compile(ignore) if ignore else None
    also_l = {a.lower() for a in also}
    followed = 0
    for li, lm in enumerate(base["landmarks"]):
        k = -1
        for g in lm["groups"]:
            for it in g["items"]:
                k += 1
                if not visit:
                    continue
                name = it["accessible_name"] or it["label"]
                href = it["href"] or ""
                why = None
                if ignore_re and ignore_re.search(it["label"]):
                    why = "excluded by --ignore (the map says it exists only in the prototype)"
                elif it["disabled"]:
                    why = "disabled"
                elif name.lower() not in also_l and it["label"].lower() not in also_l:
                    if skip_re.search(name) or skip_re.search(it["label"]):
                        why = "its name suggests it changes something or leaves this menu; follow it by hand or name it with --also"
                    elif re.match(r"^(mailto:|tel:|javascript:)", href, re.I):
                        why = "not a page"
                    elif re.match(r"^https?://", href, re.I) and urlparse(href).netloc != urlparse(start_url).netloc:
                        why = "another site"
                if why is None and followed >= max_items:
                    why = "more than %d items: the rest are listed and not followed" % max_items
                if why:
                    it["not_followed"] = why
                    continue
                before = _state(page.evaluate(READ))
                handle = page.evaluate_handle(NTH, [li, k])
                el = handle.as_element()
                if el is None:
                    it["not_followed"] = "the page redrew and the item could not be found again"
                    continue
                try:
                    el.click(timeout=4000)
                except Exception as e:  # a covered or detached element: say so, do not guess
                    it["not_followed"] = "click failed: %s" % str(e).splitlines()[0][:100]
                    continue
                page.wait_for_timeout(settle)
                after_snap = page.evaluate(READ)
                after = _state(after_snap)
                followed += 1
                it["leads_to"] = {x: after[x] for x in ("url", "title", "heading", "breadcrumb", "current")}
                it["leads_to"]["no_visible_change"] = (after["title"], after["heading"], after["breadcrumb"], after["current"]) == (before["title"], before["heading"], before["breadcrumb"], before["current"])
                it["leads_to"]["address_changed"] = after["url"] != before["url"]
                it["leads_to"]["marks_itself_current"] = bool(after["current"]) and (it["label"] in after["current"] or name in after["current"])
                if _path(after["url"]) != _path(before["url"]):
                    it["leads_to"]["new_document"] = True
                    page.goto(start_url, wait_until="load")
                    run_setup(page, setup, settle)
                    page.evaluate(EXPAND)
    final = page.evaluate(READ)
    screens = {}
    for lm in base["landmarks"]:
        for g in lm["groups"]:
            for it in g["items"]:
                lt = it.get("leads_to")
                if lt and not lt["no_visible_change"]:
                    screens.setdefault((lt["title"], lt["heading"]), []).append(it["label"])
    notes.append("only menu items were followed, once each; controls inside a screen were not")
    return {"format": FORMAT, "source": _path(start_url), "document_title": base["title"], "landmarks": base["landmarks"], "main": base["main"], "breadcrumb": base["breadcrumb"],
            "skip_link": base["skip_link"], "search": base["search"], "live_regions": base["live"], "current_at_start": base["current"],
            "screens_seen": [{"title": t, "heading": h, "reached_by": v} for (t, h), v in screens.items()], "notes": notes,
            "followed": followed, "final_title": final["title"]}


# ---------------------------------------------------------------------------------------------------- against the navigation map
def expected_groups(nav: dict) -> list:
    """[(heading or None, [labels])] in the order a reader of the page meets them: the groups, then the foot."""
    sb = (nav.get("shell") or {}).get("side_bar") or {}
    out = [(g.get("heading"), [it["label"] for it in g.get("items", [])]) for g in sb.get("groups", [])]
    foot = [it["label"] for it in sb.get("foot", [])]
    if foot:
        out.append((None, foot))
    return out


def compare_with_navigation(sm: dict, nav: dict) -> list[str]:
    """Every way the running page differs from design/navigation.json. Empty when it agrees. Needs the page to have been followed (not --no-visit) to compare what items lead to."""
    out: list[str] = []
    sb = (nav.get("shell") or {}).get("side_bar") or {}
    want_name = sb.get("label")
    lm = next((l for l in sm["landmarks"] if l["name"] == want_name), None)
    if lm is None:
        names = [l["name"] or "(no name)" for l in sm["landmarks"]]
        return ["no navigation landmark named %r on the page (found: %s)" % (want_name, ", ".join(names) or "none")]
    only = [re.compile(x) for x in sb.get("prototype_only_labels", []) or []]
    got = [(g["heading"], [i["label"] for i in g["items"] if not any(p.search(i["label"]) for p in only)]) for g in lm["groups"]]
    got = [g for g in got if g[1] or g[0]]
    want = expected_groups(nav)
    if len(got) != len(want):
        out.append("the menu has %d groups on the page and %d in the map: page %s, map %s" % (len(got), len(want), got, want))
    for n, (g, w) in enumerate(zip(got, want)):
        if g[0] != w[0]:
            out.append("menu group %d is headed %r on the page and %r in the map" % (n + 1, g[0], w[0]))
        if g[1] != w[1]:
            out.append("menu group %d (%s) holds %s on the page and %s in the map (the order counts)" % (n + 1, w[0] or "no heading", g[1], w[1]))
    for n, g in enumerate(sb.get("groups", [])):
        if g.get("collapsible"):
            page_g = next((x for x in lm["groups"] if x["heading"] == g.get("heading")), None)
            if page_g is not None and not page_g["expandable"]:
                out.append("the map says the group %r folds and on the page it does not" % g.get("heading"))
    screens = {s["id"]: s for s in nav.get("screens", [])}
    by_label = {it["label"]: it for gr in sb.get("groups", []) for it in gr.get("items", [])}
    suffix = ((nav.get("shell") or {}).get("page_title") or {}).get("document_title", "<screen title>").replace("<screen title>", "")
    for g in lm["groups"]:
        for it in g["items"]:
            if any(p.search(it["label"]) for p in only):
                continue
            m = by_label.get(it["label"])
            lt = it.get("leads_to")
            if m is None or lt is None:
                continue
            title = screens[m["screen"]]["title"]
            if lt["title"] != title + suffix:
                out.append("%r leads to a page titled %r; the map says %r" % (it["label"], lt["title"], title + suffix))
            if title not in lt["breadcrumb"]:
                out.append("%r leads to a screen whose breadcrumb is %r; it should name %r" % (it["label"], lt["breadcrumb"], title))
            if not lt["marks_itself_current"]:
                out.append("%r leads to a screen where it is not marked current (aria-current); current is %s" % (it["label"], lt["current"] or "nothing"))
            if it["current"] and it["current"] != "page":
                out.append("%r is marked current with aria-current=%r; the map says page" % (it["label"], it["current"]))
    if sm.get("followed", 0) == 0:
        out.append("no menu item was followed, so what each leads to was not compared")
    sl = (nav.get("shell") or {}).get("skip_link")
    if sl and (sm["skip_link"] or {}).get("text") != sl["label"]:
        out.append("the skip link says %r on the page and %r in the map" % ((sm["skip_link"] or {}).get("text"), sl["label"]))
    elif sm["skip_link"] and not sm["skip_link"]["target_exists"]:
        out.append("the skip link points at %r and nothing on the page has that id" % sm["skip_link"]["target"])
    se = ((nav.get("shell") or {}).get("top_bar") or {}).get("search")
    if se and (sm["search"] or {}).get("label") != se["label"]:
        out.append("the search box is labelled %r on the page and %r in the map" % ((sm["search"] or {}).get("label"), se["label"]))
    return out


# ---------------------------------------------------------------------------------------------------- command line
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page", help="a URL or an HTML file")
    ap.add_argument("--out", required=True, metavar="FILE")
    ap.add_argument("--setup", action="append", default=[], metavar="STEP")
    ap.add_argument("--against", metavar="FILE", help="design/navigation.json")
    ap.add_argument("--no-visit", action="store_true")
    ap.add_argument("--also", action="append", default=[], metavar="LABEL")
    ap.add_argument("--skip", default="", metavar="REGEX")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--settle", type=int, default=400)
    a = ap.parse_args(argv)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("site_map.py needs Playwright: pip install playwright && playwright install chromium")
    if urlparse(a.page).scheme in ("http", "https"):
        url = a.page
    else:
        path = os.path.abspath(a.page)
        if not os.path.isfile(path):
            raise SystemExit("no such file: " + a.page)
        url = "file://" + path
    skip = DEFAULT_SKIP if not a.skip else "(%s)|(%s)" % (DEFAULT_SKIP, a.skip)
    ignore = ""
    if a.against:
        pats = (((json.load(open(a.against, encoding="utf-8")).get("shell") or {}).get("side_bar") or {}).get("prototype_only_labels")) or []
        ignore = "|".join("(%s)" % x for x in pats)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            ctx = browser.new_context(viewport={"width": a.width, "height": a.height})
            page = ctx.new_page()
            page.goto(url, wait_until="load", timeout=30000)
            sm = read_site_map(page, setup=a.setup, visit=not a.no_visit, skip=skip, also=tuple(a.also), settle=a.settle, start_url=url, ignore=ignore)
        finally:
            browser.close()
    findings = []
    if a.against:
        nav = json.load(open(a.against, encoding="utf-8"))
        findings = compare_with_navigation(sm, nav)
        sm["against"] = {"file": a.against, "differences": findings}
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(sm, f, indent=2)
    n_items = sum(len(g["items"]) for l in sm["landmarks"] for g in l["groups"])
    print("%s: %d navigation landmark(s), %d item(s), %d followed" % (a.page, len(sm["landmarks"]), n_items, sm["followed"]))
    for f_ in findings:
        print("  differs: " + f_)
    if a.against:
        print("against %s: %s" % (a.against, "agrees" if not findings else "%d difference(s)" % len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
