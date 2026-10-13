# Requirements Consolidator

An app concept for opening large SysML v2 / MSOSA requirement projects, finding near-duplicate requirements mechanically first and with AI late, showing metrics for both, and treating everything as a human-verifiable draft reviewed through four lenses (SE, PE, UX, NU) before it feeds document authoring.

This repository holds the research, the design boards, the generator that makes them, and the first working code (the input layer).

| Folder | What it is |
|---|---|
| `docs/Requirements comparison app research.md` | The research report. Appendix A = how the app reads any input. Appendix B = how the Excalidraw boards were made. |
| `reqin/` | **Working code.** Reads SysML v2 (files and REST), ReqIF (MSOSA / DOORS), DOORS Next (OSLC), Digital.ai Agility, Excel/CSV, SQL, Word and PDF into one canonical model; can watch a folder of exports. `INPUT_LAYER.md` is the design, `CONNECTORS.md` is how to finish and write connectors, `GUI_CONTRACT.md` is what any screen may rely on (one dataset folder, never a file) plus the 14 datasets it must pass. |
| `connector_template/` | A working, tested starting point for your own connector, with five `TODO(agent)` seams and a ready prompt for an agent. Installs as its own package. |
| `excalidraw/` | Ten Excalidraw boards: storyboard, wireframes, flows, UI kit, scale, lenses, group decisions, assistant, pipelines, any-input. **Generated; do not edit by hand.** |
| `excalidraw_generator/` | The Python that produces the boards, with `EXCALIDRAW_GUIDE.md` (recipes, definition of done, prompts for an agent). |
| `prototype/` | Clickable prototype of the screens (one page, built from `parts/`). Open and Import screens show real `reqin` output; everything else is synthetic. See `prototype/README.md`. |
| `tools/` | `check_no_real_data.py`, the tripwire that keeps real program data out of the repo. |
| `Containerfile`, `.gitlab-ci.yml`, `Makefile` | Podman/Docker image and CI. `make check` runs what CI runs. |

## Quick start

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -e "reqin[test]"
make check          # guard + 223 reqin tests + the connector template + rebuild all ten boards and the prototype page, confirm they are identical
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
`.gitignore` blocks the usual file types, and CI job `guard:no-real-data` fails the pipeline if one gets in anyway.
The single exception is `reqin/tests/fixtures_approved/`, for anonymised excerpts that your security / export-control reviewer has approved, each recorded in `APPROVALS.md`.
To also scan for your own program code names and number patterns, set a CI/CD variable `FORBIDDEN_TERMS` (one regex per line). Keep that list out of the repo.

## What has and has not been checked

| Checked | How |
|---|---|
| `reqin`: 223 required checks pass (+1 optional with LibreOffice) | Python 3.11, 3.12 and 3.13, in clean virtual environments with no LibreOffice and no git. The connector template's 9 tests pass as shipped. |
| The live connectors' tests bite | 21 deliberate breaks (a leaked secret, a redirect to another host, TLS off, a write verb, paging that stops after page one, caches removed, settle time ignored, a `delete` in the DOORS script ...): 18 caught at once, 3 exposed missing tests, which were added and are now caught. 20 more on the dataset layer: all caught |
| Boards rebuild byte-for-byte; structurally valid | `make boards`, clean environment, standard library only |
| Prototype | Committed page equals a fresh build; static check resolves every template hole across about 1,000 states (0 issues); 39 browser checks pass at 1440 and 390 px from a clean `npm ci`; older flow scripts give identical output to the previous published version. A deliberate break makes both CI jobs fail. |
| Guard trips on what it should | 10 tests, including the real-export file types, data folders, size, missing approval entries, files not yet added to git, and that only the one reviewed DOORS script is exempt |
| `.gitlab-ci.yml` | Passes yamllint and the vendored GitLab CI JSON schema; each job's commands were run locally. **The file itself has not run on a GitLab runner.** |
| **Not checked** | The `Containerfile` has not been built (no container engine daemon was available where it was written). **Any connector against a real system.** `sysml_api`, `oslc_rm` and `agility` are fake-server-tested only (`reqin connectors` says so); the DOORS 9 script has never run in DOORS; OAuth / form sign-in is not built. Reading real MSOSA, DOORS or SysML v2 exports: all fixtures are synthetic. Opening the boards in the live Excalidraw app. Python 3.10 (not supported; 3.11+ is). |

## Next steps (not done)

1. Add one anonymised real export per source under `reqin/tests/fixtures_approved/` and run the conformance suite on it. This is the first check that matters.
2. Build the comparison engine (stages 2 to 9 in the report), then a gold set to measure it.
3. A backend and the real UI, replacing the interactive prototype.
