"""Command line for the reference server:  python -m reqin.server init|serve|verify|rotate-token  (or `reqin-server`)."""
from __future__ import annotations

import argparse
import json
import os
import sys

from .http import make_server
from .store import ServerError, Store


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reqin-server", description="Reference server for shared decisions (see SERVER.md).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("init", help="create a project from a people file and print each person's token once")
    a.add_argument("--db", required=True); a.add_argument("--project", required=True); a.add_argument("--people", required=True, help='JSON list: [{"key","name","role":"lead|reviewer|observer","lens":"SE|PE|UX|NU"}]')
    a.add_argument("--tokens-out", help="write the tokens to this file (mode 600) instead of printing them")
    r = sub.add_parser("rotate-token", help="replace one person's token (the old one stops working)")
    r.add_argument("--db", required=True); r.add_argument("--project", required=True); r.add_argument("--person", required=True)
    s = sub.add_parser("serve", help="run the server")
    s.add_argument("--db", required=True); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8780)
    s.add_argument("--allow-remote", action="store_true", help="bind to a non-loopback address (put a TLS reverse proxy in front)")
    v = sub.add_parser("verify", help="recompute the record of a project; exit 1 if it was changed")
    v.add_argument("--db", required=True); v.add_argument("--project", required=True); v.add_argument("--expect-head", default="", help="the head hash you wrote down last time")
    args = ap.parse_args(argv)
    try:
        st = Store(args.db)
        if args.cmd == "init":
            with open(args.people, encoding="utf-8") as f:
                people = json.load(f)
            tokens = st.init_project(args.project, people)
            if args.tokens_out:
                fd = os.open(args.tokens_out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(tokens, f, indent=2)
                print(f"Created {args.project} with {len(tokens)} people. Tokens are in {args.tokens_out}; they are not stored anywhere else.")
            else:
                print(json.dumps(tokens, indent=2))
                print("Copy these now: only their hashes are kept, so they cannot be shown again.", file=sys.stderr)
        elif args.cmd == "rotate-token":
            print(st.rotate_token(args.project, args.person))
            print("The old token no longer works. Copy this one now.", file=sys.stderr)
        elif args.cmd == "verify":
            res = st.verify(args.project, args.expect_head)
            print(json.dumps(res, indent=2))
            return 0 if res["ok"] else 1
        else:
            srv = make_server(st, args.host, args.port, args.allow_remote, log=lambda line: print(line, flush=True))
            print(f"Serving on http://{args.host}:{srv.server_address[1]} (Ctrl-C to stop)", flush=True)
            try:
                srv.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                srv.server_close()
        return 0
    except ServerError as e:
        print(f"error: {e.message}", file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
