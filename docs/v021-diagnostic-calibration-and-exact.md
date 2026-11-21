# v0.21 — Diagnostic calibration + post-selection exact comparisons

## What changed

v0.21 extends v0.20 without altering the fixed evaluator in `app/diagnostic_quality.py` or the established DEV and HOLDOUT candidate-selection rules. Its goal is **better LLM diagnostic reasoning**, **not a fabricated PASS**. Do not interpret this prototype as real-customer or regulatory validation.

### (A) Diagnosis: first answer → transparent model revision → fresh unseen cases

At step 04 (`/api/propose`, optional `enable_repair`) each model runs independently on the same R0 DEV evidence. If the existing deterministic rubric fails, each model is **asked once to reconsider its own answer**. Revision feedback contains only source-observable facts: independent R0 implementation PASS, the available synthetic evidence ID, and whether a FIFO/deadline explanation contradicts itself. The other model's answer, benchmark oracle, and all R1 HOLDOUT samples remain undisclosed. The app stores initial JSON, original rubric, revised JSON, final rubric, public feedback, and errors separately. Each model may remain HOLD; approval still requires explicit human action and an audited override if ODA does not pass.

At step 08 (`/api/diagnostic-benchmark/run`, optional `enable_repair`) the same 8-item frozen rubric is run over the selected synthetic fixtures. Initial predictions and scores remain immutable, even if a second inference passes. The prompt is domain-neutral and follows a published decision protocol rather than any case's expected label. Revision sees the original input and its own prediction, plus input-only consistency notes, never oracle labels. When `blind_generalization=true`, **two newly seeded synthetic cases** are evaluated *first-pass only*; neither is revised, and their outcomes never affect prompt engineering or R1 selection. `summary.initial_passed`, `summary.passed` and `blind_generalization.summary` are three **different** metrics.

**PASS conditions**: Existing deterministic rubric passes all 8 checks. For an end-to-end business-assessment diagnostic-control gate, both Qwen and ODA must pass the proposal rubric and all selected benchmark runs; if fresh blind trials are enabled, those must pass as well. Both model results remain separately visible. There is no guarantee a local model will pass. A result only certifies this finite synthetic rubric, not actual reasoning reliability.

A model may learn to reproduce the public protocol; this makes extra, untouched cases particularly important. The default four-case synthetic benchmark is insufficient to estimate population-level generalization.

### (B) Independent randomized behavioral HOLDOUT

At step 08f (after DEV selection and the existing fixed HOLDOUT) the app generates a new random root seed using the OS CSPRNG. It produces between 2 and 8 additional small synthetic scheduling problems, each 5–6 claims, 3 reviewers, 2 days, varying skills, capacity, arrival order, durations and deadlines. These data are **not** available to model generation, repair, DEV gating, source selection, or the old R0→R1 comparison. Randomized is not the same as representative of actual insurance queues.

Every selected candidate and the two Domain Skill strategies are executed in isolated E2B sandboxes; FIFO and deterministic deadline reference are included as baselines. The exact baseline is calculated independently of the Skills. Raw E2B records, seeds, inputs, sources, exact outputs, per-case validity and objective gaps are saved under `workflows/<id>/08f_*`.

**Optimization contract:** maximize number of cases served on or before deadline; subject to that, maximize total assigned cases. The source domain evaluator independently enforces all skill/duration/day/capacity/uniqueness constraints. An unassigned case counts as a missed deadline. The exact optimum compares *missed-case count*; it does not optimize real financial, fairness or operational utility.

**OR-Tools CP-SAT** is optional. The default installation requires no additional dependency and uses exhaustive branch-and-bound on at most 7 cases. The exact certificate must have `status=OPTIMAL`. `FEASIBLE`, `TIME_LIMIT`, `UNKNOWN`, or `SKIPPED_SIZE_LIMIT` **cannot** be used to assert a proven optimality gap. If OR-Tools is installed, CP-SAT is preferred and the solver's `OPTIMAL`/`FEASIBLE` status is preserved. No model or Skill can rewrite the independent scorer.

To opt into CP-SAT in Docker, edit `.env` to set:

```dotenv
INSTALL_SOLVER=1
```

Then rebuild: `docker compose build --no-cache api && docker compose up`. This installs `backend/requirements-solver.txt` in the API container. The default (`INSTALL_SOLVER=0`) is deterministic exhaustive enumeration for the small blind cases. The `ortools` package cannot be installed in the artifact-generation environment, so no real CP-SAT results are claimed for this build; fallback exact enumeration was executed in tests.

**Leakage control:** The blind inputs are sampled only *after* the candidate has been selected. If 08f fails or times out, the workflow reports FAILED and exports a PARTIAL ZIP; there is no silent synthetic success. Full reproducibility requires the recorded root seed, dataset snapshots, reviewed algorithm sources and compatible solver library/version. CP-SAT run time and E2B utilization depend on the user's setup; LLM token counts are not yet measured.

### (C) Separate decision semantics

- A Skill win is not a Qwen code-generation win.
- A prompted or revised diagnosis PASS is not the same as an initial PASS.
- A seeded blind score is independent of DEV tuning but not evidence of production generalization.
- An exact optimality certificate applies only to the stated discrete objective and dataset.
- RAG citations validate source links, not requirement truth, root cause, or a customer's authorization.
- The separate notification prototype remains synthetic, not integrated with a claims processing system.
- No operational GO is granted: production stays NO-GO until security, performance, data privacy and real-customer validation.

## Audit file map

| File | Contents |
|---|---|
| `proposals/<id>/qwen_diagnosis.json`, `oda_diagnosis.json` | Initial inference, never overwritten |
| `proposals/<id>/diagnostic_initial_scores.json` | Frozen initial rubric |
| `proposals/<id>/diagnostic_repair_audit.json` | Input-only critique and actual second inference |
| `proposals/<id>/qwen_diagnosis_final.json`, `oda_diagnosis_final.json` | Revised or original final inference when enabled |
| `benchmarks/<id>/benchmark.json` | Initial and revised scores by model and trial |
| `benchmarks/<id>/blind_cases.json` | Seeded independent diagnostic challenge cases/oracles for post-score audit |
| `benchmarks/<id>/blind_*.json` | First inference on each new case, no revision |
| `workflows/<id>/08f_blind_optimality.json` | Selected engine, status by solver, per-engine blind results |
| `workflows/<id>/08f_dataset_*.json` | Original randomized test inputs |
| `workflows/<id>/08f_exact_*.json` | Exact solver status, objective, schedule and validity |
| `workflows/<id>/08f_raw_*.json` | Raw sandbox responses including execution time and source hashes |

The bundled source ZIP contains no real public dataset bytes; as in v0.20, the app downloads source documents itself when public-evidence mode is selected, preserving their provenance. The run-export ZIP contains source documents when actually fetched.
