# v0.16 — Evidence-grounded Requirements RAG

## What is implemented

**00** downloads two specifically allowlisted public sources, indexes them locally, retrieves traceable snippets, and produces **candidate** requirements and an evidence register. This is not an automated approval engine. **01–09 keep their original synthetic benchmark and two-model/E2B workflow.** Step 10 can attach a completed 00 report to the full-run audit ZIP, but does **not** automatically transplant unapproved candidate requirements into the customer brief.

### Sources and download buttons

| ID | Source | Stored files | Scope |
|---|---|---|---|
| `community_credit` | [Community Credit Interviews, Zenodo / Dryad](https://zenodo.org/records/10425908) | Anonymous participant transcripts, interview guide and supplied README | Consumer trust/access interviews in Southern California, 30 interviews in 2022; not a representative financial-services sample |
| `cfpb_sample` | [CFPB complaints](https://www.consumerfinance.gov/data-research/consumer-complaints/) | Official public API response JSON, maximum 60 complaint search hits | Self-selected public complaints; accounts may be unverified; narratives can be absent |

Source materials are **not redistributed in the application ZIP**. When requested, the backend downloads source data at runtime into `./artifacts/evidence/<dataset>/` (a Docker bind mount), keeps `source_manifest.json` with origin URLs, fetched time and raw SHA256, and offers a **separate downloadable ZIP**. Verify licensing/usage rights with original providers. The app's fixed allowlist does not accept arbitrary URLs or credentials. Limits: HTTPS sources, 8 MB/file, 45-second request timeout.

### Retrieval

- Reproducible plain-text chunks with document/source IDs and 0-based exact text-character offsets.
- A bounded BM25 term score and character-3gram fuzzy cosine score fused by Reciprocal Rank Fusion. **These are two lexical views, not neural dense retrieval.** This distinction is deliberate; no embedding model is silently assumed to exist.
- Query, source excerpt, source URL, file name and offsets are retained. No citation is an external legal attestation.
- Optional Qwen model-based extraction returns at most four *draft* problem statements, KPI hypotheses, alternative explanations and candidate requirements. Its IDs must be present in the retrieved evidence register, but citation integrity **does not imply** the proposed conclusion is supported. The optional LLM stage needs configured Ollama; failure is reported, never silently replaced.
- Baseline extraction is deterministic and explicitly marks `REQUIRES_HUMAN_DERIVATION`, and the displayed observations are not normalized into approved requirements.

### Evaluation / uncertainty

| Signal | State | Meaning |
|---|---|---|
| `reference_status` | EXACT_LOCAL_EXCERPT | A source-excerpt pointer was derived from indexed bytes |
| `evidence_validity` | UNVERIFIED | Neither complaint/interview truth nor relevance to the fictional customer has been proved |
| `semantic_entailment` | UNVERIFIED | There is no entailment/NLI gold-reference evaluator in this version |
| `requirements_correctness` | UNVERIFIED | Hypotheses need external/customer domain verification |
| `customer_approval` | NOT_OBTAINED | The synthetic R1 technical approval is not client authorization |

**Evidence ID correctness ≠ evidence validity ≠ diagnostic correctness.** The app's `SIM-SLA-001` and `PUB-001` references are local IDs, not external certified requirements. The old R0/R1 results remain synthetic; retrieval cannot retroactively establish the FIFO hypothesis as a cause of actual complaints.

### Endpoints

```
GET  /api/evidence/datasets
POST /api/evidence/download           {"dataset_id":"community_credit"}
GET  /api/evidence/datasets/{dataset_id}/download
POST /api/evidence/index              {"dataset_id":"community_credit"}
POST /api/evidence/requirements       {"dataset_id":"community_credit","query":"financial service fees","llm_extraction":false}
GET  /api/evidence/results/{rag_id}/bundle
```

`/api/full-run/start` optionally accepts `rag_id`: a saved RAG record is copied into the workflow folder as `00_evidence_grounded_requirements.json` and thus into the signed-off/partial audit ZIP. Nothing modifies `brief`, `R0`, `R1`, existing approvals, or the independent verifier. If the id is invalid, the request fails.

### Reproducibility and test scope

```
cd backend
PYTHONPATH=. pytest -q
```

Offline automated tests use a fixed miniature corpus and mocks for external downloads and long-running E2B/Ollama. Live dataset availability, rights, complete React/Vite build, and accuracy of the generated problem statements are **not** demonstrated by those tests. This is a single-user local demonstration, not a secure multi-tenant ingestion service.
