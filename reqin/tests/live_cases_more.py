"""In-memory fakes of Jira, Polarion and Jama, written from the documented shapes (see each adapter's docstring). Everything is made up.
They are as strict as the documentation lets them be: an unknown parameter value, a wrong header or a malformed token is an error, not a shrug."""
from __future__ import annotations

import base64
import json
import re
from typing import Any

from reqin.connect import Response
from reqin.testing import FakeTransport, Req, json_response, text_response

# =====================================================================================================================
# Jira
# =====================================================================================================================
JIRA_CLOUD = "https://fictional-widgets.atlassian.net"
JIRA_DC = "https://jira.example.test/jira"
JIRA_USER, JIRA_TOKEN, JIRA_PAT = "dev@example.test", "api-token-cloud-1", "pat-token-dc-1"


def adf(*blocks: dict) -> dict:
    return {"version": 1, "type": "doc", "content": list(blocks)}


def para(*inline: dict) -> dict:
    return {"type": "paragraph", "content": list(inline)}


def txt(s: str) -> dict:
    return {"type": "text", "text": s}


def bullets(*items: str) -> dict:
    return {"type": "bulletList", "content": [{"type": "listItem", "content": [para(txt(i))]} for i in items]}


# key, id, type, summary, description (ADF dict, wiki string for v2, or None), parent, custom field value, links: [(type name, "out"|"in", other key)]
JIRA_ISSUES: list[dict[str, Any]] = [
    {"key": "WID-1", "id": "10001", "type": "Requirement", "summary": "Response time", "parent": None, "cf": "Test",
     "adf": adf(para(txt("The controller shall respond to a command within 50 ms."))),
     "wiki": "The controller shall respond to a command within 50 ms.",
     "links": [("Implements", "in", "WID-10"), ("Duplicate", "in", "WID-5")]},
    {"key": "WID-2", "id": "10002", "type": "Requirement", "summary": "Fault log", "parent": "WID-1", "cf": "Inspection",
     "adf": adf(para(txt("The controller shall log:")), bullets("every fault", "every restart")),
     "wiki": "The controller shall log:\n* every fault\n* every restart", "links": []},
    {"key": "WID-3", "id": "10003", "type": "Requirement", "summary": "Reboot", "parent": None, "cf": "Test",
     "adf": adf(para(txt("The controller shall restart"), {"type": "hardBreak"}, txt("within 30 seconds, as "), {"type": "mention", "attrs": {"id": "u1", "text": "@Ada"}},
                     txt(" asked.")),
                {"type": "mediaSingle", "content": [{"type": "media", "attrs": {"id": "m1", "type": "file"}}]}),
     "wiki": "The controller shall restart\nwithin 30 seconds, as [~ada] asked.", "links": []},
    {"key": "WID-4", "id": "10004", "type": "Requirement", "summary": "A requirement with no description", "parent": None, "cf": None, "adf": None, "wiki": None, "links": []},
    {"key": "WID-5", "id": "10005", "type": "Requirement", "summary": "Response time again", "parent": None, "cf": "Test",
     "adf": adf(para(txt("The controller shall answer a command inside 50 ms."))),
     "wiki": "The controller shall answer a command inside 50 ms.", "links": [("Duplicate", "out", "WID-1")]},
    {"key": "WID-10", "id": "10010", "type": "Story", "summary": "Implement response time", "parent": None, "cf": None,
     "adf": adf(para(txt("Build the fast path."))), "wiki": "Build the fast path.",
     "links": [("Implements", "out", "WID-1"), ("Blocks", "out", "OTHER-7")]},
    {"key": "WID-11", "id": "10011", "type": "Epic", "summary": "Controller", "parent": None, "cf": None,
     "adf": adf(para(txt("All controller work."))), "wiki": "All controller work.", "links": []},
]
JIRA_REQS = [i for i in JIRA_ISSUES if i["type"] == "Requirement"]
JIRA_GOLD = {   # what the text of each requirement must be after the reader, with the shipped profile
    "WID-1": "The controller shall respond to a command within 50 ms.",
    "WID-2": "The controller shall log:\n- every fault\n- every restart",
    "WID-3": "The controller shall restart\nwithin 30 seconds, as @Ada asked.",
    "WID-4": "A requirement with no description",              # the summary is the fallback
    "WID-5": "The controller shall answer a command inside 50 ms.",
}
LINK_TYPES = {"Implements": ("is implemented by", "implements"), "Duplicate": ("is duplicated by", "duplicates"), "Blocks": ("is blocked by", "blocks")}


def _jira_issue(i: dict, wanted: set[str] | None, v3: bool) -> dict:
    allf = {"summary": i["summary"], "issuetype": {"name": i["type"], "id": "1"}, "status": {"name": "Open", "id": "3"},
            "priority": {"name": "Medium"}, "labels": ["safety"] if i["key"] == "WID-1" else [],
            "project": {"key": "WID", "name": "Fictional Widget"}, "created": "2026-01-01T00:00:00.000+0000", "updated": f"2026-02-0{i['id'][-1]}T00:00:00.000+0000",
            "resolution": None, "description": (i["adf"] if v3 else i["wiki"]),
            "parent": {"key": i["parent"], "id": "1"} if i["parent"] else None,
            "customfield_10042": {"value": i["cf"], "id": "5"} if i["cf"] else None,
            "issuelinks": [{"id": "9", "type": {"name": n, "inward": LINK_TYPES[n][0], "outward": LINK_TYPES[n][1]},
                            ("outwardIssue" if side == "out" else "inwardIssue"): {"key": other, "id": "1"}} for n, side, other in i["links"]]}
    keep = allf if wanted is None else {k: v for k, v in allf.items() if k in wanted}
    return {"expand": "", "id": i["id"], "self": "https://x/rest/api/issue/" + i["id"], "key": i["key"], "fields": keep}


def _jql(jql: str, issues: list[dict]) -> list[dict] | None:
    """The only JQL the fake understands: project = X, issuetype = Y / in (...), joined by AND, then an optional ORDER BY key. Anything else is None (HTTP 400)."""
    m = re.split(r"(?i)\border\s+by\b", jql)
    body = m[0].strip()
    order = m[1].strip().lower() if len(m) > 1 else ""
    out = list(issues)
    for term in [t.strip() for t in re.split(r"(?i)\band\b", body) if t.strip()]:
        pm = re.fullmatch(r'(?i)project\s*=\s*"?(\w+)"?', term)
        tm = re.fullmatch(r'(?i)issuetype\s*=\s*"?([\w ]+?)"?', term)
        im = re.fullmatch(r"(?i)issuetype\s+in\s*\(([^)]*)\)", term)
        if pm:
            out = [i for i in out if i["key"].split("-")[0] == pm.group(1)]
        elif tm:
            out = [i for i in out if i["type"] == tm.group(1)]
        elif im:
            want = {x.strip().strip('"') for x in im.group(1).split(",")}
            out = [i for i in out if i["type"] in want]
        else:
            return None
    if order.startswith("key"):
        out.sort(key=lambda i: int(i["key"].split("-")[1]), reverse=order.endswith("desc"))
    return out


def jira_server(flavor: str = "cloud", issues=None, repeat_token: bool = False, fixed_total: int | None = None, no_auth_check: bool = False,
                fields_list: list[dict] | None = None, fail_fields: bool = False, repeat_issue_on_page2: bool = False) -> FakeTransport:
    issues = JIRA_ISSUES if issues is None else issues
    t = FakeTransport()
    base = JIRA_CLOUD if flavor == "cloud" else JIRA_DC
    v = "3" if flavor == "cloud" else "2"

    def authed(req: Req) -> Response | None:
        if no_auth_check:
            return None
        want = ("Basic " + base64.b64encode(f"{JIRA_USER}:{JIRA_TOKEN}".encode()).decode()) if flavor == "cloud" else f"Bearer {JIRA_PAT}"
        if req.headers.get("Authorization") != want:
            return text_response("Unauthorized", status=401)
        return None

    def search(req: Req):
        bad = authed(req)
        if bad:
            return bad
        sel = _jql(req.query.get("jql", ""), issues)
        if sel is None:
            return json_response({"errorMessages": ["Error in the JQL Query: the fake understands project, issuetype and ORDER BY key only"], "errors": {}}, status=400)
        wanted = {f for f in req.query.get("fields", "").split(",") if f} or None
        n = min(int(req.query.get("maxResults", 50)), 100)
        if flavor == "cloud":
            tok = req.query.get("nextPageToken")
            if tok is None:
                off = 0
            else:
                try:
                    off = int(base64.b64decode(tok).decode().split(":")[1])
                except Exception:  # noqa: BLE001
                    return json_response({"errorMessages": ["Invalid nextPageToken"]}, status=400)
            chunk = sel[off:off + n]
            body: dict[str, Any] = {"issues": [_jira_issue(i, wanted, True) for i in chunk]}
            if repeat_issue_on_page2 and off > 0 and chunk:
                body["issues"].append(_jira_issue(sel[0], wanted, True))
            if off + n < len(sel):
                body["nextPageToken"] = base64.b64encode(f"off:{off + n}".encode()).decode()
            if repeat_token:
                body["nextPageToken"] = base64.b64encode(b"off:0").decode() if off else body.get("nextPageToken", "")
            return json_response(body)
        start = int(req.query.get("startAt", 0))
        chunk = sel[start:start + n]
        return json_response({"expand": "schema,names", "startAt": start, "maxResults": n, "total": fixed_total if fixed_total is not None else len(sel),
                              "issues": [_jira_issue(i, wanted, False) for i in chunk]})
    t.add(f"{urlpath(base)}/rest/api/{v}/search/jql" if flavor == "cloud" else f"{urlpath(base)}/rest/api/{v}/search", search)

    def field(req: Req):
        bad = authed(req)
        if bad:
            return bad
        if fail_fields:
            return text_response("nope", status=403)
        return json_response(fields_list if fields_list is not None else [{"id": "summary", "name": "Summary"}, {"id": "customfield_10042", "name": "Verification method"}])
    t.add(f"{urlpath(base)}/rest/api/{v}/field", field)
    return t


def urlpath(base: str) -> str:
    return re.sub(r"^https?://[^/]+", "", base)


# =====================================================================================================================
# Polarion REST (JSON:API)
# =====================================================================================================================
POLARION_BASE = "https://alm.example.test/polarion"
POLARION_PAT = "pat-polarion-1"
# short id, type, title, description (type, value) or None, links: [(role, target resource id)]
POLARION_ITEMS: list[dict[str, Any]] = [
    {"id": "WI-1", "type": "requirement", "title": "Response time", "status": "open", "desc": ("text/html", "<p>The controller shall respond to a command within 50 ms.</p>"),
     "links": [("relates_to", "WIDGET/WI-2")]},
    {"id": "WI-2", "type": "requirement", "title": "Fault log", "status": "open", "desc": ("text/html", "<div>The controller shall log every <b>fault</b>.</div>"),
     "links": [("parent", "WIDGET/WI-1")]},
    {"id": "WI-3", "type": "requirement", "title": "Reboot", "status": "draft", "desc": ("text/plain", "The controller shall restart within 30 seconds."), "links": []},
    {"id": "WI-4", "type": "testcase", "title": "Check the reboot", "status": "open", "desc": ("text/plain", "Cut the power and time the restart."),
     "links": [("tests", "WIDGET/WI-3")]},
    {"id": "WI-5", "type": "requirement", "title": "A requirement with no description", "status": "open", "desc": None, "links": []},
    {"id": "WI-6", "type": "requirement", "title": "Mass", "status": "open", "desc": ("text/html", "<p>The unit shall weigh no more than 12 kg.</p>"),
     "links": [("relates_to", "OTHERPROJ/WI-9")]},
    {"id": "WI-7", "type": "heading", "title": "Mechanical", "status": "open", "desc": None, "links": []},
]
POLARION_REQS = [i for i in POLARION_ITEMS if i["type"] == "requirement"]
POLARION_GOLD = {"WI-1": "The controller shall respond to a command within 50 ms.", "WI-2": "The controller shall log every fault.",
                 "WI-3": "The controller shall restart within 30 seconds.", "WI-5": "A requirement with no description",
                 "WI-6": "The unit shall weigh no more than 12 kg."}


def _pol_item(i: dict, project: str, wanted: set[str] | None) -> dict:
    attrs: dict[str, Any] = {"id": i["id"], "type": i["type"], "title": i["title"], "status": i["status"], "updated": f"2026-03-0{len(i['id'])}T00:00:00Z",
                             "outlineNumber": i["id"][3:]}
    if i["desc"]:
        attrs["description"] = {"type": i["desc"][0], "value": i["desc"][1]}
    if wanted is not None:
        attrs = {k: v for k, v in attrs.items() if k in wanted}
    rel = {"linkedWorkItems": {"data": [{"type": "linkedworkitems", "id": f"{project}/{i['id']}/{role}/{tgt}"} for role, tgt in i["links"]]}} if i["links"] else {}
    return {"type": "workitems", "id": f"{project}/{i['id']}", "attributes": attrs, **({"relationships": rel} if rel else {})}


def _pol_query(q: str, items: list[dict]) -> list[dict] | None:
    out = list(items)
    for term in [t.strip() for t in re.split(r"(?i)\band\b|\s+", q) if t.strip() and t.strip().lower() != "and"]:
        m = re.fullmatch(r"(type|status):(\w+)", term)
        if not m:
            return None
        out = [i for i in out if i[m.group(1)] == m.group(2)]
    return out


def polarion_server(items=None, project: str = "WIDGET", with_links_object: bool = True, relative_next: bool = False, drop_total: bool = False,
                    report_total: int | None = None, no_included: bool = False, ignore_page_number: bool = False, foreign_next: bool = False,
                    loop_next: bool = False, rest_disabled: bool = False) -> FakeTransport:
    items = POLARION_ITEMS if items is None else items
    t = FakeTransport()
    root = urlpath(POLARION_BASE) + "/rest/v1"

    def workitems(req: Req):
        if req.headers.get("Authorization") != f"Bearer {POLARION_PAT}":
            return json_response({"errors": [{"status": "401", "title": "Unauthorized"}]}, status=401)
        sel = _pol_query(req.query.get("query", ""), items)
        if sel is None:
            return json_response({"errors": [{"status": "400", "title": "Bad query", "detail": "the fake understands type:x and status:y joined by AND"}]}, status=400)
        sort = req.query.get("sort")
        if sort:
            sel = sorted(sel, key=lambda i: (int(i["id"][3:])), reverse=sort.startswith("-"))
        else:
            sel = list(reversed(sel))                       # "no default sorting": any order is allowed, and this one is not the sorted one
        size = int(req.query.get("page[size]", 100))
        num = 1 if ignore_page_number else int(req.query.get("page[number]", 1))
        chunk = sel[(num - 1) * size: num * size]
        wanted_s = req.query.get("fields[workitems]", "@all")
        wanted = None if wanted_s == "@all" else set(wanted_s.split(","))
        body: dict[str, Any] = {"data": [_pol_item(i, project, wanted) for i in chunk]}
        if not drop_total:
            body["meta"] = {"totalCount": report_total if report_total is not None else len(sel)}
        if with_links_object:
            links: dict[str, str] = {"self": req.url}
            if num * size < len(sel) or loop_next:
                nxt = re.sub(r"page%5Bnumber%5D=\d+|page\[number\]=\d+", f"page%5Bnumber%5D={num + 1}", req.url)
                if "page%5Bnumber%5D" not in nxt:
                    nxt += ("&" if "?" in nxt else "?") + f"page%5Bnumber%5D={num + 1}"
                if loop_next and num >= 2:
                    nxt = req.url                                   # page 2 says its own address is the next page
                if foreign_next:
                    nxt = nxt.replace("alm.example.test", "elsewhere.example.test")
                if relative_next:
                    nxt = re.sub(r"^https?://[^/]+", "", nxt)
                links["next"] = nxt
            body["links"] = links
        if req.query.get("include") == "linkedWorkItems" and not no_included:
            body["included"] = [{"type": "linkedworkitems", "id": f"{project}/{i['id']}/{role}/{tgt}", "attributes": {"role": role, "suspect": False},
                                 "relationships": {"workItem": {"data": {"type": "workitems", "id": tgt}}}} for i in chunk for role, tgt in i["links"]]
        return json_response(body)
    if rest_disabled:
        return t                                            # no route at all: every request is a 404, as on a server with the REST API off
    t.add(f"{root}/projects/{project}/workitems", workitems)
    return t


# =====================================================================================================================
# Jama Connect REST
# =====================================================================================================================
JAMA_BASE = "https://widgets.jamacloud.example.test"
JAMA_TOKEN = "jama-bearer-token-1"
JAMA_TYPES = [{"id": 27, "display": "Requirement", "typeKey": "REQ"}, {"id": 28, "display": "Test Case", "typeKey": "TC"}, {"id": 29, "display": "Folder", "typeKey": "FLD"}]
JAMA_REL_TYPES = [{"id": 4, "name": "Verification"}, {"id": 5, "name": "Derived"}, {"id": 6, "name": "Related to"}]
JAMA_PICKS = {12: "Approved", 13: "Draft"}
JAMA_ITEMS: list[dict[str, Any]] = [
    {"id": 100, "documentKey": "WID-FLD-1", "itemType": 29, "fields": {"name$29": "Controller requirements"}, "parent": None},
    {"id": 101, "documentKey": "WID-REQ-1", "itemType": 27, "parent": 100,
     "fields": {"name$27": "Response time", "description$27": "<p>The controller shall respond to a command within 50 ms.</p>", "status$27": 12}},
    {"id": 102, "documentKey": "WID-REQ-2", "itemType": 27, "parent": 101,
     "fields": {"name$27": "Fault log", "description$27": "<p>The controller shall log <b>every</b> fault.</p>", "status$27": 13}},
    {"id": 103, "documentKey": "WID-REQ-3", "itemType": 27, "parent": 100,
     "fields": {"name$27": "Reboot", "description$27": "The controller shall restart within 30 seconds.", "status$27": 12}},
    {"id": 104, "documentKey": "WID-REQ-4", "itemType": 27, "parent": 100, "fields": {"name$27": "A requirement with no text", "description$27": "", "status$27": 13}},
    {"id": 105, "documentKey": "WID-REQ-5", "itemType": 27, "parent": 100,
     "fields": {"name$27": "Mass", "description$27": "<p>The unit shall weigh no more than 12 kg.</p>", "status$27": 12}},
    {"id": 201, "documentKey": "WID-TC-1", "itemType": 28, "parent": 100,
     "fields": {"name$28": "Check response", "description$28": "<p>Send a command and time the answer.</p>"}},
]
JAMA_REQ_COUNT = 5
JAMA_GOLD = {"WID-REQ-1": "The controller shall respond to a command within 50 ms.", "WID-REQ-2": "The controller shall log every fault.",
             "WID-REQ-3": "The controller shall restart within 30 seconds.", "WID-REQ-4": "A requirement with no text", "WID-REQ-5": "The unit shall weigh no more than 12 kg."}
# id, fromItem (upstream), toItem (downstream), relationship type id, suspect
JAMA_RELS = [(1, 101, 201, 4, False), (2, 101, 102, 5, False), (3, 103, 999, 6, True)]


def jama_server(items=None, rels=None, auth: str = "bearer", ignore_start_at: bool = False, drop_page_info: bool = False, report_total: int | None = None,
                no_rel_types: bool = False, rels_stuck: bool = False, picks=None, fail_picks: bool = False) -> FakeTransport:
    items = JAMA_ITEMS if items is None else items
    rels = JAMA_RELS if rels is None else rels
    t = FakeTransport()
    root = urlpath(JAMA_BASE) + "/rest/v1"

    def guard(fn):
        def h(req: Req):
            want = f"Bearer {JAMA_TOKEN}" if auth == "bearer" else "Basic " + base64.b64encode(b"jama-user:jama-pass").decode()
            if req.headers.get("Authorization") != want:
                return json_response({"meta": {"status": "Unauthorized"}}, status=401)
            return fn(req)
        return h

    def listing(req: Req, rows: list[dict], limit: int = 50):
        n = int(req.query.get("maxResults", 20))
        if not 1 <= n <= limit:
            return json_response({"meta": {"status": "Bad Request", "message": f"maxResults must be between 1 and {limit}"}}, status=400)
        start = 0 if ignore_start_at else int(req.query.get("startAt", 0))
        chunk = rows[start:start + n]
        info: dict[str, Any] = {"startIndex": start, "resultCount": len(chunk), "totalResults": report_total if report_total is not None else len(rows)}
        meta: dict[str, Any] = {"status": "OK"}
        if not drop_page_info:
            meta["pageInfo"] = info
        return json_response({"meta": meta, "data": chunk})

    def projects(req: Req):
        return listing(req, [{"id": 5, "fields": {"name": "Fictional Widget", "projectKey": "WID"}}, {"id": 6, "fields": {"name": "Another Fictional", "projectKey": "ANO"}}])
    t.add(f"{root}/projects", guard(projects))
    t.add(f"{root}/itemtypes", guard(lambda r: listing(r, JAMA_TYPES)))

    def abstractitems(req: Req):
        if req.query.get("project") != "5":
            return json_response({"meta": {"status": "Not Found"}}, status=404)
        rows = [{"id": i["id"], "documentKey": i["documentKey"], "globalId": f"GID-{i['id']}", "itemType": i["itemType"], "project": 5,
                 "modifiedDate": f"2026-04-{i['id'] % 28 + 1:02d}T00:00:00.000+0000", "createdDate": "2026-01-01T00:00:00.000+0000", "fields": i["fields"],
                 "location": {"parent": {"item": i["parent"]}} if i["parent"] else {}} for i in items]
        return listing(req, rows)
    t.add(f"{root}/abstractitems", guard(abstractitems))
    if not no_rel_types:
        t.add(f"{root}/relationshiptypes", guard(lambda r: listing(r, JAMA_REL_TYPES)))

    def relationships(req: Req):
        n = int(req.query.get("maxResults", 20))
        if not 1 <= n <= 1000:
            return json_response({"meta": {"status": "Bad Request"}}, status=400)
        last = int(req.query.get("lastId", 0))
        rows = [{"id": r[0], "fromItem": r[1], "toItem": r[2], "relationshipType": r[3], "type": "relationships", "suspect": r[4]} for r in rels if r[0] > last]
        chunk = rows[:n]
        if rels_stuck and chunk:
            chunk = [dict(c, id=1) for c in chunk]            # the server hands back the same last id every time
        return json_response({"meta": {"status": "OK", "pageInfo": {"startIndex": 0, "resultCount": len(chunk)}}, "data": chunk})
    t.add(f"{root}/relationships", guard(relationships))
    for pid, name in (picks if picks is not None else JAMA_PICKS).items():
        t.add(f"{root}/picklistoptions/{pid}", guard(lambda r, pid=pid, name=name: text_response("nope", status=403) if fail_picks else json_response({"meta": {"status": "OK"}, "data": {"id": pid, "name": name}})))
    return t
