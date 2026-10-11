import sys
sys.path.insert(0, '.')
from exc import Doc
from wf import *
from wf_a import notes, s_open, s_import, s_overview
from wf_b import s_review, s_actions
import wf_c
from flows import box, SRC_F, MECH_F, HUM_F, GUARD_F


def screen_map(d, ox, oy):
    d.frame_begin(ox, oy, 1000, 640, 'Screen map: how the screens connect')
    X, Y = ox, oy
    d.text(X + 20, Y + 14, 'Screen map', fs=24, family=1)
    o = box(d, X + 20, Y + 280, 130, 70, '1  Open\na project', SRC_F, fs=12)
    i = box(d, X + 190, Y + 280, 130, 70, '2  Map fields\nand prepare', SRC_F, fs=12)
    ov = box(d, X + 360, Y + 280, 130, 70, '3  Overview', SRC_F, fs=12)
    rv = box(d, X + 540, Y + 140, 160, 70, '4  Review queue\n(5  decision card)', HUM_F, fs=12)
    me = box(d, X + 540, Y + 280, 160, 70, '6  Methods\nand metrics', MECH_F, fs=12)
    au = box(d, X + 540, Y + 420, 160, 70, '7  Audit log', GUARD_F, fs=12)
    ex = box(d, X + 780, Y + 140, 190, 70, '8  Export to\ndocuments', BLUE_BG, fs=12)
    gl = box(d, X + 780, Y + 420, 190, 70, '9  Glossary\nand help', '#fff9db', stroke='#f1c40f', fs=12)
    d.connect(o, i, 'r', 'l')
    d.connect(i, ov, 'r', 'l')
    d.connect(ov, rv, 'r', 'l', label='start with safest', fs=11, lx=-20, ly=-6)
    d.connect(ov, me, 'r', 'l', dash=True, color=SOFT)
    d.connect(ov, au, 'r', 'l', dash=True, color=SOFT)
    d.connect(rv, ex, 'r', 'l', label='approved', fs=11)
    d.text(X + 722, Y + 224, 'Change / Open\nbrings you back', fs=11, family=1, color='#b35a00')
    d.text(X + 20, Y + 520, 'Solid arrow: the main loop. Dashed: reachable from the sidebar at any time.', fs=13, family=1, color=SOFT)
    d.text(X + 20, Y + 548, 'Glossary and Close project are in the sidebar on every screen. The phone layout (10) shows the same screens stacked.', fs=13, family=1, color=SOFT)
    d.frame_end()
    return ['The main loop is Overview, then the Review queue, then Export. Everything else supports it.',
            'From Export, "Change" or "Open" sends you back to the exact cluster.',
            'Methods and Audit are inspection screens: they never change a decision.']


def build(path):
    d = Doc(51)
    GAP = 100
    C1, C2 = 0, 1500
    d.text(0, 0, 'Wireframes: Requirements Consolidator', fs=32, family=1)
    d.text(0, 48, 'Low-fidelity layouts of every screen in the prototype. Red numbers match the notes beside each frame. Grey = structure; colour appears only where it carries meaning.', fs=15, family=2, color=SOFT)
    d.text(0, 80, 'Left column: the main journey, in order (1 to 5).    Right column: screen map and supporting screens (6 to 9).    Bottom: phone layout (10).', fs=15, family=2, color=SOFT)
    d.text(0, 112, 'Marks: square = mechanical method · diamond = AI · circle = person.    Everything shown is a draft until four lenses sign.', fs=15, family=2, color=SOFT)
    top = 170
    y = top
    left = [(s_open, 640), (s_import, 640), (s_overview, 640), (s_review, 1580), (s_actions, 640)]
    for fn, h in left:
        n = fn(d, C1, y)
        notes(d, C1 + 1040, y, list(enumerate(n, 1)), title='Notes')
        y += h + GAP
    left_end = y
    y = top
    right = [(screen_map, 640), (wf_c.s_methods, 900), (lambda d_, x, yy: wf_c.s_audit(d_, x, yy, False), 640), (lambda d_, x, yy: wf_c.s_audit(d_, x, yy, True), 640),
             (lambda d_, x, yy: wf_c.s_export(d_, x, yy, False), 640), (lambda d_, x, yy: wf_c.s_export(d_, x, yy, True), 800), (wf_c.s_glossary, 700)]
    for fn, h in right:
        n = fn(d, C2, y)
        notes(d, C2 + 1040, y, list(enumerate(n, 1)), title='Notes')
        y += h + GAP
    y = max(left_end, y)
    n = wf_c.s_mobile(d, C1, y)
    notes(d, C1 + 1300, y, list(enumerate(n, 1)), title='Notes')
    d.save(path)
    return d


if __name__ == '__main__':
    build(sys.argv[1] if len(sys.argv) > 1 else '02_wireframes.excalidraw')
