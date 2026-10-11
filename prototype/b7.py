from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
def nav(pg, label): pg.locator('nav button', has_text=label).first.click(); pg.wait_for_timeout(300)
def who(pg, name): pg.locator('nav button', has_text=name).first.click(); pg.wait_for_timeout(300)
def detail(pg): return pg.locator('.rv-detail').inner_text()
def resolve(pg): return pg.locator('.rv-resolve').inner_text()
def open_cluster(pg, cid):
    pg.get_by_placeholder('Search ID, title or wording').fill(cid); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='All', exact=False).filter(has_text='All').first.click() if False else None
    pg.locator('.rv-queue button', has_text=cid).first.click(); pg.wait_for_timeout(300)
ok = lambda c, m: print(('PASS ' if c else 'FAIL ') + m)
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    nav(pg, 'Review queue')
    # all tab so search covers everything
    pg.locator('.rv-queue button', has_text='All').first.click(); pg.wait_for_timeout(200)
    # 1. claim, changed
    open_cluster(pg, 'CL-002')
    pg.get_by_role('button', name='A teammate claims the open cluster').click(); pg.wait_for_timeout(300)
    ok('looking at this cluster' in detail(pg), 'claim banner')
    pg.get_by_role('button', name='A teammate changes the open cluster').click(); pg.wait_for_timeout(300)
    ok('changed after you opened it' in detail(pg), 'changed banner')
    ok(pg.get_by_role('button', name='Record decision').is_disabled(), 'record disabled while stale version')
    pg.get_by_role('button', name='Reload the cluster').click(); pg.wait_for_timeout(300)
    ok('changed after you opened it' not in detail(pg), 'reload clears banner')
    # 2. decide + drift
    pg.get_by_role('button', name='Merge into one').click(); pg.wait_for_timeout(150)
    pg.get_by_role('button', name='Most stringent').click(); pg.wait_for_timeout(150)
    pg.locator('.rv-resolve select').select_option(index=1); pg.wait_for_timeout(100)
    rec = pg.get_by_role('button', name='Record decision')
    print('   record disabled?', rec.is_disabled(), resolve(pg).split('\n')[-1])
    rec.click(); pg.wait_for_timeout(300)
    ok('Decision recorded as R3' in detail(pg), 'decision recorded banner')
    pg.get_by_role('button', name='The source drifts under a decision').click(); pg.wait_for_timeout(300)
    ok('Stale: the source changed' in detail(pg), 'stale banner')
    pg.get_by_role('button', name='Reopen for review').click(); pg.wait_for_timeout(300)
    ok('Stale:' not in detail(pg) and 'Merge into one' in resolve(pg), 'reopen from stale')
    # 3. dispute as Morgan
    who(pg, 'Morgan'); open_cluster(pg, 'CL-115')
    ok('has objected' in detail(pg), 'dispute banner for lead')
    ups = pg.get_by_role('button', name='Uphold the decision')
    ok(ups.is_disabled(), 'uphold disabled without note')
    pg.locator('.rv-detail textarea').first.fill('Reviewed both views; the decision stands on the parent value.'); pg.wait_for_timeout(150)
    ok(not ups.is_disabled(), 'uphold enabled with note')
    ups.click(); pg.wait_for_timeout(300)
    ok('has objected' not in detail(pg), 'dispute cleared')
    # 4. siblings as Sam
    who(pg, 'Sam'); open_cluster(pg, 'CL-062')
    ok('edited this at the same time' in detail(pg), 'sibling banner')
    pg.get_by_role('button', name='Keep R3a').click(); pg.wait_for_timeout(300)
    ok('edited this at the same time' not in detail(pg), 'sibling resolved')
    # 5. oversized
    open_cluster(pg, 'CL-117')
    ok('Too big to resolve' in detail(pg), 'oversized banner')
    n0 = pg.locator('.rv-detail button', has_text='Peel out').count()
    for i in range(3):
        pg.locator('.rv-detail button', has_text='Peel out').first.click(); pg.wait_for_timeout(200)
    print('   peel buttons', n0, '->', pg.locator('.rv-detail button', has_text='Peel out').count(), '|', 'Too big' in detail(pg))
    # 6. NU
    who(pg, 'Casey'); pg.locator('.rv-queue button', has_text='For me').first.click(); pg.wait_for_timeout(300)
    first = pg.locator('.rv-queue button[aria-current]').first
    rows = pg.locator('.rv-queue button:has-text("Lane")')
    print('   Casey for-me count text:', pg.locator('.rv-queue').inner_text().split('\n')[:12])
    print(bad(errs))
