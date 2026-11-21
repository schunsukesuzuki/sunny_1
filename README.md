> **v0.15 — 01〜09 Full Workflow:** 画面10から、顧客入力 → Qwen設計 → R0 E2B → Qwen/ODA独立診断 → **人間承認待ち** → R1生成/評価 → 履歴インデックス → 診断ベンチマーク＋R1仕様/ストレス → 二軸事業評価をまとめて実行し、失敗も含めて1つのZIPへ保存します。承認/却下は必ず人間が明示します。詳細は `docs/v015-full-workflow.md`。

> **v0.14（旧方式の説明） — R1 Policy / Stress Validation + One-Click Audit Export:** 既存R1の候補コードを再実行し、期限優先・希少資格を巡る行動プローブ、合成ストレス4シナリオ、Qwen/ODAの固定診断ベンチマーク、二軸事業評価を一度に実行し、完全な証跡を単一ZIPへ保存します。旧API `/api/pipeline/run-and-save` で利用できます。v0.15の画面10は新しい01〜09一括方式に置き換わっています。**元のR0/R1実験・人間承認は改変せず、取得失敗時はPARTIAL ZIPと欠落理由を保存します。** 仕様：`docs/v014-complete-audit-pipeline.md`。

> **v0.13 — Business & Delivery Assessment:** 新しい手順09で、保存したR1実験を「Business Value & Feasibility」と「AI Delivery & Operational Readiness」の2軸で根拠付き評価。Markdown/証跡ZIPを出力できます。**合成の技術PASSは実顧客・本番のGOではありません。** 評価にはLLMを使わず、特定個人の氏名・所属は評価基準やレポートに含めません。仕様：`docs/v013-business-assessment.md`。

> **v0.12 UI refresh:** 画面冒頭に「このアプリの目的・8ステップの機能案内」と「証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ」の説明を追加。低コントラストのダークUIを落ち着いたライト配色に変更しました。v0.10のバックエンドAPI・検証ロジック・監査保存を維持しています。詳細は `docs/v012-ui-guide.md`。

> **v0.10:** 要件診断の多軸独立採点・Qwen/ODAの合成ベンチマーク・過去ログ再採点を追加。詳細は `docs/v010-requirement-diagnostic-benchmark.md`。

# Claims Operations Planner — AI Venture Feasibility Studio v0.15

ドイツの保険業務SaaS企業（**架空**）の事業開発PoC。**Qwen3-Coder 30B** はサービス設計・Pythonコード生成、**OpenDataArena/ODA-Fin-RL-8B** は金融ドメイン要件診断を担当。E2Bは生成コードを隔離して実行し、独立した決定的評価器で審査割当・期限・資格・稼働上限を検証します。v0.8にあったMarkdown結果保存を維持し、生成コード・差分・各試行のE2B実行証跡・履歴取得を拡張しました。

> **技術デモです**：実顧客データもEU法令検索もありません。ODA-Fin-RL-8Bは金融推論モデルであり、EU保険規制への専門適合が実証されたモデルではありません。請求の支払可否・不正判定や法的判断は自動化しません。モデルの評価は合成データと模擬顧客証拠に限定されます。

## 新規事業仮説

想定顧客：ドイツ国内の保険業務SaaSベンダー（架空）。欧州複数国展開は事業仮説。Claims Operations Plannerを追加し、固定審査人員・総審査時間のもとで期限超過件数を減らす。

- **R0**：到着順FIFOで担当者を割り当てる。独立評価器で「R0の仕様を正確に実装した」と確認。
- **模擬反証** `SIM-SLA-001`：正しく動くFIFOでも後着の短納期案件を遅延させ得る。
- **診断比較**：Qwen-CoderとODA-Fin-RL-8Bが、同じ**DEV結果と模擬証拠**を独立に診断。R0実装の正しさと事業要件の妥当性を明示的に区別。
- **独立ゲート**：ODAが「実装バグではない」と理解できたかをルールで確認。理由と分類に矛盾があればHOLD。利用不可ならエラーとして保存し、Qwenへ黙って代替しない。
- **人間の承認**：R1はアプリ側で定義した実験用契約。ODAの提案そのものを自動承認・評価基準へ採用しない。承認前にコード生成へ進まない。
- **R1生成**：承認後、ODAの構造化診断を**参考情報としてQwenのプロンプトへ追加**し、固定R1契約に基づいてコードを生成。
- **R1評価**：E2BでDEV修正最大2回。新しいHOLDOUTは選択後一度だけ。FIFO/固定期限優先/生成コードを同じ合成データで比較。
- **事業妥当性**：**UNVERIFIED**。合成KPIは顧客価値や規制適合の証拠になりません。

## Mac Studioでの実行環境

- macOSでネイティブのOllamaを実行（利用可能ならMetal加速）。Dockerコンテナから `host.docker.internal:11434` に接続。
- Docker Compose：FastAPI + React/Vite。E2B Python SDKには `E2B_API_KEY` 必須。
- **2モデルが必要**。ODAだけの評価に置換してQwenの生成処理を削除したものではありません。

### 1. Ollamaにモデルを準備

```bash
# 既存コード生成モデル
ollama pull qwen3-coder:30b

# ODA-Fin-RL-8Bのコミュニティ製Q4_K_M GGUF（Mac Studio向け簡便な経路）
ollama pull hf.co/alexsabaka/ODA-Fin-RL-8B-GGUF:Q4_K_M

# 両モデルを確認
ollama list
```

ODAの**オリジナル**の公開元：<https://huggingface.co/OpenDataArena/ODA-Fin-RL-8B>（Qwen3-8B系、Apache-2.0、BF16）。上記のGGUFは**第三者の量子化版**です：<https://huggingface.co/alexsabaka/ODA-Fin-RL-8B-GGUF>。同じ重み・推論精度を保証しません。原版の忠実性を比較したい場合は公式Safetensorsを別途取得し、Ollama公式Import手順に従って読み込んで `ODA_FIN_MODEL` を変更してください。モデル自体の重みはZIPに含めません。

モデルIDがアプリに反映される設定は `.env.example` の `ODA_FIN_MODEL` です。量子化版が動作しない場合は利用環境・Ollamaバージョンの互換性を確認してください。

### 2. Docker Compose

```bash
bash scripts/setup-env.sh
# .env に E2B_API_KEY=... を設定。鍵をGitへコミットしない。
docker compose up --build
# http://localhost:5173
```

既にOllamaアプリが常駐している場合、別途 `ollama serve` は不要です。`bash scripts/preflight-mac.sh` で接続とモデル有無を確認できます。

### 3. UI操作（v0.15）

1. **顧客課題とR0サービス設計**：架空ブリーフ・seedを選択。
2. **R0をE2B実行**：FIFO実装の仕様適合とDEV指標を確認。
3. **Qwen × ODAで独立診断**：`SIM-SLA-001` を与え、両モデルの分類・理由・改訂提案を比較。証拠なしの対照条件も試せます。
4. **人間がR1を承認**：ODAが品質ゲートPASSなら通常承認。HOLDでも、模擬反証と独立R0 PASSを人間が確認し、HOLDを残して明示的な理由を記録すれば、技術デモのみ継続できます。
5. **R1生成・E2B検証**：ODAの診断を参考情報としてQwenへ渡し、独立評価器で資格・日別容量・期限超過・同一審査時間を評価。
6. **レポートと全証跡ZIP**：成功・失敗の記録をMac側 `./artifacts/` へ保存。「保存した実験と監査証跡」から過去の結果を読み直せます。
7. **08診断品質ベンチマーク**：QwenとODAへ同じ合成ケース・同じschemaを与えて独立採点。過去のproposal IDを再採点可能（非破壊）。
8. **09 Business & Delivery Assessment**：R1実験IDを入力（06から自動入力、または07の履歴から選択）、二軸評価を生成。**v0.14の新しい仕様・ストレス・ベンチマークをまだ紐づけていない場合、HOLD_POLICY**となります。
9. **10 一括実行＋保存**：承認済みR1の実験IDを選択し、08で指定した診断ベンチマークのケース/回数を利用して、行動プローブ・ストレス・診断・事業評価を連続実行。ブラウザが単一の完成ZIPをダウンロードし、Mac側 `artifacts/exports/<uuid>/complete_audit_package.zip` にも保存。PARTIALでも欠落一覧が入ります。

## 保存・監査

Mac側のDocker bind mount `./artifacts:/app/artifacts` を使用。主な保存構成：

```text
artifacts/
  runs/<uuid>/
    run.json, report.md, fifo.py, deadline_reference.py, dataset_hashes.json
    e2b_{fifo,deadline}_seed_*.json       # sandbox ID / stdout / stderr / output / hashes
  proposals/<uuid>/
    request.json, proposal.json           # QwenとODAの構造化診断・ルーブリック
    diagnostic_error.json                 # モデル接続・応答失敗時のみ
    decision.json
  approvals/<uuid>/
    approval.json, evaluation_started.json
    generated_<uuid>.py, generated_<uuid>.json
  benchmarks/<uuid>/
    started.json, trial_*.json, benchmark.json, report.md  # v0.10新規
  assessments/<uuid>/
    assessment.json, report.md              # v0.13新規・入力4文書のハッシュを記録
  policy_validations/<uuid>/
    started.json, validation.json, report.md
    behavior_input_*.json, behavior_generated_seed_*.json
    stress_input_*.json, stress_{fifo,deadline,generated}_seed_*.json
  workflows/<uuid>/
    workflow.json, 01_input.json, 02_service_design.json, 07_history_snapshot.json
    03_r0_started.json, 04_proposal_started.json, 08_benchmark_started.json, 08b_policy_started.json
  exports/<uuid>/
    manifest.json, complete_audit_package.zip  # 01〜09フル実行中は随時更新
    started.json, summary.md                   # 旧v0.14 APIの場合
  experiments/<uuid>/
    started.json, experiment.json, report.md, input_candidate.py, selected_r1.py
    attempt_00.py, attempt_00.json, attempt_00.diff, ...
    dev_reference_*_seed_*.json, dev_attempt_*_seed_*.json, holdout_*_seed_*.json
    error.json                             # 実行初期化失敗時
```

E2B stdout/stderrはSDK側で**末尾3000文字に制限して保存**します。プロンプト文全文・モデル内部の非公開推論過程は保存しませんが、モデルID、構造化診断、改訂根拠、コードハッシュ、評価結果、実行証跡を保存します。APIキーは出力物に書きません。実験コードを直接変更する場合は機密情報を含めないでください。

### v0.10：モデル診断の独立評価

- Qwen・ODAの両方について**原因分類の正しさと説明の整合性を別々に採点**します。品質PASSとHOLDはR1の技術的KPIとは独立です。
- 合成反例での「要件・事業目的不一致」と、実顧客の要件妥当性（常に`UNVERIFIED`）を分離します。
- モデルの改訂案が「厳密FIFOを維持しながら期限を第一優先」とする矛盾や、根拠IDの欠落を検出します（ヒューリスティックであり形式検証ではありません）。
- ODAの回答を利用して生成コードを改善したかという**因果効果**は現時点では証明していません。R1契約は依然として事前定義です。
- 過去v0.9.1の`artifacts/`を新フォルダへコピーすれば旧proposal IDを再採点できます。旧ログを上書きしません。

詳細な試験シナリオ・実行方法・評価限界：`docs/v010-requirement-diagnostic-benchmark.md`

### API（主要）

- `GET /api/sample`、`GET /api/health`、`POST /api/design`
- `POST /api/run-r0`：R0参照実装をE2Bで評価
- `POST /api/propose`：Qwen / ODAの**独立**要件診断
- `POST /api/approve`：承認・却下（ODA HOLD時は承認拒否）
- `POST /api/generate-r1`：ODA診断を参考情報として渡しQwenで生成、生成コード保存
- `POST /api/evaluate-r1`：DEV修正→単回HOLDOUT、全試行保存
- `POST /api/policy-validation/run`：保存済みR1選択コードをE2Bで追加検証（非破壊）
- `POST /api/full-run/start`：01〜04を開始（非同期）、05で停止
- `POST /api/full-run/approve-and-continue`：人間の明示的な承認/却下。承認なら06〜09＋検証を非同期実行
- `GET /api/full-run/{uuid}` / `GET /api/full-run/{uuid}/bundle`：進捗・状態と完全/部分ZIPの取得
- `GET /api/history/workflows`：01〜09の一括実行履歴
- `POST /api/pipeline/run-and-save`：旧v0.14互換。承認済みR1から追加検証してZIP化（新UIでは未使用）
- `GET /api/exports/{uuid}/bundle`：完成/一部失敗を記録した全証跡 ZIP（manifest.json / SHA256付き）
- `GET /api/history/{runs|proposals|approvals|experiments|benchmarks|assessments|policy_validations|exports|workflows}`：履歴一覧
- `GET /api/artifacts/{kind}/{uuid}`：保存JSON再取得
- `GET /api/artifacts/{kind}/{uuid}/bundle`：関連親実験含む証跡ZIP
- `GET /api/runs/{uuid}/report`、`GET /api/experiments/{uuid}/report`
- `POST /api/business-assessment/run`、`GET /api/business-assessment/{uuid}/report`、`GET /api/history/assessments`

## 独立の検証規則

- R0契約：FIFO参照割当への完全一致。R1の旧評価：資格、日別稼働上限、重複・欠損・過剰勤務なし。期限超過、**割当予定時間**、期限内率を別々に集計。
- **v0.14追加：R1の期限優先・希少資格の行動プローブを固定合成反例で独立検査。** KPIのPASSは契約振る舞いのPASSを意味しません。さらに容量圧迫・技能ボトルネック・期限短縮・到着順変化を試験し、未割当も期限超過に含めます。これは形式証明ではありません。
- ODA要件診断の固定ルーブリック：分類が `requirement_mismatch`、R0実装が `correct`、ビジネス要件が `mismatch`、証拠IDが `SIM-SLA-001`、改訂提案に期限が反映され、根本原因を誤って「software bug」と呼ばないこと。**単純な独立ルールであり、推論の意味的正しさを保証するものではありません。**
- HOLDOUTは生成・選定後に1回だけ使用し、両モデルへプロンプトとして渡さない。
- 技術PASSはあくまで合成データについて。R1契約は実験用の固定ルールであって、ODAの自由生成要件が直接テストされたわけではありません。

## テスト

```bash
cd backend
python -m pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
```

E2BとOllamaをモックしたバックエンドテストのみをローカルで実施しました。v0.14の二軸評価自体はモデル推論を呼びませんが、手順10の一括実行ではE2BとOllamaを実際に呼び出します。v0.15の追加統合テストは承認待ち・承認後・却下・エラー保存・ZIPハッシュをモックで検証しました。実Mac Studio上のQwen/ODA推論、E2Bクラウド、フロントエンドの本番ビルドはこの環境では未検証です。

## 対照条件と限界

- 同じ条件でQwenのみとODA併用の違いを比較可能ですが、今回のPoCは**複数seed・複数独立ドメイン事例にわたるモデル優位性の証明ではありません**。
- 顧客のSLA、BaFin/EIOPA等の規制資料、GDPR、データ委託の根拠はモデルに与えていません。法令準拠の判定をしてはいけません。
- 欧州複数市場への横展開、商品化・価格受容、ドイツ居住体制も未検証の事業仮説です。
- APIは**単一ユーザーのローカルデモ**用で認証・レート制限がありません。外部に公開しないでください。
- 参照「期限優先」アルゴリズムはヒューリスティックで、数学的な大域最適性は主張しません。

詳細：`docs/v09-vertical-fm-experiment.md`、`docs/v08-claims-experiment-protocol.md`、`docs/io-contract.md`。

### v0.10 API additions

- `GET /api/diagnostic-benchmark/fixtures` — Synthetic public inputs without oracles.
- `POST /api/diagnostic-benchmark/run` — body `{"case_ids":["fifo_sla_conflict","actual_fifo_implementation_bug"],"repetitions":1}`. Runs both Ollama models sequentially.
- `GET /api/diagnostic-benchmark/{benchmark_id}/report` — Markdown.
- `GET /api/diagnostic-benchmark/rescore/{proposal_id}` — non-mutating regrade of stored v0.9.1 outputs.
- `GET /api/history/benchmarks`, `GET /api/artifacts/benchmarks/{uuid}/bundle` — audit history and evidence ZIP.

### v0.14 legacy additional export example (not used by step 10)

```bash
curl -X POST http://localhost:18000/api/pipeline/run-and-save \
  -H 'Content-Type: application/json' \
  -d '{"experiment_id":"<approved-r1-experiment-uuid>","case_ids":["fifo_sla_conflict","actual_fifo_implementation_bug"],"repetitions":1}'
# Returns {export_id, bundle_url, manifest, assessment, status}; use frontend 10 for automatic ZIP download.
```

**人間の改訂承認を省略する自動実行ではありません。** 手順01–06を先に実施してください。ZIP内の`00_START_HERE.md`が読み順、`manifest.json`が収録一覧と生バイトSHA256・欠落/失敗の完全な一覧です。承認者名はレポート・AI採点プロンプトには入りませんが、根拠となる `approval.json` に入力した承認者名が保持されます。外部共有前に確認してください。

### Local tests

```bash
cd backend
PYTHONPATH=. pytest -q tests
```

The tests use mocked E2B/LLM calls and separately check the deterministic scenario grader. They do not prove real Mac Ollama/GGUF inference, production claims processes, EU compliance, or frontend dependency installation.
