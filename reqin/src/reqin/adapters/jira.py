"""Jira (Atlassian Cloud and Data Center / Server): issues as requirement-like records, over the REST API.

READ-ONLY. Only GET requests are made. If you can only get a CSV out of Jira, mind what it loses: the CSV export has the OUTWARD end of a link but not the
inward end (Atlassian's own tracker), and one column per link type, so use this connector or the JSON from the API when links matter.

URI:      jira+https://your-site.atlassian.net            Cloud
          jira+https://host/jira                          Data Center or Server (the part before /rest/api; keep a context path if there is one)
Options:  jql             REQUIRED. What to read, e.g. jql='project = ABC AND issuetype = Requirement ORDER BY key'. There is no "read everything": a Jira
                          instance can hold millions of issues, so the choice is yours. Put an ORDER BY in it (a note says so when it is missing).
          flavor          cloud | dc. Default: cloud when the host ends in .atlassian.net, else dc.
          api_version     2 or 3. Default 3 on cloud, 2 on dc. Version 3 returns descriptions as Atlassian Document Format (a JSON tree): this connector flattens
                          it to plain text. Version 2 returns the description as the wiki markup a person typed, which is kept AS WRITTEN (not converted).
          fields          comma list. Default summary,description,status,issuetype,priority,labels,project,parent,issuelinks,created,updated,resolution.
                          issuelinks and the parent field are always added, because links and hierarchy come from them.
          field_names     JSON {"customfield_10042": "Verification method"}: the name the field gets in the records. Without it a custom field keeps its id.
          resolve_field_names  true: GET /rest/api/<v>/field first and use every field's name. field_names wins where both name a field. If that call fails
                          the read goes on with ids and a note says so.
          parent_field    the field that holds the parent issue, default parent (a sub-task's parent, or a team-managed project's epic). A classic project's
                          "Epic Link" is a custom field (customfield_NNNNN) holding the epic's KEY: name it here.
          link_map        JSON {"Implements": "satisfy", "Blocks": {"kind": "trace", "source": "inward"}}: what each link TYPE (by name) becomes. A bare string
                          is the kind, with the OUTWARD issue as the source. "source": "inward" reverses it. A link type that is not listed keeps its own name
                          lowercased as the kind, outward as the source, and `discover` says which ones were unmapped. Jira does not interpret direction, so
                          this is YOUR decision per link type: see the note below.
          page_size       default 100 (maxResults)
          peek / max_pages  stop early for a trial run
          token_env       Data Center: a personal access token (sent as Authorization: Bearer)
          basic_user_env + basic_password_env   Cloud: the account's e-mail and an API token (Basic), as Atlassian's own examples show
          cookie_env | auth_hook | ca_bundle | user_agent | max_wait     see connect.auth_from_options and make_http

DIRECTION. A link entry on issue X has a type with an `inward` and an `outward` phrase, and EITHER an `outwardIssue` or an `inwardIssue` (the other end). X with
an outwardIssue Y reads "X <outward phrase> Y" (X blocks Y). X with an inwardIssue Y reads "X <inward phrase> Y" (X is blocked by Y), which is the same link as
"Y blocks X". The same link therefore shows up on both issues when both are in the result. This reader turns every entry into (the issue that carries the OUTWARD
phrase, the issue that carries the inward phrase), de-duplicates, and then applies link_map. For a type like "Implements" (outward: implements) the outward
issue is the one that implements, so "satisfy" with the default source is right: the source of a satisfy link is the design, the target the requirement.

WHAT IS VERIFIED AND WHAT IS NOT:
  from the vendor's documentation  Cloud: GET /rest/api/3/search/jql with `jql` and `nextPageToken` (the old /rest/api/3/search is removed); no `total`; a page
                                   must finish before the next. Data Center: GET /rest/api/2/search with startAt, maxResults (default 50), response startAt,
                                   maxResults, total, issues[]; a search window of 10,000 (HTTP 500 beyond it). Link entries as above. Data Center personal access
                                   tokens are sent as Bearer; Cloud examples use e-mail and API token as Basic. A 429 or 5xx carries Retry-After (the kit honours it).
                                   Atlassian's API-token rate limits apply from 22 November 2025.
  NOT seen live                    anything. Not read: whether the Cloud search response has `isLast` (recalled: when a reply says `isLast: true` the read stops there
                                   even if it still hands out a token, and when the field is absent the read ends when the token runs out), the default field
                                   list and the maximum maxResults on search/jql, the /field endpoint (recalled: a list of {id, name}), and which REST version
                                   returns ADF where (we handle both a JSON tree and a string, whatever the version).
  Tested only against an in-memory fake (tests/live_cases_more.py: jira_server) that follows the documented shapes above.
  An issue that is moved to another project gets a new KEY: a record keeps the key it had when it was read, so a move looks like one issue leaving and one arriving.
  First run: reqin sample jira+https://site.atlassian.net --opt jql='project = ABC' --opt basic_user_env=JIRA_USER --opt basic_password_env=JIRA_TOKEN
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
from ._values import adf_text, plain  # noqa: F401  (re-exported: tests and users import them from here)

DEFAULT_FIELDS = ["summary", "description", "status", "issuetype", "priority", "labels", "project", "parent", "issuelinks", "created", "updated", "resolution"]
WINDOW = 10_000        # Data Center / Server search window the vendor documents; HTTP 500 beyond it


@register
class JiraAdapter(Adapter):
    name = "jira"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=True, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, dict[str, Any]] = {}

    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("jira+http://", "jira+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and "/rest/api/" in u:
            return 0.8
        return 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    @staticmethod
    def _base(src: Source) -> str:
        return src.uri.removeprefix("jira+").split("/rest/api")[0].rstrip("/")

    # ---- options -------------------------------------------------------------------------------------
    @staticmethod
    def _link_map(o) -> dict[str, tuple[str, str]]:  # noqa: ANN001
        out: dict[str, tuple[str, str]] = {}
        for name, spec in opt_dict(o, "link_map").items():
            if isinstance(spec, str):
                out[str(name)] = (spec, "outward")
            elif isinstance(spec, dict) and spec.get("kind"):
                side = str(spec.get("source", "outward"))
                if side not in ("outward", "inward"):
                    raise ConnectError(f"link_map {name!r}: source must be outward or inward, got {side!r}")
                out[str(name)] = (str(spec["kind"]), side)
            else:
                raise ConnectError(f"link_map {name!r} must be a kind (a string) or {{\"kind\": ..., \"source\": \"outward\"|\"inward\"}}")
        return out

    # ---- the read, once per run, cached ----------------------------------------------------------------
    def _load(self, src: Source) -> dict[str, Any]:
        o = src.options
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in o.items() if a not in ("token", "token_env", "cookie_env", "basic_password_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        jql = str(o.get("jql") or "").strip()
        if not jql:
            raise ConnectError("option 'jql' is required: say what to read, e.g. jql='project = ABC AND issuetype = Requirement ORDER BY key'")
        base = self._base(src)
        host = base.split("//", 1)[-1].split("/", 1)[0].split(":")[0].lower()
        flavor = str(o.get("flavor") or ("cloud" if host.endswith(".atlassian.net") else "dc")).lower()
        if flavor not in ("cloud", "dc"):
            raise ConnectError(f"option 'flavor' must be cloud or dc, got {flavor!r}")
        ver = str(o.get("api_version") or ("3" if flavor == "cloud" else "2"))
        if ver not in ("2", "3"):
            raise ConnectError(f"option 'api_version' must be 2 or 3, got {ver!r}")
        self._http = http = make_http(o, self._transport, base_headers={"Accept": "application/json"})
        size = opt_int(o, "page_size", 100)
        parent_field = str(o.get("parent_field") or "parent")
        fields = opt_list(o, "fields", DEFAULT_FIELDS)
        for needed in ("issuelinks", parent_field):
            if needed not in fields:
                fields.append(needed)
        names = {str(k): str(v) for k, v in opt_dict(o, "field_names").items()}
        link_map = self._link_map(o)
        notes: list[str] = []
        if not re.search(r"\border\s+by\b", jql, re.I):
            notes.append("the JQL has no ORDER BY: Jira picks the order, and a project that changes while it is read can show an issue twice or skip one")
        if str(o.get("resolve_field_names") or "").lower() in ("1", "true", "yes"):
            try:
                listed = http.get_json(f"{base}/rest/api/{ver}/field")
                from_server = {str(f["id"]): str(f["name"]) for f in listed if isinstance(f, dict) and f.get("id") and f.get("name")}
                names = {**from_server, **names}
                notes.append(f"{len(from_server)} field names read from /field")
            except (ConnectError, TypeError, KeyError, ValueError) as e:
                if isinstance(e, ConnectError) and e.status == 401:
                    raise                                    # the credentials are rejected: not something to carry on past
                notes.append(f"field names could not be read from /field ({str(e)[:80]}); custom fields keep their ids")

        rows: list[dict[str, Any]] = []
        links: list[tuple[str, str, str, str]] = []
        seen: set[str] = set()
        unmapped: Counter[str] = Counter()
        skipped: Counter[str] = Counter()
        dup = 0
        reported_total: int | None = None
        token: str | None = None
        start = 0
        tokens_seen: set[str] = set()
        peek = opt_int(o, "peek", 0)
        for page_no in range(1, opt_int(o, "max_pages", 1_000_000) + 1):
            params: dict[str, Any] = {"jql": jql, "fields": ",".join(fields), "maxResults": size}
            if flavor == "cloud":
                url = f"{base}/rest/api/{ver}/search/jql"
                if token:
                    params["nextPageToken"] = token
            else:
                url = f"{base}/rest/api/{ver}/search"
                params["startAt"] = start
            body = http.get_json(url, params)
            if not isinstance(body, dict) or not isinstance(body.get("issues"), list):
                raise ConnectError(f"{http.safe_url(url)} did not return the search shape (an object with an 'issues' list): is this a Jira REST endpoint, and is the JQL valid?")
            issues = body["issues"]
            if flavor == "dc":
                tot = body.get("total")
                reported_total = tot if isinstance(tot, int) else reported_total
                if page_no == 1 and isinstance(tot, int) and tot > WINDOW:
                    raise ConnectError(f"the JQL matches {tot} issues; Jira's search window is {WINDOW} (the server answers HTTP 500 beyond it). "
                                       "Narrow the JQL (a project, an issue type, or an `updated` date range) and read in parts")
            for it in issues:
                k = str(it.get("key") or "")
                if not k:
                    continue
                if k in seen:
                    dup += 1
                    continue
                seen.add(k)
                f = it.get("fields") or {}
                rec: dict[str, Any] = {"key": k, "id": str(it.get("id", ""))}
                for fname, val in f.items():
                    if fname == "issuelinks":
                        continue
                    if fname == "project" and isinstance(val, dict):
                        rec["project"] = plain(val.get("key"))
                        rec["project_name"] = plain(val.get("name"))
                        continue
                    sk: Counter = Counter()
                    rec[names.get(fname, fname)] = plain(val, sk)
                    skipped.update(sk)
                rec["issuetype"] = rec.get("issuetype", "")
                parent = plain(f.get(parent_field))
                rows.append({"key": k, "fields": rec, "parent": parent or None})
                for entry in f.get("issuelinks") or []:
                    t = entry.get("type") or {}
                    tname = str(t.get("name", ""))
                    if isinstance(entry.get("outwardIssue"), dict):
                        out_end, in_end = k, str(entry["outwardIssue"].get("key") or "")
                    elif isinstance(entry.get("inwardIssue"), dict):
                        out_end, in_end = str(entry["inwardIssue"].get("key") or ""), k
                    else:
                        continue
                    if not out_end or not in_end:
                        continue
                    if tname in link_map:
                        kind, side = link_map[tname]
                    else:
                        kind, side = (tname.lower() or "link"), "outward"
                        unmapped[tname] += 1
                    a, b = (out_end, in_end) if side == "outward" else (in_end, out_end)
                    links.append((a, b, kind, f"{tname}:{out_end}>{in_end}"))
            if flavor == "cloud":
                nxt = body.get("nextPageToken") or None
                if not issues or not nxt or body.get("isLast") is True:
                    break
                if nxt in tokens_seen or nxt == token:
                    raise ConnectError("the server returned a nextPageToken it had already given: its paging is not advancing")
                tokens_seen.add(nxt)
                token = str(nxt)
            else:
                start += len(issues)
                if not issues or (isinstance(reported_total, int) and start >= reported_total):
                    break
                if reported_total is None and len(issues) < size:
                    break
            if peek and page_no >= peek:
                notes.append(f"[PEEK: first {peek} page(s) only, so counts and links are incomplete]")
                break
        else:
            raise ConnectError("stopped after max_pages")
        # one link seen from both of its issues is one link
        uniq, seen_l = [], set()
        for l in links:
            if (l[0], l[1], l[2]) not in seen_l:
                seen_l.add((l[0], l[1], l[2]))
                uniq.append(l)
        notes.append(f"read {len(rows)} issues via {'search/jql (token paging, no total)' if flavor == 'cloud' else 'search (startAt/total)'}; {len(uniq)} links after de-duplication")
        if flavor == "cloud":
            notes.append("this endpoint reports no total, so there is no count to check the read against")
        elif reported_total is not None and not peek and reported_total != len(rows) + dup:
            notes.append(f"WARNING the server reported a total of {reported_total} but {len(rows) + dup} came back; compare before trusting this read")
        if dup:
            notes.append(f"{dup} issues came back twice (the project changed while it was read?) and were kept once")
        if unmapped:
            notes.append("link types not in link_map, kept under their own name with the outward issue as source: "
                         + ", ".join(f"{n or '(no name)'} x{c}" for n, c in unmapped.most_common(8)))
        if skipped:
            notes.append("description parts with no text were skipped: " + ", ".join(f"{n} x{c}" for n, c in skipped.most_common(6)))
        keys = {r["key"] for r in rows}
        for r in rows:
            if r["parent"] and r["parent"] not in keys:
                notes.append(f"{r['key']}: its parent {r['parent']} is not in this result (kept as written)")
                break
        rev = hashlib.sha1(json.dumps([[r["key"], r["fields"].get("updated", "")] for r in rows]).encode()).hexdigest()[:16]
        out = {"rows": rows, "links": uniq, "notes": notes, "rev": rev, "base": base}
        self._cache[key] = out
        return out

    # ---- the Adapter contract --------------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        d = self._load(src)
        by: dict[str, list[dict[str, Any]]] = {}
        for r in d["rows"]:
            by.setdefault(r["fields"].get("issuetype") or "(no type)", []).append(r["fields"])
        cs = []
        for t, rows in sorted(by.items()):
            names = sorted({k for r in rows for k in r})
            cs.append(Container(t, len(rows), [make_field_info(k, [r.get(k, "") for r in rows]) for k in names]))
        return Discovery(cs, list(d["notes"]) + ["description is plain text when api_version is 3 (flattened) and the author's wiki markup when it is 2"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        d = self._load(src)
        for i, r in enumerate(d["rows"]):
            yield RawRecord(native_id=r["key"], fields=r["fields"], order=i, parent_native_id=r["parent"],
                            ref=SourceRef("jira", d["base"], container=r["fields"].get("issuetype") or "issue", locator=r["key"], revision=d["rev"]))
        for a, b, kind, via in d["links"]:
            yield RawLink(a, b, kind, SourceRef("jira", d["base"], container="links", locator=via, revision=d["rev"]))

    def revision(self, src: Source) -> str:
        return self._load(src)["rev"]
