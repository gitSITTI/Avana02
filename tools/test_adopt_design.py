"""The design-adoption kit (design/adopt_design): what it can take, the questions it asks, and the files it writes, checked without a browser.

What must hold: the catalog's parts really match rules in the stylesheets they claim to be drawn from; the roles map onto tokens that exist; the questions are a pure function of the
answers (the same answers give the same next question, in the order SKILL.md lists); a driver that does nothing but copy the command a question prints can finish the conversation; an
answer that is not one of the choices is refused; nothing is built until the person has seen pictures and said yes for exactly these answers, and a changed answer takes that back; and
the files that are written say what was decided, carry the values the answers give, and hold design tokens in the shape the published format asks for.

What it does not prove: that the pictures look right (tools/test_adopt_design_browser.py draws them, and skips where there is no browser), or that an agent following SKILL.md gets a good
result. Uses only the standard library and pytest, so it runs in the continuous-integration job that installs nothing else.
"""
from __future__ import annotations

import copy
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "adopt_design"
sys.path.insert(0, str(KIT / "scripts"))

import adopt  # noqa: E402
import build_out  # noqa: E402
import catalog as CAT  # noqa: E402
import make_frames as MF  # noqa: E402
import render as RD  # noqa: E402
import roles as R  # noqa: E402
from common import TOKENS_CSS, css_vars, read_json  # noqa: E402

SAMPLE_INDEX = KIT / "examples" / "sample_index"
SAMPLE_PAGE = KIT / "examples" / "sample_app" / "index.html"
SKILL = (KIT / "SKILL.md").read_text(encoding="utf-8")

# a whole conversation, in the order the questions come
FULL = [("stance", "keep"), ("guesses", "size-small"), ("fix:size-small", "ours"), ("parts", "side-bar,buttons,card"), ("change:side-bar", "palette,icons"),
        ("aspect:side-bar:palette", "ours"), ("aspect:side-bar:icons", "remove"), ("change:buttons", "corners"), ("aspect:buttons:corners", "ours"), ("change:card", "none"),
        ("screens", "screen-review"), ("rows:screen-review", "r1,r2,r3")]


# ------------------------------------------------------------------------------------------------ helpers
@pytest.fixture
def session(tmp_path, capsys):
    s = str(tmp_path / "s")
    assert adopt.main(["init", s, "--page", str(SAMPLE_PAGE), "--index-from", str(SAMPLE_INDEX)]) == 0
    capsys.readouterr()
    return s


def model(session):
    return adopt.model_of(session)[1]


def say(session, qid, val):
    return adopt.main(["answer", session, qid, val, "--no-pictures"])


def converse(session, steps):
    for qid, val in steps:
        assert adopt.next_question(model(session))["id"] == qid, "the question order is not what SKILL.md says"
        say(session, qid, val)


def refused(fn, *a):
    with pytest.raises(SystemExit) as e:
        fn(*a)
    return str(e.value)


def fake_preview_and_approve(session, said="yes, go ahead"):
    """The pictures need a browser; tools/test_adopt_design_browser.py makes the real ones. Here the preview step is recorded by hand so the steps after it can be tested."""
    s, m = adopt.model_of(session)
    s["preview"] = {"hash": m.fingerprint(), "files": [], "notes": [], "drawn": []}
    adopt.save_session(session, s)
    adopt.cmd_approve(session, said)


# ------------------------------------------------------------------------------------------------ roles
def test_every_role_drives_tokens_that_exist_and_every_role_has_a_value_in_our_design():
    ours = css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    ids = [r["id"] for r in R.ROLES["roles"]]
    assert len(ids) == len(set(ids)) == 21
    areas = {a["id"] for a in R.ROLES["areas"]}
    for r in R.ROLES["roles"]:
        assert r["area"] in areas and r["kind"] in ("colour", "length", "font", "shadow")
        for t in r["ours"] + list((r.get("derive") or {}).keys()):
            assert t in ours, f"{r['id']} drives {t}, which design/tokens.css does not define"
    got = R.read_ours(TOKENS_CSS.read_text(encoding="utf-8"))
    assert all(v["value"] is not None and v["confidence"] == "read" for v in got.values())


def test_the_tokens_a_set_of_our_own_values_drives_are_exactly_ours_as_written():
    ours = css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    vals = {k: v["value"] for k, v in R.read_ours(TOKENS_CSS.read_text(encoding="utf-8")).items()}
    toks = R.tokens_for(vals, ours)
    assert toks and all(ours[t] == v for t, v in toks.items()), "a token drove a value that is not the one design/tokens.css has"
    flat = R.tokens_for(vals)                      # without the as-written table, each role's tokens share its first value
    assert flat["--text-faint"] == flat["--text-muted"] and ours["--text-faint"] != ours["--text-muted"]


def test_the_control_height_also_sets_the_three_sizes_derived_from_it():
    t = R.tokens_for({"control-height": "50px"})
    assert (t["--target-control"], t["--target-primary"], t["--target-compact"], t["--target-smallest"]) == ("50px", "54px", "46px", "42px")


def test_same_forgives_what_a_person_cannot_see_and_identical_does_not():
    assert R.same("accent", "#1A4DB5", "#1B4EB5") and not R.identical("accent", "#1A4DB5", "#1B4EB5")
    assert R.same("size-body", "14px", "15px") and not R.identical("size-body", "14px", "15px")
    assert not R.same("accent", "#1A4DB5", "#B51A4D")
    assert R.same("font-body", '"Inter", sans-serif', "Inter") and not R.same("font-body", "Inter", "Public Sans")
    assert R.same("accent", None, None) and not R.same("accent", None, "#000000")


def test_a_value_the_person_types_is_checked_and_a_value_that_could_carry_code_is_refused():
    assert adopt.check_value("accent", "#0f0") == "#00FF00" and adopt.check_value("size-body", "15") == "15px"
    assert adopt.check_value("font-body", '"Inter", sans-serif') == '"Inter", sans-serif'
    for role, bad in [("accent", "not a colour"), ("size-body", "big"), ("accent", "#fff; background:url(x)"), ("font-body", "a}b"), ("font-body", "url(http://x)"), ("shadow-card", "0 0 1px <b>")]:
        with pytest.raises(ValueError):
            adopt.check_value(role, bad)


def test_contrast_is_worked_out_for_the_pairs_a_person_reads():
    good = {"ink": "#111111", "page": "#FFFFFF", "surface": "#FFFFFF", "ink-muted": "#555555", "accent": "#0F5BC5", "accent-text": "#FFFFFF"}
    assert all(ok for *_, ok in R.contrast_findings(good))
    bad = dict(good, **{"ink-muted": "#CCCCCC"})
    failing = [w for w, r, n, ok in R.contrast_findings(bad) if not ok]
    assert failing and all("quiet text" in w for w in failing)
    assert R.contrast_findings({}) == []


# ------------------------------------------------------------------------------------------------ catalog
def test_the_catalog_checks_out_against_the_files_it_names():
    assert CAT.check() == []
    parts = CAT.all_parts()
    assert len(parts) >= 10 and {p["kind"] for p in parts} == {"shell", "component"}


@pytest.mark.parametrize("part", CAT.all_parts(), ids=lambda p: p["id"])
def test_a_part_is_drawn_from_rules_that_exist_and_uses_no_script_or_address(part):
    css, rep = CAT.part_css(part)
    assert rep["rules"] > 0 and "{" in css
    frag = (KIT / part["specimen"]).read_text(encoding="utf-8")
    assert "<script" not in frag.lower() and "http" not in frag.lower() and "javascript:" not in frag.lower() and "on" + "click" not in frag.lower()


def test_the_catalog_check_catches_a_part_with_no_matching_rule_and_a_specimen_with_a_stray_class():
    cat = copy.deepcopy(CAT.load())
    cat["parts"][0]["css"][0]["selectors"] = ["^\\.nothing-has-this-class\\b"]
    assert any("no rule" in e for e in CAT.check(cat))
    cat = copy.deepcopy(CAT.load())
    cat["parts"][3]["areas"] = ["not-an-area"]
    assert any("not in roles.json" in e for e in CAT.check(cat))
    cat = copy.deepcopy(CAT.load())
    cat["parts"][1]["needs"] = ["ghost"]
    assert any("needs ghost" in e for e in CAT.check(cat))


def test_slicing_keeps_only_the_matching_selectors_of_a_rule_and_only_matching_rules_inside_a_media_block():
    css = "/* c */ .a, .b{color:red} .c{x:y} @media (max-width:100px){.a{y:1} .z{y:2}} @media print{.z{q:1}} .a:hover{k:v}"
    out = CAT.slice_css(css, [r"^\.a\b"])
    assert out[0] == ".a{color:red}"
    assert any(l.startswith("@media (max-width:100px)") and ".a{y:1}" in l and ".z" not in l for l in out)
    assert not any("print" in l for l in out) and ".a:hover{k:v}" in out


def test_literal_colours_become_the_token_that_names_them_by_property_and_the_rest_are_reported():
    tokens = {"--paper": "#FFFFFF", "--text-on-dark": "#FFFFFF", "--accent": "#1A4DB5", "--radius-ctl": "8px"}
    out, replaced, left = CAT.tokenise([".x{background:#fff;color:#FFFFFF;border:1px solid #1A4DB5;border-radius:8px;outline:2px solid #123456}"], tokens)
    assert "background:var(--paper)" in out[0] and "color:var(--text-on-dark)" in out[0] and "border:1px solid var(--accent)" in out[0]
    assert re.search(r"border-radius:\s*var\(--radius-ctl\)", out[0]), "a length that equals a token is written as the token"
    assert "#123456" in out[0] and any(l[2] == "#123456" for l in left)


def test_screens_come_from_the_navigation_map_and_each_has_pieces_from_the_data_map():
    nav = read_json(REPO / "design" / "navigation.json")
    scr = CAT.screens(nav, (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8"))
    assert [s["screen"] for s in scr] == [s["id"] for s in nav["screens"]]
    assert all(s["rows"] for s in scr), "a screen with no row of the data map cannot be given a brief"


def test_the_top_bar_words_the_preview_replaces_are_in_the_specimen():
    spec = (KIT / "specimens" / "top-bar.html").read_text(encoding="utf-8")
    for needle in (">Alpha project<", ">Review queue<", ">All requirements<", ">Pre-baseline<", 'placeholder="Search requirements"'):
        assert needle in spec, f"render.top_bar_from_page looks for {needle}"


# ------------------------------------------------------------------------------------------------ the questions
def test_the_questions_are_a_pure_function_of_the_answers_and_come_in_the_order_the_skill_lists(session):
    for qid, _ in FULL:
        m = model(session)
        before = copy.deepcopy(m.A)
        q1, q2 = adopt.next_question(m), adopt.next_question(m)
        assert q1 == q2 and m.A == before and q1["id"] == qid
        say(session, qid, dict(FULL)[qid])
    assert adopt.next_question(model(session)) is None
    for token in ("stance", "area:", "guesses", "parts", "change:", "aspect:", "screens", "rows:"):
        assert token in SKILL, f"SKILL.md does not list the question {token}"


def test_every_question_has_words_to_say_choices_that_differ_and_a_command_that_records_the_answer(session, capsys):
    seen = 0
    for qid, val in FULL + [("__end__", "")]:
        q = adopt.next_question(model(session))
        if q is None:
            break
        ids = [o["id"] for o in q["options"]]
        assert q["say"].strip().endswith(("?", ".")) and len(set(ids)) == len(ids) and (len(ids) >= 2 or q["id"].startswith("fix:"))
        text = adopt.describe(q, session, [], [], 1)
        assert q["id"] in text and "answer" in text and "Ask the person" in text
        if q["id"].startswith("fix:"):
            assert " set " in q["help"] and "VALUE" in q["help"], "a question with one choice must say how the person gives the right value"
        seen += 1
        say(session, qid, val)
    assert seen == len(FULL)
    capsys.readouterr()


def test_a_driver_that_only_copies_the_printed_command_and_picks_the_first_choice_can_finish(session, capsys):
    capsys.readouterr()
    for _ in range(90):
        adopt.cmd_next(session, pictures=False)
        out = capsys.readouterr().out
        if "Every question is answered" in out:
            break
        line = [l for l in out.splitlines() if " answer " in l and ("CHOICE" in l)][-1]
        argv = shlex.split(line.strip())
        assert argv[0] == "python3" and argv[2] == "answer"
        first = re.search(r"Their choices.*?:\n\s+(\S+)", out, re.S).group(1)
        argv[-1] = first
        assert adopt.main(argv[2:] + ["--no-pictures"]) == 0
        capsys.readouterr()
    else:
        pytest.fail("the conversation did not end in 90 questions")
    assert adopt.stage_of(*adopt.model_of(session)) == "ready to preview"


def test_an_answer_that_is_not_a_choice_or_not_the_question_waiting_is_refused_and_nothing_is_recorded(session):
    before = adopt.load_session(session)["answers"]
    assert "not one of the choices" in refused(adopt.cmd_answer, session, "stance", "maybe", False)
    assert "question waiting is stance" in refused(adopt.cmd_answer, session, "parts", "none", False)
    assert adopt.load_session(session)["answers"] == before == {}
    say(session, "stance", "keep")
    say(session, "guesses", "none")
    assert "cannot be combined" in refused(adopt.cmd_answer, session, "parts", "none,card", False)
    assert "not one of the choices" in refused(adopt.cmd_answer, session, "parts", "side-bar,ghost", False)
    assert "at least one choice" in refused(adopt.cmd_answer, session, "parts", " ", False)


def test_all_and_none_in_a_multiple_choice_mean_what_they_say(session):
    say(session, "stance", "keep")
    say(session, "guesses", "none")
    say(session, "parts", "all")
    assert adopt.load_session(session)["answers"]["parts"] == [p["id"] for p in CAT.all_parts()]
    adopt.main(["back", session, "--to", "parts"])
    say(session, "parts", "none")
    assert adopt.load_session(session)["answers"]["parts"] == []
    assert adopt.next_question(model(session))["id"] == "screens"


def test_the_option_that_looks_the_same_as_the_default_is_not_offered_twice(session):
    say(session, "stance", "keep")
    say(session, "guesses", "none")
    say(session, "parts", "buttons")
    say(session, "change:buttons", "corners")
    ids = [o["id"] for o in adopt.next_question(model(session))["options"]]
    assert ids == ["theme", "ours", "square"], "keeping your theme: yours is the default, so mine is not a second choice"
    adopt.main(["back", session, "--to", "stance"])
    say(session, "stance", "ours")
    say(session, "parts", "buttons")
    say(session, "change:buttons", "corners")
    assert [o["id"] for o in adopt.next_question(model(session))["options"]] == ["theme", "mine", "square"]


def test_deciding_area_by_area_asks_each_area_and_square_and_no_shadow_are_choices_only_where_they_make_sense(session):
    say(session, "stance", "choose")
    seen = []
    for area in adopt.AREAS:
        q = adopt.next_question(model(session))
        seen.append(q["id"])
        assert q["id"] == "area:" + area
        say(session, q["id"], "mine")
    assert seen == ["area:" + a for a in adopt.AREAS]
    opts = {a["id"]: a["options"] for a in R.ROLES["areas"]}
    assert "square" in opts["corners"] and "none" in opts["depth"] and "square" not in opts["palette"]


def test_a_value_read_as_a_guess_is_asked_about_once_and_a_correction_removes_the_question(session):
    say(session, "stance", "keep")
    q = adopt.next_question(model(session))
    assert q["id"] == "guesses" and {o["id"] for o in q["options"]} >= {"ink-muted", "size-small", "none"}
    adopt.main(["set", session, "ink-muted", "#334455"])
    adopt.main(["set", session, "size-small", "13"])
    adopt.main(["set", session, "font-statement", "Georgia, serif"])
    assert adopt.next_question(model(session))["id"] == "parts", "every guess was corrected, so nothing is left to ask about"
    m = model(session)
    assert m.mine_value("ink-muted") == ("#334455", "set by you") and m.theme_values()["size-small"] == "13px"


def test_in_deciding_to_take_ours_a_guess_on_the_page_is_not_asked_about_because_it_is_not_used(session):
    say(session, "stance", "ours")
    assert adopt.next_question(model(session))["id"] == "parts"


def test_back_takes_back_the_last_answer_or_everything_from_one_answer_on(session):
    converse(session, FULL[:6])
    adopt.main(["back", session])
    assert list(adopt.load_session(session)["answers"]) == [q for q, _ in FULL[:5]]
    adopt.main(["back", session, "--to", "guesses"])
    assert list(adopt.load_session(session)["answers"]) == ["stance"]
    assert "has not been answered" in refused(adopt.cmd_back, session, "parts")
    assert adopt.next_question(model(session))["id"] == "guesses"


def test_changing_an_answer_after_a_change_question_ignores_aspects_that_are_no_longer_chosen(session):
    converse(session, FULL[:5])
    adopt.main(["back", session, "--to", "change:side-bar"])
    say(session, "change:side-bar", "icons")
    m = model(session)
    assert m.changes("side-bar") == ["icons"] and adopt.next_question(m)["id"] == "aspect:side-bar:icons"


# ------------------------------------------------------------------------------------------------ decisions
def test_a_part_changed_alone_gets_only_the_tokens_it_uses_and_the_rest_of_the_result_is_untouched(session):
    converse(session, FULL)
    m = model(session)
    theme = m.theme_tokens()
    side = m.part_tokens("side-bar")
    assert side["--accent"] == m.ours_value("accent") != theme["--accent"] == m.mine_value("accent")[0]
    assert m.part_tokens("card") == theme and m.part_tokens("buttons")["--radius-ctl"] == m.ours_value("radius-control") != theme["--radius-ctl"]
    assert m.icons_off("side-bar") and not m.icons_off("buttons")
    assert m.theme_values()["radius-control"] == m.mine_value("radius-control")[0], "the theme still has the person's corners"


def test_parts_a_chosen_part_needs_are_added_and_say_so(session):
    cat = CAT.load()
    m = model(session)
    m.parts[0]["needs"] = ["card"]               # a made-up dependency: the test is about the mechanism
    m.A["parts"] = [m.parts[0]["id"]]
    assert "card" in m.selected_parts() and m.added_by_need() == ["card"]


def test_the_fingerprint_changes_when_an_answer_a_correction_or_the_page_reading_changes(session):
    converse(session, FULL)
    m = model(session)
    base = m.fingerprint()
    assert m.fingerprint() == base
    m2 = adopt.Model(m.ix, dict(m.A, **{"change:card": ["palette"]}), m.ov)
    assert m2.fingerprint() != base
    assert adopt.Model(m.ix, m.A, {"accent": "#123456"}).fingerprint() != base
    ix = copy.deepcopy(m.ix)
    ix["roles"]["accent"]["value"] = "#123456"
    assert adopt.Model(ix, m.A, m.ov).fingerprint() != base


# ------------------------------------------------------------------------------------------------ approval and build
def test_nothing_is_built_until_the_pictures_are_made_and_the_person_has_said_yes_for_exactly_these_answers(session):
    converse(session, FULL)
    assert "no pictures yet" in refused(adopt.cmd_build, session)
    assert "nothing to approve" in refused(adopt.cmd_approve, session, "yes")
    s, m = adopt.model_of(session)
    s["preview"] = {"hash": m.fingerprint(), "files": [], "notes": [], "drawn": []}
    adopt.save_session(session, s)
    assert "needs the person's own words" in refused(adopt.cmd_approve, session, "  ")
    assert "has not said yes" in refused(adopt.cmd_build, session)
    adopt.cmd_approve(session, "yes please")
    assert adopt.stage_of(*adopt.model_of(session)) == "approved"
    adopt.main(["set", session, "accent", "#123456"])                    # a change after the yes takes the yes back
    st = adopt.stage_of(*adopt.model_of(session))
    assert st in ("ready to preview", "asking") and "no pictures" in refused(adopt.cmd_build, session)
    assert "approved" not in adopt.load_session(session) and "preview" not in adopt.load_session(session)


def test_a_session_file_edited_by_hand_to_look_approved_for_other_answers_is_still_refused(session):
    converse(session, FULL)
    fake_preview_and_approve(session)
    s = adopt.load_session(session)
    s["answers"]["change:card"] = ["palette"]                              # edit an answer without going through the commands: the fingerprint no longer matches
    adopt.save_session(session, s)
    assert adopt.stage_of(*adopt.model_of(session)) in ("asking", "ready to preview")
    assert "not built" in refused(adopt.cmd_build, session)


def test_the_files_that_are_built_say_what_was_decided_and_carry_the_values_the_answers_give(session):
    converse(session, FULL)
    fake_preview_and_approve(session, "yes, build it")
    assert adopt.main(["build", session]) == 0
    out = Path(session) / "out"
    names = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    assert {"CHANGES.md", "REPORT.md", "adopted-tokens.css", "adopted.tokens.json", "decisions.json", "parts/side-bar/part.css", "parts/side-bar/specimen.html", "parts/side-bar/NOTES.md",
            "parts/buttons/part.css", "parts/card/part.css", "screens/review.md"} <= names
    assert not any(n.startswith("parts/top-bar") for n in names), "a part that was not chosen is not written"
    m = model(session)
    css = (out / "adopted-tokens.css").read_text(encoding="utf-8")
    for tok, val in m.theme_tokens().items():
        assert re.search(r"%s:%s;" % (re.escape(tok), re.escape(val)), css), f"{tok} should be {val} in adopted-tokens.css"
    side = (out / "parts" / "side-bar" / "part.css").read_text(encoding="utf-8")
    assert ".ws-nav{--accent:%s" % m.ours_value("accent") in side and ".ws-nav .nav-btn svg{display:none}" in side
    assert "What was decided for this part alone" not in (out / "parts" / "card" / "part.css").read_text(encoding="utf-8")
    changes = (out / "CHANGES.md").read_text(encoding="utf-8")
    for r in R.ROLES["roles"]:
        assert r["label"] in changes
    assert "ours, because you said the guess was wrong" in changes and "screens/review.md" in changes
    brief = (out / "screens" / "review.md").read_text(encoding="utf-8")
    assert "you kept 3 of" in brief and "Left out on purpose" in brief and "A queue row: its size" in brief
    report = (out / "REPORT.md").read_text(encoding="utf-8")
    assert "yes, build it" in report and "Contrast of the result" in report and "What was not checked" in report
    dec = read_json(out / "decisions.json")
    assert dec["fingerprint"] == m.fingerprint() and dec["approved_words"] == "yes, build it" and dec["screens"][0]["kept"] == ["r1", "r2", "r3"]


def test_every_token_a_built_part_uses_is_defined_in_the_adopted_tokens_or_in_the_part(session):
    converse(session, [("stance", "keep"), ("guesses", "none"), ("parts", "all"), *[(f"change:{p['id']}", "none") for p in CAT.all_parts()], ("screens", "none")])
    fake_preview_and_approve(session)
    adopt.main(["build", session])
    out = Path(session) / "out"
    defined = set(re.findall(r"(--[\w-]+):", (out / "adopted-tokens.css").read_text(encoding="utf-8")))
    for part_css in (out / "parts").glob("*/part.css"):
        used = set(re.findall(r"var\((--[\w-]+)", part_css.read_text(encoding="utf-8")))
        assert used <= defined, f"{part_css.parent.name} uses {sorted(used - defined)}, which nothing defines"
    assert "Token names no file defines**: none" in (out / "REPORT.md").read_text(encoding="utf-8")


def test_taking_our_theme_writes_our_tokens_as_they_are_and_square_and_no_shadow_write_zero_and_none(session):
    converse(session, [("stance", "ours"), ("parts", "card,source-chip"), ("change:card", "corners"), ("aspect:card:corners", "square"), ("change:source-chip", "depth"), ("aspect:source-chip:depth", "none"),
                       ("screens", "none")])
    fake_preview_and_approve(session)
    adopt.main(["build", session])
    out = Path(session) / "out"
    ours = css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    css = (out / "adopted-tokens.css").read_text(encoding="utf-8")
    for tok in ("--accent", "--text-faint", "--text-muted", "--radius-ctl", "--target-primary", "--shadow-lift"):
        assert "%s:%s;" % (tok, ours[tok]) in css
    card = (out / "parts" / "card" / "part.css").read_text(encoding="utf-8")
    chip = (out / "parts" / "source-chip" / "part.css").read_text(encoding="utf-8")
    assert ".rq-card{--radius-panel:0px}" in card and ".chip-src{--shadow-lift:none}" in chip


def test_the_design_tokens_file_has_the_shapes_the_2025_10_format_asks_for(session):
    converse(session, FULL)
    fake_preview_and_approve(session)
    adopt.main(["build", session])
    doc = read_json(Path(session) / "out" / "adopted.tokens.json")
    assert doc["$schema"].endswith("/2025.10/format.json")
    spaces = {"srgb", "srgb-linear", "hsl", "hwb", "lab", "lch", "oklab", "oklch", "display-p3", "a98-rgb", "prophoto-rgb", "rec2020", "xyz-d65", "xyz-d50"}

    def colour(v):
        assert isinstance(v, dict) and v["colorSpace"] in spaces and len(v["components"]) == 3 and all(0 <= c <= 1 for c in v["components"])
        assert re.fullmatch(r"#[0-9a-f]{6}", v["hex"]) and (0 <= v.get("alpha", 1) <= 1)

    def dimension(v):
        assert isinstance(v, dict) and isinstance(v["value"], (int, float)) and v["unit"] in ("px", "rem")

    n = {"color": 0, "dimension": 0, "fontFamily": 0, "shadow": 0}
    for group, toks in doc.items():
        if group.startswith("$"):
            continue
        for name, t in toks.items():
            if "$type" not in t:
                assert group == "text" and "$description" in t
                continue
            assert t["$type"] in n
            n[t["$type"]] += 1
            v = t["$value"]
            if t["$type"] == "color":
                colour(v)
            elif t["$type"] == "dimension":
                dimension(v)
            elif t["$type"] == "fontFamily":
                assert isinstance(v, (str, list)) and all(isinstance(x, str) for x in (v if isinstance(v, list) else [v]))
            else:
                for sh in (v if isinstance(v, list) else [v]):
                    colour(sh["color"])
                    [dimension(sh[k]) for k in ("offsetX", "offsetY", "blur", "spread")]
    assert all(n.values()), f"every kind of token should appear in the sample: {n}"


def test_a_colour_with_transparency_and_a_shadow_with_two_layers_become_the_formats_objects():
    c = build_out._color_obj("rgba(31, 41, 51, 0.12)")
    assert c == {"colorSpace": "srgb", "components": [0.1216, 0.1608, 0.2], "alpha": 0.12, "hex": "#1f2933"}
    two = build_out._dtcg_shadow("0 1px 2px rgba(21,32,43,.06),0 6px 18px rgba(21,32,43,.08)")
    assert isinstance(two, list) and two[1]["blur"] == {"value": 18, "unit": "px"} and two[0]["color"]["alpha"] == 0.06
    assert build_out._dtcg_shadow("inset 0 0 3px #000")["inset"] is True and build_out._dtcg_shadow("a lot of shadow") is None
    assert build_out._dimension("0.5rem") == {"value": 0.5, "unit": "rem"} and build_out._dimension("50%") is None


def test_a_name_the_persons_page_already_declares_is_reported_in_changes(session):
    ixp = Path(session) / "mine" / "index.json"
    ix = read_json(ixp)
    ix["declared_vars"].append({"name": "--accent", "value": "#FF0000", "resolved": "#FF0000", "kind": "colour", "selector": ":root", "context": ""})
    ixp.write_text(json.dumps(ix), encoding="utf-8")
    converse(session, FULL)
    fake_preview_and_approve(session)
    adopt.main(["build", session])
    changes = (Path(session) / "out" / "CHANGES.md").read_text(encoding="utf-8")
    assert "Names that clash with yours" in changes and "`--accent`" in changes


def test_a_change_to_the_pages_reading_after_the_yes_takes_the_yes_back(session):
    converse(session, FULL)
    fake_preview_and_approve(session)
    ixp = Path(session) / "mine" / "index.json"
    ix = read_json(ixp)
    ix["roles"]["accent"]["value"] = "#123456"
    ixp.write_text(json.dumps(ix), encoding="utf-8")
    assert "not built" in refused(adopt.cmd_build, session)


def test_a_part_may_offer_only_changes_that_change_its_code():
    cat = copy.deepcopy(CAT.load())
    card = next(p for p in cat["parts"] if p["id"] == "card")
    card["areas"] = card["areas"] + ["depth"]                      # the card has no shadow rule: choosing "no shadow" for it would write nothing
    assert any("card" in e and "depth" in e and "change nothing" in e for e in CAT.check(cat))
    for p in CAT.all_parts():                                    # and each part really does use a token of every area it offers
        css, _ = CAT.part_css(p)
        used = set(re.findall(r"var\((--[\w-]+)", css))
        for a in p["areas"]:
            driven = {t for r in R.roles_of_area(a) for t in R.BY_ID[r]["ours"] + list(R.BY_ID[r].get("derive") or {})}
            assert used & driven, f"{p['id']} offers {a} but its css uses none of {sorted(driven)}"


def test_choosing_our_fonts_for_a_part_reaches_the_code_and_the_heights_follow_the_control_size(session):
    converse(session, [("stance", "keep"), ("guesses", "none"), ("parts", "buttons"), ("change:buttons", "type,density"), ("aspect:buttons:type", "ours"), ("aspect:buttons:density", "ours"), ("screens", "none")])
    fake_preview_and_approve(session)
    adopt.main(["build", session])
    css = (Path(session) / "out" / "parts" / "buttons" / "part.css").read_text(encoding="utf-8")
    m = model(session)
    assert ".rq-button,.rq-primary,.ghost-btn{font-family:var(--sans);font-size:var(--size-body)}" in css and "min-height:var(--target-primary)" in css
    scoped = re.search(r"\.rq-button,\.rq-primary,\.ghost-btn\{([^}]*)\}\s*$", css).group(1)
    assert "--sans:" + m.ours_value("font-body") in scoped and "--target-primary:" + m.ours_vars["--target-primary"] in scoped


# ------------------------------------------------------------------------------------------------ the pure parts of the picture maker
def test_our_menu_is_drawn_with_the_persons_own_items_and_their_words_cannot_inject_markup():
    structure = {"landmarks": [{"groups": [{"heading": "", "items": [{"label": "Board", "current": "page", "count": "3"}, {"label": "<img src=x onerror=alert(1)>"}]},
                                              {"heading": "More <b>", "items": [{"label": "Reports"}]}]}]}
    spec = (KIT / "specimens" / "side-bar.html").read_text(encoding="utf-8")
    html, note = RD.side_bar_from_structure(structure, spec)
    assert 'aria-current="page"' in html and ">Board<" in html and ">3<" in html and "&lt;img" in html and "<img" not in html and "&lt;b&gt;" in html and "stand-in" in note
    same, note2 = RD.side_bar_from_structure(None, spec)
    assert same == spec and "could not be read" in note2


def test_the_top_bar_takes_the_persons_title_without_ours_and_without_markup_injection():
    spec = (KIT / "specimens" / "top-bar.html").read_text(encoding="utf-8")
    out = RD.top_bar_from_page(spec, "My <b>app</b>", "Board")
    assert "My &lt;b&gt;app&lt;/b&gt;" in out and ">Board<" in out and "Pre-baseline" not in out and "All requirements" not in out and "Alpha project" not in out
    for title, heading in (("My app", ""), ("My app", "My app"), ("", "")):             # no heading of theirs (or the same as the title): none of our made-up screen names is left behind
        bare = RD.top_bar_from_page(spec, title, heading)
        assert "Review queue" not in bare and "Alpha project" not in bare and ">/<" not in bare, (title, heading)


def test_the_page_preview_restyles_only_what_differs_and_only_with_selectors_that_find_their_group():
    ix = {"components": [{"kind": "button", "selector": {"selector": ".btn", "jaccard": 1.0}, "style": {"backgroundColor": "rgb(15, 118, 110)"}},
                         {"kind": "button", "selector": {"selector": ".ghost", "jaccard": 1.0}, "style": {"backgroundColor": "rgba(0, 0, 0, 0)"}},
                         {"kind": "card", "selector": {"selector": "div", "jaccard": 0.2}, "style": {}}]}
    mine = {"accent": {"value": "#0F766E"}, "radius-control": {"value": "20px"}, "radius-panel": {"value": "6px"}}
    css, drawn, missing = RD.restyle_css(ix, mine, {"accent": "#1A4DB5", "radius-control": "20px", "radius-panel": "12px"})
    assert ".btn{background-color:#1A4DB5 !important}" in css and "border-radius:20px" not in css, "an unchanged role must not be restyled"
    assert ".ghost{background-color" not in css, "only the button that has the main colour takes the main colour"
    assert "card corners" not in " ".join(drawn) and any("card" in m for m in missing), "a selector that finds a fifth of its group is not used, and the picture says so"


def test_a_picture_page_has_the_fonts_the_tokens_name_pointed_at_the_local_server_and_escapes_its_labels():
    html = RD.page_html(RD.cell_html('A <b>label</b>', {"--accent": "#123456"}, ["buttons"]), RD.parts_css(["buttons"]), "http://127.0.0.1:1", ["a <i>note</i>"], "t")
    assert "url(http://127.0.0.1:1/fonts/public-sans-latin-400-normal.woff2)" in html and "A &lt;b&gt;label" in html and "a &lt;i&gt;note" in html and "--accent:#123456" in html
    assert RD.prefix_css(".a,.b{x:y} @media (min-width:1px){.c{z:1}}", ".cell ").replace(" ", "").startswith(".cell.a,.cell.b{x:y}")


def test_the_theme_sheet_shows_every_colour_role_in_every_column_and_marks_guesses():
    vals = {k: v["value"] for k, v in R.read_ours(TOKENS_CSS.read_text(encoding="utf-8")).items()}
    html = RD.theme_sheet_html([{"title": "Yours", "values": vals, "conf": {"ink-muted": "guess"}}, {"title": "Ours", "values": vals}], "http://x")
    for r in R.ROLES["roles"]:
        if r["area"] == "palette":
            assert html.count(r["label"]) == 2
    assert "(a guess)" in html and html.count("Public Sans") >= 2


# ------------------------------------------------------------------------------------------------ SKILL.md and the kit's files say only what is true
def test_the_skill_has_the_front_matter_an_agent_runtime_reads():
    m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n", SKILL)
    assert m and m.group(1) == "adopt-design" and 20 < len(m.group(2)) <= 1024


def test_every_command_the_skill_and_the_prompt_tell_an_agent_to_run_exists_with_those_flags():
    prompt = (REPO / "docs" / "agent_prompts" / "adopt_a_design.md").read_text(encoding="utf-8")
    cmds = re.findall(r"`(python3 design/adopt_design/scripts/\w+\.py[^`]*)`", SKILL + prompt)
    assert len(cmds) >= 12
    for c in cmds:
        parts = shlex.split(c.replace("<SESSION>", "S").replace("<PAGE>", "P").replace("<what they said>", "x"))
        script = REPO / parts[1]
        assert script.is_file(), parts[1]
        sub = [parts[2]] if script.name == "adopt.py" and len(parts) > 2 and not parts[2].startswith("-") else []
        helped = subprocess.run([sys.executable, str(script), *sub, "--help"], capture_output=True, text=True)
        assert helped.returncode == 0, helped.stderr[-300:]
        for flag in re.findall(r"(?<![\w-])(--[a-z][a-z-]+)", c):
            assert flag in helped.stdout, f"{c!r}: {flag} is not a flag of {script.name} {' '.join(sub)}"


def test_every_file_the_skill_names_exists_and_it_names_no_product():
    for rel in re.findall(r"`((?:scripts|examples|specimens)/[\w./-]+|catalog\.json|roles\.json|requirements\.txt|RESEARCH\.md)`", SKILL):
        assert (KIT / rel.rstrip("/")).exists(), f"SKILL.md names {rel}, which is not in design/adopt_design"
    for rel in re.findall(r"`((?:docs|reqin|design|tools)/[\w./-]+\.(?:md|css|json|py))`", SKILL):
        assert (REPO / rel).exists(), f"SKILL.md names {rel}, which does not exist"
    low = SKILL.lower()
    for word in ("gemini", "gpt", "openai", "chatgpt", "copilot", "excalidraw", "figma", "claude", "anthropic"):
        assert word not in low, f"SKILL.md names {word}: the repo's documents name no product"
    plain = " ".join(low.replace("*", "").split())
    assert "untested" in plain and "has not been tried" in plain, "SKILL.md must say that small-model operation has not been tried"


def test_the_kits_files_hold_no_machine_path_no_personal_name_and_the_samples_are_made_up():
    for p in KIT.rglob("*"):
        if p.is_file() and p.suffix in (".md", ".json", ".html", ".py", ".txt") and "__pycache__" not in p.parts:
            t = p.read_text(encoding="utf-8")
            assert not re.search(r"/home/|/tmp/|file:///|/Users/|C:\\\\Users", t), f"{p.relative_to(REPO)} holds a machine path"
    ix = read_json(SAMPLE_INDEX / "index.json")
    assert ix["source"] == "index.html" and ix["structure"]["source"] == "index.html"
    assert "Made-up" in SAMPLE_PAGE.read_text(encoding="utf-8") or "made-up" in SAMPLE_PAGE.read_text(encoding="utf-8")


def test_the_research_page_says_what_was_not_read_and_does_not_claim_a_tool_works_that_was_not_run():
    t = (KIT / "RESEARCH.md").read_text(encoding="utf-8")
    assert "Looked for, and not read" in t and "What this research does not establish" in t and "was not installed or run" in t
    assert "**The kit does not depend on it.**" in t


# ---------------------------------------------------------------------------------------------------- frames: the pieces of our screens that have pictures
def test_every_screen_has_frames_and_every_frame_names_pieces_the_data_map_lists():
    assert MF.spec_problems() == []
    spec = MF.load_spec()
    assert set(spec["screens"]) == {s["id"] for s in read_json(REPO / "design" / "navigation.json")["screens"]}


@pytest.mark.parametrize("breakage,expected", [
    (lambda sp: sp["screens"].pop("audit"), "screen audit has no frames"),
    (lambda sp: sp["screens"].update(nowhere=[{"id": "a", "label": "x", "path": [0], "starts": "x", "rows": []}]), "not a screen"),
    (lambda sp: sp["screens"]["open"].append(dict(sp["screens"]["open"][0])), "used twice"),
    (lambda sp: sp["screens"]["open"][0].update(rows=["r99"]), "not one of the"),
    (lambda sp: sp["screens"]["open"][0].update(rows=["row1"]), "not one of the"),
    (lambda sp: sp["screens"]["open"][0].update(starts=" "), "starts is empty"),
    (lambda sp: sp["screens"]["open"][0].update(path=[]), "path must be a list"),
    (lambda sp: sp["screens"]["open"][0].update(path=[-1]), "path must be a list"),
])
def test_a_broken_frame_list_is_refused_and_says_what_is_wrong(breakage, expected):
    spec = copy.deepcopy(MF.load_spec())
    breakage(spec)
    errs = MF.spec_problems(spec)
    assert errs and any(expected in e for e in errs), errs


def test_a_piece_of_the_data_map_may_be_drawn_across_several_frames_and_a_frame_may_hold_none():
    spec = MF.load_spec()
    held: dict = {}
    for sid, frames in spec["screens"].items():
        for f in frames:
            for r in f["rows"]:
                held.setdefault((sid, r), []).append(f["id"])
    assert any(len(v) > 1 for v in held.values()), "the methods screen draws one piece across four frames; the spec lost that"
    assert any(not f["rows"] for frames in spec["screens"].values() for f in frames)


def test_the_frame_index_matches_the_spec_the_pictures_exist_and_every_box_is_inside_its_picture():
    assert MF.index_problems() == []
    idx = read_json(MF.INDEX)
    for sid, s in idx["screens"].items():
        png = (MF.OUT / s["image"]).read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n", sid
        w, h = int.from_bytes(png[16:20], "big"), int.from_bytes(png[20:24], "big")
        assert (w, h) == (s["width"], s["height"]), f"{sid}: the picture is {w}x{h}, frames.json says {s['width']}x{s['height']}"
        for f in s["frames"]:
            assert f["box"] is not None, f"{sid}/{f['id']} found nothing when the pictures were drawn"


def test_the_frame_index_is_refused_when_the_page_it_was_drawn_from_has_changed(tmp_path, monkeypatch):
    page = tmp_path / "Main.dc.html"
    page.write_text("<html>another page</html>", encoding="utf-8")
    monkeypatch.setattr(MF, "PAGE", page)
    assert any("another version" in e for e in MF.index_problems())


def test_the_frame_index_holds_no_machine_path():
    assert not re.search(r"/home/|/tmp/|file:///|/Users/", MF.INDEX.read_text(encoding="utf-8"))
