"""The secret and private-term guards must fail when they should, and stay quiet when they should.

Every test builds a throwaway git repository and breaks it on purpose: a made-up private word, a made-up token. Nothing here
names a real term. The "private word" is an invented one, and the fake token is assembled at run time so that this file itself
is not something gitleaks would flag.

The gitleaks tests need the gitleaks binary. They skip when it is missing (python tools/run_gitleaks.py install adds it), unless
REQUIRE_GITLEAKS=1 is set, as it is in the CI job that exists to run them.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
TOOLS = REPO / "tools"
DENY = [sys.executable, str(TOOLS / "denylist_check.py")]
WORD = "zebrafish-quarry"          # invented; stands in for a private term
SEPARATED = "~quasar9"             # invented; separator-insensitive


def fake_token() -> str:
    return "gh" + "p_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"[:36]


def run(cmd, cwd, env=None, **kw):
    merged = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}
    for name in ("DENYLIST_TERMS", "DENYLIST_FILE", "DENYLIST_OPTIONAL", "GITHUB_ACTIONS", "GITLAB_CI"):
        merged.pop(name, None)
    merged.update(env or {})
    return subprocess.run(cmd, cwd=cwd, env=merged, capture_output=True, text=True, **kw)


def git(cwd, *args, env=None):
    return run(["git", *args], cwd, env=env)


@pytest.fixture()
def repo(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-q", "-b", "main")
    git(work, "config", "user.name", "Test Author")
    git(work, "config", "user.email", "test@example.invalid")
    (work / "README.md").write_text("hello\n", encoding="utf-8")
    git(work, "add", ".")
    git(work, "commit", "-q", "-m", "first")
    return work


@pytest.fixture()
def terms_file(tmp_path):
    f = tmp_path / "terms.txt"
    f.write_text(f"# comment\n\n   \n{WORD}\n{SEPARATED}\n", encoding="utf-8")
    return {"DENYLIST_FILE": str(f)}


def stage(repo, name, text):
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    git(repo, "add", name)


# ---- the private-term list ---------------------------------------------------------------------------------------------

def test_clean_staged_change_passes(repo, terms_file):
    stage(repo, "a.md", "nothing private here\n")
    done = run(DENY + ["staged"], repo, terms_file)
    assert done.returncode == 0, done.stderr


def test_a_term_in_a_staged_file_fails_and_is_never_printed(repo, terms_file):
    stage(repo, "notes/a.md", f"line one\nsee the {WORD.upper()} report\n")
    done = run(DENY + ["staged"], repo, terms_file)
    assert done.returncode == 1
    assert "notes/a.md:2" in done.stderr
    assert WORD not in (done.stdout + done.stderr).lower(), "the matched text must not be printed"


def test_a_term_in_a_file_name_fails(repo, terms_file):
    stage(repo, f"{WORD}.txt", "harmless\n")
    done = run(DENY + ["staged"], repo, terms_file)
    assert done.returncode == 1 and "(file name)" in done.stderr


def test_a_term_in_a_binary_file_is_skipped(repo, terms_file):
    path = repo / "blob.bin"
    path.write_bytes(b"\0\0" + WORD.encode() + b"\0")
    git(repo, "add", "blob.bin")
    assert run(DENY + ["staged"], repo, terms_file).returncode == 0


def test_blank_and_comment_lines_do_not_match_everything(repo, tmp_path):
    f = tmp_path / "only-blanks.txt"
    f.write_text("\n   \n# nothing here\n", encoding="utf-8")
    stage(repo, "a.md", "anything at all\n")
    done = run(DENY + ["staged"], repo, {"DENYLIST_FILE": str(f)})
    assert done.returncode == 0 and "did not run" in done.stderr


def test_without_a_list_locally_it_says_so_and_passes(repo):
    stage(repo, "a.md", f"{WORD}\n")
    done = run(DENY + ["staged"], repo)
    assert done.returncode == 0 and "did not run" in done.stderr


def test_the_list_can_come_from_an_environment_variable(repo):
    stage(repo, "a.md", f"about {WORD}\n")
    done = run(DENY + ["staged"], repo, {"DENYLIST_TERMS": f"{WORD}\r\nother\r\n"})
    assert done.returncode == 1


def test_a_dot_denylist_file_in_the_repo_root_is_used(repo):
    (repo / ".denylist").write_text(WORD + "\n", encoding="utf-8")
    stage(repo, "a.md", WORD + "\n")
    assert run(DENY + ["staged"], repo).returncode == 1


def test_a_tracked_term_list_is_itself_a_failure(repo, terms_file):
    stage(repo, ".denylist", "unrelated\n")
    done = run(DENY + ["staged"], repo, terms_file)
    assert done.returncode == 1 and "must never be tracked" in done.stderr


@pytest.mark.parametrize("text,hit", [
    ("QUASAR-9 radar", True), ("quasar 9", True), ("Quasar_9s", True), ("quasar9", True),
    ("pquasar9", False), ("quasar 91", False), ("a quasar", False),
])
def test_tilde_terms_ignore_separators_but_not_word_edges(repo, terms_file, text, hit):
    stage(repo, "a.md", text + "\n")
    assert (run(DENY + ["staged"], repo, terms_file).returncode == 1) is hit


def test_a_letter_ending_tilde_term_does_not_run_across_a_space_into_the_next_word(repo, tmp_path):
    f = tmp_path / "t.txt"
    f.write_text("~kolmar\n", encoding="utf-8")
    stage(repo, "a.md", "the Kol Marathon route\nthe MKOLMAR tool\n")
    assert run(DENY + ["staged"], repo, {"DENYLIST_FILE": str(f)}).returncode == 0
    stage(repo, "b.md", "signed by K. Olmar\n")
    assert run(DENY + ["staged"], repo, {"DENYLIST_FILE": str(f)}).returncode == 1


def test_commit_message_and_author_identity(repo, terms_file, tmp_path):
    msg = tmp_path / "msg"
    msg.write_text("a perfectly fine message\n", encoding="utf-8")
    assert run(DENY + ["message", str(msg)], repo, terms_file).returncode == 0
    msg.write_text(f"mentions {WORD}\n", encoding="utf-8")
    done = run(DENY + ["message", str(msg)], repo, terms_file)
    assert done.returncode == 1 and "commit message" in done.stderr
    msg.write_text("fine again\n", encoding="utf-8")
    git(repo, "config", "user.email", f"someone@{WORD}.example")
    done = run(DENY + ["message", str(msg)], repo, terms_file)
    assert done.returncode == 1 and "author identity" in done.stderr


def test_tree_mode_sees_untracked_files_that_are_not_ignored(repo, terms_file):
    (repo / "new.md").write_text(WORD, encoding="utf-8")          # not added to git at all
    assert run(DENY + ["tree"], repo, terms_file).returncode == 1
    (repo / ".gitignore").write_text("new.md\n", encoding="utf-8")
    assert run(DENY + ["tree"], repo, terms_file).returncode == 0


def test_history_finds_a_term_that_was_later_deleted(repo, terms_file):
    stage(repo, "a.md", f"oops {WORD}\n")
    git(repo, "commit", "-q", "-m", "add")
    stage(repo, "a.md", "fixed\n")
    git(repo, "commit", "-q", "-m", "remove it again")
    assert run(DENY + ["tree"], repo, terms_file).returncode == 0, "the working tree is clean"
    done = run(DENY + ["history"], repo, terms_file)
    assert done.returncode == 1 and "a.md" in done.stderr, "but the term is still in history"


def test_history_checks_commit_messages_and_authors(repo, terms_file):
    git(repo, "commit", "-q", "--allow-empty", "-m", f"wip {WORD}")
    assert run(DENY + ["history"], repo, terms_file).returncode == 1
    clean = repo.parent / "clean"
    clean.mkdir()
    git(clean, "init", "-q", "-b", "main")
    git(clean, "-c", "user.name=A", "-c", "user.email=a@b.invalid", "commit", "-q", "--allow-empty", "-m", "ok")
    assert run(DENY + ["history"], clean, terms_file).returncode == 0
    git(clean, "-c", f"user.name={WORD}", "-c", "user.email=a@b.invalid", "commit", "-q", "--allow-empty", "-m", "ok2")
    assert run(DENY + ["history"], clean, terms_file).returncode == 1


def test_history_checks_branch_names(repo, terms_file):
    git(repo, "branch", f"feature/{WORD}")
    assert run(DENY + ["history"], repo, terms_file).returncode == 1


def test_in_ci_the_log_gets_a_count_and_no_locations(repo, terms_file):
    stage(repo, "secret-place.md", WORD + "\n")
    done = run(DENY + ["staged"], repo, {**terms_file, "GITHUB_ACTIONS": "true"})
    assert done.returncode == 1
    assert "found 1 place" in done.stderr and "secret-place" not in done.stderr


def test_ci_mode_fails_without_a_list_unless_optional(repo):
    assert run(DENY + ["ci"], repo).returncode == 1
    optional = run(DENY + ["ci"], repo, {"DENYLIST_OPTIONAL": "1"})
    assert optional.returncode == 0


def test_ci_mode_runs_tree_and_history_together(repo, terms_file):
    assert run(DENY + ["ci"], repo, terms_file).returncode == 0
    git(repo, "commit", "-q", "--allow-empty", "-m", WORD)
    assert run(DENY + ["ci"], repo, terms_file).returncode == 1


def test_bad_usage_is_exit_2(repo):
    assert run(DENY + ["nonsense"], repo).returncode == 2
    assert run(DENY + ["message"], repo, {"DENYLIST_TERMS": WORD}).returncode == 2


# ---- gitleaks and the hooks --------------------------------------------------------------------------------------------

def gitleaks_or_skip():
    done = run([sys.executable, str(TOOLS / "run_gitleaks.py"), "find"], REPO)
    if done.returncode == 0:
        return done.stdout.strip()
    if os.environ.get("REQUIRE_GITLEAKS") == "1":
        pytest.fail("gitleaks is required here but not installed")
    pytest.skip("gitleaks is not installed (python tools/run_gitleaks.py install)")


def install_project_files(work: Path) -> None:
    """Give the throwaway repo the project's own hooks, tools and config, as a real clone of this project has them."""
    for name in (".githooks", "tools"):
        shutil.copytree(REPO / name, work / name, ignore=shutil.ignore_patterns("__pycache__", "test_*"))
    for name in (".gitleaks.toml", ".gitignore"):
        shutil.copy(REPO / name, work / name)
    git(work, "config", "core.hooksPath", ".githooks")


@pytest.fixture()
def hooked(repo):
    """The throwaway repo with THIS project's hooks switched on, using the gitleaks binary the tests were given."""
    binary = gitleaks_or_skip()
    install_project_files(repo)
    repo_env["GITLEAKS_BIN"] = binary
    return repo


repo_env: dict[str, str] = {}


def commit(repo, message, env=None):
    return git(repo, "commit", "-q", "-m", message, env={**repo_env, **(env or {})})


def test_hook_blocks_a_staged_token_and_never_shows_it(hooked):
    token = fake_token()
    stage(hooked, "config.txt", f"token = {token}\n")
    done = commit(hooked, "add config")
    assert done.returncode != 0, "the commit should have been blocked"
    assert token not in done.stdout + done.stderr, "the secret must be redacted in the output"
    assert "leaks found" in (done.stdout + done.stderr).lower()
    assert git(hooked, "log", "--oneline").stdout.count("\n") == 1, "nothing new was committed"


def test_hook_lets_a_clean_commit_through(hooked):
    stage(hooked, "a.md", "plain text\n")
    assert commit(hooked, "plain").returncode == 0


def test_hook_blocks_a_private_term_in_a_file(hooked, terms_file):
    stage(hooked, "a.md", f"about {WORD}\n")
    done = commit(hooked, "innocent message", env=terms_file)
    assert done.returncode != 0 and "a.md:1" in done.stderr


def test_hook_blocks_a_private_term_in_the_message(hooked, terms_file):
    stage(hooked, "a.md", "plain\n")
    done = commit(hooked, f"about {WORD}", env=terms_file)
    assert done.returncode != 0 and "commit message" in done.stderr


def test_hook_blocks_a_real_data_file_type(hooked):
    stage(hooked, "export.reqif", "<x/>\n")
    done = commit(hooked, "add data")
    assert done.returncode != 0


def test_hook_refuses_when_gitleaks_is_missing(repo, tmp_path):
    """Fail closed: no scanner, no commit."""
    install_project_files(repo)            # no .cache/bin in this copy, and no GITLEAKS_BIN below
    stage(repo, "a.md", "plain\n")
    bare = tmp_path / "bare-bin"
    bare.mkdir()
    done = commit(repo, "no scanner", env={"GITLEAKS_BIN": "", "PATH": f"{Path(sys.executable).parent}{os.pathsep}{bare}{os.pathsep}/usr/bin{os.pathsep}/bin"})
    if "gitleaks is not installed" not in done.stderr:
        pytest.skip("a gitleaks binary is on the system PATH here, so the missing-scanner case cannot be shown")
    assert done.returncode != 0


def test_gitleaks_history_scan_finds_a_committed_token_and_then_passes_when_clean(repo):
    binary = gitleaks_or_skip()
    stage(repo, "oops.txt", f"key={fake_token()}\n")
    git(repo, "commit", "-q", "-m", "oops")
    bad = run([binary, "git", "--redact", "--no-banner", "--config", str(REPO / ".gitleaks.toml")], repo)
    assert bad.returncode != 0
    clean = repo.parent / "clean2"
    clean.mkdir()
    git(clean, "init", "-q", "-b", "main")
    stage(clean, "a.md", "nothing\n")
    git(clean, "-c", "user.name=A", "-c", "user.email=a@b.invalid", "commit", "-q", "-m", "ok")
    good = run([binary, "git", "--redact", "--no-banner", "--config", str(REPO / ".gitleaks.toml")], clean)
    assert good.returncode == 0, good.stdout + good.stderr


# ---- the wiring -------------------------------------------------------------------------------------------------------

def text(path):
    return (REPO / path).read_text(encoding="utf-8")


def test_the_term_list_is_ignored_by_git_and_never_tracked():
    assert re.search(r"^\.denylist$", text(".gitignore"), re.M)
    assert re.search(r"^\.forbidden-terms$", text(".gitignore"), re.M)
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True).stdout.split("\n")
    assert not [t for t in tracked if t.endswith(".denylist") or t.endswith(".forbidden-terms")]


def test_the_hooks_exist_and_are_executable():
    for name in ("pre-commit", "commit-msg"):
        hook = REPO / ".githooks" / name
        assert hook.is_file(), name
        assert hook.stat().st_mode & stat.S_IXUSR, f"{name} is not executable"
        assert hook.read_text(encoding="utf-8").startswith("#!/bin/sh")
    pre = text(".githooks/pre-commit")
    assert "denylist_check.py" in pre and "run_gitleaks.py" in pre and "check_no_real_data.py" in pre
    assert "denylist_check.py" in text(".githooks/commit-msg")


def test_the_pinned_gitleaks_has_a_checksum_for_every_platform():
    source = text("tools/run_gitleaks.py")
    hashes = re.findall(r'"(linux_x64|linux_arm64|darwin_x64|darwin_arm64|windows_x64)":\s*"([0-9a-f]{64})"', source)
    assert len(hashes) == 5 and len({h for _, h in hashes}) == 5
    assert re.search(r'^VERSION = "\d+\.\d+\.\d+"$', source, re.M)


def test_both_ci_systems_run_both_guards():
    github, gitlab = text(".github/workflows/ci.yml"), text(".gitlab-ci.yml")
    for body in (github, gitlab):
        assert "tools/run_gitleaks.py history" in body
        assert "tools/denylist_check.py ci" in body
    assert "fetch-depth: 0" in github and "GIT_DEPTH" in gitlab, "the scans need the whole history, not a shallow clone"
    assert "secrets.DENYLIST" in github
    assert "DENYLIST_FILE" in gitlab


def test_the_make_check_target_includes_the_secret_scan():
    makefile = text("Makefile")
    assert re.search(r"^check:.*\bsecrets\b", makefile, re.M)
    assert re.search(r"^hooks:", makefile, re.M)
