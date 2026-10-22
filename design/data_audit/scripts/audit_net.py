"""The browser part of the audit: open the person's page, read what is on the screen, record what the page loaded, and open it again with the data changed.

Needs Playwright with Chromium (`pip install playwright && playwright install chromium`). Everything else in this folder runs without it.

The rules this file keeps, because the audit must be safe to point at a real system:
  - **It sends no write that it can see.** Any HTTP request that is not GET, HEAD or OPTIONS is refused before it leaves the browser and is listed (`Visit.blocked`);
    `allow_post` is a pattern for the few addresses where a POST is a read (a search, a GraphQL query), and the person has to name it. A WebSocket the page opens is given a
    connection that goes nowhere (`Visit.sockets`); web workers, WebRTC and WebTransport are not allowed to start (`Visit.refused_features`), and service workers are blocked.
    What it cannot know: whether a GET changes something on the server (some do), and what a setup step the person asked for does on the page. The page is opened many times
    (every replay is another load), so a GET that counts visits counts them all.
  - **It changes only what the page is told.** The data replayed in a changed visit is made from the first visit's own responses. Nothing is sent anywhere.
  - **What it saves stays in the session folder** (the responses hold the person's data, and the browser state holds any sign-in the page kept), and `audit.py init` refuses a
    session folder inside a git repository.

Modes of a visit:
  record      the page as it is. Responses are recorded.
  canary      every text and number in each JSON data response replaced by an invented value (same text, same invented value: joins and filters still hold).
  empty       each JSON data response replaced by the same shape with nothing in it.
  error       each data request answered with a server error.
  disconnect  each data request fails as if the network were down.
A *data request* is a fetch or XHR. The page itself, its scripts, styles, images and fonts are loaded normally in every mode. `warm=True` starts the browser holding what the
record visit left behind (cookies, local storage, IndexedDB); the default is a clean browser.
"""
from __future__ import annotations

import contextlib
import functools
import http.server
import json
import re
import socket
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_values as V  # noqa: E402

REPO = HERE.parent.parent.parent
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))

MODES = ("record", "canary", "empty", "error", "disconnect")
READS = {"GET", "HEAD", "OPTIONS"}
DATA_TYPES = {"fetch", "xhr"}
BODY_CAP = 20_000_000                                          # a text response bigger than this is counted but not kept (see Visit.truncated)
FETCH_MS = 15000                                               # how long the audit waits to read one data response as it arrives
LATE_TYPES = {"document", "script", "stylesheet", "manifest", "other"}      # read after the page settled; data requests are read as they arrive
SKIP_NOTE = "the audit needs Playwright with Chromium:  pip install playwright && playwright install chromium"


# ------------------------------------------------------------------------------------------------ what one visit holds
@dataclass
class Visit:
    mode: str
    warm: bool = False
    url: str = ""
    origin: str = ""
    ok: bool = True
    error: str = ""
    title: str = ""
    text: str = ""                                  # the words on the screen, one space between
    items: list = field(default_factory=list)       # [{text, kind, tag, testid, hook (the element's id and classes), anc, head (the column heading of a table cell), source, state}]
    marks: list = field(default_factory=list)       # elements that say where their data came from
    body_state: str = ""
    responses: list = field(default_factory=list)   # [{url, method, status, type, content_type, json, body, bytes}]
    blocked: list = field(default_factory=list)     # requests that were not reads and were refused
    sockets: list = field(default_factory=list)     # WebSockets the page opened (each was given a connection that goes nowhere)
    refused_features: list = field(default_factory=list)   # things the page tried to start that the audit does not allow (workers, WebRTC, WebTransport)
    truncated: list = field(default_factory=list)   # text responses bigger than BODY_CAP: [{url, bytes}]
    final_url: str = ""
    refused: list = field(default_factory=list)     # data requests the mode made fail or empty: [{url, how}]
    changed: int = 0                                # data responses this mode rewrote
    page_errors: list = field(default_factory=list)
    console_errors: list = field(default_factory=list)
    shot: str = ""
    canary_replaced: int = 0
    canary_fields: dict = field(default_factory=dict)   # canary token -> the field names it stood for (never the values)

    def data_responses(self) -> list:
        return [r for r in self.responses if r["type"] in DATA_TYPES]


def visit_from_json(d: dict) -> Visit:
    names = Visit.__dataclass_fields__.keys()
    return Visit(**{k: v for k, v in d.items() if k in names})


# ------------------------------------------------------------------------------------------------ serving a local page
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a, **k):                 # no noise
        pass


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextlib.contextmanager
def served(page: str, port: int = 0):
    """The address to open. A web address is returned as it is; a file or folder is served on 127.0.0.1 for as long as the block runs."""
    if re.match(r"^https?://", page or ""):
        yield page
        return
    p = Path(page).resolve()
    if not p.exists():
        raise SystemExit("the page is not a web address and not a file or folder here: %s" % page)
    root, name = (p, "") if p.is_dir() else (p.parent, p.name)
    handler = functools.partial(_Quiet, directory=str(root))
    try:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    except OSError:
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d/%s" % (httpd.server_address[1], name)
    finally:
        httpd.shutdown()
        httpd.server_close()


def origin_of(url: str) -> str:
    m = re.match(r"^(https?://[^/]+)", url)
    return m.group(1) if m else ""


def rebase_storage(state: dict, old_origin: str, new_origin: str) -> dict:
    """The saved browser state with its origin changed, so a page served on a different local port finds what the earlier visit stored."""
    if not state or not old_origin or old_origin == new_origin:
        return state
    s = json.loads(json.dumps(state))
    for o in s.get("origins", []):
        if o.get("origin") == old_origin:
            o["origin"] = new_origin
    return s


# ------------------------------------------------------------------------------------------------ reading the screen
EXTRACT_JS = r"""
() => {
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','HEAD','TITLE','META','LINK','SVG_DEFS']);
  const INLINE = new Set(['A','B','I','EM','STRONG','SPAN','CODE','SMALL','SUB','SUP','MARK','ABBR','TIME','U','S','BDI','CITE','KBD','Q','VAR','BR','WBR']);
  const ids = new Map(); const nid = el => { if (!ids.has(el)) ids.set(el, ids.size + 1); return ids.get(el); };
  const items = [], marks = [];
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  const sees = (el, cs) => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && parseFloat(cs.opacity) !== 0; };
  const markOf = el => { const m = el.closest && el.closest('[data-source]'); return m ? {source: m.getAttribute('data-source') || '', state: m.getAttribute('data-source-state') || '', asof: m.getAttribute('data-as-of') || ''} : null; };
  const tidOf = el => { const t = el.closest && el.closest('[data-testid]'); return t ? t.getAttribute('data-testid') : ''; };
  const hookOf = el => ((el.id || '') + ' ' + (typeof el.className === 'string' ? el.className : '')).trim();
  const headOf = el => { const c = el.closest && el.closest('td'); if (!c) return ''; const t = c.closest('table'); const hr = t && ((t.tHead && t.tHead.rows[0]) || t.rows[0]); return hr && hr.cells[c.cellIndex] ? clean(hr.cells[c.cellIndex].innerText) : ''; };
  function walk(el, anc, covered) {
    if (SKIP.has(el.tagName.toUpperCase())) return;
    const cs = getComputedStyle(el);
    if (cs.display === 'none') return;
    const here = [nid(el)].concat(anc).slice(0, 9);
    const tag = el.tagName.toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      const type = (el.getAttribute('type') || '').toLowerCase();
      if (sees(el, cs) && type !== 'password' && type !== 'hidden') {
        let v = tag === 'select' ? (el.selectedOptions[0] ? el.selectedOptions[0].text : '') : el.value;
        v = clean(v);
        if (v) items.push({text: v, kind: 'input', tag, testid: tidOf(el), hook: hookOf(el), anc: here, mark: markOf(el), head: headOf(el)});
      }
      return;
    }
    let childCovered = covered;
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3 && clean(n.textContent));
    if (own.length && !covered && sees(el, cs)) {
      const allInline = Array.from(el.querySelectorAll('*')).every(d => INLINE.has(d.tagName.toUpperCase()) && !d.hasAttribute('data-testid') && !d.hasAttribute('data-source-label'));
      const text = clean(allInline ? el.innerText : own.map(n => n.textContent).join(' '));
      if (text) items.push({text, kind: 'text', tag, testid: tidOf(el), hook: hookOf(el), anc: here, mark: markOf(el), head: headOf(el)});
      if (allInline) childCovered = true;
    }
    if (el.hasAttribute && el.hasAttribute('data-source')) {
      const lab = el.querySelector('[data-source-label]');
      marks.push({source: el.getAttribute('data-source') || '', state: el.getAttribute('data-source-state') || '', asof: el.getAttribute('data-as-of') || '',
        label: lab ? clean(lab.innerText) : '', label_visible: lab ? sees(lab, getComputedStyle(lab)) : false, anc: here.slice(0, 3), shown: sees(el, cs)});
    }
    for (const c of el.children) walk(c, here, childCovered);
    if (el.shadowRoot) for (const c of el.shadowRoot.children) walk(c, here, childCovered);
  }
  if (document.body) walk(document.body, [], false);
  return {items, marks, title: document.title || '', bodyState: (document.body && document.body.getAttribute('data-state')) || '',
          text: clean(document.body ? document.body.innerText : '')};
}
"""


def _texty(content_type: str, rtype: str) -> bool:
    if rtype in ("image", "font", "media", "eventsource", "websocket", "ping"):
        return False
    ct = (content_type or "").lower()
    if "event-stream" in ct:
        return False                                            # never ends: asking for its body waits for ever
    return not ct or ct.startswith("text/") or any(k in ct for k in ("json", "javascript", "xml", "csv"))


def _entry(resp, held: dict | None = None) -> dict:
    """What the page received. `held` has the body of every data response, read as it arrived ({request: bytes}). A data response is not read afterwards: asking the browser for
    the body of a fetch or XHR answer the page never read (with `Cache-Control: no-store`) was seen to wait for ever (Chromium, Playwright 1.56). Other responses (the page, its
    scripts and styles) are read after the page has settled."""
    req = resp.request
    ct = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    e = {"url": resp.url, "method": req.method, "status": resp.status, "type": req.resource_type, "content_type": ct, "json": False, "body": "", "bytes": 0}
    if _texty(ct, req.resource_type):
        try:
            b = (held or {}).get(req)
            if b is None and req.resource_type in LATE_TYPES:
                b = resp.body()
            if b is not None:
                e["bytes"] = len(b)
                if len(b) <= BODY_CAP:
                    e["body"] = b.decode("utf-8", "replace")
                else:
                    e["truncated"] = True
        except Exception:
            pass
    e["json"] = "json" in ct or (req.resource_type in DATA_TYPES and e["body"].lstrip()[:1] in ("[", "{"))
    return e


# What the audit refuses to let a page start, because it would send or receive outside the one place the audit watches (the HTTP requests). Written as an init script so it runs
# before the page's own, in every frame.
REFUSE_JS = r"""
(() => {
  const note = what => { try { console.debug('AUDIT-REFUSED ' + what); } catch (e) {} };
  const refuse = (name, what) => {
    if (!(name in window)) return;
    const stub = function () { note(what); throw new DOMException('the audit does not allow ' + name, 'NotSupportedError'); };
    try { Object.defineProperty(window, name, {value: stub, configurable: true, writable: true}); } catch (e) {}
  };
  refuse('Worker', 'web worker'); refuse('SharedWorker', 'web worker');
  refuse('RTCPeerConnection', 'WebRTC'); refuse('webkitRTCPeerConnection', 'WebRTC'); refuse('WebTransport', 'WebTransport');
})();
"""


# ------------------------------------------------------------------------------------------------ the runner
class Runner:
    """Opens the person's page as many times as a check needs, in one browser, on one address. Use as a context manager."""

    def __init__(self, page: str, *, width: int = 1440, height: int = 900, setup=(), storage_state=None, allow_post: str = "", settle_ms: int = 800,
                 timeout_ms: int = 20000, port: int = 0):
        self.page, self.width, self.height, self.setup = page, width, height, list(setup or [])
        self.storage_state = storage_state                  # a Playwright storage-state file (a sign-in), or None
        self.allow = re.compile(allow_post) if allow_post else None
        self.settle_ms, self.timeout_ms, self.port = settle_ms, timeout_ms, port
        self._stack = contextlib.ExitStack()
        self.url = ""
        self.origin = ""

    def __enter__(self):
        self.url = self._stack.enter_context(served(self.page, self.port))
        self.origin = origin_of(self.url)
        self._started = False
        return self

    def _start(self) -> None:
        """Start Chromium the first time a visit needs it, so a command that only reads saved visits never opens a browser."""
        if self._started:
            return
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            raise SystemExit(SKIP_NOTE)
        try:
            self._pw = sync_playwright().start()
            self._stack.callback(self._pw.stop)
            self.browser = self._pw.chromium.launch()
            self._stack.callback(self.browser.close)
        except Exception as e:                               # noqa: BLE001
            raise SystemExit("could not start Chromium: %s\n%s" % (str(e).splitlines()[0] if str(e) else e, SKIP_NOTE))
        self._started = True

    def __exit__(self, *exc):
        self._stack.close()
        return False

    # -- one visit
    def visit(self, mode: str = "record", *, warm_state: dict | None = None, canary: V.Canary | None = None, shot: str | Path | None = None, want_storage: bool = False):
        """Returns (Visit, storage_state_or_None). `warm_state` is a saved browser state to start from; None means a clean browser."""
        if mode not in MODES:
            raise ValueError("mode must be one of %s" % ", ".join(MODES))
        self._start()
        v = Visit(mode=mode, warm=warm_state is not None, url=self.url, origin=self.origin)
        canary = canary or V.Canary()
        state = None
        if warm_state is not None:
            state = warm_state
        elif self.storage_state:
            state = str(self.storage_state)
        ctx = self.browser.new_context(viewport={"width": self.width, "height": self.height}, storage_state=state, service_workers="block")
        if not hasattr(ctx, "route_web_socket"):
            ctx.close()
            raise SystemExit("the audit needs Playwright 1.48 or newer: it has to be able to refuse WebSockets, so that a page cannot write over one.  pip install -U playwright")
        ctx.add_init_script(REFUSE_JS)
        try:
            self._open(ctx, v, mode, canary, shot)
            storage = None
            if want_storage:
                try:
                    storage = ctx.storage_state(indexed_db=True)
                except TypeError:
                    storage = ctx.storage_state()
        finally:
            ctx.close()
        return v, storage

    def _open(self, ctx, v: Visit, mode: str, canary: V.Canary, shot) -> None:
        pending = []
        held: dict = {}                                                  # {request: body bytes} for every data response, read as it arrives

        act = {"last": time.monotonic(), "busy": 0}                      # when the page last did something on the network, and how many answers the audit is still reading

        def handler(route):
            act["busy"] += 1
            try:
                handle(route)
            finally:
                act["busy"] -= 1
                act["last"] = time.monotonic()

        def handle(route):
            req = route.request
            url, method, rtype = req.url, req.method, req.resource_type
            is_read = method in READS
            if not is_read and not (self.allow and self.allow.search(url)):
                v.blocked.append({"method": method, "url": url})
                route.abort("blockedbyclient")
                return
            streaming = rtype == "eventsource" or "event-stream" in (req.headers.get("accept") or "").lower()
            data = rtype in DATA_TYPES and not streaming
            change = data and mode != "record"
            if change and mode == "disconnect":
                v.refused.append({"url": url, "how": "connection down"})
                route.abort("internetdisconnected")
                return
            if change and mode == "error":
                v.refused.append({"url": url, "how": "server error 500"})
                route.fulfill(status=500, content_type="application/json", body='{"error": "the audit made this request fail on purpose"}')
                return
            if data or not is_read:                                    # read the answer now; see _entry
                try:
                    resp = route.fetch(timeout=FETCH_MS)
                    body = resp.body()
                except Exception:                                      # noqa: BLE001
                    if is_read:
                        route.continue_()                              # a read can safely be asked for again
                    else:
                        route.abort("failed")                          # a POST the person allowed is never sent twice
                    return
                held[req] = body
                doc = V.parse_json(body.decode("utf-8", "replace")) if change else None
                if doc is None:
                    route.fulfill(response=resp)
                    return
                new = canary.apply(doc) if mode == "canary" else V.emptied(doc)
                v.changed += 1
                headers = {k: val for k, val in resp.headers.items() if k.lower() not in ("content-length", "content-encoding", "transfer-encoding", "content-type")}
                held[req] = json.dumps(new).encode("utf-8")
                route.fulfill(status=resp.status, headers=headers, content_type="application/json", body=json.dumps(new))
                return
            route.continue_()                                          # a stream is let through and never read

        def socket_handler(ws):
            v.sockets.append(ws.url)                                  # not connected to any server: whatever the page sends goes nowhere

        def on_console(m):
            if m.type == "debug" and m.text.startswith("AUDIT-REFUSED "):
                what = m.text[len("AUDIT-REFUSED "):]
                if what not in v.refused_features:
                    v.refused_features.append(what)
            elif m.type == "error":
                v.console_errors.append(m.text[:300])

        ctx.route("**/*", handler)
        ctx.route_web_socket(re.compile(r".*"), socket_handler)
        page = ctx.new_page()
        page.on("response", lambda r: pending.append(r))
        page.on("request", lambda r: act.update(last=time.monotonic()))
        page.on("pageerror", lambda e: v.page_errors.append(str(e)[:300]))
        page.on("console", on_console)
        try:
            page.goto(self.url, wait_until="load", timeout=self.timeout_ms)
            self._settle(page, act)
            if self.setup:
                import site_map as SM                                    # the same steps tools/gui_checks/site_map.py takes
                SM.run_setup(page, self.setup)
                self._settle(page, act)
            v.final_url = page.url
            if page.url.startswith("chrome-error:"):
                why = "; ".join("%s %s" % (b["method"], re.sub(r"^https?://[^/]+", "", b["url"])) for b in v.blocked[:3])
                raise RuntimeError("the page left for an address the audit would not open" + (" (refused: %s)" % why if why else ""))
            got = page.evaluate(EXTRACT_JS)
            texts = [got["text"]]
            for n, fr in enumerate(page.frames[1:], 1):                  # frames the person can see: their words are on the screen too
                try:
                    if not fr.frame_element().is_visible():
                        continue
                    sub = fr.evaluate(EXTRACT_JS)
                except Exception:                                        # noqa: BLE001
                    continue
                shift = n * 100000                                       # element numbers are per frame; keep them apart
                for i in sub["items"]:
                    i["anc"] = [a + shift for a in i["anc"]]
                for m in sub["marks"]:
                    m["anc"] = [a + shift for a in m["anc"]]
                got["items"] += sub["items"]
                got["marks"] += sub["marks"]
                texts.append(sub["text"])
            v.title, v.text, v.body_state = got["title"], " ".join(t for t in texts if t), got["bodyState"]
            v.items = [{**i, "source": (i.get("mark") or {}).get("source", ""), "state": (i.get("mark") or {}).get("state", "")} for i in got["items"]]
            v.marks = got["marks"]
            if shot:
                Path(shot).parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(shot), full_page=True)
                v.shot = str(shot)
        except Exception as e:                                           # noqa: BLE001
            v.ok, v.error = False, (str(e).splitlines() or [repr(e)])[0][:300]
        for r in pending:
            try:
                e = _entry(r, held)
                if e.get("truncated"):
                    v.truncated.append({"url": e["url"], "bytes": e["bytes"]})
                v.responses.append(e)
            except Exception:                                            # noqa: BLE001
                continue
        v.canary_replaced = len(canary.map) + len(canary.nmap)
        v.canary_fields = dict(canary.fields)

    def _settle(self, page, act: dict) -> None:
        """Wait until the page has been quiet on the network for `settle_ms` and the audit has finished reading every data answer, or `timeout_ms` has passed. (The browser's own
        'network idle' is not used: a fetch whose answer the page never reads keeps it from ever being idle.)"""
        end = time.monotonic() + self.timeout_ms / 1000.0
        page.wait_for_timeout(50)
        while time.monotonic() < end:
            if act["busy"] == 0 and (time.monotonic() - act["last"]) * 1000.0 >= self.settle_ms:
                return
            page.wait_for_timeout(50)


# ------------------------------------------------------------------------------------------------ the session's saved visits
def visit_path(sess: Path, key: str) -> Path:
    return Path(sess) / "visits" / (key + ".json")


def save_visit(sess: Path, key: str, v: Visit) -> None:
    p = visit_path(sess, key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(asdict(v), ensure_ascii=False) + "\n", encoding="utf-8")


def load_visit(sess: Path, key: str) -> Visit | None:
    p = visit_path(sess, key)
    return visit_from_json(json.loads(p.read_text(encoding="utf-8"))) if p.is_file() else None


def visit_key(mode: str, warm: bool) -> str:
    return mode + ("-warm" if warm else "")


def get_visit(runner: Runner, sess: Path, mode: str, warm: bool = False, fresh: bool = False) -> Visit:
    """The visit saved for this mode, or a new one (saved). The record visit also saves the browser state that `warm` visits start from."""
    sess = Path(sess)
    key = visit_key(mode, warm)
    if not fresh:
        got = load_visit(sess, key)
        if got is not None and got.ok:                              # a visit where the page did not open is tried again, not reused
            return got
    state = None
    if warm:
        sp = sess / "visits" / "storage.json"
        if not sp.is_file():
            get_visit(runner, sess, "record", fresh=True)           # the record visit is what leaves the state behind
        saved = json.loads(sp.read_text(encoding="utf-8")) if sp.is_file() else {"origin": "", "state": {}}
        state = rebase_storage(saved.get("state") or {}, saved.get("origin", ""), runner.origin)
    v, storage = runner.visit(mode, warm_state=state, shot=sess / "visits" / (key + ".png"), want_storage=(mode == "record" and not warm))
    save_visit(sess, key, v)
    if storage is not None:
        sp = sess / "visits" / "storage.json"
        sp.write_text(json.dumps({"origin": runner.origin, "state": storage}) + "\n", encoding="utf-8")
        try:
            sp.chmod(0o600)                                          # it can hold a sign-in: readable by the person who ran the audit only
        except OSError:
            pass
    return v
