"""Files that tools write when a person presses Export, read through the `tabular` adapter and the example profiles.

EVERYTHING HERE IS MADE UP. The shapes follow the vendors' documentation (docs/SOURCE_EXPORTS.md says which page for each); no real export
has been available, so the header texts below are guesses that a person with a real export must check (`reqin discover <file>`).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from reqin import Profile, Source, ingest, pick_adapter
from reqin.adapters.tabular import TabularAdapter
from reqin.testing import check_adapter

ROOT = Path(__file__).parent.parent


def profile(name: str) -> Profile:
    return Profile.from_yaml((ROOT / "profiles" / name).read_text(encoding="utf-8"))


# ---- an Agility grid export: HTML saved as .xls ------------------------------------------------------------------------------------------
AGILITY_GRID = """<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"><style>td {mso-number-format:"\\@";}</style></head>
<body><table border="1">
<tr><th>Number</th><th>Name</th><th>Description</th><th>Status</th><th>Scope</th><th>Super</th></tr>
<tr><td>S-01201</td><td>Updater</td><td><p>The updater shall verify the signature &amp; the version before install.</p><p>It shall not install on failure.</p></td><td>Active</td><td>Fictional Project</td><td>E-00100</td></tr>
<tr><td>S-01202</td><td>Buffer</td><td>The controller shall buffer 10&nbsp;messages.<br>Overflow shall be counted.</td><td>Future</td><td>Fictional Project</td><td>E-00100</td></tr>
<tr><td>E-00100</td><td>Platform</td><td><b>The platform shall support over-the-air updates.</b></td><td>Active</td><td>Fictional Project</td><td></td></tr>
<tr><td>S-01203</td><td>Spike</td><td></td><td>Active</td><td>Fictional Project</td><td></td></tr>
</table></body></html>"""


@pytest.fixture
def grid(tmp_path):
    p = tmp_path / "agility_grid.xls"                      # the extension the vendor's export uses, whatever is inside
    p.write_text(AGILITY_GRID, encoding="utf-8")
    return p


def test_an_agility_grid_export_is_html_in_an_xls_file_and_is_read_as_a_table(grid):
    assert pick_adapter(Source(str(grid))).name == "tabular"
    r = ingest(Source(str(grid)), profile=profile("agility_export.yaml"))
    assert r.report["invariant_ok"] and r.report["raw_records"] == 4 and len(r.requirements) == 4 and not r.rejected
    by = {q.uid: q for q in r.requirements}
    assert set(by) == {"S-01201", "S-01202", "E-00100", "S-01203"}
    assert by["S-01201"].text == "The updater shall verify the signature & the version before install.\nIt shall not install on failure."
    assert by["S-01202"].text == "The controller shall buffer 10 messages.\nOverflow shall be counted."       # <br> is a line break, &nbsp; a space
    assert by["E-00100"].text == "The platform shall support over-the-air updates."
    assert by["S-01201"].fields["status"] == "Active" and by["S-01201"].fields["owner"] == "Fictional Project"
    # a default grid has no Description column (the vendor says it must be added), so the profile falls back to Name; an item with an empty
    # Description therefore becomes a requirement whose text is its title. That is the profile's documented choice, and it is visible here.
    assert by["S-01203"].text == "Spike"


def test_the_agility_grid_passes_the_connector_properties(grid):
    check_adapter(TabularAdapter, Source(str(grid)), profile("agility_export.yaml"), expect_ok=4, files=[grid],
                  gold_text={"E-00100": "The platform shall support over-the-air updates."})


def test_a_default_agility_grid_without_a_description_column_is_read_by_name(tmp_path):
    p = tmp_path / "default_grid.xls"
    p.write_text("<table><tr><th>Number</th><th>Name</th><th>Status</th></tr><tr><td>S-1</td><td>As an operator I want a log</td><td>Active</td></tr></table>")
    r = ingest(Source(str(p)), profile=profile("agility_export.yaml"))
    assert [(q.uid, q.text) for q in r.requirements] == [("S-1", "As an operator I want a log")]


def test_a_real_binary_xls_is_not_claimed_and_a_page_without_a_table_is_not_either(tmp_path):
    ole = tmp_path / "old.xls"
    ole.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 600)
    page = tmp_path / "page.html"
    page.write_text("<html><body><p>No table here, only <b>prose</b>.</p></body></html>")
    table = tmp_path / "t.html"
    table.write_text("<table><tr><td>a<td>b</table>")
    ad = TabularAdapter()
    assert ad.sniff(Source(str(ole))) == 0.0 and ad.sniff(Source(str(page))) == 0.0 and ad.sniff(Source(str(table))) == 0.9


def test_tables_are_named_by_caption_or_position_and_one_can_be_chosen(tmp_path):
    p = tmp_path / "two.html"
    p.write_text("<table><caption>Summary</caption><tr><th>k</th><th>v</th><tr><td>a<td>b</table>"
                 "<table><tr><th>ID</th><th>Text</th></tr><tr><td>R1</td><td>The unit shall start.</td></tr><tr><td>R2</td><td>The unit shall stop.</td></tr></table>")
    ad = TabularAdapter()
    names = [c.name for c in ad.discover(Source(str(p))).containers]
    assert names == ["Summary", "two#2"]
    assert [c.rows for c in ad.discover(Source(str(p), {"sheet": "2"})).containers] == [2]            # by position
    assert [c.name for c in ad.discover(Source(str(p), {"sheet": "Summary"})).containers] == ["Summary"]


def test_html_that_real_exporters_write_is_tolerated(tmp_path):
    p = tmp_path / "messy.htm"
    # omitted </td> and </tr>, a colspan, script and style, an entity, a table inside a cell, uppercase tags, a file cut off in the middle
    p.write_text("<HTML><STYLE>td{color:red}</STYLE><SCRIPT>var x='<td>no</td>';</SCRIPT><TABLE><TR><TH>ID<TH>Text<TH>Note"
                 "<TR><TD>R1<TD>The unit shall start &lt; 5 s.<TD>a"
                 "<TR><TD colspan=2>R2 spans two<TD>b"
                 "<TR><TD>R3<TD><table><tr><td>inner one<td>inner two</table> after<TD>c"
                 "<TR><TD>R4<TD>cut off here")
    rows = TabularAdapter()._tables(Source(str(p)))
    t = rows[next(iter(rows))]
    assert [r["ID"] for r in t] == ["R1", "R2 spans two", "R3", "R4"]
    assert t[0]["Text"] == "The unit shall start < 5 s." and t[1]["Text"] == "" and t[1]["Note"] == "b"
    assert "inner one" in t[2]["Text"] and "after" in t[2]["Text"] and t[2]["Note"] == "c"
    assert t[3]["Text"] == "cut off here" and "var x" not in str(t)


def test_encodings_and_hostile_nesting_do_not_break_the_reader(tmp_path):
    a = tmp_path / "cp1252.xls"
    a.write_bytes('<table><tr><th>ID<th>Text<tr><td>R1<td>The caf\u00e9 shall open.</table>'.encode("cp1252"))
    b = tmp_path / "bom.xls"
    b.write_bytes(b"\xef\xbb\xbf" + "<table><tr><th>ID<th>Text<tr><td>R1<td>The unit shall run at 85\u00b0 C \u2013 caf\u00e9 mode.</table>".encode("utf-8"))
    c = tmp_path / "meta.xls"
    c.write_bytes('<meta charset="iso-8859-1"><table><tr><th>ID<th>Text<tr><td>R1<td>Ma\u00dfe shall hold.</table>'.encode("iso-8859-1"))
    d = tmp_path / "deep.xls"
    d.write_text("<table><tr><th>ID<th>Text<tr><td>R1<td>" + "<table><tr><td>" * 3000 + "deep" + "</table>" * 3000 + "</table>")
    ad = TabularAdapter()
    texts = {n: next(iter(ad._tables(Source(str(f))).values()))[0]["Text"] for n, f in (("a", a), ("b", b), ("c", c), ("d", d))}
    assert texts["a"] == "The caf\u00e9 shall open." and "85\u00b0 C \u2013 caf\u00e9" in texts["b"] and texts["c"] == "Ma\u00dfe shall hold." and "deep" in texts["d"]


# ---- an MSOSA / Cameo requirement table: #, Id, Name, Text --------------------------------------------------------------------------------
def test_a_cameo_requirement_table_as_csv_with_semicolons_and_as_html(tmp_path):
    csv_file = tmp_path / "requirements_table.csv"
    csv_file.write_text('#;Id;Name;Text\n1;REQ-1;Response;"The controller shall respond within 50 ms;\nthen log it."\n2;REQ-2;Heartbeat;The controller shall send a heartbeat every 1 s.\n', encoding="utf-8")
    html_file = tmp_path / "requirements_table.html"
    html_file.write_text("<table><tr><th>#</th><th>Id</th><th>Name</th><th>Text</th></tr><tr><td>1</td><td>REQ-1</td><td>Response</td><td>The controller shall respond within 50 ms; then log it.</td></tr>"
                         "<tr><td>2</td><td>REQ-2</td><td>Heartbeat</td><td>The controller shall send a heartbeat every 1 s.</td></tr></table>", encoding="utf-8")
    for f in (csv_file, html_file):
        r = ingest(Source(str(f)), profile=profile("cameo_requirement_table.yaml"))
        assert r.report["invariant_ok"] and [q.uid for q in r.requirements] == ["REQ-1", "REQ-2"], f.name
        assert "shall send a heartbeat every 1 s." in r.requirements[1].text
        assert r.requirements[0].extra["Name"] == "Response"                                           # not claimed by the profile, so kept


def test_a_cameo_table_without_the_id_column_falls_back_to_the_name_and_says_so(tmp_path):
    f = tmp_path / "no_id.csv"
    f.write_text("#,Name,Text\n1,Response,The controller shall respond within 50 ms.\n", encoding="utf-8")
    r = ingest(Source(str(f)), profile=profile("cameo_requirement_table.yaml"))
    assert r.requirements[0].uid == "Response"                                                       # the profile lists Name as the last resort for the identifier


# ---- a DOORS Next (DNG) module view exported as CSV --------------------------------------------------------------------------------------
DNG_CSV = ('ID,Artifact Type,isHeading,parentBinding,Primary Text,Status\n'
           '10,Heading,true,,Flight control,\n'
           '11,System Requirement,false,10,"<div>The unit shall display ""READY""\u00a0within <b>2 s</b>.</div>",Approved\n'
           '12,System Requirement,false,10,<div>The unit shall log faults.</div>,Draft\n'
           '13,Information,False,10,,Draft\n')


def test_a_dng_module_view_csv_keeps_the_artifacts_and_counts_the_headings(tmp_path):
    f = tmp_path / "view.csv"
    f.write_text(DNG_CSV, encoding="utf-8")
    r = ingest(Source(str(f)), profile=profile("dng_csv.yaml"))
    assert r.report["invariant_ok"] and r.report["raw_records"] == 4
    assert r.report["filtered_out"] == {"row filter (where) did not match": 1}                          # the heading, counted
    assert [q.uid for q in r.requirements] == ["11", "12"] and len(r.rejected) == 1                      # 13 has no primary text: rejected with a reason
    assert r.requirements[0].text == 'The unit shall display "READY"\u00a0within 2 s.'                 # markup removed; the text itself is kept as written ...
    assert r.requirements[0].norm_text == 'The unit shall display "READY" within 2 s.'                  # ... and the comparison text has the non-breaking space as a space
    assert r.requirements[0].extra["parentBinding"] == "10" and r.requirements[0].fields["status"] == "Approved"
