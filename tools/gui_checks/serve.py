#!/usr/bin/env python3
"""A small local web server for a screen and the datasets it is tested with.

    python3 tools/gui_checks/serve.py                                  serve design/reference_viewer
    python3 tools/gui_checks/serve.py --app my_app/ --datasets DIR     serve your own app and a folder of datasets
    python3 tools/gui_checks/serve.py --port 8080

What it serves, at http://127.0.0.1:PORT/ (this machine only):
    /                 the app folder (its index.html)
    /datasets/...     the datasets folder, so a page can open ?dataset=datasets/F02_everything
    /tokens.css       design/tokens.css, and /fonts/... the font files, when the app folder does not carry its own copy

so an app can link tokens.css the way the design kit says and still load its fonts without anyone copying files around.
Nothing outside those three places is ever served. The page never needs a network: every font and script is a file here.
Standard library only.
"""
from __future__ import annotations

import argparse
import contextlib
import http.server
import mimetypes
import os
import socketserver
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_APP = REPO / "design" / "reference_viewer"
TOKENS = REPO / "design" / "tokens.css"
FONTS = REPO / "prototype" / "project" / "fonts"

TYPES = {".jsonl": "application/x-ndjson; charset=utf-8", ".json": "application/json; charset=utf-8", ".woff2": "font/woff2",
         ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".html": "text/html; charset=utf-8", ".svg": "image/svg+xml"}


def _inside(root: Path, rel: str) -> Path | None:
    """The file under root that rel names, or None. A path that climbs out of root, or a symlink that leaves it, is refused."""
    root = root.resolve()
    p = (root / rel.lstrip("/")).resolve()
    if p == root or root in p.parents:
        return p
    return None


def resolve(url_path: str, app: Path, datasets: Path | None) -> Path | None:
    rel = url_path.split("?", 1)[0].split("#", 1)[0]
    from urllib.parse import unquote
    rel = unquote(rel)
    if "\x00" in rel:
        return None
    if rel.startswith("/datasets/") and datasets is not None:
        p = _inside(datasets, rel[len("/datasets/"):])
    else:
        p = _inside(app, rel or "/")
        if p is not None and p.is_dir():
            p = p / "index.html"
        if (p is None or not p.is_file()) and rel == "/tokens.css":
            p = TOKENS
        elif (p is None or not p.is_file()) and rel.startswith("/fonts/"):
            p = _inside(FONTS, rel[len("/fonts/"):])
    return p if p is not None and p.is_file() else None


def make_handler(app: Path, datasets: Path | None, quiet: bool = True):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            p = resolve(self.path, app, datasets)
            if p is None:
                self.send_error(404, "not found")
                return
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", TYPES.get(p.suffix.lower()) or mimetypes.guess_type(p.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        do_HEAD = do_GET  # noqa: N815

        def log_message(self, fmt, *args):
            if not quiet:
                sys.stderr.write("%s\n" % (fmt % args))
    return Handler


class _Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


@contextlib.contextmanager
def serving(app: str | os.PathLike = DEFAULT_APP, datasets: str | os.PathLike | None = None, port: int = 0):
    """with serving(app, datasets) as base_url: ...   The port 0 asks the system for a free one."""
    app_p = Path(app).resolve()
    if not app_p.is_dir():
        raise SystemExit("the app folder %s does not exist" % app)
    ds_p = Path(datasets).resolve() if datasets else None
    if ds_p is not None and not ds_p.is_dir():
        raise SystemExit("the datasets folder %s does not exist" % datasets)
    srv = _Server(("127.0.0.1", port), make_handler(app_p, ds_p))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield "http://127.0.0.1:%d" % srv.server_address[1]
    finally:
        srv.shutdown()
        srv.server_close()
        t.join(timeout=5)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--app", default=str(DEFAULT_APP), help="the folder with the app's index.html (default: design/reference_viewer)")
    ap.add_argument("--datasets", help="a folder of dataset folders, served at /datasets/ (for example the output of: reqin make-datasets DIR)")
    ap.add_argument("--port", type=int, default=8000)
    a = ap.parse_args(argv)
    with serving(a.app, a.datasets, a.port) as base:
        print("serving %s at %s  (Ctrl+C stops it)" % (a.app, base))
        if a.datasets:
            print("datasets at %s/datasets/   for example %s/?dataset=datasets/F02_everything" % (base, base))
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
