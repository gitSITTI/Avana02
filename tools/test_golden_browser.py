"""The drift gate (tools/gui_checks/golden.py) with a real browser: does `shot` give the same picture twice, and does a real change to a screen make the gate fail?

Skipped when Playwright or its Chromium (or Pillow) is not installed. What this proves, on the reference viewer in Chromium on one machine:
  - two pictures of the same screen, dataset and width are identical (the gate would be useless if the pictures wobbled);
  - a picture of the screen with a dataset differs from one without (so the pictures show the data);
  - after a person approves a picture, a real change to the screen's own stylesheet makes `compare` fail and writes a diff, while the untouched screen still passes;
  - the width changes the picture and its size.
What it does not prove: that the pictures are the same on another machine, another Chromium or another operating system (they are not promised to be: see golden.py), or that
the screen is good. Chromium only.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

pytest.importorskip("PIL")
pytest.importorskip("playwright")
from PIL import Image  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "reqin" / "src"))
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import golden as G  # noqa: E402


def browser_available() -> bool:
    try:
        with sync_playwright() as pw:
            pw.chromium.launch().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not browser_available(), reason="Playwright's Chromium is not installed")

VIEWER = REPO / "design" / "reference_viewer"


@pytest.fixture(scope="module")
def datasets(tmp_path_factory):
    from reqin.cli import main
    d = tmp_path_factory.mktemp("golden_browser") / "ds"
    assert main(["make-datasets", str(d), "--size", "200"]) == 0
    return d


def one(datasets: Path, prefix: str) -> str:
    return sorted(p.name for p in datasets.iterdir() if p.is_dir() and p.name.startswith(prefix))[0]


def take(app, out, datasets=None, dataset=None, width=1000, height=700):
    assert G.shot(str(app), str(datasets) if datasets else None, dataset, width, height, Path(out)) == 0
    return Path(out)


def test_the_same_screen_gives_the_same_picture_twice(tmp_path, datasets):
    name = one(datasets, "F02")
    a = take(VIEWER, tmp_path / "a.png", datasets, name)
    b = take(VIEWER, tmp_path / "b.png", datasets, name)
    ia, ib = Image.open(a), Image.open(b)
    assert ia.size == (1000, 700)
    ratio, _ = G.changed_ratio(ia, ib)
    assert ratio == 0.0


def test_the_picture_shows_the_data_and_the_width(tmp_path, datasets):
    empty = take(VIEWER, tmp_path / "empty.png")
    full = take(VIEWER, tmp_path / "full.png", datasets, one(datasets, "F02"))
    ratio, _ = G.changed_ratio(Image.open(empty), Image.open(full))
    assert ratio > 0.05, "a screen with a dataset on it should look different from one without"
    narrow = take(VIEWER, tmp_path / "narrow.png", datasets, one(datasets, "F02"), width=500)
    assert Image.open(narrow).size == (500, 700)


def test_approved_then_changed_screen_fails_and_unchanged_screen_passes(tmp_path, datasets):
    name = one(datasets, "F02")
    app = tmp_path / "app"
    shutil.copytree(VIEWER, app)
    goldens = tmp_path / "golden"
    first = take(app, tmp_path / "first.png", datasets, name)
    assert G.approve("viewer", first, goldens) == 0
    again = take(app, tmp_path / "again.png", datasets, name)
    assert G.compare(goldens / "viewer.png", again) == 0

    css = app / "viewer.css"
    old = ".lede { margin: 0 0 var(--space-12); color: var(--text-secondary); }"
    text = css.read_text(encoding="utf-8")
    assert text.count(old) == 1
    css.write_text(text.replace(old, ".lede { margin: 0 0 120px; color: var(--text-secondary); }"), encoding="utf-8")
    changed = take(app, tmp_path / "changed.png", datasets, name)
    assert G.compare(goldens / "viewer.png", changed, diff_out=tmp_path / "diff.png") == 1
    assert (tmp_path / "diff.png").exists()
