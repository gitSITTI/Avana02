"""Local harness: serves project/ and runs it in headless Chromium with React from node_modules."""
import glob, threading, http.server, socketserver, os, functools, contextlib
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 8791
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
@contextlib.contextmanager
def session(w=1440, h=1000, page='Main.dc.html'):
    handler = functools.partial(Q, directory=os.path.join(HERE, 'project'))
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.TCPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    exe = [os.environ['CHROMIUM_PATH']] if os.environ.get('CHROMIUM_PATH') else glob.glob('/opt/pw-browsers/chromium-*/chrome-linux*/chrome')
    vend = os.path.join(HERE, 'vendor', 'node_modules')
    files = {'react@18.3.1/umd/react.production.min.js': vend + '/react/umd/react.production.min.js',
             'react-dom@18.3.1/umd/react-dom.production.min.js': vend + '/react-dom/umd/react-dom.production.min.js',
             '@babel/standalone@7.29.0/babel.min.js': vend + '/@babel/standalone/babel.min.js'}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe[0] if exe else None, args=['--no-sandbox'])
        ctx = b.new_context(viewport={'width': w, 'height': h})   # a context, so a second tab of the same browser shares storage and routes
        pg = ctx.new_page()
        errs = []
        pg.on('console', lambda m: errs.append(m.type + ': ' + m.text) if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        def route(r):
            u = r.request.url
            for k, v in files.items():
                if k in u:
                    return r.fulfill(path=v, content_type='application/javascript')
            if 'fonts.g' in u: return r.abort()
            return r.continue_()
        ctx.route('**/*', route)
        pg.goto('http://127.0.0.1:%d/%s' % (PORT, page))
        pg.wait_for_timeout(1800)
        try:
            yield pg, errs
        finally:
            b.close()
            srv.shutdown(); srv.server_close()
