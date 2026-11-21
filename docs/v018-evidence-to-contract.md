# v0.18 — Evidence-grounded Requirements: topic safety and bounded evaluation

## Problem and safety boundary

In v0.17 a banking interview excerpt about online preferences could be attached to a synthetic insurance-claims FIFO/R1 experiment without any issue alignment. Public source existence is not evidence of the **particular client's** claims queue process. The new gate prevents that.

## Modes and dataset downloads

The user chooses `public` or `synthetic`. `public` defaults to `insurance_claims_uk` (three HTML publications downloaded from fixed, HTTPS, allowlisted FCA/FOS URLs). `community_credit` and `cfpb_sample` remain individually downloadable and searchable; neither can authorize insurance claims execution. Each source has a filename, source URL and downloaded raw-byte SHA256. The single ZIP contains `00_raw_source__*`, `00_source_manifest.json`, RAG results, and reports. The UI still offers a separate dataset-only ZIP. **HTML offsets refer to text extracted locally, not byte offsets in the HTML file**.

## 00 / 00b domain gate

- Extraction is BM25 + character trigram/RRF, **not a dense neural retrieval system**. Evidence is untrusted input.
- Conservative insurance lexical screening identifies a *topic match* only, never logical entailment, causation, approval, regulation or German market transferability.
- `DOMAIN_MISMATCH` / `INSUFFICIENT_TOPIC_EVIDENCE` / `OUT_OF_SCOPE` blocks 00b approval and stops prior to 01. Only a selected topic-related citation may be used.
- Human must explicitly mark the selected excerpt as supporting **problem context only**, provide rationale and write a domain-aligned hypothesis; choosing `context_only` or `contradicts` does not authorize continuation.
- Additional retrieval searches for potential competing issues (communication, external assessors, etc.) without claiming exhaustive counter-evidence coverage.
- Any human judgment may still be wrong; automatic meaningful support verification does not exist yet.

## 00c — Explicit bounded test contract

The reviewer sets maximum total missed deadlines (including unassigned), minimum improvement over FIFO percentage, and whether behavioral probes must pass. These are immutable run parameters recorded in `00c_grounded_test_contract.json` and `00c_technical_spec.md`. They **do not alter the R0/R1 reference contracts or generated candidate source**. The compiler explicitly supports only one technical domain: `insurance_claims` and one available measurable KPI: `missed_deadlines_including_unassigned`. No arbitrary customer statement, policy, or evaluator code is executed.

## 08c / 09 — Independent synthetic evaluation and reporting

After existing E2B evaluation, 08c checks held-out seeds, equivalent planned assigned hours, numeric validity, user-selected thresholds and optional behavior probes against frozen synthetic results. A failed behavioral test remains HOLD even if deadlines improve. `08c_grounded_kpi_verification.json` is a **separate synthetic result**, not a confirmation of published customer complaints or of the inferred solution.

`09` adds `E08` pointing to published context, `BV-06` distinguishing context from customer fit, `AI-09` distinguishing configured synthetic KPI compliance from validated requirements, and corrects E05 to mean **no customer-specific operational/ROI/legal evidence**, not 'no external document'. Production remains NO-GO.

## Workflows and outputs

1. Public mode: 00 download or verify, index, retrieval and source-citation snapshots.
2. 00b: inspect citation source and problem domain, human approves or rejects contextual problem hypothesis.
3. 00c: save bounded human KPI test contract before 01.
4. 01–04: synthetic service design, E2B R0 and two LLM diagnostics.
5. 05: independent human approval for R0→R1 experiment.
6. 06–08b: E2B, held-out synthetic scoring, quality benchmark, behavioral and stress tests.
7. 08c: check human KPI thresholds deterministically.
8. 09: evidence-qualified business/delivery assessment; one ZIP with manifest and sources.

Synthetic-only mode keeps 01–09 as a regression benchmark; explicitly labels 00/00b/00c/08c as skipped. The pipeline never silently switches from public to synthetic after public acquisition errors.

## Known limits and real-data next steps

- **No general-purpose semantic proof, cross-domain evaluation, or automatically generated oracle.** Natural language may be ambiguously related to passages even after the lexical topic gate.
- FCA/FOS examples concern UK insurance complaints, not a specific German SaaS customer's validated requirements. Public complaint context does not establish FIFO as a cause.
- Human-entered KPI bounds and synthetic code cannot establish customer value. Real claims timing distributions, service-level definitions, reviewer skills, sampling bias, GDPR and legal approvals are out of scope.
- Public download can fail due to websites changing or being inaccessible. The workflow stops `PARTIAL`; it does not invent a dataset or switch to a synthetic success.
