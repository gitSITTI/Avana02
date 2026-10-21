# Instructions for AI agents working in this repository

This file is for any coding or chat agent (OpenAI Codex or ChatGPT, Gemini, Claude, Copilot, Cursor, Aider, a local model ...). It is the one place the rules are written; the short files named `CLAUDE.md`, `GEMINI.md` and `.github/copilot-instructions.md` only point here. People should read [`README.md`](README.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) first.

## What this repository is

A research prototype for a **requirements consolidator**: it reads requirements from SysML v2 / MSOSA, ReqIF, DOORS, Excel and other sources, finds near-duplicates mechanically first and with AI late, shows metrics, and treats every result as a **draft that a person verifies** through four review lenses. It holds the research, the Excalidraw design boards and the code that makes them, a clickable prototype of the screens, a design kit and checks for building real screens, and the working code (the input layer, the first mechanical stages of the comparison engine, a reference server, and the AI gate and gateway). The comparison engine stops at those first stages, **the prototype does not consume its comparison output yet**. The prototype can share decisions through the reference server when served from it and signed in with a token. Nothing here has been run on a real requirements set.

## Rules that apply to every task

1. **No real data, no personal details.** Everything here is made up. Never add real requirements, exports, models, customer or programme names, or details of any real person or employer: not in files, comments, example names, test data, commit messages or pull requests. Use neutral names (`PROJ-A`, `Acme`). If a task seems to need real data, stop and say so.
2. **Do not push, publish or change a remote, a secret or a CI setting unless the owner says so in this conversation.** Committing locally is fine when asked. Never force-push. Never put a link to a private chat or session into a public repository's history.
3. **Say what you did not check.** Every claim in the docs has a check behind it, and the README's table "What has and has not been checked" lists what has none. Do not make a claim bigger than its check. If you could not run something (a browser, a platform, a real system, another language), write that, not "should work".
4. **A new test must be shown to fail.** Break the behaviour it guards, see the test fail, put the behaviour back. `tools/mutation/` does this at scale; add a change there for any new rule.
5. **Generated files are not edited by hand.** The boards in `excalidraw/`, the page `prototype/project/Main.dc.html`, the demo seed `prototype/demo/seed.json`, the pictures in `docs/images/` and `excalidraw_generator/board_spec.schema.json` are made by programs. Change the source and regenerate.
6. **No secrets in files.** Credentials come from environment variables. Gitleaks and a private-term check run before every commit and in CI ([`docs/SECRET_SCANNING.md`](docs/SECRET_SCANNING.md)); do not work around them.
7. **AI comes late and answers are drafts.** Anything that would send requirement text to a model must go through the gate (`reqin/src/reqin/aigate.py`, `prototype/parts/aigate.js`) or the gateway (`reqin/src/reqin/gateway/`). Never add a call that bypasses them, and never make a draft look decided.
8. **Keep it self-hosted and small.** Standard library first; a new dependency needs a reason. The prototype page makes no request to any outside host (a test checks). No telemetry. Python 3.11 or newer.

## Where things are

Start with [`docs/CAPABILITIES.md`](docs/CAPABILITIES.md) for current implementation boundaries and `python3 tools/doctor.py` for local setup. The capability table is generated from `docs/capabilities.json`; edit that source and run `python3 tools/capabilities.py`. It describes implementation and check locations, not deployment certification.

| Path | What it is | Change it by |
|---|---|---|
| `reqin/` | The working Python code: input layer, connectors, reference server (`SERVER.md`), AI gate and gateway | edit `reqin/src`, test in `reqin/tests` |
| `prototype/` | The clickable prototype: one page built from `prototype/parts/`. A picture of the product with a synthetic sample, **not a starting point for code**: never copy markup, styles or data from `project/Main.dc.html` | edit `parts/`, run `python3 build.py`; never edit `project/Main.dc.html` |
| `design/` | The design language as data (`design/tokens.json`, and the generated `design/tokens.css`), `design/ui_from_image/` (how to turn a picture into components in a site's own look), and `design/reference_viewer/` (a small screen that shows a dataset and passes every check) | edit `design/tokens.json`, run `python3 design/make_tokens.py`; see `design/README.md` |
| `tools/gui_checks/` | What shows a screen is bound to its data: `tools/gui_checks/hardcode_scan.py`, `tools/gui_checks/probe.py` (a real browser against the fourteen test datasets), `tools/gui_checks/serve.py`, `tools/gui_checks/check_status.py`, `tools/gui_checks/datapaths.py` | see `docs/GUI_TEST_HOOKS.md` |
| `excalidraw/` | The twelve design boards (generated) | edit `excalidraw_generator/`, rebuild |
| `excalidraw_generator/` | The Python that makes the boards; **and `board_spec.py`, which makes a board from plain JSON** | see `EXCALIDRAW_GUIDE.md` |
| `docs/` | Design, data handling, the gateway, the porting guide, task prompts for agents (`docs/agent_prompts/`) | edit the Markdown; every relative link must resolve |
| `deploy/ai-egress/` | Example network rules for keeping the model host off the internet, and the script that checks them | see its README |
| `connector_template/` | A working starting point for a new connector | see `reqin/CONNECTORS.md` |
| `tools/` | The repository's own checks, and `tools/mutation/` | `python3 -m pytest -q tools` |
| `tools/review/` | Builds a portable review screen from checked datasets and engine output; review notes and exports remain drafts | edit the builder/panel/view model; run `reqin/tests/test_review_workspace.py`, the GUI scan and probe, and `tools/mutation/review.py` |

## What to run

Set up once: `python3 -m venv .venv && . .venv/bin/activate && pip install -e "reqin[test]"`. Run from the repository root. `make check` runs everything that needs only Python and Node; `make check-full` adds the browser tests.

| You changed | Run |
|---|---|
| `reqin/` | `cd reqin && python3 -m pytest -q` |
| A board, or `excalidraw_generator/` | `cd excalidraw_generator && python3 build_all.py --out ../excalidraw && python3 validate.py ../excalidraw/*.excalidraw`, then render and **look at the picture** (`python3 render_previews.py`) |
| A board written as JSON | `python3 excalidraw_generator/board_spec.py build spec.json out.excalidraw --strict --png out.png --scale 2`, then look at `out.png` |
| A real screen (a new one, or a restyle) | `python3 tools/gui_checks/hardcode_scan.py APP` and `python3 tools/gui_checks/probe.py --app APP --datasets DIR` (`DIR` from `reqin make-datasets DIR --size 5000`); both must pass. The steps are in [`docs/agent_prompts/build_the_gui.md`](docs/agent_prompts/build_the_gui.md) |
| The prototype | `cd prototype && python3 build.py && node verify.js project/Main.dc.html` (must end `ISSUES 0`), then the browser tests for the page you touched (`python3 run_browser_tests.py`), then `python3 shots.py` and look |
| Markdown or any file in `tools/` | `python3 -m pytest -q tools` |
| A rule in a mutation script's target | `python3 tools/mutation/<name>.py --patterns` (does every change still match?) and, for the part you changed, `python3 tools/mutation/<name>.py <part of a name>` |

If a command cannot run where you are (no Node, no browser, no network), say which one and what that leaves unchecked.

## If you cannot run code

You can still make useful changes. For a board, write it as JSON in the format `reqin-board/1` (`excalidraw_generator/board_spec.schema.json`; `python3 excalidraw_generator/board_spec.py describe` prints the vocabulary) and ask the person to run the compiler, or run it yourself if a shell is offered. [`docs/agent_prompts/excalidraw_board_without_code.md`](docs/agent_prompts/excalidraw_board_without_code.md) is a prompt that works with no tools at all. For everything else, say plainly that your change is untested and list exactly which commands the person should run.

## Several agents on one task

Start with one. Split only when the pieces are independent and a single agent has first written the shared definition (what each screen takes and gives, who owns which
file). One writer per file; each agent hands back its files and a status file that `python3 tools/gui_checks/check_status.py` accepts ("done" needs commands run and a list
of what was not checked); an agent whose gate fails twice stops and reports instead of looping; work is merged one piece at a time and only when the checks pass on it.
The full protocol is in [`docs/agent_prompts/build_the_gui.md`](docs/agent_prompts/build_the_gui.md).

## Porting to another language or provider

[`docs/PORTING.md`](docs/PORTING.md) says, for each part, what is the specification, which test vectors are language-neutral, and what only exists as Python. Task prompts that stand alone are in [`docs/agent_prompts/`](docs/agent_prompts/).

## Done means

- The commands in "What to run" pass for what you changed, and you have looked at any picture you made.
- The docs that mention what you changed say the same thing, and no claim is larger than its check.
- `git status` shows only files you meant to change, none of them real data or generated by hand.
- Your reply to the person says what changed, what you ran, and what you did not.
