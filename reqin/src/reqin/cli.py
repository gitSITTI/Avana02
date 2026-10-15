"""reqin  sniff | discover | propose | import | sample | connectors | watch | check-dataset | make-datasets | vee

  sniff / discover / propose / import   the four steps the app's Import screen performs (import --out-dir DIR writes the dataset the GUI reads)
  check-dataset DIR                      is this folder a valid dataset under GUI_CONTRACT.md? what is in it?
  make-datasets DIR                      write the fourteen test datasets (F1-F14) a screen must pass
  vee DIR                                the engineering V of a dataset: requirements per level, and how many have a verification method and item
  sample                                 look at what a connector sees (first page only) so you can tune options and profile names
  connectors                             list every adapter with its maturity (fixture-tested / fake-server-tested / live-verified / stub)
  watch                                  re-ingest a folder of exports when they change; never writes to that folder
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from .adapter import Source, load_adapters, pick_adapter, sniff_all
from .connect import ConnectError
from .ingest import ingest
from .mapping import Profile, propose_profile

URI_HINTS = {
    "tabular": "path/to/file.csv|xlsx", "reqif_adapter": "path/to/file.reqif|reqifz", "reqif": "path/to/file.reqif|reqifz",
    "sysml_text": "path/to/model.sysml", "sql": "sqlite:///db.sqlite --opt query='SELECT ...'",
    "docx": "path/to/spec.docx (prose: every record needs human verification)", "pdf": "path/to/spec.pdf (prose: every record needs human verification)",
    "sysml_api": "sysml+https://host:8443/sysmlv2-api --opt project_name=... --opt token_env=NAME",
    "oslc_rm": "oslc+https://host/rm/rootservices --opt project=... --opt cookie_env=NAME", "agility": "agility+https://host/Instance --opt token_env=NAME",
    "mdzip": "(stub) export ReqIF from MSOSA instead",
}


def _src(a) -> Source:
    opts = dict(kv.split("=", 1) for kv in (a.opt or []))
    return Source(a.source, opts)


def _write_audit(ad, path: str | None) -> None:
    if path and ad.audit():
        Path(path).write_text("\n".join(json.dumps({"method": e.method, "url": e.url, "status": e.status, "bytes": e.bytes}) for e in ad.audit()) + "\n",
                              encoding="utf-8")


def _clip(v, n=160) -> str:
    s = str(v).replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _cmd_connectors() -> int:
    print(f"{'adapter':<12} {'fidelity':<11} {'maturity':<20} {'caps':<34} example")
    for name, cls in sorted(load_adapters().items()):
        caps = ",".join(k for k, v in asdict(cls.caps).items() if v) or "-"
        print(f"{name:<12} {cls.fidelity.value:<11} {cls.maturity:<20} {caps:<34} {URI_HINTS.get(name, '')}")
    print("\nfake-server-tested = proven against an in-memory fake of the documented API, NOT yet against a real server.")
    print("live-verified      = a person ran it against the real system and checked the result (nobody has, for any adapter here).")
    return 0


def _cmd_sample(a) -> int:
    src = _src(a)
    if not a.full:
        src.options.setdefault("peek", "1")
    ad = load_adapters()[a.adapter]() if a.adapter else pick_adapter(src)
    try:
        disc = ad.discover(src)
        print(f"adapter: {ad.name}   fidelity: {ad.fidelity.value}   maturity: {ad.maturity}")
        for n in disc.notes:
            print(f"  note: {n}")
        for c in disc.containers:
            print(f"\ncontainer {c.name!r}: {c.rows} rows")
            for f in c.fields:
                print(f"  {f.name:<28} filled {f.non_empty:>4.0%}  e.g. {_clip(f.samples[0] if f.samples else '', 70)!r}")
        print(f"\nfirst {a.n} records, exactly as the connector hands them over (before any mapping):")
        shown = 0
        for item in ad.read(src):
            if hasattr(item, "fields"):
                print(json.dumps({"locator": item.ref.locator, "container": item.ref.container, "parent": item.parent_native_id,
                                  "fields": {k: _clip(v) for k, v in item.fields.items()}}, ensure_ascii=False, indent=1))
                shown += 1
                if shown >= a.n:
                    break
        if not shown:
            print("  (none) -- check the options; the notes above usually say why")
    except ConnectError as e:
        print(f"connector error: {e}", file=sys.stderr)
        _write_audit(ad, a.audit)
        return 1
    if ad.audit():
        print(f"\nrequests made ({len(ad.audit())}), all GET:")
        for e in ad.audit()[:12]:
            print(f"  {e.status} {e.url}")
    _write_audit(ad, a.audit)
    return 0


def _cmd_check_dataset(a) -> int:
    from .dataset import check_dataset, describe
    ds, problems = check_dataset(a.dir)
    info = None if problems else describe(ds)             # a summary of a broken dataset would be a guess
    if a.json:
        print(json.dumps({"valid": not problems, "problems": problems, "describe": info}, indent=2, ensure_ascii=False))
        return 1 if problems else 0
    if problems:
        print(f"NOT a valid dataset: {a.dir}  ({len(problems)} problem(s))")
        for x in problems[:30]:
            print("  -", x)
        if len(problems) > 30:
            print(f"  ... and {len(problems) - 30} more")
        return 1
    print(f"ok: {a.dir} follows the contract")
    for k, v in (info or {}).items():
        print(f"  {k:<42} {v}")
    return 0


def _cmd_vee(a) -> int:
    from .dataset import check_dataset
    from .vee import render, vee_report
    ds, problems = check_dataset(a.dir)
    if problems:
        print(f"NOT a valid dataset: {a.dir}  ({len(problems)} problem(s)); run `reqin check-dataset` for the list. A V of a broken dataset would be a guess.", file=sys.stderr)
        return 1
    try:
        rep = vee_report(ds, by=a.by, level_field=a.level_field)
    except ValueError as e:
        print(f"vee: {e}", file=sys.stderr)
        return 2
    print(json.dumps(rep, indent=2, ensure_ascii=False) if a.json else render(rep))
    if a.max_gaps is not None and rep["total"]["gaps"] > a.max_gaps:
        print(f"vee: {rep['total']['gaps']} requirement(s) have no verification method or item, more than the {a.max_gaps} allowed.", file=sys.stderr)
        return 1
    return 0


def _cmd_make_datasets(a) -> int:
    from .contract_datasets import build_all, validate_all
    try:
        index = build_all(a.dir, a.only.split(",") if a.only else None, a.size)
    except ValueError as e:
        print(f"make-datasets: {e}", file=sys.stderr)
        return 2
    print(f"{'id':<4} {'name':<22} {'requirements':>12} {'rejected':>8} {'links':>6}  folder")
    for e in index:
        x = e["expect"]
        print(f"{e['id']:<4} {e['name']:<22} {x['requirements']:>12} {x['rejected']:>8} {x['links']:>6}  {', '.join(e['folders'])}")
    bad = {f: p for f, p in validate_all(a.dir).items() if p}
    for f, p in bad.items():
        print(f"INVALID {f}: {p[:3]}", file=sys.stderr)
    print(f"\n{len(index)} datasets and index.json written to {a.dir}; every one passes the contract check." if not bad else f"\n{len(bad)} dataset(s) FAILED the check (a bug in reqin).")
    return 1 if bad else 0


def _cmd_watch(a) -> int:
    from .watch import Watcher, WatchError, load_rules
    try:
        w = Watcher(Path(a.dir), Path(a.out), Path(a.state_dir) if a.state_dir else None, load_rules(Path(a.rules)) if a.rules else None,
                    settle=a.settle, recursive=a.recursive, include=a.include or None)
        if a.once:
            events = w.run_once()
            for ev in events:
                print(ev.line())
            return 1 if any(e.event == "error" for e in events) else 0
        w.run_forever(a.interval, lambda ev: print(ev.line(), flush=True))
    except WatchError as e:
        print(f"watch: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="reqin", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, h in (("sniff", "which adapter recognises this source"), ("discover", "show containers, fields and samples"),
                    ("propose", "write a PROPOSED mapping profile (YAML) for a human to edit"), ("import", "run the pipeline, print the report"),
                    ("sample", "peek at what a connector sees (first page) and the raw records it would hand over")):
        p = sub.add_parser(name, help=h)
        p.add_argument("source")
        p.add_argument("--opt", action="append", metavar="K=V", help="adapter option, e.g. query=... id_column=id sheet=Requirements token_env=NAME")
        if name in ("propose", "import", "sample"):
            p.add_argument("--adapter")
        if name in ("discover", "import", "sample"):
            p.add_argument("--audit", metavar="FILE", help="live connectors: write every request made (method, URL without secrets, status) to FILE")
        if name == "import":
            p.add_argument("--profile", help="confirmed profile YAML; omit to use a PROPOSED one")
            p.add_argument("--out", help="write requirements as JSON lines")
            p.add_argument("--out-dir", metavar="DIR", help="write the whole dataset the GUI reads (requirements, links, rejected, report, manifest) into DIR, then check it against the contract")
        if name == "sample":
            p.add_argument("-n", type=int, default=3, help="how many raw records to show")
            p.add_argument("--full", action="store_true", help="read everything, not just the first page")
    sub.add_parser("connectors", help="list adapters and how far each has been proven")
    cd = sub.add_parser("check-dataset", help="is this folder a valid dataset under GUI_CONTRACT.md, and what does it contain?")
    cd.add_argument("dir")
    cd.add_argument("--json", action="store_true", help="machine-readable result")
    vp = sub.add_parser("vee", help="the engineering V of a dataset: how many requirements at each level, and how many are traced to a verification method and item")
    vp.add_argument("dir")
    vp.add_argument("--by", choices=("depth", "field"), default="depth", help="where the level comes from: the parent tree (default) or a field")
    vp.add_argument("--level-field", metavar="NAME", help="with --by field: the field that holds the level (1 to 4, L2, system, component ...)")
    vp.add_argument("--json", action="store_true", help="machine-readable result")
    vp.add_argument("--max-gaps", type=int, metavar="N", help="exit 1 when more than N requirements lack a verification method or item (for CI)")
    md = sub.add_parser("make-datasets", help="write the fourteen test datasets (F1-F14) a requirements screen must pass")
    md.add_argument("dir")
    md.add_argument("--only", help="comma-separated ids, e.g. F1,F6,F12")
    md.add_argument("--size", type=int, default=50_000, help="requirements in the large dataset F9 (default 50000)")
    w = sub.add_parser("watch", help="re-ingest a folder of exports when they change (never writes to that folder)")
    w.add_argument("dir")
    w.add_argument("--out", required=True, help="where results go (must be OUTSIDE the watched folder)")
    w.add_argument("--rules", help="YAML: rules: [{match: '*.xlsx', profile: p.yaml, adapter: tabular, options: {sheet: X}, namespace: KEY}]")
    w.add_argument("--state-dir", help="default: <out>/.reqin-watch")
    w.add_argument("--settle", type=float, default=10.0, help="seconds a file must be quiet before it is read")
    w.add_argument("--interval", type=float, default=60.0)
    w.add_argument("--once", action="store_true", help="one pass, then exit (for cron / CI); exit code 1 if any file failed")
    w.add_argument("--recursive", action="store_true")
    w.add_argument("--include", action="append", help="glob of files to pick up when no rules are given (default: csv xlsx reqif reqifz sysml)")
    a = ap.parse_args(argv)
    if a.cmd == "connectors":
        return _cmd_connectors()
    if a.cmd == "check-dataset":
        return _cmd_check_dataset(a)
    if a.cmd == "make-datasets":
        return _cmd_make_datasets(a)
    if a.cmd == "vee":
        return _cmd_vee(a)
    if a.cmd == "watch":
        return _cmd_watch(a)
    if a.cmd == "sample":
        return _cmd_sample(a)
    src = _src(a)
    if a.cmd == "sniff":
        for score, name in sniff_all(src):
            print(f"{score:.2f}  {name}")
        return 0
    ad = load_adapters()[a.adapter]() if getattr(a, "adapter", None) else pick_adapter(src)
    try:
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
            if a.out_dir:
                from .dataset import DatasetError, validate_dataset, write_dataset
                try:
                    folder = write_dataset(res, a.out_dir)
                except DatasetError as e:
                    print(f"dataset not written: {e}", file=sys.stderr)
                    return 2
                problems = validate_dataset(folder)
                print(f"dataset written to {folder}: {len(res.requirements)} requirements, {len(res.links)} links, {len(res.rejected)} rejected; "
                      + ("it follows the contract." if not problems else f"IT DOES NOT FOLLOW THE CONTRACT ({len(problems)} problem(s)):"), file=sys.stderr)
                for x in problems[:20]:
                    print("  -", x, file=sys.stderr)
                if problems:
                    _write_audit(ad, getattr(a, "audit", None))
                    return 1
    except ConnectError as e:
        print(f"connector error: {e}", file=sys.stderr)
        _write_audit(ad, getattr(a, "audit", None))
        return 1
    _write_audit(ad, getattr(a, "audit", None))
    return 0


if __name__ == "__main__":
    sys.exit(main())
