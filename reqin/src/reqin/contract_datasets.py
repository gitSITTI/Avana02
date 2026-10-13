"""The fourteen test datasets a requirements screen must pass (GUI_CONTRACT.md section 6).

    reqin make-datasets OUT_DIR [--only F3,F9] [--size 50000]

Each is a complete, valid canonical dataset (see dataset.py) that removes ONE assumption a screen might have picked up from a single
sample file. They are synthetic and fictional, built directly in the canonical shape (no importer is involved), and deterministic:
the same arguments give byte-identical files on every machine. `index.json` lists them with machine-checkable expectations, so a
browser test can compare what the screen shows with what the dataset contains.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from .dataset import describe, load_dataset, summarise, validate_dataset, write_dataset_dicts
from .model import make_mid
from .normalise import extract_slots, fingerprint, normalise_text

SUBSYSTEMS = ["power supply", "display unit", "data recorder", "cooling loop", "radio link", "navigation filter", "fault logger", "operator console"]
TEMPLATES = [
    "The {s} shall operate at an ambient temperature between -{a} °C and {b} °C.",
    "The {s} shall respond to a valid command within {n} ms.",
    "The {s} shall not exceed {n} kg.",
    "The {s} shall log every fault with a timestamp.",
    "The {s} should show a status indication within {n} seconds of power-on.",
    "The {s} shall maintain {n} percent availability over a {m} hour mission.",
    "The {s} shall consume no more than {n} W.",
    "The {s} shall store at least {n} MB of recent events.",
]
VERIFY = ["Test", "Analysis", "Inspection", "Demonstration"]
OWNERS = ["Team A", "Team B", "Team C"]
STATUS = ["Draft", "Approved", "In review"]
BASELINES = ["PDR", "CDR", "TRR"]
LINK_KINDS = ["satisfy", "derive", "verify", "refine", "contain", "trace"]


def _text(rng: random.Random) -> str:
    return rng.choice(TEMPLATES).format(s=rng.choice(SUBSYSTEMS), a=rng.choice([20, 30, 40]), b=rng.choice([50, 60, 70]),
                                        n=rng.choice([2, 5, 10, 25, 100, 250]), m=rng.choice([4, 8, 12]))


class Src:
    """Where a dataset pretends to come from."""

    def __init__(self, ns: str, adapter: str, fidelity: str, uri: str, container: str = "", revision: str = "demo-r1") -> None:
        self.ns, self.adapter, self.fidelity, self.uri, self.container, self.revision = ns, adapter, fidelity, uri, container, revision

    def ref(self, locator: str, container: str | None = None) -> dict[str, str]:
        return {"adapter": self.adapter, "uri": self.uri, "container": self.container if container is None else container,
                "locator": locator, "revision": self.revision}


def req(src: Src, uid: str, text: str, locator: str, *, native: str | None = None, parent: str | None = None, fields: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None, synthetic: bool = False, conf: dict[str, str] | None = None, fidelity: str | None = None) -> dict[str, Any]:
    text = text.strip()
    norm = normalise_text(text)
    slots = extract_slots(norm)
    fields = dict(fields or {})
    c = {"text": "High", "uid": "Low" if synthetic else "Exact", **{k: "Exact" for k in fields}}
    c.update(conf or {})
    return {"mid": make_mid(src.ns, native or uid), "uid": uid, "uid_synthetic": synthetic, "text": text, "norm_text": norm,
            "fingerprint": fingerprint(norm, slots), "slots": asdict(slots), "fields": fields, "extra": dict(extra or {}), "conf": c,
            "ref": src.ref(locator), "fidelity": fidelity or src.fidelity, "parent_mid": parent}


def link(src: Src, a: dict[str, Any] | str, b: dict[str, Any] | str, kind: str, via: str) -> dict[str, Any]:
    """a and b are requirement dicts, or a bare uid string for an end that is outside this import."""
    def end(x: dict[str, Any] | str) -> tuple[str, str | None]:
        return (x["uid"], x["mid"]) if isinstance(x, dict) else (x, None)
    (su, sm), (tu, tm) = end(a), end(b)
    return {"source_uid": su, "target_uid": tu, "kind": kind, "source_mid": sm, "target_mid": tm, "ref": src.ref(via, container="links")}


def rejected(src: Src, reason: str, locator: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"ref": src.ref(locator), "reason": reason, "fields": fields}


def report(src_adapter: str, fidelity: str, reqs: list[dict], links: list[dict], rej: list[dict], filtered: dict[str, int] | None = None, *,
           warnings: list[str] | None = None, unclaimed: list[str] | None = None, revision: str = "demo-r1") -> dict[str, Any]:
    filtered = dict(filtered or {})
    s = summarise(reqs)
    return {"adapter": src_adapter, "fidelity": fidelity, "profile": "contract-demo", "profile_proposed": False, "revision": revision,
            "raw_records": len(reqs) + len(rej) + sum(filtered.values()), "requirements": len(reqs), "rejected": len(rej),
            "filtered_out": filtered, "links": len(links), "coverage": s["coverage"], "confidence": s["confidence"],
            "unclaimed_fields": sorted(unclaimed or []), "warnings": list(warnings or []), "invariant_ok": True}


Built = dict[str, Any]


def _ds(src: Src, reqs: list[dict], links: list[dict], rej: list[dict] | None = None, filtered: dict[str, int] | None = None, *,
        warnings: list[str] | None = None, unclaimed: list[str] | None = None) -> Built:
    rej = rej or []
    return {"requirements": reqs, "links": links, "rejected": rej,
            "report": report(src.adapter, src.fidelity, reqs, links, rej, filtered, warnings=warnings, unclaimed=unclaimed, revision=src.revision)}


def full_fields(rng: random.Random, i: int) -> dict[str, str]:
    f = {"verification": VERIFY[i % 4], "rationale": f"Needed so that operators can rely on the unit (reason {i}).", "allocation": SUBSYSTEMS[i % len(SUBSYSTEMS)],
         "owner": OWNERS[i % 3], "baseline": BASELINES[i % 3], "status": STATUS[i % 3]}
    if i % 4 == 0:
        del f["rationale"]
    if i % 5 == 0:
        del f["owner"]
    return f


# ------------------------------------------------------------------------------------------------------ F1 to F14
def f01(size: int) -> Built:
    s, rng = Src("F01", "tabular", "tabular", "minimal.csv", "minimal"), random.Random(1)
    return _ds(s, [req(s, f"MIN-{i:03d}", _text(rng), f"minimal!R{i + 1}") for i in range(1, 6)], [])


def f02(size: int) -> Built:
    s, rng = Src("F02", "reqif", "structured", "everything.reqif", "Spec"), random.Random(2)
    reqs: list[dict] = []
    links: list[dict] = []
    n = [0]

    def add(parent: dict | None) -> dict:
        n[0] += 1
        i = n[0]
        extra = {f"Custom attribute {k}": f"value {i}-{k}" for k in range(1, 11)}
        r = req(s, f"SYS-{i:04d}", _text(rng), f"SO-{i:04d}", parent=parent["mid"] if parent else None, fields=full_fields(rng, i), extra=extra)
        reqs.append(r)
        if parent:
            links.append(link(s, r, parent, "derive", f"SR-{i}a"))
            links.append(link(s, parent, r, "contain", f"SR-{i}b"))
        return r

    root = add(None)
    level2 = [add(root) for _ in range(3)]
    level3 = [add(p) for p in level2 for _ in range(3)]
    level4 = [add(p) for p in level3 for _ in range(2)]
    for i, r in enumerate(level4):
        links.append(link(s, r, level3[i // 2], "satisfy", f"SR-s{i}"))
    links.append(link(s, "TC-101", level4[0], "verify", "SR-v1"))             # a test that lives outside this import
    links.append(link(s, "TC-102", level4[1], "verify", "SR-v2"))
    links.append(link(s, level3[0], level3[1], "refine", "SR-r1"))
    links.append(link(s, level4[2], level4[5], "trace", "SR-t1"))
    return _ds(s, reqs, links, warnings=["2 links point outside this import (kept by UID)"])


def f03(size: int) -> Built:
    s, rng = Src("F03", "tabular", "tabular", "no_ids.xlsx", "Sheet1"), random.Random(3)
    return _ds(s, [req(s, f"F03:Sheet1:R{i + 1}", _text(rng), f"Sheet1!R{i + 1}", synthetic=True) for i in range(1, 13)], [])


def f04(size: int) -> Built:
    s, rng = Src("F04", "agility", "structured", "https://agility.example.test/Instance", "Story"), random.Random(4)
    reqs = [req(s, f"S-{1000 + i}", _text(rng), f"Story:{1000 + i}", fields={"status": STATUS[i % 3]}) for i in range(15)]
    links = [link(s, reqs[i], reqs[(i * 7 + 3) % 15], "trace", f"Dependencies:{i}") for i in range(12) if (i * 7 + 3) % 15 != i]
    return _ds(s, reqs, links)


def f05(size: int) -> Built:
    s, rng = Src("F05", "sysml_text", "parsed", "tree.sysml", "model"), random.Random(5)
    reqs: list[dict] = []
    for i in range(1, 16):                                  # a binary tree: TOP-1 is the root, depth 4
        parent = reqs[(i - 2) // 2]["mid"] if i > 1 else None
        reqs.append(req(s, f"TOP-{i}", _text(rng), f"L{3 * i}:R{i}", parent=parent))
    return _ds(s, reqs, [])


def f06(size: int) -> Built:
    s, rng = Src("F06", "pdf", "extracted", "srs_scan.pdf", "srs_scan.pdf"), random.Random(6)
    reqs = []
    for i in range(1, 15):
        synthetic = i % 4 == 0
        uid = f"F06:srs_scan.pdf:p{1 + i // 5}:blk{i}" if synthetic else f"SRS-{100 + i}"
        reqs.append(req(s, uid, _text(rng), f"p{1 + i // 5}:blk{i}", synthetic=synthetic, conf={"text": "Medium" if i % 3 else "Low"},
                        fields={"verification": VERIFY[i % 4]} if i % 2 else None))
    return _ds(s, reqs, [], warnings=["records were EXTRACTED from prose: every one needs human verification against its locator"])


def f07(size: int) -> Built:
    s, rng = Src("F07", "tabular", "tabular", "messy.csv", "messy"), random.Random(7)
    reqs = [req(s, f"MSY-{i:03d}", _text(rng), f"messy!R{i + 1}") for i in range(1, 11)]
    reqs.append(req(s, "MSY-003", _text(rng), "messy!R12", native="MSY-003#2"))                  # same ID twice, kept as two records
    reqs.append(req(s, "MSY-007", _text(rng), "messy!R13", native="MSY-007#2"))
    links = [link(s, reqs[0], "EXT-900", "trace", "messy!L1"), link(s, "EXT-901", reqs[1], "derive", "messy!L2"), link(s, reqs[2], reqs[3], "trace", "messy!L3")]
    return _ds(s, reqs, links, warnings=["2 duplicate UIDs (kept as separate records with distinct MIDs): ['MSY-003', 'MSY-007']",
                                          "2 links point outside this import (kept by UID)"])


def f08(size: int) -> Built:
    s, rng = Src("F08", "tabular", "tabular", "gappy.xlsx", "Requirements"), random.Random(8)
    reqs = [req(s, f"GAP-{i:03d}", _text(rng), f"Requirements!R{i + 1}") for i in range(1, 29)]
    reasons = ["empty statement text", "empty statement text", "empty statement text", "statement is only a section number"]
    rej = [rejected(s, reasons[i % 4], f"Requirements!R{30 + i}", {"ID": f"GAP-{900 + i}", "Statement": "" if i % 4 != 3 else "3.2.1"}) for i in range(12)]
    return _ds(s, reqs, [], rej, {"row filter (where) did not match": 6})


def f09(size: int) -> Built:
    s, rng = Src("F09", "tabular", "tabular", "huge.csv", "huge"), random.Random(9)
    reqs: list[dict] = []
    for i in range(size):
        parent = reqs[(i - 1) // 8]["mid"] if i else None
        reqs.append(req(s, f"BIG-{i + 1:06d}", _text(rng), f"huge!R{i + 2}", parent=parent, fields={"verification": VERIFY[i % 4], "status": STATUS[i % 3]}))
    links = [link(s, reqs[i], reqs[max(0, i - 40)], "trace", f"huge!L{i}") for i in range(40, size, 3)]
    return _ds(s, reqs, links)


def f10(size: int) -> Built:
    s = Src("F10", "docx", "tabular", "awkward.docx", "Table 1")
    long_text = "The unit shall " + " ".join(["continue to meet every performance requirement while the environment changes"] * 70) + "."
    texts = [
        long_text,
        "The sensor shall resolve ±0.5 µm at 25 °C and ≥ 99.9 % linearity (Ω ≤ 10 kΩ).",
        "The display shall show “Fault 12” and ‘Reset’ — then clear within 3 s.",
        "The unit shall accept commands in 日本語 and русский text.",
        "نظام التحكم يجب أن يسجل كل خطأ مع الوقت.",
        "The controller shall hold the setpoint.\nIt shall also report drift.\n\tIndented follow-on sentence.",
        "The panel <b>shall</b> light the &amp; indicator &lt;within&gt; 2 s.",
        "The identifier " + "X" * 300 + " shall never be shortened.",
        "The value shall be 1,234.5 kg (not 1.234,5).",
        "Combining marks: the unit shall report é as a single letter.",
        "The unit shall do   this    with    odd    spacing.",
        "The unit shall be marked ✓ when verified and ✗ when not.",
    ]
    return _ds(s, [req(s, f"AWK-{i + 1:02d}", t, f"Table 1!R{i + 2}") for i, t in enumerate(texts)], [])


def f11(size: int) -> list[Built]:
    a, rng = Src("F11A", "tabular", "tabular", "legacy_spec.xlsx", "Requirements"), random.Random(11)
    ra = [req(a, f"LEG-{i:03d}", _text(rng), f"Requirements!R{i + 1}", fields={"verification": VERIFY[i % 4]}) for i in range(1, 11)]
    b = Src("F11B", "reqif", "structured", "model_export.reqif", "Spec")
    rb = [req(b, f"MOD-{i:03d}", _text(rng), f"SO-{i}", fields=full_fields(rng, i)) for i in range(1, 11)]
    for i in range(2, 11):                                  # MOD-002..004 hang under MOD-001, the rest under earlier ones
        rb[i - 1]["parent_mid"] = rb[0]["mid"] if i <= 4 else rb[(i - 2) // 2]["mid"]
    lb = [link(b, rb[i], rb[0], "derive", f"SR-{i}") for i in range(1, 6)]
    return [_ds(a, ra, []), _ds(b, rb, lb)]


def f12(size: int) -> Built:
    s = Src("F12", "tabular", "tabular", "empty.csv", "empty")
    return _ds(s, [], [], warnings=["the source produced NO records: check the options and the profile. For a live connector run `reqin sample` to see what it can see"])


def f13(size: int) -> Built:
    s, rng = Src("F13", "tabular", "tabular", "wide.xlsx", "Requirements"), random.Random(13)
    names = [f"Custom attribute {k:02d}" for k in range(1, 28)] + ["Ünïcödé attribut", "A very long attribute name " + "x" * 80, "Attribute / with : odd ? characters"]
    reqs = [req(s, f"WID-{i:03d}", _text(rng), f"Requirements!R{i + 1}", fields={**full_fields(rng, i), "priority": ["High", "Medium", "Low"][i % 3], "safety_class": f"SC-{i % 4}"},
                extra={n: f"value {i}/{k}" for k, n in enumerate(names)}) for i in range(1, 11)]
    return _ds(s, reqs, [], unclaimed=names)


def f14(size: int) -> Built:
    s, rng = Src("F14", "oslc_rm", "structured", "https://dng.example.test/rm", "links"), random.Random(14)
    reqs = [req(s, f"UNK-{i:03d}", _text(rng), f"R{i}") for i in range(1, 13)]
    kinds = ["allocates", "x-custom", "Is Derived From", "trace", "allocates", "x-custom"]
    links = [link(s, reqs[i], reqs[i + 1], kinds[i % len(kinds)], f"L{i}") for i in range(10)]
    return _ds(s, reqs, links)


# id, name, folder, what is different, what must be true on screen, builder
SPECS: list[tuple[str, str, str, str, str, Callable[[int], Any]]] = [
    ("F1", "Minimal", "F01_minimal", "5 records: uid and text only",
     "No empty columns, no tree, no trace panel", f01),
    ("F2", "Everything", "F02_everything", "All six fields, hierarchy 4 levels deep, every link kind, extra with 10 keys",
     "Every panel works; the deep tree is navigable", f02),
    ("F3", "No IDs", "F03_no_ids", "Every uid is invented (uid_synthetic true)",
     "A badge on every ID; nothing is presented as a source ID", f03),
    ("F4", "Links only", "F04_links_only", "Links but no hierarchy",
     "Trace panel yes, tree no", f04),
    ("F5", "Hierarchy only", "F05_hierarchy_only", "Hierarchy but no links",
     "Tree yes, trace panel hidden with a reason", f05),
    ("F6", "Extracted from prose", "F06_extracted", "fidelity extracted, some uid_synthetic, Medium and Low confidence, locators like p3:blk12",
     "Verify banner; per-record verified state; Show in source shows the page and block", f06),
    ("F7", "Warnings", "F07_warnings", "Duplicate UIDs and links pointing outside the import (an end with a null mid)",
     "Warnings shown as written; outside links shown by uid and marked not in this import", f07),
    ("F8", "Heavy rejection", "F08_heavy_rejection", "30 percent of the source rejected for mixed reasons, plus filtered rows",
     "Rejected list with reasons; read, kept, rejected and filtered counts reconcile", f08),
    ("F9", "Large", "F09_large", "50,000 requirements by default (--size changes it), a hierarchy and many links",
     "Stays responsive; the list is windowed", f09),
    ("F10", "Awkward text", "F10_awkward_text", "Very long statements, Unicode, right-to-left text, symbols, line breaks, tabs, markup remnants, a 300-character word",
     "Shown verbatim; expandable; no layout break", f10),
    ("F11", "Two sources", "F11_two_sources", "Two imports in one workspace: one tabular, one structured",
     "A source chip on every record; the fidelity cue differs per record", f11),
    ("F12", "Empty", "F12_empty", "Zero requirements, a warning that says why",
     "A helpful message with the warning, not a blank grid", f12),
    ("F13", "Many unknown fields", "F13_many_unknown_fields", "30 extra keys with names the screen has never seen, and two non-standard fields keys (priority, safety_class)",
     "The Other fields panel shows them all, generically", f13),
    ("F14", "Unknown link kinds", "F14_unknown_link_kinds", "Link kinds like allocates, x-custom and Is Derived From",
     "Shown as written; not dropped; not an error", f14),
]


def _union(parts: list[dict[str, Any]]) -> dict[str, Any]:
    if len(parts) == 1:
        return parts[0]
    d: dict[str, Any] = {}
    for k in parts[0]:
        v = parts[0][k]
        if isinstance(v, bool):
            d[k] = any(p[k] for p in parts)
        elif isinstance(v, int):
            d[k] = max(p[k] for p in parts) if k == "max_depth" else sum(p[k] for p in parts)
        else:
            d[k] = sorted({x for p in parts for x in p[k]})
    return d


def build_all(out_dir: str | Path, only: list[str] | None = None, size: int = 50_000) -> list[dict[str, Any]]:
    """Write the datasets (and index.json) under out_dir. Returns the index entries."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    wanted = {x.strip().upper() for x in only} if only else None
    unknown = (wanted or set()) - {sp[0] for sp in SPECS}
    if unknown:
        raise ValueError(f"unknown dataset id(s): {', '.join(sorted(unknown))}. Known: {', '.join(sp[0] for sp in SPECS)}")
    index = []
    for did, name, folder, different, must, fn in SPECS:
        if wanted and did not in wanted:
            continue
        built = fn(size)
        parts = built if isinstance(built, list) else [built]
        folders = []
        for n, p in enumerate(parts):
            sub = folder if len(parts) == 1 else f"{folder}/{'ab'[n]}"
            write_dataset_dicts(p["requirements"], p["links"], p["rejected"], p["report"], out / sub)
            folders.append(sub)
        expect = _union([describe(load_dataset(out / f)[0]) for f in folders])
        index.append({"id": did, "name": name, "folders": folders, "different": different, "must_be_true_on_screen": must, "expect": expect})
    (out / "index.json").write_text(json.dumps({"contract": "reqin-dataset", "version": 1, "datasets": index}, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                    encoding="utf-8")
    return index


def validate_all(out_dir: str | Path) -> dict[str, list[str]]:
    idx = json.loads((Path(out_dir) / "index.json").read_text(encoding="utf-8"))["datasets"]
    return {f: validate_dataset(Path(out_dir) / f) for e in idx for f in e["folders"]}
