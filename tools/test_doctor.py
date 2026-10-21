import importlib.util
from pathlib import Path

P = Path(__file__).with_name("doctor.py")
spec = importlib.util.spec_from_file_location("doctor", P)
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


def test_required_dependencies_block_readiness_and_secret_values_are_never_reported():
    r = doctor.inspect(installed=set(), which=lambda name: None, env={"DENYLIST_TERMS": "private-canary-value"})
    assert not r["ready"]
    assert "private-canary-value" not in str(r)
    assert any(c["name"] == "package: pyyaml" and not c["ok"] for c in r["checks"])


def test_core_does_not_claim_browser_or_deployment_readiness():
    installed = {"pyyaml", "openpyxl", "reqif", "sqlalchemy", "python-docx", "pdfplumber", "pytest", "reportlab", "rdflib", "trustme"}
    r = doctor.inspect(installed=installed, which=lambda n: "/bin/node" if n == "node" else None, env={})
    assert r["ready"]
    assert not doctor.inspect("browser", installed=installed, which=lambda n: "/bin/node", env={})["ready"]
    assert not doctor.inspect("release", installed=installed, which=lambda n: None, env={})["ready"]
