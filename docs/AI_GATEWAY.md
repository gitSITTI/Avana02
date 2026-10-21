# The AI gateway

The AI gate (see [`AI_DATA_HANDLING.md`](AI_DATA_HANDLING.md)) is a set of rules. A page that shows "AI is off" is not a control: anyone can build a prompt and send it to a model by another route. The **gateway** is the one place where the rules are applied to a real request, in front of the model, using the switch and the data sheet that the shared project's lead set on the reference server, not anything the caller says.

```
  pipeline / script ──► gateway ──► (LiteLLM) ──► model
        │                  │
   token + the ids      reads the AI switch and data sheet from the reference server
   of the requirements  (every request, never kept), knows every requirement's marking,
   in the prompt        and refuses unless the gate is open for exactly that group
```

The gateway is plain Python, standard library only (`reqin/src/reqin/gateway/`). It speaks the same `POST /v1/chat/completions` shape the usual model servers do, so the pipeline needs one setting changed (the address) and one header added.

## What it is, and what it is not

| | |
|---|---|
| **It is** | the check that makes the project's AI switch and data sheet binding on every prompt that goes through it, with a tamper-evident record of what it let through and what it held back. |
| **It is not** | a wall. If the model host can be reached another way, the gateway is a door nobody has to use. The wall is the network: [`deploy/ai-egress/`](../deploy/ai-egress/README.md) has an example and `wall_check.py`, which is how you find out. |
| **It is not** | a reader of meaning. It recognises requirement wording that is *present* in a prompt; it cannot tell a paraphrase, a summary or a translation of a requirement. |

## What it checks, in this order

The first "no" wins, answers with HTTP status and a code, and **sends nothing to the model**. No answer contains a requirement's text.

| Step | Refused with | Code |
|---|---|---|
| No token, or the reference server does not know it | 401 | `no_token`, `bad_token` |
| The reference server cannot be reached, or answers oddly | 502 | `server_unreachable` |
| The body is not JSON, too large, or `stream` is on | 400, 413, 415 | `bad_json`, `too_large`, `json_only`, `no_streaming` |
| The caller is an **observer** | 403 | `observer` |
| The prompt does not say which requirements it holds, says too many, an id has odd characters, or one is unknown to the gateway | 400 | `no_requirements`, `too_many`, `bad_requirements`, `unknown_requirement` |
| The project has **no AI document** on the server | 403 | `no_sheet` |
| The document is not in a shape the gateway reads (other entries, a switch that is not true or false) | 403 | `bad_sheet` |
| The **gate** (`reqin.aigate.ensure`, the same code the pipeline uses): switch off, unreviewed sheet, contradictory sheet, classified / unknown / unstated marking, marking above what the sheet approves | 403 | `off`, `unreviewed`, `sheet`, `classified`, `unknown`, `unstated`, `marking` |
| The **route** the gateway really forwards to is not the one the sheet describes (model, where it runs, whether text leaves, what is kept, for how many days) | 403 | `sheet_mismatch` |
| The prompt holds the **wording of a requirement that was not declared** | 403 | `undeclared_text` |
| All of it is fine | the model's own answer, unchanged | |

When the gate is open the model's name, address and API key are the gateway's own: whatever model the caller names is replaced, the caller's token is never passed on, and a redirect from the model is not followed.

## Setting it up

1. **A reference server** with the project and its people ([`reqin/SERVER.md`](../reqin/SERVER.md)). A lead sets the switch and the data sheet on the page's *AI use* page (connected); they are stored as the `proj/ai` document. A project with none is closed, on the page and at the gateway.
2. **The markings file.** The gateway must know every requirement's marking, and it must know the wording to recognise it in a prompt, without keeping the wording:

   ```bash
   reqin-gateway markings --dataset out/dataset --field Marking --out markings.json    # a dataset written by `reqin ingest`
   reqin-gateway markings --list requirements.json --out markings.json                # or a JSON list of {id, marking, text}
   ```

   The file holds each requirement's marking as the source recorded it, and SHA-256 fingerprints of every run of six words of its wording (the first 16 hex digits). It is written with mode 600. Treat it as sensitive anyway: a guessable phrase can be confirmed against a fingerprint. **Build it again whenever requirements or markings change**; the gateway trusts the file, and a requirement that is not in it is refused (`unknown_requirement`), which is the safe side.
3. **The settings** (a JSON file; paths are relative to it):

   | Setting | Meaning |
   |---|---|
   | `listen` | `{"host": "127.0.0.1", "port": 8790}`. A host that is not this machine needs `"allow_remote": true` and a TLS reverse proxy in front. |
   | `server` | the reference server's address, no path |
   | `upstream` | `url` (the model's chat endpoint), `key_env` (the **name** of the environment variable holding its key; the key is never in the file), and what the route really is: `model`, `where` (`ours` / `tenant` / `vendor`), `leaves` (does text leave the network), `log` (`none` / `local` / `service`) and `days` when anything is kept. **The sheet must say the same**, or `sheet_mismatch`. |
   | `markings`, `log` | the markings file; the gateway's record |
   | `limits` | `max_body_bytes` (262144), `max_requirements` (200), `leak_min_windows` (2), `timeout_s` (120) |

   An example: [`deploy/ai-egress/gateway.compose.example.json`](../deploy/ai-egress/gateway.compose.example.json).
4. **Check, then run:**

   ```bash
   reqin-gateway check --config gateway.json     # reads everything, starts nothing
   reqin-gateway serve --config gateway.json
   ```
5. **The caller** sends its reqin token and names the requirements whose wording is in the prompt:

   ```bash
   curl -s http://127.0.0.1:8790/v1/chat/completions \
     -H "Authorization: Bearer $REQIN_TOKEN" -H "Content-Type: application/json" \
     -H "X-Reqin-Requirements: REQ-12,REQ-47" \
     -d '{"messages":[{"role":"user","content":"Compare these two requirements: ..."}]}'
   ```

   The pipeline calls `ensure(...)` itself too, so it never builds a prompt for a group the gate would hold; the gateway is the check that does not rely on the pipeline behaving.

## Recognising wording that was not declared

The caller says which requirements are in the prompt. The gateway also looks for the wording of **any other** requirement: text is normalised (Unicode NFKC, lower case, letters and digits only, so full-width letters, punctuation, underscores or other glue between words do not hide it), cut into runs of six words, hashed, and looked up in the markings file. Every string in the request counts, key names and tool descriptions included. Two or more matching runs of one undeclared requirement is a leak (one is a coincidence; a requirement shorter than two runs needs all of its runs). Runs that a declared requirement also holds are shared boilerplate and do not count.

What this does **not** find: a requirement paraphrased, summarised or translated; one of fewer than four words; text split so no six-word run survives. It catches an application that pastes the wrong requirement into a prompt, which is the mistake that happens. It does not stop someone who is trying to get text out.

## The gateway's record

One JSON line per request, each carrying the SHA-256 of the one before. A line has: sequence number, time, project, person, the requirements named, the code, the marking level, whether the gate was open, the model's HTTP status and the size of the prompt in bytes. **Never a prompt, never an answer.**

```bash
reqin-gateway verify-log --log gateway-log.jsonl --expect-head <the head you wrote down last time>
```

It says which line was edited, removed or added out of order, and with `--expect-head` whether the end was cut off. A record that does not check out is not appended to; the gateway will not start on it.

## The wall

Run the checks in [`deploy/ai-egress/README.md`](../deploy/ai-egress/README.md) from each place that matters, then combine them. A model that is switched off "passes" every wall check, so each "blocked" result must be matched by an "open" result for the same address from the place allowed to reach it; `combine` refuses the rest.

## What has and has not been checked

| Checked | How |
|---|---|
| The gateway, over real HTTP on loopback, against a real reference server and a fake model | `reqin/tests/test_gateway.py`, 82 tests: the one path that opens, and a test for each refusal |
| The tests can fail | `tools/mutation/gateway.py` breaks the gateway 56 ways; all are noticed (10 were not at first, which led to about a dozen more tests) |
| The page and the gateway agree | `reqin/tests/test_gateway_page.py`: every one of the sample's 252 groups, under every sheet in the shared table, reviewed and not, switch on and off, gets the same code and level from the page and from the gateway |
| The wall check script | `tools/test_wall_check.py`, 96 tests (one skips on a machine with no IPv6); `tools/mutation/wall.py` breaks it 29 ways, all noticed |
| The example files | the compose file passes `docker compose config`; the firewall file passes `nft -c`; the gateway settings are read by the gateway; the wall plans load and every blocked check has its proof |
| **Not checked** | A real model, LiteLLM, or any container started (no container engine daemon was running where this was written). A real firewall or network: the wall check was run only against sockets on one machine. TLS. Load. Streaming (it is refused, not supported). More than one project per gateway (the markings file is one project's). Markings that change while the gateway runs (restart it with the new file). Whether the markings in the source system are right |
