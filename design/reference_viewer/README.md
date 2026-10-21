# Reference viewer

A small, plain page (HTML, CSS, JavaScript, no build step, no libraries) that shows one canonical dataset, or several together. It exists for two reasons.

1. **It is a proof that the checks can pass.** `tools/gui_checks/probe.py` checks a screen against the fourteen test datasets. A probe nobody has seen pass proves
   little, so this page passes every check, and `tools/test_gui_checks_browser.py` shows the probe failing when the page is broken on purpose.
2. **It is a working example of a screen bound to data.** It reads only the dataset it is given, shows every value as text, windows the list, refuses a damaged
   dataset, says what the source did not provide, and uses only the design tokens. Read `viewer.js` to see how each is done; the comment at its top lists the rules.

It is **not** the design. It is deliberately plain: it has no sketch, no hero page, no side-by-side comparison. The look the product should have is in
`prototype/` (to read) and `design/tokens.json` (to build from). A screen built for users keeps the behaviour here and replaces the look.

## Run it

```
reqin make-datasets /tmp/ds --size 5000
python3 tools/gui_checks/serve.py --datasets /tmp/ds
```

then open `http://127.0.0.1:8000/?dataset=datasets/F02_everything`. Give `dataset` twice to open two together:
`?dataset=datasets/F11_two_sources/a&dataset=datasets/F11_two_sources/b`. Or open the page and use the two buttons to choose files or a folder.

The page links `tokens.css`. The server supplies it, and the fonts, from `design/` when this folder has no copy. To open `index.html` without the server, install
a copy next to it (`python3 design/make_tokens.py --install design/reference_viewer`; `.gitignore` keeps those files out of the repository). Fetching a dataset
needs the server; choosing files does not.

## Check it

```
python3 tools/gui_checks/hardcode_scan.py design/reference_viewer
python3 tools/gui_checks/probe.py --datasets /tmp/ds
```

`docs/GUI_TEST_HOOKS.md` lists the `data-testid` marks the probe reads and what each check means. To build a different screen that the same probe can check, carry
the same marks.

## What it does not do

It does not edit anything, compare datasets, draw the V, or show a results page. It has been run in one browser (Chromium) at four widths on made-up data.
Nobody has used it with a real export. Marking a record verified is kept in the page only and is lost on reload.
