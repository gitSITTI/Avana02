"""The pictures in docs/images must show the boards and the prototype as they are now, not as they were once."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BOARDS = REPO / "excalidraw"
BOARD_PNGS = REPO / "docs" / "images" / "boards"
SHOTS = REPO / "docs" / "images" / "prototype"
PAGE = REPO / "prototype" / "project" / "Main.dc.html"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_every_board_has_a_preview_that_was_rendered_from_its_current_content():
    manifest = json.loads((BOARD_PNGS / "manifest.json").read_text(encoding="utf-8"))["boards"]
    boards = sorted(p.name for p in BOARDS.glob("*.excalidraw"))
    assert boards, "no boards found"
    assert sorted(manifest) == boards, "boards and previews differ; run: cd excalidraw_generator && python3 render_previews.py"
    for b in boards:
        assert manifest[b] == _sha(BOARDS / b), f"{b} changed after its preview was rendered; run: cd excalidraw_generator && python3 render_previews.py (then look at the pictures)"
        stem = Path(b).stem
        for png in (BOARD_PNGS / f"{stem}.png", BOARD_PNGS / "thumbs" / f"{stem}.png"):
            assert png.is_file() and png.stat().st_size > 10_000, f"{png.relative_to(REPO)} is missing or empty"


def test_there_are_no_leftover_previews_for_boards_that_no_longer_exist():
    stems = {p.stem for p in BOARDS.glob("*.excalidraw")}
    for folder in (BOARD_PNGS, BOARD_PNGS / "thumbs"):
        extra = sorted(p.name for p in folder.glob("*.png") if p.stem not in stems)
        assert not extra, f"previews with no board: {extra}"


def test_the_prototype_screenshots_show_the_current_page():
    manifest = json.loads((SHOTS / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["prototype_page"] == _sha(PAGE), "the prototype page changed after its screenshots were taken; run: cd prototype && python3 shots.py (then look at the pictures)"
    assert manifest["screens"], "the screenshot manifest lists nothing"
    for name in manifest["screens"]:
        assert (SHOTS / name).is_file(), f"listed screenshot {name} is missing"
    assert sorted(p.name for p in SHOTS.glob("*.png")) == sorted(manifest["screens"]), "screenshots on disk differ from the manifest"
