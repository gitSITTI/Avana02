"""PDF with a text layer: pdfplumber text blocks become EXTRACTED candidates; ruled tables become tabular containers.

Scanned PDFs (no text layer) are detected and reported, not guessed at: they need OCR first (not included).
Multi-column layouts can interleave lines; that is why every record keeps page + block for human verification.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawRecord, SourceRef
from .prose import HEADING, candidates
from .tabular import file_sha, find_header


@register
class PdfAdapter(Adapter):
    name = "pdf"
    fidelity = Fidelity.EXTRACTED
    caps = Caps()

    def sniff(self, src: Source) -> float:
        p = Path(src.uri)
        if p.suffix.lower() != ".pdf":
            return 0.0
        try:
            return 0.95 if p.read_bytes()[:5] == b"%PDF-" else 0.0
        except OSError:
            return 0.0

    def _walk(self, src: Source):
        import pdfplumber
        prose: list[dict] = []
        tables: dict[str, list[dict]] = {}
        notes: list[str] = []
        section = ""
        with pdfplumber.open(src.uri) as pdf:
            for pn, page in enumerate(pdf.pages, start=1):
                found = page.find_tables()
                boxes = [t.bbox for t in found]

                def keep(o, boxes=boxes):   # drop characters that sit inside a ruled table: they are read as table cells instead
                    if o.get("object_type") != "char":
                        return True
                    return not any(b[0] - 1 <= o["x0"] and o["x1"] <= b[2] + 1 and b[1] - 1 <= o["top"] and o["bottom"] <= b[3] + 1 for b in boxes)

                text = page.filter(keep).extract_text() or ""
                if not text.strip() and not found:
                    notes.append(f"page {pn}: no text layer (scanned?): OCR required")
                    continue
                for ti, tb in enumerate(found, start=1):
                    rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in tb.extract()]
                    if len(rows) >= 2:
                        h = find_header(rows)
                        header = [c or f"col{j + 1}" for j, c in enumerate(rows[h])]
                        tables[f"p{pn}-table{ti}"] = [
                            {**{header[j]: r[j] for j in range(min(len(header), len(r)))}, "_loc": f"p{pn}:t{ti}!R{k}"}
                            for k, r in enumerate(rows[h + 1:], start=h + 2) if any(r)]
                blocks, cur = [], []
                for line in text.splitlines():
                    if not line.strip():
                        if cur:
                            blocks.append(" ".join(cur)); cur = []
                    elif HEADING.match(line.strip()):
                        if cur:
                            blocks.append(" ".join(cur)); cur = []
                        section = line.strip()
                    elif re.match(r"^\s*(?:\[[\w\-\.]+\]|[A-Z][A-Z0-9]{1,8}(?:-[A-Z0-9]+){1,4}\s*[:\-)])", line) and cur:
                        blocks.append(" ".join(cur)); cur = [line.strip()]
                    else:
                        cur.append(line.strip())
                if cur:
                    blocks.append(" ".join(cur))
                for bi, b in enumerate(blocks, start=1):
                    cands = candidates(b)
                    for k, (lead, stmt) in enumerate(cands, start=1):
                        loc = f"p{pn}:blk{bi}" + (f".{k}" if len(cands) > 1 else "")
                        prose.append({"text": stmt, "lead_id": lead or "", "section": section, "_loc": loc})
        return prose, tables, notes

    def discover(self, src: Source) -> Discovery:
        prose, tables, notes = self._walk(src)
        cs = []
        if prose:
            cs.append(Container("prose", len(prose), [make_field_info(c, [r[c] for r in prose]) for c in ("text", "lead_id", "section")]))
        for name, rows in tables.items():
            if rows:
                cols = [k for k in rows[0] if k != "_loc"]
                cs.append(Container(name, len(rows), [make_field_info(c, [r.get(c, "") for r in rows]) for c in cols]))
        return Discovery(cs, notes)

    def read(self, src: Source) -> Iterator[RawRecord]:
        prose, tables, _ = self._walk(src)
        rev = self.revision(src)
        n = 0
        for r in prose:
            yield RawRecord(None, {k: v for k, v in r.items() if k != "_loc"}, SourceRef("pdf", src.uri, "prose", r["_loc"], rev), order=n); n += 1
        for name, rows in tables.items():
            for r in rows:
                yield RawRecord(None, {k: v for k, v in r.items() if k != "_loc"}, SourceRef("pdf", src.uri, name, r["_loc"], rev), order=n); n += 1

    def revision(self, src: Source) -> str:
        return file_sha(src.uri)
