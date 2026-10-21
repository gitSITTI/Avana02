# Prompt: build the first mechanical stages of the comparison engine

How to use this: give an agent that can run commands in a checkout of this repository the text below the line. **This engine does not exist yet**; this is the first slice, and it is deliberately small and measured. Review what comes back before anything is built on it.

----------------------------------------------------------------------------------------------------

You are building the first stages of a requirements comparison engine in a repository that already reads requirements into one canonical dataset, has screens that show clusters, and has a way to turn labelled pairs into precision and recall with a range. The engine itself is missing. Read `AGENTS.md` in the repository root first and keep its rules: **no real data, a new test must be shown to fail, and say what you did not check.**

## Read, in this order

1. `docs/Requirements comparison app research.md`, the section "Nine stages keep mechanics first, AI late, and humans in charge": the table and the placeholder numbers. You are building stages 1 to 4 **without any AI**. The numbers there are the researchers' starting points; they say themselves that they are not validated.
2. `reqin/GUI_CONTRACT.md` sections 2 and 3: the canonical dataset you read (`requirements.jsonl`, with `norm_text` and `slots`). Do not read a source file directly; read a dataset.
3. `docs/GOLD_SET.md`: how precision and recall are estimated from labelled pairs, and why random pairs are not enough.
4. `docs/V_MODEL.md` and `docs/GUI_DESIGN_GUIDE.md`, briefly: what the screens will show, so the output carries what they need (why a pair was suggested, never just a score).

## Build

In a new package `reqin/src/reqin/compare/` (standard library first; a dependency needs a reason written down):

1. **Normalise and extract slots** from each requirement: modal (shall, should, will, may, shall not), polarity, numbers with units and comparators, conditions. Keep character spans so a screen can highlight them.
2. **A similarity ladder** that produces candidate pairs with a feature vector for each: exact match of normalised text, then a masked fuzzy match, then token overlap weighted by rarity, then (only if you can justify it) one more. For every pair keep **why**: which feature, which words, which slot differs.
3. **Slot-equality rules** that stop two requirements being called equivalent when a number, unit, comparator, modal or polarity differs. Never rely on a similarity score alone for these.
4. **Typed edges**: EQUIVALENT, VARIANT (same meaning, a value differs), SUBSUMES, CONFLICT, COMPLEMENTARY, UNRELATED, from the slot differences, by written rules.
5. **Clustering** of EQUIVALENT edges only, a validity check on each cluster, and a canonical representative. Other edge types stay as notes on the cluster, never as members.
6. **Output files** for the screens, in a format you **write down first** in `docs/COMPARE_FORMAT.md` and have a person look at before you build on it. Every cluster and every pair is marked as a **draft** with its provenance: mechanical.

## Measure

- Write a **labelled synthetic corpus** with known answers, in `reqin/tests/`: made-up requirement templates, each in several wordings (reordered, synonyms from a short fixed list, abbreviations), plus **traps** (a changed number, a changed unit, a negation, a different modal, a different subject). The answers are known because the generator wrote them.
- Report precision and recall of pairs and of clusters on it, and the cases that are wrong, as a table.
- **Say plainly that this measures the engine against a corpus written by the person who wrote the engine.** It shows that the rules do what they say and that the traps are caught. It does not show how the engine does on real requirements, and no number from it may appear on a screen as if it did.
- Do not tune thresholds on the labelled sample the screens use. Pick a rule, write why, test it, and leave the threshold where the reasoning put it.

## Rules

- No call to a model, no network, deterministic output (a fixed seed wherever there is a choice), the same result on every run.
- The engine never writes to a field a person has approved. Everything it produces is a draft.
- Do not touch the AI gate or the gateway. When AI comes (stage 5), it goes through them.
- Do not push, and do not change a remote or any CI setting.

## Done means

1. `python3 -m pytest -q` in `reqin/` passes with your new tests, and **each rule has a test that fails when the rule is broken** (add a script in `tools/mutation/` that breaks the engine one rule at a time, in the style of the others there, and run it).
2. A dataset written by `reqin make-datasets` (the fourteen deliberately different ones) runs through the engine without an error, and the output says plainly when a dataset has nothing to compare (no hierarchy, no ids, one requirement).
3. `docs/COMPARE_FORMAT.md` describes the output, and every statement in the README's table "What has and has not been checked" that you touched is still true.

## Report

What you built, the table of results on the synthetic corpus with the wrong cases listed, which rules came from the research and which you made up, what the engine cannot do (paraphrase, translation, anything needing meaning), and **Not checked**: above all, that it has never run on a real requirements set.
