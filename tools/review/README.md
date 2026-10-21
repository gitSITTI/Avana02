# Review checked comparison output

Build a portable review workspace from the actual canonical datasets and mechanical output. The builder recomputes the comparison and refuses stale, changed or mismatched inputs. It reuses the dataset component from `design/reference_viewer/` and builds the comparison panel from the sources here; it copies no prototype markup.

From a checkout with `pip install -e "reqin[test]"`:

```bash
reqin import export.csv --out-dir /tmp/imported
reqin compare /tmp/imported --out-dir /tmp/comparison
python3 tools/review/build.py /tmp/comparison --dataset /tmp/imported --out /tmp/draft-review
python3 tools/gui_checks/serve.py --app /tmp/draft-review
```

Open `http://127.0.0.1:8000/` and choose **Open checked comparison**. Use `--dataset` repeatedly for multiple sources, and `--vocab FILE` when the comparison used a custom vocabulary. The output folder must not already exist. Outputs contain source wording; keep them outside the repository.

The screen shows clusters, typed pairs, rule explanations, original wording and candidate-search limits. Record agreement, disagreement or a need for further review. Agreement and disagreement require a reason. Notes live only in page memory; **Download draft review** saves them with original requirements, internal IDs, mechanical results and an input fingerprint. **Restore draft review** refuses a different comparison, unknown IDs, invalid outcomes and missing reasons. Source wording always comes from the checked workspace, not an uploaded review file. This is a binding check against accidental mix-ups, not an authenticated signature.

Choosing another dataset hides comparison controls to prevent reviewing stale results against unrelated data. Reload to return to the bound comparison. Serve from localhost or HTTPS so the browser can verify checksums. No external hosts or models are called, and no source file is changed.

```bash
python3 tools/gui_checks/hardcode_scan.py /tmp/draft-review
reqin make-datasets /tmp/test-datasets --size 5000
python3 tools/gui_checks/probe.py --app /tmp/draft-review --datasets /tmp/test-datasets
python3 -m pytest -q reqin/tests/test_review_workspace.py
```

Limits: this is a single-reviewer draft workflow, without sign-offs or a connection to the reference server. It does not consolidate source records, write back into source systems or approve a release. No real requirements set or external system was tested. The setup diagnostic is `python3 tools/doctor.py`; [CAPABILITIES.md](../../docs/CAPABILITIES.md) lists the wider implementation boundaries.
