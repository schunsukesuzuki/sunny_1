# Change log

## v0.33.0 — Demo assumptions + human-reviewable imperfect proposals (2026-11-22)

- **Explicit demo budget and staffing:** 10R now uses example values `€30,000`, 2 engineers, PM 0.2 FTE, 8 weeks, existing APIs first, and no dedicated ops; the backend uses the same defaults. They are marked **UNVERIFIED** in UI and audit. Users can edit, blank fields to represent unknown, and regenerate manually.
- **Budget is not a cost estimate:** Numeric estimates in `estimated_cost_basis` are permitted but visibly labeled `UNVERIFIED_COST_ESTIMATE`, not binding vendor quotes or customer-confirmed budgets.
- **Draft visibility separated from hard authorization:** Typed draft with residual semantic warnings is **stored and displayed** as `DRAFT_WITH_WARNINGS`; individual options and issue descriptions remain accessible. An invalid targeted repair no longer discards the valid typed proposal. Structural/Ollama failure remains `GENERATION_FAILED`, while the independent 00–09 report and demo scenario stay visible.
- **Scoped bounded repair:** Only failed item(s), not all technical alternatives, receive at most one attempt; unsuccessful repairs are recorded and the original item is retained. Warning status can receive human feedback (never production approval). Source freshness/staleness and explicit approval requirements remain unchanged.
- **No pipeline policy changes:** Dogwood, strict constraints and human approval, CP-SAT and DEV/HOLDOUT, diagnostic gates and production `NO_GO` logic stay intact. Audit ZIP format remains `AUDIT-EXPORT-v0.25.0` with producer `0.33.0` and corrected downloadable ZIP name `claims_full_run_v033_...zip`.
- Python regression 184 PASS; TSX layout + syntax checks PASS; full Vite build / live Ollama / Docker / Rust / E2B not executed in packaging environment. See `docs/v033-demo-assumptions-and-reviewable-drafts.md`.

## v0.32.0 — Priority-high-only advisory safeguards (2026-11-22)

- **Deterministic citations / LLM hypotheses separated:** `PUB-*` IDs, source URL and excerpts come only from the human-selected evidence register, saved in `deterministic_public_context`. Model-generated customer problems always remain `hypothesis_unverified` with no source references. No independent semantic support for a specific customer is claimed.
- **Section-local semantic repair:** On a well-formed initial advisory whose semantic contract fails, regenerate only failed top-level sections via field-specific typed schemas, once per section. Keep other fields unchanged. Revalidate and fail closed if any error remains; successful repairs are recorded as `repair_actions` apart from the proposal. Structural parsing errors remain failures; full autoretry is not introduced.
- **COMPLETE synchronization:** Auto-start only after COMPLETE. PARTIAL is explicit opt-in `provisional_mode=true` with a visible provisional label; old PARTIAL proposals become stale on completion, cannot be reviewed until regenerated. Existing canonical-source SHA-256 invalidation and safe review remain.
- Existing 10 → 10R (proposal then audit) → 00 → 01..09 layout, Dogwood, CP-SAT, diagnostic quality gates, audit export format `AUDIT-EXPORT-v0.25.0`, manual approval and full-run behavior preserved. No CI/CD automation or unrelated medium-priority improvements added.

## v0.31.0 — Source-Locked Advisory / Evidence-Coupled Technical Options (2026-11-22)

- 10R's AI proposal now fingerprints the canonical workflow, latest benchmark and 09 assessment, feature acceptance/requirement trace, selected evidence and 08f, then stores `source_snapshot` and `source_hash` per version. Export ZIP repacks no longer change workflow `updated_at`. Old proposals from PARTIAL or before diagnostic retry are `STALE_ADVISORY` and cannot receive new reviews until explicitly regenerated from current data.
- `REQ-PUBLIC-001`/`claim_progress_updates`, `PUB-*` selected source IDs, notification acceptance test IDs, diagnostic quality HOLD, non-discriminating DEV (0 cases), and incomplete service integration are sent as scoped inputs. Fabricated source IDs and assignment-only alternatives masquerading as notification features are rejected; public evidence remains background context, not actual customer proof.
- Typed Japanese proposals require exactly three comparable alternatives (low-complexity / balanced / research), each with requirement alignment, necessary roles, relative effort, delivery risk, cost basis, tradeoffs and validation. Next experiment suggestions include ownership, success measures and evidence refs; unknown budget does not authorize invented prices.
- Keep deterministic `required_attention` separate from LLM advice. Store `revision_diff` between versions, including changed assumptions and source state; do not interpret a structural difference as improved quality or ROI.
- UI order unchanged: **10 → 10R AI proposal → 10R outcome analysis → 00 → 01..09**. Existing Dogwood, DEV/HOLDOUT, CP-SAT, independent diagnostics, 09 decision and audit ZIP format are preserved. AI proposal generation, history, review and retry never auto-run a new workflow or CI/CD job.
- 175 Python regression tests passed; TypeScript parse/transpile and layout checker passed with global TypeScript. Test-mode replay of the user's v0.30 audit ZIP loaded `REQ-PUBLIC-001`, three selected PUB refs, notification non-integration, diagnostic HOLD, 2 retries and correctly classified the original draft as stale. Native Rust/Docker, full Vite and real Ollama/E2B are not verified.

See `docs/v031-advisory-source-alignment-and-review.md`.

## v0.30.0 — Post-run presales advisory draft (human-loop)

- Step 10R now starts with an LLM-generated **unapproved** customer problem and technology proposal, followed by the existing independent per-stage outcome analysis. Screen order: **10 → 10R proposal → 10R results → 00 → 01–09**.
- New typed budget (EUR), engineering team size, delivery weeks and free-form scope/operational constraints. Empty means unknown. Generated choices cover rules-first/low-complexity, balanced integration and optionally research. Never infer customer facts or compliance from synthetic evidence.
- Generation is automatic once after a terminal workflow opens in the UI, then explicit only on regenerate. Long Ollama calls run in separate background tasks. 10R report itself is always read-only and never blocked by an LLM timeout.
- Stored immutable `10p_advisory_vNNNN.json` and `10p_review_vNNNN.json` plus current-index snapshot, hash-scoped evaluation provenance and version history; regenerated audit ZIP includes those artifacts. Human review never triggers autonomous reruns.
- Existing Dogwood/R1/DEV/HOLDOUT, 08f, 09 outcomes and `AUDIT-EXPORT-v0.25.0` manifest format are unchanged.
- Python regression tests and TSX order/parse checks included. Native Ollama/Docker/E2B tests must be run on target machine.

# v0.29.0 — Lexicographic 08f, Research-Only Selection Review, DEV Discrimination, Targeted Diagnosis (2026-11-22)

- Fix post-selection 08f false equivalence: require independent validity plus an `OPTIMAL` solver certificate, then compare `(missed_deadlines, unassigned_cases)` lexicographically. Conditional secondary gaps do not mix incomparable primary scores. Preserve old primary-gap field for backward compatibility.
- Separate "selected is worse than another candidate" from "selected is worse than the exact oracle" and mark old evidence with no secondary certification as inconclusive where appropriate. Never modify R1 selection from 08f.
- DEV ties now explicitly yield a **provisional research candidate** with required human review, *not* automatic approval. No extra production approval endpoint is implied.
- Add case-level DEV discrimination audit across base, extra, and stress cohorts. Identical result pairs are non-discriminative, regardless of leave-one-out stability. No 08f/HOLDOUT data leakage.
- Add opt-in input-only field-targeted benchmark repair: no oracle-driven repair invocation, no changes outside target fields, immutable first RAW, no blind feedback; record proposed vs adopted fields and failure reasoning.
- Add fields to 10R and README, keep layout **10 → 10R → 00 → 01..09**; preserve audit ZIP format `v0.25.0` and report consumer view `v0.27.0`, update producer to `0.29.0`.
- Python regression tests and TSX AST/layout checks; native Rust, Docker, Vite full dependency build, live Ollama and E2B **not verified** here.

# v0.28.0 — Preselection Robustness, RAW Diagnostic Axes, Canonical Retry Report (2026-11-22)

- Keep **10 → 10R → 00 → 01〜09** unchanged from v0.27.1.
- DEV-only candidate selection: preserve existing eligibility gates; additionally run four predeclared distribution-shift DEV fixtures (scarcity/capacity/deadline/arrival; seeds 920000..920003), alongside the original four pinned stress fixtures (910000..910003). Rank eligible candidates by ordinary DEV deadline misses and unassigned cases, new DEV-cohort worst/total misses and unassigned, original stress worst/total misses and unassigned, and only then stable source order. Store `experiments/<id>/dev_robustness_preselection.json` **before** 06 HOLDOUT. Incomplete/misaligned cohorts are excluded for every candidate and flagged for review; unresolved ties and leave-one-out sensitivity likewise require review. These extra E2B DEV runs cost time/resources. Never use 06 HOLDOUT/08f/CP-SAT in selection or model repair feedback.
- Six separately evaluated RAW diagnostic axes: classification, implementation, evidence, revision action, requirement fit, cross-field consistency. Store benchmark and workflow JSON summaries, preserve initial/latest responses, and never count blind retries as fresh initial passes.
- Canonical latest benchmark: report uses `benchmarks/<id>/benchmark.json` after selective retry. Derived `08_latest_state_index.json` and `08_diagnostic_axes.json` update atomically; older snapshots and the prior ZIP remain historical. Report warns if workflow/index and benchmark disagree.
- Preserve format compatibility: audit manifest schema `AUDIT-EXPORT-v0.25.0`; report contract `report_version=0.27.0`; producer `0.28.0` identified separately.
- Keep Dogwood deny-path probes, feature-specific acceptance tests, authorizations, R0/R1 evaluation and CP-SAT independent post-selection 08f unchanged.
- Scope: predeclared synthetic cases only, no proven production/real-client generalization or formal guarantee from diagnostic lexical checks. Docker/Rust, Vite full build, real Ollama/E2B are not tested by source packaging.

See `docs/v028-dev-robustness-diagnostic-axes-latest-report.md`.

---

# v0.27.1 — Step 10 → terminal report → Step 00 (2026-11-22)

- Render the one-click **10** section before the manual evidence **00** section, followed by 01..09.
- Move the persisted **COMPLETE/PARTIAL report** out of the Step 10 card into its own immediate sibling between 10 and 00; preserve async loading, exact Workflow ID + updated_at guards, manual reload on errors, and read-only report API.
- Expose public dataset, evidence query and optional Qwen extraction directly in Step 10 (shared React state with manual 00) so users can start without scrolling to 00.
- Update the guide and documentation. No modification to backend algorithms, policy, approval gates, evaluation or audit exports.
- Validation: Python regression suite unchanged (152 passed); TSX parsed and static AST layout verification passed. Full React/Vite and Docker/Rust live builds require external dependencies and remain unverified in this packaging environment.

See `docs/v0271-step10-report-before-step00.md`.

---

# v0.27.0 — Typed feature acceptance, semantic diagnosis, DEV selection and Dogwood negative audit (2026-11-22)

- Bind each human-approved feature to an explicit acceptance contract; `claim_progress_updates` passes only its own four notification prototype tests and never via R1 assignment KPIs. Store `08e_feature_acceptance.json` and show it in step-10 report. Keep production `NO_GO` where notification integration is absent.
- Add conservative oracle-free RAW diagnostic cross-field checks across classification, visible evidence, stated cause, proposed revision and scheduling precedence. Preserve model original answers, separate diagnostic quality HOLD from execution status.
- Record predeclared DEV-only lexicographic candidate ranking (missed deadlines, unassigned, stable tie). After selection, compare on 08f randomized synthetic cases without reselecting or feeding results into the model or DEV (`08f_selection_gap_analysis.json`). Uncertified comparisons are marked INCONCLUSIVE.
- Record synthetic Dogwood native denial probes (unapproved, workflow/proposal/approval ID mismatches, revocation), a valid approval positive control, expired approval DENY and isolated journal-tamper ERROR. Capture Docker build Rust `cargo test` output; native binary/log unavailability stays explicit and never becomes PASS.
- Preserve v0.26.1 screen order `00 → 10 → 01..09` and inline report. `AUDIT-EXPORT-v0.25.0` remains the backward-compatible ZIP schema; `producer_version=0.27.0` identifies the producing app.
- Regression: **152 Python tests passed**, TSX syntax parse passed. Native Cargo/Docker, full Vite and real E2B/Ollama not executed in this packaging environment.
- Limitations: synthetic-only acceptance and optimization, lexical consistency cannot prove semantic correctness, Dogwood actor identity and ongoing distributed authorization remain unproven; no production approval.

See `docs/v027-feature-contract-diagnostic-selection-dogwood.md`.

---

# v0.26.1 — Step 10 first, inline persisted workflow report (2026-11-22)

- Move step **10** from the bottom to **immediately after step 00 and before step 01** (the guide's order matches the rendered sections). All 00–09 operations and numbers remain unchanged.
- Add step-10 quick settings for the shared brief, seed, 04 diagnosis condition and R1 mode, plus a reviewer token field at the step-10 human approval gate. No new bypass for human approval.
- Add a read-only `GET /api/full-run/{workflow_id}/report` endpoint over persisted workflow, assessment, benchmark and Dogwood artifacts, including cross-checks for linked experiment/assessment/benchmark IDs. In-progress workflows return HTTP 409; complete/partial workflows disclose exact incomplete stage counts without fabricating an assessment.
- Render a multi-section report **inside step 10** automatically after COMPLETE or PARTIAL and after loading a saved Workflow ID. Show status, stage counts, Dogwood, diagnosis execution vs RAW quality, requirement trace, business decision, synthetic R0/R1 KPI, detailed criteria and next actions. Retain Markdown and ZIP downloads.
- Preserve core policy/diagnostic/optimizer logic and existing evidence ZIP schema. V0.26.1 is a UI/reporting-only incremental release; the existing workflow data format remains compatible.
- Validation: Python tests **142 passed**; v0.26 audit ZIP reused to confirm report returns 18/18, `ALLOW`, `HOLD_HUMAN_ADJUDICATION`, `NO_GO`. TSX syntax parser and step order checks passed. Native Rust/Docker compilation and full Vite build were not available in packaging environment.

---

# v0.26.0 — Diagnostic Execution vs Quality, Selective Timeout Replay (2026-11-21)

- Separate per-call inference timeouts (HTTP 504 -> `INCOMPLETE_TIMEOUT`) from RAW misclassification/consistency HOLD, with separate quality and execution codes.
- Deterministic, oracle-free cross-field checks across classification, implementation validity, synthetic fit, requirement change and input evidence IDs. Original 8-criterion benchmark rubric and RAW outputs stay unchanged.
- Explicit bounded retry endpoint for unfinished model calls only; same pinned model and input hash, replay artifacts, original snapshots, two retry attempts per target, best-effort local exclusive file lock, no automatic model substitution.
- Retried blind samples are labelled non-fresh and cannot create a first-pass generalization claim. No prompt feedback derived from gold labels or benchmark scores.
- Full workflow PARTIAL recovery: defer 09 if 08 execution is incomplete; after a successful replay, recompute deferred diagnostic-dependent 09 without rerunning Dogwood/06/R1/08f. Preserve original ZIP and prior audit records. Fix misleading 06 failure warning when only 08 timed out.
- Allow `ODA_FIN_TIMEOUT_SECONDS` (default 480s) distinct from Qwen's `OLLAMA_TIMEOUT_SECONDS` (default 240s).
- Python pytest regression: **138 passed** including selective timeout retry, immutable completed trials, integrity mismatch, blind replay and full-run ZIP recovery. v0.25 uploaded archive replayed locally with a stubbed model: workflow became COMPLETE, quality stayed HOLD. Rust/Docker/native Ollama and full Vite build were NOT executed in this environment; TSX syntax parsing passed.
- Production authorization remains NO-GO; this is synthetic-model diagnosis screening, not customer/legal validation.

---

# v0.25.0 — Durable Approval Journal, Native DENY Regression, Diagnostic Reliability Gate (2026-11-21)

- New persistent local SQLite append-only approval/revocation journal, SHA256 chain with optional keyed HMAC, full-chain verification and approval-record linkage before Dogwood; revoked/missing/tampered/stale approval blocks both standalone and full-run R1.
- New `POST /api/approvals/{approval_id}/revoke`, optional single-reviewer shared HTTP header token (`X-Reviewer-Token`) and optional server-side HMAC env configuration. Actor labels without a token remain self-reported, and shared secrets are not a production identity provider.
- Native Rust test fixtures now cover unrelated revocation, missing approval, malformed JSON/IDs and mismatched workflow/proposal/approval IDs. Existing pinned crates and v0.24.1 Rust API fixes retained.
- Step 08 and direct benchmark now report raw-model diagnostic reliability separately from E2B R1 technical success: fixed and fresh blind raw failures force `HOLD_HUMAN_ADJUDICATION`; assisted scores never substitute for raw. The benchmark remains a post-R1 synthetic audit, not a step 06 authorization prerequisite.
- Exports add `05_authorization_ledger.json` scoped receipt and `08_diagnostic_reliability_gate.json`, retain v0.24 lineage and source SHA256; the global SQLite database and tokens are not bundled. Updated UI with revoke control, reviewer token and gate warnings.
- Python test results from packaging environment: 132 passing (including revoke and reviewer-token API integration). **Cargo/Docker unavailable; native Rust and frontend Vite build not verified here.**
- Scope limit: SQLite is durable, *Dogwood itself remains ephemeral per-decision replay*. Revocation does not retroactively undo already running or completed R1. No external identity, multi-tenant security, formal legal-causation proof or production authorization.

---

# v0.24.1 — Rust/Dogwood compile hotfix (2026-11-21)

- Fixed `E0308`: pass `&principal` to `EventBuilder::principal(&str)`.
- Fixed five `E0277` failures: wrap `DurableError` (which does not implement `std::error::Error` in the pinned `dogwood-local-engine = 1.1.2`) as `std::io::Error` at `open`, `install`, and three `submit` call sites. The original failure is preserved in the diagnostic message; no authorization failure is converted to ALLOW.
- This is a targeted source compatibility fix. Python API/audit JSON formats remain v0.24.0; policy and schema files are unchanged.
- Validation: Python unit tests can be run in an available Python environment; native Rust compilation and Dogwood policy fixture execution **must be run in Docker** (`docker compose build --no-cache api`) because Rust/Docker are unavailable in the creation environment. Treat all runtime ALLOW/DENY assertions as **not yet verified** until those tests pass.

# v0.24.0 — Real Dogwood Local Engine Approval Gate (bounded replay)

- Add a Rust executable compiled against published `dogwood-local-engine` and `dogwood-language` 1.1, with a readable `.dw` policy, Cedar schema, and native temporal authorization fixtures. Not a fake Python policy interpreter.
- Require matching persisted human approval before R1 in BOTH full-run and direct `/api/generate-r1` / `/api/evaluate-r1` endpoints. Reject absent/stale/mismatched approval, DENY, errors and subprocess timeouts without fallback.
- Replay the approved event and requested operation into a fresh temporary durable store for every decision. Revocation is tested in Rust, but **no authenticated user-revocation UI/event ledger** is implemented. This deliberately reduces persistent infrastructure at the cost of not being a continuously running authorizer.
- Export `05_dogwood_authorization.json`, `boundary_05_to_06_dogwood.json`, exact source policy/schema, source hashes and boundary certificates; show policy status in UI. Preserve EAIR-inspired 08g, E2B, independent evaluation, diagnostic scoring and all original business controls.
- Default Docker mode `DOGWOOD_MODE=enforce`. `DOGWOOD_MODE=off` is explicitly labelled `NOT_ENFORCED` for Python regression tests only, never to be interpreted as an actual Dogwood verdict.
- Python adapter tests and old regression tests run without local Rust. Real Rust compile/test and container integration require Docker networking and were NOT verified in this authoring environment.
- Limitations: replay trusts locally persisted records and actor labels are not authenticated, no immutable audit ledger, no inter-session cumulative policies, no semantic/legal verification, and no demonstrated production ROI.

---

# v0.23.0 — Boundary-Aware Evaluation Harness

- Microsoft Research EAIR's cross-role/cross-state risk framing is adapted only to **workflow hand-offs**, not to a multi-agent simulation.
- New `backend/app/boundary_assurance.py`: reviewed requirement/evidence hand-off (00b→01), human approval integrity (05→06), experiment lineage integrity (06→08b/08c/08f/09), and deterministic shared-resource violation fixture.
- New `08g_boundary_assurance`: boundary-regression suite, bounded realization certificates, process anomalies vs intercepted harm, and topology-only provenance graph (JSON, no graph DB).
- Block a dependent step on a mismatched/missing approval or cross-workflow experiment, instead of inheriting a false `COMPLETED` status; preserve original failures and PARTIAL archive.
- Read-only per-stage risk observations, v0.23 version tags/ZIP filenames, UI visibility, and assessment linkage added.
- Retains existing evidence RAG, Domain Skill, LLM raw/assisted diagnosis, E2B execution, randomized blind exact optimization and two human gates.
- This is an **engineering demo**. No authenticated permission enforcement, formal proof, production safety claim, new real-data performance evaluation or EAIR reproduction.

---

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
