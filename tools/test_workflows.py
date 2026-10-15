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
GITLAB = REPO / ".gitlab-ci.yml"
ALLOWED_SECRETS = {"FORBIDDEN_TERMS", "DENYLIST"}


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


def job_lines(code: list[str], name: str) -> list[str]:
    """The lines of one job (two-space indent under `jobs:`), or [] if there is none."""
    for i, line in enumerate(code):
        if line == f"  {name}:":
            out = []
            for rest in code[i + 1:]:
                if re.match(r"^ {2}\S", rest):
                    break
                out.append(rest)
            return out
    return []


def secret_scan_problems(code: list[str]) -> list[str]:
    """The secrets job is the only thing standing between a leaked key or a private name and a public history, so its shape is checked."""
    job = job_lines(code, "secrets")
    if not job:
        return ["the workflow has no `secrets` job (gitleaks and the private-term check)"]
    body = "\n".join(job)
    bad: list[str] = []
    if not re.search(r"fetch-depth:\s*0\b", body):
        bad.append("the secrets job needs `fetch-depth: 0`: a shallow clone hides the history it is meant to scan")
    if "tools/run_gitleaks.py history" not in body:
        bad.append("the secrets job does not run the gitleaks history scan")
    if "tools/denylist_check.py ci" not in body:
        bad.append("the secrets job does not run the private-term check")
    if not re.search(r"DENYLIST_OPTIONAL:\s*\$\{\{\s*github\.event\.pull_request\.head\.repo\.fork\b", body):
        bad.append("DENYLIST_OPTIONAL must be set only for pull requests from forks; anything else lets a missing secret pass as a clean scan")
    holders = [b for b in steps(code) if "secrets.DENYLIST" in b]
    if len(holders) != 1 or "tools/denylist_check.py ci" not in holders[0]:
        bad.append("the DENYLIST secret must reach only the step that runs the private-term check")
    return bad


BROWSER_JOBS = {
    "prototype-browser": ["npm ci", "playwright install", "python run_browser_tests.py"],
    "prototype-scale": ["node scale.js"],
}


def browser_job_problems(code: list[str]) -> list[str]:
    """The browser tests, the accessibility scan and the scale test only protect anything if the jobs exist and run them."""
    bad: list[str] = []
    for job, must in BROWSER_JOBS.items():
        lines = job_lines(code, job)
        if not lines:
            bad.append(f"the workflow has no `{job}` job")
            continue
        body = "\n".join(lines)
        bad += [f"the `{job}` job does not run `{m}`" for m in must if m not in body]
    return bad


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

    bad += secret_scan_problems(code)
    bad += browser_job_problems(code)

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
    mapping = {"guard": "guard", "secrets": "secrets", "test": "reqin", "template": "connector-template", "boards": "boards", "proto": "prototype"}
    assert set(wanted) <= set(mapping), f"`make check` gained a target this test does not know: {sorted(set(wanted) - set(mapping))}"
    missing = [t for t in wanted if mapping[t] not in jobs]
    assert not missing, f"`make check` runs {missing} but the workflow has no matching job; jobs are {sorted(jobs)}"


def test_every_job_the_makefile_check_full_target_adds_has_a_workflow_job():
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    wanted = re.search(r"^check-full:\s*(.+)$", makefile, re.M).group(1).split()
    body = "\n".join(code_lines(WORKFLOW.read_text(encoding="utf-8")))
    jobs = set(re.findall(r"^  ([a-z][a-z0-9-]*):[ \t]*$", body.split("\njobs:", 1)[1], re.M))
    mapping = {"check": None, "proto-test": "prototype-browser", "proto-scale": "prototype-scale"}
    assert set(wanted) <= set(mapping), f"`make check-full` gained a target this test does not know: {sorted(set(wanted) - set(mapping))}"
    missing = [t for t in wanted if mapping[t] and mapping[t] not in jobs]
    assert not missing, f"`make check-full` runs {missing} but the workflow has no matching job; jobs are {sorted(jobs)}"


def test_the_make_targets_run_the_same_runner_as_the_workflow():
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    assert re.search(r"^proto-test:\n(?:\t.*\n)*?\tcd prototype && \$\(PY\) run_browser_tests\.py$", makefile, re.M)
    assert re.search(r"^proto-scale:\n\tcd prototype && node scale\.js$", makefile, re.M)


def test_the_runner_lists_every_browser_test_file():
    """A test file nobody lists is a test that never runs."""
    runner = (REPO / "prototype" / "run_browser_tests.py").read_text(encoding="utf-8")
    listed = set(re.findall(r"\('(b\d+\.py)'", runner))
    present = {p.name for p in (REPO / "prototype").glob("b[0-9]*.py") if int(p.stem[1:]) >= 11}
    assert present <= listed, f"test files the runner does not run: {sorted(present - listed)}"
    assert listed <= {p.name for p in (REPO / "prototype").glob("b*.py")}, "the runner lists a file that does not exist"


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
    ("needs `fetch-depth: 0`", lambda t: t.replace("          fetch-depth: 0\n", "", 1)),
    ("does not run the gitleaks history scan", lambda t: t.replace("python tools/run_gitleaks.py history", "python tools/run_gitleaks.py find", 1)),
    ("does not run the private-term check", lambda t: t.replace("run: python tools/denylist_check.py ci", "run: python tools/denylist_check.py status", 1)),
    ("DENYLIST_OPTIONAL must be set only for pull requests from forks", lambda t: re.sub(r"DENYLIST_OPTIONAL: .*", "DENYLIST_OPTIONAL: '1'", t, count=1)),
    ("must reach only the step", lambda t: t.replace('REQUIRE_GITLEAKS: "1"', "REQUIRE_GITLEAKS: ${{ secrets.DENYLIST }}", 1)),
    ("has no `secrets` job", lambda t: t.replace("\n  secrets:\n", "\n  secretz:\n", 1)),
    ("spans several lines", lambda t: t.replace("      - run: pip install pytest\n", "      - run: |\n          pip install pytest\n", 1)),
    ("has no `prototype-browser` job", lambda t: t.replace("\n  prototype-browser:\n", "\n  prototype-brwsr:\n", 1)),
    ("does not run `python run_browser_tests.py`", lambda t: t.replace("run: python run_browser_tests.py", "run: python run_browser_test.py", 1)),
    ("does not run `npm ci`", lambda t: t.replace("      - run: npm ci\n        working-directory: prototype/vendor\n", "", 1)),
    ("does not run `playwright install`", lambda t: t.replace("run: python -m playwright install --with-deps chromium", "run: python -m pip --version", 1)),
    ("has no `prototype-scale` job", lambda t: t.replace("\n  prototype-scale:\n", "\n  prototype-scal:\n", 1)),
    ("does not run `node scale.js`", lambda t: t.replace("run: node scale.js", "run: node verify.js project/Main.dc.html", 1)),
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


# ---- the GitLab pipeline: read, not run ----
GITLAB_JOBS = {
    "prototype:vendor": ["npm ci"],
    "prototype:browser": ["python run_browser_tests.py"],
    "prototype:scale": ["node scale.js"],
}


def gitlab_scripts(text: str) -> dict[str, list[str]]:
    """Each top-level job and its script lines, with comments removed."""
    jobs: dict[str, list[str]] = {}
    cur = None
    for line in code_lines(text):
        m = re.match(r"^([A-Za-z.][\w:.-]*):[ \t]*$", line)
        if m:
            cur = m.group(1)
            jobs[cur] = []
        elif cur is not None and re.match(r"^\s+- \S", line):
            jobs[cur].append(line.strip()[2:].strip())
    return jobs


def gitlab_problems(text: str, repo: Path = REPO) -> list[str]:
    bad: list[str] = []
    jobs = gitlab_scripts(text)
    for job, must in GITLAB_JOBS.items():
        if job not in jobs:
            bad.append(f"the pipeline has no `{job}` job")
            continue
        bad += [f"the `{job}` job does not run `{m}`" for m in must if m not in jobs[job]]
    # every file a script line names must exist, in the folder the job has moved to
    for job, lines in jobs.items():
        cwd = repo
        for line in lines:
            if line.startswith("cd "):
                cwd = repo / line[3:].strip().strip('"')
                if "$" not in line and not cwd.is_dir():
                    bad.append(f"{job}: `{line}` goes to a folder that does not exist")
                continue
            try:
                words = shlex.split(line)
            except ValueError:
                continue
            for word in words:
                if word.startswith("-") or "$" in word or any(c in word for c in "{}^[<>|"):
                    continue
                if word.endswith((".py", ".js", ".txt")) and not (glob.glob(str(cwd / word)) or glob.glob(str(repo / word))):
                    bad.append(f"{job}: `{line}` names {word!r}, which does not exist")
    # the browser image and the pinned Playwright must be the same version, or the browser the tests ask for is not in the image
    pin = re.search(r"^playwright==(\S+)", (repo / "prototype" / "requirements-test.txt").read_text(encoding="utf-8"), re.M)
    image = re.search(r'PLAYWRIGHT_IMAGE:\s*"[^"]*:v(\d+\.\d+\.\d+)', text)
    if not pin or not image or pin.group(1) != image.group(1):
        bad.append(f"the Playwright image ({image.group(1) if image else 'none'}) and prototype/requirements-test.txt ({pin.group(1) if pin else 'none'}) are not the same version")
    return bad


def test_the_gitlab_pipeline_has_no_problems():
    assert GITLAB.is_file()
    assert gitlab_problems(GITLAB.read_text(encoding="utf-8")) == []


GITLAB_MUTATIONS = [
    ("no `prototype:browser` job", lambda t: t.replace("\nprototype:browser:\n", "\nprototype:brwsr:\n", 1)),
    ("`prototype:browser` job does not run `python run_browser_tests.py`", lambda t: t.replace("    - python run_browser_tests.py\n", "    - python verify.py\n", 1)),
    ("`prototype:scale` job does not run `node scale.js`", lambda t: t.replace("    - node scale.js\n", "    - node verify.js project/Main.dc.html\n", 1)),
    ("`prototype:vendor` job does not run `npm ci`", lambda t: t.replace("    - npm ci\n", "    - npm install\n", 1)),
    ("names 'run_browser_test.py'", lambda t: t.replace("run_browser_tests.py", "run_browser_test.py", 1)),
    ("goes to a folder that does not exist", lambda t: t.replace("    - cd prototype/vendor\n", "    - cd prototype/vendr\n", 1)),
    ("are not the same version", lambda t: t.replace("playwright/python:v1.56.0-noble", "playwright/python:v1.57.0-noble", 1)),
]


@pytest.mark.parametrize("expected,mutate", GITLAB_MUTATIONS, ids=[m[0] for m in GITLAB_MUTATIONS])
def test_each_gitlab_check_can_fail(expected, mutate):
    text = GITLAB.read_text(encoding="utf-8")
    broken = mutate(text)
    assert broken != text, "the mutation did not change the pipeline; fix the test"
    found = gitlab_problems(broken)
    assert any(expected in p for p in found), f"{expected!r} not reported; got {found}"
