# Changelog

## v0.15 — 01–09 full-run workflow with explicit human review and single ZIP

- Replace UI step 10 with a complete 01–09 execution path, starting from a new brief and seed rather than requiring a preexisting R1 experiment.
- Save 01 input and 02 generated service design, R0 E2B, proposal diagnosis, explicit 05 human decision, R1 generation/evaluation, history snapshot, model diagnostic benchmark, behavior/stress verification and two-axis business assessment.
- Pause at 05 for manual review; ODA HOLD requires existing signed-off override safeguards. Never auto-approve or relabel HOLD as PASS.
- FastAPI background tasks plus polling and saved Workflow ID; export a partial ZIP even on rejection or stage errors. The final ZIP contains a manifest, raw-byte SHA256 for included files and clear missing/pending stages.
- Keep the v0.14 pipeline API for backward compatibility, but the step 10 UI uses the new full workflow.
- Add offline integration tests for human gate, rejection, manual HOLD override, failed R0 and archive checksum integrity.


## v0.14 — Behavioral policy checks, stress coverage, one-click complete export

- Add independent, predeclared R1 contract behavioral probes for deadline priority and scarce-qualified-reviewer preservation, executed **after** the original R1 candidate selection with E2B. The old KPI result is preserved and not relabeled as semantic PASS.
- Add four synthetic stress cases: capacity pressure, skill bottleneck, deadline compression, and arrival reorder; always report missed (including unassigned), unassigned and allocated scheduled hours. A fixed heuristic is a comparator, not an optimizer/proof.
- Update two-axis assessment with AI-07/AI-08, E06/E07, separate single-case diagnosis from completed Qwen/ODA benchmark, and require behavioral+stress evidence for limited customer discovery GO. Never return production GO.
- Add step 10 **Run & Save**: runs policy/stress, Qwen/ODA diagnosis benchmark, assessment, exports one single complete/partial evidence ZIP with `00_START_HERE.md` and `manifest.json`, raw-byte SHA256, explicit missing/excluded/stage-failure records. Does not auto-approve R1 or rewrite historical source records.
- Includes six new offline tests (including full archive checksum verification and failed-E2B partial export); old presales tests updated for stricter v0.14 decisions. All operations are based on synthetic data and/or mock E2B/LLM in tests.


## v0.13 — Evidence-linked two-axis presales decision report

- Add fixed **Business Value & Feasibility** (5 criteria) and **AI Delivery & Operational Readiness** (6 criteria) rubric for stored R1 experiments.
- Add a new step **09** to the calm-light React UI: generate/inspect business assessment; download Markdown and linked evidence ZIP; support archived R1 experiment IDs and saved assessments.
- Keep Qwen/ODA diagnoses and human-override states separate: no LLM re-scoring or third-party customer claims are invented.
- Decision policy: limited **GO for customer discovery** if synthetic constraints and code hash pass; otherwise technical **HOLD**. Always **NO-GO for production** without independent customer, operations and regulatory evidence.
- Persist `assessment.json` / `report.md`, source hashes, evidence registry E01–E05, uncertainties and next verification actions. Extend history/artifact APIs to `assessments` and bundle the linked R0/proposal/approval/experiment records.
- Preserve all v0.12 functionality; add six automated tests and a new documentation guide.
- Interviewer names or affiliations are absent from the assessment report and there is no assessment LLM prompt.

## v0.12 — Guided light UI and evidence-evaluation transparency

- Add a read-first Japanese app overview and feature map for existing steps 01–08.
- Explicitly separate evidence-ID traceability, evidence validity, and diagnostic correctness, with `SIM-SLA-001` identified as a synthetic app-defined ID.
- Replace all frontend dark colors with a muted, eye-friendly light palette, including buttons, inputs, code blocks, status chips, notices, and responsive layout.
- Keep all v0.10 backend logic, API endpoints, model routes, evaluation contracts, history, and ZIP exports unchanged.
- Make the default human-HOLD review note neutral rather than presupposing a missing ODA evidence ID; human reviewer still enters/approves the actual rationale.
- Update frontend version/title and document the UI changes.

## v0.10 — Diagnostic quality & independent multi-case benchmark

- Preserve v0.9.1 Claims Operations Planner R0→R1 with human HOLD review, E2B, generated code and audit ZIP.
- Add independent multi-axis scoring for BOTH Qwen and ODA diagnoses; classification alone cannot pass if the explanation or policy is contradictory.
- Distinguish synthetic business-requirement mismatch from unverified real-customer validity.
- Detect known strict-FIFO + deadline-first contradiction, invented/missing evidence IDs and false R0 implementation bug allegations.
- Add four synthetic fixed-oracle diagnostic cases, identical structured schema/prompt for both models, sequential 1–3 trials, reports and complete evidence archives.
- Add read-only rescoring of historical v0.9.1 proposals without rewriting previous human approvals/diagnostic status.
- Guard a known stale human HOLD rationale when ODA says `correct` but a note claims it said `incorrect`.
- Separate independent R1 KPI PASS from end-to-end automated-diagnosis PASS in the Markdown report.
- Add step 08 to React UI; restore all download/history functionality, extend history to benchmark records.
- No EU insurance regulation retrieval or new domain evaluator beyond the predeclared synthetic tasks; domain correctness remains unverified externally.

## 0.9.1 — 2026-11-21
- ODA-Fin-RL-8B診断がHOLDのままでも、独立R0 PASSを確認した人間の審査記録によって固定R1の技術検証に進める経路を追加。
- モデル診断の合否と、新HOLDOUT上のR1技術KPI改善を別の状態として保存。
- HOLD時、誤ったODA診断をQwenの「承認済み診断」として流用せず、人間の審査根拠のみを使用。
- 承認者、HOLD理由、独立R0 PASS確認、承認日時を監査ログに記録。
- モック結合テストと却下経路の回帰テストを追加。

# Changelog

## v0.9 — Finance-domain Vertical FM + restored audit artifacts

- ODA-Fin-RL-8B via Ollama (separate from Qwen3-Coder), independent structured diagnosis and root-cause consistency rubric.
- Two model responses shown and persisted, ODA review passed to Qwen coding stage as advisory context after human approval.
- Domain gate rejects the false diagnosis “FIFO implementation bug” if R0 already passed independent specification tests.
- Preserves per-attempt code, diffs, metrics, stdout/stderr (truncated), and outputs; restored ZIP evidence bundles and history UI.
- Logs model connection failures and E2B initialization failures; no fake fallback. All EU insurance client/regulatory validity remains unverified.
- Adds independent model-routing / regression tests, macOS Ollama setup instructions.

## v0.8 — German InsurTech Claims Operations Planner

- Replaced education-specific task and evaluator with claims assignment simulation, separate R0/R1 requirement loops and deadline KPI.
