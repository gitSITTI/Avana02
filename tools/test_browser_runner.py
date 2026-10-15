"""The runner that CI uses for the prototype's browser tests (prototype/run_browser_tests.py) must fail when a test fails, say which one and what it said, and refuse to
pass when something it needs is missing. This runs the real runner against small stand-in tests in a temporary folder; no browser is started."""
import importlib.util
from pathlib import Path

import pytest

RUNNER = Path(__file__).resolve().parent.parent / "prototype" / "run_browser_tests.py"


@pytest.fixture
def runner(tmp_path):
    spec = importlib.util.spec_from_file_location("run_browser_tests_under_test", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    (tmp_path / "project").mkdir()
    (tmp_path / "project" / "Main.dc.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "vendor" / "node_modules" / "react").mkdir(parents=True)
    mod.HERE = str(tmp_path)
    mod.PLAN = [("b91.py", "a test that passes", [1440, 390]), ("b92.py", "a test that fails at one width", [1440, 390])]
    (tmp_path / "b91.py").write_text("print('PASS one')\nprint('PASS two')\n", encoding="utf-8")
    (tmp_path / "b92.py").write_text(
        "import sys\nprint('PASS fine at every width')\n"
        "if sys.argv[1] == '390':\n    print('FAIL the thing that broke')\n    sys.exit(1)\n", encoding="utf-8")
    return mod


def test_a_run_where_everything_passes_exits_zero(runner, capsys):
    assert runner.main(["b91"]) == 0
    out = capsys.readouterr().out
    assert "2 runs" in out and "all passed" in out and "2 checks" in out


def test_one_failing_run_fails_the_whole_job_and_says_which_and_why(runner, capsys):
    assert runner.main([]) == 1
    out = capsys.readouterr().out
    assert "1 FAILED: b92.py at 390" in out
    assert "FAIL the thing that broke" in out
    assert "FAIL  b92.py" in out and "ok    b91.py" in out


def test_a_width_filter_runs_only_that_width(runner, capsys):
    assert runner.main(["--width", "1440"]) == 0
    assert "2 runs" in capsys.readouterr().out


def test_a_file_that_is_not_in_the_plan_is_refused(runner, capsys):
    assert runner.main(["b99"]) == 1
    assert "no such test: b99.py" in capsys.readouterr().out


def test_a_missing_page_or_missing_libraries_is_refused_not_passed(runner, tmp_path, capsys):
    (tmp_path / "project" / "Main.dc.html").unlink()
    assert runner.main([]) == 1
    assert "build.py first" in capsys.readouterr().out
    (tmp_path / "project" / "Main.dc.html").write_text("x", encoding="utf-8")
    (tmp_path / "vendor" / "node_modules" / "react").rmdir()
    assert runner.main([]) == 1
    assert "npm ci" in capsys.readouterr().out


def test_the_plan_lists_every_browser_test_file():
    """A new bNN.py that nobody adds to the plan would never run in CI."""
    spec = importlib.util.spec_from_file_location("run_browser_tests_plan", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    planned = {f for f, _, _ in mod.PLAN}
    on_disk = {p.name for p in RUNNER.parent.glob("b[0-9][0-9].py") if int(p.stem[1:]) >= 11}
    assert planned == on_disk, f"in the plan but not on disk: {sorted(planned - on_disk)}; on disk but not in the plan: {sorted(on_disk - planned)}"
