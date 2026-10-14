"""Every relative link or image in the Markdown files must point at a file that exists (a renamed repository must not break them either)."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".cache", "node_modules", ".pytest_cache", "__pycache__", "build", "dist", ".venv", "venv"}
MD_LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
HTML_REF = re.compile(r"""(?:src|href)\s*=\s*["']([^"']+)["']""", re.I)
FENCE = re.compile(r"^(```|~~~).*?^\1[^\n]*$", re.S | re.M)


def markdown_files():
    return sorted(p for p in REPO.rglob("*.md") if not (set(p.relative_to(REPO).parts) & SKIP_DIRS))


def targets(text: str):
    text = FENCE.sub("", text)                       # code samples may contain link-shaped text
    text = re.sub(r"`[^`\n]*`", "", text)           # and so may inline code
    for m in list(MD_LINK.finditer(text)) + list(HTML_REF.finditer(text)):
        yield m.group(1)


def broken_links():
    bad = []
    for md in markdown_files():
        for t in targets(md.read_text(encoding="utf-8", errors="replace")):
            if re.match(r"^(https?:|mailto:|tel:|#|data:)", t):
                continue
            path = unquote(t.split("#", 1)[0].split("?", 1)[0])
            if not path:
                continue
            if t.startswith("/"):
                bad.append(f"{md.relative_to(REPO)}: absolute path {t!r} breaks when the repository is renamed or moved")
            elif not (md.parent / path).exists():
                bad.append(f"{md.relative_to(REPO)}: {t!r} does not exist")
    return bad


def test_every_relative_link_and_image_in_the_markdown_files_resolves():
    assert markdown_files(), "no Markdown files found"
    assert broken_links() == []


def test_the_link_checker_can_fail(tmp_path, monkeypatch):
    import sys
    me = sys.modules[__name__]
    (tmp_path / "a.md").write_text("[ok](a.md) [gone](missing.md) ![img](nope.png) <img src=\"also-missing.png\"> [abs](/docs/x.md)\n```\n[inside code](skipped.md)\n```\n")
    monkeypatch.setattr(me, "REPO", tmp_path)
    found = broken_links()
    assert len(found) == 4 and not any("skipped" in f or "a.md'" in f for f in found), found


def test_the_readme_and_the_guide_each_show_every_board_preview():
    """Each file on its own: one showing a board must not hide that the other forgot it."""
    for doc in ("README.md", "docs/GUI_DESIGN_GUIDE.md"):
        shown = (REPO / doc).read_text(encoding="utf-8")
        for png in sorted((REPO / "docs" / "images" / "boards").glob("*.png")):
            assert png.name in shown, f"{png.name} is not shown in {doc}"
