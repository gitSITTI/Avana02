"""The `sql` adapter's parent column, links query and query files, and the Enterprise Architect query pack in connectors/ea/.

The EA tests run the shipped .sql files against a tiny MADE-UP SQLite database whose tables are shaped like what the pack expects (t_object, t_connector,
t_package, with the column names written from memory). That proves the pack and the adapter agree with each other. It proves NOTHING about a real
Enterprise Architect repository: a real one may name a column differently, which is why the pack tells the user to check the columns first."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from reqin import Profile, Source, ingest
from reqin.adapter import sniff_all
from reqin.adapters.sql import MAX_QUERY_FILE, SqlAdapter, check_query, query_text, strip_sql_comments

ROOT = Path(__file__).parent.parent
PACK = ROOT / "connectors" / "ea"
EA_PROFILE = Profile.from_yaml((ROOT / "profiles/ea_sql.yaml").read_text())

# (Object_ID, Object_Type, Name, Alias, Note, Package_ID, Stereotype, ea_guid, Status, ParentID)
OBJECTS = [
    (1, "Requirement", "Battery life", "WID-SYS-0001", "<b>The widget shall</b> run for 8 hours.", 10, "functionalRequirement", "{G-0001}", "Approved", 0),
    (2, "Requirement", "Standby life", "WID-SYS-0002", "The widget shall hold its charge for 30 days in standby.", 10, "", "{G-0002}", "Draft", 1),
    (3, "Requirement", "Charge time", "", "The widget shall charge fully in under 3 hours.", 11, None, "{G-0003}", "Draft", 0),
    (4, "Class", "Battery pack", "", "A class, not a requirement.", 11, "", "{G-0004}", "", 0),
    (5, "Requirement", "Self parent", "WID-SYS-0005", "The widget shall not be its own parent.", 10, "", "{G-0005}", "", 5),
    (6, "Requirement", "Orphan child", "WID-SYS-0006", "The widget shall survive a parent that is not a requirement.", 10, "", "{G-0006}", "", 4),
    (7, "Block", "Charger", "", "A block.", 11, "", "{G-0007}", "", 0),
]
PACKAGES = [(10, "System requirements", 0), (11, "Power", 10)]
# (Connector_ID, Connector_Type, Name, Stereotype, Start_Object_ID, End_Object_ID, ea_guid)
CONNECTORS = [
    (1, "Abstraction", "", "satisfy", 7, 3, "{C-0001}"),        # a block satisfies a requirement: the block is outside the import
    (2, "Abstraction", "", "deriveReqt", 2, 1, "{C-0002}"),     # requirement derived from requirement: both inside
    (3, "Dependency", "", "", 7, 1, "{C-0003}"),                # no stereotype: the connector type is the kind
    (4, "Association", "", "", 7, 4, "{C-0004}"),               # neither end a requirement: not read
    (5, "Abstraction", "", "satisfy", 7, 99, "{C-0005}"),       # end 99 does not exist: the join drops it
]


@pytest.fixture
def ea_db(tmp_path):
    p = tmp_path / "ea.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE t_object (Object_ID INTEGER PRIMARY KEY, Object_Type TEXT, Name TEXT, Alias TEXT, Note TEXT, Package_ID INTEGER, Stereotype TEXT, "
                "ea_guid TEXT, Status TEXT, Phase TEXT, Version TEXT, Author TEXT, ModifiedDate TEXT, ParentID INTEGER)")
    for o in OBJECTS:
        con.execute("INSERT INTO t_object (Object_ID, Object_Type, Name, Alias, Note, Package_ID, Stereotype, ea_guid, Status, ParentID) VALUES (?,?,?,?,?,?,?,?,?,?)", o)
    con.execute("CREATE TABLE t_package (Package_ID INTEGER PRIMARY KEY, Name TEXT, Parent_ID INTEGER)")
    con.executemany("INSERT INTO t_package VALUES (?,?,?)", PACKAGES)
    con.execute("CREATE TABLE t_connector (Connector_ID INTEGER PRIMARY KEY, Connector_Type TEXT, Name TEXT, Stereotype TEXT, Start_Object_ID INTEGER, "
                "End_Object_ID INTEGER, ea_guid TEXT)")
    con.executemany("INSERT INTO t_connector VALUES (?,?,?,?,?,?,?)", CONNECTORS)
    con.commit()
    con.close()
    return p


def ea_src(db: Path, **extra) -> Source:
    o = {"query_file": str(PACK / "requirements.sql"), "links_query_file": str(PACK / "links.sql"), "id_column": "guid", "parent_column": "parent_guid"}
    o.update(extra)
    return Source(f"sqlite:///{db}", o)


def ea_result(db: Path, **extra):
    return ingest(ea_src(db, **extra), EA_PROFILE)


# ------------------------------------------------------------------------------------------------ the EA pack
def test_the_ea_pack_reads_requirement_elements_and_nothing_else(ea_db):
    r = ea_result(ea_db)
    assert sorted(q.uid for q in r.requirements) == sorted(["WID-SYS-0001", "WID-SYS-0002", "{G-0003}", "WID-SYS-0005", "WID-SYS-0006"])   # class and block are not read
    assert r.report["raw_records"] == 5 and r.report["requirements"] == 5 and r.report["rejected"] == 0 and r.report["invariant_ok"]


def test_an_element_with_no_alias_gets_its_guid_as_id_and_the_others_their_alias(ea_db):
    by = {q.uid: q for q in ea_result(ea_db).requirements}
    assert by["{G-0003}"].uid_synthetic is False                      # a GUID is a real, stable id; only a locator-built id is synthetic
    assert "WID-SYS-0001" in by


def test_the_statement_comes_from_notes_with_markup_removed(ea_db):
    by = {q.uid: q for q in ea_result(ea_db).requirements}
    assert by["WID-SYS-0001"].text == "The widget shall run for 8 hours."
    assert by["WID-SYS-0002"].text.startswith("The widget shall hold its charge")


def test_nesting_becomes_hierarchy_and_a_self_or_non_requirement_parent_does_not(ea_db):
    r = ea_result(ea_db)
    by = {q.uid: q for q in r.requirements}
    assert by["WID-SYS-0002"].parent_mid == by["WID-SYS-0001"].mid        # ParentID 1
    assert by["WID-SYS-0001"].parent_mid in (None, "")                    # ParentID 0 joins no row, so it has no parent
    assert by["WID-SYS-0005"].parent_mid in (None, "")                    # its own parent: ignored, never a cycle
    assert by["WID-SYS-0006"].parent_mid in (None, "")                    # parent 4 is a class, not in the import: no parent here, and nothing crashes


def test_connectors_become_links_with_the_requirement_as_target(ea_db):
    r = ea_result(ea_db)
    got = sorted((l.source_uid, l.target_uid, l.kind) for l in r.links)
    assert got == sorted([
        ("{G-0007}", "{G-0003}", "satisfy"),          # the block stays under its GUID, the requirement under its id
        ("WID-SYS-0002", "WID-SYS-0001", "deriveReqt"),
        ("{G-0007}", "WID-SYS-0001", "Dependency"),   # no stereotype -> EA's connector type
    ])


def test_a_link_with_a_requirement_at_neither_end_or_an_unknown_end_is_not_read(ea_db):
    r = ea_result(ea_db)
    assert not [l for l in r.links if l.target_uid in ("{G-0004}", "{G-0099}") or l.ref.locator in ("{C-0004}", "{C-0005}")]


def test_every_link_carries_the_connectors_guid_as_its_locator(ea_db):
    refs = {l.ref.locator for l in ea_result(ea_db).links}
    assert refs == {"{C-0001}", "{C-0002}", "{C-0003}"}


def test_links_to_things_outside_the_import_are_counted_not_hidden(ea_db):
    r = ea_result(ea_db)
    assert any("2 links point outside this import" in w for w in r.report["warnings"]), r.report["warnings"]


def test_the_pack_without_the_links_file_still_reads_the_requirements(ea_db):
    src = ea_src(ea_db)
    del src.options["links_query_file"]
    r = ingest(src, EA_PROFILE)
    assert len(r.requirements) == 5 and not r.links


def test_the_pack_files_pass_the_read_only_guard_with_their_comments_in_them():
    for fn in ("requirements.sql", "links.sql"):
        text = (PACK / fn).read_text(encoding="utf-8")
        assert "--" in text                                            # they do explain themselves ...
        q = check_query(text)
        assert q.upper().startswith("SELECT") and "--" not in q        # ... and the comments are gone before the guard looks


def test_the_pack_says_its_column_names_are_unverified_and_tells_the_user_how_to_check():
    for fn in ("requirements.sql", "links.sql"):
        t = (PACK / fn).read_text(encoding="utf-8").lower()
        assert "memory" in t and "not checked" in t or "from memory" in t, fn
    assert "where 1 = 0" in (PACK / "requirements.sql").read_text(encoding="utf-8").lower()


def test_discover_names_the_columns_and_warns_when_the_id_or_parent_column_is_not_one_of_them(ea_db):
    d = SqlAdapter().discover(ea_src(ea_db, id_column="nope", parent_column="nada"))
    cols = [f.name for f in d.containers[0].fields]
    assert "guid" in cols and "parent_guid" in cols
    assert any("WARNING id_column 'nope'" in n for n in d.notes) and any("WARNING parent_column 'nada'" in n for n in d.notes)


# ------------------------------------------------------------------------------------------ the generic adapter
def make_db(tmp_path, rows, links=None):
    p = tmp_path / "g.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE r (id TEXT, up TEXT, txt TEXT)")
    con.executemany("INSERT INTO r VALUES (?,?,?)", rows)
    con.execute("CREATE TABLE l (a TEXT, b TEXT, k TEXT, why TEXT)")
    con.executemany("INSERT INTO l VALUES (?,?,?,?)", links or [])
    con.commit()
    con.close()
    return p


GENERIC = Profile.from_yaml("profile: g\nadapter: sql\nnamespace: G\nfields:\n  uid: {from: [id]}\n  text: {from: [txt]}\n")
ROWS = [("A", None, "The widget shall be red."), ("B", "A", "The widget shall be a bright red."), ("C", "", "The widget shall be blue.")]


def test_parent_column_gives_hierarchy_and_empty_or_null_means_none(tmp_path):
    db = make_db(tmp_path, ROWS)
    r = ingest(Source(f"sqlite:///{db}", {"query": "SELECT * FROM r", "id_column": "id", "parent_column": "up"}), GENERIC)
    by = {q.uid: q for q in r.requirements}
    assert by["B"].parent_mid == by["A"].mid and not by["A"].parent_mid and not by["C"].parent_mid


def test_a_parent_column_that_is_not_there_is_a_loud_note_not_a_silent_flat_list(tmp_path):
    db = make_db(tmp_path, ROWS)
    d = SqlAdapter().discover(Source(f"sqlite:///{db}", {"query": "SELECT * FROM r", "id_column": "id", "parent_column": "typo"}))
    assert any("WARNING parent_column 'typo'" in n for n in d.notes)


def test_links_query_kind_defaults_to_trace_and_half_empty_rows_are_skipped_and_counted(tmp_path):
    db = make_db(tmp_path, ROWS, [("B", "A", "derive", "row-x"), ("C", "A", None, None), ("", "A", "derive", None), ("C", None, "derive", None)])
    opts = {"query": "SELECT * FROM r", "id_column": "id", "links_query": "SELECT a AS source, b AS target, k AS kind, why AS ref FROM l"}
    r = ingest(Source(f"sqlite:///{db}", opts), GENERIC)
    assert sorted((l.source_uid, l.target_uid, l.kind) for l in r.links) == [("B", "A", "derive"), ("C", "A", "trace")]
    assert next(l for l in r.links if l.source_uid == "B").ref.locator == "row-x"
    d = SqlAdapter().discover(Source(f"sqlite:///{db}", opts))
    assert any("2 have an empty source or target" in n for n in d.notes), d.notes


def test_a_links_query_without_source_and_target_columns_is_refused_with_what_it_returned(tmp_path):
    db = make_db(tmp_path, ROWS, [("B", "A", "derive", None)])
    with pytest.raises(ValueError, match=r"columns source and target.*\['a', 'b'\]"):
        SqlAdapter().discover(Source(f"sqlite:///{db}", {"query": "SELECT * FROM r", "links_query": "SELECT a, b FROM l"}))


@pytest.mark.parametrize("bad", ["DELETE FROM l", "SELECT 1; DROP TABLE l", "UPDATE l SET a = 1", "PRAGMA table_info(l)", "INSERT INTO l VALUES (1,2,3,4)"])
def test_the_links_query_gets_the_same_read_only_guard_as_the_main_query(tmp_path, bad):
    db = make_db(tmp_path, ROWS, [("B", "A", "x", None)])
    with pytest.raises(ValueError, match="read-only"):
        list(SqlAdapter().read(Source(f"sqlite:///{db}", {"query": "SELECT * FROM r", "id_column": "id", "links_query": bad})))
    assert sqlite3.connect(db).execute("SELECT count(*) FROM l").fetchone()[0] == 1


def test_a_comment_in_a_query_file_is_removed_before_the_guard_and_cannot_hide_a_statement(tmp_path):
    assert strip_sql_comments("SELECT 1 -- drop table x\n").strip() == "SELECT 1"
    assert " ".join(strip_sql_comments("SELECT /* delete */ 1").split()) == "SELECT 1"
    assert check_query("-- delete everything\nSELECT 1 /* update */") == "SELECT 1"
    assert check_query("SELECT '--not a comment', 2") == "SELECT '--not a comment', 2"             # inside a string the dashes stay
    with pytest.raises(ValueError):
        check_query("SELECT 1 /* hello */ ; DELETE FROM l")                                         # a comment does not make a second statement go away
    with pytest.raises(ValueError):
        check_query("SELECT 1 -- note\n; DROP TABLE l")


def test_query_file_option_is_read_and_a_missing_or_huge_file_is_refused(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("-- all of them\nSELECT * FROM r;\n", encoding="utf-8")
    assert query_text({"query_file": str(f)}, "query").startswith("-- all of them")
    assert query_text({}, "query") is None
    with pytest.raises(ValueError, match="query_file"):
        query_text({"query_file": str(tmp_path / "nope.sql")}, "query")
    big = tmp_path / "big.sql"
    big.write_text("SELECT 1 " + " " * MAX_QUERY_FILE, encoding="utf-8")
    with pytest.raises(ValueError, match="query_file"):
        query_text({"query_file": str(big)}, "query")
    assert query_text({"query": "SELECT 2", "query_file": str(f)}, "query") == "SELECT 2"        # the inline option wins when both are given


def test_a_query_file_alone_is_enough_for_the_adapter_to_be_recognised(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("SELECT 1", encoding="utf-8")
    ranked = sniff_all(Source("sqlite:///x.db", {"query_file": str(f)}))
    assert ranked and ranked[0][1] == "sql"
    assert not [n for s, n in sniff_all(Source("sqlite:///x.db", {})) if n == "sql"]              # no query at all: not claimed


def test_a_row_limit_stops_reading_and_does_not_wrap_the_query(tmp_path):
    db = make_db(tmp_path, [(f"R{i}", None, f"The widget shall do thing {i}.") for i in range(30)])
    q = "SELECT * FROM r ORDER BY id"                                    # an ORDER BY would be illegal inside a subquery on SQL Server
    ad = SqlAdapter()
    assert len(list(ad._run(Source(f"sqlite:///{db}", {}), check_query(q), limit=7))) == 7
    assert len(list(ad._run(Source(f"sqlite:///{db}", {}), check_query(q)))) == 30
    assert ad.discover(Source(f"sqlite:///{db}", {"query": q})).containers[0].rows == 30


def test_the_revision_changes_when_the_links_query_or_the_parent_column_changes(tmp_path):
    db = make_db(tmp_path, ROWS)
    base = {"query": "SELECT * FROM r"}
    ad = SqlAdapter()
    revs = {ad.revision(Source(f"sqlite:///{db}", o)) for o in
            (base, {**base, "links_query": "SELECT a AS source, b AS target FROM l"}, {**base, "parent_column": "up"}, {**base, "query": "SELECT id FROM r"})}
    assert len(revs) == 4
