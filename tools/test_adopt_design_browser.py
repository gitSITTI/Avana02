"""The design-adoption kit (design/adopt_design) in a real browser: reading a page, drawing the pictures, and one whole conversation run only by the commands the scripts print.

Skipped when Playwright or its Chromium is not installed (the continuous-integration job installs neither). What this proves, on the made-up page in design/adopt_design/examples/sample_app:
  - reading the page gives the values the committed sample index says, and puts no path of this machine in the index;
  - a picture holds the colours it was told to hold, a font that is not installed is reported as a stand-in and one that is installed is not, and the picture of the person's own page
    differs from the page as it is by exactly the things the notes say were drawn (their button takes our main colour, our menu is drawn over theirs);
  - a page with no menu is told so instead of having one drawn on it;
  - the whole conversation (init, every question, preview, approve, build) runs from the repository's top folder using the printed command form, and the files it writes exist;
  - `verify` says "shown" for a decision the page shows and names the difference, and exits 1, for one it does not; and it does so again after the page is made to show the decision.
What it does not prove: that the pictures look good (a person has to look at them), that any browser but Chromium draws them the same, that the fonts used are installed on another machine, or that a
small model can drive the conversation (nothing here is a model).
"""
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "adopt_design"
sys.path.insert(0, str(KIT / "scripts"))

import adopt  # noqa: E402
import index_page  # noqa: E402
import render as RD  # noqa: E402
import roles as R  # noqa: E402
from common import TOKENS_CSS, css_vars, read_json  # noqa: E402


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

SAMPLE_PAGE = KIT / "examples" / "sample_app" / "index.html"
SAMPLE_INDEX = KIT / "examples" / "sample_index"
OURS = css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
FULL = [("stance", "keep"), ("guesses", "size-small"), ("fix:size-small", "ours"), ("parts", "side-bar,top-bar,buttons,card"), ("change:side-bar", "palette,icons"), ("aspect:side-bar:palette", "ours"),
        ("aspect:side-bar:icons", "remove"), ("change:top-bar", "none"), ("change:buttons", "corners"), ("aspect:buttons:corners", "ours"), ("change:card", "none"), ("screens", "screen-review"),
        ("rows:screen-review", "r1,r2,r3")]


def pil():
    return pytest.importorskip("PIL.Image")


def count_colour(png: str, hexcolour: str, tol: int = 0) -> int:
    img = pil().open(png).convert("RGB")
    want = tuple(int(hexcolour.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    raw = img.tobytes()                                         # r, g, b, r, g, b, ...
    return sum(1 for r, g, b in zip(raw[0::3], raw[1::3], raw[2::3]) if abs(r - want[0]) <= tol and abs(g - want[1]) <= tol and abs(b - want[2]) <= tol)


def run(*argv, cwd=REPO):
    return subprocess.run([sys.executable, *argv], cwd=cwd, capture_output=True, text=True)


@pytest.fixture(scope="module")
def live_index(tmp_path_factory):
    out = tmp_path_factory.mktemp("index")
    return index_page.run(str(SAMPLE_PAGE), str(out), 1440, 900, [], 6), out


def talk(session, steps):
    for qid, val in steps:
        assert adopt.next_question(adopt.model_of(session)[1])["id"] == qid
        assert adopt.main(["answer", session, qid, val, "--no-pictures"]) == 0


@pytest.fixture
def live_session(tmp_path, capsys):
    s = str(tmp_path / "s")
    assert adopt.main(["init", s, "--page", str(SAMPLE_PAGE)]) == 0
    capsys.readouterr()
    return s


# ------------------------------------------------------------------------------------------------ reading a page
def test_reading_the_sample_page_gives_the_values_the_committed_sample_index_says(live_index):
    ix, _ = live_index
    sample = read_json(SAMPLE_INDEX / "index.json")
    assert set(ix["roles"]) == set(sample["roles"]) == {r["id"] for r in R.ROLES["roles"]}
    for role, want in sample["roles"].items():
        got = ix["roles"][role]
        assert got["confidence"] == want["confidence"], f"{role}: confidence changed"
        if R.BY_ID[role]["kind"] == "colour":
            assert R.identical(role, got["value"], want["value"]), f"{role}: {got['value']} is not {want['value']}"
        else:
            assert R.same(role, got["value"], want["value"]), f"{role}: {got['value']} is not {want['value']}"


def test_the_index_of_a_local_file_holds_no_path_of_this_machine(live_index):
    ix, out = live_index
    blob = json.dumps(ix)
    for needle in (str(REPO), str(out), "file://", "/tmp/", "/home/"):
        assert needle not in blob, f"the index holds {needle}"
    assert ix["source"] == "index.html" and ix["structure"]["source"] == "index.html"
    assert any(out.rglob("*.png")), "the reader also leaves pictures of what it read (they are the person's own, in their own session folder)"


def test_the_menu_of_the_sample_page_is_read_with_its_items_and_the_current_one(live_index):
    ix, _ = live_index
    items = [it for lm in ix["structure"]["landmarks"] for g in lm["groups"] for it in g["items"]]
    assert [i["label"] for i in items][:3] == ["Board", "Backlog", "Reports"] and items[0].get("current") == "page"


# ------------------------------------------------------------------------------------------------ the pictures
def test_a_picture_holds_the_colours_it_was_told_to_hold_and_the_parts_are_drawn_in_them(tmp_path):
    magenta = "#B5179E"
    vals = {k: v["value"] for k, v in R.read_ours(TOKENS_CSS.read_text(encoding="utf-8")).items()}
    vals["accent"] = magenta
    with RD.Renderer() as r:
        sheet = r.draw(RD.theme_sheet_html([{"title": "Result", "values": vals}], r.base), tmp_path / "theme.png", [vals["font-body"]])
        tokens = R.tokens_for(vals, OURS)
        parts = r.draw(RD.page_html(RD.cell_html("Buttons", tokens, ["buttons"]), RD.parts_css(["buttons"]), r.base), tmp_path / "parts.png", [vals["font-body"]], width=700)
    assert count_colour(sheet["file"], magenta) > 200, "the swatch for the main colour is not in the theme picture"
    assert count_colour(parts["file"], magenta) > 200, "the main button is not drawn in the chosen colour"
    assert count_colour(parts["file"], OURS["--accent"]) == 0, "our main colour leaked into a picture that was told another"


def test_a_font_that_is_not_installed_is_reported_as_a_stand_in_and_ours_is_not(tmp_path):
    with RD.Renderer() as r:
        res = r.draw(RD.page_html("<p>Words</p>", "", r.base), tmp_path / "f.png", ["Nonexistent Fontname XYZ", "Public Sans", "sans-serif"])
    assert res["stand_in"] == ["Nonexistent Fontname XYZ"]


def test_the_picture_of_the_persons_page_differs_by_what_the_notes_say_and_by_nothing_else(live_session, tmp_path):
    talk(live_session, FULL[:13])
    s, m = adopt.model_of(live_session)
    sel = m.selected_parts()
    with RD.Renderer() as r:
        res = RD.preview_page(r, s["page_url"], [], m.ix, m.mine, m.theme_values(), {p: m.part_values(p) for p in sel}, {p: m.part_tokens(p) for p in sel}, [p for p in sel if m.icons_off(p)], tmp_path)
    before, after = res["before"], res["after"]
    assert Path(before).stat().st_size > 2000 and Path(after).stat().st_size > 2000 and Path(before).read_bytes() != Path(after).read_bytes()
    assert any("side menu" in d and "drawn over yours" in d for d in res["drawn"]) and any("top bar" in d for d in res["drawn"]), res["drawn"]
    theirs, ours_accent = m.mine_value("accent")[0], m.ours_value("accent")
    assert count_colour(before, theirs) > 500 and count_colour(before, ours_accent) == 0
    assert count_colour(after, ours_accent) > 20, "our menu (its current item is written in our main colour) should be drawn over theirs"
    done = "#E3F5E8"                                                  # the "Done" badge: not a part that was chosen, so it must be exactly as it was
    assert count_colour(before, done) > 100 and count_colour(before, done) == count_colour(after, done), "something that was not chosen changed"
    assert "not the code" in res["caveat"]


def test_a_chosen_component_restyles_the_persons_own_buttons_in_the_picture_and_nothing_else_moves(live_session, tmp_path):
    talk(live_session, [("stance", "keep"), ("guesses", "none"), ("parts", "buttons"), ("change:buttons", "corners"), ("aspect:buttons:corners", "ours"), ("screens", "none")])
    s, m = adopt.model_of(live_session)
    with RD.Renderer() as r:
        res = RD.preview_page(r, s["page_url"], [], m.ix, m.mine, m.theme_values(), {"buttons": m.part_values("buttons")}, {"buttons": m.part_tokens("buttons")}, [], tmp_path)
    theirs = m.mine_value("accent")[0]
    assert count_colour(res["after"], theirs) > count_colour(res["before"], theirs) + 20, "their pill button takes our (squarer) corners, so more of it is filled with their colour"
    assert any("button" in d and "corners" in d for d in res["drawn"]) and not any("drawn over yours" in d for d in res["drawn"]), res["drawn"]
    done = "#E3F5E8"
    assert count_colour(res["before"], done) == count_colour(res["after"], done) > 100, "a chip was not chosen and keeps its look"


def test_a_page_with_no_menu_is_told_so_and_no_menu_is_drawn_on_it(tmp_path, capsys):
    plain = tmp_path / "plain.html"
    plain.write_text('<!doctype html><meta charset="utf-8"><title>Plain</title><style>body{font-family:sans-serif;margin:24px}button{height:36px}</style><h1>Plain page</h1><p>No menu here.</p><button>Go</button>', encoding="utf-8")
    s = str(tmp_path / "s")
    assert adopt.main(["init", s, "--page", str(plain)]) == 0
    talk(s, [("stance", "ours")])
    adopt.main(["answer", s, "guesses", "none", "--no-pictures"]) if adopt.next_question(adopt.model_of(s)[1])["id"] == "guesses" else None
    adopt.main(["answer", s, "parts", "side-bar", "--no-pictures"])
    adopt.main(["answer", s, "change:side-bar", "none", "--no-pictures"])
    st, m = adopt.model_of(s)
    with RD.Renderer() as r:
        res = RD.preview_page(r, st["page_url"], [], m.ix, m.mine, m.theme_values(), {"side-bar": m.part_values("side-bar")}, {"side-bar": m.part_tokens("side-bar")}, [], tmp_path / "pics")
    assert any("side menu" in n and "no side menu that could be found" in n for n in res["not_drawn"]), res["not_drawn"]
    assert not any("side menu" in d and "drawn over" in d for d in res["drawn"])


# ------------------------------------------------------------------------------------------------ the whole conversation, from the command line
def test_the_whole_conversation_runs_from_the_top_folder_with_the_printed_commands_and_writes_the_files(tmp_path):
    s = str(tmp_path / "adopt-session")
    script = "design/adopt_design/scripts/adopt.py"
    r = run(script, "init", s, "--page", str(SAMPLE_PAGE))
    assert r.returncode == 0, r.stderr[-600:]
    assert f"python3 {script} next" in r.stdout, "the printed command is not the form that works from the top folder"
    for qid, val in FULL:
        nxt = run(script, "next", s, "--no-pictures")
        assert nxt.returncode == 0 and f"QUESTION" in nxt.stdout and f"({qid})" in nxt.stdout, nxt.stdout[-500:]
        printed = [l for l in nxt.stdout.splitlines() if f" answer " in l and qid in l][-1].strip()
        argv = shlex.split(printed)
        assert argv[:3] == ["python3", script, "answer"] and argv[3] == s
        done = run(*argv[1:4], qid, val, "--no-pictures")
        assert done.returncode == 0, done.stderr[-400:] + done.stdout[-400:]
    assert "Every question is answered" in run(script, "next", s, "--no-pictures").stdout
    assert "no pictures yet" in run(script, "build", s).stderr + run(script, "build", s).stdout
    pr = run(script, "preview", s)
    assert pr.returncode == 0, pr.stderr[-600:]
    pics = {p.name for p in (Path(s) / "preview").iterdir()}
    assert {"theme.png", "parts.png", "page-before.png", "page-after.png", "PREVIEW.md"} <= pics
    for png in ("theme.png", "parts.png", "page-before.png", "page-after.png"):
        assert Path(s, "preview", png).stat().st_size > 3000
    assert "has not said yes" in run(script, "build", s).stderr + run(script, "build", s).stdout
    assert run(script, "approve", s, "--said", "").returncode != 0
    assert run(script, "approve", s, "--said", "yes, write it").returncode == 0
    b = run(script, "build", s)
    assert b.returncode == 0, b.stderr[-600:]
    out = Path(s) / "out"
    assert (out / "CHANGES.md").is_file() and (out / "adopted.tokens.json").is_file() and (out / "parts" / "side-bar" / "part.css").is_file()
    assert read_json(out / "decisions.json")["approved_words"] == "yes, write it"


# ------------------------------------------------------------------------------------------------ verify
def build_session(session, steps, said="yes"):
    talk(session, steps)
    assert adopt.main(["preview", session]) == 0
    assert adopt.main(["approve", session, "--said", said]) == 0
    assert adopt.main(["build", session]) == 0


def verify(session, page, capsys):
    capsys.readouterr()
    code = adopt.main(["verify", session, "--page", str(page)])
    return code, capsys.readouterr().out


def test_verify_says_shown_for_a_page_that_already_has_the_decision_and_exits_zero(live_session, capsys):
    build_session(live_session, [("stance", "keep"), ("guesses", "none"), ("parts", "none"), ("screens", "none")])
    code, out = verify(live_session, SAMPLE_PAGE, capsys)
    assert code == 0, out
    assert out.count("shown") >= 15 and "wanted" not in out


def test_verify_names_what_is_different_and_exits_one_when_the_page_does_not_show_the_decision(live_session, capsys):
    build_session(live_session, [("stance", "ours"), ("parts", "none"), ("screens", "none")])
    code, out = verify(live_session, SAMPLE_PAGE, capsys)
    ours = OURS["--accent"].upper()
    assert code == 1 and f"wanted {ours}, the page has #0F766E" in out, out[:900]


def test_verify_notices_when_a_page_is_changed_to_show_the_decision_and_when_it_is_changed_back(live_session, tmp_path, capsys):
    build_session(live_session, [("stance", "ours"), ("parts", "none"), ("screens", "none")])
    ours = OURS["--accent"].upper()
    changed = tmp_path / "changed.html"
    html = SAMPLE_PAGE.read_text(encoding="utf-8")
    changed.write_text(html.replace("--brand: #0F766E", f"--brand: {ours}").replace("--radius: 6px; --radius-pill: 20px;", f"--radius: {OURS['--radius-ctl']}; --radius-pill: {OURS['--radius-ctl']};"), encoding="utf-8")
    code, out = verify(live_session, changed, capsys)
    line = [l for l in out.splitlines() if l.strip().startswith("Main action colour")]
    assert line and "shown" in line[0], out[:900]
    assert code == 1, "other roles (the page, the text) still differ from ours, so the report must still fail"


def test_verify_looks_for_each_chosen_part_by_its_own_class_and_says_when_the_page_has_none(live_session, tmp_path, capsys):
    build_session(live_session, [("stance", "keep"), ("guesses", "none"), ("parts", "side-bar"), ("change:side-bar", "none"), ("screens", "none")])
    code, out = verify(live_session, SAMPLE_PAGE, capsys)
    assert code == 1 and "not found (looked for .ws-nav)" in out
    with_class = tmp_path / "with-class.html"
    with_class.write_text(SAMPLE_PAGE.read_text(encoding="utf-8").replace('<nav class="side"', '<nav class="side ws-nav"'), encoding="utf-8")
    code, out = verify(live_session, with_class, capsys)
    assert "1 element(s) with .ws-nav" in out and code == 0, out[-500:]


def test_verify_refuses_before_build(live_session):
    talk(live_session, [("stance", "keep"), ("guesses", "none"), ("parts", "none"), ("screens", "none")])
    with pytest.raises(SystemExit) as e:
        adopt.main(["verify", live_session, "--page", str(SAMPLE_PAGE)])
    assert "run build first" in str(e.value)
