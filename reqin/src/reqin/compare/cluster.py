"""Clusters: groups of requirements that are EQUIVALENT to each other, and nothing else.

Chaining is the failure to avoid (a ~ b and b ~ c does not make a ~ c). So a cluster is only ever a *clique*: every member is EQUIVALENT to every other member. `merge_cliques` does that
for any list of equivalent-pair evidence (complete linkage: two groups join only if every pair across them is an edge). With this engine's rules two requirements are EQUIVALENT only when their
keys are equal, which is already an equivalence relation, so the groups it is given are cliques to begin with and it never has to split anything. The check is made anyway, on every cluster,
because a later rule that makes 'equivalent' fuzzier would break that silently.

Only EQUIVALENT edges join requirements. Variants, conflicts and the rest are notes on a cluster, never members.
"""
from __future__ import annotations

from typing import Callable, Iterable

from .slots import Slots

AUTHORITY = {"approved", "baselined", "released", "published", "accepted", "frozen"}
SIX = ("rationale", "verification", "allocation", "owner", "baseline", "status")
CHECK_ALL_PAIRS_UP_TO = 30


def merge_cliques(nodes: list[str], edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    """Complete-linkage grouping: start with one group per node and join two groups only when every cross pair is an edge. Deterministic: nodes and edges are taken in sorted order."""
    adj: dict[str, set[str]] = {n: set() for n in nodes}
    for a, b in edges:
        if a != b and a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    groups: dict[str, set[str]] = {n: {n} for n in sorted(nodes)}
    changed = True
    while changed:
        changed = False
        names = sorted(groups)
        for i, x in enumerate(names):
            if x not in groups:
                continue
            for y in names[i + 1:]:
                if y in groups and all(m in adj[k] for k in groups[x] for m in groups[y]):
                    groups[x] |= groups.pop(y)
                    changed = True
    return [sorted(g) for _, g in sorted(groups.items())]


def check_cluster(members: list[Slots], classify: Callable[[Slots, Slots], str | None]) -> bool:
    """Every pair of members is EQUIVALENT by the rule function itself (all pairs for a cluster up to 30 members; each against the first above that)."""
    if len(members) <= CHECK_ALL_PAIRS_UP_TO:
        return all(classify(a, b) == "EQUIVALENT" for i, a in enumerate(members) for b in members[i + 1:])
    return all(classify(members[0], m) == "EQUIVALENT" for m in members[1:])


def representative(members: list[tuple[Slots, dict]]) -> tuple[str, list[str]]:
    """The member to show first, and why. This is the research report's own proposal in a form that needs no model: a human-designated baseline first, then a status that says approved, then
    the most of the six well-known fields filled in, then a real id over an invented one, then the lowest id. It is a proposal, never a decision."""
    def key(m: tuple[Slots, dict]) -> tuple:
        r = m[1]
        f = r.get("fields") or {}
        return (0 if str(f.get("baseline", "")).strip() else 1, 0 if str(f.get("status", "")).strip().lower() in AUTHORITY else 1, -sum(1 for k in SIX if str(f.get(k, "")).strip()),
                1 if r.get("uid_synthetic") else 0, str(r.get("uid", "")), str(r.get("mid", "")))
    ranked = sorted(members, key=key)
    win = ranked[0]
    why: list[str] = []
    labels = ["it is in a named baseline", "its status says approved or released", "more of the six fields are filled in", "its id is the source's, not invented by the importer"]
    if len(ranked) > 1:
        a, b = key(win), key(ranked[1])
        for i, lab in enumerate(labels):
            if a[i] != b[i]:
                why.append(lab)
                break
    why.append("lowest id" if len(ranked) > 1 else "only member")
    return win[0].mid, why
