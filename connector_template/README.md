# reqin connector template

Copy this folder to start a new connector. It is a **working** example (a paged read-only JSON API) with five `TODO(agent)` seams.

```bash
cp -r connector_template ../reqin-mysystem && cd ../reqin-mysystem
pip install -e "../requirements-consolidator/reqin[test]" -e ".[test]"
pytest                                   # green before you change anything
reqin connectors                         # your connector is listed (found through the entry point in pyproject.toml)
```

Then follow `AGENT_PROMPT.md` (written for an AI agent, equally good as a checklist for a person). Everything a live connector must
do safely (GET only, verified TLS, secrets from the environment, retries, caps, audit) comes from `reqin.connect`: you do not write it.
