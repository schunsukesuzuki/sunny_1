# v0.14 — R1 Policy & Stress Validation / One-Click Audit Package

## Purpose

Close the gap between **a favorable fixed-hours KPI** and **whether generated code actually follows the R1 scheduling intent**. Also eliminate repetitive ZIP/manual export steps. This is a bounded synthetic demonstration, not formal verification, production suitability, regulatory analysis or proof of commercial ROI.

## Protocol

1. Complete 01–06 manually, including **explicit human review** of a fixed R1 contract. A saved `experiment_id` and SHA256-verified `selected_r1.py` are required.
2. In 10, choose the stored `experiment_id`, choose the diagnostic case set/repetitions in 08, click **追加検証＋診断比較＋事業評価を実行し、ZIPを保存**.
3. The backend executes *the selected code* in E2B on two pinned behavioral examples: urgent deadline takes precedence over earlier-arriving flexible work; when one reviewer has a scarce skill, common work must not monopolize their capacity if another qualified reviewer exists. This **does not** use the unseen HOLDOUT for additional model repair and **does not** mutate the original experiment.
4. Run four fixed synthetic stress scenarios (capacity pressure, skill bottleneck, deadline compression, arrival reordering) across FIFO reference, fixed deadline/skill heuristic, and selected generated code in E2B. Compare **missed including unassigned**, unassigned and scheduled assignment hours. Reference is not proven optimal.
5. Run the Qwen/ODA fixed diagnostic benchmark. Store each call, failures, condition-specific scores and summary. One favorable proposal diagnosis does not mean that the model passes independent multi-case assessment.
6. Run the deterministic two-axis business assessment, linked to the new validation and benchmark. The AI-07 policy and AI-08 stress criteria are required for limited **Customer Discovery** GO. Financial value/production/security/regulatory claims remain **UNVERIFIED**.
7. ZIP all linked inputs/outputs, source code attempts, E2B stdout/stderr, proposals, human approval, model benchmark trials, new policy/stress evidence, and final assessment.

## Completeness & integrity

- Zip root `00_START_HERE.md` is a reading guide and stage summary.
- Zip root `manifest.json` includes all linked artifact IDs, a record for **every** included file with its size and **raw-byte SHA256**, plus omitted categories, skipped oversized files, and stage failures. A zip is `PARTIAL` when any stage fails or required artifact is missing. Model rubric HOLD is a scientific **finding**, not an export error.
- `exports/<id>/complete_audit_package.zip` is stored on the bind mount and can be re-downloaded from history.
- If a backend process is interrupted mid-request, `exports/<id>/started.json` remains. The UI cannot resume that request; start a new export. An interrupted export is not marked COMPLETE.
- **No** secrets are exported intentionally, but the original `approval.json` carries a demo actor field. Review the ZIP before sharing.
- Manifest/file hashes are integrity pointers, not signed third-party attestations.
- Each explicit JSON `assessment.json` contains E01–E07 provenance classifications. No interviewer names, employer identities or biographical context are used in the rubric or assessment prompts (no LLM prompts are used for assessment).

## API

```text
POST /api/policy-validation/run     {"experiment_id":"<uuid>"}
GET  /api/policy-validation/<validation_id>/report
POST /api/business-assessment/run   {"experiment_id":"<uuid>","policy_validation_id":"<uuid>","benchmark_id":"<uuid>"}
POST /api/pipeline/run-and-save     {"experiment_id":"<uuid>","case_ids":[...],"repetitions":1}
GET  /api/exports/<export_id>/bundle
GET  /api/history/exports
GET  /api/history/policy_validations
```

## Decision scope

- `r1_independent_kpi_improvement_pass`: a historical synthetic **KPI** judgment only; not automatically converted to R1 semantic compliance.
- `behavior_pass`: the two specified behavioral probes pass (not mathematical proof).
- `stress_all_constraints_valid` and `stress_regressions_vs_reference==0`: no detected hard-constraint failures or comparator regressions in four synthetic cases (not production resilience).
- Diagnostic benchmark PASS counts require full independent rubric evaluation; a single ODA/Qwen result does not substitute for it.
- `CUSTOMER_DISCOVERY_ONLY` requires a sound linked synthetic KPI, human approval, behavioral probes and stress checks. **Production remains NO_GO** in all cases.

## Limits and security

- Each selected generated program runs in a separate E2B sandbox with internet disabled. The application only stores and replays artifacts, not E2B API keys.
- The API is unauthenticated local demonstration. Keep it bound to local/controlled networks and never expose it publicly.
- Dev/HOLDOUT seed separation is preserved, but the policy and stress probes are not independent real-world distributions.
- This exercise has neither legal/regulatory source retrieval nor customer demand, pricing or operations validation.
