"""The written rules that turn two requirements into a typed relationship. No score decides a type: a type comes from a rule, and the rule is named in the output.

Types: EQUIVALENT, VARIANT, SUBSUMES, CONFLICT, COMPLEMENTARY, UNRELATED (the taxonomy of the research report, section "Relationship taxonomy").

Two requirements are first split by *family*: the same subject and the same predicate words (after the vocabulary). Inside a family the words are the same, so only the slots can differ (modal,
polarity, conditions, numbers) and the rules below compare slot by slot. Across families the words differ, and the only relationships the engine will state are the two near misses it can
prove from words alone (the same predicate about a different subject; the same subject with different words).

`RULES` is the list that `docs/COMPARE_FORMAT.md` shows and that `tools/mutation/compare.py` breaks one rule at a time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .quantities import Quantity
from .slots import Slots

TYPES = ("EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED")

RULES: dict[str, tuple[str, str]] = {
    "EQ-DIGEST": ("EQUIVALENT", "Same subject, modal, polarity, predicate words, conditions and quantities after the vocabulary and unit conversion."),
    "MODAL-DIFF": ("VARIANT", "Everything else is equal but the modal differs in kind: shall or must (mandatory), should (goal), will (fact), may (optional). A person decides which applies."),
    "NEG-CONFLICT": ("CONFLICT", "The same subject, words, conditions, modal and numbers, one saying 'shall' and the other 'shall not' (or never): both cannot hold."),
    "NEG-COND": ("VARIANT", "One is negated and the other is not, but their conditions differ, so they might both hold in different situations."),
    "COND-ABSENT": ("SUBSUMES", "Everything else is equal, one has a condition and the other has none: the one with no condition applies always, so it is stricter."),
    "COND-DIFF": ("VARIANT", "Both have conditions and the conditions differ (different words, or a different kind: when, if, while, after, ...)."),
    "COND-VALUE": ("VARIANT", "The conditions use the same words but a different number or unit, and the two trigger ranges are not nested (or one has no stated bound), so a person decides."),
    "COND-REGION": ("SUBSUMES", "The conditions begin with when, if or while, use the same words, and one trigger range contains the other ('when above 80' contains 'when above 90'). The requirement that applies in more situations is stricter. Not said for 'unless', 'until', 'after' and the like: which side applies is not read."),
    "Q-SUBSUMES": ("SUBSUMES", "One number's allowed values lie strictly inside the other's (within 2 s is inside within 5 s; at least 99.9 percent is inside at least 99 percent). The narrower one is stricter."),
    "Q-CONFLICT": ("CONFLICT", "The allowed values do not overlap: exactly 5 s and exactly 10 s; at most 5 s and at least 10 s. No value can satisfy both. Said only when the conditions and the modal are the same: 'within 2 s when the tank is full' and 'at least 10 s when the tank is empty' may both hold, and are left as differing in condition."),
    "Q-BOUNDS": ("COMPLEMENTARY", "One is only a lower bound and the other only an upper bound of the same quantity, and they overlap: together they give a range."),
    "Q-UNSTATED": ("VARIANT", "A number is written without a bound on one or both sides ('5 s' against 'at most 5 s', or two bare numbers that differ), or with 'up to', which is a limit in one requirement and a capacity in another. Without the direction nothing stronger can be said."),
    "Q-TOLERANCE": ("VARIANT", "The same value and bound but a plus-or-minus tolerance on one side only; or different values where at least one has a tolerance (the engine does not combine a tolerance with a bound, so it says only that they differ)."),
    "Q-TOLERANCE-TIGHTER": ("SUBSUMES", "The same value and bound, both with a plus-or-minus tolerance, and one tolerance is smaller. The tighter band is stricter."),
    "Q-EXTRA": ("SUBSUMES", "One states a bounded quantity of a kind the other does not mention. The one with the extra constraint is stricter."),
    "Q-EXTRA-UNSTATED": ("VARIANT", "One has a number of a kind the other lacks, and that number has no stated bound."),
    "Q-NEGATED": ("VARIANT", "A requirement is negated ('shall not ... below 0'), so which side of a bound is allowed is reversed and the engine does not read the direction: only that the numbers differ. Also written when one is negated and the other is not and their numbers differ ('shall not open within 2 s' does not contradict 'shall open within 10 s')."),
    "Q-RANGE": ("VARIANT", "At least one number is a range ('between 5 and 10 s'). Whether the wider range is the stricter ('shall operate between') or the narrower ('shall respond between') depends on the meaning, so nothing stronger than 'differs' is said."),
    "Q-MULTI": ("VARIANT", "Several numbers of the same kind that cannot be matched one to one."),
    "MIXED": ("VARIANT", "Different slots point in different directions (one is stricter in one way and looser in another), or a range bound comes with another difference."),
    "UNEXPLAINED": ("VARIANT", "The engine saw different keys and could not say which slot differs. This should never be written; a test fails if it is."),
    "WORDS-DIFF": ("VARIANT", "The same subject, and the predicate words differ in a way no rule explains (or are the same words in a different order). Written only when the wordings overlap enough to be worth a look."),
    "SUBJ-DIFF": ("UNRELATED", "The same predicate words about a different subject. A near miss, written so a person can see why it was not merged. (Subject and object swapped is not caught: the words are not the same predicate.)"),
}


@dataclass
class Finding:
    rel: str                  # VARIANT | CONFLICT | COMPLEMENTARY | SUBSUMES_A | SUBSUMES_B
    rule: str
    code: str
    text: str
    a_span: tuple[int, int] | None = None
    b_span: tuple[int, int] | None = None


@dataclass
class Relation:
    type: str
    rule: str
    basis: str                           # slot | words_differ | subject
    direction: str | None = None
    why: list[Finding] = field(default_factory=list)
    words_only_a: list[str] = field(default_factory=list)
    words_only_b: list[str] = field(default_factory=list)

    @property
    def needs_review(self) -> bool:
        return self.type in ("VARIANT", "CONFLICT")


# ---- intervals ---------------------------------------------------------------------------------------------------
Interval = tuple[float | None, float | None, bool, bool]
_INF = float("inf")


def _lo(i: Interval) -> tuple[float, int]:
    return (-_INF, 0) if i[0] is None else (i[0], 0 if i[2] else 1)


def _hi(i: Interval) -> tuple[float, int]:
    return (_INF, 0) if i[1] is None else (i[1], 0 if i[3] else -1)


def _is_empty(lo: tuple[float, int], hi: tuple[float, int]) -> bool:
    return lo[0] > hi[0] or (lo[0] == hi[0] and (lo[1] == 1 or hi[1] == -1))


def intersects(x: Interval, y: Interval) -> bool:
    return not _is_empty(max(_lo(x), _lo(y)), min(_hi(x), _hi(y)))


def inside(x: Interval, y: Interval) -> bool:
    """Every value that x allows, y allows too."""
    return _lo(x) >= _lo(y) and _hi(x) <= _hi(y)


def _same(x: Interval, y: Interval) -> bool:
    return _lo(x) == _lo(y) and _hi(x) == _hi(y)


def _say(q: Quantity) -> str:
    return q.raw


def _tolerance(x: Quantity, y: Quantity) -> Finding:
    """The same value and bound, a different tolerance."""
    sx, sy = (x.start, x.end), (y.start, y.end)
    if x.tolerance is not None and y.tolerance is not None:
        stricter = "A" if x.tolerance < y.tolerance else "B"
        return Finding("SUBSUMES_" + stricter, "Q-TOLERANCE-TIGHTER", "tighter_tolerance", f"{stricter} has the tighter tolerance: A: {_say(x)}; B: {_say(y)}", sx, sy)
    return Finding("VARIANT", "Q-TOLERANCE", "tolerance_differs", f"A: {_say(x)}; B: {_say(y)}: the same value, a tolerance on one side only", sx, sy)


def _relate(x: Quantity, y: Quantity) -> list[Finding]:
    """One number in A against one of the same kind in B, which are not the same quantity."""
    sx, sy = (x.start, x.end), (y.start, y.end)
    if x.comparator == "up to" or y.comparator == "up to":
        return [Finding("VARIANT", "Q-UNSTATED", "direction_unread", f"A: {_say(x)}; B: {_say(y)}: 'up to' is a limit in one requirement and a capacity in another, so which is stricter is not said", sx, sy)]
    if not x.comparator or not y.comparator:
        if x.base == y.base and x.value_hi == y.value_hi and x.tolerance == y.tolerance and x.exact == y.exact:
            return [Finding("VARIANT", "Q-UNSTATED", "bound_unstated", f"A: {_say(x)}; B: {_say(y)}: the same value but one is not bounded, so nothing can be said about which is stricter", sx, sy)]
        return [Finding("VARIANT", "Q-UNSTATED", "value_differs", f"A: {_say(x)}; B: {_say(y)}: different values and no stated direction", sx, sy)]
    if x.exact != y.exact and x.base == y.base:
        return [Finding("VARIANT", "Q-UNSTATED", "value_differs", f"A: {_say(x)}; B: {_say(y)}: different values (too many digits to compare as numbers)", sx, sy)]
    ix, iy = x.interval, y.interval
    assert ix is not None and iy is not None
    if _same(ix, iy):
        return [_tolerance(x, y)]
    if x.tolerance is not None or y.tolerance is not None:
        return [Finding("VARIANT", "Q-TOLERANCE", "tolerance_differs", f"A: {_say(x)}; B: {_say(y)}: different values and a plus-or-minus tolerance on at least one, which is not applied here", sx, sy)]
    if x.comparator == "range" or y.comparator == "range":
        return [Finding("VARIANT", "Q-RANGE", "range_differs", f"A: {_say(x)}; B: {_say(y)}: a range differs, and whether the wider range is the stricter depends on the meaning", sx, sy)]
    if not intersects(ix, iy):
        return [Finding("CONFLICT", "Q-CONFLICT", "quantity_conflict", f"A: {_say(x)}; B: {_say(y)}: no value satisfies both", sx, sy)]
    x_upper, x_lower = ix[0] is None, ix[1] is None
    y_upper, y_lower = iy[0] is None, iy[1] is None
    if (x_upper and y_lower) or (x_lower and y_upper):
        return [Finding("COMPLEMENTARY", "Q-BOUNDS", "range_bounds", f"A: {_say(x)}; B: {_say(y)}: a lower and an upper bound that together give a range", sx, sy)]
    if inside(ix, iy):
        return [Finding("SUBSUMES_A", "Q-SUBSUMES", "stricter_value", f"A: {_say(x)} is stricter than B: {_say(y)}", sx, sy)]
    if inside(iy, ix):
        return [Finding("SUBSUMES_B", "Q-SUBSUMES", "stricter_value", f"B: {_say(y)} is stricter than A: {_say(x)}", sx, sy)]
    # Not reachable with today's comparators (an overlap that is neither nested nor a pair of bounds needs a two-sided value, which only a range is, and ranges are handled above).
    # It is a finding, not a crash, if a later change makes it reachable: a test fails when UNEXPLAINED is written.
    return [Finding("VARIANT", "UNEXPLAINED", "values_overlap", f"A: {_say(x)}; B: {_say(y)}: the values overlap and the engine has no rule for how", sx, sy)]


def _quantity_findings(a: Slots, b: Slots) -> list[Finding]:
    out: list[Finding] = []
    conds_equal = _cond_keys(a) == _cond_keys(b)
    for role in ("main", "condition"):
        if role == "condition" and not conds_equal:
            continue                       # the conditions themselves differ (or one has none): that is reported, and their numbers are not compared
        qa = [q for q in a.quantities if q.role == role]
        qb = [q for q in b.quantities if q.role == role]
        for dim in sorted({q.key_dim for q in qa + qb}):
            la = [q for q in qa if q.key_dim == dim]
            lb = [q for q in qb if q.key_dim == dim]
            ca, cb = sorted(map(repr, (q.canon() for q in la))), sorted(map(repr, (q.canon() for q in lb)))
            if ca == cb:
                continue
            if role == "condition":
                sa_, sb_ = ((la[0].start, la[0].end) if la else None), ((lb[0].start, lb[0].end) if lb else None)
                if len(la) == 1 and len(lb) == 1 and la[0].interval and lb[0].interval and la[0].canon()[5] == lb[0].canon()[5] and _region_trigger(a, la[0]) and _region_trigger(b, lb[0]):
                    ia, ib = la[0].interval, lb[0].interval
                    if inside(ia, ib) and not inside(ib, ia):
                        out.append(Finding("SUBSUMES_B", "COND-REGION", "wider_trigger", f"B applies in more situations ({_say(lb[0])}) than A ({_say(la[0])}), so B is stricter", sa_, sb_))
                        continue
                    if inside(ib, ia) and not inside(ia, ib):
                        out.append(Finding("SUBSUMES_A", "COND-REGION", "wider_trigger", f"A applies in more situations ({_say(la[0])}) than B ({_say(lb[0])}), so A is stricter", sa_, sb_))
                        continue
                out.append(Finding("VARIANT", "COND-VALUE", "condition_value", "A: " + "; ".join(_say(q) for q in la) + " | B: " + "; ".join(_say(q) for q in lb) + " (in the condition)", sa_, sb_))
                continue
            if len(la) == 1 and len(lb) == 1:
                tol_only = la[0].canon()[:5] == lb[0].canon()[:5] and la[0].exact == lb[0].exact
                if tol_only:
                    out.append(_tolerance(la[0], lb[0]))
                else:
                    out += _relate(la[0], lb[0])
            elif la and not lb:
                for q in la:
                    out.append(Finding("SUBSUMES_A" if q.directional else "VARIANT", "Q-EXTRA" if q.directional else "Q-EXTRA-UNSTATED", "extra_quantity" if q.directional else "extra_number",
                                       f"A also has {_say(q)}; B has no number of that kind", (q.start, q.end), None))
            elif lb and not la:
                for q in lb:
                    out.append(Finding("SUBSUMES_B" if q.directional else "VARIANT", "Q-EXTRA" if q.directional else "Q-EXTRA-UNSTATED", "extra_quantity" if q.directional else "extra_number",
                                       f"B also has {_say(q)}; A has no number of that kind", None, (q.start, q.end)))
            else:
                out.append(Finding("VARIANT", "Q-MULTI", "quantities_differ", "A: " + "; ".join(_say(q) for q in la) + " | B: " + "; ".join(_say(q) for q in lb), (la[0].start, la[-1].end), (lb[0].start, lb[-1].end)))
    if a.negated or b.negated:
        out = [Finding("VARIANT", "Q-NEGATED", "quantity_under_negation", f.text + " (the requirement is negated, so the direction of the bound is not read)", f.a_span, f.b_span)
               if f.rule in ("Q-SUBSUMES", "Q-CONFLICT", "Q-BOUNDS", "Q-EXTRA", "Q-TOLERANCE-TIGHTER") else f for f in out]
    return out


def _cond_keys(s: Slots) -> list[tuple[str, ...]]:
    return sorted(c.key for c in s.conditions)


_REGION_TRIGGERS = ("when", "if", "while")


def _region_trigger(s: Slots, q: Quantity) -> bool:
    """Whether the condition that holds this number starts with when, if or while: only then is 'the range of values that triggers it' a region that can contain another."""
    for c in s.conditions:
        if c.start <= q.start and q.end <= c.end:
            return c.trigger in _REGION_TRIGGERS
    return False


def _quantities_equal(a: Slots, b: Slots) -> bool:
    return sorted(map(repr, (q.canon() for q in a.quantities))) == sorted(map(repr, (q.canon() for q in b.quantities)))


def same_family_findings(a: Slots, b: Slots) -> list[Finding]:
    f: list[Finding] = []
    modal_same = a.modal_class == b.modal_class
    if not modal_same:
        f.append(Finding("VARIANT", "MODAL-DIFF", "modal_differs",
                         f"A: {(a.modal_text or 'no modal') + (' not' if a.negated else '')}; B: {(b.modal_text or 'no modal') + (' not' if b.negated else '')}", a.modal_span, b.modal_span))
    conds_equal = _cond_keys(a) == _cond_keys(b)
    if a.negated != b.negated:
        sp_a, sp_b = a.negation_span or a.modal_span, b.negation_span or b.modal_span
        if not conds_equal:
            f.append(Finding("VARIANT", "NEG-COND", "polarity_and_condition", f"{'A' if a.negated else 'B'} is negated and the other is not, and their conditions differ", sp_a, sp_b))
        elif not modal_same:
            pass                           # the modals differ too ('shall not' against 'may'): MODAL-DIFF says so and both might hold
        elif not _quantities_equal(a, b):
            f.append(Finding("VARIANT", "Q-NEGATED", "polarity_and_quantity", f"{'A' if a.negated else 'B'} is negated and the other is not, and their numbers differ: not a contradiction the engine can state", sp_a, sp_b))
        else:
            f.append(Finding("CONFLICT", "NEG-CONFLICT", "polarity_conflict", f"{'A' if a.negated else 'B'} says 'not' and the other does not; both cannot hold", sp_a, sp_b))
    if not conds_equal:
        ca = (a.conditions[0].start, a.conditions[0].end) if a.conditions else None
        cb = (b.conditions[0].start, b.conditions[0].end) if b.conditions else None
        if not a.conditions and b.conditions:
            f.append(Finding("SUBSUMES_A", "COND-ABSENT", "condition_absent", f"B only applies {b.conditions[0].text}; A has no condition, so it applies always", None, cb))
        elif a.conditions and not b.conditions:
            f.append(Finding("SUBSUMES_B", "COND-ABSENT", "condition_absent", f"A only applies {a.conditions[0].text}; B has no condition, so it applies always", ca, None))
        else:
            f.append(Finding("VARIANT", "COND-DIFF", "condition_differs", f"A: {a.conditions[0].text}; B: {b.conditions[0].text}", ca, cb))
    q = _quantity_findings(a, b)
    if not conds_equal or not modal_same:
        # numbers that cannot both hold are a conflict only for the same situation and the same strength of word; the condition or modal difference is already a finding above
        q = [x for x in q if x.rule != "Q-CONFLICT"]
    f += q
    return f


def combine(findings: list[Finding]) -> tuple[str, str, str | None]:
    """The type, the rule that decided it, and for SUBSUMES the stricter side ('a' or 'b')."""
    if not findings:
        return ("VARIANT", "UNEXPLAINED", None)
    conflicts = [x for x in findings if x.rel == "CONFLICT"]
    if conflicts:
        return ("CONFLICT", conflicts[0].rule, None)
    variants = [x for x in findings if x.rel == "VARIANT"]
    if variants:
        return ("VARIANT", variants[0].rule, None)
    sa = [x for x in findings if x.rel == "SUBSUMES_A"]
    sb = [x for x in findings if x.rel == "SUBSUMES_B"]
    comp = [x for x in findings if x.rel == "COMPLEMENTARY"]
    if comp:
        return ("COMPLEMENTARY", comp[0].rule, None) if len(findings) == len(comp) == 1 else ("VARIANT", "MIXED", None)
    if sa and sb:
        return ("VARIANT", "MIXED", None)
    return ("SUBSUMES", (sa or sb)[0].rule, "a" if sa else "b")


def classify_group(a: Slots, b: Slots) -> Relation:
    """Two requirements with the same subject and predicate words (a 'family'), compared by slot. Equal keys are EQUIVALENT."""
    if a.digest == b.digest:
        return Relation("EQUIVALENT", "EQ-DIGEST", "slot")
    f = same_family_findings(a, b)
    typ, rule, direction = combine(f)
    return Relation(typ, rule, "slot", direction, f)


def _bag_diff(a: Slots, b: Slots) -> tuple[list[str], list[str]]:
    wa, wb = set(a.predicate_words), set(b.predicate_words)
    return sorted(wa - wb), sorted(wb - wa)


def classify_families(a: Slots, b: Slots, overlap: float, tau: float) -> Relation | None:
    """Two requirements whose subject or predicate words differ. Only two near misses are stated; everything else is left as not related."""
    if overlap < tau:
        return None
    if a.predicate_key == b.predicate_key and a.subject_key != b.subject_key:
        oa = sorted(set(a.subject_key) - set(b.subject_key))
        ob = sorted(set(b.subject_key) - set(a.subject_key))
        return Relation("UNRELATED", "SUBJ-DIFF", "subject", None,
                        [Finding("UNRELATED", "SUBJ-DIFF", "subject_differs", f"A is about {a.subject_text or '(no subject)'}; B is about {b.subject_text or '(no subject)'}", a.subject_span, b.subject_span)],
                        oa, ob)
    if a.subject_key == b.subject_key and a.predicate_key != b.predicate_key:
        oa, ob = _bag_diff(a, b)
        order = sorted(a.predicate_key) == sorted(b.predicate_key)
        why = [Finding("VARIANT", "WORDS-DIFF", "word_order" if order else "words_differ",
                       "the same words in a different order" if order else "the words differ: A only has " + (", ".join(oa) or "-") + "; B only has " + (", ".join(ob) or "-"))]
        return Relation("VARIANT", "WORDS-DIFF", "words_differ", None, why, oa, ob)
    return None


def classify(a: Slots, b: Slots, overlap: float = 1.0, tau: float = 0.0) -> Relation | None:
    """The one entry point: the relationship of two requirements, or None when no rule says anything."""
    if a.family == b.family:
        return classify_group(a, b)
    return classify_families(a, b, overlap, tau)
