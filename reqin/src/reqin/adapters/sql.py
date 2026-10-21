"""SQL: any database SQLAlchemy can reach. The user supplies a SELECT; each result row is a record.

Options:  query            the SELECT (or WITH ...) that returns one row per requirement. Or:
          query_file       a file holding it. SQL comments in it are removed first, so a file can explain itself.
          id_column        the column that is the record's native id (needed for hierarchy and links)
          parent_column    the column holding the PARENT record's native id (empty or NULL = none)
          links_query      a second SELECT that returns one row per link, with the columns  source, target  and optionally  kind  and  ref
                           (the native ids of the two ends; kind defaults to trace). Or links_query_file.
          name             what the source is called in a locator

Safety: the real control is a read-only database role. The guard below (single SELECT/WITH statement, SQLite
opened query_only) is defence in depth, not a substitute. It applies to the links query and to a query file the same way.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawLink, RawRecord, SourceRef

_ALLOWED = re.compile(r"^\s*(select|with)\b", re.I)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|call|exec|execute|attach|pragma)\b", re.I)
_STR_OR_COMMENT = re.compile(r"'(?:[^']|'')*'|--[^\n]*|/\*.*?\*/", re.S)
MAX_QUERY_FILE = 1 << 20


def strip_sql_comments(q: str) -> str:
    """Remove -- and /* */ comments, leaving string literals as they are (a -- inside a quoted string is not a comment)."""
    return _STR_OR_COMMENT.sub(lambda m: m.group(0) if m.group(0).startswith("'") else " ", q)


def check_query(q: str) -> str:
    q = strip_sql_comments(q).strip().rstrip(";").strip()
    if ";" in q or not _ALLOWED.match(q) or _FORBIDDEN.search(re.sub(r"'(?:[^']|'')*'", "''", q)):
        raise ValueError("only a single read-only SELECT/WITH statement is allowed")
    return q


def query_text(options, key: str) -> str | None:  # noqa: ANN001
    """The SQL given as option `key`, or read from the file named by `key`_file; None when neither is given."""
    if options.get(key):
        return str(options[key])
    fn = options.get(f"{key}_file")
    if not fn:
        return None
    p = Path(str(fn))
    if not p.is_file() or p.stat().st_size > MAX_QUERY_FILE:
        raise ValueError(f"{key}_file {fn!r} is not a file of at most {MAX_QUERY_FILE >> 10} KB")
    return p.read_text(encoding="utf-8")


@register
class SqlAdapter(Adapter):
    name = "sql"
    fidelity = Fidelity.TABULAR
    caps = Caps(links=True, hierarchy=True)          # both optional: parent_column and links_query

    def sniff(self, src: Source) -> float:
        scheme = src.uri.split(":", 1)[0].split("+", 1)[0].lower()
        ok = scheme in {"sqlite", "postgresql", "mysql", "mariadb", "mssql", "oracle", "duckdb"}
        return 0.9 if ok and (src.options.get("query") or src.options.get("query_file")) else 0.0

    def _engine(self, src: Source):
        from sqlalchemy import create_engine, event
        eng = create_engine(src.uri)
        if eng.dialect.name == "sqlite":
            @event.listens_for(eng, "connect")
            def _ro(dbapi_con, _):  # noqa: ANN001
                dbapi_con.execute("PRAGMA query_only = ON")
        return eng

    def _select(self, src: Source, key: str) -> str | None:
        raw = query_text(src.options, key)
        return None if raw is None else check_query(raw)

    def _run(self, src: Source, q: str, limit: int | None = None) -> Iterator[dict]:
        """Rows of one query. A limit stops READING after that many rows; the query is never wrapped, because LIMIT is not SQL Server or Oracle
        syntax and an ORDER BY is not allowed inside a subquery there."""
        from sqlalchemy import text
        with self._engine(src).connect() as con:
            for n, row in enumerate(con.execution_options(stream_results=True).execute(text(q)).mappings()):
                if limit and n >= limit:
                    break
                yield dict(row)

    def _rows(self, src: Source, limit: int | None = None) -> Iterator[dict]:
        q = self._select(src, "query")
        if q is None:
            raise ValueError("option 'query' (or 'query_file') is required: a single SELECT that returns one row per requirement")
        return self._run(src, q, limit)

    def _link_rows(self, src: Source, limit: int | None = None) -> Iterator[dict]:
        q = self._select(src, "links_query")
        if q is None:
            return iter(())
        return self._run(src, q, limit)

    def discover(self, src: Source) -> Discovery:
        rows = list(self._rows(src, limit=500))
        cols = list(rows[0]) if rows else []
        notes = ["sampled first 500 rows"]
        if self._select(src, "links_query") is not None:
            sample = list(self._link_rows(src, limit=5000))
            if sample and not {"source", "target"} <= set(sample[0]):
                raise ValueError(f"the links query must return the columns source and target (it returned {sorted(sample[0])})")
            empty = sum(1 for r in sample if r.get("source") in ("", None) or r.get("target") in ("", None))
            notes.append(f"links query: {len(sample)} rows sampled (at most 5000); {empty} have an empty source or target and are skipped")
        pcol = src.options.get("parent_column")
        if pcol and rows and pcol not in cols:
            notes.append(f"WARNING parent_column {pcol!r} is not a column of the query (columns: {cols})")
        idc = src.options.get("id_column")
        if idc and rows and idc not in cols:
            notes.append(f"WARNING id_column {idc!r} is not a column of the query (columns: {cols})")
        return Discovery([Container("query", len(rows), [make_field_info(c, [r[c] for r in rows]) for c in cols])], notes)

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        idc, pcol = src.options.get("id_column"), src.options.get("parent_column")
        name = src.options.get("name", "db")
        rev = self.revision(src)
        for i, r in enumerate(self._rows(src)):
            f = {k: ("" if v is None else v) for k, v in r.items()}
            nid = str(f[idc]) if idc and f.get(idc) not in ("", None) else None
            parent = str(f[pcol]) if pcol and f.get(pcol) not in ("", None) and str(f[pcol]) != nid else None
            yield RawRecord(native_id=nid, fields=f, order=i, parent_native_id=parent,
                            ref=SourceRef("sql", name, container="query", locator=f"row{i + 1}", revision=rev))
        for i, r in enumerate(self._link_rows(src)):
            a, b = r.get("source"), r.get("target")
            if a in ("", None) or b in ("", None):
                continue                                       # counted in discover, never turned into a half link
            kind = str(r.get("kind") or "trace")
            yield RawLink(str(a), str(b), kind, SourceRef("sql", name, container="links", locator=str(r.get("ref") or f"link{i + 1}"), revision=rev))

    def revision(self, src: Source) -> str:
        parts = [query_text(src.options, "query") or "", query_text(src.options, "links_query") or "", str(src.options.get("parent_column", ""))]
        return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
