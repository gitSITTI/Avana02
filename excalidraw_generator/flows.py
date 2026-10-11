"""System flows: pipeline swimlanes, decision state machine, components, review-session sequence."""
from wf import *
from exc import Doc, INK

MECH_F = '#e7ecf0'
AI_F = '#f6e4ef'
HUM_F = '#e1f2e7'
GUARD_F = '#fff3bf'
SRC_F = '#d0ebff'


def box(d, x, y, w, h, label, fill, stroke=INK, fs=12, dash=False, sw=2, **kw):
    return d.rect(x, y, w, h, label, fill=fill, stroke=stroke, fs=fs, dash=dash, sw=sw, **kw)


def mark(d, x, y, kind):
    if kind == 'mech':
        d.rect(x, y, 10, 10, fill=MECH, stroke=MECH, rounded=False)
    elif kind == 'ai':
        d.shape('diamond', x - 1, y - 1, 13, 13, fill=AIC, stroke=AIC)
    else:
        d.shape('ellipse', x, y, 11, 11, fill=HUM, stroke=HUM)


def lane(d, x, y, w, h, title, kind, fill):
    d.rect(x, y, w, h, fill=fill, stroke='#ced4da', rounded=False, sw=1)
    d.rect(x, y, 150, h, fill='#ffffff', stroke='#ced4da', rounded=False, sw=1)
    mark(d, x + 12, y + 14, kind) if kind else None
    d.text(x + (30 if kind else 12), y + 10, title, fs=14, family=1, color=INK)


def flow_pipeline(d, ox, oy):
    W, H = 2000, 900
    d.frame_begin(ox, oy, W, H, 'A · End-to-end pipeline: mechanical first, AI late, human last')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Who does what, in order', fs=24, family=1)
    lanes = [('Sources', None, '#f8fbff', 60, 120), ('Mechanical', 'mech', '#f4f6f8', 180, 150), ('AI', 'ai', '#fcf3f9', 330, 130),
             ('Code guards', 'mech', '#fffbe6', 460, 110), ('Human', 'human', '#f1faf4', 570, 150), ('Record', None, '#ffffff', 720, 130)]
    for t_, k, f, ly, lh in lanes:
        lane(d, X + 20, Y + ly, W - 40, lh, t_, k, f)
    cx0 = X + 200
    st = 170
    srcs = [box(d, cx0 + i * st, Y + 80, 150, 80, t_, SRC_F, fs=11, dash=(i == 2)) for i, t_ in enumerate(
        ['SysML v2 API\nor KPAR / .sysml', 'ReqIF 1.2 export\nfrom MSOSA', '.mdzip (zipped XMI)\nexperimental', 'CSV / XLSX\nfallback'])]
    ing = box(d, cx0 + 1.5 * st - 25, Y + 195, 200, 56, 'Ingest adapters\nmap fields to fixed UI slots', MECH_F, fs=11)
    for s_ in srcs:
        d.connect(s_, ing, 'b', 't', color=SOFT, sw=1)
    labels = ['Normalise, extract slots\nnumbers, units, modals, not', 'Collapse exact and\nnear-exact copies', 'Lexical candidates\nfuzzy, TF-IDF, MinHash', 'Embedding\nshortlist',
              'Cross-encoder and NLI\nboth directions', 'Calibrated combiner\ndraft probability']
    prev = ing
    chain = []
    for k, t_ in enumerate(labels):
        el = box(d, cx0 + (3 + k) * st, Y + 264, 156, 56, t_, MECH_F, fs=10)
        d.connect(prev, el, 'r' if k else 'b', 'l' if k else 't') if k else d.connect(prev, el, 'r', 'l')
        prev = el
        chain.append(el)
    clus = box(d, cx0 + 9 * st, Y + 264, 186, 56, 'Cluster, label relationship,\nassign lane A / B / C', MECH_F, fs=10)
    d.connect(prev, clus, 'r', 'l')
    judge = box(d, clus['x'], Y + 350, 186, 80, 'AI judge: uncertain band only\nverdict + verbatim quotes\n3 runs, both A-B orders', AI_F, stroke=AIC, fs=10)
    draft = box(d, clus['x'] - 230, Y + 350, 200, 80, 'AI wording draft\nLane A only, never for\nvariants or conflicts', AI_F, stroke=AIC, fs=10)
    d.connect(clus, judge, 'b', 't', label='uncertain', fs=11, lx=34)
    d.connect(clus, draft, 'b', 't', dash=True, color=AIC)
    d.text(X + 200, Y + 380, 'Clusters the mechanical methods already settle are not sent to the AI.', fs=13, family=1, color=SOFT)
    guards = box(d, clus['x'], Y + 485, 186, 60, 'Ten code guards\nnumbers, units, shall, not...', GUARD_F, stroke='#b35a00', fs=10)
    d.connect(judge, guards, 'b', 't', label='every proposal', fs=11, lx=48)
    d.connect(draft, guards, 'b', 'l', color=AIC)
    review = box(d, clus['x'], Y + 600, 186, 76, 'Review queue\nblind-first option\nconsequences stated', HUM_F, stroke=HUM, fs=10)
    d.connect(guards, review, 'b', 't', label='pass / warn / block', fs=11, lx=60)
    sign = box(d, clus['x'] - 290, Y + 600, 200, 76, 'Four-lens sign-off\nSE · PE · UX · NU', HUM_F, stroke=HUM, fs=10)
    d.connect(review, sign, 'l', 'r', label='decide', fs=11)
    exp = box(d, clus['x'] - 620, Y + 600, 220, 76, 'Draft package\nSphinx-Needs · StrictDoc\nWord · ReqIF', HUM_F, stroke=HUM, fs=10)
    d.connect(sign, exp, 'l', 'r', label='4 of 4', fs=11)
    audit = box(d, X + 200, Y + 748, W - 260, 74, 'Append-only audit log: every suggestion, guard result, decision, undo, sign-off and export is an event\nEach event stores the hash of the one before it, so an edit to history is detectable', '#ffffff', stroke=INK, fs=12)
    for el in (review, sign, exp):
        d.connect(el, audit, 'b', 't', dash=True, color=SOFT, sw=1)
    d.text(X + 200, Y + 836, 'Mechanical methods never write to approved fields. The AI never writes either. Only a human decision does.', fs=14, family=1, color=RED)
    d.frame_end()
    return audit


def flow_states(d, ox, oy):
    W, H = 1700, 760
    d.frame_begin(ox, oy, W, H, 'B · Life of one suggestion (state machine)')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Life of one cluster: a suggestion is a draft until four lenses sign', fs=24, family=1)
    s1 = box(d, X + 60, Y + 280, 200, 90, 'SUGGESTED\ndraft, nobody has decided', '#ffffff', fs=14, sw=2, dash=True)
    s2 = box(d, X + 440, Y + 280, 200, 90, 'IN REVIEW\nhuman decided,\nwaiting for lenses', '#e8f0fd', fs=14)
    s3 = box(d, X + 820, Y + 280, 200, 90, 'APPROVED\nall four lenses signed', GREEN_BG, stroke=HUM, fs=14)
    s4 = box(d, X + 1200, Y + 280, 220, 90, 'IN DRAFT PACKAGE\nprepared for a baseline ID', BLUE_BG, fs=14)
    d.connect(s1, s2, 'r', 'l', label='human decides', fs=13)
    d.connect(s2, s3, 'r', 'l', label='4 lens sign-offs', fs=13)
    d.connect(s3, s4, 'r', 'l', label='prepare package', fs=13)
    rej = box(d, X + 20, Y + 520, 170, 70, 'REJECTED\nstays as written', '#ffffff', fs=13)
    esc = box(d, X + 250, Y + 520, 200, 70, 'ESCALATED\nquestion sent to owners', AMBER_BG, fs=13)
    skip = box(d, X + 60, Y + 100, 200, 60, 'SKIPPED\nstays Suggested', '#ffffff', fs=13, dash=True)
    blk = box(d, X + 330, Y + 90, 280, 80, 'GUARD BLOCKS MERGE\nmerge action is not offered;\nlink, ask, reject, skip remain', RED_BG, stroke=RED, fs=12)
    d.connect(s1, rej, 'b', 't', label='reject', fs=12, lx=-26)
    d.connect(s1, esc, 'b', 't', label='ask owners', fs=12, lx=26, dash=True)
    d.connect(s1, skip, 't', 'b', label='skip', fs=12, lx=-22)
    d.text(X + 330, Y + 178, 'the merge button is simply absent from the card', fs=12, family=1, color=RED)
    und = box(d, X + 470, Y + 520, 280, 90, 'UNDO\nfrom any later state: a new audit\nevent returns the cluster to Suggested\n(history is never deleted)', '#ffffff', fs=12, dash=True)
    d.connect(s2, und, 'b', 't', dash=True)
    b1 = box(d, X + 880, Y + 100, 330, 110, 'Cross-owner change:\nboth owners must approve.\nBaselined requirement: needs a\nchange request outside this tool.', '#fff9db', stroke='#f1c40f', fs=12)
    d.connect(b1, s2, 'l', 't', dash=True, color='#b35a00')
    b2 = box(d, X + 1000, Y + 470, 600, 170, 'Rules that never change\n1  AI output cannot write to approved fields\n2  Variants and conflicts are never auto-merged\n3  Skip is always available\n4  Undo adds an event, never deletes one\n5  Every transition is one audit event', '#ffffff', stroke=INK, fs=13, align='left', valign='middle', pad=16)
    d.frame_end()


def flow_components(d, ox, oy):
    W, H = 1500, 860
    d.frame_begin(ox, oy, W, H, 'C · Self-hosted components (no Kubernetes)')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Self-hosted on one box or a small cluster: Podman or Docker Compose, GitLab CI', fs=24, family=1)
    d.text(X + 20, Y + 50, 'Names are suggested defaults, each swappable. Requirement text stays on your machines unless you choose a remote model.', fs=13, family=2, color=SOFT)
    d.rect(X + 340, Y + 100, 1100, 590, fill='#fbfbfd', stroke=SOFT, dash=True, sw=2, rounded=True)
    d.text(X + 356, Y + 108, 'Podman / Docker Compose stack', fs=16, family=1, color=SOFT)
    ui = box(d, X + 380, Y + 140, 280, 80, 'Web UI\nReact + TypeScript\n(this wireframe set)', SRC_F, fs=13)
    api = box(d, X + 380, Y + 270, 280, 90, 'API service\nPython (FastAPI)\nauth, decisions, exports, audit chain', MECH_F, fs=13)
    wk = box(d, X + 380, Y + 410, 280, 90, 'Pipeline workers\nnormalise, candidates, NLI,\ncluster, guards, AI-judge batch', MECH_F, fs=13)
    gw = box(d, X + 380, Y + 550, 280, 90, 'Model gateway\nLiteLLM: routing, logging, budgets', AI_F, stroke=AIC, fs=13)
    db = box(d, X + 800, Y + 240, 280, 150, 'Postgres + pgvector\nrequirements, pairs, clusters,\ndecisions, sign-offs,\nhash-chained audit events', '#ffffff', fs=13)
    obj = box(d, X + 800, Y + 410, 280, 90, 'Object store\nsource snapshots and exports\n(MinIO or plain disk)', '#ffffff', fs=13)
    mdl = box(d, X + 800, Y + 550, 280, 90, 'Local model server\nembeddings, NLI, AI judge', AI_F, stroke=AIC, fs=13)
    d.connect(ui, api, 'b', 't', label='REST', fs=12, lx=20)
    d.connect(api, wk, 'b', 't', label='jobs', fs=12, lx=20)
    d.connect(wk, gw, 'b', 't', label='judge, embed', fs=12, lx=44, color=AIC)
    d.connect(api, db, 'r', 'l')
    d.connect(wk, db, 'r', 'l')
    d.connect(wk, obj, 'r', 'l')
    d.connect(gw, mdl, 'r', 'l', color=AIC)
    ain = box(d, X + 20, Y + 375, 260, 160, 'Ingest adapters\nSysML v2 API client\nReqIF 1.2 parser\n.sysml / KPAR reader\nCSV / XLSX, .mdzip (exp.)', SRC_F, fs=12)
    aout = box(d, X + 20, Y + 190, 260, 170, 'Export adapters\nSphinx-Needs (rst)\nStrictDoc (sdoc)\nWord from template\nReqIF 1.2', HUM_F, stroke=HUM, fs=12)
    ext = box(d, X + 20, Y + 590, 260, 90, 'MSOSA / systems v2\nonline models\nread-only to this tool', '#ffffff', fs=12, dash=True)
    d.connect(ain, wk, 'r', 'l', color=SOFT, label='read', fs=12)
    d.connect(api, aout, 'l', 'r', color=SOFT, label='write', fs=12, ly=-2)
    d.connect(ext, ain, 't', 'b', dash=True, color=SOFT)
    box(d, X + 340, Y + 730, 1100, 80, 'GitLab CI:  lint and type-check  ·  unit and guard tests  ·  golden-set regression  ·  Podman build  ·  registry  ·  compose deploy', '#fff9db', stroke='#f1c40f', fs=13)
    d.frame_end()


def seq(d, x, y, xs, names, steps, h):
    for nx, nm in zip(xs, names):
        box(d, nx - 80, y, 160, 44, nm, '#ffffff', fs=12)
        d.line([(nx, y + 44), (nx, y + h)], stroke=LINE, sw=1, dash=True)
    yy = y + 80
    for fr, to, label, dash in steps:
        a, b = xs[fr], xs[to]
        if a == b:
            d.poly([(a, yy), (a + 40, yy), (a + 40, yy + 22), (a, yy + 22)], stroke=INK, sw=2, dash=dash)
            d.text(a + 48, yy + 2, label, fs=12, family=2, color=DARK)
            yy += 48
            continue
        d.poly([(a, yy), (b, yy)], stroke=AIC if (fr in (4,) or to in (4,)) else INK, sw=2, dash=dash)
        mx = (a + b) / 2
        w = len(label) * 12 * 0.5
        d.text(mx - w / 2, yy - 18, label, fs=12, family=2, color=DARK)
        yy += 42
    return yy


def flow_sequence(d, ox, oy):
    W, H = 1700, 1000
    d.frame_begin(ox, oy, W, H, 'D · One review, step by step (sequence)')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'One cluster reviewed in blind-first mode', fs=24, family=1)
    names = ['Reviewer', 'Web UI', 'API', 'Stored evidence\n(mechanical)', 'AI judge\n(via gateway)', 'Guards', 'Audit log']
    xs = [X + 140 + i * 235 for i in range(7)]
    steps = [(0, 1, 'open cluster CL-03', False), (1, 2, 'GET cluster', False), (2, 3, 'scores, tokens, guards, impact', False), (3, 2, 'precomputed evidence', True),
             (2, 1, 'evidence, AI proposal withheld', True), (0, 1, 'records own call first', False), (1, 2, 'POST blind call', False), (2, 6, 'event: blind call (human)', False),
             (2, 1, 'reveal AI verdict and quotes', True), (0, 1, 'reads both, ticks read box, decides', False), (1, 2, 'POST decision', False), (2, 5, 're-run guards on any edit', False),
             (5, 2, 'pass / warn / block', True), (2, 6, 'event: decision + hash of previous', False), (0, 1, 'each lens signs, in turn', False), (2, 6, 'event: sign-off x4', False),
             (2, 1, 'state: Approved', True)]
    end = seq(d, X + 0, Y + 70, xs, names, steps, 860)
    d.text(X + 20, Y + H - 50, 'The AI judge is called during the batch run, not during the review. The review reads stored results, so it is fast and reproducible.', fs=14, family=1, color=RED)
    d.frame_end()


def build(path):
    d = Doc(31)
    flow_pipeline(d, 0, 0)
    flow_states(d, 0, 1000)
    flow_components(d, 0, 1860)
    flow_sequence(d, 0, 2840)
    d.save(path)
    return d


if __name__ == '__main__':
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else '03_system_flows.excalidraw')
