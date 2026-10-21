"""SysML 1.x / UML models as XMI: .xmi, .xml, .mdxml, .uml, and the MSOSA / Cameo / MagicDraw project file .mdzip. Replaces the old `mdzip` stub.

STATUS: fixture-tested only. The fixtures were written from the vendor's documentation, not from a real project: no real MSOSA, Cameo or MagicDraw file
has been read by this code. The parts the documentation states: from 17.0.1 a .mdzip is a zip of XMI 2.4 and other resources, the model is the entry
`com.nomagic.magicdraw.uml_model.model`, used projects sit in further entries (`...shared_model`, `proxy...`); before 17.0.1 it was ONE compressed XMI.
The Requirement stereotype has the properties Id and Text (OMG's SysML 1.x spells them id and text, so both are read), the six relationship
properties on a requirement (SatisfiedBy and so on) are DERIVED, not stored, so relationships are read from the relationship elements, and nested
requirements are UML nesting. What is NOT documented and was built from the shape of XMI and UML: the XML namespaces (matching is on local names, so 2.4
and 2.5 both work), that a stereotype application is a sibling of the model element with a `base_Class` attribute, that documentation is an
`ownedComment` with a `body`, that a relationship is a `uml:Abstraction` with `client` and `supplier`, and the back-pointer `base_Abstraction`.
Look at one real file (tests/fixtures_approved/README.md says how) before trusting any of this.

WHAT IS READ
  requirements    every class that carries a Requirement application (a sibling element named Requirement or ExtendedRequirement, or one of the names in
                  the option requirement_stereotypes, whose base_Class points at the class). A requirement is never dropped for lacking text: that is the
                  profile's call. An application whose class is not in this file (a used project) is still read, from the application's own values.
  fields          Id, Text (spelling normalised; both the attribute form and the child-element form are read), Name (the class), Documentation (its comments),
                  Package (the packages around it, joined with ::), Stereotype, ElementType, and every other property of the application as written.
  hierarchy       a requirement nested in a requirement (UML nesting) has the outer one as parent. Packages are NOT parents: they are in the Package field.
  links           every Abstraction, Dependency, Realization, Usage or Substitution that has a requirement at one end and ONE of the two ends: client is the
                  SOURCE, supplier the TARGET (the vendor's description: satisfy, verify and refine have the design or test element as client and the
                  requirement as supplier; derive has the derived requirement as client). The kind comes from the sibling application (DeriveReqt,
                  Satisfy, Verify, Refine, Trace, Copy ...); with none it is `dependency`, and `discover` counts those. Relationships between two things that
                  are not requirements are counted, not read.
  not read        tag values stored as separate elements, profiles, diagrams, and used projects: only ONE entry of an .mdzip is read (option entry=NAME to
                  choose another); `discover` names the entries it left alone.
OPTIONS  requirement_stereotypes (extra names, comma separated), entry (the .mdzip entry to read), max_mb (refuse an entry larger than this, default 2048).
"""
from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, opt_int, opt_list
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from .tabular import file_sha

MODEL_ENTRY = "com.nomagic.magicdraw.uml_model.model"
XML_SUFFIXES = (".xmi", ".xml", ".mdxml", ".uml")
REQ_STEREOTYPES = ("requirement", "extendedrequirement")
REL_TYPES = {"Abstraction", "Dependency", "Realization", "Usage", "Substitution"}
KIND = {"derivereqt": "derive", "derive": "derive", "satisfy": "satisfy", "verify": "verify", "refine": "refine", "trace": "trace", "copy": "copy"}
_HINT = re.compile(rb"omg\.org/spec/XMI|xmi:XMI|xmi:version", re.I)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xmi(attrs: dict[str, str], local: str) -> str | None:
    """An attribute in whichever XMI namespace the file uses (2.1, 2.4 and 2.5 each have their own URI)."""
    for k, v in attrs.items():
        if k.startswith("{") and "XMI" in k[1:k.index("}")] and k[k.index("}") + 1:] == local:
            return v
    return None


def _ref(attrs: dict[str, str]) -> str:
    """The id a reference element points at: xmi:idref, or the fragment of an href into another file (a used project)."""
    v = _xmi(attrs, "idref")
    if v:
        return v
    h = attrs.get("href", "")
    return h.rsplit("#", 1)[-1] if h else ""


def _events(opener, what: str) -> Iterator[tuple[str, ET.Element]]:
    """Stream (event, element) pairs. A DOCTYPE or ENTITY before the root element is refused, as everywhere else in this package.
    The parser may hold its first events back until the next piece (or the end of the input) arrives, so the check runs on whichever event is first."""
    parser = ET.XMLPullParser(events=("start", "end"))
    prefix = bytearray()           # everything fed until the root element has been seen
    started = False

    def refuse() -> ConnectError:
        return ConnectError(f"{what} has a DOCTYPE or ENTITY declaration; refusing to parse it (no model export needs one)")

    def drain() -> Iterator[tuple[str, ET.Element]]:
        nonlocal started, prefix
        for ev in parser.read_events():
            if not started and ev[0] == "start":
                started = True
                low = bytes(prefix).lower()
                if b"<!doctype" in low or b"<!entity" in low:
                    raise refuse()
                prefix = bytearray()
            yield ev

    with opener() as f:
        head = f.read(65536).lower()
        if b"<!doctype" in head or b"<!entity" in head:
            raise refuse()
    with opener() as f:
        while True:
            chunk = f.read(1 << 20 if started else 4096)           # small pieces until the root starts, so nothing is expanded in bulk before the check
            if not chunk:
                break
            if not started:
                prefix += chunk
                if len(prefix) > 16 << 20:
                    raise ConnectError(f"{what}: more than 16 MB before the first element; refusing")
            try:
                parser.feed(chunk)
                yield from drain()
            except ET.ParseError as e:
                raise ConnectError(f"{what} is not well-formed XML ({e})") from None
        try:
            parser.close()
            yield from drain()
        except ET.ParseError as e:
            raise ConnectError(f"{what} is not well-formed XML ({e})") from None


class _Capped:
    """A file object that refuses to deliver more than `limit` bytes: the size a zip entry declares can be a lie."""

    def __init__(self, f, limit: int, what: str, also_close=None):
        self.f, self.left, self.what, self.also = f, limit, what, also_close

    def read(self, n: int = -1) -> bytes:
        data = self.f.read(n)
        self.left -= len(data)
        if self.left < 0:
            raise ConnectError(f"{self.what} is larger than max_mb allows; refusing to read more")
        return data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.f.close()
        if self.also is not None:
            self.also.close()


@register
class SysML1XmiAdapter(Adapter):
    name = "sysml1_xmi"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True)
    maturity = "fixture-tested"

    def __init__(self) -> None:
        self._cache: dict[tuple, dict[str, Any]] = {}

    # ---- recognising the file ------------------------------------------------------------------------
    def sniff(self, src: Source) -> float:
        p = Path(src.uri)
        suffix = p.suffix.lower()
        try:
            if suffix == ".mdzip":
                with zipfile.ZipFile(p) as z:
                    names = [i.filename for i in z.infolist() if not i.is_dir()]
                return 0.95 if any(n == MODEL_ENTRY or n.startswith(MODEL_ENTRY + ".") for n in names) else 0.7
            if suffix in XML_SUFFIXES and p.is_file():
                with open(p, "rb") as f:
                    return 0.9 if _HINT.search(f.read(8192)) else 0.0
        except (zipfile.BadZipFile, OSError):
            return 0.0
        return 0.0

    # ---- opening the model ---------------------------------------------------------------------------
    def _open(self, src: Source):
        """(opener, what, entry names, entry read). The opener returns a fresh binary stream each time it is called."""
        p = Path(src.uri)
        cap = opt_int(src.options, "max_mb", 2048) << 20
        if p.suffix.lower() != ".mdzip":
            if p.stat().st_size > cap:
                raise ConnectError(f"{p.name} is larger than max_mb allows ({cap >> 20} MB)")
            return (lambda: _Capped(open(p, "rb"), cap, p.name)), p.name, [], ""
        try:
            with zipfile.ZipFile(p) as z:
                names = [i.filename for i in z.infolist() if not i.is_dir()]
                sizes = {i.filename: i.file_size for i in z.infolist()}
        except (zipfile.BadZipFile, OSError) as e:
            raise ConnectError(f"{p.name} is not a readable zip file ({type(e).__name__})") from None
        want = str(src.options.get("entry") or "")
        if want:
            if want not in names:
                raise ConnectError(f"no entry {want!r} in {p.name}; entries: {names[:20]}")
            entry = want
        else:
            model = [n for n in names if n == MODEL_ENTRY or n in (MODEL_ENTRY + s for s in XML_SUFFIXES)]
            xml = [n for n in names if n.lower().endswith(XML_SUFFIXES)]
            if len(model) == 1:
                entry = model[0]
            elif not model and len(xml) == 1:
                entry = xml[0]                                      # before 17.0.1 a project was one compressed XMI
            else:
                raise ConnectError(f"cannot tell which entry of {p.name} is the model; entries: {names[:20]}. Give entry=<name>")
        if sizes[entry] > cap:
            raise ConnectError(f"entry {entry} declares {sizes[entry] >> 20} MB, more than max_mb allows ({cap >> 20} MB)")

        def opener():
            z = zipfile.ZipFile(p)
            return _Capped(z.open(entry), cap, entry, also_close=z)
        return opener, f"{p.name}:{entry}", names, entry

    # ---- one pass over the XML -----------------------------------------------------------------------
    def _parse(self, src: Source) -> dict[str, Any]:
        opener, what, names, entry = self._open(src)
        elements: dict[str, dict[str, Any]] = {}
        apps: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []
        stack: list[dict[str, Any]] = []
        version = ""
        for ev, el in _events(opener, what):
            local = _local(el.tag)
            if ev == "start":
                attrs = dict(el.attrib)
                if not stack:
                    version = _xmi(attrs, "version") or ""
                xid, xtype = _xmi(attrs, "id"), _xmi(attrs, "type")
                xtype = xtype.split(":")[-1] if xtype else (local if xid and "/UML/" in el.tag else None)
                parent = stack[-1] if stack else None
                entry_ = {"local": local}
                base = next(((k[5:], v) for k, v in attrs.items() if k.startswith("base_")), None)
                if base and not xtype:
                    app = {"stereo": local, "base_kind": base[0], "base_id": base[1], "id": xid or "", "props": {}}
                    for k, v in attrs.items():
                        if not k.startswith("{") and not k.startswith("base_"):
                            app["props"][k] = v
                    apps.append(app)
                    entry_["app"] = app
                elif xid and xtype:
                    owner = next((e["el"]["id"] for e in reversed(stack) if "el" in e), None)
                    pkgs = [e["el"]["name"] for e in stack if "el" in e and e["el"]["type"] in ("Package", "Profile") and e["el"]["name"]]
                    node = {"id": xid, "type": xtype, "name": attrs.get("name", ""), "owner": owner, "pkg": "::".join(pkgs), "seq": len(elements),
                            "body": attrs.get("body")}
                    elements[xid] = node
                    entry_["el"] = node
                    if xtype in REL_TYPES:
                        rel = {"id": xid, "type": xtype, "client": attrs.get("client", "").split(), "supplier": attrs.get("supplier", "").split()}
                        rels.append(rel)
                        entry_["rel"] = rel
                elif parent is not None and "rel" in parent and local in ("client", "supplier"):
                    ref = _ref(attrs)
                    if ref:
                        parent["rel"][local].append(ref)
                stack.append(entry_)
            else:
                entry_ = stack.pop()
                parent = stack[-1] if stack else None
                if parent is not None and "app" in parent and "app" not in entry_ and "el" not in entry_:
                    if len(el) == 0 and (el.text or "").strip():
                        parent["app"]["props"][local] = el.text.strip()          # the child-element form of a property
                    elif _ref(el.attrib):
                        parent["app"]["props"][local] = _ref(el.attrib)
                if parent is not None and "el" in parent and parent["el"]["type"] == "Comment" and local == "body" and (el.text or "").strip():
                    parent["el"]["body"] = el.text.strip()
                if "el" in entry_ and entry_["el"]["type"] == "Comment" and entry_["el"].get("body"):
                    owner = elements.get(entry_["el"]["owner"] or "")
                    if owner is not None:
                        owner.setdefault("comments", []).append(entry_["el"]["body"])
                el.clear()
        return {"elements": elements, "apps": apps, "rels": rels, "version": version, "what": what, "names": names, "entry": entry}

    # ---- turning that into requirements and links ----------------------------------------------------
    def _load(self, src: Source) -> dict[str, Any]:
        key = self._key(src)
        if key in self._cache:
            return self._cache[key]
        raw = self._parse(src)
        elements, apps, rels = raw["elements"], raw["apps"], raw["rels"]
        selected = set(REQ_STEREOTYPES) | {s.strip().lower() for s in opt_list(src.options, "requirement_stereotypes", []) if s.strip()}
        notes: list[str] = []

        by_class: dict[str, list[dict[str, Any]]] = {}
        unselected: Counter[str] = Counter()
        for a in apps:
            if a["base_kind"] == "Class":
                if a["stereo"].lower() in selected:
                    by_class.setdefault(a["base_id"], []).append(a)
                else:
                    unselected[a["stereo"]] += 1
        req_ids = set(by_class)
        rev = file_sha(src.uri)                # once per run: the cache is keyed on the file's size and modification time, not on a hash

        def parent_of(cid: str) -> str | None:
            seen: set[str] = set()
            node = elements.get(cid)
            while node is not None and node["owner"] and node["owner"] not in seen:
                seen.add(node["owner"])
                if node["owner"] in req_ids:
                    return node["owner"]
                node = elements.get(node["owner"])
            return None

        records: list[dict[str, Any]] = []
        missing_class = more_than_one = no_text = 0
        order_of = lambda cid: elements[cid]["seq"] if cid in elements else 10 ** 9      # noqa: E731
        for cid in sorted(by_class, key=lambda c: (order_of(c), c)):
            group = by_class[cid]
            cls = elements.get(cid)
            if cls is None:
                missing_class += 1
            f: dict[str, Any] = {"Name": cls["name"] if cls else "", "Documentation": " ".join(cls.get("comments", [])) if cls else "",
                                 "Package": cls["pkg"] if cls else "", "Stereotype": ", ".join(g["stereo"] for g in group),
                                 "ElementType": cls["type"] if cls else ""}
            for gi, g in enumerate(group):
                for k, v in g["props"].items():
                    low = k.lower()
                    canon = "Id" if low == "id" else "Text" if low == "text" else k
                    if gi == 0 and canon not in f:          # Name, Package and the like are already set from the class, and Id and Text are set once
                        f[canon] = v
                    else:
                        f[f"{g['stereo']}.{k}"] = v         # a second application, or a property named like one of ours: kept, under its own name
            if len(group) > 1:
                more_than_one += 1
            f.setdefault("Id", "")
            f.setdefault("Text", "")
            if not f["Text"].strip():
                no_text += 1
            records.append({"native": cid, "fields": f, "parent": parent_of(cid), "locator": f"{f['Package'] + '::' if f['Package'] else ''}{f['Name'] or cid}"})

        kinds_of: dict[str, list[str]] = {}
        rel_ids = {r["id"] for r in rels}
        for a in apps:
            if a["base_kind"] in REL_TYPES and a["base_id"] in rel_ids:
                kinds_of.setdefault(a["base_id"], []).append(a["stereo"])
        links: list[dict[str, Any]] = []
        not_req = unstereotyped = incomplete = 0
        outside: set[str] = set()
        for r in rels:
            if not r["client"] or not r["supplier"]:
                incomplete += 1
                continue
            if not any(x in req_ids for x in r["client"] + r["supplier"]):
                not_req += 1
                continue
            names_ = kinds_of.get(r["id"], [])
            known = [KIND[n.lower()] for n in names_ if n.lower() in KIND]
            kind = known[0] if known else (names_[0].lower() if names_ else "dependency")
            unstereotyped += 0 if names_ else 1
            for c in r["client"]:
                for s in r["supplier"]:
                    outside |= {end for end in (c, s) if end not in elements and end not in req_ids}
                    links.append({"source": c, "target": s, "kind": kind, "locator": f"{r['type']} {r['id']}"})

        notes.append(f"read {raw['what']} (XMI {raw['version'] or 'version not stated'}); {len(records)} requirement classes via {sorted({a['stereo'] for g in by_class.values() for a in g})}")
        if raw["entry"]:
            left = [n for n in raw["names"] if n != raw["entry"] and re.search(r"shared_model|proxy", n, re.I)]
            if left:
                notes.append(f"{len(left)} used-project entries left unread ({left[:4]}); elements that live there appear as links ends kept by id. Read one with entry=NAME")
        if unselected:
            notes.append("stereotype applications on classes that were NOT read as requirements: "
                         + ", ".join(f"{n} x{c}" for n, c in unselected.most_common(8)) + ". A custom requirement stereotype goes in requirement_stereotypes=")
        if missing_class:
            notes.append(f"{missing_class} requirement applications point at a class that is not in this file (a used project?); read from the application alone")
        if more_than_one:
            notes.append(f"{more_than_one} classes carry more than one requirement application: the first one's Id and Text are used, the others are kept as <Stereotype>.<property>")
        if no_text:
            notes.append(f"{no_text} requirements have no Text property: the profile decides what to do with them")
        if unstereotyped:
            notes.append(f"{unstereotyped} relationships have no stereotype and are read as kind 'dependency'")
        if not_req:
            notes.append(f"{not_req} relationships join two things that are not requirements: not read")
        if incomplete:
            notes.append(f"{incomplete} relationships lack a client or a supplier: not read")
        if outside:
            notes.append(f"{len(outside)} link ends name an id that is not in this file (a used project, or an element of another kind): kept by id")
        out = {"records": records, "links": links, "notes": notes, "rev": rev}
        self._cache = {key: out}
        return out

    @staticmethod
    def _key(src: Source) -> tuple:
        st = Path(src.uri).stat()
        return (src.uri, tuple(sorted((a, str(b)) for a, b in src.options.items())), st.st_size, st.st_mtime_ns)

    # ---- the Adapter contract ------------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        d = self._load(src)
        by: dict[str, list[dict[str, Any]]] = {}
        for r in d["records"]:
            by.setdefault(r["fields"]["Stereotype"].split(",")[0].strip() or "?", []).append(r["fields"])
        cols = ("Id", "Name", "Text", "Documentation", "Package")
        cs = [Container(k, len(rows), [make_field_info(c, [r.get(c, "") for r in rows]) for c in cols]) for k, rows in sorted(by.items())]
        return Discovery(cs, list(d["notes"]))

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        d = self._load(src)
        rev = d["rev"]
        for n, r in enumerate(d["records"]):
            yield RawRecord(native_id=r["native"], fields=r["fields"], parent_native_id=r["parent"], order=n,
                            ref=SourceRef(self.name, src.uri, container=r["fields"]["Stereotype"].split(",")[0].strip() or "Requirement", locator=r["locator"], revision=rev))
        for lk in d["links"]:
            yield RawLink(lk["source"], lk["target"], lk["kind"], SourceRef(self.name, src.uri, "relations", lk["locator"], rev))

    def revision(self, src: Source) -> str:
        return self._load(src)["rev"]
