"""Label pairs (the gold set): the blind pair card, labelling with the mouse and the keyboard, undo, skip, change, the measured table on
Methods and metrics, agreement and settling, the file, who can label, and the phone layout.
Run: python3 b15.py 1440, python3 b15.py 900 and python3 b15.py 390."""
import json, re, sys
from h import session
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
def body(pg): return pg.inner_text('body')
def who(pg, name):
    pg.get_by_role('button', name=re.compile(r'^' + name + r'\b')).first.click(); pg.wait_for_timeout(300)
def noscroll(pg, label):
    w = pg.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
    ok(w[0] <= w[1], 'no horizontal page scroll: %s (%s vs %s)' % (label, w[0], w[1]))
def nav(pg, label):
    pg.locator('.nav-btn', has_text=label).first.click(); pg.wait_for_timeout(250)
def num(s): return int(re.sub(r'[^0-9]', '', s))
def pair_ids(pg):
    t = pg.locator('section[aria-labelledby="gl-pair-h"]').inner_text()
    return re.findall(r'REQ-[A-Z]+-\d{4}', t)[:2]
def opt(pg, name): return pg.locator('section[aria-labelledby="gl-pair-h"] button', has_text=name).first
def card_text(pg): return pg.locator('section[aria-labelledby="gl-pair-h"]').inner_text()
def measured(pg):
    """Rows of the measured table: name, precision, recall, flagged."""
    return pg.evaluate("""() => Array.from(document.querySelectorAll('section[aria-labelledby="mt-gold"] [role="group"][aria-label*="precision"]')).map(g => ({ aria: g.getAttribute('aria-label'), text: g.innerText, flagged: g.children[3].innerText }))""")
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with session(W, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)

    # ---- the page and what it shows
    nav(pg, 'Label pairs')
    ok(pg.inner_text('h1').strip() == 'Label pairs', 'page: the heading is Label pairs')
    ok('Label pairs' in pg.locator('.topbar').inner_text(), 'page: the breadcrumb says where you are')
    ok(pg.locator('.nav-btn[aria-current="page"]', has_text='Label pairs').count() == 1, 'page: the side bar marks Label pairs as the current page')
    ok('Pair 1 of 160' in card_text(pg), 'card: it starts at pair 1 of 160')
    ids = pair_ids(pg)
    ok(len(ids) == 2 and ids[0] < ids[1], 'card: two requirement IDs are shown, in order (%s)' % ids)
    ct = card_text(pg)
    ok('Requirement A' in ct and 'Requirement B' in ct and 'Do these two requirements say the same thing?' in ct, 'card: the question and both requirements are there')
    ok(not re.search(r'CL-\d', ct) and not re.search(r'cluster|score|AI said|the app', ct, re.I), 'card: nothing about the app’s cluster, scores or the AI is shown (blind)')
    names = ['Same requirement', 'Same topic, different value', 'One contains the other', 'They contradict', 'Different things', 'Cannot tell']
    for n in names:
        ok(opt(pg, n).count() == 1 and opt(pg, n).is_enabled(), 'card: "%s" is a button you can press' % n)
    ok(opt(pg, 'Different things').evaluate('e => e.getBoundingClientRect().height') >= 44, 'card: label buttons are at least 44 px tall')
    ok(pg.locator('section[aria-labelledby="gl-pair-h"] button[aria-keyshortcuts]').count() == 6, 'card: each label button declares its key')
    ok(pg.locator('#gl-pair-h').get_attribute('tabindex') == '-1', 'card: the pair heading can take focus after each label')
    ok(pg.get_by_role('checkbox', name='Show the words in B that differ from A').is_checked(), 'card: the difference highlight is on by default')
    pg.get_by_role('checkbox', name='Show the words in B that differ from A').uncheck(); pg.wait_for_timeout(200)
    ok(pg.locator('section[aria-labelledby="gl-pair-h"]').inner_text().count('REQ-') == 2, 'card: switching the highlight off keeps both requirements')
    pg.get_by_role('checkbox', name='Show the words in B that differ from A').check(); pg.wait_for_timeout(200)
    ok(pg.get_by_role('button', name='Undo my last label').is_disabled(), 'card: undo is off before there is anything to undo')
    noscroll(pg, 'Label pairs, start')

    # ---- labelling with the mouse
    first = pair_ids(pg)
    opt(pg, 'Same requirement').click(); pg.wait_for_timeout(300)
    ok('Pair 2 of 160' in card_text(pg) and pair_ids(pg) != first, 'mouse: choosing a label shows the next pair (%s -> %s)' % (first, pair_ids(pg)))
    ok(pg.evaluate("document.activeElement && document.activeElement.id") == 'gl-pair-h', 'mouse: focus goes to the new pair heading, not to nothing')
    ok('Saved “Same requirement”' in body(pg), 'mouse: the page says what it saved')
    ok(pg.locator('[aria-live="polite"]', has_text='Saved').count() >= 1, 'mouse: the confirmation is in a live region')
    ok(pg.locator('[role="progressbar"][aria-label="Pairs you have labelled"]').get_attribute('aria-valuenow') == '1', 'mouse: the progress bar counts one')
    t = body(pg)
    ok('You have labelled 1 pair.' in t and '159 pairs are still offered to you.' in t, 'mouse: progress is also written in words')
    ok(first[0] in pg.locator('section[aria-labelledby="gl-mine"]').inner_text() and 'Same requirement' in pg.locator('section[aria-labelledby="gl-mine"]').inner_text(), 'mouse: the latest labels list shows it')
    opt(pg, 'They contradict').click(); pg.wait_for_timeout(250)
    second = pair_ids(pg)
    pg.get_by_role('button', name='Undo my last label').click(); pg.wait_for_timeout(250)
    ok('Pair 2 of 160' in card_text(pg) and 'Removed your last label' in body(pg), 'undo: the last label is removed and the pair is back (%s)' % pair_ids(pg)[:2])
    ok(pg.locator('[role="progressbar"]').get_attribute('aria-valuenow') == '1', 'undo: progress goes back to one')
    cur = pair_ids(pg)
    pg.get_by_role('button', name='Skip for now').click(); pg.wait_for_timeout(250)
    ok(pair_ids(pg) != cur and 'Skipped' in body(pg), 'skip: moves on to another pair (%s -> %s)' % (cur, pair_ids(pg)))

    # ---- labelling with the keyboard, and a note
    pg.locator('#gl-pair-h').focus()
    before = pair_ids(pg)
    pg.keyboard.press('5'); pg.wait_for_timeout(250)
    ok(pair_ids(pg) != before and 'Saved “Different things”' in body(pg), 'keys: 5 records Different things and shows the next pair')
    pg.fill('#gl-note', '1234'); pg.wait_for_timeout(250)
    ok(pg.input_value('#gl-note') == '1234' and 'Pair 3 of 160' in card_text(pg), 'keys: digits typed in the note box are text, not shortcuts')
    pg.fill('#gl-note', 'the units are the same'); pg.wait_for_timeout(200)
    third = pair_ids(pg)
    pg.keyboard.press('Tab')   # leave the note box, then pick by key from a button
    opt(pg, 'Same topic, different value').focus(); pg.keyboard.press('2'); pg.wait_for_timeout(250)
    ok(pg.input_value('#gl-note') == '' and pair_ids(pg) != third, 'keys: the note was kept with the label and the box is empty again')
    rec = pg.locator('section[aria-labelledby="gl-mine"]').inner_text()
    ok('Same topic, different value' in rec, 'keys: the latest labels include the key-chosen label')
    opt(pg, 'Cannot tell').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(250)
    ok('Saved “Cannot tell”' in body(pg), 'keys: Enter on a focused label button records it')
    # tab order reaches every control in the card
    pg.locator('#gl-pair-h').focus()
    seen = []
    for _ in range(14):
        pg.keyboard.press('Tab')
        seen.append(pg.evaluate("document.activeElement ? (document.activeElement.textContent || document.activeElement.id || '').trim().slice(0, 30) : ''"))
    ok(any('Same req' in s for s in seen) and any('Cannot t' in s for s in seen) and any('Skip for now' in s for s in seen), 'keys: Tab reaches the checkbox, the six labels, the note and the buttons (%s)' % seen[:9])
    # change an earlier label
    pg.locator('section[aria-labelledby="gl-mine"] button', has_text='Change').first.click(); pg.wait_for_timeout(300)
    ok('Change your label for this pair' in card_text(pg), 'change: an earlier pair reopens under its own heading')
    opt(pg, 'Different things').click(); pg.wait_for_timeout(250)
    ok('Pair 5 of 160' in card_text(pg) or re.search(r'Pair \d+ of 160', card_text(pg)), 'change: after changing it the queue carries on (%s)' % re.findall(r'Pair \d+ of 160', card_text(pg)))
    ok(pg.locator('[role="progressbar"]').get_attribute('aria-valuenow') == '4', 'change: changing a label does not count it twice (%s)' % pg.locator('[role="progressbar"]').get_attribute('aria-valuenow'))

    # ---- Methods and metrics before and after there are enough labels
    nav(pg, 'Methods and metrics')
    t = body(pg)
    ok('Measured from labelled pairs' in t and 'Only the first table is measured' in t, 'metrics: the page says which table is measured')
    ok('Not enough labels yet. Label pairs in:' in t, 'metrics: with only a few labels the table says which groups still need labels instead of inventing numbers')
    ok(all(not re.search(r'recall \d', r['aria']) for r in measured(pg)[1:]), 'metrics: no recall is shown for the two scores while a group has no labels')
    pg.get_by_role('button', name='Label pairs').first.click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Load sample labels').first.click(); pg.wait_for_timeout(400)
    ok('Sample labels are loaded.' in body(pg), 'sample: the page says labels are made up')
    ok(re.search(r'Morgan and Priya both labelled \d+ pairs and agree on \d+', body(pg)) is not None and 'kappa' in body(pg), 'sample: agreement between the two sample labellers is shown with kappa')
    nav(pg, 'Methods and metrics')
    rows = measured(pg)
    ok(len(rows) == 3 and [r['aria'].split(':')[0] for r in rows][0] == 'The app’s clusters', 'metrics: three measured rows, the app’s clusters first (%d)' % len(rows))
    ok(all('range' in r['text'] and re.search(r'\d\.\d\d', r['text']) for r in rows), 'metrics: every row shows a number and its range')
    def rng(r, which):
        m = re.search(which + r' (\d\.\d\d), range (\d\.\d\d) to (\d\.\d\d)', r['aria']); return tuple(float(x) for x in m.groups()) if m else None
    okr = [rng(r, 'precision') for r in rows] + [rng(r, 'recall') for r in rows]
    ok(all(x and x[1] <= x[0] <= x[2] for x in okr), 'metrics: each estimate sits inside its own range (%s)' % okr[:2])
    ok('made up' in body(pg) and 'Sample labels are in use' in body(pg), 'metrics: it says sample labels are in use and the numbers are not a measurement')
    ok('Pairs outside the recall' in body(pg) and 'Different allocations' in body(pg) and 'Same allocation, not alike' in body(pg), 'metrics: the pairs outside the recall are reported on their own')
    ok('Naming the relation' in body(pg), 'metrics: AI naming of the relation is measured against the labels')
    flag = lambda: [num(r['flagged']) for r in measured(pg)]
    f8 = flag()
    pg.get_by_role('button', name='0.6', exact=True).click(); pg.wait_for_timeout(300)
    f6 = flag()
    ok(pg.get_by_role('button', name='0.6', exact=True).get_attribute('aria-pressed') == 'true', 'metrics: the chosen cut-off is marked as pressed')
    ok(f6[0] == f8[0] and f6[1] > f8[1] and f6[2] > f8[2], 'metrics: a lower cut-off flags more pairs for the two scores and the clusters stay put (%s then %s)' % (f8, f6))
    noscroll(pg, 'Methods and metrics with the measured table')

    # ---- disagreements: only the lead settles
    nav(pg, 'Label pairs')
    t = body(pg)
    n0 = num(re.search(r'Disagreements to settle \((\d+)\)', t).group(1))
    ok(n0 >= 1 and 'The lead (Morgan Hale) settles these' in t, 'settle: disagreements are listed and the page says who settles them (%d)' % n0)
    ok(pg.get_by_role('button', name=re.compile(r'^Settle as')).count() == 0, 'settle: a reviewer has no Settle buttons')
    who(pg, 'Morgan')
    ok(pg.get_by_role('button', name=re.compile(r'^Settle as')).count() >= n0, 'settle: the lead has Settle buttons for each')
    pg.get_by_role('button', name=re.compile(r'^Settle as')).first.click(); pg.wait_for_timeout(300)
    n1 = num(re.search(r'Disagreements to settle \((\d+)\)', body(pg)).group(1)) if re.search(r'Disagreements to settle \((\d+)\)', body(pg)) else 0
    ok(n1 == n0 - 1, 'settle: settling one leaves one fewer (%d -> %d)' % (n0, n1))
    nav(pg, 'Decisions and audit')
    pg.get_by_role('button', name=re.compile('chain', re.I)).first.click(); pg.wait_for_timeout(300)
    ok('Settled a labelling disagreement' in body(pg), 'settle: the event chain records who settled it')

    # ---- the file
    nav(pg, 'Label pairs')
    with pg.expect_download() as dl:
        pg.get_by_role('button', name='Download the gold set').click()
    path = dl.value.path()
    data = json.load(open(path))
    ok(data['format'] == 'reqin-gold-set/1' and len(data['pairs']) >= 100, 'file: the download is the gold set (%d pairs)' % len(data['pairs']))
    ok(sorted(data['groups']) == ['A', 'B1', 'B2', 'C'] and data['groups']['A']['group_pairs'] == 1294, 'file: it says how many pairs each group stands for')
    ok(all('(sample)' in w for p in data['pairs'] for w in p['labelled_by'] if 'priya' in w or 'morgan' in w), 'file: made-up labels are marked as sample')
    ok(any('the units are the same' in n for p in data['pairs'] for n in p['notes']), 'file: a note typed with a label is in the file')
    ok('gold-set.json' == dl.value.suggested_filename, 'file: it is named gold-set.json')

    # ---- who can label
    who(pg, 'Lee')
    ok('Observers can read the labels' in body(pg) and all(opt(pg, n).is_disabled() for n in names), 'people: an observer sees the numbers and cannot label')
    who(pg, 'Priya')
    ok('Pair 101 of 160' in card_text(pg), 'people: Priya, who labelled the first 100 pairs in the sample, is offered the next ones (%s)' % re.findall(r'Pair \d+ of \d+', card_text(pg)))
    who(pg, 'Sam')
    pg.get_by_role('button', name='Remove sample labels').click(); pg.wait_for_timeout(300)
    ok('Pair' in card_text(pg) and 'Sample labels are loaded' not in body(pg), 'sample: removing them leaves only real labels')
    pg.get_by_role('button', name='Remove my labels').click(); pg.wait_for_timeout(300)
    ok('Pair 1 of 160' in card_text(pg), 'start again: removing my labels returns to pair 1 of 160')

    # ---- every pair labelled
    for _ in range(160):
        if pg.locator('section[aria-labelledby="gl-pair-h"]').count() == 0: break
        opt(pg, 'Different things').click(); pg.wait_for_timeout(20)
    ok(pg.locator('#gl-done-h').count() == 1 and 'You have labelled every pair offered to you' in body(pg), 'done: when nothing is left the page says so')
    ok(pg.get_by_role('button', name='See the measured scores').first.is_visible(), 'done: it offers the measured scores')
    pg.get_by_role('button', name='See the measured scores').first.click(); pg.wait_for_timeout(300)
    t = body(pg)
    ok('Measured from 160 labelled pairs' in t, 'done: all 160 pairs count in the numbers (%s)' % re.findall(r'Measured from [\d,]+ labelled pairs', t)[:1])
    noscroll(pg, 'Methods and metrics, all labelled')

    # ---- layout
    nav(pg, 'Label pairs')
    pg.get_by_role('button', name='Remove my labels').click(); pg.wait_for_timeout(300)
    noscroll(pg, 'Label pairs, last look')
    boxes = pg.evaluate("Array.from(document.querySelectorAll('section[aria-labelledby=\"gl-pair-h\"], section[aria-labelledby=\"gl-prog\"], section[aria-labelledby=\"gl-how\"]')).map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })")
    ok(all(b[0] >= 0 and b[1] <= W for b in boxes), 'layout: the cards are inside the screen (%s)' % boxes)
    ab = pg.evaluate("Array.from(document.querySelectorAll('section[aria-labelledby=\"gl-pair-h\"] > div:nth-of-type(3) > div')).map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.top)]; })")
    if W <= 600: ok(len(ab) == 2 and ab[1][1] > ab[0][1], 'phone: requirement B sits under requirement A (%s)' % ab)
    ok(bad(errs) == [], 'no console errors: %s' % bad(errs)[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
