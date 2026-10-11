"""reqin sniff|discover|propose|import  - the same four steps the app's Import screen performs."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .adapter import Source, load_adapters, pick_adapter, sniff_all
from .ingest import ingest
from .mapping import Profile, propose_profile


def _src(a) -> Source:
    opts = dict(kv.split("=", 1) for kv in (a.opt or []))
    return Source(a.source, opts)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reqin", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, h in (("sniff", "which adapter recognises this source"), ("discover", "show containers, fields and samples"),
                    ("propose", "write a PROPOSED mapping profile (YAML) for a human to edit"), ("import", "run the pipeline, print the report")):
        p = sub.add_parser(name, help=h)
        p.add_argument("source")
        p.add_argument("--opt", action="append", metavar="K=V", help="adapter option, e.g. query=... id_column=id sheet=Requirements")
        if name in ("propose", "import"):
            p.add_argument("--adapter")
        if name == "import":
            p.add_argument("--profile", help="confirmed profile YAML; omit to use a PROPOSED one")
            p.add_argument("--out", help="write requirements as JSON lines")
    a = ap.parse_args(argv)
    src = _src(a)
    if a.cmd == "sniff":
        for score, name in sniff_all(src):
            print(f"{score:.2f}  {name}")
        return 0
    ad = load_adapters()[a.adapter]() if getattr(a, "adapter", None) else pick_adapter(src)
    if a.cmd == "discover":
        print(json.dumps(asdict(ad.discover(src)), indent=2, default=str))
    elif a.cmd == "propose":
        print(propose_profile(ad.discover(src), ad.name, name=f"proposed-{Path(a.source).stem}").to_yaml())
    else:
        prof = Profile.from_yaml(Path(a.profile).read_text()) if a.profile else None
        res = ingest(src, profile=prof, adapter=ad)
        print(json.dumps(res.report, indent=2, default=str))
        if a.out:
            with open(a.out, "w", encoding="utf-8") as f:
                for q in res.requirements:
                    f.write(json.dumps(asdict(q), default=str) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
