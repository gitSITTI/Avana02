"""OSLC Requirements Management (RM) 2.x: IBM DOORS Next, DOORS 9.x via DOORS Web Access, and any other OSLC RM provider.

READ-ONLY. Only GET requests are ever made (see connect.py). Needs the optional `rdflib` package:  pip install "reqin[oslc]"

URI:      oslc+https://host/rm/rootservices        (the root services document of the server; for DNG that is <server>/rm/rootservices)
Options:  project            title of the project area / service provider to read (listed in the error if omitted and several exist)
          configuration      configuration (stream/baseline) URI, sent as the Configuration-Context header (OSLC Config Management)
          catalog | service_provider | query_base
                             skip discovery: give the catalog URL, the service provider URL, or the query capability's queryBase
          where / prefix     oslc.where / oslc.prefix filter, e.g. where='dcterms:title="Brake*"' (OSLC Query syntax)
          select             oslc.select, default *  (all properties inline)
          page_size          oslc.pageSize hint, default 200 (servers may ignore it: nextPage is always followed)
          resource_type      default http://open-services.net/ns/rm#Requirement
          links              default | all | none | comma list of oslc_rm property names (satisfiedBy,decomposedBy,...)
          link_map           JSON {"propertyName": ["kind", "out|in"]} overrides  (out: this->value, in: value->this)
          prefixes           JSON {"prefix": "namespace URI"} extra prefixes used to name fields
          fetch_members      1 = GET every member separately when the query result lacks its properties (slow)
          token_env | basic_user_env + basic_password_env | cookie_env | auth_hook     see connect.auth_from_options
          ca_bundle          your organisation's CA bundle (TLS is always verified)

WHAT IS VERIFIED AND WHAT IS NOT:
  verified in public specs/docs  OSLC RM namespace and the Requirement link properties (OASIS OSLC RM 2.1 vocabulary); OSLC Query:
                                 oslc.where/select/prefix, oslc.pageSize as a hint, oslc:nextPage / oslc:totalCount / rdfs:member;
                                 Configuration-Context header and oslc_config.context parameter (OSLC Config Management);
                                 DNG: rootservices -> catalog -> services -> oslc:queryCapability -> queryBase, headers
                                 OSLC-Core-Version: 2.0 and Accept: application/rdf+xml
  NOT seen live                  the exact property that points from rootservices to the catalog on YOUR server (we look for
                                 any property named rmServiceProviders), the DNG primary-text property (jazz_rm:primaryText is
                                 assumed; dcterms:description is the fallback in the profile), the sign-in method your server
                                 requires (OAuth/form/OIDC are NOT built in: use cookie_env for a pilot or write an auth_hook)
  Tested only against an in-memory fake (tests/test_live_connectors.py).
  First run on your server: reqin sample oslc+https://host/rm/rootservices --opt project="..." --opt cookie_env=DNG_COOKIE
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterator

from ..adapter import Adapter, Caps, Container, Discovery, Source, make_field_info, register
from ..connect import ConnectError, ReadOnlyHttp, make_http, opt_dict, opt_int, opt_list
from ..model import Fidelity, RawLink, RawRecord, SourceRef

NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "oslc": "http://open-services.net/ns/core#", "oslc_rm": "http://open-services.net/ns/rm#",
    "dcterms": "http://purl.org/dc/terms/", "foaf": "http://xmlns.com/foaf/0.1/",
    "jazz_rm": "http://jazz.net/ns/rm#", "nav": "http://jazz.net/ns/rm/navigation#",
    "oslc_config": "http://open-services.net/ns/config#",
}
RM_REQUIREMENT = NS["oslc_rm"] + "Requirement"
# property -> (canonical link kind, direction). out: this -> value, in: value -> this.  'contain' is parent -> child.
# The vocabulary says e.g. "satisfiedBy: Requirement is satisfied by the resource", so the VALUE satisfies THIS: direction in.
DEFAULT_LINK_MAP: dict[str, tuple[str, str]] = {
    "satisfiedBy": ("satisfy", "in"), "satisfies": ("satisfy", "out"),
    "decomposedBy": ("contain", "out"), "decomposes": ("contain", "in"),
    "elaboratedBy": ("refine", "in"), "elaborates": ("refine", "out"),
    "specifiedBy": ("trace", "in"), "specifies": ("trace", "out"),
    "validatedBy": ("verify", "in"),
    "constrainedBy": ("trace", "in"), "constrains": ("trace", "out"),
    "trackedBy": ("trace", "in"), "implementedBy": ("trace", "in"), "affectedBy": ("trace", "in"),
}
DEFAULT_LINKS = ["satisfiedBy", "satisfies", "decomposedBy", "decomposes", "elaboratedBy", "elaborates",
                 "specifiedBy", "specifies", "validatedBy", "constrainedBy", "constrains"]   # requirement-to-requirement kinds
_FORMATS = {"application/rdf+xml": "xml", "text/turtle": "turtle", "application/x-turtle": "turtle",
            "application/ld+json": "json-ld", "application/n-triples": "nt", "text/xml": "xml", "application/xml": "xml"}


def _rdflib():
    try:
        import rdflib
    except ImportError:
        raise ConnectError('the OSLC connector needs rdflib: pip install "reqin[oslc]"') from None
    return rdflib


def _short(uri: str, prefixes: dict[str, str]) -> str:
    for pfx, ns in sorted(prefixes.items(), key=lambda kv: -len(kv[1])):
        if uri.startswith(ns):
            return f"{pfx}:{uri[len(ns):]}"
    return uri


@register
class OslcRmAdapter(Adapter):
    name = "oslc_rm"
    fidelity = Fidelity.STRUCTURED
    caps = Caps(structured_ids=True, links=True, hierarchy=False, incremental=False)
    maturity = "fake-server-tested"

    def __init__(self, transport=None) -> None:  # noqa: ANN001
        self._transport = transport
        self._http: ReadOnlyHttp | None = None
        self._cache: dict[str, tuple[list, list, list[str], str]] = {}

    def sniff(self, src: Source) -> float:
        u = src.uri
        if u.startswith(("oslc+http://", "oslc+https://")):
            return 0.95
        if u.startswith(("http://", "https://")) and u.rstrip("/").endswith("/rootservices"):
            return 0.85
        return 0.0

    def audit(self) -> list:
        return list(self._http.audit) if self._http else []

    # ---- helpers -----------------------------------------------------------------------------------
    @staticmethod
    def _root(src: Source) -> str:
        return src.uri.removeprefix("oslc+")

    def _headers(self, src: Source) -> dict[str, str]:
        h = {"OSLC-Core-Version": "2.0", "Accept": "application/rdf+xml, text/turtle;q=0.8"}
        if src.options.get("configuration"):
            h["Configuration-Context"] = str(src.options["configuration"])
        return h

    def _graph(self, http: ReadOnlyHttp, url: str, src: Source, params: dict | None = None, allow_empty: bool = False):
        rdflib = _rdflib()
        resp = http.get(url, params, self._headers(src))
        ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        g = rdflib.Graph()

        def fail(why: str) -> ConnectError:
            snippet = http.scrub(resp.text()[:80].replace("\n", " "))
            return ConnectError(f"{http.safe_url(url)} did not return RDF ({why}; content-type {ctype or '?'}; starts with {snippet!r}). "
                                "Usually a login page: the server wants a sign-in this connector does not do (see cookie_env / auth_hook in CONNECTORS.md).")
        if ctype in ("text/html", "application/xhtml+xml") or resp.body.lstrip()[:5].lower() in (b"<!doc", b"<html"):
            raise fail("it is an HTML page")        # a well-formed HTML page would otherwise parse as an empty graph
        try:
            g.parse(data=resp.body, format=_FORMATS.get(ctype, "xml"), publicID=url)
        except Exception as e:  # rdflib raises many parser-specific types
            raise fail(type(e).__name__) from None
        if not allow_empty and len(g) == 0:
            raise fail("it contains no RDF statements")
        return g

    # ---- discovery of the query capability ---------------------------------------------------------
    def _query_base(self, http: ReadOnlyHttp, src: Source, notes: list[str]) -> str:
        rdflib = _rdflib()
        O, RDF = rdflib.Namespace(NS["oslc"]), rdflib.RDF
        DC = rdflib.Namespace(NS["dcterms"])
        o = src.options
        if o.get("query_base"):
            notes.append("query base given explicitly")
            return str(o["query_base"])
        sp = o.get("service_provider")
        if not sp:
            cat = o.get("catalog")
            if not cat:
                g = self._graph(http, self._root(src), src)
                cats = [str(v) for _, p, v in g if str(p).endswith("rmServiceProviders")]
                if not cats:
                    raise ConnectError("the root services document has no ...rmServiceProviders property; give catalog=<URL of the "
                                       "service provider catalog> (see the server's rootservices document)")
                cat = cats[0]
            g = self._graph(http, str(cat), src)
            found_provs = set()
            for node in set(g.objects(None, O.serviceProvider)) | set(g.subjects(RDF.type, O.ServiceProvider)):
                found_provs.add((str(g.value(node, DC.title) or ""), str(node)))
            provs = sorted(found_provs)
            want = o.get("project")
            if want:
                hit = [u for t, u in provs if t == want]
                if not hit:
                    raise ConnectError(f"no project named {want!r}. Projects in this catalog: {[t for t, _ in provs][:30]}")
                sp = hit[0]
            elif len(provs) == 1:
                sp = provs[0][1]
                notes.append(f"only one project in the catalog: {provs[0][0]!r}")
            else:
                raise ConnectError(f"several projects: pick one with project=<title>. Projects: {[t for t, _ in provs][:30]}")
        g = self._graph(http, str(sp), src)
        want_type = str(o.get("resource_type", RM_REQUIREMENT))
        found: list[str] = []
        for qc in g.subjects(RDF.type, O.QueryCapability):
            types = {str(t) for t in g.objects(qc, O.resourceType)}
            found += sorted(types)
            qb = g.value(qc, O.queryBase)
            if qb is not None and want_type in types:
                notes.append(f"query capability for {want_type}")
                return str(qb)
        raise ConnectError(f"no query capability for {want_type} in {http.safe_url(str(sp))}; it offers {sorted(set(found))}")

    # ---- the read, once per run, cached --------------------------------------------------------------
    def _load(self, src: Source):
        o = src.options
        key = hashlib.sha1(json.dumps([src.uri, sorted((a, str(b)) for a, b in o.items() if a not in ("token", "token_env", "cookie_env"))]).encode()).hexdigest()
        if key in self._cache:
            return self._cache[key]
        rdflib = _rdflib()
        RDF, RDFS, OSLC = rdflib.RDF, rdflib.RDFS, rdflib.Namespace(NS["oslc"])
        self._http = http = make_http(o, self._transport)
        prefixes = {**NS, **opt_dict(o, "prefixes")}
        notes: list[str] = []
        base = self._query_base(http, src, notes)
        want_type = rdflib.URIRef(str(o.get("resource_type", RM_REQUIREMENT)))

        params: dict[str, Any] = {"oslc.pageSize": opt_int(o, "page_size", 200), "oslc.select": o.get("select", "*"), "oslc.paging": "true"}
        if o.get("where"):
            params["oslc.where"] = o["where"]
            params["oslc.prefix"] = o.get("prefix") or ",".join(f"{p}=<{NS[p]}>" for p in ("dcterms", "oslc", "oslc_rm", "jazz_rm"))
        link_names = self._link_names(o)
        link_map = {**DEFAULT_LINK_MAP, **{k: tuple(v) for k, v in opt_dict(o, "link_map").items()}}

        members: dict[str, dict[str, list[str]]] = {}
        member_links: dict[str, list[tuple[str, str]]] = {}
        seen_pages: set[str] = set()
        url: str | None = base
        total = None
        peek = opt_int(o, "peek", 0)
        for page_no in range(1, opt_int(o, "max_pages", 100_000) + 1):
            g = self._graph(http, url, src, params if url == base else None, allow_empty=True)
            subs = {m for m in g.objects(None, RDFS.member) if isinstance(m, rdflib.URIRef)} or set(g.subjects(RDF.type, want_type))
            for s in subs:
                if o.get("fetch_members") in (1, "1", True, "true") and not any(True for _ in g.predicate_objects(s) if _[0] != RDF.type):
                    g2 = self._graph(http, str(s), src)
                    self._take(g2, s, prefixes, link_names, link_map, members, member_links, rdflib)
                else:
                    self._take(g, s, prefixes, link_names, link_map, members, member_links, rdflib)
            tc = next(iter(sorted(g.objects(None, OSLC.totalCount))), None)
            total = int(tc) if tc is not None and str(tc).isdigit() else total
            nxt = next(iter(sorted(g.objects(None, OSLC.nextPage))), None)
            if peek and page_no >= peek:
                notes.append(f"[PEEK: first {peek} page(s) only, so counts and links are incomplete]")
                total = None
                break
            if nxt is None:
                break
            nxt = str(nxt)
            if nxt in seen_pages or nxt == url:
                raise ConnectError("oslc:nextPage points back to a page already read: the server's paging is not advancing")
            seen_pages.add(nxt)
            url = nxt
        else:
            raise ConnectError("stopped after max_pages")
        if total is not None and total != len(members):
            notes.append(f"WARNING: the server reported oslc:totalCount {total} but {len(members)} distinct members were read")
        notes.append(f"read {len(members)} requirement resources")

        def sort_key(uri: str):
            ident = members[uri].get("dcterms:identifier", [""])[0]
            return (0, int(ident), uri) if ident.isdigit() else (1, 0, uri)
        rows = [(u, {k: "; ".join(v) for k, v in sorted(members[u].items())}) for u in sorted(members, key=sort_key)]
        links, seen = [], set()
        for u in sorted(member_links):
            for prop, other in sorted(member_links[u]):
                kind, direction = link_map[prop]
                a, b = (u, other) if direction == "out" else (other, u)
                if (a, b, kind) not in seen:
                    seen.add((a, b, kind))
                    links.append((a, b, kind, u))
        rev = hashlib.sha1(json.dumps([str(o.get("configuration", "")), [(u, f.get("dcterms:modified", "")) for u, f in rows]]).encode()).hexdigest()[:16]
        self._cache[key] = (rows, links, notes, rev)
        return self._cache[key]

    @staticmethod
    def _link_names(o) -> set[str]:  # noqa: ANN001
        mode = str(o.get("links", "default"))
        if mode == "default":
            return set(DEFAULT_LINKS)
        if mode == "none":
            return set()
        if mode == "all":
            return set(DEFAULT_LINK_MAP)
        return set(opt_list(o, "links", []))

    @staticmethod
    def _take(g, s, prefixes, link_names, link_map, members, member_links, rdflib) -> None:  # noqa: ANN001
        """Copy one member's properties into plain fields; selected link properties become links instead (no data is lost:
        links are emitted, and a link property that is NOT selected stays as an ordinary field)."""
        fields = members.setdefault(str(s), {})
        for p, v in g.predicate_objects(s):
            if isinstance(v, rdflib.BNode):
                continue
            local = str(p).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
            if local in link_names and local in link_map and isinstance(v, rdflib.URIRef):
                member_links.setdefault(str(s), []).append((local, str(v)))
                continue
            vals = fields.setdefault(_short(str(p), prefixes), [])
            if str(v) not in vals:
                vals.append(str(v))
        for vals in fields.values():
            vals.sort()

    # ---- the adapter contract --------------------------------------------------------------------------
    def discover(self, src: Source) -> Discovery:
        rows, links, notes, _ = self._load(src)
        keys = sorted({k for _, f in rows for k in f})
        return Discovery([Container("requirements", len(rows), [make_field_info(k, [f.get(k, "") for _, f in rows]) for k in keys])],
                         notes + [f"{len(links)} links from the selected oslc_rm link properties"])

    def read(self, src: Source) -> Iterator[RawRecord | RawLink]:
        rows, links, _, rev = self._load(src)
        root = self._root(src)
        for i, (uri, f) in enumerate(rows):
            yield RawRecord(native_id=uri, fields=f, order=i,
                            ref=SourceRef("oslc_rm", root, container="requirements", locator=uri, revision=rev))
        for a, b, kind, via in links:
            yield RawLink(a, b, kind, SourceRef("oslc_rm", root, container="links", locator=via, revision=rev))

    def revision(self, src: Source) -> str:
        c = next(iter(self._cache.values()), None)
        return c[3] if c else ""
