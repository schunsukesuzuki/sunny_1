# Claims Operations Planner v0.14 — R0 実装検証

> **架空のドイツInsurTech顧客／合成請求データ**。期限超過KPIは実顧客実測ではありません。保険金支払判断・個人情報処理は対象外です。

- Run ID: `5cc60d5a-20aa-4308-964c-4d9af3bf2a5c` / UTC: 2026-11-22T03:59:54+00:00
- 顧客の相談: 想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。

[PUBLIC EVIDENCE — HUMAN-REVIEWED HYPOTHESIS, NOT CUSTOMER APPROVAL]
Hypothesis: Insurers need to improve timeliness and communication in claims processing
Evidence pointers (source statements only): PUB-001, PUB-003, PUB-004
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
  "product_scope": "保険業務SaaS企業の顧客向けサービス設計",
  "actors": [
    "顧客（ドイツ国内実績、欧州展開検討）",
    "審査担当者（固定人員・勤務時間）",
    "システム（自動化されたケース割当）"
  ],
  "use_cases": [
    "案件の到着順に従って自動的に審査担当者を割当",
    "期限超過を減らすための優先順位管理",
    "人間による保険金請求可否判断"
  ],
  "domain_entities": [
    "案件（審査所要時間、期限、保険金請求額、必要資格）",
    "審査担当者（資格、勤務時間、休日）",
    "ルールエンジン（FIFO順による割当）"
  ],
  "service_flow": [
    "案件到着 → システムに登録",
    "案件情報に基づく審査担当者候補抽出",
    "FIFOルールに従って担当者割当",
    "期限超過リスクの監視",
    "人間による最終判断"
  ],
  "hard_constraints": [
    "固定の審査人員・勤務時間",
    "先着順（FIFO）のみを採用",
    "期限超過を減らすことを目的としない",
    "人間が保険金請求可否を判断"
  ],
  "objectives": [
    "FIFOルールの正確な実装",
    "案件の到着順に従った処理",
    "期限超過の発生を最小限に抑える"
  ],
  "interfaces": [
    "案件入力インターフェース",
    "審査担当者割当インターフェース",
    "人間判断インターフェース"
  ],
  "acceptance_tests": [
    "FIFO順で案件が割当されることを確認",
    "期限超過が発生しないことを確認",
    "人間判断が正しく反映されることを確認"
  ],
  "alternatives": [
    "優先順位ルールの導入（現状では非採用）",
    "自動化された保険金請求可否判断（現状では非採用）"
  ],
  "external_validation_needed": [
    "EU法規制適合性検証",
    "顧客固有要件の確認"
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
