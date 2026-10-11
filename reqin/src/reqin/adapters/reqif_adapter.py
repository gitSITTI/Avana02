"""ReqIF (.reqif / .reqifz): the neutral interchange route for MSOSA (Cameo Requirements Modeler), DOORS and DOORS Next.

Built on the open-source `reqif` library. ReqIF dialects differ by tool, so this adapter only does what is
true for every dialect: spec objects -> fields named by their attribute LONG_NAME, XHTML flattened,
enumerations resolved to their labels, hierarchy and spec relations kept. Which attribute is the 'text'
is a mapping decision, not an adapter decision.
"""
from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from .tabular import file_sha


def _open(path: str):
    from reqif.parser import ReqIFParser
    if zipfile.is_zipfile(path):  # .reqifz: first *.reqif inside
        with zipfile.ZipFile(path) as z, tempfile.TemporaryDirectory() as d:
            inner = next(n for n in z.namelist() if n.lower().endswith(".reqif"))
            z.extract(inner, d)
            return ReqIFParser.parse(str(Path(d) / inner))
    return ReqIFParser.parse(path)


@register
class ReqIFAdapter(Adapter):
    name = "reqif"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True)

    def sniff(self, src: Source) -> float:
        p = Path(src.uri)
        if p.suffix.lower() == ".reqifz":
            return 0.95
        try:
            head = p.read_bytes()[:4096]
        except OSError:
            return 0.0
        if b"<REQ-IF" in head:
            return 1.0
        return 0.6 if p.suffix.lower() == ".reqif" else 0.0

    # -- internals ------------------------------------------------------------------------------
    def _load(self, src: Source):
        b = _open(src.uri)
        c = b.core_content.req_if_content
        enum_labels: dict[str, str] = {}
        for dt in (c.data_types or []):
            for v in (getattr(dt, "values", None) or []):
                enum_labels[v.identifier] = v.long_name or v.identifier
        type_name: dict[str, str] = {}
        attr_name: dict[str, str] = {}
        for t in (c.spec_types or []):
            if type(t).__name__ == "ReqIFSpecObjectType":
                type_name[t.identifier] = t.long_name or t.identifier
                for a in (t.attribute_definitions or []):
                    attr_name[a.identifier] = a.long_name or a.identifier
        return b, c, enum_labels, type_name, attr_name

    def _fields(self, so, attr_name, enum_labels, type_name) -> dict[str, str]:
        from reqif.models.reqif_spec_object import SpecObjectAttributeType as T
        f: dict[str, str] = {}
        for a in so.attributes:
            label = attr_name.get(a.definition_ref, a.definition_ref)
            if a.attribute_type == T.ENUMERATION:
                vals = a.value if isinstance(a.value, list) else [a.value]
                f[label] = ", ".join(enum_labels.get(v, v) for v in vals)
            elif a.attribute_type == T.XHTML:
                f[label] = a.value_stripped_xhtml or (a.value if isinstance(a.value, str) else "")
            else:
                f[label] = a.value if isinstance(a.value, str) else ", ".join(a.value)
        f["_spec_type"] = type_name.get(so.spec_object_type, so.spec_object_type)
        f["_identifier"] = so.identifier
        if so.last_change:
            f["_last_change"] = so.last_change
        return f

    def discover(self, src: Source) -> Discovery:
        b, c, enums, tname, aname = self._load(src)
        by_type: dict[str, list[dict[str, str]]] = {}
        for so in c.spec_objects or []:
            f = self._fields(so, aname, enums, tname)
            by_type.setdefault(f["_spec_type"], []).append({k: v for k, v in f.items() if not k.startswith("_")})
        cs = []
        for t, rows in by_type.items():
            cols = list(dict.fromkeys(k for r in rows for k in r))
            cs.append(Container(t, len(rows), [make_field_info(col, [r.get(col, "") for r in rows]) for col in cols]))
        notes = [f"{len(c.spec_relations or [])} spec relations", f"{len(c.specifications or [])} specifications"]
        if b.exceptions:
            notes.append(f"{len(b.exceptions)} schema warnings from the parser")
        return Discovery(cs, notes)

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        b, c, enums, tname, aname = self._load(src)
        rev = self.revision(src)
        parent: dict[str, str | None] = {}
        order: dict[str, int] = {}
        n = 0
        for spec in c.specifications or []:
            stack = list(reversed(spec.children or []))
            parents = {id(h): None for h in (spec.children or [])}
            while stack:                                   # depth-first, document order
                h = stack.pop()
                parent[h.spec_object] = parents[id(h)]
                order[h.spec_object] = n
                n += 1
                for ch in reversed(h.children or []):
                    parents[id(ch)] = h.spec_object
                    stack.append(ch)
        objs = {so.identifier: so for so in (c.spec_objects or [])}

        def label(oid: str) -> str:
            f = self._fields(objs[oid], aname, enums, tname) if oid in objs else {}
            return f.get("ReqIF.ChapterName") or f.get("ReqIF.Name") or (objs[oid].long_name if oid in objs else "") or oid

        def section(oid: str) -> str:           # heading path above this object, e.g. "3 Performance / 3.2 Latency"
            path, cur = [], parent.get(oid)
            while cur:
                path.append(label(cur))
                cur = parent.get(cur)
            return " / ".join(reversed(path))

        for so in c.spec_objects or []:
            f = self._fields(so, aname, enums, tname)
            f["_section"] = section(so.identifier)
            yield RawRecord(native_id=so.identifier, fields=f, parent_native_id=parent.get(so.identifier),
                            order=order.get(so.identifier, n),
                            ref=SourceRef("reqif", src.uri, container=f["_spec_type"], locator=so.identifier, revision=rev))
        rel_types = {t.identifier: (t.long_name or t.identifier) for t in (c.spec_types or []) if type(t).__name__ == "ReqIFSpecRelationType"}
        for r in c.spec_relations or []:
            yield RawLink(r.source, r.target, (rel_types.get(r.relation_type_ref) or "trace").lower(),
                          SourceRef("reqif", src.uri, container="relations", locator=r.identifier, revision=rev))

    def revision(self, src: Source) -> str:
        return file_sha(src.uri)
