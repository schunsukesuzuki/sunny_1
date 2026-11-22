# Claims Operations Planner v0.14 — R0 実装検証

> **架空のドイツInsurTech顧客／合成請求データ**。期限超過KPIは実顧客実測ではありません。保険金支払判断・個人情報処理は対象外です。

- Run ID: `18f330a8-e5b4-422e-8062-d24739114a33` / UTC: 2026-11-22T05:02:54+00:00
- 顧客の相談: 想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。

[PUBLIC EVIDENCE — HUMAN-REVIEWED HYPOTHESIS, NOT CUSTOMER APPROVAL]
Hypothesis: Insurers must provide clear and timely updates on claim processing steps
Evidence pointers (source statements only): PUB-003, PUB-006
Evidence support, causal attribution, customer validity: UNVERIFIED. R0 FIFO and R1 contracts remain synthetic fixed test specifications.
[END HUMAN-REVIEWED HYPOTHESIS]
- 要件 `REQ-QUEUE-001` / `CLAIMS-R0-FIFO-v1`: Process cases in ascending arrival_order (FIFO), selecting earliest feasible qualified reviewer-day
- 要件の事業妥当性: **UNVERIFIED**、実装の正しさ: **PASS**
- DEV seeds: [42, 43, 44]; HOLDOUT seeds: [10042, 10043]（モデルに非開示）

| 分割/方式 | 期限超過合計 | 実働時間合計h | 期限内率 | 制約PASS |
|---|---:|---:|---:|---|
|development / fifo|11|87|0.7963|True|
|development / deadline|0|87|1.0|True|
|holdout / fifo|8|64|0.77777|True|
|holdout / deadline|0|64|1.0|True|

## サービス設計

```json
{
  "product_scope": "保険業務SaaSのサービス設計",
  "actors": [
    "顧客（ドイツ国内実績、欧州展開検討）",
    "審査担当者（固定人員・勤務時間）",
    "システム（自動化されたケース割当と進捗管理）"
  ],
  "use_cases": [
    "ケースの到着と優先順位決定",
    "適格な審査担当者の選定",
    "期限超過の最小化",
    "人間による保険金請求可否判断"
  ],
  "domain_entities": [
    "案件情報（審査所要時間、期限、保険金請求額、必要資格）",
    "審査担当者情報（資格、勤務時間、休暇）",
    "法規制適合性（EU法規制）"
  ],
  "service_flow": [
    "案件到着 → システムによる優先順位決定（FIFO）",
    "適格な審査担当者選定 → 割当",
    "審査実施 → 人間による判断",
    "結果通知 → 顧客への進捗更新"
  ],
  "hard_constraints": [
    "固定の審査人員・勤務時間",
    "先着順（FIFO）のみを採用",
    "期限超過を減らすことを目的",
    "人間による保険金請求可否判断"
  ],
  "objectives": [
    "FIFOルールを正確に実装",
    "期限超過を最小限に抑える",
    "顧客固有のEU法規制適合性を検証しない"
  ],
  "interfaces": [
    "案件入力インターフェース",
    "審査担当者割当インターフェース",
    "進捗通知インターフェース"
  ],
  "acceptance_tests": [
    "FIFOルールの正確な実装確認",
    "期限超過件数の統計的評価",
    "人間判断プロセスの再現性確認"
  ],
  "alternatives": [
    "期限超過を減らすための優先順位ルール変更（非推奨）",
    "法規制適合性検証の実施（非推奨）"
  ],
  "external_validation_needed": [
    "EU法規制適合性の検証",
    "人間判断プロセスの有効性評価"
  ],
  "design_source": "qwen_draft_unapproved"
}
```

## 判定の分離

- 実装の正しさ: FIFO仕様を独立決定的評価器が確認。
- 要件の正しさ: 顧客証拠は0件。期限超過を減らす要件かは未検証。
- 仮説: 計画された審査担当者の時間を増やさず、期限優先方式に改訂すれば期限超過が減る。
- 比較の限界: ケースの実処理時間、担当資格、顧客の期限設定を合成値で仮定。参照方式は厳密最適解ではない。

## 追跡可能性

`REQ-QUEUE-001` → `SERVICE-R0` → `fifo.py`（SHA256 `df2ab7c14eb233fc6389441e5fff403ffbaf2a9e84f1bde64d596ee24114838a`） → deterministic evaluator.
