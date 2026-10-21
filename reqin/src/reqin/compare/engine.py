"""The engine: requirements in, clusters and typed pairs out. Deterministic, no network, no model.

    slots (one per requirement)  ->  groups of equal keys  ->  clusters (two or more in a group)
                                 ->  pairs inside a family (same subject and predicate words): the slot rules
                                 ->  pairs across families (near misses): found by rare shared words, then named by the two word rules
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from . import cluster as cl
from .ladder import features, idf_table, rung, weighted_jaccard
from .rules import RULES, TYPES, Relation, classify
from .slots import Slots, extract
from .vocabulary import Vocabulary
from .vocabulary import load as load_vocabulary

ENGINE = {"name": "reqin-compare", "version": "1"}
TYPE_ORDER = {t: i for i, t in enumerate(("CONFLICT", "VARIANT", "SUBSUMES", "COMPLEMENTARY", "UNRELATED", "EQUIVALENT"))}


@dataclass(frozen=True)
class Settings:
    tau_pair: float = 0.5          # a pair of different wordings is listed only if half of their (rarity-weighted) words are shared; never changes a cluster or a type
    max_posting: int = 100         # a word found in more than this many families is too common to find pairs by
    max_family: int = 300          # a family (same subject and predicate words) with more different numberings than this is not compared pairwise
    max_related: int = 50          # most pairs listed on a cluster


@dataclass
class Result:
    slots: list[Slots]
    clusters: list[dict[str, Any]]
    pairs: list[dict[str, Any]]
    summary: dict[str, Any]


def _hid(prefix: str, *parts: str) -> str:
    return prefix + "-" + hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:10]


def _endpoint(units: list[list[Slots]], clusters_of: dict[str, str], scope: str) -> dict[str, Any]:
    mids = sorted(m.mid for u in units for m in u)
    cids = sorted({clusters_of[m] for m in mids if m in clusters_of})
    return {"mids": mids, "clusters": cids, "scope": scope}


def _span(x: tuple[int, int] | None) -> list[int] | None:
    return None if x is None else [x[0], x[1]]


def _why(rel: Relation) -> list[dict[str, Any]]:
    return [{"code": f.code, "text": f.text, "a_span": _span(f.a_span), "b_span": _span(f.b_span)} for f in rel.why]


def compare(requirements: list[dict[str, Any]], vocab: Vocabulary | None = None, settings: Settings | None = None) -> Result:
    vocab = vocab or load_vocabulary()
    st = settings or Settings()
    req_by_mid = {r["mid"]: r for r in requirements}
    slots = [extract(r["norm_text"], vocab, r["mid"], r.get("uid", ""), r.get("text")) for r in requirements]
    slots.sort(key=lambda s: (s.uid, s.mid))
    notes: list[str] = []
    limits: dict[str, Any] = {}

    # ---- groups of equal keys, and clusters ----------------------------------------------------------------------
    groups: dict[str, list[Slots]] = defaultdict(list)
    for s in slots:
        groups[s.digest].append(s)
    units = sorted(groups.values(), key=lambda u: (u[0].uid, u[0].mid))
    clusters: list[dict[str, Any]] = []
    clusters_of: dict[str, str] = {}
    cluster_units: dict[str, list[Slots]] = {}

    def eq(a: Slots, b: Slots) -> str | None:
        r = classify(a, b)
        return r.type if r else None

    # ---- families and the pairs between wordings -----------------------------------------------------------------
    families: dict[tuple, list[list[Slots]]] = defaultdict(list)
    for u in units:
        if u[0].empty:
            continue
        families[u[0].family].append(u)
    fam_list = sorted(families.items(), key=lambda kv: (kv[1][0][0].uid, kv[1][0][0].mid))
    idf_raw, d_raw = idf_table(s.raw_tokens for u in units for s in u[:1])
    idf_canon, d_canon = idf_table(u[0].canon_tokens() for u in units)

    pair_rows: list[dict[str, Any]] = []
    equiv_edges: list[tuple[str, str]] = []        # EQUIVALENT between two different keys: none with today's rules; cluster.merge_cliques is what would join them

    def add_pair(ua: list[Slots], ub: list[Slots], rel: Relation, scope: str) -> None:
        a, b = ua[0], ub[0]
        f = features(a, b, idf_raw, d_raw, idf_canon, d_canon)
        ea, eb = _endpoint([ua], clusters_of, scope), _endpoint([ub], clusters_of, scope)
        if scope == "words":
            ea, eb = _endpoint(families[a.family], clusters_of, scope), _endpoint(families[b.family], clusters_of, scope)
        if (ea["mids"][0], eb["mids"][0]) > (eb["mids"][0], ea["mids"][0]):
            ea, eb, a, b, ua, ub = eb, ea, b, a, ub, ua
            flip = True
        else:
            flip = False
        direction = rel.direction
        why = _why(rel)
        oa, ob = rel.words_only_a, rel.words_only_b
        if flip:
            if direction:
                direction = "b" if direction == "a" else "a"
            why = [{"code": w["code"], "text": w["text"], "a_span": w["b_span"], "b_span": w["a_span"]} for w in why]
            oa, ob = ob, oa
        pair_rows.append({
            "pid": _hid("P", *ea["mids"], "|", *eb["mids"]), "status": "draft", "provenance": "mechanical", "a": ea, "b": eb, "shown_a": a.mid, "shown_b": b.mid,
            "type": rel.type, "direction": direction, "basis": rel.basis, "rule": rel.rule, "needs_review": rel.needs_review,
            "score": f["canonical_overlap"], "rung": rung(f), "features": f, "why": why, "words_only_a": oa, "words_only_b": ob,
        })

    skipped_families = 0
    for key, us in fam_list:
        if len(us) < 2:
            continue
        if len(us) > st.max_family:
            skipped_families += 1
            continue
        for ua, ub in combinations(us, 2):
            rel = classify(ua[0], ub[0])
            if rel and rel.type == "EQUIVALENT":
                equiv_edges.append((ua[0].digest, ub[0].digest))
            elif rel:
                add_pair(ua, ub, rel, "group")
    if skipped_families:
        limits["families_not_compared_pairwise"] = skipped_families
        notes.append(f"{skipped_families} set(s) of requirements with identical subject and words but more than {st.max_family} different numberings were not compared with each other.")

    # across families: only by rare shared words
    ftoks = [frozenset(t for t in us[0][0].canon_tokens() if t[0] in "sp") for _, us in fam_list]
    fidf, fdef = idf_table(ftoks)
    post: dict[str, list[int]] = defaultdict(list)
    for i, t in enumerate(ftoks):
        for w in t:
            post[w].append(i)
    too_common = sorted(w for w, ix in post.items() if len(ix) > st.max_posting)
    limits["tokens_too_common_to_find_pairs"] = len(too_common)
    seen: set[tuple[int, int]] = set()
    for w, ix in sorted(post.items()):
        if len(ix) > st.max_posting or len(ix) < 2:
            continue
        for i, j in combinations(ix, 2):
            seen.add((i, j))
    for i, j in sorted(seen):
        ov = weighted_jaccard(ftoks[i], ftoks[j], fidf, fdef)
        if ov < st.tau_pair:
            continue
        ua = max(fam_list[i][1], key=lambda u: (len(u), u[0].digest))
        ub = max(fam_list[j][1], key=lambda u: (len(u), u[0].digest))
        rel = classify(ua[0], ub[0], ov, st.tau_pair)
        if rel:
            add_pair(ua, ub, rel, "words")

    # ---- clusters: groups of equal keys, joined further only where every pair is EQUIVALENT -------------------------
    unit_of = {u[0].digest: u for u in units}
    involved = sorted({d for e in equiv_edges for d in e})
    merged: list[list[Slots]] = [unit_of[d] for d in unit_of if d not in involved]
    if involved:
        merged += [[m for d in grp for m in unit_of[d]] for grp in cl.merge_cliques(involved, equiv_edges)]
    merged.sort(key=lambda u: (u[0].uid, u[0].mid))
    for u in merged:
        if len(u) < 2:
            continue
        u.sort(key=lambda m: (m.uid, m.mid))
        cid = _hid("C", *sorted(m.mid for m in u))
        cluster_units[cid] = u
        for m in u:
            clusters_of[m.mid] = cid
    # pair endpoints were built before cluster ids existed: fill them in
    for p in pair_rows:
        for side in ("a", "b"):
            p[side]["clusters"] = sorted({clusters_of[m] for m in p[side]["mids"] if m in clusters_of})

    # ---- clusters, in full ---------------------------------------------------------------------------------------
    pair_rows.sort(key=lambda p: (TYPE_ORDER[p["type"]], -p["score"], p["pid"]))
    by_mid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for p in pair_rows:
        for m in p["a"]["mids"] + p["b"]["mids"]:
            by_mid[m].append(p)
    for cid in sorted(cluster_units):
        u = cluster_units[cid]
        members = [(m, req_by_mid[m.mid]) for m in u]
        rep, basis = cl.representative(members)
        valid = cl.check_cluster(u, eq)
        raw = [set(m.raw_tokens) for m in u]
        repr_raw = next(set(m.raw_tokens) for m in u if m.mid == rep)
        min_overlap = min(len(repr_raw & r) / len(repr_raw | r) if (repr_raw | r) else 1.0 for r in raw)
        if all(m.exact == u[0].exact for m in u):
            rg = "exact"
        elif all(m.masked == u[0].masked for m in u):
            rg = "masked"
        else:
            rg = "canonical"
        touching = {}
        for m in u:
            for p in by_mid.get(m.mid, []):
                touching[p["pid"]] = p
        rel_pairs = sorted(touching.values(), key=lambda p: (TYPE_ORDER[p["type"]], -p["score"], p["pid"]))
        clusters.append({
            "cid": cid, "status": "draft", "provenance": "mechanical",
            "members": [{"mid": m.mid, "uid": m.uid} for m in u], "representative": rep, "representative_basis": basis,
            "rung": rg, "why": _cluster_why(u), "valid": valid, "min_word_overlap": round(min_overlap, 4),
            "related": [p["pid"] for p in rel_pairs[: st.max_related]], "related_total": len(rel_pairs),
        })

    # ---- what to tell the person ---------------------------------------------------------------------------------
    n = len(slots)
    if n == 0:
        notes.append("Nothing to compare: the dataset has no requirements.")
    elif n == 1:
        notes.append("Nothing to compare: the dataset has one requirement.")
    elif not clusters and not pair_rows:
        notes.append("Nothing found: no two requirements are equivalent, and no pair of wordings overlaps enough to list. This can be true, or the wording may be too different for the written rules.")
    if any(s.empty for s in slots):
        notes.append(f"{sum(1 for s in slots if s.empty)} requirement(s) have no words in their text and were not compared.")
    if any(s.no_modal for s in slots):
        notes.append(f"{sum(1 for s in slots if s.no_modal)} requirement(s) have no 'shall', 'should', 'will', 'may' or 'must': they were compared as written, with no subject.")
    if any(s.compound for s in slots):
        notes.append(f"{sum(1 for s in slots if s.compound)} requirement(s) have more than one modal and were compared as written.")
    if any(r.get("uid_synthetic") for r in requirements):
        notes.append("Some ids were invented by the importer (the source has none); they are used only to sort and to show.")
    if all(r.get("parent_mid") is None for r in requirements) and n:
        notes.append("No requirement has a parent: the hierarchy was not used (the engine does not use it either way).")
    if too_common:
        notes.append(f"{len(too_common)} word(s) occur in more than {st.max_posting} wordings and were not used to find pairs of different wordings; "
                     "two wordings that share only such words are not compared. Requirements with equal keys are always grouped.")

    counts: dict[str, Any] = {"requirements": n, "groups": len(units), "clusters": len(clusters), "in_clusters": sum(len(c["members"]) for c in clusters),
                              "singletons": sum(1 for u in units if len(u) == 1), "pairs": {t: sum(1 for p in pair_rows if p["type"] == t) for t in TYPES if t != "EQUIVALENT"}}
    summary = {"counts": counts, "limits": limits, "notes": notes,
               "settings": {"tau_pair": st.tau_pair, "max_posting": st.max_posting, "max_family": st.max_family, "max_related": st.max_related},
               "engine": {**ENGINE, "rules": sorted(RULES), "vocabulary_sha256": vocab.sha256, "vocabulary": vocab.source}}
    return Result(slots, clusters, pair_rows, summary)


def _cluster_why(u: list[Slots]) -> list[str]:
    """Plain statements of why these requirements were put together, and what differs between their wordings."""
    out: list[str] = []
    rep = u[0]
    out.append("same subject: " + (rep.subject_text or "(none)") + (" (some wordings are in the passive voice)" if any(m.passive for m in u) else ""))
    quants = sorted({q.raw for m in u for q in m.quantities if q.role == "main"})
    if len({tuple(q.raw for q in m.quantities) for m in u}) > 1:
        out.append("numbers written differently but equal: " + "; ".join(quants[:6]))
    if any(m.passive for m in u) and not all(m.passive for m in u):
        out.append("some members are active and some passive")
    if len({m.conditions[0].start == 0 for m in u if m.conditions}) > 1:
        out.append("the condition comes first in some members and last in others")
    sets = [set(m.masked) - {"<q>"} for m in u]
    diff = sorted(set.union(*sets) - set.intersection(*sets))
    if diff:
        out.append("wordings differ in: " + ", ".join(diff[:12]) + (" ..." if len(diff) > 12 else ""))
    return out
