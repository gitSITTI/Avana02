"""Board 05 (continued): concurrency, policy/permissions, scale numbers."""
from wf2 import *


def mini_head(s, x, y, cid='CL-044', lane='B', rel='Variant', w=470):
    s.t(x + 14, y + 10, cid, fs=10, family=3, color=INK)
    s.chip(x + 70, y + 8, 56, 14, 'Lane ' + lane, fill=LANE_FILL[lane], fs=8)
    s.chip(x + 132, y + 8, 56, 14, rel, fill=REL_FILL.get(rel, GREY), fs=8)
    s.t(x + 200, y + 10, 'Heartbeat rate: 1 s or 10 s?', fs=10, color=INK)


def s4_states(d, ox, oy):
    W, H = 1000, 960
    s = new_frame(d, ox, oy, W, H, 'S4 · Many people, one cluster: claims, conflicts, disagreement, stale')
    s.t(20, 14, 'What a reviewer sees when other people (or the source) change things', fs=20, family=1, color=INK)
    cards = [
        ('a · Someone else is reviewing it', 'Soft claim, not a lock. Prevents duplicate effort.'),
        ('b · It changed since you opened it', 'Optimistic check on a version number. Nothing is lost.'),
        ('c · Two people edited the wording', 'Edits are private drafts until proposed. Never overwritten.'),
        ('d · Two lenses disagree', 'Changes requested blocks. A lead adjudicates, dissent is kept.'),
        ('e · A sign-off is on an older revision', 'Text changed after the lens signed. Re-confirm, do not assume.'),
        ('f · The source changed after the decision', 'Online projects move. The decision becomes stale, not wrong.'),
    ]
    for i, (t_, sub_) in enumerate(cards):
        bx, by = 20 + (i % 2) * 490, 54 + (i // 2) * 296
        s.card(bx, by, 470, 280)
        s.t(bx + 14, by + 10, t_, fs=12, color=INK)
        s.t(bx + 14, by + 28, sub_, fs=9, color=SOFT)
        mini_head(s, bx, by + 46)
        yy = by + 78
        if i == 0:
            s.r(bx + 14, yy, 442, 62, fill='#F1F6FF', stroke=ACC, dash=True, sw=2)
            avatar(s, bx + 24, yy + 10, 'SE', BLUE_BG, 26)
            para(s, bx + 60, yy + 8, 'SE-2 is reviewing this cluster (opened 6 min ago). You can read and comment. Decision buttons are off while the claim is active.', 380, 10, INK)
            s.btn(bx + 14, yy + 76, 110, 34, 'Take over', fs=10)
            s.btn(bx + 132, yy + 76, 170, 34, 'Tell me when it is free', fs=10)
            para(s, bx + 14, yy + 122, 'A claim expires after 15 minutes without activity. The server never locks anything.', 440, 9, SOFT)
            s.r(bx + 14, yy + 150, 442, 22, 'Decision buttons: Keep both and link · Ask the owners · Reject · Skip', fill=GREY, stroke=LINE, dash=True, fs=8, color=SOFT)
        if i == 1:
            s.r(bx + 14, yy, 442, 86, fill=AMBER_BG, stroke='#f1c40f')
            s.t(bx + 24, yy + 8, 'This cluster changed after you opened it (version 14 to 16)', fs=10, color='#5c4400')
            s.t(bx + 24, yy + 28, '•  10:42  SE-2 chose "Keep both and link"', fs=9, color=DARK)
            s.t(bx + 24, yy + 44, '•  10:44  Guard "Numbers preserved" re-ran: blocks merge', fs=9, color=DARK)
            s.t(bx + 24, yy + 60, '•  10:45  PE-1 added a note', fs=9, color=DARK)
            s.btn(bx + 14, yy + 100, 140, 34, 'Reload cluster', primary=True, fs=10)
            s.btn(bx + 162, yy + 100, 170, 34, 'Keep my draft note', fs=10)
            para(s, bx + 14, yy + 146, 'A decision is saved only if the version it was made on still matches. Your draft note is never lost.', 440, 9, SOFT)
        if i == 2:
            r2 = s.r(bx + 150, yy, 170, 34, 'R2  AI draft', fill=AI_F, stroke=AIC)
            ra = s.r(bx + 40, yy + 74, 170, 40, 'R3a  SE-1 edit\n“…within 2 s”', fill=HUM_F, stroke=HUM)
            rb = s.r(bx + 260, yy + 74, 170, 40, 'R3b  SE-2 edit\n“…within 5 s”', fill=HUM_F, stroke=HUM)
            s.poly([(bx + 235, yy + 34), (bx + 125, yy + 74)], stroke=INK, sw=1.5)
            s.poly([(bx + 235, yy + 34), (bx + 345, yy + 74)], stroke=INK, sw=1.5)
            s.btn(bx + 14, yy + 134, 150, 30, 'Compare revisions', fs=10)
            s.btn(bx + 172, yy + 134, 180, 30, 'Continue from one', fs=10)
            para(s, bx + 14, yy + 174, 'Both stay in history as siblings. Only one becomes the working revision, with a reason.', 440, 9, SOFT)
        if i == 3:
            for k, (nm, st, f) in enumerate([('SE: signed', 'signed', GREEN_BG), ('PE: changes requested', 'changes', RED_BG), ('UX: pending', 'pending', '#ffffff'), ('NU: pending', 'pending', '#ffffff')]):
                s.chip(bx + 14 + k * 112, yy, 106, 18, nm, fill=f, fs=8, dash=(st == 'pending'))
            s.chip(bx + 14, yy + 26, 80, 18, 'Disputed', fill=RED_BG, fs=9)
            s.r(bx + 14, yy + 52, 442, 40, 'PE-1: "Owners differ. Need the change-board reference before this can merge."', fill='#fff5f5', stroke=RED, fs=9, align='left', pad=8)
            s.btn(bx + 14, yy + 104, 110, 30, 'Uphold SE', fs=9)
            s.btn(bx + 130, yy + 104, 110, 30, 'Uphold PE', fs=9)
            s.btn(bx + 246, yy + 104, 190, 30, 'Send back with instructions', fs=9)
            para(s, bx + 14, yy + 144, 'Adjudicator sees both notes side by side. The losing view is kept on the record as dissent.', 440, 9, SOFT)
        if i == 4:
            s.chip(bx + 14, yy, 230, 20, 'SE signed revision R2 · text is now R3', fill=AMBER_BG, fs=9)
            s.t(bx + 14, yy + 30, 'Diff R2 to R3', fs=9, color=SOFT)
            s.r(bx + 14, yy + 46, 442, 44, fill='#ffffff', stroke=LINE)
            tokw(s, bx + 24, yy + 56, 420, 'The FCS shall transmit a heartbeat message every 2 seconds.', fs=10, differs=('2', 'seconds.'))
            s.btn(bx + 14, yy + 104, 190, 32, 'Re-confirm my sign-off', primary=True, fs=10)
            s.btn(bx + 212, yy + 104, 120, 32, 'Review diff', fs=10)
            para(s, bx + 14, yy + 148, 'Whitespace-only changes keep sign-offs. Any other change makes them stale.', 440, 9, SOFT)
        if i == 5:
            s.r(bx + 14, yy, 442, 62, fill='#efe7fb', stroke='#7048e8')
            para(s, bx + 24, yy + 8, 'REQ-FCS-0215 changed in the source on 10 Oct at 11:02. This decision was made on the earlier text, so it is marked stale.', 420, 10, '#2b1b66')
            s.btn(bx + 14, yy + 76, 130, 32, 'See what changed', fs=10)
            s.btn(bx + 152, yy + 76, 190, 32, 'Re-run this comparison', primary=True, fs=10)
            s.btn(bx + 350, yy + 76, 106, 32, 'Keep it', fs=10)
            para(s, bx + 14, yy + 122, '"Keep it" needs a reason and is logged. Re-running creates a new revision chain; the old one stays.', 440, 9, SOFT)
    d.frame_end()
    return ['Soft claims show who is working where. They are advice, not locks, and expire on their own.',
            'Every decision carries the version it was made on. If the version moved, the reviewer sees what changed before anything is saved.',
            'Edits never overwrite each other. Concurrent edits become sibling revisions and one is chosen on purpose.',
            'A "changes requested" sign-off blocks the cluster. Disputes go to an adjudicator, and the dissent is preserved.',
            'Sign-offs bind to a specific revision. Change the text and every affected sign-off becomes stale.',
            'Source drift is a first-class state. See board 09 for how refresh decides which decisions go stale.']


def s5_policy(d, ox, oy):
    W, H = 1500, 640
    s = new_frame(d, ox, oy, W, H, 'S5 · Sign-off policy and permissions', bg='#ffffff')
    s.t(20, 14, 'Who has to sign what, and who can do what', fs=24, family=1, color=INK)
    s.t(20, 50, 'Proposed defaults. Every cell is a project setting. "Binding versus advisory" per lens is open question 5.', fs=12, color=SOFT)
    s.caps(20, 84, 'SIGN-OFF POLICY MATRIX (replaces "four of four on everything")')
    Y_, N_, S_, O_ = ('Required', GREEN_BG), ('-', None), ('Sample 20%', AMBER_BG), ('If cross-owner', BLUE_BG)
    rows = [['Lane A, no new wording (alias, or keep an existing member)', Y_, S_, N_, N_, ('-', None)],
            ['Lane A, new or edited wording', Y_, Y_, Y_, Y_, ('-', None)],
            ['Lane B, no new wording (link, ask, reject)', Y_, Y_, N_, S_, O_],
            ['Lane B, new or edited wording', Y_, Y_, Y_, Y_, O_],
            ['Lane C, conflict (escalate)', Y_, Y_, N_, N_, ('Both owners; adjudicator if disputed', BLUE_BG)],
            ['Baselined requirement involved', Y_, ('Required + change-request reference', GREEN_BG), ('as above', None), ('as above', None), ('Change board, outside this tool', BLUE_BG)],
            ['Reviewers disagree', ('Adjudicator decides; dissent kept', AMBER_BG), ('', None), ('', None), ('', None), ('', None)]]
    y = table(s, 20, 106, [250, 90, 120, 80, 90, 150], ['Case', 'SE', 'PE', 'UX', 'NU', 'Others'], rows, fs=9, minh=34)
    para(s, 20, y + 10, 'Why: UX and NU lenses judge wording and comprehension. They matter when wording is new, so they sign then. SE and PE judge every change. At 250 clusters this takes about 600 sign-offs instead of 1,000 (see S6).', 780, 10, DARK)
    s.num(20 + 800, 96, 1)
    s.caps(840, 84, 'ROLES AND PERMISSIONS')
    rows2 = [['View clusters and requirements', 'Yes', 'Yes', 'Yes', 'Yes'], ['Comment and @mention', 'Yes', 'Yes', 'Yes', 'Yes'], ['Propose a resolution (decide)', 'Assigned', 'Yes', '-', '-'],
             ['Sign for a lens', 'Own lens', 'Own lens', '-', '-'], ['Request changes (block)', 'Own lens', 'Own lens', '-', '-'], ['Adjudicate disputes', '-', 'Yes', '-', '-'],
             ['Reassign clusters', '-', 'Yes', 'Yes', '-'], ['Change policy and thresholds', '-', '-', 'Yes', '-'], ['Prepare an export', '-', 'Yes', 'Yes', '-'],
             ['Reopen a decision', 'Own', 'Yes', 'Yes', '-'], ['View audit and verify the chain', 'Yes', 'Yes', 'Yes', 'Yes'], ['Preview as another lens', '-', 'Read only', 'Read only', '-']]
    y2 = table(s, 840, 106, [230, 90, 90, 90, 90], ['Action', 'Reviewer', 'Lead', 'Admin', 'Observer'], rows2, fs=9, minh=26)
    s.num(840 + 580, 96, 2)
    s.r(840, y2 + 16, 590, 110, fill='#fff9db', stroke='#f1c40f')
    s.t(854, y2 + 26, 'Identity and lenses', fs=12, family=1, color=INK)
    para(s, 854, y2 + 48, 'Users sign in through your own identity provider (for example GitLab as an OIDC provider). Lens assignments come from that identity, not a free switch, so nobody can sign as a lens they do not hold. Leads can "preview as" another lens, read only.', 560, 10, '#5c4400')
    s.num(840 + 580, y2 + 8, 3)
    d.frame_end()
    return ['Policy matrix: the required lenses depend on lane, whether wording changed, whether owners differ, and whether anything is baselined.',
            'Role matrix: four roles are enough. Reviewer, lead, admin and observer. "Sign for a lens" is the only permission tied to who you are.',
            'The prototype let anyone switch lens and sign. With real users, lens comes from identity and "preview as" is read only.']


def s6_numbers(d, ox, oy):
    W, H = 1500, 1070
    s = new_frame(d, ox, oy, W, H, 'S6 · Will it hold at 1,000 to 1,500? What we measured and what we assumed', bg='#ffffff')
    s.t(20, 14, 'Will it hold at 1,000 to 1,500 requirements?', fs=26, family=1, color=INK)
    s.t(20, 52, 'Short answer: the computing holds easily. Plain text similarity does not. Structure first, then similarity, fixes it. All figures below are from synthetic requirements, so they show behaviour, not accuracy.', fs=12, color=DARK)
    s.caps(20, 92, 'MEASURED: THE MECHANICAL FRONT HALF (2-CORE SANDBOX)')
    rows = [['214', '22,791', '1,000', '0.003 s', '0.004 s', '0.09 s'], ['1,000', '499,500', '21,010', '0.025 s', '0.12 s', '0.82 s'], ['1,500', '1,124,250', '48,177', '0.06 s', '0.19 s', '0.67 s'], ['5,000', '12,497,500', '525,410', '0.52 s', '1.96 s', '2.5 s']]
    y = table(s, 20, 114, [80, 110, 130, 110, 110, 110], ['Requirements', 'All pairs', 'Text candidates ≥ 0.35', 'All-pairs cosine', 'Fuzzy re-score', 'MinHash'], rows, fs=10, minh=28)
    para(s, 20, y + 8, 'Compute is not the constraint. The costly stages (cross-encoder, NLI, AI judge) only ever see a shortlist. The all-pairs matrix is dense, fine to a few thousand; beyond that use sparse top-k.', 650, 10, DARK)
    s.num(660, 104, 1)
    s.caps(740, 92, 'WHAT BREAKS: CHAINING (1,500 REQUIREMENTS, 10% IN PLANTED FAMILIES)')
    for i, (lab, v, note) in enumerate([('Single-link on text', 675, 'one blob holds 45% of the project'), ('Average-link on text', 39, 'largest cluster, but 265 clusters and only 6% pair precision'), ('Blocked by allocation, then average-link', 14, '342 clusters, 14 with 8 or more members, 28% pair precision, 97% of planted pairs kept as candidates')]):
        yy = 118 + i * 54
        s.t(740, yy, lab, fs=10, color=INK)
        bar_h(s, 740, yy + 18, 400 * v / 675, 1.0, fill=RED if i == 0 else ('#f08c00' if i == 1 else HUM), h=12)
        s.t(745 + 400 * v / 675, yy + 17, str(v), fs=10, color=INK, family=3)
        s.t(740 + 400 * v / 675 + 40, yy + 17, note, fs=9, color=SOFT)
    s.num(1440, 104, 2)
    s.caps(740, 292, 'CANDIDATE PAIRS GOING DOWNSTREAM (1,500 REQUIREMENTS)')
    bar_h(s, 740, 316, 400, 1.0, fill='#f08c00', h=12)
    s.t(1150, 314, '48,177  text similarity only (≥ 0.35)', fs=10, color=INK)
    bar_h(s, 740, 340, 400 * 3348 / 48177, 1.0, fill=HUM, h=12)
    s.t(740 + 400 * 3348 / 48177 + 10, 338, '3,348  blocked by allocation, text ≥ 0.50', fs=10, color=INK)
    para(s, 740, 366, 'Blocking keeps 97% of the planted pairs. The allocation is known exactly here, and real allocation fields are messier. The synthetic data is heavily templated ("The X shall…"), which is the worst case for text similarity and probably harsher than real data. Treat 28% pair precision as a floor to beat, not a forecast.', 700, 10, DARK)
    s.num(1440, 300, 3)
    # fixes
    s.r(20, 316, 700, 200, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 326, 'Five design changes this forces', fs=14, family=1, color=INK)
    for i, t_ in enumerate(['Block pairs by allocation, owner or extracted parameter before scoring text.', 'Average-link or similar. Never single-link, which chains.', 'Oversized guard: more than 12 members becomes an "oversized" state that must be split first.',
                            'Member-level review: peel one member out of a group instead of rejecting the whole group.', 'Pilot on one allocation (about 100 to 200 requirements) to replace every assumption below with a measurement.']):
        s.t(34, 354 + i * 30, str(i + 1) + '   ' + s.d.wrap(t_, 650, 11), fs=11, color=DARK)
    s.num(700, 308, 4)
    # effort
    s.caps(20, 540, 'ASSUMED: REVIEWER HOURS (NOT MEASURED)')
    rows = [['50', '5.5 h · 200', '4.2 h · 119'], ['150', '16.5 h · 600', '12.4 h · 357'], ['250', '27.5 h · 1,000', '20.8 h · 595'], ['350', '38.5 h · 1,400', '29.1 h · 833']]
    y = table(s, 20, 562, [110, 220, 220], ['Clusters', 'Four lenses on every cluster', 'Policy matrix (S5)'], rows, fs=10, minh=28)
    para(s, 20, y + 8, 'Hours · sign-offs. SE time per cluster: lane A 1.5 min, B 4, C 8, with a 40/45/15 mix. Each other sign-off 1 min. Matrix: PE on B, C and 20% of A; UX and NU on the 35% of clusters with new wording. 1,487 requirements likely yield 50 to 350 clusters: 50 is the prototype ratio, 350 the synthetic worst case.', 560, 9, SOFT)
    s.num(560, 554, 5)
    s.caps(840, 540, 'SAMPLING A LANE: CHECK THIS MANY, FIND ZERO DEFECTS, BE 95% SURE')
    rows = [['40', '38 of 40', '25 of 40', '18 of 40'], ['100', '63 of 100', '39 of 100', '23 of 100'], ['200', '90 of 200', '47 of 200', '26 of 200']]
    y2 = table(s, 840, 562, [140, 160, 160, 160], ['Lane A clusters', '≤ 2% defective', '≤ 5% defective', '≤ 10% defective'], rows, fs=10, minh=28)
    para(s, 840, y2 + 8, 'Hypergeometric, no replacement. With about 100 lane A clusters you still check 39 to rule out 5%. Sampling pays off only on large lanes, so: review every lane A cluster (1.5 min each, keyboard) and use sampling for PE, UX and NU audits instead.', 620, 10, DARK)
    s.num(1440, 554, 6)
    s.caps(20, 800, 'RISKS THE SCALE TEST DID NOT COVER')
    for i, t_ in enumerate(['Real requirements are less templated than the synthetic set, so text similarity may do better. It may also do worse where paraphrase and unit conversion are heavy.', 'Embeddings, cross-encoder and NLI were not run here (no models offline). Their cost is a function of shortlist size: at about 3,000 to 5,000 pairs it is minutes on a GPU and tens of minutes on CPU (order of magnitude, unverified).',
                            'AI judge cost scales with the uncertain band. Cap it per run and cache results by content hash so a re-run only pays for changed requirements.', 'Reviewer fatigue is real: 20 hours of review is not one sitting. Packets and resumable sessions (S1) matter more than raw speed.']):
        para(s, 20, 826 + i * 42, '•  ' + t_, 1400, 11, DARK)
    d.frame_end()
    return ['Measured, not assumed: the mechanical compute and the chaining failure. Assumed, not measured: all reviewer-time figures. Both are labelled.',
            'Chaining is the real scale problem. One blob of 675 requirements is unreviewable. Blocking plus average-link brings the largest cluster to 14.',
            'Blocking cuts the downstream workload by about 14x while keeping 97% of the planted pairs.',
            'These five changes are now in the design: blocking, average-link, an oversized state, member-level review, and a pilot.',
            'Reviewer-hours range from about 4 to 29 across the plausible cluster counts. The policy matrix saves roughly a quarter of the hours and 40% of sign-offs.',
            'Sampling math: review all of lane A; use sampling for secondary lens audits.']
