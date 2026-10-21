"""The shared project: two people in two browsers on one reference server. Sign in with a token, decide and sign, see each other's work within a second,
a change that was made on stale ground is refused with what changed, the server's rules stop what a page should not do, work made without a network waits
and is sent once, the record can be checked and a cut or edited record is noticed, and signing out gives the browser back its own work.
The page is served by the server itself (reqin/serve_standalone.py demo), so nothing but Python's standard library is needed for it.
Run: python3 b21.py 1440, python3 b21.py 900 and python3 b21.py 390."""
import json, os, re, sqlite3, subprocess, sys, tempfile, time, urllib.request
from h import launch
HERE = os.path.dirname(os.path.abspath(__file__))
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e and 'Failed to load resource' not in e]
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
AXE = os.path.join(HERE, 'vendor', 'node_modules', 'axe-core', 'axe.min.js')
PAGEJS = os.path.join(HERE, 'a11y_page.js')
def body(pg): return pg.inner_text('body')
def flat(t): return re.sub(r'\s+', ' ', t)
def noscroll(pg, label):
    w = pg.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
    ok(w[0] <= w[1], 'no horizontal page scroll: %s (%s vs %s)' % (label, w[0], w[1]))
def nav(pg, label):
    pg.locator('.nav-btn', has_text=label).first.click(); pg.wait_for_timeout(250)
def card(pg): return pg.locator('section[aria-labelledby="conn-h"]')
def keep(pg): return pg.locator('section[aria-labelledby="home-keep"]')
def wait_for(pg, js, timeout=8000):
    try:
        pg.wait_for_function(js, timeout=timeout); return True
    except Exception:
        return False
def has_text(pg, text, timeout=8000):
    return wait_for(pg, "t => document.body.innerText.replace(/\\s+/g, ' ').includes(t)", timeout) if False else _has(pg, text, timeout)
def _has(pg, text, timeout):
    try:
        pg.wait_for_function("t => document.body.innerText.replace(/\\s+/g, ' ').includes(t)", arg=text, timeout=timeout); return True
    except Exception:
        return False
def open_sample(pg):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
def open_cluster(pg, cid):
    pg.fill('#top-search', ''); pg.wait_for_timeout(150)
    pg.fill('#top-search', cid); pg.wait_for_timeout(350)
    pg.get_by_role('button', name=cid).first.click(); pg.wait_for_timeout(350)
def record(pg, cid):
    open_cluster(pg, cid)
    rv = pg.locator('.rv-resolve')
    rv.get_by_role('button', name='Most stringent').click(); pg.wait_for_timeout(200)
    rv.get_by_label('3 · Reason code').select_option(index=1); pg.wait_for_timeout(100)
    rv.locator('textarea[placeholder^="Why this choice"]').fill('Same obligation, the strictest value is kept.'); pg.wait_for_timeout(100)
    if rv.get_by_label('I have read the wordings and the guard results.').count(): rv.get_by_label('I have read the wordings and the guard results.').check()
    pg.wait_for_timeout(100)
    rec = rv.get_by_role('button', name=re.compile('^Record')).first
    ok(rec.is_enabled(), 'record: the decision on %s can be recorded' % cid)
    rec.click(); pg.wait_for_timeout(300)

# ---------------------------------------------------------------- the server: the demo project, the page served from it
tmp = tempfile.mkdtemp(prefix='reqin-b21-')
db = os.path.join(tmp, 'demo.db')
srv = subprocess.Popen([sys.executable, os.path.join(HERE, '..', 'reqin', 'serve_standalone.py'), 'demo', '--db', db, '--seed', os.path.join(HERE, 'demo', 'seed.json'), '--app', os.path.join(HERE, 'project'), '--port', '0'],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
ORIGIN = None
t0 = time.time()
while time.time() - t0 < 30:
    line = srv.stdout.readline()
    m = re.search(r'Serving on (http://127\.0\.0\.1:\d+)', line)
    if m: ORIGIN = m.group(1); break
    if not line and srv.poll() is not None: break
if not ORIGIN:
    print('FAIL the demo server did not start'); srv.kill(); sys.exit(1)
TOK = json.load(open(db + '.tokens.json'))
def api(path, token):
    rq = urllib.request.Request(ORIGIN + '/v1' + path, headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(rq, timeout=10) as r: return json.loads(r.read().decode('utf-8'))
def sign_in(pg, key, wait='Live'):
    pg.fill('#conn-token', TOK[key]); pg.get_by_role('button', name='Sign in').click()
    return _has(pg, 'Shared with your team: demo', 8000)


TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']
def axe(pg):
    return pg.evaluate("""async (tags) => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] });
      return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, ex: v.nodes.slice(0, 2).map((n) => n.target.join(' ').slice(0, 80) + ' :: ' + n.html.slice(0, 100)) }));
    }""", TAGS)
def sweep(pg, label):
    if not pg.evaluate("typeof axe !== 'undefined'"): pg.add_script_tag(path=AXE); pg.add_script_tag(path=PAGEJS)
    pg.evaluate('window.scrollTo(0, 0)')
    v = axe(pg)
    ok(not v, 'axe, %s: no violations%s' % (label, '' if not v else ' -> ' + '; '.join('%s x%d (%s) %s' % (x['id'], x['n'], x['impact'], x['ex'][0]) for x in v)))
    c = pg.evaluate('reqinA11y.contrast()')
    ok(not c['bad'] and not c['unknown'], 'contrast, %s: every text meets 4.5 to 1 and its background could be measured (%d checked)%s' % (label, c['checked'], '' if not c['bad'] else ' -> ' + '; '.join('%s "%s" %s on %s = %s' % (b['el'], b['text'][:30], b['fg'], b['bg'], b['ratio']) for b in c['bad'][:3])))
    p = pg.evaluate('reqinA11y.pointerOnly()')
    ok(not p, 'keyboard, %s: nothing reacts to a click that the keyboard cannot reach%s' % (label, '' if not p else ' -> ' + '; '.join(p[:3])))
def pr(*a): print('   ..', *a)

def stored(pg):
    return pg.evaluate("JSON.stringify({ local: Object.keys(localStorage), session: Object.keys(sessionStorage), href: location.href, cookie: document.cookie })")
def shell_has(pg, text): return text in flat(pg.inner_text('body'))
def held_puts(ctx, pattern):
    """Holds back every PUT to one document until the test lets it go: the page has sent its change, the server has not yet heard it."""
    held = []
    def h(r):
        if r.request.method == 'PUT': held.append(r)
        else: r.fallback()
    ctx.route(pattern, h)
    return held
def wait_list(lst, n=1, timeout=6000):
    t0 = time.time()
    while len(lst) < n and (time.time() - t0) * 1000 < timeout: time.sleep(0.05)
    return len(lst) >= n
def server_doc(key, doc):
    try: return api('/projects/demo/docs/' + doc, TOK[key])
    except Exception as e: return None
def conn_db(): return sqlite3.connect(db, timeout=10)

try:
  with launch() as new_page:
    sam, es = new_page(W, 1000); pri, ep = new_page(W, 1000); mor, em = new_page(W, 1000); cas, ec = new_page(W, 1000)
    for p in (sam, pri, mor, cas):
        p.add_init_script('window.__reqinPollMs = 400')
        p.goto(ORIGIN + '/app/'); p.wait_for_timeout(1500)
    sam.add_script_tag(path=AXE); sam.add_script_tag(path=PAGEJS)

    # ---------------------------------------------------------------- 1. before signing in: the page works on its own, and says so
    ok('Open a requirements project' in sam.title(), 'title: the page served by the server is the same page (%r)' % sam.title())
    c = flat(card(sam).inner_text())
    ok(card(sam).count() == 1 and 'Work with your team on a shared server' in c, 'sign in: the page offers to work with a team on a server')
    ok('Server: ' + ORIGIN in c, 'sign in: it says which server it would talk to (the one it was opened from)')
    ok(sam.locator('#conn-token').get_attribute('type') == 'password' and sam.get_by_label('Your token').count() == 1, 'sign in: the token is typed into a password field with a label')
    ok(sam.get_by_role('button', name=re.compile('^Open the sample project as')).count() == 1 and 'switch person' in flat(body(sam)), 'sign in: until then the page is the stand-alone one, with its demo person picker')
    sam.get_by_role('button', name='Sign in').click(); sam.wait_for_timeout(300)
    ok('Paste the token you were given' in flat(card(sam).inner_text()), 'sign in: an empty token is said to be empty')
    sam.fill('#conn-token', 'not-a-real-token'); sam.get_by_role('button', name='Sign in').click()
    ok(_has(sam, 'That token is not recognised', 4000), 'sign in: a wrong token is refused with a plain message')
    ok(sam.locator('#conn-token').count() == 1 and 'Shared with your team' not in flat(card(sam).inner_text()), 'sign in: a wrong token leaves the page signed out')
    noscroll(sam, 'open screen, signed out'); sweep(sam, 'open screen, a refused token')

    # ---------------------------------------------------------------- 2. signing in
    ok(sign_in(sam, 'sam'), 'sign in: the right token signs Sam in (heading names the project)')
    c = flat(card(sam).inner_text())
    ok('Live' in c and 'Signed in as Sam Okafor' in c and 'nothing is waiting to be sent' in c, 'sign in: the card says Live, who is signed in and that nothing is waiting')
    ok(sam.locator('#conn-token').count() == 0, 'sign in: the token field is gone once signed in')
    s = stored(sam)
    ok(TOK['sam'] not in s and '[]' in s.split('"session"')[0], 'token: not in the address, cookies or browser storage (%s)' % s[:160])
    ok(sam.get_by_role('button', name=re.compile('^Open the sample project as')).count() == 1 and 'switch person' not in flat(body(sam)), 'sign in: the demo person picker is gone, the login decides the person')
    noscroll(sam, 'open screen, signed in'); sweep(sam, 'open screen, signed in')
    for p, k in ((pri, 'priya'), (mor, 'morgan'), (cas, 'casey')): ok(sign_in(p, k), 'sign in: %s signs in with their own token' % k)
    for p in (sam, pri, mor, cas): open_sample(p)
    ok(shell_has(sam, 'Shared · live') and shell_has(sam, 'Signed in as Sam Okafor') and not shell_has(sam, 'Demo only: switch person'), 'shell: says Shared · live, who is signed in, and has no demo person switch')
    ok(sam.locator('[role=status][aria-live=polite]', has_text=re.compile('Shared')).count() == 1, 'shell: the sharing status is a polite live region, so a screen reader hears it change (offline, back, signed out)')
    ok('(sample)' not in sam.locator('header.topbar').inner_text() and sam.locator('[role="group"][aria-label^="Teammates"]').count() == 0, 'shell: the sample teammates are not shown as if they were online')
    nav(sam, 'Home')
    k = flat(keep(sam).inner_text())
    ok('this browser is not keeping a copy' in k, 'keeping work: the card says the server has the copy and this browser keeps none')
    ok(sam.get_by_role('button', name='Load from a file').is_disabled() and sam.get_by_role('button', name='Start over').is_disabled() and sam.get_by_role('button', name='Save to a file').is_enabled(), 'keeping work: Load and Start over are off while shared (they would write over everyone\'s copy); Save is on')
    noscroll(sam, 'home, signed in'); sweep(sam, 'home, live')

    # ---------------------------------------------------------------- 3. one person decides, the other sees it, and signs
    open_cluster(pri, 'CL-001')
    ok('Resolve CL-001' in flat(body(pri)) and pri.get_by_role('button', name=re.compile('^Record')).count() >= 1, 'two people: Priya has CL-001 open and undecided')
    t0 = time.time(); record(sam, 'CL-001')
    ok(_has(pri, 'changed it on the server while you were reading', 6000), 'two people: Priya is told Sam changed the cluster she has open (%.1f s after Sam pressed Record)' % (time.time() - t0))
    ok('Sam Okafor changed it on the server' in flat(body(pri)), 'two people: and the banner names who')
    d = server_doc('sam', 'dec/CL-001')
    ok(d is not None and d['rev'] == 1 and d['by'] == 'sam' and d['body'], 'server: the decision is there once, at revision 1, by Sam')
    pri.get_by_role('button', name='Reload the cluster').click(); pri.wait_for_timeout(400)
    ok('By Sam Okafor' in flat(body(pri)), 'two people: after reloading, Priya sees Sam\'s decision and who made it')
    pri.get_by_role('button', name=re.compile('^Sign off as')).click(); pri.wait_for_timeout(500)
    sg = server_doc('priya', 'sign/CL-001/PE')
    ok(sg is not None and sg['by'] == 'priya' and sg['body']['by'] == 'Priya Raman', 'server: Priya\'s sign-off is there, in her name, for the process-engineering lens')
    ok(_has(sam, 'Priya Raman', 6000) and sam.locator('text=Priya Raman').count() >= 1, 'two people: Sam sees Priya\'s sign-off without reloading')
    ok(sam.evaluate("Object.keys(localStorage).length") == 0, 'keeping work: after a decision and a sign-off, this browser still has stored nothing')
    sam.evaluate("window.dispatchEvent(new Event('pagehide'))"); sam.wait_for_timeout(300)
    ok(sam.evaluate("Object.keys(localStorage).length + Object.keys(sessionStorage).length") == 0, 'keeping work: closing or hiding the page does not write a browser copy while signed in (the last-change save is off too)')

    # ---------------------------------------------------------------- 4. two people decide the same cluster: the later one is refused, with what changed
    held = held_puts(sam.context, '**/v1/projects/demo/docs/dec/CL-002')
    record(sam, 'CL-002')
    ok(wait_list(held), 'conflict: Sam\'s change to CL-002 was sent and is on its way')
    record(pri, 'CL-002'); pri.wait_for_timeout(600)
    d = server_doc('priya', 'dec/CL-002')
    ok(d is not None and d['by'] == 'priya', 'conflict: Priya\'s decision on CL-002 reached the server first')
    for r in held: r.fallback() if False else r.continue_()
    ok(_has(sam, 'Priya Raman changed the decision on CL-002 first', 6000), 'conflict: Sam is told Priya changed it first, and that his change was not made')
    n = flat(sam.locator('[role="alert"]').first.inner_text()) if sam.locator('[role="alert"]').count() else ''
    ok('Not made: someone got there first' in n and 'You:' in n and 'Now:' in n, 'conflict: the notice is on top of the page he is working on, and shows his change and what stands now (%s)' % n[:140])
    d = server_doc('sam', 'dec/CL-002')
    ok(d['by'] == 'priya' and d['rev'] == 1, 'conflict: the server kept Priya\'s decision, untouched')
    ok('By Priya Raman' in flat(body(sam)) or _has(sam, 'By Priya Raman', 3000), 'conflict: Sam\'s page shows what stands, Priya\'s decision, not his own')
    noscroll(sam, 'review page with a notice'); sweep(sam, 'review page with a notice')
    sam.get_by_role('button', name='Dismiss').first.click(); sam.wait_for_timeout(200)
    ok(sam.locator('[role="alert"]').count() == 0, 'conflict: the notice can be dismissed')
    sam.context.unroute('**/v1/projects/demo/docs/dec/CL-002')

    # ---------------------------------------------------------------- 5. no network: the work waits, and is sent once
    n0 = len(api('/projects/demo/events?after=0&limit=1000', TOK['sam'])['events'])
    sam.context.set_offline(True)
    record(sam, 'CL-003'); sam.wait_for_timeout(1500)
    ok(_has(sam, 'Shared · offline, 1 waiting', 5000), 'offline: the shell says Offline and that one change is waiting')
    nav(sam, 'Home')
    ok('Offline' in flat(card(sam).inner_text()) and 'waiting here and will be sent' in flat(card(sam).inner_text()), 'offline: the card says what is waiting and that it will be sent')
    ok(server_doc('priya', 'dec/CL-003') is None, 'offline: the server has not heard it')
    noscroll(sam, 'home, offline'); sweep(sam, 'home, offline')
    sam.context.set_offline(False)
    ok(_has(sam, 'Shared · live', 8000), 'offline: when the network is back the page says Live again')
    sam.wait_for_timeout(600)
    d = server_doc('priya', 'dec/CL-003')
    ok(d is not None and d['rev'] == 1 and d['by'] == 'sam', 'offline: the change reached the server once (revision 1, by Sam)')
    ev = api('/projects/demo/events?after=0&limit=1000', TOK['sam'])['events']
    ok(len([e for e in ev if e['target'] == 'dec/CL-003']) == 1, 'offline: and only one entry in the record is about it')
    open_cluster(pri, 'CL-003')
    ok(_has(pri, 'By Sam Okafor', 4000), 'offline: and Priya sees it, with Sam\'s name, without reloading')

    # ---------------------------------------------------------------- 6. the lead switches AI off: the others follow
    nav(sam, 'AI use'); nav(mor, 'AI use')
    sw = 'Switch AI off for the whole project'
    ok(mor.get_by_role('button', name=sw).is_enabled() and (sam.get_by_role('button', name=sw).count() == 0 or sam.get_by_role('button', name=sw).is_disabled()), 'AI: the lead can switch it; a reviewer cannot')
    mor.get_by_role('button', name='Switch AI off for the whole project').click()
    ok(_has(sam, 'AI is switched off for this project', 6000), 'AI: Sam\'s AI page follows the lead\'s switch')
    ok('Morgan Hale · shared project' in flat(body(sam)) and 'as the shared project has it' in flat(body(sam)), 'AI: and his own record of AI use says it came from the shared project, by whom')
    d = server_doc('sam', 'proj/ai')
    ok(d is not None and d['by'] == 'morgan' and d['body']['on'] is False, 'server: the switch is kept by the server as the lead set it')

    # ---------------------------------------------------------------- 7. a copy of what is on screen can be saved, and opens in a plain browser
    nav(sam, 'Home')
    with sam.expect_download() as dl: sam.get_by_role('button', name='Save to a file').click()
    f = dl.value; path = os.path.join(tmp, 'saved.json'); f.save_as(path)
    saved = json.load(open(path))
    st = saved.get('state') or {}
    ok(saved.get('format') == 'reqin-project-state/1' and all((st.get('dec') or {}).get(c) for c in ('CL-001', 'CL-002', 'CL-003')), 'save: the file holds the shared decisions Sam sees, his own, Priya\'s and the one made offline (%s)' % ', '.join(sorted(k for k in (st.get('dec') or {}) if k in ('CL-001', 'CL-002', 'CL-003'))))
    ok((st.get('sign') or {}).get('CL-001', {}).get('PE'), 'save: and Priya\'s sign-off')

    # ---------------------------------------------------------------- 8. the record can be checked, and a changed record is noticed
    sam.get_by_role('button', name='Check the shared record').click()
    ok(_has(sam, 'The shared record was checked just now', 8000), 'record: the check passes and says how many entries and the newest fingerprint')
    ok(re.search(r'The shared record was checked just now: \d+ entries', flat(card(sam).inner_text())) is not None, 'record: the entry count is shown')

    # ---------------------------------------------------------------- 9. the server stops accepting a token
    with conn_db() as cx: cx.execute("UPDATE people SET token_hash = 'revoked-' || key WHERE key = 'casey'")
    ok(_has(cas, 'Signed out by the server', 6000), 'denied: when the server stops accepting Casey\'s token the page says so')
    nav(cas, 'Home')
    ok('no longer accepts your token' in flat(card(cas).inner_text()), 'denied: and says nothing more is sent or read')
    sweep(cas, 'home, token refused')

    # ---------------------------------------------------------------- 10. signing out gives the browser its own work back
    nav(sam, 'Home')
    sam.get_by_role('button', name='Sign out').click(); sam.wait_for_timeout(500)
    ok(shell_has(sam, 'Not shared') and shell_has(sam, 'Demo only: switch person') and not shell_has(sam, 'Shared · live'), 'sign out: the page is the stand-alone one again, with its demo person picker')
    ok('Signed out' in flat(card(sam).inner_text()) and sam.locator('#conn-token').count() == 1, 'sign out: it says so and offers the token field again')
    nav(sam, 'Review queue')
    ok(re.search(r'Decided\s+71 of 252', body(sam)) is not None or 'Decided 71 of 252' in flat(body(sam)), 'sign out: the shared decisions are gone from the page, the sample\'s own are back (%s)' % re.findall(r'Decided \d+ of 252', flat(body(sam)))[:1])
    ok(sam.evaluate("Object.keys(localStorage).length") == 0, 'sign out: nothing from the shared project was left in this browser by signing out')
    nav(sam, 'Home')
    sam.locator('#keep-file').set_input_files(path); sam.wait_for_timeout(600)
    ok(_has(sam, 'Replace my work with this file', 3000), 'sign out: the file saved while shared is accepted here, with the question about replacing')
    sam.get_by_role('button', name='Replace my work with this file').click(); sam.wait_for_timeout(500)
    nav(sam, 'Review queue')
    ok(re.search(r'Decided (\d+) of 252', flat(body(sam))) and int(re.search(r'Decided (\d+) of 252', flat(body(sam))).group(1)) == 74, 'sign out: and then the three decisions made in the shared project are in this browser (%s)' % re.findall(r'Decided \d+ of 252', flat(body(sam)))[:1])
    for lbl, pg_, er in (('Sam', sam, es), ('Priya', pri, ep), ('Morgan', mor, em), ('Casey', cas, ec)):
        b = bad(er)
        ok(not b, 'console: %s\'s page logged no errors or warnings%s' % (lbl, '' if not b else ' -> ' + '; '.join(b[:3])))

    # ---------------------------------------------------------------- 11. a record cut or changed on the server is noticed by the page
    sam2, es2 = new_page(W, 1000)
    sam2.add_init_script('window.__reqinPollMs = 400'); sam2.goto(ORIGIN + '/app/'); sam2.wait_for_timeout(1200)
    ok(sign_in(sam2, 'sam'), 'tamper: Sam signs in again')
    open_sample(sam2); nav(sam2, 'Home')
    with conn_db() as cx: cx.execute("UPDATE revs SET body = replace(body, 'Same obligation', 'Other obligation') WHERE doc_id = 'dec/CL-001'")
    sam2.get_by_role('button', name='Check the shared record').click()
    ok(_has(sam2, 'does not check out at entry', 8000), 'tamper: a document edited on the server\'s disk is caught by the check, at a named entry')
    ok('Do not rely on it' in flat(card(sam2).inner_text()), 'tamper: and the page says not to rely on it')
    sweep(sam2, 'home, record does not check out')
finally:
    srv.terminate()
print()
print('FAILED: %d' % len(fails) if fails else 'ALL PASSED')
sys.exit(1 if fails else 0)
