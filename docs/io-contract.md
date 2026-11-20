# v0.6 API / I/O Contract

## Endpoints

- `GET /api/health` → API/モデル/E2Bキーの設定状態
- `GET /api/sample` → 架空の教育SaaS案件
- `POST /api/analyze` `{"project": ProjectInput}` → `RequirementsDraft`
- `POST /api/design` `{"project": ProjectInput, "requirements": RequirementsDraft}` → `ServiceDesign`（未承認の中間設計）
- `POST /api/generate` `{"project": ProjectInput, "requirements": RequirementsDraft, "service_design": ServiceDesign}` → `GeneratedCode`（service_design省略時は旧API互換）
- `POST /api/run` `{"project": ProjectInput, "requirements": RequirementsDraft, "service_design": ServiceDesign, "customer_evidence": CustomerEvidence[], "requirements_revision": 0, "parent_run_id": null, "code": "<Python>"}` → `RunResponse`
- `POST /api/refine` `{"run_id": "<UUID>", "evidence": CustomerEvidence[]}` → `RequirementRefinementProposal`（旧要件はそのまま）
- `GET /api/reports/{run_id}/report.md` → 保存されたMarkdownレポート

## ProjectInput example

```json
{
  "title": "教育SaaS：AI個別学習プランニング（架空案件）",
  "brief": "既存の教育LMSの学習計画作成を自動化し、新しい有料サービスとして提供したいという架空の顧客相談文です。",
  "seed": 42,
  "evaluation_seeds": 3,
  "holdout_seeds": 2,
  "students_count": 12,
  "min_quality_ratio": 0.98,
  "min_improvement_ratio": 1.01,
  "max_repair_attempts": 2,
  "business": {
    "monthly_price_yen": 12000,
    "paying_schools": 30,
    "monthly_operating_cost_yen": 180000,
    "hours_saved_per_school": 5,
    "teacher_hourly_cost_yen": 2500
  }
}
```

- `evaluation_seeds`：修正・選択のDEV用。`seed`から連続生成。
- `holdout_seeds`：DEVとは異なるseed（`seed+10000*(1+requirements_revision)`から連続）。**生成時はQwenに非公開**、採用済み候補を最終評価するときだけ使用。
- `max_repair_attempts`：0〜3（最初の試行を除く、NO-GOとHOLDの**共通**改訂回数）。

## E2B sandbox file contract

**Input** `/home/user/input.json` : 

```json
{
  "schema_version": "1.0",
  "project_type": "weekly_study_plan",
  "students": [
    {"student_id":"S001","available_hours":8,"subjects":[
      {"name":"数学","gap":0.7,"priority":5,"max_hours":5},
      {"name":"英語","gap":0.4,"priority":3,"max_hours":5}
    ]}
  ]
}
```

**Program** `/home/user/solver.py` : Python3.11+ stdlib-only。E2B内で実行。

**Output** `/home/user/output.json` :

```json
{"plans":[{"student_id":"S001","allocations":[
  {"subject":"数学","hours":5},{"subject":"英語","hours":3}
]}]}
```

毎回実行前に`output.json`を削除して前seedの結果を使わないようにします。

## Constraint checks / proxy utility

- 生徒・科目に重複も欠落もないこと。
- 整数・非負・科目上限以下、総時間一致を全生徒で満たすこと。
- 1 seedでも失敗した場合は候補の平均代理効用をN/Aとして扱います。
- `mean_students[Σ gap×priority×(1-exp(-hours/2.5))/Σ(gap×priority)]` は**合成的な代理効用**であり、学習成果や市場価値ではありません。
- DPは**この問題だけ**の厳密最適解。

## Revision and selection

- NO-GO：初回修正にはDEV独立評価器の構造化エラー分類・代表例・入出力契約を返す。2回目以降は状態不変条件とASTヒントを追加し、`allocate_hours`関数のみを構造的に差し替える。無効パッチは拒否してログへ保存。
- HOLD：DEVでの候補・Greedy・DPの**平均スコアと改善閾値**をQwenへ返す。DPのコード・個人別の最適配分・HOLDOUTの指標は返さない。
- リトライ上限に達するかDEV条件を満たしたら、**DEVで機能合格の最高スコア試行だけ**を選択（同点は初期試行）。**全試行NO-GOなら選択なし**、`selected_attempt_index: null`となり、`generated.py`を保存しない。
- HOLDOUTは有効な候補が選ばれたとき**一度だけ**実行。全試行NO-GOならHOLDOUTのE2Bを呼び出さない。最終結果は改訂ループに利用しない。

## RunResponse important fields

- `seeds`: DEV seed番号。
- `holdout_seeds`: 最終評価用seed番号。
- `development_baseline`, `development_optimal`, `development_generated`: DEVでの参照スコア、及び選択候補（なければ最後の失敗試行の診断）。
- `baseline`, `optimal`, `generated`: HOLDOUT実行後の最終指標。未実行の場合は全て`null`。
- `repair_attempts[]`: `attempt_index`, `verdict` (NO-GO/HOLD/CONDITIONAL GO), `trigger`, `selected`, `candidate`、`feedback`, `repair_error`, `repair_strategy`, `error_summary`, `code_diff`。
- `selected_attempt_index`: DEVで選択された改訂番号。全NO-GOなら`null`（不合格の最終試行は選択しない）。
- `holdout_executed`: 最終E2B評価を行った場合のみ`true`。
- `plan_comparisons_source`: `holdout`または`development`。全NO-GOならDEVの参考比較だけを表示。
- `plan_comparisons[]`: 3方式の科目別時間配分（不正なQwen候補の配分は`null`、値を捏造しない）。
- `functional_gate`, `selection_gate`, `business_gate`: 別々の判断ゲート。
- `report_markdown`: 全過程と判断根拠を記録したMarkdown。

## Artifacts

`artifacts/<run_id>/report.md`, `run.json`, `requirements.json`, `datasets.json` (DEV + 実施した場合はHOLDOUT), `baseline.py`, `optimal.py`, `generated.py`（有効候補がある場合のみ）、`attempts/attempt_XX.py`, `attempts/attempt_XX.json`, `attempts/attempt_XX.diff`（改訂に差分がある場合）。

E2BのSandbox ID、実行結果/コード/データのハッシュを保持します。APIキーは保存しません。

## v0.6 : provenance-aware requirements

`CustomerEvidence`には`evidence_id` / `requirement_id` (`AC-01`) / `provenance` / `verdict` / `observation` / `source_reference` / `human_verified` / `reviewer`を記録。

`RequirementAssessment`は`implementation_validity` (`PASS`, `FAIL`) と `requirement_validity` (`UNVERIFIED`, `SUPPORTED_PRELIMINARY`, `REJECTED_PRELIMINARY`, `CONFLICTED`) を別々に返す。実顧客由来（自己申告）かつ出典記載、人間確認済みの証拠だけを要件妥当性の暫定判定へ採用する。偽造・錯誤・因果推論の妥当性は判定できないため、`decision=HUMAN_REVIEW_REQUIRED`を維持する。

改訂を含む実行では`requirements_revision`と`parent_run_id`をセットで使用。前回revisionが0なら次回は1。以前の要件を上書きせず、新しいrun IDに保存する。

**限界：** 2026年11月時点のサンプル評価器は教育SaaS専用。`docs/eu-insurtech-concept.md`の海外保険顧客仮説はE2Bでの検証対象ではない。
