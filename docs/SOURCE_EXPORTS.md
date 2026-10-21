# What each source tool can export, and what this repo reads

Written 15 October 2026 from the vendors' own documentation, read through a web-fetch tool. No vendor manual is copied here: every statement is a short paraphrase with a pointer to the page it came from. Everything in this repo is made up (see `AGENTS.md`); nothing below was checked against a real installation, a real export or a real server.

This page exists so that a person who wants to feed `reqin` from a tool can see, before writing any code, **which export routes the vendor documents, what each carries and loses, how it authenticates, and which of those routes the repo reads today**. The repo is vendor-agnostic: the shared kit (`reqin.connect`, `reqin.testing`, the `Adapter` contract, `connector_template/`) does not know any vendor. Each connector below is a thin adapter on that kit, tested against a fake server written from the vendor's documentation. A fake written from documentation proves the connector follows the documentation. It does not prove the vendor's server behaves as documented. See section 9 for what a person with a real instance has to send back so those gaps can close.

## 1. How to read the labels

| Label | Meaning |
|---|---|
| `read` | The fetch tool returned the page and the statement was in its text. The tool summarises pages with a small model, so wording and numbers are second-hand. Re-check anything a decision depends on. |
| `read 3rd` | Same, but the page is not the vendor's (a forum post, a client library, a partner's page, a catalogue). |
| `snippet` | Seen only in a search-result title or listing. The page was not read. |
| `memory` | My background knowledge, not checked against a page in this research. Treat it as a hypothesis. |
| `not found` | I looked and the pages I could read do not say. That is not proof the vendor does not document it. |

### What could not be read (so a gap is not mistaken for an absence)

- **IBM:** the DXL Reference Manual PDF (only the contents list and chapter 1 came through, so no function signatures); several jazz.net library articles and wiki pages (permission prompt not answered or a login page); several IBM Support notes (abstract only); one jazz.net DXL archive page (HTTP 429, told to stop); the IBM Docs shell for DOORS 9.7.
- **Dassault / No Magic:** the public Swagger of the Teamwork Cloud REST API (`osmc.nomagic.com`, permission prompt not answered). It holds the real endpoint list, so the REST route for SysML 1.x projects is described only from the pages that show example calls. The MagicDraw OpenAPI user-guide PDF (robots).
- **Digital.ai:** nine developer-library pages returned only front matter (attachments, attribute types, attribute-definition syntax, Data Mart schema, advanced filtering, custom-report export options, two export pages, delete/recover). The authentication article on the support site redirects to a sign-in page.
- **Atlassian:** the REST reference pages are JavaScript shells, so response schemas for Jira (`isLast`, default `fields`, `maxResults` cap) are `not found` from official pages.
- **Siemens:** the Polarion REST user guide and the extension page for ReqIF exchange (partly), the feature-matrix PDFs (redirected).
- **General:** the shell cannot reach vendor sites, and the shared search budget ran out part-way through two of the four research passes. Some leads are therefore untested.

## 2. Summary: route by route

"Repo today" says what the code in this repository does with that route after this change. Every row is **fixture or fake-server tested only**; none has met a real server or a real export. `[new]` marks something added in this round; `[fixed]` marks a connector that existed and had a documented mismatch corrected.

| Tool | Route | Output | Auth | Unattended | Carries | Loses or hides | Repo today |
|---|---|---|---|---|---|---|---|
| **Digital.ai Agility** | `rest-1.v1/Data` GET | JSON (with `Accept` header) or XML (the portal's own default) | Bearer access token, Basic, Windows integrated | yes | name, description (HTML), number, status, state, scope, owners, parent (`Super`), dependencies | no archive concept; deleted items hidden by default; relation names for dependencies and tests unverified | `agility` adapter `[fixed]` |
| | grid export "Export (.xls)" | **HTML saved as `.xls`** | the UI user's rights | no (UI) | the visible columns of the view | hierarchy, anything not in the view; closed-item strike-through | `tabular` HTML-table reader `[new]`, profile `agility_export` |
| | `query.v1` | JSON, but called with POST | OAuth2 scope, or "all but NTLM" (the vendor's pages disagree) | yes | nested selects, `asof`, change filters | | **not built**: it is a POST, and the GET-only kit has no exception for it |
| | Data Mart (SQL Server) | tables | DB login | yes, on-premises only | dimension and bridge tables | not available on SaaS | `sql` adapter, with a query you write (no query pack or profile is shipped for it) |
| | `api/asset`, webhooks, SDKs, Agility Connect | | | | | write capable | **never**: create, update and delete on the same endpoint |
| **IBM DOORS 9.x** | ReqIF from a RIF definition (Project Properties) | `.reqif` / `.reqifz` | a DOORS login | no (client action) | objects, attributes, enumerations, hierarchy, optional links | pictures; tables; baselines | `reqif` adapter `[fixed]` |
| | DXL script, `doors -batch` | whatever the script writes | DOORS login, client install | yes | everything the script writes | | `connectors/doors9/export_requirements.dxl` `[fixed]` |
| | export to Word, Excel, HTML, RTF, text | files | | no | not documented in what I could read | | `docx`, `tabular` |
| | DWA OSLC | RDF/XML | **OAuth 1.0a** with a browser step | hard | requirement text in `dcterms:title` as "ID: text" | hierarchy (reported absent) | not built: needs request signing the kit cannot do |
| **IBM DOORS Next (DNG, ELM)** | OSLC RM v2 | RDF/XML | OAuth 1.0a, form login, Basic if enabled, JAS bearer token | yes with a long-lived token | requirement, identifier, primary text, folder parent, link properties | module order and structure; **needs a configuration (stream or baseline) pinned** | `oslc_rm` adapter `[fixed]` |
| | ReqIF export (UI, ReqIF API) | `.reqifz` | needs the Export ReqIF permission | no | module content, optional links | OSLC-integrated links, comments, history; XHTML `colgroup` and comment quirks | `reqif` adapter `[fixed]` |
| | CSV / XLS / XLSX export of a view | file | the UI user's rights | no | the view's columns, always `isHeading`, `parentBinding`, artifact type | collections, comments, reviews | `tabular` + profile `dng_csv` `[new]` |
| | Reportable REST (`/rm/publish/...`) | XML | as above | yes | module sections and depth | official docs are behind a login | **not built** (only unofficial descriptions found) |
| **MSOSA / Cameo / MagicDraw** (SysML 1.x) | ReqIF export, plugin and wizard or `reqifexport` | `.reqif` | model read | documented as schedulable, headless unconfirmed | text, hierarchy (**only** the "Specifications" export type), custom tags if "export all properties" is on | the six SysML relationship kinds may collapse into one relation type | `reqif` adapter `[fixed]`, profile `msosa_reqif` |
| | requirement table to CSV / XLSX | `.csv` `.xlsx` `.html` | model read | no (GUI) | `#`, Id, Name, Text and added columns | hierarchy, relationships | `tabular` + profile `cameo_requirement_table` `[new]` |
| | XMI export (UML XMI 2.5) and `.mdzip` (zip of XMI 2.4) | `.xmi`, `.mdzip` | file access | yes (it is a file) | classes, stereotype applications, relationships, nesting | | `sysml1_xmi` adapter `[new]` (replaces the `mdzip` stub) |
| | Report Wizard CLI (`generate`) | any template type, no CSV | TWC login or file | yes | whatever the template writes | needs a template and an install | documented only, not a connector |
| | Teamwork Cloud REST (OSMC) | JSON-LD at EMF level | session cookie (Basic login), `Token`, OAuth `Bearer` | yes | everything, as raw EMF | tag values are separate elements; listing endpoints unread | **not built** |
| | Teamwork Cloud OSLC | RDF | OAuth 1.0a | yes | architecture-management resources only | **no requirements, no query** | **not built**; do not point `oslc_rm` at it |
| **SysML v2** | Systems Modeling API (OMG 1.0, September 2025) on Teamwork Cloud 2026x, the pilot implementation, SysON | JSON | not stated for Teamwork Cloud | yes | elements, owned documentation, relationships | `exclude used projects` must be chosen on purpose | `sysml_api` adapter `[fixed]` |
| | textual notation export (`.sysml` files in a **folder**) | text | | no (UI) | `requirement def`, `requirement`, `satisfy` | | `sysml_text` adapter, now takes a directory `[fixed]` |
| **Atlassian Jira** | REST search | JSON | Cloud: Basic `email:token`; Data Center: Bearer PAT | yes | all fields, parent, typed links with both ends | | `jira` adapter `[new]` |
| | CSV export | CSV | | no | | **inward links dropped, outward links scattered over one column per link type** | `tabular` (lossy) |
| **Siemens Polarion** | REST v1 | JSON:API | Bearer PAT (REST is off until an admin enables it) | yes | work items, role-typed links, back-links | document structure unread | `polarion` adapter `[new]` |
| | "Automatic ReqIF Exchange" extension | `.reqif` | | | | support status is described two ways by the vendor's own listing | `reqif` |
| **Jama Connect** | REST v1 | JSON | OAuth client credentials (a POST), or Basic without SSO | yes | items, relationships with `suspect`, baselines | needs a Named Creator licence | `jama` adapter `[new]` |
| | Data Exchange / Interchange (separate app) | `.reqif` | licence file, Java 8 | | | | `reqif` |
| **PTC Codebeamer** | REST v3, native ReqIF | JSON, `.reqif` | Basic, Bearer | yes | items, associations | **usage policy bars extracting data to build data sources without written permission** | ReqIF only; **no connector** until PTC confirms in writing |
| **Sparx Enterprise Architect** | SQL repository, CSV, XMI 1.1 to 2.5.1, automation API | tables, CSV, XMI | DB login | yes (SQL) | elements and connectors | CSV page documents elements only | `sql` query pack in `connectors/ea/` `[new]`; table and column names recalled, not read; file repositories not covered |
| **Rhapsody, Capella, Teamcenter, Windchill, Doorstop, StrictDoc** | see section 7 | | | | | | via `reqif` or `tabular`; no connector |

## 3. Digital.ai Agility (formerly VersionOne)

### 3.1 The documented ways out

| Path | Output | Writes? | Deployment | Evidence |
|---|---|---|---|---|
| `rest-1.v1/Data` | XML by default; JSON when the request sends `Accept: application/json` | GET reads, POST writes | SaaS and on-premises | `read`, the developer portal and the vendor's GitHub API docs |
| `rest-1.v1/Hist` | history queries ("moments"), same formats | GET | both | `read` |
| `query.v1` | JSON, called with **POST** (the portal lists "POST, GET" but never shows a GET form) | read-only by the vendor's description | both | `read` |
| `meta.v1` | XML, **no authentication**: attribute names and types per asset type | GET | both | `read` |
| `api/asset` (bulk) | JSON | **creates, updates and deletes** as well as queries | both | `read` (vendor GitHub docs only, not on the portal's endpoint list) |
| `attachments.img`, `ActivityStream`, `api/tags`, `API/ProjectRoles` | files, JSON | GET | both | `read`; the portal says the activity stream may miss changes |
| UI grid "Export (.xls)" | **an HTML table saved with an `.xls` extension**, so Excel shows a format-mismatch warning | GET | both | `read` |
| Templates, requests, "Export MPX", Report Builder | `.xls`, MPX, CSV / Excel / PDF | GET | both | `read` |
| Data Mart | a de-normalised SQL Server database loaded by an ETL that must run at least daily | read | **on-premises only** (the ETL page says it does not apply to hosted/SaaS) | `read` |

The complete endpoint list on the portal has twelve entries (activity stream, tags, asset detail, attachments, two localisation endpoints, meta, project roles, `query.v1`, `rest-1.v1/Data`, `rest-1.v1/Hist`, `rest-1.v1/New`). No newer REST, GraphQL or OData endpoint and no whole-instance bulk export was found.

### 3.2 Facts that shaped the connector

- **Format.** The portal documents XML for rest-1.v1. JSON exists but only with the `Accept` header. A proxy that strips the header turns a JSON expectation into XML. The connector reads both.
- **Query language.** `sel=` and `select=` both appear; `where=Attr='v';Attr2='v'` joins terms with `;`; dotted paths such as `Scope.Name` work; `sort=-Attr`; `page=<size>,<start>` counts items, not pages. Only equality is shown in rest-1.v1 `where` examples. `!=`, `>` and `<` inside `where` were `not found`; `!=` appears only in bracket filters on attribute paths. So an `AssetState!='255'` filter is both unnecessary and unproven.
- **Paging.** No default page size: a call without `page` returns the whole table with `pageSize` 2147483647. No maximum is documented. No order is documented without `sort`.
- **Asset states.** 0 Future, 64 Active, 128 Closed, 200 Template, 208 Broken Down, 255 Deleted. Deleted assets are hidden unless `where=IsDeleted='true'`. `AssetState='64'` is the documented-by-example way to say "open items only" (a community post, `read 3rd`).
- **Where the text is.** `Name` (text, up to 4,000 characters) and `Description` (long text, HTML). `Number` carries the item number; its prefixes are configurable (`memory`).
- **Hierarchy.** `Super` is the portfolio parent (a story's epic); `Parent` is the backlog group (old "theme"). They are different. `Category` on an epic says which portfolio level it is (Epic, Feature, Capability and so on).
- **Asset types that can hold requirement text:** `Epic` (UI name Portfolio Item), `Story`, `Defect`, `Request`, `Goal` (strategic statements), `Theme` (grouping only); `Test` and `Task` hold acceptance criteria; `Issue` is a blocker, not a requirement. Abstract types can be queried (`PrimaryWorkitem`, `BaseAsset`).
- **Links.** Dependencies, blocking issues, linked requests and test-to-story links exist in the UI and as Data Mart bridge tables. **Their REST attribute names were not on any page I could read** (`memory` says `Dependencies` and `Dependants`). A request that names an attribute that does not exist on a type returns HTTP 400 and fails the whole type.
- **Moments.** `Data` reads return ids without a moment (`Story:1432`); write responses and `Hist` or `asof` results carry one (`Story:1211:1265`).
- **Authentication.** Access tokens ("recommended", `Authorization: Bearer`), Basic, and Windows integrated (NTLM). Tokens are created in the UI by a member who may create an application grant. **No read-only API role is documented**; a guest account cannot create applications, and an administrator can disable personal applications.
- **Rate limits.** SaaS only: a quota policy set by the vendor's operations team. HTTP 429 with a JSON body that names the limit and a `RetryAfter` value in seconds. No limit headers are described. On-premises: `not found`.
- **Errors documented:** 400, 401, 404 (also "secured from the user's view"), 405, 500. 403 is not documented.
- **The vendor asks for** a custom `User-Agent`, and exponential back-off on 5xx.

### 3.3 What a grid export is

HTML with a `.xls` extension, holding **only the columns visible in the view**, across pages. `Description` is not a default column; the user must add it first. It is the one route that works for a read-only guest, needs no token and works on SaaS and on-premises. The repo's `tabular` adapter used to claim only `.csv .tsv .xlsx .xlsm`, so a real grid export was never read.

### 3.4 Not built, and why

`api/asset` and webhooks write to the instance. Agility Connect is a different product's API. The activity stream may miss changes. The vendor's SDKs wrap the same calls and can write; the Python one was last released in 2018. `query.v1` is read-only by the vendor's description but is a POST with unresolved authentication; adding it needs a deliberate, narrow exception to the GET-only rule that only the repo owner can grant.

## 4. IBM DOORS 9.x, DOORS Web Access, DOORS Next

### 4.1 DOORS 9.x (classic)

- **DXL** (the scripting language), run inside the client or headless as `doors -batch <file>` (`read`, the DOORS 9.2 API manual). It still needs a client install and a login. Whether it uses a client licence: `memory`, yes.
  - The reference manual's contents list shows chapters on baselines, baseline sets, history and versioned links. Signatures could not be read.
  - Patterns confirmed only from community code on IBM's DXL archive (`read 3rd`): open a module with `read(name, false, true)` (name, display, standard view); loop `for o in entire m` with an `isDeleted(o)` guard to see soft-deleted objects; `identifier(o)` gives the prefix-number id; outgoing links by `for lnk in obj->"*"` and `target lnk`; link history exists only if the module enables it; trap errors with `noError()` and `lastError()`.
  - Memory: opening a module opens its link modules hidden and read-only and keeps them open; one forum reply recommends one module per batch job on large databases.
  - A string attribute truncates at 968 characters; use Text for long values (`read 3rd`, a community thread quoting product docs).
- **ReqIF** from **Project Properties > ReqIF definitions** (`read`, an IBM engineering wiki guide dated September 2025, written for DOORS 9.7.2.x and DNG 7.0.3 and 7.1). The view chooses which attributes go out. Pictures are not exported. Do not exchange the module-level "Description" attribute; avoid objects that carry both a heading and text; do not change enumeration structures between exports. It does not cover links, baselines or tables. A DOORS-to-DNG round trip changes types: DOORS 9 types are per module, DNG types are per project or component. An IBM engineer's own remark on the forum: ReqIF is the lowest common denominator.
- **Export to Word, Excel, HTML, RTF, text** exists (chapter headings `read`); what each includes is `not found`. PDF is not in the list.
- **OLE/COM automation:** the API manual covers a C API and a DXL server, not an OLE client. `memory`: `CreateObject("DOORS.Application")` needs a running Windows client. Not suitable here.
- **Licence terms on automated access:** `not found`.

### 4.2 DOORS Web Access (DWA) OSLC

IBM documentation for the DWA OSLC provider was **not found**; the following is community and release-note evidence, mostly DOORS 9.4/9.5 with DWA 1.5.

- Root services at `/dwa/public/rootservices` (the `/dwa/` segment varies by installation). The catalog tree is nested: projects and folders are nested catalogs and **each module is a service provider**. Requirement query at `/dwa/rm/oslc/query/<module URN>`. `Accept: application/rdf+xml` is required or HTML comes back.
- **Authentication is OAuth 1.0a**, with a consumer key an administrator registers and a browser approval step. One thread reports 401 with a form-login library and nobody confirms Basic.
- One response seen on the wire (a 2013 mailing-list post): the result container's `rdf:about` was not the requested URL, `dcterms:title` held "ID: object text", and no paging links or total were visible. A 2012 thread says the object hierarchy is not in the OSLC XML.
- DWA 9.7.2 adds a TRS 2.0 change feed (`read`, release notes).

### 4.3 DOORS Next (DNG), part of IBM Engineering Lifecycle Management

- **OSLC RM v2** (`read`, IBM Docs 7.0.3, plus forum threads):
  - Discovery: `GET /rm/rootservices` leads to `oslc_rm:rmServiceProviders`, a catalog of project areas; each project area's `services.xml` carries the query capabilities. Resource types offered on a 7.0.2 server (a forum thread): Requirement, RequirementCollection, folder, view, ReqIF definition.
  - Required headers: `OSLC-Core-Version: 2.0` and `Accept: application/rdf+xml`; without the version header the server may return limited RDF.
  - **A query needs a configuration** (a stream, baseline or global configuration). Send it as the `Configuration-Context` header or the `oslc_config.context` query parameter; when both are present the specification says the query string wins. One configuration per query. The Reportable REST API ignored the header in one forum report and needed the parameter. With global configurations on and none given, one report shows error CRRRS6540.
  - Query: `oslc.where`, `oslc.select`, `oslc.prefix`, `oslc.pageSize` (only a hint; the specification measures it in RDF statements), `oslc.paging`. Ordering is undefined unless `oslc.orderBy` is sent. Follow `oslc:nextPage`. `where` accepts only `and`. Encode `#` as `%23`.
  - What comes back: `dcterms:identifier` (the artifact number), `dcterms:title`, `dcterms:modified`, folder parent as `nav:parent`, `oslc:instanceShape`, link properties such as `oslc_rm:validatedBy`. Query results include **module and heading artifacts** as members (a filter on artifact format selects modules). "Modules inside a collection aren't available to OSLC consumers through GET": module structure is not in OSLC.
  - **The property that holds the primary text is not named on any page I could read.** `jazz_rm:primaryText` is `memory`. IBM's article says primary text must be XML on create.
  - The V2 service supports QUERY on OSLC links as well as on requirements (`read`).
  - Configuration listing: root services exposes `oslc_config:cmServiceProviders`; stream, component and baseline URIs look like `/rm/cm/stream/<id>`; a GET on a stream's baselines container lists baselines (forum threads).
- **Authentication for ELM** (`read` for the container and for the community walk-throughs): form login (default, awkward for code), Basic (needs TLS, "not recommended on Tomcat"), client certificate; OAuth 1.0a with a consumer an administrator registers, marks trusted and ties to a functional user (HMAC-SHA1 signature on **every** request, and the authorise step is a browser flow); and the Jazz Authorization Server, an OpenID Connect provider, where one community walk-through uses a client-credentials grant and a bearer token (example lifetime 7,200 seconds; the IBM page itself does not mention that grant). IBM says use of undocumented private APIs is not supported. **Licence terms for automated access were not found** (the IBM support statement is behind a login).
- **ReqIF** (`read`, IBM Docs 7.0.2): `.reqif` or `.reqifz`; needs the **Export ReqIF** permission and, to create a definition, **Manage ReqIF**; created under project or component properties, ReqIF tab; a module needs a view and only artifacts in the view go out; options include links, folders and DOORS-9 attribute restrictions; the export is asynchronous. Not exported: audit history, comments, reviews, users, view filter information, links to OSLC-integrated artifacts, embedded artifacts and images from a component linked through a global configuration. Migrating several components or several streams through ReqIF is not supported. Known quirks: a schema-validation failure on `colgroup` (IBM Support title); XHTML comments such as `<!-- x-tinymce/html -->` inside values crashed the Python `reqif` library until 0.0.48 (that project's issue tracker). A ReqIF programmatic API exists since 6.0.6.1 but its page is login-gated.
- **CSV / XLS / XLSX export** of a view (`read`, IBM Docs 7.0.2): follows the view's columns; module views always include `isHeading`, `parentBinding` and artifact type (removing `parentBinding` makes re-import fail); link columns must be in the view and, for base-artifact links, an administrator must set `EnableCoreBaseArtifactLinksWhenExporting`. Not exportable: collections, comments, reviews, team ownership, "used in modules".
- **Reportable REST** (`/rm/publish/resources`, `/modules`, `/text?metadata=schema`): XML, read-only, described only in forum threads because the wiki is login-gated. Module content is better read through `modules`; `rrm:section` and `rrm:depth` carry structure. It needs `oslc_config.context` as a parameter. A module of about 4,000 artifacts took over five minutes through `resources`.
- **Other IBM pieces** (listing only): client extension API, Module API, change-set API, TRS 2.0 (a change feed for incremental sync, request shape not found).

### 4.4 What each route carries

| Item | DOORS 9 DXL | DOORS 9 ReqIF | DWA OSLC | DNG OSLC | DNG ReqIF | DNG CSV | DNG Reportable REST |
|---|---|---|---|---|---|---|---|
| Identifier | Absolute Number, `identifier(o)` | not read | URN with `-O-` | `dcterms:identifier` | not read | column in the view | not read |
| Text | Object Heading, Object Text | heading and text should be separate | title holds "ID: text" | name plus primary text (XML) | XHTML values | primary text with markup | XML |
| Hierarchy | by loop order or level | not read (ReqIF has hierarchy) | **absent** | folder only; **no modules** | per module | `parentBinding`, `isHeading` | `rrm:section`, `rrm:depth` |
| Links | `obj->"*"` | optional | not found | outgoing properties and a links query | optional; OSLC-integrated dropped | link columns in the view | not found |
| Baseline / stream | baseline chapters exist | not read | not found | configuration context | not across streams | not covered | `oslc_config.context` |

Suspect flags: not found on any route.

## 5. MSOSA, Cameo, MagicDraw, Teamwork Cloud, SysML v2

**Names.** In the 2026x documentation the products are named Magic Software Architect (the modelling tool formerly called MagicDraw), Magic Cyber Systems Engineer (Cameo Systems Modeler), Magic Systems of Systems Architect (MSOSA) and Magic Collaboration Studio (Teamwork Cloud and its services). Dassault Systèmes sells the family as CATIA Magic (the former No Magic products; its product pages sit under `3ds.com/products-services/catia/products/catia-magic/`). The docs space carries all three modelling names in one version menu. I found no 2026x copy of the Requirements Modeler pages; the ReqIF pages read are 2021x R1/R2 and 2024x R3.

### 5.1 SysML 1.x routes

- **ReqIF export** (Cameo Requirements Modeler plugin; whether it needs its own licence was not found). File > Export To > Requirement Interchange Format (ReqIF) File. Choose **Elements** (a flat list) or **Specifications** (requirements plus hierarchy; needs packages with the «Specification» stereotype from the ReqIF Profile, which the tool offers to apply). A **flavor** names the target tool: MagicDraw, IBM Rational DOORS, Polarion, Teamcenter, Reqtify; choose MagicDraw if yours is not listed. Options under Options > Project > General > ReqIF: the element type created for exported objects, the relationship type created for exported relationships (singular), the output path for resources such as images, and whether to export all properties. Command line: `reqifexport project_descriptor=… reqif_file=… export_type=… elements=… source_tool_id=…`.
  **What it maps is not documented.** No page I read says which ReqIF attribute names carry the id, name and text, nor how the six SysML relationship kinds are written. The importer's post-processing rules show that the Element ID and Name can each be empty. The vendor's "Exchanging requirements with ReqIF" page says the custom mapping is described only in an image.
- **Requirement table export** (`.csv`, `.xlsx`, `.html`): default columns `#`, `Id`, `Name`, `Text`; custom requirement properties can be added as columns. Excel/CSV Sync matches rows by the ID column **if it is shown, otherwise by name**. Re-importing a file made by plain Export creates new elements. Delimiter and encoding of the CSV: `not found`.
- **XMI export:** UML XMI 2.5 (`.xmi`), MagicDraw native XML, Ecore, MOF XMI, Eclipse UML2 XMI. The project file `.mdzip` is, from 17.0.1, a zip of XMI **2.4** and other resources (entry names in the developer guide: `com.nomagic.magicdraw.uml_model.model`, `…shared_model`, backups of used projects named `proxy…`); before 17.0.1 it was one compressed XMI. The developer guide documents the layout and says nothing about external readers. A third-party UML tool states that it imports `.mdzip` from 17.0.1.
  Constructed shape (`memory`, to be checked against one real file): stereotype applications are **siblings** of the model element, pointing back with `base_Class`; the Requirement stereotype's properties are `Id` and `Text` (capitalised in the vendor's JavaDoc and requirement table; OMG's SysML 1.x names are lower case, so a reader must ignore case); relationships are `uml:Abstraction` elements with `client` and `supplier`, the kind being a sibling stereotype application (`DeriveReqt`, `Satisfy`, `Verify`, `Refine`, `Trace`, `Copy`). The six relationship properties on a requirement (`SatisfiedBy` and the like) are **derived**, computed from relationship elements, not stored.
- **Report Wizard** (`generate`, also `./generate.sh`): template-driven; output types html, rtf, odt, ods, odp, docx, xlsx, pptx, xml, txt, docbook; **CSV is not listed**. With `-server … -servertype twcloud -project …` it reads a Teamwork Cloud project without opening the application. It needs a template author and a modelling-tool install; licence use is not stated. It is the best-documented unattended server-side route for SysML 1.x projects in Teamwork Cloud that avoids ReqIF, and a site could use it. It is not a connector.
- **Open API batch** (a Java program extending `CommandLine`) can read tag values directly. It needs the modelling-tool install and a licence. Macros have no documented batch mode.
- **Teamwork Cloud REST (OSMC):** JSON-LD **at the EMF level**: an element has `@id`, `kerml:esiID`, `@type` (for example `uml:Class`) and its attributes under `kerml:esiData`; a tag value is a **separate element** (`uml:StringTaggedValue`). Authentication: `GET /osmc/login` with Basic starts a session whose cookies you reuse (each call without the cookie opens a new session and **uses a licence** until the 15-minute timeout); or **`Authorization: Token <token>`** (a token or a personal access token; not `Bearer`); or OAuth 2.0 `Bearer`. Tokens need administrator set-up. The list of endpoints (projects, workspaces, revisions) was in the Swagger I could not read.
- **Teamwork Cloud OSLC API:** Architecture Management resources only; Requirements Management is not mentioned; "querying services are not supported"; OAuth 1.0a; port 8443 since 2022x R2.
- **Cameo DataHub** is a plug-in, not a service. Its CSV data source **writes changes back** and a renamed column corrupts it. Never point a watcher at a live DataHub CSV.
- **Cameo Collaborator** publishes documents; no data-export API was found.

### 5.2 SysML v2

- Teamwork Cloud 2026x states that its SysML v2 API "fully conforms" to the OMG Systems Modeling API and Services standard (REST/HTTP). Swagger at `https://<server>:8443/sysmlv2-api/swagger-ui/index.html`. Service groups: project, element navigation, project and data versioning (tag, branch, commit), query, external relationship, project usage. How it authenticates, and which earlier releases ship it, are `not found`.
- **OMG API 1.0** (formal, September 2025; `read`, the machine-readable OpenAPI): `/projects`, `/branches`, `/tags`, `/commits`, `.../commits/{id}/elements` (GET), `.../roots`, `.../elements/{id}/relationships`, `/query-results` (**GET and POST**). `GET …/elements` takes `excludeUsed` and the cursor parameters `page[size]`, `page[after]`, `page[before]`. The specification text says responses carry a `Link` header with `rel="next"`; the OpenAPI file does not declare it; whether Teamwork Cloud sends it is not stated.
- The query service does not support derived properties unless the project is indexed first (Admin UI, an Elasticsearch-based index).
- **Textual API Services** (2026x R1, Enterprise edition) return a namespace as SysML v2 text; the path is not on the page.
- **Desktop export:** File > Export To > SysML v2 Textual Notation writes **a folder of `.sysml` files**, one per selected namespace, and may use shortest qualified names, so a reference can be ambiguous across packages. Import accepts a directory.
- **v1 to v2 migration** (about 20 % of the metamodel): a requirement becomes a requirement usage; satisfy becomes a **satisfy requirement usage**; derive, verify and refine each become "**dependency plus metadata**", so the kind is in the metadata, not in the type name.
- **SysON** (open-source): base path `/api/rest/`; commits are not modelled, so the project id serves as the commit id; many project attributes are marked unsupported.
- **JSON element property names were not visible in anything I could read** (`declaredName`, `declaredShortName`, `owner`, `documentation` and so on are `memory`).

## 6. Other tools

| Tool | What to read | What the vendor says | Verdict |
|---|---|---|---|
| **Jira** (Cloud, Data Center) | REST search. Cloud: `GET /rest/api/3/search/jql` with `jql` and `nextPageToken` (no `total`; pages must be fetched in order; the old `/search` is removed). Data Center: `GET /rest/api/2/search` with `startAt`, `maxResults`, `total`; a 10,000-result window, page by `id > last` beyond it. | A link has a type with `inward` and `outward` names and carries **either** `inwardIssue` **or** `outwardIssue`; the API does not interpret direction. Description is Atlassian Document Format JSON on v3. CSV export **omits inward links and splits outward links into one column per link type**. No native ReqIF. | Connector built. Needs an explicit direction map. |
| **Polarion** | REST v1 `projects/{p}/workitems`, `fields[workitems]`, `include`, `page[number]`; links as separate resources: `linkedworkitems` (outgoing, with a `role`), `backlinkedWorkItems` (incoming). | REST is **off until an administrator enables it**. **Collection GETs have no default sort, so paged results can be inconsistent.** Rich text comes back as source, not HTML. Links stay inside a project unless `include` is used. Document structure (parts) was `not found`. | Connector built. Always sends a sort. |
| **Jama Connect** | REST v1 (`/rest/v1`). Lists return `meta.pageInfo` (default 20, maximum 50). Relationships: `GET /relationships?project&lastId&maxResults` (up to 1,000). Baselines: versioned items and versioned relationships per item. | OAuth client credentials need a **POST** to `/rest/oauth/token`, so the GET-only kit cannot mint the token: it is an `auth_hook` job. Basic works only without SSO. Over 10 requests per second returns 429. A Named Creator licence is needed. `/relationships` returns current relationships, not versioned ones. | Connector built; the token comes from a hook. |
| **Codebeamer** | REST v3 items, `POST /v3/items/query`; native ReqIF 1.0.1+ with references and associations (current revision only). | The vendor's Swagger usage policy bars "extracting data for AI model training or building data sources" without written permission, and says unlicensed API use breaches the user agreement. | **No connector.** ReqIF only until written confirmation. Read the sentence before any Codebeamer data reaches a model. |
| **Sparx Enterprise Architect** | A DBMS repository (SQL Server, MySQL, PostgreSQL, Oracle) shares the file schema; element class maps to table `t_object`; connectors have `ClientID` (source) and `SupplierID` (target). | Automation API is COM, Windows-local and write capable. CSV export is documented for elements, connectors not stated. DBMS repositories need Corporate, Unified or Ultimate edition. `t_connector` column names are `memory`. | A shipped query pack for the `sql` adapter. |
| **Rhapsody** | In-process COM or Java API; OSLC links through Rhapsody Model Manager. | No REST found. Requirements usually stay in DOORS and are linked, not copied. ReqIF through a partner's tool. | No connector. |
| **Capella / Arcadia** | `.capella` and `.aird` EMF files; an open-source Python reader exists. | "Requirements viewpoint cannot export ReqIF by itself" (forum). | No connector yet. |
| **Teamcenter, Windchill** | ReqIF through each vendor's requirements connector. | No public REST reference for requirements found. | `reqif`. |
| **Doorstop, StrictDoc** | Doorstop: one YAML file per item, export to CSV / XLSX with links. StrictDoc: `.sdoc`, exports JSON and ReqIF. | | `tabular` and `reqif` already cover them. |

## 7. Policy and licence notes, per vendor (read before shipping a connector)

A connector reads a vendor's system. The vendor's terms can restrict how. Nothing here is legal advice, and the owner of each instance has to decide.

| Vendor | What I found | What I did not find |
|---|---|---|
| Atlassian | The Acceptable Use Policy bars robots that send more requests than a person could and access outside "publicly supported interfaces". API-token rate limits apply from 22 November 2025 (numbers not given); app quotas are points-based from March 2026; 429 and 5xx carry `Retry-After`. | Numbers for API-token limits. |
| PTC (Codebeamer) | The data-extraction clause quoted in section 6. | Whether a customer's own read of its own data is covered. |
| Digital.ai | SaaS rate limiting by quota policy, 429 body with `RetryAfter`. | A read-only API role; a licence statement on automated reads. |
| IBM (DOORS, DNG) | "Use of undocumented private APIs is not supported." A DNG consumer must be approved by an administrator. | Licence terms for programmatic access (login-gated). |
| Dassault (Teamwork Cloud) | REST sessions use a licence until they time out. | Which role is least privilege; plugin licence bundling. |
| Jama | A Named Creator licence is needed for API access; 10 requests per second. | |
| Siemens (Polarion) | REST is off by default; endpoint and item permissions are separate layers. | Licence terms for REST. |
| Sparx | The EULA excerpt bars reverse engineering and working round technical limits. | Anything about direct database reads. |

Standing rule for every connector in this repo: **check the vendor's API terms for data-extraction and AI clauses before shipping it, and say in the connector's docs that you did not check them if you did not.**

## 8. Claims in this repo that the research found wrong, and what happened to each

| # | Where | It said | The vendor documentation says | Status |
|---|---|---|---|---|
| 1 | `reqin/INPUT_LAYER.md` section 5 | Jira, Polarion and Jama export paths "already work today" | Jira CSV drops inward links and scatters outward ones; Polarion and Jama have ReqIF only through a side tool | corrected, connectors added |
| 2 | `reqin/CONNECTORS.md` section 6 and `agility.py` | Agility `where` filter `AssetState!='255'` | `!=` is not shown in any rest-1.v1 `where` example; deleted items are hidden anyway | corrected |
| 3 | `agility.py` | JSON is the documented format; any other body is "a login page" | The portal documents XML; JSON needs the `Accept` header | XML fallback added |
| 4 | `agility.py` | one `select` list for every asset type | an unknown attribute on one type is a 400 for the whole type | per-type select |
| 5 | `agility.py` | export route is "xlsx/csv" | the grid export is HTML in a `.xls` file | HTML-table reader added |
| 6 | `connect.py` | reads only a `Retry-After` header | Agility's 429 puts `RetryAfter` in the JSON body | body read |
| 7 | `connect.py` `token_env` | always `Authorization: Bearer` | Teamwork Cloud tokens use the word `Token` | `token_scheme` option |
| 8 | `sysml_api.py` | never passes `excludeUsed`; every `Dependency` is `trace`; `satisfy` not read | OMG `excludeUsed`; migration writes derive, verify, refine as dependency plus metadata; satisfy is its own type | corrected, with a "types seen but not mapped" note |
| 9 | `reqin/CONNECTORS.md` section 3 | the query service "is a POST" | `/query-results` is GET **and** POST; derived-property queries need indexing | wording corrected; still not used |
| 10 | `mdzip.py` and `INPUT_LAYER.md` | "no documented layout" | the layout is documented; there is no reader contract | wording corrected; the stub is gone and `sysml1_xmi.py` reads `.xmi` and `.mdzip` (fixture-tested only) |
| 11 | `sysml_text.py` | reads one `.sysml` file | the desktop export writes a folder | directory accepted, ambiguous names reported |
| 12 | `oslc_rm.py` | "without a configuration you read the server's default" | the specification lets a server have none and fail; IBM forum answers say a query needs one | corrected; the configuration is sent as a header and as a query parameter (`configuration_mode` picks one), and a note says when none was given |
| 13 | `oslc_rm.py` | takes every member | module and heading artifacts arrive as members | not filtered by the connector: `profiles/oslc_rm.yaml` shows how to drop them with `where` |
| 14 | `reqif_adapter.py` | first `*.reqif` in a `.reqifz`; no minimum `reqif` version | XHTML comments crash `reqif` before 0.0.48; a DNG export is grouped by module | minimum version `reqif>=0.0.48` (a floor, not a pin to one version); several files read; comments are removed before the library sees the file, because a comment placed first inside an XHTML value still crashed version 0.1.0 (a test shows it) |
| 15 | `INPUT_LAYER.md` DOORS row | RIF definition "in the database properties" | Project Properties > ReqIF definitions | corrected |
| 16 | `export_requirements.dxl` | `read(path, false)`; no error trapping; no links; deleted objects neither skipped nor marked | community code uses the three-argument read, `noError()`, `isDeleted` | rewritten read-only |
| 17 | `tabular.py` | no profile for the DNG view export | module views carry `isHeading` and `parentBinding` | profile added |

"Status" is filled in from what the commit that adds this page actually contains. Anything marked "corrected" or "added" is tested against a fake only.

**Found by testing, not by the vendor research.** The check that refuses a DOCTYPE or ENTITY declaration looked only at the first 64 KB of a file in three places (`safe_xml`, the ReqIF reader and the new XMI reader), so a declaration placed behind a longer comment got through; in the XMI reader the parser also reported the root element only after the input ended. All three now search the whole input (`has_dtd` in `connect.py`; the XMI reader checks on the first event as well), and each has a test with the declaration hidden behind a comment longer than 64 KB. A file that merely mentions the word in a comment is now refused too, which is the safe way round. Separately, the count "N links point outside this import" counted only links whose **target** was outside; a design element that satisfies a requirement is the usual outside end and it sits at the source, so it went uncounted. Either end now counts.

## 9. What a person with a real instance should send back

Anonymised and fictional-ised **before** it leaves your machine, and never with a real programme, project or person name in it. These captures replace most of the `memory` items above.

- **DOORS 9 and DNG:** one `.reqifz` from each; one DNG module-view CSV; from a DNG server, the four OSLC responses `rootservices`, a project `services.xml`, one query page and one requirement, with the configuration you used.
- **MSOSA:** one `.reqif` per flavor you actually use; one requirement-table CSV or XLSX; one XMI or `.mdzip` model entry with a few requirements and each relationship kind.
- **Agility:** `meta.v1/<Type>` for Story, Epic, Defect, Request and Test (it needs no token) and one page of `rest-1.v1/Data/Story` in both JSON and XML; one grid export.
- **Jira, Polarion, Jama:** one page of each search or list response and one link of each kind.
- **Teamwork Cloud:** the response of the SysML v2 API's project list and one elements page; how it authenticated; whether it sent a `Link` header.

## 10. Not answered

- **"DESE"** appeared in the request that started this work. It is read here as Dassault Systèmes, the company behind the "Magic" line (MSOSA, Magic Cyber Systems Engineer, Magic Software Architect, Magic Collaboration Studio, sold as CATIA Magic), which section 5 covers. If it was meant to name a different tool, say which and the same research can be done.
- Everything in the vendors' blocked pages (section 1).
- Whether any of these routes is allowed by your licence.

## 11. Sources

Pages are cited by title and address as opened. Third-party pages are marked.

**Digital.ai Agility.** `docs.digital.ai/agility/docs/` (developer library): endpoints, rest-1-v1-endpoints, query, tour-query-v-1, api-authentication, access-token-authentication, authorizing-external-application-access, http-reference, http-error-codes, what-is-api-rate-limiting, meta-api, meta, getting-started-with-the-api, queries, sort, attributes, assets, xml-response, learn-by-example-history-queries, undelete-asset, data-source-objects, dimension-tables-reference, data-mart, how-to-run-the-datamart-etl-or-dataloader, installing-data-mart-etl, system-requirements, exporting-grid-data, export-templates-to-excel, export-requests-to-excel, exporting-closed-work-items, export-custom-reports, export-and-print-reports, using-grids, utility-endpoints, get-an-sdk, managing-dependencies, creating-a-new-portfolio-item. The vendor's GitHub API docs (`versionone.github.io/api-docs/`) and examples (`github.com/versionone/api-examples`). Package pages: PyPI `v1pysdk`, NuGet `VersionOne.SDK.APIClient`, npm `v1sdk`, Maven Central `VersionOne.SDK.Java.APIClient`. Third party: a Google Groups thread (`groups.google.com/g/versionone-dev`), a Planview connector page (`success.planview.com`), a Blink Ops integration page.

**IBM.** `ibm.com/docs` DOORS Next 7.0.3 "RM as OSLC service provider"; IBM Docs 7.0.2 `t_reqif_intro.html`, `t_export_reqif.html`, `c_export_csv.html`, `t_export_artifacts_modules.html`; 7.2 `c_configuring_oauth.html`; `ibm.com/support/pages` nodes 611407 and 6234954 and `doors-and-doors-web-access-97`; DOORS 9.2 manuals at `public.dhe.ibm.com/software/rationalsdp/documentation/product_doc/DOORS/version_9-2/` (`dxl_reference_manual.pdf` contents only, `doors_api_manual.pdf`, `managing_doors.pdf`, `using_doors.pdf`); `jazz.net` library articles 75, 1197, 1382, wiki `Deployment/DoorsDNGReqIFExchangeRoundTrip` and `Deployment/ELMProductAPILanding`, forum threads on DNG OSLC, configuration context and Reportable REST, DXL archive pages 41, 1830, 2271, 3296 and 3351. Standards: OSLC Query 3.0 and OSLC Config Management (OASIS OSLC OP). Third party: Eclipse Lyo mailing list and forum threads, `github.com/strictdoc-project/reqif` issue 205, a community blog on OAuth 1.0a and OIDC for ELM, a test-equipment vendor's article on DWA OAuth.

**Dassault / No Magic.** `docs.nomagic.com`: Cameo Requirements Modeler pages (exporting requirements, importing ReqIF, requirement table, generating requirement reports), the ReqIF command-line pages, "Sync with Excel or CSV files", "Importing data from Excel or CSV files", supported file types, the developer guide (MagicDraw file format; Teamwork Cloud REST: model manipulation, reusing a session, token and personal access token authentication, OAuth 2.0, OSLC API), Report Wizard command-line pages, SysML v2 plugin pages (textual notation import and export, migration from SysML v1 to v2, standard SysML v2 REST API), Cameo DataHub pages, release notes; `jdocs.nomagic.com` JavaDoc for `CommandLine` and `SysMLProfile`. Standards: OMG Systems Modeling API and Services 1.0 and its `OpenAPI.json`; the SysML v2 pilot implementation and release repositories; the SysON documentation.

**Atlassian, Siemens, Jama, PTC, Sparx, others.** Jira: Atlassian Confluence KB "Run JQL search query using Jira Cloud REST API", the issue-linking model page, the Data Center search example, the KB on the 10,000-result window, personal access tokens, "Export search results", the Acceptable Use Policy, the rate-limit blog posts; Atlassian Jira issues JRACLOUD-66797 and JRACLOUD-62217. Polarion: `developer.siemens.com/polarion` (access, enable, authentication, authorization, advanced concepts, limitations and known issues); `extensions.polarion.com` extensions 495 and 196. Jama: `dev.jamasoftware.com/cookbook/`, `support.jamasoftware.com` articles on sample API calls, OAuth token, baseline items, Data Exchange; `help.jamasoftware.com` pages on the REST API, exporting documents, relationships, API credentials. Codebeamer: `support.ptc.com/help/codebeamer` developer-guide, Swagger best-practice, release-note and ReqIF user-guide pages. Sparx: `sparxsystems.com/enterprise_architect_user_guide` pages on the repository, element, connector, CSV, XMI and licence. Rhapsody, Capella, Teamcenter, Windchill, Doorstop, StrictDoc: the vendors' or projects' documentation pages as listed in the research notes; a Capella forum thread on ReqIF.
