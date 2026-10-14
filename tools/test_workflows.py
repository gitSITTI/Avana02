"""The GitHub Actions workflow cannot be run where it is written, so these checks keep it safe and keep it pointing at things that exist.

Standard library only (the guard job installs nothing but pytest). They read the text of .github/workflows/ci.yml; they do not run it.
Syntax and expression errors are caught by `actionlint` and the GitHub workflow schema (see CONTRIBUTING.md); this file covers what those two do not:
a schema-valid workflow can still use a dangerous trigger, an unpinned action or a write token.
"""
from __future__ import annotations

import glob
import re
import shlex
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
ALLOWED_SECRETS = {"FORBIDDEN_TERMS"}


def code_lines(text: str) -> list[str]:
    """The workflow without its comments (the header comment names the triggers it refuses)."""
    return [re.sub(r"(^|\s)#.*$", "", line).rstrip() for line in text.splitlines()]


def steps(code: list[str]) -> list[str]:
    """Each job step as one block of text. Steps sit at 6 spaces of indent in this file."""
    blocks: list[list[str]] = []
    cur: list[str] | None = None
    for line in code:
        if re.match(r"^ {6}- ", line):
            cur = [line]
            blocks.append(cur)
        elif cur is not None and (line.startswith(" " * 8) or not line.strip()):
            cur.append(line)
        else:
            cur = None
    return ["\n".join(b) for b in blocks]


def problems(text: str, repo: Path = REPO) -> list[str]:
    raw = text.splitlines()
    code = code_lines(text)
    body = "\n".join(code)
    bad: list[str] = []

    for trigger in ("pull_request_target", "workflow_run"):
        if re.search(rf"\b{trigger}\b", body):
            bad.append(f"uses the {trigger} trigger, which runs with a privileged token in the context of other people's code")

    top = re.search(r"^permissions:[ \t]*\n((?:[ ]{2}\S.*\n?)+)", body, re.M)
    if not top or not re.search(r"^ {2}contents:[ \t]*read[ \t]*$", top.group(1), re.M):
        bad.append("no top-level `permissions:` with `contents: read`")
    if re.search(r":[ \t]*write(-all)?[ \t]*$|permissions:[ \t]*write-all", body, re.M):
        bad.append("grants a write permission; this workflow only reads")

    for number, line in enumerate(raw, 1):
        m = re.match(r"\s*-?\s*uses:\s*(\S+)(.*)$", line)
        if not m or m.group(1).startswith("./"):
            continue
        ref, rest = m.groups()
        if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", ref):
            bad.append(f"line {number}: {ref} is not pinned to a full commit SHA")
        elif not re.search(r"#\s*v\d", rest):
            bad.append(f"line {number}: {ref} has no version comment after the SHA")

    extra = set(re.findall(r"secrets\.([A-Za-z0-9_]+)", body)) - ALLOWED_SECRETS
    if extra:
        bad.append(f"reads secrets this workflow is not meant to have: {sorted(extra)}")

    for block in steps(code):
        if "actions/checkout@" in block and not re.search(r"persist-credentials:\s*false", block):
            bad.append("a checkout step keeps the token in .git/config (set `persist-credentials: false`)")
        wd = re.search(r"working-directory:\s*(\S+)", block)
        cwd = repo / wd.group(1) if wd else repo
        if wd and not cwd.is_dir():
            bad.append(f"working-directory {wd.group(1)!r} does not exist")
            continue
        run = re.search(r"^\s*(?:- )?run:[ \t]*(.*)$", block, re.M)
        if not run:
            continue
        command = run.group(1).strip()
        if command in ("|", ">", "|-", ">-"):
            bad.append("a `run:` step spans several lines; keep each on one line so this test can read it")
            continue
        try:
            words = shlex.split(command)
        except ValueError:
            bad.append(f"cannot read the command {command!r}")
            continue
        for word in words:
            if word.startswith("-") or "$" in word or any(c in word for c in "{}^["):
                continue                      # a flag, a shell variable, a regex or a pip extra: not a path
            looks_like_path = "/" in word or word.endswith((".py", ".js", ".html", ".yml")) or word == "Containerfile"
            if looks_like_path and not (glob.glob(str(cwd / word)) or glob.glob(str(repo / word))):
                bad.append(f"the command {command!r} names {word!r}, which does not exist")
    return bad


def test_the_workflow_file_exists_and_has_no_problems():
    assert WORKFLOW.is_file(), "the CI workflow is missing"
    assert problems(WORKFLOW.read_text(encoding="utf-8")) == []


def test_every_job_the_makefile_check_target_runs_has_a_workflow_job():
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    wanted = re.search(r"^check:\s*(.+)$", makefile, re.M).group(1).split()
    body = "\n".join(code_lines(WORKFLOW.read_text(encoding="utf-8")))
    jobs = set(re.findall(r"^  ([a-z][a-z0-9-]*):[ \t]*$", body.split("\njobs:", 1)[1], re.M))
    # make target -> the workflow job that runs the same commands
    mapping = {"guard": "guard", "test": "reqin", "template": "connector-template", "boards": "boards", "proto": "prototype"}
    assert set(wanted) <= set(mapping), f"`make check` gained a target this test does not know: {sorted(set(wanted) - set(mapping))}"
    missing = [t for t in wanted if mapping[t] not in jobs]
    assert not missing, f"`make check` runs {missing} but the workflow has no matching job; jobs are {sorted(jobs)}"


MUTATIONS = [
    ("pull_request_target", lambda t: t.replace("\non:\n", "\non:\n  pull_request_target:\n", 1)),
    ("workflow_run", lambda t: t.replace("\non:\n", "\non:\n  workflow_run:\n", 1)),
    ("contents: read", lambda t: t.replace("permissions:\n  contents: read", "permissions:\n  contents: write", 1)),
    ("write permission", lambda t: t.replace("  workflow_dispatch:\n", "  workflow_dispatch:\n\npermissions-extra:\n  id-token: write\n", 1)),
    ("not pinned", lambda t: re.sub(r"(actions/checkout)@[0-9a-f]{40}", r"\1@v7", t, count=1)),
    ("no version comment", lambda t: re.sub(r"(actions/setup-python@[0-9a-f]{40}) # v\S+", r"\1", t, count=1)),
    ("secrets this workflow is not meant", lambda t: t.replace("${{ secrets.FORBIDDEN_TERMS }}", "${{ secrets.GITHUB_TOKEN }}", 1)),
    ("persist-credentials", lambda t: t.replace("          persist-credentials: false\n", "", 1)),
    ("working-directory 'protoype'", lambda t: t.replace("working-directory: prototype", "working-directory: protoype", 1)),
    ("build_al.py", lambda t: t.replace("python build_all.py", "python build_al.py", 1)),
    ("check_nothing.py", lambda t: t.replace("run: python tools/check_no_real_data.py", "run: python tools/check_nothing.py", 1)),
    ("spans several lines", lambda t: t.replace("      - run: pip install pytest\n", "      - run: |\n          pip install pytest\n", 1)),
]


@pytest.mark.parametrize("expected,mutate", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_check_can_fail(expected, mutate):
    """Break the real workflow in one way and the checks must say so, otherwise they prove nothing."""
    text = WORKFLOW.read_text(encoding="utf-8")
    broken = mutate(text)
    assert broken != text, "the mutation did not change the workflow; fix the test"
    found = problems(broken)
    assert any(expected in p for p in found), f"{expected!r} not reported; got {found}"


def test_a_trigger_named_only_in_a_comment_is_not_a_problem():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request_target" in text   # the header comment names it
    assert not any("pull_request_target" in p for p in problems(text))
