"""Jama Connect: items (requirements, test cases, folders ...) and the relationships between them, over the REST API.

READ-ONLY. Only GET requests are made. Jama's OAuth login is a POST, which this connector deliberately does not make: mint the token with the small helper in
connectors/jama/jama_oauth_hook.py (a file you run on purpose, outside the read-only code) or give a token you already have. See `auth_hook` below.

URI:      jama+https://yourorg.jamacloud.com        (the part before /rest/v1)
Options:  project         REQUIRED. The project id (a number), or its exact name or project key (looked up with GET /projects).
          item_types      comma list of item type names, type keys or ids to keep, e.g. Requirement,REQ. Default: every item. The listing includes folders, sets
                          and text items, so read everything only to see what is there (`reqin discover`), then narrow it.
          items_path      default abstractitems (the listing endpoint that returns every kind of item in a project)
          page_size       default 50 (the vendor documents a default of 20 and an upper limit of 50 for items)
          relationships   true (default) | false: read the relationships of the project
          link_direction  downstream_to_upstream (default): the SOURCE of a link is the downstream item (toItem), the TARGET the upstream item (fromItem). That is how a
                          test case "verifies" or a derived requirement "derives from" a requirement: the repo's convention is source = the one that does the
                          satisfying, verifying or deriving. upstream_to_downstream reverses it. Jama's help says relationships run from higher level to lower
                          level; which of fromItem and toItem is which was NOT confirmed on a page, so check one link.
          link_map        JSON {"Verified by": "verify", "Derived": "derive"}: what each relationship TYPE (by name) becomes. A type that is not listed keeps its
                          own name lowercased as the kind and `discover` names it. If the type names cannot be read the kind is "reltype-<id>".
          picklist_fields comma list of FIELD names whose values are pick list option ids (status, priority ...): each id is looked up once with
                          GET /picklistoptions/<id> and replaced by its name. Off by default: the connector cannot tell a pick list id from any other number.
          peek / max_pages  stop early for a trial run
          token_env       an OAuth bearer token (sent as Authorization: Bearer)
          basic_user_env + basic_password_env   a user and password; the vendor says Basic does not work with SAML/SSO accounts
          auth_hook       e.g. jama_oauth_hook:headers (with token_url=https://yourorg.jamacloud.com/rest/oauth/token, and JAMA_CLIENT_ID / JAMA_CLIENT_SECRET in the
                          environment): see connectors/jama/jama_oauth_hook.py
          cookie_env | ca_bundle | user_agent | max_wait     see connect.auth_from_options and make_http

WHAT IS VERIFIED AND WHAT IS NOT:
  from the vendor's documentation  REST under /rest/v1, JSON only; item lists page with startAt and maxResults and answer with meta.pageInfo (startIndex,
                                   resultCount, totalResults); the default is 20 and the upper limit 50; relationships page with project, lastId, maxResults
                                   (1 to 1000) and omitCount, and an example relationship has id, fromItem, toItem, type and suspect; item types are reached
                                   through /itemtypes and admins change them, so none is hard-coded; relationships from /relationships are the CURRENT ones
                                   (a baseline's versioned relationships are another set of calls, not read here); the OAuth token comes from POST
                                   /rest/oauth/token with grant_type=client_credentials and the client id and secret as Basic, and lasts about an hour; a 429
                                   comes above 10 requests a second (the kit retries it); a Named Creator licence is needed for REST access.
  NOT seen live                    anything. Recalled and so NOT confirmed: the path abstractitems and its parameters (project, startAt, maxResults), that a field's
                                   key is its name with $<item type id> after it (status$27: this reader strips the suffix), that an item has itemType, documentKey,
                                   globalId, modifiedDate and location.parent.item, that relationships carry their type id as relationshipType, the paths
                                   /itemtypes, /relationshiptypes and /picklistoptions/<id> and their fields (display, typeKey, name), and the direction of
                                   fromItem and toItem.
  NOT read                         baselines, attachments, comments, and versions: only the current items and relationships.
  Tested only against an in-memory fake (tests/live_cases_more.py: jama_server) that follows the shapes above, the 50-item limit included.
  First run: reqin sample jama+https://yourorg.jamacloud.com --opt project=<id or name> --opt token_env=JAMA_TOKEN
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, opt_dict, opt_int, opt_list
from ..model import Fidelity, RawLink, RawRecord, SourceRef
from ._values import plain

_SUFFIX = re.compile(r"\$\d+$")


def _pages(http: ReadOnlyHttp, url: str, params: dict[str, Any], size: int, what: str, max_pages: int, state: dict[str, Any] | None = None) -> Iterator[list[dict[str, Any]]]:
    """Pages of a startAt/maxResults list, until meta.pageInfo says the end (or a page comes back empty). state["total"] gets the last totalResults seen."""
    start = 0
    for _ in range(max_pages):
        body = http.get_json(url, {**params, "startAt": start, "maxResults": size})
        if not isinstance(body, dict) or not isinstance(body.get("data"), list):
            raise ConnectError(f"{http.safe_url(url)} did not return the list shape (an object with a 'data' list): is this the Jama REST root, and is the {what} path right?")
        data = body["data"]
        info = ((body.get("meta") or {}).get("pageInfo")) or {}
        yield data
        got = info.get("resultCount") if isinstance(info.get("resultCount"), int) else len(data)
        total = info.get("totalResults")
        if state is not None and isinstance(total, int):
            state["total"] = total
        start += got
        if not data or got == 0 or (isinstance(total, int) and start >= total) or (total is None and got < size):
            return
    raise ConnectError("stopped after max_pages")


@register
class JamaAdapter(Adapter):
    name = "jama"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, dict[str, Any]] = {}

    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("jama+http://", "jama+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and "/rest/v1" in u and ("jama" in u.lower()):
            return 0.8
        return 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    @staticmethod
    def _base(src: Source) -> str:
        return src.uri.removeprefix("jama+").split("/rest/")[0].rstrip("/")

    # ---- the read, once per run, cached ----------------------------------------------------------------
    def _load(self, src: Source) -> dict[str, Any]:
        o = src.options
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in o.items() if a not in ("token", "token_env", "cookie_env", "basic_password_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        want_project = str(o.get("project") or "").strip()
        if not want_project:
            raise ConnectError("option 'project' is required: the project id, name or key")
        direction = str(o.get("link_direction") or "downstream_to_upstream")
        if direction not in ("downstream_to_upstream", "upstream_to_downstream"):
            raise ConnectError(f"option 'link_direction' must be downstream_to_upstream or upstream_to_downstream, got {direction!r}")
        base = self._base(src)
        rest = f"{base}/rest/v1"
        self._http = http = make_http(o, self._transport, base_headers={"Accept": "application/json"})
        size = opt_int(o, "page_size", 50)
        max_pages = opt_int(o, "max_pages", 1_000_000)
        peek = opt_int(o, "peek", 0)
        notes: list[str] = []
        link_map = {str(k): str(v) for k, v in opt_dict(o, "link_map").items()}

        # project
        if want_project.isdigit():
            pid = want_project
        else:
            found: list[tuple[str, str, str]] = []
            for page in _pages(http, f"{rest}/projects", {}, 50, "projects", max_pages):
                for p in page:
                    f = p.get("fields") or {}
                    found.append((str(p.get("id")), str(f.get("name", "")), str(f.get("projectKey", ""))))
            hit = [x for x in found if want_project in (x[1], x[2])]
            if len(hit) != 1:
                raise ConnectError(f"{'no' if not hit else 'several'} project named or keyed {want_project!r}. Projects: {[(i, n, k) for i, n, k in found][:30]}")
            pid = hit[0][0]
            notes.append(f"project {want_project!r} is id {pid}")

        # item types (names for the records; a failed lookup is a note, not the end)
        types: dict[str, dict[str, str]] = {}
        try:
            for page in _pages(http, f"{rest}/itemtypes", {}, 50, "item types", max_pages):
                for t in page:
                    types[str(t.get("id"))] = {"name": str(t.get("display") or t.get("name") or ""), "key": str(t.get("typeKey") or "")}
        except ConnectError as e:
            if e.status == 401:
                raise                                        # the credentials are rejected: not something to carry on past
            notes.append(f"item type names could not be read from /itemtypes ({str(e)[:80]}); records carry the type id only")
        keep = {x.lower() for x in opt_list(o, "item_types", [])}

        # items
        picklist_fields = set(opt_list(o, "picklist_fields", []))
        raw_items: list[dict[str, Any]] = []
        seen: set[str] = set()
        dup = 0
        state: dict[str, Any] = {}
        path = str(o.get("items_path") or "abstractitems").strip("/")
        for n_page, page in enumerate(_pages(http, f"{rest}/{path}", {"project": pid}, size, "items", max_pages, state), start=1):
            for it in page:
                iid = str(it.get("id", ""))
                if not iid:
                    continue
                if iid in seen:
                    dup += 1
                    continue
                seen.add(iid)
                raw_items.append(it)
            if peek and n_page >= peek:
                notes.append(f"[PEEK: first {peek} page(s) only, so counts and links are incomplete]")
                break
        reported_total = state.get("total")

        picks: dict[str, str] = {}
        rows: list[dict[str, Any]] = []
        for it in raw_items:
            tid = str(it.get("itemType", ""))
            tinfo = types.get(tid, {"name": "", "key": ""})
            if keep and not ({tid.lower(), tinfo["name"].lower(), tinfo["key"].lower()} & keep):
                continue
            rec: dict[str, Any] = {"id": str(it.get("id")), "documentKey": plain(it.get("documentKey")), "globalId": plain(it.get("globalId")),
                                   "itemType": tinfo["name"] or tid, "itemTypeId": tid, "project": plain(it.get("project")),
                                   "modifiedDate": plain(it.get("modifiedDate")), "createdDate": plain(it.get("createdDate"))}
            for fk, fv in (it.get("fields") or {}).items():
                name = _SUFFIX.sub("", fk)
                if name in picklist_fields and fv not in (None, ""):
                    fv = self._option_name(http, rest, fv, picks, notes)
                rec[name if name not in rec else fk] = plain(fv)
            loc = ((it.get("location") or {}).get("parent") or {}).get("item")
            rows.append({"id": rec["id"], "fields": rec, "parent": str(loc) if loc not in (None, "") else None})
        have = {r["id"] for r in rows}
        for r in rows:
            if r["parent"] not in have:
                r["parent"] = None                              # a folder or set above the item is not a record in this read

        # relationships
        links: list[tuple[str, str, str, str]] = []
        suspect = 0
        unmapped: Counter[str] = Counter()
        if str(o.get("relationships", "true")).lower() not in ("0", "false", "no") and not peek:
            rel_names: dict[str, str] = {}
            try:
                for page in _pages(http, f"{rest}/relationshiptypes", {}, 50, "relationship types", max_pages):
                    for t in page:
                        rel_names[str(t.get("id"))] = str(t.get("name") or t.get("display") or "")
            except ConnectError as e:
                if e.status == 401:
                    raise
                notes.append(f"relationship type names could not be read ({str(e)[:80]}); kinds are reltype-<id>")
            last_id: int | None = None
            rel_size = opt_int(o, "rel_page_size", 1000)
            n_rel = 0
            for _ in range(max_pages):
                params: dict[str, Any] = {"project": pid, "maxResults": rel_size, "omitCount": "true"}
                if last_id is not None:
                    params["lastId"] = last_id
                body = http.get_json(f"{rest}/relationships", params)
                if not isinstance(body, dict) or not isinstance(body.get("data"), list):
                    raise ConnectError("the relationships answer is not the list shape (an object with a 'data' list)")
                data = body["data"]
                for r in data:
                    n_rel += 1
                    a, b = str(r.get("fromItem") or ""), str(r.get("toItem") or "")
                    if not a or not b:
                        continue
                    rt = r.get("relationshipType") if r.get("relationshipType") is not None else (r.get("type") if isinstance(r.get("type"), int) else None)
                    tname = rel_names.get(str(rt), "") if rt is not None else ""
                    if tname in link_map:
                        kind = link_map[tname]
                    else:
                        kind = tname.lower() if tname else (f"reltype-{rt}" if rt is not None else "trace")
                        unmapped[tname or (f"reltype-{rt}" if rt is not None else "(no type)")] += 1
                    suspect += 1 if r.get("suspect") else 0
                    src_id, tgt_id = (b, a) if direction == "downstream_to_upstream" else (a, b)
                    links.append((src_id, tgt_id, kind, f"relationship {r.get('id')}"))
                if len(data) < rel_size or not data:
                    break
                new_last = data[-1].get("id")
                if not isinstance(new_last, int) or (last_id is not None and new_last <= last_id):
                    raise ConnectError("the relationships paging is not advancing (lastId did not increase)")
                last_id = new_last
            else:
                raise ConnectError("stopped after max_pages")
            notes.append(f"{n_rel} relationships read ({suspect} marked suspect: the upstream item changed after the link was last reviewed)")
        elif peek:
            notes.append("relationships were not read in a peek")
        else:
            notes.append("relationships=false: no links were read")

        notes.insert(0, f"read {len(rows)} items" + (f" of {len(raw_items)} in the project" if keep else "") + f" via /{path}")
        if reported_total is not None and not peek and reported_total != len(raw_items) + dup:
            notes.append(f"WARNING the server reported totalResults {reported_total} but {len(raw_items) + dup} came back; compare before trusting this read")
        if dup:
            notes.append(f"{dup} items came back twice and were kept once")
        if unmapped:
            notes.append("relationship types not in link_map, kept under their own name: " + ", ".join(f"{n} x{c}" for n, c in unmapped.most_common(8)))
        rev = hashlib.sha1(json.dumps([[r["id"], r["fields"].get("modifiedDate", "")] for r in rows]).encode()).hexdigest()[:16]
        out = {"rows": rows, "links": links, "notes": notes, "rev": rev, "base": base}
        self._cache[key] = out
        return out

    @staticmethod
    def _option_name(http: ReadOnlyHttp, rest: str, value: Any, cache: dict[str, str], notes: list[str]) -> Any:
        vid = str(value)
        if not vid.isdigit():
            return value
        if vid not in cache:
            try:
                body = http.get_json(f"{rest}/picklistoptions/{vid}")
                cache[vid] = plain(((body or {}).get("data") or {}).get("name")) or vid
            except ConnectError as e:
                if e.status == 401:
                    raise
                cache[vid] = vid
                if not any(n.startswith("pick list option") for n in notes):
                    notes.append(f"pick list option {vid} could not be looked up ({str(e)[:80]}); the ids stay as they are")
        return cache[vid]

    # ---- the Adapter contract --------------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        d = self._load(src)
        by: dict[str, list[dict[str, Any]]] = {}
        for r in d["rows"]:
            by.setdefault(str(r["fields"].get("itemType") or "(no type)"), []).append(r["fields"])
        cs = []
        for t, rows in sorted(by.items()):
            names = sorted({k for r in rows for k in r})
            cs.append(Container(t, len(rows), [make_field_info(k, [r.get(k, "") for r in rows]) for k in names]))
        return Discovery(cs, list(d["notes"]) + ["rich text fields (description) are HTML: use strip_markup"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        d = self._load(src)
        for n, r in enumerate(d["rows"]):
            yield RawRecord(native_id=r["id"], fields=r["fields"], order=n, parent_native_id=r["parent"],
                            ref=SourceRef("jama", d["base"], container=str(r["fields"].get("itemType") or "item"), locator=r["fields"].get("documentKey") or r["id"], revision=d["rev"]))
        for a, b, kind, via in d["links"]:
            yield RawLink(a, b, kind, SourceRef("jama", d["base"], container="links", locator=via, revision=d["rev"]))

    def revision(self, src: Source) -> str:
        return self._load(src)["rev"]
