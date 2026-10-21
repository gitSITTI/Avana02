"""The HTTP face of the store: JSON over HTTP, a bearer token for every call but /v1/health, and nothing else.

Routes (details and examples in SERVER.md):
  GET  /v1/health                                  no token; says the server is up
  GET  /v1/me                                      who the token is
  GET  /v1/projects/<p>/people                     the people in the project (no tokens)
  GET  /v1/projects/<p>/docs?prefix=&after=&limit= the newest revision of each document
  GET  /v1/projects/<p>/docs/<id>                  one document
  GET  /v1/projects/<p>/history/<id>               every revision of one document
  PUT  /v1/projects/<p>/docs/<id>                  {"body": {...} | null, "if_rev": N}   (+ Idempotency-Key header)
  GET  /v1/projects/<p>/events?after=N&limit=      the record, from entry N+1 (poll this to see what others did)
  GET  /v1/projects/<p>/verify?expect_head=        recompute the record and say where it first breaks

Given an app directory it also serves the page itself, read only:
  GET  /                                           sends you to /app/
  GET  /app/<file>                                 a file from the app directory (no token: it holds no project data), /app/ being its start page

The server speaks plain HTTP and binds to loopback unless told otherwise: tokens are bearer secrets, so anything beyond one machine goes
behind a reverse proxy that adds TLS. It sends no CORS headers, so a web page from another origin cannot call it; the page it serves is from
the same origin, so the connected page needs none.
"""
from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlsplit

from .store import ServerError, Store

MAX_REQUEST_BYTES = 1024 * 1024
MAX_STATIC_BYTES = 20 * 1024 * 1024
VERSION = "0.1"
# what the app directory may hand out; anything else is a 404, whatever is in the directory
STATIC_TYPES = {
    ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".json": "application/json", ".css": "text/css; charset=utf-8",
    ".woff2": "font/woff2", ".woff": "font/woff", ".ttf": "font/ttf", ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon", ".txt": "text/plain; charset=utf-8",
}
APP_START = "Main.dc.html"
_P = r"[a-z0-9][a-z0-9_-]{0,63}"
ROUTES = [
    ("GET", re.compile(r"/v1/health"), "health"),
    ("GET", re.compile(r"/v1/me"), "me"),
    ("GET", re.compile(rf"/v1/projects/({_P})/people"), "people"),
    ("GET", re.compile(rf"/v1/projects/({_P})/docs"), "list"),
    ("GET", re.compile(rf"/v1/projects/({_P})/docs/(.+)"), "get"),
    ("PUT", re.compile(rf"/v1/projects/({_P})/docs/(.+)"), "put"),
    ("GET", re.compile(rf"/v1/projects/({_P})/history/(.+)"), "history"),
    ("GET", re.compile(rf"/v1/projects/({_P})/events"), "events"),
    ("GET", re.compile(rf"/v1/projects/({_P})/verify"), "verify"),
]


def is_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 64

    def __init__(self, addr: tuple[str, int], store: Store, log: Callable[[str], None] | None, app_dir: Path | None = None):
        super().__init__(addr, Handler)
        self.store, self.log, self.app_dir = store, log, app_dir


class Handler(BaseHTTPRequestHandler):
    server_version = "reqin-reference"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    timeout = 15

    # nothing the caller sent in a header or body is ever written to the log: method, path, status
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: D401
        pass

    def _log(self, status: int) -> None:
        if self.server.log:
            self.server.log(f"{self.command} {urlsplit(self.path).path} {status}")

    def _unread(self) -> bool:
        """The caller sent a body this request never read. On a kept-alive connection it would be taken for the next request line, so the connection is closed."""
        n = self.headers.get("Content-Length")
        return bool(n and n.isdigit() and int(n) > 0 and not self._read)

    def _send(self, status: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        if self._unread():
            self.send_header("Connection", "close")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        self._log(status)

    def _error(self, e: ServerError) -> None:
        h = {"WWW-Authenticate": 'Bearer realm="reqin"'} if e.status == 401 else {}
        self._send(e.status, {"error": {"code": e.code, "message": e.message, **e.extra}}, h)

    def _token(self) -> str | None:
        a = self.headers.get("Authorization", "")
        m = re.fullmatch(r"Bearer ([A-Za-z0-9_-]{20,200})", a)
        return m.group(1) if m else None

    def _body(self) -> dict[str, Any]:
        n = self.headers.get("Content-Length")
        if n is None or not n.isdigit():
            raise ServerError(411, "length_required", "Send a Content-Length.")
        if int(n) > MAX_REQUEST_BYTES:
            raise ServerError(413, "too_large", f"A request is at most {MAX_REQUEST_BYTES // 1024} KB.")
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            raise ServerError(415, "json_only", "Send Content-Type: application/json.")
        raw = self.rfile.read(int(n))
        self._read = True

        def no_constants(c: str) -> Any:
            raise ValueError(c)

        try:
            obj = json.loads(raw.decode("utf-8"), parse_constant=no_constants)
        except (ValueError, UnicodeDecodeError):
            raise ServerError(400, "bad_json", "The request is not valid JSON.") from None
        if not isinstance(obj, dict) or set(obj) - {"body", "if_rev"} or "body" not in obj:
            raise ServerError(400, "bad_request", 'Send {"body": {...} or null, "if_rev": N}, and nothing else.')
        return obj

    def _static(self, rel: str) -> None:
        """A file from the app directory: GET and HEAD only, an allowed extension only, nothing that starts with a dot, nothing that resolves outside the directory."""
        root = self.server.app_dir
        if self.command not in ("GET", "HEAD"):
            raise ServerError(405, "method_not_allowed", f"{self.command} is not allowed here.")
        rel = unquote(rel) or APP_START
        parts = rel.split("/")
        if "\x00" in rel or "\\" in rel or any(p == "" or p.startswith(".") for p in parts) or Path(parts[-1]).suffix.lower() not in STATIC_TYPES:
            raise ServerError(404, "no_route", "There is no such file.")
        target = (root / rel).resolve()
        if root not in target.parents or not target.is_file() or target.stat().st_size > MAX_STATIC_BYTES:
            raise ServerError(404, "no_route", "There is no such file.")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", STATIC_TYPES[target.suffix.lower()])
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        self._log(200)

    def _route(self) -> None:
        path = urlsplit(self.path)
        if self.server.app_dir is not None:
            if path.path == "/":
                self.send_response(302)
                self.send_header("Location", "/app/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return self._log(302)
            if path.path == "/app" or path.path.startswith("/app/"):
                if path.path == "/app":
                    self.send_response(302)
                    self.send_header("Location", "/app/")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return self._log(302)
                return self._static(path.path[len("/app/"):])
        q = {k: v[-1] for k, v in parse_qs(path.query, keep_blank_values=True).items()}
        matched_path = False
        for method, rx, name in ROUTES:
            m = rx.fullmatch(path.path)
            if not m:
                continue
            matched_path = True
            if method != self.command:
                continue
            st = self.server.store
            if name == "health":
                return self._send(200, {"ok": True, "version": VERSION})
            who = st.who(self._token())
            args = [unquote(g) for g in m.groups()]
            if name == "me":
                return self._send(200, {"project": who.project, "key": who.key, "name": who.name, "role": who.role, "lens": who.lens})
            if args[0] != who.project:
                raise ServerError(403, "other_project", "That token is for a different project.")
            if name == "people":
                return self._send(200, {"people": st.people(who)})
            if name == "list":
                return self._send(200, st.list(who, q.get("prefix", ""), q.get("after", ""), _int(q.get("limit"), 200), q.get("withdrawn") == "1"))
            if name == "get":
                return self._send(200, st.get(who, args[1]))
            if name == "history":
                return self._send(200, {"revisions": st.history(who, args[1])})
            if name == "events":
                return self._send(200, st.events(who, _int(q.get("after"), 0), _int(q.get("limit"), 500)))
            if name == "verify":
                return self._send(200, st.verify(who.project, q.get("expect_head", "")))
            if name == "put":
                req = self._body()
                status, resp = st.put(who, args[1], req["body"], req.get("if_rev", None), self.headers.get("Idempotency-Key", ""))
                return self._send(status, resp, {"Idempotent-Replay": "true"} if resp.get("replay") else None)
        if matched_path:
            raise ServerError(405, "method_not_allowed", f"{self.command} is not allowed here.")
        raise ServerError(404, "no_route", "There is no such path.")

    def _handle(self) -> None:
        self._read = False
        try:
            self._route()
        except ServerError as e:
            self._error(e)
        except Exception:   # never tell a caller how the server broke
            self._send(500, {"error": {"code": "server_error", "message": "The server could not do that."}})

    do_GET = do_PUT = do_POST = do_DELETE = do_PATCH = do_OPTIONS = do_HEAD = _handle


def _int(v: str | None, default: int) -> int:
    try:
        return int(v) if v is not None else default
    except ValueError:
        raise ServerError(400, "bad_number", "That should be a whole number.") from None


def make_server(store: Store, host: str = "127.0.0.1", port: int = 8780, allow_remote: bool = False, log: Callable[[str], None] | None = None, app_dir: str | Path | None = None) -> Server:
    if not allow_remote and not is_loopback(host):
        raise ServerError(400, "remote_refused", f"{host} is not a loopback address. Tokens travel in the clear over plain HTTP: put a TLS reverse proxy in front and pass --allow-remote, or bind to 127.0.0.1.")
    root = None
    if app_dir is not None:
        root = Path(app_dir).resolve()
        if not (root / APP_START).is_file():
            raise ServerError(400, "bad_app_dir", f"{app_dir} has no {APP_START}, so there is no page to serve.")
    return Server((host, port), store, log, root)


def serve_in_thread(srv: Server) -> threading.Thread:
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return t
