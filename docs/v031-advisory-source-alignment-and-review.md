# v0.31 — 最新評価に紐づくAI技術提案・要件契約・版差分

## 目的

画面10Rの冒頭のAI提案を、単なる一般的なブレインストーミングではなく、**現在の00〜09の評価結果に紐づく未承認の意思決定支援ドラフト**として扱う。

表示順は **10 → 10R（AI提案 → 各工程の分析）→ 00 → 01〜09**。

## 変更点

1. **最新スナップショットとSTALENESS**：`current_advisory_source` は、Workflowの業務状態、最新 `benchmarks/<id>/benchmark.json`、09評価、00b/00c、08e/08f、08最新索引、読取専用レポートの内容からSHA-256を計算する。提案保存時に `source_snapshot` と `source_hash` を版付きで記録する。単なるZIPの再梱包は更新扱いにしない。背景モデル生成中に08の再試行などで元成果物が変わった場合も、保存版を `STALE_ADVISORY` として保持する。
2. **根拠・要件の接続**：人間選択済み公開資料の `PUB-*` と、`08e_requirement_trace.json` の要件ID・要求機能・受入テストIDを、要約したコンテキストの allowlist に含める。架空の根拠IDは拒否する。公開資料は業界の問題背景であり、**架空顧客の意思決定・要件承認・因果関係を立証しない**。
3. **技術選択肢の比較**：`low_complexity`、`balanced`、`research_option` の3案を必須にし、要件ID、直接対応の範囲、必要役割、相対工数、提供リスク、費用を左右する要因、トレードオフ、検証計画を出す。`claim_progress_updates` なら低複雑性案と標準案は、通知機能を直接実装する必要がある。割当KPIだけでは通知受入を代替できない。
4. **再実験**：診断HOLD、DEV候補識別不足、通知統合未実施、PARTIAL状態を決定的な `required_attention` として表示。LLMは出典ID、成功指標、担当者を伴う `next_experiments` を生成する。表示される必須の確認事項そのものはLLMが書き換えない。
5. **日本語と価格の扱い**：主要な提案本文が日本語でない場合や、予算未入力なのに金額を断定した場合、生成を失敗扱いにする。既存の評価レポートは表示を継続する。指定済みの金額についても、推定見積の正確さは保証されない。
6. **前版との差分**：前提条件と主要出力の構造差分、評価スナップショット変更の有無を `revision_diff` で記録・表示。改善やROIを自動採点しない。

## 状態遷移

- `RUNNING`：モデルが提案だけを非同期生成中。10Rの既存評価は表示可能。
- `DRAFT_UNAPPROVED` + `CURRENT_SOURCE`：現在の保存済み評価に対応する未承認ドラフト。PMレビューは別記録。
- `STALE_ADVISORY`：モデルが参照した元成果物と現在の正本が一致しない。旧版の閲覧は可能だがレビューはHTTP 409で拒否。**「提案を再生成」ボタンを明示的に押す**と、最新状態から新しい版を生成する。LLM費用を無制限に増やさないよう、08再試行後の自動再生成は行わない。
- `GENERATION_FAILED`：構造化出力、要件ID、根拠ID、言語、またはモデル応答の失敗。下段の評価レポートとワークフロー状態は保持する。

## API（変更なし）

- `GET /api/full-run/{id}/advisory`：最新の正本と比較し、`freshness_status`、`source_snapshot`、`revision_diff`、`required_attention` を返す。
- `POST /api/full-run/{id}/advisory`：`constraints` と `regenerate`。現版がSTALEなら `regenerate:false` でも新しい版を発行できる。`regenerate:true` は明示的に新しい版を生成する。
- `POST /api/full-run/{id}/advisory/review`：現版・最新ソース一致に限り、PM/技術者の記録を保存。自律的な業務実行、CI/CD、自動的な本番承認はしない。

## 安全・検証上の境界

- 条件と根拠の**構造的な整合性**を検査しているのであり、自然言語の意味や顧客ニーズを証明しない。
- Public source IDの存在確認と参照整合性は、その公開資料が顧客の真因や法令を証明したことを意味しない。
- Source hashはローカルファイルの整合性比較であり、暗号署名・本人認証・外部データの真正性を保証しない。
- 提案の差分は文字列・構造差分であり、良くなったかどうかの評価ではない。
- Qwenの提案は実機未検証。型付きJSONが成立しない場合は`GENERATION_FAILED`として証跡を残し、評価結果を改変しない。
- Rust/Dogwood認可、DEV/HOLDOUT、08f CP-SAT、09事業評価のロジックは変更しない。

## 実行・検査

```sh
cd backend && python -m pytest -q
cd ../frontend && npm ci && npm run verify:layout && npm run build
# プロジェクトルートへ戻り：
docker compose build --no-cache api web
docker compose up -d --force-recreate
```

今回の作成環境ではPython回帰テスト175件、グローバルTypeScriptによるTSX解析と表示順検査、および旧v0.30実行証跡の再読込を確認。Vite完全ビルド、Rust/Docker、実際のOllama/E2Bは未実行。
