"""Board 06: the four lens views of the same cluster (CL-042, three wordings, one AI draft)."""
from wf2 import *

A_T = 'The Flight Control Subsystem shall transmit a health status message every 1 second.'
B_T = 'The FCS shall send a heartbeat to the Mission Computer at 1 Hz.'
C_T = 'The Flight Control Subsystem shall transmit a heartbeat message every second.'
R2_T = 'The Flight Control Subsystem shall transmit a heartbeat message to the Mission Computer every 1 second.'
QUESTION = ['Is the technical content right, and is anything lost?',
            'Can this change be processed, traced and defended under our process?',
            'Will the people who read this wording understand it, and is it consistent?',
            'Can someone new understand this without insider help?']
MEANING = ['The technical meaning is preserved, nothing is lost, and any conflict was raised as a conflict.',
           'This change can be processed under our change and trace process, and the record of how it was decided is complete.',
           'The wording matches the project\'s terms and reads clearly to the people who use it.',
           'A newcomer can read this, say what it means, and tell what would show it is met.']


def top(s, cx, cy, lens, W):
    s.t(cx, cy, 'CL-042 · Health message timing', fs=20, family=2, color=INK)
    s.chip(cx, cy + 32, 60, 16, 'Lane A', fill=GREEN_BG, fs=9)
    s.chip(cx + 66, cy + 32, 70, 16, 'Equivalent', fill=BLUE_BG, fs=9)
    s.chip(cx + 142, cy + 32, 62, 16, 'In review', fill='#ffffff', fs=9)
    s.chip(cx + 210, cy + 32, 170, 16, 'New wording proposed: all four sign', fill=AMBER_BG, fs=8)
    s.t(cx + 600, cy + 8, 'Sign-offs', fs=9, color=SOFT)
    sts = ['signed', 'signed', 'pending', 'pending']
    sts = {0: ['pending', 'pending', 'pending', 'pending'], 1: ['signed', 'pending', 'pending', 'pending'], 2: ['signed', 'signed', 'pending', 'pending'], 3: ['signed', 'signed', 'pending', 'pending']}[lens]
    sign_dots(s, cx + 660, cy + 6, sts)
    s.t(cx + 735, cy + 8, 'on revision R2', fs=8, color=SOFT)
    y = cy + 58
    s.r(cx, y, 816, 44, fill=LCOL[lens], stroke=INK, sw=2)
    s.t(cx + 12, y + 7, 'YOU ARE REVIEWING AS', fs=8, color=DARK, family=3)
    s.t(cx + 12, y + 20, LENS[lens], fs=14, color=INK, family=1)
    s.t(cx + 210, y + 16, 'Your question:  ' + QUESTION[lens], fs=11, color=INK)
    return y + 56


def members(s, x, y, w, hl=None):
    s.card(x, y, w, 176)
    s.caps(x + 14, y + 10, 'THREE WORDINGS, ONE PROPOSAL (SAME FOR EVERY LENS)')
    bw = (w - 28 - 20) / 3
    for i, (rid, t_) in enumerate([('A  REQ-FCS-0212', A_T), ('B  REQ-FCS-0218', B_T), ('C  REQ-FCS-0224', C_T)]):
        bx = x + 14 + i * (bw + 10)
        s.r(bx, y + 28, bw, 70, fill='#ffffff', stroke=LINE)
        s.t(bx + 8, y + 33, rid, fs=8, family=3, color=SOFT)
        tokw(s, bx + 8, y + 48, bw - 14, t_, fs=9)
    s.r(x + 14, y + 110, w - 28, 54, fill='#f8f0fc', stroke=AIC)
    s.prov(x + 22, y + 118, 'ai')
    s.caps(x + 40, y + 118, 'AI DRAFT R2 · PROPOSED WORDING · NOT APPROVED', color=AIC)
    tokw(s, x + 22, y + 136, w - 50, R2_T, fs=10)
    s.t(x + w - 190, y + 118, 'SE-2 proposes: merge into one wording', fs=8, color=SOFT)
    return y + 188


def panel(s, x, y, w, h, lens, title):
    s.card(x, y, w, h)
    s.r(x, y, w, 26, fill=LCOL[lens], stroke=LCOL[lens], rounded=False)
    s.t(x + 12, y + 8, title, fs=9, color=INK, family=3)
    s.t(x + w - 250, y + 8, 'LENS PANEL: THIS PART CHANGES BY LENS', fs=8, color=DARK, family=3)
    s.r(x, y, w, h, fill=None, stroke=RED, sw=2, dash=True)


def signoff(s, x, y, w, lens, note, extra, others):
    s.card(x, y, w, 158)
    s.caps(x + 14, y + 10, 'YOUR NOTE · REQUIRED IF YOU REQUEST CHANGES')
    s.r(x + 14, y + 28, 440, 52, fill='#ffffff', stroke=LINE)
    s.t(x + 22, y + 34, s.d.wrap(note, 424, 9), fs=9, color=SOFT)
    s.t(x + 14, y + 88, s.d.wrap('Notes and reason codes are kept with this revision. They show in the history and the export.', 440, 8), fs=8, color=SOFT)
    s.btn(x + 480, y + 28, 190, 34, 'Sign as ' + LENS[lens], primary=True, fs=10)
    s.btn(x + 480, y + 68, 190, 30, 'Request changes', fs=10)
    s.btn(x + 680, y + 28, 122, 34, extra, fs=9)
    s.btn(x + 680, y + 68, 122, 30, 'Not my area', fs=9)
    s.r(x + 14, y + 112, w - 28, 36, fill=LCOL[lens], stroke=LCOL[lens])
    s.t(x + 24, y + 118, 'What your sign-off means', fs=8, color=SOFT, family=3)
    s.t(x + 24, y + 130, s.d.wrap(MEANING[lens], w - 60, 9), fs=9, color=INK)


def report_link(s, x, y):
    s.t(x, y, 'Problem with this screen? Report a usability issue ▸', fs=8, color=ACC)


# ------------------------------------------------------------------ L0 overview
def l0_overview(d, ox, oy):
    W, H = 1560, 720
    s = new_frame(d, ox, oy, W, H, 'L0 · One workspace, four lens panels: what changes by lens', bg='#ffffff')
    s.t(20, 14, 'Same workspace for everyone. Only the lens panel, the tools and the sign-off change.', fs=24, family=1, color=INK)
    s.t(20, 50, 'This answers "do different reviewers need different screens?". Mostly no: they need the same evidence, with a different question on top of it.', fs=12, color=SOFT)
    s.caps(20, 84, 'THE CLUSTER WORKSPACE (SCHEMATIC)')
    blocks = [('1  Header', 'Cluster, lane, relationship, status, who has signed', 'same', 34),
              ('2  Members and diff', 'Every wording side by side, differences marked', 'same', 34),
              ('3  Mechanical scores and ten guards', 'Raw values, no hidden thresholds', 'same', 34),
              ('4  AI proposal and record', 'Vote agreement, quotes, model and prompt. Hidden until your own call when blind-first is on', 'blind-first differs', 46),
              ('5  LENS PANEL', 'Evidence for your question · checklist · lens tools', 'CHANGES', 62),
              ('6  Resolve panel (sticky)', 'Pick a strategy, write the reason. Used by the assigned decider; others see it read only (board 07)', 'permission differs', 46),
              ('7  Notes, history and assistant', 'Reviewer notes, AI notes, revision chain, chat (boards 07 and 08)', 'same', 34),
              ('8  Your sign-off', 'Sign for your lens, or request changes', 'CHANGES', 34)]
    yy = 104
    for t_, sub, tag, h in blocks:
        hot = tag == 'CHANGES'
        s.r(20, yy, 480, h, fill='#fff5f5' if hot else '#F8F9FA', stroke=RED if hot else LINE, sw=2 if hot else 1, dash=hot)
        s.t(32, yy + 6, t_, fs=11, color=INK)
        s.t(32, yy + 22, s.d.wrap(sub, 330, 9), fs=9, color=SOFT)
        s.chip(360, yy + 6, 130, 16, tag, fill=RED_BG if hot else (AMBER_BG if 'differs' in tag else GREY), fs=8)
        yy += h + 8
    yy += 6
    s.r(20, yy, 480, 130, fill='#fff9db', stroke='#f1c40f')
    s.t(34, yy + 10, 'What never changes by lens', fs=12, family=1, color=INK)
    for i, t_ in enumerate(['The data, the mechanical scores and the ten guards', 'What the AI said and recorded', 'The audit trail: every action is logged with your lens', 'The rule that guards block a merge, for everyone']):
        s.t(34, yy + 36 + i * 22, '•  ' + t_, fs=10, color='#5c4400')
    s.t(34, yy + 124 - 0, '', fs=8)
    s.num(486, 92, 1)
    s.num(486, 270, 2)
    s.num(486, yy - 6, 3)
    # matrix
    s.caps(520, 84, 'WHAT CHANGES BY LENS')
    rows = [['Question it answers', QUESTION[0], QUESTION[1], QUESTION[2], QUESTION[3]],
            ['In "Needs my lens" by default', 'Every cluster with a decision to make, for your allocations', 'Lane B and C, baselined, cross-owner, plus a 20% sample of lane A', 'Clusters with new or edited wording', 'Clusters with new or edited wording, plus a 20% sample of lane B with no new wording'],
            ['Evidence first', 'Parameters, trace links, verification method, allocation', 'Baseline, owners, change requests, impacted documents, rule check, AI record', 'Term use across the project, glossary, readability, who reads it', 'Only the wording. Then terms and acronyms it uses. No source, owner or AI answer yet'],
            ['Lens tools', 'Parameter ledger, trace graph, compare any two', 'Impact list, owner notification, alias map, change-request link', 'Term finder, glossary, readability check, suggest wording', 'Explain it back, "where I got stuck", glossary lookups'],
            ['Can add to the draft', 'A resolution and any wording edit', 'Process actions (notify, attach change request, mark suspect)', 'Suggested terms and wording (as suggestions)', 'Comprehension flags and a plain-language rewrite (as suggestions)'],
            ['Blind-first default', 'Off. On for sampled audit items', 'Off', 'Off', 'On. AI proposal opens after your own reading'],
            ['Sign-off means', MEANING[0], MEANING[1], MEANING[2], MEANING[3]]]
    y = table(s, 520, 104, [120, 215, 215, 215, 215], ['', 'Systems engineer', 'Process engineer', 'UI/UX engineer', 'New user'], rows, fs=9, bold_first=True, minh=30)
    s.num(520 + 962, 94, 4)
    para(s, 520, y + 12, 'Who decides and who signs. The assigned reviewer (usually the SE) makes the group decision in the Resolve panel. The other three lenses do not re-decide. They check the draft from their own angle and sign, or request changes with a reason. This keeps one owner for each decision and four independent checks.', 980, 11, DARK)
    s.t(520, y + 80, 'Which lens do I get?', fs=12, family=1, color=INK)
    para(s, 520, y + 102, 'From your login (for example the group claim from GitLab OIDC). A person can hold more than one lens, but cannot sign two lenses on the same revision. Leads can "preview as" another lens, read only, to see what that reviewer sees.', 980, 11, DARK)
    s.t(520, y + 160, 'What each person starts on', fs=12, family=1, color=INK)
    for i, (nm, txt) in enumerate([('SE', 'Their allocation, safest first, with the Resolve panel ready.'), ('PE', 'Lane B and C and baselined items first, then the lane A sample.'), ('UX', 'A packet of clusters that changed wording, grouped by term.'), ('NU', 'A packet of fresh wordings, one at a time, with explain-it-back.')]):
        avatar(s, 520 + i * 255, y + 186, nm, LCOL[i], 24)
        s.t(520 + i * 255 + 30, y + 184, s.d.wrap(txt, 190, 9), fs=9, color=DARK)
    d.frame_end()
    return ['Same layout for every reviewer, so training, screenshots, help and the audit all work the same. Only block 5 and block 8 change.',
            'Blind-first applies to the AI panel. For the New user it is on by default, because a fresh, unanchored read is the point of that lens.',
            'Nothing about the evidence is hidden by lens. A lens changes what is shown first and what you are asked, not what is true.',
            'The matrix is also the training sheet for new reviewers. It is generated from the project policy, so it never drifts from what the tool enforces.']


# ------------------------------------------------------------------ L1 SE
def l1_se(d, ox, oy):
    W, H = 1000, 985
    s = new_frame(d, ox, oy, W, H, 'L1 · Systems engineer lens: CL-042')
    cx, cy = shell2(s, W, H, 'Review queue', 0)
    y = top(s, cx, cy, 0, W)
    y = members(s, cx, y, 816)
    panel(s, cx, y, 816, 390, 0, 'PARAMETERS, TRACES, VERIFICATION')
    A_, N_ = AMBER_BG, None
    rows = [['Receiver', ('not stated', A_), 'Mission Computer', ('not stated', A_), 'Mission Computer'],
            ['Interval', '1 s', ('1 Hz = 1 s', A_), ('"every second"', A_), '1 s'],
            ['Parent trace', 'SYS-0310', 'SYS-0310', 'SYS-0310', 'SYS-0310'],
            ['Verification', 'Test', 'Test', 'Test', 'Test'],
            ['Allocation', 'Flight Control', 'Flight Control', 'Flight Control', 'Flight Control']]
    ty = table(s, cx + 12, y + 36, [86, 78, 88, 78, 90], ['', 'A  0212', 'B  0218', 'C  0224', 'R2 draft'], rows, fs=9, minh=26, bold_first=True)
    s.t(cx + 12, ty + 4, 'Amber = a difference the SE must explain, not a defect.', fs=8, color=SOFT)
    # trace graph
    gy = ty + 26
    s.caps(cx + 12, gy, 'TRACE LINKS THAT MUST SURVIVE')
    s.r(cx + 12, gy + 54, 80, 26, 'SYS-0310', fill=BLUE_BG, stroke=INK, fs=9)
    for i, nm in enumerate(['A  0212', 'B  0218', 'C  0224']):
        yy = gy + 18 + i * 34
        s.r(cx + 140, yy, 86, 24, nm, fill='#ffffff', stroke=INK, fs=9)
        s.poly([(cx + 92, gy + 67), (cx + 140, yy + 12)], typ='arrow', stroke=SOFT, sw=1.2)
    for j, nm in enumerate(['VP-118', 'VP-131']):
        yy = gy + 24 + j * 52
        s.r(cx + 300, yy, 70, 24, nm, fill=AMBER_BG, stroke='#b35a00', fs=9)
    s.poly([(cx + 226, gy + 30), (cx + 300, gy + 36)], typ='arrow', stroke=SOFT, sw=1.2)
    s.poly([(cx + 226, gy + 64), (cx + 300, gy + 76)], typ='arrow', stroke=SOFT, sw=1.2)
    s.t(cx + 380, gy + 30, s.d.wrap('Both verification items re-link to the survivor and are marked suspect.', 70, 8), fs=8, color=DARK)
    # checklist right
    s.caps(cx + 480, y + 36, 'SE CHECKLIST')
    ck = chk_list(s, cx + 480, y + 56, 320, [('Pass', 'Number and unit survive: 1 Hz and "every second" both mean one per second.'),
                                              ('Needs you', 'Only B names the Mission Computer. Confirm A and C meant the same link.'),
                                              ('Pass', 'Parent trace and verification method are the same on all three.'),
                                              ('Pass', 'Allocation and owner are identical (Flight Control, FCS team).'),
                                              ('Needs you', 'VP-118 links to A only. Keep the strictest verification link.')])
    s.caps(cx + 480, ck + 4, 'TOOLS FOR THIS LENS')
    for i, t_ in enumerate(['Parameter ledger', 'Trace graph', 'Compare any two']):
        s.chip(cx + 480 + i * 106, ck + 24, 100, 18, t_, fs=8)
    s.r(cx + 480, ck + 54, 322, 40, fill='#F1F6FF', stroke=ACC)
    s.t(cx + 490, ck + 60, s.d.wrap('The SE also makes the group decision. The Resolve panel sits beside this panel (board 07).', 300, 9), fs=9, color=INK)
    s.num(cx + 456, y + 34, 3)
    yy = y + 402
    signoff(s, cx, yy, 816, 0, 'Why the Mission Computer link is or is not the same for A and C…', 'Resolve ▸', None)
    s.num(cx + 800, yy - 8, 5)
    report_link(s, cx, yy + 164)
    s.num(cx + 800, cy + 52, 1)
    s.num(cx + 800, cy + 108, 2)
    s.num(cx + 790, y + 34, 4)
    d.frame_end()
    return ['The banner names the lens and the one question it answers. The lens comes from the login, and the sidebar shows which lenses you do not hold.',
            'The members and the AI draft are identical in every lens view, so all four judge the same text.',
            'Evidence for this lens: parameters side by side, trace links and verification. Amber cells are differences to explain, not errors.',
            'Checklist in three states: Pass, Needs you, Blocked. Each line names its evidence. The panel has a red dashed outline in this board only, to show what swaps.',
            'Sign-off. The note is required if you request changes. "What your sign-off means" is the contract, in plain words.']


# ------------------------------------------------------------------ L2 PE
def l2_pe(d, ox, oy):
    W, H = 1000, 985
    s = new_frame(d, ox, oy, W, H, 'L2 · Process engineer lens: CL-042')
    cx, cy = shell2(s, W, H, 'Review queue', 1)
    y = top(s, cx, cy, 1, W)
    y = members(s, cx, y, 816)
    panel(s, cx, y, 816, 390, 1, 'PROCESS IMPACT OF THIS CHANGE')
    rows = [['Baseline', 'None (pre-baseline). No change request needed.'],
            ['Owner approval', 'FCS team only. Same owner, so no cross-owner step.'],
            ['IDs retired', 'REQ-FCS-0218 and REQ-FCS-0224 become aliases of REQ-FCS-0212. The old IDs keep resolving.'],
            ['Verification items', 'VP-118 and VP-131 re-link to the survivor. Marked suspect until re-confirmed.'],
            ['Documents citing these IDs', 'SRS 3.2.4 and Test plan 5.1 regenerate on the next export.'],
            ['Rule check (EARS, INCOSE)', 'R2: no warnings. C had one: "second" with no number.']]
    ty = table(s, cx + 12, y + 36, [120, 320], ['Item', 'What happens'], rows, fs=9, minh=30, bold_first=True)
    s.caps(cx + 480, y + 36, 'PE CHECKLIST')
    ck = chk_list(s, cx + 480, y + 56, 320, [('Pass', 'No baseline involved, so no change request is needed.'),
                                              ('Pass', 'Same owner on all three. No cross-owner approval needed.'),
                                              ('Needs you', 'Two verification items will be re-linked and marked suspect. Confirm the re-test plan.'),
                                              ('Needs you', 'Two aliases are created. Confirm retired IDs stay resolvable in exports.'),
                                              ('Pass', 'AI record complete: model, prompt version, 3 runs, inputs, reviewer.')])
    s.caps(cx + 480, ck + 4, 'TOOLS FOR THIS LENS')
    for i, t_ in enumerate(['Impact list', 'Alias map', 'Notify owners']):
        s.chip(cx + 480 + i * 106, ck + 24, 100, 18, t_, fs=8)
    s.chip(cx + 480, ck + 48, 150, 18, 'Attach change request ▸', fs=8, dash=True)
    s.t(cx + 640, ck + 51, 'Off here: pre-baseline', fs=8, color=SOFT)
    s.t(cx + 12, ty + 12, 'AI record for this suggestion', fs=9, color=SOFT)
    s.r(cx + 12, ty + 30, 440, 66, fill='#f8f0fc', stroke=AIC)
    s.prov(cx + 20, ty + 38, 'ai')
    s.t(cx + 40, ty + 37, 'Model, prompt version, 3 of 3 runs agree, inputs, and the reviewer who accepted', fs=9, color=DARK)
    s.t(cx + 20, ty + 58, 'Stored once as an immutable record, linked from this revision (board 07).', fs=9, color=SOFT)
    s.t(cx + 20, ty + 76, 'Open the AI record ▸', fs=9, color=ACC)
    s.num(cx + 456, y + 34, 3)
    yy = y + 402
    signoff(s, cx, yy, 816, 1, 'Re-test plan for VP-118 and VP-131: …', 'Notify owners', None)
    s.num(cx + 800, yy - 8, 5)
    report_link(s, cx, yy + 164)
    s.num(cx + 800, cy + 52, 1)
    s.num(cx + 800, cy + 108, 2)
    s.num(cx + 790, y + 34, 4)
    d.frame_end()
    return ['Same top and same members. The banner changes the question to "Can this be processed and defended under our process?"',
            'Same text, same AI draft. The PE does not re-decide the merge, they check the process around it.',
            'Evidence for this lens: baseline, owners, retired IDs, verification items, documents that cite these IDs, and the rule check.',
            'Checklist items are about consequences: suspect links, aliases, exports. "Attach change request" is off here because the project is pre-baseline.',
            'PE sign-off is binding on Lane B, C and baselined items. On Lane A without new wording it is a 20% sample (board S5).']


# ------------------------------------------------------------------ L3 UX
def l3_ux(d, ox, oy):
    W, H = 1000, 985
    s = new_frame(d, ox, oy, W, H, 'L3 · UI/UX engineer lens: CL-042')
    cx, cy = shell2(s, W, H, 'Review queue', 2)
    y = top(s, cx, cy, 2, W)
    y = members(s, cx, y, 816)
    panel(s, cx, y, 816, 390, 2, 'WORDING, TERMS AND READABILITY')
    s.caps(cx + 12, y + 38, 'HOW THE PROJECT NAMES THIS THING (REQUIREMENTS USING EACH TERM)')
    for i, (nm, n, f) in enumerate([('heartbeat message', 12, '#2A78D6'), ('health status message', 3, '#f08c00'), ('heartbeat (alone)', 2, '#f08c00')]):
        yy = y + 62 + i * 26
        s.t(cx + 12, yy, nm, fs=9, color=DARK)
        s.r(cx + 160, yy, 24 * n, 12, fill=f, stroke=f, rounded=False)
        s.t(cx + 166 + 24 * n, yy - 1, str(n), fs=9, color=INK, family=3)
    s.r(cx + 12, y + 148, 440, 54, fill='#F8F9FA', stroke=LINE)
    s.t(cx + 22, y + 154, 'Glossary GL-021', fs=8, color=SOFT, family=3)
    s.t(cx + 22, y + 168, s.d.wrap('heartbeat message: a periodic signal that shows a subsystem is alive. Preferred term.', 420, 9), fs=9, color=INK)
    s.caps(cx + 12, y + 216, 'READING CHECK')
    for i, (k, v) in enumerate([('Length', 'A 14 words · B 12 · C 11 · R2 15'), ('Reading level', 'R2 is about grade 9, one idea per sentence'), ('Number style', '"every N seconds" in 41 requirements'), ('Who reads it', 'FCS engineers, Mission Computer team, testers')]):
        kv(s, cx + 12, y + 238 + i * 22, k, v, kw=100, fs=9)
    s.caps(cx + 480, y + 36, 'UX CHECKLIST')
    ck = chk_list(s, cx + 480, y + 56, 320, [('Pass', 'One subject, one action, one value. Number and unit sit together.'),
                                              ('Needs you', 'Term choice: "heartbeat message" is used 12 times, "health status message" 3 times. Confirm one term and queue the 3 for update.'),
                                              ('Pass', 'Full name used in R2, not "FCS". Matches the glossary.'),
                                              ('Pass', 'Reading level suits engineers and testers.'),
                                              ('Needs you', '"every second" (C) and "every 1 second" (R2) mean the same. Confirm the project style.')])
    s.caps(cx + 480, ck + 4, 'TOOLS FOR THIS LENS')
    for i, t_ in enumerate(['Term finder', 'Glossary', 'Readability']):
        s.chip(cx + 480 + i * 106, ck + 24, 100, 18, t_, fs=8)
    s.chip(cx + 480, ck + 48, 150, 18, 'Suggest wording ▸', fs=8)
    s.t(cx + 640, ck + 51, 'Goes in as a suggestion', fs=8, color=SOFT)
    s.num(cx + 456, y + 34, 3)
    yy = y + 402
    signoff(s, cx, yy, 816, 2, 'Preferred term and why: …', 'Suggest wording', None)
    s.num(cx + 800, yy - 8, 5)
    report_link(s, cx, yy + 164)
    s.num(cx + 800, cy + 52, 1)
    s.num(cx + 800, cy + 108, 2)
    s.num(cx + 790, y + 34, 4)
    d.frame_end()
    return ['The UX engineer sees this cluster only because wording is new. On a Lane A cluster with no new wording it would not be in their queue.',
            'Same members and draft. The UX view adds term use across the whole project, so one cluster is judged against the project\'s language.',
            'Evidence for this lens: which term the project uses most, the glossary entry, a readability check, and who reads the requirement.',
            'A suggestion from this lens goes onto the draft as a proposed edit, with the SE as owner of the resolution. It never overwrites.',
            '"Report a usability issue" lets this lens feed the app\'s own UI review, so the UI/UX lens covers both the wording and the tool.']


# ------------------------------------------------------------------ L4 NU
def l4_nu(d, ox, oy):
    W, H = 1000, 970
    s = new_frame(d, ox, oy, W, H, 'L4 · New user lens: CL-042')
    cx, cy = shell2(s, W, H, 'Review queue', 3)
    y = top(s, cx, cy, 3, W)
    s.card(cx, y, 500, 560)
    s.r(cx, y, 500, 26, fill=LCOL[3], stroke=LCOL[3], rounded=False)
    s.t(cx + 12, y + 8, 'READ IT COLD', fs=9, color=INK, family=3)
    s.r(cx, y, 500, 560, fill=None, stroke=RED, sw=2, dash=True)
    s.caps(cx + 14, y + 38, 'STEP 1 · READ THE PROPOSED REQUIREMENT')
    s.r(cx + 14, y + 56, 472, 74, fill='#ffffff', stroke=INK, sw=2)
    s.t(cx + 26, y + 70, s.d.wrap(R2_T, 440, 14), fs=14, color=INK)
    s.t(cx + 14, y + 138, 'You see only the words. Not the source model, the owner, the other wordings or the AI answer.', fs=9, color=SOFT)
    s.caps(cx + 14, y + 166, 'STEP 2 · SAY WHAT IT MEANS, IN YOUR OWN WORDS')
    s.r(cx + 14, y + 184, 472, 78, fill='#ffffff', stroke=LINE)
    s.t(cx + 24, y + 192, s.d.wrap('The flight control part sends a regular "I am alive" message to the mission computer, once every second.', 450, 11), fs=11, color=INK)
    s.caps(cx + 14, y + 282, 'STEP 3 · WHERE DID YOU GET STUCK?')
    for i, (c, t_) in enumerate([(True, 'I had to look up "heartbeat message"'), (False, 'A word or acronym was not defined'), (False, 'Two readings are possible'), (False, 'Something was missing (who, what, when)'), (False, 'It was too long')]):
        checkbox(s, cx + 14, y + 304 + i * 26, c, t_, fs=10)
    s.btn(cx + 14, y + 450, 190, 38, 'Submit my reading', primary=True, fs=11)
    s.t(cx + 214, y + 460, 'Then the answer key opens.', fs=9, color=SOFT)
    s.t(cx + 14, y + 506, s.d.wrap('Your reading is stored with your name and this revision. It is a comprehension check of the wording, never a grade of you.', 470, 9), fs=9, color=SOFT)
    s.num(cx + 484, y - 8, 3)
    # right
    rx = cx + 516
    s.card(rx, y, 300, 218)
    s.caps(rx + 14, y + 10, 'WORDS IN THIS REQUIREMENT')
    for i, (w_, st, f) in enumerate([('Flight Control Subsystem', 'defined', GREEN_BG), ('heartbeat message', 'you looked it up', AMBER_BG), ('Mission Computer', 'defined', GREEN_BG), ('every 1 second', 'plain', GREY)]):
        s.t(rx + 14, y + 38 + i * 30, w_, fs=10, color=INK)
        s.chip(rx + 170, y + 36 + i * 30, 116, 16, st, fill=f, fs=8)
    s.t(rx + 14, y + 164, s.d.wrap('Terms that needed lookup are sent to the UX lens as "needs a gloss in the document".', 270, 9), fs=9, color=SOFT)
    s.card(rx, y + 232, 300, 150, fill='#F8F9FA', dash=True)
    s.shape('ellipse', rx + 14, y + 246, 16, 16, 'x', fs=8, fill=GREY, stroke=SOFT, pad=0)
    s.caps(rx + 38, y + 248, 'AI PROPOSAL AND AUTHOR\'S INTENT')
    s.t(rx + 14, y + 276, s.d.wrap('Locked. Blind-first is on for this lens, so your first reading is not influenced. It opens when you submit.', 272, 10), fs=10, color=SOFT)
    s.t(rx + 14, y + 330, 'After you submit', fs=9, color=INK)
    s.chip(rx + 14, y + 350, 70, 16, 'Match', fill=GREEN_BG, fs=8)
    s.chip(rx + 90, y + 350, 70, 16, 'Partial', fill=AMBER_BG, fs=8, dash=True)
    s.chip(rx + 166, y + 350, 70, 16, 'Mismatch', fill=RED_BG, fs=8, dash=True)
    s.card(rx, y + 396, 300, 164)
    s.caps(rx + 14, y + 406, 'NU CHECKLIST')
    chk_list(s, rx + 12, y + 426, 280, [('Done', 'Reading matches the intent.'), ('Needs you', '"heartbeat message" needed the glossary. Flag to UX.'), ('Pass', 'Who, what, to whom and how often are all in one sentence.'), ('Pass', 'No undefined acronyms in R2.')], fs=9, gap=6)
    s.num(rx + 284, y + 222, 4)
    yy = y + 576
    signoff(s, cx, yy, 816, 3, 'Anything an author should know about how a newcomer reads this…', 'Rewrite in plain words', None)
    s.num(cx + 800, yy - 8, 5)
    report_link(s, cx, yy + 164)
    s.num(cx + 800, cy + 52, 1)
    s.num(cx + 800, cy + 108, 2)
    d.frame_end()
    return ['The New user lens is the only one that starts from a blank mind. Blind-first is on by default so the first read is clean.',
            'Only the proposed wording is shown first. The source model, owners and other wordings stay hidden until after the reading.',
            'Explain it back is the evidence for this lens. A match, partial or mismatch with the author\'s intent becomes a measurable comprehension result.',
            'Words that needed a lookup are routed to the UX lens as "needs a gloss". The two newcomer-facing lenses talk through that route.',
            'Sign-off for this lens: "A newcomer can read this and tell what would show it is met." A mismatch blocks, with the NU reading attached.']
