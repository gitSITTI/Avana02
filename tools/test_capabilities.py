"""A stale newcomer table must fail, including when only the source registry changed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys


def test_capability_table_is_current_and_drift_is_detected(tmp_path):
    root = Path(__file__).resolve().parent.parent
    current = subprocess.run([sys.executable, str(root / "tools/capabilities.py"), "--check"], capture_output=True, text=True)
    assert current.returncode == 0, current.stdout + current.stderr
    (tmp_path / "tools").mkdir(); (tmp_path / "docs").mkdir()
    shutil.copy(root / "tools/capabilities.py", tmp_path / "tools/capabilities.py")
    (tmp_path / "component.py").touch()
    data = {"format": "reqin-capabilities/1", "capabilities": [{"name": "Example", "state": "partial", "code": "component.py", "evidence": None, "limit": "Not yet checked"}]}
    source = tmp_path / "docs/capabilities.json"
    source.write_text(json.dumps(data))
    cmd = [sys.executable, str(tmp_path / "tools/capabilities.py")]
    subprocess.run(cmd, check=True)
    assert subprocess.run(cmd + ["--check"], capture_output=True).returncode == 0
    data["capabilities"][0]["limit"] = "A changed implementation boundary"
    source.write_text(json.dumps(data))
    stale = subprocess.run(cmd + ["--check"], capture_output=True, text=True)
    assert stale.returncode != 0 and "stale" in stale.stderr
