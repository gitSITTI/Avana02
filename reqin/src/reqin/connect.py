"""Shared kit for LIVE connectors (anything that talks to a server instead of reading a file).

These rules are enforced HERE, once, so no individual connector can forget them:

* GET only. There is no method argument and no write path. A connector cannot modify the source system
  through this module, whatever its author intended.
* TLS is always verified. You can add your organisation's CA bundle (`ca_bundle=` or REQIN_CA_BUNDLE);
  there is deliberately no switch to turn verification off.
* Secrets come from environment variables (`token_env=NAME`), never from a file in the repo. Every error
  message and audit line is scrubbed of the secret values that were used.
* Redirects to another host (or from https to http) are refused, so a token is never forwarded elsewhere.
* Every request is recorded in an audit list (method, URL with secrets removed, status, bytes) that the CLI
  can write out with --audit: this is what you hand to IT security to show what the connector touched.
* Bounded: response size, request count and page count are capped, so a wrong setting cannot run forever.
* Polite: a custom User-Agent, back-off on 429 and 5xx, and a server's "retry after" (header, or the JSON body some vendors use) is
  obeyed up to a cap; a server that asks for longer than the cap is not waited for.
* XML from a server or a file is parsed without DOCTYPE or entity declarations (`safe_xml`).
"""
from __future__ import annotations

import base64
import importlib
import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol

SENSITIVE_PARAMS = {"token", "access_token", "accesstoken", "key", "apikey", "api_key", "password", "pwd", "secret", "auth", "sig", "signature"}
_HEADER_NAME = re.compile(r"^[A-Za-z0-9!#$%&'*+.^_`|~-]+$")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
USER_AGENT = "reqin-connector/0.2 (read-only; GET only)"


class ConnectError(RuntimeError):
    """A live connector could not do its job. The message never contains a secret."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Response:
    status: int
    headers: Mapping[str, str]          # lower-case names
    body: bytes
    url: str = ""

    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


class Transport(Protocol):
    """Anything that can GET. The real one is UrllibTransport; tests use reqin.testing.FakeTransport."""

    def get(self, url: str, headers: dict[str, str]) -> Response: ...


# ---- option parsing (CLI options arrive as strings) ----------------------------------------------
def opt_int(o: Mapping[str, Any], key: str, default: int) -> int:
    v = o.get(key)
    if v in (None, ""):
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        raise ConnectError(f"option {key!r} must be a whole number, got {v!r}") from None


def opt_list(o: Mapping[str, Any], key: str, default: list[str]) -> list[str]:
    v = o.get(key)
    if v in (None, ""):
        return list(default)
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v]
    return [x.strip() for x in str(v).split(",") if x.strip()]


def opt_dict(o: Mapping[str, Any], key: str, default: dict | None = None) -> dict:
    v = o.get(key)
    if v in (None, ""):
        return dict(default or {})
    if isinstance(v, dict):
        return dict(v)
    try:
        d = json.loads(str(v))
    except json.JSONDecodeError as e:
        raise ConnectError(f"option {key!r} must be a JSON object, e.g. '{{\"id\": \"@id\"}}' ({e.msg})") from None
    if not isinstance(d, dict):
        raise ConnectError(f"option {key!r} must be a JSON object")
    return d


# ---- authentication --------------------------------------------------------------------------------
def _need_env(name: str, env: Mapping[str, str]) -> str:
    val = env.get(name, "")
    if not val:
        raise ConnectError(f"environment variable {name} is not set (it must hold the credential; the value is never printed)")
    return val


def load_auth_hook(spec: str) -> Callable[[dict, Mapping[str, str]], dict[str, str]]:
    """'package.module:function' -> callable(options, env) -> {header: value}. This is the seam for logins the kit
    cannot do generically (form login, OAuth, SSO cookie): your own code returns the headers to send."""
    mod, _, fn = spec.partition(":")
    if not mod or not fn:
        raise ConnectError("auth_hook must look like 'package.module:function'")
    return getattr(importlib.import_module(mod), fn)


def auth_from_options(options: Mapping[str, Any], env: Mapping[str, str] | None = None) -> tuple[dict[str, str], set[str]]:
    """Build request headers from options. Returns (headers, secret values to scrub from messages).

    token_env=NAME                       -> Authorization: Bearer <value of $NAME>   (token_scheme=Token sends "Authorization: Token <value>", which
                                            Teamwork Cloud's REST API and some others use instead of Bearer)
    basic_user_env=U basic_password_env=P-> Authorization: Basic base64(user:password)
    cookie_env=NAME                      -> Cookie: <value of $NAME>   (a session cookie from an authenticated session: pilots only)
    auth_hook=pkg.mod:func               -> headers returned by your function (see load_auth_hook)
    token=...                            -> accepted for quick tests only; it lands in shell history, so prefer token_env
    """
    env = os.environ if env is None else env
    headers: dict[str, str] = {}
    secrets: set[str] = set()
    scheme = str(options.get("token_scheme") or "Bearer")
    if not _SCHEME.match(scheme):
        raise ConnectError(f"option 'token_scheme' must be one word such as Bearer or Token, got {scheme!r}")
    if options.get("token_env"):
        t = _need_env(str(options["token_env"]), env)
        headers["Authorization"] = f"{scheme} {t}"
        secrets.add(t)
    elif options.get("token"):
        t = str(options["token"])
        headers["Authorization"] = f"{scheme} {t}"
        secrets.add(t)
    elif options.get("basic_user_env"):
        u = _need_env(str(options["basic_user_env"]), env)
        p = _need_env(str(options.get("basic_password_env", "")), env) if options.get("basic_password_env") else ""
        raw = base64.b64encode(f"{u}:{p}".encode()).decode()
        headers["Authorization"] = f"Basic {raw}"
        secrets.update({p, raw})
    if options.get("cookie_env"):
        c = _need_env(str(options["cookie_env"]), env)
        headers["Cookie"] = c
        secrets.add(c)
    if options.get("auth_hook"):
        extra = load_auth_hook(str(options["auth_hook"]))(dict(options), env)
        for k, v in (extra or {}).items():
            headers[str(k)] = str(v)
            secrets.add(str(v))
    for k, v in headers.items():
        if not _HEADER_NAME.match(k) or any(c in v for c in "\r\n"):
            raise ConnectError(f"refusing header {k!r}: invalid characters")
    return headers, {s for s in secrets if len(s) >= 4}


_RETRY_BODY = re.compile(r"retry[_-]?after[\"'>\s:=]+(\d+(?:\.\d+)?)", re.I)


def retry_after_seconds(header: str, body: bytes = b"") -> float | None:
    """How long the server asked us to wait, in seconds, or None. The HTTP header first (a number of seconds; the HTTP-date form is not
    read and counts as 'not said'), then a `RetryAfter` value in the first 4 KB of the body, which is where Digital.ai Agility puts it."""
    h = (header or "").strip()
    if re.fullmatch(r"\d+(?:\.\d+)?", h):
        return float(h)
    m = _RETRY_BODY.search(body[:4096].decode("utf-8", errors="replace")) if body else None
    return float(m.group(1)) if m else None


_DTD = re.compile(rb"<!(?:doctype|entity)", re.I)


def has_dtd(raw: bytes) -> bool:
    """True when the bytes contain a DOCTYPE or ENTITY declaration ANYWHERE. The whole input is searched: a declaration can sit behind a comment of any
    length, so looking only at the first part of the file lets it through. The price is that a file that merely MENTIONS one inside a comment or a CDATA
    section is refused too, which is the safe way round."""
    return _DTD.search(raw) is not None


def safe_xml(data: bytes | str, what: str = "the XML") -> ET.Element:
    """Parse XML from a server or a file. A DOCTYPE or an ENTITY declaration is refused: no requirement export needs one, and they are how
    entity-expansion and external-entity attacks are written."""
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if has_dtd(raw):
        raise ConnectError(f"{what} has a DOCTYPE or ENTITY declaration; refusing to parse it (no export of requirements needs one)")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as e:
        raise ConnectError(f"{what} is not well-formed XML ({e})") from None


# ---- the real transport -----------------------------------------------------------------------------
class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        old, new = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(newurl)
        if (old.scheme, old.hostname, old.port) != (new.scheme, new.hostname, new.port):
            raise ConnectError(f"refusing redirect from {old.scheme}://{old.hostname} to {new.scheme}://{new.hostname}: "
                               "credentials are never forwarded to another host. If this is expected, use the final URL directly.", status=code)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class UrllibTransport:
    """Plain standard-library HTTP GET with retries on 429/5xx, size cap and strict TLS."""

    RETRY = {429, 502, 503, 504}

    def __init__(self, timeout: float = 60, ca_bundle: str | None = None, retries: int = 3, backoff: float = 1.0,
                 max_bytes: int = 512 * 1024 * 1024, sleep: Callable[[float], None] = time.sleep, max_wait: float = 120.0):
        ca = ca_bundle or os.environ.get("REQIN_CA_BUNDLE") or None
        ctx = ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()
        self._opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx), _SameHostRedirect())
        self.timeout, self.retries, self.backoff, self.max_bytes, self._sleep, self.max_wait = timeout, retries, backoff, max_bytes, sleep, max_wait

    def get(self, url: str, headers: dict[str, str]) -> Response:
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers, method="GET")
                with self._opener.open(req, timeout=self.timeout) as r:
                    return Response(r.status, self._hdrs(r.headers), self._read(r), url)
            except urllib.error.HTTPError as e:
                body = e.read(65536) if e.fp else b""
                if e.code in self.RETRY and attempt < self.retries:
                    asked = retry_after_seconds(e.headers.get("Retry-After", "") if e.headers else "", body)
                    wait = self.backoff * 2 ** attempt if asked is None else asked
                    if wait <= self.max_wait:
                        self._sleep(wait)
                        continue
                    # the server wants longer than we are willing to wait: say so instead of hanging
                    return Response(e.code, {**self._hdrs(e.headers), "x-reqin-retry-after-refused": str(wait)}, body, url)
                return Response(e.code, self._hdrs(e.headers), body, url)
            except ConnectError:
                raise
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                last = e
                if attempt < self.retries:
                    self._sleep(self.backoff * 2 ** attempt)
        raise ConnectError(f"could not reach the server: {type(last).__name__}: {getattr(last, 'reason', last)}")

    @staticmethod
    def _hdrs(h) -> dict[str, str]:  # noqa: ANN001
        out: dict[str, list[str]] = {}
        for k in (h.keys() if h else []):
            out.setdefault(k.lower(), []).extend(h.get_all(k) or [])
        return {k: ", ".join(v) for k, v in out.items()}

    def _read(self, r) -> bytes:  # noqa: ANN001
        chunks, total = [], 0
        while True:
            b = r.read(1 << 20)
            if not b:
                return b"".join(chunks)
            total += len(b)
            if total > self.max_bytes:
                raise ConnectError(f"response larger than {self.max_bytes} bytes: refusing (page the request or raise max_bytes)")
            chunks.append(b)


# ---- the read-only client connectors actually use ---------------------------------------------------
@dataclass
class AuditEntry:
    method: str
    url: str
    status: int
    bytes: int


@dataclass
class ReadOnlyHttp:
    transport: Transport
    headers: dict[str, str] = field(default_factory=dict)
    secrets: set[str] = field(default_factory=set)
    max_requests: int = 1_000_000
    audit: list[AuditEntry] = field(default_factory=list)

    # -- scrubbing
    def scrub(self, text: str) -> str:
        for s in sorted(self.secrets, key=len, reverse=True):
            text = text.replace(s, "***")
        return text

    @staticmethod
    def safe_url(url: str) -> str:
        p = urllib.parse.urlsplit(url)
        host = p.hostname or ""
        if p.port:
            host += f":{p.port}"
        q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
        q = [(k, "***" if k.lower() in SENSITIVE_PARAMS else v) for k, v in q]
        return urllib.parse.urlunsplit((p.scheme, host, p.path, urllib.parse.urlencode(q, safe="[]:,*"), ""))

    # -- the only verb
    def get(self, url: str, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None,
            ok: tuple[int, ...] = (200,), allow: tuple[int, ...] = ()) -> Response:
        if len(self.audit) >= self.max_requests:
            raise ConnectError(f"stopped after {self.max_requests} requests (max_requests): the paging or the filter is probably wrong")
        if params:
            sep = "&" if "?" in url else "?"
            url = url + sep + urllib.parse.urlencode(params, quote_via=urllib.parse.quote, safe="[]:,*")
        if not url.startswith(("http://", "https://")):
            raise ConnectError(f"not an http(s) URL: {self.safe_url(url)}")
        resp = self.transport.get(url, {**self.headers, **(headers or {})})
        if not resp.url:
            resp = Response(resp.status, resp.headers, resp.body, url)
        self.audit.append(AuditEntry("GET", self.safe_url(url), resp.status, len(resp.body)))
        if resp.status in ok or resp.status in allow:
            return resp
        hint = {401: " (credentials missing or rejected)", 403: " (the account is not allowed to read this: check the read-only service account's permissions)",
                404: " (not found: check the URL, project or id)",
                429: " (rate limited: the server asked the client to slow down; retries are used up, so lower the page size or run later)"}.get(resp.status, "")
        if resp.status == 400:
            said = self.scrub(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", resp.text()[:600]))).strip()[:200]
            hint = " (the server rejected the request: often a name that does not exist, such as an attribute on this type" + (f"; it said: {said!r}" if said else "") + ")"
        if resp.headers.get("x-reqin-retry-after-refused"):
            hint = f" (rate limited: the server asked for a wait of {resp.headers['x-reqin-retry-after-refused']} s, longer than max_wait)"
        raise ConnectError(self.scrub(f"GET {self.safe_url(url)} -> HTTP {resp.status}{hint}"), status=resp.status)

    def parse_json(self, resp: Response) -> Any:
        try:
            return json.loads(resp.body) if resp.body else None
        except ValueError:
            snippet = self.scrub(resp.text()[:100].replace("\n", " "))
            raise ConnectError(f"{self.safe_url(resp.url)} did not return JSON (content-type {resp.headers.get('content-type', '?')!r}; "
                               f"starts with {snippet!r}). Often a login page: check the credentials.") from None

    def get_json(self, url: str, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None, **kw: Any) -> Any:
        return self.parse_json(self.get(url, params, {"Accept": "application/json", **(headers or {})}, **kw))

    def audit_lines(self) -> list[str]:
        return [json.dumps({"method": a.method, "url": a.url, "status": a.status, "bytes": a.bytes}) for a in self.audit]


def make_http(options: Mapping[str, Any], transport: Transport | None = None, env: Mapping[str, str] | None = None,
              base_headers: Mapping[str, str] | None = None) -> ReadOnlyHttp:
    """The one way a connector builds its client: credentials from options, transport from the caller (tests) or real."""
    headers, secrets = auth_from_options(options, env)
    t = transport or UrllibTransport(timeout=opt_int(options, "timeout", 60), ca_bundle=options.get("ca_bundle"),
                                     retries=opt_int(options, "retries", 3), max_bytes=opt_int(options, "max_bytes", 512 * 1024 * 1024),
                                     max_wait=float(opt_int(options, "max_wait", 120)))
    ua = str(options.get("user_agent") or USER_AGENT)
    if any(c in ua for c in "\r\n"):
        raise ConnectError("option 'user_agent' must be one line")
    return ReadOnlyHttp(t, {"User-Agent": ua, **(base_headers or {}), **headers}, secrets, max_requests=opt_int(options, "max_requests", 1_000_000))


def next_link(link_header: str | None) -> str | None:
    """RFC 8288 Link header -> URL of rel="next" (or None)."""
    if not link_header:
        return None
    for part in re.split(r",\s*(?=<)", link_header):
        m = re.match(r"\s*<([^>]*)>(.*)", part)
        if m and re.search(r'rel\s*=\s*"?([^";]*\s)?next(\s[^";]*)?"?', m.group(2), re.I):
            return m.group(1)
    return None
