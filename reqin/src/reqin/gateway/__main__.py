"""Command line for the AI gateway:  python -m reqin.gateway serve|markings|check|verify-log   (or `reqin-gateway`)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .audit import AuditLog, verify_log
from .config import ConfigError, load_config
from .core import Markings


def _rows_from_list(path: str):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("the list file is a JSON list of {id, marking, text}")
    for r in data:
        if not isinstance(r, dict) or not isinstance(r.get("id"), str):
            raise ValueError("every entry needs an id")
        yield r["id"], r.get("marking"), r.get("text", "")


def _rows_from_dataset(folder: str, field: str):
    """requirements.jsonl of a dataset written by `reqin ingest`: the marking is read from the field the project calls it, in the canonical fields or in what the source had besides."""
    f = Path(folder) / "requirements.jsonl"
    want = field.strip().lower()
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        r = json.loads(line)
        marking = None
        for bag in (r.get("fields") or {}, r.get("extra") or {}):
            for k, v in bag.items():
                if str(k).strip().lower() == want and v not in (None, ""):
                    marking = str(v)
        if not isinstance(r.get("uid"), str):
            raise ValueError(f"line {i}: no uid")
        yield r["uid"], marking, r.get("text", "")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reqin-gateway", description="The AI gateway: forwards a prompt to the model only when the shared project's AI gate is open for it (see docs/AI_GATEWAY.md).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="run the gateway")
    s.add_argument("--config", required=True)
    c = sub.add_parser("check", help="read the settings and the markings file and say what the gateway would do; nothing is started")
    c.add_argument("--config", required=True)
    m = sub.add_parser("markings", help="make the markings file (each requirement's marking and fingerprints of its wording, never the wording) from a dataset or a list")
    src = m.add_mutually_exclusive_group(required=True)
    src.add_argument("--dataset", help="a folder written by `reqin ingest` (requirements.jsonl)")
    src.add_argument("--list", help="a JSON list of {id, marking, text}")
    m.add_argument("--field", default="Marking", help="with --dataset: the name of the field that holds the marking (default Marking)")
    m.add_argument("--out", required=True)
    v = sub.add_parser("verify-log", help="recompute the gateway's record; exit 1 if a line was changed or removed")
    v.add_argument("--log", required=True)
    v.add_argument("--expect-head", default="", help="the head hash you wrote down last time")
    args = ap.parse_args(argv)
    try:
        if args.cmd == "markings":
            rows = list(_rows_from_dataset(args.dataset, args.field) if args.dataset else _rows_from_list(args.list))
            data = Markings.build(rows)
            fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=0, sort_keys=True)
            unmarked = sum(1 for r in data["requirements"].values() if not r["marking"])
            short = sum(1 for r in data["requirements"].values() if not r["fp"])
            print(f"Wrote {args.out}: {len(rows)} requirements, {unmarked} with no marking recorded, {short} too short to be recognised in a prompt. The file holds fingerprints of the wording, not the wording; keep it with the gateway.")
            return 0
        if args.cmd == "verify-log":
            res = verify_log(args.log, args.expect_head)
            print(json.dumps(res))
            return 0 if res["ok"] else 1
        cfg = load_config(args.config)
        mk = Markings.from_file(json.loads(cfg.markings.read_text(encoding="utf-8")))
        if args.cmd == "check":
            print(f"Settings are readable. The gateway would listen on {cfg.host}:{cfg.port}, read the AI switch and data sheet from {cfg.server}, and forward to {cfg.upstream_url} as model {cfg.route['model']!r} (runs {cfg.route['where']}, text {'leaves' if cfg.route['leaves'] else 'stays inside'} the network, prompts kept: {cfg.route['log']}).")
            print(f"It knows {len(mk.marks)} requirements. The model's API key {'is read from ' + cfg.key_env + (' (set)' if os.environ.get(cfg.key_env) else ' (NOT SET in this environment)') if cfg.key_env else 'is not used'}.")
            return 0
        from .http import make_gateway
        audit = AuditLog(cfg.log)
        gw = make_gateway(cfg, mk, audit, lambda line: print(line, flush=True))
        print(f"Serving on http://{gw.server_address[0]}:{gw.server_address[1]} ({len(mk.marks)} requirements known, record in {cfg.log}). Ctrl-C to stop.", flush=True)
        try:
            gw.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            gw.server_close()
        return 0
    except (ConfigError, ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
