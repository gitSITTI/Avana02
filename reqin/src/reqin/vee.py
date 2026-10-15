"""The engineering V, worked out from an imported dataset: how many requirements sit at each level, and what checks each level.

    reqin vee DATASET_DIR                         levels from the parent links (depth in the tree)
    reqin vee DATASET_DIR --by field --level-field "Level"
    reqin vee DATASET_DIR --json                  the same, for a screen or a CI job

The V lays out systems engineering. Down the left leg, requirements get more detailed: stakeholder needs, system, subsystem, component.
Up the right leg, each level is shown to be met by a matching check: validation, then system, subsystem and component verification.
A requirement is "traced" when it has a verification method (test, analysis, inspection or demonstration) AND at least one
verification item (a verify link). Every other requirement is a gap.

Rules, all of them mechanical and written down so a person can check any number:

  Level   by depth (default): the requirement's depth in the parent tree, a root being level 1. Deeper than level 4 is counted at 4 and reported.
          If NO requirement has a parent, depth says nothing, so no requirement is placed; use --by field instead.
          by field: the value of the named field (looked up in the canonical fields, then in the source fields the importer kept).
          It reads 1 to 4, L1 to L4, "level 3", or the words need, stakeholder, system, subsystem, component. Anything else is "unplaced".
  Method  from the verification field: test, analysis (analyse), inspection, demonstration (demo), or the single letters T, A, I, D.
          Several methods in one field count under each, and the requirement counts once as having a method. Other text is "other".
  Item    a verify link counts for its target. When the target is not in the import but the source is (the link was exported the other
          way round), it counts for the source. A verify link with neither end in the import counts for no one and is reported.

The app never changes a verification item. It reports which ones a merge would leave pointing at a requirement that is gone.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .dataset import depths

LEVELS = (
    (1, "Stakeholder needs", "Validation"),
    (2, "System requirements", "System verification"),
    (3, "Subsystem requirements", "Subsystem verification"),
    (4, "Component requirements", "Component verification"),
)
METHODS = ("Test", "Analysis", "Inspection", "Demonstration")
_LETTER = {"t": "Test", "a": "Analysis", "i": "Inspection", "d": "Demonstration"}


def methods_in(value: Any) -> list[str]:
    """The verification methods named in a field value, in the order Test, Analysis, Inspection, Demonstration. ["other"] if it names none."""
    text = str(value or "").strip().lower()
    if not text:
        return []
    found = []
    if re.search(r"\btests?\b|\btesting\b", text):
        found.append("Test")
    if re.search(r"\banaly[sz]", text):
        found.append("Analysis")
    if re.search(r"\binspect", text):
        found.append("Inspection")
    if re.search(r"\bdemo", text):
        found.append("Demonstration")
    if not found:
        letters = [p for p in re.split(r"[\s,;/+&]+", text) if p]
        if letters and all(len(p) == 1 and p in _LETTER for p in letters):
            found = [_LETTER[p] for p in letters]
    if not found:
        return ["other"]
    return [m for m in METHODS if m in found]


def level_in(value: Any) -> int | None:
    """1 to 4 from text such as 2, L2, level 2, system. None when it cannot be read."""
    text = str(value or "").strip().lower()
    if not text:
        return None
    m = re.fullmatch(r"(?:l|lvl|level)?\s*([1-4])", text)
    if m:
        return int(m.group(1))
    if re.search(r"stakeholder|\bneeds?\b|\buser\b|operational", text):
        return 1
    if re.search(r"sub-?system|\bsegment\b", text):
        return 3
    if re.search(r"\bsystem\b", text):
        return 2
    if re.search(r"component|\bunit\b|\bpart\b|\bmodule\b", text):
        return 4
    return None


def _field(r: dict, name: str) -> Any:
    want = name.strip().lower()
    for bag in (r.get("fields") or {}, r.get("extra") or {}):
        for k, v in bag.items():
            if str(k).strip().lower() == want:
                return v
    return None


def vee_report(ds: dict[str, Any], by: str = "depth", level_field: str | None = None) -> dict[str, Any]:
    """The V of a dataset loaded with dataset.load_dataset. Pure: the same dataset always gives the same report."""
    if by not in ("depth", "field"):
        raise ValueError("by must be 'depth' or 'field'")
    if by == "field" and not level_field:
        raise ValueError("--by field needs --level-field NAME")
    reqs, links = ds["requirements"], ds["links"]
    mids = {r["mid"] for r in reqs}
    dep = depths(reqs)
    has_tree = any(r.get("parent_mid") for r in reqs)
    notes: list[str] = []
    if by == "depth" and not has_tree:
        notes.append("No requirement has a parent, so depth cannot place any of them. Use --by field --level-field NAME, or import with a parent column.")

    items: Counter[str] = Counter()
    unplaced_links = 0
    for l in links:
        if l["kind"] != "verify":
            continue
        s, t = l.get("source_mid"), l.get("target_mid")
        if t in mids:
            items[t] += 1
        elif s in mids and t is None:
            items[s] += 1
        else:
            unplaced_links += 1

    rows = {k: {"level": k, "name": n, "check": v, "requirements": 0, "with_method": 0, "with_item": 0, "traced": 0, "gaps": 0, "no_method": 0,
                "no_item": 0, "items": 0, "methods": {m: 0 for m in METHODS} | {"other": 0}} for k, n, v in LEVELS}
    unplaced = {"requirements": 0, "traced": 0, "gaps": 0, "items": 0}
    folded = 0
    multiple = 0
    for r in reqs:
        if by == "depth":
            lvl: int | None = (min(dep[r["mid"]], 4) if has_tree else None)
            if has_tree and dep[r["mid"]] > 4:
                folded += 1
        else:
            lvl = level_in(_field(r, level_field or ""))
        ms = methods_in((r.get("fields") or {}).get("verification"))
        n_items = items[r["mid"]]
        traced = bool(ms) and n_items > 0
        if len(ms) > 1:
            multiple += 1
        row = rows.get(lvl) if lvl else None
        if row is None:
            unplaced["requirements"] += 1
            unplaced["items"] += n_items
            unplaced["traced" if traced else "gaps"] += 1
            continue
        row["requirements"] += 1
        row["items"] += n_items
        row["with_method"] += bool(ms)
        row["with_item"] += n_items > 0
        row["no_method"] += not ms
        row["no_item"] += n_items == 0
        row["traced" if traced else "gaps"] += 1
        for m in ms:
            row["methods"][m] += 1
    if unplaced["requirements"] and not (by == "depth" and not has_tree):
        notes.append(f"{unplaced['requirements']} requirement(s) could not be placed at a level (the {level_field!r} field is missing or not readable)." if by == "field"
                     else f"{unplaced['requirements']} requirement(s) could not be placed at a level.")
    if folded:
        notes.append(f"{folded} requirement(s) sit deeper than level 4 in the tree and are counted at level 4.")
    if unplaced_links:
        notes.append(f"{unplaced_links} verify link(s) have neither end among the imported requirements and are counted for no one.")
    levels = [rows[k] for k in (1, 2, 3, 4)]
    total = {
        "requirements": len(reqs),
        "traced": sum(r["traced"] for r in levels) + unplaced["traced"],
        "gaps": sum(r["gaps"] for r in levels) + unplaced["gaps"],
        "items": sum(items.values()),
        "unplaced": unplaced["requirements"],
        "folded_into_level_4": folded,
        "with_more_than_one_method": multiple,
        "verify_links_counted_for_no_one": unplaced_links,
    }
    return {"by": by, "level_field": level_field, "hierarchy": has_tree, "levels": levels, "unplaced": unplaced, "total": total, "notes": notes}


def render(rep: dict[str, Any]) -> str:
    """A table a person can read in a terminal or paste into a ticket."""
    out = [f"The V ({'levels from the parent tree' if rep['by'] == 'depth' else 'levels from the field ' + repr(rep['level_field'])})", ""]
    head = f"{'Level':<28}{'Reqs':>7}{'Traced':>8}{'Gaps':>7}{'No method':>11}{'No item':>9}{'Items':>7}  Checked by"
    out.append(head)
    out.append("-" * len(head))
    for r in rep["levels"]:
        out.append(f"{r['level']} {r['name']:<26}{r['requirements']:>7}{r['traced']:>8}{r['gaps']:>7}{r['no_method']:>11}{r['no_item']:>9}{r['items']:>7}  {r['check']}")
    u = rep["unplaced"]
    if u["requirements"]:
        out.append(f"{'  Not placed at a level':<28}{u['requirements']:>7}{u['traced']:>8}{u['gaps']:>7}{'':>11}{'':>9}{u['items']:>7}")
    t = rep["total"]
    out.append("-" * len(head))
    out.append(f"{'All requirements':<28}{t['requirements']:>7}{t['traced']:>8}{t['gaps']:>7}{'':>11}{'':>9}{t['items']:>7}")
    out.append("")
    out.append("Methods by level (a requirement with two methods counts under each):")
    for r in rep["levels"]:
        m = r["methods"]
        out.append(f"  {r['level']} {r['name']:<26}" + "  ".join(f"{k} {m[k]}" for k in METHODS) + (f"  other {m['other']}" if m["other"] else ""))
    if rep["notes"]:
        out.append("")
        out.extend("Note: " + n for n in rep["notes"])
    return "\n".join(out)
