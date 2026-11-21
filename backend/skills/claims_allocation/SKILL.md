# Claims Allocation Domain Skill — v0.20

Use only after a human has approved **the synthetic assignment experiment**. This
skill is an application-specific, pre-reviewed deterministic capability for
scheduling reviewer work. It does **not** certify a customer's requirements.

- `schemas.py`: bounded input/output assumptions.
- `priority.py`: deadline, number of qualified reviewers, work duration, priority.
- `feasibility.py`: qualification and per-reviewer/day hard-capacity feasibility.
- `scarcity.py`: protect the capacity of sole specialists.
- `optimizer.py`: a deterministic greedy heuristic and bounded beam search.
- `validators.py`: internal output-partition assertions, NOT independent testing.
- `runner.py`: registered strategies, no arbitrary code execution.
- `bundle.py`: self-contained, content-hashed E2B source assembly.

Evaluation MUST use the separate `app.domain.validate` and `app.policy_validation`
modules, the pinned DEV/HOLDOUT seeds, and human approval. R0/R1 reference code
is an *independent comparator*, not a proof of mathematical optimality.

**Modes:** `llm_only`, `skill_only`, `compare`. In compare mode neither the
skill's metrics nor HOLDOUT are fed into Qwen's repair prompts. Only DEV selects
candidates; HOLDOUT is for post-selection verification. Explicitly label
pinned Skill candidates as **non-LLM-generated**.

The bounded beam strategy is **not an exact MILP/min-cost-flow solver**. The
current input schema has unsplittable cases with hours per reviewer-day; a
naive per-hour flow network would break that constraint.
