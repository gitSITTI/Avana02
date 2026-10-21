"""SysML v2 textual notation read from ONE file or from a FOLDER of .sysml files (what the desktop export writes). Everything here is made up."""
from __future__ import annotations

from pathlib import Path

import pytest

from reqin import Profile, Source, ingest, pick_adapter
from reqin.adapters.sysml_text import SysMLTextAdapter
from reqin.testing import check_adapter

PROFILE = Profile.from_yaml("""
profile: sysml-text-test
adapter: sysml_text
namespace: DEMO-SYSML
fields:
  uid:  {from: ["shortName", "name"]}
  text: {from: "doc"}
""")


@pytest.fixture
def folder(tmp_path):
    d = tmp_path / "export"
    (d / "sub").mkdir(parents=True)
    # two packages that both define "Speed": a plain reference to it is ambiguous, a qualified one is not
    (d / "Requirements.sysml").write_text("""package Requirements {
    requirement def <'REQ-1'> Speed { doc /* The vehicle shall not exceed 50 km/h. */ }
    requirement def <'REQ-2'> Mass { doc /* The vehicle shall weigh at most 800 kg. */ }
}
""")
    (d / "sub" / "Safety.sysml").write_text("""package Safety {
    requirement def <'REQ-3'> Speed { doc /* The vehicle shall stop within 3 s of the brake command. */ }
    part def Controller;
    part c : Controller {
        satisfy requirement Speed by c;
        satisfy requirement Requirements::Speed by c;
        satisfy requirement Mass by c;
        satisfy requirement Missing by c;
    }
}
""")
    (d / "ignored.txt").write_text("package NotRead { requirement def X { doc /* The unit shall be ignored. */ } }")
    return d


def test_a_folder_of_sysml_files_is_read_as_one_source(folder):
    assert pick_adapter(Source(str(folder))).name == "sysml_text"
    r = check_adapter(SysMLTextAdapter, Source(str(folder)), PROFILE, expect_ok=3)
    assert {q.uid for q in r.requirements} == {"REQ-1", "REQ-2", "REQ-3"}
    locs = {q.uid: q.ref.locator for q in r.requirements}
    assert locs["REQ-1"].startswith("Requirements.sysml:L") and locs["REQ-3"].startswith("sub/Safety.sysml:L")      # the file is part of where it came from
    assert next(q for q in r.requirements if q.uid == "REQ-3").extra["file"] == "sub/Safety.sysml"


def test_a_reference_is_resolved_only_when_it_is_unambiguous(folder):
    ad = SysMLTextAdapter()
    src = Source(str(folder))
    sat = [(x.source_native_id, x.target_native_id) for x in ad.read(src) if not hasattr(x, "fields") and x.kind == "satisfy"]
    targets = [b for _, b in sat]
    assert targets.count("Requirements::Speed") == 1                 # a qualified name that is one definition: resolved
    assert targets.count("Speed") == 1                               # the plain name defined in two packages: kept as written, never guessed
    assert "Requirements::Mass" in targets                           # a plain name defined once: resolved to its qualified name
    assert "Missing" in targets                                      # an unknown name: kept as written
    assert all(a == "Safety::c" or a == "c" or a.endswith("::c") for a, _ in sat)
    notes = ad.discover(src).notes
    assert any("2 .sysml files read" in n for n in notes)
    assert any("1 references name a definition that exists in more than one package" in n and "Speed" in n for n in notes)


def test_a_qualified_name_defined_twice_keeps_both_under_different_ids(tmp_path):
    (tmp_path / "a.sysml").write_text("package P { requirement def <'A'> Same { doc /* The unit shall start. */ } }")
    (tmp_path / "b.sysml").write_text("package P { requirement def <'B'> Same { doc /* The unit shall stop. */ } }")
    ad = SysMLTextAdapter()
    ids = [x.native_id for x in ad.read(Source(str(tmp_path))) if hasattr(x, "fields")]
    assert ids == ["P::Same", "P::Same#2"]
    r = ingest(Source(str(tmp_path)), profile=PROFILE)
    assert {q.uid for q in r.requirements} == {"A", "B"} and r.report["invariant_ok"]
    assert any("defined more than once" in n for n in ad.discover(Source(str(tmp_path))).notes)


def test_an_empty_folder_and_a_folder_of_other_files_say_so(tmp_path):
    d = tmp_path / "none"
    d.mkdir()
    (d / "notes.txt").write_text("hello")
    assert SysMLTextAdapter().sniff(Source(str(d))) == 0.0
    with pytest.raises(ValueError, match="no .sysml file"):
        list(SysMLTextAdapter().read(Source(str(d))))


def test_the_revision_of_a_folder_changes_when_any_file_changes(folder):
    ad = SysMLTextAdapter()
    a = ad.revision(Source(str(folder)))
    (folder / "sub" / "Safety.sysml").write_text((folder / "sub" / "Safety.sysml").read_text() + "\n// edited\n")
    assert ad.revision(Source(str(folder))) != a and len(a) == 16


def test_symbolic_links_and_hidden_folders_are_not_followed(tmp_path):
    d = tmp_path / "e"
    (d / ".hidden").mkdir(parents=True)
    (d / ".hidden" / "h.sysml").write_text("package H { requirement def <'H1'> H { doc /* The hidden unit shall hide. */ } }")
    (d / "real.sysml").write_text("package R { requirement def <'R1'> R { doc /* The real unit shall be read. */ } }")
    outside = tmp_path / "outside.sysml"
    outside.write_text("package O { requirement def <'O1'> O { doc /* The outside unit shall not be read. */ } }")
    (d / "link.sysml").symlink_to(outside)
    ids = [x.native_id for x in SysMLTextAdapter().read(Source(str(d))) if hasattr(x, "fields")]
    assert ids == ["R::R"]
