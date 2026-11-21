# v0.9 — Separate Finance Vertical FM for Requirement Diagnosis

## Research question

Can a separate finance-adapted model help detect the difference between *the correctness of a FIFO implementation* and *the suitability of the FIFO requirement for reducing missed claims deadlines*? Only synthetic case evidence is used. No real insurance customer data, EU regulatory retrieval, or actuarial inference.

## Fixed experiment design

| Item | v0.9 setting |
|---|---|
| Code model | `qwen3-coder:30b` through macOS Ollama |
| Finance model | OpenDataArena/ODA-Fin-RL-8B (third-party Q4_K_M GGUF default) |
| Propose input | R0 contract, DEV metrics, optionally synthetic `SIM-SLA-001` |
| Qwen and ODA | Independent requests; no model reads the other's output |
| R0 implementation ground truth | Pinned FIFO evaluator, already PASS |
| Business goal | Fewer overdue cases, no increased actual reviewer-hours |
| Root cause labels | requirement_mismatch / implementation_bug / insufficient_evidence |
| Decision gate | Deterministic rule on ODA schema; human approval |
| R1 requirement | Predeclared benchmark contract, not free generation |
| Code synthesis | Qwen with ODA diagnosis as advisory, fixed R1 service contract |
| Program validation | E2B + deterministic domain evaluator |
| Final evaluation | Fresh HOLDOUT only after DEV selection, not fed back into models |
| Business/regulation validity | UNVERIFIED |

## End-to-end audit

`R0 run` → `Qwen diagnosis` + `ODA diagnosis` → `independent rubric` → `human approval` → `Qwen generation with ODA advice` → `E2B DEV repairs` → `E2B HOLDOUT` → `Markdown + structured JSON + source/diff + raw E2B artifacts`.

## Design choices

1. **No silent model fallback.** If ODA is not installed, the proposal request fails visibly and error is recorded in `artifacts/proposals/`.
2. **Independent assessment.** Model-generated rationales are untrusted. The rubric rejects a root cause that calls compliant FIFO code a software bug, while requiring explicit evidence and a business deadline objective.
3. **No data leakage.** Proposals use R0 DEV aggregate only; holdout scores from R0 are not passed, and R1 new holdout is created only for selected candidate after DEV.
4. **No self-changing verifiers.** ODA can propose revisions, but the implementation must satisfy the predeclared, versioned R1 and human approval. Domain model cannot change acceptance criteria.
5. **No EU legal certainty.** Regulatory assertions are collected as open questions to verify with official sources, not implemented as law.

## Failure / negative tests

- `counterexample` with correct FIFO implementation → expect ODA `requirement_mismatch`, `correct`, `mismatch`, `SIM-SLA-001`; proposed deadline-aware scheduling.
- `control` with no evidence → expect insufficient evidence, no invented customer interviews.
- ODA claims `software bug` while R0 already passes → rubric HOLD, do not approve.
- ODA not installed → no substitution with Qwen, saved diagnostic error.
- E2B runtime fails → trial code, error metrics and input code retained where available.
- All changed code tested against unchanged evaluator and separate new HOLDOUT.

## Local operation

See README for commands to pull the Q4_K_M community GGUF and start the Mac Ollama server. Inspect model IDs in `GET /api/health` before starting.

## Interpretation

A successful demonstration proves the workflow can use a second model to make an independently checked requirement classification and pass guidance to code synthesis. It does **not** show that this particular vertical model outperforms Qwen on real EU insurance claims, nor that its recommendations are operationally correct without client evidence.
