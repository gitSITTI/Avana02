"""The AI gateway against a real reference server and a fake model, over real HTTP on loopback.

What is under test is the wall the page cannot be: whatever a browser says, a prompt reaches the model only if the shared project's switch is on, its data sheet is
reviewed and consistent, the group's markings are within what the sheet approves, the model the gateway forwards to is the model the sheet describes, and the prompt
holds no wording of requirements nobody declared. Each refusal is a test, and so is the one path that opens."""
from __future__ import annotations

import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from reqin.aigate import Sheet
from reqin.gateway import AuditLog, Markings, decide, fingerprints, load_config, make_gateway, verify_log
from reqin.gateway.config import ConfigError
from reqin.gateway.core import MARKINGS_FORMAT, prompt_text, route_mismatch, sheet_from_doc
from reqin.server import Store
from reqin.server.http import make_server

PEOPLE = [
    {"key": "sam", "name": "Sam Okafor", "role": "reviewer", "lens": "SE"},
    {"key": "morgan", "name": "Morgan Hale", "role": "lead", "lens": "SE"},
    {"key": "lee", "name": "Lee Park", "role": "observer", "lens": ""},
]
REQS = {
    "REQ-A": ("No marking", "The flight control subsystem shall transmit a health status message to the ground station within five seconds of a state change."),
    "REQ-B": ("No marking", "The ground station shall acknowledge each health status message within two seconds of receipt by the flight control subsystem."),
    "REQ-C": ("CUI", "The data recorder shall store all telemetry frames for at least thirty days in encrypted form on removable media."),
    "REQ-D": ("ITAR", "The navigation function shall compute position using only approved algorithm revisions and report its confidence to the pilot."),
    "REQ-E": ("SECRET", "The mission computer shall reject any command that is not authenticated by the ground station before it is executed."),
    "REQ-F": ("Company confidential", "The thermal control subsystem shall keep the avionics bay below sixty degrees under all operating conditions."),
    "REQ-G": (None, "The power subsystem shall switch to battery within ten milliseconds of a bus failure event on the main distribution bus."),
    "REQ-H": ("No marking", "Shall be reliable."),
}
SHEET = {"model": "Local model v1", "where": "ours", "leaves": False, "log": "local", "days": 90, "approved": "none", "unstated": "withhold", "reviewed_by": "A. Moreno, security office", "reviewed_at": "2 Oct", "entered_by": "Morgan Hale"}
ROUTE = {"model": "Local model v1", "where": "ours", "leaves": False, "log": "local", "days": 90}


class FakeModel(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), FakeModelHandler)
        self.seen: list[dict] = []
        self.status = 200
        self.reply = {"id": "cmpl-1", "choices": [{"index": 0, "message": {"role": "assistant", "content": "Merged wording."}}]}


class FakeModelHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(n))
        self.server.seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "body": body, "headers": dict(self.headers)})
        out = json.dumps(self.server.reply).encode()
        self.send_response(self.server.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)


def _serve(srv) -> None:
    """Serve in a thread that notices a shutdown request quickly (the default waits half a second to look, which made every test a second and a half slower)."""
    threading.Thread(target=lambda: srv.serve_forever(poll_interval=0.02), daemon=True).start()


@pytest.fixture()
def world(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("MODEL_KEY", "model-secret-key")
    st = Store(tmp_path / "s.db")
    tokens = st.init_project("demo", PEOPLE)
    who = {k: st.who(t) for k, t in tokens.items()}
    ref = make_server(st, port=0)
    _serve(ref)
    model = FakeModel()
    _serve(model)
    (tmp_path / "markings.json").write_text(json.dumps(Markings.build([(k, m, t) for k, (m, t) in REQS.items()])))
    cfg_path = tmp_path / "gateway.json"
    cfg = {"listen": {"host": "127.0.0.1", "port": 0}, "server": f"http://127.0.0.1:{ref.server_address[1]}", "markings": "markings.json", "log": "gateway-log.jsonl",
           "upstream": {"url": f"http://127.0.0.1:{model.server_address[1]}/v1/chat/completions", "key_env": "MODEL_KEY", **ROUTE}}
    cfg_path.write_text(json.dumps(cfg))
    c = load_config(cfg_path)
    audit = AuditLog(c.log)
    gw = make_gateway(c, Markings.from_file(json.loads(c.markings.read_text())), audit)
    _serve(gw)
    port = gw.server_address[1]

    def lead_sets(on=True, sheet=None, if_rev=None):
        cur = st.get(who["morgan"], "proj/ai") if if_rev is None and _has(st, who["morgan"], "proj/ai") else None
        rev = cur["rev"] if cur else 0
        st.put(who["morgan"], "proj/ai", {"on": on, "sheet": dict(SHEET if sheet is None else sheet)}, rev)

    def call(token=None, ids="REQ-A", body=None, method="POST", path="/v1/chat/completions", headers=None, raw=None):
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = "Bearer " + token
        if ids is not None:
            h["X-Reqin-Requirements"] = ids
        h.update(headers or {})
        data = raw if raw is not None else json.dumps(body if body is not None else {"model": "anything", "messages": [{"role": "user", "content": "Merge the wordings of the requirements named above."}]}).encode()
        c2 = http.client.HTTPConnection("127.0.0.1", port, timeout=20)
        c2.request(method, path, body=data if method not in ("GET",) else None, headers=h)
        r = c2.getresponse()
        out = r.read()
        c2.close()
        try:
            j = json.loads(out)
        except ValueError:
            j = None
        return r.status, j, r

    yield type("W", (), dict(st=st, who=who, tokens=tokens, ref=ref, model=model, gw=gw, call=call, lead_sets=lead_sets, tmp=tmp_path, audit=audit, cfg_path=cfg_path, cfg=cfg))
    gw.shutdown(); gw.server_close(); model.shutdown(); model.server_close(); ref.shutdown(); ref.server_close(); st.close()


def _has(st, who, doc):
    try:
        st.get(who, doc)
        return True
    except Exception:
        return False


def code(res) -> str:
    return (res[1] or {}).get("error", {}).get("code", "")


# ---------------------------------------------------------------- the one path that opens
def test_when_everything_is_in_order_the_model_gets_the_prompt_and_the_answer_comes_back(world):
    w = world
    w.lead_sets()
    s, j, r = w.call(w.tokens["sam"], "REQ-A,REQ-B")
    assert s == 200 and j["choices"][0]["message"]["content"] == "Merged wording."
    assert r.getheader("X-Reqin-Gate") == "open; level=none; requirements=2"
    assert len(w.model.seen) == 1
    got = w.model.seen[0]
    assert got["body"]["model"] == "Local model v1", "the model is the gateway's, whatever the caller asked for"
    assert got["auth"] == "Bearer model-secret-key" and w.tokens["sam"] not in json.dumps(got["headers"]), "the model sees the gateway's key, never the person's token"
    assert "X-Reqin-Requirements" not in got["headers"]


def test_a_lead_may_use_it_too_and_the_group_is_the_ids_named(world):
    w = world
    w.lead_sets()
    assert w.call(w.tokens["morgan"], "REQ-H")[0] == 200


# ---------------------------------------------------------------- who is asking
def test_no_token_or_a_wrong_token_is_refused_before_anything_else(world):
    w = world
    w.lead_sets()
    assert code(w.call(None)) == "no_token"
    s, j, _ = w.call("x" * 43)
    assert s == 401 and code((s, j)) == "bad_token"
    assert w.model.seen == []


def test_observers_read_they_do_not_use_the_ai(world):
    w = world
    w.lead_sets()
    s, j, _ = w.call(w.tokens["lee"])
    assert s == 403 and code((s, j)) == "observer" and w.model.seen == []


# ---------------------------------------------------------------- which requirements
@pytest.mark.parametrize("ids,want", [(None, "no_requirements"), ("", "no_requirements"), (" , ", "no_requirements"), ("REQ-A,REQ-NOPE", "unknown_requirement"), ("REQ-A,../x", "bad_requirements"),
                                      ("REQ-A\x7f", "bad_requirements")])
def test_the_prompt_must_say_which_requirements_it_holds_and_the_gateway_must_know_them(world, ids, want):
    w = world
    w.lead_sets()
    try:
        s, j, _ = w.call(w.tokens["sam"], ids)
    except Exception:
        pytest.skip("the client refused the header itself")
    assert s == 400 and code((s, j)) == want and w.model.seen == []


def test_too_many_requirements_for_one_prompt(world):
    w = world
    w.lead_sets()
    w.gw.cfg = type(w.gw.cfg)(**{**w.gw.cfg.__dict__, "max_requirements": 2})
    assert code(w.call(w.tokens["sam"], "REQ-A,REQ-B,REQ-H")) == "too_many"
    assert w.call(w.tokens["sam"], "REQ-A,REQ-B")[0] == 200


# ---------------------------------------------------------------- the switch and the sheet, as the shared project has them right now
def test_a_project_with_no_sheet_on_the_server_is_closed(world):
    w = world
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 403 and code((s, j)) == "no_sheet" and w.model.seen == []


def test_the_switch_off_closes_it_at_once_and_on_opens_it_again(world):
    w = world
    w.lead_sets(on=True)
    assert w.call(w.tokens["sam"])[0] == 200
    w.lead_sets(on=False)
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 403 and code((s, j)) == "off", "the very next request: nothing about the switch is kept from an earlier one"
    w.lead_sets(on=True)
    assert w.call(w.tokens["sam"])[0] == 200
    assert len(w.model.seen) == 2


@pytest.mark.parametrize("change,want", [({"reviewed_by": ""}, "unreviewed"), ({"reviewed_at": " "}, "unreviewed"), ({"model": ""}, "sheet"), ({"where": "mars"}, "sheet"),
                                         ({"approved": "cui", "leaves": True, "where": "vendor", "log": "none"}, "sheet")])
def test_a_sheet_that_is_not_reviewed_or_contradicts_itself_opens_nothing(world, change, want):
    w = world
    w.lead_sets(sheet={**SHEET, **change})
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 403 and code((s, j)) == want and w.model.seen == []


def test_a_sheet_the_gateway_cannot_read_opens_nothing(world):
    w = world
    for bad in ({"on": True, "sheet": {**SHEET, "surprise": 1}}, {"on": "yes", "sheet": SHEET}, {"on": True}, {"on": True, "sheet": "x"}, {"on": True, "sheet": SHEET, "extra": 1}):
        cur = _has(w.st, w.who["morgan"], "proj/ai")
        rev = w.st.get(w.who["morgan"], "proj/ai")["rev"] if cur else 0
        w.st.put(w.who["morgan"], "proj/ai", bad, rev)
        s, j, _ = w.call(w.tokens["sam"])
        assert s == 403 and code((s, j)) == "bad_sheet", bad
    assert w.model.seen == []


def test_a_withdrawn_sheet_is_no_sheet(world):
    w = world
    w.lead_sets()
    w.st.put(w.who["morgan"], "proj/ai", None, 1)
    assert code(w.call(w.tokens["sam"])) == "no_sheet"


# ---------------------------------------------------------------- the markings
@pytest.mark.parametrize("ids,approved,want", [
    ("REQ-A,REQ-B,REQ-H", "none", None),
    ("REQ-C", "none", "marking"),
    ("REQ-A,REQ-C", "none", "marking"),
    ("REQ-C", "cui", None),
    ("REQ-D", "cui", "marking"),
    ("REQ-E", "exp", "classified"),
    ("REQ-F", "exp", "unknown"),
    ("REQ-G", "none", "unstated"),
    ("REQ-A,REQ-G", "none", "unstated"),
])
def test_a_group_is_as_restricted_as_its_most_restricted_member(world, ids, approved, want):
    w = world
    sheet = {**SHEET, "approved": approved}
    w.lead_sets(sheet=sheet)
    s, j, _ = w.call(w.tokens["sam"], ids, body={"messages": [{"role": "user", "content": "Please merge these."}]})
    if want is None:
        assert s == 200
    else:
        assert s == 403 and code((s, j)) == want and w.model.seen == []


def test_an_unstated_marking_may_be_read_as_no_marking_when_the_sheet_says_so(world):
    w = world
    w.lead_sets(sheet={**SHEET, "unstated": "none"})
    assert w.call(w.tokens["sam"], "REQ-G")[0] == 200


# ---------------------------------------------------------------- the model the sheet describes is the model that is called
@pytest.mark.parametrize("field,value", [("model", "Other model v2"), ("where", "tenant"), ("leaves", True), ("log", "none"), ("days", 30)])
def test_the_sheets_approval_is_for_the_route_it_describes(world, field, value):
    w = world
    sheet = {**SHEET, field: value}
    if field == "where":
        sheet.update(leaves=False)
    w.lead_sets(sheet=sheet)
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 403 and code((s, j)) == "sheet_mismatch" and w.model.seen == []
    assert field in " ".join(j["error"]["detail"])


def test_a_sheet_that_says_the_text_stays_inside_cannot_approve_a_route_that_sends_it_out(world):
    w = world
    w.gw.cfg = type(w.gw.cfg)(**{**w.gw.cfg.__dict__, "route": {**ROUTE, "where": "vendor", "leaves": True}})
    w.lead_sets()
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 403 and code((s, j)) == "sheet_mismatch"


def test_days_only_matter_when_something_is_kept():
    s = Sheet(**{**SHEET, "log": "none", "days": 0})
    assert route_mismatch(s, {**ROUTE, "log": "none", "days": 7}) == []
    assert route_mismatch(Sheet(**{**SHEET, "log": "local", "days": 90}), {**ROUTE, "log": "local", "days": 30})


# ---------------------------------------------------------------- the wording of requirements that were not declared
def test_the_wording_of_a_requirement_nobody_declared_stops_the_prompt(world):
    w = world
    w.lead_sets(sheet={**SHEET, "approved": "none"})
    smuggle = {"messages": [{"role": "user", "content": "Merge A. Also consider: " + REQS["REQ-C"][1]}]}
    s, j, _ = w.call(w.tokens["sam"], "REQ-A", body=smuggle)
    assert s == 403 and code((s, j)) == "undeclared_text" and "REQ-C" in j["error"]["message"] and w.model.seen == []
    assert REQS["REQ-C"][1] not in json.dumps(j), "the answer never repeats the text"


@pytest.mark.parametrize("where", ["a system message", "a tool description", "a key name", "a nested list of parts", "a legacy prompt field", "different case and punctuation"])
def test_it_is_found_wherever_in_the_request_it_hides(world, where):
    w = world
    w.lead_sets()
    text = REQS["REQ-D"][1]
    body = {
        "a system message": {"messages": [{"role": "system", "content": text}, {"role": "user", "content": "go"}]},
        "a tool description": {"messages": [{"role": "user", "content": "go"}], "tools": [{"type": "function", "function": {"name": "f", "description": text}}]},
        "a key name": {"messages": [{"role": "user", "content": "go"}], "metadata": {text: 1}},
        "a nested list of parts": {"messages": [{"role": "user", "content": [{"type": "text", "text": "go"}, {"type": "text", "text": text}]}]},
        "a legacy prompt field": {"prompt": text},
        "different case and punctuation": {"messages": [{"role": "user", "content": text.upper().replace(" ", "  ").replace("shall", "SHALL,")}]},
    }[where]
    s, j, _ = w.call(w.tokens["sam"], "REQ-A", body=body)
    assert s == 403 and code((s, j)) == "undeclared_text", where


def test_a_requirement_of_four_or_five_words_is_recognised_whole():
    mk = Markings.from_file(Markings.build([("S-4", "No marking", "Pumps shall stop quickly."), ("S-5", "No marking", "The pump shall stop quickly."), ("S-9", "No marking", "The pump shall start within five seconds of the command.")]))
    assert mk.undeclared("Please consider: pumps shall stop quickly.", set()) == {"S-4": 1}
    assert mk.undeclared("Please consider: the pump shall stop quickly.", set()) == {"S-5": 1}
    assert mk.undeclared("Please consider: the pump shall stop.", set()) == {}


def test_look_alike_letters_do_not_hide_wording(world):
    """Full-width letters, ligatures and the like read as the same letters to a person and to a model."""
    w = world
    w.lead_sets()
    text = REQS["REQ-D"][1]
    wide = "".join(chr(ord(c) + 0xFEE0) if "!" <= c <= "~" else c for c in text)
    assert wide != text
    s, j, _ = w.call(w.tokens["sam"], "REQ-A", body={"prompt": wide})
    assert s == 403 and code((s, j)) == "undeclared_text"


@pytest.mark.parametrize("glue", ["_", "|", "/", ",", "-", "."])
def test_other_characters_between_the_words_do_not_hide_wording(world, glue):
    w = world
    w.lead_sets()
    s, j, _ = w.call(w.tokens["sam"], "REQ-A", body={"prompt": REQS["REQ-D"][1].replace(" ", glue)})
    assert s == 403 and code((s, j)) == "undeclared_text", glue


def test_a_declared_requirement_may_be_quoted_and_boilerplate_shared_with_a_declared_one_is_not_a_leak(world):
    w = world
    w.lead_sets()
    body = {"messages": [{"role": "user", "content": "Merge: " + REQS["REQ-A"][1] + " and " + REQS["REQ-B"][1]}]}
    assert w.call(w.tokens["sam"], "REQ-A,REQ-B", body=body)[0] == 200
    shared = {"messages": [{"role": "user", "content": "the ground station shall acknowledge"}]}      # four words held by REQ-A and REQ-B
    assert w.call(w.tokens["sam"], "REQ-A", body=shared)[0] == 200


def test_one_phrase_of_six_words_is_a_coincidence_not_a_leak(world):
    w = world
    w.lead_sets()
    one = {"messages": [{"role": "user", "content": "report its confidence to the pilot"}]}      # six words of REQ-D, once
    assert w.call(w.tokens["sam"], "REQ-A", body=one)[0] == 200
    two = {"messages": [{"role": "user", "content": "approved algorithm revisions and report its confidence to the pilot"}]}
    assert code(w.call(w.tokens["sam"], "REQ-A", body=two)) == "undeclared_text"


def test_a_requirement_too_short_to_fingerprint_is_declared_by_its_caller_only(world):
    w = world
    w.lead_sets()
    assert w.model.seen == [] and fingerprints(REQS["REQ-H"][1]) == []
    assert w.call(w.tokens["sam"], "REQ-A", body={"messages": [{"role": "user", "content": "Shall be reliable."}]})[0] == 200


# ---------------------------------------------------------------- what the caller can and cannot ask for
def test_streaming_is_not_passed_on(world):
    w = world
    w.lead_sets()
    s, j, _ = w.call(w.tokens["sam"], body={"stream": True, "messages": [{"role": "user", "content": "go"}]})
    assert s == 400 and code((s, j)) == "no_streaming" and w.model.seen == []


def test_the_model_chosen_by_the_caller_is_replaced_and_other_settings_pass_on(world):
    w = world
    w.lead_sets()
    w.call(w.tokens["sam"], body={"model": "gpt-something-else", "temperature": 0.1, "messages": [{"role": "user", "content": "go"}]})
    assert w.model.seen[0]["body"]["model"] == "Local model v1" and w.model.seen[0]["body"]["temperature"] == 0.1

def test_the_persons_token_is_never_the_credential_the_model_sees(world):
    """With no model key configured the model gets no credential at all, not the person's token."""
    w = world
    w.gw.cfg = type(w.gw.cfg)(**{**w.gw.cfg.__dict__, "key_env": ""})
    w.lead_sets()
    assert w.call(w.tokens["sam"])[0] == 200
    seen = w.model.seen[-1]
    assert seen["auth"] is None and w.tokens["sam"] not in json.dumps(seen["headers"])


def test_a_reply_larger_than_the_limit_is_not_passed_on(world, monkeypatch):
    from reqin.gateway import http as gw_http
    w = world
    w.lead_sets()
    monkeypatch.setattr(gw_http, "MAX_REPLY", 3000)      # above what the reference server answers with, below the model reply made here
    w.model.reply = {"id": "x", "choices": [{"message": {"role": "assistant", "content": "x" * 5000}}]}
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 502 and code((s, j)) == "upstream_too_large"
    rows = [json.loads(x) for x in Path(w.gw.cfg.log).read_text().splitlines()]
    assert rows[-1]["code"] == "upstream_too_large" and rows[-1]["ok"] is True


def test_if_the_server_goes_away_after_the_person_is_known_that_is_not_read_as_no_sheet(world, monkeypatch):
    from reqin.gateway import http as gw_http
    w = world
    w.lead_sets()
    real = gw_http._call

    def flaky(method, url, headers, body, timeout):
        if url.endswith("/docs/proj/ai"):
            raise gw_http.Upstream("unreachable", "gone")
        return real(method, url, headers, body, timeout)
    monkeypatch.setattr(gw_http, "_call", flaky)
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 502 and code((s, j)) == "server_unreachable" and w.model.seen == []



@pytest.mark.parametrize("kw,want", [(dict(path="/v1/models", method="GET"), 404), (dict(path="/v1/chat/completions", method="GET"), 405), (dict(path="/v1/other"), 404), (dict(method="PUT"), 404 | 405)])
def test_nothing_else_is_served(world, kw, want):
    w = world
    w.lead_sets()
    s, *_ = w.call(w.tokens["sam"], **kw)
    assert s in (404, 405) and w.model.seen == []


def test_the_body_must_be_json_and_not_too_large(world):
    w = world
    w.lead_sets()
    assert w.call(w.tokens["sam"], raw=b"not json")[0] == 400
    assert w.call(w.tokens["sam"], raw=b"[1,2]")[0] == 400
    assert w.call(w.tokens["sam"], headers={"Content-Type": "text/plain"})[0] == 415
    assert w.call(w.tokens["sam"], raw=b'{"messages": "' + b"x" * 300000 + b'"}')[0] == 413
    deep = b"[" * 100 + b"]" * 100
    assert w.call(w.tokens["sam"], raw=b'{"a": ' + deep + b"}")[0] == 400
    assert w.model.seen == []


def test_the_health_check_needs_no_token(world):
    w = world
    s, j, _ = w.call(None, None, method="GET", path="/v1/health")
    assert s == 200 and j == {"ok": True}


# ---------------------------------------------------------------- when something else is down: closed
def test_if_the_reference_server_cannot_be_reached_nothing_is_sent(world):
    w = world
    w.lead_sets()
    w.ref.shutdown(); w.ref.server_close()
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 502 and code((s, j)) == "server_unreachable" and w.model.seen == []


def test_if_the_model_is_down_the_person_is_told_and_the_record_says_the_gate_was_open(world):
    w = world
    w.lead_sets()
    w.model.shutdown(); w.model.server_close()
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 502 and code((s, j)) == "upstream_unreachable"
    rows = [json.loads(x) for x in Path(w.gw.cfg.log).read_text().splitlines()]
    assert rows[-1]["ok"] is True and rows[-1]["code"] == "upstream_unreachable"


def test_the_models_own_errors_are_passed_on_as_they_are(world):
    w = world
    w.lead_sets()
    w.model.status = 429
    w.model.reply = {"error": {"message": "slow down"}}
    s, j, _ = w.call(w.tokens["sam"])
    assert s == 429 and j == {"error": {"message": "slow down"}}


def test_a_redirect_from_the_model_is_not_followed(world):
    """A redirect would carry the model's key (and the prompt's headers) to an address nobody configured. 302 is the one urllib follows after a POST, so that is the one tried."""
    w = world
    caught: list[dict] = []

    class Catcher(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            caught.append({"auth": self.headers.get("Authorization")})
            self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")
        do_POST = do_GET

    cat = ThreadingHTTPServer(("127.0.0.1", 0), Catcher)
    _serve(cat)

    class Redirect(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            self.send_response(302); self.send_header("Location", f"http://127.0.0.1:{cat.server_address[1]}/steal"); self.send_header("Content-Length", "0"); self.end_headers()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
    _serve(srv)
    w.gw.cfg = type(w.gw.cfg)(**{**w.gw.cfg.__dict__, "upstream_url": f"http://127.0.0.1:{srv.server_address[1]}/x"})
    w.lead_sets()
    s, j, _ = w.call(w.tokens["sam"])
    srv.shutdown(); srv.server_close(); cat.shutdown(); cat.server_close()
    assert caught == [], "the redirect was followed: the model's key went to an address nobody configured"
    assert s in (302, 502)


# ---------------------------------------------------------------- the gateway's own record
def test_the_record_says_who_asked_what_and_what_was_decided_and_never_the_text(world):
    w = world
    w.lead_sets()
    w.call(w.tokens["sam"], "REQ-A,REQ-B", body={"messages": [{"role": "user", "content": "SECRETPROMPTWORDS " + REQS["REQ-A"][1]}]})
    w.lead_sets(on=False)
    w.call(w.tokens["sam"], "REQ-A")
    w.call(w.tokens["lee"], "REQ-A")
    log = Path(w.gw.cfg.log)
    text = log.read_text()
    rows = [json.loads(x) for x in text.splitlines()]
    assert [(r["person"], r["code"], r["ok"]) for r in rows] == [("sam", "open", True), ("sam", "off", False), ("lee", "observer", False)]
    assert rows[0]["requirements"] == ["REQ-A", "REQ-B"] and rows[0]["upstream"] == 200 and rows[0]["project"] == "demo"
    assert "SECRETPROMPTWORDS" not in text and "health status" not in text and "model-secret-key" not in text and w.tokens["sam"] not in text
    assert verify_log(log)["ok"]


def test_an_edited_or_removed_line_of_the_record_is_noticed(world):
    w = world
    w.lead_sets()
    for _ in range(3):
        w.call(w.tokens["sam"])
    log = Path(w.gw.cfg.log)
    good = log.read_text()
    head = verify_log(log)["head"]
    assert verify_log(log, head)["ok"]
    lines = good.splitlines()
    log.write_text(good.replace('"person":"sam"', '"person":"lee"', 1))
    assert verify_log(log) == {"ok": False, "at": 1, "why": "its contents no longer match its fingerprint"}
    log.write_text("\n".join([lines[0], lines[2]]) + "\n")
    assert verify_log(log)["ok"] is False and verify_log(log)["at"] == 2
    log.write_text("\n".join(lines[:2]) + "\n")
    assert verify_log(log)["ok"] is True and verify_log(log, head)["ok"] is False, "cut short: valid on its own, but not the end that was written down"
    log.write_text(good)


def test_a_line_edited_and_given_a_fresh_fingerprint_still_breaks_the_chain(world):
    """Someone who edits a line and recomputes its own fingerprint is caught by the line after it, which still names the old one."""
    from reqin.gateway.audit import _canon, _hash
    w = world
    w.lead_sets()
    for _ in range(3):
        w.call(w.tokens["sam"])
    log = Path(w.gw.cfg.log)
    lines = log.read_text().splitlines()
    row = json.loads(lines[1])
    row["person"] = "lee"
    row["hash"] = _hash(row)
    lines[1] = _canon(row)
    log.write_text("\n".join(lines) + "\n")
    res = verify_log(log)
    assert res["ok"] is False and res["at"] == 3 and "does not follow" in res["why"]


def test_the_last_line_given_a_wrong_number_and_a_fresh_fingerprint_is_noticed(world):
    from reqin.gateway.audit import _canon, _hash
    w = world
    w.lead_sets()
    for _ in range(2):
        w.call(w.tokens["sam"])
    log = Path(w.gw.cfg.log)
    lines = log.read_text().splitlines()
    row = json.loads(lines[-1])
    row["seq"] = 9
    row["hash"] = _hash(row)
    lines[-1] = _canon(row)
    log.write_text("\n".join(lines) + "\n")
    res = verify_log(log)
    assert res["ok"] is False and res["at"] == 2 and "out of order" in res["why"]


def test_a_record_that_does_not_check_out_is_not_appended_to(world, tmp_path):
    bad = tmp_path / "x.jsonl"
    bad.write_text('{"seq": 1}\n')
    with pytest.raises(ValueError):
        AuditLog(bad)


# ---------------------------------------------------------------- the pieces on their own
def test_the_markings_file_holds_fingerprints_not_wording():
    data = Markings.build([(k, m, t) for k, (m, t) in REQS.items()])
    blob = json.dumps(data)
    assert data["format"] == MARKINGS_FORMAT and "health status" not in blob and "transmit" not in blob
    assert Markings.from_file(data).marks["REQ-C"] == "CUI"
    for bad in ({}, {"format": "x"}, {"format": "reqin-markings/2", "requirements": {}}, {"format": MARKINGS_FORMAT, "requirements": {"R 1": {}}}, {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": 3}}},
                {"format": MARKINGS_FORMAT, "requirements": {"R1": {"marking": "x", "fp": ["zz"]}}}, {"format": MARKINGS_FORMAT, "requirements": {"R1": {"text": "the wording"}}}):
        with pytest.raises(ValueError):
            Markings.from_file(bad)
    with pytest.raises(ValueError):
        Markings.build([("R1", None, "a"), ("R1", None, "b")])


def test_decide_runs_the_same_ensure_as_the_page():
    mk = Markings.from_file(Markings.build([(k, m, t) for k, (m, t) in REQS.items()]))
    doc = {"on": True, "sheet": SHEET}
    d = lambda **kw: decide(**{**dict(role="reviewer", ids=["REQ-A"], markings=mk, ai_doc=doc, ai_present=True, route=ROUTE, prompt="go"), **kw})
    assert d().ok
    assert d(ids=["REQ-C"]).code == "marking" and d(ids=["REQ-C"]).level == "cui"
    assert d(ai_doc={"on": False, "sheet": SHEET}).code == "off"
    assert d(role="observer").status == 403 and d(ids=[]).status == 400


def test_sheet_from_doc_refuses_what_it_does_not_know():
    assert sheet_from_doc({"on": True, "sheet": SHEET})[1] is True
    assert sheet_from_doc({"on": 1, "sheet": SHEET}) is None and sheet_from_doc({"on": True, "sheet": {**SHEET, "x": 1}}) is None and sheet_from_doc(None) is None


def test_prompt_text_reads_every_string_including_keys():
    t = prompt_text({"messages": [{"role": "user", "content": ["a", {"text": "b"}]}], "k-ey": {"n": ["c"]}})
    assert all(x in t for x in "abc") and "k-ey" in t
    with pytest.raises(ValueError):
        prompt_text([[[[]]]] and json.loads("[" * 60 + "]" * 60))


# ---------------------------------------------------------------- the settings
def test_the_settings_are_checked(tmp_path, world):
    w = world
    good = dict(w.cfg)

    def write(d):
        p = tmp_path / "c.json"
        p.write_text(json.dumps(d))
        return p
    assert load_config(write(good)).route == ROUTE
    for name, change in {
        "unknown top-level key": {"surprise": 1},
        "the key itself in key_env": {"upstream": {**good["upstream"], "key_env": "not a name"}},
        "no model named": {"upstream": {**good["upstream"], "model": ""}},
        "a where it does not know": {"upstream": {**good["upstream"], "where": "cloud"}},
        "leaves not a boolean": {"upstream": {**good["upstream"], "leaves": "no"}},
        "a password in the address": {"server": "http://u:p@127.0.0.1:1"},
        "a file address": {"server": "file:///etc/passwd"},
        "a path on the server address": {"server": "http://127.0.0.1:1/v1"},
        "a limit out of range": {"limits": {"max_body_bytes": 5}},
        "an unknown limit": {"limits": {"max_cats": 5}},
    }.items():
        with pytest.raises(ConfigError):
            load_config(write({**good, **change}))
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_it_will_not_listen_beyond_this_machine_unless_told_to(world):
    w = world
    cfg = type(w.gw.cfg)(**{**w.gw.cfg.__dict__, "host": "0.0.0.0"})
    with pytest.raises(ValueError):
        make_gateway(cfg, w.gw.markings, w.audit)


# ---------------------------------------------------------------- the command line
def test_the_command_line_builds_a_markings_file_and_checks_the_settings(tmp_path, capsys, world, monkeypatch):
    from reqin.gateway.__main__ import main
    w = world
    lst = tmp_path / "list.json"
    lst.write_text(json.dumps([{"id": k, "marking": m, "text": t} for k, (m, t) in REQS.items()]))
    out = tmp_path / "m2.json"
    assert main(["markings", "--list", str(lst), "--out", str(out)]) == 0
    assert "1 with no marking recorded" in capsys.readouterr().out
    assert json.loads(out.read_text()) == json.loads((w.tmp / "markings.json").read_text())
    assert oct(out.stat().st_mode & 0o777) == "0o600"
    ds = tmp_path / "ds"
    ds.mkdir()
    (ds / "requirements.jsonl").write_text("\n".join(json.dumps({"uid": k, "text": t, "fields": {"marking": m} if m else {}, "extra": {}}) for k, (m, t) in REQS.items() if k != "REQ-C") + "\n" +
                                           json.dumps({"uid": "REQ-C", "text": REQS["REQ-C"][1], "fields": {}, "extra": {"Marking": "CUI"}}) + "\n")
    out2 = tmp_path / "m3.json"
    assert main(["markings", "--dataset", str(ds), "--field", "Marking", "--out", str(out2)]) == 0
    assert json.loads(out2.read_text())["requirements"]["REQ-C"]["marking"] == "CUI" and json.loads(out2.read_text())["requirements"]["REQ-G"]["marking"] is None
    capsys.readouterr()
    assert main(["check", "--config", str(w.cfg_path)]) == 0
    said = capsys.readouterr().out
    assert "8 requirements" in said and "MODEL_KEY (set)" in said and "Local model v1" in said
    monkeypatch.delenv("MODEL_KEY")
    main(["check", "--config", str(w.cfg_path)])
    assert "NOT SET" in capsys.readouterr().out
    assert main(["check", "--config", str(tmp_path / "nope.json")]) == 2
    w.lead_sets(); w.call(w.tokens["sam"])
    assert main(["verify-log", "--log", str(w.gw.cfg.log)]) == 0
    Path(w.gw.cfg.log).write_text(Path(w.gw.cfg.log).read_text().replace("demo", "dem0", 1))
    assert main(["verify-log", "--log", str(w.gw.cfg.log)]) == 1
