"""The tripwire has to actually trip. Each test builds a tiny tree and checks the verdict."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import check_no_real_data as g  # noqa: E402


def make(tmp: Path, files: dict[str, bytes | str]) -> list[str]:
    for rel, content in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(content if isinstance(content, bytes) else content.encode())
    return sorted(files)


def run(tmp, files, terms=()):
    return g.scan(tmp, make(tmp, files), [__import__("re").compile(t, 2) for t in terms])


def test_clean_tree_passes(tmp_path):
    assert run(tmp_path, {"README.md": "hi", "src/a.py": "x = 1"}) == []


def test_requirement_export_types_are_refused_outside_the_allowlist(tmp_path):
    for name in ("m.reqif", "m.mdzip", "m.sysml", "m.kpar", "r.xlsx", "r.csv", "s.docx", "s.pdf", "r.db"):
        assert run(tmp_path, {f"stuff/{name}": b"x"}), name


def test_the_one_reviewed_dxl_script_passes_but_every_other_dxl_is_still_refused(tmp_path):
    script = "reqin/connectors/doors9/export_requirements.dxl"
    assert script in g.ALLOW_FILES and len(g.ALLOW_FILES) == 1, "the exemption list is meant to stay tiny"
    assert run(tmp_path, {script: "// DXL export script, no data"}) == []
    for other in ("reqin/connectors/doors9/other.dxl", "stuff/export_requirements.dxl", "export_requirements.dxl",
                  "reqin/connectors/doors9/export_requirements.dxl.csv"):
        assert run(tmp_path, {other: "x"}), other


def test_the_exempt_script_is_still_subject_to_size_and_term_checks(tmp_path):
    script = next(iter(g.ALLOW_FILES))
    assert any("MB" in p for p in run(tmp_path, {script: b"x" * (g.MAX_BYTES + 1)}))
    out = run(tmp_path, {script: "// header\nPROJECT-ZEBRA"}, terms=["project-zebra"])
    assert out and ":2:" in out[0]


def test_files_not_yet_added_to_git_are_checked_too(tmp_path):
    import shutil
    import subprocess
    if shutil.which("git") is None:
        import pytest
        pytest.skip("git not installed")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    make(tmp_path, {"README.md": "x", "notes/new_export.csv": "a,b"})
    assert "notes/new_export.csv" in g.list_files(tmp_path)          # untracked, not ignored
    (tmp_path / ".gitignore").write_text("ignored/\n")
    make(tmp_path, {"ignored/x.csv": "a"})
    assert "ignored/x.csv" not in g.list_files(tmp_path)             # git-ignored files stay out of scope


def test_data_folders_are_refused(tmp_path):
    assert run(tmp_path, {"data/notes.md": "x"})
    assert run(tmp_path, {"a/private/notes.txt": "x"})


def test_allowlisted_file_needs_an_approval_entry(tmp_path):
    f = {g.ALLOW_DIR + "ok.reqif": b"x", g.APPROVALS: "nothing here"}
    assert any("not listed" in p for p in run(tmp_path, f))
    f[g.APPROVALS] = "ok.reqif approved by J. Doe 2026-10-10, ticket ABC-1"
    assert run(tmp_path, f) == []


def test_oversize_file_is_refused(tmp_path):
    assert any("MB" in p for p in run(tmp_path, {"big.js": b"x" * (g.MAX_BYTES + 1)}))


def test_forbidden_terms_are_found_and_not_echoed(tmp_path):
    out = run(tmp_path, {"a.md": "line1\nthe PROJECT-ZEBRA thing"}, terms=["project-zebra"])
    assert out and "a.md:2" in out[0] and "zebra" not in out[0].lower()


def test_main_says_when_no_term_list_was_used(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)
    make(tmp_path, {"README.md": "x"})
    assert g.main(["--root", str(tmp_path)]) == 0
    assert "structure checks only" in capsys.readouterr().out
