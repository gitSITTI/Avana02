"""The probe (tools/gui_checks/probe.py) against the reference viewer in a real browser, and against the reference viewer broken on purpose.

Skipped when Playwright or its Chromium is not installed. What this proves:
  - the reference viewer passes every probe check on all fourteen datasets, on the file inputs as well as the address, and the checks that matter did run;
  - each way of breaking the viewer listed below makes the check named for it fail. A check that cannot fail would prove nothing, so every break is applied to a
    copy of the viewer, is shown to change the file (the text to replace must occur exactly once), and is followed by a run that must fail that check;
  - every check id the probe emits is explained in docs/GUI_TEST_HOOKS.md.
What it does not prove: that the probe catches every way a screen can be wrong. The breaks are the ones its checks were written for. Chromium only.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import probe  # noqa: E402
import serve  # noqa: E402


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

VIEWER = REPO / "design" / "reference_viewer"
TOKENS = str(REPO / "design" / "tokens.css")
DOC = (REPO / "docs" / "GUI_TEST_HOOKS.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def datasets(tmp_path_factory):
    from reqin.cli import main
    d = tmp_path_factory.mktemp("probe_browser") / "ds"
    assert main(["make-datasets", str(d), "--size", "400"]) == 0
    return d


@pytest.fixture(scope="module")
def full_run(datasets):
    return probe.run(str(VIEWER), str(datasets), tokens=TOKENS)


def broken(tmp_path, file, old, new):
    """A copy of the viewer with one change. The text to replace must occur exactly once, so a break can never silently do nothing."""
    app = tmp_path / "app"
    shutil.copytree(VIEWER, app)
    p = app / file
    text = p.read_text(encoding="utf-8")
    assert text.count(old) == 1, "%r occurs %d times in %s" % (old[:60], text.count(old), file)
    p.write_text(text.replace(old, new), encoding="utf-8")
    return app


def failed_ids(R):
    return {(r["scope"].split(" ")[0], r["check"]) for r in R.failed}


# ------------------------------------------------------------------------------------------------ the reference viewer passes
def test_the_reference_viewer_passes_every_check_on_every_dataset(full_run):
    assert not full_run.failed, "\n".join("%s %s: %s" % (r["scope"], r["check"], r["detail"]) for r in full_run.failed[:10])
    ran = [r for r in full_run.rows if not r["skipped"]]
    assert len(ran) > 450


def test_the_checks_that_matter_really_ran(full_run):
    ran = {(r["scope"].split(" ")[0], r["check"]) for r in full_run.rows if not r["skipped"]}
    for needed in [("F9", "list.windowed"), ("F9", "perf.ready_within_30s"), ("F6", "detail.verified_toggle"), ("F6", "detail.show_in_source"), ("F13", "detail.other_fields"),
                   ("F14", "links.kinds_as_written"), ("F12", "empty.state"), ("F7", "facts.duplicate-ids"), ("F3", "rows.synthetic_badge"), ("F8", "rejected.list"),
                   ("F10", "layout.no_sideways_scroll@320"), ("F11", "sources.chips"), ("F1", "list.columns"), ("F2", "list.tree_depth"), ("style", "tokens.fonts_loaded"),
                   ("freshness", "canary.nothing_left_over"), ("freshness", "refuses.flipped")]:
        assert needed in ran, "%s did not run" % (needed,)


def test_every_check_id_the_probe_emits_is_explained_in_the_hooks_document(full_run):
    for cid in sorted({r["check"] for r in full_run.rows}):
        cid = cid.split("@")[0]
        prefix, _, suffix = cid.partition(".")
        explained = cid in DOC or ("`." + suffix + "`") in DOC or ("`" + prefix + ".*`") in DOC
        assert explained, "%s is not explained in docs/GUI_TEST_HOOKS.md" % cid


def test_the_viewer_also_works_through_the_file_inputs(datasets):
    R = probe.run(str(VIEWER), str(datasets), only=["f2", "f6", "f11", "f12"], load_via="files", extras=False, widths=(1440,))
    assert not R.failed, "\n".join("%s %s: %s" % (r["scope"], r["check"], r["detail"]) for r in R.failed[:6])
    assert len([r for r in R.rows if not r["skipped"]]) > 80


def test_the_command_line_exits_0_for_a_pass_and_1_for_a_failure(datasets, tmp_path):
    cmd = [sys.executable, str(REPO / "tools" / "gui_checks" / "probe.py"), "--datasets", str(datasets), "--only", "F1,F12", "--no-extras"]
    ok = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    assert ok.returncode == 0, "\n".join(l for l in ok.stdout.splitlines() if "FAIL" in l or l.startswith("         ")) + ok.stderr[-300:]
    assert "0 failed" in ok.stdout and "Not checked:" in ok.stdout
    app = broken(tmp_path, "viewer.js", '$("c-kept").textContent = kept;', '$("c-kept").textContent = 14;')
    out = tmp_path / "r.json"
    bad = subprocess.run(cmd + ["--app", str(app), "--json", str(out)], capture_output=True, text=True, timeout=300)
    assert bad.returncode == 1 and "FAIL" in bad.stdout and "counts.kept" in bad.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["format"] == "reqin-gui-probe/1" and any(c["check"] == "counts.kept" and not c["ok"] for c in data["checks"])


# ------------------------------------------------------------------------------------------------ the viewer broken on purpose
# (file, text that occurs once, what replaces it, datasets to run, expected failed (dataset, check) pairs that must all be present, run the extras?, widths, tokens?)
def run_broken(tmp_path, datasets, file, old, new, only, extras=False, widths=(1440,), tokens=None):
    app = broken(tmp_path, file, old, new)
    return probe.run(str(app), str(datasets), only=only, extras=extras, widths=widths, tokens=tokens)


def test_break_a_count_typed_in(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", '$("c-kept").textContent = kept;', '$("c-kept").textContent = 14;', ["f1", "f12"])
    assert {("F1", "counts.kept")} <= failed_ids(R) and ("F12", "counts.kept") in failed_ids(R)


def test_break_warnings_not_shown(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'S.warnings.forEach(function (t) { w.appendChild', 'S.warnings.slice(0, 0).forEach(function (t) { w.appendChild', ["f7", "f12"])
    assert {("F7", "warnings.verbatim"), ("F12", "warnings.verbatim")} <= failed_ids(R)


def test_break_link_kinds_renamed_or_dropped(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'Object.keys(count).sort().forEach(function (k) {',
                   'Object.keys(count).sort().filter(function (k) { return ["contain", "derive", "refine", "satisfy", "trace", "verify"].indexOf(k) >= 0; }).forEach(function (k) {', ["f14", "f2"])
    assert ("F14", "links.kinds_as_written") in failed_ids(R) and ("F2", "links.kinds_as_written") not in failed_ids(R)


def test_break_the_list_is_not_windowed(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", "OVERSCAN = 6", "OVERSCAN = 100000", ["f9"])
    assert ("F9", "list.windowed") in failed_ids(R)


def test_break_a_list_that_shows_only_its_first_page(tmp_path, datasets):
    """The screen is bound to the data for the first rows and then stops: the last-row check is what catches it."""
    R = run_broken(tmp_path, datasets, "viewer.js", "items: recs,", "items: recs.slice(0, 11),", ["f9", "f2"])
    assert ("F9", "list.last_rows") in failed_ids(R)


def test_break_the_empty_state_is_missing(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'show($("empty"), isEmpty); show($("body"), !isEmpty);', 'show($("empty"), false); show($("body"), true);', ["f12", "f1"])
    assert ("F12", "empty.state") in failed_ids(R) and ("F1", "empty.state") not in failed_ids(R)


def test_break_the_extracted_banner_never_shows(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'show($("verify"), !!fids.extracted);', 'show($("verify"), false);', ["f6", "f1"])
    assert ("F6", "banner.verify") in failed_ids(R)


def test_break_other_fields_are_truncated(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", "Object.keys(r.extra).map(", "Object.keys(r.extra).slice(0, 5).map(", ["f13"])
    assert ("F13", "detail.other_fields") in failed_ids(R)


def test_break_an_invented_id_looks_like_a_source_id(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'if (r.uid_synthetic) { uid.appendChild(', 'if (false) { uid.appendChild(', ["f3", "f1"])
    assert ("F3", "rows.synthetic_badge") in failed_ids(R)


def test_break_a_column_for_a_field_nobody_has(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'var columns = fieldsPresent.filter(function (k) { return STANDARD.indexOf(k) >= 0; }).slice(0, MAX_COLUMNS);',
                   'var columns = STANDARD.slice(0, MAX_COLUMNS);', ["f1", "f2"])
    assert ("F1", "list.columns") in failed_ids(R) and ("F2", "list.columns") not in failed_ids(R)


def test_break_a_changed_file_is_shown_instead_of_refused(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", 'if (!man.files[f] || got !== man.files[f].sha256)', 'if (false)', ["f1"], extras=True)
    assert ("freshness", "refuses.flipped") in failed_ids(R) and ("freshness", "refuses.no_manifest") not in failed_ids(R)


def test_break_a_screen_that_always_shows_the_same_typed_in_record(tmp_path, datasets):
    old = "d.requirements.forEach(function (r) { var o = { r: r,"
    new = ('[{mid: "m1", uid: "SYS-0001", text: "The unit shall start.", fields: {}, extra: {}, conf: {}, ref: {uri: "x.csv"}, fidelity: "tabular"}]'
           '.forEach(function (r) { var o = { r: r,')
    R = run_broken(tmp_path, datasets, "viewer.js", old, new, ["f2", "f13"], extras=True)
    ids = failed_ids(R)
    assert ("F2", "list.first_rows") in ids and ("F13", "list.first_rows") in ids and ("freshness", "canary.rows") in ids


def test_break_a_page_that_keeps_the_first_dataset_on_screen(tmp_path, datasets):
    """The second dataset chosen in the same page is not shown: the canary fails, and 'nothing left over' says why."""
    R = run_broken(tmp_path, datasets, "viewer.js", "  async function load(groups) {\n", "  async function load(groups) {\n    if (S) return;\n", ["f1"], extras=True)
    ids = failed_ids(R)
    assert ("freshness", "canary.rows") in ids or ("freshness", "canary.loads") in ids or ("freshness", "canary.nothing_left_over") in ids


def test_break_a_console_error(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.js", '    document.body.setAttribute("data-state", isEmpty ? "empty" : "ready");', '    console.error("boom");\n    document.body.setAttribute("data-state", isEmpty ? "empty" : "ready");', ["f1"])
    assert ("F1", "console.clean") in failed_ids(R)


def test_break_the_page_scrolls_sideways_on_a_phone(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.css", ".top, main { max-width: 1280px;", ".top, main { min-width: 700px; max-width: 1280px;", ["f1"], widths=(1440, 390))
    ids = failed_ids(R)
    assert ("F1", "layout.no_sideways_scroll@390") in ids and ("F1", "layout.no_sideways_scroll@1440") not in ids


def test_break_the_design_tokens_are_not_linked(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "index.html", '<link rel="stylesheet" href="tokens.css">', "", ["f1"], tokens=TOKENS, extras=False)
    assert {("style", "tokens.declared")} <= failed_ids(R)


def test_break_a_colour_that_is_not_a_token(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.css", ".counts dd { margin: 0;", ".counts dd { color: #2B6F77; margin: 0;", ["f1"], tokens=TOKENS)
    assert ("style", "tokens.colours_are_tokens") in failed_ids(R) and ("style", "tokens.declared") not in failed_ids(R)


def test_break_the_font_files_are_not_found(tmp_path, datasets):
    """The design's own tokens.css, but its font files are not where it says: text is drawn in a fallback. The usual cause of 'the CSS is off'."""
    app = tmp_path / "app"
    shutil.copytree(VIEWER, app)
    css = (REPO / "design" / "tokens.css").read_text(encoding="utf-8")
    assert css.count("public-sans-latin-400-normal.woff2") == 1
    (app / "tokens.css").write_text(css.replace("public-sans-latin-400-normal.woff2", "not-there.woff2"), encoding="utf-8")
    R = probe.run(str(app), str(datasets), only=["f1"], extras=False, widths=(1440,), tokens=TOKENS)
    ids = failed_ids(R)
    assert ("style", "tokens.fonts_loaded") in ids and ("style", "tokens.declared") not in ids


def test_break_a_font_that_is_not_loaded(tmp_path, datasets):
    R = run_broken(tmp_path, datasets, "viewer.css", "input, textarea, select { font-family: inherit;", 'body { font-family: "No Such Face", sans-serif; }\ninput, textarea, select { font-family: inherit;', ["f1"], tokens=TOKENS)
    ids = failed_ids(R)
    assert ("style", "tokens.fonts_are_tokens") in ids or ("style", "tokens.no_default_font") in ids


def test_break_a_warning_typed_in_instead_of_read_from_the_report(tmp_path, datasets):
    """A sentence typed into the screen shows on a dataset that has no warnings. The probe sees it; the source scan cannot know it is not data."""
    old = 'S.warnings.forEach(function (t) { w.appendChild(el("li", "", t, "warning")); });'
    new = 'w.appendChild(el("li", "", "2 links point outside this import (kept by UID)", "warning"));'
    R = run_broken(tmp_path, datasets, "viewer.js", old, new, ["f1", "f7"])
    assert ("F1", "warnings.verbatim") in failed_ids(R)
