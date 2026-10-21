# Keeping the work

In the prototype, what people decide, sign, write and label is kept in the browser by itself, and can be saved to a file and read back. This page says what is kept,
what is checked before a file replaces anything, and what this is not. The code is `prototype/parts/persist.js` (the rules) and `prototype/parts/c7.js` (the
Home card and the loading steps).

Nothing here has been used on a real program. The data is a synthetic sample.

## What a person sees

On **Home**, a card called "Your work":

| Button | What it does |
|---|---|
| (nothing to press) | Decide a cluster or a requirement and it is kept in this browser a moment later. The card says when it was last kept and how many decisions, sign-offs, hand-offs and labels that is. Reload the page and the work is back, with a line that says when it was saved. |
| **Save to a file** | Downloads `reqin-project-state/1`, a JSON file with the work, the project it belongs to, a count of what is in it and the record of events. |
| **Load from a file** | Reads a file and checks it. If it passes, the card shows a summary (the file's name and date, the numbers of decisions, sign-offs, hand-offs, labels and events, the AI use it brings, and notes) and asks before it replaces anything. |
| **Start over** | After a confirmation, removes what is kept in this browser and goes back to the sample as it started. A saved file is not touched. |

## What is kept, and what is not

Kept: the decisions on clusters and on single requirements, sign-offs, objections and adjudications, hand-offs to teammates and the replies, wording choices, the assistant's chat for each cluster, the gold-set labels, the sign-off policy choices, the AI switch and the AI data sheet, the choices made when the project was opened (source, scope, format), who is working, and **the record of events**.

Not kept: which screen is open, filters, search text, half-typed boxes, whether a panel is open.

## What is checked before a file replaces anything

**A file that fails any of these is refused**, the reason is shown, and the work in the browser is left as it was:

1. **The format**: a JSON object, `reqin-project-state/1`, with a saved state in it.
2. **The project**: the file names the project it was saved from, with a fingerprint of its requirement and cluster IDs. A file from another project is refused.
3. **The kind of every kept item**: a list is a list, a number is a number, a switch is on or off, the person is someone in this project, the record has at most 20,000 events and each is made of text.
4. **The record of events**: it is a chain, each entry carrying a short fingerprint of the one before it. A changed, removed or reordered entry is found, and the first entry that does not follow is named.
5. **The AI switch and the AI data sheet agree with their own record**: the page works out what the record says they should be and refuses a file that disagrees. See [`AI_DATA_HANDLING.md`](AI_DATA_HANDLING.md).
6. **The screens can draw it**: the page draws every screen, and the review screen for a spread of the clusters and the requirement screen for a spread of the requirements the file says something about, in memory. If one cannot be drawn, the file is refused and says which.

**These are not refused; they are left out, counted, and the summary says so**: entries for a cluster or requirement the project does not have, entries in the wrong shape (a date that is a number, a decision with an outcome the page does not know, a name such as `constructor` or `__proto__`), keys the page does not keep, and an allocation the project does not have (the whole project is shown instead). What stays is exactly the entries that make sense.

A browser copy larger than 4 MB is removed unread, even when it is otherwise a good file. A browser copy that fails any of the checks above is removed, nothing from it is used, and Home says why.

After a file is accepted and the person confirms, loading adds one entry to the record ("Loaded saved work from ..."), so the chain still holds and the earlier entries are untouched.

## Two tabs, a blocked browser, a full browser

- **Two tabs of one browser.** The tab that notices the other one saved something stops saving and says so, so it cannot write over the other tab's work. The person chooses whose work stands: the other tab's, or this tab's.
- **Storage that is blocked** (a private window, or a browser setting) or **full**: the card says so in words and says to save a file. The page keeps working.
- **Closing the tab** flushes the last change; saving is otherwise 350 ms after a change.

## What this is not

- **Not a shared store, until you sign in.** Two people in two browsers each have their own copy. The reference server (`reqin/src/reqin/server`, see [`reqin/SERVER.md`](../reqin/SERVER.md)) is the shared one: one copy, who may change what, no silent overwrites, a record that verifies. Open the page from the server and sign in with a token and the browser keeps **nothing** (the server has the one copy; *Load from a file* and *Start over* are off, because they would replace what everyone shares); signing out puts back what the browser had before. See *Working with a team* in [`prototype/README.md`](../prototype/README.md).
- **Not encrypted.** The browser copy and the file are plain text. On a shared computer, start over when you finish. A real deployment would keep the work on the server, behind its sign-in.
- **Not tamper-proof.** The fingerprint on each entry of the record is a short demonstration hash. It finds accidents and hand edits; it does not stop a person who understands it from writing a consistent record. The server's record uses SHA-256 and is checked by the server.
- **Not a backup.** Clearing the browser's site data removes the browser copy. Save a file.

## What has and has not been checked

| Checked | How |
|---|---|
| The checks on a loaded file | `prototype/verify.js` loads good and deliberately damaged files and requires the right outcome each time: a file the page wrote comes back exactly as it went in; a wrong format, another project, an edited record, a sheet or switch changed by hand, or a file the screens cannot draw is refused; entries for things the project does not have, or in the wrong shape, are left out and counted |
| The page in a browser | `prototype/b18.py`: autosave, restore on reload, save, load, what is refused, start over, blocked and full storage, two tabs |
| The checks bite | `tools/mutation/keep.py` removes or weakens one check at a time in a copy of the page; each must make `verify.js` fail (see [`tools/mutation/README.md`](../tools/mutation/README.md)) |
| **Not checked** | Browsers other than Chromium; very large real projects (the scale test uses made-up projects, one the sample repeated and one varied, see `prototype/scale.js`); people using it on a shared computer |
