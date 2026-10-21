"""The gateway's settings: a small JSON file. The model's API key is never in it: it names the environment variable that holds the key."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..aigate import LOG, WHERE


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    server: str                  # the reference server (where the AI switch and data sheet are kept), no trailing slash
    upstream_url: str            # the model's chat endpoint
    key_env: str                 # name of the environment variable holding the model's API key ("" for a model that wants none)
    route: dict[str, Any]        # what the route really is: model, where, leaves, log, days (the sheet must say the same)
    markings: Path
    log: Path
    max_body: int
    max_requirements: int
    min_windows: int
    timeout: float
    allow_remote: bool


def _url(v: Any, what: str, path: bool) -> str:
    if not isinstance(v, str):
        raise ConfigError(f"{what} must be a web address")
    u = urlsplit(v)
    if u.scheme not in ("http", "https") or not u.hostname or u.username or u.password or u.fragment:
        raise ConfigError(f"{what} must be an http or https address with no password in it")
    if not path and u.path not in ("", "/"):
        raise ConfigError(f"{what} is the server's address without a path")
    return v.rstrip("/") if not path else v


def load_config(path: str | Path) -> Config:
    p = Path(path)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ConfigError(f"cannot read {p}: {e}") from None
    if not isinstance(d, dict):
        raise ConfigError("the settings file must be a JSON object")
    known = {"listen", "server", "upstream", "markings", "log", "limits", "allow_remote"}
    if set(d) - known:
        raise ConfigError("unknown settings: " + ", ".join(sorted(map(str, set(d) - known))))
    lis = d.get("listen", {})
    up = d.get("upstream")
    lim = d.get("limits", {})
    if not isinstance(lis, dict) or not isinstance(up, dict) or not isinstance(lim, dict):
        raise ConfigError("listen, upstream and limits must be objects")
    host, port = lis.get("host", "127.0.0.1"), lis.get("port", 8790)
    if not isinstance(host, str) or not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ConfigError("listen needs a host and a port")
    upk = {"url", "key_env", "model", "where", "leaves", "log", "days"}
    if set(up) - upk or not {"url", "model", "where", "leaves", "log"} <= set(up):
        raise ConfigError("upstream needs url, model, where, leaves and log (and days when anything is kept); nothing else")
    if not isinstance(up["model"], str) or not up["model"].strip():
        raise ConfigError("upstream.model must name the model: the sheet has to name the same one")
    if up["where"] not in WHERE or up["log"] not in LOG or not isinstance(up["leaves"], bool):
        raise ConfigError(f"upstream.where is one of {', '.join(WHERE)}, upstream.log one of {', '.join(LOG)}, upstream.leaves true or false")
    days = up.get("days", 0)
    if isinstance(days, bool) or not isinstance(days, int) or days < 0:
        raise ConfigError("upstream.days is a whole number")
    key_env = up.get("key_env", "")
    if not isinstance(key_env, str) or (key_env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_env)):
        raise ConfigError("upstream.key_env is the NAME of an environment variable, not the key itself")
    for k in ("markings", "log"):
        if not isinstance(d.get(k), str) or not d[k]:
            raise ConfigError(f"{k} is a file path")

    def num(k: str, default: float, lo: float, hi: float) -> float:
        v = lim.get(k, default)
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            raise ConfigError(f"limits.{k} must be a number from {lo} to {hi}")
        return v

    if set(lim) - {"max_body_bytes", "max_requirements", "leak_min_windows", "timeout_s"}:
        raise ConfigError("unknown limits: " + ", ".join(sorted(set(lim) - {"max_body_bytes", "max_requirements", "leak_min_windows", "timeout_s"})))
    base = p.parent
    return Config(host=host, port=port, server=_url(d.get("server"), "server", False), upstream_url=_url(up["url"], "upstream.url", True), key_env=key_env,
                  route={"model": up["model"], "where": up["where"], "leaves": up["leaves"], "log": up["log"], "days": days},
                  markings=(base / d["markings"]), log=(base / d["log"]),
                  max_body=int(num("max_body_bytes", 262144, 1024, 8388608)), max_requirements=int(num("max_requirements", 200, 1, 5000)),
                  min_windows=int(num("leak_min_windows", 2, 1, 20)), timeout=float(num("timeout_s", 120, 1, 3600)), allow_remote=bool(d.get("allow_remote", False)))


def upstream_key(cfg: Config) -> str:
    return os.environ.get(cfg.key_env, "") if cfg.key_env else ""
