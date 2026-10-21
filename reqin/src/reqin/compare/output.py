"""Reading a dataset, running the engine on it, writing the `reqin-compare/1` folder (docs/COMPARE_FORMAT.md), and checking such a folder.

Writing is atomic and last-file-last, like a dataset: `compare.json` is written after the others, so a folder without it is an unfinished write. The same dataset and vocabulary give
byte-identical files. Nothing unrelated is ever overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from ..dataset import MANIFEST as DATASET_MANIFEST
from ..dataset import check_dataset
from .engine import Result, Settings, compare
from .rules import RULES, TYPES
from .vocabulary import Vocabulary
from .vocabulary import load as load_vocabulary

FORMAT = "reqin-compare/1"
FILES = {"clusters": "clusters.jsonl", "pairs": "pairs.jsonl", "slots": "slots.jsonl"}
SUMMARY = "compare.json"
BASES = ("slot", "words_differ", "subject")
RUNGS = ("exact", "masked", "canonical", "overlap")


class CompareError(RuntimeError):
    pass


def _line(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def run_dataset(dataset_dirs: str | Path | list[str | Path], vocab: Vocabulary | None = None, settings: Settings | None = None) -> tuple[Result, list[dict[str, Any]]]:
    """Check each dataset against the contract, then compare all their requirements together (two imports of the same spec are the usual reason to give more than one).
    Returns the result and, for each dataset, the SHA-256 of its manifest and its size. A dataset that fails its check is refused, and so is a set of datasets that share an internal key."""
    dirs = [dataset_dirs] if isinstance(dataset_dirs, (str, Path)) else list(dataset_dirs)
    if not dirs:
        raise CompareError("no dataset was given")
    reqs: list[dict[str, Any]] = []
    seen: dict[str, str] = {}
    info: list[dict[str, Any]] = []
    for d in dirs:
        ds, problems = check_dataset(d)
        if problems:
            raise CompareError(f"{d} does not follow the contract, so nothing was compared:\n  " + "\n  ".join(problems[:10]))
        for r in ds["requirements"]:
            if r["mid"] in seen:
                raise CompareError(f"{d} and {seen[r['mid']]} both contain the internal key {r['mid']}: they are not two different imports")
            seen[r["mid"]] = str(d)
        reqs += ds["requirements"]
        info.append({"manifest_sha256": hashlib.sha256((Path(d) / DATASET_MANIFEST).read_bytes()).hexdigest(), "requirements": len(ds["requirements"])})
    return compare(reqs, vocab, settings), info


def write(res: Result, out_dir: str | Path, datasets: list[dict[str, Any]]) -> Path:
    out = Path(out_dir)
    known = set(FILES.values()) | {SUMMARY}
    if out.exists():
        if not out.is_dir():
            raise CompareError(f"{out} exists and is not a folder")
        stray = sorted(p.name for p in out.iterdir() if p.name not in known and not p.name.endswith(".tmp"))
        if stray:
            raise CompareError(f"{out} already holds other files ({', '.join(stray[:5])}). Pick an empty folder or an earlier output folder; nothing unrelated is overwritten.")
    out.mkdir(parents=True, exist_ok=True)
    blobs = {
        FILES["clusters"]: "".join(_line(c) + "\n" for c in res.clusters).encode("utf-8"),
        FILES["pairs"]: "".join(_line(p) + "\n" for p in res.pairs).encode("utf-8"),
        FILES["slots"]: "".join(_line(s.to_json()) + "\n" for s in res.slots).encode("utf-8"),
    }
    entries = {}
    for name, data in blobs.items():
        _atomic(out / name, data)
        entries[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "lines": data.count(b"\n")}
    summary = {"format": FORMAT, "status": "draft", "provenance": "mechanical", "engine": res.summary["engine"],
               "datasets": datasets,
               "settings": res.summary["settings"], "counts": res.summary["counts"], "limits": res.summary["limits"], "notes": res.summary["notes"], "files": entries}
    _atomic(out / SUMMARY, (json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))      # last: its presence means "complete"
    return out


def _read(path: Path, problems: list[str]) -> list[Any]:
    rows: list[Any] = []
    if not path.exists():
        problems.append(f"{path.name} is missing")
        return rows
    for n, raw in enumerate(path.read_text(encoding="utf-8").split("\n")[:-1], 1):
        try:
            rows.append(json.loads(raw))
        except ValueError:
            problems.append(f"{path.name} line {n} is not JSON")
    return rows


def _span_ok(x: Any, limit: int | None = None) -> bool:
    return x is None or (isinstance(x, list) and len(x) == 2 and all(isinstance(i, int) and not isinstance(i, bool) and i >= 0 for i in x) and x[0] <= x[1] and (limit is None or x[1] <= limit))


def check(out_dir: str | Path, dataset_dirs: str | Path | list[str | Path] | None = None) -> list[str]:
    """Does this folder follow docs/COMPARE_FORMAT.md? With the dataset it was made from, also: does it name that dataset, and are the ids and positions real?"""
    root = Path(out_dir)
    problems: list[str] = []
    if not root.is_dir():
        return [f"{root} is not a folder"]
    sp = root / SUMMARY
    if not sp.exists():
        return [f"{SUMMARY} is missing: the folder is not a comparison output, or the write was interrupted before it finished"]
    try:
        man = json.loads(sp.read_text(encoding="utf-8"))
    except ValueError:
        return [f"{SUMMARY} is not valid JSON"]
    if man.get("format") != FORMAT:
        problems.append(f"{SUMMARY}: format is {man.get('format')!r}, expected {FORMAT!r}")
    if man.get("status") != "draft" or man.get("provenance") != "mechanical":
        problems.append(f"{SUMMARY}: everything the engine writes is a draft with provenance mechanical")
    files = man.get("files") if isinstance(man.get("files"), dict) else {}
    for name in FILES.values():
        p = root / name
        meta = files.get(name)
        if not isinstance(meta, dict):
            problems.append(f"{SUMMARY} does not list {name}")
        elif p.exists():
            data = p.read_bytes()
            if hashlib.sha256(data).hexdigest() != meta.get("sha256") or len(data) != meta.get("bytes"):
                problems.append(f"{name}: changed or cut short since it was written (the checksum in {SUMMARY} no longer matches)")
    clusters, pairs, slots = (_read(root / FILES[k], problems) for k in ("clusters", "pairs", "slots"))
    cids = set()
    pids = set()
    mids_seen: set[str] = set()
    slot_len: dict[str, int] = {}
    for i, s in enumerate(slots, 1):
        if not isinstance(s, dict) or not isinstance(s.get("mid"), str):
            problems.append(f"slots line {i}: no mid")
            continue
        if s["mid"] in mids_seen:
            problems.append(f"slots line {i}: {s['mid']} appears twice")
        mids_seen.add(s["mid"])
        for q in s.get("quantities", []):
            if not _span_ok(q.get("span")) or q.get("role") not in ("main", "condition"):
                problems.append(f"slots line {i}: a quantity with a bad span or role")
        for key in ("subject", "modal"):
            if not _span_ok((s.get(key) or {}).get("span")):
                problems.append(f"slots line {i}: {key} has a bad span")
    for i, c in enumerate(clusters, 1):
        w = f"clusters line {i}"
        if not isinstance(c, dict):
            problems.append(f"{w}: not an object")
            continue
        if c.get("cid") in cids:
            problems.append(f"{w}: {c.get('cid')} appears twice")
        cids.add(c.get("cid"))
        mem = [m.get("mid") for m in c.get("members", []) if isinstance(m, dict)]
        if len(mem) < 2:
            problems.append(f"{w}: a cluster has at least two members")
        if c.get("representative") not in mem:
            problems.append(f"{w}: the representative is not a member")
        if c.get("valid") is not True:
            problems.append(f"{w}: valid is not true; a cluster that fails the all-pairs check must not be written")
        if c.get("status") != "draft" or c.get("provenance") != "mechanical":
            problems.append(f"{w}: status and provenance must be draft and mechanical")
        if c.get("rung") not in RUNGS[:3]:
            problems.append(f"{w}: rung must be exact, masked or canonical")
        for m in mem:
            if m not in mids_seen:
                problems.append(f"{w}: member {m} has no line in slots.jsonl")
    for i, p in enumerate(pairs, 1):
        w = f"pairs line {i}"
        if not isinstance(p, dict):
            problems.append(f"{w}: not an object")
            continue
        if p.get("pid") in pids:
            problems.append(f"{w}: {p.get('pid')} appears twice")
        pids.add(p.get("pid"))
        if p.get("type") not in TYPES or p.get("type") == "EQUIVALENT":
            problems.append(f"{w}: type {p.get('type')!r} is not one of VARIANT, SUBSUMES, CONFLICT, COMPLEMENTARY, UNRELATED (equivalent requirements are clusters)")
        if (p.get("direction") in ("a", "b")) != (p.get("type") == "SUBSUMES") or p.get("direction") not in (None, "a", "b"):
            problems.append(f"{w}: direction must be a or b for SUBSUMES and null for every other type")
        if p.get("basis") not in BASES:
            problems.append(f"{w}: basis must be one of {', '.join(BASES)}")
        if p.get("rule") not in RULES:
            problems.append(f"{w}: rule {p.get('rule')!r} is not a known rule")
        elif RULES[p["rule"]][0] != p.get("type") and p.get("rule") != "MIXED":
            problems.append(f"{w}: rule {p['rule']} decides {RULES[p['rule']][0]}, not {p.get('type')}")
        if p.get("needs_review") is not (p.get("type") in ("VARIANT", "CONFLICT")):
            problems.append(f"{w}: needs_review must be true exactly for VARIANT and CONFLICT")
        if not isinstance(p.get("score"), (int, float)) or isinstance(p.get("score"), bool) or not 0 <= p["score"] <= 1:
            problems.append(f"{w}: score must be a number from 0 to 1")
        if p.get("rung") not in RUNGS:
            problems.append(f"{w}: rung must be one of {', '.join(RUNGS)}")
        ea, eb = p.get("a") or {}, p.get("b") or {}
        ma, mb = ea.get("mids") or [], eb.get("mids") or []
        if not ma or not mb or set(ma) & set(mb):
            problems.append(f"{w}: the two sides must each name requirements, and no requirement may be on both sides")
        for side, e in (("a", ea), ("b", eb)):
            if e.get("scope") not in ("group", "words"):
                problems.append(f"{w}: side {side} scope must be group or words")
            for cid in e.get("clusters", []):
                if cid not in cids:
                    problems.append(f"{w}: side {side} names cluster {cid}, which is not in clusters.jsonl")
            for m in e.get("mids", []):
                if m not in mids_seen:
                    problems.append(f"{w}: {m} has no line in slots.jsonl")
        for x in p.get("why", []):
            if not (isinstance(x, dict) and _span_ok(x.get("a_span")) and _span_ok(x.get("b_span"))):
                problems.append(f"{w}: a reason with a bad span")
    for i, c in enumerate(clusters, 1):
        for pid in (c.get("related") or []) if isinstance(c, dict) else []:
            if pid not in pids:
                problems.append(f"clusters line {i}: related names {pid}, which is not in pairs.jsonl")
    counts = man.get("counts", {})
    if counts.get("clusters") != len(clusters) or counts.get("requirements") != len(slots):
        problems.append(f"{SUMMARY} counts do not match the files")
    for t in (counts.get("pairs") or {}):
        if counts["pairs"][t] != sum(1 for p in pairs if isinstance(p, dict) and p.get("type") == t):
            problems.append(f"{SUMMARY} says {counts['pairs'][t]} {t} pairs but pairs.jsonl has a different number")
    if dataset_dirs is not None:
        dirs = [dataset_dirs] if isinstance(dataset_dirs, (str, Path)) else list(dataset_dirs)
        recorded = man.get("datasets") if isinstance(man.get("datasets"), list) else []
        if len(recorded) != len(dirs):
            problems.append(f"the output was made from {len(recorded)} dataset(s) and {len(dirs)} were given")
        req: dict[str, Any] = {}
        for k, d in enumerate(dirs):
            dm = Path(d) / DATASET_MANIFEST
            if not dm.exists():
                problems.append(f"{d} has no {DATASET_MANIFEST}")
                continue
            sha = hashlib.sha256(dm.read_bytes()).hexdigest()
            if sha not in [x.get("manifest_sha256") for x in recorded if isinstance(x, dict)]:
                problems.append(f"{d} is not one of the datasets this was made from, or has changed since (its manifest does not match any recorded)")
            ds, dprob = check_dataset(d)
            if dprob:
                problems.append(f"{d} no longer follows the contract ({dprob[0]}), so it cannot be what this output was made from")
            else:
                req.update({r["mid"]: r for r in ds["requirements"]})
        if req and set(req) != mids_seen:
            problems.append("the requirements in slots.jsonl are not the requirements of the dataset(s)")
        for i, s_ in enumerate(slots, 1):
            r = req.get(s_.get("mid"))
            if r is None:
                continue
            for q in s_.get("quantities", []):
                if not _span_ok(q.get("span"), len(r["norm_text"])):
                    problems.append(f"slots line {i}: a quantity span runs past the end of the text")
    return problems
