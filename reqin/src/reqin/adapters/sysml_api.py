"""SysML v2 Systems Modeling API (REST): the production route to large online SysML v2 projects
(Teamwork Cloud / Magic Collaboration Studio at https://<server>:8443/sysmlv2-api/, SysON at /api/rest, the Pilot Implementation).

READ-ONLY. Only GET requests are ever made (see connect.py).

URI:      sysml+https://host:8443/sysmlv2-api        (the `sysml+` prefix is optional if the URL contains /sysmlv2-api or /api/rest)
Options:  project_id | project_name     which project (name is looked up through GET /projects)
          branch                        branch name or id; default = the project's default branch
          commit_id                     read this commit instead (overrides branch)
          page_size                     elements per request, default 500
          paging                        auto (default) | link | cursor | none      (see _pages)
          page_style                    bracket (page[size], default) | underscore (page_size)
          token_env                     name of the environment variable holding a bearer token   (see connect.auth_from_options)
          ca_bundle                     path to your organisation's CA bundle (TLS is always verified)
          req_types                     comma list, default RequirementDefinition,RequirementUsage
          link_types                    JSON {"RelationshipType": "kind"}, default {"Dependency": "trace"}
          keys                          JSON overrides for the JSON property names below

WHAT IS VERIFIED AND WHAT IS NOT (be honest with yourself before trusting a number from this):
  verified in public docs   GET /projects/{projectId}/commits/{commitId}/elements returns a JSON array; /projects, @id, @type,
                            declaredName; SysON uses the project id as the commit id; TWC serves the standard API under /sysmlv2-api
  from the OMG spec, NOT seen live   defaultBranch on a project and head on a branch; the Link header for paging; page[size] /
                            page[after]; owner on elements; Documentation.body; the property names of relationships
  everything here is tested against an in-memory FAKE of that API (tests/test_live_connectors.py), never a real server.
  First run against your server:  reqin sample sysml+https://... --opt project_name=... --opt token_env=TWC_TOKEN
  and compare one element's JSON with the names in DEFAULT_KEYS; fix them with `keys` (no code change needed).
"""
from __future__ import annotations

import hashlib
import json
import urllib.parse
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, next_link, opt_dict, opt_int, opt_list
from ..model import Fidelity, RawLink, RawRecord, SourceRef

DEFAULT_KEYS = {
    "id": "@id", "type": "@type", "name": "declaredName", "short": "declaredShortName",
    "doc_body": "body", "owner": "owner", "doc_list": "documentation",
    "rel_source": ["source", "client"], "rel_target": ["target", "supplier"],
    "default_branch": "defaultBranch", "head": "head", "project_name": "name", "branch_name": "name",
    "doc_types": ["Documentation"],
}
DEFAULT_REQ_TYPES = ["RequirementDefinition", "RequirementUsage"]
DEFAULT_LINK_TYPES = {"Dependency": "trace"}
_STRUCTURAL = {"@id", "@type", "declaredName", "declaredShortName", "owner"}


def _ref(v: Any) -> str:
    """A reference in the API's JSON is {"@id": "..."} (or a bare string)."""
    if isinstance(v, dict):
        return str(v.get("@id", ""))
    return "" if v is None else str(v)


def _refs(v: Any) -> list[str]:
    if v is None:
        return []
    return [r for r in (_ref(x) for x in (v if isinstance(v, list) else [v])) if r]


@dataclass
class _Snapshot:
    rows: list[tuple[str, dict[str, Any], str | None]]       # (native id, fields, parent id)
    links: list[tuple[str, str, str, str]]                    # (source, target, kind, relationship id)
    project: str
    commit: str
    notes: list[str] = field(default_factory=list)


@register
class SysMLApiAdapter(Adapter):
    name = "sysml_api"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, _Snapshot] = {}

    # ---- identification ------------------------------------------------------------------------
    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("sysml+http://", "sysml+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and any(m in u for m in ("/sysmlv2-api", "/api/rest")):
            return 0.9
        return 0.0

    @staticmethod
    def _base(src: Source) -> str:
        return src.uri.removeprefix("sysml+").rstrip("/")

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    # ---- talking to the server -------------------------------------------------------------------
    def _client(self, src: Source) -> ReadOnlyHttp:
        self._http = make_http(src.options, self._transport, base_headers={"Accept": "application/json"})
        return self._http

    def _keys(self, src: Source) -> dict[str, Any]:
        return {**DEFAULT_KEYS, **opt_dict(src.options, "keys")}

    def _pages(self, http: ReadOnlyHttp, url: str, src: Source, k: dict[str, Any], peek: int = 0) -> Iterator[list[dict]]:
        """Yield lists of elements, following the server's paging.

        paging=auto   follow the Link header (rel="next"); if a FULL page arrives without one, continue with the cursor
                      page[after]=<id of the last element>. Progress is checked on every page: a repeated page raises an
                      error instead of looping or silently truncating.
        paging=link   Link header only; a full page without a Link header is an error.
        paging=cursor always use page[after].
        paging=none   one request, no page parameters (servers that return everything at once).
        A page shorter than page_size with no Link header means 'done'.
        """
        o = src.options
        size = opt_int(o, "page_size", 500)
        mode = str(o.get("paging", "auto"))
        style = str(o.get("page_style", "bracket"))
        if mode not in ("auto", "link", "cursor", "none") or style not in ("bracket", "underscore"):
            raise ConnectError("paging must be auto|link|cursor|none and page_style bracket|underscore")
        size_key, after_key = ("page[size]", "page[after]") if style == "bracket" else ("page_size", "page_after")
        base_params: dict[str, Any] = {} if mode == "none" else {size_key: size}
        next_url, params = url, dict(base_params)
        first_ids: set[str] = set()
        max_pages = opt_int(o, "max_pages", 1_000_000)
        for page_no in range(1, max_pages + 1):
            resp = http.get(next_url, params)
            data = http.parse_json(resp) or []
            if isinstance(data, dict):
                data = next((data[x] for x in ("elements", "items", "value", "content") if isinstance(data.get(x), list)), None)
            if not isinstance(data, list):
                raise ConnectError(f"{http.safe_url(next_url)} did not return a JSON array of elements; if this server wraps them, set page 'keys' or paging=none")
            if not data:
                return
            first = _ref(data[0].get(k["id"])) if isinstance(data[0], dict) else ""
            if first and first in first_ids:
                raise ConnectError("paging is not advancing: the server returned a page already seen. "
                                   "Set paging=link or paging=cursor or page_style explicitly (see CONNECTORS.md).")
            first_ids.add(first)
            yield data
            if peek and page_no >= peek:
                return                                            # `reqin sample`: look at the first page(s) only
            link = next_link(resp.headers.get("link")) if mode != "cursor" else None
            if link:
                next_url, params = urllib.parse.urljoin(next_url, link), {}
                continue
            if mode == "none" or len(data) != size:
                return                                            # a short page (or an unpaged server) is the end
            if mode == "link":
                raise ConnectError(f"a full page of {size} arrived without a Link header, so more may exist; refusing to guess "
                                   "(use paging=auto or paging=cursor if your server pages by cursor)")
            last = _ref(data[-1].get(k["id"])) if isinstance(data[-1], dict) else ""
            if not last:
                raise ConnectError("cannot continue paging: the last element has no id")
            next_url, params = url, {**base_params, after_key: last}
        raise ConnectError(f"stopped after {max_pages} pages (max_pages)")

    def _resolve_project(self, http: ReadOnlyHttp, base: str, src: Source, k: dict[str, Any]) -> str:
        o = src.options
        if o.get("project_id"):
            return str(o["project_id"])
        want = o.get("project_name")
        if not want:
            raise ConnectError("give project_id or project_name (the project list is at GET <base>/projects)")
        names = []
        for page in self._pages(http, f"{base}/projects", src, k):
            for p in page:
                names.append(str(p.get(k["project_name"], "")))
                if p.get(k["project_name"]) == want:
                    return _ref(p.get(k["id"]))
        raise ConnectError(f"no project named {want!r}. Projects on this server: {sorted(set(names))[:20]}")

    def _resolve_commit(self, http: ReadOnlyHttp, base: str, pid: str, src: Source, k: dict[str, Any], notes: list[str]) -> str:
        o = src.options
        if o.get("commit_id"):
            notes.append("commit given explicitly")
            return str(o["commit_id"])
        try:
            bid = ""
            if o.get("branch"):
                want = str(o["branch"])
                for page in self._pages(http, f"{base}/projects/{pid}/branches", src, k):
                    for b in page:
                        if want in (b.get(k["branch_name"]), _ref(b.get(k["id"]))):
                            bid = _ref(b.get(k["id"]))
                if not bid:
                    raise ConnectError(f"no branch {want!r} in this project")
            else:
                bid = _ref((http.get_json(f"{base}/projects/{pid}") or {}).get(k["default_branch"]))
            if bid:
                head = _ref((http.get_json(f"{base}/projects/{pid}/branches/{bid}") or {}).get(k["head"]))
                if head:
                    notes.append(f"commit {head} = head of branch {bid}")
                    return head
        except ConnectError as e:
            if e.status != 404:
                raise
        notes.append("no branch/head found: used the project id as the commit id (this is how SysON works; check it is right for your server)")
        return pid

    # ---- the read, done once per run and cached ----------------------------------------------------
    def _load(self, src: Source) -> _Snapshot:
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in src.options.items() if a not in ("token", "token_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        http, k = self._client(src), self._keys(src)
        base, notes = self._base(src), []
        pid = self._resolve_project(http, base, src, k)
        cid = self._resolve_commit(http, base, pid, src, k, notes)
        req_types = set(opt_list(src.options, "req_types", DEFAULT_REQ_TYPES))
        link_types = opt_dict(src.options, "link_types", DEFAULT_LINK_TYPES)

        reqs: dict[str, dict] = {}
        docs: list[tuple[str, str, str]] = []                    # (doc id, owner id, body) in arrival order
        rels: list[tuple[str, str, list[str], list[str]]] = []
        n = 0
        types_seen: Counter[str] = Counter()
        peek = opt_int(src.options, "peek", 0)
        for page in self._pages(http, f"{base}/projects/{pid}/commits/{cid}/elements", src, k, peek=peek):
            for e in page:
                n += 1
                t, eid = e.get(k["type"]), _ref(e.get(k["id"]))
                types_seen[str(t)] += 1
                if t in req_types:
                    reqs[eid] = e
                elif t in k["doc_types"] and e.get(k["doc_body"]):
                    docs.append((eid, _ref(e.get(k["owner"])), str(e[k["doc_body"]])))
                elif t in link_types:
                    s = next((_refs(e.get(x)) for x in k["rel_source"] if e.get(x)), [])
                    d = next((_refs(e.get(x)) for x in k["rel_target"] if e.get(x)), [])
                    rels.append((eid, str(link_types[t]), s, d))
        notes.append(f"read {n} elements; {len(reqs)} requirement elements; {len(docs)} documentation elements"
                     + (f"  [PEEK: first {peek} page(s) only, so counts and text are incomplete]" if peek else ""))
        if n and not reqs:
            top = ", ".join(f"{t}: {c}" for t, c in types_seen.most_common(12))
            notes.append(f"WARNING: no element has a type in {sorted(req_types)}. Types seen: {top}. Use req_types=... (and keys=... if the property names differ)")

        by_owner: dict[str, list[str]] = {}
        by_id = {d[0]: d for d in docs}
        for did, owner, body in docs:
            by_owner.setdefault(owner, []).append(body)
        rows = []
        for eid, e in reqs.items():
            texts = list(by_owner.get(eid, []))
            for did in _refs(e.get(k["doc_list"])):               # the requirement may list its documentation itself
                if did in by_id and by_id[did][2] not in texts:
                    texts.append(by_id[did][2])
            owner = _ref(e.get(k["owner"]))
            f: dict[str, Any] = {"shortName": e.get(k["short"]) or "", "name": e.get(k["name"]) or "", "kind": e.get(k["type"]),
                                 "doc": " ".join(texts).strip(), "owner": owner}
            for pk, pv in e.items():                              # keep every other plain property: nothing is lost
                if pk not in _STRUCTURAL and pk not in f and isinstance(pv, (str, int, float, bool)) and pv != "":
                    f[f"prop.{pk}"] = pv
            rows.append((eid, f, owner if owner in reqs else None))
        links = [(s, d, kind, rid) for rid, kind, ss, ds in rels for s in ss for d in ds if s in reqs or d in reqs]
        snap = _Snapshot(rows, links, pid, cid, notes)
        self._cache[key] = snap
        return snap

    # ---- the adapter contract --------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        s = self._load(src)
        cols = ["shortName", "name", "kind", "doc", "owner"]
        return Discovery([Container("requirements", len(s.rows), [make_field_info(c, [f.get(c, "") for _, f, _ in s.rows]) for c in cols])],
                         [f"project {s.project}, commit {s.commit}"] + s.notes
                         + ["documentation text lives in separate Documentation elements and is joined to its owner"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        s = self._load(src)
        base = self._base(src)
        rev = f"{s.project}@{s.commit}"
        for i, (eid, f, parent) in enumerate(s.rows):
            yield RawRecord(native_id=eid, fields=f, order=i, parent_native_id=parent,
                            ref=SourceRef("sysml_api", base, container="requirements", locator=eid, revision=rev))
        for sid, tid, kind, rid in s.links:
            yield RawLink(sid, tid, kind, SourceRef("sysml_api", base, container="relationships", locator=rid, revision=rev))

    def revision(self, src: Source) -> str:
        s = self._cache and next(iter(self._cache.values()))
        return f"{s.project}@{s.commit}" if s else str(src.options.get("commit_id", ""))
