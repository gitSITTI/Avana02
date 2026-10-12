"""TEMPLATE connector: a paged, READ-ONLY JSON API ("Acme Requirements").

How to use this folder
  1. Copy it, rename `acme` / `Acme` / `reqin_acme` everywhere (pyproject.toml, this file, profile.yaml, tests).
  2. Work through the five TODO(agent) markers below, in order. Run `pytest` after each one.
  3. Run `reqin sample acme+https://your-host/api --opt token_env=ACME_TOKEN` against the real system. Compare with the fake in
     tests/test_adapter.py and fix the differences (names, paging). Then keep the fake in step with what you saw.

What you get for free from reqin.connect (do not re-implement it): GET-only HTTP, TLS always verified, a CA bundle option,
retries, size/request caps, redirect safety, secrets from environment variables and scrubbed from every message, and an audit list.
"""
from __future__ import annotations

from typing import Any, Iterator

from reqin.adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from reqin.connect import ConnectError, ReadOnlyHttp, make_http, opt_int
from reqin.model import Fidelity, RawLink, RawRecord, SourceRef


@register
class AcmeAdapter(Adapter):
    name = "acme"                              # TODO(agent) 1: your connector's name. Also in pyproject.toml and profile.yaml
    fidelity = Fidelity.STRUCTURED             # TODO(agent) 2: STRUCTURED (native IDs + links) | TABULAR | PARSED | EXTRACTED. Be honest.
    caps = Caps(structured_ids=True, links=False, hierarchy=True)
    maturity = "fake-server-tested"            # leave it. Only a person who ran it on the real system may change it to "live-verified"

    def __init__(self, transport=None) -> None:  # noqa: ANN001  (tests pass a FakeTransport; real runs pass nothing)
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, list[dict]] = {}

    # TODO(agent) 3: how to recognise YOUR source. Cheap: look at the URI only, never at the network.
    def sniff(self, src: Source) -> float:
        return 0.95 if src.uri.startswith("acme+https://") else 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    # TODO(agent) 4: the paging and the JSON shape of YOUR server. This toy follows {"items": [...], "next": "<url>"} until "next" is empty.
    def _items(self, src: Source) -> list[dict[str, Any]]:
        key = src.uri + repr(sorted((k, str(v)) for k, v in src.options.items() if k != "token_env"))
        if key in self._cache:                   # discover() and read() both need the data: fetch it once per run
            return self._cache[key]
        http = self._http = make_http(src.options, self._transport, base_headers={"Accept": "application/json"})
        url: str | None = src.uri.removeprefix("acme+").rstrip("/") + "/requirements"
        params: dict[str, Any] | None = {"page_size": opt_int(src.options, "page_size", 100)}
        out: list[dict] = []
        seen_pages: set[str] = set()
        while url:
            body = http.get_json(url, params)
            if not isinstance(body, dict) or "items" not in body:
                raise ConnectError("unexpected response shape (no 'items'): often a login page. Check the URL and credentials.")
            out += body["items"]
            url, params = body.get("next"), None
            if url in seen_pages:
                raise ConnectError("paging is not advancing: the server returned the same 'next' URL twice")
            if url:
                seen_pages.add(url)
        self._cache[key] = out
        return out

    def discover(self, src: Source) -> Discovery:
        items = self._items(src)
        cols = sorted({k for it in items for k in it})
        return Discovery([Container("requirements", len(items), [make_field_info(c, [it.get(c, "") for it in items]) for c in cols])],
                         [f"read {len(items)} items"])

    # TODO(agent) 5: which JSON properties become raw fields, which one is the stable id, which one names the parent.
    #   Rules: yield what the source SAID, untouched (meaning is the profile's job); never skip a record (the pipeline rejects
    #   empty ones WITH a reason); put a locator on every record that lets a person find it again in the source system.
    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        base = src.uri.removeprefix("acme+")
        for i, it in enumerate(self._items(src)):
            yield RawRecord(native_id=str(it["id"]), fields={k: v for k, v in it.items() if k != "parent"}, order=i,
                            parent_native_id=str(it["parent"]) if it.get("parent") else None,
                            ref=SourceRef("acme", base, container="requirements", locator=str(it["id"]), revision=str(it.get("rev", ""))))

    def revision(self, src: Source) -> str:
        return ""
