# R1 Policy & Stress Validation — v0.14

> 固定した合成反例とストレスシナリオによる追加評価。形式証明・本番保証・最適性の証明ではありません。

- Validation ID: `c3965c87-2914-43fe-96c8-a326f46074ef`
- Experiment ID: `115c0ce9-ab09-4027-b981-2599a8490975`
- Source SHA256: `42adf00fbe7c9ad694bacd1a2fb942c40f338ac21e3d26527cac1a0ce49cee2a`
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
|capacity_pressure|generated|5|2|26|PASS|
|skill_bottleneck|fifo|8|2|29|PASS|
|skill_bottleneck|deadline|1|1|30|PASS|
|skill_bottleneck|generated|5|2|27|PASS|
|deadline_compression|fifo|6|0|30|PASS|
|deadline_compression|deadline|0|0|30|PASS|
|deadline_compression|generated|7|0|30|PASS|
|arrival_reordering|fifo|2|0|32|PASS|
|arrival_reordering|deadline|0|0|32|PASS|
|arrival_reordering|generated|0|0|32|PASS|

- Reference regressions in scenarios: 3
- 未割当は期限超過に含めます。総稼働量の減少だけを改善と見なしません。
- 固定参照は数学的な最適解ではありません。HOLDOUTでのKPI改善と仕様に沿う振る舞いは別の評価です。
- 各入力・E2B出力・制約検証結果は同梱JSONに記録しています。
