# Design kit

What an agent or a person needs to build a screen that looks like the product, shows the user's data, and can be checked. Nothing here is a screen the product ships:
the screens to ship are built from this with the steps in [`docs/agent_prompts/build_the_gui.md`](../docs/agent_prompts/build_the_gui.md).

| Path | What it is | Use it to |
|---|---|---|
| `tokens.json` | The design language as data: colours (with the names the prototype used), the three type families and sizes, spacing, radii, targets, shadows | change the look in one place. It is the source of truth |
| `tokens.css` | Generated from `tokens.json` by `make_tokens.py`: custom properties, the nine font faces, and a few classes (`.rq-card`, `.rq-button`, `.rq-primary`, `.rq-input`, `.rq-statement`, `.rq-id`, `.rq-caption`) | link it from a screen and write `var(--accent)`. **Never edit it by hand** (`python3 design/make_tokens.py --check` fails when it is stale) |
| `make_tokens.py` | Writes `tokens.css`; `--install DIR` copies it and the font files into another app; `--coverage` says how many of the prototype's literal colours the tokens name | keep the CSS true to the JSON; carry the look into a different app |
| `ui_from_image/` | A procedure and small scripts for going from a picture of a screen to components in a site's own look: cut the picture into blocks, take its palette, read the target page's real colours, fonts and component styles in a browser, map one onto the other, write a checked component spec. Start at its `SKILL.md` | restyle or rebuild a screen from a screenshot without copying the page it came from |
| `adopt_design/` | A skill with scripts for the other direction: someone has their own page or app and wants some of this design in it. It reads their page (theme, palette, fonts, components, menus), compares it with `tokens.css`, asks one question at a time with a picture of each choice (keep your theme, take ours, or area by area; which parts; what to change in each part; which of our screens, shown as a sheet, and which frames of each, shown cut out of a picture of the screen with a tag for where its content would come from in their app, drawn in their theme when they keep their own), draws their own page before and after, and writes code only after they have seen it and said yes. The scripts keep the order and the state so the person or agent following it only runs a printed command | let a person say "I only like this frame, and not its colour" and get exactly that. See `adopt_design/SKILL.md` and `adopt_design/RESEARCH.md` |
| `navigation.json` | How the screens are reached from each other: the menu groups and items, each move and what it leads to. `docs/NAVIGATION_MAP.md` is the same in words; `tools/gui_checks/check_navigation.py` checks it | build a screen that sits in the right place in the menu |
| `reference_viewer/` | A plain page that shows a dataset and passes every check in `tools/gui_checks/` | see how a screen bound to a dataset is built, and as the proof that the checks can pass |

The checks are in [`tools/gui_checks/`](../tools/gui_checks/) and [`docs/GUI_TEST_HOOKS.md`](../docs/GUI_TEST_HOOKS.md) says what each one means. The field-by-field map of what each part of a
screen shows is [`docs/SCREEN_DATA_MAP.md`](../docs/SCREEN_DATA_MAP.md).

## What this does not do

The adoption skill (`adopt_design/`) has been run end to end only by the person who wrote it, on a made-up page, in Chromium. No agent, large or small, has followed it; its values read from a page are
heuristics (the ones that are guesses are marked and asked about); its pictures are drawings of a decision, not the code; the screens drawn in a person's theme re-colour only what has exactly our value for a role (colours that mean something, off-ladder sizes, hover and focus states and gradients stay as ours; the notes under each picture say what was left); and fonts that are not installed show a stand-in.


It does not decide what the product should look like: the tokens are the prototype's values, written down, and nobody has judged them with users. The scripts read what one
browser drew at one width and what a picture's pixels say; they cannot see a state they cannot reach or a gradient, and the colour matching is arithmetic, not taste. The
prototype's page is deliberately left alone: its inline colours and typed-in numbers are why copying it fails.
