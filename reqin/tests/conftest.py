import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from make_fixtures import build  # noqa: E402


REQUIRED = {"csv", "xlsx", "doors_csv", "reqif", "sysml", "sqlite", "docx", "pdf"}


@pytest.fixture(scope="session")
def fx(tmp_path_factory):
    built = build(tmp_path_factory.mktemp("fixtures"))
    missing = REQUIRED - set(built)
    assert not missing, f"required fixtures not built: {sorted(missing)}. A missing fixture must FAIL, never skip."
    return built
