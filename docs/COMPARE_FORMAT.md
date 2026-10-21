# What the comparison engine writes: the `reqin-compare/1` folder

**Status of this page: written before the code, then corrected to match it. Not yet read by anyone but the person who wrote the engine.** If the format is wrong for a screen, change this page first and then the engine. No screen uses this output yet: the prototype still draws its clusters from a made-up sample ([`prototype/README.md`](../prototype/README.md)). A test (`tools/test_compare_docs.py`) fails if the table of rules below stops matching the code.

## What the engine is, and is not

The first four stages of the nine in the research report, with **no AI, no network, and no model**: read a dataset, find the numbers, units, comparators, modals, negations and conditions in each requirement, compare requirements by written rules, and group the ones that are provably the same. Everything it writes is a **draft** with provenance `mechanical`. It never writes to a requirement, and a person's decision (in the page, or on the shared server) always outranks it.

It is strict on purpose. **Two requirements are called EQUIVALENT only when every slot is equal**: same subject, same kind of modal (`shall` and `must` are one kind), same polarity, same words after a short written list of spelling variants (and any synonyms a project adds), same condition, same numbers in the same units. Anything it cannot prove equal stays a *pair* a person (or, later, the AI stage) looks at. So its recall on paraphrase is low by design, and its pairs of "nearly the same words" are the work queue, not the result. [`COMPARE_RESULTS.md`](COMPARE_RESULTS.md) says how low, measured on made-up requirements.

## Running it

```bash
reqin compare DATASET_DIR [DATASET_DIR2 ...] --out-dir OUT_DIR [--vocab FILE] [--json]
reqin check-compare OUT_DIR [--dataset DATASET_DIR ...] [--recompute [--vocab FILE]] [--json]
reqin compare-vocab FILE [--starter]
```

- `compare` takes one dataset, or several (two imports of the same specification are the usual reason). It refuses a dataset that fails its own contract (`reqin check-dataset`) and two datasets that share an internal key, and writes nothing (exit 2). **When there is nothing to compare it still exits 0 and says so** in `notes`.
- `OUT_DIR` must be empty or an earlier output folder; nothing else is ever overwritten (exit 2 if it holds other files).
- `check-compare` exits 1 and lists the problems when the folder does not follow this page. With `--dataset` (once for each dataset used) it also checks that the folder was made from exactly those datasets, unchanged, and that every position in it is real. With `--recompute` as well it runs the engine again and requires the three files to be byte for byte what it writes now (give the same `--vocab FILE` the folder was made with); without it, a file edited together with the checksum that names it passes.
- `compare-vocab FILE` writes the vocabulary the engine uses as a file to edit and pass to `compare --vocab` (it refuses to overwrite). `--starter` adds a few optional synonyms (display/show, record/log, enable/activate, ...). Each is a decision that two words mean the same everywhere in your requirements, and some do not, so none is on by default.
- The same dataset and the same vocabulary give **byte-identical files** on every run, whatever order the requirements were read in.

## The folder

| File | One line per | What it holds |
|---|---|---|
| `clusters.jsonl` | cluster of two or more requirements | members, which one to show first and why, and what the members have in common |
| `pairs.jsonl` | typed relationship between two groups | the type, the rule that decided it, the reasons in words, and where in the text the differences are |
| `slots.jsonl` | requirement | what the engine found in each one: subject, modal, polarity, conditions, quantities, with character positions |
| `compare.json` | (one file, written last) | counts, the settings used, plain-language notes, and the size and SHA-256 of the other files. A folder without it is an unfinished write |

All text is UTF-8, one JSON object per line, keys sorted. Every cluster and pair carries `"status": "draft"` and `"provenance": "mechanical"`.

### Who is in a pair

Requirements with equal keys (the engine's meaning of "the same wording") are one **group**; a group with two or more members is a **cluster**. A relationship holds between every member of one group and every member of the other, so a line in `pairs.jsonl` names two sides, not two requirements: a cluster of 40 against a cluster of 40 is one line, not 1,600.

```json
"a": {"mids": ["m_16b3b2656574", "m_f1e853bcf23e"], "clusters": ["C-9e09252255"], "scope": "group"},
"b": {"mids": ["m_51cd22e4b1e7"],                  "clusters": [],                "scope": "group"}
```

- `scope` is `group` when the side is one group of equal keys. It is `words` for a near miss between two wordings found by shared words (`WORDS-DIFF`, `SUBJ-DIFF`): the side then names **every** requirement that has that subject and those predicate words, in all their numberings, because the relationship is about the wording.
- `clusters` lists the clusters that touch the side (empty for a group of one; a `words` side can touch several).
- `shown_a` and `shown_b` are the one requirement from each side whose text the `why` positions refer to. `mids` are internal keys from `requirements.jsonl`; a screen shows `uid` and `text`, never the `mid`.
- `a` and `b` are ordered by the lowest internal key on each side, so a pair has one form and one `pid` however the engine reached it.

### `clusters.jsonl`

```json
{"cid": "C-9e09252255", "status": "draft", "provenance": "mechanical",
 "members": [{"mid": "m_f1e853bcf23e", "uid": "PUMP-001"}, {"mid": "m_16b3b2656574", "uid": "PUMP-002"}],
 "representative": "m_f1e853bcf23e", "representative_basis": ["lowest id"],
 "rung": "masked",
 "why": ["same subject: The pump controller", "numbers written differently but equal: within 5 s; within 5000 ms"],
 "valid": true, "min_word_overlap": 0.6364,
 "related": ["P-6a9a9838df", "P-7c48ccb8bc"], "related_total": 2}
```

- `rung` is the **weakest** comparison that still makes every member equal: `exact` (same words apart from case, spacing and punctuation), `masked` (same words apart from the numbers, which are equal after converting units), `canonical` (needed the vocabulary, a changed word order of clauses, the passive voice, or ignored words).
- `valid` is the check made on every cluster: every pair of members must itself be EQUIVALENT by the rule function (all pairs up to 30 members, each against the first above that). It is `true` for every cluster this engine writes, and the checker refuses a folder where it is not. It is in the file so a later stage, or a person, can see it was checked.
- `min_word_overlap` is the smallest share of words (plain, not weighted) that any member has in common with the representative, 0 to 1. A low number means a cluster whose members read very differently.
- `related` lists up to 50 pairs (by `pid`, most serious first) that touch this cluster; `related_total` is how many there are. They are notes on the cluster. They are never members.
- `representative` is a **proposal**: the member to show first. Order: it is in a named baseline; its status says approved, baselined, released, published, accepted or frozen; most of the six well-known fields (rationale, verification, allocation, owner, baseline, status) are filled in; its id is the source's and not invented by the importer; then the lowest id. `representative_basis` names the first of these that told it apart from the runner-up. The research report found no evidence for any rule, so this is its own proposal, simplified, and a person's choice outranks it.

### `pairs.jsonl`

```json
{"pid": "P-6a9a9838df", "status": "draft", "provenance": "mechanical",
 "a": {"mids": ["m_16b3b2656574", "m_f1e853bcf23e"], "clusters": ["C-9e09252255"], "scope": "group"},
 "b": {"mids": ["m_51cd22e4b1e7"], "clusters": [], "scope": "group"},
 "shown_a": "m_f1e853bcf23e", "shown_b": "m_51cd22e4b1e7",
 "type": "CONFLICT", "direction": null, "basis": "slot", "rule": "NEG-CONFLICT", "needs_review": true,
 "score": 0.758, "rung": "overlap",
 "features": {"exact": false, "masked_equal": false, "masked_ratio": 0.875, "overlap": 0.4658, "canonical_overlap": 0.758},
 "why": [{"code": "polarity_conflict", "text": "B says 'not' and the other does not; both cannot hold", "a_span": [20, 25], "b_span": [26, 29]}],
 "words_only_a": [], "words_only_b": []}
```

| Field | Values and meaning |
|---|---|
| `type` | `VARIANT`, `SUBSUMES`, `CONFLICT`, `COMPLEMENTARY`, `UNRELATED`. `EQUIVALENT` is never written here: those are clusters. `UNRELATED` is written only for the near miss "the same words about a different subject", so a person can see why it was not merged; a screen may hide it |
| `direction` | For `SUBSUMES` only: `"a"` or `"b"`, the **stricter** requirement, the one that implies the other. Otherwise `null` |
| `basis` | `slot` (a modal, polarity, condition or number differs and the words are the same), `words_differ` (same subject, different predicate words), `subject` (same predicate words, different subject) |
| `rule` | The id of the rule that decided the type, from the table below. When findings of different kinds meet, the order is CONFLICT, then VARIANT, then COMPLEMENTARY, then SUBSUMES; stricter in different directions at once is `MIXED` |
| `needs_review` | `true` exactly for `VARIANT` and `CONFLICT`: nothing mechanical can finish those |
| `score` | The rarity-weighted overlap of the two wordings' canonical words, 0 to 1. **It is not a probability and not a confidence.** It sorts pairs within a type. It never decides a type |
| `rung` | The strictest rung of the ladder at which the two matched (`exact`, `masked`, `canonical`, `overlap`) |
| `features` | The numbers behind the score, so a person can see why the pair was suggested |
| `why` | Each difference found, in words, with `a_span` and `b_span`: `[start, end)` offsets into the `norm_text` of `shown_a` and `shown_b` (see below); `null` when the difference is something one side lacks |
| `words_only_a`, `words_only_b` | For `words_differ` and `subject` pairs: the words in only one wording after the vocabulary was applied |

Pairs are listed most serious first: CONFLICT, VARIANT, SUBSUMES, COMPLEMENTARY, UNRELATED, and by score within a type.

### `slots.jsonl`

```json
{"mid": "m_f1e853bcf23e", "uid": "PUMP-001", "span_in": "norm_text", "text_differs": false,
 "subject": {"text": "The pump controller", "span": [0, 19], "key": ["pump", "controller"]},
 "modal": {"text": "shall", "span": [20, 25], "class": "mandatory"},
 "negated": false, "negation_span": null, "passive": false, "compound": false, "no_modal": false,
 "conditions": [],
 "quantities": [{"raw": "within 5 s", "span": [42, 52], "role": "main", "value": 5.0, "value_hi": null, "unit": "s", "dimension": "time",
                 "comparator": "<=", "interval": [null, 5000.0], "closed": [false, true], "base_value": 5000.0, "tolerance": null}],
 "predicate_key": ["start", "motor"], "key_digest": "666803d3891775dc"}
```

- **Spans are offsets into `norm_text`**, the importer's normalised form, not into `text`. When the two differ (markup or odd whitespace was removed) `text_differs` is `true` and a screen must not draw these spans on `text`.
- `modal.class` is `mandatory` (`shall`, `must`), `goal` (`should`), `fact` (`will`), `optional` (`may`) or `none`.
- `conditions` has one entry per condition (`trigger`, the text, its span, and `key`: the trigger word and the condition's words after the vocabulary). A condition may come first ("When the level is low, ...") or last; the key is the same either way.
- `interval` is the meaning of the quantity as a range of values, in the base unit of its dimension (`null` is unbounded). `closed` says whether each end is included. A bare number with no comparator is `comparator: ""` and `interval: null`: the engine can compare it for equality but never say which is stricter. A range ("between 5 and 10 s") is `comparator: "range"` with `value_hi`.
- `role` is `main` or `condition`: a number inside a condition ("when the temperature exceeds 80 degrees C") is compared with condition numbers only.
- `passive` is `true` when the requirement was read as `... shall be <verb>ed by <agent>` and turned into its active form for comparison. `compound` is `true` when there is more than one modal; `no_modal` when there is none. Both are compared as written and counted in `notes`.
- `key_digest` is a short hash of everything the engine compares. Equal digests are the engine's definition of "the same wording".

### `compare.json`

```json
{"format": "reqin-compare/1", "status": "draft", "provenance": "mechanical",
 "engine": {"name": "reqin-compare", "version": "1", "rules": ["COND-ABSENT", "..."], "vocabulary": "default", "vocabulary_sha256": "bcd092fc..."},
 "datasets": [{"manifest_sha256": "70d1a3b8...", "requirements": 6}],
 "settings": {"tau_pair": 0.5, "max_posting": 100, "max_family": 300, "max_related": 50},
 "counts": {"requirements": 6, "groups": 5, "clusters": 1, "in_clusters": 2, "singletons": 4,
            "pairs": {"VARIANT": 0, "SUBSUMES": 2, "CONFLICT": 2, "COMPLEMENTARY": 0, "UNRELATED": 0}},
 "limits": {"tokens_too_common_to_find_pairs": 0},
 "notes": ["No requirement has a parent: the hierarchy was not used (the engine does not use it either way)."],
 "files": {"clusters.jsonl": {"bytes": 460, "sha256": "3e30eb2e...", "lines": 1}}}
```

- `settings`: `tau_pair` is the share of rarity-weighted words two *different* wordings must have in common before a near miss between them is listed (it never changes a cluster or a type); `max_posting` is how many wordings a word may appear in and still be used to find near misses; `max_family` is how many different numberings of one wording are compared pairwise; `max_related` is the most pairs listed on a cluster. None of the four was tuned on the corpus in `COMPARE_RESULTS.md`; `tau_pair` was moved from 0.6 to 0.5 after a four-word example, before anything was measured.
- `limits` counts what was left out, so a screen can say so. `tokens_too_common_to_find_pairs` is the number of words not used to find near misses; `families_not_compared_pairwise` appears when a wording had more than `max_family` numberings. Requirements with equal keys are always grouped whatever these say.
- `notes` says plainly, in words, what a screen should say when something is missing: **nothing to compare** (no requirements, or one), **nothing found** (no two requirements are equivalent and no pair overlaps enough to list), how many requirements have no text, no modal or several modals, ids invented by the importer, no hierarchy, and any limit above that applied. "Nothing to compare" is an answer, not an error.
- `vocabulary_sha256` is the checksum of the vocabulary used, including its `fold_plurals` setting (the shipped one, or `--vocab FILE`, which replaces it completely and is checked for shape); two runs with different vocabularies can be told apart.

## The ladder: how candidates are found

| Rung | Compares | Used for |
|---|---|---|
| 1 `exact` | the words, lower-cased, with spacing and punctuation collapsed | the fast path |
| 2 `masked` | the words with each quantity replaced by one placeholder (and a fuzzy ratio on that) | finding pairs that differ only by a number or unit, which is the commonest and most dangerous difference |
| 3 `overlap` | the set of words, each weighted by how rare it is in this dataset | finding pairs whose wording differs, and ranking them |
| 4 `canonical` | the same after the vocabulary (spelling variants, abbreviations, and the synonyms a project adds), `-ed`/`-ing` stemming (plurals only when the vocabulary sets `fold_plurals`) and dropping the few words in the ignore list (the, a, an, that, which) | removing differences that are only spelling |

Rungs 1 to 4 produce **features and candidates**. They never decide a type. Types come only from the rules.

## How two requirements are compared

1. **Slots.** Each requirement is cut into: quantities (a number with a unit, how it is bounded, an optional tolerance; a number is a bound only after a comparator word such as 'at least', 'within' or 'not more than': a bare number, a version-like number and a count after 'under' or 'above' are compared as written, and 'up to' is bounded in no direction), a leading condition (up to the first comma, or in a comma-less sentence up to the last *the/a/an* before the modal), the first modal and a `not`, `never` or `no longer` straight after it (a `not` inside a bound such as "not exceed 5 kg" is part of the bound), a trailing condition (`when`, `if`, `while`, `after`, `before`, `during`, `upon`, `once`, `until`, `unless`, ...), then the subject (before the modal) and the predicate (after it).
2. **Equal keys.** Requirements with equal subject, modal kind, polarity, predicate words, conditions and numbers are one group; two or more make a cluster.
3. **Families.** Requirements with the same subject and predicate words but different keys are compared slot by slot by the *slot* and *number* rules below. These are the pairs whose difference is a modal, a negation, a condition or a number.
4. **Near misses.** Wordings that differ in subject or predicate words are only compared when they share enough rare words (`tau_pair`). Then only two statements are made: the same predicate about a different subject (`SUBJ-DIFF`, `UNRELATED`) and the same subject with different predicate words (`WORDS-DIFF`, `VARIANT`).
5. **Clusters** are only ever groups of equal keys, checked pair by pair. The engine contains complete-linkage clustering (`merge_cliques`) so a future rule that makes "equivalent" fuzzier cannot chain `a~b`, `b~c` into one cluster when `a~c` is false; with today's rules it never has anything to split.

## The rules

Every rule has an id, a type and a sentence saying what it does, and a test that fails when the rule is removed (`tools/mutation/compare.py` removes or reverses each one in turn). The list is `RULES` in [`reqin/src/reqin/compare/rules.py`](../reqin/src/reqin/compare/rules.py); this table is generated from it by `python3 tools/make_compare_docs.py` and checked by a test, so they cannot drift.

<!-- rules:begin -->
| Rule | Decides | What it says |
|---|---|---|
| `EQ-DIGEST` | EQUIVALENT | Same subject, modal, polarity, predicate words, conditions and quantities after the vocabulary and unit conversion. |
| `MODAL-DIFF` | VARIANT | Everything else is equal but the modal differs in kind: shall or must (mandatory), should (goal), will (fact), may (optional). A person decides which applies. |
| `NEG-CONFLICT` | CONFLICT | The same subject, words, conditions, modal and numbers, one saying 'shall' and the other 'shall not' (or never): both cannot hold. |
| `NEG-COND` | VARIANT | One is negated and the other is not, but their conditions differ, so they might both hold in different situations. |
| `COND-ABSENT` | SUBSUMES | Everything else is equal, one has a condition and the other has none: the one with no condition applies always, so it is stricter. |
| `COND-DIFF` | VARIANT | Both have conditions and the conditions differ (different words, or a different kind: when, if, while, after, ...). |
| `COND-VALUE` | VARIANT | The conditions use the same words but a different number or unit, and the two trigger ranges are not nested (or one has no stated bound), so a person decides. |
| `COND-REGION` | SUBSUMES | The conditions begin with when, if or while, use the same words, and one trigger range contains the other ('when above 80' contains 'when above 90'). The requirement that applies in more situations is stricter. Not said for 'unless', 'until', 'after' and the like: which side applies is not read. |
| `Q-SUBSUMES` | SUBSUMES | One number's allowed values lie strictly inside the other's (within 2 s is inside within 5 s; at least 99.9 percent is inside at least 99 percent). The narrower one is stricter. |
| `Q-CONFLICT` | CONFLICT | The allowed values do not overlap: exactly 5 s and exactly 10 s; at most 5 s and at least 10 s. No value can satisfy both. Said only when the conditions and the modal are the same: 'within 2 s when the tank is full' and 'at least 10 s when the tank is empty' may both hold, and are left as differing in condition. |
| `Q-BOUNDS` | COMPLEMENTARY | One is only a lower bound and the other only an upper bound of the same quantity, and they overlap: together they give a range. |
| `Q-UNSTATED` | VARIANT | A number is written without a bound on one or both sides ('5 s' against 'at most 5 s', or two bare numbers that differ), or with 'up to', which is a limit in one requirement and a capacity in another. Without the direction nothing stronger can be said. |
| `Q-TOLERANCE` | VARIANT | The same value and bound but a plus-or-minus tolerance on one side only; or different values where at least one has a tolerance (the engine does not combine a tolerance with a bound, so it says only that they differ). |
| `Q-TOLERANCE-TIGHTER` | SUBSUMES | The same value and bound, both with a plus-or-minus tolerance, and one tolerance is smaller. The tighter band is stricter. |
| `Q-EXTRA` | SUBSUMES | One states a bounded quantity of a kind the other does not mention. The one with the extra constraint is stricter. |
| `Q-EXTRA-UNSTATED` | VARIANT | One has a number of a kind the other lacks, and that number has no stated bound. |
| `Q-NEGATED` | VARIANT | A requirement is negated ('shall not ... below 0'), so which side of a bound is allowed is reversed and the engine does not read the direction: only that the numbers differ. Also written when one is negated and the other is not and their numbers differ ('shall not open within 2 s' does not contradict 'shall open within 10 s'). |
| `Q-RANGE` | VARIANT | At least one number is a range ('between 5 and 10 s'). Whether the wider range is the stricter ('shall operate between') or the narrower ('shall respond between') depends on the meaning, so nothing stronger than 'differs' is said. |
| `Q-MULTI` | VARIANT | Several numbers of the same kind that cannot be matched one to one. |
| `MIXED` | VARIANT | Different slots point in different directions (one is stricter in one way and looser in another), or a range bound comes with another difference. |
| `UNEXPLAINED` | VARIANT | The engine saw different keys and could not say which slot differs. This should never be written; a test fails if it is. |
| `WORDS-DIFF` | VARIANT | The same subject, and the predicate words differ in a way no rule explains (or are the same words in a different order). Written only when the wordings overlap enough to be worth a look. |
| `SUBJ-DIFF` | UNRELATED | The same predicate words about a different subject. A near miss, written so a person can see why it was not merged. (Subject and object swapped is not caught: the words are not the same predicate.) |
<!-- rules:end -->

Where the rules came from is in [`COMPARE_RESULTS.md`](COMPARE_RESULTS.md): the six types and the idea of strict, rule-named typing are from the research report; the individual rules are the engine author's own and have not been checked against anyone's real requirements.

## What the engine does not do

- **Paraphrase and meaning.** Different words for the same idea stay different unless the idea is on the short written vocabulary, and the default vocabulary holds only spelling variants (initialise/initialize). A person owns that list (`--vocab FILE`; `reqin compare-vocab FILE --starter` writes one with a few synonyms to start from). Plural words are different words ("the pump", "the pumps") unless the vocabulary sets `fold_plurals`.
- **Another language**, and anything in a script the word rules do not know.
- **Extra clauses.** "shall contain a timestamp" against "shall contain a timestamp and the operator identifier" is a `WORDS-DIFF` variant, not a subsumes: the engine does not read "and ..." as an added obligation, and does not read "only" at all.
- **Which way a number points under a negation** ("shall not start below 0 s") or inside a range ("between 5 and 10 s"): it says the numbers differ (`Q-NEGATED`, `Q-RANGE`), never which is stricter.
- **A tolerance combined with a bound**: "5 s ± 1 s" against "6 s ± 1 s" is a variant that says the numbers differ; the tolerance is not applied.
- **Number words** other than a short list ("five seconds"; only next to a unit), fractions, numbers with their unit far from them ("a rate of 5, in seconds"), rates written with words ("10 litres per minute"; only the form "10 l/min" is read), and data sizes in different units (1 GB and 1000 MB are not called equal: nobody can tell whether 1000 or 1024 was meant).
- **Voice.** Active and passive are matched only in the plain form `... shall be <verb>ed by <agent>`, with a short list of irregular verbs. A `by` phrase that is a place ("by the door"), a manner ("by default") or a method ("by dividing ...") is not an agent. One that names a means ("sent by encrypted link") is read as an agent and merged with the active; the cluster's `why` says some members are active and some passive.
- **Case.** Words are compared without case, except in the units on the table (`mHz` and `MHz`). "pump P1" and "pump p1", or two unknown units that differ only in case, are one wording.
- **`Up to`.** "up to 5 s" is not read as a bound in either direction ('a delay of up to 5 s' is a limit, 'support up to 100 users' a capacity), so it differs from "at most 5 s" (`Q-UNSTATED`).
- **A relative clause** ("the time when the fault occurred") is read as a condition, so it can be typed `COND-ABSENT` against the same words without it. It is never merged, and the type and direction are a guess.
- **Subject and object swapped** ("the charger powers the battery" against "the battery powers the charger"): not merged, and not described either.
- **The hierarchy and the links** between requirements: the engine does not use them.
- Requirements with several sentences or several modals are compared **as written**: equivalent only when everything matches.
- **Scale.** Near misses are found through words that appear in at most `max_posting` wordings, and a wording is compared with its other numberings only up to `max_family` of them; what was left out is counted in `limits` and said in `notes`.
- It has **never run on a real requirements set**. Its measured precision and recall are on made-up requirements and on pairs labelled by a language model ([`COMPARE_RESULTS.md`](COMPARE_RESULTS.md)); they say how well the rules do what they say, not how well the engine does on yours. No number from there may be shown on a screen as if it were a property of a real requirement set.
