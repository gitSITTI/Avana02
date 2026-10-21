#!/usr/bin/env python3
"""Writes the two things in the comparison docs that are computed, so they cannot drift from the code:

  * the table of rules in docs/COMPARE_FORMAT.md (between the `rules:begin` and `rules:end` marks), from `RULES` in reqin/src/reqin/compare/rules.py
  * all of docs/COMPARE_RESULTS.md: the engine run on the made-up corpus and on the two sets of labelled pairs, with every number taken from that run

    python3 tools/make_compare_docs.py            rewrite both files
    python3 tools/make_compare_docs.py --check    change nothing; exit 1 if either file is out of date (tools/test_compare_docs.py runs this)

The prose in the results page is written here, by hand, around the numbers. Where it says what a result means, the sentence is the author's reading and is meant to be argued with.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "reqin" / "src"), str(ROOT / "reqin" / "tests")]

import compare_blind as cb  # noqa: E402
import compare_corpus as cc  # noqa: E402
from reqin.compare import RULES, Settings, compare  # noqa: E402

FORMAT_MD = ROOT / "docs" / "COMPARE_FORMAT.md"
RESULTS_MD = ROOT / "docs" / "COMPARE_RESULTS.md"
BEGIN, END = "<!-- rules:begin -->", "<!-- rules:end -->"

# Where each rule came from. "research": the research report ("Requirements comparison app research.md", section "Relationship taxonomy" and the rules around it) states the relationship and the
# engine applies it mechanically. "adapted": the report names the idea in general terms and the exact form is the engine author's. "made up": the engine author's own; the report says nothing like it.
SOURCE = {
    "EQ-DIGEST": ("research", "EQUIVALENT is 'all slots equal after normalisation', with units converted. What counts as a slot, and the vocabulary, are the author's."),
    "MODAL-DIFF": ("research", "A differing modal makes a VARIANT; a modal mismatch must never be merged."),
    "NEG-CONFLICT": ("research", "'shall log' against 'shall not log' is the report's own negation example; CONFLICT is 'both cannot be satisfied'."),
    "NEG-COND": ("made up", "A negation with different conditions is called a variant because both could hold in different situations. A label written independently disagreed once (seen set B020)."),
    "COND-ABSENT": ("adapted", "The report says a dropped condition downgrades EQUIVALENT to VARIANT or SUBSUMES. Choosing SUBSUMES, with the unconditional requirement as the stricter, is the author's."),
    "COND-DIFF": ("research", "'A different trigger or state means not duplicate'; VARIANT is 'a slot value differs (... condition)'."),
    "COND-VALUE": ("made up", "Same condition words with a different number."),
    "COND-REGION": ("made up", "A wider trigger region is the stricter requirement. Two labels written independently called such pairs VARIANT (held-out H045, H088)."),
    "Q-SUBSUMES": ("research", "The report's comparator-direction rule: 'within 2 s' satisfies 'within 5 s'; for a minimum the larger number is the stricter."),
    "Q-CONFLICT": ("research", "CONFLICT includes 'incompatible values for one quantity'."),
    "Q-BOUNDS": ("adapted", "COMPLEMENTARY is 'jointly specify one behaviour'. Reading a lower and an upper bound of one quantity as that is the author's."),
    "Q-UNSTATED": ("made up", "A number with no stated bound cannot be called stricter or looser."),
    "Q-TOLERANCE": ("adapted", "The report lists tolerance among the slots whose difference makes a VARIANT. Not applying a tolerance to a bound, and so never calling such a pair a conflict, is the author's."),
    "Q-TOLERANCE-TIGHTER": ("made up", "Two tolerances on the same value: the smaller is stricter."),
    "Q-EXTRA": ("adapted", "SUBSUMES is 'A is stricter or adds a constraint'. Reading an extra bounded number as the added constraint is the author's."),
    "Q-EXTRA-UNSTATED": ("made up", "An extra number with no bound is a variant."),
    "Q-NEGATED": ("made up", "Added after a labelled pair showed that the direction of a bound flips under 'shall not'. The engine gives up on the direction instead of reading it."),
    "Q-RANGE": ("made up", "Added after a labelled pair showed that a wider range can be the stricter or the looser requirement depending on meaning. The engine gives up on the direction."),
    "Q-MULTI": ("made up", "Several numbers of one kind that cannot be matched one to one."),
    "MIXED": ("made up", "Stricter in one slot and looser in another."),
    "UNEXPLAINED": ("made up", "A safety net: the engine could not say which slot differs. Never written today; a test fails if it is."),
    "WORDS-DIFF": ("made up", "A near miss between wordings: the same subject, different predicate words. It exists so a person can see what was not merged."),
    "SUBJ-DIFF": ("made up", "A near miss between wordings: the same predicate words about a different subject."),
}
MACHINERY = [
    ("The six labels and what each means", "research", "The report's relationship taxonomy, used as written."),
    ("Types come from a named rule, never from a score", "research", "'Treat every similarity score as evidence feeding a decision, never as the decision.'"),
    ("The similarity ladder (exact, masked, overlap, canonical) as features", "adapted", "The report describes a ladder from exact to fuzzy to weighted-word overlap. The four rungs here are the author's version, with no embeddings."),
    ("Rare words count for more (inverse document frequency)", "research", "Listed in the report as the weighting for the overlap tier."),
    ("Clusters hold EQUIVALENT edges only; every cluster is checked pair by pair", "research", "Stage 3 of the report: 'cluster EQUIVALENT edges only; check cluster validity'."),
    ("Complete linkage, so a ~ b and b ~ c never make a ~ c", "research", "The report's warning about chaining with single linkage."),
    ("Which member to show first", "adapted", "The report proposes baseline, then authority, centrality, completeness and quality. Here: baseline, approved status, filled fields, real id, lowest id. The report found no evidence for any such rule."),
    ("The modal, number and condition checks as equality in the key", "adapted", "The report has them as vetoes on an AI judge. Here they are part of what 'equal' means, so no model is needed to enforce them."),
    ("Unit tables, comparator phrases, number words, irregular verbs, the vocabulary and the stemmer", "made up", "Written lists, chosen by the author, owner-editable through `--vocab` for the vocabulary only."),
    ("The settings `tau_pair`, `max_posting`, `max_family`, `max_related`", "made up", "None tuned on the corpus below. `tau_pair` was moved from 0.6 to 0.5 once, after one four-word example and before any measurement."),
]

# Why each labelled pair the engine disagreed with is a disagreement. A pair of kind "meaning" (the labeller said it needs understanding of the words) is "needs meaning" without further notes.
CAUSES = {
    "only": "The word 'only' is not read, so 'X' against 'X only' (or two different values each followed by 'only') compares as different words.",
    "extra-clause": "An extra phrase ('and shall log ...', 'and the operator identifier', 'using AES-256', 'or the load exceeds 1000 kg') is not read as an added obligation. The engine sees different words.",
    "range": "The direction of a range is not read (rule `Q-RANGE`): the engine says the numbers differ, never which range is stricter.",
    "negated-bound": "The direction of a bound under 'not' is not read (rule `Q-NEGATED`).",
    "passive-tail": "A passive with words after the agent ('... by the controller every 30 s', '... to within 5 %') is not rewritten as active, because those words are taken to be part of the agent.",
    "trigger": "'under' is not a condition trigger ('Under all operating conditions, ...').",
    "comparator-phrase": "A bound written 'down to' or 'not fall below' is not a known comparator.",
    "tolerance-range": "A tolerance ('22 ± 2') and a range ('between 20 and 24') are not converted into each other.",
    "units": "A unit not converted into the other ('kbit/s' against 'Mbit/s').",
    "cond-region": "The label says variant; the written rule `COND-REGION` says the wider trigger region is the stricter requirement. A disagreement about the label, not a slip in the code.",
    "neg-cond": "A negation with a different condition is a variant by the written rule `NEG-COND`; the label says conflict.",
    "different-words": "The sentences use different words for the same idea that are not on the vocabulary, or one has a word the other lacks ('all' against 'any'), so the engine cannot call them equal and may not list them.",
    "needs-meaning": "The labeller marked it as needing an understanding of what the words mean.",
}
GAP_LABEL = {
    "extra-clause": "An extra phrase is not read as an added obligation ('and shall log ...', 'using AES-256', 'or the load exceeds 1000 kg').",
    "only": "The word 'only' is not read.",
    "passive-tail": "A passive with words after the agent ('... by the controller every 30 s') is not turned into the active.",
    "range": "The direction of a range is not read (rule `Q-RANGE`).",
    "comparator-phrase": "'down to' and 'not fall below' are not known comparators.",
    "trigger": "'under' is not a condition trigger ('Under all operating conditions, ...').",
    "tolerance-range": "A tolerance ('22 ± 2') and a range ('between 20 and 24') are not converted into each other.",
    "units": "Units of one kind that are not converted into each other ('kbit/s' against 'Mbit/s').",
    "cond-region": "Two labels call a wider trigger region a variant where the written rule `COND-REGION` says it is the stricter requirement. Not a slip in the code, a disagreement about the rule.",
    "different-words": "Words that mean the same but are not on the vocabulary, or one extra word ('all' against 'any').",
}
SEEN_CAUSE = {"B009": "only", "B020": "neg-cond", "B035": "different-words", "B047": "only", "B049": "extra-clause", "B062": "extra-clause", "B070": "negated-bound", "B082": "only", "B097": "range",
              "B115": "extra-clause", "B139": "different-words"}
HELDOUT_CAUSE = {"H004": "comparator-phrase", "H006": "comparator-phrase", "H012": "passive-tail", "H014": "different-words", "H022": "different-words", "H026": "extra-clause", "H027": "units",
                 "H032": "different-words", "H039": "extra-clause", "H043": "different-words", "H045": "cond-region", "H048": "passive-tail", "H053": "extra-clause", "H080": "only",
                 "H084": "extra-clause", "H086": "different-words", "H087": "different-words", "H088": "cond-region", "H090": "trigger", "H091": "different-words", "H092": "range",
                 "H094": "different-words", "H095": "tolerance-range"}


def wilson(k: int, n: int) -> tuple[float, float]:
    """95 % interval for a share k/n (Wilson). With 100 pairs it is about ten points wide each way."""
    if n == 0:
        return (0.0, 1.0)
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(k: int, n: int) -> str:
    return "-" if n == 0 else f"{100 * k / n:.1f} %"


def pct_ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f} % (95 % interval {100 * lo:.0f} to {100 * hi:.0f} %)"


def table(head: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def rules_table() -> str:
    return table(["Rule", "Decides", "What it says"], [[f"`{r}`", t, text] for r, (t, text) in RULES.items()])


def sub(s: str) -> str:
    return "SUBSUMES" if s.startswith("SUBSUMES") else s


def matrix(r: dict) -> str:
    cols = ["EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED", "NONE"]
    names = ["says EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED", "says nothing"]
    rows = []
    for label in ("EQUIVALENT", "VARIANT", "SUBSUMES", "CONFLICT", "COMPLEMENTARY", "UNRELATED"):
        tot: dict[str, int] = {}
        for k, n in r["confusion"].get(label, {}).items():
            tot[sub(k.split(" (")[0])] = tot.get(sub(k.split(" (")[0]), 0) + n
        rows.append([f"**{label}**", str(sum(tot.values()))] + [str(tot.get(c, 0)) if tot.get(c, 0) else "." for c in cols])
    return table(["Labelled as", "pairs"] + names, rows)


def said_table(r: dict) -> str:
    rows = []
    for t in ("EQUIVALENT", "CONFLICT", "SUBSUMES", "COMPLEMENTARY", "VARIANT", "UNRELATED"):
        n, ok = r["said"].get(t, (0, 0))
        rows.append([t if t != "UNRELATED" else "UNRELATED or nothing said", n, ok, pct(ok, n)])
    return table(["The engine said", "times", "label agreed", "share"], rows)


def wrong_list(r: dict, causes: dict[str, str]) -> str:
    lines = []
    for w in r["wrong"]:
        if w["kind"] == "meaning":
            cause = "needs-meaning"
        else:
            if w["id"] not in causes:
                raise SystemExit(f"{w['id']} disagrees with the engine and has no cause in tools/make_compare_docs.py: read it and add one")
            cause = causes[w["id"]]
        lines.append(f"- **{w['id']}** ({w['kind']}): label {w['label']}; engine {w['engine'].replace('NONE', 'said nothing')}. Cause: {cause}.\n  - A: {w['a']}\n  - B: {w['b']}")
    return "\n".join(lines)


def cause_counts(r: dict, causes: dict[str, str]) -> str:
    n: dict[str, int] = {}
    for w in r["wrong"]:
        c = "needs-meaning" if w["kind"] == "meaning" else causes[w["id"]]
        n[c] = n.get(c, 0) + 1
    rows = [[f"`{c}`", k, CAUSES[c]] for c, k in sorted(n.items(), key=lambda kv: (-kv[1], kv[0]))]
    return table(["Cause", "pairs", "What it means"], rows)


def kind_rows(r: dict) -> list[list[str]]:
    return [[k, pct_ci(a, n)] for k, (a, n) in r["by_kind"].items()] + [["both", pct_ci(r["agree"], r["pairs"])]]


def build_results() -> str:
    st = Settings()
    corpus = cc.make_corpus()
    res = compare(cc.as_dataset_rows(corpus))
    m = cc.evaluate(corpus, res)
    seen = cb.score(cb.load("compare_blind_seen.json"))
    held = cb.score(cb.load("compare_blind_heldout.json"))
    traps = sum(1 for x in corpus if x.trap_of)
    typed_rows = []
    kinds = sorted(m["typed"])
    for k in kinds:
        p, v = m["typed"][k].get("plain", [0, 0]), m["typed"][k].get("varied", [0, 0])
        typed_rows.append([k, f"{p[0]}/{p[1]}", f"{v[0]}/{v[1]}"])
    tr = m["recall_by_transform"]
    inside_k, inside_n = tr["(none outside the vocabulary)"]
    outside_k, outside_n = tr["(any outside the vocabulary)"]
    trows = [[k, f"{a}/{n}", pct(a, n)] for k, (a, n) in tr.items() if not k.startswith("(")]
    wrong_typed = m["wrong_typed"]

    return f"""# How well the comparison engine does, and what that does not tell you

*Generated by `python3 tools/make_compare_docs.py`; a test fails if this page is out of date. Every number below comes from that run. The sentences around them are the author's reading.*

## Read this first

**This measures the engine against a corpus its own author generated, and against two sets of pairs labelled by a language model (a Claude model, the same family as the assistant that wrote the engine) that was told not to read the code. It has never been run on a real requirements set.** Nothing here says how the engine will do on yours. What it does show is that the written rules do what the rules page says, that the traps built to catch a careless merge are caught, and, from the two labelled sets, roughly how often an engine of this kind agrees with someone else's reading of a pair, and where it stops reading.

Two numbers carry the honest summary:

- **It does not merge what differs.** No false merge in the corpus ({m['fp']} wrongly merged pairs out of {m['pred_pairs']:,}) and none in either labelled set ({len(seen['false_equivalent']) + len(held['false_equivalent'])} in {seen['pairs'] + held['pairs']} pairs).
- **It finds little of what a person would call the same.** On the 100 held-out pairs it agreed with the label on {held['agree']}. Of the 25 labelled EQUIVALENT it clustered {held['confusion']['EQUIVALENT'].get('EQUIVALENT', 0)}. By design: anything it cannot prove equal it leaves as a pair for a person.

## 1. The three sets, and how each was used

{table(["Set", "Who wrote it", "Size", "How it was used"], [
    ["Corpus (`reqin/tests/compare_corpus.py`)", "The engine's author, as a generator with a fixed seed: sentence templates, wordings of each, and *traps* (a requirement changed in exactly one way)", f"{len(corpus):,} requirements, {m['meanings']} meanings, {traps} traps", "While the engine was being built. Its failures found bugs in the engine, and the engine was fixed. **It is therefore not independent of the engine.** No numeric setting was tuned on it."],
    ["Seen pairs (`reqin/tests/labelled_pairs/compare_blind_seen.json`)", "A language model, from systems-engineering knowledge and the six label definitions, without reading the code", "150 labelled pairs", "Scored, and the disagreements were read and used to fix the engine (several bugs, below). **Not held out.** Kept as a regression floor."],
    ["Held-out pairs (`reqin/tests/labelled_pairs/compare_blind_heldout.json`)", "The same kind of writer, asked afresh with a different brief and told to write realistic pairs and not to read the repository", "100 labelled pairs", "Scored once, after the last change to how requirements are read, compared and typed. **The engine was not changed because of what it showed.** The gaps it found are listed below as gaps. Two later changes (the output checker, and a capital `L` read as litres, found while adding number tests) did not change any of the 100 answers; that was checked by scoring again."],
])}

How to read the labelled sets: for each pair the engine's answer is EQUIVALENT if both sentences are in one cluster; otherwise the type of the pair line with one sentence on each side (SUBSUMES also has to name the stricter sentence correctly); otherwise *nothing said*, which counts as agreement for a pair labelled UNRELATED and as a miss for any other label. A pair labelled `surface` is one the writer says can be read from the words, numbers and modals alone; `meaning` needs understanding of what the words mean. The writer, not the engine's author, chose those tags.

## 2. The corpus

{table(["", ""], [
    ["Requirements / different meanings / traps", f"{m['requirements']:,} / {m['meanings']} / {traps}"],
    ["Pairs of requirements that mean the same (truth)", f"{m['truth_pairs']:,}"],
    ["Pairs the engine put in one cluster", f"{m['pred_pairs']:,}"],
    ["Right / wrong / missed", f"{m['tp']:,} / {m['fp']} / {m['fn']}"],
    ["Precision (of the pairs it merged, how many were right)", pct(m['tp'], m['pred_pairs'])],
    ["Recall (of the pairs that mean the same, how many it merged)", pct(m['tp'], m['truth_pairs'])],
    ["B-cubed precision / recall (per requirement, so one big cluster does not dominate)", f"{100 * m['bcubed_precision']:.1f} % / {100 * m['bcubed_recall']:.1f} %"],
])}

**Recall depends almost entirely on whether the words are on the vocabulary.** The corpus has two kinds of wordings: those that use only words the engine's vocabulary knows (spelling, abbreviations and synonyms the author put in the list) and those that use synonyms and abbreviations the author deliberately left out of it. Of the first kind the engine joined {pct_ci(inside_k, inside_n)}. Of the second kind: {pct_ci(outside_k, outside_n)}. So the corpus says the vocabulary is the limit. The in-vocabulary figure is not a measure of the engine on real wording: the corpus's word lists were written by the same person who wrote the vocabulary, and that half of the corpus was built to be matched by it.

Recall by the way a meaning was reworded (a wording can have several; a wording that uses words outside the vocabulary counts under `syn_out` or `abbr_out`):

{table(["Reworded by", "joined with the plain wording", "share"], trows)}

The traps are requirements derived from another by changing one thing. The question is whether the engine says the right type for the pair (the base wording, the trap wording), and for SUBSUMES which one is stricter. Traps worded with words outside the vocabulary are not typed (the engine cannot be expected to relate them) and are left out of this table ({m['traps_outside_vocabulary']} of them). `plain` is the trap in its plain wording, `varied` is the trap reworded in the ways above.

{table(["Trap (what changed)", "plain: right", "varied: right"], typed_rows)}

Two groups of kinds in that table are weaker tests than the rest. For `qualifier`, `verb` and `other-reference` the only expectation is that the pair is not EQUIVALENT (not in one cluster); any other answer, or none, counts as right. For `swapped` and `subject` the expectation is UNRELATED, which the engine meets by saying nothing or by listing a near miss with a different subject; it passes when it makes no stronger claim. The other kinds need the exact type, and for SUBSUMES the stricter side.

Wrongly typed traps: **{len(wrong_typed)}**{'.' if not wrong_typed else ':'}
{chr(10).join(f"- {w['kind']}: expected {w['expected']}, engine said {w['got']}. A: {w['base']} B: {w['trap']}" for w in wrong_typed)}

What this does not show. The expected type of each trap is the generator author's reading of the taxonomy, so a rule the author misread would be misread the same way in the corpus; the labelled sets below are the check on that. One expectation was changed during the work: for a *negated* requirement ("shall not ... below 0") the corpus first expected a number trap to be a SUBSUMES or a CONFLICT. A blind pair showed the direction of a bound flips under negation, so the author changed the expectation to VARIANT and the engine to say only that the numbers differ (rule `Q-NEGATED`). That is a change made after seeing a result and is listed here for that reason.

## 3. Pairs labelled by someone else

### Held-out set: {held['pairs']} pairs, scored once

{table(["Pairs", "engine agrees with the label"], kind_rows(held))}

(The interval is how much a share measured on this few pairs could move by chance alone. It says nothing about whether the writer's labels were right.)

{matrix(held)}

What the engine said, and how often the label agreed:

{said_table(held)}

When the engine commits to a strong claim it has been right on this set: {held['said'].get('EQUIVALENT', (0, 0))[1]} of {held['said'].get('EQUIVALENT', (0, 0))[0]} EQUIVALENT, {held['said'].get('CONFLICT', (0, 0))[1]} of {held['said'].get('CONFLICT', (0, 0))[0]} CONFLICT, {held['said'].get('COMPLEMENTARY', (0, 0))[1]} of {held['said'].get('COMPLEMENTARY', (0, 0))[0]} COMPLEMENTARY, and {held['said'].get('SUBSUMES', (0, 0))[1]} of {held['said'].get('SUBSUMES', (0, 0))[0]} SUBSUMES (the two that were not are the label calling it a variant; whenever the label was SUBSUMES and the engine agreed it named the stricter side correctly, {held['subsumes_direction']['right']} of {held['subsumes_direction']['right'] + held['subsumes_direction']['wrong']}). It missed a lot. The two SUBSUMES calls the label disagreed with are the rule `COND-REGION`: 'when below 5 degrees C' against 'when below 0 degrees C'. The rule says the wider trigger is the stricter requirement, which is true as logic; both labels call it a variant because a person would ask which threshold was meant. A reasonable person may side with the label; the pair is typed SUBSUMES and not marked for review.

Why it disagreed (the cause of each is a reading by the engine's author; every one is listed in the appendix):

{cause_counts(held, HELDOUT_CAUSE)}

Of the {held['by_kind'].get('surface', (0, 0))[1]} pairs the writer called `surface` the engine agreed on {held['by_kind'].get('surface', (0, 0))[0]}. The misses are not random: they are the gaps in the written rules, listed in "Known gaps" below, and a fresh set of labelled pairs would be needed to show any fix of them is real rather than fitted to these.

### Seen set: {seen['pairs']} pairs, used to fix the engine

{table(["Pairs", "engine agrees with the label"], kind_rows(seen))}

{matrix(seen)}

{said_table(seen)}

**Do not read the surface figure here as a measure.** The disagreements in this set were read and the engine was changed to fix those that were bugs (below), so the {pct(seen['by_kind']['surface'][0], seen['by_kind']['surface'][1])} on `surface` pairs is what the engine scores on pairs it was fixed against. The same engine scored {pct(held['by_kind']['surface'][0], held['by_kind']['surface'][1])} on the same kind of pair it had not seen. The first is the figure to distrust; the second is closer to what to expect. The number of agreements before the first fix was not written down.

{cause_counts(seen, SEEN_CAUSE)}

## 4. What changed while this was measured

First run on the corpus, before anything was fixed: precision 99.69 %, recall 73.98 %. The corpus and the labelled pairs found these faults in the engine. Each was fixed, and each has a test case or a mutant (`tools/mutation/compare.py`) that fails when the fix is taken out: the stemmer did not join `-ied` forms (applied/apply); the passive was not turned into the active for irregular verbs (sent, reset); a number inside one condition was compared with a number inside a different condition; a bound under a negation was read as if it were not negated (now `Q-NEGATED`); conditions joined by "and" were compared in the order written; a leading condition with no comma was not read; a leading plus-or-minus was not a bound; a tighter tolerance was not told from a looser (`Q-TOLERANCE-TIGHTER`); a wider trigger region was not told from a narrower (`COND-REGION`); a range was read like a limit (`Q-RANGE`). Earlier, hand tests found number-reading faults: a range written with "-", a tolerance across `voltage` and `voltage_dc`, a missing litre unit, "over 30 days" read as a bound, and a leftover "in" before "no more than". They are now cases in `QUANTITY_CASES`; four of those cases were only added later, when it turned out the fixes had none. The corpus generator itself had two faults that the engine's output exposed (a subject taken from the wrong relation made different meanings identical, producing three false merges that were the generator's, not the engine's; a missing comparator key).

Found while writing the rule tests, after the held-out set had been requested and before it was scored: one rule (`Q-OVERLAP`) could never fire and was removed; a number with a plus-or-minus tolerance could be reported as a conflict when the allowed ranges overlap, and is now only a variant; and "in 5 s" against "within 5 s" was a word difference and is now `Q-UNSTATED`.

Found after the held-out set was scored (none of its 100 answers changed): `check-compare` did not notice that a dataset had changed since the output was made, and a capital `L` was not read as litres, so "5 L" and "5000 ml" were different quantities. Neither was found by a labelled pair.

One setting moved: `tau_pair` from 0.6 to 0.5, after a four-word toy example fell between the two, and before the corpus was measured. It only decides which pairs of *different* wordings are listed; it never changes a cluster or a type.

## 5. Where the rules came from

{table(["Rule", "Decides", "Source", "Note"], [[f"`{r}`", RULES[r][0], SOURCE[r][0], SOURCE[r][1]] for r in RULES])}

The machinery around the rules:

{table(["Part", "Source", "Note"], [[a, b, c] for a, b, c in MACHINERY])}

"Research" means the report states it; it does not mean anyone has shown it right on real requirements. The report itself says no study validates slot-wise comparison against human judgements of equivalence.

## 6. Known gaps (found by the held-out set, deliberately not fixed)

These are the surface-readable cases the held-out set showed the engine cannot read. They were left alone so that the set stays a measure of an engine that had not seen it. Each fix should be made, and then measured on a new set written afresh.

{chr(10).join(f"- **{GAP_LABEL[c]}** ({sum(1 for w in held['wrong'] if w['kind'] == 'surface' and HELDOUT_CAUSE.get(w['id']) == c)} pair(s): {', '.join(w['id'] for w in held['wrong'] if w['kind'] == 'surface' and HELDOUT_CAUSE.get(w['id']) == c)})" for c in ('extra-clause', 'only', 'passive-tail', 'range', 'comparator-phrase', 'trigger', 'tolerance-range', 'units', 'cond-region', 'different-words'))}

And what the engine does not attempt at all, so no set could show it: paraphrase and anything that needs the meaning of the words ({sum(1 for w in held['wrong'] if w['kind'] == 'meaning')} of the {held['by_kind'].get('meaning', (0, 0))[1]} held-out `meaning` pairs it missed), another language, the hierarchy and links between requirements, and several sentences in one requirement. The list of limits is also at the end of [`COMPARE_FORMAT.md`](COMPARE_FORMAT.md).

## 7. How big it can get

Measured once on one machine (a shared cloud container), by `reqin/tests/compare_scale.py` and `reqin make-datasets --only F9 --size 25000`: 25,000 made-up requirements took about 6 seconds and 300 MB of memory and wrote 24 MB; 100,000 requirements built from a word list where a few words are very common took about 25 seconds. The 25,000 of the F9 dataset are copies of a few wordings, so they collapse into groups; the word-list input is the harder case for finding near misses. Both are made up. The engine scales with the number of different wordings, and refuses to be slow in the two places where it could be: a word found in more than `max_posting` ({st.max_posting}) wordings is not used to find near misses, and a wording with more than `max_family` ({st.max_family}) numberings is not compared with each of them. Both are counted in `compare.json` and said in `notes`. What is not shown: real requirements are not words drawn from a list, so the real worst case may be different.

## 8. Not checked

- **It has never run on a real requirements set**, of any size or kind. Everything here is made up, and so is every number.
- The labels in both labelled sets were written by a language model of the same family as the one that wrote the engine. They are not human judgements and share this family's habits of reading. No person has labelled a pair for this engine.
- The held-out set is 100 pairs. The intervals above are wide, and one set is one draw.
- The output format ([`COMPARE_FORMAT.md`](COMPARE_FORMAT.md)) has not been read by a person other than its author, and no screen uses it yet.
- The vocabulary is a short starting list chosen by the author and measured on nothing real.
- Languages other than English, and requirements in table or diagram form, were not tried.

## Appendix A: every disagreement in the held-out set

{wrong_list(held, HELDOUT_CAUSE)}

## Appendix B: every disagreement in the seen set

{wrong_list(seen, SEEN_CAUSE)}
"""


def build_format() -> str:
    text = FORMAT_MD.read_text(encoding="utf-8")
    a, b = text.index(BEGIN), text.index(END)
    return text[: a + len(BEGIN)] + "\n" + rules_table() + "\n" + text[b:]


def main(argv: list[str]) -> int:
    new_format, new_results = build_format(), build_results()
    if argv == ["--check"]:
        stale = [p.name for p, new in ((FORMAT_MD, new_format), (RESULTS_MD, new_results)) if not p.exists() or p.read_text(encoding="utf-8") != new]
        if stale:
            print("out of date: " + ", ".join(stale) + "  (run: python3 tools/make_compare_docs.py)")
            return 1
        print("docs/COMPARE_FORMAT.md and docs/COMPARE_RESULTS.md are current")
        return 0
    FORMAT_MD.write_text(new_format, encoding="utf-8")
    RESULTS_MD.write_text(new_results, encoding="utf-8")
    print("wrote", FORMAT_MD.relative_to(ROOT), "and", RESULTS_MD.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
