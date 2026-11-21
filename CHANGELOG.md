## v0.22 — Dependency-safe experiment artifacts and PARTIAL audit (2026-11-21)

- Fix stage **08b `HTTPException: Artifact not found`** caused by treating `evaluation_started.json` (06 marker) as a completed `experiment.json`.
- Add read-only, shared readiness validation for experiment JSON, required chain identifiers, execution failure status, selected R1 SHA256 and HOLDOUT completion.
- Preserve original 06 error, started-only provenance, and explicit `06_r1_failure.json` / `06_experiment_dependency.json` in the audit ZIP.
- Guard 08b, 08c, 08f and 09 against absent or incomplete R1 artifacts; record dependency-specific `SKIPPED` / `HOLD` statuses without misleading success or secondary 404.
- PARTIAL exports retain all available files with SHA256. UI surfaces first failing stage and emphasizes which results were **not executed**.
- Add 4 new backend regression tests (108 in total) for started-only and failed experiment records, source hash mismatches, and integrated PARTIAL export.
- Prior v0.21.2 RAG, Skill, independent diagnostic rubric and exact-solver comparison are retained. No change to scoring thresholds. Real E2B/Ollama and frontend full build remain unverified.

## v0.21.2 — Diagnostic grounding without silent grade inflation

- Before both Qwen and ODA benchmark calls, supply a machine-extracted **public input fact sheet** separating independent R0 implementation test, contract, synthetic KPI comparison and evidence registry. No fixture oracle is sent.
- Make model prompt explicitly assess **implementation-vs-contract** and **requirements-vs-objective** before classifying cause; synthetically supported KPI mismatch is different from unknown real customer acceptance.
- Add conservative `evidence_bind_from_input()` to attach a **single supported missing evidence ID**, only after a semantically consistent diagnosis. No class, implementation judgment, scheduling policy, or change decision is rewritten.
- Persist original model response and score, assisted response and score, any model revision and score, and the exact input-only binding audit. **Only raw model PASS contributes to automatic diagnostic acceptance** in Business Assessment.
- Keep Fresh Blind unmodified first-pass model answers; show raw and harness-assisted results separately, without revision feedback. The old blind samples inspected during development are regression examples, NOT a new independent generalization result.
- Reduce unnecessary Ollama revision calls when the *only* failure is a safely bindable evidence reference. Errors in classification still require a model revision and can remain HOLD.
- 7 new tests for independent auditing, unknown/ambiguous evidence, LLM failures, raw-vs-assisted PASS, and Fresh Blind separation. Existing functionality retained.

# Change log

## v0.21.1 — 00b feature selection / validation guidance (2026-11-21)

- Removed the frontend's implicit reviewer-assignment default; a human must explicitly choose a feature template.
- When an LLM suggestion is copied, infer a **UI suggestion** only if the text unambiguously names one supported feature.
- Provide before-submit mismatch, mixed-requirement and deadline-context guidance; disable approval until text and feature selection are consistent.
- Expose an actionable Japanese 422 explanation on the backend; no change to the evidence-domain/semantic-scope safeguards, independent KPI evaluator or dataset acquisition.
- Tests cover correct classification and actionable API error for progress-notification text submitted as assignment.


## v0.21 — Diagnosis calibration, fresh blind cases, exact gap certificates (2026-11-21)

- Preserve all original Qwen/ODA diagnoses and frozen rubric scores. Optional one-shot model revision receives only input-derived consistency notes.
- Separate initial, post-revision and extra *first-pass-only* diagnostic challenge results. No benchmark oracle passed to models or into revision prompts.
- New 08f independent randomized scheduling HOLDOUT generated after R1 DEV selection; all raw E2B outputs and source hashes archived.
- Objective is lexicographic maximum on-time cases then maximum assigned cases. Exact proof uses Python exhaustive enumeration for small problems, optionally OR-Tools CP-SAT; only OPTIMAL licenses a proven gap.
- UI controls for diagnosis revision, fresh diagnostic blind cases and 08f count. Business assessment's AI-03 gate includes fresh blind PASS when enabled.
- Added tests for initial result preservation, independent new cases, proof-status honesty and archive completeness.

## v0.20 — Claims Allocation Domain Skill + candidate provenance (2026-11-21)

- Added reviewed, app-specific `backend/skills/claims_allocation/` with strict
  schemas, priority, qualification/capacity feasibility, scarce-specialist
  protection, greedy scheduling, bounded-beam search, and internal assertions.
- Generates self-contained content-hashed scripts for E2B; evaluator and tests
  remain in independent `backend/app/` modules.
- Explicit `llm_only`, `skill_only`, `compare` strategies in Step 06 and Step
  10. `skill_only` never invokes Qwen R1 code-generation, while Step 04's
  earlier model diagnoses remain part of the workflow.
- Pinned DEV selection with behavioral probes and four stress fixtures. An
  eligible candidate is chosen **before** HOLDOUT. Comparative post-selection
  HOLDOUT never feeds back into model repair or changes the chosen engine.
- Added audit provenance fields, source-level snapshots, DEV gate details,
  experimental runtime metadata, and standalone code SHA256 to exports.
- Business reports label selected R1 provenance and avoid claiming that a
  Skill candidate proves LLM code-generation success.
- Preserved Evidence-grounded Requirements RAG, feature-typed acceptance tests,
  two human approval gates, dataset downloads, and complete audit ZIP workflow.
- `bounded_beam` is a bounded heuristic, *not* an exact optimization solver.
- Source/docs: `docs/v020-domain-skill-and-comparison.md`.

## v0.19.1 — human review 422 hotfix

- Fixed ambiguous report/notification keyword handling in requirement
  classification and surfaced API 422 details in the UI.

For the original history, see `docs/` files for v0.08–v0.19.
