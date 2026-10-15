"""Breaking the page on purpose: does the accessibility run (prototype/b20.py) notice?

Each change makes the page worse in one way a person would notice (a faint field edge, no skip link, no focus ring, a button without a name, two chart colours that look
the same to someone with red-green colour blindness, a page that needs sideways scrolling on a phone) in a throwaway copy of the page, then runs b20.py at 1440 px on the
copy. Needs the vendored libraries (cd prototype/vendor && npm ci), Playwright and a Chromium, like the browser tests. Each change takes about a minute.

Usage: python3 tools/mutation/a11y.py [part of a name ...]     --list shows the names; --patterns only checks that every change still matches the code.
Exit status 1 when a change goes unnoticed, or when b20.py failed but not on the check made for that change (the line it printed is shown either way)."""
import os, shutil, subprocess, sys
import common
from common import SRC, MUT, WORK, reset

HEAD, SHELL, METH, BUILD, C3 = 'parts/m/00_head.html', 'parts/m/30_shell_open.html', 'parts/m/70_methods.html', 'build.py', 'parts/c3.js'
GLOSSARY = '<button class="tb-icon" onClick="{{openGlossary}}" aria-label="Open the glossary" title="Glossary and help">§IC:help:20§</button>'

# (name, file, old text, new text, text the failing line must contain)
muts = [
 ('field edge too faint', BUILD, "min-height:44px;padding:0 12px;border:1px solid #7A8793;", "min-height:44px;padding:0 12px;border:1px solid #D3DAE1;", 'fields,'),
 ('page title never changes', C3, "document.title = v.pageTitle + ' · Requirements Consolidator';", "void 0;", 'title:'),
 ('skip link removed', SHELL, '<a class="skip-link" href="#main-content" onClick="{{skipToMain}}">Skip to the main content</a>', '', 'skip link'),
 ('focus ring removed', HEAD, "outline:3px solid var(--accent);outline-offset:2px}", "outline:none}", 'focus ring'),
 ('secondary text too faint', HEAD, "--slate:#54626F;", "--slate:#A3AEB9;", 'contrast,'),
 ('icon button without a name', SHELL, GLOSSARY, GLOSSARY.replace(' aria-label="Open the glossary" title="Glossary and help"', ''), 'axe,'),
 ('click that the keyboard cannot reach', SHELL, GLOSSARY, GLOSSARY.replace('<button class="tb-icon"', '<div style="cursor:pointer" class="tb-icon"').replace('</button>', '</div>'), 'nothing reacts to a click'),
 ('page needs sideways scrolling', SHELL, '<div class="content" id="main-content" tabindex="-1">', '<div class="content" id="main-content" tabindex="-1" style="min-width:700px">', 'reflow:'),
 ('two chart colours that look alike', METH, 'data-chart-mark="with and without AI" style="width:12px;height:12px;background:#2A6FD6;', 'data-chart-mark="with and without AI" style="width:12px;height:12px;background:#54626F;', 'chart colours'),
]


def prepare():
    reset()
    for f in ('h.py', 'b20.py', 'a11y_page.js', 'chart_colours.py'): shutil.copy(os.path.join(SRC, f), os.path.join(MUT, f))
    for f in ('support.js', 'canvas.json'):
        if os.path.exists(os.path.join(SRC, 'project', f)): shutil.copy(os.path.join(SRC, 'project', f), os.path.join(MUT, 'project', f))
    shutil.copytree(os.path.join(SRC, 'project', 'fonts'), os.path.join(MUT, 'project', 'fonts'))
    os.symlink(os.path.join(SRC, 'vendor'), os.path.join(MUT, 'vendor'))


def main():
    args = sys.argv[1:]
    if args == ['--list']:
        for m in muts: print(m[0])
        return 0
    if args == ['--patterns']:
        missing = [m[0] for m in muts if m[2] not in open(os.path.join(SRC, m[1]), encoding='utf-8').read()]
        for n in missing: print('PATTERN MISSING:', n)
        print('%d of %d changes still match the code' % (len(muts) - len(missing), len(muts)))
        return 1 if missing else 0
    if not os.path.isdir(os.path.join(SRC, 'vendor', 'node_modules', 'axe-core')):
        print('the vendored libraries are missing; run `npm ci` in prototype/vendor first'); return 1
    bad = []
    for name, f, a, b, expect in muts:
        if args and not any(o in name for o in args): continue
        prepare()
        p = os.path.join(MUT, f)
        s = open(p, encoding='utf-8').read()
        if a not in s:
            print('%-40s PATTERN MISSING (the code has changed; update this change)' % name, flush=True); bad.append(name); continue
        open(p, 'w', encoding='utf-8').write(s.replace(a, b, 1))
        built = subprocess.run('python3 build.py >/dev/null', cwd=MUT, shell=True, capture_output=True, text=True)
        if built.returncode != 0:
            print('%-40s DID NOT BUILD: %s' % (name, built.stderr.strip()[-100:]), flush=True); bad.append(name); continue
        r = subprocess.run([sys.executable, 'b20.py', '1440'], cwd=MUT, capture_output=True, text=True, timeout=1200)
        fails = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith('FAIL')]
        mine = [l for l in fails if expect.lower() in l.lower()]
        if r.returncode == 0 and not fails:
            print('%-40s NOT CAUGHT' % name, flush=True); bad.append(name)
        elif mine:
            print('%-40s CAUGHT (%d failing checks): %s' % (name, len(fails), mine[0][:150]), flush=True)
        else:
            print('%-40s CAUGHT, BUT NOT BY THE CHECK MADE FOR IT (%d failing checks): %s' % (name, len(fails), (fails[0] if fails else (r.stdout + r.stderr).strip()[-150:])[:150]), flush=True); bad.append(name)
    print('\n%s' % ('every change was noticed' if not bad else '%d need attention: %s' % (len(bad), '; '.join(bad))))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
