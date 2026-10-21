# Capabilities

Generated from [capabilities.json](capabilities.json) by `python3 tools/capabilities.py`; do not edit this table by hand.

Implemented means code exists with the referenced checks. It does not certify a deployment or a real requirements set.

| Capability | State | Code | Checks | Limit |
|---|---|---|---|---|
| Source ingestion | implemented | [reqin/src/reqin/adapters](../reqin/src/reqin/adapters) | [reqin/tests](../reqin/tests) | Synthetic fixtures and fake servers; no real source system verified. |
| Mechanical comparison | implemented | [reqin/src/reqin/compare](../reqin/src/reqin/compare) | [reqin/tests/test_compare.py](../reqin/tests/test_compare.py) | Draft rules and vocabulary; no general semantic understanding or real-corpus accuracy claim. |
| Portable comparison review | implemented | [tools/review](../tools/review) | [reqin/tests/test_review_workspace.py](../reqin/tests/test_review_workspace.py) | Checked datasets and engine output, review notes and draft export. No sign-offs, source write-back or final approval. |
| Prototype shared decisions | implemented | [prototype/parts/connect.js](../prototype/parts/connect.js) | [prototype/b21.py](../prototype/b21.py) | Token-based reference server; sample requirements. Does not consume imported comparison output. |
| Reference server | implemented | [reqin/src/reqin/server](../reqin/src/reqin/server) | [reqin/tests/test_server.py](../reqin/tests/test_server.py) | No SSO, token expiry, built-in TLS, disk encryption or authoritative completion policy. |
| AI gateway | implemented | [reqin/src/reqin/gateway](../reqin/src/reqin/gateway) | [reqin/tests/test_gateway.py](../reqin/tests/test_gateway.py) | No real model or deployed firewall verified; no semantic leak detection or streaming. |
| AI comparison stages | planned | [docs/agent_prompts/comparison_engine.md](../docs/agent_prompts/comparison_engine.md) | None | Later model-assisted stages are not implemented. |
| Human-labelled real-world evaluation | planned | [docs/GOLD_SET.md](../docs/GOLD_SET.md) | None | Needs two human labellers and an approved evaluation corpus outside this repository. |
