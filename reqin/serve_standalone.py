#!/usr/bin/env python3
"""Run the reference server with nothing but Python's standard library: no `pip install`, none of reqin's file-reading dependencies.

    python3 reqin/serve_standalone.py demo --db demo.db --seed prototype/demo/seed.json --app prototype/project
    python3 reqin/serve_standalone.py init|serve|verify|rotate-token ...        (the same commands as `reqin-server`)
    python3 reqin/serve_standalone.py gateway serve|check|markings|verify-log ...   (the AI gateway: the same commands as `reqin-gateway`)

The server package (src/reqin/server) uses only the standard library, but importing anything from `reqin` runs reqin's own __init__, which pulls in
the adapters and their libraries. This script puts a bare `reqin` package in front of it so that only the server is loaded. That is what the prototype's
browser tests use, so they need nothing besides Playwright, and what a small container for the server would run. tests/test_server_app.py checks that it
starts under `python -S -I`, which hides every installed package."""
import sys
import types
from pathlib import Path

if "reqin" not in sys.modules:
    pkg = types.ModuleType("reqin")
    pkg.__path__ = [str(Path(__file__).resolve().parent / "src" / "reqin")]
    sys.modules["reqin"] = pkg

from reqin.server.__main__ import main  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gateway":
        from reqin.gateway.__main__ import main as gateway_main  # noqa: E402
        sys.exit(gateway_main(sys.argv[2:]))
    sys.exit(main())
