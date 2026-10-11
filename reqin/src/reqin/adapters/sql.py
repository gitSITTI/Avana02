"""SQL: any database SQLAlchemy can reach. The user supplies a SELECT; each result row is a record.

Safety: the real control is a read-only database role. The guard below (single SELECT/WITH statement, SQLite
opened query_only) is defence in depth, not a substitute.
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawRecord, SourceRef

_ALLOWED = re.compile(r"^\s*(select|with)\b", re.I)
_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|call|exec|execute|attach|pragma)\b", re.I)


def check_query(q: str) -> str:
    q = q.strip().rstrip(";").strip()
    if ";" in q or not _ALLOWED.match(q) or _FORBIDDEN.search(re.sub(r"'[^']*'", "''", q)):
        raise ValueError("only a single read-only SELECT/WITH statement is allowed")
    return q


@register
class SqlAdapter(Adapter):
    name = "sql"
    fidelity = Fidelity.TABULAR
    caps = Caps()

    def sniff(self, src: Source) -> float:
        scheme = src.uri.split(":", 1)[0].split("+", 1)[0].lower()
        ok = scheme in {"sqlite", "postgresql", "mysql", "mariadb", "mssql", "oracle", "duckdb"}
        return 0.9 if ok and src.options.get("query") else 0.0

    def _engine(self, src: Source):
        from sqlalchemy import create_engine, event
        eng = create_engine(src.uri)
        if eng.dialect.name == "sqlite":
            @event.listens_for(eng, "connect")
            def _ro(dbapi_con, _):  # noqa: ANN001
                dbapi_con.execute("PRAGMA query_only = ON")
        return eng

    def _rows(self, src: Source, limit: int | None = None) -> Iterator[dict]:
        from sqlalchemy import text
        q = check_query(src.options["query"])
        if limit:
            q = f"SELECT * FROM ({q}) AS _q LIMIT {int(limit)}"
        with self._engine(src).connect() as con:
            for row in con.execution_options(stream_results=True).execute(text(q)).mappings():
                yield dict(row)

    def discover(self, src: Source) -> Discovery:
        rows = list(self._rows(src, limit=500))
        cols = list(rows[0]) if rows else []
        return Discovery([Container("query", len(rows), [make_field_info(c, [r[c] for r in rows]) for c in cols])],
                         ["sampled first 500 rows"])

    def read(self, src: Source) -> Iterator[RawRecord]:
        idc = src.options.get("id_column")
        rev = self.revision(src)
        for i, r in enumerate(self._rows(src)):
            f = {k: ("" if v is None else v) for k, v in r.items()}
            nid = str(f[idc]) if idc and f.get(idc) not in ("", None) else None
            yield RawRecord(native_id=nid, fields=f, order=i,
                            ref=SourceRef("sql", src.options.get("name", "db"), container="query", locator=f"row{i + 1}", revision=rev))

    def revision(self, src: Source) -> str:
        return hashlib.sha256(src.options.get("query", "").encode()).hexdigest()[:16]
