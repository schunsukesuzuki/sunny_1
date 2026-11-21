# Project Feasibility Assessment — v0.19

> 合成・架空顧客に限定した技術プリセールス用の判断支援。実顧客・市場・法令・本番運用の適合を保証しません。

- Assessment ID: `4d4dde1e-0d1e-46bd-8f87-da483a407d00`
- Experiment ID: `8971936f-076f-4402-aba0-bdf26a8446a5`
- Generated at (UTC): 2026-11-21T12:10:55+00:00
- Rubric: `PRESALES-ASSESSMENT-v0.19.0`
- Provisional decision: **HOLD** — stage `TECHNICAL_VALIDATION` (HOLD_NOTIFICATION_NOT_INTEGRATED)
- Production decision: **NO_GO** (production GO: **NO**)
- Rationale: 公開資料と進捗通知の仮説はトレース済み。独立した合成通知プロトタイプのみを検証。R1担当者割当は当該通知要件を検証しておらず、顧客連携・実運用は未実装。
- Selected R1 engine: `skill_deadline_scarcity` (PINNED_REVIEWED_DOMAIN_SKILL_NOT_LLM)
- Skill-selected source is NOT evidence of LLM code-generation or automatic repair success.

## 実施状況と合否（区別する）

- dev_candidate_selection: **ELIGIBLE_SKILL_SELECTED**
- holdout_execution: **EXECUTED**
- valid_three_way_comparison: **True**
- r1_kpi_improvement: **PASSED**
- business_validity: **UNVERIFIED**
- constraint_validation: **PASSED**

## 技術実験の要約

| 合成HOLDOUT | FIFO | 選択R1 | 期限優先参照（ヒューリスティック） |
|---|---:|---:|---:|
| 期限超過件数 | 6 | 0 | 0 |
| 割当予定時間（時間） | 68 | 68 | 68 |

- 参照方式は数学的な最適解ではありません。HOLDOUTの合成結果を実業務効果へ外挿できません。
- 要件診断ルーブリック Qwen: **PASS** / ODA: **PASS**
- 人間のデモ上書き承認: **NO**。上書き承認は元の診断HOLDをPASSに変更しません。
- R1 behavioral contract: **PASS** / stress: **NO_REGRESSION_DETECTED**
- 診断ベンチマーク 全試行PASS: **False** （単発診断との混同禁止）

## Diagnostic benchmark summary

| Model | Completed | PASS | Planned | Mean score |
|---|---:|---:|---:|---:|
| coding | 2 | 0 | 2 | 0.875 |
| finance | 2 | 0 | 2 | 0.875 |

## Business Value & Feasibility

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| BV-01 顧客課題と業務KPIの整合（合成ケース） | SUPPORTED_SYNTHETIC | 固定稼働でFIFOより期限超過が減ることを合成HOLDOUTで確認 [E01, E04] | 顧客の実データでSLA・処理時間・案件到着分布を検証する |
| BV-02 代替案の定量比較 | SUPPORTED_SYNTHETIC | FIFO・期限優先の固定ヒューリスティック・選択R1を同条件で比較済み。R1のKPI合格/不合格はBV-01で別判定 [E01, E04] | 顧客が承認した基準・失敗コストで代替案を再比較する |
| BV-03 MVPの範囲と承認ゲート | DEMO_CONTROLLED | 変更要件と人間のデモ承認が記録され、検証対象は担当者割当ロジックに限定 [E02, E03] | 顧客とスコープ、除外事項、受入基準を合意する |
| BV-04 実顧客の需要・支払意思 | UNVERIFIED | 公開された問題背景はE08に収録。実顧客の需要・支払意思・保険案件の処理フローは未検証 [E05] | 顧客ヒアリングと有償PoCの支払意思を確認する |
| BV-05 収益性・投資回収 | UNVERIFIED | 開発費・運用費・CAC・料金・期限超過削減の金銭価値は未実測 [E05] | 提案原価・運用負荷・回収可能額を見積もる |
| BV-06 外部証拠と当該事業課題の整合（限定的） | PUBLIC_PROBLEM_CONTEXT_ONLY | 原文の課題領域のみ確認。FIFO因果・顧客固有SLA・要件導出は実証していない [E08] | 当事者の一次資料と業務観測で問題原因を確認 |

## AI Delivery & Operational Readiness

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| AI-01 選択R1コードの隔離実行・制約検証 | SUPPORTED_SYNTHETIC | E2B実行済み。資格・容量などの制約を満たした。KPIの改善合否とは別 [E04] | 権限、ネットワーク出口、CPU/メモリ制限を含む実環境のセキュリティ審査を行う |
| AI-02 DEVとHOLDOUTの分離・再現性 | SUPPORTED_SYNTHETIC | DEVゲート通過コードを異なるseedのHOLDOUTで評価しハッシュを記録。KPI合否とは別 [E04] | seed追加・顧客分布の変動・回帰テストで頑健性を測る |
| AI-03 LLM要件診断の品質 | HOLD | 固定ルーブリックの初回・修復後の区別、未使用ブラインドケースの未実施・HOLD・失敗を確認する必要がある [E02, E07] | 多ケース・複数回の独立診断ベンチマークと誤判定分析を実施する |
| AI-04 人間の関与と監査可能性 | DEMO_CONTROLLED | 人間のデモ承認と要件改訂の追跡が可能 [E02, E03, E04] | 顧客側の権限分掌・承認者・監査保持期間を設計する |
| AI-05 業務ワークフロー・本番運用 | UNVERIFIED | 顧客基盤への統合、認証、SLA、障害対応、監視・復旧は未検証 [E05] | API・監査運用・例外処理・データ移行の設計レビューを行う |
| AI-06 法務・個人情報・規制 | UNVERIFIED | 実顧客のデータ処理、GDPR、保険規制との適合を検証していない [E05] | 適用法令、データ保護、委託契約、保険金判断の人間関与を専門家と確認する |
| AI-07 R1契約の振る舞い（期限と希少資格） | SUPPORTED_SYNTHETIC | 固定の期限優先・希少資格プローブで期待される割当を確認 [E06] | 追加の業務反例・プロパティテスト・顧客受入条件へ拡張する |
| AI-08 高負荷・資格偏在・短納期への頑健性 | SUPPORTED_SYNTHETIC | 固定した合成ストレスケースで制約を守り参照ヒューリスティックからの悪化は検出されず [E06] | 到着時刻・ピーク負荷・実顧客分布を使って再検証する |
| AI-09 要件種別に対応する合成受入評価 | SYNTHETIC_PROTOTYPE_ONLY | 進捗通知は独立した通知プロトタイプのみ。R1の担当者割当結果はこの要件の証明に使用しない [E08, E04, E06] | 顧客承認済みの受入条件と実業務APIで再検証 |

## Evidence register — 根拠の出所

| ID | 証拠種類 | ローカル出所 | 限界 |
|---|---|---|---|
| E01 | SYNTHETIC | runs/bb03c979-be51-475b-9224-56c3aa3c26ae/run.json | Local experiment result; not customer-reported |
| E02 | SYNTHETIC | proposals/d2f96820-a5d0-437e-8506-c54a660c5c91/proposal.json | Synthetic fixture; evidence IDs are application-defined |
| E03 | DEMO_CONTROLLED | approvals/298fb0b4-fefb-467e-90c9-f7ac7a089782/approval.json | Simulated approval, not actual client authorization |
| E04 | SYNTHETIC | experiments/8971936f-076f-4402-aba0-bdf26a8446a5/experiment.json | Synthetic E2B-based test; not production deployment |
| E05 | UNVERIFIED | No direct customer business data or authorized claims workflow attached (public contextual evidence is E08) | No independent external verification |
| E06 | SYNTHETIC | policy_validations/57c4b25c-b5eb-4230-8bf6-bc8935b5f231/validation.json | Selected synthetic behaviors only; not formal specification proof |
| E07 | SYNTHETIC | benchmarks/b373ec18-7a19-42d9-a5fe-a8f168e922d9/benchmark.json | Limited artificial cases; do not infer population-level model accuracy |
| E08 | PUBLIC_PROBLEM_CONTEXT_ONLY | workflows/5ea06547-9d3a-45f2-a5b9-a9aeaccdfd84/00b_human_evidence_review.json | Published problem context, not current client evidence, not proof of FIFO/skill scheduling |

証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ。
**合成の証拠IDは実在する顧客資料・一次資料ではありません。**

## Next validation actions

- **P1 / Customer / product owner**: 顧客の業務SLA・分布・処理時間・資格・例外を実測で確認
- **P1 / AI technical reviewer**: R1の行動プローブとストレス試験の結果を確認し、不合格時のみ修正する
- **P1 / AI technical reviewer**: 単発診断と診断ベンチマークを分離して誤判定を検証
- **P2 / Business development**: 実顧客ROI、PoC費用、採算、支払意思を検証
- **P2 / Delivery / compliance**: 本番ワークフロー、認証、監査・規制・データ保護を精査

## Audit metadata

- Local source snapshot SHA256 values (data integrity pointers, not signed attestations):

  - `experiment.json`: `293b34f72a03f7499cabdd4eafd7432b4e6525bf7a49f977336cb86266b92b74`
  - `run.json`: `b74acd2161ba04b70d772dc7a9476badbe484f6eabc4acb26d7b05cc2d35b286`
  - `proposal.json`: `3c5f99f5ba2d768ef77ae96c32402c4442dca71d9f0c4020c90fc4e0dd03810f`
  - `approval.json`: `493974f23f050ff169694b288f8df841e558e0d6d0eb9d361a392abb22342bc0`

Evidence ID correctness != evidence validity != diagnostic correctness. SIM-SLA-001 and report E01-E05 are local/synthetic references, not external citations. No customer, market, legal, regulatory or production approval is inferred.

## v0.21 Requirement trace

# Evidence → Requirement → Feature → Acceptance Trace (v0.19)

- Public evidence: PUB-001, PUB-003, PUB-004
- Requirement: Insurers need to improve timeliness and communication in claims processing
- Type: `claim_progress_updates` / Feature: `FEATURE-CLAIM-PROGRESS-NOTIFICATION`
- Human template mapping: `TEMPLATE_MAPPED_HUMAN_SELECTED`
- Target: `separate_deterministic_notification_prototype` (not the same as the published source)
- Reviewer: Technical reviewer (demo)

## KPI and acceptance tests

- KPI: `notification_coverage_pct`
- KPI: `maximum_status_update_delay_hours`
- KPI: `no_wrong_recipient`
- Acceptance test: `NOTIFY-ON-STATUS-CHANGE`
- Acceptance test: `NOTIFY-WITHIN-THRESHOLD`
- Acceptance test: `NOTIFY-CORRECT-RECIPIENT`
- Acceptance test: `NEGATIVE-CONTROL-NO-UPDATE`

## Proof boundary

- Citation exists ≠ citation supports claim ≠ requirement is correct.
- Public issue does not prove FIFO causality or customer-approved SLA.
- Scheduling R1 cannot satisfy a claim-progress notification requirement.
- The notification prototype is separate and not deployed or connected to customers.

## Evaluation

- Trace status: `SYNTHETIC_PROTOTYPE_ONLY`
- Result: `SUPPORTED_SYNTHETIC_PROTOTYPE`
- Synthetic pass: True
- Customer acceptance: NO; production approval: NO.
