"""SysML v2 textual notation (.sysml): a LIGHTWEIGHT reader for requirement definitions/usages.

Fidelity = PARSED, not STRUCTURED. This is a regex/brace scanner, good enough to pull `requirement` elements,
their short names, `doc` comments, typing, nesting and `satisfy ... by ...` out of typical files.
It does not resolve imports, redefinitions, expressions or units. For production use the OMG Pilot
Implementation (or the Systems Modeling API, see sysml_api.py), which parse the full grammar.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from .tabular import file_sha

_HDR = re.compile(
    r"\b(?P<kind>requirement\s+def|requirement)\s+(?:<(?P<short>[^>]+)>\s*)?(?P<name>'[^']+'|[A-Za-z_]\w*)?"
    r"\s*(?::>?\s*(?P<typ>[\w:\.']+))?\s*(?P<end>\{|;)")
_DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.S)
_SAT = re.compile(r"\bsatisfy\s+(?:requirement\s+)?(?P<req>[\w:\.']+)\s+by\s+(?P<by>[\w:\.']+)\s*;")
_PKG = re.compile(r"\bpackage\s+(?P<name>'[^']+'|[A-Za-z_]\w*)\s*\{")


def _unq(s: str | None) -> str:
    return (s or "").strip().strip("'")


def _mask_comments(text: str) -> str:
    """Blank out comments and string literals (same length, newlines kept) so headers and braces inside them cannot match."""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"\\])*\"", blank, text, flags=re.S)


def _match_brace(masked: str, open_idx: int) -> int:
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(masked) - 1


def _clean_doc(raw: str) -> str:
    lines = [re.sub(r"^\s*\*\s?", "", ln).strip() for ln in raw.strip().splitlines()]
    return " ".join(ln for ln in lines if ln)


@register
class SysMLTextAdapter(Adapter):
    name = "sysml_text"
    fidelity = Fidelity.PARSED
    caps = Caps(structured_ids=True, links=True, hierarchy=True)

    def sniff(self, src: Source) -> float:
        p = Path(src.uri)
        if p.suffix.lower() == ".sysml":
            return 0.95
        return 0.0

    def _scan(self, masked: str, orig: str, base: int, qprefix: str, parent: str | None, out: list, seq: list[int]) -> None:
        pos = 0
        while True:
            m = _HDR.search(masked, pos)
            if not m:
                return
            name, short = _unq(m.group("name")), _unq(m.group("short"))
            q = (qprefix + "::" if qprefix else "") + (name or short or f"anon{seq[0]}")
            seq[0] += 1
            item = {"shortName": short, "name": name, "kind": re.sub(r"\s+", " ", m.group("kind")), "typedBy": _unq(m.group("typ")),
                    "doc": "", "qualifiedName": q}
            if m.group("end") == ";":
                out.append((q, item, parent, base + m.start()))
                pos = m.end()
                continue
            o = m.end() - 1
            c = _match_brace(masked, o)
            body_m, body_o = masked[o + 1:c], orig[o + 1:c]
            nested, at = [], 0
            while True:                                      # top-level nested requirement bodies only
                mm = _HDR.search(body_m, at)
                if not mm:
                    break
                if mm.group("end") == "{":
                    end = _match_brace(body_m, mm.end() - 1) + 1
                    nested.append((mm.start(), end))
                    at = end
                else:
                    at = mm.end()
            own = body_o
            for a, b in reversed(nested):
                own = own[:a] + " " * (b - a) + own[b:]
            d = _DOC.search(own)
            item["doc"] = _clean_doc(d.group(1)) if d else ""
            out.append((q, item, parent, base + m.start()))
            self._scan(body_m, body_o, base + o + 1, q, q, out, seq)
            pos = c + 1

    def _items(self, src: Source):
        text = Path(src.uri).read_text(encoding="utf-8", errors="replace")
        out: list = []
        self._scan(_mask_comments(text), text, 0, "", None, out, [0])
        return text, out

    def discover(self, src: Source) -> Discovery:
        _, items = self._items(src)
        rows = [i[1] for i in items]
        kinds = sorted({r["kind"] for r in rows})
        cs = []
        for k in kinds:
            sub = [r for r in rows if r["kind"] == k]
            cs.append(Container(k, len(sub), [make_field_info(c, [r[c] for r in sub]) for c in ("shortName", "name", "doc", "typedBy")]))
        return Discovery(cs, ["lightweight parser (fidelity=parsed): use the Pilot Implementation or the API for full-grammar fidelity"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        text, items = self._items(src)
        rev = self.revision(src)
        by_name: dict[str, str] = {}
        for q, item, _, _ in items:                      # resolve plain names to qualified names (first definition wins)
            for key in (item["name"], item["shortName"], q):
                if key:
                    by_name.setdefault(key, q)
        res = lambda n: by_name.get(n.split("::")[-1].strip("'"), by_name.get(n, n))  # noqa: E731
        for n, (q, item, parent, off) in enumerate(items):
            line = text.count("\n", 0, off) + 1
            yield RawRecord(native_id=q, fields=item, parent_native_id=parent, order=n,
                            ref=SourceRef("sysml_text", src.uri, container=item["kind"], locator=f"L{line}:{q}", revision=rev))
            if item["typedBy"]:
                yield RawLink(q, res(item["typedBy"]), "instance-of", SourceRef("sysml_text", src.uri, "relations", f"L{line}", rev))
        for m in _SAT.finditer(_mask_comments(text)):
            line = text.count("\n", 0, m.start()) + 1
            yield RawLink(m.group("by"), res(m.group("req")), "satisfy", SourceRef("sysml_text", src.uri, "relations", f"L{line}", rev))

    def revision(self, src: Source) -> str:
        return file_sha(src.uri)
