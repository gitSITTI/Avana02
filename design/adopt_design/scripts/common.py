"""Shared by the scripts in this folder: where things are, reading and writing JSON, and small value helpers. Standard library only."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent
REPO = KIT.parent.parent
TOKENS_CSS = REPO / "design" / "tokens.css"
sys.path.insert(0, str(REPO / "design" / "ui_from_image" / "scripts"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import colour as C  # noqa: E402,F401  (re-exported: the same OKLab arithmetic the image kit uses)


def read_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def write_json(p, obj):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def digest(obj) -> str:
    """A short fingerprint of anything JSON can hold. The same answers always give the same digest."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def px(value, root: float = 16.0):
    """'12px' -> 12.0, '0.5rem' -> 8.0, '0' -> 0.0, anything else (auto, normal, a keyword, a pair of values) -> None."""
    if value is None:
        return None
    v = str(value).strip().lower()
    m = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(px|rem|em)?", v)
    if not m:
        return None
    n = float(m.group(1))
    return n * root if m.group(2) in ("rem", "em") else n


def fmt_px(n: float) -> str:
    return ("%g" % round(n, 2)) + "px"


def first_family(stack: str) -> str:
    return (stack or "").split(",")[0].strip().strip("\"'")


def css_vars(css_text: str) -> dict:
    """Every --name: value declared in the first :root block of a stylesheet, as written."""
    m = re.search(r":root\s*\{(.*?)\n\}", css_text, flags=re.S)
    block = m.group(1) if m else css_text
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", block)}
