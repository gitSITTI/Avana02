# What was read from index.html

Read with a real browser at 1440 x 900. Everything below is what the browser computed. **Roles marked guess or missing are for you to confirm or correct.**

## 1. The roles (the short list that is compared with our design)

| Role | Value | How it was read | Sure? |
|---|---|---|---|
| Main action colour (the colour of the main button) | `#0F766E` | the background of the main button ('New task', 1 on the page) | read |
| Text on the main action colour (the colour of the words on the main button) | `#FFFFFF` | the text colour of that button | read |
| Page background (the colour behind everything) | `#F7F5F0` | the page's own background | read |
| Card and panel background (the colour inside cards, panels and the side menu) | `#FFFFFF` | the background of the commonest card | read |
| Main text (the colour of ordinary text) | `#1F2933` | the text colour of the page body | read |
| Quiet text (the colour of captions and hints) | `#52606D` | the second most used text colour with enough contrast | guess |
| Card and divider lines (the thin lines round cards and between rows) | `#E4E7EB` | the border of the commonest card | read |
| Input outline (the outline of text boxes and buttons) | `#9AA5B1` | the outline of the commonest text box | read |
| Hover background (the colour a row or menu item takes under the pointer) | `#EDF2F7` | the background a menu item or button takes under the pointer | read |
| Selected background (the colour of the menu item or row that is current) | `#D9F2EE` | the background of the element marked as current or selected | read |
| Text font (the font of ordinary text) | `sans-serif` | the font of the page body | read |
| Requirement-text font (the font the wording of a requirement is shown in) | `sans-serif` | the body font: requirement wording would follow the body text | guess |
| Code font (the font of identifiers and code) | `monospace` | the font of code elements | read |
| Text size (the size of ordinary text) | `15px` | the font size of the page body | read |
| Small text size (the size of captions and chips) | `12px` | the smallest text size that carries 3 % of the characters | guess |
| Page title size (the size of the title at the top of a page) | `26px` | the size of the page's h1 | read |
| Button and input corners (how round buttons and inputs are) | `20px` | the corner of the main button | read |
| Card corners (how round cards and panels are) | `6px` | the corner of the commonest card | read |
| Chip corners (how round small labels (chips, badges) are) | `4px` | the corner of the commonest badge or chip | read |
| Card shadow (the shadow under a raised card) | `rgba(31, 41, 51, 0.12) 0px 1px 3px 0px` | the shadow of the commonest card | read |
| Control height (how tall a button or input is) | `38px` | the height most buttons and text boxes have | read |

## 2. Fonts

In use, most text first: sans-serif (329 characters), Fictional Serif (15 characters), monospace (10 characters).
- sans-serif: a generic family, so each machine picks the font; this one drew it in Liberation Sans
- Fictional Serif: asked for, but this machine does not have it, so it was drawn in Liberation Serif. A picture made here will use that stand-in

## 3. Palette

| Colour | Text | Background | Border | Icon | Your variable names for it |
|---|---|---|---|---|---|
| `#E4E7EB` | 0 | 0 | 26 | 0 | `--line` |
| `#1F2933` | 20 | 0 | 0 | 4 | `--text` |
| `#FFFFFF` | 1 | 7 | 0 | 0 | `--card` |
| `#9AA5B1` | 0 | 0 | 8 | 0 | none |
| `#52606D` | 5 | 0 | 0 | 0 | `--muted` |
| `#0F766E` | 1 | 1 | 0 | 2 | `--brand` |
| `#14532D` | 2 | 0 | 0 | 0 | none |
| `#E3F5E8` | 0 | 2 | 0 | 0 | none |
| `#D9F2EE` | 0 | 1 | 0 | 0 | `--brand-soft` |
| `#8A1C1C` | 1 | 0 | 0 | 0 | none |
| `#FDECEC` | 0 | 1 | 0 | 0 | none |
| `#EEF2F6` | 0 | 1 | 0 | 0 | none |

Radii: 6px (5), 4px (3), 20px (2), 3px (1). Shadows: rgba(31, 41, 51, 0.12) 0px 1px 3px 0px (3). Padding values: 8px, 12px, 16px, 2px, 10px, 24px. Breakpoints: 800px.

## 4. Components (distinct looks, commonest first)

| Kind | Looks like | On the page | Found again with | Picture |
|---|---|---|---|---|
| button | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 15px text, corner 20px | 1 ('Filter') | `.btn-quiet` (100% exact) | shots/01_button.png |
| button | rgb(255, 255, 255) on rgb(15, 118, 110), 15px text, corner 20px | 1 ('New task') | `.btn-primary` (100% exact) | shots/02_button.png |
| link | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 15px text, corner 6px | 2 ('Backlog') | `a` (67% exact) | - |
| link | rgb(15, 118, 110) on rgb(217, 242, 238), 15px text, corner 6px | 1 ('Board') | `a` (33% exact) | - |
| input | rgb(0, 0, 0) on rgb(255, 255, 255), 15px text, corner 6px | 1 ('Search tasks') | `input` (100% exact) | shots/05_input.png |
| heading | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 16px text, corner 0px | 3 ('Write the release notes') | `h3` (100% exact) | shots/06_heading.png |
| heading | rgb(82, 96, 109) on rgba(0, 0, 0, 0), 12px text, corner 0px | 1 ('Workspace') | `h2` (100% exact) | shots/07_heading.png |
| heading | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 26px text, corner 0px | 1 ('Team task board') | `h1` (100% exact) | shots/08_heading.png |
| table_cell | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 14px text, corner 0px | 6 ('Write the release notes') | `td` (67% exact) | shots/09_table_cell.png |
| table_cell | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 14px text, corner 0px | 3 ('Task') | `th` (100% exact) | shots/10_table_cell.png |
| table_cell | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 14px text, corner 0px | 3 ('Run make check') | `td` (33% exact) | shots/11_table_cell.png |
| badge | rgb(20, 83, 45) on rgb(227, 245, 232), 12px text, corner 4px | 2 ('Done') | `.done` (100% exact) | shots/12_badge.png |
| badge | rgb(138, 28, 28) on rgb(253, 236, 236), 12px text, corner 4px | 1 ('Blocked') | `span.badge` (33% exact) | shots/13_badge.png |
| nav_item | rgb(31, 41, 51) on rgba(0, 0, 0, 0), 15px text, corner 6px | 2 ('Backlog') | `a` (67% exact) | shots/14_nav_item.png |
| nav_item | rgb(15, 118, 110) on rgb(217, 242, 238), 15px text, corner 6px | 1 ('Board') | `a` (33% exact) | shots/15_nav_item.png |
| card | rgb(31, 41, 51) on rgb(255, 255, 255), 15px text, corner 6px, shadow | 3 ('Write the release notes\n') | `.card` (100% exact) | shots/16_card.png |

## 5. Menus and structure

- **Sections**: (no heading): Board, Backlog, Reports
- Headings in the main area: none
- Icons: 3 of 3 menu items carry one; 0 of 2 buttons carry one.
- Region 1, navigation "Sections": 220 x 900 (regions/01_navigation.png)
- Region 2, banner: 1220 x 63 (regions/02_banner.png)
- Region 3, main: 1220 x 318 (regions/03_main.png)
- Region 4, contentinfo: 1220 x 51 (regions/04_contentinfo.png)

## 6. Not read

- what this browser drew at 1440x900; a second theme, an open menu or anything behind a click or sign-in that was not set up is not read
- Which element you meant as the main button when there are several: the one the page uses most with a colour is taken. Correct it if that is wrong.
