# Reference server: one shared copy of the decisions

**What it is.** A small server (Python standard library only: `http.server` and SQLite) that keeps *one* copy of a project's decisions, sign-offs, hand-offs and labels, so two people in two browsers see the same thing and cannot silently overwrite each other.
**What it is not.** It has no user directory or single sign-on, no TLS, no encryption of the file on disk, and it has never been run with real program data. The prototype page works on its own until someone signs in: a page that is not opened from this server's address (a file on a disk, another site) is not connected to it, and keeps its own copy in the browser as before.
**How the page uses it.** Open the page from the server (`http://<server>/app/`), paste the token you were given, and the page shows the project's people, decisions, sign-offs, hand-offs, claims, labels and AI switch as the server has them, sends what you decide, and shows what others decide within a few seconds. See *The page, connected* below.
**Where the rules live.** The server enforces the few rules it can enforce without knowing your policy (table below). *Which* lenses a given decision needs signed (the policy engine) stays in the page; there is no second copy of it here, on purpose: two copies drift.

## Run it

```bash
pip install -e reqin                                   # nothing extra to install: no web framework
echo '[{"key":"sam","name":"Sam Okafor","role":"reviewer","lens":"SE"},
       {"key":"morgan","name":"Morgan Hale","role":"lead","lens":"SE"},
       {"key":"lee","name":"Lee Park","role":"observer"}]' > people.json
reqin-server init  --db shared.db --project demo --people people.json --tokens-out tokens.json   # tokens shown once, file mode 600
reqin-server serve --db shared.db                      # http://127.0.0.1:8780, this machine only
reqin-server serve --db shared.db --app prototype/project   # also serves the page, read only, at http://127.0.0.1:8780/app/ (same address, so no CORS)
reqin-server demo --db demo.db --seed prototype/demo/seed.json --app prototype/project   # a new demo project with sample activity and six people; each token goes to demo.db.tokens.json (mode 600)
python3 reqin/serve_standalone.py demo ...             # the same commands with nothing installed: only Python's standard library is loaded
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
| **Project settings and rulings are for a lead.** `proj/…` (the AI switch and data sheet), `adj/<cluster>` (a ruling on a cluster), `gadj/<a>/<b>` (a ruling on a labelled pair). | `403 lead_only` |
| **Anyone can raise an objection; only a lead can close it.** A write that withdraws `obj/<cluster>` (`null`) is a lead's. | `403 lead_only` |
| **A label is its labeller's own.** `label/<a>/<b>/<person>` is written by that person, and has exactly those four parts. | `403 not_yours`, `400 bad_label_id` |
| **A sign-off sits in the signer's own lens, including withdrawal.** `sign/<id>/SE` is for someone who reviews as SE. | `403 wrong_lens` |
| `OWN` and `ADJ` slots are for leads. | `403 lead_only` |
| **Only the signer withdraws an active sign-off.** A decision change still clears all its old sign-offs automatically. | `403 not_yours` |
| **Nobody signs a decision they made**, lead or not. | `403 self_sign` |
| A sign-off needs a decision to bind to, and names its revision: `{"rev": 2}`. | `409 nothing_to_sign`, `409 stale_signoff` (with `decision_rev`) |
| **A new revision of a decision clears the sign-offs on the old one**, in the same step, each clearing in the record. Other decisions' sign-offs are untouched. | the reply lists `cleared` |
| **A repeated request is done once.** Same key and same request: the first reply again, marked `replay: true` and `Idempotent-Replay: true`. | same key, different request: `422 idempotency_reuse` |
| **Who made the change comes from the token**, never from the body. | |
| Projects do not see each other; a token works in its own project only. | `403 other_project` |
| Sizes: 64 KB a document, 1 MB a request. Odd ids, bad JSON, `NaN`, extra fields, other content types. | `413`, `400 bad_doc_id`, `400 bad_json`, `400 bad_request`, `415 json_only` |
| Nothing a caller sends is logged (method, path without the query, status only). Errors never show a stack trace. | |

At start-up or when seeding a demo: `400 bad_app_dir` (the `--app` folder has no page), `400 bad_seed` (a seed file that cannot be read or is not for these people), `404 no_project`, `409 not_empty` (a project that already has documents is not seeded).
Other answers: `401 no_token`, `401 bad_token` (with `WWW-Authenticate`), `404 no_doc`, `404 no_route`, `405 method_not_allowed`, `411 length_required`, `500 server_error` (generic).

## The record

Every change is an entry: `seq`, `type`, `actor`, `target`, `rev`, `body_hash` (SHA-256 of the document revision), `text`, `at`, `prev`, `hash`, where `hash = SHA-256(prev + "|" + canonical JSON of the other fields)` and the first `prev` is 64 zeros. The entry and the document revision are written in one transaction, or neither is.
`verify` recomputes it from the stored documents and names the first thing that does not follow: an entry edited, removed or out of order, a document revision whose body, author or time no longer matches its entry, or a revision that is stored but not in the record.

**What the chain does not prove.** It shows the record was not edited in place. It cannot show that the *newest* entries were not removed (a shorter chain is still a valid chain), and whoever holds the database file and writes the program could rebuild the whole chain. So write down the `head` hash after a milestone, keep it somewhere the database's administrator cannot reach, and pass it back as `expect_head`.
The prototype page's own record uses a short demonstration hash (32 bits) so the screen is readable; this server uses SHA-256. They are not the same chain.

## The page, connected

Open `http://<server>/app/` (the server serves the page itself, read only, from the folder it was started with: `--app`). On Home or the opening screen, paste your token and press *Sign in*. The token is typed into a password field, kept in the page's memory only until you close the tab or sign out, and never written to the address, a cookie or the browser's storage.

1. **Signing in.** `GET /me`, `GET /people`, then `GET /docs` a page at a time. Every document is checked with the same rules the page applies to a file you load (known kind, known cluster or requirement, right shape); one that fails is left out and listed on the card, never shown. The people of the project replace the sample people, so *who you are* comes from the token, not from a picker.
2. **A decision.** The page sends it a moment after you stop (`PUT` with the revision it last read as `if_rev`, and an idempotency key so that a lost reply is retried without doing it twice). On `409` the person is told who changed it first and shown both versions; the page does not retry the same body. A refused change (`403`, `400`) is taken back and the server's words are shown.
3. **Others' work.** `GET /events?after=<last seq>` about every 4 seconds; the documents the new entries name are fetched. A cluster someone changed while you have it open is marked *changed after you opened it* and deciding is paused until you reload it.
4. **No network.** Changes wait in the page and are sent, once, when the server answers again. The shell says *Offline* and how many are waiting.
5. **No copy here.** While signed in the browser keeps nothing of the project (the autosave stops; *Load from a file* and *Start over* are off, because they would replace what everyone shares). *Save to a file* still gives you what is on screen. Signing out puts back what the browser had before, including what you had typed and the page's own record of what you did.
6. **The record.** *Check the shared record* asks the server to recompute its whole record and says what it found, naming the entry where it stops following. The page stops reading and sending, and says so, if the record is shorter or different from the one it saw a moment before.
7. **Not moved to the server.** The policy engine, the results grade and the trace map stay in the page: they are functions of the documents. The page's own short event chain (32 bits, for the screen) is not this server's record (SHA-256) and is not sent.

What a person with a lens sees and may do comes from the token. The server enforces the table above; the page also greys out what the server would refuse, so that people are not offered buttons that fail.

## Limits you should know about

* One writer at a time (SQLite). Fine for a team; not a design for hundreds of simultaneous writers.
* The page reads the server every few seconds (no push). Two people who press *Record* at the same moment on the same cluster: the second is refused and told, never silently merged.
* No user management: people and tokens are made with `init` and `rotate-token` by whoever has the database. No expiry, no single sign-on.
* The database file is not encrypted. Treat it as you treat the requirements themselves.
* The server never calls an AI model and never sends requirement text anywhere.
