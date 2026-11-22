# Claims Operations Planner v0.21 — Requirement Refinement監査レポート

> **合成案件・模擬顧客の反例に基づく技術検証のみ**。顧客要件の現実的妥当性と実業務効果は未確認。

## 1. 要件の正しさと実装の正しさ

| 検証軸 | 結果 | 根拠 |
|---|---|---|
| R0実装の正しさ | PASS | FIFO独立評価／E2B |
| Qwen-Coder 要件診断（比較用） | HOLD | R0 DEVと模擬証拠のみ |
| ODA-Fin-RL-8B 独立要件診断 | HOLD | R0 DEVと模擬証拠のみ・独立ルーブリック |
| R1独立KPI評価（仕様の完全適合とは別） | PASS | 新HOLDOUTの合成KPI・制約のみ。期限/希少資格の優先順位は追加の行動プローブで検査 |
| 自動診断を含む外側ループ | HOLD | 要件診断品質ゲートとR1技術評価を分離 |
| 顧客要件の事業妥当性 | **UNVERIFIED** | 実顧客の承認・作業実測なし |

## 2. 顧客課題と仮説

想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。

[PUBLIC EVIDENCE — HUMAN-REVIEWED HYPOTHESIS, NOT CUSTOMER APPROVAL]
Hypothesis: Insurers must identify and adapt communication for vulnerable consumers early in the claims process
Evidence pointers (source statements only): PUB-006
Evidence support, causal attribution, customer validity: UNVERIFIED. R0 FIFO and R1 contracts remain synthetic fixed test specifications.
[END HUMAN-REVIEWED HYPOTHESIS]

- 仮説: **予定審査稼働を増やさず、期限超過件数を削減できるか**。
- 固定するもの: 人員・日別容量・資格・案件の処理時間・顧客判断権限。
- 初期要件: `CLAIMS-R0-FIFO-v1`: 到着順のFIFO。
- 改訂要件: `CLAIMS-R1-SLA-v1`: 期限・技能に応じた割当。
- 実顧客・実案件に対する外挿は不可。

## 3. 反証と独立要件改訂

- Evidence: `SIM-SLA-001`（模擬データ）
- Qwen classification: `implementation_bug`
- ODA-Fin-RL model: `hf.co/alexsabaka/ODA-Fin-RL-8B-GGUF:Q4_K_M`
- ODA classification: `requirement_mismatch`
- ODA root cause: R0 contract mandates strict FIFO implementation while synthetic evidence demonstrates FIFO violates business objective of reducing deadline breaches
- ODA suggested change: Replace FIFO with deadline-first scheduling with arrival_order as tie-breaker for same-deadline cases
- ODA interpretation of R0 implementation: `correct`
- ODA interpretation of business requirement: `unverified`
- ODA evidence IDs: `[]`
- ODA rubric failures: `['EVIDENCE_IDS_INCORRECT']`
- ODA independent diagnostic quality: `{"rubric_version": "DIAG-RUBRIC-v0.10.1", "classification_ok": true, "implementation_read_ok": true, "evidence_traceability_ok": false, "revision_consistency_ok": true, "synthetic_requirement_fit": "mismatch", "real_customer_business_validity": "UNVERIFIED", "reported_business_requirement_assessment": "unverified", "checks": {"classification": true, "implementation_vs_specification": true, "evidence_ids": false, "revision_policy_consistency": true, "business_fit_not_overclaimed": true}, "pass": false, "failure_codes": ["EVIDENCE_IDS_INCORRECT"], "note": "Heuristic lexical contradictions need human inspection; no legal/market certification."}`
- Qwen independent diagnostic quality: `{"rubric_version": "DIAG-RUBRIC-v0.10.1", "classification_ok": false, "implementation_read_ok": true, "evidence_traceability_ok": true, "revision_consistency_ok": true, "synthetic_requirement_fit": "unverified", "real_customer_business_validity": "UNVERIFIED", "reported_business_requirement_assessment": null, "checks": {"classification": false, "implementation_vs_specification": true, "evidence_ids": true, "revision_policy_consistency": true, "business_fit_not_overclaimed": true}, "pass": false, "failure_codes": ["CLASSIFICATION_MISMATCH"], "note": "Heuristic lexical contradictions need human inspection; no legal/market certification."}`
- Synthetic evidence requirement fit: `mismatch`
- Real customer business validity: **UNVERIFIED**
- Model agreement: `False`
- Qwen and ODA independently assessed the **same DEV and evidence**. Neither sees HOLDOUT nor the other's diagnostic answer.
- **The final R1 contract remains predeclared**, NOT produced or certified by ODA. It requires human approval; the model cannot modify the verifier.
- ODAの診断出力は承認後、QwenのR1生成・DEV修正プロンプトへ渡す。ただし**HOLD時は誤ったODA結論を渡さず、人間の審査記録と独立R0 PASSを参照**する（評価器は変更不可）。
- Qwenの理由: The independent implementation test result is marked as PASS for the original FIFO contract, meaning the code correctly implements FIFO behavior by processing cases in ascending arrival_order. However, the synthetic evidence SIM-SLA-001, although labeled as 'fictional', describes a scenario where FIFO leads to missed deadlines for short-term cases due to prioritizing long-deadline high-value cases. This observation contradicts the stated business objective of minimizing deadline breaches, but does not contradict the implementation's adherence to the R0 contract which specifies FIFO processing without guaranteeing fewer deadline breaches. The contradiction lies in the business expectation versus the actual outcome of the FIFO logic, not in the code itself. Since the implementation correctly follows the specified rule (FIFO), and the synthetic evidence does not provide verifiable customer data or regulatory basis, this is an issue of business adequacy rather than correctness.
- 改訂案: The requirement may need clarification to address whether deadline adherence should be prioritized over strict FIFO when conflicts arise. If deadline adherence is a higher priority, then the current R0 specification might need to be updated to reflect that cases with imminent deadlines take precedence over arrival order within the same reviewer-day.

- REQ-QUEUE-001 stable ID
- FIFO arrival order → deadline / skill aware ordering
- No increase in planned reviewer hours or overtime
- Same qualification and duration constraints
- Independent pinned R1 evaluator; model cannot edit test rules
- Synthetic deadline KPI compared on new HOLDOUT

### ドメインモデルの業務上の注意事項

- Tradeoffs: []
- Regulatory questions needing primary-source verification: ["Is FIFO implementation compatible with SLA-001 deadline objectives?"]
- Uncertainty: real_customer_validity=unverified
- このデモにはEU規制の外部検索機能はありません。Vertical FMの規制主張を根拠として承認しません。

## 4. 人間の承認・監査

- Actor: `Claims Product Owner (demo)`
- Time: `2026-11-22T01:49:36+00:00`
- Rationale: 模擬反例に基づく技術検証として、期限優先方式への改訂を承認。事業妥当性は未検証。
- Approval path: `audited_human_review`
- ODA diagnostic at approval: `HOLD` (never rewritten)
- Human override rationale: R0のFIFO実装は独立評価でPASS。ODAの診断はHOLDのまま残し、理由・証拠・実装認識を個別に確認する。模擬反例と固定R1契約に基づく技術検証のみ継続し、実顧客の事業妥当性は未検証として扱う。
- ODA rubric errors preserved: ['EVIDENCE_IDS_INCORRECT']
- R0 contract hash: `630a7406a20803842949317e4f6e177e67061c8098d7299fbb2b184535829f19`
- R1 contract hash: `6bc9ca1d3ffa4de231ccf42863ec7f1c4cea6407eaef2e1234f91388117c371a`
- Service design hash: `2f88e6c7234e985ac9997d0c35bd60922962f4ba56c18dd485ef6bfbbf99ac9f`
- Selected R1 source hash: `19ff6932096cd02f84b3bd9adb8f47c893ff67a892fbd79a509134dc509efb99`
- Selected engine: `skill_deadline_scarcity` / provenance: `PINNED_REVIEWED_DOMAIN_SKILL_NOT_LLM`
- Selection mode: `compare`. A Skill selection is NOT LLM code-generation success.
- Parent run: `b317d1a3-9f4a-43be-abae-d0bff491095c` / Proposal: `dd4dd5fb-6769-425d-8e5e-474170e37ff3` / Experiment: `24f029c8-3f0d-4c10-9424-46af5e522a21`

## 5. 改訂コードの開発用評価

| Attempt | ソースSHA256 (先頭16文字) | 有効性 | 期限超過合計 |
|---:|---|---|---:|
|0|`1ce6697a84933028`|False|None|
|1|`c4e01988292f9e82`|True|0|
|2|`6b0a2e9d59112399`|True|7|

- DEV: `[142, 143, 144]`。Qwenに渡す修正指示はDEV由来のみ。
- DEV candidate gate: **`ELIGIBLE_SKILL_SELECTED`** (`R1-DEV-SELECTION-GATE-v0.19.0`) — KPI + deadline/qualification behavioral probes + four stress scenarios.
- v0.29 preselection robustness: **`TIE_UNRESOLVED_BY_DEV`**; selection uncertainty and leave-one-stress-out sensitivity are separately audited; NOT a statistical generalization guarantee.
- DEV selected attempt: `None`; no eligible candidate means the untouched holdout is **NOT_EXECUTED**, not a PASS.
- Detailed gate reasons/code hashes: `dev_selection_audit.json`.
- The 08b post-selection policy check repeats fixed DEV probes/stresses; it is NOT an untouched independent behavioral holdout.
- HOLDOUT: `[20042, 20043]`。生成・選択後に一度だけ実行。失敗した結果を修正プロンプトに転用しない。

### 5b. Domain SkillのDEV比較（LLM修復に入力しない）

|方式|DEV期限超過|制約PASS|選別適格|E2B実行秒数（DEVのみ）|
|---|---:|---|---|---:|
|skill_deadline_scarcity|0|True|True|4.562|
|skill_bounded_beam|0|True|True|4.827|

- Skillは人間が事前に用意したコードであり、LLMの生成・修復に成功したことを示しません。
- `skill_manifest.json`、`skill_component_*.py`、`skill_*.py`、実行結果と独立DEVゲートが監査対象です。
- bounded_beamは有界探索であり、厳密な最適化ソルバーではありません。
- LLMのtokenコスト・E2Bの請求額は未計測。実行秒数はE2Bコマンドの観測値のみ。

## 6. 同じHOLDOUT・共通KPIによるR0/R1比較

| 方式 | 期限超過合計 | 割当予定時間合計h | 期限内率 | 制約PASS |
|---|---:|---:|---:|---|
|fifo|6|68|0.83333|True|
|deadline|0|68|1.0|True|
|generated|0|68|1.0|True|

- 期限優先の固定参照実装はヒューリスティックであり厳密最適化とは呼ばない。
- 未割当案件も期限超過に算入。割当予定時間が減るだけでは『同一稼働で改善』と判定しない。
- 自動診断を含む外側ループ技術実証: **False**
- 人間のHOLD審査を経たR1技術KPI改善: **True**
- R1独立KPI改善（診断の適否とは別）: **True**
- 期限優先・希少資格の固定DEV反例は候補選別に用いました。選択後の08bは同一フィクスチャの再実行であり独立HOLDOUTの行動証明ではありません。
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
- `/api/artifacts/experiments/24f029c8-3f0d-4c10-9424-46af5e522a21/bundle`：生成コード全試行・差分・E2B標準出力・評価JSON・要件診断・人間承認・比較Markdownを含む証跡ZIP。
- 失敗した生成・E2B実行も試行単位で記録（個別のSDK初期化エラーは `started.json` とともに検証が必要）。

## 9. 次の顧客検証

1. Claims Managerへ期限超過ペナルティとSLAの意味を確認。
2. 実測の案件所要時間・必要資格・到着分布を取得し分布ずれを検証。
3. 実案件の匿名化等の適法性、GDPR・委託関係を法務と確認。
4. 期限超過数、平均処理待ち時間、レビュー品質、残業、担当者負荷を実測。
5. 保険金の支払可否判断を一貫して人間に保持する。
