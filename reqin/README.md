# reqin: read requirements from any source into one canonical model

Reference implementation of the design in `INPUT_LAYER.md`. Python 3.11+ (tested on 3.11, 3.12 and 3.13).

```bash
pip install -e ".[test]"          # needs: pyyaml openpyxl reqif sqlalchemy python-docx pdfplumber (+ rdflib for OSLC: the "oslc" extra)
pytest                            # 223 required checks: conformance x 8 formats, behaviour, downstream, live connectors against fakes,
                                  # the HTTP kit against real local servers, DOORS script, CLI and watch mode, the dataset layer, docs-match-code
                                  # + 1 optional (PDF made by LibreOffice): skipped, visibly, if `soffice` is not installed

reqin sniff     file.reqif                        # which adapter recognises it
reqin discover  file.xlsx                         # containers, fields, samples
reqin propose   file.xlsx > profile.yaml          # a PROPOSED mapping for a person to edit
reqin import    file.xlsx --profile profile.yaml  # run the pipeline; prints the report (add --out reqs.jsonl)
reqin import    sqlite:///reqs.db --opt "query=SELECT req_uid, statement FROM reqs" --opt id_column=req_uid

reqin import    file.xlsx --profile profile.yaml --out-dir ds/file   # the dataset folder the GUI reads, checked against the contract
reqin check-dataset ds/file                       # is this folder valid under GUI_CONTRACT.md? what is in it?
reqin make-datasets datasets/                     # the fourteen test datasets (F1-F14) a requirements screen must pass

reqin connectors                                  # every adapter and how far it has been proven
reqin sample    sysml+https://HOST:8443/sysmlv2-api --opt project_name=NAME --opt token_env=TWC_TOKEN   # first page only, GET only
reqin watch     /path/to/exports --out /path/to/out --rules rules.yaml --once                          # re-ingest what changed
```

```python
from reqin import Source, Profile, ingest
res = ingest(Source("reqs.xlsx"), profile=Profile.from_yaml(open("profiles/xlsx_srs.yaml").read()))
res.requirements   # list[Requirement]   res.links   res.rejected (with reasons)   res.report (counts, invariant_ok, warnings)
```

Layout: `src/reqin/{model,adapter,mapping,normalise,ingest,cli,connect,testing,watch,dataset,contract_datasets}.py`, `src/reqin/adapters/*` (one file per source), `profiles/*.yaml` (examples), `connectors/doors9/` (a DXL export script), `tests/` (fixtures are generated, synthetic).

**The screen's contract.** Read `GUI_CONTRACT.md`: the GUI reads one dataset folder (`dataset.py`), never a file, and must pass the fourteen datasets in `contract_datasets.py`.

**Your own connectors.** Read `CONNECTORS.md`. Start from `../connector_template/` (working example, five `TODO(agent)` seams, an agent prompt). Live connectors use the GET-only client in `connect.py` and are tested with `testing.py`.

**Status.** Fixtures are synthetic. No real MSOSA, DOORS, Teamwork Cloud or Agility system has been read. `sysml_api`, `oslc_rm` and `agility` are **fake-server-tested**: they have met only in-memory fakes written from documentation, and `reqin connectors` says so. The DOORS 9 script has never run in DOORS. `mdzip` is a deliberate stub. See `INPUT_LAYER.md` section 6 and `CONNECTORS.md`.
