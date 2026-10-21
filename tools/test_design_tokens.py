"""design/tokens.json must say what the prototype does, because an agent that builds a screen from it will believe it.

Each test reads the prototype's own source (not a copy of it) and compares. Nothing here looks at a browser; design/README.md says what the browser check adds.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "design"))
import make_tokens as mt  # noqa: E402

HEAD = (REPO / "prototype" / "parts" / "m" / "00_head.html").read_text(encoding="utf-8")
BUILD = (REPO / "prototype" / "build.py").read_text(encoding="utf-8")
T = mt.load()


def root_vars() -> dict[str, str]:
    block = re.search(r":root\{(.*?)\n\}", HEAD, re.S).group(1)
    return {m.group(1): m.group(2).strip() for m in re.finditer(r"(--[\w-]+):([^;]+);", block)}


def lum(h: str) -> float:
    r, g, b = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def test_the_stylesheet_is_what_the_json_produces():
    assert (REPO / "design" / "tokens.css").read_text(encoding="utf-8") == mt.render(T), "run: python3 design/make_tokens.py"


def test_every_variable_the_prototype_defines_has_the_same_value_here():
    css_vars = dict(re.findall(r"(--[\w-]+):([^;]+);", mt.render(T)))
    proto = root_vars()
    assert proto, "could not read the prototype's :root block"
    shared = [k for k in proto if k in css_vars]
    # the prototype's names that the tokens must carry: if one is missing the check would pass by comparing nothing
    for must in ("--ink", "--slate", "--line", "--hair", "--canvas", "--paper", "--band", "--redline", "--ok", "--warn",
                 "--radius-panel", "--radius-ctl", "--radius-chip", "--shadow-lift", "--serif", "--sans", "--mono"):
        assert must in proto, f"the prototype no longer defines {must}; update this test and tokens.json"
        assert must in css_vars, f"tokens.css lacks the prototype's {must}"
    for k in shared:
        assert css_vars[k].lower() == proto[k].lower(), f"{k}: tokens {css_vars[k]} but the prototype {proto[k]}"


def test_no_colour_is_invented():
    c = mt.coverage(T)
    assert c["named_not_in_prototype"] == [], "named by a token but written nowhere in the prototype: %s" % c["named_not_in_prototype"]


def test_the_tokens_cover_most_of_what_the_prototype_actually_uses():
    c = mt.coverage(T)
    assert c["share"] >= 0.85, "only %.1f%% of the prototype's colour uses are token colours" % (100 * c["share"])


def test_accent_default_and_options_are_the_pages_own():
    m = re.search(r'"accent":\{"editor":"color","default":"(#[0-9A-Fa-f]{6})","options":\[([^\]]*)\]', BUILD)
    assert m, "could not read the accent property from prototype/build.py"
    options = re.findall(r"#[0-9A-Fa-f]{6}", m.group(2))
    assert T["accent"]["default"].upper() == m.group(1).upper()
    assert [o.upper() for o in T["accent"]["options"]] == [o.upper() for o in options]


def test_the_five_components_are_the_prototypes_macros_exactly():
    tree = ast.parse(BUILD)
    mac = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "MAC")
    macros = {k.value: v.value for k, v in zip(mac.keys, mac.values) if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)}
    for name, key in (("card", "CARD"), ("caption", "CAP"), ("button", "BTN"), ("primary", "PRI"), ("input", "INP")):
        assert T["components"][name] == macros[key], f"component {name} differs from MAC[{key!r}]"


def test_fonts_are_the_ones_the_prototype_loads_and_they_exist():
    faces = set(re.findall(r"url\(\./fonts/([\w.-]+\.woff2)\)", HEAD))
    assert faces == set(T["font"]["files"]), "the font files in tokens.json differ from the @font-face rules in the prototype"
    d = REPO / T["font"]["files_dir"]
    for f in T["font"]["files"]:
        assert (d / f).is_file(), f"missing font file {f}"
    for lic in ("LICENSE-public-sans.txt", "LICENSE-source-serif-4.txt", "LICENSE-jetbrains-mono.txt"):
        assert (d / lic).is_file(), f"missing {lic}"


def test_the_installer_puts_everything_where_tokens_css_looks_for_it(tmp_path):
    names = mt.install(T, str(tmp_path))
    assert (tmp_path / "tokens.css").is_file()
    for f in re.findall(r"url\(\./fonts/([\w.-]+\.woff2)\)", (tmp_path / "tokens.css").read_text(encoding="utf-8")):
        assert (tmp_path / "fonts" / f).is_file(), f
    assert any(n.startswith("LICENSE-") for n in names), "the font licences must travel with the fonts"


# ---- the sentences the JSON and the guide say about contrast are checked here, not trusted ----

def test_text_and_control_colours_meet_the_contrast_the_guide_claims():
    c = T["color"]
    white = c["surface"]["paper"]["value"]
    for k in ("ink", "strong", "body", "secondary", "muted", "slate"):
        assert contrast(c["text"][k]["value"], white) >= 4.5, f"text.{k} on white is {contrast(c['text'][k]['value'], white):.2f}"
    assert contrast(c["border"]["control"]["value"], white) >= 3.0, "the control edge must be 3:1 against white"
    for k, v in c["status"].items():
        assert contrast(v["text"], v["fill"]) >= 4.5, f"status.{k}: text on its fill is {contrast(v['text'], v['fill']):.2f}"
    assert contrast(c["text"]["on_dark"]["value"], c["surface"]["band"]["value"]) >= 4.5
    assert contrast(c["text"]["on_dark_2"]["value"], c["surface"]["band"]["value"]) >= 4.5


@pytest.mark.parametrize("accent", mt.load()["accent"]["options"])
def test_white_on_every_accent_option_is_readable(accent):
    assert contrast("#FFFFFF", accent) >= 4.5, f"{accent} with white text is {contrast('#FFFFFF', accent):.2f}"


def test_a_name_defined_twice_is_refused():
    t = json.loads(json.dumps(T))
    t["color"]["text"]["body"]["prototype_name"] = "--ink"          # two tokens now claim --ink
    with pytest.raises(SystemExit):
        mt.render(t)
