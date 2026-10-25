"""Mutation run for the drift gate (tools/gui_checks/golden.py): each rule it promises is broken in a copy, one at a time, and tools/test_golden.py and tools/test_golden_browser.py must fail.

A gate that passes when it should not is worse than no gate: it tells an agent, and the person reading the report, that a screen did not change. The ways this one could go quiet are a
threshold that ignores real changes, a missing golden or a missing picture that counts as a pass, a size change that is not noticed, and an approve that does not store what was approved.

Usage: python3 tools/mutation/golden.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed and is not listed as harmless. See README.md in this folder. The browser changes need Playwright and Chromium: without them those tests are skipped, and
the changes that only they can notice are reported as NOT CAUGHT, which is the right answer: nothing was checking."""
import atexit, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MUT = tempfile.mkdtemp(prefix='reqin-mutation-golden-')
atexit.register(shutil.rmtree, MUT, True)
F = 'tools/gui_checks/golden.py'
KEEP = shutil.ignore_patterns('__pycache__', 'node_modules', 'bundle.js', '.cache')


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT + '/tools')
    shutil.copytree(REPO + '/tools/gui_checks', MUT + '/tools/gui_checks', ignore=KEEP)
    for t in ('test_golden.py', 'test_golden_browser.py'):
        shutil.copy(REPO + '/tools/' + t, MUT + '/tools/' + t)
    shutil.copytree(REPO + '/design/reference_viewer', MUT + '/design/reference_viewer', ignore=KEEP)
    shutil.copy(REPO + '/design/tokens.css', MUT + '/design/tokens.css')
    shutil.copytree(REPO + '/prototype/project/fonts', MUT + '/prototype/project/fonts', ignore=KEEP)
    shutil.copytree(REPO + '/reqin/src', MUT + '/reqin/src', ignore=KEEP)


def run():
    r = subprocess.run([sys.executable, '-m', 'pytest', 'tools/test_golden.py', 'tools/test_golden_browser.py', '-q', '-x', '-p', 'no:cacheprovider'], cwd=MUT, capture_output=True, text=True, timeout=600)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
    return r.returncode != 0, (last[-1] if last else '')


MUTS = [
 # ---- what counts as a change
 ('the noise threshold swallows every change', F, "NOISE = 24 ", "NOISE = 255 "),
 ('noise counts as a change', F, "NOISE = 24 ", "NOISE = 0 "),
 ('only the red channel is compared', F, "peak = chops.lighter(chops.lighter(r, g), bl)", "peak = r"),
 ('only the red and green channels are compared', F, "peak = chops.lighter(chops.lighter(r, g), bl)", "peak = chops.lighter(r, g)"),
 ('the tolerance is not applied', F, "    ok = ratio <= tolerance\n", "    ok = True\n"),
 ('a picture exactly at the tolerance fails', F, "    ok = ratio <= tolerance\n", "    ok = ratio < tolerance\n"),
 ('a size change is not noticed', F, "    if a.size != b.size:", "    if False:"),
 # ---- what is refused instead of passed
 ('a missing golden passes', F, "(name, shot, name, shot), file=sys.stderr)\n        return 2", "(name, shot, name, shot), file=sys.stderr)\n        return 0"),
 ('a missing picture passes', F, "so this screen was not checked\" % (name, shot), file=sys.stderr)\n        return 2", "so this screen was not checked\" % (name, shot), file=sys.stderr)\n        return 0"),
 ('compare-all passes an approved screen nobody photographed', F, "            worst = max(worst, 1)\n            continue", "            continue"),
 ('compare-all forgets the worst result', F, "worst = max(worst, compare(g, shot, tolerance, (diff_dir / g.name) if diff_dir else None))", "worst = compare(g, shot, tolerance, (diff_dir / g.name) if diff_dir else None)"),
 ('compare-all fails when nothing was approved', F, "proves nothing until the owner has approved a first version of each screen.\" % goldens)\n        return 0", "proves nothing until the owner has approved a first version of each screen.\" % goldens)\n        return 1"),
 ('a picture with no golden is not listed', F, "    new = sorted(p.stem for p in shots.glob(\"*.png\") if not (goldens / p.name).exists()) if shots.is_dir() else []", "    new = []"),
 # ---- approving
 ('approve does not store the picture', F, "    shutil.copyfile(png, dst)\n", "    pass\n"),
 ('approve takes something that is not an image', F, "    if _open(png) is None:\n        return 2\n    dst", "    if False:\n        return 2\n    dst"),
 ('approve stores the picture under the wrong name', F, "dst = goldens / (\"%s.png\" % screen)\n    dst.parent.mkdir(parents=True, exist_ok=True)\n    shutil.copyfile", "dst = goldens / \"golden.png\"\n    dst.parent.mkdir(parents=True, exist_ok=True)\n    shutil.copyfile"),
 # ---- the picture of the changes
 ('the diff picture marks nothing', F, "    dim.paste(Image.new(\"RGB\", base.size, (226, 75, 74)), mask=mask)\n", "    pass\n"),
 ('no diff picture is written', F, "        if diff_out:\n            write_diff(a, mask, diff_out)", "        if False:\n            write_diff(a, mask, diff_out)"),
 # ---- taking the picture (needs a browser)
 ('the width asked for is ignored', F, "viewport={\"width\": width, \"height\": height}", "viewport={\"width\": 1440, \"height\": height}"),
 ('the dataset asked for is not opened', F, "(\"?dataset=datasets/%s\" % dataset if dataset else \"\")", "\"\""),
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
