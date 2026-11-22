# v0.27 — Feature contracts, diagnostic semantics, independent selection review, Dogwood denial audits

This release builds on v0.26.1, **preserving step 10 directly after step 00** and the inline read-only workflow report. It is a synthetic research demonstration, not a production certification.

## 1. Feature-specific typed acceptance (08e)

`app.requirement_trace.TEMPLATES` determines the allowed mapping of a human-reviewed requirement to a feature, KPI, test target, evaluator, and exactly four acceptance-test IDs. `app.feature_acceptance.assess` validates the binding and compares acceptance evidence to the selected feature. Evidence and feature scope are not interchangeable.

- `claim_progress_updates` requires `NOTIFY-ON-STATUS-CHANGE`, `NOTIFY-WITHIN-THRESHOLD`, `NOTIFY-CORRECT-RECIPIENT` and `NEGATIVE-CONTROL-NO-UPDATE`. A deterministic notification prototype is re-evaluated, including wrong-recipient and missing-notice negative controls. R1 reviewer assignment KPIs cannot satisfy these tests.
- `claims_assignment` requires `HOLDOUT-MISSED-DEADLINES`, `PROBE-DEADLINE-RISK`, `PROBE-SCARCE-QUALIFICATION`, `STRESS-REGRESSION`; the policy-validation experiment linkage and selected-code hash are checked.
- The independent attestation is saved as `08e_feature_acceptance.json`. `08e_requirement_trace.json` and the inline report refer to it. The acceptance covers **only a fixed synthetic feature fixture**. The notification prototype is not integrated with any real customer system. The published public source does not establish the cause of a customer's delay or acceptance of an SLA.
- Public notification runs can complete workflow execution but preserve `HOLD_NOTIFICATION_NOT_INTEGRATED` and `NO_GO` for production.

## 2. Diagnostic semantic-boundary checks (08)

`app.diagnostic_semantics.assess` checks **raw**, unassisted diagnostic answers for inconsistencies across: classification, stated cause, independent implementation test visible to the model, cited evidence ID, desired requirement revision, and precedence semantics. A `raw_semantics` record accompanies applicable fixed and fresh-blind trials. The reliability gate records `*_SEMANTIC_BOUNDARY_INCONSISTENCY` where present. It does not consult the hidden benchmark oracle, repair the model response, or count an assisted correction as a RAW pass. These are conservative typed/lexical checks; natural-language truth is not formally proved.

## 3. DEV-only selection and 08f post-selection gap analysis

`app.dev_selection_audit` records the eligibility result and predeclared lexicographic ranking: minimize DEV missed deadlines, then DEV unassigned cases, then stable candidate order. The chosen candidate's identity and source hash are frozen **before** holdout and 08f randomized cases. If no candidate passes the gate, the selection remains HOLD.

`app.selection_gap_analysis` compares the **already selected** R1 to alternatives using aligned input SHA-256 and oracle-certified 08f cases, reports relative losses and uncertified comparisons, and requests review as appropriate. `08f_selection_gap_analysis.json` explicitly sets `change_selected_engine=false`, `fed_back_to_dev_selection=false`, `fed_back_to_model=false`. This is independent evaluation, not optimization leakage or proof of population-level optimality. CP-SAT remains optional (`INSTALL_SOLVER=1`) for 08f; a Python exact-search fallback is possible, and neither is automatically promoted to the R1 runtime strategy.

## 4. Dogwood negative-path evidence (08g)

`app.dogwood_negative_audit.run` executes six synthetic cases through the compiled Rust Dogwood CLI **when the real binary is available**: missing approval, mismatched workflow ID, mismatched proposal ID, mismatched approval ID, revoked approval, and a valid-approval ALLOW control. It separately checks expired-approval DENY at the Python timestamp boundary and detects a tampered approval snapshot against a detached SQLite ledger. The original live ledger is not modified by this audit. The resulting `08g_dogwood_negative_audit.json` includes expected/actual verdicts, status and scope. `NOT_EXECUTED_NATIVE` is never treated as PASS. A Docker Rust builder now runs `cargo test --release --quiet` and copies a SHA-auditable test log into the image at `/opt/dogwood-rust-tests.log`, where available. The `08g_boundary_assurance.json` contains a short summary.

**Trust boundary:** Dogwood uses a validated, persisted local approval event replay into an ephemeral store per authorization call. These tests do not authenticate the claimed human actor, establish a continuously running authorization service, prove compliance with law or guarantee whole-system safety. A failed authorization still rejects R1. Native Rust/Docker compilation is *not* verified by the offline Python test suite.

## Execution and evidence

From the unpacked project root, keep your `.env` and existing `artifacts/` outside any replacement/copy operation. Then:

```sh
docker compose build --no-cache api web
docker compose up -d --force-recreate
```

The four new report sections are present in the read-only `GET /api/full-run/{workflow_id}/report` API and UI step 10 when the relevant stage executed. Download the full-run ZIP to inspect `08e_feature_acceptance.json`, `08f_selection_gap_analysis.json`, `08g_dogwood_negative_audit.json`, and model trial `raw_semantics`. If you need actual Rust denial-test results, verify the Docker builder output and the `rust_build_test_log` status field; a Python-mocked unit test cannot substitute for native authorization testing.

The manifest retains `format_version=AUDIT-EXPORT-v0.25.0` to avoid breaking consumers of the existing export layout, while adding `producer_version=0.27.0` to identify this application's producing version.

## Packaging validation

- Python regression tests: **152 passed**, including simulated full workflows and public-evidence notification acceptance.
- Frontend TSX syntax parser: **passed**; complete Vite/React build **not run** without frontend node_modules.
- Actual Docker + Cargo build: **not run in the packaging environment**; will execute on a supported developer machine.
- Actual external Ollama/E2B/public-source networking: **not executed** in the regression tests. Verification results are limited to mocked interfaces and synthetic fixtures.
