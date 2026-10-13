# GUI contract: one screen that works for any requirements source

**For:** the agent building or fixing the requirements GUI. **Written for:** a reader who is not a systems engineer, so every term is explained once.
**Version 1, 2026-10-13.** The example data below is real output of the `reqin` importer run on a made-up four-row file; nothing in it is program data.
Three commands in `reqin` (the input layer in this repository) make the contract real: `reqin import ... --out-dir DIR` writes a dataset, `reqin check-dataset DIR` says whether a folder follows this contract, and `reqin make-datasets DIR` writes the fourteen test datasets of section 6. If `reqin` is not installed where you work, the contract is still complete: build and check datasets to the same layout yourself.

## 1. The one rule

> **The GUI never reads a file, a database or a server. It reads one *canonical dataset* (section 3), and nothing else.**

Everything that touches a source (Excel, CSV, DOORS, ReqIF, SysML, SQL, Word, PDF) happens *before* that line, in an importer, and ends with a mapping that a person confirmed.
The GUI is a function of the canonical dataset, so it behaves the same for every source, and "a new file type" is never a GUI change.

**Why the GUI keeps breaking.** When an agent builds a screen while looking at one sample file, the sample *is* the specification: the columns it has become the screen's columns, its hierarchy becomes the tree, its quirks become features. A different file then has nothing in the places the screen expects, and the screen stalls.
The fix is not more samples. It is (1) a written contract for what the screen may rely on, (2) a fixed set of deliberately *different* test datasets (section 6) that the screen must pass, and (3) a rule that a file which breaks the screen becomes a new test dataset, never a patch for that file.

## 2. What a requirement is, and what real files leave out

A requirement is one sentence that says what a system must do or be. Real exports contain only some of the following, and that is normal:

| Thing | Plain meaning | Canonical name | Often missing? |
|---|---|---|---|
| **ID** | The label people quote in meetings, e.g. `SRS-1042` | `uid` | Prose documents and some spreadsheets have none |
| **Statement** | The sentence itself, usually with "shall" | `text` | Never (a record with no statement is rejected) |
| **Modal** | *shall* = mandatory, *should* = goal, *will* = statement of fact or intent, *may* = optional | `slots.modal` | Derived from the text |
| **Parent / children** | Hierarchy: a system-level requirement broken into subsystem ones | `parent_mid` | Often missing, e.g. flat spreadsheets |
| **Links** | How requirements relate. *satisfy*: a design element or requirement meets it. *derive*: a child written because of a parent. *verify*: a test or analysis proves it. *refine*: adds detail. *contain*: structural parent-child. *trace*: any other relationship | `links[].kind` | Often missing |
| **Verification method** | How it will be proven: Test, Analysis, Inspection or Demonstration | `fields.verification` | Common |
| **Rationale** | Why the requirement exists | `fields.rationale` | Very common |
| **Allocation** | Which part of the system or which team it is assigned to | `fields.allocation` | Common |
| **Owner** | The person or team responsible | `fields.owner` | Common |
| **Baseline** | A named, frozen release of the requirement set, e.g. "CDR" | `fields.baseline` | Common |
| **Status** | Draft, approved, deleted and so on | `fields.status` | Common |
| **Everything else** | Priority, type (functional, performance, interface), criticality, custom columns | `extra` (kept, never dropped) | Varies |

So the GUI cannot assume that any optional thing exists. It must look at what arrived (section 5).

## 3. The canonical dataset

A dataset is a **folder of five files**. Everything in the GUI comes from these.

| File | What it holds |
|---|---|
| `requirements.jsonl` | One requirement per line (below). |
| `links.jsonl` | One link per line: `{source_uid, target_uid, kind, source_mid, target_mid, ref}`. `kind` is an open set (`satisfy`, `derive`, `verify`, `refine`, `contain`, `trace`, or something a source invents), so show unknown kinds as written. `source_mid` or `target_mid` is `null` when that end is outside this import. |
| `rejected.jsonl` | One line per record the importer could not turn into a requirement: `{ref, reason, fields}`. Every one has a reason. |
| `report.json` | Counts, coverage, confidence and warnings (below). It is how the GUI knows what the dataset contains. |
| `dataset.json` | The manifest, written last: contract version, counts, and the size and SHA-256 of every other file. A folder without it is an unfinished write; a file that no longer matches it was cut short or edited. |

**Before showing a dataset, run the same check the command line runs** (`reqin check-dataset DIR`, or the equivalent rules in your own code). If a folder fails, show why in words; never render a half-valid dataset as if it were complete.

**One requirement, exactly as the importer writes it:**

```json
{
  "mid": "m_8bf36832c2fd",
  "uid": "WIDGET-002",
  "uid_synthetic": false,
  "text": "The widget shall not exceed 5 kg.",
  "norm_text": "The widget shall not exceed 5 kg.",
  "fingerprint": "be3f634743c04e11",
  "slots": {
    "modal": "shall",
    "negated": true,
    "quantities": [
      {
        "raw": "5 kg",
        "value": 5.0,
        "unit": "kg",
        "comparator": "<=",
        "dimension": "mass_kg",
        "base_value": 5.0
      }
    ]
  },
  "fields": {
    "verification": "Inspection"
  },
  "extra": {
    "Absolute Number": "3",
    "Object Level": "2",
    "Object Heading": ""
  },
  "conf": {
    "text": "High",
    "uid": "Exact",
    "verification": "Exact"
  },
  "ref": {
    "adapter": "tabular",
    "uri": "ex.csv",
    "container": "ex",
    "locator": "ex!R4",
    "revision": "b80bc2b13ccd3880"
  },
  "fidelity": "tabular",
  "parent_mid": null
}
```

| Field | Always there? | Meaning for the GUI |
|---|---|---|
| `mid` | yes | Internal stable key. Use it for routing and selection. **Never show it to people.** |
| `uid` | yes | The ID to show. If `uid_synthetic` is `true` the importer invented it (no ID in the source): say so with a badge and never present it as the source's ID. |
| `text` | yes | The statement, to show. `norm_text` is for comparison only; do not show it. |
| `fingerprint` | yes | Changes only if the meaning-bearing text changes. Use it to detect "changed since last import". |
| `slots` | yes | `modal` (may be empty), `negated`, `quantities` (value, unit, comparator). Machine-read from the text; used for highlighting differences. May be empty. |
| `fields` | yes, but **any key may be missing** | The importer proposes six well-known keys: `rationale`, `verification`, `allocation`, `owner`, `baseline`, `status`. A mapping can add others (for example `priority`). Missing means the source did not provide it. Give the six friendly labels, and show any other key generically. |
| `extra` | yes, may be `{}` | Every source field the mapping did not claim. Show generically as "Other fields from the source" (key and value), never by name in the code. |
| `conf` | yes | A trust label per field: `Exact` (copied), `High` (rule), `Medium` (guessed, a person should confirm), `Low` (extracted from prose or defaulted). |
| `fidelity` | yes | How the record was read: `structured` (tool export with real IDs and links), `tabular` (spreadsheet or table rows), `parsed` (text notation), `extracted` (found inside prose: **a person must verify every one**). |
| `ref` | yes | Where it came from: `adapter`, `uri`, `container` (sheet, document), `locator` (row, identifier, page and paragraph), `revision`. Every record must offer a way to see this. |
| `parent_mid` | may be `null` | Hierarchy. All `null` means the source has no hierarchy; do not draw an empty tree. |

**The report, for the same file:**

```json
{
  "adapter": "tabular",
  "fidelity": "tabular",
  "profile": "doors-csv",
  "profile_proposed": false,
  "revision": "b80bc2b13ccd3880",
  "raw_records": 4,
  "requirements": 3,
  "rejected": 0,
  "filtered_out": {
    "row filter (where) did not match": 1
  },
  "links": 0,
  "coverage": {
    "text": 3,
    "verification": 2,
    "uid": 3
  },
  "confidence": {
    "text": {
      "High": 3
    },
    "uid": {
      "Exact": 3
    },
    "verification": {
      "Exact": 2
    }
  },
  "unclaimed_fields": [
    "Object Heading",
    "Object Level"
  ],
  "warnings": [],
  "invariant_ok": true
}
```

**Producing and checking one:**

```bash
reqin import export.csv --profile profile.yaml --out-dir ds/export     # writes the five files, then checks them; exit 1 if they break the contract
reqin check-dataset ds/export                                         # ok + a summary, or the list of problems (add --json for a machine-readable answer)
reqin watch inbox/ --out out/ --once                                  # every ingest is written as a dataset folder: out/<file>/<sha12>/
```

The writer never touches unrelated files: it refuses a folder that holds anything other than a dataset.

How to read it: `raw_records` (everything the source held) **always equals** `requirements` + `rejected` + the sum of `filtered_out`. `coverage` says how many requirements have each field, which is how the GUI decides which columns exist. `unclaimed_fields` are source columns nobody mapped (they are in `extra`). `warnings` are plain sentences to show. `invariant_ok: false` means records went missing: stop and show an error.

## 4. What each kind of source usually gives you

This is the real range the GUI has to cope with. It comes from what the current importers *can* provide when the file has it; a given file can have less, and a spreadsheet can have more if its mapping says so.

| Source | IDs | Statement | Hierarchy | Links | Other attributes | Fidelity |
|---|---|---|---|---|---|---|
| ReqIF (MSOSA and Cameo Requirements Modeler, DOORS, DOORS Next export) | real | yes | if the file has a hierarchy | if the file has links | whatever the tool exports | structured |
| SysML v2 (text file or REST API) | real | from `doc` text | from nesting or ownership | if the model has relationships | few | parsed / structured |
| DOORS Next over OSLC | real | yes | not yet | yes | via mapping | structured |
| Digital.ai Agility | real | yes | yes (parent) | yes (dependencies) | via mapping | structured |
| Excel, CSV, SQL (including a DOORS CSV export) | if a column exists | yes | **no, unless mapped** (a DOORS "Object Level" column lands in `extra`) | no, unless mapped | only mapped columns | tabular |
| Word, PDF | taken from the text if it contains one, otherwise invented | extracted sentences | no | no | none | extracted: a person must check every record |

## 5. What the screen must do

**5.1 Never hard-code a source.** No column names from any spreadsheet or tool in GUI code. The only field names the GUI may know are the ones in section 3 (the canonical record, the six well-known `fields` keys, the `report` keys). Any other key in `fields` or `extra` is displayed generically.

**5.2 Show what exists; say what does not.**
- A column, filter or panel for an optional field appears only if `report.coverage` has it above zero. In a record's detail view, a missing field says "not provided by this source", not a blank and not "N/A".
- No hierarchy (all `parent_mid` null): show a flat list. No links: hide the trace panel and say "this source provides no links".
- Group and filter lists are built from the values actually present, not from a fixed list.

**5.3 Show how far to trust it.**
- `uid_synthetic`: badge "ID invented by the importer".
- `fidelity: extracted`: banner "found inside prose; verify each against its page" and a per-record verified state.
- `conf` of `Medium` or `Low`: a visible cue next to that field.

**5.4 Nothing disappears silently.** On screen, always: how many were read, kept, rejected (with a list and reasons) and filtered (with reasons). The numbers must equal the report. `warnings` appear as written.

**5.5 Any size.** 0 records, 5 records and 50,000 records all work. Long lists are windowed; no layout assumes the size of any sample. Zero records shows a helpful message and the warnings, not an empty grid.

**5.6 Always jump back.** Every record offers "Show in source" using `ref` (file, sheet or document, row or page, and the revision), because a person must be able to verify any record against the original.

**5.7 Multiple sources.** Several imports can sit in one workspace. Each record carries its source (`ref.uri`, `ref.adapter`); show it as a chip. Do not assume one source per workspace.

**5.8 Text is text.** Statements can be long, multilingual, contain symbols, and contain markup remnants. Show verbatim; never truncate without a way to expand.

## 6. Test datasets the screen must pass

They already exist. `reqin make-datasets DIR` writes all fourteen (add `--only F1,F6` for some, `--size N` to change the large one; 50,000 by default, about 40 MB, so generate it rather than commit it). They are fictional, deterministic (the same bytes on every machine) and each one passes `reqin check-dataset`. Each removes one assumption. The screen is not done until it renders every one with no error, no blank panel without an explanation, and counts equal to the report.

`DIR/index.json` lists them with a machine-checkable `expect` block for each, so a browser test can compare what the screen shows with what the dataset contains:

| `expect` key | What the screen should be showing |
|---|---|
| `requirements`, `rejected`, `filtered`, `raw_records` | The counts in the header; `raw_records` = the other three added |
| `hierarchy`, `max_depth` | Whether there is a tree at all, and how deep it goes |
| `links`, `link_kinds`, `links_with_an_end_outside_the_import` | The trace panel, one entry per kind as written, outside ends marked |
| `synthetic_uids`, `duplicate_uids` | Count of "ID invented" badges; duplicate-ID warnings |
| `fidelities`, `sources` | Fidelity cues and source chips |
| `fields_present` | Which optional columns and filters exist; no others |
| `extra_keys` | How many generic "other fields" the detail view can show |
| `fields_below_high_confidence`, `warnings` | Trust cues, and warnings shown as written |

| # | Name | What is different | What must be true on screen |
|---|---|---|---|
| F1 | Minimal | 5 records: uid and text only | No empty columns, no tree, no trace panel |
| F2 | Everything | All six fields, hierarchy 4 levels deep, every link kind, extra with 10 keys | Every panel works; the deep tree is navigable |
| F3 | No IDs | Every uid is invented (uid_synthetic true) | A badge on every ID; nothing is presented as a source ID |
| F4 | Links only | Links but no hierarchy | Trace panel yes, tree no |
| F5 | Hierarchy only | Hierarchy but no links | Tree yes, trace panel hidden with a reason |
| F6 | Extracted from prose | fidelity extracted, some uid_synthetic, Medium and Low confidence, locators like p3:blk12 | Verify banner; per-record verified state; Show in source shows the page and block |
| F7 | Warnings | Duplicate UIDs and links pointing outside the import (an end with a null mid) | Warnings shown as written; outside links shown by uid and marked not in this import |
| F8 | Heavy rejection | 30 percent of the source rejected for mixed reasons, plus filtered rows | Rejected list with reasons; read, kept, rejected and filtered counts reconcile |
| F9 | Large | 50,000 requirements by default (--size changes it), a hierarchy and many links | Stays responsive; the list is windowed |
| F10 | Awkward text | Very long statements, Unicode, right-to-left text, symbols, line breaks, tabs, markup remnants, a 300-character word | Shown verbatim; expandable; no layout break |
| F11 | Two sources | Two imports in one workspace: one tabular, one structured | A source chip on every record; the fidelity cue differs per record |
| F12 | Empty | Zero requirements, a warning that says why | A helpful message with the warning, not a blank grid |
| F13 | Many unknown fields | 30 extra keys with names the screen has never seen, and two non-standard fields keys (priority, safety_class) | The Other fields panel shows them all, generically |
| F14 | Unknown link kinds | Link kinds like allocates, x-custom and Is Derived From | Shown as written; not dropped; not an error |

**The rule that keeps this honest.** When a real file breaks the screen, do not fix the screen for that file. First write down which assumption it broke, add a new row to this table and a new dataset, make the screen pass it, and only then run the real file again. A real file is never used as the specification.

## 7. Done means

1. A browser test loads every dataset listed in `index.json` (the repo already uses Playwright) with no console errors, and compares the screen with that dataset's `expect` block.
2. For every dataset, the counts on screen equal `report`: read, kept, rejected, filtered.
3. A grep of the GUI source finds no column or field name outside section 3 (a test dataset's own `extra` keys, such as in F13, must not appear in GUI code).
4. Deleting any optional field from F2 (one at a time) never leaves a blank panel or an error.
5. Every record's "Show in source" shows its `ref.locator`.
6. A folder that `reqin check-dataset` rejects is refused with the reason shown in words, never rendered as complete.
7. A person who has never seen the app can open F1, F2 and F6 and say what each tells them without help.

## 8. Prompt for the agent

> Read `GUI_CONTRACT.md` completely. Do not look at any customer or sample file yet. First run `reqin make-datasets datasets/` (if `reqin` is not available, build the fourteen datasets F1 to F14 yourself in the layout of section 3 and tell me), then build or fix the GUI so it reads **only** datasets and passes section 7, using each dataset's `expect` block in `index.json` in the browser tests. If the current GUI reads files or uses source-specific column names, move that logic out of the GUI into an importer that writes a dataset (`reqin import ... --out-dir`), and delete it from the GUI. After that, run a real file through the importer, run `reqin check-dataset` on the result and show me its output; if the GUI then fails, follow "the rule that keeps this honest" in section 6 and report which assumption broke. Do not weaken a test, and do not remove a dataset to make the suite pass. Report what is not covered.
