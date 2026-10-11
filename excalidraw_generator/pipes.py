"""Board 09: more pipelines."""
from wf2 import *
from g7 import numline

KIND = {'src': SRC_F, 'mech': MECH_F, 'ai': AI_F, 'hum': HUM_F, 'gov': '#fff3bf', 'chat': CHAT_F}
KST = {'src': INK, 'mech': MECH, 'ai': AIC, 'hum': HUM, 'gov': '#b35a00', 'chat': CHAT}


def pbox(s, x, y, w, h, label, kind, num=None, new=False, changed=False, fs=9):
    st = KST[kind]
    if new:
        s.r(x - 3, y - 3, w + 6, h + 6, fill=None, stroke=RED, sw=2, dash=True)
    elif changed:
        s.r(x - 3, y - 3, w + 6, h + 6, fill=None, stroke='#f08c00', sw=2)
    s.r(x, y, w, h, fill=KIND[kind], stroke=st, sw=2)
    s.t(x + 8, y + 7, s.d.wrap(label, w - 16, fs), fs=fs, color=INK)
    if num is not None:
        s.shape('ellipse', x - 8, y - 8, 18, 18, str(num), fs=8, fill='#ffffff', stroke=st, pad=0)
    if new:
        s.chip(x + w - 34, y - 12, 34, 14, 'NEW', fill=RED, stroke=RED, color='#ffffff', fs=8)
    elif changed:
        s.chip(x + w - 56, y - 12, 56, 14, 'CHANGED', fill='#f08c00', stroke='#f08c00', color='#ffffff', fs=8)


def p1_map(d, ox, oy):
    W, H = 1500, 960
    s = new_frame(d, ox, oy, W, H, 'P1 · The whole pipeline, with the new parts marked', bg='#ffffff')
    s.t(20, 14, 'The pipeline now, end to end', fs=24, family=1, color=INK)
    s.t(20, 50, 'Red dashed outline = new since board 03. Orange = changed. Numbers are the order a requirement travels. Dashed coloured lines are feedback loops.', fs=12, color=SOFT)
    lanes = [('Source and prep', SRC_F), ('Mechanical', MECH_F), ('AI', AI_F), ('People', HUM_F), ('Governance and outputs', '#fff3bf')]
    ly0, lh = 84, 112
    for i, (nm, f) in enumerate(lanes):
        s.r(20, ly0 + i * lh, 1460, lh - 8, fill=f, stroke='#ced4da', rounded=False, sw=1)
        s.r(20, ly0 + i * lh, 120, lh - 8, nm, fill='#ffffff', stroke='#ced4da', rounded=False, sw=1, fs=11, family=1)
    X = lambda c: 168 + c * 132
    Y = lambda l: ly0 + l * lh + 26
    bw, bh = 118, 64
    boxes = {1: (0, 0, 'Ingest: API, ReqIF, XMI, CSV', 'src', {}), 2: (0, 1, 'Normalise and extract parameters', 'mech', {}), 3: (0, 2, 'Quality lint (EARS, INCOSE rules)', 'mech', {'new': 1}),
             21: (0, 3, 'Parameter ledger and unit normalise', 'mech', {'new': 1}),
             4: (1, 2, 'Block by allocation, owner, parameter', 'mech', {'new': 1}), 5: (1, 3, 'Score ladder: lexical, fuzzy, embedding, cross-encoder, NLI', 'mech', {}), 6: (1, 4, 'Calibrated stacker', 'mech', {}),
             7: (1, 5, 'Cluster (average-link) and split oversized', 'mech', {'changed': 1}), 8: (1, 6, 'Relationship labels and ten guards', 'mech', {}),
             9: (2, 6, 'AI judge: uncertain band only, cached by content hash', 'ai', {}), 10: (2, 7, 'Draft wording and AI record', 'ai', {}), 20: (2, 9, 'Assistant: read-only, proposes only', 'chat', {'new': 1}),
             11: (3, 7, 'Assign and claim by lens', 'hum', {'new': 1}), 12: (3, 8, 'Lens review. SE resolves, others sign', 'hum', {'changed': 1}), 14: (3, 9, 'Adjudicate disagreements', 'hum', {'new': 1}),
             15: (4, 7, 'Revision chain and decision ledger', 'gov', {'new': 1}), 16: (4, 8, 'Hash-chained audit', 'gov', {}), 17: (4, 9, 'Export, write-back as a branch', 'gov', {'changed': 1}),
             19: (4, 4, 'Gold set and calibration', 'gov', {'new': 1}), 18: (0, 8, 'Refresh and drift: re-import and re-check', 'src', {'new': 1})}
    pos = {}
    for k, (l, c, lab, kind, fl) in boxes.items():
        pos[k] = (X(c), Y(l))
        pbox(s, X(c), Y(l), bw, bh, lab, kind, num=k if k < 18 else None, new=fl.get('new', 0), changed=fl.get('changed', 0))
    R = lambda k: (pos[k][0] + bw, pos[k][1] + bh / 2)
    L = lambda k: (pos[k][0], pos[k][1] + bh / 2)
    T = lambda k: (pos[k][0] + bw / 2, pos[k][1])
    B = lambda k: (pos[k][0] + bw / 2, pos[k][1] + bh)
    def arr(pts, **kw):
        s.poly(pts, **kw)
    arr([R(1), L(2)], stroke=INK, sw=2); arr([R(2), L(3)], stroke=INK, sw=2)
    arr([B(2), (B(2)[0], B(2)[1] + 4), (B(2)[0], Y(1) + bh / 2), L(4)], stroke=INK, sw=2)
    arr([R(4), L(5)], stroke=INK, sw=2); arr([R(5), L(6)], stroke=INK, sw=2); arr([R(6), L(7)], stroke=INK, sw=2); arr([R(7), L(8)], stroke=INK, sw=2)
    arr([B(8), T(9)], stroke=INK, sw=2); arr([R(9), L(10)], stroke=INK, sw=2)
    mid = (R(8)[0] + 8, R(8)[1])
    arr([R(8), (R(8)[0] + 8, R(8)[1]), (R(8)[0] + 8, L(11)[1]), L(11)], stroke=INK, sw=2)
    arr([R(10), (T(12)[0] - 20, R(10)[1]), (T(12)[0] - 20, T(12)[1])], stroke=INK, sw=2)
    arr([R(11), L(12)], stroke=INK, sw=2)
    arr([R(12), L(14)], stroke=INK, sw=2)
    arr([B(12), (B(12)[0], T(16)[1] - 18), (B(15)[0] + 30, T(16)[1] - 18), (B(15)[0] + 30, T(15)[1])], stroke=INK, sw=2)
    arr([R(15), L(16)], stroke=INK, sw=2); arr([R(16), L(17)], stroke=INK, sw=2)
    # loops
    arr([L(15), R(19)], stroke='#b35a00', sw=2, dash=True)
    arr([T(19), (T(19)[0], B(6)[1])], stroke='#b35a00', sw=2, dash=True)
    s.t(T(19)[0] + 6, B(6)[1] + 70, 'thresholds\nretuned', fs=8, color='#b35a00')
    arr([T(18), (T(18)[0], ly0 + 6), (X(0) + bw / 2, ly0 + 6), T(1)], stroke='#7048e8', sw=2, dash=True)
    s.t(X(4) + 10, Y(0) + 18, 'new export or API poll:\nonly changed requirements are re-checked', fs=9, color='#7048e8')
    arr([B(20), (B(20)[0], T(12)[1] - 22), (T(12)[0] + 24, T(12)[1] - 22), (T(12)[0] + 24, T(12)[1])], stroke=CHAT, sw=2, dash=True)
    s.num(1456, ly0 - 6, 1)
    # what's new table
    ty = ly0 + 5 * lh + 24
    s.t(20, ty, 'What each new piece does', fs=14, family=1, color=INK)
    rows = [['3 · 21', 'Lint and parameter ledger', 'Rule checks on every wording, and a table of subject, parameter, value and unit. Gives a second look when text similarity finds nothing.', 'P5'],
            ['4 · 7', 'Blocking and oversized split', 'Compare only inside an allocation, owner or parameter, so groups stay small enough to review.', 'S6'],
            ['11 · 14', 'Assign, claim, adjudicate', 'Many reviewers, one cluster at a time, with a lead deciding disputes.', 'S3, S4'],
            ['15', 'Revision chain and ledger', 'Notes, reasons, AI records and every edit, kept apart and searchable.', 'G3 to G5'],
            ['18', 'Refresh and drift', 'The source keeps moving. Only affected decisions go stale.', 'P2'],
            ['19', 'Gold set and calibration', 'Turns reviewer decisions into measured thresholds and tracks drift.', 'P3'],
            ['17', 'Write-back as a branch', 'Approved decisions leave as ReqIF, a SysML v2 branch, documents and a change report.', 'P4'],
            ['20', 'Assistant', 'A read-only helper with a memory of the ledger.', 'A1 to A4']]
    table(s, 20, ty + 26, [80, 220, 1010, 120], ['Step', 'New piece', 'What it does', 'Board'], rows, fs=9, minh=24, bold_first=True)
    d.frame_end()
    return ['Five lanes keep the earlier idea: mechanical first, AI near the end, people decide, governance records it. The new parts sit inside those lanes.',
            'Feedback loops are drawn dashed. Refresh (purple) goes back to ingest. Calibration (orange) goes back to the stacker and thresholds. The assistant (blue) reads from the review step.',
            'The table is the checklist of what must be built that was not in the first design.']


def p2_refresh(d, ox, oy):
    W, H = 1500, 780
    s = new_frame(d, ox, oy, W, H, 'P2 · Refresh and drift: the source moves, the decisions must notice', bg='#ffffff')
    s.t(20, 14, 'When the project changes under you', fs=24, family=1, color=INK)
    s.t(20, 50, 'The projects are online and keep changing. A decision is only as good as the text it was made on, so each one remembers that text.', fs=12, color=SOFT)
    steps = [('1 Take a snapshot', 'Each import is an immutable snapshot, like a commit.', 'src'), ('2 Match requirements', 'By stable source ID first, then text hash, then fuzzy. Ambiguous matches go to a person.', 'mech'),
             ('3 Classify the change', 'Unchanged, changed, added, removed, renamed.', 'mech'), ('4 Find what it touches', 'Clusters, revisions and sign-offs that used a changed text.', 'mech'),
             ('5 Mark and re-check', 'Mark stale. Re-run only affected blocks. Re-ask the AI only for changed content hashes.', 'ai'), ('6 Tell people', 'Stale tab, digest, and a diff of what changed.', 'hum'),
             ('7 Reviewer chooses', 'Re-confirm, re-run, or reopen. Each needs a reason.', 'hum')]
    for i, (t_, sub, k) in enumerate(steps):
        x = 20 + i * 208
        s.r(x, 86, 190, 112, fill=KIND[k], stroke=KST[k], sw=2)
        s.t(x + 10, 94, t_, fs=11, color=INK)
        s.t(x + 10, 116, s.d.wrap(sub, 170, 9), fs=9, color=DARK)
        if i < 6:
            s.poly([(x + 190, 146), (x + 208, 146)], stroke=INK, sw=2)
    s.num(1440, 78, 1)
    # example
    s.card(20, 232, 700, 292)
    s.caps(34, 244, 'EXAMPLE: IMPORT 2 AGAINST IMPORT 1 (SAMPLE NUMBERS)')
    rows = [['Requirements', '1,487', '1,502'], ['Unchanged', '', '1,449'], ['Text changed', '', '31'], ['Added', '', '14'], ['Removed', '', '3'], ['Clusters touched', '', '11'], ['Sign-offs now stale', '', '19'], ['Decisions deleted', '', '0']]
    table(s, 34, 268, [260, 130, 130], ['', 'Import 1', 'Import 2'], rows, fs=10, minh=24)
    s.num(706, 224, 2)
    s.card(740, 232, 740, 292)
    s.caps(754, 244, 'WHAT HAPPENS TO EACH KIND OF CHANGE')
    rows = [['Text of a member changed', 'Decision and sign-offs go stale. The old text stays in history. Re-run or re-confirm.'],
            ['Member removed at source', 'The decision is flagged "orphaned". A person decides whether the group still stands.'],
            ['New requirement similar to a group', 'Offered as a new member candidate. Never added automatically.'],
            ['ID renamed or moved', 'Matched by text hash. Ambiguous cases go to a "who is who" queue.'],
            ['Nothing relevant changed', 'Nothing happens. No reviewer is asked to look again.']]
    table(s, 754, 268, [230, 480], ['Change', 'What the tool does'], rows, fs=9, minh=36, bold_first=True)
    s.num(1466, 224, 3)
    # rules
    s.r(20, 548, 1460, 190, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 558, 'Rules that keep this safe', fs=14, family=1, color=INK)
    for i, t_ in enumerate(['A refresh never deletes a decision, a note or a revision. It only changes state.', 'Re-running costs money and time, so it is incremental: unchanged content hashes reuse earlier AI answers.',
                            'A "keep it" on a stale decision needs a reason and is logged. The decision then points at the new source text.', 'Baselines are frozen. A refresh never touches an exported baseline snapshot, so a past export can always be reproduced.',
                            'The comparison view can diff any two snapshots, so a program can say what changed between two reviews.']):
        s.t(34, 588 + i * 28, '•  ' + t_, fs=10, color='#5c4400')
    s.num(1466, 540, 4)
    d.frame_end()
    return ['Seven steps, mostly mechanical. The AI is used only on changed content, and people are asked only about decisions the change actually touches.',
            'Sample numbers, to show the shape of the report a lead sees after a refresh.',
            'Each kind of change has a defined result. Orphaned and ambiguous cases always go to a person.',
            'These rules are what lets a team trust a long-running review on a source that never stops changing.']


def p3_calibration(d, ox, oy):
    W, H = 1500, 800
    s = new_frame(d, ox, oy, W, H, 'P3 · The gold set and the calibration loop', bg='#ffffff')
    s.t(20, 14, 'How the thresholds earn their numbers', fs=24, family=1, color=INK)
    s.t(20, 50, 'No score is trusted until it is measured against human decisions. Reviewer decisions feed a gold set, and the gold set sets the thresholds.', fs=12, color=SOFT)
    ring = [(60, 110, 'Reviewer decisions and overrides', 'hum'), (400, 110, 'Gold set: labelled pairs, versioned', 'gov'), (740, 110, 'Refit stacker and thresholds, offline', 'mech'),
            (740, 300, 'Evaluate on held-out allocations', 'mech'), (400, 300, 'Approve and publish a versioned config', 'hum'), (60, 300, 'Monitor override rate and drift each week', 'gov')]
    for i, (x, y, t_, k) in enumerate(ring):
        pbox(s, x, y, 260, 90, t_, k, num=i + 1, fs=11)
    s.poly([(320, 155), (400, 155)], stroke=INK, sw=2); s.poly([(660, 155), (740, 155)], stroke=INK, sw=2)
    s.poly([(870, 200), (870, 300)], stroke=INK, sw=2); s.poly([(740, 345), (660, 345)], stroke=INK, sw=2)
    s.poly([(400, 345), (320, 345)], stroke=INK, sw=2); s.poly([(190, 300), (190, 200)], stroke=INK, sw=2)
    s.t(204, 240, 'loop closes: new decisions\nbecome new labels', fs=9, color=SOFT)
    s.num(1010, 102, 1)
    s.r(1050, 100, 430, 310, fill='#ffffff', stroke=INK, sw=2)
    s.t(1064, 110, 'The monthly calibration report (empty template)', fs=12, family=1, color=INK)
    rows = [['Pairs in the gold set', '–', '–', '–'], ['Precision of "equivalent" at the lane A threshold', '–', '–', '–'], ['Recall of true duplicates in the candidates', '–', '–', '–'], ['Human override rate', '–', '–', '–'], ['AI judge agrees with human', '–', '–', '–'], ['Calibration error', '–', '–', '–']]
    table(s, 1064, 140, [200, 70, 70, 70], ['Metric', 'Lane A', 'Lane B', 'Lane C'], rows, fs=9, minh=32)
    s.t(1064, 380, 'Filled from your own gold set. No figures are shown here because none exist yet.', fs=9, color=SOFT)
    s.num(1466, 92, 2)
    s.r(20, 440, 1460, 330, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 450, 'What makes a gold set trustworthy', fs=14, family=1, color=INK)
    rules = ['Stratified: it holds easy and hard pairs from every allocation, relationship type and lane, not just the pairs reviewers happened to see first.',
             'Split by allocation, not by pair. If the same allocation is in training and testing, the scores look better than they are.',
             'Two people label a sample (10 to 20%). Their agreement (for example Cohen\'s kappa) is the ceiling the tool can be expected to reach.',
             'A reviewer who overrides the AI and gives a reason produces a labelled example. Those are the most valuable rows.',
             'Thresholds are versioned configuration with a change log. Changing one needs a lead and an admin, and a re-run on the gold set first.',
             'The weekly monitor looks at the human override rate. A sudden rise means the data, the model or the source changed.',
             'Seeded checks (known-answer clusters mixed in) are optional and off by default. They are for training and tool quality, not for scoring people.']
    for i, t_ in enumerate(rules):
        s.shape('ellipse', 34, 484 + i * 38, 18, 18, str(i + 1), fs=9, fill='#ffffff', stroke='#b35a00', pad=0)
        s.t(60, 485 + i * 38, s.d.wrap(t_, 1380, 11), fs=11, color='#3b2f00')
    s.num(1466, 432, 3)
    d.frame_end()
    return ['The loop. Every decision made in review can become a label, so the tool improves from use rather than from a one-off tuning exercise.',
            'The report is a template. It stays empty until a gold set exists, which is the honest state of the design today.',
            'Seven rules for the gold set. The split-by-allocation rule is the one most often missed and the one that flatters the numbers most.']


def p4_writeback(d, ox, oy):
    W, H = 1500, 710
    s = new_frame(d, ox, oy, W, H, 'P4 · How decisions leave the tool: write-back and downstream', bg='#ffffff')
    s.t(20, 14, 'Nothing goes to the source model without a branch and a human merge', fs=24, family=1, color=INK)
    s.t(20, 50, 'The tool never edits your model in place. Approved decisions leave as packages, and the model changes only through a branch you review.', fs=12, color=SOFT)
    pbox(s, 20, 110, 200, 90, 'Approved decisions only. No stale, no pending sign-offs.', 'hum', fs=11)
    pbox(s, 280, 110, 220, 90, 'Pre-export checks: hash chain valid, policy met, no oversized clusters', 'gov', fs=11)
    pbox(s, 560, 110, 200, 90, 'Package builder (a dry run first, with a diff)', 'mech', fs=11)
    s.poly([(220, 155), (280, 155)], stroke=INK, sw=2); s.poly([(500, 155), (560, 155)], stroke=INK, sw=2)
    outs = [('ReqIF', 'A .reqif file with duplicate-of and supersedes relations. The documented route back into MSOSA.', SRC_F), ('SysML v2 branch', 'A commit on a branch through the SysML v2 API, if your version exposes it. To be verified against the real tool.', SRC_F),
            ('Documents', 'DOCX or Markdown from templates: requirement IDs, status, trace table and a provenance label per requirement.', HUM_F), ('Change report', 'What changed, who decided, how much came from AI, and what is still open. For the review board.', '#fff3bf'),
            ('Data package', 'JSON and CSV with every revision and record. For other tools and for backup.', MECH_F)]
    for i, (t_, sub, f) in enumerate(outs):
        x = 20 + i * 292
        s.r(x, 270, 276, 130, fill=f, stroke=INK, sw=2)
        s.t(x + 12, 280, t_, fs=13, family=1, color=INK)
        s.t(x + 12, 308, s.d.wrap(sub, 252, 10), fs=10, color=DARK)
        s.poly([(660, 200), (660, 236), (x + 138, 236), (x + 138, 270)], stroke=INK, sw=1.5)
    s.num(1440, 262, 1)
    s.r(20, 430, 700, 250, fill='#e3f4fb', stroke=CHAT)
    s.t(34, 440, 'The branch and merge-request path (GitLab CI)', fs=13, family=1, color=INK)
    for i, t_ in enumerate(['The package builder commits to a branch, never to main or a baseline.', 'A CI job validates the package: schema, hash chain, policy, and a round trip (re-import the export and compare).',
                            'A merge request opens with the change report attached. A named human approves it.', 'Only after the merge does the source model change. The tool then takes a new snapshot (P2).']):
        s.t(34, 474 + i * 44, str(i + 1) + '  ' + s.d.wrap(t_, 660, 11), fs=11, color=DARK)
    s.num(706, 422, 2)
    s.r(740, 430, 740, 250, fill='#fff9db', stroke='#f1c40f')
    s.t(754, 440, 'Open questions to settle with the real tool', fs=13, family=1, color=INK)
    for i, t_ in enumerate(['Which MSOSA release and SysML v2 API version you run. Write support differs and must be tested on a copy.', 'Whether ReqIF import in your MSOSA setup keeps relations and IDs.', 'Who owns the merge: the program SE lead, or the model owner.', 'How baselined requirements are changed: through your change board, outside this tool. The package only lists them.']):
        s.t(754, 474 + i * 44, '•  ' + s.d.wrap(t_, 700, 11), fs=11, color='#5c4400')
    s.num(1466, 422, 3)
    d.frame_end()
    return ['Five outputs from one checked package. Documents are one of five, which is the downstream the original request named.',
            'The branch path uses your existing GitLab habits. The tool proposes and a person merges.',
            'These are the things only your real environment can answer, so they are questions, not assumptions.']


def p5_lint(d, ox, oy):
    W, H = 1500, 820
    s = new_frame(d, ox, oy, W, H, 'P5 · Quality lint and the parameter ledger', bg='#ffffff')
    s.t(20, 14, 'Two cheap checks that find what text similarity misses', fs=24, family=1, color=INK)
    s.t(20, 50, 'Lint judges one requirement at a time. The ledger lines requirements up by what they say about, not by how they are worded.', fs=12, color=SOFT)
    s.caps(20, 84, 'QUALITY LINT (EXAMPLES; PROJECT RULES ARE EDITABLE)')
    rows = [['One requirement, one idea', 'The recorder shall store and transmit faults.', 'The recorder shall store faults.', 'PE, UX'], ['No vague words', 'The system shall respond quickly.', 'The system shall respond within 2 seconds.', 'SE, UX'],
            ['Measurable', 'The display shall be readable.', 'The display shall show 12 point text at 0.7 m.', 'SE, NU'], ['No escape clauses', 'Where practicable, log faults. TBD.', 'The recorder shall log each fault.', 'PE'],
            ['Clear reference', 'It shall send them to the unit.', 'The subsystem shall send heartbeats to the Mission Computer.', 'NU'], ['A recognised pattern', 'Heartbeats are sent.', 'When armed, the subsystem shall send a heartbeat every 1 second.', 'UX, NU']]
    table(s, 20, 106, [160, 250, 270, 70], ['Rule', 'Fails', 'Passes', 'Lens'], rows, fs=9, minh=40, bold_first=True)
    s.num(760, 96, 1)
    s.t(20, 420, s.d.wrap('Lint warnings appear in the PE and UX lens panels and on the New user reading. They advise. They never block a merge, only guards do.', 740, 10), fs=10, color=DARK)
    s.caps(800, 84, 'PARAMETER LEDGER (SAMPLE ROWS)')
    rows = [['FCS', 'heartbeat interval', '1', 's', '=', 'FCS-0212'], ['FCS', 'heartbeat interval', '1', 's (from 1 Hz)', '=', 'FCS-0218'], ['FCS', 'heartbeat interval', ('10', RED_BG), 's', '=', ('GND-0047', RED_BG)],
            ['Data Recorder', 'fault event retention', '30', 'd', '≥', 'SYS-0140'], ['Data Recorder', 'fault event retention', '365', 'd (from 1 year)', '≥', 'SYS-0147']]
    y = table(s, 800, 106, [100, 160, 50, 120, 40, 120], ['Subject', 'Parameter', 'Value', 'Unit', 'Cmp', 'Requirement'], rows, fs=9, minh=30)
    s.chip(800, y + 10, 330, 18, 'Same subject and parameter, different value: possible conflict', fill=RED_BG, fs=9)
    s.t(800, y + 34, 'Found without any text similarity, and the texts need not look alike.', fs=9, color=SOFT)
    s.chip(800, y + 60, 330, 18, 'Same direction and unit: can be ranked (board 07)', fill=GREEN_BG, fs=9)
    s.num(1396, 96, 2)
    s.r(20, 470, 1460, 320, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 480, 'What the ledger is used for', fs=14, family=1, color=INK)
    uses = [('A second look when nothing matched', 'S2 says "No match found is not proof". Search by parameter finds requirements that say the same thing in different words.'),
            ('A conflict detector', 'Same subject and parameter, different value or unit. Feeds lane C and the SE checklist, with no model call.'),
            ('Rankable groups', 'It is what makes "most stringent" and "least stringent" possible, because it knows the value, the unit and the direction.'),
            ('Coverage and orphans', 'Requirements with no parent trace or no verification method, listed for the PE lens.'),
            ('A terms index', 'Acronyms and terms with counts, so the UX and New user lenses can see which words need a gloss.')]
    for i, (t_, sub) in enumerate(uses):
        s.shape('ellipse', 34, 514 + i * 52, 18, 18, str(i + 1), fs=9, fill='#ffffff', stroke='#b35a00', pad=0)
        s.t(62, 513 + i * 52, t_, fs=12, color=INK)
        s.t(62, 531 + i * 52, s.d.wrap(sub, 1360, 10), fs=10, color='#5c4400')
    s.num(1466, 462, 3)
    d.frame_end()
    return ['Lint is the cheapest quality gate and the one engineers already know from INCOSE and EARS. It runs on every revision, including human and AI edits.',
            'The ledger is a table of facts pulled from the text. It is mechanical, so it is cheap, repeatable and checkable, and it needs no model call.',
            'Five uses, from conflict detection to the terms index. Most of them answer a question one of the lenses already asks.']
