"""The frames of our screens drawn in a person's theme (design/adopt_design/scripts/frames_theme.py).

Two kinds of test live here.

Offline, standard library and pytest only (they run in the continuous-integration job that installs nothing else): how colours are read and written, which role of ours owns a computed value
(the rules in the module's docstring, tried on plain dicts), how the report is grouped, what the command line refuses and says, and that the module imports without Playwright or Pillow.

In a browser, skipped when Playwright, Pillow, a launchable Chromium or prototype/vendor/node_modules is missing (the same skip as the other *_browser tests): the re-theme on small pages whose every
element is known, and on the real prototype. What they prove:
  - drawing with theirs == ours changes nothing: every picture has the pixels of docs/images/frames/<screen>.png and every frame the box in frames.json (this is the test of the whole remap and of the
    second measuring pass; where a machine cannot reproduce the committed pictures even without the remap, the picture is compared with a plain make_frames drawing made in the same run instead);
  - changing one role moves that role and no other: the main button's pixels take a new accent, the page and surface pixels stay; square control corners square the buttons and leave the cards round;
  - a bigger body text makes a taller page and the boxes of the frames are the ones measured after that;
  - the report names the colours that are meaning (the greens, ambers and reds of the status chips) and does not name the colours of the roles;
  - drawing stops, names the frame and writes nothing when the prototype stopped matching frames_spec.json.
What they do not prove: that the themed pictures look good (a person has to look at them), that another Chromium or another set of installed fonts draws the same pixels, that hover, focus and
pseudo-element states are re-themed (they are not), or that a person's own page would look like this.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import warnings
from functools import lru_cache
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "adopt_design"
sys.path.insert(0, str(KIT / "scripts"))

import adopt  # noqa: E402
import frames_theme as FT  # noqa: E402
import make_frames as MF  # noqa: E402
import roles as R  # noqa: E402
from common import digest, read_json  # noqa: E402

SCRIPT = KIT / "scripts" / "frames_theme.py"
SAMPLE_PAGE = KIT / "examples" / "sample_app" / "index.html"
SAMPLE_INDEX = KIT / "examples" / "sample_index"
NODE_MODULES = REPO / "prototype" / "vendor" / "node_modules" / "react"
OURS = FT.default_ours()
INDEX_NAME = FT.INDEX_NAME

# a theme that moves every role (the colours are clearly not ours, the fonts are installed on most machines that draw)
ALL_CHANGED = {"accent": "#B5179E", "accent-text": "#101010", "page": "#FFF8E1", "surface": "#FFFDF5", "ink": "#2B1B3D", "ink-muted": "#6B5B7B", "border": "#CDB4DB", "border-control": "#8E6BB5",
               "hover": "#F3E5F5", "selected": "#E1BEE7", "font-body": "Inter, sans-serif", "font-statement": "DejaVu Serif, serif", "font-mono": "DejaVu Sans Mono, monospace",
               "size-body": "16px", "size-small": "14px", "size-title": "36px", "radius-control": "20px", "radius-panel": "4px", "radius-chip": "12px",
               "shadow-card": "0 4px 12px rgba(0,0,0,.25)", "control-height": "48px"}


def tables(**changes):
    return FT.build_tables(OURS, {k.replace("_", "-"): v for k, v in changes.items()})


def facts(**kw):
    return {"control": False, "h1": False, "root": False, "on_accent": False, **kw}


# ============================================================================================================ colours
@pytest.mark.parametrize("text, expect", [
    ("#fff", "rgb(255, 255, 255)"), ("#FFF", "rgb(255, 255, 255)"), ("#1a4db5", "rgb(26, 77, 181)"), ("#1A4DB5", "rgb(26, 77, 181)"),
    ("#1A4DB5FF", "rgb(26, 77, 181)"), ("#1A4DB580", "rgba(26, 77, 181, 0.502)"), ("#0008", "rgba(0, 0, 0, 0.533)"),
    ("rgb(26, 77, 181)", "rgb(26, 77, 181)"), ("rgb(26 77 181)", "rgb(26, 77, 181)"), ("rgb(10%, 20%, 30%)", "rgb(26, 51, 77)"),
    ("rgba(255,255,255,.94)", "rgba(255, 255, 255, 0.94)"), ("rgba(255, 255, 255, 1)", "rgb(255, 255, 255)"), ("rgb(26 77 181 / 50%)", "rgba(26, 77, 181, 0.5)"),
    ("color(srgb 0.910196 0.930196 0.97098)", "rgb(232, 237, 248)"), ("hsl(0, 100%, 50%)", "rgb(255, 0, 0)"), ("hsla(120, 100%, 25%, .5)", "rgba(0, 128, 0, 0.5)"),
    ("white", "rgb(255, 255, 255)"), ("WHITE", "rgb(255, 255, 255)"), ("black", "rgb(0, 0, 0)"), ("rebeccapurple", "rgb(102, 51, 153)"), ("transparent", "rgba(0, 0, 0, 0)"),
    ("  #fff  ", "rgb(255, 255, 255)")])
def test_colours_are_written_the_way_the_browser_writes_a_computed_one(text, expect):
    assert FT.norm_colour(text) == expect


@pytest.mark.parametrize("text", ["", "banana", "#12", "#12345", "#GGGGGG", "rgb(1, 2)", "rgb(1, 2, 3, 4, 5)", "rgb(a, b, c)", "hsl(0, 50, 50)", "color(display-p3 1 0 0)", "currentcolor", "inherit", None, 12])
def test_a_text_that_is_not_a_colour_is_none(text):
    assert FT.parse_colour(text) is None and FT.norm_colour(text) is None


def test_hex_is_only_given_for_an_opaque_colour_and_alpha_is_multiplied_in():
    assert FT.hex_colour("rgb(26, 77, 181)") == "#1A4DB5" and FT.hex_colour("white") == "#FFFFFF"
    assert FT.hex_colour("rgba(0, 0, 0, 0.5)") is None
    assert FT.with_alpha("#202020", 0.94) == "rgba(32, 32, 32, 0.94)"
    assert FT.with_alpha("rgba(32, 32, 32, 0.5)", 0.5) == "rgba(32, 32, 32, 0.25)"


def test_there_are_one_hundred_and_forty_eight_named_colours_and_the_ones_everybody_uses_are_right():
    assert len(FT.NAMED) == 148
    assert FT.NAMED["red"] == (255, 0, 0) and FT.NAMED["gray"] == FT.NAMED["grey"] == (128, 128, 128) and FT.NAMED["navy"] == (0, 0, 128)


# ============================================================================================================ values of a theme
@pytest.mark.parametrize("role, raw, expect", [
    ("accent", "#0f766e", "#0F766E"), ("accent", "rgb(15, 118, 110)", "#0F766E"), ("accent", "teal", "#008080"), ("accent", "#0f766e80", "rgba(15, 118, 110, 0.502)"),
    ("radius-control", "0", "0px"), ("radius-control", "8px", "8px"), ("radius-control", "0.5rem", "8px"), ("radius-control", "12", "12px"), ("size-body", "14.50px", "14.5px"),
    ("font-body", "  Inter,   sans-serif ", "Inter, sans-serif"), ("font-mono", "'JetBrains Mono', monospace", "'JetBrains Mono', monospace"),
    ("shadow-card", "none", "none"), ("shadow-card", "0 1px 3px rgba(0,0,0,.2)", "0 1px 3px rgba(0,0,0,.2)")])
def test_a_value_is_checked_and_written_in_its_usual_form(role, raw, expect):
    assert FT.check_value(role, raw) == expect


@pytest.mark.parametrize("role, raw, words", [
    ("accent", "banana", "not a colour"), ("accent", "#12", "not a colour"), ("accent", "", "must be text"), ("accent", None, "must be text"), ("accent", 12, "must be text"),
    ("radius-control", "wide", "not a length"), ("radius-control", "-4px", "not a length"), ("radius-control", "12pt", "not a length"), ("size-body", "auto", "not a length"),
    ("font-body", "12345", "not a font stack"), ("font-body", "Inter; color: red", "not a plain value"), ("font-body", "Inter } body {", "not a plain value"),
    ("font-body", "url(x.woff2)", "not a plain value"), ("shadow-card", "banana", "not a shadow"), ("shadow-card", "0 1px 2px red; x", "not a plain value"),
    ("colour", "#fff", "not a role"), ("", "#fff", "not a role")])
def test_a_value_that_is_not_one_of_its_kind_is_refused_with_a_message_that_names_the_role(role, raw, words):
    with pytest.raises(ValueError) as e:
        FT.check_value(role, raw)
    assert words in str(e.value)
    if role in R.BY_ID:
        assert role in str(e.value)


def test_a_theme_that_leaves_roles_out_keeps_ours_for_them_and_an_unknown_role_is_refused():
    t = FT.complete_theme({"accent": "#FF0000"}, OURS)
    assert set(t) == set(R.ROLE_IDS) and t["accent"] == "#FF0000"
    assert all(FT.same_value(r, t[r], OURS[r]) for r in R.ROLE_IDS if r != "accent")
    with pytest.raises(ValueError, match="'colour' is not a role"):
        FT.complete_theme({"colour": "#fff"}, OURS)


def test_values_are_the_same_when_they_draw_the_same():
    assert FT.same_value("accent", "#1A4DB5", "rgb(26, 77, 181)") and not FT.same_value("accent", "#1A4DB5", "#1A4DB6")
    assert not FT.same_value("surface", "#FFFFFF", "rgba(255, 255, 255, 0.9)")
    assert FT.same_value("radius-control", "8px", "0.5rem") and not FT.same_value("radius-control", "8px", "9px")
    assert FT.same_value("font-body", "'Public Sans', system-ui", "Public Sans, Arial") and not FT.same_value("font-body", "Public Sans", "Inter")
    assert FT.same_value("shadow-card", "0 1px 2px red", "0  1px   2px RED") and not FT.same_value("shadow-card", "none", "0 1px 2px red")


def test_a_font_stack_ends_in_a_generic_family_so_a_missing_font_falls_back_to_its_own_kind():
    assert FT.font_stack("font-body", "Inter") == "Inter, sans-serif"
    assert FT.font_stack("font-statement", "Georgia") == "Georgia, serif"
    assert FT.font_stack("font-mono", "Fira Code") == "Fira Code, monospace"
    assert FT.font_stack("font-body", "Inter, system-ui") == "Inter, system-ui" and FT.font_stack("font-mono", "'Fira Code', Monospace") == "'Fira Code', Monospace"


# ============================================================================================================ the tables
def test_a_theme_equal_to_ours_changes_no_role_and_writes_nothing():
    t = FT.build_tables(OURS, dict(OURS))
    assert t["changed"] == [] and t["target"] == {}
    t = FT.build_tables(OURS, {})
    assert t["changed"] == []


def test_only_the_roles_that_differ_are_changed_and_a_forgiving_equality_is_not_used():
    t = tables(accent="#D81B60", radius_control="0px")
    assert t["changed"] == ["accent", "radius-control"] and t["target"] == {"accent": "#D81B60", "radius-control": "0px"}
    assert tables(accent="#1A4DB6")["changed"] == ["accent"], "one digit off is a different colour"
    assert tables(font_body="'Public Sans', Arial")["changed"] == [], "the same first family is the same font"
    assert tables(radius_control="0.5rem")["changed"] == [], "0.5rem is 8px"


def test_every_value_a_role_names_in_the_tokens_is_ours_not_only_the_first():
    t = tables(accent="#D81B60")
    c = t["colour"]
    assert c[(84, 98, 111)] == ["ink-muted"], "--slate is the quiet grey most of the page uses"
    assert {c[(79, 91, 102)][0], c[(60, 72, 82)][0], c[(90, 102, 114)][0]} == {"ink-muted"}
    assert {c[(27, 39, 51)][0], c[(42, 53, 63)][0], c[(18, 23, 28)][0]} == {"ink"}
    assert {c[(216, 223, 230)][0], c[(231, 236, 241)][0], c[(227, 231, 234)][0], c[(213, 218, 222)][0]} == {"border"}
    assert c[(122, 135, 147)] == ["border-control"] and c[(238, 242, 246)] == ["hover"] and c[(243, 245, 248)] == ["page"]
    assert t["font"] == {"public sans": "font-body", "source serif 4": "font-statement", "jetbrains mono": "font-mono"}
    assert t["size"] == {14.0: "size-body", 13.0: "size-small", 30.0: "size-title"}
    assert t["radius"] == {"control": {8.0}, "panel": {12.0, 14.0}, "chip": {4.0, 6.0}}
    assert t["height"] == {40.0: 0, 44.0: 4, 36.0: -4, 32.0: -8}


def test_white_is_two_roles_and_a_colour_that_the_info_colour_shares_with_selected_is_left_alone():
    t = tables(accent="#D81B60")
    assert sorted(t["colour"][(255, 255, 255)]) == ["accent-text", "surface"]
    assert (232, 240, 253) not in t["colour"], "--surface-selected-2 is the same #E8F0FD as --info-fill, which is meaning"
    assert ("selected", "rgb(232, 240, 253)") in t["dropped"]
    assert t["colour"][(241, 246, 255)] == ["selected"], "the role's own first value is never dropped"


# ============================================================================================================ which role owns a value
RADIUS_THEME = {"radius_control": "1px", "radius_panel": "2px", "radius_chip": "3px"}
# (what changed in the theme, property, computed value, facts, expected role, expected value to write, words the "why" has)
CASES = [
    # text colours
    ({"ink": "#FF0000"}, "color", "rgb(27, 39, 51)", {}, "ink", "#FF0000", None),
    ({"ink": "#FF0000"}, "color", "rgb(42, 53, 63)", {}, "ink", "#FF0000", None),
    ({"ink": "#FF0000"}, "color", "rgb(18, 23, 28)", {}, "ink", "#FF0000", None),
    ({"ink_muted": "#00FF00"}, "color", "rgb(84, 98, 111)", {}, "ink-muted", "#00FF00", None),
    ({"ink_muted": "#00FF00"}, "color", "rgb(79, 91, 102)", {}, "ink-muted", "#00FF00", None),
    ({"ink_muted": "#00FF00"}, "color", "rgb(60, 72, 82)", {}, "ink-muted", "#00FF00", None),
    ({"accent": "#D81B60"}, "color", "rgb(26, 77, 181)", {}, "accent", "#D81B60", None),
    ({"ink": "#FF0000"}, "color", "rgb(84, 98, 111)", {}, "ink-muted", None, None),                 # a role that did not change is found but not written
    ({"ink": "#FF0000"}, "color", "rgb(20, 80, 43)", {}, None, None, None),                            # the green of a pass chip is meaning
    ({"ink": "#FF0000"}, "color", "rgb(0, 0, 0)", {}, None, None, None),                               # the browser's own black
    ({"ink": "#FF0000"}, "color", "rgba(0, 0, 0, 0)", {}, None, None, None),
    # white text: accent-text only on our accent
    ({"accent_text": "#101010"}, "color", "rgb(255, 255, 255)", {"on_accent": True}, "accent-text", "#101010", None),
    ({"accent_text": "#101010"}, "color", "rgb(255, 255, 255)", {"on_accent": False}, None, None, "not our main action colour"),
    ({"surface": "#202020"}, "color", "rgb(255, 255, 255)", {"on_accent": True}, "accent-text", None, None),
    ({"surface": "#202020"}, "color", "rgb(255, 255, 255)", {"on_accent": False}, None, None, "not our main action colour"),
    # backgrounds: white is the surface, never the text on the accent
    ({"surface": "#202020", "accent_text": "#101010"}, "background-color", "rgb(255, 255, 255)", {}, "surface", "#202020", None),
    ({"surface": "#202020", "accent_text": "#101010"}, "background-color", "rgb(255, 255, 255)", {"on_accent": True}, "surface", "#202020", None),
    ({"surface": "#202020"}, "background-color", "rgba(255, 255, 255, 0.94)", {}, "surface", "rgba(32, 32, 32, 0.94)", None),    # opacity is kept
    ({"surface": "#202020"}, "background-color", "rgba(255, 255, 255, 0.1)", {}, None, None, None),                               # a faint overlay is not a surface
    ({"accent": "#D81B60"}, "background-color", "rgb(26, 77, 181)", {}, "accent", "#D81B60", None),
    ({"hover": "#00FFFF"}, "background-color", "rgb(238, 242, 246)", {}, "hover", "#00FFFF", None),
    ({"selected": "#FFFF00"}, "background-color", "rgb(241, 246, 255)", {}, "selected", "#FFFF00", None),
    ({"selected": "#FFFF00"}, "background-color", "rgb(232, 240, 253)", {}, None, None, None),                                     # the info fill
    ({"page": "#EEDDCC"}, "background-color", "rgb(243, 245, 248)", {}, "page", "#EEDDCC", None),
    ({"accent": "#D81B60"}, "background-color", "color(srgb 0.910196 0.930196 0.97098)", {}, None, None, None),                  # a tint made of the accent: it follows the token, not a role
    ({"accent": "#D81B60"}, "background-color", "rgba(0, 0, 0, 0)", {}, None, None, None),
    # borders: the four sides are one property
    ({"border": "#FF00FF"}, "border-top-color", "rgb(216, 223, 230)", {}, "border", "#FF00FF", None),
    ({"border": "#FF00FF"}, "border-left-color", "rgb(231, 236, 241)", {}, "border", "#FF00FF", None),
    ({"border": "#FF00FF"}, "border-bottom-color", "rgb(213, 218, 222)", {}, "border", "#FF00FF", None),
    ({"border_control": "#FF00FF"}, "border-right-color", "rgb(122, 135, 147)", {}, "border-control", "#FF00FF", None),
    ({"border_control": "#FF00FF"}, "border-top-color", "rgb(123, 135, 146)", {}, None, None, None),                               # one digit away: the explorer's "alone" grey
    ({"border_control": "#FF00FF"}, "border-top-color", "rgb(186, 195, 202)", {}, None, None, None),                               # a quiet outline no role names
    ({"accent": "#D81B60"}, "border-top-color", "rgb(26, 77, 181)", {}, "accent", "#D81B60", None),
    ({"surface": "#202020"}, "border-top-color", "rgb(255, 255, 255)", {}, "surface", "#202020", None),                            # the white ring that separates things
    ({"accent": "#D81B60"}, "outline-color", "rgb(26, 77, 181)", {}, "accent", "#D81B60", None),
    ({"border": "#FF00FF"}, "outline-color", "rgb(216, 223, 230)", {}, "border", "#FF00FF", None),
    # drawings
    ({"accent": "#D81B60"}, "fill", "rgb(26, 77, 181)", {}, "accent", "#D81B60", None),
    ({"surface": "#202020", "accent_text": "#101010"}, "fill", "rgb(255, 255, 255)", {"on_accent": False}, "surface", "#202020", None),
    ({"surface": "#202020", "accent_text": "#101010"}, "stroke", "rgb(255, 255, 255)", {"on_accent": True}, "accent-text", "#101010", None),
    ({"ink_muted": "#00FF00"}, "stroke", "rgb(84, 98, 111)", {}, "ink-muted", "#00FF00", None),
    # fonts, by the first family
    ({"font_body": "Inter"}, "font-family", '"Public Sans", system-ui, -apple-system, "Segoe UI", sans-serif', {}, "font-body", "Inter, sans-serif", None),
    ({"font_statement": "Georgia"}, "font-family", '"Source Serif 4", Georgia, "Times New Roman", serif', {}, "font-statement", "Georgia, serif", None),
    ({"font_mono": "Fira Code"}, "font-family", '"JetBrains Mono", ui-monospace, Menlo, Consolas, monospace', {}, "font-mono", "Fira Code, monospace", None),
    ({"font_body": "Inter"}, "font-family", '"Times New Roman"', {}, None, None, None),
    ({"font_body": "Inter"}, "font-family", "Arial", {}, None, None, None),
    # sizes
    ({"size_body": "18px"}, "font-size", "14px", {}, "size-body", "18px", None),
    ({"size_small": "15px"}, "font-size", "13px", {}, "size-small", "15px", None),
    ({"size_title": "40px"}, "font-size", "30px", {"h1": True}, "size-title", "40px", None),
    ({"size_title": "40px"}, "font-size", "30px", {"h1": False}, None, None, "not a page title"),
    ({"size_body": "18px"}, "font-size", "12px", {}, None, None, None),
    ({"size_body": "18px"}, "font-size", "13.3333px", {}, None, None, None),
    # corners: the element decides first
    (RADIUS_THEME, "border-top-left-radius", "8px", {"control": True}, "radius-control", "1px", None),
    (RADIUS_THEME, "border-top-left-radius", "6px", {"control": True}, "radius-control", "1px", None),                               # a 6px button is still a button
    (RADIUS_THEME, "border-top-left-radius", "4px", {"control": True}, "radius-control", "1px", None),
    (RADIUS_THEME, "border-top-left-radius", "12px", {"control": True}, "radius-panel", "2px", None),                               # a card that is a button
    (RADIUS_THEME, "border-bottom-right-radius", "12px", {}, "radius-panel", "2px", None),
    (RADIUS_THEME, "border-top-right-radius", "14px", {}, "radius-panel", "2px", None),
    (RADIUS_THEME, "border-bottom-left-radius", "8px", {}, "radius-panel", "2px", None),                                            # 8px on a div is a card, not a button
    (RADIUS_THEME, "border-top-left-radius", "6px", {}, "radius-chip", "3px", None),
    (RADIUS_THEME, "border-top-left-radius", "4px", {}, "radius-chip", "3px", None),
    (RADIUS_THEME, "border-top-left-radius", "999px", {}, None, None, None),                                                        # a pill is a shape
    (RADIUS_THEME, "border-top-left-radius", "999px", {"control": True}, None, None, None),
    (RADIUS_THEME, "border-top-left-radius", "50%", {}, None, None, None),
    (RADIUS_THEME, "border-top-left-radius", "2px", {}, None, None, None),                                                          # the map's squares
    (RADIUS_THEME, "border-top-left-radius", "0px", {"control": True}, None, None, None),
    (RADIUS_THEME, "border-top-left-radius", "8px 4px", {}, None, None, None),
    # control height: ours and the three sizes derived from it keep their distance
    ({"control_height": "50px"}, "min-height", "44px", {"control": True}, "control-height", "54px", None),
    ({"control_height": "50px"}, "min-height", "40px", {"control": True}, "control-height", "50px", None),
    ({"control_height": "50px"}, "min-height", "36px", {"control": True}, "control-height", "46px", None),
    ({"control_height": "50px"}, "min-height", "32px", {"control": True}, "control-height", "42px", None),
    ({"control_height": "50px"}, "min-height", "40px", {"control": False}, None, None, None),
    ({"control_height": "50px"}, "min-height", "52px", {"control": True}, None, None, None),
    ({"control_height": "50px"}, "min-height", "auto", {"control": True}, None, None, None),
    ({"control_height": "0.5rem"}, "min-height", "40px", {"control": True}, "control-height", "8px", None),
    # anything else is nobody's
    ({"accent": "#D81B60"}, "margin-top", "14px", {}, None, None, None),
    ({"accent": "#D81B60"}, "line-height", "20px", {}, None, None, None),
]


@pytest.mark.parametrize("changes, prop, value, fx, role, write, why", CASES, ids=["%d-%s-%s" % (i, c[1], c[2][:24]) for i, c in enumerate(CASES)])
def test_which_role_owns_a_computed_value_and_what_it_is_written_as(changes, prop, value, fx, role, write, why):
    d = FT.decide(prop, value, facts(**fx), tables(**changes))
    assert (d.role, d.value) == (role, write)
    if why:
        assert why in d.why
    else:
        assert d.why is None


def test_a_shadow_is_found_by_the_whole_list_as_the_browser_writes_it():
    t = tables(shadow_card="0 2px 4px rgba(0,0,0,.5)")
    t["shadow_computed"] = "rgba(21, 32, 43, 0.06) 0px 1px 2px 0px, rgba(21, 32, 43, 0.08) 0px 6px 18px 0px"
    assert FT.decide("box-shadow", "rgba(21, 32, 43, 0.06) 0px 1px 2px 0px,   rgba(21, 32, 43, 0.08) 0px 6px 18px 0px", facts(), t) == ("shadow-card", "0 2px 4px rgba(0,0,0,.5)", None)
    assert FT.decide("box-shadow", "rgb(179, 90, 0) 0px -2px 0px 0px inset", facts(), t).role is None
    assert FT.decide("box-shadow", "none", facts(), t).role is None


def test_the_page_and_the_surface_are_told_apart_by_the_element_when_a_design_gives_them_one_colour():
    ours = {**OURS, "page": OURS["surface"]}
    t = FT.build_tables(ours, {**ours, "page": "#EEDDCC", "surface": "#112233"})
    assert FT.decide("background-color", "rgb(255, 255, 255)", facts(root=True), t).role == "page"
    assert FT.decide("background-color", "rgb(255, 255, 255)", facts(root=False), t).role == "surface"


def test_every_role_is_owned_by_some_property_so_none_of_the_twenty_one_can_be_silently_skipped():
    t = tables()
    t["shadow_computed"] = " ".join(OURS["shadow-card"].split()).lower()
    owned = set()
    for r in R.ROLES["roles"]:
        kind, v = r["kind"], OURS[r["id"]]
        for fx in ({}, {"on_accent": True}, {"control": True}, {"h1": True}, {"root": True}):
            probes = []
            if kind == "colour":
                probes = [(p, v) for p in FT.COLOUR_ROLES]
            elif kind == "font":
                probes = [("font-family", v)]
            elif kind == "shadow":
                probes = [("box-shadow", OURS["shadow-card"])]
            elif r["id"].startswith("size"):
                probes = [("font-size", v)]
            elif r["id"].startswith("radius"):
                probes = [("border-top-left-radius", v)]
            else:
                probes = [("min-height", v)]
            for prop, val in probes:
                if FT.decide(prop, val, facts(**fx), t).role == r["id"]:
                    owned.add(r["id"])
    assert owned == set(R.ROLE_IDS), "no property owns: %s" % sorted(set(R.ROLE_IDS) - owned)


# ============================================================================================================ the report
def test_the_report_groups_by_property_and_value_and_leaves_out_what_is_no_choice():
    cases = [
        {"prop": "border-top-color", "value": "rgb(27, 107, 58)", "n_own": 3, "example": "span.a"},
        {"prop": "border-left-color", "value": "rgb(27, 107, 58)", "n_own": 2, "example": "span.b"},
        {"prop": "border-top-color", "value": "#1B6B3A", "n_own": 1, "example": "div.c"},            # the same colour written another way
        {"prop": "background-color", "value": "rgba(0, 0, 0, 0)", "n_own": 900, "example": "div"},     # transparent
        {"prop": "border-top-left-radius", "value": "0px", "n_own": 900, "example": "div"},
        {"prop": "border-top-left-radius", "value": "999px", "n_own": 4, "example": "span.pill"},
        {"prop": "border-top-right-radius", "value": "999px", "n_own": 4, "example": "span.pill"},
        {"prop": "box-shadow", "value": "none", "n_own": 900, "example": "div"},
        {"prop": "fill", "value": "none", "n_own": 900, "example": "path"},
        {"prop": "color", "value": "rgb(255, 255, 255)", "n_own": 7, "example": "b.chip", "why": "text on a background that is not our main action colour"},
        {"prop": "color", "value": "rgb(20, 80, 43)", "n_own": 0, "example": "span"},                  # nobody has it of their own
        {"prop": "font-size", "value": "12px", "n_own": 12, "example": 'span "Project"'},
    ]
    out = FT.group_unmapped(cases)
    by = {(g["property"], g["value"]): g for g in out}
    assert by[("border-color", "rgb(27, 107, 58)")]["count"] == 4 and by[("border-color", "rgb(27, 107, 58)")]["example"] == "span.a", "3 + 1 elements on the top, 2 on the left: 4 elements"
    assert by[("border-radius", "999px")]["count"] == 4, "four elements with a pill on two corners are four elements, not eight"
    assert by[("font-size", "12px")]["example"] == 'span "Project"' and "why" not in by[("font-size", "12px")]
    assert by[("color", "rgb(255, 255, 255)")]["why"].startswith("text on a background")
    assert len(out) == 4 and [g["count"] for g in out] == sorted((g["count"] for g in out), reverse=True)
    assert not any(g["value"] in ("rgba(0, 0, 0, 0)", "0px", "none") for g in out)
    assert not any(g["value"] == "rgb(20, 80, 43)" for g in out), "a value nobody has of their own is not listed"


def test_the_report_of_nothing_is_an_empty_list():
    assert FT.group_unmapped([]) == []


@pytest.mark.parametrize("value, pale", [
    ("rgb(244, 246, 248)", True), ("#E4E9ED", True), ("rgb(215, 215, 215)", True), ("white", True),
    ("rgb(214, 220, 225)", False),            # one channel under the line
    ("rgb(225, 242, 231)", False),            # a pale green is a status colour, not a grey
    ("rgb(232, 240, 253)", False),            # a pale blue is the info fill, not a grey
    ("rgba(255, 255, 255, 0.6)", False),      # not solid
    ("banana", False), ("", False),
])
def test_a_pale_grey_is_a_solid_light_colour_with_almost_no_hue(value, pale):
    assert FT.light_neutral(value) is pale


def _grey(count, value="rgb(244, 246, 248)", prop="background-color"):
    return {"property": prop, "value": value, "count": count, "example": "div"}


def test_a_dark_page_or_surface_gets_a_note_on_the_pale_greys_that_stay_pale():
    unmapped = [_grey(4), _grey(3, "rgb(228, 233, 237)"), _grey(9, "rgb(225, 242, 231)"), _grey(5, "rgb(244, 246, 248)", "color"), _grey(2, "rgb(0, 0, 0)")]
    note = FT.dark_theme_note(unmapped, {"page": "#10131A", "surface": "#1A1F2B"})
    assert note is not None and note.startswith("7 element(s) are drawn on pale greys that no role names"), note
    assert "dark page and surface" in note and "hard to read" in note, "names which of the two is dark"
    assert "dark page" in FT.dark_theme_note(unmapped, {"page": "#10131A", "surface": "#FFFFFF"}) and "surface" not in FT.dark_theme_note(unmapped, {"page": "#10131A", "surface": "#FFFFFF"})
    assert "dark surface" in FT.dark_theme_note(unmapped, {"page": "#FFFFFF", "surface": "#1A1F2B"})


def test_no_note_on_a_light_theme_or_when_no_pale_grey_is_left():
    unmapped = [_grey(4), _grey(3, "rgb(228, 233, 237)")]
    assert FT.dark_theme_note(unmapped, {"page": "#FFFFFF", "surface": "#F3F5F8"}) is None, "light theme: pale greys are fine"
    assert FT.dark_theme_note(unmapped, {"page": "#808080", "surface": "#808080"}) is None, "a mid grey is not dark"
    assert FT.dark_theme_note([_grey(9, "rgb(225, 242, 231)"), _grey(2, "rgb(0, 0, 0)")], {"page": "#10131A", "surface": "#1A1F2B"}) is None, "dark, but nothing pale is left"
    assert FT.dark_theme_note([], {"page": "#10131A", "surface": "#1A1F2B"}) is None


# ============================================================================================================ the command line
def run(*argv, cwd=REPO):
    return subprocess.run([sys.executable, str(SCRIPT), *argv], cwd=cwd, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})


def theme_file(tmp_path, data, name="theme.json"):
    p = tmp_path / name
    p.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(p)


@pytest.fixture
def session(tmp_path, capsys):
    s = str(tmp_path / "s")
    assert adopt.main(["init", s, "--page", str(SAMPLE_PAGE), "--index-from", str(SAMPLE_INDEX)]) == 0
    capsys.readouterr()
    return s


def test_a_session_that_does_not_exist_is_refused_with_a_message(tmp_path):
    r = run(str(tmp_path / "nope"))
    assert r.returncode == 2 and "no session here" in r.stderr and not (tmp_path / "nope").exists()


def test_a_folder_that_is_not_a_started_session_is_refused(tmp_path):
    (tmp_path / "s").mkdir()
    r = run(str(tmp_path / "s"))
    assert r.returncode == 2 and "no session here" in r.stderr
    (tmp_path / "s" / "session.json").write_text(json.dumps({"format": "reqin-adopt/1", "answers": {}, "overrides": {}}))
    r = run(str(tmp_path / "s"))
    assert r.returncode == 2 and "mine/index.json" in r.stderr


@pytest.mark.parametrize("data, words", [
    ('{"accent": "banana"}', "accent: 'banana' is not a colour"),
    ('{"colour": "#fff"}', "'colour' is not a role"),
    ('{"radius-control": "wide"}', "radius-control: 'wide' is not a length"),
    ('{"font-body": 12345}', "font-body: the value must be text"),
    ('{"font-body": "Inter; x"}', "not a plain value"),
    ('{"shadow-card": "banana"}', "not a shadow"),
    ('{"accent": null}', "accent: the value must be text"),
    ('["accent"]', "must hold one JSON object"),
    ('"accent"', "must hold one JSON object"),
    ("{not json", "is not JSON"),
    ("", "is not JSON"),
])
def test_a_theme_file_that_is_wrong_is_refused_with_a_clear_message_and_nothing_is_drawn(tmp_path, data, words):
    out = tmp_path / "out"
    r = run("--theme", theme_file(tmp_path, data), str(out))
    assert r.returncode == 2, r.stderr
    assert words in r.stderr and r.stderr.startswith("not drawn:") and "Traceback" not in r.stderr
    assert not out.exists() and r.stdout == ""


def test_a_theme_file_that_is_missing_is_refused(tmp_path):
    r = run("--theme", str(tmp_path / "missing.json"), str(tmp_path / "out"))
    assert r.returncode == 2 and "no theme file here" in r.stderr


def test_a_screen_that_is_not_ours_is_refused_and_the_message_lists_the_screens(tmp_path):
    r = run("--theme", theme_file(tmp_path, {"accent": "#D81B60"}), str(tmp_path / "out"), "--screens", "review,nope")
    assert r.returncode == 2 and "'nope'" in r.stderr and "explorer" in r.stderr and not (tmp_path / "out").exists()


def test_a_dry_run_of_a_theme_file_says_what_differs_and_what_would_be_drawn_without_a_browser(tmp_path):
    out = tmp_path / "out"
    r = run("--theme", theme_file(tmp_path, {"accent": "#D81B60", "radius-control": "0", "ink": "#1B2733"}), str(out), "--screens", "review,open", "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "2 of 21 roles differ from ours: accent, radius-control" in r.stdout and "review, open" in r.stdout and str(out) in r.stdout
    assert not out.exists(), "a dry run writes nothing"


def test_a_dry_run_of_an_empty_theme_says_the_pictures_would_be_ours(tmp_path):
    r = run("--theme", theme_file(tmp_path, {}), str(tmp_path / "out"), "--dry-run")
    assert r.returncode == 0 and "0 of 21 roles differ" in r.stdout and "would be ours" in r.stdout
    assert "would draw 14 screen(s)" in r.stdout


def test_a_dry_run_of_a_session_reads_the_theme_the_way_adopt_reads_it(session):
    theirs, ours = FT.load_session_theme(session)
    m = adopt.model_of(session)[1]
    assert theirs == m.theme_values() and ours == {r: m.ours_value(r) for r in R.ROLE_IDS}
    r = run(session, "--dry-run", "--screens", "policy")
    assert r.returncode == 0 and "would draw 1 screen(s) into" in r.stdout and str(Path(session) / "pictures" / "frames") in r.stdout
    assert "differ from ours" in r.stdout and "accent" in r.stdout            # the sample page has its own green
    assert adopt.main(["answer", session, "stance", "ours", "--no-pictures"]) == 0
    theirs, ours = FT.load_session_theme(session)
    assert theirs == ours, "taking our whole theme means the pictures are ours"
    assert "0 of 21 roles differ" in run(session, "--dry-run").stdout


def test_a_dry_run_never_opens_a_browser(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(FT, "draw_themed", lambda *a, **k: pytest.fail("a dry run must not draw"))
    assert FT.main(["--theme", theme_file(tmp_path, {"accent": "#D81B60"}), str(tmp_path / "out"), "--dry-run"]) == 0
    assert "1 of 21 roles differ from ours: accent" in capsys.readouterr().out


def test_the_module_imports_with_only_the_standard_library():
    code = ("import sys\nfor m in ('playwright', 'PIL', 'numpy'):\n    sys.modules[m] = None\n"
            "sys.path.insert(0, %r)\nimport frames_theme\nassert 'playwright' not in [k for k, v in sys.modules.items() if v is not None]\nprint('imported')\n" % str(KIT / "scripts"))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert r.returncode == 0 and "imported" in r.stdout, r.stderr


# ============================================================================================================ in a browser: small pages
@lru_cache(maxsize=1)
def chromium_launches() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


@pytest.fixture
def blank():
    """A page with nothing on it but what a test sets (no prototype, no server): a Chromium, one page, and a helper that re-themes it and reads computed values back."""
    pytest.importorskip("playwright")
    if not chromium_launches():
        pytest.skip("Playwright's Chromium is not installed")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 800, "height": 600})

        class P:
            page = pg

            def set(self, html):
                pg.set_content("<!doctype html><html><body style='margin:0'>%s</body></html>" % html)

            def remap(self, **theirs):
                return FT.remap_page(pg, OURS, {k.replace("_", "-"): v for k, v in theirs.items()})

            def css(self, selector, prop):
                return pg.evaluate("([s, p]) => getComputedStyle(document.querySelector(s)).getPropertyValue(p)", [selector, prop])

            def html(self):
                return pg.evaluate("document.documentElement.outerHTML")

        yield P()
        b.close()


def listed(report, prop, value):
    return [u for u in report["unmapped"] if u["property"] == prop and u["value"] == value]


def test_white_text_takes_the_accent_text_only_on_our_accent_and_the_green_chip_keeps_its_white(blank):
    blank.set('<div id=a style="background:#1A4DB5;color:#fff">a</div><div id=b style="background:#1B6B3A;color:#fff">b</div><div id=c style="background:#fff;color:#1B2733">c</div>')
    rep = blank.remap(accent_text="#101010")
    assert blank.css("#a", "color") == "rgb(16, 16, 16)"
    assert blank.css("#b", "color") == "rgb(255, 255, 255)" and blank.css("#c", "background-color") == "rgb(255, 255, 255)"
    assert rep["changed"] == {"accent-text": 1}
    assert listed(rep, "color", "rgb(255, 255, 255)")[0]["why"].startswith("text on a background that is not our main action colour")


def test_a_white_background_is_the_surface_and_not_the_text_on_the_accent(blank):
    blank.set('<div id=a style="background:#fff">a</div><div id=b style="background:#1A4DB5;color:#fff">b</div>')
    rep = blank.remap(surface="#202020", accent_text="#101010")
    assert blank.css("#a", "background-color") == "rgb(32, 32, 32)" and blank.css("#b", "color") == "rgb(16, 16, 16)" and blank.css("#b", "background-color") == "rgb(26, 77, 181)"
    assert rep["changed"] == {"surface": 1, "accent-text": 1}


def test_a_see_through_white_keeps_its_opacity_and_a_faint_one_is_left_alone(blank):
    blank.set('<div id=a style="background:rgba(255,255,255,.94)">a</div><div id=b style="background:rgba(255,255,255,.1)">b</div>')
    blank.remap(surface="#202020")
    assert blank.css("#a", "background-color") == "rgba(32, 32, 32, 0.94)" and blank.css("#b", "background-color") == "rgba(255, 255, 255, 0.1)"


def test_a_value_set_with_important_in_a_rule_is_still_replaced(blank):
    blank.set('<style>.x{background:#F3F5F8 !important;color:#1B2733 !important;border:1px solid #D8DFE6 !important}</style><div class=x id=a>t</div>')
    blank.remap(page="#FFE0E0", ink="#220000", border="#00FF00")
    assert blank.css("#a", "background-color") == "rgb(255, 224, 224)" and blank.css("#a", "color") == "rgb(34, 0, 0)" and blank.css("#a", "border-top-color") == "rgb(0, 255, 0)"


def test_a_theme_equal_to_ours_leaves_the_page_exactly_as_it_was(blank):
    blank.set('<div style="background:#1A4DB5;color:#fff;border:1px solid #D8DFE6;border-radius:8px;font:14px \'Public Sans\'">a</div><button style="min-height:44px">b</button>')
    before = blank.html()
    rep = blank.remap(**{k.replace("-", "_"): v for k, v in OURS.items()})
    assert blank.html() == before and rep["changed"] == {} and rep["tokens"] == {} and rep["followed"] == {} and rep["font"] == {}
    assert blank.remap()["changed"] == {} and blank.html() == before


def test_something_made_of_a_token_follows_it_when_the_token_is_on_the_root_on_an_element_or_in_a_rule(blank):
    tint = "color-mix(in srgb, var(--accent) 10%, #fff)"
    for name, html in [("root", '<style>:root{--accent:#1A4DB5}</style><div id=t style="background:%s">t</div>' % tint),
                       ("element", '<div style="--accent:#1A4DB5"><div id=t style="background:%s">t</div></div>' % tint),
                       ("rule", '<style>.scope{--accent:#1A4DB5}</style><div class=scope><div id=t style="background:%s">t</div></div>' % tint)]:
        blank.set(html)
        before = blank.css("#t", "background-color")
        rep = blank.remap(accent="#B5179E")
        want = blank.page.evaluate("() => { const e = document.createElement('div'); e.style.background = 'color-mix(in srgb, #B5179E 10%, #fff)'; document.body.appendChild(e); return getComputedStyle(e).backgroundColor; }")
        assert blank.css("#t", "background-color") == want != before, name
        assert rep["followed"].get("background-color") == 1 and not listed(rep, "background-color", before), name


def test_a_role_is_never_applied_to_a_value_that_only_became_the_persons(blank):
    """Their accent happens to be our ink: the accent text must not then be turned into their ink as well."""
    blank.set('<div id=a style="color:#1A4DB5">a</div><div id=b style="color:#1B2733">b</div>')
    blank.remap(accent="#1B2733", ink="#FF0000")
    assert blank.css("#a", "color") == "rgb(27, 39, 51)" and blank.css("#b", "color") == "rgb(255, 0, 0)"


def test_corners_follow_the_element_first_and_then_the_value(blank):
    blank.set("".join('<%s id=%s style="border-radius:%s;display:block;width:40px;height:40px">x</%s>' % (t, i, r, t) for t, i, r in [
        ("button", "b8", "8px"), ("button", "b6", "6px"), ("button", "bp", "12px"), ("input", "in8", "8px"), ("div", "d12", "12px"), ("div", "d14", "14px"), ("div", "d8", "8px"),
        ("span", "s6", "6px"), ("span", "s4", "4px"), ("span", "pill", "999px"), ("div", "circle", "50%"), ("div", "tiny", "2px"), ("div", "none", "0px")]))
    rep = blank.remap(radius_control="1px", radius_panel="2px", radius_chip="3px")
    got = {i: blank.css("#" + i, "border-top-left-radius") for i in ("b8", "b6", "bp", "in8", "d12", "d14", "d8", "s6", "s4", "pill", "circle", "tiny", "none")}
    assert got == {"b8": "1px", "b6": "1px", "bp": "2px", "in8": "1px", "d12": "2px", "d14": "2px", "d8": "2px", "s6": "3px", "s4": "3px", "pill": "999px", "circle": "50%", "tiny": "2px", "none": "0px"}
    assert rep["changed"] == {"radius-control": 3, "radius-panel": 4, "radius-chip": 2}
    assert {u["value"] for u in rep["unmapped"] if u["property"] == "border-radius"} == {"999px", "50%", "2px"}, "0px is no choice and is not listed"


def test_the_four_corners_are_each_read_so_a_card_with_square_bottom_corners_keeps_them(blank):
    blank.set('<div id=a style="border-radius:12px 12px 0 0;width:40px;height:40px"></div>')
    blank.remap(radius_panel="2px")
    assert [blank.css("#a", "border-%s-radius" % c) for c in ("top-left", "top-right", "bottom-right", "bottom-left")] == ["2px", "2px", "0px", "0px"]


def test_control_height_moves_ours_and_the_three_sizes_derived_from_it_and_only_on_controls(blank):
    blank.set("".join('<button id=b%d style="min-height:%dpx">x</button>' % (n, n) for n in (44, 40, 36, 32, 52)) + '<div id=d style="min-height:40px">x</div><input id=i style="min-height:40px">')
    rep = blank.remap(control_height="50px")
    assert [blank.css("#b%d" % n, "min-height") for n in (44, 40, 36, 32, 52)] == ["54px", "50px", "46px", "42px", "52px"]
    assert blank.css("#d", "min-height") == "40px" and blank.css("#i", "min-height") == "50px" and rep["changed"] == {"control-height": 5}
    assert [u["value"] for u in rep["unmapped"] if u["property"] == "min-height"] == ["52px"]


def test_the_font_of_a_role_is_found_by_its_first_family_and_an_unrelated_font_is_left_alone(blank):
    have = [f for f, ok in FT.installed_fonts(blank.page, ["Inter", "DejaVu Sans", "Liberation Sans", "Noto Sans"]).items() if ok]
    if not have:
        pytest.skip("none of the fonts the test would ask for is installed here")
    f = have[0]
    blank.set('''<span id=a style="font-family:'Public Sans', system-ui, sans-serif">a</span><span id=b style="font-family:'Source Serif 4', Georgia, serif">b</span>
                <span id=c style="font-family:'JetBrains Mono', monospace">c</span><span id=d style="font-family:Arial">d</span>''')
    rep = blank.remap(font_body=f, font_statement=f + ", serif", font_mono=f)
    assert blank.css("#a", "font-family").strip('"').startswith(f) and blank.css("#a", "font-family").endswith("sans-serif")
    assert blank.css("#b", "font-family").strip('"').startswith(f) and blank.css("#c", "font-family").endswith("monospace")
    assert blank.css("#d", "font-family") == "Arial" and rep["changed"] == {"font-body": 1, "font-statement": 1, "font-mono": 1}
    assert rep["font"]["font-body"] == {"asked": f, "drawn_with": f, "stand_in": False}
    assert [u["value"] for u in rep["unmapped"] if u["property"] == "font-family"] == ["Arial"]


def test_a_font_this_machine_does_not_have_is_drawn_in_a_stand_in_and_the_report_says_so(blank):
    blank.set('<span id=a style="font-family:\'Public Sans\'">a</span>')
    rep = blank.remap(font_body="Zyzzyva Sans")
    assert rep["font"]["font-body"] == {"asked": "Zyzzyva Sans", "drawn_with": "sans-serif", "stand_in": True}
    assert blank.css("#a", "font-family").replace('"', "") == "Zyzzyva Sans, sans-serif"
    assert any("no Zyzzyva Sans" in n and "sans-serif" in n for n in rep["notes"])
    have = [f for f, ok in FT.installed_fonts(blank.page, ["Inter", "DejaVu Sans", "Liberation Sans"]).items() if ok]
    if have:
        blank.set('<span id=a style="font-family:\'Public Sans\'">a</span>')
        rep = blank.remap(font_body="Zyzzyva Sans, %s, sans-serif" % have[0])
        assert rep["font"]["font-body"] == {"asked": "Zyzzyva Sans, %s, sans-serif" % have[0], "drawn_with": have[0], "stand_in": True}


def test_text_sizes_are_found_by_value_and_the_title_size_only_on_a_page_title(blank):
    blank.set('<span id=a style="font-size:14px">a</span><span id=b style="font-size:13px">b</span><span id=c style="font-size:12px">c</span>'
              '<h1 id=h style="font-size:30px;margin:0">h</h1><div id=f style="font-size:30px">f</div>')
    rep = blank.remap(size_body="18px", size_small="15px", size_title="40px")
    assert [blank.css("#" + i, "font-size") for i in ("a", "b", "c", "h", "f")] == ["18px", "15px", "12px", "40px", "30px"]
    assert rep["changed"] == {"size-body": 1, "size-small": 1, "size-title": 1}
    assert listed(rep, "font-size", "30px")[0]["why"].endswith("something that is not a page title") and listed(rep, "font-size", "12px")


def test_one_digit_off_is_a_different_colour_and_stays(blank):
    blank.set('<div id=a style="border:1px solid #7A8793">a</div><div id=b style="border:1px solid rgb(123,135,146)">b</div>')
    rep = blank.remap(border_control="#FF00FF")
    assert blank.css("#a", "border-top-color") == "rgb(255, 0, 255)" and blank.css("#b", "border-top-color") == "rgb(123, 135, 146)"
    assert listed(rep, "border-color", "rgb(123, 135, 146)")[0]["count"] == 1 and rep["changed"] == {"border-control": 1}


def test_a_border_is_only_read_where_one_is_drawn_and_an_outline_only_where_there_is_one(blank):
    blank.set('<div id=a style="border:0 solid #D8DFE6">a</div><div id=b style="border:1px solid #D8DFE6">b</div><div id=c style="outline:2px solid #1A4DB5">c</div>'
              '<div id=d style="border:1px none #D8DFE6">d</div>')
    rep = blank.remap(border="#00FF00", accent="#FF0000")
    assert blank.css("#b", "border-top-color") == "rgb(0, 255, 0)" and blank.css("#c", "outline-color") == "rgb(255, 0, 0)"
    assert blank.page.evaluate("[...document.querySelectorAll('#a, #d')].map(e => e.getAttribute('style'))") == ["border:0 solid #D8DFE6", "border:1px none #D8DFE6"]
    assert rep["changed"] == {"border": 1, "accent": 1}


def test_each_side_of_a_border_is_taken_alone(blank):
    blank.set('<div id=a style="border-style:solid;border-width:1px;border-color:#D8DFE6 #7A8793 #D8DFE6 #1A4DB5">a</div>')
    blank.remap(border="#00FF00", border_control="#FF00FF", accent="#FF0000")
    assert [blank.css("#a", "border-%s-color" % s) for s in ("top", "right", "bottom", "left")] == ["rgb(0, 255, 0)", "rgb(255, 0, 255)", "rgb(0, 255, 0)", "rgb(255, 0, 0)"]


def test_a_card_shadow_is_found_whole_and_a_value_the_browser_refuses_is_reported(blank):
    ours = "0 1px 2px rgba(21,32,43,.06),0 6px 18px rgba(21,32,43,.08)"
    blank.set('<div id=a style="box-shadow:%s">a</div><div id=b style="box-shadow:0 1px 2px rgba(21,32,43,.06)">b</div>' % ours)
    rep = blank.remap(shadow_card="0 2px 4px rgba(0,0,0,.5)")
    assert blank.css("#a", "box-shadow") == "rgba(0, 0, 0, 0.5) 0px 2px 4px 0px" and blank.css("#b", "box-shadow") == "rgba(21, 32, 43, 0.06) 0px 1px 2px 0px" and rep["changed"] == {"shadow-card": 1}
    blank.set('<div id=a style="box-shadow:%s">a</div>' % ours)
    assert blank.remap(shadow_card="none")["changed"] == {"shadow-card": 1} and blank.css("#a", "box-shadow") == "none"
    blank.set('<div id=a style="box-shadow:%s">a</div>' % ours)
    rep = blank.remap(shadow_card="0 1px banana")
    assert rep["rejected"] == [{"property": "box-shadow", "value": "0 1px banana"}] and rep["changed"] == {"shadow-card": 0}
    assert any("refused" in n for n in rep["notes"]) and blank.css("#a", "box-shadow") != "none"


def test_a_changed_role_that_nothing_on_the_screen_uses_is_said_to_show_no_change(blank):
    blank.set('<div style="color:#1B2733">a</div>')
    rep = blank.remap(hover="#00FFFF")
    assert rep["changed"] == {"hover": 0} and any("hover background" in n and "no change" in n for n in rep["notes"])


def test_drawings_take_the_accent_and_their_white_is_the_accent_text_only_on_the_accent(blank):
    blank.set('<div style="background:#1A4DB5"><svg width=20 height=20><circle id=a cx=10 cy=10 r=5 fill="#1A4DB5" stroke="#fff"/></svg></div>'
              '<svg width=20 height=20><circle id=b cx=10 cy=10 r=5 fill="none" stroke="#fff"/></svg><svg width=20 height=20><path id=c d="M0 0L5 5" stroke="#54626F" fill="none"/></svg>')
    blank.remap(accent="#FF0000", accent_text="#000000", surface="#00FF00", ink_muted="#0000FF")
    assert blank.css("#a", "fill") == "rgb(255, 0, 0)" and blank.css("#a", "stroke") == "rgb(0, 0, 0)"
    assert blank.css("#b", "stroke") == "rgb(0, 255, 0)" and blank.css("#c", "stroke") == "rgb(0, 0, 255)"


def test_the_report_names_what_means_something_and_counts_an_inherited_value_once(blank):
    blank.set('<div style="color:#14502B;background:#E1F2E7">green <span>a</span><span>b</span></div><div style="color:#1B2733">ink</div><p style="margin:0;background:#fff">white</p>')
    rep = blank.remap(ink="#FF0000", surface="#202020")
    g = listed(rep, "color", "rgb(20, 80, 43)")
    assert len(g) == 1 and g[0]["count"] == 1 and g[0]["example"].startswith('div "green')
    assert listed(rep, "background-color", "rgb(225, 242, 231)") and not listed(rep, "color", "rgb(27, 39, 51)") and not listed(rep, "background-color", "rgb(255, 255, 255)")
    assert set(rep) == {"changed", "unmapped", "followed", "font", "tokens", "notes", "rejected"}
    assert all(set(u) >= {"property", "value", "count", "example"} for u in rep["unmapped"])


def test_the_named_colours_are_the_ones_the_browser_means(blank):
    blank.set("<div id=t></div>")
    want = blank.page.evaluate("(names) => names.map(n => { const e = document.getElementById('t'); e.style.color = ''; e.style.color = n; return getComputedStyle(e).color; })", sorted(FT.NAMED))
    assert [FT.norm_colour(n) for n in sorted(FT.NAMED)] == want
    sample = ["#1a4db5", "#fff8", "rgb(10%, 20%, 30%)", "rgba(255,255,255,.94)", "rgb(26 77 181 / 50%)", "hsl(0, 100%, 50%)", "hsl(120, 100%, 25%)"]
    got = blank.page.evaluate("(vals) => vals.map(n => { const e = document.getElementById('t'); e.style.color = ''; e.style.color = n; return getComputedStyle(e).color; })", sample)
    assert [FT.norm_colour(s) for s in sample] == got


# ============================================================================================================ in a browser: the real prototype
@pytest.fixture
def proto():
    pytest.importorskip("playwright")
    pytest.importorskip("PIL")
    if not chromium_launches():
        pytest.skip("Playwright's Chromium is not installed")
    if not NODE_MODULES.is_dir():
        pytest.skip("prototype/vendor/node_modules is not installed (the prototype page needs React from there)")


def im(path):
    from PIL import Image
    return Image.open(path).convert("RGB")


def near(image, colour, tol=0):
    """A mask (255 where the pixel is within tol of the colour, summed over the three channels)."""
    from PIL import Image, ImageChops
    r, g, b = ImageChops.difference(image, Image.new("RGB", image.size, colour)).split()
    return ImageChops.add(ImageChops.add(r, g), b).point(lambda v: 255 if v <= tol else 0)


def count(mask):
    return mask.histogram()[255]


def overlap(a, b):
    from PIL import ImageChops
    return count(ImageChops.multiply(a, b))


def same_pixels(a, b):
    return a.size == b.size and a.tobytes() == b.tobytes()


def plain_draw(screens, out):
    """The pictures make_frames would draw (no re-theme), for a machine that cannot reproduce the committed ones."""
    sys.path.insert(0, str(REPO / "prototype"))
    from h import session
    out.mkdir(parents=True, exist_ok=True)
    with session(MF.WIDTH, 900) as (pg, _):
        for i, sid in enumerate(screens):
            if i:
                MF.fresh(pg)
            MF.reach(pg, sid)
            MF.tall(pg)
            pg.screenshot(path=str(out / (sid + ".png")), full_page=True)
            MF._shrink(out / (sid + ".png"))


def draw(tmp_path, theirs, screens, name="out"):
    res = FT.draw_themed(theirs, tmp_path / name, screens)
    assert res["ok"], res["problems"]
    return res, tmp_path / name


def test_drawing_in_our_own_theme_changes_nothing_in_any_of_the_fourteen_pictures(proto, tmp_path):
    """The key test of the remap and of the second measuring pass: with nothing to change, the pictures have the pixels of the committed ones and the frames the committed boxes."""
    res, out = draw(tmp_path, dict(OURS), None)
    committed = read_json(MF.INDEX)
    spec = MF.load_spec()
    assert list(res["index"]["screens"]) == list(spec["screens"]) and len(spec["screens"]) == 14
    assert res["index"]["prototype_page"] == MF.page_hash() == committed["prototype_page"] and res["index"]["theme"] == digest(FT.complete_theme(OURS, OURS))
    differs = []
    for sid, s in res["index"]["screens"].items():
        old, new = committed["screens"][sid], s
        assert (new["width"], new["height"]) == (old["width"], old["height"]), sid
        assert new["frames"] == old["frames"], "%s: the boxes are not the committed ones" % sid
        rep = new["report"]
        assert rep["changed"] == {} and rep["tokens"] == {} and rep["followed"] == {} and rep["font"] == {} and rep["notes"] == [], sid
        if not same_pixels(im(out / s["image"]), im(MF.OUT / old["image"])):
            differs.append(sid)
    if differs:                                          # this machine may not draw what was committed, with or without the re-theme: then the plain drawing is the thing to equal
        plain_draw(differs, tmp_path / "plain")
        for sid in differs:
            assert same_pixels(im(out / (sid + ".png")), im(tmp_path / "plain" / (sid + ".png"))), "%s: the re-theme changed a picture that should not change" % sid
        warnings.warn("these pictures are not pixel-equal to docs/images/frames here even without the re-theme (another Chromium or other fonts?): %s" % differs)
    assert (out / INDEX_NAME).is_file() and json.loads((out / INDEX_NAME).read_text())["format"] == "reqin-frames-theme/1"


@pytest.fixture
def accent_run(proto, tmp_path):
    return draw(tmp_path, {"accent": "#D81B60"}, ["review"], "accent")


def test_changing_only_the_accent_recolours_the_main_buttons_and_leaves_the_page_and_the_surfaces(accent_run):
    res, out = accent_run
    rep = res["index"]["screens"]["review"]["report"]
    new, old = im(out / "review.png"), im(MF.OUT / "review.png")
    assert new.size == old.size, "nothing was laid out again"
    assert list(k for k, v in rep["changed"].items() if v) == ["accent"] and rep["changed"]["accent"] > 0 and rep["font"] == {}
    was_accent = near(old, (26, 77, 181), 6)
    assert count(was_accent) > 500, "the review screen has main buttons and accent marks"
    assert overlap(was_accent, near(new, (216, 27, 96), 14)) / count(was_accent) > 0.95, "what was our accent is theirs"
    for colour, what in (((243, 245, 248), "the page"), ((255, 255, 255), "the surfaces")):
        was = near(old, colour, 2)
        assert count(was) > 10000
        assert overlap(was, near(new, colour, 14)) / count(was) > 0.995, "%s moved colour" % what
    assert rep["followed"].get("background-color", 0) > 0, "the tints made of the accent (the chosen row) follow it"


def test_square_control_corners_square_the_buttons_and_leave_the_cards_round_and_nothing_else_moves(proto, tmp_path):
    res, out = draw(tmp_path, {"radius-control": "0px"}, ["review"], "square")
    rep = res["index"]["screens"]["review"]["report"]
    assert [k for k, v in rep["changed"].items() if v] == ["radius-control"] and rep["followed"] == {}
    from PIL import ImageChops
    new, old = im(out / "review.png"), im(MF.OUT / "review.png")
    assert new.size == old.size
    moved = ImageChops.difference(new, old).convert("L").point(lambda v: 255 if v > 40 else 0)
    assert 0 < count(moved) < 0.005 * new.size[0] * new.size[1], "only the corners of the controls change colour"
    sys.path.insert(0, str(REPO / "prototype"))
    from h import session
    from PIL import Image
    import io

    def corner(pg, locator):
        b = locator.bounding_box()
        png = pg.screenshot(clip={"x": b["x"], "y": b["y"], "width": 4, "height": 4})
        return Image.open(io.BytesIO(png)).convert("RGB").getpixel((1, 1))

    with session(MF.WIDTH, 900) as (pg, _):
        MF.reach(pg, "review")
        MF.tall(pg)
        button, card = pg.get_by_role("button", name="Next cluster for me"), pg.locator("aside.rv-resolve")
        b_before, c_before = corner(pg, button), corner(pg, card)
        assert max(abs(a - b) for a, b in zip(b_before, (26, 77, 181))) > 40, "the main button starts with a round corner, so its corner pixel is not the button's colour"
        FT.remap_page(pg, OURS, {"radius-control": "0px"})
        assert max(abs(a - b) for a, b in zip(corner(pg, button), (26, 77, 181))) <= 4, "now the corner pixel is the button's colour: the corner is square"
        assert corner(pg, card) == c_before, "the card keeps its round corner"
        MF.fresh(pg)
        MF.reach(pg, "review")
        MF.tall(pg)
        FT.remap_page(pg, OURS, {"radius-panel": "0px"})
        assert corner(pg, card) != c_before and max(abs(a - b) for a, b in zip(corner(pg, button), b_before)) <= 4, "square cards leave the buttons round"


def test_a_bigger_body_text_makes_a_taller_page_and_the_boxes_are_the_ones_measured_after_it(proto, tmp_path):
    res, out = draw(tmp_path, {"size-body": "20px"}, ["policy", "open"], "big")
    committed = read_json(MF.INDEX)
    spec = MF.load_spec()
    for sid in ("policy", "open"):
        s, old = res["index"]["screens"][sid], committed["screens"][sid]
        assert s["height"] > old["height"] + 100, "%s: 20px body text makes the page taller" % sid
        assert im(out / s["image"]).size == (s["width"], s["height"])
        assert [f["id"] for f in s["frames"]] == [f["id"] for f in spec["screens"][sid]]
        for f in s["frames"]:
            b = f["box"]
            assert b["x"] >= 0 and b["y"] >= 0 and b["w"] > 0 and b["h"] > 0 and b["x"] + b["w"] <= s["width"] + 1 and b["y"] + b["h"] <= s["height"] + 1, (sid, f)
        assert [f["box"] for f in s["frames"]] != [f["box"] for f in old["frames"]], "%s: the boxes were not measured again after the re-theme" % sid
        grown = [f["box"]["h"] > o["box"]["h"] for f, o in zip(s["frames"], old["frames"])]
        assert sum(grown) >= len(grown) // 2, "%s: most frames hold text, which is taller now" % sid
        last, old_last = max(f["box"]["y"] + f["box"]["h"] for f in s["frames"]), max(f["box"]["y"] + f["box"]["h"] for f in old["frames"])
        assert last > old_last, "%s: the last frame ends lower" % sid
        assert s["report"]["changed"]["size-body"] > 50
    pol, pic = res["index"]["screens"]["policy"], im(out / "policy.png")
    assert max(abs(a - b) for a, b in zip(pic.getpixel((100, pol["height"] - 30)), (255, 255, 255))) <= 4, "the side bar (white, 100vh) still reaches the bottom of the taller page"
    assert max(abs(a - b) for a, b in zip(im(MF.OUT / "policy.png").getpixel((100, committed["screens"]["policy"]["height"] - 30)), (255, 255, 255))) <= 4


def test_the_report_on_the_real_prototype_names_the_meaning_colours_and_not_the_colours_of_the_roles(proto, tmp_path):
    res, out = draw(tmp_path, ALL_CHANGED, ["review", "explorer"], "all")
    index = json.loads((out / INDEX_NAME).read_text())
    assert index["theme"] == digest(FT.complete_theme(ALL_CHANGED, OURS)) and list(index["screens"]) == ["review", "explorer"]
    for sid, s in res["index"]["screens"].items():
        rep = s["report"]
        un = {(u["property"], u["value"]) for u in rep["unmapped"]}
        meaning_here = {"review": [("border-color", "rgb(27, 107, 58)"), ("background-color", "rgb(225, 242, 231)"), ("background-color", "rgb(255, 224, 173)"), ("background-color", "rgb(143, 203, 166)")],
                        "explorer": [("background-color", "rgb(27, 107, 58)"), ("background-color", "rgb(79, 143, 230)"), ("background-color", "rgb(28, 92, 171)"), ("border-color", "rgb(27, 107, 58)")]}[sid]
        for prop, value in meaning_here:      # the green of a pass chip and of an approved square, the amber of a number chip, the blue of an open square
            assert (prop, value) in un, "%s: %s %s is meaning and should be listed" % (sid, prop, value)
        roles_listed = {("color", "rgb(27, 39, 51)"), ("color", "rgb(84, 98, 111)"), ("color", "rgb(79, 91, 102)"), ("color", "rgb(26, 77, 181)"), ("background-color", "rgb(255, 255, 255)"),
                        ("background-color", "rgb(243, 245, 248)"), ("background-color", "rgb(26, 77, 181)"), ("background-color", "rgb(238, 242, 246)"), ("background-color", "rgb(241, 246, 255)"),
                        ("border-color", "rgb(216, 223, 230)"), ("border-color", "rgb(122, 135, 147)"), ("border-color", "rgb(26, 77, 181)"), ("border-color", "rgb(231, 236, 241)")}
        assert not (un & roles_listed), "%s: the colours of the roles must not be listed as meaning: %s" % (sid, sorted(un & roles_listed))
        assert all(rep["changed"][r] > 0 for r in ("accent", "page", "surface", "ink", "ink-muted", "border", "border-control", "font-body", "size-body", "size-small", "radius-control",
                                                  "radius-panel", "control-height")), (sid, rep["changed"])
        assert set(rep["font"]) == {"font-body", "font-statement", "font-mono"} and all(set(f) == {"asked", "drawn_with", "stand_in"} for f in rep["font"].values())
        assert rep["tokens"]["--accent"] == "#B5179E" and rep["tokens"]["--target-primary"] == "52px"
    # the explorer's status colours (the chart colours) are what is left as drawn
    ex = {(u["property"], u["value"]) for u in res["index"]["screens"]["explorer"]["report"]["unmapped"]}
    assert ("border-color", "rgb(123, 135, 146)") in ex, "the 'alone' grey, one digit from the input outline, is a status colour and stays"


DARK = {"accent": "#7AA2F7", "accent-text": "#10131A", "page": "#10131A", "surface": "#1A1F2B", "ink": "#E6EAF2", "ink-muted": "#9AA5B8", "border": "#2A3140", "border-control": "#4A5468",
        "hover": "#232A3A", "selected": "#27324A"}


def test_a_dark_theme_on_the_real_prototype_says_that_pale_greys_no_role_names_stay_pale_and_a_light_one_does_not(proto, tmp_path):
    res, out = draw(tmp_path, DARK, ["review"], "dark")
    rep = res["index"]["screens"]["review"]["report"]
    notes = [n for n in rep["notes"] if "pale greys" in n]
    assert len(notes) == 1 and "dark page and surface" in notes[0], rep["notes"]
    n = int(notes[0].split(" ")[0])
    assert n >= 10, "the review picture has dozens of elements on quiet fills; the note counts them (%d)" % n
    left = sum(u["count"] for u in rep["unmapped"] if u["property"] == "background-color" and FT.light_neutral(u["value"]))
    assert n == left, "the sentence and the report list say the same number"
    assert rep["changed"]["page"] > 0 and rep["changed"]["surface"] > 0 and rep["changed"]["ink"] > 0
    res, _ = draw(tmp_path, ALL_CHANGED, ["review"], "light")
    assert not [x for x in res["index"]["screens"]["review"]["report"]["notes"] if "pale greys" in x], "a light theme has nothing to warn about"


def test_drawing_stops_and_names_the_frame_when_the_prototype_no_longer_matches_the_spec_and_writes_nothing(proto, tmp_path, monkeypatch):
    spec = copy.deepcopy(MF.load_spec())
    next(f for f in spec["screens"]["review"] if f["id"] == "queue")["starts"] = "This text is not there"
    monkeypatch.setattr(MF, "load_spec", lambda: spec)
    res = FT.draw_themed({"accent": "#D81B60"}, tmp_path / "out", ["review"])
    assert res["ok"] is False and res["index"] is None and res["files"] == []
    assert len(res["problems"]) == 1 and "review/queue" in res["problems"][0] and "This text is not there" in res["problems"][0] and "nothing was written" in res["problems"][0]
    assert res["problems"][0].startswith("the prototype no longer matches frames_spec.json"), "found before the theme was applied, not blamed on it"
    assert not (tmp_path / "out").exists()
    spec2 = copy.deepcopy(MF.load_spec())
    res = FT.draw_themed({}, tmp_path / "out2", ["nope"], spec=spec2)
    assert res["ok"] is False and "'nope'" in res["problems"][0] and not (tmp_path / "out2").exists()
    with pytest.raises(ValueError, match="not a colour"):
        FT.draw_themed({"accent": "banana"}, tmp_path / "out3", ["review"])


def test_drawing_writes_nothing_when_the_page_reports_an_error_while_it_is_drawn(proto, tmp_path, monkeypatch):
    real = FT.remap_page

    def noisy(pg, ours, theirs, *a, **k):
        out = real(pg, ours, theirs, *a, **k)
        pg.evaluate("console.error('something broke')")
        return out

    monkeypatch.setattr(FT, "remap_page", noisy)
    res = FT.draw_themed({"accent": "#D81B60"}, tmp_path / "out", ["policy"])
    assert res["ok"] is False and "reported problems" in res["problems"][0] and "something broke" in res["problems"][0] and not (tmp_path / "out").exists()


def test_pictures_of_the_same_theme_are_kept_when_more_screens_are_drawn_and_those_of_another_theme_are_removed(proto, tmp_path):
    out = tmp_path / "pics"
    for sid in ("policy", "gold"):
        assert FT.draw_themed({"accent": "#D81B60"}, out, [sid])["ok"]
    index = read_json(out / INDEX_NAME)
    assert list(index["screens"]) == ["gold", "policy"] or list(index["screens"]) == ["policy", "gold"]
    assert list(index["screens"]) == [s for s in MF.load_spec()["screens"] if s in index["screens"]], "in the order of the spec"
    assert (out / "policy.png").is_file() and (out / "gold.png").is_file()
    assert FT.draw_themed({"accent": "#00AA55"}, out, ["gold"])["ok"]
    index = read_json(out / INDEX_NAME)
    assert list(index["screens"]) == ["gold"] and not (out / "policy.png").exists() and index["theme"] == digest(FT.complete_theme({"accent": "#00AA55"}, OURS))


def test_the_command_line_draws_a_session_into_its_pictures_folder(proto, session, capsys):
    before = Path(session, "session.json").read_text()
    assert FT.main([session, "--screens", "policy"]) == 0
    out = Path(session) / "pictures" / "frames"
    printed = capsys.readouterr().out
    assert "wrote 1 pictures" in printed and "policy" in printed and (out / "policy.png").is_file()
    index = read_json(out / INDEX_NAME)
    theirs, ours = FT.load_session_theme(session)
    assert index["theme"] == digest(FT.complete_theme(theirs, ours)) and index["prototype_page"] == MF.page_hash()
    s = index["screens"]["policy"]
    assert [f["id"] for f in s["frames"]] == [f["id"] for f in MF.load_spec()["screens"]["policy"]] and s["report"]["changed"]["accent"] > 0
    assert Path(session, "session.json").read_text() == before, "drawing does not change the session"
    assert sorted(p.name for p in Path(session).iterdir()) == ["mine", "pictures", "session.json"]
