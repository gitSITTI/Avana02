# What was read to design the adoption kit, and what that does and does not show

Written 21 October 2026, by the agent that built the kit. The question: *what is needed to take a page or an app, take apart its components, theme and palette, compare it with
our design, and let a person choose piece by piece, with pictures, what to bring across?* This page says what was read, what was taken from it, what was not used, and what was
not read. It is not a survey of the field: seven searches and eleven page requests (one was refused and one came back cut short; both are listed below).

## Read, and used

| What | What it says (as read) | What the kit took from it |
|---|---|---|
| [Design Tokens Format Module 2025.10](https://www.designtokens.org/TR/drafts/format) (the first 100,000 of 103,202 characters were read; the page is a Community Group *draft*, and says the latest published version is 2025.10) | `dimension` is an object `{value, unit}` with `px` or `rem` (a plain string is not valid); `fontFamily` is a string or a list; `shadow` is an object (or list of objects) with `color`, `offsetX`, `offsetY`, `blur`, `spread`, optional `inset`; media type `application/design-tokens+json`, file names `.tokens` or `.tokens.json` | `adopted.tokens.json` is written in this shape |
| [Design Tokens Color Module 2025.10](https://www.designtokens.org/tr/drafts/color/) | a colour's `$value` is an object: `colorSpace` (e.g. `srgb`), `components` (0 to 1 for `srgb`), optional `alpha`, optional 6-digit `hex`; a bare hex string is not the value | colours are written as `{colorSpace: srgb, components, alpha (when not 1), hex}` |
| [Dembrandt: "extract any website's design system"](https://dev.to/thevangelist/i-built-dembrandt-extract-any-websites-design-system-in-seconds-open-source-2n6d) (an article by the tool's author) | an open-source command-line tool: "uses Playwright to render a live site ... analyzes computed DOM styles and CSS variables, and distills real usage patterns into confidence-scored design tokens"; lists colours, typography, spacing, borders, logo; `--dtcg` exports the token standard; the author says it "won't replace a proper brand guide" and that results depend on flags for heavy or bot-protected sites | Confirms the approach (render in a real browser, read computed styles, say how sure each value is). This kit does the same reading itself (`design/ui_from_image/scripts/target_tokens.py`, written before this research) and adds what the article does not mention: roles shared with our design, a menu and component index, and the choosing |
| [Chrome DevTools: CSS Overview](https://developer.chrome.com/docs/devtools/css-overview) | a panel that reports colours (by type), fonts (grouped by size, weight and line height), unused declarations and media queries; the page is dated 2021 and calls it a preview in Chrome 96 | The index covers the same ground in a file instead of a panel (colours with what each is used for, fonts, breakpoints). It was not used: DevTools needs a person at the panel |
| [shadcn/ui theming](https://ds.shadcn.com/docs/concepts/theming) (the page that came back is the design-system variant of the docs) | variables come in pairs: `background`/`foreground`, `card`/`card-foreground`, `primary`/`primary-foreground`, `muted`, `accent`, `destructive`, plus `border`, `input`, `ring`, `radius` | The idea that a design is a short list of named roles, with the text colour paired to the surface it sits on, is the idea behind `roles.json`. The kit's 21 roles are its own list (they include a hover and a selected background, a quiet text colour and a control height that the page above does not list) |
| [LongFuncEval](https://arxiv.org/pdf/2505.10570) (abstract and tested-model list) | function calling gets worse as the tool list, the tool replies and the conversation grow: drops of 7 % to 85 %, 7 % to 91 % and 13 % to 40 % are reported; the models tested include four 8-billion-parameter open ones | The reason the scripts, not the model, hold the order, the state and the pictures, and print one question at a time. It supports the *premise* (long conversations hurt smaller models). It does **not** show that this kit works with them |

## Read, and not used

| What | Why not |
|---|---|
| [development-toolbox-web-style-extractor](https://github.com/development-toolbox/development-toolbox-web-style-extractor) README: a Python script that drives headless Chrome through Selenium and writes JSON, a Tailwind config, tokens or an HTML report; MIT licence; says some sites block automated requests and that it falls back to basic CSS extraction | It reads a site into files and stops there. It was not installed or run, so nothing is claimed about how well it works |
| [Playwright aria snapshots](https://playwright.dev/python/docs/aria-snapshots): a YAML of the accessibility tree (role, name, states) meant for structure tests; the docs call it "not ideal for highly dynamic content" | The menus are read by `tools/gui_checks/site_map.py`, which also keeps each item's address, its count badge and its current mark and can follow each item. The aria page, as read, does not mention addresses, so the kit does not rely on it for them. It may be a useful second view |

## Looked for, and not read

- **Dembrandt's own repository** (its licence, its flags, its source): the page was not fetched (the request for permission was not answered). Only the author's article was read, so no claim is made about its licence or its quality, and it was not installed or run. **The kit does not depend on it.**
- **Material Design's colour roles**: searched; the one reference page that came back was longer than the reader's limit and was not read as far as the role list. Nothing is claimed from it.
- The last 3,202 characters of the token format page (they were cut off).

## What this research does not establish

- That the roles are the right short list. They are a guess at the smallest list that lets a person say "keep my colours, take your corners". The `guesses` question and `set` exist because the reading is a heuristic (for example, which button is "the main one" when a page has several).
- That the result is accessible. Only six colour pairs are checked for contrast (`roles.py`, `PAIRS`), and a part drawn in a colour nobody listed is not.
- That the pictures match what a browser will draw once the code is in. They are drawings of the decision (see `SKILL.md`).
- That an agent, large or small, can follow the skill. None has.
- Other tools that do this (browser extensions, paid services, design-tool plug-ins) were not surveyed beyond the search results above, so "nothing else does the choosing" is **not** claimed.

## What it suggests for later

- A *bridge* that writes the result under the person's own variable names when they use a known convention (the shadcn names above are one), instead of only under ours.
- A second reading of the person's page through the accessibility tree, to cross-check the menu.
- A check of every pair of colours a chosen part draws, not just six.
