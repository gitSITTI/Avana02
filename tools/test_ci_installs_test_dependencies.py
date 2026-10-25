"""CI must install the libraries the tests in tools/ use (Pillow, numpy, pyyaml through reqin, Playwright), so those tests run there instead of being skipped.

Many tests in tools/ start with `pytest.importorskip(...)`: the picture-to-components scripts and the drift gate need Pillow and numpy, the dataset tests need pyyaml (through reqin), the
browser tests need Playwright. A skipped test is not a failed test, so a CI job that quietly lost an install would keep going green while checking nothing. This test fails in CI (the `CI`
variable that GitHub Actions and GitLab both set) when one is missing, and does nothing on a developer's machine, where skipping is the right thing. GitLab's guard job is a slim Python
image with no browser, so it sets `CI_GUARD_NO_BROWSER=1` to leave Playwright out of the requirement; the browser tests run there in `prototype:browser`.

What this proves: the CI environment has what those tests need, and the check itself can fail (the second test). What it does not prove: that the jobs ran; it says nothing about a
machine that does not set `CI`. Standard library only.
"""
from __future__ import annotations

import importlib.util
import os

NEEDED = ("PIL", "numpy", "yaml", "playwright")


def missing_in_ci(env, find_spec=importlib.util.find_spec) -> list[str]:
    """The libraries CI must have and does not. Empty when not running in CI."""
    if env.get("CI", "").lower() not in ("true", "1"):
        return []
    needed = [m for m in NEEDED if not (m == "playwright" and env.get("CI_GUARD_NO_BROWSER"))]
    return [m for m in needed if find_spec(m) is None]


def test_ci_has_the_libraries_the_tests_need():
    assert missing_in_ci(os.environ) == [], "CI must install these in the job that runs `pytest tools`, or those tests are silently skipped"


def test_the_check_fails_when_a_library_is_missing_and_stays_quiet_outside_ci():
    nothing_installed = lambda name: None  # noqa: E731
    assert missing_in_ci({"CI": "true"}, nothing_installed) == ["PIL", "numpy", "yaml", "playwright"]
    assert missing_in_ci({"CI": "true", "CI_GUARD_NO_BROWSER": "1"}, nothing_installed) == ["PIL", "numpy", "yaml"]
    assert missing_in_ci({"CI": "1"}, lambda n: None if n == "numpy" else object()) == ["numpy"]
    assert missing_in_ci({}, nothing_installed) == []
    assert missing_in_ci({"CI": "false"}, nothing_installed) == []
