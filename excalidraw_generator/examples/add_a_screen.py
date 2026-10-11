"""Recipe A: add a screen. Run from the package root:  python examples/add_a_screen.py out/example.excalidraw

A screen is a function (doc, ox, oy) -> list of note strings. It opens a frame, draws with frame-local coordinates,
closes the frame, and returns the notes that will sit beside it, numbered to match the red callouts it drew."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from wf2 import *  # noqa: E402,F401,F403  (Doc, notes, new_frame, shell2, para, table, chk_list, palette ...)


def s_example(d, ox, oy):
    W, H = 1000, 520
    s = new_frame(d, ox, oy, W, H, '11.1 · Example screen')          # opens the frame, paints the background, returns a Scr
    cx, cy = shell2(s, W, H, 'Review queue', lens=0)                   # sidebar + title block + banner; returns content origin
    s.h1(cx, cy, 'Example screen', fs=24)
    s.card(cx, cy + 44, 420, 150)
    s.caps(cx + 16, cy + 58, 'A CAPTION IN SMALL CAPS')
    para(s, cx + 16, cy + 82, 'Body text must be wrapped with para() or d.wrap(); a bare s.t() does not wrap and will overflow the frame.', 380, fs=11)
    s.btn(cx + 16, cy + 146, 170, 32, 'Primary action', primary=True)
    s.prov(cx + 220, cy + 154, 'mech', 'a mechanical step')
    s.num(cx - 18, cy + 46, 1)                                          # red callout; the note below must be #1
    s.num(cx - 18, cy + 148, 2)
    d.frame_end()
    return ['Say what callout 1 points at and why the design is this way.',
            'One idea per note. Notes are the reasoning; the picture is only the layout.']


if __name__ == '__main__':
    d = Doc(1101)                                                       # unique seed per board: it fixes every element id
    d.text(0, -70, '11 · Example board', fs=36, family=1, color=INK)
    n = s_example(d, 0, 0)
    notes(d, 1040, 0, list(enumerate(n, 1)), title='Notes')           # Notes column sits OUTSIDE the frame, to its right
    d.save(sys.argv[1] if len(sys.argv) > 1 else 'example.excalidraw')
