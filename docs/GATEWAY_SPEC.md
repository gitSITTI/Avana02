# The gateway's decision core: a specification for porting it

[`AI_GATEWAY.md`](AI_GATEWAY.md) says what the gateway is for and how to run the Python one. This page says exactly **what its decisions are**, in words that do not depend on Python, so the same decisions can be made in another language (Node, Go, Java, C#, Rust ...) or by another provider's agent. The test vectors are in [`gateway_cases.json`](gateway_cases.json): a port is correct when it gives every answer in that file. The reference implementation is [`reqin/src/reqin/gateway/`](../reqin/src/reqin/gateway/) and [`reqin/src/reqin/aigate.py`](../reqin/src/reqin/aigate.py).

**What is covered by vectors, and what is not.** The decision core (sections 2 to 11 here) is pure: text and JSON in, an answer out, no network, no files. It is all covered by `gateway_cases.json`. The HTTP side (sockets, headers, forwarding to the model, the reference-server calls, the order in which they happen) is described in [`AI_GATEWAY.md`](AI_GATEWAY.md) and tested only by the Python tests over real HTTP: **there is no language-neutral conformance suite for it.** A port has to be tested by someone who reads that page and tries each refusal.

## 1. Conventions

- Data is JSON: objects, arrays, strings, numbers, `true`, `false`, `null`. A string is a sequence of Unicode code points (not bytes, not UTF-16 units; a character outside the first plane counts as one).
- "Hash" means SHA-256 of the UTF-8 bytes, written as 64 lower-case hexadecimal digits. "Short hash" is its first 16 digits.
- Keys of objects are compared as written; where an order of keys matters it is said.
- Numbers in the cases are whole numbers, except `days`, which is compared as a number (90 and 90.0 are equal).

## 2. `words(text)` → list of strings

The words of a text, as used for recognising wording. In this order:

1. **NFKC**: Unicode normalisation form KC.
2. **Lower-case**: full Unicode lower-casing, independent of any language or locale (the `SpecialCasing` rules, so `İ` U+0130 becomes `i` followed by U+0307, and a capital sigma at the end of a word becomes `ς`). A simple one-to-one lower-case (Go's `unicode.ToLower`, for one) gives different words for `İ` and is wrong here.
3. **Split** on every code point that is *not* a letter or a number, and drop empty pieces. A letter is a code point whose Unicode general category starts with `L`; a number, with `N`. Everything else separates words: spaces, punctuation, the underscore, symbols, emoji, and **combining marks** (category `M`), so a vowel sign inside a Devanagari word splits it, and a soft hyphen or a zero-width space splits a word.

Unicode keeps adding letters. The vectors use only characters that have been assigned for many years; a port on an old Unicode version may differ on a recent script, and that is a difference of the platform, not a mistake.

## 3. `fingerprints(text)` → sorted list of short hashes

Let `w = words(text)`. If `w` has fewer than **4** words the answer is the empty list: a wording that short cannot be recognised in a prompt, and only its caller can declare it. Otherwise the *runs* are: all of `w` when it has at most **6** words, else every run of 6 consecutive words. The answer is the sorted list of the distinct short hashes of the runs, where the hash of a run is the hash of its words joined by one space.

## 4. The markings file (`reqin-markings/1`) and how it is read

```json
{"format": "reqin-markings/1", "window": 6, "requirements": {"REQ-1": {"marking": "CUI", "fp": ["0123456789abcdef", "..."]}}}
```

**Building**: for each requirement `(id, marking, wording)`, an entry with the marking exactly as the source recorded it (text, or `null` for none recorded) and `fingerprints(wording)` (an empty list for a missing wording). Ids are unique; the object is written with ids sorted. The wording itself is never written.

**Reading** is strict, and refuses the file (an error, nothing served) when:
- `format` is not `reqin-markings/1`, or `requirements` is not an object;
- an id does not match `[A-Za-z0-9][A-Za-z0-9._:-]{0,199}` completely (ASCII only);
- an entry is not an object, or has a key other than `marking` and `fp`;
- `marking` is present and is neither text nor `null`;
- `fp` is present and is not a list of strings of exactly 16 characters from `0-9a-f` (capitals are refused).

An entry with neither key is fine: no marking recorded, no fingerprints. Reading builds two tables: each id's marking, and for each fingerprint the *set of ids* whose list holds it; and the count of distinct fingerprints of each id.

## 5. `undeclared(prompt, declared, min_windows)` → map from id to number

The requirements whose wording is in the prompt although they were not declared for it.

1. `w = words(prompt)`. Collect the set `S` of short hashes of **every** run of `n` consecutive words of `w` for each `n` from 4 to 6 (runs of 4 and 5 words can only be a whole short requirement; runs of 6 are what longer ones are cut into). A prompt with fewer than `n` words has no run of `n`.
2. For each hash in `S` that is in the table: if **any** id that holds it is in `declared`, skip it (shared boilerplate). Otherwise add 1 to the count of **every** id that holds it.
3. Keep the ids whose count is at least `min(min_windows, count_of_fingerprints(id))` (so a requirement with a single fingerprint needs only one hit; an id that has no fingerprints is never kept). The answer maps each kept id to its count; **list the ids sorted** (the vectors compare the mapping; `decide` below uses the order).

## 6. `prompt_text(body)` → string

Every string in a request body that a model could read: walk the JSON; collect each string value, and each object **key** too (before the key's value). Join the collected strings with a line feed. Arrays and objects nested more than **40** levels deep are an error (the request is refused as `bad_json`; the vectors say `null`). Keep the order of the document. Note for languages whose JSON reader reorders keys (JavaScript puts integer-like keys first): the order only matters for a run of words that spans two strings, and the vectors do not depend on it.

## 7. The header and the ids

The caller lists the requirements in a prompt in the header `X-Reqin-Requirements`: split on `,`, trim whitespace, drop empty pieces and repeats (keep the first), keep the order. An id that does not match the id pattern in section 4 makes the request `bad_requirements` (400). Matching is case-sensitive: `req-1` and `REQ-1` are different ids.

## 8. `sheet_from_doc(doc)` → (sheet, switch) or nothing

`doc` is the server's `proj/ai` document. Answer **nothing** (the gateway then says `bad_sheet`) unless all of these hold:
- `doc` is an object with only the keys `on` and `sheet`, `on` is a boolean (`1` and `"true"` are not), and `sheet` is an object;
- `sheet` has only these keys: `model where leaves log days approved unstated reviewed_by reviewed_at entered_by`;
- `model where log approved unstated reviewed_by reviewed_at entered_by` are, if present, text (not numbers, not `null`), and `leaves` is, if present, a boolean.

Missing keys take these defaults: `model ""`, `where "ours"`, `leaves false`, `log "none"`, `days 0`, `approved "none"`, `unstated "withhold"`, `reviewed_by ""`, `reviewed_at ""`, `entered_by ""`. `days` is **not** checked here: the gate names it when it matters.

## 9. The gate

`ensure(sheet, switch, markings)` is the AI gate, specified in [`AI_DATA_HANDLING.md`](AI_DATA_HANDLING.md) (what each code means, how a marking is read, the order of the rules) and tested by the table [`ai_gate_cases.json`](ai_gate_cases.json) (58 marking cases, 14 group cases, 16 sheet cases, 19 whole decisions), which a second implementation already runs: `prototype/parts/aigate.js`. **Port the gate first, and pass that table, before the gateway.** It answers one of `open`, `off`, `unreviewed`, `sheet`, `classified`, `unknown`, `unstated`, `marking`, with the group's marking `level` (`none`, `cui`, `exp`, or the level that stopped it) and, for `sheet`, the list of problem codes in this fixed order: `model values vendor_leaves leaves_marked log_marked exp_where days`.

Two points a port gets wrong: an empty list of markings is `unstated` (when the sheet says to withhold) and "reviewed" needs **both** a reviewer and a date that are not blank.

## 10. `route_mismatch(sheet, route)` → list of field names

`route` is what the gateway really forwards to: `model where leaves log days`. The sheet's approval is for the model it names, run the way it says. The answer lists, in this order, each of `model`, `where`, `leaves`, `log` whose value differs, then `days` **if** either the sheet's `log` or the route's `log` is not `"none"` and the days differ. A port may phrase a message as it likes; the vectors compare the field names, and the first part of each entry in the HTTP answer's `detail` (up to the colon) must be the name.

## 11. `decide(role, ids, markings, ai_doc, ai_present, route, prompt, max_requirements, min_windows)` → answer

The first rule that says no wins. The answer has `ok`, an HTTP `status`, a `code`, the group's marking `level` (empty when it was not reached), and a `detail` list.

| # | If | Then (status, code, detail) |
|---|---|---|
| 1 | `role` is `observer` | 403 `observer` |
| 2 | `ids` is empty | 400 `no_requirements` |
| 3 | `ids` has more than `max_requirements` entries | 400 `too_many` |
| 4 | an id is not in the markings | 400 `unknown_requirement`; detail = the unknown ids in order, at most 20 |
| 5 | `ai_present` is false (the server has no `proj/ai`) | 403 `no_sheet` |
| 6 | `sheet_from_doc(ai_doc)` is nothing | 403 `bad_sheet` |
| 7 | the gate says no | 403 with the gate's code (`off unreviewed sheet classified unknown unstated marking`), its level, and for `sheet` the problem codes as detail |
| 8 | `route_mismatch` is not empty | 403 `sheet_mismatch`, level of the group, detail = the field names (or entries that start with them) |
| 9 | `undeclared(prompt, set(ids), min_windows)` is not empty | 403 `undeclared_text`, level of the group, detail = the ids, in order, at most 20 |
| 10 | otherwise | 200 `open`, level of the group |

The marking given to the gate for each id is the marking from the markings file (`null` stays `null`, which the gate reads as nothing recorded). No answer contains any requirement's text.

## 12. The record: a chain of hashes

One JSON object per line. The entries, and no others: `seq at project person requirements code level ok upstream prompt_bytes prev hash`.

- `seq` counts from 1; `prev` is the `hash` of the line before, or 64 zeros for the first line.
- `hash` is the hash (section 1) of `prev`, then `|`, then the **canonical JSON** of the line without its `hash` entry.
- **Canonical JSON**: keys sorted by code point, no spaces after `:` or `,`, strings with only `"`, `\` and control characters (below U+0020) escaped, everything else, including non-ASCII, written as it is. A line is written as the canonical JSON of the full object (with `hash`) and a line feed.
- **Verifying** a log: for each line in order, it must parse as a JSON object with exactly those entries, `seq` equal to its position, `prev` equal to the hash of the line before, and a `hash` equal to the one computed. The first line that fails is reported by its number. Removing lines from the **end** is not noticed unless the verifier is given the newest hash that was written down.

The record holds who asked, the requirement ids named, the code, the level, whether the gate was open, the model's HTTP status (or `null`) and the size of the prompt in bytes. **Never a prompt and never an answer.**

## 13. What a port tends to get wrong

| Mistake | Why it matters | Which vector shows it |
|---|---|---|
| `\w` or `[a-z0-9]` for a word | misses letters and digits of other alphabets; a requirement in full-width letters or another script is then not recognised | `words`: full-width letters, Arabic-Indic digits, `ΟΔΥΣΣΕΥΣ` |
| Lower-casing before NFKC, or simple lower-casing | different words for `İ`, `ẞ`, `ǅ`, ligatures | `words`: `İstanbul`, `ǅ and ẞ`, `ﬁre ﬂow` |
| Treating combining marks as letters | one word where the reference has several (or the reverse) | `words`: Devanagari, `àb`, `a​b a­b` |
| Windows of 6 only, when looking for a whole short requirement | a 4- or 5-word requirement pasted whole is not found | `undeclared`: four- and five-word cases |
| Counting a window held by a declared requirement | shared boilerplate flags innocent prompts | `undeclared`: shared wording cases |
| Not looking at keys and nested strings | text hidden in a field the code does not know | `prompt_text`, `decide` |
| Capital-letter fingerprints accepted, or a looser id rule | a file that does not mean what it says | `markings_file_errors` |
| Hash of the JSON with spaces, or keys in written order | a record the Python verifier refuses | `audit_chain` |
| Checking the sheet's `days` when nothing is kept | a refusal that should not happen, or the reverse | `route_mismatch` |
| A step in another order | a reason is given that hides the real one, or a request that should be refused is not | `decide`: the cases that stack two reasons |

## 14. Checking a port

1. Read `gateway_cases.json`. Its sections: `words`, `fingerprints`, `markings_file`, `undeclared`, `route_mismatch`, `sheet_from_doc`, `prompt_text`, `requirement_headers`, `markings_file_errors`, `decide` (with `decide_markings`), `audit_chain`, `verify_log`. Each case has its inputs and an `expect`.
2. Run every case through your implementation. Pass means **every** case, not most.
3. Then do what the vectors cannot: build the HTTP side from [`AI_GATEWAY.md`](AI_GATEWAY.md), and try each refusal against it, with a fake model that records whether it was called. A refusal after which the fake model was called is the failure that matters.

What passing the vectors shows: your decision core makes the reference's decisions on those cases. It does not show that the cases are enough (they are a sample of what went wrong in one language), that the HTTP side is right, or that the network wall exists.
