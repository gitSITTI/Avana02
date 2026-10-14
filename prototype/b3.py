from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
def txt(pg, sel): return pg.locator(sel).first.inner_text()
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    pg.get_by_role('button', name='Open CL-050').click(); pg.wait_for_timeout(400)
    # median, choose looser side
    pg.get_by_role('button', name='Median').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Looser middle').click(); pg.wait_for_timeout(200)
    res = pg.locator('.rv-resolve').inner_text()
    print('--- RESOLVE (median, looser) ---'); print(res[:1800])
    pg.screenshot(path='s_cl050_b.png')
    print(bad(errs))
