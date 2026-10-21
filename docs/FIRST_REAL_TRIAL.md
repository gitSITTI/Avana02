# The first trial with real requirements

This is a plan for the first time anyone points this software at requirements that are real. It is written for the person who runs that trial. **Nothing here has been done.** Nobody has used any part of this repository on a real program, so every step below is a proposal, and the "what to expect" notes are guesses until someone writes down what actually happened.

The plan is short on purpose, because what a trial can answer today is short. Read the first table before agreeing to anything.

## What a trial can and cannot answer today

| Question | Can it be answered now? | Why |
|---|---|---|
| Does the input layer read our exports correctly: the right identifiers, the right text, the right counts? | **Yes.** This is the first trial, and the only one that uses real data. | `reqin` reads files and writes a dataset folder; `reqin check-dataset` checks it against [`reqin/GUI_CONTRACT.md`](../reqin/GUI_CONTRACT.md). |
| Do the live connectors work against our systems? | **Only for files.** | `sysml_api`, `oslc_rm`, `agility`, `jira`, `polarion` and `jama` have met nothing but fakes written from documentation; the Jama token helper and the DOORS 9 script have never run against the real thing; the `.mdzip` / XMI reader and the Enterprise Architect query pack were built from documentation and recall and have read only made-up files (`reqin connectors` says which is which). Each live connector needs the owner of that system in the room. |
| Does the comparison find our near-duplicates? | **Not known.** | The mechanical engine (no model) is built and has been run on a made-up corpus and on pairs a language model labelled; it has never run on real requirements, and on the held-out pairs it finds little of what a person would call the same ([`COMPARE_RESULTS.md`](COMPARE_RESULTS.md)). The clusters and scores on the screens still come from a made-up sample. |
| Are the numbers on Methods and metrics real? | **No.** | They are placeholders, apart from the precision and recall that come from labelled pairs, and those are labelled on the sample. See [`GOLD_SET.md`](GOLD_SET.md). |
| Can people follow the screens: find a cluster, decide, hand off, label, save? | **Yes, with the sample.** | That is a trial of the screens, not of the data (trial 1 below). |
| Does shared review work for several people? | **With the demo project only.** | The reference server has never run with real data and has no sign-in system of its own ([`reqin/SERVER.md`](../reqin/SERVER.md)). |
| Would the AI gate keep marked text away from a model? | **No, and the AI stays off.** | The gate is a check inside the application. The wall is a network rule that belongs to your IT staff ([`AI_DATA_HANDLING.md`](AI_DATA_HANDLING.md)). |

So the first real trial is **trial 0: read one real export and check the result by hand.** Trial 1 uses no real data. A trial of the comparison on real requirements has to wait for the engine; the last section says what must exist first.

## Agree these first, in writing

A trial on real requirements is not a software question until these are settled. Write the answers in a note that is **not in this repository**.

1. **Whose data is it, and who may approve using it here?** Name the person. If the requirements are marked, export-controlled or proprietary, name the security or export-control reviewer and get their answer for *this* machine and *this* person.
2. **Where does it run?** On a computer the data is already allowed on. The export is a read-only copy; the output folder is on the same approved storage; both are deleted when the trial ends, and someone checks that they were.
3. **The AI stays off.** Not a switch left on "just to see", not a snippet pasted into a chat to ask what a requirement means, not a coding agent given the folder. [`AGENTS.md`](../AGENTS.md) says the same to agents; say it to people too.
4. **Nothing leaves the trial machine except what you decided.** The dataset folder is real data. A screenshot, a bug report, a commit message or an issue is a way for it to leave. Decide now where problems get written down and what may be quoted in them.
5. **When do you stop?** The stop conditions for trial 0 are below; agree them before you start, so they are not argued afterwards.

## Trial 0: read one export (about half a day, two people)

One person runs it, a second checks it. The second person did not run the import and does not see the profile first.

**Set up.** Use the container with no network, if you can: the read-only export is mounted, the output folder is the only thing it can write.

```bash
podman run --rm --network=none --userns=keep-id --user "$(id -u):$(id -g)" \
  -v "$PWD/exports:/data:ro,Z" -v "$PWD/out:/out:Z" requirements-consolidator/reqin:dev \
  sniff /data/export.reqif
```

The container image has not been built by the people who wrote it (no container engine was available), so the first thing the trial may find is a problem with the image. If so, install `reqin` in a virtual environment on the approved machine instead; file readers need no network either way.

**The steps** (the same commands, outside a container):

```bash
reqin sniff    export.reqif                                       # which reader recognises it
reqin discover export.reqif                                       # containers, fields, samples
reqin propose  export.reqif > profile.yaml                        # a PROPOSAL; edit it, it is not trusted until you do
reqin import   export.reqif --profile profile.yaml --out-dir ds/export
reqin check-dataset ds/export
```

Spreadsheets and CSV files need the profile edited more than anything else; ReqIF from a tool that follows the standard needs the least. Keep every version of the profile; what you changed is a finding.

**What the second person checks, against the source tool and not against the output of `reqin`:**

| Check | How | Pass |
|---|---|---|
| The count | Count the requirements in the source tool for the same scope, then count the lines in the dataset's requirements file | The same number, or every difference explained (headings, information items, deleted items) |
| Twenty requirements, chosen by the second person | For each: the identifier, the text, the owner and the status, as the source tool shows them | Identical. A difference in whitespace or line breaks is noted; a difference in any word, number or unit is a failure |
| The rejected file | Read every line | Each rejected record has a reason that is true, and nothing that is a real requirement is in it |
| Links and verification items, if the export has them | Pick five requirements that have parents or verification items | The same links appear |
| Marking fields, if the export has them | Pick five marked requirements | The marking came through unchanged, and a requirement with no marking in the source has none here |
| `reqin check-dataset ds/export` | Run it | Exit 0 |

**Stop, and write it down, when:** the counts differ and nobody can say why; a word, number or unit was changed; identifiers were changed or collide; a marking was lost; or `check-dataset` fails. Do not edit the profile until it agrees. A profile that was tuned until the numbers matched must be reported as tuned.

**Write down** (in the note outside the repository): the file type and the tool that made it, the count in and the count out, the profile and each change to it, every difference found, and how long it took. If the trial found something wrong in `reqin`, describe it **without quoting a requirement**: the field name, the kind of value, the shape of the text.

## Trial 1: people use the screens on the sample (no real data)

Open the prototype ([`prototype/README.md`](../prototype/README.md)) and give two to four people the tasks below, one at a time, with someone watching and saying as little as possible. Use the demonstration project; it contains made-up requirements.

1. Find the cluster that needs the most attention and say why you think so.
2. Decide it, with a reason, and see what happens to the verification items.
3. Ask a colleague for a second opinion, then see it waiting.
4. Label ten pairs on the Label pairs page, without being told what the app thought.
5. Save your work to a file, close the tab, and load it back.
6. Find where the AI is switched off, and say what that means.

For each task write down: could they do it, how long, where they stopped to think, what they said out loud, and what they got wrong. Ask afterwards what they thought a screen was for. A screen that people use correctly but describe wrongly is a problem too.

What this tells you is whether the screens make sense to people like yours. It says nothing about whether the comparison is right, and nobody should leave thinking it does.

## What must exist before a trial of the comparison on real requirements

| Needed | State today |
|---|---|
| The comparison engine, with its mechanical stages measured on a made-up corpus whose right answers are known | Built (stages 1 to 4, no model) and measured on a made-up corpus; [`COMPARE_RESULTS.md`](COMPARE_RESULTS.md) says what that shows and what it does not. Not run on real data. The brief it was built from is [`agent_prompts/comparison_engine.md`](agent_prompts/comparison_engine.md) |
| A way to load a dataset folder into the page, so real requirements reach the screens | Not built: the Open and Import screens read real `reqin` output; the rest of the page uses the sample |
| The page connected to the reference server, if more than one person works on it | Not done; see [`reqin/SERVER.md`](../reqin/SERVER.md) |
| A written data sheet, a gateway and the network wall, **if** the AI is ever switched on | Not done; the AI stays off in the first trials |
| Two people who will label real pairs, and an hour a day for them | Yours to arrange. 160 pairs may not be enough for your project ([`GOLD_SET.md`](GOLD_SET.md)) |

## If something goes wrong

| What happened | Do this |
|---|---|
| Real text appears in a screenshot, a bug report, a chat, a commit or this repository | Stop. Tell the reviewer you named above. Remove it from where it went and from history if it was committed; the repository's guard job and `tools/check_no_real_data.py` are a tripwire for files, not for text in a message |
| The output looks wrong but the counts match | Do not fix the profile to match what you expected. Write down what is wrong and where, and keep the profile that produced it |
| Someone proposes "just trying the AI on three requirements" | The answer is the one agreed above |
| The trial finds that the tool cannot read your export at all | That is a result. Write down what the file was and what the reader said; do not hand the file to anyone outside the approved set to find out why |

## What has and has not been checked

| Checked | How |
|---|---|
| Every command above exists and the dataset check can fail | `reqin/tests/`, run on synthetic exports of each type |
| Every path this page names exists | The Markdown link check in `tools/` |
| **Not checked** | **That any of it works on a real export.** The time estimates, the "what to expect" remarks and the stop conditions are the authors' guesses. The container image has not been built. No real MSOSA, DOORS, Teamwork Cloud or Agility system has been read |
