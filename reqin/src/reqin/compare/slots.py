"""What is in a requirement: subject, modal, polarity, conditions, quantities, and the plain words that are left, each with where it is in the text.

Written rules only (regular expressions and word lists), no model. The pieces are cut out of `norm_text` in this order, and the order matters:

1. quantities (so that "not exceed 5 kg" is one bound and not a negation, and a comma inside "1,000" is not a clause break)
2. a leading condition: "When X, ..." up to the first comma
3. the first modal (shall, should, will, may, must) and a "not" or "never" straight after it
4. a trailing condition: "... when X", "... after X", up to the end of the sentence
5. what is left before the modal is the subject; what is left after it is the predicate

A requirement with no modal, or with several, is still compared (as written), and says so.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any

from .quantities import Quantity, find_quantities
from .vocabulary import Vocabulary

MODAL_CLASS = {"shall": "mandatory", "must": "mandatory", "should": "goal", "will": "fact", "may": "optional", "": "none"}
_MODAL = re.compile(r"\b(shall|should|will|may|must)\b", re.I)
_LEAD = re.compile(r"^\s*(if|when|whenever|while|during|upon|after|before|once|unless|in the event of|in the event that|in case of|in case|on|at(?!\s+(?:least|most|a\s+minimum|a\s+maximum)\b)|following|prior to|until|as soon as|where)\b", re.I)
_TRAIL = re.compile(r"\b(when|whenever|if|while|unless|during|upon|after|before|once|until|as soon as|in the event of|in the event that|in case of|in case|following|prior to|where)\b", re.I)
_DET = re.compile(r"\b(?:the|a|an)\b", re.I)
_NEG_AFTER_MODAL = re.compile(r"\s+(not|never|no longer)\b", re.I)
_TOKEN = re.compile(r"[^\W_]+(?:[-_/.'’][^\W_]+)*")
# A capital A is the article only at the start of a clause or after one of these words ("when A pump stops"); anywhere else ("Pump A shall start") it names something and is kept as "A".
_BEFORE_ARTICLE = frozenset("""shall should will may must not never be is are been being of to in for with by from on at as than when whenever if while unless until after before once upon during
and or but per via into onto over under through within without between against among around whether that which who where then also each every no""".split())
_CLAUSE_PUNCT = re.compile(r"[,;:.()\[\]]")
_TRIGGER_CANON = {"whenever": "when", "in the event of": "if", "in the event that": "if", "in case of": "if", "in case": "if", "prior to": "before"}
# the plain passive "shall be <participle> by <agent>" is turned into the active form, which needs the verb the participle comes from. Regular participles (-ed) are handled by the stemmer;
# these are the common irregular ones. A participle not on this list is not recognised as passive, and the requirement is compared as written.
_IRREGULAR_PARTICIPLES = {"sent": "send", "built": "build", "kept": "keep", "held": "hold", "made": "make", "shown": "show", "given": "give", "written": "write", "taken": "take",
                          "found": "find", "lost": "lose", "sold": "sell", "known": "know", "seen": "see", "done": "do", "broken": "break", "chosen": "choose", "driven": "drive",
                          "spoken": "speak", "begun": "begin", "hidden": "hide", "stolen": "steal", "worn": "wear", "left": "leave", "forgotten": "forget",
                          "run": "run", "set": "set", "reset": "reset", "preset": "preset", "read": "read", "put": "put", "shut": "shut", "cut": "cut", "hit": "hit", "let": "let"}


def _loose(w: str) -> str:
    """A key as the search for similar requirements sees it: a plural is the singular ('pumps' and 'pump' are looked at together, though they are not merged)."""
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")) and w.isascii() and w.isalpha() else w


# "shall be placed by the door", "shall be calculated by dividing", "shall be disabled by default": the word after 'by' is a place, a method or a manner, not the one who acts, so the sentence is not turned
# into the active. A participle or a 'by' phrase that is not on these lists is still read as an agent, and a cluster that holds both a passive and an active wording says so.
_LOCATIVE_PARTICIPLES = frozenset({"placed", "located", "positioned", "situated", "mounted", "installed", "fitted", "stationed", "parked", "seated", "housed", "attached", "secured", "fixed",
                                   "laid", "hung", "stood", "sited", "anchored", "kept", "held", "set", "put"})
_NOT_AN_AGENT = frozenset({"default", "hand", "design", "definition", "reference", "convention", "means", "law", "contract", "itself", "themselves"})


def _agent_is_one_who_acts(participle: str, agent: list[str]) -> bool:
    lead = next((w for w in agent if w not in ("the", "a", "an")), "")
    gerund = agent[0].endswith("ing") and len(agent[0]) > 4          # "by dividing the load" (a method); "by the cooling fan" starts with 'the' and is an agent
    return participle not in _LOCATIVE_PARTICIPLES and not gerund and lead not in _NOT_AN_AGENT


def words(s: str) -> list[str]:
    out: list[str] = []
    prev_end, prev = 0, ""
    for m in _TOKEN.finditer(s):
        t = m.group(0)
        if t == "A" and prev and prev not in _BEFORE_ARTICLE and not _CLAUSE_PUNCT.search(s, prev_end, m.start()):
            out.append("A")                    # an identifier, not the article
        else:
            out.append(t.lower())
        prev_end, prev = m.end(), t.lower()
    return out


@dataclass
class Condition:
    trigger: str
    text: str
    start: int
    end: int
    key: tuple[str, ...]


@dataclass
class Slots:
    mid: str
    uid: str
    norm_text: str
    text_differs: bool
    subject_text: str = ""
    subject_span: tuple[int, int] | None = None
    subject_key: tuple[str, ...] = ()
    modal_text: str = ""
    modal_span: tuple[int, int] | None = None
    modal_class: str = "none"
    negated: bool = False
    negation_span: tuple[int, int] | None = None
    no_modal: bool = False
    compound: bool = False
    passive: bool = False
    conditions: list[Condition] = field(default_factory=list)
    quantities: list[Quantity] = field(default_factory=list)
    predicate_key: tuple[str, ...] = ()
    predicate_words: tuple[str, ...] = ()           # the words as written (lower case), for showing what differs
    exact: str = ""
    masked: tuple[str, ...] = ()
    raw_tokens: frozenset[str] = frozenset()
    empty: bool = False
    digest: str = ""

    @property
    def family(self) -> tuple[tuple[str, ...], tuple[str, ...]]:
        return (self.subject_key, self.predicate_key)

    def canon_tokens(self) -> frozenset[str]:
        """The words and slot kinds this requirement is found by when looking for similar ones: subject, predicate and condition words, and the kind of each number."""
        t = {"s:" + _loose(w) for w in self.subject_key} | {"p:" + _loose(w) for w in self.predicate_key}
        for c in self.conditions:
            t |= {"c:" + _loose(w) for w in c.key}
        for q in self.quantities:
            t.add("q:" + q.role + ":" + q.key_dim)
        return frozenset(t)

    def to_json(self) -> dict[str, Any]:
        def sp(x: tuple[int, int] | None) -> list[int] | None:
            return None if x is None else [x[0], x[1]]
        return {
            "mid": self.mid, "uid": self.uid, "span_in": "norm_text", "text_differs": self.text_differs,
            "subject": {"text": self.subject_text, "span": sp(self.subject_span), "key": list(self.subject_key)},
            "modal": {"text": self.modal_text, "span": sp(self.modal_span), "class": self.modal_class},
            "negated": self.negated, "negation_span": sp(self.negation_span),
            "passive": self.passive, "compound": self.compound, "no_modal": self.no_modal,
            "conditions": [{"trigger": c.trigger, "text": c.text, "span": [c.start, c.end], "key": list(c.key)} for c in self.conditions],
            "quantities": [{"raw": q.raw, "span": [q.start, q.end], "role": q.role, "value": q.value, "value_hi": q.value_hi, "unit": q.unit, "dimension": q.dimension,
                            "comparator": q.comparator, "interval": None if q.interval is None else [q.interval[0], q.interval[1]], "closed": None if q.interval is None else [q.interval[2], q.interval[3]],
                            "base_value": q.base, "tolerance": q.tolerance} for q in self.quantities],
            "predicate_key": list(self.predicate_key), "key_digest": self.digest,
        }


def _inside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(a <= pos < b for a, b in spans)


_COPULA_BEFORE = re.compile(r"\b(?:be|is|are|am|was|were|been|being)\s*$", re.I)


def _cut(text: str, lo: int, hi: int, spans: list[tuple[int, int]]) -> str:
    """text[lo:hi] with every span that lies in it removed (replaced by a space), and with the 'is' or 'be' that stood right in front of it: 'the mass shall be at least 12 kg' and 'the mass
    shall not exceed 12 kg' say the same thing about the same words, and the copula only joins the subject to the number."""
    out, p = [], lo
    for a, b in sorted(spans):
        if b <= lo or a >= hi:
            continue
        before = text[p:max(a, lo)]
        out.append(_COPULA_BEFORE.sub("", before))
        out.append(" ")
        p = min(b, hi)
    out.append(text[p:hi])
    return "".join(out)


def _keyify(tokens: list[str], v: Vocabulary) -> tuple[str, ...]:
    out = []
    for t in v.apply_phrases(tokens):
        c = v.canon(t)
        if c:
            out.append(c)
    return tuple(out)


# words that say which comes first: "the door opens and then the lid closes" is not "the lid closes and then the door opens"
_ORDER_WORDS = frozenset({"then", "before", "after", "once", "until", "followed", "next", "subsequently", "finally", "first", "second", "third", "afterwards", "later", "earlier", "previously", "thereafter"})


def _condition_key(tokens: list[str], v: Vocabulary) -> tuple[str, ...]:
    """The words of a condition. A list of conditions joined only by 'and' means the same in any order ('the lid is open and the rotor is spinning'), so those clauses are sorted;
    a condition that also contains 'or' is kept in the order written, because which 'and' binds which 'or' is not something to guess."""
    if "and" in tokens and "or" not in tokens and not _ORDER_WORDS.intersection(tokens):
        clauses, cur = [], []
        for t in tokens:
            if t == "and":
                clauses.append(cur)
                cur = []
            else:
                cur.append(t)
        clauses.append(cur)
        keyed = sorted(_keyify(c, v) for c in clauses if c)
        out: list[str] = []
        for k in keyed:
            out += list(k) + ["&"]
        return tuple(out[:-1])
    return _keyify(tokens, v)


def extract(norm_text: str, v: Vocabulary, mid: str = "", uid: str = "", text: str | None = None) -> Slots:
    t = norm_text
    sl = Slots(mid=mid, uid=uid, norm_text=t, text_differs=(text is not None and text != norm_text))
    qs = find_quantities(t)
    qspans = [(q.start, q.end) for q in qs]
    sl.exact = " ".join(words(t))
    sl.empty = not sl.exact
    # rung 2 material: the whole text as words, with each quantity as one placeholder
    sl.masked = tuple(w for w in words(_cut_with(t, qspans, " <q> ")) if w)
    sl.raw_tokens = frozenset(words(t))

    # 2. a leading condition
    rest_start = 0
    conds: list[tuple[str, int, int]] = []     # trigger, start, end (spans in t)
    lead = _LEAD.match(t)
    if lead:
        c = next((i for i in range(lead.end(), len(t)) if t[i] == "," and not _inside(i, qspans)), None)
        if c is not None:
            a = lead.start(1)
            conds.append((lead.group(1).lower(), a, c))
            rest_start = c + 1
        else:
            # no comma: "On reset the controller shall ...". The subject is taken to start at the last 'the', 'a' or 'an' before the modal (only if something stands between the trigger and it).
            mm = next((m for m in _MODAL.finditer(t, lead.end()) if not _inside(m.start(), qspans)), None)
            if mm:
                dets = [d for d in _DET.finditer(t, lead.end(), mm.start()) if t[lead.end():d.start()].strip()]
                if dets:
                    a = lead.start(1)
                    end = dets[-1].start()
                    while end > a and t[end - 1] == " ":
                        end -= 1
                    conds.append((lead.group(1).lower(), a, end))
                    rest_start = dets[-1].start()

    # 3. the first modal, and the word that negates it
    modal = None
    for m in _MODAL.finditer(t, rest_start):
        if not _inside(m.start(), qspans):
            modal = m
            break
    pred_start = rest_start
    if modal:
        sl.modal_text = modal.group(1).lower()
        sl.modal_span = (modal.start(), modal.end())
        sl.modal_class = MODAL_CLASS[sl.modal_text]
        pred_start = modal.end()
        n = _NEG_AFTER_MODAL.match(t, modal.end())
        if n and not _inside(n.start(1), qspans):
            sl.negated = True
            sl.negation_span = (n.start(1), n.end(1))
            pred_start = n.end(1)
        sl.compound = any(not _inside(m.start(), qspans) for m in _MODAL.finditer(t, pred_start))
    else:
        sl.no_modal = True

    # 4. a trailing condition
    trail_at = len(t)
    tm = next((m for m in _TRAIL.finditer(t, pred_start) if not _inside(m.start(), qspans)), None)
    if tm:
        end = len(t)
        while end > tm.start() and t[end - 1] in " .;":
            end -= 1
        conds.append((tm.group(1).lower(), tm.start(), end))
        trail_at = tm.start()

    # roles of quantities: those inside a condition belong to it
    for q in qs:
        q.role = "condition" if any(a <= q.start and q.end <= b for _, a, b in conds) else "main"
    sl.quantities = qs

    for trig, a, b in conds:
        cq = [s for s in qspans if a <= s[0] and s[1] <= b]
        body_start = a + len(trig)
        body = _cut(t, body_start, b, cq)
        trig_c = _TRIGGER_CANON.get(trig, trig)
        sl.conditions.append(Condition(trig_c, t[a:b], a, b, (trig_c,) + _condition_key(words(body), v)))

    # 5. subject and predicate
    cond_spans = [(a, b) for _, a, b in conds]
    subj_end = modal.start() if modal else rest_start
    subj_raw = words(_cut(t, rest_start, subj_end, qspans)) if modal else []
    if modal:
        lo, hi = rest_start, subj_end
        while lo < hi and t[lo] in " ,":
            lo += 1
        while hi > lo and t[hi - 1] in " ":
            hi -= 1
        sl.subject_text, sl.subject_span = t[lo:hi], (lo, hi)
    pred_hi = trail_at if tm else len(t)
    pred_raw = words(_cut(t, pred_start, pred_hi, qspans))
    pred_raw = v.apply_phrases(pred_raw)
    subj_raw = v.apply_phrases(subj_raw)
    # plain passive: "... shall be <verb>ed [x] by <agent>"  ->  agent is the subject; the old subject is the object
    if modal and len(pred_raw) >= 4 and pred_raw[0] == "be" and "by" in pred_raw[2:]:
        part = pred_raw[1]
        j = pred_raw.index("by", 2)
        agent = pred_raw[j + 1:]
        if agent and (part.endswith("ed") or part in _IRREGULAR_PARTICIPLES) and _agent_is_one_who_acts(part, agent):
            sl.passive = True
            pred_raw = [_IRREGULAR_PARTICIPLES.get(part, part)] + subj_raw + pred_raw[2:j]
            subj_raw = agent
            sl.subject_key = _keyify(subj_raw, v)
    if not sl.passive:
        sl.subject_key = _keyify(subj_raw, v)
    sl.predicate_words = tuple(pred_raw)
    sl.predicate_key = _keyify(pred_raw, v)

    sl.digest = digest_of(sl) if not sl.empty else hashlib.sha256(("empty|" + mid).encode()).hexdigest()[:16]
    return sl


def _cut_with(text: str, spans: list[tuple[int, int]], filler: str) -> str:
    out, p = [], 0
    for a, b in sorted(spans):
        out.append(text[p:a])
        out.append(filler)
        p = b
    out.append(text[p:])
    return "".join(out)


def digest_of(sl: Slots) -> str:
    """A short hash of everything the engine compares. Equal digests are the engine's definition of 'the same requirement'."""
    payload = json.dumps([list(sl.subject_key), sl.modal_class, sl.negated, list(sl.predicate_key), sorted(list(c.key) for c in sl.conditions),
                          sorted(map(list, (q.canon() for q in sl.quantities)), key=json.dumps)], separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
