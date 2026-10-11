# How the Excalidraw boards were made, and how an agent can expand and recreate them

The ten boards (storyboard, wireframes, system flows, UI kit, scale, lenses, group decisions, assistant, more pipelines, any-input) were **not drawn by hand**. Each is produced by a small Python program that writes an `.excalidraw` file. That is why an agent can change one rule (a colour, a banner, a widget) and regenerate every board consistently, or add a screen by writing a function.

**Checked in this session:** all nine earlier boards rebuild **byte-for-byte identical** to the files you already have (`python build_all.py --check`), the package works from a clean copy (`npm ci`, bundle, build, validate, render), and the example in recipe A runs. **Not checked:** opening the files in the live Excalidraw app. Every check used Excalidraw's own exporter (`@excalidraw/utils`) rather than the app. Open one board in Excalidraw before you build on top of the format.

## 1. What is in the package

| File | Role |
|---|---|
| `exc.py` | The scene builder. Turns shapes, text, arrows and frames into valid Excalidraw JSON. Standard library only. |
| `wf.py` | Wireframe widgets (card, button, chip, provenance mark, callout) and the colour palette. |
| `wf2.py` | Higher-level helpers: wrapped paragraphs, tables, checklists, sign-off dots, the sidebar with a lens selector. |
| `wf_a.py` `wf_b.py` `wf_c.py` | Screens 1 to 10 of the original wireframes (open, map fields, overview, review, actions, methods, audit, export, glossary, phone). |
| `sb.py` `flows.py` `kit.py` | Boards 01, 03 and 04: storyboard, system flows, information architecture and UI kit. Each has `build(path)`. |
| `sc.py` `sc2.py` `lens.py` `g7.py` `asst.py` `pipes.py` `screens_input.py` | Screens for boards 05 to 10. |
| `build_wf.py` | Composer for board 02 (it also has `build(path)`). |
| `boards_05_09.py` | Boards 05 to 10 as **data**: title, seed, and the list of screens with their frame sizes. |
| `build_all.py` | Builds every board, validates each, and with `--check` compares to files you already have. |
| `validate.py` | Structural checks (duplicate ids, dangling references, frame order, overflow). |
| `render.py`, `entry.js`, `make_bundle.sh`, `package.json` | Render a board to PNG with Excalidraw's own exporter in headless Chromium. |
| `examples/hello_board.py`, `examples/add_a_screen.py` | The smallest board, and a worked example of adding a screen. |

Deliberately **not** shipped: `bundle.js` (about 20 MB, rebuilt in seconds), `node_modules`, and PNG previews.

## 2. Commands (all verified)

```bash
# Build boards: standard library only
python build_all.py --out out                 # all ten boards, each validated
python build_all.py --only 02,05 --out out    # a subset
python build_all.py --check --out ../excalidraw   # fresh build vs. the files you already have: "identical" or "DIFFERS"

# Look at them: needs Node, Playwright and a Chromium
pip install playwright pillow                 # Chromium: set CHROMIUM_PATH, or use Playwright's own install
npm ci && sh make_bundle.sh                   # one time: builds bundle.js from @excalidraw/utils (MIT) and esbuild (MIT)
python render.py out/05_scale_and_multiuser.excalidraw out/05.png 0.5     # last number = scale
python validate.py out/*.excalidraw
```

Rendering is offline and skips font loading, so the hand-drawn font appears as a plain sans in the PNG preview. In Excalidraw proper it is hand-drawn. Judge text fit with margin, because the real font is a little wider than the preview.

## 3. How to think about it

A board is a stack of **frames**. A frame is one screen or one diagram. Beside each frame sits a **Notes** column of numbered statements that match red numbered **callouts** drawn on the frame. The picture is the layout; the notes are the reasoning. A screen is one Python function:

```python
def s_example(d, ox, oy):            # d = the Doc, (ox, oy) = where this frame's top-left corner goes on the board
    ...draw with frame-local coordinates...
    return ['note 1', 'note 2']      # shown beside the frame, numbered 1, 2 ...
```

Layers, from the bottom:

1. **`exc.Doc`** knows Excalidraw's file format. It knows nothing about requirements.
2. **`wf.Scr(d, ox, oy)`** wraps `Doc` so every coordinate is relative to the frame's corner. It adds widgets.
3. **`wf2` helpers** build repeated structures (tables, checklists, the sidebar).
4. **Screen functions** are the design content.
5. **Composers** (`build_all.py`, `boards_05_09.py`, each `build(path)`) stack screens on a board and write the file.

## 4. `exc.Doc`: the file format and the API

An `.excalidraw` file is JSON: `{"type":"excalidraw","version":2,"source":...,"elements":[...],"appState":{...},"files":{}}`. Each element has an `id`, `type` (`rectangle`, `ellipse`, `diamond`, `text`, `arrow`, `line`, `frame`), position and size, colours, and links to other elements. The builder gets four things right that are easy to get wrong:

- **Text inside a shape** is a separate `text` element with `containerId` set to the shape, and the shape lists it under `boundElements`. `Doc.shape(..., label=...)` does both.
- **Arrows glued to shapes** carry `startBinding` / `endBinding` and appear in each shape's `boundElements`, so moving a box drags its arrows. `Doc.connect` does this.
- **Frames** list their children by `frameId`, and the frame element must come **after** its children in the `elements` array. `frame_end()` appends it last. `validate.py` fails a file that breaks this.
- **Determinism.** Every random value (element ids, seeds, version nonces) comes from `random.Random(seed)`. Same code and same `Doc(seed)` give the same bytes. Use a **unique seed per board**.

| Call | What it does |
|---|---|
| `Doc(seed)` | New scene. |
| `d.frame_begin(x, y, w, h, name)` / `d.frame_end()` | Everything drawn in between belongs to that frame. Cannot nest. |
| `d.rect / ellipse / diamond(x, y, w, h, label=None, fill=, stroke=, sw=, dash=, fs=, family=, align=, valign=, pad=, rounded=)` | A shape, optionally with bound, auto-wrapped text. Returns the element dict. |
| `d.text(x, y, s, fs=14, color=, family=2, align=, w=)` | Free text. `\n` breaks lines. Does **not** wrap. |
| `d.wrap(s, width_px, fs, family=2)` | Wrap to a pixel width using the average-glyph-width table `CW` (family 1: 0.60, 2: 0.55, 3: 0.60, 5: 0.58 of the font size; line height 1.25). |
| `d.poly(points, typ='arrow'\|'line', head=, tail=, dash=, sw=, start=, end=)` | Poly-line or arrow through absolute points. |
| `d.connect(a, b, sa='r', sb='l', label=None, dash=, color=, lx=, ly=)` | Elbow arrow from side `sa` (`l r t b`) of shape `a` to side `sb` of `b`, bound to both. |
| `d.save(path)` | Writes the file. Drops empty unbound text. |

Fonts: `family=1` hand-drawn (titles, annotations, callout captions), `2` clean sans (UI text), `3` monospace (small caps captions, table headers, code-like text). `roughness` is 0 everywhere, so shapes are crisp and only the font is hand-drawn.

## 5. The wireframe vocabulary (`wf.Scr`, `wf2`)

All `x, y` are relative to the frame's top-left corner.

| Call | Draws |
|---|---|
| `s.r(x,y,w,h,label,fill=,stroke=,dash=)` | Rectangle (shape with optional label). `s.t(x,y,s,fs=,color=,family=)` is text. |
| `s.card(x,y,w,h,fill=,dash=)` | White rounded panel. Dashed = optional or not yet built. |
| `s.caps(x,y,text)` | Small monospace caption in soft grey: the label of a section. |
| `s.h1(x,y,text,fs=22)` | Page heading. |
| `s.btn(x,y,w,h,label,primary=,disabled=)` | Button. One primary action per screen. |
| `s.chip(x,y,w,h,label,fill=,stroke=,dash=)` | Small pill: a state or a label. Always a word, never colour alone. |
| `s.bar(x,y,w,frac)` / `bar_h(...)` | Progress bar / labelled horizontal bar. |
| `s.ph(x,y,w,n,gap=)` | Placeholder text lines (grey bars). |
| `s.prov(x,y,kind,label)` | Provenance mark: **square = mechanical**, **diamond = AI**, **circle = person**. |
| `s.num(x,y,n)` | Red numbered callout. The note with the same number goes in the Notes column. |
| `s.check(x,y)`, `checkbox(s,x,y,checked,label)` | Tick marks. |
| `s.tokens(x,y,words)` | A statement with highlighted numbers (amber), modals (blue), negation (red), conditions (violet). |
| `para(s,x,y,text,w,fs=10)` | **Wrapped** text. Returns the y below it. Use this for any sentence. |
| `table(s,x,y,widths,head,rows,fs=,minh=,bold_first=)` | Wrapped table. Cells may be `(text, fill)`. Returns y below. |
| `chk_list(s,x,y,w,[(state,text),...])` | Checklist with `Pass / Needs you / Blocked / Done / Open` chips. |
| `sign_dots(s,x,y,[state x4])` | Four lens markers S P U N: `signed / pending / changes / na / stale`. |
| `kv(s,x,y,key,value)`, `avatar(...)`, `new_frame(d,ox,oy,w,h,name)` | Key-value line; initials circle; open a frame with its background and return a `Scr`. |
| `shell2(s,W,H,active,lens=0)` | App chrome: sidebar with a lens selector, title block, DRAFT banner. Returns the content origin `(168, 76)`. Needs a frame at least about 500 high (the example uses 520). |
| `notes(d,x,y,[(n,text),...],title='Notes')` | The numbered Notes column, placed **outside and right of** the frame. |
| `flows.box(d,x,y,w,h,label,fill,stroke=,dash=)`, `flows.mark(d,x,y,kind)` | Boxes and marks for diagrams (swimlanes, state machines, architecture). |

Palette (names in `wf.py`): `GREY #f1f3f5` page background, `DARK #343a40` body text, `SOFT #868e96` captions, `ACC #1A4DB5` primary action, `RED #e03131` callouts and notes, and the fills `GREEN_BG #b2f2bb`, `AMBER_BG #ffec99`, `RED_BG #ffc9c9`, `BLUE_BG #a5d8ff`, `VIOLET_BG #eebefa`. Provenance colours: `MECH #34424F`, `AIC #8B1F6B`, `HUM #1B6B3A`; assistant (speech bubble) `#0B6E99` on `#e3f4fb`. Diagram fills in `flows.py`: `SRC_F`, `MECH_F`, `AI_F`, `HUM_F`, `GUARD_F`.

## 6. Design rules the boards follow (keep them when you extend)

1. **Grey is structure; colour appears only where it carries meaning.** Lane, state and trust level are always also a word.
2. **Every screen has red callouts and a Notes column.** One idea per note, and the note says *why*, not *what*.
3. **Marks never change meaning:** square mechanical, diamond AI, circle person.
4. **Everything is a draft.** The DRAFT banner is part of the chrome. Nothing on a screen implies an approval.
5. **Sample data only.** Names, counts and IDs come from the synthetic sample. Never paste real program data into a board.
6. **One primary action per screen.** Dashed means optional or not yet built.
7. **A frame is a screen.** Name frames `N.M · Title`, so the boards read as an index in Excalidraw's frame list.

## 7. Where each screen lives

| Board | Composer | Screen functions (file) |
|---|---|---|
| 01 Storyboard | `sb.build` | nine panels in `sb.PANELS` |
| 02 Wireframes | `build_wf.build` | `s_open s_import s_overview` (`wf_a`), `s_review s_actions` (`wf_b`), `s_methods s_audit s_export s_glossary s_mobile` (`wf_c`) |
| 03 System flows | `flows.build` | `flow_pipeline flow_states flow_components flow_sequence` |
| 04 UI kit and IA | `kit.build` | `ia kit tokens lenses questions` |
| 05 Scale | `boards_05_09.BOARDS` | `sc.s1_queue s2_explorer s3_team`, `sc2.s4_states s5_policy s6_numbers` |
| 06 Lenses | same | `lens.l0_overview l1_se l2_pe l3_ux l4_nu` |
| 07 Group decisions | same | `g7.g1_workspace g2_strategies g3_rationale g4_revisions g5_ledger` |
| 08 Assistant | same | `asst.a1_drawer a2_scenarios a3_architecture a4_effects` |
| 09 Pipelines | same | `pipes.p1_map p2_refresh p3_calibration p4_writeback p5_lint` |
| 10 Any input | same | `screens_input.i1_open_any i2_map_any i3_extract i4_arch` |

## 8. Recipes

### A. Add a screen to a board
Copy `examples/add_a_screen.py`, change the drawing, then register the function. For an existing board add one tuple to its `screens` list in `boards_05_09.py`: `(my_module.my_screen, frame_width, frame_height)`. The width decides where the Notes column sits (`width + 40`), and the height plus 80 is the gap to the next screen. Then:

```bash
python build_all.py --only 10 --out out        # builds and validates
python render.py out/10_input_any_source.excalidraw out/10.png 0.6
```

Look at the PNG. Crop to a frame with Pillow (`Image.open(p).crop((x0,y0,x1,y1))`) when the board is tall.

### B. Add a new board
Add an entry to `BOARDS` in `boards_05_09.py` with a new `seed`, a `title` and its `screens`. `build_all.py` picks it up and `--only NN` works from the leading number. Never reuse a seed.

### C. Change something shared, then see what moved
Edit a colour in `wf.py` or a widget in `Scr`, then run `python build_all.py --check --out ../excalidraw`. Boards that use it print `DIFFERS`, and the ones you did not mean to change stay `identical`. That is the regression test for design changes.

### D. Boards 01 to 04 still say "four lenses sign off" (not yet changed)
The prototype and boards 05 to 10 use the policy rule: the lenses your sign-off policy requires must sign. Boards 01 to 04 were drawn earlier and still show the old text in 17 lines across `sb.py`, `flows.py`, `kit.py`, `wf.py`, `wf_a.py`, `wf_b.py`, `wf_c.py`, `build_wf.py`. Find them with `grep -n "four lenses\|all four" *.py`. Replace each with the policy wording (the constant `BANNER` in `wf2.py` is the banner text), rebuild, and read each changed frame, because the replacement text is longer in places. `flows.py` line 88 is a state box ("APPROVED, all four lenses signed") that should become "APPROVED, required lenses signed". I did not make this change, so the boards you have are still the originals.

### E. Redraw a prototype screen as a wireframe
Open the prototype page, list its regions top to bottom, and map each to a widget in section 5 (a heading, a card, a table, a chip row). Write the screen function with frame-local coordinates, put a red callout on each region that needs explaining, and write the notes. Render and compare side by side.

### F. Recreate everything from nothing
`python build_all.py --out out` plus `python validate.py out/*.excalidraw`. If you have the original files, add `--check` to prove the rebuild is identical.

## 9. Definition of done for any board change

1. `build_all.py` exits 0. `validate.py` reports `dup 0`, `dangling 0`, `frame-order 0`.
2. `outside frame` is 0, or each overflow is explained. It means a child drawn outside its frame, usually unwrapped text. Fix it with `para()`.
3. You rendered the board and **looked** at every changed frame. Check text fit, overlapping arrows, and that callout numbers match the Notes.
4. Boards you did not mean to touch still say `identical` under `--check`.
5. No real program data on any screen.

## 10. Things that bit me

- Bare `s.t()` and `d.text()` do **not** wrap. Long sentences overflow the frame. Use `para()` or `d.wrap()`.
- Text width is an estimate (`CW`), not a measurement. Leave 10 to 15 percent spare width in chips and buttons. A label that wraps inside a chip spills out of it.
- `shell2` assumes a frame at least about 500 high. In a shorter frame the sidebar's note overlaps the Glossary button.
- Connector labels sit at the midpoint of the elbow and collide with the line when the gap between shapes is under about 80 px. Widen the gap, or place a separate `d.text` instead of using `label=`.
- Seven arrows into one box merge into one thick bus. That is fine for "many sources into one profile", but not for distinct flows.
- Left-edge callouts at `x=22` can touch text that starts at `x=40`. Use `x=12` where a screen's text starts at 40.
- The frame must be added **after** its children. Do not edit `frame_end()`.

## 11. Prompts to give an agent

**Rebuild and prove it.** "In `excalidraw_generator/`, run `python build_all.py --out out` and then `--check --out <folder with the boards I have>`. Report any board that says DIFFERS. Do not edit any file."

**Add a screen.** "Read `EXCALIDRAW_GUIDE.md` sections 3 to 6 and `examples/add_a_screen.py`. Add a screen `<name>` to board `<NN>` that shows `<what>` for the `<lens>` lens. Use only widgets from section 5, keep the design rules in section 6, give every callout a note that says why, and use sample data only. Build, validate, render, and look at the frame. Report what you saw and anything that overflowed. Do not change other boards; prove it with `--check`."

**Redraw from the prototype.** "Open `<prototype url or file>`, list the regions of screen `<X>`, and redraw it as a wireframe frame in board `<NN>` following recipe E. Every region that is a decision point gets a callout and a note."

**Refresh boards 01 to 04.** "Follow recipe D. Replace every 'four lenses' statement in boards 01 to 04 with the policy wording from `wf2.BANNER`. Rebuild, read every changed frame, and list each replacement with its file and line. Boards 05 to 10 must stay identical."

**Audit.** "Read-only. Render every board at scale 0.4 and list inconsistencies: wording that disagrees with `wf2.BANNER`, marks used for the wrong meaning, a screen with no callouts, a Notes column whose count differs from its callouts. Do not edit anything."

## 12. Licences

`@excalidraw/utils` 0.1.5 and `esbuild` 0.28.2 are MIT (read from their `package.json`). Excalidraw's own app and file format are open source. Check the licence terms of anything else you pull in.
