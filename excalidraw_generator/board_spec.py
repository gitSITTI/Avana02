#!/usr/bin/env python3
"""A board written as plain JSON, compiled to an Excalidraw file: the way for ANY agent to make these boards, with or without running code.

The boards in this repository are written as Python (EXCALIDRAW_GUIDE.md). An agent that cannot run code, or that writes JSON more reliably than Python, can describe a board in the
format below instead; this program checks it, lays it out with the same widgets and the same palette, and writes the .excalidraw file. The format is small on purpose: fifteen kinds of
item, no raw Excalidraw JSON, no colours but the palette's names, so a model cannot draw a board that breaks the design rules.

  python board_spec.py check   spec.json                  check only; say every problem at once, each with its path (feed them back to the model)
  python board_spec.py build   spec.json out.excalidraw   check, lay out, write, then run validate.py on the result   [--strict: warnings are errors]  [--png out.png --scale 3]  [--svg out.svg: a vector picture]
  python board_spec.py describe                           the vocabulary in Markdown, generated from the same table the checker uses (paste it into a prompt)
  python board_spec.py example                            a small working spec, to start from
  python board_spec.py schema [FILE]                      the JSON Schema (2020-12), generated from the same table; written to FILE or printed

Add  --json  to check or build for a machine-readable result:  {"ok": bool, "errors": [...], "warnings": [...]}.

A spec:  {"format": "reqin-board/1", "title": "13 · Review", "seed": 1301, "frames": [ {"name": "13.1 · A screen", "width": 1000, "chrome": "app", "active": "Review queue",
          "items": [ {"type": "heading", "text": "..."}, {"type": "card", "w": 420, "callout": 1, "items": [...]} ], "notes": ["why the screen is like this", ...]} ]}

Layout. Items are placed top to bottom with a 14 px gap unless they say where they go. `x` is the left edge (default 0). `y` is the top edge; leave it out to go below everything so far,
or give `"y": "same"` to sit level with the previous item (two columns), or a number for a fixed position. A card holds items of its own, laid out the same way inside it, and grows to fit
them. Coordinates are relative to the content area (to the right of the sidebar when `chrome` is "app"). The frame's height is worked out when you leave it out.

Callouts. Give any item `"callout": 1` and a red number 1 is drawn on its top-left corner; the first note beside the frame explains it. Every note should have a callout and every callout a note.
"""
from __future__ import annotations

import json
import re
import sys
import zlib
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FORMAT = "reqin-board/1"
GAP = 14
CARD_PAD_X, CARD_PAD_Y = 16, 14
MAX_FRAMES, MAX_ITEMS, MAX_NOTES, MAX_DEPTH = 20, 300, 20, 5
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,39}")
TONES = ["white", "grey", "green", "amber", "red", "blue", "violet"]
SIDEBAR = ["Overview", "Review queue", "Methods and metrics", "Audit log", "Export to documents"]
STATES = ["Pass", "Needs you", "Blocked", "Done", "Open"]
SIDES = ["l", "r", "t", "b"]
SIDE_NAMES = {"l": "left", "r": "right", "t": "top", "b": "bottom"}

# ------------------------------------------------------------------------------------------------ the vocabulary, as data
# One table drives the checker, the JSON Schema and the Markdown that is pasted into prompts, so the three cannot disagree.
# a field is (name, kind, required, options, what it is). Kinds: str, int, num, bool, enum, strs, ints, id, items, rows, checks.
F = lambda name, kind, req=False, doc="", **opt: (name, kind, req, opt, doc)      # noqa: E731

ITEMS: dict[str, dict[str, Any]] = {
    "heading": {"doc": "A heading.", "fields": [F("text", "str", True, "the words", maxlen=120), F("size", "int", False, "font size, default 22", lo=12, hi=48)]},
    "text": {"doc": "A paragraph, wrapped to a width. Use this for every sentence.", "fields": [
        F("text", "str", True, "the words", maxlen=600), F("w", "int", False, "width in px, default: what is left of the row", lo=40, hi=2000),
        F("size", "int", False, "font size, default 11", lo=8, hi=24), F("tone", "enum", False, "body (default), soft (grey) or danger (red)", values=["body", "soft", "danger"])]},
    "caps": {"doc": "A small monospace caption in soft grey: the label of a section. Write it in capitals.", "fields": [F("text", "str", True, "the words", maxlen=80)]},
    "card": {"doc": "A white panel that holds items of its own. It grows to fit them unless you give `h`. Dashed means optional or not built yet.", "fields": [
        F("w", "int", False, "width, default: what is left of the row", lo=40, hi=2000), F("h", "int", False, "height, default: fits the items", lo=20, hi=3000),
        F("tone", "enum", False, "fill, default white", values=TONES), F("dash", "bool", False, "dashed outline"), F("items", "items", False, "the items inside; x and y are relative to the card's inside")]},
    "button": {"doc": "A button. One primary button per screen.", "fields": [
        F("label", "str", True, "the words", maxlen=60), F("w", "int", False, "width, default fits the label", lo=40, hi=600), F("h", "int", False, "height, default 32", lo=20, hi=80),
        F("primary", "bool", False, "the one main action"), F("disabled", "bool", False, "dashed, greyed")]},
    "chip": {"doc": "A small pill that says a state or a label. Always a word, never colour alone.", "fields": [
        F("label", "str", True, "the words", maxlen=40), F("w", "int", False, "width, default fits the label", lo=30, hi=400), F("tone", "enum", False, "fill, default grey", values=TONES),
        F("dash", "bool", False, "dashed outline")]},
    "bar": {"doc": "A progress bar.", "fields": [F("w", "int", True, "width", lo=20, hi=2000), F("frac", "num", True, "how full, 0 to 1", lo=0, hi=1)]},
    "placeholder": {"doc": "Grey bars standing in for text that does not matter to this picture.", "fields": [
        F("w", "int", True, "width", lo=20, hi=2000), F("lines", "int", False, "how many bars, default 3", lo=1, hi=8)]},
    "mark": {"doc": "A provenance mark: square = mechanical, diamond = AI, circle = person. These meanings never change.", "fields": [
        F("kind", "enum", True, "mech, ai or human", values=["mech", "ai", "human"]), F("label", "str", False, "words beside the mark", maxlen=60)]},
    "table": {"doc": "A table with wrapped cells. Every row has as many cells as `head`, and `widths` has one width per column.", "fields": [
        F("widths", "ints", True, "column widths in px", lo=30, hi=1200, maxn=8), F("head", "strs", True, "column headings", maxlen=40, maxn=8),
        F("rows", "rows", True, "a list of rows; a cell is a string, or {\"text\": ..., \"tone\": ...} to colour it", maxn=60),
        F("size", "int", False, "font size, default 10", lo=8, hi=14), F("bold_first", "bool", False, "the first column in dark text")]},
    "checklist": {"doc": "A checklist; each line has a state chip.", "fields": [
        F("w", "int", True, "width", lo=150, hi=2000), F("items", "checks", True, "lines: {\"state\": Pass | Needs you | Blocked | Done | Open, \"text\": ...}", maxn=30)]},
    "kv": {"doc": "A key and its value on one line.", "fields": [
        F("key", "str", True, "the key", maxlen=40), F("value", "str", True, "the value", maxlen=100), F("key_w", "int", False, "width of the key column, default 110", lo=40, hi=400)]},
    "box": {"doc": "A box for a diagram (a step, a state, a part). Give it an `id` so arrows can join it.", "fields": [
        F("label", "str", True, "the words inside", maxlen=120), F("w", "int", True, "width", lo=30, hi=800), F("h", "int", True, "height", lo=20, hi=600),
        F("id", "id", False, "a name for arrows to use: a letter, then letters, digits, _ or -"), F("shape", "enum", False, "rect (default), ellipse or diamond", values=["rect", "ellipse", "diamond"]),
        F("tone", "enum", False, "fill, default white", values=TONES), F("dash", "bool", False, "dashed outline"), F("size", "int", False, "font size, default 12", lo=8, hi=24)]},
    "arrow": {"doc": "An arrow between two boxes, glued to both so it follows them when they are moved in Excalidraw. Takes no space of its own.", "fields": [
        F("from", "id", True, "the id of the box it starts at"), F("to", "id", True, "the id of the box it ends at"),
        F("from_side", "enum", False, "l, r, t or b; default r", values=SIDES), F("to_side", "enum", False, "l, r, t or b; default l", values=SIDES),
        F("label", "str", False, "a word on the line", maxlen=40), F("dash", "bool", False, "dashed line")]},
    "callout": {"doc": "A red number placed by hand. (Easier: give another item `callout`.)", "fields": [F("n", "int", True, "the number; the note with the same number explains it", lo=1, hi=MAX_NOTES)]},
}
COMMON = [F("x", "int", False, "left edge, default 0", lo=-200, hi=4000),
          F("y", "ypos", False, "top edge: a number, \"same\" (level with the previous item), or leave it out (below everything so far)", lo=-200, hi=6000),
          F("callout", "int", False, "draw a red number on this item's top-left corner", lo=1, hi=MAX_NOTES)]
NO_COMMON = {"arrow": {"x", "y", "callout"}, "callout": {"callout"}}     # an arrow takes no space; a callout is not numbered by another callout
TEXT_LIKE = ("heading", "text", "caps", "kv", "mark")                   # these have words at their left edge, so their callout goes beside them, not on them


def fields_of(t: str) -> list:
    return ITEMS[t]["fields"] + [f for f in COMMON if f[0] not in NO_COMMON.get(t, ())]


FRAME_FIELDS = [
    F("name", "str", True, "the frame's name: 'N.M · Title', so the boards read as an index in Excalidraw's frame list", maxlen=100),
    F("width", "int", False, "default 1000", lo=500, hi=2400), F("height", "int", False, "default: worked out from the items", lo=200, hi=3000),
    F("chrome", "enum", False, "app = the sidebar, title block and DRAFT banner; none (default) = a bare frame, for diagrams", values=["app", "none"]),
    F("active", "enum", False, "with chrome app: which sidebar entry is highlighted", values=SIDEBAR), F("lens", "int", False, "with chrome app: 0 systems, 1 process, 2 UI/UX, 3 new user", lo=0, hi=3),
    F("items", "items", True, "what is drawn, top to bottom"), F("notes", "strs", False, "the reasoning beside the frame, numbered 1, 2, ...; one idea each; say why, not what", maxlen=400, maxn=MAX_NOTES)]
BOARD_FIELDS = [F("format", "enum", True, f"always {FORMAT}", values=[FORMAT]), F("title", "str", True, "the board's title", maxlen=100),
                F("seed", "int", False, "a number that fixes the hand-drawn look of every element, so a rebuild is byte-identical; default made from the title", lo=1, hi=2**31 - 1),
                F("frames", "frames", True, "the screens or diagrams, top to bottom", maxn=MAX_FRAMES)]

# ------------------------------------------------------------------------------------------------------------- the checker


class SpecError(Exception):
    def __init__(self, errors: list[str], warnings: list[str] | None = None):
        super().__init__("; ".join(errors[:3]))
        self.errors, self.warnings = errors, warnings or []


def _kind(v: Any) -> str:
    return "null" if v is None else "a boolean" if isinstance(v, bool) else "a number" if isinstance(v, (int, float)) else "text" if isinstance(v, str) else "a list" if isinstance(v, list) else "an object"


def _val(kind: str, opt: dict, v: Any, path: str, errs: list[str], item_check: Callable[[Any, str], None] | None = None) -> None:
    def bad(msg: str) -> None:
        errs.append(f"{path}: {msg}")
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)   # noqa: E731
    if kind == "str":
        if not isinstance(v, str) or not v.strip():
            return bad(f"must be non-empty text, not {_kind(v)}")
        if len(v) > opt.get("maxlen", 400):
            bad(f"is {len(v)} characters; at most {opt.get('maxlen', 400)} (split it, or use a text item)")
    elif kind == "int":
        if not isinstance(v, int) or isinstance(v, bool):
            return bad(f"must be a whole number, not {_kind(v)}")
        if not opt.get("lo", -10**9) <= v <= opt.get("hi", 10**9):
            bad(f"is {v}; it must be from {opt.get('lo')} to {opt.get('hi')}")
    elif kind == "num":
        if not num(v):
            return bad(f"must be a number, not {_kind(v)}")
        if not opt.get("lo", -1e9) <= v <= opt.get("hi", 1e9):
            bad(f"is {v}; it must be from {opt.get('lo')} to {opt.get('hi')}")
    elif kind == "bool":
        if not isinstance(v, bool):
            bad(f"must be true or false, not {_kind(v)}")
    elif kind == "enum":
        if v not in opt["values"]:
            bad(f"is {json.dumps(v)}; it must be one of {', '.join(map(str, opt['values']))}")
    elif kind == "id":
        if not isinstance(v, str) or not ID_RE.fullmatch(v):
            bad("must be an id: a letter, then up to 39 letters, digits, _ or -")
    elif kind == "ypos":
        if v == "same":
            return
        if not isinstance(v, int) or isinstance(v, bool):
            return bad('must be a whole number or the word "same"')
        if not opt["lo"] <= v <= opt["hi"]:
            bad(f"is {v}; it must be from {opt['lo']} to {opt['hi']}")
    elif kind in ("strs", "ints"):
        if not isinstance(v, list) or not v:
            return bad("must be a non-empty list")
        if len(v) > opt.get("maxn", 50):
            bad(f"has {len(v)} entries; at most {opt.get('maxn', 50)}")
        for i, x in enumerate(v):
            _val("str" if kind == "strs" else "int", opt, x, f"{path}[{i}]", errs)
    elif kind == "rows":
        if not isinstance(v, list) or not v:
            return bad("must be a non-empty list of rows")
        if len(v) > opt.get("maxn", 60):
            bad(f"has {len(v)} rows; at most {opt.get('maxn', 60)}")
        for i, row in enumerate(v):
            if not isinstance(row, list) or not row:
                errs.append(f"{path}[{i}]: must be a list of cells")
                continue
            for j, c in enumerate(row):
                cp = f"{path}[{i}][{j}]"
                if isinstance(c, str):
                    if len(c) > 300:
                        errs.append(f"{cp}: is {len(c)} characters; at most 300")
                elif isinstance(c, dict):
                    extra = set(c) - {"text", "tone"}
                    if extra or not isinstance(c.get("text"), str) or c.get("tone", "white") not in TONES:
                        errs.append(f"{cp}: a coloured cell is {{\"text\": ..., \"tone\": one of {', '.join(TONES)}}}")
                else:
                    errs.append(f"{cp}: a cell is text, or {{\"text\": ..., \"tone\": ...}}, not {_kind(c)}")
    elif kind == "checks":
        if not isinstance(v, list) or not v:
            return bad("must be a non-empty list")
        if len(v) > opt.get("maxn", 30):
            bad(f"has {len(v)} lines; at most {opt.get('maxn', 30)}")
        for i, c in enumerate(v):
            if not isinstance(c, dict) or set(c) != {"state", "text"} or c["state"] not in STATES or not isinstance(c["text"], str) or not c["text"].strip():
                errs.append(f"{path}[{i}]: a line is {{\"state\": {' | '.join(STATES)}, \"text\": ...}}")
    elif kind in ("items", "frames"):
        if not isinstance(v, list):
            return bad("must be a list")
        if kind == "frames" and not v:
            return bad("needs at least one frame")
        if len(v) > (MAX_FRAMES if kind == "frames" else MAX_ITEMS):
            bad(f"has {len(v)} entries; at most {MAX_FRAMES if kind == 'frames' else MAX_ITEMS}")
        for i, x in enumerate(v):
            (item_check or (lambda *_: None))(x, f"{path}[{i}]")


def _fields(obj: Any, fields: list, path: str, errs: list[str], item_check: Callable[[Any, str], None], where: str) -> None:
    names = {f[0] for f in fields}
    for name, kind, req, opt, _doc in fields:
        if name in obj:
            _val(kind, opt, obj[name], f"{path}.{name}" if path else name, errs, item_check)
        elif req:
            errs.append(f"{path or 'the board'}: missing {name!r} ({where} needs it)")


def check_spec(spec: Any) -> list[str]:
    """Every structural problem in a spec, each starting with its path. [] means the spec is well formed (layout problems come when it is built)."""
    errs: list[str] = []
    if not isinstance(spec, dict):
        return [f"the spec must be a JSON object, not {_kind(spec)}"]

    def item(it: Any, path: str) -> None:
        if not isinstance(it, dict):
            errs.append(f"{path}: an item is an object like {{\"type\": \"text\", ...}}, not {_kind(it)}")
            return
        t = it.get("type")
        if not isinstance(t, str) or t not in ITEMS:
            errs.append(f"{path}.type: {json.dumps(t)} is not an item type; use one of {', '.join(ITEMS)}")
            return
        if path.count(".items[") > MAX_DEPTH:
            errs.append(f"{path}: items are nested more than {MAX_DEPTH} deep (cards inside cards); flatten the board")
            return
        fields = fields_of(t)
        unknown = sorted(set(it) - {"type"} - {f[0] for f in fields})
        if unknown:
            errs.append(f"{path}: {t} has no field {', '.join(map(repr, unknown))}; it has {', '.join(f[0] for f in fields)}")
        _fields(it, fields, path, errs, item, f"a {t}")

    def frame(fr: Any, path: str) -> None:
        if not isinstance(fr, dict):
            errs.append(f"{path}: a frame is an object")
            return
        unknown = sorted(set(fr) - {f[0] for f in FRAME_FIELDS})
        if unknown:
            errs.append(f"{path}: a frame has no field {', '.join(map(repr, unknown))}; it has {', '.join(f[0] for f in FRAME_FIELDS)}")
        _fields(fr, FRAME_FIELDS, path, errs, item, "a frame")
        if fr.get("chrome", "none") == "none" and ("active" in fr or "lens" in fr):
            errs.append(f"{path}: active and lens only mean something with \"chrome\": \"app\"")

    unknown = sorted(set(spec) - {f[0] for f in BOARD_FIELDS})
    if unknown:
        errs.append(f"the board has no field {', '.join(map(repr, unknown))}; it has {', '.join(f[0] for f in BOARD_FIELDS)}")
    _fields(spec, BOARD_FIELDS, "", errs, frame, "the board")
    return errs


# ------------------------------------------------------------------------------------------------------------- the layout

from exc import Doc, INK  # noqa: E402
from wf2 import (BLUE_BG, DARK, GREEN_BG, GREY, LINE, RED, RED_BG, SOFT, VIOLET_BG, AMBER_BG, chk_list, kv, new_frame, notes, para, shell2, table)  # noqa: E402

FILL = {"white": "#ffffff", "grey": GREY, "green": GREEN_BG, "amber": AMBER_BG, "red": RED_BG, "blue": BLUE_BG, "violet": VIOLET_BG}
TEXT_TONE = {"body": DARK, "soft": SOFT, "danger": RED}


class Node:
    def __init__(self, path: str, kind: str, w: float, h: float, draw: Callable | None = None, kids: list | None = None, item: dict | None = None, label: str = ""):
        self.path, self.kind, self.w, self.h, self.draw, self.kids, self.item, self.label = path, kind, w, h, draw, kids or [], item or {}, label
        self.x = self.y = 0.0


class Ctx:
    def __init__(self, d: Doc, errors: list[str], warnings: list[str]):
        self.d, self.errors, self.warnings = d, errors, warnings
        self.box_paths: dict[str, str] = {}
        self.els: dict[str, dict] = {}
        self.arrows: list[Node] = []
        self.callouts: list[int] = []


def _lines(d: Doc, text: str, w: float, fs: float) -> int:
    return d.wrap(text, max(10, w), fs).count("\n") + 1


def _node(it: dict, path: str, avail: float, c: Ctx) -> Node:
    t, d = it["type"], c.d
    label = (it.get("text") or it.get("label") or it.get("key") or "")[:30]
    if t == "heading":
        fs = it.get("size", 22)
        return Node(path, t, min(avail, len(it["text"]) * fs * 0.55 + 4), fs * 1.25, lambda s, X, Y: s.h1(X, Y, it["text"], fs=fs), item=it, label=label)
    if t == "text":
        w, fs = it.get("w", avail), it.get("size", 11)
        wrapped = d.wrap(it["text"], w, fs)
        h = (wrapped.count("\n") + 1) * fs * 1.25
        return Node(path, t, w, h, lambda s, X, Y: s.t(X, Y, wrapped, fs=fs, color=TEXT_TONE[it.get("tone", "body")]), item=it, label=label)
    if t == "caps":
        return Node(path, t, len(it["text"]) * 5.6 + 2, 12, lambda s, X, Y: s.caps(X, Y, it["text"]), item=it, label=label)
    if t == "card":
        w = it.get("w", avail)
        inner, bottom = _flow(it.get("items", []), path + ".items", w - 2 * CARD_PAD_X, c)
        h = it.get("h") or max(60, bottom + 2 * CARD_PAD_Y)

        def draw(s, X, Y):
            s.card(X, Y, w, h, fill=FILL[it.get("tone", "white")], dash=it.get("dash", False))
            _draw(inner, s, X + CARD_PAD_X, Y + CARD_PAD_Y, c)
        for k in inner:
            if k.kind not in ("arrow", "callout") and k.w and k.x + k.w > w - 2 * CARD_PAD_X + 1:
                c.warnings.append(f"{k.path} ({k.kind} {k.label!r}) is wider than the inside of its card ({round(k.x + k.w)} px against {round(w - 2 * CARD_PAD_X)}); make it narrower or the card wider")
        if it.get("h") and bottom + 2 * CARD_PAD_Y > it["h"] + 2:
            c.warnings.append(f"{path}: the items need {round(bottom + 2 * CARD_PAD_Y)} px but h is {it['h']}; they run out of the card (leave h out to let it grow)")
        return Node(path, t, w, h, draw, kids=inner, item=it, label=label)
    if t == "button":
        lab = it["label"]
        w, h = it.get("w", max(100, len(lab) * 7.2 + 28)), it.get("h", 32)
        if len(lab) * 6.6 + 12 > w:
            c.warnings.append(f"{path}: the label may not fit a button {w} px wide (about {round(len(lab) * 6.6 + 12)} px needed)")
        return Node(path, t, w, h, lambda s, X, Y: s.btn(X, Y, w, h, lab, primary=it.get("primary", False), disabled=it.get("disabled", False)), item=it, label=label)
    if t == "chip":
        lab = it["label"]
        w = it.get("w", max(48, len(lab) * 5.6 + 20))
        if len(lab) * 5.2 + 8 > w:
            c.warnings.append(f"{path}: the label may wrap inside a chip {w} px wide (about {round(len(lab) * 5.2 + 8)} px needed)")
        return Node(path, t, w, 18, lambda s, X, Y: s.chip(X, Y, w, 18, lab, fill=FILL[it.get("tone", "grey")], dash=it.get("dash", False)), item=it, label=label)
    if t == "bar":
        return Node(path, t, it["w"], 8, lambda s, X, Y: s.bar(X, Y, it["w"], it["frac"]), item=it)
    if t == "placeholder":
        n = it.get("lines", 3)
        return Node(path, t, it["w"], (n - 1) * 10 + 5, lambda s, X, Y: s.ph(X, Y, it["w"], n), item=it)
    if t == "mark":
        lab = it.get("label", "")
        kind = {"mech": "mech", "ai": "ai", "human": "human"}[it["kind"]]
        return Node(path, t, 14 + len(lab) * 5.4, 12, lambda s, X, Y: s.prov(X, Y, kind, lab or None), item=it, label=lab[:30])
    if t == "table":
        widths, head, rows, fs = it["widths"], it["head"], it["rows"], it.get("size", 10)
        if len(widths) != len(head):
            c.errors.append(f"{path}: widths has {len(widths)} entries but head has {len(head)}; one width per column")
        bad = [i for i, r in enumerate(rows) if len(r) != len(head)]
        for i in bad[:3]:
            c.errors.append(f"{path}.rows[{i}]: has {len(rows[i])} cells but head has {len(head)}")
        if len(widths) != len(head) or bad:
            return Node(path, t, 0, 0, None, item=it)
        cells = [[(x, None) if isinstance(x, str) else (x["text"], FILL[x.get("tone", "white")]) for x in r] for r in rows]
        h = 26
        for r in cells:
            n = max(_lines(d, txt, wd - 16, fs) for wd, (txt, _f) in zip(widths, r))
            h += max(26, n * fs * 1.25 + 14)
        return Node(path, t, sum(widths), h, lambda s, X, Y: table(s, X, Y, widths, head, [[(txt, f) if f else txt for txt, f in r] for r in cells], fs=fs, bold_first=it.get("bold_first", False)), item=it)
    if t == "checklist":
        w, lines = it["w"], it["items"]
        h = sum(max(24, _lines(d, ln["text"], w - 84, 9) * 9 * 1.25 + 8) for ln in lines)
        return Node(path, t, w, h, lambda s, X, Y: chk_list(s, X, Y, w, [(ln["state"], ln["text"]) for ln in lines]), item=it)
    if t == "kv":
        kw = it.get("key_w", 110)
        return Node(path, t, kw + len(it["value"]) * 5, 14, lambda s, X, Y: kv(s, X, Y, it["key"], it["value"], kw=kw), item=it, label=it["key"][:30])
    if t == "box":
        fs, w, h = it.get("size", 12), it["w"], it["h"]
        need = _lines(d, it["label"], w - 12, fs) * fs * 1.25 + 8
        if need > h:
            c.warnings.append(f"{path}: the label needs about {round(need)} px of height but the box is {h}")
        bid = it.get("id")
        if bid:
            if bid in c.box_paths:
                c.errors.append(f"{path}.id: {bid!r} is already used by {c.box_paths[bid]}; ids must be unique within a frame")
            c.box_paths[bid] = path
        typ = {"rect": "rectangle", "ellipse": "ellipse", "diamond": "diamond"}[it.get("shape", "rect")]

        def draw(s, X, Y):
            el = s.shape(typ, X, Y, w, h, it["label"], fs=fs, fill=FILL[it.get("tone", "white")], stroke="#495057", dash=it.get("dash", False))
            if bid:
                c.els[bid] = el
        return Node(path, t, w, h, draw, item=it, label=it["label"][:30])
    if t == "arrow":
        n = Node(path, t, 0, 0, None, item=it)
        c.arrows.append(n)
        return n
    if t == "callout":
        c.callouts.append(it["n"])
        return Node(path, t, 20, 20, lambda s, X, Y: s.num(X, Y, it["n"]), item=it)
    raise AssertionError(t)


def _anchor(el: dict, side: str) -> tuple[float, float]:
    x, y, w, h = el["x"], el["y"], el["width"], el["height"]
    return {"l": (x, y + h / 2), "r": (x + w, y + h / 2), "t": (x + w / 2, y), "b": (x + w / 2, y + h)}[side]


def _flow(items: list, path: str, avail: float, c: Ctx) -> tuple[list[Node], float]:
    """Lay a list of items out in a column. Returns the nodes (with x, y) and the bottom edge of the lowest."""
    nodes: list[Node] = []
    cur = 0.0
    bottom = 0.0
    prev: Node | None = None
    for i, it in enumerate(items):
        x = it.get("x", 0)
        n = _node(it, f"{path}[{i}]", max(40, avail - x), c)
        y = it.get("y")
        if y is None:
            y = cur
        elif y == "same":
            y = prev.y if prev else cur
        n.x, n.y = x, y
        if it.get("callout"):
            c.callouts.append(it["callout"])
        if n.kind not in ("arrow", "callout"):
            if it.get("y") is None or it.get("y") == "same":
                cur = max(cur, y + n.h + GAP)
            bottom = max(bottom, y + n.h)
            prev = n
        nodes.append(n)
    return nodes, bottom


def _draw(nodes: list[Node], s: Any, X0: float, Y0: float, c: Ctx) -> None:
    for n in nodes:
        if n.draw:
            n.draw(s, X0 + n.x, Y0 + n.y)
        k = n.item.get("callout")
        if k:
            if n.kind in TEXT_LIKE:
                s.num(X0 + n.x - 26, Y0 + n.y - 3, k)
            else:
                s.num(X0 + n.x - 10, Y0 + n.y - 10, k)


def _boxes(nodes: list[Node], ox: float, oy: float):
    for n in nodes:
        if n.kind in ("arrow", "callout") or not n.w:
            continue
        yield n, ox + n.x, oy + n.y


def _contains(a, b) -> bool:
    return a[0] <= b[0] + 1 and a[1] <= b[1] + 1 and a[2] >= b[2] - 1 and a[3] >= b[3] - 1


def _overlaps(nodes: list[Node], c: Ctx) -> None:
    rects = [(n, (n.x, n.y, n.x + n.w, n.y + n.h)) for n in nodes if n.kind not in ("arrow", "callout") and n.w and n.h]
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            (a, ra), (b, rb) = rects[i], rects[j]
            inter = ra[0] < rb[2] - 2 and rb[0] < ra[2] - 2 and ra[1] < rb[3] - 2 and rb[1] < ra[3] - 2
            if inter and not _contains(ra, rb) and not _contains(rb, ra):
                c.warnings.append(f"{b.path} ({b.kind} {b.label!r}) overlaps {a.path} ({a.kind} {a.label!r}); move one, or leave y out so they stack")
    for n in nodes:
        if n.kids:
            _overlaps(n.kids, c)


def _seed_of(title: str) -> int:
    return zlib.crc32(title.encode("utf-8")) % (2**31 - 1) + 1


def compile_spec(spec: dict) -> tuple[Doc, list[str]]:
    """Check, lay out and draw. Returns the Doc (call .save(path)) and the warnings. Raises SpecError with every error found."""
    errs = check_spec(spec)
    if errs:
        raise SpecError(errs)
    d = Doc(spec.get("seed") or _seed_of(spec["title"]))
    d.text(0, -70, spec["title"], fs=36, family=1, color=INK)
    errors: list[str] = []
    warnings: list[str] = []
    y = 0.0
    for fi, fr in enumerate(spec["frames"]):
        fp = f"frames[{fi}]"
        c = Ctx(d, errors, warnings)
        W = fr.get("width", 1000)
        app = fr.get("chrome", "none") == "app"
        ox, oy_ = (180, 76) if app else (36, 24)
        nodes, bottom = _flow(fr["items"], fp + ".items", W - ox - 24, c)
        H = fr.get("height") or max(520 if app else 200, round(oy_ + bottom + 40))
        content = (150 if app else 0, 60 if app else 0, W, H)
        for n, ax, ay in _boxes(nodes, ox, oy_):
            if ax < content[0] - 1 or ay < content[1] - 1 or ax + n.w > content[2] + 1 or ay + n.h > content[3] + 1:
                warnings.append(f"{n.path} ({n.kind} {n.label!r}) runs outside the {'content area' if app else 'frame'} ({round(ax)},{round(ay)} to {round(ax + n.w)},{round(ay + n.h)}; the frame is {W} x {H}); make it narrower, or the frame wider or taller")
        _overlaps(nodes, c)
        for a in c.arrows:
            it = a.item
            for end in ("from", "to"):
                if it[end] not in c.box_paths:
                    errors.append(f"{a.path}.{end}: no box has the id {it[end]!r} (the boxes are: {', '.join(sorted(c.box_paths)) or 'none'})")
        if errors:
            continue
        s = new_frame(d, 0, y, W, H, fr["name"])
        if app:
            shell2(s, W, H, fr.get("active", "Review queue"), lens=fr.get("lens", 0))
        _draw(nodes, s, ox, oy_, c)
        for a in c.arrows:
            it = a.item
            ea, eb, sa, sb = c.els[it["from"]], c.els[it["to"]], it.get("from_side", "r"), it.get("to_side", "l")
            d.connect(ea, eb, sa, sb, label=it.get("label"), dash=it.get("dash", False))
            if it.get("label"):
                (ax_, ay_), (bx_, by_) = _anchor(ea, sa), _anchor(eb, sb)
                run, need = abs(ax_ - bx_) + abs(ay_ - by_), len(it["label"]) * 8 + 36
                if run < need:
                    warnings.append(f"{a.path}: the label {it['label']!r} needs about {need} px of line but {it['from']} to {it['to']} is {round(run)} px long; move the boxes apart, or shorten the label")
        ends: dict[tuple[str, str], list[Node]] = {}           # two labelled arrows that meet one side of one box run together there, and a label can land on the other's line
        for a in c.arrows:
            if a.item.get("label"):
                for end, side in (("from", "r"), ("to", "l")):
                    ends.setdefault((a.item[end], a.item.get(end + "_side", side)), []).append(a)
        for (box, side), group in ends.items():
            if len(group) > 1:
                warnings.append(f"{', '.join(a.path for a in group)}: {len(group)} labelled arrows meet at the {SIDE_NAMES[side]} side of {box}, so their lines run together and a label can sit on another arrow; "
                                "end them on different sides (from_side, to_side), or label only one of them")
        d.frame_end()
        want = set(range(1, len(fr.get("notes", [])) + 1))
        have = set(c.callouts)
        if not have <= want:
            warnings.append(f"{fp}: callout {', '.join(map(str, sorted(have - want)))} has no note (notes are numbered from 1)")
        if want - have:
            warnings.append(f"{fp}: note {', '.join(map(str, sorted(want - have)))} has no callout pointing at it")
        nb = notes(d, W + 40, y, list(enumerate(fr.get("notes", []), 1)), title="Notes") if fr.get("notes") else y
        y += max(H, nb - y) + 80
    if errors:
        raise SpecError(errors, warnings)
    return d, warnings


# ------------------------------------------------------------------------------------- schema, vocabulary and example, from the table

def _field_schema(kind: str, opt: dict) -> dict:
    lim = lambda o: {k: v for k, v in (("minimum", o.get("lo")), ("maximum", o.get("hi"))) if v is not None}   # noqa: E731
    if kind == "str":
        return {"type": "string", "pattern": "\\S", "maxLength": opt.get("maxlen", 400)}
    if kind == "int":
        return {"type": "integer", **lim(opt)}
    if kind == "num":
        return {"type": "number", **lim(opt)}
    if kind == "bool":
        return {"type": "boolean"}
    if kind == "enum":
        return {"enum": opt["values"]}
    if kind == "id":
        return {"type": "string", "pattern": f"^{ID_RE.pattern}$"}
    if kind == "ypos":
        return {"oneOf": [{"type": "integer", **lim(opt)}, {"const": "same"}]}
    if kind == "strs":
        return {"type": "array", "minItems": 1, "maxItems": opt.get("maxn", 50), "items": {"type": "string", "pattern": "\\S", "maxLength": opt.get("maxlen", 400)}}
    if kind == "ints":
        return {"type": "array", "minItems": 1, "maxItems": opt.get("maxn", 50), "items": {"type": "integer", **lim(opt)}}
    if kind == "rows":
        cell = {"oneOf": [{"type": "string", "maxLength": 300}, {"type": "object", "additionalProperties": False, "required": ["text"], "properties": {"text": {"type": "string"}, "tone": {"enum": TONES}}}]}
        return {"type": "array", "minItems": 1, "maxItems": opt.get("maxn", 60), "items": {"type": "array", "minItems": 1, "items": cell}}
    if kind == "checks":
        return {"type": "array", "minItems": 1, "maxItems": opt.get("maxn", 30), "items": {"type": "object", "additionalProperties": False, "required": ["state", "text"], "properties": {"state": {"enum": STATES}, "text": {"type": "string", "pattern": "\\S"}}}}
    if kind == "items":
        return {"type": "array", "maxItems": MAX_ITEMS, "items": {"$ref": "#/$defs/item"}}
    if kind == "frames":
        return {"type": "array", "minItems": 1, "maxItems": MAX_FRAMES, "items": {"$ref": "#/$defs/frame"}}
    raise AssertionError(kind)


def _obj(fields: list, extra_const: dict | None = None, title: str = "") -> dict:
    props = {f[0]: {**_field_schema(f[1], f[3]), "description": f[4]} for f in fields}
    req = [f[0] for f in fields if f[2]]
    if extra_const:
        props = {**{k: {"const": v} for k, v in extra_const.items()}, **props}
        req = list(extra_const) + req
    o: dict[str, Any] = {"type": "object", "additionalProperties": False, "properties": props, "required": req}
    if title:
        o["description"] = title
    return o


def schema() -> dict:
    defs: dict[str, Any] = {"item": {"oneOf": [{"$ref": f"#/$defs/{t}"} for t in ITEMS]}, "frame": _obj(FRAME_FIELDS, title="One screen or diagram.")}
    for t, spec in ITEMS.items():
        defs[t] = _obj(fields_of(t), {"type": t}, spec["doc"])
    out = _obj(BOARD_FIELDS, title="A board for Excalidraw, described as data. Compile it with excalidraw_generator/board_spec.py.")
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": "https://github.com/gitSITTI/Avana02/excalidraw_generator/board_spec.schema.json", "title": "reqin-board/1", **out, "$defs": defs}


LAYOUT_RULES = [
    "Items are placed top to bottom, with a 14 px gap, unless they say where they go.",
    "`x` is the left edge (default 0). `y` is the top edge: leave it out to go below everything so far, give `\"same\"` to sit level with the previous item (this is how two columns are made), or give a number for a fixed position.",
    "A `card` holds items of its own, laid out the same way inside it; `x` and `y` inside a card are measured from the card's inside corner. A card grows to fit its items unless you give `h`.",
    "With `chrome` `app`, positions are measured from the content area to the right of the sidebar; a frame is 1000 px wide unless you say otherwise, so about 800 px is usable. With `chrome` `none` there is a 36 px margin.",
    "Give any item `callout: 1` and a red number 1 is drawn beside it; the first note beside the frame explains it. Every note should have a callout, and every callout a note.",
    "Colours are never written. Use `tone`: white, grey, green, amber, red, blue or violet. Meaning never rests on colour alone: a chip or a mark always carries a word.",
    "Give each labelled arrow its own side of a box (`from_side`, `to_side`): two labelled arrows that meet at one side run together and a label can land on the other's line.",
    "The compiler warns when something runs outside its frame, two items overlap, a label may not fit, labelled arrows meet at one side of a box, or a callout and a note do not pair up. Fix every warning; they are mistakes.",
]


def describe() -> str:
    def fld(f: tuple) -> str:
        name, kind, req, opt, doc = f
        extra = f" Values: {', '.join(map(str, opt['values']))}." if kind == "enum" else ""
        return f"- `{name}`{' (required)' if req else ''} — {doc.rstrip('.')}.{extra}"
    out = [f"# The board format, `{FORMAT}`", "", "A board is `{\"format\": \"%s\", \"title\": ..., \"seed\": ..., \"frames\": [...]}`. Every field is optional unless it says required. Fields not listed are refused." % FORMAT, "",
           "## Layout", ""] + [f"- {r}" for r in LAYOUT_RULES] + ["", "## A frame (one screen or diagram)", ""]
    out += [fld(f) for f in FRAME_FIELDS]
    out += ["", "## Items", "", "Every item has `type` plus its own fields, and (except where a type says otherwise) these three: " + "; ".join(f"`{f[0]}` — {f[4]}" for f in COMMON) + ".", ""]
    for t, spec in ITEMS.items():
        out += [f"### `{t}`", spec["doc"], ""]
        out += [fld(f) for f in spec["fields"]]
        out.append("")
    return "\n".join(out)


EXAMPLE = {
    "format": FORMAT, "title": "99 · Example board", "seed": 9901,
    "frames": [
        {"name": "99.1 · A review screen", "width": 1000, "chrome": "app", "active": "Review queue", "lens": 0, "items": [
            {"type": "heading", "text": "Review cluster CL-017", "size": 24, "callout": 1},
            {"type": "card", "w": 440, "items": [
                {"type": "caps", "text": "THE TWO WORDINGS"},
                {"type": "text", "text": "The pump shall start within five seconds of the command. The controller shall start the pump within 5 s of receiving the start command.", "w": 400},
                {"type": "mark", "kind": "mech", "label": "found by the mechanical comparison"}]},
            {"type": "table", "widths": [120, 160, 160], "head": ["Source", "Wording", "Number"], "rows": [["SysML", "within five seconds", {"text": "5 s", "tone": "green"}], ["DOORS", "within 5 s", {"text": "5 s", "tone": "green"}]], "callout": 2},
            {"type": "checklist", "w": 440, "items": [{"state": "Pass", "text": "Numbers and units agree"}, {"state": "Needs you", "text": "Choose the surviving wording"}]},
            {"type": "button", "label": "Accept the merge", "primary": True, "x": 0},
            {"type": "button", "label": "Keep both", "y": "same", "x": 190}],
         "notes": ["The first thing a reviewer sees is what the cluster is, so the heading names it.", "The table shows the evidence before the choice, so the reviewer does not decide from the summary alone."]},
        {"name": "99.2 · How a decision flows", "width": 1000, "chrome": "none", "items": [
            {"type": "box", "id": "read", "label": "Read and normalise", "w": 170, "h": 60, "tone": "blue"},
            {"type": "box", "id": "compare", "label": "Mechanical comparison", "w": 170, "h": 60, "tone": "green", "x": 280, "y": "same"},
            {"type": "box", "id": "decide", "label": "A person decides", "w": 170, "h": 60, "tone": "amber", "x": 560, "y": "same", "callout": 1},
            {"type": "arrow", "from": "read", "to": "compare", "label": "records"},
            {"type": "arrow", "from": "compare", "to": "decide", "label": "draft"}],
         "notes": ["The person decides last: everything before this step is a draft."]}]}


# --------------------------------------------------------------------------------------------------------------- the CLI

def _load(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise SystemExit(f"cannot read {path}: {e.strerror or e}")
    except ValueError as e:
        raise SystemExit(f"{path} is not valid JSON: {e}")


def main(argv: list[str] | None = None) -> int:
    a = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in a
    strict = "--strict" in a
    a = [x for x in a if x not in ("--json", "--strict")]
    png = scale = None
    def value_of(flag: str) -> str | None:                   # the word after a flag, which must be there and must not be another flag
        if flag not in a:
            return None
        i = a.index(flag)
        if i + 1 >= len(a) or a[i + 1].startswith("--"):
            raise SystemExit(f"{flag} needs a value after it, for example: {flag} picture.png" if flag != "--scale" else "--scale needs a number after it, for example: --scale 2")
        v = a[i + 1]
        del a[i:i + 2]
        return v
    for flag in ("--png", "--svg"):                           # a raster picture (with --scale) or a vector one
        png = value_of(flag) or png
    scale = value_of("--scale")
    cmd = a[0] if a else ""
    if cmd == "describe":
        print(describe())
        return 0
    if cmd == "example":
        print(json.dumps(EXAMPLE, indent=1, ensure_ascii=False))
        return 0
    if cmd == "schema":
        text = json.dumps(schema(), indent=1, ensure_ascii=False) + "\n"
        if len(a) > 1:
            Path(a[1]).write_text(text, encoding="utf-8")
            print(f"wrote {a[1]}")
        else:
            print(text, end="")
        return 0
    if cmd not in ("check", "build") or len(a) < 2 or (cmd == "build" and len(a) < 3):
        print(__doc__)
        return 2

    def report(ok: bool, errors: list[str], warnings: list[str], extra: dict | None = None) -> int:
        if as_json:
            print(json.dumps({"ok": ok, "errors": errors, "warnings": warnings, **(extra or {})}, ensure_ascii=False))
        else:
            for e in errors:
                print("ERROR  " + e)
            for w in warnings:
                print("WARN   " + w)
            if ok:
                print(f"ok{' (' + extra['summary'] + ')' if extra and extra.get('summary') else ''}" + (f", {len(warnings)} warning(s)" if warnings else ""))
        return 0 if ok else 1

    spec = _load(a[1])
    try:
        if cmd == "check":
            errs = check_spec(spec)
            if errs:
                return report(False, errs, [])
            d, warns = compile_spec(spec)                      # layout problems only show when it is laid out
            return report(not (strict and warns), [], warns, {"summary": f"{len(spec['frames'])} frame(s), {len(d.els)} elements"})
        d, warns = compile_spec(spec)
    except SpecError as e:
        return report(False, e.errors, e.warnings)
    if strict and warns:
        return report(False, [], warns)
    d.save(a[2])
    from validate import check as validate_file
    v = validate_file(a[2], verbose=False)
    if not v["ok"]:
        return report(False, [f"the file does not pass validate.py: {v}"], warns)
    summary = f"{v['frames']} frame(s), {v['elements']} elements, dup {v['dup']} dangling {v['dangling']} frame-order {v['order']} outside {v['outside']}"
    if png:
        import subprocess
        r = subprocess.run([sys.executable, str(HERE / "render.py"), a[2], png] + ([scale] if scale else []), capture_output=True, text=True)
        if r.returncode:
            warns.append("could not render a picture: " + (r.stderr or r.stdout).strip().splitlines()[-1][:160] + " (see EXCALIDRAW_GUIDE.md, section 2)")
        else:
            summary += f"; picture {png}"
    return report(True, [], warns, {"summary": summary, "file": a[2]})


if __name__ == "__main__":
    sys.exit(main())
