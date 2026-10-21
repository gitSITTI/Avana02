"""What the AI gateway decides, as plain functions: no sockets, no files, so every rule can be tested on its own.

The gateway sits between the pipeline and the model. Before it forwards a prompt it asks, in this order:

  1. who is asking (the reference server says, from the token), and is that person allowed to use AI at all (observers are not)
  2. which requirements are in the prompt (the caller must say), and does the gateway know every one of them
  3. does the shared project have an AI switch and a data sheet, and does `reqin.aigate.ensure` open for the group (the same rules, the same code, as the page's)
  4. is the model route this gateway really forwards to the one the sheet describes (model, where it runs, whether text leaves, what is kept, for how long)
  5. does the prompt hold the wording of any requirement the caller did not declare (checked against fingerprints of every requirement's wording)

The first "no" wins and names the rule. Nothing the gateway says contains a requirement's text.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..aigate import AiBlocked, Decision, Sheet, ensure

MARKINGS_FORMAT = "reqin-markings/1"
WINDOW = 6                      # words in one fingerprint
MIN_WORDS = 4                   # a requirement shorter than this cannot be recognised in a prompt, and is declared by its caller only
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,199}")
SHEET_FIELDS = tuple(Sheet.__dataclass_fields__)
STR_FIELDS = ("model", "where", "log", "approved", "unstated", "reviewed_by", "reviewed_at", "entered_by")

# What a person is told for each way the gate can say no. Codes are the gate's own (reqin.aigate.Decision.code) plus the gateway's.
WORDS = {
    "off": "The AI switch is off for this project, so nothing goes to a model. A lead switches it on, on the AI use page.",
    "unreviewed": "The AI data sheet has no reviewer's name and date, so nothing goes to a model.",
    "sheet": "The AI data sheet contradicts itself, so nothing goes to a model.",
    "classified": "A requirement in this group carries a classified marking. It is never sent.",
    "unknown": "A requirement in this group carries a marking this table does not know. It is never sent: add the marking style to the rules, in the open.",
    "unstated": "A requirement in this group has no marking recorded, and the sheet says to keep those from the AI.",
    "marking": "This group is marked above what the AI data sheet approves.",
    "no_sheet": "The shared project has no AI data sheet yet. A lead sets one on the AI use page; until then nothing goes to a model.",
    "bad_sheet": "The AI data sheet on the server is not in a shape the gateway reads, so nothing goes to a model.",
    "sheet_mismatch": "The model this gateway forwards to is not the one the AI data sheet describes, so the sheet's approval does not apply.",
    "observer": "Observers read; they do not use the AI.",
    "undeclared_text": "The prompt contains the wording of requirements that were not declared for it.",
}


@dataclass
class Verdict:
    ok: bool
    status: int                 # the HTTP status to answer with when not ok
    code: str
    message: str
    level: str = ""             # the marking of the group, as far as it was read
    detail: list[str] = field(default_factory=list)


def words(text: str) -> list[str]:
    """The words of a text for fingerprinting: Unicode-normalised, lower case, letters and digits only."""
    t = unicodedata.normalize("NFKC", text).lower()
    return [w for w in re.split(r"[\W_]+", t) if w]


def _hash(run: list[str]) -> str:
    return hashlib.sha256(" ".join(run).encode("utf-8")).hexdigest()[:16]


def fingerprints(text: str) -> list[str]:
    """Hashes of every run of WINDOW words of a requirement's wording (the whole wording when it is shorter). The wording itself is not kept."""
    w = words(text)
    if len(w) < MIN_WORDS:
        return []
    runs = [w] if len(w) <= WINDOW else [w[i:i + WINDOW] for i in range(len(w) - WINDOW + 1)]
    return sorted({_hash(r) for r in runs})


@dataclass
class Markings:
    """The requirements the gateway knows: each one's marking (as the source recorded it) and the fingerprints of its wording."""
    marks: dict[str, Any]
    holders: dict[str, set[str]]            # fingerprint -> the requirements whose wording holds it
    count: dict[str, int] = field(default_factory=dict)     # how many fingerprints each requirement has

    @classmethod
    def from_file(cls, data: Any) -> "Markings":
        if not isinstance(data, dict) or data.get("format") != MARKINGS_FORMAT or not isinstance(data.get("requirements"), dict):
            raise ValueError(f"not a markings file: its format is not {MARKINGS_FORMAT}")
        marks: dict[str, Any] = {}
        holders: dict[str, set[str]] = {}
        count: dict[str, int] = {}
        for rid, row in data["requirements"].items():
            if not ID_RE.fullmatch(str(rid)) or not isinstance(row, dict) or set(row) - {"marking", "fp"}:
                raise ValueError(f"requirement {str(rid)[:60]!r}: not an id and a marking with fingerprints")
            m = row.get("marking")
            if m is not None and not isinstance(m, str):
                raise ValueError(f"requirement {rid}: the marking must be text or null")
            fp = row.get("fp", [])
            if not isinstance(fp, list) or not all(isinstance(x, str) and re.fullmatch(r"[0-9a-f]{16}", x) for x in fp):
                raise ValueError(f"requirement {rid}: fingerprints are 16 hex digits each")
            marks[rid] = m
            count[rid] = len(set(fp))
            for x in fp:
                holders.setdefault(x, set()).add(rid)
        return cls(marks, holders, count)

    @staticmethod
    def build(rows: Iterable[tuple[str, Any, str]]) -> dict[str, Any]:
        """The file for [(id, marking, wording), ...]. Only fingerprints of the wording go in it."""
        out: dict[str, Any] = {}
        for rid, marking, text in rows:
            if rid in out:
                raise ValueError(f"requirement {rid} appears twice")
            out[rid] = {"marking": marking, "fp": fingerprints(text or "")}
        return {"format": MARKINGS_FORMAT, "window": WINDOW, "requirements": dict(sorted(out.items()))}

    def undeclared(self, prompt: str, declared: set[str], min_windows: int = 2) -> dict[str, int]:
        """Requirements whose wording is in the prompt although they were not declared: {id: how many fingerprints of it were found}. A fingerprint that a declared
        requirement also holds is not counted (shared boilerplate). Fewer than `min_windows` fingerprints of one requirement is a coincidence, not a leak (a requirement that
        has fewer fingerprints than that needs all of them)."""
        w = words(prompt)
        seen: set[str] = set()
        for n in range(MIN_WORDS, WINDOW + 1):          # runs of 4 and 5 words can only be a whole short requirement; runs of 6 are what longer ones are cut into
            seen.update(_hash(w[i:i + n]) for i in range(len(w) - n + 1))
        hits: dict[str, int] = {}
        for fp in seen:
            who = self.holders.get(fp)
            if not who or who & declared:
                continue
            for rid in who:
                hits[rid] = hits.get(rid, 0) + 1
        return {r: n for r, n in sorted(hits.items()) if n >= min(min_windows, self.count.get(r, 1))}


def sheet_from_doc(doc: Any) -> tuple[Sheet, bool] | None:
    """The sheet and the switch from the `proj/ai` document of the reference server, or None when it is not in a shape this reads. Unknown entries are refused: what this
    returns decides whether text may leave."""
    if not isinstance(doc, dict) or set(doc) - {"on", "sheet"} or not isinstance(doc.get("on"), bool) or not isinstance(doc.get("sheet"), dict):
        return None
    sh = doc["sheet"]
    if set(sh) - set(SHEET_FIELDS):
        return None
    # a name or a date that is a number, or a "leaves" that is not true or false, is not a sheet anyone reviewed: say so instead of failing later. `days` is left to the gate's own check.
    if any(k in sh and not isinstance(sh[k], str) for k in STR_FIELDS) or ("leaves" in sh and not isinstance(sh["leaves"], bool)):
        return None
    try:
        return Sheet(**sh), doc["on"]
    except TypeError:
        return None


def route_mismatch(sheet: Sheet, route: dict[str, Any]) -> list[str]:
    """What the sheet says about the model that the route this gateway forwards to does not do. The sheet's approval is for the model it names, run the way it says."""
    out = []
    for k in ("model", "where", "leaves", "log"):
        if sheet.__dict__[k] != route[k]:
            out.append(f"{k}: the sheet says {sheet.__dict__[k]!r}, this route is {route[k]!r}")
    if sheet.log != "none" or route["log"] != "none":
        if sheet.days != route["days"]:
            out.append(f"days: the sheet says {sheet.days!r}, this route is {route['days']!r}")
    return out


def prompt_text(body: Any) -> str:
    """Every piece of text in a request that a model could read: every string in it, keys included (so text cannot hide in a field this code does not know about)."""
    parts: list[str] = []

    def walk(v: Any, depth: int = 0) -> None:
        if depth > 40:
            raise ValueError("the request is nested too deeply")
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, list):
            for x in v:
                walk(x, depth + 1)
        elif isinstance(v, dict):
            for k, x in v.items():
                parts.append(str(k))
                walk(x, depth + 1)

    walk(body)
    return "\n".join(parts)


def decide(*, role: str, ids: list[str], markings: Markings, ai_doc: Any, ai_present: bool, route: dict[str, Any], prompt: str, max_requirements: int = 200, min_windows: int = 2) -> Verdict:
    """The gateway's decision for one request, in the order described at the top. `ai_present` is False when the server holds no `proj/ai` document."""
    if role == "observer":
        return Verdict(False, 403, "observer", WORDS["observer"])
    if not ids:
        return Verdict(False, 400, "no_requirements", "Say which requirements are in the prompt: X-Reqin-Requirements: REQ-1,REQ-2.")
    if len(ids) > max_requirements:
        return Verdict(False, 400, "too_many", f"At most {max_requirements} requirements in one prompt.")
    missing = [i for i in ids if i not in markings.marks]
    if missing:
        return Verdict(False, 400, "unknown_requirement", "The gateway does not know these requirements: " + ", ".join(missing[:5]) + (" …" if len(missing) > 5 else ""), detail=missing[:20])
    if not ai_present:
        return Verdict(False, 403, "no_sheet", WORDS["no_sheet"])
    parsed = sheet_from_doc(ai_doc)
    if parsed is None:
        return Verdict(False, 403, "bad_sheet", WORDS["bad_sheet"])
    sheet, switch = parsed
    try:
        d: Decision = ensure(sheet, switch, [markings.marks[i] for i in ids])
    except AiBlocked as e:
        return Verdict(False, 403, e.decision.code, WORDS.get(e.decision.code, "The gate says no."), e.decision.level, list(e.decision.detail))
    bad = route_mismatch(sheet, route)
    if bad:
        return Verdict(False, 403, "sheet_mismatch", WORDS["sheet_mismatch"], d.level, bad)
    leaks = markings.undeclared(prompt, set(ids), min_windows)
    if leaks:
        return Verdict(False, 403, "undeclared_text", WORDS["undeclared_text"] + " " + ", ".join(list(leaks)[:5]) + (" …" if len(leaks) > 5 else ""), d.level, list(leaks)[:20])
    return Verdict(True, 200, "open", "The gate is open for this group.", d.level)


def canon(v: Any) -> str:
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
