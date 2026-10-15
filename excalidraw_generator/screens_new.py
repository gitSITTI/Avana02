"""Board 12: the screens added after the V: labelling pairs, deciding one requirement and what it moves, the AI gate, keeping the work, and how it was checked.
A third worked example of adding screens (see EXCALIDRAW_GUIDE.md, recipe A).

Numbers and wordings here are the prototype's seeded SAMPLE values (the same ones its screenshots show). Nothing on this board comes from a real program.
Each function draws one frame at (ox, oy) and returns the notes boards_05_09.build_board places beside it."""
from wf2 import *  # noqa: F401,F403  (Doc, Scr, palette, new_frame, para, table, chk_list, kv, bar_h, shell2 ...)
from flows import box, mark, SRC_F, MECH_F, AI_F, HUM_F, GUARD_F  # noqa: F401
from g7 import radio

SIDE = ['Review queue', 'All requirements', 'Methods and metrics', 'Label pairs', 'AI use']
W = 1500


def head(s, cx, cy, title, sub, w=1100):
    s.h1(cx, cy, title, fs=26)
    return para(s, cx, cy + 40, sub, w, fs=11, color=DARK)


# ---------------------------------------------------------------- 12.1 label pairs
def n1_label_pairs(d, ox, oy):
    H = 1060
    s = new_frame(d, ox, oy, W, H, '12.1 · Label pairs: a blind card, six answers, and why the numbers can be trusted')
    cx, cy = shell2(s, W, H, 'Label pairs', 0, SIDE)
    head(s, cx, cy, 'Label pairs', 'Say whether two requirements are the same. Your labels turn the precision and recall on Methods and metrics from placeholders into measurements. You will not see what the app or the AI thought of a pair.')
    # the card
    x0, y0 = cx, cy + 96
    s.card(x0, y0, 780, 640)
    s.t(x0 + 20, y0 + 16, 'Pair 1 of 160', fs=16, color=INK)
    s.t(x0 + 600, y0 + 20, 'Labelling as Sam Okafor', fs=9, color=SOFT)
    s.t(x0 + 20, y0 + 50, 'Do these two requirements say the same thing?', fs=12, color=INK)
    wa = 'Reported position error of the Flight Control Subsystem shall be 5 m or less.'
    wb = 'Reported position error of the Flight Control Subsystem shall be 2 m or less while during start-up.'
    for k, (lab, rid, txt) in enumerate([('Requirement A', 'REQ-FCS-0328', wa), ('Requirement B', 'REQ-FCS-0342', wb)]):
        x = x0 + 20 + k * 370
        s.r(x, y0 + 80, 350, 124, fill=GREY, stroke=LINE)
        s.t(x + 12, y0 + 90, lab + '   ' + rid, fs=10, color=INK)
        s.t(x + 12, y0 + 108, 'Flight Control', fs=9, color=SOFT)
        para(s, x + 12, y0 + 128, txt, 326, fs=11, color=DARK)
    s.t(x0 + 20 + 370 + 12, y0 + 176, 'Words in B that differ:', fs=9, color=SOFT)
    s.chip(x0 + 20 + 370 + 142, y0 + 172, 40, 20, '2 m', fill='#ffe0ad', stroke='#ffe0ad', fs=9)
    s.chip(x0 + 20 + 370 + 188, y0 + 172, 130, 20, 'while during start-up', fill='#e8deff', stroke='#e8deff', fs=9)
    checkbox(s, x0 + 20, y0 + 222, True, 'Show the words in B that differ from A', fs=10)
    answers = [('1', 'Same requirement', 'They say the same thing with the same values. One of them is redundant.'),
               ('2', 'Same topic, different value', 'They set a different number, limit or condition for the same thing.'),
               ('3', 'One contains the other', 'One says everything the other says, and more.'),
               ('4', 'They contradict', 'Both cannot be true at once.'),
               ('5', 'Different things', 'Nothing to merge, link or compare.'),
               ('6', 'Cannot tell', 'You need the owner or more context. Left out of the numbers.')]
    for k, (n, name, help_) in enumerate(answers):
        y = y0 + 252 + k * 46
        s.r(x0 + 20, y, 740, 40, fill='#ffffff', stroke=INK if k < 5 else SOFT, dash=(k == 5), rounded=True)
        s.shape('ellipse', x0 + 30, y + 10, 20, 20, n, fs=9, fill=GREY, stroke=SOFT, pad=0)
        s.t(x0 + 62, y + 5, name, fs=11, color=INK)
        s.t(x0 + 62, y + 22, help_, fs=9, color=DARK)
    s.t(x0 + 20, y0 + 536, 'Why? (optional, kept with the label)', fs=10, color=INK)
    s.r(x0 + 20, y0 + 556, 430, 32, fill='#ffffff', stroke=LINE)
    s.btn(x0 + 470, y0 + 556, 120, 32, 'Skip for now', fs=10)
    s.btn(x0 + 604, y0 + 556, 156, 32, 'Undo my last label', fs=10, disabled=True)
    s.t(x0 + 20, y0 + 604, 'Keys 1 to 6 choose a label while the focus is in this box. Choosing records it and shows the next pair.', fs=9, color=SOFT)
    # right column
    rx = x0 + 804
    rw = W - rx - 24
    s.card(rx, y0, rw, 120)
    s.t(rx + 20, y0 + 14, 'Progress', fs=14, color=INK)
    bar_h(s, rx + 20, y0 + 44, rw - 100, 0.0)
    s.t(rx + rw - 70, y0 + 42, '0 of 160', fs=10, color=INK)
    para(s, rx + 20, y0 + 66, 'You have labelled 0 pairs. 160 pairs are still offered to you. All labellers together: 0 pairs labelled.', rw - 40, fs=9, color=DARK)
    s.card(rx, y0 + 136, rw, 100)
    s.t(rx + 20, y0 + 150, 'Do two people agree?', fs=14, color=INK)
    para(s, rx + 20, y0 + 176, 'No pair has been labelled by two people yet. One pair in five is offered to a second person, and nobody sees another person’s label.', rw - 40, fs=9, color=DARK)
    s.card(rx, y0 + 252, rw, 150)
    s.t(rx + 20, y0 + 266, 'The gold set file', fs=14, color=INK)
    s.btn(rx + 20, y0 + 292, 150, 28, 'Download the gold set', primary=True, disabled=True, fs=10)
    s.r(rx + 20, y0 + 330, rw - 40, 60, fill='#1e1e1e', stroke='#1e1e1e')
    s.t(rx + 30, y0 + 338, '{ "format": "reqin-gold-set/1",\n  "about": "Pairs of requirements labelled by\n  people. Each pair says how it was drawn ...', fs=9, color='#e9ecef', family=3)
    s.card(rx, y0 + 418, rw, 140, dash=True)
    s.t(rx + 20, y0 + 432, 'Try it with sample labels', fs=14, color=INK)
    para(s, rx + 20, y0 + 456, 'Adds 119 labels from two made-up labellers so you can see the measured scores before labelling anything yourself. They are marked as sample everywhere and are not real judgments.', rw - 40, fs=9, color=DARK)
    s.btn(rx + 20, y0 + 512, 140, 30, 'Load sample labels', fs=10)
    s.btn(rx + 172, y0 + 512, 160, 30, 'Remove sample labels', fs=10, disabled=True)
    # the table of groups
    ty = y0 + 664
    s.t(cx, ty, 'How the pairs were chosen, and why the numbers can be trusted', fs=14, color=INK)
    s.t(cx, ty + 22, 'The sample is 160 pairs from 778,128 in the project. Each group is a simple random sample with a fixed seed, so the same project always offers the same pairs.', fs=10, color=DARK)
    rows = [['A · Put in a cluster by the app', '1,294', '50', 'The app’s own suggestions.'],
            ['B1 · Read alike, not clustered', '3,698', '60', 'Text match or keyword overlap of 0.6 or more: the near misses.'],
            ['B2 · Same allocation, not alike', '100,257', '25', 'The rest of the pairs inside one allocation.'],
            ['C · Different allocations', '672,879', '25', 'The app never compares these.']]
    table(s, cx, ty + 46, [330, 150, 150, 560], ['GROUP OF PAIRS', 'PAIRS IT STANDS FOR', 'IN THE SAMPLE', 'WHAT IT IS'], rows, fs=10, bold_first=True, minh=26)
    for k, (x, y) in enumerate([(x0 + 360, y0 + 4), (x0 + 748, y0 + 248), (rx + rw - 28, y0 + 140), (cx - 12, ty + 40), (rx + rw - 28, y0 + 420)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['Blind on purpose. The card never says whether the app clustered the pair, what the scores were or what the AI thought. A person who has seen the app’s answer tends to agree with it, and that would make the app look better than it is.',
            'Six answers, keys 1 to 6. Five count (four kinds of related, or different things). “Cannot tell” leaves the pair out of the numbers. A note can travel with the label, a skipped pair comes back last, the last label can be undone.',
            'Every fifth pair also goes to a second person. When two people have labelled the same pairs the page shows how often they agree and the agreement beyond chance (kappa). A disagreement goes to the lead; the original labels stay in the record.',
            'A plain random sample would hold less than one cluster pair, because 1,294 of 778,128 pairs are in a cluster. So the pairs are drawn from four groups on purpose and each group is weighted by the pairs it stands for. Precision and recall come with a 95 percent range, not just a middle.',
            'Sample labels are made up from a rule that knows how the demonstration was made. They are marked as samples on every screen and in the file. Remove them before relying on any figure. Nothing here has been used on a real program.']


# ---------------------------------------------------------------- 12.2 one requirement, and what a decision moves
def n2_one_requirement(d, ox, oy):
    H = 1000
    s = new_frame(d, ox, oy, W, H, '12.2 · Decide one requirement, and see what the decision moves outside the list')
    cx, cy = shell2(s, W, H, 'All requirements', 0, SIDE)
    head(s, cx, cy, 'All requirements', 'Every requirement in scope, whether or not anything similar was found. Open any one, put another beside it if you like, and record what you decide.')
    # A: the list
    xa, ya = cx, cy + 96
    s.caps(xa, ya, 'A · OPEN ANY REQUIREMENT')
    for lab, cxo, cw, on in [('All 1248', 0, 70, False), ('Alone 446', 78, 90, True), ('Needs a decision 572', 176, 160, False)]:
        s.chip(xa + cxo, ya + 24, cw, 26, lab, fill=BLUE_BG if on else '#ffffff', stroke=INK if on else LINE, fs=9)
    s.card(xa, ya + 64, 400, 150)
    para(s, xa + 14, ya + 76, 'Map, grouped by allocation. Each square is one requirement. The list below does the same from the keyboard.', 370, fs=9, color=SOFT)
    for row in range(3):
        s.t(xa + 14, ya + 112 + row * 32, ['Flight Control · 252', 'Ground Station · 197', 'Data Recorder · 145'][row], fs=9, color=INK)
        for q in range(26):
            alone = (q * 7 + row * 3) % 5 in (0, 1)
            s.r(xa + 14 + q * 14.2, ya + 126 + row * 32 - 0, 9, 9, fill=GREY if not alone else '#ffffff', stroke=SOFT if alone else MID, rounded=False, sw=1.2)
    for k, (rid, txt) in enumerate([('REQ-FCS-0438', 'Upon receipt of a fault query, the Flight Control ...'), ('REQ-FCS-0440', 'The Flight Control Subsystem shall transmit a k...'),
                                    ('REQ-FCS-0443', 'The Flight Control Subsystem shall have a maximum mass of 12 kilograms.'), ('REQ-FCS-0445', 'The Flight Control Subsystem shall operate at a...')]):
        y = ya + 232 + k * 46
        on = k == 2
        s.r(xa, y, 400, 38, fill='#ffffff', stroke=ACC if on else '#dee2e6', sw=2 if on else 1)
        s.t(xa + 10, y + 5, rid, fs=9, color=INK, family=3)
        s.t(xa + 10, y + 21, s.d.wrap(txt, 380, 9).split('\n')[0], fs=9, color=DARK)
    para(s, xa, ya + 424, 'Alone means nothing similar was found, or a person took it out of its cluster. Those are the ones decided one at a time. A requirement in a cluster is decided with its cluster.', 400, fs=9, color=SOFT)
    # B: the panel
    xb = cx + 424
    s.caps(xb, ya, 'B · THE PANEL')
    s.card(xb, ya + 24, 460, 730)
    s.t(xb + 16, ya + 36, 'REQ-FCS-0443', fs=12, color=INK, family=3)
    s.chip(xb + 130, ya + 36, 170, 18, 'Not yet decided', fill=GREY, fs=9)
    para(s, xb + 16, ya + 66, 'The Flight Control Subsystem shall have a maximum mass of 12 kilograms.', 420, fs=12, color=INK)
    para(s, xb + 16, ya + 112, 'Flight Control · owner FCS team. Level 2 · System. Checked by analysis at system verification, 1 verification item linked. Not in any cluster: four methods compared it with every other requirement in its allocation and found nothing close.', 428, fs=9, color=SOFT)
    s.t(xb + 16, ya + 176, 'Compare with another requirement', fs=11, color=INK)
    for k, (rid, ov) in enumerate([('REQ-FCS-0564', 'text match 1.00 · keyword overlap 1.00'), ('REQ-FCS-0298', 'text match 0.92 · keyword overlap 0.78')]):
        y = ya + 198 + k * 44
        s.r(xb + 16, y, 428, 38, fill='#ffffff', stroke=LINE)
        s.t(xb + 26, y + 5, rid + '   maximum mass of ' + ('12 kilograms' if k == 0 else '2.5 kilograms'), fs=9, color=INK)
        s.t(xb + 26, y + 21, ov, fs=8, color=SOFT)
    s.t(xb + 16, ya + 294, 'Decide this requirement', fs=11, color=INK)
    for k, (kk, name, help_) in enumerate([('keep', 'Keep as written', 'It is a real requirement and the wording is fine.'),
                                          ('reword', 'Keep, with new wording', 'It is a real requirement. The wording needs to change.'),
                                          ('drop', 'Drop it', 'It no longer applies, or another requirement covers it.'),
                                          ('notreq', 'Not a requirement', 'A definition, a note or a rationale.'),
                                          ('ask', 'Ask the owner', 'You cannot tell. Nothing changes until they answer.')]):
        y = ya + 318 + k * 40
        radio(s, xb + 18, y + 8, kk == 'drop', None)
        s.t(xb + 44, y + 2, name, fs=10, color=INK)
        s.t(xb + 44, y + 18, help_, fs=8, color=SOFT)
    s.t(xb + 16, ya + 526, 'Reason', fs=9, color=SOFT)
    s.r(xb + 16, ya + 542, 428, 26, 'Another requirement in this project covers it (S-COV)', fill='#ffffff', stroke=LINE, fs=9, align='left', pad=8)
    s.t(xb + 16, ya + 578, 'Note (at least 12 characters)', fs=9, color=SOFT)
    s.r(xb + 16, ya + 594, 428, 40, 'Same mass limit as REQ-FCS-0564, which stays.', fill='#ffffff', stroke=LINE, fs=9, align='left', pad=8)
    s.t(xb + 16, ya + 646, 'Dropping a requirement needs the owners and the process engineer.', fs=9, color='#b35a00')
    s.btn(xb + 16, ya + 676, 160, 30, 'Record the decision', primary=True, fs=10)
    s.t(xb + 190, ya + 684, 'It counts as soon as it is recorded.', fs=9, color=SOFT)
    # C: what it moves
    xc = xb + 484
    wc = W - xc - 24
    s.caps(xc, ya, 'C · WHAT THIS MOVES')
    s.card(xc, ya + 24, wc, 300)
    s.t(xc + 16, ya + 36, 'Dropping it moves more than the list', fs=12, color=INK)
    items = [('Verification items', '1 item (TC-1…) must point at the requirement that takes its place, or the check proves nothing.', AMBER_BG),
             ('Child requirements', '2 requirements below it need a new parent. The one above it can be left with no child.', AMBER_BG),
             ('Baseline', 'It is in BL-1, so a change request number (CR-nnnnn) is needed before the decision can be recorded.', RED_BG)]
    for k, (t_, body, fill) in enumerate(items):
        y = ya + 66 + k * 82
        s.r(xc + 16, y, wc - 32, 74, fill=fill, stroke=fill, rounded=True)
        s.t(xc + 28, y + 8, t_, fs=10, color=INK)
        para(s, xc + 28, y + 26, body, wc - 56, fs=9, color=DARK)
    s.card(xc, ya + 340, wc, 444)
    s.t(xc + 16, ya + 352, 'Export to documents: the trace map', fs=12, color=INK)
    para(s, xc + 16, ya + 376, 'Two real downloads list every old and new ID, so the tools that hold the links can be brought into step.', wc - 32, fs=9, color=DARK)
    s.btn(xc + 16, ya + 416, 150, 28, 'trace-map.json', fs=10)
    s.btn(xc + 176, ya + 416, 150, 28, 'alias-map.csv', fs=10)
    rows = [['REQ-FCS-0443', 'dropped', 'REQ-FCS-0564'], ['REQ-FCS-0612', 'merged into', 'REQ-FCS-0610'], ['REQ-GND-0071', 'kept', 'REQ-GND-0071']]
    table(s, xc + 16, ya + 462, [130, 100, 130], ['OLD ID', 'WHAT HAPPENED', 'NEW ID'], rows, fs=9, bold_first=True, minh=24)
    para(s, xc + 16, ya + 592, 'Items, parent and child links, and baselines come with each row. Levels, items, links and baselines in this prototype are sample values and the file says so.', wc - 32, fs=9, color=SOFT)
    chk_list(s, xc + 16, ya + 668, wc - 32, [('Pass', 'Item rows equal the V’s “to carry over” number.'), ('Pass', 'Old IDs equal the requirements that leave the left leg.')], fs=9)
    for k, (x, y) in enumerate([(xa - 12, ya + 20), (xb - 12, ya + 20), (xb + 440, ya + 316), (xc - 12, ya + 20), (xc - 12, ya + 340)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['Most of the project is decided cluster by cluster. This panel is for a requirement that stands alone: nothing similar was found, or a person took it out of its cluster. Any other requirement can be put beside it first.',
            'Five outcomes: keep as written, keep with new wording, drop it, not a requirement, ask the owner. “Ask the owner” changes nothing in the counts. New wording gets the same checks a cluster’s wording gets: a lost number, an incompatible unit, a flipped “not” or a lost “shall” blocks it.',
            'Dropping a requirement, or calling it “not a requirement”, takes it out of the set, so it always needs the owners and the process engineer. A requirement in a baseline also needs a change request number. The person who decided cannot sign the decision off.',
            'A decision on a single requirement counts on Results, the V and the ledger exactly as a cluster decision does. The rules live in one file, so nothing counts it a second way.',
            'The trace map lists what hangs on a removed requirement: its verification items, the requirements below it, its baseline. The checks make the rows add up to the V’s numbers. This prototype is not connected to the tools that hold those links; it lists what to change in them.']


# ---------------------------------------------------------------- 12.3 AI use
def n3_ai_use(d, ox, oy):
    H = 1180
    s = new_frame(d, ox, oy, W, H, '12.3 · AI use: one switch, one data sheet, a gate in front of every prompt')
    cx, cy = shell2(s, W, H, 'AI use', 0, SIDE)
    head(s, cx, cy, 'AI use', 'Requirement text goes to an AI model only when every rule on this page says yes. Anything else stays with the mechanical methods and your reviewers. The wall that keeps text from leaving is the network rule at your gateway, which your IT staff set.')
    y0 = cy + 100
    colw = (W - cx - 24 - 24) / 2
    # switch
    s.card(cx, y0, 2 * colw + 24, 70)
    s.shape('ellipse', cx + 18, y0 + 22, 26, 26, fill=GREEN_BG, stroke=HUM)
    s.poly([(cx + 24, y0 + 36), (cx + 29, y0 + 41), (cx + 38, y0 + 30)], typ='line', stroke=HUM, sw=2)
    s.t(cx + 58, y0 + 12, 'AI is on', fs=14, color=INK)
    s.t(cx + 58, y0 + 38, '212 of 252 groups can go to the model. 40 are held back, and each one says why.', fs=10, color=DARK)
    s.btn(cx + 2 * colw + 24 - 270, y0 + 20, 250, 30, 'Switch AI off for the whole project', fs=10)
    # gate bars
    ya = y0 + 90
    s.card(cx, ya, colw, 290)
    s.t(cx + 16, ya + 12, 'What the gate does with the 252 groups', fs=13, color=INK)
    bars = [('Open to the AI', 212, '84%', HUM), ('Marked export controlled, above what the sheet approves', 7, '3%', '#b35a00'), ('Marked CUI, above what the sheet approves', 26, '10%', '#b35a00'),
            ('A marking this page does not recognise', 5, '2%', '#b35a00'), ('No marking recorded, and the sheet keeps those from the AI', 2, '1%', '#b35a00')]
    for k, (lab, n, pc, col) in enumerate(bars):
        y = ya + 46 + k * 38
        s.t(cx + 16, y, s.d.wrap(lab, 250, 9), fs=9, color=DARK)
        s.r(cx + 280, y + 3, 180, 10, fill=GREY, stroke=GREY, rounded=False)
        s.r(cx + 280, y + 3, max(3, 180 * n / 252), 10, fill=col, stroke=col, rounded=False)
        s.t(cx + 470, y, str(n) + ' · ' + pc, fs=9, color=INK, family=3)
    para(s, cx + 16, ya + 244, 'A group is as restricted as its most restricted requirement. Markings come from the source system: this page shows them and does not let anyone edit one.', colw - 32, fs=9, color=SOFT)
    # markings
    xb = cx + colw + 24
    s.card(xb, ya, colw, 290)
    s.t(xb + 16, ya + 12, 'The 1,248 requirements, by marking', fs=13, color=INK)
    for k, (lab, v) in enumerate([('No marking', '1,190 · 95%'), ('CUI', '37 · 3%'), ('Export controlled', '13 · 1%'), ('Classified', '0 · 0%'), ('Marking not recognised', '5 · <1%'), ('No marking recorded', '3 · <1%')]):
        y = ya + 46 + k * 28
        s.t(xb + 16, y, lab, fs=10, color=DARK)
        s.t(xb + colw - 110, y, v, fs=10, color=INK, family=3)
        s.line([(xb + 16, y + 20), (xb + colw - 16, y + 20)], stroke='#e9ecef', sw=1)
    para(s, xb + 16, ya + 224, 'Classified and unrecognised markings are never sent, whatever the sheet says. The sample’s markings are made up so that every kind of hold can be seen.', colw - 32, fs=9, color=SOFT)
    # sheet
    yb = ya + 310
    s.card(cx, yb, colw, 330)
    s.t(cx + 16, yb + 12, 'AI data sheet', fs=13, color=INK)
    s.btn(cx + colw - 290, yb + 8, 150, 26, 'Change the data sheet', fs=9)
    s.btn(cx + colw - 132, yb + 8, 116, 26, 'Withdraw approval', fs=9)
    para(s, cx + 16, yb + 44, 'What the people who approved the AI were told about the model. The reviewers decide what goes on it. The gate refuses to go beyond it.', colw - 32, fs=9, color=DARK)
    for k, (kk, v) in enumerate([('Model', 'Local model v1'), ('Where it runs', 'On our own servers'), ('Does requirement text leave your network?', 'No'), ('Prompts and answers', 'Kept on our servers, 90 days'),
                                 ('Highest marking approved', 'Requirements with no marking only'), ('A requirement with no marking recorded', 'Keep the group from the AI'), ('Reviewed by', 'A. Moreno, security office, 2 Oct')]):
        y = yb + 84 + k * 34
        s.t(cx + 16, y, kk, fs=9, color=SOFT)
        s.t(cx + 270, y, v, fs=9, color=INK)
        s.line([(cx + 16, y + 22), (cx + colw - 16, y + 22)], stroke='#e9ecef', sw=1)
    # rules
    s.card(xb, yb, colw, 330)
    s.t(xb + 16, yb + 12, 'The rules, in the order they are checked', fs=13, color=INK)
    rules = ['The switch is off: nothing goes to a model.', 'The data sheet has no reviewer’s name and date: nothing goes.',
             'The sheet contradicts itself (for example a vendor service with text that does not leave): nothing goes.',
             'Classified, unrecognised, or unstated markings (when the sheet says withhold) are held.',
             'A group marked above what the sheet approves is held. Export-controlled text can only be approved for a model on your own servers.',
             'Otherwise the group is open. The first rule that says no wins, and every no carries a code.']
    yy = yb + 44
    for k, r_ in enumerate(rules):
        s.shape('ellipse', xb + 16, yy, 18, 18, str(k + 1), fs=8, fill=GREY, stroke=SOFT, pad=0)
        yy = para(s, xb + 44, yy + 1, r_, colw - 64, fs=9, color=DARK) + 8
    # wall diagram
    yc = yb + 350
    s.t(cx, yc, 'What the gate is, and what it is not', fs=13, color=INK)
    bx = cx
    box(d, ox + bx, oy + yc + 30, 180, 70, 'The page\nand the pipeline', MECH_F, fs=11)
    box(d, ox + bx + 230, oy + yc + 30, 180, 70, 'The gate\nasks before every prompt', GUARD_F, fs=11)
    box(d, ox + bx + 520, oy + yc + 30, 180, 70, 'Your gateway\nonly the pipeline can reach', HUM_F, fs=11)
    box(d, ox + bx + 810, oy + yc + 30, 180, 70, 'The model host\nno route to the internet', AI_F, fs=11)
    for a, b in [(180, 230), (410, 520), (700, 810)]:
        s.poly([(bx + a, yc + 65), (bx + b, yc + 65)], stroke=INK, sw=2)
    s.line([(bx + 455, yc + 18), (bx + 455, yc + 116)], stroke=RED, sw=3, dash=True)
    s.t(bx + 380, yc + 120, 'THE WALL (NETWORK RULES)', fs=9, color=RED, family=3)
    para(s, bx + 1030, yc + 30, 'The gate stops the application from knocking on the door with the wrong text. A switch in a web page is not a security control; the wall is.', W - cx - 1030 - 24, fs=10, color=DARK)
    for k, (x, y) in enumerate([(cx + 2 * colw + 24 - 292, y0 + 14), (cx - 12, ya + 6), (cx - 12, yb + 6), (xb - 12, yb + 6), (bx + 440, yc + 8)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['One project-wide switch. Only the lead can change it, and not from a lens preview. Switching off holds every group, and it is a recorded event in the chain with a fingerprint of the sheet.',
            'Every group gets a code and a reason. A held group is still reviewed by people, from the mechanical results. The sample’s AI answers that already exist are hidden for held groups; in the pipeline the gate runs before the call, so no answer is ever made for them.',
            'The sheet records what the approvers were told: model, where it runs, whether text leaves, what is kept and for how long, the highest marking approved, what to do with an unmarked requirement, who reviewed it and when. A sheet that contradicts itself opens nothing.',
            'The rules are written twice, in the page and in the Python library the pipeline uses, and tested against one table of cases plus tens of thousands of generated inputs. That comparison found a real difference when first run, which was fixed.',
            'Not a wall. The wall is the network: no route from the model host to the internet, no logging at the model host that the sheet does not describe, a gateway only the pipeline can reach. That is for IT and security to build; no page can.']


# ---------------------------------------------------------------- 12.4 keeping the work
def n4_keeping(d, ox, oy):
    H = 860
    s = new_frame(d, ox, oy, W, H, '12.4 · Keeping the work: in this browser, in a file, and what is checked before a file replaces anything')
    s.t(40, 28, 'WHAT PEOPLE DECIDE, SIGN, WRITE AND LABEL IS KEPT BY ITSELF. NOTHING HERE IS SHARED BETWEEN PEOPLE, AND NOTHING IS ENCRYPTED.', fs=10, color=SOFT, family=3)
    s.h1(40, 56, 'Your work', fs=26)
    s.card(40, 110, 700, 170)
    s.t(60, 124, 'Your work', fs=14, color=INK)
    s.t(60, 150, 'Kept automatically at 23:50:11: 1 decision, 0 sign-offs, 1 hand-off, 0 labels.', fs=11, color=INK)
    para(s, 60, 176, 'It stays in this browser and is not encrypted, so a colleague on another computer does not see it. On a shared computer, start over when you finish. Sharing between people needs the server, which this prototype is not connected to.', 660, fs=9, color=SOFT)
    s.btn(60, 232, 120, 30, 'Save to a file', fs=10)
    s.btn(192, 232, 130, 30, 'Load from a file', fs=10)
    s.btn(334, 232, 100, 30, 'Start over', fs=10)
    # where it lives
    s.caps(40, 304, 'WHERE THE WORK LIVES')
    box(d, ox + 40, oy + 330, 200, 90, 'This page\nthe decisions you make', MECH_F, fs=11)
    box(d, ox + 330, oy + 330, 200, 90, 'This browser\nlocal storage, 350 ms after a change and when the tab closes', HUM_F, fs=10)
    box(d, ox + 620, oy + 330, 200, 90, 'A project file\nreqin-project-state/1', SRC_F, fs=11)
    s.poly([(240, 375), (330, 375)], stroke=INK, sw=2)
    s.poly([(530, 375), (620, 375)], stroke=INK, sw=2)
    s.poly([(720, 430), (720, 462), (430, 462), (430, 428)], stroke=INK, sw=2, dash=True)
    s.t(470, 468, 'Load from a file: checked first, then you confirm', fs=9, color=DARK)
    s.card(40, 520, 780, 300, dash=True)
    s.t(60, 534, 'The shared version is not on this page', fs=13, color=INK)
    para(s, 60, 560, 'The reference server (reqin/src/reqin/server) is the shared one: one copy, who may change what, no silent overwrites, and a record that verifies with SHA-256. It has its own tests. This page is not connected to it yet, so two people in two browsers each have their own copy.', 740, fs=10, color=DARK)
    box(d, ox + 60, oy + 640, 240, 80, 'The page\nper browser, per file', MECH_F, fs=11)
    box(d, ox + 520, oy + 640, 280, 80, 'Reference server\nshared, signed in, one record', HUM_F, fs=11, dash=True)
    s.poly([(300, 680), (520, 680)], stroke=RED, sw=2, dash=True)
    s.t(330, 656, 'NOT CONNECTED', fs=9, color=RED, family=3)
    para(s, 60, 740, 'Not encrypted. Not tamper-proof: the page’s fingerprints are a short demonstration hash that finds accidents and hand edits. Not a backup: clearing the browser’s site data removes the browser copy. Save a file.', 740, fs=9, color=SOFT)
    # what is checked
    s.card(860, 110, 600, 320)
    s.t(880, 124, 'Checked before a file replaces anything', fs=14, color=INK)
    chk_list(s, 880, 156, 560, [('Pass', '1 · Format: reqin-project-state/1 with a saved state in it.'),
                                ('Pass', '2 · Project: it names the project it came from, with a fingerprint of the requirement and cluster IDs. Another project’s file is refused.'),
                                ('Pass', '3 · Kind of every item: lists are lists, switches are on or off, the person is in this project, at most 20,000 events.'),
                                ('Pass', '4 · The record of events is a chain. A changed, removed or reordered entry is found and the first bad one is named.'),
                                ('Pass', '5 · The AI switch and data sheet agree with their own record.'),
                                ('Pass', '6 · Every screen can draw it, in memory, before anything is replaced.')], fs=10, gap=10)
    para(s, 880, 350, 'A file that fails any of these is refused, the reason is shown, and the work in the browser is left as it was. Entries for things the project does not have, or in the wrong shape, are left out and counted in the summary.', 560, fs=10, color=DARK)
    s.card(860, 450, 600, 170)
    s.caps(880, 464, 'TWO TABS, A BLOCKED BROWSER, A FULL BROWSER')
    para(s, 880, 490, 'Two tabs of one browser cannot write over each other: the tab that notices the other one saved stops saving and asks whose work stands. A blocked or full browser says so in words and says to save a file. The page keeps working.', 560, fs=11, color=DARK)
    s.card(860, 640, 600, 180)
    s.caps(880, 654, 'NOT KEPT')
    para(s, 880, 678, 'Which screen is open, filters, search text, half-typed boxes and whether a panel is open. Everything else a person decided, signed, wrote or labelled is kept, with the record of events and the AI switch and data sheet.', 560, fs=11, color=DARK)
    para(s, 880, 752, 'A browser copy larger than 4 MB is removed unread. After a file is accepted and you confirm, loading adds one entry to the record, so the chain still holds.', 560, fs=9, color=SOFT)
    for k, (x, y) in enumerate([(28, 118), (28, 336), (28, 526), (848, 118), (848, 648)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['The card sits on Home. Nothing to press: decide something and it is kept a moment later. The card says when, and how many decisions, sign-offs, hand-offs and labels that is.',
            'Three places: the page, the browser’s own storage, and a file you can download and read back later. The file is plain JSON with the project it belongs to, a count of what is in it and the record of events.',
            'Sharing between people is the reference server’s job, not this page’s. Until the page is connected to it, each browser and each file is its own copy. Say so to anyone who asks.',
            'Six checks stand between a file and your work. A file that fails one changes nothing. These were shown to fail on purpose: a wrong format, another project, an edited record, a changed sheet, a file the screens cannot draw.',
            'What is not kept is deliberate: view state. What is not promised is honest: encryption, tamper-proofing, backup. On a shared computer, start over when you finish.']


# ---------------------------------------------------------------- 12.5 how it was checked
def n5_checked(d, ox, oy):
    H = 600
    s = new_frame(d, ox, oy, W, H, '12.5 · How it was checked, and what was not')
    s.t(40, 28, 'THE PROTOTYPE RUNS ON A SYNTHETIC SAMPLE. NO REAL PROGRAM HAS BEEN USED. EVERY CLAIM BELOW IS ONE A TEST ENFORCES, OR IS LISTED AS NOT CHECKED.', fs=10, color=SOFT, family=3)
    s.h1(40, 56, 'Checked, and not checked', fs=26)
    cols = [('AT SCALE', 40, [('Pass', '20 times the sample: 24,960 requirements and 5,040 clusters, every page drawn and timed.'),
                              ('Pass', 'Slowest first drawing (All requirements) 0.7 s against a 4 s limit. Counting every pair for the gold set 1.5 s against 19 s; the first version took 204 s.'),
                              ('Pass', 'The faster counting gives the same numbers as comparing every pair, on several hundred random and edge-case sets.'),
                              ('Open', 'The larger project is the sample repeated, so many wordings are identical. A real corpus has another shape.')]),
            ('ACCESSIBILITY', 530, [('Pass', 'axe-core on every page and on the states that open more of a page, at 1440, 900 and 390 px: WCAG 2.2 AA and best practice.'),
                                    ('Pass', 'Own checks: contrast as drawn, keyboard from the first Tab stop (a skip link), a visible focus ring, landmarks, reflow at 320 px, reduced motion.'),
                                    ('Pass', 'The two charts that use colour to tell marks apart are checked for red-green colour blindness.'),
                                    ('Open', 'Nobody has used it with a screen reader, a switch or voice control. No person with a disability has tried it. Chromium only.')]),
            ('THE CHECKS THEMSELVES', 1020, [('Pass', '30 browser runs in CI, about 17 minutes, plus the static checks and the Python tests.'),
                                             ('Pass', 'Deliberate breaks: 263 of 267 changes to the code were noticed. The 4 that were not change nothing a person can see, and each reason is written down.'),
                                             ('Pass', 'The page’s and the library’s AI gate rules agree on tens of thousands of generated inputs.'),
                                             ('Open', 'The CI files have not yet run on both services in their final form.')])]
    for title, x, items in cols:
        s.card(x, 110, 460, 280)
        s.caps(x + 20, 126, title)
        chk_list(s, x + 20, 154, 420, items, fs=10, gap=12)
    s.card(40, 410, 1420, 160, dash=True)
    s.caps(60, 424, 'NOT CHECKED')
    para(s, 60, 448, 'Any real program’s requirements, markings or rules. Whether people labelling real requirements agree with each other, and whether 160 pairs is enough for your project. The network wall, which is not in the application. Whether the page is easy to use for someone who has never seen it. The page is not connected to the reference server.', 1380, fs=11, color=DARK)
    para(s, 60, 510, 'The next real test is yours: import one real project, remove the sample labels, have two people label an hour each, and read agreement before reading any score.', 1380, fs=11, color=INK)
    for k, (x, y) in enumerate([(28, 118), (518, 118), (1008, 118), (28, 418)]):
        s.num(x, y, k + 1)
    d.frame_end()
    return ['Each “Pass” is something a test fails on. Each “Open” is something nobody has checked or that cannot be checked from here. Both kinds are shown, on purpose.',
            'Automated accessibility checks find a part of the problems. They do not replace a person using the page with assistive technology.',
            'The deliberate-break scripts live in tools/mutation. A fast check in CI makes sure every break still matches the code, so the scripts cannot quietly stop testing anything.',
            'What was not checked is a plan, not a footnote.']
