"""Write what the answers decided as files, and check a changed page against them.

    build(model, out_dir, said, page)   adopted-tokens.css, adopted.tokens.json, parts/<id>/..., screens/<id>.md, CHANGES.md, REPORT.md, decisions.json
    verify(model, page, setup, out_dir) read the changed page again and say, decision by decision, whether it shows

Nothing here changes the person's app. The files are for them (or their tools) to copy in; CHANGES.md says how. Standard library, plus Playwright for verify.
"""
from __future__ import annotations

import html as H
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT, REPO, TOKENS_CSS, css_vars, first_family, px, read_json, write_json  # noqa: E402
import catalog as CAT  # noqa: E402
import roles as R  # noqa: E402
import render as RD  # noqa: E402

HEADER = "/* Written by design/adopt_design (build). %s */\n"


def _ad():
    import adopt                          # imported late: adopt imports this module's functions through its commands
    return adopt


def token_closure(tokens_wanted: set, ours_vars: dict) -> tuple:
    """Every token a set of tokens leads to through var() in design/tokens.css values. Returns (all names reached, names nobody defines)."""
    seen, missing, todo = set(), set(), list(tokens_wanted)
    while todo:
        t = todo.pop()
        if t in seen:
            continue
        seen.add(t)
        if t not in ours_vars:
            missing.add(t)
            continue
        todo += re.findall(r"var\((--[\w-]+)", ours_vars[t])
    return seen, missing


def role_of_token() -> dict:
    out = {}
    for r in R.ROLES["roles"]:
        for t in r["ours"] + list((r.get("derive") or {}).keys()):
            out[t] = r["id"]
    return out


def theme_file(m, parts_css_text: str) -> tuple:
    """(css text, report) for adopted-tokens.css: the tokens the answers drive, then any token the chosen parts use that no answer drives, as written in design/tokens.css."""
    vals, tokens = m.theme_values(), m.theme_tokens()
    t_role = role_of_token()
    used = set(re.findall(r"var\((--[\w-]+)", parts_css_text))
    for sel in m.selected_parts():                                       # the scoped per-part overrides use tokens too
        pc = CAT.part_css(m.bp[sel], m.ours_vars)[0]
        used |= {t for t in m.part_token_diff(sel) if t in set(re.findall(r"var\((--[\w-]+)", pc))}
    reach, missing = token_closure(used, m.ours_vars)
    extra = sorted(t for t in reach if t not in tokens and t in m.ours_vars)
    lines = []
    for t in sorted(tokens):
        role = t_role.get(t)
        if role:
            if m.area_source(R.AREA_OF[role]) == "ours":
                why = "ours"
            else:
                why = m.mine_value(role)[1]
            lines.append("  %s:%s; /* %s: %s */" % (t, tokens[t], R.BY_ID[role]["label"].lower(), why))
    for t in extra:
        lines.append("  %s:%s; /* ours, as written in design/tokens.css: no answer drives it */" % (t, m.ours_vars[t]))
    fams = {first_family(vals.get(k) or "") for k in ("font-body", "font-statement", "font-mono")}
    for pid in m.selected_parts():
        fams |= {first_family(m.part_tokens(pid).get(k, "")) for k in ("--sans", "--serif", "--mono")}
    faces = [b for b in re.findall(r"@font-face\{[^}]*\}", TOKENS_CSS.read_text(encoding="utf-8")) if re.search(r"font-family:'([^']+)'", b) and re.search(r"font-family:'([^']+)'", b).group(1) in fams]
    css = HEADER % "Colours, type, corners, shadow and sizes that the answers decided, under the names our parts use." + ("\n".join(faces) + "\n" if faces else "") + ":root{\n" + "\n".join(lines) + "\n}\n"
    return css, {"tokens": len(tokens), "from_ours_as_written": extra, "undefined": sorted(missing), "font_files": [f for b in faces for f in re.findall(r"url\(\./fonts/([^)]+)\)", b)]}


def _color_obj(css: str):
    """A CSS colour as a Design Tokens 2025.10 colour value: {colorSpace: srgb, components: [r, g, b] from 0 to 1, alpha (only when not 1), hex}. None when it is not a colour this reads."""
    css = css.strip()
    short = re.fullmatch(r"#([0-9A-Fa-f])([0-9A-Fa-f])([0-9A-Fa-f])([0-9A-Fa-f])?", css)             # #fff and #fffa: the colour reader takes six or eight digits
    if short:
        css = "#" + "".join(c * 2 for c in short.groups() if c)
    eight = re.fullmatch(r"#([0-9A-Fa-f]{6})([0-9A-Fa-f]{2})", css)
    if eight:                                                                                         # #rrggbbaa -> the same colour with its alpha, as rgba()
        h, a = eight.groups()
        css = "rgba(%d,%d,%d,%s)" % (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), round(int(a, 16) / 255, 4))
    p = R.C.parse_css(css)
    if not p:
        return None
    hx = p[0].lstrip("#")
    comps = [round(int(hx[i:i + 2], 16) / 255, 4) for i in (0, 2, 4)]
    out = {"colorSpace": "srgb", "components": comps}
    if p[1] < 0.999:
        out["alpha"] = round(p[1], 4)
    out["hex"] = "#" + hx.lower()
    return out


def _dimension(v: str):
    """A px or rem length as {value, unit} (the only units the format allows), or None."""
    m = re.fullmatch(r"\s*(-?\d*\.?\d+)(px|rem)\s*", v)
    return {"value": float(m.group(1)) if "." in m.group(1) else int(m.group(1)), "unit": m.group(2)} if m else None


def _dtcg_shadow(v: str):
    """A CSS box-shadow as shadow objects ({color, offsetX, offsetY, blur, spread[, inset]}), or None when it cannot be split into those parts."""
    layers = []
    for layer in re.split(r",(?![^(]*\))", v):
        inset = bool(re.search(r"\binset\b", layer))
        layer = re.sub(r"\binset\b", "", layer)
        col = re.search(r"rgba?\([^)]*\)|#[0-9A-Fa-f]{3,8}", layer)
        nums = re.findall(r"(?<![\w.#])-?\d*\.?\d+(?:px)?(?![\w.])", layer.replace(col.group(0), "") if col else layer)
        c = _color_obj(col.group(0)) if col else None
        if not c or not 2 <= len(nums) <= 4:
            return None
        n = [_dimension(x if x.endswith("px") else x + "px") for x in nums] + [{"value": 0, "unit": "px"}] * (4 - len(nums))
        obj = {"color": c, "offsetX": n[0], "offsetY": n[1], "blur": n[2], "spread": n[3]}
        if inset:
            obj["inset"] = True
        layers.append(obj)
    return layers[0] if len(layers) == 1 else layers


def dtcg(tokens: dict, extra: dict) -> dict:
    """The tokens in the Design Tokens Community Group format, version 2025.10 (the latest published one when this was written): a colour is an object with a colour space and
    components, a length is {value, unit}, a font family is a string or a list, a shadow is an object of those. Anything that does not fit (a rem-less length, a shadow that cannot be
    split) is kept as the CSS text with no $type, and says so."""
    out: dict = {"$schema": "https://www.designtokens.org/schemas/2025.10/format.json",
                 "$description": "Written by design/adopt_design. Names are the product's own token names without the leading --. A token kept as text has no $type."}
    t_role = role_of_token()
    for name, val in sorted({**extra, **tokens}.items()):
        role = t_role.get(name)
        kind = R.BY_ID[role]["kind"] if role else ("colour" if re.fullmatch(r"#[0-9A-Fa-f]{3,8}", val) else "length" if _dimension(val) else "other")
        key = name[2:]
        tok = None
        if kind == "colour":
            c = _color_obj(val)
            tok = ("color", {"$type": "color", "$value": c}) if c else None
        elif kind == "length":
            d = _dimension(val)
            tok = ("dimension", {"$type": "dimension", "$value": d}) if d else None
        elif kind == "font":
            tok = ("fontFamily", {"$type": "fontFamily", "$value": [x.strip().strip("'\"") for x in val.split(",")]})
        elif kind == "shadow":
            sh = None if val.strip() == "none" else _dtcg_shadow(val)
            tok = ("shadow", {"$type": "shadow", "$value": sh}) if sh else None
        if tok is None:
            out.setdefault("text", {})[key] = {"$value": val, "$description": "kept as CSS text: not a value the token format can hold"}
        else:
            out.setdefault(tok[0], {})[key] = tok[1]
    return out


def part_files(m, pid: str, out: Path, rep_left: list) -> list:
    p = m.bp[pid]
    css, rep = CAT.part_css(p, m.ours_vars)
    rep_left.append((pid, rep["left_literal"]))
    used, _ = token_closure(set(re.findall(r"var\((--[\w-]+)", css)), m.ours_vars)
    diff = {t: v for t, v in m.part_token_diff(pid).items() if t in used}          # only the tokens this part's rules use
    roots = ",".join(p.get("roots", []))
    parts_css = "/* %s: the rules our design uses for it (from %s). Literal colours that a token names exactly are written as that token. */\n%s" % (
        p["name"], ", ".join(sorted({s["file"] for s in p["css"]})), css)
    if diff:
        parts_css += "\n/* What was decided for this part alone (the rest follows adopted-tokens.css) */\n%s{%s}\n" % (roots, ";".join("%s:%s" % kv for kv in sorted(diff.items())))
    if m.icons_off(pid):
        parts_css += "\n/* Icons taken out: %s */\n%s\n" % (p["icons"]["label"], p["icons"]["css"])
    d = out / "parts" / pid
    d.mkdir(parents=True, exist_ok=True)
    (d / "part.css").write_text(HEADER % ("Part: " + p["name"]) + parts_css, encoding="utf-8")
    spec = (KIT / p["specimen"]).read_text(encoding="utf-8")
    (d / "specimen.html").write_text(
        '<!doctype html>\n<meta charset="utf-8"><title>%s</title>\n<link rel="stylesheet" href="../../adopted-tokens.css"><link rel="stylesheet" href="part.css">\n<style>%s\nbody{margin:0;padding:24px;background:var(--canvas);color:var(--ink);font-family:var(--sans);font-size:var(--size-body)}</style>\n%s\n'
        % (H.escape(p["name"]), p.get("stage_css", ""), spec), encoding="utf-8")
    notes = ["# %s" % p["name"], "", p["what"], "", "## What was decided", ""]
    for a in m.aspects_of(pid):
        if a == "icons":
            if "icons" in m.changes(pid):
                notes.append("- Icons: %s." % ("taken out" if m.icons_off(pid) else "kept"))
        elif a in m.changes(pid):
            notes.append("- %s: %s." % (_ad().ASPECT_WORDS[a].capitalize(), _ad().SOURCE_LABEL.get(m.aspect_source(pid, a), "same as the rest of your result").lower()))
    if not m.changes(pid):
        notes.append("- Nothing changed for this part: it follows adopted-tokens.css.")
    notes += ["", "## Files", "", "- `part.css`: the rules. Link it after `adopted-tokens.css`.", "- `specimen.html`: the part drawn with made-up words, to open in a browser. **It is a drawing for looking at.** The words and the markup are made up; take the real markup from the prototype source below.", ""]
    if p.get("font_base"):
        notes += ["## Fonts", "", "`part.css` begins with a rule that sets the font and size from `--sans` and `--size-body` on the part's outer element (the prototype takes them from the page body). Text inside a "
                  "button follows only if your page lets buttons inherit the font (`button{font:inherit}`), as the prototype does.", ""]
    if p.get("source"):
        notes += ["## Where the real markup is", ""] + ["- `%s` (in this product's repository; it is built from templates with inline styles, so treat it as a reference for structure and words)" % f for f in p["source"]] + [""]
    if p.get("navigation"):
        notes += ["## Where it leads", "", "Read `design/navigation.json` at `%s`; `docs/NAVIGATION_MAP.md` is the same in words." % p["navigation"], ""]
    if p.get("data_map"):
        notes += ["## Where its words and numbers come from", "", "`docs/SCREEN_DATA_MAP.md`, section %s." % ", ".join(p["data_map"]), ""]
    if p.get("hooks"):
        notes += ["## Marks the checks look for", "", "Keep these when you build it: %s. They are explained in `docs/GUI_TEST_HOOKS.md`." % ", ".join("`%s`" % h for h in p["hooks"]), ""]
    if rep["left_literal"]:
        notes += ["## Values left as written", "", "No token names these exactly, so they stay as literal values in `part.css`; change them by hand if they clash with your theme:", ""] + [
            "- `%s` %s: %s" % (s, pr, v) for s, pr, v in rep["left_literal"]] + [""]
    (d / "NOTES.md").write_text("\n".join(notes), encoding="utf-8")
    return ["parts/%s/part.css" % pid, "parts/%s/specimen.html" % pid, "parts/%s/NOTES.md" % pid]


def where_in_menu(nav: dict, screen_id: str) -> list:
    out = []
    for g in nav["shell"]["side_bar"]["groups"]:
        for i, it in enumerate(g["items"], 1):
            if it.get("screen") == screen_id:
                out.append("item %d of %d %s, labelled \"%s\"" % (i, len(g["items"]), ("in the menu group \"%s\"" % g["heading"]) if g.get("heading") else "at the top of the menu (no group heading)", it["label"]))
    return out


def screen_file(m, sid: str, out: Path) -> str:
    s = m.bs[sid]
    nav = m._nav
    kept, rows = m.rows_kept(sid), m.rows_of(sid)
    dropped = [r for r in rows if r not in kept]
    L = ["# %s" % s["name"], "", "A build brief for one screen of our design. It lists what the screen holds and where each piece comes from; it is not a picture and it is not code.", ""]
    sel = m.selected_parts()
    L += ["## Where it sits", ""]
    L += ["- %s" % x for x in where_in_menu(nav, s["screen"])] or ["- It is not an item in the side menu: see `design/navigation.json` (flows, sheets and overlays) for how it is reached."]
    if s["entry"]:
        L.append("- It is where the product starts.")
    if s.get("part_file"):
        L.append("- Our prototype's markup for it: `prototype/parts/m/%s`." % s["part_file"])
    L += ["", "## What is on it (you kept %d of %d)" % (len(kept), len(rows)), "", "| Piece | Where it comes from |", "|---|---|"] + ["| %s | %s |" % (r["part"], r["source"]) for r in kept]
    if dropped:
        L += ["", "## Left out on purpose (you dropped these)", ""] + ["- %s" % r["part"] for r in dropped]
    L += ["", "## Build it with", ""]
    L += ["- The codes in the table (DS, CL, PR, WORK, STATIC, NONE) are explained in `docs/SCREEN_DATA_MAP.md`, section 2.", "- `adopted-tokens.css` for colours, type, corners and sizes.", "- The parts you took: %s." % (", ".join(m.bp[p]["name"].lower() for p in sel) or "none: build it from your own components")]
    L += ["- `docs/agent_prompts/build_the_gui.md` in our repository, which says how to build a screen from a picture and these maps without losing the menu, the order of the pieces or the marks the checks read.",
          "- `docs/SCREEN_DATA_MAP.md`, section(s) %s, for the data each piece shows." % ", ".join(s["sections"]), ""]
    (out / "screens").mkdir(parents=True, exist_ok=True)
    (out / "screens" / (s["screen"] + ".md")).write_text("\n".join(L), encoding="utf-8")
    return "screens/%s.md" % s["screen"]


def collisions(m, tokens_css_text: str) -> list:
    """Names adopted-tokens.css sets that the person's page already declares as custom properties, and whether the value is the same."""
    mine = {d["name"]: d.get("resolved") or d["value"] for d in m.ix.get("declared_vars", [])}
    out = []
    for name, val in re.findall(r"(--[\w-]+):([^;]+);", tokens_css_text.split(":root{", 1)[-1]):
        if name in mine:
            out.append((name, mine[name], val.strip()))
    return out


def build(m, out: Path, said: str, page: str) -> list:
    """Write every file. Returns the relative names written."""
    AD = _ad()
    out.mkdir(parents=True, exist_ok=True)
    written = []
    sel = m.selected_parts()
    left: list = []
    for pid in sel:
        written += part_files(m, pid, out, left)
    parts_text = "\n".join((out / "parts" / pid / "part.css").read_text(encoding="utf-8") for pid in sel)
    tcss, trep = theme_file(m, parts_text)
    (out / "adopted-tokens.css").write_text(tcss, encoding="utf-8")
    written.append("adopted-tokens.css")
    if trep["font_files"]:
        (out / "fonts").mkdir(exist_ok=True)
        for f in sorted(set(trep["font_files"])):
            shutil.copy2(RD.FONT_DIR / f, out / "fonts" / f)
            written.append("fonts/" + f)
    toks = m.theme_tokens()
    write_json(out / "adopted.tokens.json", dtcg(toks, {t: m.ours_vars[t] for t in trep["from_ours_as_written"]}))
    written.append("adopted.tokens.json")
    for sid in m.selected_screens():
        written.append(screen_file(m, sid, out))
    vals = m.theme_values()
    rows = []
    for r in R.ROLES["roles"]:
        mine_v, origin = m.mine_value(r["id"])
        theirs = (m.mine.get(r["id"]) or {}).get("value")
        rows.append((r, theirs, vals[r["id"]], origin if m.area_source(r["area"]) == "mine" else "ours (you chose ours for %s)" % AD.AREA_BY[r["area"]]["label"].lower()))
    coll = collisions(m, tcss)
    C_ = ["# What changes in your app", "", "Written for the answers you approved. Nothing in your app has been changed: these are files to copy in.", "", "## What was decided", ""] + ["- " + x if not x.startswith("  ") else x for x in AD.describe_decisions(m)]
    C_ += ["", "## Your values, role by role", "", "| What | Yours now | The result | Where the result's value comes from |", "|---|---|---|---|"]
    for r, theirs, res, origin in rows:
        same = theirs is not None and R.identical(r["id"], theirs, res)
        C_.append("| %s | %s | %s%s | %s |" % (r["label"], R.value_text(r["id"], theirs), R.value_text(r["id"], res), " (same)" if same else "", origin))
    C_ += ["", "## Put it in", "", "1. Copy `adopted-tokens.css` into your app and link it where your other stylesheets are linked." + (" Copy the `fonts/` folder next to it: the font files are ours, so check their licences in the repository you took them from." if trep["font_files"] else "")]
    for i, pid in enumerate(sel, 2):
        C_.append("%d. %s: copy `parts/%s/part.css`, and build its markup from the prototype source named in `parts/%s/NOTES.md` (open `specimen.html` to see what it looks like)." % (i, m.bp[pid]["name"], pid, pid))
    n = len(sel) + 2
    for sid in m.selected_screens():
        C_.append("%d. %s: follow `screens/%s.md`." % (n, m.bs[sid]["name"], m.bs[sid]["screen"]))
        n += 1
    C_.append("%d. When it is in, run `python3 design/adopt_design/scripts/adopt.py verify SESSION --page YOUR-PAGE` to read the page again and see which decisions it shows." % n)
    if coll:
        C_ += ["", "## Names that clash with yours", "", "Your page already declares these custom properties. `adopted-tokens.css` sets them too; loading it changes how your own styles that use them look when the values differ.", "",
               "| Name | Your value | Value in adopted-tokens.css |", "|---|---|---|"] + ["| `%s` | %s | %s |" % c for c in coll]
    C_ += ["", "## Not decided here", "", "- Anything the pictures could not show (see `REPORT.md`).", ""]
    (out / "CHANGES.md").write_text("\n".join(C_), encoding="utf-8")
    written.append("CHANGES.md")
    R_ = ["# What was not checked", "", "Everything above was decided from what a browser computed on your page and from our design files. This report lists what that does not cover.", "",
          "- **Reads that are guesses.** %s." % ("; ".join("%s (%s)" % (R.BY_ID[r]["label"].lower(), "you said it is " + ("wrong" if r in (m.A.get("guesses") or []) else "right")) for r in R.ROLE_IDS if (m.mine.get(r) or {}).get("confidence") == "guess" and m.mine[r].get("value") is not None) or "none"),
          "- **Roles your page has nothing for** (ours was used): %s." % (", ".join(R.BY_ID[r]["label"].lower() for r in R.ROLE_IDS if (m.mine.get(r) or {}).get("value") is None and r not in m.ov) or "none"),
          "- **Left as written in design/tokens.css** because no answer drives them: %s." % (", ".join(trep["from_ours_as_written"]) or "nothing"),
          "- **Token names no file defines**: %s." % (", ".join(trep["undefined"]) or "none"),
          "- **Literal values left in part files** (no token names them): %s." % ("; ".join("%s: %d" % (pid, len(v)) for pid, v in left if v) or "none"),
          "- **Contrast of the result's main pairs** (WCAG 2.x ratio; 4.5 for text, 3 for a coloured control): %s. Pairs not listed were not checked." % (
              "; ".join("%s %.2f:1 %s" % (w, r, "ok" if ok else "BELOW %g" % need) for w, r, need, ok in R.contrast_findings(vals)) or "no pair could be worked out"),
          "- Pictures are drawings of the decision from specimens and your own page restyled; they are not the code, and they were drawn by one browser (Chromium) on one machine.",
          "- Fonts that were not installed where the pictures were drawn appeared in a stand-in; the files use the font you chose.",
          "- Screens are briefs, with no pictures. Nothing was built from them here.",
          "- A second theme (dark mode), anything behind a click or a sign-in that was not set up, and the layout at narrow widths were not read or drawn.",
          "- The person's words approving this: \"%s\"" % said.replace('"', "'"), ""]
    (out / "REPORT.md").write_text("\n".join(R_), encoding="utf-8")
    written.append("REPORT.md")
    write_json(out / "decisions.json", {"format": "reqin-adopt-decisions/1", "page": m.ix.get("source"), "approved_words": said, "fingerprint": m.fingerprint(), "answers": m.A, "overrides": m.ov,
                                         "roles": {r["id"]: {"yours": t, "result": v, "origin": o} for r, t, v, o in rows},
                                         "parts": [{"id": p, "tokens_for_this_part_only": m.part_token_diff(p), "icons": "removed" if m.icons_off(p) else "kept"} for p in sel],
                                         "screens": [{"id": s, "kept": [r["id"] for r in m.rows_kept(s)], "dropped": [r["id"] for r in m.rows_of(s) if r not in m.rows_kept(s)]} for s in m.selected_screens()]})
    written.append("decisions.json")
    return sorted(written)


# ------------------------------------------------------------------------------------------------ after the page has been changed
def verify(m, page: str, setup: list, out: Path) -> int:
    """Read the person's changed page and say, role by role, whether it shows what was decided. Exit 1 when a decision is not shown."""
    import index_page
    from playwright.sync_api import sync_playwright
    import site_map as SM
    with tempfile.TemporaryDirectory() as tmp:
        ix = index_page.run(page, tmp, 1440, 900, setup, 6)
    want = m.theme_values()
    bad = 0
    print("Your page, read again, against what was decided (colours within a small tolerance, sizes within a pixel):")
    for r in R.ROLES["roles"]:
        got = (ix["roles"].get(r["id"]) or {})
        w = want[r["id"]]
        if got.get("value") is None:
            line = "not found on the page"
            ok = None
        elif R.same(r["id"], got["value"], w):
            line, ok = "shown", True
        else:
            line, ok = "wanted %s, the page has %s" % (R.value_name(r["id"], w), R.value_name(r["id"], got["value"])), False
        if ok is False and got.get("confidence") == "guess":
            line += " (the page value is itself a guess)"
        if ok is False:
            bad += 1
        print("  %-34s %s" % (r["label"], line))
    url = page if re.match(r"^https?://", page) else "file://" + str(Path(page).resolve())
    print("\nParts (is an element of each part's own class on the page?):")
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        try:
            pg = b.new_page(viewport={"width": 1440, "height": 900})
            pg.goto(url, wait_until="load", timeout=30000)
            if setup:
                SM.run_setup(pg, setup)
            for pid in m.selected_parts():
                roots = m.bp[pid].get("roots", [])
                n = sum(pg.locator(rt).count() for rt in roots) if roots else 0
                print("  %-16s %s" % (m.bp[pid]["name"], ("%d element(s) with %s" % (n, ", ".join(roots))) if n else "not found (looked for %s)" % ", ".join(roots)))
                bad += 0 if n else 1
        finally:
            b.close()
    print("\n%s" % ("Everything decided is shown." if not bad else "%d thing(s) not shown. This reads the page the way index_page.py reads any page; a role read as a guess can differ without being wrong." % bad))
    return 1 if bad else 0
