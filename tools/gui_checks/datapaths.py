"""Every field path that really occurs in what reqin writes, found by running reqin.

docs/SCREEN_DATA_MAP.md names fields like `DS.fields.allocation` or `CL.members[].uid`. This module makes those names checkable: it generates the
fourteen test datasets, runs the comparison engine and the V report on them, and collects every key path that occurs in any line of any file.

The prefixes:  DS requirements.jsonl   LK links.jsonl   RJ rejected.jsonl   RPT report.json   MAN dataset.json
               CL clusters.jsonl   PR pairs.jsonl   SL slots.jsonl   CMP compare.json   VEE `reqin vee --json`
A list is written `[]` and its items are walked; a dict contributes its own path and the path of everything inside it.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path

PREFIXES = ("DS", "LK", "RJ", "RPT", "MAN", "CL", "PR", "SL", "CMP", "VEE")


def walk(obj, prefix: str):
    """Yield the path of obj and of everything inside it."""
    yield prefix
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, f"{prefix}.{k}")
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, prefix + "[]")


def _run(main, argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        rc = main(argv)
    return rc, out.getvalue()


def _jsonl(path: Path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            yield json.loads(line)


def generate(work: Path, size: int = 300) -> dict:
    """Write the fourteen datasets, compare and vee each; return {dataset id: {'folders': [...], 'compare': Path|None, 'vee': dict|None}}."""
    from reqin.cli import main

    rc, text = _run(main, ["make-datasets", str(work / "ds"), "--size", str(size)])
    if rc != 0:
        raise RuntimeError("make-datasets failed: " + text)
    index = json.loads((work / "ds" / "index.json").read_text(encoding="utf-8"))
    result = {}
    for d in index["datasets"]:
        folders = [work / "ds" / f for f in d["folders"]]
        cmp_dir = work / "cmp" / d["id"]
        rc, text = _run(main, ["compare", *map(str, folders), "--out-dir", str(cmp_dir)])
        vee = None
        if len(folders) == 1:
            rc2, text2 = _run(main, ["vee", str(folders[0]), "--json"])
            if rc2 == 0:
                vee = json.loads(text2)
        result[d["id"]] = {"folders": folders, "compare": cmp_dir if rc == 0 else None, "vee": vee, "expect": d["expect"]}
    return result


def collect(generated: dict) -> dict[str, set[str]]:
    """{prefix: set of paths} over every dataset that was generated."""
    seen: dict[str, set[str]] = {p: set() for p in PREFIXES}
    for g in generated.values():
        for folder in g["folders"]:
            for rec in _jsonl(folder / "requirements.jsonl"):
                seen["DS"].update(walk(rec, "DS"))
            for rec in _jsonl(folder / "links.jsonl"):
                seen["LK"].update(walk(rec, "LK"))
            for rec in _jsonl(folder / "rejected.jsonl"):
                seen["RJ"].update(walk(rec, "RJ"))
            seen["RPT"].update(walk(json.loads((folder / "report.json").read_text(encoding="utf-8")), "RPT"))
            seen["MAN"].update(walk(json.loads((folder / "dataset.json").read_text(encoding="utf-8")), "MAN"))
        c = g["compare"]
        if c is not None:
            for name, pre in (("clusters.jsonl", "CL"), ("pairs.jsonl", "PR"), ("slots.jsonl", "SL")):
                for rec in _jsonl(c / name):
                    seen[pre].update(walk(rec, pre))
            seen["CMP"].update(walk(json.loads((c / "compare.json").read_text(encoding="utf-8")), "CMP"))
        if g["vee"] is not None:
            seen["VEE"].update(walk(g["vee"], "VEE"))
    return seen


def main(argv=None) -> int:
    import argparse
    import sys
    import tempfile

    ap = argparse.ArgumentParser(description="Print every field path that reqin really writes (for writing docs/SCREEN_DATA_MAP.md), or write them as JSON for the checkers.")
    ap.add_argument("--json", metavar="FILE", help="write {prefix: [paths]} here instead of printing")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "reqin" / "src"))
    with tempfile.TemporaryDirectory() as t:
        found = collect(generate(Path(t)))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({pre: sorted(found[pre]) for pre in PREFIXES}, f, indent=1)
            f.write("\n")
        print("wrote", a.json, "-", sum(len(v) for v in found.values()), "paths")
    else:
        for pre in PREFIXES:
            print("##", pre)
            for p in sorted(found[pre]):
                print(p)
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
