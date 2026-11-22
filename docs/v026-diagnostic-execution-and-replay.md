# v0.26 — 診断モデルの実行失敗と品質HOLDの分離・限定再実行

## 背景 / 実証されたv0.25の事象

実際の `claims_full_run_v025` 証跡では、05 DogwoodはALLOW、06 R1評価は完了、08のODA-Fin-RL-8Bの固定ケース1件が240秒でタイムアウトしました。他のRAW回答も採点不合格のため、診断品質は `HOLD_HUMAN_ADJUDICATION` です。v0.25では08をFAILEDと記録したうえで、一般的な06失敗時の警告が画面に表示されました。したがって「技術実験の実行成否」と「要件診断の信頼性」を分離して見せる必要があります。

## 変更点

- 08の各モデル呼び出しは `COMPLETED` / `INCOMPLETE_TIMEOUT`（HTTP 504） / `INCOMPLETE_TRANSPORT`（503） / `INCOMPLETE_MODEL_RESPONSE`（502） / `FAILED_EXECUTION`（その他）を区別します。**タイムアウトは誤診断の点数に含みません**。ただし実行完了もPASSとは数えません。
- ベンチマーク全体の `status` は全試行完了時 `COMPLETED`、タイムアウトが残る場合 `INCOMPLETE_TIMEOUT` です。古い一般的エラーは従来互換の `COMPLETED_WITH_ERRORS` を維持します。
- `reliability_gate` は `execution_status`（COMPLETE/INCOMPLETE_TIMEOUT/INCOMPLETE_EXECUTION）、`quality_status` と別々の `execution_failure_codes` / `quality_failure_codes` を報告します。総合ゲートの `HOLD_HUMAN_ADJUDICATION` は自律改訂不許可を意味し、R1の動作結果の破棄を意味しません。
- `diagnostic_consistency.py` は **モデル回答と公開入力のみ**から `classification`、`implementation_assessment`、`synthetic_requirement_fit`、`change_required`、`scheduling_precedence`、根拠IDの相互整合を確認します。フィクスチャの正解ラベルは使わず、モデル出力を改変しません。これは型付きの決定的チェックであり、自然言語の意味が真であることの証明ではありません。元の独立ルーブリックの点数は変更しません。
- `ODA_FIN_TIMEOUT_SECONDS=480`（既定）を追加。`OLLAMA_TIMEOUT_SECONDS=240` はQwen等の既定値のまま。実行時間が増える可能性があります。無制限のリトライは行いません。
- 08完了待ちの09は `SKIPPED` と明記します。08再実行成功時に09がベンチマーク未完了のため失敗・保留されていた場合に限り、元の公開根拠・通知/割当種別の検証を維持して**09の決定的評価だけ**再実行します。05承認・Dogwood・06 R1・08f最適性評価は再実行しません。

## API

### 08のみ（独立したベンチマーク）

`POST /api/diagnostic-benchmark/retry-incomplete`

```json
{"benchmark_id": "<保存済みbenchmark UUID>", "include_fixed": true, "include_blind": true}
```

### 00〜09の一括ワークフローで再開する場合

`POST /api/full-run/<workflow UUID>/retry-diagnostic-timeouts`（JSON本文不要）

ワークフローの状態が `PARTIAL` かつ `phase=DONE` であることを要求します。08の未完了試行を実行し、成功したら09を必要時のみ復旧して、現時点のZIPを再作成します。ブラウザ画面10にもボタンを追加しました。元の監査ZIPは `artifacts/exports/<export UUID>/before_diagnostic_retry_*.zip` に退避します。

**前提**: 同じMac上の元 `./artifacts/` を保持してください。ZIPだけを新フォルダへ展開しても、保存済み `artifacts/` が自動復元されるわけではありません。バックアップしてからアップグレードしてください。v0.25のFull Run ZIPから復元する場合は、展開先を別途慎重に確認してください。

## 再実行の制約と監査

1. 再実行はユーザーの明示操作によってのみ実行されます。既に `COMPLETED` のモデル呼び出しや品質不合格のモデル回答を上書きしません。
2. 固定ケースはフィクスチャバージョンとSHA-256を再検証し、Blindケースは保存済み `blind_cases.json` の入力とSHA-256を再利用します。モデル名が変更されている場合は409で拒否します。正解ラベル/ルーブリックの失敗内容を再試行プロンプトへ渡しません。
3. 各対象は最大2回までの明示的な再試行に制限します。同時実行時は排他ロックを取得し、元の`benchmark.json`を `retry_before_*.json` に退避します。`retry_*.json` に実行証跡を保存し、最新集計は原子的に更新します。
4. **Fresh Blindでタイムアウトしたケースを同じ入力で再実行した場合は `replayed_after_incomplete=true` にします。これは新規の独立・初回評価ではないため、`BLIND_REPLAY_NOT_FRESH` を品質HOLD理由に追加します。** 本当に新しいBlindの初回一般化を測るには、新しいベンチマークを実行します。
5. 09がベンチマーク未完了で失敗した場合だけ、検証済みの06成果物から決定的な事業評価を再生成します。以前の失敗/保留記録は残します。顧客価値・ROI・法令適合・本番導入は引き続き未検証/NO-GOです。
6. 実装上、ファイル操作はローカル開発用であり、複数ホストをまたぐ分散ロック、権限分離、改ざん耐性のある第三者証明ではありません。

## 動作確認

```bash
cp -n .env.example .env # .envがなければのみ作成。既存.envを上書きしない
# v0.25の ./artifacts/ を維持した状態で
docker compose build --no-cache api web
docker compose up -d --force-recreate
```

画面10で保存済みWorkflow IDを読み込むと、08が未完了のPARTIALだけに再実行ボタンが表示されます。画面08では個別ベンチマークの再試行が可能です。モデルを本当に起動する場合はOllamaが必要です。

開発環境で `pytest` は**138件PASS**。v0.25のアップロード済み監査ZIPを再構成したローカル模擬試行では、08を1件再評価後、Workflow=COMPLETE・execution=COMPLETE・quality=HOLDを確認しました。**実際のOllama再推論/モデル品質改善、Rust/CargoおよびDockerの実ビルド、Viteの完全ビルドはこのパッケージ作成環境では未検証です**。TypeScript/TSXの構文解析のみ実施しました。
