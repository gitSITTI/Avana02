"""The comparison engine (reqin.compare): what each written rule says, what it never says, that it is deterministic, that its output follows docs/COMPARE_FORMAT.md, and how it measures up.

Three kinds of check live here and are kept apart on purpose:
  * rule tests: one sentence pair per rule, plus the pairs that must NEVER be called equivalent. `tools/mutation/compare.py` breaks every rule and feature in a copy of the code and requires that
    one of these tests fails for each; a rule without a test that notices it is gone does not stay.
  * measurements: the engine against a corpus its own author generated (compare_corpus.py) and against two sets of pairs labelled by a language model that had not seen the engine
    (compare_blind.py). The floors below are regression floors set at what the engine achieved when they were written. They are NOT a claim about real requirements.
  * format tests: the output folder, its checker, and the command line.
"""
from __future__ import annotations

import copy
import hashlib
import json
import random
import shutil
from pathlib import Path

import pytest

import compare_blind as cb
import compare_corpus as cc
from reqin.cli import main as cli
from reqin.compare import RULES, TYPES, Settings, check, classify, compare, extract, load_vocabulary, run_dataset, write
from reqin.compare import cluster as cl
from reqin.compare.engine import compare as engine_compare
from reqin.compare.ladder import idf_table, rung, weighted_jaccard
from reqin.compare.output import CompareError
from reqin.compare.quantities import find_quantities
from reqin.compare.rules import combine, inside, intersects, Finding
from reqin.compare.vocabulary import build as build_vocabulary, stem
from reqin.contract_datasets import Src, _ds, build_all, req
from reqin.dataset import write_dataset_dicts
from reqin.normalise import normalise_text

ROOT = Path(__file__).parent.parent


# ------------------------------------------------------------------------------------------------------------ helpers
def rows(*texts: str) -> list[dict]:
    return [{"mid": f"m{i}", "uid": f"R{i}", "uid_synthetic": False, "text": t, "norm_text": normalise_text(t), "fields": {}, "parent_mid": None} for i, t in enumerate(texts)]


def filler(n: int) -> list[str]:
    return [f"The unit{i} shall perform task{i} and record value{i}." for i in range(n)]


def rel(a: str, b: str, pad: int = 0) -> tuple[str, str, str | None] | None:
    """What the engine says about two sentences: (type, rule, stricter side) or None when it says nothing. `pad` adds unrelated requirements so that words are rare enough to find pairs by."""
    res = compare(rows(a, b, *filler(pad)))
    if any({m["mid"] for m in c["members"]} >= {"m0", "m1"} for c in res.clusters):
        return ("EQUIVALENT", "EQ-DIGEST", None)
    for p in res.pairs:
        sa, sb = set(p["a"]["mids"]), set(p["b"]["mids"])
        if "m0" in sa | sb and "m1" in sa | sb:
            d = p["direction"]
            if d and "m0" not in sa:
                d = "b" if d == "a" else "a"
            return (p["type"], p["rule"], d)
    return None


# one pair of sentences per rule, and the answer the rule must give. (rule, a, b, expected, padding)
RULE_CASES = [
    ("EQ-DIGEST", "The pump controller shall start the motor within 5 s.", "The pump controller must start the motor in no more than 5000 ms.", ("EQUIVALENT", "EQ-DIGEST", None), 0),
    ("MODAL-DIFF", "The pump controller shall start the motor.", "The pump controller should start the motor.", ("VARIANT", "MODAL-DIFF", None), 0),
    ("NEG-CONFLICT", "The pump controller shall start the motor.", "The pump controller shall not start the motor.", ("CONFLICT", "NEG-CONFLICT", None), 0),
    ("NEG-COND", "The pump controller shall not start the motor when the door is open.", "The pump controller shall start the motor when the level is low.", ("VARIANT", "NEG-COND", None), 0),
    ("COND-ABSENT", "The pump controller shall close the valve.", "The pump controller shall close the valve when the level is low.", ("SUBSUMES", "COND-ABSENT", "a"), 0),
    ("COND-DIFF", "The pump controller shall close the valve when the level is low.", "The pump controller shall close the valve if the supply fails.", ("VARIANT", "COND-DIFF", None), 0),
    ("COND-VALUE", "The pump controller shall close the valve when the temperature is between 70 and 90 degrees C.",
     "The pump controller shall close the valve when the temperature is between 80 and 100 degrees C.", ("VARIANT", "COND-VALUE", None), 0),
    ("COND-REGION", "The pump controller shall close the valve when the temperature is above 80 degrees C.",
     "The pump controller shall close the valve when the temperature is above 90 degrees C.", ("SUBSUMES", "COND-REGION", "a"), 0),
    ("Q-SUBSUMES", "The pump controller shall start the motor within 2 s.", "The pump controller shall start the motor within 5 s.", ("SUBSUMES", "Q-SUBSUMES", "a"), 0),
    ("Q-CONFLICT", "The pump controller shall start the motor in exactly 5 s.", "The pump controller shall start the motor in exactly 10 s.", ("CONFLICT", "Q-CONFLICT", None), 0),
    ("Q-BOUNDS", "The pump controller shall start the motor in at least 2 s.", "The pump controller shall start the motor in at most 5 s.", ("COMPLEMENTARY", "Q-BOUNDS", None), 0),
    ("Q-UNSTATED", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor in 5 s.", ("VARIANT", "Q-UNSTATED", None), 0),
    ("Q-TOLERANCE", "The pump controller shall start the motor in 5 s.", "The pump controller shall start the motor in 5 s ± 1 s.", ("VARIANT", "Q-TOLERANCE", None), 0),
    ("Q-TOLERANCE-TIGHTER", "The pump controller shall start the motor in exactly 5 s ± 1 s.", "The pump controller shall start the motor in exactly 5 s ± 2 s.",
     ("SUBSUMES", "Q-TOLERANCE-TIGHTER", "a"), 0),
    ("Q-EXTRA", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor.", ("SUBSUMES", "Q-EXTRA", "a"), 0),
    ("Q-EXTRA-UNSTATED", "The pump controller shall start the motor in 5 s.", "The pump controller shall start the motor.", ("VARIANT", "Q-EXTRA-UNSTATED", None), 0),
    ("Q-NEGATED", "The pump controller shall not start the motor within 2 s.", "The pump controller shall not start the motor within 5 s.", ("VARIANT", "Q-NEGATED", None), 0),
    ("Q-RANGE", "The pump controller shall operate between 5 and 10 s.", "The pump controller shall operate between 6 and 8 s.", ("VARIANT", "Q-RANGE", None), 0),
    ("Q-MULTI", "The pump controller shall start the motor within 5 s and within 7 s.", "The pump controller shall start the motor within 6 s and within 9 s.", ("VARIANT", "Q-MULTI", None), 0),
    ("MIXED", "The pump controller shall respond within 2 s when the level is low.", "The pump controller shall respond within 5 s.", ("VARIANT", "MIXED", None), 0),
    ("WORDS-DIFF", "The pump controller shall start the motor slowly.", "The pump controller shall start the motor.", ("VARIANT", "WORDS-DIFF", None), 0),
    ("SUBJ-DIFF", "The pump controller shall close the supply valve and sound the alarm.", "The battery pack shall close the supply valve and sound the alarm.", ("UNRELATED", "SUBJ-DIFF", None), 40),
]


def test_every_rule_has_a_case_and_the_case_makes_the_engine_say_it():
    covered = {c[0] for c in RULE_CASES}
    assert covered == set(RULES) - {"UNEXPLAINED"}, f"rules with no case: {sorted(set(RULES) - covered - {'UNEXPLAINED'})}; cases for no rule: {sorted(covered - set(RULES))}"
    for rule, a, b, want, pad in RULE_CASES:
        assert rel(a, b, pad) == want, f"{rule}: {a!r} / {b!r}"
        assert RULES[rule][0] == want[0], f"{rule}: the rule table says {RULES[rule][0]} but the case gives {want[0]}"


@pytest.mark.parametrize("case", RULE_CASES, ids=[c[0] for c in RULE_CASES])
def test_a_pair_read_the_other_way_round_gives_the_mirror_answer(case):
    rule, a, b, want, pad = case
    got = rel(b, a, pad)
    mirror = (want[0], want[1], {"a": "b", "b": "a", None: None}[want[2]])
    assert got == mirror, f"{rule}: reversed, expected {mirror}, got {got}"


def test_every_type_and_rule_belongs_to_the_taxonomy():
    assert TYPES == ("EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED")
    for rule, (typ, text) in RULES.items():
        assert typ in TYPES and len(text) > 40, rule


# Pairs that differ in exactly one way a reader cares about. None of them may ever be put in one cluster.
NEVER_EQUIVALENT = [
    ("a different number", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor within 6 s."),
    ("a different unit", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor within 5 ms."),
    ("at least against at most", "The pump controller shall wait at least 5 s.", "The pump controller shall wait at most 5 s."),
    ("more than against at least", "The pump controller shall wait more than 5 s.", "The pump controller shall wait at least 5 s."),
    ("less than against at most", "The pump controller shall wait less than 5 s.", "The pump controller shall wait at most 5 s."),
    ("a negation", "The pump controller shall start the motor.", "The pump controller shall not start the motor."),
    ("never", "The pump controller shall start the motor.", "The pump controller shall never start the motor."),
    ("shall against should", "The pump controller shall start the motor.", "The pump controller should start the motor."),
    ("shall against may", "The pump controller shall start the motor.", "The pump controller may start the motor."),
    ("a different subject", "The pump controller shall start the motor.", "The battery pack shall start the motor."),
    ("a different verb", "The pump controller shall start the motor.", "The pump controller shall stop the motor."),
    ("an extra word", "The pump controller shall start the motor.", "The pump controller shall start the motor gradually."),
    ("the agent of a passive swapped", "The motor shall be started by the pump controller.", "The pump controller shall be started by the motor."),
    ("a different reference", "The pump controller shall comply with REQ-12.", "The pump controller shall comply with REQ-13."),
    ("a condition", "The pump controller shall start the motor.", "The pump controller shall start the motor when the level is low."),
    ("a different condition", "The pump controller shall start the motor when the level is low.", "The pump controller shall start the motor when the level is high."),
    ("a different trigger word", "The pump controller shall start the motor when the door is open.", "The pump controller shall start the motor after the door is open."),
    ("a tolerance", "The supply shall provide 12 V.", "The supply shall provide 12 V ± 0.5 V."),
    ("a range against a limit", "The pump controller shall respond between 5 and 10 s.", "The pump controller shall respond within 10 s."),
    ("the same words in another order", "The pump controller shall start the motor.", "The pump controller shall the motor start."),
    ("kilobytes against kibibyte guess", "The recorder shall store 1 GB.", "The recorder shall store 1000 MB."),
    ("and and or reordered", "The pump controller shall close the valve when the level is low and the door is open or the lid is open.",
     "The pump controller shall close the valve when the door is open or the lid is open and the level is low."),
    ("be safe by design is not a passive", "The unit shall be safe by design.", "The design shall be safe by unit."),
]


@pytest.mark.parametrize("why,a,b", NEVER_EQUIVALENT, ids=[x[0] for x in NEVER_EQUIVALENT])
def test_these_are_never_called_equivalent(why, a, b):
    got = rel(a, b)
    assert got is None or got[0] != "EQUIVALENT", f"{why}: {a!r} / {b!r} -> {got}"


# Pairs that mean the same and are written differently in ways the written rules do handle. They must be one cluster.
ALWAYS_EQUIVALENT = [
    ("case, spacing and punctuation", "The pump controller shall start the motor.", "  the PUMP  controller shall start the motor "),
    ("shall and must", "The pump controller shall start the motor.", "The pump controller must start the motor."),
    ("a unit conversion", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor within 5000 ms."),
    ("a minute and its seconds", "The pump controller shall wait at least 2 min.", "The pump controller shall wait at least 120 s."),
    ("kilo prefix", "The fan shall run at 50 Hz.", "The fan shall run at 0.05 kHz."),
    ("a comparator in other words", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor in no more than 5 s."),
    ("a number word", "The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor within five seconds."),
    ("the passive voice", "The pump controller shall start the motor.", "The motor shall be started by the pump controller."),
    ("the passive with an irregular verb", "The pump controller shall send the alarm message.", "The alarm message shall be sent by the pump controller."),
    ("the condition first", "The pump controller shall close the valve when the level is low.", "When the level is low, the pump controller shall close the valve."),
    ("the condition first, no comma", "The pump controller shall close the valve when the level is low.", "When the level is low the pump controller shall close the valve."),
    ("two conditions in the other order", "The pump controller shall close the valve when the level is low and the door is open.", "The pump controller shall close the valve when the door is open and the level is low."),
    ("an article", "The pump controller shall start the motor.", "A pump controller shall start the motor."),
    ("a synonym in the shipped vocabulary", "The pump controller shall transmit the status message.", "The pump controller shall send the status message."),
    ("an abbreviation in the shipped vocabulary", "The pump controller shall send the status message.", "The pump controller shall send the status msg."),
    ("a spelling variant", "The pump controller shall initialise the sensor.", "The pump controller shall initialize the sensor."),
    ("whenever and when", "The pump controller shall close the valve whenever the level is low.", "The pump controller shall close the valve when the level is low."),
    ("a fixed phrase", "The pump controller shall send the alarm in order to warn the operator.", "The pump controller shall send the alarm to warn the operator."),
    ("a plural and its singular", "The pump controller shall record each fault.", "The pump controller shall record each faults."),
]


@pytest.mark.parametrize("why,a,b", ALWAYS_EQUIVALENT, ids=[x[0] for x in ALWAYS_EQUIVALENT])
def test_these_are_put_in_one_cluster(why, a, b):
    assert rel(a, b) == ("EQUIVALENT", "EQ-DIGEST", None), f"{why}: {a!r} / {b!r}"


def test_chains_are_not_clusters_only_keys_that_are_equal_are():
    # a ~ b (5 s = 5000 ms) and b ~ c would not make a ~ c: c is 6 s, which is its own key.
    res = compare(rows("The unit shall run within 5 s.", "The unit shall run within 5000 ms.", "The unit shall run within 6 s."))
    assert [sorted(m["mid"] for m in c["members"]) for c in res.clusters] == [["m0", "m1"]]
    assert res.clusters[0]["valid"] is True


def test_nothing_is_ever_written_as_unexplained_or_as_a_type_outside_the_taxonomy(corpus_result, seen_pairs_result):
    for res in (corpus_result[1], seen_pairs_result):
        assert all(p["rule"] != "UNEXPLAINED" for p in res.pairs)
        assert {p["type"] for p in res.pairs} <= set(TYPES) - {"EQUIVALENT"}
        assert all(p["rule"] in RULES and RULES[p["rule"]][0] == p["type"] or p["rule"] == "MIXED" for p in res.pairs)
        assert all(p["status"] == "draft" and p["provenance"] == "mechanical" for p in res.pairs)
        assert all(c["status"] == "draft" and c["provenance"] == "mechanical" and c["valid"] for c in res.clusters)


def test_a_finding_the_engine_cannot_place_is_written_as_unexplained_not_a_crash():
    assert combine([]) == ("VARIANT", "UNEXPLAINED", None)


# ------------------------------------------------------------------------------------------------------------ combining findings
def test_combining_findings_conflict_beats_variant_beats_the_rest():
    f = lambda rel_, rule: Finding(rel_, rule, "x", "x")
    assert combine([f("VARIANT", "A"), f("CONFLICT", "B"), f("SUBSUMES_A", "C")])[:2] == ("CONFLICT", "B")
    assert combine([f("SUBSUMES_A", "C"), f("VARIANT", "A")])[:2] == ("VARIANT", "A")
    assert combine([f("SUBSUMES_A", "C"), f("SUBSUMES_A", "D")]) == ("SUBSUMES", "C", "a")
    assert combine([f("SUBSUMES_B", "C")]) == ("SUBSUMES", "C", "b")
    assert combine([f("SUBSUMES_A", "C"), f("SUBSUMES_B", "D")]) == ("VARIANT", "MIXED", None)
    assert combine([f("COMPLEMENTARY", "E")]) == ("COMPLEMENTARY", "E", None)
    assert combine([f("COMPLEMENTARY", "E"), f("SUBSUMES_A", "C")]) == ("VARIANT", "MIXED", None)


def test_intervals():
    inf = None
    assert intersects((inf, 5, False, True), (5, inf, True, False))              # at most 5 and at least 5 meet at 5
    assert not intersects((inf, 5, False, False), (5, inf, True, False))         # less than 5 and at least 5 do not
    assert inside((inf, 2, False, True), (inf, 5, False, True))
    assert not inside((inf, 5, False, True), (inf, 5, False, False)) and inside((inf, 5, False, False), (inf, 5, False, True))
    assert inside((5, 5, True, True), (3, 9, True, True)) and not inside((3, 9, True, True), (5, 5, True, True))


# ------------------------------------------------------------------------------------------------------------ quantities
def q(text: str):
    return [(x.comparator, x.base, None if x.value_hi is None else x.value_hi * x.factor, x.dimension, x.tolerance, x.role) for x in find_quantities(text)]


QUANTITY_CASES = [
    ("The pump shall start within 5 s.", [("<=", 5000.0, None, "time", None, "main")]),
    ("The pump shall start in no more than 5000 ms.", [("<=", 5000.0, None, "time", None, "main")]),
    ("Availability shall be at least 99.9 percent.", [(">=", 99.9, None, "percent", None, "main")]),
    ("It shall respond between 5 and 10 s.", [("range", 5000.0, 10000.0, "time", None, "main")]),
    ("It shall respond 5 to 10 s.", [("range", 5000.0, 10000.0, "time", None, "main")]),
    ("It shall respond in 5-10 s.", [("range", 5000.0, 10000.0, "time", None, "main")]),
    ("The supply shall be 12 V ± 0.5 V.", [("", 12.0, None, "voltage", 0.5, "main")]),
    ("The error shall be within ±0.5 degrees C.", [("<=", 0.5, None, "temperature", None, "main")]),
    ("The error shall be ±0.5 degrees C.", [("<=", 0.5, None, "temperature", None, "main")]),
    ("The alarm shall sound when the temperature exceeds 80 degrees C.", [(">", 80.0, None, "temperature", None, "main")]),
    ("It shall respond within five seconds.", [("<=", 5000.0, None, "time", None, "main")]),
    ("It shall not exceed 5 kg.", [("<=", 5.0, None, "mass", None, "main")]),
    ("It shall respond in 5 s or less.", [("<=", 5000.0, None, "time", None, "main")]),
    ("It shall complete in 5 s.", [("", 5000.0, None, "time", None, "main")]),
    ("The delay shall be 1,000 ms.", [("", 1000.0, None, "time", None, "main")]),
    ("It shall weigh less than 5 kg and more than 2 kg.", [("<", 5.0, None, "mass", None, "main"), (">", 2.0, None, "mass", None, "main")]),
    ("The data shall be kept over 30 days.", [("", 2592000000.0, None, "time", None, "main")]),        # 'over' is not read as a bound: "over 30 days" is a period
    ("The log shall be retained for more than 30 days.", [(">", 2592000000.0, None, "time", None, "main")]),
    ("The bus shall carry 28 Vdc ± 1 V.", [("", 28.0, None, "voltage_dc", 1.0, "main")]),               # a tolerance written in plain V under a Vdc value
    ("The pump shall deliver 10 l/min.", [("", 10 * (1 / 60000.0), None, "volume/time", None, "main")]),      # litres per minute, in litres per millisecond
    ("The tank shall hold 5 litres.", [("", 5.0, None, "volume", None, "main")]),
    ("The tank shall hold 5 L.", [("", 5.0, None, "volume", None, "main")]),                           # capital L is the usual litre symbol; other single capitals are not units
    ("The tank shall hold 250 mL.", [("", 0.25, None, "volume", None, "main")]),
    # not quantities: a number word with no unit, a reference, a standard's number
    ("It shall perform one of the following.", []),
    ("It shall comply with REQ-12.", []),
    ("It shall use the ARINC 429 bus.", []),
]


@pytest.mark.parametrize("text,want", QUANTITY_CASES, ids=[c[0][:48] for c in QUANTITY_CASES])
def test_quantities_are_read_as_written(text, want):
    assert q(text) == want


def test_units_of_one_kind_are_the_same_quantity_and_data_sizes_are_not_guessed():
    one = lambda t: find_quantities(t)[0].canon()
    assert one("The mass shall be 40 kg.") == one("The mass shall be 40000 g.")
    assert one("It shall wait 2 min.") == one("It shall wait 120 s.")
    assert one("It shall run at 0.05 kHz.") == one("It shall run at 50 Hz.")
    assert one("Storage shall be 1 GB.") != one("Storage shall be 1000 MB.")
    assert one("A voltage of 28 V.") != one("A voltage of 28 mV.")
    assert one("A mass of 5 kg.") != one("A mass of 5 lb.")
    assert one("The tank shall hold 5 L.") == one("The tank shall hold 5000 ml.") == one("The tank shall hold 5 litres.")
    assert find_quantities("Item 5 S is blue.") == [] and find_quantities("Part 5 M is blue.") == []      # a single capital letter that is not a listed symbol is not a unit


def test_the_span_of_a_quantity_is_its_own_text_including_its_bound():
    t = "The pump shall start in no more than 5000 ms after power-on."
    x = find_quantities(t)[0]
    assert t[x.start:x.end] == "in no more than 5000 ms" == x.raw


# ------------------------------------------------------------------------------------------------------------ slots
V = load_vocabulary()


def slots(text: str):
    n = normalise_text(text)
    return n, extract(n, V, "m", "u")


def test_the_slots_of_a_plain_requirement_and_where_they_are_in_the_text():
    n, s = slots("The pump controller shall not start the motor when the level is low.")
    assert s.subject_key == ("pump", "controller") and n[slice(*s.subject_span)] == "The pump controller"
    assert s.modal_class == "mandatory" and n[slice(*s.modal_span)] == "shall"
    assert s.negated and n[slice(*s.negation_span)] == "not"
    assert len(s.conditions) == 1 and s.conditions[0].trigger == "when" and n[s.conditions[0].start:s.conditions[0].end].endswith("the level is low")
    assert s.predicate_key == ("start", "motor") and not s.passive and not s.empty and not s.no_modal and not s.compound


def test_the_passive_becomes_the_active_and_says_so():
    _, a = slots("The motor shall be started by the pump controller.")
    _, b = slots("The pump controller shall start the motor.")
    assert a.passive and not b.passive and a.digest == b.digest and a.subject_key == ("pump", "controller")
    _, c = slots("The motor shall be started.")
    assert not c.passive                       # no agent: not rewritten, compared as written
    _, d = slots("The unit shall be safe by design.")
    assert not d.passive                       # 'safe' is not a participle


def test_a_not_inside_a_bound_is_not_a_negation_but_one_after_the_modal_is():
    _, a = slots("The response time shall not exceed 5 s.")
    assert not a.negated and a.quantities[0].comparator == "<="
    _, b = slots("The pump controller shall no longer start the motor.")
    assert b.negated
    _, c = slots("The pump controller shall never start the motor.")
    assert c.negated


def test_no_modal_two_modals_and_empty_text_are_each_said_not_hidden():
    assert slots("Start the motor.")[1].no_modal
    assert slots("The pump shall start and the fan shall stop.")[1].compound
    assert slots("")[1].empty


def test_conditions_first_or_last_have_the_same_key_and_different_trigger_words_do_not():
    a = slots("When the level is low, the pump controller shall close the valve.")[1]
    b = slots("The pump controller shall close the valve when the level is low.")[1]
    c = slots("The pump controller shall close the valve if the level is low.")[1]
    assert a.digest == b.digest != c.digest


def test_every_span_in_every_slot_points_into_the_normalised_text():
    for r in cc.make_corpus(30, 3):
        n = normalise_text(r.text)
        s = extract(n, V, "m", "u")
        j = s.to_json()
        for key in ("subject", "modal"):
            sp = j[key]["span"]
            assert sp is None or (0 <= sp[0] <= sp[1] <= len(n) and n[sp[0]:sp[1]].strip() != "" or sp[0] == sp[1])
        for x in j["quantities"]:
            assert n[x["span"][0]:x["span"][1]] == x["raw"], (n, x)


# ------------------------------------------------------------------------------------------------------------ vocabulary and stemming
STEM_FAMILIES = [["start", "started", "starting", "starts"], ["stop", "stopped", "stopping", "stops"], ["close", "closes", "closed", "closing"], ["fault", "faults"],
                 ["battery", "batteries"], ["apply", "applies", "applied", "applying"], ["store", "stores", "stored", "storing"], ["sound", "sounds", "sounded"]]


@pytest.mark.parametrize("family", STEM_FAMILIES, ids=[f[0] for f in STEM_FAMILIES])
def test_the_stemmer_gives_every_form_of_a_word_the_same_stem(family):
    assert len({stem(w) for w in family}) == 1, [stem(w) for w in family]


def test_the_stemmer_does_not_join_different_words():
    assert len({stem(w) for w in ("start", "stop", "store", "sound", "close", "closet", "reset", "set")}) == 8
    assert stem("bus") == "bus" and stem("gas") == "gas" and stem("is") == "is"          # short words are left alone


def test_an_owner_vocabulary_changes_what_is_merged_and_is_recorded_by_its_checksum(tmp_path):
    a, b = "The pump controller shall halt the motor.", "The pump controller shall stop the motor."
    assert rel(a, b) != ("EQUIVALENT", "EQ-DIGEST", None)
    f = tmp_path / "vocab.json"
    f.write_text(json.dumps({"synonyms": [["halt", "stop"]]}), encoding="utf-8")
    custom = load_vocabulary(str(f))
    assert custom.sha256 != V.sha256
    res = compare(rows(a, b), custom)
    assert len(res.clusters) == 1 and res.summary["engine"]["vocabulary_sha256"] == custom.sha256 != V.sha256


def test_a_vocabulary_file_that_is_not_understood_is_refused_not_ignored(tmp_path):
    f = tmp_path / "v.json"
    f.write_text("{not json", encoding="utf-8")
    with pytest.raises((ValueError, CompareError)):
        load_vocabulary(str(f))


# ------------------------------------------------------------------------------------------------------------ the ladder and clusters
def test_weighted_overlap_counts_a_rare_shared_word_for_more_than_a_common_one():
    idf, d = idf_table([{"the", "pump"}, {"the", "fan"}, {"the", "heater"}, {"the", "valve"}])
    assert weighted_jaccard({"the", "pump"}, {"the", "fan"}, idf, d) < weighted_jaccard({"pump", "valve"}, {"pump", "valve"}, idf, d) == 1.0
    assert weighted_jaccard(set(), set(), idf, d) == 1.0
    assert weighted_jaccard({"a"}, {"b"}, idf, d) == 0.0


def test_the_rung_is_the_strictest_comparison_that_matched():
    assert rung({"exact": True, "masked_equal": True, "canonical_overlap": 1.0}) == "exact"
    assert rung({"exact": False, "masked_equal": True, "canonical_overlap": 1.0}) == "masked"
    assert rung({"exact": False, "masked_equal": False, "canonical_overlap": 1.0}) == "canonical"
    assert rung({"exact": False, "masked_equal": False, "canonical_overlap": 0.7}) == "overlap"


def test_merge_cliques_never_chains():
    # a-b and b-c are equivalent but a-c is not: they cannot be one cluster
    out = cl.merge_cliques(["a", "b", "c"], [("a", "b"), ("b", "c")])
    assert sorted(map(len, out)) == [1, 2]
    # all three pairs: one cluster
    assert cl.merge_cliques(["a", "b", "c"], [("a", "b"), ("b", "c"), ("a", "c")]) == [["a", "b", "c"]]
    # four nodes in two separate cliques, and the same answer whatever the order of the edges
    edges = [("a", "b"), ("c", "d")]
    assert cl.merge_cliques(["d", "c", "b", "a"], edges[::-1]) == cl.merge_cliques(["a", "b", "c", "d"], edges) == [["a", "b"], ["c", "d"]]
    assert cl.merge_cliques(["a"], []) == [["a"]]


def test_a_cluster_is_checked_pair_by_pair_with_the_rule_function_itself():
    s = [extract(normalise_text(t), V, f"m{i}", f"u{i}") for i, t in enumerate(["The unit shall run within 5 s.", "The unit shall run within 5000 ms.", "The unit shall run within 6 s."])]
    eq = lambda a, b: "EQUIVALENT" if a.digest == b.digest else None
    assert cl.check_cluster(s[:2], eq) and not cl.check_cluster(s, eq)
    big = [s[0]] * 40
    assert cl.check_cluster(big, eq) and not cl.check_cluster([s[0]] * 39 + [s[2]], eq)
    # a ~ b and a ~ c, but b is not ~ c: every pair is looked at, not each against the first
    table = {("m0", "m1"), ("m0", "m2")}
    chain = lambda a, b: "EQUIVALENT" if (a.mid, b.mid) in table else None
    assert not cl.check_cluster(s, chain)


def test_the_representative_is_chosen_by_written_rules_and_says_which():
    members = []
    for i, f in enumerate([{}, {"status": "Approved", "owner": "x"}, {"baseline": "BL1"}, {"status": "Approved"}]):
        members.append((extract(normalise_text("The unit shall run."), V, f"m{i}", f"R{i}"), {"mid": f"m{i}", "uid": f"R{i}", "fields": f}))
    rep, why = cl.representative(members)
    assert rep == "m2" and why[0] == "it is in a named baseline"
    rep, why = cl.representative(members[:1] + members[3:])
    assert rep == "m3" and why[0].startswith("its status")
    rep, why = cl.representative(members[:2] + members[3:])
    assert rep == "m1" and why[0].startswith("more of the six")
    assert cl.representative(members[:1])[1] == ["only member"]
    synthetic = [(extract(normalise_text("The unit shall run."), V, f"m{i}", f"R{i}"), {"mid": f"m{i}", "uid": f"R{i}", "uid_synthetic": i == 0, "fields": {}}) for i in range(2)]
    rep, why = cl.representative(synthetic)
    assert rep == "m1" and why[0].startswith("its id is the source's")
    plain = [(extract(normalise_text("The unit shall run."), V, f"m{i}", f"R{i}"), {"mid": f"m{i}", "uid": uid, "fields": {}}) for i, uid in enumerate(["R-9", "R-2"])]
    rep, why = cl.representative(plain)
    assert rep == "m1" and why == ["lowest id"]


# ------------------------------------------------------------------------------------------------------------ determinism
def test_the_same_requirements_in_any_order_give_the_same_answer(corpus_result):
    corpus, res = corpus_result
    base = cc.as_dataset_rows(corpus)
    shuffled = base[:]
    random.Random(7).shuffle(shuffled)
    again = compare(shuffled)
    assert json.dumps([again.clusters, again.pairs], sort_keys=True) == json.dumps([res.clusters, res.pairs], sort_keys=True)


def test_two_runs_write_identical_bytes(tmp_path):
    corpus = cc.make_corpus(25, 11)
    r = compare(cc.as_dataset_rows(corpus))
    ds = [{"manifest_sha256": "0" * 64, "requirements": len(corpus)}]
    a, b = write(r, tmp_path / "a", ds), write(compare(cc.as_dataset_rows(corpus)), tmp_path / "b", ds)
    for name in ("clusters.jsonl", "pairs.jsonl", "slots.jsonl", "compare.json"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


# ------------------------------------------------------------------------------------------------------------ limits are stated, not hidden
def test_a_family_with_too_many_numberings_is_not_compared_pairwise_and_says_so():
    texts = [f"The unit shall run within {n} s." for n in range(2, 12)]
    res = compare(rows(*texts), settings=Settings(max_family=5))
    assert res.summary["limits"].get("families_not_compared_pairwise") == 1
    assert any("not compared with each other" in n for n in res.summary["notes"]) and not res.pairs


def test_words_too_common_to_find_pairs_by_are_counted_and_said():
    texts = [f"The unit{i} shall perform the common task {i}." for i in range(8)]
    res = compare(rows(*texts), settings=Settings(max_posting=3))
    assert res.summary["limits"]["tokens_too_common_to_find_pairs"] > 0
    assert any("were not used to find pairs" in n for n in res.summary["notes"])


def test_nothing_to_compare_is_said_plainly():
    assert any("no requirements" in n for n in compare([]).summary["notes"])
    assert any("one requirement" in n for n in compare(rows("The unit shall run.")).summary["notes"])
    two = compare(rows("The pump shall start.", "The valve shall close slowly in the cold."))
    assert not two.clusters and not two.pairs and any(n.startswith("Nothing found") for n in two.summary["notes"])


def test_requirements_that_cannot_be_read_as_subject_and_modal_are_compared_as_written_and_counted():
    res = compare(rows("Start the motor.", "Start the motor.", "The pump shall start and the fan shall stop.", "   "))
    notes = " ".join(res.summary["notes"])
    assert "no 'shall'" in notes and "more than one modal" in notes and "no words in their text" in notes
    assert len(res.clusters) == 1 and len(res.clusters[0]["members"]) == 2          # equal text is still equal text


# ------------------------------------------------------------------------------------------------------------ measurements
@pytest.fixture(scope="session")
def corpus_result():
    corpus = cc.make_corpus()
    return corpus, compare(cc.as_dataset_rows(corpus))


@pytest.fixture(scope="session")
def seen_pairs_result():
    return compare(cb.rows_for(cb.load("compare_blind_seen.json")))


def test_the_corpus_has_the_size_and_traps_the_results_document_says():
    corpus = cc.make_corpus()
    assert len(corpus) == 1390 and len({r.meaning for r in corpus}) == 681 and sum(1 for r in corpus if r.trap_of) == 794
    assert corpus == cc.make_corpus(), "the corpus must be the same every time"


def test_corpus_no_two_requirements_that_mean_different_things_are_ever_merged(corpus_result):
    corpus, res = corpus_result
    m = cc.evaluate(corpus, res)
    assert m["fp"] == 0, m["false_merges"][:5]
    assert m["precision"] == 1.0 and m["bcubed_precision"] == 1.0


def test_corpus_recall_is_high_for_wordings_inside_the_vocabulary_and_low_outside_it(corpus_result):
    corpus, res = corpus_result
    m = cc.evaluate(corpus, res)
    inside_, total_in = m["recall_by_transform"]["(none outside the vocabulary)"]
    out_, total_out = m["recall_by_transform"]["(any outside the vocabulary)"]
    assert inside_ / total_in >= 0.99, (inside_, total_in)
    assert out_ / total_out < 0.5, "if this rises, the corpus no longer tests words the vocabulary lacks (or the vocabulary grew: update docs/COMPARE_RESULTS.md)"
    assert 0.75 <= m["recall"] <= 0.85 and m["bcubed_recall"] >= 0.88


def test_corpus_types_of_the_pairs_that_differ_in_one_thing(corpus_result):
    corpus, res = corpus_result
    m = cc.evaluate(corpus, res)
    for kind, cells in m["typed"].items():
        r, n = cells.get("plain", [0, 0])
        assert r == n, (kind, "plain", cells, [w for w in m["wrong_typed"] if w["kind"] == kind][:3])
    right = sum(c[0] for k in m["typed"].values() for c in k.values())
    total = sum(c[1] for k in m["typed"].values() for c in k.values())
    assert right / total >= 0.98, [w for w in m["wrong_typed"]][:5]


def test_corpus_recall_by_transform_is_reported_for_every_transform(corpus_result):
    corpus, res = corpus_result
    m = cc.evaluate(corpus, res)
    assert {"abbr_in", "abbr_out", "comp", "cond_first", "det", "modal", "noise", "numwords", "passive", "syn_in", "syn_out", "units"} <= set(m["recall_by_transform"])


def test_blind_pairs_seen_while_fixing_the_engine_are_a_regression_floor_not_a_test(seen_pairs_result):
    pairs = cb.load("compare_blind_seen.json")
    r = cb.score(pairs)
    assert r["pairs"] == 150 and len(pairs) == 150
    assert r["false_equivalent"] == [] and r["dangerous"] == []
    assert r["agree"] >= 105 and r["by_kind"]["surface"][0] >= 94, (r["agree"], r["by_kind"])
    assert r["by_kind"]["meaning"][0] <= 20, "wordings that need meaning are not read by written rules: a jump here means the corpus was fitted"


def test_blind_pairs_held_out_were_scored_once_and_this_is_what_they_showed():
    """Scored once, before the engine was touched again, and the engine was not changed because of what it showed (docs/COMPARE_RESULTS.md has the table and every disagreement).
    The numbers here are the ones then measured: a floor against getting worse, not a target. Raising the floor after reading these pairs would turn them into a training set."""
    pairs = cb.load("compare_blind_heldout.json")
    r = cb.score(pairs)
    assert r["pairs"] == 100
    assert r["false_equivalent"] == []                       # never merged what the labeller says differs
    # the two the labeller called VARIANT and the engine called SUBSUMES: 'when below 5' against 'when below 0'. The written rule COND-REGION says the wider trigger is the stricter requirement.
    assert sorted(w["id"] for w in r["dangerous"]) == ["H045", "H088"]
    assert r["agree"] >= 45 and r["by_kind"]["surface"][0] >= 37 and r["by_kind"]["meaning"][0] >= 8, (r["agree"], r["by_kind"])


def test_the_scorer_reads_the_engine_the_way_it_says(tmp_path):
    pairs = [{"id": "X1", "a": "The pump shall start within 5 s.", "b": "The pump must start in no more than 5000 ms.", "type": "EQUIVALENT", "direction": None, "kind": "surface"},
             {"id": "X2", "a": "The pump shall start within 2 s.", "b": "The pump shall start within 5 s.", "type": "SUBSUMES", "direction": "a", "kind": "surface"},
             {"id": "X3", "a": "The pump shall start within 2 s.", "b": "The pump shall start within 5 s.", "type": "SUBSUMES", "direction": "b", "kind": "surface"},
             {"id": "X4", "a": "The fan shall run.", "b": "The valve shall close slowly.", "type": "UNRELATED", "direction": None, "kind": "surface"}]
    r = cb.score(pairs)
    assert r["agree"] == 3 and [w["id"] for w in r["wrong"]] == ["X3"] and r["wrong"][0]["engine"] == "SUBSUMES (a stricter)"


# ------------------------------------------------------------------------------------------------------------ the output folder
def make_dataset(tmp: Path, ns: str, texts: list[str], name: str = "d") -> Path:
    s = Src(ns, "tabular", "tabular", f"{name}.csv", name)
    out = tmp / name
    b = _ds(s, [req(s, f"{ns}-{i:03d}", t, f"{name}!R{i + 1}") for i, t in enumerate(texts, 1)], [])
    write_dataset_dicts(b["requirements"], b["links"], b["rejected"], b["report"], out)
    return out


@pytest.fixture()
def small(tmp_path):
    ds = make_dataset(tmp_path, "S1", ["The pump controller shall start the motor within 5 s.", "The pump controller shall start the motor within 5000 ms.",
                                       "The pump controller shall start the motor within 2 s.", "The pump controller shall not start the motor.",
                                       "The battery pack shall store the calibration data.", "The battery pack shall store the calibration data when power is lost."])
    res, info = run_dataset(ds)
    out = write(res, tmp_path / "out", info)
    return ds, out, res


def test_the_files_the_format_promises_are_there_and_everything_is_a_draft(small):
    ds, out, res = small
    assert sorted(p.name for p in out.iterdir()) == ["clusters.jsonl", "compare.json", "pairs.jsonl", "slots.jsonl"]
    man = json.loads((out / "compare.json").read_text())
    assert man["format"] == "reqin-compare/1" and man["status"] == "draft" and man["provenance"] == "mechanical"
    assert man["datasets"][0]["requirements"] == 6 and len(man["datasets"][0]["manifest_sha256"]) == 64
    assert man["engine"]["vocabulary_sha256"] == V.sha256 and sorted(man["engine"]["rules"]) == sorted(RULES)
    for name, meta in man["files"].items():
        data = (out / name).read_bytes()
        assert meta == {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "lines": data.count(b"\n")}
    assert check(out, ds) == [] and check(out) == []


def test_what_the_small_dataset_should_show(small):
    _, out, res = small
    assert [sorted(m["uid"] for m in c["members"]) for c in res.clusters] == [["S1-001", "S1-002"]]
    kinds = {(p["type"], p["rule"]) for p in res.pairs}
    assert ("SUBSUMES", "Q-SUBSUMES") in kinds and ("CONFLICT", "NEG-CONFLICT") in kinds and ("SUBSUMES", "COND-ABSENT") in kinds


def _rewrite(out: Path, name: str, fn, fix_checksum: bool = True) -> None:
    rows_ = [json.loads(x) for x in (out / name).read_text().splitlines()]
    rows_ = fn(rows_)
    data = "".join(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows_).encode()
    (out / name).write_bytes(data)
    if fix_checksum:
        man = json.loads((out / "compare.json").read_text())
        man["files"][name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "lines": data.count(b"\n")}
        (out / "compare.json").write_text(json.dumps(man, sort_keys=True, indent=1) + "\n")


def mutate_cluster(key, value):
    def f(rows_):
        rows_[0][key] = value
        return rows_
    return f


@pytest.mark.parametrize("name,edit,needle", [
    ("clusters.jsonl", mutate_cluster("valid", False), "valid is not true"),
    ("clusters.jsonl", mutate_cluster("representative", "nobody"), "representative is not a member"),
    ("clusters.jsonl", mutate_cluster("status", "approved"), "draft and mechanical"),
    ("clusters.jsonl", mutate_cluster("rung", "overlap"), "rung must be"),
    ("clusters.jsonl", mutate_cluster("members", [{"mid": "x", "uid": "y"}]), "at least two members"),
    ("pairs.jsonl", mutate_cluster("type", "EQUIVALENT"), "equivalent requirements are clusters"),
    ("pairs.jsonl", mutate_cluster("rule", "MADE-UP"), "not a known rule"),
    ("pairs.jsonl", mutate_cluster("rule", "MODAL-DIFF"), "decides VARIANT"),
    ("pairs.jsonl", mutate_cluster("direction", "a"), "direction must be"),
    ("pairs.jsonl", mutate_cluster("needs_review", False), "needs_review"),
    ("pairs.jsonl", mutate_cluster("score", 7), "score must be"),
    ("pairs.jsonl", mutate_cluster("basis", "vibes"), "basis must be"),
    ("pairs.jsonl", mutate_cluster("rung", "feels-right"), "rung must be"),
    ("pairs.jsonl", mutate_cluster("why", [{"code": "x", "text": "x", "a_span": [5, 1], "b_span": None}]), "bad span"),
    ("slots.jsonl", mutate_cluster("mid", 7), "no mid"),
])
def test_the_checker_names_each_way_the_output_can_be_wrong(small, name, edit, needle):
    ds, out, _ = small
    _rewrite(out, name, edit)
    problems = check(out, ds)
    assert any(needle in p for p in problems), (needle, problems)


def test_a_pair_cannot_have_the_same_requirement_on_both_sides(small):
    ds, out, _ = small

    def f(rows_):
        rows_[0]["b"] = dict(rows_[0]["a"])
        return rows_
    _rewrite(out, "pairs.jsonl", f)
    assert any("no requirement may be on both sides" in p for p in check(out, ds))


def test_a_pair_that_names_an_unknown_cluster_or_requirement_is_caught(small):
    ds, out, _ = small

    def f(rows_):
        rows_[0]["a"]["clusters"] = ["C-nothing"]
        rows_[0]["b"]["mids"] = ["m_gone"]
        return rows_
    _rewrite(out, "pairs.jsonl", f)
    probs = " ".join(check(out, ds))
    assert "C-nothing" in probs and "m_gone" in probs


def test_a_changed_file_fails_its_checksum_and_a_missing_summary_means_unfinished(small):
    ds, out, _ = small
    p = out / "pairs.jsonl"
    p.write_bytes(p.read_bytes()[:-20])
    assert any("checksum" in x for x in check(out))
    (out / "compare.json").unlink()
    assert any("write was interrupted" in x for x in check(out))
    assert check(out / "nothing-here")


def test_the_output_names_the_dataset_it_was_made_from_and_notices_another(small, tmp_path):
    ds, out, _ = small
    other = make_dataset(tmp_path, "S2", ["The pump controller shall start the motor within 5 s.", "The fan shall run."], "other")
    probs = check(out, other)
    assert any("not one of the datasets this was made from" in p for p in probs)
    assert any("not the requirements of the dataset" in p for p in probs)
    assert any("1 dataset" in p or "made from" in p for p in check(out, [ds, other]))


def test_a_changed_dataset_is_noticed(small):
    ds, out, _ = small
    f = ds / "requirements.jsonl"
    f.write_bytes(f.read_bytes().replace(b"within 5 s", b"within 6 s"))
    # the dataset's own manifest no longer matches its file, and the comparison output is no longer for this dataset
    assert check(out, ds)


def test_writing_never_touches_unrelated_files_and_will_rewrite_its_own(small, tmp_path):
    ds, out, res = small
    stray = tmp_path / "mine"
    stray.mkdir()
    (stray / "notes.txt").write_text("mine")
    with pytest.raises(CompareError, match="other files"):
        write(res, stray, [])
    (tmp_path / "afile").write_text("x")
    with pytest.raises(CompareError, match="not a folder"):
        write(res, tmp_path / "afile", [])
    res2, info = run_dataset(ds)
    again = write(res2, out, info)                  # an earlier output folder is replaced in place
    assert check(again, ds) == []


def test_a_dataset_that_fails_its_contract_is_refused_and_nothing_is_written(small, tmp_path):
    ds, _, _ = small
    bad = tmp_path / "bad"
    shutil.copytree(ds, bad)
    f = bad / "requirements.jsonl"
    f.write_bytes(f.read_bytes()[:-50])
    with pytest.raises(CompareError, match="does not follow the contract"):
        run_dataset(bad)
    with pytest.raises(CompareError, match="no dataset"):
        run_dataset([])


def test_two_datasets_are_compared_together_and_two_copies_of_one_are_refused(tmp_path):
    a = make_dataset(tmp_path, "A1", ["The pump controller shall start the motor within 5 s.", "The fan shall run."], "a")
    b = make_dataset(tmp_path, "B1", ["The pump controller must start the motor in no more than 5000 ms.", "The fan shall stop."], "b")
    res, info = run_dataset([a, b])
    assert len(info) == 2 and [sorted(m["uid"] for m in c["members"]) for c in res.clusters] == [["A1-001", "B1-001"]]
    out = write(res, tmp_path / "ab", info)
    assert check(out, [a, b]) == [] and any("made from 2 dataset" in p for p in check(out, a))
    with pytest.raises(CompareError, match="both contain the internal key"):
        run_dataset([a, a])


# ------------------------------------------------------------------------------------------------------------ the fourteen contract datasets
@pytest.fixture(scope="session")
def fourteen(tmp_path_factory):
    out = tmp_path_factory.mktemp("ds14")
    return out, build_all(out, None, 60)


def test_the_engine_runs_on_all_fourteen_datasets_and_each_output_passes_its_checker(fourteen, tmp_path):
    root, index = fourteen
    assert len(index) == 14
    for e in index:
        dirs = [root / f for f in e["folders"]]
        res, info = run_dataset(dirs)
        out = write(res, tmp_path / e["id"], info)
        assert check(out, dirs) == [], (e["id"], check(out, dirs)[:3])
        assert res.summary["counts"]["requirements"] == e["expect"]["requirements"], e["id"]
        assert res.clusters or res.pairs or res.summary["notes"], f"{e['id']}: when nothing is found the run must say so"
        assert all(p["rule"] != "UNEXPLAINED" for p in res.pairs), e["id"]


def test_the_empty_dataset_says_there_is_nothing_to_compare(fourteen, capsys):
    root, index = fourteen
    f12 = next(e for e in index if e["id"] == "F12")
    res, _ = run_dataset([root / f for f in f12["folders"]])
    assert res.summary["counts"]["requirements"] == 0 and not res.clusters and not res.pairs
    assert any("Nothing to compare" in n for n in res.summary["notes"])
    assert cli(["compare", str(root / f12["folders"][0]), "--out-dir", str(root / "out12")]) == 0
    assert "Nothing to compare" in capsys.readouterr().out


def test_a_dataset_of_one_requirement_says_there_is_nothing_to_compare(tmp_path):
    ds = make_dataset(tmp_path, "O1", ["The pump controller shall start the motor."], "one")
    res, _ = run_dataset(ds)
    assert any("one requirement" in n for n in res.summary["notes"]) and not res.clusters


def test_the_ids_the_importer_invented_are_said_to_be_used_only_for_sorting(fourteen):
    root, index = fourteen
    f03 = next(e for e in index if e["id"] == "F3")
    res, _ = run_dataset([root / f for f in f03["folders"]])
    assert any("ids were invented" in n for n in res.summary["notes"])


def test_two_sources_of_the_same_spec_find_the_requirements_they_share(fourteen):
    root, index = fourteen
    f11 = next(e for e in index if e["id"] == "F11")
    res, _ = run_dataset([root / f for f in f11["folders"]])
    assert res.summary["counts"]["requirements"] == f11["expect"]["requirements"] and len(f11["folders"]) == 2


# ------------------------------------------------------------------------------------------------------------ the command line
def test_cli_compare_then_check_compare(fourteen, tmp_path, capsys):
    root, index = fourteen
    folder = root / next(e for e in index if e["id"] == "F9")["folders"][0]
    out = tmp_path / "o"
    assert cli(["compare", str(folder), "--out-dir", str(out)]) == 0
    text = capsys.readouterr().out
    assert text.startswith("compared ") and "drafts, provenance: mechanical" in text
    assert cli(["check-compare", str(out), "--dataset", str(folder)]) == 0
    assert "matches the dataset" in capsys.readouterr().out
    assert cli(["compare", str(folder), "--out-dir", str(out), "--json"]) == 0
    j = json.loads(capsys.readouterr().out)
    assert j["counts"]["requirements"] > 0 and j["engine"]["name"] == "reqin-compare"


def test_cli_refuses_bad_input_with_a_message_and_a_code(fourteen, tmp_path, capsys):
    root, index = fourteen
    assert cli(["compare", str(tmp_path / "missing"), "--out-dir", str(tmp_path / "x")]) == 2
    assert "does not follow the contract" in capsys.readouterr().err
    folder = root / next(e for e in index if e["id"] == "F1")["folders"][0]
    out = tmp_path / "o2"
    assert cli(["compare", str(folder), "--out-dir", str(out)]) == 0
    capsys.readouterr()
    (out / "pairs.jsonl").write_text("garbage\n")
    assert cli(["check-compare", str(out)]) == 1
    assert capsys.readouterr().out.startswith("NOT a valid comparison output")
    assert cli(["check-compare", str(out), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["valid"] is False
    stray = tmp_path / "stray"
    stray.mkdir()
    (stray / "a.txt").write_text("x")
    assert cli(["compare", str(folder), "--out-dir", str(stray)]) == 2
    assert "other files" in capsys.readouterr().err


def test_cli_takes_an_owner_vocabulary_and_records_it(fourteen, tmp_path, capsys):
    root, index = fourteen
    folder = root / next(e for e in index if e["id"] == "F1")["folders"][0]
    v = tmp_path / "v.json"
    v.write_text(json.dumps({"synonyms": [["halt", "stop"]]}), encoding="utf-8")
    out = tmp_path / "ov"
    assert cli(["compare", str(folder), "--out-dir", str(out), "--vocab", str(v)]) == 0
    assert json.loads((out / "compare.json").read_text())["engine"]["vocabulary_sha256"] != V.sha256
    assert cli(["compare", str(folder), "--out-dir", str(tmp_path / "ov2"), "--vocab", str(tmp_path / "nope.json")]) == 2


# ------------------------------------------------------------------------------------------------------------ more on what the engine says and does not say
def test_a_tolerance_is_never_the_reason_for_a_conflict_or_a_stricter_claim():
    # exactly 5 s ± 3 s and exactly 6 s ± 1 s have values in common, so 'no value satisfies both' would be false
    assert rel("The pump controller shall respond in exactly 5 s ± 3 s.", "The pump controller shall respond in exactly 6 s ± 1 s.") == ("VARIANT", "Q-TOLERANCE", None)


def test_the_edges_of_a_bound_are_read_exactly():
    base = "The pump controller shall wait "
    assert rel(base + "less than 5 s.", base + "at most 5 s.") == ("SUBSUMES", "Q-SUBSUMES", "a")
    assert rel(base + "more than 5 s.", base + "at least 5 s.") == ("SUBSUMES", "Q-SUBSUMES", "a")
    assert rel(base + "at least 5 s.", base + "at most 5 s.") == ("COMPLEMENTARY", "Q-BOUNDS", None)           # they meet at 5
    assert rel(base + "more than 5 s.", base + "less than 5 s.") == ("CONFLICT", "Q-CONFLICT", None)           # nothing is both
    assert rel(base + "exactly 5 s.", base + "at most 8 s.") == ("SUBSUMES", "Q-SUBSUMES", "a")
    assert rel(base + "at least 8 s.", base + "at most 5 s.") == ("CONFLICT", "Q-CONFLICT", None)


def test_wordings_are_listed_as_a_near_miss_only_when_they_overlap_enough():
    short_a, short_b = "The pump controller shall start the motor.", "The battery pack shall start the motor."
    assert rel(short_a, short_b, 40) is None                  # one shared predicate against two different subjects: under half the weight
    long_a = "The pump controller shall close the supply valve and sound the alarm."
    long_b = "The battery pack shall close the supply valve and sound the alarm."
    assert rel(long_a, long_b, 40) == ("UNRELATED", "SUBJ-DIFF", None)
    assert rel("The pump controller shall start the motor slowly.", "The pump controller shall start the motor.", 40) == ("VARIANT", "WORDS-DIFF", None)
    assert rel("The pump controller shall start the motor.", "The pump controller shall the motor start.", 40) == ("VARIANT", "WORDS-DIFF", None)
    order = compare(rows("The pump controller shall start the motor.", "The pump controller shall the motor start.", *filler(40))).pairs[0]
    assert order["basis"] == "words_differ" and order["why"][0]["code"] == "word_order" and "different order" in order["why"][0]["text"]
    diff = compare(rows("The pump controller shall start the motor slowly.", "The pump controller shall start the motor.", *filler(40))).pairs[0]
    assert diff["why"][0]["code"] == "words_differ" and diff["words_only_a"] == ["slowly"] and diff["words_only_b"] == []
    # a subject and an object swapped are not the same predicate: nothing is said (the safe answer: not merged, not described)
    assert rel("The charger shall power the battery pack.", "The battery pack shall power the charger.", 40) is None


def test_classify_says_nothing_about_different_wordings_that_overlap_too_little():
    a = extract(normalise_text("The pump controller shall start the motor."), V, "m0", "R0")
    b = extract(normalise_text("The battery pack shall start the motor."), V, "m1", "R1")
    assert classify(a, b, 0.1, 0.5) is None
    assert classify(a, b, 0.5, 0.5).rule == "SUBJ-DIFF"
    assert classify(a, b).type == "UNRELATED"                                    # called with no threshold it states the near miss


def test_words_found_in_too_many_wordings_are_not_used_to_find_pairs():
    texts = [f"The pump{i} shall close the supply valve and sound the alarm." for i in range(8)]
    assert compare(rows(*texts, *filler(40))).pairs                              # the shared predicate words find the pairs (many unrelated requirements make those words rare enough)
    limited = compare(rows(*texts, *filler(40)), settings=Settings(max_posting=3))
    assert not limited.pairs and limited.summary["limits"]["tokens_too_common_to_find_pairs"] > 0


def test_a_cluster_that_fails_the_all_pairs_check_is_written_as_invalid_and_the_checker_refuses_it(tmp_path, monkeypatch):
    import reqin.compare.engine as engine
    monkeypatch.setattr(engine, "classify", lambda a, b, *x: None)
    res = engine.compare(rows("The unit shall run within 5 s.", "The unit shall run within 5000 ms."))
    assert len(res.clusters) == 1 and res.clusters[0]["valid"] is False
    out = write(res, tmp_path / "o", [])
    assert any("valid is not true" in p for p in check(out))


def test_the_serious_pairs_come_first_and_the_stricter_side_follows_the_sentence_not_the_order_of_the_ids():
    def row(mid, uid, text):
        return {"mid": mid, "uid": uid, "uid_synthetic": False, "text": "", "norm_text": text, "fields": {}, "parent_mid": None}
    # the first has the lower internal key and the later id; an article of another length moves the number to another position in each text
    r = [row("m0", "Z-1", "The unit shall run within 5 s."), row("m1", "A-1", "A unit shall run within 2 s."),
         row("m2", "B-1", "The unit shall not run within 2 s."), row("m3", "C-1", "The unit shall run within 2 s when the door is open.")]
    res = compare(r)
    order = [p["type"] for p in res.pairs]
    assert order == sorted(order, key=("CONFLICT", "VARIANT", "SUBSUMES", "COMPLEMENTARY", "UNRELATED").index)
    sub = next(p for p in res.pairs if p["type"] == "SUBSUMES" and {*p["a"]["mids"], *p["b"]["mids"]} == {"m0", "m1"})
    stricter = sub["a"] if sub["direction"] == "a" else sub["b"]
    assert stricter["mids"] == ["m1"]                                   # within 2 s is stricter than within 5 s, whichever way round the pair is written
    assert {sub["shown_a"], sub["shown_b"]} == {"m0", "m1"} and sub["shown_a"] == sub["a"]["mids"][0]
    by_mid = {s_.mid: s_ for s_ in res.slots}
    why = sub["why"][0]
    a_mid, b_mid = sub["a"]["mids"][0], sub["b"]["mids"][0]
    assert why["a_span"] == [by_mid[a_mid].quantities[0].start, by_mid[a_mid].quantities[0].end]       # the reasons' spans are swapped together with the sides
    assert why["b_span"] == [by_mid[b_mid].quantities[0].start, by_mid[b_mid].quantities[0].end]
    assert by_mid["m0"].quantities[0].start != by_mid["m1"].quantities[0].start


def test_words_scope_pairs_name_every_requirement_of_the_two_wordings():
    texts = [f"The pump{i} shall close the supply valve and sound the alarm." for i in range(3)] + [f"The fan shall close the supply valve and sound the alarm within {n} s." for n in (2, 3)]
    res = compare(rows(*texts) + [])
    words = [p for p in res.pairs if p["a"]["scope"] == "words"]
    assert words, [p["rule"] for p in res.pairs]
    everyone = {m for p in words for m in p["a"]["mids"] + p["b"]["mids"]}
    assert {"m3", "m4"} <= everyone                                      # the two numberings of the fan wording are both on the side that names it
    assert any({"m3", "m4"} <= set(p["a"]["mids"]) or {"m3", "m4"} <= set(p["b"]["mids"]) for p in words)


def test_the_rung_and_the_overlap_of_a_cluster_say_how_alike_its_members_are():
    same = compare(rows("The unit shall run.", "The unit shall run.")).clusters[0]
    assert same["rung"] == "exact" and same["min_word_overlap"] == 1.0
    units = compare(rows("The unit shall run within 5 s.", "The unit shall run within 5000 ms.")).clusters[0]
    assert units["rung"] == "masked" and units["min_word_overlap"] < 1.0
    words = compare(rows("The unit shall send the status message.", "The unit shall transmit the status msg.")).clusters[0]
    assert words["rung"] == "canonical" and 0 < words["min_word_overlap"] < 1.0


def test_a_cluster_lists_the_pairs_that_touch_it_serious_ones_first():
    res = compare(rows("The unit shall run within 5 s.", "The unit shall run within 5000 ms.", "The unit shall not run within 5 s.", "The unit shall run within 2 s."))
    c = res.clusters[0]
    ids = [p["pid"] for p in res.pairs]
    assert c["related_total"] == len(c["related"]) > 0 and all(p in ids for p in c["related"])
    types = {p["pid"]: p["type"] for p in res.pairs}
    order = [types[p] for p in c["related"]]
    assert order == sorted(order, key=("CONFLICT", "VARIANT", "SUBSUMES", "COMPLEMENTARY", "UNRELATED").index)


def test_two_empty_requirements_are_not_paired_and_not_merged():
    res = compare(rows("   ", "  ", "The unit shall run."))
    assert not res.clusters and not res.pairs and "2 requirement(s) have no words" in " ".join(res.summary["notes"])


def test_a_write_that_stops_part_way_leaves_no_summary(tmp_path, monkeypatch):
    import reqin.compare.output as output
    res = compare(rows("The unit shall run within 5 s.", "The unit shall run within 5000 ms."))
    real = output._atomic

    def flaky(path, data):
        if path.name == "compare.json":
            raise OSError("disk full")
        real(path, data)
    monkeypatch.setattr(output, "_atomic", flaky)
    with pytest.raises(OSError):
        write(res, tmp_path / "o", [])
    assert not (tmp_path / "o" / "compare.json").exists()
    assert any("write was interrupted" in p for p in check(tmp_path / "o"))


def test_counts_in_the_summary_must_match_the_files(small):
    ds, out, _ = small
    man = json.loads((out / "compare.json").read_text())
    man["counts"]["clusters"] += 1
    (out / "compare.json").write_text(json.dumps(man))
    assert any("counts do not match" in p for p in check(out))
    man["counts"]["clusters"] -= 1
    man["counts"]["pairs"]["CONFLICT"] += 5
    (out / "compare.json").write_text(json.dumps(man))
    assert any("CONFLICT pairs" in p for p in check(out))


def test_the_checker_rejects_a_slot_with_a_span_outside_its_text(small):
    ds, out, _ = small

    def f(rows_):
        rows_[0]["modal"]["span"] = [9, 3]
        for r in rows_:
            if r["quantities"]:
                r["quantities"][0]["span"] = [0, 5000]
                break
        return rows_
    _rewrite(out, "slots.jsonl", f)
    probs = " ".join(check(out, ds))
    assert "modal has a bad span" in probs and "runs past the end of the text" in probs


@pytest.mark.parametrize("bad", [{"synonyms": "halt"}, {"abbreviations": {"X": "y"}}, {"nonsense": 1}, {"synonyms": [["a b", "c"], ["only"]]}, {"ignore": [1]}, {"phrases": {"a": 1}}])
def test_a_vocabulary_of_the_wrong_shape_is_refused(bad, tmp_path):
    f = tmp_path / "v.json"
    f.write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        load_vocabulary(str(f))


def test_the_vocabulary_checksum_covers_everything_that_changes_what_is_merged():
    base = {"abbreviations": {"msg": "message"}, "synonyms": [["send", "transmit"]], "phrases": {"in order to": "to"}, "ignore": ["the"]}
    sha = lambda d: build_vocabulary(d).sha256
    assert sha(base) == sha(copy.deepcopy(base))
    for key, other in (("abbreviations", {"msg": "messages"}), ("synonyms", [["send", "convey"]]), ("phrases", {"in order to": "so"}), ("ignore", ["the", "a"])):
        changed = copy.deepcopy(base)
        changed[key] = other
        assert sha(changed) != sha(base), key
    assert sha({**base, "ignore": ["the", "a"]}) == sha({**base, "ignore": ["a", "the"]})           # the order of the ignore list is not a difference


def test_the_default_vocabulary_is_the_one_in_the_code_and_its_checksum_is_stable():
    assert V.sha256 == load_vocabulary().sha256 and len(V.sha256) == 64 and V.source == "default"
    assert V.canon("the") is None and V.canon("msg") == V.canon("message") and V.canon("transmit") == V.canon("send") and V.canon("pumps") == V.canon("pump")
