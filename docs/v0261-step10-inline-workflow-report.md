# v0.26.1 — Step 10 at the top and inline workflow report

## UI order

- The manual source/evidence panel **00** remains first.
- **10** is immediately after **00** and before **01**, so the one-click workflow is visible at the top. The 10 controls share state with 01, 04, 06 and 08.
- The overview guide shows `00 → 10 → 01–09` in exactly that order.
- The operator must still approve public evidence at 00b and the R1 change at 05; no automatic approvals.

## Report lifecycle

`GET /api/full-run/{workflow_id}/report` is read-only and returns HTTP 409 until `COMPLETE` or `PARTIAL`. UI automatically fetches it on the transition to a terminal state, and when a saved Workflow ID is loaded. The UI guards against showing an older run's report.

The response is assembled from persisted `workflow.json`, `assessment.json`, `benchmark.json`, and `05_dogwood_authorization.json`. The report includes source references, stage counts, exact diagnosis execution/quality, requirement trace, business assessment with criteria and next actions, and observed synthetic metrics. If an assessment does not exist (e.g. an earlier failure), the response sets `business_assessment=null`; the UI reports `09 未評価` instead of showing GO. Where IDs exist but conflict, the endpoint returns HTTP 409 instead of mixing evidence across runs.

The report is informational and **does not** restart an LLM, sandbox, evaluator, Dogwood, approval, or any background task. Historical ZIP and business-assessment Markdown endpoints are preserved. The UI is intended for trusted local demos, not untrusted multi-tenant deployment.

## Regression checks

- `PYTHONPATH=backend python -m pytest -q backend/tests`: 142 passed.
- TSX parses without diagnostics; section order is `00 → 10 → 01 → ... → 09`.
- Existing v0.26 audit ZIP (18 stages) returns `status=COMPLETE`, `stage_counts.completed=18`, `authorization_status=ALLOW`, `diagnostic.quality_status=HOLD_HUMAN_ADJUDICATION`, and business production status `NO_GO`.
- Frontend's complete dependency build and Rust/Docker build require a machine with dependencies/network and remain unverified in this packaging environment.
