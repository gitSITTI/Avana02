"""Wireframe widgets on top of exc.Doc. All coordinates are local to a frame origin."""
from exc import Doc, INK

GREY = '#f1f3f5'
MID = '#ced4da'
LINE = '#adb5bd'
DARK = '#343a40'
SOFT = '#868e96'
ACC = '#1A4DB5'
ACC_BG = '#d0e0ff'
RED = '#e03131'
AMBER_BG = '#ffec99'
GREEN_BG = '#b2f2bb'
RED_BG = '#ffc9c9'
BLUE_BG = '#a5d8ff'
VIOLET_BG = '#eebefa'
MECH = '#34424F'
AIC = '#8B1F6B'
HUM = '#1B6B3A'


class Scr:
    def __init__(self, d: Doc, ox, oy):
        self.d, self.ox, self.oy = d, ox, oy

    def r(self, x, y, w, h, label=None, **kw):
        kw.setdefault('stroke', LINE)
        return self.d.rect(self.ox + x, self.oy + y, w, h, label, **kw)

    def t(self, x, y, s, **kw):
        return self.d.text(self.ox + x, self.oy + y, s, **kw)

    def shape(self, typ, x, y, w, h, label=None, **kw):
        return self.d.shape(typ, self.ox + x, self.oy + y, w, h, label, **kw)

    def poly(self, pts, **kw):
        return self.d.poly([(self.ox + a, self.oy + b) for a, b in pts], **kw)

    def line(self, pts, **kw):
        return self.d.line([(self.ox + a, self.oy + b) for a, b in pts], **kw)

    # ---- widgets ----
    def card(self, x, y, w, h, fill='#ffffff', dash=False):
        return self.r(x, y, w, h, fill=fill, dash=dash)

    def caps(self, x, y, s, color=SOFT):
        return self.t(x, y, s, fs=9, color=color, family=3)

    def h1(self, x, y, s, fs=22):
        return self.t(x, y, s, fs=fs, family=2, color=INK)

    def txt(self, x, y, s, fs=11, color=DARK, **kw):
        return self.t(x, y, s, fs=fs, color=color, **kw)

    def ph(self, x, y, w, n=3, gap=10, h=5, fracs=(1, .92, .7, .85, .6)):
        for i in range(n):
            self.r(x, y + i * gap, w * fracs[i % len(fracs)], h, fill=MID, stroke=MID, rounded=False)

    def btn(self, x, y, w, h, label, primary=False, disabled=False, fs=11):
        if primary:
            return self.r(x, y, w, h, label, fill=ACC if not disabled else '#a5b4d8', stroke=ACC, color='#ffffff', fs=fs)
        return self.r(x, y, w, h, label, fill='#ffffff', stroke=SOFT, color=DARK, fs=fs, dash=disabled)

    def chip(self, x, y, w, h, label, fill=GREY, stroke=LINE, fs=9, dash=False, color=DARK):
        return self.r(x, y, w, h, label, fill=fill, stroke=stroke, fs=fs, pad=3, dash=dash, color=color)

    def bar(self, x, y, w, frac, h=8):
        self.r(x, y, w, h, fill='#d0e0ff', stroke='#d0e0ff', rounded=False)
        self.r(x, y, max(3, w * frac), h, fill='#2A78D6', stroke='#2A78D6', rounded=False)

    def prov(self, x, y, kind, label=None, fs=9):
        """Provenance mark: square = mechanical, diamond = AI, circle = human."""
        if kind == 'mech':
            self.r(x, y + 1, 9, 9, fill=MECH, stroke=MECH, rounded=False)
        elif kind == 'ai':
            self.shape('diamond', x - 1, y, 11, 11, fill=AIC, stroke=AIC)
        else:
            self.shape('ellipse', x, y, 10, 10, fill=HUM, stroke=HUM)
        if label:
            self.t(x + 14, y - 1, label, fs=fs, color=DARK)

    def num(self, x, y, n):
        e = self.shape('ellipse', x, y, 20, 20, str(n), fs=11, fill=RED, stroke=RED, color='#ffffff', pad=0)
        return e

    def check(self, x, y):
        self.shape('ellipse', x, y, 14, 14, fill=GREEN_BG, stroke=HUM)
        self.poly([(x + 3.5, y + 7.5), (x + 6, y + 10), (x + 10.5, y + 4.5)], typ='line', stroke=HUM, sw=2)

    def tokens(self, x, y, words, fs=11):
        """Draw a line of words; words are (text, kind) with kind in None,num,modal,neg,cond."""
        fills = {'num': '#ffe0ad', 'modal': '#d5e3ff', 'neg': '#ffd3ce', 'cond': '#e8deff'}
        cx = x
        for w, k in words:
            wd = len(w) * fs * 0.56 + 6
            if k:
                self.r(cx - 2, y - 2, wd, fs + 6, fill=fills[k], stroke=fills[k], rounded=False)
            self.t(cx, y, w, fs=fs, family=2, color=DARK)
            cx += wd + 3
        return cx


def sidebar(s: Scr, h, active, labels=None):
    labels = labels or ['Overview', 'Review queue', 'Methods and metrics', 'Audit log', 'Export to documents']
    s.r(0, 0, 150, h, fill=DARK, stroke=DARK, rounded=False)
    s.t(14, 12, 'Consolidator', fs=12, color='#ffffff')
    s.r(10, 36, 130, 40, fill='#495057', stroke='#495057')
    s.t(18, 42, 'PROJECT', fs=7, color='#adb5bd', family=3)
    s.t(18, 54, 'Reference air vehicle', fs=9, color='#ffffff')
    for i, lab in enumerate(labels):
        y = 90 + i * 30
        if lab == active:
            s.r(8, y, 134, 26, lab, fill='#1f4e8f', stroke='#1f4e8f', color='#ffffff', fs=10, align='left', pad=10)
        else:
            s.t(18, y + 7, lab, fs=10, color='#dee2e6')
    s.t(14, 256, 'REVIEWING AS', fs=7, color='#adb5bd', family=3)
    for i, lab in enumerate(['Systems engineer', 'Process engineer', 'UI/UX engineer', 'New user']):
        s.r(10, 270 + i * 28, 130, 24, lab, fill='#ffffff' if i == 0 else 'transparent', stroke='#6c757d', color=INK if i == 0 else '#dee2e6', fs=9, align='left', pad=8)
    s.r(10, h - 70, 130, 24, 'Glossary and help', stroke='#6c757d', color='#dee2e6', fs=9, align='left', pad=8)
    s.t(18, h - 36, 'Close project', fs=9, color='#adb5bd')


def shell(s: Scr, w, h, active, view_title=None):
    """Sidebar + title block + draft banner. Returns the content origin (x, y)."""
    sidebar(s, h, active)
    cells = ['PROJECT\nReference air vehicle', 'SOURCE\nAPI or KPAR', 'BASELINE\nNone, pre-baseline', 'STATUS\nDRAFT', 'REVIEWING AS\nSystems engineer']
    cw = (w - 150) / 5
    for i, c in enumerate(cells):
        s.r(150 + i * cw, 0, cw, 36, fill='#ffffff', stroke='#dee2e6', rounded=False)
        a, b = c.split('\n')
        s.t(158 + i * cw, 5, a, fs=7, color=SOFT, family=3)
        s.t(158 + i * cw, 18, b, fs=9, color=INK)
    s.r(150, 36, w - 150, 24, fill=AMBER_BG, stroke='#f1c40f', rounded=False)
    s.chip(160, 41, 34, 14, 'DRAFT', fill='#ffffff', stroke=DARK, fs=8)
    s.t(202, 42, 'Suggestions are proposals. Each stays a draft until all four lenses sign off. Nothing is written back to the source model.', fs=8, color='#5c4400')
    return 168, 76
