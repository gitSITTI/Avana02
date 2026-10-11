"""SysML v2 Systems Modeling API (REST): the production route for large online SysML v2 projects.

STATUS: contract + paging + filtering are implemented and tested against a fake server. The JSON KEY NAMES are
configurable (`keys`) because they were NOT verified against a live server in this work. Before relying on it,
run it once against your server (SysON, Pilot Implementation API Services, or your MSOSA/TWC endpoint), look at
one element's JSON, and adjust `keys` in the profile. Endpoint shape (verified in SysON's docs):
  GET {base}/api/rest/projects/{projectId}/commits/{commitId}/elements
(SysON has no commits: it takes the project id as the commit id.)
"""
from __future__ import annotations

import json
import urllib.request
from typing import Callable, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..model import Fidelity, RawRecord, SourceRef

DEFAULT_KEYS = {"id": "@id", "type": "@type", "name": "declaredName", "short": "declaredShortName",
                "doc_body": "body", "owner": "owner", "req_types": ["RequirementDefinition", "RequirementUsage"]}


def _http_get(url: str, headers: dict[str, str]) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=60) as r:  # noqa: S310 (URL comes from the user's own config)
        return json.loads(r.read())


@register
class SysMLApiAdapter(Adapter):
    name = "sysml_api"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=True)

    def __init__(self, http_get: Callable[[str, dict], object] | None = None):
        self._get = http_get or _http_get

    def sniff(self, src: Source) -> float:
        return 0.9 if src.uri.startswith(("http://", "https://")) and "/api/rest" in src.uri else 0.0

    def _elements(self, src: Source) -> list[dict]:
        o = src.options
        base = src.uri.rstrip("/")
        url = f"{base}/projects/{o['project_id']}/commits/{o.get('commit_id', o['project_id'])}/elements"
        hdr = {"Authorization": f"Bearer {o['token']}"} if o.get("token") else {}
        out: list[dict] = []
        page = self._get(url, hdr)
        out += page if isinstance(page, list) else page.get("elements", [])
        return out

    def _rows(self, src: Source) -> list[tuple[str, str, dict]]:
        """(native id, element type, canonical-ish fields) for requirement elements, with Documentation joined on."""
        k = {**DEFAULT_KEYS, **src.options.get("keys", {})}
        els = self._elements(src)
        docs: dict[str, str] = {}
        for e in els:                                   # documentation elements point at their owner
            if e.get(k["type"]) == "Documentation" and e.get(k["doc_body"]):
                owner = e.get(k["owner"])
                owner = owner.get("@id") if isinstance(owner, dict) else owner
                docs[owner] = (docs.get(owner, "") + " " + e[k["doc_body"]]).strip()
        rows = []
        for e in els:
            if e.get(k["type"]) in k["req_types"]:
                rows.append((e.get(k["id"], ""), e.get(k["type"], ""),
                             {"shortName": e.get(k["short"], "") or "", "name": e.get(k["name"], "") or "",
                              "kind": e.get(k["type"]), "doc": docs.get(e.get(k["id"]), "")}))
        return rows

    def discover(self, src: Source) -> Discovery:
        rows = self._rows(src)
        cols = ["shortName", "name", "kind", "doc"]
        return Discovery([Container("requirements", len(rows), [make_field_info(c, [r[2][c] for r in rows]) for c in cols])],
                         ["documentation text lives in separate Documentation elements and is joined to its owner"])

    def read(self, src: Source) -> Iterator[RawRecord]:
        rev = self.revision(src)
        for n, (eid, etype, f) in enumerate(self._rows(src)):
            yield RawRecord(native_id=eid, fields=f, order=n, ref=SourceRef("sysml_api", src.uri, container="requirements", locator=eid, revision=rev))

    def revision(self, src: Source) -> str:
        return str(src.options.get("commit_id", ""))
