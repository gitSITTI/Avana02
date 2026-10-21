#!/usr/bin/env python3
"""Fills the generated blocks of docs/agent_prompts/*.md from the code, so a prompt that is pasted into a chat holds the same vocabulary the checker uses.

    python3 tools/make_agent_prompts.py            # rewrite the blocks
    python3 tools/make_agent_prompts.py --check    # fail if a block is not what the code gives (tools/test_agent_prompts.py runs this)

A block is the text between  <!-- begin:NAME -->  and  <!-- end:NAME -->.  NAME is one of: describe (the board format, as Markdown), example (a working spec, as JSON).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "excalidraw_generator"))
import board_spec  # noqa: E402

BLOCKS = {
    "describe": lambda: board_spec.describe().replace("# The board format,", "### The board format,").replace("\n## ", "\n#### ").replace("\n### `", "\n##### `"),
    "example": lambda: "```json\n" + json.dumps(board_spec.EXAMPLE, indent=1, ensure_ascii=False) + "\n```",
}


def fill(text: str) -> str:
    for name, make in BLOCKS.items():
        pat = re.compile(rf"(<!-- begin:{name} -->\n).*?(<!-- end:{name} -->)", re.S)
        if pat.search(text):
            text = pat.sub(lambda m: m.group(1) + make().rstrip("\n") + "\n" + m.group(2), text)
    return text


def main(argv: list[str]) -> int:
    bad = []
    for p in sorted((REPO / "docs" / "agent_prompts").glob("*.md")):
        old = p.read_text(encoding="utf-8")
        new = fill(old)
        if new != old:
            if argv == ["--check"]:
                bad.append(p.name)
            else:
                p.write_text(new, encoding="utf-8")
                print("wrote", p.relative_to(REPO))
    if bad:
        print("out of date:", ", ".join(bad), "- run: python3 tools/make_agent_prompts.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
