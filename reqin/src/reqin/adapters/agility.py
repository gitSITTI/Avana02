"""Digital.ai Agility (formerly VersionOne): stories, epics and defects as requirement-like records, over the REST Data API.

READ-ONLY. Only GET requests are made (the query.v1 endpoint is a POST and is deliberately NOT used; api/asset creates and deletes and is never touched).
If you work from the grid "Export (.xls)" instead, you do not need this connector: that file is an HTML table, which the tabular adapter
reads with profiles/agility_export.yaml.

URI:      agility+https://host/Instance          (the part before /rest-1.v1)
Options:  asset_types     comma list, default Epic,Story,Defect. Others the vendor documents as able to hold requirement text: Request, Goal, Theme;
                          Test and Task hold acceptance criteria; Issue is a blocker; abstract types such as PrimaryWorkitem can be read as one stream.
          select          comma list of attributes for every type, default Number,Name,Description,Scope.Name,Status.Name,AssetState,Super,Dependencies,ChangeDateUTC
          select_by_type  JSON {"Epic": ["Number", ...], "Goal": [...]}: used EXACTLY as given for that type. Needed because an attribute that does not
                          exist on one type is HTTP 400 for the whole type, and the types do not share all attributes.
          preflight       "meta": before reading a type, GET meta.v1/<Type> (documented as XML, no authentication) and leave out selected attributes the
                          type does not have, saying which. If the answer cannot be understood the select is sent as given.
          where           Agility where-clause: equality terms joined by ';', e.g. where="Scope.Name='My Project';AssetState='64'". The vendor's examples
                          show only equality; do not rely on != inside where. Deleted assets are hidden by default, so there is nothing to exclude.
          sort            attribute to sort by, default Number ("none" turns it off). Without a sort the vendor documents no order, and paged reads of an
                          unordered list can skip or repeat rows.
          page_size       default 500 (the vendor documents no default page size and no maximum: a call without `page` returns the whole table)
          format          json (default; sends Accept: application/json) or xml (sends Accept: text/xml). Whatever comes back is read as JSON or XML.
          parent_attr     attribute holding the parent (default Super: a story's epic. `Parent` is the backlog group, a different hierarchy)
          link_attrs      JSON {"Attribute": "kind"}, default {"Dependencies": "trace"}  (this -> each referenced asset)
          select_param    name of the select query parameter, default sel
          token_env       environment variable with an Agility access token (sent as Authorization: Bearer)
          basic_user_env + basic_password_env | cookie_env | auth_hook | ca_bundle | user_agent | max_wait     see connect.auth_from_options and make_http

WHAT IS VERIFIED AND WHAT IS NOT:
  from the vendor's documentation  GET <base>/rest-1.v1/Data/<Asset> returns XML by default and JSON with Accept: application/json;
                                   JSON {"_type":"Assets","total":N,"pageSize":..,"pageStart":..,"Assets":[{"id":"Story:1005","Attributes":{"Name":{"name":"Name","value":..}}}]}
                                   and the XML twin <Assets total pageSize pageStart><Asset id=".."><Attribute name="..">..</Attribute><Relation name=".."><Asset idref=".."/></Relation>;
                                   page=size,start counts items; access tokens go in Authorization: Bearer; the AssetState codes
                                   (0 Future, 64 Active, 128 Closed, 200 Template, 208 Broken Down, 255 Deleted); Super is the portfolio parent;
                                   an attribute unknown to a type is HTTP 400; a 429 carries the wait as RetryAfter in a JSON body (the kit reads it).
  NOT seen live                    anything: no Agility instance was available. How a multi-valued relation looks in JSON (we accept {"idref": "Epic:12"},
                                   a list of those, or a bare "Epic:12"); the REST names of dependencies (Dependencies is recalled, not read: check meta.v1);
                                   whether `sort=Number` is accepted on every type; the real shape of meta.v1 (we look for elements named AttributeDefinition).
  Tested only against an in-memory fake (tests/live_cases.py: agility_server) that follows the documented shapes above.
  First run on your instance: reqin sample agility+https://host/Instance --opt token_env=AGILITY_TOKEN --opt where="Scope.Name='<project>'"
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, opt_dict, opt_int, opt_list, safe_xml
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


def assets_from_xml(raw: bytes) -> dict[str, Any]:
    """The documented XML of rest-1.v1 as the same dict the JSON form gives:
    <Assets total pageSize pageStart><Asset id><Attribute name>text</Attribute><Relation name><Asset idref/></Relation></Asset></Assets>."""
    root = safe_xml(raw, "the Agility response")
    if root.tag != "Assets":
        raise ConnectError(f"the Agility response is XML but its root element is <{root.tag}>, not <Assets>")
    out: dict[str, Any] = {"_type": "Assets", "Assets": []}
    for k in ("total", "pageSize", "pageStart"):
        if root.get(k, "").lstrip("-").isdigit():
            out[k] = int(root.get(k))
    for a in root.findall("Asset"):
        attrs: dict[str, Any] = {}
        for child in a:
            name = child.get("name", "")
            if not name:
                continue
            if child.tag == "Attribute":
                attrs[name] = {"name": name, "value": (child.text or "").strip() if (child.text or "").strip() or len(child) else None}
            elif child.tag == "Relation":
                refs = [{"_type": "Asset", "idref": x.get("idref") or x.get("id", "")} for x in child.findall("Asset")]
                attrs[name] = {"name": name, "value": None if not refs else refs[0] if len(refs) == 1 else refs}
        out["Assets"].append({"_type": "Asset", "href": a.get("href", ""), "id": a.get("id", ""), "Attributes": attrs})
    return out


def _meta_attribute_names(http: ReadOnlyHttp, base: str, atype: str) -> set[str] | None:
    """Attribute names of one asset type from meta.v1 (documented as XML and as needing no authentication). None when the answer cannot be understood."""
    try:
        resp = http.get(f"{base}/meta.v1/{atype}", headers={"Accept": "text/xml"})
        root = safe_xml(resp.body, f"meta.v1/{atype}")
    except ConnectError:
        return None
    names = {e.get("name", "") for e in root.iter() if e.tag.rsplit("}", 1)[-1].lower() == "attributedefinition" and e.get("name")}
    return names or None


def _read_page(http: ReadOnlyHttp, url: str, params: dict[str, Any], fmt: str) -> dict[str, Any]:
    resp = http.get(url, params, {"Accept": "application/json" if fmt == "json" else "text/xml"})
    body = resp.body.lstrip()
    if body[:1] in (b"{", b"["):
        data = http.parse_json(resp)
        if isinstance(data, dict) and "Assets" in data:
            return data
    elif body[:7] == b"<Assets" or (body[:5] == b"<?xml" and b"<Assets" in body[:2048]):
        return assets_from_xml(resp.body)
    snippet = http.scrub(resp.text()[:100].replace("\n", " "))
    raise ConnectError(f"{http.safe_url(url)} did not return Agility's {{\"Assets\": [...]}} JSON or its <Assets> XML (content-type {resp.headers.get('content-type', '?')!r}; "
                       f"starts with {snippet!r}). A login page looks like this: check the URL, the instance name and the credentials.")


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
        fmt = str(o.get("format") or "json").lower()
        if fmt not in ("json", "xml"):
            raise ConnectError(f"option 'format' must be json or xml, got {fmt!r}")
        self._http = http = make_http(o, self._transport, base_headers={"Accept": "application/json" if fmt == "json" else "text/xml"})
        base = self._base(src)
        size = opt_int(o, "page_size", 500)
        select = opt_list(o, "select", DEFAULT_SELECT)
        by_type = {str(k): [str(x) for x in v] if isinstance(v, list) else opt_list({"v": v}, "v", []) for k, v in opt_dict(o, "select_by_type").items()}
        parent_attr = str(o.get("parent_attr", "Super"))
        link_attrs = opt_dict(o, "link_attrs", DEFAULT_LINK_ATTRS)
        for needed in {parent_attr, *link_attrs}:
            if needed not in select:
                select.append(needed)
        sort = str(o.get("sort", "Number") or "")
        preflight = str(o.get("preflight") or "")
        if preflight not in ("", "meta"):
            raise ConnectError(f"option 'preflight' must be meta or empty, got {preflight!r}")
        types = opt_list(o, "asset_types", DEFAULT_ASSET_TYPES)
        rows: list[tuple[str, str, dict[str, Any], str | None, str]] = []   # oid, type, fields, parent, moment
        links: list[tuple[str, str, str, str]] = []
        notes: list[str] = []
        seen: set[str] = set()
        for atype in types:
            start, before, reported_total = 0, len(rows), None
            sel = list(by_type[atype]) if atype in by_type else list(select)
            if preflight == "meta":
                have = _meta_attribute_names(http, base, atype)
                if have is None:
                    notes.append(f"{atype}: meta.v1 gave no attribute list that could be read; the select was sent as given")
                else:
                    gone = [x for x in sel if x.split(".")[0] not in have]
                    if gone:
                        sel = [x for x in sel if x not in gone]
                        notes.append(f"{atype}: left out of the select because meta.v1 does not list them for this type: {', '.join(gone)}")
            peek = opt_int(o, "peek", 0)
            for page_no in range(1, opt_int(o, "max_pages", 1_000_000) + 1):
                params: dict[str, Any] = {str(o.get("select_param", "sel")): ",".join(sel), "page": f"{size},{start}"}
                if sort and sort.lower() != "none":
                    params["sort"] = sort
                if o.get("where"):
                    params["where"] = o["where"]
                body = _read_page(http, f"{base}/rest-1.v1/Data/{atype}", params, fmt)
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
                reported_total = total if isinstance(total, int) else reported_total
                if not assets or (isinstance(total, int) and start >= total) or (total is None and len(assets) < size):
                    break
                if peek and page_no >= peek:
                    notes.append(f"{atype}: [PEEK: first {peek} page(s) only]")
                    break
            else:
                raise ConnectError("stopped after max_pages")
            notes.append(f"{atype}: {len(rows) - before} assets")
            if reported_total is not None and not peek and reported_total != start:
                notes.append(f"{atype}: WARNING the server reported a total of {reported_total} but {start} came back; compare before trusting this read")
        rows.sort(key=lambda r: (types.index(r[1]), int(r[0].split(":")[1]) if r[0].split(":")[-1].isdigit() else 0, r[0]))
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
