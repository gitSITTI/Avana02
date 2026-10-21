"""Mutation run for the network wall check (deploy/ai-egress/wall_check.py): each rule it promises is broken in a copy, one at a time, and tools/test_wall_check.py must fail.

The script is what IT trusts to say "the model cannot be reached from where it must not be", so a check in it that cannot fail would be worse than no check.

Usage: python3 tools/mutation/wall.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed and is not listed as harmless. See README.md in this folder."""
import atexit, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MUT = tempfile.mkdtemp(prefix='reqin-mutation-wall-')
atexit.register(shutil.rmtree, MUT, True)
F = 'deploy/ai-egress/wall_check.py'


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT + '/tools')
    shutil.copytree(REPO + '/deploy', MUT + '/deploy', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(REPO + '/tools/test_wall_check.py', MUT + '/tools/test_wall_check.py')
    os.symlink(REPO + '/reqin', MUT + '/reqin')           # the test that reads the gateway's example settings runs the real gateway code


def run():
    r = subprocess.run([sys.executable, '-m', 'pytest', 'tools/test_wall_check.py', '-q', '-x', '-p', 'no:cacheprovider'], cwd=MUT, capture_output=True, text=True, timeout=300)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
    return r.returncode != 0, (last[-1] if last else '')


MUTS = [
 ('a timeout is not recognised as a block', F, "if isinstance(e, socket.timeout) or isinstance(e, TimeoutError):\n        return TIMEOUT", "if False:\n        return TIMEOUT"),
 ('a refusal is not recognised as a block', F, "if isinstance(e, ConnectionRefusedError) or getattr(e, \"errno\", None) == errno.ECONNREFUSED:\n        return REFUSED", "if False:\n        return REFUSED"),
 ('an unreachable network is not recognised as a block', F, "BLOCKED_OUTCOMES = {REFUSED, TIMEOUT, UNREACHABLE}", "BLOCKED_OUTCOMES = {REFUSED, TIMEOUT}"),
 ('a connection that opens passes as blocked', F, "        if out == OPEN:\n            ok, line = False, f\"IS REACHABLE", "        if False:\n            ok, line = False, f\"IS REACHABLE"),
 ('a wrong answer on the gateway port still passes', F, "elif h is not None and not h[\"ok\"]:", "elif False:"),
 ('the HTTP answer is never asked for', F, "        if probe:\n            out[\"http\"]", "        if False:\n            out[\"http\"]"),
 ('the status of the HTTP answer is not compared', F, "ok = r.status == want_status and want_text in body", "ok = want_text in body"),
 ('the text of the HTTP answer is not compared', F, "ok = r.status == want_status and want_text in body", "ok = r.status == want_status"),
 ('a name that does not resolve passes as blocked', F, "ok = bool(check.get(\"allow_unresolved\"))", "ok = True"),
 ('a wanted connection that fails still passes', F, "            ok, line = False, f\"should be reachable and is not", "            ok, line = True, f\"should be reachable and is not"),
 ('a blocked check passes without proof the target is up', F, "if pr is None or pr.get(\"ok\") is not True or pr.get(\"outcome\") != OPEN:", "if False:"),
 ('a blocked check with no proof in the plan passes the plan', F, "            if not up:\n                fail(", "            if False:\n                fail("),
 ('a report of another plan is counted', F, "if rp.get(\"plan_sha256\") != plan[\"_sha256\"]:", "if False:"),
 ('reports of different copies of the script are accepted', F, "if len({rp.get(\"script_sha256\") for rp in by_role.values()}) > 1:", "if False:"),
 ('reports from different days are accepted', F, "if max(when) - min(when) > timedelta(hours=max_age_hours):", "if False:"),
 ('a week-old report is accepted', F, "if now - min(when) > timedelta(hours=max_age_hours * 7):", "if False:"),
 ('an earlier run replaces a later one', F, "_when(rp[\"at\"]) > _when(old[\"at\"])", "_when(rp[\"at\"]) < _when(old[\"at\"])"),
 ('a report for some other address is accepted', F, "if r[\"_role\"] != c[\"from\"] or r.get(\"to\") != c[\"to\"] or r.get(\"expect\") != c[\"expect\"]:", "if False:"),
 ('a check the plan does not have is not noticed', F, "    if extra:\n        fail(", "    if False:\n        fail("),
 ('a missing report is not noticed', F, "        if r is None:\n            fail(f\"{c['id']}: no report", "        if False:\n            fail(f\"{c['id']}: no report"),
 ('a proof from the same role is allowed', F, "or p[\"from\"] == c[\"from\"]", "or False"),
 ('a proof for another address is allowed', F, "or p[\"to\"] != c[\"to\"]", "or False"),
 ('a port out of range is allowed', F, "or not 1 <= int(m.group(2)) <= 65535", "or False"),
 ('a duplicate id is allowed', F, "or c[\"id\"] in ids:", ":"),
 ('a check without a reason is allowed', F, "or not isinstance(c[\"why\"], str) or not c[\"why\"].strip():", ":"),
 ('every role runs every check', F, "checks = [c for c in plan[\"checks\"] if c[\"from\"] == role]", "checks = list(plan[\"checks\"])"),
 ('a run that found a surprise exits zero', F, "            return 0 if rep[\"ok\"] else 1", "            return 0"),
 ('a combine that failed exits zero', F, "        print(\"\\n\".join(lines))\n        return 0 if ok else 1", "        print(\"\\n\".join(lines))\n        return 0"),
 ('the report does not carry the plan fingerprint', F, "\"plan_sha256\": plan[\"_sha256\"], \"script_sha256\"", "\"plan_sha256\": \"\", \"script_sha256\""),
]
# a change to a place the tests cannot reach, with the reason (none yet)
EQUIVALENT = {}

only = sys.argv[1:]
if only == ['--patterns']:
    gone = [m[0] for m in MUTS if m[2] not in open(os.path.join(REPO, m[1]), encoding='utf-8').read()]
    for n in gone: print('PATTERN MISSING:', n)
    print('%d of %d changes still match the code' % (len(MUTS) - len(gone), len(MUTS)))
    sys.exit(1 if gone else 0)
if only == ['--list']:
    for m in MUTS: print(m[0])
    sys.exit(0)
unnoticed = []
for name, f, a, b in MUTS:
    if only and not any(o in name for o in only): continue
    reset()
    p = os.path.join(MUT, f); s = open(p, encoding='utf-8').read()
    if a not in s:
        print('%-60s PATTERN MISSING (the code has changed; update this mutant)' % name, flush=True); unnoticed.append(name); continue
    open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
    try:
        caught, why = run()
    except subprocess.TimeoutExpired:
        caught, why = True, 'TIMEOUT'
    if caught: print('%-60s CAUGHT: %s' % (name, why[:80]), flush=True)
    elif name in EQUIVALENT: print('%-60s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
    else: print('%-60s NOT CAUGHT' % name, flush=True); unnoticed.append(name)
print('\n%s' % ('every change was noticed' if not unnoticed else '%d went unnoticed: %s' % (len(unnoticed), '; '.join(unnoticed))))
sys.exit(1 if unnoticed else 0)
