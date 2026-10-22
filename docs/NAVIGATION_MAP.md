# Navigation map: screens, menus, moves and where each screen's content comes from

<!-- Generated from design/navigation.json by `python3 tools/gui_checks/check_navigation.py --write-doc docs/NAVIGATION_MAP.md`. Do not edit by hand: a test fails when this page and the JSON disagree. -->

**What this page is for.** A picture of a screen shows the words in a menu and not where they lead, nor which screen a button on another screen opens, nor what it carries along. An agent rebuilding the product from pictures gets the menu's words and no wiring. This page is the wiring, written down once: [`design/navigation.json`](../design/navigation.json) is the same facts for a program, and `tools/gui_checks/check_navigation.py` checks it. Where a screen's content comes from is in [`SCREEN_DATA_MAP.md`](SCREEN_DATA_MAP.md); how things look is in `design/tokens.css`.

**Where it came from.** One agent read the prototype's source (`prototype/parts/`) and wrote it down. The check compares the screens, titles, menu groups, their order and labels, the start screen, the page titles, and every jump a handler in the source can make, with this map, so a screen or a jump added to the prototype and not to the map fails. It does not know which screen a handler is shown on (the *From* column was read by a person) or whether the words in *Control* and *Carries* are right. Nobody has built a menu from this page yet. **Everything is made up:** the sample project is invented.

## 1. Screens

A *workspace* screen has the shell (side bar and top bar); an *entry* screen does not. *Moves from the start* counts the fewest moves from `open`. *Content* is the sections of the data map that say where each part of the screen comes from, with their status there.

| Screen | Title it shows | Kind | In the menu | Content (data map) | Status there | Reached from | Moves from the start |
|---|---|---|---|---|---|---|---|
| `open` | Open a requirements project | entry | no | 4.1 Open | dataset only, plus an importer the GUI cannot be | the start | 0 |
| `import` | Check statements found in a document / Map fields and choose scope | entry | no | 4.2 Import: check what the app found (statements found inside a document), 4.3 Import: check how your fields map, choose scope | dataset only, partly without a producer | `open`, `home` | 1 |
| `home` | Home | workspace | (top) | 4.5 Home | needs comparison output, needs saved work | `import`, `home`; the menu | 2 |
| `review` | Review queue | workspace | (top) | 4.7 Review (the queue and one cluster) | needs comparison output, needs saved work, partly without a producer | `any workspace screen`, `home`, `overview`, `explorer`, `vee`, `results`, `audit`, `ai`, `export`; the menu | 3 |
| `explorer` | All requirements | workspace | (top) | 4.9 All requirements | needs comparison output, needs saved work | `overview`, `vee`, `results`, `audit`; the menu | 3 |
| `overview` | Overview | workspace | Progress and evidence | 4.6 Overview | partly without a producer | `home`; the menu | 3 |
| `vee` | The V | workspace | Progress and evidence | 4.10 The V | dataset only, plus saved work for "after your decisions" | `any workspace screen`; the menu | 3 |
| `results` | Results and grade | workspace | Progress and evidence | 4.11 Results and grade | partly without a producer | `overview`; the menu | 3 |
| `methods` | Methods and metrics | workspace | Progress and evidence | 4.13 Methods and metrics | partly without a producer | `results`, `gold`; the menu | 3 |
| `gold` | Label pairs | workspace | Progress and evidence | 4.12 Label pairs (the gold set) | needs saved work | `methods`; the menu | 3 |
| `audit` | Decisions and audit | workspace | Progress and evidence | 4.14 Decisions and audit | needs saved work | `any workspace screen`, `home`; the menu | 3 |
| `policy` | Sign-off policy | workspace | Policy and output | 4.15 Sign-off policy | needs saved work | no listed move; the menu | 3 |
| `ai` | AI use | workspace | Policy and output | 4.16 AI use | needs saved work, partly without a producer | `home`, `review`; the menu | 3 |
| `export` | Export to documents | workspace | Policy and output | 4.17 Export | needs comparison output, needs saved work | `vee`, `results`; the menu | 3 |

- `open`: The first screen. No side bar and no top bar: they belong to the workspace.
- `import`: A step bar runs along the top: for a document, 1 Source, 2 Verify statements, 3 Map fields / choose scope / prepare, 4 Workspace; for any other source, 1 Source, 2 Map fields / choose scope / prepare, 3 Workspace. No side bar.
- `review`: The queue and one cluster at a time. 'Line up the words' (4.8) is a sheet opened from a cluster, listed under sheets.

## 2. The side bar (workspace screens only)

Accessible name: **Main**. Layout: a column 256px wide down the left, kept at the top of the window, scrolling by itself when it is taller than the window.
At most 900px wide: a full-width wrapping row above the content, not kept at the top; the group headings are hidden and every item is shown whether its group was folded or not; the project card is hidden. *(read from the prototype's styles in prototype/parts/m/00_head.html; not run in a browser for this map.)*

A build that follows this map must show every item at that width (`nav.narrow_shows_every_item` in `docs/GUI_TEST_HOOKS.md`).

- **(no heading)** (does not fold)
  - Home → `home` (icon `home`)
  - Review queue → `review` (icon `queue`) with a count: clusters waiting for the person signed in (the same number as the main button on Home). From `CMP.counts.clusters`, `WORK`. When nothing produces it: show no count, not 0
  - All requirements → `explorer` (icon `table`)
- **Progress and evidence** (folds; starts open)
  - Overview → `overview` (icon `chart`)
  - The V → `vee` (icon `vee`)
  - Results and grade → `results` (icon `medal`)
  - Methods and metrics → `methods` (icon `flask`)
  - Label pairs → `gold` (icon `tag`)
  - Decisions and audit → `audit` (icon `clock`)
- **Policy and output** (folds; starts open)
  - Sign-off policy → `policy` (icon `shield`)
  - AI use → `ai` (icon `spark`)
  - Export to documents → `export` (icon `export`)
- **Foot**
  - Glossary and help (icon `book`): opens the glossary overlay
  - Close project (icon `exit`): goes to `open`; also closes the assistant

Current item: The item whose screen is showing carries aria-current=page. Nothing is current on a screen that has no item (none in this product: every workspace screen has one).

Group headings are buttons that fold their items (aria-expanded). The count is on one item only.

Only in the prototype, not part of the product: the project card above the menu; the 'Signed in as' card; 'Demo only' lens preview; 'Demo only' switch person; 'Demo only' simulate a teammate.
These sit inside the same `nav` element as the menu, so a program reading the menu sees them too. `site_map.py` leaves out any item whose label matches one of these patterns: `^(Sam|Priya|Jordan|Casey|Morgan|Lee)[A-Z a-z]`, `^A teammate `, `^The source drifts`, `^My own lens$`, `^(Systems|Process|UX|New)[A-Za-z ]* lens$`.

## 3. The top bar and the frame (workspace screens only)

- Breadcrumb: the project name / the title of the screen showing. The project name is not in any dataset: WORK or STATIC (docs/SCREEN_DATA_MAP.md 4.4).
- A chip for the scope, from `DS.fields.allocation`.
- A chip for the baseline, from `DS.fields.baseline`.
- Search ("Search requirements") over `DS.uid`, `DS.text`. Once text is entered it goes to `review` carrying the text as the search, the All tab, every filter cleared, page one; emptied, it stays on the screen showing and clears the search.
- Button "The V": goes to `vee`.
- Button "Glossary and help": opens the glossary overlay.
- Button "Decisions and audit": goes to `audit`.
- Button "Ask the assistant": shows and hides the assistant overlay.
- Only in the prototype: the avatars of teammates on the project.
- The draft bar under the top bar, on every workspace screen: words only, not data (4.4).
- A skip link "Skip to the main content" is the first thing a keyboard reaches; it moves focus to the content area.
- Title of the page: `<screen title> · Requirements Consolidator`. When the screen changes, a polite live region says 'Now showing: <screen title>', and the document title changes with it.

## 4. Moves between screens

Every control on one screen that opens another, apart from the side bar and the top bar above. *Carries* is what is set on arrival. The *Evidence* column names the piece of the prototype's code the move was read from.

| From | To | Control | Carries | Evidence |
|---|---|---|---|---|
| any workspace screen | `open` | 'Close project' at the foot of the side bar | nothing; the assistant is closed | `c1.js valsShell` |
| any workspace screen | `review` | the top bar's search, once text is entered | the text as the search; the All tab; filters cleared | `c1.js valsShell` |
| any workspace screen | `review` | the button that uses a draft the assistant wrote | the draft as the person's own wording in the Resolve panel of the cluster the assistant is about; nothing is recorded until the person records the decision | `c3.js valsAssist` |
| any workspace screen | `vee` | the small V in the top bar; also 'Open the V' on Home and on Results | nothing | `c3.js valsVeeStrip` |
| any workspace screen | `audit` | the clock button in the top bar | nothing | `c1.js valsShell` |
| `open`, `home` | `import` | choosing a way in: a source card, a recent import, the sample, a ReqIF file, a dropped file, or one of the three 'Bring in requirements' cards on Home | the chosen source type; the import starts at its first step | `c1.js goImport` |
| `import` | `open` | the first step in the step bar, or 'Back' on the map step when the source is not a document | nothing | `c1.js valsImport` |
| `import` | `open` | 'Back' on the verify step | nothing | `c1.js valsVerify` |
| `import` | `home` | 'Confirm mapping and import' | the scope chosen: everything, or one allocation as a pilot | `c1.js valsImport` |
| `home` | `open` | 'See all six sources' | nothing | `c1.js valsHome` |
| `home` | `open` | the 'Your work is kept' panel: 'Start over' | everything kept in this browser is removed | `c7.js keepStartOver` |
| `home` | `home` | the 'Your work is kept' panel: show the work another tab saved | the saved work replaces what was showing; a message says so | `c7.js keepTakeOther` |
| `home` | `home` | the 'Your work is kept' panel: load the saved work that was read in | the saved work replaces what was showing; a message says so | `c7.js keepApply` |
| `home` | `review` | the main button ('Review the next cluster' / 'Look at the next cluster') | the first cluster waiting for this person, else the first undecided, else the first; the tab that lists this person's clusters | `c1.js startReviewFor` |
| `home` | `review` | a bar in 'Open clusters by allocation'; a row in 'Latest activity' that names a cluster | that allocation as a filter with status Open, or that cluster selected; the All tab | `c1.js valsHome` |
| `home` | `overview` | 'Open the overview' | nothing | `c1.js valsHome` |
| `home` | `audit` | 'Open the log' | nothing | `c1.js valsHome` |
| `home` | `ai` | 'AI use' in the security band | nothing | `c1.js valsHome` |
| `review` | `ai` | 'Open AI use' in the banner shown when AI is held back for a cluster | nothing | `c2.js valsDetail` |
| `explorer` | `review` | 'Open its cluster' on a selected requirement | that cluster selected; the All tab | `c3.js valsExplorer` |
| `explorer` | `review` | 'Open CLUSTER' beside 'Take it out of CLUSTER' in the single-requirement panel | that cluster selected; the All tab | `c5.js valsSingle` |
| `overview` | `review` | 'Start with the safest cluster' and 'Open CL-050' | the first waiting cluster, or a named one; the prototype types the id CL-050 into its source: a screen built from a dataset must pick a real cluster (4.6) | `c1.js valsOverview` |
| `overview` | `explorer` | 'See all requirements on a map' | nothing | `c1.js valsOverview` |
| `overview` | `results` | 'See results and grade' | nothing | `c1.js valsOverview` |
| `vee` | `review` | the button that opens the undecided clusters of a level of the V | that level as a filter; status Undecided; the All tab | `c3.js valsVee` |
| `vee` | `explorer` | 'See the gaps' on a level | that level as a filter and the gaps-only switch on | `c3.js valsVee` |
| `vee` | `export` | 'Open Export' | nothing | `c3.js valsVee` |
| `results` | `review` | a count, a cluster or a requirement named in the grade panels, for example what would raise the grade | a filter, or that cluster selected; the All tab | `c3.js valsResults` |
| `results` | `explorer` | a requirement named in the grade panels | that requirement selected; filters cleared | `c3.js valsResults` |
| `results` | `methods` | 'See what the AI adds' | nothing | `c3.js valsResults` |
| `results` | `export` | 'Go to export' | nothing | `c3.js valsResults` |
| `methods` | `gold` | 'Label pairs' | nothing | `c4.js valsGoldPanel` |
| `gold` | `methods` | 'See the measured scores' | nothing | `c4.js valsGold` |
| `audit` | `review` | 'Open' on an event whose target is a cluster | that cluster selected; the All tab | `c3.js valsAudit` |
| `audit` | `explorer` | 'Open' on an event whose target is a requirement | that requirement selected; filters cleared | `c3.js valsAudit` |
| `ai` | `review` | 'Open CLUSTER in the review queue' on a group held back from AI | that cluster selected; the All tab | `c8.js valsAi` |
| `export` | `review` | a cluster named in the list of what needs attention before export | that cluster selected; the All tab | `c3.js valsExport` |

Not a move: `c7.js keepProbe`: a self-check that draws every screen to prove saved work can be shown; no person triggers it as a move.

## 5. Sheets and overlays

- **Line up the words** (sheet, `align`), opened from `review`. A sheet over a cluster, not a screen: the screen behind it and the side bar stay. Closing it returns focus to the button that opened it. Content: 4.8 Line up the words.
- **Glossary and help** (overlay, `glossary`), opened by the side bar's 'Glossary and help', the top bar's 'Glossary and help'; closed by its own 'Close glossary' button; shown as a panel at the top of the content area, above the screen that was showing; the screen stays where it was. Content: 4.4 Workspace shell (side bar, top bar, DRAFT bar, help).
- **The assistant** (overlay, `assistant`), opened by the top bar's 'Ask the assistant'; closed by the same top-bar button (now labelled 'Hide the assistant'), the 'Close the assistant' button inside it, or 'Close project'; shown as a panel beside the content, named 'Assistant' for a screen reader, on any workspace screen. Content: 4.18 Assistant drawer.

## 6. Notes

- A screen's name (the menu label, the breadcrumb, the document title) is not always the heading inside the screen. Read from the running prototype's sample project: nine screens repeat their name as the heading; Home's heading is a sentence with a count taken from the data; the Review queue's is the name of the cluster showing; The V's is 'The engineering V'. A rebuild puts the name in the menu, the breadcrumb and the title, and lets the heading be what the screen needs. Do not take a screen's name from its heading in a picture.
- A screen's content is described by its data_map sections in docs/SCREEN_DATA_MAP.md. A menu item's words are STATIC; only the count on 'Review queue' is data.
- 'from' was read from the code by one agent: the checks confirm which screens each piece of code can lead to, not which screen that code is shown on.
- In the prototype a menu item changes only which screen shows. A cluster selected or a filter set earlier is still set when you come back to that screen (read from the code, not run). Say in your report if you keep or clear that state differently.

## 7. What this page does not say

- Nobody has built a menu or a screen from it. The first agent to do so should say which line did not work as written.
- It describes the prototype's navigation. What the product's navigation *should* be (for example addresses that survive a reload, the back button, a menu on a phone) is not decided here; where the prototype does not say, this page does not either.
- It was read from the source and the styles; the side bar's narrow layout was not run in a browser for this page. `tools/gui_checks/site_map.py` reads the same facts from a running page, and `docs/GUI_TEST_HOOKS.md` says how a screen exposes them to the probe.
- Roles and lenses: what each person sees in the menu or on a screen (a lead, an observer) is not mapped here. The prototype shows the same menu to every person.
