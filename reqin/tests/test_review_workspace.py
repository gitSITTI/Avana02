"""The review package is a draft bound to checked source datasets, never sample data."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from reqin.compare.output import run_dataset, write
from reqin.contract_datasets import build_all, SPECS

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("review_build", ROOT / "tools/review/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


def workspace(tmp_path):
    build_all(tmp_path / "datasets", size=20)
    ds = tmp_path / "datasets/F02_everything"
    result, info = run_dataset(ds)
    cmp = write(result, tmp_path / "compare", info)
    return ds, cmp


def test_workspace_preserves_sources_and_refuses_changed_comparison(tmp_path):
    ds, cmp = workspace(tmp_path)
    before = (ds / "requirements.jsonl").read_bytes()
    out = builder.build(cmp, [ds], tmp_path / "app")
    payload = json.loads((out / "review-input.json").read_text())
    assert payload["requirements"] == [json.loads(l) for l in before.splitlines()]
    assert payload["summary"]["status"] == "draft" and payload["pairs"]
    assert (out / "data/source-1/requirements.jsonl").read_bytes() == before
    assert (out / "fonts/LICENSE-public-sans.txt").exists()
    with pytest.raises(ValueError, match="already exists"):
        builder.build(cmp, [ds], out)
    with pytest.raises(ValueError, match="outside"):
        builder.build(cmp, [ds], ds / "review")
    with (cmp / "pairs.jsonl").open("a") as f:
        f.write('{}\n')
    with pytest.raises(ValueError, match="Comparison refused"):
        builder.build(cmp, [ds], tmp_path / "refused")
    assert not (tmp_path / "refused").exists()
    assert (ds / "requirements.jsonl").read_bytes() == before


def test_review_notes_require_known_ids_matching_input_and_reasons(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js is required for the browser view model")
    ds, cmp = workspace(tmp_path)
    out = builder.build(cmp, [ds], tmp_path / "app")
    js = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const model = require(process.argv[1]);
const data = JSON.parse(fs.readFileSync(process.argv[2]));
const items = model.itemsOf(data);
assert.equal(items.length, data.clusters.length + data.pairs.length);
assert.equal(items[0].records[0].text, data.requirements.find(r => r.mid === items[0].records[0].mid).text);
const notes = { [items[0].id]: { outcome: 'agree', reason: 'The quantities and conditions agree.' } };
const draft = model.exportDraft(data, 'binding', notes);
assert.deepEqual(model.restore(draft, data, 'binding'), notes);
assert.equal(draft.status, 'draft');
assert.throws(() => model.restore(draft, data, 'other'));
assert.throws(() => model.restore({ ...draft, decisions: { unknown: notes[items[0].id] } }, data, 'binding'));
assert.throws(() => model.restore({ ...draft, decisions: { [items[0].id]: { outcome: 'agree', reason: ' ' } } }, data, 'binding'));
assert.throws(() => model.restore({ ...draft, decisions: { [items[0].id]: { outcome: 'approved', reason: 'A reason' } } }, data, 'binding'));
assert.throws(() => model.itemsOf({ ...data, requirements: [] }));
assert.ok(model.coverageOf(data).some(x => x.includes('tokens too common')));
'''
    subprocess.run(["node", "-e", js, str(ROOT / "tools/review/review.js"), str(out / "review-input.json")], check=True, capture_output=True, text=True)


@pytest.mark.parametrize("dataset_id", [s[0] for s in SPECS])
def test_review_view_model_handles_every_contract_shape(tmp_path, dataset_id):
    if not shutil.which("node"):
        pytest.skip("Node.js required")
    entry = build_all(tmp_path / "datasets", only=[dataset_id], size=5000)[0]
    folders = [tmp_path / "datasets" / name for name in entry["folders"]]
    result, info = run_dataset(folders)
    comparison = write(result, tmp_path / "compare", info)
    app = builder.build(comparison, folders, tmp_path / "app")
    script = "const m=require(process.argv[1]),fs=require('fs'),d=JSON.parse(fs.readFileSync(process.argv[2]));if(m.itemsOf(d).length!==d.clusters.length+d.pairs.length)process.exit(1);"
    subprocess.run(["node", "-e", script, str(ROOT / "tools/review/review.js"), str(app / "review-input.json")], check=True)
