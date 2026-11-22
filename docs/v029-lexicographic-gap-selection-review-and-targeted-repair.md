# v0.29 — Lexicographic Objective, DEV Discrimination, and Targeted Diagnostic Repair

## Scope and precedence

This is a source-level extension of v0.28 and the UI ordering established by
v0.27.1. It preserves **10 → 10R report → 00 → 01..09**, the human
approval boundary at step 05, Dogwood's Rust-backed authorization, and all
feature-specific notification acceptance checks. No production permission is
implied by a synthetic PASS.

### 1. Certified 08f optimality uses the complete declared objective

For the claims scheduling benchmark, the **predeclared** objective is
lexicographic minimization of

1. `missed_deadlines` (includes unassigned cases), followed by
2. `unassigned_cases` when the primary score ties,

subject to independent qualification, daily capacity, duration, and
one-assignment-per-claim constraints. CP-SAT's `(n+1)*on_time + assigned`
maximization is equivalent on a fixed set of `n` cases. Small-case exhaustive
search uses `(on_time, assigned)` tuples. **Only `OPTIMAL`** is a certificate;
`FEASIBLE`, `TIME_LIMIT`, missing, or invalid candidate outputs are not.

The post-selection audit now includes:

- `optimality_gap_missed_cases` — previous primary-only field (retained for
  backwards compatibility).
- `optimality_gap_unassigned_conditional` — secondary gap **only when the
  primary objective equals the certified oracle optimum**.
- `lexicographic_optimal` — true only when both gaps are zero and the
  independent validator says the candidate is valid.
- `primary_ties_secondary_losses` and `primary_ties_secondary_wins` per
  alternative, where the primary score ties but unassigned differs.
- `selected_oracle_gap_cases`, separate from a **relative** candidate gap.

Results for 08f never feed back into DEV selection, model repair, or R1 source
selection. The 08f data and exact solver are post-selection only.

An offline compatibility check on the *previous v0.28 archived execution*
reclassifies its `skill_deadline_scarcity` selection as
`POST_SELECTION_GAP_DETECTED`: the `skill_bounded_beam` comparator has one
case with the same missed deadlines but fewer unassigned cases. Historical
records remain unchanged. Old archives missing secondary oracle gaps remain
uncertified as to *absolute* lexicographic optimality.

### 2. DEV ties are research-only, never a human review

The DEV rank order and optional extra DEV scenarios are unchanged. When two
candidates tie, the original deterministic source order still yields a
**research execution candidate**, so the synthetic experiment can complete.

New `selection_review` fields declare whether human review is required,
whether any review occurred, and that `production_selection_authorized=false`.
A tie is `PROVISIONAL_RESEARCH_SELECTION_REVIEW_REQUIRED`. This is **not**
a hidden human approval and does not replace step 05 approval, customer
acceptance, or any production authorization. This release does not provide
an additional authenticated reviewer approval endpoint for production.

### 3. How discriminative are the DEV cases?

`dev_case_discrimination.json` records per-case candidate objective pairs,
lexicographic case winners, and whether each DEV case actually separates
eligible candidates. The three cohorts are original DEV, four extra DEV
fixtures, and four stress scenarios. A scenario where all candidates have
identical objective pairs is explicitly **non-discriminative**; leaving it
out without changing a fixed-order winner does not establish generalization.

If none of the comparable cases separates candidates, the audit says
`NO_SEPARATING_CASES`. It does not manufacture a discriminating case nor
leak any of the 08f/06 HOLDOUT fixtures into DEV. Case counts are an
engineering sensitivity analysis, not confidence intervals or evidence of
population-level performance.

### 4. Targeted diagnostic repair, no oracle-based repair routing

Fixed diagnostic trials can opt into a second model call if their unaltered
RAW answer conflicts with public input facts. The planner inspects the
independent input PASS/FAIL statement, visible evidence IDs, and cross-field
rules. It selects an allowlist of fields that may be reconsidered. The model
must return a schema-compatible JSON; the harness **adopts only these fields**
and discards all other proposed changes. First RAW responses and the original
rubric remain separately preserved.

Most importantly, the **hidden synthetic fixture oracle is not used even to
trigger a repair**. No hidden label or rubric failure is passed to the model.
If no input-observable contradiction exists, an oracle-scored wrong answer
still remains an unmodified failure. A safe missing-evidence-ID binding can
avoid a redundant second inference, but its assistance is never reported as
RAW success. Blind trials never receive critiques, revisions, or retraining
feedback; a blind retry is a replay, not new independent evidence.

`targeted_repair_summary.json`, individual `trial_*.json` records, and the
10R inline report expose the repair plan, revised fields, discarded model
edits, and first-pass-vs-revised evaluation. This is input-consistency
triage, **not** a formal proof of natural language or real customer truth.

## Unchanged guarantees and limitations

- Dogwood's existing refusal tests, event journal, and research-only
  authentication caveats remain unchanged.
- Notification acceptance and allocation KPI acceptance remain distinct.
- The audit ZIP schema remains `AUDIT-EXPORT-v0.25.0` and the report view
  contract remains `report_version=0.27.0`; the producer version is `0.29.0`.
- Only the installed Python unit/integration regression tests and global
  TypeScript parser/layout checks ran in this build environment. There is no
  claim of a full Docker/Rust native build, Vite install/build, actual Mac
  Ollama inference or an E2B/CP-SAT end-to-end run in this environment.

## Run

Back up `.env` and `artifacts/`; copy the source snapshot over your previous
source (do not overwrite the old audit archives). Then:

```bash
docker compose build --no-cache api web
docker compose up -d --force-recreate
```

The optional OR-Tools CP-SAT dependency must be enabled in the backend build
configuration as described in the existing README/compose setup. Inspect
`08f_exact_<seed>.json` for `OPTIMAL` before interpreting certified gaps.
