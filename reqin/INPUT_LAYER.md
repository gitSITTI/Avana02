# Making the app work with any input

**Short answer.** Yes, and the way to do it is to stop teaching the app about file formats. Teach it one thing, a **canonical requirement record**, and put every source behind a small **adapter** that only reads. Meaning (which column is the statement, which is the ID) lives in a small **mapping profile**, a text file a person confirms. Then a new spreadsheet layout costs a profile and no code, and a new file format costs one adapter that must pass a shared test suite. Everything after that point (comparison, AI, review screens, export) never knows or cares where a requirement came from.

"Any data" has to mean something precise, or the app will mislead people. It means **any source that contains statement text you can point to**. The app labels every record with how far to trust it (Structured, Tabular, Parsed or Extracted), keeps a link back to where it came from, and refuses to drop anything silently. It cannot promise a lossless round trip back into the source tool, or readable text from a scanned PDF without OCR.

**Built to prove it.** A working reference implementation, `reqin/` (about 3,900 lines of source and 6,500 lines of Python in all, tests included), reads eight kinds of file input through one pipeline: CSV, XLSX, a DOORS-style CSV export, ReqIF, SysML v2 text, SQL, DOCX and PDF. It also has three live connectors (SysML v2 REST, DOORS Next over OSLC, Digital.ai Agility), a DOORS 9 export script and a watch-folder mode. **227 automated checks pass** (226 where LibreOffice is absent; the PDF-conversion check is then skipped, visibly). **The three live connectors have only ever met in-memory fakes I wrote from documentation, and the DOORS script has never run inside DOORS.** The same downstream comparison function finds the same near-duplicate pair (200 ms against 0.2 seconds) in all eight formats, and across two different sources. A 20,000-row import takes about 1.2 seconds in the sandbox. I then broke the code on purpose in 21 ways (secrets leaking into errors, a redirect to another host, TLS checks off, a write verb on the client, paging that stops after page one, caches removed, the settle time ignored, a `delete` call inside the DOORS script, and so on). 18 were caught at once; the other three showed tests I had not written (OSLC and Agility reading the server twice, and the no-record-vanishes flag never being able to turn false). I added those tests and all three are now caught. I then did the same to the dataset layer (20 deliberate breaks of the checker, the writer, the command line and the fourteen datasets): all 20 were caught. Section 6 says plainly what this does *not* prove.

## 1. The shape: five layers, and only two know about formats

| Layer | It knows | It must not know | Changes when |
|---|---|---|---|
| **Sources** | Files, servers, databases | Anything about review | Never (you do not own them) |
| **Adapters** | How to read one kind of source and describe what is in it | What a field *means* | A new format appears |
| **Mapping profile** | Which source field is the ID, the statement, the verification method | How to read a file | A new layout appears (a text edit, a person confirms) |
| **Canonical model** | One shape for a requirement, a link, a rejected row, and a report | Where the data came from, except a locator | Rarely, deliberately |
| **The app** (compare, AI, review, ledger, export) | Only the canonical model | Formats, tools, vendors | Features |

Board 10, frame 10.4 in the Excalidraw set draws this. Six rules hold it together:

1. **Adapters read; they never interpret.** An adapter yields what the source said (`RawRecord`, `RawLink`) and nothing else.
2. **Meaning is data.** Mapping lives in a YAML profile saved with the project and replayed on every re-import.
3. **Nothing is dropped silently.** Every raw record ends as a requirement, a *rejected* row with a reason, or a *filtered* row with a rule. The pipeline checks `raw = kept + rejected + filtered` and reports it.
4. **Every record carries its source locator** (row, ReqIF identifier, page and paragraph) so a person can jump back to the original.
5. **AI may propose, a person confirms.** A proposed profile is flagged as proposed until confirmed, and results from it carry a warning.
6. **Read-only by default.** No adapter writes to a source. Write-back would be a separate, explicit capability.

## 2. The canonical model

This is the whole contract between "reading" and "everything else" (`reqin/model.py`, trimmed):

```python
@dataclass
class Requirement:
    mid: str              # machine ID: sha1(namespace + native ID); stable; never shown to people
    uid: str              # the ID people use (REQ-FCS-0212); may be invented, then uid_synthetic=True
    uid_synthetic: bool
    text: str             # original statement
    norm_text: str        # NFKC, markup stripped, whitespace collapsed: what comparison uses
    fingerprint: str      # hash of norm_text + modal + numbers; changes only if meaning-bearing text changes
    slots: Slots          # modal (shall/should/will), negated, quantities [{value, unit, comparator, base_value}]
    fields: dict          # rationale, verification, allocation, owner, baseline, status
    extra: dict           # every source field the profile did not claim: lossless
    conf: dict            # Exact | High | Medium | Low, per field
    ref: SourceRef        # adapter, uri, container, locator, revision (file hash / commit id)
    fidelity: Fidelity    # structured | tabular | parsed | extracted
    parent_mid: str | None
```

Why each part exists:

- **MID and UID are different on purpose.** People know `REQ-FCS-0212`; a re-export may renumber or duplicate it. The MID is derived from the source's native ID inside a **namespace you set once per project** (for example `PROJ-A`), so the same requirement keeps the same MID across re-imports. Matching on re-import would go MID, then UID, then fingerprint (designed here, **not built**). Row numbers make poor native IDs because they move when rows are inserted. When a source has no native ID and the profile names none, the app invents a UID from the locator and **labels it invented** (`Low`).
- **Fingerprint** is how a re-import tells "reworded" from "reformatted". It ignores markup and whitespace and notices a changed number, unit, comparator or modal verb. Doorstop uses the same idea for staleness (see the report).
- **Slots** are extracted by rules, not by AI: `shall`/`should`/`will`, negation, and numbers with units and comparators (`at least`, `no more than`, `within`). `200 ms` and `0.2 seconds` both get `base_value 200` in time, so a downstream step can see they are the same quantity. Only time, mass, length and frequency are converted; anything else keeps its unit as written.
- **`extra`** keeps every source field the profile did not claim, so nothing a source said is lost. The test suite checks this on every format.
- **Confidence labels** are the ones the prototype's Import screen already shows. `Exact` means copied from a field you chose. `High` means a deterministic rule on a named field (a value map, a regex, markup stripping). `Medium` means guessed from names or values. `Low` means defaulted or invented.
- **Fidelity** is a property of the *source route*, not of a record. Structured sources have stable IDs and links. Tabular sources have rows you map. Parsed means a light read of model text. Extracted means found in prose.

## 3. The adapter contract

An adapter has four jobs (`reqin/adapter.py`):

```python
class Adapter(ABC):
    name: str;  fidelity: Fidelity;  caps: Caps    # structured_ids, links, hierarchy, write_back, incremental

    def sniff(self, src) -> float            # 0..1: can I read this? Cheap: extension and first bytes
    def discover(self, src) -> Discovery     # containers and fields with samples, row counts
    def read(self, src) -> Iterator[RawRecord | RawLink]   # what the source says, untouched, read-only, deterministic
    def revision(self, src) -> str           # file hash, commit id or query hash
```

- **Registry and sniffing.** Adapters register with `@register`. `sniff_all()` ranks them, and `pick_adapter()` takes the best at 0.5 or above, or the one you name. A broken sniff never blocks the others.
- **Plug-ins without touching the core.** A third-party package declares an entry point in the group `reqin.adapters`, and `load_adapters()` imports it. A new format ships as a package.
- **Containers** are whatever the source calls a group: a sheet, a ReqIF spec-object type, a SQL query, a document's prose or one of its tables. A profile can select which containers are requirements (a Cover sheet or a Heading type is not).
- **Capabilities** are declared honestly. Every adapter here is read-only (`write_back=False`).

## 4. Mapping profiles: where meaning lives

A profile is a small YAML file. This one (`profiles/msosa_reqif.yaml`) maps a ReqIF export:

```yaml
profile: msosa-reqif
adapter: reqif
namespace: DEMO-MSOSA          # keep stable across re-imports: part of every MID
containers: [Requirement]      # spec-object types that are requirements; headings are not
fields:
  uid:          {from: ["ReqIF.ForeignID", "ReqIF.Name"]}      # first non-empty wins
  text:         {from: ["ReqIF.Text", "Text"], strip_markup: true}
  rationale:    {from: "Rationale"}
  verification: {from: "Verification Method", map: {T: Test, A: Analysis, I: Inspection, D: Demonstration}}
```

Links can come from the source (ReqIF relations, SysML `satisfy`) or from a column. For a spreadsheet with a "Parent ID" column:

```yaml
links:
  - {kind: derive, from: "Parent ID"}     # a column holding target IDs, split on comma, semicolon or space
```

Operators: `from` (list, first non-empty), `join` + `sep`, `regex` (group 1), `map` (case-insensitive value translation), `default`, `const`, `strip_markup`, and an explicit `conf`. A profile can also filter rows with `where` (`{Object Text: {not_empty: true}}` to skip DOORS heading rows) and derive links from a column.

**The proposer.** With no profile, the app writes a *proposed* one from what it sees, using deterministic heuristics: the statement column is the one whose values most often contain `shall/should/will/must/may` and are long; the ID column matches an ID-like name, is unique and filled, and its values look like IDs (`SRS-12` beats `12`, which is why a DOORS "Object Identifier" wins over "Absolute Number"); a verification column has values from `T/A/I/D` or `Test/Analysis/...`. Each proposed rule carries a label (`High`/`Medium`) and a one-line reason, which is what the Import screen shows (frame 10.2). `reqin propose file.xlsx` prints it as YAML for a person to edit.

**What AI is for here.** AI can *propose* a profile when names and values are not enough, and it can *propose segmentation* of prose into statements. It must not apply either. The reference code has **only the heuristic proposer**; an AI refinement step is a design, not code. This is the same rule as the rest of the project: mechanics first, AI late, a person decides. It also keeps imports cheap and reproducible. A 20,000-row file is read by code in about a second, not by a model.

## 5. Source by source: the route, what exists, and what is not verified

| Source | Route and adapter | Fidelity | What I verified | Caveats |
|---|---|---|---|---|
| **SysML v2 (server)** | Systems Modeling API (REST), `sysml_api`; details in `CONNECTORS.md` | Structured | Rebuilt: reads page by page (Link header or `page[after]` cursor) and stops with an error rather than truncating when paging does not advance; finds the project by name or id; takes the default branch's head commit, or the project id as the commit id as SysON does; joins `documentation` to its requirement; keeps parent and `Dependency` links. Endpoint shape from SysON's docs ([SysON docs, v2024.11](https://doc.mbse-syson.org/syson/v2024.11.0/user-manual/integration/api.html)). Tested against an in-memory fake, and the shared GET-only client (retries, redirects, TLS, size cap) against real local HTTP and HTTPS servers | **Never run against a real server.** Paging style, branch/head lookup, relationship names and JSON keys are assumptions behind options. An earlier version of this adapter claimed to page and did not; that was a bug, now fixed and tested. Teamwork Cloud's API version is unknown to me. Run `reqin sample` first |
| **SysML v2 (files)** | `.sysml` text, `sysml_text` | Parsed | Tested on a synthetic file (nested definitions, wrapped `doc` comments, a comment that contains the word "requirement", `satisfy ... by ...`) | A lightweight scanner: no imports, redefinitions, expressions or units. For the full grammar use the Pilot Implementation. KPAR packages are not read by the reference code |
| **SysML v1 / MSOSA** | **ReqIF** from the Cameo Requirements Modeler plugin, `reqif` | Structured | The plugin's ReqIF route is documented in the report; the adapter was tested on a hand-written ReqIF 1.0 file in the standard shape | **No real MSOSA export was available.** ReqIF dialects differ by tool, so the first real export may need profile edits or an adapter fix. This is the riskiest item, as the report already says |
| **MSOSA project file** | `.mdzip`, `mdzip` | Structured | Layout documented since 17.0.1: a zip of XMI 2.4 with entries such as `com.nomagic.magicdraw.uml_model.model` | **Deliberately not implemented**: no documented reader contract. The adapter recognises the file and tells you to export ReqIF instead. It is the template for the next adapter |
| **DOORS (classic)** | ReqIF export, or CSV/Excel export | Structured / Tabular | From 9.5, create a RIF definition in the database properties and choose ReqIF v1.0 ([Jazz article](https://jazz.net/library/article/1243)) | Attribute names are defined per module, so modules can name the same thing differently (the article shows numeric suffixes such as "Criticality 2" after import into DOORS Next), and a profile's `from` list covers the variants. DOORS Next did not import system attributes such as created by or modified on in that article, so check whether your export carries them. OLE objects are exported as separate `.rtf` files. A CSV profile for the standard attributes (`Object Identifier`, `Object Text`) is in `profiles/doors_csv.yaml`; check the names against your own module **Added:** `connectors/doors9/export_requirements.dxl` is a read-only DXL script that writes the CSV the `doors_csv` profile reads. The CSV side is tested, a test scans the script for edit/delete/save/share/create calls, and **it has never run inside DOORS**. If your site exposes OSLC through DOORS Web Access, the `oslc_rm` route below might apply (assumed, not checked). |
| **DOORS Next** | ReqIF `.reqif` / `.reqifz` | Structured | IBM documents ReqIF import and export of both formats ([IBM](https://ibm.com/support/knowledgecenter/SSYMRC_7.0.2/com.ibm.rational.rrm.help.doc/topics/t_reqif_intro.html)); the adapter unzips `.reqifz` | Not tested on a real file. IBM says ReqIF is not a supported way to migrate whole repositories, which does not matter for reading **Added:** `oslc_rm` reads requirements over OSLC RM (rootservices, then catalog, then a paged query). Tested against a fake only. Sign-in is a session cookie or token read from an environment variable; OAuth and form logins are not built (`auth_hook` is the seam). |
| **Excel / CSV** | `tabular` | Tabular | Tested: title rows above the header, a Cover sheet, a hidden sheet, a blank row inside the data, duplicate headers, and a Windows-1252 semicolon CSV. By design, not tested: formula cells are read as their cached values and never executed | You confirm the columns once, then the profile replays |
| **SQL** | `sql` (SQLAlchemy URL plus a SELECT) | Tabular | SQLite: a guard that allows one `SELECT`/`WITH` statement, and a database opened `query_only` | The real control is a **read-only database role**. Other databases need their driver; they were not tested |
| **Word** | `docx` | Tabular for tables, Extracted for prose | Tables become rows; paragraphs with `shall/must/should/will` become candidates, with a location and a section heading; one paragraph with two obligations splits in two | Heuristic. Old `.doc` must be converted first (LibreOffice) |
| **PDF** | `pdf` (pdfplumber) | Extracted (tables Tabular) | Ruled tables are read as tables; the rest as text blocks with page locators; pages with no text layer are reported | **Borderless tables read as text lines with the columns interleaved**: my first run produced "The Power Subsystem shall Analysis not exceed…" before I excluded ruled tables from the prose pass. Scanned PDFs need OCR, which is not included. Docling (listed in the report) is a stronger reader and could sit behind the same contract (I) |
| **Digital.ai Agility** | REST (Data API, GET only), `agility`; or an export file through `tabular` with `profiles/agility_export.yaml` | Structured / Tabular | Response shape taken from public documentation, not re-checked against an instance; paged with `page=size,start`; identity survives edits because the trailing moment is stripped from the asset id; `Super` becomes the parent and `Dependencies` become trace links. Tested against an in-memory fake | **Never run against a real instance.** Stories and features are not always requirements: choose the asset types and a `where` filter |
| **Jama, Polarion, Jira...** | A later adapter each, starting from `connector_template/` | Structured | Nothing | Not built. Their export-to-CSV or ReqIF paths already work today through the adapters above |

## 6. What was tested, and what that does and does not show

**The conformance suite** (`tests/test_conformance.py`) runs the same eight properties against a fixture in every format. A format is "done" when it is listed there and green.

| Property | What it checks |
|---|---|
| Sniff | The right adapter ranks first |
| Discover | Containers and fields come back with samples |
| Counts, no silent drops | `raw = kept + rejected + filtered`; every rejection has a reason |
| Verbatim text | After normalisation the statement equals the original, for every real UID |
| Identity and provenance | Unique MIDs, a locator on every record, a fidelity and confidence on every field |
| Deterministic | Two imports give identical MIDs and fingerprints |
| Source untouched | The file's hash is the same after import |
| Nothing lost | Every non-empty source field is claimed by the profile or kept in `extra` |

Beyond that: 16 behaviour tests (units and comparators, markup, proposed versus confirmed profiles, value translation, DOORS headings, ReqIF hierarchy and `derive` links, `.reqifz` archives, links from a column, SysML nesting, extracted-record flags, legacy CSV encodings and duplicate headers, the SQL guard, a read-only database, the `.mdzip` refusal, and that the no-record-vanishes flag can actually go false), 2 downstream tests (same code, every format, plus across two sources), and the live-connector work: 55 tests of the three live connectors against in-memory fakes (paging at several page sizes, link directions, login pages, loops, lying totals, secrets, read-once, GET-only), 12 tests of the shared client against real local HTTP and HTTPS servers, 3 of the DOORS script, 16 of the command line and watch mode, 3 that keep the guide in step with the code, 3 that keep the licence files in step, and 51 of the dataset layer (the writer, a checker that must catch each of 19 deliberate corruptions plus several more cases, and the fourteen test datasets). **65 + 16 + 2 + 55 + 12 + 3 + 16 + 3 + 3 + 51 = 226 checks that need no office software, all passing.** The PDF fixture is generated in pure Python (reportlab). A 227th check converts the same document with LibreOffice when it is installed and is skipped, visibly, when it is not. Beside these: 33 tests in `tools/` (10 of the real-data guard, 2 on the licence files, 3 on picture freshness, 3 on Markdown links, 15 on the GitHub workflow) and 9 of the connector template. Run on Python 3.11, 3.12 and 3.13 in clean virtual environments.

**It does not show:**

- That a real MSOSA or DOORS export imports cleanly. The fixtures are synthetic and written by me. The next step is to add **one anonymised real export of each** as a fixture, and let the suite tell you what breaks.
- That the heuristics find the right columns on messy real spreadsheets. They gave `High` or `Medium` labels on my fixtures, and a person still confirms.
- That **any live connector works against a real server.** SysML v2 REST, OSLC RM and Agility have only met fakes I wrote from documentation, so every request shape, paging style, header and sign-in step stays an assumption until someone runs `reqin sample` against the real system. Sign-in is by token or cookie from an environment variable; OAuth, form and OIDC logins are not built.
- That the DOORS 9 DXL script runs. It has never been inside DOORS.
- That the container builds or the pipeline runs on GitLab. No container engine was available here: the image's test stage was simulated by installing only the files the Containerfile copies, and `.gitlab-ci.yml` passed a YAML lint and GitLab's published schema but has not run on a runner.
- Behaviour at 100,000 objects, in other languages, or under hostile input. The SQL guard is defence in depth, not a security boundary.

## 7. Adding a new input: three paths

**Path 1: a new spreadsheet, CSV or SQL layout. No code, minutes.**
`reqin propose layout.xlsx > profile.yaml`, edit the column names, then `reqin import layout.xlsx --profile profile.yaml`. Read the report: `invariant_ok`, rejected and filtered counts, unclaimed fields. Commit the profile with the project.

**Path 2: a new file format. One adapter, hours.**
1. For a file format, copy `adapters/tabular.py` and implement `sniff`, `discover`, `read`. For anything that talks to a server, start from `connector_template/` instead: a working, tested example with five `TODO(agent)` seams and a ready agent prompt, shipped as its own package. `CONNECTORS.md` is the guide.
2. Add a small, anonymised fixture to `tests/make_fixtures.py`.
3. Add one line to `CASES` in `tests/test_conformance.py`.
4. Run `pytest`. When it is green the adapter is done, and nothing else in the app changes.
5. Ship it in its own package with an entry point in the group `reqin.adapters`.

**Path 3: unstructured documents.** Use `docx` or `pdf`. Treat every record as unverified until a person has checked it against its locator (frame 10.3 shows the screen).

**Prompt for an agent that writes an adapter.** "Read `INPUT_LAYER.md` sections 1 to 3 and `adapters/tabular.py`. Implement an adapter for `<format>`. It must be read-only and deterministic, yield `RawRecord` and `RawLink` only, and put no field-meaning logic in the adapter. Add an anonymised fixture, add it to `CASES`, and make `pytest` pass. Report what the fixture does not cover, and do not weaken any test."

## 8. How this connects to the app and the boards

- **The screen's contract.** The screens read a *dataset folder*, never a file: `reqin import --out-dir` writes one, `reqin check-dataset` verifies one, and `reqin make-datasets` writes the fourteen test datasets a screen must pass. `GUI_CONTRACT.md` defines all of it in plain language.
- **Import screen.** The `Exact/High/Medium` chips on the prototype's Import screen are the `conf` labels. The dry-run report (`invariant_ok`, rejected, filtered, unclaimed fields, duplicate IDs, links pointing outside the import) is the content of frame 10.2. The **fidelity** badge follows every record into the review screens.
- **Pipeline.** This is stage one of the nine-stage pipeline in the report ("read and normalise"). `normalise.py` is the Python port of the prototype's number-and-modal logic, with comparators and base-unit conversion added.
- **Re-import and staleness** (design, not built): match by MID, then UID, then fingerprint, and report added, removed, changed (fingerprint differs) and stale (a decision exists on text that has since changed).
- **Write-back** is out of scope for adapters here. Each adapter would declare `write_back=True` only when it can prove a round trip on a real export. The report already names the ReqIF round trip as the riskiest prototype.

## 9. Questions for the project owner, and cautions

1. **Which exports can you actually get?** The most useful single input is one **anonymised ReqIF from MSOSA** and one from DOORS. The `reqif` package ships an `anonymize` command, but its help text is inherited from StrictDoc's SDoc and I did not run it on a ReqIF file, so test it before you rely on it.
2. **What is "systems v2"?** The report could not identify it. If it is a SysML v2 server, send one element's JSON from it and the API adapter's `keys` can be fixed in minutes. If it is an internal project name, the route is unknown.
3. **Where may the AI step run?** Real program requirements may be export-controlled or otherwise restricted. The mechanical path in this section uses no AI at all. Route any AI call through an endpoint your security office has approved, or leave it off. Keep fixtures synthetic or approved for sharing.
4. **Size.** DOORS-to-DOORS Next guidance recommends at most about 5,000 objects per module and about 200,000 in total ([Jazz article](https://jazz.net/library/article/1243)). Your largest module is the right scale test, and ReqIF parse memory at that size was not measured.
5. **Licences.** Check the licence of each dependency (`reqif`, `openpyxl`, `pdfplumber`, `python-docx`, `SQLAlchemy`) before you ship the code inside a product.

## Sources

- [SysON: SysML v2 REST API](https://doc.mbse-syson.org/syson/v2024.11.0/user-manual/integration/api.html) (endpoint paths, "not fully available yet")
- [Jazz: exporting from Rational DOORS and importing to DOORS Next by using ReqIF](https://jazz.net/library/article/1243) (DOORS 9.5+ ReqIF export, caveats, size guidance)
- [IBM: importing and exporting ReqIF files](https://ibm.com/support/knowledgecenter/SSYMRC_7.0.2/com.ibm.rational.rrm.help.doc/topics/t_reqif_intro.html) (DOORS Next `.reqif` and `.reqifz`)
- The research report's sections on opening MSOSA projects, ReqIF, Doorstop, StrictDoc and Docling, which carry the Cameo Requirements Modeler and `.mdzip` sources.
