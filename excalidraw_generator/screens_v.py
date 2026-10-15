"""Board 11: the engineering V as the app shows it. A second worked example of adding screens (see EXCALIDRAW_GUIDE.md, recipe A).

Numbers on these screens are the prototype's seeded SAMPLE values (levels, methods and items are given to each requirement for the demo).
Each function draws one frame at (ox, oy) and returns the notes boards_05_09.build_board places beside it."""
from wf2 import *  # noqa: F401,F403  (Doc, Scr, palette, new_frame, para, table, chk_list, kv ...)
from flows import box, mark, SRC_F, MECH_F, AI_F, HUM_F, GUARD_F  # noqa: F401

LEFT = '#1C5CAB'          # left leg: circles
LEFT_MID = '#7FB0EE'
RIGHT = '#1B6B3A'         # right leg: squares
RIGHT_MID = '#8FCBA6'
RIGHT_LOW = '#FFD9A8'
LEVELS = [('Stakeholder needs', 'Validation', 'Needs'), ('System requirements', 'System verification', 'System'),
          ('Subsystem requirements', 'Subsystem verification', 'Subsystem'), ('Component requirements', 'Component verification', 'Component')]
# the seeded sample: requirements, after the decisions so far, clusters, decided, traced, items to re-point, methods (T, A, I, D, none), state
SAMPLE = [dict(reqs=63, after=58, clusters=9, decided=2, traced=55, re=11, m=(14, 12, 9, 25, 3), state='Still being consolidated'),
          dict(reqs=425, after=397, clusters=87, decided=22, traced=372, re=40, m=(101, 99, 97, 107, 21), state='Still being consolidated'),
          dict(reqs=597, after=567, clusters=122, decided=30, traced=513, re=44, m=(115, 168, 137, 139, 38), state='Still being consolidated'),
          dict(reqs=163, after=159, clusters=34, decided=9, traced=132, re=4, m=(42, 20, 48, 42, 11), state='Still being consolidated')]


def vee_glyph(s, x, y, w=300, nums=True, ring=(), size=None):
    """The small V: circles down the left leg (decided), squares up the right leg (traced), a diamond at the bottom (design and build).
    The spacing follows the width so the shapes never overlap, from a 330 px hero to a 76 px header button."""
    size = size or (22 if w >= 300 else 16 if w >= 180 else 8)
    margin = size / 2 + 3
    dx = (w / 2 - margin - size * 1.4) / 3
    dy = dx * 0.8
    pts_l = [(x + margin + dx * k, y + margin + dy * k) for k in range(4)]
    pts_r = [(x + w - margin - dx * k, y + margin + dy * k) for k in range(4)]
    vx, vy = x + w / 2, y + margin + dy * 3 + dy + size * 0.3
    s.line(pts_l + [(vx, vy)] + pts_r[::-1], stroke=SOFT, sw=2 if size >= 14 else 1.5)
    fs = 10 if size >= 20 else 8
    for k, (cx, cy) in enumerate(pts_l):
        hi = (k + 1) in ring
        s.shape('ellipse', cx - size / 2, cy - size / 2, size, size, str(k + 1) if nums else None, fs=fs, fill='#ffffff', stroke=LEFT, sw=3 if hi else 2, pad=0)
        if hi:
            s.shape('ellipse', cx - size / 2 - 5, cy - size / 2 - 5, size + 10, size + 10, stroke=RED, sw=2)
    for k, (cx, cy) in enumerate(pts_r):
        hi = (k + 1) in ring
        s.r(cx - size / 2, cy - size / 2, size, size, str(k + 1) if nums else None, fs=fs, fill=RIGHT_MID, stroke=RIGHT, sw=3 if hi else 2, rounded=False, pad=0)
        if hi:
            s.r(cx - size / 2 - 5, cy - size / 2 - 5, size + 10, size + 10, stroke=RED, sw=2, rounded=False)
    s.shape('diamond', vx - size * 0.45, vy - size * 0.45, size * 0.9, size * 0.9, fill=MID, stroke=SOFT, sw=2)


def legend(s, x, y):
    s.shape('ellipse', x, y, 11, 11, fill='#ffffff', stroke=LEFT, sw=2)
    s.t(x + 18, y - 1, 'left leg: what we require. Fuller means more decided.', fs=9, color=DARK)
    s.r(x, y + 20, 11, 11, fill=RIGHT_MID, stroke=RIGHT, sw=2, rounded=False)
    s.t(x + 18, y + 19, 'right leg: how we show it. Fuller means more traced.', fs=9, color=DARK)


def v1_the_v_page(d, ox, oy):
    W, H = 1000, 1060
    s = new_frame(d, ox, oy, W, H, '11.1 · The engineering V: one page for every level')
    s.t(40, 28, 'THE V   /   LEFT LEG   /   BETWEEN THE LEGS   /   RIGHT LEG', fs=10, color=SOFT, family=3)
    s.h1(40, 56, 'The engineering V', fs=28)
    para(s, 40, 100, 'Each level of requirements on the left is checked at the matching level on the right. Consolidating requirements changes the left side. This page shows what that does to the right side, so nothing is left with nothing to verify it.', 520, fs=11)
    vee_glyph(s, 640, 24, 300)
    legend(s, 40, 160)
    s.chip(40, 196, 920, 28, 'Sample values. Levels, verification methods and verification items are sample values given to each requirement for this demo.', fill=AMBER_BG, stroke='#f1c40f', fs=10)
    cards = [('LEFT LEG: WHAT WE REQUIRE', '63 of 252', 'clusters with a standing decision', '1,248 requirements now, 1,181 after your decisions. 8 more clusters have a stale or disputed decision, which does not count.', None),
             ('BETWEEN THE LEGS: TO CARRY OVER', '99', 'verification items must move to the requirement that takes the place of one removed, before export', None, 'Open Export'),
             ('RIGHT LEG: HOW WE SHOW IT', '1,072 of 1,248', 'requirements fully traced', '176 requirements with no method or no verification item (73 have no method, 163 no item)', None)]
    for i, (cap, big, sub, extra, btn) in enumerate(cards):
        x = 40 + i * 312
        s.card(x, 244, 296, 150)
        s.caps(x + 16, 258, cap)
        s.t(x + 16, 276, big, fs=24, color=INK)
        yy = para(s, x + 16, 312, sub, 264, fs=10, color=DARK)
        if extra:
            para(s, x + 16, yy + 4, extra, 264, fs=9, color=SOFT)
        if btn:
            s.btn(x + 16, 352, 100, 28, btn, fs=10)
    s.card(40, 412, 920, 600)
    s.t(60, 426, 'Level by level', fs=16, color=INK)
    s.t(60, 450, 'Read down the left, then up the right. The dashed line joins each level to the check that shows it is met.', fs=10, color=DARK)
    for i, ((lname, ver, short), v) in enumerate(zip(LEVELS, SAMPLE)):
        y = 486 + i * 118
        ind = i * 24
        lx, rx, cw = 60 + ind, 940 - ind - 300, 300
        s.r(lx, y, cw, 104, fill='#ffffff', stroke=LEFT, sw=2)
        s.shape('ellipse', lx + 12, y + 12, 10, 10, fill=LEFT, stroke=LEFT)
        s.caps(lx + 28, y + 10, f'LEVEL {i + 1}')
        s.t(lx + 12, y + 28, lname, fs=13, color=INK)
        s.t(lx + 12, y + 50, f"{v['reqs']} requirements  ·  {v['after']} after your decisions", fs=9, color=DARK)
        s.bar(lx + 12, y + 70, cw - 24, v['decided'] / v['clusters'], h=8)
        s.t(lx + 12, y + 83, f"{v['decided']} of {v['clusters']} clusters decided", fs=9, color=DARK)
        s.r(rx, y, cw, 104, fill='#ffffff', stroke=RIGHT, sw=2)
        s.r(rx + 12, y + 12, 10, 10, fill=RIGHT, stroke=RIGHT, rounded=False)
        s.caps(rx + 28, y + 10, 'CHECKED BY')
        s.t(rx + 12, y + 28, ver, fs=13, color=INK)
        t_, a_, i_, d_, n_ = v['m']
        s.t(rx + 12, y + 50, f'Test {t_} · Analysis {a_} · Inspection {i_} · Demo {d_} · none {n_}', fs=8.5, color=DARK)
        s.r(rx + 12, y + 70, cw - 24, 8, fill='#D6EBDD', stroke='#D6EBDD', rounded=False)
        s.r(rx + 12, y + 70, (cw - 24) * v['traced'] / v['reqs'], 8, fill=RIGHT, stroke=RIGHT, rounded=False)
        s.t(rx + 12, y + 83, f"{v['traced']} of {v['reqs']} traced  ·  {v['re']} items to re-point", fs=9, color=DARK)
        mx0, mx1 = lx + cw, rx
        s.line([(mx0, y + 52), (mx1, y + 52)], stroke=SOFT, sw=2, dash=True)
        pw = 96
        s.r((mx0 + mx1) / 2 - pw / 2, y + 36, pw, 32, v['state'], fill=GREY, stroke=LINE, fs=8, pad=3)
    s.r(300, 962, 400, 36, 'Bottom of the V · Design and build · outside this app', fill='#f8f9fa', stroke=SOFT, dash=True, fs=10)
    for k, (x, y) in enumerate([(12, 80), (12, 244), (12, 486), (12, 966)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['The glyph is the page in miniature: circles down the left leg, squares up the right, a diamond for the build in between. Shape carries the meaning, so it still reads in greyscale. The numbers beside each level repeat it.',
            'Three numbers first: how much of the left leg is decided, what must move between the legs, and how much of the right leg is traced. The decided count only counts decisions that stand (stale or disputed ones are held back and said so).',
            'Each level is a pair: the requirements on the left, the check that matches them on the right, joined by a dashed line. The middle chip says in words if the level is in step, needs attention or is still being consolidated.',
            'The app works on the left leg only. It never changes a verification item. It says how many must move to a requirement that survives.']


def v2_where_it_shows(d, ox, oy):
    W, H = 1500, 860
    s = new_frame(d, ox, oy, W, H, '11.2 · The V on every screen')
    s.t(40, 28, 'THE SMALL V TRAVELS WITH YOU: HEADER, HOME, THE CLUSTER YOU ARE LOOKING AT, RESULTS, EXPORT AND THE FILTERS', fs=10, color=SOFT, family=3)
    # a) header
    s.caps(40, 56, 'A · HEADER OF EVERY WORKSPACE SCREEN')
    s.card(40, 76, 1420, 56, fill='#ffffff')
    s.t(60, 96, 'Reference air vehicle  /  Review queue', fs=11, color=INK)
    s.chip(330, 94, 90, 20, 'Whole project', fill=GREY, fs=9)
    s.chip(430, 94, 80, 20, 'Pre-baseline', fill=GREY, fs=9)
    s.r(560, 92, 380, 26, 'Search requirements', fill='#ffffff', stroke=LINE, fs=10, align='left', pad=10, color=SOFT)
    for k, ini in enumerate(['PR', 'JE', 'CW']):
        s.shape('ellipse', 990 + k * 22, 92, 26, 26, ini, fs=8, fill=[VIOLET_BG, AMBER_BG, GREEN_BG][k], stroke=INK, pad=0)
    s.r(1076, 84, 92, 44, fill=GREY, stroke=LINE)
    vee_glyph(s, 1084, 90, 76, nums=False, size=8)
    s.shape('ellipse', 1190, 94, 22, 22, '?', fs=10, stroke=SOFT, pad=0)
    s.btn(1236, 90, 190, 30, 'Ask the assistant', fs=10)
    s.t(1060, 138, 'press it: opens the V page', fs=9, color=RED)
    s.poly([(1120, 140), (1120, 132)], stroke=RED, sw=1.5)
    # b) Home
    s.caps(40, 170, 'B · HOME')
    s.card(40, 190, 680, 160)
    vee_glyph(s, 56, 204, 190, size=16)
    s.t(270, 206, 'Where the work sits in the V', fs=14, color=INK)
    for k, (shape, t) in enumerate([('c', '63 of 252 clusters have a standing decision on the left leg (8 more are held as stale or disputed)'),
                                    ('s', '176 requirements with no verification method or item on the right leg'), ('l', '99 verification items will have to move to a surviving requirement')]):
        yy = 236 + k * 26
        if shape == 'c':
            s.shape('ellipse', 270, yy + 1, 11, 11, fill=LEFT, stroke=LEFT)
        elif shape == 's':
            s.r(270, yy + 1, 11, 11, fill=RIGHT, stroke=RIGHT, rounded=False)
        else:
            s.line([(268, yy + 7), (284, yy + 7)], stroke=SOFT, sw=2, dash=True)
        s.t(292, yy, s.d.wrap(t, 400, 10), fs=10, color=DARK)
    s.btn(270, 312, 100, 26, 'Open the V', fs=10)
    # c) cluster strip, one level and two levels
    s.caps(40, 360, 'C · THE CLUSTER YOU ARE REVIEWING SAYS WHERE IT SITS IN THE V')
    for k, (head, lines_, ring) in enumerate([
            ('Level 3 · Subsystem requirements, checked at subsystem verification',
             '4 verification items are linked across them (M1: 2, M2: 2). A merge moves the items of every wording that goes onto the one that stays.', (3,)),
            ('Spans level 1 (Needs) and level 2 (System)',
             'One of these is the parent of the other, a level up. Link them as parent and child. Merging would leave level 1 with a check that proves nothing. Each stays with its own requirement.', (1, 2))]):
        x = 40 + k * 680
        s.card(x, 380, 660, 130, fill='#F4F7FA')
        vee_glyph(s, x + 12, 394, 190, nums=True, ring=ring, size=16)
        s.t(x + 216, 396, s.d.wrap(head, 420, 11), fs=11, color=INK)
        para(s, x + 216, 430, lines_, 420, fs=10, color=DARK)
    # d) results table
    s.caps(40, 530, 'D · RESULTS: ORIGINAL AND AFTER, BY LEVEL')
    rows = [['1 · Needs', '63', '58', '−5', '11', '8'], ['2 · System', '425', '397', '−28', '40', '53'], ['3 · Subsystem', '597', '567', '−30', '44', '84'],
            ['4 · Component', '163', '159', '−4', '4', '31'], ['All levels', '1,248', '1,181', '−67', '99', '176']]
    table(s, 40, 552, [150, 90, 80, 80, 130, 70], ['LEVEL', 'ORIGINAL', 'AFTER', 'CHANGE', 'ITEMS TO RE-POINT', 'GAPS'], rows, fs=10, bold_first=True, minh=26)
    para(s, 40, 740, '99 verification items sit on requirements your decisions remove or mark superseded. Each has to be pointed at the requirement that takes its place, or the check proves nothing.', 600, fs=9, color=SOFT)
    # e) export
    s.caps(740, 530, 'E · EXPORT')
    s.card(740, 552, 720, 70)
    s.t(760, 566, 'On the V:', fs=11, color=INK)
    s.t(830, 566, s.d.wrap('99 verification items move to a surviving requirement. Most are at level 3.', 400, 11), fs=11, color=DARK)
    s.btn(1290, 576, 150, 28, 'Open the V', fs=10)
    # f) filters
    s.caps(740, 650, 'F · FILTERS: FIND THE WORK AT ONE LEVEL')
    s.card(740, 672, 720, 150)
    s.t(760, 686, 'All requirements', fs=11, color=INK)
    for k, lab in enumerate(['All levels', 'Level 1 · Needs', 'Level 2 · System', 'Level 3 · Subsystem', 'Level 4 · Component']):
        s.chip(760 + k * 134, 712, 126, 24, lab, fill=ACC_BG if k == 3 else '#ffffff', stroke=ACC if k == 3 else LINE, fs=9)
    s.chip(760, 746, 160, 24, 'Verification gaps only', fill=ACC_BG, stroke=ACC, fs=9)
    s.t(940, 750, 'Showing 1 to 25 of 84', fs=10, color=DARK)
    s.t(760, 786, 'Review queue: a "Any V level" menu and a "Still to decide" status, so "Review the open ones" on the V lands on exactly those clusters.', fs=9, color=SOFT)
    for k, (x, y) in enumerate([(12, 80), (12, 192), (12, 382), (12, 554), (722, 554), (722, 674)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['The small V sits in the header of every workspace screen and is a button: press it to open the V page. Its spoken label gives the three counts, so a screen reader hears what a sighted person sees.',
            'Home shows the same V with three plain lines. The decided count is the one that stands, with the held ones named.',
            'In a cluster, the V says which level it sits at and which check matches it. A cluster that mixes levels says to link, never merge, and the "Merge into one" choice is not offered.',
            'Results counts requirements by level, before and after your decisions, and how many verification items must move. The numbers are the V page numbers.',
            'Export carries the same line, so the person preparing documents sees what has to move.',
            'Level chips and a gap filter turn any number on the V into the list behind it.']


def v3_what_a_decision_does(d, ox, oy):
    W, H = 1500, 890
    s = new_frame(d, ox, oy, W, H, '11.3 · What a decision does to the right leg')
    s.t(40, 28, 'LEFT LEG CHANGES. THE RIGHT LEG IS NEVER CHANGED BY THE APP. IT IS TOLD WHAT MUST MOVE.', fs=10, color=SOFT, family=3)

    def req_box(x, y, label, sub, fill='#ffffff', stroke=LEFT, dash=False, w=190):
        return s.r(x, y, w, 52, f'{label}\n{sub}', fill=fill, stroke=stroke, sw=2, fs=10, dash=dash)

    def item_box(x, y, label, fill='#ffffff', stroke=RIGHT, dash=False, w=104):
        return s.r(x, y, w, 30, label, fill=fill, stroke=stroke, sw=2, fs=9, dash=dash, rounded=False)

    # 1: a merge inside one level
    s.caps(40, 56, '1 · TWO WORDINGS AT ONE LEVEL, MERGED INTO ONE')
    s.card(40, 76, 700, 360)
    s.t(60, 90, 'Before', fs=11, color=SOFT)
    s.t(420, 90, 'Subsystem verification', fs=9, color=RIGHT)
    req_box(60, 112, 'M1 · REQ-0410', '2 verification items')
    req_box(60, 196, 'M2 · REQ-0414', '2 verification items')
    for x, y, lab in [(420, 108, 'TC-11 · Test'), (420, 142, 'TC-12 · Test'), (420, 192, 'TC-21 · Test'), (420, 226, 'TC-22 · Test')]:
        item_box(x, y, lab)
        s.line([(250, 138 if y < 180 else 222), (x, y + 15)], stroke=SOFT, sw=1.5, dash=True)
    s.t(60, 268, 'After you record "keep M1, merge M2 into it"', fs=11, color=SOFT)
    req_box(60, 292, 'M1 · REQ-0410', 'keeps its 2 items', fill='#e7f0fd')
    req_box(60, 364, 'M2 · REQ-0414', 'merged into M1', fill=GREY, stroke=SOFT, dash=True)
    for x, y, lab in [(420, 288, 'TC-11 · Test'), (420, 322, 'TC-12 · Test')]:
        item_box(x, y, lab)
        s.line([(250, 318), (x, y + 15)], stroke=SOFT, sw=1.5, dash=True)
    for x, y, lab in [(420, 362, 'TC-21 · Test'), (420, 396, 'TC-22 · Test')]:
        item_box(x, y, lab, fill=AMBER_BG, stroke='#b35a00')
    s.poly([(420, 411), (330, 411), (330, 328), (252, 322)], stroke='#b35a00', sw=2.5, dash=True)
    s.t(540, 384, 'must move to M1', fs=11, color='#b35a00')
    # 2: spans two levels
    s.caps(780, 56, '2 · A REQUIREMENT AND ITS PARENT, ONE LEVEL APART')
    s.card(780, 76, 680, 360)
    s.t(800, 96, 'Level 1 · Needs', fs=10, color=LEFT)
    s.t(800, 214, 'Level 2 · System', fs=10, color=LEFT)
    req_box(800, 116, 'N1 · REQ-0050', 'stakeholder need')
    req_box(800, 234, 'S1 · REQ-0402', 'system requirement')
    s.line([(895, 168), (895, 234)], stroke=SOFT, sw=2)
    s.t(906, 196, 'parent and child', fs=9, color=SOFT)
    s.t(1130, 96, 'Validation', fs=10, color=RIGHT)
    s.t(1130, 214, 'System verification', fs=10, color=RIGHT)
    item_box(1130, 124, 'VAL-3 · Demo', w=130)
    item_box(1130, 242, 'TC-31 · Test', w=130)
    s.line([(990, 142), (1130, 139)], stroke=SOFT, sw=1.5, dash=True)
    s.line([(990, 260), (1130, 257)], stroke=SOFT, sw=1.5, dash=True)
    s.r(800, 322, 300, 64, 'Offered: Link as parent and child, or Supersede. Never "Merge into one".', fill=GUARD_F, stroke='#f1c40f', fs=10)
    s.r(1120, 322, 320, 64, 'Merging would leave level 1 with a check (validation) that proves nothing.', fill=RED_BG, stroke=RED, fs=10)
    # 3: new wording
    s.caps(40, 456, '3 · A NEW WORDING REPLACES THREE (TYPED, OR AN AI DRAFT YOU APPROVED)')
    s.card(40, 476, 700, 220)
    for k in range(3):
        req_box(60, 496 + k * 62, f'M{k + 1}', 'replaced', fill=GREY, stroke=SOFT, dash=True, w=130)
    req_box(300, 556, 'NEW · pending ID', 'adds one requirement', fill='#e7f0fd', w=200)
    for k in range(3):
        s.poly([(190, 522 + k * 62), (300, 582)], stroke=SOFT, sw=1.5)
    para(s, 524, 540, 'All the items on M1, M2 and M3 move to the new requirement, including M1’s. Nothing survives to keep them.', 200, fs=10, color=DARK)
    s.t(524, 620, 'Requirements after = before − 3 + 1', fs=10, color=INK)
    # 4: what counts as traced
    s.caps(780, 456, '4 · WHAT COUNTS AS TRACED: A METHOD AND AT LEAST ONE ITEM')
    s.card(780, 476, 680, 220)
    cases = [('Method + item', 'Traced', GREEN_BG), ('Method, no item', 'Gap', AMBER_BG), ('Item, no method', 'Gap', AMBER_BG), ('Neither', 'Gap', RED_BG)]
    for k, (a, b, fill) in enumerate(cases):
        y = 496 + k * 44
        s.r(800, y, 240, 32, a, fill='#ffffff', stroke=LINE, fs=11, align='left', pad=10)
        s.t(1050, y + 8, '→', fs=14, color=SOFT)
        s.chip(1080, y + 4, 120, 24, b, fill=fill, stroke=HUM if b == 'Traced' else '#b35a00', fs=10)
    s.t(1220, 506, 'Method is one of Test,\nAnalysis, Inspection,\nDemonstration.\nAn item is a verify link.', fs=9, color=SOFT)
    # 5: the bottom line
    s.card(40, 716, 1420, 150)
    s.caps(60, 730, 'THE PROMISES')
    chk_list(s, 60, 752, 1380, [('Pass', 'The app reads requirements and writes nothing back. It never changes a verification item. It tells you which ones must move.'),
                                ('Pass', 'Every number on the V adds up to the Results page: requirements after, decisions counted, items moved. Tests fail when they drift apart.'),
                                ('Pass', 'Levels, methods and items on this prototype are sample values, and the page says so. A real import reads the level from a field or the parent links.')], fs=10)
    for k, (x, y) in enumerate([(12, 78), (752, 78), (12, 478), (752, 478)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['Merging inside one level moves the items of the wording that goes onto the wording that stays. The count of items to move is the sum of the items on every requirement the decision removes.',
            'A cluster that mixes levels is a requirement and its parent. Linking keeps both, each with its own check at its own level. Supersede keeps the stricter one and marks the other; its items then land at a different level, which the V says plainly.',
            'A new wording has no history of its own, so every item on the replaced wordings, including the first, must move to it.',
            'Traced needs both halves. A method with no item is a promise with no evidence; an item with no method says nothing about how it is checked.']


def v4_how_it_is_counted(d, ox, oy):
    W, H = 1500, 630
    s = new_frame(d, ox, oy, W, H, '11.4 · How the V is counted (reqin vee)')
    s.t(40, 28, 'THE SAME RULES RUN IN THE COMMAND LINE, IN CI AND ON THE SCREEN. NO AI IS USED.', fs=10, color=SOFT, family=3)
    box(d, ox + 40, oy + 60, 220, 90, 'A dataset folder\nrequirements.jsonl\nlinks.jsonl', SRC_F, fs=11)
    steps = [('1 · Level', 'By depth in the parent tree (root is level 1; deeper than 4 counts at 4).\nOr from a field you name: 1 to 4, L2, system, component.\nNo parent links and no field: nobody is placed, and it says so.'),
             ('2 · Method', 'From the verification field: test, analysis, inspection,\ndemonstration, or T, A, I, D. Two methods count under each.\nOther text is "other". Empty is "no method".'),
             ('3 · Items', 'A verify link counts for its target. If the target is outside\nthe import but the source is inside, it counts for the source.\nNeither end inside: counted for no one, and reported.'),
             ('4 · Traced or gap', 'Traced = a method AND at least one item.\nEverything else is a gap. Totals are the sum of the levels\nplus anything not placed, so nothing is lost.')]
    for k, (t_, body) in enumerate(steps):
        x = 300 + k * 290
        box(d, ox + x, oy + 60, 270, 160, '', MECH_F, fs=11)
        mark(d, ox + x + 12, oy + 74, 'mech')
        s.t(x + 32, 70, t_, fs=13, color=INK)
        para(s, x + 14, 100, body.replace('\n', ' '), 244, fs=10, color=DARK)
    for k in range(4):
        s.poly([(260 if k == 0 else 300 + k * 290 - 20, 105), (300 + k * 290, 105)], stroke=INK, sw=2)
    s.caps(40, 250, 'WHAT IT PRINTS (SAMPLE DATASET WITH FOUR LEVELS)')
    s.r(40, 270, 880, 190, fill='#1e1e1e', stroke='#1e1e1e')
    code = ['$ reqin vee datasets/F02_everything',
            'The V (levels from the parent tree)',
            '',
            'Level                          Reqs  Traced   Gaps  No method  No item  Items  Checked by',
            '1 Stakeholder needs               1       0      1          0        1      0  Validation',
            '2 System requirements             3       0      3          0        3      0  System verification',
            '3 Subsystem requirements          9       0      9          0        9      0  Subsystem verification',
            '4 Component requirements         18       2     16          0       16      2  Component verification',
            'All requirements                 31       2     29                          2']
    s.t(56, 284, '\n'.join(code), fs=11, color='#e9ecef', family=3)
    s.caps(960, 250, 'USING IT')
    chk_list(s, 960, 272, 500, [('Pass', 'reqin vee DIR prints the table. --json gives a screen the same numbers.'),
                                ('Pass', '--by field --level-field "Level" when the level is a column, not the tree.'),
                                ('Pass', '--max-gaps 0 makes a CI job fail while any requirement lacks a method or an item.'),
                                ('Open', 'Needs the dataset from "reqin import --out-dir". A broken dataset is refused, not guessed at.')], fs=10)
    s.card(40, 490, 1420, 110)
    s.caps(60, 504, 'WHY THESE RULES')
    para(s, 60, 524, 'Level, method and item are all things a person can check in the source: a column, a field and a link. Nothing is inferred by a model. If a source has no parent links and no level field, the honest answer is "cannot place", and every screen shows it that way instead of putting everything at level 1.', 1320, fs=11, color=DARK)
    d.frame_end()
    return ['The command is the screen’s source of truth: the same function, the same rules.',
            'It reads a validated dataset only. A folder that breaks the contract is refused.',
            'Every table in the output is also in --json, so a CI job or a dashboard can use it.']
