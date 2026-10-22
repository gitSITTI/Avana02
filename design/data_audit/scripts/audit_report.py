"""The chief of staff's part: put every hat's findings together into BRIEF.md (for a person) and report.json (for a script). Standard library only.

What the brief does not do: decide that the screen is fine. The top line is one of
  blocked    something serious was found
  open       nothing serious was found, but a check was not run, was skipped, or could not run, so part of the screen was not looked at
  attention  every check ran, and only smaller things were found
  clear      every one of the eight checks ran, and none found anything
and the line under it always says what clear does not mean. A check skipped with a reason is written down as skipped; it still keeps the top line from saying clear.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_common as C  # noqa: E402

REPORT_FORMAT = "reqin-audit-report/1"
ORDER = ("trace", "canary", "outage", "marks", "states", "known", "scan", "diff")
SEV_ORDER = ("high", "medium", "low", "info")
SEV_WORDS = {"high": "Fix first", "medium": "Then these", "low": "Smaller things", "info": "For information"}
VERDICT_WORDS = {"problem": "PROBLEM", "attention": "attention", "clear": "clear", "not-run": "NOT RUN"}
CLEAR_MEANS = ("**Clear means all eight checks ran and found nothing of the kind they look for.** It does not mean the screen is right: a typed-in value that equals the real one, "
               "a wrong field shown in a place the audit could not map, a slow or half-failing source, plain words (names, titles) the audit does not trace, and anything under "
               "\"What this audit cannot show\" are all invisible to it. A person still has to look, with their own data, on the running app.")


THEMES = [
    ("typed", "Values written into the page", r"^(trace\.typed|canary\.stayed|scan\.typed-in)",
     "Numbers, IDs or sentences that are in the page's own code or markup and do not follow the data. Each has to be read from the data instead."),
    ("fallback", "Sample, or old, data shown when the source fails", r"^outage\.[a-z-]+\.(appeared|left|stale)$",
     "When the source gave nothing or failed, the screen kept showing values (typed-in samples, or a copy kept in the browser) with nothing to say they are not live."),
    ("wrong-field", "A place on the screen showing another field or another record's text", r"^(canary\.wrong-field|known\.field|known\.text\.)",
     "The value under a heading is not the value of the field the heading names."),
    ("silent", "The screen does not say what state its data is in", r"^(marks\.|states\.|outage\.[a-z-]+\.(silent|identical))",
     "Nothing on the screen tells a person whether the data is live, saved, sample, empty or failed, or the screen looks the same in every case."),
    ("writes", "The page tries to write", r"^trace\.write", "The page sent requests that change something. The audit refused them; ask whether it is meant to."),
    ("storage", "A second copy of the data kept in the browser", r"^scan\.(storage|outside-data)", "The source keeps or fetches data outside the one request that should provide it."),
    ("changes", "Changes between two copies of the data", r"^diff\.", "Records or fields changed, were added or removed."),
]


def themes(findings: list) -> list:
    """[{id, title, says, count, worst, checks}] for each group of findings that is about the same kind of fault, so a person reads six lines before reading thirty."""
    import re
    out = []
    for tid, title, rx, says in THEMES:
        hit = [f for f in findings if re.search(rx, f["id"]) and f["severity"] != "info"]
        if hit:
            out.append({"id": tid, "title": title, "says": says, "count": len(hit), "worst": min((f["severity"] for f in hit), key=SEV_ORDER.index),
                        "checks": sorted({f["skill"] for f in hit})})
    return out


def readiness(sess: dict, results: dict) -> tuple:
    """(state, reasons): blocked | open | attention | clear. Clear needs all eight checks to have run and found nothing; a skipped check, with or without a reason, is open."""
    high = sum(1 for r in results.values() for f in r["findings"] if f["severity"] == "high")
    if high:
        return "blocked", ["%d serious finding(s)" % high]
    reasons = []
    skipped = sess.get("skipped", {})
    for sid in ORDER:
        r = results.get(sid)
        if sid in skipped:
            reasons.append("%s was skipped, so nothing was looked at by it: %s" % (sid, C.short(skipped[sid], 100)))
        elif r is None:
            reasons.append("%s was not run and not skipped" % sid)
        elif r["verdict"] == "not-run":
            reasons.append("%s could not run: %s" % (sid, C.short(r["summary"], 100)))
    if reasons:
        return "open", reasons
    smaller = sum(1 for r in results.values() for f in r["findings"] if f["severity"] in ("medium", "low"))
    return ("attention", ["%d smaller finding(s)" % smaller]) if smaller else ("clear", [])


def build(session: str) -> dict:
    sess = C.load_session(session)
    results = C.load_results(session)
    state, reasons = readiness(sess, results)
    skills, hats = C.skills(), C.hats()
    findings = []
    for sid, r in results.items():
        for f in r["findings"]:
            findings.append({**f, "skill": sid, "hat": r["hat"]})
    findings.sort(key=lambda f: (SEV_ORDER.index(f["severity"]), ORDER.index(f["skill"]) if f["skill"] in ORDER else 99, f["id"]))
    not_run = [{"skill": sid, "hat": skills[sid]["default_hat"], "command": skills[sid]["command"], "needs": skills[sid]["needs"]}
               for sid in ORDER if sid not in results and sid not in sess.get("skipped", {})]
    ran_hats = {r["hat"] for r in results.values()}
    asked = []
    for hid in C.hat_order():
        if hid in ran_hats:
            for q in hats[hid]["asks_the_person"]:
                if q not in asked:
                    asked.append(q)
    cannot = []
    for r in results.values():
        for x in r.get("not_checked", []):
            if x not in cannot:
                cannot.append(x)
    for n in not_run:
        cannot.append("nothing was looked at by %s (not run): %s" % (n["skill"], C.short(skills[n["skill"]]["does"], 160)))
    for sid, why in sess.get("skipped", {}).items():
        cannot.append("nothing was looked at by %s (skipped: %s)" % (sid, C.short(why, 100)))
    return {"format": REPORT_FORMAT, "page": sess.get("page"), "created": sess.get("created"), "built": C.now(), "state": state, "reasons": reasons,
            "counts": dict(Counter(f["severity"] for f in findings)), "themes": themes(findings), "findings": findings, "not_run": not_run, "skipped": sess.get("skipped", {}),
            "hats_worn": sess.get("hats_worn", {}), "questions": asked, "cannot_show": cannot,
            "files": sorted({x for r in results.values() for x in r.get("files", []) if x}),
            "runs": {sid: {"hat": r["hat"], "verdict": r["verdict"], "summary": r["summary"]} for sid, r in results.items()}}


def render(rep: dict, session: str) -> str:
    L = ["# Data audit brief", "",
         "Page: %s" % rep["page"], "Session started %s, brief built %s." % (rep["created"], rep["built"]),
         "This session folder holds the person's data (responses the page loaded, the records picked). Keep it out of any repository.", "",
         "## Where this stands: %s" % rep["state"].upper(), ""]
    L += ["- " + r for r in rep["reasons"]] if rep["reasons"] else ["- all eight checks ran and none found anything"]
    L += ["", CLEAR_MEANS, ""]
    if rep["themes"]:
        L += ["## In short", ""]
        for t in rep["themes"]:
            L.append("- **%s** (%d finding%s, worst: %s; seen by %s): %s" % (t["title"], t["count"], "" if t["count"] == 1 else "s", t["worst"], ", ".join(t["checks"]), t["says"]))
        L.append("")
    by = {s: [f for f in rep["findings"] if f["severity"] == s] for s in SEV_ORDER}
    for s in SEV_ORDER:
        if not by[s]:
            continue
        L += ["## %s (%d)" % (SEV_WORDS[s], len(by[s])), ""]
        for n, f in enumerate(by[s], 1):
            L.append("%d. **%s** (%s, %s hat): %s" % (n, f["where"], f["skill"], f["hat"], f["what"]))
            if f.get("evidence"):
                L.append("   - seen: %s" % f["evidence"])
            if f.get("next_step"):
                L.append("   - next: %s" % f["next_step"])
        L.append("")
    if rep["files"]:
        L += ["## Things for a person to look at", ""]
        top = [x for x in rep["files"] if Path(x).name in ("states.png", "known_values.md", "diff.md")]
        rest = [x for x in rep["files"] if x not in top and Path(x).suffix == ".png"]
        L += ["- `%s`" % Path(x).name for x in top]
        if rest:
            L.append("- one picture of the screen for each replay: %s (in `visits/`)" % ", ".join("`%s`" % Path(x).name for x in rest))
        L.append("")
    L += ["## What ran", "", "| check | hat | result |", "|---|---|---|"]
    for sid, r in rep["runs"].items():
        L.append("| %s | %s | %s: %s |" % (sid, r["hat"], VERDICT_WORDS.get(r["verdict"], r["verdict"]), C.short(r["summary"], 150).replace("|", "/")))
    L.append("")
    if rep["not_run"] or rep["skipped"]:
        L += ["## Not run", ""]
        for n in rep["not_run"]:
            L.append("- **%s** (%s hat): not run yet. %s" % (n["skill"], n["hat"], ("Needs " + ", ".join(n["needs"]) + ". ") if n["needs"] else "") + "Command: `%s`" % n["command"])
        for sid, why in rep["skipped"].items():
            L.append("- **%s**: skipped. Reason given: %s" % (sid, why))
        L.append("")
    if rep["questions"]:
        L += ["## Questions for the person", ""] + ["- " + q for q in rep["questions"]] + [""]
    L += ["## What this audit cannot show", ""] + ["- " + x for x in rep["cannot_show"]] + [""]
    L += ["Written by the chief of staff hat. The findings files, the pictures and the minutes (`MINUTES.md`) are in %s." % session, ""]
    return "\n".join(L)


def write(session: str) -> tuple:
    rep = build(session)
    brief = Path(session) / "BRIEF.md"
    brief.write_text(render(rep, session), encoding="utf-8")
    C.write_json(Path(session) / "report.json", rep)
    return brief, rep
