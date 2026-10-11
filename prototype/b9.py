from h import session
def nav(pg, label): pg.locator('nav button', has_text=label).first.click(); pg.wait_for_timeout(300)
def who(pg, name): pg.locator('nav button', has_text=name).first.click(); pg.wait_for_timeout(300)
def open_cluster(pg, cid):
    pg.locator('.rv-queue button', has_text='All').first.click(); pg.wait_for_timeout(200)
    pg.get_by_placeholder('Search ID, title or wording').fill(cid); pg.wait_for_timeout(200)
    pg.locator('.rv-queue button', has_text=cid).first.click(); pg.wait_for_timeout(300)
with session(1440, 1000) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    nav(pg, 'Review queue'); who(pg, 'Jordan'); open_cluster(pg, 'CL-042')
    el = pg.get_by_text('YOUR LENS ·').first
    el.scroll_into_view_if_needed(); pg.evaluate('window.scrollBy(0,-120)'); pg.wait_for_timeout(200)
    pg.screenshot(path='s_lens.png')
    pg.evaluate('window.scrollBy(0,820)'); pg.wait_for_timeout(200)
    pg.screenshot(path='s_lens2.png')
