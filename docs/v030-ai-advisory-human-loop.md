# v0.30 — Post-run AI presales proposal / Human-in-the-loop iteration

## UI order

**10 (batch execution) → 10R (AI presales proposal first → each-stage results/analysis) → 00 → 01–09.**

After a workflow becomes `COMPLETE` or `PARTIAL`, the UI starts one independent Ollama/Qwen proposal request (if none exists for that workflow). The 10R report and audit remain accessible while the proposal is `RUNNING`, `GENERATION_FAILED`, or `DRAFT_UNAPPROVED`. Generating or reviewing a proposal does **not** change R0/R1/08/09 results, access authorization, or the selected Skill. No CI/CD, autonomous code deployment, or autonomous follow-up run is performed.

## Input constraints / provenance

The proposal may use **allowlisted summaries** from the same workflow's saved, scoped 10R report: completion status, approval result, requirement type, typed feature acceptance status, diagnostic execution/quality gate, DEV review and discrimination status, 08f gap status, business decision, aggregate synthetic FIFO/R1 results, and the workflow's submitted brief. It receives neither raw hidden HOLDOUT examples nor scoring-oracle data for DEV selection. The requirement description and human-entered notes are untrusted data. All generated output remains a hypothesis.

Inputs are explicitly typed `AdvisoryConstraints`: budget EUR (optional), team size (optional), delivery weeks (optional), engineering scope, operational constraints, stakeholder notes. Empty numerical inputs represent **unknown**, not zero. The model is told not to invent prices, customer statements, causal explanations, regulation compliance or production authorization.

Model outputs are validated with Pydantic: problem hypotheses including uncertainty and a restricted source-file reference allowlist; low-complexity, balanced and optionally research-level alternatives; budget/team tradeoffs; next experiment; questions for the customer; and PM/engineer review prompts. The source reference allowlist checks *existence in the declared report schema only*, not semantic entailment. No source reference is a verified causal proof.

## API

- `GET /api/full-run/{workflow_id}/report`: unchanged read-only execution report.
- `GET /api/full-run/{workflow_id}/advisory`: current proposal status, latest draft and immutable version index; never generates.
- `POST /api/full-run/{workflow_id}/advisory` `{constraints:{...}, regenerate:false}`: starts Ollama generation as a FastAPI background task (for terminal workflows only). Same snapshot + assumptions are idempotent; explicit `regenerate:true` creates a new version. API responds immediately with RUNNING.
- `POST /api/full-run/{workflow_id}/advisory/review`: records `actor`, `rationale`, `decision`, `next_iteration_brief` against one completed proposal version. One append-only review per version; **review does not approve production or start the workflow**.

The model failure is `GENERATION_FAILED`, separate from workflow `COMPLETE`/`PARTIAL`. `10p_advisory_vNNNN.json` and `10p_review_vNNNN.json` are immutable snapshots; `10p_advisory_current.json` is an atomic latest-view index. File records and their SHA256 are included in regenerated workflow audit ZIPs, without changing the audit-format version `AUDIT-EXPORT-v0.25.0`.

The editor can change constraints and regenerate a proposal. A PM can save an optional human-edited next-cycle brief, copy it into the 10/01 input field and **explicitly start a new 00–09 workflow**, followed by existing human approval gates. Prior workflow results remain historical and are never overwritten.

## Limits

- This is a local, single-user demonstration. Review actor is self-reported; no identity proof or multi-tenant access control.
- Calling Qwen may time out depending on the Mac and local model. The report remains usable if proposal generation fails.
- No real customer requirements, ROI, fees, capacity, regulations, or budget are inferred from the synthetic test.
- Prompt/JSON schema constraints do not prove that the generated recommendation is semantically correct. Validate against customer facts.
- Runtime Ollama, Docker/Rust, E2B and Vite integration need execution in the target environment.
