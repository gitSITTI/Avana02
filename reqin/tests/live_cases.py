"""In-memory FAKES of the servers the live connectors talk to, built from the DOCUMENTED shapes (see each adapter's docstring
for what is verified and what is assumed). Everything here is synthetic and fictional. Passing against these proves the
connector's logic (paging, joining, hierarchy, safety); it does NOT prove the real server matches. That is a human step.
"""
from __future__ import annotations

import urllib.parse

from reqin.testing import FakeTransport, Req, json_response, text_response

# =====================================================================================================================
# SysML v2 REST API
# =====================================================================================================================
SYSML_BASE = "https://twc.example.test:8443/sysmlv2-api"

SYSML_ELEMENTS = [
    {"@id": "pkg1", "@type": "Package", "declaredName": "Requirements"},
    {"@id": "r1", "@type": "RequirementDefinition", "declaredShortName": "REQ-001", "declaredName": "ResponseTime",
     "owner": {"@id": "pkg1"}, "isAbstract": False, "elementId": "r1"},
    {"@id": "d1", "@type": "Documentation", "body": "The controller shall respond to a command within 50 ms.", "owner": {"@id": "r1"}},
    {"@id": "r2", "@type": "RequirementDefinition", "declaredShortName": "REQ-002", "declaredName": "FaultLogging", "owner": {"@id": "pkg1"}},
    {"@id": "d2a", "@type": "Documentation", "body": "The controller shall record every fault.", "owner": {"@id": "r2"}},
    {"@id": "d2b", "@type": "Documentation", "body": "Each record shall include a timestamp.", "owner": {"@id": "r2"}},
    {"@id": "r3", "@type": "RequirementUsage", "declaredShortName": "REQ-003", "declaredName": "Reboot", "owner": {"@id": "r2"},
     "documentation": [{"@id": "d3"}]},
    {"@id": "d3", "@type": "Documentation", "body": "The controller shall restart within 30 seconds.", "owner": {"@id": "pkg1"}},
    {"@id": "p1", "@type": "PartUsage", "declaredName": "Valve"},
    {"@id": "r4", "@type": "RequirementUsage", "declaredShortName": "REQ-004", "declaredName": "NoDocumentation", "owner": {"@id": "pkg1"}},
    {"@id": "r5", "@type": "RequirementDefinition", "declaredName": "Heartbeat", "owner": {"@id": "pkg1"}},
    {"@id": "d5", "@type": "Documentation", "body": "The controller shall send a heartbeat every 1 s.", "owner": {"@id": "r5"}},
    {"@id": "dep1", "@type": "Dependency", "client": [{"@id": "r3"}], "supplier": [{"@id": "r1"}]},
    {"@id": "dep2", "@type": "Dependency", "client": [{"@id": "r1"}], "supplier": [{"@id": "p1"}]},
    {"@id": "dep3", "@type": "Dependency", "client": [{"@id": "p1"}], "supplier": [{"@id": "pkg1"}]},
]
SYSML_GOLD = {
    "REQ-001": "The controller shall respond to a command within 50 ms.",
    "REQ-002": "The controller shall record every fault. Each record shall include a timestamp.",
    "REQ-003": "The controller shall restart within 30 seconds.",
    "Heartbeat": "The controller shall send a heartbeat every 1 s.",
}
SYSML_OK, SYSML_REJECTED, SYSML_LINKS = 4, 1, 2     # REQ-004 has no documentation; dep3 touches no requirement


def sysml_server(mode: str = "link", style: str = "bracket", head: bool = True, token_required: str | None = None,
                 elements: list[dict] | None = None, base: str = SYSML_BASE) -> FakeTransport:
    """mode: link   -> pages carry a Link rel=next header
            cursor -> no Link header, but page[after]=<last id> is honoured
            stuck  -> no Link header and page[after] is ignored (a server we cannot page: the connector must refuse)
            all    -> page size is ignored and everything comes back at once
       head=False -> GET /projects/{id} has no branch (SysON-like: the project id is the commit id)"""
    els = elements if elements is not None else SYSML_ELEMENTS
    prefix = urllib.parse.urlsplit(base).path
    sk, ak = ("page[size]", "page[after]") if style == "bracket" else ("page_size", "page_after")
    t = FakeTransport()

    def guard(req: Req):
        if token_required and req.headers.get("Authorization") != f"Bearer {token_required}":
            return json_response({"error": "unauthorised"}, status=403)
        return None

    def paged(items: list[dict], url: str, req: Req):
        size = int(req.query[sk]) if sk in req.query and mode != "all" else len(items) or 1
        start = 0
        if req.query.get(ak) and mode != "stuck":
            start = [e["@id"] for e in items].index(req.query[ak]) + 1
        chunk = items[start:start + size]
        headers = {}
        if mode == "link" and start + size < len(items):
            headers["Link"] = f'<{url}?{ak}={chunk[-1]["@id"]}&{sk}={size}>; rel="next"'
        return json_response(chunk, headers=headers)

    def route(path, fn):
        def h(req: Req):
            return guard(req) or fn(req)
        t.add(prefix + path, h)

    projects = [{"@id": "P1", "name": "Fictional Widget Controller"}, {"@id": "P2", "name": "Another Fictional Model"}]
    route("/projects", lambda r: paged(projects, f"{base}/projects", r))
    route("/projects/P1", lambda r: {"@id": "P1", "name": "Fictional Widget Controller", **({"defaultBranch": {"@id": "B1"}} if head else {})}
          if head else json_response({"message": "no such"}, status=404))
    route("/projects/P1/branches", lambda r: paged([{"@id": "B1", "name": "main"}, {"@id": "B2", "name": "draft"}], f"{base}/projects/P1/branches", r))
    route("/projects/P1/branches/B1", lambda r: {"@id": "B1", "name": "main", "head": {"@id": "C9"}})
    route("/projects/P1/branches/B2", lambda r: {"@id": "B2", "name": "draft", "head": {"@id": "C7"}})
    for cid in ("C9", "C7", "P1"):
        route(f"/projects/P1/commits/{cid}/elements",
              lambda r, cid=cid: paged(els if cid != "C7" else els[:3], f"{base}/projects/P1/commits/{cid}/elements", r))
    return t


# =====================================================================================================================
# OSLC RM (DOORS Next / DOORS Web Access)
# =====================================================================================================================
OSLC_ROOT = "https://dng.example.test"
OSLC_NS = ('xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#" '
           'xmlns:oslc="http://open-services.net/ns/core#" xmlns:oslc_rm="http://open-services.net/ns/rm#" '
           'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:jazz_rm="http://jazz.net/ns/rm#"')

# id, title, primary text (XHTML) or None, link properties (property -> targets)
OSLC_REQS = [
    (1, "Response time", "<p>The controller shall respond to a command within 50 ms.</p>", {"decomposedBy": [2, 3]}),
    (2, "Fault log", "<p>The controller shall log every fault.</p>", {"decomposes": [1]}),
    (3, "Reboot", "<p>The controller shall restart within <b>30</b> seconds.</p>", {"satisfiedBy": [5]}),
    (4, "A heading with no text", None, {}),
    (5, "Mass", "<p>The unit shall weigh no more than 12 kg.</p>", {}),
    (6, "Vibration", "<p>The unit shall survive 5 g of vibration.</p>", {"validatedBy": ["TC-1"]}),
    (7, "Heartbeat", "<p>The controller shall send a heartbeat every 1 s.</p>", {"trackedBy": ["CR-9"]}),
]
OSLC_GOLD = {"1": "The controller shall respond to a command within 50 ms.", "2": "The controller shall log every fault.",
             "3": "The controller shall restart within 30 seconds.", "5": "The unit shall weigh no more than 12 kg.",
             "6": "The unit shall survive 5 g of vibration.", "7": "The controller shall send a heartbeat every 1 s."}
OSLC_OK, OSLC_REJECTED = 6, 1
OSLC_LINKS = 4        # contain 1->2 and 1->3 (the reverse statement on 2 is the SAME link, emitted once), satisfy 5->3, verify TC-1->6


def _res(i) -> str:
    return f"{OSLC_ROOT}/rm/resources/_{i}" if isinstance(i, int) else f"{OSLC_ROOT}/ext/{i}"


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _rdf(body: str) -> str:
    return f'<?xml version="1.0" encoding="UTF-8"?><rdf:RDF {OSLC_NS}>{body}</rdf:RDF>'


def _req_xml(r) -> str:
    i, title, text, links = r
    x = f'<oslc_rm:Requirement rdf:about="{_res(i)}"><dcterms:identifier>{i}</dcterms:identifier><dcterms:title>{_esc(title)}</dcterms:title>'
    x += f'<dcterms:modified>2026-01-0{i}T10:00:00Z</dcterms:modified>'
    if text:
        x += f'<jazz_rm:primaryText rdf:parseType="Literal"><div xmlns="http://www.w3.org/1999/xhtml">{text}</div></jazz_rm:primaryText>'
    for prop, targets in links.items():
        for t in targets:
            x += f'<oslc_rm:{prop} rdf:resource="{_res(t)}"/>'
    return x + "</oslc_rm:Requirement>"


def oslc_server(honor_page_size: bool = True, loop: bool = False, login_page: bool = False, turtle_catalog: bool = False,
                reqs=None, drop_total: bool = False, report_total: int | None = None) -> FakeTransport:
    reqs = OSLC_REQS if reqs is None else reqs
    t = FakeTransport()
    sp1, sp2 = f"{OSLC_ROOT}/rm/oslc_rm/PA1/services.xml", f"{OSLC_ROOT}/rm/oslc_rm/PA2/services.xml"
    cat = f"{OSLC_ROOT}/rm/oslc_rm/catalog"

    def oslc_only(fn):
        def h(req: Req):
            if login_page:
                return text_response("<html><body>Please sign in</body></html>", "text/html")
            if req.headers.get("OSLC-Core-Version") != "2.0":
                return text_response("OSLC-Core-Version header missing", status=400)
            return fn(req)
        return h

    t.add("/rm/rootservices", oslc_only(lambda r: text_response(
        _rdf(f'<rdf:Description rdf:about="{OSLC_ROOT}/rm/rootservices"><oslc_rm:rmServiceProviders rdf:resource="{cat}"/></rdf:Description>'),
        "application/rdf+xml")))
    if turtle_catalog:
        ttl = (f'@prefix oslc: <http://open-services.net/ns/core#> . @prefix dcterms: <http://purl.org/dc/terms/> .\n'
               f'<{cat}> a oslc:ServiceProviderCatalog ; oslc:serviceProvider <{sp1}>, <{sp2}> .\n'
               f'<{sp1}> a oslc:ServiceProvider ; dcterms:title "Fictional Widget Project" .\n'
               f'<{sp2}> a oslc:ServiceProvider ; dcterms:title "Another Fictional Project" .\n')
        t.add("/rm/oslc_rm/catalog", oslc_only(lambda r: text_response(ttl, "text/turtle")))
    else:
        t.add("/rm/oslc_rm/catalog", oslc_only(lambda r: text_response(_rdf(
            f'<oslc:ServiceProviderCatalog rdf:about="{cat}">'
            f'<oslc:serviceProvider><oslc:ServiceProvider rdf:about="{sp1}"><dcterms:title>Fictional Widget Project</dcterms:title></oslc:ServiceProvider></oslc:serviceProvider>'
            f'<oslc:serviceProvider><oslc:ServiceProvider rdf:about="{sp2}"><dcterms:title>Another Fictional Project</dcterms:title></oslc:ServiceProvider></oslc:serviceProvider>'
            f'</oslc:ServiceProviderCatalog>'), "application/rdf+xml")))

    def services(pa: str):
        qb = _esc(f"{OSLC_ROOT}/rm/views?oslc.query=true&projectURL={pa}")
        return oslc_only(lambda r: text_response(_rdf(
            f'<oslc:ServiceProvider rdf:about="{OSLC_ROOT}/rm/oslc_rm/{pa}/services.xml"><oslc:service><oslc:Service>'
            f'<oslc:queryCapability><oslc:QueryCapability><oslc:queryBase rdf:resource="{qb}"/>'
            f'<oslc:resourceType rdf:resource="http://open-services.net/ns/rm#RequirementCollection"/></oslc:QueryCapability></oslc:queryCapability>'
            f'<oslc:queryCapability><oslc:QueryCapability><oslc:queryBase rdf:resource="{qb}"/>'
            f'<oslc:resourceType rdf:resource="http://open-services.net/ns/rm#Requirement"/></oslc:QueryCapability></oslc:queryCapability>'
            f'</oslc:Service></oslc:service></oslc:ServiceProvider>'), "application/rdf+xml"))
    t.add("/rm/oslc_rm/PA1/services.xml", services("PA1"))
    t.add("/rm/oslc_rm/PA2/services.xml", services("PA2"))

    def views(req: Req):
        if req.query.get("projectURL") != "PA1":
            return text_response(_rdf(""), "application/rdf+xml")
        n = int(req.query.get("oslc.pageSize", 1000)) if honor_page_size else len(reqs) or 1
        start = int(req.query.get("_startIndex", 0))
        chunk = reqs[start:start + n]
        me = f"{OSLC_ROOT}/rm/views?oslc.query=true&projectURL=PA1&_startIndex={start}"
        body = f'<rdf:Description rdf:about="{_esc(me)}">' + "".join(f'<rdfs:member rdf:resource="{_res(r[0])}"/>' for r in chunk) + "</rdf:Description>"
        info = f'<oslc:ResponseInfo rdf:about="{_esc(me)}">' + ("" if drop_total else f"<oslc:totalCount>{report_total if report_total is not None else len(reqs)}</oslc:totalCount>")
        if start + n < len(reqs):
            nxt = me.replace(f"_startIndex={start}", f"_startIndex={start + n}")
            info += f'<oslc:nextPage rdf:resource="{_esc(nxt)}"/>'
        if loop:
            info += f'<oslc:nextPage rdf:resource="{_esc(me)}"/>'
        return text_response(_rdf(body + info + "</oslc:ResponseInfo>" + "".join(_req_xml(r) for r in chunk)), "application/rdf+xml")
    t.add("/rm/views", oslc_only(views))
    return t


# =====================================================================================================================
# Digital.ai Agility (VersionOne) REST Data API
# =====================================================================================================================
AG_BASE = "https://agility.example.test/Instance"


def _attrs(**kw):
    return {k: {"_type": "Attribute", "name": k, "value": v} for k, v in kw.items()}


def _asset(atype, num, moment=1, **kw):
    return {"_type": "Asset", "href": f"/Instance/rest-1.v1/Data/{atype}/{num}", "id": f"{atype}:{num}:{moment}", "Attributes": _attrs(**kw)}


def agility_assets(moment: int = 1) -> dict[str, list[dict]]:
    rel = lambda oid: {"_type": "Relation", "idref": oid}  # noqa: E731
    return {
        "Epic": [_asset("Epic", 100, moment, Number="E-00100", Name="Platform", Description="<p>The platform shall support over-the-air updates.</p>",
                        **{"Scope.Name": "Fictional Project", "Status.Name": "Active"}, AssetState=64, Super=None, Dependencies=[], ChangeDateUTC="2026-01-01T00:00:00")],
        "Story": [
            _asset("Story", 201, moment, Number="S-01201", Name="Updater", Description="<p>The updater shall verify the signature before install.</p>",
                   **{"Scope.Name": "Fictional Project", "Status.Name": "Active"}, AssetState=64, Super=rel("Epic:100"), Dependencies=[rel("Story:202")], ChangeDateUTC="2026-01-02T00:00:00"),
            _asset("Story", 202, moment, Number="S-01202", Name="Buffer", Description="<p>The controller shall buffer 10 messages.</p>",
                   **{"Scope.Name": "Fictional Project", "Status.Name": "Future"}, AssetState=0, Super=rel("Epic:100"), Dependencies=[], ChangeDateUTC="2026-01-03T00:00:00"),
            _asset("Story", 203, moment, Number="S-01203", Name="Spike", Description="",
                   **{"Scope.Name": "Fictional Project", "Status.Name": "Active"}, AssetState=64, Super=None, Dependencies=[], ChangeDateUTC="2026-01-04T00:00:00"),
        ],
        "Defect": [_asset("Defect", 301, moment, Number="B-00301", Name="Flicker", Description="<p>The display shall not flicker.</p>",
                          **{"Scope.Name": "Fictional Project", "Status.Name": "Active"}, AssetState=64, Super=None, Dependencies=[], ChangeDateUTC="2026-01-05T00:00:00")],
    }


AG_GOLD = {"E-00100": "The platform shall support over-the-air updates.", "S-01201": "The updater shall verify the signature before install.",
           "S-01202": "The controller shall buffer 10 messages.", "B-00301": "The display shall not flicker."}
AG_OK, AG_REJECTED, AG_FILTERED, AG_LINKS = 4, 0, 1, 1      # S-01203 has an empty Description: filtered by the profile's `where`


def agility_server(assets=None, honor_page: bool = True, token: str | None = None, drop_total: bool = False, wrong_shape: bool = False,
                   stuck: bool = False) -> FakeTransport:
    """honor_page=False -> the page parameter is ignored and everything comes back at once; stuck=True -> every request returns the first page."""
    data = assets or agility_assets()
    t = FakeTransport()
    for atype, items in data.items():
        def h(req: Req, items=items):
            if token and req.headers.get("Authorization") != f"Bearer {token}":
                return json_response({"error": "unauthorised"}, status=401)
            if wrong_shape:
                return text_response("<html>sign in</html>", "text/html")
            size, start = (int(x) for x in req.query["page"].split(",")) if honor_page and "page" in req.query else (len(items) or 1, 0)
            start = 0 if stuck else start
            chunk = items[start:start + size]
            body = {"_type": "Assets", "pageSize": size, "pageStart": start if honor_page else 0, "Assets": chunk}
            if not drop_total:
                body["total"] = len(items)
            return json_response(body)
        t.add(f"/Instance/rest-1.v1/Data/{atype}", h)
    return t
