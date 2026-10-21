"""Numbers, units and comparators found in a requirement, with the position of each in the text. Standard library only; no model.

What a quantity is here: a value (or a range), the unit it is written in, how it is bounded ("at most", "within", "at least", "exactly", ...), an optional plus-or-minus tolerance, and where in the
text it is. Units of the same kind are converted to one base unit, so that "5 s" and "5000 ms" are the same quantity. Units the engine does not know are not guessed: a number with no known unit
after it is a bare number (a count, a version, an identifier fragment), and the word after it stays a word.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# surface form -> (dimension, factor to that dimension's base unit). The base units: millisecond, kilogram, metre, hertz, volt, ampere, watt, pascal, degree Celsius.
UNITS_CI: dict[str, tuple[str, float]] = {
    "msec": ("time", 1.0), "millisecond": ("time", 1.0), "milliseconds": ("time", 1.0),
    "s": ("time", 1000.0), "sec": ("time", 1000.0), "secs": ("time", 1000.0), "second": ("time", 1000.0), "seconds": ("time", 1000.0),
    "min": ("time", 60000.0), "mins": ("time", 60000.0), "minute": ("time", 60000.0), "minutes": ("time", 60000.0),
    "h": ("time", 3600000.0), "hr": ("time", 3600000.0), "hrs": ("time", 3600000.0), "hour": ("time", 3600000.0), "hours": ("time", 3600000.0),
    "day": ("time", 86400000.0), "days": ("time", 86400000.0),
    "kg": ("mass", 1.0), "kilogram": ("mass", 1.0), "kilograms": ("mass", 1.0), "g": ("mass", 0.001), "gram": ("mass", 0.001), "grams": ("mass", 0.001),
    "lb": ("mass", 0.45359237), "lbs": ("mass", 0.45359237), "pound": ("mass", 0.45359237), "pounds": ("mass", 0.45359237),
    "m": ("length", 1.0), "meter": ("length", 1.0), "meters": ("length", 1.0), "metre": ("length", 1.0), "metres": ("length", 1.0),
    "km": ("length", 1000.0), "cm": ("length", 0.01), "ft": ("length", 0.3048), "foot": ("length", 0.3048), "feet": ("length", 0.3048),
    "inch": ("length", 0.0254), "inches": ("length", 0.0254),
    "hz": ("frequency", 1.0), "khz": ("frequency", 1e3), "ghz": ("frequency", 1e9),
    "volt": ("voltage", 1.0), "volts": ("voltage", 1.0), "vdc": ("voltage_dc", 1.0), "vac": ("voltage_ac", 1.0),
    "amp": ("current", 1.0), "amps": ("current", 1.0), "ampere": ("current", 1.0), "amperes": ("current", 1.0),
    "watt": ("power", 1.0), "watts": ("power", 1.0),
    "pa": ("pressure", 1.0), "kpa": ("pressure", 1e3), "bar": ("pressure", 1e5), "psi": ("pressure", 6894.757293168),
    "%": ("percent", 1.0), "percent": ("percent", 1.0),
    "rad": ("angle", 57.29577951308232), "deg": ("angle", 1.0), "degree": ("angle", 1.0), "degrees": ("angle", 1.0),
    "l": ("volume", 1.0), "liter": ("volume", 1.0), "liters": ("volume", 1.0), "litre": ("volume", 1.0), "litres": ("volume", 1.0),
    "byte": ("bytes", 1.0), "bytes": ("bytes", 1.0), "bit": ("bits", 1.0), "bits": ("bits", 1.0), "kbit": ("kbit", 1.0), "mbit": ("mbit", 1.0),
}
# written case matters where a prefix is m (milli) or M (mega): mA/MA, mW/MW, mHz/MHz, mPa/MPa, mm/Mm, mg/Mg, ms/Ms, ml/Ml differ by a factor of a million or more, so those are listed here and
# matched exactly; a lower-case "mhz" or an upper-case "MS" is not guessed at (it stays a bare number and a word). A single capital letter is a unit only if it is listed here (V, A, W, B, L):
# "item 5 S" is not a time.
UNITS_CS: dict[str, tuple[str, float]] = {
    "ms": ("time", 1.0), "mm": ("length", 1e-3), "mg": ("mass", 1e-6), "ml": ("volume", 1e-3), "mbar": ("pressure", 100.0), "mHz": ("frequency", 1e-3), "mPa": ("pressure", 1e-3), "GPa": ("pressure", 1e9),
    "V": ("voltage", 1.0), "v": ("voltage", 1.0), "mV": ("voltage", 1e-3), "kV": ("voltage", 1e3),
    "A": ("current", 1.0), "mA": ("current", 1e-3),
    "W": ("power", 1.0), "mW": ("power", 1e-3), "kW": ("power", 1e3), "MW": ("power", 1e6),
    "B": ("bytes", 1.0), "kB": ("kbytes", 1.0), "KB": ("kbytes", 1.0), "MB": ("mbytes", 1.0), "GB": ("gbytes", 1.0), "TB": ("tbytes", 1.0),
    "Pa": ("pressure", 1.0), "kPa": ("pressure", 1e3), "MPa": ("pressure", 1e6), "Hz": ("frequency", 1.0), "kHz": ("frequency", 1e3), "MHz": ("frequency", 1e6), "GHz": ("frequency", 1e9),
    "L": ("volume", 1.0), "mL": ("volume", 1e-3),
    "°": ("angle", 1.0), "°C": ("temperature", 1.0), "degC": ("temperature", 1.0), "deg C": ("temperature", 1.0), "degrees C": ("temperature", 1.0), "degree C": ("temperature", 1.0),
    "degrees Celsius": ("temperature", 1.0), "degree Celsius": ("temperature", 1.0), "deg Celsius": ("temperature", 1.0),
}
# data sizes are not converted between each other: "1 GB" and "1000 MB" are left as different units, because nobody can tell here whether a thousand or 1024 was meant.
_FORMS = sorted({*UNITS_CI, *UNITS_CS}, key=lambda f: (-len(f), f))

MODIFIERS = r"(?:\s*(?:±|\+/-|\+-|plus or minus)\s*)"

# comparator phrases, as they are written right before a number. Longest first when matching.
COMPARATORS: dict[str, str] = {}
for _sym, _phrases in {
    "<=": ["at most", "no more than", "not more than", "no greater than", "not greater than", "not to exceed", "not exceed", "not exceeding", "no longer than", "not longer than",
           "no later than", "not later than", "no higher than", "not higher than", "no larger than", "not larger than", "no bigger than", "within", "maximum of", "a maximum of",
           "max of", "a max of", "maximum", "a maximum", "max", "not be greater than", "not be more than", "not be longer than", "not be higher than", "not be larger than",
           "less than or equal to", "equal to or less than", "at or below", "not over", "<=", "≤", "not above"],
    ">=": ["at least", "no less than", "not less than", "no fewer than", "not fewer than", "no lower than", "not lower than", "no shorter than", "not shorter than",
           "no earlier than", "not earlier than", "minimum of", "a minimum of", "min of", "a min of", "minimum", "a minimum", "min", "not be less than", "not be lower than",
           "not be shorter than", "greater than or equal to", "equal to or greater than", "at or above", "not below", "not under", ">=", "≥"],
    "<": ["less than", "fewer than", "lower than", "shorter than", "smaller than", "below", "under", "earlier than", "<"],
    ">": ["more than", "greater than", "higher than", "longer than", "larger than", "bigger than", "later than", "above", "in excess of", "exceeding", "exceeds", "exceed", ">"],
    "=": ["exactly", "precisely", "equal to", "equals", "equal", "="],
    # "carry up to 10 A" can mean a capacity (at least 10 A must work) or a limit (no more than 10 A): the direction is not read, so the quantity has no interval
    "up to": ["up to"],
}.items():
    for _p in _phrases:
        COMPARATORS[_p] = _sym
_CMP_RE = re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(p).replace(r"\ ", r"\s+") for p in sorted(COMPARATORS, key=lambda p: (-len(p), p))) + r")\s*$", re.I)
_POSTFIX = re.compile(r"\s+(?:or\s+(less|fewer|lower|shorter|smaller|more|greater|higher|longer|larger|bigger)|(maximum|minimum|max|min))\b", re.I)
_POST_SYM = {"less": "<=", "fewer": "<=", "lower": "<=", "shorter": "<=", "smaller": "<=", "maximum": "<=", "max": "<=",
             "more": ">=", "greater": ">=", "higher": ">=", "longer": ">=", "larger": ">=", "bigger": ">=", "minimum": ">=", "min": ">="}
# "under 3 conditions", "above 2 levels": a preposition in front of a bare number is not a bound. With a unit ("under 5 V") it is.
_PREPOSITIONS = frozenset({"under", "below", "above"})
_SLASH = re.compile(r"\s*/\s*")
_WINDOW = 80          # how far back from a number the comparator, range word and so on are looked for; a longer look only makes a long text slower
_LEAD_IN = re.compile(r"(?<![A-Za-z])in\s+$", re.I)
_RANGE_LEAD = re.compile(r"(?<![A-Za-z])(between|from)\s+$", re.I)
_PM_BEFORE = re.compile(r"(?:±|\+/-|\+-|plus or minus)\s*$", re.I)
_TOL = re.compile(r"\s*(?:±|\+/-|\+-|plus or minus)\s*", re.I)

# A number: 1,500 and 1 500 are fifteen hundred (groups of exactly three, first group not starting with 0), 0,5 and 12,34 have a decimal comma, 1.5 a decimal point. A number of more than 30
# digits is left as text. Bare numbers (no unit) are compared as written, so a version "2.10" is not "2.1".
_NUMBODY = r"(?:[1-9]\d{0,2}(?:,\d{3})+|[1-9]\d{0,2}(?: \d{3})+|\d+)(?:[.,]\d+)?(?!\d)"
_NUM = re.compile(rf"(?<![\w.\-−])(?:[-−](?=\d))?{_NUMBODY}|(?<![\w.])[-−](?=\d){_NUMBODY}")
_MAX_DIGITS = 30
_WORDNUMS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
             "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
             "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100}
_TENS = "twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety"
_ONES = "one|two|three|four|five|six|seven|eight|nine"
_WORDNUM = re.compile(rf"(?<![A-Za-z])(?:(?:{_TENS})[- ](?:{_ONES})|{'|'.join(sorted(_WORDNUMS, key=lambda w: -len(w)))})(?![A-Za-z])", re.I)
_NUMBER_AT = re.compile(rf"[-−]?{_NUMBODY}")
_GROUPED = re.compile(r"-?[1-9]\d{0,2}(?:,\d{3})+(?:\.\d+)?")


def _number_at(text: str, pos: int) -> tuple[int, float, bool, str] | None:
    m = _NUMBER_AT.match(text, pos)
    if m and _digits_ok(m.group(0)):
        t = _canon_text(m.group(0))
        return (m.end(), float(t), False, t)
    w = _WORDNUM.match(text, pos)
    if w:
        v = _wordnum(w.group(0))
        return (w.end(), v, True, str(int(v)))
    return None


def _digits_ok(s: str) -> bool:
    return sum(c.isdigit() for c in s) <= _MAX_DIGITS


def _canon_text(s: str) -> str:
    """The number as plain decimal text: separators resolved (1,500 -> 1500; 0,5 -> 0.5), sign as '-', nothing else changed ('2.10' stays '2.10')."""
    t = s.replace("−", "-").replace(" ", "")
    return t.replace(",", "") if _GROUPED.fullmatch(t) else t.replace(",", ".")


_RANGE_SEP = re.compile(r"\s*(to|and|-|–|—)\s*", re.I)      # 'and' only counts after 'between': "calibrated at 5 V and 10 V" is two values, not a range
# a number right after one of these words is part of a name or a reference, not a quantity: "ARINC 429", "Section 3", "step 2", "requirement 12"
_REF_WORDS = {"section", "sections", "table", "figure", "fig", "step", "clause", "paragraph", "para", "annex", "appendix", "requirement", "req", "item", "revision", "rev", "version", "ver",
              "issue", "part", "chapter", "page", "no", "number", "note", "level", "class", "type", "mode", "phase", "rfc", "iso", "iec", "ieee", "mil", "std", "do", "ecss"}


@dataclass
class Quantity:
    raw: str
    start: int
    end: int
    value: float | None          # the number as written (the low end of a range)
    value_hi: float | None       # the high end of a range
    unit: str                    # as written, "" for a bare number
    dimension: str               # "" for a bare number
    factor: float
    comparator: str              # "<=", ">=", "<", ">", "=", "range", "up to" (a bound whose direction is not read) or "" (not stated)
    tolerance: float | None      # in base units
    role: str = "main"           # or "condition"
    word_number: bool = False
    text: str = ""               # the number as plain decimal text ("1500", "0.5", "2.10"); the high end of a range is in text_hi
    text_hi: str = ""

    @property
    def directional(self) -> bool:
        """Whether the comparator says which side of the value is allowed ('up to' does not)."""
        return bool(self.comparator) and self.comparator != "up to"

    @property
    def exact(self) -> str:
        """The number as written, when a float cannot stand for it: a bare number (a version, a count, an identifier fragment: '2.10' is not '2.1') or more than 12 significant digits."""
        if not self.text:
            return ""
        sig = len(self.text.lstrip("-").replace(".", "").strip("0"))
        sig_hi = len(self.text_hi.lstrip("-").replace(".", "").strip("0"))
        if not self.dimension or sig > 12 or sig_hi > 12:
            return self.text + ("" if not self.text_hi else "~" + self.text_hi)
        return ""

    @property
    def key_dim(self) -> str:
        return self.dimension or ""

    @property
    def base(self) -> float | None:
        return None if self.value is None else self.value * self.factor

    @property
    def interval(self) -> tuple[float | None, float | None, bool, bool] | None:
        """The values this quantity allows, in base units: (low, high, low included, high included); None for 'unbounded on that side'. A number with no stated bound has no interval."""
        b = self.base
        if b is None or not self.comparator or self.comparator == "up to":
            return None
        c = self.comparator
        if c == "range":
            return (b, self.value_hi * self.factor, True, True)
        if c == "<=":
            return (None, b, False, True)
        if c == "<":
            return (None, b, False, False)
        if c == ">=":
            return (b, None, True, False)
        if c == ">":
            return (b, None, False, False)
        return (b, b, True, True)

    def canon(self) -> tuple:
        def r(x: float | None) -> float | None:
            return None if x is None else float(f"{x:.12g}")
        return (self.role, self.key_dim, self.comparator, r(self.base), r(None if self.value_hi is None else self.value_hi * self.factor), r(self.tolerance), self.exact)


def _wordnum(s: str) -> float:
    parts = re.split(r"[- ]", s.lower())
    return float(sum(_WORDNUMS[p] for p in parts))


def _simple_unit_at(text: str, pos: int) -> tuple[str, str, float, int] | None:
    for f in _FORMS:
        if not text.startswith(f, pos) and not text[pos:pos + len(f)].lower() == f.lower():
            continue
        got = text[pos:pos + len(f)]
        hit = UNITS_CS.get(got) or (UNITS_CI.get(got.lower()) if got.lower() in UNITS_CI else None)
        if hit is None:
            continue
        end = pos + len(f)
        if end < len(text) and (text[end].isalnum() or text[end] in "_"):
            continue
        if f.isalpha() and len(f) == 1 and got not in UNITS_CS and not (got.islower()):
            continue
        return (got, hit[0], hit[1], end)
    return None


def _unit_at(text: str, pos: int) -> tuple[str, str, float, int] | None:
    """A known unit starting at `pos` (spaces already skipped): (as written, dimension, factor, end). One division is joined ('m/s'); 'a/b/c' is read as 'a/b' and the rest left alone."""
    u = _simple_unit_at(text, pos)
    if u is None:
        return None
    name, dim, fac, end = u
    m = _SLASH.match(text, end)
    if m:
        more = _simple_unit_at(text, m.end())
        if more:
            return (text[pos:more[3]], f"{dim}/{more[1]}", fac / more[2], more[3])
    return u


def _before(text: str, pos: int) -> tuple[str, int]:
    """The few characters in front of `pos`, and where they start."""
    lo = max(0, pos - _WINDOW)
    return text[lo:pos], lo


def find_quantities(text: str) -> list[Quantity]:
    """Every quantity in `text`, left to right, each with its comparator, tolerance and character span. Positions index into `text`."""
    cands: list[tuple[int, int, float, bool, str]] = []
    for m in _NUM.finditer(text):
        if _digits_ok(m.group(0)):
            t = _canon_text(m.group(0))
            cands.append((m.start(), m.end(), float(t), False, t))
    for m in _WORDNUM.finditer(text):
        v = _wordnum(m.group(0))
        cands.append((m.start(), m.end(), v, True, str(int(v))))
    cands.sort()
    out: list[Quantity] = []
    used_to = 0
    i = 0
    while i < len(cands):
        s, e, v, is_word, vtext = cands[i]
        i += 1
        if s < used_to:
            continue
        # a unit right after the number?
        p = e
        while p < len(text) and text[p] == " ":
            p += 1
        u1 = _unit_at(text, p) if (p == e or p > e) else None
        win, woff = _before(text, s)
        lead = _RANGE_LEAD.search(win)
        # a range: 5 to 10 s, between 5 and 10 s, 5-10 s, 5 s to 10 s. 'and' only after 'between'.
        rng = None
        q = u1[3] if u1 else e
        sep = _RANGE_SEP.match(text, q)
        if sep and (sep.group(1).lower() != "and" or (lead is not None and lead.group(1).lower() == "between")):
            n2 = _number_at(text, sep.end())
            if n2:
                p2 = n2[0]
                while p2 < len(text) and text[p2] == " ":
                    p2 += 1
                u2 = _unit_at(text, p2)
                if u2 and (u1 is None or u1[1] == u2[1]) and n2[1] >= v:
                    rng = (n2, u2)
        if rng:
            (n2e, n2v, n2w, n2t), u2 = rng
            end = u2[3]
            start = s
            if lead:
                start = lead.start() + woff
            fac = u2[2]
            if u1 and u1[2] != u2[2]:
                v = v * u1[2] / u2[2]
            out.append(Quantity(text[start:end], start, end, v, n2v, u2[0], u2[1], fac, "range", None, word_number=is_word or n2w, text=vtext, text_hi=n2t))
            used_to = end
            continue
        if u1 is None:
            if is_word:
                continue                       # a number word with no unit ("one of the following") is just a word
            prev = re.search(r"([A-Za-z][A-Za-z0-9\-]*)\s*$", win)
            pw = prev.group(1) if prev else ""
            if pw and (pw.lower() in _REF_WORDS or (len(pw) >= 2 and pw.isupper()) or any(c.isdigit() for c in pw) or "-" in pw) and not _CMP_RE.search(win):
                continue                       # "ARINC 429", "Section 3": a name or a reference, not a quantity
            if e < len(text) and (text[e].isalpha() or text[e] in "_"):
                continue                       # "3rd", "5G"
            unit, dim, fac, end_u = "", "", 1.0, e
        else:
            unit, dim, fac, end_u = u1
        start, end = s, end_u
        cmp_ = ""
        pm = _PM_BEFORE.search(win)
        if pm:
            pm_at = pm.start() + woff
            bwin, boff = _before(text, pm_at)
        else:
            pm_at = -1
            bwin, boff = win, woff
        m = _CMP_RE.search(bwin)
        if m and u1 is None and re.sub(r"\s+", " ", m.group(1).lower()) in _PREPOSITIONS:
            m = None                           # "under 3 conditions": no bound on a bare number
        if pm:
            start = pm_at
            cmp_ = "<="                       # "within ±0.5 degrees": the size of the error is bounded
        if m:
            cmp_ = COMPARATORS[re.sub(r"\s+", " ", m.group(1).lower())]
            start = m.start(1) + boff
            lwin, loff = _before(text, start)
            lead_in = _LEAD_IN.search(lwin)       # "in no more than 5 s": the 'in' says nothing the bound does not
            if lead_in:
                start = lead_in.start() + loff
        elif u1 and not pm:
            lwin, loff = _before(text, start)
            lead_in = _LEAD_IN.search(lwin)       # "complete in 5 s": the same 'in' with no bound (a number with a unit only; 'in 5 places' stays words)
            if lead_in:
                start = lead_in.start() + loff
        tol = None
        mt = _TOL.match(text, end)
        if mt:
            n3 = _number_at(text, mt.end())
            if n3:
                p3 = n3[0]
                while p3 < len(text) and text[p3] == " ":
                    p3 += 1
                u3 = _unit_at(text, p3)
                if u3 and u3[1].split("_")[0] == dim.split("_")[0] and dim:
                    tol, end = n3[1] * u3[2], u3[3]
                elif not u3:
                    tol, end = n3[1] * fac, n3[0]
        if not cmp_:
            mp = _POSTFIX.match(text, end)
            if mp:
                cmp_ = _POST_SYM[(mp.group(1) or mp.group(2)).lower()]
                end = mp.end()
        out.append(Quantity(text[start:end], start, end, v, None, unit, dim, fac, cmp_, tol, word_number=is_word, text=vtext))
        used_to = end
    return out
