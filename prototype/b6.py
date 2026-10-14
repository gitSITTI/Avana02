from h import session
import sys
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
W = int(sys.argv[1]) if len(sys.argv) > 1 else 900
with session(W, 900) as (pg, errs):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(200)
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(300)
    pg.locator('.nav-btn', has_text='Overview').first.click(); pg.wait_for_timeout(300)   # the workspace now opens on Home
    pg.locator('nav button', has_text='Review queue').first.click(); pg.wait_for_timeout(300)
    pg.evaluate('window.scrollTo(0,0)')
    pg.screenshot(path='n_%d_top.png' % W)
    pg.evaluate('window.scrollTo(0,800)')
    pg.screenshot(path='n_%d_mid.png' % W)
    print(W, 'scrollWidth', pg.evaluate('document.documentElement.scrollWidth'), 'clientWidth', pg.evaluate('document.documentElement.clientWidth'), bad(errs))
