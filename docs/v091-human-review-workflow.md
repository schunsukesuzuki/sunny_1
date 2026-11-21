# v0.9.1 — ODA診断HOLD時の手動審査経路

## 起こった事象
R0実装は独立E2BテストでPASSしたが、ODA-Fin-RL-8Bが `r0_implementation_assessment=incorrect` と誤認し、`SIM-SLA-001` を引用しなかった。結果として `DOMAIN_REVIEW_HOLD` に至り、Step 05→06が実行不能になった。これはODAの実測された診断品質上の失敗であり、再試行でPASSになる保証はない。

## 追加機能
Step 05に「人間のHOLD審査を記録してR1検証へ進む」を追加。独立R0 PASS、模擬反例、ODA診断をレビューし、担当者名・理由・HOLD理由を改変せずに保存。独立評価器・R1契約は不変。R1生成には不正確なODA結論を「承認済み」として渡さず、独立R0 PASSと人間が確認した反証内容をコンテキストとして渡す。

- 通常承認: ODA診断ルーブリックがPASSした場合だけ。
- HOLDからの承認: 人間による明示的な認識・説明、R0独立PASS、`SIM-SLA-001` の合成証拠、固定R1契約を条件とする。
- 証拠がない対照群、R0独立評価がFAIL、未記録のODA診断ではHOLDを解除できない。
- `finance_diagnosis_pass` はHOLDのまま。`human_adjudicated_r1_kpi_improvement_demonstrated` を別指標で表示し、自動診断成功と混同しない。
- ファイル `artifacts/approvals/*/approval.json` と `artifacts/experiments/*/report.md` に承認経路、差分根拠を記録。

## 既存のv0.9で作られた提案の扱い
ZIPを同じ開発ディレクトリに展開し、以前の `artifacts/` を引き継いだ場合、Step 07で提案の履歴を選択し結果を見る操作からHOLD提案を再表示できる。Step 05でHOLD時の人間レビューを明示して続行。元の提案IDとログが保持される。

## 注意点
- 実顧客との合意、EUの法令遵守、実保険業務の品質は未検証。
- 人間の審査はモデルを訂正したという証拠であり、ODAが正しく推論できたという証拠ではない。
- HOLDのまま継続する経路はデモ実験専用である。運用環境の審査許可に流用しない。
