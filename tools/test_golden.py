"""The drift gate (tools/gui_checks/golden.py): does it say "drifted" when a picture changed, and only then?

What this proves, on pictures drawn here whose right answer is known: an unchanged picture passes; noise below the threshold is ignored and a real colour change is not; a change
bigger than the tolerance fails and one smaller passes; a size change fails; a missing golden or a missing picture is refused instead of passing; `compare-all` FAILS for an
approved screen that was not photographed (the silent pass that would make the gate useless) and lists a picture nobody approved; the diff picture marks the changed area; approve
copies exactly the bytes it was given and refuses something that is not an image; the command line returns the exit statuses its docstring promises.
What it does not prove: anything about a real browser (tools/test_golden_browser.py takes the pictures), or that a screen that passes is good. Skipped when Pillow is not installed.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

PIL = pytest.importorskip("PIL")
from PIL import Image  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "tools" / "gui_checks" / "golden.py"
sys.path.insert(0, str(REPO / "tools" / "gui_checks"))
import golden as G  # noqa: E402


def png(path: Path, colour=(255, 255, 255), box=None, box_colour=(20, 20, 200), size=(100, 80)) -> Path:
    im = Image.new("RGB", size, colour)
    if box:
        im.paste(box_colour, box)
    im.save(path)
    return path


def run(cwd: Path, *args):
    return subprocess.run([sys.executable, str(GOLDEN), *args], cwd=cwd, capture_output=True, text=True)


def test_an_unchanged_picture_passes(tmp_path):
    a = png(tmp_path / "a.png", box=(10, 10, 40, 40))
    g = tmp_path / "g"
    assert G.approve("home", a, g) == 0
    assert G.compare(g / "home.png", a) == 0


def test_noise_under_the_threshold_is_ignored_and_a_real_change_is_not(tmp_path):
    g = tmp_path / "g"
    G.approve("home", png(tmp_path / "a.png", colour=(200, 200, 200)), g)
    # the number 24 is written out on purpose: a test that read G.NOISE would move with a break to it (the mutation run found exactly that)
    assert G.compare(g / "home.png", png(tmp_path / "noise.png", colour=(224, 200, 200)), tolerance=0.0) == 0
    assert G.compare(g / "home.png", png(tmp_path / "moved.png", colour=(225, 200, 200)), tolerance=0.0) == 1


@pytest.mark.parametrize("channel", [0, 1, 2], ids=["red", "green", "blue"])
def test_a_change_in_any_one_colour_channel_counts(tmp_path, channel):
    g = tmp_path / "g"
    G.approve("home", png(tmp_path / "a.png", colour=(100, 100, 100)), g)
    shifted = [100, 100, 100]
    shifted[channel] = 200
    assert G.compare(g / "home.png", png(tmp_path / "b.png", colour=tuple(shifted)), tolerance=0.0) == 1


def test_the_tolerance_decides_how_much_change_is_too_much(tmp_path):
    g = tmp_path / "g"
    G.approve("home", png(tmp_path / "a.png"), g)
    small = png(tmp_path / "small.png", box=(0, 0, 10, 8))          # 80 of 8000 pixels = 1 %
    big = png(tmp_path / "big.png", box=(0, 0, 30, 20))             # 600 of 8000 = 7.5 %
    assert G.compare(g / "home.png", small, tolerance=0.02) == 0
    assert G.compare(g / "home.png", small, tolerance=0.005) == 1
    assert G.compare(g / "home.png", big, tolerance=0.02) == 1


def test_a_different_size_fails(tmp_path, capsys):
    g = tmp_path / "g"
    G.approve("home", png(tmp_path / "a.png"), g)
    assert G.compare(g / "home.png", png(tmp_path / "wide.png", size=(120, 80))) == 1
    assert "120x80" in capsys.readouterr().out


def test_nothing_to_compare_against_is_refused_not_passed(tmp_path, capsys):
    a = png(tmp_path / "a.png")
    assert G.compare(tmp_path / "g" / "none.png", a) == 2
    G.approve("home", a, tmp_path / "g")
    assert G.compare(tmp_path / "g" / "home.png", tmp_path / "absent.png") == 2
    assert "not checked" in capsys.readouterr().err


def test_the_diff_picture_marks_where_it_changed(tmp_path):
    g = tmp_path / "g"
    G.approve("home", png(tmp_path / "a.png"), g)
    changed = png(tmp_path / "b.png", box=(50, 40, 90, 70))
    out = tmp_path / "d" / "diff.png"
    assert G.compare(g / "home.png", changed, diff_out=out) == 1
    d = Image.open(out).convert("RGB")
    assert d.getpixel((60, 50)) == (226, 75, 74)                   # inside the change: red
    assert d.getpixel((5, 5)) != (226, 75, 74)                     # outside it: not red


def test_approve_copies_the_bytes_and_refuses_what_is_not_an_image(tmp_path):
    a = png(tmp_path / "a.png", box=(1, 1, 9, 9))
    assert G.approve("home", a, tmp_path / "g") == 0
    assert (tmp_path / "g" / "home.png").read_bytes() == a.read_bytes()
    (tmp_path / "notes.txt").write_text("not a picture")
    assert G.approve("bad", tmp_path / "notes.txt", tmp_path / "g") == 2
    assert not (tmp_path / "g" / "bad.png").exists()
    assert G.approve("gone", tmp_path / "nope.png", tmp_path / "g") == 2


def test_compare_all_says_so_when_nothing_was_approved(tmp_path, capsys):
    (tmp_path / "shots").mkdir()
    png(tmp_path / "shots" / "home.png")
    assert G.compare_all(tmp_path / "shots", tmp_path / "g", 0.01, None) == 0
    assert "NOTHING WAS COMPARED" in capsys.readouterr().out


def test_compare_all_fails_for_an_approved_screen_nobody_photographed(tmp_path, capsys):
    shots, g = tmp_path / "shots", tmp_path / "g"
    shots.mkdir()
    a = png(tmp_path / "a.png")
    G.approve("home", a, g)
    G.approve("detail", a, g)
    png(shots / "home.png")                                          # `detail` was not photographed
    assert G.compare_all(shots, g, 0.01, None) == 1
    assert "FAIL detail" in capsys.readouterr().out


def test_compare_all_lists_a_picture_with_no_golden_and_still_passes(tmp_path, capsys):
    shots, g = tmp_path / "shots", tmp_path / "g"
    shots.mkdir()
    G.approve("home", png(tmp_path / "a.png"), g)
    png(shots / "home.png")
    png(shots / "brand-new.png")
    assert G.compare_all(shots, g, 0.01, None) == 0
    assert "brand-new" in capsys.readouterr().out


def test_compare_all_fails_when_any_one_screen_drifted(tmp_path):
    shots, g = tmp_path / "shots", tmp_path / "g"
    shots.mkdir()
    a = png(tmp_path / "a.png")
    G.approve("home", a, g)
    G.approve("detail", a, g)
    png(shots / "home.png")
    png(shots / "detail.png", colour=(0, 0, 0))
    assert G.compare_all(shots, g, 0.01, tmp_path / "diffs") == 1
    assert (tmp_path / "diffs" / "detail.png").exists() and not (tmp_path / "diffs" / "home.png").exists()


def test_the_command_line_returns_the_statuses_the_docstring_promises(tmp_path):
    a = png(tmp_path / "a.png")
    assert run(tmp_path, "approve", "home", "a.png", "--goldens", "g").returncode == 0
    assert run(tmp_path, "compare", "home", "a.png", "--goldens", "g").returncode == 0
    b = png(tmp_path / "b.png", colour=(0, 0, 0))
    r = run(tmp_path, "compare", "home", "b.png", "--goldens", "g")
    assert r.returncode == 1 and "FAIL home" in r.stdout
    assert run(tmp_path, "compare", "nope", "a.png", "--goldens", "g").returncode == 2
    assert b.exists() and a.exists()


def test_the_docstring_names_only_commands_that_exist():
    doc = G.__doc__
    for cmd in ("shot", "approve", "compare", "compare-all"):
        assert f"golden.py {cmd}" in doc
    r = subprocess.run([sys.executable, str(GOLDEN), "--help"], capture_output=True, text=True)
    assert r.returncode == 0 and all(c in r.stdout for c in ("shot", "approve", "compare-all"))
