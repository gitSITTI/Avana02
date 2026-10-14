# Contributing

Thank you for looking. This is a research prototype, so the most useful contributions are small, checked, and honest about what they did not check.

## Before anything else: no real data

**Never commit real requirements, exports or models.** Not in a test, not as an example, not "temporarily", not in a branch, not in an issue or pull request. Everything in this repository is made up. Use made-up names and numbers for examples, and neutral names for projects and organisations (`PROJ-A`, `Acme`).

Do not put personal details of any person, or details of a real programme or employer, into files, comments, example names or commit messages either.

`tools/check_no_real_data.py` is a tripwire for honest mistakes and runs in CI. The only place an anonymised excerpt may live is `reqin/tests/fixtures_approved/`, with an entry in `APPROVALS.md` saying who approved it. A pull request that trips the guard will not be merged.

## Set up

```bash
python3 -m venv .venv && . .venv/bin/activate      # Python 3.11 or newer
pip install -e "reqin[test]"
make check        # guard + reqin tests + connector template + boards + prototype page
```

`make check` runs what CI runs (see `.github/workflows/ci.yml` and `.gitlab-ci.yml`). The browser tests and the container image are separate: `make proto-test`, `make image-test`.

## What to run for the change you made

| You changed | Run | Why |
|---|---|---|
| `reqin/` code | `cd reqin && python -m pytest -q` | Tests use generated, made-up fixtures and in-memory fake servers. They never touch a network. |
| A connector | the above; raise its `maturity` only if it has run against the real system | `reqin connectors` must not claim more than was checked. |
| An Excalidraw board | in `excalidraw_generator/`: `python3 build_all.py --out ../excalidraw`, then `python3 render_previews.py`, then **look at the pictures** | Boards are generated: never edit a `.excalidraw` file by hand. A test fails if a board and its picture disagree. |
| A prototype screen | in `prototype/`: `python3 build.py`, `node verify.js project/Main.dc.html`, `python3 b11.py 1440`, `python3 b11.py 390`, then `python3 shots.py` and look | `project/Main.dc.html` is built: never edit it by hand. |
| A Markdown file | `python3 -m pytest -q tools` | Every relative link and image must resolve. |
| `.github/workflows/ci.yml` | `python3 -m pytest -q tools`, and `actionlint` plus `check-jsonschema --builtin-schema vendor.github-workflows` if you have them | The tests keep the token read-only and the actions pinned; the two tools catch syntax errors. |

The regeneration commands for boards, previews and screenshots need Node, Playwright and a Chromium. The guides ([`excalidraw_generator/EXCALIDRAW_GUIDE.md`](excalidraw_generator/EXCALIDRAW_GUIDE.md), [`docs/GUI_DESIGN_GUIDE.md`](docs/GUI_DESIGN_GUIDE.md), [`prototype/README.md`](prototype/README.md)) say how to set them up.

## Writing a connector

Start from [`connector_template/`](connector_template/) and read [`reqin/CONNECTORS.md`](reqin/CONNECTORS.md). A connector is read-only, verifies TLS, takes secrets from environment variables, and keeps its `maturity` at `fake-server-tested` until a person has run it against the real system and said so.

## Be honest about checks

The README has a table, "What has and has not been checked". If you add a claim, add the check that backs it, and say how you ran it. If you did not run something (a platform, a real system, a Python version), say that instead. A change that makes the table longer on the "Not checked" side is welcome; a change that quietly makes a claim larger is not.

## Pull requests

- Keep each pull request to one idea, with tests for new behaviour. A new test should be shown to fail when the behaviour it guards is broken.
- Write commit messages in plain sentences that say what changed and why.
- Python 3.11 or newer. Standard library first; a new dependency needs a reason in the pull request.
- Do not add generated or downloaded files that are not needed (`bundle.js`, `node_modules`, build output are git-ignored).

## Licence

The project is under the Apache License 2.0 ([`LICENSE`](LICENSE)). Unless you say otherwise in the pull request, anything you contribute is licensed under the same terms (section 5 of the licence). Bundled third-party code is listed in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md); do not add code whose licence is not compatible, and list what you add.

## Security

Report vulnerabilities privately: see [`SECURITY.md`](SECURITY.md).
