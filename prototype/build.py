import glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'parts')
MAC = {
 'CARD': "background:#FFFFFF;border:1px solid #BAC3CA;border-radius:8px;",
 'CAP': "font-family:'IBM Plex Mono',monospace;font-size:12px;letter-spacing:.08em;color:#4F5B66;",
 'BTN': "min-height:44px;padding:0 14px;background:#FFFFFF;border:1px solid #8C98A3;border-radius:6px;cursor:pointer;",
 'PRI': "min-height:44px;padding:0 16px;background:var(--accent);color:#FFFFFF;border:0;border-radius:6px;font-weight:600;cursor:pointer;",
 'INP': "min-height:44px;padding:0 10px;border:1px solid #8C98A3;border-radius:6px;background:#FFFFFF;font-family:inherit;font-size:14px;box-sizing:border-box;",
}
def icons(v):
    sv = '<svg width="18" height="18" viewBox="0 0 20 20" aria-hidden="true" style="flex:none;margin-top:1px">%s</svg>'
    pas = sv % '<circle cx="10" cy="10" r="9" fill="#E1F2E7" stroke="#1B6B3A" stroke-width="1.5"/><path d="M6 10.5l2.7 2.7L14 7.8" fill="none" stroke="#1B6B3A" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
    wrn = sv % '<path d="M10 2.5l8 14H2z" fill="#FFF0D2" stroke="#A15C00" stroke-width="1.5" stroke-linejoin="round"/><path d="M10 8v4M10 14.2v.1" stroke="#6B3D00" stroke-width="2" stroke-linecap="round"/>'
    fal = sv % '<circle cx="10" cy="10" r="9" fill="#FDE3E0" stroke="#A6261E" stroke-width="1.5"/><path d="M7 7l6 6M13 7l-6 6" stroke="#7A1510" stroke-width="2" stroke-linecap="round"/>'
    inf = sv % '<circle cx="10" cy="10" r="9" fill="#E8F0FD" stroke="#1C5CAB" stroke-width="1.5"/><path d="M10 9v5M10 6v.1" stroke="#10337F" stroke-width="2" stroke-linecap="round"/>'
    def blk(flag, svg, d): return '<sc-if value="{{%s.%s}}" hint-placeholder-val="{{ %s }}">%s</sc-if>' % (v, flag, d, svg)
    return blk('isPass', pas, 'true') + blk('isWarn', wrn, 'false') + blk('isFail', fal, 'false') + blk('isInfo', inf, 'false')
def expand(t):
    t = re.sub(r'§GI:(\w+)§', lambda m: icons(m.group(1)), t)
    t = re.sub(r'§(\w+)§', lambda m: MAC[m.group(1)], t)
    return t
markup = ''.join(open(f).read() for f in sorted(glob.glob(os.path.join(P, 'm', '*.html'))))
markup = expand(markup)
js_order = ['data1', 'data2', 'data3', 'logic1', 'misc', 'logic2']
js = '\n'.join(open(os.path.join(P, n + '.js')).read() for n in js_order)
cls = 'class Component extends DCLogic {\n' + '\n'.join(open(os.path.join(P, n + '.js')).read() for n in ['c1', 'c2', 'c3']) + '}\n'
props = '{"accent":{"editor":"color","default":"#1A4DB5","options":["#1A4DB5","#0B6E6E","#7A3E00","#2F3B46"]},"showHints":{"editor":"boolean","default":true}}'
out = markup + "\n</x-dc>\n" if not markup.rstrip().endswith('</x-dc>') else markup
out = out.rstrip() + "\n<script type=\"text/x-dc\" data-dc-script data-props='" + props + "'>\n" + js + "\n" + cls + "</script>\n</body>\n</html>\n"
dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'project', 'Main.dc.html')
open(dest, 'w').write(out)
print('wrote', dest, len(out), 'bytes', out.count('\n'), 'lines')
