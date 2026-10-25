"""CI must install Pillow and numpy, so the tests that need them run there instead of being skipped.

Several tests in tools/ start with `pytest.importorskip("PIL")` (the picture-to-components scripts and the drift gate, `tools/gui_checks/golden.py`). A skipped test is not a failed
test, so a CI job that quietly lost the install would keep going green while checking nothing. This test fails in CI (the `CI` variable that GitHub Actions and GitLab both set) when
either library is missing, and does nothing on a developer's machine, where skipping is the right thing.

What this proves: the CI environment has what those tests need, and the check itself can fail (the second test). What it does not prove: that the jobs ran; it says nothing about a
machine that does not set `CI`. Standard library only.
"""
from __future__ import annotations

import importlib.util
import os

NEEDED = ("PIL", "numpy")


def missing_in_ci(env, find_spec=importlib.util.find_spec) -> list[str]:
    """The libraries CI must have and does not. Empty when not running in CI."""
    if env.get("CI", "").lower() not in ("true", "1"):
        return []
    return [m for m in NEEDED if find_spec(m) is None]


def test_ci_has_the_libraries_the_picture_tests_need():
    assert missing_in_ci(os.environ) == [], "CI must `pip install pillow numpy` in the job that runs `pytest tools`, or those tests are silently skipped"


def test_the_check_fails_when_a_library_is_missing_and_stays_quiet_outside_ci():
    nothing_installed = lambda name: None  # noqa: E731
    assert missing_in_ci({"CI": "true"}, nothing_installed) == ["PIL", "numpy"]
    assert missing_in_ci({"CI": "1"}, lambda n: None if n == "numpy" else object()) == ["numpy"]
    assert missing_in_ci({}, nothing_installed) == []
    assert missing_in_ci({"CI": "false"}, nothing_installed) == []
