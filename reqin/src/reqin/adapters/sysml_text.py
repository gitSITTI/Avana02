"""SysML v2 textual notation (.sysml): a LIGHTWEIGHT reader for requirement definitions/usages.

Fidelity = PARSED, not STRUCTURED. This is a regex/brace scanner, good enough to pull `requirement` elements,
their short names, `doc` comments, typing, nesting and `satisfy ... by ...` out of typical files.
It does not resolve imports, redefinitions, expressions or units. For production use the OMG Pilot
Implementation (or the Systems Modeling API, see sysml_api.py), which parse the full grammar.

A SOURCE IS ONE .sysml FILE OR A FOLDER OF THEM. The vendor documents that File > Export To > SysML v2 Textual Notation writes a folder of
.sysml files, one per selected namespace, and that it may use shortest qualified names, so a plain name can mean different things in different
packages. Every *.sysml under a folder is read (sorted by path; symbolic links are not followed). A reference is resolved only when it is unambiguous:
an exact qualified name, a qualified name that matches the end of exactly one definition, or a plain name defined once. A reference that is
ambiguous or unknown is kept AS WRITTEN (never guessed), and `discover` says how many. A qualified name defined twice (a namespace split over
two files, or two definitions with one name) keeps its first definition under its own id and gives the others `#2`, `#3`.
"""
from __future__ import annotations

import hashlib
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
        if p.suffix.lower() == ".sysml" and p.is_file():
            return 0.95
        if p.is_dir() and self._files(p, limit=1):
            return 0.9
        return 0.0

    MAX_FILES = 5000

    @staticmethod
    def _files(folder: Path, limit: int | None = None) -> list[Path]:
        out: list[Path] = []
        for f in sorted(folder.rglob("*")):
            if f.suffix.lower() == ".sysml" and f.is_file() and not f.is_symlink() and not any(part.startswith(".") for part in f.relative_to(folder).parts):
                out.append(f)
                if limit and len(out) >= limit:
                    break
        return out

    def _scan(self, masked: str, orig: str, base: int, qprefix: str, parent: str | None, out: list, seq: list[int]) -> None:
        pos = 0
        while True:
            m, pm = _HDR.search(masked, pos), _PKG.search(masked, pos)
            if pm and (not m or pm.start() < m.start()):          # a package: its name is part of the qualified name of everything inside it
                o = pm.end() - 1
                c = _match_brace(masked, o)
                self._scan(masked[o + 1:c], orig[o + 1:c], base + o + 1, (qprefix + "::" if qprefix else "") + _unq(pm.group("name")), parent, out, seq)
                pos = c + 1
                continue
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

    def _texts(self, src: Source) -> list[tuple[str, str]]:
        """(name shown in the locator, text) for the one file or for every .sysml in the folder."""
        p = Path(src.uri)
        if not p.is_dir():
            return [("", p.read_text(encoding="utf-8", errors="replace"))]
        files = self._files(p)
        if not files:
            raise ValueError(f"no .sysml file under {src.uri!r}")
        if len(files) > self.MAX_FILES:
            raise ValueError(f"{len(files)} .sysml files under {src.uri!r}: more than {self.MAX_FILES}; point at a smaller folder")
        return [(f.relative_to(p).as_posix(), f.read_text(encoding="utf-8", errors="replace")) for f in files]

    def _items(self, src: Source):
        """Every requirement element of every file with a native id that is unique across the source: (native id, qualified name, item, parent native id, file, offset)."""
        texts = self._texts(src)
        entries: list[tuple[str, str, dict, str | None, int, int]] = []
        used: dict[str, int] = {}
        for fi, (name, text) in enumerate(texts):
            out: list = []
            self._scan(_mask_comments(text), text, 0, "", None, out, [0])
            native_of: dict[str, str] = {}
            for q, item, parent, off in out:
                used[q] = used.get(q, 0) + 1
                nid = q if used[q] == 1 else f"{q}#{used[q]}"
                native_of[q] = nid
                if name:
                    item = {**item, "file": name}
                entries.append((nid, q, item, native_of.get(parent) if parent else None, fi, off))
        return texts, entries

    def _resolver(self, entries):
        """name -> native id when that is unambiguous; (resolve, ambiguous names)."""
        by_key: dict[str, set[str]] = {}
        qual: dict[str, str] = {}
        for nid, q, item, _, _, _ in entries:
            qual[nid] = q
            for key in (item["name"], item["shortName"], q):
                if key:
                    by_key.setdefault(key, set()).add(nid)
        ambiguous: set[str] = set()

        def resolve(ref: str) -> str:
            ref = ref.strip().strip("'")
            hit = by_key.get(ref, set())
            if len(hit) == 1:
                return next(iter(hit))
            if len(hit) > 1:
                ambiguous.add(ref)
                return ref
            if "::" in ref:
                cands = {nid for nid, q in qual.items() if q.endswith("::" + ref)}
                if len(cands) == 1:
                    return next(iter(cands))
            last = by_key.get(ref.split("::")[-1].strip("'"), set())
            if len(last) == 1:
                return next(iter(last))
            if len(last) > 1:
                ambiguous.add(ref)
            return ref
        return resolve, ambiguous

    def discover(self, src: Source) -> Discovery:
        texts, entries = self._items(src)
        rows = [e[2] for e in entries]
        kinds = sorted({r["kind"] for r in rows})
        cs = []
        for k in kinds:
            sub = [r for r in rows if r["kind"] == k]
            cs.append(Container(k, len(sub), [make_field_info(c, [r[c] for r in sub]) for c in ("shortName", "name", "doc", "typedBy")]))
        notes = ["lightweight parser (fidelity=parsed): use the Pilot Implementation or the API for full-grammar fidelity"]
        if len(texts) > 1 or texts[0][0]:
            notes.append(f"{len(texts)} .sysml files read")
        dup = sorted({e[1] for e in entries if "#" in e[0].rsplit("::", 1)[-1] and e[0] != e[1]})
        if dup:
            notes.append(f"{len(dup)} qualified names are defined more than once (first keeps its name, the others get #2, #3): {dup[:5]}")
        amb = {x for x in self._ambiguous_names(src, texts, entries)}
        if amb:
            notes.append(f"{len(amb)} references name a definition that exists in more than one package; they are kept as written, not guessed: {sorted(amb)[:5]}")
        return Discovery(cs, notes)

    def _ambiguous_names(self, src, texts, entries):  # noqa: ANN001
        resolve, ambiguous = self._resolver(entries)
        list(self._links(src, texts, entries, resolve))
        return ambiguous

    def _links(self, src, texts, entries, resolve=None):  # noqa: ANN001
        resolve = resolve or self._resolver(entries)[0]
        rev = self.revision(src)
        for nid, q, item, parent, fi, off in entries:
            fname, text = texts[fi]
            line = text.count("\n", 0, off) + 1
            if item["typedBy"]:
                yield RawLink(nid, resolve(item["typedBy"]), "instance-of", SourceRef("sysml_text", src.uri, "relations", f"{fname + ':' if fname else ''}L{line}", rev))
        for fname, text in texts:
            for m in _SAT.finditer(_mask_comments(text)):
                line = text.count("\n", 0, m.start()) + 1
                yield RawLink(resolve(m.group("by")), resolve(m.group("req")), "satisfy", SourceRef("sysml_text", src.uri, "relations", f"{fname + ':' if fname else ''}L{line}", rev))

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        texts, entries = self._items(src)
        rev = self.revision(src)
        for n, (nid, q, item, parent, fi, off) in enumerate(entries):
            fname, text = texts[fi]
            line = text.count("\n", 0, off) + 1
            yield RawRecord(native_id=nid, fields=item, parent_native_id=parent, order=n,
                            ref=SourceRef("sysml_text", src.uri, container=item["kind"], locator=f"{fname + ':' if fname else ''}L{line}:{q}", revision=rev))
        yield from self._links(src, texts, entries)

    def revision(self, src: Source) -> str:
        p = Path(src.uri)
        if not p.is_dir():
            return file_sha(src.uri)
        h = hashlib.sha256()
        for f in self._files(p):
            h.update(f.relative_to(p).as_posix().encode() + b"\0" + file_sha(str(f)).encode() + b"\0")
        return h.hexdigest()[:16]
