"""The short written lists the engine uses to call two spellings the same word: abbreviations, synonyms, a few fixed phrases, and the words it ignores.

This is data a person owns. The defaults below are a **starting list of general engineering vocabulary, chosen by the engine's author, not measured on any real requirement set**. A project adds its
own with `reqin compare --vocab FILE` (JSON of the same shape); the SHA-256 of what was used is written into `compare.json`, so two runs can be told apart.

Every entry is a decision that two words mean the same thing everywhere in the requirements. Keep the list short and keep it boring: a wrong synonym merges requirements that differ, and nothing
downstream can undo that, whereas a missing synonym only leaves a pair for a person to look at.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT: dict[str, Any] = {
    # an abbreviation -> the word it stands for (applied to a whole word, case-insensitively)
    "abbreviations": {
        "msg": "message", "msgs": "messages", "cfg": "configuration", "config": "configuration", "info": "information", "cmd": "command", "cmds": "commands",
        "ctrl": "control", "sw": "software", "hw": "hardware", "app": "application", "apps": "applications", "spec": "specification", "specs": "specifications",
        "param": "parameter", "params": "parameters", "init": "initialise", "diag": "diagnostic", "comms": "communication", "ref": "reference", "qty": "quantity",
    },
    # words that mean the same: every word in a list is replaced by the first. Spelling variants (initialise/initialize) go here too.
    "synonyms": [
        ["display", "show"],
        ["transmit", "send"],
        ["initialise", "initialize", "start up", "startup"],
        ["activate", "enable"],
        ["deactivate", "disable"],
        ["acknowledge", "confirm"],
        ["generate", "produce"],
        ["record", "log"],
        ["retrieve", "fetch"],
        ["verify", "check"],
        ["utilise", "use", "utilize"],
        ["colour", "color"],
        ["behaviour", "behavior"],
        ["analyse", "analyze"],
        ["catalogue", "catalog"],
        ["metre", "meter"],
    ],
    # fixed phrases, written as the words they replace -> the words they become (applied before anything else; words are lower-case)
    "phrases": {
        "in order to": "to",
        "is able to": "can",
        "at a minimum": "at least",
        "prior to": "before",
        "as well as": "and",
    },
    # words that carry no meaning of their own here: left out of every comparison
    "ignore": ["the", "a", "an", "be", "is", "are", "been", "being", "that", "which", "also", "then"],
}


def stem(w: str) -> str:
    """A plain suffix stripper: not linguistics, only a way to give 'logs', 'logged' and 'logging' one key. It never makes two different words equal on purpose, and it only
    acts on words of four letters or more made of letters. It is applied to both sides of every comparison, so what matters is that it is the same function."""
    if len(w) < 4 or not w.isalpha():
        return w
    s = w
    if s.endswith("ies") and len(s) > 4:
        s = s[:-3] + "y"
    elif s.endswith("ied") and len(s) > 4:
        s = s[:-3] + "y"                                 # applied -> apply, verified -> verify
    elif s.endswith("s") and not s.endswith(("ss", "us", "is")):
        s = s[:-1]
    for suf in ("ing", "ed"):
        if s.endswith(suf) and len(s) - len(suf) >= 3:
            b = s[: -len(suf)]
            if len(b) >= 2 and b[-1] == b[-2] and b[-1] not in "aeioulsz":
                b = b[:-1]
            s = b
            break
    if s.endswith("e") and len(s) >= 5:
        s = s[:-1]
    return s


_WORD = re.compile(r"^[a-z0-9][a-z0-9 \-]*$")


def _check(v: Any) -> list[str]:
    bad: list[str] = []
    if not isinstance(v, dict) or set(v) - {"abbreviations", "synonyms", "phrases", "ignore"}:
        return ["the vocabulary must be an object with only abbreviations, synonyms, phrases and ignore"]
    ab, sy, ph, ig = v.get("abbreviations", {}), v.get("synonyms", []), v.get("phrases", {}), v.get("ignore", [])
    if not (isinstance(ab, dict) and all(isinstance(k, str) and isinstance(x, str) and _WORD.match(k) and _WORD.match(x) for k, x in ab.items())):
        bad.append("abbreviations must map a lower-case word to a lower-case word")
    if not (isinstance(sy, list) and all(isinstance(g, list) and len(g) >= 2 and all(isinstance(x, str) and _WORD.match(x) for x in g) for g in sy)):
        bad.append("synonyms must be a list of lists of at least two lower-case words")
    if not (isinstance(ph, dict) and all(isinstance(k, str) and isinstance(x, str) and _WORD.match(k) and _WORD.match(x) for k, x in ph.items())):
        bad.append("phrases must map lower-case words to lower-case words")
    if not (isinstance(ig, list) and all(isinstance(x, str) and _WORD.match(x) for x in ig)):
        bad.append("ignore must be a list of lower-case words")
    return bad


@dataclass(frozen=True)
class Vocabulary:
    abbreviations: dict[str, str]
    synonym_of: dict[str, str]         # stem of a word -> stem of the word it becomes
    phrases: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...]   # longest first
    ignore: frozenset[str]
    sha256: str
    source: str

    def canon(self, token: str) -> str | None:
        """The key a lower-case word is compared by, or None when the word is ignored."""
        if token in self.ignore:
            return None
        t = self.abbreviations.get(token, token)
        s = stem(t)
        return self.synonym_of.get(s, s)

    def apply_phrases(self, tokens: list[str]) -> list[str]:
        out: list[str] = []
        i = 0
        while i < len(tokens):
            for src, dst in self.phrases:
                if tuple(tokens[i:i + len(src)]) == src:
                    out.extend(dst)
                    i += len(src)
                    break
            else:
                out.append(tokens[i])
                i += 1
        return out


def build(v: dict[str, Any], source: str = "default") -> Vocabulary:
    bad = _check(v)
    if bad:
        raise ValueError("; ".join(bad))
    ab = {k: x for k, x in v.get("abbreviations", {}).items()}
    syn: dict[str, str] = {}
    for group in v.get("synonyms", []):
        head = stem(group[0].replace(" ", "")) if " " not in group[0] else None
        if head is None:
            raise ValueError(f"the first word of a synonym list must be one word: {group[0]!r}")
        for alt in group[1:]:
            if " " in alt:
                continue            # multi-word alternatives are phrases; see phrase handling below
            k = stem(alt)
            if k in syn and syn[k] != head:
                raise ValueError(f"{alt!r} is listed as a synonym of two different words")
            syn[k] = head
    phrases = {tuple(k.split()): tuple(x.split()) for k, x in v.get("phrases", {}).items()}
    for group in v.get("synonyms", []):
        for alt in group[1:]:
            if " " in alt:
                phrases[tuple(alt.split())] = (group[0],)
    ordered = tuple(sorted(phrases.items(), key=lambda kv: (-len(kv[0]), kv[0])))
    canonical = json.dumps({"abbreviations": ab, "synonyms": v.get("synonyms", []), "phrases": v.get("phrases", {}), "ignore": sorted(v.get("ignore", []))},
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return Vocabulary(ab, syn, ordered, frozenset(v.get("ignore", [])), hashlib.sha256(canonical.encode("utf-8")).hexdigest(), source)


def load(path: str | Path | None = None) -> Vocabulary:
    """The default vocabulary, or the one in a JSON file (which replaces the default completely; it is not merged)."""
    if path is None:
        return build(DEFAULT)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read the vocabulary {path}: {e}") from e
    return build(data, source=str(path))
