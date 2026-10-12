"""DOORS 9.x route: a DXL script writes a CSV, the tabular adapter reads it. The DXL itself has NEVER run in DOORS; these tests
check what can be checked without DOORS: the CSV shape it promises is what the profile reads, the reader copes with what DXL-style
quoting produces, and the script contains no call that could change a DOORS database."""
from __future__ import annotations

import csv
import re
from pathlib import Path

from reqin import Profile, Source, ingest

ROOT = Path(__file__).parent.parent
DXL = (ROOT / "connectors/doors9/export_requirements.dxl").read_text(encoding="utf-8")
PROFILE = Profile.from_yaml((ROOT / "profiles/doors_csv.yaml").read_text())


def _code(dxl: str) -> str:
    """The DXL without comments and string literals, so a word in a comment cannot hide or fake a call."""
    dxl = re.sub(r"//[^\n]*", "", dxl)
    dxl = re.sub(r"/\*.*?\*/", "", dxl, flags=re.S)
    return re.sub(r'"(?:\\.|[^"\\])*"', '""', dxl)


def _header() -> list[str]:
    m = re.search(r'const string HEADER = "([^"]*)\\n"', DXL)
    assert m, "HEADER constant not found in the DXL"
    return m.group(1).split(",")


def test_the_columns_the_script_writes_are_the_columns_the_profile_reads():
    cols = set(_header())
    wanted = {c for rule in PROFILE.fields.values() for c in rule.src + rule.join} | set(PROFILE.where)
    assert wanted <= cols, f"profile reads {sorted(wanted - cols)} but the script does not write them"
    row_fn = _code(DXL).split("void writeRow", 1)[1]
    assert row_fn.count("putField(") == len(cols), "writeRow must write exactly one field per HEADER column"


def test_the_script_cannot_change_a_doors_database():
    code = _code(DXL)
    for forbidden in ("edit", "share", "save", "delete", "purge", "create", "modify", "unlock", "lock", "set", "import", "system",
                      "exec", "batch", "copy", "paste", "clear", "restore", "baseline", "link"):
        assert not re.search(rf"\b{forbidden}\b\s*[(\w\"]", code), f"DXL contains '{forbidden}'"
    assert "read(modulePath, false)" in code.replace(" ", " ") and "write(outPath)" in code
    assert code.count("write(") == 1, "the only write() allowed is the output file"


def _dxl_style_csv(path: Path, rows: list[list[str]]) -> None:
    """What putField() produces: every field quoted, quotes doubled, line breaks kept, UTF-8, no BOM."""
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(_header()) + "\n")
        for r in rows:
            f.write(",".join('"' + c.replace('"', '""') + '"' for c in r) + "\n")


def test_dxl_style_csv_round_trips_through_the_tabular_adapter(tmp_path):
    p = tmp_path / "doors_dxl_export.csv"
    rows = [
        ["1", "SRS-1", "1", "Flight control", "", ""],                                               # heading: no text
        ["2", "SRS-10", "2", "", 'The unit shall display "READY", then beep, within 2 s.', "Test"],  # quotes and commas
        ["3", "SRS-11", "2", "", "The unit shall log faults.\nEach record shall have a time.", "Analysis"],   # line break inside a field
        ["4", "SRS-12", "2", "", "The unit shall operate at 85° C – café mode.", "Inspection"],     # non-ASCII
    ]
    _dxl_style_csv(p, rows)
    r = ingest(Source(str(p)), profile=PROFILE)
    assert r.report["invariant_ok"] and len(r.requirements) == 3
    by = {q.uid: q for q in r.requirements}
    assert by["SRS-10"].text == 'The unit shall display "READY", then beep, within 2 s.'
    assert "Each record shall have a time." in by["SRS-11"].text and "85° C – café" in by["SRS-12"].text
    assert by["SRS-10"].fields["verification"] == "Test"
    assert r.report["filtered_out"] == {"row filter (where) did not match": 1}                       # the heading row, counted, not lost
    assert sum(1 for _ in csv.reader(p.open(encoding="utf-8"))) == 5
