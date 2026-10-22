"""The probe's menu checks (probe.check_navigation) against a small fixture app in a real browser, and against the fixture broken on purpose.

Skipped when Playwright or its Chromium is not installed. What this proves:
  - a fixture whose menu follows docs/GUI_TEST_HOOKS.md passes every navigation check, with the map and without it;
  - each way of breaking the fixture listed below makes the check named for it fail. Every break must change the file (the text to replace occurs exactly once),
    so a break can never silently do nothing;
  - an app with no menu gets one 'not applicable' line and no failure, so a one-screen app is not blamed for lacking one (the reference viewer is such an app);
  - every mark the checks read is in the hooks document, and every navigation check id is explained there.
What it does not prove: that the checks catch every way a menu can be wrong, or that a real app's menu is right. The fixture is tiny and made up; the breaks are the ones the
checks were written for. Chromium only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import probe  # noqa: E402
import serve  # noqa: E402


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

DOC = (REPO / "docs" / "GUI_TEST_HOOKS.md").read_text(encoding="utf-8")

# the map the fixture is built from, in the shape of design/navigation.json (only the parts the probe reads)
MAP = {
    "screens": [{"id": "home", "title": "Home", "kind": "workspace"}, {"id": "review", "title": "Review queue", "kind": "workspace"},
                {"id": "explorer", "title": "All requirements", "kind": "workspace"}, {"id": "overview", "title": "Overview", "kind": "workspace"},
                {"id": "vee", "title": "The V", "kind": "workspace"}],
    "shell": {"side_bar": {"label": "Main",
                           "groups": [{"id": "top", "heading": None, "collapsible": False,
                                       "items": [{"screen": "home", "label": "Home"}, {"screen": "review", "label": "Review queue", "count": {"what": "x"}},
                                                 {"screen": "explorer", "label": "All requirements"}]},
                                      {"id": "progress", "heading": "Progress and evidence", "collapsible": True, "default_open": True,
                                       "items": [{"screen": "overview", "label": "Overview"}, {"screen": "vee", "label": "The V"}]}],
                           "layout": {"narrow": {"at_most_width": "900px", "what": "a wrapping row", "all_items_visible": True}}},
              "page_title": {"document_title": "<screen title> · Fixture"}},
}

FIXTURE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Home · Fixture</title>
<style>
body { margin: 0; font: 16px sans-serif; }
.side { position: fixed; top: 0; left: 0; bottom: 0; width: 240px; display: flex; flex-direction: column; }
.main { margin-left: 260px; padding: 16px; }
.side button { text-align: left; padding: 8px; }
@media (max-width: 900px) { .side { position: static; width: auto; flex-direction: row; flex-wrap: wrap; } .main { margin-left: 0; } .heading { display: none; } }
</style></head>
<body data-state="ready">
<nav data-testid="nav" aria-label="Main" class="side">
  <div data-testid="nav-group" data-group="top">
    <button data-testid="nav-item" data-screen="home">Home</button>
    <button data-testid="nav-item" data-screen="review">Review queue</button>
    <button data-testid="nav-item" data-screen="explorer">All requirements</button>
  </div>
  <div data-testid="nav-group" data-group="progress">
    <div class="heading">Progress and evidence</div>
    <button data-testid="nav-item" data-screen="overview">Overview</button>
    <button data-testid="nav-item" data-screen="vee">The V</button>
  </div>
</nav>
<div class="main">
  <div data-testid="breadcrumb" id="crumb"></div>
  <section data-testid="screen" id="screen" data-screen="home"></section>
</div>
<script>
const TITLES = {home: "Home", review: "Review queue", explorer: "All requirements", overview: "Overview", vee: "The V"};
const BODY = {home: "Welcome. Nothing is waiting.", review: "The queue is empty.", explorer: "Every requirement is listed here.", overview: "Counts by status.", vee: "The V shows each level."};
let shown = 0;
function show(id) {
  shown += 1;
  document.getElementById("screen").setAttribute("data-screen", id);
  document.getElementById("screen").textContent = BODY[id];
  document.getElementById("crumb").textContent = "Fixture project / " + TITLES[id];
  document.title = TITLES[id] + " · Fixture";
  document.querySelectorAll('[data-testid="nav-item"]').forEach(function (b) { b.setAttribute("aria-current", b.dataset.screen === id ? "page" : "false"); });
}
document.querySelectorAll('[data-testid="nav-item"]').forEach(function (b) { b.addEventListener("click", function () { show(b.dataset.screen); }); });
show("home");
</script>
</body></html>
"""


def write_app(tmp_path, changes=()):
    app = tmp_path / "app"
    app.mkdir()
    text = FIXTURE
    for old, new in changes:
        assert text.count(old) == 1, "%r occurs %d times in the fixture" % (old[:70], text.count(old))
        text = text.replace(old, new)
    (app / "index.html").write_text(text, encoding="utf-8")
    return app


def run_checks(app, nav=None):
    R = probe.Results()
    with serve.serving(str(app)) as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        P = probe.Page(browser, base)
        P.pg.goto(base + "/")
        P.wait(5000)
        probe.check_navigation(P, R, nav)
        browser.close()
    return R


def failed(R):
    return {r["check"].split("@")[0] for r in R.failed}


# ------------------------------------------------------------------------------------------------ the good fixture
def test_a_menu_that_follows_the_hooks_passes_with_and_without_the_map(tmp_path):
    app = write_app(tmp_path)
    for nav in (None, MAP):
        R = run_checks(app, nav)
        assert not R.failed, "\n".join("%s: %s" % (r["check"], r["detail"]) for r in R.failed)
        ran = {r["check"].split("@")[0] for r in R.rows if not r["skipped"]}
        for needed in ("nav.landmark", "nav.items_listed", "nav.items_are_controls", "nav.starts_on_current_screen", "nav.each_item_opens_its_screen",
                       "nav.each_item_marks_itself_current", "nav.each_screen_has_its_own_content", "nav.breadcrumb_follows", "nav.keeps_the_dataset", "nav.round_trip",
                       "nav.keyboard", "nav.count_not_invented"):
            assert needed in ran, "%s did not run (map: %s)" % (needed, bool(nav))
        if nav:
            assert {"nav.groups", "nav.default_open_visible", "nav.page_title_follows", "nav.narrow_shows_every_item"} <= ran
        else:
            skipped = {r["check"].split("@")[0] for r in R.rows if r["skipped"]}
            assert {"nav.groups", "nav.page_title_follows", "nav.narrow_shows_every_item"} <= skipped


def test_an_app_with_no_menu_gets_one_not_applicable_line_and_no_failure(tmp_path):
    app = write_app(tmp_path, [('<nav data-testid="nav" aria-label="Main" class="side">', '<div class="side">'), ("</nav>", "</div>")])
    R = run_checks(app, MAP)
    assert [(r["check"], r["skipped"], r["ok"]) for r in R.rows] == [("nav.present", True, True)]
    assert "one-screen" in R.rows[0]["detail"]


def test_the_reference_viewer_is_a_one_screen_app_and_is_not_blamed(tmp_path_factory):
    from reqin.cli import main
    d = tmp_path_factory.mktemp("nav_ds") / "ds"
    assert main(["make-datasets", str(d), "--size", "60"]) == 0
    R = probe.run(str(REPO / "design" / "reference_viewer"), str(d), only=["f1"], extras=False, widths=(1440,), navigation=str(REPO / "design" / "navigation.json"))
    rows = [r for r in R.rows if r["scope"] == "navigation"]
    assert [(r["check"], r["skipped"]) for r in rows] == [("nav.present", True)]
    assert not R.failed


# ------------------------------------------------------------------------------------------------ the breaks
VEE = '<button data-testid="nav-item" data-screen="vee">The V</button>'
BREAKS = [
    # (name, changes, check that must fail, with the map or not)
    ("the menu is a div, not a nav landmark", [('<nav data-testid="nav" aria-label="Main" class="side">', '<div data-testid="nav" class="side">'), ("</nav>", "</div>")], "nav.landmark", None),
    ("the menu has no name", [('<nav data-testid="nav" aria-label="Main" class="side">', '<nav data-testid="nav" class="side">')], "nav.landmark", None),
    ("the menu has another name than the map", [('aria-label="Main"', 'aria-label="Sections"')], "nav.landmark", MAP),
    ("an item is missing from the menu", [('    <button data-testid="nav-item" data-screen="explorer">All requirements</button>\n', "")], "nav.items_listed", MAP),
    ("an item is called something else", [(">All requirements</button>", ">Everything</button>")], "nav.items_listed", MAP),
    ("two items name the same screen", [('data-screen="overview">Overview', 'data-screen="vee">Overview')], "nav.items_listed", None),
    ("an item is in the wrong group", [('<div data-testid="nav-group" data-group="progress">', '<div data-testid="nav-group" data-group="other">')], "nav.groups", MAP),
    ("an item is a div nobody can press from the keyboard", [(VEE, '<div data-testid="nav-item" data-screen="vee" tabindex="-1">The V</div>')], "nav.items_are_controls", None),
    ("an item opens another screen", [('show(b.dataset.screen); }); });', 'show(b.dataset.screen === "vee" ? "overview" : b.dataset.screen); }); });')], "nav.each_item_opens_its_screen", None),
    ("the current item is never marked", [('b.setAttribute("aria-current", b.dataset.screen === id ? "page" : "false");', "")], "nav.each_item_marks_itself_current", None),
    ("the current item stays on the first one", [('b.dataset.screen === id ? "page"', 'b.dataset.screen === "home" ? "page"')], "nav.each_item_marks_itself_current", None),
    ("the app starts with a different screen than the item marked", [('show("home");\n</script>', 'show("home"); document.getElementById("screen").setAttribute("data-screen", "review");\n</script>')],
     "nav.starts_on_current_screen", None),
    ("the screens all show the same words", [('textContent = BODY[id];', 'textContent = BODY.home;')], "nav.each_screen_has_its_own_content", None),
    ("the breadcrumb is not updated", [('document.getElementById("crumb").textContent = "Fixture project / " + TITLES[id];', 'if (shown === 1) document.getElementById("crumb").textContent = "Fixture project / Home";')],
     "nav.breadcrumb_follows", None),
    ("the page title is not updated", [('document.title = TITLES[id] + " \u00b7 Fixture";', "")], "nav.page_title_follows", MAP),
    ("a screen drops the dataset", [('document.getElementById("screen").textContent = BODY[id];', 'document.getElementById("screen").textContent = BODY[id]; if (id === "overview") document.body.setAttribute("data-state", "idle");')],
     "nav.keeps_the_dataset", None),
    ("a screen throws", [('document.getElementById("screen").textContent = BODY[id];', 'document.getElementById("screen").textContent = BODY[id]; if (id === "overview") nothing.here();')], "nav.keeps_the_dataset", None),
    ("a screen shows different content when you come back", [('textContent = BODY[id];', 'textContent = BODY[id] + (id === "home" ? " (visit " + shown + ")" : "");')], "nav.round_trip", None),
    ("Enter on a focused item does nothing", [('b.addEventListener("click", function () { show(b.dataset.screen); }); });', 'b.addEventListener("mousedown", function () { show(b.dataset.screen); }); });')], "nav.keyboard", None),
    ("a count shows 0 where nothing produces it", [('data-screen="review">Review queue', 'data-screen="review">Review queue <span data-testid="nav-count">0</span>')], "nav.count_not_invented", None),
    ("a count is not a number", [('data-screen="review">Review queue', 'data-screen="review">Review queue <span data-testid="nav-count">lots</span>')], "nav.count_not_invented", None),
    ("a count is on an item the map gives none", [('data-screen="home">Home', 'data-screen="home">Home <span data-testid="nav-count">3</span>')], "nav.count_not_invented", MAP),
    ("an item is hidden in a narrow window", [("@media (max-width: 900px) { .side {", "@media (max-width: 900px) { .side button[data-screen=vee] { display: none; } .side {")], "nav.narrow_shows_every_item", MAP),
    ("an item runs off the edge in a narrow window", [("@media (max-width: 900px) { .side {", "@media (max-width: 900px) { .side button[data-screen=vee] { margin-left: 600px; } .side {")], "nav.narrow_shows_every_item", MAP),
    ("an item in a group that starts open is hidden", [("</style>", ".side button[data-screen=vee] { display: none; }\n</style>")], "nav.default_open_visible", MAP),
]


@pytest.mark.parametrize("name,changes,check,nav", BREAKS, ids=[b[0] for b in BREAKS])
def test_break_(tmp_path, name, changes, check, nav):
    R = run_checks(write_app(tmp_path, changes), nav)
    assert check in failed(R), "%s: %s did not fail; failed: %s" % (name, check, sorted(failed(R)))


def test_the_failure_says_which_item_and_what_was_found(tmp_path):
    R = run_checks(write_app(tmp_path, [('show(b.dataset.screen); }); });', 'show(b.dataset.screen === "vee" ? "overview" : b.dataset.screen); }); });')]))
    row = next(r for r in R.failed if r["check"] == "nav.each_item_opens_its_screen")
    assert "vee" in row["detail"] and "overview" in row["detail"]


# ------------------------------------------------------------------------------------------------ the hooks document
NAV_MARKS = {"nav", "nav-group", "nav-item", "nav-count", "breadcrumb", "screen"}


def test_every_navigation_mark_the_checks_read_is_in_the_hooks_document():
    src = (REPO / "tools" / "gui_checks" / "probe.py").read_text(encoding="utf-8")
    read = {m for m in re.findall(r'data-testid=\\*"([a-z][a-z0-9-]*)', src)} | set(re.findall(r'tid\("([a-z][a-z0-9-]*)"\)', src)) | set(re.findall(r'P\.count\("([a-z][a-z0-9-]*)"\)', src))
    assert NAV_MARKS <= read, "marks the checks no longer read: %s" % sorted(NAV_MARKS - read)
    section = DOC.split("## Navigation marks", 1)[1].split("\n## ", 1)[0]
    cells = set()
    for cell in re.findall(r"^\|\s*((?:`[^`]+`(?:,\s*|\s+and\s+|\s*)?)+)\s*\|", section, flags=re.M):
        cells |= set(re.findall(r"`([a-z][a-z0-9-]*)`", cell))
    assert NAV_MARKS <= cells, "marks the document does not define in its Navigation marks section: %s" % sorted(NAV_MARKS - cells)


def test_every_navigation_check_id_is_explained_in_the_hooks_document(tmp_path):
    R = run_checks(write_app(tmp_path), MAP)
    ids = {r["check"].split("@")[0] for r in R.rows}
    assert len(ids) >= 15
    for cid in sorted(ids):
        assert cid in DOC, "%s is not explained in docs/GUI_TEST_HOOKS.md" % cid


def test_the_map_the_fixture_uses_has_the_shape_of_the_real_map():
    real = json.loads((REPO / "design" / "navigation.json").read_text(encoding="utf-8"))
    assert set(MAP["shell"]["side_bar"]) <= set(real["shell"]["side_bar"])
    assert probe.expected_menu(real)["narrow_all_visible"] is True
    assert probe.expected_menu(real)["narrow_width"] == 900
    assert [i["screen"] for i in probe.expected_menu(real)["items"]][:3] == ["home", "review", "explorer"]
