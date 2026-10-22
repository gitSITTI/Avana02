# Test hooks: how one probe can check any screen

A screen is bound to data when what is on it changes with the dataset and equals what the dataset says. To check that without knowing how a screen was
built, the screen marks the parts the check needs with a `data-testid` attribute. The probe (`tools/gui_checks/probe.py`) reads only these marks. Any app that
carries them, in any framework, can be checked by the same probe, and `design/reference_viewer/` is a small app that carries all of them and passes.

This page is the contract between the screen and the probe. It is not a design: where the marks go and how the screen looks are up to the screen. The data
the marks must show is defined in `reqin/GUI_CONTRACT.md` and the field-by-field map is `docs/SCREEN_DATA_MAP.md`.

## How to run the check

```
reqin make-datasets DIR --size 5000                         once: the fourteen datasets F1 to F14, and DIR/index.json
python3 tools/gui_checks/hardcode_scan.py my_app/           in a second: typed-in data, literal colours, markup injection
python3 tools/gui_checks/probe.py --app my_app/ --datasets DIR
python3 tools/gui_checks/serve.py --app my_app/ --datasets DIR      to look at it yourself at http://127.0.0.1:8000/?dataset=datasets/F02_everything
```

`--size` sets the length of the large dataset (F9). The default is 50,000, which is the real test of the windowed list and takes a minute or two to write;
5,000 is enough to see whether the list is windowed. `--only F1,F12` runs some datasets. `--json FILE` keeps the result. The exit status is 1 when any check
fails, so the same command is the merge gate.

The probe starts the app itself from a folder. `serve.py` gives the page `tokens.css` and the font files at `/tokens.css` and `/fonts/` when the app folder
has no copy of its own, and the datasets at `/datasets/`.

## What the app must do

1. **Open a dataset from the address:** `?dataset=datasets/F02_everything`. Give `dataset` more than once to open several together (F11 is two datasets).
2. **Also accept the files:** an `<input type="file" multiple>` marked `dataset-file-input` and an `<input type="file" webkitdirectory>` marked
   `dataset-folder-input`. Choosing a second dataset replaces the first completely.
3. **Say what state it is in** on `<body data-state="...">`: `idle` (nothing chosen), `loading`, `ready`, `empty` (a dataset with no requirements), `error`
   (a dataset it refused).
4. **Refuse a dataset that fails its own checks,** whole: a missing `dataset.json`, a file whose checksum no longer matches, counts that do not match the lines.
   Show what is wrong in `dataset-error` and one `dataset-problem` per problem, and show nothing from the dataset. A half-valid dataset must never look complete.
5. **Show only what is in the dataset.** Counts, chips, columns, panels and rows come from the files. A field no record has gets no column. A source with no
   links gets no trace panel, and says so.
6. **Put every value on the page as text,** never as markup (`textContent`, not `innerHTML`). A requirement that contains `<b>` is shown as those characters.
7. **Window the list.** Only the rows near the view are in the page. 50,000 requirements must not mean 50,000 elements.

## The marks

`text` means the element's text is exactly that value, with nothing added. `contains` means the value appears inside the element's text.
An element that must be hidden is hidden (`hidden`, `display: none`), not merely empty.

| Mark | On | What it holds |
|---|---|---|
| `dataset-file-input`, `dataset-folder-input` | the two file inputs | |
| `dataset-error` | a container | shown only in the `error` state |
| `dataset-problem` | one per problem | a plain-language sentence |
| `count-read`, `count-kept`, `count-rejected`, `count-filtered` | the four counts | text: the integer, from `report.json` and the file line counts |
| `count-mismatch` | a message | visible only when read is not kept + rejected + filtered |
| `warning` | one per `report.json` warning | contains the warning as written |
| `filtered-reason` | one per `filtered_out` entry | contains `reason: count` |
| `source-chip` | one per source | text: the `ref.uri` |
| `fidelity-chip` | one per fidelity | text: the fidelity as written |
| `verify-banner` | a message | visible exactly when a record has fidelity `extracted` |
| `fact` | one line per condition that holds | `data-fact` is `synthetic-ids`, `duplicate-ids` or `outside-links`, `data-value` is the number; absent when the number is 0 |
| `empty-state` | a message | visible only in the `empty` state; the `warning`s stay visible beside it |
| `list` | the scrolling element of the list | |
| `row-total` | a number | text: how many requirements the list holds now (after a filter) |
| `row` | one per requirement in the page | `data-index` (position in the list), `data-depth` (1 is top level), `data-uid`, `data-mid` |
| `row-uid`, `row-text` | in a row | text: `uid` and `text` word for word |
| `row-fidelity`, `row-source` | in a row | text: `fidelity` and `ref.uri` |
| `synthetic-badge` | in a row | present exactly when `uid_synthetic` is true |
| `verify-badge` | in a row of an extracted record | text `verify` or `verified` |
| `row-cell` and `col-head` | cells and column heads | `data-field`; a column exists only for a field some record has |
| `tree` | a cue | visible exactly when some record has a parent; `data-depth` is the deepest level |
| `filter-input` | a search box (optional) | filters by ID and wording; `row-total` follows it |
| `detail` | the panel for the selected row | opens when a row is clicked |
| `detail-uid`, `detail-text` | in the detail | start with the uid; text: the statement word for word |
| `field-value` | one per standard field the dataset has | `data-field`; contains the value, or says the source does not provide it |
| `confidence-cue` | in a `field-value` | present exactly when that field was read with Medium or Low confidence |
| `other-field-name`, `other-field-value` | pairs in the detail | every `fields` key that is not a standard field, and every `extra` key, as written |
| `show-source`, `source-location`, `source-position` | a button, then what it opens | the locator as written; for a locator like `p3:blk12`, `page 3, block 12` |
| `mark-verified`, `verified-state` | an extracted record only | toggles; the row's `verify-badge` follows |
| `no-links` | a message | visible exactly when the dataset has no links |
| `trace-panel` | the links panel | visible exactly when the dataset has links |
| `link-kind` | one per kind in the trace panel | `data-kind` as written (never renamed, never dropped), `data-count` |
| `link` | one per link: in the trace panel, and in the detail for the selected record | `data-kind`, `data-source-uid`, `data-target-uid` |
| `link-outside` | on a link with an end outside the import | the end is shown by its uid and marked |
| `links-more` | a message | when a long list stops: at most 200 are shown at once |
| `rejected-item`, `rejected-reason`, `rejected-more` | the rejected records | the reason as written; `rejected-more` says that the list stops |

Standard fields are `status`, `verification`, `owner`, `allocation`, `baseline`, `rationale`. Anything else is an other field.

## Navigation marks

Only for an app with more than one screen. An app with one screen, like `design/reference_viewer/`, carries none of these and is not blamed for it: the probe prints one
'not applicable' line. An app that has a menu carries all of them, because a menu that is only partly marked cannot be checked.

| Mark | On | What it holds |
|---|---|---|
| `nav` | the side-bar menu | a `<nav>` (or an element with `role="navigation"`) with an accessible name (`aria-label`); the only element with this mark |
| `nav-group` | one per group of items | `data-group`: the group's id from `design/navigation.json` (`top`, `progress`, `output`). Every `nav-item` is inside one |
| `nav-item` | one per menu item | `data-screen`: the id of the screen it opens; text: the label as written. A `<button>` or an `<a href>`, so the keyboard reaches it. Carries `aria-current="page"` exactly when its screen is the one showing |
| `nav-count` | in a `nav-item` that has a count | text: digits only. Left out, not shown as 0, when nothing produces the number |
| `screen` | the content of the screen showing | `data-screen`: the id of that screen. Exactly one is visible at a time. Its text is what the person reads, so it differs from screen to screen |
| `breadcrumb` | the line above the content (optional) | contains the title of the screen showing, as `design/navigation.json` gives it (the title in the menu and the breadcrumb is not always the heading on the page) |

```html
<nav data-testid="nav" aria-label="Main">
  <div data-testid="nav-group" data-group="top">
    <button data-testid="nav-item" data-screen="home" aria-current="page">Home</button>
    <button data-testid="nav-item" data-screen="review">Review queue <span data-testid="nav-count">4</span></button>
  </div>
</nav>
<div data-testid="breadcrumb">Alpha project / Home</div>
<section data-testid="screen" data-screen="home"> ... </section>
```

Where the menu lives and what it holds is `design/navigation.json` (readable form: `docs/NAVIGATION_MAP.md`). The marks say where the page exposes it. Pass the map to the probe
with `--navigation design/navigation.json` and it also compares the menu with the map. Without it the probe still checks that the menu works.

## What the probe checks, and what to fix when it fails

Every dataset F1 to F14 is opened and the screen is compared with its files. The probe reads the files itself, so a screen cannot pass by agreeing with a
summary.

| Check | It fails when |
|---|---|
| `loads` | the state never becomes `ready` or `empty`, within 30 seconds |
| `console.clean` | the page logs an error, throws, or asks for a file that is not there |
| `oracle.agrees_with_index` | the probe's reading of the files and `index.json` disagree (a bug in the probe or a stale `index.json`, not in the screen) |
| `counts.read`, `.kept`, `.rejected`, `.filtered` | a count is not what the files say. Typed-in numbers fail here |
| `counts.reconcile` | read is not kept + rejected + filtered and the screen does not say so |
| `warnings.verbatim`, `filtered.reasons` | a warning or a reason is missing, reworded, or merged |
| `sources.chips`, `fidelity.chips` | a chip is missing or invented |
| `banner.verify` | the extracted-records banner is missing, or shows when nothing was extracted |
| `facts.synthetic-ids`, `.duplicate-ids`, `.outside-links` | the screen does not say how many IDs were invented, repeated, or point outside the import |
| `empty.state`, `empty.state_hidden`, `empty.warning_still_shown` | an empty dataset shows a blank list, or a non-empty one shows the empty message |
| `list.total` | the list says a different number of requirements |
| `list.first_rows`, `list.last_rows`, `list.middle_rows` | rows are not the records in the files, word for word. A screen that shows the first page of a typed-in list fails at the last rows |
| `list.windowed` | a list of more than 300 has more than 150 rows in the page |
| `list.columns` | a column exists for a field no record has |
| `list.tree_cue`, `list.tree_depth`, `rows.depth` | the hierarchy cue is missing, shown without a hierarchy, or at the wrong depth |
| `rows.synthetic_badge`, `rows.source_and_fidelity` | an invented ID looks like a source ID; the source or the fidelity is wrong on a row |
| `detail.uid_and_text` | the detail shows another requirement, or an edited statement |
| `detail.fields`, `detail.confidence_cue` | a field value is wrong, a missing field is filled in, or a low-confidence reading carries no cue |
| `detail.other_fields` | an `extra` key or a non-standard `fields` key is dropped, truncated or reworded |
| `detail.links` | the links of the selected record are not all in the detail |
| `detail.show_in_source`, `detail.verified_toggle` | the locator, page or block is not shown; marking a record verified changes nothing |
| `filter.total` | the optional filter is present and the total does not follow it |
| `links.panel`, `links.listed`, `links.outside_marked` | the trace panel shows with no links, or is missing with links, or an outside end is not marked |
| `links.kinds_as_written` | a link kind such as `x-custom` or `Is Derived From` is renamed, merged or dropped (F14) |
| `rejected.list` | a rejected record or its reason is missing |
| `nav.present` | the app has no `nav` mark (not a failure: a one-screen app has no menu) or more than one |
| `nav.landmark` | the menu is not a `<nav>` or `role="navigation"`, has no accessible name, or has another name than the map's |
| `nav.items_listed` | a menu item has no `data-screen`, two items name one screen, fewer than two items, or (with the map) the items or their order differ from the map |
| `nav.groups`, `nav.default_open_visible` | (with the map) an item is in another group than the map says, or an item in a group that starts open is hidden |
| `nav.items_are_controls` | a menu item is not a `<button>` or an `<a href>` |
| `nav.starts_on_current_screen` | at the start not exactly one screen shows, not exactly one item is `aria-current`, or they are not the same screen |
| `nav.each_item_opens_its_screen` | after clicking an item the screen showing is not the item's. This is the menu leading somewhere else than its label says |
| `nav.each_item_marks_itself_current` | after a click the item marked as current is not the one clicked (nothing, or the first item, or two items) |
| `nav.each_screen_has_its_own_content` | a screen shows exactly what the screen before it showed: the menu changes the highlight and not the page |
| `nav.breadcrumb_follows`, `nav.page_title_follows` | the breadcrumb or (with the map) the document title does not name the screen showing |
| `nav.keeps_the_dataset` | going from screen to screen leaves the app in another state than `ready`, or logs an error: the data did not survive the move |
| `nav.round_trip` | the first screen, visited again after all the others, shows other content than the first time |
| `nav.keyboard` | focusing an item and pressing Enter does not open its screen |
| `nav.count_not_invented` | a count that is not a whole number, is 0, or (with the map) is on an item that has none. The probe cannot tell whether a count that looks right was computed from the data |
| `nav.narrow_shows_every_item@390` | (with the map, when it says the narrow layout shows every item) an item is hidden or cut off at 390 px |
| `layout.no_sideways_scroll@1440`, `@900`, `@390`, `@320` | the page scrolls sideways at that width (F10 has a 300-character word) |
| `perf.ready_within_30s` | the large dataset takes more than 30 seconds to appear |
| `tokens.declared` | the page does not carry the design's variables: `tokens.css` is not linked, or not found |
| `tokens.colours_are_tokens` | a colour on screen is not within 2.5 (OKLab × 100) of a token colour |
| `tokens.fonts_are_tokens`, `tokens.fonts_loaded`, `tokens.no_default_font` | text is drawn in a font the design does not name, or in a browser default because the named font did not load. This is the usual meaning of "the CSS is off" |
| `canary.*` | a dataset written fresh for this run (so nothing could have been typed in beforehand) is not shown completely: rows, statements, warning, link kind, rejected reason, other field, counts. `canary.nothing_left_over`: part of the dataset opened before is still on the screen |
| `refuses.flipped`, `.no_manifest`, `.wrong_count` | a dataset with one byte changed, no manifest, or a wrong count is shown instead of refused |

## What the probe does not do

The menu checks do not look at the foot items (Glossary and help, Close project), the top-bar shortcuts, the search box, the panels that open over a screen, or the steps of the import; `tools/gui_checks/site_map.py` reads those from a running page. They say that every item leads to the screen its label names, not that the screen's content is right: that is the dataset checks. It shows that the screen is bound to the dataset and that the behaviours in the table hold for these fourteen shapes in one browser (Chromium). It does not
tell whether the screen is good to look at or to use, whether it is accessible beyond what the marks expose, whether it works with real requirements, or
what happens in another browser. It reads the files itself, so a bug in `probe.py` is possible: the tests in `tools/test_gui_checks_browser.py` break the
reference viewer in many separate ways (the `test_break_` tests) and show that the probe fails each one, which is evidence the checks can fail, not proof that nothing is missed.
