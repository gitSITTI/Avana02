"""The image-to-UI kit (design/ui_from_image) is checked here on pictures whose right answer is known, on the prototype's own screenshots, and against its own SKILL.md.

What this proves: the scripts find the colours and blocks that were drawn into synthetic pictures, find the prototype's own tokens in its own screenshots, refuse the mistakes
the component-spec checker exists to refuse, and the commands SKILL.md tells an agent to run exist with the flags it names.
What it does not prove: that an agent following SKILL.md builds a good screen. That has not been measured.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

np = pytest.importorskip("numpy")
PIL = pytest.importorskip("PIL")
from PIL import Image, ImageDraw  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
KIT = REPO / "design" / "ui_from_image"
SCRIPTS = KIT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
sys.path.insert(0, str(REPO / "reqin" / "src"))
import check_component_specs as ccs  # noqa: E402
import colour as C  # noqa: E402
import conform as cf  # noqa: E402
import frames as F  # noqa: E402
import palette_from_image as P  # noqa: E402

SHOTS = REPO / "docs" / "images" / "prototype"
TOKENS_CSS = REPO / "design" / "tokens.css"


# ---------------------------------------------------------------- colour arithmetic

def test_colour_arithmetic_on_known_values():
    assert C.delta_e("#FFFFFF", "#FFFFFF") == 0
    assert C.contrast("#000000", "#FFFFFF") == pytest.approx(21.0, abs=0.01)
    assert C.delta_e("#FFFFFF", "#000000") > 90
    assert C.parse_css("rgb(26, 77, 181)") == ("#1A4DB5", 1.0)
    assert C.parse_css("rgba(0, 0, 0, 0.08)") == ("#000000", 0.08)
    assert C.parse_css("color(srgb 1 0 0 / 50%)") == ("#FF0000", 0.5)
    assert C.parse_css("linear-gradient(red, blue)") is None
    assert C.is_neutral("#54626F") and not C.is_neutral("#FDE3E0")        # a blue-grey is neutral; a pale red is a tint
    assert C.status_group("#FDE3E0") == "danger" and C.status_group("#E1F2E7") == "ok"


# ---------------------------------------------------------------- the palette, on a picture with known colours

def words(d, x: int, y: int, width: int, height: int, fill: str) -> None:
    """Something that looks like a line of text to a block cutter: short runs with gaps, never one long straight edge."""
    x1, step = x + width, 0
    while x < x1:
        w = (14, 22, 9, 30, 17)[step % 5]
        d.rectangle([x, y, min(x + w, x1), y + height], fill=fill)
        x += w + 5
        step += 1


def synthetic_page(path: Path) -> dict:
    """800 x 600: a light page, two white cards and a tall panel with a 1 px border, a dark band, a blue button, a red tint 'danger' chip, lines of word-like text."""
    page, card, border, dark, blue, text, red = "#F3F5F8", "#FFFFFF", "#D8DFE6", "#15202B", "#1A4DB5", "#1B2733", "#FDE3E0"
    im = Image.new("RGB", (800, 600), page)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 799, 60], fill=dark)
    words(d, 40, 22, 160, 16, "#FFFFFF")                              # a white title in the dark band
    for x0, y0, x1, y1 in ((40, 100, 400, 280), (40, 320, 400, 560), (440, 100, 760, 560)):
        d.rounded_rectangle([x0, y0, x1, y1], radius=12, fill=card, outline=border, width=1)
    words(d, 60, 120, 160, 14, text)                                 # a title line
    for y in (160, 182):
        words(d, 60, y, 280, 9, text)                                # two body lines, 12 px apart: one block at the default gap of 12 (10 once the marks' margins are taken)
    d.rounded_rectangle([60, 220, 170, 256], radius=8, fill=blue)    # the button
    words(d, 80, 234, 70, 8, "#FFFFFF")
    d.rounded_rectangle([60, 350, 180, 374], radius=12, fill=red)    # the chip
    words(d, 70, 358, 100, 8, "#7A1510")
    words(d, 460, 120, 200, 14, text)                                # two blocks of text in the tall panel, far apart
    words(d, 460, 300, 240, 14, text)
    im.save(path)
    return {"cards": [(40, 100, 360, 180), (40, 320, 360, 240), (440, 100, 320, 460)], "button": (60, 220, 110, 36), "colours": {"page": page, "card": card, "dark": dark, "blue": blue, "red": red}}


@pytest.fixture(scope="module")
def synth(tmp_path_factory):
    p = tmp_path_factory.mktemp("synth") / "page.png"
    return p, synthetic_page(p)


def test_the_palette_recovers_every_colour_that_was_drawn(synth):
    path, truth = synth
    pal = P.palette(str(path))
    got = {e["hex"]: e for e in pal["colours"]}
    for name, hx in truth["colours"].items():
        assert hx.upper() in got, f"{name} {hx} was drawn but not found; found {sorted(got)}"
    # the cards cover more of this picture than the page does, so white is the colour with the largest share, and that is what 'background' means
    assert pal["colours"][0]["hex"] == truth["colours"]["card"].upper() and pal["colours"][0]["role_hint"] == "background"
    assert got[truth["colours"]["page"].upper()]["role_hint"] == "surface"
    assert got[truth["colours"]["blue"].upper()]["role_hint"] == "accent"
    assert got[truth["colours"]["red"].upper()]["role_hint"] == "danger-fill"
    assert got[truth["colours"]["dark"].upper()]["role_hint"] == "surface"          # a dark BAND is a surface, not text: it is flat area


def test_anti_aliasing_noise_is_merged_into_the_colour_it_surrounds(tmp_path):
    rng = np.random.default_rng(1)
    a = np.zeros((200, 200, 3), dtype=np.uint8)
    a[:] = (26, 77, 181)
    a = np.clip(a.astype(int) + rng.integers(-2, 3, a.shape), 0, 255).astype(np.uint8)     # +-2 per channel, like compression
    Image.fromarray(a).save(tmp_path / "noise.png")
    pal = P.palette(str(tmp_path / "noise.png"))
    assert len(pal["colours"]) == 1, [e["hex"] for e in pal["colours"]]
    assert C.delta_e(pal["colours"][0]["hex"], "#1A4DB5") < 1.5


def test_a_transparent_png_is_read_over_white(tmp_path):
    im = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    im.save(tmp_path / "t.png")
    assert P.palette(str(tmp_path / "t.png"))["colours"][0]["hex"] == "#FFFFFF"


# ---------------------------------------------------------------- the block cutter

def inside(box, outer, slack=5):
    x, y, w, h = box
    ox, oy, ow, oh = outer
    return x >= ox - slack and y >= oy - slack and x + w <= ox + ow + slack and y + h <= oy + oh + slack


def test_blocks_respect_the_borders_of_panels(synth):
    path, truth = synth
    nodes = F.detect_tree(F._open(str(path)))
    leaves = [n for n in nodes if n["leaf"]]
    assert len(leaves) >= 7, f"only {len(leaves)} leaves found"
    for n in leaves:
        x, y, w, h = n["box"]
        if y < 70:                                    # the dark band across the top
            continue
        assert any(inside(n["box"], c) for c in truth["cards"]), f"leaf {n['box']} straddles a card edge"
    for c in truth["cards"]:                          # each card is a node of its own
        assert any(n["box"][0] >= c[0] - 5 and abs(n["box"][0] - c[0]) <= 5 and abs(n["box"][2] - c[2]) <= 8 and abs(n["box"][1] - c[1]) <= 5 for n in nodes), f"card {c} not found as a block"


def test_the_button_is_a_block_of_its_own_and_its_two_body_lines_are_one(synth):
    path, truth = synth
    leaves = [tuple(n["box"]) for n in F.detect_tree(F._open(str(path))) if n["leaf"]]
    bx, by, bw, bh = truth["button"]
    assert any(abs(x - bx) <= 4 and abs(y - by) <= 4 and abs(w - bw) <= 8 and abs(h - bh) <= 8 for x, y, w, h in leaves), f"no leaf matches the button {truth['button']}: {leaves}"
    body = [b for b in leaves if 150 <= b[1] <= 180 and b[0] <= 70]
    assert len(body) == 1 and body[0][3] <= 40, f"two lines 12 px apart should stay one block: {body}"


def test_a_smaller_gap_splits_what_the_default_keeps_together(synth):
    path, _ = synth
    im = F._open(str(path))
    region = (55, 150, 290, 50)
    assert len([n for n in F.detect_tree(im, region) if n["leaf"]]) == 1
    assert len([n for n in F.detect_tree(im, region, min_gap=3) if n["leaf"]]) == 2      # the lines are 12 px apart: 10 once each side's margin is taken


def test_a_tall_letter_stem_is_not_mistaken_for_a_border(tmp_path):
    """A heading whose letters have strokes 22 px tall in a band 24 px tall: the strokes cross 90% of the band, but a border is a long line, and this is not one."""
    im = Image.new("RGB", (600, 60), "white")
    d = ImageDraw.Draw(im)
    for x in range(20, 400, 14):
        d.rectangle([x, 18, x + 3, 40], fill="#1B2733")
    im.save(tmp_path / "stems.png")
    leaves = [n for n in F.detect_tree(F._open(str(tmp_path / "stems.png"))) if n["leaf"]]
    assert len(leaves) == 1 and leaves[0]["box"][2] > 360, "the strokes were cut apart as if they were borders"


def test_a_strip_between_two_panels_is_not_a_block(synth):
    path, _ = synth
    nodes = F.detect_tree(F._open(str(path)))
    assert not any(n["box"][3] < 40 and n["box"][2] > 600 and n["box"][1] > 60 for n in nodes), "a thin full-width strip between panels was reported as a block"


def test_detect_on_the_prototype_home_screen_finds_what_a_person_would():
    shot = SHOTS / "03_home.png"
    if not shot.is_file():
        pytest.skip("prototype screenshot not present")
    nodes = F.detect_tree(F._open(str(shot)))
    leaves = [n for n in nodes if n["leaf"]]
    assert 30 <= len(leaves) <= 140, f"{len(leaves)} leaves: a page like this should come out in dozens, not 1 and not hundreds"
    assert not any(n["box"][2] > 1300 and n["box"][3] > 1500 for n in leaves), "the whole page came back as one block"

    def has(box, slack=8):
        return any(all(abs(a - b) <= slack for a, b in zip(n["box"], box)) for n in nodes)

    assert has([280, 166, 1136, 117], 12), "the dark security band is not a block"
    assert has([11, 0, 244, 1796], 12) or any(n["box"][2] < 260 and n["box"][3] > 1700 for n in nodes), "the side bar is not a block"
    pt = (350, 427)                                   # the primary button 'Review the next cluster'
    hit = [n for n in leaves if n["box"][0] <= pt[0] <= n["box"][0] + n["box"][2] and n["box"][1] <= pt[1] <= n["box"][1] + n["box"][3]]
    assert hit and hit[0]["box"][2] < 500 and hit[0]["box"][3] < 70, f"the button's block is {hit and hit[0]['box']}"


def test_crop_refuses_a_box_outside_the_picture_and_records_a_hash(synth, tmp_path):
    path, _ = synth
    with pytest.raises(SystemExit):
        F.crop(str(path), str(tmp_path), {"x": (700, 500, 200, 200)})
    fr = F.crop(str(path), str(tmp_path), {"button": (60, 220, 110, 36)})
    assert Path(tmp_path, "button.png").is_file() and len(fr[0]["sha256"]) == 64
    assert Image.open(tmp_path / "button.png").size == (110, 36)
    meta = json.loads((tmp_path / "frames.json").read_text(encoding="utf-8"))
    assert meta["format"] == "reqin-frames/1" and meta["frames"][0]["box"] == [60, 220, 110, 36]


def test_the_command_line_writes_the_overview_and_the_tree(synth, tmp_path):
    path, _ = synth
    r = subprocess.run([sys.executable, str(SCRIPTS / "frames.py"), "detect", str(path), str(tmp_path / "o")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "o" / "overview.png").is_file()
    tree = json.loads((tmp_path / "o" / "candidates.json").read_text(encoding="utf-8"))
    assert tree["format"] == "reqin-candidates/2" and tree["nodes"][0]["parent"] is None
    assert all(n["parent"] is None or n["parent"] < n["n"] for n in tree["nodes"])


# ---------------------------------------------------------------- conforming a picture's colours to a target's

def target_css(tmp_path, body: str) -> Path:
    p = tmp_path / "t.css"
    p.write_text(":root{" + body + "}", encoding="utf-8")
    return p


def palette_of(*rows) -> dict:
    return {"format": "reqin-palette/1", "image": "x.png", "colours": [{"hex": h, "share": s, "role_hint": r} for h, s, r in rows]}


def test_the_prototype_screenshot_conforms_to_the_prototype_tokens():
    shot = SHOTS / "03_home.png"
    if not shot.is_file():
        pytest.skip("prototype screenshot not present")
    res = cf.conform(P.palette(str(shot)), cf.load_target(str(TOKENS_CSS)))
    assert res["share_of_picture"]["use"] >= 0.95, res["share_of_picture"]
    accent = next(c for c in res["colours"] if c["role_hint"] == "accent")
    assert accent["match"]["hex"] == "#1A4DB5" and accent["replace_with"] == "var(--accent)"


def test_a_colour_the_target_does_not_have_is_none_and_is_not_forced(tmp_path):
    t = cf.load_target(str(target_css(tmp_path, "--accent:#1A4DB5;--ink:#1B2733;--paper:#FFFFFF;")))
    res = cf.conform(palette_of(("#E0218A", 0.02, "accent")), t)
    c = res["colours"][0]
    assert c["decision"] == "none" and c["match"] is None and c["replace_with"] is None and c["nearest"]


def test_a_close_colour_is_used_a_middling_one_is_reviewed(tmp_path):
    t = cf.load_target(str(target_css(tmp_path, "--accent:#1A4DB5;--paper:#FFFFFF;")))
    close = C.rgb_to_hex(28, 78, 181)
    mid = "#3A6BCB"                                      # visibly lighter: between 6 and 12 steps away
    assert 6 < C.delta_e(mid, "#1A4DB5") <= 12, C.delta_e(mid, "#1A4DB5")
    res = cf.conform(palette_of((close, 0.1, "accent"), (mid, 0.1, "accent")), t)
    assert [c["decision"] for c in res["colours"]] == ["use", "review"]
    assert res["colours"][0]["replace_with"] == "var(--accent)"


def test_a_colour_is_not_matched_to_a_token_that_does_another_job(tmp_path):
    t = cf.load_target(str(target_css(tmp_path, "--surface-sunken:#F4F6F8;--text-muted:#4F5B66;--line:#D8DFE6;")))
    # a pale grey TEXT colour next to the sunken surface token: close in colour, wrong job
    res = cf.conform(palette_of(("#F5F7F9", 0.02, "text")), t)
    c = res["colours"][0]
    assert c["match"] is None or "--surface-sunken" not in c["match"]["names"]
    assert c.get("wrong_job", {}).get("names") == ["--surface-sunken"]


def test_strict_mode_is_for_pages_you_wrote(tmp_path):
    t = cf.load_target(str(target_css(tmp_path, "--accent:#1A4DB5;")))
    off = "#2459BF"                                     # about 3 steps from the accent
    assert 2.5 < C.delta_e(off, "#1A4DB5") < 6
    assert cf.conform(palette_of((off, 0.1, "accent")), t)["colours"][0]["decision"] == "use"
    assert cf.conform(palette_of((off, 0.1, "accent")), t, cf.STRICT_USE, cf.STRICT_REVIEW)["colours"][0]["decision"] == "review"


def test_conform_refuses_a_file_that_is_not_a_palette(tmp_path):
    with pytest.raises(SystemExit):
        cf.conform({"format": "something-else"}, [])


# ---------------------------------------------------------------- the component spec checker

@pytest.fixture(scope="module")
def real_paths(tmp_path_factory):
    pytest.importorskip("yaml", reason="reqin needs pyyaml; the guard job installs only pytest, pillow and numpy, so these tests run where reqin is installed")
    import datapaths
    found = datapaths.collect(datapaths.generate(tmp_path_factory.mktemp("paths")))
    return {k: sorted(v) for k, v in found.items()}


@pytest.fixture(scope="module")
def tokens():
    return ccs.token_names(str(TOKENS_CSS))


def good_spec():
    return json.loads((KIT / "examples" / "home_components.json").read_text(encoding="utf-8"))


def errors_of(spec, tokens, paths=None):
    return ccs.check(spec, tokens, paths)["errors"]


def test_the_shipped_example_passes_against_real_tokens_and_real_paths(tokens, real_paths):
    rep = ccs.check(good_spec(), tokens, real_paths)
    assert rep["ok"], rep["errors"]
    assert rep["paths_checked"] is True
    assert any("STATIC" in w for w in rep["warnings"]), "STATIC slots must be listed for a person to look at"


def test_a_literal_colour_or_size_where_a_token_belongs_is_an_error(tokens):
    s = good_spec()
    s["components"][0]["style"]["background"] = "#1A4DB5"
    assert any("literal" in e and "#1A4DB5" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["style"]["radius"] = "8px"
    assert any("literal" in e and "8px" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["style"]["padding"] = "--space-10 14px"
    assert any("14px" in e for e in errors_of(s, tokens))


def test_a_token_that_does_not_exist_is_an_error(tokens):
    s = good_spec()
    s["components"][0]["style"]["color"] = "--text-on-light"
    assert any("--text-on-light" in e for e in errors_of(s, tokens))


def test_a_new_token_needs_a_reason_and_may_not_redefine_an_existing_one(tokens):
    s = good_spec()
    s["new_tokens"] = [{"name": "--status-new", "value": "#6B3D00", "reason": ""}]
    assert any("no reason" in e for e in errors_of(s, tokens))
    s["new_tokens"] = [{"name": "--accent", "value": "#000000", "reason": "x"}]
    assert any("already exists" in e for e in errors_of(s, tokens))
    s["new_tokens"] = [{"name": "--status-new", "value": "#6B3D00", "reason": "the picture has a status the target lacks"}]
    s["components"][3]["style"]["color"] = "--status-new"
    rep = ccs.check(s, tokens)
    assert rep["ok"] and rep["new_tokens"] == ["--status-new"]
    s["components"][3]["style"]["color"] = "--ok-text"
    assert any("no component uses it" in w for w in ccs.check(s, tokens)["warnings"])


def test_a_field_path_that_does_not_occur_in_real_output_is_an_error(tokens, real_paths):
    s = good_spec()
    s["components"][2]["data"]["count"] = "CMP.counts.clusterz"
    assert any("CMP.counts.clusterz" in e and "does not occur" in e for e in errors_of(s, tokens, real_paths))
    s["components"][2]["data"]["count"] = "clusters"
    assert any("is not STATIC, NONE or a field path" in e for e in errors_of(s, tokens, real_paths))


def test_without_a_paths_file_the_report_says_existence_was_not_checked(tokens):
    rep = ccs.check(good_spec(), tokens)
    assert rep["paths_checked"] is False and any("not checked" in w for w in rep["warnings"])


def test_a_component_that_does_not_say_where_its_content_comes_from_is_an_error(tokens):
    s = good_spec()
    del s["components"][0]["data"]
    assert any("data is missing" in e for e in errors_of(s, tokens))


def test_names_kinds_states_and_frames_are_checked(tokens):
    s = good_spec()
    s["components"][1]["name"] = s["components"][0]["name"]
    assert any("used twice" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["kind"] = "widget"
    assert any("kind 'widget'" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["states"] = ["hover"]
    assert any("'default'" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["state_style"] = {"active": {"background": "--accent"}}
    assert any("state_style has 'active'" in e for e in errors_of(s, tokens))
    s = good_spec()
    s["components"][0]["frame"]["box"] = [10, 10, 0, 40]
    assert any("frame.box" in e for e in errors_of(s, tokens))


def test_weights_and_unitless_line_heights_are_not_literals(tokens):
    s = good_spec()
    s["components"][0]["style"].update({"font-weight": "600", "line-height": "1.5"})
    assert errors_of(s, tokens) == []
    s["components"][0]["style"]["font-weight"] = "650"
    assert errors_of(s, tokens)


def test_the_schema_accepts_the_example_and_refuses_a_component_without_data():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((KIT / "component.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(good_spec(), schema)
    bad = good_spec()
    del bad["components"][0]["data"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)
    bad = good_spec()
    bad["components"][0]["data"]["label"] = "the cluster count"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_the_example_frames_lie_inside_the_screenshot_they_name():
    spec = good_spec()
    for c in spec["components"]:
        fr = c["frame"]
        shot = SHOTS / fr["image"]
        if not shot.is_file():
            pytest.skip("prototype screenshot not present")
        w, h = Image.open(shot).size
        x, y, bw, bh = fr["box"]
        assert x + bw <= w and y + bh <= h, f"{c['name']}: {fr['box']} is outside {fr['image']} ({w} x {h})"


# ---------------------------------------------------------------- SKILL.md says only what is true

SKILL = (KIT / "SKILL.md").read_text(encoding="utf-8")


def test_the_skill_has_the_front_matter_an_agent_runtime_reads():
    m = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n", SKILL)
    assert m, "SKILL.md must start with a name and a description between --- lines"
    assert m.group(1) == "ui-from-image" and 20 < len(m.group(2)) <= 1024


def test_every_command_the_skill_tells_an_agent_to_run_exists_with_those_flags():
    lines = [l for l in SKILL.splitlines() if "python3 scripts/" in l or "python3 tools/" in l]
    assert len(lines) >= 9, "the skill should show its commands"
    for line in lines:
        for cmd in re.findall(r"`(python3 (?:scripts|tools/gui_checks)/\S+\.py[^`]*)`", line):
            parts = cmd.split()
            script = REPO / "design" / "ui_from_image" / parts[1] if parts[1].startswith("scripts/") else REPO / parts[1]
            assert script.is_file(), f"{parts[1]} does not exist"
            sub = [parts[2]] if script.name == "frames.py" and len(parts) > 2 and not parts[2].startswith("-") else []
            helped = subprocess.run([sys.executable, str(script), *sub, "--help"], capture_output=True, text=True)
            if helped.returncode != 0 and "needs Playwright" in helped.stderr:
                continue    # the script exists (checked above); its flags are checked wherever Playwright is installed (the guard job has none)
            assert helped.returncode == 0, helped.stderr[-300:]
            for flag in re.findall(r"(?<![\w-])(--[a-z][a-z-]+)", cmd):
                assert flag in helped.stdout, f"{cmd!r}: {flag} is not a flag of {script.name} {' '.join(sub)}"


def test_every_file_the_skill_names_exists():
    for rel in re.findall(r"`((?:scripts|examples)/[\w./-]+|component\.schema\.json|requirements\.txt)`", SKILL):
        assert (KIT / rel).exists(), f"SKILL.md names {rel}, which is not in design/ui_from_image"
    for rel in re.findall(r"`((?:docs|reqin|design)/[\w./-]+\.(?:md|css|json))`", SKILL):
        assert (REPO / rel).exists(), f"SKILL.md names {rel}, which does not exist"


def test_the_skill_names_no_product():
    low = SKILL.lower()
    for word in ("gemini", "gpt", "openai", "chatgpt", "copilot", "excalidraw", "figma"):
        assert word not in low, f"SKILL.md names {word}: the repo's documents name no product"
