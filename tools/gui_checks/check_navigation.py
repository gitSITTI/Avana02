#!/usr/bin/env python3
"""Check the navigation map (format reqin-navigation/1) and, optionally, check it against the prototype's source.

    python3 tools/gui_checks/check_navigation.py [design/navigation.json] [--data-map docs/SCREEN_DATA_MAP.md] [--prototype prototype]
                                                 [--write-doc docs/NAVIGATION_MAP.md | --check-doc docs/NAVIGATION_MAP.md] [--json report.json]

A picture of a screen shows the words in a menu and not where they lead. This map says which screens exist, what each menu holds, what each control leads to, and which part of
docs/SCREEN_DATA_MAP.md says where a screen's content comes from. What this check enforces, because each of these is how a rebuilt product lost its way:

  the map itself      ids are unique and well formed; every screen is reachable from the start screen; every workspace screen has a menu item (or says why not); a menu item, a
                      shortcut or a move names a screen that exists; an overlay is opened by a control that exists; an entry screen leads somewhere; a count names where it comes from.
  the data map        every screen names the sections of docs/SCREEN_DATA_MAP.md that say where its content comes from, those sections exist, and no section is claimed by nobody.
  the prototype       (--prototype) the screens, their titles, the three menu groups, their order and labels, the group headings, the start screen, the page titles, the markup block of
                      each screen, and EVERY jump the source can make (a `view: 'x'` written in a handler) are the ones the map lists. A jump added to the source and not to the map
                      fails, and so does a move in the map that the source no longer makes. What it cannot tell: which screen a handler is shown on (the `from` column), and whether the
                      words in 'control' and 'carries' are right: a person reads those.

Exit status 1 when there is any error. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FORMAT = "reqin-navigation/1"
ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SECTION = re.compile(r"^\d+\.\d+$")
PATH = re.compile(r"^(DS|LK|RJ|RPT|MAN|CL|PR|SL|CMP|VEE|WORK)(\.[A-Za-z_]\w*|\[\])+$")
BARE = ("WORK", "STATIC", "NONE")
KINDS = ("entry", "workspace")
HEADING = re.compile(r"^###\s+(\d+\.\d+)\s+(.*?)\s*(?:·\s*status:\s*(.*?))?\s*$")
WORKSPACE = "workspace"

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_NAV = REPO / "design" / "navigation.json"
DEFAULT_MAP = REPO / "docs" / "SCREEN_DATA_MAP.md"
DEFAULT_PROTO = REPO / "prototype"


# ---------------------------------------------------------------------------------------------------- the map on its own
def _s(v) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _sections(v, where, errs, nonempty=True):
    if not isinstance(v, list) or (nonempty and not v) or not all(isinstance(x, str) and SECTION.match(x) for x in v):
        errs.append("%s: data_map must be a list of section numbers such as \"4.5\"" % where)
        return []
    return v


def _source(v, where, errs):
    if not (isinstance(v, str) and (v in BARE or PATH.match(v))):
        errs.append("%s: %r is not WORK, STATIC, NONE or a field path such as CMP.counts.clusters" % (where, v))


def screens_by_id(nav) -> dict:
    return {s["id"]: s for s in nav.get("screens", []) if isinstance(s, dict) and isinstance(s.get("id"), str)}


def shell_edges(nav) -> list:
    """(from, to, how) for everything the shell offers on every workspace screen."""
    out = []
    ws = [s["id"] for s in nav.get("screens", []) if s.get("kind") == WORKSPACE]
    shell = nav.get("shell") or {}
    sb = shell.get("side_bar") or {}
    targets = []
    for g in sb.get("groups", []) or []:
        for it in g.get("items", []) or []:
            targets.append((it.get("screen"), "side bar: " + str(it.get("label"))))
    for it in sb.get("foot", []) or []:
        if it.get("goes_to"):
            targets.append((it["goes_to"], "side bar: " + str(it.get("label"))))
    tb = shell.get("top_bar") or {}
    for sc in tb.get("shortcuts", []) or []:
        if sc.get("goes_to"):
            targets.append((sc["goes_to"], "top bar: " + str(sc.get("label"))))
    w = (tb.get("search") or {}).get("when_text_entered") or {}
    if w.get("goes_to"):
        targets.append((w["goes_to"], "top bar: search"))
    for a in ws:
        for t, how in targets:
            out.append((a, t, how))
    return out


def edges(nav) -> list:
    """Every (from, to, how) the map allows: the listed moves, plus what the shell offers on every workspace screen."""
    ws = [s["id"] for s in nav.get("screens", []) if s.get("kind") == WORKSPACE]
    out = []
    for f in nav.get("flows", []) or []:
        frm = ws if f.get("from") == WORKSPACE else (f.get("from") if isinstance(f.get("from"), list) else [])
        for a in frm:
            out.append((a, f.get("to"), f.get("control")))
    return out + shell_edges(nav)


def reachable(nav) -> dict:
    """screen -> number of moves from the start screen (0 for the start)."""
    start = nav.get("start")
    dist = {start: 0}
    es = edges(nav)
    frontier = [start]
    while frontier:
        nxt = []
        for a in frontier:
            for x, y, _ in es:
                if x == a and y not in dist:
                    dist[y] = dist[a] + 1
                    nxt.append(y)
        frontier = nxt
    return dist


def unconfirmed(nav) -> list[tuple[str, object]]:
    """Every entry in the map that carries an "unconfirmed" note, as (where, the note). A map drawn from pictures cannot know where a control leads or what a screen is called
    until someone has followed it, and says so here instead of guessing. The note says what is not known. A checker that counts them lets a person see how much is still a guess."""
    found: list[tuple[str, object]] = []

    def walk(v, where):
        if isinstance(v, dict):
            if "unconfirmed" in v:
                name = next((str(v[k]) for k in ("id", "label", "control", "screen", "to") if isinstance(v.get(k), str)), "")
                found.append((where + (" " + name if name else ""), v["unconfirmed"]))
            for k, x in v.items():
                if k != "unconfirmed":
                    walk(x, where + "." + k if where else k)
        elif isinstance(v, list):
            for i, x in enumerate(v):
                walk(x, "%s[%d]" % (where, i))

    walk(nav, "")
    return found


def check(nav, data_map_text: str | None = None, root: Path | None = None) -> list[str]:
    errs: list[str] = []
    if not isinstance(nav, dict):
        return ["the navigation map must be a JSON object"]
    if nav.get("format") != FORMAT:
        errs.append("format must be %r" % FORMAT)
    for k in ("product", "start"):
        if not _s(nav.get(k)):
            errs.append("%s must be a non-empty string" % k)
    screens = nav.get("screens")
    if not isinstance(screens, list) or not screens:
        return errs + ["screens must be a non-empty list"]

    for where, note in unconfirmed(nav):
        if not _s(note):
            errs.append("%s: unconfirmed must say what is not known, in words (not true, not empty)" % where)

    ids: dict[str, str] = {}
    claimed: dict[str, str] = {}              # data-map section -> the id that claims it

    def in_shell(owner):
        return owner == "shell" or owner.startswith("overlay:")

    def claim(sec_list, owner, where):
        """One section, one owner. The shell and the overlays it opens (the glossary) may share a section: the data map describes them together."""
        for sec in sec_list:
            if sec in claimed and claimed[sec] != owner and not (in_shell(owner) and in_shell(claimed[sec])):
                errs.append("%s: data-map section %s is also claimed by %s" % (where, sec, claimed[sec]))
            claimed.setdefault(sec, owner)

    def new_id(i, where):
        if not (isinstance(i, str) and ID.match(i)):
            errs.append("%s: id %r must be lower case words joined by hyphens" % (where, i))
        elif i in ids:
            errs.append("%s: id %r is already used by %s" % (where, i, ids[i]))
        else:
            ids[i] = where

    for n, s in enumerate(screens):
        where = "screens[%d]" % n
        if not isinstance(s, dict):
            errs.append("%s must be an object" % where)
            continue
        new_id(s.get("id"), where)
        where = "screen %s" % s.get("id")
        if not _s(s.get("title")):
            errs.append("%s: title must say the name the screen shows" % where)
        if s.get("kind") not in KINDS:
            errs.append("%s: kind must be one of %s" % (where, ", ".join(KINDS)))
        secs = _sections(s.get("data_map"), where, errs)
        claim(secs, s.get("id"), where)
        if "in_menu" in s and s["in_menu"] is False and not _s(s.get("note")):
            errs.append("%s: in_menu is false, so a note must say how a person gets there" % where)
        for st in s.get("steps", []) or []:
            if not (isinstance(st, dict) and ID.match(str(st.get("id", ""))) and _s(st.get("title"))):
                errs.append("%s: each step needs an id and a title" % where)
                continue
            ssecs = _sections(st.get("data_map"), where + " step " + st["id"], errs)
            claim(ssecs, s.get("id"), where + " step " + st["id"])
            for x in ssecs:
                if x not in secs:
                    errs.append("%s: step %s names section %s, which the screen does not list" % (where, st["id"], x))
        if "component_spec" in s:
            if not _s(s["component_spec"]):
                errs.append("%s: component_spec must be a path" % where)
            elif root is not None and not (root / s["component_spec"]).exists():
                errs.append("%s: component_spec %s does not exist" % (where, s["component_spec"]))
    by_id = screens_by_id(nav)
    if nav.get("start") not in by_id:
        errs.append("start %r is not a screen" % nav.get("start"))
    elif by_id[nav["start"]].get("kind") != "entry":
        errs.append("start screen %r must be an entry screen (it has no shell)" % nav["start"])
    titles = [s.get("title") for s in screens if isinstance(s, dict) and s.get("kind") == WORKSPACE]
    for t in set(titles):
        if titles.count(t) > 1:
            errs.append("two workspace screens are both titled %r: the breadcrumb could not tell them apart" % t)

    # sheets and overlays
    for kind in ("sheets", "overlays"):
        for n, o in enumerate(nav.get(kind, []) or []):
            where = "%s[%d]" % (kind, n)
            if not isinstance(o, dict):
                errs.append("%s must be an object" % where)
                continue
            new_id(o.get("id"), where)
            where = "%s %s" % (kind[:-1], o.get("id"))
            if not _s(o.get("title")):
                errs.append("%s: title is missing" % where)
            claim(_sections(o.get("data_map"), where, errs), "%s:%s" % (kind[:-1], o.get("id")), where)
            if kind == "sheets":
                of = o.get("opened_from")
                if not (isinstance(of, list) and of and all(x in by_id for x in of)):
                    errs.append("%s: opened_from must list screens that exist" % where)
            else:
                if not (isinstance(o.get("opened_by"), list) and o["opened_by"]):
                    errs.append("%s: opened_by must name the controls that open it" % where)
                for k in ("closed_by", "where"):
                    if not _s(o.get(k)):
                        errs.append("%s: %s must say how" % (where, k))
    overlays = {o.get("id") for o in nav.get("overlays", []) or [] if isinstance(o, dict)}

    # the shell
    ws = [s for s in screens if isinstance(s, dict) and s.get("kind") == WORKSPACE]
    shell = nav.get("shell")
    menu_screens: dict[str, str] = {}
    controls: dict[str, str] = {}               # "side_bar.foot[Label]" / "top_bar.shortcuts[Label]" -> the overlay it opens or toggles
    if ws and not isinstance(shell, dict):
        errs.append("there are workspace screens and no shell")
        shell = {}
    shell = shell or {}
    if shell:
        claim(_sections(shell.get("data_map"), "shell", errs), "shell", "shell")
        sb = shell.get("side_bar")
        if not isinstance(sb, dict) or not isinstance(sb.get("groups"), list) or not sb["groups"]:
            errs.append("shell.side_bar.groups must be a non-empty list")
            sb = {"groups": []}
        labels = []
        gids = set()
        for g in sb["groups"]:
            gw = "side_bar group %s" % g.get("id")
            if not (isinstance(g.get("id"), str) and ID.match(g["id"])) or g["id"] in gids:
                errs.append("%s: id is missing, badly formed or repeated" % gw)
            gids.add(g.get("id"))
            if g.get("heading") is not None and not _s(g.get("heading")):
                errs.append("%s: heading must be a string or null" % gw)
            if not isinstance(g.get("collapsible"), bool):
                errs.append("%s: collapsible must be true or false" % gw)
            elif g["collapsible"] and not isinstance(g.get("default_open"), bool):
                errs.append("%s: a group that folds must say whether it starts open (default_open)" % gw)
            if g.get("collapsible") and g.get("heading") is None:
                errs.append("%s: a group that folds needs a heading to fold by" % gw)
            if not isinstance(g.get("items"), list) or not g["items"]:
                errs.append("%s: items must be a non-empty list" % gw)
                continue
            for it in g["items"]:
                iw = "%s item %s" % (gw, it.get("label"))
                if it.get("screen") not in by_id:
                    errs.append("%s: screen %r is not a screen" % (iw, it.get("screen")))
                elif by_id[it["screen"]].get("kind") != WORKSPACE:
                    errs.append("%s: %s is an entry screen and has no side bar" % (iw, it["screen"]))
                elif it["screen"] in menu_screens:
                    errs.append("%s: %s already has a menu item" % (iw, it["screen"]))
                else:
                    menu_screens[it["screen"]] = it.get("label")
                if not _s(it.get("label")):
                    errs.append("%s: label is missing" % iw)
                elif it["label"] in labels:
                    errs.append("%s: two menu items are labelled %r" % (iw, it["label"]))
                labels.append(it.get("label"))
                if not _s(it.get("icon")):
                    errs.append("%s: icon must name the icon" % iw)
                if "count" in it:
                    c = it["count"]
                    if not (isinstance(c, dict) and _s(c.get("what")) and isinstance(c.get("sources"), list) and c["sources"] and _s(c.get("no_producer"))):
                        errs.append("%s: a count needs what it counts, its sources and what to show when nothing produces it" % iw)
                    else:
                        for src in c["sources"]:
                            _source(src, iw + " count", errs)
        lay = sb.get("layout")
        if lay is not None:
            if not (isinstance(lay, dict) and _s(lay.get("wide"))):
                errs.append("side_bar.layout must describe the wide layout (wide)")
            nar = (lay or {}).get("narrow") if isinstance(lay, dict) else None
            if nar is not None:
                if not (isinstance(nar, dict) and re.fullmatch(r"[0-9]+px", str(nar.get("at_most_width", ""))) and _s(nar.get("what"))):
                    errs.append("side_bar.layout.narrow needs at_most_width as pixels (for example 900px) and what it looks like")
                elif "all_items_visible" in nar and not isinstance(nar["all_items_visible"], bool):
                    errs.append("side_bar.layout.narrow.all_items_visible must be true or false")
        for pat in sb.get("prototype_only_labels", []) or []:
            try:
                re.compile(pat)
            except (re.error, TypeError):
                errs.append("side_bar.prototype_only_labels: %r is not a regular expression" % (pat,))
        for it in sb.get("foot", []) or []:
            iw = "side_bar foot %s" % it.get("label")
            if not _s(it.get("label")):
                errs.append("%s: label is missing" % iw)
            have = [k for k in ("opens", "goes_to") if it.get(k)]
            if len(have) != 1:
                errs.append("%s: say either what it opens or where it goes, once" % iw)
            if it.get("opens"):
                if it["opens"] not in overlays:
                    errs.append("%s: opens %r, which is not an overlay" % (iw, it["opens"]))
                controls["side_bar.foot[%s]" % it.get("label")] = it["opens"]
            if it.get("goes_to") and it["goes_to"] not in by_id:
                errs.append("%s: goes_to %r is not a screen" % (iw, it["goes_to"]))
        for s in ws:
            if s["id"] not in menu_screens and s.get("in_menu") is not False:
                errs.append("workspace screen %s has no menu item (if that is intended, set in_menu to false and say in the note how a person gets there)" % s["id"])
            if s["id"] in menu_screens and s.get("in_menu") is False:
                errs.append("workspace screen %s says in_menu is false and has a menu item" % s["id"])
        tb = shell.get("top_bar")
        if not isinstance(tb, dict):
            errs.append("shell.top_bar must be an object")
            tb = {}
        for c in tb.get("chips", []) or []:
            for src in c.get("sources", []) or []:
                _source(src, "top bar chip %s" % c.get("what"), errs)
        search = tb.get("search")
        if search:
            for src in search.get("over", []) or []:
                _source(src, "top bar search", errs)
            w = search.get("when_text_entered") or {}
            if w.get("goes_to") not in by_id:
                errs.append("top bar search: when_text_entered.goes_to %r is not a screen" % w.get("goes_to"))
        for sc in tb.get("shortcuts", []) or []:
            sw = "top bar shortcut %s" % sc.get("label")
            have = [k for k in ("goes_to", "opens", "toggles") if sc.get(k)]
            if not _s(sc.get("label")) or len(have) != 1:
                errs.append("%s: a label, and exactly one of goes_to, opens or toggles" % sw)
                continue
            if "goes_to" in have and sc["goes_to"] not in by_id:
                errs.append("%s: goes_to %r is not a screen" % (sw, sc["goes_to"]))
            if ("opens" in have or "toggles" in have):
                o = sc.get("opens") or sc.get("toggles")
                if o not in overlays:
                    errs.append("%s: %r is not an overlay" % (sw, o))
                controls["top_bar.shortcuts[%s]" % sc.get("label")] = o
    for o in nav.get("overlays", []) or []:
        for c in o.get("opened_by", []) or []:
            if c not in controls:
                errs.append("overlay %s: opened_by %r is not a control in the shell (have: %s)" % (o.get("id"), c, ", ".join(sorted(controls)) or "none"))
            elif controls[c] != o.get("id"):
                errs.append("overlay %s: %s opens %r, not this overlay" % (o.get("id"), c, controls[c]))

    # the moves between screens
    flows = nav.get("flows")
    if not isinstance(flows, list):
        errs.append("flows must be a list")
        flows = []
    for n, f in enumerate(flows):
        fw = "flows[%d]" % n
        if not isinstance(f, dict):
            errs.append("%s must be an object" % fw)
            continue
        frm = f.get("from")
        if frm != WORKSPACE and not (isinstance(frm, list) and frm and all(x in by_id for x in frm)):
            errs.append("%s: from must be %r or a list of screens that exist (got %r)" % (fw, WORKSPACE, frm))
        if f.get("to") not in by_id:
            errs.append("%s: to %r is not a screen" % (fw, f.get("to")))
        for k in ("control", "carries", "evidence"):
            if not _s(f.get(k)):
                errs.append("%s: %s must say something (write 'nothing' when nothing is carried)" % (fw, k))
    for n, x in enumerate(nav.get("not_navigation", []) or []):
        if not (isinstance(x, dict) and _s(x.get("evidence")) and _s(x.get("why"))):
            errs.append("not_navigation[%d] needs the evidence it excuses and why" % n)

    # every screen can be reached, and an entry screen leads somewhere
    if nav.get("start") in by_id:
        dist = reachable(nav)
        for sid in by_id:
            if sid not in dist:
                errs.append("screen %s cannot be reached from the start screen %s by any move or menu item" % (sid, nav["start"]))
    out_of = {}
    for a, b, _ in edges(nav):
        out_of.setdefault(a, set()).add(b)
    for s in screens:
        if isinstance(s, dict) and s.get("kind") == "entry" and not out_of.get(s.get("id")):
            errs.append("entry screen %s leads nowhere" % s.get("id"))

    # the data map
    if data_map_text is not None:
        heads = data_map_sections(data_map_text)
        for sec, who in claimed.items():
            if sec not in heads:
                errs.append("%s claims section %s, which docs/SCREEN_DATA_MAP.md does not have" % (who, sec))
        for sec in heads:
            if sec not in claimed:
                errs.append("section %s of docs/SCREEN_DATA_MAP.md (%s) is claimed by no screen, sheet, overlay or the shell: no one knows where it is shown" % (sec, heads[sec][0]))
    return errs


def data_map_sections(text: str) -> dict:
    """'4.5' -> (title, [status words]) for every `### 4.N Title · status: ...` heading."""
    out = {}
    for line in text.split("\n"):
        m = HEADING.match(line)
        if m:
            out[m.group(1)] = (m.group(2).strip(), [x.strip() for x in (m.group(3) or "").split(",") if x.strip()])
    return out


# ---------------------------------------------------------------------------------------------------- against the prototype's source
def _quoted(text: str) -> list:
    return re.findall(r"'([^']*)'", text)


def scan_prototype(proto: Path) -> dict:
    """What the prototype's source says about its screens and its moves. Raises ValueError, naming the file, when the source no longer has the shape this reads."""
    parts = proto / "parts"

    def read(name):
        p = parts / name
        if not p.is_file():
            raise ValueError("%s is missing" % p)
        return p.read_text(encoding="utf-8")

    c1, c3, d1, shell = read("c1.js"), read("c3.js"), read("data1.js"), read("m/30_shell_open.html")
    out: dict = {}
    m = re.search(r"renderVals\(\) \{(.*?)\n  \}\n", c3, re.S)
    if not m:
        raise ValueError("c3.js: cannot find renderVals()")
    out["views"] = sorted(set(re.findall(r"S\.view === '([a-z]+)'", m.group(1))))
    m = re.search(r"const NAME = \{(.*?)\};", c1, re.S)
    if not m:
        raise ValueError("c1.js: cannot find the NAME map of screen titles")
    out["names"] = dict(re.findall(r"([a-z]+):\s*'([^']*)'", m.group(1)))
    m = re.search(r"navTop: \[(.*?)\]\.map\(item\), navProg: \[(.*?)\]\.map\(item\), navOut: \[(.*?)\]\.map\(item\)", c1, re.S)
    if not m:
        raise ValueError("c1.js: cannot find navTop, navProg and navOut")
    out["groups"] = [_quoted(m.group(1)), _quoted(m.group(2)), _quoted(m.group(3))]
    out["group_headings"] = re.findall(r'class="nav-ghead"[^>]*>.*?<span>(.*?)</span>', shell, re.S)
    out["foot_labels"] = re.findall(r'<div class="ws-foot">(.*?)</div>', shell, re.S)
    out["foot_labels"] = re.findall(r"<span>(.*?)</span>", out["foot_labels"][0]) if out["foot_labels"] else []
    m = re.search(r"view: '([a-z]+)'", d1)
    out["start"] = m.group(1) if m else None
    out["nav_closed_default"] = re.search(r"navClosed: (\{[^}]*\})", d1).group(1) if re.search(r"navClosed: (\{[^}]*\})", d1) else None
    m = re.search(r"v\.pageTitle = (.*?);\n", c3, re.S)
    out["page_titles"] = _quoted(m.group(1)) if m else []
    out["title_suffix"] = (re.search(r"document\.title !== v\.pageTitle \+ '([^']*)'", c3) or [None, None])[1]
    out["nav_label"] = (re.search(r'<nav class="ws-nav" aria-label="([^"]*)"', shell) or [None, None])[1]
    out["skip_label"] = (re.search(r'class="skip-link"[^>]*>([^<]*)<', shell) or [None, None])[1]
    out["search_label"] = (re.search(r'id="top-search"[^>]*aria-label="([^"]*)"', shell) or [None, None])[1]
    out["markup"] = {f.name: f.read_text(encoding="utf-8") for f in (parts / "m").glob("*.html")}
    jumps: dict[str, set] = {}
    for f in sorted(parts.glob("c[0-9].js")):
        method = None
        for line in f.read_text(encoding="utf-8").split("\n"):
            mm = re.match(r"^  (?:static )?([A-Za-z_]\w*)\s*\([^)]*\)\s*\{", line)
            if mm and mm.group(1) not in ("if", "for", "while", "switch", "catch"):
                method = mm.group(1)
            for t in re.findall(r"\bview: '([a-z]+)'", line):
                jumps.setdefault("%s %s" % (f.name, method), set()).add(t)
    out["jumps"] = jumps
    return out


def check_prototype(nav: dict, proto: dict) -> list[str]:
    errs: list[str] = []
    by_id = screens_by_id(nav)
    if sorted(by_id) != proto["views"]:
        errs.append("the screens differ: the map has %s, the prototype's renderVals has %s" % (sorted(by_id), proto["views"]))
    if nav.get("start") != proto["start"]:
        errs.append("the start screen is %r in the map and %r in the prototype's DEFAULTS" % (nav.get("start"), proto["start"]))
    # titles
    names = proto["names"]
    ws_ids = sorted(s for s, v in by_id.items() if v.get("kind") == WORKSPACE)
    if ws_ids != sorted(names):
        errs.append("the workspace screens differ: the map has %s, the prototype's NAME map has %s" % (ws_ids, sorted(names)))
    for sid in ws_ids:
        if sid in names and by_id[sid].get("title") != names[sid]:
            errs.append("screen %s is titled %r in the map and %r in the prototype" % (sid, by_id[sid].get("title"), names[sid]))
    pt = proto["page_titles"]
    open_title = by_id.get("open", {}).get("title")
    imp = by_id.get("import", {})
    step_titles = [st.get("title") for st in imp.get("steps", [])]
    for want, where in [(open_title, "open"), *[(t, "import step") for t in step_titles]]:
        if want not in pt:
            errs.append("the map titles %s %r, which is not among the prototype's page titles %s" % (where, want, pt))
    if imp and imp.get("title") not in pt:
        errs.append("the import screen is titled %r, not among the prototype's page titles" % imp.get("title"))
    # the menu
    sb = (nav.get("shell") or {}).get("side_bar") or {}
    groups = sb.get("groups", [])
    if len(groups) != len(proto["groups"]):
        errs.append("the map has %d menu groups and the prototype has %d" % (len(groups), len(proto["groups"])))
    else:
        for g, keys in zip(groups, proto["groups"]):
            got = [it.get("screen") for it in g.get("items", [])]
            if got != keys:
                errs.append("menu group %r holds %s in the map and %s in the prototype (the order counts)" % (g.get("id"), got, keys))
            for it in g.get("items", []):
                if it.get("screen") in names and it.get("label") != names[it["screen"]]:
                    errs.append("menu item for %s is labelled %r in the map and %r in the prototype" % (it["screen"], it.get("label"), names[it["screen"]]))
        heads = [g.get("heading") for g in groups if g.get("heading")]
        if heads != proto["group_headings"]:
            errs.append("the folding group headings are %s in the map and %s in the prototype" % (heads, proto["group_headings"]))
        if groups and groups[0].get("heading") is not None:
            errs.append("the prototype's first menu group has no heading; the map gives it one")
        if proto["nav_closed_default"] not in (None, "{}") and any(g.get("default_open") for g in groups):
            errs.append("the prototype starts with a menu group folded (navClosed %s) and the map says every group starts open" % proto["nav_closed_default"])
    foot = [it.get("label") for it in sb.get("foot", [])]
    if foot != proto["foot_labels"]:
        errs.append("the foot of the side bar is %s in the map and %s in the prototype" % (foot, proto["foot_labels"]))
    if sb.get("label") != proto["nav_label"]:
        errs.append("the side bar's accessible name is %r in the map and %r in the prototype" % (sb.get("label"), proto["nav_label"]))
    shell = nav.get("shell") or {}
    if (shell.get("skip_link") or {}).get("label") != proto["skip_label"]:
        errs.append("the skip link says %r in the map and %r in the prototype" % ((shell.get("skip_link") or {}).get("label"), proto["skip_label"]))
    if ((shell.get("top_bar") or {}).get("search") or {}).get("label") != proto["search_label"]:
        errs.append("the top bar's search is labelled %r in the map and %r in the prototype" % (((shell.get("top_bar") or {}).get("search") or {}).get("label"), proto["search_label"]))
    suffix = (shell.get("page_title") or {}).get("document_title", "")
    if proto["title_suffix"] is None or not suffix.endswith(proto["title_suffix"]):
        errs.append("the document title is %r in the map and the prototype ends it with %r" % (suffix, proto["title_suffix"]))
    # the markup block of each screen
    for sid, s in by_id.items():
        part = s.get("part")
        if not part:
            continue
        text = proto["markup"].get(part)
        if text is None:
            errs.append("screen %s names the markup file %s, which the prototype does not have" % (sid, part))
            continue
        flags = [("is" + st["id"].capitalize()) for st in s.get("steps", [])] or ["is" + sid.capitalize()]
        for flag in flags:
            if "{{%s}}" % flag not in text:
                errs.append("screen %s: %s does not switch on {{%s}}" % (sid, part, flag))
    for o in (nav.get("sheets", []) or []):
        if o.get("part") and o["part"] not in proto["markup"]:
            errs.append("sheet %s names the markup file %s, which the prototype does not have" % (o.get("id"), o["part"]))
    # every jump the source can make
    want: dict[str, set] = {}
    for f in nav.get("flows", []):
        want.setdefault(f.get("evidence"), set()).add(f.get("to"))
    excused = {x.get("evidence") for x in nav.get("not_navigation", []) or []}
    have = proto["jumps"]
    for ev, targets in sorted(have.items()):
        if ev in excused:
            continue
        if ev not in want:
            errs.append("the source makes a jump the map does not list: %s leads to %s" % (ev, ", ".join(sorted(targets))))
        elif want[ev] != targets:
            errs.append("%s leads to %s in the source and to %s in the map" % (ev, ", ".join(sorted(targets)), ", ".join(sorted(want[ev]))))
    for ev in sorted(want):
        if ev not in have:
            errs.append("the map lists a move from %s, and the source has no jump there" % ev)
    for ev in sorted(excused):
        if ev not in have:
            errs.append("not_navigation excuses %s, and the source has no jump there" % ev)
    return errs


# ---------------------------------------------------------------------------------------------------- the page for people
def _control_words(ref: str) -> str:
    """'side_bar.foot[Glossary and help]' -> the side bar's 'Glossary and help'"""
    m = re.match(r"^(side_bar|top_bar)\.\w+\[(.*)\]$", ref)
    return ("the %s's '%s'" % (m.group(1).replace("_", " "), m.group(2))) if m else ref


def render_doc(nav: dict, data_map_text: str) -> str:
    heads = data_map_sections(data_map_text)
    by_id = screens_by_id(nav)
    dist = reachable(nav)
    flows = nav["flows"]
    shell = nav.get("shell") or {}
    sb = shell.get("side_bar") or {}
    tb = shell.get("top_bar") or {}
    ws_ids = [s["id"] for s in nav["screens"] if s.get("kind") == WORKSPACE]

    def sec(s):
        return ", ".join("%s %s" % (x, heads.get(x, ("?", []))[0]) for x in s)

    def status(secs):
        words = []
        for x in secs:
            for w in heads.get(x, ("", []))[1]:
                if w not in words:
                    words.append(w)
        return ", ".join(words) or "?"

    menu_of = {it["screen"]: (g.get("heading") or "(top)") for g in sb.get("groups", []) for it in g.get("items", [])}
    inbound: dict[str, list] = {}
    for f in flows:
        frm = ws_ids if f["from"] == WORKSPACE else f["from"]
        inbound.setdefault(f["to"], [])
        for a in (["any workspace screen"] if f["from"] == WORKSPACE else frm):
            if a not in inbound[f["to"]]:
                inbound[f["to"]].append(a)
    L = []
    w = L.append
    w("# Navigation map: screens, menus, moves and where each screen's content comes from")
    w("")
    w("<!-- Generated from design/navigation.json by `python3 tools/gui_checks/check_navigation.py --write-doc docs/NAVIGATION_MAP.md`. Do not edit by hand: a test fails when this page and the JSON disagree. -->")
    w("")
    w("**What this page is for.** A picture of a screen shows the words in a menu and not where they lead, nor which screen a button on another screen opens, nor what it carries along. An agent rebuilding the product from pictures gets the menu's words and no wiring. This page is the wiring, written down once: [`design/navigation.json`](../design/navigation.json) is the same facts for a program, and `tools/gui_checks/check_navigation.py` checks it. Where a screen's content comes from is in [`SCREEN_DATA_MAP.md`](SCREEN_DATA_MAP.md); how things look is in `design/tokens.css`.")
    w("")
    w("**Where it came from.** One agent read the prototype's source (`prototype/parts/`) and wrote it down. The check compares the screens, titles, menu groups, their order and labels, the start screen, the page titles, and every jump a handler in the source can make, with this map, so a screen or a jump added to the prototype and not to the map fails. It does not know which screen a handler is shown on (the *From* column was read by a person) or whether the words in *Control* and *Carries* are right. Nobody has built a menu from this page yet. **Everything is made up:** the sample project is invented.")
    w("")
    w("## 1. Screens")
    w("")
    w("A *workspace* screen has the shell (side bar and top bar); an *entry* screen does not. *Moves from the start* counts the fewest moves from `%s`. *Content* is the sections of the data map that say where each part of the screen comes from, with their status there." % nav["start"])
    w("")
    w("| Screen | Title it shows | Kind | In the menu | Content (data map) | Status there | Reached from | Moves from the start |")
    w("|---|---|---|---|---|---|---|---|")
    for s in nav["screens"]:
        sid = s["id"]
        reach = ", ".join("`%s`" % a for a in inbound.get(sid, [])) or "no listed move"
        if sid in menu_of:
            reach += "; the menu"
        elif sid == nav["start"]:
            reach = "the start"
        title = s["title"] if not s.get("steps") else " / ".join(st["title"] for st in s["steps"])
        w("| `%s` | %s | %s | %s | %s | %s | %s | %s |" % (sid, title, s["kind"], menu_of.get(sid, "no"), sec(s["data_map"]), status(s["data_map"]), reach, dist.get(sid, "not reachable")))
    w("")
    for s in nav["screens"]:
        if s.get("note"):
            w("- `%s`: %s" % (s["id"], s["note"]))
    w("")
    w("## 2. The side bar (workspace screens only)")
    w("")
    w("Accessible name: **%s**. Layout: %s." % (sb.get("label"), sb.get("layout", {}).get("wide", "not described")))
    n = (sb.get("layout") or {}).get("narrow")
    if n:
        w("At most %s wide: %s. *(%s.)*" % (n["at_most_width"], n["what"], (sb["layout"]).get("how_known", "")))
        if n.get("all_items_visible"):
            w("")
            w("A build that follows this map must show every item at that width (`nav.narrow_shows_every_item` in `docs/GUI_TEST_HOOKS.md`).")
    w("")
    for g in sb.get("groups", []):
        head = g.get("heading") or "(no heading)"
        fold = ("folds; starts %s" % ("open" if g.get("default_open") else "closed")) if g.get("collapsible") else "does not fold"
        w("- **%s** (%s)" % (head, fold))
        for it in g["items"]:
            extra = ""
            if it.get("count"):
                extra = " with a count: %s. From %s. When nothing produces it: %s" % (it["count"]["what"], ", ".join("`%s`" % x for x in it["count"]["sources"]), it["count"]["no_producer"])
            w("  - %s → `%s` (icon `%s`)%s" % (it["label"], it["screen"], it["icon"], extra))
    w("- **Foot**")
    for it in sb.get("foot", []):
        tgt = ("opens the %s overlay" % it["opens"]) if it.get("opens") else ("goes to `%s`" % it["goes_to"] + ("; also " + it["also"] if it.get("also") else ""))
        w("  - %s (icon `%s`): %s" % (it["label"], it["icon"], tgt))
    w("")
    w("Current item: %s" % sb.get("current", ""))
    w("")
    if sb.get("note"):
        w(sb["note"])
        w("")
    if sb.get("prototype_only"):
        w("Only in the prototype, not part of the product: %s." % "; ".join(sb["prototype_only"]))
        if sb.get("prototype_only_labels"):
            w("These sit inside the same `nav` element as the menu, so a program reading the menu sees them too. `site_map.py` leaves out any item whose label matches one of these patterns: %s." % ", ".join("`%s`" % x for x in sb["prototype_only_labels"]))
        w("")
    w("## 3. The top bar and the frame (workspace screens only)")
    w("")
    w("- Breadcrumb: %s. The project name is %s." % (" / ".join(tb.get("breadcrumb", [])), tb.get("project_name", "")))
    for c in tb.get("chips", []):
        w("- A chip for the %s, from %s." % (c["what"], ", ".join("`%s`" % x for x in c["sources"])))
    s = tb.get("search")
    if s:
        w("- Search (\"%s\") over %s. Once text is entered it goes to `%s` carrying %s; emptied, it %s." % (s["label"], ", ".join("`%s`" % x for x in s["over"]), s["when_text_entered"]["goes_to"], s["when_text_entered"]["carries"], s["when_emptied"]))
    for sc in tb.get("shortcuts", []):
        what = ("goes to `%s`" % sc["goes_to"]) if sc.get("goes_to") else ("opens the %s overlay" % sc["opens"]) if sc.get("opens") else ("shows and hides the %s overlay" % sc["toggles"])
        w("- Button \"%s\": %s." % (sc["label"], what))
    if tb.get("prototype_only"):
        w("- Only in the prototype: %s." % "; ".join(tb["prototype_only"]))
    for f in shell.get("frame", []) or []:
        w("- %s." % f.rstrip("."))
    sl = shell.get("skip_link")
    if sl:
        w("- A skip link \"%s\" is the first thing a keyboard reaches; it moves focus to %s." % (sl["label"], sl["moves_focus_to"]))
    pt = shell.get("page_title")
    if pt:
        w("- Title of the page: `%s`. %s." % (pt["document_title"], pt["announce"][0].upper() + pt["announce"][1:]))
    w("")
    w("## 4. Moves between screens")
    w("")
    w("Every control on one screen that opens another, apart from the side bar and the top bar above. *Carries* is what is set on arrival. The *Evidence* column names the piece of the prototype's code the move was read from.")
    w("")
    w("| From | To | Control | Carries | Evidence |")
    w("|---|---|---|---|---|")
    order = {sid: i for i, sid in enumerate(by_id)}
    for f in sorted(flows, key=lambda f: (-1 if f["from"] == WORKSPACE else order.get(f["from"][0], 99), order.get(f["to"], 99))):
        frm = "any workspace screen" if f["from"] == WORKSPACE else ", ".join("`%s`" % a for a in f["from"])
        w("| %s | `%s` | %s | %s | `%s` |" % (frm, f["to"], f["control"], f["carries"], f["evidence"]))
    w("")
    for x in nav.get("not_navigation", []) or []:
        w("Not a move: `%s`: %s." % (x["evidence"], x["why"].rstrip(".")))
    w("")
    w("## 5. Sheets and overlays")
    w("")
    for o in nav.get("sheets", []) or []:
        w("- **%s** (sheet, `%s`), opened from %s. %s Content: %s." % (o["title"], o["id"], ", ".join("`%s`" % x for x in o["opened_from"]), o.get("note", ""), sec(o["data_map"])))
    for o in nav.get("overlays", []) or []:
        w("- **%s** (overlay, `%s`), opened by %s; closed by %s; shown as %s. Content: %s." % (o["title"], o["id"], ", ".join(_control_words(x) for x in o["opened_by"]), o["closed_by"], o["where"], sec(o["data_map"])))
    w("")
    w("## 6. Notes")
    w("")
    for x in nav.get("notes", []) or []:
        w("- %s" % x)
    w("")
    guesses = unconfirmed(nav)
    if guesses:
        w("## 7. Not confirmed")
        w("")
        w("These entries were written down without having been followed in a running page or read from the source. Treat each as a guess until someone has done that, and take the note off when they have.")
        w("")
        for where, note in guesses:
            w("- `%s`: %s" % (where, note))
        w("")
    w("## %d. What this page does not say" % (8 if guesses else 7))
    w("")
    w("- Nobody has built a menu or a screen from it. The first agent to do so should say which line did not work as written.")
    w("- It describes the prototype's navigation. What the product's navigation *should* be (for example addresses that survive a reload, the back button, a menu on a phone) is not decided here; where the prototype does not say, this page does not either.")
    w("- It was read from the source and the styles; the side bar's narrow layout was not run in a browser for this page. `tools/gui_checks/site_map.py` reads the same facts from a running page, and `docs/GUI_TEST_HOOKS.md` says how a screen exposes them to the probe.")
    w("- Roles and lenses: what each person sees in the menu or on a screen (a lead, an observer) is not mapped here. The prototype shows the same menu to every person.")
    w("")
    return "\n".join(L)


# ---------------------------------------------------------------------------------------------------- command line
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("nav", nargs="?", default=str(DEFAULT_NAV))
    ap.add_argument("--data-map", default=str(DEFAULT_MAP), help="docs/SCREEN_DATA_MAP.md; every section must be claimed and every claim must exist ('none' to skip)")
    ap.add_argument("--prototype", help="the prototype folder: check the map against its source")
    ap.add_argument("--write-doc", help="write the page for people to this file")
    ap.add_argument("--check-doc", help="fail when this file is not what --write-doc would write now")
    ap.add_argument("--json", help="write the result here")
    a = ap.parse_args(argv)
    try:
        nav = json.loads(Path(a.nav).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("cannot read %s: %s" % (a.nav, e))
        return 1
    dm = None if a.data_map == "none" else Path(a.data_map).read_text(encoding="utf-8")
    errs = check(nav, dm, Path(a.nav).resolve().parent.parent)
    if a.prototype and not errs:
        try:
            errs += check_prototype(nav, scan_prototype(Path(a.prototype)))
        except ValueError as e:
            errs.append("the prototype's source no longer has the shape this check reads: %s" % e)
    if not errs and (a.write_doc or a.check_doc):
        if dm is None:
            errs.append("the page for people needs the data map")
        else:
            doc = render_doc(nav, dm)
            if a.write_doc:
                Path(a.write_doc).write_text(doc, encoding="utf-8")
                print("wrote %s" % a.write_doc)
            if a.check_doc:
                try:
                    have = Path(a.check_doc).read_text(encoding="utf-8")
                except OSError as e:
                    have, errs = None, errs + ["cannot read %s: %s" % (a.check_doc, e)]
                if have is not None and have != doc:
                    errs.append("%s is not what design/navigation.json produces now: run with --write-doc" % a.check_doc)
    for e in errs:
        print("  " + e)
    dist = reachable(nav) if not errs else {}
    if not errs and unconfirmed(nav):
        print("  %d entr%s marked unconfirmed (a guess nobody has followed): %s" % (len(unconfirmed(nav)), "y is" if len(unconfirmed(nav)) == 1 else "ies are", "; ".join(w for w, _ in unconfirmed(nav)[:5])))
    print("%s: %s%s" % (a.nav, "ok" if not errs else "%d problem%s" % (len(errs), "" if len(errs) == 1 else "s"),
                        ("  (%d screens, all reachable; %d moves listed%s)" % (len(nav["screens"]), len(nav["flows"]), "; checked against the prototype" if a.prototype else "; NOT checked against any source")) if not errs else ""))
    if a.json:
        Path(a.json).write_text(json.dumps({"errors": errs, "reachable": dist}, indent=2), encoding="utf-8")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
