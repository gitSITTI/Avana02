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
    # words that mean the same: every word in a list is replaced by the first. The default list holds only spelling variants of one word, where the two spellings can never be two meanings.
    # Words that merely overlap in meaning (display/show, record/log, enable/activate, ...) are NOT here: they merge requirements that differ, and nothing downstream can undo that. A project that
    # wants them adds them in its own vocabulary file; `STARTER_SYNONYMS` below is a list to copy from, not a default.
    "synonyms": [
        ["initialise", "initialize"],
        ["utilise", "utilize"],
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
    },
    # words that carry no meaning of their own here: left out of every comparison. 'is', 'are', 'be', 'also' and 'then' are NOT in this list: "shall be open" is not "shall open",
    # "shall not also open" is not "shall not open", and "stop when A and then B" is not "stop when B and then A".
    "ignore": ["the", "a", "an", "that", "which"],
    # whether 'pump' and 'pumps' are one word. Off: "monitor the pump" and "monitor the pumps" are different requirements (one pump, or every pump), so they are not merged.
    "fold_plurals": False,
}

# Not used unless a project asks for it (`reqin compare --vocab FILE` with these entries in FILE). Each pair is a decision that the two words mean the same thing in that project's requirements:
# 'record' and 'log' are also nouns, 'check' is also a noun, 'enable' is not always 'activate'. Written down so that a project can copy what fits and drop what does not.
STARTER_SYNONYMS: list[list[str]] = [
    ["display", "show"], ["transmit", "send"], ["activate", "enable"], ["deactivate", "disable"], ["acknowledge", "confirm"], ["generate", "produce"],
    ["record", "log"], ["retrieve", "fetch"], ["verify", "check"], ["utilise", "use"], ["initialise", "start up", "startup"],
]


def starter() -> dict[str, Any]:
    """The default vocabulary plus `STARTER_SYNONYMS`, as a dictionary a project can save as its own file and edit."""
    v = json.loads(json.dumps(DEFAULT))
    heads = {g[0]: g for g in v["synonyms"]}
    for g in STARTER_SYNONYMS:
        if g[0] in heads:
            heads[g[0]].extend(w for w in g[1:] if w not in heads[g[0]])
        else:
            v["synonyms"].append(list(g))
    return v


def _cons(s: str, i: int) -> bool:
    ch = s[i]
    if ch in "aeiou":
        return False
    if ch == "y":
        return i == 0 or not _cons(s, i - 1)
    return True


def _measure(s: str) -> int:
    """How many vowel-run then consonant-run pairs the word has (Porter's m): 'tr' 0, 'tap' 1, 'monitor' 3."""
    shape = "".join("c" if _cons(s, i) else "v" for i in range(len(s)))
    return shape.count("vc") if shape else 0


def _cvc(s: str) -> bool:
    """Ends consonant, vowel, consonant, the last not w, x or y: 'tap', 'plan', 'clos'."""
    return len(s) >= 3 and _cons(s, len(s) - 3) and not _cons(s, len(s) - 2) and _cons(s, len(s) - 1) and s[-1] not in "wxy"


def stem(w: str, plurals: bool = False) -> str:
    """A small suffix stripper: not linguistics, only a way to give 'logged' and 'logging' one key. It follows the first steps of the Porter stemmer for -ed and -ing, so that the e that
    the suffix hid comes back where it belongs ('taped' is 'tape', 'tapped' is 'tap'; 'plane' and 'plan' stay apart) and the final e is dropped only the way that stemmer drops it. It acts only on
    words of four letters or more written with the letters a to z. 'pumps' is 'pump' only when `plurals` is on (the vocabulary option fold_plurals); otherwise a plural is a different word.
    It is applied to both sides of every comparison, so what matters is that it is the same function."""
    if len(w) < 4 or not (w.isascii() and w.isalpha()):
        return w
    s = w
    if s.endswith("ied") and len(s) > 4:
        s = s[:-3] + "y"                                 # applied -> apply, verified -> verify
    elif plurals and s.endswith("ies") and len(s) > 4:
        s = s[:-3] + "y"
    elif plurals and s.endswith("sses"):
        s = s[:-2]
    elif plurals and s.endswith("s") and not s.endswith(("ss", "us", "is")):
        s = s[:-1]
    if s.endswith("eed"):
        if len(s) > 4 and _measure(s[:-3]) > 0:
            s = s[:-1]                                   # agreed -> agree
    else:
        for suf in ("ed", "ing"):
            if s.endswith(suf) and any(not _cons(s[:-len(suf)], i) for i in range(len(s) - len(suf))):
                b = s[: -len(suf)]
                if b.endswith(("at", "bl", "iz")):
                    b += "e"
                elif len(b) >= 2 and b[-1] == b[-2] and _cons(b, len(b) - 1) and b[-1] not in "lsz":
                    b = b[:-1]                           # tapped -> tap
                elif _measure(b) == 1 and (_cvc(b) or len(b) <= 2):
                    b += "e"                             # taped -> tape, used -> use
                s = b
                break
    if s.endswith("e") and len(s) >= 4:
        b = s[:-1]
        m = _measure(b)
        if m > 1 or (m == 1 and not _cvc(b)):
            s = b
    return s


_WORD = re.compile(r"^[a-z0-9][a-z0-9 \-]*$")


def _check(v: Any) -> list[str]:
    bad: list[str] = []
    if not isinstance(v, dict) or set(v) - {"abbreviations", "synonyms", "phrases", "ignore", "fold_plurals"}:
        return ["the vocabulary must be an object with only abbreviations, synonyms, phrases, ignore and fold_plurals"]
    ab, sy, ph, ig = v.get("abbreviations", {}), v.get("synonyms", []), v.get("phrases", {}), v.get("ignore", [])
    if not isinstance(v.get("fold_plurals", False), bool):
        bad.append("fold_plurals must be true or false")
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
    fold_plurals: bool = False

    def canon(self, token: str) -> str | None:
        """The key a lower-case word is compared by, or None when the word is ignored."""
        if token in self.ignore:
            return None
        t = self.abbreviations.get(token, token)
        s = stem(t, self.fold_plurals)
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
    fold = bool(v.get("fold_plurals", False))
    syn: dict[str, str] = {}
    for group in v.get("synonyms", []):
        head = stem(group[0].replace(" ", ""), fold) if " " not in group[0] else None
        if head is None:
            raise ValueError(f"the first word of a synonym list must be one word: {group[0]!r}")
        for alt in group[1:]:
            if " " in alt:
                continue            # multi-word alternatives are phrases; see phrase handling below
            k = stem(alt, fold)
            if k in syn and syn[k] != head:
                raise ValueError(f"{alt!r} is listed as a synonym of two different words")
            syn[k] = head
    phrases = {tuple(k.split()): tuple(x.split()) for k, x in v.get("phrases", {}).items()}
    for group in v.get("synonyms", []):
        for alt in group[1:]:
            if " " in alt:
                phrases[tuple(alt.split())] = (group[0],)
    ordered = tuple(sorted(phrases.items(), key=lambda kv: (-len(kv[0]), kv[0])))
    canonical = json.dumps({"abbreviations": ab, "synonyms": v.get("synonyms", []), "phrases": v.get("phrases", {}), "ignore": sorted(v.get("ignore", [])), "fold_plurals": fold},
                           sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return Vocabulary(ab, syn, ordered, frozenset(v.get("ignore", [])), hashlib.sha256(canonical.encode("utf-8")).hexdigest(), source, fold)


def load(path: str | Path | None = None) -> Vocabulary:
    """The default vocabulary, or the one in a JSON file (which replaces the default completely; it is not merged)."""
    if path is None:
        return build(DEFAULT)
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ValueError(f"cannot read the vocabulary {path}: {e}") from e
    return build(data, source=str(path))
