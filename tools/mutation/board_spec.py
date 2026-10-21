"""Mutation run for the JSON board compiler (excalidraw_generator/board_spec.py): each rule it promises is broken in a copy, one at a time, and tools/test_board_spec.py must fail.

An agent that cannot run code is told "if the checker says ok, the board is sound", so a rule in the checker or the layout that no test can fail is a board that goes out wrong.

Usage: python3 tools/mutation/board_spec.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed and is not listed as harmless. See README.md in this folder."""
import atexit, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MUT = tempfile.mkdtemp(prefix='reqin-mutation-boardspec-')
atexit.register(shutil.rmtree, MUT, True)
F = 'excalidraw_generator/board_spec.py'


def reset():
    shutil.rmtree(MUT, ignore_errors=True)
    os.makedirs(MUT + '/tools')
    shutil.copytree(REPO + '/excalidraw_generator', MUT + '/excalidraw_generator', ignore=shutil.ignore_patterns('__pycache__', 'node_modules', 'bundle.js'))
    shutil.copy(REPO + '/tools/test_board_spec.py', MUT + '/tools/test_board_spec.py')


def run():
    r = subprocess.run([sys.executable, '-m', 'pytest', 'tools/test_board_spec.py', '-q', '-x', '-p', 'no:cacheprovider'], cwd=MUT, capture_output=True, text=True, timeout=300)
    last = [l for l in (r.stdout + r.stderr).strip().splitlines() if l.strip()]
    return r.returncode != 0, (last[-1] if last else '')


MUTS = [
 # ---- the checker
 ('a blank text passes', F, "if not isinstance(v, str) or not v.strip():", "if not isinstance(v, str):"),
 ('text over its length limit passes', F, "        if len(v) > opt.get(\"maxlen\", 400):\n            bad(", "        if False:\n            bad("),
 ('true counts as a whole number', F, "        if not isinstance(v, int) or isinstance(v, bool):\n            return bad(f\"must be a whole number, not {_kind(v)}\")", "        if not isinstance(v, int):\n            return bad(f\"must be a whole number, not {_kind(v)}\")"),
 ('a whole number out of its range passes', F, "if not opt.get(\"lo\", -10**9) <= v <= opt.get(\"hi\", 10**9):", "if False:"),
 ('a number out of its range passes', F, "if not opt.get(\"lo\", -1e9) <= v <= opt.get(\"hi\", 1e9):", "if False:"),
 ('true counts as a number', F, "num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)", "num = lambda x: isinstance(x, (int, float))"),
 ('a yes/no field takes anything', F, "        if not isinstance(v, bool):\n            bad(f\"must be true or false", "        if False:\n            bad(f\"must be true or false"),
 ('a word that is not one of the choices passes', F, "        if v not in opt[\"values\"]:", "        if False:"),
 ('an id may have anything after its first characters', F, "ID_RE.fullmatch(v)", "ID_RE.match(v)"),
 ('y takes any text', F, "        if not isinstance(v, int) or isinstance(v, bool):\n            return bad('must be a whole number or the word \"same\"')", "        if False:\n            return bad('must be a whole number or the word \"same\"')"),
 ('y may be any number', F, "        if not opt[\"lo\"] <= v <= opt[\"hi\"]:", "        if False:"),
 ('an empty list of headings passes', F, "        if not isinstance(v, list) or not v:\n            return bad(\"must be a non-empty list\")\n        if len(v) > opt.get(\"maxn\", 50):", "        if not isinstance(v, list):\n            return bad(\"must be a non-empty list\")\n        if len(v) > opt.get(\"maxn\", 50):"),
 ('a list may have any number of entries', F, "        if len(v) > opt.get(\"maxn\", 50):", "        if False:"),
 ('a table may have any number of rows', F, "        if len(v) > opt.get(\"maxn\", 60):", "        if False:"),
 ('a row that is not a list passes', F, "            if not isinstance(row, list) or not row:", "            if False:"),
 ('a very long cell passes', F, "                    if len(c) > 300:", "                    if False:"),
 ('a cell with a colour outside the palette passes', F, "c.get(\"tone\", \"white\") not in TONES", "False"),
 ('a cell with other keys passes', F, "extra = set(c) - {\"text\", \"tone\"}\n                    if extra or ", "extra = set(c) - {\"text\", \"tone\"}\n                    if "),
 ('a number as a cell passes', F, "                else:\n                    errs.append(f\"{cp}: a cell is text,", "                elif False:\n                    errs.append(f\"{cp}: a cell is text,"),
 ('a checklist line may carry other keys', F, "or set(c) != {\"state\", \"text\"}", "or False"),
 ('a checklist state may be anything', F, "or c[\"state\"] not in STATES", "or False"),
 ('a checklist may have any number of lines', F, "        if len(v) > opt.get(\"maxn\", 30):", "        if False:"),
 ('an item may have any number of items', F, "        if len(v) > (MAX_FRAMES if kind == \"frames\" else MAX_ITEMS):", "        if False:"),
 ('a board with no frames passes', F, "        if kind == \"frames\" and not v:", "        if False:"),
 ('an item type that is not a string crashes the checker', F, "if not isinstance(t, str) or t not in ITEMS:", "if t not in ITEMS:"),
 ('an item may have fields it does not define', F, "        if unknown:\n            errs.append(f\"{path}: {t} has no field", "        if False:\n            errs.append(f\"{path}: {t} has no field"),
 ('a frame may have fields it does not define', F, "        if unknown:\n            errs.append(f\"{path}: a frame has no field", "        if False:\n            errs.append(f\"{path}: a frame has no field"),
 ('the board may have fields it does not define', F, "    if unknown:\n        errs.append(f\"the board has no field", "    if False:\n        errs.append(f\"the board has no field"),
 ('a missing required field is not noticed', F, "        elif req:\n            errs.append(", "        elif False:\n            errs.append("),
 ('active and lens are accepted without the app chrome', F, "if fr.get(\"chrome\", \"none\") == \"none\" and (", "if False and ("),
 ('an arrow may carry a position', F, "NO_COMMON = {\"arrow\": {\"x\", \"y\", \"callout\"}, ", "NO_COMMON = {\"arrow\": set(), "),
 ('a callout item may carry a callout', F, "\"callout\": {\"callout\"}}", "\"callout\": set()}"),
 ('items may nest without limit', F, "if path.count(\".items[\") > MAX_DEPTH:", "if False:"),
 ('the depth limit is one too many', F, "if path.count(\".items[\") > MAX_DEPTH:", "if path.count(\".items[\") > MAX_DEPTH + 1:"),
 # ---- laying out
 ('a table whose widths do not match its head is drawn', F, "        if len(widths) != len(head):\n            c.errors.append(", "        if False:\n            c.errors.append("),
 ('a row with the wrong number of cells is drawn', F, "        bad = [i for i, r in enumerate(rows) if len(r) != len(head)]", "        bad = []"),
 ('two boxes may share an id', F, "            if bid in c.box_paths:\n                c.errors.append(", "            if False:\n                c.errors.append("),
 ('an arrow to a box that is not there is not noticed', F, "                if it[end] not in c.box_paths:", "                if False:"),
 ('only the start of an arrow is checked', F, "for end in (\"from\", \"to\"):", "for end in (\"from\",):"),
 ('a frame with errors is still drawn', F, "        if errors:\n            continue\n        s = new_frame", "        if False:\n            continue\n        s = new_frame"),
 ('the seed in the spec is ignored', F, "d = Doc(spec.get(\"seed\") or _seed_of(spec[\"title\"]))", "d = Doc(_seed_of(spec[\"title\"]))"),
 ('the seed made from the title is the same for every title', F, "return zlib.crc32(title.encode(\"utf-8\")) % (2**31 - 1) + 1", "return 1234"),
 ('no gap between items', F, "cur = max(cur, y + n.h + GAP)", "cur = max(cur, y + n.h)"),
 ('same is the same as leaving y out', F, "        elif y == \"same\":\n            y = prev.y if prev else cur", "        elif False:\n            y = prev.y if prev else cur"),
 ('a row does not wait for its tallest item', F, "            if it.get(\"y\") is None or it.get(\"y\") == \"same\":\n                cur = max(cur, y + n.h + GAP)", "            if it.get(\"y\") is None:\n                cur = max(cur, y + n.h + GAP)"),
 ('an item with a fixed y pushes the stack down', F, "            if it.get(\"y\") is None or it.get(\"y\") == \"same\":\n                cur = max(cur, y + n.h + GAP)", "            if True:\n                cur = max(cur, y + n.h + GAP)"),
 ('an item to the right keeps the full width', F, "n = _node(it, f\"{path}[{i}]\", max(40, avail - x), c)", "n = _node(it, f\"{path}[{i}]\", max(40, avail), c)"),
 ('a card has no space at the bottom', F, "h = it.get(\"h\") or max(60, bottom + 2 * CARD_PAD_Y)", "h = it.get(\"h\") or max(60, bottom + CARD_PAD_Y)"),
 ('a card draws what is in it against its edge', F, "_draw(inner, s, X + CARD_PAD_X, Y + CARD_PAD_Y, c)", "_draw(inner, s, X, Y, c)"),
 ('a card is not asked to hold its items inside it', F, "w - 2 * CARD_PAD_X, c)\n        h = it.get", "w, c)\n        h = it.get"),
 ('content starts on top of the sidebar', F, "ox, oy_ = (180, 76) if app else (36, 24)", "ox, oy_ = (100, 76) if app else (36, 24)"),
 ('an app frame can be short', F, "H = fr.get(\"height\") or max(520 if app else 200,", "H = fr.get(\"height\") or max(0 if app else 200,"),
 ('the chosen sidebar entry is ignored', F, "shell2(s, W, H, fr.get(\"active\", \"Review queue\"), lens=fr.get(\"lens\", 0))", "shell2(s, W, H, \"Review queue\", lens=fr.get(\"lens\", 0))"),
 ('the chosen lens is ignored', F, "shell2(s, W, H, fr.get(\"active\", \"Review queue\"), lens=fr.get(\"lens\", 0))", "shell2(s, W, H, fr.get(\"active\", \"Review queue\"), lens=0)"),
 # ---- the warnings that stand in for looking at the picture
 ('nothing is said when an item runs off the right edge', F, "or ax + n.w > content[2] + 1 or", "or False or"),
 ('nothing is said when an item runs off the bottom', F, "or ay + n.h > content[3] + 1:", "or False:"),
 ('nothing is said when an item runs off the left edge', F, "if ax < content[0] - 1 or", "if False or"),
 ('nothing is said when an item runs off the top', F, "or ay < content[1] - 1 or", "or False or"),
 ('overlapping items are not noticed', F, "            if inter and not _contains(ra, rb) and not _contains(rb, ra):", "            if False:"),
 ('a card round something counts as an overlap', F, "            if inter and not _contains(ra, rb) and not _contains(rb, ra):", "            if inter:"),
 ('overlaps inside a card are not looked for', F, "        if n.kids:\n            _overlaps(n.kids, c)", "        if False:\n            _overlaps(n.kids, c)"),
 ('items wider than their card are not noticed', F, "if k.kind not in (\"arrow\", \"callout\") and k.w and k.x + k.w > w - 2 * CARD_PAD_X + 1:", "if False:"),
 ('a card too short for its items is not noticed', F, "if it.get(\"h\") and bottom + 2 * CARD_PAD_Y > it[\"h\"] + 2:", "if False:"),
 ('a button label that will not fit is not noticed', F, "if len(lab) * 6.6 + 12 > w:", "if False:"),
 ('a chip label that will not fit is not noticed', F, "if len(lab) * 5.2 + 8 > w:", "if False:"),
 ('a box label that will not fit is not noticed', F, "        if need > h:", "        if False:"),
 ('a callout with no note is not noticed', F, "        if not have <= want:", "        if False:"),
 ('a note with no callout is not noticed', F, "        if want - have:", "        if False:"),
 ('a callout item is not counted', F, "        c.callouts.append(it[\"n\"])\n", "        pass\n"),
 ('a callout on an item is not counted', F, "        if it.get(\"callout\"):\n            c.callouts.append(it[\"callout\"])", "        if False:\n            c.callouts.append(it[\"callout\"])"),
 ('an arrow label too long for the arrow is not noticed', F, "                if run < need:", "                if False:"),
 ('labelled arrows that meet at one side of a box are not noticed', F, "            if len(group) > 1:", "            if False:"),
 ('an arrow with no label is counted as meeting the others', F, "            if a.item.get(\"label\"):\n                for end, side in", "            if True:\n                for end, side in"),
 ('the default side an arrow leaves from is wrong in the count', F, "for end, side in ((\"from\", \"r\"), (\"to\", \"l\")):", "for end, side in ((\"from\", \"l\"), (\"to\", \"l\")):"),
 ('the default side an arrow arrives at is wrong in the count', F, "for end, side in ((\"from\", \"r\"), (\"to\", \"l\")):", "for end, side in ((\"from\", \"r\"), (\"to\", \"r\")):"),
 ('the start of an arrow is left out of the count', F, "for end, side in ((\"from\", \"r\"), (\"to\", \"l\")):", "for end, side in ((\"to\", \"l\"),):"),
 ('a flag with no value after it crashes the command line', F, "        if i + 1 >= len(a) or a[i + 1].startswith(\"--\"):", "        if False:"),
 ('a flag followed by another flag takes it as its value', F, "        if i + 1 >= len(a) or a[i + 1].startswith(\"--\"):", "        if i + 1 >= len(a):"),
 ('the start of an arrow is measured from the wrong side of the box', F, "\"l\": (x, y + h / 2), \"r\": (x + w, y + h / 2)", "\"l\": (x + w, y + h / 2), \"r\": (x + w, y + h / 2)"),
 ('the bottom of a box is measured from its top', F, "\"b\": (x + w / 2, y + h)}[side]", "\"b\": (x + w / 2, y)}[side]"),
 ('a callout on words covers them', F, "TEXT_LIKE = (\"heading\", \"text\", \"caps\", \"kv\", \"mark\")", "TEXT_LIKE = ()"),
 ('a callout on a box is placed away from its corner', F, "                s.num(X0 + n.x - 10, Y0 + n.y - 10, k)", "                s.num(X0 + n.x - 60, Y0 + n.y - 60, k)"),
 ('the notes are drawn on the frame', F, "nb = notes(d, W + 40, y,", "nb = notes(d, W - 300, y,"),
 ('the next frame ignores how tall the notes are', F, "y += max(H, nb - y) + 80", "y += H + 80"),
 # ---- the schema and the description
 ('the schema lets blank text through', F, "return {\"type\": \"string\", \"pattern\": \"\\\\S\", \"maxLength\": opt.get(\"maxlen\", 400)}", "return {\"type\": \"string\", \"maxLength\": opt.get(\"maxlen\", 400)}"),
 ('the schema does not anchor ids', F, "\"pattern\": f\"^{ID_RE.pattern}$\"", "\"pattern\": ID_RE.pattern"),
 ('the schema lets objects carry other fields', F, "o: dict[str, Any] = {\"type\": \"object\", \"additionalProperties\": False,", "o: dict[str, Any] = {\"type\": \"object\", \"additionalProperties\": True,"),
 ('the schema forgets which fields are required', F, "    req = [f[0] for f in fields if f[2]]\n", "    req = []\n"),
 ('the description leaves out the values of a choice', F, "extra = f\" Values: {', '.join(map(str, opt['values']))}.\" if kind == \"enum\" else \"\"", "extra = \"\""),
 ('the description leaves out the layout rules', F, "] + [f\"- {r}\" for r in LAYOUT_RULES] + [", "] + [] + ["),
]
# a change to a place the tests cannot reach, with the reason (none yet)
EQUIVALENT = {}

only = sys.argv[1:]
if only == ['--patterns']:
    gone = [m[0] for m in MUTS if m[2] not in open(os.path.join(REPO, m[1]), encoding='utf-8').read()]
    for n in gone: print('PATTERN MISSING:', n)
    print('%d of %d changes still match the code' % (len(MUTS) - len(gone), len(MUTS)))
    sys.exit(1 if gone else 0)
if only == ['--list']:
    for m in MUTS: print(m[0])
    sys.exit(0)
unnoticed = []
for name, f, a, b in MUTS:
    if only and not any(o in name for o in only): continue
    reset()
    p = os.path.join(MUT, f); s = open(p, encoding='utf-8').read()
    if a not in s:
        print('%-60s PATTERN MISSING (the code has changed; update this mutant)' % name, flush=True); unnoticed.append(name); continue
    open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
    try:
        caught, why = run()
    except subprocess.TimeoutExpired:
        caught, why = True, 'TIMEOUT'
    if caught: print('%-60s CAUGHT: %s' % (name, why[:80]), flush=True)
    elif name in EQUIVALENT: print('%-60s not noticed, and harmless: %s' % (name, EQUIVALENT[name]), flush=True)
    else: print('%-60s NOT CAUGHT' % name, flush=True); unnoticed.append(name)
print('\n%s' % ('every change was noticed' if not unnoticed else '%d went unnoticed: %s' % (len(unnoticed), '; '.join(unnoticed))))
sys.exit(1 if unnoticed else 0)
