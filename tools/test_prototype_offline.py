"""The prototype page must work with no network and must not call any other site: SECURITY.md says so, and these tests keep it true.
It does not run the page; it reads the text of the built page and the folder of font files."""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGE = REPO / "prototype" / "project" / "Main.dc.html"
FONTS = REPO / "prototype" / "project" / "fonts"


def test_the_page_names_no_other_site():
    text = PAGE.read_text(encoding="utf-8")
    found = sorted(set(re.findall(r"https?://[^\s\"'<>)]+", text)))
    assert found == [], f"the prototype page mentions other sites; it must work offline and call no one: {found}"


def test_every_font_file_the_page_asks_for_exists_and_no_font_file_is_unused():
    text = PAGE.read_text(encoding="utf-8")
    asked = set(re.findall(r"url\(\./fonts/([\w.-]+\.woff2)\)", text))
    assert asked, "the page asks for no bundled font; did the @font-face rules go?"
    on_disk = {f.name for f in FONTS.glob("*.woff2")}
    assert asked <= on_disk, f"the page asks for font files that are not in prototype/project/fonts/: {sorted(asked - on_disk)}"
    assert on_disk <= asked, f"font files that the page never uses (remove them or use them): {sorted(on_disk - asked)}"
