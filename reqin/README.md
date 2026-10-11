# reqin: read requirements from any source into one canonical model

Reference implementation of the design in `INPUT_LAYER.md`. Python 3.11+ (tested on 3.11, 3.12 and 3.13).

```bash
pip install -e ".[test]"          # needs: pyyaml openpyxl reqif sqlalchemy python-docx pdfplumber
pytest                            # 83 required checks: conformance x 8 formats, behaviour, cross-format downstream
                                  # + 1 optional (PDF made by LibreOffice): skipped, visibly, if `soffice` is not installed

reqin sniff     file.reqif                        # which adapter recognises it
reqin discover  file.xlsx                         # containers, fields, samples
reqin propose   file.xlsx > profile.yaml          # a PROPOSED mapping for a person to edit
reqin import    file.xlsx --profile profile.yaml  # run the pipeline; prints the report (add --out reqs.jsonl)
reqin import    sqlite:///reqs.db --opt "query=SELECT req_uid, statement FROM reqs" --opt id_column=req_uid
```

```python
from reqin import Source, Profile, ingest
res = ingest(Source("reqs.xlsx"), profile=Profile.from_yaml(open("profiles/xlsx_srs.yaml").read()))
res.requirements   # list[Requirement]   res.links   res.rejected (with reasons)   res.report (counts, invariant_ok, warnings)
```

Layout: `src/reqin/{model,adapter,mapping,normalise,ingest,cli}.py`, `src/reqin/adapters/*` (one file per format), `profiles/*.yaml` (examples), `tests/` (fixtures are generated, synthetic).

**Status.** Fixtures are synthetic. No real MSOSA, DOORS or SysML v2 server data has been read. `sysml_api` uses assumed JSON key names (configurable) and `mdzip` is a deliberate stub. See `INPUT_LAYER.md` section 6.
