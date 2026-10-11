from wf import *
import re

LANE_FILL = {'A': GREEN_BG, 'B': AMBER_BG, 'C': RED_BG}
LANE_NAME = {'A': 'Lane A · low risk', 'B': 'Lane B · needs evidence', 'C': 'Lane C · conflict'}
REL_FILL = {'Equivalent': BLUE_BG, 'Variant': VIOLET_BG, 'Subsumes': BLUE_BG, 'Conflict': RED_BG}
GUARDS = ['Cited requirement IDs exist', 'Quoted evidence is verbatim', 'Numbers preserved', 'Units compatible', 'Shall / should / will preserved',
          'Negation preserved', 'Conditions kept', 'Actors, acronyms, part numbers match', 'No invented content', 'Round-trip entailment holds']


def kind_of(w):
    t = w.lower().strip('.,;:')
    if t in ('shall', 'should', 'will', 'may', 'must'):
        return 'modal'
    if t in ('not', 'no', 'never', 'without'):
        return 'neg'
    if t in ('upon', 'when', 'if', 'while', 'unless', 'after', 'before'):
        return 'cond'
    if re.fullmatch(r'\d+(\.\d+)?', t) or t in ('second', 'seconds', 'ms', 'milliseconds', 'days'):
        return 'num'
    return None


def tokw(s, x, y, w, text, fs=11, differs=()):
    """Wrapped token line with slot highlights and an underline under words that differ between A and B."""
    fills = {'num': '#ffe0ad', 'modal': '#d5e3ff', 'neg': '#ffd3ce', 'cond': '#e8deff'}
    cx, cy = x, y
    lh = fs * 1.9
    for w_ in text.split():
        wd = len(w_) * fs * 0.5 + 5
        if cx + wd > x + w:
            cx, cy = x, cy + lh
        k = kind_of(w_)
        if k:
            s.r(cx - 2, cy - 2, wd, fs + 6, fill=fills[k], stroke=fills[k], rounded=False)
        s.t(cx, cy, w_, fs=fs, family=2, color=DARK)
        if w_.strip('.,;:') in differs:
            s.line([(cx - 2, cy + fs + 4), (cx + wd - 4, cy + fs + 4)], stroke='#b35a00', sw=2)
        cx += wd + 3
    return cy + lh


def guard_row(s, x, y, w, name, state, note=''):
    col = {'p': HUM, 'w': '#b35a00', 'f': RED}[state]
    if state == 'f':
        s.r(x - 4, y - 3, w + 8, 32, fill='#fff5f5', stroke=RED)
    if state == 'p':
        s.shape('ellipse', x, y + 1, 12, 12, fill=GREEN_BG, stroke=HUM)
        s.poly([(x + 3, y + 7), (x + 5.5, y + 9.5), (x + 9.5, y + 4)], typ='line', stroke=HUM, sw=1.5)
    elif state == 'w':
        s.shape('diamond', x - 1, y, 14, 14, fill=AMBER_BG, stroke='#b35a00')
    else:
        s.shape('ellipse', x, y + 1, 12, 12, fill=RED_BG, stroke=RED)
        s.poly([(x + 3.5, y + 4.5), (x + 8.5, y + 9.5)], typ='line', stroke=RED, sw=1.5)
        s.poly([(x + 8.5, y + 4.5), (x + 3.5, y + 9.5)], typ='line', stroke=RED, sw=1.5)
    s.t(x + 20, y, name, fs=9, color=INK)
    tag = {'p': 'Pass', 'w': 'Warning', 'f': 'Blocks merge'}[state]
    s.t(x + 20, y + 13, tag + (' · ' + note if note else ''), fs=8, color=col)


def queue(s, x, y, selected=2):
    s.caps(x, y, 'CLUSTERS · SAFEST FIRST')
    rows = [('CL-01', 'A', 'Health message timing, two wordings', 'Equivalent', 'Approved'), ('CL-02', 'A', 'Fault record retention', 'Equivalent', 'In review'),
            ('CL-03', 'B', 'Heartbeat rate: 1 s or 10 s?', 'Variant', 'Suggested'), ('CL-04', 'B', 'Fault logging: plain or with timestamp', 'Subsumes', 'Suggested'),
            ('CL-05', 'B', 'Health display: shall or should?', 'Variant', 'Suggested'), ('CL-06', 'C', 'Bus voltage: 28 VDC or 270 VDC?', 'Conflict', 'Suggested'),
            ('CL-07', 'C', 'Telemetry encryption: on or off?', 'Conflict', 'Suggested')]
    for i, (cid, lane, title, rel, st) in enumerate(rows):
        yy = y + 20 + i * 76
        sel = i == selected
        s.r(x, yy, 190, 70, fill='#F1F6FF' if sel else '#ffffff', stroke=ACC if sel else LINE, sw=2 if sel else 1)
        s.t(x + 10, yy + 8, cid, fs=10, color=INK, family=3)
        s.chip(x + 100, yy + 6, 80, 14, 'Lane ' + lane, fill=LANE_FILL[lane], fs=8)
        s.t(x + 10, yy + 26, s.d.wrap(title, 172, 9), fs=9, color=DARK)
        s.chip(x + 10, yy + 52, 74, 14, rel, fill=REL_FILL[rel], fs=8)
        fill = {'Approved': GREEN_BG, 'In review': ACC_BG, 'Suggested': '#ffffff'}[st]
        s.chip(x + 92, yy + 52, 88, 14, st, fill=fill, fs=8, dash=(st == 'Suggested'))


def s_review(d, ox, oy):
    W, H = 1000, 1580
    d.frame_begin(ox, oy, W, H, '4 · Review queue and one cluster (CL-03 selected)')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Review queue')
    queue(s, cx, cy)
    x = cx + 206   # detail column
    dw = 610
    y = cy
    # header
    s.chip(x, y, 54, 22, 'CL-03', fs=10)
    s.chip(x + 62, y, 140, 22, 'Lane B · needs evidence', fill=AMBER_BG, fs=9)
    s.chip(x + 210, y, 66, 22, 'Variant', fill=VIOLET_BG, fs=9)
    s.chip(x + 284, y, 76, 22, 'Suggested', fs=9, dash=True)
    s.btn(x + 440, y - 2, 170, 26, 'Blind-first mode: off', fs=9)
    s.h1(x, y + 34, 'Heartbeat rate: 1 s or 10 s?', fs=20)
    s.t(x, y + 64, 'Variant: same subject, but a value, unit, modal verb or condition differs.', fs=10, color=DARK)
    s.caps(x, y + 88, 'SUGGESTED BY')
    s.prov(x + 90, y + 88, 'mech', 'Mechanical methods')
    s.prov(x + 240, y + 88, 'ai', 'AI judge')
    # A / B
    yy = y + 112
    A = 'The Flight Control Subsystem shall transmit a heartbeat message to the Ground Station every 1 second.'
    B = 'The Flight Control Subsystem shall transmit a heartbeat message to the Ground Station every 10 seconds.'
    for i, (lab, rid, txt, own, alloc, diffs) in enumerate([('A', 'REQ-FCS-0215', A, 'FCS team', 'Flight Control', ('1', 'second')), ('B', 'REQ-GCS-0102', B, 'Ground team', 'Ground Station', ('10', 'seconds'))]):
        bx = x + i * 310
        s.card(bx, yy, 300, 200)
        s.caps(bx + 12, yy + 10, lab + ' · ' + rid, color=INK)
        tokw(s, bx + 12, yy + 30, 276, txt, fs=11, differs=diffs)
        for j, (k, v, dif) in enumerate([('Owner', own, True), ('Level', 'System', False), ('Verification', 'Test', False), ('Allocated to', alloc, True), ('Baseline', 'Pre-baseline', False)]):
            ry = yy + 106 + j * 18
            s.t(bx + 12, ry, k, fs=9, color=SOFT)
            if dif:
                s.r(bx + 100, ry - 2, len(v) * 5.4 + 40, 14, fill='#FFF0D2', stroke='#FFF0D2', rounded=False)
                s.t(bx + 104, ry, v + ' (differs)', fs=9, color='#6B3D00')
            else:
                s.t(bx + 104, ry, v, fs=9, color=DARK)
    s.num(978, yy - 8, 3)
    # key
    ky = yy + 208
    s.t(x, ky, 'Key', fs=9, color=SOFT)
    for lab, fill, kx in [('number or unit', '#ffe0ad', 28), ('shall / should', '#d5e3ff', 128), ('not', '#ffd3ce', 228), ('condition', '#e8deff', 266)]:
        s.r(x + kx, ky - 2, len(lab) * 5.4 + 8, 14, fill=fill, stroke=fill, rounded=False)
        s.t(x + kx + 4, ky, lab, fs=9, color=DARK)
    s.t(x + 350, ky, 'underlined = differs between A and B', fs=9, color='#b35a00')
    # methods
    my = ky + 28
    s.card(x, my, dw, 168)
    s.num(978, my - 8, 4)
    s.caps(x + 14, my + 10, 'MECHANICAL METHODS')
    vals = [('Text match (fuzzy)', .96), ('Keyword overlap (TF-IDF)', .86), ('Meaning (embedding)', .97), ('Cross-encoder', .93),
            ('A implies B (NLI)', .81), ('B implies A (NLI)', .79), ('Contradiction (NLI)', .05), ('Combined: same obligation', .71)]
    for i, (nm, v) in enumerate(vals):
        cxx = x + 14 + (i // 4) * 300
        ryy = my + 34 + (i % 4) * 24
        s.t(cxx, ryy, nm, fs=9, color=DARK)
        s.bar(cxx + 140, ryy + 1, 110, v, h=9)
        s.t(cxx + 258, ryy, '%.2f' % v, fs=9, color=INK, family=3)
    s.t(x + 14, my + 134, d.wrap('Every similarity score is high, yet the interval differs tenfold. Similarity cannot see this; the number guard can. Scores are uncalibrated until a gold set exists.', 580, 9), fs=9, color=SOFT)
    # guards
    gy = my + 182
    s.card(x, gy, dw, 214)
    s.num(978, gy - 8, 5)
    s.caps(x + 14, gy + 10, 'GUARDS · 9 OF 10 PASS · 1 BLOCKING')
    for i, g in enumerate(GUARDS):
        col, row = divmod(i, 5)
        st = 'f' if i == 2 else 'p'
        guard_row(s, x + 18 + col * 300, gy + 38 + row * 34, 250, g, st, '1 second ≠ 10 seconds' if i == 2 else '')
    # ai
    ay = gy + 228
    s.card(x, ay, dw, 216)
    s.num(978, ay - 8, 6)
    s.prov(x + 14, ay + 12, 'ai')
    s.caps(x + 32, ay + 12, 'AI PROPOSAL · DRAFT', color=AIC)
    s.t(x + 330, ay + 10, 'VARIANT · 88% · 3 of 3 runs agree', fs=10, color=INK)
    s.t(x + 14, ay + 34, d.wrap('Same actor, action and object. The interval differs (1 s against 10 s) and the two owners differ, so neither wording can replace the other.', 580, 10), fs=10, color=DARK)
    for i, (who, q) in enumerate([('A', 'every 1 second'), ('B', 'every 10 seconds')]):
        s.r(x + 14 + i * 200, ay + 80, 188, 24, fill='#f8f0fc', stroke=AIC)
        s.t(x + 22 + i * 200, ay + 86, who + '  “' + q + '”', fs=10, color=DARK)
    s.t(x + 14, ay + 118, 'Suggested next step:  Keep both and ask the two owners which interval applies.', fs=10, color=INK)
    s.r(x + 14, ay + 146, 440, 26, 'Proposal: no merged wording (a merge would break the number guard)', fill=GREY, stroke=LINE, fs=9, align='left', pad=8, dash=True)
    s.t(x + 14, ay + 186, 'Why was this suggested?  ▸  model, prompt version, runs, inputs, guards', fs=10, color=ACC)
    # impact
    iy = ay + 230
    s.card(x, iy, dw, 104)
    s.num(978, iy - 8, 7)
    s.caps(x + 14, iy + 10, 'WHAT HAPPENS IF YOU FOLLOW THE SUGGESTION')
    for i, t_ in enumerate(['Nothing is merged. A "variant of" link joins the two requirements.', 'A question is sent to FCS team and Ground team.', 'Cross-owner changes need both owners to approve.']):
        s.t(x + 14, iy + 34 + i * 20, '•  ' + t_, fs=10, color=DARK)
    # action card
    ac = iy + 118
    s.card(x, ac, dw, 150)
    s.num(978, ac - 8, 8)
    s.r(x + 14, ac + 14, 16, 16, fill='#ffffff', stroke=INK, sw=2)
    s.t(x + 40, ac + 15, 'I have read both wordings and the guard results.', fs=10, color=INK)
    for i, (lab, prim) in enumerate([('Keep both and link', True), ('Ask the owners', False), ('Reject suggestion', False), ('Skip', False)]):
        s.btn(x + 14 + i * 148, ac + 50, 138, 40, lab, primary=prim, fs=10)
    s.t(x + 14, ac + 106, 'Your decision appears here once you choose, with an Undo link.', fs=9, color=SOFT)
    s.t(x + 14, ac + 124, 'Nothing is written to the source model by any of these buttons.', fs=9, color=SOFT)
    # sign-off
    sy = ac + 164
    s.card(x, sy, dw, 214)
    s.num(978, sy - 8, 9)
    s.caps(x + 14, sy + 10, 'FOUR-LENS SIGN-OFF')
    for i, nm in enumerate(['Systems engineer', 'Process engineer', 'UI/UX engineer', 'New user']):
        s.chip(x + 14 + i * 148, sy + 30, 138, 18, nm + ': pending', fs=8, dash=True, fill='#ffffff')
    s.t(x + 14, sy + 60, 'Checks for the Systems engineer lens', fs=10, color=INK)
    for i, (lab, fill, txt) in enumerate([('Blocked', RED_BG, 'Numbers, units, shall/should and not agree between A and B.'), ('Needs you', AMBER_BG, 'Owners differ (FCS team and Ground team). Both must approve any change.'),
                                         ('Pass', GREEN_BG, 'Verification method is the same (Test).'), ('Needs you', AMBER_BG, 'Confirm trace links, rationale and allocation stay put.')]):
        s.chip(x + 14, sy + 82 + i * 22, 70, 16, lab, fill=fill, fs=8)
        s.t(x + 94, sy + 84 + i * 22, txt, fs=9, color=DARK)
    s.btn(x + 14, sy + 176, 220, 28, 'Sign as Systems engineer', fs=10, disabled=True)
    s.t(x + 246, sy + 184, 'Unlocks after you record a decision.', fs=9, color=SOFT)
    # remaining callouts
    s.num(cx + 160, cy - 10, 1)
    s.num(978, y - 8, 2)
    d.frame_end()
    return ['Queue is ordered safest first (Lane A, then B, then C). Lane, relationship and status are all text labels, so colour is never the only signal. It stays visible while the detail scrolls.',
            'Relationship in plain words, plus the blind-first switch. When on, the AI panel stays hidden until you record your own first call.',
            'A and B side by side. Numbers, units, shall/should, not and conditions are highlighted; the words that differ are underlined; owner and allocation differences are flagged in the metadata.',
            'Every mechanical score shown as a raw value with a bar. The note says plainly that scores are uncalibrated until a human-labelled gold set exists.',
            'Ten deterministic guards. A failing guard names the reason and blocks the merge action, so the AI cannot override it.',
            'AI proposal, marked with the diamond. Verdict, vote agreement, verbatim quotes and the next step. "Why was this suggested?" opens model, prompt version and inputs.',
            'Consequences are stated before any click: what links, what is flagged suspect, who gets asked.',
            'Decision card. Lanes B and C require the read box before any decision unlocks (Skip is always open). Merge is not offered when a guard blocks it.',
            'Four lenses, each with its own checklist of Pass, Needs you or Blocked. Approved means four of four have signed.']


def s_actions(d, ox, oy):
    W, H = 1000, 640
    d.frame_begin(ox, oy, W, H, '5 · Decision card: six states')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cards = [
        ('a · Lane A (low risk)', 'No read-gate. Primary action is the safe default.', 'none', [('Accept merge', True, False), ('Edit wording', False, False), ('Not a duplicate', False, False), ('Skip', False, False)], None),
        ('b · Lane B or C, not yet read', 'Decisions are dashed and disabled. Skip stays open. A line says why.', 'unchecked', [('Keep both and link', True, True), ('Ask the owners', False, True), ('Reject', False, True), ('Skip', False, False)], 'Tick the box to unlock your decision.'),
        ('c · Read, ready to decide', 'Box ticked. All decisions enabled.', 'checked', [('Keep both and link', True, False), ('Ask the owners', False, False), ('Reject', False, False), ('Skip', False, False)], None),
        ('d · Edit the proposed wording', 'Text box opens inline. The guards re-run on Save.', 'edit', [('Save edited wording', True, False), ('Cancel edit', False, False)], None),
        ('e · Decided', 'Decision recorded in the audit log. Undo is one click. Sign-off unlocks.', 'decided', [], None),
        ('f · A guard blocks the merge', 'Merge is not offered at all. Only link, ask, reject and skip remain.', 'blocked', [('Keep both and link', True, False), ('Ask the owners', False, False), ('Reject', False, False), ('Skip', False, False)], None),
    ]
    for i, (title, sub, mode, btns, helper) in enumerate(cards):
        bx, by = 20 + (i % 2) * 490, 20 + (i // 2) * 200
        s.card(bx, by, 470, 184)
        s.t(bx + 14, by + 10, title, fs=12, color=INK)
        s.t(bx + 14, by + 28, d.wrap(sub, 440, 9), fs=9, color=SOFT)
        yy = by + 56
        if mode in ('unchecked', 'checked'):
            s.r(bx + 14, yy, 16, 16, fill='#ffffff', stroke=INK, sw=2)
            if mode == 'checked':
                s.poly([(bx + 17, yy + 8), (bx + 21, yy + 12), (bx + 27, yy + 4)], typ='line', stroke=INK, sw=2.5)
            s.t(bx + 40, yy + 1, 'I have read both wordings and the guard results.', fs=10, color=INK)
            yy += 30
        if mode == 'edit':
            s.r(bx + 14, yy, 440, 58, 'Upon a state change, the Flight Control Subsystem shall transmit a health status message to the Ground Station within 5 seconds.', fill='#ffffff', stroke=ACC, sw=2, fs=9, align='left', valign='top', pad=8, family=1)
            yy += 70
        if mode == 'blocked':
            s.r(bx + 14, yy, 440, 24, 'Guard "Numbers preserved" blocks merge: 1 second ≠ 10 seconds', fill=RED_BG, stroke=RED, fs=9, align='left', pad=8)
            yy += 34
        if mode == 'decided':
            s.r(bx + 14, yy, 440, 44, 'Your decision: Kept and linked. Recorded in the audit log.', fill=GREEN_BG, stroke=HUM, fs=10, align='left', pad=10)
            s.btn(bx + 14, yy + 56, 70, 28, 'Undo', fs=10)
            s.prov(bx + 100, yy + 62, 'human', 'Human decision')
        bxx = bx + 14
        for lab, prim, dis in btns:
            w = max(80, len(lab) * 6.2 + 28)
            s.btn(bxx, yy, w, 38, lab, primary=prim and not dis, disabled=dis, fs=10)
            bxx += w + 8
        if helper:
            s.t(bx + 14, yy + 50, helper, fs=9, color='#b35a00')
    d.frame_end()
    return ['Same card, six states. Each is a real state in the live prototype.',
            'The read-gate exists because a reviewer who has not read both wordings should not be able to approve a change.',
            'Disabled actions are dashed outlines, not just grey, and a sentence says why. Skip is never disabled.',
            'Undo is always one click and is logged. Nothing is final until four lenses sign.']
