# v0.19 — Evidence → Requirement → Feature → Acceptance / R1 DEV selection gates

> Status: technical presales DEMO. The modeled customer and operational cases are synthetic. External public insurance publications document problems but do not authorize customer-specific requirements, prove FIFO causality, or define service SLAs.

## Problem addressed

v0.18 retrieved insurance-source evidence about **timely progress updates**, yet evaluated only FIFO/reviewer scheduling. That is a **wrong feature being tested**, even when the evidence is real and the synthetic evaluator is correct.

v0.19 introduces a typed intermediate record:

`source_evidence_ids → human-reviewed requirement_hypothesis → requirement_type → feature_id → KPI template → acceptance_test_ids → test_target → execution evidence → proof boundary`.

The trace is saved as `00c_requirement_trace.json` and `08e_requirement_trace.json`, with a Markdown explanation and raw source pointers. Type mismatch, ambiguous mixed-feature or underspecified requirements fail with HTTP 422 **before 01 runs**. The human reviewer, not the LLM, explicitly chooses the template.

## Bounded templates

| Human-selected template | Acceptance test target | Pinned metrics | Interpretation |
|---|---|---|---|
| `claims_assignment` | Generated R1 code executed in E2B | missed including unassigned, equal hours, deadline priority, scarce qualifications, four stress cases | Synthetic claims-assignment evaluation only; KPI and behavioral checks are separate |
| `claim_progress_updates` | `app.notification_demo.prototype_notifications`, a standalone deterministic example | notification coverage, max synthetic delay, correct recipient/status, negative controls | A separate synthetic notification prototype, **not** the generated R1, not a production component |

For the notification type, `08c_grounded_kpi_verification.json` explicitly reports `NOT_APPLICABLE_TO_NOTIFICATION`. `08d_notification_prototype.json` holds the reference prototype, synthetic fixture, oracle checks, failed negative controls and thresholds. `08e_requirement_trace.json` reports `SYNTHETIC_PROTOTYPE_ONLY` if the example passes; **Customer acceptance stays false and production NO_GO regardless**. The fixed claims R0/R1 execution remains as an independent *technical regression*, not proof of the notification requirement.

Unknown requirements are rejected rather than converted into mutable Python evaluation programs. A single hypothesis mixing notification and assignment must be split into separate, reviewed requirements. The web UI exposes the template and type-specific threshold controls.

## Changed R1 development→selection→holdout logic

Prior versions selected an R1 candidate after checking only DEV capacity and deadline-hour metrics, then learned about scarce qualifications and stress regressions after selection. v0.19 checks **in DEV for each attempt**:

1. Three fixed DEV seeds: independently valid capacity/qualification results, same planned hours per seed, **no worse FIFO per seed** and improved on at least one seed.
2. `deadline_risk_probe` and `scarce_qualification_probe` (fixed, deterministic).
3. Four fixed DEV stress cases: constraints remain valid; no missed/unassigned regression against the deterministic deadline *heuristic*. This heuristic is not globally optimal.
4. Any failure sends the full DEV-only failure codes, probe results and stress comparison back into the next Qwen repair prompt, up to the existing two repairs.
5. Only a candidate passing **all** gates may be selected. If none passes, `selection_status = HOLD_NO_ELIGIBLE_CANDIDATE` and **HOLDOUT is not executed**. This is a correct negative result, not a missing-data success.
6. Only after an eligible selection are two untouched HOLDOUT seeds executed **once**; results are never fed into Qwen. `dev_selection_audit.json` stores all attempts, source hashes, rejections and the no-leakage flag.

This increases DEV E2B work (the behavioral and stress fixtures run for every repair attempt). The post-selection `08b` reruns the **same pinned behavioral and stress fixtures**, so **it is a reproducibility check, not an independent statistical holdout**. Only the separate generated case HOLDOUT seeds are untouched.

## Report semantics

`business_assessment.py` explicitly distinguishes:

- `NOT_EXECUTED`: no selected code or untouched HOLDOUT evaluation.
- `EXECUTED_FAILED_KPI`: comparable HOLDOUT exists but R1 misses the improvement requirement.
- `EXECUTED_FAILED_CONSTRAINTS`: an executed output violated reviewer assignment constraints.
- `VALIDATION_HOLD`: the KPI was measured but another audit/integrity gate is missing.
- `SUPPORTED_SYNTHETIC`: bounded technical evidence only.
- `UNVERIFIED`: customer need, revenue, ROI, data governance, integration and production.

`execution_outcome` is also recorded in `assessment.json`/`report.md`. A completed export ZIP only means **all expected stages were processed and archived**, not that any criterion passed. Notification trace status is appended to the business report without changing the separate claims R1 benchmark decision into a notification PASS.

## Main audit files

```text
workflows/<workflow_id>/
  00_evidence_grounded_requirements.json
  00_source_manifest.json
  00_raw_source__*.html
  00b_human_evidence_review.json
  00c_grounded_test_contract.json
  00c_requirement_trace.json
  00c_requirement_trace.md
  00c_technical_spec.md
  01_input.json
  ...
  08c_grounded_kpi_verification.json
  08d_notification_prototype.json         # only for notifications
  08e_requirement_trace.json
  08e_requirement_trace.md
  workflow.json
experiments/<experiment_id>/
  attempt_*.json
  attempt_*.py
  dev_selection_audit.json
  experiment.json
  selected_r1.py                        # only if DEV-eligible candidate exists
  ...
assessments/<assessment_id>/assessment.json
manifest.json                            # SHA256 for included artifacts
```

Public datasets can still be fetched separately from step 00. Cached source SHA256 is verified before reuse; failures never silently switch to simulated evidence. For offline testing, the suite uses mocks for E2B, LLM and public HTTPS downloads, and is **not** a live service integration test.

## Running tests and launching

```bash
PYTHONPATH=backend python -m pytest backend/tests -q
bash scripts/setup-env.sh
# Set E2B_API_KEY in .env; run Ollama models as documented in README
# macOS:
docker compose up --build
```

Check the v0.19 documentation and the per-stage audit results before accepting an R1 candidate. Actual RAG corpus retrieval, E2B and Ollama require the corresponding external services.
