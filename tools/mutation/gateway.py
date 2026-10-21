"""Mutation run for the AI gateway (reqin/src/reqin/gateway): each rule it promises in docs/AI_GATEWAY.md is broken in a copy, one at a time, and tests/test_gateway.py must fail.

The gateway is the place where "the page says it is off" becomes "nothing reaches the model", so a rule in it that no test can fail is a hole.

Usage: python3 tools/mutation/gateway.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed and is not listed as harmless. See README.md in this folder."""
import atexit, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'reqin')
MUT = tempfile.mkdtemp(prefix='reqin-mutation-gateway-')
atexit.register(shutil.rmtree, MUT, True)
C, H, A, G = 'src/reqin/gateway/core.py', 'src/reqin/gateway/http.py', 'src/reqin/gateway/audit.py', 'src/reqin/gateway/config.py'


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT)
    shutil.copytree(SRC + '/src', MUT + '/src', ignore=shutil.ignore_patterns('__pycache__'))
    os.makedirs(MUT + '/tests')
    shutil.copy(SRC + '/tests/test_gateway.py', MUT + '/tests/test_gateway.py')


def run():
    r = subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_gateway.py', '-q', '-x', '-p', 'no:cacheprovider'], cwd=MUT, capture_output=True, text=True, timeout=300, env=dict(os.environ, PYTHONPATH='src'))
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
    return r.returncode != 0, (last[-1] if last else '')


MUTS = [
 # who may ask, and about what
 ('observers may use the AI', C, 'if role == "observer":', 'if False:'),
 ('a prompt need not say which requirements it holds', C, '    if not ids:\n        return Verdict(False, 400, "no_requirements"', '    if False:\n        return Verdict(False, 400, "no_requirements"'),
 ('any number of requirements in one prompt', C, 'if len(ids) > max_requirements:', 'if False:'),
 ('a requirement the gateway does not know is passed', C, '    if missing:\n', '    if False:\n'),
 ('an id with odd characters is accepted', H, 'bad_id = [x for x in ids if not ID_RE.fullmatch(x)]', 'bad_id = []'),
 ('no token is needed', H, 'if not auth.startswith("Bearer ") or not auth[7:].strip():', 'if False:'),
 ('a token the server does not know is accepted', H, '        if st == 401:\n            return self._error(401, "bad_token", "The reference server does not know that token.")\n        try:\n            who =', '        try:\n            who ='),
 # the switch and the sheet
 ('a project with no sheet is open', C, '    if not ai_present:\n        return Verdict(False, 403, "no_sheet"', '    if False:\n        return Verdict(False, 403, "no_sheet"'),
 ('a name or date that is not text is let through to fail later', C, "if any(k in sh and not isinstance(sh[k], str) for k in STR_FIELDS) or", "if False or"),
 ('a switch-like entry that is not true or false is let through', C, "or (\"leaves\" in sh and not isinstance(sh[\"leaves\"], bool)):", "or False:"),
 ('a sheet in a shape it cannot read is trusted', C, '    if parsed is None:\n        return Verdict(False, 403, "bad_sheet"', '    if False:\n        return Verdict(False, 403, "bad_sheet"'),
 ('the sheet document may carry other entries', C, 'or set(doc) - {"on", "sheet"} or', 'or'),
 ('the switch need not be true or false', C, 'or not isinstance(doc.get("on"), bool)', ''),
 ('the gate is not asked', C, 'd: Decision = ensure(sheet, switch, [markings.marks[i] for i in ids])', 'd: Decision = ensure(sheet, True, [markings.marks[i] for i in ids])'),
 ('a withdrawn sheet is read as a sheet', H, 'present = doc is not None', 'present = True'),
 # the route
 ('the route need not be the sheet\'s model', C, 'for k in ("model", "where", "leaves", "log"):', 'for k in ("where", "leaves", "log"):'),
 ('the route may run elsewhere than the sheet says', C, 'for k in ("model", "where", "leaves", "log"):', 'for k in ("model", "leaves", "log"):'),
 ('the route may send text out when the sheet says it stays', C, 'for k in ("model", "where", "leaves", "log"):', 'for k in ("model", "where", "log"):'),
 ('the route may keep prompts the sheet says are not kept', C, 'for k in ("model", "where", "leaves", "log"):', 'for k in ("model", "where", "leaves"):'),
 ('the days kept need not match', C, 'if sheet.log != "none" or route["log"] != "none":', 'if False:'),
 ('a route that does not match is passed', C, '    bad = route_mismatch(sheet, route)\n    if bad:', '    bad = route_mismatch(sheet, route)\n    if False:'),
 # wording nobody declared
 ('wording of undeclared requirements is not looked for', C, '    leaks = markings.undeclared(prompt, set(ids), min_windows)\n    if leaks:', '    leaks = markings.undeclared(prompt, set(ids), min_windows)\n    if False:'),
 ('a declared requirement counts as a leak', C, 'if not who or who & declared:', 'if not who:'),
 ('one shared phrase is a leak', C, 'if n >= min(min_windows, self.count.get(r, 1))', 'if n >= 1'),
 ('a leak must be half the requirement', C, 'if n >= min(min_windows, self.count.get(r, 1))', 'if n >= max(min_windows, self.count.get(r, 1) // 2)'),
 ('a short requirement is looked for as a long one', C, 'for n in range(MIN_WORDS, WINDOW + 1):', 'for n in range(WINDOW, WINDOW + 1):'),
 ('case matters when looking for wording', C, 't = unicodedata.normalize("NFKC", text).lower()', 't = unicodedata.normalize("NFKC", text)'),
 ('look-alike letters are not folded', C, 't = unicodedata.normalize("NFKC", text).lower()', 't = text.lower()'),
 ('punctuation hides wording', C, 'return [w for w in re.split(r"[\\W_]+", t) if w]', 'return [w for w in t.split() if w]'),
 ('keys of the request are not read', C, '                parts.append(str(k))\n', '                pass\n'),
 ('lists in the request are not read', C, '        elif isinstance(v, list):\n            for x in v:\n                walk(x, depth + 1)\n', '        elif isinstance(v, list):\n            pass\n'),
 ('a very deep request is read without limit', C, 'if depth > 40:', 'if depth > 4000:'),
 # what is passed on
 ('streaming is passed on', H, 'if body.get("stream"):', 'if False:'),
 ('the caller chooses the model', H, '        body["model"] = cfg.route["model"]\n', ''),
 ('the person\'s token is passed to the model', H, 'hdr = {"Content-Type": "application/json"}\n        key = upstream_key(cfg)', 'hdr = {"Content-Type": "application/json", "Authorization": "Bearer " + token}\n        key = upstream_key(cfg)'),
 ('the model\'s key is not sent', H, '        if key:\n            hdr["Authorization"] = "Bearer " + key', '        if False:\n            hdr["Authorization"] = "Bearer " + key'),
 ('a redirect from the model is followed', H, '_OPENER = urllib.request.build_opener(_NoRedirect)', '_OPENER = urllib.request.build_opener()'),
 ('a request of any size is read', H, 'if int(n) > cfg.max_body:', 'if False:'),
 ('any content type is read', H, 'if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != "application/json":', 'if False:'),
 ('a reply of any size is passed on', H, 'if len(udata) > MAX_REPLY:', 'if False:'),
 ('the model\'s own errors are hidden', H, 'self._send(ust, udata,', 'self._send(200, udata,'),
 ('the gate\'s answer is not sent', H, '"X-Reqin-Gate": f"open; level={v.level or \'none\'}; requirements={len(ids)}"', '"X-Reqin-Gate": ""'),
 ('a refused request is not recorded', H, '            srv.audit.add(project=project, person=person, requirements=[x for x in ids if ID_RE.fullmatch(x)][:200], code=v.code, level=v.level, ok=False, upstream=None, prompt_bytes=prompt_bytes)\n', ''),
 ('the record is cut into lines at more than line feeds', A, '.read_text(encoding="utf-8").split("\\n")', '.read_text(encoding="utf-8").splitlines()'),
 ('a blank last line is a record that does not parse', A, '        if lines and lines[-1] == "":\n            lines.pop()\n', ''),
 ('a request that went to the model is not recorded', H, '        srv.audit.add(project=project, person=person, requirements=ids, code="open", level=v.level, ok=True, upstream=ust, prompt_bytes=len(raw))\n', ''),
 ('it listens beyond this machine without being told to', H, 'if not is_loopback(cfg.host) and not cfg.allow_remote:', 'if False:'),
 ('the server being down is read as no sheet', H, '        except Upstream:\n            return self._error(502, "server_unreachable", "The reference server could not be reached, so nothing was sent to the model.")\n        doc: Any = None', '        except Upstream:\n            st, data = 404, b""\n        doc: Any = None'),
 # the record
 ('the record\'s lines are not linked', A, 'if row["prev"] != prev:', 'if False:'),
 ('an edited line in the record is not noticed', A, 'if _hash(row) != row["hash"]:', 'if False:'),
 ('a removed line in the record is not noticed', A, 'if row["seq"] != i:', 'if False:'),
 ('a record cut short is not noticed', A, 'if expect_head and prev != expect_head:', 'if False:'),
 ('a record that does not check out is appended to', A, '            if not res["ok"]:\n                raise ValueError', '            if False:\n                raise ValueError'),
 # the markings file and the settings
 ('a markings file of another format is read', C, 'data.get("format") != MARKINGS_FORMAT or', ''),
 ('a fingerprint of any shape is read', C, 'not all(isinstance(x, str) and re.fullmatch(r"[0-9a-f]{16}", x) for x in fp)', 'False'),
 ('the key may be written in the settings', G, 'or (key_env and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key_env))', ''),
 ('a password may be in a web address', G, 'or u.username or u.password or u.fragment', ''),
 ('a route that names no model is read', G, 'if not isinstance(up["model"], str) or not up["model"].strip():', 'if False:'),
 ('unknown settings are ignored', G, 'if set(d) - known:', 'if False:'),
 ('a model that is not on our servers need not say so', G, 'if up["where"] not in WHERE or up["log"] not in LOG or not isinstance(up["leaves"], bool):', 'if False:'),
]
# a change to a place the tests cannot reach, with the reason
EQUIVALENT = {}

only = sys.argv[1:]
if only == ['--patterns']:
    gone = [m[0] for m in MUTS if m[2] not in open(os.path.join(SRC, m[1]), encoding='utf-8').read()]
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
        print('%-62s PATTERN MISSING (the code has changed; update this mutant)' % name, flush=True); unnoticed.append(name); continue
    open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
    try:
        caught, why = run()
    except subprocess.TimeoutExpired:
        caught, why = True, 'TIMEOUT'
    if caught: print('%-62s CAUGHT: %s' % (name, why[:80]), flush=True)
    elif name in EQUIVALENT: print('%-62s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
    else: print('%-62s NOT CAUGHT' % name, flush=True); unnoticed.append(name)
print('\n%s' % ('every change was noticed' if not unnoticed else '%d went unnoticed: %s' % (len(unnoticed), '; '.join(unnoticed))))
sys.exit(1 if unnoticed else 0)
