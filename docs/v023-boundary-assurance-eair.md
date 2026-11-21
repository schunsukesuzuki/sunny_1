# v0.23 — Boundary-Aware Evaluation Harness (EAIR-inspired)

## Design goal

Production-oriented **separation of responsibilities**, not a replica of the EAIR multi-agent research environment. A small insurance-claims PoC should not require more LLM agents, GraphRAG, a graph database, Lean, or an organizational simulator merely to check workflow hand-offs.

Sources informing the design:

- Microsoft Research, **EAIR: Interaction Risks in Enterprise LLM Multi-Agent Systems** (2026), https://www.microsoft.com/en-us/research/publication/eair-interaction-risks-in-enterprise-llm-multi-agent-systems/ and https://arxiv.org/abs/2610.14800 . Key lesson: locally reasonable operations may violate cross-role, organizational or stateful constraints; inspect the first boundary, propagation, interception and task utility separately.
- Google DeepMind, **AlphaProof Code** (2026), https://deepmind.google/blog/introducing-alphaproof-code/ . Design analogy only: separate generated candidates from trusted checks and do not silently weaken human-approved specifications. **No Lean proof generation is implemented here.**

This implementation **does not claim to run MSR's EAIR Toolkit** or reproduce its risk/repair metrics. The risk names and certificate fields are inspired by its engineering ideas; all experiments here are a local, deterministic, narrowly scoped adaptation.

## Implemented

`backend/app/boundary_assurance.py`:

- **Boundary Contract Registry**: `00b_to_01`, `05_to_06`, `06_to_downstream`, plus a synthetic shared-budget example. Defines source owner, consumer and testable invariants.
- **00b→01**: verifies persisted human-reviewed source evidence, selected current-RAG evidence IDs, `requirement_type`, approved hypothesis, typed trace, and the demo-only/customer-approval distinction **before** continuing to 02.
- **05→06**: requires a persisted approved decision whose approval and proposal IDs match the active workflow. A missing/mismatched record blocks R1 generation, not only the later independent evaluator.
- **06→08b/08c/08f/09**: extends v0.22's completed-artifact and selected-code SHA256 check. The experiment's R0 run, proposal, approval and experiment IDs must match the active workflow; otherwise its state becomes `LINEAGE_MISMATCH`, and downstream consumers fail closed.
- **08g Boundary Assurance**: runs four named boundary controls (including the synthetic resource-budget fixture), persists a deterministic five-scenario regression suite, summarizes detected anomalies and produces narrow failure certificates. The standalone risk vectors do not claim measured incident probabilities.
- **Minimal provenance DAG**: writes ID/dependency adjacency JSON, not GraphRAG or an online graph store; a final version after stage 09 includes the assessment node when available.
- **Audit and UI**: ZIP stores registry, checkpoints, failure certificates, risk summary, regression outcomes and topology. Step 10 displays the boundary status separately from model diagnosis and business decision.

### Key files in the resulting audit ZIP

```text
workflows/<id>/boundary_00b_to_01.json          # Public-evidence hand-off, if applicable
workflows/<id>/boundary_05_to_06.json          # Human-revision gate
workflows/<id>/boundary_06_lineage.json        # R1 experiment lineage (if attempted)
workflows/<id>/boundary_08b_lineage.json       # Behavioral validation dependency
workflows/<id>/boundary_08f_lineage.json       # Blind evaluation dependency
workflows/<id>/08g_boundary_contracts.json
workflows/<id>/08g_boundary_regression.json
workflows/<id>/08g_boundary_assurance.json
workflows/<id>/08g_boundary_assurance.md
workflows/<id>/08g_provenance_dag.json
workflows/<id>/09_final_provenance_dag.json
```

The certificate identifies **observed** anomalies, a candidate repair and whether the consuming stage was stopped. It does not invent a causal path that was not observed in stored artifacts. The ZIP's `COMPLETE` status is process/export completeness, not customer or production validity.

### Interception outcomes

- `PASS_CONTROLLED`: tested local cross-stage contracts held. This is **not** a model or customer correctness PASS.
- `HOLD`: a detected hand-off breach or failing synthetic regression; no subsequent dependent evaluation may be counted as a successful independent verification.
- `INCOMPLETE_UPSTREAM`: upstream R1 is missing/incomplete and its specific lineage check is deferred; the earlier v0.22 readiness gate remains active. Do not treat as PASS.
- `PARTIAL` ZIP is retained for stops, missing dependencies, or user rejections. Successful checkpoint archives remain available after human approval waits.

### What is intentionally not implemented

- Live cross-organization authorization, authenticated reviewer identity, immutable event-store / cryptographic signatures, real customer consent, regulatory compliance.
- Multi-agent strategy simulation, EAIR-Worlds recreation, risk occurrence-rate measurement, formal SAT/SMT/Lean proofs, autonomous repair of policies.
- A claim that evidence IDs, schema checks or typed IR demonstrate semantic requirement correctness or causal attribution.

## Reproduce (offline tests)

```bash
cd backend
PYTHONPATH=. pytest -q tests/test_v023_boundary_assurance.py
PYTHONPATH=. pytest -q
```

The new tests include two separately identifiable paths: normal one-click execution and fail-closed behavior when `approval.json` is missing; pure tests check cross-workflow ID substitution, hypothesis drift and aggregated shared-capacity oversubscription. E2B and Ollama are **mocked** for the test suite; on a live Mac they must be verified with real credentials/models and source downloads.

## What to measure in a customer-facing PoC

Interception rate for seeded boundary violations, workflow utility (not just number of blocks), false positive rate, hand-off/debugging time, LLM invocation/tokens, and storage/indexing overhead. No demonstrated reduction in real operations TCO is claimed.
