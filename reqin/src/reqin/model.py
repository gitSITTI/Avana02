"""Canonical model: the ONE shape every source is translated into.

Rules that keep the rest of the app source-agnostic:
  * Adapters never decide meaning. They emit RawRecord / RawLink (what the source said).
  * Mapping profiles (data, not code) turn raw fields into canonical fields.
  * Nothing is dropped silently: every RawRecord ends up as a Requirement or a Rejected row.
  * Every canonical field carries a confidence label, and every record carries its source locator
    so a human can jump back to the original.
"""
from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Fidelity(str, Enum):
    STRUCTURED = "structured"  # native model / interchange with stable IDs and links (ReqIF, SysML v2 API)
    TABULAR = "tabular"        # rows with mapped columns (CSV, XLSX, SQL)
    PARSED = "parsed"          # lightweight parse of a structured text notation (SysML v2 textual)
    EXTRACTED = "extracted"    # segmented out of prose (DOCX, PDF): a human must verify every record


class Conf(str, Enum):
    EXACT = "Exact"    # copied verbatim from a field the profile names
    HIGH = "High"      # derived by a deterministic rule from a named field
    MEDIUM = "Medium"  # guessed by a heuristic or inherited from a parent: human confirms
    LOW = "Low"        # extracted from prose or defaulted


@dataclass(frozen=True)
class SourceRef:
    adapter: str           # e.g. "reqif"
    uri: str               # file path, connection name or URL
    container: str = ""    # sheet, specification, table, document, page
    locator: str = ""      # row number, identifier, "p3:para12" ... enough to jump back
    revision: str = ""     # file hash, commit id, query hash


@dataclass
class RawRecord:
    """What the source said, before any interpretation."""
    native_id: str | None
    fields: dict[str, Any]
    ref: SourceRef
    parent_native_id: str | None = None
    order: int = 0


@dataclass
class RawLink:
    source_native_id: str
    target_native_id: str
    kind: str              # satisfy | derive | verify | refine | contain | trace | instance-of ...
    ref: SourceRef


@dataclass
class Slots:
    """Machine-readable parts of the statement, filled deterministically by normalise.py."""
    modal: str = ""                      # shall | should | will | may | must | ""
    negated: bool = False
    quantities: list[dict[str, Any]] = field(default_factory=list)  # value, unit, comparator, raw


@dataclass
class Requirement:
    mid: str                             # machine ID: stable, never shown to people
    uid: str                             # human ID as the source shows it
    uid_synthetic: bool                  # True when we had to invent it
    text: str                            # original statement, untouched except for markup stripping
    norm_text: str                       # normalised for comparison (see normalise.py)
    fingerprint: str                     # hash of norm_text + slots; changes only if meaning-bearing text changes
    slots: Slots
    fields: dict[str, Any]               # canonical optional fields: rationale, verification, allocation, owner, baseline, status
    extra: dict[str, Any]                # every source field the profile did not claim: lossless
    conf: dict[str, Conf]                # per canonical field
    ref: SourceRef
    fidelity: Fidelity
    parent_mid: str | None = None


@dataclass
class Link:
    source_uid: str                      # kept even when an end is outside this import
    target_uid: str
    kind: str
    ref: SourceRef
    source_mid: str | None = None        # None when that end is not a requirement in this import
    target_mid: str | None = None


@dataclass
class Rejected:
    ref: SourceRef
    reason: str
    fields: dict[str, Any]


@dataclass
class IngestResult:
    requirements: list[Requirement]
    links: list[Link]
    rejected: list[Rejected]
    report: dict[str, Any]


def make_mid(namespace: str, native_id: str) -> str:
    return "m_" + hashlib.sha1(f"{namespace}\x1f{native_id}".encode("utf-8")).hexdigest()[:12]


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)
