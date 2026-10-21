"""Siemens Polarion ALM: work items (requirements, test cases, headings ...) as records, over the REST API.

READ-ONLY. Only GET requests are made. The REST API is OFF by default: an administrator has to set com.siemens.polarion.rest.enabled=true and restart, and
the service account needs the read rights for the endpoint and for each item. A 404 on the first request therefore often means "not enabled", not "wrong URL".

URI:      polarion+https://host/polarion            (the part before /rest/v1)
Options:  project         REQUIRED. The project id, e.g. WIDGET.
          query           Polarion's Lucene query, e.g. query='type:requirement AND status:open'. Without one, every work item of the project is read.
          fields          default @all (sent as fields[workitems]); or a comma list such as id,title,description,status,type,outlineNumber
          page_size       default 100 (sent as page[size])
          sort            default id. SENT ON EVERY PAGE, because the vendor's own list of known limits says collection requests have NO default sorting, and
                          a paged read of an unordered list can skip or repeat items. "none" turns it off (a note says so); "-id" and other fields pass through.
          include_links   default true: ask for linkedWorkItems to be included (include=linkedWorkItems) so that each link comes with its role and target.
          role_map        JSON {"tests": "verify", "implements": {"kind": "satisfy", "source": "linked"}}: what each link ROLE becomes. A bare string is the kind,
                          with the work item that CARRIES the link as the source and the linked item as the target. "source": "linked" reverses that. A role that is
                          not listed keeps its own name lowercased as the kind and `discover` names it. Polarion's own pages do not say which end a role such as
                          `parent` points at, so the direction is YOUR decision per role: see parent_role.
          parent_role     the link role that points at a work item's PARENT (for example parent). Such a link becomes the record's parent, not a link. Off by
                          default, because the direction of the built-in roles was not verified.
          peek / max_pages  stop early for a trial run
          token_env       a personal access token (sent as Authorization: Bearer)
          cookie_env | auth_hook | ca_bundle | user_agent | max_wait     see connect.auth_from_options and make_http

WHAT IS VERIFIED AND WHAT IS NOT:
  from the vendor's documentation  base https://[server]/polarion/rest/v1; Authorization: Bearer {personal access token}; fields[workitems]=@all;
                                   include=linkedWorkItems with fields[linkedworkitems]=@all; resource kinds workitems, linkedworkitems, backlinkedWorkItems,
                                   externallylinkedworkitems; roles such as relates_to, parent, tests; page[number] on requests; a `links` object (first, last,
                                   self) in responses; collection GETs have no default sorting; rich text is returned as source (HTML or text), not rendered;
                                   linked-item lists stay inside the project, which is why `include` is the way to reach other projects' items.
  NOT seen live                    anything. Taken from third-party client libraries or recalled and so NOT confirmed: the parameter names page[size], query and sort,
                                   `links.next`, `meta.totalCount`, the exact shape of a link id (we read the example's shape
                                   <project>/<item>/<role>/<project>/<item> only when the server sent a link without its resource), and the work item attribute
                                   names. No baseline or LiveDoc-part endpoint is read: document structure is NOT read, only the work items.
  NOT read                         links that point AT an item from an item outside this query or project (backlinkedWorkItems), and external links.
  Tested only against an in-memory fake (tests/live_cases_more.py: polarion_server) that follows the shapes above.
  First run: reqin sample polarion+https://host/polarion --opt project=WIDGET --opt token_env=POLARION_TOKEN --opt query='type:requirement'
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from collections import Counter
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, opt_dict, opt_int
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from ._values import plain


def _flat(attrs: dict[str, Any]) -> dict[str, Any]:
    """Work item attributes as plain strings. A rich text attribute {type, value} gives its value and, beside it, its type."""
    out: dict[str, Any] = {}
    for k, v in attrs.items():
        if isinstance(v, dict) and "value" in v and "type" in v and isinstance(v.get("value"), str):
            out[k] = v["value"]
            out[f"{k}_type"] = str(v["type"])
        else:
            out[k] = plain(v)
    return out


def _parse_link_id(link_id: str) -> tuple[str, str, str] | None:
    """<project>/<item>/<role>/<project>/<item> -> (owner, role, target), or None when the id does not have that shape."""
    parts = link_id.split("/")
    if len(parts) != 5 or not all(parts):
        return None
    return f"{parts[0]}/{parts[1]}", parts[2], f"{parts[3]}/{parts[4]}"


@register
class PolarionAdapter(Adapter):
    name = "polarion"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, dict[str, Any]] = {}

    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("polarion+http://", "polarion+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and "/polarion/rest/v1" in u:
            return 0.85
        return 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    @staticmethod
    def _base(src: Source) -> str:
        return src.uri.removeprefix("polarion+").split("/rest/v1")[0].rstrip("/")

    @staticmethod
    def _role_map(o) -> dict[str, tuple[str, str]]:  # noqa: ANN001
        out: dict[str, tuple[str, str]] = {}
        for role, spec in opt_dict(o, "role_map").items():
            if isinstance(spec, str):
                out[str(role)] = (spec, "owner")
            elif isinstance(spec, dict) and spec.get("kind"):
                side = str(spec.get("source", "owner"))
                if side not in ("owner", "linked"):
                    raise ConnectError(f"role_map {role!r}: source must be owner or linked, got {side!r}")
                out[str(role)] = (str(spec["kind"]), side)
            else:
                raise ConnectError(f"role_map {role!r} must be a kind (a string) or {{\"kind\": ..., \"source\": \"owner\"|\"linked\"}}")
        return out

    def _same_host(self, base: str, url: str) -> bool:
        a, b = urllib.parse.urlsplit(base), urllib.parse.urlsplit(url)
        return (a.scheme, a.hostname, a.port or (443 if a.scheme == "https" else 80)) == (b.scheme, b.hostname, b.port or (443 if b.scheme == "https" else 80))

    # ---- the read, once per run, cached ----------------------------------------------------------------
    def _load(self, src: Source) -> dict[str, Any]:
        o = src.options
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in o.items() if a not in ("token", "token_env", "cookie_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        project = str(o.get("project") or "").strip()
        if not project:
            raise ConnectError("option 'project' is required: the Polarion project id, e.g. project=WIDGET")
        base = self._base(src)
        rest = f"{base}/rest/v1"
        self._http = http = make_http(o, self._transport, base_headers={"Accept": "application/json"})
        size = opt_int(o, "page_size", 100)
        sort = str(o.get("sort", "id") or "")
        include_links = str(o.get("include_links", "true")).lower() not in ("0", "false", "no")
        role_map = self._role_map(o)
        parent_role = str(o.get("parent_role") or "")
        notes: list[str] = []
        if not sort or sort.lower() == "none":
            sort = ""
            notes.append("no sort was sent: the vendor documents no default order for collection requests, so a paged read can skip or repeat work items")
        params: dict[str, Any] = {"fields[workitems]": str(o.get("fields") or "@all"), "page[size]": size, "page[number]": 1}
        if o.get("query"):
            params["query"] = o["query"]
        if sort:
            params["sort"] = sort
        if include_links:
            params["include"] = "linkedWorkItems"
            params["fields[linkedworkitems]"] = "@all"

        items: list[dict[str, Any]] = []
        link_res: dict[str, dict[str, Any]] = {}                 # link id -> {role, target}
        owner_of: dict[str, str] = {}                            # link id -> work item that lists it
        seen: set[str] = set()
        seen_urls: set[str] = set()
        dup = 0
        total: int | None = None
        url = f"{rest}/projects/{urllib.parse.quote(project, safe='')}/workitems"
        first = True
        page_no = 0
        peek = opt_int(o, "peek", 0)
        for _ in range(opt_int(o, "max_pages", 1_000_000)):
            page_no += 1
            try:
                body = http.get_json(url, params if first else None)
            except ConnectError as e:
                if first and e.status == 404:
                    raise ConnectError(f"{e} The Polarion REST API is off by default (com.siemens.polarion.rest.enabled=true, then a restart), "
                                       "and the project id must exist: check both", status=404) from None
                raise
            if not isinstance(body, dict) or not isinstance(body.get("data"), list):
                raise ConnectError(f"{http.safe_url(url)} did not return a JSON:API document (an object with a 'data' list): is this the Polarion REST root?")
            new_here = 0
            for it in body["data"]:
                rid = str(it.get("id") or "")
                if not rid:
                    continue
                if rid in seen:
                    dup += 1
                    continue
                new_here += 1
                seen.add(rid)
                attrs = it.get("attributes") or {}
                f = _flat(attrs)
                f["_resource_id"] = rid
                f.setdefault("id", rid.split("/")[-1])
                items.append({"rid": rid, "fields": f})
                for ref in (((it.get("relationships") or {}).get("linkedWorkItems") or {}).get("data") or []) if include_links else []:
                    if isinstance(ref, dict) and ref.get("id"):
                        owner_of[str(ref["id"])] = rid
            for inc in body.get("included") or []:
                if isinstance(inc, dict) and str(inc.get("type", "")).lower() == "linkedworkitems" and inc.get("id"):
                    tgt = (((inc.get("relationships") or {}).get("workItem") or {}).get("data") or {}).get("id")
                    link_res[str(inc["id"])] = {"role": str((inc.get("attributes") or {}).get("role", "")), "target": str(tgt or ""),
                                                "suspect": bool((inc.get("attributes") or {}).get("suspect"))}
            if body["data"] and new_here == 0:
                raise ConnectError(f"page {page_no} held only work items that were already read: the server is not advancing (does it honour page[number] and the next link?)")
            mt = (body.get("meta") or {}).get("totalCount")
            total = mt if isinstance(mt, int) else total
            nxt = (body.get("links") or {}).get("next")
            if peek and page_no >= peek:
                notes.append(f"[PEEK: first {peek} page(s) only, so counts and links are incomplete]")
                total = None
                break
            if nxt:
                nxt = str(nxt)
                if nxt.startswith("/"):
                    p = urllib.parse.urlsplit(base)
                    nxt = f"{p.scheme}://{p.netloc}{nxt}"
                if not nxt.startswith(("http://", "https://")):
                    nxt = f"{rest}/{nxt.lstrip('/')}"
                if not self._same_host(base, nxt):
                    raise ConnectError(f"the server's next link points at another host ({http.safe_url(nxt)}); credentials are never sent to a different host, so the read stops")
                if nxt in seen_urls or nxt == url:
                    raise ConnectError("the server's next link points back to a page already read: its paging is not advancing")
                seen_urls.add(nxt)
                url, first = nxt, False
                continue
            if not body["data"] or (total is not None and len(items) + dup >= total) or (total is None and len(body["data"]) < size):
                break
            # the server sent no next link: ask for the next page number ourselves
            params["page[number]"] = int(params["page[number]"]) + 1
            url, first = f"{rest}/projects/{urllib.parse.quote(project, safe='')}/workitems", True
        else:
            raise ConnectError("stopped after max_pages")

        # links
        links: list[tuple[str, str, str, str]] = []
        parents: dict[str, str] = {}
        unmapped: Counter[str] = Counter()
        from_ids = unread = 0
        seen_l: set[tuple[str, str, str]] = set()
        for lid, owner in owner_of.items():
            res = link_res.get(lid)
            if res and res["target"]:
                role, target = res["role"], res["target"]
            else:
                parsed = _parse_link_id(lid)
                if not parsed:
                    unread += 1
                    continue
                _, role, target = parsed
                from_ids += 1
            if parent_role and role == parent_role:
                parents[owner] = target
                continue
            if role in role_map:
                kind, side = role_map[role]
            else:
                kind, side = (role.lower() or "link"), "owner"
                unmapped[role] += 1
            a, b = (owner, target) if side == "owner" else (target, owner)
            if (a, b, kind) not in seen_l:
                seen_l.add((a, b, kind))
                links.append((a, b, kind, lid))
        notes.append(f"read {len(items)} work items; {len(links)} links" + (f"; {len(parents)} parents from the {parent_role!r} role" if parent_role else ""))
        if total is not None and not peek and total != len(items) + dup:
            notes.append(f"WARNING the server reported a totalCount of {total} but {len(items) + dup} came back; compare before trusting this read")
        if total is None and not peek:
            notes.append("the server sent no meta.totalCount, so there is no count to check the read against")
        if dup:
            notes.append(f"{dup} work items came back twice and were kept once")
        if unmapped:
            notes.append("link roles not in role_map, kept under their own name with the carrying item as source: " + ", ".join(f"{n or '(no role)'} x{c}" for n, c in unmapped.most_common(8)))
        if from_ids:
            notes.append(f"{from_ids} links were read from the shape of their id because the server did not include the link resources: check them against Polarion")
        if unread:
            notes.append(f"{unread} links could not be read (no included resource and an id of an unknown shape)")
        if not include_links:
            notes.append("include_links is off: no links were read")
        rev = hashlib.sha1(json.dumps([[i["rid"], i["fields"].get("updated", "")] for i in items]).encode()).hexdigest()[:16]
        out = {"items": items, "links": links, "parents": parents, "notes": notes, "rev": rev, "base": base}
        self._cache[key] = out
        return out

    # ---- the Adapter contract --------------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        d = self._load(src)
        by: dict[str, list[dict[str, Any]]] = {}
        for i in d["items"]:
            by.setdefault(str(i["fields"].get("type") or "(no type)"), []).append(i["fields"])
        cs = []
        for t, rows in sorted(by.items()):
            names = sorted({k for r in rows for k in r})
            cs.append(Container(t, len(rows), [make_field_info(k, [r.get(k, "") for r in rows]) for k in names]))
        return Discovery(cs, list(d["notes"]) + ["description is HTML or plain text as stored (see description_type); use strip_markup for HTML"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        d = self._load(src)
        for n, i in enumerate(d["items"]):
            yield RawRecord(native_id=i["rid"], fields=i["fields"], order=n, parent_native_id=d["parents"].get(i["rid"]),
                            ref=SourceRef("polarion", d["base"], container=str(i["fields"].get("type") or "workitem"), locator=i["rid"], revision=d["rev"]))
        for a, b, kind, via in d["links"]:
            yield RawLink(a, b, kind, SourceRef("polarion", d["base"], container="links", locator=via, revision=d["rev"]))

    def revision(self, src: Source) -> str:
        return self._load(src)["rev"]
