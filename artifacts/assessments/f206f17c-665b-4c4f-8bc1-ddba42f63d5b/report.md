# Project Feasibility Assessment — v0.14

> 合成・架空顧客に限定した技術プリセールス用の判断支援。実顧客・市場・法令・本番運用の適合を保証しません。

- Assessment ID: `f206f17c-665b-4c4f-8bc1-ddba42f63d5b`
- Experiment ID: `115c0ce9-ab09-4027-b981-2599a8490975`
- Generated at (UTC): 2026-11-21T06:02:21+00:00
- Rubric: `PRESALES-ASSESSMENT-v0.14.0`
- Provisional decision: **HOLD** — stage `TECHNICAL_VALIDATION` (HOLD_GROUNDED_CONTRACT)
- Production decision: **NO_GO** (production GO: **NO**)
- Rationale: 公開問題背景は取得済みだが、合成データでの人間設定KPI・仕様検証がHOLD。顧客事業価値は未検証。

## 技術実験の要約

| 合成HOLDOUT | FIFO | 生成R1 | 期限優先参照（ヒューリスティック） |
|---|---:|---:|---:|
| 期限超過件数 | 6 | 7 | 0 |
| 割当予定時間（時間） | 68 | 68 | 68 |

- 参照方式は数学的な最適解ではありません。HOLDOUTの合成結果を実業務効果へ外挿できません。
- 要件診断ルーブリック Qwen: **HOLD** / ODA: **HOLD**
- 人間のデモ上書き承認: **YES**。上書き承認は元の診断HOLDをPASSに変更しません。
- R1 behavioral contract: **HOLD** / stress: **REVIEW_REQUIRED**
- 診断ベンチマーク 全試行PASS: **False** （単発診断との混同禁止）

## Diagnostic benchmark summary

| Model | Completed | PASS | Planned | Mean score |
|---|---:|---:|---:|---:|
| coding | 2 | 0 | 2 | 0.75 |
| finance | 2 | 0 | 2 | 0.8125 |

## Business Value & Feasibility

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| BV-01 顧客課題と業務KPIの整合（合成ケース） | HOLD | 同一条件のR1独立KPI改善が確認できない [E01, E04] | 顧客の実データでSLA・処理時間・案件到着分布を検証する |
| BV-02 代替案の定量比較 | HOLD | 比較対象または有効なHOLDOUT評価が不足している [E01, E04] | 顧客が承認した基準・失敗コストで代替案を再比較する |
| BV-03 MVPの範囲と承認ゲート | DEMO_CONTROLLED | 変更要件と人間のデモ承認が記録され、検証対象は担当者割当ロジックに限定 [E02, E03] | 顧客とスコープ、除外事項、受入基準を合意する |
| BV-04 実顧客の需要・支払意思 | UNVERIFIED | 公開された問題背景はE08に収録。実顧客の需要・支払意思・保険案件の処理フローは未検証 [E05] | 顧客ヒアリングと有償PoCの支払意思を確認する |
| BV-05 収益性・投資回収 | UNVERIFIED | 開発費・運用費・CAC・料金・期限超過削減の金銭価値は未実測 [E05] | 提案原価・運用負荷・回収可能額を見積もる |
| BV-06 外部証拠と当該事業課題の整合（限定的） | PUBLIC_PROBLEM_CONTEXT_ONLY | 原文の課題領域のみ確認。FIFO因果・顧客固有SLA・要件導出は実証していない [E08] | 当事者の一次資料と業務観測で問題原因を確認 |

## AI Delivery & Operational Readiness

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| AI-01 生成コードの隔離実行・制約検証 | HOLD | 有効なE2B実行・制約評価の証跡が不足 [E04] | 権限、ネットワーク出口、CPU/メモリ制限を含む実環境のセキュリティ審査を行う |
| AI-02 DEVとHOLDOUTの分離・再現性 | HOLD | 独立HOLDOUT・コード選択の証跡が不足 [E04] | seed追加・顧客分布の変動・回帰テストで頑健性を測る |
| AI-03 LLM要件診断の品質 | HOLD | 単発診断PASSは十分でない。独立ベンチマークの未実施・HOLD・未完了を含めてレビューが必要 [E02, E07] | 多ケース・複数回の独立診断ベンチマークと誤判定分析を実施する |
| AI-04 人間の関与と監査可能性 | DEMO_CONTROLLED | モデル診断HOLDを保持したままデモ上の人間審査で技術検証を継続 [E02, E03, E04] | 顧客側の権限分掌・承認者・監査保持期間を設計する |
| AI-05 業務ワークフロー・本番運用 | UNVERIFIED | 顧客基盤への統合、認証、SLA、障害対応、監視・復旧は未検証 [E05] | API・監査運用・例外処理・データ移行の設計レビューを行う |
| AI-06 法務・個人情報・規制 | UNVERIFIED | 実顧客のデータ処理、GDPR、保険規制との適合を検証していない [E05] | 適用法令、データ保護、委託契約、保険金判断の人間関与を専門家と確認する |
| AI-07 R1契約の振る舞い（期限と希少資格） | HOLD | KPI改善と独立に検証するR1の行動プローブが未実施または不合格 [E06] | 追加の業務反例・プロパティテスト・顧客受入条件へ拡張する |
| AI-08 高負荷・資格偏在・短納期への頑健性 | HOLD | ストレステストが未実施、制約違反、または固定参照より期限超過/未割当が多いケースあり [E06] | 到着時刻・ピーク負荷・実顧客分布を使って再検証する |
| AI-09 人間設定の閾値による根拠紐付け合成評価 | HOLD | 顧客承認仕様ではなく、合成HOLDOUTと既存独立プローブでの判定 [E08, E04, E06] | 実業務データと顧客承認の評価基準を別途取得 |

## Evidence register — 根拠の出所

| ID | 証拠種類 | ローカル出所 | 限界 |
|---|---|---|---|
| E01 | SYNTHETIC | runs/830ed111-4981-4c1d-9998-89fe2fe97a40/run.json | Local experiment result; not customer-reported |
| E02 | SYNTHETIC | proposals/cd5e0420-521f-472c-8be1-18cfb23091c5/proposal.json | Synthetic fixture; evidence IDs are application-defined |
| E03 | DEMO_CONTROLLED | approvals/7c409320-df8f-4bf2-9b60-621a1aa19487/approval.json | Simulated approval, not actual client authorization |
| E04 | SYNTHETIC | experiments/115c0ce9-ab09-4027-b981-2599a8490975/experiment.json | Synthetic E2B-based test; not production deployment |
| E05 | UNVERIFIED | No direct customer business data or authorized claims workflow attached (public contextual evidence is E08) | No independent external verification |
| E06 | SYNTHETIC | policy_validations/c3965c87-2914-43fe-96c8-a326f46074ef/validation.json | Selected synthetic behaviors only; not formal specification proof |
| E07 | SYNTHETIC | benchmarks/caf99615-3b44-4a20-8569-9f8c71fcdbfb/benchmark.json | Limited artificial cases; do not infer population-level model accuracy |
| E08 | PUBLIC_PROBLEM_CONTEXT_ONLY | workflows/b02d9bb2-6ac4-4f9e-b8c8-b6aec8555787/00b_human_evidence_review.json | Published problem context, not current client evidence, not proof of FIFO/skill scheduling |

証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ。
**合成の証拠IDは実在する顧客資料・一次資料ではありません。**

## Next validation actions

- **P1 / Customer / product owner**: 顧客の業務SLA・分布・処理時間・資格・例外を実測で確認
- **P1 / AI technical reviewer**: R1の期限・希少資格の行動プローブとストレス試験の不合格を修正/再評価
- **P1 / AI technical reviewer**: 単発診断と診断ベンチマークを分離して誤判定を検証
- **P2 / Business development**: 実顧客ROI、PoC費用、採算、支払意思を検証
- **P2 / Delivery / compliance**: 本番ワークフロー、認証、監査・規制・データ保護を精査

## Audit metadata

- Local source snapshot SHA256 values (data integrity pointers, not signed attestations):

  - `experiment.json`: `9cc05b6159ac5b2849d3cf98042e4deccf6932a82d36b5dcd7c998fccb5bb55c`
  - `run.json`: `0ce9bc022468fb4226a942d91769b273a2720cdaf43e05701bc209bf3ddea92e`
  - `proposal.json`: `71e77bd968263a7df958e96bcdf381222b5fd990483bedcb2ff8a21756eeacdc`
  - `approval.json`: `458072610370ec72b90acb58adec557fc31b3aa001e87e930fd233af090441ed`

Evidence ID correctness != evidence validity != diagnostic correctness. SIM-SLA-001 and report E01-E05 are local/synthetic references, not external citations. No customer, market, legal, regulatory or production approval is inferred.
