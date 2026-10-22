# Prompt: find out whether a screen shows the person's real data, or only looks as if it does

How to use this: give an agent that can run commands in a checkout of this repository the text below the line, and the address (or file) of the page to audit. To give each hat to its own agent, see the section "One agent per hat". For an agent that cannot run commands, see the last section. It is the same task for any provider: nothing here depends on one agent's habits, and it names no product.

**Status.** The commands below were written and run here, end to end, against two made-up pages (one planted with faults, one clean), in one browser (Chromium). No agent other than the one that wrote them has followed this prompt, it has **not** been tried with a small or local model, and it has not been run on a real system. If you are the first outside agent: when a step does not work as written, say which step and what happened, and do not work around it silently.

----------------------------------------------------------------------------------------------------

You are helping a person find out whether a screen of their app shows **their real, current data**, or something that only looks right: values typed into the page, a sample shown when the source fails, a copy kept in the browser and shown with nothing to say it is a copy, a count written in once, a column that shows another field. Tests on made-up data do not find these, so the audit changes, empties and breaks what the page receives and looks at what the screen does. Read `AGENTS.md` in the repository root first and keep its rules: **everything in this repository is made up, and say what you did not check.** The person's own data stays in the session folder, which must be outside any git repository (`init` refuses otherwise); never copy it into this repository.

The scripts keep the order and the state; you do not have to remember anything. Every command prints the next thing to do and the next command to run. `design/data_audit/SKILL.md` has the same procedure with every check and every file explained; read it if anything below is unclear.

**The audit sends no write that it can see.** Every HTTP request the page makes that is not a GET, HEAD or OPTIONS is refused before it leaves the browser and is listed; a WebSocket goes nowhere; workers are not allowed to start. It cannot know whether a GET changes something on the server, it opens the page about eight times, and a setup click is a click on the person's page: tell the person that before you start, and do not point it at a system where that matters without asking. Never change the person's app or data to make a check pass.

## Do this, in this order, from the repository's top folder

1. **Start.** `python3 design/data_audit/scripts/audit.py init <SESSION> --page <PAGE>` (`<SESSION>` is a new folder outside any repository). Add what the person has: `--data <FILE>` (their own records: JSON, JSON lines or CSV), `--source <DIR>` (the app's source), `--before <FILE> --after <FILE> --key <FIELD>` (two copies of the data around a change); `--setup "click:Label"` for each click needed to reach the screen they mean; `--allow-post <REGEX>` only for a POST that is really a read. Ask for these; do not make them up.
2. **Ask what comes next.** `python3 design/data_audit/scripts/audit.py next <SESSION>`. Run the command it prints, in the order it gives. When it says it needs something from the person, ask for it in those words; if they have none, run the `skip` command it prints, so the brief lists the check as not checked (a skipped check means the brief cannot say "clear"). When it says a check "could not run", put that right (the page did not open, nothing was readable) and run it again, or skip it.
3. **Run and read.** `python3 design/data_audit/scripts/audit.py run <SESSION> <CHECK>` (the command `next` printed). Tell the person the verdict and read them every high finding in the printed words. Show the pictures it names. Add `--fresh` to open the page again after the person has changed the app.
4. **Repeat 2 and 3** until `next` says every check has run or been skipped.
5. **Put it together.** `python3 design/data_audit/scripts/audit.py brief <SESSION>` writes `<SESSION>/BRIEF.md`. Give it to the person and read them the part headed "Where this stands". Ask the questions at the end; do not answer them for the person.
6. **Write down what they decide.** `python3 design/data_audit/scripts/audit.py minutes <SESSION> --kind decision --said-by <NAME> --text "<what they said>"`. Then `python3 design/data_audit/scripts/audit.py verify <SESSION>`.

## One agent per hat

There are six hats: Database and data analyst, UI/UX engineer, Systems requirements engineer, Configuration management, Scribe, Chief of staff. One agent can wear them in turn (`next` says which). To give each to its own agent: `python3 design/data_audit/scripts/audit.py hat <SESSION> <HAT>` prints that hat's whole brief (purpose, rules, its checks and their commands, what to ask the person, what to look for, who to hand to), with `<HAT>` one of `data-analyst`, `ui-ux`, `systems-requirements`, `configuration-management`, `scribe`, `chief-of-staff`. All hats share the session folder. A hat may run only its own checks; `run` refuses the rest and says which hat owns it. The chief of staff puts the findings together with `brief`, and the scribe keeps the minutes. The hats' briefs are generated from `design/data_audit/hats.json`, so nothing needs copying out of this file.

## Rules that do not bend

- Run what `next` printed, in its order. Do not merge checks, skip them on your own, or report one you did not run.
- A check that was not run is never "clear", and **clear does not mean the screen is right**: it means that check found nothing of the kind it looks for. Say that in the words "this check found nothing", not "the screen is fine".
- Read the high findings aloud as printed; do not soften them or add to them. Where the answer is a choice (keep a fallback, show a message, allow a write), say what the choice is and ask the person.
- Never write real requirements, real exports or real names into this repository. The person's data lives in the session folder only.

## What "done" means, and what to report

Done is: every check has run or been skipped with a reason, the person has `<SESSION>/BRIEF.md`, has been asked its questions, and what they decided is in the minutes. Report: the readiness the brief gives (blocked, open, attention or clear; clear needs all eight checks to have run) and why; the high findings and where each was seen; the checks skipped or that could not run, and why; and, under **not checked**, each check's "cannot find" list from the brief plus: no agent has followed this prompt before you, it has not been tried with a small model, the pictures are drawings made by one browser on one machine, a GET that changes something on the server is not something the audit can see, and nothing was run on the person's real system unless they say it was.

## If you cannot run commands

Ask the person to run each command and paste what it prints, and to open each picture file themselves. Everything else is the same: you read the printed instructions to them, they run the next command. Say plainly that you have not run anything.
