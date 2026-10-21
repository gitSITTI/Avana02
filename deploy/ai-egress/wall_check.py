#!/usr/bin/env python3
"""Does the network wall around the AI model stand? A check IT runs from each place, then combines.

The AI gate (reqin.aigate, and the gateway in front of the model) refuses to send text the data sheet does not cover. The gate is software; the wall is the network.
This script tests the wall: it tries to open TCP connections, from the machine it runs on, to the places a plan says must be reachable and the places that must not be.
It uses only Python's standard library and sends no requirement text (it sends nothing but an empty connection and, for one kind of check, a GET of /v1/health).

  python3 wall_check.py run     --plan wall.json --role app      [--timeout 3] [--out app.json]      run on a machine of that role; prints what it found, exit 1 on a surprise
  python3 wall_check.py combine --plan wall.json app.json gateway.json model.json [--max-age-hours 24]     the verdict, from the reports of every role
  python3 wall_check.py self-test                                                                        runs the checks against sockets on this machine, to show the script works here
  python3 wall_check.py hash --plan wall.json                                                             the fingerprint of the plan (reports carry it)

Why two steps. A connection to the model that FAILS from a workstation proves the wall only if the model was up and listening. A model that is switched off "passes" every
wall check. So each "blocked" check names an "open" check (`target_up_from`) that shows the same address answering from the place that is allowed to reach it, and `combine`
refuses a blocked check that has no such proof, or whose proof failed, or was made a different day. A single `run` says BLOCKED (not proven up) and leaves the verdict to `combine`.

Reports are evidence for a mistake or an audit, not protection against someone who forges one: they carry the plan's SHA-256, this script's SHA-256, the machine's name and the
time. Keep them with the firewall configuration they were run against.

The plan is a JSON file, format "reqin-wall/1":
  {"format": "reqin-wall/1", "checks": [
     {"id": "app-to-gateway", "from": "app", "to": "10.0.0.5:8790", "expect": "open", "why": "...", "http": {"path": "/v1/health", "status": 200, "contains": "ok"}},
     {"id": "app-to-model",   "from": "app", "to": "10.0.1.9:8000", "expect": "blocked", "target_up_from": "gateway-to-model", "why": "..."},
     {"id": "gateway-to-model", "from": "gateway", "to": "10.0.1.9:8000", "expect": "open", "why": "..."},
     {"id": "model-to-internet", "from": "model", "to": "1.1.1.1:443", "expect": "blocked", "target_up_from": "app-to-internet", "why": "..."}]}
`to` is host:port (an IPv6 address in square brackets). Use IP addresses for what must be blocked: a name that does not resolve proves the name is cut off, not the route
(set "allow_unresolved": true to accept that, knowing it is weaker). Connection attempts bypass any HTTP proxy set in the environment: this tests the path itself.
"""
from __future__ import annotations

import argparse
import errno
import hashlib
import http.client
import json
import re
import socket
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PLAN_FORMAT = "reqin-wall/1"
REPORT_FORMAT = "reqin-wall-report/1"
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
ROLE_RE = re.compile(r"[a-z][a-z0-9_-]{0,31}")
CHECK_KEYS = {"id", "from", "to", "expect", "why", "http", "target_up_from", "allow_unresolved"}
HTTP_KEYS = {"method", "path", "status", "contains"}

# what a connection attempt can come to
OPEN, REFUSED, TIMEOUT, UNREACHABLE, UNRESOLVED, ERROR = "open", "refused", "timeout", "unreachable", "unresolved", "error"
BLOCKED_OUTCOMES = {REFUSED, TIMEOUT, UNREACHABLE}          # the wall did its job (or nothing was listening: that is what `target_up_from` is for)
_UNREACH = {errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ENETDOWN, errno.EHOSTDOWN, errno.EACCES, errno.EPERM}
_UNREACH |= {getattr(errno, n) for n in ("EADDRNOTAVAIL", "ENOPROTOOPT") if hasattr(errno, n)}


class PlanError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------------------------- the plan

def split_target(to: str) -> tuple[str, int]:
    m = re.fullmatch(r"\[([0-9A-Fa-f:.%a-zA-Z]+)\]:(\d{1,5})", to) or re.fullmatch(r"([^\s:\[\]]+):(\d{1,5})", to)
    if not m or not 1 <= int(m.group(2)) <= 65535:
        raise PlanError(f"{to!r}: write host:port, an IPv6 address in square brackets")
    return m.group(1), int(m.group(2))


def load_plan(path: str | Path) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
        plan = json.loads(raw)
    except (OSError, ValueError) as e:
        raise PlanError(f"cannot read the plan {path}: {e}") from None
    if not isinstance(plan, dict) or plan.get("format") != PLAN_FORMAT or not isinstance(plan.get("checks"), list) or not plan["checks"]:
        raise PlanError(f'the plan must be {{"format": "{PLAN_FORMAT}", "checks": [...]}} with at least one check')
    ids: dict[str, dict[str, Any]] = {}
    for i, c in enumerate(plan["checks"], 1):
        if not isinstance(c, dict) or set(c) - CHECK_KEYS or not {"id", "from", "to", "expect", "why"} <= set(c):
            raise PlanError(f"check {i}: needs id, from, to, expect and why, and nothing but {', '.join(sorted(CHECK_KEYS))}")
        if not isinstance(c["id"], str) or not ID_RE.fullmatch(c["id"]) or c["id"] in ids:
            raise PlanError(f"check {i}: the id must be unique letters, digits, . _ -")
        if not isinstance(c["from"], str) or not ROLE_RE.fullmatch(c["from"]):
            raise PlanError(f"check {c['id']}: 'from' is a role name in lower case (app, gateway, model, ...)")
        if c["expect"] not in ("open", "blocked") or not isinstance(c["why"], str) or not c["why"].strip():
            raise PlanError(f"check {c['id']}: expect is open or blocked, and why says what the check protects")
        split_target(c["to"] if isinstance(c["to"], str) else "")
        if "allow_unresolved" in c and (not isinstance(c["allow_unresolved"], bool) or c["expect"] != "blocked"):
            raise PlanError(f"check {c['id']}: allow_unresolved is true or false, and only for a blocked check")
        h = c.get("http")
        if h is not None:
            if c["expect"] != "open" or not isinstance(h, dict) or set(h) - HTTP_KEYS or not isinstance(h.get("path"), str) or not h["path"].startswith("/"):
                raise PlanError(f"check {c['id']}: http is for an open check: {{path, status, contains}}")
            if h.get("method", "GET") not in ("GET", "HEAD") or not isinstance(h.get("status", 200), int) or not isinstance(h.get("contains", ""), str):
                raise PlanError(f"check {c['id']}: http method is GET or HEAD; status a number; contains text")
        ids[c["id"]] = c
    for c in plan["checks"]:
        up = c.get("target_up_from")
        if up is None:
            continue
        p = ids.get(up)
        if c["expect"] != "blocked" or not isinstance(up, str) or not p:
            raise PlanError(f"check {c['id']}: target_up_from names an open check of the same plan, and only a blocked check has one")
        if p["expect"] != "open" or p["to"] != c["to"] or p["from"] == c["from"]:
            raise PlanError(f"check {c['id']}: target_up_from must be an open check of the same address from another role ({up} is not)")
    plan["_sha256"] = hashlib.sha256(raw).hexdigest()
    return plan


def script_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------------ one attempt

def _classify(e: BaseException) -> str:
    if isinstance(e, socket.timeout) or isinstance(e, TimeoutError):
        return TIMEOUT
    if isinstance(e, ConnectionRefusedError) or getattr(e, "errno", None) == errno.ECONNREFUSED:
        return REFUSED
    if isinstance(e, (ConnectionResetError, ConnectionAbortedError)):
        return REFUSED
    if getattr(e, "errno", None) in _UNREACH:
        return UNREACHABLE
    return ERROR


def attempt(to: str, timeout: float, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Try to open a connection to host:port, on every address the name has. Never uses a proxy. Returns the outcome and what was seen."""
    host, port = split_target(to)
    t0 = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        return {"outcome": UNRESOLVED, "detail": f"the name did not resolve ({e.strerror or e})", "ms": round((time.monotonic() - t0) * 1000), "addresses": {}}
    addrs: dict[str, str] = {}
    opened = None
    for fam, typ, proto, _, sa in infos:
        a = sa[0]
        if a in addrs:
            continue
        s = socket.socket(fam, typ, proto)
        s.settimeout(timeout)
        try:
            s.connect(sa)
            addrs[a] = OPEN
            opened = opened or (fam, sa)
        except OSError as e:
            addrs[a] = _classify(e) if not isinstance(e, socket.gaierror) else UNRESOLVED
            if addrs[a] == ERROR:
                addrs[a] = f"{ERROR}: {e.strerror or e.__class__.__name__}"
        finally:
            s.close()
    ms = round((time.monotonic() - t0) * 1000)
    if opened:
        out: dict[str, Any] = {"outcome": OPEN, "detail": f"connected to {opened[1][0]} in {ms} ms", "ms": ms, "addresses": addrs}
        if probe:
            out["http"] = _http_probe(opened[1][0], port, probe, timeout)
        return out
    kinds = set(v.split(":")[0] for v in addrs.values())
    for k in (UNREACHABLE, TIMEOUT, REFUSED):          # when addresses differ, say the most "walled" thing first
        if k in kinds and kinds <= BLOCKED_OUTCOMES:
            return {"outcome": k if len(kinds) == 1 else "blocked", "detail": ", ".join(f"{a}: {v}" for a, v in addrs.items()), "ms": ms, "addresses": addrs}
    return {"outcome": ERROR, "detail": ", ".join(f"{a}: {v}" for a, v in addrs.items()), "ms": ms, "addresses": addrs}


def _http_probe(addr: str, port: int, spec: dict[str, Any], timeout: float) -> dict[str, Any]:
    want_status, want_text = spec.get("status", 200), spec.get("contains", "")
    try:
        c = http.client.HTTPConnection(addr, port, timeout=timeout)
        c.request(spec.get("method", "GET"), spec["path"], headers={"Connection": "close", "User-Agent": "reqin-wall-check"})
        r = c.getresponse()
        body = r.read(65536).decode("utf-8", "replace")
        c.close()
        ok = r.status == want_status and want_text in body
        return {"ok": ok, "status": r.status, "detail": "" if ok else f"answered {r.status}" + (f" without {want_text!r}" if want_text not in body else "")}
    except (OSError, http.client.HTTPException) as e:
        return {"ok": False, "status": 0, "detail": f"no HTTP answer ({e.__class__.__name__})"}


# ---------------------------------------------------------------------------------------------------------------- run

def judge(check: dict[str, Any], res: dict[str, Any]) -> dict[str, Any]:
    """Does what happened match what the plan expects? Adds ok and a one-line verdict."""
    out = res["outcome"]
    if check["expect"] == "open":
        h = res.get("http")
        if out != OPEN:
            ok, line = False, f"should be reachable and is not ({out}): {res['detail']}"
        elif h is not None and not h["ok"]:
            ok, line = False, f"reachable, but not the right answer: {h['detail']}"
        else:
            ok, line = True, "reachable, as planned" + (f"; answered {h['status']}" if h else "")
    else:
        if out == OPEN:
            ok, line = False, f"IS REACHABLE but must not be: {res['detail']}"
        elif out in BLOCKED_OUTCOMES or out == "blocked":
            ok = True
            line = f"blocked ({out}); " + ("not yet shown that the target is up: `combine` needs the proof" if check.get("target_up_from") else "no proof given that the target is up")
        elif out == UNRESOLVED:
            ok = bool(check.get("allow_unresolved"))
            line = "the name does not resolve (accepted, weaker: it shows the name is cut off, not the route)" if ok else "the name did not resolve, so nothing was tested: use the IP address, or set allow_unresolved"
        else:
            ok, line = False, f"could not tell ({res['detail']})"
    return dict(res, ok=ok, verdict=line)


def run_role(plan: dict[str, Any], role: str, timeout: float) -> dict[str, Any]:
    checks = [c for c in plan["checks"] if c["from"] == role]
    if not checks:
        roles = sorted({c["from"] for c in plan["checks"]})
        raise PlanError(f"the plan has no checks from role {role!r}; its roles are: {', '.join(roles)}")
    results = []
    for c in checks:
        r = judge(c, attempt(c["to"], timeout, c.get("http")))
        results.append({"id": c["id"], "to": c["to"], "expect": c["expect"], "why": c["why"], **r})
    return {"format": REPORT_FORMAT, "role": role, "host": socket.gethostname(), "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "plan_sha256": plan["_sha256"], "script_sha256": script_hash(), "timeout_s": timeout, "results": results, "ok": all(x["ok"] for x in results)}


# ------------------------------------------------------------------------------------------------------------ combine

def _when(s: Any) -> datetime | None:
    try:
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else None
    except (TypeError, ValueError):
        return None


def combine(plan: dict[str, Any], reports: list[dict[str, Any]], max_age_hours: float = 24, now: datetime | None = None) -> tuple[bool, list[str]]:
    """The verdict from the reports of every role: (ok, lines). Every problem is a line starting with 'FAIL'."""
    lines: list[str] = []
    fail = lambda m: lines.append("FAIL " + m)          # noqa: E731
    by_role: dict[str, dict[str, Any]] = {}
    for rp in reports:
        if not isinstance(rp, dict) or rp.get("format") != REPORT_FORMAT or not isinstance(rp.get("results"), list) or not isinstance(rp.get("role"), str):
            fail("a file is not a wall report"); continue
        if rp.get("plan_sha256") != plan["_sha256"]:
            fail(f"the report from {rp.get('role')} ({rp.get('host')}) was run against a different plan"); continue
        if _when(rp.get("at")) is None:
            fail(f"the report from {rp['role']} has no usable time"); continue
        old = by_role.get(rp["role"])
        if old is None or _when(rp["at"]) > _when(old["at"]):      # a later run replaces an earlier one
            by_role[rp["role"]] = rp
    if len({rp.get("script_sha256") for rp in by_role.values()}) > 1:
        fail("the reports were made by different copies of this script")
    when = [_when(rp["at"]) for rp in by_role.values()]
    if when:
        now = now or datetime.now(timezone.utc)
        if max(when) - min(when) > timedelta(hours=max_age_hours):
            fail(f"the reports are more than {max_age_hours:g} hours apart")
        if now - min(when) > timedelta(hours=max_age_hours * 7):
            fail("the oldest report is more than a week old: run the checks again")
    res: dict[str, dict[str, Any]] = {}
    for role, rp in by_role.items():
        for r in rp["results"]:
            if isinstance(r, dict) and isinstance(r.get("id"), str):
                res[r["id"]] = dict(r, _role=role)
    ok_count = 0
    for c in plan["checks"]:
        r = res.get(c["id"])
        if r is None:
            fail(f"{c['id']}: no report from role {c['from']!r} has this check")
            continue
        if r["_role"] != c["from"] or r.get("to") != c["to"] or r.get("expect") != c["expect"]:
            fail(f"{c['id']}: the report does not match the plan's check")
            continue
        if r.get("ok") is not True:
            fail(f"{c['id']} ({c['from']} -> {c['to']}, {c['expect']}): {r.get('verdict', 'not as planned')}")
            continue
        if c["expect"] == "blocked":
            up = c.get("target_up_from")
            if not up:
                fail(f"{c['id']}: blocked, but the plan gives no check that shows {c['to']} is up (target_up_from), so a switched-off target would pass")
                continue
            pr = res.get(up)
            if pr is None or pr.get("ok") is not True or pr.get("outcome") != OPEN:
                fail(f"{c['id']}: blocked, but {c['to']} was not shown to be up (check {up} {'is missing' if pr is None else 'did not pass'})")
                continue
        ok_count += 1
    extra = [i for i in res if i not in {c['id'] for c in plan["checks"]}]
    if extra:
        fail("reports hold checks the plan does not: " + ", ".join(sorted(extra)[:5]))
    ok = not any(l.startswith("FAIL") for l in lines)
    lines.append(("PASS" if ok else "RESULT: the wall is NOT shown to stand;") + f" {ok_count} of {len(plan['checks'])} checks hold" + (f" (roles seen: {', '.join(sorted(by_role))})" if by_role else ""))
    return ok, lines


# ---------------------------------------------------------------------------------------------------------- self-test

def self_test() -> int:
    """Open and closed sockets on this machine, and the combine rules on made-up reports. Shows the script works here; says nothing about your network."""
    import tempfile
    failures: list[str] = []

    def check(cond: bool, what: str) -> None:
        print(("PASS " if cond else "FAIL ") + what)
        if not cond:
            failures.append(what)

    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    up_port = srv.getsockname()[1]
    stop = threading.Event()

    def accept() -> None:
        srv.settimeout(0.2)
        while not stop.is_set():
            try:
                c, _ = srv.accept()
                c.close()
            except OSError:
                pass

    th = threading.Thread(target=accept, daemon=True)
    th.start()
    tmp = socket.socket()
    tmp.bind(("127.0.0.1", 0))
    closed_port = tmp.getsockname()[1]
    tmp.close()
    try:
        a = attempt(f"127.0.0.1:{up_port}", 2)
        check(a["outcome"] == OPEN, "a listening port is seen as open")
        b = attempt(f"127.0.0.1:{closed_port}", 2)
        check(b["outcome"] == REFUSED, "a closed port is seen as refused")
        check(attempt("no-such-name.invalid:80", 2)["outcome"] == UNRESOLVED, "a name that does not exist is 'unresolved', not 'blocked'")
        plan_doc = {"format": PLAN_FORMAT, "checks": [
            {"id": "app-gateway", "from": "app", "to": f"127.0.0.1:{up_port}", "expect": "open", "why": "the pipeline reaches the gateway"},
            {"id": "gateway-model", "from": "gateway", "to": f"127.0.0.1:{up_port}", "expect": "open", "why": "the gateway reaches the model"},
            {"id": "app-model", "from": "app", "to": f"127.0.0.1:{closed_port}", "expect": "blocked", "why": "the pipeline cannot reach the model", "target_up_from": "ok-up"},
            {"id": "ok-up", "from": "gateway", "to": f"127.0.0.1:{closed_port}", "expect": "open", "why": "stand-in for the model being up"}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "plan.json"
            p.write_text(json.dumps(plan_doc))
            plan = load_plan(p)
            check(True, "a plan is read")
            ra, rg = run_role(plan, "app", 2), run_role(plan, "gateway", 2)
            check(ra["results"][0]["ok"] and ra["results"][1]["ok"], "a reachable address and a blocked one are judged as planned")
            check(not rg["ok"], "an address that should be open and is not is a failure (the stand-in for a model that is down)")
            ok, lines = combine(plan, [ra, rg])
            check(not ok and any("not shown to be up" in l for l in lines), "a blocked check whose target was not shown to be up is refused by combine")
    finally:
        stop.set()
        srv.close()
    print(f"{'ok' if not failures else 'FAILED'}: {len(failures)} failure(s)")
    return 1 if failures else 0


# ----------------------------------------------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wall_check.py", description="Does the network wall around the AI model stand? See the top of this file.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="run the checks of one role, from this machine")
    r.add_argument("--plan", required=True)
    r.add_argument("--role", required=True)
    r.add_argument("--timeout", type=float, default=3.0)
    r.add_argument("--out", help="write the report here (JSON)")
    c = sub.add_parser("combine", help="the verdict from the reports of every role")
    c.add_argument("--plan", required=True)
    c.add_argument("--max-age-hours", type=float, default=24.0)
    c.add_argument("reports", nargs="+")
    sub.add_parser("self-test", help="check the script on this machine, using sockets of its own")
    h = sub.add_parser("hash", help="print the plan's SHA-256")
    h.add_argument("--plan", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "self-test":
            return self_test()
        plan = load_plan(a.plan)
        if a.cmd == "hash":
            print(plan["_sha256"])
            return 0
        if a.cmd == "run":
            if not 0.2 <= a.timeout <= 60:
                raise PlanError("--timeout is from 0.2 to 60 seconds")
            rep = run_role(plan, a.role, a.timeout)
            for x in rep["results"]:
                print(f"{'PASS' if x['ok'] else 'FAIL'}  {x['id']:<28} {x['expect']:<8} {x['to']:<24} {x['verdict']}")
            if a.out:
                Path(a.out).write_text(json.dumps(rep, indent=1), encoding="utf-8")
                print(f"report written to {a.out} (role {rep['role']}, host {rep['host']}, plan {rep['plan_sha256'][:12]})")
            print("every check from this role is as planned; run `combine` with the reports of every role for the verdict" if rep["ok"] else "SOMETHING IS NOT AS PLANNED")
            return 0 if rep["ok"] else 1
        reports = []
        for f in a.reports:
            try:
                reports.append(json.loads(Path(f).read_text(encoding="utf-8")))
            except (OSError, ValueError) as e:
                raise PlanError(f"cannot read the report {f}: {e}") from None
        ok, lines = combine(plan, reports, a.max_age_hours)
        print("\n".join(lines))
        return 0 if ok else 1
    except PlanError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
