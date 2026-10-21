"""The demo project: the people and the sample activity the prototype page shows, as a project on the reference server.

The seed file is written by the page itself (`node prototype/export_seed.js`), so the people here are the page's people and the sample decisions
are the page's sample decisions. Nothing in it is real: it is the same made-up air vehicle project the page shows without a server.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import PROJECT_ID, ServerError, Store

SEED_FORMAT = "reqin-demo-seed/1"
MAX_SEED_BYTES = 32 * 1024 * 1024


def load_seed(path: str | Path) -> dict[str, Any]:
    """Read and check a seed file. Raises ServerError with a sentence the person can act on."""
    p = Path(path)
    if not p.is_file() or p.stat().st_size > MAX_SEED_BYTES:
        raise ServerError(400, "bad_seed", f"{p} is not a seed file I can read (missing, or larger than {MAX_SEED_BYTES // 1048576} MB).")
    try:
        seed = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise ServerError(400, "bad_seed", f"{p} is not valid JSON.") from None
    if not isinstance(seed, dict) or seed.get("format") != SEED_FORMAT:
        raise ServerError(400, "bad_seed", f"{p} is not a demo seed: its format should be {SEED_FORMAT}.")
    if not PROJECT_ID.fullmatch(str(seed.get("project", ""))) or not isinstance(seed.get("people"), list) or not isinstance(seed.get("docs"), list):
        raise ServerError(400, "bad_seed", f"{p} needs a project id, a list of people and a list of documents.")
    return seed


def make_demo(store: Store, seed_path: str | Path) -> tuple[str, dict[str, str], int]:
    """Create the demo project and its sample activity. Returns (project id, {person key: token}, documents seeded)."""
    seed = load_seed(seed_path)
    tokens = store.init_project(seed["project"], seed["people"])
    return seed["project"], tokens, store.seed(seed["project"], seed["docs"])
