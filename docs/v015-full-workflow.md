# v0.15 — 01–09 Full Workflow + Single ZIP Export

## Scope

手順10は、以前の「承認済みR1実験を起点とする追加検証」ではなく、**手順01から09までを最初から連続実行・保存**するボタンです。手順07は新しい解析ではなく、証跡インデックスの自動保存と履歴参照です。v0.14の旧 `POST /api/pipeline/run-and-save` はAPI互換性のため残していますが、手順10のUIからは呼びません。

| Step | Batch action | Saved evidence |
|---|---|---|
| 01 | 現在の顧客ブリーフ、seed、模擬反例条件、診断ケース・繰り返しを確定 | `workflows/<id>/01_input.json` |
| 02 | Qwenでサービス設計ドラフト生成 | `workflows/<id>/02_service_design.json` |
| 03 | R0 FIFOと期限優先参照をE2Bで実行・独立評価 | `runs/<id>` にソース・seed・E2B出力 |
| 04 | QwenとODAで同一DEV/模擬証拠を独立診断 | `proposals/<id>` の生診断・採点 |
| **05** | **一時停止。人間が事実・根拠・HOLD原因を確認して承認/却下** | `approvals/<id>` に人間の明示的判断 |
| 06 | 承認時のみR1コード生成・DEV修正・単回HOLDOUT | `experiments/<id>` に全試行・差分・ログ |
| 07 | 履歴・監査証跡の参照インデックス作成 | `workflows/<id>/07_history_snapshot.json` |
| 08 | 診断品質の合成ベンチマーク（Qwen/ODA） | `benchmarks/<id>` に全診断・採点 |
| 08b | R1の事後行動プローブと4つの合成ストレスシナリオ | `policy_validations/<id>` |
| 09 | 固定ルーブリックで事業価値/デリバリー評価 | `assessments/<id>` にJSONとMarkdown |

## 操作

1. MacのOllama・E2Bを用意し、画面01のブリーフとseed、04の模擬反例条件、08のケース・回数を設定。
2. 10の **「01〜09 一括実行を開始（05で一時停止）」** を押す。バックエンドは01〜04を自動実行し、`AWAITING_APPROVAL`で停止する。
3. 10に表示される診断結果/証跡をレビューする。通常の承認には明示チェックが必要。ODAがHOLDなら、R0独立評価PASSの確認・例外理由・確認チェックを追加で要求する。**モデルのHOLDはPASSに変更しない。** 顧客証拠のない対照条件では承認できない。
4. **「05を承認して06〜09を自動実行・ZIP保存」** を押すと残りを実行。却下すれば停止し、その時点までのZIPを残す。
5. 最終ZIPは10のリンクからダウンロード。`GET /api/full-run/<workflow_id>`または07「01〜09一括実行の履歴」で再表示できる。

## 完全性判定

- `COMPLETE`は**すべての要求工程が実行され、その関連成果物がZIPに含まれた**ことを示す。技術・モデル・事業のPASSではない。
- `PARTIAL`は例外/却下/中断/欠落/サイズ制限を含み、`manifest.json`の`missing`, `skipped`, `pending_or_failed_steps`, `stages`に記録する。
- 人間の承認待ち中も`PARTIAL` ZIPを取得できる。承認後は同じWorkflow IDの最終ZIPに更新する。承認記録は保存時の原文を保持する。
- ルーブリックHOLDはモデル品質に関する所見であり、別途人間レビューが記録され、実行が完了していればZIP自体は`COMPLETE`になり得る。
- 保存した各ファイルのSHA256は**そのファイルの生バイト**のハッシュ。署名/第三者による証明ではない。
- 実験失敗は隠さず保存し、新しい別のHOLDOUTデータからモデルを修復しない。R1の意味的振る舞いは事後行動プローブで別途評価する。
- 承認者のデモ名などは**監査証跡には含まれる**。外部共有前にはZIPを確認すること。事業評価レポートのプロンプトやルーブリックには特定の面接官の氏名・所属は含めない。
- バックグラウンド実行は稼働中のFastAPIプロセス内で行う。サーバー再起動による中断からの自動再開やジョブキューの耐久性は未実装。保存済みの証跡とWorkflow IDは残る。実運用にする場合はジョブキュー、再試行/冪等性、認証、長時間プロセス管理が必要。

## API

```text
POST /api/full-run/start
    {"brief":"...","seed":42,"evidence_condition":"counterexample",
     "case_ids":["fifo_sla_conflict","actual_fifo_implementation_bug"],"repetitions":1}
GET  /api/full-run/<workflow_id>
POST /api/full-run/approve-and-continue
    {"workflow_id":"<uuid>","approval":{
       "proposal_id":"<proposal_uuid>","decision":"approved",
       "actor":"Human reviewer (demo)","rationale":"Synthetic demo approval only",
       "domain_review_override":false}}
GET  /api/full-run/<workflow_id>/bundle
GET  /api/history/workflows
```

## Security and limitations

実データ・実顧客の承認・市場受容・EU規制適合を評価するものではありません。未承認のプログラムはE2Bで隔離実行されますが、任意のアクセス権限を渡したときの漏洩やコストをゼロにはしません。無認証のローカル開発用APIです。公開ネットワークに露出しないでください。
