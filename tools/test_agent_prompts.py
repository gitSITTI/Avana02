"""The files an agent from any provider is pointed to: AGENTS.md, the short files that point to it, and the prompts in docs/agent_prompts/.

What must hold: a prompt that is pasted into a chat holds the vocabulary the checker uses, today's and not last month's; every repository path a prompt or AGENTS.md names exists (or is on the short list
of files the task is to create); the prompts name no product, so they work for any agent; the pointer files really point; and the board example inside the no-code prompt is a board the checker accepts.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PROMPTS = sorted((REPO / "docs" / "agent_prompts").glob("*.md"))
sys.path.insert(0, str(REPO / "excalidraw_generator"))

# what a prompt asks the agent to make, or leaves for the person to fill in: not expected to exist
TO_CREATE = {"requirements.jsonl", "rejected.jsonl", "spec.json", "out.excalidraw", "out.png", "audit.jsonl", "docs/COMPARE_FORMAT.md", "reqin/src/reqin/compare/", "DIR", "ports/<language>/", "ports/<language>/gateway_core/", "status.json", "work/CONTRACT.md", "paths.json"}
SEARCH_IN = ("", "excalidraw_generator/", "reqin/", "tools/", "docs/", "connector_template/", "prototype/")       # prompts say "from excalidraw_generator/" for some commands
PRODUCTS = ["claude", "anthropic", "chatgpt", "openai", "gpt-", "gemini", "copilot", "codex", "cursor", "aider", "llama", "mistral", "deepseek", "grok"]


def paths_in(text: str) -> set[str]:
    out = set()
    for tok in re.findall(r"`([^`\s]+)`", text):
        if tok.startswith(("http", "-", "$", "<", "#", ".")) or re.fullmatch(r"reqin-[a-z-]+/\d+", tok) or any(c in tok for c in "*{}=()|") or tok.endswith(("...", "…")):
            continue
        if "/" in tok or re.search(r"\.(md|py|json|js|jsonl|yaml|yml|sh|excalidraw|png|svg)$", tok):
            out.add(tok)
    return out


def exists(tok: str) -> bool:
    return tok in TO_CREATE or any((REPO / (base + tok)).exists() for base in SEARCH_IN) or "<" in tok


def test_there_are_the_six_prompts_and_the_porting_guide_lists_every_one():
    names = {p.name for p in PROMPTS}
    assert names == {"excalidraw_board_without_code.md", "excalidraw_board_with_code.md", "new_connector.md", "port_gateway_core.md", "comparison_engine.md", "build_the_gui.md"}
    porting = (REPO / "docs" / "PORTING.md").read_text(encoding="utf-8")
    for n in names:
        assert f"agent_prompts/{n}" in porting, f"docs/PORTING.md does not list {n}"


@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
def test_every_path_a_prompt_names_exists(prompt):
    missing = sorted(t for t in paths_in(prompt.read_text(encoding="utf-8")) if not exists(t))
    assert not missing, f"{prompt.name} names files that are not there: {missing}"


def test_agents_md_names_only_files_that_exist():
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    missing = sorted(t for t in paths_in(text) if not exists(t) and t not in {"spec.json", "out.excalidraw", "out.png"})
    assert not missing, missing


@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
def test_a_prompt_names_no_product_and_says_what_it_did_not_check(prompt):
    text = prompt.read_text(encoding="utf-8")
    low = text.lower()
    named = [w for w in PRODUCTS if re.search(rf"(?<![a-z]){re.escape(w)}", low)]
    assert not named, f"{prompt.name} names a product: {named}; a prompt must work for any agent"
    assert "not checked" in low, f"{prompt.name} does not ask for a statement of what was not checked"


@pytest.mark.parametrize("prompt", PROMPTS, ids=lambda p: p.name)
def test_a_prompt_forbids_real_data_or_points_to_the_rules_that_do(prompt):
    low = prompt.read_text(encoding="utf-8").lower()
    assert "agents.md" in low or "sample data only" in low or "made up" in low, prompt.name


def test_the_generated_blocks_in_the_prompts_are_current():
    r = subprocess.run([sys.executable, str(REPO / "tools" / "make_agent_prompts.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_the_no_code_prompt_is_self_contained_and_its_example_is_a_board_the_checker_accepts():
    import board_spec as bs
    text = (REPO / "docs" / "agent_prompts" / "excalidraw_board_without_code.md").read_text(encoding="utf-8")
    for t in bs.ITEMS:
        assert f"`{t}`" in text, f"the prompt does not describe the item type {t}, and an agent with no other file cannot guess it"
    for entry in bs.SIDEBAR:
        assert entry in text
    for tone in bs.TONES:
        assert tone in text
    block = re.search(r"<!-- begin:example -->\n```json\n(.*?)\n```\n<!-- end:example -->", text, re.S)
    assert block, "no example block"
    spec = json.loads(block.group(1))
    assert bs.check_spec(spec) == []
    assert bs.compile_spec(spec)[1] == [], "the example in the prompt must build with no warnings: a model copies what it is shown"


def test_the_no_code_prompt_states_the_limits_the_checker_enforces():
    import board_spec as bs
    text = (REPO / "docs" / "agent_prompts" / "excalidraw_board_without_code.md").read_text(encoding="utf-8")
    assert f"At most {bs.MAX_FRAMES} frames, {bs.MAX_ITEMS} items in a frame, {bs.MAX_NOTES} notes" in text
    assert "600 characters" in text and "400" in text
    assert str(round(1000 - 180 - 24)) in text, "the usable width of the default app frame"
    assert "8 px per character" in text and "36 px" in text, "the arrow-label rule the compiler warns about"


def test_the_short_files_for_other_tools_point_to_agents_md_and_repeat_the_three_rules_that_matter():
    for rel, link in (("CLAUDE.md", "AGENTS.md"), ("GEMINI.md", "AGENTS.md"), (".github/copilot-instructions.md", "../AGENTS.md")):
        text = (REPO / rel).read_text(encoding="utf-8")
        assert f"]({link})" in text, rel
        low = text.lower()
        assert "made up" in low and "do not push" in low and "did not check" in low, f"{rel} must carry the three rules in case the tool does not follow the link"
        assert len(text) < 1200, f"{rel} is meant to be short; the rules live in AGENTS.md"


def test_agents_md_has_the_rules_the_owner_asked_for():
    low = (REPO / "AGENTS.md").read_text(encoding="utf-8").lower()
    for phrase in ("no real data", "do not push", "say what you did not check", "must be shown to fail", "generated files are not edited by hand", "no secrets in files"):
        assert phrase in low, phrase


def test_the_prompts_and_agents_md_hold_nothing_that_looks_like_a_secret_or_a_private_name():
    for p in PROMPTS + [REPO / "AGENTS.md", REPO / "docs" / "PORTING.md", REPO / "docs" / "GATEWAY_SPEC.md"]:
        low = p.read_text(encoding="utf-8").lower()
        for w in ("password:", "api_key=", "sk-", "begin private key"):
            assert w not in low, (p.name, w)
