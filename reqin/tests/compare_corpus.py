"""A made-up, labelled corpus for the comparison engine, and the measurement of the engine against it.

WHAT THIS IS. Requirement sentences generated from templates, each in several wordings, plus *traps*: a requirement derived from another by changing exactly one thing (a number, a unit, a negation, a
modal, the subject, the condition ...). The right answers are known because the generator wrote them. The generator was written by the person who wrote the engine, and the synonym and abbreviation lists
below overlap with the engine's vocabulary only in part on purpose (the rest is reported as "outside the vocabulary").

WHAT IT IS NOT. A measure of how the engine does on real requirements. It shows that the rules do what they say and that the traps are caught. No number from here may be shown on a screen as if it
were a property of a real requirement set. The expected type of each trap is the generator author's reading of the taxonomy in the research report, written independently of the engine's code.

No thresholds were tuned on this corpus (see docs/COMPARE_RESULTS.md for the one value that was changed before any measurement, and why).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field, replace
from itertools import combinations
from typing import Any

SEED = 20241015

SUBJECTS = ["pump controller", "battery pack", "conveyor drive", "lift controller", "thermostat", "data logger", "robot arm", "ground station", "lab analyser", "water heater",
            "gate actuator", "cooling fan", "display panel", "radio module", "charger", "alarm unit", "door lock", "flow meter", "pressure regulator", "inverter"]
# verb, object, past participle, synonym tags used by the SYN transform
ACTIONS = [("start", "the motor", "started"), ("close", "the supply valve", "closed"), ("open", "the access door", "opened"), ("report", "the measured temperature", "reported"),
           ("apply", "the brake", "applied"), ("sound", "the alarm", "sounded"), ("reset", "the event counter", "reset"), ("store", "the calibration data", "stored"),
           ("transmit", "the status message", "transmitted"), ("enable", "the heater", "enabled"), ("disable", "the output stage", "disabled"), ("acknowledge", "each command", "acknowledged"),
           ("record", "each fault", "recorded"), ("display", "the diagnostic information", "displayed"), ("retrieve", "the configuration data", "retrieved"),
           ("stop", "the conveyor", "stopped"), ("send", "the alarm message", "sent"), ("generate", "the summary report", "generated"), ("verify", "the supply voltage", "verified"),
           ("initialise", "the sensor interface", "initialised")]
QUANTITIES = [  # comparator symbol, value, unit, alternative spelling of the same quantity (value, unit) or None
    ("<=", 5, "s", (5000, "ms")), ("<=", 2, "min", (120, "s")), ("<=", 10, "ms", None), ("<=", 40, "kg", (40000, "g")), ("<=", 3, "m", (3000, "mm")), ("<=", 100, "mm", None),
    (">=", 99.9, "%", None), (">=", 10, "l/min", None), (">=", 50, "Hz", (0.05, "kHz")), (">=", 2, "h", (120, "min")), (">=", 28, "V", (28000, "mV")), ("=", 12, "V", None),
    ("=", 20, "ms", (0.02, "s")), ("=", 5, "bar", (500, "kPa")), ("<=", 80, "degrees C", None), (">=", 1, "kW", (1000, "W")), ("<", 15, "A", (15000, "mA")), (">", 200, "kPa", None),
]
COMPARATOR_WORDS = {"<=": ["within", "no more than", "at most", "not more than", "up to"], ">=": ["at least", "no less than", "a minimum of", "not less than"],
                    "": [""], "=": ["exactly", "equal to"], "<": ["less than", "below"], ">": ["more than", "above", "greater than"]}
CONDITIONS = [("when", "the level is low"), ("if", "the supply fails"), ("while", "the door is open"), ("after", "power-on"), ("during", "startup"), ("when", "a fault is detected"),
              ("if", "the temperature exceeds 80 degrees C"), ("when", "the operator presses reset")]
# the corpus's own synonym and abbreviation lists. 'in' means the engine's default vocabulary has the pair, 'out' that it does not (written down BEFORE looking at the engine's list lines).
SYN_IN = {"transmit": "send", "send": "transmit", "display": "show", "enable": "activate", "record": "log", "retrieve": "fetch", "verify": "check", "generate": "produce", "initialise": "initialize"}
SYN_OUT = {"start": "begin", "stop": "halt", "close": "shut", "sound": "raise", "report": "indicate", "apply": "engage", "reset": "zero", "store": "save", "acknowledge": "accept",
           "open": "unlock", "disable": "inhibit"}
ABBR_IN = {"message": "msg", "configuration": "config", "information": "info", "command": "cmd"}
ABBR_OUT = {"temperature": "temp", "diagnostic": "diag.", "calibration": "cal", "supply": "supp", "measured": "meas"}
NUM_WORDS = {1: "one", 2: "two", 3: "three", 5: "five", 10: "ten", 12: "twelve", 20: "twenty", 28: "twenty-eight", 40: "forty", 50: "fifty"}
RELATIONS = [("pump", "feed", "tank"), ("charger", "power", "battery pack"), ("fan", "cool", "inverter"), ("controller", "monitor", "heater"), ("logger", "calibrate", "sensor"), ("gateway", "forward", "radio module")]


@dataclass(frozen=True)
class Meaning:
    """What a requirement says, as data. Two requirements with equal Meaning are equivalent."""
    subject: str
    action: int                       # index into ACTIONS, or -1 for a relation
    relation: int = -1
    modal: str = "shall"
    negated: bool = False
    qty: tuple | None = None          # (comparator, value, unit) or None
    cond: tuple | None = None         # (trigger, text) or None
    qualifier: str = ""
    ref: str = ""                     # "REQ-12" for the 'shall comply with' meanings


@dataclass
class Req:
    mid: str
    uid: str
    text: str
    meaning: Meaning
    transforms: tuple[str, ...]
    outside_vocab: bool
    trap_of: str | None = None
    trap_kind: str = ""
    expected: str = ""                # for a trap: the type the generator says the pair (base, trap) has
    direction: str | None = None      # 'base' or 'trap' for SUBSUMES: who is stricter


def _num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _qty_phrase(q: tuple, cmp_word: str | None = None, alt: bool = False, words: bool = False, rng: random.Random | None = None) -> str:
    cmp_, v, unit = q
    spec = next((x for x in QUANTITIES if x[0] == cmp_ and x[1] == v and x[2] == unit), None)
    if alt and spec and spec[3]:
        v, unit = spec[3]
    w = cmp_word if cmp_word is not None else COMPARATOR_WORDS[cmp_][0]
    n = NUM_WORDS.get(v) if (words and isinstance(v, (int, float)) and unit in ("s", "min", "h")) else None
    if n:
        unit = {"s": "seconds", "min": "minutes", "h": "hours"}[unit]
    return f"{w} {n or _num(v)} {unit}".strip()


def render(m: Meaning, *, style: str = "base", cmp_word: str | None = None, alt_unit: bool = False, num_words: bool = False, modal_word: str | None = None, syn: str = "",
           abbr: str = "", noise: bool = False, det: bool = False) -> tuple[str, bool]:
    """One wording of a meaning. Returns (text, uses_words_outside_the_engine_vocabulary)."""
    modal = modal_word or m.modal
    if m.action >= 0:
        verb, obj, pp = ACTIONS[m.action][0], ACTIONS[m.action][1], ACTIONS[m.action][2]
    else:
        a, vb, b = RELATIONS[m.relation]
        verb, obj, pp = vb, f"the {b}", vb + "ed"
    outside = False
    if syn == "in" and verb in SYN_IN:
        verb = SYN_IN[verb]
        pp = {"send": "sent"}.get(verb, verb + ("d" if verb.endswith("e") else "ed"))
    elif syn == "out" and verb in SYN_OUT:
        verb = SYN_OUT[verb]
        pp = verb + ("d" if verb.endswith("e") else "ed")
        outside = True
    subj = RELATIONS[m.relation][0] if m.relation >= 0 else m.subject
    neg = " not" if m.negated else ""
    q = _qty_phrase(m.qty, cmp_word, alt_unit, num_words) if m.qty else ""
    cond = f"{m.cond[0]} {m.cond[1]}" if m.cond else ""
    qual = (" " + m.qualifier) if m.qualifier else ""
    ref = f" with {m.ref}" if m.ref else ""
    if m.ref:
        text_active = f"The {subj} {modal}{neg} comply{ref}"
    else:
        text_active = f"The {subj} {modal}{neg} {verb} {obj}{qual}"
    if det:
        text_active = "A" + text_active[3:]
    tail = " ".join(x for x in (q,) if x)
    if style == "passive" and not m.ref and not m.negated:
        s = f"{obj[0].upper() + obj[1:]} {modal} be {pp} by the {subj}" + (f" {tail}" if tail else "")
        if m.qualifier:
            s = f"{obj[0].upper() + obj[1:]} {modal} be {pp} by the {subj}{qual}" + (f" {tail}" if tail else "")
    else:
        s = text_active + (f" {tail}" if tail else "")
    if m.cond:
        s = f"{cond[0].upper() + cond[1:]}, {s[0].lower() + s[1:]}" if style == "cond_first" else f"{s} {cond}"
    s += "."
    for k, v in ABBR_IN.items():
        if abbr == "in" and k in s:
            s = s.replace(k, v)
    for k, v in ABBR_OUT.items():
        if abbr == "out" and k in s:
            s = s.replace(k, v)
            outside = True
    if noise:
        s = "  " + s.replace(" ", "  ", 1).rstrip(".") + " "
    return s, outside


def _wordings(m: Meaning, rng: random.Random, k: int) -> list[tuple[str, tuple[str, ...], bool]]:
    """k distinct wordings of one meaning; the first is the plain one."""
    out = [(*render(m), ())]
    out = [(out[0][0], (), out[0][1])]
    seen = {out[0][0]}
    tries = 0
    while len(out) < k and tries < 40:
        tries += 1
        opts: dict[str, Any] = {}
        tags: list[str] = []
        pool = ["cond_first", "units", "comp", "modal", "passive", "abbr_in", "abbr_out", "syn_in", "syn_out", "numwords", "noise", "det"]
        for t in rng.sample(pool, rng.randint(1, 3)):
            if t == "cond_first" and m.cond:
                opts["style"] = "cond_first"
            elif t == "passive" and not m.negated and not m.ref and "style" not in opts:
                opts["style"] = "passive"
            elif t == "units" and m.qty:
                opts["alt_unit"] = True
            elif t == "comp" and m.qty:
                opts["cmp_word"] = rng.choice(COMPARATOR_WORDS[m.qty[0]])
            elif t == "modal" and m.modal == "shall":
                opts["modal_word"] = "must"
            elif t == "abbr_in":
                opts["abbr"] = "in"
            elif t == "abbr_out":
                opts["abbr"] = "out"
            elif t == "syn_in":
                opts["syn"] = "in"
            elif t == "syn_out":
                opts["syn"] = "out"
            elif t == "numwords" and m.qty:
                opts["num_words"] = True
            elif t == "noise":
                opts["noise"] = True
            elif t == "det":
                opts["det"] = True
            else:
                continue
            tags.append(t)
        if not tags:
            continue
        text, outside = render(m, **opts)
        if text in seen or text.strip() == out[0][0].strip():
            continue
        # the spoken form of a unit-converted or word-number wording is only a variant if the text really changed
        seen.add(text)
        out.append((text, tuple(sorted(tags)), outside))
    return out


def _stricter(cmp_: str, a: float, b: float) -> str | None:
    """Of two values under the same comparator, which one is stricter? 'a', 'b', or None when equal. Written separately from the engine's interval code."""
    if a == b:
        return None
    if cmp_ in ("<=", "<"):
        return "a" if a < b else "b"
    if cmp_ in (">=", ">"):
        return "a" if a > b else "b"
    return None


_BASE_OF = {"s": 1000.0, "ms": 1.0, "min": 60000.0, "h": 3600000.0, "kg": 1.0, "g": 0.001, "m": 1.0, "mm": 0.001, "kHz": 1e3, "Hz": 1.0, "V": 1.0, "mV": 1e-3, "kPa": 1e3, "bar": 1e5, "kW": 1e3, "W": 1.0,
            "A": 1.0, "mA": 1e-3}


def make_corpus(n_meanings: int = 150, seed: int = SEED) -> list[Req]:
    rng = random.Random(seed)
    meanings: dict[Meaning, None] = {}
    while len(meanings) < n_meanings:
        kind = rng.random()
        if kind < 0.10:
            i = rng.randrange(len(RELATIONS))
            m = Meaning(subject=RELATIONS[i][0], action=-1, relation=i, modal=rng.choice(["shall", "shall", "should"]), negated=False, qty=None, cond=rng.choice([None, None, rng.choice(CONDITIONS)]))
        elif kind < 0.16:
            m = Meaning(subject=rng.choice(SUBJECTS), action=-1, relation=-1, modal="shall", ref=f"REQ-{rng.randint(10, 99)}")
        else:
            m = Meaning(subject=rng.choice(SUBJECTS), action=rng.randrange(len(ACTIONS)), modal=rng.choice(["shall", "shall", "shall", "should"]), negated=rng.random() < 0.12,
                        cond=rng.choice([None, None, rng.choice(CONDITIONS)]))
            if rng.random() < 0.6:
                m = replace(m, qty=rng.choice(QUANTITIES)[:3])
        # a requirement must not say the same twice: skip meanings that collide on (subject, action, relation) and everything else
        meanings.setdefault(m, None)
    reqs: list[Req] = []
    n = 0

    def add(text: str, m: Meaning, tr: tuple[str, ...], outside: bool, **kw: Any) -> Req:
        nonlocal n
        n += 1
        r = Req(f"m_{n:05d}", f"SYN-{n:05d}", text, m, tr, outside, **kw)
        reqs.append(r)
        return r

    base_ids: dict[Meaning, str] = {}
    for m in sorted(meanings, key=repr):
        for text, tr, outside in _wordings(m, rng, rng.randint(2, 6)):
            r = add(text, m, tr, outside)
            base_ids.setdefault(m, r.mid)
    # traps: each derived from a meaning by one change. The expected type is the generator author's reading of the taxonomy, reasoned here on plain numbers, not with the engine's interval code.
    for m in sorted(meanings, key=repr):
        traps: list[tuple[str, Meaning, str, str | None]] = []   # kind, meaning, expected type, which one is stricter ('base' or 'trap') for SUBSUMES
        if m.qty:
            c, v, u = m.qty
            other = v * 10 if v < 500 else v / 10
            if c in ("<=", "<", ">=", ">"):
                traps.append(("number", replace(m, qty=(c, other, u)), "SUBSUMES", "base" if _stricter(c, v, other) == "a" else "trap"))
            else:
                traps.append(("number", replace(m, qty=(c, other, u)), "CONFLICT", None))
            small = {"s": "ms", "min": "s", "kg": "g", "m": "mm", "kHz": "Hz", "V": "mV", "h": "min", "kPa": "bar"}.get(u)
            if small and u in _BASE_OF and small in _BASE_OF:
                nb, ob = v * _BASE_OF[u], v * _BASE_OF[small]
                if c == "=":
                    traps.append(("unit", replace(m, qty=(c, v, small)), "CONFLICT", None))
                else:
                    traps.append(("unit", replace(m, qty=(c, v, small)), "SUBSUMES", "base" if _stricter(c, nb, ob) == "a" else "trap"))
            if c == ">=":
                traps.append(("bounds", replace(m, qty=("<=", v * 4, u)), "COMPLEMENTARY", None))
                traps.append(("bounds-conflict", replace(m, qty=("<=", v / 4, u)), "CONFLICT", None))
            if c == "<=":
                traps.append(("bounds", replace(m, qty=(">=", v / 4, u)), "COMPLEMENTARY", None))
            traps.append(("unstated", replace(m, qty=("", v, u)), "VARIANT", None))
        elif m.action >= 0 and not m.ref:
            spec = rng.choice([x for x in QUANTITIES if x[0] in ("<=", "<")])
            traps.append(("extra-constraint", replace(m, qty=spec[:3]), "SUBSUMES", "trap"))
        if not m.ref and m.relation < 0:
            traps.append(("negation", replace(m, negated=not m.negated), "CONFLICT", None))
            traps.append(("modal", replace(m, modal="should" if m.modal == "shall" else "shall"), "VARIANT", None))
            traps.append(("subject", replace(m, subject=next(x for x in SUBJECTS if x != m.subject and x[0] != m.subject[0])), "UNRELATED", None))
            traps.append(("qualifier", replace(m, qualifier=rng.choice(["gradually", "automatically", "twice", "manually"])), "NOT_EQUIVALENT", None))
            traps.append(("verb", replace(m, action=(m.action + 3) % len(ACTIONS)), "NOT_EQUIVALENT", None))
            if m.cond:
                traps.append(("condition-dropped", replace(m, cond=None), "SUBSUMES", "trap"))
                traps.append(("condition-changed", replace(m, cond=next(x for x in CONDITIONS if x != m.cond)), "VARIANT", None))
            else:
                traps.append(("condition-added", replace(m, cond=rng.choice(CONDITIONS)), "SUBSUMES", "base"))
        if m.relation >= 0:
            traps.append(("swapped", m, "UNRELATED", None))
        if m.ref:
            traps.append(("other-reference", replace(m, ref=f"REQ-{int(m.ref[4:]) + 1}"), "NOT_EQUIVALENT", None))
        if m.negated:
            # "shall not ... below 0" forbids the values below 0: under a negation the direction of a bound is reversed, so the author's reading is that only 'the numbers differ' can be said
            traps = [(k, t, "VARIANT" if k in ("number", "unit", "bounds", "bounds-conflict", "extra-constraint") else e, None if k in ("number", "unit", "bounds", "bounds-conflict", "extra-constraint") else w)
                     for k, t, e, w in traps]
        rng.shuffle(traps)
        for kind, tm, expected, who in traps[:4]:
            if tm in meanings and kind != "swapped":
                continue
            if kind == "swapped":
                a_, vb, b_ = RELATIONS[m.relation]
                text = f"The {b_} {m.modal} {vb} the {a_}" + (f" {m.cond[0]} {m.cond[1]}" if m.cond else "") + "."
                add(text, Meaning(b_, -1, m.relation, m.modal, False, None, m.cond), (), False, trap_of=base_ids[m], trap_kind=kind, expected=expected)
                continue
            for text, tr, outside in _wordings(tm, rng, rng.randint(1, 2)):
                add(text, tm, tr, outside, trap_of=base_ids[m], trap_kind=kind, expected=expected, direction=who)
    return reqs


def as_dataset_rows(corpus: list[Req]) -> list[dict[str, Any]]:
    from reqin.normalise import normalise_text
    return [{"mid": r.mid, "uid": r.uid, "uid_synthetic": False, "text": r.text, "norm_text": normalise_text(r.text), "fields": {}, "parent_mid": None} for r in corpus]


# ------------------------------------------------------------------------------------------------------ measurement
def evaluate(corpus: list[Req], res: Any) -> dict[str, Any]:
    by_mid = {r.mid: r for r in corpus}
    cluster_of = {m["mid"]: c["cid"] for c in res.clusters for m in c["members"]}
    truth_pairs = {(a.mid, b.mid) for a, b in combinations(corpus, 2) if a.meaning == b.meaning}
    pred_pairs = {tuple(sorted((a["mid"], b["mid"]))) for c in res.clusters for a, b in combinations(c["members"], 2)}
    tp = truth_pairs & pred_pairs
    fp = pred_pairs - truth_pairs
    fn = truth_pairs - pred_pairs
    prec = len(tp) / len(pred_pairs) if pred_pairs else 1.0
    rec = len(tp) / len(truth_pairs) if truth_pairs else 1.0
    # B-cubed
    truth_group: dict[Meaning, set[str]] = {}
    for r in corpus:
        truth_group.setdefault(r.meaning, set()).add(r.mid)
    cl_members: dict[str, set[str]] = {}
    for c in res.clusters:
        cl_members[c["cid"]] = {m["mid"] for m in c["members"]}
    bp = br = 0.0
    for r in corpus:
        mine = cl_members.get(cluster_of.get(r.mid, ""), {r.mid})
        truth = truth_group[r.meaning]
        both = len(mine & truth)
        bp += both / len(mine)
        br += both / len(truth)
    bp, br = bp / len(corpus), br / len(corpus)
    # recall by transformation: of the pairs (plain wording, variant) of one meaning
    plain = {r.meaning: r for r in corpus if not r.transforms and not r.trap_of}
    per: dict[str, list[int]] = {}
    for r in corpus:
        p = plain.get(r.meaning)
        if r.trap_of or not r.transforms or p is None or p.mid == r.mid:
            continue
        hit = cluster_of.get(r.mid) is not None and cluster_of.get(r.mid) == cluster_of.get(p.mid)
        keys = list(r.transforms) + (["(any outside the vocabulary)"] if r.outside_vocab else ["(none outside the vocabulary)"])
        for t in keys:
            per.setdefault(t, [0, 0])
            per[t][1] += 1
            per[t][0] += int(hit)
    # typed pairs on traps: engine's answer for (base wording, trap wording). Engine pair lines name groups of requirements.
    where: dict[str, list[dict]] = {}
    for p in res.pairs:
        for ma in p["a"]["mids"]:
            where.setdefault(ma, []).append(p)
        for mb in p["b"]["mids"]:
            where.setdefault(mb, []).append(p)
    typed: dict[str, dict[str, list[int]]] = {}     # trap kind -> {'plain' | 'varied': [right, total]}
    skipped_outside = 0
    wrong: list[dict[str, Any]] = []
    for r in corpus:
        if not r.trap_of:
            continue
        if r.outside_vocab:
            skipped_outside += 1                        # a trap worded with words the vocabulary does not hold cannot be typed; it is counted under recall, not here
            continue
        base = by_mid[r.trap_of]
        got = "UNRELATED"
        direction = None                  # who the engine says is stricter, as 'base' or 'trap'
        if cluster_of.get(r.mid) is not None and cluster_of.get(r.mid) == cluster_of.get(base.mid):
            got = "EQUIVALENT"
        else:
            for p in where.get(r.mid, []):
                a_, b_ = set(p["a"]["mids"]), set(p["b"]["mids"])
                if (base.mid in a_ and r.mid in b_) or (base.mid in b_ and r.mid in a_):
                    got = p["type"]
                    if p["direction"]:
                        trap_side = "a" if r.mid in a_ else "b"
                        direction = "trap" if p["direction"] == trap_side else "base"
                    break
        exp = r.expected
        ok = (got != "EQUIVALENT") if exp == "NOT_EQUIVALENT" else (got == exp and (exp != "SUBSUMES" or direction == r.direction))
        cell = typed.setdefault(r.trap_kind, {}).setdefault("varied" if r.transforms else "plain", [0, 0])
        cell[0] += int(ok)
        cell[1] += 1
        if not ok:
            wrong.append({"kind": r.trap_kind, "expected": exp + (f" ({r.direction} stricter)" if r.direction else ""), "got": got + (f" ({direction} stricter)" if direction else ""),
                          "base": base.text.strip(), "trap": r.text.strip(), "transforms": list(r.transforms)})
    false_merges = [{"a": by_mid[a].text.strip(), "b": by_mid[b].text.strip(), "kind": by_mid[a].trap_kind or by_mid[b].trap_kind} for a, b in sorted(fp)]
    return {"requirements": len(corpus), "meanings": len(truth_group), "truth_pairs": len(truth_pairs), "pred_pairs": len(pred_pairs), "tp": len(tp), "fp": len(fp), "fn": len(fn),
            "precision": prec, "recall": rec, "bcubed_precision": bp, "bcubed_recall": br, "recall_by_transform": {k: tuple(v) for k, v in sorted(per.items())},
            "typed": typed, "traps_outside_vocabulary": skipped_outside, "wrong_typed": wrong, "false_merges": false_merges, "missed_equivalents": [(by_mid[a].text.strip(), by_mid[b].text.strip(), by_mid[a].transforms + by_mid[b].transforms) for a, b in sorted(fn)]}
