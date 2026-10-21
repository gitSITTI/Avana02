"""Keeping the work: autosave in this browser, restore on reload, save to a file, load from a file (and what is refused), start over,
storage that is blocked or full, and two tabs of one browser. Run: python3 b18.py 1440, python3 b18.py 900 and python3 b18.py 390."""
import json, re, sys
from h import session
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
def body(pg): return pg.inner_text('body')
def noscroll(pg, label):
    w = pg.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
    ok(w[0] <= w[1], 'no horizontal page scroll: %s (%s vs %s)' % (label, w[0], w[1]))
def nav(pg, label):
    pg.locator('.nav-btn', has_text=label).first.click(); pg.wait_for_timeout(250)
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
STORE = 'reqin-prototype-state/1'
FILE = 'reqin-project-state.json'
def keep(pg): return pg.locator('section[aria-labelledby="home-keep"]')
def stored(pg):
    raw = pg.evaluate("k => { try { return localStorage.getItem(k); } catch (e) { return null; } }", STORE)
    return json.loads(raw) if raw else None
def status(pg): return keep(pg).locator('[role="status"]').inner_text().strip()
def btn(pg, name): return keep(pg).get_by_role('button', name=re.compile(r'^' + name))
def open_sample(pg):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
def open_cluster(pg, cid):
    pg.fill('#top-search', ''); pg.wait_for_timeout(150)   # the box only reacts to a change, so it is emptied first
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
    rec.click(); pg.wait_for_timeout(400)
def home(pg): nav(pg, 'Home')
def waiting(pg): return pg.inner_text('h1')
def chain(pg):
    nav(pg, 'Decisions and audit'); pg.get_by_role('button', name='Event chain').click(); pg.wait_for_timeout(250)
    pg.get_by_role('button', name='Verify the chain').click(); pg.wait_for_timeout(250)
    return re.search(r'Chain verified: all (\d+) entries', body(pg))
def pick_file(pg, name, data, mime='application/json'):
    """Choose a file and wait until the card has answered: a new message, or the question about replacing."""
    js = "() => { const s = document.querySelector('section[aria-labelledby=home-keep]'); return s ? s.innerText : ''; }"
    before = pg.evaluate(js)
    pg.set_input_files('#keep-file', {'name': name, 'mimeType': mime, 'buffer': data if isinstance(data, bytes) else data.encode('utf-8')})
    pg.wait_for_function("([js, before]) => { const t = eval(js)(); return t !== before; }", arg=[js, before], timeout=15000); pg.wait_for_timeout(150)

with session(W, 1000) as (pg, errs):
    ok(stored(pg) is None, 'start: nothing is kept before anything is done')
    open_sample(pg)
    # ---- the card, with nothing decided
    k = keep(pg)
    ok(k.count() == 1 and k.locator('h2').inner_text().strip() == 'Your work', 'card: Home has a "Your work" card')
    ok('it is kept here by itself' in k.inner_text() and 'not encrypted' in k.inner_text() and 'sign in to the team’s server' in k.inner_text(), 'card: it says what is kept, that it is not encrypted and that sharing is done by signing in to the team’s server')
    ok(btn(pg, 'Start over').is_disabled() and btn(pg, 'Save to a file').is_enabled() and btn(pg, 'Load from a file').is_enabled(), 'card: Start over is off until there is work; save and load are on')
    ok(all(btn(pg, n).evaluate('e => e.getBoundingClientRect().height') >= 44 for n in ['Save to a file', 'Load from a file', 'Start over']), 'card: every button is at least 44 px tall')
    fi = pg.locator('#keep-file')
    ok(fi.get_attribute('aria-label') == 'Choose a saved project file' and fi.get_attribute('tabindex') == '-1' and fi.evaluate('e => getComputedStyle(e).display') == 'none', 'card: the file chooser is hidden, named, and not a tab stop (the button opens it)')
    ok(k.locator('[role="status"]').count() == 1, 'card: there is one status region for messages')
    for label in ['Review queue', 'All requirements', 'The V']: nav(pg, label)
    pg.get_by_role('button', name=re.compile(r'^Priya\b')).first.click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name=re.compile(r'^Sam\b')).first.click(); pg.wait_for_timeout(300)
    home(pg); pg.wait_for_timeout(600)
    ok(stored(pg) is None, 'autosave: moving around and changing person is not work, so nothing is written')
    h1_fresh = waiting(pg)
    noscroll(pg, 'Home with the Your work card')

    # ---- a decision is kept by itself
    record(pg, 'CL-001'); pg.wait_for_timeout(700)
    s = stored(pg)
    ok(s is not None and s['format'] == 'reqin-project-state/1' and s['opened'] is True and s['state']['dec']['CL-001']['outcome'] == 'merge', 'autosave: after a decision the work is in the browser, marked as opened')
    ok(s and 'view' not in s['state'] and 'selected' not in s['state'] and 'qSearch' not in s['state'] and 'keepMsg' not in s['state'], 'autosave: which screen is open and what is typed are not kept')
    ok(s and s['project']['requirements'] > 1000 and len(s['project']['fingerprint']) >= 6, 'autosave: the file says which project it belongs to')
    home(pg)
    t = keep(pg).inner_text()
    ok(re.search(r'Kept automatically at \d\d:\d\d:\d\d: 1 decision, 0 sign-offs', t) is not None, 'card: it says when the work was kept and what is in it (%s)' % re.sub(r'\s+', ' ', t)[:160])
    ok(btn(pg, 'Start over').is_enabled(), 'card: Start over is on once there is work')
    h1_done = waiting(pg)
    ok(h1_done != h1_fresh, 'check: the Home headline changed with the decision (%r to %r)' % (h1_fresh, h1_done))
    noscroll(pg, 'Home after a decision')

    # ---- save to a file
    with pg.expect_download() as dl:
        btn(pg, 'Save to a file').click()
    path = dl.value.path()
    ok(dl.value.suggested_filename == FILE, 'save: the file is called %s (%s)' % (FILE, dl.value.suggested_filename))
    saved = json.load(open(path))
    ok(saved['format'] == 'reqin-project-state/1' and saved['state']['dec']['CL-001'] == s['state']['dec']['CL-001'] and saved['counts']['decisions'] == 1 and saved['project']['fingerprint'] == s['project']['fingerprint'], 'save: the file holds the decision, its counts and the project it belongs to')
    ok(len(saved['state']['events']) >= 1 and all(e['hash'] and e['prev'] for e in saved['state']['events']), 'save: the file holds the record of events')
    pg.wait_for_timeout(200)
    ok('Saved ' + FILE + ': 1 decision, 0 sign-offs, 1 event.' in status(pg), 'save: the status region says what was saved (%s)' % status(pg)[:80])
    ok(chain(pg) is not None, 'audit: the chain still verifies after saving')
    ok('Saved the project state to a file' in body(pg), 'audit: saving a file is in the log')
    home(pg)

    # ---- reload: the work comes back
    pg.reload(); pg.wait_for_timeout(1800)
    ok(keep(pg).count() == 1 and 'Picked up where you left off' in keep(pg).inner_text(), 'restore: after a reload Home says it picked up where the person left off')
    ok(waiting(pg) == h1_done, 'restore: the headline is the one from before the reload (%r)' % waiting(pg))
    ok(btn(pg, 'Start over').is_enabled(), 'restore: Start over is available')
    m = chain(pg)
    ok(m is not None and int(m.group(1)) >= 5, 'restore: the record of events came back and its chain verifies (%s)' % (m.group(0) if m else re.sub(r'\s+', ' ', body(pg))[:200]))
    ok('Decision:' in body(pg), 'restore: the decision is in the log')
    open_cluster(pg, 'CL-001')
    ok('changed after you opened it' not in body(pg), 'restore: nothing reads as changed behind the person’s back')
    ok(bad(errs) == [], 'no console errors through reload: %s' % bad(errs)[:3])
    home(pg)

    # ---- start over asks first
    btn(pg, 'Start over').click(); pg.wait_for_timeout(200)
    g = keep(pg).locator('[role="group"][aria-label="Confirm start over"]')
    ok(g.count() == 1 and 'Remove my work and start over' in g.inner_text() and 'A saved file is not touched' in g.inner_text(), 'start over: it asks first and says a saved file is not touched')
    ok(stored(pg) is not None, 'start over: nothing is removed yet')
    g.get_by_role('button', name='Keep my work').click(); pg.wait_for_timeout(200)
    ok(g.count() == 0 and stored(pg) is not None and btn(pg, 'Start over').is_enabled(), 'start over: keeping the work closes the question and removes nothing')
    noscroll(pg, 'Home with a question open')
    btn(pg, 'Start over').click(); pg.wait_for_timeout(200)
    keep(pg).get_by_role('button', name='Remove my work and start over').click(); pg.wait_for_timeout(500)
    ok(pg.get_by_role('button', name='Open the sample project').count() == 1, 'start over: it goes back to Open')
    ok(stored(pg) is None, 'start over: what the browser held is removed')
    pg.reload(); pg.wait_for_timeout(1500)
    ok(pg.get_by_role('button', name='Open the sample project').count() == 1 and 'Picked up' not in body(pg), 'start over: a reload starts clean')
    open_sample(pg)
    ok(waiting(pg) == h1_fresh, 'start over: the headline is the fresh one again')
    ok(stored(pg) is None, 'start over: and the empty page does not write itself back')

    # ---- load from a file: checked first, replaced only when the person says
    pick_file(pg, FILE, json.dumps(saved))
    g = keep(pg).locator('[role="group"][aria-label="Confirm loading a file"]')
    ok(g.count() == 1 and 'Replace the work in this browser with this file?' in g.inner_text(), 'load: a good file asks before replacing')
    gt = g.inner_text()
    ok(FILE in gt and '1 decision, 0 sign-offs' in gt and 'The record of events is intact' in gt and 'passed every check' in gt, 'load: the summary names the file, what is in it and that the record is intact (%s)' % re.sub(r'\s+', ' ', gt)[:200])
    ok(waiting(pg) == h1_fresh and stored(pg) is None, 'load: nothing has changed yet')
    noscroll(pg, 'Home with the load question open')
    g.get_by_role('button', name='Keep my work').click(); pg.wait_for_timeout(200)
    ok(g.count() == 0 and waiting(pg) == h1_fresh, 'load: cancelling leaves the work as it was')
    pick_file(pg, FILE, json.dumps(saved))
    keep(pg).get_by_role('button', name='Replace my work with this file').click(); pg.wait_for_timeout(700)
    ok('Loaded ' + FILE in status(pg), 'load: the status region says it was loaded (%s)' % status(pg)[:90])
    ok(waiting(pg) == h1_done, 'load: the headline is the one from the file')
    m = chain(pg)
    ok(m is not None and 'Loaded saved work from ' + FILE in body(pg), 'load: the chain verifies and the log says the file was loaded')
    home(pg); pg.wait_for_timeout(500)
    ok(stored(pg) is not None and stored(pg)['state']['dec']['CL-001']['outcome'] == 'merge', 'load: and the loaded work is kept by itself from then on')

    # ---- files that are refused leave the work as it was
    def refuse(name, data, want, mime='application/json'):
        pick_file(pg, name, data, mime)
        st = status(pg)
        ok('was not loaded' in st or 'is not a saved project' in st, '%s: refused (%s)' % (name, st[:110]))
        ok(re.search(want, st + ' ' + keep(pg).inner_text()) is not None, '%s: the reason is given (%s)' % (name, want))
        ok(keep(pg).locator('[role="group"][aria-label="Confirm loading a file"]').count() == 0 and waiting(pg) == h1_done, '%s: nothing is offered and nothing changed' % name)
    refuse('notes.txt', 'hello', r'not valid JSON', 'text/plain')
    refuse('list.json', '[]', r'not a saved project')
    refuse('other.json', json.dumps(dict(saved, format='reqin-project-state/9')), r'format')
    refuse('nostate.json', json.dumps({k: v for k, v in saved.items() if k != 'state'}), r'no saved work')
    o = json.loads(json.dumps(saved)); o['project']['fingerprint'] = 'ffff'
    refuse('elsewhere.json', json.dumps(o), r'different project')
    t = json.loads(json.dumps(saved)); t['state']['events'][0]['text'] = 'Changed after the fact'
    refuse('tampered.json', json.dumps(t), r'has been changed: entry \d+')
    w = json.loads(json.dumps(saved)); w['state']['dec'] = []
    refuse('wrongtype.json', json.dumps(w), r'“dec” should be object and is array')
    refuse('big.json', b'{"x":"' + b'a' * (5 * 1024 * 1024) + b'"}', r'larger than 4 MB')
    # a file with entries for things the project does not have loads, and says how many were left out
    x = json.loads(json.dumps(saved)); x['state']['dec']['CL-9999'] = x['state']['dec']['CL-001']; x['state']['rdec'] = {'REQ-NOPE-1': {'outcome': 'keep', 'by': 'x', 'rev': 'S1'}}
    pick_file(pg, 'extra.json', json.dumps(x))
    gt = keep(pg).locator('[role="group"][aria-label="Confirm loading a file"]').inner_text()
    ok('2 entries pointed at something this project does not have' in gt, 'extra entries: they are counted and said before anything is replaced (%s)' % re.sub(r'\s+', ' ', gt)[-150:])
    keep(pg).get_by_role('button', name='Keep my work').click(); pg.wait_for_timeout(200)
    ok(bad(errs) == [], 'no console errors through the load and the refusals: %s' % bad(errs)[:3])

    # ---- keyboard
    pg.locator('#top-search').focus()
    reached = False
    for _ in range(80):
        pg.keyboard.press('Tab')
        if (pg.evaluate("document.activeElement.textContent || ''") or '').strip() == 'Save to a file': reached = True; break
    ok(reached, 'keyboard: Tab reaches Save to a file')
    ol = pg.evaluate("(() => { const s = getComputedStyle(document.activeElement); return [s.outlineStyle, s.boxShadow]; })()")
    ok(ol[0] != 'none' or ol[1] != 'none', 'keyboard: it shows a focus ring (%s)' % ol)
    pg.keyboard.press('Tab'); pg.keyboard.press('Tab'); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ok(keep(pg).locator('[role="group"][aria-label="Confirm start over"]').count() == 1, 'keyboard: Tab, Tab, Enter reaches Start over and opens its question')
    keep(pg).get_by_role('button', name='Keep my work').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ok(keep(pg).locator('[role="group"]').count() == 0, 'keyboard: Enter on Keep my work closes it')

with session(W, 1000) as (pg, errs):
    # ---- storage that is blocked: the page works and says so
    pg.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new DOMException('blocked', 'SecurityError'); } });")
    pg.reload(); pg.wait_for_timeout(1500)
    open_sample(pg)
    ok('Your work is not being kept' in keep(pg).inner_text() and 'Save a file before you close the tab' in keep(pg).inner_text(), 'blocked: Home says plainly that nothing is being kept and what to do')
    record(pg, 'CL-001'); home(pg)
    ok('Your work is not being kept' in keep(pg).inner_text() and btn(pg, 'Save to a file').is_enabled(), 'blocked: after a decision it still says so, and saving a file works')
    with pg.expect_download() as dl:
        btn(pg, 'Save to a file').click()
    ok(json.load(open(dl.value.path()))['state']['dec']['CL-001']['outcome'] == 'merge', 'blocked: the saved file has the decision')
    noscroll(pg, 'Home with storage blocked')
    ok(bad(errs) == [], 'blocked: no console errors: %s' % bad(errs)[:3])

with session(W, 1000) as (pg, errs):
    # ---- storage that is full
    pg.add_init_script("(() => { const o = Storage.prototype.setItem; Storage.prototype.setItem = function (k, v) { if (k === '%s') throw new DOMException('full', 'QuotaExceededError'); return o.apply(this, arguments); }; })();" % STORE)
    pg.reload(); pg.wait_for_timeout(1500)
    open_sample(pg); record(pg, 'CL-001'); pg.wait_for_timeout(700); home(pg)
    ok('Your work is too large to keep here' in keep(pg).inner_text() and 'Save a file' in keep(pg).inner_text(), 'full: Home says plainly that the work is too large to keep, and what to do')
    ok(bad(errs) == [], 'full: no console errors: %s' % bad(errs)[:3])

with session(W, 1000) as (pg, errs):
    # ---- a store holding something that is not this app’s work
    pg.add_init_script("if (!sessionStorage.getItem('seeded')) { localStorage.setItem('%s', '{not json'); sessionStorage.setItem('seeded', '1'); }" % STORE)
    pg.reload(); pg.wait_for_timeout(1500)
    ok(stored(pg) is None, 'garbage: unreadable saved work is removed')
    open_sample(pg)
    ok('Picked up' not in keep(pg).inner_text(), 'garbage: and the page starts clean')
    ok(bad(errs) == [], 'garbage: no console errors: %s' % bad(errs)[:3])
    # a good file whose record was changed
    pg.evaluate("([k, v]) => localStorage.setItem(k, v)", [STORE, json.dumps(t)])
    pg.reload(); pg.wait_for_timeout(1500)
    ok(stored(pg) is None, 'tampered: saved work whose record was changed is removed, not used')
    open_sample(pg)
    ok('could not be used and was removed' in keep(pg).inner_text() and 'has been changed' in keep(pg).inner_text(), 'tampered: Home says why (%s)' % re.sub(r'\s+', ' ', keep(pg).inner_text())[-200:])
    ok(waiting(pg) == h1_fresh, 'tampered: nothing from it was used')

with session(W, 1000) as (pg, errs):
    # ---- two tabs of one browser
    open_sample(pg); record(pg, 'CL-001'); pg.wait_for_timeout(700)
    pg2 = pg.context.new_page(); errs2 = []
    pg2.on('pageerror', lambda e: errs2.append(str(e)))
    pg2.goto('http://127.0.0.1:8791/Main.dc.html'); pg2.wait_for_timeout(1800)
    ok('Picked up where you left off' in keep(pg2).inner_text(), 'two tabs: a second tab picks up the same work')
    record(pg2, 'CL-002'); pg2.wait_for_timeout(700)
    ok(len(stored(pg2)['state']['dec']) == 2, 'two tabs: the second tab saved its own decision (%d decisions kept)' % len(stored(pg2)['state']['dec']))
    pg.bring_to_front(); pg.wait_for_timeout(500)
    home(pg)
    kt = keep(pg).inner_text()
    ok('Another tab changed this project' in kt and 'Which tab’s work should stand?' in kt, 'two tabs: the first tab is told, and asked whose work stands')
    # a change made now is not written over the other tab's work
    before = json.dumps(stored(pg)['state']['dec'], sort_keys=True)
    open_cluster(pg, 'CL-003')
    pg.wait_for_timeout(700)
    ok(json.dumps(stored(pg)['state']['dec'], sort_keys=True) == before, 'two tabs: this tab does not save while the question is open')
    home(pg)
    noscroll(pg, 'Home with the two-tabs question open')
    keep(pg).get_by_role('button', name=re.compile(r'^Use the other tab')).click(); pg.wait_for_timeout(600)
    ok('Now showing the work the other tab saved' in status(pg) and 'Another tab changed' not in keep(pg).inner_text(), 'two tabs: taking the other tab’s work shows it and clears the question')
    record(pg, 'CL-003'); pg.wait_for_timeout(700)
    ok(len(stored(pg)['state']['dec']) == 3, 'two tabs: after that this tab saves again (%d decisions kept)' % len(stored(pg)['state']['dec']))
    pg2.bring_to_front(); pg2.wait_for_timeout(500); home(pg2)
    ok('Another tab changed this project' in keep(pg2).inner_text(), 'two tabs: and now the second tab is told')
    keep(pg2).get_by_role('button', name=re.compile(r'^Keep this tab')).click(); pg2.wait_for_timeout(700)
    ok(len(stored(pg2)['state']['dec']) == 2 and 'saved over' in status(pg2), 'two tabs: keeping this tab’s work overwrites the other’s, and says so (%d decisions kept)' % len(stored(pg2)['state']['dec']))
    ok(errs2 == [] and bad(errs) == [], 'two tabs: no errors: %s %s' % (errs2[:2], bad(errs)[:2]))

print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
