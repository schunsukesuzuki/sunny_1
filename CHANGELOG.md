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
