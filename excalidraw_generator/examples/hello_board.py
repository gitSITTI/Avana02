"""Smallest useful board: one frame, three shapes, one connector, one handwritten note.
Run from the package root:  python examples/hello_board.py out/hello.excalidraw && python render.py out/hello.excalidraw out/hello.png"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exc import Doc  # noqa: E402

d = Doc()                                              # Doc(seed): the seed fixes element ids, so rebuilds are byte-identical
d.frame_begin(0, 0, 400, 260, "Test frame")           # everything drawn until frame_end() belongs to this frame
a = d.rect(20, 40, 160, 60, "Read and normalise 214 requirements", fill="#a5d8ff")
b = d.rect(220, 40, 160, 60, "Mechanical ladder", fill="#b2f2bb")
c = d.diamond(220, 140, 160, 90, "Guards pass?", fill="#ffec99")
d.connect(a, b, label="next")                         # right side of a -> left side of b, arrow bound to both shapes
d.connect(b, c, "b", "t")                             # bottom of b -> top of c
d.text(20, 200, "Handwritten note", fs=16, family=1, color="#e03131")   # family 1 = hand-drawn font, 2 = clean sans, 3 = mono
d.frame_end()
d.save(sys.argv[1] if len(sys.argv) > 1 else "hello.excalidraw")
