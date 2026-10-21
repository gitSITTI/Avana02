"""Scoring the comparison engine against pairs labelled by someone who had not seen the engine.

The pairs in `data/*.json` were written by a language model asked for realistic examples of each relationship (EQUIVALENT, VARIANT, SUBSUMES with a direction, CONFLICT, COMPLEMENTARY,
UNRELATED), told not to read any code in this repository. The sentences are invented. It is a *different* author from the one who wrote the engine and its synthetic corpus, but it is the same model
family as the assistant that wrote the engine, so it is not an independent human judgement. `docs/COMPARE_RESULTS.md` says which sets were looked at while the engine was being fixed and which were
scored once, untouched.

How an answer is read off the engine's output: the two sentences go into one dataset together with all the others. If they are in the same cluster the engine said EQUIVALENT. Otherwise the answer is
the type of the pair line that has one sentence on each side (SUBSUMES also with its direction). If there is no such line the engine said nothing about the pair, which is scored as UNRELATED
(for a label of UNRELATED that is agreement; for anything else it is a miss).
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DATA = Path(__file__).with_name("labelled_pairs")
ANSWERS = ("EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED")


def load(name: str) -> list[dict[str, Any]]:
    obj = json.loads((DATA / name).read_text(encoding="utf-8"))
    return obj["pairs"] if isinstance(obj, dict) else obj


def rows_for(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from reqin.normalise import normalise_text
    rows = []
    for p in pairs:
        for side in ("a", "b"):
            mid = f"{p['id']}{side}"
            rows.append({"mid": mid, "uid": mid, "uid_synthetic": False, "text": p[side], "norm_text": normalise_text(p[side]), "fields": {}, "parent_mid": None})
    return rows


def answers(pairs: list[dict[str, Any]], res: Any) -> dict[str, tuple[str, str | None]]:
    """For each pair id: (type, direction) where direction is 'a' or 'b' (which sentence is the stricter) for SUBSUMES, else None. 'NONE' means the engine said nothing."""
    cluster_of = {m["mid"]: c["cid"] for c in res.clusters for m in c["members"]}
    where: dict[str, list[dict]] = defaultdict(list)
    for pr in res.pairs:
        for m in pr["a"]["mids"] + pr["b"]["mids"]:
            where[m].append(pr)
    out: dict[str, tuple[str, str | None]] = {}
    for p in pairs:
        ma, mb = f"{p['id']}a", f"{p['id']}b"
        if cluster_of.get(ma) is not None and cluster_of.get(ma) == cluster_of.get(mb):
            out[p["id"]] = ("EQUIVALENT", None)
            continue
        got: tuple[str, str | None] = ("NONE", None)
        for pr in where.get(ma, []):
            sa, sb = set(pr["a"]["mids"]), set(pr["b"]["mids"])
            if (ma in sa and mb in sb) or (ma in sb and mb in sa):       # opposite sides only: both on one side is not a statement about the two
                d = pr["direction"]
                if d:
                    d = "a" if (d == "a") == (ma in sa) else "b"
                got = (pr["type"], d)
                break
        out[p["id"]] = got
    return out


def direction_of(got: dict[str, tuple[str, str | None]], p: dict[str, Any]) -> bool:
    return got[p["id"]][1] == p.get("direction")


def score(pairs: list[dict[str, Any]], vocab: Any = None, settings: Any = None) -> dict[str, Any]:
    from reqin.compare import compare
    res = compare(rows_for(pairs), vocab, settings)
    got = answers(pairs, res)
    agree = 0
    by_kind: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    confusion: dict[str, Counter] = defaultdict(Counter)
    wrong: list[dict[str, Any]] = []
    rules: Counter = Counter()
    said: dict[str, list[int]] = defaultdict(lambda: [0, 0])          # what the engine said -> [times, times the label agreed]
    dir_counts = {"right": 0, "wrong": 0}
    for p in pairs:
        typ, direction = got[p["id"]]
        label, ldir = p["type"], p.get("direction")
        shown = "UNRELATED" if typ == "NONE" else typ
        ok = shown == label and (label != "SUBSUMES" or direction == ldir)
        agree += ok
        said[shown][0] += 1
        said[shown][1] += int(ok)
        if label == "SUBSUMES" and typ == "SUBSUMES":
            dir_counts["right" if direction_of(got, p) else "wrong"] += 1
        cell = by_kind[p.get("kind", "?")]
        cell[0] += int(ok)
        cell[1] += 1
        confusion[label][typ + (f" ({direction} stricter)" if direction else "")] += 1
        if not ok:
            wrong.append({"id": p["id"], "kind": p.get("kind"), "label": label + (f" ({ldir} stricter)" if ldir else ""), "engine": typ + (f" ({direction} stricter)" if direction else ""),
                          "a": p["a"], "b": p["b"], "why_label": p.get("why", "")})
    for pr in res.pairs:
        rules[pr["rule"]] += 1
    dangerous = [w for w in wrong if w["engine"].startswith("EQUIVALENT") or (w["engine"].startswith("SUBSUMES") and not w["label"].startswith("SUBSUMES"))
                 or (w["engine"].startswith("CONFLICT") and not w["label"].startswith("CONFLICT"))]
    return {"pairs": len(pairs), "agree": agree, "by_kind": {k: tuple(v) for k, v in sorted(by_kind.items())},
            "confusion": {k: dict(sorted(v.items())) for k, v in sorted(confusion.items())}, "wrong": wrong, "said": {k: tuple(v) for k, v in sorted(said.items())}, "subsumes_direction": dir_counts,
            "false_equivalent": [w for w in wrong if w["engine"].startswith("EQUIVALENT")], "dangerous": dangerous, "rules_used": dict(sorted(rules.items()))}
