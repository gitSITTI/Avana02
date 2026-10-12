"""The guide must not drift away from the code: if a connector is added, renamed or promoted, the docs have to say so."""
from __future__ import annotations

from pathlib import Path

from reqin.adapter import load_adapters

ROOT = Path(__file__).parent.parent
GUIDE = (ROOT / "CONNECTORS.md").read_text(encoding="utf-8")


def _builtin():
    return {n: c for n, c in load_adapters().items() if c.__module__.startswith("reqin.adapters.")}


def test_the_guide_names_every_built_in_live_connector_and_its_maturity():
    for name, cls in _builtin().items():
        if cls.maturity == "fake-server-tested":
            assert f"`{name}`" in GUIDE, f"CONNECTORS.md does not mention the {name} connector"
    assert "fake-server-tested" in GUIDE and "live-verified" in GUIDE


def test_the_guide_keeps_its_honesty_caveats():
    low = GUIDE.lower()
    assert "never run in doors" in low, "the DOORS script caveat disappeared"
    assert "nobody has, for any connector here" in low, "the statement that nobody has run these against a real system disappeared"
    assert "a real server" in low and "a real instance" in low, "the 'not proven' column of the maturity table disappeared"
    assert "2013" in GUIDE, "the OAuth statement must stay dated"


def test_every_option_the_guide_tells_you_to_set_is_one_the_code_reads():
    # Option names that appear as `--opt name=` in the guide must exist in the adapter sources, so a renamed option cannot linger in the docs.
    import re
    src = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "reqin").rglob("*.py"))
    names = set(re.findall(r"--opt\s+([a-z_]+)=", GUIDE))
    assert names, "the guide shows no --opt examples"
    missing = sorted(n for n in names if f'"{n}"' not in src and f"'{n}'" not in src)
    assert not missing, f"CONNECTORS.md uses options the code never reads: {missing}"
