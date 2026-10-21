# Accessibility

What the prototype was checked for, how to run the checks, and what has **not** been checked. The target is WCAG 2.2 level AA. The checks are automated, so they find a
part of the problems and not all of them: nobody has used this page with a screen reader, a switch device or a voice control program, and nobody with a disability has
tested it. Read "What has not been checked" before you tell anyone it is accessible.

## What is checked, on every run

`prototype/b20.py` runs at 1440, 900 and 390 px wide (`python3 b20.py 390`, or all of them with `make proto-test`). It scans every page and the states that open more of
a page, with two tools: axe-core 4.13.0 (pinned in `prototype/vendor/package.json`) and checks written for this page (`prototype/a11y_page.js`, `prototype/chart_colours.py`).

| Check | What it does | Where it comes from |
|---|---|---|
| Automated scan | axe-core with the rule sets `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa` and `best-practice` on the entry page, the import page, each of the 12 workspace pages, a cluster open for review, the assistant open, one requirement open, Methods as a table, the AI data sheet form, Label pairs and the glossary. No violations allowed; anything axe cannot decide is printed as a note. The rule sets include the WCAG 2.2 minimum target size (24 px); it was shown to flag a 10 px button | axe-core |
| Contrast as drawn | Measures the colour of every piece of text against what is behind it in the browser (colour set by a rule, a variable or a style attribute, translucent layers laid over each other, text in SVG over the shape behind it): 4.5 to 1, or 3 to 1 for large text. A page the check cannot measure (a picture or gradient behind text) fails the check rather than passing silently | WCAG 1.4.3 |
| Edges of fields | The edge or fill of every text box, menu and button-like control stands out from what is behind it by 3 to 1 | WCAG 1.4.11 |
| Mouse-only things | Nothing that reacts to a click (a pointer cursor) is out of the keyboard's reach, unless it is a picture whose content is also in a list | WCAG 2.1.1 |
| Invisible Tab stops | Nothing the Tab key can land on is without size | WCAG 2.4.7, 2.4.11 |
| Where you are | Every page has its own title in the tab, one main area, one top heading, a named menu with the current page marked, a "Skip to the main content" link, and a polite announcement ("Now showing: ...") when the page changes | WCAG 2.4.1, 2.4.2, 4.1.3 |
| Keyboard | The first Tab stop is the skip link; it is on screen and moves focus into the main area. Walking the page with Tab reaches every control, never sticks, shows a focus ring on every stop, scrolls it into view and does not leave it behind the sticky top bar. The window that lines up the wordings keeps Tab inside, closes on Escape and gives focus back | WCAG 2.1.2, 2.4.3, 2.4.7, 2.4.11 |
| Pictures | Every SVG picture in the V, Overview, Methods and Results is hidden from a screen reader or has a name | WCAG 1.1.1 |
| Chart colours | The colours in the key of the status map (All requirements), of the with-and-without-AI chart (Methods), of the four lenses (the person's avatar in the side bar, for each lens), of the two legs of the V and of the AI gate's bars (open and held) are far enough apart for someone with red-green colour blindness (OKLab distance of 6 or more, 8 is the target, using the Machado 2009 simulation) and for ordinary vision (15 or more), and each mark stands out from the page by 3 to 1. In the status map two of the five marks also differ by pattern (hatched, hollow); the V's two legs differ by shape (circle, square); every lens and every bar has its name beside it. White initials on each lens colour read at 4.5 to 1 | WCAG 1.4.1, 1.4.3, 1.4.11 |
| Reduced motion | With "reduce motion" asked for, nothing repeats an animation and no control has a transition | WCAG 2.3.3 (level AAA, checked anyway), 2.2.2 |
| Reflow | At 320 px wide (a 1280 px page at 400 percent zoom) no page needs sideways scrolling | WCAG 1.4.10 |

Each of these was shown to be able to fail; see "Breaking it on purpose" below. Not every line in the table has been broken that way (the pictures check, the dialog,
reduced motion and the announcement of a page change, for example, have not), and the list below says which have.

## What was changed because of them

- A skip link, landmarks, a heading and a title on every page, and a polite announcement when the page changes.
- Scrolling lists and tables can be reached with the keyboard.
- The edges of text boxes and menus are darker (3 to 1 against what is behind them).
- A sticky top bar no longer covers the control that has focus (`scroll-padding-top`).
- The explorer rows reflow at 320 px.
- The status map is a picture for the mouse; it is hidden from assistive technology, and the list under it is the way in for the keyboard and a screen reader.
- The "Without AI" mark in the Methods chart changed from slate to blue, because slate and the plum "With AI" mark could not be told apart by someone with red-green colour blindness. The status map's "needs attention" orange and "open" blue were adjusted for the same check.
- The four lens colours changed (blue `#125AB2`, purple `#660E8C`, orange `#B25D12`, green `#296652`): the old purple and blue, and the old orange and green, were too close for red-green colour blindness. Every pair is now 8.2 or more apart (the target is 8), and 15 or more for ordinary vision.
- The AI gate's "open" and "held" bars changed (teal `#0A665A` and orange `#B25D12`): the old green and amber were 4.0 apart for red-green colour blindness, and the new check named them the first time it ran.

## Breaking it on purpose

A check that cannot fail proves nothing. `tools/mutation/a11y.py` makes one accessibility mistake at a time in a throwaway copy of the page, runs `b20.py` at 1440 px on
the copy, and requires it to fail **on the check made for that mistake** (not just to fail somewhere). It was run on the final page: all nine were caught by the intended
check, and the real page was never touched.

| The mistake | What caught it |
|---|---|
| Text boxes and menus with a faint edge (a 1.3 to 1 edge instead of 3 to 1) | "fields": the edge or fill of every field stands out 3 to 1 (it named the search box on the review queue first) |
| The tab title never changes | "title": every page has its own title |
| The skip link removed | "landmarks" on every page, and "the first Tab stop is the skip link" |
| The focus ring removed | "every Tab stop has a visible focus ring", on the first stop onward |
| Secondary text lightened (2.15 to 1 on the page background) | "contrast": every text meets 4.5 to 1 (it named the word "Project" in the side bar first, at 2.15 to 1) |
| An icon button without a name | axe `button-name` (critical) |
| A control that reacts to a click but cannot be reached with the keyboard | "nothing reacts to a click that the keyboard cannot reach" |
| A page that needs sideways scrolling at 320 px | "reflow", on every page |
| The "Without AI" chart mark and the "With AI" mark made to look alike for red-green colour blindness | "chart colours: with and without AI" |
| Two lens colours made to look alike; a lens colour too pale for white initials | "chart colours: the four lenses ..." and "white initials" |
| The AI gate's open and held bars given the old, too-similar colours | "chart colours: the AI gate bars ..." |

Run it with `python3 tools/mutation/a11y.py` (about a minute per mistake; it needs the same libraries as the browser tests). `--list` shows the names, and `--patterns` checks
in under a second that each mistake still matches the code; `tools/test_mutation_scripts.py` runs that in CI so the script cannot quietly stop testing anything.

**The CI jobs fail when a browser test fails.** GitHub and GitLab run `python run_browser_tests.py`, which exits 1 when any run fails and prints everything that run said.
`tools/test_browser_runner.py` shows this against stand-in tests (a failing run fails the job and names the file and the width; a missing page or library is refused, not
passed; a new `bNN.py` that is not in the runner's list is a failing test). Neither CI file has run on its platform yet.

**What has not been broken on purpose**: the checks for the pictures (hidden from a screen reader or named), reduced motion, the announcement of a page change, the dialog (Tab
stays inside, Escape closes), and a background the contrast check cannot measure. They run on every build and pass, but nobody has shown that they fail.

## What has not been checked

- **No screen reader, switch device or voice control** has been used with the page. Names and roles are checked by a program; whether the page *makes sense* when read aloud is not.
- **No people with disabilities** have used it, and nobody has run a usability study.
- **Chromium only.** Not Firefox, Safari or a phone's own browser. The 390 px layout is checked at that width in desktop Chromium, not on a phone.
- **Colour pairs that are still not run through the chart-colour check:** the result and progress bars, the chips that name a decision's state or a disposition, and the grade letter's colour. Each is paired with a word or a number, and none depends on colour alone, but nobody has measured them. The design boards (Excalidraw) still draw the four lenses in their older pastel colours; they are drawings, not the page.
- **Text spacing, 200 percent text-only zoom, high-contrast and forced-colours modes, dark mode, and other languages** have not been tested.
- **Content in the files the app exports** (the Word, ReqIF, JSON and CSV files) is not checked.
- **Automated tools find a part of the problems.** A page with no axe violations can still be hard to use.

## Running the checks

```bash
cd prototype/vendor && npm ci                  # React, Babel and axe-core, pinned
cd .. && python3 b20.py 1440                   # then 900 and 390
python3 chart_colours.py '#4F8FE6,#1C5CAB,#1B6B3A,#C47A00'   # any palette, on its own
```

To add a page, add it to `PAGES` in `b20.py`. To add a chart, give each mark in its key `data-chart-mark="<chart name>"` and list it in the "chart colours" loop in `b20.py`.
