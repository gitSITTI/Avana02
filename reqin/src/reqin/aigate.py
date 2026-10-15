"""The AI gate: the rules that decide whether requirement text may be sent to an AI model at all, before any prompt is built.

The prototype page and this module follow the same rules; `docs/ai_gate_cases.json` is the shared table both are tested against, so they
cannot drift apart without a test failing. The rules are written in docs/AI_DATA_HANDLING.md. What this module is *not*: a decision about
what is allowed. Your security and export-control reviewers decide that and write it into the data sheet; this code refuses to go beyond
what the sheet says, and refuses everything while the sheet is unreviewed, inconsistent, or the switch is off.

A pipeline should call `ensure(...)` for each group of requirements before it builds a prompt, and put no text in the prompt when it raises.
Network rules at the gateway (no route from the model host to the internet, no logging at the model host) are the real wall: this is the
check that stops the application from knocking on it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

LEVELS = ("none", "cui", "exp")          # what the sheet can approve, lowest to highest
RANK = {"none": 0, "cui": 1, "exp": 2}
WHERE = ("ours", "tenant", "vendor")      # on our own servers / in our organisation's cloud tenant / a vendor's shared service
LOG = ("none", "local", "service")        # prompts and answers: not kept / kept on our servers / kept by the service provider
UNSTATED = ("none", "withhold")           # a requirement with no marking recorded: treat as "no marking", or keep it from the AI

# How a marking is read, written out so the page (prototype/parts/aigate.js) can read it exactly the same way: a space is any Unicode space (str.isspace), and part of a
# word is any letter or digit of any alphabet, or "_". So "cui" next to a letter of another alphabet ("cuié") is a word this table does not know, which is `unknown`,
# which is never sent. reqin/tests/test_aigate_page.py feeds both languages many thousands of odd markings and requires the same answer.
_NONE = {"no marking", "none", "unmarked", "public"}
_CLASSIFIED = re.compile(r"\b(top secret|secret|classified|sci)\b")
_EXPORT = re.compile(r"\b(itar|ear\d*|expt|export)\b")
_CUI = re.compile(r"\b(cui|controlled unclassified)\b")


def marking_level(text: object) -> str:
    """What a marking says: none, cui, exp (export controlled), classified, unknown (words this table does not know), unstated (nothing recorded).
    Anything not recognised is `unknown`, and `unknown` is never sent: a new marking style has to be added here, in the open, not guessed."""
    if text is None:
        return "unstated"
    if not isinstance(text, str):
        return "unknown"
    t = re.sub(r"\s+", " ", text.strip().lower().lstrip("/ "))
    if not t:
        return "unstated"
    if _CLASSIFIED.search(t):
        return "classified"
    if _EXPORT.search(t):
        return "exp"
    if _CUI.search(t):
        return "cui"
    if t in _NONE:
        return "none"
    return "unknown"


def group_level(levels: Iterable[str], unstated: str = "withhold") -> str:
    """The marking of a group of requirements is the most restrictive marking of its members."""
    levels = list(levels)
    if not levels:
        return "unstated" if unstated == "withhold" else "none"
    for bad in ("classified", "unknown"):
        if bad in levels:
            return bad
    if "unstated" in levels and unstated == "withhold":
        return "unstated"
    known = [RANK[x] for x in levels if x in RANK]
    return LEVELS[max(known)] if known else "none"


@dataclass(frozen=True)
class Sheet:
    """The AI data sheet: what the people who approved it were told about the model."""
    model: str = ""            # model name and version, as the gateway reports it
    where: str = "ours"
    leaves: bool = False       # does any requirement text leave your network on its way to the model
    log: str = "none"
    days: int = 0              # how long prompts and answers are kept, when they are kept
    approved: str = "none"     # the highest marking the reviewers approved
    unstated: str = "withhold"
    reviewed_by: str = ""
    reviewed_at: str = ""
    entered_by: str = ""       # who typed it in; not read by the gate, kept so the record says who

    def problems(self) -> list[str]:
        """Codes, in a fixed order. A sheet with any problem opens nothing: the approver has to make it consistent, nothing is capped quietly."""
        out: list[str] = []
        if not str(self.model).strip():
            out.append("model")
        if self.where not in WHERE or self.log not in LOG or self.approved not in LEVELS or self.unstated not in UNSTATED:
            out.append("values")
        if self.where == "vendor" and not self.leaves:
            out.append("vendor_leaves")
        if self.leaves and self.approved != "none":
            out.append("leaves_marked")
        if self.log == "service" and self.approved != "none":
            out.append("log_marked")
        if self.approved == "exp" and self.where != "ours":
            out.append("exp_where")
        if self.log != "none" and not (isinstance(self.days, int) and not isinstance(self.days, bool) and 1 <= self.days <= 3650):
            out.append("days")
        return out

    @property
    def reviewed(self) -> bool:
        return bool(self.reviewed_by.strip() and self.reviewed_at.strip())


@dataclass(frozen=True)
class Decision:
    open: bool
    code: str      # open, off, unreviewed, sheet, classified, unknown, unstated, marking
    level: str     # the marking of the group, as far as it was looked at
    detail: list[str] = field(default_factory=list)


def gate(sheet: Sheet, switch_on: bool, markings: Iterable[object]) -> Decision:
    """May the text of this group of requirements go to the AI? The first rule that says no wins."""
    if not switch_on:
        return Decision(False, "off", "")
    if not sheet.reviewed:
        return Decision(False, "unreviewed", "")
    p = sheet.problems()
    if p:
        return Decision(False, "sheet", "", p)
    lvl = group_level([marking_level(m) for m in markings], sheet.unstated)
    if lvl in ("classified", "unknown", "unstated"):
        return Decision(False, lvl, lvl)
    if RANK[lvl] > RANK[sheet.approved]:
        return Decision(False, "marking", lvl)
    return Decision(True, "open", lvl)


USE_FILE_FORMAT = "reqin-ai-use/1"


def load_use_file(data: dict) -> tuple[Sheet, bool]:
    """Read the `ai-use.json` the prototype page writes (or any file in that format): the sheet and whether the switch is on.
    Anything else is refused, because what this returns decides whether text may leave. Unknown keys inside the sheet are refused too."""
    if not isinstance(data, dict) or data.get("format") != USE_FILE_FORMAT:
        raise ValueError(f"not an AI use file: its format is not {USE_FILE_FORMAT}")
    sh, switch = data.get("sheet"), data.get("switch")
    if not isinstance(sh, dict) or switch not in ("on", "off"):
        raise ValueError("the AI use file has no sheet or no switch")
    names = {f for f in Sheet.__dataclass_fields__}
    extra = set(sh) - names
    if extra:
        raise ValueError("the sheet has entries this library does not know: " + ", ".join(sorted(map(str, extra))))
    return Sheet(**sh), switch == "on"


class AiBlocked(RuntimeError):
    def __init__(self, decision: Decision):
        super().__init__(f"AI is not used on this group: {decision.code}")
        self.decision = decision


def ensure(sheet: Sheet, switch_on: bool, markings: Iterable[object]) -> Decision:
    """`gate`, raising instead of returning a no: put this in front of the code that builds a prompt."""
    d = gate(sheet, switch_on, markings)
    if not d.open:
        raise AiBlocked(d)
    return d
