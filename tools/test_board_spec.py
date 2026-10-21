"""The JSON board format (excalidraw_generator/board_spec.py): the way an agent that cannot run code, or that writes JSON more reliably than Python, makes the repository's Excalidraw boards.

What has to hold: the checker says every problem at once and each starts with the place it is; the JSON Schema and the Markdown that is pasted into prompts are made from the same table as the
checker (and the committed copy is current); a spec always compiles to the same bytes; a spec that is accepted never produces a file that fails validate.py; nothing a model can type makes the
program crash; and the layout warnings that stand in for "look at the picture" fire when they should.
"""
from __future__ import annotations

import copy
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
GEN = REPO / "excalidraw_generator"
sys.path.insert(0, str(GEN))

import board_spec as bs  # noqa: E402
from validate import check as validate_file  # noqa: E402

DEL = object()


def base() -> dict:
    return copy.deepcopy(bs.EXAMPLE)


def put(spec: dict, path: tuple, value) -> dict:
    """A copy of spec with the value at path replaced (or the key removed when value is DEL)."""
    out = copy.deepcopy(spec)
    node = out
    for k in path[:-1]:
        node = node[k]
    if value is DEL:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return out


def one(items: list, **frame) -> dict:
    return {"format": bs.FORMAT, "title": "T", "frames": [{"name": "1.1 · T", **frame, "items": items}]}


def build(spec: dict, tmp_path: Path, name: str = "o.excalidraw"):
    d, warns = bs.compile_spec(spec)
    p = tmp_path / name
    d.save(str(p))
    return p, warns


# ------------------------------------------------------------------------------------------------- the example and the committed files

def test_the_example_is_accepted_and_builds_a_valid_file(tmp_path):
    assert bs.check_spec(bs.EXAMPLE) == []
    p, warns = build(bs.EXAMPLE, tmp_path)
    assert warns == [], warns
    v = validate_file(str(p), verbose=False)
    assert v["ok"] and v["frames"] == 2 and v["dup"] == v["dangling"] == v["order"] == v["outside"] == 0


def test_a_rebuild_is_byte_identical_and_the_seed_matters(tmp_path):
    a, _ = build(bs.EXAMPLE, tmp_path, "a.excalidraw")
    b, _ = build(bs.EXAMPLE, tmp_path, "b.excalidraw")
    assert a.read_bytes() == b.read_bytes()
    c, _ = build(put(bs.EXAMPLE, ("seed",), 7), tmp_path, "c.excalidraw")
    assert c.read_bytes() != a.read_bytes()


def test_with_no_seed_one_is_made_from_the_title_and_is_stable(tmp_path):
    spec = put(bs.EXAMPLE, ("seed",), DEL)
    a, _ = build(spec, tmp_path, "a.excalidraw")
    b, _ = build(spec, tmp_path, "b.excalidraw")
    other, _ = build(put(spec, ("title",), "98 · Another"), tmp_path, "c.excalidraw")
    assert a.read_bytes() == b.read_bytes() != other.read_bytes()
    seeds = lambda p: [e["seed"] for e in json.loads(p.read_text(encoding="utf-8"))["elements"]]     # noqa: E731
    assert seeds(a) != seeds(other), "two different titles must not give every element the same hand-drawn jitter"


def test_the_committed_schema_is_what_the_program_makes():
    committed = json.loads((GEN / "board_spec.schema.json").read_text(encoding="utf-8"))
    assert committed == bs.schema(), "board_spec.schema.json is stale; run: cd excalidraw_generator && python3 board_spec.py schema board_spec.schema.json"


def test_the_committed_example_is_the_programs_example():
    committed = json.loads((GEN / "examples" / "board_spec_example.json").read_text(encoding="utf-8"))
    assert committed == bs.EXAMPLE, "examples/board_spec_example.json is stale; run: cd excalidraw_generator && python3 board_spec.py example > examples/board_spec_example.json"


def test_the_schema_is_a_valid_json_schema_and_accepts_the_example():
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.Draft202012Validator.check_schema(bs.schema())
    jsonschema.validate(bs.EXAMPLE, bs.schema())


def test_the_description_names_every_type_and_every_field():
    text = bs.describe()
    for t, spec in bs.ITEMS.items():
        assert f"### `{t}`" in text
        assert spec["doc"] in text
        for f in spec["fields"]:
            assert f"`{f[0]}`" in text, (t, f[0])
    for f in bs.FRAME_FIELDS + bs.COMMON:
        assert f"`{f[0]}`" in text
    for tone in bs.TONES:
        assert tone in text
    for entry in bs.SIDEBAR:
        assert entry in text, "an agent cannot guess the sidebar entries"
    for rule in bs.LAYOUT_RULES:
        assert rule in text, "the layout rules are what lets an agent place things without seeing the picture"


def test_every_type_in_the_table_can_be_drawn(tmp_path):
    """One spec with one of every type; it must compile, and a type with no drawing code would raise."""
    items = [
        {"type": "heading", "text": "H"}, {"type": "text", "text": "words", "w": 300}, {"type": "caps", "text": "CAPS"},
        {"type": "card", "w": 300, "items": [{"type": "text", "text": "inside", "w": 250}]},
        {"type": "button", "label": "Go", "primary": True}, {"type": "chip", "label": "Open", "tone": "amber"}, {"type": "bar", "w": 200, "frac": 0.4},
        {"type": "placeholder", "w": 200}, {"type": "mark", "kind": "ai", "label": "AI"},
        {"type": "table", "widths": [100, 100], "head": ["A", "B"], "rows": [["1", {"text": "2", "tone": "red"}]]},
        {"type": "checklist", "w": 300, "items": [{"state": "Done", "text": "x"}]}, {"type": "kv", "key": "k", "value": "v"},
        {"type": "box", "id": "a", "label": "A", "w": 100, "h": 40, "x": 400, "y": 20}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "x": 650, "y": 20, "shape": "ellipse"},
        {"type": "arrow", "from": "a", "to": "b"}, {"type": "callout", "n": 1, "x": 500, "y": 300}]
    assert {i["type"] for i in items} == set(bs.ITEMS)
    p, warns = build(one(items, width=1100, notes=["one"]), tmp_path)
    assert validate_file(str(p), verbose=False)["ok"]


# -------------------------------------------------------------------------------------------------------- what is refused, and how it is said

def bs_nest(n: int) -> dict:
    it: dict = {"type": "caps", "text": "A"}
    for _ in range(n):
        it = {"type": "card", "items": [it]}
    return it


BAD = [
    # (name, spec, a fragment the message must contain, a JSON Schema can say no too)
    ("not an object", [], "must be a JSON object", True),
    ("no format", put(base(), ("format",), DEL), "the board: missing 'format'", True),
    ("another format", put(base(), ("format",), "reqin-board/2"), "format: is \"reqin-board/2\"", True),
    ("an unknown board field", put(base(), ("colour",), "red"), "no field 'colour'", True),
    ("no frames", put(base(), ("frames",), []), "needs at least one frame", True),
    ("twenty-one frames", put(base(), ("frames",), [base()["frames"][1]] * 21), "at most 20", True),
    ("a frame with no name", put(base(), ("frames", 0, "name"), DEL), "frames[0]: missing 'name'", True),
    ("a frame that is not an object", put(base(), ("frames", 0), "x"), "a frame is an object", True),
    ("an unknown frame field", put(base(), ("frames", 0, "background"), "#fff"), "no field 'background'", True),
    ("a frame too narrow", put(base(), ("frames", 0, "width"), 100), "frames[0].width", True),
    ("a width that is true", put(base(), ("frames", 0, "width"), True), "whole number", True),
    ("an unknown chrome", put(base(), ("frames", 0, "chrome"), "sidebar"), "frames[0].chrome", True),
    ("an unknown sidebar entry", put(base(), ("frames", 0, "active"), "Settings"), "frames[0].active", True),
    ("active without the app chrome", put(base(), ("frames", 1, "active"), "Overview"), "only mean something", False),
    ("an item that is a string", put(base(), ("frames", 0, "items", 0), "heading"), "an item is an object", True),
    ("an unknown type", put(base(), ("frames", 0, "items", 0, "type"), "paragraph"), "\"paragraph\" is not an item type", True),
    ("a missing type", put(base(), ("frames", 0, "items", 0, "type"), DEL), "is not an item type", True),
    ("a colour typed in", put(base(), ("frames", 0, "items", 0, "color"), "#ff0000"), "no field 'color'", True),
    ("empty heading", put(base(), ("frames", 0, "items", 0, "text"), "  "), "items[0].text", True),
    ("a size that is text", put(base(), ("frames", 0, "items", 0, "size"), "big"), "items[0].size: must be a whole number", True),
    ("a size out of range", put(base(), ("frames", 0, "items", 0, "size"), 400), "from 12 to 48", True),
    ("a fraction where a whole number goes", put(base(), ("frames", 0, "items", 1, "w"), 300.5), "whole number", True),
    ("a missing required field", put(base(), ("frames", 0, "items", 2, "head"), DEL), "missing 'head'", True),
    ("an error inside a card", put(base(), ("frames", 0, "items", 1, "items", 0, "text"), ""), "frames[0].items[1].items[0].text", True),
    ("a card's items that are not a list", put(base(), ("frames", 0, "items", 1, "items"), "x"), "items[1].items: must be a list", True),
    ("an unknown tone", put(base(), ("frames", 0, "items", 1, "tone"), "pink"), "pink", True),
    ("a bar over full", one([{"type": "bar", "w": 100, "frac": 1.5}]), "items[0].frac", True),
    ("an unknown mark", one([{"type": "mark", "kind": "robot"}]), "items[0].kind", True),
    ("no head", put(base(), ("frames", 0, "items", 2, "head"), []), "non-empty list", True),
    ("widths that are text", put(base(), ("frames", 0, "items", 2, "widths"), ["a", "b", "c"]), "widths[0]", True),
    ("a number as a cell", put(base(), ("frames", 0, "items", 2, "rows"), [[1, 2, 3]]), "rows[0][0]: a cell is text", True),
    ("a cell with an extra key", put(base(), ("frames", 0, "items", 2, "rows"), [["a", {"text": "b", "color": "red"}, "c"]]), "rows[0][1]: a coloured cell", True),
    ("a row that is not a list", put(base(), ("frames", 0, "items", 2, "rows"), ["a"]), "rows[0]: must be a list of cells", True),
    ("an unknown state", one([{"type": "checklist", "w": 300, "items": [{"state": "Maybe", "text": "x"}]}]), "items[0].items[0]: a line is", True),
    ("a checklist line with no text", one([{"type": "checklist", "w": 300, "items": [{"state": "Pass"}]}]), "a line is", True),
    ("a kv with no value", one([{"type": "kv", "key": "k"}]), "missing 'value'", True),
    ("an id that starts with a digit", one([{"type": "box", "id": "1a", "label": "x", "w": 50, "h": 40}]), "must be an id", True),
    ("an arrow with no end", one([{"type": "arrow", "from": "a"}]), "missing 'to'", True),
    ("an arrow with a position", one([{"type": "arrow", "from": "a", "to": "b", "x": 5}]), "arrow has no field 'x'", True),
    ("a callout item with a callout", one([{"type": "callout", "n": 1, "callout": 2}]), "callout has no field 'callout'", True),
    ("a callout number of zero", one([{"type": "callout", "n": 0}]), "items[0].n", True),
    ("y as a word", put(base(), ("frames", 0, "items", 0, "y"), "below"), "or the word \"same\"", True),
    ("y as a fraction", put(base(), ("frames", 0, "items", 0, "y"), 10.5), "whole number", True),
    ("a callout number of zero on an item", put(base(), ("frames", 0, "items", 0, "callout"), 0), "items[0].callout", True),
    ("an empty note", put(base(), ("frames", 0, "notes"), ["fine", ""]), "notes[1]", True),
    ("a note that is far too long", put(base(), ("frames", 0, "notes"), ["x" * 401]), "notes[0]", True),
    ("cards nested too deep", one([{"type": "caps", "text": "A"}]) | {"frames": [{"name": "1.1", "items": [bs_nest(8)]}]}, "nested more than 5 deep", False),
    ("an id with a space in it", one([{"type": "box", "id": "a b", "label": "x", "w": 50, "h": 40}]), "must be an id", True),
    ("an id that is too long", one([{"type": "box", "id": "a" * 41, "label": "x", "w": 50, "h": 40}]), "must be an id", True),
    ("y far below the frame's limit", put(base(), ("frames", 0, "items", 0, "y"), 7000), "from -200 to 6000", True),
    ("twenty-one notes", put(base(), ("frames", 0, "notes"), ["n"] * 21), "at most 20", True),
    ("sixty-one rows", one([{"type": "table", "widths": [100], "head": ["h"], "rows": [["c"]] * 61}]), "at most 60", True),
    ("thirty-one checklist lines", one([{"type": "checklist", "w": 300, "items": [{"state": "Pass", "text": "x"}] * 31}]), "at most 30", True),
    ("nine columns", one([{"type": "table", "widths": [40] * 9, "head": ["h"] * 9, "rows": [["c"] * 9]}]), "at most 8", True),
    ("a table cell over 300 characters", one([{"type": "table", "widths": [100], "head": ["h"], "rows": [["c" * 301]]}]), "at most 300", True),
    ("a table cell with a colour that is not in the palette", one([{"type": "table", "widths": [100], "head": ["h"], "rows": [[{"text": "c", "tone": "pink"}]]}]), "a coloured cell is", True),
    ("a checklist line with an extra key", one([{"type": "checklist", "w": 300, "items": [{"state": "Pass", "text": "x", "colour": "red"}]}]), "a line is", True),
    ("a bar whose fraction is true", one([{"type": "bar", "w": 100, "frac": True}]), "items[0].frac", True),
    ("a float for a number of rows", one([{"type": "placeholder", "w": 100, "lines": 2.5}]), "whole number", True),
    ("a width of zero", one([{"type": "bar", "w": 0, "frac": 0.5}]), "from 20 to 2000", True),
    ("three hundred and one items", one([{"type": "caps", "text": "A"}] * 301), "at most 300", True),
]


@pytest.mark.parametrize("name,spec,fragment,schema_too", BAD, ids=[b[0] for b in BAD])
def test_a_bad_spec_is_refused_with_the_place_and_the_reason(name, spec, fragment, schema_too):
    errs = bs.check_spec(spec)
    assert errs, name
    assert any(fragment in e for e in errs), (fragment, errs)
    for e in errs:
        assert re.match(r"(format|title|seed|frames(\[\d+\])?|the board|the spec)\b", e), f"an error without its place: {e}"
    with pytest.raises(bs.SpecError):
        bs.compile_spec(spec)
    if schema_too:
        jsonschema = pytest.importorskip("jsonschema")
        assert not jsonschema.Draft202012Validator(bs.schema()).is_valid(spec), f"the JSON Schema accepts {name!r}, the checker does not"


def test_every_problem_is_reported_at_once_not_one_per_try():
    spec = base()
    spec["frames"][0]["items"][0]["size"] = "big"
    spec["frames"][0]["items"][1]["tone"] = "pink"
    spec["frames"][1]["name"] = ""
    spec["colour"] = 1
    errs = bs.check_spec(spec)
    assert len(errs) >= 4, errs


GOOD = [
    ("the least", one([{"type": "caps", "text": "A"}])),
    ("a coordinate that is zero", one([{"type": "caps", "text": "A", "x": 0, "y": 0}])),
    ("level with the first item", one([{"type": "caps", "text": "A", "y": "same"}])),
    ("a negative x", one([{"type": "caps", "text": "A", "x": -20}])),
    ("a bar that is empty", one([{"type": "bar", "w": 100, "frac": 0}])),
    ("a bar that is full", one([{"type": "bar", "w": 100, "frac": 1}])),
    ("a bar that is half, as a whole-number float", one([{"type": "bar", "w": 100, "frac": 0.5}])),
    ("a card with nothing in it", one([{"type": "card"}])),
    ("a non-ASCII title and text", one([{"type": "text", "text": "Fünf Sekunden · 5 s · ≤ 10 ms · 日本語"}])),
    ("a frame with no notes", one([{"type": "caps", "text": "A"}], width=800)),
]


@pytest.mark.parametrize("name,spec", GOOD, ids=[g[0] for g in GOOD])
def test_a_good_spec_is_accepted_by_the_checker_and_the_schema_and_builds(name, spec, tmp_path):
    assert bs.check_spec(spec) == [], name
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(spec, bs.schema())
    p, _ = build(spec, tmp_path)
    assert validate_file(str(p), verbose=False)["ok"]


def test_the_checker_and_the_schema_agree_on_a_thousand_mutated_specs():
    """Break the example at random (delete a key, put the wrong kind of value in). Where the schema can say, it must say what the checker says."""
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(bs.schema())
    rnd = random.Random(20261015)
    junk = [None, True, False, 0, -1, 1.5, "", " ", "x", "same", "Pass", "red", [], {}, [1], {"text": "a"}, 10**9, "y" * 700]
    differ = []
    for n in range(1000):
        spec = base()
        for _ in range(rnd.choice((1, 1, 2))):
            spots = []

            def walk(o, path):
                if isinstance(o, dict):
                    for k, v in o.items():
                        spots.append(path + (k,))
                        walk(v, path + (k,))
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        spots.append(path + (i,))
                        walk(v, path + (i,))
            walk(spec, ())
            where = rnd.choice(spots)
            node = spec
            for k in where[:-1]:
                node = node[k]
            if rnd.random() < 0.3 and isinstance(node, dict):
                del node[where[-1]]
            else:
                node[where[-1]] = rnd.choice(junk)
        mine = not bs.check_spec(spec)
        theirs = validator.is_valid(spec)
        if theirs and not mine:
            # the checker is allowed to be stricter only where the schema cannot say it
            errs = bs.check_spec(spec)
            if not all("only mean something" in e for e in errs):
                differ.append((n, errs[:2]))
        if mine and not theirs:
            differ.append((n, "the checker accepted what the schema refuses", [e.message for e in validator.iter_errors(spec)][:2]))
    assert not differ, differ[:5]


def test_five_levels_of_items_are_allowed_and_six_are_not():
    assert bs.check_spec(one([bs_nest(4)])) == []
    assert any("nested more than 5 deep" in e for e in bs.check_spec(one([bs_nest(5)])))


def test_a_board_nested_a_thousand_deep_is_refused_not_a_stack_overflow():
    deep = one([bs_nest(1000)])
    errs = bs.check_spec(deep)
    assert errs and "nested more than 5 deep" in errs[0]


def test_nothing_a_model_can_type_makes_the_program_crash():
    """Checker and compiler on 1500 random breakages: each ends in a clean answer (errors, or a Doc), never an exception."""
    rnd = random.Random(7)
    built = refused = 0
    junk = [None, True, 0, -5, 3.7, "", "x" * 50, "same", [], {}, [[]], [{}], {"type": "text"}, {"type": "card", "items": 5}, 10**12, -10**12, float("1e300")]
    for n in range(1500):
        spec = base()
        node = spec
        for _ in range(rnd.randint(0, 5)):
            keys = list(node) if isinstance(node, dict) else list(range(len(node))) if isinstance(node, list) else []
            if not keys:
                break
            k = rnd.choice(keys)
            if isinstance(node[k], (dict, list)) and rnd.random() < 0.8:
                node = node[k]
            else:
                node[k] = rnd.choice(junk)
                break
        else:
            if isinstance(node, dict) and node:
                node[rnd.choice(list(node))] = rnd.choice(junk)
        try:
            bs.compile_spec(spec)
            built += 1
        except bs.SpecError as e:
            assert e.errors, "an error with no message"
            refused += 1
        except Exception as e:     # noqa: BLE001
            pytest.fail(f"case {n}: {type(e).__name__}: {e}\n{json.dumps(spec)[:300]}")
    assert built > 100 and refused > 100, (built, refused)     # the breakages reach both outcomes, so neither is untested


# ------------------------------------------------------------------------------------------------------------ errors found while laying out

def test_a_table_whose_widths_do_not_match_its_head_is_an_error_naming_both_counts():
    spec = one([{"type": "table", "widths": [100, 100], "head": ["A", "B", "C"], "rows": [["1", "2", "3"]]}])
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec(spec)
    assert any("widths has 2 entries but head has 3" in m and m.startswith("frames[0].items[0]") for m in e.value.errors), e.value.errors


def test_a_row_with_the_wrong_number_of_cells_is_an_error_naming_the_row():
    spec = one([{"type": "table", "widths": [100, 100], "head": ["A", "B"], "rows": [["1", "2"], ["3"], ["4", "5", "6"]]}])
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec(spec)
    assert any(".rows[1]: has 1 cells but head has 2" in m for m in e.value.errors)
    assert any(".rows[2]: has 3 cells but head has 2" in m for m in e.value.errors)


def test_an_arrow_to_a_box_that_does_not_exist_names_the_boxes_that_do():
    spec = one([{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "arrow", "from": "a", "to": "nowhere"}])
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec(spec)
    assert any("items[1].to" in m and "'nowhere'" in m and "boxes are: a" in m for m in e.value.errors), e.value.errors


def test_the_same_box_id_twice_in_a_frame_is_an_error():
    spec = one([{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "a", "label": "B", "w": 100, "h": 40, "x": 200, "y": "same"}])
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec(spec)
    assert any("already used by frames[0].items[0]" in m for m in e.value.errors)


def test_the_same_box_id_in_two_frames_is_fine_because_arrows_stay_inside_a_frame(tmp_path):
    fr = {"name": "1.1 · A", "items": [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "x": 300, "y": "same"}, {"type": "arrow", "from": "a", "to": "b"}]}
    spec = {"format": bs.FORMAT, "title": "T", "frames": [fr, {**fr, "name": "1.2 · B"}]}
    p, _ = build(spec, tmp_path)
    assert validate_file(str(p), verbose=False)["ok"]


def test_an_arrow_in_one_frame_cannot_join_a_box_in_another():
    a = {"name": "1.1 · A", "items": [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}]}
    b = {"name": "1.2 · B", "items": [{"type": "box", "id": "b", "label": "B", "w": 100, "h": 40}, {"type": "arrow", "from": "a", "to": "b"}]}
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec({"format": bs.FORMAT, "title": "T", "frames": [a, b]})
    assert any("frames[1].items[1].from" in m for m in e.value.errors)


def test_errors_in_two_frames_are_both_reported():
    bad = {"type": "table", "widths": [100], "head": ["A", "B"], "rows": [["1", "2"]]}
    spec = {"format": bs.FORMAT, "title": "T", "frames": [{"name": "1.1", "items": [bad]}, {"name": "1.2", "items": [bad]}]}
    with pytest.raises(bs.SpecError) as e:
        bs.compile_spec(spec)
    assert any(m.startswith("frames[0]") for m in e.value.errors) and any(m.startswith("frames[1]") for m in e.value.errors)


# ------------------------------------------------------------------------------------------------------------------------- layout

def positions(spec: dict, tmp_path: Path) -> dict[str, tuple[float, float]]:
    """Where each text element landed, by its text."""
    p, _ = build(spec, tmp_path)
    els = json.loads(p.read_text(encoding="utf-8"))["elements"]
    return {e["text"]: (e["x"], e["y"]) for e in els if e["type"] == "text"}


def test_items_stack_downwards_with_a_gap_and_the_next_one_waits_for_the_tallest(tmp_path):
    pos = positions(one([{"type": "heading", "text": "FIRST"}, {"type": "caps", "text": "SECOND"}, {"type": "caps", "text": "THIRD"}]), tmp_path)
    assert pos["FIRST"][1] < pos["SECOND"][1] < pos["THIRD"][1]
    assert pos["SECOND"][0] == pos["FIRST"][0]
    gap1, gap2 = pos["SECOND"][1] - pos["FIRST"][1], pos["THIRD"][1] - pos["SECOND"][1]
    assert gap1 > gap2 > 12, "the heading is taller than a caption, so the gap after it is bigger"


def test_same_puts_an_item_level_with_the_one_before_and_x_moves_it_across(tmp_path):
    pos = positions(one([{"type": "caps", "text": "LEFT"}, {"type": "caps", "text": "RIGHT", "x": 300, "y": "same"}, {"type": "caps", "text": "BELOW"}]), tmp_path)
    assert pos["LEFT"][1] == pos["RIGHT"][1]
    assert pos["RIGHT"][0] - pos["LEFT"][0] == 300
    assert pos["BELOW"][1] > pos["LEFT"][1]


def test_a_fixed_y_does_not_move_what_comes_after(tmp_path):
    pos = positions(one([{"type": "caps", "text": "A"}, {"type": "caps", "text": "FIXED", "y": 400}, {"type": "caps", "text": "B"}]), tmp_path)
    assert pos["FIXED"][1] - pos["A"][1] == 400
    assert pos["B"][1] < pos["FIXED"][1], "an item that says where it goes does not push the stack"


def test_a_card_grows_to_fit_and_what_follows_it_starts_below_it(tmp_path):
    spec = one([{"type": "card", "w": 300, "items": [{"type": "text", "text": "LINE " * 120, "w": 260}]}, {"type": "caps", "text": "AFTER"}])
    p, warns = build(spec, tmp_path)
    els = json.loads(p.read_text(encoding="utf-8"))["elements"]
    card = next(e for e in els if e["type"] == "rectangle" and e["width"] == 300)
    after = next(e for e in els if e["type"] == "text" and e["text"] == "AFTER")
    assert card["height"] > 100 and after["y"] >= card["y"] + card["height"] - 1 and warns == []


def test_the_frame_height_is_worked_out_from_the_items_unless_given(tmp_path):
    tall = one([{"type": "caps", "text": "A"}, {"type": "caps", "text": "B", "y": 900}])
    p, _ = build(tall, tmp_path)
    fr = next(e for e in json.loads(p.read_text(encoding="utf-8"))["elements"] if e["type"] == "frame")
    assert fr["height"] >= 900 + 24
    p2, _ = build(put(tall, ("frames", 0, "height"), 300), tmp_path, "p2.excalidraw")
    assert next(e for e in json.loads(p2.read_text(encoding="utf-8"))["elements"] if e["type"] == "frame")["height"] == 300


def test_an_arrow_is_glued_to_both_boxes_so_it_follows_them(tmp_path):
    spec = one([{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "x": 300, "y": "same"}, {"type": "arrow", "from": "a", "to": "b"}])
    p, _ = build(spec, tmp_path)
    els = json.loads(p.read_text(encoding="utf-8"))["elements"]
    arrow = next(e for e in els if e["type"] == "arrow")
    boxes = {e["id"] for e in els if e["type"] == "rectangle"}
    assert arrow["startBinding"]["elementId"] in boxes and arrow["endBinding"]["elementId"] in boxes
    assert arrow["startBinding"]["elementId"] != arrow["endBinding"]["elementId"]


def test_every_element_of_a_frame_is_inside_it_in_the_file(tmp_path):
    p, _ = build(bs.EXAMPLE, tmp_path)
    els = json.loads(p.read_text(encoding="utf-8"))["elements"]
    frames = [e for e in els if e["type"] == "frame"]
    assert len(frames) == 2
    assert all(e.get("frameId") for e in els if e["type"] != "frame" and e["x"] < frames[0]["x"] + frames[0]["width"] and e["y"] > frames[0]["y"] and e["y"] < frames[0]["y"] + frames[0]["height"] and e.get("frameId") is not None)


# ---------------------------------------------------------------------------------------------------------------------- warnings

def warns_of(spec: dict) -> list[str]:
    return bs.compile_spec(spec)[1]


def test_an_item_that_runs_past_the_frame_is_warned_about_with_its_place():
    w = warns_of(one([{"type": "text", "text": "wide", "w": 1200}], chrome="app"))
    assert any(m.startswith("frames[0].items[0]") and "runs outside" in m for m in w), w
    assert warns_of(one([{"type": "text", "text": "fits", "w": 700}], chrome="app")) == []


def test_two_items_on_top_of_each_other_are_warned_about():
    w = warns_of(one([{"type": "button", "label": "One"}, {"type": "button", "label": "Two", "y": 5}]))
    assert any("overlaps" in m and "items[1]" in m for m in w), w


def test_a_card_around_something_is_not_an_overlap():
    assert warns_of(one([{"type": "card", "w": 300, "items": [{"type": "text", "text": "in", "w": 200}]}])) == []


def test_two_items_side_by_side_are_not_an_overlap():
    assert warns_of(one([{"type": "button", "label": "One"}, {"type": "button", "label": "Two", "x": 150, "y": "same"}])) == []


def test_something_wider_than_its_card_is_warned_about():
    w = warns_of(one([{"type": "card", "w": 200, "items": [{"type": "text", "text": "x", "w": 300}]}]))
    assert any("wider than the inside of its card" in m for m in w), w


def test_a_card_with_a_height_that_is_too_small_is_warned_about():
    w = warns_of(one([{"type": "card", "w": 300, "h": 40, "items": [{"type": "text", "text": "word " * 60, "w": 260}]}]))
    assert any("run out of the card" in m for m in w), w


def test_a_label_that_will_not_fit_its_button_chip_or_box_is_warned_about():
    w = warns_of(one([{"type": "button", "label": "A very long label for a small button", "w": 60},
                      {"type": "chip", "label": "A long long label", "w": 40, "y": 100},
                      {"type": "box", "label": "A very long label that wraps many times over", "w": 60, "h": 30, "y": 200}]))
    assert any("may not fit a button" in m for m in w) and any("inside a chip" in m for m in w) and any("height but the box is" in m for m in w), w


def test_a_callout_without_a_note_and_a_note_without_a_callout_are_both_warned_about():
    w = warns_of(one([{"type": "heading", "text": "H", "callout": 2}], notes=["one", "two"]))
    assert any("note 1 has no callout" in m for m in w), w
    assert not any("callout 2 has no note" in m for m in w)
    w = warns_of(one([{"type": "heading", "text": "H", "callout": 3}], notes=["one"]))
    assert any("callout 3 has no note" in m for m in w) and any("note 1 has no callout" in m for m in w), w
    assert warns_of(one([{"type": "heading", "text": "H", "callout": 1}], notes=["one"])) == []


def test_an_explicit_callout_item_counts_as_a_callout_for_its_note():
    assert warns_of(one([{"type": "callout", "n": 1, "x": 10, "y": 10}], notes=["one"])) == []


def test_an_arrow_label_longer_than_the_arrow_is_warned_about():
    items = [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "x": 220, "y": "same"},
             {"type": "arrow", "from": "a", "to": "b", "label": "twelve chars"}]
    assert any("needs about" in m and "of line" in m and "120 px long" in m for m in warns_of(one(items))), "the line between the boxes is 120 px"
    items[1]["x"] = 300
    assert warns_of(one(items)) == []


def _two_arrows_into_one_box(**second) -> list:
    return [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "y": 120},
            {"type": "box", "id": "c", "label": "C", "w": 100, "h": 40, "x": 300, "y": 60},
            {"type": "arrow", "from": "a", "to": "c", "label": "one", "from_side": "r", "to_side": "t"},
            {"type": "arrow", "from": "b", "to": "c", "label": "two", "from_side": "r", "to_side": "t", **second}]


def test_labelled_arrows_that_meet_at_one_side_of_a_box_are_warned_about():
    got = [m for m in warns_of(one(_two_arrows_into_one_box())) if "meet at" in m]
    assert len(got) == 1 and "2 labelled arrows meet at the top side of c" in got[0] and "frames[0].items[3]" in got[0] and "frames[0].items[4]" in got[0], got


def test_arrows_that_end_on_different_sides_or_are_not_both_labelled_are_not_warned_about():
    assert not [m for m in warns_of(one(_two_arrows_into_one_box(to_side="l"))) if "meet at" in m], "different sides of the box"
    items = _two_arrows_into_one_box()
    del items[4]["label"]
    assert not [m for m in warns_of(one(items)) if "meet at" in m], "only one of the two carries a label"
    del items[3]["label"]
    assert not [m for m in warns_of(one(items)) if "meet at" in m], "neither carries a label"


def test_labelled_arrows_that_leave_one_side_of_a_box_are_warned_about_too_and_the_defaults_are_right_and_left():
    items = [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "x": 300},
             {"type": "box", "id": "c", "label": "C", "w": 100, "h": 40, "x": 300, "y": 100},
             {"type": "arrow", "from": "a", "to": "b", "label": "one"}, {"type": "arrow", "from": "a", "to": "c", "label": "two", "from_side": "r"}]
    got = [m for m in warns_of(one(items)) if "meet at" in m]
    assert len(got) == 1 and "right side of a" in got[0], "the default start is the right side"
    items[4].pop("from_side")
    items[3]["to_side"] = "l"
    items.append({"type": "arrow", "from": "c", "to": "b", "label": "three"})
    got = [m for m in warns_of(one(items)) if "meet at" in m]
    assert any("left side of b" in m for m in got), "the default end is the left side"


def test_each_warning_is_given_once_even_with_three_arrows_at_one_side():
    items = _two_arrows_into_one_box() + [{"type": "box", "id": "d", "label": "D", "w": 100, "h": 40, "y": 220}, {"type": "arrow", "from": "d", "to": "c", "label": "three", "from_side": "r", "to_side": "t"}]
    got = [m for m in warns_of(one(items)) if "meet at" in m]
    assert len(got) == 1 and "3 labelled arrows" in got[0]


def test_an_arrow_between_boxes_one_above_the_other_measures_the_vertical_gap():
    items = [{"type": "box", "id": "a", "label": "A", "w": 100, "h": 40}, {"type": "box", "id": "b", "label": "B", "w": 100, "h": 40, "y": 100},
             {"type": "arrow", "from": "a", "to": "b", "from_side": "b", "to_side": "t", "label": "twelve chars"}]
    assert any("60 px long" in m for m in warns_of(one(items)))


# ----------------------------------------------------------------------------------------------------------------------------- the CLI

def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(GEN / "board_spec.py"), *args], capture_output=True, text=True, cwd=str(GEN))


def test_the_command_line_check_build_describe_example_and_schema(tmp_path):
    spec = tmp_path / "s.json"
    r = run("example")
    assert r.returncode == 0
    spec.write_text(r.stdout, encoding="utf-8")
    assert json.loads(r.stdout) == bs.EXAMPLE
    r = run("check", str(spec))
    assert r.returncode == 0 and r.stdout.startswith("ok (2 frame(s)"), r.stdout
    out = tmp_path / "o.excalidraw"
    r = run("build", str(spec), str(out))
    assert r.returncode == 0 and out.is_file() and "dup 0 dangling 0" in r.stdout, r.stdout + r.stderr
    assert run("describe").stdout == bs.describe() + "\n"
    r = run("schema", str(tmp_path / "x.json"))
    assert r.returncode == 0 and json.loads((tmp_path / "x.json").read_text(encoding="utf-8")) == bs.schema()
    assert json.loads(run("schema").stdout) == bs.schema()


def test_a_flag_with_no_value_is_a_message_and_not_a_traceback(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(bs.EXAMPLE), encoding="utf-8")
    for args, word in ((("build", str(spec), str(tmp_path / "o.excalidraw"), "--png"), "--png"), (("build", str(spec), str(tmp_path / "o.excalidraw"), "--png", "--strict"), "--png"), (("build", str(spec), str(tmp_path / "o.excalidraw"), "--png", "--scale", "2"), "--png"),
                       (("build", str(spec), str(tmp_path / "o.excalidraw"), "--svg"), "--svg"), (("build", str(spec), str(tmp_path / "o.excalidraw"), "--png", "p.png", "--scale"), "--scale")):
        r = run(*args)
        assert r.returncode == 1, args
        assert "Traceback" not in r.stderr and f"{word} needs" in r.stderr, (args, r.stderr)


def test_the_command_line_reports_errors_one_per_line_and_exits_1(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(put(put(base(), ("frames", 0, "items", 0, "size"), "big"), ("colour",), 1)), encoding="utf-8")
    r = run("check", str(spec))
    assert r.returncode == 1
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("ERROR")]
    assert len(lines) == 2 and any("items[0].size" in ln for ln in lines) and any("'colour'" in ln for ln in lines), r.stdout
    r = run("build", str(spec), str(tmp_path / "o.excalidraw"))
    assert r.returncode == 1 and not (tmp_path / "o.excalidraw").exists(), "a spec with errors writes no file"


def test_the_json_output_is_machine_readable_for_a_repair_loop(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(put(base(), ("frames", 0, "items", 0, "size"), "big")), encoding="utf-8")
    r = run("check", str(spec), "--json")
    got = json.loads(r.stdout)
    assert r.returncode == 1 and got["ok"] is False and got["errors"] and got["warnings"] == []
    spec.write_text(json.dumps(bs.EXAMPLE), encoding="utf-8")
    got = json.loads(run("check", str(spec), "--json").stdout)
    assert got["ok"] is True and got["errors"] == []


def test_strict_turns_a_warning_into_a_failure_and_writes_no_file(tmp_path):
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(one([{"type": "text", "text": "wide", "w": 1200}], chrome="app")), encoding="utf-8")
    out = tmp_path / "o.excalidraw"
    r = run("build", str(spec), str(out))
    assert r.returncode == 0 and "WARN" in r.stdout and out.is_file()
    out.unlink()
    r = run("build", str(spec), str(out), "--strict")
    assert r.returncode == 1 and "WARN" in r.stdout and not out.exists()
    assert run("check", str(spec), "--strict").returncode == 1


def test_a_file_that_is_not_json_or_not_there_is_said_plainly(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    r = run("check", str(bad))
    assert r.returncode != 0 and "is not valid JSON" in (r.stderr + r.stdout) and "Traceback" not in r.stderr
    r = run("check", str(tmp_path / "missing.json"))
    assert r.returncode != 0 and "cannot read" in (r.stderr + r.stdout) and "Traceback" not in r.stderr


def test_with_no_arguments_it_prints_how_to_use_it():
    r = run()
    assert r.returncode == 2 and "python board_spec.py build" in r.stdout


def test_a_picture_can_be_asked_for_and_is_a_real_png(tmp_path):
    if not (GEN / "bundle.js").exists():
        pytest.skip("bundle.js is not built here (npm ci && sh make_bundle.sh), so no picture can be drawn")
    spec = tmp_path / "s.json"
    spec.write_text(json.dumps(bs.EXAMPLE), encoding="utf-8")
    png = tmp_path / "o.png"
    r = run("build", str(spec), str(tmp_path / "o.excalidraw"), "--png", str(png), "--scale", "1")
    if "could not render a picture" in r.stdout:
        pytest.skip("no browser to draw with here: " + r.stdout.strip().splitlines()[-1][:100])
    assert r.returncode == 0 and png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and png.stat().st_size > 20_000
    svg = tmp_path / "o.svg"
    r = run("build", str(spec), str(tmp_path / "o2.excalidraw"), "--svg", str(svg))
    assert r.returncode == 0, r.stdout + r.stderr
    import xml.dom.minidom
    root = xml.dom.minidom.parse(str(svg)).documentElement
    assert root.tagName == "svg" and root.getAttribute("xmlns") == "http://www.w3.org/2000/svg" and int(root.getAttribute("width")) > 1000, "a vector picture that any viewer can open"


def test_the_committed_boards_are_not_changed_by_this_program():
    """The Python boards and this compiler share the widgets; building a spec must not alter shared state (a leftover from one build must not leak into the next)."""
    a = bs.compile_spec(bs.EXAMPLE)[0]
    bs.compile_spec(one([{"type": "heading", "text": "other"}]))
    b = bs.compile_spec(bs.EXAMPLE)[0]
    assert json.dumps(a.els, sort_keys=True) == json.dumps(b.els, sort_keys=True)


# ------------------------------------------------------------------------------------------------- where things land, checked in the file

def els_of(spec: dict, tmp_path: Path) -> list[dict]:
    p, _ = build(spec, tmp_path)
    return json.loads(p.read_text(encoding="utf-8"))["elements"]


def test_content_in_an_app_frame_starts_to_the_right_of_the_sidebar(tmp_path):
    els = els_of(one([{"type": "heading", "text": "HEAD"}], chrome="app"), tmp_path)
    fr = next(e for e in els if e["type"] == "frame")
    head = next(e for e in els if e.get("text") == "HEAD")
    assert 174 <= head["x"] - fr["x"] <= 260, "the sidebar is 150 px wide; content needs a gutter beside it and should not float far from it"


def test_a_frame_with_the_app_chrome_is_at_least_as_tall_as_the_sidebar_and_a_bare_frame_is_short(tmp_path):
    app = next(e for e in els_of(one([{"type": "caps", "text": "A"}], chrome="app"), tmp_path) if e["type"] == "frame")
    bare = next(e for e in els_of(one([{"type": "caps", "text": "A"}]), tmp_path) if e["type"] == "frame")
    assert app["height"] == 520 and bare["height"] == 200


def test_the_active_entry_and_the_lens_change_the_drawing(tmp_path):
    def bytes_of(**kw):
        return json.dumps(els_of(one([{"type": "caps", "text": "A"}], chrome="app", **kw), tmp_path), sort_keys=True)
    assert bytes_of(active="Overview") != bytes_of(active="Audit log")
    assert bytes_of(lens=0) != bytes_of(lens=2)


def test_a_row_waits_for_its_tallest_item(tmp_path):
    pos = positions(one([{"type": "caps", "text": "SHORT"}, {"type": "heading", "text": "TALL", "size": 40, "x": 400, "y": "same"}, {"type": "caps", "text": "BELOW"}]), tmp_path)
    assert pos["BELOW"][1] > pos["TALL"][1] + 40 * 1.25, "the next item starts below the tallest item of the row, not the last one"


def test_a_card_has_the_same_space_above_and_below_what_it_holds(tmp_path):
    words = "INSIDE " + "more words " * 30
    els = els_of(one([{"type": "card", "w": 300, "items": [{"type": "text", "text": words, "w": 250}]}]), tmp_path)
    card = next(e for e in els if e["type"] == "rectangle" and e["width"] == 300)
    txt = next(e for e in els if e.get("text", "").startswith("INSIDE"))
    assert card["height"] > 100
    above, below = txt["y"] - card["y"], card["y"] + card["height"] - (txt["y"] + txt["height"])
    assert abs(above - below) <= 6, (above, below)


def test_what_is_inside_a_card_is_drawn_inside_it(tmp_path):
    els = els_of(one([{"type": "card", "w": 300, "items": [{"type": "text", "text": "INSIDE", "w": 200}]}]), tmp_path)
    card = next(e for e in els if e["type"] == "rectangle" and e["width"] == 300)
    txt = next(e for e in els if e.get("text") == "INSIDE")
    assert card["x"] < txt["x"] and txt["x"] + txt["width"] < card["x"] + card["width"] and txt["x"] - card["x"] >= 12


def test_a_callout_on_words_sits_beside_them_and_on_a_box_sits_on_its_corner(tmp_path):
    els = els_of(one([{"type": "heading", "text": "HEAD", "callout": 1}, {"type": "box", "label": "BOX", "w": 100, "h": 40, "callout": 2, "y": 100}], notes=["a", "b"]), tmp_path)
    fr = next(e for e in els if e["type"] == "frame")
    by_id = {e["id"]: e for e in els}
    reds = {}
    for e in els:
        if e["type"] == "text" and e.get("text") in ("1", "2") and e.get("containerId"):
            c = by_id[e["containerId"]]
            if c["type"] == "ellipse" and c["width"] == 20 and c["x"] < fr["x"] + fr["width"]:       # the numbers in the frame, not the ones in the notes column
                reds[e["text"]] = c
    assert set(reds) == {"1", "2"}
    head = next(e for e in els if e.get("text") == "HEAD")
    assert reds["1"]["x"] + reds["1"]["width"] <= head["x"], "a number on the first letters of a heading hides them"
    box = next(e for e in els if e["type"] == "rectangle" and e["width"] == 100)
    assert abs(reds["2"]["x"] - box["x"]) <= 12 and abs(reds["2"]["y"] - box["y"]) <= 12


def test_the_notes_are_beside_their_frame_and_the_next_frame_starts_below_them(tmp_path):
    long_notes = ["A note that says why, in a sentence long enough to wrap onto several lines of the notes column. " * 2] * 8
    spec = {"format": bs.FORMAT, "title": "T", "frames": [{"name": "1.1 · A", "width": 600, "height": 200, "items": [{"type": "caps", "text": "A"}], "notes": long_notes},
                                                          {"name": "1.2 · B", "width": 600, "height": 200, "items": [{"type": "caps", "text": "B"}]}]}
    els = els_of(spec, tmp_path)
    frames = sorted((e for e in els if e["type"] == "frame"), key=lambda e: e["y"])
    notes = [e for e in els if e["type"] == "text" and e.get("text", "").startswith("A note")]
    assert notes and all(n["x"] >= frames[0]["x"] + frames[0]["width"] for n in notes), "notes belong beside the frame, not on it"
    assert frames[1]["y"] >= max(n["y"] + n["height"] for n in notes), "the second frame would sit on top of the first one's notes"


def test_text_placed_to_the_right_wraps_into_what_is_left_of_the_row(tmp_path):
    spec = one([{"type": "text", "text": "word " * 80, "x": 500}], chrome="app")
    p, warns = build(spec, tmp_path)
    assert warns == [], warns


def test_each_edge_of_the_frame_is_checked():
    for kw in ({"x": -100}, {"y": -100}, {"y": 700}, {"x": 900}):
        w = warns_of(one([{"type": "button", "label": "Edge", **kw}], chrome="app", height=600))
        assert any("runs outside" in m for m in w), (kw, w)
    assert warns_of(one([{"type": "button", "label": "Edge", "x": 10, "y": 10}], chrome="app", height=600)) == []


def test_default_width_text_in_a_card_is_narrower_than_the_card_and_draws_inside_it(tmp_path):
    spec = one([{"type": "card", "w": 300, "items": [{"type": "text", "text": "word " * 60}]}])
    p, warns = build(spec, tmp_path)
    assert warns == [], warns
    els = json.loads(p.read_text(encoding="utf-8"))["elements"]
    card = next(e for e in els if e["type"] == "rectangle" and e["width"] == 300)
    txt = next(e for e in els if e["type"] == "text" and e["text"].startswith("word"))
    assert txt["x"] + txt["width"] <= card["x"] + card["width"] - 12


def test_an_item_placed_on_a_card_that_is_a_sibling_is_not_an_overlap_but_one_half_on_it_is():
    card = {"type": "card", "w": 400, "h": 200}
    assert warns_of(one([card, {"type": "button", "label": "On it", "x": 20, "y": 20}])) == []
    w = warns_of(one([card, {"type": "button", "label": "Half on it", "x": 350, "y": 20}]))
    assert any("overlaps" in m for m in w), w


def test_overlaps_inside_a_card_are_noticed_too():
    w = warns_of(one([{"type": "card", "w": 400, "items": [{"type": "button", "label": "One"}, {"type": "button", "label": "Two", "y": 5}]}]))
    assert any("overlaps" in m and "items[0].items[1]" in m for m in w), w
