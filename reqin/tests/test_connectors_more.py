"""Jira, Polarion and Jama connectors against in-memory fakes written from each vendor's documentation (tests/live_cases_more.py).
These prove the connectors do what they say on the DOCUMENTED shapes. They prove nothing about a real server: see each adapter's docstring."""
from __future__ import annotations

from pathlib import Path

import pytest

from live_cases_more import (JIRA_CLOUD, JIRA_DC, JIRA_GOLD, JIRA_ISSUES, JIRA_PAT, JIRA_REQS, JIRA_TOKEN, JIRA_USER, POLARION_BASE, POLARION_GOLD, POLARION_ITEMS,
                             POLARION_PAT, POLARION_REQS, JAMA_BASE, JAMA_GOLD, JAMA_ITEMS, JAMA_REQ_COUNT, JAMA_TOKEN, jama_server, jira_server, polarion_server)
from reqin import Profile, Source, ingest
from reqin.adapter import sniff_all
from reqin.adapters.jira import JiraAdapter, adf_text, plain
from reqin.adapters.jama import JamaAdapter
from reqin.adapters.polarion import PolarionAdapter, _parse_link_id
from reqin.connect import ConnectError
from reqin.model import RawLink, RawRecord

ROOT = Path(__file__).parent.parent
JIRA_PROFILE = Profile.from_yaml((ROOT / "profiles/jira.yaml").read_text())
POLARION_PROFILE = Profile.from_yaml((ROOT / "profiles/polarion.yaml").read_text())
JAMA_PROFILE = Profile.from_yaml((ROOT / "profiles/jama.yaml").read_text())


# ---------------------------------------------------------------------------------------------------- Jira
@pytest.fixture
def jira_env(monkeypatch):
    monkeypatch.setenv("JIRA_USER", JIRA_USER)
    monkeypatch.setenv("JIRA_TOKEN", JIRA_TOKEN)
    monkeypatch.setenv("JIRA_PAT", JIRA_PAT)


def cloud_src(**opts) -> Source:
    return Source("jira+" + JIRA_CLOUD, {"jql": "project = WID ORDER BY key", "basic_user_env": "JIRA_USER", "basic_password_env": "JIRA_TOKEN", **opts})


def dc_src(**opts) -> Source:
    return Source("jira+" + JIRA_DC, {"jql": "project = WID ORDER BY key", "token_env": "JIRA_PAT", **opts})


def jira_read(ad, src):
    items = list(ad.read(src))
    return [i for i in items if isinstance(i, RawRecord)], [i for i in items if isinstance(i, RawLink)]


@pytest.mark.parametrize("size", [1, 2, 3, 100])
def test_jira_cloud_reads_every_issue_at_any_page_size_and_follows_the_token_to_its_end(jira_env, size):
    t = jira_server("cloud")
    ad = JiraAdapter(transport=t)
    recs, _ = jira_read(ad, cloud_src(page_size=size))
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_ISSUES]
    assert len(t.requests) == -(-len(JIRA_ISSUES) // size)
    assert all(r.path == "/rest/api/3/search/jql" and r.query["maxResults"] == str(size) for r in t.requests)
    assert all(r.query["jql"] == "project = WID ORDER BY key" for r in t.requests), "every page must repeat the query"
    assert sum("nextPageToken" in r.query for r in t.requests) == len(t.requests) - 1


def test_jira_cloud_has_no_total_and_says_so_while_data_center_has_one_and_is_checked(jira_env):
    assert any("reports no total" in n for n in JiraAdapter(transport=jira_server("cloud")).discover(cloud_src()).notes)
    ok = JiraAdapter(transport=jira_server("dc")).discover(dc_src()).notes
    assert not any("WARNING" in n or "reports no total" in n for n in ok)
    lying = JiraAdapter(transport=jira_server("dc", fixed_total=99)).discover(dc_src()).notes
    assert any("WARNING the server reported a total of 99 but 7 came back" in n for n in lying)


@pytest.mark.parametrize("size", [1, 3, 50])
def test_jira_data_center_pages_with_startat_and_stops_at_the_total(jira_env, size):
    t = jira_server("dc")
    recs, _ = jira_read(JiraAdapter(transport=t), dc_src(page_size=size))
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_ISSUES]
    assert [r.query["startAt"] for r in t.requests] == [str(n) for n in range(0, len(JIRA_ISSUES), size)]
    assert all(r.path == "/jira/rest/api/2/search" for r in t.requests), "the context path of a Data Center site must be kept"


def test_jira_data_center_refuses_a_query_beyond_the_search_window_instead_of_reading_into_an_http_500(jira_env):
    t = jira_server("dc", fixed_total=10_001)
    with pytest.raises(ConnectError, match="search window is 10000"):
        JiraAdapter(transport=t).discover(dc_src())
    assert len(t.requests) == 1


def test_jira_links_are_one_per_link_whichever_issue_they_are_seen_from_and_direction_comes_from_link_map(jira_env):
    def links(**opts):
        return sorted((l.source_native_id, l.target_native_id, l.kind) for l in jira_read(JiraAdapter(transport=jira_server("cloud")), cloud_src(**opts))[1])
    default = links()
    assert default == [("WID-10", "OTHER-7", "blocks"), ("WID-10", "WID-1", "implements"), ("WID-5", "WID-1", "duplicate")]     # seen from both ends, kept once
    mapped = links(link_map='{"Implements": "satisfy", "Duplicate": {"kind": "trace", "source": "inward"}}')
    assert mapped == [("WID-1", "WID-5", "trace"), ("WID-10", "OTHER-7", "blocks"), ("WID-10", "WID-1", "satisfy")]
    flipped = links(link_map='{"Implements": {"kind": "satisfy", "source": "inward"}}')
    assert ("WID-1", "WID-10", "satisfy") in flipped and ("WID-10", "WID-1", "satisfy") not in flipped


def test_jira_a_link_whose_other_end_is_outside_the_query_is_still_found_from_the_end_that_is_inside(jira_env):
    only_reqs = cloud_src(jql="project = WID AND issuetype = Requirement ORDER BY key", link_map='{"Implements": "satisfy"}')
    recs, links = jira_read(JiraAdapter(transport=jira_server("cloud")), only_reqs)
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_REQS]
    assert ("WID-10", "WID-1", "satisfy") in {(l.source_native_id, l.target_native_id, l.kind) for l in links}      # WID-10 is not in the result, WID-1 says so
    r = ingest(only_reqs, profile=JIRA_PROFILE, adapter=JiraAdapter(transport=jira_server("cloud")))
    sat = next(l for l in r.links if l.kind == "satisfy")
    assert (sat.source_uid, sat.target_uid) == ("WID-10", "WID-1") and sat.source_mid is None and sat.target_mid is not None     # the outside end keeps its key


def test_jira_unmapped_link_types_are_named_in_discover_and_never_guessed(jira_env):
    notes = JiraAdapter(transport=jira_server("cloud")).discover(cloud_src(link_map='{"Implements": "satisfy"}')).notes
    assert any(n.startswith("link types not in link_map") and "Duplicate x2" in n and "Blocks x1" in n and "Implements" not in n for n in notes)


def test_jira_description_in_atlassian_document_format_becomes_text_and_what_was_skipped_is_said(jira_env):
    ad = JiraAdapter(transport=jira_server("cloud"))
    recs, _ = jira_read(ad, cloud_src())
    got = {r.native_id: r.fields["description"] for r in recs}
    assert got["WID-1"] == "The controller shall respond to a command within 50 ms."
    assert got["WID-2"] == "The controller shall log:\n- every fault\n- every restart"
    assert got["WID-3"] == "The controller shall restart\nwithin 30 seconds, as @Ada asked."
    assert got["WID-4"] == ""
    assert any("description parts with no text were skipped: media x1" in n for n in ad.discover(cloud_src()).notes)


def test_adf_and_plain_unit_cases():
    assert adf_text({"type": "doc", "content": [{"type": "orderedList", "content": [
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "one"}]}]},
        {"type": "listItem", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "two"}]}]}]}]}) == "1. one\n2. two"
    assert adf_text({"type": "doc", "content": [{"type": "table", "content": [{"type": "tableRow", "content": [
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "a"}]}]},
        {"type": "tableCell", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "b"}]}]}]}]}]}) == "a | b"
    assert plain(None) == "" and plain(True) == "true" and plain(3) == "3" and plain(["a", "", "b"]) == "a, b"
    assert plain({"value": "Test"}) == "Test" and plain({"displayName": "Ada", "name": "ada"}) == "Ada" and plain({"key": "X-1", "id": "7"}) == "X-1"
    assert plain({"odd": [1, 2]}) == '{"odd": [1, 2]}'                    # an object of unknown shape keeps its JSON, so nothing is lost


def test_jira_data_center_keeps_the_wiki_markup_as_the_author_wrote_it(jira_env):
    recs, _ = jira_read(JiraAdapter(transport=jira_server("dc")), dc_src())
    assert {r.native_id: r.fields["description"] for r in recs}["WID-2"] == "The controller shall log:\n* every fault\n* every restart"


def test_jira_auth_is_basic_on_cloud_and_bearer_on_data_center_and_a_wrong_secret_never_shows(jira_env, monkeypatch):
    t = jira_server("cloud")
    JiraAdapter(transport=t).discover(cloud_src())
    assert all(r.headers["Authorization"].startswith("Basic ") and r.headers["Accept"] == "application/json" and "reqin" in r.headers["User-Agent"].lower() for r in t.requests)
    t2 = jira_server("dc")
    JiraAdapter(transport=t2).discover(dc_src())
    assert all(r.headers["Authorization"] == f"Bearer {JIRA_PAT}" for r in t2.requests)
    monkeypatch.setenv("JIRA_TOKEN", "wrong-secret-xyz")
    ad = JiraAdapter(transport=jira_server("cloud"))
    with pytest.raises(ConnectError, match="HTTP 401") as e:
        ad.discover(cloud_src())
    assert "wrong-secret-xyz" not in str(e.value) and all("wrong-secret-xyz" not in a.url for a in ad.audit())
    assert [a.method for a in ad.audit()] == ["GET"]


def test_jira_an_invalid_jql_is_the_servers_message_not_a_traceback(jira_env):
    with pytest.raises(ConnectError, match="Error in the JQL Query"):
        JiraAdapter(transport=jira_server("cloud")).discover(cloud_src(jql="assignee = nobody"))


def test_jira_option_errors_say_what_is_wrong(jira_env):
    ad = JiraAdapter(transport=jira_server("cloud"))
    with pytest.raises(ConnectError, match="'jql' is required"):
        ad.discover(Source("jira+" + JIRA_CLOUD, {"basic_user_env": "JIRA_USER", "basic_password_env": "JIRA_TOKEN"}))
    for bad, match in [({"flavor": "server"}, "flavor"), ({"api_version": "4"}, "api_version"), ({"link_map": '{"X": {"source": "outward"}}'}, "link_map"),
                       ({"link_map": '{"X": {"kind": "k", "source": "left"}}'}, "outward or inward"), ({"page_size": "many"}, "page_size")]:
        with pytest.raises(ConnectError, match=match):
            JiraAdapter(transport=jira_server("cloud")).discover(cloud_src(**bad))


def test_jira_says_when_the_jql_has_no_order_by(jira_env):
    assert any("no ORDER BY" in n for n in JiraAdapter(transport=jira_server("cloud")).discover(cloud_src(jql="project = WID")).notes)
    assert not any("no ORDER BY" in n for n in JiraAdapter(transport=jira_server("cloud")).discover(cloud_src(jql="project = WID order   by key desc")).notes)


def test_jira_a_token_that_does_not_advance_is_refused_and_an_issue_seen_twice_is_kept_once(jira_env):
    with pytest.raises(ConnectError, match="already given"):
        JiraAdapter(transport=jira_server("cloud", repeat_token=True)).discover(cloud_src(page_size=2, max_requests=50))     # the cap: a missing guard fails here at once, not after a million requests
    ad = JiraAdapter(transport=jira_server("cloud", repeat_issue_on_page2=True))
    recs, _ = jira_read(ad, cloud_src(page_size=3))
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_ISSUES]
    assert any("came back twice" in n for n in ad.discover(cloud_src(page_size=3)).notes)


def test_jira_custom_fields_get_the_names_you_give_or_the_server_gives_and_a_failed_lookup_is_a_note(jira_env):
    def rec(**opts):
        recs, _ = jira_read(JiraAdapter(transport=jira_server("cloud", **opts.pop("fake", {}))), cloud_src(fields="summary,customfield_10042", **opts))
        return {r.native_id: r.fields for r in recs}["WID-1"]
    assert rec()["customfield_10042"] == "Test"
    assert rec(field_names='{"customfield_10042": "Verification method"}')["Verification method"] == "Test"
    assert rec(resolve_field_names="true")["Verification method"] == "Test"
    assert rec(resolve_field_names="true", field_names='{"customfield_10042": "VM"}')["VM"] == "Test"
    ad = JiraAdapter(transport=jira_server("cloud", fail_fields=True))
    notes = ad.discover(cloud_src(resolve_field_names="true")).notes
    assert any("field names could not be read from /field" in n for n in notes)
    assert jira_read(JiraAdapter(transport=jira_server("cloud", fail_fields=True)), cloud_src(resolve_field_names="true", fields="summary,customfield_10042"))[0][0].fields["customfield_10042"] == "Test"


def test_jira_a_rejected_login_stops_the_read_even_in_the_optional_field_name_lookup(jira_env, monkeypatch):
    monkeypatch.setenv("JIRA_TOKEN", "wrong-secret-xyz")
    ad = JiraAdapter(transport=jira_server("cloud"))
    with pytest.raises(ConnectError, match="HTTP 401"):
        ad.discover(cloud_src(resolve_field_names="true"))
    assert len(ad.audit()) == 1, "the read must not go on to the search after the credentials were refused"


def test_jira_links_and_parent_are_always_asked_for_even_when_the_field_list_is_narrow(jira_env):
    t = jira_server("cloud")
    recs, links = jira_read(JiraAdapter(transport=t), cloud_src(fields="summary"))
    asked = t.requests[0].query["fields"].split(",")
    assert "issuelinks" in asked and "parent" in asked and "summary" in asked
    assert links and {r.native_id: r.parent_native_id for r in recs}["WID-2"] == "WID-1"


def test_jira_parent_field_can_name_another_field_and_a_missing_parent_is_noted(jira_env):
    ad = JiraAdapter(transport=jira_server("cloud"))
    recs, _ = jira_read(ad, cloud_src(parent_field="customfield_10042"))
    assert {r.native_id: r.parent_native_id for r in recs}["WID-1"] == "Test"
    assert any("its parent Test is not in this result" in n for n in ad.discover(cloud_src(parent_field="customfield_10042")).notes)


def test_jira_the_project_and_the_issue_type_are_readable_fields_and_containers(jira_env):
    ad = JiraAdapter(transport=jira_server("cloud"))
    d = ad.discover(cloud_src())
    assert [(c.name, c.rows) for c in d.containers] == [("Epic", 1), ("Requirement", 5), ("Story", 1)]
    recs, _ = jira_read(ad, cloud_src())
    f = {r.native_id: r.fields for r in recs}["WID-1"]
    assert (f["project"], f["project_name"], f["status"], f["issuetype"], f["priority"], f["labels"], f["id"]) == ("WID", "Fictional Widget", "Open", "Requirement", "Medium", "safety", "10001")


def test_jira_read_once_peek_and_revision(jira_env):
    t = jira_server("cloud")
    ad = JiraAdapter(transport=t)
    ad.discover(cloud_src(page_size=2))
    n = len(t.requests)
    list(ad.read(cloud_src(page_size=2)))
    rev = ad.revision(cloud_src(page_size=2))
    assert len(t.requests) == n and len(rev) == 16
    t2 = jira_server("cloud")
    ad2 = JiraAdapter(transport=t2)
    recs, _ = jira_read(ad2, cloud_src(page_size=2, peek="1"))
    assert len(recs) == 2 and len(t2.requests) == 1 and any("PEEK" in x for x in ad2.discover(cloud_src(page_size=2, peek="1")).notes)


def test_jira_through_the_pipeline_with_the_shipped_profile(jira_env):
    src = cloud_src(jql="project = WID AND issuetype = Requirement ORDER BY key", link_map='{"Implements": "satisfy"}')
    r = ingest(src, profile=JIRA_PROFILE, adapter=JiraAdapter(transport=jira_server("cloud")))
    assert r.report["invariant_ok"] and {q.uid: q.text for q in r.requirements} == JIRA_GOLD
    by_uid = {q.uid: q for q in r.requirements}
    assert by_uid["WID-2"].parent_mid == by_uid["WID-1"].mid and by_uid["WID-1"].parent_mid is None
    assert sorted((l.kind) for l in r.links) == ["duplicate", "satisfy"]


def test_jira_sniff():
    assert sniff_all(Source("jira+" + JIRA_CLOUD))[0][1] == "jira"
    assert sniff_all(Source(JIRA_DC + "/rest/api/2/search"))[0][1] == "jira"


# ---------------------------------------------------------------------------------------------------- Polarion
@pytest.fixture
def pol_env(monkeypatch):
    monkeypatch.setenv("POLARION_TOKEN", POLARION_PAT)


def pol_src(**opts) -> Source:
    return Source("polarion+" + POLARION_BASE, {"project": "WIDGET", "token_env": "POLARION_TOKEN", **opts})


IDS = [i["id"] for i in POLARION_ITEMS]


@pytest.mark.parametrize("relative", [False, True])
@pytest.mark.parametrize("size", [1, 2, 3, 100])
def test_polarion_reads_every_work_item_at_any_page_size_following_the_next_link(pol_env, size, relative):
    t = polarion_server(relative_next=relative)
    recs, _ = jira_read(PolarionAdapter(transport=t), pol_src(page_size=size))
    assert [r.fields["id"] for r in recs] == IDS                                    # sorted by id, though the fake's unsorted order is the reverse
    assert len(t.requests) == -(-len(IDS) // size)
    assert t.requests[0].query["page[size]"] == str(size) and t.requests[0].query["page[number]"] == "1"
    assert all(r.path == "/polarion/rest/v1/projects/WIDGET/workitems" for r in t.requests)


def test_polarion_without_a_next_link_asks_for_the_next_page_number_itself(pol_env):
    t = polarion_server(with_links_object=False)
    recs, _ = jira_read(PolarionAdapter(transport=t), pol_src(page_size=3))
    assert [r.fields["id"] for r in recs] == IDS and [r.query["page[number]"] for r in t.requests] == ["1", "2", "3"]


def test_polarion_always_sends_a_sort_and_says_so_when_told_not_to(pol_env):
    t = polarion_server()
    PolarionAdapter(transport=t).discover(pol_src(page_size=3))
    assert all(r.query["sort"] == "id" for r in t.requests)
    t2 = polarion_server()
    ad = PolarionAdapter(transport=t2)
    notes = ad.discover(pol_src(sort="none")).notes
    assert "sort" not in t2.requests[0].query and any("no sort was sent" in n for n in notes)
    t3 = polarion_server()
    recs, _ = jira_read(PolarionAdapter(transport=t3), pol_src(sort="-id"))
    assert t3.requests[0].query["sort"] == "-id" and [r.fields["id"] for r in recs] == list(reversed(IDS))


def test_polarion_asks_for_all_fields_and_the_linked_items_unless_told_otherwise(pol_env):
    t = polarion_server()
    PolarionAdapter(transport=t).discover(pol_src())
    q = t.requests[0].query
    assert q["fields[workitems]"] == "@all" and q["include"] == "linkedWorkItems" and q["fields[linkedworkitems]"] == "@all" and "query" not in q
    t2 = polarion_server()
    ad = PolarionAdapter(transport=t2)
    recs, links = jira_read(ad, pol_src(fields="id,title", include_links="false", query="type:requirement"))
    q2 = t2.requests[0].query
    assert q2["fields[workitems]"] == "id,title" and "include" not in q2 and q2["query"] == "type:requirement" and links == []
    assert set(recs[0].fields) == {"id", "title", "_resource_id"} and any("include_links is off" in n for n in ad.discover(pol_src(include_links="false")).notes)


def test_polarion_links_come_from_the_included_resources_with_the_carrying_item_as_source(pol_env):
    ad = PolarionAdapter(transport=polarion_server())
    _, links = jira_read(ad, pol_src())
    got = sorted((l.source_native_id, l.target_native_id, l.kind) for l in links)
    assert got == [("WIDGET/WI-1", "WIDGET/WI-2", "relates_to"), ("WIDGET/WI-2", "WIDGET/WI-1", "parent"), ("WIDGET/WI-4", "WIDGET/WI-3", "tests"),
                   ("WIDGET/WI-6", "OTHERPROJ/WI-9", "relates_to")]
    mapped = sorted((l.source_native_id, l.target_native_id, l.kind) for l in jira_read(PolarionAdapter(transport=polarion_server()),
                    pol_src(role_map='{"tests": "verify", "relates_to": {"kind": "trace", "source": "linked"}}'))[1])
    assert ("WIDGET/WI-4", "WIDGET/WI-3", "verify") in mapped and ("WIDGET/WI-2", "WIDGET/WI-1", "trace") in mapped and ("WIDGET/WI-1", "WIDGET/WI-2", "trace") not in mapped
    notes = ad.discover(pol_src(role_map='{"tests": "verify"}')).notes
    assert any(n.startswith("link roles not in role_map") and "parent x1" in n and "relates_to x2" in n and "tests" not in n.split(":", 1)[1] for n in notes)


def test_polarion_parent_role_makes_a_parent_and_not_a_link(pol_env):
    recs, links = jira_read(PolarionAdapter(transport=polarion_server()), pol_src(parent_role="parent"))
    assert {r.fields["id"]: r.parent_native_id for r in recs}["WI-2"] == "WIDGET/WI-1"
    assert not any(l.kind == "parent" for l in links) and len(links) == 3
    recs0, _ = jira_read(PolarionAdapter(transport=polarion_server()), pol_src())
    assert all(r.parent_native_id is None for r in recs0), "no hierarchy unless the role is named: its direction was not verified"


def test_polarion_links_are_read_from_the_shape_of_their_id_only_when_the_server_did_not_include_them_and_that_is_said(pol_env):
    ad = PolarionAdapter(transport=polarion_server(no_included=True))
    _, links = jira_read(ad, pol_src())
    assert len(links) == 4 and ("WIDGET/WI-4", "WIDGET/WI-3", "tests") in {(l.source_native_id, l.target_native_id, l.kind) for l in links}
    assert any("4 links were read from the shape of their id" in n for n in ad.discover(pol_src()).notes)
    assert _parse_link_id("P/WI-1/relates_to/Q/WI-2") == ("P/WI-1", "relates_to", "Q/WI-2") and _parse_link_id("P/WI-1/relates_to") is None and _parse_link_id("a//b/c/d") is None


def test_polarion_rich_text_keeps_its_value_and_its_type_and_the_pipeline_strips_the_markup(pol_env):
    recs, _ = jira_read(PolarionAdapter(transport=polarion_server()), pol_src())
    f = {r.fields["id"]: r.fields for r in recs}
    assert f["WI-2"]["description"] == "<div>The controller shall log every <b>fault</b>.</div>" and f["WI-2"]["description_type"] == "text/html"
    assert f["WI-3"]["description_type"] == "text/plain" and "description" not in f["WI-5"] and f["WI-1"]["_resource_id"] == "WIDGET/WI-1"
    r = ingest(pol_src(query="type:requirement"), profile=POLARION_PROFILE, adapter=PolarionAdapter(transport=polarion_server()))
    assert r.report["invariant_ok"] and {q.uid: q.text for q in r.requirements} == POLARION_GOLD


def test_polarion_totalcount_is_checked_and_its_absence_is_said(pol_env):
    assert not any("WARNING" in n or "no meta.totalCount" in n for n in PolarionAdapter(transport=polarion_server()).discover(pol_src(page_size=3)).notes)
    assert any("WARNING the server reported a totalCount of 99 but 7 came back" in n for n in PolarionAdapter(transport=polarion_server(report_total=99)).discover(pol_src()).notes)
    assert any("no meta.totalCount" in n for n in PolarionAdapter(transport=polarion_server(drop_total=True)).discover(pol_src()).notes)


def test_polarion_auth_is_bearer_a_404_names_the_disabled_rest_api_and_a_wrong_secret_never_shows(pol_env, monkeypatch):
    t = polarion_server()
    PolarionAdapter(transport=t).discover(pol_src())
    assert all(r.headers["Authorization"] == f"Bearer {POLARION_PAT}" and r.headers["Accept"] == "application/json" for r in t.requests)
    with pytest.raises(ConnectError, match="com.siemens.polarion.rest.enabled") as e:
        PolarionAdapter(transport=polarion_server(rest_disabled=True)).discover(pol_src())
    assert e.value.status == 404
    monkeypatch.setenv("POLARION_TOKEN", "wrong-secret-abc")
    ad = PolarionAdapter(transport=polarion_server())
    with pytest.raises(ConnectError, match="HTTP 401") as e2:
        ad.discover(pol_src())
    assert "wrong-secret-abc" not in str(e2.value) and [a.method for a in ad.audit()] == ["GET"]


def test_polarion_never_follows_a_next_link_to_another_host_or_back_to_the_same_page_or_a_page_that_adds_nothing(pol_env):
    with pytest.raises(ConnectError, match="another host"):
        PolarionAdapter(transport=polarion_server(foreign_next=True)).discover(pol_src(page_size=2, max_requests=50))
    with pytest.raises(ConnectError, match="points back"):
        PolarionAdapter(transport=polarion_server(loop_next=True)).discover(pol_src(page_size=2, max_requests=50))
    with pytest.raises(ConnectError, match="already read: the server is not advancing"):
        PolarionAdapter(transport=polarion_server(with_links_object=False, ignore_page_number=True, drop_total=True)).discover(pol_src(page_size=3, max_requests=50))


def test_polarion_option_errors_and_a_query_the_server_rejects(pol_env):
    with pytest.raises(ConnectError, match="'project' is required"):
        PolarionAdapter(transport=polarion_server()).discover(Source("polarion+" + POLARION_BASE, {"token_env": "POLARION_TOKEN"}))
    for bad, match in [({"role_map": '{"x": {"source": "owner"}}'}, "role_map"), ({"role_map": '{"x": {"kind": "k", "source": "me"}}'}, "owner or linked"),
                       ({"page_size": "lots"}, "page_size")]:
        with pytest.raises(ConnectError, match=match):
            PolarionAdapter(transport=polarion_server()).discover(pol_src(**bad))
    with pytest.raises(ConnectError, match="HTTP 400"):
        PolarionAdapter(transport=polarion_server()).discover(pol_src(query="title:Mass"))


def test_polarion_containers_read_once_peek_and_revision(pol_env):
    t = polarion_server()
    ad = PolarionAdapter(transport=t)
    d = ad.discover(pol_src(page_size=3))
    assert [(c.name, c.rows) for c in d.containers] == [("heading", 1), ("requirement", 5), ("testcase", 1)]
    n = len(t.requests)
    list(ad.read(pol_src(page_size=3)))
    assert len(t.requests) == n and len(ad.revision(pol_src(page_size=3))) == 16
    t2 = polarion_server()
    ad2 = PolarionAdapter(transport=t2)
    recs, _ = jira_read(ad2, pol_src(page_size=2, peek="1"))
    assert len(recs) == 2 and len(t2.requests) == 1 and any("PEEK" in x for x in ad2.discover(pol_src(page_size=2, peek="1")).notes)


def test_polarion_sniff():
    assert sniff_all(Source("polarion+" + POLARION_BASE))[0][1] == "polarion"
    assert sniff_all(Source(POLARION_BASE + "/rest/v1/projects/X/workitems"))[0][1] == "polarion"


# ---------------------------------------------------------------------------------------------------- Jama
@pytest.fixture
def jama_env(monkeypatch):
    monkeypatch.setenv("JAMA_TOKEN", JAMA_TOKEN)
    monkeypatch.setenv("JAMA_USER", "jama-user")
    monkeypatch.setenv("JAMA_PASS", "jama-pass")


def jama_src(**opts) -> Source:
    return Source("jama+" + JAMA_BASE, {"project": "5", "token_env": "JAMA_TOKEN", **opts})


ITEM_IDS = [str(i["id"]) for i in JAMA_ITEMS]


@pytest.mark.parametrize("size", [1, 2, 3, 50])
def test_jama_reads_every_item_at_any_page_size_with_startat_and_stops_at_the_total(jama_env, size):
    t = jama_server()
    recs, _ = jira_read(JamaAdapter(transport=t), jama_src(page_size=size, relationships="false"))
    assert [r.native_id for r in recs] == ITEM_IDS
    pages = [r for r in t.requests if r.path.endswith("/abstractitems")]
    assert [r.query["startAt"] for r in pages] == [str(n) for n in range(0, len(ITEM_IDS), size)]
    assert all(r.query["project"] == "5" and r.query["maxResults"] == str(size) for r in pages)


def test_jama_a_page_size_over_the_vendors_limit_is_the_servers_message_not_a_hang(jama_env):
    with pytest.raises(ConnectError, match="maxResults must be between 1 and 50"):
        JamaAdapter(transport=jama_server()).discover(jama_src(page_size=100))


def test_jama_the_project_can_be_an_id_a_name_or_a_key_and_an_unknown_one_lists_the_choices(jama_env):
    t = jama_server()
    JamaAdapter(transport=t).discover(jama_src(relationships="false"))
    assert not any(r.path.endswith("/projects") for r in t.requests), "an id needs no lookup"
    for name in ("Fictional Widget", "WID"):
        t2 = jama_server()
        ad = JamaAdapter(transport=t2)
        assert len(jira_read(ad, jama_src(project=name, relationships="false"))[0]) == len(ITEM_IDS)
        assert any("is id 5" in n for n in ad.discover(jama_src(project=name, relationships="false")).notes)
    with pytest.raises(ConnectError, match=r"no project named or keyed 'Nope'.*Fictional Widget.*Another Fictional"):
        JamaAdapter(transport=jama_server()).discover(jama_src(project="Nope"))


def test_jama_field_names_lose_their_item_type_suffix_and_the_type_gets_its_display_name(jama_env):
    ad = JamaAdapter(transport=jama_server())
    recs, _ = jira_read(ad, jama_src(relationships="false"))
    f = {r.native_id: r.fields for r in recs}
    assert f["101"]["name"] == "Response time" and f["101"]["itemType"] == "Requirement" and f["101"]["itemTypeId"] == "27" and f["101"]["documentKey"] == "WID-REQ-1"
    assert f["101"]["globalId"] == "GID-101" and f["101"]["project"] == "5" and f["201"]["itemType"] == "Test Case" and f["100"]["itemType"] == "Folder"
    assert "status" in f["101"] and "status$27" not in f["101"] and f["101"]["status"] == "12"            # a pick list value stays an id unless asked
    assert [(c.name, c.rows) for c in ad.discover(jama_src(relationships="false")).containers] == [("Folder", 1), ("Requirement", 5), ("Test Case", 1)]


@pytest.mark.parametrize("keep,expected", [("Requirement", 5), ("req", 5), ("27", 5), ("Requirement,TC", 6), ("test case", 1)])
def test_jama_item_types_keep_by_name_key_or_id(jama_env, keep, expected):
    recs, _ = jira_read(JamaAdapter(transport=jama_server()), jama_src(item_types=keep, relationships="false"))
    assert len(recs) == expected


def test_jama_a_parent_is_kept_only_when_it_is_one_of_the_records_read(jama_env):
    all_recs, _ = jira_read(JamaAdapter(transport=jama_server()), jama_src(relationships="false"))
    assert {r.native_id: r.parent_native_id for r in all_recs}["101"] == "100" and {r.native_id: r.parent_native_id for r in all_recs}["102"] == "101"
    only, _ = jira_read(JamaAdapter(transport=jama_server()), jama_src(item_types="Requirement", relationships="false"))
    assert {r.native_id: r.parent_native_id for r in only}["101"] is None and {r.native_id: r.parent_native_id for r in only}["102"] == "101"


@pytest.mark.parametrize("rel_size", [1, 2, 1000])
def test_jama_relationships_page_with_lastid_and_the_downstream_item_is_the_source(jama_env, rel_size):
    t = jama_server()
    _, links = jira_read(JamaAdapter(transport=t), jama_src(rel_page_size=rel_size))
    got = sorted((l.source_native_id, l.target_native_id, l.kind) for l in links)
    assert got == [("102", "101", "derived"), ("201", "101", "verification"), ("999", "103", "related to")]
    rq = [r for r in t.requests if r.path.endswith("/relationships")]
    assert rq[0].query["project"] == "5" and "lastId" not in rq[0].query and rq[0].query["omitCount"] == "true"
    assert [r.query.get("lastId") for r in rq[1:]] == [str(n) for n in range(rel_size, 4, rel_size)]       # each page asks after the id the last one ended on


def test_jama_link_direction_link_map_and_the_notes_about_what_was_not_mapped(jama_env):
    flipped = jira_read(JamaAdapter(transport=jama_server()), jama_src(link_direction="upstream_to_downstream"))[1]
    assert ("101", "201", "verification") in {(l.source_native_id, l.target_native_id, l.kind) for l in flipped}
    ad = JamaAdapter(transport=jama_server())
    mapped = jira_read(ad, jama_src(link_map='{"Verification": "verify", "Derived": "derive"}'))[1]
    assert {(l.source_native_id, l.target_native_id, l.kind) for l in mapped} == {("201", "101", "verify"), ("102", "101", "derive"), ("999", "103", "related to")}
    notes = ad.discover(jama_src(link_map='{"Verification": "verify", "Derived": "derive"}')).notes
    assert any(n.startswith("relationship types not in link_map") and "Related to x1" in n and "Derived" not in n for n in notes)
    assert any("3 relationships read (1 marked suspect" in n for n in notes)


def test_jama_without_relationship_type_names_the_kind_is_the_type_id_and_that_is_said(jama_env):
    ad = JamaAdapter(transport=jama_server(no_rel_types=True))
    kinds = sorted(l.kind for l in jira_read(ad, jama_src())[1])
    assert kinds == ["reltype-4", "reltype-5", "reltype-6"]
    assert any("relationship type names could not be read" in n for n in ad.discover(jama_src()).notes)


def test_jama_relationships_can_be_switched_off_and_a_peek_reads_none(jama_env):
    t = jama_server()
    ad = JamaAdapter(transport=t)
    assert jira_read(ad, jama_src(relationships="false"))[1] == [] and not any(r.path.endswith("/relationships") for r in t.requests)
    assert any("relationships=false" in n for n in ad.discover(jama_src(relationships="false")).notes)
    t2 = jama_server()
    ad2 = JamaAdapter(transport=t2)
    recs, links = jira_read(ad2, jama_src(page_size=2, peek="1"))
    assert len(recs) == 2 and links == [] and len([r for r in t2.requests if r.path.endswith("/abstractitems")]) == 1
    assert any("PEEK" in n for n in ad2.discover(jama_src(page_size=2, peek="1")).notes)


def test_jama_a_relationship_listing_that_does_not_advance_is_refused(jama_env):
    with pytest.raises(ConnectError, match="not advancing"):
        JamaAdapter(transport=jama_server(rels_stuck=True)).discover(jama_src(rel_page_size=1))


def test_jama_pick_list_ids_become_names_only_for_the_fields_you_name_and_each_id_is_looked_up_once(jama_env):
    t = jama_server()
    recs, _ = jira_read(JamaAdapter(transport=t), jama_src(picklist_fields="status", relationships="false"))
    f = {r.native_id: r.fields for r in recs}
    assert (f["101"]["status"], f["102"]["status"], f["103"]["status"]) == ("Approved", "Draft", "Approved")
    assert sum(r.path.endswith("/picklistoptions/12") for r in t.requests) == 1 and sum(r.path.endswith("/picklistoptions/13") for r in t.requests) == 1
    assert "status" not in f["201"]
    ad = JamaAdapter(transport=jama_server(fail_picks=True))
    recs2, _ = jira_read(ad, jama_src(picklist_fields="status", relationships="false"))
    assert {r.native_id: r.fields for r in recs2}["101"]["status"] == "12" and any("pick list option 12 could not be looked up" in n for n in ad.discover(jama_src(picklist_fields="status", relationships="false")).notes)


def test_jama_totals_are_checked_and_a_server_that_ignores_startat_is_caught(jama_env):
    assert not any("WARNING" in n for n in JamaAdapter(transport=jama_server()).discover(jama_src(page_size=3)).notes)
    assert any("WARNING the server reported totalResults 99 but 7 came back" in n for n in JamaAdapter(transport=jama_server(report_total=99)).discover(jama_src()).notes)
    ad = JamaAdapter(transport=jama_server(ignore_start_at=True))
    recs, _ = jira_read(ad, jama_src(page_size=2, relationships="false"))
    notes = ad.discover(jama_src(page_size=2, relationships="false")).notes
    assert [r.native_id for r in recs] == ITEM_IDS[:2] and any("came back twice" in n for n in notes) and any("WARNING" in n for n in notes)
    recs3, _ = jira_read(JamaAdapter(transport=jama_server(drop_page_info=True)), jama_src(page_size=3, relationships="false"))
    assert [r.native_id for r in recs3] == ITEM_IDS, "without pageInfo a short page is the end"


def test_jama_auth_bearer_basic_and_a_wrong_secret_never_shows(jama_env, monkeypatch):
    t = jama_server()
    JamaAdapter(transport=t).discover(jama_src(relationships="false"))
    assert all(r.headers["Authorization"] == f"Bearer {JAMA_TOKEN}" and r.headers["Accept"] == "application/json" for r in t.requests)
    t2 = jama_server(auth="basic")
    JamaAdapter(transport=t2).discover(Source("jama+" + JAMA_BASE, {"project": "5", "basic_user_env": "JAMA_USER", "basic_password_env": "JAMA_PASS", "relationships": "false"}))
    assert all(r.headers["Authorization"].startswith("Basic ") for r in t2.requests)
    monkeypatch.setenv("JAMA_TOKEN", "wrong-secret-qrs")
    ad = JamaAdapter(transport=jama_server())
    with pytest.raises(ConnectError, match="HTTP 401") as e:
        ad.discover(jama_src())
    assert "wrong-secret-qrs" not in str(e.value) and [a.method for a in ad.audit()] == ["GET"]


def test_jama_option_errors(jama_env):
    with pytest.raises(ConnectError, match="'project' is required"):
        JamaAdapter(transport=jama_server()).discover(Source("jama+" + JAMA_BASE, {"token_env": "JAMA_TOKEN"}))
    for bad, match in [({"link_direction": "sideways"}, "link_direction"), ({"page_size": "big"}, "page_size"), ({"items_path": "nope"}, "HTTP 404")]:
        with pytest.raises(ConnectError, match=match):
            JamaAdapter(transport=jama_server()).discover(jama_src(**bad))


def test_jama_read_once_and_revision_and_the_pipeline_with_the_shipped_profile(jama_env):
    t = jama_server()
    ad = JamaAdapter(transport=t)
    ad.discover(jama_src(item_types="Requirement"))
    n = len(t.requests)
    list(ad.read(jama_src(item_types="Requirement")))
    assert len(t.requests) == n and len(ad.revision(jama_src(item_types="Requirement"))) == 16
    r = ingest(jama_src(item_types="Requirement", link_map='{"Verification": "verify", "Derived": "derive"}'), profile=JAMA_PROFILE, adapter=JamaAdapter(transport=jama_server()))
    assert r.report["invariant_ok"] and len(r.requirements) == JAMA_REQ_COUNT and {q.uid: q.text for q in r.requirements} == JAMA_GOLD
    by_uid = {q.uid: q for q in r.requirements}
    assert by_uid["WID-REQ-2"].parent_mid == by_uid["WID-REQ-1"].mid
    assert sorted(l.kind for l in r.links) == ["derive", "related to", "verify"]
    derive = next(l for l in r.links if l.kind == "derive")
    assert (derive.source_uid, derive.target_uid) == ("WID-REQ-2", "WID-REQ-1") and derive.source_mid and derive.target_mid


def test_jama_sniff():
    assert sniff_all(Source("jama+" + JAMA_BASE))[0][1] == "jama"
    assert sniff_all(Source("https://acme.jamacloud.example.test/rest/v1/items"))[0][1] == "jama"
    assert not any(n == "jama" for _, n in sniff_all(Source("https://example.test/rest/v1/items")))


# ---------------------------------------------------------------------------------------------------- the one POST: the Jama token helper
def _token_server(answer: dict | None, status: int = 200):
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    seen: list[dict] = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):  # noqa: ANN002
            pass

        def do_POST(self):  # noqa: N802
            body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode()
            seen.append({"path": self.path, "auth": self.headers.get("Authorization"), "ctype": self.headers.get("Content-Type"), "body": body})
            out = __import__("json").dumps(answer).encode()
            self.send_response(status)
            self.send_header("Content-Length", str(len(out)))
            self.end_headers()
            self.wfile.write(out)
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


def test_the_jama_token_helper_posts_the_documented_request_and_hands_back_only_a_bearer_header(monkeypatch):
    import base64
    monkeypatch.syspath_prepend(str(ROOT / "connectors/jama"))
    import jama_oauth_hook as hook
    srv, seen = _token_server({"access_token": "tok-from-server-1", "token_type": "bearer", "expires_in": 3599})
    try:
        url = f"http://127.0.0.1:{srv.server_port}/rest/oauth/token"
        out = hook.headers({"token_url": url}, {"JAMA_CLIENT_ID": "cid-1", "JAMA_CLIENT_SECRET": "secret-1"})
    finally:
        srv.shutdown()
    assert out == {"Authorization": "Bearer tok-from-server-1"}
    assert seen == [{"path": "/rest/oauth/token", "auth": "Basic " + base64.b64encode(b"cid-1:secret-1").decode(), "ctype": "application/x-www-form-urlencoded",
                     "body": "grant_type=client_credentials"}]


def test_the_jama_token_helper_plugs_into_the_connector_and_its_token_is_scrubbed(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "connectors/jama"))
    monkeypatch.setenv("JAMA_CLIENT_ID", "cid-1")
    monkeypatch.setenv("JAMA_CLIENT_SECRET", "secret-1")
    srv, _ = _token_server({"access_token": JAMA_TOKEN})
    try:
        ad = JamaAdapter(transport=jama_server())
        src = Source("jama+" + JAMA_BASE, {"project": "5", "relationships": "false", "auth_hook": "jama_oauth_hook:headers", "token_url": f"http://127.0.0.1:{srv.server_port}/rest/oauth/token"})
        assert len(jira_read(ad, src)[0]) == len(ITEM_IDS)
    finally:
        srv.shutdown()
    assert all(JAMA_TOKEN not in a.url for a in ad.audit())


def test_the_jama_token_helper_refuses_clear_text_missing_secrets_and_a_bad_answer(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "connectors/jama"))
    import jama_oauth_hook as hook
    env = {"JAMA_CLIENT_ID": "cid-1", "JAMA_CLIENT_SECRET": "secret-1"}
    with pytest.raises(hook.TokenError, match="https://"):
        hook.headers({"token_url": "http://jama.example.test/rest/oauth/token"}, env)
    with pytest.raises(hook.TokenError, match="JAMA_CLIENT_ID and JAMA_CLIENT_SECRET"):
        hook.headers({"token_url": "https://x.example.test/t"}, {})
    for answer, status, match in [({"nope": 1}, 200, "no access_token"), ({"error": "invalid_client"}, 401, "HTTP 401")]:
        srv, _ = _token_server(answer, status)
        try:
            with pytest.raises(hook.TokenError, match=match) as e:
                hook.headers({"token_url": f"http://127.0.0.1:{srv.server_port}/t"}, env)
        finally:
            srv.shutdown()
        assert "secret-1" not in str(e.value)
