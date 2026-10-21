"""The connected page's sync engine (prototype/parts/connect.js) against the real reference server, several people at once, run under node.

The engine is plain JavaScript with the network passed in, so node can run it exactly as the browser does. prototype/conn_test.js signs in six people of the
demo project, has them decide, sign, object, label and switch AI off at the same time, and checks what the server holds and what each page shows. This test
starts the server on a loopback port with the demo seed and reports every failed check. Skipped when node or the prototype is not in this checkout."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from reqin.server import Store
from reqin.server.demo import make_demo
from reqin.server.http import make_server, serve_in_thread

ROOT = Path(__file__).resolve().parents[2]
PROTO = ROOT / "prototype"
pytestmark = pytest.mark.skipif(not shutil.which("node") or not (PROTO / "build.py").is_file(), reason="needs node and the prototype folder")


@pytest.fixture(scope="module")
def page(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("page") / "Main.dc.html"
    subprocess.run([sys.executable, str(PROTO / "build.py"), str(out)], check=True, capture_output=True, cwd=PROTO)
    return out


@pytest.fixture()
def server(tmp_path):
    seed = PROTO / "demo" / "seed.json"
    st = Store(tmp_path / "demo.db")
    _, tokens, n = make_demo(st, seed)
    srv = make_server(st, port=0)
    serve_in_thread(srv)
    tok = tmp_path / "tokens.json"
    tok.write_text(json.dumps(tokens))
    yield srv.server_address[1], tok, st
    srv.shutdown(); srv.server_close(); st.close()


def test_the_engine_against_the_real_server(page, server):
    port, tok, st = server
    r = subprocess.run(["node", str(PROTO / "conn_test.js"), str(page), str(port), str(tok)], capture_output=True, text=True, timeout=180, cwd=PROTO)
    lines = (r.stdout + r.stderr).splitlines()
    failed = [l for l in lines if l.startswith("FAIL")]
    assert r.returncode == 0 and not failed, "\n".join(lines[-60:])
    assert sum(1 for l in lines if l.startswith("PASS")) >= 40, "the checks did not all run:\n" + "\n".join(lines)
    assert st.verify("demo")["ok"], "whatever the pages did, the record on the server still checks out"
