# v0.22 — R1 Artifact Readiness & Dependency-Safe Audit Pipeline

## Root cause

The previous `full_run.second_half()` catches an exception at stage 06 and may recover `experiment_id` from an `approvals/<approval_id>/evaluation_started.json` marker. This marker proves **only that the evaluation was launched**. It does not prove `experiments/<experiment_id>/experiment.json` was created. Stage 08b then used to call `m.load(..., "experiment.json")` **outside** its try/except, causing a secondary `HTTPException: Artifact not found`, which overshadowed the upstream 06 failure.

## v0.22 behavior

- The shared, **read-only** `backend/app/artifact_readiness.py` validates a canonical experiment UUID, directory and `experiment.json` presence, parseability, required chain IDs, the explicit failure status, `selected_r1.py` existence and SHA256, and the recorded HOLDOUT completion.
- `READY`: complete R1 artifact + selected-source hash verified + HOLDOUT executed. Post-selection 08b/08f may run.
- `NO_SELECTED_R1`: experiment completed but no eligible code was selected. Do **not** run 08b or 08f; allow the deterministic 09 rubric to report HOLD when it can use a complete record.
- `STARTED_ONLY`, `FAILED`, `INCOMPLETE_RESULT`, `CORRUPT_RESULT`, `ID_MISMATCH`, `SELECTED_CODE_MISSING`, or `SELECTED_CODE_HASH_MISMATCH`: downstream dependencies are **SKIPPED**, never treated as successful verification.
- Stage 06 preserves the **original exception** in `workflows/<workflow_id>/06_r1_failure.json` and the Workflow's `error` field. If an experiment directory exists, the linked experiment ID and its partial files remain in the ZIP; no missing `experiment.json` is synthesized as a success.
- Stage 08b records `08b_experiment_dependency.json` and `08b_policy_skip.json` rather than raising a second HTTP 404. Failure inside policy validation (where a complete R1 exists) remains `FAILED`, with a separate `08b_policy_failure.json`.
- Stage 08c, in public **assignment** mode, emits a `HOLD_UPSTREAM_R1_INCOMPLETE` record rather than running the KPI verifier on missing R1 data. **Notification** requirements remain independent and use their own synthetic prototype; that does not repair R1.
- Stage 08f does not generate blind seeds or open E2B Sandboxes when the selected R1 is missing or its code hash mismatches. Its JSON explicitly states that nothing was executed.
- Stage 09 does not attempt the business assessment without a complete R1 artifact. It writes `09_assessment_skip.json` and makes no production/GO assertion.
- The ZIP manifest uses `AUDIT-EXPORT-v0.22.0`, lists SKIPPED/FAILED steps, remains **PARTIAL** whenever a required stage was skipped or failed, and preserves the reason and original upstream event. The user interface also highlights PARTIAL independently of individual stage labels.

## Example: inspect a PARTIAL run on Mac

```bash
WID=<the Workflow UUID shown on screen>
cat "artifacts/workflows/$WID/06_r1_failure.json"
cat "artifacts/workflows/$WID/08b_experiment_dependency.json"
cat "artifacts/workflows/$WID/08b_policy_skip.json"
cat "artifacts/workflows/$WID/09_assessment_skip.json"
cat "artifacts/workflows/$WID/workflow.json"
```

If `experiment.json` is absent, look at the linked `artifacts/experiments/<experiment_id>/started.json`, `error.json`, and any `dev_*` / E2B raw logs available. The root cause could be E2B transport or execution failure, LLM generation, an artifact write failure, or an unexpected exception. The wrapper cannot repair those failures automatically. **Do not relabel an incomplete experiment as successful.**

## Test coverage

- Regression: a stage-06 exception after writing `evaluation_started.json` and `started.json`, but before writing `experiment.json`.
- Regression: a failure-only experiment record (both `error.json` and terminal `experiment.json` have FAILED status).
- Validation: corrupted JSON, invalid UUID, omitted code, tampered `selected_r1.py`, valid selected source, and no eligible R1.
- Integration: failure origin persists, 08 benchmark can finish independently, 08b/08f/09 are SKIPPED, PARTIAL ZIP is downloadable, and each archived file matches its SHA256 manifest entry.

## Limitations

This patch provides **failure isolation, traceability, and accurate stage status**, not root-cause remediation or an automatic resume mechanism for the same Workflow ID. A NEW explicit run is needed after correcting a failed model/E2B dependency. No actual Ollama, E2B or public dataset network run was performed during packaged tests. The application is a synthetic demo and not a production multi-tenant audit system.
