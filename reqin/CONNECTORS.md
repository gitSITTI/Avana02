# Connectors: reading live systems, and finishing each one against yours

`reqin` reads files (CSV, Excel, ReqIF, SysML text, MSOSA/SysML 1.x model files, SQL, Word, PDF) and, through the connectors on this page, six live systems.
Every connector is **read-only**, runs **inside your network** with a **read-only service account**, and is built so that your agent can
do the last mile: the parts only your real server can settle are named settings, not buried code.

> **How far each one has been proven.** `reqin connectors` prints this table from the code.
>
> | Connector | Source | Proven against | Not proven |
> |---|---|---|---|
> | `sysml_api` | SysML v2 REST API (Teamwork Cloud / Magic Collaboration Studio, SysON, Pilot Implementation) | An in-memory fake built from the public API docs and the OMG spec | A real server. Paging style, JSON property names, branch/head lookup, relationship properties |
> | `oslc_rm` | OSLC RM: DOORS Next, and DOORS 9.x through DOORS Web Access | An in-memory fake built from the OASIS OSLC Query / RM / Config specs and IBM's published discovery steps | A real server. The sign-in (OAuth / form / OIDC), the DNG text property, rootservices details on your version |
> | `agility` | Digital.ai Agility (VersionOne) REST Data API | An in-memory fake built from the published API docs | A real instance. Relation shape inside `Attributes`, your attribute names, your sign-in |
> | `jira` | Jira Cloud and Data Center / Server REST: issues and issue links | An in-memory fake built from Atlassian's documented shapes | A real site. Field ids and names, link types and their direction, the Cloud paging end (`isLast`), what your JQL returns |
> | `polarion` | Siemens Polarion REST v1: work items and their linked work items | An in-memory fake built from Siemens' documented shapes | A real server. REST is off by default; the parameter names `page[size]`, `query`, `sort` and the `links.next` / `meta.totalCount` answers are recalled, not confirmed; which end a role such as `parent` points at |
> | `jama` | Jama Connect REST: items and relationships | An in-memory fake built from Jama's documented shapes (the 50-item limit included) | A real instance. The `abstractitems` listing, the `$<type id>` field-name suffix, the direction of `fromItem` and `toItem`, the sign-in token |
> | `sysml1_xmi` | A SysML 1.x / UML model as XMI, or an MSOSA / Cameo project file (`.mdzip`) | **Fixtures written from the vendor's documentation (maturity `fixture-tested`)**, never a real project | A real MSOSA file. Namespaces, how a stereotype application sits next to its class, how documentation and relationships are stored |
> | `sql` with the EA pack | A Sparx Enterprise Architect DBMS repository, through `connectors/ea/*.sql` | A tiny made-up SQLite database shaped like the recalled tables | A real repository. The table and column names are **recalled, not read**; check them first (see section 11) |
> | DOORS 9 export | `connectors/doors9/export_requirements.dxl` writes a CSV; `tabular` reads it | The CSV side, in tests | **The DXL has never run in DOORS** |
>
> `fake-server-tested` means exactly that: the connector's logic (paging, joining, hierarchy, safety) works against a fake of the documented
> API. It does **not** mean a real server answers the same way. `live-verified` is reserved for a person who ran the connector on the
> real system and checked the output against the source; nobody has, for any connector here.

## 1. Rules every connector keeps (enforced in `reqin/connect.py`, not left to each author)

| Rule | How it is enforced and tested |
|---|---|
| **GET only** | `ReadOnlyHttp` has no write method. `test_connect` runs a real HTTP server that records every verb. |
| **TLS always verified** | No switch exists to turn it off. A private CA works with `ca_bundle=` or `REQIN_CA_BUNDLE`. Tested with a real HTTPS server and a throwaway CA. |
| **Secrets from environment variables** | `token_env=NAME`, `basic_user_env`/`basic_password_env`, `cookie_env`, or your own `auth_hook`. Values are scrubbed from every error and audit line. |
| **No credential forwarding** | A redirect to another host (or https to http) is refused. |
| **Bounded** | Response size, request count (`max_requests`) and page count (`max_pages`) are capped. |
| **Paging that cannot truncate silently** | A server that repeats a page or a `next` link raises an error. It never loops, and never quietly returns half. |
| **Audit** | `--audit FILE` writes every request (method, URL without secrets, status, bytes). This is what you hand to IT security. |
| **Nothing dropped silently, locator on every record** | The same pipeline invariant as every file adapter. `reqin.testing.check_adapter` asserts it. |

## 2. First contact with a real system (any live connector)

A person does steps 1 to 3; an agent can do 4 to 8.

1. **Approval.** Get IT security and your export-control reviewer to approve running this inside your network, and a **read-only service account**. The code is a backup to that account, not a replacement. Nothing in this repo assumes anything about classification.
2. **Network placement.** Run `reqin` where it can reach the server (a container on the same network). Cloud-hosted tools generally cannot.
3. **Credential.** Put it in an environment variable on that machine. Never in a file, a command line or the repo.
4. `reqin sample <uri> --opt ...`: reads **one page**, prints the notes, the fields with example values, the first records exactly as handed over, and the requests made. Compare with the fake in `tests/live_cases.py` and note every difference.
5. Fix differences with **options first** (`keys`, `req_types`, `select`, `link_map`, `page_style`, `paging`). Only change code if no option can express it, and then add a test to the fake first.
6. `reqin propose` then confirm the profile (see the connector's profile file). Set `namespace` to your project key and keep it stable: it is part of every requirement's MID.
7. `reqin import <uri> --profile ... --opt ... --audit audit.jsonl --out reqs.jsonl`. Read the report: `invariant_ok`, rejected (with reasons), filtered, unclaimed fields, warnings.
8. Hand `audit.jsonl` to IT. If your reviewer approves, an anonymised excerpt may go in `reqin/tests/fixtures_approved/` (see its `APPROVALS.md`); the real-data guard blocks everything else.

## 3. SysML v2 REST: `sysml_api`

**Source.** The standard Systems Modeling API. Teamwork Cloud serves it at `https://<server>:8443/sysmlv2-api/` (Swagger UI at `.../swagger-ui/index.html`, per the Dassault Systèmes / No Magic docs; the API groups are project, branch/tag/commit, element navigation, query, external relationship, project usage). SysON serves it at `/api/rest`.

```bash
export TWC_TOKEN=...      # however your server issues a read-only token
reqin sample sysml+https://twc.example.com:8443/sysmlv2-api --opt project_name="My Model" --opt token_env=TWC_TOKEN
reqin import sysml+https://twc.example.com:8443/sysmlv2-api --opt project_name="My Model" --opt token_env=TWC_TOKEN \
      --profile profiles/sysml_api.yaml --audit audit.jsonl --out reqs.jsonl
```

| Option | Meaning |
|---|---|
| `project_name` / `project_id` | Which project. A wrong name lists the projects that exist. |
| `branch` / `commit_id` | Default: the project's default branch, then that branch's head commit. If the server gives no branch, the project id is used as the commit id (SysON does this) and the discovery note says so. |
| `page_size`, `paging`, `page_style` | `paging=auto` follows `Link: rel="next"`, then falls back to `page[after]=<last id>`; `link`, `cursor`, `none` force a style; `page_style=underscore` for servers that take `page_size`. |
| `req_types`, `link_types`, `keys` | Which `@type`s are requirements; which relationship types become links (`{"Dependency":"trace"}`); the JSON property names. |

**What the connector does.** Streams `GET /projects/{id}/commits/{commit}/elements`, keeps requirement elements, joins `Documentation` elements (by `owner`, or by the requirement's own `documentation` list) into the statement text, sets the parent when the owner is another requirement, turns configured relationship types into links, and keeps every other plain property as `prop.<name>`.

**Verified vs assumed.**

| Verified in public docs | From the spec, not seen on a live server |
|---|---|
| `GET .../commits/{commitId}/elements` returns a JSON array; `/projects`; `@id`, `@type`, `declaredName`; SysON uses the project id as the commit id; TWC base path and service groups | `defaultBranch` on a project and `head` on a branch; the `Link` header and `page[size]`/`page[after]` (the Python client lists `page_size`/`page_after`); `owner` on elements; `Documentation.body`; `client`/`supplier` on `Dependency` |

**Your agent finishes it by:** (1) running `reqin sample`; (2) reading the notes: if it says *"no element has a type in [...]"* it lists the types the server uses, so set `req_types`; (3) checking the paging notes and the audit URLs, then setting `paging`/`page_style` explicitly; (4) checking where the human requirement ID lives (`declaredShortName`? a metadata attribute? the qualified name?) and editing `uid` in `profiles/sysml_api.yaml`; (5) deciding which relationships are traces and setting `link_types`; (6) if projects have millions of elements, discussing server-side filtering with the server's admins: the Query service exists but is not used here because it is a POST.

**Agent prompt.** "Finish the `sysml_api` connector against our Teamwork Cloud. Read `reqin/CONNECTORS.md` sections 1 to 3 and `src/reqin/adapters/sysml_api.py`. A human gives you `TWC_TOKEN` and approval. Run `reqin sample` and `reqin import --audit`. Change only options and `profiles/sysml_api.yaml` unless an option cannot express the difference; if code must change, first change the fake server in `tests/live_cases.py` to return the real SHAPE (fictional content), see the test fail, then fix. Never print or commit the token or any real requirement text. Keep `maturity` as `fake-server-tested`. Report what you could not confirm."

## 4. DOORS Next and DOORS 9.x via OSLC RM: `oslc_rm`

**Source.** OSLC Requirements Management 2.x. DOORS Next serves it under `https://<server>/rm/`; DOORS 9.x offers OSLC through DOORS Web Access (assumed, not checked here). Needs `pip install "reqin[oslc]"` (rdflib).

```bash
export DNG_COOKIE='JSESSIONID=...'     # pilots only; see "sign-in" below
reqin sample oslc+https://dng.example.com/rm/rootservices --opt project="My Project Area" --opt cookie_env=DNG_COOKIE
```

| Option | Meaning |
|---|---|
| `project` | The project area (service provider) title. Omitted with several present: the error lists them. |
| `configuration` | A stream/baseline URI, sent as the `Configuration-Context` header. **Without it you read the server's default configuration.** |
| `where`, `prefix`, `select`, `page_size` | OSLC query pass-through (`oslc.where`, `oslc.prefix`, `oslc.select` default `*`, `oslc.pageSize`). |
| `catalog`, `service_provider`, `query_base` | Skip discovery if you already know a URL. |
| `links`, `link_map`, `prefixes`, `fetch_members`, `resource_type` | Which `oslc_rm` link properties become links (default: requirement-to-requirement ones), their direction, extra prefixes, per-member fetch, the resource type. |

**What the connector does.** Rootservices, then the catalog, then the project's services, then the `oslc:queryCapability` for `oslc_rm:Requirement`, then the paged query, following `oslc:nextPage` and checking `oslc:totalCount`. Fields are named `prefix:property` (`dcterms:identifier`, `dcterms:title`, `jazz_rm:primaryText`, ...). Links use the OASIS RM vocabulary with the right direction (`satisfiedBy` means the *value* satisfies *this*), and the same fact stated from both ends is emitted once.

**Verified vs assumed.**

| Verified in public specs and docs | Not seen on a live server |
|---|---|
| RM namespace and the Requirement link properties (OASIS RM 2.1); OSLC Query paging (`oslc:nextPage`, `oslc:totalCount`, `rdfs:member`, `oslc.pageSize` as a hint); `Configuration-Context` header and `oslc_config.context` parameter (OSLC Config Mgmt); DNG discovery chain and the headers `OSLC-Core-Version: 2.0` / `Accept: application/rdf+xml` | The property from rootservices to the catalog on **your** version (we look for any property named `rmServiceProviders`; `catalog=` overrides); `jazz_rm:primaryText` as the rich text (`dcterms:description` is the fallback); how your server signs you in |

**Sign-in is the part you must finish.** A Jazz article from 2013 said OSLC consumers "must implement and follow the OAuth protocol"; I did not check whether your version still requires that, and it may differ (Basic, form login or an SSO in front). OAuth, form login and OIDC are **not** built in, because they depend on how your Jazz server is set up. Options: `basic_user_env`/`basic_password_env` (works only if your server accepts Basic for OSLC), `cookie_env` (paste a session cookie from an authenticated session: good for a pilot, expires), or `auth_hook=my_pkg.login:headers` returning the headers your SSO needs. A login page is detected and reported as such.

**Your agent finishes it by:** (1) getting a working sign-in via `auth_hook` and testing it with `reqin sample`; (2) confirming the catalog/service-provider discovery or giving `query_base`; (3) choosing the `configuration` (stream or baseline) so results are reproducible; (4) confirming the text property and, if statements live in the Name, adding `dcterms:title` as a third source in `profiles/oslc_rm.yaml` and filtering headings with `where`; (5) checking links and `link_map`; (6) for DOORS 9.x, checking whether DWA exposes the same shapes, otherwise using the DXL route below.

**Agent prompt.** "Finish the `oslc_rm` connector against our DOORS Next. Read `reqin/CONNECTORS.md` sections 1, 2 and 4 and `src/reqin/adapters/oslc_rm.py`. First build the sign-in as an `auth_hook` in a separate private package (never in this repo, never print a credential). Then `reqin sample` and compare with `oslc_server()` in `tests/live_cases.py`; update that fake to the real SHAPE with fictional content before changing code. Pin a `configuration`. Confirm the text and identifier properties and edit `profiles/oslc_rm.yaml`. Report anything you could not confirm. Keep `maturity` as `fake-server-tested`."

## 5. DOORS 9.x without OSLC: the DXL export script

`connectors/doors9/export_requirements.dxl` opens **one module read-only** (`read(path, false)`), loops its objects and writes a CSV with the columns `profiles/doors_csv.yaml` reads. Run it in DOORS (Tools > Edit DXL), then `reqin import export.csv --profile profiles/doors_csv.yaml`.

**It has never run in DOORS.** It follows patterns in public DXL examples (jazz.net/dxl) and a test scans it for calls that could change a database (edit, share, save, delete, create, system...). Expect a compile error or two the first time. **Your agent finishes it by:** setting `modulePath` and `outPath`, adding extra attribute columns one at a time (each needs one HEADER entry and one `putField` line), adding a `Links` column if you want traces, and mirroring any change in `profiles/doors_csv.yaml` (the test `test_the_columns_the_script_writes_are_the_columns_the_profile_reads` fails if they drift). If you also have ReqIF export, that route is already supported (`profiles/msosa_reqif.yaml`).

**Agent prompt.** "Finish `connectors/doors9/export_requirements.dxl` for module `<path>`. You cannot run DOORS; a human will run it and paste back only the DXL error text (no requirement text). Keep it read-only: only `read()`, never `edit`/`share`/`save`/`delete`/`create`. Keep `HEADER`, `writeRow` and `profiles/doors_csv.yaml` in step; `pytest tests/test_doors9.py` must stay green."

## 6. Digital.ai Agility: `agility`

**Two routes.** (a) If you already work from Agility **exports** (xlsx/csv), use the tabular adapter with `profiles/agility_export.yaml`; no connector needed. (b) The REST connector reads Epics, Stories and Defects directly.

```bash
export AGILITY_TOKEN=...      # an Agility access token (sent as Authorization: Bearer)
reqin sample agility+https://www.example.com/MyInstance --opt token_env=AGILITY_TOKEN --opt where="Scope.Name='My Project'"
```

| Option | Meaning |
|---|---|
| `asset_types` | Default `Epic,Story,Defect`. |
| `select` | Attributes to read (default `Number,Name,Description,Scope.Name,Status.Name,AssetState,Super,Dependencies,ChangeDateUTC`). |
| `where` | Agility where-clause, passed through (e.g. `AssetState!='255'` to exclude deleted). |
| `parent_attr`, `link_attrs`, `select_param`, `page_size` | The parent attribute (`Super`), which attributes become links (`{"Dependencies":"trace"}`), the select parameter name (`sel`), page size. |

**What the connector does.** `GET <base>/rest-1.v1/Data/<Asset>?sel=...&where=...&page=<size>,<start>` with `Accept: application/json`, paging with the documented `total`/`pageStart`. The asset id's trailing *moment* (it changes on every edit) is stripped, so a requirement's identity survives edits. `Super` becomes the parent; `Dependencies` become links; the Description is HTML and the profile strips it. The `query.v1` endpoint is a POST and is deliberately not used.

**Verified vs assumed.**

| Verified in the public API docs | Not seen on a live instance |
|---|---|
| `Data/<Asset>` + `Accept: application/json`; the `{"_type":"Assets","total","pageSize","pageStart","Assets":[...]}` shape; `Attributes` as `{name, value}`; `page` as size,start; `Authorization: Bearer <access token>`; the AssetState codes; Story/Epic/Scope/Super/Number/Name | The shape of a *relation* value (we accept `{"idref": "Epic:12"}`, a list of those, or a bare `Epic:12`); whether `Description`, `Dependencies`, `Status.Name` exist under those names on your instance; whether your instance puts stories and defects at one level (your dashboard says they are) |

**Honest caution.** Agility work items are not always requirements. The profile keeps items with a Description and sends the rest to *filtered* with a count, so you can see what was left out and decide.

**Your agent finishes it by:** (1) `reqin sample`, then fixing `select` to attributes that exist (the notes and an error will say if the shape is wrong); (2) checking the relation shape in the sample and, if different, adjusting `_idrefs` in `adapters/agility.py` after changing the fake first; (3) deciding which asset types and which `where` define "requirements" for your program; (4) setting `link_attrs` for upstream/downstream dependency attributes; (5) editing `profiles/agility_api.yaml` (or `agility_export.yaml` with the real column headers).

**Agent prompt.** "Finish the `agility` connector against our Agility instance. Read `reqin/CONNECTORS.md` sections 1, 2 and 6 and `src/reqin/adapters/agility.py`. A human gives you `AGILITY_TOKEN`. Run `reqin sample` with a `where` that limits it to one project. Compare with `agility_server()` in `tests/live_cases.py`; update the fake to the real SHAPE (fictional content) before changing code. Decide with the human which items count as requirements and encode that in `profiles/agility_api.yaml`. Keep `maturity` as `fake-server-tested`."

## 7. Jira: `jira`

Jira is where some programmes keep their requirements as issues. The connector reads issues over the REST API and turns issue links into links. There is no "read everything": you give a JQL query, because an instance can hold millions of issues.

```bash
export JIRA_USER=you@example.com JIRA_TOKEN=...          # Cloud: the account e-mail and an API token (Basic)
reqin sample jira+https://your-site.atlassian.net --opt jql='project = ABC AND issuetype = Requirement ORDER BY key' --opt basic_user_env=JIRA_USER --opt basic_password_env=JIRA_TOKEN
```

| Option | Meaning |
|---|---|
| `jql` | **Required.** Put an `ORDER BY` in it; a note says so when it is missing, because an unordered paged read can skip or repeat an issue. |
| `flavor`, `api_version` | `cloud` (host ends in `.atlassian.net`) or `dc`; version 3 on Cloud, 2 on Data Center. Cloud reads `search/jql` with a page token and no total; Data Center reads `search` with `startAt` and checks the total and its 10,000 window. |
| `link_map` | What each link **type** becomes, and which end is the source. Jira does not say which end of "Blocks" is the requirement; **you** decide per type. A type you do not list keeps its own name, outward issue as source, and `discover` names it. |
| `parent_field`, `fields`, `field_names`, `resolve_field_names` | The parent field (a classic project's "Epic Link" is a custom field), the fields to read, and names for custom fields. |
| `token_env` (Data Center), `basic_user_env` + `basic_password_env` (Cloud) | The sign-in. |

**What it does.** Reads the pages, drops a repeated issue (counted), flattens Atlassian's rich-text description to plain text (version 3) or keeps the wiki markup as written (version 2), reads the parent and every link, shows one link seen from both of its issues once, and says in the notes what it did not like (no ORDER BY, a total that did not match, link types it had to name itself). A rejected login stops the read, even in the optional field-name lookup.

**Not seen on a live site:** anything. Whether Cloud's response has `isLast`, the default field list and the largest `maxResults` on `search/jql`, the `/field` answer, and which version returns rich text where. The profile is `profiles/jira.yaml`; confirm which field is the human requirement id (the issue key is the default).

**Agent prompt.** "Finish the `jira` connector against our Jira. Read `reqin/CONNECTORS.md` sections 1, 2 and 7 and `src/reqin/adapters/jira.py`. A human gives you the credentials in environment variables. Run `reqin sample` with a JQL limited to one project. Compare with `jira_server()` in `tests/live_cases_more.py`; update the fake to the real SHAPE (fictional content) before changing code. Ask the human what each link type means and put it in `link_map`. Keep `maturity` as `fake-server-tested`."

## 8. Polarion: `polarion`

```bash
export POLARION_TOKEN=...      # a personal access token (sent as Authorization: Bearer)
reqin sample polarion+https://host/polarion --opt project=WIDGET --opt token_env=POLARION_TOKEN --opt query='type:requirement'
```

| Option | Meaning |
|---|---|
| `project` | **Required.** The project id. |
| `query` | Polarion's Lucene query. Without one, every work item of the project is read. |
| `sort` | Default `id`, **sent on every page**: the vendor lists "no default sorting" for collection requests, so an unsorted paged read can skip or repeat a work item. `none` turns it off, with a note. |
| `role_map`, `parent_role` | What each link **role** becomes and which end is the source; and which role means "my parent". Polarion's pages do not say which end `parent` points at, so both are your decision, and `parent_role` is off until you set it. |
| `include_links`, `fields`, `page_size` | Links come with their role through `include=linkedWorkItems`; fields default to all. |

**What it does.** Pages through the work items, follows `links.next` only to the same host (credentials never go anywhere else), refuses a page that holds nothing new or a next link that points back, reads each link from the included link resources (or, when the server leaves them out, from the shape of the link id, and says how many), and reports a total that does not match.

**Not seen on a real server:** anything. REST is **off by default** (an administrator sets `com.siemens.polarion.rest.enabled=true` and restarts), so a 404 on the first request often means "not enabled"; the connector says so. The parameter names `page[size]`, `query`, `sort`, `links.next`, `meta.totalCount` and the exact link id shape are from third-party clients or recall. Links that point at an item from outside the query are not read. Profile: `profiles/polarion.yaml`.

**Agent prompt.** "Finish the `polarion` connector against our Polarion. Read `reqin/CONNECTORS.md` sections 1, 2 and 8 and `src/reqin/adapters/polarion.py`. A human gives you `POLARION_TOKEN` and confirms the REST API is enabled. Run `reqin sample` with a `query` limited to requirements. Compare with `polarion_server()` in `tests/live_cases_more.py`; update the fake to the real SHAPE (fictional content) before changing code. Ask the human which role means parent and which means satisfies, and set `parent_role` and `role_map`. Keep `maturity` as `fake-server-tested`."

## 9. Jama Connect: `jama`

```bash
export JAMA_TOKEN=...         # an OAuth bearer token; see the token helper below
reqin sample jama+https://yourorg.jamacloud.com --opt project=<id, name or key> --opt token_env=JAMA_TOKEN
```

| Option | Meaning |
|---|---|
| `project` | **Required.** A number, or an exact name or key (looked up with `GET /projects`; two matches stop the read). |
| `item_types` | Which item types to keep (names, keys or ids). Default is every item, **folders, sets and text items included**: read once to see what is there (`reqin discover`), then narrow. |
| `link_direction`, `link_map` | Default `downstream_to_upstream`: the source of a link is the downstream item (a test, a derived requirement), the target the requirement. Jama's help says relationships run from higher to lower level, but which of `fromItem` and `toItem` is which was **not confirmed**: check one link. |
| `picklist_fields` | Field names whose values are pick list option ids (status, priority): each id is looked up once and replaced by its name. |
| `relationships`, `page_size`, `rel_page_size` | Read relationships (default yes); the item page size (50 is the vendor's upper limit) and the relationship page size. |

**What it does.** Pages the item listing by `startAt`, follows `meta.pageInfo`, strips the `$<item type id>` suffix from field names, reads each item's parent from its location (a folder above it is not a record), pages relationships by `lastId`, counts the ones marked suspect, and reports a total that does not match.

**The one POST.** Jama's OAuth login is a POST, and the connector kit is GET-only, so the token is made by a small helper outside the read-only code: `connectors/jama/jama_oauth_hook.py`, a file you choose to use (`--opt auth_hook=jama_oauth_hook:headers`). It exchanges your client id and secret for a token, nothing else, and never prints the secret. It is the only POST anywhere in `reqin`'s connectors. **It has never run against a real Jama server.** A token lasts about an hour: read in parts for a big project.

**Not seen on a real instance:** anything. The `abstractitems` path, the field-key suffix, `itemType`, `documentKey`, `location.parent.item`, the relationship type field and the direction of the ends are recalled. Baselines, attachments, comments and versions are not read. Profile: `profiles/jama.yaml`.

**Agent prompt.** "Finish the `jama` connector against our Jama. Read `reqin/CONNECTORS.md` sections 1, 2 and 9, `src/reqin/adapters/jama.py` and `connectors/jama/jama_oauth_hook.py`. A human gives you the API credentials in environment variables. Run `reqin sample`, then `reqin discover` to see the item types, then set `item_types` and `picklist_fields`. Check the direction of one real link with the human and set `link_direction`. Compare with `jama_server()` in `tests/live_cases_more.py`; update the fake to the real SHAPE (fictional content) before changing code. Keep `maturity` as `fake-server-tested`."

## 10. MSOSA, Cameo and MagicDraw model files: `sysml1_xmi`

For a SysML 1.x model the supported routes are, in order of how well they are described: ReqIF (`profiles/msosa_reqif.yaml`), a requirement table exported as CSV or Excel (`profiles/cameo_requirement_table.yaml`), and this reader for the model itself: XMI (`.xmi`, `.xml`, `.mdxml`, `.uml`) or the project file `.mdzip`. There is no network in this one; it reads a file.

```bash
reqin discover model.mdzip          # which requirement stereotypes it found, and which other stereotypes it left alone
reqin sample   model.mdzip
reqin import   model.mdzip --profile profiles/sysml1_xmi.yaml --out reqs.jsonl
```

| Option | Meaning |
|---|---|
| `requirement_stereotypes` | Extra stereotype names to read as requirements (default: Requirement and ExtendedRequirement). A custom one is **not** read until you name it, and `discover` lists the ones it left alone. |
| `entry` | Which entry of a `.mdzip` to read. Default: the model entry; with none or several it stops and lists the entries. |
| `max_mb` | Refuse an entry larger than this (default 2048), checked on what the zip declares **and** on what it actually delivers. |

**What it reads.** Each class that carries a requirement stereotype becomes a record with `Id`, `Text`, `Name`, `Documentation`, `Package` (the packages around it), `Stereotype` and every other property of the application. A requirement nested in a requirement has the outer one as parent. Abstraction, Dependency, Realization, Usage and Substitution with a requirement at one end become links with the client (the design or test) as source and the supplier (the requirement) as target; the kind comes from the sibling stereotype (derive, satisfy, verify, refine, trace, copy), or `dependency` when there is none, and `discover` counts those. A file with a DOCTYPE or ENTITY declaration is refused.

**Honest limits.** A real `.mdzip` was never read: the fixtures follow the vendor's documentation (a zip of XMI 2.4 from version 17.0.1, the model entry `com.nomagic.magicdraw.uml_model.model`, the Requirement stereotype's `Id` and `Text`) and the shape of XMI and UML. Tag values stored as separate elements, profiles, diagrams and used projects are not read; the used-project entries are named, not opened. Many models leave `Id` empty and write the statement in the name: the profile says how to change that. Maturity is `fixture-tested`, not `fake-server-tested`: there is no server.

## 11. Sparx Enterprise Architect: a query pack for `sql`

Enterprise Architect has no HTTP API. When its repository is a database server, the safe read is a `SELECT` through a read-only login, and `reqin` ships that as two query files for the vendor-agnostic `sql` adapter, not as EA-specific code.

```bash
reqin sample 'postgresql+psycopg://reader@host/ea' --adapter sql --opt query_file=connectors/ea/requirements.sql --opt links_query_file=connectors/ea/links.sql --opt id_column=guid --opt parent_column=parent_guid
```

The same `sql` options work for any other database: `query` (or `query_file`), `id_column`, `parent_column` (the column that holds the parent's id), and `links_query` (or `links_query_file`; columns `source`, `target`, optionally `kind` and `ref`). All of them go through the same guard (one `SELECT` or `WITH`, comments removed first, SQLite opened read-only), and the row limit never wraps your query, so it also works on SQL Server and Oracle.

**The table and column names in the pack are from memory.** Sparx documents that a database repository has the same logical structure as the file one and that the element class maps to `t_object`; it does not list the columns. Run `SELECT * FROM t_object WHERE 1 = 0` (and the same for `t_connector`, `t_package`) first and fix a name in the `.sql` files if it differs. **Nobody has run this against a real Enterprise Architect repository**, and the link direction (start end = source) is a convention to check with `reqin sample`. `connectors/ea/README.md` lists what else is not covered (file repositories, tagged values, package paths).

## 12. Watch a folder: nightly exports

`reqin watch DIR --out OUT` re-ingests exports dropped into a folder and tells you exactly what changed.

```bash
reqin watch /exports --out /results --rules rules.yaml --settle 30 --interval 300      # or --once from cron
```

`rules.yaml`: `rules: [{match: "srs*.xlsx", profile: profiles/xlsx_srs.yaml, namespace: F-PROJ}, {match: "*.reqif", profile: profiles/msosa_reqif.yaml}]`.
Without rules it picks up only `csv xlsx xlsm reqif reqifz sysml`; Word and PDF need an explicit rule because their records must be verified by a person.

It never writes into the watched folder (and refuses an `--out` inside it), waits until a file has been quiet for `--settle` seconds, re-ingests only when the content hash changes, does not retry a failed file until it changes, ignores lock/temp/hidden files and symlinks, and writes `OUT/<file>/<hash>.jsonl`, a report with `added / removed / changed` since the previous version (by MID and fingerprint), and `latest.json`. One JSON line per event on stdout; `--once` exits 1 if any file failed. A damaged state file stops the run loudly instead of silently forgetting history.

## 13. Writing your own connector

Use `connector_template/` (a working, tested example with five `TODO(agent)` seams and an agent prompt). Anything that talks to a server uses `reqin.connect.make_http` and tests with `reqin.testing.FakeTransport` and `check_adapter`. To test what the connector does with an awkward answer (a page that comes back short, a missing total, a link with an empty end, a 401 on one path) without writing a second fake, put `reqin.testing.Tweaked` in front of your fake and bend that one reply; `tests/test_connector_edges.py` has about seventy such cases. Ship it as its own package with an entry point in the group `reqin.adapters`; the app and CLI find it without any change here.

## 14. Not built, on purpose

- **Write-back** to any system. Each adapter would need to prove a round trip on a real export first; the default stays read-only.
- **OAuth / form / OIDC sign-in.** Too dependent on your server's setup; `auth_hook` is the seam.
- **Cameo DataHub** is a feature of the modelling tool (it syncs MSOSA with DOORS, DOORS Next and CSV), not an API to call. If you use it, the DOORS side is read by the connectors above.
- **Server-side query** for SysML v2 (`POST .../query-results`): a read, but a POST; add it only after your security reviewer agrees an allow-listed read-only POST is acceptable.
- **Incremental sync.** `revision()` lets you detect that something changed; fetching only the changes is not implemented. `reqin watch` diffs whole exports.
- **Codebeamer.** Its usage terms, as read, bar building a data source for it without permission from the vendor. A connector needs that permission first; there is none here. Use its ReqIF export through `reqif`, or a CSV through `tabular`.
- **OAuth sign-in inside the connector kit.** Jama's token is the one POST in the connectors, in a separate file you opt into (section 9), not in the read-only code.
- **Used projects inside an `.mdzip`.** The reader opens one entry; the others are named, not read.
