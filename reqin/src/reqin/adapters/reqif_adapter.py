"""ReqIF (.reqif / .reqifz): the neutral interchange route for MSOSA (Cameo Requirements Modeler), DOORS and DOORS Next.

Built on the open-source `reqif` library (version 0.0.48 or later; XML comments are removed before it sees the file, because DOORS Next writes
`<!-- x-tinymce/html -->` inside XHTML values and the library has crashed on that, see _parse). ReqIF dialects differ by tool, so this adapter only does what is
true for every dialect: spec objects -> fields named by their attribute LONG_NAME, XHTML flattened,
enumerations resolved to their labels, hierarchy and spec relations kept. Which attribute is the 'text'
is a mapping decision, not an adapter decision.

A `.reqifz` is a zip that can hold SEVERAL .reqif files (a DOORS Next export is grouped by module): every one is read, sorted by name. If an identifier
occurs in more than one file, the later ones are kept as `<file>::<identifier>` so no record replaces another. An archive that expands to more than
1 GiB, or holds more than 1,000 .reqif files, is refused.
What the vendors document as NOT in a ReqIF file (so do not look for it here): DOORS Next leaves out links to OSLC-integrated artifacts, comments, reviews
and history; DOORS 9 leaves out pictures, tables and baselines. MSOSA's Cameo exports only the "Specifications" type with hierarchy, and which ReqIF
attribute carries its id, name and text is not documented: run `reqin discover` on a real file before trusting a profile.
"""
from __future__ import annotations

import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import has_dtd
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from .tabular import file_sha


MAX_UNCOMPRESSED = 1 << 30
MAX_MEMBERS = 1000


_COMMENT = re.compile(rb"<!--.*?-->", re.S)


def _parse(raw: bytes, name: str):
    """Parse one ReqIF document. Two things are done first, whatever the version of the library:
    a DOCTYPE or ENTITY declaration is refused (no ReqIF file needs one; they are how entity attacks are written), and XML comments are removed
    (DOORS Next writes `<!-- x-tinymce/html -->` inside XHTML values; the `reqif` library crashed on these before 0.0.48, and a test here
    shows that a comment placed first inside an XHTML value still crashes version 0.1.0). A comment carries no requirement content."""
    from reqif.parser import ReqIFParser
    if has_dtd(raw):                                                # the whole file, before any comment is removed: a declaration can hide behind a long comment
        raise ValueError(f"{name} has a DOCTYPE or ENTITY declaration; refusing to parse it (no ReqIF file needs one)")
    stripped = 0
    if b"<!--" in raw:
        raw, stripped = _COMMENT.subn(b"", raw)
    with tempfile.TemporaryDirectory() as d:
        target = Path(d) / "doc.reqif"                              # a name of our own: nothing in an archive decides where a file goes
        target.write_bytes(raw)
        try:
            return ReqIFParser.parse(str(target))
        except Exception as e:  # the library raises many types
            try:
                import importlib.metadata as md
                ver = md.version("reqif")
            except Exception:  # noqa: BLE001
                ver = "unknown"
            raise ValueError(f"could not read {name} as ReqIF ({type(e).__name__}: {str(e)[:120]}; {stripped} XML comments were removed first). "
                             f"Installed reqif library: {ver}; use 0.0.48 or later. A file that is not ReqIF fails the same way.") from None


def _open_all(path: str) -> list[tuple[str, Any]]:
    """[(name, parsed ReqIF)]: one for a .reqif, one per .reqif inside a .reqifz (sorted by name)."""
    if not zipfile.is_zipfile(path):
        return [(Path(path).name, _parse(Path(path).read_bytes(), Path(path).name))]
    with zipfile.ZipFile(path) as z:
        inners = sorted((i for i in z.infolist() if i.filename.lower().endswith(".reqif") and not i.is_dir()), key=lambda i: i.filename)
        if not inners:
            raise ValueError(f"no .reqif file inside {Path(path).name}")
        if len(inners) > MAX_MEMBERS or sum(i.file_size for i in inners) > MAX_UNCOMPRESSED:
            raise ValueError(f"{Path(path).name} holds {len(inners)} .reqif files of {sum(i.file_size for i in inners) >> 20} MiB: more than the limits "
                             f"({MAX_MEMBERS} files, {MAX_UNCOMPRESSED >> 20} MiB); refusing to expand it")
        return [(i.filename, _parse(z.read(i), i.filename)) for i in inners]


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
        """One tuple per .reqif: (file name, parsed, content, enum labels, spec-type names, attribute names)."""
        docs = []
        for name, b in _open_all(src.uri):
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
            docs.append((name, b, c, enum_labels, type_name, attr_name))
        return docs

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
        docs = self._load(src)
        by_type: dict[str, list[dict[str, str]]] = {}
        rels = specs = warnings = 0
        for _, b, c, enums, tname, aname in docs:
            for so in c.spec_objects or []:
                f = self._fields(so, aname, enums, tname)
                by_type.setdefault(f["_spec_type"], []).append({k: v for k, v in f.items() if not k.startswith("_")})
            rels += len(c.spec_relations or [])
            specs += len(c.specifications or [])
            warnings += len(b.exceptions or [])
        cs = []
        for t, rows in by_type.items():
            cols = list(dict.fromkeys(k for r in rows for k in r))
            cs.append(Container(t, len(rows), [make_field_info(col, [r.get(col, "") for r in rows]) for col in cols]))
        notes = [f"{rels} spec relations", f"{specs} specifications"]
        if len(docs) > 1:
            notes.append(f"{len(docs)} .reqif files read: " + ", ".join(d[0] for d in docs[:8]) + (" ..." if len(docs) > 8 else ""))
        if warnings:
            notes.append(f"{warnings} schema warnings from the parser")
        return Discovery(cs, notes)

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        docs = self._load(src)
        rev = self.revision(src)
        seen_ids: set[str] = set()
        n = 0
        for di, (fname, b, c, enums, tname, aname) in enumerate(docs):
            mine = {so.identifier for so in (c.spec_objects or [])}
            clash = mine & seen_ids if di else set()
            nid = (lambda ident, clash=clash, fname=fname: f"{fname}::{ident}" if ident in clash else ident)
            seen_ids |= mine
            parent: dict[str, str | None] = {}
            order: dict[str, int] = {}
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

            def label(oid: str, objs=objs, enums=enums, tname=tname, aname=aname) -> str:
                f = self._fields(objs[oid], aname, enums, tname) if oid in objs else {}
                return f.get("ReqIF.ChapterName") or f.get("ReqIF.Name") or (objs[oid].long_name if oid in objs else "") or oid

            def section(oid: str, parent=parent, label=label) -> str:      # heading path above this object, e.g. "3 Performance / 3.2 Latency"
                path, cur = [], parent.get(oid)
                while cur:
                    path.append(label(cur))
                    cur = parent.get(cur)
                return " / ".join(reversed(path))

            for so in c.spec_objects or []:
                f = self._fields(so, aname, enums, tname)
                f["_section"] = section(so.identifier)
                if len(docs) > 1:
                    f["_file"] = fname
                pid = parent.get(so.identifier)
                yield RawRecord(native_id=nid(so.identifier), fields=f, parent_native_id=nid(pid) if pid else None,
                                order=order.get(so.identifier, n),
                                ref=SourceRef("reqif", src.uri, container=f["_spec_type"], locator=nid(so.identifier), revision=rev))
            rel_types = {t.identifier: (t.long_name or t.identifier) for t in (c.spec_types or []) if type(t).__name__ == "ReqIFSpecRelationType"}
            for r in c.spec_relations or []:
                yield RawLink(nid(r.source), nid(r.target), (rel_types.get(r.relation_type_ref) or "trace").lower(),
                              SourceRef("reqif", src.uri, container="relations", locator=r.identifier, revision=rev))

    def revision(self, src: Source) -> str:
        return file_sha(src.uri)
