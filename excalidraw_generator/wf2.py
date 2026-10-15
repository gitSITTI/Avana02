"""Shared helpers for the second round of boards (scale, lenses, groups, assistant, pipelines)."""
from wf import *
from wf_a import notes
from wf_b import tokw, guard_row, LANE_FILL, REL_FILL, GUARDS
from flows import box, mark, SRC_F, MECH_F, AI_F, HUM_F, GUARD_F
from exc import Doc, INK

CHAT = '#0B6E99'   # assistant mark colour (speech-bubble mark)
CHAT_F = '#e3f4fb'


def new_frame(d, ox, oy, w, h, name, bg=GREY):
    d.frame_begin(ox, oy, w, h, name)
    s = Scr(d, ox, oy)
    s.r(0, 0, w, h, fill=bg, stroke=bg, rounded=False)
    return s


def para(s, x, y, text, w, fs=10, color=DARK, **kw):
    wrapped = s.d.wrap(text, w, fs)
    s.t(x, y, wrapped, fs=fs, color=color, **kw)
    return y + (wrapped.count('\n') + 1) * fs * 1.25


def lines(d, text, w, fs):
    return d.wrap(text, w, fs).count('\n') + 1


def table(s, x, y, widths, head, rows, fs=10, head_fill=DARK, pad=8, row_fills=None, bold_first=False, minh=26):
    """Draw a wrapped-text table. rows: list of list of str (or (str, fill) tuples). Returns y below the table."""
    W = sum(widths)
    s.r(x, y, W, 26, fill=head_fill, stroke=head_fill, rounded=False)
    cx = x
    for wd, h_ in zip(widths, head):
        s.t(cx + pad, y + 7, h_, fs=fs - 1, color='#ffffff', family=3)
        cx += wd
    y += 26
    for ri, row in enumerate(rows):
        wrapped = []
        for wd, cell in zip(widths, row):
            txt = cell[0] if isinstance(cell, tuple) else cell
            wrapped.append(s.d.wrap(txt, wd - 2 * pad, fs))
        n = max(w_.count('\n') + 1 for w_ in wrapped)
        h = max(minh, n * fs * 1.25 + 14)
        base = '#ffffff' if ri % 2 == 0 else '#F8F9FA'
        s.r(x, y, W, h, fill=base, stroke='#e9ecef', rounded=False)
        cx = x
        for ci, (wd, cell, w_) in enumerate(zip(widths, row, wrapped)):
            if isinstance(cell, tuple) and cell[1]:
                s.r(cx + 2, y + 2, wd - 4, h - 4, fill=cell[1], stroke=cell[1], rounded=False)
            s.t(cx + pad, y + 7, w_, fs=fs, color=INK if (ci == 0 and bold_first) else DARK)
            cx += wd
        y += h
    return y


def avatar(s, x, y, ini, fill=BLUE_BG, r=22):
    s.shape('ellipse', x, y, r, r, ini, fs=8, fill=fill, stroke=INK, pad=0)


def sign_dots(s, x, y, states):
    """Four tiny lens markers: S P U N, filled when signed, dashed when pending, X when changes requested."""
    for i, (lab, st) in enumerate(zip('SPUN', states)):
        fill = {'signed': GREEN_BG, 'pending': '#ffffff', 'changes': RED_BG, 'na': GREY, 'stale': AMBER_BG}[st]
        s.shape('ellipse', x + i * 16, y, 14, 14, lab, fs=7, fill=fill, stroke=HUM if st == 'signed' else (RED if st == 'changes' else SOFT), dash=(st in ('pending', 'na')), pad=0)


def checkbox(s, x, y, checked=False, label=None, fs=9):
    s.r(x, y, 12, 12, fill='#ffffff', stroke=INK, sw=1.5)
    if checked:
        s.poly([(x + 2.5, y + 6.5), (x + 5, y + 9), (x + 9.5, y + 3.5)], typ='line', stroke=INK, sw=2)
    if label:
        s.t(x + 18, y - 1, label, fs=fs, color=DARK)


def kv(s, x, y, k, v, kw=110, fs=9, vcolor=INK):
    s.t(x, y, k, fs=fs, color=SOFT)
    s.t(x + kw, y, v, fs=fs, color=vcolor)


def bar_h(s, x, y, w, frac, label=None, value=None, fill='#2A78D6', h=10):
    s.r(x, y, w, h, fill='#d0e0ff', stroke='#d0e0ff', rounded=False)
    s.r(x, y, max(2, w * frac), h, fill=fill, stroke=fill, rounded=False)
    if label:
        s.t(x - 4 - len(label) * 5.2, y - 1, label, fs=9, color=DARK)
    if value:
        s.t(x + w + 6, y - 1, value, fs=9, color=INK, family=3)


# ---------------------------------------------------------------- shell with a selectable lens
LENS = ['Systems engineer', 'Process engineer', 'UI/UX engineer', 'New user']
LCOL = [BLUE_BG, VIOLET_BG, AMBER_BG, GREEN_BG]
LSHORT = ['SE', 'PE', 'UX', 'NU']
BANNER = 'Suggestions are proposals. Each stays a draft until the lenses your policy requires have signed. Nothing is written back to the source model.'


def sidebar2(s, h, active, lens=0, labels=None):
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
    s.t(14, 256, 'YOUR LENS (FROM YOUR LOGIN)', fs=7, color='#adb5bd', family=3)
    for i, lab in enumerate(LENS):
        on = (i == lens)
        s.r(10, 270 + i * 28, 130, 24, lab, fill='#ffffff' if on else 'transparent', stroke='#6c757d', color=INK if on else '#868e96', fs=9, align='left', pad=8, dash=not on)
    s.t(14, 386, 'Dashed lenses are not yours.', fs=8, color='#868e96')
    s.r(10, h - 70, 130, 24, 'Glossary and help', stroke='#6c757d', color='#dee2e6', fs=9, align='left', pad=8)
    s.t(18, h - 36, 'Close project', fs=9, color='#adb5bd')


def shell2(s, w, h, active, lens=0, labels=None):
    sidebar2(s, h, active, lens, labels)
    cells = ['PROJECT\nReference air vehicle', 'SOURCE\nAPI or KPAR', 'BASELINE\nNone, pre-baseline', 'STATUS\nDRAFT', 'REVIEWING AS\n' + LENS[lens]]
    cw = (w - 150) / 5
    for i, c in enumerate(cells):
        s.r(150 + i * cw, 0, cw, 36, fill='#ffffff', stroke='#dee2e6', rounded=False)
        a, b = c.split('\n')
        s.t(158 + i * cw, 5, a, fs=7, color=SOFT, family=3)
        s.t(158 + i * cw, 18, b, fs=9, color=INK)
    mini_vee(s, w - 72, 2)
    s.r(150, 36, w - 150, 24, fill=AMBER_BG, stroke='#f1c40f', rounded=False)
    s.chip(160, 41, 34, 14, 'DRAFT', fill='#ffffff', stroke=DARK, fs=8)
    s.t(202, 42, BANNER, fs=8, color='#5c4400')
    return 168, 76


def chk_list(s, x, y, w, items, fs=9, gap=8):
    """Checklist with state chips. items: (state, text). Returns y below."""
    fills = {'Pass': GREEN_BG, 'Needs you': AMBER_BG, 'Blocked': RED_BG, 'Done': GREEN_BG, 'Open': '#ffffff'}
    for st, txt in items:
        wr = s.d.wrap(txt, w - 84, fs)
        n = wr.count('\n') + 1
        s.chip(x, y, 66, 16, st, fill=fills.get(st, GREY), fs=8, dash=(st == 'Open'))
        s.t(x + 76, y + 1, wr, fs=fs, color=DARK)
        y += max(24, n * fs * 1.25 + gap)
    return y
