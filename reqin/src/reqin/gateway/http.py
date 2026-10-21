"""The gateway's HTTP side: POST /v1/chat/completions in the shape the usual model servers (LiteLLM, vLLM, Ollama, an OpenAI-compatible endpoint) speak.

What a caller sends:   Authorization: Bearer <their reqin token>      X-Reqin-Requirements: REQ-1,REQ-2 (the requirements whose wording is in the prompt)      a JSON body
What it gets:          the model's own answer, unchanged, when the gate is open; otherwise {"error": {"code", "message"}} and nothing was sent to the model.
The model's API key, the model's name and the address of the model are the gateway's, never the caller's. Nothing the caller sends is logged.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import quote, urlsplit

from ..server.http import is_loopback
from .audit import AuditLog
from .config import Config, upstream_key
from .core import ID_RE, Markings, Verdict, decide, prompt_text

MAX_REPLY = 16 * 1024 * 1024


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """A redirect would carry a token or the model's key to an address nobody configured."""

    def redirect_request(self, *a: Any, **k: Any) -> None:
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


class Upstream(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def _call(method: str, url: str, headers: dict[str, str], body: bytes | None, timeout: float) -> tuple[int, bytes, str]:
    rq = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with _OPENER.open(rq, timeout=timeout) as r:
            data = r.read(MAX_REPLY + 1)
            return r.status, data, r.headers.get("Content-Type", "application/json")
    except urllib.error.HTTPError as e:
        data = e.read(MAX_REPLY + 1)
        return e.code, data, e.headers.get("Content-Type", "application/json") if e.headers else "application/json"
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Upstream("unreachable", str(getattr(e, "reason", e))[:120]) from None


class Gateway(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, cfg: Config, markings: Markings, audit: AuditLog, log: Callable[[str], None] | None = None):
        super().__init__((cfg.host, cfg.port), Handler)
        self.cfg, self.markings, self.audit, self.log = cfg, markings, audit, log


class Handler(BaseHTTPRequestHandler):
    server_version = "reqin-gateway"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 30

    def log_message(self, fmt: str, *args: Any) -> None:
        pass

    def handle_one_request(self) -> None:
        self._close = False                      # per request: a kept-alive connection must not inherit the last request's "close"
        super().handle_one_request()

    def _send(self, status: int, data: bytes, ctype: str = "application/json", extra: dict[str, str] | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        if getattr(self, "_close", False):
            self.send_header("Connection", "close")
            self.close_connection = True
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        if self.server.log:
            self.server.log(f"{self.command} {urlsplit(self.path).path} {status}")

    def _error(self, status: int, code: str, message: str, detail: list[str] | None = None, extra: dict[str, str] | None = None) -> None:
        err: dict[str, Any] = {"code": code, "message": message}
        if detail:
            err["detail"] = detail
        self._send(status, json.dumps({"error": err}).encode("utf-8"), extra=extra)

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        if path == "/v1/health":
            return self._send(200, b'{"ok":true}')
        self._close = True
        self._error(405 if path == "/v1/chat/completions" else 404, "method_not_allowed" if path == "/v1/chat/completions" else "no_route", "Only POST /v1/chat/completions is served here.")

    do_PUT = do_DELETE = do_PATCH = do_HEAD = do_GET

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/v1/chat/completions":
            self._close = True
            return self._error(404, "no_route", "Only POST /v1/chat/completions is served here.")
        try:
            self._chat()
        except Exception:      # nothing about the request is shown: a stack trace could hold part of a prompt
            self._close = True
            self._error(500, "gateway_error", "The gateway could not do that. Nothing was sent to the model.")

    def _chat(self) -> None:
        srv: Gateway = self.server  # type: ignore[assignment]
        cfg = srv.cfg
        n = self.headers.get("Content-Length")
        if not n or not n.isdigit():
            self._close = True
            return self._error(411, "length_required", "Send a Content-Length.")
        if int(n) > cfg.max_body:
            self._close = True
            return self._error(413, "too_large", f"A request is at most {cfg.max_body} bytes.")
        raw = self.rfile.read(int(n))
        if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":
            return self._error(415, "json_only", "Send application/json.")
        auth = self.headers.get("Authorization") or ""
        if not auth.startswith("Bearer ") or not auth[7:].strip():
            return self._error(401, "no_token", "Send your reqin token: Authorization: Bearer <token>.")
        token = auth[7:].strip()
        # who is asking: the reference server says, from the token
        try:
            st, data, _ = _call("GET", cfg.server + "/v1/me", {"Authorization": "Bearer " + token}, None, 10)
        except Upstream:
            return self._error(502, "server_unreachable", "The reference server could not be reached, so nothing was sent to the model.")
        if st == 401:
            return self._error(401, "bad_token", "The reference server does not know that token.")
        try:
            who = json.loads(data)
            project, person, role = who["project"], who["key"], who["role"]
            assert st == 200 and all(isinstance(x, str) for x in (project, person, role))
        except Exception:
            return self._error(502, "server_unreachable", "The reference server did not answer as expected, so nothing was sent to the model.")
        ids: list[str] = []
        for x in (self.headers.get("X-Reqin-Requirements") or "").split(","):
            x = x.strip()
            if x and x not in ids:
                ids.append(x)
        bad_id = [x for x in ids if not ID_RE.fullmatch(x)]

        def refuse(v: Verdict, prompt_bytes: int = 0) -> None:
            srv.audit.add(project=project, person=person, requirements=[x for x in ids if ID_RE.fullmatch(x)][:200], code=v.code, level=v.level, ok=False, upstream=None, prompt_bytes=prompt_bytes)
            self._error(v.status, v.code, v.message, v.detail)

        if bad_id:
            return refuse(Verdict(False, 400, "bad_requirements", "A requirement id is letters, digits and . _ : - only: " + bad_id[0][:40]))
        try:
            body = json.loads(raw)
            if not isinstance(body, dict):
                raise ValueError("not an object")
            prompt = prompt_text(body)
        except ValueError:
            return refuse(Verdict(False, 400, "bad_json", "The body is not a JSON object the gateway can read."))
        if body.get("stream"):
            return refuse(Verdict(False, 400, "no_streaming", "This gateway forwards whole answers only: leave stream off."), len(raw))
        # the AI switch and data sheet, as the shared project has them right now (never kept from an earlier request)
        try:
            st, data, _ = _call("GET", f"{cfg.server}/v1/projects/{quote(project, safe='')}/docs/proj/ai", {"Authorization": "Bearer " + token}, None, 10)
        except Upstream:
            return self._error(502, "server_unreachable", "The reference server could not be reached, so nothing was sent to the model.")
        doc: Any = None
        present = False
        if st == 200:
            try:
                doc = json.loads(data).get("body")
                present = doc is not None
            except Exception:
                return self._error(502, "server_unreachable", "The reference server did not answer as expected, so nothing was sent to the model.")
        elif st == 401:
            return self._error(401, "bad_token", "The reference server does not know that token.")
        elif st != 404:
            return self._error(502, "server_unreachable", "The reference server did not answer as expected, so nothing was sent to the model.")
        v = decide(role=role, ids=ids, markings=srv.markings, ai_doc=doc, ai_present=present, route=cfg.route, prompt=prompt, max_requirements=cfg.max_requirements, min_windows=cfg.min_windows)
        if not v.ok:
            return refuse(v, len(raw))
        # open: the model, its address and its key are the gateway's own
        body["model"] = cfg.route["model"]
        hdr = {"Content-Type": "application/json"}
        key = upstream_key(cfg)
        if key:
            hdr["Authorization"] = "Bearer " + key
        try:
            ust, udata, uctype = _call("POST", cfg.upstream_url, hdr, json.dumps(body).encode("utf-8"), cfg.timeout)
        except Upstream:
            srv.audit.add(project=project, person=person, requirements=ids, code="upstream_unreachable", level=v.level, ok=True, upstream=None, prompt_bytes=len(raw))
            return self._error(502, "upstream_unreachable", "The model could not be reached. The gate was open; nothing came back.")
        if len(udata) > MAX_REPLY:
            srv.audit.add(project=project, person=person, requirements=ids, code="upstream_too_large", level=v.level, ok=True, upstream=ust, prompt_bytes=len(raw))
            return self._error(502, "upstream_too_large", "The model's answer is larger than this gateway passes on.")
        srv.audit.add(project=project, person=person, requirements=ids, code="open", level=v.level, ok=True, upstream=ust, prompt_bytes=len(raw))
        self._send(ust, udata, uctype.split(";")[0].strip() or "application/json", {"X-Reqin-Gate": f"open; level={v.level or 'none'}; requirements={len(ids)}"})


def make_gateway(cfg: Config, markings: Markings, audit: AuditLog, log: Callable[[str], None] | None = None) -> Gateway:
    if not is_loopback(cfg.host) and not cfg.allow_remote:
        raise ValueError(f"{cfg.host} is not this machine. Bind it to a non-loopback address only behind a TLS proxy, and set allow_remote in the settings.")
    return Gateway(cfg, markings, audit, log)
