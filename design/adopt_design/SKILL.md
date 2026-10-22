---
name: adopt-design
description: Bring parts of this product's design (menu, top bar, buttons, cards, screens) into someone else's existing app. Reads their page, asks one question at a time with pictures of each choice, keeps what they want of their own theme, and writes the code only after the person has seen the result and said yes.
---

# Adopt parts of our design into your own app

Use this when a person has an app or a page of their own and wants some of what this repository's design has: "I like your menu but not its colour", "only that card, not the
bottom bar", "keep my theme and add your screens on top". The person decides piece by piece. They see a picture of each choice before they make it, and nothing is written into
their app until they have seen the whole result and said yes.

It is built so that **the scripts, not you, keep the order and the state.** You never need to remember what was asked: every command prints the next thing to say and the next
command to run. A model that can run a shell command, read a short question aloud and type back the person's answer can use it. That is the design goal; it has **not** been
tried with a small model yet (see the last section).

## What you need

| You need | Where it comes from | If it is missing |
|---|---|---|
| The person's page | a web address (`http://...`) or an HTML file | ask for it: nothing here works from a description |
| This repository, checked out | the person | the commands below are run from its top folder |
| A browser the scripts can drive | `pip install -r design/adopt_design/requirements.txt && playwright install chromium` | the questions still work with `--no-pictures`, but without pictures the person is choosing blind: say so, and ask them to run `init` for you |
| What can be taken | `python3 design/adopt_design/scripts/catalog.py list` | it prints our parts and our screens |

If the person's page is behind a sign-in or needs clicks to reach the screen they mean, give `init` the steps with `--setup "click:Label"` (the same steps `tools/gui_checks/site_map.py` takes).

## The loop

Run every command from the repository's top folder. `SESSION` is a folder the scripts make; pick a name such as `adopt-session`.

**1. Read the page.**
`python3 design/adopt_design/scripts/adopt.py init SESSION --page PAGE`
This opens the page in a browser and writes `SESSION/mine/INDEX.md`: its theme, its palette, its fonts, its components, its menus and the role each colour plays, with every guess
marked. Tell the person where it is and read them the line it printed (how many values were read and how many are guesses).

**2. Ask.**
`python3 design/adopt_design/scripts/adopt.py next SESSION`
It prints one question, the choices, a picture to show (a file path), and the exact command that records the answer. **Say the question to the person in the words printed. Show
them the picture. Do not answer for them.** When they choose, run the command it printed with their choice.

**3. Record, and repeat.**
`python3 design/adopt_design/scripts/adopt.py answer SESSION QUESTION-ID CHOICE`
It records the answer and prints the next question. Keep going until it says every question is answered. The questions come in this order, and each is skipped when it does not apply:

| Question | What it settles |
|---|---|
| `stance` | keep your whole theme, take ours, or decide area by area |
| `area:...` | only when deciding area by area: colours, type, corners, shadows, control height |
| `guesses` | which of the values read from the page were guesses that are wrong |
| `parts` | which of our parts to bring (menu, top bar, draft bar, buttons, text box, card, chips, folding row, wording row) |
| `change:PART` | for each part chosen: what to change (colours, corners, type, shadow, height, icons), or nothing |
| `aspect:PART:WHAT` | for each thing to change: the options side by side, as pictures |
| `screens`, `rows:SCREEN` | which of our screens to get a build brief for, and which pieces of each to keep |

Two commands do not follow that order:
- `python3 design/adopt_design/scripts/adopt.py set SESSION ROLE VALUE` corrects a value read from the page ("the main colour is `#1A4DB5`").
- `python3 design/adopt_design/scripts/adopt.py back SESSION` takes back the last answer; `back SESSION --to QUESTION-ID` takes back that answer and everything after it.

If you lose your place, run `python3 design/adopt_design/scripts/adopt.py status SESSION` (what has been decided, in words) or `next` again. They change nothing.

**4. Show the whole result before anything is written.**
`python3 design/adopt_design/scripts/adopt.py preview SESSION`
It draws: your values and ours and the result side by side; each part chosen, in the result's colours; and **the person's own page, before and after**, with our menu and top bar drawn
over theirs (their own menu items in our menu) and their buttons, text boxes, cards and chips restyled. Show the person every picture it lists and read them the notes it prints
(what could not be drawn). Then ask: *is this what you want me to write into your app?*

**5. Record their yes, in their words.**
`python3 design/adopt_design/scripts/adopt.py approve SESSION --said "what the person said"`
It refuses an empty `--said`, and it refuses if any answer has changed since the pictures were drawn (`preview` again). **Do not approve for the person.**

**6. Write the files.**
`python3 design/adopt_design/scripts/adopt.py build SESSION`
It refuses unless the pictures were drawn and approved for exactly these answers. It writes `SESSION/out/`:

| File | What it is |
|---|---|
| `CHANGES.md` | start here: what was decided, role by role what the person's value is and what the result is, where each value came from, and the steps to put it in |
| `adopted-tokens.css`, `adopted.tokens.json` | the colours, type, corners, shadow and sizes, as CSS custom properties and in the Design Tokens format (version 2025.10) |
| `parts/PART/part.css`, `specimen.html`, `NOTES.md` | each part: the rules, a drawing of it, and where its real markup, menu paths, data and test marks are |
| `screens/SCREEN.md` | a build brief per screen: the pieces kept and dropped, where each piece's data comes from, where the screen sits in the menu |
| `REPORT.md` | what was not checked. Give it to the person |
| `decisions.json` | the answers, the resolved values and the person's approving words |

Nothing in the person's app has been changed. Give them `CHANGES.md`, or follow its steps for them if they have asked you to.

**7. After the code is in.**
`python3 design/adopt_design/scripts/adopt.py verify SESSION --page PAGE` reads the changed page again and says, role by role, whether it shows what was decided, and whether each part's
class is on the page. A role read as a guess can differ without being wrong; a part built with the person's own class names shows as "not found": look at it by eye.

## When something goes wrong

| It says | Do |
|---|---|
| `the question waiting is X, not Y` | run `next`, answer X |
| `not recorded: ... is not one of the choices` | tell the person the choices again; do not guess |
| `not built: the person has not said yes yet` | `preview`, show, ask, then `approve --said` |
| `pictures not made: Playwright is not installed` | install it (table above); or go on without pictures and say so |
| The pictures show a stand-in font | the note under the picture says which fonts this machine lacks; the real result uses the font chosen |
| The page could not be opened again for the preview | the other pictures are made; say the page preview is missing |
| `init` says a value is `missing` | the page has nothing that plays that part (for example no hover colour); ours is used and `REPORT.md` says so |

## Rules that do not bend

- One question at a time, in the printed words. Do not merge questions, reorder them or skip them.
- Show the picture before the person answers. If there is none, say there is none.
- Never invent a colour, a size or a font. A value comes from the page (`mine`), from `design/tokens.css` (`ours`), or from the person (`set`).
- Never approve for the person, and never run `build` around its refusal by editing `session.json`.
- Say what was not checked: give the person `REPORT.md`, and say that the pictures are drawings of the decision made by one browser (Chromium) on one machine, not the code.
- This repository's rules apply to anything you write into it: everything in it is made up; no real requirements, exports or names.

## What is in this folder

| Path | What it is |
|---|---|
| `scripts/adopt.py` | the session: init, next, answer, set, back, status, preview, approve, build, verify |
| `scripts/index_page.py` | reads a page into `index.json` and `INDEX.md` (use it alone when the person only wants a synopsis of their page) |
| `scripts/catalog.py` | what can be taken: `list`, `css PART` (the rules a part really uses) |
| `scripts/roles.py`, `roles.json` | the shared vocabulary: 21 roles (what colour is the main button, how round are the corners, ...) that a page and our design both answer, and which of our tokens each drives |
| `scripts/render.py` | draws the pictures |
| `scripts/build_out.py` | writes the files; reads a changed page for `verify` |
| `catalog.json`, `specimens/` | our parts: what each is, which stylesheet rules it uses, and a made-up drawing of it |
| `examples/sample_app/`, `examples/sample_index/` | a made-up page to try it on, and what reading it gives |
| `RESEARCH.md` | what was read to design this, what was used and what was not |

## What has not been checked

- **No agent has followed this skill yet**, large or small. The commands were run end to end by the person who wrote it, on a made-up page, in one browser (Chromium). The claim that
  a small local model can run it is the design goal and is **untested**.
- The values read from a page are what the browser computed. Which element is "the main button" when there are several is a rule (the most used coloured filled button); the
  `guesses` question exists for that.
- A picture is a drawing of a decision. Our parts are drawn from specimens made for this kit with the stylesheet rules our design really uses; the page preview restyles the person's
  elements by the selectors the index found. Neither is the code that will be written.
- Not read: a second theme (dark mode), anything behind a click or sign-in that `--setup` did not do, gradients and images, styles inside cross-origin stylesheets or shadow roots,
  and the layout at narrow widths.
- Screens are build briefs from `design/navigation.json` and `docs/SCREEN_DATA_MAP.md`. They have no pictures and nothing was built from them here.
