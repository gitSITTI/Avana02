"""The shared live-connector kit (connect.py) against a REAL local HTTP(S) server: retries, redirects, size cap, TLS, secrets."""
from __future__ import annotations

import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
import trustme

from reqin.connect import (ConnectError, ReadOnlyHttp, UrllibTransport, auth_from_options, make_http, next_link, opt_dict, opt_int,
                           opt_list)


class _H(BaseHTTPRequestHandler):
    seen: list = []
    flaky = {"n": 0}
    rate = {"n": 0}

    def log_message(self, *a):  # silence
        pass

    def do_GET(self):  # noqa: N802
        _H.seen.append(("GET", self.path, self.headers.get("Authorization")))
        if self.path == "/ok":
            return self._send(200, b'{"ok": true}')
        if self.path == "/flaky":
            _H.flaky["n"] += 1
            return self._send(200 if _H.flaky["n"] > 2 else 503, b"{}")
        if self.path == "/rate":
            _H.rate["n"] += 1
            return self._send(200 if _H.rate["n"] > 1 else 429, b"{}", {"Retry-After": "2"})
        if self.path == "/redirect-same":
            return self._send(302, b"", {"Location": "/ok"})
        if self.path == "/redirect-other":
            return self._send(302, b"", {"Location": f"http://127.0.0.2:{self.server.server_port}/ok"})
        if self.path == "/big":
            return self._send(200, b"x" * (3 * 1024 * 1024))
        if self.path == "/page":
            return self._send(200, b"[]", {"Link": '<https://h/a?p=1>; rel="prev", <https://h/a?p=3>; rel="next"'})
        return self._send(404, b"nope")

    def _send(self, code, body, headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # any other verb: record it so the test can prove the client never sends one
    def do_POST(self):  # noqa: N802
        _H.seen.append(("POST", self.path, None)); self._send(405, b"")
    do_PUT = do_DELETE = do_PATCH = do_POST


class _QuietServer(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):  # a client that rejects our certificate aborts the handshake: expected, not news
        pass


def _serve(ctx: ssl.SSLContext | None = None):
    srv = _QuietServer(("127.0.0.1", 0), _H)
    if ctx:
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def server():
    _H.seen.clear(); _H.flaky["n"] = 0; _H.rate["n"] = 0
    s = _serve()
    yield f"http://127.0.0.1:{s.server_port}"
    s.shutdown()


def test_get_works_and_only_get_is_ever_sent(server):
    http = make_http({"token": "tok-12345"})
    assert http.get_json(server + "/ok") == {"ok": True}
    assert _H.seen == [("GET", "/ok", "Bearer tok-12345")]
    assert not hasattr(http, "post") and not hasattr(http, "put") and not hasattr(http, "delete")


def test_transient_errors_are_retried_with_backoff_and_retry_after_is_honoured(server):
    sleeps = []
    t = UrllibTransport(retries=3, backoff=1.0, sleep=sleeps.append)
    assert ReadOnlyHttp(t).get(server + "/flaky").status == 200 and sleeps == [1.0, 2.0]
    sleeps.clear()
    assert ReadOnlyHttp(t).get(server + "/rate").status == 200 and sleeps == [2.0]


def test_gives_up_after_the_retry_budget_and_reports_the_status(server):
    t = UrllibTransport(retries=1, sleep=lambda _s: None)
    _H.flaky["n"] = -100                                         # always 503
    with pytest.raises(ConnectError) as e:
        ReadOnlyHttp(t).get(server + "/flaky")
    assert e.value.status == 503


def test_same_host_redirect_is_followed_other_host_is_refused(server):
    http = ReadOnlyHttp(UrllibTransport(sleep=lambda _s: None), headers={"Authorization": "Bearer tok-12345"})
    assert http.get(server + "/redirect-same").status == 200
    with pytest.raises(ConnectError, match="refusing redirect"):
        http.get(server + "/redirect-other")
    assert [p for _, p, _a in _H.seen] == ["/redirect-same", "/ok", "/redirect-other"]       # the other host was never contacted


def test_response_size_is_capped(server):
    with pytest.raises(ConnectError, match="larger than"):
        ReadOnlyHttp(UrllibTransport(max_bytes=1024 * 1024)).get(server + "/big")


def test_not_found_and_unreachable_have_helpful_messages(server):
    with pytest.raises(ConnectError, match="HTTP 404 .*not found") as e:
        ReadOnlyHttp(UrllibTransport()).get(server + "/missing")
    assert e.value.status == 404
    with pytest.raises(ConnectError, match="could not reach the server"):
        ReadOnlyHttp(UrllibTransport(retries=0)).get("http://127.0.0.1:9/never")


def test_the_request_budget_stops_runaway_paging(server):
    http = ReadOnlyHttp(UrllibTransport(), max_requests=2)
    http.get(server + "/ok"); http.get(server + "/ok")
    with pytest.raises(ConnectError, match="max_requests"):
        http.get(server + "/ok")


def test_tls_is_always_verified_and_a_ca_bundle_makes_a_private_ca_work(tmp_path):
    ca = trustme.CA()
    cert = ca.issue_cert("localhost", "127.0.0.1")
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    cert.configure_cert(ctx)
    srv = _serve(ctx)
    try:
        url = f"https://127.0.0.1:{srv.server_port}/ok"
        with pytest.raises(ConnectError, match="could not reach the server.*(CERTIFICATE|certificate|SSL)"):
            ReadOnlyHttp(UrllibTransport(retries=0)).get(url)                    # unknown CA: refused, and there is no switch to turn that off
        bundle = tmp_path / "ca.pem"
        ca.cert_pem.write_to_path(str(bundle))
        assert ReadOnlyHttp(UrllibTransport(ca_bundle=str(bundle))).get_json(url) == {"ok": True}
        assert make_http({"ca_bundle": str(bundle)}).get_json(url) == {"ok": True}
    finally:
        srv.shutdown()


def test_secrets_are_scrubbed_from_errors_and_urls():
    http = ReadOnlyHttp(UrllibTransport(), headers={}, secrets={"hunter2-secret"})
    assert http.scrub("boom hunter2-secret boom") == "boom *** boom"
    assert http.safe_url("https://user:pw@h:8443/p?access_token=abc&x=1") == "https://h:8443/p?access_token=***&x=1"


def test_auth_comes_from_env_names_not_values():
    h, s = auth_from_options({"token_env": "T"}, {"T": "bearer-value"})
    assert h == {"Authorization": "Bearer bearer-value"} and "bearer-value" in s
    h, s = auth_from_options({"basic_user_env": "U", "basic_password_env": "P"}, {"U": "alice", "P": "pw-secret"})
    assert h["Authorization"].startswith("Basic ") and "pw-secret" in s
    with pytest.raises(ConnectError, match="NOPE is not set"):
        auth_from_options({"token_env": "NOPE"}, {})
    with pytest.raises(ConnectError, match="invalid characters"):
        auth_from_options({"cookie_env": "C"}, {"C": "a\r\nX-Evil: 1"})


def test_auth_hook_is_the_seam_for_logins_the_kit_cannot_do(tmp_path, monkeypatch):
    (tmp_path / "my_login.py").write_text("def headers(options, env):\n    return {'X-Session': 'sess-' + env['WHO']}\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    h, s = auth_from_options({"auth_hook": "my_login:headers"}, {"WHO": "me"})
    assert h == {"X-Session": "sess-me"} and "sess-me" in s


def test_link_header_parsing_and_option_helpers():
    assert next_link('<https://h/a?p=1>; rel="prev", <https://h/a?p=3>; rel="next"') == "https://h/a?p=3"
    assert next_link('<https://h/a?p=1>; rel="prev"') is None and next_link(None) is None
    assert next_link('<https://h/a?p=3>; rel=next') == "https://h/a?p=3"
    assert opt_int({"n": "5"}, "n", 1) == 5 and opt_int({}, "n", 7) == 7
    with pytest.raises(ConnectError, match="whole number"):
        opt_int({"n": "x"}, "n", 1)
    assert opt_list({"l": "a, b"}, "l", []) == ["a", "b"] and opt_dict({"d": '{"a": 1}'}, "d") == {"a": 1}
    with pytest.raises(ConnectError, match="JSON object"):
        opt_dict({"d": "nope"}, "d")
