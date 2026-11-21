# Project Feasibility Assessment — v0.14

> 合成・架空顧客に限定した技術プリセールス用の判断支援。実顧客・市場・法令・本番運用の適合を保証しません。

- Assessment ID: `eadc70ea-8ab3-4be8-800f-a309b195105b`
- Experiment ID: `e6271dae-951f-44a4-a512-a4f264989dfc`
- Generated at (UTC): 2026-11-21T05:26:51+00:00
- Rubric: `PRESALES-ASSESSMENT-v0.14.0`
- Provisional decision: **HOLD** — stage `TECHNICAL_VALIDATION` (HOLD_POLICY)
- Production decision: **NO_GO** (production GO: **NO**)
- Rationale: 独立KPI評価・承認・仕様の振る舞い・ストレス評価のいずれかが不足。顧客提案前にHOLDを確認する。

## 技術実験の要約

| 合成HOLDOUT | FIFO | 生成R1 | 期限優先参照（ヒューリスティック） |
|---|---:|---:|---:|
| 期限超過件数 | 6 | 0 | 0 |
| 割当予定時間（時間） | 68 | 68 | 68 |

- 参照方式は数学的な最適解ではありません。HOLDOUTの合成結果を実業務効果へ外挿できません。
- 要件診断ルーブリック Qwen: **HOLD** / ODA: **HOLD**
- 人間のデモ上書き承認: **YES**。上書き承認は元の診断HOLDをPASSに変更しません。
- R1 behavioral contract: **HOLD** / stress: **REVIEW_REQUIRED**
- 診断ベンチマーク 全試行PASS: **False** （単発診断との混同禁止）

## Diagnostic benchmark summary

| Model | Completed | PASS | Planned | Mean score |
|---|---:|---:|---:|---:|
| coding | 2 | 0 | 2 | 0.6875 |
| finance | 2 | 0 | 2 | 0.8125 |

## Business Value & Feasibility

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| BV-01 顧客課題と業務KPIの整合（合成ケース） | SUPPORTED_SYNTHETIC | 固定稼働でFIFOより期限超過が減ることを合成HOLDOUTで確認 [E01, E04] | 顧客の実データでSLA・処理時間・案件到着分布を検証する |
| BV-02 代替案の定量比較 | SUPPORTED_SYNTHETIC | FIFO・期限優先の固定ヒューリスティック・生成R1を同条件で比較 [E01, E04] | 顧客が承認した基準・失敗コストで代替案を再比較する |
| BV-03 MVPの範囲と承認ゲート | DEMO_CONTROLLED | 変更要件と人間のデモ承認が記録され、検証対象は担当者割当ロジックに限定 [E02, E03] | 顧客とスコープ、除外事項、受入基準を合意する |
| BV-04 実顧客の需要・支払意思 | UNVERIFIED | 顧客インタビュー、受注、価格受容の外部証拠なし [E05] | 顧客ヒアリングと有償PoCの支払意思を確認する |
| BV-05 収益性・投資回収 | UNVERIFIED | 開発費・運用費・CAC・料金・期限超過削減の金銭価値は未実測 [E05] | 提案原価・運用負荷・回収可能額を見積もる |

## AI Delivery & Operational Readiness

| 評価項目 | 状態 | 根拠 | 次の検証 |
|---|---|---|---|
| AI-01 生成コードの隔離実行・制約検証 | SUPPORTED_SYNTHETIC | E2B実行結果と独立評価器で資格・容量・処理を評価 [E04] | 権限、ネットワーク出口、CPU/メモリ制限を含む実環境のセキュリティ審査を行う |
| AI-02 DEVとHOLDOUTの分離・再現性 | SUPPORTED_SYNTHETIC | 異なるseedでDEV/非開示HOLDOUTを分離しコードハッシュを記録 [E04] | seed追加・顧客分布の変動・回帰テストで頑健性を測る |
| AI-03 LLM要件診断の品質 | HOLD | 単発診断PASSは十分でない。独立ベンチマークの未実施・HOLD・未完了を含めてレビューが必要 [E02, E07] | 多ケース・複数回の独立診断ベンチマークと誤判定分析を実施する |
| AI-04 人間の関与と監査可能性 | DEMO_CONTROLLED | モデル診断HOLDを保持したままデモ上の人間審査で技術検証を継続 [E02, E03, E04] | 顧客側の権限分掌・承認者・監査保持期間を設計する |
| AI-05 業務ワークフロー・本番運用 | UNVERIFIED | 顧客基盤への統合、認証、SLA、障害対応、監視・復旧は未検証 [E05] | API・監査運用・例外処理・データ移行の設計レビューを行う |
| AI-06 法務・個人情報・規制 | UNVERIFIED | 実顧客のデータ処理、GDPR、保険規制との適合を検証していない [E05] | 適用法令、データ保護、委託契約、保険金判断の人間関与を専門家と確認する |
| AI-07 R1契約の振る舞い（期限と希少資格） | HOLD | KPI改善と独立に検証するR1の行動プローブが未実施または不合格 [E06] | 追加の業務反例・プロパティテスト・顧客受入条件へ拡張する |
| AI-08 高負荷・資格偏在・短納期への頑健性 | HOLD | ストレステストが未実施、制約違反、または固定参照より期限超過/未割当が多いケースあり [E06] | 到着時刻・ピーク負荷・実顧客分布を使って再検証する |

## Evidence register — 根拠の出所

| ID | 証拠種類 | ローカル出所 | 限界 |
|---|---|---|---|
| E01 | SYNTHETIC | runs/7ec35f52-2ceb-404f-9cc8-42fc30aa0069/run.json | Local experiment result; not customer-reported |
| E02 | SYNTHETIC | proposals/31e61107-bb23-49fd-bdc7-d3d0f30cf162/proposal.json | Synthetic fixture; evidence IDs are application-defined |
| E03 | DEMO_CONTROLLED | approvals/b2513311-89ee-4346-bfcf-fc633b4c08ee/approval.json | Simulated approval, not actual client authorization |
| E04 | SYNTHETIC | experiments/e6271dae-951f-44a4-a512-a4f264989dfc/experiment.json | Synthetic E2B-based test; not production deployment |
| E05 | UNVERIFIED | No external/customer evidence attached | No independent external verification |
| E06 | SYNTHETIC | policy_validations/4089d035-f16a-4444-b78a-e7ad760cd8a3/validation.json | Selected synthetic behaviors only; not formal specification proof |
| E07 | SYNTHETIC | benchmarks/83cbfda3-f679-4892-8cfd-cc2306a6bf4d/benchmark.json | Limited artificial cases; do not infer population-level model accuracy |

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

  - `experiment.json`: `8a53b127e1b70b3f998b91c15c7ef37397d562bd01eaf4fa5b063d4615e7ffda`
  - `run.json`: `dcf47fa7ed9f92e6183d548065c3d2133f1a68c7e1f04411defce3c468af787c`
  - `proposal.json`: `e53ffb07853a2122cf2ae7b23401f95a3b36978dbdd897fbaf154b5490341d54`
  - `approval.json`: `8765cf56cee0a65f23c11f0353c17c8b3c615f7cc9b7013ff880267f46c33362`

Evidence ID correctness != evidence validity != diagnostic correctness. SIM-SLA-001 and report E01-E05 are local/synthetic references, not external citations. No customer, market, legal, regulatory or production approval is inferred.
