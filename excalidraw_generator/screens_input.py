"""Board 10: the input layer as the user sees it. A WORKED EXAMPLE of adding screens (see EXCALIDRAW_GUIDE.md, recipe A).

Each function draws one frame at (ox, oy) and returns the list of note strings that boards_05_09.build_board
places in the Notes column beside it."""
from wf2 import *  # noqa: F401,F403  (Doc, Scr, palette, new_frame, para, table, chk_list, kv, shell2 ...)
from flows import box, mark, SRC_F, MECH_F, AI_F, HUM_F, GUARD_F

TIER_FILL = {'Structured': GREEN_BG, 'Tabular': BLUE_BG, 'Parsed': AMBER_BG, 'Extracted': RED_BG}


def i1_open_any(d, ox, oy):
    W, H = 1000, 700
    s = new_frame(d, ox, oy, W, H, '10.1 · Open a project: any source')
    s.t(40, 30, '1 · SOURCE   /   2 · MAP FIELDS AND PREPARE   /   3 · WORKSPACE', fs=10, color=SOFT, family=3)
    s.h1(40, 60, 'Open a requirements project', fs=28)
    para(s, 40, 104, 'Drop a file, paste a model address, or connect a database. The app says what it recognised and how far to trust what it read, before you go on.', 820, fs=11)
    # drop zone + recognised line
    s.r(40, 150, 920, 84, fill='#ffffff', stroke=SOFT, dash=True)
    s.t(64, 164, 'Drop files here, paste a model URL, or choose "Database" below', fs=13, color=INK)
    s.chip(64, 198, 560, 22, 'Recognised: ReqIF · reqs.reqif · 9 objects (8 requirements, 1 heading)', fill=GREEN_BG, fs=10, stroke=HUM)
    s.btn(780, 190, 160, 32, 'Use this', primary=True)
    cards = [('SysML v2 model', 'Structured or Parsed', 'Systems Modeling API address (Structured), KPAR package, or a .sysml text file (Parsed).', 'Structured'),
             ('ReqIF export', 'Structured', 'From MSOSA, DOORS or DOORS Next. The most reliable file route.', 'Structured'),
             ('Spreadsheet or CSV', 'Tabular', 'One requirement per row. You confirm which column is which.', 'Tabular'),
             ('Database (SQL)', 'Tabular', 'You give a read-only query. Nothing is ever written to the database.', 'Tabular'),
             ('Word or PDF document', 'Extracted', 'Statements are found in the text. You verify every one against the page.', 'Extracted'),
             ('MSOSA project file (.mdzip)', 'Not read directly yet', 'Export ReqIF from MSOSA and open that instead.', None)]
    for i, (t_, tier, body, key) in enumerate(cards):
        r_, c_ = divmod(i, 3)
        x, y = 40 + c_ * 312, 266 + r_ * 176
        s.card(x, y, 296, 160, dash=(key is None))
        s.t(x + 16, y + 14, t_, fs=14, color=INK if key else SOFT)
        s.chip(x + 16, y + 44, 150 if len(tier) > 12 else 90, 18, tier, fill=TIER_FILL.get(key, GREY), fs=9, dash=(key is None))
        para(s, x + 16, y + 74, body, 262, fs=10, color=DARK if key else SOFT)
        s.btn(x + 16, y + 118, 110, 28, 'Choose' if key else 'See how', fs=10, disabled=(key is None))
    s.t(40, 628, 'Trust level in words:  Structured = stable IDs and links.  Tabular = rows you map.  Parsed = light read of model text.  Extracted = found in prose, you verify each.', fs=9, color=SOFT)
    s.t(40, 646, 'Sample data only. Names and counts are from the synthetic fixtures.', fs=9, color=SOFT)
    s.num(12, 152, 1)
    s.num(12, 268, 2)
    s.num(12, 620, 3)
    d.frame_end()
    return ['The app sniffs the file first (extension and first bytes) and names what it found. You can override it.',
            'Every card states a trust level in words, never colour alone. Structured and Tabular are different promises from Extracted.',
            'The legend repeats the four trust levels. They stay on every record later as a fidelity badge.']


def i2_map_any(d, ox, oy):
    W, H = 1000, 780
    s = new_frame(d, ox, oy, W, H, '10.2 · Map fields for any source')
    s.t(40, 30, '1 · SOURCE   /   2 · MAP FIELDS AND PREPARE   /   3 · WORKSPACE', fs=10, color=SOFT, family=3)
    s.h1(40, 60, 'Check how your columns map', fs=26)
    s.chip(40, 100, 330, 20, 'PROPOSED by the app. Not trusted until you confirm.', fill=AMBER_BG, stroke='#f1c40f', fs=10)
    s.t(384, 104, 'Source: reqs.xlsx · sheet "Requirements" (Cover sheet skipped)', fs=10, color=DARK)
    s.card(40, 136, 620, 380)
    s.caps(56, 148, 'MAPPING PROFILE  xlsx-srs   (saved with the project, replayed on re-import)')
    rows = [['Requirement ID', 'Req #', 'REQ-FCS-0101', ('Medium', AMBER_BG), 'Change'],
            ['Statement', 'Requirement Text', 'The Flight Control…', ('High', GREEN_BG), 'Change'],
            ['Rationale', 'Why', 'Bounds ground-station…', ('Medium', AMBER_BG), 'Change'],
            ['Verification', 'V Method  (T→Test, A→Analysis)', 'T', ('High', GREEN_BG), 'Change'],
            ['Allocated to', 'Subsystem', 'Flight Control Subsystem', ('Medium', AMBER_BG), 'Change'],
            ['Owner', 'IPT', 'FCS team', ('Medium', AMBER_BG), 'Change'],
            ['Baseline', 'not found: empty slot', '—', ('Low', RED_BG), 'Choose']]
    table(s, 56, 172, [120, 170, 150, 70, 80], ['SLOT', 'SOURCE FIELD', 'SAMPLE', 'LABEL', ''], rows, fs=10, bold_first=True, minh=34)
    s.t(56, 460, 'Why Medium: the column name matches (Req #) or the values look right, but nobody has confirmed it. Exact = copied from a field you chose.', fs=9, color=SOFT)
    s.t(56, 478, 'Every source field you do not map is kept under "other fields", never discarded.', fs=9, color=SOFT)
    s.card(680, 136, 280, 380)
    s.caps(696, 148, 'DRY-RUN REPORT')
    y = chk_list(s, 696, 172, 250, [('Pass', 'Every row accounted for: 9 read = 8 kept + 0 rejected + 1 filtered'), ('Pass', 'No duplicate IDs; no ID had to be invented'),
                                    ('Needs you', 'Profile is proposed: confirm it'), ('Needs you', '1 field has no source: Baseline'), ('Pass', 'Source file not modified (hash unchanged)')], fs=9)
    para(s, 696, y + 6, 'Rejected rows list their reason. Filtered rows list the rule that excluded them.', 250, fs=9, color=SOFT)
    s.card(40, 534, 920, 140)
    s.caps(56, 546, 'FIRST THREE RECORDS AS THE REVIEW SCREENS WILL SHOW THEM')
    table(s, 56, 566, [110, 480, 110, 90], ['ID', 'STATEMENT', 'VERIFICATION', 'FIDELITY'], [
        ['REQ-FCS-0101', 'The Flight Control Subsystem shall transmit a status message to the ground station within 200 ms of a mode change.', 'Test', 'Tabular'],
        ['REQ-FCS-0102', 'The Flight Control Subsystem shall transmit a status message to the ground station within 0.2 seconds of a mode change.', 'Test', 'Tabular']],
          fs=9, minh=30)
    s.btn(40, 700, 230, 38, 'Confirm mapping and import', primary=True, fs=12)
    s.btn(286, 700, 190, 38, 'Save profile (YAML)', fs=11)
    s.btn(492, 700, 150, 38, 'Back', fs=11)
    s.num(22, 138, 1)
    s.num(662, 138, 2)
    s.num(22, 536, 3)
    s.num(22, 702, 4)
    d.frame_end()
    return ['The mapping table is the whole "program" for a new spreadsheet. Changing a row edits a small text profile, not code.',
            'The dry run proves nothing was lost: rows read must equal rows kept, rejected and filtered. Anything else is a bug and stops the import.',
            'Records appear exactly as the review screens will show them, so a wrong column is caught here, not in the middle of a review.',
            'Confirming saves the profile. Re-importing next month replays it and shows what changed.']


def i3_extract(d, ox, oy):
    W, H = 1000, 720
    s = new_frame(d, ox, oy, W, H, '10.3 · Verify statements found in a document')
    s.t(40, 30, 'IMPORT FROM DOCUMENT: srs.pdf   (Fidelity: Extracted)', fs=10, color=SOFT, family=3)
    s.h1(40, 58, 'Check what the app found', fs=26)
    s.chip(40, 98, 470, 20, 'Found in text by rules. Each record needs your check against the page.', fill=RED_BG, stroke=RED, fs=10)
    s.card(40, 134, 520, 520)
    s.caps(56, 146, '8 STATEMENTS FOUND  ·  2 VERIFIED  ·  SHOWING 5')
    items = [('REQ-FCS-0101', 'p1 ¶3', True, 'The Flight Control Subsystem shall transmit a status message… within 200 ms'),
             ('REQ-FCS-0102', 'p1 ¶4', True, 'The Flight Control Subsystem shall transmit a status message… within 0.2 seconds'),
             ('REQ-FCS-0103', 'p1 ¶5.1', False, 'The Flight Control Subsystem shall retain at least 30 days of fault records.'),
             ('ID invented: pdf:p1:5.2', 'p1 ¶5.2', False, 'The Flight Control Subsystem should retain at least 14 days of fault records.'),
             ('REQ-PWR-0201', 'table 1, row 2', False, 'The Power Subsystem shall not exceed a mass of 12 kg.')]
    for i, (uid, loc, ok, txt) in enumerate(items):
        y = 172 + i * 90
        s.line([(40, y - 6), (560, y - 6)], stroke='#dee2e6', sw=1)
        checkbox(s, 56, y + 2, ok)
        s.t(80, y, uid, fs=11, color=INK if 'invented' not in uid else RED)
        s.chip(400, y, 140, 16, 'Found at ' + loc, fill=GREY, fs=9)
        para(s, 80, y + 22, txt, 440, fs=10)
        if 'invented' in uid:
            s.chip(80, y + 58, 250, 16, 'No ID in the document: confirm or type one', fill=AMBER_BG, fs=9)
    s.btn(56, 612, 150, 28, 'Verify selected', primary=True, fs=10)
    s.card(580, 134, 380, 520, fill='#fbfbfd')
    s.caps(596, 146, 'SOURCE PAGE 1  (highlight = selected record)')
    s.r(610, 176, 320, 440, fill='#ffffff', stroke=LINE)
    s.ph(626, 196, 288, 4, gap=14)
    s.r(622, 262, 296, 50, fill=AMBER_BG, stroke='#f1c40f', rounded=False)
    s.ph(626, 270, 288, 3, gap=14, fracs=(1, 1, .6))
    s.ph(626, 332, 288, 5, gap=14)
    s.ph(626, 420, 288, 4, gap=14)
    s.t(610, 626, 'Open in the document at p1 ¶5.1', fs=9, color=ACC)
    s.num(22, 136, 1)
    s.num(562, 136, 2)
    s.num(22, 614, 3)
    d.frame_end()
    return ['Statements found in prose carry a location (page and paragraph or table row) so a person can look at the original in one click.',
            'An ID that the document did not contain is invented and labelled as invented; it never passes as a real ID.',
            'Verifying is deliberate and per record. Unverified records stay marked Extracted everywhere they appear. (Design proposal: confirm the rule with your process lens.)']


def i4_arch(d, ox, oy):
    W, H = 1500, 820
    d.frame_begin(ox, oy, W, H, '10.4 · How any source becomes the same thing')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Five layers. Only the first two know about file formats.', fs=24, family=1)
    heads = [(20, 'SOURCES', 'what you have'), (310, 'ADAPTERS', 'read, never interpret'), (600, 'MAPPING PROFILE', 'small text file, human-confirmed'),
             (940, 'CANONICAL MODEL', 'one shape for everything'), (1240, 'THE APP', 'sees only the canonical model')]
    for x, t_, sub_ in heads:
        d.text(X + x, Y + 64, t_, fs=14, family=1, color=RED)
        d.text(X + x, Y + 86, sub_, fs=11, family=2, color=SOFT)
    srcs = ['SysML v2 API / KPAR', 'SysML v2 text (.sysml)', 'ReqIF (MSOSA, DOORS, DOORS Next)', 'Excel / CSV (incl. DOORS export)', 'SQL database', 'Word (.docx)', 'PDF with text layer', 'MSOSA .mdzip (not yet)']
    ads = ['sysml_api', 'sysml_text', 'reqif', 'tabular', 'sql', 'docx', 'pdf', 'mdzip (stub)']
    tiers = ['Structured', 'Parsed', 'Structured', 'Tabular', 'Tabular', 'Extracted', 'Extracted', '']
    bs, ba = [], []
    for i, (a, b, t_) in enumerate(zip(srcs, ads, tiers)):
        y = Y + 120 + i * 78
        bs.append(box(d, X + 20, y, 250, 56, a, SRC_F, fs=11, dash=(i == 7)))
        ba.append(box(d, X + 310, y, 230, 56, b + ('\n' + t_ if t_ else ''), MECH_F, fs=11, dash=(i == 7)))
        d.connect(bs[-1], ba[-1], 'r', 'l', color=SOFT, sw=1)
    prof = box(d, X + 600, Y + 160, 250, 270, 'profile: msosa-reqif\nadapter: reqif\ncontainers: [Requirement]\nfields:\n  uid:  ReqIF.ForeignID\n  text: ReqIF.Text\n  verification:\n    from: Verification Method\nlinks: ...', HUM_F, stroke=HUM, fs=11, align='left', valign='middle', pad=16, family=3)
    d.text(X + 600, Y + 440, 'A person confirms it.\nThe app can propose one by\nlooking at names and values.', fs=11, family=1, color=HUM)
    can = box(d, X + 940, Y + 120, 250, 410, 'Requirement\n  mid  (machine ID)\n  uid  (the ID people use)\n  text, normalised text\n  fingerprint\n  slots: shall/should,\n         not, numbers + units\n  fields: rationale,\n          verification,\n          allocation, owner…\n  conf per field\n  source locator\n  fidelity\nLink · Rejected · Report', GUARD_F, fs=11, align='left', valign='middle', pad=16, family=3)
    for b in ba[:7]:
        d.connect(b, prof, 'r', 'l', color=SOFT, sw=1)
    d.connect(prof, can, 'r', 'l', sw=2)
    d.text(X + 856, Y + 250, 'map +\nnormalise', fs=11, family=1, color=INK)
    app = [('Compare\nmechanical ladder', MECH_F), ('AI judge and drafts\n(proposes only)', AI_F), ('Review screens\nand lenses', HUM_F), ('Ledger and audit', GUARD_F), ('Export to documents', BLUE_BG)]
    for i, (t_, f) in enumerate(app):
        y = Y + 120 + i * 82
        b = box(d, X + 1240, y, 240, 62, t_, f, fs=11)
        d.connect(can, b, 'r', 'l', color=SOFT, sw=1)
    d.text(X + 20, Y + 760, 'Add a source: write one adapter, add a fixture, make the conformance tests pass. Nothing else changes.   Add a spreadsheet layout: write a profile, no code.', fs=14, family=1, color=RED)
    d.frame_end()
    return ['Left of the profile: file formats. Right of it: nothing knows or cares where a requirement came from.',
            'The profile is the only place meaning is decided, and a person confirms it. AI may propose one; it never applies one.',
            'Every record keeps its source locator and a trust level, so the review screens can always say where it came from and how much to trust it.',
            'Dashed: the MSOSA project file is recognised but not read directly yet. Export ReqIF from MSOSA instead.']
