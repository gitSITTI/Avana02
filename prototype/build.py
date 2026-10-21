import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'parts')
MAC = {
 'CARD': "background:#FFFFFF;border:1px solid #D8DFE6;border-radius:12px;",
 'CAP': "font-size:13px;font-weight:600;color:#54626F;",
 'BTN': "min-height:44px;padding:0 14px;background:#FFFFFF;border:1px solid #7A8793;border-radius:8px;cursor:pointer;font-weight:500;",
 'PRI': "min-height:44px;padding:0 16px;background:var(--accent);color:#FFFFFF;border:0;border-radius:8px;font-weight:600;cursor:pointer;",
 'INP': "min-height:44px;padding:0 12px;border:1px solid #7A8793;border-radius:8px;background:#FFFFFF;font-family:inherit;font-size:14px;box-sizing:border-box;",
}
def _macro_file(name):
    t = open(os.path.join(P, name)).read()
    return re.sub(r'§(\w+)§', lambda m: MAC[m.group(1)], t)
MAC['CONNNOTES'] = _macro_file('conn_notes.html')      # the notices of the shared project: in the card on the Open screen, on top of every other page
MAC['CONN'] = _macro_file('conn_card.html')
def icons(v):
    sv = '<svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" style="flex:none;margin-top:1px">%s</svg>'
    pas = sv % '<circle cx="10" cy="10" r="9" fill="#E1F2E7" stroke="#1B6B3A" stroke-width="1.5"/><path d="M6 10.5l2.7 2.7L14 7.8" fill="none" stroke="#1B6B3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    wrn = sv % '<path d="M10 2.5l8 14H2z" fill="#FFF0D2" stroke="#A15C00" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 8v4M10 14.2v.1" stroke="#6B3D00" stroke-width="2" stroke-linecap="round"/>'
    fal = sv % '<circle cx="10" cy="10" r="9" fill="#FDE3E0" stroke="#A6261E" stroke-width="1.5"/><path d="M7 7l6 6M13 7l-6 6" stroke="#7A1510" stroke-width="2" stroke-linecap="round"/>'
    inf = sv % '<circle cx="10" cy="10" r="9" fill="#E8F0FD" stroke="#1C5CAB" stroke-width="1.5"/><path d="M10 9v5M10 6v.1" stroke="#10337F" stroke-width="2" stroke-linecap="round"/>'
    def blk(flag, svg, d): return '<sc-if value="{{%s.%s}}" hint-placeholder-val="{{ %s }}">%s</sc-if>' % (v, flag, d, svg)
    return blk('isPass', pas, 'true') + blk('isWarn', wrn, 'false') + blk('isFail', fal, 'false') + blk('isInfo', inf, 'false')
ICONS = {
 'home': '<path d="M3.5 9.2 10 3.5l6.5 5.7V16a1 1 0 0 1-1 1H12v-4.5H8V17H4.5a1 1 0 0 1-1-1z"/>',
 'queue': '<path d="M3 11.5 5 4.5h10l2 7V16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M3 11.5h4.2l.8 2h4l.8-2H17"/>',
 'table': '<rect x="3" y="4" width="14" height="12" rx="2"/><path d="M3 8.5h14M8 8.5V16"/>',
 'chart': '<path d="M4.5 16.5v-6M10 16.5v-12M15.5 16.5v-8"/>',
 'flask': '<path d="M8 3h4M8.8 3v5L4.6 15.2A1.5 1.5 0 0 0 5.9 17.5h8.2a1.5 1.5 0 0 0 1.3-2.3L11.2 8V3"/><path d="M6.5 12.5h7"/>',
 'clock': '<circle cx="10" cy="10" r="7"/><path d="M10 6v4.2l2.8 1.6"/>',
 'shield': '<path d="M10 2.8 16 5v4.6c0 3.8-2.5 6.2-6 7.6-3.5-1.4-6-3.8-6-7.6V5z"/><path d="m7.4 10 1.9 1.9 3.4-3.8"/>',
 'export': '<path d="M10 12.5V4M6.6 7.4 10 4l3.4 3.4"/><path d="M4 12.5V15a1.5 1.5 0 0 0 1.5 1.5h9A1.5 1.5 0 0 0 16 15v-2.5"/>',
 'book': '<path d="M4 4.5A1.5 1.5 0 0 1 5.5 3H16v12.5H5.5A1.5 1.5 0 0 0 4 17z"/><path d="M4 4.5V17M7.5 6.5H13"/>',
 'exit': '<path d="M8 3.5H5a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h3"/><path d="m12.2 6.5 3.5 3.5-3.5 3.5M15.7 10H8"/>',
 'chevron': '<path d="m7.5 4.5 5.5 5.5-5.5 5.5"/>',
 'search': '<circle cx="8.8" cy="8.8" r="5.3"/><path d="m13 13 3.8 3.8"/>',
 'plus': '<path d="M10 4v12M4 10h12"/>',
 'lock': '<rect x="4.2" y="8.8" width="11.6" height="8" rx="2"/><path d="M7 8.8V6.6a3 3 0 0 1 6 0v2.2"/>',
 'spark': '<path d="M10 3 11.7 8.3 17 10l-5.3 1.7L10 17l-1.7-5.3L3 10l5.3-1.7z"/>',
 'help': '<circle cx="10" cy="10" r="7"/><path d="M7.9 8a2.1 2.1 0 1 1 3 1.9c-.7.3-.9.8-.9 1.4M10 14v.1"/>',
 'check': '<path d="m4.5 10.5 3.5 3.5 7.5-8"/>',
 'eye': '<path d="M2.5 10S5 5 10 5s7.5 5 7.5 5-2.5 5-7.5 5-7.5-5-7.5-5z"/><circle cx="10" cy="10" r="2.2"/>',
 'network': '<rect x="3" y="3.5" width="14" height="9" rx="2"/><path d="M7.5 16.5h5M10 12.5v4"/>',
 'medal': '<circle cx="10" cy="7.8" r="4.6"/><path d="m7.6 11.6-1.3 5.4 3.7-2.1 3.7 2.1-1.3-5.4"/>',
 'send': '<path d="M17 3 9 11M17 3l-5 14-3-6-6-3z"/>',
 'vee': '<path d="M3.5 4.5 10 16l6.5-11.5"/><circle cx="3.5" cy="4.5" r="1.1"/><circle cx="16.5" cy="4.5" r="1.1"/>',
 'edit': '<path d="m12.5 4.5 3 3M4 16l.7-3.3L13 4.4a1.4 1.4 0 0 1 2 0l.6.6a1.4 1.4 0 0 1 0 2L7.3 15.3z"/>',
 'tag': '<path d="M3.5 10.6V4.7a1.2 1.2 0 0 1 1.2-1.2h5.9l6 6a1.2 1.2 0 0 1 0 1.7l-4.9 4.9a1.2 1.2 0 0 1-1.7 0z"/><circle cx="7.3" cy="7.3" r="1.1"/>',
}
NAV_ICONS = ['home', 'queue', 'table', 'chart', 'vee', 'medal', 'flask', 'tag', 'clock', 'shield', 'spark', 'export']
def svg(name, size=18):
    return '<svg width="%s" height="%s" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" style="flex:none">%s</svg>' % (size, size, ICONS[name])
def nav_icons(v):
    return ''.join('<sc-if value="{{%s.ic%s}}" hint-placeholder-val="{{ false }}">%s</sc-if>' % (v, n.capitalize(), svg(n)) for n in NAV_ICONS)
def vglyph(v, w, hidden=False):
    """The small V, drawn with plain elements (the page runtime does not fill holes inside <svg>): four circles down the left leg, four
    squares up the right leg, a vertex. Data comes from veeGlyph() in logic3.js, which gives each shape's style in an 88 by 44 box.
    hidden=True when the glyph sits inside something that already says the same in words (a button with a label)."""
    h = round(w * 44 / 88)
    role = 'aria-hidden="true"' if hidden else 'role="img" aria-label="{{%s.aria}}"' % v
    line = '<svg width="88" height="44" viewBox="0 0 88 44" style="position:absolute;left:0;top:0" aria-hidden="true"><polyline points="8,6 44,38 80,6" fill="none" stroke="#596674" stroke-width="1.5" stroke-linejoin="round"/></svg>'
    return ('<span %s style="position:relative;display:block;flex:none;width:%spx;height:%spx">'
            '<span aria-hidden="true" style="position:absolute;left:0;top:0;width:88px;height:44px;transform:scale(%.4f);transform-origin:0 0">%s'
            '<span style="position:absolute;left:41.4px;top:35.4px;width:5.2px;height:5.2px;border-radius:50%%;background:#596674"></span>'
            '<sc-for list="{{%s.left}}" as="gl" hint-placeholder-count="4"><span style="{{gl.style}}">{{gl.n}}</span></sc-for>'
            '<sc-for list="{{%s.right}}" as="gr" hint-placeholder-count="4"><span style="{{gr.style}}">{{gr.n}}</span></sc-for>'
            '</span></span>') % (role, w, h, w / 88, line, v, v)
def impact(v):
    """The 'what this moves' block: a heading from v.head and the lines in v.lines, each a label and a sentence."""
    return ('<sc-if value="{{%s.on}}" hint-placeholder-val="{{ false }}"><div style="border:1px solid #D5DADE;border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;background:#F7F9FA">'
            '<div style="font-weight:600;font-size:13px">{{%s.head}}</div>'
            '<sc-for list="{{%s.lines}}" as="il" hint-placeholder-count="3"><div style="display:grid;grid-template-columns:110px minmax(0,1fr);gap:8px;font-size:13px"><span style="color:#54626F">{{il.k}}</span><span>{{il.v}}</span></div></sc-for>'
            '</div></sc-if>') % (v, v, v)
def expand(t):
    t = re.sub(r'§IMP:([\w.]+)§', lambda m: impact(m.group(1)), t)
    t = re.sub(r'§VG:([\w.]+)(?::(\d+))?(?::(h))?§', lambda m: vglyph(m.group(1), int(m.group(2) or 88), bool(m.group(3))), t)
    t = re.sub(r'§IC:(\w+)(?::(\d+))?§', lambda m: svg(m.group(1), m.group(2) or 18), t)
    t = re.sub(r'§NI:(\w+)§', lambda m: nav_icons(m.group(1)), t)
    t = re.sub(r'§GI:(\w+)§', lambda m: icons(m.group(1)), t)
    t = re.sub(r'§(\w+)§', lambda m: MAC[m.group(1)], t)
    return t
markup = ''.join(open(f).read() for f in sorted(glob.glob(os.path.join(P, 'm', '*.html'))))
markup = expand(markup)
js_order = ['data1', 'data2', 'data3', 'data4', 'logic1', 'misc', 'logic2', 'logic3', 'gold', 'single', 'trace', 'aigate', 'persist', 'connect']
js = '\n'.join(open(os.path.join(P, n + '.js')).read() for n in js_order)
# A test build with a bigger project, for the scale test (scale.js): REQIN_SCALE=20 makes 20 times as many requirements and clusters.
# It never writes the shipped page: give it another destination.
SCALE = int(os.environ.get('REQIN_SCALE', '1'))
if SCALE > 1:
    assert len(sys.argv) > 1, 'a scaled build must be written somewhere other than project/Main.dc.html'
    for pat, rep in [(r"const TOTAL_REQS = 1248;", "const TOTAL_REQS = 1248 * %d;" % SCALE), (r"n <= 252; n\+\+", "n <= 252 * %d; n++" % SCALE)]:
        js, n = re.subn(pat, rep, js); assert n == 1, pat
    js, n = re.subn(r"add\('(\w+)', (\d+)\);", lambda m: "add('%s', %d);" % (m.group(1), int(m.group(2)) * SCALE), js); assert n == 7, n
# REQIN_SHAPE=varied: the same size, a different shape. The sample repeated K times has many identical wordings, one balanced spread over the allocations and clusters of
# 2 to 14 members, which is kind to the counting of pairs (it counts once per different wording). The varied shape has mostly different wordings of different lengths drawn
# from a larger vocabulary, three in ten requirements in one allocation, and a few very large clusters. It is made up, like the sample: it tests how fast, not how well.
SHAPE = os.environ.get('REQIN_SHAPE', 'sample')
assert SHAPE in ('sample', 'varied'), 'REQIN_SHAPE is sample or varied'
if SHAPE == 'varied':
    assert len(sys.argv) > 1, 'a varied build must be written somewhere other than project/Main.dc.html'
    vary = r"""const SHAPE_SYL = ['ka','lo','mi','ren','tav','ul','bex','or','dun','fa','shi','pel','qua','zor','nim','gal','vo','tek','sar','ine'];
const SHAPE_VOC = (() => { const r = rng(7), out = []; for (let i = 0; i < 700; i++) { let w = ''; const k = 2 + Math.floor(r() * 2); for (let j = 0; j < k; j++) w += SHAPE_SYL[Math.floor(r() * SHAPE_SYL.length)]; out.push(w); } return out; })();
function VARY(text, R) {
  const extra = Math.floor(R() * R() * 14), w = [];
  for (let i = 0; i < extra; i++) w.push(SHAPE_VOC[Math.floor(SHAPE_VOC.length * R() * R())]);
  const tag = SHAPE_VOC[Math.floor(SHAPE_VOC.length * R())] + ' ' + SHAPE_VOC[Math.floor(SHAPE_VOC.length * R())];      // two words, no digits: a number here would be read as a value
  return text.replace(/\.$/, '') + (w.length ? ', ' + w.join(' ') : '') + ' (ref ' + tag + ').';
}
function genAll() {"""
    big = "const OVER = (() => { const o = { 'CL-117': 120, 'CL-201': 200 }; for (let n = 300; n <= 252 * %d; n += 97) o['CL-' + String(n).padStart(3, '0')] = 40 + (n %% 7) * 10; return o; })();" % SCALE
    for pat, rep in [(r"function genAll\(\) \{", vary),
                     (r"const OVER = \{ 'CL-117': 13, 'CL-201': 14 \};", big),
                     (r"const al = wpk\(ALLOCS\), fam = pk\(FAMS\), thing = pk\(fam.things\);", "const al = R() < 0.3 ? ALLOCS[0] : wpk(ALLOCS), fam = pk(FAMS), thing = pk(fam.things);"),
                     (r"text: fam.mk\(al.sub, val, s0, thing, cnd\), cid: null", "text: VARY(fam.mk(al.sub, val, s0, thing, cnd), R), cid: null"),
                     (r"'Pre-baseline', text, extra\);", "'Pre-baseline', VARY(text, R), extra);")]:
        js, n = re.subn(pat, lambda m, rep=rep: rep, js); assert n == 1, pat
cls = 'class Component extends DCLogic {\n' + '\n'.join(open(os.path.join(P, n + '.js')).read() for n in ['c1', 'c2', 'c3', 'c4', 'c5', 'c6', 'c7', 'c8', 'c9']) + '}\n'
props = '{"accent":{"editor":"color","default":"#1A4DB5","options":["#1A4DB5","#0B6E6E","#7A3E00","#2F3B46"]},"showHints":{"editor":"boolean","default":true}}'
out = markup + "\n</x-dc>\n" if not markup.rstrip().endswith('</x-dc>') else markup
out = out.rstrip() + "\n<script type=\"text/x-dc\" data-dc-script data-props='" + props + "'>\n" + js + "\n" + cls + "</script>\n</body>\n</html>\n"
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'project', 'Main.dc.html')
open(dest, 'w').write(out)
print('wrote', dest, len(out), 'bytes', out.count('\n'), 'lines')
