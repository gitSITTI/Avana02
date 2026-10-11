"""OPTIONAL extra: the same document, converted to PDF by a real word processor (LibreOffice).

Skipped, visibly, when LibreOffice is not installed. The required PDF checks in test_conformance.py never depend on it."""
from __future__ import annotations

import pytest

from reqin import Source, ingest

from test_conformance import COUNT


def test_pdf_made_by_a_word_processor_gives_the_same_result(fx):
    if "pdf_office" not in fx:
        pytest.skip("optional: LibreOffice (soffice) not installed")
    r = ingest(Source(str(fx["pdf_office"])))
    assert r.report["invariant_ok"] and len(r.requirements) == COUNT and not r.rejected
    assert {q.uid for q in r.requirements if not q.uid_synthetic} >= {"REQ-PWR-0201", "REQ-FCS-0101"}
