# Mutation runs: do the checks notice when something is broken?

A test that cannot fail proves nothing. These scripts check the checks. Each one makes **one change at a time** in a throwaway copy of the code (a comparison flipped, a
rule removed, a number off by one), runs the project's own checks on the copy, and reports whether they noticed. The real files are never touched: every run works in a
temporary folder that is deleted when the script ends.

| Script | What it breaks | The checks that must notice | Changes |
|---|---|---|---|
| `ai.py` | The AI gate: markings, the data sheet, the order of the rules, the switch, what is written to the record, what Home says | `prototype/verify.js` (and the shared cases in `docs/ai_gate_cases.json`) | 93 |
| `gold.py` | The gold set's estimator: weights, ranges, recall, what a pair counts as, the queue, blind labelling | `prototype/verify.js` | 15 |
| `population.py` | The shortcuts that count and draw pairs at tens of thousands of requirements (the indexes, the exact counts, the drawing) | `prototype/verify.js`, which counts every pair in several hundred random and boundary-case sets | 17 |
| `keep.py` | Keeping the work: the checks on a loaded file, the browser copy, two tabs | `prototype/verify.js` | 53 |
| `trace.py` | The trace map: what a decision moves outside the requirement list | `prototype/verify.js` | 30 |
| `vee.py` | The engineering V: the counts at each level | `prototype/verify.js` | 10 |
| `compare.py` | The comparison engine: every written slot, number and wording rule, the clustering, the quantity and slot extraction, the stemmer and vocabulary, the output folder and its checker | `reqin/tests/test_compare.py` | 199 |
| `connectors.py` | The connectors written from vendor documentation: Jira, Polarion and Jama (paging, totals, link direction and de-duplication, rejected logins, option errors), the `.xmi` / `.mdzip` reader (the DOCTYPE check, size limits, which entry is the model, stereotypes, nesting, link ends and kinds, document order), the Agility reader, the OSLC configuration handling, the `sql` adapter's read-only guard, parent column and links query, the DOCTYPE check the readers share, and the count of links that leave an import | the connector tests together (`reqin/tests/test_connect.py`, `test_live_connectors.py`, `test_connectors_more.py`, `test_connector_edges.py`, `test_sysml1_xmi.py`, `test_sql_packs.py`, `test_reqif_archives.py`, `test_behaviour.py`, `test_doors9.py`) | 178 |
| `server.py` | The reference server: every rule `reqin/SERVER.md` promises (no silent overwrite, roles, sign-offs, the record, idempotency) | `reqin/tests/test_server.py` | 40 |
| `a11y.py` | The page's accessibility: a faint field edge, no page title, no skip link, no focus ring, faint text, an unnamed button, a click-only control, sideways scrolling at 320 px, look-alike chart colours, look-alike lens colours, a pale lens colour, look-alike gate bars | `prototype/b20.py` in a browser, **on the check made for that mistake** | 12 |

## Running them

```bash
python3 tools/mutation/ai.py                      # every change in that script (about half an hour; each one builds the page and runs verify.js)
python3 tools/mutation/ai.py "leading slash"      # only changes whose name contains this text
python3 tools/mutation/ai.py --list               # the names
python3 tools/mutation/ai.py --patterns           # fast: does every change still match the code? (runs no checks)
```

Each change prints one line:

- `CAUGHT (n): ...` the checks failed, and this is the first thing they said. A crash counts: the change was noticed, though not by a gate written for it.
- `NOT CAUGHT` the checks all passed on broken code. **That is a missing check.** Write the check, then run the change again.
- `PATTERN MISSING` the code the change edits has been rewritten, so the change tests nothing. Update the change.
- `not noticed, and harmless: ...` listed in the script's `EQUIVALENT` table with the reason: the change alters how fast the code runs, not what it answers.

The exit status is 1 when any change went unnoticed and is not listed as harmless. A full run is slow, so CI does not run it. CI does run `tools/test_mutation_scripts.py`,
which checks, in under a second, that every change still matches the code, so the scripts cannot quietly rot.

## Adding a change

Add a row `(name, file, old text, new text)` to the script's list. The old text must occur in the file; the first occurrence is replaced. Pick the change a careless
edit would make, not a random one. If the checks do not notice it, add the check first.

## What the last full run found

Run on 14 October 2026 on the final code of this commit, one script after the other on one machine. Run them again after you change the code they break.

| Script | Changes | Noticed | Not noticed, and harmless | Not noticed | Time |
|---|---|---|---|---|---|
| `vee.py` | 10 | 10 | 0 | 0 | 3 min |
| `gold.py` | 15 | 15 | 0 | 0 | 6 min |
| `population.py` | 17 | 14 | 3 | 0 | 5 min |
| `trace.py` | 30 | 30 | 0 | 0 | 10 min |
| `keep.py` | 53 | 52 | 1 | 0 | 17 min |
| `ai.py` | 93 | 93 | 0 | 0 | 28 min |
| `server.py` | 40 | 40 | 0 | 0 | 2 min |
| `a11y.py` | 12 | 12 (each by the check made for it) | 0 | 0 | about 13 min |
| **All** | **267** | **263** | **4** | **0** | |

The times are with other jobs (the browser tests) running at the same time, so alone they would be shorter.

**`compare.py` was run separately, on 15 October 2026,** on the code of the comparison engine after the adversarial review (the table above is the earlier run and does not include it): 199 changes. The first full run noticed 192, listed 1 as harmless and did not notice 6. For five of those six a test was added (two pairs that must never be called equivalent, the stemmer leaving short words and words with other characters alone, a bound with no direction having no interval in the slots, and a number such as `0,500,500` not stopping the run), and those five changes were then run again on their own: all five were noticed. The sixth was read by hand and judged harmless (below). **The full run was not repeated after the tests were added**, so "197 noticed, 2 harmless" is the full run plus the five re-runs plus one reading of the code. The full run took about half an hour on one machine (a shared cloud container).

The two harmless ones, each listed in `compare.py`'s `EQUIVALENT` table with its reason: "any overlap is enough for a near miss (engine)", because the same threshold is applied again inside `classify()`, which a test checks on its own, so removing either copy leaves the other in force; and "COND-REGION is said when the other side has no region trigger", because a number in a condition is only compared when the two conditions have equal keys and a key starts with its trigger word, so both sides have the same trigger and the check on side B repeats the check on side A (this one rests on reading the code, not on a test).

**`connectors.py` was run on 15 October 2026** on the code of this commit (a shared cloud container, about an hour for the whole script). **The first full run noticed 122 of the 178 changes and did not notice 56.** Of the 122, two were noticed only because the run's 150-second clock killed a test run that was looping (a repeated page token in Jira, and a Polarion page that adds nothing new), and one only because the changed code ate the run's memory ceiling (a Polarion work item that comes back twice). Those three are real catches, since nobody could ship a connector that hangs, but they are slow and say nothing about the rule. The script now prints them as `CAUGHT, ONLY BY THE CLOCK` and `CAUGHT, ONLY BY THE MEMORY CEILING`, and the loop tests carry a request cap (`max_requests=50`) so a missing guard fails in a second.

The 56 were in Jira (6), Polarion (8), Jama (14), the `.xmi` reader (20), Agility (5), OSLC (1) and the `sql` guard (2). Among them: paging that skips rows when a server returns fewer than it was asked for (Jira, Jama); a short last page not taken as the end; Jira's `isLast`; the Jira revision ignoring `updated`; links with an empty end; replies that are not the expected shape; a rejected login in an optional lookup (Jama); two projects with one name; Polarion links (the same link seen from both items, an id of the wrong shape, an included resource with no target, a next link with no scheme, a decoy among the included resources); Jama pick lists and custom fields named like built-ins; in the `.xmi` reader a DOCTYPE in the first 64 KB, 16 MB before the first element, both size limits, which entry is the model, stereotypes on things that are not classes, the comment and profile forms, the order of requirements and the kinds and counts of links; the Agility XML forms; an empty RDF answer from OSLC; and two holes in the `sql` guard (a second harmless statement, and `VALUES`, `EXPLAIN` or `SHOW` in place of a SELECT). **For 54 of them a test was written** (`reqin/tests/test_connector_edges.py`, 71 tests, which bend one reply of a documentation-shaped fake with `reqin.testing.Tweaked`). One was read and judged harmless (below). One was a check in the `.xmi` reader that no test could tell from its neighbour because the neighbour already did the work: it was removed from the code and its change replaced by one on the line that remains. Writing the empty-end tests also found a small bug: a link end that is `null` in the JSON was read as the text "None" (Jira and Jama). It is now an empty end and the link is skipped.

**The whole script was then run again, from the start: 178 changes, 177 noticed by a test, 1 harmless, 0 missed, none noticed only by the clock or the memory ceiling.** The log cuts each first message at 100 characters, so this run did not count how many of the 177 were crashes rather than failed assertions. This is a statement about the tests and the documentation-shaped fakes. **It says nothing about a real Jira, Polarion, Jama, MSOSA or Agility.**

The harmless one, listed in `connectors.py`'s `EQUIVALENT` table: "an item with no parent gets the parent 'None'" (Jama). The next step sets every parent that is not one of the records to none, and the text "None" is not the id of a record (Jama ids are numbers).

**What `connectors.py` does not cover:** `sysml_api`, `sysml_text`, `tabular`, `reqif_adapter`, `docx`, `pdf`, the DXL script, the Jama token helper (`reqin/connectors/jama/jama_oauth_hook.py`, the only code in the repository that sends a POST, which has never run), the rest of `connect.py` (12 tests run it against real local HTTP and HTTPS servers, but nothing breaks it on purpose here) and `oslc_rm.py` beyond the configuration handling and the empty-answer check. A rule in those files that nobody thought to break is not shown to be checked by this run.

**Not noticed, and harmless (4).** Each is listed in its script's `EQUIVALENT` table with the reason, and was looked at by hand:

- `population.py`, "shared-word test counts once": the cheap pre-check lets more pairs through; every pair still gets its exact score, so the answers are the same.
- `population.py`, "start trim ignores the end": when one side is empty, `n + m` and `max(n, m)` are the same number. A change that changes nothing.
- `population.py`, "repeated words counted as one": numbering repeated words only makes the filter tighter. Without it the filter stays complete, and the pair counts are identical (also at 24,960 requirements with `node scale.js`).
- `keep.py`, "a save is not debounced": during a burst of changes the page writes more often, but each write holds the whole current state and a write of an unchanged state is skipped, so what is kept is the same. It could cost time on a very large project; nothing times the autosave on its own.

**A weaker kind of "noticed".** A change counts as noticed when the checks fail on it, and a crash is a failure. 17 of the 93 changes in `ai.py`, and 1 to 2 in each of `vee.py`, `gold.py`, `population.py`, `trace.py` and `keep.py`, were noticed only because the page threw an error and the checks never got to run, not because a check written for that rule failed. They are real catches (nobody could ship a page that crashes), but a check aimed at the rule would say more. `ai.py --list` and a run with `CAUGHT (1): TypeError` lines show which.

**What this does not show.** These are changes somebody thought of. A rule nobody thought to break is not covered, and the scripts cannot show that a rule is *right*, only that the checks would notice if it stopped being what they expect. They cover the prototype's logic, its accessibility run and the reference server; they do not cover `reqin`'s older file importers (`tabular`, `reqif_adapter`, `docx`, `pdf`, `sysml_text`). `connectors.py`, above, covers the connectors written from vendor documentation.
