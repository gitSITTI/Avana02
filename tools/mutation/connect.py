"""Breaking the connected page on purpose: do the checks notice?

Two sets of changes, each made one at a time in a throwaway copy of the page, which is rebuilt each time:

  engine   the sync rules in prototype/parts/connect.js (send the revision you read, a refused change is taken back, a lost answer is not sent twice, a record that went
           backwards is noticed, a change of yours that is waiting is not written over). Checked by prototype/conn_test.js against a REAL reference server started for
           the run, with several people at once. Needs node only. About 10 seconds each.
  page     what the page does with the engine (nothing is kept in the browser while signed in, Load and Start over are off, signing out puts the browser's own work back,
           a refused change is shown where the person is working). Checked by prototype/b21.py in a browser, four people on one server. Needs Playwright and a Chromium,
           like the browser tests. About 2 minutes each.

Usage: python3 tools/mutation/connect.py [engine|page] [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed and is not listed as harmless."""
import os, shutil, subprocess, sys
import common
from common import SRC, MUT, WORK, REPO, reset

CONN, C7, C9, SHELL = 'parts/connect.js', 'parts/c7.js', 'parts/c9.js', 'parts/m/30_shell_open.html'

# (name, file, old text, new text)
ENGINE = [
 ('a change is sent without the revision it changes', CONN, "const rev = ctx.revs[ch.id] || 0, wire", "const rev = 0, wire"),
 ('a refused change stays on the screen', CONN, "in the server's words\n  connSet(ctx, [{ id: ch.id, body: ctx.base[ch.id] || null }]);", "in the server's words\n"),
 ('someone got there first and the page keeps its own version', CONN, "connSet(ctx, [{ id: ch.id, body: theirs, rev: typeof e.rev === 'number' ? e.rev : rev }]);", ""),
 ('someone got there first and nothing is said', CONN, "if (!connSame(theirs, ch.body)) ctx.hooks.notice({ kind: 'conflict', id: ch.id, text: connWho(", "if (false) ctx.hooks.notice({ kind: 'conflict', id: ch.id, text: connWho("),
 ('a lost answer makes the next try a new request', CONN, "const key = ctx.idem[ck] || (ctx.idem[ck] = 'c' +", "const key = (ctx.idem[ck] = 'c' +"),
 ('no network is taken for a refusal', CONN, "if (r.status === 0 || r.status === 429 || r.status >= 500) { ctx.hooks.status('offline'", "if (r.status === 429 || r.status >= 500) { ctx.hooks.status('offline'"),
 ('a token the server dropped is not noticed when sending', CONN, "if (r.status === 401) { ctx.hooks.status('denied', 0); return 'stop'; }\n  delete ctx.idem[ck];", "delete ctx.idem[ck];"),
 ('a record that went backwards is not noticed', CONN, "if (head.seq < ctx.head.seq || (head.seq === ctx.head.seq && ctx.head.hash && head.hash !== ctx.head.hash)) {", "if (false) {"),
 ('a rewritten record is not noticed', CONN, "(head.seq === ctx.head.seq && ctx.head.hash && head.hash !== ctx.head.hash)", "(false)"),
 ('their change is written over a change of yours that is waiting', CONN, "if (!connSame(local[c.id], ctx.base[c.id])) return;", ""),
 ('an older revision is taken as news', CONN, "if (c.rev <= (ctx.revs[c.id] || 0)) return;\n    if (!connSame", "if (!connSame"),
 ('a document that does not fit is shown', CONN, "if (why) { ctx.revs[c.id] = c.rev; ctx.bad[c.id] = true;", "if (false) { ctx.revs[c.id] = c.rev; ctx.bad[c.id] = true;"),
 ('sign-offs the server cleared stay on the screen', CONN, "{ connSet(ctx, [{ id: cid, body: null }]); ctx.hooks.notice({ kind: 'cleared'", "{ ctx.hooks.notice({ kind: 'cleared'"),
 ('a sign-off names the wrong revision of the decision', CONN, "dr = ctx.revs['dec/' + target] || ctx.revs['rdec/' + target] || 0;", "dr = 1;"),
 ('a sign-off goes before the decision it binds to', CONN, "return out.sort((a, b) => ord(a.id) - ord(b.id) || (a.id < b.id", "return out.sort((a, b) => (a.id < b.id"),
 ('the sample\'s own activity is kept when signing in', CONN, "if (k.empty !== undefined) Object.keys(k.seed()).forEach((id) => { m[id] = k.empty; });", ""),
 ('a withdrawn document comes back', CONN, "Object.keys(ctx.base).forEach((id) => { if (!(id in docs)) changes.push({ id, rev: (ctx.revs[id] || 0) + 1, body: null }); });", ""),
 ('the lead\'s AI switch is not taken', CONN, "if (pl.top === 'ai') { patch.aiOn = body ? body.on : CONN_NO_AI.on;", "if (pl.top === 'ai') { return; patch.aiOn = body ? body.on : CONN_NO_AI.on;"),
 ('a shared project with no AI document is open', CONN, "sk.aiOn = CONN_NO_AI.on; sk.aiSheet = CONN_NO_AI.sheet;", "sk.aiOn = DEFAULTS.aiOn; sk.aiSheet = DEFAULTS.aiSheet;"),
 ('a withdrawn AI document leaves the old switch on the screen', CONN, "patch.aiOn = body ? body.on : CONN_NO_AI.on; patch.aiSheet = body ? body.sheet : CONN_NO_AI.sheet;", "patch.aiOn = body ? body.on : S.aiOn; patch.aiSheet = body ? body.sheet : S.aiSheet;"),
 ('a failed record check is reported as passed', CONN, "if (v.body.ok) return { ok: true,", "if (true) return { ok: true,"),
 ('an AI setting that cannot be read is trusted', CONN, "if (ai && connCheck(ai.id, ai.body)) {", "if (false) {"),
]

PAGE = [
 ('a browser copy is written when the page is hidden while signed in', C7, "if (this._keepHold || this._conn || !persistHasWork(S)) return;", "if (!persistHasWork(S)) return;"),
 ('Load from a file is on while shared', C7, "kLoadDisabled: conn,", "kLoadDisabled: false,"),
 ('Start over is on while shared', C7, "kStartDisabled: conn || (!work", "kStartDisabled: (!work"),
 ('signing out leaves what was typed in the browser', CONN, "const CONN_DRAFT_KEYS = ['res', 'why',", "const CONN_DRAFT_KEYS = ['why',"),
 ('signing out leaves the page\'s record of what was done', CONN, "'blind', 'blindDone', 'liveVer', 'events', 'person'];", "'blind', 'blindDone', 'liveVer', 'person'];"),
 ('signing out keeps the shared decisions', C9, "const back = Object.assign({}, this._connBefore);", "const back = {};"),
 ('a refused change is shown only on Home', C9, "cnNotesInShell: (c.notices || []).length > 0 && S.view !== 'open'", "cnNotesInShell: false"),
 ('the demo person picker stays while signed in', C9, "cnDemo: !signed", "cnDemo: true"),
 ('sample teammates shown as online while shared', SHELL, '<sc-if value="{{cnDemo}}" hint-placeholder-val="{{ true }}"><span style="display:inline-flex;align-items:center;padding-right:10px" role="group"', '<sc-if value="{{ true }}" hint-placeholder-val="{{ true }}"><span style="display:inline-flex;align-items:center;padding-right:10px" role="group"'),
 ('the sharing status is not announced', SHELL, '<span role="status" aria-live="polite" style="{{cnShortStyle}}">', '<span style="{{cnShortStyle}}">'),
]

EQUIVALENT = {
    'a withdrawn document comes back': 'the list is asked for withdrawn documents too (withdrawn=1), so a document is never missing from it; this line is a second guard for a server that leaves one out',
}


def run_engine():
    sys.path.insert(0, SRC)
    import run_conn_test
    r = subprocess.run('python3 build.py >/dev/null', cwd=MUT, shell=True, capture_output=True, text=True)
    if r.returncode: return True, 'the page no longer builds: ' + (r.stderr or r.stdout)[-100:]
    ok, lines = run_conn_test.run(os.path.join(MUT, 'project', 'Main.dc.html'), timeout=150, cwd=MUT)
    fails = [l for l in lines if l.startswith('FAIL')]
    return not ok, (fails or [''])[0]


def run_page():
    r = subprocess.run('python3 build.py >/dev/null && python3 b21.py 1440', cwd=MUT, shell=True, capture_output=True, text=True, timeout=900)
    out = r.stdout + r.stderr
    fails = [l for l in out.splitlines() if l.startswith('FAIL')]
    crash = [l for l in out.splitlines() if 'Error' in l][:1]
    return r.returncode != 0 or bool(fails), (fails or crash or [''])[0]


def prepare_page():
    for f in ('h.py', 'b21.py', 'a11y_page.js', 'export_seed.js'): shutil.copy(os.path.join(SRC, f), os.path.join(MUT, f))
    for f in ('support.js', 'canvas.json'):
        if os.path.exists(os.path.join(SRC, 'project', f)): shutil.copy(os.path.join(SRC, 'project', f), os.path.join(MUT, 'project', f))
    if os.path.exists(os.path.join(SRC, 'project', 'fonts')): shutil.copytree(os.path.join(SRC, 'project', 'fonts'), os.path.join(MUT, 'project', 'fonts'))
    shutil.copytree(os.path.join(SRC, 'demo'), os.path.join(MUT, 'demo'))
    os.symlink(os.path.join(SRC, 'vendor'), os.path.join(MUT, 'vendor'))
    # b21 starts the server from ../reqin and serves the copy's project folder: the copy sits in WORK/prototype, so the server code is found beside it
    if not os.path.lexists(os.path.join(WORK, 'reqin')): os.symlink(os.path.join(REPO, 'reqin'), os.path.join(WORK, 'reqin'))


def main():
    args = sys.argv[1:]
    which = [a for a in args if a in ('engine', 'page')]
    rest = [a for a in args if a not in ('engine', 'page') and not a.startswith('--')]
    sets = [(n, m) for n, m in (('engine', ENGINE), ('page', PAGE)) if not which or n in which]
    if '--list' in args:
        for n, ms in sets:
            for m in ms: print('%s: %s' % (n, m[0]))
        return 0
    if '--patterns' in args:
        missing = [m[0] for n, ms in sets for m in ms if m[2] not in open(os.path.join(SRC, m[1]), encoding='utf-8').read()]
        for n in missing: print('PATTERN MISSING:', n)
        print('%d of %d changes still match the code' % (sum(len(ms) for _, ms in sets) - len(missing), sum(len(ms) for _, ms in sets)))
        return 1 if missing else 0
    survivors = []
    for n, ms in sets:
        print('--- %s' % n)
        for name, f, a, b in ms:
            if rest and not any(o in name for o in rest): continue
            reset()
            if n == 'page': prepare_page()
            else: shutil.copy(os.path.join(SRC, 'conn_test.js'), os.path.join(MUT, 'conn_test.js'))
            p = os.path.join(MUT, f)
            s = open(p, encoding='utf-8').read()
            if a not in s:
                print('%-62s PATTERN MISSING (the code has changed; update this change)' % name, flush=True); survivors.append(name); continue
            open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
            caught, why = (run_engine if n == 'engine' else run_page)()
            if caught: print('%-62s CAUGHT: %s' % (name, why[:100]), flush=True)
            elif name in EQUIVALENT: print('%-62s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
            else: print('%-62s NOT CAUGHT' % name, flush=True); survivors.append(name)
    print('\n%s' % ('every change was noticed' if not survivors else '%d went unnoticed: %s' % (len(survivors), '; '.join(survivors))))
    return 1 if survivors else 0


if __name__ == '__main__':
    sys.exit(main())
