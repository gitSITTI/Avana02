import h
with h.session(page='Test.dc.html') as (pg, errs):
    print(pg.inner_text('#out'), pg.locator('.row').count(), pg.locator('.chip').count(), pg.locator('.flag').count())
    pg.select_option('#sel','a'); pg.fill('#inp','hello'); pg.locator('.chip').first.click(); pg.locator('#btn').click(); pg.wait_for_timeout(200)
    print(pg.inner_text('#out'), pg.locator('#btn').is_disabled())
    print([e for e in errs if 'ERR_FAILED' not in e])
