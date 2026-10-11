from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
    print('import:', pg.inner_text('h1'))
    pg.screenshot(path='s_import.png', full_page=True)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
    print('overview:', pg.inner_text('h1'), bad(errs))
    pg.screenshot(path='s_overview.png')
    pg.get_by_role('button', name='Start with the safest cluster').click(); pg.wait_for_timeout(500)
    pg.screenshot(path='s_review.png')
    print('review h1:', pg.locator('h1').first.inner_text(), bad(errs))
