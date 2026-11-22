# v0.28 — DEV Robustness / Independent Diagnosis Axes / Latest Snapshot

This release changes the *pre-HOLDOUT selection* for R1, without changing the
fixed R1 requirements, Dogwood authorization policy, E2B evaluator, or 08f
post-selection randomized oracle. It also adds diagnostic axis reporting and
a canonical report source after retry.

## 1. DEV selection — new bounded robustness tie break

The immutable selection gate remains the first screen: valid claims allocation,
equal assigned hours, DEV FIFO improvement, both behavioral probes, and four
synthetic stress scenarios with no regression versus the pinned heuristic.

For eligible candidates, v0.28 evaluates **two predetermined and separate DEV cohorts**:

- Four additional, fixed **DEV distribution-shift** datasets (skill scarcity,
  reviewer capacity, deadlines, arrival order), with seeds `920000..920003`.
  They are materialized from a fixed generator before candidate selection and
  evaluated independently in E2B using the ordinary unmodified evaluator.
- The four existing pinned DEV stress scenarios, seeds `910000..910003`.
  Those remain mandatory eligibility gates; they are not replaced by the new
  DEV distribution-shift cohort.

The declared selection order, computed **before** 06 HOLDOUT, is:

1. Ordinary DEV missed deadlines, ascending.
2. Ordinary DEV unassigned cases, ascending.
3. **New extra DEV cohort:** maximum missed deadlines, then total missed,
   then total unassigned, ascending.
4. **Original four pinned stress scenarios:** maximum missed deadlines, then
   total missed, then total unassigned, ascending.
5. Stable source order, only when all comparable DEV scores tie.

Each cohort is compared across candidates **only if every eligible candidate**
has a complete, aligned cohort. A missing cohort is excluded from ranking for
**all** candidates rather than rewarding missing measurements; incompleteness
is reported and requires review. The eligibility gate remains unchanged.

`dev_robustness_preselection.json` stores the cohort seeds, per-candidate
metrics, score tuples, rank, selection status, and uncertainty **before**
HOLDOUT. `dev_selection_rationale.json` independently cross-checks selection.
`leave_one_extra_dev_out` and `leave_one_stress_out` repeat the ranking with
one fixture omitted to flag winner instability. Unresolved ties and incomplete
comparability are explicitly shown instead of being called robust successes.
These are **deterministic synthetic sensitivity checks, not statistical
confidence intervals, population draws, or proven generalization**. Additional
E2B candidate runs increase resource cost and latency.

**No leakage:** neither 06 HOLDOUT, 08f, nor any CP-SAT exact solution is used
for this selection or in LLM repair prompts. The independent post-selection
08f file remains observational and cannot change the selected R1.

## 2. Six independent RAW diagnostic axes

`diagnostic_axes.json` contains per-model, per-case-family counts for:

| Axis | Independent rubric fields |
|---|---|
| Cause classification | `cause_classification` |
| Implementation correctness | `implementation_correctness`, `no_implementation_contradiction` |
| Evidence quality | `evidence_traceability`, `real_world_humility` |
| Revision action | `revision_targets_requirement`, `no_conflicting_revision_policy` |
| Requirement fit | `synthetic_business_fit` |
| Cross-field consistency | `raw_consistency.passed`, `raw_semantics.passed` |

Each axis reports its own PASS/HOLD/NOT_EVALUATED, completed and planned counts,
and the case IDs of failed checks where applicable. An otherwise correct cause
classification **does not** imply that an action is acceptable. First RAW and
latest RAW on fixed cases are separated; repaired answers are never silently
promoted into first-pass success. Blind retries are flagged as **not fresh**.

All rubric checks are from the existing independent synthetic scorer, with
its unchanged hidden oracle. No oracle-derived labels reach the model prompts,
DEV selector, or runtime Dogwood policy. The lexical consistency checker can
miss or falsely flag nuanced semantics; this is not proof of legal or customer
requirements.

## 3. Canonical latest benchmark after replay

`benchmarks/<benchmark-id>/benchmark.json` is the current state, including
`retry_history`, and `benchmarks/<id>/diagnostic_axes.json` is a *derived*
summary of that current state. `08_latest_state_index.json` in the workflow
folder points to it with current quality/execution, retry count, and update
UTC. During selective retry, previous attempts stay append-only, while the
**derived** index and axes are atomically refreshed. Old retry snapshots and
previously exported PARTIAL ZIPs remain historical evidence.

The read-only report API obtains the latest benchmark by linked ID; it reports
whether workflow status and current-index status agree, and warns explicitly
on disagreement. It never recomputes LLM or E2B executions. The report
schema stays `report_version=0.27.0` for backward compatibility, while
`producer_version=0.28.0` identifies the application release. The audit ZIP
format similarly remains `AUDIT-EXPORT-v0.25.0`.

## 4. UI and reproducibility

Preserved order: **10 → 10R finished report → 00 → 01..09**. Step 10 report adds
DEV robustness/selection uncertainty, six diagnosis axes, and the canonical
latest/retry source index. Old v0.27 data still loads; unavailable new fields
are labeled NOT_RUN/legacy, not PASS.

For a fresh build:

```bash
# Backup .env and artifacts/ first
# Optional: enable actual CP-SAT comparison in 08f via build arg, per compose settings
docker compose build --no-cache api web
docker compose up -d --force-recreate
```

Validation: Python pytest regression, TSX syntax AST and top-level layout
checks are run when packaging. A full Vite dependency build, Docker/Rust build,
actual E2B and Ollama calls require the end user's environment and are not
claimed as verified by this source release.

The whole sample remains synthetic unless explicitly using supported public
context evidence (which still does not establish real client needs).
No production/legal/security authorization is established. Existing Dogwood
and feature-acceptance logic are unchanged.
