# Claims Operations Planner v0.21.2 — Diagnostic Benchmark

> **合成フィクスチャの独立採点です。実顧客要件の正しさ・EU規制適合性を検証しません。**

- Benchmark ID: `5b5eaefd-7dc6-413d-a7e2-7627d7c0bb27`
- Date: 2026-11-21T11:23:57+00:00
- Fixtures: `CLAIMS-DIAG-FIXTURES-v0.10.1` / Rubric: `DIAG-RUBRIC-v0.10.1`
- Cases: fifo_sla_conflict, actual_fifo_implementation_bug / Repetitions: 1
- 両モデルは同じ入力・同じスキーマ・同じ推論パラメータです。出力・独立評価は別々に記録します。
- 入力だけから作ったFact Sheetを両モデルへ渡し、独立実装テストと合成事業KPIを区別して読ませます。
- 初回結果と修復後の結果を別々に報告します。修復フィードバックには隠された正解ラベルを使用しません。

| Model | completed | overall rubric PASS | mean criterion score |
|---|---:|---:|---:|
|coding|2|0|0.875|
|finance|2|0|0.6875|

## Trial-level evidence

| case | repetition | model | classification | result | score | failures |
|---|---:|---|---|---|---:|---|
|fifo_sla_conflict|0|coding|requirement_mismatch|COMPLETED|0.875|REVISION_TARGETS_REQUIREMENT|
|fifo_sla_conflict|0|finance|insufficient_evidence|COMPLETED|0.625|CAUSE_CLASSIFICATION, SYNTHETIC_BUSINESS_FIT, REVISION_TARGETS_REQUIREMENT|
|actual_fifo_implementation_bug|0|coding|implementation_bug|COMPLETED|0.875|SYNTHETIC_BUSINESS_FIT|
|actual_fifo_implementation_bug|0|finance|implementation_bug|COMPLETED|0.75|SYNTHETIC_BUSINESS_FIT, REVISION_TARGETS_REQUIREMENT|

## Model raw inference vs audited harness assistance

**Raw PASS is the model's own prediction. Assisted PASS includes deterministic citation binding and MUST NOT be described as model-only accuracy.**

| model | initial raw PASS | final raw PASS | initial assisted PASS | final assisted PASS | revision calls | citations bound |
|---|---:|---:|---:|---:|---:|---:|
|coding|0|0|0|0|2|0|
|finance|0|0|0|0|2|0|

## Fresh blind generalization (initial calls only)

These additional seeded synthetic cases receive no feedback or revisions.
| model | raw PASS | assisted PASS | grounded | completed | planned |
|---|---:|---:|---:|---:|---:|
|coding|0|0|0|2|2|
|finance|1|1|0|2|2|

## Interpretation

- 生回答・根拠ID補完後・再診断後を別々に保存。補完後PASSはモデル単独PASSではありません。
- 元入力の単一証拠IDのみ、説明と整合するときに補助付与。欠落ID以外の診断・改訂方針は自動修正しません。
- 分類だけでは合格しません。説明・改訂案・証拠ID・実装判定を独立採点します。
- 同一アーキテクチャでもモデル差以外に量子化、ランダム性、応答形式の差が残ります。
- 語句に基づく矛盾検出は限定的で、意味論的な証明ではありません。
- 正解ラベルはモデル入力へ渡していません。市場と顧客による検証はUNVERIFIEDのままです。
- 各試行の診断JSON、根拠、エラー、ハッシュは同梱証跡ZIPから取得できます。
