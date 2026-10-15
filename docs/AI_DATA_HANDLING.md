# AI data handling

Requirements can carry export-controlled, controlled-unclassified (CUI) or proprietary text. Before any requirement text is put in a prompt, this project asks one
question: **is this group of requirements allowed to go to this model, under what the people who approved the model were told about it?** This page says what the
check is, what it is not, and what your IT and security staff still have to do themselves.

## What the gate is, and what it is not

| | |
|---|---|
| **The gate is** | a check inside the application that stops it from sending text the data sheet does not cover, refuses everything while the sheet is unreviewed or contradicts itself, and refuses everything while the project-wide switch is off. |
| **The gate is not** | a decision about what is lawful or allowed. Your security and export-control reviewers decide that and write it into the data sheet. The gate will not go beyond what they wrote, and nobody can make it. |
| **The gate is not** | a wall. A switch in a web page is not a security control. The wall is the network: no route from the model host to the internet, no logging at the model host, and a gateway that only the pipeline can reach. The gate stops the application from knocking on that door with the wrong text. |

## The AI data sheet

One sheet per project. It records what the approvers were told about the model:

| Field | Values | Why it matters |
|---|---|---|
| Model | name and version, as the gateway reports it | an approval is for one model; a new version needs a new look |
| Where it runs | `ours` (our own servers), `tenant` (our organisation's cloud tenant), `vendor` (a vendor's shared service) | export-controlled text may only go to `ours` |
| Does text leave your network | yes / no | a vendor service always means yes |
| Prompts and answers are | `none` (not kept), `local` (kept on our servers), `service` (kept by the provider) | a provider that keeps prompts is a copy you do not control |
| Days kept | 1 to 3650, when anything is kept | retention is part of what was approved |
| Highest marking approved | `none` (no marking only), `cui`, `exp` (export controlled) | what the reviewers were willing to approve |
| A requirement with no marking recorded | `withhold` (keep the group from the AI) or `none` (treat as no marking) | an empty marking is not the same as "no marking" |
| Reviewed by, and the date | a name and a date | no name and date, no review, no AI |

### A sheet that contradicts itself opens nothing

Nothing is quietly capped. If the sheet has any of these problems, no group goes to the model until someone makes it consistent:

- `model`: no model is named.
- `values`: an answer is not one of the choices above.
- `vendor_leaves`: a vendor's shared service, but the sheet says the text does not leave.
- `leaves_marked`: the text leaves the network, but marked requirements are approved.
- `log_marked`: the provider keeps prompts and answers, but marked requirements are approved.
- `exp_where`: export-controlled text approved for anything but a model on your own servers.
- `days`: prompts are kept but the number of days is not a whole number from 1 to 3650.

## Markings

Each requirement carries a marking from the source system. The tool reads it, never edits it, and never guesses.

| The marking says | Reads as | Examples |
|---|---|---|
| nothing recorded (empty or missing) | `unstated` | `""`, no value |
| no marking | `none` | `No marking`, `Unmarked`, `Public` |
| CUI | `cui` | `CUI`, `CUI // Basic`, `Controlled Unclassified Information` |
| export controlled | `exp` | `ITAR`, `EAR99`, `CUI//SP-EXPT`, `Export controlled` |
| classified | `classified` | `SECRET`, `TS//SCI` |
| anything else | `unknown` | `Company confidential`, `Proprietary`, `Unclassified` |

A marking is read the same way in Python and in the page: any Unicode space (the non-breaking space too) at the ends is dropped and runs of spaces become one, a leading `/` is dropped, case does not matter, and a marking word has to stand on its own. A letter or digit of **any** alphabet stuck to it (`CUIé`, `ITARß`, `яsecret`, `CUI2`) makes it a word the table does not know, so it reads as `unknown`. A byte order mark (U+FEFF) is not a space: `CUI` after one still reads as CUI, `none` after one reads as `unknown`.

`classified` and `unknown` are never sent, whatever the sheet says. A marking style the table does not know has to be added to the table, in the open, with a test
case, rather than guessed at. Note that `Unclassified` is deliberately `unknown`: it says something about classification, not about CUI or export control.

A **group** is as restricted as its most restricted member. One CUI requirement makes the group CUI.

## The order the rules are checked

The first rule that says no wins, and every no carries a code:

1. The project switch is off: `off`.
2. The sheet has no reviewer or date: `unreviewed`.
3. The sheet has a problem: `sheet`.
4. The group's marking is `classified`, `unknown` or (when the sheet says to withhold) `unstated`: that code.
5. The group's marking is above what the sheet approves: `marking`.
6. Otherwise: `open`.

## Where the rules live

The rules are written twice, because the pipeline is Python and the page is JavaScript, and they are tested against one table so they cannot drift apart.

| Place | What it is |
|---|---|
| `reqin/src/reqin/aigate.py` | the library the pipeline uses: `gate(...)` returns a decision, `ensure(...)` raises `AiBlocked`, `load_use_file(...)` reads the page's `ai-use.json` |
| `prototype/parts/aigate.js` | the same rules in the prototype page |
| `docs/ai_gate_cases.json` | the one table of cases: markings, groups, sheets and complete gate decisions. `reqin/tests/test_aigate.py` and `prototype/verify.js` both run all of it |
| `reqin/tests/test_aigate_page.py` | feeds the Python library and the page's JavaScript the same tens of thousands of generated markings, groups and sheets (odd spaces, letters from other alphabets, control characters, every combination of sheet answers) and requires the same answer from both. It needs Node.js. It found that the two had read letters from other alphabets differently; the page now follows the Python rules above |

In the pipeline, put `ensure(...)` in front of the code that builds a prompt, and put no text in the prompt when it raises:

```python
from reqin.aigate import Sheet, AiBlocked, ensure

try:
    ensure(sheet, switch_on, [m.marking for m in cluster.members])
except AiBlocked as blocked:
    record_held(cluster, blocked.decision.code)      # off, unreviewed, sheet, marking, classified, unknown, unstated
else:
    answer = ask_model(build_prompt(cluster))
```

## What the prototype page does

- **AI use** page (left menu, under Policy and output): the project-wide switch, the data sheet and the form to change it, what the gate does with every group and why, the groups held back, the rules in plain words, and a history of changes.
- Only the **lead** can change the switch or the sheet, and not from a lens preview. Saving a sheet needs a reviewer's name; the date and who typed it in are recorded.
- A held group is shown **without any AI answer**, with the reason, in the review page, the assistant (switched off for that group) and the AI wording choice (not offered). A decision recorded earlier is not changed.
- Every change is an entry in the event chain, with a fingerprint of the sheet. A project file or browser copy whose switch or sheet **does not match its own record of events** is refused when it is loaded.
- `ai-use.json` can be downloaded: the switch, the sheet, the number of groups held back for each reason and the ID of each held group. It holds no requirement text.
- In the sample project the AI answers already exist, because the sample was made before the gate. The page hides them for held groups. **In the pipeline the gate runs before the call, so no answer is ever made for those groups.** The scores on the Methods page come from a trial run on the sample data set and do not move with the switch or the sheet.
- The sample project's markings are made up, the same way every time, so that every kind of hold can be seen. About one group in six is held back with the sample's starting sheet.

## What your IT and security staff still have to do

These are not in the application and cannot be:

1. **Network.** The model host has no route to the internet. The gateway is the only thing that can reach it, and only the pipeline can reach the gateway. This is what a malicious or mistaken change to the page cannot undo.
2. **Logging at the model host.** What the sheet says about prompt retention has to be true. Check it on the host rather than trusting the sheet.
3. **The marking source.** Markings come from the requirements system. If they are wrong or missing there, the gate cannot know. Decide whether an empty marking means "no marking" for your data (the sheet's last question) and who owns fixing markings at the source.
4. **Review of the sheet.** Who reviews it, how often, and when a new model version needs a new review. The page only records a name and a date.
5. **Export-control and classification rules.** Whether any text may go to any model, and which. The gate enforces the answer you give; it does not know the law.

## What has and has not been checked

| Checked | How |
|---|---|
| The markings, groups, sheets and decisions | One table of cases (`docs/ai_gate_cases.json`) run by both `reqin/tests/test_aigate.py` and `prototype/verify.js` |
| The page and the library agree | `reqin/tests/test_aigate_page.py` (with the other gate tests, 115 tests): the same generated inputs go to both and the answers must match. The comparison itself was shown to fail (a test breaks one side on purpose). It skips itself when Node.js is not installed. The first time it ran it found a real difference, which was fixed |
| The page in a browser | `prototype/b19.py`: 75 checks at each of 1440, 900 and 390 px (the switch, the sheet form, a held group in review and in the assistant, what is kept and written) |
| The checks bite | `tools/mutation/ai.py` changes the gate 93 ways (markings, the sheet's problems, the order of the rules, the switch, what is written to the record, what Home says about a loaded file); every change was noticed, 17 of them only because the page crashed, not by a case written for them (see [`tools/mutation/README.md`](../tools/mutation/README.md)) |
| **Not checked** | Any real program's markings or rules. That a reviewer reads the sheet before signing it. The network wall, which is not in the application. A marking style nobody has listed yet (it reads as `unknown` and is held back, which is the safe side, but it is a hold nobody asked for) |

## Limits

- The page keeps the switch and the sheet in the browser (not encrypted) and in project files. The record-of-events check catches accidents and hand edits, not a determined person: the page's fingerprint is a short demonstration hash, and the reference server's chain uses SHA-256. Anyone who can edit browser storage can edit what the page believes. The wall is the network.
- The prototype page is not connected to the reference server, so the sheet is per browser and per project file, not shared.
- Prompt and response logging, redaction of text inside a prompt, and per-user permissions on who may ask the AI are not built.
- Nothing here has been validated against a real program's data, markings or rules.
