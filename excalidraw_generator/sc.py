"""Board 05: scale and multi-user."""
from wf2 import *


# ---------------------------------------------------------------- S1 queue at scale
def s1_queue(d, ox, oy):
    W, H = 1000, 1090
    s = new_frame(d, ox, oy, W, H, 'S1 · Review queue at 1,487 requirements (252 clusters)')
    cx, cy = shell2(s, W, H, 'Review queue')
    s.h1(cx, cy, 'Review queue', fs=22)
    s.chip(cx + 560, cy + 4, 256, 18, 'Project: 1,487 requirements · 252 clusters', fs=9)
    # stacked progress
    y = cy + 34
    segs = [('Approved 38', 38, GREEN_BG), ('In review 23', 23, ACC_BG), ('Stale 3', 3, AMBER_BG), ('Disputed 4', 4, RED_BG), ('Suggested 184', 184, '#ffffff')]
    x = cx
    for lab, n, f in segs:
        w = 816 * n / 252
        s.r(x, y, w, 16, fill=f, stroke=LINE, rounded=False, dash=(lab.startswith('Suggested')))
        x += w
    s.t(cx, y + 22, 'Approved 38   ·   In review 23   ·   Stale 3   ·   Disputed 4   ·   Suggested 184      Lane A 98 · Lane B 112 · Lane C 42', fs=9, color=DARK)
    s.num(cx + 800, y - 8, 1)
    # tabs
    ty = cy + 78
    tabs = [('My queue (31)', True), ('Needs my lens (58)', False), ('Waiting on others (12)', False), ('Disagreements (4)', False), ('Stale (3)', False), ('All (252)', False)]
    x = cx
    for lab, on in tabs:
        w = len(lab) * 6.0 + 24
        s.r(x, ty, w, 28, lab, fill='#F1F6FF' if on else '#ffffff', stroke=ACC if on else LINE, sw=2 if on else 1, fs=9, color=INK)
        x += w + 6
    s.num(cx + 800, ty - 8, 2)
    # facets
    fy = ty + 42
    s.r(cx, fy, 190, 800, fill='#ffffff', stroke=LINE)
    s.caps(cx + 12, fy + 10, 'FILTERS')
    s.t(cx + 130, fy + 9, 'Clear all', fs=9, color=ACC)
    yy = fy + 32
    sections = [('LANE', [('Lane A · low risk', 98, True), ('Lane B · evidence', 112, True), ('Lane C · conflict', 42, True)]),
                ('RELATIONSHIP', [('Equivalent', 71, False), ('Variant', 96, False), ('Subsumes', 33, False), ('Conflict', 42, False), ('Complementary', 10, False)]),
                ('STATUS', [('Suggested', 184, True), ('In review', 23, False), ('Approved', 38, False), ('Stale', 3, False), ('Disputed', 4, False)]),
                ('ALLOCATION', [('Flight Control', 41, False), ('Data Recorder', 29, False), ('Ground Station', 27, False), ('Power Distribution', 22, False), ('+ 26 more, search', 0, False)]),
                ('ASSIGNED TO', [('Me', 31, True), ('Unassigned', 54, False), ('Others', 167, False)]),
                ('CLUSTER SIZE', [('2 members', 148, False), ('3 to 5', 78, False), ('6 to 12', 22, False), ('13+ (oversized)', 4, False)]),
                ('GUARDS', [('Any guard blocks', 29, False), ('Warnings only', 37, False)])]
    for title, items in sections:
        s.caps(cx + 12, yy, title)
        yy += 16
        for lab, n, on in items:
            checkbox(s, cx + 14, yy, on, lab, fs=9)
            if n:
                s.t(cx + 150, yy, str(n), fs=9, color=SOFT, family=3)
            yy += 19
        yy += 8
    s.num(cx - 24, fy + 10, 3)
    # list
    lx = cx + 206
    s.r(lx, fy, 610, 34, fill='#ffffff', stroke=LINE)
    s.r(lx + 10, fy + 6, 240, 22, 'Search ID, text or parameter', fill=GREY, stroke=LINE, fs=9, align='left', pad=8, color=SOFT)
    s.r(lx + 262, fy + 6, 130, 22, 'Sort: safest first', fill='#ffffff', stroke=SOFT, fs=9)
    s.r(lx + 400, fy + 6, 90, 22, 'Compact', fill='#ffffff', stroke=SOFT, fs=9)
    s.btn(lx + 500, fy + 4, 102, 26, 'Start packet', primary=True, fs=9)
    s.num(lx + 590, fy - 8, 4)
    # bulk bar
    by = fy + 42
    s.r(lx, by, 610, 32, fill='#F1F6FF', stroke=ACC, sw=2)
    s.t(lx + 12, by + 9, '3 selected', fs=10, color=INK)
    s.btn(lx + 100, by + 3, 120, 26, 'Review as stack', fs=9)
    s.btn(lx + 228, by + 3, 90, 26, 'Assign to…', fs=9)
    s.r(lx + 326, by + 3, 270, 26, 'Accept all: off for this project (decisions stay one at a time)', fill='#ffffff', stroke=SOFT, dash=True, fs=8, color=SOFT)
    s.num(lx + 590, by - 8, 5)
    rows = [('CL-041', 'A', 'Fault record retention, 30 days', 'Equivalent', 'x2', 'Data Recorder', 'Suggested', ['pending', 'pending', 'na', 'na'], 'SE'),
            ('CL-042', 'A', 'Health message timing, two wordings', 'Equivalent', 'x3', 'Flight Control', 'In review', ['signed', 'pending', 'na', 'na'], 'SE'),
            ('CL-043', 'A', 'Time sync interval 1 Hz', 'Equivalent', 'x2', 'Time Reference', 'Suggested', ['pending', 'pending', 'na', 'na'], 'SE'),
            ('CL-044', 'B', 'Heartbeat rate: 1 s or 10 s?', 'Variant', 'x2', 'Flight Control', 'Suggested', ['pending'] * 4, 'SE'),
            ('CL-045', 'B', 'Log fault codes: with timestamp?', 'Subsumes', 'x2', 'Data Recorder', 'In review', ['signed', 'signed', 'pending', 'pending'], 'PE'),
            ('CL-046', 'B', 'Alert annunciation time, 5 variants', 'Variant', 'x5', 'Cockpit Display', 'Suggested', ['pending'] * 4, 'SE'),
            ('CL-047', 'B', 'Display refresh: shall or should?', 'Variant', 'x2', 'Cockpit Display', 'Stale', ['stale', 'pending', 'pending', 'pending'], 'SE'),
            ('CL-048', 'C', 'Bus voltage: 28 VDC or 270 VDC?', 'Conflict', 'x2', 'Power Distribution', 'Disputed', ['signed', 'changes', 'na', 'na'], 'PE'),
            ('CL-049', 'C', 'Telemetry encryption: on or off?', 'Conflict', 'x2', 'Comms', 'Suggested', ['pending'] * 4, 'SE'),
            ('CL-050', 'B', 'Data retention: 6 wordings', 'Variant', 'x6', 'Data Recorder', 'Suggested', ['pending'] * 4, 'SE')]
    ry = by + 42
    s.num(lx - 24, ry + 4, 6)
    for i, (cid, ln, t_, rel, n, alloc, st, signs, who) in enumerate(rows):
        yy = ry + i * 58
        sel = i in (0, 2, 3)
        s.r(lx, yy, 610, 54, fill='#F1F6FF' if i == 3 else '#ffffff', stroke=ACC if i == 3 else LINE, sw=2 if i == 3 else 1)
        checkbox(s, lx + 10, yy + 12, sel)
        s.t(lx + 32, yy + 10, cid, fs=9, family=3, color=INK)
        s.chip(lx + 86, yy + 8, 48, 14, 'Lane ' + ln, fill=LANE_FILL[ln], fs=8)
        s.t(lx + 142, yy + 9, t_, fs=10, color=INK)
        s.chip(lx + 142, yy + 31, 66, 14, rel, fill=REL_FILL.get(rel, GREY), fs=8)
        s.t(lx + 214, yy + 32, n + ' · ' + alloc, fs=8, color=SOFT)
        fill = {'Suggested': '#ffffff', 'In review': ACC_BG, 'Stale': AMBER_BG, 'Disputed': RED_BG, 'Approved': GREEN_BG}[st]
        s.chip(lx + 420, yy + 8, 62, 14, st, fill=fill, fs=8, dash=(st == 'Suggested'))
        sign_dots(s, lx + 420, yy + 30, signs)
        avatar(s, lx + 560, yy + 16, who, BLUE_BG if who == 'SE' else VIOLET_BG)
        s.prov(lx + 500, yy + 10, 'mech' if ln == 'A' else 'ai')
    # scrollbar and footer
    s.r(lx + 602, ry, 6, 580, fill=MID, stroke=MID, rounded=False)
    s.r(lx + 602, ry, 6, 28, fill=SOFT, stroke=SOFT, rounded=False)
    fy2 = ry + 590
    s.t(lx, fy2, 'Showing 1 to 31 of 31 in My queue · only about 20 rows are drawn at once (windowed list)', fs=9, color=SOFT)
    s.t(lx, fy2 + 18, 'Keys: J / K move   Enter open   X select   A accept   E edit   R reject   S skip   U undo   ? help', fs=9, color=SOFT, family=3)
    s.num(lx + 590, fy2 - 6, 7)
    d.frame_end()
    return ['Progress bar and counts are always in words: Approved, In review, Stale, Disputed, Suggested. Every number is a button that applies that filter.',
            'Saved views are the main navigation at scale. "My queue" is the default for a reviewer; "Needs my lens" shows clusters where your lens is required but not yet signed.',
            'Facets with live counts. Cluster size has an "oversized" bucket for clusters the pipeline refused to trust (see S6).',
            'The list is windowed, so 250 clusters or 1,500 requirements cost the same to draw. Search matches ID, text and extracted parameters.',
            'Bulk actions are limited to assigning and opening a stack. Decisions stay one cluster at a time unless a project turns on policy-gated lane A acceptance.',
            'Each row: lane, relationship, member count, allocation, status, four lens markers (S P U N), provenance mark, assignee. Dashed marker = not yet required or pending.',
            'Keyboard triage for lane A and B. Everything has a visible button too, so keys are an accelerator, not the only way.']


# ---------------------------------------------------------------- S2 explorer + map
def s2_explorer(d, ox, oy):
    W, H = 1000, 840
    s = new_frame(d, ox, oy, W, H, 'S2 · All requirements: project map and table')
    cx, cy = shell2(s, W, H, 'Review queue')
    s.h1(cx, cy, 'All requirements (1,487)', fs=22)
    s.btn(cx + 560, cy - 2, 120, 28, 'Map', primary=True, fs=10)
    s.btn(cx + 690, cy - 2, 126, 28, 'Table', fs=10)
    s.t(cx, cy + 32, 'Every requirement in the project, including the ones no method matched. Nothing is hidden because it was not flagged.', fs=10, color=DARK)
    # legend
    ly = cy + 56
    leg = [('No match found', '#ffffff', True), ('Suggested', AMBER_BG, False), ('In review', ACC_BG, False), ('Approved', GREEN_BG, False), ('Conflict (lane C)', RED_BG, False), ('Stale', '#e0d4f7', False)]
    x = cx
    for lab, f, dash in leg:
        s.r(x, ly, 14, 14, fill=f, stroke=SOFT, dash=dash)
        s.t(x + 20, ly, lab, fs=9, color=DARK)
        x += len(lab) * 5.6 + 48
    s.num(cx + 800, ly - 8, 1)
    # map
    my = ly + 30
    s.card(cx, my, 816, 380)
    s.t(cx + 14, my + 10, 'Each square is 5 requirements, coloured by the most urgent status inside it. Groups are allocations.', fs=9, color=SOFT)
    groups = [('Flight Control', 115), ('Data Recorder', 90), ('Ground Station', 85), ('Power Distribution', 80), ('Comms', 110), ('Cockpit Display', 95), ('Mission Computer', 130), ('Radar', 140),
              ('Environmental', 70), ('Fuel Mgmt', 60), ('Landing Gear', 55), ('Other (26 more)', 457)]
    import random
    rng = random.Random(5)
    px, py = cx + 14, my + 34
    colw = 250
    cols = 2
    gy = [py] * cols
    for gi, (nm, n) in enumerate(groups):
        c = gi % cols
        cells = max(1, n // 5)
        gx = px + c * (colw + 10)
        y0 = gy[c]
        s.t(gx, y0, nm + '  ' + str(n), fs=9, color=INK)
        per = 20
        rows_ = (cells + per - 1) // per
        for k in range(cells):
            r_ = rng.random()
            f, dash = '#ffffff', True
            if r_ < .09:
                f, dash = AMBER_BG, False
            elif r_ < .12:
                f, dash = ACC_BG, False
            elif r_ < .145:
                f, dash = GREEN_BG, False
            elif r_ < .165:
                f, dash = RED_BG, False
            elif r_ < .17:
                f, dash = '#e0d4f7', False
            s.r(gx + (k % per) * 11.5, y0 + 16 + (k // per) * 11.5, 9, 9, fill=f, stroke=LINE if dash else '#868e96', rounded=False, dash=dash, sw=1)
        gy[c] = y0 + 16 + rows_ * 11.5 + 14
    s.r(cx + 540, my + 40, 260, 170, fill='#ffffff', stroke=ACC, sw=2)
    s.t(cx + 552, my + 50, 'Flight Control · 115 requirements', fs=10, color=INK)
    for i, (k, v) in enumerate([('No match found', '84'), ('In a cluster, suggested', '19'), ('In review', '5'), ('Approved', '5'), ('Conflict', '1'), ('Stale', '1')]):
        kv(s, cx + 552, my + 72 + i * 18, k, v, kw=170, fs=9)
    s.btn(cx + 552, my + 180, 150, 24, 'Open in queue', primary=True, fs=9)
    s.num(cx + 800, my - 8, 2)
    # table
    tyy = my + 396
    s.caps(cx, tyy, 'TABLE VIEW (same data, the accessible equivalent of the map)')
    widths = [96, 290, 120, 90, 110, 110]
    head = ['ID', 'Statement (start)', 'Allocation', 'Owner', 'Status', 'Cluster']
    rows = [['REQ-FCS-0212', 'The Flight Control Subsystem shall transmit a health status message…', 'Flight Control', 'FCS team', ('Suggested', AMBER_BG), 'CL-042 (x3)'],
            ['REQ-FCS-0301', 'The Flight Control Subsystem shall log each mode change…', 'Flight Control', 'FCS team', ('No match found', None), 'none'],
            ['REQ-SYS-0140', 'The Data Recorder shall store all fault events for at least 30 days.', 'Data Recorder', 'Data team', ('Approved', GREEN_BG), 'CL-041 (x2)'],
            ['REQ-PWR-0007', 'The Power Distribution Unit shall supply 28 VDC to…', 'Power Distribution', 'Power team', ('Conflict', RED_BG), 'CL-048 (x2)']]
    y2 = table(s, cx, tyy + 16, widths, head, rows, fs=9, minh=30)
    s.t(cx, y2 + 8, '"No match found" is not proof a requirement is unique. The methods can miss paraphrases and converted units. Use Search by parameter (see 09) for a second look.', fs=9, color='#b35a00')
    s.num(cx + 800, tyy - 8, 3)
    d.frame_end()
    return ['Map view: the whole project on one screen. Colour is paired with a legend and a table below, so the map is never the only way to read status.',
            'Group by allocation (or owner, level, baseline). Click a group to see its breakdown and jump into the queue with that filter applied.',
            'Table view lists every requirement, including ones no method matched. "No match found" is worded carefully because absence of a match is not proof of uniqueness.']


# ---------------------------------------------------------------- S3 team and assignments
def s3_team(d, ox, oy):
    W, H = 1000, 830
    s = new_frame(d, ox, oy, W, H, 'S3 · Team and assignments (lead view)')
    cx, cy = shell2(s, W, H, 'Review queue')
    s.h1(cx, cy, 'Team and assignments', fs=22)
    s.t(cx, cy + 32, 'Who is reviewing what, how far along they are, and what is waiting. Visible to leads and admins.', fs=10, color=DARK)
    y = cy + 60
    s.card(cx, y, 816, 262)
    s.caps(cx + 14, y + 10, 'REVIEWERS')
    widths = [150, 60, 70, 60, 70, 100, 258]
    head = ['Reviewer', 'Lens', 'Assigned', 'Done', 'Waiting', 'Min per cluster', 'Load']
    rows = [['SE-1  (Flight Control)', 'SE', '62', '41', '21', '3.4', ''], ['SE-2  (Data, Ground)', 'SE', '55', '30', '25', '4.1', ''], ['SE-3  (Power, Comms)', 'SE', '58', '12', '46', '5.2', ''],
            ['PE-1', 'PE', '118', '64', '54', '1.2', ''], ['UX-1', 'UX', '40', '22', '18', '1.0', ''], ['NU-1', 'NU', '40', '35', '5', '1.3', '']]
    y1 = table(s, cx + 14, y + 28, widths, head, rows, fs=9, minh=28)
    for i, (n, load) in enumerate([(62, .9), (55, .8), (58, 1.0), (118, .7), (40, .5), (40, .3)]):
        bar_h(s, cx + 14 + 150 + 60 + 70 + 60 + 70 + 100 + 8, y + 28 + 26 + i * 28 + 9, 160, load, value=None)
    s.t(cx + 14, y + 28 + 26 + 6 * 28 + 6, 'Load = assigned and waiting against 3 hours per day over the review window. Sample figures.', fs=9, color=SOFT)
    s.num(cx + 800, y - 8, 1)
    y += 278
    s.card(cx, y, 400, 220)
    s.caps(cx + 14, y + 10, 'UNASSIGNED (54)')
    for i, (a, n) in enumerate([('Flight Control', 9), ('Data Recorder', 14), ('Ground Station', 11), ('Power Distribution', 8), ('Other', 12)]):
        s.t(cx + 14, y + 36 + i * 24, a, fs=10, color=DARK)
        s.t(cx + 170, y + 36 + i * 24, str(n), fs=10, color=INK, family=3)
        s.btn(cx + 220, y + 32 + i * 24, 80, 20, 'Assign…', fs=8)
    s.btn(cx + 14, y + 168, 200, 32, 'Auto-assign by rules', primary=True, fs=10)
    s.t(cx + 224, y + 176, 'Preview first, then confirm.', fs=9, color=SOFT)
    s.num(cx + 384, y - 8, 2)
    s.card(cx + 416, y, 400, 220)
    s.caps(cx + 430, y + 10, 'AUTO-ASSIGN RULES')
    for i, t_ in enumerate(['Allocation to reviewer (map once, reuse)', 'Owner team to an SE who is not in that team', 'Lane C: senior SE plus an adjudicator', 'Same allocation stays with the same reviewer',
                            'Cap: no reviewer over 60 open clusters', 'Never assign a person their own requirement']):
        s.t(cx + 430, y + 36 + i * 26, '•  ' + t_, fs=10, color=DARK)
    s.num(cx + 800, y - 8, 3)
    y += 236
    s.card(cx, y, 816, 150)
    s.caps(cx + 14, y + 10, 'WAITING THE LONGEST')
    for i, (cid, t_, who, days) in enumerate([('CL-048', 'Bus voltage: 28 VDC or 270 VDC?', 'Disputed, needs adjudicator', '6 days'), ('CL-047', 'Display refresh: shall or should?', 'Stale since source changed', '4 days'), ('CL-045', 'Log fault codes: with timestamp?', 'Waiting on UX-1', '3 days')]):
        s.t(cx + 14, y + 36 + i * 30, cid, fs=10, family=3, color=INK)
        s.t(cx + 80, y + 36 + i * 30, t_, fs=10, color=DARK)
        s.t(cx + 400, y + 36 + i * 30, who, fs=10, color=DARK)
        s.chip(cx + 720, y + 34 + i * 30, 80, 16, days, fill=AMBER_BG if i else RED_BG, fs=9)
    s.num(cx + 800, y - 8, 4)
    d.frame_end()
    return ['Reviewer table: lens, assigned, done, waiting, average minutes per cluster, load. Used to balance work, not to rank people. Sample figures only.',
            'Unassigned clusters grouped by allocation, with a previewed auto-assign. Nothing is moved until the lead confirms.',
            'Assignment rules are written down and editable. Key rule: nobody reviews a requirement they own.',
            'Aging list surfaces disputed, stale and blocked clusters first, with the reason in words.']
