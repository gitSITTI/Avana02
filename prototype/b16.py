"""One requirement at a time (All requirements): put another beside it, decide it (keep, reword, drop, not a requirement, ask the owner),
sign it off, and see it counted on Results, the V and the ledger.
Run: python3 b16.py 1440, python3 b16.py 900 and python3 b16.py 390."""
import re, sys
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
def who(pg, name):
    pg.get_by_role('button', name=re.compile(r'^' + name + r'\b')).first.click(); pg.wait_for_timeout(300)
def num(s): return int(re.sub(r'[^0-9]', '', s))
def dest(t, label):
    m = re.search(re.escape(label) + r'\n[^\n]*\n([\d,]+)\n', t)
    return num(m.group(1)) if m else -1
def after(pg):
    t = body(pg)
    m = re.search(r'After your decisions so far\s*\n?\s*([\d,]+)', t)
    return num(m.group(1)) if m else -1
def panel(pg): return pg.locator('aside[aria-label="One requirement"]')
def kind(pg, name): return panel(pg).get_by_role('button', name=name).first
def pick_row(pg, i):
    rows = pg.locator('button[aria-pressed]:has(span:text-matches("^REQ-"))')
    rows.nth(i).click(); pg.wait_for_timeout(250)
def picked_id(pg): return panel(pg).locator('#xp-h span').first.inner_text().strip()
def go_alone(pg):
    nav(pg, 'All requirements')
    pg.get_by_role('button', name=re.compile(r'^Alone\b')).first.click(); pg.wait_for_timeout(250)
def decide(pg, name, reason=None, note=None, text=None, q=None):
    kind(pg, name).click(); pg.wait_for_timeout(150)
    if reason: pg.select_option('#xp-reason', reason); pg.wait_for_timeout(120)
    if text is not None: pg.fill('#xp-text', text); pg.locator('#xp-text').blur(); pg.wait_for_timeout(120)
    if q is not None: pg.fill('#xp-q', q); pg.locator('#xp-q').blur(); pg.wait_for_timeout(120)
    if note is not None: pg.fill('#xp-note', note); pg.locator('#xp-note').blur(); pg.wait_for_timeout(120)
def pick_id(pg, rid):
    nav(pg, 'All requirements')
    pg.get_by_role('button', name=re.compile(r'^All\b')).first.click(); pg.wait_for_timeout(200)
    pg.locator('.xmap span[title^="' + rid + '"]').first.click(); pg.wait_for_timeout(250)
def record_btn(pg): return panel(pg).get_by_role('button', name=re.compile(r'^(Record this decision|Record the new decision|Send the question)$')).first
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with session(W, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
    nav(pg, 'Results and grade')
    t0 = body(pg); asis0 = dest(t0, 'Stays as it is'); after0 = after(pg); esc0 = dest(t0, 'Waiting for the owners')
    ok(asis0 > 100 and after0 > 100, 'start: Results reads %d staying as they are and %d after decisions' % (asis0, after0))
    ok(all(dest(t0, l) == 0 for l in ['Kept after a person looked', 'Kept with new wording', 'Dropped', 'Not a requirement']), 'start: the four single-decision destinations are on the page and at zero')
    nav(pg, 'The V'); vt0 = body(pg)

    # ---- the panel
    go_alone(pg)
    pick_row(pg, 0)
    p = panel(pg)
    first_id = picked_id(pg)
    ok(re.match(r'REQ-[A-Z]+-\d{4}$', first_id) is not None, 'panel: a requirement picked from the list opens (%s)' % first_id)
    ok(p.locator('h3', has_text='Compare with another requirement').count() == 1 and p.locator('h3', has_text='Decide this requirement').count() == 1, 'panel: it has a Compare section and a Decide section')
    near = p.locator('button[aria-label^="Put REQ-"]')
    ok(near.count() == 5, 'compare: five nearest requirements are offered (%d)' % near.count())
    ok(all(near.nth(i).evaluate('e => e.getBoundingClientRect().height') >= 44 for i in range(5)), 'compare: each suggestion is at least 44 px tall')
    ok('Text match' in near.nth(0).inner_text() and 'keyword overlap' in near.nth(0).inner_text(), 'compare: each suggestion shows its two scores in words')
    kinds = ['Keep as written', 'Keep, with new wording', 'Drop it', 'Not a requirement', 'Ask the owner']
    for k in kinds:
        ok(kind(pg, k).count() == 1 and kind(pg, k).is_enabled() and kind(pg, k).evaluate('e => e.getBoundingClientRect().height') >= 44, 'decide: "%s" is a button at least 44 px tall' % k)
    ok(record_btn(pg).count() == 0 or record_btn(pg).is_disabled(), 'decide: nothing can be recorded before a choice')
    ok('Choose what to do with this requirement.' in p.inner_text(), 'decide: the form says what to do first')
    noscroll(pg, 'the panel')

    # ---- compare
    near.nth(0).click(); pg.wait_for_timeout(250)
    near_id = near.nth(0).get_attribute('aria-label').split(' ')[1]
    grp = p.locator('[role="group"][aria-label$="beside ' + first_id + '"]')
    ok(grp.count() == 1 and near_id in grp.inner_text(), 'compare: choosing one puts it beside this one (%s)' % near_id)
    gt = grp.inner_text()
    ok('This one' in gt and 'Beside it' in gt and all(f in gt for f in ['Allocation', 'Owner', 'Level', 'Verification', 'Verification items', 'Where it is']), 'compare: both wordings and six facts are shown')
    ok(re.search(r'Text match 0\.\d\d', gt) and re.search(r'Keyword overlap 0\.\d\d', gt), 'compare: the two scores are written out')
    ok(near.nth(0).get_attribute('aria-pressed') == 'true', 'compare: the chosen suggestion is marked pressed')
    grp.get_by_role('button', name='Look at ' + near_id + ' instead').click(); pg.wait_for_timeout(250)
    ok(picked_id(pg) == near_id and first_id in panel(pg).locator('[role="group"][aria-label$="beside ' + near_id + '"]').inner_text(), 'compare: the two can be swapped')
    panel(pg).get_by_role('button', name='Stop comparing').click(); pg.wait_for_timeout(200)
    ok(panel(pg).locator('[role="group"][aria-label*="beside"]').count() == 0, 'compare: nothing is beside it after stopping')
    # back to the first requirement, then choose the second one from the list
    pick_row(pg, 0)
    panel(pg).get_by_role('button', name='Choose another from the list').click(); pg.wait_for_timeout(200)
    ok(panel(pg).get_by_role('button', name='Cancel choosing').get_attribute('aria-pressed') == 'true' and 'Click a square on the map' in panel(pg).inner_text(), 'compare: choosing another from the list says how')
    cur = picked_id(pg)
    rows = pg.locator('button[aria-pressed]:has(span:text-matches("^REQ-"))')
    second_id = rows.nth(3).locator('span').first.inner_text().strip()
    rows.nth(3).click(); pg.wait_for_timeout(250)
    ok(picked_id(pg) == cur and second_id in panel(pg).locator('[role="group"][aria-label*="beside"]').first.inner_text(), 'compare: a click on the list puts it beside the first without losing the first (%s beside %s)' % (second_id, cur))
    ok(panel(pg).get_by_role('button', name='Choose another from the list').get_attribute('aria-pressed') == 'false', 'compare: choosing switches itself off afterwards')
    panel(pg).get_by_role('button', name='Stop comparing').click(); pg.wait_for_timeout(200)

    # ---- keep it
    decide(pg, 'Keep as written')
    ok('Choose the reason.' in panel(pg).inner_text() and record_btn(pg).is_disabled(), 'keep: it asks for a reason before it can be recorded')
    pg.select_option('#xp-reason', 'S-OK'); pg.wait_for_timeout(150)
    ok(record_btn(pg).is_enabled(), 'keep: with a reason it can be recorded')
    ok('Needs sign-off from: Systems engineer' in panel(pg).inner_text(), 'keep: it says who has to sign')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    pt = panel(pg).inner_text()
    ok('On record' in pt and 'Decided' in pt and 'Keep as written' in pt and 'Sam Okafor' in pt, 'keep: the decision is on record with who made it')
    ok(pg.evaluate("document.activeElement && document.activeElement.id") == 'xp-h', 'keep: after recording, focus goes to the requirement heading')
    ok('You recorded this decision, so a colleague signs it' in pt and panel(pg).get_by_role('button', name=re.compile('^Sign off as')).count() == 0, 'keep: the person who decided cannot sign their own decision')
    ok('collecting sign-offs' in panel(pg).locator('#xp-h').inner_text(), 'keep: the heading shows it as decided and collecting sign-offs')
    who(pg, 'Morgan')
    ok(panel(pg).get_by_role('button', name=re.compile('^Sign off as')).count() == 1, 'sign: a colleague with the lens is offered the sign-off')
    panel(pg).get_by_role('button', name=re.compile('^Sign off as')).click(); pg.wait_for_timeout(300)
    ok('Approved' in panel(pg).inner_text() and 'Signed by Morgan Hale' in panel(pg).inner_text(), 'sign: with every lens the policy asks for, it is approved')
    ok('Approved' in panel(pg).locator('#xp-h').inner_text(), 'sign: the heading shows approved')
    panel(pg).get_by_role('button', name='Withdraw my sign-off').click(); pg.wait_for_timeout(250)
    ok('Approved' not in panel(pg).inner_text().split('On record')[1][:60], 'sign: a sign-off can be withdrawn')
    who(pg, 'Sam')

    # ---- results move
    nav(pg, 'Results and grade')
    t1 = body(pg)
    ok(dest(t1, 'Kept after a person looked') == 1 and dest(t1, 'Stays as it is') == asis0 - 1, 'results: the kept requirement leaves "stays as it is" for "kept after a person looked" (%d, %d)' % (dest(t1, 'Stays as it is'), asis0))
    ok(after(pg) == after0, 'results: keeping one does not change the count after decisions (%d)' % after(pg))
    ok('All 1,248 originals, each in exactly one place.' in t1, 'results: every original is still in exactly one place')
    ok(sum(dest(t1, l) for l in ['Stays as it is', 'Kept as the surviving wording', 'Merged into another', 'Stays separate', 'Kept and linked', 'Waiting for the owners', 'Superseded', 'Kept after a person looked', 'Kept with new wording', 'Dropped', 'Not a requirement', 'Not decided yet']) == 1248, 'results: the twelve destinations add up to 1,248')
    noscroll(pg, 'results with a single decision')

    # ---- drop it, covered by another
    go_alone(pg)
    pick_row(pg, 1)
    id2 = picked_id(pg)
    decide(pg, 'Drop it', reason='S-COV', note='Covered by the other requirement.')
    ok('beside this one' in panel(pg).inner_text() and record_btn(pg).is_disabled(), 'drop: "covered by another" needs the other put beside it')
    panel(pg).locator('button[aria-label^="Put REQ-"]').nth(0).click(); pg.wait_for_timeout(250)
    cover_id = panel(pg).locator('button[aria-label^="Put REQ-"]').nth(0).get_attribute('aria-label').split(' ')[1]
    if pg.locator('#xp-cr').count():   # a baselined requirement also needs the number of the change request that covers it
        pg.fill('#xp-cr', 'CR-2041'); pg.wait_for_timeout(200)
    ok('Covered by ' + cover_id in panel(pg).inner_text() and record_btn(pg).is_enabled(), 'drop: with the other beside it the drop can be recorded')
    ok('Needs sign-off from' in panel(pg).inner_text() and 'Owners' in panel(pg).inner_text(), 'drop: it says the owners have to sign')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    ok('Covered by' in panel(pg).inner_text() and cover_id in panel(pg).inner_text() and 'Owners' in panel(pg).inner_text(), 'drop: the covering requirement and the owners’ sign-off are on record')
    nav(pg, 'Results and grade'); t2 = body(pg)
    ok(dest(t2, 'Dropped') == 1 and after(pg) == after0 - 1, 'results: a drop takes one off the count after decisions (%d, was %d)' % (after(pg), after0))
    m0 = re.search(r'(\d+) of (\d+) merges are clean', t0); m2 = re.search(r'(\d+) of (\d+) merges and removals are clean', t2)
    ok(m0 and m2 and m2.group(1) == m0.group(1) and int(m2.group(2)) == int(m0.group(2)) + 1, 'results: an unsigned drop is one more change that could loosen, and it is not clean (%s -> %s)' % (m0 and m0.group(0), m2 and m2.group(0)))
    ok('Settle 2 changes that loosen a requirement' in t2, 'results: the list of things that would raise the grade now says 2 changes loosen')
    ok('merges and removals' in t2 or 'No merge or removal' in t2, 'results: the check names removals as well as merges')
    nav(pg, 'The V'); vt = body(pg)
    ok('dropped or not a requirement' in vt, 'the V: it says how many were dropped at that level')
    vm = re.search(r'All levels\t([\d,]+)\t([\d,]+)', vt)
    ok(vm and num(vm.group(1)) == 1248 and num(vm.group(2)) == after0 - 1, 'the V: the whole-V row says 1,248 now and %d after the drop (%s)' % (after0 - 1, vm and vm.groups()))
    noscroll(pg, 'the V with a drop')

    # ---- new wording
    go_alone(pg)
    pick_row(pg, 2)
    id3 = picked_id(pg)
    decide(pg, 'Keep, with new wording')
    ta = pg.locator('#xp-text')
    ok(ta.count() == 1 and ta.input_value() == panel(pg).locator('#xp-text').input_value(), 'reword: the wording box starts with the old wording')
    ok('same wording' in panel(pg).inner_text() and record_btn(pg).is_disabled(), 'reword: the same wording is blocked')
    old = ta.input_value()
    pg.fill('#xp-text', re.sub(r'\bshall\b', 'shall promptly', old, count=1)); pg.locator('#xp-text').blur(); pg.wait_for_timeout(200)
    ok('Numbers preserved' in panel(pg).inner_text() and 'Shall / should / will' in panel(pg).inner_text(), 'reword: the checks on numbers, units, shall, not and conditions are listed')
    pg.select_option('#xp-reason', 'S-CLR'); pg.wait_for_timeout(120)
    ok('Write why' in panel(pg).inner_text() and record_btn(pg).is_disabled(), 'reword: it asks why before it can be recorded')
    pg.fill('#xp-note', 'Clearer about timing, same obligation.'); pg.locator('#xp-note').blur(); pg.wait_for_timeout(150)
    ok(record_btn(pg).is_enabled() and 'New user' in panel(pg).inner_text(), 'reword: with a note it can be recorded and says the new-user lens has to sign')
    pg.fill('#xp-text', re.sub(r'\bshall\b', 'should', old, count=1)); pg.locator('#xp-text').blur(); pg.wait_for_timeout(200)
    ok('Needs the owners' in panel(pg).inner_text(), 'reword: shall to should is allowed but flagged for the owners')
    pg.fill('#xp-text', re.sub(r'\bshall\b', 'shall promptly', old, count=1)); pg.locator('#xp-text').blur(); pg.wait_for_timeout(150)
    record_btn(pg).click(); pg.wait_for_timeout(300)
    ok('New wording' in panel(pg).inner_text() and 'shall promptly' in panel(pg).inner_text(), 'reword: the new wording is on record')
    # the New user lens needs to say it back
    who(pg, 'Casey')
    ok('Say it back in your own words' in panel(pg).inner_text() and panel(pg).get_by_role('button', name=re.compile('^Sign off as')).is_disabled(), 'sign: the new-user lens has to explain it back before signing')
    pg.fill('#xp-nu', 'It must answer promptly, within the time given.'); pg.locator('#xp-nu').blur(); pg.wait_for_timeout(150)
    ok(panel(pg).get_by_role('button', name=re.compile('^Sign off as')).is_enabled(), 'sign: after the explanation the sign-off is open')
    who(pg, 'Sam')
    nav(pg, 'Results and grade'); t3 = body(pg)
    ok(dest(t3, 'Kept with new wording') == 1 and after(pg) == after0 - 1, 'results: new wording keeps the requirement (count unchanged by it)')

    # ---- not a requirement and ask the owner
    go_alone(pg)
    pick_row(pg, 3); id4 = picked_id(pg)
    decide(pg, 'Not a requirement', reason='S-DEF', note='This is a definition of a term.')
    record_btn(pg).click(); pg.wait_for_timeout(250)
    pick_row(pg, 4); id5 = picked_id(pg)
    decide(pg, 'Ask the owner', q='Is the time limit still the one in the ICD?')
    ok('Sent to the owner' in panel(pg).inner_text() and 'Choose the reason' not in panel(pg).inner_text(), 'ask: it needs a question and no reason, and says who it goes to')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    ok('Waiting for the owner' in panel(pg).inner_text() and 'Is the time limit still' in panel(pg).inner_text(), 'ask: the question is on record and it is waiting')
    nav(pg, 'Results and grade'); t4 = body(pg)
    ok(dest(t4, 'Not a requirement') == 1 and dest(t4, 'Waiting for the owners') == esc0 + 1 and after(pg) == after0 - 2, 'results: not-a-requirement leaves the set, ask leaves it as it is (after %d, was %d)' % (after(pg), after0))
    ok(sum(dest(t4, l) for l in ['Stays as it is', 'Kept as the surviving wording', 'Merged into another', 'Stays separate', 'Kept and linked', 'Waiting for the owners', 'Superseded', 'Kept after a person looked', 'Kept with new wording', 'Dropped', 'Not a requirement', 'Not decided yet']) == 1248, 'results: still 1,248 across the twelve places')
    # the owner answers
    pick_id(pg, id5)
    ok(picked_id(pg) == id5, 'ask: the same requirement is back (%s)' % id5)
    panel(pg).get_by_role('button', name='Record the owner’s answer').click(); pg.wait_for_timeout(250)
    decide(pg, 'Keep as written', reason='S-OK', note='The owner confirmed the limit in the ICD.')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    ok('Earlier question' in panel(pg).inner_text() and 'Is the time limit still' in panel(pg).inner_text(), 'ask: the owner’s answer becomes a decision that keeps the question')

    # ---- the ledger, the V and the map
    nav(pg, 'Decisions and audit')
    lt = body(pg)
    ok(id2 in lt or id3 in lt or id4 in lt, 'ledger: single decisions are listed with the clusters')
    pg.fill('#l-filter', id3); pg.locator('#l-filter').blur(); pg.wait_for_timeout(250)
    ok(pg.get_by_role('button', name='Open requirement ' + id3).count() == 1, 'ledger: a single decision opens the requirement, not a cluster')
    pg.get_by_role('button', name='Open requirement ' + id3).click(); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1').strip() == 'All requirements' and picked_id(pg) == id3, 'ledger: opening it lands on its panel (%s)' % picked_id(pg))
    nav(pg, 'The V'); vt2 = body(pg)
    ok('read again against new wording' in vt2, 'the V: the reworded requirement’s items are to be read again')
    nav(pg, 'Results and grade')
    ok(after(pg) == after0 - 2, 'results: after the owner answered and the others stood, the count is %d' % after(pg))

    # ---- withdraw
    pick_id(pg, id2)
    ok(picked_id(pg) == id2, 'withdraw: the dropped requirement is picked from the map (%s)' % id2)
    panel(pg).get_by_role('button', name='Withdraw the decision').click(); pg.wait_for_timeout(250)
    ok('On record' not in panel(pg).inner_text() and panel(pg).get_by_role('button', name='Keep as written').count() == 1, 'withdraw: it goes back to undecided')
    nav(pg, 'Results and grade')
    ok(dest(body(pg), 'Dropped') == 0 and after(pg) == after0 - 1, 'withdraw: the drop no longer counts (after %d)' % after(pg))

    # ---- keyboard
    go_alone(pg); pick_row(pg, 6)
    kind(pg, 'Drop it').focus(); pg.keyboard.press('Space'); pg.wait_for_timeout(150)
    ok(kind(pg, 'Drop it').get_attribute('aria-pressed') == 'true', 'keyboard: a choice can be made with the space bar')
    labels = pg.evaluate("""() => Array.from(document.querySelectorAll('aside[aria-label="One requirement"] textarea, aside[aria-label="One requirement"] select')).map(e => !!(e.id && document.querySelector('label[for="' + e.id + '"]')))""")
    ok(len(labels) >= 2 and all(labels), 'keyboard: every box and menu in the panel has a label (%s)' % labels)
    unnamed = pg.evaluate("""() => Array.from(document.querySelectorAll('aside[aria-label="One requirement"] button')).filter(b => !(b.innerText || '').trim() && !b.getAttribute('aria-label')).length""")
    ok(unnamed == 0, 'keyboard: every button in the panel has a name')

    # ---- who can decide
    who(pg, 'Lee')
    ok(panel(pg).get_by_role('button', name='Keep as written').count() == 0 and 'not decide them' in panel(pg).inner_text(), 'observer: Lee can look and compare but not decide')
    ok(panel(pg).locator('button[aria-label^="Put REQ-"]').count() == 5, 'observer: Lee can still compare')
    who(pg, 'Sam')

    # ---- a requirement inside a cluster
    nav(pg, 'All requirements')
    pg.get_by_role('button', name=re.compile(r'^Needs a decision')).first.click(); pg.wait_for_timeout(250)
    done = False
    for i in range(8):
        pick_row(pg, i)
        peel = panel(pg).get_by_role('button', name=re.compile(r'^Take it out of CL-'))
        if i == 0:
            ok('decided there with the others' in panel(pg).inner_text() and panel(pg).get_by_role('button', name='Keep as written').count() == 0, 'cluster member: it is decided with its cluster, so no decision form is offered')
        if peel.count() and peel.is_enabled():
            peel.click(); pg.wait_for_timeout(300)
            ok(panel(pg).get_by_role('button', name='Keep as written').count() == 1, 'cluster member: once taken out of its cluster it can be decided on its own')
            done = True; break
        elif i == 0:
            ok(panel(pg).locator('text=/only two|already has a decision/').count() >= 1, 'cluster member: when it cannot be taken out, the panel says why')
    ok(done, 'cluster member: one of the first eight could be taken out of its cluster')
    noscroll(pg, 'a requirement taken out of its cluster')
    ok(bad(errs) == [], 'no console errors: %s' % bad(errs)[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
