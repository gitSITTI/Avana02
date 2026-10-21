"""Deterministic text normalisation and slot extraction. No AI. Ported from the prototype's logic."""
from __future__ import annotations

import hashlib
import html
import re

from .model import Slots, nfkc

# Markup is a tag with a known HTML/XHTML name and name="value" attributes, a comment, a processing instruction or a CDATA mark. Anything else between < and > is text: "<5 V and the output shall be >3 V"
# and "if a<b and c>d" must survive, and a loose "<[^>]+>" removes everything from the first < to the next >.
_TAGNAME = (r"(?:[A-Za-z][\w.-]*:)?(?:a|abbr|address|b|big|blockquote|body|br|caption|center|cite|code|col|colgroup|dd|del|div|dl|dt|em|font|h[1-6]|head|hr|html|i|img|ins|li|object|ol|p|param|pre|q|"
            r"s|small|span|strike|strong|sub|sup|table|tbody|td|tfoot|th|thead|title|tr|tt|u|ul|var|xhtml)")
_TAG = re.compile(rf"</?{_TAGNAME}(?![\w-])(?:\s+[\w:.-]+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^\s\"'<>]+))*\s*/?>|<!--.*?-->|<\?[^>]*\?>|<!\[CDATA\[|\]\]>", re.I | re.S)
_WS = re.compile(r"\s+")
_MODAL = re.compile(r"\b(shall|should|will|may|must)\b", re.I)
_NEG = re.compile(r"\b(shall|should|will|must|may)\s+not\b|\bnever\b|\bwithout\b", re.I)
_UNIT = (r"milliseconds?|ms|seconds?|secs?|s|minutes?|min|hours?|hrs?|h|days?|hz|khz|mhz|ghz|percent|%|"
         r"kg|kilograms?|g|grams?|meters?|metres?|m|km|mm|cm|degrees?|deg|c|volts?|vdc|v|amps?|a|watts?|w|"
         r"fault\s+records?|records?|bytes?|kb|mb|gb")
_QTY = re.compile(rf"(\d[\d,]*(?:\.\d+)?)\s*({_UNIT})\b", re.I)
_CMP = [
    (re.compile(r"(at least|no less than|not less than|minimum of|>=|≥)\s*$", re.I), ">="),
    (re.compile(r"(at most|no more than|not more than|not exceed|maximum of|<=|≤|up to)\s*$", re.I), "<="),
    (re.compile(r"(less than|below|under|<)\s*$", re.I), "<"),
    (re.compile(r"(more than|greater than|above|over|>)\s*$", re.I), ">"),
    (re.compile(r"(within|in)\s*$", re.I), "<="),
    (re.compile(r"(exactly|equal to|=)\s*$", re.I), "="),
]
# SI-ish canonical units for the few dimensions we convert. Anything else is kept as written.
_TO_BASE = {
    "ms": ("time_ms", 1), "millisecond": ("time_ms", 1), "milliseconds": ("time_ms", 1),
    "s": ("time_ms", 1000), "sec": ("time_ms", 1000), "secs": ("time_ms", 1000), "second": ("time_ms", 1000), "seconds": ("time_ms", 1000),
    "min": ("time_ms", 60000), "minute": ("time_ms", 60000), "minutes": ("time_ms", 60000),
    "h": ("time_ms", 3600000), "hr": ("time_ms", 3600000), "hrs": ("time_ms", 3600000), "hour": ("time_ms", 3600000), "hours": ("time_ms", 3600000),
    "kg": ("mass_kg", 1), "kilogram": ("mass_kg", 1), "kilograms": ("mass_kg", 1), "g": ("mass_kg", 0.001), "gram": ("mass_kg", 0.001), "grams": ("mass_kg", 0.001),
    "m": ("length_m", 1), "meter": ("length_m", 1), "meters": ("length_m", 1), "metre": ("length_m", 1), "metres": ("length_m", 1),
    "km": ("length_m", 1000), "mm": ("length_m", 0.001), "cm": ("length_m", 0.01),
    "hz": ("freq_hz", 1), "khz": ("freq_hz", 1e3), "mhz": ("freq_hz", 1e6), "ghz": ("freq_hz", 1e9),
}


def strip_markup(s: str) -> str:
    """Remove HTML/XHTML tags and entities (ReqIF XHTML, Word-to-HTML output). Keeps text order."""
    s = re.sub(r"</(p|div|li|br)\s*>|<br\s*/?>", " ", s, flags=re.I)
    return html.unescape(_TAG.sub("", s))


def normalise_text(s: str) -> str:
    """NFKC, collapse whitespace, unify dashes and quotes. Case is kept: 'shall' vs 'Shall' is harmless
    but acronyms and part numbers are case-sensitive."""
    s = nfkc(strip_markup(s))
    s = s.replace("–", "-").replace("—", "-").replace("‘", "'").replace("’", "'")
    s = s.replace("“", '"').replace("”", '"')
    return _WS.sub(" ", s).strip()


def extract_slots(text: str) -> Slots:
    sl = Slots()
    m = _MODAL.search(text)
    sl.modal = m.group(1).lower() if m else ""
    sl.negated = bool(_NEG.search(text))
    for q in _QTY.finditer(text):
        raw_n, unit = q.group(1), q.group(2).lower()
        n = float(raw_n.replace(",", ""))
        before = text[max(0, q.start() - 24): q.start()]
        cmp_ = ""
        for rx, sym in _CMP:
            if rx.search(before):
                cmp_ = sym
                break
        base = _TO_BASE.get(unit)
        sl.quantities.append({
            "raw": q.group(0), "value": n, "unit": unit, "comparator": cmp_,
            "dimension": base[0] if base else "",
            "base_value": n * base[1] if base else None,
        })
    return sl


def fingerprint(norm_text: str, slots: Slots) -> str:
    """Changes when meaning-bearing content changes, not when markup or whitespace changes."""
    payload = norm_text + "\x1e" + slots.modal + str(slots.negated) + "\x1e" + "|".join(
        f"{q['comparator']}{q['value']}{q['unit']}" for q in slots.quantities)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
