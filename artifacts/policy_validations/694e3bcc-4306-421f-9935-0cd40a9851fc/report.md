# R1 Policy & Stress Validation — v0.14

> 固定した合成反例とストレスシナリオによる追加評価。形式証明・本番保証・最適性の証明ではありません。

- Validation ID: `694e3bcc-4306-421f-9935-0cd40a9851fc`
- Experiment ID: `f692e410-bb74-4bae-bf9a-1e93c5dd8ed7`
- Source SHA256: `19ff6932096cd02f84b3bd9adb8f47c893ff67a892fbd79a509134dc509efb99`
- Behavioral contract probes: **PASS**
- Stress validity: **PASS**
- Stress heuristic comparisons: **NO_REGRESSION_DETECTED_IN_FIXTURES**

## Behavioral probes

| scenario | pass | independent checks | missed | unassigned |
|---|---|---|---:|---:|
|deadline_risk_probe|True|urgent_served_on_due_day:True, both_cases_served:True|0|0|
|scarce_qualification_probe|True|scarce_case_uses_sole_specialist:True, common_case_preserves_specialist_capacity:True, all_cases_served:True|0|0|

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
|deadline_compression|generated|0|0|30|PASS|
|arrival_reordering|fifo|2|0|32|PASS|
|arrival_reordering|deadline|0|0|32|PASS|
|arrival_reordering|generated|0|0|32|PASS|

- Reference regressions in scenarios: 0
- 未割当は期限超過に含めます。総稼働量の減少だけを改善と見なしません。
- 固定参照は数学的な最適解ではありません。HOLDOUTでのKPI改善と仕様に沿う振る舞いは別の評価です。
- 各入力・E2B出力・制約検証結果は同梱JSONに記録しています。
