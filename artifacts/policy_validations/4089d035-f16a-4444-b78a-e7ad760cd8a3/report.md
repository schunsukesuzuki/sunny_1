# R1 Policy & Stress Validation — v0.14

> 固定した合成反例とストレスシナリオによる追加評価。形式証明・本番保証・最適性の証明ではありません。

- Validation ID: `4089d035-f16a-4444-b78a-e7ad760cd8a3`
- Experiment ID: `e6271dae-951f-44a4-a512-a4f264989dfc`
- Source SHA256: `b7f4b2cd0729d5e226b7ef5dc93ae2b2f2f01026bc89ccdeed1af76d33db3894`
- Behavioral contract probes: **HOLD**
- Stress validity: **PASS**
- Stress heuristic comparisons: **REVIEW_REQUIRED**

## Behavioral probes

| scenario | pass | independent checks | missed | unassigned |
|---|---|---|---:|---:|
|deadline_risk_probe|True|urgent_served_on_due_day:True, both_cases_served:True|0|0|
|scarce_qualification_probe|False|scarce_case_uses_sole_specialist:False, common_case_preserves_specialist_capacity:False, all_cases_served:False|1|1|

## Synthetic stress scenarios

| scenario | method | missed incl. unassigned | unassigned | assigned hours | constraints |
|---|---|---:|---:|---:|---|
|capacity_pressure|fifo|7|0|31|PASS|
|capacity_pressure|deadline|0|0|31|PASS|
|capacity_pressure|generated|0|0|31|PASS|
|skill_bottleneck|fifo|8|2|29|PASS|
|skill_bottleneck|deadline|1|1|30|PASS|
|skill_bottleneck|generated|1|1|30|PASS|
|deadline_compression|fifo|6|0|30|PASS|
|deadline_compression|deadline|0|0|30|PASS|
|deadline_compression|generated|1|0|30|PASS|
|arrival_reordering|fifo|2|0|32|PASS|
|arrival_reordering|deadline|0|0|32|PASS|
|arrival_reordering|generated|0|0|32|PASS|

- Reference regressions in scenarios: 1
- 未割当は期限超過に含めます。総稼働量の減少だけを改善と見なしません。
- 固定参照は数学的な最適解ではありません。HOLDOUTでのKPI改善と仕様に沿う振る舞いは別の評価です。
- 各入力・E2B出力・制約検証結果は同梱JSONに記録しています。
