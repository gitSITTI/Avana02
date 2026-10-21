"""No network: the shipped page, in a browser that refuses every request that is not to the machine serving it, opens the sample, imports it, reaches Home, opens a cluster and a
few more pages, and never tries to reach another site. The text check in tools/test_prototype_offline.py only reads the file; this one runs the page.
Run: python3 b22.py 1440 (the width does not matter here, so the runner runs this file once).
project/support.js holds three addresses on cdn.jsdelivr.net (React, ReactDOM and Babel); the page does not request them, and this test is what shows it."""
import functools, http.server, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright
import h
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
PORT = 8792
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.TCPServer(('127.0.0.1', PORT), functools.partial(Q, directory=os.path.join(h.HERE, 'project')))
threading.Thread(target=srv.serve_forever, daemon=True).start()
outside, local, errs = [], [], []
try:
    with sync_playwright() as p:
        b = h.start(p)
        ctx = b.new_context(viewport={'width': W, 'height': 1000})
        pg = ctx.new_page()
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type == 'error' else None)
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        def route(r):
            u = r.request.url
            if u.startswith('http://127.0.0.1:%d/' % PORT) or u.startswith(('data:', 'blob:')):
                local.append(u); return r.continue_()
            outside.append(u); return r.abort()
        ctx.route('**/*', route)
        pg.goto('http://127.0.0.1:%d/Main.dc.html' % PORT)
        pg.wait_for_timeout(2500)
        ok(pg.get_by_role('button', name='Open the sample project').count() == 1, 'the opening screen is there')
        pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
        pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(600)
        ok('clusters are waiting for you' in pg.inner_text('h1'), 'importing the sample reaches Home (h1=%r)' % pg.inner_text('h1'))
        for label in ['Review queue', 'Methods and metrics', 'The V', 'Label pairs', 'Decisions and audit', 'AI use']:
            nav = pg.locator('.nav-btn', has_text=label).first
            if nav.count():
                nav.click(); pg.wait_for_timeout(300)
                ok(pg.inner_text('h1').strip() != '', 'page %r draws a heading (%r)' % (label, pg.inner_text('h1')[:40]))
            else:
                ok(False, 'page %r is in the menu' % label)
        ok(pg.evaluate("document.fonts.check('16px \"Public Sans\"')") is True and any(u.endswith('.woff2') for u in local), 'the bundled fonts loaded from the page\'s own folder')
        ok(len(local) > 5, 'the page and its files were served by the local server (%d requests)' % len(local))
        b.close()
finally:
    srv.shutdown(); srv.server_close()
ok(outside == [], 'no request was made to any other site (%s)' % outside[:3])
ok([e for e in errs if 'ERR_FAILED' not in e] == [], 'no console errors (%s)' % errs[:3])
print('FAILS:', fails)
sys.exit(1 if fails else 0)
