# v0.20 — Claims Allocation Skill / reproducible E2B comparison

## Rationale

In v0.19, valid DEV KPI alone did not ensure that Qwen's selected program
preserved the only qualified specialist's available hours. The repair attempts
repeated that failure. A hard constraint validator also cannot itself infer
whether the scheduling *strategy* handles an edge case. The application now
makes such scheduling know-how a first-class, independently auditable, **app-
specific Domain Skill**.

The design explicitly separates:

1. **Evidence and requirements**: public third-party problem context, human
   hypothesis approval, claim-assignment vs progress-notification feature.
2. **Policy strategy**: Qwen-generated R1 code *or* pinned Domain Skill.
3. **Execution**: each candidate executed in an E2B sandbox, no internet.
4. **Independent grading**: `app.domain.validate`, `app.policy_validation`,
   and `app.dev_selection`, all outside `skills/`.
5. **Decision**: DEV-only gate then untouched HOLDOUT. This is synthetic proof
   of tested examples, not a formal or external business guarantee.

## Modes

| `r1_mode` | What gets executed | Can use LLM for R1 code? | Notes |
|---|---|---|---|
| `llm_only` | Qwen candidate + up to 2 DEV repairs | YES | v0.19 behavior |
| `skill_only` | Pinned `skill_deadline_scarcity` and `skill_bounded_beam` | NO | No Qwen `generate` for R1; prior Qwen/ODA diagnosis remains |
| `compare` (default in Step 10) | LLM candidates + both Skill candidates | YES | Independent, no Skill results in repair prompts |

The standalone `/api/evaluate-r1` remains backward-compatible, defaulting to
`llm_only`. The `compare` button in the UI and `/api/full-run/start` default
to `compare` when no mode is supplied.

### Domain Skill components

```
backend/skills/claims_allocation/
    SKILL.md
    schemas.py       # bounded input validation
    priority.py      # deadline, reviewer supply, duration, priority
    feasibility.py   # skill+capacity feasible reviewer-days
    scarcity.py      # deterministic reservation penalty
    optimizer.py     # greedy and bounded-beam heuristics
    validators.py    # internal output partition sanity only
    runner.py        # only registered strategy dispatcher
    bundle.py        # immutable scripts for E2B + content manifest
```

Two strategies intentionally remain inspectable and run without external
optimization packages. `bounded_beam` is a **bounded heuristic**, not an exact
MIP or min-cost-flow solver and not a certificate of optimality. Cases are
unsplittable multi-hour jobs; a naive per-hour flow would be invalid.

The `bundle.py` materializes complete self-contained Python scripts containing
source snapshots of the reviewed components, not an LLM-composed list of
arbitrary functions. The scripts read `/home/user/input.json`, write
`/home/user/output.json`, and are run by the existing E2B executor. These
sources do *not* import the independent grading code.

### DEV / HOLDOUT protocol

- DEV datasets: three seeds `seed+100..102`;
- DEV policy cases: fixed 900001 deadline probe, 900002 scarce specialist;
- DEV stress: four pinned scenarios (capacity, skill, deadlines, arrivals);
- Only candidates passing **all** existing DEV gates are eligible;
- If more than one eligible: lowest total DEV missed-deadlines wins; ties retain
  existing LLM candidate or first pinned Skill (predeclared order);
- HOLDOUT: `seed+20000` and `seed+20001`, evaluated **after selection**;
- When `compare`, additional DEV-eligible comparators may be separately run
  on the same held-out seeds *after selection*, without changing the selection.
- No HOLDOUT metrics, Skill results, or comparator scores are included in LLM
  DEV repair prompts. A failed candidate must not be silently reported as
  a successful model repair.

Both candidate algorithms and the fixed deadline heuristic are independently
graded using `domain.validate`. That heuristic is a useful reference, but not
an exact optimality oracle; gate strictness is a *design decision for this
synthetic fixture*.

### Audit artifacts

```
experiments/<id>/
    experiment.json                # selected_engine, source_provenance, KPI, modes
    execution_mode.json
    skill_manifest.json            # files/strategies with SHA256
    skill_component_*.py           # complete reviewed source snapshots
    skill_deadline_scarcity.py
    skill_bounded_beam.py
    skill_*_dev_gate.json
    skill_dev_*_seed_*.json        # raw E2B execution metadata
    dev_selection_audit.json       # separate LLM / Skill gate reasons
    selected_r1.py                # actual code executed on HOLDOUT
    holdout_*.json
    holdout_comparators.json       # ONLY when other DEV-eligible candidates exist
    report.md
```

`selected_engine` and `selected_source_provenance` distinguish generated R1
source from the pinned Skill. Business assessment explicitly preserves that
label. `technical_closed_loop_demonstrated` can be true only if the **LLM**
source was selected and the other conditions are met. A Skill-selected
candidate may pass synthetic KPIs without establishing model-driven synthesis.

E2B command elapsed times are recorded but **do not** include model inference,
network, developer time, or monetary charges; no invented API billing or token
usage is reported. This is not a multi-tenant secured software product.

## Example API inputs

```json
{
  "evidence_mode": "public",
  "r1_mode": "compare",
  "dataset_id": "insurance_claims_uk",
  "evidence_query": "insurance claim delays complaint handling",
  "llm_extraction": false,
  "brief": "Your synthetic insurance claims demo brief at least 20 characters",
  "seed": 42
}
```

Endpoint: `POST /api/full-run/start`; human review required at 00b and 05.
To inspect the pinned code manifest: `GET /api/skills/claims-allocation`.
Use `GET /api/full-run/{id}/bundle` for the export ZIP.

**Public problem context does not imply assignment-scheduling is the cause or
solution.** The independent progress-notification prototype stays separate;
Skill performance cannot be reported as acceptance of a notification feature.

## Tests and limitations

- Back-end tests exercise both local strategies, real standalone Python via
  a local subprocess, edge-case fixtures, and mocked E2B integration.
- The local subprocess checks the E2B script text but is **not** an E2B
  sandbox security test.
- Real E2B SDK, real Ollama, public dataset network access, Docker Compose,
  and React full build require validation in the deployment environment.
- Customer-specific data, authorization, pricing, causal explanation, and
  production operating requirements remain **UNVERIFIED**.
