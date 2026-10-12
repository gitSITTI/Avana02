"""Template tests. Keep them green, then extend the fake so it matches what the REAL server sent you in `reqin sample`."""
from __future__ import annotations

from pathlib import Path

import pytest

from reqin import Profile, Source, ingest
from reqin.connect import ConnectError
from reqin.testing import FakeTransport, Req, check_adapter, json_response, text_response

from reqin_acme.adapter import AcmeAdapter

BASE = "acme+https://acme.example.test/api"
ITEMS = [  # synthetic and fictional. Never put real requirement text in a test.
    {"id": 1, "key": "ACME-1", "statement": "<p>The widget shall start within 5 s.</p>", "rev": "7"},
    {"id": 2, "key": "ACME-2", "statement": "The widget shall log every fault.", "parent": 1, "rev": "7"},
    {"id": 3, "key": "ACME-3", "statement": "", "rev": "7"},                       # empty: must be REJECTED with a reason
    {"id": 4, "key": "ACME-4", "statement": "The widget shall weigh under 2 kg.", "parent": 1, "rev": "8"},
    {"id": 5, "key": "ACME-5", "statement": "The widget shall survive 5 g of vibration.", "rev": "8"},
]
GOLD = {"ACME-1": "The widget shall start within 5 s.", "ACME-2": "The widget shall log every fault.",
        "ACME-4": "The widget shall weigh under 2 kg.", "ACME-5": "The widget shall survive 5 g of vibration."}
PROFILE = Profile.from_yaml((Path(__file__).parent.parent / "profile.yaml").read_text())


def server(page: int = 2, token: str | None = None, loop: bool = False) -> FakeTransport:
    t = FakeTransport()

    def handler(req: Req):
        if token and req.headers.get("Authorization") != f"Bearer {token}":
            return json_response({"error": "no"}, status=401)
        if "start" not in req.query and "page_size" in req.query:
            page_size = int(req.query["page_size"])
        else:
            page_size = page
        start = int(req.query.get("start", 0))
        chunk = ITEMS[start:start + page_size]
        nxt = f"https://acme.example.test/api/requirements?start={start + page_size}&page_size={page_size}" if start + page_size < len(ITEMS) else None
        if loop:
            nxt = f"https://acme.example.test/api/requirements?start={start}&page_size={page_size}"
        return json_response({"items": chunk, "next": nxt})
    return t.add("/api/requirements", handler)


@pytest.mark.parametrize("page", [1, 2, 5, 100])
def test_reads_everything_whatever_the_page_size(page):
    t = server(page=page)
    r = check_adapter(lambda: AcmeAdapter(transport=t), Source(BASE, {"page_size": page}), PROFILE, expect_ok=4, expect_rejected=1, gold_text=GOLD)
    by = {q.uid: q for q in r.requirements}
    assert by["ACME-2"].parent_mid == by["ACME-1"].mid


def test_secret_comes_from_the_environment_and_is_not_leaked(monkeypatch):
    monkeypatch.setenv("ACME_TOKEN", "super-secret-value")
    with pytest.raises(ConnectError) as e:
        AcmeAdapter(transport=server(token="other")).discover(Source(BASE, {"token_env": "ACME_TOKEN"}))
    assert "401" in str(e.value) and "super-secret-value" not in str(e.value)


def test_a_server_that_repeats_its_next_link_is_refused_not_looped():
    with pytest.raises(ConnectError, match="not advancing"):
        ingest(Source(BASE), profile=PROFILE, adapter=AcmeAdapter(transport=server(loop=True)))


def test_only_get_requests_are_made():
    t = server()
    ad = AcmeAdapter(transport=t)
    ingest(Source(BASE), profile=PROFILE, adapter=ad)
    assert ad.audit() and all(a.method == "GET" for a in ad.audit())


def test_reads_once_per_run_not_twice():
    t = server(page=100)
    ingest(Source(BASE), adapter=AcmeAdapter(transport=t))          # no profile: discover() and read() both run
    assert len(t.requests) == 1


def test_never_claims_to_be_live_verified():
    assert AcmeAdapter.maturity != "live-verified"
