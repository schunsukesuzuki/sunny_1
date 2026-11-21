# v0.10 — Requirements diagnosis benchmark and audit protocol

This is an **offline-synthetic evaluation design** that invokes the local Ollama models during actual use. It does not retrieve real German insurance contracts, claim files, EIOPA guidance, GDPR requirements or business customers. It is not a general semantic-proving engine.

## Research question

Does domain-adapted `ODA-Fin-RL-8B` identify the *type and cause* of a requirement defect more reliably than `qwen3-coder:30b`, when both receive **the same case and output schema**, including the independent implementation result?

A correct top-level `requirement_mismatch` classification is insufficient if the explanation calls a correct FIFO implementation a bug, invents a source, or advises both strict FIFO and deadline-first as simultaneous primary priorities.

## Four pinned synthetic cases

| Case ID | Given independent implementation finding | Business/customer evidence | Expected cause |
|---|---|---|---|
| `fifo_sla_conflict` | PASS, strict FIFO | Synthetic paired KPI and `SIM-SLA-001` | `requirement_mismatch` |
| `correct_fifo_no_customer_evidence` | PASS | None | `insufficient_evidence` |
| `actual_fifo_implementation_bug` | FAIL, inverted arrival order | `SIM-BUG-001` deterministic trace | `implementation_bug` |
| `conflicting_stakeholder_notes` | PASS | Synthetic opinions disagree, no controlled KPI | `insufficient_evidence` |

Fixed oracles and case IDs are defined in `backend/app/diagnostic_benchmark.py`. The model only receives `FIXTURES[case_id]["input"]`; oracle labels are held by the independent scorer. A small synthetic benchmark demonstrates software behavior **only**, not production accuracy. Do not claim statistical significance from two cases or a few repeats.

## Two independent axes

1. **Implementation correctness:** passes the *pinned* software contract? Separate independent evaluator; a failed business KPI does not imply a code defect.
2. **Requirement adequacy:** the synthetic, specified business objective is or is not supported under the fixture assumptions? This can be `mismatch` even though **real-world customer validity remains `unverified`**.

A third, separate question is whether the proposed replacement requirement is coherent. `deadline_first_fifo_tiebreak` means deadline first and FIFO only among equal deadlines. `fifo_first` must not be falsely represented as deadline first. Rules in `diagnostic_quality.py` flag known conflicting patterns and missing evidence IDs. These are **partial lexical checks**, not complete semantic verification. Human review remains necessary.

## How to run

1. Start Mac Ollama with both models, launch Docker Compose with E2B credentials as before.
2. The existing 01–07 R0 → Qwen+ODA proposal → human approval → R1 → E2B workflow is unchanged except for the stronger diagnosis gate. Quality HOLD still permits an **explicit, audited human override** for counterexample-only technical exploration.
3. In **08 — 診断品質ベンチマーク**, select one or more synthetic cases and repetitions (1–3). One case with 1 repeat causes **2 sequential** model calls; 4 cases × 3 repeats causes **24** model calls. Both models use the same schema, prompt template, temperature and input fixture. The two models differ in size and training, so this is not a controlled estimate of *domain adaptation alone*.
4. Inspect per-dimension checks rather than overall score alone. Review original Qwen and ODA responses alongside the fixed rubric. A failed model call is saved separately and never silently replaced by the other model.
5. Download the Markdown and **complete artifacts ZIP**; local persistent artifacts include all trials, errors, scorecards, input hashes, model IDs, and time measurements. No API keys are saved.
6. To **re-evaluate old v0.9.1 proposals**, copy the previous `artifacts/` directory into the new project, visit step 08, enter the historical `proposal_id`, and use **旧診断を再採点**. This is read-only: neither prior approval nor its original rubric status is rewritten.

## Pass criteria and limitations

The model's independent rubric checks: root-cause class, R0 implementation status, synthetic business fit, refusal to certify real customer validity, supplied evidence IDs, explanation's consistency with independent R0 result, scheduling revision conflict, and whether a change should target *requirements* or *implementation*.

**A successful benchmark run does not mean the models passed.** `COMPLETED` means the API calls completed and scores were logged. Check `summary.{coding,finance}.passed`, `trials[].rubric`, and possible model failures.

With actual customer evidence, the benchmark and the pinned business criteria must be redesigned and reviewed independently; do not import real personal/insurance claim data into this demo. Legal requirements require current primary sources and qualified review.

## Audit preservation and known gaps

- R0/R1 code, E2B stdout/stderr, attempts, diffs, approval records and report ZIP continue to be persisted under `./artifacts/` (local bind mount).
- **The independent R1 KPI gate is shown separately from the model's requirement diagnostic quality gate.** An ODA HOLD must not falsely label successful R1 E2B code as a failed technical implementation.
- The predeclared R1 contract and independent evaluator are deliberately not generated by ODA. Therefore, positive R1 KPIs do not prove ODA contributed to the improvement. A full intervention/ablation study would need to permit distinct, independently reviewed proposals to cause different implementations.
- Benchmark fixtures and deterministic rubric are intentionally small; generalization to real insurance operations is **UNVERIFIED**.
- Lexical detection covers documented contradictions but cannot prove logical correctness of unrestricted natural-language proposals. The schema-based criterion is more reliable than inferring conclusions from prose, but it can still be gamed or mis-specified.
- The test suite mocks Ollama and E2B; Qwen/ODA generation on the user's Mac and the frontend production build must be independently checked.
