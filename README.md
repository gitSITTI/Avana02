# Requirements Consolidator

An app concept for opening large SysML v2 / MSOSA requirement projects, finding near-duplicate requirements mechanically first and with AI late, showing metrics for both, and treating everything as a human-verifiable draft reviewed through four lenses (SE, PE, UX, NU) before it feeds document authoring.

This repository holds the research, the design boards, the generator that makes them, a clickable prototype of the screens, and the first working code: the input layer, a reference server for shared review, and the library behind the AI data-handling gate.

## What it looks like

Everything on these screens is a synthetic sample. Click a picture for full size; the guide explains the design: [`docs/GUI_DESIGN_GUIDE.md`](docs/GUI_DESIGN_GUIDE.md). The fonts are bundled with the prototype, so the pictures show the real typefaces.

<a href="docs/images/prototype/03_home.png"><img src="docs/images/prototype/03_home.png" width="32%" alt="Home screen: what needs you, where to bring requirements in, recent imports, open clusters and latest activity"></a>
<a href="docs/images/prototype/07_cluster_review_six_wordings.png"><img src="docs/images/prototype/07_cluster_review_six_wordings.png" width="32%" alt="Cluster review: six wordings compared with one reference, changed words highlighted"></a>
<a href="docs/images/prototype/08_wordings_lined_up.png"><img src="docs/images/prototype/08_wordings_lined_up.png" width="32%" alt="The same six wordings lined up word by word in columns"></a>
<a href="docs/images/prototype/20_the_v.png"><img src="docs/images/prototype/20_the_v.png" width="32%" alt="The engineering V: requirements on the left leg, their checks on the right, and what the decisions so far do to each level"></a>
<a href="docs/images/prototype/17_results_and_grade.png"><img src="docs/images/prototype/17_results_and_grade.png" width="32%" alt="Results: a grade for the consolidated set against the original, and the parts it is made of"></a>
<a href="docs/images/prototype/18_hand_off_waiting.png"><img src="docs/images/prototype/18_hand_off_waiting.png" width="32%" alt="A cluster waiting on a teammate who was asked for a second opinion"></a>
<a href="docs/images/prototype/23_label_pairs.png"><img src="docs/images/prototype/23_label_pairs.png" width="32%" alt="Label pairs: a blind card with six answers, for building a gold set that makes the precision and recall numbers real"></a>
<a href="docs/images/prototype/24_one_requirement.png"><img src="docs/images/prototype/24_one_requirement.png" width="32%" alt="One requirement opened from the map: compared with the closest ones, decided with a reason, waiting for a colleague's sign-off"></a>
<a href="docs/images/prototype/25_trace_map.png"><img src="docs/images/prototype/25_trace_map.png" width="32%" alt="The trace map: old and new IDs, verification items, parent and child links and baselines that a decision moves"></a>
<a href="docs/images/prototype/27_ai_use.png"><img src="docs/images/prototype/27_ai_use.png" width="32%" alt="AI use: the project switch, the data sheet, what the gate did with each group and why it held some back"></a>
<a href="docs/images/prototype/28_held_group_review.png"><img src="docs/images/prototype/28_held_group_review.png" width="32%" alt="A group held back from the AI: the review page says why no AI answer is shown and carries on from the mechanical results"></a>
<a href="docs/images/prototype/09_all_requirements.png"><img src="docs/images/prototype/09_all_requirements.png" width="32%" alt="All requirements as a map: each square one requirement, colours that are also patterns and hollow squares, with a list for the keyboard under it"></a>

The twelve design boards (Excalidraw files, rendered here because GitHub cannot show them):

| | | | | |
|---|---|---|---|---|
| [![01](docs/images/boards/thumbs/01_storyboard.png)](docs/images/boards/01_storyboard.png)<br>Storyboard | [![02](docs/images/boards/thumbs/02_wireframes.png)](docs/images/boards/02_wireframes.png)<br>Wireframes | [![03](docs/images/boards/thumbs/03_system_flows.png)](docs/images/boards/03_system_flows.png)<br>System flows | [![04](docs/images/boards/thumbs/04_ui_kit_and_IA.png)](docs/images/boards/04_ui_kit_and_IA.png)<br>UI kit | [![05](docs/images/boards/thumbs/05_scale_and_multiuser.png)](docs/images/boards/05_scale_and_multiuser.png)<br>Scale |
| [![06](docs/images/boards/thumbs/06_lens_views.png)](docs/images/boards/06_lens_views.png)<br>Four lenses | [![07](docs/images/boards/thumbs/07_group_and_decisions.png)](docs/images/boards/07_group_and_decisions.png)<br>Group decisions | [![08](docs/images/boards/thumbs/08_assistant.png)](docs/images/boards/08_assistant.png)<br>The assistant | [![09](docs/images/boards/thumbs/09_more_pipelines.png)](docs/images/boards/09_more_pipelines.png)<br>Pipelines | [![10](docs/images/boards/thumbs/10_input_any_source.png)](docs/images/boards/10_input_any_source.png)<br>Any input |
| [![11](docs/images/boards/thumbs/11_the_engineering_v.png)](docs/images/boards/11_the_engineering_v.png)<br>The engineering V | [![12](docs/images/boards/thumbs/12_newer_screens.png)](docs/images/boards/12_newer_screens.png)<br>Labelling, one requirement, AI use, keeping the work | | | |

| Folder | What it is |
|---|---|
| `docs/Requirements comparison app research.md` | The research report. Appendix A = how the app reads any input. Appendix B = how the Excalidraw boards were made. |
| `docs/V_MODEL.md` | The engineering V: where the app shows it, how every number is counted (`reqin vee` uses the same rules), what is sample and what is not. |
| `docs/GOLD_SET.md`, `docs/KEEPING_THE_WORK.md`, `docs/AI_DATA_HANDLING.md`, `docs/ACCESSIBILITY.md` | How the precision and recall numbers become real (labelling pairs), what the prototype keeps and checks before a saved file replaces anything, what the AI gate is and is not, and what the accessibility checks cover and do not. Each ends with what has **not** been checked. |
| `docs/GUI_DESIGN_GUIDE.md`, `docs/images/` | How to design the review screens, how to make the Excalidraw drawings clear and good-looking, and the screenshots and board renders (regenerate with `prototype/shots.py` and `excalidraw_generator/render.py`). |
| `reqin/` | **Working code.** Reads SysML v2 (files and REST), ReqIF (MSOSA / DOORS), DOORS Next (OSLC), Digital.ai Agility, Excel/CSV, SQL, Word and PDF into one canonical model; can watch a folder of exports. Also a reference server for shared review (`SERVER.md`: no silent overwrite, roles, sign-offs, a record that verifies; the prototype is **not** connected to it yet) and the AI gate library (`aigate.py`). `INPUT_LAYER.md` is the design, `CONNECTORS.md` is how to finish and write connectors, `GUI_CONTRACT.md` is what any screen may rely on (one dataset folder, never a file) plus the 14 datasets it must pass. |
| `connector_template/` | A working, tested starting point for your own connector, with five `TODO(agent)` seams and a ready prompt for an agent. Installs as its own package. |
| `excalidraw/` | Twelve Excalidraw boards: storyboard, wireframes, flows, UI kit, scale, lenses, group decisions, assistant, pipelines, any-input, the engineering V, and the newer screens (labelling, one requirement, AI use, keeping the work, how it was checked). **Generated; do not edit by hand.** |
| `excalidraw_generator/` | The Python that produces the boards, with `EXCALIDRAW_GUIDE.md` (recipes, definition of done, prompts for an agent). |
| `prototype/` | Clickable prototype of the screens (one page, built from `parts/`). Open and Import screens show real `reqin` output; everything else is synthetic. See `prototype/README.md`. |
| `tools/` | `check_no_real_data.py`, the tripwire that keeps real program data out of the repo, and the tests that keep the licence files, the board and screenshot pictures, the Markdown links and the GitHub workflow honest. `tools/mutation/` breaks the code on purpose, one change at a time, to show that the checks notice (see its README for what the last full run found). |
| `Containerfile`, `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `Makefile` | Podman/Docker image and CI (GitHub Actions and GitLab). `make check` runs what CI runs. |
| `CONTRIBUTING.md`, `SECURITY.md` | How to change things safely, and how to report a vulnerability privately. |

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e "reqin[test]"
make check          # guard + 492 reqin tests + the connector template + rebuild all twelve boards and the prototype page, confirm they are identical
```

Try the CLI on your own export (read-only; the source file is never modified):

```bash
reqin sniff    export.reqif
reqin propose  export.xlsx > profile.yaml     # a PROPOSED mapping: edit it, it is not trusted until you do
reqin import   export.xlsx --profile profile.yaml --out reqs.jsonl
```

In a container (nothing from the host is writable except what you mount; no network needed for file sources):

```bash
make image
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  -v "$PWD/exports:/data:ro,Z" -v "$PWD/out:/out:Z" requirements-consolidator/reqin:dev \
  import /data/export.reqif --out /out/reqs.jsonl
```

## Real program data

**Do not commit real requirements, exports or models.** Not in `data/`, not "temporarily", not in a branch.
`.gitignore` blocks the usual file types, and the CI guard job (`guard:no-real-data` on GitLab, `guard` on GitHub) fails the pipeline if one gets in anyway.
The single exception is `reqin/tests/fixtures_approved/`, for anonymised excerpts that your security / export-control reviewer has approved, each recorded in `APPROVALS.md`.
To also scan for your own program code names and number patterns, set a CI/CD variable (GitLab) or repository secret (GitHub) named `FORBIDDEN_TERMS` (one regex per line). Keep that list out of the repo.

## What has and has not been checked

| Checked | How |
|---|---|
| `reqin`: 492 checks pass | Python 3.11, 3.12 and 3.13, each in a clean virtual environment (33 s each), with Node.js on the path (it runs the page-against-library comparison of the AI gate; that comparison skips itself without Node) and no LibreOffice (an optional extra test runs where it is installed). The connector template's 9 tests pass as shipped. |
| The live connectors' tests bite | 21 deliberate breaks (a leaked secret, a redirect to another host, TLS off, a write verb, paging that stops after page one, caches removed, settle time ignored, a `delete` in the DOORS script ...): 18 caught at once, 3 exposed missing tests, which were added and are now caught. 20 more on the dataset layer: all caught |
| Boards rebuild byte-for-byte; structurally valid | `make boards`, clean environment, standard library only |
| Prototype, static | The committed page equals a fresh build. `verify.js` resolves every template hole across about 1,000 states (0 issues) and holds the rules to their promises: the grade rule, the V's counts against Results, the gold-set estimator against exact answers, every pair counted in several hundred random sets, the AI gate against its table of cases, and the checks on a saved file. |
| Prototype, in a browser | Ten test files, each run at 1440, 900 and 390 px: 30 runs, all passing (about 17 minutes together): Open and Import (44 checks), the side bar, Home and the wording comparison (55 to 56), dispositions, the AI-last step, hand-offs, metrics and results (73), the engineering V (79 to 81), label pairs (74 to 75), one requirement at a time (86), the trace map (73), keeping the work (106), AI use (75) and accessibility (224). The metrics scores other than the labelled table are placeholders, and the grade rule is a proposal. The older flow scripts only print what they see. |
| Scale | `node scale.js` builds a project 20 times the sample (24,960 requirements, 5,040 clusters), draws every page, counts the gold-set pairs, and writes and reads back the project file and the trace map, each against a limit about three times what a laptop needs. It runs twice: with the sample repeated (the pair counting takes 1.5 s; the first version took 204 s) and with a varied shape, every wording different and a few very large clusters (9.6 s). At 49,920 requirements the varied shape took 42 s for that one count. **Both are made up: they test how fast, not how well, and a real corpus has its own shape.** |
| Accessibility | axe-core (WCAG 2.2 AA and best-practice rules) plus checks written for this page, on every page and several states at three widths, with no violations: contrast as drawn, field edges, the keyboard, reflow at 320 px, reduced motion, chart colours checked for red-green colour blindness. Nine deliberate mistakes were each caught by the check made for them. **No screen reader, switch device or voice control has been used with it and no person with a disability has tried it;** Chromium only; the four lens colours fail the colour-blind check for two pairs (the lens is always named in words). [`docs/ACCESSIBILITY.md`](docs/ACCESSIBILITY.md) |
| AI gate | The page and the Python library (`reqin.aigate`) give the same answer on one shared table of cases and on tens of thousands of generated inputs (the first such comparison found a real difference, which was fixed). It is a check in the application, **not a security control**: the wall is the network rule at your gateway. [`docs/AI_DATA_HANDLING.md`](docs/AI_DATA_HANDLING.md) |
| Keeping the work and the server | The prototype keeps decisions, sign-offs, hand-offs and labels in the browser and can save and load a file after checking it (106 browser checks). It is **not shared between people and not encrypted**. The reference server (`reqin/SERVER.md`: no silent overwrite, roles, sign-offs, a SHA-256 record) has 80 tests; **the page is not connected to it.** [`docs/KEEPING_THE_WORK.md`](docs/KEEPING_THE_WORK.md) |
| The checks bite | 267 deliberate changes in `tools/mutation/` (the page's logic, the AI gate, the gold set, the trace map, saving, accessibility and the reference server): 263 noticed, 4 change nothing a person can see (each explained), none missed. 17 of the 93 AI-gate changes were noticed only because the page crashed. [`tools/mutation/README.md`](tools/mutation/README.md) |
| Guard trips on what it should | 10 tests, including the real-export file types, data folders, size, missing approval entries, files not yet added to git, and that only the one reviewed DOORS script is exempt |
| Pictures, links and workflow stay true | 114 tests in `tools/` (the guard's included). Every board picture and the prototype screenshots must have been made from the current board or page; every relative link in the Markdown files must resolve; the licence files must agree and every bundled font family must ship with its licence and a notice; the prototype page must make no request to an outside host; the GitHub workflow must keep a read-only token, pinned actions and no `pull_request_target`, and name only files that exist; the browser-test runner must fail the job when a test fails; and every deliberate-change script must still match the code it changes. Each check was shown to fail on a deliberate break. |
| Secret scanning | gitleaks (pinned, checksum-verified) and a private-term list kept outside the repository run before each commit and in CI over the whole history; their tests show a planted secret and a planted term are stopped. The term list and the `DENYLIST` secret are yours to supply. [`docs/SECRET_SCANNING.md`](docs/SECRET_SCANNING.md) |
| `.gitlab-ci.yml`, `.github/workflows/ci.yml` | Both pass their platform's JSON schema; the GitHub file also passes `actionlint` 1.7.7. Each job's commands were run locally. **The current versions of both files have not run on their platforms.** An earlier, smaller GitHub workflow did run twice on the public repository and passed. |
| **Not checked** | Anything with real people or real data: the prototype has been used by nobody on a real program, and its screens use a synthetic sample. The `Containerfile` has not been built (no container engine daemon was available where it was written). **Any connector against a real system.** `sysml_api`, `oslc_rm` and `agility` are fake-server-tested only (`reqin connectors` says so); the DOORS 9 script has never run in DOORS; OAuth / form sign-in is not built. Reading real MSOSA, DOORS or SysML v2 exports: all fixtures are synthetic. Opening the boards in the live Excalidraw app. Browsers other than Chromium. Python 3.10 (not supported; 3.11+ is). |

## Next steps (not done)

1. Add one anonymised real export per source under `reqin/tests/fixtures_approved/` and run the conformance suite on it. This is the first check that matters.
2. Build the comparison engine (stages 2 to 9 in the report). The labelling page and the estimator that turn its output into precision and recall with a range are built (`docs/GOLD_SET.md`); the engine they would measure is not.
3. Connect the page to the reference server (shared work, sign-in, a record the server verifies), then build the real UI in place of the prototype.
4. Run both CI files on their platforms, add the `DENYLIST` secret (GitHub) or `DENYLIST_FILE` variable (GitLab) and your own term list, and put the network rules in front of any model host (`docs/AI_DATA_HANDLING.md`).
5. Have people use the prototype with a screen reader and with the keyboard alone, and label real pairs with two labellers.

## License and contributing

Apache License 2.0: see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Copyright 2026 gitSITTI. Some bundled files are not covered: `prototype/project/support.js` is a copy of React (MIT) and `prototype/project/fonts/` holds three font families (SIL Open Font License 1.1). Both are listed with their licences in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

This is a research prototype and comes **as is**, without warranty (see sections 7 and 8 of the licence). Read "What has and has not been checked" above before relying on it: no connector has been run against a real MSOSA, Teamwork Cloud, DOORS or Agility system.

Secrets and private names are checked before every commit and again in CI over the whole history (gitleaks at a pinned, checksum-verified version, plus a private-term list that is kept outside the repository): [`docs/SECRET_SCANNING.md`](docs/SECRET_SCANNING.md).

Contributions are accepted under the same licence: see [`CONTRIBUTING.md`](CONTRIBUTING.md). Never commit real requirements, exports or models; the guard described above exists to stop that, and a pull request that trips it will not be merged. Report vulnerabilities privately: [`SECURITY.md`](SECURITY.md).
