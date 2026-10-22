"""What can be taken from this product's design: the parts (catalog.json), their stylesheet rules, and the screens (design/navigation.json + docs/SCREEN_DATA_MAP.md).

    python3 scripts/catalog.py                    check the catalog and print what it holds
    python3 scripts/catalog.py css PART           the rules the prototype and the design kit really use for a part, with literal colours replaced by token names where one matches exactly
    python3 scripts/catalog.py list               one line per part and per screen

The stylesheet rules are cut out of the real stylesheets by selector, not retyped, so a change to the prototype's CSS shows up here. Standard library only.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import KIT, REPO, TOKENS_CSS, css_vars, read_json  # noqa: E402

CATALOG = KIT / "catalog.json"
AT_WITH_RULES = ("@media", "@container", "@supports", "@layer")


def load() -> dict:
    return read_json(CATALOG)


# ------------------------------------------------------------------------------------------------ cutting rules out of a stylesheet
def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _blocks(css: str):
    """Top-level items of a stylesheet as (prelude, body) pairs. A rule's body is its declarations; an at-rule that holds rules has those as its body text."""
    i, n, out = 0, len(css), []
    while i < n:
        j = i
        while j < n and css[j] not in "{;":
            j += 1
        if j >= n:
            break
        if css[j] == ";":                               # @import / @charset: nothing to cut
            i = j + 1
            continue
        depth, k = 1, j + 1
        while k < n and depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        out.append((css[i:j].strip(), css[j + 1:k - 1].strip()))
        i = k
    return out


def _split_selectors(prelude: str) -> list:
    parts, depth, cur = [], 0, ""
    for ch in prelude:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def slice_css(css: str, patterns: list) -> list:
    """The rules whose selectors match any pattern, as ready-to-write lines. A rule that lists several selectors keeps only those that match. At-rules that hold rules (media, container
    queries) are kept with only the matching rules inside them, and dropped when none are left."""
    pats = [re.compile(p) for p in patterns]

    def keep(blocks, indent=""):
        out = []
        for prelude, body in blocks:
            if prelude.startswith("@"):
                if prelude.split("(")[0].split()[0].lower() in AT_WITH_RULES:
                    inner = keep(_blocks(body), indent + "  ")
                    if inner:
                        out.append("%s%s{\n%s\n%s}" % (indent, prelude, "\n".join(inner), indent))
                continue
            sels = [s for s in _split_selectors(prelude) if any(p.search(s) for p in pats)]
            if sels:
                out.append("%s%s{%s}" % (indent, ",".join(sels), body))
        return out

    return keep(_blocks(_strip_comments(css)))


def classes_in(css_lines: list) -> set:
    return set(re.findall(r"\.([A-Za-z_][\w-]*)", "\n".join(css_lines)))


# ------------------------------------------------------------------------------------------------ naming literals with the product's own tokens
COLOUR_PROPS = {"color": r"^--(text|ink|slate|accent)", "fill": r"^--(text|ink|slate|accent)", "stroke": r"^--(text|ink|slate|accent)",
                "background": r"^--(paper|canvas|surface|band|accent)", "background-color": r"^--(paper|canvas|surface|band|accent)"}
BORDER_RE = r"^--(border|line|hair)"


def _norm_hex(h: str) -> str:
    h = h.lstrip("#").upper()
    return "#" + (h if len(h) == 6 else "".join(c * 2 for c in h))


def tokenise(lines: list, tokens: dict) -> tuple:
    """Replace each literal colour that equals a token's value exactly with var(--token), choosing by the property when several tokens share a value, and a single-value border-radius
    that equals a radius token, a min-height that equals a control-height token, and a font-size that equals a text-size token. Returns (lines, replaced, left) where left lists the
    colour literals no token names (so someone looks at them)."""
    by_value: dict = {}
    for name, val in tokens.items():
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", val):
            by_value.setdefault(val.upper(), []).append(name)
    radius = {val: name for name, val in tokens.items() if name.startswith("--radius-")}
    lengths = {"min-height": {val: name for name, val in tokens.items() if name.startswith("--target-")},
               "font-size": {val: name for name, val in tokens.items() if name.startswith("--size-")}}
    replaced, left = [], []

    def pick(names, prop):
        pattern = COLOUR_PROPS.get(prop) or (BORDER_RE if prop.startswith(("border", "outline")) or prop == "box-shadow" else None)
        if len(names) == 1:
            return names[0]
        if pattern:
            hit = [n for n in names if re.search(pattern, n)]
            if hit:
                return hit[0]
        return None

    def fix_decl(decl, selector):
        if ":" not in decl:
            return decl
        prop, _, val = decl.partition(":")
        p = prop.strip().lower()
        if p.startswith("--"):
            return decl

        def sub(m):
            lit = _norm_hex(m.group(0))
            names = by_value.get(lit)
            if not names:
                left.append((selector, p, m.group(0)))
                return m.group(0)
            name = pick(names, p)
            if name is None:
                left.append((selector, p, "%s (named by %s: not chosen)" % (m.group(0), ", ".join(names))))
                return m.group(0)
            replaced.append((selector, p, m.group(0), name))
            return "var(%s)" % name

        new = re.sub(r"#[0-9A-Fa-f]{3}(?![0-9A-Fa-f])|#[0-9A-Fa-f]{6}(?![0-9A-Fa-f])", sub, val)
        if p == "border-radius":
            m = re.fullmatch(r"\s*(\d+(?:\.\d+)?px)\s*(!important)?\s*", new)
            if m and m.group(1) in radius:
                replaced.append((selector, p, m.group(1), radius[m.group(1)]))
                new = " var(%s)%s" % (radius[m.group(1)], " !important" if m.group(2) else "")
        elif p in lengths:
            m = re.fullmatch(r"(\s*)(\d+(?:\.\d+)?px)\s*(!important)?\s*", new)
            if m and m.group(2) in lengths[p]:
                replaced.append((selector, p, m.group(2), lengths[p][m.group(2)]))
                new = "%svar(%s)%s" % (m.group(1), lengths[p][m.group(2)], " !important" if m.group(3) else "")
        return prop + ":" + new

    out = []
    for line in lines:
        def rule(m):
            body = ";".join(fix_decl(d, m.group(1).strip()) for d in m.group(2).split(";"))
            return "%s{%s}" % (m.group(1), body)
        out.append(re.sub(r"([^{}\n]+)\{([^{}]*)\}", rule, line))
    return out, replaced, left


# ------------------------------------------------------------------------------------------------ parts and screens
def part_css(part: dict, tokens: dict | None = None) -> tuple:
    """(css text, report) for one part: its rules from the real stylesheets, literals named where a token matches exactly."""
    tokens = tokens if tokens is not None else css_vars(TOKENS_CSS.read_text(encoding="utf-8"))
    lines, replaced, left = [], [], []
    for src in part["css"]:
        cut = slice_css((REPO / src["file"]).read_text(encoding="utf-8"), src["selectors"])
        cut, rep, lf = tokenise(cut, tokens)
        lines += cut
        replaced += rep
        left += lf
    if part.get("font_base") and part.get("roots"):
        # The prototype takes its font and size from the page body. Written first, so that a rule of the part that sets its own size still wins, but a page's reset of buttons does not.
        lines.insert(0, "%s{font-family:var(--sans);font-size:var(--size-body)}" % ",".join(part["roots"]))
    return "\n".join(lines) + "\n", {"rules": len(lines), "replaced": len(replaced), "left_literal": left}


def data_map_rows(text: str) -> dict:
    """{'4.4': [(part, source), ...]} for every numbered section of docs/SCREEN_DATA_MAP.md."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^###\s+(\d+\.\d+)\s", line)
        if m:
            cur = m.group(1)
            out[cur] = []
            continue
        if cur and line.startswith("|") and not re.match(r"^\|\s*(Part|---)", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                out[cur].append((cells[0], cells[1]))
        elif line.startswith("#"):
            cur = None
    return out


# Where a piece's content comes from, as docs/SCREEN_DATA_MAP.md section 2 names it, in the words a person would use.
KIND_WORDS = {"data": "from your requirements data", "compare": "from the comparison run", "work": "typed by people in the app", "words": "fixed words",
              "none": "nothing produces it yet", "worked": "worked out, not read directly", "unlisted": "not in the data map (words and layout)"}
_DATA_CODES = re.compile(r"\b(DS|LK|RJ|RPT|MAN|VEE)\b(?=[.\[`])")
_COMPARE_CODES = re.compile(r"\b(CL|PR|SL|CMP)\b(?=[.\[`])")


def source_kinds(source: str) -> list:
    """The kinds (keys of KIND_WORDS) a data-map row's source text names, in a fixed order. A source that names none of the codes is worked out from other values."""
    kinds = []
    if _DATA_CODES.search(source):
        kinds.append("data")
    if _COMPARE_CODES.search(source):
        kinds.append("compare")
    for word, kind in (("WORK", "work"), ("STATIC", "words"), ("NONE", "none")):
        if re.search(r"\b%s\b" % word, source):
            kinds.append(kind)
    return kinds or ["worked"]


def screens(nav: dict, data_map_text: str) -> list:
    """One entry per screen in the navigation map, with the rows of the data map that say what it shows."""
    rows = data_map_rows(data_map_text)
    out = []
    for s in nav["screens"]:
        sections = s.get("data_map", [])
        out.append({"id": "screen-" + s["id"], "screen": s["id"], "kind": "screen", "name": s["title"], "entry": s["kind"] == "entry", "sections": sections,
                    "rows": [{"section": sec, "part": a, "source": b, "kinds": source_kinds(b)} for sec in sections for a, b in rows.get(sec, [])], "part_file": s.get("part", "")})
    return out


def all_parts() -> list:
    return load()["parts"]


# ------------------------------------------------------------------------------------------------ the catalog checks itself
def check(catalog: dict | None = None) -> list:
    cat = catalog or load()
    errs = []
    roles = read_json(KIT / "roles.json")
    areas = {a["id"] for a in roles["areas"]}
    area_tokens: dict = {}
    for r in roles["roles"]:
        area_tokens.setdefault(r["area"], set()).update(set(r["ours"]) | set((r.get("derive") or {}).keys()))
    ids = [p["id"] for p in cat["parts"]]
    if len(set(ids)) != len(ids):
        errs.append("a part id is used twice")
    nav = read_json(REPO / "design" / "navigation.json")
    for p in cat["parts"]:
        w = "part %s" % p.get("id")
        for k in ("id", "kind", "name", "what", "specimen", "css", "areas"):
            if k not in p:
                errs.append("%s: %s is missing" % (w, k))
        if errs and any(e.startswith(w) for e in errs):
            continue
        if p["kind"] not in ("shell", "component"):
            errs.append("%s: kind must be shell or component" % w)
        if not (KIT / p["specimen"]).is_file():
            errs.append("%s: specimen %s does not exist" % (w, p["specimen"]))
        for a in p["areas"]:
            if a not in areas:
                errs.append("%s: area %r is not in roles.json" % (w, a))
        for src in p["css"]:
            if not (REPO / src["file"]).is_file():
                errs.append("%s: stylesheet %s does not exist" % (w, src["file"]))
                continue
            for pat in src["selectors"]:
                try:
                    re.compile(pat)
                except re.error:
                    errs.append("%s: %r is not a regular expression" % (w, pat))
        if errs and any(e.startswith(w) for e in errs):
            continue
        css, rep = part_css(p)
        if rep["rules"] == 0:
            errs.append("%s: no rule in the stylesheets matches its selectors, so it would be drawn unstyled" % w)
        frag = (KIT / p["specimen"]).read_text(encoding="utf-8")
        used = {c for grp in re.findall(r'class="([^"]+)"', frag) for c in grp.split()}
        known = classes_in(css.splitlines())
        stray = sorted(c for c in used if c not in known and c not in ("sr",))
        if stray:
            errs.append("%s: the specimen uses classes no rule of the part styles: %s" % (w, ", ".join(stray)))
        used_tokens = set(re.findall(r"var\((--[\w-]+)", css))
        for a in p["areas"]:
            if a in area_tokens and not used_tokens & area_tokens[a]:
                errs.append("%s: it offers a change of %s, but none of its rules uses a token that choice sets, so choosing it would change nothing" % (w, a))
        for root in p.get("roots", []):
            if not any(root in line for line in css.splitlines()):
                errs.append("%s: root %s is styled by none of the part's rules" % (w, root))
        for n in p.get("needs", []):
            if n not in ids:
                errs.append("%s: needs %s, which is not a part" % (w, n))
        if "icons" in p and not (p["icons"].get("css") and p["icons"].get("label")):
            errs.append("%s: icons needs a label and the css that removes them" % w)
        nvp = p.get("navigation")
        if nvp:
            cur = nav
            for key in nvp.split("."):
                cur = cur.get(key) if isinstance(cur, dict) else None
            if cur is None:
                errs.append("%s: navigation pointer %s is not in design/navigation.json" % (w, nvp))
        for f in p.get("source", []):
            if not (REPO / f).is_file():
                errs.append("%s: source file %s does not exist" % (w, f))
        text = (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8")
        for sec in p.get("data_map", []):
            if sec not in data_map_rows(text):
                errs.append("%s: data-map section %s does not exist" % (w, sec))
        doc = (REPO / "docs" / "GUI_TEST_HOOKS.md").read_text(encoding="utf-8")
        for h in p.get("hooks", []):
            if "`%s`" % h not in doc:
                errs.append("%s: mark %s is not in docs/GUI_TEST_HOOKS.md" % (w, h))
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", nargs="?", default="check", choices=("check", "list", "css"))
    ap.add_argument("part", nargs="?")
    a = ap.parse_args(argv)
    errs = check()
    for e in errs:
        print("  " + e)
    if a.what == "css":
        p = next((x for x in all_parts() if x["id"] == a.part), None)
        if not p:
            print("no part %r; parts: %s" % (a.part, ", ".join(x["id"] for x in all_parts())))
            return 1
        css, rep = part_css(p)
        print(css)
        print("/* %d rules; %d literals replaced by tokens; %d literals no token names: %s */" % (rep["rules"], rep["replaced"], len(rep["left_literal"]), "; ".join("%s %s %s" % t for t in rep["left_literal"][:6])))
        return 1 if errs else 0
    nav = read_json(REPO / "design" / "navigation.json")
    scr = screens(nav, (REPO / "docs" / "SCREEN_DATA_MAP.md").read_text(encoding="utf-8"))
    if a.what == "list":
        for p in all_parts():
            print("%-15s %-9s %s" % (p["id"], p["kind"], p["name"]))
        for s in scr:
            print("%-15s %-9s %s (%d rows of the data map)" % (s["id"], "screen", s["name"], len(s["rows"])))
    print("catalog: %s (%d parts, %d screens)" % ("ok" if not errs else "%d problem(s)" % len(errs), len(all_parts()), len(scr)))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
