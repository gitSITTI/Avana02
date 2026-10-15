# Requirements Consolidator

An app concept for opening large SysML v2 / MSOSA requirement projects, finding near-duplicate requirements mechanically first and with AI late, showing metrics for both, and treating everything as a human-verifiable draft reviewed through four lenses (SE, PE, UX, NU) before it feeds document authoring.

This repository holds the research, the design boards, the generator that makes them, and the first working code (the input layer).

## What it looks like

Everything on these screens is a synthetic sample. Click a picture for full size; the guide explains the design: [`docs/GUI_DESIGN_GUIDE.md`](docs/GUI_DESIGN_GUIDE.md). The fonts are bundled with the prototype, so the pictures show the real typefaces.

<a href="docs/images/prototype/03_home.png"><img src="docs/images/prototype/03_home.png" width="32%" alt="Home screen: what needs you, where to bring requirements in, recent imports, open clusters and latest activity"></a>
<a href="docs/images/prototype/07_cluster_review_six_wordings.png"><img src="docs/images/prototype/07_cluster_review_six_wordings.png" width="32%" alt="Cluster review: six wordings compared with one reference, changed words highlighted"></a>
<a href="docs/images/prototype/08_wordings_lined_up.png"><img src="docs/images/prototype/08_wordings_lined_up.png" width="32%" alt="The same six wordings lined up word by word in columns"></a>

The ten design boards (Excalidraw files, rendered here because GitHub cannot show them):

| | | | | |
|---|---|---|---|---|
| [![01](docs/images/boards/thumbs/01_storyboard.png)](docs/images/boards/01_storyboard.png)<br>Storyboard | [![02](docs/images/boards/thumbs/02_wireframes.png)](docs/images/boards/02_wireframes.png)<br>Wireframes | [![03](docs/images/boards/thumbs/03_system_flows.png)](docs/images/boards/03_system_flows.png)<br>System flows | [![04](docs/images/boards/thumbs/04_ui_kit_and_IA.png)](docs/images/boards/04_ui_kit_and_IA.png)<br>UI kit | [![05](docs/images/boards/thumbs/05_scale_and_multiuser.png)](docs/images/boards/05_scale_and_multiuser.png)<br>Scale |
| [![06](docs/images/boards/thumbs/06_lens_views.png)](docs/images/boards/06_lens_views.png)<br>Four lenses | [![07](docs/images/boards/thumbs/07_group_and_decisions.png)](docs/images/boards/07_group_and_decisions.png)<br>Group decisions | [![08](docs/images/boards/thumbs/08_assistant.png)](docs/images/boards/08_assistant.png)<br>The assistant | [![09](docs/images/boards/thumbs/09_more_pipelines.png)](docs/images/boards/09_more_pipelines.png)<br>Pipelines | [![10](docs/images/boards/thumbs/10_input_any_source.png)](docs/images/boards/10_input_any_source.png)<br>Any input |

| Folder | What it is |
|---|---|
| `docs/Requirements comparison app research.md` | The research report. Appendix A = how the app reads any input. Appendix B = how the Excalidraw boards were made. |
| `docs/GUI_DESIGN_GUIDE.md`, `docs/images/` | How to design the review screens, how to make the Excalidraw drawings clear and good-looking, and the screenshots and board renders (regenerate with `prototype/shots.py` and `excalidraw_generator/render.py`). |
| `reqin/` | **Working code.** Reads SysML v2 (files and REST), ReqIF (MSOSA / DOORS), DOORS Next (OSLC), Digital.ai Agility, Excel/CSV, SQL, Word and PDF into one canonical model; can watch a folder of exports. `INPUT_LAYER.md` is the design, `CONNECTORS.md` is how to finish and write connectors, `GUI_CONTRACT.md` is what any screen may rely on (one dataset folder, never a file) plus the 14 datasets it must pass. |
| `connector_template/` | A working, tested starting point for your own connector, with five `TODO(agent)` seams and a ready prompt for an agent. Installs as its own package. |
| `excalidraw/` | Ten Excalidraw boards: storyboard, wireframes, flows, UI kit, scale, lenses, group decisions, assistant, pipelines, any-input. **Generated; do not edit by hand.** |
| `excalidraw_generator/` | The Python that produces the boards, with `EXCALIDRAW_GUIDE.md` (recipes, definition of done, prompts for an agent). |
| `prototype/` | Clickable prototype of the screens (one page, built from `parts/`). Open and Import screens show real `reqin` output; everything else is synthetic. See `prototype/README.md`. |
| `tools/` | `check_no_real_data.py`, the tripwire that keeps real program data out of the repo, and the tests that keep the licence files, the board and screenshot pictures, the Markdown links and the GitHub workflow honest. |
| `Containerfile`, `.github/workflows/ci.yml`, `.gitlab-ci.yml`, `Makefile` | Podman/Docker image and CI (GitHub Actions and GitLab). `make check` runs what CI runs. |
| `CONTRIBUTING.md`, `SECURITY.md` | How to change things safely, and how to report a vulnerability privately. |

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e "reqin[test]"
make check          # guard + 226 reqin tests + the connector template + rebuild all ten boards and the prototype page, confirm they are identical
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
| `reqin`: 226 required checks pass (+1 optional with LibreOffice) | Python 3.11, 3.12 and 3.13, in clean virtual environments with no LibreOffice and no git. The connector template's 9 tests pass as shipped. |
| The live connectors' tests bite | 21 deliberate breaks (a leaked secret, a redirect to another host, TLS off, a write verb, paging that stops after page one, caches removed, settle time ignored, a `delete` in the DOORS script ...): 18 caught at once, 3 exposed missing tests, which were added and are now caught. 20 more on the dataset layer: all caught |
| Boards rebuild byte-for-byte; structurally valid | `make boards`, clean environment, standard library only |
| Prototype | Committed page equals a fresh build; static check resolves every template hole across about 1,000 states (0 issues); three browser test files with assertions (44 checks at 1440, 900 and 390 px for Open and Import; 56 at 1440 px and 55 at 390 px for the side bar, Home and the wording comparison; 73 at each of 1440, 900 and 390 px for dispositions, the AI-last step, sending to a teammate, the metrics page and the results page) pass from a clean `npm ci`. The metrics scores are placeholders, and the grade rule on the results page is a proposal. The older flow scripts only print what they see; they were re-run after the redesign but are not assertions. A deliberate break makes both CI jobs fail. |
| Guard trips on what it should | 10 tests, including the real-export file types, data folders, size, missing approval entries, files not yet added to git, and that only the one reviewed DOORS script is exempt |
| Pictures, links and workflow stay true | 26 more tests in `tools/` (36 in all). Every board picture and the prototype screenshots must have been made from the current board or page; every relative link in the Markdown files must resolve; the licence files must agree and every bundled font family must ship with its licence and a notice; the prototype page must make no request to an outside host; the GitHub workflow must keep a read-only token, pinned actions and no `pull_request_target`, and name only files that exist. Each check was shown to fail on a deliberate break. |
| `.gitlab-ci.yml`, `.github/workflows/ci.yml` | Both pass yamllint and their platform's JSON schema; the GitHub file also passes `actionlint`. Each job's commands were run locally. **Neither file has run on its platform yet.** |
| **Not checked** | The `Containerfile` has not been built (no container engine daemon was available where it was written). **Any connector against a real system.** `sysml_api`, `oslc_rm` and `agility` are fake-server-tested only (`reqin connectors` says so); the DOORS 9 script has never run in DOORS; OAuth / form sign-in is not built. Reading real MSOSA, DOORS or SysML v2 exports: all fixtures are synthetic. Opening the boards in the live Excalidraw app. Python 3.10 (not supported; 3.11+ is). |

## Next steps (not done)

1. Add one anonymised real export per source under `reqin/tests/fixtures_approved/` and run the conformance suite on it. This is the first check that matters.
2. Build the comparison engine (stages 2 to 9 in the report), then a gold set to measure it.
3. A backend and the real UI, replacing the interactive prototype.

## License and contributing

Apache License 2.0: see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE). Copyright 2026 gitSITTI. Some bundled files are not covered: `prototype/project/support.js` is a copy of React (MIT) and `prototype/project/fonts/` holds three font families (SIL Open Font License 1.1). Both are listed with their licences in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

This is a research prototype and comes **as is**, without warranty (see sections 7 and 8 of the licence). Read "What has and has not been checked" above before relying on it: no connector has been run against a real MSOSA, Teamwork Cloud, DOORS or Agility system.

Secrets and private names are checked before every commit and again in CI over the whole history (gitleaks at a pinned, checksum-verified version, plus a private-term list that is kept outside the repository): [`docs/SECRET_SCANNING.md`](docs/SECRET_SCANNING.md).

Contributions are accepted under the same licence: see [`CONTRIBUTING.md`](CONTRIBUTING.md). Never commit real requirements, exports or models; the guard described above exists to stop that, and a pull request that trips it will not be merged. Report vulnerabilities privately: [`SECURITY.md`](SECURITY.md).
