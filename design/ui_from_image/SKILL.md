---
name: ui-from-image
description: Turn a screenshot or mock-up into screens that use an existing site's own CSS and real data. Cut the picture into component frames, read the target's real colours, type and component styles, map the picture's colours onto them, write a checked component spec, build, bind to data, verify.
---

# From a picture to a screen in the target's own style, bound to real data

Use this when you are given a picture of a screen (a screenshot, a mock-up, a drawing, a page you cannot copy the source of) and asked to build or restyle a screen
so that it **looks like the site it will live in** and **shows the user's data**. It exists because the two usual shortcuts both fail:

- *Copy the page.* A picture, or the exported source of a design tool, is not a stylesheet. Colours come out a few shades off, a font that was never loaded falls back to
  another one, a value that a runtime injected is missing. The result is "the CSS is off".
- *Restyle to the target and stop.* The screen then looks right and is a painting: every number, name and status is typed into the markup, so it shows the sample and
  never the user's data.

The procedure below is plain files and plain commands. Any agent that can run a shell can follow it. An agent that cannot (a chat with no tools) can follow the same
steps by hand with the person running the commands: see the last section.

Everything in `scripts/` is deliberately small and says what it did not look at. Nothing here is a model: the colour arithmetic, the block cutter and the checks are
ordinary code, so two agents given the same picture get the same answer.

## What to have before you start

| You need | Where it comes from | If it is missing |
|---|---|---|
| The picture(s) | the person | ask for it: you cannot do this from a description |
| The target's design language | a running page: `scripts/target_tokens.py PAGE`; or a token file such as `design/tokens.css` | with neither, you are inventing a design: stop and say so |
| What data each part of a screen shows | `docs/SCREEN_DATA_MAP.md`, and `python3 tools/gui_checks/datapaths.py --json paths.json` for the list of real field paths | with no map, every number you place is invented: say so in the spec as STATIC and do not call the screen finished |
| A browser the scripts can drive | `pip install -r requirements.txt && playwright install chromium` | `target_tokens.py` will not run: ask the person to run it and send you `target_tokens.json` |
| The marks a screen carries and the checks it must pass | `docs/GUI_TEST_HOOKS.md`; `tools/gui_checks/hardcode_scan.py` and `tools/gui_checks/probe.py`; `design/reference_viewer/` is a screen that passes them | without them, step 6's gate is your own word: say so |

## The procedure. Each step has a gate: do not go on until it holds.

**1. Read the target before you look at the picture.**
`python3 scripts/target_tokens.py PAGE --out target_tokens.json --shots shots/`
Open `target_tokens.json`. It lists the page's declared `--variables`, every colour it paints with (and which variable names it), its fonts (and whether each one
*rendered* or fell back), radii, shadows, spacing, and for buttons, links, inputs, badges, nav items and cards each distinct look with what hover and keyboard focus change.
*Gate:* you can say, in a sentence each, what the target's primary button, input and card look like. **The target's CSS wins every time it disagrees with the picture.**

**2. Cut the picture into frames, and look at the cuts.**
`python3 scripts/frames.py grid shot.png grid.png` (a labelled grid: read positions off the picture, do not estimate them)
`python3 scripts/frames.py detect shot.png out/` (candidate blocks; open `out/overview.png`)
`python3 scripts/frames.py detect shot.png out2/ --region X,Y,W,H --min-gap 6` to look inside one block more finely
`python3 scripts/frames.py crop shot.png frames/ --box primary-button=280,405,205,44 ...`
`detect` splits along empty bands and long straight borders. It finds blocks, not buttons: two buttons 8 px apart stay one block until you ask it to look closer.
*Gate:* you have **looked at each crop** and it is the component you named. A crop that is the wrong thing means the box was wrong; fix the box, do not build from it.

**3. Take the picture's colours, then map them onto the target's.**
`python3 scripts/palette_from_image.py shot.png --json palette.json --swatches swatches.png`
`python3 scripts/conform.py --source palette.json --target target_tokens.json --out conform.json`
Each colour in the picture is *use* (the target has it, distance up to 6), *review* (6 to 12: look and decide) or *none* (over 12). Use the target's colour for *use*.
*Gate:* every *review* and *none* has a decision written down: a new token (with a reason), a different existing token, or a question to the person.
A *none* is an answer. Never swap in the nearest colour to make the table look complete.

**4. Write the component spec, then check it.**
One entry per component, in `reqin-components/1` (`component.schema.json`, example in `examples/home_components.json`): its kind, its states, its style **as token names
only**, and for each slot where its content comes from: `STATIC` (text that is part of the design), `NONE` (decoration), or a field path that exists in real output.
`python3 scripts/check_component_specs.py spec.json --tokens target_tokens.json --paths paths.json`
*Gate:* no errors. The report lists every STATIC slot: look at each. A slot that holds a number, a name or a status and says STATIC is a hard-coded screen.

**5. Build one component at a time, from tokens.**
Use the token names (`var(--accent)`), never a hex value or a pixel size you read off the picture. Build a component, screenshot it alone, put its screenshot beside the crop
from step 2, and look at both. Structure, order, spacing rhythm and what is emphasised should match the picture; colour and type come from the target, not the picture.
*Gate:* the component and its crop look like the same component in the target's clothes.

**6. Bind to data in the same pass, not afterwards.**
The screen reads **one canonical dataset** through one view-model function (`docs/SCREEN_DATA_MAP.md`; `reqin/GUI_CONTRACT.md`: the GUI never reads a file, a database or a
server, only a canonical dataset). No sample text in markup, no counts typed in, no generated rows. Make the page take a dataset (a file input, and `?dataset=` so a test can
load one). Show an empty state when there is nothing, and say "not provided by this source" for a field a source does not give: never fill the gap with a plausible value.
*Gate:* load two different datasets: the numbers, names and lists change, and each count equals what the dataset says. In this repository that gate is a command:
`python3 tools/gui_checks/hardcode_scan.py APP` and `python3 tools/gui_checks/probe.py --app APP --datasets DIR` (`DIR` from `reqin make-datasets DIR --size 5000`), which open all fourteen test datasets in a browser and compare the screen with the files. They need the marks in `docs/GUI_TEST_HOOKS.md`.

**7. Verify the result as a stranger would.**
`python3 scripts/target_tokens.py BUILT_PAGE --out built_tokens.json`
`python3 scripts/conform.py --source built_tokens.json --target target_tokens.json --strict`
(`--strict` is for a page you wrote: a colour 4 steps from a token is a different colour.) The built screen's colours should all be *use* against the target; its fonts should have rendered, not fallen back; no console errors; no horizontal overflow at 1440, 900, 390
and 320 px wide. Then compare the built screenshot with the picture for structure.
*Gate:* say what you checked and what you did not. A screen that was only looked at is "looked at", not "verified".

## Rules that keep a run from wasting time

- **Never copy markup from a design-tool export** (a "canvas" page, a runtime-injected variable, inline styles with literal colours). Read it for structure; build from tokens.
- **Never read a colour off pixels when a token exists.** Pixels are a few steps off after compression and anti-aliasing; the palette tool merges those, and `conform.py` snaps to the token.
- **Do the cheap checks first.** Steps 1, 3 and 4 take seconds and catch most of what goes wrong. Do not start building before they pass.
- **Stop, report and ask** when the target has no token for something the picture needs, when a field has no producer in the data map, or when a step's gate does not hold after
  two tries. Say what you tried. Do not loop.
- **One writer per file.** If several agents work at once, split by component or screen, give each its own files, and merge only what passes the checks.
- **Claim what a check shows and no more.** "The colours are the target's" is true after step 7; "it looks right" is an opinion until someone looks.

## What the scripts do not do

- `frames.py detect` does not know what a button is. It will cut through a block whose parts are closer together than `--min-gap`, and it will merge things that touch.
  Always look at `overview.png`.
- `palette_from_image.py` reads flat colours. A gradient, a photograph or a thin 1 px line can be missing or mis-named; `role_hint` is a heuristic, written out in the script.
- `target_tokens.py` reads what one browser drew at one width with no sign-in and no clicks. A state it cannot reach (an open menu, a signed-in view) is not measured.
- `conform.py` is colour distance between colours of the same job. It cannot see where a colour sits in the picture.
- `check_component_specs.py` checks that names and paths exist and that no literals slipped in. It cannot tell that a STATIC slot should have been bound: you must.
- Nothing here checks accessibility beyond contrast arithmetic. Read `docs/ACCESSIBILITY.md` and test with the real thing.

## If you cannot run commands (a chat with no shell)

Ask the person to run steps 1 to 3 and to send you `target_tokens.json`, `palette.json`, `conform.json` and `out/overview.png`; then do steps 4 to 7 by writing the spec and the
code as files they can run, and ask them to run `check_component_specs.py` and send back its output. Do not describe a colour or a size from memory of the picture: if the
numbers are not in a file you were given, say you do not have them.
