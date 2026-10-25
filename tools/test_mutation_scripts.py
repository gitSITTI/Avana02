"""The mutation scripts in tools/mutation/ change one thing in a copy of the code and expect the project's checks to notice. When the code they change is
rewritten, a script can quietly stop matching anything and prove nothing. This test fails then: every change a script makes must still match the current code.
It runs no checks and finishes in under a second; the full runs take minutes (see tools/mutation/README.md)."""
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent / "mutation"
SCRIPTS = ["a11y", "ai", "board_spec", "connect", "gateway", "gold", "keep", "trace", "vee", "population", "server", "wall", "compare", "connectors", "review", "firefox", "golden"]


@pytest.mark.parametrize("name", SCRIPTS)
def test_every_change_the_script_makes_still_matches_the_code(name):
    r = subprocess.run([sys.executable, str(HERE / f"{name}.py"), "--patterns"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr


def test_every_script_in_the_folder_is_listed():
    found = {p.stem for p in HERE.glob("*.py")} - {"common"}
    assert found == set(SCRIPTS), f"scripts not covered by this test: {sorted(found - set(SCRIPTS))}"


def test_the_pattern_check_can_fail(tmp_path):
    """Break one pattern and the check must say so; otherwise it proves nothing."""
    src = (HERE / "vee.py").read_text(encoding="utf-8").replace("l.after = l.reqs - l.mergedAway", "l.after = l.reqs - l.mergedAwa", 1)
    (tmp_path / "common.py").write_text((HERE / "common.py").read_text(encoding="utf-8").replace("REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))", f"REPO = {str(HERE.parent.parent)!r}"), encoding="utf-8")
    (tmp_path / "vee.py").write_text(src, encoding="utf-8")
    r = subprocess.run([sys.executable, str(tmp_path / "vee.py"), "--patterns"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 1 and "PATTERN MISSING" in r.stdout
