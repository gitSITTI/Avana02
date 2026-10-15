"""The engineering V: the page, the small V in the header, Home, the cluster strip, the filters, the numbers on Results and Export,
what recording a decision does to the V, keyboard use and the phone layout.
Run: python3 b14.py 1440, python3 b14.py 900 and python3 b14.py 390."""
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
def num(s): return int(re.sub(r'[^0-9]', '', s))
def open_cluster(pg, cid):
    pg.fill('#top-search', cid); pg.wait_for_timeout(350)
    pg.get_by_role('button', name=cid).first.click(); pg.wait_for_timeout(350)
def table_rows(pg, caption):
    """Rows of the table with this caption, as lists of cell text."""
    return pg.evaluate("""(cap) => { const t = Array.from(document.querySelectorAll('table')).find(x => x.querySelector('caption') && x.querySelector('caption').textContent.indexOf(cap) === 0);
      return t ? Array.from(t.querySelectorAll('tbody tr')).map(r => Array.from(r.children).map(c => c.textContent.trim())) : []; }""", caption)
def vee_numbers(pg):
    """Open the V and read the table, the three stat cards and the level groups."""
    nav(pg, 'The V')
    rows = table_rows(pg, 'Requirements, decisions and verification at each level of the V')
    t = body(pg)
    return rows, t
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
with session(W, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)

    # ---- the small V in the header, on every workspace screen
    for label in ['Overview', 'Review queue', 'All requirements', 'Results and grade', 'Methods and metrics', 'Decisions and audit', 'Export to documents']:
        nav(pg, label)
        g = pg.locator('button[aria-label^="Open the V."]')
        ok(g.count() == 1 and g.first.is_visible(), 'header: the small V is on "%s"' % label)
    nav(pg, 'Overview')
    aria = pg.locator('button[aria-label^="Open the V."]').first.get_attribute('aria-label')
    ok(re.search(r'\d+ of 252 clusters decided', aria) and 'verification items to move' in aria, 'header: it says in words what it shows (%s)' % aria[:90])
    ok(pg.locator('button[aria-label^="Open the V."]').first.evaluate('e => e.getBoundingClientRect().height') >= 36, 'header: the small V is a big enough target')
    pg.locator('button[aria-label^="Open the V."]').first.click(); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1').strip() == 'The engineering V', 'header: pressing it opens the V page (h1=%r)' % pg.inner_text('h1').strip())
    ok('The V' in pg.locator('.topbar').inner_text(), 'header: the breadcrumb says where you are')

    # ---- the V page
    rows, t = vee_numbers(pg)
    ok(len(rows) == 5 and rows[-1][0] == 'All levels', 'page: the table has four levels and a total (%d rows)' % len(rows))
    ok([r[0] for r in rows[:4]] == ['1 · Needs', '2 · System', '3 · Subsystem', '4 · Component'], 'page: the four levels are named (%s)' % [r[0] for r in rows[:4]])
    ok(sum(num(r[1]) for r in rows[:4]) == num(rows[4][1]) == 1248, 'page: the levels add up to the 1,248 requirements (%s)' % [r[1] for r in rows])
    ok(sum(num(r[5]) for r in rows[:4]) == num(rows[4][5]) and sum(num(r[6]) for r in rows[:4]) == num(rows[4][6]), 'page: gaps and items to re-point add up in the total row')
    ok(all(num(r[2]) <= num(r[1]) for r in rows[:4]), 'page: after the decisions no level has more than it started with')
    groups = pg.locator('[role="group"][aria-label^="Level "]')
    ok(groups.count() == 4, 'page: each level is one group a screen reader can step through (%d)' % groups.count())
    ok(all(re.match(r'Level \d\. .+ and .+\. (In step|Needs attention|Still being consolidated)\.$', groups.nth(i).get_attribute('aria-label')) for i in range(4)), 'page: each group says its level, its check and its state in words')
    for name in ['Stakeholder needs', 'System requirements', 'Subsystem requirements', 'Component requirements', 'Validation', 'System verification', 'Subsystem verification', 'Component verification', 'Design and build']:
        ok(name in t, 'page: "%s" is on the page' % name)
    ok('Sample values.' in t and 'sample values given to each requirement' in t, 'page: it says the levels, methods and items are sample values')
    ok(re.search(r'(\d+) of 252\s+clusters with a standing decision', t) is not None, 'page: the left leg counts clusters with a standing decision')
    decided_top = int(re.search(r'(\d+) of 252\s+clusters with a standing decision', t).group(1))
    ok(decided_top == num(rows[4][3].split(' of ')[0]), 'page: the left-leg card and the table agree (%d)' % decided_top)
    repoint_top = int(re.search(r'Between the legs: to carry over\s+(\d+)', t).group(1))
    ok(repoint_top == num(rows[4][6]), 'page: the carry-over card and the table agree (%d)' % repoint_top)
    traced_top = int(re.search(r'([\d,]+) of ([\d,]+)\s+requirements fully traced', t).group(1).replace(',', ''))
    ok(traced_top == num(rows[4][4].split(' ')[0]) and traced_top + num(rows[4][5]) == 1248, 'page: traced plus gaps is all 1,248 (%d + %s)' % (traced_top, rows[4][5]))
    ok(pg.locator('details summary', has_text='What the V is, and what this app does to it').count() == 1, 'page: the plain explanation is one press away')
    ok(pg.locator('table caption').count() >= 1 and pg.locator('table th[scope="col"]').count() >= 7 and pg.locator('table th[scope="row"]').count() >= 5, 'page: the table has a caption and header cells')
    ok('Needs attention' in t or 'Still being consolidated' in t, 'page: a level never claims to be finished while clusters are open')
    noscroll(pg, 'V page')
    pg.screenshot(path='o_vee%d.png' % W, full_page=True)

    # ---- the legs link to the work: open clusters, gaps, Export
    lvl1_open = num(re.search(r'Review the (\d+) open', pg.locator('[role="group"][aria-label^="Level 1."]').inner_text()).group(1))
    pg.locator('[role="group"][aria-label^="Level 1."]').get_by_role('button', name=re.compile('^Review the')).click(); pg.wait_for_timeout(350)
    ok('Review queue' in pg.locator('.topbar').inner_text() and pg.locator('#q-lvl').input_value() == '1', 'links: "Review the open" opens the queue on that level')
    info = pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text()
    ok(num(info.split(' of ')[1]) == lvl1_open, 'links: the queue lists exactly the open clusters the V counted (%s, V said %d)' % (info, lvl1_open))
    ok(pg.locator('#q-status').input_value() == 'undecided', 'links: the status filter says "still to decide", so the list is the clusters the V called open')
    pg.get_by_role('button', name='Clear filters').click(); pg.wait_for_timeout(250)
    all_info = pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text()
    ok(num(all_info.split(' of ')[1]) == 252 and pg.get_by_role('button', name='Clear filters').count() == 0, 'links: clearing the filters shows all 252 clusters (%s)' % all_info)
    pg.locator('#q-lvl').select_option('2'); pg.wait_for_timeout(250)
    l2 = num(pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text().split(' of ')[1])
    ok(0 < l2 < 252, 'links: the level filter narrows the queue (level 2: %d)' % l2)
    pg.get_by_role('button', name='Clear filters').click(); pg.wait_for_timeout(250)
    nav(pg, 'The V')
    gap_group = pg.locator('[role="group"][aria-label^="Level 1."]')
    gaps1 = num(re.search(r'(\d+) requirements? without a method or an item', gap_group.inner_text()).group(1))
    gap_group.get_by_role('button', name=re.compile('^See the gaps')).click(); pg.wait_for_timeout(350)
    ok(pg.inner_text('h1').strip() == 'All requirements', 'links: "See the gaps" opens All requirements')
    ok(pg.get_by_role('button', name='Level 1 · Needs').get_attribute('aria-pressed') == 'true' and pg.get_by_role('button', name='Verification gaps only').get_attribute('aria-pressed') == 'true', 'links: the level and the gap filter are both on, and say so')
    ok(num(pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text().split(' of ')[1]) == gaps1, 'links: All requirements lists the %d gaps the V counted' % gaps1)
    pg.get_by_role('button', name='Verification gaps only').click(); pg.wait_for_timeout(250)
    pg.get_by_role('button', name='All levels').click(); pg.wait_for_timeout(250)
    ok(num(pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text().split(' of ')[1]) == 1248, 'links: with both filters off All requirements shows all 1,248')
    pg.get_by_role('button', name='Level 3 · Subsystem').click(); pg.wait_for_timeout(250)
    l3 = num(pg.locator('text=/Showing 1 to \\d+ of \\d+/').first.inner_text().split(' of ')[1])
    ok(l3 == num(rows[2][1]), 'links: the level chip lists the requirements the V counted at that level (%d)' % l3)
    noscroll(pg, 'All requirements with the level filter')
    nav(pg, 'The V')
    pg.get_by_role('button', name='Open Export').click(); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1').strip().startswith('Export'), 'links: "Open Export" goes to Export')
    ok('On the V:' in body(pg) and re.search(r'On the V: %d verification items move' % repoint_top, body(pg)) is not None, 'export: it says how many verification items move (%d)' % repoint_top)
    noscroll(pg, 'Export')

    # ---- Home, Results and the cluster strip carry the same numbers
    nav(pg, 'Home')
    th = body(pg)
    ok('Where the work sits in the V' in th and ('%d of 252 clusters have a standing decision on the left leg' % decided_top) in th, 'home: the card has the same count as the V page (%d)' % decided_top)
    ok(('%d verification items will have to move' % repoint_top) in th, 'home: the card has the same carry-over count (%d)' % repoint_top)
    pg.locator('section[aria-labelledby="home-v"]').get_by_role('button', name='Open the V').click(); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1').strip() == 'The engineering V', 'home: the card opens the V page')
    nav(pg, 'Results and grade')
    rrows = table_rows(pg, 'Requirements before and after your decisions, by level of the V')
    ok(len(rrows) == 5 and [r[1] for r in rrows] == [r[1] for r in rows] and [r[2] for r in rrows] == [r[2] for r in rows], 'results: the by-level table has the same originals and the same "after" as the V page')
    ok(rrows[4][2] == rows[4][2] and num(rrows[4][4]) == repoint_top, 'results: the total after and the items to re-point match the V page (%s, %s)' % (rrows[4][2], rrows[4][4]))
    ok(sum(int(x[3].replace('−', '-').replace('+', '')) for x in rrows[:4]) == int(rrows[4][3].replace('−', '-').replace('+', '')) == num(rows[4][2]) - 1248, 'results: the changes by level add up to the change in the total')
    noscroll(pg, 'Results with the V table')

    # a cluster inside one level, and one that spans two levels
    nav(pg, 'Overview')
    open_cluster(pg, 'CL-001')
    strip = pg.locator('[role="group"][aria-label="Where this cluster sits in the V"]')
    st = strip.inner_text()
    ok('Level 3 · Subsystem requirements, checked at subsystem verification' in st and '4 verification items are linked across them (M1: 2, M2: 2)' in st, 'cluster: a one-level cluster says its level, its check and its verification items (%r)' % st[:150])
    ok('Merging would leave' not in st, 'cluster: no warning about levels when there is only one')
    open_cluster(pg, 'CL-038')
    st = pg.locator('[role="group"][aria-label="Where this cluster sits in the V"]').inner_text()
    ok('Spans level 1 (Needs) and level 2 (System)' in st and 'Link them as parent and child' in st and 'Merging would leave level 1 with a check that proves nothing.' in st, 'cluster: a cluster that spans two levels says to link, not merge (%r)' % st[:150])
    acts = pg.locator('.rv-resolve').inner_text()
    ok('Merge into one' not in acts, 'cluster: a cluster that spans two levels does not offer "Merge into one"')
    ok('Each stays with its own requirement' in st, 'cluster: it says each verification item stays with its own level')
    noscroll(pg, 'cluster with the V strip')
    pg.screenshot(path='o_veestrip%d.png' % W, full_page=True)

    # ---- recording one decision moves the V, by exactly what the decision did
    nav(pg, 'The V')
    before = [list(r) for r in rows]
    open_cluster(pg, 'CL-001')
    rv = pg.locator('.rv-resolve')
    rv.get_by_role('button', name='Most stringent').click(); pg.wait_for_timeout(200)
    rv.get_by_label('3 · Reason code').select_option(index=1); pg.wait_for_timeout(100)
    rv.locator('textarea[placeholder^="Why this choice"]').fill('Same obligation, the strictest value is kept.'); pg.wait_for_timeout(100)
    if rv.get_by_label('I have read the wordings and the guard results.').count(): rv.get_by_label('I have read the wordings and the guard results.').check()
    pg.wait_for_timeout(100)
    rec = rv.get_by_role('button', name=re.compile('^Record')).first
    ok(rec.is_enabled(), 'record: the decision on CL-001 can be recorded')
    rec.click(); pg.wait_for_timeout(400)
    after, t2 = vee_numbers(pg)
    ok(num(after[2][3].split(' of ')[0]) == num(before[2][3].split(' of ')[0]) + 1 and num(after[4][3].split(' of ')[0]) == num(before[4][3].split(' of ')[0]) + 1, 'record: level 3 and the total each gain one decided cluster')
    ok(num(after[2][2]) == num(before[2][2]) - 1 and num(after[4][2]) == num(before[4][2]) - 1, 'record: merging two wordings into one takes one requirement off level 3 and off the total (%s to %s)' % (before[2][2], after[2][2]))
    ok(num(after[2][6]) == num(before[2][6]) + 2 and num(after[4][6]) == num(before[4][6]) + 2, 'record: the two verification items on the wording that goes must now move (%s to %s)' % (before[2][6], after[2][6]))
    ok([r[1] for r in after] == [r[1] for r in before] and [r[4] for r in after] == [r[4] for r in before] and [r[5] for r in after] == [r[5] for r in before], 'record: requirements, traced and gaps do not change, only the decisions do')
    ok([r[3] for i, r in enumerate(after) if i not in (2, 4)] == [r[3] for i, r in enumerate(before) if i not in (2, 4)], 'record: no other level changed')
    noscroll(pg, 'V page after a decision')

    # ---- keyboard: the small V can be reached and pressed without a mouse
    nav(pg, 'Overview')
    pg.locator('#top-search').focus()
    reached = False
    for _ in range(14):
        pg.keyboard.press('Tab')
        if (pg.evaluate("document.activeElement.getAttribute('aria-label') || ''") or '').startswith('Open the V.'): reached = True; break
    ok(reached, 'keyboard: Tab from the search box reaches the small V')
    outline = pg.evaluate("(() => { const s = getComputedStyle(document.activeElement); return [s.outlineStyle, s.outlineWidth, s.boxShadow]; })()")
    ok(outline[0] != 'none' or outline[2] != 'none', 'keyboard: the small V shows a focus ring (%s)' % outline)
    pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    ok(pg.inner_text('h1').strip() == 'The engineering V', 'keyboard: Enter on the small V opens the page')
    pg.locator('summary', has_text='What the V is').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(150)
    ok(pg.locator('details').first.get_attribute('open') is not None and 'Consolidation removes requirements from the left.' in body(pg), 'keyboard: the explanation opens with Enter')

    # ---- who can see it: every person, and the phone layout
    for who in ['Jordan', 'Casey', 'Lee']:
        pg.locator('button', has_text=who).first.click(); pg.wait_for_timeout(250)
        nav(pg, 'The V')
        ok(pg.inner_text('h1').strip() == 'The engineering V' and pg.locator('[role="group"][aria-label^="Level "]').count() == 4, 'people: %s sees the same V' % who)
    if W <= 900:
        ok(pg.locator('.v-head').evaluate('e => getComputedStyle(e).display') == 'none', 'narrow: the two column titles are hidden when the legs are stacked')
        boxes = pg.evaluate("Array.from(document.querySelectorAll('.v-card')).map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.left), Math.round(r.right)]; })")
        ok(all(b[0] >= 0 and b[1] <= W for b in boxes), 'narrow: every level card is inside the screen (%d cards)' % len(boxes))
    noscroll(pg, 'V page, last look')
    ok(bad(errs) == [], 'no console errors: %s' % bad(errs)[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
