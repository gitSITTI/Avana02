#!/usr/bin/env python3
"""Find out whether a screen shows the person's real data, or something that only looks right (typed-in, sample, kept from an earlier load, or the wrong field).

    python3 design/data_audit/scripts/audit.py init SESSION --page URL_OR_FILE        start (opens nothing yet)
    python3 design/data_audit/scripts/audit.py next SESSION                           what to do now, and which hat to wear for it
    python3 design/data_audit/scripts/audit.py hat SESSION HAT                        a hat's whole brief (give it to an agent of its own)
    python3 design/data_audit/scripts/audit.py run SESSION SKILL [options]            run one check
    python3 design/data_audit/scripts/audit.py skip SESSION SKILL --because TEXT      say a check will not be run, and why
    python3 design/data_audit/scripts/audit.py minutes SESSION --kind decision --said-by NAME --text TEXT
    python3 design/data_audit/scripts/audit.py brief SESSION                          put every hat's findings together (BRIEF.md, report.json)
    python3 design/data_audit/scripts/audit.py status SESSION | verify SESSION | list

The audit sends no write that it can see: any HTTP request the page makes that is not a GET, HEAD or OPTIONS is refused and listed, a WebSocket is given a connection that goes
nowhere, and web workers, WebRTC and WebTransport are not allowed to start. It cannot know whether a GET changes something on the server, and it opens the page many times.
Everything it saves stays in the SESSION folder, which holds the person's data (and any sign-in the page kept) and therefore must not be inside a git repository (init refuses).
skills.json is the whole list of checks; hats.json says which hat may run which. A hat is a way of working, not a lock: the commands refuse a hat that names a check it does not
own, but nothing proves who typed the command.
Needs Playwright 1.48 or newer with Chromium for the checks that open the page (trace, canary, outage, marks, states, and known when its visit is not saved yet).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_common as C  # noqa: E402
import audit_report as R  # noqa: E402

CHECKS = R.ORDER
VERDICT_WORDS = R.VERDICT_WORDS
SHOW_MAX = 14


# ------------------------------------------------------------------------------------------------ small helpers
def hat_name(hid: str) -> str:
    return C.hats()[hid]["name"]


def need_hat(hat: str, skill: str) -> None:
    hats = C.hats()
    if hat not in hats:
        raise SystemExit("no such hat: %s (the hats are: %s)" % (hat, ", ".join(C.hat_order())))
    if skill not in hats[hat]["skills"]:
        raise SystemExit("refused: the %s hat may not run %s. It may run: %s. Wear the hat that owns it: %s" % (
            hats[hat]["name"], skill, ", ".join(hats[hat]["skills"]), C.cmd("hat", "SESSION", C.skills()[skill]["default_hat"])))


def runner_for(sess: dict):
    import audit_net as net
    return net.Runner(sess["page"], width=sess.get("width", 1440), height=sess.get("height", 900), setup=sess.get("setup") or [], storage_state=sess.get("storage_state") or None,
                      allow_post=sess.get("allow_post") or "", settle_ms=sess.get("settle_ms", 800))


def minute(session: str, hat: str, kind: str, text: str, said_by: str = "") -> None:
    C.add_minute(session, hat, kind, text, said_by)


def line(s: str = "") -> None:
    print(s)


def sev_sort(findings: list) -> list:
    return sorted(findings, key=lambda f: R.SEV_ORDER.index(f["severity"]))


def show_result(res: dict, session: str) -> None:
    line("%s (%s hat): %s" % (res["skill"], hat_name(res["hat"]), VERDICT_WORDS.get(res["verdict"], res["verdict"])))
    line("  " + res["summary"])
    fs = sev_sort(res["findings"])
    for n, f in enumerate(fs[:SHOW_MAX], 1):
        line("  %d. [%s] %s: %s" % (n, f["severity"], f["where"], f["what"]))
        if f.get("evidence"):
            line("       seen: %s" % f["evidence"])
        if f.get("next_step"):
            line("       next: %s" % f["next_step"])
    if len(fs) > SHOW_MAX:
        line("  ... %d more in %s" % (len(fs) - SHOW_MAX, Path(session) / "findings" / (res["skill"] + ".json")))
    for x in res.get("files", []):
        if x:
            line("  file: %s" % x)
    if res.get("not_checked"):
        line("  not checked: " + "; ".join(res["not_checked"][:3]) + ("; and %d more (see the findings file)" % (len(res["not_checked"]) - 3) if len(res["not_checked"]) > 3 else ""))


def state_of(sess: dict, results: dict, sid: str) -> str:
    if sid in results:
        return VERDICT_WORDS.get(results[sid]["verdict"], results[sid]["verdict"])
    if sid in sess.get("skipped", {}):
        return "skipped: " + sess["skipped"][sid]
    return "not run"


# ------------------------------------------------------------------------------------------------ init
def cmd_init(a) -> int:
    sp = Path(a.session)
    where = C.inside_a_git_tree(sp)                                  # works for a folder that is not made yet: it looks at the folders above
    if where:
        raise SystemExit("refused: %s is inside the git repository at %s. A session holds the person's data (the responses the page loaded). Use a folder outside any repository." % (sp, where))
    if (sp / "session.json").is_file():
        raise SystemExit("there is already a session here: %s (use `next` to continue)" % sp)
    page = a.page
    if not page.startswith(("http://", "https://")):
        p = Path(page)
        if not p.exists():
            raise SystemExit("the page is neither a web address nor a file or folder here: %s" % page)
        page = str(p.resolve())
    sess = {"format": C.FORMAT, "created": C.now(), "page": page, "setup": a.setup or [], "storage_state": str(Path(a.storage_state).resolve()) if a.storage_state else "",
            "allow_post": a.allow_post or "", "width": a.width, "height": a.height, "settle_ms": a.settle, "runs": {}, "skipped": {}, "hats_worn": {},
            "inputs": {k: v for k, v in {"data": a.data, "source": a.source, "before": a.before, "after": a.after, "key": a.key, "id_field": a.id_field, "text_field": a.text_field,
                                         "allowed": a.allowed, "expect": a.expect}.items() if v}}
    sp.mkdir(parents=True, exist_ok=True)
    C.save_session(a.session, sess)
    (sp / "README.txt").write_text("This folder is a data audit session. It holds the data the person's page loaded, records picked from their data, and (visits/storage.json) what the\n"
                                   "browser kept after the first visit, which can include a sign-in. Keep it out of any repository and do not share it.\n"
                                   "Start with:  %s\n" % C.cmd("next", a.session), encoding="utf-8")
    minute(a.session, "chief-of-staff", "started", "Audit started for %s." % page)
    line("Audit session made: %s" % sp)
    line("Page: %s" % page)
    if importlib.util.find_spec("playwright") is None:
        line("Playwright is not installed, so the checks that open the page cannot run yet:  pip install playwright && playwright install chromium")
    line("The audit sends no write that it can see: a request that is not a GET, HEAD or OPTIONS is refused and listed, a WebSocket goes nowhere, and workers are not allowed. It cannot")
    line("know whether a GET changes something on the server, and it opens the page many times.")
    if a.storage_state:
        line("The sign-in you gave is read, not changed; a COPY of what the browser holds after the first visit is saved in %s (readable by you only). Do not share this folder." % (sp / "visits" / "storage.json"))
    line("Next: %s" % C.cmd("next", a.session))
    return 0


# ------------------------------------------------------------------------------------------------ next, hat, status, list
def run_command(sess: dict, session: str, sid: str, hat: str | None = None) -> str:
    """The command to run one check, as it can be copied. It names the hat, so the command is refused if the hat does not own the check."""
    inp = sess.get("inputs", {})
    base = ["run", session, sid] + (["--hat", hat] if hat else [])
    if sid == "known":
        base += ["--data", inp.get("data") or "FILE"]
    elif sid == "scan":
        base += ["--source", inp.get("source") or "DIR"]
    elif sid == "diff":
        base += ["--before", inp.get("before") or "FILE", "--after", inp.get("after") or "FILE", "--key", inp.get("key") or "FIELD"]
    return C.cmd(*base)


def record_command(sess: dict, session: str, sid: str, hat: str) -> str:
    """The command for a skill that is not a check (minutes, brief, skip)."""
    if sid == "minutes":
        return C.cmd("minutes", session, "--hat", hat, "--kind", "decision", "--said-by", "NAME", "--text", '"WHAT THEY SAID, IN THEIR WORDS"')
    if sid == "brief":
        return C.cmd("brief", session)
    return C.cmd("skip", session, "CHECK", "--hat", hat, "--because", '"WHY IT WILL NOT BE RUN"')


def missing_inputs(sess: dict, sid: str) -> list:
    inp = sess.get("inputs", {})
    need = {"known": ["data"], "scan": ["source"], "diff": ["before", "after", "key"]}.get(sid, [])
    return [n for n in need if not inp.get(n)]


def cmd_next(a) -> int:
    sess = C.load_session(a.session)
    results = C.load_results(a.session)
    skills = C.skills()
    for sid in CHECKS:
        failed = sid in results and results[sid]["verdict"] == "not-run" and sid not in sess.get("skipped", {})
        if (sid in results and not failed) or sid in sess.get("skipped", {}):
            continue
        hat = skills[sid]["default_hat"]
        if failed:
            line("Next: %s (%s hat) could not run: %s" % (sid, hat_name(hat), C.short(results[sid]["summary"], 200)))
            line("  Put that right and run it again, or skip it so the brief says it was not looked at.")
        else:
            line("Next: %s (%s hat)." % (sid, hat_name(hat)))
        line("  What it does: %s" % skills[sid]["does"])
        miss = missing_inputs(sess, sid)
        if miss:
            line("  It needs from the person: %s." % ", ".join({"data": "a file of their own records (JSON, JSON lines or CSV)", "source": "the folder of the app's source files",
                                                                 "before": "the copy of the data from before the change", "after": "the copy from after it", "key": "the name of the field that identifies a record"}[m] for m in miss))
            line("  Ask for it. If they have none, skip it so the brief says so:")
            line("    %s" % C.cmd("skip", a.session, sid, "--because", '"the person has no %s to give"' % "/".join(miss)))
            line("  Or give it and run:  %s" % run_command(sess, a.session, sid, hat))
        else:
            line("  Run:  %s" % run_command(sess, a.session, sid, hat))
            if failed:
                line("  Or skip it:  %s" % C.cmd("skip", a.session, sid, "--because", '"WHY"'))
            if hat not in sess.get("hats_worn", {}):
                line("  (Own agent for this hat? Give it:  %s)" % C.cmd("hat", a.session, hat))
        line("Then:  %s" % C.cmd("next", a.session))
        return 0
    brief = Path(a.session) / "BRIEF.md"
    if not brief.is_file() or brief.stat().st_mtime < (Path(a.session) / "session.json").stat().st_mtime:
        line("Next: put the findings together (chief of staff hat).")
        line("  Run:  %s" % C.cmd("brief", a.session))
        return 0
    line("Every check has run or been skipped, and the brief is up to date.")
    line("Give the person %s and read them the part headed \"Where this stands\". Ask the questions at the end. Write what they decide in the minutes:" % (Path(a.session) / "BRIEF.md"))
    line("  %s" % C.cmd("minutes", a.session, "--kind", "decision", "--said-by", "NAME", "--text", '"WHAT THEY SAID"'))
    return 0


def cmd_hat(a) -> int:
    sess = C.load_session(a.session)
    results = C.load_results(a.session)
    hats, skills = C.hats(), C.skills()
    if a.hat not in hats:
        raise SystemExit("no such hat: %s (the hats are: %s)" % (a.hat, ", ".join(C.hat_order())))
    h = hats[a.hat]
    line("You are wearing the %s hat." % h["name"])
    line("Purpose: %s" % h["purpose"])
    line("")
    line("Rules for every hat:")
    for r in C.read_json(C.KIT / "hats.json")["never_for_every_hat"]:
        line("  - Never: %s" % r)
    line("")
    line("Your skills (the commands refuse a hat that names one it does not own; nothing proves who typed them):")
    for sid in h["skills"]:
        if skills[sid]["kind"] != "check":
            line("  - %s: %s" % (sid, skills[sid]["does"]))
            line("      run: %s" % record_command(sess, a.session, sid, a.hat))
            continue
        miss = missing_inputs(sess, sid)
        line("  - %s [%s]: %s" % (sid, state_of(sess, results, sid), skills[sid]["does"]))
        line("      run: %s%s" % (run_command(sess, a.session, sid, a.hat), "   (needs %s from the person)" % ", ".join(miss) if miss else ""))
        line("      cannot find: %s" % "; ".join(skills[sid]["cannot_find"]))
    line("")
    line("Ask the person:")
    for q in h["asks_the_person"]:
        line("  - %s" % q)
    line("Look for: %s." % "; ".join(h["looks_for"]))
    line("Hand to:")
    for k, v in h["hands_to"].items():
        line("  - %s: %s" % (hat_name(k), v))
    line("")
    line("Findings go into %s. When you are done:  %s" % (Path(a.session) / "findings", C.cmd("next", a.session)))
    C.update_session(a.session, lambda x: x.setdefault("hats_worn", {}).__setitem__(a.hat, C.now()))
    minute(a.session, a.hat, "hat", "The %s hat was put on." % h["name"])
    return 0


def cmd_status(a) -> int:
    sess = C.load_session(a.session)
    results = C.load_results(a.session)
    line("Page: %s" % sess["page"])
    for sid in CHECKS:
        line("  %-8s %-24s %s" % (sid, hat_name(C.skills()[sid]["default_hat"]), state_of(sess, results, sid)))
    state, reasons = R.readiness(sess, results)
    line("Where this stands: %s%s" % (state, " (%s)" % "; ".join(reasons) if reasons else ""))
    line("Hats that have run a check: %s. Put on with `hat`: %s." % (", ".join(sorted({r["hat"] for r in results.values()})) or "none", ", ".join(sorted(sess.get("hats_worn", {}))) or "none"))
    return 0


def cmd_list(a) -> int:
    line("Checks (skills.json):")
    for s in C.read_json(C.KIT / "skills.json")["skills"]:
        line("  %-8s %-9s %s" % (s["id"], s["kind"], s["does"].split(". ")[0].rstrip(".") + "."))
    line("")
    line("Hats (hats.json):")
    for h in C.read_json(C.KIT / "hats.json")["hats"]:
        line("  %-26s %s  [runs: %s]" % (h["id"], h["name"], ", ".join(h["skills"])))
    return 0


# ------------------------------------------------------------------------------------------------ run
def _remember(sess: dict, session: str, a) -> dict:
    """Inputs given on the command line are kept in the session, so `next` and `brief` show the same commands. A new --data file drops the ID and text fields kept for the old one."""
    def keep(x):
        inp = x.setdefault("inputs", {})
        if getattr(a, "data", None) and inp.get("data") and inp["data"] != a.data:
            inp.pop("id_field", None)
            inp.pop("text_field", None)
        for k in ("data", "source", "before", "after", "key", "id_field", "text_field", "allowed", "expect"):
            v = getattr(a, k, None)
            if v:
                inp[k] = v
    return C.update_session(session, keep).get("inputs", {})


def cmd_run(a) -> int:
    sess = C.load_session(a.session)
    skills = C.skills()
    sid = a.skill
    if sid not in skills or skills[sid]["kind"] != "check":
        raise SystemExit("%s is not a check you can run this way. The checks are: %s" % (sid, ", ".join(CHECKS)))
    hat = a.hat or skills[sid]["default_hat"]
    need_hat(hat, sid)
    inp = _remember(sess, a.session, a)
    sp = Path(a.session)
    if sid in ("trace", "canary", "outage", "marks", "states"):
        import audit_checks as checks
        with runner_for(sess) as r:
            res = getattr(checks, sid)(sp, r, hat, fresh=a.fresh)
    elif sid == "known":
        import audit_files as files
        import audit_net as net
        if not inp.get("data"):
            raise SystemExit("known needs the person's own records: --data FILE (JSON, JSON lines or CSV)")
        rec = net.load_visit(sp, "record") if not a.fresh else None
        if rec is None:
            with runner_for(sess) as r:
                rec = net.get_visit(r, sp, "record", fresh=True)
        res = files.known(sp, hat, rec, inp["data"], inp.get("id_field"), inp.get("text_field"), a.sample)
    elif sid == "scan":
        import audit_files as files
        if not inp.get("source"):
            raise SystemExit("scan needs the app's source folder: --source DIR")
        res = files.scan(sp, hat, inp["source"])
    else:
        import audit_files as files
        miss = missing_inputs(sess, "diff")
        if miss:
            raise SystemExit("diff needs: --%s" % ", --".join(miss))
        res = files.diff(sp, hat, inp["before"], inp["after"], inp["key"], [x for x in (inp.get("allowed") or "").split(",") if x], [x for x in (inp.get("expect") or "").split(",") if x])
    C.save_result(a.session, res)
    n_high = sum(1 for f in res["findings"] if f["severity"] == "high")
    minute(a.session, hat, "ran", "Ran %s: %s. %d finding(s), %d serious." % (sid, VERDICT_WORDS.get(res["verdict"], res["verdict"]), len(res["findings"]), n_high))
    show_result(res, a.session)
    line("Next:  %s" % C.cmd("next", a.session))
    return 1 if a.strict and res["verdict"] in ("problem", "not-run") else 0


def cmd_skip(a) -> int:
    sess = C.load_session(a.session)
    if a.skill not in CHECKS:
        raise SystemExit("only a check can be skipped: %s" % ", ".join(CHECKS))
    need_hat(a.hat, "skip")
    done = C.load_results(a.session).get(a.skill)
    if done is not None and done["verdict"] != "not-run":
        raise SystemExit("%s has already run (%s); a check that ran cannot be skipped. Its findings stand." % (a.skill, VERDICT_WORDS.get(done["verdict"], done["verdict"])))
    if len((a.because or "").strip()) < 5:
        raise SystemExit("give the reason in words (--because \"...\"): the brief lists it as not checked")
    C.update_session(a.session, lambda x: x.setdefault("skipped", {}).__setitem__(a.skill, a.because.strip()))
    minute(a.session, a.hat, "skipped", "%s will not be run. Reason: %s" % (a.skill, a.because.strip()))
    line("Recorded: %s skipped. The brief will list it as not checked, with the reason, and will not say \"clear\" while it is skipped." % a.skill)
    line("Next:  %s" % C.cmd("next", a.session))
    return 0


# ------------------------------------------------------------------------------------------------ minutes, brief, verify
PERSON_KINDS = ("said", "decision", "note")


def cmd_minutes(a) -> int:
    C.load_session(a.session)
    if a.verify:
        bad = C.minutes_chain_problems(a.session)
        for b in bad:
            line("PROBLEM: " + b)
        line("The minutes hold %d entries; %s." % (len(C.minutes_entries(a.session)), "the chain holds" if not bad else "the chain is broken"))
        return 1 if bad else 0
    if a.show or not a.text:
        for e in C.minutes_entries(a.session):
            line("%d. %s · %s · %s%s: %s" % (e["n"], e["at"], e["hat"], e["kind"], (" · " + e["said_by"]) if e.get("said_by") else "", e["text"]))
        return 0
    need_hat(a.hat, "minutes")
    if a.kind not in PERSON_KINDS:
        raise SystemExit("--kind must be one of %s (the audit writes the other kinds itself)" % ", ".join(PERSON_KINDS))
    if len(a.text.strip()) < 3:
        raise SystemExit("--text is empty")
    if a.kind in ("said", "decision") and not (a.said_by or "").strip():
        raise SystemExit("a %s needs --said-by NAME: a decision with no name is not a decision. Read it back to the person first, in their words." % a.kind)
    e = C.add_minute(a.session, a.hat, a.kind, a.text, a.said_by or "")
    line("Entry %d written (%s). It cannot be changed; to correct it, write another entry." % (e["n"], e["hash"]))
    return 0


def cmd_brief(a) -> int:
    sess = C.load_session(a.session)
    need_hat("chief-of-staff", "brief")
    path, rep = R.write(a.session)
    minute(a.session, "chief-of-staff", "brief", "Brief written: %s." % rep["state"])
    line("Where this stands: %s" % rep["state"].upper())
    for r in rep["reasons"]:
        line("  - %s" % r)
    c = rep["counts"]
    line("Findings: %s" % (", ".join("%d %s" % (c[k], k) for k in R.SEV_ORDER if c.get(k)) or "none"))
    line("Brief: %s" % path)
    line("Give the person the brief and read them the part headed \"Where this stands\". Then ask the questions at its end.")
    return 0


def cmd_verify(a) -> int:
    sess = C.load_session(a.session)
    bad = list(C.minutes_chain_problems(a.session))
    for sid, r in C.load_results(a.session).items():
        for k in ("format", "skill", "hat", "ran_at", "verdict", "summary", "findings", "not_checked"):
            if k not in r:
                bad.append("findings/%s.json is missing %r" % (sid, k))
        if r.get("skill") != sid:
            bad.append("findings/%s.json says it is for %r" % (sid, r.get("skill")))
        if r.get("verdict") == "clear" and r.get("verdict") != C.verdict_of(r.get("findings", [])):
            bad.append("findings/%s.json says clear but has findings" % sid)
        for f in r.get("findings", []):
            if f.get("severity") not in C.SEVERITIES:
                bad.append("findings/%s.json has a finding with severity %r" % (sid, f.get("severity")))
    for sid in sess.get("skipped", {}):
        got = C.load_results(a.session).get(sid)
        if got is not None and got.get("verdict") != "not-run":
            bad.append("%s is both skipped and run" % sid)
    for b in bad:
        line("PROBLEM: " + b)
    line("Checked the minutes' fingerprints and the findings files: %s." % ("no problems" if not bad else "%d problem(s)" % len(bad)))
    return 1 if bad else 0


# ------------------------------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    p = sub.add_parser("init")
    p.add_argument("session")
    p.add_argument("--page", required=True, help="a web address, or a file or folder of the app")
    p.add_argument("--setup", action="append", metavar="STEP", help='steps to reach the screen, as tools/gui_checks/site_map.py takes them: "click:Label", "wait:500", "goto:URL". A click is a click on the person\'s page: it can start a GET that has an effect')
    p.add_argument("--storage-state", metavar="FILE", help="a Playwright storage-state file (a sign-in the person made); it is read, not changed, and a copy of what the browser holds after the first visit is kept in the session folder")
    p.add_argument("--allow-post", metavar="REGEX", help="addresses where a POST is a read (a search, a query); everything else that writes is refused")
    p.add_argument("--width", type=int, default=1440)
    p.add_argument("--height", type=int, default=900)
    p.add_argument("--settle", type=int, default=800, metavar="MS", help="how long the page must be quiet on the network before the screen is read (raise it for a page that draws late)")
    for k, h in (("data", "the person's own records (JSON, JSON lines, CSV), for `known`"), ("source", "the app's source folder, for `scan`"), ("before", "the earlier copy, for `diff`"),
                 ("after", "the later copy, for `diff`"), ("key", "the field that identifies a record, for `diff`"), ("id_field", "the ID field in the data, for `known`"), ("text_field", "the text field, for `known`"),
                 ("allowed", "fields meant to change, comma separated, for `diff`"), ("expect", "records meant to change, comma separated, for `diff`")):
        p.add_argument("--" + k.replace("_", "-"), dest=k, help=h)
    p.set_defaults(fn=cmd_init)
    for name, fn in (("next", cmd_next), ("status", cmd_status), ("brief", cmd_brief), ("verify", cmd_verify)):
        p = sub.add_parser(name)
        p.add_argument("session")
        p.set_defaults(fn=fn)
    p = sub.add_parser("list")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("hat")
    p.add_argument("session")
    p.add_argument("hat")
    p.set_defaults(fn=cmd_hat)
    p = sub.add_parser("run")
    p.add_argument("session")
    p.add_argument("skill")
    p.add_argument("--hat", help="which hat runs it (default: the check's own hat; a hat may run only its own checks)")
    p.add_argument("--fresh", action="store_true", help="open the page again instead of using the visits saved in the session")
    p.add_argument("--strict", action="store_true", help="exit 1 when the check finds a problem or could not run")
    p.add_argument("--sample", type=int, default=5, help="how many records `known` picks")
    for k in ("data", "source", "before", "after", "key", "id_field", "text_field", "allowed", "expect"):
        p.add_argument("--" + k.replace("_", "-"), dest=k)
    p.set_defaults(fn=cmd_run)
    p = sub.add_parser("skip")
    p.add_argument("session")
    p.add_argument("skill")
    p.add_argument("--because", required=True)
    p.add_argument("--hat", default="chief-of-staff")
    p.set_defaults(fn=cmd_skip)
    p = sub.add_parser("minutes")
    p.add_argument("session")
    p.add_argument("--hat", default="scribe")
    p.add_argument("--kind", default="note")
    p.add_argument("--text")
    p.add_argument("--said-by", dest="said_by")
    p.add_argument("--show", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.set_defaults(fn=cmd_minutes)
    return ap


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
