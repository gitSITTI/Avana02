# Interactive prototype

A clickable prototype of the app's screens, built as a single `Main.dc.html` page (the design-canvas format: `<x-dc>` templates with `{{holes}}`, one `Component` class). **Every number in it is synthetic**, except the Open and Import screens, whose counts, mapping labels and locators are the real output of `reqin` run on its fixtures.

| Path | What it is |
|---|---|
| `parts/m/*.html` | The screens, one file per screen. Edit these. |
| `parts/*.js` | Data (`data*.js`), logic (`logic*.js`, `misc.js`) and the component (`c1-c3.js`). |
| `build.py` | Joins the parts into `project/Main.dc.html`. **Never edit `Main.dc.html` by hand.** |
| `verify.js` | Static check: every `{{hole}}` in the template resolves to a value of the right kind, across about 1,000 generated states. It also holds the grade rule to its promises (a perfect set gets an A and 100, an empty set is not graded, one loosening merge holds an A at C, the destinations add up to the originals). Exits 1 on any issue. |
| `b11.py` | Browser test with assertions for the Open, Import, Change and Verify flows (44 checks, run at 1440, 900 and 390 px). |
| `b12.py` | Browser test with assertions for the side bar and top bar, the Home screen, and the wording comparison including the "Line up the words" window (56 checks at 1440 px, 55 at 390 px). |
| `b13.py` | Browser test with assertions for what happens to each requirement, the AI-last step, sending a cluster to a teammate and the answers, the metrics page controls, and the results page (73 checks at each of 1440, 900 and 390 px). |
| `b0.py` to `b10.py`, `t0.py` | Older flow scripts: they drive every other screen and print what they see. They do not assert; compare their output before and after a change. |
| `shots.py` | Retakes the pictures in `docs/images/prototype/` and records which page build they came from. |
| `project/support.js` | The runtime that the design-canvas format needs. It is not authored here (it bundles React under the MIT license). |

```bash
python3 build.py                          # rebuild project/Main.dc.html from parts/
node verify.js project/Main.dc.html       # static check; prints ISSUES 0
# browser tests (need Playwright for Python and a Chromium; set CHROMIUM_PATH if it is not auto-found)
(cd vendor && npm ci)                     # React and Babel for the local harness
python3 b11.py 1440 && python3 b11.py 390
python3 b12.py 1440 && python3 b12.py 390
python3 b13.py 1440 && python3 b13.py 390
```

CI runs the first two (GitLab: `prototype:build-identical`, `prototype:verify`; GitHub: the `prototype` job). The browser tests are run by hand: `make proto-test`.

**Fonts and network.** The page carries its own fonts: Public Sans (interface), Source Serif 4 (requirement wording) and JetBrains Mono (identifiers), as `.woff2` files in `project/fonts/` with their licences (SIL Open Font License 1.1). It makes no request to any other site, so it looks the same offline and on a locked-down network. `tools/test_prototype_offline.py` fails if a link to an outside host is added.

## Open and Import screens (board 10, made interactive)

* Open: six source cards, each with a trust level in words (Structured, Tabular, Parsed, Extracted; `.mdzip` says "not read directly yet" and offers the ReqIF route). A drop zone names what a sample file would be recognised as.
* Import: a proposed mapping with a label per row, a **Change** control that edits the profile, a dry-run report that recounts as you change things, the first three records as the review screens will show them, and the profile as YAML.
* Word or PDF: an extra step to **verify each found statement** against the page, with its location, an invented-ID warning, and a source-page view.

What is not real: nothing is read from your computer, no server is contacted, and nothing is saved. The workspace after Import always uses the same synthetic 1,248-requirement sample. The SysML v2 API route ("systems v2" recent project) is illustrative: its field names are assumed in the reference code and untested against a real server.

## Home screen and the wording comparison

* Home: a dark band that says sources are read-only; the project title with three source chips (spreadsheet or CSV, ERP database, Word or PDF); recent imports as expandable rows; four bars for where the open clusters stand (a bar opens that part of the queue); and recent activity. "ERP database" is not a source `reqin` reads. The chip opens the read-only SQL query route and says so.
* Comparing wordings, which replaced the earlier A and B cards: one wording is the **reference** (the strictest that can be ranked, or one you pick with "Use as reference"). Every other member is shown as a redline against it: matched words are faded, and each difference is a coloured chip (number, unit, shall or should, not, condition, other). A ledger underneath lists what the wordings do not carry in the words, such as different parent requirements or owners.
* "Line up the words" opens a window that aligns all the wordings in columns, with gaps where a member lacks a word the others have. It is a window, not a section of the page, so it can use the full width. It moves focus into itself, keeps Tab inside, closes on Escape and gives focus back.
* The comparison is word-level and mechanical. It does not understand meaning: two wordings that say the same thing in different words show as many differences, and a swapped number inside a longer phrase can show as a replacement rather than a change of value. That is why the guards and the human decision stay.

## Dispositions, hand-offs, metrics and results

* **What happens to each requirement.** In the cluster, every member carries a disposition chip (Keep, Merged into M4, Stays separate, Kept and linked, Waiting for the owners, Superseded) and a one-line reason built from the comparison. It is a preview while you choose and a record once you decide. The code is `dispositionsOf` in `parts/logic1.js`.
* **Mechanical first, the AI last.** The Resolve panel runs: what happens, which wording survives (most stringent, least, median, one member, your own), then an optional AI step that opens with a summary of what the mechanical steps decided. The scorecard on the metrics page also scores the AI first, then the mechanical steps.
* **Send to a teammate.** `S.hand[clusterId]` holds the request (who, what was asked, the message, the sender's draft, status). Three kinds: a second opinion before you record, "please decide this one", and "please review this decision". The sender sees "Waiting on", recording pauses, the teammate agrees or sends it back (a comment is needed to send back), and every step is in the event chain. A second opinion counts as "checked by" only if you then record what they agreed to.
* **Methods and metrics.** Four ways of working (mechanical only, mechanical then AI, AI then mechanical, AI only), each mechanical method with the AI after and before, and a category-by-category comparison with and without the AI. **All of the scores on that page are placeholders** (`parts/data4.js`) until a human-labelled set exists. The blocks marked "live" come from the decisions in the session.
* **Results and grade.** A letter and a score computed from the decisions by `resultsOf` in `parts/logic3.js`: Accounted for 20 points, Obligations preserved 30, Signed off 20, The why is written down 15, A second pair of eyes 15. A is 90 and over, B 80, C 70, D 60, F below. A merge that loosens a requirement without both the owners and the process engineer having signed holds the letter at C. The grade is provisional (dashed box) until 90 percent of the clusters are decided, and stale or disputed decisions do not count. **The weights and bands are a proposal for a team to agree, not a standard**, and the decisions that ship with the sample are sample data.
