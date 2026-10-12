"""Digital.ai Agility (formerly VersionOne): stories, epics and defects as requirement-like records, over the REST Data API.

READ-ONLY. Only GET requests are made (the query.v1 endpoint is a POST and is deliberately NOT used).
If you already work from Agility exports (xlsx/csv), you do not need this connector: the tabular adapter plus
profiles/agility_export.yaml reads those.

URI:      agility+https://host/Instance          (the part before /rest-1.v1)
Options:  asset_types   comma list, default Epic,Story,Defect
          select        comma list of attributes, default Number,Name,Description,Scope.Name,Status.Name,AssetState,Super,Dependencies,ChangeDateUTC
          where         Agility where-clause, e.g. where="Scope.Name='My Project';AssetState!='255'"   (passed through as-is)
          page_size     default 500
          parent_attr   attribute holding the parent (default Super)
          link_attrs    JSON {"Attribute": "kind"}, default {"Dependencies": "trace"}  (this -> each referenced asset)
          select_param  name of the select query parameter, default sel
          token_env     environment variable with an Agility access token (sent as Authorization: Bearer)
          basic_user_env + basic_password_env | cookie_env | auth_hook | ca_bundle     see connect.auth_from_options

WHAT IS VERIFIED AND WHAT IS NOT:
  verified in the public API docs  GET <base>/rest-1.v1/Data/<Asset> with Accept: application/json returns
                                   {"_type":"Assets","total":N,"pageSize":..,"pageStart":..,"Assets":[{"id":"Story:1005","Attributes":{"Name":{"name":"Name","value":..}}}]};
                                   the page parameter takes size,start; access tokens go in Authorization: Bearer; the AssetState codes
                                   (0 Future, 64 Active, 128 Closed, 200 Template, 208 Broken Down, 255 Deleted); Story/Epic/Scope/Super/Number/Name
  NOT seen live                    how a relation looks inside Attributes (we accept {"idref": "Epic:12"}, a list of those, or a bare "Epic:12");
                                   whether `Description`, `Dependencies`, `Status.Name` exist under those names on YOUR instance (names are
                                   configurable: select, link_attrs, parent_attr); whether ids carry a trailing moment (we strip it)
  Tested only against an in-memory fake (tests/test_live_connectors.py).
  First run on your instance: reqin sample agility+https://host/Instance --opt token_env=AGILITY_TOKEN --opt where="Scope.Name='<project>'"
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, opt_dict, opt_int, opt_list
from ..model import Fidelity, RawLink, RawRecord, SourceRef

DEFAULT_ASSET_TYPES = ["Epic", "Story", "Defect"]
DEFAULT_SELECT = ["Number", "Name", "Description", "Scope.Name", "Status.Name", "AssetState", "Super", "Dependencies", "ChangeDateUTC"]
DEFAULT_LINK_ATTRS = {"Dependencies": "trace"}


def oid_of(raw_id: str) -> str:
    """'Story:1005:1236' -> 'Story:1005'. The third token is the asset's MOMENT: it changes with every edit, so it must not be part of the identity."""
    return ":".join(str(raw_id).split(":")[:2])


def _idrefs(v: Any) -> list[str]:
    if v is None or v == "":
        return []
    if isinstance(v, list):
        return [r for x in v for r in _idrefs(x)]
    if isinstance(v, dict):
        return [oid_of(str(v["idref"]))] if v.get("idref") else []
    s = str(v)
    return [oid_of(s)] if s.count(":") >= 1 and s.split(":")[0].isalpha() and s.split(":")[1].isdigit() else []


def _plain(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, list):
        return "; ".join(x for x in (_plain(i) for i in v) if x)
    if isinstance(v, dict):
        return "; ".join(_idrefs(v)) if v.get("idref") else ""
    return str(v)


@register
class AgilityAdapter(Adapter):
    name = "agility"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, tuple[list, list, list[str], str]] = {}

    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("agility+http://", "agility+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and "/rest-1.v1" in u:
            return 0.85
        return 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    @staticmethod
    def _base(src: Source) -> str:
        return src.uri.removeprefix("agility+").split("/rest-1.v1")[0].rstrip("/")

    def _load(self, src: Source):
        o = src.options
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in o.items() if a not in ("token", "token_env", "cookie_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        self._http = http = make_http(o, self._transport, base_headers={"Accept": "application/json"})
        base = self._base(src)
        size = opt_int(o, "page_size", 500)
        select = opt_list(o, "select", DEFAULT_SELECT)
        parent_attr = str(o.get("parent_attr", "Super"))
        link_attrs = opt_dict(o, "link_attrs", DEFAULT_LINK_ATTRS)
        for needed in {parent_attr, *link_attrs}:
            if needed not in select:
                select.append(needed)
        rows: list[tuple[str, str, dict[str, Any], str | None, str]] = []   # oid, type, fields, parent, moment
        links: list[tuple[str, str, str, str]] = []
        notes: list[str] = []
        seen: set[str] = set()
        for atype in opt_list(o, "asset_types", DEFAULT_ASSET_TYPES):
            start, before = 0, len(rows)
            peek = opt_int(o, "peek", 0)
            for page_no in range(1, opt_int(o, "max_pages", 1_000_000) + 1):
                params: dict[str, Any] = {str(o.get("select_param", "sel")): ",".join(select), "page": f"{size},{start}"}
                if o.get("where"):
                    params["where"] = o["where"]
                body = http.get_json(f"{base}/rest-1.v1/Data/{atype}", params)
                if not isinstance(body, dict) or "Assets" not in body:
                    raise ConnectError(f"{http.safe_url(base)}/rest-1.v1/Data/{atype} did not return the documented {{\"Assets\": [...]}} shape; "
                                       "check the URL, the instance name and the credentials (a login page also looks like this)")
                if body.get("pageStart") not in (None, start) and int(body["pageStart"]) != start:
                    raise ConnectError(f"asked for page start {start} but the server answered with pageStart {body['pageStart']}: paging is not advancing")
                assets = body["Assets"]
                for a in assets:
                    oid = oid_of(a.get("id", ""))
                    if not oid or oid in seen:
                        continue
                    seen.add(oid)
                    attrs = {n: v.get("value") if isinstance(v, dict) else v for n, v in (a.get("Attributes") or {}).items()}
                    fields: dict[str, Any] = {"AssetType": atype}
                    for n, v in attrs.items():
                        fields[n] = _plain(v)
                    parents = _idrefs(attrs.get(parent_attr))
                    for attr, kind in link_attrs.items():
                        for tgt in _idrefs(attrs.get(attr)):
                            links.append((oid, tgt, str(kind), oid))
                    moment = str(a.get("id", "")).split(":")[2] if str(a.get("id", "")).count(":") >= 2 else ""
                    rows.append((oid, atype, fields, parents[0] if parents else None, moment))
                start += len(assets)
                total = body.get("total")
                if not assets or (isinstance(total, int) and start >= total) or (total is None and len(assets) < size):
                    break
                if peek and page_no >= peek:
                    notes.append(f"{atype}: [PEEK: first {peek} page(s) only]")
                    break
            else:
                raise ConnectError("stopped after max_pages")
            notes.append(f"{atype}: {len(rows) - before} assets")
        rows.sort(key=lambda r: (opt_list(o, "asset_types", DEFAULT_ASSET_TYPES).index(r[1]), int(r[0].split(":")[1]) if r[0].split(":")[-1].isdigit() else 0, r[0]))
        rev = hashlib.sha1(json.dumps([[r[0], r[2].get("ChangeDateUTC", "")] for r in rows]).encode()).hexdigest()[:16]
        self._cache[key] = (rows, links, notes, rev)
        return self._cache[key]

    def discover(self, src: Source) -> Discovery:
        rows, links, notes, _ = self._load(src)
        out = []
        for atype in opt_list(src.options, "asset_types", DEFAULT_ASSET_TYPES):
            sub = [r for r in rows if r[1] == atype]
            keys = sorted({k for r in sub for k in r[2]})
            out.append(Container(atype, len(sub), [make_field_info(k, [r[2].get(k, "") for r in sub]) for k in keys]))
        return Discovery(out, notes + [f"{len(links)} dependency links; Description is HTML: use strip_markup"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        rows, links, _, rev = self._load(src)
        base = self._base(src)
        for i, (oid, atype, fields, parent, moment) in enumerate(rows):
            yield RawRecord(native_id=oid, fields={**fields, "_moment": moment}, order=i, parent_native_id=parent,
                            ref=SourceRef("agility", base, container=atype, locator=oid, revision=rev))
        for a, b, kind, via in links:
            yield RawLink(a, b, kind, SourceRef("agility", base, container="links", locator=via, revision=rev))

    def revision(self, src: Source) -> str:
        c = next(iter(self._cache.values()), None)
        return c[3] if c else ""
