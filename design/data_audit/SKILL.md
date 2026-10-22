---
name: audit-data-binding
description: Find out whether a screen shows the person's real, current data, or something that only looks right (typed in, sample, kept from an earlier load, or the wrong field). Runs read-only checks, one hat at a time or one agent per hat, and writes a brief of what is wrong, what was not looked at, and what the person has to decide.
---

# Audit what a screen really shows

Use this when a person has a screen, a page or an app and the worry is: *it looks right, but is it their data?* A requirement typed into the page instead of read from the source. A count
that was written in once and stayed. A sample shown when the source fails. A copy kept in the browser and shown with nothing to say it is a copy. A column that shows another field.
None of these fail on made-up data, so a test on made-up data does not find them. These checks change the data the page receives, empty it, break it and cut the connection, and then look
at what the screen did.

It is built so that **the scripts, not you, keep the order and the state.** Every command prints the next thing to do and the exact command to run. A model that can run a shell command, read
what it printed and ask the person what it says to ask can use it. That is the design goal; it has **not been tried with a small model** yet (see the last section).

## What the audit does and does not do

- It **sends no write that it can see.** The page is opened in a browser the scripts drive. Every HTTP request that is not a GET, HEAD or OPTIONS is refused before it leaves the browser and is listed in
  the findings; a WebSocket the page opens is given a connection that goes nowhere; web workers, WebRTC and WebTransport are not allowed to start; service workers are blocked. If a POST is how the page
  reads (a search, a query), the person names it once with `--allow-post REGEX`. **What this does not cover:** a GET that changes something on the server (some do), a click the setup steps make on the
  person's page, and the fact that the page is opened many times (about eight loads for a full audit, more with `--fresh`), so a GET that counts visits counts them all. Do not point the audit at a system where that matters without
  asking the person.
- It keeps the person's data in a **session folder** that must not be inside a git repository (`init` refuses). It never copies their data into this repository. The folder also holds a copy of what the
  browser kept after the first visit (`visits/storage.json`), which can include a sign-in: it is readable by the person who ran the audit only, and the folder must not be shared.
- A check that was not run is never "clear": the brief lists it as not checked, with the reason, and **a skipped check keeps the brief from saying "clear" at all**. A check that found nothing says what it
  looked at and what it cannot see.
- **A clear result does not mean the screen is right.** It means this check found nothing of the kind it looks for. Only a person who knows the data can say a screen is right.

## What you need

| You need | Where it comes from | If it is missing |
|---|---|---|
| The person's page | a web address (`http://...`), or an HTML file or folder | ask for it: nothing here works from a description |
| This repository, checked out | the person | the commands below are run from its top folder |
| A browser the scripts can drive | `pip install playwright pillow && playwright install chromium` (Playwright 1.48 or newer: older ones cannot refuse a WebSocket, and the audit stops) | `trace`, `canary`, `outage`, `marks` and `states` cannot run: say so; the brief lists them as not checked |
| A file of their own records (JSON, JSON lines or CSV) | the person, from their own source | `known` is skipped with the reason, and the brief says so |
| The app's source folder | the person | `scan` is skipped with the reason |
| Two copies of the data, before and after a change, and the field that identifies a record | the person | `diff` is skipped with the reason |

If the screen needs clicks to reach, give `init` the steps with `--setup "click:Label"` (the steps `tools/gui_checks/site_map.py` takes: `click:Label`, `wait:500`, `goto:URL`; there is no step that types
text). If it is behind a sign-in, give a sign-in the person made themselves with `--storage-state FILE` (the file is read, not changed; a copy of what the browser holds after the first visit is kept in the
session folder). Never ask for a password. If the page draws late, give `--settle MS` (how long it must be quiet on the network before the screen is read; the default is 800).

## The loop

Run every command from the repository's top folder. `SESSION` is a folder the scripts make, outside any git repository.

**1. Start.**
`python3 design/data_audit/scripts/audit.py init SESSION --page PAGE`
Add what the person has: `--data FILE` (their records, and `--id-field NAME` / `--text-field NAME` if the names are not obvious), `--source DIR` (the app's source), `--before FILE --after FILE --key FIELD`
(two copies of the data), `--allowed FIELDS` and `--expect IDS` (what the change was meant to touch). Nothing is opened yet.

**2. Ask what to do next.**
`python3 design/data_audit/scripts/audit.py next SESSION`
It prints which check is next, which hat is wearing it, what the check does, and the exact command to run. When a check needs something from the person, it says what to ask for, and gives the
`skip` command for when they have none. **Run the command it printed. Do not choose another check; do not reorder them.**

**3. Run, and read what it says.**
`python3 design/data_audit/scripts/audit.py run SESSION CHECK`
It prints a verdict (`PROBLEM`, `attention`, `clear`, `NOT RUN`), the findings by severity with what was seen on the screen and what to do, and the files it wrote (pictures included). Tell the
person the verdict and read them the high findings in the words printed. Do not soften them and do not add to them. Add `--fresh` to open the page again instead of reusing the visits saved in the
session (do that after the person has changed the app). Add `--strict` to make the exit code 1 when a check finds a problem or could not run.

**4. If a check will not be run.**
`python3 design/data_audit/scripts/audit.py skip SESSION CHECK --because "the person has no records to give"`
The brief then lists it as not checked, with that reason. A check left out without `skip` is reported as not run.

**5. Repeat 2 to 4** until `next` says the checks have run or been skipped.

**6. Put it together.**
`python3 design/data_audit/scripts/audit.py brief SESSION`
It writes `SESSION/BRIEF.md` and `SESSION/report.json`: the readiness (`blocked` when any finding is high; `open` when any of the eight checks was not run, was skipped or could not run; `attention` when all
ran and found smaller things; `clear` only when all eight ran and found nothing), what to fix first, what was not looked at and why, the pictures, and the questions the person has to answer. Give them `BRIEF.md` and read them the part headed "Where this stands".

**7. Write down what they decide.**
`python3 design/data_audit/scripts/audit.py minutes SESSION --kind decision --said-by NAME --text "WHAT THEY SAID"`
The minutes only grow: an entry is never changed, and each carries a fingerprint of the one before it. `python3 design/data_audit/scripts/audit.py verify SESSION` checks the chain and that no check is
both skipped and run. `python3 design/data_audit/scripts/audit.py status SESSION` says, check by check, where things stand. `python3 design/data_audit/scripts/audit.py list` prints every check and every hat.

## The checks

| Check | What it does | What it finds | What it cannot find |
|---|---|---|---|
| `trace` | takes every number, ID and sentence on the screen and looks for it in what the page loaded and in the page's own code | a value found only in the code (typed in); values no response explains; a request that writes (refused); a socket or worker the page tried; a count or sum of the data, and which | a typed-in value that happens to equal the real one; a wrong field in the right place; values built from pieces at run time; plain words (names, titles); a page whose HTML the server writes from data (its values look typed in); see "Which values are looked at" |
| `canary` | loads the page again with every text and number in the data replaced by an invented one that carries the name of its field | values that stay although their source changed; a column that shows another field (when its heading is the field's name); how much of the screen follows the data at all | data that does not come through a request the audit can change (a socket, an event stream, a worker, a server-rendered page); a typed-in count equal to the number of records (`outage` empties the data); a page that turns what it gets into its own words |
| `outage` | loads the page with the data empty, with the source failing, and with the connection down, once in a clean browser and once in a browser holding what the first visit left | old or sample values after the source gave nothing or failed; a copy kept in the browser and shown with nothing to say it is a copy; a blank screen; a count that does not change when the records do | a slow source (it does not wait out real timeouts); partial failures; what happens after days of staleness |
| `marks` | looks for the marks that say where each part got its data and when, checks they carry words and change when the source is emptied, fails or is down | no sign whether the data is live, cached or sample; a mark that says live while the source is failing | whether the words are clear to a person or true (they are compared with the state using a short list of English words); marks that are only colour or an icon; parts of the screen with no mark |
| `states` | draws the screen with data, with none, with an error and with no connection, side by side in one picture (`states.png`) | an error that looks like the normal screen; an empty screen that looks like a full one | whether a state is well designed: a person has to look at the picture |
| `known` | picks a handful of records from the person's own data (first, last, a middle one, the longest, one with unusual characters), writes a sheet to tick, and looks for each on the screen with its other fields beside it | a record whose ID is on the screen with a different text, owner or status; a record missing from the screen | records on another page or behind a search the setup steps do not reach; records the sample did not pick |
| `scan` | reads the person's code and markup (`.js .jsx .ts .tsx .vue .svelte .html`) for requirement-shaped sentences, IDs, records and counts written into them, and for browser storage used as a second source of data; lists the files and folders it did not read | sample data written into code or markup | sample data in JSON, CSV, YAML, SQL or Python files (it lists them, it does not read them); anything in `node_modules`, `dist`, `build`, `vendor`; code that builds the same things at run time; files not given |
| `diff` | compares two copies of the same data record by record and field by field; it never writes | a change nobody asked for; a record that disappeared; a field that changed in many records at once | whether the change is right: a person has to read it before anything is pushed |

The values the audit looks at are sorted into five classes, and a finding says which: *bound* (found in what the page loaded), *derived* (a count or sum of it), *typed* (found only in the page's code or
markup), *clock* (a date or time found nowhere) and *unexplained*.

**Which values are looked at.** Only these: numbers of 10 or more, decimals and percentages (a single digit only where the element is marked as a count: a `data-testid`, `id` or class with count, total, sum,
metric, score, number, percent or share in it; zero is ignored); IDs written in capitals with a number (`PMP-0012`, `SYS_REQ_7`; **not** `pmp-0012`, **not** `R-4`); dates; times; and sentences of 24 or more
characters with *shall*, *must* or *should*. **Plain words are not looked at**: a name, a title or a status typed into a page passes `trace` and `canary`; `known` against the person's own records is what
checks them. A sentence is matched to the data with a few words allowed in front (an ID, a label) and behind (an owner, a status); a change inside it is found, a change in its first four or last six words
may not be. A number that appears only inside a long text in the data is not taken as a number of the data. Records held by ID (`{"PMP-0012": {...}}`) count: their keys are searched and changed too.

## The marks a page can carry

What lets a person (and `marks`) tell live data from the rest is a small convention, which a screen can add without changing how it works:

```html
<span data-source="requirements" data-source-state="live" data-as-of="2026-10-21T16:30:00Z">
  <span data-source-label>Live from the server</span>
</span>
```

`data-source` names the source. `data-source-state` is one of `live`, `cached`, `sample`, `empty`, `error`, `loading` and changes when the state does. `data-source-label` holds the words a person reads, so the state is
never colour alone, and `marks` checks that the words say the state (it also catches a mark whose attribute says `error` and whose words say "Live"). `data-as-of` says when the data was read. This repository's test hook
`body[data-state]` (`idle`, `loading`, `ready`, `empty`, `error`; see `docs/GUI_TEST_HOOKS.md`) is read but does not count as a sign to a person: nobody can see an attribute.
`design/data_audit/examples/good_app/` carries them; `examples/bad_app/` is the same screen with the faults this audit exists to find. Both are made up.

## The hats

One agent can wear the hats in turn (`next` says which), or each hat can be given to its own agent: `python3 design/data_audit/scripts/audit.py hat SESSION HAT` prints that hat's whole brief
(purpose, rules, its skills and their commands, what to ask the person, what to look for, who to hand to). **A hat may run only its own checks,** and `run` refuses a hat that names a check it does not own and says
which hat does. This is a way of working, not a lock: the commands the scripts print carry `--hat`, but nothing proves who typed a command. Every hat writes into the same session folder, so the brief can put them
together; commands that write to it take a short lock, so several agents can share one folder.

| Hat (name to use with `hat`) | Purpose | May run |
|---|---|---|
| `data-analyst`: Database and data analyst | whether what is on the screen really comes from the data, and what it does when the data is empty, wrong or missing | `trace`, `canary`, `outage`, `known`, `diff` |
| `ui-ux`: UI/UX engineer | whether a person looking at the screen could tell live from cached, sample, empty and failed | `marks`, `states`, `outage` |
| `systems-requirements`: Systems requirements engineer | that the records a person knows are on the screen with the right ID, text and fields, word for word | `known`, `trace` |
| `configuration-management`: Configuration management | what changed between two copies of the data, whether anything outside what was meant to change did, and where a second copy is kept; nothing is written back before a person has read the difference | `scan`, `diff`, `marks` |
| `scribe`: Scribe | the record: what was run, what was found, what the person said and decided | `minutes` |
| `chief-of-staff`: Chief of staff | put the findings together, say what matters first, what was not looked at, and what the person has to decide | `brief`, `skip`, `minutes` |

Rules every hat keeps: never write to or change anything in the person's app, the system behind it or any file of theirs; never put the person's data into this repository or any file outside the session
folder; never say a check passed when it was not run, or that it covers more than its "cannot find" column says; never decide for the person: where the answer is a choice, say what the choice is and ask.

## When something goes wrong

| It says | Do |
|---|---|
| `refused: the X hat may not run Y` | put on the hat that owns it (the message prints the command), or run `next` |
| `NOT RUN` with `the page did not open` | check the address with the person; the check is not clear, so do not report it as clear |
| `no data requests` from `trace` | the page asked for nothing the audit could see: ask the person what to click first, and `init` again with `--setup` |
| `nothing readable was found on the screen` | the content is in a picture, a canvas or a closed shadow root, or is drawn later than the audit waits, or is behind a click: `init` again with `--settle MS` or `--setup`; `canary` and `outage` are NOT RUN until something can be read |
| a request listed as refused (`POST`, `PUT`, `DELETE`) | tell the person the page writes when it opens; that is a finding. If the POST is how the page reads, they can name it with `--allow-post REGEX` |
| a WebSocket, worker, WebRTC or WebTransport listed as refused | tell the person: the audit does not let them carry data, so what the page gets that way was not seen |
| `the page left for an address the audit would not open` | the page sent the browser away with a form post or a link the audit refused; the check is NOT RUN. Ask the person which screen they mean |
| the brief says `OPEN` and lists a skipped check | nothing was looked at by that check; ask the person whether to get what it needs, or say so in the minutes |
| `init` refuses the folder | it is inside a git repository: pick another place for the session |
| a check needs data, source or two copies | ask the person; if they have none, `skip` it with the reason |

## Rules that do not bend

- Run the command `next` printed, in its order. Do not merge checks, skip them on your own, or report one you did not run.
- The audit sends no write that it can see. Never edit the person's app or data to make a check pass, and never run a check around its refusal.
- Say what a result means and no more: `clear` is "this check found nothing of its kind", never "the screen is right".
- Read the high findings aloud in the printed words; show the pictures (`states.png`, and the ones under `visits/`); say the pictures are drawings of one browser's view on one machine.
- The person decides. Write what they decide in the minutes in their words.
- This repository's rules apply to anything you write into it: everything in it is made up; no real requirements, exports, names or programmes. The session folder is where the person's data lives, and it stays outside.

## What is in this folder

| Path | What it is |
|---|---|
| `scripts/audit.py` | the session: init, next, hat, run, skip, minutes, brief, status, verify, list |
| `scripts/audit_values.py` | finds the values on a screen and sorts them (bound, derived, typed, clock, unexplained) |
| `scripts/audit_net.py` | opens the page with the data changed, emptied or failed; refuses writes, sockets and workers; saves each visit |
| `scripts/audit_checks.py` | `trace`, `canary`, `outage`, `marks`, `states` |
| `scripts/audit_files.py` | `known`, `scan`, `diff` (they read files, and a saved visit) |
| `scripts/audit_report.py` | the brief: readiness, order, what was not run, questions |
| `scripts/audit_common.py` | the session folder, the minutes and their fingerprints, the shape of a finding |
| `skills.json`, `hats.json` | the whole list of checks and hats; nothing else is a check or a hat |
| `examples/` | a made-up app that reads everything from its data and says what state it is in (`good_app`), the same screen with faults planted in it (`bad_app`), made-up records, and a small server that records any write it receives |

## What has not been checked

- **No agent has followed this skill yet**, large or small. The commands were run end to end by the person who wrote it, against the made-up apps in `examples/` and some small pages written for tests, in one
  browser (Chromium) on one machine. An independent reviewer then tried to make it say "clear" for a screen that is wrong and found several ways; those were fixed and each has a test, but the same reviewer has
  not looked again. The claim that a small local model can run it is the design goal and has **not been tried with a small model**.
- Nothing here has been run on a real system. A real app can load its data in ways these checks do not see (sockets, server-rendered pages, values built from pieces at run time, browser storage written by an earlier visit);
  each check's "cannot find" column says which.
- The checks find a screen that shows what it was not given. They do not find a screen that shows a real record in the wrong place, a typed-in value that equals the real one, or a wrong field under a heading that is not the field's name.
  `known`, run against records the person knows, is the nearest thing to that, and it checks only the records it picked.
- A slow source, a source that fails for some requests and not others, and staleness over hours or days are not simulated.
- "Sends no write that it can see" is about HTTP requests, sockets, workers and the browser's other channels the scripts block. A GET with an effect on the server, WebRTC or WebTransport on a browser the scripts
  do not control, and anything a setup click starts are outside it.
- Words are matched in English only (the marks and the "says something about its state" tests), and a page in another language is judged on what it shares with these words.
- The minutes' fingerprints show a slip, not a person: someone who can change the minutes and the small file that holds their last fingerprint can change both.
- The pictures are for a person to look at. Whether a state is clear to a reader is not something a script can say.
- **A clear result does not mean the screen is right.** It means the checks that ran found nothing of the kind they look for.
