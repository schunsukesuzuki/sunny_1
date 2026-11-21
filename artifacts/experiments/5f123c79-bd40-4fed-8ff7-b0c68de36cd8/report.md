# Claims Operations Planner v0.10 — Requirement Refinement監査レポート

> **合成案件・模擬顧客の反例に基づく技術検証のみ**。顧客要件の現実的妥当性と実業務効果は未確認。

## 1. 要件の正しさと実装の正しさ

| 検証軸 | 結果 | 根拠 |
|---|---|---|
| R0実装の正しさ | PASS | FIFO独立評価／E2B |
| Qwen-Coder 要件診断（比較用） | HOLD | R0 DEVと模擬証拠のみ |
| ODA-Fin-RL-8B 独立要件診断 | HOLD | R0 DEVと模擬証拠のみ・独立ルーブリック |
| R1コードの独立技術評価 | PASS | 新HOLDOUTでの共通KPIと制約 |
| 自動診断を含む外側ループ | HOLD | 要件診断品質ゲートとR1技術評価を分離 |
| 顧客要件の事業妥当性 | **UNVERIFIED** | 実顧客の承認・作業実測なし |

## 2. 顧客課題と仮説

想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。

- 仮説: **予定審査稼働を増やさず、期限超過件数を削減できるか**。
- 固定するもの: 人員・日別容量・資格・案件の処理時間・顧客判断権限。
- 初期要件: `CLAIMS-R0-FIFO-v1`: 到着順のFIFO。
- 改訂要件: `CLAIMS-R1-SLA-v1`: 期限・技能に応じた割当。
- 実顧客・実案件に対する外挿は不可。

## 3. 反証と独立要件改訂

- Evidence: `SIM-SLA-001`（模擬データ）
- Qwen classification: `requirement_mismatch`
- ODA-Fin-RL model: `hf.co/alexsabaka/ODA-Fin-RL-8B-GGUF:Q4_K_M`
- ODA classification: `requirement_mismatch`
- ODA root cause: conflict between FIFO implementation and deadline prioritization goal
- ODA suggested change: remove strict FIFO; prioritize deadline_first_fifo_tiebreak
- ODA interpretation of R0 implementation: `incorrect`
- ODA interpretation of business requirement: `mismatch`
- ODA evidence IDs: `['SIM-SLA-001']`
- ODA rubric failures: `['IMPLEMENTATION_PASS_MISREAD']`
- ODA independent diagnostic quality: `{"rubric_version": "DIAG-RUBRIC-v0.10.1", "classification_ok": true, "implementation_read_ok": false, "evidence_traceability_ok": true, "revision_consistency_ok": true, "synthetic_requirement_fit": "mismatch", "real_customer_business_validity": "UNVERIFIED", "reported_business_requirement_assessment": "mismatch", "checks": {"classification": true, "implementation_vs_specification": false, "evidence_ids": true, "revision_policy_consistency": true, "business_fit_not_overclaimed": true}, "pass": false, "failure_codes": ["IMPLEMENTATION_PASS_MISREAD"], "note": "Heuristic lexical contradictions need human inspection; no legal/market certification."}`
- Qwen independent diagnostic quality: `{"rubric_version": "DIAG-RUBRIC-v0.10.1", "classification_ok": true, "implementation_read_ok": false, "evidence_traceability_ok": true, "revision_consistency_ok": true, "synthetic_requirement_fit": "unverified", "real_customer_business_validity": "UNVERIFIED", "reported_business_requirement_assessment": null, "checks": {"classification": true, "implementation_vs_specification": false, "evidence_ids": true, "revision_policy_consistency": true, "business_fit_not_overclaimed": true}, "pass": false, "failure_codes": ["EXPLANATION_CONTRADICTS_R0_PASS"], "note": "Heuristic lexical contradictions need human inspection; no legal/market certification."}`
- Synthetic evidence requirement fit: `mismatch`
- Real customer business validity: **UNVERIFIED**
- Model agreement: `True`
- Qwen and ODA independently assessed the **same DEV and evidence**. Neither sees HOLDOUT nor the other's diagnostic answer.
- **The final R1 contract remains predeclared**, NOT produced or certified by ODA. It requires human approval; the model cannot modify the verifier.
- ODAの診断出力は承認後、QwenのR1生成・DEV修正プロンプトへ渡す。ただし**HOLD時は誤ったODA結論を渡さず、人間の審査記録と独立R0 PASSを参照**する（評価器は変更不可）。
- Qwenの理由: The synthetic evidence SIM-SLA-001 directly contradicts R0 by demonstrating that the FIFO implementation allows high-value, long-term deadline cases to be processed before short-term deadline cases, resulting in missed deadlines for later-arriving urgent cases. This violates the core FIFO principle of processing cases in arrival order and shows the system fails to meet the requirement's stated goal of 'Process cases in ascending arrival_order (FIFO)' while maintaining deadline adherence.
- 改訂案: Modify R0 to specify that FIFO must prioritize cases by arrival order AND maintain deadline adherence, or clarify that deadline breaches are acceptable under certain conditions

- REQ-QUEUE-001 stable ID
- FIFO arrival order → deadline / skill aware ordering
- No increase in planned reviewer hours or overtime
- Same qualification and duration constraints
- Independent pinned R1 evaluator; model cannot edit test rules
- Synthetic deadline KPI compared on new HOLDOUT

### ドメインモデルの業務上の注意事項

- Tradeoffs: []
- Regulatory questions needing primary-source verification: []
- Uncertainty: no_holdout_data
- このデモにはEU規制の外部検索機能はありません。Vertical FMの規制主張を根拠として承認しません。

## 4. 人間の承認・監査

- Actor: `Claims Product Owner (demo)`
- Time: `2026-11-21T01:59:22+00:00`
- Rationale: 模擬反例に基づく技術検証として、期限優先方式への改訂を承認。事業妥当性は未検証。
- Approval path: `audited_human_review`
- ODA diagnostic at approval: `HOLD` (never rewritten)
- Human override rationale: R0のFIFO実装は独立評価でPASS。ODAの診断の証拠ID欠落や優先順位の矛盾などを確認した。HOLDを保存したまま合成反例と固定R1契約に基づく技術検証のみ進める。
- ODA rubric errors preserved: ['IMPLEMENTATION_PASS_MISREAD']
- R0 contract hash: `630a7406a20803842949317e4f6e177e67061c8098d7299fbb2b184535829f19`
- R1 contract hash: `6bc9ca1d3ffa4de231ccf42863ec7f1c4cea6407eaef2e1234f91388117c371a`
- Service design hash: `2f88e6c7234e985ac9997d0c35bd60922962f4ba56c18dd485ef6bfbbf99ac9f`
- Generated code hash: `eb4b89040a4a17a14ee8214964c3ac33ef1a32fac85a7d8c6c9c9aaf8d9d210d`
- Parent run: `91de9e58-8b70-4cbb-ac77-d6ce6681fc70` / Proposal: `ca076474-4377-436f-93af-6cb99c0b24ca` / Experiment: `5f123c79-bd40-4fed-8ff7-b0c68de36cd8`

## 5. 改訂コードの開発用評価

| Attempt | ソースSHA256 (先頭16文字) | 有効性 | 期限超過合計 |
|---:|---|---|---:|
|0|`13687c955a5b771e`|False|None|
|1|`6119e5dff065d3c0`|False|None|
|2|`eb4b89040a4a17a1`|True|0|

- DEV: `[142, 143, 144]`。Qwenに渡す修正指示はDEV由来のみ。
- HOLDOUT: `[20042, 20043]`。生成・選択後に一度だけ実行。失敗した結果を修正プロンプトに転用しない。

## 6. 同じHOLDOUT・共通KPIによるR0/R1比較

| 方式 | 期限超過合計 | 実働時間合計h | 期限内率 | 制約PASS |
|---|---:|---:|---:|---|
|fifo|6|68|0.83333|True|
|deadline|0|68|1.0|True|
|generated|0|68|1.0|True|

- 期限優先の固定参照実装はヒューリスティックであり厳密最適化とは呼ばない。
- 生成候補が欠損案件を隠す行為は制約違反。実働時間が減るだけでも『同一稼働で改善』とは判定しない。
- 自動診断を含む外側ループ技術実証: **False**
- 人間のHOLD審査を経たR1技術KPI改善: **True**
- R1独立KPI改善（診断の適否とは別）: **True**
- 市場受容・価格受容・法務/GDPR・現地業務手順: **UNVERIFIED**

## 7. 事業開発の収益仮説（すべて未検証）

- SaaS追加機能料金: 月額 **EUR 2,500 / 顧客**（架空）
- パイロット契約: **4社**（仮定、成約実績はゼロ）
- 月間売上: 4 × EUR 2,500 = **EUR 10,000**
- 月間運用費: **EUR 6,000**（仮定）
- 単純な月間貢献: **EUR 4,000**。営業・CAC、実装、規制対応、税・契約費用を含まない。
- SLA期限超過の金銭価値は**未設定**。合成データ上の期限内率を金銭効果へ換算しない。
- 海外市場は開拓仮説であり、EU各国への販売可能性を確認したわけではない。

## 8. 監査ファイルの再取得

- `/api/history/experiments`：過去の実験一覧。
- `/api/artifacts/experiments/5f123c79-bd40-4fed-8ff7-b0c68de36cd8/bundle`：生成コード全試行・差分・E2B標準出力・評価JSON・要件診断・人間承認・比較Markdownを含む証跡ZIP。
- 失敗した生成・E2B実行も試行単位で記録（個別のSDK初期化エラーは `started.json` とともに検証が必要）。

## 9. 次の顧客検証

1. Claims Managerへ期限超過ペナルティとSLAの意味を確認。
2. 実測の案件所要時間・必要資格・到着分布を取得し分布ずれを検証。
3. 実案件の匿名化等の適法性、GDPR・委託関係を法務と確認。
4. 期限超過数、平均処理待ち時間、レビュー品質、残業、担当者負荷を実測。
5. 保険金の支払可否判断を一貫して人間に保持する。
