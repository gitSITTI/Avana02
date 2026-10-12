from __future__ import annotations

from pathlib import Path

import pytest

from make_fixtures import REQS
from reqin import Profile, Source, ingest
from reqin.adapter import pick_adapter
from reqin.adapters.sql import check_query
from reqin.model import Conf
from reqin.normalise import extract_slots, normalise_text

ROOT = Path(__file__).parent.parent


def test_slots_units_comparators_modals():
    a = extract_slots("The subsystem shall respond within 0.2 seconds.")
    b = extract_slots("The subsystem shall respond within 200 ms.")
    assert a.modal == b.modal == "shall"
    assert a.quantities[0]["base_value"] == pytest.approx(200) == b.quantities[0]["base_value"]
    assert a.quantities[0]["comparator"] == "<="
    c = extract_slots("It shall retain at least 30 days of records and shall not exceed 12 kg.")
    assert [q["comparator"] for q in c.quantities] == [">=", "<="] and c.negated
    assert extract_slots("The unit should weigh 5 kg.").modal == "should"


def test_markup_is_stripped_from_text():
    assert normalise_text("<xhtml:div><p>The   system&nbsp;shall–go.</p></xhtml:div>") == "The system shall-go."


def test_proposed_profile_is_flagged_and_labelled(fx):
    r = ingest(Source(str(fx["xlsx"])))
    assert r.report["profile_proposed"] and any("PROPOSED" in w for w in r.report["warnings"])
    assert r.requirements[0].conf["rationale"] in (Conf.MEDIUM, Conf.HIGH)


def test_confirmed_profile_gives_exact_labels_and_translates_values(fx):
    prof = Profile.from_yaml((ROOT / "profiles/xlsx_srs.yaml").read_text())
    r = ingest(Source(str(fx["xlsx"])), profile=prof)
    assert not r.report["profile_proposed"]
    q = r.requirements[0]
    assert q.uid == "REQ-FCS-0101" and not q.uid_synthetic
    assert q.fields["verification"] == "Test" and q.conf["verification"] == Conf.HIGH   # translated -> High
    assert q.conf["uid"] == Conf.EXACT and q.conf["text"] == Conf.EXACT
    assert r.report["unclaimed_fields"] == []


def test_profile_yaml_roundtrip():
    prof = Profile.from_yaml((ROOT / "profiles/doors_csv.yaml").read_text())
    again = Profile.from_yaml(prof.to_yaml())
    assert again.fields.keys() == prof.fields.keys() and again.where == prof.where and again.namespace == prof.namespace


def test_doors_profile_filters_headings_instead_of_rejecting(fx):
    prof = Profile.from_yaml((ROOT / "profiles/doors_csv.yaml").read_text())
    r = ingest(Source(str(fx["doors_csv"])), profile=prof)
    assert len(r.requirements) == 6 and len(r.rejected) == 0
    assert sum(r.report["filtered_out"].values()) == 2 and r.report["invariant_ok"]
    assert r.requirements[0].uid == "REQ-FCS-0101"      # Object Identifier wins over Absolute Number


def test_msosa_reqif_profile(fx):
    prof = Profile.from_yaml((ROOT / "profiles/msosa_reqif.yaml").read_text())
    r = ingest(Source(str(fx["reqif"])), profile=prof)
    assert len(r.requirements) == 6 + 2 and r.requirements[0].fields["verification"] == "Test"
    assert r.requirements[1].extra["_section"] == "Subsystem requirements"   # heading was filtered, but its place in the tree is kept
    assert [(l.kind, l.source_uid, l.target_uid) for l in r.links] == [("derive", "REQ-FCS-0102", "REQ-FCS-0101")]


def test_link_rule_from_a_column(fx):
    prof = Profile.from_yaml("""
profile: csv-links
adapter: tabular
fields:
  uid: {from: "Requirement ID"}
  text: {from: "Statement"}
links:
  - {kind: derive, from: "Parent ID"}
""")
    r = ingest(Source(str(fx["csv"])), profile=prof)
    got = {(l.source_uid, l.target_uid) for l in r.links}
    assert got == {("REQ-FCS-0102", "REQ-FCS-0101"), ("REQ-FCS-0104", "REQ-FCS-0103")}
    assert all(l.source_mid and l.target_mid for l in r.links)


def test_sysml_nesting_and_comment_safety(fx):
    r = ingest(Source(str(fx["sysml"])))
    by = {q.uid: q for q in r.requirements}
    assert by["REQ-FCS-0104"].parent_mid == by["REQ-FCS-0103"].mid          # nested requirement def
    assert "ground station within 200 ms" in by["REQ-FCS-0101"].norm_text     # wrapped doc comment re-joined
    assert r.report["fidelity"] == "parsed"


def test_extracted_sources_are_flagged_for_human_verification(fx):
    for k in ("docx", "pdf"):
        r = ingest(Source(str(fx[k])))
        assert r.report["fidelity"] == "extracted" and any("EXTRACTED" in w for w in r.report["warnings"])
        by = {q.uid: q for q in r.requirements}
        assert by["REQ-PWR-0201"].fields.get("verification") == "Analysis"    # table column survived
        assert any(q.uid_synthetic for q in r.requirements)                    # the un-numbered sentence, labelled as such
        assert all(q.conf["uid"] == Conf.LOW for q in r.requirements if q.uid_synthetic)


def test_sql_guard():
    assert check_query("SELECT a FROM t;") == "SELECT a FROM t"
    for bad in ("DROP TABLE t", "SELECT 1; DELETE FROM t", "UPDATE t SET a=1", "PRAGMA writable_schema=1", "WITH x AS (SELECT 1) DELETE FROM t"):
        with pytest.raises(ValueError):
            check_query(bad)


def test_sql_database_is_opened_read_only(fx):
    from sqlalchemy import text
    from reqin.adapters.sql import SqlAdapter
    src = Source("sqlite:///" + str(fx["sqlite"]), {"query": "SELECT 1"})
    with SqlAdapter()._engine(src).connect() as con:
        with pytest.raises(Exception):
            con.execute(text("INSERT INTO reqs (req_uid) VALUES ('x')"))


def test_mdzip_is_recognised_but_honestly_unimplemented(tmp_path):
    import zipfile
    p = tmp_path / "x.mdzip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("dummy", "x")
    ad = pick_adapter(Source(str(p)))
    assert ad.name == "mdzip"
    with pytest.raises(NotImplementedError, match="ReqIF"):
        list(ad.read(Source(str(p))))


def test_csv_windows_encoding_semicolons_and_duplicate_headers(tmp_path):
    p = tmp_path / "legacy.csv"
    p.write_bytes("Req ID;Statement;Note;Note\nR-1;The unit shall operate at 85° C – café mode.;first;second\n".encode("cp1252"))
    r = ingest(Source(str(p)))
    q = r.requirements[0]
    assert q.uid == "R-1" and "85° C" in q.text and "café" in q.text
    assert "second" in str(q.extra) + str(q.fields)


def test_reqifz_archive_is_read_like_a_reqif(fx, tmp_path):
    import zipfile
    z = tmp_path / "bundle.reqifz"
    with zipfile.ZipFile(z, "w") as f:
        f.write(fx["reqif"], "inner/reqs.reqif")
    r = ingest(Source(str(z)), profile=Profile.from_yaml((ROOT / "profiles/msosa_reqif.yaml").read_text()))
    assert len(r.requirements) == 8 and r.report["adapter"] == "reqif"


def test_the_no_record_vanishes_check_can_actually_fail():
    from reqin.ingest import invariant_holds
    assert invariant_holds(5, 3, 1, {"container not selected: X": 1})
    assert not invariant_holds(5, 3, 1, {})                  # one record unaccounted for
    assert not invariant_holds(5, 3, 1, {"row filter (where) did not match": 2})     # more accounted for than read
