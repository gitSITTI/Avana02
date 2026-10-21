#!/usr/bin/env python3
"""The connected page's sync engine against a REAL reference server: starts the demo project on a free loopback port with nothing but Python's standard library
(reqin/serve_standalone.py), runs conn_test.js on a built page (six people at once: deciding, signing, objecting, labelling, going offline, losing an answer),
and says what failed. Needs python3 and node; no browser, no pip install.

  python3 run_conn_test.py [page.html]        default: project/Main.dc.html        exit status 1 if any check failed, or the run did not finish

`make proto` and the CI jobs run it. reqin/tests/test_connect_engine.py runs the same checks from pytest."""
import json, os, re, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
STANDALONE = os.path.join(HERE, '..', 'reqin', 'serve_standalone.py')


def start_server(workdir, app=None):
    """The demo project, seeded from demo/seed.json: (process, port, tokens file). The caller terminates the process."""
    db = os.path.join(workdir, 'demo-%d.db' % int(time.time() * 1000))
    cmd = [sys.executable, STANDALONE, 'demo', '--db', db, '--seed', os.path.join(HERE, 'demo', 'seed.json'), '--app', app or os.path.join(HERE, 'project'), '--port', '0']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t0 = time.time()
    while time.time() - t0 < 30:
        line = p.stdout.readline()
        m = re.search(r'Serving on http://127\.0\.0\.1:(\d+)', line)
        if m: return p, int(m.group(1)), db + '.tokens.json'
        if not line and p.poll() is not None: break
    p.kill()
    raise SystemExit('the demo server did not start')


def run(page, timeout=240, cwd=None):
    """(ok, the lines it printed). A run that does not finish in time is a failure, not a hang."""
    with tempfile.TemporaryDirectory(prefix='reqin-conn-') as tmp:
        p, port, tok = start_server(tmp)
        try:
            r = subprocess.run(['node', os.path.join(HERE, 'conn_test.js'), page, str(port), tok], capture_output=True, text=True, timeout=timeout, cwd=cwd or HERE)
            lines = (r.stdout + r.stderr).splitlines()
            ok = r.returncode == 0 and not any(l.startswith('FAIL') for l in lines) and sum(1 for l in lines if l.startswith('PASS')) >= 40
            if r.returncode == 0 and sum(1 for l in lines if l.startswith('PASS')) < 40: lines.append('FAIL fewer than 40 checks ran')
            return ok, lines
        except subprocess.TimeoutExpired:
            return False, ['FAIL the run did not finish in %d seconds (a page that never stops sending?)' % timeout]
        finally:
            p.terminate()
            try: p.wait(10)
            except Exception: p.kill()


def main(argv):
    page = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(HERE, 'project', 'Main.dc.html')
    ok, lines = run(page)
    fails = [l for l in lines if l.startswith('FAIL')]
    for l in fails: print(l)
    print('%s: %d checks passed, %d failed' % ('ok' if ok else 'FAIL', sum(1 for l in lines if l.startswith('PASS')), len(fails)))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
