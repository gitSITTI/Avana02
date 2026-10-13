"""The repository-root licence files and the copies that travel with the Python package must be the same bytes."""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_root_and_package_copies_of_licence_and_notice_are_identical():
    for name in ("LICENSE", "NOTICE"):
        root, pkg = REPO / name, REPO / "reqin" / name
        assert root.is_file() and pkg.is_file(), f"{name} must exist at the repository root and in reqin/"
        assert root.read_bytes() == pkg.read_bytes(), f"reqin/{name} differs from {name}: update both"


def test_the_bundled_third_party_file_is_covered_by_a_notice():
    notices = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    bundled = REPO / "prototype" / "project" / "support.js"
    assert bundled.is_file() and "prototype/project/support.js" in notices and "MIT" in notices
    assert "@license React" in bundled.read_text(encoding="utf-8")[:400], "the bundled file no longer carries its own licence header"
