"""Declarative mapping: raw fields -> canonical fields, as DATA (YAML), not code.

A profile is what makes the app work with data it has never seen: the user (or an AI that only PROPOSES)
fills in one small file; a human confirms it; it is saved with the project and replayed on re-import.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

from .adapter import Container, Discovery
from .model import Conf
from .normalise import strip_markup

CANONICAL = ["uid", "text", "rationale", "verification", "allocation", "owner", "baseline", "status", "parent"]


@dataclass
class Rule:
    src: list[str] = field(default_factory=list)        # 'from': first non-empty wins
    join: list[str] = field(default_factory=list)       # alternative: concatenate these with sep
    sep: str = " "
    regex: str | None = None                            # capture group 1 of this pattern
    map: dict[str, str] = field(default_factory=dict)   # value translation (case-insensitive keys)
    default: str | None = None
    const: str | None = None
    strip_markup: bool = False
    conf: Conf | None = None                            # explicit label, e.g. from the proposer
    why: str = ""                                       # human-readable reason, shown in the Import screen


@dataclass
class LinkRule:
    kind: str
    src: str                                            # column holding target UIDs
    split: str = r"[,;\s]+"
    direction: str = "out"                              # out: this -> target; in: target -> this


@dataclass
class Profile:
    name: str
    adapter: str
    containers: list[str] | None = None                 # None = all containers
    where: dict[str, Any] = field(default_factory=dict)  # row filter: {field: value | [values] | {regex: ..} | {not_empty: true}}
    fields: dict[str, Rule] = field(default_factory=dict)
    links: list[LinkRule] = field(default_factory=list)
    namespace: str = ""                                 # MID namespace, e.g. project key: keep stable across re-imports
    proposed: bool = False                              # True until a human confirms

    # ---- (de)serialisation -------------------------------------------------------------------
    @staticmethod
    def from_yaml(text: str) -> "Profile":
        d = yaml.safe_load(text)
        rules = {}
        for k, v in (d.get("fields") or {}).items():
            v = v if isinstance(v, dict) else {"from": v}
            frm = v.get("from", [])
            rules[k] = Rule(
                src=[frm] if isinstance(frm, str) else list(frm), join=list(v.get("join", [])), sep=v.get("sep", " "),
                regex=v.get("regex"), map=v.get("map", {}) or {}, default=v.get("default"), const=v.get("const"),
                strip_markup=bool(v.get("strip_markup", False)),
                conf=Conf(v["conf"]) if v.get("conf") else None, why=v.get("why", ""))
        links = [LinkRule(kind=l["kind"], src=l["from"], split=l.get("split", r"[,;\s]+"), direction=l.get("direction", "out"))
                 for l in d.get("links", [])]
        return Profile(name=d["profile"], adapter=d["adapter"], containers=d.get("containers"), where=d.get("where", {}) or {},
                       fields=rules, links=links, namespace=d.get("namespace", ""), proposed=bool(d.get("proposed", False)))

    def to_yaml(self) -> str:
        out: dict[str, Any] = {"profile": self.name, "adapter": self.adapter, "namespace": self.namespace, "proposed": self.proposed}
        if self.containers is not None:
            out["containers"] = self.containers
        if self.where:
            out["where"] = self.where
        out["fields"] = {}
        for k, r in self.fields.items():
            e: dict[str, Any] = {}
            if r.src:
                e["from"] = r.src if len(r.src) > 1 else r.src[0]
            if r.join:
                e["join"] = r.join
                e["sep"] = r.sep
            for attr in ("regex", "default", "const"):
                if getattr(r, attr) is not None:
                    e[attr] = getattr(r, attr)
            if r.map:
                e["map"] = r.map
            if r.strip_markup:
                e["strip_markup"] = True
            if r.conf:
                e["conf"] = r.conf.value
            if r.why:
                e["why"] = r.why
            out["fields"][k] = e
        if self.links:
            out["links"] = [{"kind": l.kind, "from": l.src, "split": l.split, "direction": l.direction} for l in self.links]
        return yaml.safe_dump(out, sort_keys=False, allow_unicode=True)


# ---- applying a rule -------------------------------------------------------------------------
def _get(raw: dict[str, Any], key: str) -> str:
    v = raw.get(key)
    if v is None:
        return ""
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v).strip()


def apply_rule(rule: Rule, raw: dict[str, Any]) -> tuple[str, Conf, list[str]]:
    """Return (value, confidence, raw keys consumed). Empty value means 'not present'."""
    used: list[str] = []
    val = ""
    if rule.join:
        parts = [_get(raw, k) for k in rule.join]
        used += [k for k, p in zip(rule.join, parts) if p]
        val = rule.sep.join(p for p in parts if p)
    else:
        for k in rule.src:
            v = _get(raw, k)
            if v:
                val, used = v, [k]
                break
    transformed = bool(rule.join)
    if val and rule.strip_markup:
        val, transformed = strip_markup(val), True
    if val and rule.regex:
        m = re.search(rule.regex, val)
        val, transformed = (m.group(1) if m and m.groups() else (m.group(0) if m else "")), True
    if val and rule.map:
        lowered = {k.lower(): v for k, v in rule.map.items()}
        val, transformed = lowered.get(val.lower(), val), True
    if not val and rule.const is not None:
        return rule.const, Conf.LOW, used
    if not val and rule.default is not None:
        return rule.default, Conf.LOW, used
    conf = rule.conf or (Conf.HIGH if transformed else Conf.EXACT)
    return val, conf, used


def row_matches(where: dict[str, Any], raw: dict[str, Any]) -> bool:
    for key, cond in where.items():
        v = _get(raw, key)
        if isinstance(cond, dict):
            if "regex" in cond and not re.search(cond["regex"], v):
                return False
            if cond.get("not_empty") and not v:
                return False
        elif isinstance(cond, list):
            if v not in [str(c) for c in cond]:
                return False
        elif v != str(cond):
            return False
    return True


# ---- the proposer: deterministic heuristics first; an AI may refine, a human must confirm --------
def _key(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# Header-name patterns on the normalised key (lower-case letters and digits only). Ordered: first group = strongest.
PATTERNS: dict[str, str] = {
    "uid": r"^(id|uid|key|ref|reference|number|tag|shortname|foreignid|reqifforeignid|objectidentifier|absolutenumber|objectnumber|leadid)$"
           r"|^(req|rqmt|spec|srs|sss|ssts|sys)\w*(id|uid|no|num|number|key|ref)$|^(req|reqno|reqnum)$",
    "rationale": r"rationale|justification|^why$|^reason$|^comments?$|^notes?$",
    "verification": r"verif|vmethod|testmethod|^(method|tia|tiad|vm)$",
    "allocation": r"alloc|^(subsystem|component|system|element|assignedto)$",
    "owner": r"owner|responsible|^(author|createdby|team|ipt)$",
    "baseline": r"baseline|^(release|version|issue|revision)$",
    "status": r"status|^(state|lifecycle|approval)$",
    "parent": r"^parent|derivedfrom",
}
HUMAN_ID = re.compile(r"^[A-Za-z][A-Za-z0-9]*([-_./][A-Za-z0-9]+)+$")
VERIF_WORDS = {"t", "a", "i", "d", "test", "analysis", "inspection", "demonstration", "demo", "review"}


def propose_profile(disc: Discovery, adapter: str, name: str = "proposed") -> Profile:
    """Pick requirement-like containers and the best column per canonical field, with a label and a reason for each."""
    prof = Profile(name=name, adapter=adapter, proposed=True)
    chosen: list[Container] = []
    for c in disc.containers:
        best = max((f for f in c.fields), key=lambda f: _text_score(f), default=None)
        if best and _text_score(best) >= 0.35:
            chosen.append(c)
    prof.containers = [c.name for c in chosen]
    text_cols: list[str] = []
    for c in chosen:
        best = max(c.fields, key=_text_score)
        text_cols.append(best.name)
    if text_cols:
        top = max((f for c in chosen for f in c.fields if f.name in text_cols), key=_text_score)
        conf = Conf.HIGH if top.modal_ratio >= 0.6 else Conf.MEDIUM
        prof.fields["text"] = Rule(src=list(dict.fromkeys(text_cols)), strip_markup=True, conf=conf,
                                   why=f"{top.modal_ratio:.0%} of '{top.name}' values contain shall/should/will/must/may; mean length {top.mean_len:.0f}")
    claimed = set(text_cols)
    for canon in ("uid", "rationale", "verification", "allocation", "owner", "baseline", "status", "parent"):
        cols: list[str] = []
        whys: list[str] = []
        score_best = 0.0
        for c in chosen:
            cand = [(f, _field_score(canon, f)) for f in c.fields if f.name not in claimed or canon == "uid"]
            cand = [(f, s) for f, s in cand if s > 0]
            if cand:
                f, s = max(cand, key=lambda t: t[1])
                if f.name not in cols:
                    cols.append(f.name)
                    whys.append(f"column '{f.name}' ({_why(canon, f)})")
                score_best = max(score_best, s)
        if cols:
            prof.fields[canon] = Rule(src=cols, conf=Conf.HIGH if score_best >= 1.5 else Conf.MEDIUM, why="; ".join(whys))
            claimed.update(cols)
    return prof


def _text_score(f) -> float:
    return 0.6 * f.modal_ratio + 0.4 * min(f.mean_len / 120.0, 1.0) * (1 if f.non_empty > 0.5 else 0.3)


def _field_score(canon: str, f) -> float:
    k = _key(f.name)
    name_hit = bool(re.search(PATTERNS[canon], k))
    score = 1.0 if name_hit else 0.0
    looks_like_id = bool(f.samples) and all(HUMAN_ID.match(x) for x in f.samples)
    if canon == "uid":
        ok_shape = f.unique >= 0.95 and f.non_empty >= 0.95 and f.mean_len <= 40
        if name_hit and ok_shape:
            score += 0.7
        if name_hit and looks_like_id:
            score += 0.3                      # prefers 'Object Identifier' (SRS-12) over 'Absolute Number' (12)
        if not name_hit and ok_shape and looks_like_id:
            score = 0.8                       # value-shape fallback: nothing in the name, but every sample is an ID
    elif canon == "verification":
        vals = {x.lower() for x in f.samples}
        if vals and vals <= VERIF_WORDS:
            score = max(score + 0.7, 1.0)
    elif canon in ("rationale", "owner", "allocation", "baseline", "status", "parent"):
        if f.non_empty < 0.05:
            return 0.0
    return score


def _why(canon: str, f) -> str:
    named = bool(re.search(PATTERNS[canon], _key(f.name)))
    return f"{'name matches' if named else 'values look like'} '{canon}'; {f.non_empty:.0%} filled, {f.unique:.0%} unique"
