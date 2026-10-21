#!/usr/bin/env python3
"""Build a portable draft-review workspace from checked comparison output.

python tools/review/build.py COMPARISON --dataset DATASET --out NEW_FOLDER
Serve NEW_FOLDER with tools/gui_checks/serve.py --app NEW_FOLDER.
Uses the reference viewer as a reusable dataset component; no prototype markup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "reqin/src"))


def build(comparison, datasets, out, vocab=None):
    from reqin.compare.output import check
    from reqin.compare.vocabulary import load
    from reqin.dataset import check_dataset
    comparison, out = Path(comparison), Path(out)
    if any(out.resolve().is_relative_to(Path(src).resolve()) for src in [comparison, *datasets]):
        raise ValueError("Output must be outside all source dataset and comparison folders.")
    if out.exists():
        raise ValueError("Output already exists; choose a new folder. Nothing was overwritten.")
    problems = check(comparison, datasets, recompute=True, vocab=load(vocab) if vocab else None)
    if problems:
        raise ValueError("Comparison refused: " + "; ".join(problems))
    checked = [check_dataset(d)[0] for d in datasets]
    read_rows = lambda name: [json.loads(line) for line in (comparison / name).read_text().splitlines() if line]
    payload = dict(format="reqin-review-input/1", summary=json.loads((comparison / "compare.json").read_text()),
                   clusters=read_rows("clusters.jsonl"), pairs=read_rows("pairs.jsonl"),
                   requirements=[r for d in checked for r in d["requirements"]],
                   datasets=["data/source-" + str(i + 1) for i in range(len(datasets))])
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    binding = hashlib.sha256(raw).hexdigest()
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix=".reqin-review-", dir=out.parent))
    try:
        reference = ROOT / "design/reference_viewer"
        for name in ("viewer.js", "viewer.css"):
            shutil.copy2(reference / name, temp / name)
        for name in ("review.js", "review.css"):
            shutil.copy2(Path(__file__).parent / name, temp / name)
        shutil.copy2(ROOT / "design/tokens.css", temp / "tokens.css")
        shutil.copytree(ROOT / "prototype/project/fonts", temp / "fonts")
        for i, folder in enumerate(datasets):
            dest = temp / "data" / ("source-" + str(i + 1))
            dest.mkdir(parents=True)
            for name in ("dataset.json", "requirements.jsonl", "links.jsonl", "rejected.jsonl", "report.json"):
                shutil.copy2(Path(folder) / name, dest / name)
        (temp / "review-input.json").write_bytes(raw)
        html = (reference / "index.html").read_text()
        html = html.replace("<title>Dataset viewer</title>", "<title>Requirements draft review</title>")
        html = html.replace("<h1>Dataset viewer</h1>", "<h1>Requirements draft review</h1>")
        html = html.replace("Shows one canonical dataset, or several. It reads nothing else.", "Review mechanical comparisons against their source requirements. Every result remains a draft.")
        html = html.replace("</head>", '<link rel="stylesheet" href="review.css">\n</head>')
        fragment = (Path(__file__).parent / "panel.html").read_text()
        html = html.replace("<main>", '<main>\n' + fragment)
        html = html.replace('<script src="viewer.js"></script>', '<script src="viewer.js"></script>\n<script src="review.js" data-binding="' + binding + '"></script>')
        (temp / "index.html").write_text(html)
        (temp / "README.txt").write_text("Requirements draft review. Serve this folder on localhost.\nDecisions are kept only in page memory until you download a review file.\nLoading another dataset hides comparison controls; reload to return to this comparison.\nNo sign-offs, source write-back, semantic recall guarantee, or final approval.\n")
        temp.rename(out)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comparison")
    ap.add_argument("--dataset", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--vocab")
    a = ap.parse_args(argv)
    try:
        print("Draft review written to " + str(build(a.comparison, a.dataset, a.out, a.vocab)))
    except (OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
