# The engineering V in this project

Systems engineers think in the V. Down the left leg the requirements get more detailed (what the stakeholders need, then system, subsystem and component requirements). At the bottom the thing is designed and built. Up the right leg each level is shown to be met by a matching check (component, subsystem and system verification, then validation by the people who asked for it).

Consolidating requirements changes the left leg: it removes some requirements, replaces others and adds reworded ones. That is only safe if the right leg still has something that proves each requirement that is left. So this project shows the V wherever a person is deciding, and says what each decision does to it.

This page says what is shown, where, how every number is counted and what is only a sample. Nothing here has been used on a real program.

## Where the V appears

| Place | What it shows | Real or sample |
|---|---|---|
| Prototype, header of every workspace screen | A small V (four circles down the left, four squares up the right). A fuller circle means more of that level decided; a fuller square means more of that level traced. It is a button that opens the V page. Its accessible name says the numbers in words. | Sample levels and verification |
| Prototype, **The V** page | The whole V as a picture and as a table: requirements now and after your decisions, clusters decided, requirements with a method and an item, gaps, items to re-point, and a button to see the gaps | Sample levels and verification |
| Prototype, Home | One card: how many clusters have a standing decision on the left leg, how many requirements are traced on the right | Sample |
| Prototype, cluster review | A strip: at which level the members sit, whether the cluster crosses levels (then it offers link or supersede, never merge), and which verification items would have to move | Sample |
| Prototype, Results | A by-level table of before and after, and a note on how many verification items sit on requirements your decisions remove | Sample |
| Prototype, review queue and All requirements | Filters for the level and for "gap: no method" and "gap: no item" | Sample |
| Prototype, Export | One line saying what the V looks like in the package | Sample |
| `reqin vee DATASET_DIR` | The same table, worked out from an imported dataset (see below) | **Real, from the data** |
| Excalidraw board 11 | The V page, the V on every screen, what one decision does to the right leg, and how the numbers are counted | Drawn from the same sample |
| Excalidraw boards 02, 05, 06, 07, 08 | The small V in each wireframe's header, so a drawing of a screen shows where the real one has it | Drawn |

The same small drawing is on every screen on purpose: people see where they are in the V without leaving what they are doing, and the picture is the same everywhere so it is learned once.

## How every number is counted

These rules are written so a person can check any figure by hand. The prototype and `reqin vee` use the same ones, and each has tests that fail if a rule changes.

**Level.** There are four: 1 Stakeholder needs, 2 System, 3 Subsystem, 4 Component. Each is checked on the right by Validation, System verification, Subsystem verification and Component verification.

- `reqin vee` by default places a requirement by its depth in the parent tree (a root is level 1; anything deeper than 4 is counted at 4 and reported). If no requirement has a parent, depth says nothing, so no requirement is placed and the report says so. With `--by field --level-field NAME` it reads a field instead: `1` to `4`, `L2`, `level 3`, or the words need, stakeholder, system, subsystem, component. Anything else is reported as "not placed at a level".
- The prototype's levels are sample values generated from each requirement's ID. They show the shape of the page and nothing about any real project.

**Method.** Test, Analysis, Inspection or Demonstration, read from the verification field (the words, or the single letters T, A, I, D). A field naming two methods counts under each and the requirement counts once as having a method. Any other text is "other" and is not a method.

**Item.** A verify link: the verification item is the link's source and the requirement it proves is the target. If the target is not in the import but the source is (the link was exported the other way round), it counts for the source. A verify link with neither end in the import counts for no one and is reported.

**Traced.** A requirement is traced when it has a method **and** at least one item. Everything else is a gap, listed as "no method", "no item" or both. A method without an item is a promise; an item without a method is evidence nobody said how to read.

**After your decisions.** A requirement leaves the left leg when a decision merges it away or marks it superseded (the same rule as the Results page: `dispositionsOf` decides, nothing else). A decision that gives a cluster a new wording adds one requirement at the level of the cluster's members. A cluster only counts as decided when it has a standing decision: decided, in review, approved, or its members kept as siblings. A decision that is stale or disputed is held and not counted, and the Home card says how many are held. One function (`standingDec` in `prototype/parts/logic3.js`) is the rule for the V, the Results page and the review queue, so the three cannot disagree.

**Items to carry over.** Verification items that sit on a requirement a decision removes. They must be pointed at the requirement that takes its place. The app never does this for you and never changes a verification item (it works on the left leg only and writes nothing back); it counts the items so the work is visible before sign-off. The prototype also counts how many of those items would land on a different level than the one they were written for.

**Clusters that cross levels.** A cluster whose members sit at different levels (typically a system requirement and the component requirement that restates it) is a refinement, not a duplicate. The app offers "Link" or "Supersede" and does not offer "Merge", so a decision cannot silently collapse two levels into one.

## `reqin vee`

```
reqin vee DATASET_DIR                         levels from the parent links (depth in the tree)
reqin vee DATASET_DIR --by field --level-field "Level"
reqin vee DATASET_DIR --json                  the same, for a screen or a CI job
```

It reads a dataset folder, never a file (see `reqin/GUI_CONTRACT.md` section 5.9), and prints one row per level: requirements, traced, gaps, no method, no item, items and the check that level is met by. Below the table it prints the methods by level and any notes ("12 verify links have neither end among the imported requirements"). It is pure: the same dataset always gives the same report. The source is `reqin/src/reqin/vee.py`; the 69 tests are in `reqin/tests/test_vee.py`.

What it does **not** do: judge whether a verification item is adequate, read a model's verification cases, or know your program's level names. If your levels are not these four, map them with a field.

## What has and has not been checked

| Checked | How |
|---|---|
| The prototype's numbers add up and agree between pages | `prototype/verify.js` resolves every template hole across about 1,000 states and has gates for the V: requirements after decisions equal the Results page's count, the queue's "still to decide" equals the V's open count, traced is counted independently of the page's own function |
| The gates bite | `tools/mutation/vee.py` changes the counting rules in a copy of the prototype 10 ways (traced counts items only, superseded not removed, new wording not added, items lost when merged, a level past 4, and others); every change makes `verify.js` fail (one of them by a crash). The first run of an earlier version of this showed that "traced counts items only" escaped, which is why it now has its own gate. See [`tools/mutation/README.md`](../tools/mutation/README.md) |
| The V page in a browser | `prototype/b14.py`: 79 checks at 1440 px and 81 at each of 900 and 390 px (the page, the header glyph on each screen, the filters, keyboard order, focus ring, no sideways scroll, the names read by a screen reader) |
| `reqin vee` | 69 tests, including the depth rule, each way of writing a level, each way of writing a method, link directions, links with no end in the import, and deliberate breaks of the rules |
| The board | Rebuilds byte for byte (`make boards`); structurally valid; every picture is checked to be made from the current board |
| **Not checked** | Any real project's levels, methods or verification items. The sample levels in the prototype are generated. Whether people who live in the V find this the right view: that is why it is shown before it is built further. Whether four levels is the right number for your program |

## Adding the V to another screen

- Put the macro `§VG:name:width§` where the glyph should go and give the component a `name` from `veeGlyph()` in `prototype/parts/logic3.js`. It draws the glyph with plain elements because the page runtime does not fill template holes inside an `<svg>`.
- If the screen shows a number about the V, get it from `veeOf(S, infos)`. Do not count it again in the screen: `verify.js` compares every V number on screen with `veeOf` and with the Results page.
- Say it in words as well. The glyph has an accessible name that reads the same numbers; add the sentence a person would say ("84 of 252 clusters have a standing decision on the left leg").
- On a board, call `mini_vee(s, x, y)` from `excalidraw_generator/wf.py` in the screen's header, or draw the full V with `vee_glyph` from `screens_v.py`.
