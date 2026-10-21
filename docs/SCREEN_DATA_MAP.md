# Screen data map: where every number on every screen comes from

**What this page is for.** The prototype's screens are drawings with made-up numbers in them. A person (or an agent) who copies a screen copies the made-up numbers too, and the screen looks right and shows nothing real. This page says, for every screen and every element on it, **which real output feeds it, by field name**, and which elements have **no producer yet**.

**How it is checked.** Every field name written like `DS.fields.allocation` or `CL.members[].uid` in this page is looked up by a test (`tools/test_screen_data_map.py`) in what `reqin` really writes: the fourteen test datasets, the comparison engine run on each, and the V report. A name that does not occur fails the test. That proves the names exist. It does **not** prove that a screen built from this page is right, or that the rules written in plain words here are the best ones.

**Who wrote it.** One agent, from the prototype's source, `reqin/GUI_CONTRACT.md`, `docs/COMPARE_FORMAT.md` and the output of the real commands. Nobody has built a screen from it yet. Where this page says a value has no producer, that is a finding to be confirmed by the owner, not a design decision.

## 1. The rule

Every value on a screen is one of four things:

| It is | Example | What the screen does |
|---|---|---|
| **Read** | the count of requirements, an ID, a statement | shows the field, nothing else |
| **Counted or worked out from read values** | "12 clusters need you", the share traced to a verification item | worked out in one place (the *view model*, below), and says so when it is a guess or a sample |
| **Typed by a person in the GUI** | a decision, a sign-off, a label | kept as saved work, never mixed into the dataset |
| **Words** | a title, a sentence under it, a button label | written in the GUI source, and that is fine |

Anything else is a **made-up value**, and it is the one thing that must never reach a screen. If a screen needs a value that this page lists as having no producer, the screen shows an honest empty state ("no labelled pairs yet") and the person who owns the work is told. A number is never typed in to make the screen look full.

**The view model.** Between the data and the markup sits one function per screen: it takes the data in section 2 and returns exactly what the markup shows (the counts, the rows, the labels, what is hidden). It is plain code with no markup in it, so it can be tested with the fourteen datasets without a browser. A screen that reads a file, or does arithmetic inside its markup, has no place for that test.

## 2. The six places data comes from

| Code | What it is | Made by | Where it is |
|---|---|---|---|
| `DS`, `LK`, `RJ`, `RPT`, `MAN` | the canonical dataset: `requirements.jsonl`, `links.jsonl`, `rejected.jsonl`, `report.json`, `dataset.json` | `reqin import SOURCE --out-dir DIR`; the fourteen tests from `reqin make-datasets DIR` | a folder of five files ([`reqin/GUI_CONTRACT.md`](../reqin/GUI_CONTRACT.md) section 3) |
| `CL`, `PR`, `SL`, `CMP` | the comparison output: `clusters.jsonl`, `pairs.jsonl`, `slots.jsonl`, `compare.json` | `reqin compare DATASET... --out-dir OUT` | a folder of four files ([`docs/COMPARE_FORMAT.md`](COMPARE_FORMAT.md)) |
| `VEE` | the engineering V counted from a dataset | `reqin vee DIR --json` | printed |
| WORK | decisions, sign-offs, hand-offs, labels, the AI switch and sheet, the event record | people, in the GUI | the browser (`reqin-project-state/1`, [`prototype/parts/persist.js`](../prototype/parts/persist.js)) or the shared server ([`reqin/SERVER.md`](../reqin/SERVER.md)); **not** part of any dataset |
| STATIC | titles, sentences, labels, explanations | the designer | the GUI's own source |
| NONE | nothing produces it yet | | see section 5 |

Order of the folders: a dataset is made first and never changes; the comparison output is made *from* datasets (`CMP.datasets[].manifest_sha256` says which); saved work refers to both by IDs. A screen that loads a comparison folder made from a different dataset says so and refuses it.

## 3. How to read the screen sections

Each section gives the screen's name (the same name the prototype's markup uses), what it **needs**, and a table of its parts. A part's source is a code from section 2 and the field names. `mid` is the internal key: it routes and joins, and is **never shown**. `uid` is the ID people quote.

A **status** word is on every screen:

- **Dataset only**: everything it shows comes from a dataset (and `VEE`), so it can be built and tested today with the fourteen datasets.
- **Needs comparison output**: also needs a folder from `reqin compare`.
- **Needs saved work**: also needs decisions or labels that people make in the GUI; before anyone has made any, it shows the empty state.
- **Partly without a producer**: something it shows has no producer yet (listed in its table and in section 5).

## 4. Screen by screen

### 4.1 Open  ·  status: dataset only, plus an importer the GUI cannot be

| Part | Source |
|---|---|
| The six source cards and their trust words | STATIC. A trust word must never claim more than `reqin connectors` prints in its maturity column |
| "Drop a file" and what the file would be recognised as | the importer (`reqin sniff FILE`). The GUI cannot read the file (contract rule 1), so this needs a service that runs the importer, or the person runs the command and gives the GUI the folder |
| Recent projects: name, source, record count | one per dataset folder opened: `MAN.sources[].uri`, `MAN.sources[].adapter`, `RPT.requirements`, `RPT.fidelity` |
| "Signed in as" and the six sample people | NONE from a dataset. Identity comes from the shared server's tokens; the prototype's people are sample |

### 4.2 Import: check what the app found (statements found inside a document)  ·  status: dataset only, partly without a producer

| Part | Source |
|---|---|
| One row per found statement: ID, and "ID invented by the importer" | `DS.uid`, `DS.uid_synthetic` |
| The statement | `DS.text` |
| Where it was found (page and block) | `DS.ref.container`, `DS.ref.locator` |
| How sure, with a visible cue on Medium and Low | `DS.conf.text`, `DS.conf.uid` |
| The banner "found inside prose; verify each against its page" | shown when `DS.fidelity` is `extracted` (the same value is in `RPT.fidelity`) |
| Verified or not, per record | WORK: a person's tick |
| The page of the document with the statements highlighted | **NONE.** The dataset keeps the locator, not the page, and the GUI cannot open the original. Show the locator and say where the original is, or extend the contract first |

### 4.3 Import: check how your fields map, choose scope  ·  status: partly without a producer

This screen is the front of the importer, not of a dataset.

| Part | Source |
|---|---|
| The proposed mapping rows (slot, source column, sample, how sure, change) | the importer's proposed profile, written as YAML by `reqin propose SOURCE`. It is not in the dataset. `RPT.profile` names the profile used and `RPT.profile_proposed` says whether a person confirmed it. Needs a service that runs the importer |
| What stayed unmapped | `RPT.unclaimed_fields[]` |
| Dry-run counts: read, kept, rejected, filtered | `RPT.raw_records`, `RPT.requirements`, `RPT.rejected`, `RPT.filtered_out` (a count for each reason) |
| The first three records as the review screens will show them | the first lines of `requirements.jsonl`: `DS.uid`, `DS.text`, `DS.fields.verification`, `DS.fields.allocation`, `DS.fidelity` |
| Warnings | `RPT.warnings[]`, as written |
| The scope choices (all, one allocation, a pilot) | the values present in `DS.fields.allocation`; none offered when `RPT.coverage.allocation` is missing |

### 4.4 Workspace shell (side bar, top bar, DRAFT bar, help)  ·  status: dataset only

| Part | Source |
|---|---|
| Source name | `MAN.sources[].uri`. The project's name is not in a dataset: WORK or STATIC |
| Side-bar items and their counts | words are STATIC; counts come from the screens they lead to |
| Scope and baseline in the top bar | the values present in `DS.fields.allocation` and `DS.fields.baseline` |
| The small V | `VEE.levels[]` (section 4.10) |
| Search | over `DS.uid` and `DS.text` |
| The DRAFT bar, the glossary | STATIC. The DRAFT bar is part of the frame, not of the content |
| People, presence, the lens switcher, "demo" controls | prototype only; see 4.1 |

### 4.5 Home  ·  status: needs comparison output, needs saved work

| Part | Source |
|---|---|
| The title and the one button ("N clusters need you") | `CMP.counts.clusters` less the ones WORK has decided |
| The security band and its facts | STATIC wording, plus the AI sheet from WORK (4.16) |
| "Bring in requirements": three ways in | STATIC |
| The V card | `VEE` (4.10) |
| Recent imports (expandable: records, trust, who) | per dataset: `RPT.requirements`, `RPT.adapter`, `RPT.fidelity`, `MAN.sources[].uri`; the person is WORK |
| Open clusters by allocation (bars) | each cluster's members' allocation: `CL.members[].mid` to `DS.mid` to `DS.fields.allocation`. Hidden when no requirement has an allocation |
| Latest activity | WORK (the event record) |
| "Your work is kept" | WORK (what the browser or server holds) |

### 4.6 Overview  ·  status: partly without a producer

| Part | Source |
|---|---|
| How the list narrowed (read, kept, grouped, in clusters) | `RPT.raw_records`, `RPT.requirements`, `CMP.counts.groups`, `CMP.counts.in_clusters`, `CMP.counts.clusters`, `CMP.counts.singletons` |
| Open count, "for me" | `CMP.counts.clusters` and WORK |
| The three lanes (low risk, needs evidence, conflict) | **NONE.** Lanes are an idea from the design research that depends on the AI stage (guards, verifier and panel agreeing); the engine writes `PR.type` and `PR.needs_review`, not a lane. A lane from mechanical output alone would be a rule somebody has to write, test and agree first |
| Sign-off meters | WORK |
| The grade line | **NONE** until the grade exists as code (4.11) |

### 4.7 Review (the queue and one cluster)  ·  status: needs comparison output, needs saved work, partly without a producer

| Part | Source |
|---|---|
| A queue row: its size | the length of `CL.members[]` |
| A queue row: its title | the representative's statement: `CL.representative` to `DS.mid` to `DS.text` |
| The IDs shown | `CL.members[].uid` (never `mid`) |
| The relationship chip | the most serious of the pairs in `CL.related[]`: `PR.pid` to `PR.type` |
| The state chip (waiting, decided, signed) | WORK |
| Filters by allocation and by level | the values present in `DS.fields.allocation`; the level is counted as 4.10 says |
| A filter by lane | **NONE** (4.6) |
| The wordings of the cluster | `DS.text` of each member of `CL.members[]` |
| Which wording is the reference | `CL.representative`: a proposal, and `CL.representative_basis[]` says why it was chosen. The prototype's default ("the strictest wording") is a different rule; it may be worked out, but then it is labelled as worked out |
| What differs, in words, with the changed words highlighted | for a pair: `PR.why[].text` with `PR.why[].a_span` and `PR.why[].b_span`, which are positions in `DS.norm_text` (not `DS.text`) of `PR.shown_a` and `PR.shown_b`. For any set of wordings: the pure function `compareRows` / `alignRows` ([`prototype/parts/logic1.js`](../prototype/parts/logic1.js)) works the difference out from the texts |
| Why the engine suggested it | `CL.why[]`, `CL.rung`, `PR.rule`, `PR.basis`; `PR.score` only ever as "sorts pairs, not a probability" |
| The small table of other fields (owner, level, verification, allocation, baseline) | `DS.fields` where they differ. A key a source did not provide reads "not provided by this source" |
| A group of six wordings whose **numbers** differ ("365 → 60") | **Partly NONE.** The engine's clusters hold only requirements it proved equal. Wordings whose numbers or modals differ come as VARIANT pairs (`PR.type`) that hang off a cluster (`CL.related[]`). Assembling a multi-wording group from those pairs is view-model work to write and test; it is not a cluster in the output |
| The Resolve panel: outcome, which wording, reason, note; sending it to a teammate | WORK |
| The AI box | **NONE.** No AI stage is built. It shows "no AI answer" and the gate's reason (4.16), never a sample answer |

### 4.8 Line up the words  ·  status: dataset only (given a cluster)

| Part | Source |
|---|---|
| The columns, one per word of the reference, with changed words under them | worked out from the texts by `alignRows`; the texts are `DS.text` of the members of one `CL.members[]` |
| Which wording is the reference | as 4.7 |
| The change chips ("365 → 60") | worked out by `compareRows` from the same texts |

### 4.9 All requirements  ·  status: needs comparison output, needs saved work

| Part | Source |
|---|---|
| One square per requirement | one per line of `requirements.jsonl`; the total is `RPT.requirements` |
| Grouped by | any key present in `DS.fields` (how many have it: `RPT.coverage`). The group names are the values present, never a fixed list |
| A square "alone, nothing similar found" | a requirement whose `DS.mid` is in no `CL.members[].mid` and in no `PR.a.mids` / `PR.b.mids` |
| A square "in a cluster, needs a decision" | its `DS.mid` is in `CL.members[].mid` and WORK has no decision for that cluster |
| Squares "decided", "approved", "needs attention" | WORK |
| The list under the map, windowed | `DS.uid`, `DS.text`, `CL.cid` |
| The detail panel: ID, "ID invented" badge, statement | `DS.uid`, `DS.uid_synthetic`, `DS.text` |
| The six well-known fields, and "other fields from the source" | `DS.fields` (any key may be missing), `DS.extra` shown key by key without naming any key in code |
| How sure | `DS.conf`, `DS.fidelity` |
| Show in source | `DS.ref.uri`, `DS.ref.container`, `DS.ref.locator`, `DS.ref.revision` |
| The trace panel | `LK.kind`, `LK.source_uid`, `LK.target_uid`. An end whose `LK.source_mid` or `LK.target_mid` is null reads "not in this import". Hidden, with the reason, when `RPT.links` is 0 |
| Parent and children, the tree | `DS.parent_mid`. A flat list when every one is null |
| What the methods found about it | the entries of `CL` and `PR` that name its `DS.mid` |
| "The five closest in its allocation" | worked out in the view model from `DS.fields.allocation` and `PR.score`, and labelled as worked out |
| A source chip on each record | `DS.ref.uri`, `DS.ref.adapter` |
| Recording a decision with a reason code | WORK |

### 4.10 The V  ·  status: dataset only, plus saved work for "after your decisions"

| Part | Source |
|---|---|
| A row per level: its name and the check that proves it | `VEE.levels[].level`, `VEE.levels[].name`, `VEE.levels[].check` |
| Requirements at the level; with a method; with an item; traced | `VEE.levels[].requirements`, `.with_method`, `.with_item`, `.traced` |
| Gaps, and which half is missing | `VEE.levels[].gaps`, `.no_method`, `.no_item` |
| Verification items at the level, and the methods used | `VEE.levels[].items`, `VEE.levels[].methods.Test`, `.Analysis`, `.Inspection`, `.Demonstration`, `.other` |
| The totals, and requirements placed at no level | `VEE.total.requirements`, `.traced`, `.gaps`, `.items`, `VEE.unplaced.requirements` |
| The plain-words notes | `VEE.notes[]`, as written |
| "Sample values" next to the picture | shown whenever the levels are not read from the data: `VEE.hierarchy` is false and `VEE.level_field` is null, so nobody is placed, and the screen says that instead of putting everybody at level 1 |
| "After your decisions" next to "now" | worked out: WORK decisions applied to the numbers above and to `CL.members[]` |
| Clusters whose members sit at different levels (link or supersede, never merge) | worked out: each member's level is the depth of its `DS.parent_mid` chain, or a field the person names; `VEE` has only the counts |
| Verification items that would have to move | worked out: `LK.kind` verify links whose target is a requirement a merge would remove |

### 4.11 Results and grade  ·  status: partly without a producer

| Part | Source |
|---|---|
| The grade letter, the score, the bands, the cap rule, the five parts with their weights | **NONE as data.** The arithmetic exists only as `GRADE_PARTS` and `GRADE_BANDS` in [`prototype/parts/logic3.js`](../prototype/parts/logic3.js); no code in `reqin/src` computes it. It would have to be ported, given test vectors, and checked by the owner before a number is shown to anyone |
| The original set against the consolidated one | `RPT.requirements`, the clusters in `CL.members[]`, and WORK decisions |
| Where each original requirement ended up | WORK decisions, requirement by requirement |
| What would raise the grade | worked out from the above |
| What this does to each level of the V | `VEE` plus WORK |
| Each part of the system graded on its own | the same arithmetic over each value of `DS.fields.allocation` |

### 4.12 Label pairs (the gold set)  ·  status: needs saved work

| Part | Source |
|---|---|
| The pair on screen, with no method's opinion shown | two requirements chosen from the pairs the engine wrote: `PR.pid`, `PR.shown_a`, `PR.shown_b`, texts from `DS.text`. The sampling plan is in [`prototype/parts/gold.js`](../prototype/parts/gold.js) |
| The six labels, progress, "do two people agree", the latest labels | WORK: these are what people typed |
| The gold set file | written from WORK |

### 4.13 Methods and metrics  ·  status: partly without a producer

| Part | Source |
|---|---|
| How the mechanical engine scored on a generated corpus | [`docs/COMPARE_RESULTS.md`](COMPARE_RESULTS.md) (generated). It is about the engine, not about this project |
| Mechanical against AI; with and without AI; best category with and without AI; how often people accept, by confidence | **NONE.** There is no AI stage, and no gold labels yet (4.12). Until both exist the screen says "no labelled pairs yet" and shows no number |
| "This session", "Guards", "Progress by lane" | the first two partly from WORK; lanes are NONE (4.6) |

### 4.14 Decisions and audit  ·  status: needs saved work

| Part | Source |
|---|---|
| The ledger: cluster, decision, reason, note, who, when | WORK |
| The chain of events and its verification | WORK. The shared server's chain is SHA-256 and can be verified there; the prototype's own chain is 32-bit and is only a local record (the page says so) |

### 4.15 Sign-off policy  ·  status: needs saved work

| Part | Source |
|---|---|
| Who must sign what, per lane or per kind of change | WORK (the policy the leads set) with STATIC explanations. The lane column depends on 4.6 |

### 4.16 AI use  ·  status: needs saved work, partly without a producer

| Part | Source |
|---|---|
| The switch, the data sheet, who reviewed it, the changes to it | WORK |
| What the gate does with each group, the groups held back and why | the gate: [`reqin/src/reqin/aigate.py`](../reqin/src/reqin/aigate.py) (and its JavaScript twin `prototype/parts/aigate.js`), checked against [`docs/ai_gate_cases.json`](ai_gate_cases.json). Its inputs are the groups from `CL.members[]` and each requirement's marking |
| Each requirement's marking | **NONE by default.** No marking is a field of the dataset contract. It arrives only if a mapping puts one in `DS.fields` or `DS.extra`; otherwise it is "no marking recorded" and the sheet says what happens to those |

### 4.17 Export  ·  status: needs comparison output, needs saved work

| Part | Source |
|---|---|
| Decisions ready to export, and those still waiting | WORK, with `CL.cid` and `CL.members[].uid` |
| What moves outside the requirement list: verification items, child requirements, baselines | worked out as 4.10 says; the writers of `trace-map.json` and `alias-map.csv` are in [`prototype/parts/trace.js`](../prototype/parts/trace.js) and described in [`docs/V_MODEL.md`](V_MODEL.md) |
| The baseline to export against | the values present in `DS.fields.baseline` |
| The formats | STATIC |

### 4.18 Assistant drawer  ·  status: partly without a producer

| Part | Source |
|---|---|
| The questions and answers | **NONE** from a dataset. They would go through the gateway ([`docs/AI_GATEWAY.md`](AI_GATEWAY.md)), which the gate (4.16) must have let through. The prototype's replies are scripted |

## 5. What has no producer yet (so no screen may show a value for it)

1. **Lanes** (4.6, 4.7, 4.13, 4.15): need the AI stage, or a mechanical rule that does not exist yet.
2. **A cluster of wordings with different numbers** (4.7): the engine writes VARIANT *pairs*; building a multi-wording group from them is not done.
3. **The AI's proposal, verdict and wording** (4.7, 4.13, 4.18): no AI stage.
4. **The grade** (4.6, 4.11): code only in the prototype.
5. **Method-against-AI and with-and-without-AI numbers** (4.13): need the AI stage and gold labels.
6. **A requirement's marking** (4.16): not in the contract.
7. **The page of the document** behind an extracted statement (4.2): the dataset keeps only the locator.
8. **The importer's proposed mapping** (4.3) and **what a file is recognised as** (4.1): the importer runs outside the GUI; there is no service for it.
9. **Who the person is** (4.1): the shared server's tokens; the prototype's six people are sample.

## 6. Which prototype code to reuse, and which to never copy

**Pure functions that work from their arguments, so they can be ported:** `compareRows`, `alignRows`, `diffTokens`, `editRatio` ([`logic1.js`](../prototype/parts/logic1.js)); `veeGlyph` (draws the small V from numbers, [`logic3.js`](../prototype/parts/logic3.js)); the AI gate (`aigate.js`, with its Python twin and its table of cases); the event-chain check `chainCheck` ([`persist.js`](../prototype/parts/persist.js)).

**Sample generators and sample constants. Never port or copy these; they are why a copy of a screen is static:** `genAll`, `TOTAL_REQS`, `CLUSTERS`, `ORDER`, `REQS`, `REQ_BY` ([`data3.js`](../prototype/parts/data3.js)); `vHash` ([`logic3.js`](../prototype/parts/logic3.js)); `SEED` ([`logic2.js`](../prototype/parts/logic2.js)); `EV_SEED` ([`misc.js`](../prototype/parts/misc.js)); `SOURCES`, `RECENTS`, `FILES`, `IMPORTS`, `DOC_ITEMS`, `PEOPLE` ([`data1.js`](../prototype/parts/data1.js)); and [`prototype/demo/seed.json`](../prototype/demo/seed.json).

## 7. What this page does not claim

- That a screen built from it is correct. It lists where values come from; it does not say how a screen should look (the pictures and [`GUI_DESIGN_GUIDE.md`](GUI_DESIGN_GUIDE.md) do) or whether the rules in plain words are the right ones.
- That the engine's output is good enough to review with. [`COMPARE_RESULTS.md`](COMPARE_RESULTS.md) says how it did on a corpus its author generated, and that it was never run on a real requirements set.
- That the statuses are complete. A screen element that is not in a table is a gap in this page; add the row, and the test will check the names.
