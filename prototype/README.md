# Interactive prototype

A clickable prototype of the app's screens, built as a single `Main.dc.html` page (the design-canvas format: `<x-dc>` templates with `{{holes}}`, one `Component` class). **Every number in it is synthetic**, except the Open and Import screens, whose counts, mapping labels and locators are the real output of `reqin` run on its fixtures.

| Path | What it is |
|---|---|
| `parts/m/*.html` | The screens, one file per screen. Edit these. |
| `parts/*.js` | Data (`data*.js`), logic (`logic*.js`, `misc.js`) and the component (`c1-c3.js`). |
| `build.py` | Joins the parts into `project/Main.dc.html`. **Never edit `Main.dc.html` by hand.** |
| `verify.js` | Static check: every `{{hole}}` in the template resolves to a value of the right kind, across about 1,000 generated states. Exits 1 on any issue. |
| `b11.py` | Browser test with assertions for the Open, Import, Change and Verify flows (39 checks, run at 1440, 900 and 390 px). |
| `b0.py` to `b10.py`, `t0.py`, `t1.py` | Older flow scripts: they drive every other screen and print what they see. They do not assert; compare their output before and after a change. |
| `project/support.js` | The runtime that the design-canvas format needs. It is not authored here (it bundles React under the MIT license). |

```bash
python3 build.py                          # rebuild project/Main.dc.html from parts/
node verify.js project/Main.dc.html       # static check; prints ISSUES 0
# browser tests (need Playwright for Python and a Chromium; set CHROMIUM_PATH if it is not auto-found)
(cd vendor && npm ci)                     # React and Babel for the local harness
python3 b11.py 1440 && python3 b11.py 390
```

CI runs the first two (GitLab: `prototype:build-identical`, `prototype:verify`; GitHub: the `prototype` job). The browser tests are run by hand: `make proto-test`.

**Fonts and network.** Opened with network access, the page requests IBM Plex Sans, Serif and Mono from Google Fonts (`fonts.googleapis.com`; the request carries no requirement data, but it does tell Google the page was opened). Offline, or on a network that blocks it, the page still works and uses the browser's own fonts. The browser tests and `shots.py` block that request on purpose, so the pictures in `docs/images/prototype/` show the fallback fonts. If your network forbids the request, self-host the fonts (they are under the SIL Open Font License) and change the `<link>` in `parts/m/00_head.html`; that is not done yet.

## Open and Import screens (board 10, made interactive)

* Open: six source cards, each with a trust level in words (Structured, Tabular, Parsed, Extracted; `.mdzip` says "not read directly yet" and offers the ReqIF route). A drop zone names what a sample file would be recognised as.
* Import: a proposed mapping with a label per row, a **Change** control that edits the profile, a dry-run report that recounts as you change things, the first three records as the review screens will show them, and the profile as YAML.
* Word or PDF: an extra step to **verify each found statement** against the page, with its location, an invented-ID warning, and a source-page view.

What is not real: nothing is read from your computer, no server is contacted, and nothing is saved. The workspace after Import always uses the same synthetic 1,248-requirement sample. The SysML v2 API route ("systems v2" recent project) is illustrative: its field names are assumed in the reference code and untested against a real server.
