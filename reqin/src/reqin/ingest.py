"""The one pipeline every source goes through:  adapter.read -> select -> map -> normalise -> canonical.

Invariant (tested for every adapter):  raw records == requirements + rejected + filtered_out.
Nothing disappears without a reason in the report.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from .adapter import Adapter, Source, pick_adapter
from .mapping import LinkRule, Profile, apply_rule, propose_profile, row_matches
from .model import Conf, IngestResult, Link, RawLink, RawRecord, Rejected, Requirement, make_mid
from .normalise import extract_slots, fingerprint, normalise_text, strip_markup


def ingest(src: Source, profile: Profile | None = None, adapter: Adapter | None = None, namespace: str | None = None) -> IngestResult:
    adapter = adapter or pick_adapter(src, profile.adapter if profile else None)
    warnings: list[str] = []
    if profile is None:
        profile = propose_profile(adapter.discover(src), adapter.name, name=f"proposed-{adapter.name}")
        warnings.append("profile was PROPOSED by heuristics: a human must confirm it before results are trusted")
    ns = namespace or profile.namespace or adapter.name

    raws: list[RawRecord] = []
    raw_links: list[RawLink] = []
    for item in adapter.read(src):
        (raws if isinstance(item, RawRecord) else raw_links).append(item)

    reqs: list[Requirement] = []
    rejected: list[Rejected] = []
    filtered: Counter[str] = Counter()
    uid_to_mid: dict[str, str] = {}
    native_to_mid: dict[str, str] = {}
    pending_parent: list[tuple[Requirement, str | None, str | None]] = []
    coverage: defaultdict[str, int] = defaultdict(int)
    conf_count: defaultdict[str, Counter] = defaultdict(Counter)
    claimed_keys: set[str] = set()
    text_rule = profile.fields.get("text")
    claimed_all: set[str] = set()
    for rule in profile.fields.values():
        claimed_all.update(rule.src + rule.join)
    mid_to_uid: dict[str, str] = {}

    for rec in raws:
        if profile.containers is not None and rec.ref.container not in profile.containers:
            filtered[f"container not selected: {rec.ref.container}"] += 1
            continue
        if profile.where and not row_matches(profile.where, rec.fields):
            filtered["row filter (where) did not match"] += 1
            continue
        if text_rule is None:
            rejected.append(Rejected(rec.ref, "profile has no 'text' rule", rec.fields))
            continue
        text, tconf, used = apply_rule(text_rule, rec.fields)
        used = list(used)
        if not text.strip():
            rejected.append(Rejected(rec.ref, "empty statement text", rec.fields))
            continue
        text = strip_markup(text).strip() if text_rule.strip_markup else text.strip()
        canon: dict[str, str] = {}
        conf: dict[str, Conf] = {"text": tconf}
        for name, rule in profile.fields.items():
            if name == "text":
                continue
            v, c, u = apply_rule(rule, rec.fields)
            used += u
            if v:
                canon[name] = v
                conf[name] = c
        uid = canon.pop("uid", "") or (rec.native_id or "")
        synthetic = False
        if not uid:
            uid, synthetic = f"{ns}:{rec.ref.container}:{rec.ref.locator}", True
        conf["uid"] = conf.get("uid", Conf.LOW) if not synthetic else Conf.LOW
        native = rec.native_id or uid
        mid = make_mid(ns, native)
        norm = normalise_text(text)
        slots = extract_slots(norm)
        parent_ref = canon.pop("parent", None)
        r = Requirement(mid=mid, uid=uid, uid_synthetic=synthetic, text=text, norm_text=norm, fingerprint=fingerprint(norm, slots),
                        slots=slots, fields=canon,
                        extra={k: v for k, v in rec.fields.items() if k not in used and (k not in claimed_all or str(v).strip())},
                        conf=conf, ref=rec.ref, fidelity=adapter.fidelity)
        reqs.append(r)
        for k in ("text", *canon.keys(), *([] if synthetic else ["uid"])):
            coverage[k] += 1
        for k, c in conf.items():
            conf_count[k][c.value] += 1
        uid_to_mid.setdefault(uid, mid)
        mid_to_uid[mid] = uid
        native_to_mid[native] = mid
        pending_parent.append((r, rec.parent_native_id, parent_ref))

    claimed_keys.update(claimed_all)

    # parents: adapter-provided hierarchy first, then a profile 'parent' column
    for r, pn, pu in pending_parent:
        if pn and pn in native_to_mid:
            r.parent_mid = native_to_mid[pn]
        elif pu and pu in uid_to_mid:
            r.parent_mid = uid_to_mid[pu]

    links: list[Link] = []
    for rl in raw_links:
        s_mid, t_mid = native_to_mid.get(rl.source_native_id), native_to_mid.get(rl.target_native_id)
        links.append(Link(source_uid=mid_to_uid.get(s_mid or "", rl.source_native_id), target_uid=mid_to_uid.get(t_mid or "", rl.target_native_id),
                          kind=rl.kind, ref=rl.ref, source_mid=s_mid, target_mid=t_mid))
    for lr in profile.links:
        links += _links_from_column(lr, reqs, raws, uid_to_mid)

    dups = [u for u, c in Counter(r.uid for r in reqs).items() if c > 1]
    if dups:
        warnings.append(f"{len(dups)} duplicate UIDs (kept as separate records with distinct MIDs): {dups[:5]}")
    mids = Counter(r.mid for r in reqs)
    clash = [m for m, c in mids.items() if c > 1]
    if clash:
        warnings.append(f"{len(clash)} MID collisions: two records share the same native ID; check the profile's uid rule")
    unresolved = sum(1 for l in links if l.target_mid is None)
    if unresolved:
        warnings.append(f"{unresolved} links point outside this import (kept by UID)")
    if adapter.fidelity.value == "extracted":
        warnings.append("records were EXTRACTED from prose: every one needs human verification against its locator")

    seen_keys = {k for r in raws if profile.containers is None or r.ref.container in profile.containers
                 for k in r.fields if not k.startswith("_")}
    report = {
        "adapter": adapter.name, "fidelity": adapter.fidelity.value, "profile": profile.name, "profile_proposed": profile.proposed,
        "revision": adapter.revision(src), "raw_records": len(raws), "requirements": len(reqs), "rejected": len(rejected),
        "filtered_out": dict(filtered), "links": len(links), "coverage": dict(coverage),
        "confidence": {k: dict(v) for k, v in conf_count.items()},
        "unclaimed_fields": sorted(seen_keys - claimed_keys), "warnings": warnings,
        "invariant_ok": len(raws) == len(reqs) + len(rejected) + sum(filtered.values()),
    }
    return IngestResult(requirements=reqs, links=links, rejected=rejected, report=report)


def _links_from_column(lr: LinkRule, reqs: list[Requirement], raws: list[RawRecord], uid_to_mid: dict[str, str]) -> list[Link]:
    by_ref = {(r.ref.container, r.ref.locator): r for r in reqs}
    out: list[Link] = []
    for rec in raws:
        r = by_ref.get((rec.ref.container, rec.ref.locator))
        v = rec.fields.get(lr.src)
        if r is None or not v:
            continue
        for tgt in [t for t in re.split(lr.split, str(v)) if t]:
            a, b = (r.uid, tgt) if lr.direction == "out" else (tgt, r.uid)
            out.append(Link(source_uid=a, target_uid=b, kind=lr.kind, ref=rec.ref,
                            source_mid=uid_to_mid.get(a), target_mid=uid_to_mid.get(b)))
    return out
