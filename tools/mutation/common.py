"""Shared by the mutation scripts in this folder.

A mutation script changes ONE thing in a copy of the code (a comparison flipped, a check removed, a number off by one), runs the project's own checks on the copy
and says whether they noticed. A check that cannot fail proves nothing; this is how the checks were shown to be able to fail.

Nothing here touches the real files: every run works in a fresh temporary folder that is deleted when the script ends.
"""
import atexit, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'prototype')
WORK = tempfile.mkdtemp(prefix='reqin-mutation-')
MUT = os.path.join(WORK, 'prototype')          # verify.js reads ../docs/ai_gate_cases.json, so docs/ sits beside prototype/ in the copy
atexit.register(shutil.rmtree, WORK, True)


def reset():
    """A clean copy of the prototype's sources."""
    if os.path.exists(MUT): shutil.rmtree(MUT)
    os.makedirs(MUT + '/project')
    shutil.copytree(SRC + '/parts', MUT + '/parts', ignore=shutil.ignore_patterns('__pycache__'))
    for f in ('build.py', 'verify.js'): shutil.copy(os.path.join(SRC, f), os.path.join(MUT, f))
    os.makedirs(WORK + '/docs', exist_ok=True)
    shutil.copy(os.path.join(REPO, 'docs', 'ai_gate_cases.json'), WORK + '/docs/ai_gate_cases.json')


def run(cmd):
    r = subprocess.run(cmd, cwd=MUT, shell=True, capture_output=True, text=True, timeout=900)
    return r.returncode, r.stdout + r.stderr


def main(mutants, equivalent=None, width=60, what_counts=None):
    """mutants: (name, file, old text, new text). equivalent: {name: why a change that no check notices is harmless}.
    what_counts: a function from a line of verify.js output to True when it is a report of a failed check (default: lines that start with ' - ').
    Usage: python3 <script>.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.   Exit status 1 when a change goes unnoticed and is not listed as equivalent."""
    equivalent = equivalent or {}
    what_counts = what_counts or (lambda l: l.startswith(' - '))
    args = sys.argv[1:]
    if args == ['--patterns']:                       # fast: does every change still match the code? (no checks are run)
        missing = [m[0] for m in mutants if m[2] not in open(os.path.join(SRC, m[1]), encoding='utf-8').read()]
        for n in missing: print('PATTERN MISSING:', n)
        print('%d of %d changes still match the code' % (len(mutants) - len(missing), len(mutants)))
        return 1 if missing else 0
    if args == ['--list']:
        for m in mutants: print(m[0])
        return 0
    survivors = []
    for name, f, a, b in mutants:
        if args and not any(o in name for o in args): continue
        reset()
        p = os.path.join(MUT, f)
        s = open(p, encoding='utf-8').read()
        if a not in s:
            print('%-*s PATTERN MISSING (the code has changed; update this mutant)' % (width, name), flush=True); survivors.append(name); continue
        open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
        rc, out = run('python3 build.py >/dev/null && node verify.js project/Main.dc.html')
        lines = [l for l in out.splitlines() if what_counts(l)]
        if not lines: lines = [l for l in out.splitlines() if l.startswith(' - ')][:1] or [l for l in out.splitlines() if 'Error' in l][:1]
        if rc != 0 or lines:
            print('%-*s CAUGHT (%d): %s' % (width, name, len(lines), (lines[0] if lines else '')[:110]), flush=True)
        elif name in equivalent:
            print('%-*s not noticed, and harmless: %s' % (width, name, equivalent[name]), flush=True)
        else:
            print('%-*s NOT CAUGHT' % (width, name), flush=True); survivors.append(name)
    print('\n%s' % ('every change was noticed' if not survivors else '%d went unnoticed: %s' % (len(survivors), '; '.join(survivors))))
    return 1 if survivors else 0
