"""A .reqifz can hold several .reqif files (a DOORS Next export is grouped by module). Everything here is made up."""
from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from reqin import Profile, Source, ingest
from reqin.adapters import reqif_adapter
from reqin.adapters.reqif_adapter import ReqIFAdapter

ROOT = Path(__file__).parent.parent
PROFILE = Profile.from_yaml((ROOT / "profiles/msosa_reqif.yaml").read_text())


def _bundle(path: Path, fx, names: list[str], second_uids: str = "X") -> Path:
    first = Path(fx["reqif"]).read_text(encoding="utf-8")
    # a second module: the same SPEC-OBJECT identifiers (so they clash) but other requirement ids and text
    second = first
    for part in ("REQ-FCS", "REQ-PWR", "REQ-MC"):                      # not "REQ-", which would also rename the root element REQ-IF
        second = second.replace(part, f"{second_uids}{part}")
    second = second.replace("shall", "shall also")
    with zipfile.ZipFile(path, "w") as z:
        for i, n in enumerate(names):
            z.writestr(n, first if i == 0 else second)
    return path


def test_every_reqif_in_an_archive_is_read_and_a_clashing_identifier_does_not_replace_another(fx, tmp_path):
    z = _bundle(tmp_path / "grouped.reqifz", fx, ["module_b/b.reqif", "module_a/a.reqif"])          # sorted by name: a.reqif is read first
    ad = ReqIFAdapter()
    recs = [x for x in ad.read(Source(str(z))) if hasattr(x, "fields")]
    assert len(recs) == 18 and len({r.native_id for r in recs}) == 18                                  # 9 spec objects in each file (8 requirements and a heading)
    assert sum(1 for r in recs if "::" in r.native_id) == 9 and all(r.native_id.startswith("module_b/b.reqif::") for r in recs if "::" in r.native_id)
    assert {r.fields["_file"] for r in recs} == {"module_a/a.reqif", "module_b/b.reqif"}
    r = ingest(Source(str(z)), profile=PROFILE)
    assert r.report["invariant_ok"] and len(r.requirements) == 16 and {q.uid for q in r.requirements} >= {"REQ-FCS-0101", "XREQ-FCS-0101"}
    assert any("2 .reqif files read" in n for n in ad.discover(Source(str(z))).notes)
    # the parent of every object is the heading of ITS OWN file, even though both headings have the identifier so-h1
    assert {r.parent_native_id for r in recs if r.fields["_file"] == "module_b/b.reqif" and r.parent_native_id} == {"module_b/b.reqif::so-h1"}
    assert {r.parent_native_id for r in recs if r.fields["_file"] == "module_a/a.reqif" and r.parent_native_id} == {"so-h1"}


def test_an_archive_with_no_reqif_or_too_much_in_it_is_refused(fx, tmp_path, monkeypatch):
    empty = tmp_path / "empty.reqifz"
    with zipfile.ZipFile(empty, "w") as z:
        z.writestr("readme.txt", "no ReqIF here")
    with pytest.raises(ValueError, match="no .reqif file inside"):
        list(ReqIFAdapter().read(Source(str(empty))))
    z2 = _bundle(tmp_path / "ok.reqifz", fx, ["a.reqif"])
    monkeypatch.setattr(reqif_adapter, "MAX_UNCOMPRESSED", 1000)
    with pytest.raises(ValueError, match="refusing to expand it"):
        list(ReqIFAdapter().read(Source(str(z2))))
    monkeypatch.setattr(reqif_adapter, "MAX_UNCOMPRESSED", 1 << 30)
    monkeypatch.setattr(reqif_adapter, "MAX_MEMBERS", 1)
    with pytest.raises(ValueError, match="refusing to expand it"):
        list(ReqIFAdapter().read(Source(str(_bundle(tmp_path / "two.reqifz", fx, ["a.reqif", "b.reqif"])))))


def test_a_member_name_cannot_make_the_reader_write_outside_its_own_folder(fx, tmp_path):
    z = tmp_path / "sneaky.reqifz"
    with zipfile.ZipFile(z, "w") as f:
        f.write(fx["reqif"], "../../escape.reqif")
    recs = [x for x in ReqIFAdapter().read(Source(str(z))) if hasattr(x, "fields")]
    assert len(recs) == 9 and not (tmp_path / "escape.reqif").exists() and not (tmp_path.parent / "escape.reqif").exists()


def test_a_file_that_is_not_reqif_says_what_to_check(tmp_path):
    p = tmp_path / "broken.reqif"
    p.write_text("<REQ-IF><nonsense></REQ-IF>")
    with pytest.raises(ValueError, match=r"could not read broken\.reqif as ReqIF .*Installed reqif library: .*0\.0\.48 or later"):
        list(ReqIFAdapter().read(Source(str(p))))


def test_a_reqif_with_an_xhtml_comment_inside_a_value_is_read(fx, tmp_path):
    """DOORS Next exports can carry <!-- x-tinymce/html --> inside XHTML values; the reqif library crashed on it before 0.0.48."""
    text = Path(fx["reqif"]).read_text(encoding="utf-8")
    assert "<xhtml:div><xhtml:p>" in text
    p = tmp_path / "commented.reqif"
    p.write_text(text.replace("<xhtml:div><xhtml:p>", "<xhtml:div><!-- x-tinymce/html --><xhtml:p>", 1), encoding="utf-8")
    r = ingest(Source(str(p)), profile=PROFILE)
    assert len(r.requirements) == 8 and r.report["invariant_ok"]


def test_a_doctype_or_entity_is_refused_even_behind_a_long_comment_and_a_comment_alone_is_fine(fx, tmp_path):
    text = Path(fx["reqif"]).read_text(encoding="utf-8")
    decl, root = text.split("?>", 1)
    plain = tmp_path / "plain.reqif"
    plain.write_text(decl + '?><!DOCTYPE x [<!ENTITY a "aaaa">]>' + root, encoding="utf-8")
    hidden = tmp_path / "hidden.reqif"
    hidden.write_text(decl + "?><!--" + "x" * 70000 + '--><!DOCTYPE x [<!ENTITY a "aaaa">]>' + root, encoding="utf-8")
    for f in (plain, hidden):
        with pytest.raises(ValueError, match="DOCTYPE or ENTITY"):
            list(ReqIFAdapter().read(Source(str(f))))
    ok = tmp_path / "ok.reqif"
    ok.write_text(decl + "?><!--" + "x" * 70000 + "-->" + root, encoding="utf-8")
    assert sum(1 for x in ReqIFAdapter().read(Source(str(ok))) if hasattr(x, "fields")) == 9
