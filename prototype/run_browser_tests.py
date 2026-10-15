#!/usr/bin/env python3
"""Runs the prototype's browser tests (b11.py to b20.py) at the screen widths each one is meant for, and says which failed.

It is the one place that lists them, so `make proto-test`, the GitHub workflow and the GitLab pipeline all run the same thing.
Needs the vendored libraries (cd vendor && npm ci), Playwright for Python and a Chromium it can start. The page under test is project/Main.dc.html.

  python3 run_browser_tests.py                run everything, one browser at a time (the tests share a port)
  python3 run_browser_tests.py b20 b14        only these files
  python3 run_browser_tests.py --width 390    only this width
  python3 run_browser_tests.py --list         what would run

A failing test prints everything it said; a passing one prints one line. Exit status 1 if anything failed or was missing.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
DESK, MID, PHONE = 1440, 900, 390
PLAN = [                       # (file, what it checks, widths)
    ('b11.py', 'opening a project and mapping each source', [DESK, MID, PHONE]),
    ('b12.py', 'the shell, Home and the wording comparison', [DESK, MID, PHONE]),
    ('b13.py', 'dispositions, AI last, hand-offs, metrics and results', [DESK, MID, PHONE]),
    ('b14.py', 'the engineering V', [DESK, MID, PHONE]),
    ('b15.py', 'label pairs (the gold set)', [DESK, MID, PHONE]),
    ('b16.py', 'one requirement at a time', [DESK, MID, PHONE]),
    ('b17.py', 'the trace map', [DESK, MID, PHONE]),
    ('b18.py', 'keeping the work: autosave, files, two tabs', [DESK, MID, PHONE]),
    ('b19.py', 'AI use: the switch, the data sheet, held groups', [DESK, MID, PHONE]),
    ('b20.py', 'accessibility: axe, contrast, keyboard, reflow, chart colours', [DESK, MID, PHONE]),
]


def main(argv):
    only, width, listing = [], None, False
    it = iter(argv)
    for a in it:
        if a == '--width': width = int(next(it))
        elif a == '--list': listing = True
        elif a in ('-h', '--help'): print(__doc__); return 0
        else: only.append(a if a.endswith('.py') else a + '.py')
    runs = [(f, what, w) for f, what, ws in PLAN for w in ws if (not only or f in only) and (width is None or w == width)]
    unknown = [o for o in only if o not in [f for f, _, _ in PLAN]]
    if unknown:
        print('no such test: ' + ', '.join(unknown)); return 1
    if listing:
        for f, what, w in runs: print('%s %d  %s' % (f, w, what))
        return 0
    if not os.path.isfile(os.path.join(HERE, 'project', 'Main.dc.html')):
        print('project/Main.dc.html is missing; run build.py first'); return 1
    if not os.path.isdir(os.path.join(HERE, 'vendor', 'node_modules', 'react')):
        print('the vendored libraries are missing; run `npm ci` in prototype/vendor first'); return 1
    failed, started = [], time.time()
    for f, what, w in runs:
        t = time.time()
        r = subprocess.run([sys.executable, f, str(w)], cwd=HERE, capture_output=True, text=True, timeout=1200)
        out = r.stdout + r.stderr
        seconds = time.time() - t
        passed = sum(1 for l in out.splitlines() if l.startswith('PASS'))
        ok = r.returncode == 0
        print('%s  %-7s %4d px  %3d checks  %5.1f s   %s' % ('ok  ' if ok else 'FAIL', f, w, passed, seconds, what), flush=True)
        if not ok:
            failed.append((f, w))
            print('-' * 78); print(out.rstrip()); print('-' * 78, flush=True)
    print('\n%d runs in %.0f s: %s' % (len(runs), time.time() - started, 'all passed' if not failed else '%d FAILED: %s' % (len(failed), ', '.join('%s at %d' % x for x in failed))))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
