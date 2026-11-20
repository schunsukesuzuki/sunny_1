"""Audit-friendly report: development revisions vs one-time held-out decision."""
from __future__ import annotations

from .models import (BusinessScenario, CandidateResult, PlanComparison, ProjectInput,
                     RepairAttempt, RequirementsDraft)


def bullets(values: list[str]) -> str:
    return "\n".join(f"- {x}" for x in values) or "- （未記載）"


def metric(n: float | None, decimals: int = 5) -> str:
    return "N/A" if n is None else f"{n:.{decimals}f}"


def comparison_table(b: CandidateResult, o: CandidateResult, g: CandidateResult) -> str:
    rows = [
        ("全seed制約充足", lambda c: "PASS" if c.hard_constraint_pass else "FAIL"),
        ("成功seed数", lambda c: f"{c.passed_seeds}/{c.total_seeds}"),
        ("平均代理効用", lambda c: metric(c.score)),
        ("代理効用標準偏差", lambda c: metric(c.score_std)),
        ("最悪seed代理効用", lambda c: metric(c.min_score)),
        ("平均コマンド実行時間 (秒)", lambda c: f"{c.elapsed_seconds:.3f}"),
        ("ソースSHA256（先頭16文字）", lambda c: f"`{c.source_sha256[:16]}…`"),
    ]
    return "\n".join(f"| {label} | {getter(b)} | {getter(o)} | {getter(g)} |"
                     for label, getter in rows)


def per_seed_table(b: CandidateResult, o: CandidateResult, g: CandidateResult) -> str:
    return "\n".join(
        f"| {bb.seed} | {metric(bb.score)} | {metric(oo.score)} | {metric(gg.score)} | "
        f"{' / '.join('PASS' if x.hard_constraint_pass else 'FAIL' for x in (bb, oo, gg))} |"
        for bb, oo, gg in zip(b.per_seed, o.per_seed, g.per_seed)
    )


def evidence_rows(candidates: list[CandidateResult]) -> str:
    return "\n".join(
        f"| {c.name} | {s.seed} | `{s.sandbox_id}` | `{(s.output_sha256 or 'N/A')[:16]}` | {s.status} |"
        for c in candidates for s in c.per_seed
    )


def attempts_section(attempts: list[RepairAttempt]) -> str:
    rows = []
    details = []
    for a in attempts:
        c = a.candidate
        rows.append(f"| {a.attempt_index} | {a.verdict} | {a.repair_strategy} | "
                    f"{c.passed_seeds}/{c.total_seeds} | {metric(c.score)} | "
                    f"{'✓' if a.selected else ''} | `{a.source_sha256[:16]}…` |")
        if a.error_summary:
            details.append(f"**Attempt {a.attempt_index} エラー分類（検証器より）**: "
                           + ", ".join(f"`{k}`={v}" for k, v in a.error_summary.items()))
        if a.code_diff:
            details.append(f"**Attempt {a.attempt_index} 前試行からの差分**"
                           "\n\n```diff\n" + a.code_diff + "\n```")
        if a.verdict == "NO-GO":
            chunks = []
            for s in c.per_seed:
                if s.hard_constraint_pass:
                    continue
                chunks.append(
                    f"seed={s.seed}, sandbox={s.sandbox_id}, status={s.status}\n"
                    f"output_sha256={s.output_sha256 or 'N/A'}\n"
                    "[validator violations]\n" + ("\n".join(s.violations) or "(empty)") +
                    "\n[stderr]\n" + (s.stderr or "(empty)") +
                    "\n[stdout]\n" + (s.stdout or "(empty)")
                )
            details.append(f"### Attempt {a.attempt_index} — NO-GO\n\n"
                           + "\n\n".join("```text\n" + chunk + "\n```" for chunk in chunks))
        if a.verdict == "HOLD":
            details.append(f"### Attempt {a.attempt_index} — 品質HOLD\n\n"
                           f"開発用平均代理効用: **{metric(c.score)}**。実行は成功したが品質閾値に未達。")
        if a.feedback:
            details.append("**次のQwen修正に渡した情報（開発用のみ）：**\n\n```text\n"
                           + a.feedback + "\n```")
        if a.repair_error:
            details.append("**Qwenの再生成エラー：**\n\n```text\n" + a.repair_error + "\n```")
    return (
        "| 試行 | 開発判定 | 修正方法 | 合格seed | DEV代理効用 | 採用 | ソースSHA256 |\n"
        "|---|---|---|---:|---:|---:|---|\n"
        + "\n".join(rows) + "\n\n"
        + "\n\n".join(details or ["- 再生成用エラー／品質フィードバックなし"])
    )


def example_plan_table(plans: list[PlanComparison]) -> str:
    if not plans:
        return "- 比較可能な計画例を取得できませんでした。"
    sections = []
    for row in plans:
        t = [f"### seed {row.seed} / {row.student_id} / 利用可能 {row.available_hours} 時間",
             "", "| 科目 | 理解ギャップ | 優先度 | 上限h | 静的Greedy | 厳密DP | Qwen候補 |",
             "|---|---:|---:|---:|---:|---:|---:|"]
        for s in row.subjects:
            def hours(x):
                return "N/A" if x is None else str(x)
            t.append(f"| {s.subject} | {s.gap:.2f} | {s.priority} | {s.max_hours} | "
                     f"{hours(s.baseline_hours)} | {hours(s.optimal_hours)} | {hours(s.generated_hours)} |")
        if not row.generated_valid:
            t.append("\n> Qwen候補はこの例の出力を有効に取得できなかったため、N/Aと表示します。")
        sections.append("\n".join(t))
    return "\n\n".join(sections)


def generate_report(*, run_id: str, created_at: str, project: ProjectInput,
                    req: RequirementsDraft, model: str,
                    dev_datasets: dict[int, dict], holdout_datasets: dict[int, dict],
                    dataset_hashes: dict[str, str],
                    dev_baseline: CandidateResult, dev_optimal: CandidateResult,
                    dev_generated: CandidateResult,
                    baseline: CandidateResult | None, optimal: CandidateResult | None,
                    generated: CandidateResult | None,
                    functional_gate: str, selection_gate: str, gate_reasons: list[str],
                    scenario: BusinessScenario, repair_attempts: list[RepairAttempt],
                    selected_attempt_index: int | None, holdout_executed: bool,
                    plan_comparisons_source: str, plan_comparisons: list[PlanComparison]) -> str:
    b = project.business
    dev_seeds = list(dev_datasets)
    holdout_seeds = list(holdout_datasets)
    errors = []
    for c in (baseline, optimal, generated):
        if c is None:
            continue
        for e in c.per_seed:
            if not e.hard_constraint_pass:
                errors.append(f"### {c.name}, seed {e.seed} — FINAL HOLDOUT NO-GO\n\n"
                              + "```text\n" +
                              f"sandbox={e.sandbox_id} status={e.status}\n"
                              "[validator]\n" + "\n".join(e.violations) + "\n"
                              "[stderr]\n" + (e.stderr or "(empty)") + "\n"
                              "[stdout]\n" + (e.stdout or "(empty)") + "\n```")
    errors_section = "\n\n".join(errors) if errors else "- 最終評価の制約違反なし。"
    hashes = "\n".join(f"- **{'DEV' if seed in dev_datasets else 'HOLDOUT'}** seed {seed}: "
                       f"`{dataset_hashes[str(seed)]}`"
                       for seed in [*dev_seeds, *holdout_seeds])
    selected_label = (f"**{selected_attempt_index}**（DEVで機能合格した候補から選択）"
                      if selected_attempt_index is not None else "**なし**（全DEV試行がNO-GO）")
    if holdout_executed:
        assert baseline is not None and optimal is not None and generated is not None
        holdout_section = f"""## 4. 最終評価（未使用seedによる一度限りの審査）

| 指標 | A: Greedy | B: 厳密DP | C: Qwen候補 |
|---|---:|---:|---:|
{comparison_table(baseline, optimal, generated)}

| HOLDOUT seed | A | B | C | 制約 A/B/C |
|---|---:|---:|---:|---|
{per_seed_table(baseline, optimal, generated)}

- C / B：**{metric(generated.relative_to_optimal)}**。
- C / A：**{metric(generated.relative_to_baseline)}**。
- CとAの配分一致seed：**{generated.same_plans_as_baseline if generated.same_plans_as_baseline is not None else '比較不能'} / {len(holdout_seeds)}**。
- CとBの配分一致seed：**{generated.same_plans_as_optimal if generated.same_plans_as_optimal is not None else '比較不能'} / {len(holdout_seeds)}**。

### 最終の独立審査

- **Functional Gate：{functional_gate}**
- **Technology Selection Gate：{selection_gate}**
{bullets(gate_reasons)}

最終NO-GO／実行エラーログ（保持）：

{errors_section}

### E2B最終実行証跡

| 方式 | seed | Sandbox ID | 出力SHA256先頭 | コマンド状態 |
|---|---:|---|---|---|
{evidence_rows([baseline,optimal,generated])}

## 5. 顧客向け学習計画の比較例（HOLDOUTデータ）

{example_plan_table(plan_comparisons)}

> 合成生徒の具体例。学習効果の立証ではありません。
"""
    else:
        holdout_section = f"""## 4. 最終評価：実施せず（NO VALID CANDIDATE）

**HOLDOUT未実行**。すべての開発試行が機能的NO-GOだったため、生成コードを採用せず、最終Sandboxを呼び出していません。未使用データでの成績を推測・捏造しません。

- Functional Gate：**{functional_gate}**
- Technology Selection Gate：**{selection_gate}**
{bullets(gate_reasons)}

## 5. 学習計画の比較例（DEVデータのみ）

{example_plan_table(plan_comparisons)}

> 上記は**開発用データ**であり、未使用データでの評価ではありません。Qwen候補は機能不合格のためN/Aです。
"""
    return f"""# AI Venture Feasibility Studio v0.6 — 新規事業の技術選定レポート

> **架空案件／合成データによる検証**。代理効用は学習効果ではありません。事業化承認、市場受容、講師の実測工数削減を意味しません。

| 項目 | 値 |
|---|---|
| 案件名 | {project.title.replace('|','／')} |
| 実行ID | `{run_id}` |
| UTC実行日時 | {created_at} |
| 生成モデル | `{model}`（Mac Studio / Ollama、Metal実稼働はMac側で確認） |
| 比較方式 | 静的Greedy / 厳密DP / Qwen生成候補 |
| 開発用seed（修正に使用） | {', '.join(map(str, dev_seeds))} |
| 最終評価用seed（Qwenに非開示） | {', '.join(map(str, holdout_seeds)) if holdout_executed else '未実行（DEVで有効候補なし）'} |
| 各seed生徒数 | {project.students_count} |
| コード改訂数 | {max(0,len(repair_attempts)-1)} / 上限 {project.max_repair_attempts} |
| **採用した開発試行** | {selected_label} |
| HOLDOUT実行 | {'実施' if holdout_executed else '未実行（無効候補のみ）'} |
| 最終 Functional Gate | {functional_gate} |
| 最終 Technology Gate | {selection_gate} |

## 1. 顧客の相談と未承認の要件ドラフト

{project.brief}

**顧客課題**：{req.customer_problem}

**対象ユーザー**：{', '.join(req.target_users)}

**提供価値の仮説**：{req.value_hypothesis}

### 必須機能・受入基準
{bullets(req.must_have)}
{bullets(req.acceptance_criteria)}

### 顧客確認が必要な事項
{bullets(req.unverified_assumptions)}
{bullets(req.unanswered_questions)}

## 2. 方式・評価手続き

- **A: 固定Greedy**：`gap × priority` の高い科目からまとめて時間を配分。
- **B: 厳密DP**：定義した分離可能・整数時間配分の代理効用の範囲で最適化。現実の学習成果の最適性ではありません。
- **C: Qwen生成コード**：E2Bでコード実行、FastAPI側の独立した決定的評価器で検証。
- 機能 **NO-GO**：制約違反・実行エラーの検証ログに基づく修正を指示。
- 品質 **HOLD**：開発用seedでの平均代理効用比と改善目標を返し、アルゴリズム改善を指示（最大{project.max_repair_attempts}回の改訂枠を共有）。
- **段階的な機能修正**：1回目は構造化した検証エラーと出力契約で修正。2回目以降は不変条件と静的ASTの参考診断を渡し、`allocate_hours`関数のみを構造的に差し替えます（該当関数が無い場合は修正失敗として記録）。
- **改訂案の選択**：制約を満たす開発試行のうち、開発用代理効用が最大のコードを選択。全試行で不合格なら**選択なし**、HOLDOUTをスキップ。
- **最終評価**：有効な候補がある場合に限り、隔離した別seedで1回だけ検証。最終結果をQwenへフィードバックしません。
- 制約：生徒と科目は各1回、時間は非負整数、科目上限以下、合計は利用可能時間と一致。
- 代理効用：`mean_students[Σ gap × priority × (1-exp(-hours/2.5)) / Σ(gap×priority)]`。
- しきい値：Qwen / DP ≥ {project.min_quality_ratio:.3f}、Qwen / 固定Greedy ≥ {project.min_improvement_ratio:.3f}。
- **注意**：この評価は固定した合成データ分布と仮定した代理効用の内部比較です。実測時間は単発のSandboxコマンド時間で、モデル推論・Sandbox起動・E2Bの実課金を含みません。

## 3. 開発用seedでの比較・反復

| 指標 | A: Greedy | B: 厳密DP | C: {'DEV選択候補' if selected_attempt_index is not None else '最後のNO-GO試行（不採用）'} |
|---|---:|---:|---:|
{comparison_table(dev_baseline, dev_optimal, dev_generated)}

| DEV seed | A | B | C | 制約 A/B/C |
|---|---:|---:|---:|---|
{per_seed_table(dev_baseline, dev_optimal, dev_generated)}

### 自動修正・品質改善履歴

{attempts_section(repair_attempts)}

> 開発用データへの適合は最終評価の成功を保証しません。品質フィードバックは開発用の集計値のみで、最終評価データは非開示です。

{holdout_section}
## 6. 事業仮説の単純試算（市場未検証）

| 入力仮定・計算項目 | 値 |
|---|---:|
| 月額料金／塾 | ¥{b.monthly_price_yen:,} |
| 有料契約塾数 | {b.paying_schools:,} |
| 月間売上（仮定） | ¥{scenario.monthly_revenue_yen:,} |
| 月間運用費（仮定） | ¥{scenario.monthly_operating_cost_yen:,} |
| 月間貢献利益（単純試算） | ¥{scenario.monthly_contribution_yen:,} |
| 月間講師工数削減（1塾当たり・仮定） | {b.hours_saved_per_school:.1f} 時間 |
| 1塾当たり仮の時間価値 | ¥{scenario.hypothetical_customer_value_yen:,.0f} |
| 単純損益分岐塾数 | {scenario.break_even_schools if scenario.break_even_schools is not None else '計算不能'} |

**Business Gate：未検証**。価格受容性・獲得費・導入費・解約率・教師の実測工数削減・学習成果など未確認。

## 7. 次の顧客検証と責任分担

{bullets(req.next_customer_validation)}

- [ ] 事業責任者：顧客ニーズ・支払意思・販売チャネルの調査
- [ ] 技術責任者：評価関数・データ分布・外れ値・制約の妥当性確認
- [ ] 現場講師：実務タスクでの作業時間・使い勝手・成果の評価

## 8. 実行再現情報

{hashes}

成果物：`requirements.json`、`datasets.json`、`baseline.py`、`optimal.py`、`attempts/attempt_XX.py`、`attempts/attempt_XX.json`、`attempts/attempt_XX.diff`、`run.json`、`report.md`。`generated.py`は有効な候補が存在するときだけ保存。APIキーは保存しません。**この実験は実顧客データへの外挿を保証しません。**
"""
