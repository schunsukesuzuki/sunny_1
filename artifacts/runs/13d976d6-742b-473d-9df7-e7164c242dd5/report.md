# Claims Operations Planner v0.14 — R0 実装検証

> **架空のドイツInsurTech顧客／合成請求データ**。期限超過KPIは実顧客実測ではありません。保険金支払判断・個人情報処理は対象外です。

- Run ID: `13d976d6-742b-473d-9df7-e7164c242dd5` / UTC: 2026-11-21T08:16:28+00:00
- 顧客の相談: 想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。

[PUBLIC EVIDENCE — HUMAN-REVIEWED HYPOTHESIS, NOT CUSTOMER APPROVAL]
Hypothesis: Insurers must provide clear and timely updates on claim progress
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
    "顧客（ドイツ国内で実績あり、欧州展開を検討）",
    "審査担当者（固定人員・勤務時間）",
    "システム（自動化されたケース割当と進捗管理）"
  ],
  "use_cases": [
    "ケースの到着順による自動割当（FIFO）",
    "審査担当者の資格と勤務時間に合致するケースの選定",
    "期限超過を減らすための優先順位調整（未実装）",
    "人間による保険金請求可否判断"
  ],
  "domain_entities": [
    "案件情報（審査所要時間、期限、保険金請求額、必要資格）",
    "審査担当者情報（資格、勤務時間、休日）",
    "法規制適合性（EU法規制、未検証）"
  ],
  "service_flow": [
    "案件到着 → システムによるFIFO順の自動割当 → 対応可能な審査担当者選定 → 审査開始",
    "審査中 → 進捗状況のリアルタイム更新 → 期限超過リスクの監視",
    "審査完了 → 人間による保険金請求可否判断 → 結果の通知"
  ],
  "hard_constraints": [
    "固定の審査人員・勤務時間",
    "先着順（FIFO）のみを採用",
    "期限超過を減らすことを目的としない",
    "人間による保険金請求判断を必須"
  ],
  "objectives": [
    "FIFOルールの正確な実装",
    "期限超過の発生を最小限に抑える（ただし、目標としていない）",
    "顧客固有のEU法規制適合性の検証は未実施"
  ],
  "interfaces": [
    "案件入力インターフェース",
    "審査担当者選定インターフェース",
    "進捗通知インターフェース",
    "人間判断インターフェース"
  ],
  "acceptance_tests": [
    "FIFOルールの実装確認テスト",
    "審査担当者選定ロジックの検証テスト",
    "期限超過発生率の統計的評価（未達成）"
  ],
  "alternatives": [
    "優先順位調整機能の追加（未実装）",
    "法規制適合性の自動チェック機能（未実装）"
  ],
  "external_validation_needed": [
    "EU法規制適合性の検証",
    "実際の業務効率の評価"
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
