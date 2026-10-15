# The gold set: how the precision and recall numbers become real

Every score on the Methods and metrics page used to be a placeholder. A placeholder shows the layout and says nothing about whether a method finds the right pairs. The only way to make it real is to have people look at pairs of requirements and say what they are. That list of labelled pairs is the **gold set**. This page says how the prototype builds one, what it counts, how sure it is, and what it does not do.

Nothing here has been used on a real program. The demonstration has made-up labels that you can load and remove.

## What a person does

On **Label pairs** a person sees two requirements and picks one of six answers:

| Answer | Counts as |
|---|---|
| Same requirement | related |
| Same topic, different value | related |
| One contains the other | related |
| They contradict | related |
| Different things | not related |
| Cannot tell | left out of the numbers |

The page is **blind**. It does not say whether the app clustered the pair, what the scores were, or what the AI thought. A person who has seen the app's answer tends to agree with it, and that would make the app look better than it is. Keys 1 to 6 choose an answer, a note can travel with the label, a skipped pair comes back last, and the last label can be undone.

## Which pairs are offered

A plain random sample would be almost all unrelated pairs. In the demonstration world (1,248 requirements) there are about 105,000 pairs inside the allocations and 1,294 of them are in a cluster, so 160 random pairs out of about 778,000 would hold, on average, less than one cluster pair and the numbers would mean nothing. The pairs from different allocations, which the app never compares, number about 673,000. So the pairs are drawn from four groups on purpose and each group is weighted by the number of pairs it stands for:

| Group | What it is | Drawn |
|---|---|---|
| A | Pairs the app put in the same cluster | 50 |
| B1 | Same allocation, not clustered, but the text match or the keyword overlap is 0.6 or more: the near misses | 60 |
| B2 | The rest of the pairs inside one allocation | 25 |
| C | Pairs from different allocations, which the app never compares | 25 |

Inside a group the draw is a simple random sample with a fixed seed, so the same project always offers the same pairs in the same order. The order is mixed: the next pair always comes from the group that is furthest behind its share, so stopping early still leaves a fair sample of each group.

**Every fifth pair goes to a second person.** Nobody sees another person's label. When two people have labelled the same pairs the page shows how often they agree and the agreement beyond chance (kappa). When they disagree, the pair is shown to the lead, who settles it; the original labels stay in the record. A pair with two labels that name different relations but are both "related" is a dispute about the kind of relation, and still counts as related. A pair labelled "related" by one person and "different things" by the other is left out of the numbers until it is settled.

## How the numbers are worked out

For a method (the app's clusters, or one of the two scores at a cut-off you pick):

- **Precision** is of the pairs the method flagged, the share that are related.
- **Recall** is of the related pairs among groups A and B1, the share that the method flagged.

Both are worked out group by group and scaled up. In group A and in group B1 the method flags some pairs and not others, so there are four cells. Each cell holds the number of pairs it stands for (counted exactly, over every pair), the labelled pairs drawn from it, and how many of those are related. The related share in a cell, times the cell's pair count, is the estimated number of related pairs in the cell. Precision is the flagged cells' related pairs divided by the flagged pairs. Recall is the flagged cells' related pairs divided by all the related pairs.

**The range.** Each cell's share gets a Wilson 95 percent interval. The ends are combined so that the lowest and highest values the intervals allow become the range. A cell that stands for pairs but has none labelled makes the number unavailable instead of guessing, and the page says which group needs labels.

**What the range means.** With the demonstration world fully labelled, the range held the exact answer in 96 to 100 of 100 random samples of the planned size. Treat it as about 95 percent and no better. A range from a few labels is wide on purpose.

**What recall does not cover.** Groups B2 and C are not in the recall. They are reported on their own: from the labelled pairs there, how many related pairs could be hiding. If that number is not small, the recall figure is flattering.

**The sample labels.** "Load sample labels" fills in 100 made-up labels from a rule that knows how the demonstration world was made. They exist to show the page filled in and are marked as samples everywhere, including in the exported file. Remove them before relying on any figure.

## What is measured, and what is still a placeholder

Only the first table on Methods and metrics comes from labels: the app's clusters, text match and keyword overlap. The four ways of working (mechanical only, mechanical then AI, AI then mechanical, AI only) and the per-category table are still placeholders until the engine scores pairs and the labels cover the AI's answers. A banner says this.

One thing the labels can already say about the AI: among the pairs the app clustered that people call related, how often the AI named the relation the way the people did. That is reported with its own range.

## The file

**Download the gold set** writes `reqin-gold-set/1`: for each labelled pair, both wordings, the group it was drawn from, who labelled it, what it counts as, and for each group how many pairs it stands for. That last number is what turns the labels into precision and recall. Labels from the demonstration are marked `(sample)`.

The `reqin` command line does **not** read this file yet. Evaluating a method against a gold set from the command line is a later step.

## At tens of thousands of requirements

The groups are not found by comparing every pair: at 25,000 requirements there are about 300 million pairs and the first version, which did, took 204 seconds. A (the clusters) comes from the clusters; B1 (the near misses) is found with an index over each wording's rarest words and then confirmed with the exact scores, so nothing that reads alike at 0.6 or more is missed (any such pair must share some of the rarest words); B2 and C are counted by subtraction and drawn from by position, never listed. The numbers are the same as comparing every pair. `verify.js` checks that on several hundred random and boundary-case sets of requirements (blank wordings, copies of one text, repeated words, very short and very long wordings), and `tools/mutation/population.py` breaks the shortcuts 17 ways to see that it would notice: 14 changes were noticed, and the 3 that were not change nothing a person can see (each reason is in [`tools/mutation/README.md`](../tools/mutation/README.md)). `node scale.js` times the whole thing in a page with 24,960 requirements.

## What has and has not been checked

| Checked | How |
|---|---|
| The groups and their sizes | `prototype/verify.js` recounts every pair in the demonstration world with separate code and compares it with the app's counts |
| The estimator | A census gate labels every pair with the demonstration truth and the estimate must equal the exact precision and recall. A second gate draws 100 samples of the planned size and requires the range to hold the exact answer in at least 95 of them, for four methods |
| What a pair counts as | Gates for one label, agreement, dispute, cannot tell, and a settled pair |
| Blind labelling | A gate looks through everything the labelling page can show for pairs in group A and fails if a cluster ID, a score or what the app or the AI thought appears |
| The page in a browser | `prototype/b15.py`: 74 checks at 1440 and 900 px and 75 at 390 px (labelling by mouse and keyboard, undo, skip, second labeller, settling, the sample labels, the file, the table, no sideways scroll, names read by a screen reader) |
| The gates bite | `tools/mutation/gold.py` changes the estimator, the queue and blind labelling in a copy of the prototype one at a time (15 changes); every one made a check fail. `tools/mutation/population.py` does the same to the shortcuts that count and draw pairs (17 changes, below). See below and [`tools/mutation/README.md`](../tools/mutation/README.md) |
| At 25,000 requirements | `prototype/scale.js` builds a project 20 times the sample (24,960 requirements) and times the pair counting: 1.5 s here, against 204 s for the first version. At that size it checks that the four groups add up to every pair, that group A is every pair inside a cluster, and that the plan draws 160 different pairs in the planned numbers from each group; it does not recount the near misses pair by pair (`verify.js` does that on smaller sets). The larger project is the sample repeated, so many wordings are identical; a real corpus has a different shape |
| **Not checked** | Whether people labelling real requirements agree with each other, how long labelling takes, and whether 160 pairs is enough for your project. The demonstration world is made up, so its precision and recall say nothing about the real engine |

### Changes the checks catch

Each change is made in a copy by `tools/mutation/gold.py` and `verify.js` has to report it. The last full run noticed all 15. The names below are the ones in the table above; the script holds the exact edits.

| Change | Caught by |
|---|---|
| Weights use the sample size instead of the group size | Range coverage and census |
| Recall ignores the pairs the method did not flag | Census |
| The range is the best guess | Range coverage |
| A plain normal range instead of Wilson | Range coverage |
| Near misses folded into the unrelated group | Population recount |
| "Cannot tell" counted as a vote | What a pair counts as |
| Related against not related counted as related | What a pair counts as |
| The lead's settled label ignored | What a pair counts as |
| No pair sent to a second person | Queue |
| A labelled pair offered again | Queue |
| Sample labels no longer marked as samples | Sample labels |
| Kappa replaced by plain agreement | Agreement |
| Best case reported as the precision | Census |
| The cluster shown on the labelling card | Blind labelling |
| An observer can label | Handlers |

## Using it for real

1. Import the project and run the mechanical steps.
2. Press "Remove sample labels". Ask two or three people to label in an hour or so each; every fifth pair is shared.
3. Read agreement first. If it is weak, the labelling instructions are the problem and the precision and recall do not mean what they seem to.
4. Read the table. Look at the range, not the middle. Look at the pairs hiding in B2 and C before trusting the recall.
5. Keep the exported file with the project. It is the evidence for any number you quote.
