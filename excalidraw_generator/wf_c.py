from wf import *
from wf_b import tokw, queue, LANE_FILL, REL_FILL


def para(s, x, y, text, w, fs=10, color=DARK, **kw):
    wrapped = s.d.wrap(text, w, fs)
    s.t(x, y, wrapped, fs=fs, color=color, **kw)
    return y + (wrapped.count('\n') + 1) * fs * 1.25


def s_methods(d, ox, oy):
    W, H = 1000, 900
    d.frame_begin(ox, oy, W, H, '6 · Methods and metrics')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Methods and metrics')
    s.h1(cx, cy, 'Methods and metrics', fs=24)
    para(s, cx, cy + 32, 'Every suggestion source is scored the same way, so the mechanical methods and the AI can be compared fairly.', 800, 10)
    s.r(cx, cy + 56, 816, 46, fill=AMBER_BG, stroke='#f1c40f')
    para(s, cx + 12, cy + 62, 'Illustrative numbers. No gold set of human-labelled pairs exists yet, so the accuracy figures below are placeholders that show the layout. The "This session" and "Guards" panels are computed live from what you do in the sample.', 790, 9, '#5c4400')
    y1 = cy + 116
    s.card(cx, y1, 816, 262)
    s.num(cx + 800, y1 - 8, 1)
    s.caps(cx + 14, y1 + 10, 'EACH SOURCE, SIDE BY SIDE (SAMPLE VALUES)')
    cols = [('Source', 14), ('Precision (95% range)', 250), ('Recall', 470), ('Calibration error', 610), ('Pairs scored', 730)]
    for lab, off in cols:
        s.t(cx + off, y1 + 32, lab, fs=9, color=SOFT)
    rows = [('Text match (fuzzy)', 'mech', .61, '0.47–0.73', .48, .21, 63), ('Keyword overlap (TF-IDF)', 'mech', .58, '0.44–0.70', .52, .18, 63),
            ('Embedding model A', 'mech', .71, '0.55–0.83', .84, .09, 41), ('Embedding model B', 'mech', .69, '0.53–0.81', .81, .11, 41),
            ('Cross-encoder re-score', 'mech', .78, '0.62–0.88', .76, .07, 41), ('Combined score', 'mech', .86, '0.72–0.94', .80, .04, 41), ('AI judge', 'ai', .83, '0.44–0.97', .71, .08, 4)]
    for i, (nm, k, p, rg, r, e, n) in enumerate(rows):
        yy = y1 + 52 + i * 26
        s.line([(cx, yy - 4), (cx + 816, yy - 4)], stroke='#e9ecef', sw=1)
        s.prov(cx + 14, yy + 2, k, nm, fs=10)
        s.bar(cx + 250, yy + 4, 100, p, h=9)
        s.t(cx + 358, yy + 1, '%.2f' % p, fs=10, color=INK, family=3)
        s.t(cx + 394, yy + 2, rg, fs=8, color=SOFT, family=3)
        s.bar(cx + 470, yy + 4, 80, r, h=9)
        s.t(cx + 558, yy + 1, '%.2f' % r, fs=10, color=INK, family=3)
        s.t(cx + 610, yy + 1, '%.2f' % e, fs=10, color=INK, family=3)
        s.t(cx + 730, yy + 1, str(n), fs=10, color=INK, family=3)
    s.t(cx + 14, y1 + 238, 'The AI judge scored few pairs, so its range is wide. Read the range, not just the number.', fs=9, color=SOFT)
    y2 = y1 + 276
    s.card(cx, y2, 400, 192)
    s.num(cx + 384, y2 - 8, 2)
    s.caps(cx + 14, y2 + 10, 'MECHANICAL AGAINST AI (SAMPLE VALUES)')
    for i, (n, lab, sub) in enumerate([('9', 'Both suggest a merge', 'Strongest candidates'), ('6', 'Mechanical only', 'Check for lookalikes'), ('3', 'AI only', 'Check for invented links'), ('23', 'Neither', 'Left alone')]):
        bx, by = cx + 14 + (i % 2) * 190, y2 + 32 + (i // 2) * 60
        s.r(bx, by, 180, 52, fill=GREY, stroke=MID)
        s.t(bx + 10, by + 6, n, fs=20, color=INK)
        s.t(bx + 54, by + 8, lab, fs=9, color=INK)
        s.t(bx + 54, by + 24, sub, fs=8, color=SOFT)
    para(s, cx + 14, y2 + 156, 'Kappa 0.58. Agreement is not accuracy: both can miss the same thing. Disagreements are the best pairs to label next.', 372, 9, SOFT)
    s.card(cx + 416, y2, 400, 192)
    s.num(cx + 800, y2 - 8, 3)
    s.caps(cx + 430, y2 + 10, 'HOW OFTEN PEOPLE ACCEPT, BY CONFIDENCE (SAMPLE)')
    for i, (b, v) in enumerate([('Under 0.50', .31), ('0.50 to 0.70', .52), ('0.70 to 0.90', .74), ('Over 0.90', .93)]):
        yy = y2 + 34 + i * 24
        s.t(cx + 430, yy, b, fs=9, color=DARK)
        s.bar(cx + 520, yy + 1, 190, v, h=9)
        s.t(cx + 722, yy, '%d%%' % round(v * 100), fs=9, color=INK, family=3)
    para(s, cx + 430, y2 + 136, 'Acceptance alone can flatter the AI, because people tend to agree with it. The check is the planted wrong suggestions: 0 of 6 were accepted.', 372, 9, SOFT)
    y3 = y2 + 206
    s.card(cx, y3, 400, 172)
    s.num(cx + 384, y3 - 8, 4)
    s.caps(cx + 14, y3 + 10, 'THIS SESSION (LIVE)')
    for i, (k, v) in enumerate([('Decisions made', '0 of 7'), ('Followed the first suggestion', '0'), ('Rejected the suggestion', '0'), ('Edited the AI wording', '0'), ('Decisions undone', '0')]):
        s.t(cx + 14, y3 + 36 + i * 24, k, fs=10, color=DARK)
        s.t(cx + 330, y3 + 36 + i * 24, v, fs=10, color=INK, family=3)
    s.card(cx + 416, y3, 400, 172)
    s.num(cx + 800, y3 - 8, 5)
    s.caps(cx + 430, y3 + 10, 'GUARDS (LIVE FROM THE SAMPLE)')
    for i, (k, v) in enumerate([('Checks run', '70'), ('Passed', '67 (96%)'), ('Warnings', '1'), ('Blocked a merge', '2'), ('AI judgements stopped by a guard', '2 of 4'), ('Quoted evidence found verbatim', '9 of 9')]):
        s.t(cx + 430, y3 + 34 + i * 22, k, fs=10, color=DARK)
        s.t(cx + 720, y3 + 34 + i * 22, v, fs=10, color=INK, family=3)
    d.frame_end()
    return ['One table, one scoring method, mechanical and AI side by side. Provenance marks (square or diamond) identify each source. The AI row has a wide range because only four pairs were judged.',
            'Mechanical against AI: where they agree is the strongest evidence; where they disagree is what to label next. Agreement is explicitly not accuracy.',
            'Acceptance is shown with a warning that people anchor on AI. The real check is planted wrong suggestions that should be rejected.',
            'Live panel: counts what the reviewer actually did this session, so the human side is measured too.',
            'Guards panel: how often a deterministic check stopped the AI. This is the evidence that the guards earn their place.']


def audit_row(s, x, y, seq, tm, kind, actor, text, about, prev, h, bad=False, broken=False):
    s.r(x, y, 816, 50, fill='#fff0f0' if bad else '#ffffff', stroke='#e9ecef', rounded=False)
    s.t(x + 14, y + 8, str(seq), fs=10, color=INK, family=3)
    s.t(x + 44, y + 8, tm, fs=9, color=DARK, family=3)
    s.prov(x + 112, y + 8, kind, {'mech': 'Mechanical', 'ai': 'AI', 'human': 'Human'}[kind], fs=9)
    s.t(x + 212, y + 8, actor, fs=9, color=DARK)
    para(s, x + 302, y + 8, text, 210, 9, INK)
    s.t(x + 530, y + 8, about, fs=9, color=DARK)
    s.t(x + 650, y + 6, prev + '\n→ ' + h, fs=8, color=RED if bad else SOFT, family=3)
    if broken:
        s.t(x + 740, y + 32, 'chain broken', fs=8, color=RED)


def s_audit(d, ox, oy, tamper=False):
    W, H = 1000, 640
    d.frame_begin(ox, oy, W, H, '7 · Audit log: ' + ('tamper detected' if tamper else 'chain verified'))
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Audit log')
    s.h1(cx, cy, 'Audit log', fs=24)
    para(s, cx, cy + 32, 'Every suggestion and every decision is an event. Each event carries a fingerprint that includes the one before it, so editing an old entry breaks the chain. Undo adds a new event; it never deletes one.', 800, 10)
    s.btn(cx, cy + 74, 130, 32, 'Verify the chain', primary=True, fs=10)
    s.r(cx + 150, cy + 82, 16, 16, fill='#ffffff', stroke=INK, sw=2)
    if tamper:
        s.poly([(cx + 153, cy + 90), (cx + 157, cy + 94), (cx + 163, cy + 86)], typ='line', stroke=INK, sw=2.5)
    s.t(cx + 176, cy + 83, 'Demo: alter entry 2 after the fact', fs=10, color=INK)
    if tamper:
        s.r(cx, cy + 118, 816, 34, 'Chain broken at entry 2. The entry no longer matches its fingerprint.', fill=RED_BG, stroke=RED, fs=10, align='left', pad=12)
    else:
        s.r(cx, cy + 118, 816, 34, 'Chain verified: all 6 entries match their fingerprints.', fill=GREEN_BG, stroke=HUM, fs=10, align='left', pad=12)
    ty = cy + 166
    s.r(cx, ty, 816, 26, fill=DARK, stroke=DARK, rounded=False)
    for lab, off in [('#', 14), ('Time', 44), ('Source', 112), ('Actor', 212), ('Event', 302), ('About', 530), ('Fingerprint (previous → this)', 650)]:
        s.t(cx + off, ty + 7, lab, fs=8, color='#ffffff', family=3)
    rows = [(1, '09:02:11', 'mech', 'Pipeline', 'Read and normalised 214 requirements', 'whole project', '00000000', '3be1a07c'),
            (2, '09:02:48', 'mech', 'Pipeline', 'Built 39 candidate pairs and 7 clusters (edited after the fact)' if tamper else 'Built 41 candidate pairs and 7 clusters', 'CL-01 to CL-07', '3be1a07c', '9d40c2e5'),
            (3, '09:03:30', 'ai', 'AI judge', 'Judged 4 clusters, drafted wording for 2; ten guards run on every proposal', 'CL-01 to CL-06', '9d40c2e5', '51ab7710'),
            (4, '09:14:02', 'human', 'Systems engineer', 'Decided CL-03: Kept and linked', 'CL-03', '51ab7710', 'c7e90d3a'),
            (5, '09:15:40', 'human', 'Systems engineer', 'Signed off CL-03', 'CL-03', 'c7e90d3a', '08fd62b4'),
            (6, '09:16:05', 'human', 'Systems engineer', 'Undo: CL-03 decision reversed (a new event)', 'CL-03', '08fd62b4', 'e21a9f6c')]
    for i, r in enumerate(rows):
        audit_row(s, cx, ty + 26 + i * 50, *r, bad=tamper and r[0] == 2, broken=tamper and r[0] > 2)
    s.num(cx + 800, cy + 70, 1)
    s.num(cx + 800, cy + 112, 2)
    s.num(cx + 800, ty - 8, 3)
    d.frame_end()
    return ['Verify and the tamper demo are real controls, so a reviewer can see the chain break instead of trusting a claim.',
            ('Result bar is text plus a colour, and it names the first bad entry.' if tamper else 'Success states what was checked (all 6 entries), not just "OK".'),
            'Each event: time, provenance mark, actor, plain-language event, about, and fingerprint chain. Undo is a new row, never a delete.']


def s_export(d, ox, oy, prepared=False):
    W, H = 1000, 800 if prepared else 640
    d.frame_begin(ox, oy, W, H, '8 · Export to documents: ' + ('draft package prepared' if prepared else 'nothing approved yet'))
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Export to documents')
    s.h1(cx, cy, 'Export to documents', fs=24)
    para(s, cx, cy + 32, 'Documents are generated from the approved list only, never from copied text. This step prepares a draft package. It does not change your source model.', 800, 10)
    y = cy + 66
    hh = 232 if prepared else 150
    s.card(cx, y, 816, hh)
    s.num(cx + 800, y - 8, 1)
    s.caps(cx + 14, y + 10, 'CHECK BEFORE YOU PREPARE')
    if prepared:
        s.t(cx + 14, y + 32, 'Approved by all four lenses (2)', fs=11, color=INK)
        for i, (cid, t_, dec) in enumerate([('CL-03', 'Heartbeat rate: 1 s or 10 s?', 'Kept and linked'), ('CL-01', 'Health message timing, two wordings', 'Merge accepted')]):
            yy = y + 56 + i * 32
            s.r(cx + 14, yy, 788, 26, fill=GREY, stroke=MID)
            s.t(cx + 24, yy + 6, cid + '  ' + t_ + ' · ' + dec, fs=10, color=DARK)
            s.btn(cx + 716, yy + 1, 76, 24, 'Change', fs=9)
        s.t(cx + 14, y + 128, 'Decided, waiting for sign-off (1)', fs=11, color=INK)
        s.r(cx + 14, y + 150, 788, 26, fill=GREY, stroke=MID)
        s.t(cx + 24, y + 156, 'CL-02  still needs: Process engineer, UI/UX engineer, New user', fs=10, color=DARK)
        s.btn(cx + 716, y + 151, 76, 24, 'Open', fs=9)
        s.t(cx + 14, y + 192, '4 clusters have no decision yet. They are left out of the package.', fs=10, color=SOFT)
    else:
        s.t(cx + 14, y + 32, 'Approved by all four lenses (0)', fs=11, color=INK)
        s.t(cx + 14, y + 54, 'Nothing is approved yet. Decide a cluster in the review queue, then have each lens sign off.', fs=10, color=DARK)
        s.t(cx + 14, y + 84, 'Decided, waiting for sign-off (0)', fs=11, color=INK)
        s.t(cx + 14, y + 112, '7 clusters have no decision yet. They are left out of the package.', fs=10, color=SOFT)
    y += hh + 14
    s.card(cx, y, 816, 270)
    s.num(cx + 800, y - 8, 2)
    s.caps(cx + 14, y + 10, 'PACKAGE')
    s.t(cx + 14, y + 32, 'Draft baseline ID', fs=10, color=INK)
    s.r(cx + 14, y + 50, 220, 32, 'DRAFT-0001', fill='#ffffff', stroke=INK, fs=11, align='left', pad=10, family=3)
    s.t(cx + 14, y + 96, 'Format', fs=10, color=INK)
    fm = [('Sphinx-Needs (reStructuredText)', 'Needs-as-code pages with trace tables'), ('StrictDoc (SDoc)', 'Requirements document, HTML or PDF'), ('Word (.docx)', 'Built from a Word template'), ('ReqIF 1.2', 'Round trip back to MSOSA')]
    for i, (a, b) in enumerate(fm):
        bx, by = cx + 14 + (i % 2) * 396, y + 116 + (i // 2) * 48
        on = i == 0
        s.r(bx, by, 388, 42, fill='#F1F6FF' if on else '#ffffff', stroke=ACC if on else LINE, sw=2 if on else 1)
        s.shape('ellipse', bx + 10, by + 14, 14, 14, fill=ACC if on else '#ffffff', stroke=ACC if on else SOFT, sw=2)
        s.t(bx + 34, by + 6, a, fs=10, color=INK)
        s.t(bx + 34, by + 22, b, fs=8, color=SOFT)
    by2 = y + 220
    s.btn(cx + 14, by2, 300, 38, 'Prepare 2 changes as a draft package' if prepared else 'Prepare draft package', primary=True, disabled=not prepared, fs=11)
    s.t(cx + 330, by2 + 12, 'Preparing is logged. You can prepare again after more approvals.' if prepared else 'Disabled until at least one change is approved by all four lenses.', fs=9, color=SOFT)
    if prepared:
        y += 284
        s.r(cx, y, 816, 90, fill=GREEN_BG, stroke=HUM)
        s.t(cx + 14, y + 10, 'Draft package prepared for DRAFT-0001', fs=12, color=INK)
        s.t(cx + 14, y + 32, 'Files: requirements.rst, traceability.rst, change-record.rst', fs=10, color=INK, family=3)
        para(s, cx + 14, y + 54, 'Each entry shows the baseline ID and lists any superseded or alias IDs. Your source model is unchanged.', 780, 9, DARK)
        s.num(cx + 800, y - 8, 3)
    d.frame_end()
    return ['Gate list: only changes signed by all four lenses go out. Waiting items say exactly which lens is missing and link back. Undecided clusters are named and left out.' if prepared else 'Empty state explains what to do next instead of showing a blank list. The primary action is disabled and says why.',
            'Format choice and baseline ID. Formats feed the document-authoring tools: Sphinx-Needs, StrictDoc, Word from a template, or ReqIF round trip.',
            'Result states the files and the guarantee that the source model is unchanged. Every Prepare click is an audit event.' if prepared else 'Nothing is written until at least one change has four of four sign-offs.']


def s_glossary(d, ox, oy):
    W, H = 1000, 700
    d.frame_begin(ox, oy, W, H, '9 · Glossary and help (new-user support)')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill=GREY, stroke=GREY, rounded=False)
    cx, cy = shell(s, W, H, 'Glossary and help')
    s.h1(cx, cy, 'Glossary and help', fs=24)
    s.btn(cx + 716, cy, 100, 30, 'Close', fs=10)
    terms = [('Draft', 'A suggestion nobody has approved yet. Everything you see here is a draft.'), ('Cluster', 'A small group of requirements that look alike. You decide what happens to each one.'),
             ('Equivalent', 'Same obligation, worded differently. Safe to merge once checked.'), ('Variant', 'Same subject, but a value, unit, shall/should or condition differs. Never merged automatically.'),
             ('Subsumes', 'One requirement contains the other and adds more. Keep the stricter one and link the other.'), ('Conflict', 'Both cannot be true at once. Escalated to the owners, never merged.'),
             ('Merge', 'Combine into one surviving requirement. Other IDs stay as aliases so no trace link is lost.'), ('Supersede', 'Mark the older requirement as replaced. Its ID and links stay.'),
             ('Baseline', 'A formally frozen version of the requirements. Changing one afterwards needs a change request.'), ('Suspect link', 'A trace link flagged for re-checking because something it points to changed.'),
             ('Guard', 'A plain code check that blocks a suggestion if it changes a number, unit, shall/should, a "not" or a condition.'), ('Lane A, B, C', 'Risk lanes. A is low risk, B needs you to read the evidence, C is a conflict.'),
             ('Lens', 'One reviewer point of view: systems engineer, process engineer, UI/UX engineer or new user.'), ('Provenance', 'Who or what made a suggestion: a mechanical method (square), the AI (diamond) or a person (circle).'),
             ('Embedding', 'A numeric fingerprint of meaning, used to find requirements that say similar things.'), ('NLI', 'A model that says whether one sentence implies, contradicts or is unrelated to another.'),
             ('Gold set', 'Pairs of requirements that people have labelled. Accuracy can only be measured against it.'), ('Calibration', 'Whether "90% sure" turns out right about 90% of the time.')]
    for i, (t_, x_) in enumerate(terms):
        col, row = i // 9, i % 9
        bx, by = cx + col * 412, cy + 48 + row * 62
        s.card(bx, by, 404, 54)
        s.t(bx + 12, by + 8, t_, fs=11, color=INK)
        para(s, bx + 12, by + 25, x_, 380, 8)
    s.num(cx + 800, cy - 24, 1)
    s.num(cx - 24, cy + 52, 2)
    d.frame_end()
    return ['Close returns to exactly where you were. Help is one click from every screen (sidebar).',
            'Eighteen plain-language terms, each one or two sentences. The provenance marks are explained here too.']


def phone(d, ox, oy, title, h=800):
    d.frame_begin(ox, oy, 390, h, title)
    s = Scr(d, ox, oy)
    s.r(0, 0, 390, h, fill=GREY, stroke=GREY, rounded=False)
    return s


def s_mobile(d, ox, oy):
    H = 800
    # phone 1
    s = phone(d, ox, oy, '10a · Phone: open a project', H)
    s.r(16, 16, 20, 20, fill=ACC, stroke=ACC)
    s.t(46, 18, 'Requirements Consolidator', fs=11, color=INK)
    s.chip(16, 48, 200, 16, 'PROTOTYPE · SAMPLE DATA ONLY', fill='#ffffff', fs=8)
    s.h1(16, 80, 'Open a requirements\nproject', fs=24)
    s.caps(16, 152, 'CHOOSE A SOURCE')
    for i, (a, tag, b) in enumerate([('SysML v2 model', 'API or KPAR', 'Connect to an API endpoint or open a .sysml or KPAR package.'), ('ReqIF export', 'ReqIF 1.2', 'Open a .reqif exported from MSOSA via Cameo Requirements Modeler.'),
                                      ('MSOSA project file', '.mdzip', 'Experimental: zipped XMI, element text and links only.'), ('Spreadsheet', 'CSV / XLSX', 'Fallback: one requirement per row.')]):
        yy = 172 + i * 92
        s.card(16, yy, 358, 84)
        s.t(28, yy + 10, a, fs=12, color=INK)
        s.chip(282, yy + 10, 80, 16, tag, fs=8)
        para(s, 28, yy + 36, b, 330, 9)
    s.caps(16, 548, 'RECENT PROJECTS')
    for i, (a, b) in enumerate([('systems v2', 'SysML v2 model'), ('MSoSA', 'ReqIF export')]):
        s.card(16, 568 + i * 54, 358, 46)
        s.t(28, 576 + i * 54, a, fs=11, color=INK)
        s.t(28, 594 + i * 54, b + ' · opens the synthetic sample', fs=8, color=SOFT)
    s.card(16, 684, 358, 100)
    s.t(28, 694, 'First time here?', fs=12, color=INK)
    para(s, 28, 714, 'Draft = suggested, not approved. Your source model is never changed.', 330, 9)
    s.btn(28, 744, 170, 32, 'Open the sample project', primary=True, fs=10)
    d.frame_end()
    # phone 2
    s = phone(d, ox + 430, oy, '10b · Phone: workspace top (menu, title, queue)', H)
    s.r(0, 0, 390, 300, fill=DARK, stroke=DARK, rounded=False)
    s.t(16, 14, 'Consolidator', fs=12, color='#ffffff')
    s.r(16, 38, 358, 40, fill='#495057', stroke='#495057')
    s.t(26, 44, 'PROJECT', fs=7, color='#adb5bd', family=3)
    s.t(26, 57, 'Reference air vehicle', fs=10, color='#ffffff')
    for i, lab in enumerate(['Overview', 'Review queue', 'Methods and metrics', 'Audit log', 'Export to documents']):
        yy = 88 + i * 28
        if lab == 'Review queue':
            s.r(10, yy, 370, 26, lab, fill='#1f4e8f', stroke='#1f4e8f', color='#ffffff', fs=10, align='left', pad=10)
            s.chip(340, yy + 5, 28, 16, '7', fill='#ffffff', fs=8)
        else:
            s.t(20, yy + 7, lab, fs=10, color='#dee2e6')
    s.t(16, 236, 'REVIEWING AS', fs=7, color='#adb5bd', family=3)
    for i, lab in enumerate(['Systems engineer', 'Process engineer']):
        s.r(16 + i * 182, 252, 176, 28, lab, fill='#ffffff' if i == 0 else 'transparent', stroke='#6c757d', color=INK if i == 0 else '#dee2e6', fs=9, align='left', pad=8)
    s.t(16, 286, '… UI/UX engineer · New user · Glossary and help · Close project', fs=8, color='#adb5bd')
    for i, (a, b) in enumerate([('PROJECT', 'Reference air vehicle'), ('SOURCE', 'API or KPAR'), ('BASELINE', 'None, pre-baseline'), ('STATUS', 'DRAFT')]):
        s.r((i % 2) * 195, 300 + (i // 2) * 40, 195, 40, fill='#ffffff', stroke='#dee2e6', rounded=False)
        s.t((i % 2) * 195 + 12, 306 + (i // 2) * 40, a, fs=7, color=SOFT, family=3)
        s.t((i % 2) * 195 + 12, 320 + (i // 2) * 40, b, fs=10, color=INK)
    s.r(0, 380, 390, 56, fill=AMBER_BG, stroke='#f1c40f', rounded=False)
    s.chip(12, 388, 40, 14, 'DRAFT', fill='#ffffff', stroke=DARK, fs=8)
    para(s, 12, 408, 'Suggestions are proposals. Each stays a draft until all four lenses sign off.', 366, 9, '#5c4400')
    s.caps(16, 450, 'CLUSTERS · SAFEST FIRST')
    rows = [('CL-01', 'A', 'Health message timing, two wordings', 'Equivalent'), ('CL-02', 'A', 'Fault record retention', 'Equivalent'), ('CL-03', 'B', 'Heartbeat rate: 1 s or 10 s?', 'Variant'), ('CL-04', 'B', 'Fault logging: plain or with timestamp', 'Subsumes'), ('CL-05', 'B', 'Health display: shall or should?', 'Variant')]
    for i, (cid, ln, t_, rel) in enumerate(rows):
        yy = 470 + i * 64
        sel = i == 0
        s.r(16, yy, 358, 58, fill='#F1F6FF' if sel else '#ffffff', stroke=ACC if sel else LINE, sw=2 if sel else 1)
        s.t(28, yy + 8, cid, fs=10, color=INK, family=3)
        s.chip(292, yy + 6, 70, 14, 'Lane ' + ln, fill=LANE_FILL[ln], fs=8)
        s.t(28, yy + 26, t_, fs=10, color=DARK)
        s.chip(28, yy + 42, 70, 12, rel, fill=REL_FILL[rel], fs=7)
    s.t(16, 790, 'continues: CL-06, CL-07, then the selected cluster', fs=8, color=SOFT)
    d.frame_end()
    # phone 3
    s = phone(d, ox + 860, oy, '10c · Phone: one cluster, stacked', H)
    s.chip(16, 16, 54, 20, 'CL-01', fs=9)
    s.chip(78, 16, 130, 20, 'Lane A · low risk', fill=GREEN_BG, fs=9)
    s.chip(216, 16, 80, 20, 'Equivalent', fill=BLUE_BG, fs=9)
    s.btn(16, 44, 140, 26, 'Blind-first: off', fs=9)
    s.chip(164, 46, 80, 22, 'Suggested', fs=9, dash=True)
    s.h1(16, 82, 'Health message timing,\ntwo wordings', fs=20)
    para(s, 16, 134, 'Equivalent: same obligation, worded differently.', 358, 10)
    s.prov(16, 156, 'mech', 'Mechanical methods')
    s.prov(160, 156, 'ai', 'AI wording draft')
    for i, (lab, rid, txt) in enumerate([('A', 'REQ-FCS-0212', 'The Flight Control Subsystem shall transmit a health status message to the Ground Station within 5 seconds of a state change.'),
                                         ('B', 'REQ-GCS-0087', 'Upon a state change, the Flight Control Subsystem shall send a health status message to the Ground Station within 5000 milliseconds.')]):
        yy = 184 + i * 168
        s.card(16, yy, 358, 156)
        s.caps(28, yy + 10, lab + ' · ' + rid, color=INK)
        e = tokw(s, 28, yy + 30, 330, txt, fs=11, differs=('5', 'seconds', '5000', 'milliseconds'))
        s.t(28, yy + 118, 'Owner: FCS team   Level: System\nVerification: Test   Baseline: Pre-baseline', fs=8, color=SOFT)
    s.card(16, 524, 358, 120)
    s.caps(28, 534, 'MECHANICAL METHODS')
    for i, (n_, v) in enumerate([('Text match (fuzzy)', .58), ('Meaning (embedding)', .93), ('Cross-encoder', .90), ('Combined: same obligation', .97)]):
        s.t(28, 558 + i * 20, n_, fs=9, color=DARK)
        s.bar(190, 560 + i * 20, 120, v, h=8)
        s.t(318, 558 + i * 20, '%.2f' % v, fs=9, color=INK, family=3)
    s.card(16, 656, 358, 100)
    s.caps(28, 666, 'GUARDS · 10 OF 10 PASS')
    s.t(28, 686, 'All ten checks pass. Units: 5 seconds = 5000 ms after conversion.', fs=9, color=DARK)
    s.btn(28, 712, 150, 36, 'Accept merge', primary=True, fs=10)
    s.btn(186, 712, 90, 36, 'Edit', fs=10)
    s.t(16, 780, 'continues: AI proposal, impact, decision, sign-off', fs=8, color=SOFT)
    d.frame_end()
    return ['Phone layout is one column. The sidebar becomes a full menu at the top, then the title block, the draft banner, the queue, and the cluster detail stack.',
            'Touch targets stay at least 44 px high. Nothing scrolls sideways at 390 px.',
            'Same four-lens, guard, and provenance content as the desktop. Only the arrangement changes.']
