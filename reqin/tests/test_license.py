"""The licence has to stay what the package metadata and the notice files say it is."""
from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).parent.parent                    # the reqin/ folder (also /opt/reqin in the container image)
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_the_package_declares_apache_2_and_ships_the_licence_files():
    assert PYPROJECT["license"] == "Apache-2.0"
    assert set(PYPROJECT["license-files"]) == {"LICENSE", "NOTICE"}
    for name in PYPROJECT["license-files"]:
        assert (ROOT / name).is_file(), f"{name} is declared in pyproject.toml but missing"


def test_the_licence_file_is_the_unmodified_apache_2_text():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert text.lstrip().startswith("Apache License\n"), "LICENSE does not start with the Apache License heading"
    assert "Version 2.0, January 2004" in text and "END OF TERMS AND CONDITIONS" in text
    # The standard text ends with the appendix template; if someone fills in the template here, the file is no longer the canonical text.
    assert "Copyright [yyyy] [name of copyright owner]" in text
    assert len(text.splitlines()) == 201, "the standard text has 201 lines; this one was edited"


def test_the_notice_names_a_copyright_holder_and_the_licence():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert "Copyright 20" in notice and "Apache License, Version 2.0" in notice
