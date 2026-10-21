"""Colour arithmetic shared by the scripts in this folder: hex, OKLab, difference, contrast, hue names. Standard library only (numpy is used elsewhere, not here)."""
from __future__ import annotations

import math
import re

_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
_RGB = re.compile(r"^rgba?\(\s*([\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$")
_SRGB = re.compile(r"^color\(\s*srgb\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)(?:\s*/\s*([\d.]+%?))?\s*\)$")


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    m = _HEX.match(h.strip())
    if not m:
        raise ValueError(f"not a six-digit hex colour: {h!r}")
    v = m.group(1)
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def rgb_to_hex(r: float, g: float, b: float) -> str:
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(round(x)))) for x in (r, g, b))


def parse_css(value: str):
    """A computed CSS colour as (hex, alpha), or None when it is not one this script reads (a gradient, a keyword, a colour space it does not convert)."""
    v = value.strip().lower()
    if v in ("transparent",):
        return "#000000", 0.0
    m = _RGB.match(v)
    if m:
        a = m.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return rgb_to_hex(float(m.group(1)), float(m.group(2)), float(m.group(3))), alpha
    m = _SRGB.match(v)
    if m:
        a = m.group(4)
        alpha = 1.0 if a is None else (float(a[:-1]) / 100 if a.endswith("%") else float(a))
        return rgb_to_hex(*(float(m.group(i)) * 255 for i in (1, 2, 3))), alpha
    if _HEX.match(v):
        return "#" + v.lstrip("#").upper(), 1.0
    return None


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def oklab(h: str) -> tuple[float, float, float]:
    r, g, b = (_lin(x) for x in hex_to_rgb(h))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def delta_e(a: str, b: str) -> float:
    """Distance in OKLab times 100. Under about 2 two colours look the same; under 6 they are the same colour for a design system's purposes."""
    x, y = oklab(a), oklab(b)
    return 100 * math.sqrt(sum((p - q) ** 2 for p, q in zip(x, y)))


def lch(h: str) -> tuple[float, float, float]:
    L, a, b = oklab(h)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def luminance(h: str) -> float:
    r, g, b = (_lin(x) for x in hex_to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def composite(fg: str, alpha: float, bg: str) -> str:
    f, b = hex_to_rgb(fg), hex_to_rgb(bg)
    return rgb_to_hex(*(alpha * x + (1 - alpha) * y for x, y in zip(f, b)))


# OKLCH hue angles of the sRGB primaries and secondaries, to name a hue in words.
_HUES = [(29, "red"), (55, "orange"), (85, "amber"), (110, "yellow"), (145, "green"), (185, "teal"), (215, "cyan"), (265, "blue"), (295, "violet"), (330, "magenta")]


def is_neutral(h: str) -> bool:
    """Grey, or a blue-grey ('slate') as interface greys often are. A pale red or green tint is not neutral, so its status can still be read."""
    _, C, H = lch(h)
    return C < 0.02 or (C < 0.035 and 215 <= H <= 275)


def hue_name(h: str) -> str:
    if is_neutral(h):
        return "neutral"
    H = lch(h)[2]
    return min(_HUES, key=lambda p: min(abs(H - p[0]), 360 - abs(H - p[0])))[1]


# the four meanings an interface gives colour; anything else is "other"
STATUS_OF_HUE = {"red": "danger", "orange": "warn", "amber": "warn", "yellow": "warn", "green": "ok", "blue": "info", "cyan": "info"}


def status_group(h: str) -> str:
    return STATUS_OF_HUE.get(hue_name(h), "other")
