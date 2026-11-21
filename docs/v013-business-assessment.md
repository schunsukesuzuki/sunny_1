# v0.13 — Business Value & AI Delivery Assessment

## Purpose

Add a **deterministic, audit-linked** two-axis project feasibility report to the existing claims allocation harness. This report is a decision-support artifact for technical presales, **not** customer approval, production authorization, legal compliance certification or proof of financial return.

The rubric is **generic** and contains no interviewer, employer or employee names, titles, or biographical context. There is **no LLM call or assessment prompt** in this feature. This is deliberate: historical Qwen/ODA diagnostic HOLDs must not be overwritten by a newly generated model opinion.

## Use

1. Execute R0, compare Qwen/ODA, record human review, generate/evaluate R1 (steps 01–06), **or** open a saved R1 experiment from step 07.
2. In step **09 Business & Delivery Assessment**, use the auto-populated `experiment_id`, or paste a previously saved experiment UUID.
3. Click **Generate Business Assessment**. This is a local, fast read of stored artifact JSON and selected code; it does not call Ollama or E2B again.
4. Inspect the two evidence-linked evaluation axes, the limited GO/HOLD/NO-GO decision, missing evidence, and next validation actions.
5. Download Markdown via the new endpoint, or download a ZIP with the source experiment, R0 run, proposal, approval and assessment snapshots.

## Rubric dimensions

**Business Value & Feasibility**

- `BV-01` Alignment of customer goal and synthetic operational KPI
- `BV-02` Comparing FIFO vs fixed deadline heuristic vs generated R1
- `BV-03` Pinned MVP scope, human control and approval
- `BV-04` Actual customer demand / willingness to pay — **UNVERIFIED**
- `BV-05` Real-world economics and ROI — **UNVERIFIED**

**AI Delivery & Operational Readiness**

- `AI-01` E2B execution and independent constraint checking
- `AI-02` Separate DEV/HOLDOUT seeds, selected code hash check
- `AI-03` Independent diagnostic quality, with original Qwen/ODA HOLD preserved
- `AI-04` Demo human override and audit chain
- `AI-05` Production workflow, access control, operations — **UNVERIFIED**
- `AI-06` GDPR, insurance regulations and personal data controls — **UNVERIFIED**

Each criterion stores status, source-reference IDs, an evidence-bounded finding, and a suggested next validation. These are **fixed heuristics**, not validated business assessment scales.

## Decision policy (conservative)

- **GO / CUSTOMER_DISCOVERY** only when an independently verified synthetic improvement, intact selected code hash, linked approval, and matching work-hour constraint are present. It means *consider the next customer-discovery step*, **not** business GO or production GO.
- **HOLD / TECHNICAL_VALIDATION** if this limited technical chain is incomplete or fails. A missing/tampered selected R1 code artifact also triggers HOLD.
- **NO-GO / PRODUCTION** for **all** records, because customer, operations, security, financial and legal validation are absent.
- Customer demand and ROI remain UNVERIFIED regardless of the synthetic KPI value. A human override never turns a model's diagnosis HOLD into PASS.

## Evidence semantics

- Report-local IDs `E01`–`E05` are references to saved local artifacts or declared gaps. The earlier application ID `SIM-SLA-001` is an **invented synthetic fixture identifier**, not an external source.
- **Evidence ID correctness ≠ evidence validity ≠ diagnostic correctness.** Local path and SHA-256 values help with traceability and unintentional changes, but **are not cryptographic third-party attestations**.
- `SYNTHETIC`: simulated E2B/test data; `DEMO_CONTROLLED`: demo human intervention; `UNVERIFIED`: missing real customer/external evidence.
- The stored report intentionally does not reproduce the approval actor name or personal data from the underlying approval artifact. The optional bundle does include the original approval audit record; check before sharing it publicly.

## API & artifacts

```text
POST /api/business-assessment/run
  {"experiment_id": "<UUID of completed experiment>"}
GET /api/business-assessment/<assessment_id>/report   # Markdown
GET /api/history/assessments
GET /api/artifacts/assessments/<assessment_id>
GET /api/artifacts/assessments/<assessment_id>/bundle
```

Output is stored in `artifacts/assessments/<uuid>/assessment.json` and `report.md`. Assessment snapshots include local SHA-256 values of all four input JSON records. The ZIP export includes the linked existing source records if present. Every new generation creates a new assessment record; source records are not altered.

## Known limits

This example assesses **one narrow claims-allocation scenario**. It is not a generic presales engine that can automatically ingest arbitrary customer documents, build and deploy a Web app, or evaluate real-world market needs. The underlying fixed deadline-first reference is a heuristic, **not** a globally optimal solver. The `GO/HOLD/NO-GO` rubric is an engineering aid, **not** a validated predictor of commercial success.

Back-end tests use mock E2B and LLM calls, not a real Mac Ollama/GGUF or E2B cloud run. A frontend full production build requires the normal npm dependencies; syntax checking alone is insufficient to certify browser behavior.
