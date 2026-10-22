# Prompt: bring parts of this product's design into someone's own app, one choice at a time

How to use this: give an agent that can run commands in a checkout of this repository the text below the line, and the address (or file) of the page to change. For an agent that cannot run commands, see the last section. It is the same task for any provider: nothing here depends on one agent's habits, and it names no product.

**Status.** The commands below were written and run here, end to end, on a made-up page, in one browser (Chromium). No agent other than the one that wrote them has followed this prompt, and it has **not** been tried with a small or local model. If you are the first outside agent: when a step does not work as written, say which step and what happened, and do not work around it silently.

----------------------------------------------------------------------------------------------------

You are helping a person bring parts of this repository's design (its side menu, top bar, buttons, text boxes, cards, chips, rows, and a build brief for each of its screens) into **their own app or page**, keeping whatever they want of their own look. The person decides piece by piece, sees a picture of every choice before making it, and sees the whole result before anything is written. Read `AGENTS.md` in the repository root first and keep its rules: **everything in this repository is made up, and say what you did not check.**

The scripts keep the order and the state; you do not have to remember anything. Every command prints the next thing to say and the next command to run. `design/adopt_design/SKILL.md` has the same procedure with every file explained; read it if anything below is unclear.

## Do this, in this order, from the repository's top folder

1. **Read the page.** `python3 design/adopt_design/scripts/adopt.py init <SESSION> --page <PAGE>` (`<SESSION>` is a new folder name; add `--setup "click:Label"` for each click needed to reach the screen the person means). Tell the person what it printed and where `<SESSION>/mine/INDEX.md` is: it is a synopsis and index of their page (theme, palette, fonts, components, menus, and the role each colour plays), with every guess marked.
2. **Ask, one question at a time.** `python3 design/adopt_design/scripts/adopt.py next <SESSION>`. Say the question to the person in the words printed. Show them the picture it names. Do not answer for them. Record their choice with the command it prints (`answer <SESSION> <QUESTION-ID> <CHOICE>`), which prints the next question. Repeat until it says every question is answered. To correct a value read from their page: `set <SESSION> <ROLE> <VALUE>`. To take back an answer: `back <SESSION>`. If you lose your place: `status <SESSION>` or `next <SESSION>`.
3. **Show the whole result.** `python3 design/adopt_design/scripts/adopt.py preview <SESSION>`. Show the person every picture it lists (including their own page before and after) and read them every note it prints, including the notes about what could not be drawn and any contrast below the usual minimum. Ask: *is this what you want me to write into your app?*
4. **Record their yes in their words.** `python3 design/adopt_design/scripts/adopt.py approve <SESSION> --said "<what they said>"`. Never approve for them. If any answer changes later, go back to step 3.
5. **Write the files.** `python3 design/adopt_design/scripts/adopt.py build <SESSION>`. Give the person `<SESSION>/out/CHANGES.md` (what changes and how to put it in) and `<SESSION>/out/REPORT.md` (what was not checked). Do not change their app unless they ask you to; if they do, follow `CHANGES.md` step by step.
6. **After the code is in.** `python3 design/adopt_design/scripts/adopt.py verify <SESSION> --page <PAGE>`.

## Rules that do not bend

- One question at a time, in the printed words; no merging, reordering or skipping. Show the picture first; if there is none, say there is none.
- Never invent a colour, size or font. Values come from the page, from `design/tokens.css`, or from the person.
- Never run `build` around its refusal (for example by editing the session file). It refuses on purpose until the person has seen the pictures and said yes for exactly these answers.
- Never write real requirements, real exports or real names into this repository or into a session you keep in it.

## What "done" means, and what to report

Done is: the person has seen the pictures, said yes, and has `CHANGES.md`. Report: which choices were made; which values were guesses and what the person said about them; which pictures could not be drawn and why; the contrast notes; what `verify` said (or that it was not run); and, under **not checked**, the list in `<SESSION>/out/REPORT.md` plus: no agent has followed this prompt before you, the pictures are drawings made by one browser, and screens are build briefs that nothing was built from.

## If you cannot run commands

Ask the person to run each command and paste what it prints, and to open each picture file themselves. Everything else is the same: you read the printed question to them, they choose, you tell them the next command. Say plainly that you have not run anything.
