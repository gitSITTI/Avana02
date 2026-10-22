#!/usr/bin/env python3
"""Check that a screen shows what a canonical dataset says, using a real browser and the fourteen test datasets.

    reqin make-datasets DIR --size 5000                              once: the fourteen datasets (F1-F14) and their index.json
    python3 tools/gui_checks/probe.py --app design/reference_viewer --datasets DIR
    python3 tools/gui_checks/probe.py --app my_app/ --datasets DIR --only F01,F08,F12 --json result.json

It starts the app on this machine (serve.py), opens each dataset the way a user would (?dataset=FOLDER, or --load-via files to use the file input),
and compares what is on the screen with what the dataset FILES say. It does not know the app's markup: it reads only the data-testid hooks in
docs/GUI_TEST_HOOKS.md, so one probe checks any app that carries them. For every dataset it checks, among others:

    the four counts and that they add up; every warning and filtered reason as written; the source and fidelity chips; the list total; the first rows, the
    last rows and a middle row, word for word (so a screen that shows the first page of a typed-in list fails); that a long list is windowed; the columns
    (a field no record has gets no column); the hierarchy cue; one detail panel per sample row (text, fields, confidence cue, other fields, links); the trace
    panel or its reason; link kinds as written; rejected reasons; the empty state; the extracted-records banner; invented-ID badges; no sideways scroll at
    1440, 900, 390 and 320 px wide; no console error, failed request or uncaught exception.

Once per run it also checks that the page uses the design tokens (declared variables present, fonts loaded, every painted colour a token colour), that a
dataset nobody has seen before (a canary written fresh for this run) is shown and that nothing from the previous dataset is left on the screen, and that a
dataset with a changed byte or a missing manifest is refused outright.

An app with more than one screen can also carry the navigation marks (docs/GUI_TEST_HOOKS.md, "Navigation marks"). Then the probe clicks through the menu and checks
that every item opens its own screen, that exactly that item is marked as the current one, that the breadcrumb and the page title follow, that the data is still on the
screen after the move, that the keyboard works, and that no count is invented. With --navigation design/navigation.json it also compares the menu, item by item, with
the map of the prototype. An app with no menu gets one 'not applicable' line for this.

What this does not do: judge whether the screen is attractive, accessible beyond what the hooks expose, or right for a real user. It proves that the screen is
bound to the dataset and that the listed behaviours hold for these fourteen shapes. Exit status 1 when any check fails. Needs Playwright and Chromium.
"""
from __future__ import annotations

import argparse
import collections
import copy
import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "design" / "ui_from_image" / "scripts"))
import serve  # noqa: E402

WIDTHS = (1440, 900, 390, 320)
STANDARD = ["status", "verification", "owner", "allocation", "baseline", "rationale"]
FILES = ("dataset.json", "requirements.jsonl", "links.jsonl", "rejected.jsonl", "report.json")
LIST_CAP = 200                                  # the most any one list of links or rejected records must show; a screen may show more
WINDOW_MAX_ROWS = 150                           # a list over WINDOW_OVER records may hold at most this many rows in the page
WINDOW_OVER = 300


def tid(name: str) -> str:
    return '[data-testid="%s"]' % name


# ---------------------------------------------------------------------------------------------------- the oracle: what the files say
def read_jsonl(p: Path) -> list:
    return [json.loads(l) for l in p.read_text(encoding="utf-8").split("\n") if l.strip()]


def oracle(folders: list[Path]) -> dict:
    reqs, links, rej, warns, filt, read = [], [], [], [], collections.Counter(), 0
    for f in folders:
        rep = json.loads((f / "report.json").read_text(encoding="utf-8"))
        rs = read_jsonl(f / "requirements.jsonl")
        for r in rs:
            r["_ds"] = str(f)
        reqs += rs
        links += read_jsonl(f / "links.jsonl")
        rej += read_jsonl(f / "rejected.jsonl")
        warns += rep.get("warnings") or []
        filt.update(rep.get("filtered_out") or {})
        read += rep.get("raw_records", len(rs) + len(read_jsonl(f / "rejected.jsonl")) + sum((rep.get("filtered_out") or {}).values()))
    by = {(r["_ds"], r["mid"]): r for r in reqs}
    depth = {}
    for r in reqs:
        d, cur, seen = 1, r, set()
        while cur.get("parent_mid") and (cur["_ds"], cur["parent_mid"]) in by and id(cur) not in seen:
            seen.add(id(cur))
            cur = by[(cur["_ds"], cur["parent_mid"])]
            d += 1
        depth[id(r)] = d
    fields = {k for r in reqs for k in r["fields"]}
    return {"reqs": reqs, "links": links, "rejected": rej, "warnings": warns, "filtered": dict(filt), "read": read, "depth": [depth[id(r)] for r in reqs],
            "hierarchy": any(r.get("parent_mid") for r in reqs), "max_depth": max(depth.values(), default=0),
            "fields_present": [k for k in STANDARD if k in fields] + sorted(fields - set(STANDARD)),
            "fidelities": sorted({r["fidelity"] for r in reqs}), "sources": sorted({r["ref"]["uri"] for r in reqs}),
            "synthetic": sum(1 for r in reqs if r["uid_synthetic"]), "duplicates": sum(1 for n in collections.Counter(r["uid"] for r in reqs).values() if n > 1),
            "outside": sum(1 for l in links if l["source_mid"] is None or l["target_mid"] is None),
            "low_conf": sum(1 for r in reqs for c in r["conf"].values() if c in ("Medium", "Low")),
            "link_kinds": dict(collections.Counter(l["kind"] for l in links))}


def plain(v):
    return v if isinstance(v, str) else json.dumps(v)


# ---------------------------------------------------------------------------------------------------- results
class Results:
    def __init__(self):
        self.rows: list[dict] = []

    def add(self, scope: str, cid: str, ok: bool, detail: str = "", skipped: bool = False):
        self.rows.append({"scope": scope, "check": cid, "ok": bool(ok), "detail": detail, "skipped": skipped})

    @property
    def failed(self):
        return [r for r in self.rows if not r["ok"] and not r["skipped"]]


# ---------------------------------------------------------------------------------------------------- driving the page
class Page:
    def __init__(self, browser, base: str):
        self.base = base
        self.pg = browser.new_page(viewport={"width": 1440, "height": 900})
        self.errors: list[str] = []
        self.pg.on("console", lambda m: self.errors.append("console %s: %s" % (m.type, m.text)) if m.type == "error" and "favicon" not in m.text else None)
        self.pg.on("pageerror", lambda e: self.errors.append("uncaught: %s" % e))
        self.pg.on("requestfailed", lambda r: self.errors.append("request failed: %s" % r.url) if not r.url.endswith("favicon.ico") else None)
        self.pg.on("response", lambda r: self.errors.append("HTTP %d: %s" % (r.status, r.url)) if r.status >= 400 and not r.url.endswith("favicon.ico") else None)

    def q(self, name):
        return self.pg.locator(tid(name))

    def count(self, name):
        return self.q(name).count()

    def visible(self, name):
        n = self.q(name)
        return n.count() > 0 and n.first.is_visible()

    def texts(self, name):
        return [t or "" for t in self.q(name).all_text_contents()]

    def text(self, name):
        n = self.q(name)
        return (n.first.text_content() or "") if n.count() else None

    def state(self):
        return self.pg.evaluate("document.body.getAttribute('data-state')")

    def open(self, rel_urls: list[str], timeout=30000):
        self.errors.clear()
        url = self.base + "/?" + "&".join("dataset=" + u for u in rel_urls)
        self.pg.goto(url + "&_=%s" % secrets.token_hex(3))
        return self.wait(timeout)

    def open_files(self, path: Path, timeout=30000):
        self.errors.clear()
        self.pg.goto(self.base + "/?_=%s" % secrets.token_hex(3))
        self.pg.locator(tid("dataset-folder-input")).set_input_files(str(path))
        return self.wait(timeout)

    def wait(self, timeout):
        t0 = time.time()
        try:
            self.pg.wait_for_function("['ready','empty','error'].includes(document.body.getAttribute('data-state'))", timeout=timeout)
        except Exception:
            return None
        return time.time() - t0

    def scroll_list(self, frac):
        self.pg.evaluate("f => { const l = document.querySelector('[data-testid=\"list\"]'); l.scrollTop = f * (l.scrollHeight - l.clientHeight); }", frac)
        self.pg.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
        self.pg.wait_for_timeout(60)

    def rows(self):
        """[(index or None, uid, text)] for the rows now in the page."""
        out = []
        for i in range(self.count("row")):
            row = self.q("row").nth(i)
            idx = row.get_attribute("data-index")
            out.append((int(idx) if idx is not None and idx.lstrip("-").isdigit() else None,
                        row.locator(tid("row-uid")).first.text_content(), row.locator(tid("row-text")).first.text_content()))
        return out


# ---------------------------------------------------------------------------------------------------- one dataset
def check_dataset(P: Page, R: Results, scope: str, o: dict, entry: dict | None, load_s: float | None, widths=WIDTHS):
    ok = lambda cid, cond, detail="", skipped=False: R.add(scope, cid, cond, detail if not cond or skipped else "", skipped)  # noqa: E731
    n = len(o["reqs"])
    st = P.state()
    ok("loads", load_s is not None and st in ("ready", "empty"), "state is %r after %s" % (st, "the wait" if load_s is None else "%.1fs" % load_s))
    if st not in ("ready", "empty"):
        return
    ok("console.clean", not P.errors, "; ".join(P.errors[:3]))

    if entry:
        ex = entry["expect"]
        mine = {"requirements": n, "links": len(o["links"]), "rejected": len(o["rejected"]), "filtered": sum(o["filtered"].values()), "raw_records": o["read"], "warnings": len(o["warnings"]),
                "hierarchy": o["hierarchy"], "max_depth": o["max_depth"], "synthetic_uids": o["synthetic"], "duplicate_uids": o["duplicates"], "fidelities": o["fidelities"],
                "sources": o["sources"], "link_kinds": sorted(o["link_kinds"])}
        diff = {k: (mine[k], ex.get(k)) for k in mine if k in ex and mine[k] != ex[k]}
        ok("oracle.agrees_with_index", not diff, "the probe's reading of the files differs from index.json: %s" % diff)

    # counts
    kept, rej, filt = n, len(o["rejected"]), sum(o["filtered"].values())
    for name, want in (("count-read", o["read"]), ("count-kept", kept), ("count-rejected", rej), ("count-filtered", filt)):
        got = (P.text(name) or "").strip()
        ok("counts." + name.split("-")[1], got == str(want), "%s shows %r, the files say %d" % (name, got, want))
    adds = o["read"] == kept + rej + filt
    ok("counts.reconcile", P.visible("count-mismatch") == (not adds), "read %d, kept %d, rejected %d, filtered %d: the screen %s say they do not add up" % (o["read"], kept, rej, filt, "should" if not adds else "should not"))

    # warnings and filtered reasons, as written
    shown = P.texts("warning")
    ok("warnings.verbatim", len(shown) == len(o["warnings"]) and all(w in s for w, s in zip(o["warnings"], shown)),
       "files say %r; screen shows %r" % (o["warnings"][:3], shown[:3]))
    fr = P.texts("filtered-reason")
    want_f = ["%s: %d" % (k, v) for k, v in o["filtered"].items()]
    ok("filtered.reasons", len(fr) == len(want_f) and all(w in s for w, s in zip(want_f, fr)), "files say %r; screen shows %r" % (want_f, fr))
    ok("sources.chips", sorted(set(t.strip() for t in P.texts("source-chip"))) == o["sources"], "files: %r; screen: %r" % (o["sources"], sorted(set(P.texts("source-chip")))))
    ok("fidelity.chips", sorted(set(t.strip() for t in P.texts("fidelity-chip"))) == o["fidelities"], "files: %r; screen: %r" % (o["fidelities"], sorted(set(P.texts("fidelity-chip")))))
    ok("banner.verify", P.visible("verify-banner") == ("extracted" in o["fidelities"]), "the extracted-records banner must show exactly when a record was extracted from prose (fidelities %r)" % o["fidelities"])
    for fact, want in (("synthetic-ids", o["synthetic"]), ("duplicate-ids", o["duplicates"]), ("outside-links", o["outside"])):
        got = P.pg.evaluate("f => { const e = document.querySelector('[data-testid=\"fact\"][data-fact=\"' + f + '\"]'); return e ? e.getAttribute('data-value') : null }", fact)
        ok("facts." + fact, (got is None and want == 0) or got == str(want), "files say %d; screen says %r" % (want, got))

    # empty state
    if n == 0:
        ok("empty.state", P.visible("empty-state") and not P.visible("list"), "an import with no requirements must show the empty state, not a blank list")
        ok("empty.warning_still_shown", (not o["warnings"]) or P.visible("warning"), "the warning that explains why nothing was found must stay on screen")
        ok("list.total", (P.text("row-total") or "").strip() in ("0", ""), "")
        _layout(P, ok, widths)
        return
    ok("empty.state_hidden", not P.visible("empty-state"), "the empty state must not show when there are requirements")

    # list
    ok("list.total", (P.text("row-total") or "").strip() == str(n), "row-total %r, files %d" % (P.text("row-total"), n))
    rows = P.rows()
    ok("list.first_rows", len(rows) >= min(n, 5) and all(rows[i][1] == o["reqs"][i]["uid"] and rows[i][2] == o["reqs"][i]["text"] for i in range(min(5, len(rows), n))),
       "first rows on screen %r; first records in the files %r" % ([(r[1], (r[2] or "")[:40]) for r in rows[:2]], [(r["uid"], r["text"][:40]) for r in o["reqs"][:2]]))
    if n > WINDOW_OVER:
        ok("list.windowed", len(rows) <= WINDOW_MAX_ROWS, "%d rows are in the page for a list of %d: it must hold only what is in view" % (len(rows), n))
    else:
        ok("list.windowed", True, "", skipped=True)
    P.scroll_list(1.0)
    rows = P.rows()
    last = o["reqs"][-1]
    ok("list.last_rows", bool(rows) and rows[-1][1] == last["uid"] and rows[-1][2] == last["text"], "last row on screen %r; last record in the files %r" % ((rows[-1][1], (rows[-1][2] or "")[:40]) if rows else None, (last["uid"], last["text"][:40])))
    if n > 12:
        P.scroll_list(0.5)
        rows = P.rows()
        mid_ok = bool(rows) and all(any(r["uid"] == u and r["text"] == t for r in o["reqs"]) for _, u, t in rows[:3])
        ok("list.middle_rows", mid_ok, "rows at the middle of the list are not records from the files: %r" % [(u, (t or '')[:30]) for _, u, t in rows[:2]])
    P.scroll_list(0.0)
    rows = P.rows()
    # columns
    cols = [(P.q("col-head").nth(i).get_attribute("data-field") or "") for i in range(P.count("col-head"))]
    ok("list.columns", all(c in o["fields_present"] for c in cols) and (o["fields_present"] or not cols), "columns %r but only %r exist in the data: a field nobody provides gets no column" % (cols, o["fields_present"]))
    # hierarchy
    ok("list.tree_cue", P.visible("tree") == o["hierarchy"], "hierarchy in the data: %s" % o["hierarchy"])
    if o["hierarchy"]:
        ok("list.tree_depth", (P.pg.evaluate("document.querySelector('[data-testid=\"tree\"]').getAttribute('data-depth')") or "") == str(o["max_depth"]), "deepest level in the data: %d" % o["max_depth"])
        bad = [i for i, r in enumerate(P.q("row").all()) if r.get_attribute("data-index") is not None and r.get_attribute("data-depth") != str(o["depth"][int(r.get_attribute("data-index"))])]
        ok("rows.depth", not bad, "rows %r show a depth that is not in the data" % bad[:5])
    # per-row cues, first 20 rows in view
    bad_s, bad_src = [], []
    for i in range(min(20, P.count("row"))):
        row = P.q("row").nth(i)
        idx = row.get_attribute("data-index")
        if idx is None:
            continue
        rec = o["reqs"][int(idx)]
        if (row.locator(tid("synthetic-badge")).count() > 0) != bool(rec["uid_synthetic"]):
            bad_s.append(rec["uid"])
        if (row.locator(tid("row-source")).first.text_content() if row.locator(tid("row-source")).count() else None) != rec["ref"]["uri"] or \
           (row.locator(tid("row-fidelity")).first.text_content() if row.locator(tid("row-fidelity")).count() else None) != rec["fidelity"]:
            bad_src.append(rec["uid"])
    ok("rows.synthetic_badge", not bad_s, "invented-ID badge wrong on %r" % bad_s[:5])
    ok("rows.source_and_fidelity", not bad_src, "source chip or fidelity cue wrong on %r" % bad_src[:5])
    # detail panel
    _detail(P, ok, o)
    # filter (optional hook)
    if P.count("filter-input"):
        word = o["reqs"][0]["uid"]
        P.q("filter-input").fill(word)
        P.pg.wait_for_timeout(150)
        want = sum(1 for r in o["reqs"] if word.lower() in (r["uid"] + "\n" + r["text"]).lower())
        ok("filter.total", (P.text("row-total") or "").strip() == str(want), "filtering by %r: files say %d, screen says %r" % (word, want, P.text("row-total")))
        P.q("filter-input").fill("")
        P.pg.wait_for_timeout(100)
    else:
        ok("filter.total", True, "", skipped=True)
    # trace panel
    nl = len(o["links"])
    ok("links.panel", P.visible("no-links") == (nl == 0) and P.visible("trace-panel") == (nl > 0), "links in the data: %d; no-links visible %s; trace-panel visible %s" % (nl, P.visible("no-links"), P.visible("trace-panel")))
    kinds = {(P.q("link-kind").nth(i).get_attribute("data-kind")): P.q("link-kind").nth(i).get_attribute("data-count") for i in range(P.count("link-kind"))}
    ok("links.kinds_as_written", kinds == {k: str(v) for k, v in o["link_kinds"].items()}, "files: %r; screen: %r" % (o["link_kinds"], kinds))
    if 0 < nl <= LIST_CAP:
        in_panel = lambda name: P.pg.locator('[data-testid="trace-panel"] ' + tid(name)).count()  # noqa: E731
        ok("links.listed", in_panel("link") == nl, "%d links in the data, %d listed in the trace panel" % (nl, in_panel("link")))
        ok("links.outside_marked", in_panel("link-outside") == o["outside"], "links with an end outside the import: %d in the data, %d marked" % (o["outside"], in_panel("link-outside")))
    # rejected
    nr = len(o["rejected"])
    if nr == 0:
        ok("rejected.list", P.count("rejected-item") == 0 or not P.visible("rejected-item"), "no records were rejected")
    elif nr <= LIST_CAP:
        reasons = collections.Counter(P.texts("rejected-reason"))
        want_r = collections.Counter(x["reason"] for x in o["rejected"])
        ok("rejected.list", reasons == want_r, "reasons in the data %r; on screen %r" % (dict(want_r), dict(reasons)))
    else:
        ok("rejected.list", P.count("rejected-item") >= 50 and P.visible("rejected-more"), "a long rejected list must show many and say there are more")
    _layout(P, ok, widths)


def _detail(P: Page, ok, o: dict):
    """Select a few rows (the first screen, then the last record) and compare the detail panel with the record in the files."""
    bad = collections.defaultdict(list)
    n = P.count("row")
    targets = [("top", i) for i in sorted({0, min(2, n - 1), min(4, n - 1)})] + [("bottom", None)]
    for where, i in targets:
        if where == "bottom":
            P.scroll_list(1.0)
            i = P.count("row") - 1
        row = P.q("row").nth(i)
        idx = row.get_attribute("data-index")
        rec = o["reqs"][int(idx)] if idx is not None else o["reqs"][i]
        row.click()
        P.pg.wait_for_timeout(80)
        if (P.text("detail-uid") or "").strip().split(" ")[0] != rec["uid"]:
            bad["uid"].append(rec["uid"])
        if P.text("detail-text") != rec["text"]:
            bad["text"].append(rec["uid"])
        for f in o["fields_present"]:
            if f not in STANDARD:
                continue
            cell = P.pg.locator('[data-testid="field-value"][data-field="%s"]' % f)
            have = f in rec["fields"]
            if cell.count() != 1:
                bad["field"].append((rec["uid"], f, "missing"))
                continue
            got = cell.text_content() or ""
            if have and plain(rec["fields"][f]) not in got:
                bad["field"].append((rec["uid"], f, got[:30]))
            if not have and "not provided" not in got.lower():
                bad["field"].append((rec["uid"], f, "should say the source does not provide it"))
            if have and (cell.locator(tid("confidence-cue")).count() > 0) != (rec["conf"].get(f) in ("Medium", "Low")):
                bad["confidence"].append((rec["uid"], f))
        want = {k: plain(v) for k, v in rec["fields"].items() if k not in STANDARD}
        want.update({k: plain(v) for k, v in rec["extra"].items()})
        got = {P.q("other-field-name").nth(j).text_content(): P.q("other-field-value").nth(j).text_content() for j in range(P.count("other-field-name"))}
        if got != want:
            bad["other"].append((rec["uid"], "missing %r; different %r" % (sorted(set(want) - set(got))[:3], [k for k in want if k in got and got[k] != want[k]][:3])))
        mine = [l for l in o["links"] if rec["mid"] in (l["source_mid"], l["target_mid"])]
        shown = P.pg.locator('[data-testid="detail"] [data-testid="link"]').count()
        if len(mine) <= LIST_CAP and shown != len(mine):
            bad["links"].append((rec["uid"], "%d in the data, %d shown" % (len(mine), shown)))
        if rec["fidelity"] == "extracted" and where == "top":
            P.q("show-source").click()
            loc = P.text("source-location") or ""
            if rec["ref"]["locator"] not in loc:
                bad["locator"].append(rec["uid"])
            m = re.match(r"^p(\d+):blk(\d+)$", rec["ref"]["locator"])
            pos = P.text("source-position") or ""
            if m and ("page %s" % m.group(1) not in pos or "block %s" % m.group(2) not in pos):
                bad["position"].append(rec["uid"])
            if P.count("mark-verified"):
                before = P.text("verified-state")
                P.q("mark-verified").click()
                after = P.text("verified-state")
                badge = P.q("row").nth(i).locator(tid("verify-badge"))
                if before == after or not badge.count() or (badge.first.text_content() or "").strip() != "verified":
                    bad["verify_toggle"].append(rec["uid"])
                P.q("mark-verified").click()
            else:
                bad["verify_toggle"].append(rec["uid"])
    ok("detail.uid_and_text", not bad["uid"] and not bad["text"], "wrong uid on %r; wrong text on %r" % (bad["uid"], bad["text"]))
    ok("detail.fields", not bad["field"], "%r" % bad["field"][:3])
    ok("detail.confidence_cue", not bad["confidence"], "%r" % bad["confidence"][:3])
    ok("detail.other_fields", not bad["other"], "%r" % bad["other"][:2])
    ok("detail.links", not bad["links"], "the links of a record are not all shown: %r" % bad["links"][:3])
    if any(r["fidelity"] == "extracted" for r in o["reqs"]):
        ok("detail.show_in_source", not bad["locator"] and not bad["position"], "locator not shown for %r; page and block not shown for %r" % (bad["locator"], bad["position"]))
        ok("detail.verified_toggle", not bad["verify_toggle"], "marking a record verified did not change its state and its badge: %r" % bad["verify_toggle"])
    else:
        ok("detail.show_in_source", True, "", skipped=True)
        ok("detail.verified_toggle", True, "", skipped=True)


def _layout(P: Page, ok, widths):
    for w in widths:
        P.pg.set_viewport_size({"width": w, "height": 900})
        P.pg.wait_for_timeout(120)
        sw = P.pg.evaluate("[document.documentElement.scrollWidth, window.innerWidth]")
        ok("layout.no_sideways_scroll@%d" % w, sw[0] <= sw[1], "the page is %dpx wide in a %dpx window" % (sw[0], sw[1]))
    P.pg.set_viewport_size({"width": 1440, "height": 900})


# ---------------------------------------------------------------------------------------------------- tokens and fonts
PAINT_JS = """() => {
  const colours = {}, fonts = {}, used = {}, bad = [];
  const add = (rgb, where) => { if (!rgb || rgb === 'rgba(0, 0, 0, 0)' || rgb === 'transparent') return; (colours[rgb] = colours[rgb] || {n: 0, where: where}).n++; };
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect(); if (r.width === 0 || r.height === 0) continue;
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const hasText = Array.from(el.childNodes).some(n => n.nodeType === 3 && n.textContent.trim()) || ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName);
    if (hasText) { add(cs.color, el.tagName.toLowerCase() + ' text'); const f = cs.fontFamily.split(',')[0].trim().replace(/^["']|["']$/g, ''); fonts[f] = (fonts[f] || 0) + 1; const k = f + '|' + cs.fontWeight + '|' + cs.fontStyle; used[k] = (used[k] || 0) + 1; }
    add(cs.backgroundColor, el.tagName.toLowerCase() + ' background');
    for (const side of ['Top', 'Right', 'Bottom', 'Left']) if (parseFloat(cs['border' + side + 'Width']) > 0 && cs['border' + side + 'Style'] !== 'none') add(cs['border' + side + 'Color'], el.tagName.toLowerCase() + ' border');
  }
  const root = getComputedStyle(document.documentElement);
  const declared = {};
  for (const n of arguments_names) declared[n] = root.getPropertyValue(n).trim();
  const faces = Array.from(document.fonts).map(f => ({family: f.family.replace(/^["']|["']$/g, ''), weight: String(f.weight), style: f.style, status: f.status}));
  const loaded = faces.filter(f => f.status === 'loaded').map(f => f.family);
  return {colours, fonts, used, faces, declared, loaded, body: getComputedStyle(document.body).fontFamily};
}"""


# ---------------------------------------------------------------------------------------------------- the menu and the screens it leads to
_JS_VISIBLE = "const vis = e => { const r = e.getBoundingClientRect(); const cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };"
_JS_MENU = """() => { %s
  const q = s => Array.from(document.querySelectorAll('[data-testid="' + s + '"]'));
  return q('nav-item').map(e => {
    const g = e.closest('[data-testid="nav-group"]'); const c = e.querySelector('[data-testid="nav-count"]'); const r = e.getBoundingClientRect();
    const copy = e.cloneNode(true); copy.querySelectorAll('[data-testid="nav-count"]').forEach(x => x.remove());
    return {screen: e.getAttribute('data-screen'), label: (copy.textContent || '').replace(/\\s+/g, ' ').trim(), count: c ? (c.textContent || '').trim() : null,
            current: e.getAttribute('aria-current'), group: g ? g.getAttribute('data-group') : null, tag: e.tagName.toLowerCase(), href: e.getAttribute('href'),
            visible: vis(e), left: r.left, right: r.right};
  }); }""" % _JS_VISIBLE
_JS_SCREEN = """() => { %s
  const shown = Array.from(document.querySelectorAll('[data-testid="screen"]')).filter(vis);
  const crumb = document.querySelector('[data-testid="breadcrumb"]');
  return {visible: shown.map(e => e.getAttribute('data-screen')), text: shown.length ? (shown[0].innerText || '').trim() : '', breadcrumb: crumb ? (crumb.textContent || '').trim() : null,
          title: document.title, state: document.body.getAttribute('data-state')}; }""" % _JS_VISIBLE
_JS_LANDMARK = """() => { const e = document.querySelector('[data-testid="nav"]'); if (!e) return null;
  let name = e.getAttribute('aria-label') || '';
  const by = e.getAttribute('aria-labelledby');
  if (!name && by) name = by.split(/\\s+/).map(i => { const x = document.getElementById(i); return x ? (x.textContent || '').trim() : ''; }).join(' ').trim();
  return {tag: e.tagName.toLowerCase(), role: e.getAttribute('role'), name: name.trim()}; }"""


def expected_menu(nav: dict) -> dict:
    """What design/navigation.json says the side bar holds: the groups with their items, the screen titles, the title suffix, whether the narrow layout shows every item."""
    sb = (nav.get("shell") or {}).get("side_bar") or {}
    screens = {s["id"]: s for s in nav.get("screens", [])}
    groups = [{"id": g["id"], "heading": g.get("heading"), "collapsible": bool(g.get("collapsible")), "default_open": bool(g.get("default_open")),
               "items": [{"screen": i["screen"], "label": i["label"], "count": "count" in i, "title": screens[i["screen"]]["title"]} for i in g.get("items", [])]} for g in sb.get("groups", [])]
    suffix = ((nav.get("shell") or {}).get("page_title") or {}).get("document_title", "").replace("<screen title>", "")
    narrow = (sb.get("layout") or {}).get("narrow") or {}
    return {"label": sb.get("label"), "groups": groups, "items": [i for g in groups for i in g["items"]], "suffix": suffix,
            "narrow_width": int(str(narrow["at_most_width"]).replace("px", "")) if narrow.get("at_most_width") else None, "narrow_all_visible": bool(narrow.get("all_items_visible")),
            "workspace": {s["id"] for s in nav.get("screens", []) if s.get("kind") == "workspace"}}


def check_navigation(P: Page, R: Results, nav: dict | None = None, scope: str = "navigation"):
    """The menu of an app with more than one screen. Reads only the navigation marks. With the map (design/navigation.json) the menu is also compared with it."""
    from playwright.sync_api import TimeoutError as PWTimeout
    ok = lambda cid, cond, detail="", skipped=False: R.add(scope, cid, cond, detail if not cond or skipped else "", skipped)  # noqa: E731
    P.pg.set_viewport_size({"width": 1440, "height": 900})
    if P.count("nav") == 0:
        ok("nav.present", True, "no element carries the nav mark: a one-screen app has no menu to check", skipped=True)
        return
    exp = expected_menu(nav) if nav else None
    ok("nav.present", P.count("nav") == 1, "%d elements carry the nav mark; there must be exactly one" % P.count("nav"))
    lm = P.pg.evaluate(_JS_LANDMARK)
    why = []
    if lm["tag"] != "nav" and lm["role"] != "navigation":
        why.append("it is a <%s>, not a <nav> and without role=navigation, so a screen reader does not list it as navigation" % lm["tag"])
    if not lm["name"]:
        why.append("it has no accessible name (aria-label)")
    elif exp and lm["name"] != exp["label"]:
        why.append("its name is %r; the map says %r" % (lm["name"], exp["label"]))
    ok("nav.landmark", not why, "; ".join(why))

    items = P.pg.evaluate(_JS_MENU)
    shown = [(i["screen"], i["label"]) for i in items]
    ids = [i["screen"] for i in items]
    problems = []
    if len(items) < 2:
        problems.append("%d nav-item marks; a menu has at least two" % len(items))
    if any(not x for x in ids):
        problems.append("a nav-item has no data-screen")
    if len(set(ids)) != len(ids):
        problems.append("two menu items name the same screen: %s" % sorted({x for x in ids if ids.count(x) > 1}))
    if exp:
        want = [(i["screen"], i["label"]) for i in exp["items"]]
        if shown != want:
            problems.append("the menu holds %s; the map says %s (the order counts)" % (shown, want))
    ok("nav.items_listed", not problems, "; ".join(problems))
    if exp:
        got_groups = [(g, [i["screen"] for i in items if i["group"] == g]) for g in dict.fromkeys(i["group"] for i in items)]
        want_groups = [(g["id"], [i["screen"] for i in g["items"]]) for g in exp["groups"]]
        ok("nav.groups", got_groups == want_groups, "groups on the page %s; in the map %s" % (got_groups, want_groups))
        closed = [i["screen"] for g in exp["groups"] if not g["collapsible"] or g["default_open"] for i in g["items"] if i["screen"] in ids and not next(x for x in items if x["screen"] == i["screen"])["visible"]]
        ok("nav.default_open_visible", not closed, "items in a group that starts open (or never folds) are not visible: %s" % closed)
    else:
        ok("nav.groups", True, "no --navigation map, so the groups are not compared", skipped=True)
        ok("nav.default_open_visible", True, "no --navigation map", skipped=True)
    bad = [i["screen"] for i in items if not (i["tag"] == "button" or (i["tag"] == "a" and i["href"]))]
    ok("nav.items_are_controls", not bad, "menu items that are not a <button> or an <a href>, so the keyboard cannot reach them: %s" % bad)

    # where the app starts
    st = P.pg.evaluate(_JS_SCREEN)
    cur = [i["screen"] for i in items if i["current"] == "page"]
    why = []
    if len(st["visible"]) != 1:
        why.append("%d screen marks are visible at the start; exactly one must be" % len(st["visible"]))
    if len(cur) != 1:
        why.append("%d menu items carry aria-current=page at the start; exactly one must" % len(cur))
    elif len(st["visible"]) == 1 and cur[0] != st["visible"][0]:
        why.append("the screen showing is %r and the current menu item is %r" % (st["visible"][0], cur[0]))
    if exp and len(st["visible"]) == 1 and st["visible"][0] not in exp["workspace"]:
        why.append("the app starts on %r, which the map does not list as a screen with the menu" % st["visible"][0])
    ok("nav.starts_on_current_screen", not why, "; ".join(why))
    state_before, first_text, errors_before = st["state"], st["text"], len(P.errors)

    # follow every item
    titles = {i["screen"]: i["title"] for i in exp["items"]} if exp else {i["screen"]: i["label"] for i in items}
    wrong_screen, wrong_current, wrong_crumb, wrong_title, same_text, hung = [], [], [], [], [], []
    seen_crumb = seen_title = False
    previous, previous_id = st["text"], (st["visible"][0] if len(st["visible"]) == 1 else None)
    for i in items:
        sid = i["screen"]
        try:
            P.pg.locator(tid("nav-item") + '[data-screen="%s"]' % sid).first.click(timeout=3000)
            P.pg.wait_for_function("s => { const e = Array.from(document.querySelectorAll('[data-testid=\"screen\"]')).filter(x => { const r = x.getBoundingClientRect(); return r.width > 0 && r.height > 0; });"
                                   " return e.length === 1 && e[0].getAttribute('data-screen') === s; }", arg=sid, timeout=3000)
        except PWTimeout:
            hung.append(sid)
        P.pg.wait_for_timeout(120)
        now = P.pg.evaluate(_JS_SCREEN)
        menu = P.pg.evaluate(_JS_MENU)
        if sid in hung:
            wrong_screen.append("%s -> %s" % (sid, now["visible"] or "no screen"))
            continue
        marked = [m["screen"] for m in menu if m["current"] == "page"]
        if marked != [sid]:
            wrong_current.append("%s -> %s" % (sid, marked or "nothing"))
        if now["breadcrumb"] is not None:
            seen_crumb = True
            if titles[sid] not in now["breadcrumb"]:
                wrong_crumb.append("%s: %r lacks %r" % (sid, now["breadcrumb"], titles[sid]))
        if exp and exp["suffix"]:
            seen_title = True
            if now["title"] != titles[sid] + exp["suffix"]:
                wrong_title.append("%s: %r, the map says %r" % (sid, now["title"], titles[sid] + exp["suffix"]))
        if now["text"] == previous and sid != previous_id:
            same_text.append(sid)
        previous, previous_id = now["text"], sid
    ok("nav.each_item_opens_its_screen", not wrong_screen, "after a click the screen showing was not the item's: %s" % wrong_screen[:5])
    ok("nav.each_item_marks_itself_current", not wrong_current, "after a click, the item marked aria-current=page was not the one clicked: %s" % wrong_current[:5])
    ok("nav.each_screen_has_its_own_content", not same_text, "these screens show exactly what the screen before them showed, so the menu changes the highlight and not the page: %s" % same_text[:5])
    if seen_crumb:
        ok("nav.breadcrumb_follows", not wrong_crumb, "; ".join(wrong_crumb[:3]))
    else:
        ok("nav.breadcrumb_follows", True, "no breadcrumb mark", skipped=True)
    if seen_title:
        ok("nav.page_title_follows", not wrong_title, "; ".join(wrong_title[:3]))
    else:
        ok("nav.page_title_follows", True, "no --navigation map, or it has no page title rule", skipped=True)
    end = P.pg.evaluate(_JS_SCREEN)
    ok("nav.keeps_the_dataset", end["state"] == state_before and len(P.errors) == errors_before,
       "after the clicks the page state is %r (was %r) and %d new errors appeared: %s" % (end["state"], state_before, len(P.errors) - errors_before, "; ".join(P.errors[errors_before:errors_before + 2])))
    home = st["visible"][0] if len(st["visible"]) == 1 else None
    if home in ids and not hung:
        try:
            P.pg.locator(tid("nav-item") + '[data-screen="%s"]' % home).first.click(timeout=3000)
        except PWTimeout:
            pass
        P.pg.wait_for_timeout(200)
        back = P.pg.evaluate(_JS_SCREEN)
        ok("nav.round_trip", back["visible"] == [home] and back["text"] == first_text, "coming back to %r after visiting every other screen shows %s than it did the first time" % (home, "another screen" if back["visible"] != [home] else "different content"))
    else:
        ok("nav.round_trip", True, "the screen the app starts on is not a menu item, or an item did not open (see above)", skipped=True)

    # the keyboard
    menu = P.pg.evaluate(_JS_MENU)
    target = next((m["screen"] for m in reversed(menu) if m["current"] != "page"), None)
    if target and not hung:
        loc = P.pg.locator(tid("nav-item") + '[data-screen="%s"]' % target).first
        loc.focus()
        focused = P.pg.evaluate("document.activeElement && document.activeElement.closest('[data-testid=\"nav-item\"]') ? document.activeElement.closest('[data-testid=\"nav-item\"]').getAttribute('data-screen') : null")
        P.pg.keyboard.press("Enter")
        P.pg.wait_for_timeout(250)
        after = P.pg.evaluate(_JS_SCREEN)
        ok("nav.keyboard", focused == target and after["visible"] == [target], "focus went to %r (wanted %r); after Enter the screen showing is %s" % (focused, target, after["visible"]))
    else:
        ok("nav.keyboard", True, "no item to try", skipped=True)

    # counts
    menu = P.pg.evaluate(_JS_MENU)
    why = []
    for m in menu:
        if m["count"] is None:
            continue
        if not re.fullmatch(r"[0-9]+", m["count"]):
            why.append("%s shows %r, which is not a whole number" % (m["screen"], m["count"]))
        elif m["count"] == "0":
            why.append("%s shows 0: a menu count that nothing produces is left out, not shown as 0" % m["screen"])
        if exp and not next((x for x in exp["items"] if x["screen"] == m["screen"]), {"count": False})["count"]:
            why.append("%s carries a count the map does not give it" % m["screen"])
    ok("nav.count_not_invented", not why, "; ".join(why))

    # a narrow window
    if exp and exp["narrow_all_visible"] and exp["narrow_width"]:
        w = min(390, exp["narrow_width"])
        P.pg.set_viewport_size({"width": w, "height": 800})
        P.pg.wait_for_timeout(150)
        cut = [m["screen"] for m in P.pg.evaluate(_JS_MENU) if not m["visible"] or m["left"] < -1 or m["right"] > w + 1]
        ok("nav.narrow_shows_every_item@%d" % w, not cut, "at %d px wide these items are hidden or cut off: %s" % (w, cut))
        P.pg.set_viewport_size({"width": 1440, "height": 900})
    else:
        ok("nav.narrow_shows_every_item", True, "the map does not say the narrow layout shows every item", skipped=True)


def check_tokens(P: Page, R: Results, tokens_css: Path):
    import colour as C
    import conform as CF
    scope = "style"
    ok = lambda cid, cond, detail="", skipped=False: R.add(scope, cid, cond, detail if not cond else "", skipped)  # noqa: E731
    rows = CF.load_target(str(tokens_css))
    text = re.sub(r"/\*.*?\*/", "", tokens_css.read_text(encoding="utf-8"), flags=re.S)
    colour_vars = {name: v.strip() for name, v in re.findall(r"(--[\w-]+)\s*:\s*([^;{}]+)", text) if (C.parse_css(v.strip()) or (None, 0))[1] == 1.0 and v.strip().startswith("#")}
    families = sorted(set(re.findall(r"font-family:'([^']+)'", text)))
    js = PAINT_JS.replace("arguments_names", json.dumps(sorted(colour_vars)))
    # a web font loads when text that needs it is first laid out, so wait until none is still on its way before asking which ones loaded
    P.pg.evaluate("async () => { await document.fonts.ready; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); await document.fonts.ready; }")
    got = P.pg.evaluate(js)
    missing = [n for n in colour_vars if got["declared"].get(n, "").lower() != colour_vars[n].lower()]
    ok("tokens.declared", not missing, "the page does not carry the design tokens (%d of %d variables missing or different, e.g. %s): link tokens.css" % (len(missing), len(colour_vars), missing[:3]))
    off = []
    for rgb, info in got["colours"].items():
        p = C.parse_css(rgb)
        if not p or p[1] != 1.0:
            continue
        best = min(C.delta_e(p[0], r["hex"]) for r in rows)
        if best > CF.STRICT_USE:
            off.append("%s (%s, %d uses, %.1f from the nearest token)" % (p[0], info["where"], info["n"], best))
    ok("tokens.colours_are_tokens", not off, "colours on screen that are not a token colour: %s" % "; ".join(off[:6]))
    used = [f for f in got["fonts"]]
    unknown = [f for f in used if f not in families and f not in ("sans-serif", "serif", "monospace")]
    ok("tokens.fonts_are_tokens", not unknown, "fonts drawn that the design does not name: %s" % unknown[:4])
    not_loaded = []
    for key in got["used"]:
        fam, wt, st = key.split("|")
        if fam not in families:
            continue
        exact = [f for f in got["faces"] if f["family"] == fam and f["weight"] == wt and f["style"] == st]
        if exact and not any(f["status"] == "loaded" for f in exact):
            not_loaded.append("%s %s %s (%s)" % (fam, wt, st, exact[0]["status"]))
        elif not exact and fam not in got["loaded"]:
            not_loaded.append("%s (no face loaded)" % fam)
    ok("tokens.fonts_loaded", not not_loaded, "fonts the design names that did not load, so another font was drawn instead (the usual cause of 'the CSS is off'): %s" % not_loaded)
    generic = [f for f in used if f in ("sans-serif", "serif", "monospace", "Times New Roman", "Arial")]
    ok("tokens.no_default_font", not generic, "text is drawn in a browser default font: %s" % generic)


# ---------------------------------------------------------------------------------------------------- canary and corruption
def make_canary(dest: Path, tag: str, template_record: dict) -> dict:
    sys.path.insert(0, str(REPO / "reqin" / "src"))
    from reqin.dataset import write_dataset_dicts
    recs = []
    for i in range(3):
        r = copy.deepcopy(template_record)
        r.update({"mid": "m_canary%s%d" % (tag, i), "uid": "CANARY-%s-%d" % (tag.upper(), i), "text": "Canary %s%d: the beacon %s shall blink %d times." % (tag, i, tag[::-1], 7 + i),
                  "norm_text": "canary", "fingerprint": "f%s%d" % (tag, i), "parent_mid": None, "uid_synthetic": False, "fidelity": "tabular",
                  "fields": {"status": "Canary status %s" % tag}, "conf": {"status": "Exact", "text": "High", "uid": "Exact"}, "extra": {"Canary key %s" % tag: "canary value %d" % i},
                  "ref": {"adapter": "canary", "container": "c", "locator": "R%d" % i, "revision": "r1", "uri": "canary-%s.csv" % tag}})
        recs.append(r)
    links = [{"kind": "canary-kind-%s" % tag, "ref": recs[0]["ref"], "source_mid": recs[0]["mid"], "source_uid": recs[0]["uid"], "target_mid": recs[1]["mid"], "target_uid": recs[1]["uid"]}]
    rejected = [{"fields": {"ID": "X"}, "reason": "canary reason %s" % tag, "ref": recs[0]["ref"]}]
    report = {"adapter": "canary", "confidence": {"status": {"Exact": 3}, "text": {"High": 3}, "uid": {"Exact": 3}}, "coverage": {"status": 3, "text": 3, "uid": 3}, "fidelity": "tabular", "filtered_out": {}, "invariant_ok": True, "links": 1, "profile": "canary", "profile_proposed": False,
              "raw_records": 4, "rejected": 1, "requirements": 3, "revision": "r1", "unclaimed_fields": [], "warnings": ["canary warning %s" % tag]}
    write_dataset_dicts(recs, links, rejected, report, dest)
    return {"tag": tag, "recs": recs}


def check_canary_and_corruption(P: Page, R: Results, app: Path, folder_for_state: Path, template: dict):
    """A dataset written fresh for this run must be shown; loading it into a page that already shows another dataset must leave nothing of the other; a damaged dataset is refused."""
    scope = "freshness"
    ok = lambda cid, cond, detail="": R.add(scope, cid, cond, detail if not cond else "")  # noqa: E731
    tag = secrets.token_hex(3)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        make_canary(td / "canary", tag, template)
        for sub in ("normal", "flipped", "no_manifest", "wrong_count"):
            shutil.copytree(folder_for_state, td / sub)
        p = td / "flipped" / "requirements.jsonl"                      # one byte changed, same length: only the checksum can tell
        data = bytearray(p.read_bytes())
        i = data.index(b"shall") if b"shall" in data else 10
        data[i] = ord("S") if data[i] != ord("S") else ord("s")
        p.write_bytes(bytes(data))
        (td / "no_manifest" / "dataset.json").unlink()
        m = json.loads((td / "wrong_count" / "dataset.json").read_text(encoding="utf-8"))
        m["counts"]["requirements"] += 1
        (td / "wrong_count" / "dataset.json").write_text(json.dumps(m), encoding="utf-8")
        first = read_jsonl(folder_for_state / "requirements.jsonl")[0]["uid"]
        with serve.serving(app, td) as base:
            Q = Page(P.pg.context.browser, base)
            Q.open(["datasets/normal"])
            ok("canary.first_dataset_shows", first in [r[1] for r in Q.rows()], "the ordinary dataset did not show before the canary was loaded")
            if Q.count("dataset-folder-input"):                         # a second dataset into the same page, through the folder input
                Q.errors.clear()
                Q.pg.locator(tid("dataset-folder-input")).set_input_files(str(td / "canary"))
                Q.wait(15000)
                ok("canary.loads", Q.state() == "ready", "state %r after choosing the canary folder" % Q.state())
                text = Q.pg.evaluate("document.body.innerText")
                ok("canary.nothing_left_over", first not in text, "%r from the previous dataset is still on the screen" % first)
            else:
                Q.open(["datasets/canary"])
                ok("canary.loads", Q.state() == "ready", "state %r" % Q.state())
                ok("canary.nothing_left_over", True)
            rows = Q.rows()
            ok("canary.rows", [r[1] for r in rows] == ["CANARY-%s-%d" % (tag.upper(), i) for i in range(3)], "rows on screen: %r" % [r[1] for r in rows])
            ok("canary.text", [r[2] for r in rows] == [x["text"] for x in make_canary_texts(tag)], "the statements on screen are not the ones in the files")
            ok("canary.warning", any("canary warning %s" % tag in t for t in Q.texts("warning")), "the warning written in the file is not on screen")
            ok("canary.link_kind", ("canary-kind-%s" % tag) in [Q.q("link-kind").nth(j).get_attribute("data-kind") for j in range(Q.count("link-kind"))], "the link kind written in the file is not on screen")
            ok("canary.rejected_reason", any("canary reason %s" % tag in t for t in Q.texts("rejected-reason")), "the rejected reason written in the file is not on screen")
            ok("canary.counts", (Q.text("count-kept") or "").strip() == "3" and (Q.text("count-rejected") or "").strip() == "1" and (Q.text("count-read") or "").strip() == "4",
               "read %r, kept %r, rejected %r (files: 4, 3, 1)" % (Q.text("count-read"), Q.text("count-kept"), Q.text("count-rejected")))
            Q.q("row").first.click()
            Q.pg.wait_for_timeout(80)
            ok("canary.other_field", ("Canary key %s" % tag) in Q.texts("other-field-name"), "the field name written in the file is not on screen")
            for name, why in (("flipped", "one byte changed, same length"), ("no_manifest", "dataset.json missing"), ("wrong_count", "the manifest counts a record that is not there")):
                Q.open(["datasets/" + name])
                refused = Q.state() == "error" and Q.visible("dataset-error") and Q.count("row") == 0 and not Q.visible("count-kept") and Q.count("dataset-problem") >= 1
                ok("refuses." + name, refused, "%s: the screen must refuse the whole dataset and show nothing from it (state %r, rows %d)" % (why, Q.state(), Q.count("row")))
            Q.pg.close()


def make_canary_texts(tag: str) -> list:
    return [{"text": "Canary %s%d: the beacon %s shall blink %d times." % (tag, i, tag[::-1], 7 + i)} for i in range(3)]


# ---------------------------------------------------------------------------------------------------- main
def run(app: str, datasets: str, only: list[str] | None = None, load_via: str = "url", tokens: str | None = None, widths=WIDTHS, extras: bool = True, navigation: str | None = None) -> Results:
    from playwright.sync_api import sync_playwright
    root = Path(datasets).resolve()
    index = json.loads((root / "index.json").read_text(encoding="utf-8"))
    entries = [e for e in index["datasets"] if not only or any(o == e["id"].lower() or any(f.lower() == o or f.lower().startswith(o + "_") for f in e["folders"]) for o in only)]
    if not entries:
        raise SystemExit("no dataset in %s matches %s" % (datasets, ",".join(only or [])))
    R = Results()
    with serve.serving(app, root) as base, sync_playwright() as pw:
        browser = pw.chromium.launch()
        P = Page(browser, base)
        first_tokens_done = False
        for e in entries:
            folders = [root / f for f in e["folders"]]
            o = oracle(folders)
            scope = "%s %s" % (e["id"], e["name"])
            if load_via == "files":
                parent = folders[0].parent if len(folders) > 1 else folders[0]
                secs = P.open_files(parent)
            else:
                secs = P.open(["datasets/" + f for f in e["folders"]])
            check_dataset(P, R, scope, o, e, secs, widths)
            if e["id"] == "F9" and secs is not None:
                R.add(scope, "perf.ready_within_30s", secs < 30, "ready after %.1fs for %d requirements" % (secs, len(o["reqs"])))
            if tokens and not first_tokens_done and P.state() == "ready":
                P.open(["datasets/" + e["folders"][0]])
                check_tokens(P, R, Path(tokens))
                first_tokens_done = True
        nav = json.loads(Path(navigation).read_text(encoding="utf-8")) if navigation else None
        P.pg.set_viewport_size({"width": 1440, "height": 900})
        P.open(["datasets/" + f for f in entries[0]["folders"]])
        if P.state() == "ready":
            check_navigation(P, R, nav)
        if extras:
            template = None
            for e in entries:
                rs = read_jsonl(root / e["folders"][0] / "requirements.jsonl")
                if rs:
                    template, state_folder = rs[0], root / e["folders"][0]
                    break
            if template is not None:
                check_canary_and_corruption(P, R, Path(app), state_folder, template)
        browser.close()
    return R


def report(R: Results) -> int:
    scope = None
    for r in R.rows:
        if r["scope"] != scope:
            scope = r["scope"]
            print("\n" + scope)
        mark = "-" if r["skipped"] else ("ok" if r["ok"] else "FAIL")
        line = "  %-4s %s" % (mark, r["check"])
        if r["skipped"] and r["detail"]:
            line += "  (not applicable: %s)" % r["detail"]
        if not r["ok"] and not r["skipped"]:
            line += "\n         " + r["detail"]
        print(line)
    total = [r for r in R.rows if not r["skipped"]]
    print("\n%d checks run, %d passed, %d failed, %d not applicable" % (len(total), len(total) - len(R.failed), len(R.failed), len(R.rows) - len(total)))
    print("Not checked: whether it is attractive or accessible beyond the hooks, anything a real user does with real requirements, any browser but Chromium.")
    return 1 if R.failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default=str(serve.DEFAULT_APP), help="folder holding the app's index.html (default: design/reference_viewer)")
    ap.add_argument("--datasets", required=True, help="the folder reqin make-datasets wrote (it holds index.json)")
    ap.add_argument("--only", help="comma list of dataset ids or folder prefixes, for example F1,F12 or F06")
    ap.add_argument("--load-via", choices=("url", "files"), default="url", help="url: ?dataset=FOLDER (default); files: the folder input")
    ap.add_argument("--tokens", default=str(serve.TOKENS), help="design tokens to check the page's colours and fonts against; 'none' skips that check")
    ap.add_argument("--no-extras", action="store_true", help="skip the canary and the corrupted-dataset checks")
    ap.add_argument("--navigation", metavar="FILE", help="design/navigation.json: also compare the menu with the map of the prototype (without it, an app that has a menu gets the structure checks only)")
    ap.add_argument("--json", metavar="FILE")
    a = ap.parse_args(argv)
    R = run(a.app, a.datasets, [s.strip().lower() for s in a.only.split(",")] if a.only else None, a.load_via, None if a.tokens == "none" else a.tokens, extras=not a.no_extras, navigation=a.navigation)
    if a.json:
        Path(a.json).write_text(json.dumps({"format": "reqin-gui-probe/1", "app": os.path.basename(os.path.normpath(a.app)), "checks": R.rows}, indent=1) + "\n", encoding="utf-8")
    return report(R)


if __name__ == "__main__":
    sys.exit(main())
