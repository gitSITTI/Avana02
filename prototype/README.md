# Interactive prototype

> **To build a real screen, do not start from this page.** It is a generated picture of the product with a synthetic sample: its numbers and names are typed in and its colours are literal, so a copy shows the sample in the wrong look. Read `parts/` to see what a screen contains, then build from [`design/`](../design/README.md) and follow [`docs/agent_prompts/build_the_gui.md`](../docs/agent_prompts/build_the_gui.md).

A clickable prototype of the app's screens, built as a single `Main.dc.html` page (the design-canvas format: `<x-dc>` templates with `{{holes}}`, one `Component` class). **Every number in it is synthetic**, except the Open and Import screens, whose counts, mapping labels and locators are the real output of `reqin` run on its fixtures.

| Path | What it is |
|---|---|
| `parts/m/*.html` | The screens, one file per screen. Edit these. |
| `parts/*.js` | Data (`data1-4.js`), logic (`logic1-3.js`, `misc.js`), the gold-set estimator (`gold.js`), single requirements (`single.js`), the trace map (`trace.js`), the AI gate (`aigate.js`), keeping the work (`persist.js`) and the component (`c1-c8.js`). |
| `build.py` | Joins the parts into `project/Main.dc.html`. **Never edit `Main.dc.html` by hand.** `REQIN_SCALE=20 python3 build.py DIR` builds a test project with 20 times the sample, for the scale test. |
| `verify.js` | Static check: every `{{hole}}` in the template resolves to a value of the right kind, across about 1,000 generated states. It also holds the rules to their promises: the grade rule (a perfect set gets an A and 100, an empty set is not graded, one loosening merge holds an A at C), the V's counts against Results, the gold-set estimator against exact answers (a census gives the exact precision and recall; the range holds the exact answer in 95 of 100 random samples), every pair counted in several hundred random and boundary-case sets, the AI gate against the table of cases it shares with the Python library (`docs/ai_gate_cases.json`), and the checks on a saved file (good and deliberately damaged ones). Exits 1 on any issue. |
| `b11.py` to `b20.py` | Browser tests with assertions, listed below. `run_browser_tests.py` runs all of them at the widths each is meant for (30 runs). |
| `h.py` | The harness: serves `project/` and opens it in headless Chromium with React from `vendor/`. |
| `a11y_page.js`, `chart_colours.py`, `vendor/` | What `b20.py` measures with: checks written for this page (contrast as drawn, field edges, Tab stops), the colour-blind check for chart palettes, and the pinned libraries (React, Babel, axe-core). |
| `scale.js` | The scale test: 20 times the sample (24,960 requirements, 5,040 clusters) in two shapes (the sample repeated, and a varied one), every page drawn and timed, the gold-set pair counts, the project file and the trace map file. |
| `b0.py` to `b10.py`, `t0.py` | Older flow scripts: they drive every other screen and print what they see. They do not assert; compare their output before and after a change. |
| `shots.py` | Retakes the pictures in `docs/images/prototype/` and records which page build they came from. `design/adopt_design/scripts/make_frames.py` does the same for the frame pictures in `docs/images/frames/` (it uses `h.py`). |
| `requirements-test.txt` | The pinned Playwright the browser tests and the CI image use. |
| `project/support.js` | The runtime that the design-canvas format needs. It is not authored here (it bundles React under the MIT license). |

The browser tests, each at 1440, 900 and 390 px wide unless noted:

| File | What it checks (assertions) |
|---|---|
| `b11.py` | Open, Import, Change and Verify flows (44) |
| `b12.py` | The side bar and top bar, Home, the wording comparison including "Line up the words" (56 at 1440 px, 55 at the others) |
| `b13.py` | What happens to each requirement, the AI-last step, sending a cluster to a teammate and the answers, the metrics page controls, the results page (73) |
| `b14.py` | The engineering V: the page, the small V in every header, the strip on a cluster, the filters, keyboard order and focus, names for a screen reader (79 at 1440 px, 81 at the others) |
| `b15.py` | Label pairs (the gold set): the blind card, the keyboard, undo, a second labeller, settling, the sample labels, the file, the measured table (74 at 1440 and 900 px, 75 at 390 px) |
| `b16.py` | One requirement at a time: compare, decide, sign off, and see it counted on Results, the V and the ledger (86) |
| `b17.py` | The trace map: tables, two real downloads, the same numbers before and after a decision, a baselined requirement needing a change request (73) |
| `b18.py` | Keeping the work: autosave, restore, save, load and what is refused, start over, blocked and full storage, two tabs (106) |
| `b19.py` | AI use: the page, the switch, the data sheet form, a held group in review and in the assistant, what is kept and written (75) |
| `b20.py` | Accessibility: axe-core on every page and state, contrast as drawn, the keyboard, reflow at 320 px, reduced motion, chart colours (224) |

```bash
python3 build.py                          # rebuild project/Main.dc.html from parts/
node verify.js project/Main.dc.html       # static check; prints ISSUES 0
node scale.js 20 sample                   # 24,960 requirements, the sample repeated; prints SCALE OK (about 10 seconds)
node scale.js 20 varied                   # the same size, a different shape (mostly different wordings, very large clusters); about 20 seconds
# browser tests (need Playwright for Python and a Chromium; set CHROMIUM_PATH if it is not auto-found)
(cd vendor && npm ci)                     # React, Babel and axe-core, pinned by package-lock.json
pip install -r requirements-test.txt && python -m playwright install --with-deps chromium
python3 run_browser_tests.py              # all 30 runs, one browser at a time (they share a port)
python3 run_browser_tests.py b20 --width 390   # one file, one width
python3 b15.py 1440                       # or a file on its own
```

CI runs the build comparison, `verify.js`, the browser tests (`run_browser_tests.py`) and the scale test on both GitHub Actions and GitLab; `make check-full` runs the same things here. GitHub CI ran on 2026-10-21: Chromium and WebKit passed; Firefox reported five keyboard failures in `b20.py` at 1440 px. GitLab execution remains unverified. See the [run](https://github.com/gitSITTI/Avana02/actions/runs/39619948023). A deliberate break of the page makes the jobs fail; `tools/mutation/` shows it for each area (see its README).

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

## The engineering V

* **What it is.** The V pairs each level of requirements down the left (needs, system, subsystem, component) with the check that proves it up the right (validation, then system, subsystem and component verification). Every workspace screen has a small V in its header that opens the V page; Home, the cluster, Results and Export each say what it means for them. The account of the rules, and what is sample, is in [`docs/V_MODEL.md`](../docs/V_MODEL.md).
* **One rule for what counts.** `standingDec` in `parts/logic3.js` says when a cluster has a decision that counts. The V, the Results page and the review queue all use it, so they cannot disagree. `veeOf` counts the levels; `verify.js` checks it against `resultsOf` (requirements after decisions must be equal) and against its own independent count of "traced".
* **Sample values.** The level, verification method and verification items of each requirement are generated from its ID (`vHash` in `parts/logic3.js`), because the sample has no real ones. The page says "Sample values". `reqin vee` is the real thing: it works the same numbers out from an imported dataset.

## Dispositions, hand-offs, metrics and results

* **What happens to each requirement.** In the cluster, every member carries a disposition chip (Keep, Merged into M4, Stays separate, Kept and linked, Waiting for the owners, Superseded) and a one-line reason built from the comparison. It is a preview while you choose and a record once you decide. The code is `dispositionsOf` in `parts/logic1.js`.
* **Mechanical first, the AI last.** The Resolve panel runs: what happens, which wording survives (most stringent, least, median, one member, your own), then an optional AI step that opens with a summary of what the mechanical steps decided. The scorecard on the metrics page also scores the AI first, then the mechanical steps.
* **Send to a teammate.** `S.hand[clusterId]` holds the request (who, what was asked, the message, the sender's draft, status). Three kinds: a second opinion before you record, "please decide this one", and "please review this decision". The sender sees "Waiting on", recording pauses, the teammate agrees or sends it back (a comment is needed to send back), and every step is in the event chain. A second opinion counts as "checked by" only if you then record what they agreed to.
* **Methods and metrics.** Four ways of working (mechanical only, mechanical then AI, AI then mechanical, AI only), each mechanical method with the AI after and before, and a category-by-category comparison with and without the AI. The first table (the app's clusters, text match and keyword overlap) is measured from the gold set once people have labelled pairs (next section). **Every other score on that page is still a placeholder** (`parts/data4.js`), and says so. The blocks marked "live" come from the decisions in the session.
* **Results and grade.** A letter and a score computed from the decisions by `resultsOf` in `parts/logic3.js`: Accounted for 20 points, Obligations preserved 30, Signed off 20, The why is written down 15, A second pair of eyes 15. A is 90 and over, B 80, C 70, D 60, F below. A merge that loosens a requirement without both the owners and the process engineer having signed holds the letter at C. The grade is provisional (dashed box) until 90 percent of the clusters are decided, and stale or disputed decisions do not count. **The weights and bands are a proposal for a team to agree, not a standard**, and the decisions that ship with the sample are sample data.

## Label pairs, one requirement and the trace map

* **Label pairs (the gold set).** A blind card shows two requirements without saying what any method thought; a person picks one of six answers. The pairs are drawn from four groups on purpose and weighted by the number of pairs each stands for, so a few hundred labels give a precision and recall with a range, not just a middle. Every fifth pair goes to a second person, and a lead settles disagreements. "Load sample labels" fills the page with made-up labels that are marked as samples everywhere. The rules, the estimate and what it does not cover are in [`docs/GOLD_SET.md`](../docs/GOLD_SET.md); the code is `parts/gold.js`.
* **One requirement at a time.** On All requirements, any requirement (also one nothing was found similar to) opens in a panel: what the methods found, the five closest in its allocation to put beside it, and a decision with a reason code and a note (`parts/single.js`). Decisions on single requirements count on Results, the V and the ledger like cluster decisions, and are signed off under the sign-off policy (the person who decided cannot sign it).
* **The trace map.** A merge, a supersede or a drop changes more than the list: verification items must be pointed at the survivor, child requirements need a new parent, baselines need to follow. Export lists old and new IDs, items, parent and child links and baselines, and offers two real downloads (`trace-map.json` and `alias-map.csv`, from `parts/trace.js`). The levels, items, links and baselines are sample values and the files say so. A baselined requirement needs a change request.

## Keeping the work

What people decide, sign, write and label is kept in this browser by itself (about 350 ms after a change, and when the tab closes), and can be saved to a file and read back. A file is checked before it replaces anything: its format, the project it belongs to, the kind of every item, the chain of the record of events, that the AI switch and data sheet agree with their own record, and that every screen can draw it. A file that fails is refused; entries for things the project does not have are left out and counted. Two tabs of one browser cannot write over each other. The card is on Home. [`docs/KEEPING_THE_WORK.md`](../docs/KEEPING_THE_WORK.md) has the whole list, and says what this is not: **not shared between people** unless you sign in to the reference server (next section), **not encrypted**, not tamper-proof (the fingerprints in the record are a short demonstration hash, not SHA-256), not a backup. The code is `parts/persist.js` and `parts/c7.js`.

## Working with a team: the shared project

Open the page from the reference server (`http://<server>/app/`, see [`reqin/SERVER.md`](../reqin/SERVER.md)), paste the token you were given into the card on the opening screen or Home, and press *Sign in*. From then on the project is the server's one copy: your login decides who you are, your lens and what you may change; what you decide, sign, hand off, claim, object to and label is sent a moment later; what others do appears within a few seconds; the lead's AI switch and data sheet are everyone's. Without signing in the page is the stand-alone one it was.

What it does when things go wrong, each with a browser test (`b21.py`, four people in four browsers on one real server, at three screen widths):

* **Someone got there first.** The second change to the same decision is refused by the server. A notice on top of the page you are working on (not only on Home) says who changed it, when, what you tried and what stands now; the page shows what stands. Nothing is merged silently, and the same body is never sent again.
* **A cluster you have open was changed.** A banner names who changed it; deciding is paused until you reload it.
* **No network.** The shell says *Shared · offline* and how many changes wait; they are sent once when the server answers (a lost answer is retried with the same key, so the server does it once).
* **The server stops accepting your token**, or its record becomes shorter or different from the one the page saw: the page stops sending and reading and says so.
* **The record.** *Check the shared record* asks the server to recompute its whole record; a document edited on the server's disk is named, at its entry.
* **Nothing is kept in this browser while you are signed in** (the autosave stops; *Load from a file* and *Start over* are off); the token is held in the page only. Signing out puts back what the browser had before, including what you had typed. *Save to a file* still saves what you see.

What it is **not**: there is no sign-in to a company directory (a token is a password for one person, made by whoever runs the server), no TLS in the server itself (put a proxy in front), the page polls every 4 seconds rather than being pushed to, and nobody has used it on a real project. The policy engine, results grade and trace map are still computed in the page from the shared documents.

To try it: `python3 reqin/serve_standalone.py demo --db /tmp/demo.db --seed prototype/demo/seed.json --app prototype/project` starts a demo project (six people, sample activity) and writes one token per person to `/tmp/demo.db.tokens.json`. Nothing needs installing but Python.

## AI use

One project-wide switch, one AI data sheet (what the approvers were told about the model), a marking on every requirement, and a gate that runs before any text could go to a model (`parts/aigate.js`). A group is as restricted as its most restricted member; a sheet that contradicts itself, or has no reviewer and date, opens nothing; a classified or unrecognised marking is never sent. The AI use page shows what the gate did with each group and why, and a held group is still reviewed by people from the mechanical results (the sample AI answers that exist are hidden for it). The same rules are written in Python (`reqin/src/reqin/aigate.py`), and a table of cases (`docs/ai_gate_cases.json`) plus a random comparison in `reqin/tests/test_aigate_page.py` fail if the page and the library ever disagree: that comparison found a real difference when it was first written (how a marking and blank names are read), which was fixed. **A switch in a web page is not a security control.** The wall is the network rule at your gateway; [`docs/AI_DATA_HANDLING.md`](../docs/AI_DATA_HANDLING.md) says what the gate is, what it is not and what your IT staff still have to do.

## Scale

`node scale.js 20 sample` builds a page with 20 times the sample (24,960 requirements, 5,040 clusters) in a temporary folder and times what a person waits for. The first drawing of every page, the drawing after a change, the one-off counting of pairs for the gold set (which was once quadratic and took 204 s at this size), writing and reading back the project file, and the trace map file each have a limit about three times what a laptop needs; the run also checks that counts are still true at that size and that memory stays within bounds. `SCALE_SLACK=2` doubles every limit for a slow machine.

**The sample repeated is kind to the counting of pairs**, because only one in five of its wordings is different and the pair counts are made once per different wording. So there is a second run, `node scale.js 20 varied`: the same number of requirements and clusters, but every wording different (a seeded stream of made-up words added to each, 6 to 34 words long), about three in ten requirements in one allocation, and 51 clusters of 40 to 200 members. The run prints what shape it got and fails if the project is not varied, so it cannot quietly turn back into the repeated sample. Measured on the machine this was written on:

| | sample repeated | varied |
|---|---|---|
| Requirements, clusters | 24,960, 5,040 | 24,960, 5,040 |
| Different wordings | 20 % | 100 % |
| Counting the pairs for the gold set (the slowest step) | 1.5 s (limit 19 s) | 9.6 s (limit 34 s) |
| Slowest other step (the first drawing of All requirements) | 0.5 s (limit 4 s) | 0.8 s (limit 4 s) |
| Memory in use at the end | about 100 MB | 200 to 400 MB (limit 1,500 MB) |

The pair counting grows faster than the project does on the varied shape: at 49,920 requirements (`node scale.js 40 varied`) it took 42 s. That is a one-off count made the first time the Methods or Gold set page is opened, and it is kept afterwards; there is no promise for projects of that size. **Both shapes are made up. They test how fast, not how well: nothing here says whether the comparison would find the right pairs in a real corpus, and a real corpus has its own shape that neither run reproduces.**

## Accessibility

`b20.py` runs axe-core (WCAG 2.2 AA and best-practice rules) and checks written for this page on every page and on the states that open more of a page, at three widths: contrast as drawn, the edges of fields, the keyboard from the first Tab stop (a skip link), a visible focus ring on every stop, landmarks, titles, announcements, reflow at 320 px, reduced motion, and the colours of the two charts that use colour to tell marks apart (checked for red-green colour blindness). Automated checks find a part of the problems: **nobody has used the page with a screen reader or with a switch or voice control, and no person with a disability has tried it.** Chromium only. [`docs/ACCESSIBILITY.md`](../docs/ACCESSIBILITY.md) lists what is checked, what changed because of it, what was shown to fail on purpose, and what has not been checked.

## Do the checks check?

A test that cannot fail proves nothing. `tools/mutation/` makes one change at a time in a throwaway copy of the code (a comparison flipped, a rule removed, a number off by one) and asks whether the checks notice: `ai.py`, `gold.py`, `population.py`, `keep.py`, `trace.py`, `vee.py`, `a11y.py` (the page) and `server.py` (the reference server). Its README says what each one breaks and records what the last full run found. A fast check (`tools/test_mutation_scripts.py`, part of CI) makes sure every change still matches the code, so the scripts cannot quietly stop testing anything.
