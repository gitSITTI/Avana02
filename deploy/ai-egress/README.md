# The network wall around the AI model

These are **examples** and a **check**. The gateway ([`docs/AI_GATEWAY.md`](../../docs/AI_GATEWAY.md)) refuses prompts the project has not approved; this folder is about making the gateway the only way to the model.

| File | What it is |
|---|---|
| `wall_check.py` | the check IT runs from each machine that matters. Python standard library only. |
| `wall.example.json` | a plan for separate hosts (pipeline, gateway, reference server, model, a person's workstation) |
| `nftables-model-host.example.nft` | the model host's firewall: only the gateway reaches the model's port; the host starts no connection to anything |
| `compose.example.yaml`, `gateway.compose.example.json`, `litellm.example.yaml`, `wall.compose.example.json` | the same idea on one machine with containers: the model on an `internal` network with no route out, the gateway the only container on both networks |

Every address in them is a placeholder. **Nothing here was started** by the author (no container engine daemon was running where it was written): `docker compose config` accepts the compose file and `nft -c` accepts the firewall file, and the check was run against sockets on one machine. The check is how you find out whether it holds on yours.

## How the check works

`wall_check.py run` tries to open TCP connections, from the machine it runs on, to the places the plan says must be reachable (`open`) and must not be (`blocked`). It sends no requirement text; for the gateway it also does a `GET /v1/health` to be sure the door that answered is the gateway.

A connection that fails proves the wall only if the target was up and listening, and a model that is switched off "passes" every wall check. So every `blocked` check in a plan names an `open` check of the **same address from another role** (`target_up_from`), and the verdict comes from `combine`, which needs the reports of every role, made against the same plan by the same copy of the script on the same day:

```bash
python3 wall_check.py hash --plan wall.json                                   # the plan's fingerprint: the same on every machine
python3 wall_check.py run --plan wall.json --role app      --out app.json     # on the pipeline host
python3 wall_check.py run --plan wall.json --role gateway  --out gateway.json # on the gateway host
python3 wall_check.py run --plan wall.json --role model    --out model.json   # on the model host
python3 wall_check.py run --plan wall.json --role workstation --out ws.json   # on a person's machine
python3 wall_check.py run --plan wall.json --role admin    --out admin.json   # on any machine that is allowed out to the internet
python3 wall_check.py combine --plan wall.json app.json gateway.json model.json ws.json admin.json
```

`run` exits 1 when something is not as planned and prints which. `combine` exits 0 only when every check holds and every blocked check has its proof. Keep the reports with the firewall configuration they were run against; they carry the plan's and the script's SHA-256, the machine's name and the time. They catch mistakes. They do not stop someone who forges one.

`python3 wall_check.py self-test` runs the script against sockets of its own to show it works on the machine.

Use IP addresses for what must be blocked: a name that does not resolve proves the name is cut off, not the route (`"allow_unresolved": true` accepts that, knowing it is weaker). The check connects directly and ignores `HTTP_PROXY`; it tests the path, not a proxy.

## One machine with containers

```bash
export MODEL_IMAGE=...  LITELLM_IMAGE=...  LITELLM_MASTER_KEY=...        # images pinned by digest
touch markings.json                                                       # make the real one first (docs/AI_GATEWAY.md)
docker compose -f compose.example.yaml up -d

mkdir -p out
# the gateway's own view of the network
docker run --rm --network container:reqin-ai-gateway-1 -v "$PWD:/w:ro" -v "$PWD/out:/out" python:3.13-slim \
  python /w/wall_check.py run --plan /w/wall.compose.example.json --role gateway --out /out/gateway.json
# a throwaway container on the team network, and one on the model's network
docker run --rm --network reqin-ai_team  -v "$PWD:/w:ro" -v "$PWD/out:/out" python:3.13-slim \
  python /w/wall_check.py run --plan /w/wall.compose.example.json --role team-probe  --out /out/team-probe.json
docker run --rm --network reqin-ai_inner -v "$PWD:/w:ro" -v "$PWD/out:/out" python:3.13-slim \
  python /w/wall_check.py run --plan /w/wall.compose.example.json --role inner-probe --out /out/inner-probe.json
# on the host, and on a machine with internet access
python3 wall_check.py run --plan wall.compose.example.json --role app   --out out/app.json
python3 wall_check.py run --plan wall.compose.example.json --role admin --out out/admin.json
python3 wall_check.py combine --plan wall.compose.example.json out/*.json
```

(The container names depend on your engine; `docker ps` shows them.) **What this layout does not do:** on one machine the gateway sits on a network that can reach the internet, so a compromised gateway could. Keeping it in would take rules on the host (the `DOCKER-USER` chain, or your network's egress rules); the plan does not claim it.

## Separate hosts

Load `nftables-model-host.example.nft` on the model host (`nft -c -f` first), put the gateway on a network only the pipeline can reach, give the reference server the same treatment, and use `wall.example.json`. The model host should be on a network with no route to the internet at all; the firewall file is the second layer, not the first.

## What a passing result does not mean

That the markings are right, that the sheet is true (does the model really keep nothing?), or that the model host logs nothing. Check logging on the host itself. See "What your IT and security staff still have to do" in [`docs/AI_DATA_HANDLING.md`](../../docs/AI_DATA_HANDLING.md).
