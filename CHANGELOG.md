# Changelog

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
