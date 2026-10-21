"""Prove the Firefox keyboard checks notice the scroller and page-boundary regressions.

Needs Playwright, Firefox and prototype/vendor installed. Uses a throwaway copy.
python3 tools/mutation/firefox.py [part of a name | --patterns]
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

from common import SRC, MUT, reset

muts = [
    ("navigation scroller becomes an extra tab stop", "parts/m/30_shell_open.html", 'class="ws-nav" aria-label="Main" tabindex="-1"', 'class="ws-nav" aria-label="Main"', "focus ring"),
    ("review scroller becomes an extra tab stop", "parts/m/50_review.html", 'class="rv-resolve" aria-label="Resolve this group" tabindex="-1"', 'class="rv-resolve" aria-label="Resolve this group"', "focus ring"),
    ("headless page boundary looks like a focus trap", "b20.py", "or s['end']", "or False", "focus never sticks"),
]


def main():
    args = sys.argv[1:]
    if args == ["--patterns"]:
        missing = [name for name, path, old, _, _ in muts if old not in (Path(SRC) / path).read_text()]
        print(f"{len(muts) - len(missing)} of {len(muts)} changes still match the code")
        return int(bool(missing))
    if args == ["--list"]:
        print("\n".join(m[0] for m in muts)); return 0
    missed = []
    for name, file, old, new, expected in muts:
        if args and not any(a in name for a in args):
            continue
        reset()
        for f in ("h.py", "b20.py", "a11y_page.js", "chart_colours.py"):
            shutil.copy(Path(SRC) / f, Path(MUT) / f)
        shutil.copy(Path(SRC) / "project/support.js", Path(MUT) / "project/support.js")
        shutil.copytree(Path(SRC) / "project/fonts", Path(MUT) / "project/fonts")
        os.symlink(Path(SRC) / "vendor", Path(MUT) / "vendor")
        path = Path(MUT) / file
        text = path.read_text()
        if old not in text:
            print(name + ": PATTERN MISSING", flush=True); missed.append(name); continue
        path.write_text(text.replace(old, new, 1))
        subprocess.run([sys.executable, "build.py"], cwd=MUT, check=True, capture_output=True)
        command = "import h,runpy,sys; h.PORT=8896; sys.argv=['b20.py','1440']; runpy.run_path('b20.py',run_name='__main__')"
        env = dict(os.environ, REQIN_BROWSER="firefox")
        result = subprocess.run([sys.executable, "-c", command], cwd=MUT, env=env, capture_output=True, text=True, timeout=300)
        caught = result.returncode == 1 and any(line.startswith("FAIL") and expected in line for line in result.stdout.splitlines())
        print(name + (": CAUGHT" if caught else ": NOT CAUGHT\n" + (result.stdout + result.stderr)[-2000:]), flush=True)
        if not caught:
            missed.append(name)
    return int(bool(missed))


if __name__ == "__main__":
    sys.exit(main())
