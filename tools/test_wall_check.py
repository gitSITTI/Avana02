"""deploy/ai-egress/wall_check.py: the script IT runs to find out whether the network wall around the AI model stands.

What these tests can and cannot show. They show that the script tells an open connection from a refused one, a timeout, an unreachable network and a name that does not
resolve; that it judges each against what the plan expects; that `combine` refuses a "blocked" result whose target was never shown to be up; and that the example plans and
settings in deploy/ai-egress/ are well formed. They cannot show that a firewall works: a firewall is tried on the real network, with this script. On one machine every
connection is allowed or refused by the same host, so "blocked" is tested here with closed ports and with errors raised on purpose.
"""
import errno
import http.server
import importlib.util
import json
import socket
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy" / "ai-egress"
SCRIPT = DEPLOY / "wall_check.py"
spec = importlib.util.spec_from_file_location("wall_check", SCRIPT)
wc = importlib.util.module_from_spec(spec)
sys.modules["wall_check"] = wc
spec.loader.exec_module(wc)


# ----------------------------------------------------------------------------------------------------------------- helpers

@pytest.fixture
def listener():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen(16)
    stop = threading.Event()

    def accept():
        s.settimeout(0.1)
        while not stop.is_set():
            try:
                c, _ = s.accept()
                c.close()
            except OSError:
                pass

    t = threading.Thread(target=accept, daemon=True)
    t.start()
    yield s.getsockname()[1]
    stop.set()
    t.join(2)
    s.close()


def closed_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class Health(http.server.BaseHTTPRequestHandler):
    status, body = 200, b'{"ok":true}'

    def do_GET(self):
        self.send_response(self.status)
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *a):
        pass


def serve_health(status=200, body=b'{"ok":true}'):
    h = type("H", (Health,), {"status": status, "body": body})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def plan_file(tmp_path, checks, name="plan.json"):
    p = tmp_path / name
    p.write_text(json.dumps({"format": wc.PLAN_FORMAT, "checks": checks}))
    return p


def chk(id_, role, to, expect, **kw):
    return {"id": id_, "from": role, "to": to, "expect": expect, "why": "because", **kw}


# ------------------------------------------------------------------------------------------------------------ the plan

BAD_PLANS = {
    "wrong format": {"format": "x", "checks": [chk("a", "app", "1.2.3.4:5", "open")]},
    "no checks": {"format": wc.PLAN_FORMAT, "checks": []},
    "unknown key": {"format": wc.PLAN_FORMAT, "checks": [dict(chk("a", "app", "1.2.3.4:5", "open"), speed="fast")]},
    "no why": {"format": wc.PLAN_FORMAT, "checks": [{"id": "a", "from": "app", "to": "1.2.3.4:5", "expect": "open"}]},
    "blank why": {"format": wc.PLAN_FORMAT, "checks": [dict(chk("a", "app", "1.2.3.4:5", "open"), why="  ")]},
    "expect neither": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "maybe")]},
    "no port": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4", "open")]},
    "port zero": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:0", "open")]},
    "port too big": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:65536", "open")]},
    "ipv6 without brackets": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "::1:80", "open")]},
    "duplicate id": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "open"), chk("a", "gw", "1.2.3.4:5", "open")]},
    "odd id": {"format": wc.PLAN_FORMAT, "checks": [chk("a b", "app", "1.2.3.4:5", "open")]},
    "role in capitals": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "App", "1.2.3.4:5", "open")]},
    "http on a blocked check": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "blocked", http={"path": "/"})]},
    "http path not a path": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "open", http={"path": "health"})]},
    "http POST": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "open", http={"path": "/", "method": "POST"})]},
    "allow_unresolved on an open check": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "x:5", "open", allow_unresolved=True)]},
    "proof names nothing": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "blocked", target_up_from="nope")]},
    "proof is itself blocked": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "blocked", target_up_from="b"), chk("b", "gw", "1.2.3.4:5", "blocked")]},
    "proof is another address": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "blocked", target_up_from="b"), chk("b", "gw", "1.2.3.4:6", "open")]},
    "proof from the same role": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "blocked", target_up_from="b"), chk("b", "app", "1.2.3.4:5", "open")]},
    "proof on an open check": {"format": wc.PLAN_FORMAT, "checks": [chk("a", "app", "1.2.3.4:5", "open", target_up_from="b"), chk("b", "gw", "1.2.3.4:5", "open")]},
}


@pytest.mark.parametrize("name", sorted(BAD_PLANS))
def test_a_plan_with_this_fault_is_refused(tmp_path, name):
    p = tmp_path / "p.json"
    p.write_text(json.dumps(BAD_PLANS[name]))
    with pytest.raises(wc.PlanError):
        wc.load_plan(p)


def test_a_plan_that_is_not_json_or_is_missing_is_refused(tmp_path):
    (tmp_path / "p.json").write_text("{not json")
    for f in ("p.json", "missing.json"):
        with pytest.raises(wc.PlanError):
            wc.load_plan(tmp_path / f)


def test_a_good_plan_is_read_and_carries_its_fingerprint(tmp_path):
    p = plan_file(tmp_path, [chk("up", "gw", "10.0.0.1:8000", "open"), chk("no", "app", "10.0.0.1:8000", "blocked", target_up_from="up"),
                             chk("v6", "app", "[::1]:80", "open"), chk("n", "app", "model.internal:80", "blocked", allow_unresolved=True)])
    plan = wc.load_plan(p)
    import hashlib
    assert plan["_sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert wc.split_target("[::1]:80") == ("::1", 80) and wc.split_target("a.b:443") == ("a.b", 443)


def test_the_plan_fingerprint_changes_with_one_character(tmp_path):
    a = wc.load_plan(plan_file(tmp_path, [chk("a", "app", "10.0.0.1:80", "open")], "a.json"))
    b = wc.load_plan(plan_file(tmp_path, [chk("a", "app", "10.0.0.1:81", "open")], "b.json"))
    assert a["_sha256"] != b["_sha256"]


# -------------------------------------------------------------------------------------------------------- one attempt

def test_a_listening_port_is_open(listener):
    r = wc.attempt(f"127.0.0.1:{listener}", 2)
    assert r["outcome"] == wc.OPEN and r["addresses"] == {"127.0.0.1": wc.OPEN}


def test_a_closed_port_is_refused():
    r = wc.attempt(f"127.0.0.1:{closed_port()}", 2)
    assert r["outcome"] == wc.REFUSED


def test_a_name_that_does_not_exist_is_unresolved_not_blocked():
    assert wc.attempt("no-such-name.invalid:80", 2)["outcome"] == wc.UNRESOLVED


def test_ipv6_loopback_when_the_machine_has_it(listener):
    try:
        s = socket.socket(socket.AF_INET6)
        s.bind(("::1", 0))
    except OSError:
        pytest.skip("this machine has no IPv6 loopback")
    p = s.getsockname()[1]
    s.close()
    assert wc.attempt(f"[::1]:{p}", 2)["outcome"] == wc.REFUSED


@pytest.mark.parametrize("exc,outcome", [
    (socket.timeout("timed out"), wc.TIMEOUT),
    (TimeoutError(), wc.TIMEOUT),
    (OSError(errno.ENETUNREACH, "Network is unreachable"), wc.UNREACHABLE),
    (OSError(errno.EHOSTUNREACH, "No route to host"), wc.UNREACHABLE),
    (OSError(errno.EACCES, "Permission denied"), wc.UNREACHABLE),
    (ConnectionRefusedError(errno.ECONNREFUSED, "refused"), wc.REFUSED),
    (ConnectionResetError(errno.ECONNRESET, "reset"), wc.REFUSED),
    (OSError(errno.EMFILE, "Too many open files"), wc.ERROR),
])
def test_each_way_a_connection_can_fail_is_named(monkeypatch, exc, outcome):
    class S:
        def __init__(self, *a): pass
        def settimeout(self, t): pass
        def connect(self, sa): raise exc
        def close(self): pass
    monkeypatch.setattr(wc.socket, "socket", S)
    assert wc.attempt("127.0.0.1:9", 1)["outcome"] == outcome


def test_a_name_with_two_addresses_is_open_if_either_answers(monkeypatch, listener):
    real = wc.socket.getaddrinfo
    monkeypatch.setattr(wc.socket, "getaddrinfo", lambda h, p, **k: real("127.0.0.1", listener, **k) + real("127.0.0.1", closed_port(), **k)[:0])
    r = wc.attempt(f"two.example:{listener}", 2)
    assert r["outcome"] == wc.OPEN


def test_a_name_whose_addresses_are_all_refused_is_blocked_and_says_for_each(monkeypatch):
    p = closed_port()
    real = wc.socket.getaddrinfo
    monkeypatch.setattr(wc.socket, "getaddrinfo", lambda h, port, **k: real("127.0.0.1", p, **k))
    r = wc.attempt(f"x.example:{p}", 2)
    assert r["outcome"] == wc.REFUSED and "127.0.0.1" in r["detail"]


# ----------------------------------------------------------------------------------------------------- the HTTP answer

def test_the_health_answer_of_the_right_thing_passes():
    srv = serve_health()
    try:
        r = wc.attempt(f"127.0.0.1:{srv.server_address[1]}", 2, {"path": "/v1/health", "status": 200, "contains": "ok"})
        assert r["outcome"] == wc.OPEN and r["http"]["ok"] is True and r["http"]["status"] == 200
    finally:
        srv.shutdown()


@pytest.mark.parametrize("status,body", [(200, b"hello"), (500, b'{"ok":true}'), (404, b"")])
def test_a_wrong_answer_on_an_open_port_is_not_the_gateway(status, body):
    srv = serve_health(status, body)
    try:
        r = wc.attempt(f"127.0.0.1:{srv.server_address[1]}", 2, {"path": "/v1/health", "status": 200, "contains": "ok"})
        assert r["outcome"] == wc.OPEN and r["http"]["ok"] is False
        j = wc.judge(chk("a", "app", "x:1", "open", http={"path": "/"}), r)
        assert j["ok"] is False and "not the right answer" in j["verdict"]
    finally:
        srv.shutdown()


def test_a_port_that_accepts_and_says_nothing_is_not_the_gateway(listener):
    r = wc.attempt(f"127.0.0.1:{listener}", 1, {"path": "/v1/health", "status": 200, "contains": "ok"})
    assert r["outcome"] == wc.OPEN and r["http"]["ok"] is False and "no HTTP answer" in r["http"]["detail"]


# ----------------------------------------------------------------------------------------------------------- judging

def res(outcome, **kw):
    return {"outcome": outcome, "detail": "d", "ms": 1, "addresses": {}, **kw}


@pytest.mark.parametrize("expect,outcome,ok", [
    ("open", wc.OPEN, True), ("open", wc.REFUSED, False), ("open", wc.TIMEOUT, False), ("open", wc.UNREACHABLE, False), ("open", wc.UNRESOLVED, False), ("open", wc.ERROR, False),
    ("blocked", wc.OPEN, False), ("blocked", wc.REFUSED, True), ("blocked", wc.TIMEOUT, True), ("blocked", wc.UNREACHABLE, True), ("blocked", "blocked", True),
    ("blocked", wc.UNRESOLVED, False), ("blocked", wc.ERROR, False),
])
def test_what_happened_is_judged_against_what_was_planned(expect, outcome, ok):
    assert wc.judge(chk("a", "app", "x:1", expect), res(outcome))["ok"] is ok


def test_an_unresolved_name_passes_only_when_the_plan_accepts_the_weaker_proof():
    c = chk("a", "app", "x:1", "blocked", allow_unresolved=True)
    j = wc.judge(c, res(wc.UNRESOLVED))
    assert j["ok"] is True and "weaker" in j["verdict"]
    assert wc.judge(chk("a", "app", "x:1", "blocked"), res(wc.UNRESOLVED))["ok"] is False


def test_a_reachable_thing_that_must_be_blocked_is_called_out_in_capitals():
    assert "IS REACHABLE" in wc.judge(chk("a", "app", "x:1", "blocked"), res(wc.OPEN))["verdict"]


def test_a_blocked_result_says_it_does_not_yet_show_the_target_is_up():
    j = wc.judge(chk("a", "app", "x:1", "blocked", target_up_from="b"), res(wc.TIMEOUT))
    assert j["ok"] is True and "not yet shown" in j["verdict"]


# --------------------------------------------------------------------------------------------------- run one role

def test_run_role_checks_only_that_roles_lines(tmp_path, listener):
    plan = wc.load_plan(plan_file(tmp_path, [chk("a", "app", f"127.0.0.1:{listener}", "open"), chk("b", "gw", f"127.0.0.1:{closed_port()}", "open")]))
    rep = wc.run_role(plan, "app", 2)
    assert [r["id"] for r in rep["results"]] == ["a"] and rep["ok"] is True
    assert rep["plan_sha256"] == plan["_sha256"] and rep["script_sha256"] == wc.script_hash() and rep["role"] == "app"
    assert datetime.fromisoformat(rep["at"]).tzinfo is not None


def test_a_role_the_plan_does_not_have_is_an_error_naming_the_roles(tmp_path):
    plan = wc.load_plan(plan_file(tmp_path, [chk("a", "app", "127.0.0.1:1", "open"), chk("b", "gateway", "127.0.0.1:1", "open")]))
    with pytest.raises(wc.PlanError, match="app, gateway"):
        wc.run_role(plan, "modle", 1)


# -------------------------------------------------------------------------------------------------------- combine

class World:
    """A plan with the gateway, an app host that must not reach the model, and the reports each would give."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.checks = [chk("gw-model", "gateway", "10.0.1.9:4000", "open"), chk("app-model", "app", "10.0.1.9:4000", "blocked", target_up_from="gw-model"),
                       chk("app-gw", "app", "10.0.0.5:8790", "open")]
        self.now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    def plan(self, checks=None, name="p.json"):
        return wc.load_plan(plan_file(self.tmp, checks or self.checks, name))

    def report(self, plan, role, outcomes, at=None, script="s1", plan_sha=None):
        results = []
        for c in plan["checks"]:
            if c["from"] != role:
                continue
            r = wc.judge(c, res(outcomes[c["id"]]))
            results.append({"id": c["id"], "to": c["to"], "expect": c["expect"], "why": c["why"], **r})
        return {"format": wc.REPORT_FORMAT, "role": role, "host": role + "-host", "at": (at or self.now).isoformat(), "plan_sha256": plan_sha or plan["_sha256"], "script_sha256": script,
                "timeout_s": 3, "results": results, "ok": all(x["ok"] for x in results)}

    def good(self, plan, **kw):
        return [self.report(plan, "gateway", {"gw-model": wc.OPEN}, **kw), self.report(plan, "app", {"app-model": wc.TIMEOUT, "app-gw": wc.OPEN}, **kw)]


def test_the_wall_stands_when_every_role_reports_as_planned(tmp_path):
    w = World(tmp_path); plan = w.plan()
    ok, lines = wc.combine(plan, w.good(plan), now=w.now)
    assert ok and lines[-1].startswith("PASS 3 of 3")


def test_a_model_that_is_switched_off_does_not_prove_a_wall(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = [w.report(plan, "gateway", {"gw-model": wc.REFUSED}), w.report(plan, "app", {"app-model": wc.REFUSED, "app-gw": wc.OPEN})]
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok
    assert any("app-model" in l and "not shown to be up" in l for l in lines) and any(l.startswith("FAIL gw-model") for l in lines)


def test_a_blocked_check_with_no_proof_in_the_plan_is_refused(tmp_path):
    w = World(tmp_path)
    plan = w.plan([chk("gw-model", "gateway", "10.0.1.9:4000", "open"), chk("app-model", "app", "10.0.1.9:4000", "blocked")], "q.json")
    reps = [w.report(plan, "gateway", {"gw-model": wc.OPEN}), w.report(plan, "app", {"app-model": wc.TIMEOUT})]
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("gives no check that shows" in l for l in lines)


def test_the_model_reachable_from_the_app_is_a_failure(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = [w.report(plan, "gateway", {"gw-model": wc.OPEN}), w.report(plan, "app", {"app-model": wc.OPEN, "app-gw": wc.OPEN})]
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("IS REACHABLE" in l for l in lines)


def test_a_missing_role_is_a_failure_naming_the_check(tmp_path):
    w = World(tmp_path); plan = w.plan()
    ok, lines = wc.combine(plan, w.good(plan)[:1], now=w.now)
    assert not ok and any("app-model: no report from role 'app'" in l for l in lines) and any("app-gw: no report" in l for l in lines)


def test_a_report_for_another_plan_is_not_counted(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = w.good(plan)
    reps[1]["plan_sha256"] = "0" * 64
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("different plan" in l for l in lines)


def test_reports_made_by_different_copies_of_the_script_are_refused(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = w.good(plan)
    reps[1]["script_sha256"] = "edited"
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("different copies" in l for l in lines)


def test_reports_from_different_days_are_refused(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = [w.report(plan, "gateway", {"gw-model": wc.OPEN}, at=w.now - timedelta(days=3)), w.report(plan, "app", {"app-model": wc.TIMEOUT, "app-gw": wc.OPEN})]
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("hours apart" in l for l in lines)


def test_reports_more_than_a_week_old_are_refused(tmp_path):
    w = World(tmp_path); plan = w.plan()
    old = w.now - timedelta(days=8)
    ok, lines = wc.combine(plan, w.good(plan, at=old), now=w.now)
    assert not ok and any("more than a week old" in l for l in lines)


def test_a_later_run_of_a_role_replaces_an_earlier_one(tmp_path):
    w = World(tmp_path); plan = w.plan()
    bad_earlier = w.report(plan, "app", {"app-model": wc.OPEN, "app-gw": wc.OPEN}, at=w.now - timedelta(hours=2))
    reps = w.good(plan) + [bad_earlier]
    ok, _ = wc.combine(plan, reps, now=w.now)
    assert ok, "the earlier failing run must not count against the later passing one"
    later_bad = w.report(plan, "app", {"app-model": wc.OPEN, "app-gw": wc.OPEN}, at=w.now + timedelta(hours=1))
    ok, _ = wc.combine(plan, w.good(plan) + [later_bad], now=w.now)
    assert not ok, "a later failing run replaces an earlier passing one"


def test_a_report_that_claims_ok_for_a_check_it_did_not_make_as_planned_is_refused(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = w.good(plan)
    reps[1]["results"][0]["to"] = "10.9.9.9:4000"            # the report says it tried some other address
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("does not match the plan's check" in l for l in lines)


def test_a_check_the_plan_does_not_have_is_noticed(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = w.good(plan)
    reps[1]["results"].append(dict(reps[1]["results"][0], id="sneaky"))
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("sneaky" in l for l in lines)


@pytest.mark.parametrize("bad", [None, [], {"format": "x"}, {"format": wc.REPORT_FORMAT, "results": 1, "role": "app"}, {"format": wc.REPORT_FORMAT, "results": [], "role": 3}])
def test_a_file_that_is_not_a_report_is_refused(tmp_path, bad):
    w = World(tmp_path); plan = w.plan()
    ok, lines = wc.combine(plan, w.good(plan) + [bad], now=w.now)
    assert not ok and any("not a wall report" in l for l in lines)


def test_a_report_with_no_usable_time_is_refused(tmp_path):
    w = World(tmp_path); plan = w.plan()
    reps = w.good(plan)
    reps[0]["at"] = "yesterday"
    ok, lines = wc.combine(plan, reps, now=w.now)
    assert not ok and any("no usable time" in l for l in lines)


# --------------------------------------------------------------------------------------------------- the command line

def cli(*args):
    r = subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def test_the_self_test_passes_on_this_machine():
    rc, out = cli("self-test")
    assert rc == 0 and "FAIL" not in out.replace("0 failure(s)", "") and out.count("PASS") >= 7


def test_run_writes_a_report_and_exits_zero_when_all_is_as_planned(tmp_path, listener):
    p = plan_file(tmp_path, [chk("a", "app", f"127.0.0.1:{listener}", "open"), chk("n", "app", f"127.0.0.1:{closed_port()}", "blocked")])
    rc, out = cli("run", "--plan", str(p), "--role", "app", "--out", str(tmp_path / "app.json"))
    rep = json.loads((tmp_path / "app.json").read_text())
    assert rc == 0 and rep["ok"] is True and rep["role"] == "app" and "PASS  a" in out and "PASS  n" in out


def test_run_exits_one_when_something_is_not_as_planned(tmp_path, listener):
    p = plan_file(tmp_path, [chk("a", "app", f"127.0.0.1:{listener}", "blocked")])
    rc, out = cli("run", "--plan", str(p), "--role", "app")
    assert rc == 1 and "IS REACHABLE" in out and "SOMETHING IS NOT AS PLANNED" in out


def test_run_exits_two_for_a_bad_plan_role_or_timeout(tmp_path):
    p = plan_file(tmp_path, [chk("a", "app", "127.0.0.1:9", "open")])
    assert cli("run", "--plan", str(p), "--role", "other")[0] == 2
    assert cli("run", "--plan", str(tmp_path / "none.json"), "--role", "app")[0] == 2
    assert cli("run", "--plan", str(p), "--role", "app", "--timeout", "0")[0] == 2


def test_combine_by_command_line_gives_pass_and_fail_by_exit_status(tmp_path):
    w = World(tmp_path); plan = w.plan()
    now = datetime.now(timezone.utc)
    w.now = now
    good = w.good(plan)
    bad = [good[0], w.report(plan, "app", {"app-model": wc.OPEN, "app-gw": wc.OPEN})]
    p = tmp_path / "p.json"
    for name, reps, want in (("good", good, 0), ("bad", bad, 1)):
        files = []
        for i, r in enumerate(reps):
            f = tmp_path / f"{name}{i}.json"
            f.write_text(json.dumps(r))
            files.append(str(f))
        rc, out = cli("combine", "--plan", str(p), *files)
        assert rc == want, out
    assert cli("combine", "--plan", str(p), str(tmp_path / "missing.json"))[0] == 2


def test_hash_prints_the_plan_fingerprint(tmp_path):
    p = plan_file(tmp_path, [chk("a", "app", "127.0.0.1:9", "open")])
    rc, out = cli("hash", "--plan", str(p))
    assert rc == 0 and out.strip() == wc.load_plan(p)["_sha256"]


# -------------------------------------------------------------------------------------------- the examples in deploy/

EXAMPLE_PLANS = ["wall.example.json", "wall.compose.example.json"]


@pytest.mark.parametrize("name", EXAMPLE_PLANS)
def test_the_example_plans_are_well_formed_and_every_blocked_check_has_its_proof(name):
    plan = wc.load_plan(DEPLOY / name)
    blocked = [c for c in plan["checks"] if c["expect"] == "blocked"]
    assert blocked and all(c.get("target_up_from") for c in blocked), "a blocked check without a proof of life would pass for a switched-off target"
    assert all(c["why"].strip() for c in plan["checks"])


@pytest.mark.parametrize("name", EXAMPLE_PLANS)
def test_every_role_of_an_example_plan_has_something_to_do_and_every_proof_is_from_a_role_that_is_allowed_through(name):
    plan = wc.load_plan(DEPLOY / name)
    by_id = {c["id"]: c for c in plan["checks"]}
    for c in plan["checks"]:
        if c.get("target_up_from"):
            assert by_id[c["target_up_from"]]["to"] == c["to"] and by_id[c["target_up_from"]]["from"] != c["from"]


def test_the_compose_plan_uses_the_addresses_the_compose_file_gives():
    compose = (DEPLOY / "compose.example.yaml").read_text()
    plan = wc.load_plan(DEPLOY / "wall.compose.example.json")
    for c in plan["checks"]:
        host = wc.split_target(c["to"])[0]
        if host.startswith("172.30."):
            assert f"ipv4_address: {host}" in compose, f"{host} is not an address in compose.example.yaml"
    assert "internal: true" in compose


def test_the_example_nftables_file_closes_input_and_output():
    nft = (DEPLOY / "nftables-model-host.example.nft").read_text()
    assert nft.count("policy drop;") == 3                       # input, forward, output
    out = nft[nft.index("chain output"):]
    assert "accept" in out and "oif \"lo\" accept" in out
    assert not any(l.strip().startswith(("ip daddr", "tcp dport", "udp dport")) for l in out.splitlines()), "the model host starts no connection to anything"


@pytest.mark.skipif(not Path("/usr/sbin/nft").exists(), reason="nft is not installed here")
def test_the_example_nftables_file_passes_nfts_own_syntax_check():
    r = subprocess.run(["/usr/sbin/nft", "-c", "-f", str(DEPLOY / "nftables-model-host.example.nft")], capture_output=True, text=True, timeout=30)
    if "Operation not permitted" in r.stderr:
        pytest.skip("this machine does not let nft check a file")
    assert r.returncode == 0, r.stderr


def test_the_example_gateway_settings_are_read_by_the_gateway(tmp_path):
    cfg = json.loads((DEPLOY / "gateway.compose.example.json").read_text())
    cfg["markings"], cfg["log"] = "markings.json", "audit.jsonl"
    (tmp_path / "gateway.json").write_text(json.dumps(cfg))
    (tmp_path / "list.json").write_text(json.dumps([{"id": "R-1", "marking": "CUI", "text": "The pump shall start within five seconds of the command."}]))
    run = lambda *a: subprocess.run([sys.executable, str(REPO / "reqin" / "serve_standalone.py"), "gateway", *a], capture_output=True, text=True, timeout=60)
    m = run("markings", "--list", str(tmp_path / "list.json"), "--out", str(tmp_path / "markings.json"))
    assert m.returncode == 0, m.stderr
    r = run("check", "--config", str(tmp_path / "gateway.json"))
    assert r.returncode == 0, r.stderr
    assert "'reqin-local'" in r.stdout and "http://server:8780" in r.stdout and "stays inside" in r.stdout


def test_the_example_litellm_settings_keep_no_prompt_text():
    text = (DEPLOY / "litellm.example.yaml").read_text()
    for needed in ("turn_off_message_logging: true", "store_prompts_in_spend_logs: false", "disable_spend_logs: true"):
        assert needed in text
    assert "model_name: reqin-local" in text


def test_the_gateway_settings_and_the_litellm_model_name_agree():
    cfg = json.loads((DEPLOY / "gateway.compose.example.json").read_text())
    assert f"model_name: {cfg['upstream']['model']}" in (DEPLOY / "litellm.example.yaml").read_text()
    compose = (DEPLOY / "compose.example.yaml").read_text()
    assert "litellm" in cfg["upstream"]["url"] and "server:8780" in cfg["server"] and "UPSTREAM_KEY" in compose
