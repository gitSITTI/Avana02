# Prompt: build or restyle a screen so it shows the user's dataset in the product's look

How to use this: give an agent that can run commands in a checkout of this repository the text below the line. For an agent that cannot, see the last section. It
is the same task for any provider: nothing here depends on one agent's habits, and it names no product.

**Status.** Everything this prompt points to was written and run here, on made-up data, in one browser (Chromium). It has been followed by no agent other than the
one that wrote it. If you are that first outside agent: when a step does not work as written, say which step and what happened, and do not work around it silently.

----------------------------------------------------------------------------------------------------

You are building or restyling **one screen** of a requirements consolidator. The screen must (a) look like the product, (b) show the user's data, and (c) prove both
with checks that someone else can run. Read `AGENTS.md` in the repository root first and keep its rules: **everything here is made up, a new test must be shown to
fail, and say what you did not check.**

## What exists, and what to do with each

| Path | What it is | What to do |
|---|---|---|
| `design/tokens.json` and `design/tokens.css` | The product's design language: colours, type, spacing, radii, sizes, and a few classes (`.rq-card`, `.rq-button`, `.rq-primary`, `.rq-input`, `.rq-statement`, `.rq-id`, `.rq-caption`). `tokens.css` is generated from the JSON by `design/make_tokens.py` | **Build from these names only** (`var(--accent)`). Never a hex value, a pixel size or a font name you read off a picture. Do not edit `tokens.css` by hand |
| `docs/SCREEN_DATA_MAP.md` | For each part of each screen, the dataset field that fills it, or that nothing fills it yet | Read the rows for your screen before you write anything. Every number, name and status you show comes from a row |
| `reqin/GUI_CONTRACT.md` | What a screen may rely on: **one canonical dataset** (five files in a folder), never a file, a database or a server | Your screen opens a dataset and nothing else |
| `design/reference_viewer/` | A small plain screen that passes every check below | Read `design/reference_viewer/viewer.js` and its README before you write yours. Copy its behaviour (loading, refusing, windowing, "not provided", textContent only), not its look |
| `design/ui_from_image/SKILL.md` | How to go from a picture to components in the target's own look, with scripts and gates | Use it when you are given a picture |
| `tools/gui_checks/` and `docs/GUI_TEST_HOOKS.md` | The scan of the source (`tools/gui_checks/hardcode_scan.py`), the probe (`tools/gui_checks/probe.py`: a real browser against the fourteen test datasets), a local server (`tools/gui_checks/serve.py`), the status checker (`tools/gui_checks/check_status.py`), and the marks (`data-testid`) a screen carries so one probe can check any screen | Your screen carries the marks and passes both checks |
| `prototype/` | A clickable picture of the product with a synthetic sample. The page `prototype/project/Main.dc.html` is generated, about 780 KB, and every number and name in it is typed in | **Never copy markup, styles or data from it.** It uses variables a runtime injects and literal colours, which is exactly what makes a copy come out with the wrong look, and its numbers are the sample's. Read `prototype/parts/` to see what a screen contains and in what order, and `docs/GUI_DESIGN_GUIDE.md` for why |

## Why earlier attempts went wrong (so you do not repeat them)

1. **The look came out wrong** because a design was copied from a page whose colours are literal and whose variables were injected when it ran, or because a font
   that was never loaded fell back to another one. The fix is tokens, and the check is `tokens.*` in the probe.
2. **The screen showed the sample, not the data** because the numbers, names and statuses were typed into the markup. The fix is one function per screen that turns
   the dataset into what the screen shows. The checks are `counts.*`, `list.*` and `canary.*`: the canary is a dataset written fresh for the run, so nothing can have
   been typed in for it.
3. **Nobody said where each value comes from.** `docs/SCREEN_DATA_MAP.md` does.
4. **Some ideas have no producer yet** (the screen needs comparison output or saved work that no code supplies to the screen). Build the empty state and say so on
   the screen and in your report; never invent a plausible value.
5. **Several agents worked at once with no shared definition** of what each piece takes and gives. See "When more than one agent works".
6. **An agent stopped to report something it could have fixed,** and nothing moved until a person read the report. The rule is in `AGENTS.md` (rule 9): fix what is yours, write down
   what is not (what is blocked, what you tried, what is needed), carry on with every part that does not depend on it, and stop only for what only the owner can do.
7. **To satisfy a check or fill a gap, the agent invented sample data and then grew the screen to show it.** The rule is in `AGENTS.md` (rule 10): an empty state and a line in the
   report, never a new dataset, a new field or a new panel. The screen takes the datasets it is given.
8. **The look drifted while the data was being bound.** The probe says the screen shows the data; it does not say the screen still looks like what the owner approved. Step 9 does.

## Build in three layers, so a change of look never touches the data code

1. **Tokens.** Already done: `design/tokens.css`.
2. **Components.** A component takes plain properties (text, a number, a status word) and draws them with token variables. It knows nothing about datasets.
3. **Screens.** One function per screen, the view model: `dataset in, properties out`, pure, testable without a browser. The screen is that function plus components.
   This is the only place that names a dataset field; `docs/SCREEN_DATA_MAP.md` says which.

## Steps. Each has a gate: do not go on until it holds.

0. **Choose the one screen or part.** Write down which rows of `docs/SCREEN_DATA_MAP.md` it uses, and which of them have no producer. *Gate:* you can name them.
1. **Get the datasets.** `reqin make-datasets DIR --size 5000`. Open F1 (minimal), F2 (everything), F6 (extracted from prose), F12 (empty) and look at their files.
   `python3 tools/gui_checks/datapaths.py --json paths.json` lists every real field path. *Gate:* you have seen what a record, a link and a rejected record look like.
2. **Read the look.** The tokens, and if the screen must match an existing page, `design/ui_from_image/SKILL.md` step 1. *Gate:* you can say what the primary button,
   an input and a card look like in a sentence each.
3. **If you were given a picture,** follow steps 2 to 5 of `design/ui_from_image/SKILL.md`: cut it into component frames, map its colours onto the tokens, write the
   component spec and check it with `design/ui_from_image/scripts/check_component_specs.py`. *Gate:* no errors, and you have looked at every crop.
4. **Write the view model and test it on the datasets.** `describe()` in `reqin/src/reqin/dataset.py` states, for each dataset, what a screen must be showing; test
   against it. *Gate:* the view model is right on F1 to F14 before any markup exists.
5. **Build the components and the screen from tokens,** one component at a time, and put the screen's marks on it (`docs/GUI_TEST_HOOKS.md`).
6. **Run the two checks.**
   `python3 tools/gui_checks/hardcode_scan.py YOUR_APP` and `python3 tools/gui_checks/probe.py --app YOUR_APP --datasets DIR`.
   *Gate:* 0 errors and 0 failed. Do not edit the probe, the hooks document or the datasets to make a check pass. If you believe a check is wrong, say which and why
   in your report and leave it as it is.
7. **Break your own screen on purpose,** one way at a time (a count typed in, a field dropped, a hook removed), and see that a check fails for each. A check you have
   not seen fail is not evidence. Put the screen back.
8. **Look at it.** Take a screenshot at 1440 and at 390 px wide and open both. The probe cannot tell you whether it is clear. Say that you looked, not that it is good.
9. **Lock the look, but only when the owner has approved it.** `python3 tools/gui_checks/golden.py shot --app YOUR_APP --datasets DIR --dataset F02_everything --width 1440 --out shots/home-1440.png`
   (and at 390), show the pictures to the owner, and if they say yes: `python3 tools/gui_checks/golden.py approve home-1440 shots/home-1440.png`. If the screen was approved before you
   started, take the same pictures and run `python3 tools/gui_checks/golden.py compare-all --shots shots/`. *Gate:* it passes, or the owner has approved the new look. You never approve
   your own work, and you do not edit `tools/gui_checks/golden.py` or the approved pictures to make it pass. The limits (per machine, one browser, drift not quality) are in `docs/GUI_TEST_HOOKS.md`.

## When more than one agent works

**Start with one agent.** Most screens do not need more. Split only when the pieces are independent (one component each, or one screen each) and only after steps 0 to 4 are
done by a single agent, because everything below depends on a shared definition.

- **A contract file first.** One agent writes `work/CONTRACT.md` before anyone builds: for each screen, the view model's input and output; for each component, its
  properties; which `data-testid` marks each piece carries; and **which agent owns which files**. The others read it and do not change it.
- **One writer per file.** An agent changes only files it owns. If it needs a change elsewhere, it says so in its status file; it does not make it.
- **A finished piece is files plus a status file,** `status.json`, written as the contract `reqin-agent-status/1` and checked with
  `python3 tools/gui_checks/check_status.py status.json`: who, which task, `done`, `partial` or `blocked`, the files, every command run with its exit code, what was
  not checked, and what it is blocked on. A message that says "done" with no status file is not done.
- **Own checkout, own branch.** Each agent works in its own git worktree on its own branch (`git worktree add ../NAME -b agent/NAME`). Two agents never share a working folder or a
  branch; git refuses to check one branch out twice, so a clash fails at once instead of corrupting work. Nobody pushes `main`; the lead agent merges one branch at a time.
- **Budgets and blockers.** Give each agent a limit (a number of steps or a time). A gate that does not hold after two tries means: change the approach, and if the cause is not in the
  agent's own files, put a blocker in its status file (`blocked` or `partial`: what is blocked, what it tried, what is needed) and take the next piece. An agent does not loop on one
  step, does not stop while it has independent work, and does not go quiet. A tool or service that does not answer is reported once, not retried in a loop. An agent that has produced no
  file and no status within its limit is stopped and its work taken back. Questions for the owner go in one list, not one at a time.
- **Merging is a gate, not a vote.** Bring in one piece at a time. A piece goes in only when the scan and the probe pass on it, and the probe is run again
  after each merge. When two pieces disagree, the contract file decides; if it does not, the person decides.

## What to give each kind of agent

| It can | Give it |
|---|---|
| Run a shell in a checkout | the repository and this prompt |
| Run code but has no checkout (a sandbox) | `design/` (tokens, fonts, the reference viewer, the `ui_from_image` scripts), `tools/gui_checks/`, `reqin/` (for `make-datasets`), `docs/GUI_TEST_HOOKS.md`, `docs/SCREEN_DATA_MAP.md`, the datasets folder, and this prompt. It needs Playwright with Chromium for the probe; without it, it can still run the scan |
| Only write text | this prompt, `design/tokens.css`, `docs/GUI_TEST_HOOKS.md`, `docs/SCREEN_DATA_MAP.md` and `design/reference_viewer/viewer.js`, pasted. It writes the files; a person runs the two checks and pastes the output back; **the agent must say that it ran nothing.** Do not paste `prototype/project/Main.dc.html`: it is too large and it is the wrong thing to copy |

An agent with a small window: work on one screen and one component at a time, read the rows of the data map for that screen only, and read `design/reference_viewer/viewer.js` in pieces.

## Rules

- No real data, no real names, no details of any person. The datasets are generated. Use neutral names.
- Do not push, publish, or change a remote, a secret or a CI setting.
- Every value from a dataset reaches the page as text, never as markup. No `innerHTML`.
- No call to a model, no request to another host, no analytics. The page works with no network.
- Do not edit generated files by hand (`design/tokens.css`, `prototype/project/Main.dc.html`, the boards).
- Say what you looked at and what you did not.

## Done means

1. The scan reports 0 errors and the probe reports 0 failed, and you pasted both outputs into your report.
2. The view model has tests that pass on F1 to F14, and you have seen at least three of them fail when you broke the code they guard.
3. You looked at screenshots at 1440 and 390 px.
4. Every part of the screen that has no producer says so on the screen, and the list is in your report.
5. `git status` shows only the files you meant to change.
6. If the owner had approved the look of this screen, `golden.py compare-all` passes or the owner has approved the new look. If nobody has approved it yet, your report says so.

## Report

What you built; the two check outputs; which rows of `docs/SCREEN_DATA_MAP.md` you used and which had no producer; the ways you broke it and what each broke; and
**Not checked**: at the least, that it has not been used with real requirements, that it has not been tried in a browser other than Chromium, and that nobody has
judged how it looks or whether it is accessible beyond what the probe measures.
