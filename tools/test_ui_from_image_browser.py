"""design/ui_from_image/scripts/target_tokens.py drives a real browser, so it is checked here against a page whose every value is known.

Skipped when Playwright or its Chromium is not installed. What this proves: the script reads back the colours, custom properties, radii, shadows, hover and focus changes
and fonts that were written into a fixture page, including a stylesheet a script may not read, and it notices a font that fell back. It does not prove anything about any
real site: pages with shadow roots, cross-origin frames, gradients, canvas drawing or content behind a sign-in are not covered.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "design" / "ui_from_image" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "design"))
import conform as cf  # noqa: E402
import make_tokens  # noqa: E402
import target_tokens as tt  # noqa: E402

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fixture page</title>
<link rel="stylesheet" href="tokens.css">
<style>
:root{--brand:#0B6E6E;--gap:12px}
body{margin:0;background:var(--canvas);color:var(--ink);font-family:var(--sans)}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px;margin:20px;width:420px;box-shadow:0 1px 2px rgba(0,0,0,.08)}
button.go{background:var(--brand);color:#fff;border:0;border-radius:8px;padding:10px 16px;font:600 14px var(--sans)}
button.go:hover{background:#094f4f}
button.go:focus-visible{outline:3px solid #F5A623;outline-offset:2px}
input{border:1px solid #7A8793;border-radius:8px;padding:8px 10px;font:14px var(--sans)}
h1{font-family:"No Such Face",sans-serif;font-size:28px;margin:20px}
.chip{display:inline-block;background:#E1F2E7;color:#14502B;border-radius:999px;padding:2px 10px;font-size:12px}
</style></head><body>
<h1>Fixture heading</h1>
<div class="card"><p>Body text in a card.</p><button class="go">Save</button> <input placeholder="Type here"> <span class="chip">approved</span></div>
</body></html>
"""


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")


@pytest.fixture(scope="module")
def fixture_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("fixture")
    make_tokens.install(make_tokens.load(), str(d))          # tokens.css and the font files, next to the page
    (d / "page.html").write_text(PAGE, encoding="utf-8")
    return d


@pytest.fixture(scope="module")
def result(fixture_dir):
    return tt.run(str(fixture_dir / "page.html"), shots_dir=str(fixture_dir / "shots"))


def by_hex(res, hx):
    return next((c for c in res["colours"] if c["hex"] == hx), None)


def test_custom_properties_come_from_the_page_and_from_a_sheet_a_script_may_not_read(result):
    names = {d["name"]: d for d in result["declared_vars"]}
    assert names["--brand"]["resolved"] == "#0B6E6E" and "from" not in names["--brand"]
    assert names["--accent"]["resolved"] == "#1A4DB5" and names["--accent"]["from"] == "tokens.css"
    assert names["--accent"]["kind"] == "colour" and names["--gap"]["kind"] == "length"


def test_colours_are_exact_counted_by_use_and_named(result):
    brand = by_hex(result, "#0B6E6E")
    assert brand and brand["names"] == ["--brand"] and brand["uses"]["background"] == 1
    ink = by_hex(result, "#1B2733")
    assert ink and "--ink" in ink["names"] and ink["uses"]["text"] >= 2
    assert by_hex(result, "#E1F2E7")["uses"]["background"] == 1 and by_hex(result, "#14502B")["uses"]["text"] == 1
    assert by_hex(result, "#7A8793")["uses"]["border"] >= 1                        # the input's edge
    assert not any(r["value"].startswith("rgba(0, 0, 0") for r in result["unparsed_colours"]), "a translucent colour must not be reported as unreadable"
    assert any(t["value"].startswith("rgba(0, 0, 0") or "0.08" in t["value"] for t in result["translucent_colours"]) or result["shadows"], "the shadow colour was lost"


def test_radii_shadows_and_the_look_of_a_button_are_read_back(result):
    radii = {r["value"]: r["count"] for r in result["radii"]}
    assert radii["12px"] == 1 and radii["8px"] >= 2 and radii["999px"] == 1
    assert any("0px 1px 2px" in s["value"] for s in result["shadows"])
    btn = next(c for c in result["components"] if c["kind"] == "button")
    assert btn["text"] == "Save" and btn["style"]["backgroundColor"] == "rgb(11, 110, 110)" and btn["style"]["borderTopLeftRadius"] == "8px"
    assert btn["style"]["paddingTop"] == "10px" and btn["style"]["fontWeight"] == "600"


def test_hover_and_keyboard_focus_changes_are_measured(result):
    btn = next(c for c in result["components"] if c["kind"] == "button")
    assert btn["states"]["hover"]["backgroundColor"] == ["rgb(11, 110, 110)", "rgb(9, 79, 79)"]
    foc = btn["states"]["keyboard_focus"]
    assert foc["outlineStyle"] == ["none", "solid"] and foc["outlineWidth"] == ["0px", "3px"]
    inp = next(c for c in result["components"] if c["kind"] == "input")
    assert inp["states"]["keyboard_focus"]["outlineStyle"] == ["none", "solid"]       # the design system's own ring from tokens.css


def test_a_font_that_fell_back_is_reported_and_one_that_loaded_is_not(result):
    rendered = {(r["kind"], r["asked_for_first"]): r for r in result["type"]["rendered"]}
    head = rendered[("heading", "No Such Face")]
    assert head["asked_for_font_was_used"] is False and head["drawn_with"] and not head["drawn_with"][0]["custom_font"]
    assert rendered[("button", "Public Sans")]["asked_for_font_was_used"] is True
    faces = {(f["family"], f["status"]) for f in result["type"]["web_fonts_declared"]}
    assert ("Public Sans", "loaded") in faces


def test_every_component_look_has_a_screenshot_and_it_is_a_real_image(result, fixture_dir):
    shots = [c for c in result["components"] if "screenshot" in c]
    assert len(shots) >= 5
    for c in shots:
        data = (fixture_dir / "shots" / c["screenshot"]).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) > 100


def test_nothing_in_the_result_names_a_folder_on_this_machine(result, fixture_dir):
    text = json.dumps(result)
    assert str(fixture_dir) not in text and "/tmp/" not in text, "the output must not carry paths from the machine it ran on"
    assert result["source"] == "page.html"


def test_a_page_built_with_a_colour_the_target_lacks_is_flagged_in_strict_mode(result):
    """Step 7 of SKILL.md: the built page's colours, against the target's tokens. The page's teal button is not one of the target's colours; everything else is."""
    res = cf.conform(result, cf.load_target(str(REPO / "design" / "tokens.css")), cf.STRICT_USE, cf.STRICT_REVIEW)
    not_used = {c["source_hex"]: c["decision"] for c in res["colours"] if c["decision"] != "use"}
    assert not_used == {"#0B6E6E": "review"}, not_used


def test_the_command_line_writes_the_result_and_says_what_fell_back(fixture_dir, tmp_path):
    out = tmp_path / "t.json"
    r = subprocess.run([sys.executable, str(SCRIPTS / "target_tokens.py"), str(fixture_dir / "page.html"), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-400:]
    assert json.loads(out.read_text(encoding="utf-8"))["format"] == "reqin-target-tokens/1"
    assert "fell back to another font" in r.stdout and "(1 fell back" in r.stdout


def test_a_missing_file_is_refused_with_a_plain_message(tmp_path):
    with pytest.raises(SystemExit) as e:
        tt.run(str(tmp_path / "nope.html"))
    assert "no such file" in str(e.value)
