# Claims Operations Planner v0.29 — Diagnostic Benchmark

> **合成フィクスチャの独立採点です。実顧客要件の正しさ・EU規制適合性を検証しません。**

- Benchmark ID: `7fb1dd86-9162-4f3d-a35d-c927829cb09f`
- Date: 2026-11-22T01:51:15+00:00
- Fixtures: `CLAIMS-DIAG-FIXTURES-v0.10.1` / Rubric: `DIAG-RUBRIC-v0.10.1`
- Cases: fifo_sla_conflict, actual_fifo_implementation_bug / Repetitions: 1
- 両モデルは同じ入力・同じスキーマ・同じ推論パラメータです。出力・独立評価は別々に記録します。
- 入力だけから作ったFact Sheetを両モデルへ渡し、独立実装テストと合成事業KPIを区別して読ませます。
- 初回結果と修復後の結果を別々に報告します。修復フィードバックには隠された正解ラベルを使用しません。

| Model | completed | overall rubric PASS | mean criterion score |
|---|---:|---:|---:|
|coding|2|0|0.875|
|finance|2|1|0.9375|

## Execution completeness (separate from answer quality)

- Status: **COMPLETED**
- INCOMPLETE_TIMEOUT is an inference failure, not an incorrect model answer.
- A user-triggered retry runs only unfinished model calls and never upgrades rubric failures.
- A retry on a previously exposed blind case is a **replay**, not independent fresh-blind evidence.

| model | timeouts | completed | planned | structural raw consistency |
|---|---:|---:|---:|---:|
|coding|0|2|2|1|
|finance|0|2|2|1|

## v0.29 RAW dimension-by-dimension audit

| group / model | cause | implementation | evidence | revision | requirement fit | cross-field |
|---|---|---|---|---|---|---|
|fixed_first_raw / coding|1/2 (HOLD)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|1/2 (HOLD)|1/2 (HOLD)|
|fixed_first_raw / finance|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|1/2 (HOLD)|
|fixed_latest_raw / coding|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|1/2 (HOLD)|0/2 (HOLD)|
|fixed_latest_raw / finance|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|1/2 (HOLD)|
|blind_raw / coding|1/2 (HOLD)|2/2 (PASS_SYNTHETIC)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|1/2 (HOLD)|1/2 (HOLD)|
|blind_raw / finance|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|2/2 (PASS_SYNTHETIC)|1/2 (HOLD)|

## v0.29 Input-only targeted repair audit

- Opt-in: **True**; repairs proposed: **2**; model calls: **2**; adopted: **2**
- Oracle rubric scores DO NOT trigger repairs. Only observable input/RAW inconsistencies select mutable fields.
- All edits outside selected fields are discarded. Blind trials receive no repair/feedback. RAW first-pass is immutable.

RAW axes are independent; a passing classification does not validate the revision. Blind replay is NOT fresh evidence. No production/legal certification.


## Trial-level evidence

| case | repetition | model | classification | result | score | failures |
|---|---:|---|---|---|---:|---|
|fifo_sla_conflict|0|coding|requirement_mismatch|COMPLETED|0.875|REVISION_TARGETS_REQUIREMENT|
|fifo_sla_conflict|0|finance|requirement_mismatch|COMPLETED|1.0|—|
|actual_fifo_implementation_bug|0|coding|implementation_bug|COMPLETED|0.875|SYNTHETIC_BUSINESS_FIT|
|actual_fifo_implementation_bug|0|finance|implementation_bug|COMPLETED|0.875|SYNTHETIC_BUSINESS_FIT|

## Model raw inference vs audited harness assistance

**Raw PASS is the model's own prediction. Assisted PASS includes deterministic citation binding and MUST NOT be described as model-only accuracy.**

| model | initial raw PASS | final raw PASS | initial assisted PASS | final assisted PASS | revision calls | citations bound |
|---|---:|---:|---:|---:|---:|---:|
|coding|0|0|0|0|1|0|
|finance|0|1|0|1|1|0|

## Fresh blind generalization (initial calls only)

These additional seeded synthetic cases receive no feedback or revisions.
| model | raw PASS | assisted PASS | grounded | completed | planned |
|---|---:|---:|---:|---:|---:|
|coding|0|0|0|2|2|
|finance|1|1|0|2|2|

## v0.29 raw diagnostic reliability gate

- Status: **HOLD_HUMAN_ADJUDICATION**
- Human adjudication required: **True**
- Prespecified criteria: Both models: >=2 fixed and >=2 fresh blind synthetic cases; all calls completed; 100% RAW rubric PASS and cross-field consistency. Replayed blind calls are not fresh.
- Quality failure codes: CODING_RAW_FIXED_DIAGNOSIS_FAILURE, CODING_RAW_BLIND_DIAGNOSIS_FAILURE, CODING_CROSS_FIELD_INCONSISTENCY, CODING_SEMANTIC_BOUNDARY_INCONSISTENCY, FINANCE_RAW_FIXED_DIAGNOSIS_FAILURE, FINANCE_RAW_BLIND_DIAGNOSIS_FAILURE, FINANCE_CROSS_FIELD_INCONSISTENCY, FINANCE_SEMANTIC_BOUNDARY_INCONSISTENCY
- Execution failure codes: None
- Raw test completion is distinct from synthetic R1 KPI; neither is production or legal validation.
- Semantic boundary: conservative RAW classification/evidence/revision checks; not a proof of natural-language truth.

## Interpretation

- 生回答・根拠ID補完後・再診断後を別々に保存。補完後PASSはモデル単独PASSではありません。
- 元入力の単一証拠IDのみ、説明と整合するときに補助付与。欠落ID以外の診断・改訂方針は自動修正しません。
- 分類だけでは合格しません。説明・改訂案・証拠ID・実装判定を独立採点します。
- 同一アーキテクチャでもモデル差以外に量子化、ランダム性、応答形式の差が残ります。
- 語句に基づく矛盾検出は限定的で、意味論的な証明ではありません。
- 正解ラベルはモデル入力へ渡していません。市場と顧客による検証はUNVERIFIEDのままです。
- 各試行の診断JSON、根拠、エラー、ハッシュは同梱証跡ZIPから取得できます。
