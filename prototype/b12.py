"""Workspace shell, Home screen and the wording comparison: navigation, Home chips and lists, top search, reference picking,
the "Line up the words" window and its keyboard behaviour. Run: python3 b12.py 1440 and python3 b12.py 390."""
import sys
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
with session(W, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
    # ---- Home
    ok('clusters are waiting for you' in pg.inner_text('h1'), 'home: lands on Home (h1=%r)' % pg.inner_text('h1'))
    t = body(pg)
    ok('High security' in t and 'Sources are read-only' in t, 'home: security band')
    for chip in ['Spreadsheet or CSV', 'ERP database', 'Word or PDF']:
        ok(pg.locator('.chip-src', has_text=chip).count() == 1, 'home: source chip "%s"' % chip)
    ok('A read-only SQL query' in t, 'home: the ERP chip says it is a read-only SQL query')
    ok(pg.locator('.bar-row').count() == 4, 'home: four bars (%d)' % pg.locator('.bar-row').count())
    ok(pg.locator('.home-aside li').count() >= 3, 'home: activity list has items')
    heads = pg.locator('.acc-head')
    ok(heads.count() == 3 and heads.nth(0).get_attribute('aria-expanded') == 'true' and heads.nth(1).get_attribute('aria-expanded') == 'false', 'home: recent imports start with the first open')
    heads.nth(1).click(); pg.wait_for_timeout(150)
    ok(pg.locator('.acc-head').nth(1).get_attribute('aria-expanded') == 'true' and 'Records read' in body(pg), 'home: a row opens')
    pg.locator('.acc-head').nth(1).click(); pg.wait_for_timeout(150)
    ok(pg.locator('.acc-head').nth(1).get_attribute('aria-expanded') == 'false', 'home: the same row closes')
    noscroll(pg, 'home')
    pg.screenshot(path='o_home%d.png' % W, full_page=True)
    # a source chip starts the import flow for that source
    pg.locator('.chip-src', has_text='ERP database').click(); pg.wait_for_timeout(300)
    ok('Read-only query: SELECT' in body(pg), 'home: ERP chip opens the read-only SQL import')
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
    # a bar opens the queue filtered to that allocation's open clusters
    pg.locator('.bar-row').first.click(); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1') != '' and 'Review queue' in pg.locator('.topbar').inner_text(), 'home: a bar opens the review queue')
    ok(pg.locator('#q-alloc').input_value() != '' and pg.locator('#q-status').input_value() == 'open', 'home: bar sets the allocation and status filters')
    nav(pg, 'Home')
    # ---- navigation groups
    expanded = lambda: pg.locator('.nav-ghead').nth(0).get_attribute('aria-expanded')
    ok(expanded() == 'true' and pg.locator('.nav-btn', has_text='Methods and metrics').first.is_visible() or W <= 900, 'nav: groups start open')
    if W > 900:
        pg.locator('.nav-ghead').nth(0).click(); pg.wait_for_timeout(150)
        ok(expanded() == 'false' and not pg.locator('.nav-btn', has_text='Methods and metrics').first.is_visible(), 'nav: a group closes')
        pg.locator('.nav-ghead').nth(0).click(); pg.wait_for_timeout(150)
    for label, h1 in [('Overview', 'Overview'), ('Methods and metrics', 'Methods and metrics'), ('Decisions and audit', 'Decisions and audit'), ('Sign-off policy', 'Sign-off policy'), ('Export to documents', 'Export to documents'), ('All requirements', 'All requirements')]:
        nav(pg, label)
        ok(pg.inner_text('h1').strip() == h1, 'nav: %s (h1=%r)' % (label, pg.inner_text('h1').strip()))
        ok(pg.locator('.nav-btn[aria-current="page"]').count() == 1, 'nav: exactly one current item on %s' % label)
    # ---- top bar
    pg.fill('#top-search', 'retention'); pg.wait_for_timeout(300)
    ok('Review queue' in pg.locator('.topbar').inner_text() and pg.locator('#q-search').input_value() == 'retention', 'top bar: searching opens the queue with the term')
    pg.get_by_role('button', name='Open the glossary').click(); pg.wait_for_timeout(200)
    ok('Glossary and help' in body(pg) and pg.get_by_role('button', name='Close glossary').count() == 1, 'top bar: glossary opens')
    pg.get_by_role('button', name='Close glossary').click(); pg.wait_for_timeout(150)
    pg.get_by_role('button', name='Open the audit log').click(); pg.wait_for_timeout(250)
    ok(pg.inner_text('h1').strip() == 'Decisions and audit', 'top bar: audit log opens')
    pg.get_by_role('button', name='Ask the assistant').click(); pg.wait_for_timeout(200)
    ok(pg.locator('aside[aria-label="Assistant"]').count() == 1 and pg.get_by_role('button', name='Hide the assistant').get_attribute('aria-pressed') == 'true', 'top bar: assistant opens')
    pg.get_by_role('button', name='Close the assistant').click(); pg.wait_for_timeout(150)
    ok(pg.locator('aside[aria-label="Assistant"]').count() == 0, 'top bar: assistant closes')
    # ---- comparison on the six-wording group
    nav(pg, 'Overview'); pg.get_by_role('button', name='Open CL-050').click(); pg.wait_for_timeout(500)
    t = body(pg)
    ok('Every wording is compared with M4 · REQ-SYS-0431, the strictest' in t, 'compare: reference starts as the strictest')
    ok(pg.locator('.cmp-row').count() == 6 and pg.locator('.cmp-row[data-ref="true"]').count() == 1, 'compare: six rows, one reference')
    ok(pg.locator('.cmp-row').first.get_attribute('data-ref') == 'true', 'compare: reference row is first')
    ok(pg.get_by_role('button', name='Use as reference').count() == 5, 'compare: five rows offer "Use as reference"')
    ok('365 → 30' in t and 'retain → store' in t and 'at least → a minimum of' in t, 'compare: change chips name each difference')
    ok('Reworded' in t and 'Same words as the reference' not in t, 'compare: the rewritten member is called Reworded')
    ok('A' not in [b.strip() for b in pg.locator('.cmp-row button').all_inner_texts()], 'compare: no A/B buttons any more')
    ok('Beyond the words' in t and 'Owner' in t and 'Verification' in t, 'compare: fields other than the words are listed')
    noscroll(pg, 'compare redline')
    pg.screenshot(path='o_compare%d.png' % W, full_page=True)
    pg.get_by_role('button', name='Use as reference: M1').click(); pg.wait_for_timeout(250)
    t = body(pg)
    ok('Every wording is compared with M1 · REQ-SYS-0412.' in t and pg.locator('.cmp-row').first.get_attribute('data-ref') == 'true' and 'REQ-SYS-0412' in pg.locator('.cmp-row').first.inner_text(), 'compare: choosing M1 moves it to the top as the reference')
    ok('30 → 365' in t, 'compare: differences are now measured against M1 (30 → 365)')
    # the lined-up window
    pg.get_by_role('button', name='Line up the words').click(); pg.wait_for_timeout(350)
    dlg = pg.get_by_role('dialog')
    ok(dlg.count() == 1 and 'lined up against M1 · REQ-SYS-0412' in dlg.inner_text(), 'align: the window opens for the reference')
    ok(pg.evaluate('document.activeElement && document.activeElement.id') == 'al-close', 'align: focus moves to Close')
    ok(dlg.locator('[role="row"]').count() == 6, 'align: one row per wording (%d)' % dlg.locator('[role="row"]').count())
    box = dlg.bounding_box(); vp = pg.viewport_size
    ok(box['x'] >= 0 and box['x'] + box['width'] <= vp['width'] + 1, 'align: the window stays inside the screen (%d..%d of %d)' % (box['x'], box['x'] + box['width'], vp['width']))
    noscroll(pg, 'align window')
    pg.screenshot(path='o_align%d.png' % W)
    for _ in range(40):                       # focus must stay inside the window
        pg.keyboard.press('Tab')
    ok(pg.evaluate("document.activeElement.closest('[role=dialog]') !== null"), 'align: Tab keeps focus inside the window')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    ok(pg.get_by_role('dialog').count() == 0, 'align: Escape closes it')
    ok(pg.evaluate('document.activeElement && document.activeElement.id') == 'al-open', 'align: focus returns to the button that opened it')
    # peeling out the reference falls back to the strictest
    pg.get_by_role('button', name='Peel out M1').click(); pg.wait_for_timeout(250)
    ok('Every wording is compared with M4' in body(pg) and pg.locator('.cmp-row').count() == 5, 'compare: peeling out the reference falls back to the strictest')
    noscroll(pg, 'compare after peel')
    ok(bad(errs) == [], 'no console errors: %s' % bad(errs)[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
