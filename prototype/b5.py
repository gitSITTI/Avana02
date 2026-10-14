from h import session
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
def enter(pg):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
def nav(pg, label): pg.locator('nav button', has_text=label).first.click(); pg.wait_for_timeout(400)
with session(1440, 1000) as (pg, errs):
    enter(pg)
    nav(pg, 'All requirements'); pg.evaluate('window.scrollTo(0,0)'); pg.screenshot(path='v_explorer.png')
    nav(pg, 'Decisions and audit'); pg.evaluate('window.scrollTo(0,0)'); pg.screenshot(path='v_audit.png')
    nav(pg, 'Sign-off policy'); pg.evaluate('window.scrollTo(0,0)'); pg.screenshot(path='v_policy.png', full_page=False)
    nav(pg, 'Review queue')
    pg.get_by_role('button', name='Ask the assistant').click(); pg.wait_for_timeout(300)
    pg.get_by_role('button', name='What does this group say?').click() if pg.get_by_role('button', name='What does this group say?').count() else None
    pg.evaluate('window.scrollTo(0,0)'); pg.screenshot(path='v_chat.png')
    print([b.inner_text() for b in pg.locator('aside[aria-label=Assistant] button').all()][:12])
    print(bad(errs))
