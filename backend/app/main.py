from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from .baseline import BASELINE_SOURCE
from .optimal import OPTIMAL_SOURCE
from .e2b_runner import run_in_e2b
from .evaluator import (
    build_plan_comparisons, business_scenario, canonical_json, decide_gates,
    normalize_plans, sha256_string,
)
from .models import (AnalyzeRequest, GenerateRequest, GeneratedCode, RequirementsDraft,
                     RunRequest, RunResponse, DesignRequest, ServiceDesign,
                     RefineRequest, RequirementRefinementProposal, ProjectInput)
from .ollama_client import (
    OLLAMA_MODEL, analyze_requirements, design_service, generate_code,
    refine_requirements, improve_code,
    local_model_status, repair_code,
)
from .report import generate_report
from .repair_loop import candidate_from_raw, execute_repair_loop
from .sample import SAMPLE_PROJECT, create_dataset
from .requirements_loop import assess_requirements, fallback_design

app = FastAPI(title="AI Venture Feasibility Studio", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False, allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)
ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "/app/artifacts"))


@app.get("/api/health")
async def health():
    model = await local_model_status()
    return {
        "api": "ok", "version": "0.6.0", "model": OLLAMA_MODEL,
        "ollama": model, "e2b_configured": bool(os.getenv("E2B_API_KEY", "").strip()),
        "sandbox": "E2B Cloud: separate sandboxes per method and revision",
    }


@app.get("/api/sample")
def sample():
    return SAMPLE_PROJECT


@app.post("/api/analyze", response_model=RequirementsDraft)
async def analyze(body: AnalyzeRequest):
    return await analyze_requirements(body.project)


@app.post("/api/design", response_model=ServiceDesign)
async def design(body: DesignRequest):
    return await design_service(body.project, body.requirements)


@app.post("/api/generate", response_model=GeneratedCode)
async def generate(body: GenerateRequest):
    # Legacy v0.5 API clients can omit service_design; the v0.6 UI always supplies it.
    if body.service_design is None:
        return await generate_code(body.project, body.requirements)
    return await generate_code(body.project, body.requirements, body.service_design)


def _safe_run_path(run_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f-]{36}", run_id):
        raise HTTPException(404, "Run not found")
    path = ARTIFACT_DIR / run_id
    if not (path / "run.json").is_file():
        raise HTTPException(404, "Run not found")
    return path


@app.post("/api/refine", response_model=RequirementRefinementProposal)
async def refine(body: RefineRequest):
    """Outer-loop proposal. Only DEV data and human evidence enter the LLM context."""
    path = _safe_run_path(body.run_id)
    previous = RunResponse.model_validate_json((path / "run.json").read_text(encoding="utf-8"))
    project = ProjectInput.model_validate_json((path / "project.json").read_text(encoding="utf-8"))
    req = RequirementsDraft.model_validate_json((path / "requirements.json").read_text(encoding="utf-8"))
    design = previous.service_design or fallback_design(req)
    summary = {
        "development_baseline_score": previous.development_baseline.score,
        "development_optimal_score": previous.development_optimal.score,
        "development_candidate_score": previous.development_generated.score,
        "development_candidate_errors": previous.development_generated.violations[:20],
        "repair_attempts": [{"verdict": a.verdict, "feedback": a.feedback[:900]}
                            for a in previous.repair_attempts],
        "requirement_assessment": previous.requirement_assessment.model_dump()
        if previous.requirement_assessment else None,
    }
    proposal = await refine_requirements(project, req, design, summary,
                                          body.evidence, body.run_id)
    # Preserve each proposed revision, without changing prior approved requirements.
    (path / f"proposal_{uuid.uuid4().hex[:12]}.json").write_text(
        proposal.model_dump_json(indent=2), encoding="utf-8")
    return proposal


def _remote_error(exc: Exception) -> str:
    key = os.getenv("E2B_API_KEY", "")
    text = f"{type(exc).__name__}: {str(exc)}"
    return (text.replace(key, "[REDACTED]") if key else text)[:400]


def _annotate_comparisons(baseline, optimal, generated, seeds, reference_raw, generated_raw):
    if generated.hard_constraint_pass:
        if baseline.hard_constraint_pass:
            generated.same_plans_as_baseline = sum(
                normalize_plans(generated_raw[seed].output) == normalize_plans(b.output)
                for seed, b in zip(seeds, reference_raw["baseline"])
            )
        if optimal.hard_constraint_pass:
            generated.same_plans_as_optimal = sum(
                normalize_plans(generated_raw[seed].output) == normalize_plans(o.output)
                for seed, o in zip(seeds, reference_raw["optimal"])
            )
    if generated.score is not None and optimal.score and optimal.score > 0:
        generated.relative_to_optimal = round(generated.score / optimal.score, 6)
    if generated.score is not None and baseline.score and baseline.score > 0:
        generated.relative_to_baseline = round(generated.score / baseline.score, 6)


@app.post("/api/run", response_model=RunResponse)
async def run(body: RunRequest):
    if not os.getenv("E2B_API_KEY", "").strip():
        raise HTTPException(503, "E2B_API_KEYが未設定です。Mac上の.envを確認してください。")
    try:
        ast.parse(body.code)
    except SyntaxError as exc:
        raise HTTPException(422, f"コードの構文エラー（line {exc.lineno}）") from exc

    project = body.project
    design = body.service_design or fallback_design(body.requirements)
    if body.parent_run_id:
        previous = RunResponse.model_validate_json((_safe_run_path(body.parent_run_id) / "run.json").read_text(encoding="utf-8"))
        if body.requirements_revision != previous.requirements_revision + 1:
            raise HTTPException(422, "要件改訂番号は親実行の番号+1にしてください。")
    elif body.requirements_revision != 0:
        raise HTTPException(422, "要件改訂が1以上ならparent_run_idが必要です。")
    dev_seeds = [project.seed + i for i in range(project.evaluation_seeds)]
    # The holdout is never used by the code-generation or refinement callbacks.
    # A requirement-level revision uses a disjoint holdout seed block.
    holdout_seeds = [project.seed + 10_000 * (1 + body.requirements_revision) + i
                     for i in range(project.holdout_seeds)]
    dev_data = {s: create_dataset(project.model_copy(update={"seed": s})) for s in dev_seeds}
    # Held-out datasets are materialized only if a functionally valid DEV candidate exists.
    holdout_data: dict[int, dict] = {}
    dataset_hashes = {str(s): sha256_string(canonical_json(data)) for s, data in dev_data.items()}

    # The model sees ONLY validation errors and aggregate development quality.
    try:
        dev_references = await asyncio.to_thread(
            run_in_e2b, dev_data, {"baseline": BASELINE_SOURCE, "optimal": OPTIMAL_SOURCE}
        )
        dev_baseline = candidate_from_raw("baseline", "Static Greedy", dev_data,
                                          dev_references["baseline"], BASELINE_SOURCE)
        dev_optimal = candidate_from_raw("optimal", "Exact DP / proxy optimum", dev_data,
                                         dev_references["optimal"], OPTIMAL_SOURCE)
        if not dev_baseline.hard_constraint_pass or not dev_optimal.hard_constraint_pass:
            raise HTTPException(502, "開発用データで参照アルゴリズムの検証に失敗しました。")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"E2B開発用Sandboxの初期化に失敗しました: {_remote_error(exc)}") from exc

    try:
        attempts, dev_generated_raw, revisions, selected_idx = await execute_repair_loop(
            dev_data, body.code, project.max_repair_attempts,
            execute=run_in_e2b, repair=repair_code, improve=improve_code,
            baseline=dev_baseline, optimal=dev_optimal,
            optimal_floor=project.min_quality_ratio,
            improvement_floor=project.min_improvement_ratio,
        )
    except Exception as exc:
        raise HTTPException(502, f"E2B開発用候補の実行に失敗しました: {_remote_error(exc)}") from exc
    selected_code = revisions[selected_idx] if selected_idx is not None else None
    # With no valid candidate, show the last DEV failure as diagnostics only.
    dev_generated = attempts[selected_idx].candidate if selected_idx is not None else attempts[-1].candidate
    if selected_idx is not None:
        assert dev_generated_raw is not None
        _annotate_comparisons(dev_baseline, dev_optimal, dev_generated, dev_seeds,
                              dev_references, dev_generated_raw)

    holdout_executed = selected_code is not None
    if holdout_executed:
        # One-time holdout. Never pass its results to the model or repair loop.
        holdout_data = {s: create_dataset(project.model_copy(update={"seed": s})) for s in holdout_seeds}
        dataset_hashes.update({str(s): sha256_string(canonical_json(data))
                               for s, data in holdout_data.items()})
        try:
            heldout_raw = await asyncio.to_thread(run_in_e2b, holdout_data, {
                "baseline": BASELINE_SOURCE, "optimal": OPTIMAL_SOURCE, "generated": selected_code,
            })
        except Exception as exc:
            raise HTTPException(502, f"E2B最終評価Sandboxに失敗しました: {_remote_error(exc)}") from exc
        baseline = candidate_from_raw("baseline", "Static Greedy", holdout_data,
                                       heldout_raw["baseline"], BASELINE_SOURCE)
        optimal = candidate_from_raw("optimal", "Exact DP / proxy optimum", holdout_data,
                                      heldout_raw["optimal"], OPTIMAL_SOURCE)
        generated = candidate_from_raw("generated", "Qwen code selected by DEV score", holdout_data,
                                        heldout_raw["generated"], selected_code)
        final_raw = {r.seed: r for r in heldout_raw["generated"]}
        _annotate_comparisons(baseline, optimal, generated, holdout_seeds, heldout_raw, final_raw)
        functional, selection, reasons = decide_gates(
            baseline, optimal, generated,
            optimal_floor=project.min_quality_ratio,
            improvement_floor=project.min_improvement_ratio,
        )
        plans = build_plan_comparisons(
            holdout_data,
            {r.seed: r for r in heldout_raw["baseline"]},
            {r.seed: r for r in heldout_raw["optimal"]}, final_raw,
        )
        plan_source = "holdout"
    else:
        baseline = optimal = generated = None
        functional = "NO-GO（DEV全試行が機能制約違反）"
        selection = "NO-GO（有効な生成候補なし・HOLDOUT未実行）"
        reasons = [
            f"全{len(attempts)}試行でFunctional Gateが不合格です。採用候補はありません。",
            "無効なコードを最良候補として採用せず、HOLDOUT Sandboxの実行を省略しました。",
            "各試行の失敗ログとコード差分を確認し、開発用データで合格してから再実行してください。",
        ]
        # Development examples ONLY. Label clearly so they cannot be mistaken for holdout.
        # Never fabricate a candidate plan when every generated program failed.
        plans = build_plan_comparisons(
            dev_data,
            {r.seed: r for r in dev_references["baseline"]},
            {r.seed: r for r in dev_references["optimal"]}, {},
        )
        plan_source = "development"
    assessment = assess_requirements(body.requirements, body.customer_evidence,
                                     bool(holdout_executed and generated and generated.hard_constraint_pass))
    scenario = business_scenario(project.business)
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = str(uuid.uuid4())
    report = generate_report(
        run_id=run_id, created_at=created_at, project=project, req=body.requirements,
        model=OLLAMA_MODEL, dev_datasets=dev_data, holdout_datasets=holdout_data,
        dataset_hashes=dataset_hashes, dev_baseline=dev_baseline,
        dev_optimal=dev_optimal, dev_generated=dev_generated,
        baseline=baseline, optimal=optimal, generated=generated,
        repair_attempts=attempts, selected_attempt_index=selected_idx,
        holdout_executed=holdout_executed, plan_comparisons_source=plan_source,
        plan_comparisons=plans, functional_gate=functional,
        selection_gate=selection, gate_reasons=reasons, scenario=scenario,
    )
    # Requirement validation is separate from technical feasibility. Never turn a
    # synthetic technical score into a claim that real customer value is proven.
    report = report.replace("v0.5 —", "v0.6 —", 1)
    report += "\n\n" + _requirement_report_extension(
        design, assessment, body.customer_evidence, body.requirements_revision,
        body.parent_run_id, body.requirements, project,
    )
    result = RunResponse(
        run_id=run_id, created_at=created_at, model=OLLAMA_MODEL,
        seeds=dev_seeds, holdout_seeds=holdout_seeds, dataset_hashes=dataset_hashes,
        development_baseline=dev_baseline, development_optimal=dev_optimal,
        development_generated=dev_generated,
        baseline=baseline, optimal=optimal, generated=generated,
        repair_attempts=attempts, max_repair_attempts=project.max_repair_attempts,
        selected_attempt_index=selected_idx, holdout_executed=holdout_executed,
        plan_comparisons_source=plan_source, plan_comparisons=plans,
        functional_gate=functional, selection_gate=selection,
        business_gate="未検証（実顧客の検証が必要）", gate_reasons=reasons,
        business_scenario=scenario, report_markdown=report,
        service_design=design, customer_evidence=body.customer_evidence,
        requirement_assessment=assessment,
        requirements_revision=body.requirements_revision,
        parent_run_id=body.parent_run_id,
        requirements_sha256=sha256_string(canonical_json(body.requirements.model_dump())),
        service_design_sha256=sha256_string(canonical_json(design.model_dump())),
    )
    folder = ARTIFACT_DIR / run_id
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "report.md").write_text(report, encoding="utf-8")
    (folder / "requirements.json").write_text(body.requirements.model_dump_json(indent=2), encoding="utf-8")
    (folder / "project.json").write_text(project.model_dump_json(indent=2), encoding="utf-8")
    (folder / "service_design.json").write_text(design.model_dump_json(indent=2), encoding="utf-8")
    (folder / "customer_evidence.json").write_text(
        json.dumps([e.model_dump() for e in body.customer_evidence], ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "requirement_assessment.json").write_text(assessment.model_dump_json(indent=2), encoding="utf-8")
    (folder / "requirement_change_log.json").write_text(json.dumps({
        "run_id": run_id, "parent_run_id": body.parent_run_id,
        "revision": body.requirements_revision,
        "requirements_sha256": result.requirements_sha256,
        "service_design_sha256": result.service_design_sha256,
        "customer_evidence_ids": [e.evidence_id for e in body.customer_evidence],
        "decision": "HUMAN_REVIEW_REQUIRED", "timestamp": created_at,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "datasets.json").write_text(json.dumps(
        {"development": dev_data, "holdout": holdout_data}, ensure_ascii=False, indent=2), encoding="utf-8")
    for name, source in {"baseline": BASELINE_SOURCE, "optimal": OPTIMAL_SOURCE}.items():
        (folder / f"{name}.py").write_text(source, encoding="utf-8")
    if selected_code is not None:
        (folder / "generated.py").write_text(selected_code, encoding="utf-8")
    attempts_folder = folder / "attempts"
    attempts_folder.mkdir()
    for attempt in attempts:
        (attempts_folder / f"attempt_{attempt.attempt_index:02d}.py").write_text(
            revisions[attempt.attempt_index], encoding="utf-8")
        (attempts_folder / f"attempt_{attempt.attempt_index:02d}.json").write_text(
            attempt.model_dump_json(indent=2), encoding="utf-8")
        if attempt.code_diff:
            (attempts_folder / f"attempt_{attempt.attempt_index:02d}.diff").write_text(
                attempt.code_diff, encoding="utf-8")
    (folder / "run.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return result


@app.get("/api/reports/{run_id}/report.md")
def download_report(run_id: str):
    if not re.fullmatch(r"[0-9a-f-]{36}", run_id):
        raise HTTPException(404, "Report not found")
    path = ARTIFACT_DIR / run_id / "report.md"
    if not path.is_file():
        raise HTTPException(404, "Report not found")
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=f"report-{run_id}.md")


def _requirement_report_extension(design, assessment, evidence, revision, parent_id, req, project) -> str:
    from .report import bullets
    findings = "\n".join(
        f"| {f.requirement_id} | {f.criterion.replace('|', '／')} | {f.status} | "
        f"{', '.join(f.admissible_evidence_ids) or 'なし'} |"
        for f in assessment.findings
    )
    provenance = "\n".join(
        f"| {e.evidence_id} | {e.requirement_id} | {e.provenance} | {e.verdict} | "
        f"{'確認済み（自己申告）' if e.human_verified else '未確認'} | "
        f"{e.source_reference.replace('|', '／') or '出典未入力'} |"
        for e in evidence
    ) or "| （なし） | — | — | — | — | — |"
    return f"""## 9. サービス設計（要件と実装の中間表現）

**設計の状態**：`{design.design_source}`。要件と設計の一致は独立評価していません。生成された設計は人間による確認前のドラフトです。

**提供範囲**：{design.product_scope}

### Actors / Use cases
{bullets(design.actors)}
{bullets(design.use_cases)}

### 業務フロー・ドメイン
{bullets(design.service_flow)}
{bullets(design.domain_entities)}

### ハード制約・ソフト目的・受入テスト
{bullets(design.hard_constraints)}
{bullets(design.soft_objectives)}
{bullets(design.acceptance_tests)}

### 代替案・未確認の前提
{bullets(design.alternatives)}
{bullets(design.assumptions)}

## 10. 二軸の検証結果

| 検証軸 | 判定 | 判断主体・根拠 |
|---|---|---|
| 実装の正しさ | {assessment.implementation_validity} | 独立決定的評価器＋E2B最終評価 |
| 要件の妥当性 | **{assessment.requirement_validity}** | 顧客証拠の出典・人間の確認状況（暫定） |

{assessment.note}

| 受入基準ID | 要件 | 暫定評価 | 採用した証拠ID |
|---|---|---|---|
{findings}

### 顧客証拠台帳（LLM生成の根拠ではない）

| Evidence ID | 要件ID | 由来 | 向き | 人間の確認 | 出典 |
|---|---|---|---|---|---|
{provenance}

### 未検証事項と次の顧客確認
{bullets(assessment.next_customer_validation)}

## 11. Requirement Refinement / 監査ログ

- 要件改訂番号：**{revision}**
- 直前の実行ID：`{parent_id or 'なし（初回）'}`
- 要件JSON SHA256：`{sha256_string(canonical_json(req.model_dump()))}`
- サービス設計JSON SHA256：`{sha256_string(canonical_json(design.model_dump()))}`
- 顧客証拠件数：**{len(evidence)}**
- 要件の自動承認：**しない**（人間の明示的な採否判断が必要）
- 改訂後は新しいHOLDOUT seed群を使用する（同じ最終データを改訂フィードバックへ流用しない）。
- `/api/refine` が返すのは**提案のみ**で、既存要件は書き換えない。

**重要な制限**：現行の独立評価器・データ生成器は教育SaaSの週次配分問題に特化。海外InsurTech等の設計案を入力しても、この実験でその業務要件を検証したことにはなりません。実運用の保険案件には独立したドメイン評価器と顧客データ検証が必要です。
"""
