"""Shared helper for unstructured sources (DOCX paragraphs, PDF text): find requirement-like statements.

This is segmentation by deterministic rules, not understanding. Every output keeps its locator, is flagged
Fidelity.EXTRACTED, and must be verified by a human against the source page or paragraph.
"""
from __future__ import annotations

import re

MODAL = re.compile(r"\b(shall|must|should|will)\b", re.I)
# "REQ-FCS-0212:" / "[SRS-12]" / "3.2.1" at the start of a statement
LEAD_ID = re.compile(
    r"^\s*(?:\[(?P<b>[A-Z][\w\-\.]{2,30})\]\s*"
    r"|(?P<a>[A-Z][A-Z0-9]{1,8}(?:-[A-Z0-9]+){1,4})(?:\s*[:\-\u2013)]\s*|\s+)"
    r"|(?P<n>\d+(?:\.\d+){1,5})\s+)")
SENT_SPLIT = re.compile(r"(?<=[.;])\s+(?=[A-Z0-9\[])")
HEADING = re.compile(r"^\s*(\d+(?:\.\d+)*)\s+([A-Z][^.]{2,80})$")


def candidates(block: str) -> list[tuple[str | None, str]]:
    """One block of text -> [(lead_id or None, statement)]. A block with several 'shall' sentences is split."""
    block = re.sub(r"\s+", " ", block).strip()
    if not block or not MODAL.search(block):
        return []
    parts = [s for s in SENT_SPLIT.split(block) if s.strip()]
    shall_parts = [p for p in parts if MODAL.search(p)]
    pieces = shall_parts if len(shall_parts) >= 2 and len(shall_parts) == len([p for p in parts if len(p) > 25]) else [block]
    out = []
    for p in pieces:
        m = LEAD_ID.match(p)
        lead = (m.group("b") or m.group("a") or m.group("n")) if m else None
        stmt = p[m.end():].strip() if m else p.strip()
        out.append((lead, stmt))
    return out
