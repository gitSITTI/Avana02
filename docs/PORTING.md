# Porting and re-implementing: for other agents, other providers, other languages

This repository was built with one provider's coding agent. Nothing in it needs that agent. This page says, for each part, **what a different agent or a different language has to go on**: a written specification, test vectors that do not depend on Python, or only the reference code. It says where there is nothing but the code, so nobody finds out halfway through.

> **What has and has not been tried.** The specifications and vectors were written and checked here. A second implementation of the gateway's decision core and a board written from the no-code prompt were each produced by an agent given only the written material, to see whether the material is enough: the results are in the last section. **No agent from OpenAI, Google or any other provider has been run on this repository**, so "it works with X" is not claimed for any named product. What is claimed is narrower: the material is written so that it does not rely on tools or habits of one agent, and the places where it still might are listed.

## 1. What each part gives a newcomer

| Part | Written specification | Language-neutral test vectors | Reference code | How to know a port is right |
|---|---|---|---|---|
| **Excalidraw boards** (the design drawings) | [`EXCALIDRAW_GUIDE.md`](../excalidraw_generator/EXCALIDRAW_GUIDE.md); the JSON format `reqin-board/1` ([`board_spec.schema.json`](../excalidraw_generator/board_spec.schema.json), `board_spec.py describe`) | [`examples/board_spec_example.json`](../excalidraw_generator/examples/board_spec_example.json); a JSON Schema any validator can run | Python: `exc.py`, `wf.py`, `board_spec.py` | the compiler's own checks and warnings, then looking at the picture. [`agent_prompts/excalidraw_board_without_code.md`](agent_prompts/excalidraw_board_without_code.md) needs no tools at all |
| **The screens** (clickable prototype) | [`GUI_DESIGN_GUIDE.md`](GUI_DESIGN_GUIDE.md), [`prototype/README.md`](../prototype/README.md), [`V_MODEL.md`](V_MODEL.md) for how each number is counted | the AI gate's table ([`ai_gate_cases.json`](ai_gate_cases.json)); the rest is checked by browser tests written in Python and Node | JavaScript in `prototype/parts/` | the checks in `prototype/` (`verify.js`, the browser tests). A port to another UI toolkit has **no** vectors for layout; the design boards are the reference for what a screen is for |
| **Input layer and connectors** | [`reqin/INPUT_LAYER.md`](../reqin/INPUT_LAYER.md), [`reqin/CONNECTORS.md`](../reqin/CONNECTORS.md) | the **canonical dataset** ([`reqin/GUI_CONTRACT.md`](../reqin/GUI_CONTRACT.md): five JSONL/JSON files with sizes and SHA-256 in a manifest) and fourteen deliberately different test datasets | Python `reqin/` | a connector or an importer in any language is right when the dataset it writes passes `reqin check-dataset DIR` and the GUI contract's rules |
| **The AI gate** (may this group of requirements go to this model) | [`AI_DATA_HANDLING.md`](AI_DATA_HANDLING.md) | [`ai_gate_cases.json`](ai_gate_cases.json): 58 markings, 14 groups, 16 sheets, 19 whole decisions | Python `aigate.py` **and** JavaScript `prototype/parts/aigate.js`: two languages already pass the one table | every case in the table |
| **The gateway's decision core** | [`GATEWAY_SPEC.md`](GATEWAY_SPEC.md) | [`gateway_cases.json`](gateway_cases.json): about 250 cases | Python `reqin/src/reqin/gateway/` | every case in the file; then the HTTP refusals, by hand |
| **The gateway's HTTP side** | [`AI_GATEWAY.md`](AI_GATEWAY.md) | **none** | Python | tests you write from that page, against a fake model that records whether it was called |
| **The reference server** (shared review: roles, no silent overwrite, a record that verifies) | [`reqin/SERVER.md`](../reqin/SERVER.md) | **none** (82 Python tests over real HTTP) | Python `reqin/src/reqin/server/` | tests you write from that page. This is the largest part with no neutral suite |
| **The network wall check** | [`deploy/ai-egress/README.md`](../deploy/ai-egress/README.md): the plan format `reqin-wall/1` | the example plans in `deploy/ai-egress/` | Python `wall_check.py` | run it against your own network; no fake can show that |
| **The comparison engine** | the research report (stages 2 to 9) | **none: it is not built** | none | nothing to port yet |
| **The checks that the checks bite** | [`tools/mutation/README.md`](../tools/mutation/README.md) | the method, not a file format | Python scripts | see section 4, step 6 |

## 2. Three kinds of agent

What an agent can do depends on what it is given, not on its brand.

| It can | What to give it | What it can do here | What it must say it did not do |
|---|---|---|---|
| **Run a shell** with Python 3.11+ and ideally Node.js (a command-line coding agent, an IDE agent, a CI job) | the repository, and [`AGENTS.md`](../AGENTS.md) | everything: run the tests, make boards, change code, port a part and run the vectors | what needs a browser it has not got (the browser tests) or a platform it cannot reach (CI, a container engine) |
| **Run code in a sandbox** but with no shell, no repository checkout, or no network (a chat product's code tool) | the files it needs, uploaded: for a board, `excalidraw_generator/` and a spec; for a port, the spec and the vectors | write and run a port of a pure part against the vectors; compile a board spec if it can run Python | anything that needs the whole repository, a browser, or a network; and it cannot install packages if it has no network |
| **Only write text** (a chat window) | one prompt from [`agent_prompts/`](agent_prompts/) pasted in, plus the schema or spec the prompt names | a board as JSON, a port of a pure part as source text | **that it ran anything.** A person (or another tool) has to run the compiler or the vectors, and the agent must say its work is unrun |

[`AGENTS.md`](../AGENTS.md) is the file most coding agents look for first; `CLAUDE.md`, `GEMINI.md` and `.github/copilot-instructions.md` point to it. Which tool reads which file was not tested here: if yours does not, paste `AGENTS.md` into its instructions.

## 3. Prompts that stand on their own

Each file in [`agent_prompts/`](agent_prompts/) is a complete task for an agent that has seen nothing else: what to make, which files to read (by path), what is forbidden, what "done" means, and what to report. They name no tool by product.

| Task | Prompt | Needs |
|---|---|---|
| A board for Excalidraw, **no code** | [`excalidraw_board_without_code.md`](agent_prompts/excalidraw_board_without_code.md) | text only; a person runs the compiler |
| A board for Excalidraw, **with code** | [`excalidraw_board_with_code.md`](agent_prompts/excalidraw_board_with_code.md) | Python, a shell |
| A connector for a new source | [`new_connector.md`](agent_prompts/new_connector.md) | Python, a shell |
| The gateway's decision core in another language | [`port_gateway_core.md`](agent_prompts/port_gateway_core.md) | that language's toolchain, or a person to run the vectors |
| The comparison engine (first mechanical stages) | [`comparison_engine.md`](agent_prompts/comparison_engine.md) | Python, a shell |

## 4. How to port a part, step by step

This is the order that found the problems in the Python and JavaScript versions of the gate, and in the gateway's own first version.

1. **Read the specification and the vectors before writing anything.** The vectors show what the words leave open.
2. **Port the pure core first**: text in, answer out. No sockets, no files. Write it so each function can be called on its own.
3. **Run every vector.** All of them. A port that passes most has a rule wrong, and the vectors that fail say which.
4. **Add the outside**: the HTTP side, the files, the clock, in the same shape as the reference. Keep the core free of them.
5. **Try each refusal** against the finished thing with a fake of the model that records whether it was called. A refusal that still calls the model is the failure that matters most.
6. **Break your port on purpose.** Change one rule at a time (a comparison flipped, a check removed, a number off by one) and see that a vector or a test fails. A rule no test can fail is not checked. [`tools/mutation/README.md`](../tools/mutation/README.md) says how it is done here; it works in any language.
7. **Write what you did not check.** In the port's own README, as a short table, the way [`README.md`](../README.md) does.

## 5. Things that differ between languages and bite

These are the differences that were found or are known; each has a vector where it can have one.

| Thing | Pitfall | Where it is pinned down |
|---|---|---|
| What a letter or a digit is | `\w` and `[a-z]` mean different things in every language; the rule here is the Unicode categories `L` and `N` | `GATEWAY_SPEC.md` section 2 |
| Lower-casing | full (`İ` becomes two code points) versus simple (one) | the vectors for `İstanbul`, `ẞ` |
| Normalisation | NFKC first, then lower-case | the full-width and ligature vectors |
| Marking words | a letter of any alphabet stuck to `CUI` makes it a different word | `ai_gate_cases.json` |
| The order of JSON keys | some readers reorder integer-like keys; the hash of the audit record needs sorted keys | `GATEWAY_SPEC.md` sections 6 and 12 |
| JSON text | escape only what must be escaped, and write other characters as they are | the audit vectors |
| Numbers | whole numbers only, except `days` (90 equals 90.0) | the route vectors |
| Time | the record uses UTC written as `2026-03-04T05:06:07Z` | `GATEWAY_SPEC.md` section 12 |
| Strings in the Excalidraw files | text is wrapped by the generator, not by Excalidraw; a long word will not break | `EXCALIDRAW_GUIDE.md` |
| Unicode version | a new script may be in one platform's tables and not another's | `GATEWAY_SPEC.md` section 2 |

## 6. What the neutral material cannot do

- It cannot make a port behave well under load, over a bad network, or with a real model, a real firewall or a real requirements system. None of that was ever run here, by any agent.
- It does not replace a person who owns the decision. The gate and the gateway enforce what a reviewer wrote on the data sheet; they do not decide what is allowed.
- It was written and checked by one provider's agent. A different agent may read a sentence differently. Where that happens, the vectors are the arbiter, and the sentence should be fixed.

## 7. What was tried

*(Filled in below after the material was given to agents that had seen nothing else.)*
