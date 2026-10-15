# Reference server: one shared copy of the decisions

**What it is.** A small server (Python standard library only: `http.server` and SQLite) that keeps *one* copy of a project's decisions, sign-offs, hand-offs and labels, so two people in two browsers see the same thing and cannot silently overwrite each other.
**What it is not.** The prototype page is **not connected to it yet**. Today each browser keeps its own copy (autosave, plus *Save to a file* and *Load from a file* on Home). This server is the part a connected version would stand on, built and tested on its own first. It has no user directory or single sign-on, no TLS, no encryption of the file on disk, and it has never been run with real program data.
**Where the rules live.** The server enforces the few rules it can enforce without knowing your policy (table below). *Which* lenses a given decision needs signed (the policy engine) stays in the page; there is no second copy of it here, on purpose: two copies drift.

## Run it

```bash
pip install -e reqin                                   # nothing extra to install: no web framework
echo '[{"key":"sam","name":"Sam Okafor","role":"reviewer","lens":"SE"},
       {"key":"morgan","name":"Morgan Hale","role":"lead","lens":"SE"},
       {"key":"lee","name":"Lee Park","role":"observer"}]' > people.json
reqin-server init  --db shared.db --project demo --people people.json --tokens-out tokens.json   # tokens shown once, file mode 600
reqin-server serve --db shared.db                      # http://127.0.0.1:8780, this machine only
reqin-server verify --db shared.db --project demo      # exit 0 if the record is intact, 1 if it was changed
reqin-server rotate-token --db shared.db --project demo --person sam   # a lost or leaked token: the old one stops working
```

`serve` refuses any address that is not this machine. To let colleagues reach it, put a reverse proxy that adds TLS in front and pass `--allow-remote`; tokens travel in a header, so plain HTTP beyond one machine would hand them to anyone on the path. Back it up with SQLite's own `.backup`, and write down the `head` hash after a milestone (see *The record*).

## The calls

Every call except `/v1/health` carries `Authorization: Bearer <token>`. Bodies are JSON (`Content-Type: application/json`). No CORS headers are sent, so a web page from another origin cannot call it; the page would be served from the same address or through the same proxy.

| Call | What it does |
|---|---|
| `GET /v1/health` | says the server is up (no token) |
| `GET /v1/me` | who the token is: project, key, name, role, lens |
| `GET /v1/projects/<p>/people` | the people in the project (never their tokens) |
| `GET /v1/projects/<p>/docs?prefix=dec/&after=<id>&limit=200` | the newest revision of each document whose id starts with the prefix, in id order, a page at a time (`next` is the cursor) |
| `GET /v1/projects/<p>/docs/<id>` | one document: `rev`, `body`, `by`, `lens`, `at`, `event`, `body_hash` |
| `GET /v1/projects/<p>/history/<id>` | every revision of one document |
| `PUT /v1/projects/<p>/docs/<id>` | `{"body": {...} or null, "if_rev": N}`; add `Idempotency-Key: <1 to 64 characters>` to make a retry safe |
| `GET /v1/projects/<p>/events?after=N&limit=500` | the record from entry N+1, and the current `head`: poll this to see what others did |
| `GET /v1/projects/<p>/verify?expect_head=<hash>` | recompute the whole record from what is stored |

**Document ids** are a kind and one to three names: `dec/CL-014` (a cluster decision), `rdec/REQ-FCS-0312` (a decision on one requirement), `sign/CL-014/SE` (a sign-off in a slot), `hand/CL-014`, `label/REQ-A/REQ-B/sam`. Letters, digits and `. _ : -` only, at most 200 characters, no `..`.
**A document** is a JSON object of at most 64 KB, or `null` for "withdrawn". A withdrawn document keeps its revision number, so the next write still says which revision it is changing.

## What it promises, and where each promise is tested

Everything below has a test in `tests/test_server.py`, and each rule was broken on purpose to see that a test fails: `tools/mutation/server.py` makes 40 such changes in a copy of the server and requires `tests/test_server.py` to fail on each (last run: all 40 noticed; see [`tools/mutation/README.md`](../tools/mutation/README.md)).

| Rule | Answer when broken |
|---|---|
| **No silent overwrite.** A write says which revision it changes (`if_rev`; 0 for a new document). If it is not the current one, nothing is written. | `409 conflict`, with the current document in `error.current` so the second person sees what changed |
| A write without `if_rev` (or with text, a negative number, `true`) is not a write. | `400 if_rev_required` |
| **Observers read, never write.** | `403 observer` |
| **A sign-off sits in the signer's own lens.** `sign/<id>/SE` is for someone who reviews as SE. | `403 wrong_lens` |
| `OWN` and `ADJ` slots are for leads. | `403 lead_only` |
| **Nobody signs a decision they made**, lead or not. | `403 self_sign` |
| A sign-off needs a decision to bind to, and names its revision: `{"rev": 2}`. | `409 nothing_to_sign`, `409 stale_signoff` (with `decision_rev`) |
| **A new revision of a decision clears the sign-offs on the old one**, in the same step, each clearing in the record. Other decisions' sign-offs are untouched. | the reply lists `cleared` |
| **A repeated request is done once.** Same key and same request: the first reply again, marked `replay: true` and `Idempotent-Replay: true`. | same key, different request: `422 idempotency_reuse` |
| **Who made the change comes from the token**, never from the body. | |
| Projects do not see each other; a token works in its own project only. | `403 other_project` |
| Sizes: 64 KB a document, 1 MB a request. Odd ids, bad JSON, `NaN`, extra fields, other content types. | `413`, `400 bad_doc_id`, `400 bad_json`, `400 bad_request`, `415 json_only` |
| Nothing a caller sends is logged (method, path without the query, status only). Errors never show a stack trace. | |

Other answers: `401 no_token`, `401 bad_token` (with `WWW-Authenticate`), `404 no_doc`, `404 no_route`, `405 method_not_allowed`, `411 length_required`, `500 server_error` (generic).

## The record

Every change is an entry: `seq`, `type`, `actor`, `target`, `rev`, `body_hash` (SHA-256 of the document revision), `text`, `at`, `prev`, `hash`, where `hash = SHA-256(prev + "|" + canonical JSON of the other fields)` and the first `prev` is 64 zeros. The entry and the document revision are written in one transaction, or neither is.
`verify` recomputes it from the stored documents and names the first thing that does not follow: an entry edited, removed or out of order, a document revision whose body, author or time no longer matches its entry, or a revision that is stored but not in the record.

**What the chain does not prove.** It shows the record was not edited in place. It cannot show that the *newest* entries were not removed (a shorter chain is still a valid chain), and whoever holds the database file and writes the program could rebuild the whole chain. So write down the `head` hash after a milestone, keep it somewhere the database's administrator cannot reach, and pass it back as `expect_head`.
The prototype page's own record uses a short demonstration hash (32 bits) so the screen is readable; this server uses SHA-256. They are not the same chain.

## How a connected page would use it (not built)

1. On open: `GET /docs` (page through it) to fill the page's maps, `GET /events` for the record, remember the `head`.
2. On a decision: `PUT` with the `rev` just read. On `409`, show the person what changed (`error.current`) and let them decide again; never retry the same body.
3. Sign-offs, hand-offs and labels are separate documents, so two people working on different parts of a cluster do not conflict.
4. Every few seconds: `GET /events?after=<last seq>`; fetch the documents the new entries name.
5. Keep the page's policy engine, results grade and trace map as they are: they are functions of the documents.

## Limits you should know about

* One writer at a time (SQLite). Fine for a team; not a design for hundreds of simultaneous writers.
* No user management: people and tokens are made with `init` and `rotate-token` by whoever has the database. No expiry, no single sign-on.
* The database file is not encrypted. Treat it as you treat the requirements themselves.
* The server never calls an AI model and never sends requirement text anywhere.
