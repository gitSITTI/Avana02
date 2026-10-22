"""design/navigation.json says how the product's screens, menus and content relate. This checks the checker (tools/gui_checks/check_navigation.py) and the map: the map is
clean, it agrees with the prototype's source, the page for people is what the JSON produces now, and every rule fires when it is broken. A rule that was never seen to
fail proves nothing, so each one has a test that breaks the map or the source in one way and expects that error.

Standard library and pytest only: this runs in the CI job that installs nothing else."""
from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import check_navigation as cn  # noqa: E402

NAV_PATH = REPO / "design" / "navigation.json"
MAP_PATH = REPO / "docs" / "SCREEN_DATA_MAP.md"
DOC_PATH = REPO / "docs" / "NAVIGATION_MAP.md"
PROTO = REPO / "prototype"


@pytest.fixture()
def nav():
    return json.loads(NAV_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def data_map():
    return MAP_PATH.read_text(encoding="utf-8")


def errors(nav, data_map=None):
    return cn.check(nav, data_map, REPO)


def has(errs, *words):
    return any(all(w in e for w in words) for e in errs)


# ------------------------------------------------------------------------------------------------ the committed map
def test_the_map_is_clean_on_its_own_and_against_the_data_map(nav, data_map):
    assert errors(nav, data_map) == []


def test_the_map_agrees_with_the_prototypes_source(nav):
    assert cn.check_prototype(nav, cn.scan_prototype(PROTO)) == []


def test_the_page_for_people_is_what_the_map_produces_now(nav, data_map):
    assert DOC_PATH.read_text(encoding="utf-8") == cn.render_doc(nav, data_map), "run: python3 tools/gui_checks/check_navigation.py --prototype prototype --write-doc docs/NAVIGATION_MAP.md"


def test_the_command_line_passes_and_fails(tmp_path, capsys, nav):
    assert cn.main(["--prototype", str(PROTO), "--check-doc", str(DOC_PATH)]) == 0
    assert "checked against the prototype" in capsys.readouterr().out
    bad = copy.deepcopy(nav)
    bad["flows"][0]["to"] = "nowhere"
    f = tmp_path / "n.json"
    f.write_text(json.dumps(bad), encoding="utf-8")
    assert cn.main([str(f)]) == 1
    assert "nowhere" in capsys.readouterr().out
    assert cn.main([str(tmp_path / "missing.json")]) == 1


def test_a_stale_page_for_people_is_refused(tmp_path, capsys):
    stale = tmp_path / "doc.md"
    stale.write_text(DOC_PATH.read_text(encoding="utf-8").replace("Home", "Hom", 1), encoding="utf-8")
    assert cn.main(["--check-doc", str(stale)]) == 1
    assert "not what design/navigation.json produces" in capsys.readouterr().out


def test_every_screen_in_the_map_can_be_reached_and_the_start_is_zero_moves(nav):
    dist = cn.reachable(nav)
    assert dist[nav["start"]] == 0 and set(dist) == {s["id"] for s in nav["screens"]}


# ------------------------------------------------------------------------------------------------ the rules fire
def mutate(nav, fn):
    n = copy.deepcopy(nav)
    fn(n)
    return n


def screen(n, sid):
    return next(s for s in n["screens"] if s["id"] == sid)


def item(n, sid):
    for g in n["shell"]["side_bar"]["groups"]:
        for it in g["items"]:
            if it["screen"] == sid:
                return g, it
    raise KeyError(sid)


CASES = [
    ("wrong format", lambda n: n.update(format="x"), ["format must be"]),
    ("no start", lambda n: n.update(start="nope"), ["start 'nope' is not a screen"]),
    ("start is a workspace screen", lambda n: n.update(start="home"), ["must be an entry screen"]),
    ("duplicate screen id", lambda n: n["screens"].append(dict(screen(n, "home"))), ["is already used"]),
    ("badly formed id", lambda n: screen(n, "home").update(id="Home Page"), ["must be lower case words"]),
    ("kind unknown", lambda n: screen(n, "home").update(kind="page"), ["kind must be one of"]),
    ("no title", lambda n: screen(n, "home").update(title=""), ["title must say"]),
    ("two workspace screens with one title", lambda n: screen(n, "policy").update(title="Home"), ["both titled"]),
    ("data map section not a number", lambda n: screen(n, "home").update(data_map=["Home"]), ["must be a list of section numbers"]),
    ("a section that does not exist", lambda n: screen(n, "home").update(data_map=["4.99"]), ["claims section 4.99"]),
    ("a section nobody claims", lambda n: screen(n, "explorer").update(data_map=["4.99"]), ["claimed by no screen"]),
    ("two screens claim one section", lambda n: screen(n, "gold").update(data_map=["4.13"]), ["also claimed by"]),
    ("step names a section the screen does not list", lambda n: screen(n, "import")["steps"][0].update(data_map=["4.9"]), ["does not list"]),
    ("workspace screen with no menu item", lambda n: item(n, "policy")[0]["items"].remove(item(n, "policy")[1]), ["workspace screen policy has no menu item"]),
    ("menu item for a screen that does not exist", lambda n: item(n, "policy")[1].update(screen="ghost"), ["not a screen"]),
    ("menu item for an entry screen", lambda n: item(n, "policy")[1].update(screen="open"), ["has no side bar"]),
    ("two items for one screen", lambda n: item(n, "home")[0]["items"].append({"screen": "home", "label": "Again", "icon": "home"}), ["already has a menu item"]),
    ("two items with one label", lambda n: item(n, "policy")[1].update(label="Home"), ["labelled 'Home'"]),
    ("an item without an icon", lambda n: item(n, "home")[1].update(icon=""), ["icon must name"]),
    ("a count with no source", lambda n: item(n, "review")[1]["count"].update(sources=[]), ["a count needs"]),
    ("a count from a made-up path", lambda n: item(n, "review")[1]["count"].update(sources=["the clusters"]), ["is not WORK, STATIC, NONE or a field path"]),
    ("a count with no fallback", lambda n: item(n, "review")[1]["count"].pop("no_producer"), ["a count needs"]),
    ("a group that folds with no start state", lambda n: n["shell"]["side_bar"]["groups"][1].pop("default_open"), ["whether it starts open"]),
    ("a group that folds with no heading", lambda n: n["shell"]["side_bar"]["groups"][1].update(heading=None), ["needs a heading"]),
    ("foot item both opens and goes", lambda n: n["shell"]["side_bar"]["foot"][0].update(goes_to="open"), ["either what it opens or where it goes"]),
    ("foot item goes to a ghost", lambda n: n["shell"]["side_bar"]["foot"][1].update(goes_to="ghost"), ["not a screen"]),
    ("shortcut with two targets", lambda n: n["shell"]["top_bar"]["shortcuts"][0].update(opens="glossary"), ["exactly one of goes_to"]),
    ("shortcut to a ghost screen", lambda n: n["shell"]["top_bar"]["shortcuts"][0].update(goes_to="ghost"), ["not a screen"]),
    ("search to a ghost screen", lambda n: n["shell"]["top_bar"]["search"]["when_text_entered"].update(goes_to="ghost"), ["when_text_entered.goes_to"]),
    ("chip from a made-up path", lambda n: n["shell"]["top_bar"]["chips"][0].update(sources=["scope"]), ["is not WORK"]),
    ("overlay opened by a control that is not there", lambda n: n["overlays"][0].update(opened_by=["top_bar.shortcuts[Nothing]"]), ["is not a control in the shell"]),
    ("overlay opened by another overlay's control", lambda n: n["overlays"][0].update(opened_by=["top_bar.shortcuts[Ask the assistant]"]), ["opens 'assistant', not this overlay"]),
    ("overlay with no way to close it", lambda n: n["overlays"][0].update(closed_by=""), ["closed_by must say how"]),
    ("sheet opened from a ghost", lambda n: n["sheets"][0].update(opened_from=["ghost"]), ["opened_from must list screens"]),
    ("a move to a ghost", lambda n: n["flows"][0].update(to="ghost"), ["not a screen"]),
    ("a move from a ghost", lambda n: n["flows"][0].update({"from": ["ghost"]}), ["from must be"]),
    ("a move that says nothing about what it carries", lambda n: n["flows"][0].update(carries=""), ["carries must say"]),
    ("a move with no control", lambda n: n["flows"][0].update(control=" "), ["control must say"]),
    ("a move with no evidence", lambda n: n["flows"][0].pop("evidence"), ["evidence must say"]),
    ("an excuse with no reason", lambda n: n["not_navigation"][0].pop("why"), ["not_navigation[0] needs"]),
    ("a screen nothing leads to", lambda n: n["screens"].append({"id": "island", "title": "Island", "kind": "entry", "data_map": ["4.1"]}) or n["flows"].append({"from": ["island"], "to": "open", "control": "x", "carries": "nothing", "evidence": "x y"}), ["screen island cannot be reached"]),
    ("an entry screen that leads nowhere", lambda n: n["flows"].__setitem__(slice(None), [f for f in n["flows"] if f["from"] != ["import"]]), ["entry screen import leads nowhere"]),
    ("a missing component spec", lambda n: screen(n, "home").update(component_spec="design/none.json"), ["component_spec design/none.json does not exist"]),
]


@pytest.mark.parametrize("name,fn,words", CASES, ids=[c[0] for c in CASES])
def test_each_rule_fires(nav, data_map, name, fn, words):
    errs = errors(mutate(nav, fn), data_map)
    assert errs, "%s: the map was broken and the check said nothing" % name
    assert has(errs, *words), "%s: expected an error with %s, got %s" % (name, words, errs)


def test_a_screen_with_no_menu_item_is_allowed_when_it_says_how_a_person_gets_there(nav, data_map):
    def f(n):
        g, it = item(n, "policy")
        g["items"].remove(it)
        screen(n, "policy").update(in_menu=False, note="Reached only from the AI use screen")
        n["flows"].append({"from": ["ai"], "to": "policy", "control": "a link", "carries": "nothing", "evidence": "c8.js valsAiPolicy"})
    assert errors(mutate(nav, f), data_map) == []
    def g2(n):
        g, it = item(n, "policy")
        g["items"].remove(it)
        screen(n, "policy").update(in_menu=False)
    assert has(errors(mutate(nav, g2), data_map), "a note must say how a person gets there")


def test_a_screen_that_says_it_has_no_menu_item_and_has_one_is_refused(nav, data_map):
    assert has(errors(mutate(nav, lambda n: screen(n, "policy").update(in_menu=False, note="x")), data_map), "says in_menu is false and has a menu item")


def test_with_no_moves_listed_nothing_leads_out_of_the_start_screen(nav):
    n = mutate(nav, lambda x: x.update(flows=[]))
    dist = cn.reachable(n)
    assert dist.get("open") == 0 and "home" not in dist, "with no moves at all, nothing leads out of the start screen"


# ------------------------------------------------------------------------------------------------ against the prototype's source
@pytest.fixture()
def proto_copy(tmp_path):
    dest = tmp_path / "prototype" / "parts"
    (dest / "m").mkdir(parents=True)
    for f in (REPO / "prototype" / "parts").glob("c[0-9].js"):
        shutil.copy(f, dest / f.name)
    shutil.copy(REPO / "prototype" / "parts" / "data1.js", dest / "data1.js")
    for f in (REPO / "prototype" / "parts" / "m").glob("*.html"):
        shutil.copy(f, dest / "m" / f.name)
    return tmp_path / "prototype"


def edit(proto, rel, old, new, count=1):
    p = proto / "parts" / rel
    t = p.read_text(encoding="utf-8")
    assert t.count(old) == count, "%s: %r occurs %d times, expected %d" % (rel, old[:50], t.count(old), count)
    p.write_text(t.replace(old, new), encoding="utf-8")


def against(nav, proto):
    return cn.check_prototype(nav, cn.scan_prototype(proto))


def test_a_copy_of_the_prototype_is_clean(nav, proto_copy):
    assert against(nav, proto_copy) == []


SOURCE_BREAKS = [
    ("a jump added to the source", "c1.js", "openOverview: () => this.setState({ view: 'overview' }),", "openOverview: () => this.setState({ view: 'overview' }), sneak: () => this.setState({ view: 'policy' }),", ["c1.js valsHome leads to"]),
    ("a jump removed from the source", "c1.js", "openOverview: () => this.setState({ view: 'overview' }),", "", ["c1.js valsHome leads to"]),
    ("a jump to another screen", "c1.js", "openOverview: () => this.setState({ view: 'overview' }),", "openOverview: () => this.setState({ view: 'vee' }),", ["c1.js valsHome leads to"]),
    ("a whole handler that is new", "c4.js", "gToMetrics: () => this.setState({ view: 'methods' }),", "gToMetrics: () => this.setState({ view: 'methods' }), other: () => this.setState({ view: 'audit' }),", ["c4.js valsGold leads to"]),
    ("a screen renamed", "c1.js", "overview: 'Overview'", "overview: 'Summary'", ["screen overview is titled"]),
    ("a menu group reordered", "c1.js", "navProg: ['overview', 'vee',", "navProg: ['vee', 'overview',", ["menu group 'progress' holds"]),
    ("a menu item moved to another group", "c1.js", "navTop: ['home', 'review', 'explorer'].map(item)", "navTop: ['home', 'review'].map(item)", ["menu group 'top' holds"]),
    ("a new screen with no entry in the map", "c3.js", "v.isExport = S.view === 'export';", "v.isExport = S.view === 'export'; v.isTrash = S.view === 'trash';", ["the screens differ"]),
    ("another start screen", "data1.js", "view: 'open', source: 'sample'", "view: 'home', source: 'sample'", ["the start screen is"]),
    ("a group heading renamed", "m/30_shell_open.html", "<span>Progress and evidence</span>", "<span>Progress</span>", ["folding group headings"]),
    ("a foot item renamed", "m/30_shell_open.html", "<span>Close project</span>", "<span>Quit</span>", ["the foot of the side bar"]),
    ("the side bar renamed for a screen reader", "m/30_shell_open.html", 'aria-label="Main"', 'aria-label="Menu"', ["accessible name"]),
    ("the search relabelled", "m/30_shell_open.html", 'aria-label="Search requirements"', 'aria-label="Find"', ["search is labelled"]),
    ("the skip link reworded", "m/30_shell_open.html", ">Skip to the main content<", ">Skip<", ["skip link says"]),
    ("a page title changed", "c3.js", "'Open a requirements project'", "'Open a project'", ["page titles"]),
    ("the document title changed", "c3.js", "' · Requirements Consolidator'", "' | Consolidator'", ["document title"], 2),
    ("a screen's markup block removed", "m/35_home.html", '{{isHome}}', '{{isHomeX}}', ["does not switch on {{isHome}}"]),
    ("a menu group starts folded", "data1.js", "navClosed: {}", "navClosed: { prog: true }", ["starts with a menu group folded"]),
]


@pytest.mark.parametrize("name,rel,old,new,words,count", [(c + (1,))[:6] for c in SOURCE_BREAKS], ids=[c[0] for c in SOURCE_BREAKS])
def test_a_change_in_the_prototype_source_that_the_map_does_not_have_is_found(nav, proto_copy, name, rel, old, new, words, count):
    edit(proto_copy, rel, old, new, count=count)
    errs = against(nav, proto_copy)
    assert errs, "%s: the source changed and the check said nothing" % name
    assert has(errs, *words), "%s: expected an error with %s, got %s" % (name, words, errs)


def test_a_source_that_no_longer_has_the_shape_is_reported_not_passed(nav, proto_copy):
    edit(proto_copy, "c1.js", "const NAME = {", "const TITLES = {")
    with pytest.raises(ValueError, match="NAME map"):
        cn.scan_prototype(proto_copy)
    assert cn.main([str(NAV_PATH), "--prototype", str(proto_copy)]) == 1


def test_a_move_the_map_lists_and_the_source_does_not_make_is_found(nav, proto_copy):
    n = mutate(nav, lambda x: x["flows"].append({"from": ["home"], "to": "policy", "control": "a ghost button", "carries": "nothing", "evidence": "c1.js valsHomeGhost"}))
    assert has(against(n, proto_copy), "the map lists a move from c1.js valsHomeGhost")


def test_an_excuse_for_a_jump_that_is_not_there_is_found(nav, proto_copy):
    n = mutate(nav, lambda x: x["not_navigation"].append({"evidence": "c1.js nothingHere", "why": "x"}))
    assert has(against(n, proto_copy), "not_navigation excuses c1.js nothingHere")


def test_the_scan_finds_every_jump_the_source_makes_and_none_that_are_only_a_word_in_another_word(proto_copy):
    jumps = cn.scan_prototype(proto_copy)["jumps"]
    assert jumps["c1.js valsHome"] == {"review", "ai", "overview", "open", "audit"}
    assert "c9.js connSignOut" not in jumps, "preview: '' is not a jump"
    assert sum(len(v) for v in jumps.values()) >= 30


# ------------------------------------------------------------------------------------------------ the narrow layout, 'unconfirmed', and where a component leads
def test_the_narrow_layout_must_say_a_width_in_pixels_and_whether_every_item_shows(nav):
    bad = copy.deepcopy(nav)
    bad["shell"]["side_bar"]["layout"]["narrow"]["at_most_width"] = "narrow"
    assert has(errors(bad), "narrow", "pixels")
    bad = copy.deepcopy(nav)
    bad["shell"]["side_bar"]["layout"]["narrow"]["all_items_visible"] = "yes"
    assert has(errors(bad), "all_items_visible", "true or false")
    bad = copy.deepcopy(nav)
    del bad["shell"]["side_bar"]["layout"]["wide"]
    assert has(errors(bad), "wide layout")
    assert nav["shell"]["side_bar"]["layout"]["narrow"]["all_items_visible"] is True


def test_an_unconfirmed_entry_must_say_what_is_not_known_and_is_listed_for_people(nav, data_map):
    assert cn.unconfirmed(nav) == []
    guess = copy.deepcopy(nav)
    guess["flows"][0]["unconfirmed"] = "read from a picture: the button was not pressed"
    assert errors(guess, data_map) == []
    found = cn.unconfirmed(guess)
    assert len(found) == 1 and found[0][0].startswith("flows[0]") and "not pressed" in found[0][1]
    page = cn.render_doc(guess, data_map)
    assert "## 7. Not confirmed" in page and "not pressed" in page and "## 8. What this page does not say" in page
    assert "Not confirmed" not in cn.render_doc(nav, data_map)
    for empty in ("", "   ", True, None, 3):
        bad = copy.deepcopy(nav)
        bad["screens"][2]["unconfirmed"] = empty
        assert has(errors(bad), "unconfirmed", "what is not known"), repr(empty)


def test_the_command_line_counts_what_is_unconfirmed(tmp_path, capsys, nav):
    guess = copy.deepcopy(nav)
    guess["screens"][3]["unconfirmed"] = "title taken from a picture"
    guess["screens"][4]["unconfirmed"] = "title taken from a picture"
    f = tmp_path / "n.json"
    f.write_text(json.dumps(guess), encoding="utf-8")
    assert cn.main([str(f)]) == 0
    out = capsys.readouterr().out
    assert "2 entries are marked unconfirmed" in out and "review" in out


def test_the_map_says_a_screen_name_is_not_the_heading_inside_it(nav):
    assert any("not always the heading inside the screen" in n for n in nav["notes"])


def _component_checker():
    sys.path.insert(0, str(REPO / "design" / "ui_from_image" / "scripts"))
    import check_component_specs as ccs
    return ccs


def _spec(**over):
    comp = {"name": "go-review", "kind": "button", "states": ["default"], "style": {}, "data": {"label": "STATIC"}}
    comp.update(over)
    return {"format": "reqin-components/1", "components": [comp], "new_tokens": []}


def test_a_component_that_leads_somewhere_must_say_where_and_the_screen_must_exist(nav):
    ccs = _component_checker()
    tokens = ccs.token_names(str(REPO / "design" / "tokens.css"))
    ok = ccs.check(_spec(goes_to="review"), tokens, None, nav)
    assert ok["errors"] == [], ok["errors"]
    for goes, word in (("nowhere", "not a screen in the navigation map"), ("sheet:missing", "not a sheet"), ("overlay:missing", "not an overlay"), ("Review Queue", "is not a screen id")):
        rep = ccs.check(_spec(goes_to=goes), tokens, None, nav)
        assert any(word in e for e in rep["errors"]), (goes, rep["errors"])
    for goes in ("sheet:align", "overlay:glossary", "none: it only changes the list", "external: the project's issue tracker", "unknown: what the arrow does"):
        assert ccs.check(_spec(goes_to=goes), tokens, None, nav)["errors"] == [], goes


def test_a_menu_item_tab_or_link_with_no_goes_to_is_an_error_with_the_map_and_a_warning_without(nav):
    ccs = _component_checker()
    tokens = ccs.token_names(str(REPO / "design" / "tokens.css"))
    for kind in ("nav-item", "tab", "link"):
        spec = _spec(kind=kind, name="menu-thing")
        assert any("must say where it leads" in e for e in ccs.check(spec, tokens, None, nav)["errors"]), kind
        alone = ccs.check(spec, tokens)
        assert alone["errors"] == [] and any("no --navigation file" in w for w in alone["warnings"]), kind
    spec = _spec(kind="button")
    assert any("a button with no goes_to" in w for w in ccs.check(spec, tokens, None, nav)["warnings"])


def test_an_unknown_destination_is_reported_so_nobody_takes_it_for_a_checked_one(nav):
    ccs = _component_checker()
    tokens = ccs.token_names(str(REPO / "design" / "tokens.css"))
    rep = ccs.check(_spec(goes_to="unknown: where the arrow goes"), tokens, None, nav)
    assert any("not confirmed" in w and "where the arrow goes" in w for w in rep["warnings"])
