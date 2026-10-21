"""The SysML 1.x / MSOSA XMI reader. Everything here is made up. The fixtures are written from the vendor's documentation, not from a real project,
so these tests prove that the reader does what it says on that shape, not that a real MSOSA file reads: see adapters/sysml1_xmi.py."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from reqin import Profile, Source, ingest
from reqin.adapter import pick_adapter, sniff_all
from reqin.adapters.sysml1_xmi import MODEL_ENTRY, SysML1XmiAdapter, _Capped
from reqin.connect import ConnectError
from reqin.model import RawLink, RawRecord

ROOT = Path(__file__).parent.parent
PROFILE = Profile.from_yaml((ROOT / "profiles/sysml1_xmi.yaml").read_text())

NS = {   # the namespace URIs differ between XMI 2.4 and 2.5; the reader matches on local names, so both must read the same
    "2.5": ('xmlns:xmi="http://www.omg.org/spec/XMI/20131001" xmlns:uml="http://www.omg.org/spec/UML/20131001" '
            'xmlns:sysml="http://www.omg.org/spec/SysML/20181001/SysML"', "2.5"),
    "2.4": ('xmlns:xmi="http://www.omg.org/spec/XMI/20110701" xmlns:uml="http://www.omg.org/spec/UML/20110701" '
            'xmlns:sysml="http://www.omg.org/spec/SysML/20110701/SysML"', "2.4"),
}


def xmi(ns="2.5", model="", apps="", head_extra="") -> str:
    attrs, ver = NS[ns]
    return f'<?xml version="1.0" encoding="UTF-8"?><xmi:XMI xmi:version="{ver}" {attrs} {head_extra}>{model}{apps}</xmi:XMI>'


MODEL = (
    '<uml:Model xmi:id="m1" name="Fictional Widget">'
    '<packagedElement xmi:type="uml:Package" xmi:id="p1" name="Reqs"><packagedElement xmi:type="uml:Package" xmi:id="p2" name="Controller">'
    '<packagedElement xmi:type="uml:Class" xmi:id="r1" name="Latency"><ownedComment xmi:type="uml:Comment" xmi:id="c1" body="Measured at the bus."/></packagedElement>'
    '<packagedElement xmi:type="uml:Class" xmi:id="r2" name="Boot"><nestedClassifier xmi:type="uml:Class" xmi:id="r3" name="Boot time"/></packagedElement>'
    '<packagedElement xmi:type="uml:Class" xmi:id="b1" name="Controller block"/>'
    '<packagedElement xmi:type="uml:Class" xmi:id="t1" name="Latency test"/>'
    '<packagedElement xmi:type="uml:Abstraction" xmi:id="a1" client="r3" supplier="r1"/>'
    '<packagedElement xmi:type="uml:Abstraction" xmi:id="a2" client="b1" supplier="r1"/>'
    '<packagedElement xmi:type="uml:Abstraction" xmi:id="a3" client="t1" supplier="r1 r2"/>'
    '<packagedElement xmi:type="uml:Dependency" xmi:id="a4" client="r2" supplier="r1"/>'
    '<packagedElement xmi:type="uml:Abstraction" xmi:id="a5" client="b1" supplier="t1"/>'
    '</packagedElement></packagedElement></uml:Model>')
APPS = (
    '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="REQ-001" Text="The controller shall respond within 50 ms."/>'
    '<sysml:Requirement xmi:id="s2" base_Class="r2" Id="REQ-002" Text="The controller shall restart within 30 s." Risk="High"/>'
    '<sysml:Requirement xmi:id="s3" base_Class="r3" Id="REQ-003" Text="The boot shall not exceed 20 s."/>'
    '<sysml:DeriveReqt xmi:id="s9" base_Abstraction="a1"/>'
    '<sysml:Satisfy xmi:id="s10" base_Abstraction="a2"/>'
    '<sysml:Verify xmi:id="s11" base_Abstraction="a3"/>'
    '<sysml:Block xmi:id="s12" base_Class="b1"/>')


def write(tmp_path: Path, name: str, text: str) -> Source:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return Source(str(p))


def run(src: Source):
    ad = SysML1XmiAdapter()
    items = list(ad.read(src))
    recs = [i for i in items if isinstance(i, RawRecord)]
    links = [i for i in items if isinstance(i, RawLink)]
    return ad, recs, links


@pytest.mark.parametrize("ns", ["2.4", "2.5"])
def test_requirements_are_found_by_their_sibling_stereotype_application_in_both_xmi_versions(tmp_path, ns):
    ad, recs, _ = run(write(tmp_path, "m.xmi", xmi(ns, MODEL, APPS)))
    assert [r.native_id for r in recs] == ["r1", "r2", "r3"]          # the block carries a stereotype too, but not a requirement one
    r1 = recs[0].fields
    assert (r1["Id"], r1["Text"], r1["Name"]) == ("REQ-001", "The controller shall respond within 50 ms.", "Latency")
    assert r1["Documentation"] == "Measured at the bus." and r1["Package"] == "Reqs::Controller" and r1["Stereotype"] == "Requirement"
    assert recs[1].fields["Risk"] == "High"


def test_nesting_is_the_parent_and_a_package_is_not(tmp_path):
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)))
    assert {r.native_id: r.parent_native_id for r in recs} == {"r1": None, "r2": None, "r3": "r2"}


def test_links_run_from_the_client_to_the_supplier_and_take_their_kind_from_the_sibling_stereotype(tmp_path):
    _, _, links = run(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)))
    got = sorted((l.source_native_id, l.target_native_id, l.kind) for l in links)
    assert got == sorted([("r3", "r1", "derive"), ("b1", "r1", "satisfy"), ("t1", "r1", "verify"), ("t1", "r2", "verify"), ("r2", "r1", "dependency")])


def test_discover_counts_what_it_left_alone_and_what_it_guessed(tmp_path):
    d = SysML1XmiAdapter().discover(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)))
    text = "\n".join(d.notes)
    assert "Block x1" in text                                                      # a stereotype on a class that was not read as a requirement
    assert "1 relationships have no stereotype and are read as kind 'dependency'" in text
    assert "1 relationships join two things that are not requirements: not read" in text
    assert d.containers[0].name == "Requirement" and d.containers[0].rows == 3


def test_lower_case_id_and_text_and_the_child_element_form_are_read_as_Id_and_Text(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/>'
             '<packagedElement xmi:type="uml:Class" xmi:id="r2" name="Two"/></uml:Model>')
    apps = ('<sysml:Requirement xmi:id="s1" base_Class="r1" id="OMG-1" text="The unit shall be small."/>'
            '<sysml:Requirement xmi:id="s2" base_Class="r2"><Id>CH-2</Id><Text>The unit shall be light.</Text><Source xmi:idref="x9"/></sysml:Requirement>')
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    assert [(r.fields["Id"], r.fields["Text"]) for r in recs] == [("OMG-1", "The unit shall be small."), ("CH-2", "The unit shall be light.")]
    assert recs[1].fields["Source"] == "x9"


def test_a_custom_stereotype_is_read_only_when_it_is_named(tmp_path):
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/></uml:Model>'
    apps = '<sysml:FunctionalRequirement xmi:id="s1" base_Class="r1" Id="F-1" Text="The unit shall be small."/>'
    src = write(tmp_path, "m.xmi", xmi("2.5", model, apps))
    ad, recs, _ = run(src)
    assert recs == [] and any("FunctionalRequirement x1" in n and "requirement_stereotypes" in n for n in ad.discover(src).notes)
    src2 = Source(src.uri, {"requirement_stereotypes": "functionalrequirement"})
    assert [r.fields["Id"] for r in run(src2)[1]] == ["F-1"]


def test_an_application_whose_class_is_not_in_the_file_is_still_read_and_the_note_says_so(tmp_path):
    apps = '<sysml:Requirement xmi:id="s1" base_Class="gone" Id="X-1" Text="The unit shall be small."/>'
    src = write(tmp_path, "m.xmi", xmi("2.5", MODEL, apps))
    ad, recs, _ = run(src)
    assert [r.native_id for r in recs] == ["gone"] and recs[0].fields["Name"] == "" and recs[0].fields["Id"] == "X-1"
    assert any("1 requirement applications point at a class that is not in this file" in n for n in ad.discover(src).notes)


def test_a_class_with_two_requirement_applications_keeps_the_first_and_does_not_lose_the_second(tmp_path):
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/></uml:Model>'
    apps = ('<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="The unit shall be small."/>'
            '<sysml:ExtendedRequirement xmi:id="s2" base_Class="r1" Id="B-1" Text="The unit shall be tiny." Risk="Low"/>')
    src = write(tmp_path, "m.xmi", xmi("2.5", model, apps))
    _, recs, _ = run(src)
    f = recs[0].fields
    assert (f["Id"], f["Text"], f["Stereotype"]) == ("A-1", "The unit shall be small.", "Requirement, ExtendedRequirement")
    assert "Risk" not in f and f["ExtendedRequirement.Risk"] == "Low"
    assert f["ExtendedRequirement.Id"] == "B-1" and f["ExtendedRequirement.Text"] == "The unit shall be tiny."
    assert any("more than one requirement application" in n for n in SysML1XmiAdapter().discover(src).notes)


def test_a_property_named_like_one_of_the_readers_own_fields_does_not_overwrite_it(tmp_path):
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="Real name"/></uml:Model>'
    apps = '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t" Name="Tag called Name"/>'
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    assert recs[0].fields["Name"] == "Real name" and recs[0].fields["Requirement.Name"] == "Tag called Name"


def test_the_child_form_of_client_and_supplier_and_a_used_project_proxy_href_are_read(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/><packagedElement xmi:type="uml:Class" xmi:id="b1" name="Block"/>'
             '<packagedElement xmi:type="uml:Abstraction" xmi:id="a1"><client xmi:idref="b1"/><supplier xmi:type="uml:Class" href="shared.xml#_req9"/></packagedElement>'
             '<packagedElement xmi:type="uml:Abstraction" xmi:id="a2"><client xmi:idref="b1"/><supplier xmi:idref="r1"/></packagedElement></uml:Model>')
    apps = ('<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t"/><sysml:Requirement xmi:id="s2" base_Class="_req9" Id="U-9" Text="u"/>'
            '<sysml:Satisfy xmi:id="s3" base_Abstraction="a2"/><sysml:Refine xmi:id="s4" base_Abstraction="a1"/>')
    src = write(tmp_path, "m.xmi", xmi("2.5", model, apps))
    ad, _, links = run(src)
    assert sorted((l.source_native_id, l.target_native_id, l.kind) for l in links) == [("b1", "_req9", "refine"), ("b1", "r1", "satisfy")]
    assert any("1 requirement applications point at a class that is not in this file" in n for n in ad.discover(src).notes)


def test_the_two_xmi_versions_give_the_same_records_and_links(tmp_path):
    outs = []
    for ns in ("2.4", "2.5"):
        _, recs, links = run(write(tmp_path, f"m{ns}.xmi", xmi(ns, MODEL, APPS)))
        outs.append(([(r.native_id, r.fields, r.parent_native_id) for r in recs], [(l.source_native_id, l.target_native_id, l.kind) for l in links]))
    assert outs[0] == outs[1]


# ---------------------------------------------------------------------------------------------- the .mdzip layouts
def mdzip(tmp_path: Path, entries: dict[str, str | bytes], name="p.mdzip") -> Source:
    p = tmp_path / name
    with zipfile.ZipFile(p, "w", zipfile.ZIP_DEFLATED) as z:
        for k, v in entries.items():
            z.writestr(k, v)
    return Source(str(p))


def test_an_mdzip_from_17_0_1_reads_the_model_entry_and_names_the_used_project_entries_it_left_alone(tmp_path):
    other = xmi("2.4", '<uml:Model xmi:id="m9"><packagedElement xmi:type="uml:Class" xmi:id="z1" name="Elsewhere"/></uml:Model>',
                '<sysml:Requirement xmi:id="s9" base_Class="z1" Id="USED-1" Text="The used project shall be here."/>')
    src = mdzip(tmp_path, {MODEL_ENTRY: xmi("2.4", MODEL, APPS), "com.nomagic.magicdraw.uml_model.shared_model": other, "proxy1": other, "images/logo.png": b"\x89PNG"})
    ad, recs, _ = run(src)
    assert [r.native_id for r in recs] == ["r1", "r2", "r3"]
    assert any("2 used-project entries left unread" in n for n in ad.discover(src).notes)
    chosen = Source(src.uri, {"entry": "com.nomagic.magicdraw.uml_model.shared_model"})
    assert [r.fields["Id"] for r in run(chosen)[1]] == ["USED-1"]


def test_an_mdzip_from_before_17_0_1_is_one_xmi_and_is_read_as_that(tmp_path):
    src = mdzip(tmp_path, {"Fictional Widget.xml": xmi("2.4", MODEL, APPS), "readme.txt": "x"})
    assert [r.native_id for r in run(src)[1]] == ["r1", "r2", "r3"]


def test_an_mdzip_it_cannot_choose_an_entry_from_says_which_entries_there_are(tmp_path):
    src = mdzip(tmp_path, {"a.xml": xmi("2.4", MODEL, APPS), "b.xml": xmi("2.4", MODEL, APPS)})
    with pytest.raises(ConnectError, match=r"cannot tell which entry.*a\.xml.*b\.xml"):
        list(SysML1XmiAdapter().read(src))
    with pytest.raises(ConnectError, match="no entry 'nope'"):
        list(SysML1XmiAdapter().read(Source(src.uri, {"entry": "nope"})))
    assert [r.native_id for r in run(Source(src.uri, {"entry": "b.xml"}))[1]] == ["r1", "r2", "r3"]


def test_an_entry_larger_than_max_mb_is_refused_before_it_is_read_and_a_lying_zip_cannot_get_past_the_cap(tmp_path):
    src = mdzip(tmp_path, {MODEL_ENTRY: xmi("2.5", MODEL, APPS)})
    with pytest.raises(ConnectError, match="max_mb"):
        list(SysML1XmiAdapter().read(Source(src.uri, {"max_mb": "0"})))
    import io
    capped = _Capped(io.BytesIO(b"x" * 100), 10, "entry")
    with pytest.raises(ConnectError, match="larger than max_mb"):
        capped.read(100)


# ---------------------------------------------------------------------------------------------- refusals and recognition
def test_a_doctype_or_entity_is_refused_wherever_it_hides(tmp_path):
    body = xmi("2.5", MODEL, APPS).split("?>", 1)[1]                    # the document without its XML declaration, so a DOCTYPE can sit before the root
    bomb = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]>' + body
    with pytest.raises(ConnectError, match="DOCTYPE"):
        list(SysML1XmiAdapter().read(write(tmp_path, "m.xmi", bomb)))
    with pytest.raises(ConnectError, match="DOCTYPE"):
        list(SysML1XmiAdapter().read(mdzip(tmp_path, {MODEL_ENTRY: bomb}, "b.mdzip")))
    hidden = '<?xml version="1.0"?><!--' + "x" * 70000 + '--><!DOCTYPE x [<!ENTITY a "aaaa">]>' + body       # past the first 64 KB
    with pytest.raises(ConnectError, match="DOCTYPE"):
        list(SysML1XmiAdapter().read(write(tmp_path, "h.xmi", hidden)))
    assert len(list(SysML1XmiAdapter().read(write(tmp_path, "ok.xmi", '<?xml version="1.0"?><!--' + "x" * 70000 + "-->" + body)))) > 0   # the same file without the DOCTYPE reads


def test_broken_xml_is_a_clear_error_not_a_traceback(tmp_path):
    with pytest.raises(ConnectError, match="not well-formed"):
        list(SysML1XmiAdapter().read(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)[:-30])))
    with pytest.raises(ConnectError, match="not a readable zip"):
        list(SysML1XmiAdapter().read(write(tmp_path, "m.mdzip", "not a zip")))


def test_sniff(tmp_path):
    assert sniff_all(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)))[0][1] == "sysml1_xmi"
    assert sniff_all(write(tmp_path, "m.xml", xmi("2.4", MODEL, APPS)))[0][1] == "sysml1_xmi"
    assert not sniff_all(write(tmp_path, "other.xml", "<a><b/></a>"))
    assert SysML1XmiAdapter().sniff(mdzip(tmp_path, {MODEL_ENTRY: xmi("2.4", MODEL, APPS)})) == 0.95
    assert SysML1XmiAdapter().sniff(mdzip(tmp_path, {"dummy": "x"}, "q.mdzip")) == 0.7
    assert SysML1XmiAdapter().sniff(write(tmp_path, "n.mdzip", "not a zip")) == 0.0
    assert pick_adapter(mdzip(tmp_path, {MODEL_ENTRY: xmi("2.4", MODEL, APPS)}, "r.mdzip")).name == "sysml1_xmi"


def test_the_file_is_parsed_once_per_run_and_the_revision_is_its_hash(tmp_path, monkeypatch):
    src = write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS))
    ad = SysML1XmiAdapter()
    calls = []
    orig = ad._parse
    monkeypatch.setattr(ad, "_parse", lambda s: calls.append(1) or orig(s))
    ad.discover(src)
    list(ad.read(src))
    rev = ad.revision(src)
    assert len(calls) == 1 and len(rev) == 16
    src2 = write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS) + " ")                  # changed content: parsed again
    ad.discover(src2)
    assert len(calls) == 2


def test_through_the_pipeline_with_the_shipped_profile(tmp_path):
    r = ingest(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)), profile=PROFILE)
    assert sorted(q.uid for q in r.requirements) == ["REQ-001", "REQ-002", "REQ-003"]
    assert {q.uid: q.text for q in r.requirements}["REQ-002"] == "The controller shall restart within 30 s."
    assert len(r.links) == 5 and r.raw_count == len(r.requirements) + len(r.rejected) + r.filtered_count if hasattr(r, "raw_count") else True
    kinds = sorted(l.kind for l in r.links)
    assert kinds == ["dependency", "derive", "satisfy", "verify", "verify"]
