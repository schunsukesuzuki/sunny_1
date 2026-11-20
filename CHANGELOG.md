# Changelog

## v0.6 — service design and requirement refinement outer loop

- Structured, editable `ServiceDesign` between requirement drafting and code generation.
- Deterministic requirement-assessment gate separate from implementation validity. No business GO from synthetic proxy.
- Human-reviewed customer-evidence ledger with provenance and per-acceptance-criterion findings.
- `/api/refine` proposes an outer-loop requirement revision using DEV diagnostics only; human approval is required in UI.
- Revision lineage (`parent_run_id`, `requirements_revision`), disjoint holdout seed blocks per revision, design/evidence hashes and audit artifacts.
- EU InsurTech scenario documented as conceptual (NOT benchmark-validated); preserved educational v0.5 benchmark.
- v0.5 functional repair and quality holdout contract maintained; backend mocked tests added.


## v0.5 — strict selection, staged diagnosis and scoped repair

- **NO VALID CANDIDATE => NO SELECTION**: no longer selects the final invalid attempt merely because all revisions fail. The response explicitly reports `selected_attempt_index: null` and `holdout_executed: false`; `generated.py` is NOT saved as an accepted candidate.
- **Skip HOLDOUT**: when all DEV attempts are functionally invalid, skip all final-reference and generated-code E2B Sandboxes. Preserve development references and logs; show DEV-only plan examples explicitly labelled as such.
- **Staged functional repair**: first failed attempt produces structured validator categories, deduplicated examples and a precise output contract. After another functional failure, the repair feedback escalates to explicit state invariants and conservative AST-based diagnostic hints.
- **Function-scoped patching**: functional repair at revision 2+ requests `allocate_hours` alone, and applies it structurally with AST ranges. The original main function, imports and other functions remain untouched. Malformed patches are rejected and logged, rather than silently accepted.
- **Code audit trail**: `repair_strategy`, `error_summary` and a bounded unified `code_diff` for each revision; `.diff` files saved alongside individual sources and attempt JSON.
- **Quality HOLD refinement** and DEV/HOLDOUT separation remain as in v0.4. The selected code, if any, is the best functionally passing DEV code; even then, HOLDOUT is run only once and never fed to Qwen.
- Compose host API port remains `18000` (configurable) to avoid the previous `8000` conflict; native macOS Ollama + Metal architecture unchanged.

## v0.4

- Development-quality refinement loop on HOLD, best valid DEV selection, separated held-out evaluation, student schedule visualisations.

## v0.3

- Functional NO-GO bounded retries with E2B validation evidence.

## v0.2

- Three-algorithm comparison, multi-seed assessment, functional and adoption gates.
