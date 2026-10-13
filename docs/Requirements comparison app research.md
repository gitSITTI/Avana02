# Build a Mechanics-First, Human-Verified Requirements Consolidator

The research notes support one defensible architecture: a Python 3.12/3.13 and React/TypeScript pipeline in which cheap, deterministic, explainable methods do nearly all the work, an AI judge enters late as a calibrated and vetoable proposer, and every output stays a draft until human review lenses sign it off. No surveyed tool combines cross-project ingestion, a ladder of mechanical similarity methods with per-method metrics, a late AI layer, role-based verification and a feed into document authoring; the nearest vendor features are QVscribe's lexical-plus-semantic similarity analysis ([Kenney and Cooper](https://ceur-ws.org/Vol-2584/NLP4RE-paper3.pdf)), Innoslate's within-document similarity percentage ([Innoslate 4.10](https://help.specinnovations.com/4.10-quality-check)) and Polarion's semantic requirement mapping ([Siemens](https://blogs.sw.siemens.com/polarion/enhancing-efficiency-in-polarion-with-ai-driven-requirements-management/)), and none of the pages the researchers opened documents reviewer-visible accept/reject metrics, so the combination is the novelty and must be assembled from open parts. The central technical finding is that lexical and embedding scores are blind to exactly the edits that matter in requirements (negation, shall/should, a changed number or unit), so number, unit, modal and negation checks must be independent deterministic vetoes rather than features inside a similarity score; in the researchers' own eight-pair toy run a negation, a modal swap and a 10x numeric change all scored **0.9+** on character-level measures, above a true paraphrase (**0.4-0.7**). The second finding is a data gap: no public gold set labels requirement pairs with a full relationship taxonomy, and the public duplicate/conflict sets hold almost no positives (PURE: **20 conflicts in 2,211 pairs**; OpenCoss: **10 in 6,786**) ([PassionNet](https://arxiv.org/abs/2412.01657)), so a locally labelled gold set of roughly **600-1,000 pairs** (the researchers' estimate) is the first real deliverable and every threshold below is a placeholder until calibrated on it. The inputs are also uncertain: "MSoSa" most likely means Magic Systems of Systems Architect (MSOSA) but this is unverified, the documented exchange route is ReqIF from the Cameo Requirements Modeler plugin ([Cameo Requirements Modeler 2024x](https://docs.nomagic.com/x/wy4mC)), `.mdzip` is zipped XMI with no documented reader contract, and the Teamwork Cloud REST API has no verified OpenAPI description. For sensitive text, supply-chain and licence hygiene matter: a single security blog reports malicious LiteLLM versions on PyPI in March 2026 ([Bastion](https://bastion.tech/blog/litellm-pypi-supply-chain-attack)), which the reader should verify and then pin, hash-lock and mirror, and several attractive components are copyleft, non-commercial, BSL or Elastic-licensed. Slot-wise comparison, veto rules, canonical-requirement selection and all numeric thresholds are the researchers' hypotheses to test, not validated results, and the export-control and CUI remarks in this report are general information, not legal advice.

> **Reading key.** Table rows carry a basis tag. **V** = stated on a page the researchers opened (link given). **S** = URL seen only in a search listing, so a lead rather than a fact. **I** = the researchers' inference, proposal or hypothesis; no source states it. "Placeholder" marks an uncalibrated starting number. Versions and dates are as of 2026-10-09, the notes' research date. This report adds no links or facts beyond the notes. Where a note was internally inconsistent or two notes disagreed, the report says so.

> **Added 2026-10-10.** Appendix A (at the end) designs and tests an input-agnostic ingestion layer for SysML v2, SysML v1/MSOSA, DOORS, Excel/CSV, SQL, Word and PDF. Appendix B documents how the Excalidraw boards were generated so an agent can rebuild and extend them. Verified and unverified items are separated in each appendix (a "what I verified" column or plain statements), and (I) marks inference.

## Nine stages keep mechanics first, AI late, and humans in charge

The stage order follows the evidence on what each tier is good for. A deterministic graph method found strict user-story redundancies in **0.6 seconds**, while GPT-4o-mini needed about **180 minutes** for 12,719 story pairs but found the many semantic redundancies the graph could not: at most 25% of goal redundancies were strict ([Hofmann et al.](https://www.uni-marburg.de/de/fb12/arbeitsgruppen/swt/publikationen/dateien/2025/hofmannetal.pdf)). Hybrid pipelines that combine language-model embeddings with several similarity measures beat any single score across six duplicate/conflict datasets, though the paper's own tables are internally inconsistent ([PassionNet](https://arxiv.org/abs/2412.01657)). A fully local, LLM-free encoder-scale pipeline with bidirectional NLI reported F1 of **0.94-0.97** on 120 enterprise documents ([GVD](https://arxiv.org/abs/2609.17696)), which supports keeping the LLM stage narrow (inference). Stages 2 through 4 form a funnel: the ladder produces candidate pairs and feature vectors, a calibrated stacker converts them to P(equivalent), typed edges are assigned, and clustering runs on EQUIVALENT edges only, with the other edge types kept as annotations and cannot-link constraints (inference; the relation labels draw on [GVD](https://arxiv.org/abs/2609.17696)).

| # | Stage | What happens | Default pick | One alternative | Basis |
|---|---|---|---|---|---|
| 1 | Ingestion and normalisation | Parse source projects into one requirement model with stable machine IDs (MID) kept apart from human IDs (UID); strip IDs and numbering, expand glossary acronyms; tag modal (SHALL/SHOULD/WILL/MAY/SHALL_NOT), polarity, conditions and quantities (value, unit, comparator, tolerance); extract slots with character spans | ReqIF exported by the Cameo Requirements Modeler plugin, read with [`reqif`](https://pypi.org/project/reqif/) (Apache-2.0, 0.1.0, 2026-08-11); CSV/XLSX fallback via pandas and python-calamine; [Pint](https://pypi.org/project/pint/), [quantulum3](https://pypi.org/project/quantulum3/) and spaCy rules for units, numbers and modals | Direct `.mdzip`/XMI parsing, SysML v2 text/KPAR/API, or [capellambse](https://pypi.org/project/capellambse/) for Capella; Docling or python-docx for Word | V parts; I ranking |
| 2 | Mechanical similarity ladder and fusion | Exact and near-exact collapse, then fuzzy, then TF-IDF/BM25, then dense embeddings with ANN top-k (k = 20-30), then cross-encoder and NLI re-scoring in both orders, then a calibrated logistic-regression stacker with slot-equality flags | [RapidFuzz](https://pypi.org/project/rapidfuzz/) on placeholder-masked text; [scikit-learn](https://pypi.org/project/scikit-learn/) TF-IDF; [sentence-transformers](https://pypi.org/project/sentence-transformers/) with Qwen3-Embedding-0.6B plus one of EmbeddingGemma 2, Granite-311M-R2 or BGE-M3; [FAISS](https://pypi.org/project/faiss-cpu/); bge-reranker-v2-m3; nli-deberta-v3-base; scikit-learn logistic regression and calibration | [datasketch](https://pypi.org/project/datasketch/) MinHash/LSH only above roughly 50k requirements; fastembed or Model2Vec for a light footprint; Splink for field-level matching; gradient-boosted trees after 1,000-2,000 labels | V parts; I recipe |
| 3 | Clustering | Cluster EQUIVALENT edges only; check cluster validity (minimum pairwise probability); enforce cannot-link from vetoes; choose a canonical representative | scikit-learn `AgglomerativeClustering`, average-link on distance 1 - P with `distance_threshold` | Correlation clustering (pivot or local search); HDBSCAN or Leiden for a separate "related topics" view | V properties; I settings |
| 4 | Relationship taxonomy | Label each pair EQUIVALENT, VARIANT, SUBSUMES, CONFLICT, COMPLEMENTARY or UNRELATED from slot diffs, bidirectional entailment and comparator direction | Rule-plus-NLI logic with a written labelling guideline and 3-5 examples per label | Multiclass softmax head with temperature scaling once labels exist; the four labels of GVD (duplicate, contradiction, asymmetric refinement, new knowledge) | I |
| 5 | AI proposal with deterministic vetoes | LLM judge only for the uncertain band (0.3 <= P < tau_high) or mechanical/AI disagreement, and for drafting diffs and merged text; structured JSON with verbatim evidence, both orders, N = 3 votes; ten code-level post-checks can veto | [LiteLLM](https://pypi.org/project/litellm/) (pinned, hash-locked, mirrored) in front of Ollama (dev), vLLM (GPU server) or llama.cpp (CPU); [Pydantic AI](https://pypi.org/project/pydantic-ai/) for typed outputs | Direct OpenAI-compatible SDK calls with no proxy; Instructor; Outlines or llguidance for small local models | V parts; I protocol |
| 6 | Human review lenses | Cluster-first queue in risk lanes; side-by-side token-level diff; "why suggested" panel; separate sign-offs for systems engineer, process engineer, UI/UX engineer and new user, modelled on Gerrit labels | Purpose-built React UI: TanStack Table plus Virtual, jsdiff, Cytoscape.js for exploration | Embed Label Studio (Apache-2.0) only as a labelling back-end | V patterns; I composition |
| 7 | Metrics | Per-source precision-recall and calibration, cluster-level B-cubed/ARI/AMI, mechanical-vs-AI agreement, workflow and safety metrics | scikit-learn plus DuckDB; Inspect AI and Promptfoo for AI regression; Langfuse (Docker Compose) for traces | DeepEval; OpenTelemetry spans written into the app's own Postgres | V tools; I metric set |
| 8 | Draft/approval lifecycle and audit | AI output is a separate proposal object that cannot write to approved fields; lifecycle suggested, in review, accepted/rejected/edited, approved, published; Doorstop-style fingerprints mark stale suggestions; append-only hash-chained events | Postgres event table with hash chaining, `eventsourcing` and `sqlalchemy-continuum` patterns, W3C PROV export | Dolt for branch/merge/diff on tables, or Git-tracked canonical exports per approved baseline | I (build-it); V parts |
| 9 | Export to document authoring | Render documents from the approved baseline with baseline ID and superseded IDs visible; ReqIF 1.2 round trip | [Sphinx](https://pypi.org/project/sphinx/) plus Sphinx-Needs; Pandoc with a reference .docx plus python-docx/docxtpl for Word | StrictDoc (SDoc, ReqIF, HTML/PDF); Typst for PDF | V parts; I flow |

**Cross-cutting platform default (V parts, I composition).** Python 3.12 or 3.13, FastAPI, SQLAlchemy 2 with Alembic, one PostgreSQL container with pgvector, and Procrastinate as a Postgres-backed job queue so no Redis or Celery is needed ([Procrastinate](https://pypi.org/project/procrastinate/)); React, Vite and TypeScript with an OpenAPI-generated client; GitLab CI with Podman or Docker and no Kubernetes. The alternative is SQLite with sqlite-vec as a single-file "project" mode behind the same repository interface ([sqlite-vec](https://pypi.org/project/sqlite-vec/)).

```
sources: ReqIF | .mdzip XMI | SysML v2 | XLSX/CSV | DOCX
   |  [1] parse -> normalise -> slots (modal, polarity, quantity+unit, condition) with char spans
   v
requirement records: original text + normalised text + slot spans + MID/UID
   |  [2] exact -> fuzzy -> TF-IDF/BM25 -> embeddings+ANN -> cross-encoder/NLI -> calibrated stacker
   v
candidate pairs with feature vectors and P(equivalent)
   |  [4] typed edges: EQUIVALENT | VARIANT | SUBSUMES | CONFLICT | COMPLEMENTARY
   |  [3] cluster EQUIVALENT edges only; validity check; cannot-link from vetoes
   v
clusters + typed links --(uncertain band or mech/AI disagreement)--> [5] AI proposal --> deterministic vetoes
   v
[6] human lenses (SE | PE | UX | NU) --> [8] draft -> approved lifecycle + audit log --> [9] export
        \______ [7] metrics on every source, mechanical and AI, computed from the same decision ledger ______/
```

**Placeholder operating numbers (I; the researchers state these are not validated and must be re-derived on the gold set).** The notes' starting points are: auto-suggest tier `tau_high` = calibrated P(equivalent) >= **0.95** with a lower confidence bound >= 0.90; review-queue floor `tau_low` = P of **0.15-0.30**, chosen so recall of gold equivalents is >= 0.90; clustering edge threshold `tau_edge` = **0.90**; minimum intra-cluster pairwise P `tau_min` = **0.5-0.6**; LLM band 0.3 <= P < 0.95; exact-duplicate fast path only when normalised text is equal, or placeholder-masked Jaccard >= 0.9 **and** all slots are equal; conflict candidates when NLI P(contradiction) >= 0.5 in either direction or the same actor, object and condition carry an incompatible quantity or modal. The notes explicitly warn not to hard-code cosine cut-offs because cosine scales differ between models; derive `tau_candidate` from the 99th percentile of random-pair cosine on the owner's own data.

## The catalog: nine categories of what to learn, borrow and build

The catalog follows the order you asked for. Each category states what the notes verified, what the researchers inferred, and where the evidence stops.

### Theory and math: scores that ignore negation, modals and numbers cannot decide anything alone

Treat every similarity score as evidence feeding a decision, never as the decision. The theory notes reach this from three directions: the behaviour of lexical metrics on requirement-shaped text, the known weakness of embeddings and NLI models on negation and numbers, and the instability of LLM judges.

#### Lexical methods collapse copies but miss the edits that matter

RapidFuzz offers `ratio`, `partial_ratio`, `token_sort_ratio`, `token_set_ratio` and `token_ratio` on a 0-100 scale; `token_set_ratio` scores "fuzzy was a bear" against "fuzzy fuzzy was a bear" at 100 ([RapidFuzz docs mirror](https://tessl.io/registry/tessl/pypi-rapidfuzz/3.14.0/files/docs/fuzzy-matching.md)). MinHash LSH in datasketch fixes its Jaccard threshold and `num_perm` at index creation and is approximate, with a `weights=(fp, fn)` trade-off ([datasketch README mirror](https://github.com/fpug/datasketch)). SimHash with 64 bits and Hamming distance k = 3 was validated for about 8 billion web pages, not for 20-word sentences ([Manku et al.](https://www.www2007.cpsc.ucalgary.ca/papers/paper215.pdf)). On real requirements specifications, clone detection found an average **13.6%** clone coverage (range 0% to about 72%) across 28 specifications totalling 8,667 pages, and reached 99% average precision after roughly ten minutes of tailoring per specification ([Juergens et al.](https://arxiv.org/abs/1711.05472)). Lexical methods stay competitive on sparse industrial text: string-level Jaccard reached F1 about 0.81 and TF-IDF 0.78 against 0.84 for ST-Roberta on benchmark pairs, and on confidential railway requirements Jaccard (rho about 0.50) and TF-IDF (about 0.49) correlated better with source-code similarity than GloVe or FastText (about 0.30), because 925 of 2,370 unique industrial words were out of vocabulary for word-embedding models ([Abbas et al.](https://www.es.mdu.se/pdf_publications/6922.pdf)).

The researchers ran a small experiment to show the blind spots (rapidfuzz 3.14.6 and scikit-learn 1.9.1; eight hand-written pairs; a toy, not a benchmark, and its numbers must not be reused as thresholds).

| Pair type | `ratio` | `token_set_ratio` | Jaro-Winkler | Word Jaccard | Char-3gram Jaccard | TF-IDF cosine |
|---|---|---|---|---|---|---|
| Negation ("shall log" vs "shall not log") | 95.9 | **100.0** | 0.94 | 0.89 | 0.87 | 0.79 |
| Modal swap (shall vs should) | 93.5 | 93.5 | 0.96 | 0.75 | 0.74 | 0.70 |
| Number change (5 s vs 50 s) | 98.8 | 98.8 | **1.00** | 0.75 | 0.88 | 0.66 |
| Unit-equivalent (5 seconds vs 5000 milliseconds) | 91.3 | 91.3 | 0.97 | 0.56 | 0.72 | 0.52 |
| Active vs passive, same meaning | 71.9 | 89.9 | 0.86 | 0.20 | 0.63 | 0.38 |
| Subset plus an extra major constraint | 68.0 | **90.3** | 0.90 | 0.36 | 0.48 | 0.56 |
| True paraphrase | 61.4 | 71.5 | 0.76 | 0.46 | 0.40 | 0.32 |
| Unrelated, same "The system shall ..." template | 64.3 | 64.3 | **0.89** | 0.27 | 0.24 | 0.11 |

Four conclusions follow, and the researchers state they are properties of the metrics rather than of the toy data (I). A negation, a modal change and a tenfold numeric change outscore a true paraphrase on character-level measures. `token_set_ratio` is blind to set containment and must never be used to claim "same requirement". Jaro-Winkler rewards a shared template prefix and is unsuitable for sentences. A unit-equivalent pair is penalised by every lexical score, so units must be normalised first. The recommended use of lexical methods is therefore three narrow jobs (I): exact and near-exact collapse, blocking for large sets (MinHash-LSH on word 2-3 shingles or character 4-5 grams), and an explainable overlap feature in the fusion model. Below about 20k requirements, skip LSH entirely and compute full pairwise TF-IDF or embedding similarity, because roughly 2x10^8 pairs at n = 20k is feasible with sparse or GPU matrix multiplication and LSH adds recall loss for little gain.

#### Embeddings, rerankers and NLI supply recall and direction, not decisions

Sentence-BERT-style bi-encoders compared by cosine are the recall tier ([Reimers and Gurevych](https://arxiv.org/abs/1908.10084)). Embeddings are weak where requirements are most fragile: PAWS-style adversarial pairs, negation and number handling are known failure areas ([PAWS](https://arxiv.org/abs/1904.01130); [negation benchmark](https://arxiv.org/abs/2310.15941); [numeracy probing](https://arxiv.org/abs/1909.07940); these are index blurbs, full texts unread), and the S3CDA paper reports SBERT cosines of 0.96 and 0.84 on OpenCoss conflict pairs where TF-IDF gave 0.44 and 0.16 ([S3CDA](https://arxiv.org/abs/2206.13690)), meaning a high cosine can coincide with a conflict. Zero-shot NLI used for conflict detection reached only **F1 22% to 55%** (ChatGPT 9% to 30%) and failed on conflicts that need a third requirement ([Fazelnia et al.](https://arxiv.org/abs/2405.05135)). The notes could not open the live MTEB leaderboard, so no "current rank" claim is made, and no independent benchmark of these models on requirement-pair similarity was found; the researchers recommend a local bake-off on the owner's own labelled pairs (I). Licences below are Hub tags as read on 2026-10-09.

| Model | Size | Licence (Hub tag) | Notes | Link |
|---|---|---|---|---|
| Qwen3-Embedding 0.6B / 4B / 8B | 0.6B / 4B / 7.6B | Apache-2.0 | Instruction-aware, 32k context; the 8B card claims No.1 on MTEB multilingual (70.58) as of 2025-06-05 (vendor claim) | [0.6B](https://hf.co/Qwen/Qwen3-Embedding-0.6B) ([paper](https://arxiv.org/abs/2506.05176)) |
| BGE-M3 | ~568M | MIT | Dense, sparse and multi-vector in one model; useful for hybrid lexical fusion | [hf.co/BAAI/bge-m3](https://hf.co/BAAI/bge-m3) |
| IBM Granite Embedding 311M / 97M R2 | 311M / 97M | Apache-2.0 | ModernBERT-based, 32k context, ONNX/OpenVINO shipped | [311m](https://hf.co/ibm-granite/granite-embedding-311m-multilingual-r2) |
| EmbeddingGemma 2 | 740M total (270M text) | Apache-2.0 tag, but the card links a Gemma 4 licence page | Vendor-reported MTEB English v2 68.46; created 2026-09-14; **read the licence before adopting** | [hf.co/google/embeddinggemma-2](https://hf.co/google/embeddinggemma-2) |
| EmbeddingGemma-300m | 303M | `gemma` licence, gated | One blog calls it Apache-2.0; the Hub tag says `gemma` and is authoritative | [hf.co/google/embeddinggemma-300m](https://hf.co/google/embeddinggemma-300m) |
| gte-modernbert-base; modernbert-embed-base | 149M each | Apache-2.0 | English ModernBERT bases | [gte](https://hf.co/Alibaba-NLP/gte-modernbert-base) |
| all-MiniLM-L6-v2; all-mpnet-base-v2 | 22.7M; 109.5M | Apache-2.0 | Classic baselines; MiniLM-L6 is the CPU-friendly floor | [MiniLM](https://hf.co/sentence-transformers/all-MiniLM-L6-v2) |
| jina-embeddings-v5-text-small / nano; jina-embeddings-v3 | ~0.6B / 239M | **CC-BY-NC-4.0** | Non-commercial; exclude unless programme licensing allows | [v5 small](https://hf.co/jinaai/jina-embeddings-v5-text-small) |
| llama-embed-nemotron-8b | ~8B | Custom NVIDIA **non-commercial** (per Modal blog) | Hub page not opened | [Modal blog](https://modal.com/blog/mteb-leaderboard-article) |

For re-scoring, the notes list BGE-reranker-v2-m3 and Qwen3-Reranker-0.6B (both Apache-2.0; [bge](https://hf.co/BAAI/bge-reranker-v2-m3), [qwen](https://hf.co/Qwen/Qwen3-Reranker-0.6B)) and flag jina-reranker-v3.5 as CC-BY-NC-4.0. For NLI, `cross-encoder/nli-deberta-v3-base` (Apache-2.0, 184M, SNLI test 92.38%, label order contradiction/entailment/neutral; [card](https://hf.co/cross-encoder/nli-deberta-v3-base)) and the MIT DeBERTa-v3-large mnli-fever-anli-ling-wanli model ([card](https://hf.co/MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli)) are the open candidates. No NLI checkpoint fine-tuned on requirements was found. The proposed NLI use (I): P(A entails B) and P(B entails A) both high means equivalent; one direction only means one requirement is stricter; high contradiction in either direction means a conflict candidate; both neutral but high cosine means complementary. Score both orders and average, since cross-encoders and NLI are asymmetric. Sentence-transformers' `community_detection` defaults to `min_community_size=10`, which must be lowered to 2 to find pairs ([SBERT retrieval utilities](https://sbert.net/docs/package_reference/util/retrieval.html)).

#### Requirement-specific literature is small, imbalanced and internally inconsistent

| Source | What it shows | Caveat |
|---|---|---|
| NLP4RE mapping: 404 studies, 130 new tools, 15 (11.54%) findable online ([Zhao et al.](https://arxiv.org/abs/2004.01099)) | Large gap between state of the art and practice; "Detection" includes equivalent requirements | Pre-LLM (to April 2019) |
| ReqSimile, 2001 ([Natt och Dag et al.](https://www.lunduniversity.lu.se/lup/publication/b13e16d5-f000-4ba4-a5ac-a9e2a29e864b)) | IR-style statistical similarity can find duplicate requirements and interdependencies | Foundational |
| PassionNet: 760 pipelines on six datasets ([arXiv 2412.01657](https://arxiv.org/abs/2412.01657)) | Best hybrid conflict-class F1 from **0.609** (OpenCoss) to **0.974** (PURE) | Text and Table 5 macro-F1 figures disagree |
| S3CDA: similarity, then entity-overlap filter ([arXiv 2206.13690](https://arxiv.org/abs/2206.13690)) | Threshold picked by maximising TPR - (1 - FPR); phase II filters on actors, actions, objects, metrics, operators | Synthetic conflicts dominate several sets |
| SR-BERT and dual-encoder follow-up ([2301.03709](https://arxiv.org/abs/2301.03709); [2511.23007](https://arxiv.org/abs/2511.23007)) | SBERT/SimCSE transfer learning, rule-based filter; ~10.4% in-domain and ~11.4% cross-domain macro-F1 gains | Abstract-level reading |
| Domain-specific sentence embeddings ([Das et al.](https://iris.unive.it/handle/10278/3736435)) | 88.35% accuracy, ~10% above benchmarks | Foundational, 2021 |
| VeriMed neurosymbolic auditing ([arXiv 2605.13817](https://arxiv.org/abs/2605.13817)) | LLM-to-SMT checking raised verified accuracy from 55.4% to 98.5% on a hemodialysis QA benchmark | Route to proof-backed redundancy/conflict evidence for formalisable requirements only |
| Annotator agreement ([Dalpiaz et al.](https://webspace.science.uu.nl/~dalpi001/papers/dalp-dell-ayde-cevi-19-re.pdf)) | Only 1 of 16 Krippendorff alpha values exceeded 0.8 on functional/quality tagging | No agreement study exists for a four- or five-way requirement relationship taxonomy |

The EARS slot idea, comparing actor, action, object, condition, state, constraint, quantity-plus-unit and modal slot by slot and showing a slot diff, is the most human-verifiable layer, but **no paper validates slot-wise similarity against human equivalence judgements**, so it is a design hypothesis to test on the gold set (I). Extraction options are regex and dependency rules for When/While/If-then/Where, a spaCy dependency parse, or an LLM with JSON-schema output validated by the rule that every slot value is a literal substring of the source. EARS itself is described in [Mavin et al.](https://research.manchester.ac.uk/en/publications/easy-approach-to-requirements-syntax-ears/), and RFC 2119 and NASA's handbook fix modal semantics (MUST/SHALL absolute, SHOULD a valid-reasons exception, MAY optional; NASA treats "will" as a statement of fact and "should" as a goal) ([RFC 2119](https://rfc-editor.org/rfc/rfc2119); [NASA SEH Appendix C](https://www.nasa.gov/seh/appendix-c-how-to-write-a-good-requirement)).

#### Fusion and calibration: rank fusion for candidates, calibrated stacking for decisions

Reciprocal rank fusion, `RRF(d) = sum over sources of 1 / (k + rank)` with k = 60, is label-free, insensitive to k in the pilot, and on TREC runs beat Condorcet Fuse in every case, CombMNZ in all but one, and the best individual run in all but one collection; it yields rankings, not probabilities, so use it for candidate generation only ([Cormack et al.](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf)). For decisions, the researchers recommend a logistic-regression stacker over lexical scores, two or three embedding cosines, the cross-encoder logit, NLI probabilities in both directions, and boolean slot-equality flags (modal, polarity, quantities after unit conversion, actor, object), trained on human labels with L2 regularisation and symmetric features (I). Calibration follows scikit-learn guidance: sigmoid (Platt) for small samples, isotonic only above about **1,000** calibration samples because it overfits, temperature scaling for multiclass heads, and a calibrator fitted on data independent of the classifier's training data ([scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html); [Guo et al.](https://arxiv.org/abs/1706.04599)). Fellegi-Sunter match weights, `log2(m/u)` per comparison level, give human-readable evidence ("modal verbs equal: +2.1 bits; quantity differs: -6.4 bits" is the researchers' illustration), but embedding cosines are correlated and break the independence assumption, so a fitted regression is preferred ([Splink overview](https://www.gov.uk/government/publications/joined-up-data-in-government-the-future-of-data-linking-methods/splink-mojs-open-source-library-for-probabilistic-record-linkage-at-scale)).

Three further rules carry weight (all I). First, prevalence: a pool of 10,000 requirements with 1,000 duplicate pairs has per-pair prevalence near 2x10^-5, so evaluate on the candidate distribution the system actually produces, or prior-correct with `logit p' = logit p + log(pi_new/(1 - pi_new)) - log(pi_train/(1 - pi_train))`. Second, a three-zone policy: P >= `tau_high` shows an evidence-backed suggestion, `tau_low` <= P < `tau_high` goes to a review queue ordered by uncertainty, and P < `tau_low` stays hidden; thresholds come from the precision-recall curve with a Wilson or Clopper-Pearson lower bound, are logged with a version, and are re-estimated about every 200 new human decisions. Third, active learning: sample around the boundary (P in 0.3-0.7) mixed with 10-20% random and 10-20% diverse items, add hard negatives from minimal-pair perturbations and mechanical/AI disagreements, keep an untouched random audit set of about 300 pairs, and split every dataset by requirement document or connected component, never by pair, to prevent leakage. Conformal prediction could give a recall guarantee for the review queue but assumes exchangeability that breaks across programmes ([Angelopoulos and Bates](https://arxiv.org/abs/2107.07511), listed only, not opened).

#### Clustering: single-link chaining is the main failure, so cluster typed, calibrated edges

Thresholded connected components are single linkage: one weak bridge merges two clusters, and "respond within 2 s" ~ "within 3 s" ~ ... ~ "within 10 s" chains to unrelated ends. If each adjacent pair is right with probability p, a k-hop endpoint pair is right with probability about p^k, so p = 0.95 over five hops gives about **0.77** (independence assumption, I). The mitigations the researchers rank by cost are a high edge threshold plus a minimum-pairwise-probability validity check, complete- or average-link agglomeration, correlation clustering, splitting failing clusters with Leiden or minimum cuts, and hard cannot-link edges from vetoes. They argue average or complete link beats HDBSCAN as the default because requirement sets are mostly singletons with small tight groups, a "find the small cliques" problem; HDBSCAN suits a second, topic-like "related" view (I).

| Method | Strength | Failure mode | Starting settings (I) |
|---|---|---|---|
| Thresholded components (single link) | Trivial and explainable | Chaining, giant components | Only after a high-precision edge filter; monitor largest component |
| scikit-learn agglomerative, `linkage="average"` or `"complete"`, `distance_threshold` | Bounded diameter (complete); no cluster count | O(n^2) memory; threshold is model-specific | `distance_threshold = 1 - tau_edge` |
| HDBSCAN ([how it works](https://hdbscan.readthedocs.io/en/latest/how_hdbscan_works.html)) | Flags noise; no cosine threshold | Can be too coarse for number-only differences | `min_cluster_size=2`, `min_samples=1-2`; the `leaf` option comes from library knowledge, not the fetched page |
| Leiden ([Traag et al.](https://arxiv.org/abs/1810.08473)) | Guarantees connected communities; Louvain produced badly connected ones in up to 25% of experiments | Resolution limit; no pairwise-similarity guarantee | Tune resolution on the gold set; post-validate |
| Correlation clustering ([Bansal et al.](https://mlanthology.org/mlj/2004/bansal2004mlj-correlation)) | Principled with uncertain pairs; number of clusters is not an input | Needs calibrated edges; NP-hard | Edge weight `log(p/(1 - p))`, cut at p = 0.5 |

For the canonical requirement of a cluster, the researchers propose a priority order (I): a human-designated baseline requirement first, then the member maximising `w1*centrality + w2*completeness + w3*quality + w4*authority` (centrality as mean pairwise probability or medoid; completeness as filled slots; quality as lint pass; authority as source priority or baselined status). An LLM-drafted merged text must cite every contributing ID, pass the deterministic preservation checks and appear as a diff against the representative; the notes found no sourced evidence for any canonical-selection rule, so this is a proposal. New requirements arriving later attach to a cluster only if they clear the threshold against the representative and a quorum of members, and human-approved clusters are pinned as must-link constraints.

#### Relationship taxonomy: six labels with operational tests, and comparator direction

No standard defines duplicate-of, conflicts-with or supersedes (see Standards), so the taxonomy is the app's own contract. The working definitions below are the researchers' synthesis of GVD's relation set and the NLI-direction logic, with no published human-agreement study for requirements, so measuring inter-annotator agreement is part of the project (I).

| Label | Operational test | Action |
|---|---|---|
| EQUIVALENT | Mutual entailment and all slots equal after normalisation | Merge into one canonical requirement; keep other IDs as aliases for traceability |
| VARIANT | Same actor, action and object but at least one slot value differs (number, unit, tolerance, modal, condition) | Never auto-merge; show the slot diff; a human decides which value applies |
| SUBSUMES | A entails B but not B entails A (A stricter or adds a constraint) | Keep A and mark B derived/satisfied, or keep both with a parent-child link |
| CONFLICT | Both cannot be satisfied: contradiction, incompatible values for one quantity, mutually exclusive states | Escalate; never merge |
| COMPLEMENTARY | Jointly specify one behaviour, neither implies the other | Link; consider a parent requirement |
| UNRELATED | None of the above | No action |

Direction matters: "respond within 2 s" satisfies "respond within 5 s", but for a minimum such as ">= 99.9% availability" the larger number is the stricter, so the engine must store the comparison operator per quantity slot. "Within 2 s" versus "within 5 s" is not a conflict because both can hold, while "exactly 5 s" versus "exactly 10 s" is. The standards note states the blunter rule that requirements with different numerical values on a shared subject must surface as conflicts, not duplicates; the safe reconciliation is that such pairs are never auto-merged and are labelled VARIANT or CONFLICT according to the comparator (I).

#### LLM judges are unstable and biased, so demand structured evidence and ten code-level vetoes

LLM judges matched human preference with over 80% agreement in the original study (GPT-4 85% against 81% human-human) but show position and verbosity bias, which swapping positions and counting only consistent wins mitigates ([Zheng et al.](https://arxiv.org/abs/2306.05685)); position bias varies by judge and task and grows with the quality gap ([Shi et al.](https://arxiv.org/abs/2406.07791)); the CALM framework names 12 biases ([Ye et al.](https://arxiv.org/abs/2410.02736)). Run-to-run stability is the sharper problem: three open-weight judges run three times on identical prompts reached self-agreement Krippendorff's alpha of **0.33 / 0.63 / 0.79** on factual consistency and **0.27 / 0.51 / 0.56** on MT-Bench pairwise, a majority vote over three runs improved balanced accuracy, and more than three runs did not change reliability ([Haldar and Hockenmaier](https://arxiv.org/abs/2510.27106)). Newer 2026 work, known only from index summaries, adds rationalisation bias, overlap bias and position bias in rubric scoring ([2605.23970](https://arxiv.org/abs/2605.23970); [2602.07673](https://arxiv.org/abs/2602.07673); [2602.02219](https://arxiv.org/abs/2602.02219)). No peer-reviewed evaluation of LLM judges for requirement equivalence with slot-level evidence was found.

The proposed judge protocol (I; design proposals, not published methods): feed the judge the two texts verbatim with IDs and the extracted slot tables but withhold mechanical scores so it stays an independent signal; run (A,B) and (B,A) with randomised ID labels, N = 3 samples each at temperature 0.3-0.7, aggregate by majority and keep the vote fraction as a calibrated feature; ask for per-slot verdicts before the overall relation; and require constrained JSON with verbatim quotes and character-offset spans.

```
{ "pair": {"a_id": "...", "b_id": "..."},
  "relation": "EQUIVALENT|VARIANT|A_SUBSUMES_B|B_SUBSUMES_A|CONFLICT|COMPLEMENTARY|UNRELATED|UNSURE",
  "slots": [{"slot":"quantity","a":{"text":"5 seconds","span":[34,43]},"b":{"text":"5000 ms","span":[36,43]},
             "relation":"EQUAL_AFTER_NORMALISATION"}],
  "differences": [{"kind":"modal|number|unit|negation|actor|object|condition|scope|other","a_span":[..],"b_span":[..],"material":true}],
  "evidence": {"a_quotes":["..."],"b_quotes":["..."]},
  "confidence": 0-100, "abstain_reason": null }
```

| # | Deterministic post-check (pure code, logged pass/fail in the UI) | Effect |
|---|---|---|
| 1 | Every cited requirement ID exists in the input pair | Reject |
| 2 | Every quote is a verbatim substring (whitespace-normalised) of the cited source | Reject paraphrased "quotes" |
| 3 | Number preservation via quantulum3 or regex plus Pint; different values with an EQUIVALENT verdict | Hard veto unless equal after unit conversion |
| 4 | Units normalised to SI and compared with relative tolerance; unit present in one text only | Flag |
| 5 | Modal tag mismatch (SHALL / SHALL NOT / SHOULD / WILL / MAY / MUST) with an EQUIVALENT verdict | Veto |
| 6 | Polarity: not/no/never/without/unless/prevent/inhibit/fail plus a domain antonym list (enable/disable, open/close) | Veto on mismatch |
| 7 | Count and compare conditional clauses (if/when/while/unless/where/after/before/during) | Dropped condition downgrades EQUIVALENT to VARIANT or SUBSUMES |
| 8 | Actors, acronyms, part numbers and signal names match or are listed as differences | Flag |
| 9 | Merged text length within 0.8-1.3x of the longer source and no new non-stoplist tokens absent from both sources | Catches invented content |
| 10 | Round-trip NLI both ways between merged text and each source | Any contradiction vetoes |

The researchers list seven failure modes to design against (I): hallucinated merges that ignore a number, tolerance, modal, negation, condition or actor; over-merging on boilerplate such as "The system shall"; order effects; verbosity bias; rationalisation; run-to-run instability; and human anchoring on the AI verdict. A planned anchoring test shows 30% of sampled items to reviewers without the AI verdict.

#### Math toolbox

Formulas marked "background" are standard definitions the researchers wrote from knowledge and did not re-derive from a fetched paper.

| Concept | Formula or rule | Use here | Source |
|---|---|---|---|
| Normalised Levenshtein; RapidFuzz `ratio` | `1 - lev/max(len)`; indel variant `1 - indel/(len_a + len_b)` | Lexical tier | background |
| Jaccard; containment | `abs(A and B)/abs(A or B)`; containment `abs(A and B)/abs(A)` is asymmetric | Containment is the primitive for subsumption candidates | background |
| TF-IDF cosine; BM25 | `w = (1 + log tf) * log(N/df)`; BM25 is asymmetric, so symmetrise (max or mean) | Sparse tier | background |
| MinHash and LSH | `Pr[min match] = J`; error about `sqrt(J(1-J)/num_perm)`; band retrieval `1 - (1 - J^r)^b` | Blocking above ~50k items | [datasketch](https://github.com/fpug/datasketch) for behaviour; formulas background |
| Cosine on L2-normalised vectors | `abs(u - v)^2 = 2(1 - cos)`; re-normalise after Matryoshka truncation; thresholds never transfer between models | Dense tier | background |
| Reciprocal rank fusion | `sum 1/(60 + rank)` | Candidate ordering | [Cormack et al.](https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf) |
| Platt, isotonic, temperature scaling | `p = 1/(1 + exp(A f + B))`; softmax(z/T) | Calibrated probabilities | [scikit-learn](https://scikit-learn.org/stable/modules/calibration.html) |
| Prior shift | `logit p' = logit p + log(pi_new/(1-pi_new)) - log(pi_train/(1-pi_train))` | Moving between pools | background |
| Chain probability | about `p^k` | Why single link fails | inference |
| Correlation clustering | Minimise "+" edges cut plus "-" edges kept | Triangle-violation penalty | [Bansal et al.](https://mlanthology.org/mlj/2004/bansal2004mlj-correlation) |
| HDBSCAN mutual reachability | `max(core_k(a), core_k(b), d(a,b))` | Density view | [HDBSCAN docs](https://hdbscan.readthedocs.io/en/latest/how_hdbscan_works.html) |
| B-cubed | Per item `P_e = abs(C(e) and L(e))/abs(C(e))`, `R_e = abs(C(e) and L(e))/abs(L(e))`, averaged over all items including singletons | Cluster metric; only BCubed satisfied all formal constraints in a classic comparison | [Amigo et al.](https://e-spacio.uned.es/entities/publication/7c9fc169-a6c8-4008-8515-7bc304c6ddd5/full) |
| Rand, ARI, NMI, AMI | RI is near 1.0 even for different clusterings; ARI and AMI are chance-adjusted | Secondary cluster summaries | [scikit-learn](https://scikit-learn.org/stable/modules/clustering.html) |
| Cohen's kappa, Krippendorff's alpha | `kappa = (p_o - p_e)/(1 - p_e)`; `alpha = 1 - D_o/D_e`; add raw agreement and positive-specific agreement `2a/(2a+b+c)` because rare positives depress kappa | Agreement | background; [Landis and Koch](https://pubmed.ncbi.nlm.nih.gov/843571/) abstract only |
| Precision sample size | `n = 1.96^2 * p(1-p)/d^2`, about 200 accepted pairs for p = 0.95, +/-3 points | Gold-set sizing | background |

### Libraries: one default and one alternative per component, with licence and maintenance flags attached

Every row below is V for version, licence and date (registry data pulled on 2026-10-09) and I for the default-versus-alternative choice, which is the researchers' assessment. GitHub's API and HTML were blocked during the research, so "last activity" means the latest registry release unless a GitHub page is cited. Registry trove labels (Beta, Alpha) are maintainers' self-declared. Standardise the whole backend on **Python 3.12 or 3.13**: Pint, NetworkX, text-dedup and Sphinx need 3.12 or newer, while Unstructured, Outlines and guardrails-ai cap below 3.14.

**Interchange and ingestion**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| ReqIF | [`reqif`](https://pypi.org/project/reqif/) 0.1.0 (2026-08-11), Apache-2.0; parses and unparses ReqIF, pretty-prints, validates, **anonymises files for safe sharing** | [StrictDoc](https://pypi.org/project/strictdoc/) 0.30.2 (2026-10-09), Apache-2.0, with its own ReqIF and XLSX import/export | `reqif` is 0.x; dialects and XHTML rich text vary by tool, so budget a normalisation layer and per-tool fixtures (I). [pyreqif](https://pypi.org/project/pyreqif/) is stale (2021) |
| Capella models | [capellambse](https://pypi.org/project/capellambse/) 0.8.1 (2026-01-20), Apache-2.0 AND OFL-1.1; reads Capella without Java | [Eclipse Capella](https://projects.eclipse.org/projects/polarsys.capella) 7.1.0 (2026-07-10, EPL-2.0) as a sidecar | Releases 3 in 12 months |
| SysML v2 | [SysML-v2-Release](https://github.com/Systems-Modeling/SysML-v2-Release/releases) monthly tags (2026-04 latest); text `.sysml`, KPAR and the REST API | Pilot Implementation / SysON as sidecar services (EPL-2.0, Java) | The official Python API client is LGPL-3.0 and last updated 14 Oct 2021; Syside's `syside` is **proprietary**; no verified open Python library reads SysML v2 natively |
| ALM clients | [polarion-rest-api-client](https://pypi.org/project/polarion-rest-api-client/) 2.3.3 (Apache-2.0) | CSV/XLSX export route | [py-jama-rest-client](https://pypi.org/project/py-jama-rest-client/) stale (2023); none found for DOORS or Codebeamer |
| Spreadsheets | pandas 3.0.6 plus [python-calamine](https://pypi.org/project/python-calamine/) 0.8.3 (MIT) | [openpyxl](https://pypi.org/project/openpyxl/) 3.1.5 (2024-06-28) for write/format-aware work | openpyxl and python-docx have no release in 12 months; the researchers read that as stability |
| Word and PDF | [python-docx](https://pypi.org/project/python-docx/) 1.2.0 (MIT) plus lxml for numbering and tracked-change gaps; [Docling](https://pypi.org/project/docling/) 2.137.0 (MIT) | [MarkItDown](https://pypi.org/project/markitdown/) (MIT, Beta), [Unstructured](https://pypi.org/project/unstructured/) (Apache-2.0), mammoth | PyMuPDF licence **unverified**; pdfplumber (MIT) avoids the question |

**Mechanical and semantic similarity**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| Fuzzy / lexical | [RapidFuzz](https://pypi.org/project/rapidfuzz/) 3.14.6 (MIT, 2026-08-30) | [bm25s](https://pypi.org/project/bm25s/) 0.3.13 (MIT) or scikit-learn TF-IDF | `rank-bm25` (2022), `textdistance` (2024), `simhash` (2022) are stale |
| Near-duplicate | [datasketch](https://pypi.org/project/datasketch/) 2.0.0 (MIT) | [text-dedup](https://pypi.org/project/text-dedup/) 0.4.1 (Apache-2.0 per repo; Python 3.12+) | Script-style interface; datasketch gives more control for an interactive app (I) |
| Field-level linkage | [Splink](https://pypi.org/project/splink/) 5.0.0 (MIT) | Custom NetworkX tree/graph comparison | [dedupe](https://pypi.org/project/dedupe/) (2024-08-15) and recordlinkage (2023) are effectively dormant |
| Embeddings | [sentence-transformers](https://pypi.org/project/sentence-transformers/) 6.1.0 (Apache-2.0) with Qwen3-Embedding-0.6B or BGE-M3 | [fastembed](https://pypi.org/project/fastembed/) 0.9.0 (ONNX, no PyTorch) or [Model2Vec](https://pypi.org/project/model2vec/) | Avoid jina-embeddings-v3 (CC-BY-NC) and EmbeddingGemma (gated, Gemma licence) where redistribution or air-gapped provisioning matters |
| Semantic dedup helper | [SemHash](https://pypi.org/project/semhash/) 0.5.0 (MIT, Beta) | Own FAISS threshold search | Pre-1.0: wrap behind your own interface |
| ANN index | [FAISS](https://pypi.org/project/faiss-cpu/) 1.15.1 (MIT) | [USearch](https://pypi.org/project/usearch/) 2.26.4 (Apache-2.0) | [hnswlib](https://pypi.org/project/hnswlib/) last released 2023-12-03: poor new dependency |
| Clustering | scikit-learn agglomerative; [hdbscan](https://pypi.org/project/hdbscan/) 0.8.44 (BSD, Beta) | UMAP (Alpha) for visualisation only | Whether scikit-learn 1.9.1 ships HDBSCAN is background knowledge, not verified |
| NLI / rerank / few-shot | `cross-encoder/nli-deberta-v3-base`, `bge-reranker-v2-m3`; [SetFit](https://pypi.org/project/setfit/) 1.2.0 (Apache-2.0) | MoritzLaurer DeBERTa NLI (MIT); Qwen3-Reranker-0.6B | NLI models are trained on captions and news, not requirements: show scores as flags for review only (I) |
| Units and numbers | [Pint](https://pypi.org/project/pint/) 0.26.1 (BSD, Beta, Python 3.12+) with [quantulum3](https://pypi.org/project/quantulum3/) 0.10.0 (MIT, Alpha) | Regex rules | `number-parser` stale (2023); no paper found evaluating unit-normalised requirement comparison |
| Negation, modality, EARS | [spaCy](https://pypi.org/project/spacy/) 3.8.16 (MIT) Matcher/DependencyMatcher rules, built in-house; [vale-ears](https://github.com/tbhb/vale-ears) as a rule specification | [negspacy](https://pypi.org/project/negspacy/) 1.1.0 (MIT) | **No maintained EARS or modal-verb parser library was found**; vale-ears has 0 stars and 12 commits, so re-implement its rules rather than depend on it |

**Storage, graph and audit**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| Primary store | PostgreSQL plus pgvector ([PostgreSQL licence](https://raw.githubusercontent.com/pgvector/pgvector/HEAD/LICENSE)), [SQLAlchemy](https://pypi.org/project/sqlalchemy/) 2.1.4 and [Alembic](https://pypi.org/project/alembic/) | SQLite plus sqlite-vec 0.1.9 as a single-file project mode | [psycopg](https://pypi.org/project/psycopg/) 3 is LGPL-3.0-only (normally fine when dynamically linked from Python; background knowledge). sqlite-vec is pre-1.0 |
| Analytics | [DuckDB](https://pypi.org/project/duckdb/) 1.5.6 (MIT) over exported Parquet/SQLite | Polars 2.0.0 | 90 releases in 12 months: pin |
| Vector DB if outgrown | pgvector | [Qdrant](https://github.com/qdrant/qdrant/releases) (Apache-2.0, v1.19.2) or [LanceDB](https://pypi.org/project/lancedb/) (Alpha) | No load test was run at target scale |
| Job queue | [Procrastinate](https://pypi.org/project/procrastinate/) 3.10.0 (MIT) | Plain Python state machine plus a durable job table | Avoids Redis and Celery |
| Graph | [NetworkX](https://pypi.org/project/networkx/) 3.7 (BSD-3) over edge tables | LadybugDB (MIT; Kuzu successor; version from a secondary blog) | **Kuzu archived 2025-10-10**; python-igraph is GPL |
| Audit and versioning | Hash-chained append-only event table (**build-it; no library found**) with [eventsourcing](https://pypi.org/project/eventsourcing/) and [SQLAlchemy-Continuum](https://pypi.org/project/sqlalchemy-continuum/) patterns, [prov](https://pypi.org/project/prov/) export | [Dolt](https://github.com/dolthub/dolt/releases) (Apache-2.0) for table-level diff/branch/merge | [lakeFS](https://raw.githubusercontent.com/treeverse/lakeFS/HEAD/LICENSE) and [immudb](https://raw.githubusercontent.com/codenotary/immudb/HEAD/LICENSE) are BSL, not OSI open source; doltpy/doltcli wrappers are stale |

**LLM plumbing, agents and MCP**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| Gateway | [LiteLLM](https://pypi.org/project/litellm/) 1.104.2 (MIT; **252 releases in 12 months**), pinned, hash-locked, mirrored | Direct OpenAI-compatible SDK calls | **Supply-chain incident reported in March 2026**; see Risks. Keep app code on the OpenAI-compatible API so the gateway can be swapped (I) |
| Local inference | [Ollama](https://github.com/ollama/ollama/releases) v0.40.2 (MIT, dev machines); [vLLM](https://pypi.org/project/vllm/) 0.31.0 (Apache-2.0, GPU server) | [llama.cpp](https://github.com/ggml-org/llama.cpp/releases) (MIT, CPU or small GPU) | OpenAI-compatible endpoints are background knowledge. Candidate open judges (Apache-2.0): gpt-oss-20b/120b and Qwen3.8-27B; **their accuracy on requirements was not evaluated** |
| Typed outputs | [Pydantic AI](https://pypi.org/project/pydantic-ai/) 2.55.0 (MIT; 200 releases in 12 months) | [Instructor](https://pypi.org/project/instructor/) 1.17.0 (MIT); [Outlines](https://pypi.org/project/outlines/) or llguidance for hard constrained decoding on small local models | Constrained decoding only if small models cannot emit valid JSON (I) |
| Orchestration | Plain Python state machine plus Procrastinate jobs | [LangGraph](https://pypi.org/project/langgraph/) 1.2.14 (MIT) for durable pause/resume at approval nodes | Heavy frameworks are optional for a fixed pipeline (I) |
| MCP | [`mcp`](https://pypi.org/project/mcp/) Python SDK 2.3.0 (MIT), or [FastMCP](https://pypi.org/project/fastmcp/) 4.1.0 (Apache-2.0) | `@modelcontextprotocol/sdk` (TypeScript) | The Python SDK page recommends pinning `mcp>=1.28,<2` until migrating. The TypeScript licence discrepancy (npm says MIT, repo file begins Apache-2.0) is explained on the [SDK's GitHub page](https://github.com/modelcontextprotocol/typescript-sdk) as Apache-2.0 for new contributions and MIT for existing code |
| Claude Agent SDK | [Python package](https://pypi.org/project/claude-agent-sdk/) 0.2.165 (MIT, Alpha) | MCP SDK directly | The TypeScript package is under Anthropic commercial terms ([licence file](https://raw.githubusercontent.com/anthropics/claude-agent-sdk-typescript/HEAD/LICENSE.md)): not strictly OSS |

**Evaluation, tracing and annotation**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| LLM evals | [Inspect AI](https://pypi.org/project/inspect-ai/) 0.3.278 (MIT) plus [Promptfoo](https://www.npmjs.com/package/promptfoo) 0.124.1 (MIT) for CI regression | [DeepEval](https://pypi.org/project/deepeval/) 4.2.8 (Apache-2.0) | Promptfoo's README says it is now part of OpenAI and remains MIT; a secondary report notes licence and governance are not irrevocably committed. Ragas slowed to 7 releases in 12 months |
| Pair-level metrics | scikit-learn plus DuckDB | Polars | Plain Python (I) |
| Tracing | [Langfuse](https://github.com/langfuse/langfuse) (MIT except `ee` folders), self-hosted with Docker Compose on one VM | OpenTelemetry/OpenInference spans into the app's own Postgres | Langfuse documents Kubernetes/Helm as the preferred production path; the exact Compose service set and offline operation are **unverified**. [Arize Phoenix](https://pypi.org/project/arize-phoenix/) is Elastic-2.0 |
| Annotation | [Label Studio](https://pypi.org/project/label-studio/) 1.23.2 (Apache-2.0) | Purpose-built React UI | Argilla's authors have moved on (bug fixes only); doccano release 1.8.4 was 2023 in one note (1.8.5 in 2026-01 in another); Prodigy is paid |

**Front end (React 19.3, Vite 8.3, TypeScript 7.0, Vitest 5.0)**

| Component | Default | Alternative | Flags |
|---|---|---|---|
| Large grid | [TanStack Table](https://www.npmjs.com/package/@tanstack/react-table) 9.2.8 plus [TanStack Virtual](https://www.npmjs.com/package/@tanstack/react-virtual) (MIT) | [AG Grid Community](https://www.npmjs.com/package/ag-grid-community) 36.2.0 (MIT) | AG Grid's row grouping and pivoting are commercial; Handsontable is not OSI-licensed; Glide, mantine-react-table and material-react-table are stale; TanStack Table v9 migration impact not researched |
| Typed API | FastAPI OpenAPI plus [openapi-typescript](https://www.npmjs.com/package/openapi-typescript) 7.13.0 | Orval | `@hey-api/openapi-ts` has 541 releases in 12 months: pin |
| Graph exploration | [Cytoscape.js](https://www.npmjs.com/package/cytoscape) 3.34.3 (MIT) for duplicate-group graphs up to a few thousand nodes | [Sigma.js](https://www.npmjs.com/package/sigma) 4.0.0 (WebGL; shipped the day before the research, check `@react-sigma/core` compatibility); [React Flow](https://www.npmjs.com/package/@xyflow/react) for editable flows | `reactflow` is superseded by `@xyflow/react`; [embedding-atlas](https://www.npmjs.com/package/embedding-atlas) (MIT, pre-1.0) for embedding-cluster maps |
| Diff and merge | [jsdiff](https://www.npmjs.com/package/diff) 9.0.0 `diffWords` with a custom component | [@codemirror/merge](https://www.npmjs.com/package/@codemirror/merge) 6.12.2; [react-diff-viewer-continued](https://www.npmjs.com/package/react-diff-viewer-continued) 4.4.0 | Google `diff-match-patch` **archived 2024-08-05**; original `react-diff-viewer` last released 2020 |
| Rich-text tracked changes | [Tiptap](https://www.npmjs.com/package/@tiptap/core) 3.31.4 with [@manuscripts/track-changes-plugin](https://www.npmjs.com/package/@manuscripts/track-changes-plugin) 2.4.0 (Apache-2.0) after a spike | [tiptap-track-changes](https://github.com/sungkhum/tiptap-track-changes) 0.2.1 (15 stars) or hand-built suggestion marks | Neither is proven; the manuscripts plugin's repo could not be identified from npm; whether Tiptap sells a track-changes extension was not checked |
| UI kit | [shadcn](https://www.npmjs.com/package/shadcn) on radix-ui and Tailwind 4.3 (components are copied in, so no runtime dependency) | [React Aria Components](https://www.npmjs.com/package/react-aria-components) 1.22.1 (Apache-2.0; strongest accessibility story) | Base UI package renamed to `@base-ui/react`; React 19.3 / Tailwind 4.3 compatibility untested |
| Charts | [Recharts](https://www.npmjs.com/package/recharts) 3.10.1 | [ECharts](https://www.npmjs.com/package/echarts) 6.1.0 for dense 10^4-point scatter | Observable Plot has had no npm release since Feb 2025 |
| Test and accessibility | [Playwright](https://www.npmjs.com/package/@playwright/test) 1.64.0, [@axe-core/playwright](https://www.npmjs.com/package/@axe-core/playwright) (MPL-2.0), Storybook, Vitest | n/a | Storybook (828) and Playwright (562) release constantly: use lockfiles and batched updates |

**Platform notes (I).** For an air-gapped build, mirror PyPI and npm internally with hash-locked lockfiles, pre-download all model weights (embedding, reranker, NLI, chat), and vendor Pandoc and Playwright browsers into the CI image; none of this was tested, and container-image provenance for Postgres/pgvector, Qdrant, Langfuse, Ollama and vLLM was not verified because Docker Hub and ghcr.io were unreachable. Put every third-party dependency behind a small interface (similarity method, vector index, LLM client, diff renderer) so archived or stale picks can be swapped with limited blast radius. The researchers rank the riskiest prototypes first: the ReqIF round trip across the owner's real exports, Tiptap track-changes maturity, Langfuse offline operation, the embedding shortlist on the owner's labelled pairs, and the hash-chained audit log with an auditor-style verifier script.

### Existing tools and sample projects: every ingredient exists, none combines them

The researchers sorted the open-source field into tools with 2026 evidence of life and dormant ones, then mined commercial products for review patterns. The open-source requirements tools (StrictDoc, Doorstop, Sphinx-Needs, TRLC) focus on authoring, traceability, linting and publishing of one project; none of the pages opened describes cross-project comparison or consolidation ([StrictDoc guide](https://strictdoc.readthedocs.io/en/stable/stable/docs/strictdoc_01_user_guide.html); [Doorstop](https://github.com/doorstop-dev/doorstop); [Sphinx-Needs](https://github.com/useblocks/sphinx-needs); [TRLC](https://pypi.org/project/trlc/)).

#### Open-source requirements and MBSE tools

| Tool | Evidence (2026) | Licence | What to take from it (I) |
|---|---|---|---|
| [StrictDoc](https://github.com/strictdoc-project/strictdoc) | 0.30.2 on 2026-10-09; ~380 stars; web UI, ReqIF and XLSX import/export, diff/changelog screen built on stable machine IDs; its server is documented as not yet hardened | Apache-2.0 | Safe dependency or alternative store; copy the MID/UID split and the static-HTML-plus-local-server delivery model |
| [Doorstop](https://github.com/doorstop-dev/doorstop) | 3.2 on 2026-07-10; ~667 stars; one YAML file per item | LGPL-3.0 | Its `reviewed` field stores an item's fingerprint at last review, so a mismatch reveals unreviewed change ([item reference, v1.3 docs](https://doorstop.readthedocs.io/en/v1.3/reference/items/)); reuse the idea to mark AI suggestions stale when a source requirement changes |
| [Sphinx-Needs](https://github.com/useblocks/sphinx-needs) | 8.5.0 on 2026-09-03; ~304 stars; needtable, needflow, needpie, needbar views | MIT | Report types; a test-reports command can emit `needs.json` without a full Sphinx build, a model for headless CI runs |
| [TRLC](https://pypi.org/project/trlc/) | 3.1.0 on 2026-09-30 | GPL-3.0-or-later | Strong copyleft: borrow ideas (typed schema, user-defined check rules, Python API for diff and impact analysis), not code |
| [BASIL](https://github.com/elisa-tech/BASIL) | ~61 stars; REST API; imports SPDX 3, CSV, XLSX; ships Containerfiles | GPL-2.0 | Ideas only |
| [Eclipse Capella](https://projects.eclipse.org/projects/polarsys.capella) and [capellambse](https://github.com/dbinfrago/py-capellambse) | Capella 7.1.0 (2026-07-10); capellambse example notebook 06 finds requirements, shows their traces and exports to Excel or ReqIF | EPL-2.0; Apache-2.0 AND OFL-1.1 | Capella ingestion path |
| [SysON](https://projects.eclipse.org/projects/modeling.syson) and the SysML v2 Pilot Implementation / API Services | SysON 2026.7.0, `docker-compose.yml` in repo; Pilot needs Eclipse 2025-12 with Java 21; API Services is Play + sbt + JDK 11 + PostgreSQL with Swagger docs | EPL-2.0 | SysML v2 ingestion would run as a sidecar service |
| [OpenMBEE](https://github.com/Open-MBEE) | 171 repos; `exec-cameo-mdk` ("Cameo plugin for MMS sync and DocGen"), `flexo-mms-sysmlv2`, `sysmlv2-testing` (W3C EARL + PROV-O ledger) | Apache-2.0 on several | Cameo bridge and a provenance-ledger model; many repos show identical Sep 2026 dates, possibly a bulk change |
| [Gaphor](https://github.com/gaphor/gaphor) | 3.3.2; ~2.3k stars; usable as a library | Apache-2.0 | SysML v1 vs v2 support not stated |
| Dormant | [Capra](https://projects.eclipse.org/projects/modeling.capra) (last release 2021), [ProR / RMF](https://projects.eclipse.org/projects/modeling.rmf) (2016), [OSRMT](https://sourceforge.net/projects/osrmt) (2019), [Tracey](https://www.npmjs.com/package/tracey-cli) (2020), pyreqif (2021), the SysML v2 Python client (2021) | Mixed | Reading material for trace-matrix and ReqIF-GUI UX, not dependencies |

RTEMS evaluated eight requirements tools, required open source, plain-text storage, git and Sphinx output, rejected tools built on databases or complex Eclipse XML, and wrote a custom Doorstop-inspired Python tool; its complaints about Doorstop were rigid policies, links without custom attributes, alphabetical link order and no type-based verification rules ([RTEMS requirements tooling](https://docs.rtems.org/docs/6.1/eng/req/tooling.html)). Its checklist is a useful requirements list for any requirements-as-code design (I).

#### Commercial and research tools as UX references

| Tool | Pattern worth borrowing | Source |
|---|---|---|
| Jama Connect | Suspect links: administrator-chosen field changes raise a red indicator, a "Causing Suspect" relation, a project-wide list and bulk clearing; Advisor scores text against INCOSE and/or EARS rules in bulk | [suspect tracking](https://www.jamasoftware.com/?p=58660); [Advisor](https://www.jamasoftware.com/blog/2025/03/20/utilize-artificial-intelligence-and-natural-language-processing-to-produce-high-quality-requirements-with-jama-connect-advisor/) |
| Altium 365 Requirements Portal | AI-proposed edits shown as an apply-or-discard change set, colour-coded new (green), changed (purple), suggested removal (red); thumbs up/down feedback; admin can disable external AI providers | [Altium docs](https://www.altium.com/documentation/altium-365/requirements-portal/valiassistant/quality-assessment?version=18) |
| Innoslate | Eight quality attributes, six automatic (maximum automatic score 75% on one page, 78% on another); human can override an attribute and the score recalculates; choose-your-own LLM | [help](https://help.specinnovations.com/quality-check-requirements); [AI page](https://specinnovations.com/innoslate/artificial-intelligence-in-mbse) |
| IBM Engineering Requirements Quality Assistant | Score, issues, suggestions, apply, recheck loop; **cloud-hosted** (German data centres), no fully on-premises option described | [architecture](https://www.ibm.com/docs/SS3UPN/com.ibm.help.rm.assist.doc/topics/c_rqa_architecture.html) |
| Visure ViVIA | The only vendor mention of a "Human-in-the-Loop Review Session Workflow" around AI scoring | [ViVIA](https://visuresolutions.com/tool-suite/vivia) |
| Polarion | "Intelligent requirement mapping" matches new requirements to existing ones to reduce duplication; claims up to 70% effort reduction with no method stated | [Siemens blog](https://blogs.sw.siemens.com/polarion/enhancing-efficiency-in-polarion-with-ai-driven-requirements-management/) |
| QVscribe (QRA) | Lexical and semantic similarity as two named signals; analysis runs entirely on the workstation | [FAQs](https://qracorp.com/faqs/); [paper](https://ceur-ws.org/Vol-2584/NLP4RE-paper3.pdf) |
| Smella (requirements smells) | Reviewers accept, reject and blacklist findings; per-smell precision and recall (about 59% and 82% overall, wide spread by smell) | [Femmer et al.](https://arxiv.org/abs/1611.08847) |
| OpenRefine "Cluster and edit" | Methods ordered strictest to most lenient; per-cluster approval (pick an existing value, type a new one, or skip); "Merge selected and re-cluster" | [manual](https://openrefine.org/docs/manual/cellediting) |
| Codebeamer | Immutable baselines as snapshots, not copies | [baselines](https://support.ptc.com/help/codebeamer/r3.1/en/codebeamer/user_guide/31705.html) |

Open-source quality and similarity tools are small. The OpenReq quality service (EPL-2.0, Dockerised, updated July 2026) checks wording with Lexical, RegularExpressions and CompoundNouns algorithms, and the OpenReq similarity recommender (EPL-2.0, last updated July 2023) computes pairwise similarity of every requirement against all others ([quality service](https://github.com/OpenReqEU/prs-improving-requirements-quality); [recommender](https://github.com/OpenReqEU/similar-related-requirements-recommender)); `aac-req-qa` (MIT, 2024) asks an LLM to rate "shall" statements ([PyPI](https://pypi.org/project/aac-req-qa/)). No maintained open-source duplicate-detection product was found and no repo publishes a precision/recall benchmark for requirement duplicates. "Requirements Scout" from Qualicen could not be verified at all. Cloud-only assistants (IBM RQA; Modern Requirements Copilot4DevOps, which uses the OpenAI API ([press release](https://www.modernrequirements.com/press-releases/revolutionary-generative-ai-requirements-solution-launched-for-microsoft-azure-devops/))) fail a self-hosted constraint; only QVscribe, Prodigy and Innoslate's selectable LLM document local or air-gapped operation.

#### What the gap analysis says to build (I)

| Differentiator, in priority order | Why nothing existing covers it |
|---|---|
| Cross-project comparison and consolidation: open several large projects, normalise to one model with stable IDs, find equal, variant and conflicting requirements across them | Surveyed tools manage one project |
| A transparent strictness ladder with live per-method metrics, AI scored on the same ledger | Vendors publish no reviewer-visible metrics; OpenRefine supplies the ordering idea, Smella the per-rule precision idea |
| Everything is a draft with provenance and automatic staleness | Combines Doorstop fingerprints with Jama-style suspect UX |
| Lens-based review with separate approvals (SE, PE, UX, new user) | No surveyed tool offers role lenses; Gerrit labels are the closest analogue |
| Offline-first optional AI behind a provider abstraction, with disclosure when text leaves the machine | Cloud-only assistants cannot be used in self-hosted settings |
| Hand-off of the reviewed-merge ledger to document authoring (SDoc, Doorstop YAML, ReqIF, Sphinx-Needs) with traceability from each generated paragraph | Existing tools publish documents but do not ingest a reviewed-merge ledger |
| Scale without a hard database requirement | RTEMS rejected database-bound tools |

The researchers caution that competitors released after the cited pages, or niche 2026 start-ups, may already cover parts of this gap.

#### Opening MSOSA and "systems v2" projects: ReqIF first, XMI second, API only with access

The notes **do not identify what "systems v2" is**; if it is a SysML v2 model the ingest path is textual `.sysml`, KPAR or the REST API, and if it is an internal project name its format is unknown (I). For "MSoSa", Dassault's 2021x documentation describes Magic Systems of Systems Architect (MSOSA) as built on the MagicDraw platform and bundling the SysML, UPDM 2, UAF and Cameo Requirements Modeler plugins ([docs.nomagic.com 2021x](https://docs.nomagic.com/x/y2vfAw)), and the current documentation set pairs each current brand with a legacy name, "Magic Systems of Systems Architect / Cameo Enterprise Architecture" being one ([docs.nomagic.com latest](https://docs.nomagic.com/MT/latest/magic-systems-of-systems-architect---cameo-enterprise-architecture/sysml-v1-validation-303998303.html)). The exact spelling "MSoSA" is not an official acronym, so the identification is **probable, not confirmed**; the standards notes also could not verify "MSoSA" as an architecture framework and suspect a vendor tool name. SysML v2 arrives in the 2026 releases: a reseller blog says Cameo Systems Modeler Enterprise Edition supports it while the Architect Edition and MagicDraw with the SysML plugin do not, and does not say whether v1 projects convert ([GoEngineer](https://www.goengineer.com/en-us/blog/advantages-of-sysml-v2-now-available-in-no-magic-cameo-and-catia-magic-2026)).

| Rank (I) | Route | What the notes verified | Status |
|---|---|---|---|
| 1 | **ReqIF** from the Cameo Requirements Modeler plugin, read with `reqif` | The plugin imports and exports ReqIF for DOORS 9.4-9.6, DOORS Next, PTC Integrity, Polarion REQUIREMENTS, Siemens Teamcenter and Dassault Reqtify ([2024x docs](https://docs.nomagic.com/x/wy4mC)) | Documented and vendor-supported; round-trip untested on the owner's files |
| 2 | SysML v2 text, KPAR or API | Release repo ships spec PDFs, example models and KPAR/XMI libraries; API Services exposes a REST API with Swagger docs | Relevant only if the project is SysML v2 |
| 3 | **`.mdzip` / `.mdxml` XMI parsing** | Before 17.0.1 `.mdzip` was compressed XMI; from 17.0.1 a project is a zip of XMI 2.4, text and binary resources, with entries such as `com.nomagic.magicdraw.uml_model.model`; Sparx Enterprise Architect imports MDZIP from 17.0.1+ ([MagicDraw file format](https://docs.nomagic.com/x/RRwmC); [Sparx help](https://www.sparxsystems.com/enterprise_architect_user_guide/14.0/model_publishing/import_a_magicdraw_mdzip_file.html)) | Doable but **documents no supported reader API and no format stability**; 2026x file-format docs were not retrieved |
| 4 | Teamwork Cloud REST / Java Client API | A feature table lists REST API for Teamwork Cloud only; it mentions a Java client, a CLI and OSLC but **no OpenAPI or Swagger**, and the page was last updated 8 Apr 2020 ([TWC docs](https://docs.nomagic.com/x/T35UAw)); a third-party Python interface `atwc` exists ([PyPI](https://pypi.org/project/atwc/)) | Verify the endpoint contract with whoever grants access; "OpenAPI/Teamwork Cloud" is **unverified** |
| 5 | OpenMBEE bridge | `exec-cameo-mdk` syncs Cameo to MMS; `flexo-mms-sysmlv2` exposes a SysML v2 API on Flexo ([OpenMBEE](https://github.com/Open-MBEE)) | Optional |

Do not promise diagram import: diagram symbols are binary resources referenced by ID, and requirement and model-element text is the realistic target (I). A 3DSwym community post reports a CATIA Magic SysML v2 MCP server that is "TWC REST API based" ([post](https://3dswym.3dexperience.3ds.com/post/catia-mbse-cyber-systems/jama-mcp-catia-magic-sysml-v2-mcp_1DTXnzN9Rlms0us42ZwSZA)), evidence that a TWC route exists in practice. Magic/Cameo licensing constraints on third-party reading of project files were not researched.

### Datasets to test on: public sets are smoke tests, not gold

| Dataset | What it holds | Licence and size | Link |
|---|---|---|---|
| PURE | 79 public requirements documents, 34,268 sentences; the most reused dataset in a 2026 mapping study | CC BY 4.0; `requirements.zip` 33.6 MB | [Zenodo 1414117](https://zenodo.org/records/1414117) |
| PROMISE NFR ("nfr") | Functional vs 11 non-functional types | CC BY 4.0; 224.3 kB; sources count it as 625 or 969 requirements, which probably reflects versions (I) | [Zenodo 268542](https://zenodo.org/records/268542) |
| NoRBERT supplement | Relabelled PROMISE data, code, pretrained models | **GPL-3.0-or-later**; 3.6 GB of models | [Zenodo 3837375](https://zenodo.org/records/3837375) |
| Dalpiaz user stories | 22 datasets of at least 50 requirements each | Licence blank on the page | [Mendeley Data](https://data.mendeley.com/datasets/7zbk8zsd8y/1) |
| Crowd annotation of online feedback; multilingual crowd RE package | Annotation results; 859.9 MB package | CC BY 4.0 | [3626185](https://zenodo.org/records/3626185); [11424209](https://zenodo.org/doi/10.5281/zenodo.11424209) |
| Conflict sets (UAV, WorldVista, OpenCoss, PURE-derived, IBM-UAV) and the Fazelnia set | Known plus synthetic conflicts; Fazelnia adds defect classes | Availability of labelled pair files **not verified** | [S3CDA](https://arxiv.org/abs/2206.13690); [Fazelnia](https://arxiv.org/abs/2405.05135) |
| User-story redundancy sets | 137 plus 83 stories, 12,719 pairs | See paper | [Hofmann et al.](https://www.uni-marburg.de/de/fb12/arbeitsgruppen/swt/publikationen/dateien/2025/hofmannetal.pdf) |
| Meta-catalogue of 62 RE datasets | Web catalogue; only 11 of 62 (17.7%) reused as published; **57.4% state no licence**; no dedicated similarity/duplicate task | Catalogue not opened | [arXiv 2510.18787](https://arxiv.org/abs/2510.18787); catalogue at https://nlp4se.github.io/LLM4RE-Datasets/ |
| Model-based inputs | SysML v2 release example models (EPL-2.0); StrictDoc, Doorstop, TRLC and RTEMS requirement trees; Capella IFE sample (S, unopened) | EPL-2.0 or project licences | [SysML-v2-Release](https://github.com/Systems-Modeling/SysML-v2-Release); [Capella IFE](https://wiki.locationtech.org/Capella/Samples/IFE) |
| Space-sector documents | NASA CubeSat Design Specification, QB50, NTNU, OreSat (all S, search hits only) | Check before redistributing | [NASA PDF](https://www.nasa.gov/wp-content/uploads/2018/01/cubesatdesignspecificationrev14_12022-02-09.pdf) |

**Test pyramid (I).** Use PURE for realistic document-scale text similarity, with cross-document pairs as negatives and manufactured variants as positives; use PROMISE and the Dalpiaz sets for small labelled smoke tests; use SysML v2 release examples and a Capella export for model-based ingestion; use the git-native requirement trees for plain-text structures; and build a shareable test corpus from the owner's own ReqIF exports with the `reqif` anonymiser, since no large public ReqIF corpus was verified. **Labelled duplicates do not exist in these corpora**, so labels must be synthesised or reviewer-made; the minimal-pair adversarial set (negation, number, modal, unit, actor, condition perturbations of real sentences, human-verified) can be derived from PURE sentences. "Massive" is not covered by public data (PURE is about 34 MB zipped), so scale tests need synthetic generation of ReqIF or SysML v2 files. The researchers also note that the extreme class imbalance in public sets (PURE: 20 conflicts in 2,211 pairs; OpenCoss: 10 in 6,786) makes precision-at-k and PR curves more informative than accuracy or ROC AUC.

### Standards and governance: nothing defines consolidation, so model it as a controlled change to a baseline

This section is general information, not legal or certification advice. Standards text is paraphrased in the notes, several primary documents were paywalled or blocked, and the role-tagged checks near the end are inferences. The consolidating idea is that no standard the researchers could read defines a requirement-consolidation activity. The obligations come from requirements management and configuration management: bidirectional traceability, resolving duplicates repeated across levels, parent concurrence for self-derived requirements, and change-board approval with impact analysis for baselined items.

#### Requirement-writing anchors

| Anchor | What the notes verified | Use in the app |
|---|---|---|
| INCOSE Guide to Writing Requirements v4 (June 2023, INCOSE-TP-2010-006-04) | 42 rules R1-R42 in 14 categories; 15 characteristics (C1-C9 individual, C10-C15 sets) ([summary sheet](https://www.incose.org/docs/default-source/working-groups/requirements-wg/guidetowritingrequirements/incose_rwg_gtwr_v4_summary_sheet.pdf)); recommends "shall" for requirements and priority via attributes; discusses AI/NLP tools, noting many implement only a subset of rules, the team must still analyse and correct, and some tools upload requirements to vendor servers, which may limit use on government or military programs ([guide drafts](https://www.incose.org/docs/default-source/working-groups/requirements-wg/gtwr/incose_rwg_gtwr_v4_040423_final_drafts.pdf)) | Declare one rule baseline per project and record it in each AI result. Rules touching this app: R6 Common Units, R7 Vague Terms, R16 Use of "Not", R19 Combinators, R26 Absolutes, R29 Classification, R30 **Unique Expression**, R33 Range of Values, R34 Measurable Performance, R41-R42 Related Needs / Structured Sets |
| ISO/IEC/IEEE 29148:2018 | Nine individual characteristics plus set characteristics; **Edition 3 is in DIS ballot from 2026-09-14 for 12 weeks** ([ISO project page](https://www.iso.org/standard/94091.html)); table of contents seen in an [ANSI preview](https://webstore.ansi.org/preview-pages/BSI/preview_30357521.pdf) | Cite characteristics by name, not clause number, so references survive renumbering (I) |
| EARS | Five basic patterns (ubiquitous, event-driven WHEN, state-driven WHILE, optional WHERE, unwanted behaviour IF-THEN); the author's page adds "complex" as a sixth ([Mavin](https://alistairmavin.com/ears/); [Wikipedia](https://en.wikipedia.org/wiki/Easy_Approach_to_Requirements_Syntax)) | EARS pattern as a similarity feature: same response under different triggers or states is usually distinct, not duplicate (I) |
| NASA SEH Appendix C and NPR 7123.1D | "Shall" as requirement, one thought per requirement, unverifiable words, tolerances ([Appendix C](https://www.nasa.gov/seh/appendix-c-how-to-write-a-good-requirement)); unique, quantitative, measurable shall statements traceable to higher level ([NPR 7123.1D](https://explorers.larc.nasa.gov/APSMEX25/SMEX/pdf_files/NASA02_NPR_7123_1D.pdf)) | Lint rules; the notes could not read Appendix C's checklist text in full |

Two requirements that differ only by an ambiguity word ("fast" versus "within 200 ms") are not duplicates: the weak-word hit lowers a quality score but must not trigger a merge. Conformance to a "shall" convention is a mechanical check, whereas Necessary, Feasible and Correct cannot be settled from text and should be human-only fields (I); Innoslate shows the same ceiling, with 100% reachable only after human verification ([Quality Check help](https://help.specinnovations.com/4.10-quality-check)). No authoritative weak-word list from a standards body was found, only vendor lists.

#### Consolidation as controlled change

NASA's handbook says each requirement traces to a parent in a baselined document or is marked self-derived with higher-level concurrence, that trace should be independently checked so children cover parents, that requirements go under formal configuration control after the System Requirements Review with a board assessing cost, schedule, architecture, interface and related-requirement impact, and that duplicates repeated across levels should be resolved ([NASA SEH 6.2](https://www.nasa.gov/seh/6-2-requirements-management)). NASA's software requirement SWE-053 asks that records show what changed since the last baseline, who changed it, when and why, and that rejected changes are communicated ([SWE-053](https://swehb.nasa.gov/spaces/SWEHBVB/pages/32604509/SWE-053+-+Manage+Requirements+Changes)). DoDI 5000.88 asks for an audit trail of design decisions and a configuration-controlled digital baseline as the authoritative source of truth ([DoDI 5000.88](https://www.esd.whs.mil/Portals/54/Documents/DD/issuances/dodi/500088p.pdf)). The inference the researchers draw: a consolidation is a proposed change set with impact analysis over trace links, routed to the owning change authority, applied only after approval, and leaving an audit trail; pre-baseline items can be revised under normal edit control while post-baseline items need a change-request record (I). Self-derived flags and parent concurrence records must survive a merge. Conflict detection should be offered as an advisory finding with human adjudication because NASA and SEBoK say nothing about conflicts beyond "consistency".

#### Relationship vocabulary and a duplicate-handling guide

SysML v1 tooling documents Copy, Derive Reqt, Refine, Satisfy, Trace and Verify requirement relationships plus nesting ([PTC Modeler](https://support.ptc.com/help/modeler/r10.2/en/Modeler/sysml/Overview_of_working_with_requirements.html)); Copy ties a slave requirement's read-only text to a master ([Copy relationship](https://support.ptc.com/help/modeler/r10.1/en/Modeler/sysml/SysML_Copy.html)); OSLC adds `elaboratedBy`-style links ([OSLC RM 2.1](https://docs.oasis-open-projects.org/oslc-op/rm/v2.1/os/requirements-management-spec.html)); Jama's suspect link is a state flag, not a link type ([Jama](https://help.jamasoftware.com/en/manage-content/coverage-and-traceability/relationships/clear-suspect-links.html)). **Duplicate-of, near-duplicate-of, conflicts-with and supersedes are not standardised anywhere the researchers could read**, so they are app-level definitions (I).

| Decision | When (I) | What to do |
|---|---|---|
| Supersede | One statement is canonical, the others become inactive | Keep the old ID, mark superseded, forward trace links, record who, when and why |
| Merge | Same obligation, same level, same owner | Choose or create the surviving ID, union traces, allocations and verification links, keep rationale and sources of all, record as one change |
| Retain with cross-reference | Similar text at different levels, owners, allocations or verification contexts | Link as related; use a master/copy pattern where the text must stay identical |
| Never auto-merge | Across owners, across baselines, or where verification methods or allocations differ | Escalate to the owner or change board |

Fields to preserve in any consolidation (I, each anchored in NASA, SEBoK or DoD sources): all requirement IDs with an old-to-new forwarding map; parent and child traces in both directions; rationale, source, owner, status and criticality or priority; verification method and success criteria with links to test procedures; allocation; baseline and version at time of change; self-derived flag and concurrence; change record; and TBD/TBR markers ([SEBoK System Requirements](https://sebokwiki.org/wiki/System_Requirements)). Configuration-management skeletons come from ISO 10007:2017 (planning, identification, change control, status accounting, audit) and EIA-649 ([ISO 10007](https://blog.ansi.org/ansi/configuration-management-iso-10007-2017/); [EIA-649](https://en.wikipedia.org/wiki/EIA-649_National_Consensus_Standard_for_Configuration_Management)).

#### Verification linkage

SEBoK defines inspection, analysis, demonstration and test, and a verification matrix tying each action to requirement, method, expected and obtained result ([SEBoK System Verification](https://sebokwiki.org/wiki/System_Verification)); DO-178C requires bidirectional traces from requirements to code, test cases and results ([DO-178C](https://en.wikipedia.org/wiki/DO-178C)). Merge rules the researchers propose (I): the survivor keeps the strictest verification method and the union of success criteria, differing methods (for example Test versus Analysis) block auto-merge, every linked test procedure or matrix row gets a suspect flag after any merge or supersede, and the UI shows which test procedures a change touches before Accept. A verifiability check means a stated method, measurable success criteria and an identified verification artifact or planned slot; absence should block "ready for baseline". No source specifies how verification artifacts must be updated on a merge.

#### Exchange and MBSE standards

| Standard | Status in the notes | Implication (I) |
|---|---|---|
| ReqIF 1.2 | July 2016; file exchange between organisations that cannot share a repository ([OMG](https://www.omg.org/spec/ReqIF)) | Round-trip first; record format version in export metadata |
| OSLC RM 2.1 | OASIS Standard, 21 June 2021 ([OASIS](https://docs.oasis-open-projects.org/oslc-op/rm/v2.1/os/requirements-management-spec.html)) | Linked-data/REST integration; a later path |
| SysML v2.0, KerML 1.0, Systems Modeling API 1.0 | Final adoption dated 30 June 2025 on GitHub, 21 July 2025 in the OMG release, specification publication September 2025 per Wikipedia; editorial update March 2026 for ISO; conformance suite still in development ([GitHub](https://github.com/systems-modeling/sysml-v2-release); [OMG](https://www.omg.org/news/releases/pr2025/07-21-25.htm); [Wikipedia](https://en.wikipedia.org/wiki/Systems_modeling_language)) | Do not make v2 a hard dependency; plan the data model to map to the API later |
| SysML v1 | ISO/IEC 19514:2017; v1.6 (December 2019) the latest per Wikipedia | Installed base |
| UAF 1.3 | April 2026; enables DoDAF and NAF ([OMG](https://www.omg.org/spec/UAF)) | Not needed for requirement text |
| ISO/IEC/IEEE 21840:2019 | Guidelines for 15288 in a system-of-systems context ([iTeh](https://iteh.es/catalog/standards/iso/5686ea51-d015-4efd-867d-1cf88b5ba638/iso-iec-ieee-21840-2019)) | Cross-owner merges in SoS are the highest-risk case and need explicit owner approval |

#### AI governance, assurance and sensitive-data handling (general information)

No single standard governs an LLM that drafts requirement suggestions; frameworks converge on provenance, risk-based human oversight, pre-deployment testing and third-party control. NIST AI 600-1 lists 12 generative-AI risks, including confabulation, human-AI configuration (over-reliance), information security and value-chain integration, and suggests actions the app can mirror: trace origin and edits of content, tamper-evident history, minimum performance thresholds as go/no-go criteria, independent evaluation, structured human feedback and third-party inventories ([NIST AI 600-1](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf); [AI RMF page](https://www.nist.gov/itl/ai-risk-management-framework)). ISO/IEC 42001:2023 is a published AI management-system standard ([ISO](https://www.iso.org/standard/42001)). Aerospace AI guidance (EASA concept paper, ED-324/ARP6983) targets AI inside products, not AI used as a development aid, and ED-324's publication date conflicts between sources (June 2026 target in August 2025 slides, Q4 2026 in September 2026 EASA slides) ([EASA AI Days](https://www.easa.europa.eu/en/downloads/144162/en); [FAA tech-exchange deck](https://na.eventscloud.com/file_uploads/115fca49330a77ce92d7fe04e9874faf_Day1-Jahn-202508ED-324ARP6983presFAAAI-MLTechExchangeMeeting_8-5-25-Read-Only.pdf)). The FAA roadmap says companies remain responsible for compliance regardless of how artifacts are created and lists LLMs for requirements traceability in certification tools as a research priority ([FAA roadmap](https://www.faa.gov/media/82891)). DoD's 2020 AI ethical principles and 2022 RAI pathway sit beside a January 2026 strategy that redefines responsible AI, and which is operative is unclear ([CSIAC](https://csiac.dtic.mil/wp-content/uploads/2024/08/Webinar_CSIAC_The-DoDs-Approach-to-Responsible-AI-and-the-RAI-Toolkit_v3.pdf); [summary](https://www.insidegovernmentcontracts.com/2026/02/pentagon-releases-artificial-intelligence-strategy/)). The EU AI Act is likely low-relevance for an internal US defence tool, but its defence carve-out was not verified ([Gibson Dunn](https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/)).

On tool qualification, the researchers suggest (I) an explicit intended-use statement, "assistive, advisory; not a verification tool; no verification credit taken", because if the app's output were used as verification credit, DO-330 thinking applies, notably the criterion that a tool "could fail to detect an error" ([DO-330 intro](https://afuzion.com/?p=358)).

For sensitive requirement text, the notes offer only general, partly secondary information: 22 CFR 120.54 says sending unclassified technical data is not an export if protected by end-to-end encryption using FIPS 140-2 (or successor) validated modules and the decryption means are not given to third parties ([eCFR](https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-120/subpart-C/section-120.54)); a vendor explainer says DFARS 252.204-7012 requires NIST SP 800-171 controls, FedRAMP Moderate cloud providers and incident reporting for covered defence information ([PreVeil](https://preveil.com/blog/what-is-dfars-7012/)); and a promotional vendor blog argues that exposure can arise at each inference stage (hosting, gateways, vector databases, logging) ([Kiteworks](https://www.kiteworks.com/regulatory-compliance/itar-ai-agents-compliance-gap/)). The notes found no DoD policy specific to generative AI on CUI or export-controlled requirement text, and EAR, NIST SP 800-171 Rev 3, CMMC and DoDI 5200.48 were not verified. The design principle consistent with these sources (I): default to self-hosted or local models or an accredited enclave for real program data, send only sanitised or synthetic text to external APIs and only after the responsible compliance office has made the export-control and CUI determination, and log every outbound call.

One licensing point matters for the agent knowledge base: ISO's standard pages state that ISO content may not be used to prompt AI tools to generate responses, except content on its Open Data page ([ISO 9241-210 page](https://www.iso.org/standard/77520.html)). The notes did not check other publishers' terms, and most core documents are paid or restricted (the INCOSE Guide beyond its summary sheet, ISO/IEC/IEEE 29148, SAE ARP4754B), whereas the NASA handbook and NPR 7123.1D, NIST AI 600-1, WCAG, ReqIF, OSLC RM and DoDI 5000.88 are public. The body-of-knowledge repo should therefore hold paraphrased rule identifiers and names, which is also what the notes themselves do (I).

#### Human-factors standards for the review UI

ISO 9241-210:2019 sets the human-centred-design process; WCAG 2.2 (W3C Recommendation, also ISO/IEC 40500:2025) adds criteria directly relevant to a review queue: Focus Not Obscured (2.4.11), Dragging Movements (2.5.7), Target Size Minimum (2.5.8), Consistent Help (3.2.6) and Redundant Entry (3.3.7) ([WCAG 2.2](https://www.w3.org/TR/WCAG22/); [W3C news](https://www.w3.org/WAI/news/2025-10-21/wcag22-iso)). NN/g's ten heuristics are the common review checklist ([NN/g](https://www.nngroup.com/articles/ten-usability-heuristics/)). Section 508 and DoD accessibility mandates were not researched.

#### Reviewer-lens checklists (proposals)

The notes convert the sources into four lenses; each bullet can become a pass, fail or needs-human check (I; no external source provides an official AI-assisted requirement-review checklist).

| Lens | Checks |
|---|---|
| Systems engineer (SE) | Rule baseline stated and each finding cites rule ID plus text span; singular, solution-free, "shall", measurable; EARS pattern classified (different trigger or state means not duplicate); candidate duplicates compared on subject, response, condition, value and tolerance, level, owner, allocation, verification method, where any difference blocks auto-merge; traces and allocation preserved with no orphans; strictest verification method kept and linked tests flagged suspect; conflicts raised as conflicts; set-level consistency and no lost coverage |
| Process engineer (PE) | Baseline status checked before any change and approving authority matches owner; AI-assist record per suggestion (model and version, location, prompt template version, inputs with versions, output, reviewer, decision, justification); AI cannot write approved fields; intended-use statement with no verification credit; data classification before any external call; acceptance and override monitoring, seeded-error spot checks and model-change regression runs; generated documents carry baseline ID and show superseded IDs |
| UI/UX engineer (UX) | Status badges use text and shape, not colour alone; undo, diff and confirm for consequential actions, batch limited to low-risk categories; WCAG 2.2 AA spot checks (keyboard, focus not obscured, target size, no drag-only action, no redundant entry, consistent help); grouping by cluster, risk sort, progress and resumable sessions; blind-first or justification-required modes for sampled items; provenance visible in context |
| New user (NU) | Can say what an "AI draft" is and that it is not approved; rule IDs shown with plain-language names (R7 as "vague word"); terms (duplicate, near-duplicate, supersede, merge, baseline, suspect link) defined in-app; consequence of Accept shown before it happens; Reject and Skip as easy as Accept with no default nudge; clear where data goes (local or external) |

### Agent skills, roles and MCP: put hard guarantees in code, judgement in isolated reviewer agents

Agent Skills are now an open standard: a directory with a required `SKILL.md` (frontmatter `name` of 1-64 lowercase characters and hyphens matching the directory, and a `description` of up to 1,024 characters saying what it does and when to use it), optional `scripts/`, `references/` and `assets/`, and three-tier progressive disclosure that loads only about 100 tokens of metadata at startup ([Agent Skills specification](https://agentskills.io/specification); [anthropics/skills](https://github.com/anthropics/skills)). Anthropic's guidance is to start with evaluations, keep SKILL.md under 500 lines, match instruction rigidity to fragility, and use "validate, fix, repeat" loops and a plan-validate-execute step where the agent writes a `changes.json`, validates it and only then applies it ([engineering post](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills); [best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)). The decisive design fact is that skills are model-invoked and advisory, whereas hooks and scripts can block actions, so anything that must never fail (units, numbers, modals, trace preservation) belongs in deterministic validators ([Destefanis, via alphaxiv summary](https://www.alphaxiv.org/abs/2607.25032)). Keep skills within the open-spec subset (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools`) because surfaces outside Claude Code hard-error on other keys ([Claude Code skills](https://code.claude.com/docs/en/skills)); the "Skills over MCP" extension is Final, so skills can also be served from the app's own MCP server ([charter](https://modelcontextprotocol.io/community/working-groups/skills-over-mcp)).

Reviewer personas should be subagents with their own system prompt, read-only tools and scoped MCP servers, each with a fresh context ([Claude Code subagents](https://code.claude.com/docs/en/sub-agents)). Generator and verifier must be separated: intrinsic self-correction without external feedback generally reduced reasoning accuracy ([Huang et al.](https://arxiv.org/pdf/2310.01798)), LLM judges favour their own generations ([Panickssery et al.](https://arxiv.org/abs/2404.13076)), and a panel of diverse smaller judges beat a single large judge while costing over 7x less ([Verga et al.](https://arxiv.org/abs/2404.18796)). The evidence on one judge versus several conflicts: Anthropic found a single rubric judge more consistent than multiple judges ([research-system post](https://www.anthropic.com/engineering/multi-agent-research-system)). For consensus, debate is not a reliable booster: it can reduce accuracy and agents flip most when no peer agrees with them ([Wynn et al.](https://arxiv.org/abs/2509.05396)); sycophancy drives "disagreement collapse" and centralised judge designs proved more resilient ([Yao et al.](https://arxiv.org/abs/2509.23055)), though Du et al. reported gains from debate ([ICML 2024](https://proceedings.mlr.press/v235/du24e.html)). Anthropic's own multi-agent system used about **15x** the tokens of chat ([post](https://www.anthropic.com/engineering/multi-agent-research-system)).

**Recommended consensus protocol (I).** Generate once; run deterministic guards; run the verifier and three or four personas in parallel and independently, without seeing each other's outputs; let a separate adjudicator tally verdicts, record dissent verbatim and route any non-unanimous or `unknown` result to a human instead of seeking agreement; allow at most one revision loop, then re-run guards and the independent verifier; and stop on guards passing, on 2-3 iterations, or when a revision does not change the objection set. Use different model families via LiteLLM for verifier and personas, reserve the full panel for high-impact proposals that pass cheap gates, and measure disagreement collapse in the eval harness with seeded cases where a lone reviewer is right.

**Proposed skill and role list (I; every row is a proposal, not an existing artifact).** D = deterministic script or validator, L = LLM skill, S = subagent role.

| # | Name | Type | One-line purpose |
|---|---|---|---|
| 1 | `guarding-units-and-numbers` | D | Extract numbers, units, comparators, modals and tolerances from source and proposal and hard-fail any proposal whose set differs without a visible justification |
| 2 | `checking-trace-preservation` | D | Verify every source ID has a disposition (kept, merged, superseded, rejected) and none is orphaned or silently dropped |
| 3 | `validating-proposal-schema` | D | JSON-schema validate each proposal (relation, evidence spans, provenance) before it enters the review queue |
| 4 | `generating-similarity-candidates` | D | Cheap recall stage: embeddings plus BM25/TF-IDF candidate pairs with per-project tuned thresholds |
| 5 | `triaging-requirement-similarity` | L | Classify each candidate pair into the fixed taxonomy with cited evidence spans and calibrated confidence |
| 6 | `detecting-requirement-conflicts` | L | Find contradictory values, modals, scopes or conditions and output the exact conflicting clauses |
| 7 | `proposing-consolidation` | L | Draft a merged requirement with clause-level provenance and a stated disposition for every source clause |
| 8 | `rewriting-to-ears` | L plus guard 1 | Constrained rewrite into EARS or the project template preserving every constraint, always shown as a diff |
| 9 | `checking-requirement-quality` | L | Rubric check per quality characteristic with evidence, advisory only |
| 10 | `explaining-diffs` | L | Plain-language summary of what changed and what could be lost, feeding the diff UI |
| 11 | `verifying-proposals-independently` | S | Fresh-context verifier from a different model family receiving only sources, proposal and rubric, returning a structured verdict that includes `unknown` |
| 12 | `reviewing-as-systems-engineer` | S | Persona review of verifiability, allocation, interface and traceability implications |
| 13 | `reviewing-as-process-engineer` | S | Persona review of procedure, test and V&V consequences and release implications |
| 14 | `reviewing-as-ux-engineer` | S | Persona review of operator-facing wording and human-factors implications |
| 15 | `reviewing-as-new-user` | S | Jargon-naive persona that flags undefined acronyms and unclear wording and seeds glossary entries |
| 16 | `adjudicating-reviewer-panel` | L | Aggregate persona and verifier verdicts, preserve dissent, compute disagreement, decide "needs human" versus "auto-low-risk" |
| 17 | `authoring-documents-from-requirements` | L | Compose document sections from approved requirements only, every sentence traceable to requirement IDs |
| 18 | `recording-decisions-and-lessons` | L | Turn reviewer rulings and reversals into decision records and lesson drafts, submitted as merge requests, never direct writes |
| 19 | `explaining-jargon` | L | Glossary-grounded explanations for tooltips and first-run help |
| 20 | `running-skill-evals` | D plus L | Run the golden set against any skill, prompt or model change and block merge on regression |

Persona guidance (I): give personas distinct rubrics and evidence requirements rather than only different names; at least one persona should be told to look for what is lost, because decentralised debates were best with mixed "peacemaker and troublemaker" personas and worst when all debaters were sycophantic ([Yao et al.](https://arxiv.org/abs/2509.23055)); make the new-user persona deliberately jargon-naive and deny it the glossary. **No reusable public persona prompts for these four roles exist**; they must be authored and evaluated in-house. Role decomposition precedents are MARE (five RE role agents, evaluated only on OpenAI models with a small three-student human evaluation; [MARE](https://arxiv.org/abs/2405.03256)) and Elicitron's simulated users ([Elicitron](https://arxiv.org/abs/2404.16045)), and an open evaluator model that grades against a user-supplied rubric exists in Prometheus ([Prometheus](https://arxiv.org/abs/2310.08491)).

**MCP surface (I, built on verified spec facts).** The current specification revision is 2026-07-28: stateless, self-contained requests with per-request capability negotiation, sessions and the `initialize` handshake removed, and Tasks, Skills and Apps as opt-in extensions ([spec](https://modelcontextprotocol.io/specification/latest); [changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)). The tools spec says there should always be a human in the loop able to deny tool invocations, treats tool annotations as untrusted unless from trusted servers, and describes an explicit handle pattern for stateful tools ([Tools spec](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)). The researchers' design: read-only tools exposed broadly (`search_requirements`, `get_requirement`, `get_relations`, `list_clusters`, `get_glossary_term`, `get_review_history`, each with an `outputSchema`); propose-only tools that return an opaque `proposal_id` (`create_draft_proposal`, `add_evidence_to_proposal`, `run_guards`, `submit_for_review`), with drafts living in a separate table; and **no apply or approve tool exposed to agents at all**, since approval happens only in the authenticated human UI. Keep servers small and role-scoped, enforce read/write separation by credentials and database roles rather than annotation hints, carry `proposal_id` and review round explicitly, and use the Tasks extension for whole-corpus runs. LiteLLM's proxy can act as an MCP gateway with per-key access control and a `require_approval` setting ([LiteLLM MCP docs](https://docs.litellm.ai/docs/mcp)).

Existing servers worth studying: easeRequirements for Jira, which asks for confirmation with an affected-items summary on destructive operations ([announcement](https://go.easesolutions.com/ai-requirements-management-with-ease-req-mcp-server)); Atlassian's Rovo MCP server ([docs](https://developer.atlassian.com/cloud/rovo-mcp/)); an academic SysML v2 MCP server (C#.NET, open source, branch-based workflows, qualitative case studies only, with the authors noting LLM reasoning degrades with many tools) ([Design Society paper](https://www.cambridge.org/core/product/16D1E8B53ED56E1DF43C41AF38757D40/core-reader)); and a Jama MCP plus CATIA Magic SysML v2 MCP demonstration ([3DSwym post](https://3dswym.3dexperience.3ds.com/post/catia-mbse-cyber-systems/jama-mcp-catia-magic-sysml-v2-mcp_1DTXnzN9Rlms0us42ZwSZA)). **No DOORS MCP server and no server with a propose-then-approve staging model was verified.**

**Proposed body-of-knowledge repo layout (I; the researchers' synthesis, not a community standard).** Built from verified conventions: AGENTS.md for repo-level agent instructions ([agents.md](https://agents.md/)), MADR decision records ([adr/madr](https://github.com/adr/madr)), Diataxis documentation types ([diataxis.fr](https://diataxis.fr/)), Agent Skills folders, and the MCP project's PR-based proposal workflow with a deprecation policy as a model of a governed living repo ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).

```
body-of-knowledge/
  AGENTS.md                  # how agents may read/write this repo; write = merge request only
  decisions/                 # MADR ADRs: 0001-...md (status, context, options, outcome, consequences)
  lessons/                   # dated lessons-learned linking evidence (proposal IDs, eval runs)
  playbooks/                 # Diataxis how-tos for reviewers and for agent operators
  glossary/terms.yaml        # single source for tooltips and new-user persona checks
  skills/<name>/SKILL.md     # (+ scripts/, references/) open-spec subset only
  agents/<role>.md           # subagent/persona definitions (system prompt, tools, model)
  evals/golden/*.jsonl       # versioned golden sets: labels, labeler IDs, adjudication notes
  evals/suites/              # Inspect AI / Promptfoo / DeepEval configs; CI gates
  CHANGELOG.md               # skill, prompt and model version history tied to eval results
```

Agents propose changes to this repo only as merge requests, CI runs the golden-set regression suite and `skills-ref validate` on every request, and a human owner approves. The loop closes when reviewer reversals and overrides in the app's audit log open a draft lesson and a candidate golden case, with promotion from candidate to golden requiring two human labels (I). Remember the repo should carry paraphrased standards content, not copied text (see Standards).

### Evaluation and metrics: human agreement bounds the score, so measure it first

Report two families side by side for every suggestion source (each lexical method, each embedding model, the fused model and the AI judge): pairwise precision, recall and PR curves on the candidate distribution, and cluster-level B-cubed with ARI and AMI as secondary summaries. Measure human agreement before anything else because it caps achievable agreement, then add workflow metrics. All of this is the researchers' recommended dashboard (I) built on verified metric definitions.

| View | Metric | Why |
|---|---|---|
| Per source (each lexical metric, each embedding model, fused model, AI judge) | PR curve and average precision; precision and recall at the operating threshold with Wilson 95% intervals; reliability curve and expected calibration error | Comparable across sources on the same gold pairs |
| Per relationship label | Per-class precision, recall, F1 and a confusion matrix | Shows VARIANT and SUBSUMES as the confusing classes |
| Cluster level | B-cubed P/R/F1, ARI, AMI, cluster count, singleton fraction, largest cluster, minimum intra-cluster probability | Detects chaining and giant clusters |
| Mechanical vs AI | Contingency table (both, mechanical-only, AI-only, neither), kappa between the two systems, complementarity of human-confirmed pairs found by each | Disagreement is where labelling effort is most valuable; kappa between systems is **not** accuracy, and both can share a blind spot such as unit-converted equivalents |
| Systems vs humans | Each system against adjudicated gold; human-human kappa or alpha as the ceiling | At the noise ceiling, further model gains are invisible |
| Workflow | Acceptance rate by source and confidence bin, rejection reasons, **edit distance of human edits to AI-proposed merged text** (token-level and slot-level), time to decision, coverage, reversal rate | Leading indicators of trust and hidden failure |
| Safety | Veto pass rate (number, unit, modal, negation preserved), citation validity (every cited ID and quote exists verbatim), hallucinated-merge rate in audited samples, canary catch rate | Shows AI suggestions are verifiable |

Acceptance rate is a biased quality metric: anchoring and automation bias raise it and fatigue lowers it, so compare it with acceptance of randomly planted known-false suggestions ("canaries") and with a blind-reviewed random sample. A rising acceptance rate with falling edit distance is ambiguous on its own. Show reviewers calibrated historical labels ("suggestions at this level were accepted X% of the time and confirmed correct Y% in audit") instead of raw model scores, and abstain ("needs human") when the verifier says `unknown` or the panel disagrees.

**Building the gold set (I; the plan targets 600-1,000 labelled pairs in roughly 2-3 reviewer-days, which is the researchers' estimate).**

| Step | Action |
|---|---|
| 1 | Pool candidates as in TREC: union of top-10 neighbours from each method per requirement, so every method's positives are represented |
| 2 | Stratify by fused-score bins (about 40 pairs per bin), add all pairs where methods disagree, 100 random pairs for prevalence, and the human-verified minimal-pair adversarial set |
| 3 | Double-label 25-30% with two reviewers, compute kappa or alpha per class, adjudicate, refine the written guideline (3-5 examples per label, including the comparator rule) and iterate once |
| 4 | Split group-aware (by document or connected component): develop 60%, calibration 20%, test 20%; freeze the test split |
| 5 | Estimate prevalence from the random slice and weight sampled pairs by inverse inclusion probability for unbiased precision and recall |
| 6 | Let an LLM pre-label for cheaper verification but keep at least 30% of items blind to measure anchoring; never use the LLM as sole ground truth |
| 7 | Version the gold set (immutable test split, append-only audit set, reason codes) and report bootstrap intervals resampled by group |

Because humans may not agree, expect the ceiling to be modest: only 1 of 16 alpha values exceeded 0.8 in a requirements-tagging study ([Dalpiaz et al.](https://webspace.science.uu.nl/~dalpi001/papers/dalp-dell-ayde-cevi-19-re.pdf)), and no agreement study for a four- or five-way requirement relationship taxonomy exists. Rare positives depress kappa and alpha, so also report raw and positive-specific agreement.

**Three regression suites (I, following Anthropic's eval advice).** Start from 20-50 simple tasks drawn from real failures; keep deterministic guard unit tests (synthetic mutations that swap a unit, drop a tolerance or flip shall/should), a capability set of hard pairs where a low pass rate is allowed, and a regression set that runs near 100% on every prompt, skill or model change in GitLab CI; run several trials and report pass^k next to pass@k; give judges an explicit "Unknown"; grade each rubric dimension with an isolated judge; and read transcripts ([Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)). A 0% pass rate usually signals a broken task. Release gates from the theory plan: the minimal-pair suite must yield zero auto-suggested merges for number, unit, modal or negation toggles; PR curves, clustering metrics and calibration by slice (with or without numbers, with or without negation, same-document or cross-document) on the frozen test split; a bake-off with ablations (lexical only, each embedding, plus cross-encoder, plus NLI, plus stacker, plus LLM judge); pilot workflow metrics; an audit-set drift check on every model or prompt change (pin model version and prompt hash); and pinned model hashes and licences.

**What published LLM-for-RE work says about trusting an AI judge.**

| Study | Finding |
|---|---|
| Systematic review of LLMs for RE: 74 primary studies, 2023-2024 ([arXiv 2509.11446](https://arxiv.org/abs/2509.11446)) | Mostly GPT, zero/few-shot, controlled settings, limited industrial use |
| Quality assessment against ISO 29148 characteristics, Llama 2 70B ([Lubos et al.](https://arxiv.org/abs/2408.10886)) | The LLM judged far fewer requirements as meeting each characteristic; precision for flaw detection low (0.1257 on one set), recall high; human-LLM Cohen's kappa **0.0486 rising to 0.2223** once humans saw the LLM output (another set 0.4028 to 0.7545), which the researchers read as strong anchoring |
| Quality assessment against INCOSE criteria, ten Claude and GPT models, NASA Astrobee requirements ([Shefa et al.](https://arxiv.org/html/2609.03230)) | Misses dominate (one top model: median false-negative rate about 0.67, precision about 0.48); "Necessary" missed in every run; "not yet trustworthy autonomous evaluators"; the abstract's 47% detection and the results' 0.33 true-positive rate looked inconsistent |
| LLM-as-judge for generated requirements ([Paiva et al.](https://link.springer.com/article/10.1007/s00766-026-00462-z)) | A Qwen QwQ-32B judge validated by five humans on 50 samples correlated significantly with aggregate human judgement; prompt style trades singularity against verifiability |
| SRS drafting ([Krishna et al.](https://arxiv.org/abs/2404.17842)) | One model **substantially changed a performance requirement's response-time threshold** during correction and mis-sectioned requirements |
| AI-vs-expert on 20 medical-equipment requirements ([arXiv 2604.15222](https://arxiv.org/abs/2604.15222)) | A roughly 40-point spread between models and internal inconsistencies; treat as a caution, not a benchmark |
| Conflict detection in Arabic, 27K pairs ([AraREQ](https://aclanthology.org/2026.lrec-1.553/)) | Few-shot prompting helps most on the minority conflict class |
| Traceability candidate filtering ([Fuchss et al.](https://fuchss.org/conferences/aire25/)) | IR candidate selection needs per-project tuning; small language models can shrink candidate spaces with little recall loss |

The notes found no public benchmark for requirement consolidation (merge, keep, split with constraint preservation), and no paper measuring "hallucinated merge", "dropped constraint" or "unit change" rates; the unit-change evidence is the single Krishna observation.

### Review UX: show evidence before verdicts, force engagement only where risk is high

The automation-bias literature is the reason the review UI is not a plain accept/reject list. A systematic review of 74 studies (from 13,821 retrieved) found the tendency to over-rely on automation rises with workload, task complexity and time pressure, and that mitigators include accountability and design choices such as where advice appears and offering information rather than direct recommendations ([Goddard et al., JAMIA 2012](https://academic.oup.com/jamia/article/19/1/121/732254)). In an experiment with 199 participants, cognitive forcing functions reduced overreliance more than explainable-AI approaches, but the designs that reduced it most were rated least favourably ([Buçinca et al.](https://arxiv.org/abs/2102.09692)). Complacency and automation bias occur in novices and experts alike and are not prevented by training or instructions ([Parasuraman and Manzey](https://trid.trb.org/View/1085175)). No usability evidence exists at thousands-of-suggestions scale, and graph-view efficacy for review is unstudied.

| Pattern (I unless stated) | Design | Source |
|---|---|---|
| Cluster-first triage | Group candidates into clusters ordered by method strictness so the safest merges are reviewed first and can be bulk-approved; per cluster choose an existing wording, type a new one, or mark not-a-duplicate; re-cluster after each merge; "not a duplicate, never suggest again" | [OpenRefine](https://openrefine.org/docs/manual/cellediting); [Smella](https://arxiv.org/abs/1611.08847) |
| Risk lanes | Lane A (guards pass, verifier and panel agree, high-acceptance bucket): Prodigy-style keyboard triage (accept, reject, skip, undo). Lane B (guard warnings, dissent, conflicts): evidence shown before Accept is enabled, typed rationale or per-clause confirmation | [Prodigy](https://future.prodi.gy/docs/api-web-app); cognitive forcing per Buçinca |
| Evidence before verdict | Source texts side by side with the proposal; for Lane B hide or collapse the AI recommendation; randomly hide recommendation and confidence for a sample to measure anchoring | Goddard; Lubos |
| Token-level diff with semantic highlighting | Distinct colours for numbers, units, comparators, modals and condition keywords; "constraint delta" chips driven by the deterministic guard, with a "nothing numeric changed" badge only when the guard proves it | Altium colour coding |
| "Why suggested" panel | One-line reason, evidence spans, skill and model version, guard results, verifier verdict, panel dissent; deeper detail one click away, two levels at most | [Carbon for AI](https://carbondesignsystem.com/guidelines/carbon-for-ai/); [NN/g progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/) |
| Provenance badges | Mechanical, AI (skill and model version), human-edited, human-approved; editing AI text flips the badge and offers revert-to-AI; store a model version per suggestion | Carbon; [Label Studio predictions](https://labelstud.io/guide/predictions) |
| Status lifecycle | suggested, in review, accepted/rejected/edited, approved (role sign-off), published, with draft and discarded states; undo is a new event, never a delete | [Argilla](https://docs.argilla.io/latest/reference/argilla/records/responses) response statuses |
| Role sign-off as labels | One label per lens (SE, PE, UX, NU) with separate comment, approve and block permissions; a block vote prevents publish; cross-owner merges need the owner's approval | [Gerrit labels](https://gerrit-review.googlesource.com/Documentation/config-labels.html) |
| Review-before-publish page | Summary list with a "Change" link per item and a specific action label ("Publish 14 consolidations") | [GOV.UK Check answers](https://design-system.service.gov.uk/patterns/check-answers/) |
| Batch as one change set | Batch-accept Lane A items as one auditable change set with co-author-style attribution to the model and the reviewer | [GitHub suggested changes](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/incorporating-feedback-in-your-pull-request) |
| Staleness | Fingerprint source requirements and mark a pending suggestion stale if any source changes; show an indicator column, "caused by" relation and bulk clear | Doorstop fingerprints; Jama suspect links |
| Onboarding | Walkthrough with empty states that carry learning cues and a direct path to the first task; a sample project so the queue is never empty; glossary tooltips from the maintained glossary | [Primer empty states](https://primer.style/product/ui-patterns/empty-states/); [NN/g empty states](https://www.nngroup.com/articles/empty-state-interface-design/) |

Design inferences added by the researchers (I): sort by risk and impact (trace-link count, baselined status), allow batch actions only for low-risk categories and never for cross-owner merges, offer "blind first" mode where the reviewer records an initial judgement before seeing the AI suggestion, seed known-wrong suggestions at a low rate to measure vigilance, and display each reviewer's accept rate. Use a mature open design system for AI labels and empty states rather than inventing conventions (Carbon and Primer were cited; their React package details were not verified). Persistent text badges, not colour alone, support the accessibility lens (see WCAG items under Standards).

### Downstream document authoring: render documents from the approved baseline, never from hand-typed copies

Requirement-driven, traceable generation means a document is rendered from the approved requirement baseline (IDs, text, links, status) rather than hand-typed. Sphinx-Needs does this natively with need objects, links, filters and traceability tables, and Sphinx renders HTML and PDF; StrictDoc does it with its own text format and an in-house `reqif` library, making it the self-contained alternative ([PyPI sphinx-needs](https://pypi.org/project/sphinx-needs/); [StrictDoc](https://pypi.org/project/strictdoc/)).

| Need | Default | Alternative | Flags |
|---|---|---|---|
| Traceable HTML and PDF | [Sphinx](https://pypi.org/project/sphinx/) 9.1.0 (BSD-2-Clause; Python 3.12+) with Sphinx-Needs 8.5.0 (MIT), MyST-Parser | StrictDoc 0.30.2 (HTML, PDF, ReqIF; the exact export formats were not verified from its docs) | Avoid new investment in MkDocs 1.x and Material for MkDocs (maintenance mode per [one reference page](https://pydevtools.com/handbook/reference/mkdocs-material/); announcement date differs by source); Zensical was only existence-checked |
| Word deliverables | Pandoc 3.11 (GPL-2, invoked as an external binary) with `--reference-doc`, plus python-docx or [docxtpl](https://pypi.org/project/docxtpl/) 0.20.2 (LGPL-2.1-only) | npm [docx](https://www.npmjs.com/package/docx) 9.9.0 (MIT) | The container image must carry the GPL notice for Pandoc; record LGPL/GPL tools in the licence inventory |
| Deterministic PDF | [Typst](https://github.com/typst/typst/releases) 0.15.1 (Apache-2.0; Python binding `typst`) | [WeasyPrint](https://pypi.org/project/weasyprint/) 70.0 (BSD); Quarto (MIT) | LaTeX and DocBook toolchains not researched |

The document types the downstream authoring must feed come from older standards the researchers could only partly read. MIL-STD-498 (cancelled 1998) defined the System/Subsystem Specification, Software Requirements Specification, Interface Requirements Specification and System/Subsystem Design Description among 22 DIDs ([Wikipedia](https://en.wikipedia.org/wiki/MIL-STD-498)); the SRS DID DI-IPSC-81433A (December 1999) remains a format reference ([EverySpec](https://everyspec.com/DATA-ITEM-DESC-DIDs/DI-IPSC/DI-IPSC-81433A_3709/)); MIL-STD-961E with Change 3 governs defence and program-unique specification format and content ([EverySpec](https://everyspec.com/MIL-STD/MIL-STD-0900-1099/MIL-STD-961E_CHG-3_52833/)); and ISO/IEC/IEEE 29148 clauses 8 and 9 give outlines and content for BRS, StRS, SyRS and SRS ([ANSI preview](https://webstore.ansi.org/preview-pages/BSI/preview_30357521.pdf)). **PIDS, the SSDD DID number, ICD format and the MIL-STD-490/961 lineage were not verified**, and the notes found no standard prescribing how requirement databases generate documents. Whether Sphinx-Needs or StrictDoc outputs satisfy the owner's customer-specific templates was not assessed.

Rules for the export stage (I): expose per-document views (SSS from system-level items, SRS from software items, IRS or ICD from interface items) filtered by level and allocation instead of one flat list; keep superseded IDs visible in change tables and trace appendices rather than silently renumbering; stamp every generated document with the database baseline ID and generation time so it ties to a baseline; offer a read-only "preview as SRS/SSS" so reviewers see a merge in context; embed requirement IDs as bookmarks or content controls in Word; and keep the canonical approved baseline in the database and in Git-tracked exports. The `authoring-documents-from-requirements` skill composes only from approved requirements, with each sentence traceable to requirement IDs. The gap analysis adds (I) that each generated paragraph should trace back to the merge decisions that produced it, which existing tools do not ingest.

## Risks and caveats: licences, supply chain, unverified items and untested design bets

**Licences.** Copyleft is not disqualifying for a tool run as a separate process or used internally, but the owner should set a policy up front; the researchers' example is "no AGPL/GPL linked into the app; GPL command-line tools allowed as external processes" (I).

| Flag | Items (all from registry or licence-file reads) |
|---|---|
| Strong copyleft | TRLC (GPL-3.0), LOBSTER (AGPL-3.0), OpenFastTrace (GPL-3.0), python-igraph (GPL), BASIL (GPL-2.0), NoRBERT supplement (GPL-3.0-or-later), OSRMT (GPLv2) |
| Weaker or file-level copyleft | Doorstop, psycopg 3 and the SysML v2 Python client (LGPL-3.0), docxtpl (LGPL-2.1), pyxlsb (LGPL-3.0+), pygit2 (GPLv2 with linking exception), Pandoc (GPL-2), elkjs (EPL-2.0 or GPL-3.0-or-later), axe-core (MPL-2.0), Eclipse and OpenReq projects (EPL) |
| Non-commercial or custom model licences | jina-embeddings-v3 and v5, jina-reranker-v3.5 (CC-BY-NC-4.0), llama-embed-nemotron-8b (custom NVIDIA non-commercial), EmbeddingGemma-300m (gated `gemma`), EmbeddingGemma 2 (Apache-2.0 tag but the card links a Gemma 4 licence page) |
| BSL, Elastic, proprietary or commercial | lakeFS and immudb (BSL, not OSI open source), Arize Phoenix (Elastic-2.0), Handsontable, AG Grid Enterprise, Syside's `syside` (proprietary), Claude Agent SDK TypeScript package (Anthropic commercial terms), Prodigy (paid), document skills in anthropics/skills (source-available) |
| Licence unclear | PyPI licence field blank for FlagEmbedding, hnswlib, text-dedup, DSPy, Ragas, sqlite-vec, typst, guidance and smolagents (repo files used instead); PyMuPDF licence unverified; verify before shipping an SBOM |

**Archived, renamed, stale or fast-moving.** Kuzu was archived on 2025-10-10 (its fork LadybugDB is reported by a secondary blog; [article](https://oneuptime.com/blog/post/2026-08-12-kuzu-archived-pin-0-11-3-fork-or-migrate/view)); Google's diff-match-patch was archived 2024-08-05; `reactflow` is superseded by `@xyflow/react`, `@base-ui-components/react` was renamed `@base-ui/react`, `@finos/perspective` is deprecated, and Ragas moved GitHub organisations; Material for MkDocs is in maintenance mode. No registry release in over 12 months: hnswlib, dedupe, recordlinkage, rank-bm25, textdistance, simhash, pysbd, number-parser, medspacy, pyreqif, py-jama-rest-client, immudb-py, doltcli, doltpy, pyecore, mkdocs, panflute, pandocfilters, uptrain, openpyxl and python-docx (the last two read as mature rather than abandoned), plus npm graphology, Observable Plot, Glide Data Grid and mantine-react-table. Dormant tools: Capra, ProR/RMF, OSRMT, Tracey, the SysML v2 Python client; Argilla's authors say they have moved on. Fast-moving dependencies (releases in 12 months) to pin: LiteLLM 252, Pydantic AI 200, Arize Phoenix 195, Claude Agent SDK Python 147, Inspect AI 118, Docling 96, FastAPI 94, DuckDB 90, and on npm Storybook 828, Playwright 562, `@hey-api/openapi-ts` 541, React 425, Zod 229. No vulnerability scan (OSV or Dependabot) was run on any package.

**LiteLLM supply-chain report (single secondary source: verify, then pin and mirror).** A security blog states that on 2026-03-24 a compromised LiteLLM 1.82.8 was published to PyPI with 1.82.7 carrying the same payload, both yanked by 20:15 UTC the same day; the payload was a malicious `litellm_init.pth` that runs on every Python start, harvested SSH keys, `.env` files and cloud and Kubernetes credentials, and exfiltrated them; it was reportedly found when the package arrived as a transitive dependency of an MCP plugin in Cursor ([Bastion](https://bastion.tech/blog/litellm-pypi-supply-chain-attack)). An OECD.AI incident listing and other outlets appeared in search results but were not read ([OECD.AI](https://oecd.ai/en/incidents/2026-03-24-ca8f)); **no vendor post-mortem was located and it is unknown whether official Docker images were affected.** The blog's mitigations: exact-version pins, hash-locked installs (`--require-hashes`), `pip-audit` in CI, auditing `.pth` files, isolated virtualenvs or containers, secrets out of `.env`, and egress monitoring. Given LiteLLM's release cadence the researchers add (I): consume it from an internal mirror or vendored wheels, pin the container image digest, keep secrets out of the build environment, and write app code against the OpenAI-compatible API so the gateway can be removed.

**Unverified items to carry forward.** The meaning of "MSoSa" (probable MSOSA, not confirmed) and of "systems v2"; whether Teamwork Cloud publishes an OpenAPI description; 2026x MagicDraw file-format documentation; whether SysML v1 projects convert to v2; "Requirements Scout"; a DOORS MCP server; a propose-then-approve MCP server; the live MTEB ranking; EmbeddingGemma 2's licence; any NLI model fine-tuned on requirements; the accuracy of local open-weight judges; hardware and compute figures (all order-of-magnitude); Langfuse offline operation and its exact Compose services; container-image provenance; Capella IFE sample licence and format; Dalpiaz licence; PURE v2.0 contents; and the availability and licences of the labelled conflict-pair files.

**No public gold set with a full relationship taxonomy exists.** Public duplicate and conflict sets are tiny in positives, partly synthetic, mixed in licence (57.4% of 62 public RE datasets state none) and internally inconsistent in the papers that use them, so published F1 values (0.609 to 0.974 for PassionNet) are not priors for this task; and the only prevalence anchor is the 13.6% average clone coverage from 28 specifications.

**Design bets that are hypotheses, not results.** The following come from the researchers' reasoning, and the notes say none has been validated.

| Hypothesis | How to test it |
|---|---|
| Slot-wise (EARS-style) comparison predicts human equivalence judgements | Score slot agreement against the adjudicated gold set; no paper validates it |
| The ten veto rules block bad merges without blocking too many true equivalents | Minimal-pair suite must give zero auto-suggested merges; measure false-block rate on gold equivalents |
| The canonical-selection score (centrality, completeness, quality, authority) matches reviewer choices | Compare with reviewers' picks; no sourced evidence for any selection rule |
| Thresholds (`tau_high`, `tau_low`, `tau_edge`, `tau_min`) and the LLM band | Derive on the gold set with Wilson bounds; re-estimate about every 200 decisions; log threshold versions |
| Average-link clustering beats HDBSCAN for small tight groups; the p^k chain argument | B-cubed comparison on the gold set |
| Six labels can be annotated reliably | Inter-annotator kappa or alpha per label; no published agreement study exists |
| The judge protocol (withheld scores, both orders, N = 3, structured evidence) improves reliability and does not anchor reviewers | Ablations and the 30% blind-review anchoring test |
| Local open-weight judges are accurate enough | Local bake-off; no accuracy evidence for gpt-oss or Qwen3.8 on requirements |

**Evidence quality.** Several cited papers are preprints; model scores are vendor-reported; ISO, INCOSE, SAE and RTCA/EUROCAE texts were partly unreadable; DFARS and ITAR points come from a vendor explainer and a promotional blog; a "best AI requirements software" article is sponsored (low reliability); and some pages conflict (the SysML v2 adoption date, the ED-324 target, EARS's five versus six patterns, Innoslate's 75% versus 78% ceiling). Several 2026 judge-bias papers were read only as index summaries. The ISO restriction on prompting AI tools with ISO content (above) applies to anything loaded into agent skills.

**Sensitive data.** Whether the program's requirement text is CUI or export-controlled is outside what the notes can say. Nothing in them supports sending such text to an external API, and the GtWR itself warns that some quality tools require uploading requirements to vendor servers. This is general information, not legal advice; the responsible compliance office decides.

## Conclusion: the decision ledger is the product, and the veto layer is the safety case

Two implications go beyond the component catalog. First, the same stream of reviewer decisions, each tagged with the method that proposed it, is simultaneously the workflow record, the audit trail, the metrics source and a first labelled relationship-taxonomy dataset for this task, because the research found none public and no vendor publishing accuracy for duplicate detection. That makes the ledger design (method attribution, reason codes, stale flags, hash chaining, frozen test split) the highest-leverage early decision, ahead of any model choice. It also means the metrics screen and the gold set are one asset, so every reviewer click should be captured in a form that can be replayed against the next model.

Second, the evidence says to put safety where the guarantees are deterministic. LLM judges reached self-agreement alpha of only 0.27 to 0.79 on repeated runs, a top model in an INCOSE-criteria benchmark missed flaws at a median false-negative rate of about 0.67, and showing reviewers the model's verdict moved their agreement with ground truth from kappa 0.0486 to 0.2223 in one study, an effect that could be accuracy or could be anchoring. A system that lets such a judge propose, while code vetoes any change to a number, unit, modal or negation, and while reviewers see evidence before verdicts on high-risk lanes, can use AI without relying on it. The consequence for sequencing is to build the adversarial minimal-pair suite and the ReqIF round trip before touching a model: they are cheap, they gate everything else, and they are where this problem differs from generic duplicate detection.

## First 30 days: build the deterministic core and the ledger before the AI

This is a proposed priority order (I), not a staffing estimate; the only duration in the notes is the 2-3 reviewer-days for the gold set. The riskiest prototypes the researchers named go first: the ReqIF round trip on the owner's real exports, the hash-chained audit log with a verifier script, the embedding shortlist on labelled pairs, Tiptap track-changes maturity, and Langfuse offline operation.

| Days | Build | Learn or decide | Exit test |
|---|---|---|---|
| 1-3 | Repo, GitLab CI with Podman, internal PyPI/npm mirror plan, hash-locked lockfiles on Python 3.12/3.13; body-of-knowledge repo scaffold with AGENTS.md; skills 1 and 3 as stubs | Answers to the confirmation list below; licence policy; data classification; LiteLLM pin policy. Skim the free GtWR v4 summary sheet, NASA SEH 6.2, EARS, RFC 2119 | Written decisions on format, classification and licence policy |
| 3-8 | Ingestion: export ReqIF from the Cameo Requirements Modeler plugin, parse with `reqif`, anonymise a shareable corpus, define the canonical record (MID/UID, fingerprint, original and normalised text); probe the `.mdzip` XMI route in parallel; CSV/XLSX fallback | ReqIF dialect quirks; SysML v2 only if "systems v2" is SysML v2 | Round trip on a real export; anonymised test corpus; scale and parse-time numbers |
| 6-12 | Deterministic core: normaliser, modal, polarity, condition and quantity slots (Pint, quantulum3, spaCy rules), vetoes 3 to 8, minimal-pair adversarial suite from PURE sentences, guard unit tests | Lexical blind spots (rerun the toy table on your own pairs); unit semantics and comparator direction | Zero auto-suggested merges across number, unit, modal and negation toggles |
| 10-16 | Mechanical ladder and bake-off: RapidFuzz, TF-IDF/BM25, Qwen3-Embedding-0.6B, BGE-M3 and MiniLM floor (EmbeddingGemma 2 and Granite only after licence reading), FAISS top-k, pooled sampling; reviewers label 600-1,000 pairs with a written guideline and 25-30% double labelling | RRF, calibration, B-cubed, kappa and alpha | Frozen test split; per-label kappa; first per-source PR curves |
| 14-20 | Stacker (logistic regression with slot flags, sigmoid calibration), thresholds with Wilson bounds, average-link clustering with validity check, DuckDB metrics screen | Reliability diagrams; chaining behaviour on your data | Largest-cluster size and min-pairwise-probability under control; ECE by slice |
| 18-25 | Review UI: TanStack Table plus Virtual, jsdiff, risk lanes, four lens labels, status lifecycle, hash-chained event table and verifier script, fingerprint staleness, Playwright with axe | Gerrit labels, OpenRefine cluster flow, automation-bias design | A reviewer clears a cluster keyboard-only; audit verifier passes; Tiptap spike decision |
| 22-28 | AI stage: pinned, hash-locked LiteLLM from the mirror to Ollama or vLLM; Pydantic AI JSON output; both orders, N = 3; all ten vetoes; invoke only on the uncertain band; personas as AI pre-review subagents; Promptfoo or Inspect AI regression in CI | Local judge bake-off; anchoring test and canaries | AI proposals compared with mechanical on the same ledger (kappa, complementarity); nothing applies without a human |
| 26-30 | Export: Sphinx-Needs or StrictDoc render from the approved baseline, Pandoc .docx, baseline ID and superseded IDs, ReqIF re-export; first ADRs and the golden set committed to the body-of-knowledge repo | Customer document templates | One document generated from an approved baseline with trace to merge decisions; threshold retrospective |

## What to ask the project owner to confirm

| # | Question | What it decides |
|---|---|---|
| 1 | What exactly does "MSoSa" mean (Magic Systems of Systems Architect / MSOSA?), which release and edition, SysML v1 or the 2026x SysML v2, and do projects live in Teamwork Cloud? | The ingest route and whether `.mdzip`, ReqIF, API or SysML v2 text applies |
| 2 | What is "systems v2": a SysML v2 model, an internal project name, something else? In what file format? | SysML v2 tooling versus ReqIF/CSV |
| 3 | What file formats can each project actually export (ReqIF from the Cameo Requirements Modeler plugin, CSV/XLSX, DOCX), and how many requirements or model elements is "massive"? | Parser scope, scale target, whether MinHash/ANN are needed (the notes suggest full pairwise below about 20k) |
| 4 | Is the requirement text CUI, export-controlled or otherwise restricted, and where may it be processed (enclave, workstation, air-gapped network)? Are any external AI APIs permitted? | Local-only deployment, model choice, logging of outbound calls; the compliance office should decide |
| 5 | Which review roles are required (systems engineer, process engineer, UI/UX engineer, new user), who staffs them, and which sign-offs are binding versus advisory? | Lens labels, block permissions, reviewer capacity for the gold set |
| 6 | Are the requirements baselined, who owns them, and does a change board govern edits? Are cross-owner merges in scope? | Gating of the lifecycle; cross-owner merge rules |
| 7 | Is the tool advisory only, or will anyone take verification credit for its output? | Intended-use statement and DO-330-style assessment |
| 8 | Which writing conventions apply (GtWR v4 subset, EARS, shall/will/should rules) and is there a project glossary? | Rule baseline, slot extractor, new-user persona checks |
| 9 | Which downstream documents are needed (SSS, SRS, IRS/ICD, SSDD, PIDS, customer DIDs/DRDs) and are Word templates mandatory? | Export stage design (Sphinx-Needs versus Word) |
| 10 | What compute exists (GPU, RAM), is the network air-gapped, and are internal PyPI/npm/container mirrors available? Is Podman rootless a constraint on GitLab runners? | Embedding and judge model sizes, mirroring plan |
| 11 | What is the licence policy: copyleft as external processes only? Non-commercial model licences acceptable? | Library and model shortlist |
| 12 | Who will label pairs, how many reviewer-days are available, and is English the only language? | Gold-set size and schedule |
| 13 | How should derived or allocated requirements that intentionally repeat parent text, and equivalent requirements that apply to different configurations, be treated? | Taxonomy edge cases (link, not merge) |
| 14 | Is LiteLLM already deployed or approved, and what is the organisation's supply-chain policy for fast-moving packages? | Gateway choice and pinning |
| 15 | Do you accept the six-label taxonomy and the comparator rule (stricter versus looser by operator)? | The contract that labelling and the UI will encode |

## Appendix A. Making the app work with any input: SysML v2, SysML v1/MSOSA, DOORS, Excel, SQL, Word, PDF

> Section numbers in this appendix are local to it. The code it describes is in the `reqin` folder of the kit.

**Short answer.** Yes, and the way to do it is to stop teaching the app about file formats. Teach it one thing, a **canonical requirement record**, and put every source behind a small **adapter** that only reads. Meaning (which column is the statement, which is the ID) lives in a small **mapping profile**, a text file a person confirms. Then a new spreadsheet layout costs a profile and no code, and a new file format costs one adapter that must pass a shared test suite. Everything after that point (comparison, AI, review screens, export) never knows or cares where a requirement came from.

"Any data" has to mean something precise, or the app will mislead people. It means **any source that contains statement text you can point to**. The app labels every record with how far to trust it (Structured, Tabular, Parsed or Extracted), keeps a link back to where it came from, and refuses to drop anything silently. It cannot promise a lossless round trip back into the source tool, or readable text from a scanned PDF without OCR.

**Built to prove it.** A working reference implementation, `reqin/` (about 3,900 lines of source and 6,500 lines of Python in all, tests included), reads eight kinds of file input through one pipeline: CSV, XLSX, a DOORS-style CSV export, ReqIF, SysML v2 text, SQL, DOCX and PDF. It also has three live connectors (SysML v2 REST, DOORS Next over OSLC, Digital.ai Agility), a DOORS 9 export script and a watch-folder mode. **224 automated checks pass** (223 where LibreOffice is absent; the PDF-conversion check is then skipped, visibly). **The three live connectors have only ever met in-memory fakes I wrote from documentation, and the DOORS script has never run inside DOORS.** The same downstream comparison function finds the same near-duplicate pair (200 ms against 0.2 seconds) in all eight formats, and across two different sources. A 20,000-row import takes about 1.2 seconds in the sandbox. I then broke the code on purpose in 21 ways (secrets leaking into errors, a redirect to another host, TLS checks off, a write verb on the client, paging that stops after page one, caches removed, the settle time ignored, a `delete` call inside the DOORS script, and so on). 18 were caught at once; the other three showed tests I had not written (OSLC and Agility reading the server twice, and the no-record-vanishes flag never being able to turn false). I added those tests and all three are now caught. I then did the same to the dataset layer (20 deliberate breaks of the checker, the writer, the command line and the fourteen datasets): all 20 were caught. Section 6 says plainly what this does *not* prove.

### 1. The shape: five layers, and only two know about formats

| Layer | It knows | It must not know | Changes when |
|---|---|---|---|
| **Sources** | Files, servers, databases | Anything about review | Never (you do not own them) |
| **Adapters** | How to read one kind of source and describe what is in it | What a field *means* | A new format appears |
| **Mapping profile** | Which source field is the ID, the statement, the verification method | How to read a file | A new layout appears (a text edit, a person confirms) |
| **Canonical model** | One shape for a requirement, a link, a rejected row, and a report | Where the data came from, except a locator | Rarely, deliberately |
| **The app** (compare, AI, review, ledger, export) | Only the canonical model | Formats, tools, vendors | Features |

Board 10, frame 10.4 in the Excalidraw set draws this. Six rules hold it together:

1. **Adapters read; they never interpret.** An adapter yields what the source said (`RawRecord`, `RawLink`) and nothing else.
2. **Meaning is data.** Mapping lives in a YAML profile saved with the project and replayed on every re-import.
3. **Nothing is dropped silently.** Every raw record ends as a requirement, a *rejected* row with a reason, or a *filtered* row with a rule. The pipeline checks `raw = kept + rejected + filtered` and reports it.
4. **Every record carries its source locator** (row, ReqIF identifier, page and paragraph) so a person can jump back to the original.
5. **AI may propose, a person confirms.** A proposed profile is flagged as proposed until confirmed, and results from it carry a warning.
6. **Read-only by default.** No adapter writes to a source. Write-back would be a separate, explicit capability.

### 2. The canonical model

This is the whole contract between "reading" and "everything else" (`reqin/model.py`, trimmed):

```python
@dataclass
class Requirement:
    mid: str              # machine ID: sha1(namespace + native ID); stable; never shown to people
    uid: str              # the ID people use (REQ-FCS-0212); may be invented, then uid_synthetic=True
    uid_synthetic: bool
    text: str             # original statement
    norm_text: str        # NFKC, markup stripped, whitespace collapsed: what comparison uses
    fingerprint: str      # hash of norm_text + modal + numbers; changes only if meaning-bearing text changes
    slots: Slots          # modal (shall/should/will), negated, quantities [{value, unit, comparator, base_value}]
    fields: dict          # rationale, verification, allocation, owner, baseline, status
    extra: dict           # every source field the profile did not claim: lossless
    conf: dict            # Exact | High | Medium | Low, per field
    ref: SourceRef        # adapter, uri, container, locator, revision (file hash / commit id)
    fidelity: Fidelity    # structured | tabular | parsed | extracted
    parent_mid: str | None
```

Why each part exists:

- **MID and UID are different on purpose.** People know `REQ-FCS-0212`; a re-export may renumber or duplicate it. The MID is derived from the source's native ID inside a **namespace you set once per project** (for example `PROJ-A`), so the same requirement keeps the same MID across re-imports. Matching on re-import would go MID, then UID, then fingerprint (designed here, **not built**). Row numbers make poor native IDs because they move when rows are inserted. When a source has no native ID and the profile names none, the app invents a UID from the locator and **labels it invented** (`Low`).
- **Fingerprint** is how a re-import tells "reworded" from "reformatted". It ignores markup and whitespace and notices a changed number, unit, comparator or modal verb. Doorstop uses the same idea for staleness (see the report).
- **Slots** are extracted by rules, not by AI: `shall`/`should`/`will`, negation, and numbers with units and comparators (`at least`, `no more than`, `within`). `200 ms` and `0.2 seconds` both get `base_value 200` in time, so a downstream step can see they are the same quantity. Only time, mass, length and frequency are converted; anything else keeps its unit as written.
- **`extra`** keeps every source field the profile did not claim, so nothing a source said is lost. The test suite checks this on every format.
- **Confidence labels** are the ones the prototype's Import screen already shows. `Exact` means copied from a field you chose. `High` means a deterministic rule on a named field (a value map, a regex, markup stripping). `Medium` means guessed from names or values. `Low` means defaulted or invented.
- **Fidelity** is a property of the *source route*, not of a record. Structured sources have stable IDs and links. Tabular sources have rows you map. Parsed means a light read of model text. Extracted means found in prose.

### 3. The adapter contract

An adapter has four jobs (`reqin/adapter.py`):

```python
class Adapter(ABC):
    name: str;  fidelity: Fidelity;  caps: Caps    # structured_ids, links, hierarchy, write_back, incremental

    def sniff(self, src) -> float            # 0..1: can I read this? Cheap: extension and first bytes
    def discover(self, src) -> Discovery     # containers and fields with samples, row counts
    def read(self, src) -> Iterator[RawRecord | RawLink]   # what the source says, untouched, read-only, deterministic
    def revision(self, src) -> str           # file hash, commit id or query hash
```

- **Registry and sniffing.** Adapters register with `@register`. `sniff_all()` ranks them, and `pick_adapter()` takes the best at 0.5 or above, or the one you name. A broken sniff never blocks the others.
- **Plug-ins without touching the core.** A third-party package declares an entry point in the group `reqin.adapters`, and `load_adapters()` imports it. A new format ships as a package.
- **Containers** are whatever the source calls a group: a sheet, a ReqIF spec-object type, a SQL query, a document's prose or one of its tables. A profile can select which containers are requirements (a Cover sheet or a Heading type is not).
- **Capabilities** are declared honestly. Every adapter here is read-only (`write_back=False`).

### 4. Mapping profiles: where meaning lives

A profile is a small YAML file. This one (`profiles/msosa_reqif.yaml`) maps a ReqIF export:

```yaml
profile: msosa-reqif
adapter: reqif
namespace: DEMO-MSOSA          # keep stable across re-imports: part of every MID
containers: [Requirement]      # spec-object types that are requirements; headings are not
fields:
  uid:          {from: ["ReqIF.ForeignID", "ReqIF.Name"]}      # first non-empty wins
  text:         {from: ["ReqIF.Text", "Text"], strip_markup: true}
  rationale:    {from: "Rationale"}
  verification: {from: "Verification Method", map: {T: Test, A: Analysis, I: Inspection, D: Demonstration}}
```

Links can come from the source (ReqIF relations, SysML `satisfy`) or from a column. For a spreadsheet with a "Parent ID" column:

```yaml
links:
  - {kind: derive, from: "Parent ID"}     # a column holding target IDs, split on comma, semicolon or space
```

Operators: `from` (list, first non-empty), `join` + `sep`, `regex` (group 1), `map` (case-insensitive value translation), `default`, `const`, `strip_markup`, and an explicit `conf`. A profile can also filter rows with `where` (`{Object Text: {not_empty: true}}` to skip DOORS heading rows) and derive links from a column.

**The proposer.** With no profile, the app writes a *proposed* one from what it sees, using deterministic heuristics: the statement column is the one whose values most often contain `shall/should/will/must/may` and are long; the ID column matches an ID-like name, is unique and filled, and its values look like IDs (`SRS-12` beats `12`, which is why a DOORS "Object Identifier" wins over "Absolute Number"); a verification column has values from `T/A/I/D` or `Test/Analysis/...`. Each proposed rule carries a label (`High`/`Medium`) and a one-line reason, which is what the Import screen shows (frame 10.2). `reqin propose file.xlsx` prints it as YAML for a person to edit.

**What AI is for here.** AI can *propose* a profile when names and values are not enough, and it can *propose segmentation* of prose into statements. It must not apply either. The reference code has **only the heuristic proposer**; an AI refinement step is a design, not code. This is the same rule as the rest of the project: mechanics first, AI late, a person decides. It also keeps imports cheap and reproducible. A 20,000-row file is read by code in about a second, not by a model.

### 5. Source by source: the route, what exists, and what is not verified

| Source | Route and adapter | Fidelity | What I verified | Caveats |
|---|---|---|---|---|
| **SysML v2 (server)** | Systems Modeling API (REST), `sysml_api`; details in `CONNECTORS.md` | Structured | Rebuilt: reads page by page (Link header or `page[after]` cursor) and stops with an error rather than truncating when paging does not advance; finds the project by name or id; takes the default branch's head commit, or the project id as the commit id as SysON does; joins `documentation` to its requirement; keeps parent and `Dependency` links. Endpoint shape from SysON's docs ([SysON docs, v2024.11](https://doc.mbse-syson.org/syson/v2024.11.0/user-manual/integration/api.html)). Tested against an in-memory fake, and the shared GET-only client (retries, redirects, TLS, size cap) against real local HTTP and HTTPS servers | **Never run against a real server.** Paging style, branch/head lookup, relationship names and JSON keys are assumptions behind options. An earlier version of this adapter claimed to page and did not; that was a bug, now fixed and tested. Teamwork Cloud's API version is unknown to me. Run `reqin sample` first |
| **SysML v2 (files)** | `.sysml` text, `sysml_text` | Parsed | Tested on a synthetic file (nested definitions, wrapped `doc` comments, a comment that contains the word "requirement", `satisfy ... by ...`) | A lightweight scanner: no imports, redefinitions, expressions or units. For the full grammar use the Pilot Implementation. KPAR packages are not read by the reference code |
| **SysML v1 / MSOSA** | **ReqIF** from the Cameo Requirements Modeler plugin, `reqif` | Structured | The plugin's ReqIF route is documented in the report; the adapter was tested on a hand-written ReqIF 1.0 file in the standard shape | **No real MSOSA export was available.** ReqIF dialects differ by tool, so the first real export may need profile edits or an adapter fix. This is the riskiest item, as the report already says |
| **MSOSA project file** | `.mdzip`, `mdzip` | Structured | Layout documented since 17.0.1: a zip of XMI 2.4 with entries such as `com.nomagic.magicdraw.uml_model.model` | **Deliberately not implemented**: no documented reader contract. The adapter recognises the file and tells you to export ReqIF instead. It is the template for the next adapter |
| **DOORS (classic)** | ReqIF export, or CSV/Excel export | Structured / Tabular | From 9.5, create a RIF definition in the database properties and choose ReqIF v1.0 ([Jazz article](https://jazz.net/library/article/1243)) | Attribute names are defined per module, so modules can name the same thing differently (the article shows numeric suffixes such as "Criticality 2" after import into DOORS Next), and a profile's `from` list covers the variants. DOORS Next did not import system attributes such as created by or modified on in that article, so check whether your export carries them. OLE objects are exported as separate `.rtf` files. A CSV profile for the standard attributes (`Object Identifier`, `Object Text`) is in `profiles/doors_csv.yaml`; check the names against your own module **Added:** `connectors/doors9/export_requirements.dxl` is a read-only DXL script that writes the CSV the `doors_csv` profile reads. The CSV side is tested, a test scans the script for edit/delete/save/share/create calls, and **it has never run inside DOORS**. If your site exposes OSLC through DOORS Web Access, the `oslc_rm` route below might apply (assumed, not checked). |
| **DOORS Next** | ReqIF `.reqif` / `.reqifz` | Structured | IBM documents ReqIF import and export of both formats ([IBM](https://ibm.com/support/knowledgecenter/SSYMRC_7.0.2/com.ibm.rational.rrm.help.doc/topics/t_reqif_intro.html)); the adapter unzips `.reqifz` | Not tested on a real file. IBM says ReqIF is not a supported way to migrate whole repositories, which does not matter for reading **Added:** `oslc_rm` reads requirements over OSLC RM (rootservices, then catalog, then a paged query). Tested against a fake only. Sign-in is a session cookie or token read from an environment variable; OAuth and form logins are not built (`auth_hook` is the seam). |
| **Excel / CSV** | `tabular` | Tabular | Tested: title rows above the header, a Cover sheet, a hidden sheet, a blank row inside the data, duplicate headers, and a Windows-1252 semicolon CSV. By design, not tested: formula cells are read as their cached values and never executed | You confirm the columns once, then the profile replays |
| **SQL** | `sql` (SQLAlchemy URL plus a SELECT) | Tabular | SQLite: a guard that allows one `SELECT`/`WITH` statement, and a database opened `query_only` | The real control is a **read-only database role**. Other databases need their driver; they were not tested |
| **Word** | `docx` | Tabular for tables, Extracted for prose | Tables become rows; paragraphs with `shall/must/should/will` become candidates, with a location and a section heading; one paragraph with two obligations splits in two | Heuristic. Old `.doc` must be converted first (LibreOffice) |
| **PDF** | `pdf` (pdfplumber) | Extracted (tables Tabular) | Ruled tables are read as tables; the rest as text blocks with page locators; pages with no text layer are reported | **Borderless tables read as text lines with the columns interleaved**: my first run produced "The Power Subsystem shall Analysis not exceed…" before I excluded ruled tables from the prose pass. Scanned PDFs need OCR, which is not included. Docling (listed in the report) is a stronger reader and could sit behind the same contract (I) |
| **Digital.ai Agility** | REST (Data API, GET only), `agility`; or an export file through `tabular` with `profiles/agility_export.yaml` | Structured / Tabular | Response shape taken from public documentation, not re-checked against an instance; paged with `page=size,start`; identity survives edits because the trailing moment is stripped from the asset id; `Super` becomes the parent and `Dependencies` become trace links. Tested against an in-memory fake | **Never run against a real instance.** Stories and features are not always requirements: choose the asset types and a `where` filter |
| **Jama, Polarion, Jira...** | A later adapter each, starting from `connector_template/` | Structured | Nothing | Not built. Their export-to-CSV or ReqIF paths already work today through the adapters above |

### 6. What was tested, and what that does and does not show

**The conformance suite** (`tests/test_conformance.py`) runs the same eight properties against a fixture in every format. A format is "done" when it is listed there and green.

| Property | What it checks |
|---|---|
| Sniff | The right adapter ranks first |
| Discover | Containers and fields come back with samples |
| Counts, no silent drops | `raw = kept + rejected + filtered`; every rejection has a reason |
| Verbatim text | After normalisation the statement equals the original, for every real UID |
| Identity and provenance | Unique MIDs, a locator on every record, a fidelity and confidence on every field |
| Deterministic | Two imports give identical MIDs and fingerprints |
| Source untouched | The file's hash is the same after import |
| Nothing lost | Every non-empty source field is claimed by the profile or kept in `extra` |

Beyond that: 16 behaviour tests (units and comparators, markup, proposed versus confirmed profiles, value translation, DOORS headings, ReqIF hierarchy and `derive` links, `.reqifz` archives, links from a column, SysML nesting, extracted-record flags, legacy CSV encodings and duplicate headers, the SQL guard, a read-only database, the `.mdzip` refusal, and that the no-record-vanishes flag can actually go false), 2 downstream tests (same code, every format, plus across two sources), and the live-connector work: 55 tests of the three live connectors against in-memory fakes (paging at several page sizes, link directions, login pages, loops, lying totals, secrets, read-once, GET-only), 12 tests of the shared client against real local HTTP and HTTPS servers, 3 of the DOORS script, 16 of the command line and watch mode, 3 that keep the guide in step with the code, and 51 of the dataset layer (the writer, a checker that must catch each of 19 deliberate corruptions plus several more cases, and the fourteen test datasets). **65 + 16 + 2 + 55 + 12 + 3 + 16 + 3 + 51 = 223 checks that need no office software, all passing.** The PDF fixture is generated in pure Python (reportlab). A 224th check converts the same document with LibreOffice when it is installed and is skipped, visibly, when it is not. Beside these: 10 tests of the real-data guard and 9 of the connector template. Run on Python 3.11, 3.12 and 3.13 in clean virtual environments.

**It does not show:**

- That a real MSOSA or DOORS export imports cleanly. The fixtures are synthetic and written by me. The next step is to add **one anonymised real export of each** as a fixture, and let the suite tell you what breaks.
- That the heuristics find the right columns on messy real spreadsheets. They gave `High` or `Medium` labels on my fixtures, and a person still confirms.
- That **any live connector works against a real server.** SysML v2 REST, OSLC RM and Agility have only met fakes I wrote from documentation, so every request shape, paging style, header and sign-in step stays an assumption until someone runs `reqin sample` against the real system. Sign-in is by token or cookie from an environment variable; OAuth, form and OIDC logins are not built.
- That the DOORS 9 DXL script runs. It has never been inside DOORS.
- That the container builds or the pipeline runs on GitLab. No container engine was available here: the image's test stage was simulated by installing only the files the Containerfile copies, and `.gitlab-ci.yml` passed a YAML lint and GitLab's published schema but has not run on a runner.
- Behaviour at 100,000 objects, in other languages, or under hostile input. The SQL guard is defence in depth, not a security boundary.

### 7. Adding a new input: three paths

**Path 1: a new spreadsheet, CSV or SQL layout. No code, minutes.**
`reqin propose layout.xlsx > profile.yaml`, edit the column names, then `reqin import layout.xlsx --profile profile.yaml`. Read the report: `invariant_ok`, rejected and filtered counts, unclaimed fields. Commit the profile with the project.

**Path 2: a new file format. One adapter, hours.**
1. For a file format, copy `adapters/tabular.py` and implement `sniff`, `discover`, `read`. For anything that talks to a server, start from `connector_template/` instead: a working, tested example with five `TODO(agent)` seams and a ready agent prompt, shipped as its own package. `CONNECTORS.md` is the guide.
2. Add a small, anonymised fixture to `tests/make_fixtures.py`.
3. Add one line to `CASES` in `tests/test_conformance.py`.
4. Run `pytest`. When it is green the adapter is done, and nothing else in the app changes.
5. Ship it in its own package with an entry point in the group `reqin.adapters`.

**Path 3: unstructured documents.** Use `docx` or `pdf`. Treat every record as unverified until a person has checked it against its locator (frame 10.3 shows the screen).

**Prompt for an agent that writes an adapter.** "Read `INPUT_LAYER.md` sections 1 to 3 and `adapters/tabular.py`. Implement an adapter for `<format>`. It must be read-only and deterministic, yield `RawRecord` and `RawLink` only, and put no field-meaning logic in the adapter. Add an anonymised fixture, add it to `CASES`, and make `pytest` pass. Report what the fixture does not cover, and do not weaken any test."

### 8. How this connects to the app and the boards

- **The screen's contract.** The screens read a *dataset folder*, never a file: `reqin import --out-dir` writes one, `reqin check-dataset` verifies one, and `reqin make-datasets` writes the fourteen test datasets a screen must pass. `GUI_CONTRACT.md` defines all of it in plain language.
- **Import screen.** The `Exact/High/Medium` chips on the prototype's Import screen are the `conf` labels. The dry-run report (`invariant_ok`, rejected, filtered, unclaimed fields, duplicate IDs, links pointing outside the import) is the content of frame 10.2. The **fidelity** badge follows every record into the review screens.
- **Pipeline.** This is stage one of the nine-stage pipeline in the report ("read and normalise"). `normalise.py` is the Python port of the prototype's number-and-modal logic, with comparators and base-unit conversion added.
- **Re-import and staleness** (design, not built): match by MID, then UID, then fingerprint, and report added, removed, changed (fingerprint differs) and stale (a decision exists on text that has since changed).
- **Write-back** is out of scope for adapters here. Each adapter would declare `write_back=True` only when it can prove a round trip on a real export. The report already names the ReqIF round trip as the riskiest prototype.

### 9. Questions for the project owner, and cautions

1. **Which exports can you actually get?** The most useful single input is one **anonymised ReqIF from MSOSA** and one from DOORS. The `reqif` package ships an `anonymize` command, but its help text is inherited from StrictDoc's SDoc and I did not run it on a ReqIF file, so test it before you rely on it.
2. **What is "systems v2"?** The report could not identify it. If it is a SysML v2 server, send one element's JSON from it and the API adapter's `keys` can be fixed in minutes. If it is an internal project name, the route is unknown.
3. **Where may the AI step run?** Real program requirements may be export-controlled or otherwise restricted. The mechanical path in this section uses no AI at all. Route any AI call through an endpoint your security office has approved, or leave it off. Keep fixtures synthetic or approved for sharing.
4. **Size.** DOORS-to-DOORS Next guidance recommends at most about 5,000 objects per module and about 200,000 in total ([Jazz article](https://jazz.net/library/article/1243)). Your largest module is the right scale test, and ReqIF parse memory at that size was not measured.
5. **Licences.** Check the licence of each dependency (`reqif`, `openpyxl`, `pdfplumber`, `python-docx`, `SQLAlchemy`) before you ship the code inside a product.

### Sources

- [SysON: SysML v2 REST API](https://doc.mbse-syson.org/syson/v2024.11.0/user-manual/integration/api.html) (endpoint paths, "not fully available yet")
- [Jazz: exporting from Rational DOORS and importing to DOORS Next by using ReqIF](https://jazz.net/library/article/1243) (DOORS 9.5+ ReqIF export, caveats, size guidance)
- [IBM: importing and exporting ReqIF files](https://ibm.com/support/knowledgecenter/SSYMRC_7.0.2/com.ibm.rational.rrm.help.doc/topics/t_reqif_intro.html) (DOORS Next `.reqif` and `.reqifz`)
- The research report's sections on opening MSOSA projects, ReqIF, Doorstop, StrictDoc and Docling, which carry the Cameo Requirements Modeler and `.mdzip` sources.


## Appendix B. How the Excalidraw boards were made, and how an agent can expand and recreate them

> Section numbers in this appendix are local to it. The code it describes is in the `excalidraw_generator` folder of the kit.

The ten boards (storyboard, wireframes, system flows, UI kit, scale, lenses, group decisions, assistant, more pipelines, any-input) were **not drawn by hand**. Each is produced by a small Python program that writes an `.excalidraw` file. That is why an agent can change one rule (a colour, a banner, a widget) and regenerate every board consistently, or add a screen by writing a function.

**Checked in this session:** all nine earlier boards rebuild **byte-for-byte identical** to the files you already have (`python build_all.py --check`), the package works from a clean copy (`npm ci`, bundle, build, validate, render), and the example in recipe A runs. **Not checked:** opening the files in the live Excalidraw app. Every check used Excalidraw's own exporter (`@excalidraw/utils`) rather than the app. Open one board in Excalidraw before you build on top of the format.

### 1. What is in the package

| File | Role |
|---|---|
| `exc.py` | The scene builder. Turns shapes, text, arrows and frames into valid Excalidraw JSON. Standard library only. |
| `wf.py` | Wireframe widgets (card, button, chip, provenance mark, callout) and the colour palette. |
| `wf2.py` | Higher-level helpers: wrapped paragraphs, tables, checklists, sign-off dots, the sidebar with a lens selector. |
| `wf_a.py` `wf_b.py` `wf_c.py` | Screens 1 to 10 of the original wireframes (open, map fields, overview, review, actions, methods, audit, export, glossary, phone). |
| `sb.py` `flows.py` `kit.py` | Boards 01, 03 and 04: storyboard, system flows, information architecture and UI kit. Each has `build(path)`. |
| `sc.py` `sc2.py` `lens.py` `g7.py` `asst.py` `pipes.py` `screens_input.py` | Screens for boards 05 to 10. |
| `build_wf.py` | Composer for board 02 (it also has `build(path)`). |
| `boards_05_09.py` | Boards 05 to 10 as **data**: title, seed, and the list of screens with their frame sizes. |
| `build_all.py` | Builds every board, validates each, and with `--check` compares to files you already have. |
| `validate.py` | Structural checks (duplicate ids, dangling references, frame order, overflow). |
| `render.py`, `entry.js`, `make_bundle.sh`, `package.json` | Render a board to PNG with Excalidraw's own exporter in headless Chromium. |
| `examples/hello_board.py`, `examples/add_a_screen.py` | The smallest board, and a worked example of adding a screen. |

Deliberately **not** shipped: `bundle.js` (about 20 MB, rebuilt in seconds), `node_modules`, and PNG previews.

### 2. Commands (all verified)

```bash
# Build boards: standard library only
python build_all.py --out out                 # all ten boards, each validated
python build_all.py --only 02,05 --out out    # a subset
python build_all.py --check --out ../excalidraw   # fresh build vs. the files you already have: "identical" or "DIFFERS"

# Look at them: needs Node, Playwright and a Chromium
pip install playwright pillow                 # Chromium: set CHROMIUM_PATH, or use Playwright's own install
npm ci && sh make_bundle.sh                   # one time: builds bundle.js from @excalidraw/utils (MIT) and esbuild (MIT)
python render.py out/05_scale_and_multiuser.excalidraw out/05.png 0.5     # last number = scale
python validate.py out/*.excalidraw
```

Rendering is offline and skips font loading, so the hand-drawn font appears as a plain sans in the PNG preview. In Excalidraw proper it is hand-drawn. Judge text fit with margin, because the real font is a little wider than the preview.

### 3. How to think about it

A board is a stack of **frames**. A frame is one screen or one diagram. Beside each frame sits a **Notes** column of numbered statements that match red numbered **callouts** drawn on the frame. The picture is the layout; the notes are the reasoning. A screen is one Python function:

```python
def s_example(d, ox, oy):            # d = the Doc, (ox, oy) = where this frame's top-left corner goes on the board
    ...draw with frame-local coordinates...
    return ['note 1', 'note 2']      # shown beside the frame, numbered 1, 2 ...
```

Layers, from the bottom:

1. **`exc.Doc`** knows Excalidraw's file format. It knows nothing about requirements.
2. **`wf.Scr(d, ox, oy)`** wraps `Doc` so every coordinate is relative to the frame's corner. It adds widgets.
3. **`wf2` helpers** build repeated structures (tables, checklists, the sidebar).
4. **Screen functions** are the design content.
5. **Composers** (`build_all.py`, `boards_05_09.py`, each `build(path)`) stack screens on a board and write the file.

### 4. `exc.Doc`: the file format and the API

An `.excalidraw` file is JSON: `{"type":"excalidraw","version":2,"source":...,"elements":[...],"appState":{...},"files":{}}`. Each element has an `id`, `type` (`rectangle`, `ellipse`, `diamond`, `text`, `arrow`, `line`, `frame`), position and size, colours, and links to other elements. The builder gets four things right that are easy to get wrong:

- **Text inside a shape** is a separate `text` element with `containerId` set to the shape, and the shape lists it under `boundElements`. `Doc.shape(..., label=...)` does both.
- **Arrows glued to shapes** carry `startBinding` / `endBinding` and appear in each shape's `boundElements`, so moving a box drags its arrows. `Doc.connect` does this.
- **Frames** list their children by `frameId`, and the frame element must come **after** its children in the `elements` array. `frame_end()` appends it last. `validate.py` fails a file that breaks this.
- **Determinism.** Every random value (element ids, seeds, version nonces) comes from `random.Random(seed)`. Same code and same `Doc(seed)` give the same bytes. Use a **unique seed per board**.

| Call | What it does |
|---|---|
| `Doc(seed)` | New scene. |
| `d.frame_begin(x, y, w, h, name)` / `d.frame_end()` | Everything drawn in between belongs to that frame. Cannot nest. |
| `d.rect / ellipse / diamond(x, y, w, h, label=None, fill=, stroke=, sw=, dash=, fs=, family=, align=, valign=, pad=, rounded=)` | A shape, optionally with bound, auto-wrapped text. Returns the element dict. |
| `d.text(x, y, s, fs=14, color=, family=2, align=, w=)` | Free text. `\n` breaks lines. Does **not** wrap. |
| `d.wrap(s, width_px, fs, family=2)` | Wrap to a pixel width using the average-glyph-width table `CW` (family 1: 0.60, 2: 0.55, 3: 0.60, 5: 0.58 of the font size; line height 1.25). |
| `d.poly(points, typ='arrow'\|'line', head=, tail=, dash=, sw=, start=, end=)` | Poly-line or arrow through absolute points. |
| `d.connect(a, b, sa='r', sb='l', label=None, dash=, color=, lx=, ly=)` | Elbow arrow from side `sa` (`l r t b`) of shape `a` to side `sb` of `b`, bound to both. |
| `d.save(path)` | Writes the file. Drops empty unbound text. |

Fonts: `family=1` hand-drawn (titles, annotations, callout captions), `2` clean sans (UI text), `3` monospace (small caps captions, table headers, code-like text). `roughness` is 0 everywhere, so shapes are crisp and only the font is hand-drawn.

### 5. The wireframe vocabulary (`wf.Scr`, `wf2`)

All `x, y` are relative to the frame's top-left corner.

| Call | Draws |
|---|---|
| `s.r(x,y,w,h,label,fill=,stroke=,dash=)` | Rectangle (shape with optional label). `s.t(x,y,s,fs=,color=,family=)` is text. |
| `s.card(x,y,w,h,fill=,dash=)` | White rounded panel. Dashed = optional or not yet built. |
| `s.caps(x,y,text)` | Small monospace caption in soft grey: the label of a section. |
| `s.h1(x,y,text,fs=22)` | Page heading. |
| `s.btn(x,y,w,h,label,primary=,disabled=)` | Button. One primary action per screen. |
| `s.chip(x,y,w,h,label,fill=,stroke=,dash=)` | Small pill: a state or a label. Always a word, never colour alone. |
| `s.bar(x,y,w,frac)` / `bar_h(...)` | Progress bar / labelled horizontal bar. |
| `s.ph(x,y,w,n,gap=)` | Placeholder text lines (grey bars). |
| `s.prov(x,y,kind,label)` | Provenance mark: **square = mechanical**, **diamond = AI**, **circle = person**. |
| `s.num(x,y,n)` | Red numbered callout. The note with the same number goes in the Notes column. |
| `s.check(x,y)`, `checkbox(s,x,y,checked,label)` | Tick marks. |
| `s.tokens(x,y,words)` | A statement with highlighted numbers (amber), modals (blue), negation (red), conditions (violet). |
| `para(s,x,y,text,w,fs=10)` | **Wrapped** text. Returns the y below it. Use this for any sentence. |
| `table(s,x,y,widths,head,rows,fs=,minh=,bold_first=)` | Wrapped table. Cells may be `(text, fill)`. Returns y below. |
| `chk_list(s,x,y,w,[(state,text),...])` | Checklist with `Pass / Needs you / Blocked / Done / Open` chips. |
| `sign_dots(s,x,y,[state x4])` | Four lens markers S P U N: `signed / pending / changes / na / stale`. |
| `kv(s,x,y,key,value)`, `avatar(...)`, `new_frame(d,ox,oy,w,h,name)` | Key-value line; initials circle; open a frame with its background and return a `Scr`. |
| `shell2(s,W,H,active,lens=0)` | App chrome: sidebar with a lens selector, title block, DRAFT banner. Returns the content origin `(168, 76)`. Needs a frame at least about 500 high (the example uses 520). |
| `notes(d,x,y,[(n,text),...],title='Notes')` | The numbered Notes column, placed **outside and right of** the frame. |
| `flows.box(d,x,y,w,h,label,fill,stroke=,dash=)`, `flows.mark(d,x,y,kind)` | Boxes and marks for diagrams (swimlanes, state machines, architecture). |

Palette (names in `wf.py`): `GREY #f1f3f5` page background, `DARK #343a40` body text, `SOFT #868e96` captions, `ACC #1A4DB5` primary action, `RED #e03131` callouts and notes, and the fills `GREEN_BG #b2f2bb`, `AMBER_BG #ffec99`, `RED_BG #ffc9c9`, `BLUE_BG #a5d8ff`, `VIOLET_BG #eebefa`. Provenance colours: `MECH #34424F`, `AIC #8B1F6B`, `HUM #1B6B3A`; assistant (speech bubble) `#0B6E99` on `#e3f4fb`. Diagram fills in `flows.py`: `SRC_F`, `MECH_F`, `AI_F`, `HUM_F`, `GUARD_F`.

### 6. Design rules the boards follow (keep them when you extend)

1. **Grey is structure; colour appears only where it carries meaning.** Lane, state and trust level are always also a word.
2. **Every screen has red callouts and a Notes column.** One idea per note, and the note says *why*, not *what*.
3. **Marks never change meaning:** square mechanical, diamond AI, circle person.
4. **Everything is a draft.** The DRAFT banner is part of the chrome. Nothing on a screen implies an approval.
5. **Sample data only.** Names, counts and IDs come from the synthetic sample. Never paste real program data into a board.
6. **One primary action per screen.** Dashed means optional or not yet built.
7. **A frame is a screen.** Name frames `N.M · Title`, so the boards read as an index in Excalidraw's frame list.

### 7. Where each screen lives

| Board | Composer | Screen functions (file) |
|---|---|---|
| 01 Storyboard | `sb.build` | nine panels in `sb.PANELS` |
| 02 Wireframes | `build_wf.build` | `s_open s_import s_overview` (`wf_a`), `s_review s_actions` (`wf_b`), `s_methods s_audit s_export s_glossary s_mobile` (`wf_c`) |
| 03 System flows | `flows.build` | `flow_pipeline flow_states flow_components flow_sequence` |
| 04 UI kit and IA | `kit.build` | `ia kit tokens lenses questions` |
| 05 Scale | `boards_05_09.BOARDS` | `sc.s1_queue s2_explorer s3_team`, `sc2.s4_states s5_policy s6_numbers` |
| 06 Lenses | same | `lens.l0_overview l1_se l2_pe l3_ux l4_nu` |
| 07 Group decisions | same | `g7.g1_workspace g2_strategies g3_rationale g4_revisions g5_ledger` |
| 08 Assistant | same | `asst.a1_drawer a2_scenarios a3_architecture a4_effects` |
| 09 Pipelines | same | `pipes.p1_map p2_refresh p3_calibration p4_writeback p5_lint` |
| 10 Any input | same | `screens_input.i1_open_any i2_map_any i3_extract i4_arch` |

### 8. Recipes

#### A. Add a screen to a board
Copy `examples/add_a_screen.py`, change the drawing, then register the function. For an existing board add one tuple to its `screens` list in `boards_05_09.py`: `(my_module.my_screen, frame_width, frame_height)`. The width decides where the Notes column sits (`width + 40`), and the height plus 80 is the gap to the next screen. Then:

```bash
python build_all.py --only 10 --out out        # builds and validates
python render.py out/10_input_any_source.excalidraw out/10.png 0.6
```

Look at the PNG. Crop to a frame with Pillow (`Image.open(p).crop((x0,y0,x1,y1))`) when the board is tall.

#### B. Add a new board
Add an entry to `BOARDS` in `boards_05_09.py` with a new `seed`, a `title` and its `screens`. `build_all.py` picks it up and `--only NN` works from the leading number. Never reuse a seed.

#### C. Change something shared, then see what moved
Edit a colour in `wf.py` or a widget in `Scr`, then run `python build_all.py --check --out ../excalidraw`. Boards that use it print `DIFFERS`, and the ones you did not mean to change stay `identical`. That is the regression test for design changes.

#### D. Boards 01 to 04 still say "four lenses sign off" (not yet changed)
The prototype and boards 05 to 10 use the policy rule: the lenses your sign-off policy requires must sign. Boards 01 to 04 were drawn earlier and still show the old text in 17 lines across `sb.py`, `flows.py`, `kit.py`, `wf.py`, `wf_a.py`, `wf_b.py`, `wf_c.py`, `build_wf.py`. Find them with `grep -n "four lenses\|all four" *.py`. Replace each with the policy wording (the constant `BANNER` in `wf2.py` is the banner text), rebuild, and read each changed frame, because the replacement text is longer in places. `flows.py` line 88 is a state box ("APPROVED, all four lenses signed") that should become "APPROVED, required lenses signed". I did not make this change, so the boards you have are still the originals.

#### E. Redraw a prototype screen as a wireframe
Open the prototype page, list its regions top to bottom, and map each to a widget in section 5 (a heading, a card, a table, a chip row). Write the screen function with frame-local coordinates, put a red callout on each region that needs explaining, and write the notes. Render and compare side by side.

#### F. Recreate everything from nothing
`python build_all.py --out out` plus `python validate.py out/*.excalidraw`. If you have the original files, add `--check` to prove the rebuild is identical.

### 9. Definition of done for any board change

1. `build_all.py` exits 0. `validate.py` reports `dup 0`, `dangling 0`, `frame-order 0`.
2. `outside frame` is 0, or each overflow is explained. It means a child drawn outside its frame, usually unwrapped text. Fix it with `para()`.
3. You rendered the board and **looked** at every changed frame. Check text fit, overlapping arrows, and that callout numbers match the Notes.
4. Boards you did not mean to touch still say `identical` under `--check`.
5. No real program data on any screen.

### 10. Things that bit me

- Bare `s.t()` and `d.text()` do **not** wrap. Long sentences overflow the frame. Use `para()` or `d.wrap()`.
- Text width is an estimate (`CW`), not a measurement. Leave 10 to 15 percent spare width in chips and buttons. A label that wraps inside a chip spills out of it.
- `shell2` assumes a frame at least about 500 high. In a shorter frame the sidebar's note overlaps the Glossary button.
- Connector labels sit at the midpoint of the elbow and collide with the line when the gap between shapes is under about 80 px. Widen the gap, or place a separate `d.text` instead of using `label=`.
- Seven arrows into one box merge into one thick bus. That is fine for "many sources into one profile", but not for distinct flows.
- Left-edge callouts at `x=22` can touch text that starts at `x=40`. Use `x=12` where a screen's text starts at 40.
- The frame must be added **after** its children. Do not edit `frame_end()`.

### 11. Prompts to give an agent

**Rebuild and prove it.** "In `excalidraw_generator/`, run `python build_all.py --out out` and then `--check --out <folder with the boards I have>`. Report any board that says DIFFERS. Do not edit any file."

**Add a screen.** "Read `EXCALIDRAW_GUIDE.md` sections 3 to 6 and `examples/add_a_screen.py`. Add a screen `<name>` to board `<NN>` that shows `<what>` for the `<lens>` lens. Use only widgets from section 5, keep the design rules in section 6, give every callout a note that says why, and use sample data only. Build, validate, render, and look at the frame. Report what you saw and anything that overflowed. Do not change other boards; prove it with `--check`."

**Redraw from the prototype.** "Open `<prototype url or file>`, list the regions of screen `<X>`, and redraw it as a wireframe frame in board `<NN>` following recipe E. Every region that is a decision point gets a callout and a note."

**Refresh boards 01 to 04.** "Follow recipe D. Replace every 'four lenses' statement in boards 01 to 04 with the policy wording from `wf2.BANNER`. Rebuild, read every changed frame, and list each replacement with its file and line. Boards 05 to 10 must stay identical."

**Audit.** "Read-only. Render every board at scale 0.4 and list inconsistencies: wording that disagrees with `wf2.BANNER`, marks used for the wrong meaning, a screen with no callouts, a Notes column whose count differs from its callouts. Do not edit anything."

### 12. Licences

`@excalidraw/utils` 0.1.5 and `esbuild` 0.28.2 are MIT (read from their `package.json`). Excalidraw's own app and file format are open source. Check the licence terms of anything else you pull in.
