#!/usr/bin/env python3
"""Read an app's source and report what makes a screen a painting instead of a view of a dataset. No browser needed; runs in a second.

    python3 tools/gui_checks/hardcode_scan.py design/reference_viewer
    python3 tools/gui_checks/hardcode_scan.py my_app/ --json findings.json --strict

Each finding names the file and line, the rule and why it matters. Rules:

  typed-in-requirement   a sentence with 'shall' typed into markup or a string: sample data
  typed-in-id            something shaped like a requirement ID (ABC-0123) typed into markup or a string
  typed-in-record        an object written out with uid/text keys: a list of records in code
  typed-in-count         a count hook (data-testid="count-...", "row-total") whose element already holds a number
  literal-colour         a colour written as #hex, rgb(), hsl() or a colour name instead of a design token (var(--...))
  literal-font           a font-family that is not var(--...)
  html-injection         innerHTML, outerHTML, insertAdjacentHTML, document.write: a requirement containing markup would be run, not shown
  dynamic-code           eval() or new Function()
  outside-data           fetch/XMLHttpRequest/WebSocket to an absolute address, or an import of a script or stylesheet from another site
  storage                localStorage, sessionStorage or indexedDB: a second source of data (a warning: fine for a remembered filter, wrong for records)

tokens.css and tokens.json (the design's own values) and font files are not scanned. A hit is a reason to look, not a proof: a colour name inside a sentence
can be a false alarm, and the scan cannot see code that builds the same things at run time from pieces. The probe (probe.py) is the check that shows what
the screen really does. Exit status 1 when there is an error (a warning counts only with --strict). Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CODE = {".js", ".mjs", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
STYLE = {".css", ".scss"}
MARK = {".html", ".htm"}
SKIP_DIRS = {"node_modules", "dist", "build", ".git", "fonts", "__pycache__", "vendor"}
SKIP_FILES = {"tokens.css", "tokens.json"}

COLOUR_NAMES = r"white|black|red|green|blue|gray|grey|orange|yellow|purple|pink|brown|navy|teal|silver|maroon|olive|lime|aqua|cyan|magenta"
RULES = [
    ("html-injection", "error", re.compile(r"\.(innerHTML|outerHTML)\b|insertAdjacentHTML|document\.write\(|dangerouslySetInnerHTML|v-html"), CODE | MARK,
     "dataset text would be parsed as markup. Use textContent (or the framework's text binding)"),
    ("dynamic-code", "error", re.compile(r"\beval\s*\(|new\s+Function\s*\("), CODE | MARK, "running text as code"),
    ("outside-data", "error", re.compile(r"(fetch\s*\(\s*[`'\"]https?:|XMLHttpRequest|new\s+WebSocket\s*\(|new\s+EventSource\s*\(|<script[^>]+src=[\"']https?:|<link[^>]+href=[\"']https?:|@import\s+(url\()?[\"']?https?:|url\([\"']?https?:)"),
     CODE | MARK | STYLE, "a screen reads only a dataset and works offline: every script, stylesheet and font is a local file"),
    ("storage", "warn", re.compile(r"\b(localStorage|sessionStorage|indexedDB)\b"), CODE | MARK, "a second source of data; fine for a remembered filter, wrong for records"),
    ("literal-colour", "error", re.compile(r"(?<![\w&\-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b(?![\w-])|\b(?:rgba?|hsla?|oklch|oklab)\s*\(|(?:color|background(?:-color)?|border(?:-[a-z]+)*|fill|stroke|outline(?:-color)?)\s*:[^;}\"'{]*(?<![\w-])(?:" + COLOUR_NAMES + r")(?![\w-])"),
     CODE | MARK | STYLE, "write colours as design tokens, var(--name); a literal drifts from the design and from the other screens"),
    ("literal-font", "error", re.compile(r"font-family\s*:(?!\s*(?:var\(|inherit|initial|unset))[^;}\"']+|fontFamily\s*[:=]\s*[\"'](?!var\()"), CODE | MARK | STYLE,
     "use the token fonts, var(--sans), var(--serif), var(--mono); a name that is not loaded falls back silently"),
    ("typed-in-requirement", "error", re.compile(r"[\"'>`][^\"'<>`\n]{3,}\b(shall|shall not)\b[^\"'<>`\n]{8,}[\"'<`]"), CODE | MARK, "sample requirement text typed into the screen"),
    ("typed-in-id", "error", re.compile(r"[\"'>`]\s*(?!(?:SHA|UTF|ISO|RFC|AES|MD|TLS|SSL|ASCII)-)[A-Z]{2,6}-\d{2,6}\b"), CODE | MARK, "a requirement ID typed into the screen"),
    ("typed-in-record", "error", re.compile(r"[\"']?\buid[\"']?\s*:\s*[\"'`]"), CODE | MARK, "records written out in code"),
    ("typed-in-count", "error", re.compile(r"data-testid=[\"'](?:count-[\w-]+|row-total)[\"'][^>]*>\s*[\d,]+\s*<"), MARK, "a count typed into the markup; it must come from the dataset"),
]


def blank_comments(text: str, suffix: str) -> str:
    """The text with comments replaced by spaces (newlines kept so line numbers stay true)."""
    if suffix in MARK:
        return re.sub(r"<!--.*?-->", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    out, i, n, q = [], 0, len(text), None
    line_comments = suffix in CODE
    while i < n:
        c, d = text[i], text[i + 1] if i + 1 < n else ""
        if q:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
        elif c in "\"'`" and not (suffix in STYLE and c == "'" and False):
            q = c
            out.append(c)
            i += 1
        elif c == "/" and d == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append(re.sub(r"[^\n]", " ", text[i:j]))
            i = j
        elif line_comments and c == "/" and d == "/" and (i == 0 or text[i - 1] != ":"):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def scan_text(text: str, suffix: str, name: str) -> list[dict]:
    clean = blank_comments(text, suffix)
    lines = clean.split("\n")
    found = []
    for rule, sev, rx, kinds, why in RULES:
        if suffix not in kinds:
            continue
        for lineno, line in enumerate(lines, 1):
            for m in rx.finditer(line):
                if rule == "literal-colour" and re.search(r"(href|src|id|for|url)\s*[=(]\s*[\"']?$", line[:m.start()]):
                    continue                                    # an anchor such as href="#add", not a colour
                if rule == "literal-colour" and suffix in MARK and re.search(r"href=[\"']#", line[max(0, m.start() - 8):m.start() + 1]):
                    continue
                found.append({"file": name, "line": lineno, "rule": rule, "severity": sev, "why": why, "text": line.strip()[:140]})
    return found


def scan(root: str | Path) -> list[dict]:
    root = Path(root)
    if not root.is_dir():
        raise SystemExit("%s is not a folder" % root)
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE | STYLE | MARK or p.name in SKIP_FILES or p.name.endswith(".min.js"):
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts[:-1]):
            continue
        out += scan_text(p.read_text(encoding="utf-8", errors="replace"), p.suffix.lower(), str(p.relative_to(root)))
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app", help="the app's folder")
    ap.add_argument("--json", metavar="FILE")
    ap.add_argument("--strict", action="store_true", help="count warnings as errors")
    a = ap.parse_args(argv)
    found = scan(a.app)
    for f in found:
        print("%s:%d  %-20s %-5s %s\n      %s" % (f["file"], f["line"], f["rule"], f["severity"], f["text"], f["why"]))
    errors = [f for f in found if f["severity"] == "error" or a.strict]
    print("\n%d errors, %d warnings in %s" % (sum(1 for f in found if f["severity"] == "error"), sum(1 for f in found if f["severity"] == "warn"), a.app))
    print("Not checked: anything built at run time from pieces, images, and what the screen actually does (that is probe.py).")
    if a.json:
        Path(a.json).write_text(json.dumps({"format": "reqin-hardcode-scan/1", "findings": found}, indent=1) + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
