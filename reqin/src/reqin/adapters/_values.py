"""Turning field values from a JSON API into text, shared by the Jira and Polarion readers: nothing is dropped, an unknown object keeps its JSON,
and Atlassian Document Format (a JSON tree) is flattened to plain text."""
from __future__ import annotations

import json
from collections import Counter
from typing import Any


# ---- Atlassian Document Format -> text -----------------------------------------------------------------
def _inline(n: dict[str, Any], skipped: Counter) -> str:
    t, a = n.get("type"), n.get("attrs") or {}
    if t == "text":
        return str(n.get("text", ""))
    if t == "hardBreak":
        return "\n"
    if t == "mention":
        return str(a.get("text") or ("@" + str(a.get("id", ""))))
    if t == "emoji":
        return str(a.get("text") or a.get("shortName") or "")
    if t in ("inlineCard", "blockCard"):
        return str(a.get("url") or "")
    if t == "status":
        return str(a.get("text") or "")
    if t == "date":
        return str(a.get("timestamp") or "")
    kids = n.get("content") or []
    if kids:
        return "".join(_inline(k, skipped) for k in kids if isinstance(k, dict))
    skipped[str(t)] += 1
    return ""


def _block(n: dict[str, Any], skipped: Counter) -> list[str]:
    t, kids = n.get("type"), [k for k in (n.get("content") or []) if isinstance(k, dict)]
    if t in ("paragraph", "heading", "codeBlock"):
        s = "".join(_inline(k, skipped) for k in kids)
        return s.split("\n") if s else []
    if t in ("bulletList", "orderedList"):
        out: list[str] = []
        for i, li in enumerate(kids, 1):
            mark = "- " if t == "bulletList" else f"{i}. "
            sub = _block(li, skipped)
            out += ([mark + sub[0]] + ["  " + x for x in sub[1:]]) if sub else [mark.rstrip()]
        return out
    if t == "tableRow":
        return [" | ".join(" ".join(_block(c, skipped)) for c in kids)]
    if t in ("media", "mediaSingle", "mediaGroup", "mediaInline"):
        skipped["media"] += 1
        return []
    if t in ("rule",):
        return []
    if not kids:
        s = _inline(n, skipped)
        return s.split("\n") if s else []
    out = []
    for k in kids:
        out += _block(k, skipped)
    return out


def adf_text(doc: dict[str, Any], skipped: Counter | None = None) -> str:
    return "\n".join(_block(doc, skipped if skipped is not None else Counter())).strip()


def plain(v: Any, skipped: Counter | None = None) -> str:
    """A Jira field value as text: nothing is dropped, an unknown object keeps its JSON."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return ", ".join(s for s in (plain(x, skipped) for x in v) if s)
    if isinstance(v, dict):
        if v.get("type") == "doc" and "content" in v:
            return adf_text(v, skipped)
        for k in ("value", "displayName", "name", "key"):
            if v.get(k) not in (None, ""):
                return plain(v[k], skipped)
        return json.dumps(v, sort_keys=True, ensure_ascii=False)
    return str(v)
