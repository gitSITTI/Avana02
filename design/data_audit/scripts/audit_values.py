"""The pure parts of the audit: finding the values on a screen, finding them again in what the page loaded, inventing replacement values, and working out which numbers are counts of
the data. No browser, no network, standard library only, so every rule here is tested without one.

A *value* here is a number, an ID, a date or time, or a sentence that looks like a requirement. Plain words (labels, headings, button names) are not values: they are the app's own
words, and the audit does not ask where they came from.
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import Counter

# ------------------------------------------------------------------------------------------------ text
ID_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,9}(?:[-_][A-Z][A-Z0-9]{1,9})*[-_]\d{1,8}\b")        # PMP-0012, SYS_REQ_7: capitals, then a number. Not pmp-0012, not R-4.
KEY_ID_RE = re.compile(r"^(?:[A-Za-z][A-Za-z0-9]{0,9}(?:[-_][A-Za-z][A-Za-z0-9]{0,9})*[-_]\d{1,8}|\d{2,})$")      # a dictionary key that is an ID or a number: records held by ID
DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)?\b")
TIME_RE = re.compile(r"(?<![\d:])\d{1,2}:\d{2}(?::\d{2})?(?![\d:])")
NUM_RE = re.compile(r"(?<![\w.\-])\d{1,3}(?:[,  ]\d{3})+(?:\.\d+)?%?|(?<![\w.\-])\d+(?:\.\d+)?%?")
SHALL_RE = re.compile(r"\b(shall|must|should)\b", re.I)
STATEMENT_MIN = 24                                             # a sentence with shall, must or should is a statement from this length
ISO_LIKE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?)?$")


def norm(s) -> str:
    """Lower case, one space between words, compatibility characters folded (so a non-breaking space or a curly quote does not make two equal texts differ)."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", str(s)).casefold()).strip()


def canon_number(raw: str) -> str:
    """'1,248' -> '1248', '7.50' -> '7.5', '84%' -> '84%'. The same number written in different ways gives the same text."""
    s = str(raw).replace(",", "").replace(" ", "").replace(" ", "").strip()
    pct = s.endswith("%")
    s = s.rstrip("%")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s + ("%" if pct else "")


def atoms(text: str) -> list:
    """The values in a piece of text: [{'kind': 'date'|'id'|'time'|'number'|'statement', 'value': ..., 'raw': ...}]. Small numbers (under 10, and years) are page numbers and
    list numbers, not data, and are left out; so is anything that is plain words."""
    out, rest = [], text or ""
    for kind, rx in (("date", DATE_RE), ("id", ID_RE), ("time", TIME_RE)):
        for m in rx.finditer(rest):
            out.append({"kind": kind, "value": norm(m.group(0)) if kind != "id" else m.group(0).lower(), "raw": m.group(0)})
        rest = rx.sub(" ", rest)
    for m in NUM_RE.finditer(rest):
        raw = m.group(0)
        c = canon_number(raw)
        digits = c.rstrip("%")
        if not c.endswith("%") and "." not in digits and (len(digits) < 2 or (len(digits) == 4 and 1900 <= int(digits) <= 2100 and "," not in raw)):
            continue
        out.append({"kind": "number", "value": c, "raw": raw})
    if len(text or "") >= STATEMENT_MIN and SHALL_RE.search(text):
        out.append({"kind": "statement", "value": norm(text), "raw": text})
    return out


SHORT_TEXT = 24
COUNT_HOOK = re.compile(r"count|total|sum|metric|score|number|percent|share", re.I)


def item_atoms(item: dict) -> list:
    """The values of one thing on the screen. A single digit is a value only where the page marks a number as data (a data-testid, an id or a class with count, total, sum, metric,
    score, number, percent or share in it), because elsewhere it is a page or list number."""
    got = atoms(item.get("text", ""))
    t = (item.get("text") or "").strip()
    if not got and COUNT_HOOK.search("%s %s" % (item.get("testid") or "", item.get("hook") or "")) and re.fullmatch(r"\d+(?:\.\d+)?%?", t) and canon_number(t).rstrip("%") != "0":
        got = [{"kind": "number", "value": canon_number(t), "raw": t}]
    return got


def is_data_like(text: str) -> bool:
    return bool(atoms(text))


STATE_WORDS = re.compile(r"\b(no (data|results|requirements|records|items)|nothing (to show|here|loaded|yet)|empty|unavailable|could not|couldn't|cannot|can't|failed|failure|error|offline|"
                         r"not connected|disconnected|unable|try again|retry|no connection|sample|demo|cached|out of date|stale|last (updated|synced|refreshed)|as of)\b", re.I)


def says_something_about_state(text: str) -> bool:
    """Whether a screen's words give any sign that data is missing, old or not live. A loose test on purpose: it asks only whether the screen says anything at all."""
    return bool(STATE_WORDS.search(text or ""))


# ------------------------------------------------------------------------------------------------ what the page loaded
def parse_json(body: str):
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return None


def walk(obj, path="$"):
    """Every value of a JSON document with where it is: (path, value). Lists are written path[]."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from walk(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v, path + "[]")
    else:
        yield path, obj


LEAD_WORDS, TRAIL_WORDS = 4, 6                                  # words a screen may add before a sentence (an ID, a label) and after it (an owner, a status)


def statement_in(value: str, haystack: str) -> bool:
    """A sentence is found when all of it is in the text, or all of it less a few words in front (an ID, a label) and a few at the end (an owner, a status, a cut-off '…').
    A word or a number changed in the middle is not found: 'below 10 percent' is not 'below 15 percent'."""
    v = value.rstrip(". \u2026")
    if v in haystack:
        return True
    words = v.split(" ")
    n = len(words)
    need = max(5, -(-n * 6 // 10))                              # at least 6 words in 10 must be left
    lead, trail = LEAD_WORDS, TRAIL_WORDS
    while n - lead - trail < need and (lead or trail):
        if trail:
            trail -= 1
        else:
            lead -= 1
    if n - lead - trail < need or (lead == 0 and trail == 0):
        return False
    least = " ".join(words[lead:n - trail]).strip(" .,;:\u2026")      # what is left when the most is taken off: every closer match holds it too
    if len(least) < 20 or least not in haystack:
        return False
    for t in range(0, trail + 1):
        for l in range(0, lead + 1):
            core = " ".join(words[l:n - t]).strip(" .,;:\u2026")
            if n - l - t >= need and len(core) >= 20 and core in haystack:
                return True
    return False


def dict_keys(obj):
    """Every key of every object in a JSON document that is an ID or a number (records held by ID: {"PMP-0012": {...}})."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and KEY_ID_RE.match(k):
                yield k
            yield from dict_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from dict_keys(v)


def plain(s: str) -> str:
    """Text as a page shows it when the data holds markup: tags dropped, entities read."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", s))).strip()


class Loaded:
    """What the page loaded, ready to be searched: every text and number in the data responses (as JSON values), the plain text of other text responses, and the page's own code."""

    def __init__(self, responses: list):
        strings, numbers, blob, code = [], set(), [], []
        self.derived: dict = {}
        self.sources: dict = {}                                # normalised string -> first response url that holds it
        for r in responses:
            body = r.get("body") or ""
            if r.get("type") in ("document", "script", "stylesheet"):
                code.append(norm(body))
                if r.get("type") == "document":
                    j = None
                else:
                    continue
            j = parse_json(body) if r.get("json") else None
            if j is None:
                if r.get("type") not in ("document", "script", "stylesheet") and (r.get("content_type", "").startswith("text/") or "csv" in r.get("content_type", "")):
                    blob.append(norm(body))
                    for m in NUM_RE.finditer(body):
                        numbers.add(canon_number(m.group(0)))
                continue
            for path, v in walk(j):
                if isinstance(v, str):
                    for form in ((v, plain(v)) if ("<" in v or "&" in v) else (v,)):
                        n = norm(form)
                        if n:
                            strings.append(n)
                            self.sources.setdefault(n, r.get("url", ""))
                    if len(v) <= SHORT_TEXT:                           # a number in a short text ("12 kg", "84%") is a number of the data; one inside a sentence is part of the sentence
                        for m in NUM_RE.finditer(v):
                            numbers.add(canon_number(m.group(0)))
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    numbers.add(canon_number(repr(v) if isinstance(v, float) else str(v)))
            for k in dict_keys(j):
                strings.append(norm(k))
                self.sources.setdefault(norm(k), r.get("url", ""))
                if k.isdigit():
                    numbers.add(canon_number(k))
            self._derive(j, r.get("url", ""))
        self.strings = set(strings)
        self.blob = "\x00".join(strings + blob)
        self.numbers = numbers
        self.code = "\x00".join(code)

    # -- numbers that are counts of the data
    def _derive(self, j, url: str, path="$"):
        if isinstance(j, dict):
            for k, v in j.items():
                self._derive(v, url, "%s.%s" % (path, k))
        elif isinstance(j, list) and len(j) <= 100000:
            self._fact(len(j), "the number of items in `%s`" % path)
            dicts = [x for x in j if isinstance(x, dict)]
            if len(dicts) >= 2:
                keys = {k for d in dicts for k in d}
                for k in sorted(keys):
                    vals = [d.get(k) for d in dicts if k in d]
                    nums = [v for v in vals if isinstance(v, (int, float)) and not isinstance(v, bool)]
                    if len(nums) == len(vals) and nums:
                        self._fact(sum(nums), "the sum of `%s` over the items in `%s`" % (k, path), "sum")
                    strs = [v for v in vals if isinstance(v, str)]
                    if len(strs) == len(vals) and strs:
                        self._fact(len(set(strs)), "the number of different `%s` values in `%s`" % (k, path))
                        for val, n in (Counter(strs).items() if len(set(strs)) <= 30 else ()):
                            if len(val) <= 40:
                                self._fact(n, "the number of items in `%s` whose `%s` is %r" % (path, k, val))
                                if len(j):
                                    self._fact(round(100 * n / len(j)), "the share (%%) of items in `%s` whose `%s` is %r" % (path, k, val), "count", pct=True)
            for x in j[:200]:
                self._derive(x, url, path + "[]")

    def _fact(self, n, label: str, kind: str = "count", pct: bool = False):
        """Remember that a number can be explained: kind is 'count' (does not change when the values of the records change) or 'sum' (does)."""
        c = canon_number(repr(n) if isinstance(n, float) else str(n))
        info = {"label": label, "kind": kind}
        self.derived.setdefault(c + ("%" if pct else ""), info)
        if pct:
            self.derived.setdefault(c, info)

    # -- looking a value up
    def has_in_data(self, atom: dict) -> bool:
        if atom["kind"] == "number":
            return atom["value"] in self.numbers
        if atom["kind"] == "statement":
            return statement_in(atom["value"], self.blob)
        return atom["value"] in self.blob

    def has_in_code(self, atom: dict) -> bool:
        if atom["kind"] == "number":
            c = atom["value"].rstrip("%")
            grouped = "{:,}".format(int(c)) if re.fullmatch(r"\d+", c) else c
            for form in {c, grouped}:
                if re.search(r"(?<![\w.,])" + re.escape(form) + r"(?![\w]|,\d{3}|\.\d)", self.code):
                    return True
            return False
        if atom["kind"] == "statement":
            return statement_in(atom["value"], self.code)
        return atom["value"] in self.code

    def explain(self, atom: dict) -> dict | None:
        """{'label': ..., 'kind': 'count'|'sum'} when the number is one the data gives by counting or adding, else None."""
        return self.derived.get(atom["value"]) if atom["kind"] == "number" else None


# ------------------------------------------------------------------------------------------------ inventing values
class Canary:
    """Replacement values for a data response. The same text always becomes the same invented text, so the screen's joins and filters still hold.
    A text is replaced by CANARY-<FIELD>-<n>, where FIELD is the name of the field it was in, so a screen that shows the wrong field in a column can be caught."""

    def __init__(self, strings: bool = True, numbers: bool = True, keep_dates: bool = True):
        self.strings, self.numbers, self.keep_dates = strings, numbers, keep_dates
        self.map: dict = {}
        self.nmap: dict = {}
        self.fields: dict = {}                                 # token -> the field names it stood for

    @staticmethod
    def tag(key: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", str(key).upper())[:10] or "X"

    def string(self, s: str, key: str = "") -> str:
        if not self.strings or not s.strip() or re.match(r"^(https?:|/|#)", s) or (self.keep_dates and ISO_LIKE_RE.match(s.strip())):
            return s
        if s not in self.map:
            self.map[s] = "CANARY-%s-%d" % (self.tag(key), len(self.map) + 1)
        tok = self.map[s]
        self.fields.setdefault(tok, [])
        if key and key not in self.fields[tok]:
            self.fields[tok].append(key)
        return tok

    def number(self, n):
        if not self.numbers:
            return n
        if n not in self.nmap:
            self.nmap[n] = n + 7000000 + len(self.nmap) * 11
        return self.nmap[n]

    def apply(self, obj, key: str = ""):
        if isinstance(obj, dict):
            return {(self.string(k, "KEY") if isinstance(k, str) and KEY_ID_RE.match(k) else k): self.apply(v, k) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.apply(v, key) for v in obj]
        if isinstance(obj, bool) or obj is None:
            return obj
        if isinstance(obj, str):
            return self.string(obj, key)
        if isinstance(obj, (int, float)):
            return self.number(obj)
        return obj


def emptied(obj):
    """The same document with nothing in it: lists empty, numbers 0, texts empty, keys kept. What a source with no data would plausibly send."""
    if isinstance(obj, dict):
        return {k: emptied(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return []
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, str):
        return ""
    if isinstance(obj, (int, float)):
        return 0
    return obj


def texts_of(items: list) -> Counter:
    """How many times each (normalised) text is on the screen."""
    return Counter(norm(i["text"]) for i in items if norm(i.get("text", "")))
