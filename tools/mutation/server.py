"""Mutation run for the reference server (reqin/src/reqin/server): each rule it promises in reqin/SERVER.md is broken in a copy, one at a time, and tests/test_server.py or tests/test_server_app.py must fail.

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
    shutil.copy(SRC+'/serve_standalone.py', MUT+'/serve_standalone.py')
def run():
    r = subprocess.run('PYTHONPATH=src python3 -m pytest tests/test_server.py tests/test_server_app.py -q -x -p no:cacheprovider 2>&1 | tail -4', cwd=MUT, shell=True, capture_output=True, text=True, timeout=300)
    return r.stdout
S='src/reqin/server/store.py'; H='src/reqin/server/http.py'
muts = [
 ('withdrawal bypasses slot permissions', S, '        if slot in LEAD_SLOTS and who.role != "lead":', '        if body is None:\n            return\n        if slot in LEAD_SLOTS and who.role != "lead":'),
 ('another signer withdraws an approval', S, 'current["by_person"] != who.key', 'False'),
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
 ('a refused body is not read, so the answer can be lost to a reset', H, "        if self._unread():\n            self._drain()\n", "        pass\n"),
 ('verify ignores a missing entry', S, 'if e["seq"] != n:', "if False:"),
 ('a document may be any size', S, "if len(text.encode(\"utf-8\")) > MAX_BODY_BYTES:", "if False:"),
 ('a failed write stays half done', S, "                if self.db.in_transaction:\n                    self.db.execute(\"ROLLBACK\")", "                pass"),
 ('projects see each other', S, 'return self.db.execute("SELECT * FROM revs WHERE project=? AND doc_id=? ORDER BY rev DESC LIMIT 1", (project, doc_id)).fetchone()', 'return self.db.execute("SELECT * FROM revs WHERE doc_id=? ORDER BY rev DESC LIMIT 1", (doc_id,)).fetchone()'),
 ('an id may end in a newline', S, "not DOC_ID.fullmatch(doc_id)", "not DOC_ID.match(doc_id)"),
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
 ('project settings are open to reviewers', S, 'if parts[0] in LEAD_ONLY_KINDS:\n            if who.role != "lead":', 'if parts[0] in LEAD_ONLY_KINDS:\n            if False:'),
 ('rulings on labelled pairs are open to reviewers', S, 'LEAD_ONLY_KINDS = ("proj", "adj", "gadj")', 'LEAD_ONLY_KINDS = ("proj", "adj")'),
 ('anyone closes an objection', S, 'if parts[0] == "obj" and body is None and who.role != "lead":', 'if False:'),
 ('a label under someone else\'s key', S, 'if parts[3] != who.key:', 'if False:'),
 ('a label of the wrong shape', S, 'if len(parts) != 4:\n                raise ServerError(400, "bad_label_id"', 'if False:\n                raise ServerError(400, "bad_label_id"'),
 ('a seed overwrites a project that has work', S, 'if self.db.execute("SELECT 1 FROM revs WHERE project=? LIMIT 1", (project,)).fetchone():', 'if False:'),
 ('a seed names an observer as an author', S, 'if not isinstance(by, str) or by not in people or people[by]["role"] == "observer":', 'if not isinstance(by, str) or by not in people:'),
 ('the page can read files outside its folder', H, 'if root not in target.parents or not target.is_file()', 'if not target.is_file()'),
 ('files that start with a dot are served', H, 'any(p == "" or p.startswith(".") for p in parts)', 'any(p == "" for p in parts)'),
 ('the page can be changed through the server', H, 'if self.command not in ("GET", "HEAD"):\n            raise ServerError(405, "method_not_allowed", f"{self.command} is not allowed here.")', 'if False:\n            raise ServerError(405, "method_not_allowed", f"{self.command} is not allowed here.")'),
 ('any file type is served', H, 'or Path(parts[-1]).suffix.lower() not in STATIC_TYPES:', 'or False:'),
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
