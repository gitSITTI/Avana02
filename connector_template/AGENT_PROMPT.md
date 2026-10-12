# Prompt for the agent that finishes this connector against the real system

You are finishing a reqin connector. Read `src/reqin_acme/adapter.py` (five TODO(agent) markers), `profile.yaml`, `tests/test_adapter.py`,
and `../reqin/CONNECTORS.md` section "Rules every connector keeps".

Do, in this order, and run `pytest` after each step:
1. Run `reqin sample acme+https://<host>/<base> --opt token_env=<NAME>` (a human provides the environment variable and the approval). Paste NOTHING
   from the real system into the repo except what the human has approved and sanitised.
2. Make `sniff`, the URL/paging in `_items`, and the field names in `read` match what you saw. Keep the connector read-only: use only `ReadOnlyHttp.get`.
3. Update the fake server in the tests to return the same SHAPE you saw (with fictional content) and add a test for every difference you had to handle.
4. Edit `profile.yaml` so `uid` and `text` come from the right fields. Do not guess: if two fields could be the statement, ask the human.
5. Run `reqin import ... --profile profile.yaml --audit audit.jsonl`; give `audit.jsonl` to the human for IT review.
6. Do NOT change `maturity` to "live-verified": a human does that after checking the result against the source system.

Definition of done: `pytest` green; every record has a locator; nothing is dropped without a reason; no secret in any file, log or message; only GET requests in the audit.
