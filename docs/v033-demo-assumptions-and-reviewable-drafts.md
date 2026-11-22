# v0.33 — Demo assumptions and reviewable 10R proposals

## Goal

10R first presents a provisional presales proposal (where an LLM delivered a structurally valid draft) and **then** the independent 00–09 evidence and assessment report. The target is an iterative PM/engineer review, **not** automatic acceptance of the model's proposal. Screen order remains **10 → 10R (proposal → findings) → 00 → 01–09**.

## Unverified starter scenario

The UI and the `AdvisoryConstraints` API defaults use the same **unconfirmed demo scenario**:

| Parameter | Demo value | Meaning |
| --- | --- | --- |
| Project budget | €30,000 | hypothetical spending ceiling, **not** quoted development cost |
| Engineering team | 2 people | hypothetical delivery staffing, excluding part-time PM |
| PM allocation | 0.2 FTE | hypothetical weekly PM allocation |
| Delivery horizon | 8 weeks | hypothetical target, not agreed deadline |
| Engineering scope | Existing system / APIs first | cost-conscious hypothetical scope |
| Operations | No dedicated operations engineer; low ops load | hypothetical support model |

The input controls show these values and identify them as **demo assumptions**, not customer facts. The backend supplies the same values for `POST /api/full-run/{workflow_id}/advisory` with `"constraints":{}` or omitted constraints. An **explicit** JSON `null` means unknown; it is not silently replaced with a demo number. The `assumptions_origin` map marks unchanged defaults `DEMO_PLACEHOLDER_UNVERIFIED` and changed values `USER_EDIT_UNVERIFIED`; **neither is customer confirmed**. Users can clear fields and manually regenerate. No automatic deployment or re-running 00–09 is triggered.

## Project budget vs. cost estimate

Budget input is not a verified vendor quote and does not logically prevent the LLM from estimating the project cost. For example, an option can say `仮の単価€2,000/週 × 8週 = €16,000 の概算（要見積）`. This is displayed as **AI概算・費用仮説（確定見積ではない）**, with `UNVERIFIED_COST_ESTIMATE` annotation. Neither the presence of a currency symbol nor an unknown customer budget is a reason to discard an otherwise viewable draft. Independently verifying estimation assumptions and contractual price remains human work.

## Status and evaluation separation

- `DRAFT_UNAPPROVED`: structurally valid draft; no outstanding *detected* semantic contract violations. **Not** customer-approved or production-ready.
- `DRAFT_WITH_WARNINGS`: structurally valid draft after a bounded repair attempt, but one or more semantic contract warnings remain. Show **all three options and individual warning labels**, preserve the model-generated text, and allow human feedback for a future iteration. This is **not** a PASS or approved recommendation.
- `GENERATION_FAILED`: no structurally valid model draft was obtained, e.g. Ollama unavailable / JSON schema validation failed. The UI still shows the starter scenario and **the existing independent evaluation report**; do not fabricate an AI proposal.
- `STALE_ADVISORY`: canonical source changed; a previous draft (including one with warnings) cannot be reviewed as current.

When semantic inconsistencies are found, the existing *one bounded repair attempt* now targets each invalid option separately (or a single invalid scalar/list item) rather than regenerating all three alternatives. A failed repair **keeps the original typed item**, records the attempt status, and retains a visible `contract_issues` map. This is a draft presentation policy, **not fail-open for execution authorization**. Dogwood, constraint enforcement, approvals, CP-SAT/DEV/HOLDOUT, and 09 production decision remain unchanged.

## Audit/API

Each `10p_advisory_vNNNN.json` contains `constraints`, `assumptions_origin`, `scenario_basis`, `contract_issues`, `estimate_notices`, `repair_actions`, `approval_status=NOT_APPROVED`, and the canonical source hash. `10p_review_vNNNN.json` saves human feedback, including warning count and `not_production_approval=true`, without triggering another run. Review accepts current `DRAFT_WITH_WARNINGS` for **feedback only**, not for changing authorization. The audit ZIP retains all versions, the source SHA-256 and reviews; its existing format remains `AUDIT-EXPORT-v0.25.0` with producer `0.33.0`.

## Verifications and limitations

- Python regressions: **184 passed**, including five v0.33-specific tests with mocked LLM responses.
- TypeScript/TSX syntax and AST-based UI order check: passed using global TypeScript.
- Complete Vite build: **not verified** because `react` / React type dependencies are unavailable offline.
- Native Rust, Docker, real Qwen/Ollama and E2B: **not executed** in the packaging environment.
- Semantic keyword checks are heuristics, not proof that a proposal satisfies a real customer request. Real clients, cost estimates, GDPR/regulatory requirements, and operational readiness need independent validation.
