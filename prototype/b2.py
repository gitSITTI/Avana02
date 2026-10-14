from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    pg.get_by_role('button', name='Open CL-050').click(); pg.wait_for_timeout(500)
    pg.evaluate('window.scrollTo(0,0)')
    pg.screenshot(path='s_cl050.png')
    # pick median
    pg.get_by_role('button', name='Median').click(); pg.wait_for_timeout(300)
    pg.screenshot(path='s_cl050_median.png')
    print(bad(errs))
