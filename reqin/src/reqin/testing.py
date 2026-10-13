"""Test helpers for connector authors (shipped inside the package so your own plugin's tests can import them).

    from reqin.testing import FakeTransport, json_response, check_adapter

* FakeTransport stands in for a server. It only has `get`, so a connector tested with it cannot write; every
  request it receives is recorded in `.requests`.
* check_adapter runs the same properties the built-in conformance suite checks, against any adapter and source:
  nothing silently dropped, the result is a valid GUI dataset, text verbatim, identity and provenance, deterministic, nothing lost, source untouched.
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from .adapter import Adapter, Source
from .connect import Response
from .dataset import validate_result
from .ingest import ingest
from .mapping import Profile, propose_profile
from .normalise import normalise_text


def json_response(obj: Any, status: int = 200, headers: dict[str, str] | None = None) -> Response:
    return Response(status, {"content-type": "application/json", **{k.lower(): v for k, v in (headers or {}).items()}},
                    json.dumps(obj).encode())


def text_response(text: str, content_type: str = "text/plain", status: int = 200, headers: dict[str, str] | None = None) -> Response:
    return Response(status, {"content-type": content_type, **{k.lower(): v for k, v in (headers or {}).items()}}, text.encode())


@dataclass
class Req:
    url: str
    path: str
    query: dict[str, str]          # first value of each parameter, URL-decoded
    headers: dict[str, str]        # as sent, original case


class FakeTransport:
    """A tiny in-memory server. Routes match on the URL path; a handler gets the Req and returns a Response,
    a dict/list (sent as JSON), or a str (sent as text)."""

    def __init__(self) -> None:
        self._routes: list[tuple[str, Callable[[Req], Any]]] = []
        self.requests: list[Req] = []

    def add(self, path: str, handler: Callable[[Req], Any] | Any) -> "FakeTransport":
        self._routes.append((path, handler if callable(handler) else (lambda _r, h=handler: h)))
        return self

    def get(self, url: str, headers: dict[str, str]) -> Response:
        p = urllib.parse.urlsplit(url)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(p.query, keep_blank_values=True).items()}
        req = Req(url, p.path, q, dict(headers))
        self.requests.append(req)
        for path, handler in self._routes:
            if path == p.path or path == f"{p.scheme}://{p.netloc}{p.path}":
                out = handler(req)
                if isinstance(out, Response):
                    return out
                if isinstance(out, str):
                    return text_response(out)
                return json_response(out)
        return Response(404, {"content-type": "text/plain"}, b"no such route in FakeTransport: " + p.path.encode(), url)

    def paths(self) -> list[str]:
        return [r.path for r in self.requests]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def check_adapter(make_adapter: Callable[[], Adapter], src: Source, profile: Profile | None = None, *, expect_ok: int,
                  expect_rejected: int = 0, gold_text: dict[str, str] | None = None, files: Iterable[Path] = (),
                  expect_links: int | None = None) -> Any:
    """Assert the connector properties. `make_adapter` must build a FRESH adapter each call (so caching cannot hide
    nondeterminism). Returns the first IngestResult so callers can add their own assertions."""
    files = list(files)
    before = {p: _sha(p) for p in files}
    a1 = make_adapter()
    r = ingest(src, profile=profile, adapter=a1)
    # 1. nothing is dropped silently, and counts are what the fixture says
    assert r.report["invariant_ok"], r.report
    # the result must also be a dataset the GUI can read (GUI_CONTRACT.md): the same checker `reqin check-dataset` runs
    contract = validate_result(r)
    assert not contract, contract[:5]
    # ...and do not take the pipeline's word for it: count the raw records straight from a fresh adapter.
    raw_n = sum(1 for x in make_adapter().read(src) if hasattr(x, "fields"))
    assert raw_n == r.report["raw_records"] == len(r.requirements) + len(r.rejected) + sum(r.report["filtered_out"].values()), \
        f"{raw_n} records read from the source but {len(r.requirements)} kept + {len(r.rejected)} rejected + filtered {r.report['filtered_out']}"
    assert len(r.requirements) == expect_ok, r.report
    assert len(r.rejected) == expect_rejected, [x.reason for x in r.rejected]
    assert all(x.reason for x in r.rejected), "a rejected record without a reason"
    if expect_links is not None:
        assert len(r.links) == expect_links, [(x.source_uid, x.kind, x.target_uid) for x in r.links]
    # 2. identity and provenance
    assert len({q.mid for q in r.requirements}) == len(r.requirements), "MID collision"
    for q in r.requirements:
        assert q.ref.locator and q.ref.adapter == a1.name and q.ref.uri, q.ref
        assert q.text.strip() and "text" in q.conf and "uid" in q.conf
        assert q.fidelity.value in ("structured", "tabular", "parsed", "extracted")
    # 3. text is verbatim after normalisation
    if gold_text:
        by_uid = {q.uid: q for q in r.requirements if not q.uid_synthetic}
        assert by_uid, "no requirement kept a real UID"
        for uid, q in by_uid.items():
            if uid in gold_text:
                assert q.norm_text == normalise_text(gold_text[uid]), (uid, q.norm_text)
    # 4. deterministic, from a fresh adapter
    r2 = ingest(src, profile=profile, adapter=make_adapter())
    assert [(q.mid, q.fingerprint, q.uid) for q in r.requirements] == [(q.mid, q.fingerprint, q.uid) for q in r2.requirements]
    # 5. nothing in the source is lost: every non-empty raw field is claimed by the profile or kept in `extra`
    prof = profile or propose_profile(make_adapter().discover(src), a1.name)
    claimed = {k for rule in prof.fields.values() for k in rule.src + rule.join}
    by_loc = {(q.ref.container, q.ref.locator): q for q in r.requirements}
    for raw in make_adapter().read(src):
        if not hasattr(raw, "fields"):
            continue
        q = by_loc.get((raw.ref.container, raw.ref.locator))
        if q is None:
            continue
        for k, v in raw.fields.items():
            if str(v).strip():
                assert k in claimed or k in q.extra, (q.uid, k)
    # 6. the source is untouched: files unchanged, and a live adapter made only GETs
    for p, h in before.items():
        assert _sha(p) == h, f"{p} was modified"
    audit = getattr(a1, "audit", None)
    if callable(audit):
        assert all(e.method == "GET" for e in audit()), "a live connector made a non-GET request"
    return r
