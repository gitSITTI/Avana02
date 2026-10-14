from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    pg.get_by_role('button', name='Open CL-050').click(); pg.wait_for_timeout(400)
    pg.get_by_role('button', name='Median').click(); pg.wait_for_timeout(150)
    pg.get_by_role('button', name='Looser middle').click(); pg.wait_for_timeout(150)
    rec = pg.get_by_role('button', name='Record decision')
    print('record disabled initially:', rec.is_disabled(), '|', pg.locator('.rv-resolve').inner_text().split('\n')[-1])
    pg.locator('.rv-resolve select').select_option(index=2); pg.wait_for_timeout(100)
    print('after reason, disabled:', rec.is_disabled(), '|', pg.locator('.rv-resolve').inner_text().split('\n')[-1])
    pg.locator('.rv-resolve textarea').fill('Retention needs to cover the 60 day ground pass; owners agree in the weekly sync.'); pg.wait_for_timeout(100)
    print('after note, disabled:', rec.is_disabled(), '|', pg.locator('.rv-resolve').inner_text().split('\n')[-1])
    pg.locator('.rv-resolve input[type=checkbox]').check(); pg.wait_for_timeout(100)
    print('after ack, disabled:', rec.is_disabled(), '|', pg.locator('.rv-resolve').inner_text().split('\n')[-1])
    rec.click(); pg.wait_for_timeout(400)
    print('--- after record ---'); print(pg.locator('.rv-resolve').inner_text()[:900])
    det = pg.locator('.rv-detail').inner_text()
    i = det.index('Sign-off policy for this cluster'); print(det[:240]); print('...'); print(det[i:i+900])
    pg.screenshot(path='s_recorded.png')
    # sign as other lenses
    for who, lens in [('Priya','Process engineer'),('Jordan','UI/UX engineer'),('Casey','New user'),('Morgan',None)]:
        pg.locator('nav button', has_text=who).first.click(); pg.wait_for_timeout(300)
        det = pg.locator('.rv-detail').inner_text()
        i = det.index('Sign-off policy for this cluster')
        btns = [b.inner_text() for b in pg.locator('.rv-detail button').all() if 'ign' in b.inner_text() or 'approval' in b.inner_text() or 'Record' in b.inner_text()]
        print(who, '->', btns, '|', det[i+30:i+160].replace('\n',' / '))
    print(bad(errs))
