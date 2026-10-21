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
    # writeRow() has one if/else per optional field, so putField() appears more often than there are columns; commas between fields do not
    body = DXL.split("void writeRow", 1)[1].split("\n}\n", 1)[0]
    assert _code(body).count("comma(out)") == len(_header()) - 1, "writeRow must separate exactly as many fields as HEADER has columns"
    # the attributes are read in the order HEADER lists them (the ones that are object attributes, not computed)
    attrs = [c for c in _header() if f'o."{c}"' in body]
    assert attrs and [body.index(f'o."{c}"') for c in attrs] == sorted(body.index(f'o."{c}"') for c in attrs), "attributes out of HEADER order"


def test_the_script_cannot_change_a_doors_database():
    code = _code(DXL)
    for forbidden in ("edit", "share", "save", "delete", "purge", "create", "modify", "unlock", "lock", "set", "import", "system",
                      "exec", "batch", "copy", "paste", "clear", "restore", "baseline", "link"):
        assert not re.search(rf"\b{forbidden}\b\s*[(\w\"]", code), f"DXL contains '{forbidden}'"
    assert re.search(r"\bread\(modulePath,\s*false", code) and "write(outPath)" in code
    assert code.count("read(") == 1 and code.count("write(") == 1, "the only read() is the module and the only write() is the output file"


def _dxl_style_csv(path: Path, rows: list[list[str]]) -> None:
    """What putField() produces: every field quoted, quotes doubled, line breaks kept, UTF-8, no BOM."""
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(",".join(_header()) + "\n")
        for r in rows:
            f.write(",".join('"' + c.replace('"', '""') + '"' for c in r) + "\n")


def test_dxl_style_csv_round_trips_through_the_tabular_adapter(tmp_path):
    p = tmp_path / "doors_dxl_export.csv"
    # Module, Absolute Number, Object Identifier, Object Level, Object Heading, Object Text, Verification Method, Deleted, Links
    rows = [
        ["/DEMO/SRS", "1", "SRS-1", "1", "Flight control", "", "", "0", ""],                                               # heading: no text
        ["/DEMO/SRS", "2", "SRS-10", "2", "", 'The unit shall display "READY", then beep, within 2 s.', "Test", "0", "/DEMO/SYS#7;/DEMO/SYS#8"],  # quotes, commas, two links
        ["/DEMO/SRS", "3", "SRS-11", "2", "", "The unit shall log faults.\nEach record shall have a time.", "Analysis", "0", ""],   # line break inside a field
        ["/DEMO/SRS", "4", "SRS-12", "2", "", "The unit shall operate at 85° C – café mode.", "Inspection", "0", ""],     # non-ASCII
        ["/DEMO/SRS", "5", "SRS-13", "2", "", "The unit shall never be written to.", "Test", "1", ""],                      # a deleted object, written because includeDeleted was true
    ]
    _dxl_style_csv(p, rows)
    r = ingest(Source(str(p)), profile=PROFILE)
    assert r.report["invariant_ok"] and len(r.requirements) == 4
    by = {q.uid: q for q in r.requirements}
    assert by["SRS-10"].text == 'The unit shall display "READY", then beep, within 2 s.'
    assert "Each record shall have a time." in by["SRS-11"].text and "85° C – café" in by["SRS-12"].text
    assert by["SRS-10"].fields["verification"] == "Test"
    assert r.report["filtered_out"] == {"row filter (where) did not match": 1}                       # the heading row, counted, not lost
    assert sum(1 for _ in csv.reader(p.open(encoding="utf-8"))) == 6
    # the module and the deleted flag are not dropped, so a deleted object can be seen for what it is
    assert by["SRS-13"].extra["Deleted"] == "1" and by["SRS-10"].extra["Deleted"] == "0" and by["SRS-10"].extra["Module"] == "/DEMO/SRS"
    # links point at "<module>#<number>", which is not a requirement identifier here: kept by that text, reported, never dropped
    kept = [(l.source_uid, l.target_uid, l.kind) for l in r.links]
    assert kept == [("SRS-10", "/DEMO/SYS#7", "trace"), ("SRS-10", "/DEMO/SYS#8", "trace")]
    assert "2 links point outside this import (kept by UID)" in r.report["warnings"]
