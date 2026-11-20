# AI Venture Feasibility Studio — v0.6

**事業仮説 → 要件ドラフト → サービス設計（新規） → コード生成 → E2B実証 → 実装・要件の二軸審査 → 改訂案 → 監査可能なレポート**を、React + FastAPI + macOS上のOllamaで一貫して実行する、**非公式の独立開発サンプル**です。Sun Asteriskの公式サービス・実顧客案件ではありません。

題材は架空の**教育SaaS企業による週次学習計画の自動生成サービス**です。三橋さんのような新規事業支援担当者が検証のための証拠をそろえ、事業責任者・技術責任者が人間として判断するシナリオを想定しています。

## v0.6 の追加機能（v0.5の検証契約・改訂ループを維持）

**最大の変更：コードの正しさと要件自体の妥当性を別々に判定**します。合成データ上でのCONDITIONAL GOは、顧客価値の証明になりません。

1. `/api/analyze`で要件ドラフトを生成し、人間が編集。`AC-01`等の受入基準を定義。
2. **`/api/design`でサービス設計をJSON中間表現として生成**し、人間がActor、ユースケース、業務フロー、ハード制約、代替案、受入テストを確認・編集。
3. `/api/generate`へサービス設計を渡しQwen3-Coderが候補を生成。v0.5と同じ固定Greedy・厳密DP・生成候補をE2Bで比較。コード修正の内側ループ、DEV/HOLDOUT分離、機能不合格時のHOLDOUTスキップは保持。
4. **顧客証拠台帳**：`AC-01`等の要件に対して、`synthetic` / `real_customer` / `stakeholder` / `desk_research` の出典、観測、支持/反証、参照ID、人間の確認状況を記録。実顧客由来と申告され出典・人間の確認がある証拠だけから、**暫定的な**要件判定を作成（`UNVERIFIED`、`SUPPORTED_PRELIMINARY`、`REJECTED_PRELIMINARY`、`CONFLICTED`）。いずれも最終承認はしない。
5. **`/api/refine`が要件改訂を提案**。Qwenに送るのはDEV側の診断・集計結果と明示的な顧客証拠だけで、HOLDOUT結果は送らない。提案を自動適用せず、UI上の採用操作が必要。
6. 採用時に要件改訂番号を上げ、サービス設計を作り直す。**改訂ごとに別のHOLDOUT seed群**を使う（初回`seed+10000`、改訂1回目`seed+20000`）。DEVは同じseedを使って仮説修正を継続できるが、評価器の仕様は改訂前後で独立に固定。
7. 新しい成果物：`service_design.json`、`customer_evidence.json`、`requirement_assessment.json`、`requirement_change_log.json`、`project.json`。既存の試行コード・差分・Sandboxログ・Markdown/JSONレポートも保持。

**スコープに関する重要事項：** 現在E2Bで実行可能な数理最適化ベンチマークはv0.5から引き継いだ**教育SaaSの整数時間配分**のみです。ドイツ/欧州のInsurTech向け`Claims Operations Planner`は `docs/eu-insurtech-concept.md` に**設計検討用ケース**として収録しました。顧客の審査資格・期限・担当者の個別稼働制約を満たす実行可能な保険システムではなく、実証済みと表示しません。

**AI生成設計とアプリ内の固定評価器を分離**：UIからハード制約を記述し直しても、固定されたE2B教育ベンチマークのテストが自動で変更されるわけではありません。要件変更がベンチマークの入出力契約・目的関数まで変える場合は、独立評価器を人間が更新して再検証する必要があります。

## v0.5の重要な改修

v0.4で**Qwenが全ての試行において科目重複・時間不一致でNO-GOになったにもかかわらず、最後の試行が「採用」に選ばれてHOLDOUTを実行した**問題を修正しました。

- **全DEV試行NO-GOなら採用候補なし**：`selected_attempt_index = null`、`holdout_executed = false`、`generated = null`。`generated.py`は保存しません。DEVの不合格コードとログは`attempts/`にすべて保存します。
- **HOLDOUTの実行を省略**：無効な候補に対して最終Sandboxを起動しないため、無駄なE2B消費を防ぎます。UIとレポートの学習計画表示はDEVの固定Greedy・厳密DPのみの比較として明示し、Qwen配分はN/Aにします。
- **段階的なエラー診断**：最初の修正では独立評価器のエラーをカテゴリ別に集約（重複科目・時間不一致など）、代表例とJSON入出力契約をフィードバックします。2回目以降の機能修正では不変条件（制約値を変更しない・累積配分時間を管理・限界効用を正しく計算・科目を1回のみ出力）と静的ASTのヒューリスティック警告を追加します。
- **関数単位の修正**：2回目以降の機能修正は`allocate_hours`の関数定義だけをQwenに生成させ、ASTの行範囲で元の関数を置換します。周辺コードの全体再生成を避けます。対象関数がない／パッチが不正な場合はエラーとして記録し、成功を偽装しません。
- **監査可能な修正履歴**：各試行の`repair_strategy`、エラー分類、前回試行との差分、SandboxログをJSONとMarkdownに保存。`attempt_XX.diff`も出力します。差分は表示上の長さを制限し、完全な各試行コードを別途保存します。
- **品質HOLDでも改善**：v0.4の機能は維持。Functional PASS候補だけからDEV代理効用で選び、HOLDOUTで1回のみ評価。最終結果をLLMへフィードバックしません。

**注意**：実装は架空教育SaaSの評価契約に特化しています。静的コード診断は根本原因の証明ではなく改善のヒントです。利用者が任意の顧客案件を貼るだけで安全かつ正確に実験が自動生成される汎用製品ではありません。

## 動作環境・アーキテクチャ

| コンポーネント | 実装 | 実行場所 |
|---|---|---|
| UI | React 19 / TypeScript / Vite | Docker Compose |
| API・要件・技術審査・レポート | FastAPI / Pydantic | Docker Compose |
| 基盤モデル | **Qwen3-Coder 30B**（オープンウェイト） | **macOSネイティブOllama／Apple Metal** |
| Pythonコード実行 | E2B SDK | **E2Bクラウドの隔離Sandbox** |
| 評価器 | コード非依存の決定的関数 | FastAPI（LLMから独立） |

**Apple GPU上の推論を利用するため、OllamaをDocker内では起動しません。** Dockerからは`host.docker.internal:11434`を経由してMac側のOllamaを呼びます。生成されたPythonコードはMacやAPIコンテナ内で直接実行せず、E2B上で実行します。

## セットアップ（Mac Studio）

### 1. OllamaとMetalの確認

```bash
curl -fsS http://127.0.0.1:11434/api/tags
ollama pull qwen3-coder:30b
ollama run qwen3-coder:30b "Write a correct Python marginal-gain allocation function."
ollama ps
```

Ollamaアプリがすでにポート11434を使用している場合、`ollama serve`を別途実行する必要はありません。`ollama ps`の`PROCESSOR`欄でGPU利用を確認してください。モデルの保存容量のみではMac Studioのメモリ容量は判断できません。

### 2. `.env`の作成

ZIPに`.env.example`を同梱しています。APIキーを含んだ`.env`は**含まれていません**。

```bash
bash scripts/setup-env.sh
nano .env
```

必要な設定例（キーは必ずご自身のものに差し替え）：

```dotenv
E2B_API_KEY=ここにご自身の実際のAPIキー
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3-coder:30b
OLLAMA_TIMEOUT_SECONDS=240
E2B_SANDBOX_TIMEOUT_SECONDS=180
E2B_COMMAND_TIMEOUT_SECONDS=45
API_PORT=18000
WEB_PORT=5173
```

`.env`内のURLはMarkdownリンクやバックスラッシュを付けず、そのまま記載してください。**APIキーをGitHubやチャットに公開しないでください。**

既存v0.3の`.env`はコピーして利用できます。v0.3が同じホストの5173番で動いている場合は、まず既存ディレクトリで`docker compose down`してください（もしくは新しい`.env`で`WEB_PORT=5174`等に変更。ただしVite開発サーバーの許可オリジンは5173番前提です）。

### 3. Docker Composeで起動

```bash
docker compose up --build -d
docker compose ps
bash scripts/preflight-mac.sh
```

- **Web:** http://127.0.0.1:5173
- **FastAPI Docs:** http://127.0.0.1:18000/docs
- **API health:** http://127.0.0.1:18000/api/health

**以前のポート8000競合を回避**するため、公開設定は`127.0.0.1:${API_PORT:-18000}:8000`です。Viteの`/api`プロキシはDocker内部の`http://api:8000`を利用します。ホスト側のAPIポートを変更してもフロントエンドの接続先を変更する必要はありません。

APIキー状態を表示せずに確認：

```bash
curl -fsS http://127.0.0.1:18000/api/health
docker compose exec api python -c 'import os; print("E2B configured:", bool(os.getenv("E2B_API_KEY", "").strip()))'
```

## UIでの実行手順

1. **顧客相談を入力**し、Qwenで要件ドラフトを作成。未確認事項を人間がレビュー・編集。
2. **Qwenでサービス設計案を生成**。Actors、ユースケース、サービスフロー、制約、代替案、受入テストを編集。
3. **Qwenが第三の方式をPythonで生成**。サービス設計を中間表現として渡し、コードを編集可能。
4. `evaluation_seeds`（開発用、既定3）、`holdout_seeds`（最終評価、既定2）、`max_repair_attempts`（既定2）を確認。
5. E2Bで静的Greedy・厳密DP・Qwenコードを開発用seedで実行。機能NO-GOならエラーログで修正、品質HOLDなら**代理効用と改善閾値の差**で改善。各改訂は新Sandboxで実行。
6. 開発用データで最良の**制約充足**候補を選択。**全候補NO-GOなら選択せず、HOLDOUTを省略**。有効候補がある場合だけ別seedで最終評価を1回実行して判定。
7. **科目別学習計画の比較例**、DEVと（実施した場合だけ）HOLDOUTのseed別スコア、改訂履歴・コード差分・NO-GOログ・架空の事業試算を確認し、MarkdownまたはJSONを出力。

### レポート上の解釈に関する重要な注意

- **NO-GO**：実行エラー・形式違反・時間制約違反など、機能上の失敗。
- **HOLD**：機能的には動くが、設定した代理効用の品質閾値に未達。
- **CONDITIONAL GO**：代理目的関数と合成データでは条件を満たす。**市場受容、実際の教育効果、事業化の判断を意味しない**。
- **厳密DP**は、この実験用に定義した離散・分離可能な代理目的関数についてだけ最適です。
- **Qwen生成コード**の品質は毎回変わり得ます。改善ループで必ずCONDITIONAL GOになる保証はありません。
- 実行時間はE2B内コマンド時間の単発測定で、LLM推論・起動待ち・実際のE2B課金額を含みません。
- 合成データのDEV/HOLDOUT分割は過適合リスクを下げるための仕組みであり、現実の顧客データでの汎化性能を保証しません。

## 保存する証跡

```text
artifacts/<run-id>/
├── project.json
├── requirements.json
├── service_design.json
├── customer_evidence.json
├── requirement_assessment.json
├── requirement_change_log.json
├── proposal_*.json              # 外側ループの改訂提案を生成した場合
├── datasets.json               # DEV / HOLDOUT分割
├── baseline.py
├── optimal.py
├── generated.py                # Functional PASSがある場合のみ出力
├── attempts/
│   ├── attempt_00.py
│   ├── attempt_00.json
│   ├── attempt_01.py
│   ├── attempt_01.json
│   └── attempt_01.diff
├── run.json                    # DEV/HOLDOUT評価・実行証跡・計画例
└── report.md                  # NO-GOログ・HOLD履歴・審査結果
```

APIキーは保存しません。実際に試した改訂回数によって`attempt_XX`の数は変わります。

### 自動テスト

```bash
cd backend
python -m pip install -r requirements.txt pytest
PYTHONPATH=. python -m pytest -q
```

本配布版は**バックエンドのモック付き自動テスト（選択ロジック、部分修正、HOLDOUT非実行を含む）**を実施しています。実Mac StudioのMetal推論、E2B実接続およびフロントエンドの完全ビルドは、この環境では検証できませんでした。

詳細仕様： [Architecture](docs/architecture.md) · [I/O Contract](docs/io-contract.md) · [CHANGELOG](CHANGELOG.md)

### v0.6 JSON応答の重要フィールド

- `selected_attempt_index: null` / `generated: null`: **有効な生成候補なし**。最終採用コードは存在しません。
- `holdout_executed: false`: 最終評価のSandboxは一切呼び出していません。`baseline` / `optimal`も最終評価についてはnull、`development_*`のみ取得済みです。
- `plan_comparisons_source: "development"`: 表示中の学習計画はDEVデータです。最終評価データではありません。
- `repair_attempts[].error_summary`, `code_diff`, `repair_strategy`: 検証器の種類別件数、前回との差分と修正段階です。診断は推定のため誤検出があり得ます。

**キーを公開しないこと**：`.env` をGit管理に追加しないでください。Docker Composeのホスト公開ポートは既定18000番、UIは5173番です。`API_PORT`と`WEB_PORT`で変更できます。

### 新規フィールドとエンドポイント

- `POST /api/design` `{project, requirements}` → `ServiceDesign`
- `POST /api/generate` に `service_design`（省略可／旧API互換）を追加
- `POST /api/run` に `service_design`, `customer_evidence`, `requirements_revision`, `parent_run_id` を追加
- `POST /api/refine` `{run_id, evidence}` → `RequirementRefinementProposal`（提案のみ、旧要件は変更しない）
- `RunResponse.requirement_assessment`：Implementation Validity と Requirement Validity の別判定。
- `RunResponse.requirements_sha256`, `service_design_sha256`, `parent_run_id`：追跡用。

**検証済み範囲：** バックエンドのモック付き単体・APIテストを実行。E2Bクラウド実行、Mac MetalのQwen推論、React依存導入後のフロントエンド完全ビルドはこの実行環境では検証していません。
