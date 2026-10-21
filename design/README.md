# Design kit

What an agent or a person needs to build a screen that looks like the product, shows the user's data, and can be checked. Nothing here is a screen the product ships:
the screens to ship are built from this with the steps in [`docs/agent_prompts/build_the_gui.md`](../docs/agent_prompts/build_the_gui.md).

| Path | What it is | Use it to |
|---|---|---|
| `tokens.json` | The design language as data: colours (with the names the prototype used), the three type families and sizes, spacing, radii, targets, shadows | change the look in one place. It is the source of truth |
| `tokens.css` | Generated from `tokens.json` by `make_tokens.py`: custom properties, the nine font faces, and a few classes (`.rq-card`, `.rq-button`, `.rq-primary`, `.rq-input`, `.rq-statement`, `.rq-id`, `.rq-caption`) | link it from a screen and write `var(--accent)`. **Never edit it by hand** (`python3 design/make_tokens.py --check` fails when it is stale) |
| `make_tokens.py` | Writes `tokens.css`; `--install DIR` copies it and the font files into another app; `--coverage` says how many of the prototype's literal colours the tokens name | keep the CSS true to the JSON; carry the look into a different app |
| `ui_from_image/` | A procedure and small scripts for going from a picture of a screen to components in a site's own look: cut the picture into blocks, take its palette, read the target page's real colours, fonts and component styles in a browser, map one onto the other, write a checked component spec. Start at its `SKILL.md` | restyle or rebuild a screen from a screenshot without copying the page it came from |
| `reference_viewer/` | A plain page that shows a dataset and passes every check in `tools/gui_checks/` | see how a screen bound to a dataset is built, and as the proof that the checks can pass |

The checks are in [`tools/gui_checks/`](../tools/gui_checks/) and [`docs/GUI_TEST_HOOKS.md`](../docs/GUI_TEST_HOOKS.md) says what each one means. The field-by-field map of what each part of a
screen shows is [`docs/SCREEN_DATA_MAP.md`](../docs/SCREEN_DATA_MAP.md).

## What this does not do

It does not decide what the product should look like: the tokens are the prototype's values, written down, and nobody has judged them with users. The scripts read what one
browser drew at one width and what a picture's pixels say; they cannot see a state they cannot reach or a gradient, and the colour matching is arithmetic, not taste. The
prototype's page is deliberately left alone: its inline colours and typed-in numbers are why copying it fails.
