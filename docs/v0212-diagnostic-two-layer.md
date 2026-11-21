# v0.21.2 — Input-fact protocol and independent diagnostic evaluation

## Why

In the prior user's v0.21 full-run archive (`AUDIT-EXPORT-v0.21.0`), Qwen had **0/2 raw Fresh Blind PASS** even though the classification and implementation judgments were correct: both answers omitted a single available evidence ID. ODA also had 0/2 but included substantive errors (business vs implementation judgment; unnecessary requirement change). These are different failure modes. We must not transform evidence repair into a false claim of improved LLM inference.

## What changed

1. `observable_fact_sheet` is derived ONLY from each diagnostic input. It reports the independent PASS/FAIL text, contract, KPI comparison, available evidence and customer interview count. It includes no hidden fixture labels or answer keys. Both Qwen and ODA receive the same sheet plus original input.
2. The prompt asks for three explicit checks: code-vs-contract, specification-vs-observed business outcome, and only then cause/requirements decision. Real-world absence of customer interviews does NOT negate a synthetic comparison, but a synthetic comparison is NOT customer proof.
3. `evidence_bind_from_input` is optional deterministic *harness assistance*, not a model inference. It can add precisely one uncited ID if the single input evidence observation and the model's own valid class + implementation status + description agree. It will not repair invalid IDs, ambiguous/absent evidence, incorrect class, wrong implementation status, unjustified requirement rewrites, or unsupported outcomes. Source ID and source observation are stored.
4. Audit scores:

| Metric | Meaning |
|---|---|
| `initial_rubric` | Unmodified first LLM response, evaluated by original rubric |
| `assisted_initial_rubric` | First answer with labeled deterministic evidence binding |
| `latest_raw_rubric` | Last actual model response (before any binding) |
| `rubric` | Last assisted answer, full unchanged rubric |
| `raw_initial_passed` | Number of raw first-call successes |
| `raw_final_passed` | Number of raw successes after optional model revision |
| `assisted_final_passed` | Number of successes allowing traceable harness help |
| `blind_generalization.summary[*].passed` | Raw Fresh Blind PASS: no revisions or postprocessing counted |
| `blind_generalization.summary[*].assisted_passed` | Fresh Blind with citation helper, explicitly attributed to harness |

An existing `passed` key is retained for compatibility and means final assisted result for the selected fixtures, **not model-only correctness**. The business assessment uses `raw_final_passed` and the raw blind `passed` for its automatic LLM diagnostic quality gate.

## Non-leakage policy

- Benchmark oracle remains in evaluator and exported local audit bundle only; neither initial LLM request nor revision request includes it.
- The binder reads only payload + prediction, never oracle or rubric failures. Only source-backed IDs can be appended; no labels or requirements are substituted.
- Fresh Blind gets no repair roundtrip; its raw answers are immutable and its assisted scores are displayed separately.
- Previously observed blind answers replayed in development are regression examples, not counted as fresh generalization. New runs use newly sampled, non-revised cases; the distribution is still synthetic and narrow.

## Measured historical replay (not new model results)

Rerunning the v0.21.0 stored Fresh Blind **responses** through the v0.21.2 deterministic binder (no LLM calls): Qwen raw 0/2, assisted 2/2; ODA raw 0/2, assisted 0/2. This demonstrates a citation-format problem in Qwen's prior outputs, **not model generalization** and not a solution to ODA's semantic errors. A real run with Qwen/ODA in Ollama is necessary to determine new model-only PASS rates.

## Run / debug

```bash
bash scripts/setup-env.sh
# set E2B_API_KEY and ensure both Ollama models exist
docker compose up --build
```

After step 08, inspect the workflow's benchmark `benchmark.json` or `report.md` and compare raw and assisted pass counts. `trial_*.json` includes raw `initial_diagnosis`, `latest_raw_diagnosis`, `initial_grounding`, optional `revised_grounding`, and corresponding rubrics. The full-run audit ZIP includes these artifacts. The `00b` reviewed-requirement workflow remains unchanged.

**Limitations:** Fact sheets do not independently confirm the truth of external sources. Lexical ID support is a conservative traceability aid, not semantic proof. The fixed synthetic fixtures are not a representative real-world insurance requirement benchmark. **We cannot promise that ODA or Qwen will pass on a new run.**
