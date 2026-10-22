#!/usr/bin/env python3
"""A made-up server for the example apps: it serves an app's files and answers GET /api/requirements with a data file, and it records every request that is not a read.

    python3 design/data_audit/examples/server.py bad_app            # then open the address it prints
    python3 design/data_audit/examples/server.py good_app --port 8765

The tests use make_server() to prove the audit never sends a write: `writes` stays empty. Standard library only.
"""
from __future__ import annotations

import argparse
import functools
import http.server
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "records" / "requirements.json"


def make_server(app_dir, data_file=DATA, port: int = 0):
    """(httpd, log): log['reads'] and log['writes'] are lists of "METHOD path". The caller starts and stops the server (see serve_in_thread)."""
    log = {"reads": [], "writes": []}
    data_path = Path(data_file)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

        def _send(self, status, body: bytes, ctype="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            log["reads"].append("GET " + self.path)
            if self.path.split("?")[0] == "/api/requirements":
                self._send(200, data_path.read_bytes())
            else:
                super().do_GET()

        def _write(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n:
                self.rfile.read(n)
            log["writes"].append("%s %s" % (self.command, self.path))
            self._send(200, b"{}")

        do_POST = do_PUT = do_PATCH = do_DELETE = _write

    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(app_dir)))
    return httpd, log


def serve_in_thread(httpd):
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return t


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("app", help="bad_app or good_app (a folder next to this file), or any folder")
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--data", default=str(DATA))
    a = ap.parse_args(argv)
    app = Path(a.app) if Path(a.app).is_dir() else HERE / a.app
    httpd, _ = make_server(app, a.data, a.port)
    print("serving %s at http://127.0.0.1:%d/  (Ctrl-C to stop)" % (app, httpd.server_address[1]))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
