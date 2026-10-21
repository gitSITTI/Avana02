"""Break draft-review and setup rules in temporary checkouts; never edit the source.

python3 tools/mutation/review.py [part of a name | --patterns]
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
muts = [
    ("review output cannot modify source folders", "tools/review/build.py", "if any(out.resolve().is_relative_to(Path(src).resolve()) for src in [comparison, *datasets]):", "if False:", "reqin/tests/test_review_workspace.py"),
    ("review refuses stale engine output", "tools/review/build.py", "if problems:", "if False:", "reqin/tests/test_review_workspace.py"),
    ("review binds restored notes to the input", "tools/review/review.js", "file.binding !== binding", "false", "reqin/tests/test_review_workspace.py"),
    ("review refuses unknown comparison ids", "tools/review/review.js", "!known.has(id)", "false", "reqin/tests/test_review_workspace.py"),
    ("review requires reasons", "tools/review/review.js", '(d.outcome !== "needs_review" && !d.reason.trim())', "false", "reqin/tests/test_review_workspace.py"),
    ("review export remains draft", "tools/review/review.js", 'format: FORMAT, status: "draft", binding, decisions', 'format: FORMAT, status: "approved", binding, decisions', "reqin/tests/test_review_workspace.py"),
    ("doctor requires installed packages", "tools/doctor.py", 'available(name), True,', 'True, True,', "tools/test_doctor.py"),
    ("doctor requires browser tooling in its browser profile", "tools/doctor.py", 'profile == "browser"', "False", "tools/test_doctor.py"),
    ("doctor never echoes secrets", "tools/doctor.py", '"profile": profile, "ready":', '"environment": dict(env), "profile": profile, "ready":', "tools/test_doctor.py"),
]


def main():
    args = sys.argv[1:]
    if args == ["--patterns"]:
        missing = [name for name, path, old, _, _ in muts if old not in (ROOT / path).read_text()]
        print(f"{len(muts) - len(missing)} of {len(muts)} changes still match the code")
        return int(bool(missing))
    if args == ["--list"]:
        print("\n".join(m[0] for m in muts))
        return 0
    failed = []
    for name, path, old, new, test in muts:
        if args and not any(a in name for a in args):
            continue
        with tempfile.TemporaryDirectory(prefix="reqin-review-mutation-") as work:
            target = Path(work) / "repo"
            shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns(".git", "node_modules", ".cache", "__pycache__", "images", "excalidraw"))
            file = target / path
            text = file.read_text()
            if old not in text:
                print(name + ": PATTERN MISSING", flush=True); failed.append(name); continue
            file.write_text(text.replace(old, new, 1))
            env = dict(os.environ, PYTHONPATH=str(target / "reqin/src"))
            r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", test], cwd=target, env=env, capture_output=True, text=True, timeout=120)
            caught = r.returncode == 1 and "failed" in r.stdout
            print(name + (": CAUGHT" if caught else ": NOT CAUGHT\n" + (r.stdout + r.stderr)[-1500:]), flush=True)
            if not caught:
                failed.append(name)
    return int(bool(failed))


if __name__ == "__main__":
    sys.exit(main())
