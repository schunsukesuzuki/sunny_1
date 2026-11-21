# Project Feasibility Assessment — v0.13

> 合成・架空顧客に限定した技術プリセールス用の判断支援。実顧客・市場・法令・本番運用の適合を保証しません。

- Assessment ID: `db0e3f3e-5e97-4285-9f7b-e76300ca0dd0`
- Experiment ID: `e776ae09-b083-4408-91be-ff1cceed591b`
- Generated at (UTC): 2026-11-21T03:28:44+00:00
- Rubric: `PRESALES-ASSESSMENT-v0.13.0`
- Provisional decision: **GO** — stage `CUSTOMER_DISCOVERY` (CUSTOMER_DISCOVERY_ONLY)
- Production decision: **NO_GO** (production GO: **NO**)
- Rationale: 合成HOLDOUTの技術結果は有望。ただし事業価値と本番提供は未検証。人間の技術審査を前提とした顧客ディスカバリーへの移行のみ検討可能。

## 技術実験の要約

| 合成HOLDOUT | FIFO | 生成R1 | 期限優先参照（ヒューリスティック） |
|---|---:|---:|---:|
| 期限超過件数 | 6 | 0 | 0 |
| 実働時間（時間） | 68 | 68 | 68 |

- 参照方式は数学的な最適解ではありません。HOLDOUTの合成結果を実業務効果へ外挿できません。
- 要件診断ルーブリック Qwen: **HOLD** / ODA: **PASS**
- 人間のデモ上書き承認: **NO**。上書き承認は元の診断HOLDをPASSに変更しません。

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
| AI-03 LLM要件診断の品質 | HOLD | 少なくとも一方が独立ルーブリックでHOLD。承認履歴でHOLDは解消されない [E02] | 多ケース・複数回の独立診断ベンチマークと誤判定分析を実施する |
| AI-04 人間の関与と監査可能性 | DEMO_CONTROLLED | 人間のデモ承認と要件改訂の追跡が可能 [E02, E03, E04] | 顧客側の権限分掌・承認者・監査保持期間を設計する |
| AI-05 業務ワークフロー・本番運用 | UNVERIFIED | 顧客基盤への統合、認証、SLA、障害対応、監視・復旧は未検証 [E05] | API・監査運用・例外処理・データ移行の設計レビューを行う |
| AI-06 法務・個人情報・規制 | UNVERIFIED | 実顧客のデータ処理、GDPR、保険規制との適合を検証していない [E05] | 適用法令、データ保護、委託契約、保険金判断の人間関与を専門家と確認する |

## Evidence register — 根拠の出所

| ID | 証拠種類 | ローカル出所 | 限界 |
|---|---|---|---|
| E01 | SYNTHETIC | runs/9e823f64-e27a-4a2a-951c-d21412cbbdcb/run.json | Local experiment result; not customer-reported |
| E02 | SYNTHETIC | proposals/1a7ec7e9-f3c8-4359-b17f-7bb04bca9896/proposal.json | Synthetic fixture; evidence IDs are application-defined |
| E03 | DEMO_CONTROLLED | approvals/46aa646e-b6f5-4cd5-b11c-0fc90d89e6a8/approval.json | Simulated approval, not actual client authorization |
| E04 | SYNTHETIC | experiments/e776ae09-b083-4408-91be-ff1cceed591b/experiment.json | Synthetic E2B-based test; not production deployment |
| E05 | UNVERIFIED | No external/customer evidence attached | No independent external verification |

証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ。
**合成の証拠IDは実在する顧客資料・一次資料ではありません。**

## Next validation actions

- **P1 / Customer / product owner**: 顧客の業務SLA・分布・処理時間・資格・例外を実測で確認
- **P1 / AI technical reviewer**: モデル診断HOLDの誤判定を再現し、独立レビューを継続
- **P2 / Business development**: 実顧客ROI、PoC費用、採算、支払意思を検証
- **P2 / Delivery / compliance**: 本番ワークフロー、認証、監査・規制・データ保護を精査

## Audit metadata

- Local source snapshot SHA256 values (data integrity pointers, not signed attestations):

  - `experiment.json`: `1733b34b74dd8f2812bc0ed2e36e2ef143d025544bdef72144b2ff5b3014341f`
  - `run.json`: `ee0c7a1ee3f063ecd3ab328fc2e20f5b5760995ebcb5b17a911231a24a3d5c27`
  - `proposal.json`: `4546417ec630fe6d0fb8e2b161f1c2d20570cd9ed0a77e6e692daa59af63a0ee`
  - `approval.json`: `a17bde2730ceac364883e27c179fc06e131d478f0b6026e558e5496161f01658`

Evidence ID correctness != evidence validity != diagnostic correctness. SIM-SLA-001 and report E01-E05 are local/synthetic references, not external citations. No customer, market, legal, regulatory or production approval is inferred.
