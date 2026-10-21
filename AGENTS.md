# Instructions for AI agents working in this repository

This file is for any coding or chat agent (OpenAI Codex or ChatGPT, Gemini, Claude, Copilot, Cursor, Aider, a local model ...). It is the one place the rules are written; the short files named `CLAUDE.md`, `GEMINI.md` and `.github/copilot-instructions.md` only point here. People should read [`README.md`](README.md) and [`CONTRIBUTING.md`](CONTRIBUTING.md) first.

## What this repository is

A research prototype for a **requirements consolidator**: it reads requirements from SysML v2 / MSOSA, ReqIF, DOORS, Excel and other sources, finds near-duplicates mechanically first and with AI late, shows metrics, and treats every result as a **draft that a person verifies** through four review lenses. It holds the research, the Excalidraw design boards and the code that makes them, a clickable prototype of the screens, and the first working code (the input layer, a reference server, and the AI gate and gateway). The comparison engine itself is **not built yet**.

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

| Path | What it is | Change it by |
|---|---|---|
| `reqin/` | The working Python code: input layer, connectors, reference server (`SERVER.md`), AI gate and gateway | edit `reqin/src`, test in `reqin/tests` |
| `prototype/` | The clickable prototype: one page built from `prototype/parts/` | edit `parts/`, run `python3 build.py`; never edit `project/Main.dc.html` |
| `excalidraw/` | The twelve design boards (generated) | edit `excalidraw_generator/`, rebuild |
| `excalidraw_generator/` | The Python that makes the boards; **and `board_spec.py`, which makes a board from plain JSON** | see `EXCALIDRAW_GUIDE.md` |
| `docs/` | Design, data handling, the gateway, the porting guide, task prompts for agents (`docs/agent_prompts/`) | edit the Markdown; every relative link must resolve |
| `deploy/ai-egress/` | Example network rules for keeping the model host off the internet, and the script that checks them | see its README |
| `connector_template/` | A working starting point for a new connector | see `reqin/CONNECTORS.md` |
| `tools/` | The repository's own checks, and `tools/mutation/` | `python3 -m pytest -q tools` |

## What to run

Set up once: `python3 -m venv .venv && . .venv/bin/activate && pip install -e "reqin[test]"`. Run from the repository root. `make check` runs everything that needs only Python and Node; `make check-full` adds the browser tests.

| You changed | Run |
|---|---|
| `reqin/` | `cd reqin && python3 -m pytest -q` |
| A board, or `excalidraw_generator/` | `cd excalidraw_generator && python3 build_all.py --out ../excalidraw && python3 validate.py ../excalidraw/*.excalidraw`, then render and **look at the picture** (`python3 render_previews.py`) |
| A board written as JSON | `python3 excalidraw_generator/board_spec.py build spec.json out.excalidraw --strict --png out.png --scale 2`, then look at `out.png` |
| The prototype | `cd prototype && python3 build.py && node verify.js project/Main.dc.html` (must end `ISSUES 0`), then the browser tests for the page you touched (`python3 run_browser_tests.py`), then `python3 shots.py` and look |
| Markdown or any file in `tools/` | `python3 -m pytest -q tools` |
| A rule in a mutation script's target | `python3 tools/mutation/<name>.py --patterns` (does every change still match?) and, for the part you changed, `python3 tools/mutation/<name>.py <part of a name>` |

If a command cannot run where you are (no Node, no browser, no network), say which one and what that leaves unchecked.

## If you cannot run code

You can still make useful changes. For a board, write it as JSON in the format `reqin-board/1` (`excalidraw_generator/board_spec.schema.json`; `python3 excalidraw_generator/board_spec.py describe` prints the vocabulary) and ask the person to run the compiler, or run it yourself if a shell is offered. [`docs/agent_prompts/excalidraw_board_without_code.md`](docs/agent_prompts/excalidraw_board_without_code.md) is a prompt that works with no tools at all. For everything else, say plainly that your change is untested and list exactly which commands the person should run.

## Porting to another language or provider

[`docs/PORTING.md`](docs/PORTING.md) says, for each part, what is the specification, which test vectors are language-neutral, and what only exists as Python. Task prompts that stand alone are in [`docs/agent_prompts/`](docs/agent_prompts/).

## Done means

- The commands in "What to run" pass for what you changed, and you have looked at any picture you made.
- The docs that mention what you changed say the same thing, and no claim is larger than its check.
- `git status` shows only files you meant to change, none of them real data or generated by hand.
- Your reply to the person says what changed, what you ran, and what you did not.
