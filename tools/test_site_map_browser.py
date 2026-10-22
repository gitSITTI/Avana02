"""tools/gui_checks/site_map.py in a real browser: on a small page written for the test, and on the running prototype, whose navigation it must read the way the map says.

Skipped when Playwright or its Chromium is not installed. What this proves:
  - the reader finds a menu's groups, items, counts and current item, opens a folded group to read it, follows each item once, and says what each leads to;
  - it does NOT click what it was told to leave alone (a control whose name says it deletes, a link to another site, a disabled item), and the test shows that the control
    really was not clicked;
  - on the running prototype (the sample project opened) it finds the 12 menu items in their three groups and the foot, each leads to the screen whose title the map gives,
    and the comparison with design/navigation.json reports no difference; and it does report one when the map is changed in each of several ways, so a clean report means something.
What it does not prove: that it reads every kind of menu (a menu that opens on hover, a tree of folders, a menu drawn on a canvas); only these. Chromium only.
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
sys.path.insert(0, str(REPO / "prototype"))
import site_map as sm  # noqa: E402


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Alpha · Demo</title>
<style>.kids[hidden]{display:none} nav{display:flex;flex-direction:column;width:200px} .count{background:#eee;margin-left:6px}</style></head><body>
<a href="#content" class="skip">Skip to the content</a>
<nav aria-label="Main">
  <a href="#/alpha">Alpha</a>
  <div class="grp"><button id="tog" aria-expanded="true">More</button>
    <div class="kids"><a href="#/beta">Beta <span class="count">3</span></a><a href="#/gamma">Gamma</a></div></div>
  <div class="foot"><button id="del" onclick="document.getElementById('log').textContent='deleted'">Delete everything</button>
    <a href="https://example.com/elsewhere">Elsewhere</a><a aria-disabled="true" href="#/delta">Delta</a></div>
</nav>
<div class="crumb">Demo / <span id="crumb">Alpha</span></div>
<main><h1 id="h">Alpha heading</h1><p id="content" tabindex="-1">Body</p><p id="log"></p></main>
<script>
const params = new URLSearchParams(location.search);
const T = {alpha: 'Alpha', beta: 'Beta', gamma: 'Gamma'};
const kids = document.querySelector('.kids'), tog = document.getElementById('tog');
if (params.get('folded')) { kids.hidden = true; tog.setAttribute('aria-expanded', 'false'); }
tog.addEventListener('click', () => { const open = tog.getAttribute('aria-expanded') !== 'true'; tog.setAttribute('aria-expanded', String(open)); kids.hidden = !open; });
function show() {
  const k = (location.hash || '#/alpha').slice(2), t = T[k] || 'Alpha';
  document.title = t + ' · Demo'; document.getElementById('h').textContent = t + ' heading'; document.getElementById('crumb').textContent = t;
  document.querySelectorAll('nav a[href^="#/"]').forEach((a) => {
    if (a.getAttribute('href') === '#/' + k && !params.get('nocurrent')) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  });
}
addEventListener('hashchange', show); show();
</script></body></html>"""

NAV = {
    "screens": [{"id": "alpha", "title": "Alpha"}, {"id": "beta", "title": "Beta"}, {"id": "gamma", "title": "Gamma"}],
    "shell": {
        "side_bar": {
            "label": "Main",
            "groups": [
                {"heading": None, "collapsible": False, "items": [{"screen": "alpha", "label": "Alpha"}]},
                {"heading": "More", "collapsible": True, "default_open": True, "items": [{"screen": "beta", "label": "Beta"}, {"screen": "gamma", "label": "Gamma"}]},
            ],
            "foot": [{"label": "Delete everything"}, {"label": "Elsewhere"}, {"label": "Delta"}],
        },
        "skip_link": {"label": "Skip to the content"},
        "page_title": {"document_title": "<screen title> · Demo"},
        "top_bar": {},
    },
}


def read(tmp_path, query="", visit=True, **kw):
    f = tmp_path / "page.html"
    f.write_text(PAGE, encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        try:
            pg = b.new_page(viewport={"width": 1200, "height": 800})
            url = "file://%s%s" % (f, query)
            pg.goto(url)
            r = sm.read_site_map(pg, visit=visit, start_url=url, settle=150, **kw)
            log = pg.inner_text("#log")
        finally:
            b.close()
    return r, log


def items(r):
    return [(g["heading"], [i["label"] for i in g["items"]]) for g in r["landmarks"][0]["groups"]]


def item(r, label):
    return next(i for g in r["landmarks"][0]["groups"] for i in g["items"] if i["label"] == label)


# ------------------------------------------------------------------------------------------------ a small page
def test_it_reads_the_groups_items_counts_and_the_current_item(tmp_path):
    r, _ = read(tmp_path, visit=False)
    assert r["landmarks"][0]["name"] == "Main"
    assert items(r) == [(None, ["Alpha"]), ("More", ["Beta", "Gamma"]), (None, ["Delete everything", "Elsewhere", "Delta"])]
    assert item(r, "Beta")["badge"] == "3" and item(r, "Beta")["label"] == "Beta"
    assert item(r, "Alpha")["current"] == "page" and item(r, "Beta")["current"] == ""
    assert item(r, "Delta")["disabled"] is True and item(r, "Alpha")["href"] == "#/alpha"
    assert r["skip_link"] == {"text": "Skip to the content", "target": "#content", "target_exists": True}
    assert r["main"]["headings"] == ["Alpha heading"] and "Demo" in r["breadcrumb"] and r["followed"] == 0


def test_it_follows_each_item_once_and_says_where_it_leads(tmp_path):
    r, log = read(tmp_path)
    beta, gamma, alpha = item(r, "Beta")["leads_to"], item(r, "Gamma")["leads_to"], item(r, "Alpha")["leads_to"]
    assert beta["title"] == "Beta · Demo" and beta["heading"] == "Beta heading" and beta["marks_itself_current"] and not beta["no_visible_change"]
    assert gamma["title"] == "Gamma · Demo" and gamma["current"] == ["Gamma"]
    assert alpha["no_visible_change"] is True, "it was already on Alpha"
    assert [s["title"] for s in r["screens_seen"]] == ["Beta · Demo", "Gamma · Demo"]
    assert r["followed"] == 3


def test_it_leaves_alone_what_it_was_told_to_and_the_control_was_really_not_clicked(tmp_path):
    r, log = read(tmp_path)
    assert log == "", "the delete control was clicked: the page now says %r" % log
    assert "changes something" in item(r, "Delete everything")["not_followed"]
    assert item(r, "Elsewhere")["not_followed"] == "another site"
    assert item(r, "Delta")["not_followed"] == "disabled"
    assert "leads_to" not in item(r, "Delete everything")


def test_a_skipped_item_can_be_followed_when_asked_and_that_really_clicks_it(tmp_path):
    r, log = read(tmp_path, also=("Delete everything",))
    assert log == "deleted" and "leads_to" in item(r, "Delete everything")


def test_an_extra_skip_pattern_and_the_ignore_pattern_leave_items_alone(tmp_path):
    r, _ = read(tmp_path, skip=sm.DEFAULT_SKIP + "|(^Gamma$)")
    assert "leads_to" not in item(r, "Gamma") and "leads_to" in item(r, "Beta")
    r, _ = read(tmp_path, ignore="^Beta$")
    assert "excluded by --ignore" in item(r, "Beta")["not_followed"] and "leads_to" in item(r, "Gamma")


def test_a_folded_group_is_opened_to_be_read_and_the_page_says_so(tmp_path):
    r, _ = read(tmp_path, query="?folded=1", visit=False)
    assert items(r)[1] == ("More", ["Beta", "Gamma"]) and any("folded" in n for n in r["notes"])
    assert r["landmarks"][0]["groups"][1]["expandable"] is True


def test_a_menu_whose_pages_are_separate_documents_is_followed_and_the_start_is_restored(tmp_path):
    (tmp_path / "a.html").write_text('<!doctype html><title>A</title><nav aria-label="Main"><a href="b.html">To B</a><a href="a.html" aria-current="page">A</a></nav><main><h1>A page</h1></main>', encoding="utf-8")
    (tmp_path / "b.html").write_text('<!doctype html><title>B</title><nav aria-label="Main"><a href="a.html">To A</a><a href="b.html" aria-current="page">B</a></nav><main><h1>B page</h1></main>', encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        try:
            pg = b.new_page()
            url = "file://%s" % (tmp_path / "a.html")
            pg.goto(url)
            r = sm.read_site_map(pg, start_url=url, settle=100)
            back = pg.title()
        finally:
            b.close()
    lt = item(r, "To B")["leads_to"]
    assert lt["title"] == "B" and lt["heading"] == "B page" and lt["new_document"] is True
    assert back == "A", "after following a link to another document the page must be put back where it started"


def test_an_icon_only_item_is_named_by_its_aria_label(tmp_path):
    (tmp_path / "i.html").write_text('<!doctype html><title>I</title><nav aria-label="Tools"><button aria-label="Open settings"><svg width="10" height="10"></svg></button></nav><main><h1>x</h1></main>', encoding="utf-8")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        try:
            pg = b.new_page()
            pg.goto("file://%s" % (tmp_path / "i.html"))
            r = sm.read_site_map(pg, visit=False)
        finally:
            b.close()
    assert items(r) == [(None, ["Open settings"])]


# ------------------------------------------------------------------------------------------------ against a map
def nav_copy():
    return copy.deepcopy(NAV)


def test_the_comparison_agrees_when_the_page_and_the_map_agree(tmp_path):
    r, _ = read(tmp_path)
    assert sm.compare_with_navigation(r, nav_copy()) == []


def breaks():
    def rename(n):
        n["shell"]["side_bar"]["groups"][1]["items"][0]["label"] = "Beta!"

    def reorder(n):
        g = n["shell"]["side_bar"]["groups"][1]["items"]
        g[0], g[1] = g[1], g[0]

    def heading(n):
        n["shell"]["side_bar"]["groups"][1]["heading"] = "Less"

    def extra_group(n):
        n["shell"]["side_bar"]["groups"].append({"heading": "Extra", "collapsible": False, "items": [{"screen": "alpha", "label": "Alpha again"}]})

    def title(n):
        n["screens"][1]["title"] = "Bravo"

    def suffix(n):
        n["shell"]["page_title"]["document_title"] = "<screen title> | Demo"

    def landmark(n):
        n["shell"]["side_bar"]["label"] = "Menu"

    def skip(n):
        n["shell"]["skip_link"]["label"] = "Skip"

    def folds(n):
        n["shell"]["side_bar"]["groups"][0]["collapsible"] = True
        n["shell"]["side_bar"]["groups"][0]["heading"] = "More"
        n["shell"]["side_bar"]["groups"][1]["heading"] = "More"

    return [("a label renamed in the map", rename, "holds"), ("two items reordered", reorder, "the order counts"), ("a group heading renamed", heading, "is headed"),
            ("a group the page does not have", extra_group, "groups on the page"), ("a screen retitled", title, "leads to a page titled"),
            ("another document title pattern", suffix, "leads to a page titled"), ("another landmark name", landmark, "no navigation landmark named"),
            ("another skip link", skip, "skip link says")]


@pytest.mark.parametrize("name,fn,word", breaks(), ids=[b[0] for b in breaks()])
def test_the_comparison_reports_each_way_the_map_and_the_page_differ(tmp_path, name, fn, word):
    r, _ = read(tmp_path)
    n = nav_copy()
    fn(n)
    out = sm.compare_with_navigation(r, n)
    assert out, "%s: the map was changed and the comparison said nothing" % name
    assert any(word in o for o in out), "%s: expected %r in %s" % (name, word, out)


def test_the_comparison_reports_a_current_item_that_is_not_marked(tmp_path):
    r, _ = read(tmp_path, query="?nocurrent=1")
    out = sm.compare_with_navigation(r, nav_copy())
    assert any("not marked current" in o for o in out), out


def test_the_comparison_says_so_when_nothing_was_followed(tmp_path):
    r, _ = read(tmp_path, visit=False)
    assert any("no menu item was followed" in o for o in sm.compare_with_navigation(r, nav_copy()))


def test_the_command_line_writes_the_result_and_exits_with_the_comparison(tmp_path, capsys):
    f = tmp_path / "page.html"
    f.write_text(PAGE, encoding="utf-8")
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(NAV), encoding="utf-8")
    n = nav_copy()
    n["shell"]["side_bar"]["groups"][1]["items"][0]["label"] = "Bravo"
    bad.write_text(json.dumps(n), encoding="utf-8")
    out = tmp_path / "sm.json"
    assert sm.main([str(f), "--out", str(out), "--against", str(good), "--settle", "150"]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["format"] == "reqin-site-map/1"
    assert sm.main([str(f), "--out", str(out), "--against", str(bad), "--settle", "150"]) == 1
    assert "differs:" in capsys.readouterr().out


# ------------------------------------------------------------------------------------------------ the running prototype
NODE = REPO / "prototype" / "vendor" / "node_modules" / "react"
SETUP = ["click:Open the sample project", "click:Confirm mapping and import"]


def prototype_map():
    from h import session
    nav = json.loads((REPO / "design" / "navigation.json").read_text(encoding="utf-8"))
    ignore = "|".join("(%s)" % x for x in nav["shell"]["side_bar"]["prototype_only_labels"])
    with session(1440, 1000) as (pg, errs):
        r = sm.read_site_map(pg, setup=SETUP, settle=500, ignore=ignore)
    return nav, r


@pytest.fixture(scope="module")
def proto():
    if not NODE.exists():
        pytest.skip("the prototype's vendored runtime is not installed (prototype/vendor/node_modules)")
    return prototype_map()


def test_the_running_prototype_has_the_menu_the_map_describes(proto):
    nav, r = proto
    lm = next(l for l in r["landmarks"] if l["name"] == "Main")
    heads = [(g["heading"], [i["label"] for i in g["items"] if not any(__import__("re").search(p, i["label"]) for p in nav["shell"]["side_bar"]["prototype_only_labels"])]) for g in lm["groups"]]
    heads = [h for h in heads if h[1]]
    assert [h[0] for h in heads] == [None, "Progress and evidence", "Policy and output", None]
    assert [len(h[1]) for h in heads] == [3, 6, 3, 2]
    assert sm.compare_with_navigation(r, nav) == []
    assert len(r["screens_seen"]) == 12, "each of the 12 menu items leads to its own screen"
    assert r["skip_link"]["target_exists"] and r["search"]["label"] == "Search requirements"


def test_each_menu_item_of_the_prototype_leads_to_the_screen_the_map_names(proto):
    nav, r = proto
    by_label = {it["label"]: it for g in nav["shell"]["side_bar"]["groups"] for it in g["items"]}
    titles = {s["id"]: s["title"] for s in nav["screens"]}
    lm = next(l for l in r["landmarks"] if l["name"] == "Main")
    seen = 0
    for g in lm["groups"]:
        for it in g["items"]:
            if it["label"] in by_label and "leads_to" in it:
                want = titles[by_label[it["label"]]["screen"]]
                assert it["leads_to"]["title"] == want + " · Requirements Consolidator", it["label"]
                assert it["leads_to"]["marks_itself_current"], it["label"]
                seen += 1
    assert seen == 12
    review = next(i for g in lm["groups"] for i in g["items"] if i["label"] == "Review queue")
    assert review["badge"].isdigit(), "the count on the review item is a number in the prototype's sample"


def test_a_heading_is_not_the_name_of_the_screen(proto):
    """The menu, the breadcrumb and the document title use one name for a screen; the heading at the top of the screen often does not. An agent that matches menu items to screens by heading gets it wrong."""
    nav, r = proto
    lm = next(l for l in r["landmarks"] if l["name"] == "Main")
    home = next(i for g in lm["groups"] for i in g["items"] if i["label"] == "Home")["leads_to"]
    vee = next(i for g in lm["groups"] for i in g["items"] if i["label"] == "The V")["leads_to"]
    assert home["heading"] != "Home" and vee["heading"] != "The V"


PROTO_BREAKS = [
    ("a menu item renamed in the map", lambda n: n["shell"]["side_bar"]["groups"][0]["items"][1].update(label="Queue"), "holds"),
    ("two menu items swapped in the map", lambda n: n["shell"]["side_bar"]["groups"][1]["items"].reverse(), "the order counts"),
    ("a screen retitled in the map", lambda n: [s.update(title="Summary") for s in n["screens"] if s["id"] == "overview"], "leads to a page titled"),
    ("a group heading changed in the map", lambda n: n["shell"]["side_bar"]["groups"][2].update(heading="Output"), "is headed"),
    ("the skip link reworded in the map", lambda n: n["shell"]["skip_link"].update(label="Skip"), "skip link says"),
    ("the search relabelled in the map", lambda n: n["shell"]["top_bar"]["search"].update(label="Find"), "search box is labelled"),
]


@pytest.mark.parametrize("name,fn,word", PROTO_BREAKS, ids=[b[0] for b in PROTO_BREAKS])
def test_the_prototype_comparison_reports_a_changed_map(proto, name, fn, word):
    nav, r = proto
    n = copy.deepcopy(nav)
    fn(n)
    out = sm.compare_with_navigation(r, n)
    assert out and any(word in o for o in out), "%s: %s" % (name, out)
