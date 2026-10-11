"""CSV / TSV / XLSX: one requirement per row. Also used by DOORS 'export to CSV/Excel' and any ALM export."""
from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawRecord, SourceRef


def file_sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def find_header(rows: list[list[str]], scan: int = 15) -> int:
    """Header = first row (within the first `scan`) that is mostly filled, mostly non-numeric, and followed by data.
    Skips title blocks and blank lines that real spreadsheets have above the table."""
    for i, row in enumerate(rows[:scan]):
        cells = [c.strip() for c in row]
        filled = [c for c in cells if c]
        if len(filled) < 2 or len(filled) < 0.6 * len(cells):
            continue
        numeric = sum(1 for c in filled if c.replace(".", "", 1).isdigit())
        if numeric > 0.3 * len(filled):
            continue
        if i + 1 < len(rows) and any(c.strip() for c in rows[i + 1]):
            return i
    return 0


def _read_csv(path: str) -> list[list[str]]:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    return [list(r) for r in csv.reader(io.StringIO(text), dialect)]


def _read_xlsx(path: str) -> dict[str, list[list[str]]]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)  # data_only: cached values, never formulas
    out: dict[str, list[list[str]]] = {}
    for ws in wb.worksheets:
        if ws.sheet_state != "visible":
            continue
        out[ws.title] = [["" if c is None else str(c) for c in row] for row in ws.iter_rows(values_only=True)]
    wb.close()
    return out


@register
class TabularAdapter(Adapter):
    name = "tabular"
    fidelity = Fidelity.TABULAR
    caps = Caps()

    def sniff(self, src: Source) -> float:
        ext = Path(src.uri).suffix.lower()
        if ext in (".csv", ".tsv"):
            return 0.9
        if ext in (".xlsx", ".xlsm"):
            try:
                return 0.95 if "xl/workbook.xml" in zipfile.ZipFile(src.uri).namelist() else 0.0
            except (zipfile.BadZipFile, OSError):
                return 0.0
        return 0.0

    def _tables(self, src: Source) -> dict[str, list[dict[str, str]]]:
        ext = Path(src.uri).suffix.lower()
        sheets = {Path(src.uri).stem: _read_csv(src.uri)} if ext in (".csv", ".tsv") else _read_xlsx(src.uri)
        want = src.options.get("sheet")
        out: dict[str, list[dict[str, str]]] = {}
        for name, rows in sheets.items():
            if want and name != want:
                continue
            rows = [r for r in rows]
            if not any(any(c.strip() for c in r) for r in rows):
                continue
            h = src.options.get("header_row")
            h = find_header(rows) if h is None else int(h)
            header = [c.strip() or f"col{j + 1}" for j, c in enumerate(rows[h])]
            seen: dict[str, int] = {}
            for j, c in enumerate(header):           # make duplicate headers unique instead of losing a column
                seen[c] = seen.get(c, 0) + 1
                if seen[c] > 1:
                    header[j] = f"{c}#{seen[c]}"
            body = []
            for k, r in enumerate(rows[h + 1:], start=h + 2):  # 1-based sheet row numbers
                if not any(c.strip() for c in r):
                    continue
                d = {header[j]: (r[j] if j < len(r) else "") for j in range(len(header))}
                d["_row"] = str(k)
                body.append(d)
            out[name] = body
        return out

    def discover(self, src: Source) -> Discovery:
        cs = []
        for name, rows in self._tables(src).items():
            cols = [k for k in rows[0] if k != "_row"] if rows else []
            cs.append(Container(name, len(rows), [make_field_info(c, [r.get(c, "") for r in rows]) for c in cols]))
        return Discovery(cs, ["header row auto-detected; override with options['header_row'] (0-based)"])

    def read(self, src: Source) -> Iterator[RawRecord]:
        rev = self.revision(src)
        for name, rows in self._tables(src).items():
            for i, r in enumerate(rows):
                fields = {k: v for k, v in r.items() if k != "_row"}
                yield RawRecord(native_id=None, fields=fields, order=i,
                                ref=SourceRef("tabular", src.uri, container=name, locator=f"{name}!R{r['_row']}", revision=rev))

    def revision(self, src: Source) -> str:
        return file_sha(src.uri)
