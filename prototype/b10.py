from h import session
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='Pilot on one allocation').click(); pg.wait_for_timeout(300)
    pg.screenshot(path='s_import2.png')
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(400)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    print(pg.locator('main').inner_text()[:700])
    pg.screenshot(path='s_pilot_overview.png')
