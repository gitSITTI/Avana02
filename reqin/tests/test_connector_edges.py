"""Awkward replies and awkward files, for the connectors written from vendor documentation. Everything here is made up.

Each test bends one thing a server (or a file) may do and says what the connector must then do. They were written after tools/mutation/connectors.py
showed that the first set of tests let 56 deliberate breakages through: every test below fails when its rule is removed from the code.
The fakes are the same documentation-shaped ones as in the other connector tests, with reqin.testing.Tweaked bending single replies. A pass here says the
connectors keep their rules on those shapes. It says nothing about a real server or a real model file."""
from __future__ import annotations

import io
from pathlib import Path

import pytest

from live_cases import AG_BASE, agility_server, oslc_server
from live_cases_more import JAMA_ITEMS, JIRA_ISSUES, jama_server, jira_server, polarion_server
from reqin import Source
from reqin.adapters.agility import AgilityAdapter, _idrefs, assets_from_xml
from reqin.adapters.jama import JamaAdapter
from reqin.adapters.jira import JiraAdapter
from reqin.adapters.oslc_rm import OslcRmAdapter
from reqin.adapters.polarion import PolarionAdapter
from reqin.adapters.sql import check_query
from reqin.adapters.sysml1_xmi import MODEL_ENTRY, SysML1XmiAdapter, _events
from reqin.connect import ConnectError
from reqin.model import RawLink, RawRecord
from reqin.testing import Tweaked, json_response, text_response
from test_connectors_more import cloud_src, dc_src, jama_env, jama_src, jira_env, jira_read, pol_env, pol_src  # noqa: F401  (the fixtures are used by name)
from test_live_connectors import oslc_src
from test_sysml1_xmi import APPS, MODEL, mdzip, run, write, xmi


def split(adapter, src):
    items = list(adapter.read(src))
    return [i for i in items if isinstance(i, RawRecord)], [i for i in items if isinstance(i, RawLink)]


def ends(links):
    return sorted((l.source_native_id, l.target_native_id, l.kind) for l in links)


# ---------------------------------------------------------------------------------------------------- the helper itself
def test_tweaked_bends_a_successful_reply_leaves_errors_alone_and_records_every_request():
    t = Tweaked(jira_server("cloud", no_auth_check=True))
    t.rewrite("/search/jql", lambda body, req: {**body, "marker": req.query["maxResults"]})
    t.replace("/field", lambda req: text_response("nope", status=401) if req.query.get("x") else None)
    ok = t.get("https://fictional-widgets.atlassian.net/rest/api/3/search/jql?jql=project%20%3D%20WID&maxResults=3", {})
    assert ok.status == 200 and b'"marker": "3"' in ok.body
    assert t.get("https://fictional-widgets.atlassian.net/rest/api/3/search/jql?jql=bad", {}).status == 400          # an error is not rewritten
    assert t.get("https://fictional-widgets.atlassian.net/rest/api/3/field?x=1", {}).status == 401                    # replaced
    assert t.get("https://fictional-widgets.atlassian.net/rest/api/3/field", {}).status == 200                         # None: the fake answers
    assert [r.path.rsplit("/", 1)[-1] for r in t.requests] == ["jql", "jql", "field", "field"]


# ---------------------------------------------------------------------------------------------------- Jira
def test_jira_data_center_starts_the_next_page_where_the_issues_that_came_back_end_not_where_the_page_size_says(jira_env):
    t = Tweaked(jira_server("dc")).rewrite("/search", lambda b, r: {**b, "issues": b["issues"][:2]})         # a server that caps a page below maxResults
    recs, _ = jira_read(JiraAdapter(transport=t), dc_src(page_size=5))
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_ISSUES]
    assert [r.query["startAt"] for r in t.requests] == ["0", "2", "4", "6"]


def test_jira_data_center_with_no_total_stops_at_a_short_page_and_asks_for_nothing_more(jira_env):
    t = Tweaked(jira_server("dc")).rewrite("/search", lambda b, r: {k: v for k, v in b.items() if k != "total"})
    recs, _ = jira_read(JiraAdapter(transport=t), dc_src(page_size=3))
    assert len(recs) == len(JIRA_ISSUES)
    assert len(t.requests) == 3                                                                    # 3 + 3 + 1: the short page is the end


def test_jira_cloud_stops_when_a_reply_says_isLast_even_if_it_still_hands_out_a_token(jira_env):
    t = Tweaked(jira_server("cloud")).rewrite("/search/jql", lambda b, r: {**b, "isLast": True})
    recs, _ = jira_read(JiraAdapter(transport=t), cloud_src(page_size=3))
    assert [r.native_id for r in recs] == [i["key"] for i in JIRA_ISSUES][:3] and len(t.requests) == 1


def test_jira_the_revision_changes_when_an_issue_is_updated_and_only_then(jira_env):
    def bump(body, req):
        for i in body["issues"]:
            if i["key"] == "WID-2":
                i["fields"]["updated"] = "2030-01-01T00:00:00.000+0000"
        return body
    before = JiraAdapter(transport=jira_server("cloud")).revision(cloud_src())
    assert before == JiraAdapter(transport=jira_server("cloud")).revision(cloud_src())
    assert before != JiraAdapter(transport=Tweaked(jira_server("cloud")).rewrite("/search/jql", bump)).revision(cloud_src())


def test_jira_a_link_whose_other_end_has_no_key_is_not_read_whether_the_key_is_missing_or_null(jira_env):
    kind = {"name": "Blocks", "inward": "is blocked by", "outward": "blocks"}

    def broken(body, req):
        for i in body["issues"]:
            if i["key"] == "WID-2":
                i["fields"]["issuelinks"] = [{"id": "1", "type": kind, "outwardIssue": {"id": "7"}}, {"id": "2", "type": kind, "inwardIssue": {"key": None, "id": "8"}},
                                             {"id": "3", "type": kind, "outwardIssue": {"key": None, "id": "9"}}]
        return body
    want = ends(jira_read(JiraAdapter(transport=jira_server("cloud")), cloud_src())[1])
    got = ends(jira_read(JiraAdapter(transport=Tweaked(jira_server("cloud")).rewrite("/search/jql", broken)), cloud_src())[1])
    assert got == want and all(a and b for a, b, _ in got)


@pytest.mark.parametrize("flavor,path", [("cloud", "/search/jql"), ("dc", "/search")])
@pytest.mark.parametrize("reply", [[], {"errorMessages": ["x"]}, {"issues": "nope"}, "text"])
def test_jira_a_reply_that_is_not_a_search_result_is_refused_with_a_clear_error(jira_env, flavor, path, reply):
    t = Tweaked(jira_server(flavor)).rewrite(path, lambda b, r: reply)
    with pytest.raises(ConnectError, match="search shape"):
        JiraAdapter(transport=t).discover(cloud_src() if flavor == "cloud" else dc_src())


# ---------------------------------------------------------------------------------------------------- Polarion
def _pol_item(i: str, links=()):
    return {"id": i, "type": "requirement", "title": i, "status": "open", "desc": ("text/plain", f"The unit shall {i}."), "links": list(links)}


def _pol_links(src_opts=None, tweak=None, items=None, page_size=100):
    t = polarion_server(items=items)
    if tweak:
        t = Tweaked(t).rewrite("/workitems", tweak)
    ad = PolarionAdapter(transport=t)
    recs, links = split(ad, pol_src(page_size=page_size, **(src_opts or {})))
    return ad, t, recs, links


def test_polarion_the_same_link_seen_from_both_of_its_items_is_one_link(pol_env):
    items = [_pol_item("WI-1", [("implements", "WIDGET/WI-2")]), _pol_item("WI-2", [("implemented_by", "WIDGET/WI-1")])]
    opts = {"role_map": '{"implements": "satisfy", "implemented_by": {"kind": "satisfy", "source": "linked"}}'}
    _, _, _, links = _pol_links(opts, items=items)
    assert ends(links) == [("WIDGET/WI-1", "WIDGET/WI-2", "satisfy")]


def test_polarion_a_404_on_a_later_page_is_not_blamed_on_the_rest_api_being_off(pol_env):
    t = Tweaked(polarion_server()).replace("/workitems", lambda req: text_response("gone", status=404) if req.query.get("page[number]") == "2" else None)
    with pytest.raises(ConnectError) as e:
        PolarionAdapter(transport=t).discover(pol_src(page_size=2))
    assert e.value.status == 404 and "off by default" not in str(e.value)
    with pytest.raises(ConnectError, match="off by default"):                                       # on the first page the advice is right
        PolarionAdapter(transport=polarion_server(rest_disabled=True)).discover(pol_src())


def test_polarion_a_link_with_an_id_of_an_unknown_shape_and_no_included_resource_is_counted_not_guessed(pol_env):
    def bend(body, req):
        for it in body["data"]:
            it.pop("relationships", None)
        body["data"][0]["relationships"] = {"linkedWorkItems": {"data": [{"type": "linkedworkitems", "id": "nonsense"}]}}
        body.pop("included", None)
        return body
    ad, _, _, links = _pol_links(tweak=bend)
    assert links == [] and any("1 links could not be read" in n for n in ad.discover(pol_src()).notes)


def test_polarion_an_included_link_with_no_target_falls_back_to_its_id_and_says_so(pol_env):
    def no_target(body, req):
        for inc in body.get("included", []):
            inc.pop("relationships", None)
        return body
    _, _, _, want = _pol_links()
    ad, _, _, got = _pol_links(tweak=no_target)
    assert ends(got) == ends(want) and want
    assert any("read from the shape of their id" in n for n in ad.discover(pol_src()).notes)


def test_polarion_a_next_link_with_neither_scheme_nor_leading_slash_is_taken_as_relative_to_the_rest_root(pol_env):
    def bare(body, req):
        nxt = (body.get("links") or {}).get("next")
        if nxt:
            body["links"]["next"] = nxt.split("/rest/v1/", 1)[1]
        return body
    _, _, want, _ = _pol_links(page_size=2)
    _, t, got, _ = _pol_links(tweak=bare, page_size=2)
    assert [r.native_id for r in got] == [r.native_id for r in want] and len(t.requests) > 1


def test_polarion_a_work_item_without_an_id_is_skipped(pol_env):
    ghost = lambda body, req: {**body, "data": body["data"] + [{"type": "workitems", "attributes": {"title": "ghost"}}]}   # noqa: E731
    _, _, want, _ = _pol_links(page_size=3)
    _, _, got, _ = _pol_links(tweak=ghost, page_size=3)
    assert [r.native_id for r in got] == [r.native_id for r in want] and "" not in [r.native_id for r in got]


def test_polarion_when_the_attributes_have_no_id_the_short_id_is_the_last_part_of_the_resource_id(pol_env):
    _, _, recs, _ = _pol_links({"fields": "title"})
    r = next(x for x in recs if x.native_id == "WIDGET/WI-1")
    assert r.fields["id"] == "WI-1" and r.fields["_resource_id"] == "WIDGET/WI-1"


def test_polarion_only_included_link_resources_are_links(pol_env):
    link_id = "WIDGET/WI-1/relates_to/WIDGET/WI-2"

    def decoy(body, req):
        body.setdefault("included", []).append({"type": "workitems", "id": link_id, "attributes": {"role": "decoy"},
                                                "relationships": {"workItem": {"data": {"type": "workitems", "id": "WIDGET/WI-99"}}}})
        return body
    _, _, _, want = _pol_links()
    _, _, _, got = _pol_links(tweak=decoy)
    assert ("WIDGET/WI-1", "WIDGET/WI-2", "relates_to") in ends(want) and ends(got) == ends(want)


def test_polarion_a_work_item_that_comes_back_twice_is_kept_once_and_the_note_says_so(pol_env):
    twice = lambda body, req: {**body, "data": body["data"] + body["data"][:1]}                       # noqa: E731
    _, _, want, _ = _pol_links(page_size=3)
    ad, _, got, _ = _pol_links(tweak=twice, page_size=3)
    assert [r.native_id for r in got] == [r.native_id for r in want]
    assert any("came back twice" in n for n in ad.discover(pol_src(page_size=3)).notes)


# ---------------------------------------------------------------------------------------------------- Jama
def jama_ids(recs):
    return [r.native_id for r in recs]


def info(body, **change):
    pi = {**body["meta"]["pageInfo"], **change}
    return {**body, "meta": {**body["meta"], "pageInfo": {k: v for k, v in pi.items() if v is not None}}}


def test_jama_the_next_page_starts_after_the_items_that_came_back_not_after_the_page_size(jama_env):
    cut = lambda b, r: info({**b, "data": b["data"][:2]}, resultCount=2)                              # noqa: E731  (a server that gives fewer than were asked for)
    recs, _ = split(JamaAdapter(transport=Tweaked(jama_server()).rewrite("/abstractitems", cut)), jama_src(page_size=5))
    assert jama_ids(recs) == [str(i["id"]) for i in JAMA_ITEMS]


def test_jama_the_next_page_starts_after_the_servers_own_count_and_the_shortfall_is_reported(jama_env):
    drop_last = lambda b, r: {**b, "data": b["data"][:-1]}                                            # noqa: E731  (resultCount still says 3)
    ad = JamaAdapter(transport=Tweaked(jama_server()).rewrite("/abstractitems", drop_last))
    src = jama_src(page_size=3)
    assert jama_ids(split(ad, src)[0]) == ["100", "101", "103", "104"]
    assert any("WARNING" in n and "totalResults" in n for n in ad.discover(src).notes)


def test_jama_with_no_total_a_short_page_is_the_end_and_nothing_more_is_asked_for(jama_env):
    t = Tweaked(jama_server()).rewrite("/abstractitems", lambda b, r: info(b, totalResults=None))
    recs, _ = split(JamaAdapter(transport=t), jama_src(page_size=3))
    assert len(recs) == len(JAMA_ITEMS)
    assert sum(p.endswith("/abstractitems") for p in t.paths()) == 3                                  # 3 + 3 + 1


def test_jama_a_page_that_says_it_holds_nothing_ends_the_read_even_when_it_sent_rows(jama_env):
    t = Tweaked(jama_server()).rewrite("/abstractitems", lambda b, r: info(b, resultCount=0))
    ad = JamaAdapter(transport=t)
    src = jama_src(page_size=3, max_pages=20)
    assert jama_ids(split(ad, src)[0]) == ["100", "101", "102"]
    assert any("WARNING" in n for n in ad.discover(src).notes)


def test_jama_two_projects_with_one_name_are_refused_and_both_are_named(jama_env):
    t = Tweaked(jama_server()).rewrite("/projects", lambda b, r: {**b, "data": b["data"] + [{"id": 7, "fields": {"name": "Fictional Widget", "projectKey": "WID2"}}]})
    with pytest.raises(ConnectError, match=r"several project.*'WID'.*'WID2'"):
        JamaAdapter(transport=t).discover(jama_src(project="Fictional Widget"))


@pytest.mark.parametrize("path_end,opts", [("/relationshiptypes", {}), ("/picklistoptions/12", {"picklist_fields": "status"})])
def test_jama_a_rejected_login_stops_the_read_in_every_optional_lookup(jama_env, path_end, opts):
    t = Tweaked(jama_server()).replace(path_end, lambda req: json_response({"meta": {"status": "Unauthorized"}}, status=401))
    with pytest.raises(ConnectError) as e:
        JamaAdapter(transport=t).discover(jama_src(**opts))
    assert e.value.status == 401


def test_jama_a_custom_field_named_like_a_built_in_one_keeps_its_suffix_and_does_not_overwrite_it(jama_env):
    items = [{"id": 101, "documentKey": "WID-REQ-1", "itemType": 27, "parent": None,
              "fields": {"name$27": "N", "description$27": "The unit shall be small.", "id$27": "custom-id", "documentKey$27": "custom-key"}}]
    recs, _ = split(JamaAdapter(transport=jama_server(items=items)), jama_src())
    assert [r.native_id for r in recs] == ["101"]
    f = recs[0].fields
    assert (f["id"], f["documentKey"], f["id$27"], f["documentKey$27"]) == ("101", "WID-REQ-1", "custom-id", "custom-key")


def test_jama_a_relationship_with_a_missing_or_null_end_is_not_read(jama_env):
    def bad(body, req):
        kind = {"relationshipType": 4, "type": "relationships", "suspect": False}
        return {**body, "data": body["data"] + [{"id": 90, "fromItem": 101, **kind}, {"id": 91, "fromItem": 101, "toItem": None, **kind},
                                                {"id": 92, "fromItem": None, "toItem": 101, **kind}]}
    want = ends(split(JamaAdapter(transport=jama_server()), jama_src())[1])
    got = ends(split(JamaAdapter(transport=Tweaked(jama_server()).rewrite("/relationships", bad)), jama_src())[1])
    assert got == want and want and all(a and b for a, b, _ in got)


def _status_items(value):
    return [{"id": 101, "documentKey": "WID-REQ-1", "itemType": 27, "parent": None, "fields": {"name$27": "N", "description$27": "The unit shall be small.", "status$27": value}}]


def test_jama_a_pick_list_value_that_is_not_an_id_is_kept_without_asking_the_server(jama_env):
    t = jama_server(items=_status_items("Approved"))
    recs, _ = split(JamaAdapter(transport=t), jama_src(picklist_fields="status"))
    assert recs[0].fields["status"] == "Approved" and not any("/picklistoptions/" in p for p in t.paths())


def test_jama_a_pick_list_option_with_no_name_keeps_its_id(jama_env):
    recs, _ = split(JamaAdapter(transport=jama_server(items=_status_items(12), picks={12: ""})), jama_src(picklist_fields="status"))
    assert recs[0].fields["status"] == "12"


def test_jama_a_pick_list_failure_is_said_once_not_once_per_option(jama_env):
    ad = JamaAdapter(transport=jama_server(fail_picks=True))
    notes = ad.discover(jama_src(picklist_fields="status")).notes
    assert sum(n.startswith("pick list option") for n in notes) == 1


def test_jama_an_item_type_with_no_name_is_shown_by_its_id(jama_env):
    nameless = lambda b, r: {**b, "data": [{**t, "display": ""} for t in b["data"]]}                  # noqa: E731
    recs, _ = split(JamaAdapter(transport=Tweaked(jama_server()).rewrite("/itemtypes", nameless)), jama_src())
    assert {r.fields["itemType"] for r in recs} == {"27", "28", "29"}


# ---------------------------------------------------------------------------------------------------- the .xmi / .mdzip reader
def one_class(extra_attrs="", inside="", head_extra=""):
    model = f'<uml:Model xmi:id="m1"><packagedElement {extra_attrs} xmi:type="uml:Class" xmi:id="r1" name="One">{inside}</packagedElement></uml:Model>'
    return xmi("2.5", model, '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="The unit shall be small."/>', head_extra)


def test_xmi_requirements_come_out_in_the_order_of_the_file_not_the_order_of_their_ids(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="z9" name="Late id, first in the file"/>'
             '<packagedElement xmi:type="uml:Class" xmi:id="a1" name="Early id, second in the file"/></uml:Model>')
    apps = '<sysml:Requirement xmi:id="s1" base_Class="a1" Id="B" Text="t"/><sysml:Requirement xmi:id="s2" base_Class="z9" Id="A" Text="t"/>'
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    assert [r.native_id for r in recs] == ["z9", "a1"]


def test_xmi_several_comments_are_joined_with_a_space_and_a_body_given_as_a_child_element_is_read(tmp_path):
    inside = '<ownedComment xmi:type="uml:Comment" xmi:id="c1" body="First."/><ownedComment xmi:type="uml:Comment" xmi:id="c2"><body>Second.</body></ownedComment>'
    _, recs, _ = run(write(tmp_path, "m.xmi", one_class(inside=inside)))
    assert recs[0].fields["Documentation"] == "First. Second."


def test_xmi_a_profile_around_a_requirement_is_part_of_its_package_path(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Profile" xmi:id="pf1" name="Library">'
             '<packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/></packagedElement></uml:Model>')
    apps = '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t"/>'
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    assert recs[0].fields["Package"] == "Library"


def test_xmi_a_model_element_that_happens_to_have_a_base_attribute_is_still_a_model_element_and_the_pointer_is_not_a_property(tmp_path):
    ad, recs, _ = run(write(tmp_path, "m.xmi", one_class(extra_attrs='base_Thing="x"')))
    assert recs[0].fields["Name"] == "One" and not any(k.startswith("base_") for k in recs[0].fields)
    assert not any("not in this file" in n for n in ad.discover(write(tmp_path, "m.xmi", one_class(extra_attrs='base_Thing="x"'))).notes)


def test_xmi_a_requirement_stereotype_on_something_that_is_not_a_class_is_not_a_requirement(tmp_path):
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Package" xmi:id="p1" name="Pack"/></uml:Model>'
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, '<sysml:Requirement xmi:id="s1" base_Package="p1" Id="A-1" Text="t"/>')))
    assert recs == []


def test_xmi_a_property_named_like_the_readers_own_field_goes_under_the_stereotypes_name_even_for_documentation_and_package(tmp_path):
    apps = '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t" Documentation="D" Package="P" Stereotype="S" ElementType="E"/>'
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Package" xmi:id="p1" name="Real"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/></packagedElement></uml:Model>'
    _, recs, _ = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    f = recs[0].fields
    assert (f["Package"], f["Stereotype"], f["ElementType"]) == ("Real", "Requirement", "Class")
    assert (f["Requirement.Documentation"], f["Requirement.Package"], f["Requirement.Stereotype"], f["Requirement.ElementType"]) == ("D", "P", "S", "E")


def test_xmi_a_stereotype_the_reader_does_not_know_still_names_the_kind_of_the_link(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/><packagedElement xmi:type="uml:Class" xmi:id="b1" name="Block"/>'
             '<packagedElement xmi:type="uml:Abstraction" xmi:id="a1" client="b1" supplier="r1"/></uml:Model>')
    apps = '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t"/><sysml:Allocate xmi:id="s2" base_Abstraction="a1"/>'
    _, _, links = run(write(tmp_path, "m.xmi", xmi("2.5", model, apps)))
    assert ends(links) == [("b1", "r1", "allocate")]


def test_xmi_a_relationship_without_a_client_or_a_supplier_is_counted_and_not_read(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/>'
             '<packagedElement xmi:type="uml:Abstraction" xmi:id="a1" supplier="r1"/></uml:Model>')
    src = write(tmp_path, "m.xmi", xmi("2.5", model, '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t"/>'))
    ad, _, links = run(src)
    assert links == [] and any("1 relationships lack a client or a supplier: not read" in n for n in ad.discover(src).notes)


def test_xmi_a_link_end_that_is_not_in_the_file_is_kept_by_id_and_counted(tmp_path):
    model = ('<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/>'
             '<packagedElement xmi:type="uml:Abstraction" xmi:id="a1" client="gone" supplier="r1"/></uml:Model>')
    src = write(tmp_path, "m.xmi", xmi("2.5", model, '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1" Text="t"/>'))
    ad, _, links = run(src)
    assert ends(links) == [("gone", "r1", "dependency")] and any("1 link ends name an id that is not in this file" in n for n in ad.discover(src).notes)


def test_xmi_a_requirement_with_no_text_is_read_and_counted(tmp_path):
    model = '<uml:Model xmi:id="m1"><packagedElement xmi:type="uml:Class" xmi:id="r1" name="One"/></uml:Model>'
    src = write(tmp_path, "m.xmi", xmi("2.5", model, '<sysml:Requirement xmi:id="s1" base_Class="r1" Id="A-1"/>'))
    ad, recs, _ = run(src)
    assert [r.fields["Text"] for r in recs] == [""] and any("1 requirements have no Text property" in n for n in ad.discover(src).notes)


def test_xmi_an_attribute_called_id_in_another_namespace_is_not_the_xmi_id(tmp_path):
    ad, recs, _ = run(write(tmp_path, "m.xmi", one_class(extra_attrs='other:id="WRONG"', head_extra='xmlns:other="urn:other"')))
    assert recs[0].fields["Name"] == "One"


def test_xmi_two_entries_that_could_both_be_the_model_are_not_chosen_between(tmp_path):
    src = mdzip(tmp_path, {MODEL_ENTRY: xmi("2.4", MODEL, APPS), MODEL_ENTRY + ".xml": xmi("2.4", MODEL, APPS)})
    with pytest.raises(ConnectError, match="cannot tell which entry"):
        list(SysML1XmiAdapter().read(src))


def test_xmi_the_size_limit_is_checked_before_reading_for_a_plain_file_and_for_an_entry(tmp_path):
    with pytest.raises(ConnectError, match=r"allows \(0 MB\)"):
        list(SysML1XmiAdapter().read(Source(write(tmp_path, "m.xmi", xmi("2.5", MODEL, APPS)).uri, {"max_mb": 0})))
    with pytest.raises(ConnectError, match="declares"):
        list(SysML1XmiAdapter().read(Source(mdzip(tmp_path, {MODEL_ENTRY: xmi("2.5", MODEL, APPS)}).uri, {"max_mb": 0})))


def test_xmi_a_doctype_in_the_first_64_kb_is_refused_before_the_parser_is_given_a_single_byte():
    opened = []

    def opener():
        opened.append(1)
        return io.BytesIO(b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><x>&a;</x>')
    with pytest.raises(ConnectError, match="DOCTYPE"):
        list(_events(opener, "m.xmi"))
    assert opened == [1]                                                  # the stream was opened once, for the look at its start, and never again


def test_xmi_more_than_16_mb_before_the_first_element_is_refused():
    big = b"<?xml version='1.0'?><!--" + b"x" * (17 << 20) + b"--><a/>"
    with pytest.raises(ConnectError, match="more than 16 MB"):
        list(_events(lambda: io.BytesIO(big), "m.xmi"))


# ---------------------------------------------------------------------------------------------------- Agility
def ag_ids(t, **opts):
    recs, links = split(AgilityAdapter(transport=t), Source("agility+" + AG_BASE, opts))
    return [r.native_id for r in recs], links, recs


def test_agility_an_asset_that_comes_back_twice_is_kept_once():
    twice = lambda b, r: {**b, "Assets": b["Assets"] + b["Assets"][:1]}                               # noqa: E731
    want, _, _ = ag_ids(agility_server())
    got, _, _ = ag_ids(Tweaked(agility_server()).rewrite("/Data/Story", twice))
    assert got == want and len(set(got)) == len(got)


def test_agility_xml_whose_root_is_not_assets_is_refused():
    with pytest.raises(ConnectError, match="not <Assets>"):
        assets_from_xml(b"<Other><Assets/></Other>")


def test_agility_several_related_assets_in_one_relation_are_all_kept():
    raw = b'<Assets total="1"><Asset id="Story:1"><Relation name="Dependencies"><Asset idref="Story:2"/><Asset idref="Story:3"/></Relation></Asset></Assets>'
    assert _idrefs(assets_from_xml(raw)["Assets"][0]["Attributes"]["Dependencies"]["value"]) == ["Story:2", "Story:3"]


def test_agility_the_parent_and_link_attributes_are_asked_for_even_when_the_select_leaves_them_out():
    t = agility_server()
    ids, links, recs = ag_ids(t, asset_types="Story", select="Number,Name")
    asked = {a for r in t.requests for a in r.query["sel"].split(",")}
    assert {"Super", "Dependencies"} <= asked
    assert len(links) == 1 and next(r for r in recs if r.native_id == "Story:201").parent_native_id == "Epic:100"


@pytest.mark.parametrize("value,want", [("Epic:12", ["Epic:12"]), ("Epic:abc", []), ("12:34", []), ("Epic", []), ("", []), (None, [])])
def test_agility_a_bare_reference_is_an_id_only_when_it_is_a_type_name_and_a_number(value, want):
    assert _idrefs(value) == want


# ---------------------------------------------------------------------------------------------------- OSLC
def test_oslc_a_root_that_is_well_formed_rdf_with_nothing_in_it_is_refused(monkeypatch):
    monkeypatch.setenv("DNG_COOKIE", "JSESSIONID=abc123secret")
    empty = '<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"/>'
    t = Tweaked(oslc_server()).replace("/rm/rootservices", lambda req: text_response(empty, "application/rdf+xml"))
    with pytest.raises(ConnectError, match="no RDF statements"):
        OslcRmAdapter(transport=t).discover(oslc_src())


# ---------------------------------------------------------------------------------------------------- the read-only guard of the sql adapter
@pytest.mark.parametrize("q", ["SELECT 1; SELECT 2", "SELECT 1 ;SELECT 2;", "WITH a AS (SELECT 1) SELECT * FROM a; SELECT 2"])
def test_sql_two_statements_are_refused_even_when_each_is_harmless(q):
    with pytest.raises(ValueError, match="single"):
        check_query(q)


@pytest.mark.parametrize("q", ["VALUES (1)", "EXPLAIN SELECT 1", "SHOW TABLES", "DESCRIBE t", "TABLE t", ""])
def test_sql_only_a_select_or_a_with_statement_is_allowed(q):
    with pytest.raises(ValueError, match="single"):
        check_query(q)
