"""Board 07: group resolution, rationale, revision history, decision ledger."""
from wf2 import *


def radio(s, x, y, on, label, fs=10, color=INK):
    s.shape('ellipse', x, y, 13, 13, fill='#ffffff', stroke=INK, sw=1.5, pad=0)
    if on:
        s.shape('ellipse', x + 3.5, y + 3.5, 6, 6, fill=INK, stroke=INK, pad=0)
    if label:
        s.t(x + 20, y - 1, label, fs=fs, color=color)


def numline(s, x, y, w, pts, marks=(), scale=365):
    """pts: list of (label, value). marks: list of (label, value, color)."""
    s.line([(x, y + 30), (x + w, y + 30)], stroke=SOFT, sw=2)
    for lab, v in pts:
        px = x + w * v / scale
        s.shape('ellipse', px - 5, y + 25, 10, 10, fill='#ffffff', stroke=INK, sw=1.5, pad=0)
        s.t(px - 14, y + 40, lab, fs=8, color=DARK)
    for lab, v, col in marks:
        px = x + w * v / scale
        s.poly([(px, y + 4), (px, y + 24)], typ='line', stroke=col, sw=2, dash=True)
        s.t(px - len(lab) * 2.6, y - 10, lab, fs=8, color=col, family=3)


# ---------------------------------------------------------------- G1 workspace with resolve panel
def g1_workspace(d, ox, oy):
    W, H = 1000, 960
    s = new_frame(d, ox, oy, W, H, 'G1 · A group of six: evidence on the left, Resolve panel docked on the right (no separate screen)')
    cx, cy = shell2(s, W, H, 'Review queue', 0)
    s.t(cx, cy, 'CL-050 · Data retention: 6 wordings', fs=20, family=2, color=INK)
    s.chip(cx, cy + 32, 60, 16, 'Lane B', fill=AMBER_BG, fs=9)
    s.chip(cx + 66, cy + 32, 62, 16, 'Variant', fill=VIOLET_BG, fs=9)
    s.chip(cx + 134, cy + 32, 62, 16, 'In review', fill='#ffffff', fs=9)
    s.chip(cx + 202, cy + 32, 90, 16, '6 members', fill=GREY, fs=9)
    s.chip(cx + 298, cy + 32, 150, 16, 'Needs a decision from you', fill=RED_BG, fs=8)
    sign_dots(s, cx + 660, cy + 6, ['pending'] * 4)
    # left: members
    y0 = cy + 62
    s.card(cx, y0, 500, 300)
    s.caps(cx + 14, y0 + 10, 'MEMBERS (6) · SAME ACTOR, ACTION AND OBJECT')
    rows = [['M1  SYS-0140', 'store all fault events for at least 30 days', '30 d', ('Comparable', GREEN_BG)],
            ['M2  SYS-0141', 'store all fault records for at least 60 days', '60 d', ('Comparable', GREEN_BG)],
            ['M3  SYS-0143', 'store fault events for a minimum of 90 days', '90 d', ('Comparable', GREEN_BG)],
            ['M4  SYS-0147', 'store all faults for 1 year', '365 d', ('Comparable', GREEN_BG)],
            ['M5  SYS-0152', 'store fault events for 30 days after landing', '30 d', ('Different condition', AMBER_BG)],
            ['M6  SYS-0158', 'store fault event data until the next maintenance cycle', 'none', ('Not a number', RED_BG)]]
    ty = table(s, cx + 12, y0 + 30, [86, 222, 52, 116], ['ID', 'The Data Recorder shall…', 'Value', 'Can we rank it?'], rows, fs=9, minh=34)
    s.t(cx + 14, ty + 8, 'Rank = which is stricter. Only M1 to M4 can be ranked automatically.', fs=8, color=SOFT)
    s.num(cx + 484, y0 - 8, 1)
    # number line
    y1 = y0 + 314
    s.card(cx, y1, 500, 128)
    s.caps(cx + 14, y1 + 10, 'WHERE THE COMPARABLE VALUES SIT (DAYS)')
    numline(s, cx + 40, y1 + 44, 420, [('M1 30', 30), ('M2 60', 60), ('M3 90', 90), ('M4 365', 365)], [('least', 30, '#b35a00'), ('median 75', 75, AIC), ('most', 365, RED)])
    s.t(cx + 14, y1 + 100, s.d.wrap('Stricter means longer for a retention minimum. The direction is set once per parameter type by an SE (see G2) and reused.', 470, 9), fs=9, color=SOFT)
    s.num(cx + 484, y1 - 8, 2)
    # what is the same and discussion
    y2 = y1 + 142
    s.card(cx, y2, 500, 124)
    s.caps(cx + 14, y2 + 10, 'DISCUSSION (2) · NOTES FROM OTHER PEOPLE')
    avatar(s, cx + 14, y2 + 32, 'PE', VIOLET_BG, 22)
    s.t(cx + 44, y2 + 32, s.d.wrap('PE-1: Parent SYS-0310 says "retain at least one year". M1 to M3 look under-specified.', 440, 9), fs=9, color=DARK)
    avatar(s, cx + 14, y2 + 72, 'SE', BLUE_BG, 22)
    s.t(cx + 44, y2 + 72, s.d.wrap('SE-1: @Data-team-lead can you confirm 365 days is intended? M5 and M6 look separate.', 440, 9), fs=9, color=DARK)
    s.num(cx + 484, y2 - 8, 3)
    # guards
    y3 = y2 + 138
    s.card(cx, y3, 500, 156)
    s.caps(cx + 14, y3 + 10, 'GUARDS ON THE RESULT YOU PICK (RE-RUN LIVE)')
    guard_row(s, cx + 14, y3 + 34, 460, 'Numbers preserved', 'p', 'comes from M4')
    guard_row(s, cx + 14, y3 + 60, 460, 'Units compatible', 'w', '1 year = 365 d')
    guard_row(s, cx + 14, y3 + 86, 460, 'Shall / should / will preserved', 'p')
    guard_row(s, cx + 14, y3 + 112, 460, 'Condition kept for every member in the merge', 'w', 'M5 excluded')
    # right panel
    rx = cx + 516
    s.r(rx, y0, 300, 690, fill='#ffffff', stroke=ACC, sw=2)
    s.r(rx, y0, 300, 28, fill=ACC_BG, stroke=ACC_BG, rounded=False)
    s.t(rx + 12, y0 + 8, 'RESOLVE THIS GROUP', fs=9, color=ACC, family=3)
    s.t(rx + 168, y0 + 8, 'stays in view as you scroll', fs=8, color=SOFT)
    s.caps(rx + 12, y0 + 40, '1  WHAT SHOULD HAPPEN?')
    cxx = rx + 12
    for lab, on, wd in [('Merge', True, 52), ('Keep and link', False, 84), ('Ask owners', False, 72), ('Reject', False, 52)]:
        s.chip(cxx, y0 + 58, wd, 22, lab, fill=ACC if on else '#ffffff', stroke=ACC, color='#ffffff' if on else DARK, fs=9)
        cxx += wd + 5
    s.caps(rx + 12, y0 + 94, '2  HOW IS THE MERGED WORDING SET?')
    opts = [('Most stringent', 'mech', 'at least 1 year (from M4)', True), ('Least stringent', 'mech', 'at least 30 days. Weakens: owner must approve', False),
            ('Median member', 'mech', '60 or 90 d: pick lower or upper middle', False), ('One member\'s wording', 'mech', 'use M3 as the base', False),
            ('My own wording', 'hum', 'opens the editor', False), ('Ask the AI to propose', 'ai', 'it picks, drafts and explains. You review', False)]
    for i, (lab, k, sub, on) in enumerate(opts):
        yy = y0 + 114 + i * 42
        if on:
            s.r(rx + 6, yy - 4, 288, 40, fill='#F1F6FF', stroke=ACC)
        radio(s, rx + 14, yy, on, lab, fs=10)
        s.prov(rx + 14 + 120 + 20, yy + 1, k)
        s.t(rx + 34, yy + 16, s.d.wrap(sub, 250, 8), fs=8, color=SOFT)
    yy = y0 + 114 + 6 * 42 + 6
    s.caps(rx + 12, yy, '3  PREVIEW (NOT SAVED)')
    s.r(rx + 12, yy + 18, 276, 62, fill='#ffffff', stroke=LINE)
    tokw(s, rx + 20, yy + 24, 262, 'The Data Recorder shall store all fault events for at least 365 days.', fs=9, differs=('365',))
    s.t(rx + 12, yy + 86, 'Covers M1 to M4. M5 and M6 stay as they are and link as related.', fs=8, color=SOFT)
    yy += 108
    s.caps(rx + 12, yy, '4  WHY? (REQUIRED HERE: M5 AND M6 NOT COVERED)')
    s.r(rx + 12, yy + 18, 276, 24, 'Reason code:  Strictest satisfies all ranked members  ▾', fill='#ffffff', stroke=LINE, fs=8, align='left', pad=6)
    s.r(rx + 12, yy + 48, 276, 54, fill='#ffffff', stroke=LINE)
    s.t(rx + 20, yy + 54, s.d.wrap('Note: Parent SYS-0310 requires one year. Data team lead to confirm on…', 258, 8), fs=8, color=SOFT)
    yy += 114
    s.btn(rx + 12, yy, 160, 34, 'Save decision', primary=True, fs=10)
    s.btn(rx + 180, yy, 108, 34, 'Save draft', fs=9)
    s.t(rx + 12, yy + 44, s.d.wrap('Saving sends this to PE, UX and NU for sign-off. The note is stored with the revision. You can undo.', 276, 8), fs=8, color=SOFT)
    s.num(rx + 284, y0 - 8, 4)
    d.frame_end()
    return ['Left: the evidence, in the order a reviewer reads it. A table of all six with a plain "can we rank it?" column, a number line, notes from other people and live guards.',
            'The number line makes the strategies concrete: least, median and most are positions on it. Items that cannot be placed (M5, M6) are named, not hidden.',
            'Discussion is part of the workspace. @mentions notify people. The assistant (board 08) can read this thread.',
            'The Resolve panel is docked, not a separate screen. Evidence and decision stay in view together, so there is no tab-hopping and no lost context. Four steps: outcome, wording, preview, reason.',
            'Why not a separate screen: it would split evidence from the decision, add a step on every cluster, and hide the guards. The panel collapses on small screens and becomes a bottom sheet on a phone.']


# ---------------------------------------------------------------- G2 strategies
def g2_strategies(d, ox, oy):
    W, H = 1500, 790
    s = new_frame(d, ox, oy, W, H, 'G2 · The six ways to resolve a group, shown on one numeric example', bg='#ffffff')
    s.t(20, 14, 'Six strategies, and what each really does', fs=24, family=1, color=INK)
    s.t(20, 50, 'Example: CL-050, four rankable members (30, 60, 90, 365 days). "At least" minimums. Marks: square = computed, circle = person writes it, diamond = AI proposes.', fs=12, color=SOFT)
    rows = [['Most stringent', '', 'Computed', 'at least 365 days', 'Safety, compliance, or the strictest value already satisfies all the others (true for minimums).', 'May over-constrain the design or cost. Owner should know the cost of the longest value.'],
            ['Least stringent', '', 'Computed', 'at least 30 days', 'The strict values were mistakes, and the owner says so.', 'Weakens the requirement. Always flagged "weakening", needs the owner and PE, and a note. Never a default.'],
            ['Median', '', 'Computed', '75 d does not exist. Pick 60 (lower) or 90 (upper).', 'A negotiated target with a tolerance, agreed by all owners.', 'A median can satisfy nobody\'s source need. Offered, but gated: owner confirmation and a note.'],
            ['One member\'s wording', '', 'You pick', 'M3: at least 90 days', 'One owner is the source of truth and the others are copies.', 'Others\' values are dropped. Guard checks that nothing numeric is lost.'],
            ['My own wording', '', 'You write it', 'Anything, within guards', 'The members disagree on structure, or a new condition is needed.', 'Reason required. Becomes a human revision. Guards still run.'],
            ['Ask the AI to propose', '', 'AI proposes, you review', 'Picks a strategy, drafts, explains', 'Many members, and you want a second opinion or a first draft.', 'AI never saves a decision. Lane C: it may summarise the options but not choose one.']]
    y = table(s, 20, 82, [128, 34, 112, 190, 250, 300], ['Strategy', 'Mark', 'Who sets it', 'Result on CL-050', 'Use it when', 'Watch out for'], rows, fs=9, minh=50, bold_first=True)
    for i, k in enumerate(['mech', 'mech', 'mech', 'mech', 'hum', 'ai']):
        s.prov(20 + 128 + 12, 82 + 26 + i * 50 + 20, k)
    s.num(20 + 1000, 72, 1)
    # not comparable
    s.r(20, y + 20, 1014, 140, fill='#fff9db', stroke='#f1c40f')
    s.t(34, y + 30, 'Members that cannot be ranked (M5 and M6)', fs=13, family=1, color=INK)
    for i, t_ in enumerate(['M5 "30 days after landing" has a different condition from the others. The tool does not compare a condition to a number. Offer: keep separate and link, or add the condition to the merged wording.',
                            'M6 "until the next maintenance cycle" has no number. Offer: keep separate, ask the owner for a number, or include it in your own wording.',
                            'Automatic strategies only ever act on members they can rank. The panel says how many it covered, and what happens to the rest.']):
        s.t(34, y + 56 + i * 30, '•  ' + s.d.wrap(t_, 970, 10), fs=10, color='#5c4400')
    s.num(20 + 1000, y + 12, 2)
    # right: stringency direction
    s.caps(1070, 82, 'WHICH WAY IS "STRICTER"? SET ONCE PER PARAMETER TYPE')
    rows2 = [['Retention period (minimum)', 'Longer', 'Human'],
             ['Response or latency (maximum)', 'Shorter', 'Human'],
             ['Update interval (maximum)', 'Shorter', 'Human'],
             ['Position error (maximum)', 'Smaller', 'Human'],
             ['Availability (minimum)', 'Higher', 'Human'],
             ['Operating temperature range', 'Wider', 'Human'],
             ['Anything not listed', 'Unknown: ask', 'Needs an SE']]
    y2 = table(s, 1070, 104, [200, 130, 80], ['Parameter type', 'Stricter means', 'Set by'], rows2, fs=9, minh=26)
    s.num(1070 + 400, 94, 3)
    para(s, 1070, y2 + 10, 'The tool never guesses direction. The AI may suggest one, a person confirms it, and it is recorded with who and when. Without a direction the strategy is disabled, not defaulted.', 410, 10, DARK)
    # number line example
    s.card(1070, y2 + 90, 410, 150)
    s.caps(1084, y2 + 100, 'CL-050 ON THE NUMBER LINE (DAYS)')
    numline(s, 1100, y2 + 134, 350, [('30', 30), ('60', 60), ('90', 90), ('365', 365)], [('least', 30, '#b35a00'), ('median 75', 75, AIC), ('most', 365, RED)])
    s.t(1084, y2 + 208, 'No member sits at 75, so Median asks you to pick 60 or 90.', fs=8, color=SOFT)
    s.num(1070 + 400, y2 + 82, 4)
    # AI decides: correct the user
    yb = y + 180
    s.r(20, yb, 1014, 170, fill='#f8f0fc', stroke=AIC)
    s.prov(34, yb + 14, 'ai')
    s.t(54, yb + 11, '"Let the AI decide": what that can and cannot mean', fs=13, family=1, color=AIC)
    for i, (t_, ok) in enumerate([('AI chooses a strategy and drafts the wording, with reasons and quotes. Yes.', True), ('You review a one-screen summary and accept, edit or reject. Yes.', True),
                                  ('In low-risk Lane A the project may allow one-click accept per cluster, with a reason code filled in from the AI record. Optional, project setting.', True),
                                  ('AI saving a decision on its own, or accepting for you in bulk. No. "Accept all" is off, and guards cannot be overridden by the AI.', False)]):
        s.t(34, yb + 42 + i * 30, ('✓  ' if ok else '✕  ') + s.d.wrap(t_, 960, 10), fs=10, color=DARK if ok else RED)
    s.num(20 + 1000, yb - 8, 5)
    d.frame_end()
    return ['Each strategy says who sets the result (computed, you, or AI), what it gives on this example, when it fits and what to watch.',
            'Not every member can be ranked. The tool names those, offers keep-separate or ask-the-owner, and never silently drops them.',
            '"Stricter" depends on the parameter. Shorter latency is stricter, longer retention is stricter, a wider temperature range is stricter. A person sets it once per type.',
            'Correction to the idea of a median: for requirements it is rarely right, because it can satisfy nobody\'s source need. It is available, gated and noted.',
            'AI makes a proposal with reasons. A person makes the decision. A project may allow one-click accept in Lane A, never unattended bulk accept.']


# ---------------------------------------------------------------- G3 rationale
def g3_rationale(d, ox, oy):
    W, H = 1500, 810
    s = new_frame(d, ox, oy, W, H, 'G3 · Why was it decided? The human record and the AI record, kept apart', bg='#ffffff')
    s.t(20, 14, 'Two records per decision: what the person said, and what the AI said', fs=24, family=1, color=INK)
    s.t(20, 50, 'They are stored separately on purpose. The AI\'s reasons are explanations, not proof, and a reviewer\'s note is never auto-filled from them.', fs=12, color=SOFT)
    # human record
    s.card(20, 84, 470, 660)
    s.prov(34, 98, 'hum')
    s.caps(52, 96, 'DECISION RECORD · CL-050 · HUMAN')
    s.t(34, 118, 'SE-2 · 3 Oct 10:42 · lens SE · saved on cluster version 16', fs=9, color=SOFT)
    for i, (k, v) in enumerate([('Decision', 'Merge into one wording'), ('Strategy', 'Most stringent (computed)'), ('Covers', 'M1 to M4. M5 and M6 kept, linked as related'), ('Result', 'R4 · human-edited AI draft · hash 7c1e…'), ('Reason code', 'Strictest satisfies all ranked members')]):
        kv(s, 34, 146 + i * 24, k, v, kw=100, fs=10)
    s.caps(34, 276, 'REVIEWER\'S NOTE (FREE TEXT, THEIR OWN WORDS)')
    s.r(34, 296, 440, 84, fill='#fffdf5', stroke='#f1c40f')
    s.t(44, 304, s.d.wrap('Parent SYS-0310 requires one year. Data team lead confirmed 365 days by email on 2 Oct. M5 and M6 stay separate because their conditions differ.', 420, 10), fs=10, color=INK)
    s.caps(34, 398, 'ATTACHED AUTOMATICALLY (THEY CANNOT BE FORGOTTEN)')
    for i, t_ in enumerate(['The six original wordings as they were on the decision date (hashes)', 'Parent trace SYS-0310 and the guard results at that time', 'AI record AIR-0412 and the discussion thread (2 comments)', 'Your lens, the cluster version and the revision hash']):
        s.t(34, 420 + i * 22, '•  ' + t_, fs=9, color=DARK)
    s.caps(34, 520, 'SIGN-OFFS BOUND TO R4')
    sign_dots(s, 34, 540, ['signed', 'signed', 'pending', 'pending'])
    s.t(120, 542, 'A change to the text makes these stale.', fs=9, color=SOFT)
    s.btn(34, 580, 170, 32, 'Reopen with a reason', fs=10)
    s.btn(212, 580, 130, 32, 'View history', fs=10)
    s.r(34, 630, 440, 40, fill=GREY, stroke=LINE)
    s.t(44, 636, s.d.wrap('A decision is never edited. Reopening creates a new decision that points back to this one.', 420, 9), fs=9, color=DARK)
    s.num(470, 76, 1)
    # AI record
    s.r(510, 84, 470, 660, fill='#fbf5fd', stroke=AIC)
    s.prov(524, 98, 'ai')
    s.caps(542, 96, 'AI RECOMMENDATION RECORD · AIR-0412 · IMMUTABLE', color=AIC)
    s.t(524, 118, 'Written by the system when the AI ran. Nobody can edit it.', fs=9, color=SOFT)
    for i, (k, v) in enumerate([('Model', 'exact id and version (sample)'), ('Prompt', 'merge-v7 · hash 91ab…'), ('Inputs', 'six wordings + parent trace · hash 5d20…'), ('Runs', '3 of 3 agree'), ('Suggested', 'Merge · Most stringent'), ('Guards then', 'numbers pass · units warning')]):
        kv(s, 524, 146 + i * 24, k, v, kw=100, fs=10)
    s.caps(524, 304, 'THE AI\'S REASONS (ITS WORDS, VERBATIM QUOTES CHECKED)', color=AIC)
    s.r(524, 324, 440, 118, fill='#ffffff', stroke=AIC)
    for i, t_ in enumerate(['All six describe how long the Data Recorder keeps fault events.', 'M1 to M3 give a minimum, so the longest value (M4) also satisfies them.', 'M5 adds "after landing" and M6 gives no number, so they are not merged.']):
        s.t(534, 334 + i * 34, '•  ' + s.d.wrap(t_, 410, 10), fs=10, color=DARK)
    s.caps(524, 458, 'QUOTES IT RELIED ON', color=AIC)
    for i, (m, q) in enumerate([('M3', '"a minimum of 90 days"'), ('M4', '"for 1 year"')]):
        s.t(524, 480 + i * 24, m + '  ' + q, fs=10, color=INK)
        s.chip(740, 478 + i * 24, 130, 16, 'verbatim check: pass', fill=GREEN_BG, fs=8)
    s.caps(524, 548, 'WHAT THE REVIEWER DID WITH IT', color=AIC)
    for i, (lab, f) in enumerate([('Strategy: accepted', GREEN_BG), ('Wording: light edit, 8%', AMBER_BG), ('Overall: agreed', GREEN_BG)]):
        s.chip(524 + i * 150, 570, 144, 20, lab, fill=f, fs=9)
    s.t(524, 604, s.d.wrap('If the reviewer had disagreed, a reason would be required and this line would say "overrode AI".', 440, 9), fs=9, color=SOFT)
    s.r(524, 646, 440, 50, fill=AMBER_BG, stroke='#f1c40f')
    s.t(534, 652, s.d.wrap('Reasons from a model are explanations, not proof. They are shown and kept, but guards and people decide.', 420, 9), fs=9, color='#5c4400')
    s.num(960, 76, 2)
    # right side
    s.caps(1000, 84, 'REASON CODES (PROJECT LIST, EDITABLE BY ADMIN)')
    for i, t_ in enumerate(['Strictest satisfies all ranked members', 'Parent requires this value', 'Owner confirmed (comment linked)', 'Different condition: kept separate', 'Not a duplicate: different function', 'AI was wrong about: unit, scope, number, other', 'Source changed: decided again', 'Other (a note is required)']):
        s.r(1000, 104 + i * 28, 470, 24, fill='#ffffff', stroke=LINE)
        s.t(1010, 109 + i * 28, t_, fs=10, color=DARK)
    s.num(1456, 94, 3)
    s.caps(1000, 346, 'A NOTE IS REQUIRED WHEN YOU…')
    for i, t_ in enumerate(['pick least stringent, median or your own wording', 'disagree with the AI\'s strategy', 'weaken a requirement (looser value, shall to should)', 'override a guard warning (leads only)', 'reject a suggestion in lane B or C', 'reopen any decision']):
        s.t(1000, 368 + i * 24, '•  ' + t_, fs=10, color=DARK)
    s.t(1000, 524, 'Not required: accepting the computed default in lane A. A reason code is enough.', fs=10, color=SOFT)
    s.num(1456, 338, 4)
    s.r(1000, 560, 470, 184, fill='#fff9db', stroke='#f1c40f')
    s.t(1014, 572, 'Why keep disagreements', fs=12, family=1, color=INK)
    s.t(1014, 600, s.d.wrap('When a reviewer overrides the AI and says why, that pair becomes a labelled example. The gold set (board 09) grows from real disagreements, which is where the model is weakest and where the next calibration should look.', 440, 10), fs=10, color='#5c4400')
    s.t(1014, 690, s.d.wrap('It also answers the audit question: what did the AI say, and what did you do with it?', 440, 10), fs=10, color='#5c4400')
    s.num(1456, 552, 5)
    d.frame_end()
    return ['Human record: decision, strategy, reason code, free-text note, and what was attached automatically. Sign-offs are bound to the revision.',
            'AI record: model, prompt version, inputs, runs, reasons and verbatim quotes, plus what the reviewer did with it. Written once, never edited.',
            'Reason codes make decisions searchable and comparable. The list is project-specific. "Other" always needs a note.',
            'Notes are required where the stakes or the disagreement are highest. The default accept path in lane A stays light.',
            'Disagreements with the AI are kept as labelled examples. That is how the gold set stays honest.']


# ---------------------------------------------------------------- G4 revision chain
def g4_revisions(d, ox, oy):
    W, H = 1500, 990
    s = new_frame(d, ox, oy, W, H, 'G4 · Revision chain: what happens when a human edits after the AI', bg='#ffffff')
    s.t(20, 14, 'Every wording is a revision. Edits add children, nothing is overwritten.', fs=24, family=1, color=INK)
    s.t(20, 50, 'Example: CL-050, the merged retention requirement. Square = computed, diamond = AI, circle = a person.', fs=12, color=SOFT)
    nodes = [(20, 'R0', 'originals M1 to M6', 'from source, read only', SRC_F, INK, False, 'src'), (265, 'R1', 'computed result', 'most stringent', MECH_F, INK, False, 'mech'),
             (510, 'R2', 'AI draft', 'AIR-0412', AI_F, AIC, False, 'ai'), (755, 'R3a', 'SE-2 edit', 'adds "(1 year)"', HUM_F, HUM, False, 'hum'), (1000, 'R4', 'SE-2 edit', 'after UX suggestion', HUM_F, HUM, False, 'hum')]
    ny = 110
    for x, rid, l1, l2, f, st, dash, k in nodes:
        s.r(x, ny, 200, 76, fill=f, stroke=st, sw=2, dash=dash)
        s.t(x + 12, ny + 8, rid, fs=14, family=1, color=INK)
        if k != 'src':
            s.prov(x + 170, ny + 12, k)
        s.t(x + 12, ny + 32, l1, fs=11, color=INK)
        s.t(x + 12, ny + 50, l2, fs=9, color=SOFT)
    for x in (220, 465, 710, 955):
        s.poly([(x, ny + 38), (x + 45, ny + 38)], stroke=INK, sw=2)
    # siblings and suggestion
    s.r(755, ny + 130, 200, 66, fill='#ffffff', stroke=SOFT, dash=True, sw=2)
    s.t(767, ny + 138, 'R3b  SE-1 edit', fs=11, color=INK)
    s.t(767, ny + 158, 'sibling, not chosen. Kept.', fs=9, color=SOFT)
    s.poly([(690, ny + 76), (690, ny + 162), (755, ny + 162)], stroke=SOFT, sw=1.5, dash=True)
    s.r(1000, ny + 130, 200, 66, fill='#ffffff', stroke=ACC, dash=True, sw=2)
    s.t(1012, ny + 138, 'UX-1 suggestion', fs=11, color=INK)
    s.t(1012, ny + 158, s.d.wrap('say "fault events", not "records"', 180, 9), fs=9, color=SOFT)
    s.poly([(1180, ny + 130), (1180, ny + 76)], stroke=ACC, sw=1.5, dash=True)
    s.r(1250, ny, 210, 76, fill='#ffffff', stroke=HUM, sw=3)
    s.t(1262, ny + 8, 'Approved', fs=14, family=1, color=INK)
    s.t(1262, ny + 32, 'when required lenses sign R4', fs=9, color=DARK)
    sign_dots(s, 1262, ny + 52, ['signed', 'signed', 'pending', 'pending'])
    s.poly([(1200, ny + 38), (1250, ny + 38)], stroke=INK, sw=2)
    s.r(1250, ny + 130, 210, 66, fill='#f8f0fc', stroke=AIC, dash=True, sw=2)
    s.t(1262, ny + 138, 'R5-ai  AI re-suggestion', fs=11, color=INK)
    s.t(1262, ny + 158, s.d.wrap('new model or source change. Sibling, never replaces R4', 190, 9), fs=9, color=SOFT)
    s.prov(1436, ny + 142, 'ai')
    s.num(1440, ny - 10, 1)
    s.num(940, ny + 120, 2)
    s.num(1440, ny + 120, 3)
    for x, t_ in [(20, 'hash 51fe…  parent: none'), (265, 'hash 3a9c…  parent R0'), (510, 'hash 8d02…  parent R1'), (755, 'hash 2b77…  parent R2'), (1000, 'hash 7c1e…  parent R3a')]:
        s.t(x + 4, ny + 84, t_, fs=8, color=SOFT, family=3)
    # diff panel
    s.card(20, 340, 760, 250)
    s.caps(34, 350, 'DIFF R2 TO R3a · REASON IS REQUIRED FOR EVERY HUMAN EDIT')
    s.t(34, 380, 'R2', fs=10, color=AIC)
    tokw(s, 70, 376, 690, 'The Data Recorder shall store all fault events for at least 365 days.', fs=10)
    s.t(34, 420, 'R3a', fs=10, color=HUM)
    tokw(s, 70, 416, 690, 'The Data Recorder shall store all fault events for at least 365 days (1 year).', fs=10, differs=('(1', 'year).'))
    s.caps(34, 466, 'REASON')
    s.r(34, 484, 730, 26, 'Readers think in years for this item. Number unchanged.', fill='#fffdf5', stroke='#f1c40f', fs=10, align='left', pad=8, color=INK)
    s.caps(34, 526, 'WHERE THE TEXT CAME FROM (R4)')
    s.r(34, 546, 440, 18, fill=AIC, stroke=AIC, rounded=False)
    s.r(34 + 440 * .92, 546, 440 * .08, 18, fill=HUM, stroke=HUM, rounded=False)
    s.t(484, 546, '92% from AI draft · 8% human', fs=10, color=INK)
    s.t(34, 570, 'Bucket: light edit. Computed from the text, not typed by anyone.', fs=9, color=SOFT)
    s.num(764, 332, 4)
    # buckets
    s.card(800, 340, 660, 250)
    s.caps(814, 350, 'HOW MUCH OF THE AI DRAFT SURVIVED')
    rows = [['As is', 'under 5% changed', 'Labelled "AI-drafted, human-approved"'], ['Light edit', '5% to 30%', 'Labelled "AI-assisted, human-edited"'], ['Heavy edit', '30% to 70%', 'Labelled "AI-assisted, human-edited"'], ['Rewritten', 'over 70%', 'Labelled "human-written, AI-informed"']]
    ty = table(s, 814, 372, [100, 150, 360], ['Bucket', 'Words changed', 'Label in exports and reports'], rows, fs=9, minh=28, bold_first=True)
    s.t(814, ty + 10, s.d.wrap('Buckets are proposals for the project to set. They are measured by edit distance on words, so a typo fix and a new idea are not the same.', 620, 9), fs=9, color=SOFT)
    s.num(1440, 332, 5)
    # rules
    s.r(20, 620, 1440, 340, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 632, 'How a human edit after an AI edit is treated', fs=14, family=1, color=INK)
    rules = ['The AI draft is never overwritten. A human edit is a new child of it. R3a is a child of R2, and R2 stays viewable forever.',
             'A reason is required for every human edit, and it is stored with the diff.',
             'Authorship is tracked by text, not by label: each revision stores how much of its words came from the AI draft.',
             'Exports and reports carry that label ("AI-assisted, human-edited"). They never say only "approved".',
             'Sign-offs bind to a revision hash. Change the words and every earlier sign-off is stale, unless the change is whitespace only.',
             'If the AI runs again, its output arrives as a new sibling (R5-ai). It never replaces a revision a person edited. You can compare, and adopt by editing.',
             'Two people editing at once make sibling revisions (R3a, R3b). Someone picks one on purpose and says why. Both stay in history.',
             'Reverting is a new revision that copies an old one. History only grows.']
    for i, t_ in enumerate(rules):
        s.shape('ellipse', 34, 666 + i * 36, 18, 18, str(i + 1), fs=9, fill='#ffffff', stroke='#b35a00', pad=0)
        s.t(60, 667 + i * 36, s.d.wrap(t_, 1360, 11), fs=11, color='#3b2f00')
    s.num(1440, 612, 6)
    d.frame_end()
    return ['The chain: R0 originals, R1 computed, R2 AI draft, R3a human edit, R4 human edit. Each box has a hash, a parent and an author mark.',
            'Branches are visible. R3b was a second person\'s edit at the same time. It stays in history, marked not chosen.',
            'A later AI run is a sibling, never a replacement. A person decides whether to adopt anything from it.',
            'Diff with a required reason. The reason, not the diff alone, is what a later reader needs.',
            'Authorship by buckets. The project chooses the thresholds and the labels. The measure is computed, so nobody has to remember to tag it.',
            'The eight rules in one place. These are the answer to "how is a human edit after an AI edit treated".']


# ---------------------------------------------------------------- G5 ledger and history
def g5_ledger(d, ox, oy):
    W, H = 1000, 880
    s = new_frame(d, ox, oy, W, H, 'G5 · Decision ledger and the history of one requirement')
    cx, cy = shell2(s, W, H, 'Audit log', 0)
    s.h1(cx, cy, 'Decision ledger', fs=22)
    s.t(cx, cy + 32, 'Every decision in the project, newest first. Open any row to see the record, the AI record and the revisions.', fs=10, color=DARK)
    for i, (lab, on, wd) in enumerate([('All', True, 40), ('Mine', False, 48), ('Overrode AI', False, 86), ('Weakening', False, 80), ('Reopened', False, 72), ('Stale', False, 50)]):
        pass
    x = cx
    for lab, on, wd in [('All', True, 40), ('Mine', False, 48), ('Overrode AI', False, 86), ('Weakening', False, 80), ('Reopened', False, 72), ('Stale', False, 50)]:
        s.chip(x, cy + 58, wd, 20, lab, fill=ACC if on else '#ffffff', stroke=ACC, color='#ffffff' if on else DARK, fs=9)
        x += wd + 8
    s.r(cx + 520, cy + 58, 296, 20, 'Search notes, reasons, IDs', fill='#ffffff', stroke=LINE, fs=9, align='left', pad=8, color=SOFT)
    rows = [['3 Oct 10:42', 'CL-050', 'Merge M1 to M4', 'Most stringent', 'SE-2', 'Strictest satisfies all ranked members', 'Agreed', ('Current', GREEN_BG)],
            ['3 Oct 09:15', 'CL-048', 'Ask owners', '-', 'SE-1', 'Different owners: change board', 'Agreed', ('Disputed', RED_BG)],
            ['2 Oct 16:30', 'CL-046', 'Merge', 'Own wording', 'SE-3', 'Parent requires this value', ('Overrode AI', AMBER_BG), ('Current', GREEN_BG)],
            ['1 Oct 11:05', 'CL-047', 'Merge', 'Least stringent', 'SE-1', 'Owner confirmed (weakening)', ('Overrode AI', AMBER_BG), ('Stale', '#e8deff')],
            ['1 Oct 10:20', 'CL-042', 'Merge', 'AI proposal', 'SE-2', 'Strictest satisfies all ranked members', 'Agreed', ('Current', GREEN_BG)],
            ['30 Sep 15:48', 'CL-041', 'Reject', '-', 'SE-1', 'Not a duplicate: different function', ('Overrode AI', AMBER_BG), ('Reopened', AMBER_BG)]]
    y = table(s, cx, cy + 92, [76, 52, 100, 92, 40, 220, 74, 62], ['When', 'Cluster', 'Decision', 'Strategy', 'By', 'Reason code', 'Vs AI', 'State'], rows, fs=8, minh=32, pad=5)
    s.num(cx + 800, cy + 84, 1)
    # history
    hy = y + 24
    s.card(cx, hy, 480, 410)
    s.caps(cx + 14, hy + 10, 'HISTORY OF REQ-SYS-0140')
    ev = [('src', '18 Sep', 'Imported from source (R0, hash 51fe…)'), ('mech', '19 Sep', 'Placed in CL-050 by the methods (score 0.74)'), ('ai', '20 Sep', 'AI proposed merge, most stringent (AIR-0412)'),
          ('hum', '2 Oct', 'SE-1 note: ask the Data team lead'), ('hum', '3 Oct', 'SE-2 decided: merge M1 to M4, wording R4'), ('hum', '3 Oct', 'PE-1 signed R4'),
          ('src', '8 Oct', 'Source changed: SYS-0143 text. Decision marked stale'), ('hum', '9 Oct', 'SE-2 re-ran the comparison. R5-ai waiting for review')]
    s.line([(cx + 28, hy + 40), (cx + 28, hy + 40 + (len(ev) - 1) * 44)], stroke=LINE, sw=2)
    for i, (k, dt, t_) in enumerate(ev):
        yy = hy + 34 + i * 44
        if k == 'src':
            s.shape('ellipse', cx + 22, yy + 4, 12, 12, fill='#d0ebff', stroke=INK, pad=0)
        else:
            s.prov(cx + 23, yy + 4, k)
        s.t(cx + 46, yy, dt, fs=9, color=SOFT, family=3)
        s.t(cx + 100, yy, s.d.wrap(t_, 360, 10), fs=10, color=DARK)
    s.num(cx + 464, hy - 8, 2)
    s.card(cx + 496, hy, 320, 410)
    s.caps(cx + 510, hy + 10, 'WHY IS THIS REQUIREMENT AN ALIAS?')
    s.t(cx + 510, hy + 36, s.d.wrap('REQ-SYS-0140 was retired as an alias of the merged requirement on 3 Oct by SE-2.', 292, 10), fs=10, color=INK)
    for i, (k, v) in enumerate([('Strategy', 'Most stringent'), ('Reason', 'Strictest satisfies all ranked members'), ('Signed', 'SE, PE. UX and NU pending'), ('Now', 'Stale since 8 Oct')]):
        kv(s, cx + 510, hy + 84 + i * 36, k, s.d.wrap(v, 200, 9), kw=76, fs=9)
    s.r(cx + 510, hy + 244, 292, 50, fill=AMBER_BG, stroke='#f1c40f')
    s.t(cx + 520, hy + 250, s.d.wrap('The source changed after this decision. Re-run the comparison before relying on it.', 272, 9), fs=9, color='#5c4400')
    s.btn(cx + 510, hy + 310, 136, 32, 'Open decision', fs=10)
    s.btn(cx + 654, hy + 310, 148, 32, 'Reopen with a reason', fs=9)
    s.r(cx + 510, hy + 354, 292, 34, 'Ask the assistant why ▸', fill='#e3f4fb', stroke=CHAT, color=CHAT, fs=10)
    s.num(cx + 800, hy + 348, 3)
    d.frame_end()
    return ['One ledger for the whole project. Filter by who, which lens, and the cases that matter later: overrode the AI, weakened a requirement, reopened, stale.',
            'Per-requirement history in plain language. Source events, mechanical events, AI events and human events use the same marks as everywhere else.',
            '"Ask the assistant why" opens the chat already loaded with this requirement\'s history (board 08).']
