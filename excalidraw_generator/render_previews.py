#!/usr/bin/env python3
"""Render every board in ../excalidraw to PNG for the README and the design guide.

    python3 render_previews.py [OUT_DIR]       default OUT_DIR: ../docs/images/boards

Needs what render.py needs (Node-built bundle.js, Playwright and a Chromium: see EXCALIDRAW_GUIDE.md section 2) and Pillow.
For each board it writes   NN_name.png  (full size, 256-colour to keep the repository small)
                           thumbs/NN_name.png  (the top of the board, 640 px wide, for galleries)
and a manifest.json that records the SHA-256 of each board file it rendered. A test (tools/test_previews_fresh.py) compares
those hashes with the boards, so a board cannot change without its picture being refreshed. LOOK at the pictures before you commit them.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
BOARDS = HERE.parent / "excalidraw"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "docs" / "images" / "boards"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    (OUT / "thumbs").mkdir(parents=True, exist_ok=True)
    manifest: dict[str, str] = {}
    for board in sorted(BOARDS.glob("*.excalidraw")):
        png = OUT / (board.stem + ".png")
        r = subprocess.run([sys.executable, str(HERE / "render.py"), str(board), str(png), "1"], capture_output=True, text=True)
        if r.returncode != 0 or "errors []" not in r.stdout:
            print(f"FAILED {board.name}:\n{r.stdout}\n{r.stderr}", file=sys.stderr)
            return 1
        im = Image.open(png).convert("RGB")
        im.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(png, optimize=True)
        w, h = im.size
        crop = min(h, int(w * 0.68))
        im.crop((0, 0, w, crop)).resize((640, round(crop * 640 / w)), Image.LANCZOS).save(OUT / "thumbs" / png.name, optimize=True)
        manifest[board.name] = sha256(board)
        print(f"{png.name:34} {im.size}  {png.stat().st_size // 1024} KB")
    (OUT / "manifest.json").write_text(json.dumps({"boards": manifest}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
