"""Mint a Jama Connect OAuth bearer token for reqin's `jama` connector.

WHY THIS IS A SEPARATE FILE: Jama's login is `POST /rest/oauth/token`. Everything in reqin's connector kit is GET-only, and reqin says so and proves it, so the one
POST lives here, in a file you choose to use, and does exactly one thing: it exchanges your API client id and secret for a token and hands the token back as a header.
It reads nothing else, writes nothing, and never prints the secret.

USE
    export JAMA_CLIENT_ID=...        # an API credential pair (Jama: set API credentials); a Named Creator licence is needed for REST access
    export JAMA_CLIENT_SECRET=...
    PYTHONPATH=connectors/jama reqin sample jama+https://yourorg.jamacloud.com \
        --opt project=<id or name> --opt auth_hook=jama_oauth_hook:headers \
        --opt token_url=https://yourorg.jamacloud.com/rest/oauth/token

The token lasts about an hour (the vendor's page says 3,599 seconds), so a long read can outlive it: read in parts (item_types, peek) or run again.
Status: written from the vendor's description of the call (grant_type=client_credentials, id and secret as Basic). NEVER run against a real Jama server.
Options: token_url (required), client_id_env / client_secret_env (names of the environment variables; default JAMA_CLIENT_ID / JAMA_CLIENT_SECRET), timeout (seconds, 30).
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping


class TokenError(RuntimeError):
    """The token could not be had. The message never holds the client secret."""


def headers(options: Mapping[str, Any], env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ if env is None else env
    id_name, secret_name = str(options.get("client_id_env") or "JAMA_CLIENT_ID"), str(options.get("client_secret_env") or "JAMA_CLIENT_SECRET")
    cid, secret = env.get(id_name, ""), env.get(secret_name, "")
    if not cid or not secret:
        raise TokenError(f"environment variables {id_name} and {secret_name} must hold the API client id and secret (their values are never printed)")
    url = str(options.get("token_url") or "")
    host = urllib.parse.urlsplit(url).hostname or ""
    if not url.startswith("https://") and host not in ("localhost", "127.0.0.1", "::1"):
        raise TokenError("option 'token_url' must be an https:// URL (a client secret is never sent in clear text)")
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    req = urllib.request.Request(url, data=b"grant_type=client_credentials", method="POST",
                                 headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=float(options.get("timeout") or 30)) as r:      # noqa: S310  (https or loopback, checked above)
            body = json.loads(r.read(1 << 20))
    except urllib.error.HTTPError as e:
        raise TokenError(f"the token request was refused: HTTP {e.code} (check the client id and secret, and that the account may use REST)") from None
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise TokenError(f"the token request failed ({type(e).__name__})") from None
    token = body.get("access_token") if isinstance(body, dict) else None
    if not token or not isinstance(token, str):
        raise TokenError("the token answer has no access_token")
    return {"Authorization": f"Bearer {token}"}
