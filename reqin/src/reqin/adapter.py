"""The adapter contract (the 'port') and the registry.

An adapter knows ONE thing: how to read a kind of source and say what it contains.
It never maps fields to meaning (mapping.py does) and never judges requirements (the pipeline does).
New formats = new adapter + fixture + passing the conformance suite. No other file changes.
"""
from __future__ import annotations

import importlib
import importlib.metadata
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator

from .model import Fidelity, RawLink, RawRecord


@dataclass(frozen=True)
class Source:
    uri: str                                   # path, URL or connection name
    options: dict[str, Any] = field(default_factory=dict)  # sheet, query, url, project_id ...


@dataclass(frozen=True)
class Caps:
    structured_ids: bool = False   # source has stable native IDs
    links: bool = False            # source carries relationships
    hierarchy: bool = False        # source carries parent/child structure
    write_back: bool = False       # adapter can push changes back (default: read-only)
    incremental: bool = False      # adapter can read only what changed since a revision


@dataclass
class FieldInfo:
    name: str
    samples: list[str]
    non_empty: float               # 0..1
    unique: float                  # 0..1
    modal_ratio: float             # share of non-empty values containing shall/should/will/must/may
    mean_len: float


@dataclass
class Container:
    name: str                      # sheet, spec type, table, document section
    rows: int
    fields: list[FieldInfo]


@dataclass
class Discovery:
    containers: list[Container]
    notes: list[str] = field(default_factory=list)


class Adapter(ABC):
    name: str = ""
    fidelity: Fidelity = Fidelity.TABULAR
    caps: Caps = Caps()

    @abstractmethod
    def sniff(self, src: Source) -> float:
        """0..1: how sure am I that I can read this? Must be cheap (look at name and first bytes)."""

    @abstractmethod
    def discover(self, src: Source) -> Discovery:
        """Describe containers and fields with samples, so a human or a heuristic can build a mapping."""

    @abstractmethod
    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        """Stream what the source says, untouched. Must be read-only and deterministic."""

    def revision(self, src: Source) -> str:
        """A string that changes when the source changes (file hash, commit id, query hash)."""
        return ""


_REGISTRY: dict[str, type[Adapter]] = {}


def register(cls: type[Adapter]) -> type[Adapter]:
    if not cls.name:
        raise ValueError("adapter needs a name")
    _REGISTRY[cls.name] = cls
    return cls


def load_adapters() -> dict[str, type[Adapter]]:
    """Built-ins plus any third-party package that declares the 'reqin.adapters' entry-point group."""
    for mod in ("tabular", "reqif_adapter", "sysml_text", "sysml_api", "sql", "docx_adapter", "pdf_adapter", "mdzip"):
        importlib.import_module(f"reqin.adapters.{mod}")
    for ep in importlib.metadata.entry_points(group="reqin.adapters"):
        ep.load()  # importing registers it
    return dict(_REGISTRY)


def sniff_all(src: Source) -> list[tuple[float, str]]:
    out = []
    for name, cls in load_adapters().items():
        try:
            score = cls().sniff(src)
        except Exception:  # a broken sniff must never block the others
            score = 0.0
        if score > 0:
            out.append((score, name))
    return sorted(out, reverse=True)


def pick_adapter(src: Source, name: str | None = None) -> Adapter:
    reg = load_adapters()
    if name:
        return reg[name]()
    ranked = sniff_all(src)
    if not ranked or ranked[0][0] < 0.5:
        raise ValueError(f"no adapter recognises {src.uri!r}; ranked={ranked}")
    return reg[ranked[0][1]]()


def profile_fields(values: list[str]) -> dict[str, float]:
    """Shared column statistics used by every adapter's discover()."""
    import re
    vals = [v for v in values if v not in ("", None)]
    n = len(values) or 1
    modal = re.compile(r"\b(shall|should|will|must|may)\b", re.I)
    return {
        "non_empty": len(vals) / n,
        "unique": (len(set(vals)) / len(vals)) if vals else 0.0,
        "modal_ratio": (sum(1 for v in vals if modal.search(str(v))) / len(vals)) if vals else 0.0,
        "mean_len": (sum(len(str(v)) for v in vals) / len(vals)) if vals else 0.0,
    }


def make_field_info(name: str, values: list[Any]) -> FieldInfo:
    strs = ["" if v is None else str(v) for v in values]
    st = profile_fields(strs)
    return FieldInfo(name=name, samples=[s for s in strs if s][:3], **st)
