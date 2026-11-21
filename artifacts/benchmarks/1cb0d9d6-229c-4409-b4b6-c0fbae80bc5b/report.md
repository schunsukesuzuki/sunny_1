# Claims Operations Planner v0.21 — Diagnostic Benchmark

> **合成フィクスチャの独立採点です。実顧客要件の正しさ・EU規制適合性を検証しません。**

- Benchmark ID: `1cb0d9d6-229c-4409-b4b6-c0fbae80bc5b`
- Date: 2026-11-21T07:27:29+00:00
- Fixtures: `CLAIMS-DIAG-FIXTURES-v0.10.1` / Rubric: `DIAG-RUBRIC-v0.10.1`
- Cases: fifo_sla_conflict, actual_fifo_implementation_bug / Repetitions: 1
- 両モデルは同じ入力・同じスキーマ・同じ推論パラメータです。出力・独立評価は別々に記録します。
- 初回結果と修復後の結果を別々に報告します。修復フィードバックには隠された正解ラベルを使用しません。

| Model | completed | overall rubric PASS | mean criterion score |
|---|---:|---:|---:|
|coding|2|1|0.9375|
|finance|2|1|0.75|

## Trial-level evidence

| case | repetition | model | classification | result | score | failures |
|---|---:|---|---|---|---:|---|
|fifo_sla_conflict|0|coding|requirement_mismatch|COMPLETED|1.0|—|
|fifo_sla_conflict|0|finance|insufficient_evidence|COMPLETED|0.5|CAUSE_CLASSIFICATION, IMPLEMENTATION_CORRECTNESS, SYNTHETIC_BUSINESS_FIT, REVISION_TARGETS_REQUIREMENT|
|actual_fifo_implementation_bug|0|coding|implementation_bug|COMPLETED|0.875|REVISION_TARGETS_REQUIREMENT|
|actual_fifo_implementation_bug|0|finance|implementation_bug|COMPLETED|1.0|—|

## Initial vs post-revision PASS

| model | initial PASS | post-revision PASS | revised calls |
|---|---:|---:|---:|
|coding|0|1|2|
|finance|1|1|1|

## Fresh blind generalization (initial calls only)

These additional seeded synthetic cases receive no feedback or revisions.
| model | passed | completed | planned |
|---|---:|---:|---:|
|coding|0|2|2|
|finance|0|2|2|

## Interpretation

- 分類だけでは合格しません。説明・改訂案・証拠ID・実装判定を独立採点します。
- 同一アーキテクチャでもモデル差以外に量子化、ランダム性、応答形式の差が残ります。
- 語句に基づく矛盾検出は限定的で、意味論的な証明ではありません。
- 正解ラベルはモデル入力へ渡していません。市場と顧客による検証はUNVERIFIEDのままです。
- 各試行の診断JSON、根拠、エラー、ハッシュは同梱証跡ZIPから取得できます。
