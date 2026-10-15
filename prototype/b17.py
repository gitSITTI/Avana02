"""The trace map: what a decision moves outside the requirement list (verification items, parent and child links, baselines).
Export has the tables and two real downloads; the panels say the same thing before and after a decision; a baselined requirement needs a change request.
Run: python3 b17.py 1440, python3 b17.py 900 and python3 b17.py 390."""
import csv, io, json, re, sys
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
def panel(pg): return pg.locator('aside[aria-label="One requirement"]')
def kind(pg, name): return panel(pg).get_by_role('button', name=name).first
def pick_row(pg, i):
    rows = pg.locator('button[aria-pressed]:has(span:text-matches("^REQ-"))')
    rows.nth(i).click(); pg.wait_for_timeout(250)
def picked_id(pg): return panel(pg).locator('#xp-h span').first.inner_text().strip()
def go_alone(pg):
    nav(pg, 'All requirements')
    pg.get_by_role('button', name=re.compile(r'^Alone\b')).first.click(); pg.wait_for_timeout(250)
def record_btn(pg): return panel(pg).get_by_role('button', name=re.compile(r'^(Record this decision|Record the new decision|Send the question)$')).first
def scan(pg, test, pages=10):
    """Walk the list a page of eight at a time; return whatever test() returns for the first row that gives something."""
    for _ in range(pages):
        n = min(8, pg.locator('button[aria-pressed]:has(span:text-matches("^REQ-"))').count())
        for i in range(n):
            pick_row(pg, i)
            got = test()
            if got: return got
        nxt = pg.get_by_role('button', name='Next')
        if nxt.count() == 0 or nxt.first.is_disabled(): break
        nxt.first.click(); pg.wait_for_timeout(250)
    return None
def fill(pg, sel, text):
    pg.fill(sel, text); pg.locator(sel).blur(); pg.wait_for_timeout(120)
def section(pg): return pg.locator('section[aria-labelledby="tr-h"]')
def tab_btn(pg, name): return section(pg).get_by_role('button', name=re.compile(r'^' + name))
def tab_count(pg, name):
    t = tab_btn(pg, name).first.inner_text()
    m = re.search(r'\(([\d,]+)\)', t)
    return num(m.group(1)) if m else -1
def table_rows(pg): return section(pg).locator('[role="table"] [role="row"]')
def v_move_count(pg):
    m = re.search(r'On the V:\s*([\d,]+) verification items? move', body(pg))
    return num(m.group(1)) if m else -1
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with session(W, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)

    # ---- the section, as it opens
    nav(pg, 'Export')
    s = section(pg)
    ok(s.count() == 1 and s.locator('h2', has_text='What moves outside the requirement list').count() == 1, 'section: Export has a trace map with a heading')
    ok(s.get_by_role('radio', name=re.compile(r'^Approved only')).is_checked() and not s.get_by_role('radio', name=re.compile(r'^Every decided change')).is_checked(), 'scope: it opens on approved changes only')
    names = ['Old and new IDs', 'Verification items', 'Parent and child links', 'Baselines']
    ok(all(tab_btn(pg, n).count() == 1 for n in names), 'tables: there is one button for each of the four tables')
    ok(tab_btn(pg, names[0]).get_attribute('aria-pressed') == 'true' and all(tab_btn(pg, n).get_attribute('aria-pressed') == 'false' for n in names[1:]), 'tables: the first is pressed, the others are not')
    ok(all(tab_btn(pg, n).evaluate('e => e.getBoundingClientRect().height') >= 44 for n in names), 'tables: each button is at least 44 px tall')
    ok(s.locator('[role="table"]').count() == 1 and s.locator('[role="columnheader"]').count() == 5, 'table: it is a table with five column headers')
    ok(table_rows(pg).count() >= 2 and table_rows(pg).count() <= 13, 'table: it shows a header and at most twelve rows (%d)' % table_rows(pg).count())
    ok(s.get_by_role('button', name=re.compile(r'^Download the trace map')).is_enabled(), 'download: the trace map button is on when something is approved')
    ok('real files' in s.inner_text() and 'sample values' in s.inner_text(), 'honesty: the page says the downloads are real and the data is sample data')
    noscroll(pg, 'Export with the trace map')
    ok(bad(errs) == [], 'no console errors on Export: %s' % bad(errs)[:3])
    approved_n = {n: tab_count(pg, n) for n in names}

    # ---- every decided change is the whole thing; it matches the V
    s.get_by_role('radio', name=re.compile(r'^Every decided change')).check(); pg.wait_for_timeout(250)
    all_n = {n: tab_count(pg, n) for n in names}
    ok(all(all_n[n] >= approved_n[n] for n in names) and all_n[names[0]] > approved_n[names[0]], 'scope: every decided change has more rows than approved only (%s vs %s)' % (all_n[names[0]], approved_n[names[0]]))
    vmove = v_move_count(pg)
    ok(vmove > 0 and all_n[names[1]] == vmove, 'reconcile: the verification-item rows (%d) are the V’s “verification items move” (%d)' % (all_n[names[1]], vmove))
    ok(re.search(r'\d+ old IDs? retires?', s.inner_text()) is not None and re.search(r'\d+ verification items? moves?', s.inner_text()) is not None, 'summary: it says in words how many IDs retire and how many items move')
    nav(pg, 'The V')
    vt = body(pg)
    m = re.search(r'([\d,]+)\s*\n?\s*verification items? must move', vt)
    ok(m is not None and num(m.group(1)) == vmove, 'reconcile: the V page says the same number of items must move (%s)' % (m.group(1) if m else None))
    nav(pg, 'Export')
    ok(section(pg).get_by_role('radio', name=re.compile(r'^Every decided change')).is_checked(), 'scope: the choice is still there after leaving and coming back')

    # ---- tables
    tab_btn(pg, names[1]).click(); pg.wait_for_timeout(250)
    ok(tab_btn(pg, names[1]).get_attribute('aria-pressed') == 'true' and tab_btn(pg, names[0]).get_attribute('aria-pressed') == 'false', 'tables: choosing a table presses it')
    hdr = [section(pg).locator('[role="columnheader"]').nth(i).inner_text() for i in range(5)]
    ok(hdr == ['Item', 'Method', 'Was on', 'What to do', 'Status'], 'tables: the item table has its own columns (%s)' % hdr)
    rows = table_rows(pg)
    first = rows.nth(1).inner_text()
    ok(re.match(r'(TC|AN|IN|DM|VI)-\d+', first) is not None, 'tables: the first row starts with an item ID (%s)' % first.split('\n')[0])
    ok('Move to' in section(pg).inner_text() and ('Approved' in section(pg).inner_text() or 'Waiting for sign-off' in section(pg).inner_text()), 'tables: each row says what to do and whether the decision is approved')
    ok(section(pg).locator('text=/and [\\d,]+ more in the file/').count() == 1, 'tables: rows past the twelfth are counted, not listed')
    tab_btn(pg, names[2]).click(); pg.wait_for_timeout(200)
    ok(section(pg).locator('[role="columnheader"]').first.inner_text() == 'Requirement' and table_rows(pg).count() >= 2, 'tables: parent and child links list requirements')
    tab_btn(pg, names[3]).click(); pg.wait_for_timeout(200)
    ok(section(pg).locator('[role="columnheader"]').nth(2).inner_text() == 'Change request', 'tables: baselines show the change request column')
    ok(all_n[names[3]] == 0 and 'Nothing in this table.' in section(pg).inner_text(), 'tables: no baselined requirement has been changed yet, and the table says so (%d)' % all_n[names[3]])
    # keyboard: focus the first table button and use the keys alone
    tab_btn(pg, names[0]).focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ok(tab_btn(pg, names[0]).get_attribute('aria-pressed') == 'true', 'keyboard: Enter on a table button shows that table')
    tab_btn(pg, names[1]).focus(); pg.keyboard.press('Space'); pg.wait_for_timeout(200)
    ok(tab_btn(pg, names[1]).get_attribute('aria-pressed') == 'true', 'keyboard: Space does the same')

    # ---- the files
    with pg.expect_download() as dl:
        section(pg).get_by_role('button', name=re.compile(r'^Download the trace map')).click()
    ok(dl.value.suggested_filename == 'trace-map.json', 'json: it is named trace-map.json (%s)' % dl.value.suggested_filename)
    data = json.loads(open(dl.value.path()).read())
    ok(data['format'] == 'reqin-trace-map/1' and data['sample_data'] is True and 'sample values' in data['sample_note'], 'json: it is versioned and says its data is sample data')
    ok(len(data['old_ids']) == all_n[names[0]] and len(data['verification_items']) == all_n[names[1]] and len(data['parent_child_links']) == all_n[names[2]] and len(data['baselines']) == all_n[names[3]], 'json: each list has as many rows as its table says')
    ok(data['changes'].startswith('every decided change') and set(x['status'] for x in data['old_ids']) <= {'approved', 'pending'} and 'pending' in set(x['status'] for x in data['old_ids']), 'json: it says which changes it holds and marks each as approved or pending')
    ids_ = [x['item_id'] for x in data['verification_items'] if x['action'] != 'reread']
    ok(len(ids_) == len(set(ids_)) == vmove, 'json: every item moves once, and together they are the V’s number (%d)' % len(ids_))
    olds = set(x['old_id'] for x in data['old_ids'])
    ok(all(x['was_on'] in olds for x in data['verification_items'] if x['action'] in ('move', 'choose')) and all((x['move_to'] is None) == (x['action'] != 'move') for x in data['verification_items']), 'json: every moved item was on an old ID, and only a moved item says where to')
    ok(all(x['becomes'] is None or x['becomes'] not in olds for x in data['old_ids']), 'json: nothing becomes an ID that is itself retiring')
    msg = section(pg).locator('[role="status"]').inner_text()
    ok(re.match(r'Prepared trace-map\.json with ' + str(sum(all_n.values())) + r' rows \(every decided change\)\.', msg) is not None, 'json: the page says what it made (%s)' % msg)
    with pg.expect_download() as dl2:
        section(pg).get_by_role('button', name=re.compile(r'^Download this table')).click()
    ok(dl2.value.suggested_filename == 'verification-items.csv', 'csv: it is named for the table shown (%s)' % dl2.value.suggested_filename)
    text = open(dl2.value.path(), newline='').read()
    rows_ = list(csv.reader(io.StringIO(text)))
    ok(rows_[0] == ['item_id', 'method', 'was_on', 'action', 'move_to', 'level_change', 'method_change', 'decided_in', 'status'] and len(rows_) - 1 == all_n[names[1]], 'csv: a header and one row per table row (%d)' % (len(rows_) - 1))
    ok(all(len(r) == 9 for r in rows_) and text.endswith('\r\n'), 'csv: every row has the same nine columns and ends with a line break')
    ok([r[0] for r in rows_[1:]] == [x['item_id'] for x in data['verification_items']], 'csv: the rows are the JSON rows in the same order')
    # the approved-only file is the approved part
    section(pg).get_by_role('radio', name=re.compile(r'^Approved only')).check(); pg.wait_for_timeout(250)
    with pg.expect_download() as dl3:
        section(pg).get_by_role('button', name=re.compile(r'^Download the trace map')).click()
    data2 = json.loads(open(dl3.value.path()).read())
    ok(data2['changes'] == 'approved only' and all(x['status'] == 'approved' for x in data2['old_ids'] + data2['verification_items'] + data2['baselines']), 'approved only: the file holds only approved rows')
    ok(0 < len(data2['old_ids']) < len(data['old_ids']) and set(x['old_id'] for x in data2['old_ids']) <= olds, 'approved only: it is a smaller part of the whole')
    nav(pg, 'Decisions and audit'); pg.get_by_role('button', name='Event chain').click(); pg.wait_for_timeout(250)
    ok('Downloaded trace-map.json' in body(pg) and 'Downloaded verification-items.csv' in body(pg), 'audit: both downloads are in the log')
    nav(pg, 'Export')

    # ---- a drop with nowhere to send its items, then with a covering requirement
    go_alone(pg)
    def drop_with_kids():
        rid = picked_id(pg)
        kind(pg, 'Drop it').click(); pg.wait_for_timeout(150)
        t = panel(pg).inner_text()
        m = re.search(r'(\d+) items? (?:has|have) no requirement to point at', t)
        k = re.search(r'(\d+) requirements? needs? a new parent', t)
        if m and k and panel(pg).locator('#xp-cr').count() == 0: return (rid, int(m.group(1)), int(k.group(1)))
        return None
    found = scan(pg, drop_with_kids)
    pg.select_option('#xp-reason', 'S-OBS'); pg.wait_for_timeout(120)
    ok(found is not None, 'impact: a standalone requirement with items and requirements below it was found')
    rid, n_items, n_kids = found
    ok('What this moves' in panel(pg).inner_text() and 'Above it' in panel(pg).inner_text() and 'Baseline' in panel(pg).inner_text(), 'impact: choosing “Drop it” shows what it would move, before anything is recorded')
    ok(n_items > 0 and n_kids > 0, 'impact: it counts %d items and %d requirements below that would have nowhere to go' % (n_items, n_kids))
    fill(pg, '#xp-note', 'No longer applies after the redesign.')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    ok('On record' in panel(pg).inner_text() and 'What this moves' in panel(pg).inner_text(), 'impact: after recording, the decision on record shows the same lines')
    ok(re.search(r'%d items? (?:has|have) no requirement to point at' % n_items, panel(pg).inner_text()) is not None, 'impact: the numbers on record are the numbers before')
    nav(pg, 'Export')
    section(pg).get_by_role('radio', name=re.compile(r'^Every decided change')).check(); pg.wait_for_timeout(250)
    ok(tab_count(pg, names[1]) == all_n[names[1]] + n_items, 'drop: the item table grows by that requirement’s %d items (%d to %d)' % (n_items, all_n[names[1]], tab_count(pg, names[1])))
    ok(tab_count(pg, names[0]) == all_n[names[0]] + 1, 'drop: the old-ID table grows by one')
    ok(tab_count(pg, names[2]) >= all_n[names[2]] + n_kids, 'drop: the link table grows by at least the %d requirements that need a parent' % n_kids)
    tab_btn(pg, names[1]).click(); pg.wait_for_timeout(250)
    ok(section(pg).locator('text=/Needs a requirement to point at/').count() >= 1 or 'more in the file' in section(pg).inner_text(), 'drop: items with nowhere to go say so')
    ok(re.search(r'%d (?:has|have) no requirement to point at' % n_items, section(pg).inner_text()) is not None, 'drop: the summary counts them (%d)' % n_items)
    ok(v_move_count(pg) == all_n[names[1]] + n_items, 'drop: the V line on Export counts them too (%d)' % v_move_count(pg))
    # with a covering requirement the same items move there
    nav(pg, 'All requirements')
    pg.get_by_role('button', name=re.compile(r'^All\b')).first.click(); pg.wait_for_timeout(200)
    pg.locator('.xmap span[title^="' + rid + '"]').first.click(); pg.wait_for_timeout(250)
    ok('On record' in panel(pg).inner_text(), 'cover: the dropped requirement opens with its decision on record')
    panel(pg).get_by_role('button', name='Change the decision').click(); pg.wait_for_timeout(200)
    near = panel(pg).locator('button[aria-label^="Put REQ-"]').first
    cover_id = near.get_attribute('aria-label').split(' ')[1]
    near.click(); pg.wait_for_timeout(250)
    kind(pg, 'Drop it').click(); pg.wait_for_timeout(150)
    pg.select_option('#xp-reason', 'S-COV'); pg.wait_for_timeout(150)
    fill(pg, '#xp-note', 'Covered by the requirement beside it.')
    ptxt = panel(pg).inner_text()
    ok(re.search(r'%d items? moves? to %s' % (n_items, cover_id), ptxt) is not None, 'cover: the panel says the items move to %s' % cover_id)
    ok(re.search(r'%d requirements? moves? under %s' % (n_kids, cover_id), ptxt) is not None, 'cover: and the requirements below move under it')
    record_btn(pg).click(); pg.wait_for_timeout(300)
    nav(pg, 'Export')
    section(pg).get_by_role('radio', name=re.compile(r'^Every decided change')).check(); pg.wait_for_timeout(250)
    tab_btn(pg, names[0]).click(); pg.wait_for_timeout(200)
    with pg.expect_download() as dl4:
        section(pg).get_by_role('button', name=re.compile(r'^Download the trace map')).click()
    d4 = json.loads(open(dl4.value.path()).read())
    ok(any(x['old_id'] == rid and x['becomes'] == cover_id and x['what_happened'] == 'dropped' for x in d4['old_ids']), 'cover: the file says %s becomes %s' % (rid, cover_id))
    ok(sum(1 for x in d4['verification_items'] if x['was_on'] == rid and x['move_to'] == cover_id) == n_items and sum(1 for x in d4['parent_child_links'] if x['was'] == rid and x['now'] == cover_id) == n_kids, 'cover: its %d items and %d requirements below are listed as moving to %s' % (n_items, n_kids, cover_id))
    ok(re.search(r'%d (?:has|have) no requirement to point at' % n_items, section(pg).inner_text()) is None, 'cover: nothing is left without a requirement to point at')
    ok(tab_count(pg, names[1]) == all_n[names[1]] + n_items, 'cover: the item rows are the same number, now with somewhere to go')

    # ---- a baselined requirement needs a change request
    go_alone(pg)
    def baselined():
        kind(pg, 'Drop it').click(); pg.wait_for_timeout(120)
        return picked_id(pg) if panel(pg).locator('#xp-cr').count() == 1 else None
    bl = scan(pg, baselined, 14)
    ok(bl is not None, 'baseline: a baselined standalone requirement was found among the first sixty')
    if bl:
        pg.select_option('#xp-reason', 'S-OBS'); pg.wait_for_timeout(120)
        fill(pg, '#xp-note', 'No longer applies after the redesign.')
        lbl = panel(pg).locator('label[for="xp-cr"]').inner_text()
        ok(re.match(r'Change request \(baseline BL-\d\)', lbl) is not None, 'baseline: the field names the baseline (%s)' % lbl)
        ok(record_btn(pg).is_disabled() and 'change request' in panel(pg).inner_text().lower(), 'baseline: with no change request it cannot be recorded, and the panel says why')
        fill(pg, '#xp-cr', 'CR-1')
        ok(record_btn(pg).is_disabled(), 'baseline: “CR-1” does not look like a change request')
        fill(pg, '#xp-cr', ' cr-2041 ')
        ok(record_btn(pg).is_enabled(), 'baseline: “cr-2041” does, whatever the case')
        ok('In baseline BL-' in panel(pg).inner_text() and 'needs a change request' in panel(pg).inner_text(), 'baseline: the impact lines mention the baseline')
        record_btn(pg).click(); pg.wait_for_timeout(300)
        ok('CR-2041' in panel(pg).inner_text() and 'Change request' in panel(pg).inner_text(), 'baseline: the decision on record shows CR-2041, tidied')
        nav(pg, 'Export')
        section(pg).get_by_role('radio', name=re.compile(r'^Every decided change')).check(); pg.wait_for_timeout(250)
        tab_btn(pg, names[3]).click(); pg.wait_for_timeout(250)
        ok(tab_count(pg, names[3]) == all_n[names[3]] + 1 and bl in section(pg).inner_text() + ' ' + (section(pg).locator('text=/more in the file/').inner_text() if section(pg).locator('text=/more in the file/').count() else ''), 'baseline: the baselines table gains the requirement (%d to %d)' % (all_n[names[3]], tab_count(pg, names[3])))
        nav(pg, 'Decisions and audit'); pg.get_by_role('button', name='Event chain').click(); pg.wait_for_timeout(250)
        ok('change request CR-2041' in body(pg), 'baseline: the audit log carries the change request')

    # ---- a cluster says what its decision moves
    nav(pg, 'Review queue')
    pg.locator('section[aria-label="Review queue"]').get_by_role('button', name=re.compile(r'^All\b')).first.click(); pg.wait_for_timeout(200)
    pg.select_option('#q-status', 'approved'); pg.wait_for_timeout(300)
    rows = pg.locator('button:has(span:text-matches("^CL-[0-9]+$"))')
    seen = None
    for i in range(min(rows.count(), 8)):
        rows.nth(i).click(); pg.wait_for_timeout(250)
        ct = body(pg)
        seen = re.search(r'This decision: (\d+) requirements? leaves?, (\d+) verification items? moves?, (\d+) requirements? below changes? parent', ct)
        if seen: break
    ok(seen is not None, 'cluster: an approved merge says how many requirements leave, how many items move and how many requirements below change parent')
    ok('requirement' in body(pg) and re.search(r'sits? below them|sit below them|No requirement sits below these', body(pg)) is not None, 'cluster: the V strip says what sits below these wordings')
    noscroll(pg, 'a cluster with its trace lines')
    pg.fill('#q-search', 'CL-023'); pg.wait_for_timeout(300)
    pg.select_option('#q-status', ''); pg.wait_for_timeout(300)
    pg.locator('button:has(span:text-matches("^CL-[0-9]+$"))').first.click(); pg.wait_for_timeout(250)
    ct = body(pg)
    ok(re.search(r'is in baseline BL-\d', ct) is not None and 'CR-2041' in ct, 'cluster: a baselined wording is named with its baseline and change request')
    ok(bad(errs) == [], 'no console errors: %s' % bad(errs)[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
