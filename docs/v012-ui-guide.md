# v0.12 — UI explanation and light theme

This release is a **frontend-only usability update** built on v0.10. Backend business logic, synthetic fixtures, model selection, E2B runner, verifier, HOLD approval, benchmark and evidence ZIP routes remain unchanged.

## Purpose shown to users

The app is a **technical presales research demonstration** for a fictional German InsurTech claims-operations vendor. It turns a customer problem into structured service design, compares FIFO with deadline-aware allocation, runs code in E2B, checks constraints on held-out synthetic data, and captures reviews and audit artifacts. It **does not** automate claim payment decisions, prove customer value, establish market viability, or certify EU regulatory compliance.

## Existing screen capabilities (unchanged)

1. Editable fictional customer brief, seed and business goals.
2. Service-design intermediate representation from the LLM or fixed template.
3. R0/FIFO E2B execution and deterministic specification tests.
4. Independent Qwen/ODA diagnoses against the same DEV data and synthetic evidence.
5. Human approval or hold review for predeclared R1 contract.
6. R1 code generation, attempted DEV repair and isolated HOLDOUT validation.
7. Stored experiment/diagnostic records, reports and downloadable evidence ZIPs.
8. Diagnostic-quality benchmark and non-destructive rescore.

## The three different checks

| Check | Question | What current demo proves |
|---|---|---|
| Evidence-ID correctness | Does an identifier point to a supplied record? | Limited matching/traceability on synthetic fixtures; e.g., `SIM-SLA-001` is app-defined, not an external source. |
| Evidence validity | Is the underlying record authentic, complete, relevant and representative? | Not proven: all customer examples are simulated. |
| Diagnostic correctness | Does the conclusion follow logically from the evidence and the specification? | Partially checked by deterministic rubrics/constraints; no general semantic or formal proof. |

## Presentation

Soft sage background, off-white surfaces, gentle borders and dark slate text; blue-green accents, amber HOLD banners, green PASS labels. Inputs, links, textareas, code/pre, and focus states use light styles and preserve readable contrast. Mobile layout collapses feature/evidence cards to a single column. The theme is static light mode; it does not depend on OS dark-mode preferences.

## Running and validation

Use the v0.10 setup: `bash scripts/setup-env.sh`, then configure `.env` including `E2B_API_KEY` and run `docker compose up --build` at `http://localhost:5173`. Reuse your existing `.env` and `artifacts/` after extracting this ZIP into its own folder. No credentials are included.
