# Claims Operations Planner v0.13 — Diagnostic Benchmark

> **合成フィクスチャの独立採点です。実顧客要件の正しさ・EU規制適合性を検証しません。**

- Benchmark ID: `7eb3d37c-c456-4bb8-96d3-22a445626c72`
- Date: 2026-11-21T03:27:49+00:00
- Fixtures: `CLAIMS-DIAG-FIXTURES-v0.10.1` / Rubric: `DIAG-RUBRIC-v0.10.1`
- Cases: fifo_sla_conflict, actual_fifo_implementation_bug / Repetitions: 1
- 両モデルは同じ入力・同じスキーマ・同じ推論パラメータです。出力・独立評価は別々に記録します。

| Model | completed | overall rubric PASS | mean criterion score |
|---|---:|---:|---:|
|coding|2|0|0.8125|
|finance|2|0|0.8125|

## Trial-level evidence

| case | repetition | model | classification | result | score | failures |
|---|---:|---|---|---|---:|---|
|fifo_sla_conflict|0|coding|implementation_bug|COMPLETED|0.75|CAUSE_CLASSIFICATION, EVIDENCE_TRACEABILITY|
|fifo_sla_conflict|0|finance|requirement_mismatch|COMPLETED|0.875|IMPLEMENTATION_CORRECTNESS|
|actual_fifo_implementation_bug|0|coding|implementation_bug|COMPLETED|0.875|SYNTHETIC_BUSINESS_FIT|
|actual_fifo_implementation_bug|0|finance|implementation_bug|COMPLETED|0.75|SYNTHETIC_BUSINESS_FIT, REVISION_TARGETS_REQUIREMENT|

## Interpretation

- 分類だけでは合格しません。説明・改訂案・証拠ID・実装判定を独立採点します。
- 同一アーキテクチャでもモデル差以外に量子化、ランダム性、応答形式の差が残ります。
- 語句に基づく矛盾検出は限定的で、意味論的な証明ではありません。
- 正解ラベルはモデル入力へ渡していません。市場と顧客による検証はUNVERIFIEDのままです。
- 各試行の診断JSON、根拠、エラー、ハッシュは同梱証跡ZIPから取得できます。
