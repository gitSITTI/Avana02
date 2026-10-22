#!/usr/bin/env python3
"""Bring parts of our design into your app, one question at a time, with pictures before anything is written.

    python3 design/adopt_design/scripts/adopt.py init    SESSION --page PAGE [--setup STEP ...]     read your page (opens it in a browser) and start a session folder
    python3 design/adopt_design/scripts/adopt.py next    SESSION                                    the question to ask the person now, with its pictures and the exact command that records the answer
    python3 design/adopt_design/scripts/adopt.py answer  SESSION QUESTION-ID CHOICE                 record the answer (several choices: a,b,c) and print the next question
    python3 design/adopt_design/scripts/adopt.py set     SESSION ROLE VALUE                         correct a value read from your page (a colour as #RRGGBB, a size as 14px, ...)
    python3 design/adopt_design/scripts/adopt.py back    SESSION [--to QUESTION-ID]                 take back the last answer, or everything from that question on
    python3 design/adopt_design/scripts/adopt.py status  SESSION                                    what has been decided so far, in words
    python3 design/adopt_design/scripts/adopt.py preview SESSION                                    draw the pictures of the whole result (needs every question answered)
    python3 design/adopt_design/scripts/adopt.py approve SESSION --said "the person's words"        record the person's yes to exactly what the pictures show
    python3 design/adopt_design/scripts/adopt.py build   SESSION                                    write the code files (refused until approved, and refused if anything changed since)
    python3 design/adopt_design/scripts/adopt.py verify  SESSION --page PAGE [--setup STEP ...]     read the changed page again and say which decisions it shows

Everything that happens in what order is decided here, from the answers so far, so the one who runs this only has to run the command it printed, read the question to the person in the
words given, and record the answer. The questions are a plain function of the answers: the same answers always give the same next question (tools/test_adopt_design.py checks that).

What it does not do: it does not look at a picture (colours and sizes are the numbers the browser computed); it does not change your app (build writes files into SESSION/out/ for you
or your tools to copy in); nothing is sent anywhere. Pictures and reading a page need Playwright with Chromium:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import C, KIT, REPO, TOKENS_CSS, css_vars, digest, read_json, write_json  # noqa: E402
import catalog as CAT  # noqa: E402
import make_frames as MF  # noqa: E402
import roles as R  # noqa: E402

FORMAT = "reqin-adopt/1"
CMD = "python3 " + shlex.quote(os.path.relpath(Path(__file__).resolve()))          # the command as it can be typed from where this was started, so a printed command can be copied


def cmd(verb: str, *args: str) -> str:
    return " ".join([CMD, verb, *args])

AREAS = [a["id"] for a in R.ROLES["areas"]]
AREA_BY = {a["id"]: a for a in R.ROLES["areas"]}
SOURCE_LABEL = {"mine": "Keep yours", "ours": "Use ours", "square": "Square corners (no rounding)", "none": "No shadow"}
ASPECT_WORDS = {"palette": "colours", "type": "fonts and sizes", "corners": "corner roundness", "depth": "shadow", "density": "height of buttons and inputs"}
KEY_ROLES = {"palette": ["accent", "page", "surface", "ink"], "type": ["font-body", "size-body", "size-title", "font-mono"], "corners": ["radius-control", "radius-panel", "radius-chip"],
             "depth": ["shadow-card"], "density": ["control-height"]}
ASPECT_ASK = {"palette": "Which colours should the {n} use?", "type": "Which fonts and text sizes should the {n} use?", "corners": "How round should the corners of the {n} be?",
              "depth": "Which shadow should the {n} have?", "density": "How tall should the buttons and inputs in the {n} be?"}
RADIUS = R.roles_of_area("corners")


# ------------------------------------------------------------------------------------------------ the session folder
def sess_path(session: str) -> Path:
    return Path(session)


def load_session(session: str) -> dict:
    f = sess_path(session) / "session.json"
    if not f.is_file():
        raise SystemExit("no session here: %s (start one with: %s)" % (session, cmd("init", shlex.quote(session), "--page", "PAGE")))
    return read_json(f)


def save_session(session: str, s: dict) -> None:
    write_json(sess_path(session) / "session.json", s)


def _forget_later_steps(s: dict) -> None:
    """A changed answer makes the pictures, the person's approval and what was built out of date."""
    for k in ("preview", "approved", "built"):
        s.pop(k, None)


def load_index(session: str) -> dict:
    return read_json(sess_path(session) / "mine" / "index.json")


# ------------------------------------------------------------------------------------------------ the decisions, as a function of the answers
class Model:
    """Everything that follows from the answers so far. Pure: it reads design/tokens.css, the catalog and the page index, and writes nothing."""

    def __init__(self, ix: dict, answers: dict, overrides: dict):
        self.ix, self.A, self.ov = ix, answers, overrides
        text = TOKENS_CSS.read_text(encoding="utf-8")
        self.ours_vars = css_vars(text)
        self.ours = R.read_ours(text)
        self.mine = ix["roles"]
        self.parts = CAT.all_parts()
        self.bp = {p["id"]: p for p in self.parts}
        self._nav = read_json(REPO / "design" / "navigation.json")
        self.screens = CAT.screens(self._nav, (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8"))
        self.bs = {s["id"]: s for s in self.screens}
        self.frame_spec = MF.load_spec()["screens"]

    # -- values
    def ours_value(self, role):
        return self.ours[role]["value"]

    def mine_value(self, role):
        """(value, where it came from) for a role as the person's page has it, after what they corrected or declined."""
        if role in self.ov:
            return self.ov[role], "set by you"
        v = (self.mine.get(role) or {}).get("value")
        if v is None:
            return self.ours_value(role), "ours, because your page has nothing that plays this part"
        if role in (self.A.get("guesses") or []) and self.A.get("fix:" + role) == "ours":
            return self.ours_value(role), "ours, because you said the guess was wrong"
        conf = (self.mine.get(role) or {}).get("confidence", "read")
        if conf == "guess":
            return v, "your page (a guess%s)" % (", you said it is right" if "guesses" in self.A and role not in self.A["guesses"] else ", not confirmed")
        return v, "your page (read)"

    def value(self, role, source):
        if source == "mine":
            return self.mine_value(role)[0]
        if source == "ours":
            return self.ours_value(role)
        if source == "square":
            return "0px" if role in RADIUS else self.mine_value(role)[0]
        if source == "none":
            return "none" if role == "shadow-card" else self.mine_value(role)[0]
        raise KeyError(source)

    def area_source(self, area):
        st = self.A.get("stance")
        if st == "ours":
            return "ours"
        if st == "choose":
            return self.A.get("area:" + area, "mine")
        return "mine"

    def theme_values(self):
        return {r: self.value(r, self.area_source(R.AREA_OF[r])) for r in R.ROLE_IDS}

    def theme_tokens(self):
        return R.tokens_for(self.theme_values(), self.ours_vars)

    # -- parts
    def selected_parts(self):
        sel = list(self.A.get("parts") or [])
        grow = True
        while grow:
            grow = False
            for pid in list(sel):
                for n in self.bp[pid].get("needs", []):
                    if n not in sel:
                        sel.append(n)
                        grow = True
        return [p["id"] for p in self.parts if p["id"] in sel]

    def added_by_need(self):
        asked = set(self.A.get("parts") or [])
        return [p for p in self.selected_parts() if p not in asked]

    def aspects_of(self, pid):
        p = self.bp[pid]
        return list(p["areas"]) + (["icons"] if p.get("icons") else [])

    def changes(self, pid):
        return [a for a in self.aspects_of(pid) if a in (self.A.get("change:" + pid) or [])]

    def aspect_source(self, pid, aspect):
        return self.A.get("aspect:%s:%s" % (pid, aspect), "theme") if aspect in self.changes(pid) else "theme"

    def part_values(self, pid, replace: dict | None = None):
        vals = self.theme_values()
        for area in self.bp[pid]["areas"]:
            s = (replace or {}).get(area) or self.aspect_source(pid, area)
            if s != "theme":
                for r in R.roles_of_area(area):
                    vals[r] = self.value(r, s)
        return vals

    def part_tokens(self, pid, replace: dict | None = None):
        return R.tokens_for(self.part_values(pid, replace), self.ours_vars)

    def part_token_diff(self, pid):
        base, mine = self.theme_tokens(), self.part_tokens(pid)
        return {t: v for t, v in mine.items() if base.get(t) != v}

    def icons_off(self, pid):
        return self.aspect_source(pid, "icons") == "remove"

    # -- screens
    def rows_of(self, sid):
        return [{"id": "r%d" % (i + 1), **row} for i, row in enumerate(self.bs[sid]["rows"])]

    def selected_screens(self):
        sel = self.A.get("screens") or []
        return [s["id"] for s in self.screens if s["id"] in sel]

    def frames_of(self, sid):
        """The frames of a screen (design/adopt_design/frames_spec.json), numbered in the order the picture shows them."""
        return [{"n": i, **f} for i, f in enumerate(self.frame_spec.get(self.bs[sid]["screen"], []), 1)]

    def frames_kept(self, sid):
        frames = self.frames_of(sid)
        if "frames:" + sid not in self.A:
            return frames
        keep = set(self.A["frames:" + sid])
        return [f for f in frames if f["id"] in keep]

    def rows_unpictured(self, sid):
        """Pieces of the screen's data map that no frame holds: the sample does not draw them in this state (they need a click, another person or a file)."""
        held = {r for f in self.frames_of(sid) for r in f["rows"]}
        return [r for r in self.rows_of(sid) if r["id"] not in held]

    def rows_kept(self, sid):
        """Pieces the person keeps: those held by a frame they kept, and those the sample does not draw that they chose (all of them until they are asked)."""
        held = {r for f in self.frames_kept(sid) for r in f["rows"]}
        unpictured = self.rows_unpictured(sid)
        keep_un = set(self.A["rows:" + sid]) if "rows:" + sid in self.A else {r["id"] for r in unpictured}
        return [r for r in self.rows_of(sid) if r["id"] in held or r["id"] in keep_un]

    def frame_kinds(self, sid, frame):
        """Where a frame's content would come from in the person's app, as keys of catalog.KIND_WORDS: the kinds of the pieces it holds, or "unlisted" when it holds none."""
        rows = {r["id"]: r for r in self.rows_of(sid)}
        found = {k for rid in frame["rows"] for k in rows[rid]["kinds"]}
        return [k for k in CAT.KIND_WORDS if k in found] or ["unlisted"]

    # -- identity of the decisions
    def fingerprint(self):
        return digest({"answers": self.A, "overrides": self.ov, "mine": self.mine, "ours": self.ours_vars, "parts": [p["id"] for p in self.parts], "screens": [s["id"] for s in self.screens]})


# ------------------------------------------------------------------------------------------------ the questions
def _opt(i, label, detail=""):
    return {"id": i, "label": label, "detail": detail}


def summary(m: Model, area: str, source: str) -> str:
    return "; ".join("%s %s" % (R.BY_ID[r]["label"].lower(), R.value_name(r, m.value(r, source))) for r in KEY_ROLES[area])


def q_stance(m):
    return {"id": "stance", "kind": "single", "say": "Do you want to keep your own theme (colours, fonts, corner shapes) and add our designs on top of it, take our whole theme, or decide area by area?",
            "options": [_opt("keep", "Keep my theme (recommended)", "everything we add is drawn in your colours, fonts and corners"),
                        _opt("ours", "Use our theme", "our colours, fonts, corners, shadows and sizes on everything we add"),
                        _opt("choose", "Decide area by area", "I will ask about colours, type, corners, shadows and size of controls, one at a time")],
            "picture": {"kind": "theme"}}


def q_area(m, area):
    a = AREA_BY[area]
    return {"id": "area:" + area, "kind": "single", "say": a["ask"],
            "options": [_opt(o, SOURCE_LABEL[o], summary(m, area, o)) for o in a["options"]], "picture": {"kind": "area", "area": area}}


def guess_roles(m: Model) -> list:
    return [r for r in R.ROLE_IDS if (m.mine.get(r) or {}).get("confidence") == "guess" and m.mine[r].get("value") is not None and m.area_source(R.AREA_OF[r]) == "mine" and r not in m.ov]


def q_guesses(m, roles):
    opts = [_opt(r, "%s: %s" % (R.BY_ID[r]["label"], R.value_name(r, m.mine[r]["value"])), "guessed: " + m.mine[r]["how"]) for r in roles] + [_opt("none", "None, all of these are right")]
    return {"id": "guesses", "kind": "multi",
            "say": "I could not read these values straight from your page, so I guessed them. The picture shows each one. Which are wrong? Pick any, or none.",
            "options": opts, "picture": {"kind": "guesses", "roles": roles}}


def q_fix(m, role):
    return {"id": "fix:" + role, "kind": "single",
            "say": "You said the guess for %s is wrong. I can use ours (%s) for it, or you can tell me the right value." % (R.BY_ID[role]["plain"], R.value_name(role, m.ours_value(role))),
            "options": [_opt("ours", "Use ours instead", R.value_name(role, m.ours_value(role)))],
            "help": "To give the right value, run this instead: %s VALUE (for example %s)" % (cmd("set", "SESSION", role), {"colour": "#1A4DB5", "length": "14px", "font": "\"Inter\", sans-serif", "shadow": "none"}[R.BY_ID[role]["kind"]]),
            "picture": None}


def q_parts(m):
    opts = [_opt(p["id"], p["name"], p["what"]) for p in m.parts] + [_opt("all", "All of them"), _opt("none", "None of them")]
    return {"id": "parts", "kind": "multi", "say": "Which of our parts would you like in your app? Pick any, or none. The picture shows each one drawn in the theme you chose.", "options": opts, "picture": {"kind": "parts"}}


def q_change(m, pid):
    p = m.bp[pid]
    asp = [_opt(a, "The " + ("icons" if a == "icons" else ASPECT_WORDS[a])) if a != "icons" else _opt(a, "Take out " + p["icons"]["label"]) for a in m.aspects_of(pid)]
    return {"id": "change:" + pid, "kind": "multi", "say": "The %s: %s Would you change anything about it for your app? Pick what you would change, or none." % (p["name"].lower(), p["what"]),
            "options": asp + [_opt("none", "Nothing, use it as it is drawn")], "picture": {"kind": "part", "part": pid}}


def aspect_options(m: Model, pid: str, aspect: str) -> list:
    if aspect == "icons":
        return [_opt("keep", "Keep them"), _opt("remove", "Take them out")]
    theme_vals = m.part_values(pid, {aspect: "theme"})
    opts = [_opt("theme", "Same as the rest of your result", summary_values(m, aspect, theme_vals))]
    for s in AREA_BY[aspect]["options"]:
        vals = {r: m.value(r, s) for r in R.roles_of_area(aspect)}
        if all(R.same(r, vals[r], theme_vals[r]) for r in vals):          # an option that looks the same as the default is not a choice
            continue
        opts.append(_opt(s, SOURCE_LABEL[s], summary_values(m, aspect, {**theme_vals, **vals})))
    return opts


def summary_values(m, area, vals):
    return "; ".join("%s %s" % (R.BY_ID[r]["label"].lower(), R.value_name(r, vals[r])) for r in KEY_ROLES[area])


def q_aspect(m, pid, aspect):
    p = m.bp[pid]
    say = ("The %s has %s. Keep them or take them out?" % (p["name"].lower(), p["icons"]["label"])) if aspect == "icons" else ASPECT_ASK[aspect].format(n=p["name"].lower())
    return {"id": "aspect:%s:%s" % (pid, aspect), "kind": "single", "say": say, "options": aspect_options(m, pid, aspect), "picture": {"kind": "strip", "part": pid, "aspect": aspect}}


def q_screens(m):
    opts = [_opt(s["id"], s["name"], "%d frame%s, %d piece%s listed in the data map" % (len(m.frames_of(s["id"])), "" if len(m.frames_of(s["id"])) == 1 else "s", len(s["rows"]), "" if len(s["rows"]) == 1 else "s"))
            for s in m.screens] + [_opt("none", "None of them")]
    return {"id": "screens", "kind": "multi", "say": "Which of our screens would you like a build brief for? The picture shows the top of each, in our colours and with made-up sample content. Each brief lists what is on the screen, "
            "where its content comes from and where it leads. Pick any, or none.", "options": opts, "picture": {"kind": "screens"}}


def frame_detail(m, sid, f):
    kinds = m.frame_kinds(sid, f)
    return "content: " + ", ".join(CAT.KIND_WORDS[k] for k in kinds) + ("; no source yet, so a built screen shows an empty state, not a value" if "none" in kinds else "")


def q_frames(m, sid):
    s = m.bs[sid]
    opts = [_opt(f["id"], "%d. %s" % (f["n"], f["label"]), frame_detail(m, sid, f)) for f in m.frames_of(sid)] + [_opt("all", "All of them"), _opt("none", "None of them")]
    return {"id": "frames:" + sid, "kind": "multi",
            "say": "The \"%s\" screen is cut into the frames in the picture, drawn in our colours with made-up sample content. Which do you want in your app? Anything you leave out is dropped from the brief. "
                   "Under each frame the picture says where its content would come from in your app." % s["name"],
            "options": opts, "picture": {"kind": "frames", "screen": sid}}


def q_rows(m, sid):
    s = m.bs[sid]
    return {"id": "rows:" + sid, "kind": "multi",
            "say": "The sample does not draw these pieces of the \"%s\" screen in the picture: they need a click, another person or a file. Which do you want? Anything you leave out is dropped from the brief." % s["name"],
            "options": [_opt(r["id"], r["part"], r["source"] if len(r["source"]) <= 100 else r["source"][:97].rstrip() + "...") for r in m.rows_unpictured(sid)] + [_opt("all", "All of them")], "picture": None}


def next_question(m: Model):
    """The one question to ask now, or None when everything is decided. Depends only on the answers."""
    A = m.A
    if "stance" not in A:
        return q_stance(m)
    if A["stance"] == "choose":
        for area in AREAS:
            if "area:" + area not in A:
                return q_area(m, area)
    gr = guess_roles(m)
    if gr and "guesses" not in A:
        return q_guesses(m, gr)
    for role in A.get("guesses") or []:
        if role not in m.ov and "fix:" + role not in A:
            return q_fix(m, role)
    if "parts" not in A:
        return q_parts(m)
    for pid in m.selected_parts():
        if "change:" + pid not in A:
            return q_change(m, pid)
        for asp in m.changes(pid):
            if "aspect:%s:%s" % (pid, asp) not in A:
                return q_aspect(m, pid, asp)
    if m.screens and "screens" not in A:
        return q_screens(m)
    for sid in m.selected_screens():
        if m.frames_of(sid) and "frames:" + sid not in A:
            return q_frames(m, sid)
        if m.rows_unpictured(sid) and "rows:" + sid not in A:
            return q_rows(m, sid)
    return None


def parse_answer(q: dict, raw: str):
    """The stored form of an answer, or ValueError saying what the choices are."""
    raw = (raw or "").strip()
    ids = [o["id"] for o in q["options"]]
    if q["kind"] == "single":
        if raw not in ids:
            raise ValueError("%r is not one of the choices: %s" % (raw, ", ".join(ids)))
        return raw
    toks = [t.strip() for t in raw.split(",") if t.strip()]
    if not toks:
        raise ValueError("give at least one choice, or none: %s" % ", ".join(ids))
    for t in toks:
        if t not in ids:
            raise ValueError("%r is not one of the choices: %s" % (t, ", ".join(ids)))
    real = [i for i in ids if i not in ("all", "none")]
    if "none" in toks:
        if len(toks) > 1:
            raise ValueError("none cannot be combined with other choices")
        return []
    if "all" in toks:
        return real
    return [i for i in real if i in toks]


def check_value(role: str, raw: str) -> str:
    """A corrected value for a role, or ValueError. Colours become #RRGGBB, lengths px, fonts and shadows must be plain CSS."""
    kind = R.BY_ID[role]["kind"]
    s = (raw or "").strip()
    if re.search(r"[;{}<>]|url\(|expression|@import|\\", s) or not s:
        raise ValueError("that is not a plain value")
    if kind == "colour":
        p = C.parse_css(s) if not re.fullmatch(r"#[0-9A-Fa-f]{3}", s) else C.parse_css("#" + "".join(ch * 2 for ch in s[1:]))
        if not p:
            raise ValueError("%r is not a colour: write it as #RRGGBB" % s)
        return p[0]
    if kind == "length":
        m = re.fullmatch(r"(\d+(?:\.\d+)?)(px)?", s)
        if not m:
            raise ValueError("%r is not a length: write it in pixels, for example 14px" % s)
        return "%gpx" % float(m.group(1))
    return s


# ------------------------------------------------------------------------------------------------ pictures
def _fonts(*token_dicts):
    out = []
    for t in token_dicts:
        out += [t.get(k, "") for k in ("--sans", "--serif", "--mono")]
    return out


def draw_for(session: str, m: Model, q: dict):
    """Make the pictures a question refers to. Returns (list of files, list of notes)."""
    import render as RD
    pic = q.get("picture")
    if not pic:
        return [], []
    if not RD.available():
        return [], ["pictures not made: Playwright is not installed (pip install playwright && playwright install chromium). Describe the choices from the text."]
    out_dir = sess_path(session) / "pictures"
    fn = out_dir / (re.sub(r"[^A-Za-z0-9]+", "_", q["id"]).strip("_") + ".png")
    notes = []
    base = m.theme_tokens()
    with RD.Renderer() as r:
        if pic["kind"] == "theme":
            cols = [{"title": "Yours", "sub": "read from your page", "values": {k: v["value"] for k, v in m.mine.items()}, "conf": {k: v["confidence"] for k, v in m.mine.items()}},
                    {"title": "Ours", "sub": "design/tokens.css", "values": {k: v["value"] for k, v in m.ours.items()}}]
            res = r.draw(RD.theme_sheet_html(cols, r.base), fn, [c["values"].get("font-body") for c in cols] + [c["values"].get("font-mono") for c in cols])
        elif pic["kind"] == "guesses":
            res = r.draw(RD.samples_html([(ro, m.mine[ro]["value"]) for ro in pic["roles"]], r.base), fn, [m.mine[ro]["value"] for ro in pic["roles"] if R.BY_ID[ro]["kind"] == "font"], width=900)
        elif pic["kind"] == "area":
            area = pic["area"]
            cells = []
            for o in q["options"]:
                vals = m.theme_values()
                vals.update({rr: m.value(rr, o["id"]) for rr in R.roles_of_area(area)})
                cells.append((o["label"], R.tokens_for(vals, m.ours_vars), ""))
            res = r.draw(RD.strip_html(cells, RD.AREA_SAMPLE, r.base), fn, _fonts(*[c[1] for c in cells]), width=1300)
        elif pic["kind"] in ("screens", "frames"):
            res = draw_frames_picture(r, m, pic, fn, notes)
            if res is None:
                return [], notes
        elif pic["kind"] == "parts":
            body = "".join(RD.cell_html(p["name"], base, [p["id"]]) for p in m.parts)
            res = r.draw(RD.page_html(body, RD.parts_css([p["id"] for p in m.parts]), r.base), fn, _fonts(base), width=1300)
        elif pic["kind"] == "part":
            pid = pic["part"]
            res = r.draw(RD.page_html(RD.cell_html(m.bp[pid]["name"], m.part_tokens(pid), [pid]), RD.parts_css([pid]), r.base), fn, _fonts(m.part_tokens(pid)), width=1100)
        else:                                                           # strip: one picture per option of an aspect question
            pid, asp = pic["part"], pic["aspect"]
            cells, off = [], []
            for o in q["options"]:
                if asp == "icons":
                    tk, label = m.part_tokens(pid), o["label"]
                    cells.append((label, tk, ""))
                    if o["id"] == "remove":
                        off.append(len(cells) - 1)
                else:
                    cells.append((o["label"], m.part_tokens(pid, {asp: o["id"]}), ""))
            body = "".join(RD.cell_html(lb, tk, [pid], [pid] if (i in off or (asp != "icons" and m.icons_off(pid))) else [], nt) for i, (lb, tk, nt) in enumerate(cells))
            res = r.draw(RD.page_html(body, RD.parts_css([pid]), r.base), fn, _fonts(*[c[1] for c in cells]), width=1300)
    if res["stand_in"]:
        notes.append("this machine has no %s, so the picture shows a stand-in where that font is used; the real result will use the font" % ", ".join(res["stand_in"]))
    return [res["file"]], notes


def draw_frames_picture(r, m: Model, pic: dict, fn, notes: list):
    """The picture of our screens (a sheet to choose from) or of one screen cut into its frames. These are drawn from the pictures docs/images/frames/ holds (made by scripts/make_frames.py
    from the running prototype), not from the person's page. Returns the draw result, or None (with a note) when those pictures are missing or of another version of the prototype."""
    import render as RD
    problems = MF.index_problems()
    if not MF.INDEX.is_file():
        notes.append("the pictures of our screens are missing (%s). Describe the screens from the text." % problems[0])
        return None
    idx = read_json(MF.INDEX)
    if problems:
        notes.append("the pictures of our screens may be out of date: " + problems[0])
    if pic["kind"] == "screens":
        cells = []
        for s in m.screens:
            e = idx["screens"][s["screen"]]
            cells.append({"name": s["name"], "image": r.stage_file(MF.OUT / e["image"]), "width": e["width"], "n_frames": len(e["frames"]), "n_pieces": len(s["rows"])})
        res = r.draw(RD.screens_sheet_html(cells), fn, [], width=1300)
    else:
        sid = pic["screen"]
        e = idx["screens"][m.bs[sid]["screen"]]
        rows = {x["id"]: x for x in m.rows_of(sid)}
        boxes = {f["id"]: f["box"] for f in e["frames"]}
        frames = [{"id": f["id"], "label": f["label"], "box": boxes[f["id"]], "kinds": m.frame_kinds(sid, f), "pieces": [rows[x]["part"] for x in f["rows"]]} for f in m.frames_of(sid)]
        res = r.draw(RD.frames_sheet_html(m.bs[sid]["name"], r.stage_file(MF.OUT / e["image"]), e["width"], e["height"], frames), fn, [], width=1300)
    notes.append("these pictures are our screens with made-up content: they show what is on a screen, not what your data would look like there, and they are not drawn in your theme")
    return res


def describe(q: dict, session: str, files: list, notes: list, step: int) -> str:
    sq = shlex.quote(session)
    L = ["QUESTION %d (%s)" % (step, q["id"]), "", "Ask the person, in these words:", "  " + q["say"], ""]
    if q.get("help"):
        L += ["  (" + q["help"].replace("SESSION", sq) + ")", ""]
    L.append("Their choices:" if q["kind"] == "single" else "Their choices (any number, comma-separated, or none):")
    for o in q["options"]:
        L.append("  %-14s %s%s" % (o["id"], o["label"], (" - " + o["detail"]) if o["detail"] else ""))
    L.append("")
    if files:
        L.append("Show the person this picture before they answer: %s" % ", ".join(files))
    for n in notes:
        L.append("Note: " + n)
    L += ["", "When they have chosen, run:", "  " + cmd("answer", sq, shlex.quote(q["id"]), "CHOICE" if q["kind"] == "single" else "CHOICE[,CHOICE...]")]
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ commands
def model_of(session: str):
    s = load_session(session)
    return s, Model(load_index(session), s["answers"], s["overrides"])


def cmd_next(session: str, pictures: bool = True) -> int:
    s, m = model_of(session)
    q = next_question(m)
    if q is None:
        print("Every question is answered. Next, run:\n  " + cmd("preview", shlex.quote(session)))
        return 0
    files, notes = draw_for(session, m, q) if pictures else ([], [])
    print(describe(q, session, files, notes, len(s["answers"]) + 1))
    return 0


def cmd_answer(session: str, qid: str, raw: str, pictures: bool = True) -> int:
    s, m = model_of(session)
    q = next_question(m)
    if q is None:
        raise SystemExit("no question is waiting. Run: " + cmd("preview", shlex.quote(session)))
    if qid != q["id"]:
        raise SystemExit("the question waiting is %s, not %s. Run: %s" % (q["id"], qid, cmd("next", shlex.quote(session))))
    try:
        val = parse_answer(q, raw)
    except ValueError as e:
        raise SystemExit("not recorded: %s" % e)
    s["answers"][qid] = val
    _forget_later_steps(s)
    save_session(session, s)
    print("Recorded %s = %s.\n" % (qid, val if not isinstance(val, list) else (",".join(val) or "none")))
    return cmd_next(session, pictures)


def cmd_set(session: str, role: str, raw: str) -> int:
    s = load_session(session)
    if role not in R.BY_ID:
        raise SystemExit("no role %r. The roles are: %s" % (role, ", ".join(R.ROLE_IDS)))
    try:
        v = check_value(role, raw)
    except ValueError as e:
        raise SystemExit("not recorded: %s" % e)
    s["overrides"][role] = v
    s["answers"].pop("fix:" + role, None)
    _forget_later_steps(s)
    save_session(session, s)
    print("Recorded: %s is %s on your page." % (R.BY_ID[role]["plain"], v))
    return 0


def cmd_back(session: str, to: str | None) -> int:
    s = load_session(session)
    keys = list(s["answers"])
    if not keys:
        raise SystemExit("nothing to take back")
    if to:
        if to not in s["answers"]:
            raise SystemExit("%r has not been answered. Answered so far: %s" % (to, ", ".join(keys)))
        drop = keys[keys.index(to):]
    else:
        drop = keys[-1:]
    for k in drop:
        del s["answers"][k]
    _forget_later_steps(s)
    save_session(session, s)
    print("Took back: %s." % ", ".join(drop))
    return cmd_next(session)


def describe_decisions(m: Model) -> list:
    L = []
    st = m.A.get("stance")
    L.append("Theme: %s." % {"keep": "keep your own", "ours": "use ours", "choose": "decided area by area"}.get(st, "not decided yet"))
    if st == "choose":
        for a in AREAS:
            if "area:" + a in m.A:
                L.append("  %s: %s" % (AREA_BY[a]["label"], SOURCE_LABEL[m.A["area:" + a]].lower()))
    if m.ov:
        L.append("Corrected by you: " + "; ".join("%s = %s" % (R.BY_ID[k]["label"].lower(), v) for k, v in m.ov.items()))
    if "parts" in m.A:
        sel = m.selected_parts()
        L.append("Parts: %s." % (", ".join(m.bp[p]["name"].lower() for p in sel) or "none"))
        for p in m.added_by_need():
            L.append("  (%s was added because another part needs it)" % m.bp[p]["name"].lower())
        for p in sel:
            ch = m.changes(p)
            if ch:
                L.append("  %s: %s" % (m.bp[p]["name"], "; ".join(("icons %s" % ("taken out" if m.icons_off(p) else "kept")) if a == "icons" else "%s: %s" % (ASPECT_WORDS[a], SOURCE_LABEL.get(m.aspect_source(p, a), "same as the rest of your result").lower()) for a in ch if "aspect:%s:%s" % (p, a) in m.A)))
    if "screens" in m.A:
        sc = m.selected_screens()
        L.append("Screen briefs: %s." % (", ".join(m.bs[x]["name"] for x in sc) or "none"))
        for x in sc:
            if "frames:" + x in m.A or "rows:" + x in m.A:
                L.append("  %s: keeps %d of %d frames and %d of %d pieces" % (m.bs[x]["name"], len(m.frames_kept(x)), len(m.frames_of(x)), len(m.rows_kept(x)), len(m.rows_of(x))))
    return L


def stage_of(s: dict, m: Model) -> str:
    if next_question(m) is not None:
        return "asking"
    fp = m.fingerprint()
    if (s.get("built") or {}).get("hash") == fp:
        return "built"
    if (s.get("approved") or {}).get("hash") == fp:
        return "approved"
    if (s.get("preview") or {}).get("hash") == fp:
        return "previewed"
    return "ready to preview"


def cmd_status(session: str) -> int:
    s, m = model_of(session)
    print("Session %s, reading %s" % (session, s["page"]))
    for line in describe_decisions(m):
        print(line)
    print("Stage: %s" % stage_of(s, m))
    return 0


def cmd_preview(session: str) -> int:
    import render as RD
    s, m = model_of(session)
    if next_question(m) is not None:
        raise SystemExit("not every question is answered. Run: " + cmd("next", shlex.quote(session)))
    if not RD.available():
        raise SystemExit("pictures need Playwright: pip install playwright && playwright install chromium")
    out = sess_path(session) / "preview"
    out.mkdir(parents=True, exist_ok=True)
    values, tokens = m.theme_values(), m.theme_tokens()
    sel = m.selected_parts()
    files, notes, stand = [], [], []
    with RD.Renderer() as r:
        cols = [{"title": "Yours", "sub": "read from your page", "values": {k: v["value"] for k, v in m.mine.items()}, "conf": {k: v["confidence"] for k, v in m.mine.items()}},
                {"title": "Ours", "sub": "design/tokens.css", "values": {k: v["value"] for k, v in m.ours.items()}},
                {"title": "Result", "sub": "what the answers give", "values": values}]
        res = r.draw(RD.theme_sheet_html(cols, r.base), out / "theme.png", [values.get("font-body"), values.get("font-mono"), values.get("font-statement")])
        files.append(res["file"])
        stand += res["stand_in"]
        if sel:
            body = "".join(RD.cell_html(m.bp[p]["name"], m.part_tokens(p), [p], [p] if m.icons_off(p) else []) for p in sel)
            res = r.draw(RD.page_html(body, RD.parts_css(sel), r.base), out / "parts.png", _fonts(tokens, *[m.part_tokens(p) for p in sel]), width=1300)
            files.append(res["file"])
            stand += res["stand_in"]
        page = {}
        try:
            page = RD.preview_page(r, s.get("page_url") or s["page"], s.get("setup", []), m.ix, m.mine, values, {p: m.part_values(p) for p in sel},
                                    {p: m.part_tokens(p) for p in sel}, [p for p in sel if m.icons_off(p)], out)
            files += [page["before"], page["after"]]
        except Exception as e:                                         # the page moved, needs a sign-in, or is gone
            notes.append("your page could not be opened again to draw it with the changes (%s); the other pictures are made" % str(e).splitlines()[0][:120])
    if stand:
        notes.append("this machine has no %s, so those pictures show a stand-in where that font is used" % ", ".join(sorted(set(stand))))
    notes += page.get("not_drawn", [])
    for what, ratio, need, ok in R.contrast_findings(values):
        if not ok:
            notes.append("contrast: %s is %.2f:1 and %g:1 is the usual minimum; the result would be hard to read there" % (what, ratio, need))
    lines = ["# What the pictures show", "", "Look at these before saying yes.", ""] + ["- %s" % f for f in files] + [""]
    if page:
        lines += ["## Your page, before and after", "", page["caveat"], "", "Drawn on your page: " + ("; ".join(page["drawn"]) or "nothing needed to change"), ""]
    lines += ["## Not shown", ""] + (["- " + n for n in notes] or ["- nothing else to report"]) + ["- screens: you saw our frames in our colours with made-up content when you chose them; they are not drawn in your theme or on your data, and the briefs written at build are text, not code", ""]
    (out / "PREVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    s["preview"] = {"hash": m.fingerprint(), "files": files, "notes": notes, "drawn": page.get("drawn", [])}
    s.pop("approved", None)
    s.pop("built", None)
    save_session(session, s)
    print("Pictures made. Show the person these, and read them the notes:")
    for f in files:
        print("  " + f)
    for n in notes:
        print("  note: " + n)
    print("\nWhat was decided:")
    for line in describe_decisions(m):
        print("  " + line)
    print("\nAsk: 'Is this what you want me to write into your app?' If they say yes, run:\n  " + cmd("approve", shlex.quote(session), "--said", "\"WHAT THEY SAID\""))
    return 0


def cmd_approve(session: str, said: str) -> int:
    s, m = model_of(session)
    if not said or not said.strip():
        raise SystemExit("--said needs the person's own words, for example --said \"yes, go ahead\"")
    if stage_of(s, m) not in ("previewed", "approved"):
        raise SystemExit("nothing to approve: the pictures are missing or out of date (stage: %s). Run: %s" % (stage_of(s, m), cmd("preview", shlex.quote(session))))
    s["approved"] = {"hash": m.fingerprint(), "said": said.strip()}
    save_session(session, s)
    print("Approved. Next:\n  " + cmd("build", shlex.quote(session)))
    return 0


def cmd_build(session: str) -> int:
    import build_out
    s, m = model_of(session)
    st = stage_of(s, m)
    if st not in ("approved", "built"):
        raise SystemExit("not built: %s. The person must see the pictures (preview) and say yes (approve) for exactly these answers." % (
            {"asking": "questions are still open", "ready to preview": "no pictures yet", "previewed": "the person has not said yes yet"}.get(st, st)))
    out = sess_path(session) / "out"
    if out.exists():
        shutil.rmtree(out)
    written = build_out.build(m, out, s["approved"]["said"], s["page"])
    s["built"] = {"hash": m.fingerprint(), "files": written}
    save_session(session, s)
    print("Wrote %d files into %s. Start with %s." % (len(written), out, out / "CHANGES.md"))
    return 0


def cmd_verify(session: str, page: str, setup: list) -> int:
    import build_out
    s, m = model_of(session)
    if stage_of(s, m) != "built":
        raise SystemExit("verify checks a page that was changed after build; run build first (stage: %s)" % stage_of(s, m))
    return build_out.verify(m, page, setup, sess_path(session) / "out")


def cmd_init(session: str, page: str, setup: list, index_from: str | None) -> int:
    d = sess_path(session)
    if (d / "session.json").exists():
        raise SystemExit("%s already holds a session. Pick another folder, or run: %s" % (session, cmd("status", shlex.quote(session))))
    d.mkdir(parents=True, exist_ok=True)
    if index_from:
        src = Path(index_from)
        if not (src / "index.json").is_file():
            raise SystemExit("%s has no index.json" % index_from)
        shutil.copytree(src, d / "mine", dirs_exist_ok=True)
        ix = read_json(d / "mine" / "index.json")
    else:
        import index_page
        ix = index_page.run(page, str(d / "mine"), 1440, 900, setup, 6)
        write_json(d / "mine" / "index.json", ix)
        (d / "mine" / "INDEX.md").write_text(index_page.render_md(ix), encoding="utf-8")
    url = page if re.match(r"^https?://", page) else "file://" + str(Path(page).resolve())
    save_session(session, {"format": FORMAT, "page": page, "page_url": url, "setup": setup, "answers": {}, "overrides": {}})
    conf: dict = {}
    for v in ix["roles"].values():
        conf[v["confidence"]] = conf.get(v["confidence"], 0) + 1
    print("Read %s: %s." % (ix["source"], ", ".join("%d %s" % (n, k) for k, n in sorted(conf.items()))))
    print("What was read, in words: %s" % (d / "mine" / "INDEX.md"))
    for n in ix.get("notes", []):
        print("  note: " + n)
    print("\nNext, run:\n  " + cmd("next", shlex.quote(session)))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("session")
    p.add_argument("--page", required=True)
    p.add_argument("--setup", action="append", default=[])
    p.add_argument("--index-from", default=None, help="use an index folder that was already made instead of opening the page")
    p = sub.add_parser("next")
    p.add_argument("session")
    p.add_argument("--no-pictures", action="store_true")
    p = sub.add_parser("answer")
    p.add_argument("session")
    p.add_argument("question")
    p.add_argument("choice")
    p.add_argument("--no-pictures", action="store_true")
    p = sub.add_parser("set")
    p.add_argument("session")
    p.add_argument("role")
    p.add_argument("value")
    p = sub.add_parser("back")
    p.add_argument("session")
    p.add_argument("--to", default=None)
    for name in ("status", "preview", "build"):
        sub.add_parser(name).add_argument("session")
    p = sub.add_parser("approve")
    p.add_argument("session")
    p.add_argument("--said", default="")
    p = sub.add_parser("verify")
    p.add_argument("session")
    p.add_argument("--page", required=True)
    p.add_argument("--setup", action="append", default=[])
    a = ap.parse_args(argv)
    if a.cmd == "init":
        return cmd_init(a.session, a.page, a.setup, a.index_from)
    if a.cmd == "next":
        return cmd_next(a.session, not a.no_pictures)
    if a.cmd == "answer":
        return cmd_answer(a.session, a.question, a.choice, not a.no_pictures)
    if a.cmd == "set":
        return cmd_set(a.session, a.role, a.value)
    if a.cmd == "back":
        return cmd_back(a.session, a.to)
    if a.cmd == "status":
        return cmd_status(a.session)
    if a.cmd == "preview":
        return cmd_preview(a.session)
    if a.cmd == "approve":
        return cmd_approve(a.session, a.said)
    if a.cmd == "build":
        return cmd_build(a.session)
    return cmd_verify(a.session, a.page, a.setup)


if __name__ == "__main__":
    sys.exit(main())
