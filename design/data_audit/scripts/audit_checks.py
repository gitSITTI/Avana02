"""The checks that open the person's page: trace, canary, outage, marks, states. Each takes the session folder and a net.Runner and returns a result (common.result).

Nothing here decides that a screen is right. Each check says what it saw, what that suggests, and (in `not_checked`) what it cannot see. A check that could not do its job says
`not-run` and why: it never reports "clear" for something it did not test.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_common as C  # noqa: E402
import audit_net as net  # noqa: E402
import audit_values as V  # noqa: E402

BODY_MB = net.BODY_CAP // 1000000
COMMON_NOT_CHECKED = [
    "anything drawn as a picture (a chart on a canvas, an image of text)",
    "content in closed shadow roots, and in frames that are hidden or that the browser would not let the audit read",
    "rows a long list keeps out of the page until it is scrolled to (the audit reads what is in the page when it settles)",
    "anything behind a click or a sign-in that the setup steps did not do",
    "anything the page gets over a WebSocket or an event stream, or from inside a web worker (the audit does not allow workers or sockets to carry data)",
]
MAX_SHOWN = 12                                                  # findings listed one by one per rule; the rest are counted
MARK_STATES = ("live", "cached", "sample", "empty", "error", "loading")
STATE_WORD = {                                                  # words a person would read as that state
    "live": r"\b(live|current|up to date|synced|in sync|now)\b",
    "cached": r"\b(cache|cached|saved copy|stored|offline|last (updated|synced|refreshed)|copy)\b",
    "sample": r"\b(sample|demo|example|test data|made.?up)\b",
    "empty": r"\b(empty|no|none|nothing)\b",
    "error": r"\b(error|fail\w*|could not|couldn.t|cannot|can.t|unavailable|offline|not connected|down|try again)\b",
}
NOT_LIVE = re.compile(r"\b(not|isn.t|is not|no longer|never|out of)\s+(live|current|up to date|synced|in sync)\b|\b(unsynced|not now)\b", re.I)


# ------------------------------------------------------------------------------------------------ helpers
def where_of(item: dict) -> str:
    t = re.sub(r"\s+", " ", item.get("text", "")).strip()
    t = (t[:50] + "…") if len(t) > 50 else t
    if item.get("testid"):
        return "the element marked %s (%r)" % (item["testid"], t)
    if item.get("head"):
        return "the %r column: %r" % (item["head"], t)
    return "%s: %r" % (item.get("tag", "text"), t)


def not_run(skill: str, hat: str, why: str, findings: list | None = None, files: list | None = None) -> dict:
    return C.result(skill, hat, "Not run: " + why, findings or [], not_checked=[why], files=files, verdict="not-run")


def notes(skill: str, extra: list | None = None) -> list:
    return list(C.skills()[skill]["cannot_find"]) + (extra or []) + COMMON_NOT_CHECKED


def classify(items: list, loaded: V.Loaded) -> list:
    """Every value on the screen with where it came from: bound (found in the data the page loaded), derived (a count or a sum of it), typed (found only in the page's own code
    or markup), clock (a date or time found nowhere: probably the current time), unexplained (found nowhere)."""
    out = []
    for it in items:
        got = V.item_atoms(it)
        if any(a["kind"] == "statement" for a in got):
            got = [a for a in got if a["kind"] != "number"]       # the numbers inside a sentence belong to the sentence
        for a in got:
            info = loaded.explain(a)
            if info:
                cls = "derived"
            elif loaded.has_in_data(a):
                cls = "bound"
            elif loaded.has_in_code(a):
                cls = "typed"
            elif a["kind"] in ("date", "time"):
                cls = "clock"
            else:
                cls = "unexplained"
            out.append({"item": it, "atom": a, "class": cls, "info": info})
    return out


def keyed(cls: list, classes: tuple) -> dict:
    """{(kind, value): first entry} for the values of the given classes."""
    out = {}
    for c in cls:
        if c["class"] in classes:
            out.setdefault((c["atom"]["kind"], c["atom"]["value"]), c)
    return out


def raw_of(item: dict, key: tuple) -> str:
    for a in V.item_atoms(item):
        if (a["kind"], a["value"]) == key:
            return a["raw"]
    return key[1]


def a_or_an(kind: str) -> str:
    return "An" if kind[0] in "aeiou" else "A"


def screen_values(items: list, kinds=("id", "number", "statement")) -> dict:
    out = {}
    for it in items:
        got = V.item_atoms(it)
        if any(a["kind"] == "statement" for a in got):
            got = [a for a in got if a["kind"] != "number"]
        for a in got:
            if a["kind"] in kinds:
                out.setdefault((a["kind"], a["value"]), it)
    return out


def present(a_key: tuple, vals: dict, text: str) -> bool:
    """Whether a value from one visit is on the screen of another."""
    if a_key in vals:
        return True
    kind, value = a_key
    return kind == "statement" and V.statement_in(value, V.norm(text))


def own_errors(errors: list) -> list:
    """The page's uncaught errors, without the ones the audit caused by refusing a worker or WebRTC."""
    return [e for e in errors if "the audit does not allow" not in e]


def blocked_writes(*visits) -> list:
    seen, out = set(), []
    for v in visits:
        for b in v.blocked:
            k = (b["method"], re.sub(r"^https?://[^/]+", "", b["url"]))
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out


def indicator(v: net.Visit, loaded: V.Loaded | None = None, base: net.Visit | None = None) -> bool:
    """Whether the screen gives a sign about the state of its data that a person could read: a mark with visible words, or words about it that the normal screen (`base`) did not
    already have. The data's own words do not count (a requirement about an 'error' margin is not a message about an error), and neither do words the normal screen has too (a menu
    item called 'Error log'). An attribute no one can see does not count."""
    if any(m.get("state") in ("empty", "error", "cached", "sample") and m.get("label") and m.get("label_visible") and m.get("shown", True) for m in v.marks):
        return True
    before = {V.norm(i.get("text", "")) for i in base.items} if base is not None else set()
    for it in v.items:
        t = it.get("text", "")
        if V.norm(t) in before:
            continue
        if loaded is not None and (V.norm(t) in loaded.strings or any(loaded.has_in_data(a) for a in V.item_atoms(it))):
            continue
        if V.says_something_about_state(t):
            return True
    return False


def nothing_seen(rec: net.Visit) -> bool:
    """The page opened and nothing readable is on it: no text, no filled input."""
    return rec.ok and not rec.items


NOTHING_SEEN = ("Nothing readable was found on the screen. The content may be a picture or a canvas, in a closed shadow root, drawn later than the audit waits (give a longer wait "
                "with --settle MS when starting), or behind a click (--setup \"click:Label\").")


def count_line(counter: Counter, order) -> str:
    return ", ".join("%d %s" % (counter[k], k) for k in order if counter[k])


# ------------------------------------------------------------------------------------------------ trace
def trace(sess: Path, runner: net.Runner, hat: str, fresh: bool = False) -> dict:
    rec = net.get_visit(runner, sess, "record", fresh=fresh)
    if not rec.ok:
        return not_run("trace", hat, "the page did not open: " + rec.error)
    L = V.Loaded(rec.responses)
    data = rec.data_responses()
    cls = classify(rec.items, L)
    n = Counter(c["class"] for c in cls)
    F = []
    streams = [r for r in rec.responses if r["type"] == "eventsource"]
    if not data and (streams or rec.sockets):
        F.append(C.finding("trace.stream-only", "medium", "the whole page", "The page made no fetch or XHR request; it gets its data over %s." % (
            "an event stream (EventSource)" if streams else "a WebSocket"), "responses seen: %s" % (count_line(Counter(r["type"] for r in rec.responses), sorted({r["type"] for r in rec.responses})) or "none"),
                           "The audit lets an event stream through without reading it and gives a socket a connection that goes nowhere, so it cannot say where the values on this screen come "
                           "from or change them. Ask where they come from."))
    elif not data:
        F.append(C.finding("trace.no-data-requests", "high", "the whole page",
                           "The page asked for no data (no fetch or XHR request), yet it shows %d values." % len(cls) if cls else
                           "The page asked for no data (no fetch or XHR request).",
                           "responses seen: %s" % (count_line(Counter(r["type"] for r in rec.responses), sorted({r["type"] for r in rec.responses})) or "none"),
                           "Everything on this screen is in its own files, or the server wrote it into the page. If it is meant to show a person's data, it is not connected to any. "
                           "If the data arrives some other way (a script file, the server writing it into the page), say how: the audit cannot tell typed-in from server-written."))
    if nothing_seen(rec):
        F.append(C.finding("trace.nothing-seen", "medium", "the whole screen", NOTHING_SEEN, "%d data response(s) loaded" % len(data), "Say where the values are, or let the audit reach them."))
    if not cls and not nothing_seen(rec):
        F.append(C.finding("trace.no-values", "low", "the whole screen", "The screen has words but no number, ID, date or requirement-shaped sentence, so this check had nothing to look at.", "",
                           "Plain words (names, titles, labels) are not traced. Use `known` with the person's own records to check them."))
    for i, sock in enumerate(rec.sockets[:MAX_SHOWN], 1):
        F.append(C.finding("trace.socket.%d" % i, "medium", "the page's requests", "The page opened a WebSocket (%s). The audit gave it a connection that goes nowhere: it cannot tell a message that reads from one that writes."
                           % re.sub(r"^wss?://[^/]+", "", sock), "", "Whatever arrives over a socket was not seen. Ask what the screen shows from it."))
    for i, what in enumerate(rec.refused_features[:MAX_SHOWN], 1):
        F.append(C.finding("trace.refused.%d" % i, "medium", "the page", "The page tried to start a %s. The audit does not allow it: a %s could send what the audit means to refuse." % (what, what), "",
                           "Whatever it would have done was not done. Ask what it is for."))
    if rec.truncated:
        F.append(C.finding("trace.too-big", "medium", "the page's requests", "%d response(s) were bigger than the audit keeps (%d MB), so what is in them was not searched." % (
            len(rec.truncated), BODY_MB), "; ".join("%s (%d MB)" % (re.sub(r"^https?://[^/]+", "", t["url"])[:60], t["bytes"] // 1000000) for t in rec.truncated[:3]),
            "Values taken from them are reported as 'not explained' or 'typed in'. Check those by hand."))
    shown = Counter()
    for c in cls:
        a, it = c["atom"], c["item"]
        if c["class"] == "typed":
            sev = "medium" if a["kind"] == "number" else "high"
            key = "typed"
            if shown[key] < MAX_SHOWN:
                F.append(C.finding("trace.typed.%d" % (shown[key] + 1), sev, where_of(it),
                                   "%s %s on the screen is in the page's own code or markup and in none of the data it loaded." % (a_or_an(a["kind"]), a["kind"] if a["kind"] != "id" else "ID"),
                                   C.short(a["raw"], 100),
                                   "Find where it is written and replace it with the value read from the data. If the server writes it into the page from data, say so: the audit cannot tell."))
            shown[key] += 1
        elif c["class"] == "unexplained" and a["kind"] in ("id", "statement"):
            if shown["unexplained"] < MAX_SHOWN:
                F.append(C.finding("trace.unexplained.%d" % (shown["unexplained"] + 1), "medium", where_of(it),
                                   "%s %s on the screen is in nothing the page loaded and nowhere in its code." % (a_or_an(a["kind"]), a["kind"] if a["kind"] != "id" else "ID"), C.short(a["raw"], 100),
                                   "It is built from pieces, comes from a source the audit could not see (a socket, a worker), or is made up at run time. Ask what produces it."))
            shown["unexplained"] += 1
        elif c["class"] == "unexplained" and a["kind"] == "number":
            if shown["unexplained-number"] < MAX_SHOWN:
                F.append(C.finding("trace.unexplained-number.%d" % (shown["unexplained-number"] + 1), "low", where_of(it),
                                   "A number on the screen is not in the data and is not a count or a sum of it that the audit could work out.", C.short(a["raw"], 60),
                                   "Ask the person what it is meant to be (an average, a percentage of something, a score). If it is worked out, check it by hand once."))
            shown["unexplained-number"] += 1
    for key, label in (("typed", "typed in"), ("unexplained", "not explained"), ("unexplained-number", "numbers not explained")):
        if shown[key] > MAX_SHOWN:
            F.append(C.finding("trace.%s.more" % key, "info", "the screen", "%d more values %s are not listed one by one." % (shown[key] - MAX_SHOWN, label), "", ""))
    # a value both in the data and in the code: a copy that can be shown instead of the data
    copies = [c for c in cls if c["class"] == "bound" and c["atom"]["kind"] in ("id", "statement") and L.has_in_code(c["atom"])]
    for i, c in enumerate(copies[:MAX_SHOWN], 1):
        F.append(C.finding("trace.copy.%d" % i, "low", where_of(c["item"]), "This %s is in the data the page loaded and also in its own code: a copy that could be shown when the data is missing." % c["atom"]["kind"],
                           C.short(c["atom"]["raw"], 100), "The outage check shows whether the copy is ever used."))
    derived = [c for c in cls if c["class"] == "derived"]
    if derived:
        why = Counter(c["info"]["label"] for c in derived)
        F.append(C.finding("trace.derived", "info", "the screen", "%d number%s a count or a sum the audit could work out from the data." % (len(derived), " is" if len(derived) == 1 else "s are"),
                           "; ".join("%s: %s" % (k, v) for k, v in list(why.items())[:3]), "A person should still check one of them by hand: a number that is right by accident looks the same."))
    for i, (m, path) in enumerate(blocked_writes(rec), 1):
        F.append(C.finding("trace.write.%d" % i, "medium", "the page's requests", "The page tried to send a request that writes (%s %s). The audit refused it." % (m, path), "",
                           "Ask whether the screen is meant to write when it opens (a visit counter, an autosave). The audit sends none; give `--allow-post` a pattern only for a POST that is really a read."))
    own = own_errors(rec.page_errors)
    if own:
        F.append(C.finding("trace.page-error", "low", "the page", "The page raised %d uncaught error(s) while loading." % len(own), C.short(own[0], 160), "Read it in the browser's console."))
    total = len(cls)
    summary = ("%d values on the screen: %s. %d data responses loaded." % (total, count_line(n, ("bound", "derived", "typed", "unexplained", "clock")) or "none", len(data))) if total else \
        ("Nothing readable was found on the screen (%d data responses loaded)." % len(data) if nothing_seen(rec) else
         "No numbers, IDs or sentences were found on the screen, only words (%d data responses loaded)." % len(data))
    return C.result("trace", hat, summary, F, {"values": total, "bound": n["bound"], "derived": n["derived"], "typed": n["typed"], "unexplained": n["unexplained"], "clock": n["clock"],
                                                "data_responses": len(data), "items": len(rec.items)}, notes("trace"), [str(rec.shot)] if rec.shot else [])


# ------------------------------------------------------------------------------------------------ canary
def _head_key(head: str, keys: list):
    h = re.sub(r"[^a-z0-9]", "", head.lower())
    for k in keys:
        if re.sub(r"[^a-z0-9]", "", k.lower()) == h and h:
            return k
    return None


def canary(sess: Path, runner: net.Runner, hat: str, fresh: bool = False) -> dict:
    rec = net.get_visit(runner, sess, "record", fresh=fresh)
    if not rec.ok:
        return not_run("canary", hat, "the page did not open: " + rec.error)
    can = net.get_visit(runner, sess, "canary", fresh=fresh)
    if not can.ok:
        return not_run("canary", hat, "the page did not open with the data changed: " + can.error)
    if nothing_seen(rec):
        return not_run("canary", hat, NOTHING_SEEN, [C.finding("canary.nothing-seen", "medium", "the whole screen", NOTHING_SEEN, "", "Say where the values are, or let the audit reach them.")])
    if can.changed == 0:
        f = C.finding("canary.no-lever", "medium", "the page's data requests",
                      "Nothing could be changed: the page made no fetch or XHR request that returned JSON, so there was no data to replace.", "",
                      "Point the audit at a screen that reads JSON through a request, or say how this one gets its data. The trace shows what is typed in.")
        return C.result("canary", hat, "Not run: no JSON data request to change.", [f], {"responses_changed": 0}, notes("canary"), verdict="not-run")
    L = V.Loaded(rec.responses)
    rvals = screen_values(rec.items)
    cvals = screen_values(can.items)
    F, followed, stayed = [], 0, []
    for key, it in rvals.items():
        a = next((x for x in V.item_atoms(it) if (x["kind"], x["value"]) == key), None)
        info = L.explain(a) if a else None
        if info and info["kind"] != "sum":
            continue                                                  # a count of the records does not change when their values do
        if present(key, cvals, can.text):
            stayed.append((key, it))
        else:
            followed += 1
    for i, (key, it) in enumerate(stayed[:MAX_SHOWN], 1):
        sev = "medium" if key[0] == "number" else "high"
        F.append(C.finding("canary.stayed.%d" % i, sev, where_of(it), "%s %s stayed on the screen after the data it should come from was replaced." % (a_or_an(key[0]), "ID" if key[0] == "id" else key[0]), C.short(raw_of(it, key), 100),
                           "It is typed in, kept from an earlier load, or read from a source the audit did not change. Find where the page gets it."))
    if len(stayed) > MAX_SHOWN:
        F.append(C.finding("canary.stayed.more", "info", "the screen", "%d more values stayed; they are not listed one by one." % (len(stayed) - MAX_SHOWN), "", ""))
    tokens = [i for i in can.items if re.search(r"canary-[a-z0-9]*-\d+", V.norm(i["text"])) or any(a["kind"] == "number" and int(a["value"].rstrip("%").split(".")[0] or 0) >= 7000000 for a in V.item_atoms(i) if re.fullmatch(r"\d+(\.\d+)?%?", a["value"]))]
    if not tokens:
        # values that stayed AND none of the invented ones came: the screen is not showing this data. Values that went and none of the invented ones came: the page broke on the
        # invented values, or it maps them (a status to a label) and shows something of its own in their place
        F.append(C.finding("canary.none-reached", "high" if stayed else "medium", "the screen", "None of the invented values reached the screen%s." % (
            ": nothing on it follows the requests the audit changed" if stayed else ", though %d value(s) left it" % followed), "",
            "Either the screen is not showing this data, or it shows a copy from somewhere else. Run the trace and the outage check." if stayed else
            "The page may turn the values it gets into its own words (a status into a label), or it failed on the invented values. Look at the picture of the canary visit."))
    # a column that shows another field: the invented text carries the name of the field it came from
    mism = Counter()
    keys = sorted({k for ks in can.canary_fields.values() for k in ks})
    where_first = {}
    for it in can.items:
        head = it.get("head") or ""
        m = re.fullmatch(r"\s*(CANARY-[A-Z0-9]+-\d+)\s*", it["text"].upper() if it["text"] else "")
        if not head or not m:
            continue
        tok = m.group(1)
        fields = can.canary_fields.get(tok) or can.canary_fields.get(it["text"].strip()) or []
        want = _head_key(head, keys)
        if want and fields and want not in fields:
            mism[(head, want, tuple(fields))] += 1
    for i, ((head, want, fields), n) in enumerate(mism.items(), 1):
        F.append(C.finding("canary.wrong-field.%d" % i, "high", "the %r column" % head, "The %r column shows the value of the field %s, not of the field %r." % (head, " / ".join(repr(f) for f in fields), want),
                           "%d cells" % n, "Read the cell's value from the field the heading names, or rename the heading."))
    if own_errors(can.page_errors) and not own_errors(rec.page_errors):
        F.append(C.finding("canary.page-error", "medium", "the page", "The page raised an error when the values changed but not when they did not.", C.short(own_errors(can.page_errors)[0], 160),
                           "It depends on the values it was given (a format, a length). Read the error in the browser's console."))
    total = followed + len(stayed)
    summary = "%d of %d values that come from the data changed when the data changed; %d stayed. %d things on the screen show invented values. %d data response(s) were rewritten." % (
        followed, total, len(stayed), len(tokens), can.changed)
    return C.result("canary", hat, summary, F, {"values_checked": total, "followed": followed, "stayed": len(stayed), "canary_items_on_screen": len(tokens), "responses_changed": can.changed,
                                                 "wrong_field_columns": len(mism)}, notes("canary", ["a typed-in count equal to the number of records (the outage check empties the data)", "values that are not text or numbers in JSON"]),
                    [str(can.shot)] if can.shot else [])


# ------------------------------------------------------------------------------------------------ outage
OUTAGE_RUNS = (("empty", False), ("error", False), ("disconnect", False), ("error", True), ("disconnect", True))
OUTAGE_WORDS = {"empty": "the source returned nothing", "error": "the source failed", "disconnect": "the connection was down"}


def outage(sess: Path, runner: net.Runner, hat: str, fresh: bool = False) -> dict:
    rec = net.get_visit(runner, sess, "record", fresh=fresh)
    if not rec.ok:
        return not_run("outage", hat, "the page did not open: " + rec.error)
    if not rec.data_responses():
        f = C.finding("outage.no-lever", "medium", "the page's data requests", "The page made no data request, so there was nothing to empty or break.", "", "The trace says what is typed in.")
        return C.result("outage", hat, "Not run: no data request to change.", [f], {}, notes("outage"), verdict="not-run")
    if nothing_seen(rec):
        return not_run("outage", hat, NOTHING_SEEN, [C.finding("outage.nothing-seen", "medium", "the whole screen", NOTHING_SEEN, "", "Say where the values are, or let the audit reach them.")])
    L = V.Loaded(rec.responses)
    cls = classify(rec.items, L)
    from_data = keyed(cls, ("bound", "derived"))
    rec_all = screen_values(rec.items)
    F, counts, files = [], {}, [str(rec.shot)] if rec.shot else []
    for mode, warm in OUTAGE_RUNS:
        tag = "%s%s" % (mode, "-warm" if warm else "")
        v = net.get_visit(runner, sess, mode, warm, fresh=fresh)
        if not v.ok:
            F.append(C.finding("outage.%s.no-open" % tag, "medium", "the page", "The page did not open when %s%s: %s" % (OUTAGE_WORDS[mode], " (with its stored data kept)" if warm else "", v.error), "",
                               "A page that cannot open without its data may need a message instead."))
            continue
        files.append(v.shot)
        vals = screen_values(v.items)
        left = [(k, it) for k, it in vals.items() if k in from_data]
        # values that were not there when the data was: a sample or fallback
        appeared = [(k, it) for k, it in vals.items() if k not in rec_all and not V.says_something_about_state(it["text"]) and not (k[0] == "number" and re.fullmatch(r"[45]\d\d", k[1]))]
        ind = indicator(v, L, rec)
        counts[tag] = {"left": len(left), "appeared": len(appeared), "indicator": ind, "items": len(v.items)}
        what = OUTAGE_WORDS[mode] + (" and the browser kept what the first visit stored" if warm else "")
        eg = lambda pairs: "; ".join(C.short(raw_of(it, k), 60) for k, it in pairs[:3])          # noqa: E731
        if left and not warm:
            F.append(C.finding("outage.%s.left" % tag, "high", where_of(left[0][1]) + (" and %d more" % (len(left) - 1) if len(left) > 1 else ""),
                               "%d value(s) from the data are still on the screen when %s, with a clean browser." % (len(left), what), "e.g. " + eg(left),
                               "A clean browser has no earlier visit to remember, so these are typed in or are a sample kept in the page. Find where they are written."))
        elif left and warm:
            if ind:
                F.append(C.finding("outage.%s.saved-copy" % tag, "info", "the screen", "When %s, the screen still shows %d values from the data and gives a sign about its state." % (what, len(left)),
                                   C.short(v.text, 140), "A person should read that sign and decide whether it is clear enough (the marks and states checks look at it)."))
            else:
                F.append(C.finding("outage.%s.stale" % tag, "high", where_of(left[0][1]) + (" and %d more" % (len(left) - 1) if len(left) > 1 else ""),
                                   "Old data stays on the screen when %s, and nothing says it is old (%d value(s))." % (what, len(left)), "e.g. " + eg(left),
                                   "Show where it came from and when (a saved copy, last updated), or do not show it."))
        if appeared:
            F.append(C.finding("outage.%s.appeared" % tag, "high", where_of(appeared[0][1]) + (" and %d more" % (len(appeared) - 1) if len(appeared) > 1 else ""),
                               "%d value(s) appear on the screen only when %s: a sample or fallback." % (len(appeared), what), "e.g. " + eg(appeared),
                               "Remove the fallback data, or show an empty or error state in its place."))
        if not warm and not left and not appeared and not ind:
            sev = "low" if mode == "empty" else "medium"
            F.append(C.finding("outage.%s.silent" % tag, sev, "the screen", "When %s the screen says nothing about it (no message, no state, no mark)." % what, C.short(v.text, 140),
                               "Show a message that says what happened and what to do. An empty screen with no words looks like one that is still loading."))
        if not warm and v.text == rec.text:
            F.append(C.finding("outage.%s.identical" % tag, "high", "the whole screen", "The words on the screen are exactly the same when %s as when the data was there." % what, "",
                               "The screen does not depend on the data it asks for."))
        if len(own_errors(v.page_errors)) > len(own_errors(rec.page_errors)):
            F.append(C.finding("outage.%s.page-error" % tag, "medium", "the page", "The page raised an uncaught error when %s." % what, C.short(own_errors(v.page_errors)[-1], 160), "Handle the failure and show a message."))
        extra = [w for w in blocked_writes(v) if w not in blocked_writes(rec)]
        if extra:
            F.append(C.finding("outage.%s.write" % tag, "medium", "the page's requests", "The page tried to send a request that writes only when %s (%s %s). The audit refused it." % (what, extra[0][0], extra[0][1]),
                               "%d such request(s)" % len(extra), "A page that writes when its source fails (a log, a retry, a queue) may repeat the write on the real system. Ask whether it should."))
    bad = sum(1 for f in F if f["severity"] == "high")
    summary = "Ran %d replays (the source empty, failing, or the connection down; each with a clean browser and with what the first visit stored). %d serious finding(s)." % (len(counts), bad)
    return C.result("outage", hat, summary, F, {"replays": len(counts), **{"%s.%s" % (t, k): v for t, d in counts.items() for k, v in d.items()}}, notes("outage"), files)


# ------------------------------------------------------------------------------------------------ marks
def _label_matches(state: str, label: str) -> bool:
    """Whether the words would be read as the state. 'Not synced' is not live."""
    rx = STATE_WORD.get(state)
    if not rx:
        return True
    if state == "live" and NOT_LIVE.search(label):
        return False
    return bool(re.search(rx, label, re.I))


def marks(sess: Path, runner: net.Runner, hat: str, fresh: bool = False) -> dict:
    rec = net.get_visit(runner, sess, "record", fresh=fresh)
    if not rec.ok:
        return not_run("marks", hat, "the page did not open: " + rec.error)
    F = []
    L = V.Loaded(rec.responses)
    has_data = any(c["class"] in ("bound", "derived", "typed") for c in classify(rec.items, L)) or bool(rec.data_responses())
    if not rec.marks:
        if has_data:
            F.append(C.finding("marks.none", "medium", "the whole screen", "The screen has no marks that say where its data came from or whether it is live, saved, sample, empty or failed.", "no element carries data-source",
                               "Add `data-source=\"NAME\"` and `data-source-state=\"live|cached|sample|empty|error\"` to what shows data, and a visible `data-source-label` with the words. See SKILL.md."))
        return C.result("marks", hat, "The screen carries no provenance marks.", F, {"marks": 0}, notes("marks"), [str(rec.shot)] if rec.shot else [])
    for i, m in enumerate(rec.marks, 1):
        w = "mark %r" % m["source"]
        if m["state"] not in MARK_STATES:
            F.append(C.finding("marks.state.%d" % i, "medium", w, "The mark has no recognised state (%r); it should be one of %s." % (m["state"], ", ".join(MARK_STATES)), "", "Set data-source-state."))
        if not m["label"] or not m["label_visible"]:
            F.append(C.finding("marks.label.%d" % i, "medium", w, "The mark has no visible words, so a person looking at the screen cannot read it.", "", "Add a visible data-source-label inside it, not colour or an icon alone."))
        elif not _label_matches(m["state"], m["label"]):
            F.append(C.finding("marks.words.%d" % i, "low", w, "The words (%r) do not seem to say the state (%r)." % (m["label"], m["state"]), "", "Say it in words a person would read as that state."))
        if m["state"] in ("live", "cached") and not m["asof"]:
            F.append(C.finding("marks.asof.%d" % i, "low", w, "A %s mark gives no time (data-as-of)." % m["state"], "", "Say when the data was read."))
        if m["state"] == "sample":
            F.append(C.finding("marks.sample.%d" % i, "info", w, "The screen says its data is a sample.", C.short(m["label"], 80), "Make sure that is the intended state."))
    for mode, warm, allowed in (("empty", False, ("empty",)), ("error", False, ("error",)), ("disconnect", False, ("error",)), ("disconnect", True, ("error", "cached"))):
        v = net.get_visit(runner, sess, mode, warm, fresh=fresh)
        tag = mode + ("-warm" if warm else "")
        if not v.ok:
            continue
        for m in rec.marks:
            got = [x for x in v.marks if x["source"] == m["source"]]
            if not got:
                F.append(C.finding("marks.%s.gone.%s" % (tag, re.sub(r"\W+", "", m["source"])[:20]), "medium", "mark %r" % m["source"], "The mark disappears when %s." % OUTAGE_WORDS[mode], "",
                                   "Keep the mark and change its state, so the screen says the source is not giving data."))
                continue
            st = got[0]["state"]
            lab = got[0].get("label") or ""
            if st in allowed and lab and got[0].get("label_visible") and not _label_matches(st, lab):
                says_live = bool(re.search(STATE_WORD["live"], lab, re.I)) and not NOT_LIVE.search(lab)
                F.append(C.finding("marks.%s.words.%s" % (tag, re.sub(r"\W+", "", m["source"])[:20]), "high" if says_live else "medium", "mark %r" % m["source"],
                                   "The mark's state is %r when %s, but the words a person reads on it are %r." % (st, OUTAGE_WORDS[mode], C.short(lab, 60)), "",
                                   "Make the words follow the state. A person reads the words, not the attribute."))
            if st not in allowed:
                sev = "high" if st in ("live", "loading", "sample") or not st else "medium"
                F.append(C.finding("marks.%s.state.%s" % (tag, re.sub(r"\W+", "", m["source"])[:20]), sev, "mark %r" % m["source"],
                                   "The mark says %r when %s (it should say %s)." % (st or "nothing", OUTAGE_WORDS[mode], " or ".join(allowed)), "", "Set the state from what the request returned, not from what was shown before."))
    return C.result("marks", hat, "%d mark(s) on the screen; checked against the source empty, failing and down." % len(rec.marks), F, {"marks": len(rec.marks)}, notes("marks"),
                    [str(rec.shot)] if rec.shot else [])


# ------------------------------------------------------------------------------------------------ states
def _panel_changed(a, b, tol: int = 24, top: int = 900) -> float:
    from PIL import Image, ImageChops
    w, h = max(a.width, b.width), min(max(a.height, b.height), top)
    A = Image.new("RGB", (w, h), (255, 255, 255))
    B = Image.new("RGB", (w, h), (255, 255, 255))
    A.paste(a.crop((0, 0, a.width, min(a.height, h))), (0, 0))
    B.paste(b.crop((0, 0, b.width, min(b.height, h))), (0, 0))
    hist = ImageChops.difference(A, B).convert("L").histogram()
    return sum(hist[tol + 1:]) / float(w * h)


def states(sess: Path, runner: net.Runner, hat: str, fresh: bool = False) -> dict:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return not_run("states", hat, "Pillow is not installed (pip install pillow)")
    rec = net.get_visit(runner, sess, "record", fresh=fresh)
    if not rec.ok:
        return not_run("states", hat, "the page did not open: " + rec.error)
    vis = {"record": rec}
    for mode in ("empty", "error", "disconnect"):
        vis[mode] = net.get_visit(runner, sess, mode, fresh=fresh)
    imgs = {m: Image.open(v.shot).convert("RGB") for m, v in vis.items() if v.ok and v.shot and Path(v.shot).is_file()}
    if "record" not in imgs:
        return not_run("states", hat, "no picture of the screen could be taken")
    F, changed = [], {}
    for m in ("empty", "error", "disconnect"):
        if m not in imgs:
            F.append(C.finding("states.%s.no-open" % m, "medium", "the page", "The page did not open when %s." % OUTAGE_WORDS[m], vis[m].error, "A message would help."))
            continue
        changed[m] = _panel_changed(imgs["record"], imgs[m])
        same_text = vis[m].text == rec.text
        if changed[m] < 0.01 and same_text:
            F.append(C.finding("states.%s.same" % m, "high", "the whole screen", "The screen looks and reads the same when %s as with the data." % OUTAGE_WORDS[m], "%.1f%% of the top of the page changed" % (100 * changed[m]),
                               "A person could not tell. Show a state that says what happened."))
        elif changed[m] < 0.05 and not indicator(vis[m], V.Loaded(rec.responses), rec):
            F.append(C.finding("states.%s.quiet" % m, "medium", "the whole screen", "The screen changes little (%.1f%% of the top of the page) when %s and says nothing about it." % (100 * changed[m], OUTAGE_WORDS[m]),
                               C.short(vis[m].text, 140), "Show a message or a state that says what happened."))
        elif changed[m] < 0.01:
            F.append(C.finding("states.%s.looks-same" % m, "medium", "the whole screen", "The screen looks almost the same when %s (only %.1f%% of the top of the page changed), although its words changed." % (OUTAGE_WORDS[m], 100 * changed[m]),
                               C.short(vis[m].text, 140), "Look at the picture: is the change easy to see?"))
    if "empty" in imgs and "error" in imgs and vis["empty"].text == vis["error"].text:
        F.append(C.finding("states.empty-is-error", "medium", "the whole screen", "An empty source and a failing source give the same words on the screen.", C.short(vis["error"].text, 140),
                           "A person cannot tell that nothing is there from that something went wrong."))
    # one picture, side by side
    W, top = 420, 1100
    font = ImageFont.load_default(size=15)
    panels = []
    for m in ("record", "empty", "error", "disconnect"):
        if m in imgs:
            im = imgs[m].crop((0, 0, imgs[m].width, min(imgs[m].height, top)))
            im = im.resize((W, max(1, round(im.height * W / im.width))))
            panels.append((m, im))
    H = max(p.height for _, p in panels) + 34
    sheet = Image.new("RGB", (len(panels) * (W + 12) + 12, H + 12), (236, 236, 236))
    d = ImageDraw.Draw(sheet)
    names = {"record": "the data as it is", "empty": "the source returned nothing", "error": "the source failed", "disconnect": "the connection was down"}
    for i, (m, im) in enumerate(panels):
        x = 12 + i * (W + 12)
        d.text((x, 10), names[m], fill=(20, 20, 20), font=font)
        sheet.paste(im, (x, 34))
    out = Path(sess) / "states.png"
    sheet.save(out)
    summary = "Four screens drawn side by side in %s. How much of the top of the page changed from the normal one: %s. Look at the picture; the check counts changes, it cannot judge them." % (
        out.name, ", ".join("%s %.0f%%" % (m, 100 * c) for m, c in changed.items()) or "none")
    return C.result("states", hat, summary, F, {"changed_%s" % m: round(c, 4) for m, c in changed.items()}, notes("states"), [str(out)])
