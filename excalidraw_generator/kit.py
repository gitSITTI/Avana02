"""IA / site map, UI kit, design tokens, four-lens review board, open questions."""
from wf import *
from wf_b import tokw, guard_row
from flows import box, SRC_F, MECH_F, AI_F, HUM_F, GUARD_F
from exc import Doc, INK


def cap(s, x, y, t_):
    s.t(x, y, t_, fs=11, family=1, color=RED)


def sub(s, x, y, t_):
    s.t(x, y, t_, fs=9, color=SOFT)


# ------------------------------------------------------------------ IA
def ia(d, ox, oy):
    W, H = 1500, 800
    d.frame_begin(ox, oy, W, H, 'K1 · Information architecture (site map)')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Information architecture: one loop, no dead ends', fs=24, family=1)
    launch = box(d, X + 20, Y + 340, 110, 64, 'Launch', '#ffffff', fs=14)
    opn = box(d, X + 190, Y + 320, 180, 104, 'Open a project\n4 source cards\nrecent projects\nfirst-run help', SRC_F, fs=12)
    imp = box(d, X + 470, Y + 320, 180, 104, 'Map fields and\nprepare\ndetected fields\n+ prepared comparisons', SRC_F, fs=12)
    d.connect(launch, opn, 'r', 'l')
    d.connect(opn, imp, 'r', 'l', label='choose', fs=11)
    d.rect(X + 700, Y + 70, 780, 700, fill='#fbfbfd', stroke=SOFT, dash=True, sw=2)
    d.text(X + 716, Y + 78, 'Workspace', fs=18, family=1, color=SOFT)
    d.poly([(X + 652, Y + 372), (X + 698, Y + 372)])
    d.text(X + 658, Y + 350, 'open', fs=11, family=1)
    chrome = box(d, X + 730, Y + 110, 720, 70, 'Always visible:  title block (project, source, baseline, status, reviewing as)  ·  DRAFT banner  ·  sidebar  ·  lens switch  ·  Glossary and help  ·  Close project', '#ffffff', fs=11, dash=True)
    names = [('Overview', 'where to start', SRC_F), ('Review queue', 'the main loop', HUM_F), ('Methods\nand metrics', 'compare sources', MECH_F), ('Audit log', 'verify the chain', GUARD_F), ('Export to\ndocuments', 'draft package', BLUE_BG)]
    views = []
    for i, (n_, sub_, f) in enumerate(names):
        views.append(box(d, X + 730 + i * 146, Y + 220, 134, 76, n_ + '\n' + sub_, f, fs=11))
    detail = box(d, X + 820, Y + 350, 250, 360, 'CLUSTER DETAIL (top to bottom)\n1  header: lane, relationship, blind-first\n2  A and B side by side + metadata\n3  mechanical methods\n4  ten guards\n5  AI proposal, evidence, record\n6  consequences\n7  decision card\n8  four-lens sign-off', '#ffffff', fs=12, align='left', valign='middle', pad=14)
    d.connect(views[1], detail, 'b', 't')
    exp_note = box(d, X + 1100, Y + 350, 340, 100, 'Export  →  Review\n"Change" or "Open" on a listed\ncluster jumps to that cluster', '#ffffff', fs=12, dash=True)
    d.connect(views[4], exp_note, 'b', 't', dash=True)
    aud_note = box(d, X + 1100, Y + 480, 340, 80, 'Every action anywhere\nappends one event to the audit log', '#ffffff', fs=12, dash=True)
    d.connect(exp_note, aud_note, 'b', 't', dash=True, color=SOFT)
    box(d, X + 1100, Y + 600, 340, 100, 'Glossary and help\n18 plain terms, one click from anywhere,\nreturns to where you were', '#fff9db', stroke='#f1c40f', fs=12)
    d.text(X + 30, Y + 540, 'Rules', fs=18, family=1, color=RED)
    d.text(X + 30, Y + 572, d.wrap('1  Every view is one click from the sidebar.\n2  The Overview names the first action.\n3  Glossary and Close project are always present.\n4  Reviewing as (lens) never changes what the data says, only which checks you see.\n5  Phone: the same list becomes a stacked menu.', 600, 13), fs=13, family=2, color=DARK)
    d.frame_end()


# ------------------------------------------------------------------ kit
def kit(d, ox, oy):
    W, H = 1500, 1110
    d.frame_begin(ox, oy, W, H, 'K2 · UI kit (components as built in the prototype)')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill='#EEF1F3', stroke='#EEF1F3', rounded=False)
    s.t(20, 14, 'UI kit: every component, every state', fs=24, family=1, color=INK)

    # chips
    cap(s, 20, 60, 'Lane chips')
    for i, (t_, f, c) in enumerate([('Lane A · low risk', '#E1F2E7', '#14502B'), ('Lane B · needs evidence', '#FFF0D2', '#6B3D00'), ('Lane C · conflict', '#FDE3E0', '#7A1510')]):
        s.chip(20, 84 + i * 28, 160, 22, t_, fill=f, stroke=f, color=c, fs=10)
    sub(s, 20, 170, 'Lane is always a word, never only a colour.')
    cap(s, 220, 60, 'Relationship chips')
    for i, (t_, f, c) in enumerate([('Equivalent', '#E1F2E7', '#14502B'), ('Variant', '#FFF0D2', '#6B3D00'), ('Subsumes', '#E4ECFB', '#123C8C'), ('Conflict', '#FDE3E0', '#7A1510'), ('Complementary', '#EDE8F8', '#3A2A80')]):
        s.chip(220 + (i % 2) * 130, 84 + (i // 2) * 28, 120, 22, t_, fill=f, stroke=f, color=c, fs=10)
    cap(s, 520, 60, 'Status chips')
    s.chip(520, 84, 110, 22, 'Suggested', fill='#ffffff', stroke='#6B7782', dash=True, fs=10)
    s.chip(520, 112, 110, 22, 'In review', fill='#E8F0FD', stroke='#E8F0FD', color='#123C8C', fs=10)
    s.chip(520, 140, 110, 22, 'Approved', fill='#E1F2E7', stroke='#E1F2E7', color='#14502B', fs=10)
    sub(s, 520, 170, 'Dashed = nobody has decided.')
    cap(s, 680, 60, 'Detected-field confidence')
    for i, (t_, f) in enumerate([('Exact', '#E1F2E7'), ('High', '#E1F2E7'), ('Medium', '#FFF0D2')]):
        s.chip(680, 84 + i * 28, 80, 22, t_, fill=f, stroke=f, fs=10)

    # provenance
    cap(s, 860, 60, 'Provenance marks')
    s.prov(860, 90, 'mech', 'Square: mechanical method', fs=11)
    s.prov(860, 118, 'ai', 'Diamond: AI', fs=11)
    s.prov(860, 146, 'human', 'Circle: a person', fs=11)
    sub(s, 860, 170, 'Shape + label, so it survives greyscale.')

    # buttons
    cap(s, 1100, 60, 'Buttons')
    s.btn(1100, 84, 150, 40, 'Primary', primary=True, fs=11)
    s.btn(1260, 84, 150, 40, 'Secondary', fs=11)
    s.btn(1100, 134, 150, 40, 'Disabled', disabled=True, fs=11)
    s.r(1260, 134, 150, 40, 'Keyboard focus', fill='#ffffff', stroke=SOFT, fs=11, color=DARK)
    s.r(1254, 128, 162, 52, stroke=ACC, sw=3)
    sub(s, 1100, 182, '44 px high at full size · focus ring is 3 px accent')

    # tokens
    cap(s, 20, 220, 'Slot highlights in requirement text')
    s.r(20, 244, 700, 70, fill='#ffffff', stroke=LINE)
    tokw(s, 34, 256, 670, 'The Flight Control Subsystem shall transmit a heartbeat message every 10 seconds, not after a state change unless upon request.', fs=12, differs=('10', 'seconds,'))
    for i, (lab, f) in enumerate([('number or unit', '#ffe0ad'), ('shall / should', '#d5e3ff'), ('not', '#ffd3ce'), ('condition', '#e8deff')]):
        s.r(740 + i * 0, 244 + i * 18, 14, 12, fill=f, stroke=f, rounded=False)
        s.t(762, 244 + i * 18, lab, fs=10, color=DARK)
    s.t(740, 320, 'orange underline = differs between A and B', fs=10, color='#b35a00')

    # guard rows
    cap(s, 20, 350, 'Guard rows')
    for i, (st, n_, note) in enumerate([('p', 'Numbers preserved', ''), ('w', 'No invented content', 'adds "UTC timestamp"'), ('f', 'Numbers preserved', '1 second ≠ 10 seconds')]):
        guard_row(s, 30 + i * 260, 384, 220, n_, st, note)
    # lens chips
    cap(s, 820, 350, 'Lens check chips')
    for i, (t_, f) in enumerate([('Pass', GREEN_BG), ('Needs you', AMBER_BG), ('Blocked', RED_BG)]):
        s.chip(820 + i * 110, 384, 100, 20, t_, fill=f, fs=10)
    s.chip(820, 414, 150, 20, 'Systems engineer: pending', fill='#ffffff', dash=True, fs=9)
    s.chip(980, 414, 150, 20, 'Systems engineer: signed', fill='#E1F2E7', fs=9)

    # banners
    cap(s, 20, 470, 'Banners')
    s.r(20, 494, 700, 30, fill=AMBER_BG, stroke='#f1c40f')
    s.chip(30, 502, 44, 16, 'DRAFT', fill='#ffffff', stroke=DARK, fs=9)
    s.t(84, 501, 'Suggestions are proposals. Each stays a draft until all four lenses sign off.', fs=10, color='#5c4400')
    s.r(20, 534, 340, 30, 'Chain verified: all 6 entries match.', fill=GREEN_BG, stroke=HUM, fs=10, align='left', pad=10)
    s.r(380, 534, 340, 30, 'Chain broken at entry 2.', fill=RED_BG, stroke=RED, fs=10, align='left', pad=10)
    s.r(20, 574, 700, 46, 'Illustrative numbers. No gold set exists yet, so figures show layout only.', fill=AMBER_BG, stroke='#f1c40f', fs=10, align='left', pad=10)

    # inputs
    cap(s, 760, 470, 'Inputs')
    s.r(760, 494, 200, 30, 'DRAFT-0001', fill='#ffffff', stroke=INK, fs=11, align='left', pad=10, family=3)
    s.r(980, 498, 18, 18, fill='#ffffff', stroke=INK, sw=2)
    s.t(1004, 499, 'unchecked', fs=10, color=DARK)
    s.r(980, 524, 18, 18, fill='#ffffff', stroke=INK, sw=2)
    s.poly([(984, 533), (988, 538), (995, 528)], typ='line', stroke=INK, sw=2.5)
    s.t(1004, 525, 'checked', fs=10, color=DARK)
    s.r(1110, 494, 330, 70, 'Textarea for edited wording. The guards re-run on Save.', fill='#ffffff', stroke=ACC, sw=2, fs=10, align='left', valign='top', pad=8, family=1)
    s.r(760, 536, 200, 44, fill='#F1F6FF', stroke=ACC, sw=2)
    s.shape('ellipse', 770, 552, 14, 14, fill=ACC, stroke=ACC)
    s.t(792, 548, 'Selected option card', fs=10, color=INK)
    s.r(760, 590, 200, 44, fill='#ffffff', stroke=LINE)
    s.shape('ellipse', 770, 606, 14, 14, fill='#ffffff', stroke=SOFT, sw=2)
    s.t(792, 602, 'Unselected option card', fs=10, color=DARK)

    # cards and queue rows
    cap(s, 20, 650, 'Queue rows')
    s.r(20, 674, 200, 64, fill='#F1F6FF', stroke=ACC, sw=2)
    s.t(30, 682, 'CL-03', fs=10, family=3, color=INK)
    s.chip(140, 680, 70, 14, 'Lane B', fill='#FFF0D2', stroke='#FFF0D2', fs=8)
    s.t(30, 700, 'Heartbeat rate: 1 s or 10 s?', fs=9, color=DARK)
    s.chip(30, 718, 60, 14, 'Variant', fill='#FFF0D2', stroke='#FFF0D2', fs=8)
    s.chip(98, 718, 80, 14, 'Suggested', fill='#ffffff', dash=True, fs=8)
    sub(s, 20, 744, 'Selected: 2 px accent border')
    s.r(240, 674, 200, 64, fill='#ffffff', stroke=LINE)
    s.t(250, 682, 'CL-04', fs=10, family=3, color=INK)
    s.chip(360, 680, 70, 14, 'Lane B', fill='#FFF0D2', stroke='#FFF0D2', fs=8)
    s.t(250, 700, 'Fault logging: plain or with timestamp', fs=9, color=DARK)
    sub(s, 240, 744, 'Not selected')

    # meters / tables
    cap(s, 480, 650, 'Meters')
    s.bar(480, 684, 220, .31)
    s.t(710, 680, '31%', fs=10, family=3, color=INK)
    s.bar(480, 706, 220, .74)
    s.t(710, 702, '74%', fs=10, family=3, color=INK)
    s.r(480, 730, 220, 10, fill='#d0e0ff', stroke='#d0e0ff', rounded=False)
    sub(s, 480, 748, 'Sign-off meter: 0 of 4 (empty track still visible)')
    cap(s, 760, 650, 'Table row (audit)')
    s.r(760, 674, 680, 50, fill='#ffffff', stroke='#e9ecef', rounded=False)
    s.t(774, 682, '2', fs=10, family=3, color=INK)
    s.t(804, 682, '09:02:48', fs=9, family=3, color=DARK)
    s.prov(870, 682, 'mech', 'Mechanical', fs=9)
    s.t(970, 682, 'Built 41 candidate pairs and 7 clusters', fs=9, color=INK)
    s.t(1250, 680, '3be1a07c\n→ 9d40c2e5', fs=8, family=3, color=SOFT)
    s.r(760, 732, 680, 50, fill='#fff0f0', stroke='#e9ecef', rounded=False)
    s.t(774, 740, '2', fs=10, family=3, color=INK)
    s.t(970, 740, 'Built 39 candidate pairs (edited after the fact)', fs=9, color=RED)
    sub(s, 760, 788, 'Broken entry is tinted and says so in words.')

    # decision card
    cap(s, 20, 810, 'Decision card')
    s.r(20, 834, 700, 112, fill='#ffffff', stroke=LINE)
    s.r(34, 846, 16, 16, fill='#ffffff', stroke=INK, sw=2)
    s.t(60, 847, 'I have read both wordings and the guard results.', fs=10, color=INK)
    for i, (l_, p) in enumerate([('Keep both and link', True), ('Ask the owners', False), ('Reject suggestion', False), ('Skip', False)]):
        s.btn(34 + i * 168, 880, 158, 44, l_, primary=p, fs=11)
    sub(s, 34, 930, 'Nothing is written to the source model.')
    cap(s, 760, 810, 'First-run help')
    s.r(760, 834, 680, 112, fill='#ffffff', stroke=LINE)
    s.t(776, 844, 'New here? Three things to do on each cluster', fs=12, color=INK)
    s.t(776, 868, '1  Read both wordings    2  Check the guards    3  Decide, then four lenses sign off', fs=11, color=DARK)
    s.btn(776, 898, 110, 36, 'Hide this', fs=11)

    # glossary tile & icon note
    cap(s, 20, 980, 'Rules for every component')
    rules = ['Real buttons, inputs and labels. Icon-only buttons carry an aria-label.', 'Touch targets 44 px or larger on every screen.', 'No state is colour alone: each has a word or a shape.',
             'No emoji. Marks are drawn shapes. Lines use gap, not margin hacks.', 'Disabled controls say why, in a sentence next to them.', 'Every consequential action shows its consequence before the click and offers Undo after.']
    for i, r_ in enumerate(rules):
        s.t(20 + (i % 2) * 720, 1010 + (i // 2) * 30, '•  ' + r_, fs=12, color=DARK)
    d.frame_end()


# ------------------------------------------------------------------ tokens
def tokens(d, ox, oy):
    W, H = 1500, 700
    d.frame_begin(ox, oy, W, H, 'K3 · Design tokens')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill='#ffffff', stroke='#ffffff', rounded=False)
    s.t(20, 14, 'Design tokens (as used in the prototype)', fs=24, family=1, color=INK)
    sw = [('Surface', '#EEF1F3', INK), ('Card', '#FFFFFF', INK), ('Ink', '#17202A', '#ffffff'), ('Accent (Tweak)', '#1A4DB5', '#ffffff'), ('Bar fill', '#256ABF', '#ffffff'), ('Muted text', '#2F3B46', '#ffffff')]
    cap(s, 20, 60, 'Core')
    for i, (n_, c, tc) in enumerate(sw):
        s.r(20 + i * 130, 84, 120, 70, n_ + '\n' + c, fill=c, stroke=LINE, fs=10, color=tc)
    cap(s, 20, 180, 'Relationship and status')
    pairs = [('Equivalent', '#E1F2E7', '#14502B'), ('Variant', '#FFF0D2', '#6B3D00'), ('Subsumes', '#E4ECFB', '#123C8C'), ('Conflict', '#FDE3E0', '#7A1510'), ('Complementary', '#EDE8F8', '#3A2A80'), ('Approved', '#E1F2E7', '#14502B')]
    for i, (n_, f, c) in enumerate(pairs):
        s.r(20 + i * 130, 204, 120, 56, n_ + '\n' + f + ' / ' + c, fill=f, stroke=LINE, fs=9, color=c)
    cap(s, 20, 286, 'Provenance')
    for i, (n_, c) in enumerate([('Mechanical  #34424F', '#34424F'), ('AI  #8B1F6B', '#8B1F6B'), ('Human  #1B6B3A', '#1B6B3A')]):
        s.r(20 + i * 190, 310, 180, 40, n_, fill=c, stroke=c, fs=10, color='#ffffff')
    cap(s, 600, 286, 'Slot highlights')
    for i, (n_, c) in enumerate([('number / unit  #FFE0AD', '#FFE0AD'), ('shall / should  #D5E3FF', '#D5E3FF'), ('not  #FFD3CE', '#FFD3CE'), ('condition  #E8DEFF', '#E8DEFF')]):
        s.r(600 + i * 200, 310, 190, 40, n_, fill=c, stroke=LINE, fs=10)
    cap(s, 20, 380, 'Type (IBM Plex)')
    s.t(20, 406, 'Plex Sans: interface', fs=20, color=INK)
    s.t(20, 440, 'Plex Serif: requirement text, so wording reads as a document', fs=16, color=INK, family=2)
    s.t(20, 470, 'Plex Mono: IDs and hashes   REQ-FCS-0212   3be1a07c', fs=14, color=INK, family=3)
    s.t(20, 500, 'Body 16 px · labels 14 px · captions 12 px minimum', fs=12, color=SOFT)
    cap(s, 760, 380, 'Space, shape, targets')
    for i, v in enumerate([4, 8, 12, 16, 24, 32]):
        s.r(760 + i * 70, 410, v, v, fill=ACC, stroke=ACC, rounded=False)
        s.t(760 + i * 70, 450, str(v), fs=10, family=3, color=DARK)
    s.t(760, 470, 'Radius 4 (chips), 6 (buttons), 8 (cards)', fs=12, color=DARK)
    s.r(760, 500, 44, 44, fill='#ffffff', stroke=INK, sw=2)
    s.t(816, 514, '44 px minimum touch target', fs=12, color=DARK)
    cap(s, 20, 560, 'Accessibility gates')
    gates = ['Contrast: text 4.5:1 or better (ink on surface, white on accent)', 'Status never by colour alone: word or shape always present', 'Keyboard: visible 3 px focus ring, logical order, no keyboard trap',
             'Phone 390 px: no sideways scroll', 'Dark mode: not in the prototype (listed as a gap)']
    for i, g in enumerate(gates):
        s.t(20 + (i % 2) * 720, 590 + (i // 2) * 28, '•  ' + g, fs=12, color=DARK)
    d.frame_end()


# ------------------------------------------------------------------ lens board
def lenses(d, ox, oy):
    W, H = 1500, 760
    d.frame_begin(ox, oy, W, H, 'K4 · Four-lens design review board')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill='#ffffff', stroke='#ffffff', rounded=False)
    s.t(20, 14, 'Four-lens review board: how each reviewer judges a suggestion and the UI itself', fs=24, family=1, color=INK)
    cols = [('Systems engineer', BLUE_BG, ['Each finding cites a rule and the exact text span', 'Compare subject, response, condition, value, tolerance, level, owner, allocation, verification method', 'Any difference blocks auto-merge',
                                      'Traces and allocation preserved, no orphans', 'Strictest verification method kept; linked tests flagged suspect', 'Conflicts are raised as conflicts', 'No lost coverage at set level']),
            ('Process engineer', VIOLET_BG, ['Baseline status checked before any change', 'Approving authority matches owner; cross-owner needs both', 'AI record per suggestion: model, version, prompt version, inputs, output, reviewer, decision',
                                          'AI cannot write approved fields', 'Intended use stated: no verification credit taken', 'Data classification before any external call', 'Exports carry the baseline ID and list superseded IDs']),
            ('UI/UX engineer', AMBER_BG, ['Status by text and shape, not colour alone', 'Diff, undo and confirm on consequential actions', 'Keyboard, visible focus, 44 px targets, no drag-only action', 'Grouped by cluster, safest first, progress visible',
                                       'Blind-first available for sampled items', 'Provenance visible in context', 'Consistent help in the same place on every screen']),
            ('New user', GREEN_BG, ['Can say what an "AI draft" is, and that it is not approved', 'Terms (duplicate, supersede, merge, baseline, suspect link) defined in the app', 'Consequence of Accept shown before the click',
                                 'Reject and Skip as easy as Accept; no default nudge', 'Clear where the data goes (local or external)', 'Sample data labelled as sample', 'First-run help can be dismissed'])]
    for i, (nm, f, items) in enumerate(cols):
        x = 20 + i * 365
        s.r(x, 70, 350, 40, nm, fill=f, stroke=INK, fs=14, family=1, sw=2)
        yy = 124
        for it in items:
            w_ = d.wrap(it, 296, 11)
            n = w_.count('\n') + 1
            s.r(x, yy, 350, n * 14 + 20, fill='#ffffff', stroke=LINE)
            s.r(x + 10, yy + 10, 14, 14, fill='#ffffff', stroke=INK, sw=2)
            s.t(x + 34, yy + 9, w_, fs=11, color=DARK)
            yy += n * 14 + 28
    s.t(20, 722, 'Source: reviewer-lens checklists in the research report (proposals; no external source provides an official AI-assisted requirement-review checklist).', fs=11, family=1, color=SOFT)
    d.frame_end()


# ------------------------------------------------------------------ open questions
QUESTIONS = [
    ('What exactly is "MSoSa" (probably MSOSA), which release and edition, SysML v1 or v2, and do projects live in Teamwork Cloud?', 'Ingest route: .mdzip, ReqIF, API or SysML v2 text'),
    ('What is "systems v2": a SysML v2 model, an internal name, something else? In what file format?', 'SysML v2 tooling versus ReqIF/CSV'),
    ('Which formats can each project export, and how many requirements is "massive"?', 'Parser scope, scale target, whether MinHash/ANN are needed'),
    ('Is the text CUI or export-controlled, and where may it be processed? Are any external AI APIs permitted?', 'Local-only deployment, model choice, logging'),
    ('Which review roles are required, who staffs them, and which sign-offs are binding or advisory?', 'Lens labels, block permissions, gold-set capacity'),
    ('Are requirements baselined, who owns them, does a change board govern edits? Cross-owner merges in scope?', 'Lifecycle gating, cross-owner rules'),
    ('Is the tool advisory only, or will anyone take verification credit for its output?', 'Intended-use statement and tool assessment'),
    ('Which writing conventions apply (INCOSE GtWR subset, EARS, shall/will/should) and is there a project glossary?', 'Rule baseline, slot extractor, new-user checks'),
    ('Which downstream documents are needed (SSS, SRS, IRS/ICD, SSDD, PIDS, DIDs) and are Word templates mandatory?', 'Export design: Sphinx-Needs versus Word'),
    ('What compute exists, is the network air-gapped, are internal PyPI/npm/container mirrors available? Rootless Podman on runners?', 'Model sizes, mirroring plan'),
    ('What is the licence policy: copyleft as external processes only? Non-commercial model licences acceptable?', 'Library and model shortlist'),
    ('Who will label pairs, how many reviewer-days, is English the only language?', 'Gold-set size and schedule'),
    ('How should derived or allocated requirements that repeat parent text, and equivalent requirements for different configurations, be treated?', 'Taxonomy edge cases: link, not merge'),
    ('Is LiteLLM already deployed or approved? What is the supply-chain policy for fast-moving packages?', 'Gateway choice and pinning'),
    ('Do you accept the six-label taxonomy and the stricter-versus-looser comparator rule?', 'The contract the labelling and the UI encode'),
]


def questions(d, ox, oy):
    W = 1500
    rows = []
    for q, w in QUESTIONS:
        a = d.wrap(q, 840, 12)
        b = d.wrap(w, 520, 12)
        n = max(a.count('\n'), b.count('\n')) + 1
        rows.append((a, b, n))
    H = 130 + sum(n * 15 + 22 for _, _, n in rows) + 30
    d.frame_begin(ox, oy, W, H, 'K5 · Fifteen things to confirm before building')
    s = Scr(d, ox, oy)
    s.r(0, 0, W, H, fill='#ffffff', stroke='#ffffff', rounded=False)
    s.t(20, 14, 'Fifteen answers that change what gets built', fs=24, family=1, color=INK)
    s.t(20, 52, 'From the research report. The prototype assumes sensible defaults for every one of these; none is settled.', fs=13, color=SOFT)
    s.r(20, 90, 1460, 30, fill=DARK, stroke=DARK, rounded=False)
    s.t(34, 98, '#', fs=10, color='#ffffff', family=3)
    s.t(80, 98, 'Question', fs=11, color='#ffffff')
    s.t(940, 98, 'What it decides', fs=11, color='#ffffff')
    y = 120
    for i, (a, b, n) in enumerate(rows):
        h = n * 15 + 22
        s.r(20, y, 1460, h, fill='#F8F9FA' if i % 2 else '#ffffff', stroke='#e9ecef', rounded=False)
        s.t(34, y + 10, str(i + 1), fs=12, color=RED, family=3)
        s.t(80, y + 10, a, fs=12, color=INK)
        s.t(940, y + 10, b, fs=12, color=DARK)
        y += h
    d.frame_end()
    return H


def build(path):
    d = Doc(41)
    ia(d, 0, 0)
    kit(d, 0, 880)
    tokens(d, 0, 880 + 1110 + 80)
    lenses(d, 0, 880 + 1110 + 80 + 700 + 80)
    questions(d, 0, 880 + 1110 + 80 + 700 + 80 + 760 + 80)
    d.save(path)


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else '04_ui_kit_and_IA.excalidraw')
