"""Mutation run for the reference server (reqin/src/reqin/server): each rule it promises in reqin/SERVER.md is broken in a copy, one at a time, and tests/test_server.py must fail.

Usage: python3 tools/mutation/server.py [part of a name ...]     See README.md in this folder."""
import subprocess, shutil, os, sys
import atexit, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(REPO, 'reqin')
MUT = tempfile.mkdtemp(prefix='reqin-mutation-server-')
atexit.register(shutil.rmtree, MUT, True)
def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT)
    shutil.copytree(SRC+'/src', MUT+'/src', ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copytree(SRC+'/tests', MUT+'/tests', ignore=shutil.ignore_patterns('__pycache__','fixtures_approved'))
    shutil.copy(SRC+'/SERVER.md', MUT+'/SERVER.md')
def run():
    r = subprocess.run('PYTHONPATH=src python3 -m pytest tests/test_server.py -q -x -p no:cacheprovider 2>&1 | tail -4', cwd=MUT, shell=True, capture_output=True, text=True, timeout=300)
    return r.stdout
S='src/reqin/server/store.py'; H='src/reqin/server/http.py'
muts = [
 ('a stale revision overwrites', S, "if if_rev != have:", "if False:"),
 ('observers may write', S, 'if who.role == "observer":\n            raise ServerError(403, "observer"', 'if False:\n            raise ServerError(403, "observer"'),
 ('any lens signs any slot', S, "if slot in LENS_SLOTS and who.lens != slot:", "if False:"),
 ('anyone signs owner and adjudicator slots', S, "if slot in LEAD_SLOTS and who.role != \"lead\":", "if False:"),
 ('people sign their own decisions', S, 'if dec["by_person"] == who.key:', "if False:"),
 ('a sign-off may bind to any revision', S, 'body.get("rev") != dec["rev"]', "False"),
 ('a new revision keeps the old sign-offs', S, 'cleared = self._clear_signoffs(who, doc_id) if doc_id.split("/")[0] in ("dec", "rdec") else []', "cleared = []"),
 ('a withdrawn decision can be signed', S, 'if not dec or json.loads(dec["body"]) is None:', "if not dec:"),
 ('requirement decisions are looked up as cluster decisions', S, 'dec_id = ("rdec/" if not target.startswith("CL-") else "dec/") + target', 'dec_id = "dec/" + target'),
 ('a repeated request is done twice', S, "                    if old:\n", "                    if False:\n"),
 ('a key can be reused for another request', S, 'if old["request_hash"] != req_hash:', "if False:"),
 ('tokens are stored in the clear', S, 'def token_hash(token: str) -> str:\n    return sha256("reqin-token|" + token)', 'def token_hash(token: str) -> str:\n    return token'),
 ('verify ignores edited entries', S, "if self._entry_hash(prev, d) != e[\"hash\"]:", "if False:"),
 ('verify ignores the link between entries', S, 'if e["prev"] != prev:', "if False:"),
 ('verify ignores edited documents', S, 'if sha256(r["body"]) != e["body_hash"] or r["body_hash"] != e["body_hash"]:', "if False:"),
 ('verify ignores who and when', S, 'if r["by_person"] != e["actor"] or r["at"] != e["at"]:', "if False:"),
 ('verify ignores documents outside the record', S, "        if extra:", "        if False:"),
 ('verify ignores a remembered head', S, "if expect_head and expect_head != prev:", "if False:"),
 ('verify ignores a missing entry', S, 'if e["seq"] != n:', "if False:"),
 ('a document may be any size', S, "if len(text.encode(\"utf-8\")) > MAX_BODY_BYTES:", "if False:"),
 ('a failed write stays half done', S, "                if self.db.in_transaction:\n                    self.db.execute(\"ROLLBACK\")", "                pass"),
 ('projects see each other', S, 'return self.db.execute("SELECT * FROM revs WHERE project=? AND doc_id=? ORDER BY rev DESC LIMIT 1", (project, doc_id)).fetchone()', 'return self.db.execute("SELECT * FROM revs WHERE doc_id=? ORDER BY rev DESC LIMIT 1", (doc_id,)).fetchone()'),
 ('an id may end in a newline', S, "DOC_ID.fullmatch(doc_id or \"\")", "DOC_ID.match(doc_id or \"\")"),
 ('a prefix is a pattern', S, 'return prefix.replace("\\\\", "\\\\\\\\").replace("%", "\\\\%").replace("_", "\\\\_") + "%"', 'return prefix + "%"'),
 ('if_rev of true counts', S, "isinstance(if_rev, bool) or ", ""),
 ('the actor can be forged', S, 'ev = self._append(who.project, "doc", who.key, doc_id,', 'ev = self._append(who.project, "doc", (body or {}).get("by", who.key) if isinstance(body, dict) else who.key, doc_id,'),
 ('an old token keeps working', S, 'UPDATE people SET token_hash=? WHERE project=? AND key=?", (token_hash(tok), project, person)', 'UPDATE people SET token_hash=token_hash WHERE project=? AND key=?", (project, person)'),
 ('a token works in any project', H, "if args[0] != who.project:", "if False:"),
 ('replies may be cached', H, 'self.send_header("Cache-Control", "no-store")', "pass"),
 ('replies may be sniffed', H, 'self.send_header("X-Content-Type-Options", "nosniff")', "pass"),
 ('other websites may call the server', H, 'self.send_header("Cache-Control", "no-store")', 'self.send_header("Cache-Control", "no-store"); self.send_header("Access-Control-Allow-Origin", "*")'),
 ('the log keeps the query', H, "{urlsplit(self.path).path} {status}", "{self.path} {status}"),
 ('any address may be bound', H, "if not allow_remote and not is_loopback(host):", "if False:"),
 ('any content type is read', H, 'if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":', "if False:"),
 ('extra fields are accepted', H, 'set(obj) - {"body", "if_rev"}', "set()"),
 ('NaN is accepted', H, "json.loads(raw.decode(\"utf-8\"), parse_constant=no_constants)", "json.loads(raw.decode(\"utf-8\"))"),
 ('a huge request is read', H, "if int(n) > MAX_REQUEST_BYTES:", "if False:"),
 ('a missing revision means new', H, 'req.get("if_rev", None)', 'req.get("if_rev", 0)'),
 ('a 401 does not say how to sign in', H, "h = {\"WWW-Authenticate\": 'Bearer realm=\"reqin\"'} if e.status == 401 else {}", "h = {}"),
 ('an unexpected failure shows its cause', H, "self._send(500, {\"error\": {\"code\": \"server_error\", \"message\": \"The server could not do that.\"}})", "raise"),
]
only = sys.argv[1:]
if only == ['--patterns']:                           # fast: does every change still match the code? (no checks are run)
    gone = [m[0] for m in muts if m[2] not in open(os.path.join(SRC, m[1]), encoding='utf-8').read()]
    for n in gone: print('PATTERN MISSING:', n)
    print('%d of %d changes still match the code' % (len(muts) - len(gone), len(muts)))
    sys.exit(1 if gone else 0)
if only == ['--list']:
    for m in muts: print(m[0])
    sys.exit(0)
unnoticed = []
for name, f, a, b in muts:
    if only and not any(o in name for o in only): continue
    reset()
    p = MUT+'/'+f; s = open(p).read()
    if a not in s:
        print('%-60s PATTERN MISSING (the code has changed; update this mutant)' % name, flush=True); unnoticed.append(name); continue
    open(p,'w').write(s.replace(a, b, 1))
    try:
        out = run()
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT failed'
    last = [l for l in out.strip().splitlines() if l.strip()]
    failed = any(('failed' in l or 'error' in l.lower()) for l in last)
    print('%-60s %s' % (name, ('CAUGHT: ' + (last[-1] if last else ''))[:120] if failed else 'NOT CAUGHT: ' + (last[-1] if last else '')), flush=True)
    if not failed: unnoticed.append(name)
print('\n%s' % ('every change was noticed' if not unnoticed else '%d went unnoticed: %s' % (len(unnoticed), '; '.join(unnoticed))))
sys.exit(1 if unnoticed else 0)
