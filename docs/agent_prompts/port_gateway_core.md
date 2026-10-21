# Prompt: port the AI gateway's decision core to another language

How to use this: give an agent the text below the line, with the language filled in where it says `<LANGUAGE>`. It works with a shell (it can run its own code) or without one (it writes the source, and a person runs the vectors). The agent needs **no other file than the ones named**.

----------------------------------------------------------------------------------------------------

Write the decision core of an "AI gateway" in **<LANGUAGE>**, using only that language's standard library (plus a JSON reader, which every language has). A reference implementation exists in Python; you will not read it. You work from a written specification and test vectors, and your job is done when your code gives every answer in the vectors.

## Read

1. `docs/GATEWAY_SPEC.md`: the specification. Read all of it, including section 13 (what ports get wrong) and section 14.
2. `docs/gateway_cases.json`: the test vectors (format `reqin-gateway-cases/1`). Its sections are listed in section 14 of the specification.
3. `docs/AI_DATA_HANDLING.md` and `docs/ai_gate_cases.json`: the AI **gate**, which the gateway's decision calls (section 9 of the specification). The gate has its own table of cases. **Port the gate first and pass that table, then the rest.** Read the table's `about` entry for its format.

## Write

In a new folder `ports/<language>/gateway_core/` (use the language's usual name for the folder):

- the gate and the decision core as **pure functions**, with no sockets and no files: `words`, `fingerprints`, the markings file reader and builder, `undeclared`, `prompt_text`, the requirement header parser, `sheet_from_doc`, the gate, `route_mismatch`, `decide`, the audit record's hash and its verifier;
- a **runner**, one command, that reads `docs/ai_gate_cases.json` and `docs/gateway_cases.json`, runs every case, prints the name of each case that fails with what it expected and what it got, prints `N of N cases pass`, and exits with a non-zero status unless all pass;
- a `README.md` in that folder with the command to run, what the code is, and a short table **Checked / Not checked** (see below).

## Rules

- Do not change `GATEWAY_SPEC.md` or either vectors file. If a case looks wrong, or the specification is unclear, say which and why in your report; do not edit it to fit your code, and do not special-case a vector.
- Do not copy code from anywhere else in the repository. The point is to find out whether the specification is enough.
- Standard library only. No network. No file outside `ports/<language>/` is written.
- All text in the folder is made up; do not paste real requirements anywhere.

## Done means

1. The runner reports every case passing, for both files. If you could not run it, say so plainly and write nothing that implies you did.
2. **You broke it on purpose.** Change one rule at a time in a copy (flip a comparison, remove the NFKC step, use a window of 5, drop the sort of the ids), run the runner, and see that it fails. Record in the README how many changes you tried and that each was noticed. A rule that no vector fails on is a rule the vectors do not check: list those.
3. The README says what you did **not** check, at least: the HTTP side was not written, no model or network was involved, and the Unicode version of your platform.

## Report

Whether every case passes; the number of changes you tried and any that were not noticed; each place the specification was unclear or seemed wrong; and **Not checked**.
