"""Board 08: the assistant."""
from wf2 import *
from g7 import numline


def bubble_mark(s, x, y, size=12):
    """Speech-bubble mark for assistant-origin content."""
    s.r(x, y, size, size - 2, fill=CHAT, stroke=CHAT)
    s.poly([(x + 2, y + size - 2), (x + 2, y + size + 3), (x + 6, y + size - 2)], typ='line', stroke=CHAT, sw=1.5)


def user_msg(s, x, y, w, text, fs=9):
    wr = s.d.wrap(text, w - 20, fs)
    h = (wr.count('\n') + 1) * fs * 1.3 + 14
    s.r(x + 40, y, w - 40, h, fill=GREY, stroke=LINE)
    s.t(x + 50, y + 7, wr, fs=fs, color=INK)
    return y + h + 8


def asst_msg(s, x, y, w, text, srcs=(), fs=9, tail=None):
    wr = s.d.wrap(text, w - 36, fs)
    n = wr.count('\n') + 1
    h = n * fs * 1.3 + 14 + (22 if srcs else 0) + (n2(s, tail, w - 36, fs) if tail else 0)
    s.r(x, y, w - 20, h, fill=CHAT_F, stroke=CHAT)
    bubble_mark(s, x + 8, y + 8, 10)
    s.t(x + 26, y + 7, wr, fs=fs, color=INK)
    yy = y + 7 + n * fs * 1.3
    if tail:
        wt = s.d.wrap(tail, w - 36, fs)
        s.t(x + 26, yy + 4, wt, fs=fs, color='#7a4b00')
        yy += (wt.count('\n') + 1) * fs * 1.3 + 4
    cx = x + 26
    for sr in srcs:
        wd = len(sr) * 5 + 14
        s.chip(cx, yy + 4, wd, 14, sr, fill='#ffffff', stroke=CHAT, fs=8, color=CHAT)
        cx += wd + 4
    return y + h + 8


def n2(s, t, w, fs):
    return (s.d.wrap(t, w, fs).count('\n') + 1) * fs * 1.3 + 4


def a1_drawer(d, ox, oy):
    W, H = 1000, 880
    s = new_frame(d, ox, oy, W, H, 'A1 · The assistant docks beside the work. It reads, explains and drafts. It never decides.')
    cx, cy = shell2(s, W, H, 'Review queue', 0)
    # left workspace, simplified
    s.t(cx, cy, 'CL-050 · Data retention', fs=18, family=2, color=INK)
    s.chip(cx, cy + 30, 56, 16, 'Lane B', fill=AMBER_BG, fs=9)
    s.chip(cx + 62, cy + 30, 62, 16, 'Variant', fill=VIOLET_BG, fs=9)
    s.chip(cx + 130, cy + 30, 78, 16, '6 members', fill=GREY, fs=9)
    s.card(cx, cy + 58, 456, 292)
    s.caps(cx + 12, cy + 68, 'MEMBERS')
    rows = [['M1', 'at least 30 days', '30 d', ('Comparable', GREEN_BG)], ['M2', 'at least 60 days', '60 d', ('Comparable', GREEN_BG)], ['M3', 'a minimum of 90 days', '90 d', ('Comparable', GREEN_BG)],
            ['M4', 'for 1 year', '365 d', ('Comparable', GREEN_BG)], ['M5', '30 days after landing', '30 d', ('Condition', AMBER_BG)], ['M6', 'until the next maintenance cycle', 'none', ('Not a number', RED_BG)]]
    ty = table(s, cx + 10, cy + 88, [40, 196, 54, 144], ['', 'The Data Recorder shall store…', 'Value', 'Rank'], rows, fs=9, minh=30, pad=6)
    s.t(cx + 12, ty + 6, 'Same data and the same guards as before. The assistant adds no new facts.', fs=8, color=SOFT)
    s.card(cx, cy + 364, 456, 80)
    s.caps(cx + 12, cy + 374, 'RESOLVE THIS GROUP (COLLAPSED)')
    s.btn(cx + 12, cy + 396, 190, 34, 'Open Resolve panel ▸', primary=True, fs=10)
    s.t(cx + 212, cy + 398, s.d.wrap('The only place a decision is made. The chat has no save button.', 232, 9), fs=9, color=DARK)
    s.r(cx, cy + 458, 456, 150, fill='#fff9db', stroke='#f1c40f')
    s.t(cx + 12, cy + 468, 'Facts the screen shows without the model', fs=11, family=1, color=INK)
    for i, t_ in enumerate(['Owners differ, baseline status, guard failures', 'Which members could not be ranked', 'The AI record and its quotes']):
        s.t(cx + 12, cy + 494 + i * 22, '•  ' + t_, fs=9, color='#5c4400')
    s.t(cx + 12, cy + 562, s.d.wrap('Anything critical is drawn by the interface from data. The chat explains it, but a wrong or missing chat answer cannot hide it.', 432, 9), fs=9, color='#5c4400')
    s.num(cx + 440, cy + 50, 1)
    # drawer
    dx = cx + 476
    dh = 706
    s.r(dx, cy - 4, 340, dh, fill='#ffffff', stroke=CHAT, sw=2)
    s.r(dx, cy - 4, 340, 34, fill=CHAT_F, stroke=CHAT_F, rounded=False)
    bubble_mark(s, dx + 12, cy + 8, 12)
    s.t(dx + 32, cy + 6, 'Assistant', fs=12, color=CHAT, family=2)
    s.chip(dx + 104, cy + 7, 150, 16, 'reads · drafts · never saves', fill='#ffffff', stroke=CHAT, fs=8, color=CHAT)
    s.t(dx + 318, cy + 6, '×', fs=12, color=SOFT)
    s.chip(dx + 10, cy + 38, 48, 14, 'CL-050', fs=8)
    s.chip(dx + 62, cy + 38, 52, 14, 'Lens: SE', fs=8)
    s.chip(dx + 118, cy + 38, 98, 14, 'Sees 6 requirements', fs=8)
    s.t(dx + 224, cy + 40, 'What can it see? ▸', fs=8, color=ACC)
    s.caps(dx + 10, cy + 62, 'HEADS-UP · RETRIEVED, NOT GENERATED')
    for i, t_ in enumerate(['Overlaps CL-042, decided 1 Oct by SE-2', 'Parent SYS-0310 says "at least one year"']):
        s.r(dx + 10, cy + 80 + i * 30, 320, 24, fill=AMBER_BG, stroke='#f1c40f')
        s.t(dx + 18, cy + 86 + i * 30, t_, fs=9, color='#5c4400')
        s.t(dx + 296, cy + 86 + i * 30, 'open ▸', fs=8, color=ACC)
    y = cy + 150
    y = user_msg(s, dx + 10, y, 320, 'Why did the AI pick most stringent?')
    y = asst_msg(s, dx + 10, y, 320, 'It reasoned that M1 to M3 are minimums, so M4 (1 year) also satisfies them, and it left M5 and M6 out because they differ in condition and form.', srcs=['AIR-0412', 'M3', 'M4'], tail='Not checked: whether 365 days is affordable for storage.')
    y = user_msg(s, dx + 10, y, 320, 'Has something like this been decided before?')
    y = asst_msg(s, dx + 10, y, 320, 'Yes, two earlier decisions: CL-042 (1 Oct, SE-2) merged with the strictest value, and CL-041 (30 Sep, SE-1) rejected a merge as not a duplicate.', srcs=['CL-042', 'CL-041'])
    y = user_msg(s, dx + 10, y, 320, 'Draft one wording for M1 to M4.')
    s.r(dx + 10, y, 300, 110, fill='#ffffff', stroke=CHAT, dash=True, sw=2)
    bubble_mark(s, dx + 18, y + 8, 10)
    s.caps(dx + 34, y + 8, 'DRAFT · NOT SAVED', color=CHAT)
    tokw(s, dx + 20, y + 26, 280, 'The Data Recorder shall store all fault events for at least 365 days.', fs=9, differs=('365',))
    s.t(dx + 20, y + 62, 'numbers pass · units warning (1 year = 365 d)', fs=8, color='#b35a00')
    s.btn(dx + 18, y + 78, 150, 24, 'Use as my wording', fs=9)
    s.btn(dx + 176, y + 78, 70, 24, 'Discard', fs=9)
    s.num(dx + 318, y - 2, 4)
    y += 122
    # prompts and input
    s.caps(dx + 10, y, 'QUICK PROMPTS')
    for i, t_ in enumerate(['Explain this group', 'Show differences', 'Why this suggestion?', 'Earlier decisions', 'Draft wording', 'Argue the other side']):
        s.chip(dx + 10 + (i % 3) * 108, y + 18 + (i // 3) * 24, 104, 18, t_, fs=8, color=CHAT, stroke=CHAT, fill='#ffffff')
    y += 74
    s.r(dx + 10, y, 320, 34, 'Ask about this group…', fill='#ffffff', stroke=CHAT, color=SOFT, fs=10, align='left', pad=10)
    checkbox(s, dx + 12, y + 44, False, 'Attach this chat to my decision note', fs=9)
    s.num(dx + 318, cy - 12, 2)
    s.num(dx + 318, cy + 144, 3)
    s.num(dx + 318, y - 6, 5)
    d.frame_end()
    return ['The workspace is unchanged. The drawer is optional and docks on the right, so the evidence stays visible while you talk.',
            'Context is explicit: which cluster, which lens, and what it can see. "What can it see?" lists the records the assistant is allowed to read as you.',
            'Heads-up cards are retrieved from the ledger and the traces by the application. They are not written by the model, so they are there even if you never open the chat.',
            'A draft is a proposal card. It carries a bubble mark, the guard results, and two buttons: use it as your own wording (it opens the editor), or discard. There is no "apply".',
            'Quick prompts cover the six jobs. "Argue the other side" is the guard against anchoring on whatever the assistant said first.']


def a2_scenarios(d, ox, oy):
    W, H = 1500, 820
    s = new_frame(d, ox, oy, W, H, 'A2 · Six jobs the assistant does, and what stops each from going wrong', bg='#ffffff')
    s.t(20, 14, 'Somebody over your shoulder, with a memory and a rulebook', fs=24, family=1, color=INK)
    s.t(20, 50, 'Each job is a question, the read-only tools it calls, what comes back, and the guardrail that applies.', fs=12, color=SOFT)
    cards = [('1 · Understand a requirement or group', 'What is this group about, in plain words?', ['get_cluster', 'get_requirement', 'get_glossary'],
              'Six wordings of how long the Data Recorder keeps fault events. Four are minimums (30, 60, 90, 365 days). M5 adds "after landing". M6 has no number.', ['M1', 'M2', 'M3', 'M4', 'M5', 'M6'], 'Every claim links to a record. If it cannot find a source it says so.'),
             ('2 · Decide whether it needs revising', 'Does M2 need a rewrite?', ['lint_requirement', 'get_trace', 'get_parameter_ledger'],
              'Reasons to revise: no verification method named. Reasons to keep: subject and unit are clear, and SYS-0310 asks for one year. Your call.', ['lint', 'SYS-0310'], 'It lists reasons for and against. It does not say "revise" or "keep".'),
             ('3 · Author or edit', 'Draft one wording for M1 to M4.', ['propose_wording', 'run_guards'],
              'Draft (not saved): "The Data Recorder shall store all fault events for at least 365 days." Numbers pass. Units warn: 1 year = 365 d.', ['guards', 'M4'], 'Propose only. A draft you use becomes an AI-origin revision with its own record.'),
             ('4 · Show differences', 'How do M3 and M4 differ?', ['get_diff'],
              'Value 90 d against 365 d, unit days against year, and "a minimum of" against no modifier. Subject, verb and object are the same. Open the diff view for the marked-up version.', ['M3', 'M4', 'diff'], 'Differences are computed by code. The model only narrates them.'),
             ('5 · Defend a mechanical or AI decision', 'Why was this called a variant?', ['get_scores_and_guards', 'get_ai_record'],
              'Text score 0.74, meaning score 0.81. The AI said variant because actor and object match while the value differs.', ['AIR-0412', 'scores'], 'It reports what the record says, then argues the other side: the M5 condition may make it a different requirement.'),
             ('6 · Recall earlier decisions', 'Has anyone decided this before?', ['search_decisions', 'get_history'],
              'Two earlier decisions mention fault-event retention: CL-042 (1 Oct, SE-2, strictest value) and CL-041 (30 Sep, SE-1, rejected). Neither covers these requirement IDs.', ['CL-042', 'CL-041'], 'Search is filtered by your access. It will not reveal what you cannot open.')]
    for i, (t_, q, tools, ans, srcs, guard) in enumerate(cards):
        bx, by = 20 + (i % 3) * 490, 84 + (i // 3) * 356
        s.card(bx, by, 470, 340)
        s.t(bx + 14, by + 12, t_, fs=13, color=INK)
        s.r(bx + 14, by + 42, 300, 28, fill=GREY, stroke=LINE)
        s.t(bx + 24, by + 49, '“' + q + '”', fs=10, color=INK)
        s.caps(bx + 14, by + 86, 'READ-ONLY TOOLS IT CALLS')
        cxx = bx + 14
        for tn in tools:
            wd = len(tn) * 5.6 + 14
            s.chip(cxx, by + 106, wd, 18, tn, fs=8, color=CHAT, stroke=CHAT, fill='#ffffff', )
            cxx += wd + 6
        s.caps(bx + 14, by + 142, 'WHAT COMES BACK (EXAMPLE)')
        asst_msg(s, bx + 14, by + 162, 462, ans, srcs=srcs, fs=10)
        s.r(bx + 14, by + 252, 442, 72, fill='#fff9db', stroke='#f1c40f')
        s.caps(bx + 24, by + 260, 'GUARDRAIL', color='#b35a00')
        s.t(bx + 24, by + 278, s.d.wrap(guard, 420, 10), fs=10, color='#5c4400')
        s.num(bx + 450, by - 8, i + 1)
    d.frame_end()
    return ['The two you named first, understanding and deciding whether to revise, are the most used. Neither writes anything.',
            'Authoring is propose-only. Using a draft creates an AI-origin revision (diamond) that you then edit as a human (circle), so the chain in board 07 stays truthful.',
            'Defending a decision means reading the record back, then arguing the opposite. If the model never gave a reason, the assistant says so rather than make one up.',
            'Recall is the "someone who remembers" job: prior decisions, revisions and notes you may not have seen. It is only as good as the ledger, which is why the ledger is structured.',
            'Every tool is read-only except propose_wording, which only creates a draft card. Nothing here can save, sign or export.']


def a3_architecture(d, ox, oy):
    W, H = 1500, 900
    s = new_frame(d, ox, oy, W, H, 'A3 · How it is built, and the walls around it', bg='#ffffff')
    s.t(20, 14, 'A read-only assistant with no path to the decision service', fs=24, family=1, color=INK)
    s.t(20, 50, 'It acts as the signed-in user, calls read-only tools, and talks only to models inside your boundary. Self-hosted, in the same Podman or Docker compose stack.', fs=12, color=SOFT)
    # user
    s.r(20, 90, 220, 170, fill=BLUE_BG, stroke=INK, sw=2)
    s.t(32, 98, 'Reviewer · browser', fs=12, family=1, color=INK)
    s.r(32, 128, 196, 44, 'Chat drawer', fill=CHAT_F, stroke=CHAT, color=CHAT, fs=11)
    s.r(32, 190, 196, 56, 'Resolve panel\n(the only way to decide)', fill=HUM_F, stroke=HUM, fs=10)
    # assistant service
    s.r(290, 90, 320, 330, fill=CHAT_F, stroke=CHAT, sw=2)
    s.t(302, 98, 'Assistant service', fs=12, family=1, color=CHAT)
    for i, (t_, sub) in enumerate([('Context builder', 'cluster, your lens, your access'), ('Tool router', 'picks read-only tools, bounded steps'), ('Output checks', 'IDs exist · quotes verbatim · no "saved" claims'), ('Transcript log', 'hashed, attachable on request')]):
        s.r(302, 126 + i * 72, 296, 62, fill='#ffffff', stroke=CHAT)
        s.t(312, 134 + i * 72, t_, fs=11, color=INK)
        s.t(312, 154 + i * 72, s.d.wrap(sub, 276, 9), fs=9, color=SOFT)
    # tools
    s.r(670, 90, 270, 330, fill='#ffffff', stroke=CHAT, sw=2)
    s.t(682, 98, 'Read-only tools', fs=12, family=1, color=CHAT)
    for i, tn in enumerate(['search_requirements', 'get_cluster · get_requirement', 'get_diff', 'get_scores_and_guards', 'get_ai_record', 'search_decisions · get_history', 'get_glossary · get_parameter_ledger', 'lint_requirement · get_trace']):
        s.chip(682, 126 + i * 26, 246, 20, tn, fs=9, color=CHAT, stroke=CHAT, fill='#ffffff')
    s.r(682, 340, 246, 66, fill='#ffffff', stroke=CHAT, dash=True, sw=2)
    s.t(692, 348, 'propose_wording', fs=10, color=CHAT)
    s.t(692, 366, s.d.wrap('returns a draft card only. Creates nothing in the project until a person uses it.', 228, 9), fs=9, color=SOFT)
    # data
    s.r(1000, 90, 230, 170, fill=GREY, stroke=INK, sw=2)
    s.t(1012, 98, 'Project data', fs=12, family=1, color=INK)
    s.t(1012, 124, s.d.wrap('Postgres: requirements, revisions, decisions, AI records, ledger. A vector index for similar-text search.', 206, 10), fs=10, color=DARK)
    s.chip(1012, 214, 206, 34, 'Row-level access applied as the user', fill=AMBER_BG, fs=9)
    # decision service
    s.r(20, 470, 220, 150, fill=HUM_F, stroke=HUM, sw=2)
    s.t(32, 478, 'Decision service', fs=12, family=1, color=INK)
    s.t(32, 504, s.d.wrap('save decision · sign · reopen · export. Checks roles, policy and guards. Writes the hash-chained audit.', 196, 10), fs=10, color=DARK)
    # litellm
    s.r(670, 470, 270, 90, fill=MECH_F, stroke=MECH, sw=2)
    s.t(682, 478, 'LiteLLM gateway', fs=12, family=1, color=INK)
    s.t(682, 502, s.d.wrap('one place for model routing, keys, budgets, logs and a block on external hosts', 246, 10), fs=10, color=DARK)
    s.r(1000, 470, 230, 90, fill=MECH_F, stroke=MECH, sw=2)
    s.t(1012, 478, 'Models inside your boundary', fs=11, family=1, color=INK)
    s.t(1012, 502, s.d.wrap('local or approved hosts only when data is controlled', 206, 10), fs=10, color=DARK)
    # arrows
    s.poly([(228, 150), (290, 150)], stroke=CHAT, sw=2)
    s.t(232, 134, 'user token', fs=8, color=SOFT)
    s.poly([(610, 250), (670, 250)], stroke=CHAT, sw=2)
    s.poly([(940, 180), (1000, 180)], stroke=CHAT, sw=2)
    s.poly([(450, 420), (450, 515), (670, 515)], stroke=CHAT, sw=2)
    s.poly([(940, 515), (1000, 515)], stroke=MECH, sw=2)
    s.poly([(130, 246), (130, 470)], stroke=HUM, sw=2)
    s.t(140, 330, 'user acts here, directly', fs=9, color=HUM)
    # the wall
    s.poly([(340, 420), (340, 540), (240, 540)], stroke=RED, sw=3, dash=True)
    s.shape('ellipse', 328, 468, 24, 24, 'X', fs=11, fill=RED, stroke=RED, color='#ffffff', pad=0)
    s.r(252, 552, 200, 56, fill='#fff5f5', stroke=RED, dash=True)
    s.t(262, 558, s.d.wrap('No credentials. The assistant cannot call the decision service.', 180, 9), fs=9, color=RED)
    s.num(1210, 82, 1)
    # bottom: injection and eval
    s.r(20, 650, 700, 220, fill='#fff9db', stroke='#f1c40f')
    s.t(34, 660, 'Requirement text is data, not instructions', fs=13, family=1, color=INK)
    for i, t_ in enumerate(['Requirement text is passed inside a marked block and labelled untrusted. The prompt says to ignore commands found in it.', 'Tools are read-only, so an injected "approve this" has nothing to call.', 'Output checks reject answers that cite IDs that do not exist or quotes that are not verbatim.', 'A planted-instruction test set runs in CI with every release.']):
        s.t(34, 690 + i * 40, '•  ' + s.d.wrap(t_, 660, 10), fs=10, color='#5c4400')
    s.num(700, 642, 2)
    s.r(740, 650, 740, 220, fill='#e3f4fb', stroke=CHAT)
    s.t(754, 660, 'The assistant is tested like any other model', fs=13, family=1, color=INK)
    for i, t_ in enumerate(['A fixed question set per project type, with the records each answer must cite.', 'Measured every release: citation accuracy, refusals when there is no source, and injection resistance.', 'A regression in any of these blocks the release, the same as a failing guard test.', 'Questions, answers and sources opened are logged so the team can see where it is not helping.']):
        s.t(754, 690 + i * 40, '•  ' + s.d.wrap(t_, 700, 10), fs=10, color=DARK)
    s.num(1460, 642, 3)
    # guardrail list right
    s.r(1250, 90, 230, 330, fill='#ffffff', stroke=INK, sw=2)
    s.t(1262, 98, 'Eight rules', fs=12, family=1, color=INK)
    for i, t_ in enumerate(['Read-only. No save, sign or export', 'Acts as the user. Sees only what they can open', 'Models inside the boundary for controlled data', 'Cites a record for every project fact', 'Respects blind-first for the AI verdict', 'No yes/no verdict on a decision', 'Requirement text is untrusted', 'Every call is logged']):
        s.t(1262, 126 + i * 36, str(i + 1) + '  ' + s.d.wrap(t_, 200, 9), fs=9, color=DARK)
    s.num(1460, 82, 4)
    d.frame_end()
    return ['Left to right: the reviewer, the assistant service, its read-only tools, and the project data. Row-level access is applied as the signed-in user.',
            'The prompt-injection answer is structural: the model can only call read-only tools, so there is nothing to hijack. Prompt wording is the second line, not the first.',
            'The assistant has its own test set and is measured every release like the AI judge. Without that, "helpful" is only a feeling.',
            'The red dashed wall is the most important line on the board. The decision service is a different service and the assistant has no key to it.']


def a4_effects(d, ox, oy):
    W, H = 1500, 700
    s = new_frame(d, ox, oy, W, H, 'A4 · What adding the assistant changes in the design, and the new risks', bg='#ffffff')
    s.t(20, 14, 'It changes seven things. It does not change who decides.', fs=24, family=1, color=INK)
    s.t(20, 50, 'Each row is something already in boards 01 to 08 that moves, the new risk that creates, and what we do about it.', fs=12, color=SOFT)
    rows = [['Provenance', 'Three marks: computed, AI, human.', 'A fourth mark, the bubble, for chat text. A draft you use becomes an AI-origin revision (diamond). Your edits after that are human (circle).', 'Text laundered through chat looks human-written.', 'Use as my wording creates an AI revision with its own record. The AI-share bucket is computed from the text, the same as board 07.'],
            ['Blind-first', 'The AI panel stays hidden until you record your own call.', 'The assistant follows the same rule. It can explain the evidence, but not reveal the AI verdict until you have made your call.', 'The chat becomes a back door around blind-first.', 'The rule is enforced in the tool layer (get_ai_record is refused), not in the prompt.'],
            ['Anchoring', 'The reviewer forms a view from the evidence.', 'A fluent answer can set your view before you have looked.', 'Automation bias. A confident wrong answer.', 'Evidence before verdict. Every answer cites sources and says what it did not check. "Argue the other side" is one click. No yes/no verdicts.'],
            ['Audit trail', 'Decisions, notes, AI records, the hash chain.', 'Chat transcripts are stored hashed, with the records each answer used. They attach to a decision only if you choose.', 'The chat becomes an unreviewed side channel.', 'Attaching is explicit. The decision refers to the excerpt, not the other way round. Retention is a project setting.'],
            ['Security and data', 'Local models, ten guards, role checks.', 'A new surface that reads every record and takes free text.', 'Prompt injection from requirement text. Privilege escalation. Data leaving the boundary.', 'Untrusted-text block, read-only tools, access applied as the user, models only inside the boundary for controlled data, no web access.'],
            ['Cost and speed', 'A batch AI run, once per import.', 'Interactive calls all day.', 'Latency and contention on a shared GPU.', 'A small local model by default, caching by content hash, per-user rate limits, and a larger model only on request.'],
            ['Quality of the assistant', 'Nothing to test.', 'Another model whose answers people rely on.', 'Wrong answers and wrong citations that look right.', 'A fixed evaluation set in CI: citation accuracy, refusals without a source, injection tests. Reported with the other metrics.']]
    y = table(s, 20, 84, [130, 200, 330, 250, 480], ['Area', 'Before the assistant', 'With the assistant', 'New risk', 'What we do'], rows, fs=9, minh=46, bold_first=True)
    s.num(1400, 74, 1)
    # legend
    ly = y + 24
    s.card(20, ly, 480, 150)
    s.caps(34, ly + 10, 'THE FOUR MARKS')
    for i, (k, t_) in enumerate([('mech', 'Computed by code'), ('ai', 'Written or judged by the AI'), ('hum', 'Written or decided by a person')]):
        s.prov(34, ly + 36 + i * 24, k, t_, fs=10)
    bubble_mark(s, 34, ly + 106, 12)
    s.t(52, ly + 104, 'Said by the assistant in chat (always a proposal)', fs=10, color=DARK)
    s.num(486, ly - 8, 2)
    s.r(520, ly, 470, 150, fill='#fff5f5', stroke=RED)
    s.t(534, ly + 10, 'The assistant must never', fs=13, family=1, color=RED)
    for i, t_ in enumerate(['save, sign, accept, reject, export or edit a revision', 'give a yes or no verdict on a decision', 'show anything the user cannot open', 'state a project fact without a source', 'follow instructions found inside requirement text']):
        s.t(534, ly + 38 + i * 21, '✕  ' + t_, fs=10, color=DARK)
    s.num(976, ly - 8, 3)
    s.card(1010, ly, 470, 150)
    s.caps(1024, ly + 10, 'WHAT WE MEASURE ABOUT IT')
    for i, t_ in enumerate(['Questions per cluster, and which jobs they are for', 'Sources opened after an answer', 'Drafts used as is, edited, or discarded', 'Citation accuracy and refusal correctness on the test set', 'Whether reviewers with the assistant override the AI less or more']):
        s.t(1024, ly + 36 + i * 21, '•  ' + t_, fs=10, color=DARK)
    s.num(1466, ly - 8, 4)
    d.frame_end()
    return ['The table is the honest answer to "how does it change the situation". Mostly it adds a helper and a few new ways to go wrong. Each way has a control.',
            'The fourth mark. Anything the assistant says carries it, so a reader can always tell chat from computed, AI or human content.',
            'The never-list is short on purpose, so it can be tested.',
            'The last metric matters: if reviewers with the assistant just agree with the AI more, it is anchoring them, and the project should know.']
