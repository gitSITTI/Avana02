"""Storyboard: nine panels, persona card, emotion curve."""
from wf import *
from exc import Doc, INK

PW, PH = 500, 350
SK = dict(rough=1)  # hand-drawn look


def person(s, x, y, mood='ok', sc=1.0, label=None):
    s.shape('ellipse', x - 12 * sc, y, 24 * sc, 24 * sc, fill='#ffffff', stroke=INK, sw=2, **SK)
    s.shape('ellipse', x - 6 * sc, y + 8 * sc, 2.5, 2.5, fill=INK, stroke=INK)
    s.shape('ellipse', x + 3.5 * sc, y + 8 * sc, 2.5, 2.5, fill=INK, stroke=INK)
    m = {'worried': [(-5, 18), (-2, 15), (2, 15), (5, 18)], 'ok': [(-5, 16), (5, 16)], 'happy': [(-6, 14), (-3, 18), (3, 18), (6, 14)]}[mood]
    s.poly([(x + a * sc, y + b * sc) for a, b in m], typ='line', stroke=INK, sw=1.5)
    s.line([(x, y + 24 * sc), (x, y + 70 * sc)], stroke=INK, sw=2, **SK)
    s.line([(x - 22 * sc, y + 56 * sc), (x, y + 38 * sc), (x + 22 * sc, y + 56 * sc)], stroke=INK, sw=2, **SK)
    s.line([(x - 16 * sc, y + 102 * sc), (x, y + 70 * sc), (x + 16 * sc, y + 102 * sc)], stroke=INK, sw=2, **SK)
    if label:
        s.t(x - len(label) * 3, y + 106 * sc, label, fs=11, family=1, color=SOFT)


def bubble(s, x, y, w, h, text, tail_to=None, fs=12, fill='#fff9db'):
    s.shape('ellipse', x, y, w, h, text, fs=fs, family=1, fill=fill, stroke=INK, sw=1.5, pad=10, **SK)
    if tail_to:
        tx, ty = tail_to
        s.shape('ellipse', x + w * 0.2, y + h + 2, 9, 9, fill=fill, stroke=INK, **SK)
        s.shape('ellipse', x + w * 0.1, y + h + 14, 5, 5, fill=fill, stroke=INK, **SK)


def screen(s, x, y, w, h, title=None):
    s.r(x, y, w, h, fill='#ffffff', stroke=INK, sw=2, **SK)
    s.r(x, y, w, 18, fill='#dee2e6', stroke=INK, sw=1, rounded=False)
    s.shape('ellipse', x + 7, y + 6, 6, 6, fill=RED, stroke=RED)
    s.shape('ellipse', x + 17, y + 6, 6, 6, fill='#fab005', stroke='#fab005')
    s.shape('ellipse', x + 27, y + 6, 6, 6, fill='#40c057', stroke='#40c057')
    if title:
        s.t(x + 44, y + 3, title, fs=10, color=DARK, family=2)


def mini_check(s, x, y):
    s.shape('ellipse', x, y, 12, 12, fill=GREEN_BG, stroke=HUM)
    s.poly([(x + 3, y + 6.5), (x + 5.5, y + 9), (x + 9.5, y + 4)], typ='line', stroke=HUM, sw=1.5)


def d_wrap(s, text, w, fs):
    return s.d.wrap(text, w, fs)


def arrow(s, a, b, label=None, color=INK, dash=False):
    e = s.poly([a, b], stroke=color, sw=2, dash=dash)
    if label:
        s.t((a[0] + b[0]) / 2 - len(label) * 3, min(a[1], b[1]) - 16, label, fs=11, family=1, color=color)
    return e


# ---------------- scenes (local to the panel; scene area is y 48..240) ----------------
def sc1(s):
    person(s, 70, 110, 'worried')
    bubble(s, 100, 50, 190, 54, 'Are these two the same requirement?', tail_to=(80, 110))
    s.t(290, 52, 'thousands of near-duplicates', fs=12, family=1, color=RED)
    for i in range(4):
        s.r(286 + i * 16, 80 + i * 18, 150, 52, fill='#ffffff', stroke=INK, sw=1.5, **SK)
    s.t(298 + 3 * 16, 88 + 3 * 18, 'REQ-FCS-0212', fs=10, family=3, color=INK)
    s.ph(298 + 3 * 16, 108 + 3 * 18, 110, 2, gap=8)
    s.r(20, 215, 100, 22, 'systems v2', fill=BLUE_BG, stroke=INK, fs=11, family=1, **SK)
    s.r(130, 215, 100, 22, 'MSoSA', fill=BLUE_BG, stroke=INK, fs=11, family=1, **SK)
    s.t(250, 220, 'huge, online, read-only to us', fs=11, family=1, color=SOFT)


def sc2(s):
    s.r(14, 70, 130, 48, 'systems v2\n(SysML v2 API / KPAR)', fill=BLUE_BG, stroke=INK, fs=11, family=1, **SK)
    s.r(14, 140, 130, 48, 'MSoSA\n(ReqIF export)', fill=BLUE_BG, stroke=INK, fs=11, family=1, **SK)
    arrow(s, (146, 94), (196, 120), 'open', INK)
    arrow(s, (146, 164), (196, 140))
    screen(s, 200, 56, 280, 176, 'Requirements Consolidator')
    for i, t_ in enumerate(['SysML v2 model', 'ReqIF export', 'MSOSA .mdzip', 'Spreadsheet']):
        s.r(212 + (i % 2) * 130, 86 + (i // 2) * 66, 122, 56, t_, fill=GREY, stroke=INK, fs=10, **SK)
    s.chip(212, 214, 150, 14, 'SAMPLE DATA ONLY', fs=8, fill=AMBER_BG)


def sc3(s):
    screen(s, 14, 56, 300, 182, 'Map fields and prepare')
    steps = ['Read and normalise: 214', 'Fuzzy + keyword: 63 pairs', 'Embedding shortlist: 41', 'Cross-encoder + NLI re-score', 'Cluster and label: 7', 'AI judge, uncertain band: 4']
    for i, st in enumerate(steps):
        mini_check(s, 28, 82 + i * 22)
        s.t(48, 82 + i * 22, st, fs=11, color=DARK)
    s.prov(28, 216, 'mech', 'mechanical first, AI only at the end', fs=9)
    for i in range(7):
        s.r(340 + (i % 3) * 50, 78 + (i // 3) * 44, 42, 38, 'CL-0%d' % (i + 1), fill=[GREEN_BG, GREEN_BG, AMBER_BG, AMBER_BG, AMBER_BG, RED_BG, RED_BG][i], stroke=INK, fs=9, **SK)
    s.t(330, 60, '7 clusters, not 214 rows', fs=11, family=1, color=RED)
    s.t(340, 214, 'lane = risk, in words', fs=11, family=1, color=SOFT)


def sc4(s):
    screen(s, 14, 56, 300, 182, 'Overview')
    s.t(30, 82, '7', fs=44, family=2, color=INK)
    s.t(80, 90, 'clusters waiting\nfor a decision', fs=11, color=DARK)
    for i, (nm, f) in enumerate([('Lane A\nlow risk', GREEN_BG), ('Lane B\nevidence', AMBER_BG), ('Lane C\nconflict', RED_BG)]):
        s.r(28 + i * 94, 150, 86, 56, nm, fill=f, stroke=INK, fs=10, **SK)
    s.btn(28, 214, 160, 18, 'Start with the safest', primary=True, fs=9)
    person(s, 400, 100, 'ok')
    bubble(s, 340, 48, 150, 44, 'Start with Lane A.', tail_to=(400, 100))


def sc5(s):
    for i, (lab, txt) in enumerate([('A  REQ-FCS-0215', 'every 1 second'), ('B  REQ-GCS-0102', 'every 10 seconds')]):
        x = 14 + i * 176
        s.r(x, 56, 168, 100, fill='#ffffff', stroke=INK, sw=1.5, **SK)
        s.t(x + 10, 64, lab, fs=9, family=3, color=INK)
        s.t(x + 10, 84, 'The Flight Control\nSubsystem shall transmit\na heartbeat message...', fs=10, color=DARK)
        s.r(x + 10, 128, 110, 18, fill='#ffe0ad', stroke='#ffe0ad', rounded=False)
        s.t(x + 14, 130, txt, fs=11, color=INK)
        s.line([(x + 10, 146), (x + 120, 146)], stroke='#b35a00', sw=2)
    s.r(14, 168, 352, 40, 'Guard "Numbers preserved": 1 s is not 10 s. Merge blocked.', fill=RED_BG, stroke=RED, sw=2, fs=10, **SK)
    s.t(14, 218, 'similarity said 0.96 — the guard saw the tenfold difference', fs=11, family=1, color=RED)
    person(s, 430, 100, 'ok')
    bubble(s, 372, 48, 120, 40, 'Not a duplicate.', tail_to=(430, 100))


def sc6(s):
    screen(s, 10, 56, 210, 150, 'Blind-first')
    s.t(24, 84, 'The AI proposal is hidden.\nRecord your own call first.', fs=10, color=DARK)
    for i, lab in enumerate(['Same', 'Different', 'Unsure']):
        s.r(22 + i * 64, 130, 60, 28, lab, fill='#ffffff', stroke=INK, fs=9, pad=3, **SK)
    s.t(24, 176, 'stops you anchoring on the AI', fs=10, family=1, color=SOFT)
    arrow(s, (224, 130), (262, 130), 'reveal')
    screen(s, 268, 56, 226, 150, 'AI judge')
    s.prov(280, 84, 'ai')
    s.t(296, 82, 'VARIANT · 88% · 3 of 3 runs', fs=10, color=AIC)
    s.r(280, 106, 200, 22, '“1 second”  /  “10 seconds”', fill='#f8f0fc', stroke=AIC, fs=9)
    s.t(280, 140, 'You said: Different.\nThe AI said: Variant.', fs=10, color=DARK)
    s.t(280, 176, 'verbatim quotes, checked by code', fs=10, family=1, color=SOFT)
    s.t(10, 222, 'AI = diamond. Mechanical = square. Human = circle.', fs=11, family=1, color=SOFT)


def sc7(s):
    s.r(14, 62, 18, 18, fill='#ffffff', stroke=INK, sw=2)
    s.poly([(18, 71), (22, 76), (29, 66)], typ='line', stroke=INK, sw=2.5)
    s.t(40, 62, d_wrap(s, 'I have read both wordings and the guards.', 150, 10), fs=10, color=DARK)
    s.btn(14, 96, 150, 34, 'Keep both and link', primary=True, fs=11)
    s.t(14, 140, 'Decision logged. Undo is one click.', fs=10, family=1, color=SOFT)
    for i, (ini, nm) in enumerate([('SE', 'Systems'), ('PE', 'Process'), ('UX', 'UI/UX'), ('NU', 'New user')]):
        x = 210 + i * 70
        s.shape('ellipse', x, 70, 52, 52, ini, fill=[BLUE_BG, VIOLET_BG, AMBER_BG, GREEN_BG][i], stroke=INK, sw=2, fs=14, family=1, **SK)
        s.t(x + 26 - len(nm) * 2.8, 128, nm, fs=10, color=DARK)
        mini_check(s, x + 20, 148)
    s.r(210, 180, 270, 40, 'Approved only when all four lenses have signed', fill=GREEN_BG, stroke=HUM, sw=2, fs=11, family=1, **SK)


def sc8(s):
    s.t(14, 54, 'same scoring for mechanical and AI', fs=12, family=1, color=RED)
    for i, (k, nm, p) in enumerate([('mech', 'Fuzzy', .61), ('mech', 'Embedding', .71), ('mech', 'Combined', .86), ('ai', 'AI judge', .83)]):
        yy = 84 + i * 30
        s.prov(14, yy, k)
        s.t(32, yy - 1, nm, fs=10, color=DARK)
        s.bar(110, yy + 1, 110, p, h=9)
        s.t(226, yy - 1, '%.2f' % p, fs=10, family=3, color=INK)
    s.t(14, 210, 'illustrative until a gold set exists', fs=10, family=1, color=SOFT)
    s.t(290, 54, 'hash-chained audit log', fs=12, family=1, color=RED)
    for i in range(4):
        bad = i == 2
        s.r(262 + (i % 2) * 112, 84 + (i // 2) * 66, 96, 46, '#%d  %s' % (i + 1, 'edited!' if bad else 'ok'), fill=RED_BG if bad else GREY, stroke=RED if bad else INK, fs=10, **SK)
    arrow(s, (358, 107), (374, 107), color=INK)
    arrow(s, (430, 130), (310, 150), color=INK)
    arrow(s, (358, 173), (374, 173), color=RED)
    s.t(262, 224, 'break one entry, the chain shows it', fs=10, family=1, color=RED)


def sc9(s):
    s.r(14, 70, 120, 90, 'Approved\nCL-01\nCL-03', fill=GREEN_BG, stroke=INK, fs=12, family=1, **SK)
    arrow(s, (136, 115), (170, 115))
    s.r(172, 80, 110, 70, 'Draft package\nDRAFT-0001', fill=BLUE_BG, stroke=INK, fs=11, family=1, **SK)
    for i, nm in enumerate(['Sphinx-Needs (.rst)', 'StrictDoc (.sdoc)', 'Word (.docx)', 'ReqIF 1.2']):
        s.r(330, 56 + i * 40, 140, 32, nm, fill='#ffffff', stroke=INK, fs=10, **SK)
        arrow(s, (284, 115), (328, 72 + i * 40), color=SOFT)
    s.t(14, 176, 'only four-lens-approved changes go out', fs=11, family=1, color=RED)
    s.t(14, 198, 'the source model is never written to', fs=11, family=1, color=SOFT)
    s.t(330, 218, '→ document authoring', fs=12, family=1, color=INK)


PANELS = [
    ('The problem', 'A huge systems v2 / MSoSA project is full of requirements that say almost the same thing. Nobody can read them all, and merging by hand is risky.', 'Overwhelmed', sc1),
    ('Open the project', 'The analyst opens a SysML v2 model, a ReqIF export from MSOSA, or a spreadsheet. The app maps the fields into a fixed, familiar layout.', 'Curious', sc2),
    ('It is already prepared', 'Cheap mechanical methods ran first and narrowed 214 requirements to 7 clusters. The AI only judged the uncertain few.', 'Reassured', sc3),
    ('Start with the safest', 'The overview shows one number and three risk lanes in words. A first-timer is told exactly where to begin.', 'Oriented', sc4),
    ('Compare side by side', 'Both wordings sit together with numbers, units, shall/should and not highlighted. A guard catches what similarity cannot.', 'Alert', sc5),
    ('The AI speaks last', 'In blind-first mode the analyst records their own call, then sees the AI verdict with verbatim quotes.', 'In control', sc6),
    ('Decide, then four lenses', 'The analyst decides, and the systems, process, UI/UX and new-user lenses each sign off. Nothing is final until all four have.', 'Confident', sc7),
    ('Check the numbers', 'Metrics score the mechanical methods and the AI the same way. The audit log proves nothing was altered after the fact.', 'Informed', sc8),
    ('Export to documents', 'Only approved changes flow to a draft package for document authoring, with baseline IDs and alias lists.', 'Relieved', sc9),
]


def panel(d, ox, oy, i, title, caption, feel, fn):
    d.frame_begin(ox, oy, PW, PH, '%d · %s' % (i, title))
    s = Scr(d, ox, oy)
    s.r(0, 0, PW, PH, fill='#ffffff', stroke='#ffffff', rounded=False)
    s.shape('ellipse', 12, 12, 28, 28, str(i), fill=RED, stroke=RED, color='#ffffff', fs=14, family=1, pad=0)
    s.t(50, 14, title, fs=20, family=1, color=INK)
    fn(s)
    s.line([(14, 254), (PW - 14, 254)], stroke='#dee2e6', sw=1)
    s.t(14, 262, d.wrap(caption, PW - 28, 13), fs=13, color=DARK, family=2)
    s.chip(14, PH - 30, 150, 18, 'Analyst feels: ' + feel.lower(), fill=GREY, fs=10)
    d.frame_end()


def build(path):
    d = Doc(21)
    GAP = 30
    GW = 3 * PW + 2 * GAP
    # title block
    d.text(0, 0, 'Storyboard: from a huge requirements project to approved, audited, draft-ready documents', fs=30, family=1)
    d.text(0, 44, 'Requirements Consolidator · nine moments in one review session · everything on screen is a draft until four lenses sign', fs=15, family=2, color=SOFT)
    # persona
    d.frame_begin(0, 90, GW, 150, 'Who this is for')
    s = Scr(d, 0, 90)
    s.r(0, 0, GW, 150, fill='#fff9db', stroke='#fff9db', rounded=False)
    person(s, 60, 24, 'ok', 0.9)
    s.t(110, 14, 'Persona: Systems analyst on a large engineering program', fs=16, family=1, color=INK)
    s.t(110, 42, d.wrap('Works from systems v2 and MSoSA models that are online, very large and shared. Wants fewer duplicate requirements without losing a single trace link. Must be able to show a reviewer exactly why every change was made.', 560, 12), fs=12, color=DARK)
    s.t(700, 14, 'Also served', fs=14, family=1, color=RED)
    s.t(700, 38, d.wrap('Process engineer: control and audit.\nUI/UX engineer: clear, consistent screens.\nNew user: nothing assumes prior knowledge.', 340, 12), fs=12, color=DARK)
    s.t(1060, 14, 'How to read the marks', fs=14, family=1, color=RED)
    s.prov(1060, 44, 'mech', 'Square: a mechanical method', fs=11)
    s.prov(1060, 70, 'ai', 'Diamond: the AI', fs=11)
    s.prov(1060, 96, 'human', 'Circle: a person', fs=11)
    s.t(110, 118, 'All names and numbers in these drawings are from the synthetic sample.', fs=11, family=1, color=SOFT)
    d.frame_end()
    # grid
    gy = 270
    for i, (t_, c, f, fn) in enumerate(PANELS):
        r_, c_ = divmod(i, 3)
        panel(d, c_ * (PW + GAP), gy + r_ * (PH + GAP), i + 1, t_, c, f, fn)
    # emotion curve
    ey = gy + 3 * (PH + GAP) + 10
    d.frame_begin(0, ey, GW, 260, 'Emotion curve')
    s = Scr(d, 0, ey)
    s.r(0, 0, GW, 260, fill='#ffffff', stroke='#ffffff', rounded=False)
    s.t(16, 12, 'Emotion curve across the nine moments', fs=18, family=1, color=INK)
    s.line([(60, 60), (60, 220), (GW - 40, 220)], stroke=SOFT, sw=1)
    s.t(8, 52, 'calm', fs=11, family=1, color=SOFT)
    s.t(8, 214, 'tense', fs=11, family=1, color=SOFT)
    lv = [200, 150, 110, 90, 150, 100, 70, 80, 50]
    xs = [60 + 90 + k * ((GW - 200) / 8) for k in range(9)]
    s.poly(list(zip(xs, lv)), typ='line', stroke=ACC, sw=3, **SK)
    for k, (x, y) in enumerate(zip(xs, lv)):
        s.shape('ellipse', x - 7, y - 7, 14, 14, fill=ACC, stroke=ACC)
        s.t(x - len(PANELS[k][2]) * 3, (y + 14) if k not in (0, 4) else (y - 30), PANELS[k][2], fs=11, family=1, color=INK)
        s.t(x - 4, 226, str(k + 1), fs=11, family=1, color=SOFT)
    s.t(xs[4] + 12, lv[4] + 8, 'dip is intentional: a real difference deserves attention', fs=11, family=1, color=RED)
    d.frame_end()
    d.save(path)
    return d


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else '01_storyboard.excalidraw')
