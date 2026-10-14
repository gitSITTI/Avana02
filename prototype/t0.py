import h
with h.session() as (pg, errs):
    print('title', pg.title())
    print(pg.inner_text('body')[:200].replace('\n',' | '))
    pg.get_by_text('Open the sample project').first.click(); pg.wait_for_timeout(300)
    pg.get_by_text('Confirm mapping and import').first.click(); pg.wait_for_timeout(500)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    print(pg.inner_text('body')[:300].replace('\n',' | '))
    print('errs', errs[:10])
