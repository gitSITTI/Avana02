"""Boards 05-09 as DATA: a title, a random seed (fixes element ids so rebuilds are byte-identical) and the
screens to stack. Each screen is a function (doc, x, y) -> list of note strings. Width/height are the frame
size the screen function draws; width decides where the Notes column sits, height decides the gap to the next screen.

To add a screen to a board: write the function (see lens.py / sc.py for examples), then add (fn, W, H) here."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from wf2 import *  # noqa: E402,F401,F403  (Doc, INK, notes, palette constants)
import asst, g7, lens, pipes, sc, sc2, screens_input, screens_v  # noqa: E402

BOARDS = {
    "05_scale_and_multiuser": dict(seed=105, title="05 · Scale and many reviewers: 1,000 to 1,500 requirements", screens=[
        (sc.s1_queue, 1000, 1090), (sc.s2_explorer, 1000, 840), (sc.s3_team, 1000, 830),
        (sc2.s4_states, 1000, 960), (sc2.s5_policy, 1500, 640), (sc2.s6_numbers, 1500, 1070)]),
    "06_lens_views": dict(seed=206, title="06 · Four lens views of the same cluster", screens=[
        (lens.l0_overview, 1560, 720), (lens.l1_se, 1000, 985), (lens.l2_pe, 1000, 985), (lens.l3_ux, 1000, 985), (lens.l4_nu, 1000, 970)]),
    "07_group_and_decisions": dict(seed=307, title="07 · Group resolution, rationale, revisions and the decision ledger", screens=[
        (g7.g1_workspace, 1000, 960), (g7.g2_strategies, 1500, 790), (g7.g3_rationale, 1500, 810), (g7.g4_revisions, 1500, 990), (g7.g5_ledger, 1000, 880)]),
    "08_assistant": dict(seed=408, title="08 · The assistant: a second pair of eyes, with a rulebook", screens=[
        (asst.a1_drawer, 1000, 880), (asst.a2_scenarios, 1500, 820), (asst.a3_architecture, 1500, 900), (asst.a4_effects, 1500, 700)]),
    "09_more_pipelines": dict(seed=509, title="09 · More pipelines: refresh, calibration, write-back, quality", screens=[
        (pipes.p1_map, 1500, 960), (pipes.p2_refresh, 1500, 780), (pipes.p3_calibration, 1500, 800), (pipes.p4_writeback, 1500, 710), (pipes.p5_lint, 1500, 820)]),
    "10_input_any_source": dict(seed=610, title="10 · Any input: open, map, verify, and how it works underneath", screens=[
        (screens_input.i1_open_any, 1000, 700), (screens_input.i2_map_any, 1000, 780), (screens_input.i3_extract, 1000, 720), (screens_input.i4_arch, 1500, 820)]),
    "11_the_engineering_v": dict(seed=711, title="11 · The engineering V: where every requirement sits, and what a decision does to its verification", screens=[
        (screens_v.v1_the_v_page, 1000, 1060), (screens_v.v2_where_it_shows, 1500, 860), (screens_v.v3_what_a_decision_does, 1500, 890), (screens_v.v4_how_it_is_counted, 1500, 630)]),
}


def build_board(name: str, path: str) -> int:
    spec = BOARDS[name]
    d = Doc(spec["seed"])
    y = 0
    d.text(0, -70, spec["title"], fs=36, family=1, color=INK)
    for fn, w, h in spec["screens"]:
        n = fn(d, 0, y)
        notes(d, w + 40, y, list(enumerate(n, 1)), title="Notes")
        y += h + 80
    d.save(path)
    return len(d.els)
