from wf import *

NOTE_W = 300


def notes(d, x, y, items, title=None, w=NOTE_W):
    """Numbered annotation column placed beside a frame (outside it, so nothing clips)."""
    cy = y
    if title:
        d.text(x, cy, title, fs=16, family=1, color=RED)
        cy += 30
    for n, s in items:
        e = d.shape('ellipse', x, cy, 20, 20, str(n), fs=11, fill=RED, stroke=RED, color='#ffffff', pad=0)
        wrapped = d.wrap(s, w - 34, 12, 2)
        d.text(x + 28, cy + 1, wrapped, fs=12, color=DARK, family=2)
        cy += max(30, (wrapped.count('\n') + 1) * 12 * 1.25 + 14)
    return cy


def s_open(d, ox, oy):
    d.frame_begin(ox, oy, 1000, 640, '1 · Open a project (no sidebar yet)')
    s = Scr(d, ox, oy)
    s.r(0, 0, 1000, 640, fill=GREY, stroke=GREY, rounded=False)
    s.r(40, 28, 24, 24, fill=ACC, stroke=ACC)
    s.t(74, 32, 'Requirements Consolidator', fs=12, color=INK)
    s.chip(280, 30, 190, 18, 'PROTOTYPE · SAMPLE DATA ONLY', fill='#ffffff')
    s.h1(40, 80, 'Open a requirements project', fs=30)
    s.ph(40, 128, 540, 3, gap=12)
    s.caps(40, 180, 'CHOOSE A SOURCE')
    cards = [('SysML v2 model', 'API or KPAR', 'Connect to an API endpoint,\nor open a .sysml / KPAR package.', 'For MSOSA releases that use SysML v2'),
             ('ReqIF export', 'ReqIF 1.2', 'Open a .reqif exported from MSOSA\nvia Cameo Requirements Modeler.', 'The documented export route'),
             ('MSOSA project file', '.mdzip', 'Read zipped XMI directly.\nElement text and links only.', 'Experimental: no documented reader'),
             ('Spreadsheet', 'CSV / XLSX', 'One requirement per row.', 'Fallback when no model export exists')]
    for i, (t_, tag, body, note) in enumerate(cards):
        x, y = 40 + (i % 2) * 270, 200 + (i // 2) * 138
        s.card(x, y, 255, 124)
        s.t(x + 14, y + 12, t_, fs=13, color=INK)
        s.chip(x + 160, y + 12, 82, 16, tag)
        s.t(x + 14, y + 44, body, fs=10, color=DARK)
        s.t(x + 14, y + 96, note, fs=9, color=SOFT)
    s.caps(600, 180, 'RECENT PROJECTS')
    for i, (n, sub) in enumerate([('systems v2', 'SysML v2 model'), ('MSoSA', 'ReqIF export')]):
        s.card(600, 200 + i * 56, 360, 48)
        s.t(614, 208 + i * 56, n, fs=12, color=INK)
        s.t(614, 226 + i * 56, sub + ' · opens the synthetic sample in this prototype', fs=9, color=SOFT)
    s.card(600, 322, 360, 230)
    s.t(614, 336, 'First time here?', fs=13, color=INK)
    for i, line in enumerate(['Draft = suggested, not approved. Your source model is never changed.', 'Four lenses review each suggestion.', 'Guards block any change to a number, unit, shall/should or "not".']):
        s.t(626, 366 + i * 40, '•  ' + d.wrap(line, 320, 10), fs=10, color=DARK)
    s.btn(614, 500, 170, 36, 'Open the sample project', primary=True)
    s.num(22, 202, 1)
    s.num(582, 202, 2)
    s.num(582, 324, 3)
    d.frame_end()
    return ['Source cards are real buttons (44 px high at full size). Experimental and fallback routes say so on the card.',
            'Recent slots hold "systems v2" and "MSoSA". The prototype opens a synthetic sample, never your real files.',
            'First-run panel: three plain ideas and one primary action, so a new user is never stuck.']


def s_import(d, ox, oy):
    d.frame_begin(ox, oy, 1000, 640, '2 · Map fields and prepare')
    s = Scr(d, ox, oy)
    s.r(0, 0, 1000, 640, fill=GREY, stroke=GREY, rounded=False)
    s.t(40, 30, '1 · SOURCE   /   2 · MAP FIELDS AND PREPARE   /   3 · WORKSPACE', fs=10, color=SOFT, family=3)
    s.h1(40, 62, 'We found the fields your review screens need', fs=24)
    s.t(40, 100, 'Source: ReqIF export. The standard review layout fills itself from these fields. Missing fields show as empty slots, never guesses.', fs=10, color=DARK)
    s.card(40, 140, 560, 330)
    s.caps(56, 152, 'DETECTED STRUCTURE')
    rows = [('Requirement ID', 'REQ-FCS-0212', 'ID on every screen', 'Exact', GREEN_BG), ('Statement text', 'The Flight Control Subsystem shall…', 'Requirement statement', 'Exact', GREEN_BG),
            ('Rationale', 'Bounds ground-station loop latency', 'Rationale panel', 'High', GREEN_BG), ('Verification method', 'Test', 'Verification: T, A, I or D', 'High', GREEN_BG),
            ('Allocation', 'Flight Control Subsystem', 'Allocated to', 'Medium', AMBER_BG), ('Owner', 'FCS team', 'Owner (blocks cross-owner merges)', 'Medium', AMBER_BG), ('Baseline', 'none', 'Baseline badge', 'Medium', AMBER_BG)]
    for i, (a, b, c, conf, col) in enumerate(rows):
        y = 176 + i * 40
        s.line([(40, y), (600, y)], stroke='#dee2e6', sw=1)
        s.t(56, y + 6, a, fs=11, color=INK)
        s.t(56, y + 22, b, fs=8, color=SOFT, family=3)
        s.t(236, y + 12, c, fs=10, color=DARK)
        s.chip(520, y + 10, 62, 18, conf, fill=col)
    s.card(620, 140, 340, 420)
    s.caps(636, 152, 'COMPARISONS PREPARED (SAMPLE RUN)')
    steps = ['Read and normalise: 214', 'Collapse exact copies: 2 groups', 'Fuzzy and keyword candidates: 63', 'Embedding shortlist: 41', 'Cross-encoder and NLI re-score', 'Combine scores (uncalibrated)', 'Cluster and label: 7 clusters', 'AI judge on uncertain band: 4', 'Guard checks on every proposal']
    for i, st in enumerate(steps):
        s.check(636, 178 + i * 40)
        s.t(660, 180 + i * 40, st, fs=10, color=DARK)
    s.btn(40, 500, 170, 38, 'Open workspace', primary=True, fs=12)
    s.t(40, 550, 'Prototype note: numbers come from a small synthetic sample.', fs=9, color=SOFT)
    s.num(22, 142, 1)
    s.num(602, 142, 2)
    s.num(22, 502, 3)
    d.frame_end()
    return ['Detected fields map onto fixed UI slots. Confidence shown as text (Exact, High, Medium), not colour alone.',
            'The mechanical ladder and the AI pass already ran, so the workspace opens with real content, not an empty queue.',
            'One primary action. A "Change mapping" control is the next addition for Medium rows.']


def s_overview(d, ox, oy):
    W, H = 1000, 640
    d.frame_begin(ox, oy, W, H, '3 · Overview')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Overview')
    s.h1(cx, cy, 'Overview', fs=24)
    s.t(cx, cy + 32, 'Sample run: 214 requirements, 41 candidate pairs, 7 clusters. Numbers come from the synthetic sample.', fs=10, color=DARK)
    y = cy + 60
    s.card(cx, y, 816, 62)
    s.t(cx + 14, y + 10, 'New here? Three things to do on each cluster', fs=11, color=INK)
    s.t(cx + 14, y + 30, '1 Read both wordings   2 Check the guards   3 Decide, then four lenses sign off', fs=10, color=DARK)
    s.btn(cx + 700, y + 14, 100, 32, 'Hide this')
    y += 76
    s.card(cx, y, 230, 130)
    s.t(cx + 16, y + 10, '7', fs=48, color=INK)
    s.t(cx + 16, y + 70, 'clusters waiting for a decision', fs=11, color=DARK)
    s.btn(cx + 16, y + 92, 190, 28, 'Start with the safest cluster', primary=True, fs=10)
    for i, (nm, n, of, fill, sub) in enumerate([('Lane A · low risk', 2, 2, GREEN_BG, 'Guards pass, methods agree'), ('Lane B · needs evidence', 3, 3, AMBER_BG, 'Read before you decide'), ('Lane C · conflicts', 2, 2, RED_BG, 'Escalate, never merge')]):
        x = cx + 244 + i * 192
        s.card(x, y, 180, 130)
        s.chip(x + 12, y + 12, 150, 18, nm, fill=fill)
        s.t(x + 12, y + 44, '%d of %d open' % (n, of), fs=14, color=INK)
        s.t(x + 12, y + 80, sub, fs=9, color=SOFT)
    y += 144
    s.card(cx, y, 480, 170)
    s.caps(cx + 14, y + 10, 'HOW THE LIST NARROWED')
    for i, (lab, v) in enumerate([('Requirements read', 214), ('Candidate pairs', 63), ('After embedding shortlist', 41), ('Clusters', 7), ('Judged by the AI', 4)]):
        yy = y + 34 + i * 26
        s.t(cx + 14, yy, lab, fs=10, color=DARK)
        s.r(cx + 160, yy, max(6, 250 * v / 214), 14, fill='#4dabf7', stroke='#4dabf7', rounded=False)
        s.t(cx + 166 + max(6, 250 * v / 214), yy, str(v), fs=10, color=INK)
    s.card(cx + 496, y, 320, 170)
    s.caps(cx + 510, y + 10, 'SIGN-OFF BY LENS')
    for i, nm in enumerate(['Systems engineer', 'Process engineer', 'UI/UX engineer', 'New user']):
        yy = y + 34 + i * 30
        s.t(cx + 510, yy, nm, fs=10, color=INK)
        s.t(cx + 740, yy, '0 of 7', fs=9, color=SOFT)
        s.r(cx + 510, yy + 16, 290, 7, fill='#d0e0ff', stroke='#d0e0ff', rounded=False)
    s.num(cx - 22, cy + 60, 1)
    s.num(cx - 22, cy + 136, 2)
    s.num(cx + 224, cy + 136, 3)
    s.num(cx - 22, cy + 280, 4)
    s.num(cx + 480, cy + 280, 5)
    d.frame_end()
    return ['Dismissible first-run guidance. It never returns once hidden (a Tweak can switch it off for experts).',
            'One hero number: how many clusters need a decision. One primary action: start with the safest.',
            'Three risk lanes. Lane is a text label with a name, not only a colour.',
            'Funnel shows how 214 requirements became 7 clusters, so the reduction is not a black box.',
            'Four sign-off meters. A suggestion is approved only when all four lenses have signed.']
