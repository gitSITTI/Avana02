#!/usr/bin/env python3
"""Render a .excalidraw file to PNG so you can LOOK at it:  python render.py board.excalidraw out.png [scale]
(or to a vector picture that stays sharp at any size:  python render.py board.excalidraw out.svg )

Uses Excalidraw's own exporter (@excalidraw/utils, bundled by esbuild into bundle.js) inside headless Chromium,
so what you see is what Excalidraw will draw. Build the bundle once:  npm ci && sh make_bundle.sh
Browser: set CHROMIUM_PATH, else a Playwright-managed Chromium under /opt/pw-browsers, else Playwright's default install."""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent


def main() -> None:
    src, out = sys.argv[1], sys.argv[2]
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    data = json.load(open(src))
    bundle = HERE / "bundle.js"
    if not bundle.exists():
        sys.exit("bundle.js missing: run  npm ci && sh make_bundle.sh")
    exe = os.environ.get("CHROMIUM_PATH") or next(iter(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")), None)
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"]) if exe else p.chromium.launch(args=["--no-sandbox"])
        pg = b.new_page()
        errs: list[str] = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())  # offline: never fetch fonts
        pg.set_content('<html><body style="margin:0;background:#fff"><div id="o"></div></body></html>')
        pg.add_script_tag(path=str(bundle))
        svg = pg.evaluate("""async (d) => { const s = await window.exportToSvg({data: {elements: d.elements, appState: {exportBackground: true, viewBackgroundColor: '#ffffff'}, files: {}}, config: {padding: 20, skipInliningFonts: true}}); return s.outerHTML; }""", data)
        if out.lower().endswith(".svg"):
            Path(out).write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg + "\n", encoding="utf-8")
            print("svg written", out, "errors", errs)
            b.close()
            return
        pg.set_content('<html><body style="margin:0;background:#fff">' + svg + "</body></html>")
        dims = pg.evaluate('(()=>{const s=document.querySelector("svg");return [s.width.baseVal.value,s.height.baseVal.value]})()')
        print("svg size", dims, "errors", errs)
        pg.set_viewport_size({"width": int(dims[0]), "height": int(dims[1])})
        pg.evaluate('(s)=>{const e=document.querySelector("svg"); e.style.width=(e.width.baseVal.value*s)+"px"; e.style.height=(e.height.baseVal.value*s)+"px";}', scale)
        pg.set_viewport_size({"width": int(dims[0] * scale), "height": int(dims[1] * scale)})
        pg.screenshot(path=out)
        b.close()


if __name__ == "__main__":
    main()
