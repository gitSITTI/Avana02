"""Accessibility: axe-core on every page and state, then the checks a scanner cannot make: contrast measured as drawn, the keyboard, a screen reader's view of the page,
reflow at 320 pixels, and reduced motion.
Run: python3 b20.py 1440, python3 b20.py 900 and python3 b20.py 390.  A WCAG 2.2 AA scan with axe-core 4.13 (vendor/package.json) plus the checks in a11y_page.js."""
import json, os, re, sys
from h import session, HERE
import chart_colours
fails = []
def ok(cond, msg):
    print(('PASS ' if cond else 'FAIL ') + msg)
    if not cond: fails.append(msg)
def bad(errs): return [e for e in errs if 'ERR_FAILED' not in e]
W = int(sys.argv[1]) if len(sys.argv) > 1 else 1440
AXE = os.path.join(HERE, 'vendor', 'node_modules', 'axe-core', 'axe.min.js')
PAGEJS = os.path.join(HERE, 'a11y_page.js')
TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice']

def nav(pg, label):
    pg.locator('.nav-btn', has_text=label).first.click(); pg.wait_for_timeout(300)
def open_sample(pg):
    pg.get_by_role('button', name='Open the sample project').click(); pg.wait_for_timeout(300)
def import_it(pg):
    pg.get_by_role('button', name='Confirm mapping and import').click(); pg.wait_for_timeout(500)
def open_cluster(pg, cid):
    pg.fill('#top-search', ''); pg.wait_for_timeout(150)
    pg.fill('#top-search', cid); pg.wait_for_timeout(350)
    pg.get_by_role('button', name=cid).first.click(); pg.wait_for_timeout(350)
def who(pg, name):
    pg.get_by_role('button', name=re.compile(r'^' + name + r'\b')).first.click(); pg.wait_for_timeout(300)

def axe(pg):
    return pg.evaluate("""async (tags) => {
      const r = await axe.run(document, { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations', 'incomplete'] });
      const one = (v) => ({ id: v.id, impact: v.impact, help: v.help, n: v.nodes.length, ex: v.nodes.slice(0, 2).map((n) => n.target.join(' ').slice(0, 80) + ' :: ' + n.html.slice(0, 100) + ' :: ' + ((n.any.concat(n.all).concat(n.none)[0] || {}).message || '').slice(0, 200)) });
      return { violations: r.violations.map(one), incomplete: r.incomplete.filter((v) => v.id !== 'color-contrast').map(one) };
    }""", TAGS)

def sweep(pg, label):
    pg.evaluate('window.scrollTo(0, 0)')
    r = axe(pg)
    ok(not r['violations'], 'axe, %s: no violations%s' % (label, '' if not r['violations'] else ' -> ' + '; '.join('%s x%d (%s) %s' % (v['id'], v['n'], v['impact'], v['ex'][0]) for v in r['violations'])))
    for v in r['incomplete']: print('NOTE axe could not decide %s on %s (x%d): %s' % (v['id'], label, v['n'], v['ex'][0][:120]))
    c = pg.evaluate('reqinA11y.contrast()')
    ok(not c['bad'], 'contrast, %s: every text meets 4.5 to 1 (3 to 1 when large)%s' % (label, '' if not c['bad'] else ' -> ' + '; '.join('%s "%s" %s on %s = %s (needs %s)' % (b['el'], b['text'][:30], b['fg'], b['bg'], b['ratio'], b['need']) for b in c['bad'][:3])))
    ok(c['checked'] > 0 and not c['unknown'], 'contrast, %s: the background behind every text could be measured (%d checked)%s' % (label, c['checked'], '' if not c['unknown'] else ' -> ' + '; '.join('%s "%s" %s' % (u['el'], u['text'][:25], u['why']) for u in c['unknown'][:3])))
    n = pg.evaluate('reqinA11y.nonText()')
    ok(not n['bad'], 'fields, %s: the edge or fill of every field stands out 3 to 1%s' % (label, '' if not n['bad'] else ' -> ' + json.dumps(n['bad'][:2])))
    p = pg.evaluate('reqinA11y.pointerOnly()')
    ok(not p, 'keyboard, %s: nothing reacts to a click that the keyboard cannot reach%s' % (label, '' if not p else ' -> ' + '; '.join(p[:3])))
    h = pg.evaluate('reqinA11y.hiddenStops()')
    ok(not h, 'keyboard, %s: no Tab stop is invisible%s' % (label, '' if not h else ' -> ' + '; '.join(h[:3])))

PAGES = [('Home', 'Home'), ('Review queue', 'Review queue'), ('All requirements', 'All requirements'), ('Overview', 'Overview'), ('The V', 'The V'), ('Results and grade', 'Results and grade'),
         ('Methods and metrics', 'Methods and metrics'), ('Label pairs', 'Label pairs'), ('Decisions and audit', 'Decisions and audit'), ('Sign-off policy', 'Sign-off policy'), ('AI use', 'AI use'), ('Export to documents', 'Export to documents')]

with session(W, 1000) as (pg, errs):
    pg.add_script_tag(path=AXE); pg.add_script_tag(path=PAGEJS)
    # ---- the entry pages
    ok(pg.title() == 'Open a requirements project · Requirements Consolidator', 'title: the entry page says what it is (%r)' % pg.title())
    ok(pg.locator('main').count() == 1 and pg.locator('h1').count() == 1, 'landmarks: the entry page has one main landmark and one heading')
    ok(pg.locator('[role="status"]').first.inner_text().strip() == 'Now showing: Open a requirements project', 'screen reader: the entry page is announced')
    sweep(pg, 'entry page')
    open_sample(pg)
    ok(pg.locator('main').count() == 1 and pg.locator('h1').count() == 1, 'landmarks: the import page has one main landmark and one heading')
    ok(pg.title().startswith('Map fields and choose scope'), 'title: the import page says what it is (%r)' % pg.title())
    sweep(pg, 'import page')
    import_it(pg)

    # ---- every page: the title, the landmarks, one heading, the current page, and a screen reader is told when the page changes
    for label, name in PAGES:
        nav(pg, label)
        f = pg.evaluate("""() => ({ title: document.title, h1: Array.from(document.querySelectorAll('h1')).map((e) => e.textContent.trim()), main: document.querySelectorAll('main').length,
          nav: Array.from(document.querySelectorAll('nav')).map((e) => e.getAttribute('aria-label')), cur: Array.from(document.querySelectorAll('[aria-current="page"]')).map((e) => e.textContent.trim()),
          say: (document.querySelector('[role="status"]') || {}).textContent, skip: document.querySelectorAll('a.skip-link').length })""")
        ok(f['title'] == name + ' · Requirements Consolidator', 'title: %s is in the tab title (%r)' % (name, f['title']))
        ok(f['main'] == 1 and len(f['h1']) == 1 and f['nav'] == ['Main'] and f['skip'] == 1, 'landmarks: %s has one main landmark, one heading, a named menu and a skip link' % name)
        ok(len(f['cur']) == 1 and f['cur'][0].startswith(name), 'menu: %s is the one current page' % name)
        ok((f['say'] or '').strip() == 'Now showing: ' + name, 'screen reader: a change to %s is announced' % name)
        sweep(pg, name)

    # ---- states that open more of the page
    nav(pg, 'Review queue'); open_cluster(pg, 'CL-050'); sweep(pg, 'a cluster open for review')
    pg.get_by_role('button', name='Ask the assistant').first.click(); pg.wait_for_timeout(400); sweep(pg, 'the assistant open')
    pg.get_by_role('button', name='Close the assistant').click(); pg.wait_for_timeout(300)
    nav(pg, 'All requirements'); pg.locator('main button[aria-pressed]').filter(has_text=re.compile(r'^\s*REQ-')).first.click(); pg.wait_for_timeout(400); sweep(pg, 'one requirement open')
    nav(pg, 'Methods and metrics')
    if pg.get_by_role('button', name=re.compile('table', re.I)).count(): pg.get_by_role('button', name=re.compile('table', re.I)).first.click(); pg.wait_for_timeout(300); sweep(pg, 'Methods as a table')
    who(pg, 'Morgan'); nav(pg, 'AI use')
    pg.get_by_role('button', name='Change the data sheet').click(); pg.wait_for_timeout(300); sweep(pg, 'the AI data sheet form')
    nav(pg, 'Label pairs'); sweep(pg, 'Label pairs, as the lead')
    pg.get_by_role('button', name='Glossary and help').first.click(); pg.wait_for_timeout(300); sweep(pg, 'the glossary')

    # ---- the keyboard: from the top of the page
    nav(pg, 'Home'); pg.reload(); pg.wait_for_timeout(1500)
    pg.add_script_tag(path=AXE); pg.add_script_tag(path=PAGEJS)
    if pg.get_by_role('button', name='Open the sample project').count():
        open_sample(pg); import_it(pg)
    pg.evaluate('document.activeElement && document.activeElement.blur()')
    pg.keyboard.press('Tab')
    first = pg.evaluate("() => { const e = document.activeElement; return { cls: e.className, text: e.textContent.trim() }; }")
    ok('skip-link' in first['cls'] and first['text'] == 'Skip to the main content', 'keyboard: the first Tab stop is the skip link (%r)' % first)
    ok(pg.evaluate("() => { const r = document.activeElement.getBoundingClientRect(); return r.top >= 0 && r.left >= 0 && r.width > 40; }"), 'keyboard: the skip link is on screen while it has focus')
    pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
    ok(pg.evaluate("document.activeElement && document.activeElement.id") == 'main-content', 'keyboard: the skip link moves focus to the main content')
    pg.keyboard.press('Tab')
    nxt = pg.evaluate("() => { const e = document.activeElement; return { inMain: !!e.closest('#main-content'), text: (e.getAttribute('aria-label') || e.textContent).trim().slice(0, 40) }; }")
    ok(nxt['inMain'], 'keyboard: the next Tab stop after skipping is inside the main content (%r)' % nxt['text'])
    # walk the page: every stop is seen, has a visible focus ring, is not hidden or covered by the sticky bar, and the focus never gets stuck
    def walk(label, limit):
        want = pg.evaluate("""() => Array.from(document.body.querySelectorAll('a[href],button,input:not([type=hidden]),select,textarea,summary,[tabindex]')).filter((e) => !e.disabled && e.tabIndex >= 0 && getComputedStyle(e).visibility !== 'hidden' && e.getBoundingClientRect().width > 0 && !e.closest('[aria-hidden="true"]')).length""")
        pg.evaluate("() => { window.scrollTo(0, 0); document.body.tabIndex = -1; document.body.focus(); document.body.removeAttribute('tabindex'); }"); seen = []; stuck = 0; noring = []; offscreen = []; covered = []
        for i in range(limit):
            pg.keyboard.press('Tab')
            s = pg.evaluate("""() => { const e = document.activeElement, cs = getComputedStyle(e), r = e.getBoundingClientRect();
              const mx = Math.min(Math.max(r.left + r.width / 2, 1), innerWidth - 1), my = Math.min(Math.max(r.top + Math.min(r.height / 2, 20), 1), innerHeight - 1), top = document.elementFromPoint(mx, my);
              return { key: e.tagName + '|' + (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 30) + '|' + Math.round(r.top) + '|' + Math.round(r.left),
                ring: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) >= 2) || (cs.boxShadow !== 'none'), onscreen: r.width > 0 && r.height > 0 && r.right > 0 && r.bottom > 0 && r.left < innerWidth && r.top < innerHeight,
                covered: !!top && !e.contains(top) && !top.contains(e), by: top ? top.tagName + '.' + top.className : '', body: e === document.body }; }""")
            if s['body']: break
            if seen and seen[-1] == s['key']: stuck += 1
            seen.append(s['key'])
            if not s['ring']: noring.append(s['key'])
            if not s['onscreen']: offscreen.append(s['key'])
            if s['covered']: covered.append(s['key'] + ' under ' + s['by'])
        ok(len(set(seen)) >= min(want, limit) - 1, 'keyboard, %s: Tab reaches every control (%d of %d)' % (label, len(set(seen)), want))
        ok(stuck == 0, 'keyboard, %s: the focus never sticks in one place' % label)
        ok(not noring, 'keyboard, %s: every Tab stop has a visible focus ring%s' % (label, '' if not noring else ' -> ' + '; '.join(noring[:3])))
        ok(not offscreen, 'keyboard, %s: every Tab stop is scrolled into view%s' % (label, '' if not offscreen else ' -> ' + '; '.join(offscreen[:3])))
        ok(not covered, 'keyboard, %s: no Tab stop is hidden behind the sticky bar or a panel%s' % (label, '' if not covered else ' -> ' + '; '.join(covered[:3])))
    walk('Home', 70)
    # a keyboard walks into the review page and does the main thing without a mouse
    nav(pg, 'Review queue'); pg.keyboard.press('Tab')
    ok(pg.evaluate("document.activeElement !== document.body"), 'keyboard: after choosing a page with the keyboard, Tab continues from there')
    open_cluster(pg, 'CL-050')
    walk('a cluster open for review', 90)
    # the sheet that lines up wordings traps the focus, closes on Escape and gives the focus back
    opener = pg.locator('#al-open')
    if opener.count():
        opener.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
        ok(pg.locator('[role="dialog"][aria-modal="true"]').count() == 1 and pg.evaluate("!!document.activeElement.closest('[role=dialog]')"), 'dialog: opening the sheet puts the focus inside it')
        for _ in range(40): pg.keyboard.press('Tab')
        ok(pg.evaluate("!!document.activeElement.closest('[role=dialog]')"), 'dialog: Tab cannot leave the sheet')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        ok(pg.locator('[role="dialog"]').count() == 0 and pg.evaluate("document.activeElement.id") == 'al-open', 'dialog: Escape closes the sheet and gives the focus back to the button that opened it')
    else:
        ok(False, 'dialog: the review page has the button that opens the sheet')

    # ---- the colours of the charts: tellable apart by people who see colour differently, and every mark stands out from the page
    MARKS = """() => Array.from(document.querySelectorAll('[data-chart-mark]')).filter((e) => e.getBoundingClientRect().width > 1).map((e) => {
      const cs = getComputedStyle(e), rgb = (s) => { const m = /rgba?\\((\\d+)[ ,]+(\\d+)[ ,]+(\\d+)(?:[ ,\\/]+([\\d.]+))?\\)/.exec(s || ''); return m ? { hex: '#' + [m[1], m[2], m[3]].map((v) => (+v).toString(16).padStart(2, '0')).join(''), a: m[4] === undefined ? 1 : +m[4] } : null; };
      const img = rgb(cs.backgroundImage), fill = rgb(cs.backgroundColor), edge = rgb(cs.borderTopColor);
      return { chart: e.getAttribute('data-chart-mark'), label: (e.parentElement.textContent || '').trim().replace(/\\s+/g, ' '), fill: fill && fill.a > 0 ? fill.hex : null, hatch: cs.backgroundImage !== 'none' ? (img || {}).hex : null,
               outline: (!fill || fill.a === 0) && cs.backgroundImage === 'none' && parseFloat(cs.borderTopWidth) > 0 && edge ? edge.hex : null }; })"""
    for label, chart, count in [('All requirements', 'status map', 5), ('Methods and metrics', 'with and without AI', 2)]:
        nav(pg, label)
        marks = [m for m in pg.evaluate(MARKS) if m['chart'] == chart]
        ok(len(marks) == count, 'chart colours: %s shows %d marks in its key (%d)' % (chart, count, len(marks)))
        ok(all(m['label'] for m in marks), 'chart colours: %s, every mark in the key has a name beside it' % chart)
        fills = [m['hatch'] or m['fill'] for m in marks if m['hatch'] or m['fill']]
        outlines = [m['outline'] for m in marks if m['outline']]
        probs, notes = chart_colours.check(fills, '#FFFFFF', outlines)
        ok(not probs, 'chart colours: %s, the colours are tellable apart with red-green colour blindness and stand out from the page%s' % (chart, '' if not probs else ' -> ' + '; '.join(probs[:3])))
        for n in notes: print('NOTE', chart, n)
        if chart == 'status map':
            ok(sum(1 for m in marks if m['hatch']) == 1 and sum(1 for m in marks if m['outline']) == 1, 'chart colours: status map, two of the marks differ by pattern as well as colour (a hatched one and a hollow one)')

    # ---- a screen reader's view of the pictures
    for label in ['The V', 'Overview', 'Methods and metrics', 'Results and grade']:
        nav(pg, label)
        r = pg.evaluate("""() => Array.from(document.querySelectorAll('main svg')).filter((s) => !s.closest('[aria-hidden="true"]') && s.getAttribute('aria-hidden') !== 'true' && s.getBoundingClientRect().width > 14).filter((s) => {
          const name = s.getAttribute('aria-label') || (s.querySelector('title') || {}).textContent || s.getAttribute('aria-labelledby');
          return !(s.getAttribute('role') === 'img' && name) && !s.closest('button,a'); }).map((s) => (s.parentElement.getAttribute('aria-label') || s.parentElement.textContent || '').trim().slice(0, 40))""")
        ok(not r, 'screen reader: %s, every picture is hidden from a screen reader or has a name%s' % (label, '' if not r else ' -> ' + '; '.join(r[:3])))

    # ---- reduced motion
    pg.emulate_media(reduced_motion='reduce')
    for label in ['Home', 'Review queue', 'Methods and metrics']:
        nav(pg, label)
        r = pg.evaluate("""() => ({ running: document.getAnimations().filter((a) => a.playState === 'running' && a.effect && a.effect.getTiming().duration > 0 && a.effect.getTiming().iterations > 1).length,
          slow: Array.from(document.querySelectorAll('button,a,input')).filter((e) => parseFloat(getComputedStyle(e).transitionDuration) > 0).length })""")
        ok(r['running'] == 0 and r['slow'] == 0, 'motion: with reduced motion asked for, nothing animates or fades on %s (%s)' % (label, r))
    pg.emulate_media(reduced_motion='no-preference')

    # ---- reflow at 320 pixels (a 1280 pixel page at 400 percent): nothing is cut off and nothing needs sideways scrolling in two directions
    pg.set_viewport_size({'width': 320, 'height': 800}); pg.wait_for_timeout(300)
    for label, name in PAGES:
        nav(pg, label)
        w = pg.evaluate('[document.documentElement.scrollWidth, document.documentElement.clientWidth]')
        ok(w[0] <= w[1], 'reflow: %s at 320 pixels needs no sideways scrolling of the page (%s vs %s)' % (name, w[0], w[1]))
    pg.set_viewport_size({'width': W, 'height': 1000})
    ok(not bad(errs), 'no console errors: %s' % bad(errs)[:3])

print('\n%d failed' % len(fails) if fails else '\nALL PASS')
sys.exit(1 if fails else 0)
