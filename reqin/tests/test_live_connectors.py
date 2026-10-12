"""Live connectors, tested against in-memory fakes (see live_cases.py). Every connector here is 'fake-server-tested'.

Each test below would FAIL if the behaviour it names were removed: paging, the guard against a non-advancing server,
secret scrubbing, read-only, the document join. Run `reqin connectors` to see each adapter's maturity.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from live_cases import (AG_BASE, AG_FILTERED, AG_GOLD, AG_LINKS, AG_OK, AG_REJECTED, OSLC_GOLD, OSLC_LINKS, OSLC_OK, OSLC_REJECTED,
                        OSLC_ROOT, SYSML_BASE, SYSML_GOLD, SYSML_LINKS, SYSML_OK, SYSML_REJECTED, agility_assets, agility_server,
                        oslc_server, sysml_server)
from reqin import Profile, Source, ingest
from reqin.adapter import pick_adapter, sniff_all
from reqin.adapters.agility import AgilityAdapter, oid_of
from reqin.adapters.oslc_rm import OslcRmAdapter
from reqin.adapters.sysml_api import SysMLApiAdapter
from reqin.connect import ConnectError
from reqin.testing import check_adapter

ROOT = Path(__file__).parent.parent
SYS_PROFILE = Profile.from_yaml((ROOT / "profiles/sysml_api.yaml").read_text())
OSLC_PROFILE = Profile.from_yaml((ROOT / "profiles/oslc_rm.yaml").read_text())
AG_PROFILE = Profile.from_yaml((ROOT / "profiles/agility_api.yaml").read_text())


def sysml_src(**opts) -> Source:
    return Source("sysml+" + SYSML_BASE, {"project_name": "Fictional Widget Controller", "token_env": "TWC_TOKEN", **opts})


@pytest.fixture(autouse=True)
def _token(monkeypatch):
    monkeypatch.setenv("TWC_TOKEN", "s3cr3t-token-value")


# ---------------------------------------------------------------------------------------------------- SysML v2 REST
@pytest.mark.parametrize("size", [4, 5, 15, 100])          # 15 elements: exact multiple, exact fit, and one big page
@pytest.mark.parametrize("mode", ["link", "cursor", "all"])
def test_sysml_reads_every_element_whatever_the_paging(mode, size):
    t = sysml_server(mode=mode)
    r = check_adapter(lambda: SysMLApiAdapter(transport=t), sysml_src(page_size=size), SYS_PROFILE,
                      expect_ok=SYSML_OK, expect_rejected=SYSML_REJECTED, expect_links=SYSML_LINKS, gold_text=SYSML_GOLD)
    assert {q.uid for q in r.requirements} == set(SYSML_GOLD)


def test_sysml_underscore_page_style():
    t = sysml_server(mode="cursor", style="underscore")
    check_adapter(lambda: SysMLApiAdapter(transport=t), sysml_src(page_size=4, page_style="underscore"), SYS_PROFILE,
                  expect_ok=SYSML_OK, expect_rejected=SYSML_REJECTED, expect_links=SYSML_LINKS)


def test_sysml_refuses_a_server_it_cannot_page_instead_of_truncating():
    t = sysml_server(mode="stuck")
    with pytest.raises(ConnectError, match="not advancing"):
        ingest(sysml_src(page_size=4), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=t))


def test_sysml_link_only_mode_refuses_a_full_page_without_a_link():
    t = sysml_server(mode="cursor")
    with pytest.raises(ConnectError, match="without a Link header"):
        ingest(sysml_src(page_size=4, paging="link"), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=t))


def test_sysml_joins_documentation_hierarchy_and_links():
    t = sysml_server()
    r = ingest(sysml_src(), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=t))
    by = {q.uid: q for q in r.requirements}
    assert by["REQ-002"].text == "The controller shall record every fault. Each record shall include a timestamp."   # two Documentation elements
    assert by["REQ-003"].text == "The controller shall restart within 30 seconds."                                    # reached through `documentation` list
    assert by["REQ-003"].parent_mid == by["REQ-002"].mid                                                               # nested usage -> parent
    assert by["REQ-001"].parent_mid is None                                                                            # owner is a Package
    assert {(l.source_uid, l.kind, l.target_uid) for l in r.links} == {("REQ-003", "trace", "REQ-001"), ("REQ-001", "trace", "p1")}
    assert [x.reason for x in r.rejected] == ["empty statement text"]
    assert by["REQ-001"].extra.get("prop.isAbstract") is False                                                        # plain properties are kept


def test_sysml_resolves_default_branch_head_and_named_branch():
    t = sysml_server()
    ad = SysMLApiAdapter(transport=t)
    assert ingest(sysml_src(), profile=SYS_PROFILE, adapter=ad).report["revision"] == "P1@C9"
    assert any(p.endswith("/commits/C9/elements") for p in t.paths())
    ad2 = SysMLApiAdapter(transport=t)
    r = ingest(sysml_src(branch="draft"), profile=SYS_PROFILE, adapter=ad2)           # draft = C7 = first 3 elements only
    assert r.report["revision"] == "P1@C7" and len(r.requirements) == 1
    r3 = ingest(sysml_src(commit_id="C9"), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=sysml_server()))
    assert r3.report["revision"] == "P1@C9"


def test_sysml_falls_back_to_project_id_as_commit_like_syson_and_says_so():
    t = sysml_server(head=False)
    ad = SysMLApiAdapter(transport=t)
    r = ingest(sysml_src(), profile=SYS_PROFILE, adapter=ad)
    assert r.report["revision"] == "P1@P1" and len(r.requirements) == SYSML_OK
    assert any("project id as the commit id" in n for n in ad.discover(sysml_src()).notes)


def test_sysml_unknown_project_lists_what_exists():
    with pytest.raises(ConnectError, match="Another Fictional Model"):
        SysMLApiAdapter(transport=sysml_server()).discover(Source("sysml+" + SYSML_BASE, {"project_name": "Nope"}))


def test_sysml_key_names_are_configurable_without_code_changes():
    renamed = [{**e, "@type": {"RequirementDefinition": "ReqDef"}.get(e["@type"], e["@type"])} for e in
               __import__("live_cases").SYSML_ELEMENTS]
    t = sysml_server(elements=renamed)
    r = ingest(sysml_src(req_types="ReqDef,RequirementUsage"), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=t))
    assert len(r.requirements) == SYSML_OK


def test_sysml_is_discovered_by_scheme_and_by_path():
    assert sniff_all(Source("sysml+https://h/x"))[0][1] == "sysml_api"
    assert sniff_all(Source("https://h:8443/sysmlv2-api"))[0][1] == "sysml_api"
    assert pick_adapter(Source("sysml+https://h/x")).name == "sysml_api"
    assert not [s for s in sniff_all(Source("https://example.test/page"))]


# ---------------------------------------------------------------------------------------------- safety, all connectors
def test_credentials_come_from_the_environment_and_are_never_printed(monkeypatch):
    t = sysml_server(token_required="a-different-token")                 # server rejects our token
    with pytest.raises(ConnectError) as e:
        ingest(sysml_src(), profile=SYS_PROFILE, adapter=SysMLApiAdapter(transport=t))
    assert "403" in str(e.value) and "s3cr3t-token-value" not in str(e.value)
    assert t.requests[0].headers["Authorization"] == "Bearer s3cr3t-token-value"
    monkeypatch.delenv("TWC_TOKEN")
    with pytest.raises(ConnectError, match="TWC_TOKEN is not set"):
        SysMLApiAdapter(transport=sysml_server()).discover(sysml_src())


def test_only_get_requests_are_made_and_the_audit_has_no_secrets():
    t = sysml_server()
    ad = SysMLApiAdapter(transport=t)
    ingest(sysml_src(), profile=SYS_PROFILE, adapter=ad)
    audit = ad.audit()
    assert audit and all(a.method == "GET" for a in audit)
    assert not any("s3cr3t" in a.url for a in audit)
    assert len(audit) == len(t.requests)


def test_a_live_connector_reads_once_per_run_not_twice():
    t = sysml_server()
    ad = SysMLApiAdapter(transport=t)
    ingest(sysml_src(page_size=500), adapter=ad)                          # no profile: the pipeline calls discover() THEN read()
    assert t.paths().count("/sysmlv2-api/projects/P1/commits/C9/elements") == 1


# ------------------------------------------------------------------------------------------------ OSLC RM (DOORS Next)
def oslc_src(**opts) -> Source:
    return Source("oslc+" + OSLC_ROOT + "/rm/rootservices", {"project": "Fictional Widget Project", "cookie_env": "DNG_COOKIE", **opts})


@pytest.fixture
def _cookie(monkeypatch):
    monkeypatch.setenv("DNG_COOKIE", "JSESSIONID=abc123secret")


@pytest.mark.parametrize("page_size", [1, 3, 7, 50])
def test_oslc_discovers_the_query_base_and_follows_nextpage(page_size, _cookie):
    t = oslc_server()
    r = check_adapter(lambda: OslcRmAdapter(transport=t), oslc_src(page_size=page_size), OSLC_PROFILE, expect_ok=OSLC_OK,
                      expect_rejected=OSLC_REJECTED, expect_links=OSLC_LINKS, gold_text=OSLC_GOLD)
    assert {q.uid for q in r.requirements} == set(OSLC_GOLD)
    q = [x for x in t.requests if x.path == "/rm/views"]
    assert q and all(x.query["projectURL"] == "PA1" for x in q)              # the right project's query capability, not PA2's


def test_oslc_links_have_the_right_direction_and_are_not_duplicated(_cookie):
    r = ingest(oslc_src(), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server()))
    got = {(l.source_uid, l.kind, l.target_uid) for l in r.links}
    assert got == {("1", "contain", "2"), ("1", "contain", "3"),          # 1 decomposedBy 2,3 -- and 2 decomposes 1 says the SAME thing: once
                   ("5", "satisfy", "3"),                                  # 3 satisfiedBy 5  =>  5 satisfies 3
                   (OSLC_ROOT + "/ext/TC-1", "verify", "6")}               # 6 validatedBy TC-1  =>  TC-1 verifies 6 (outside this import: kept by URI)
    assert len(r.links) == 4


def test_oslc_keeps_unselected_link_properties_as_plain_fields_so_nothing_is_lost(_cookie):
    r = ingest(oslc_src(), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server()))
    seven = next(q for q in r.requirements if q.uid == "7")
    assert OSLC_ROOT + "/ext/CR-9" in str(seven.extra.get("oslc_rm:trackedBy"))
    r2 = ingest(oslc_src(links="all"), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server()))
    assert len(r2.links) == OSLC_LINKS + 1 and not next(q for q in r2.requirements if q.uid == "7").extra.get("oslc_rm:trackedBy")
    r3 = ingest(oslc_src(links="none"), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server()))
    assert r3.links == []


def test_oslc_sends_the_required_headers_and_the_configuration_context(_cookie):
    t = oslc_server()
    ingest(oslc_src(configuration="https://dng.example.test/rm/cm/stream/_S1"), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=t))
    assert all(r.headers["OSLC-Core-Version"] == "2.0" and "rdf+xml" in r.headers["Accept"] for r in t.requests)
    assert all(r.headers["Configuration-Context"] == "https://dng.example.test/rm/cm/stream/_S1" for r in t.requests)
    assert all(r.headers["Cookie"] == "JSESSIONID=abc123secret" for r in t.requests)


def test_oslc_project_selection_errors_name_the_choices(_cookie):
    with pytest.raises(ConnectError, match="Another Fictional Project"):
        OslcRmAdapter(transport=oslc_server()).discover(oslc_src(project="Nope"))
    with pytest.raises(ConnectError, match="several projects.*Fictional Widget Project"):
        OslcRmAdapter(transport=oslc_server()).discover(Source("oslc+" + OSLC_ROOT + "/rm/rootservices", {"cookie_env": "DNG_COOKIE"}))


def test_oslc_query_filter_is_passed_with_prefixes(_cookie):
    t = oslc_server()
    ingest(oslc_src(where='dcterms:title="Mass"'), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=t))
    q = next(x for x in t.requests if x.path == "/rm/views")
    assert q.query["oslc.where"] == 'dcterms:title="Mass"' and "dcterms=<http://purl.org/dc/terms/>" in q.query["oslc.prefix"]


def test_oslc_query_base_shortcut_skips_discovery(_cookie):
    t = oslc_server()
    qb = OSLC_ROOT + "/rm/views?oslc.query=true&projectURL=PA1"
    r = ingest(oslc_src(query_base=qb), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=t))
    assert len(r.requirements) == OSLC_OK and set(t.paths()) == {"/rm/views"}


def test_oslc_reads_turtle_as_well_as_rdfxml(_cookie):
    r = ingest(oslc_src(), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server(turtle_catalog=True)))
    assert len(r.requirements) == OSLC_OK


def test_oslc_refuses_a_server_whose_paging_loops(_cookie):
    with pytest.raises(ConnectError, match="not advancing"):
        ingest(oslc_src(page_size=3), profile=OSLC_PROFILE, adapter=OslcRmAdapter(transport=oslc_server(loop=True)))


def test_oslc_says_so_when_the_server_answers_with_a_login_page(_cookie):
    with pytest.raises(ConnectError, match="did not return RDF.*login"):
        OslcRmAdapter(transport=oslc_server(login_page=True)).discover(oslc_src())


def test_oslc_warns_when_totalcount_disagrees_with_what_was_read(_cookie):
    notes = OslcRmAdapter(transport=oslc_server()).discover(oslc_src(page_size=3)).notes
    assert not any("WARNING" in n for n in notes)
    lying = OslcRmAdapter(transport=oslc_server(report_total=99)).discover(oslc_src()).notes
    assert any("totalCount 99" in n and "WARNING" in n for n in lying)


def test_oslc_is_read_only_and_its_audit_hides_the_cookie(_cookie):
    t = oslc_server()
    ad = OslcRmAdapter(transport=t)
    ingest(oslc_src(), profile=OSLC_PROFILE, adapter=ad)
    assert ad.audit() and all(a.method == "GET" for a in ad.audit())
    assert not any("abc123secret" in a.url for a in ad.audit())


def test_oslc_reads_once_per_run_not_twice(_cookie):
    t = oslc_server()
    ad = OslcRmAdapter(transport=t)
    ad.discover(oslc_src(page_size=3))
    after_discover = len(t.requests)
    assert after_discover > 0
    list(ad.read(oslc_src(page_size=3)))
    ad.revision(oslc_src(page_size=3))
    assert len(t.requests) == after_discover, "the second look at the same source went back to the server"


def test_oslc_sniff():
    assert sniff_all(Source("oslc+https://h/rm/rootservices"))[0][1] == "oslc_rm"
    assert sniff_all(Source("https://h/rm/rootservices"))[0][1] == "oslc_rm"


# ---------------------------------------------------------------------------------------- Digital.ai Agility (VersionOne)
def ag_src(**opts) -> Source:
    return Source("agility+" + AG_BASE, {"token_env": "AGILITY_TOKEN", **opts})


@pytest.fixture
def _ag_token(monkeypatch):
    monkeypatch.setenv("AGILITY_TOKEN", "agility-secret-token")


@pytest.mark.parametrize("size", [1, 2, 500])
def test_agility_reads_every_asset_type_page_by_page(size, _ag_token):
    t = agility_server()
    r = check_adapter(lambda: AgilityAdapter(transport=t), ag_src(page_size=size), AG_PROFILE, expect_ok=AG_OK, expect_rejected=AG_REJECTED,
                      expect_links=AG_LINKS, gold_text=AG_GOLD)
    assert r.report["filtered_out"] == {"row filter (where) did not match": AG_FILTERED}
    assert {q.uid for q in r.requirements} == set(AG_GOLD)


def test_agility_hierarchy_links_and_status_labels(_ag_token):
    r = ingest(ag_src(), profile=AG_PROFILE, adapter=AgilityAdapter(transport=agility_server()))
    by = {q.uid: q for q in r.requirements}
    assert by["S-01201"].parent_mid == by["E-00100"].mid and by["B-00301"].parent_mid is None
    assert [(l.source_uid, l.kind, l.target_uid) for l in r.links] == [("S-01201", "trace", "S-01202")]
    assert by["S-01202"].fields["status"] == "Future" and by["E-00100"].fields["status"] == "Active"
    assert by["S-01201"].fields["owner"] == "Fictional Project"


def test_agility_identity_ignores_the_moment_that_changes_with_every_edit(_ag_token):
    a = ingest(ag_src(), profile=AG_PROFILE, adapter=AgilityAdapter(transport=agility_server(agility_assets(moment=1))))
    b = ingest(ag_src(), profile=AG_PROFILE, adapter=AgilityAdapter(transport=agility_server(agility_assets(moment=999))))
    assert [q.mid for q in a.requirements] == [q.mid for q in b.requirements]
    assert oid_of("Story:1005:1236") == oid_of("Story:1005") == "Story:1005"


def test_agility_request_shape_matches_the_documented_api(_ag_token):
    t = agility_server()
    ingest(ag_src(page_size=2, where="Scope.Name='Fictional Project'"), profile=AG_PROFILE, adapter=AgilityAdapter(transport=t))
    first = t.requests[0]
    assert first.path == "/Instance/rest-1.v1/Data/Epic" and first.query["page"] == "2,0"
    assert first.query["where"] == "Scope.Name='Fictional Project'" and "Number" in first.query["sel"].split(",")
    assert first.headers["Accept"] == "application/json" and first.headers["Authorization"] == "Bearer agility-secret-token"
    story_pages = [r.query["page"] for r in t.requests if r.path.endswith("/Story")]
    assert story_pages == ["2,0", "2,2"]


def test_agility_refuses_a_server_that_ignores_the_page_parameter_and_repeats_itself(_ag_token):
    with pytest.raises(ConnectError, match="not advancing"):
        ingest(ag_src(page_size=2), profile=AG_PROFILE, adapter=AgilityAdapter(transport=agility_server(stuck=True)))


def test_agility_without_total_stops_on_a_short_page(_ag_token):
    r = ingest(ag_src(page_size=2), profile=AG_PROFILE, adapter=AgilityAdapter(transport=agility_server(drop_total=True)))
    assert len(r.requirements) == AG_OK


def test_agility_wrong_shape_is_reported_as_a_likely_login_page(_ag_token):
    with pytest.raises(ConnectError, match="did not return JSON|documented"):
        AgilityAdapter(transport=agility_server(wrong_shape=True)).discover(ag_src())


def test_agility_token_is_required_from_the_environment_and_not_leaked(monkeypatch):
    monkeypatch.setenv("AGILITY_TOKEN", "agility-secret-token")
    with pytest.raises(ConnectError) as e:
        AgilityAdapter(transport=agility_server(token="other")).discover(ag_src())
    assert "401" in str(e.value) and "agility-secret-token" not in str(e.value)
    monkeypatch.delenv("AGILITY_TOKEN")
    with pytest.raises(ConnectError, match="AGILITY_TOKEN is not set"):
        AgilityAdapter(transport=agility_server()).discover(ag_src())


def test_agility_is_read_only_and_audited(_ag_token):
    t = agility_server()
    ad = AgilityAdapter(transport=t)
    ingest(ag_src(), profile=AG_PROFILE, adapter=ad)
    assert ad.audit() and all(a.method == "GET" for a in ad.audit()) and not any("secret" in a.url for a in ad.audit())


def test_agility_reads_once_per_run_not_twice(_ag_token):
    t = agility_server()
    ad = AgilityAdapter(transport=t)
    ad.discover(ag_src(page_size=2))
    after_discover = len(t.requests)
    assert after_discover > 0
    list(ad.read(ag_src(page_size=2)))
    ad.revision(ag_src(page_size=2))
    assert len(t.requests) == after_discover, "the second look at the same source went back to the server"


def test_agility_sniff():
    assert sniff_all(Source("agility+https://h/Inst"))[0][1] == "agility"
    assert sniff_all(Source("https://h/Inst/rest-1.v1/Data/Story"))[0][1] == "agility"


# ------------------------------------------------------------------------------------------------------- the registry
LIVE_ADAPTERS = {"sysml_api": SysMLApiAdapter, "oslc_rm": OslcRmAdapter, "agility": AgilityAdapter}


def test_every_fake_server_tested_adapter_has_live_tests_and_nothing_claims_to_be_live_verified():
    from reqin.adapter import load_adapters
    builtin = {n: c for n, c in load_adapters().items() if c.__module__.startswith("reqin.adapters.")}      # a plugin you installed has its own tests
    claimed = {n for n, c in builtin.items() if c.maturity == "fake-server-tested"}
    assert claimed == set(LIVE_ADAPTERS), "a connector says fake-server-tested but has no tests here, or the reverse"
    assert not [n for n, c in builtin.items() if c.maturity == "live-verified"], \
        "only a person who ran a connector against the real system may set live-verified, and this repo has no such evidence"
