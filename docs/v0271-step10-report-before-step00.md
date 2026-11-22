# v0.27.1 — Step 10 and report ahead of 00

## Requested UI order

**10 (full workflow) → 10R (report only for COMPLETE/PARTIAL) → 00 (manual evidence tools) → 01–09**.

The 10R report is a **sibling section**, not nested within Step 10. It appears automatically after a run completes (including partial completion) and after a saved Workflow ID is loaded. For RUNNING / AWAITING_EVIDENCE_REVIEW / AWAITING_APPROVAL, no final report is displayed. The existing `GET /api/full-run/{workflow_id}/report` is used without invoking an LLM, Dogwood or sandbox. Stale report guards compare Workflow ID and updated_at and allow a manual reload when fetch fails.

Step 10 now directly exposes the previously 00-only dataset selector, query and Qwen extraction option. Both sections use the same React state; changing one updates the other. The 00 panel remains available for manual evidence acquisition/indexing/search.

## Checks

- `cd frontend && npm run verify:layout`: TS AST checks the direct siblings, exact ordering and report guards.
- `PYTHONPATH=backend python -m pytest -q backend/tests`: backend regression (152 tests in packaging environment).
- `cd frontend && npm run build`: requires installed React/Vite/TypeScript dependencies; not run in packaging environment.
- `docker compose build --no-cache api web && docker compose up -d --force-recreate`: requires Docker, Ollama and configured E2B as appropriate; not run in packaging environment.

This is a layout release. All policy, evaluation and export formats remain unchanged.
