"""The canonical dataset on disk: the ONE thing the GUI reads (see GUI_CONTRACT.md).

A dataset is a folder:

    requirements.jsonl   one requirement per line
    links.jsonl          one link per line
    rejected.jsonl       one rejected record per line, each with a reason
    report.json          counts, coverage, confidence and warnings
    dataset.json         manifest, written LAST: contract version, counts, size and sha256 of every file

`write_dataset` produces it from an import, `validate_dataset` says whether a folder follows the contract (and what is wrong if
not), `describe` summarises what a screen has to cope with. Nothing here knows about any source format.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from .model import IngestResult

CONTRACT = "reqin-dataset"
VERSION = 1
FILES = {"requirements": "requirements.jsonl", "links": "links.jsonl", "rejected": "rejected.jsonl", "report": "report.json"}
MANIFEST = "dataset.json"

FIDELITIES = ("structured", "tabular", "parsed", "extracted")
CONFS = ("Exact", "High", "Medium", "Low")
MODALS = ("", "shall", "should", "will", "may", "must")
REQ_KEYS = ("mid", "uid", "uid_synthetic", "text", "norm_text", "fingerprint", "slots", "fields", "extra", "conf", "ref", "fidelity", "parent_mid")
LINK_KEYS = ("source_uid", "target_uid", "kind", "source_mid", "target_mid", "ref")
REJECTED_KEYS = ("ref", "reason", "fields")
REF_KEYS = ("adapter", "uri", "container", "locator", "revision")
REPORT_KEYS = ("adapter", "fidelity", "profile", "profile_proposed", "revision", "raw_records", "requirements", "rejected", "filtered_out",
               "links", "coverage", "confidence", "unclaimed_fields", "warnings", "invariant_ok")


class DatasetError(RuntimeError):
    pass


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def plain(obj: Any) -> Any:
    """Round-trip through JSON so enums and dataclass leftovers become what a file reader would see."""
    return json.loads(_dump(obj))


# ---- what the report must be consistent with ------------------------------------------------------------------
def summarise(requirements: Iterable[dict]) -> dict[str, Any]:
    """coverage and confidence, recomputed from the records themselves (the same rules the importer follows)."""
    coverage: Counter[str] = Counter()
    confidence: defaultdict[str, Counter[str]] = defaultdict(Counter)
    for r in requirements:
        coverage["text"] += 1
        if not r["uid_synthetic"]:
            coverage["uid"] += 1
        for k in r["fields"]:
            coverage[k] += 1
        for k, c in r["conf"].items():
            confidence[k][c] += 1
    return {"coverage": dict(coverage), "confidence": {k: dict(v) for k, v in confidence.items()}}


def depths(requirements: list[dict]) -> dict[str, int]:
    """Depth of every requirement in the hierarchy (a root is 1). Iterative, so 100,000 deep chains do not overflow."""
    parent = {r["mid"]: r.get("parent_mid") for r in requirements}
    depth: dict[str, int] = {}
    for mid in parent:
        chain, cur = [], mid
        while cur is not None and cur in parent and cur not in depth and len(chain) <= len(parent):
            chain.append(cur)
            cur = parent[cur]
        base = depth.get(cur, 0) if cur is not None else 0
        for m in reversed(chain):
            base += 1
            depth[m] = base
    return depth


# ---- the contract, as checks -----------------------------------------------------------------------------------
def check_records(requirements: list[Any], links: list[Any], rejected: list[Any], report: Any) -> list[str]:
    """Every way a dataset can break the contract, as sentences a person can act on. Empty list = valid."""
    problems: list[str] = []

    def bad(where: str, msg: str) -> None:
        problems.append(f"{where}: {msg}")

    def is_int(v: Any) -> bool:
        return isinstance(v, int) and not isinstance(v, bool)

    def check_ref(where: str, ref: Any, need_locator: bool = True) -> None:
        if not isinstance(ref, dict):
            return bad(where, "ref is missing or not an object")
        for k in REF_KEYS:
            if not isinstance(ref.get(k), str):
                bad(where, f"ref.{k} is missing or not text")
        if need_locator and not str(ref.get("locator", "")).strip():
            bad(where, "ref.locator is empty: a person must be able to jump back to the source")
        if not str(ref.get("adapter", "")).strip() or not str(ref.get("uri", "")).strip():
            bad(where, "ref.adapter and ref.uri must say where this came from")

    mids: dict[str, int] = {}
    uid_count: Counter[str] = Counter()
    good_reqs: list[dict] = []
    for i, r in enumerate(requirements, 1):
        w = f"requirements.jsonl:{i}"
        if not isinstance(r, dict):
            bad(w, "not an object")
            continue
        missing = [k for k in REQ_KEYS if k not in r]
        if missing:
            bad(w, f"missing {', '.join(missing)}")
            continue
        ok = True
        if not isinstance(r["mid"], str) or not r["mid"]:
            bad(w, "mid must be non-empty text"); ok = False
        elif r["mid"] in mids:
            bad(w, f"mid {r['mid']} is already used by line {mids[r['mid']]}: the screen uses mid as the key, so records would overwrite each other")
        else:
            mids[r["mid"]] = i
        if not isinstance(r["uid"], str) or not r["uid"].strip():
            bad(w, "uid must be non-empty text (an invented one is allowed, with uid_synthetic true)"); ok = False
        else:
            uid_count[r["uid"]] += 1
        if not isinstance(r["uid_synthetic"], bool):
            bad(w, "uid_synthetic must be true or false"); ok = False
        if not isinstance(r["text"], str) or not r["text"].strip():
            bad(w, "text must be a non-empty statement"); ok = False
        for k in ("norm_text", "fingerprint"):
            if not isinstance(r[k], str):
                bad(w, f"{k} must be text"); ok = False
        sl = r["slots"]
        if not isinstance(sl, dict) or sl.get("modal") not in MODALS or not isinstance(sl.get("negated"), bool) or not isinstance(sl.get("quantities"), list):
            bad(w, "slots needs modal (shall, should, will, may, must or empty), negated (true or false) and quantities (a list)"); ok = False
        for k in ("fields", "extra"):
            if not isinstance(r[k], dict):
                bad(w, f"{k} must be an object"); ok = False
        if isinstance(r["fields"], dict) and any(v is None or isinstance(v, (dict, list)) for v in r["fields"].values()):
            bad(w, "fields values must be plain text or numbers (a missing field is left out, not null)")
        c = r["conf"]
        if not isinstance(c, dict) or "text" not in c or "uid" not in c or any(v not in CONFS for v in c.values()):
            bad(w, f"conf needs at least text and uid, each one of {', '.join(CONFS)}"); ok = False
        if r["fidelity"] not in FIDELITIES:
            bad(w, f"fidelity must be one of {', '.join(FIDELITIES)}"); ok = False
        check_ref(w, r["ref"])
        if r["parent_mid"] is not None and not isinstance(r["parent_mid"], str):
            bad(w, "parent_mid must be text or null"); ok = False
        if ok:
            good_reqs.append(r)

    uid_of = {r["mid"]: r["uid"] for r in good_reqs}
    for i, r in enumerate(requirements, 1):
        if isinstance(r, dict) and isinstance(r.get("parent_mid"), str):
            p = r["parent_mid"]
            if p == r.get("mid"):
                bad(f"requirements.jsonl:{i}", "a requirement cannot be its own parent")
            elif p not in mids:
                bad(f"requirements.jsonl:{i}", f"parent_mid {p} is not a requirement in this dataset (use null when the parent is outside the import)")
    if not any("parent" in p for p in problems):
        # cycles: follow each chain once
        parent = {r["mid"]: r["parent_mid"] for r in good_reqs}
        state: dict[str, int] = {}
        for start in parent:
            chain, cur = [], start
            while cur is not None and cur in parent and state.get(cur, 0) == 0:
                state[cur] = 1
                chain.append(cur)
                cur = parent[cur]
            if cur is not None and state.get(cur) == 1:
                bad("requirements.jsonl", f"the hierarchy loops back on itself at mid {cur}")
                break
            for m in chain:
                state[m] = 2

    for i, l in enumerate(links, 1):
        w = f"links.jsonl:{i}"
        if not isinstance(l, dict) or any(k not in l for k in LINK_KEYS):
            bad(w, f"needs {', '.join(LINK_KEYS)}")
            continue
        if not isinstance(l["kind"], str) or not l["kind"].strip():
            bad(w, "kind must be non-empty text (any kind is allowed, the screen shows it as written)")
        for end in ("source", "target"):
            uid, mid = l[f"{end}_uid"], l[f"{end}_mid"]
            if not isinstance(uid, str) or not uid.strip():
                bad(w, f"{end}_uid must be non-empty text")
            if mid is not None:
                if mid not in mids:
                    bad(w, f"{end}_mid {mid} is not a requirement in this dataset (use null when that end is outside the import)")
                elif uid_of.get(mid) is not None and uid_of[mid] != uid:
                    bad(w, f"{end}_uid {uid!r} disagrees with the uid of {end}_mid ({uid_of[mid]!r})")
        check_ref(w, l["ref"], need_locator=False)

    for i, x in enumerate(rejected, 1):
        w = f"rejected.jsonl:{i}"
        if not isinstance(x, dict) or any(k not in x for k in REJECTED_KEYS):
            bad(w, f"needs {', '.join(REJECTED_KEYS)}")
            continue
        if not isinstance(x["reason"], str) or not x["reason"].strip():
            bad(w, "every rejected record needs a reason a person can read")
        if not isinstance(x["fields"], dict):
            bad(w, "fields must be an object")
        check_ref(w, x["ref"])

    w = "report.json"
    if not isinstance(report, dict):
        bad(w, "not an object")
        return problems
    missing = [k for k in REPORT_KEYS if k not in report]
    if missing:
        bad(w, f"missing {', '.join(missing)}")
        return problems
    if report["fidelity"] not in FIDELITIES + ("mixed",):
        bad(w, f"fidelity must be one of {', '.join(FIDELITIES)} (or mixed)")
    for k in ("adapter", "profile", "revision"):
        if not isinstance(report[k], str):
            bad(w, f"{k} must be text")
    if not isinstance(report["profile_proposed"], bool):
        bad(w, "profile_proposed must be true or false")
    for k in ("raw_records", "requirements", "rejected", "links"):
        if not is_int(report[k]):
            bad(w, f"{k} must be a whole number")
    if not isinstance(report["filtered_out"], dict) or not all(is_int(v) and v >= 0 for v in report["filtered_out"].values()):
        bad(w, "filtered_out must map each reason to a count")
        return problems
    if not isinstance(report["warnings"], list) or not all(isinstance(x, str) for x in report["warnings"]):
        bad(w, "warnings must be a list of sentences")
        return problems
    if not isinstance(report["unclaimed_fields"], list):
        bad(w, "unclaimed_fields must be a list")
    if not all(is_int(report[k]) for k in ("raw_records", "requirements", "rejected", "links")):
        return problems
    for k, n in (("requirements", len(requirements)), ("rejected", len(rejected)), ("links", len(links))):
        if report[k] != n:
            bad(w, f"says {k} = {report[k]} but the file has {n}")
    filtered = sum(report["filtered_out"].values())
    if report["raw_records"] != report["requirements"] + report["rejected"] + filtered:
        bad(w, f"raw_records ({report['raw_records']}) is not requirements ({report['requirements']}) + rejected ({report['rejected']}) + filtered ({filtered}): "
               "records went missing, or were counted twice")
    if report["invariant_ok"] is not True:
        bad(w, "invariant_ok is not true: the importer itself says records went missing. Do not show this dataset as complete")
    if len(good_reqs) == len(requirements):
        s = summarise(good_reqs)
        if report["coverage"] != s["coverage"]:
            bad(w, f"coverage {report['coverage']} does not match the records {s['coverage']}")
        if report["confidence"] != s["confidence"]:
            bad(w, "confidence counts do not match the records")
    dups = sorted(u for u, n in uid_count.items() if n > 1)
    if dups and not any("duplicate" in x.lower() for x in report["warnings"]):
        bad(w, f"{len(dups)} uids are used more than once (for example {dups[0]!r}) but no warning says so; nothing may be silent")
    if not requirements and not report["warnings"] and not report["raw_records"]:
        bad(w, "an empty dataset needs a warning that says why, so the screen can show it instead of a blank grid")
    return problems


# ---- writing ---------------------------------------------------------------------------------------------------
def _atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _jsonl(rows: Iterable[Any]) -> bytes:
    return "".join(_dump(r) + "\n" for r in rows).encode("utf-8")


def write_dataset_dicts(requirements: list[dict], links: list[dict], rejected: list[dict], report: dict, out_dir: str | Path) -> Path:
    out = Path(out_dir)
    if out.exists():
        if not out.is_dir():
            raise DatasetError(f"{out} exists and is not a folder")
        stray = sorted(p.name for p in out.iterdir() if p.name not in set(FILES.values()) | {MANIFEST} and not p.name.endswith(".tmp"))
        if stray:
            raise DatasetError(f"{out} already holds other files ({', '.join(stray[:5])}). Pick an empty folder or an old dataset folder; "
                               "nothing unrelated is ever overwritten or removed.")
    out.mkdir(parents=True, exist_ok=True)
    blobs = {FILES["requirements"]: _jsonl(requirements), FILES["links"]: _jsonl(links), FILES["rejected"]: _jsonl(rejected),
             FILES["report"]: (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=1, default=str) + "\n").encode("utf-8")}
    entries = {}
    for name, data in blobs.items():
        _atomic(out / name, data)
        entries[name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "lines": data.count(b"\n")}
    sources = sorted({(x["ref"]["adapter"], x["ref"]["uri"]) for x in [*requirements, *rejected] if isinstance(x.get("ref"), dict)})
    manifest = {"contract": CONTRACT, "version": VERSION,
                "counts": {"requirements": len(requirements), "links": len(links), "rejected": len(rejected)},
                "files": entries, "sources": [{"adapter": a, "uri": u} for a, u in sources]}
    _atomic(out / MANIFEST, (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=1) + "\n").encode("utf-8"))   # last: its presence means "complete"
    return out


def write_dataset(res: IngestResult, out_dir: str | Path) -> Path:
    """Write an import's result as a dataset folder. Deterministic: the same import gives byte-identical files."""
    return write_dataset_dicts([plain(asdict(q)) for q in res.requirements], [plain(asdict(l)) for l in res.links],
                               [plain(asdict(x)) for x in res.rejected], plain(res.report), out_dir)


def validate_result(res: IngestResult) -> list[str]:
    """The contract check on an in-memory import (used by the connector conformance helper)."""
    return check_records([plain(asdict(q)) for q in res.requirements], [plain(asdict(l)) for l in res.links],
                         [plain(asdict(x)) for x in res.rejected], plain(res.report))


# ---- reading ---------------------------------------------------------------------------------------------------
def _read_jsonl(path: Path, problems: list[str]) -> list[Any]:
    rows: list[Any] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        problems.append(f"{path.name}: cannot be read ({e})")
        return rows
    for n, line in enumerate(text.split("\n"), 1):
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            problems.append(f"{path.name}:{n}: not valid JSON")
    return rows


def load_dataset(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    """Read a dataset folder into plain dicts, returning (dataset, problems found while reading and checking the files)."""
    root = Path(path)
    problems: list[str] = []
    ds: dict[str, Any] = {"requirements": [], "links": [], "rejected": [], "report": None, "manifest": None}
    if not root.is_dir():
        return ds, [f"{root} is not a folder"]
    mp = root / MANIFEST
    if not mp.exists():
        problems.append(f"{MANIFEST} is missing: the folder is not a dataset, or the write was interrupted before it finished")
    else:
        try:
            ds["manifest"] = json.loads(mp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            problems.append(f"{MANIFEST} is not valid JSON")
    man = ds["manifest"]
    if isinstance(man, dict):
        if man.get("contract") != CONTRACT:
            problems.append(f"{MANIFEST}: this is not a {CONTRACT} manifest")
        elif man.get("version") != VERSION:
            problems.append(f"{MANIFEST}: contract version {man.get('version')} but this checker knows version {VERSION}")
    for key in ("requirements", "links", "rejected"):
        p = root / FILES[key]
        if not p.exists():
            problems.append(f"{FILES[key]} is missing")
        else:
            ds[key] = _read_jsonl(p, problems)
    rp = root / FILES["report"]
    if not rp.exists():
        problems.append(f"{FILES['report']} is missing")
    else:
        try:
            ds["report"] = json.loads(rp.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            problems.append(f"{FILES['report']} is not valid JSON")
    if isinstance(man, dict) and isinstance(man.get("files"), dict):
        for name, meta in man["files"].items():
            p = root / name
            if p.exists() and isinstance(meta, dict):
                data = p.read_bytes()
                if hashlib.sha256(data).hexdigest() != meta.get("sha256"):
                    problems.append(f"{name}: changed or cut short since it was written (the checksum in {MANIFEST} no longer matches)")
        counts = man.get("counts", {})
        for key in ("requirements", "links", "rejected"):
            if isinstance(counts, dict) and counts.get(key) != len(ds[key]):
                problems.append(f"{MANIFEST} says {counts.get(key)} {key} but {FILES[key]} has {len(ds[key])}")
    return ds, problems


def check_dataset(path: str | Path) -> tuple[dict[str, Any], list[str]]:
    """Load a dataset folder and check it against the contract. Returns (dataset, problems); no problems means valid."""
    ds, problems = load_dataset(path)
    if ds["report"] is not None:
        problems += check_records(ds["requirements"], ds["links"], ds["rejected"], ds["report"])
    return ds, problems


def validate_dataset(path: str | Path) -> list[str]:
    return check_dataset(path)[1]


# ---- what a screen has to cope with ----------------------------------------------------------------------------
def describe(ds: dict[str, Any]) -> dict[str, Any]:
    """Machine-checkable facts about a dataset: what the screen should be showing. GUI tests compare the screen to this."""
    reqs, links, rejected, rep = ds["requirements"], ds["links"], ds["rejected"], ds["report"] or {}
    dep = depths(reqs)
    field_keys = sorted({k for r in reqs for k in r["fields"]})
    return {
        "raw_records": rep.get("raw_records", len(reqs) + len(rejected)),
        "requirements": len(reqs),
        "rejected": len(rejected),
        "filtered": sum((rep.get("filtered_out") or {}).values()),
        "links": len(links),
        "hierarchy": any(r.get("parent_mid") for r in reqs),
        "max_depth": max(dep.values(), default=0),
        "link_kinds": sorted({l["kind"] for l in links}),
        "links_with_an_end_outside_the_import": sum(1 for l in links if l["source_mid"] is None or l["target_mid"] is None),
        "synthetic_uids": sum(1 for r in reqs if r["uid_synthetic"]),
        "duplicate_uids": sum(1 for n in Counter(r["uid"] for r in reqs).values() if n > 1),
        "fidelities": sorted({r["fidelity"] for r in reqs}),
        "sources": sorted({r["ref"]["uri"] for r in reqs}),
        "fields_present": field_keys,
        "extra_keys": len({k for r in reqs for k in r["extra"]}),
        "fields_below_high_confidence": sum(1 for r in reqs for k, c in r["conf"].items() if c in ("Medium", "Low")),
        "warnings": len(rep.get("warnings") or []),
    }
