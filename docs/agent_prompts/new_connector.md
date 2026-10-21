# Prompt: finish a connector for a new requirements source (for an agent with a shell)

How to use this: give an agent that can run commands in a checkout of this repository the text below the line, with the source's name filled in where it says `<SOURCE>`. A **person** has to provide the access: an approved read-only account, the address, and a secret in an environment variable. The agent must not ask for the secret in the conversation, and must not write it to any file.

----------------------------------------------------------------------------------------------------

You are adding a connector for **<SOURCE>** to a repository that reads requirements from many systems into one canonical dataset. Read `AGENTS.md` in the repository root first and keep its rules (above all: no real data, no secrets in files, and say what you did not check).

## Read, in this order

1. `reqin/CONNECTORS.md`: the table of how far each connector has been proven, and the rules every connector keeps.
2. `connector_template/README.md` and `connector_template/AGENT_PROMPT.md`: a working, tested starting point with five `TODO(agent)` seams, and the steps to follow. **Follow that prompt's steps and order; this page only adds the repository rules and the report.**
3. `reqin/INPUT_LAYER.md` (the canonical model) and `reqin/GUI_CONTRACT.md` sections 3 and 6 (what a dataset is, and the fourteen test datasets).

## What you must keep

- **Read-only.** Only `ReadOnlyHttp.get`. No write verb, no way to turn TLS verification off, no credential forwarded to another host.
- **Secrets from environment variables**, never in a file, a command line, a log line, an error message or a commit.
- **Nothing dropped silently, a locator on every record.** A record that cannot become a requirement goes to `rejected.jsonl` with a reason.
- **No real data in the repository.** The fake server in the tests returns the *shape* of what the real system returns, with invented content. If a person pastes something from the real system, do not copy it into a file.
- **`maturity` stays `fake-server-tested`.** Only a person who has run the connector on the real system and compared the output with the source changes it to `live-verified`.

## Done means

1. `python3 -m pytest -q` in `reqin/` and in your connector's folder passes, and your connector's tests include one for **every difference** between your fake and what the real system does that you had to handle.
2. `reqin check-dataset DIR` passes on a dataset your connector wrote from the fake, and the connector passes `reqin.testing.check_adapter`.
3. `reqin connectors` lists it with the right maturity and a "Not proven" column that says what only the real system can settle.
4. You broke it on purpose at least three ways (a write verb, a dropped record, a leaked secret) and a test failed each time.
5. `git status` shows no secret, no real data, no generated file.

## Report

What you built, what you assumed about the real system and could not check, each difference from the fake, the `audit.jsonl` the person should give to IT security (described, not pasted), and a list headed **Not checked**.
