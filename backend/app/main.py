"""Claims Operations Planner v0.10: E2B + local Qwen + auditable two-level verification."""
from __future__ import annotations

import asyncio
import io
import zipfile
import difflib
from dataclasses import asdict
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import statistics
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

from .domain import (CONTRACT_R0, CONTRACT_R1, SERVICE_R0, SERVICE_R1,
                     SIMULATED_EVIDENCE, canonical, sha256, make_dataset,
                     get_reference_sources, validate, common_score)
from .e2b_runner import run_in_e2b
from . import llm
from . import diagnostic_quality as dq
from .diagnostic_benchmark import FIXTURES, FIXTURE_VERSION, public_cases

ARTIFACT_DIR = Path(os.getenv("ARTIFACT_DIR", "/app/artifacts"))
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


BRIEF = ("想定顧客：ドイツ国内で実績があり欧州の複数国への展開を検討する保険業務SaaS企業（架空）。"
         "案件ごとに審査所要時間、期限、保険金請求額、必要資格が異なる。"
         "固定の審査人員・勤務時間で、先着順よりも期限超過を減らしたい。"
         "支払可否は人間が判断する。顧客固有のEU法規制適合は未検証。"
         "サービス設計→コード生成→E2B評価→要件改訂を再現可能な実験にする。")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fresh_id() -> str:
    return str(uuid.uuid4())


def path_for(kind: str, id_: str) -> Path:
    try:
        if str(uuid.UUID(id_)) != id_:
            raise ValueError()
    except ValueError as exc:
        raise HTTPException(404, "Artifact not found") from exc
    return ARTIFACT_DIR / kind / id_


def store(kind: str, id_: str, filename: str, data: object):
    p = path_for(kind, id_)
    p.mkdir(parents=True, exist_ok=True)
    target = p / filename
    with target.open("x", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data, indent=2, ensure_ascii=False))
    return target


app = FastAPI(title="Claims Operations Planner · AI Venture Feasibility Studio", version="0.10.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["GET", "POST"], allow_headers=["Content-Type"])


def store_raw_e2b(kind: str, id_: str, stage: str, runs: dict) -> None:
    """Persist per-seed raw E2B output, stderr/stdout, sandbox IDs and hashes."""
    for approach, series in runs.items():
        for item in series:
            store(kind, id_, f"{stage}_{approach}_seed_{item.seed}.json", asdict(item))


def store_attempt_code(experiment_id: str, number: int, source: str, previous: str | None) -> None:
    store("experiments", experiment_id, f"attempt_{number:02d}.py", source)
    diff = ''.join(difflib.unified_diff((previous or '').splitlines(keepends=True),
                   source.splitlines(keepends=True), fromfile="previous.py", tofile=f"attempt_{number:02d}.py"))
    store("experiments", experiment_id, f"attempt_{number:02d}.diff", diff or "# initial or unchanged\n")


def store_failure(eid: str, phase: str, exc: Exception):
    """Preserve failed operations, not only successful experiments."""
    item={"experiment_id": eid, "created_at":now(), "status":"FAILED",
          "phase":phase, "error_type":type(exc).__name__, "detail":str(exc)[:700]}
    store("experiments", eid, "error.json", item)
    store("experiments", eid, "experiment.json", item)
    store("experiments", eid, "report.md", "# FAILED — " + phase + "\n\n" + item["detail"] + "\n")


def _artifact_index(kind: str):
    """Demonstration-only: local artifact index, no auth / multi-tenancy."""
    if kind not in {"runs", "proposals", "approvals", "experiments", "benchmarks"}:
        raise HTTPException(404, "Unknown artifact type")
    base = ARTIFACT_DIR / kind
    results = []
    if base.exists():
        primary = {"runs":"run.json", "proposals":"proposal.json", "approvals":"approval.json", "experiments":"experiment.json", "benchmarks":"benchmark.json"}[kind]
        for folder in base.iterdir():
            if not folder.is_dir():
                continue
            f = folder / primary
            if not f.exists() and kind == "benchmarks":
                f = folder / "started.json"  # interrupted benchmark is still exportable
            if f.exists():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                    results.append({"id": folder.name, "created_at": data.get("created_at", data.get("timestamp_utc", "")),
                                    "status": data.get("status", data.get("decision", "completed")),
                                    "report_available": (folder / "report.md").exists(),
                                    "files": len([x for x in folder.iterdir() if x.is_file()])})
                except (OSError, ValueError):
                    pass
    return sorted(results, key=lambda r: r["created_at"], reverse=True)[:200]


@app.get("/api/history/{kind}")
def history(kind: str):
    return {"kind": kind, "items": _artifact_index(kind)}


@app.get("/api/artifacts/{kind}/{artifact_id}/bundle")
def artifact_bundle(kind: str, artifact_id: str):
    if kind not in {"runs", "proposals", "approvals", "experiments", "benchmarks"}:
        raise HTTPException(404, "Unknown artifact kind")
    p = path_for(kind, artifact_id)
    if not p.is_dir():
        raise HTTPException(404, "Artifact not found")
    data = io.BytesIO()
    with zipfile.ZipFile(data, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        # Export related records too so the R0 -> evidence -> approval -> experiment chain can be audited offline.
        folders = [(kind, artifact_id)]
        if kind == "experiments" and (p / "experiment.json").exists():
            exp = json.loads((p / "experiment.json").read_text())
            folders += [("runs", exp["r0_run_id"]), ("proposals", exp["proposal_id"]), ("approvals", exp["approval_id"])]
        for k, identifier in folders:
            fp = path_for(k, identifier)
            if fp.is_dir():
                for f in sorted(fp.iterdir()):
                    if f.is_file() and f.stat().st_size < 2_000_000:
                        z.write(f, arcname=f"{k}/{identifier}/{f.name}")
    data.seek(0)
    return StreamingResponse(data, media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="claims_{kind}_{artifact_id}.zip"'})


@app.get("/api/artifacts/{kind}/{artifact_id}")
def artifact_detail(kind: str, artifact_id: str):
    if kind not in {"runs", "proposals", "approvals", "experiments", "benchmarks"}:
        raise HTTPException(404, "Unknown artifact kind")
    filename={"runs":"run.json", "proposals":"proposal.json", "approvals":"approval.json", "experiments":"experiment.json", "benchmarks":"benchmark.json"}[kind]
    return load(kind, artifact_id, filename)


def load(kind: str, id_: str, filename: str) -> dict:
    path = path_for(kind, id_) / filename
    if not path.is_file():
        raise HTTPException(404, "Artifact not found")
    return json.loads(path.read_text(encoding="utf-8"))


def load_code(kind: str, id_: str, name: str) -> str:
    target = path_for(kind, id_) / name
    if not target.is_file():
        raise HTTPException(404, "Code artifact not found")
    return target.read_text(encoding="utf-8")


class R0Request(BaseModel):
    seed: int = Field(42, ge=0, le=9999)
    brief: str = Field(default=BRIEF, min_length=20, max_length=5000)
    service_design: dict | None = None


class ProposeRequest(BaseModel):
    r0_run_id: str
    evidence_condition: Literal["counterexample", "control"] = "counterexample"


class ApprovalRequest(BaseModel):
    proposal_id: str
    decision: Literal["approved", "rejected"]
    actor: str = Field(min_length=2, max_length=100)
    rationale: str = Field(min_length=5, max_length=1000)
    # Never converts an LLM HOLD to PASS. Permits a separately logged human adjudication.
    domain_review_override: bool = False
    override_rationale: str | None = Field(default=None, max_length=1500)
    acknowledges_independent_r0_pass: bool = False


class GenerateRequest(BaseModel):
    approval_id: str


class EvaluateRequest(BaseModel):
    approval_id: str
    python_code: str = Field(min_length=100, max_length=30000)
    max_repairs: int = Field(2, ge=0, le=2)


class DesignRequest(BaseModel):
    brief: str = Field(default=BRIEF, min_length=20, max_length=5000)
    version: Literal["r0", "r1"] = "r0"


def _evaluate_e2b(runs: dict, datasets: dict, *, r0_strict: bool = False) -> dict:
    out = {}
    for name, series in runs.items():
        items = []
        for raw in series:
            dataset = datasets[raw.seed]
            metric = validate(dataset, raw.output, policy="r0" if (name == "fifo" and r0_strict) else "r1")
            if raw.error:
                metric["valid"] = False
                metric["violations"].append(raw.error)
            metric.update({"seed": raw.seed, "sandbox_id": raw.sandbox_id,
                           "source_sha256": raw.source_sha256, "output_sha256": raw.output_sha256,
                           "dataset_sha256": sha256(dataset), "elapsed_seconds": raw.elapsed_seconds,
                           "stderr": raw.stderr[-250:]})
            items.append(metric)
        out[name] = items
    return out


def _aggregate(rows: list[dict]) -> dict:
    if not rows:
        return {"valid": False, "missed_total": None, "worked_hours_total": None}
    valid = all(x["valid"] for x in rows)
    return {"valid": valid,
            "missed_total": sum(m["missed_deadlines"] for m in rows) if valid else None,
            "worked_hours_total": sum(m["assigned_hours"] for m in rows) if valid else None,
            "deadline_hit_rate": round(statistics.mean(m["deadline_hit_rate"] for m in rows), 5) if valid else None,
            "all_claims_completed": valid and all(m["completed"] == m["total_cases"] for m in rows),
            "violations": [v for m in rows for v in m["violations"]][:10], "seeds": [m["seed"] for m in rows]}


@app.get("/api/sample")
def sample():
    return {"title": "Claims Operations Planner", "version": "0.10.0", "customer_profile": "German InsurTech SaaS (fictional)",
            "brief": BRIEF, "contract_r0": CONTRACT_R0, "contract_r1": CONTRACT_R1,
            "service_design_r0": SERVICE_R0, "service_design_r1": SERVICE_R1,
            "synthetic_counterexample": SIMULATED_EVIDENCE,
            "business_hypotheses_eur": {"monthly_license_fee": 2500, "pilot_clients": 4,
                "monthly_operating_cost": 6000, "label": "illustrative assumptions only; no observed WTP/CAC"},
            "evaluation_dimensions": ["implementation correctness", "requirement validity", "deadline adherence", "fixed staffed hours"],
            "diagnostic_models": {"code_generator": llm.MODEL, "independent_vertical_fm": llm.FINANCE_MODEL,
                "vertical_base": llm.FINANCE_MODEL_SOURCE}}


@app.get("/api/health")
async def health():
    return {"app": "ok", "version": "0.10.0", "e2b_configured": bool(os.getenv("E2B_API_KEY")),
            "ollama": await llm.status()}


@app.post("/api/design")
async def design(body: DesignRequest):
    draft = await llm.design(body.brief, CONTRACT_R0 if body.version == "r0" else CONTRACT_R1)
    return {"service_design": draft.model_dump(), "approved": False,
            "warning": "LLM-generated service design is a draft; the independent acceptance contract is pinned."}


@app.post("/api/run-r0")
async def run_r0(body: R0Request):
    rid = fresh_id()
    dev = [body.seed, body.seed+1, body.seed+2]
    holdout = [body.seed+10000, body.seed+10001]
    datasets = {seed: make_dataset(seed) for seed in dev + holdout}
    fifo, deadline = get_reference_sources()
    try:
        raws = await asyncio.to_thread(run_in_e2b, datasets, {"fifo": fifo, "deadline": deadline})
    except Exception as exc:
        err = {"run_id": rid, "created_at":now(), "status":"FAILED",
               "implementation_validity":"UNVERIFIED", "error":str(exc)[:600], "brief":body.brief}
        store("runs", rid, "run.json", err)
        store("runs", rid, "report.md", "# R0 execution failed\n\n" + str(exc)[:600] + "\n")
        raise HTTPException(502, "E2B実行に失敗しました: " + str(exc)[:240]) from exc
    store_raw_e2b("runs", rid, "e2b", raws)
    results = _evaluate_e2b(raws, datasets, r0_strict=True)
    dev_metrics = {name: _aggregate([m for m in metrics if m["seed"] in dev]) for name, metrics in results.items()}
    held_metrics = {name: _aggregate([m for m in metrics if m["seed"] in holdout]) for name, metrics in results.items()}
    if not dev_metrics["fifo"]["valid"] or not held_metrics["fifo"]["valid"]:
        raise HTTPException(502, "R0 FIFOの独立評価が失敗しました。")
    data = {"run_id": rid, "created_at": now(), "version": "0.10.0", "contract": CONTRACT_R0,
            "service_design": body.service_design or SERVICE_R0, "brief": body.brief,
            "seed": body.seed, "dev_seeds": dev, "holdout_seeds": holdout,
            "development": dev_metrics, "holdout": held_metrics,
            "seed_evidence": results, "implementation_validity": "PASS",
            "requirement_validity": "UNVERIFIED", "evidence_count": 0,
            "models": {"coding": llm.MODEL, "vertical": llm.FINANCE_MODEL},
            "note": "R0 FIFO contract passes. Deadline KPI is synthetic; no market evidence."}
    store("runs", rid, "run.json", data)
    store("runs", rid, "fifo.py", fifo)
    store("runs", rid, "deadline_reference.py", deadline)
    store("runs", rid, "dataset_hashes.json", {str(s): sha256(datasets[s]) for s in datasets})
    store("runs", rid, "report.md", report_r0(data))
    return data


@app.post("/api/propose")
async def propose(body: ProposeRequest):
    parent = load("runs", body.r0_run_id, "run.json")
    if parent["implementation_validity"] != "PASS":
        raise HTTPException(422, "R0 implementation must pass before proposing a revision")
    pid = fresh_id()
    store("proposals", pid, "request.json", {"parent_run_id": body.r0_run_id,
          "evidence_condition": body.evidence_condition, "created_at": now(),
          "coding_model": llm.MODEL, "finance_model": llm.FINANCE_MODEL})
    # Independent inputs and SEQUENTIAL invocations to avoid simultaneously loading
    # 30B + 8B into constrained Mac unified memory. Neither sees the other's output.
    # A failed/missing vertical model must not silently fall back to Qwen.
    try:
        diagnosis = await llm.diagnosis(parent["development"], body.evidence_condition)
        store("proposals", pid, "qwen_diagnosis.json", diagnosis.model_dump())
        finance_diagnosis = await llm.finance_diagnosis(parent["development"], body.evidence_condition)
        store("proposals", pid, "oda_diagnosis.json", finance_diagnosis.model_dump())
    except Exception as exc:
        err = {"created_at":now(), "error_type":type(exc).__name__,
               "detail": str(getattr(exc,"detail",exc))[:600]}
        store("proposals", pid, "diagnostic_error.json", err)
        store("proposals", pid, "proposal.json", {"proposal_id":pid,
              "parent_run_id":body.r0_run_id, "status":"FAILED", "diagnostic_error":err})
        raise
    # Independent multi-dimensional rubric: DO NOT accept a correct category paired with
    # a self-contradictory explanation or a conflicting scheduling revision.
    vertical_score = dq.legacy_diagnostic_score(finance_diagnosis.model_dump(),
                       condition=body.evidence_condition, is_vertical=True)
    coding_score = dq.legacy_diagnostic_score(diagnosis.model_dump(),
                       condition=body.evidence_condition, is_vertical=False)
    domain_pass, domain_errors = vertical_score["pass"], vertical_score["failure_codes"]
    baseline_pass = coding_score["pass"]
    evidence = [SIMULATED_EVIDENCE] if body.evidence_condition == "counterexample" else []
    proposal = {"proposal_id": pid, "parent_run_id": body.r0_run_id, "created_at": now(),
                "condition": body.evidence_condition, "evidence": evidence,
                "diagnosis": diagnosis.model_dump(), "diagnosis_matches_rubric": baseline_pass,
                "finance_diagnosis": finance_diagnosis.model_dump(),
                "finance_diagnosis_matches_rubric": domain_pass,
                "finance_diagnosis_rubric_failures": domain_errors,
                "qwen_diagnostic_quality": coding_score,
                "oda_diagnostic_quality": vertical_score,
                "synthetic_requirement_fit": vertical_score["synthetic_requirement_fit"],
                "real_customer_business_validity":"UNVERIFIED",
                "model_comparison": {"qwen":llm.MODEL, "oda_fin_rl_8b":llm.FINANCE_MODEL,
                    "same_inputs_independent": True,
                    "classification_agreement": diagnosis.classification == finance_diagnosis.classification,
                    "qwen_rubric_pass":baseline_pass, "finance_rubric_pass":domain_pass},
                "contract_before": CONTRACT_R0, "proposed_contract": CONTRACT_R1,
                "proposed_service_design": SERVICE_R1, "contract_delta": [
                    "REQ-QUEUE-001 stable ID", "FIFO arrival order → deadline / skill aware ordering",
                    "No increase in planned reviewer hours or overtime", "Same qualification and duration constraints",
                    "Independent pinned R1 evaluator; model cannot edit test rules",
                    "Synthetic deadline KPI compared on new HOLDOUT",],
                "status": "AWAITING_HUMAN_APPROVAL" if domain_pass else "DOMAIN_REVIEW_HOLD",
                "external_validity": "UNVERIFIED"}
    store("proposals", pid, "proposal.json", proposal)
    return proposal


def approved(aid: str) -> tuple[dict, dict, dict]:
    rec = load("approvals", aid, "approval.json")
    prop = load("proposals", rec["proposal_id"], "proposal.json")
    run = load("runs", rec["parent_run_id"], "run.json")
    if rec["decision"] != "approved" or prop["condition"] != "counterexample":
        raise HTTPException(422, "Approved counterexample required")
    if not prop.get("finance_diagnosis"):
        raise HTTPException(409, "ODA diagnostic record required; old v0.8 approvals cannot be reused")
    if rec.get("domain_review_override"):
        if prop.get("finance_diagnosis_matches_rubric") or not rec.get("acknowledges_independent_r0_pass"):
            raise HTTPException(409, "Human review override is inconsistent with the proposal")
        if run.get("implementation_validity") != "PASS" or not any(
            e.get("evidence_id") == "SIM-SLA-001" and e.get("provenance") == "synthetic"
            for e in prop.get("evidence", [])
        ):
            raise HTTPException(409, "Override requires independent R0 PASS and the pinned synthetic evidence")
    elif not prop.get("finance_diagnosis_matches_rubric"):
        raise HTTPException(409, "ODA rubric HOLD requires explicit, audited human review override")
    if rec.get("finance_diagnosis_sha256") != sha256(prop["finance_diagnosis"]):
        raise HTTPException(409, "ODA diagnosis has changed since approval")
    if rec["contract_r0_sha256"] != sha256(CONTRACT_R0) or rec["contract_r1_sha256"] != sha256(CONTRACT_R1):
        raise HTTPException(409, "Evaluator contract changed since approval")
    if rec["evidence_sha256"] != sha256(prop["evidence"]) or rec["service_sha256"] != sha256(SERVICE_R1):
        raise HTTPException(409, "Evidence or design changed since approval")
    return rec, prop, run


@app.post("/api/approve")
def approve(body: ApprovalRequest):
    proposal = load("proposals", body.proposal_id, "proposal.json")
    if body.decision == "approved" and proposal["condition"] != "counterexample":
        raise HTTPException(422, "Cannot approve a change without a counterexample")
    override = body.decision == "approved" and body.domain_review_override
    if body.decision == "approved" and not proposal.get("finance_diagnosis_matches_rubric", False):
        if not override:
            raise HTTPException(422, "ODA diagnostic HOLD: acknowledge and document independent human review to proceed")
        parent = load("runs", proposal["parent_run_id"], "run.json")
        if (parent.get("implementation_validity") != "PASS"
            or not any(e.get("evidence_id") == "SIM-SLA-001" and e.get("provenance") == "synthetic"
                       for e in proposal.get("evidence", []))):
            raise HTTPException(422, "Override requires independent R0 PASS and pinned synthetic evidence")
        if (not body.acknowledges_independent_r0_pass or
            len((body.override_rationale or "").strip()) < 20):
            raise HTTPException(422, "Human review must acknowledge R0 PASS and explain ODA errors (20+ characters)")
    elif override:
        raise HTTPException(422, "An override is unnecessary when the ODA rubric passes")
    # A pre-filled/stale human explanation must not contradict the actual saved ODA output.
    # This guards the exact audit flaw observed in v0.9.1; it is a narrow textual guard,
    # not general natural-language fact verification.
    if override:
        original = proposal.get("finance_diagnosis", {})
        narrative = (body.override_rationale or "").lower()
        if original.get("r0_implementation_assessment") == "correct" and (
            "odaはincorrect" in narrative or "odaがincorrect" in narrative
            or "oda incorrectly says implementation is incorrect" in narrative
        ):
            raise HTTPException(422, "監査理由が保存済みODA診断と矛盾します。incorrect以外の実際のHOLD原因を記録してください。")
    target = path_for("proposals", body.proposal_id) / "decision.json"
    rid = fresh_id()
    rec = {"approval_id": rid, "proposal_id": body.proposal_id,
           "parent_run_id": proposal["parent_run_id"], "decision": body.decision,
           "actor": body.actor, "rationale": body.rationale, "timestamp_utc": now(),
           "contract_r0_sha256": sha256(CONTRACT_R0), "contract_r1_sha256": sha256(CONTRACT_R1),
           "service_sha256": sha256(SERVICE_R1), "evidence_sha256": sha256(proposal["evidence"]),
           "finance_diagnosis_sha256": sha256(proposal.get("finance_diagnosis", {})),
           "finance_model": llm.FINANCE_MODEL,
           "domain_review_override": bool(override),
           "acknowledges_independent_r0_pass": bool(override and body.acknowledges_independent_r0_pass),
           "override_rationale": body.override_rationale.strip() if override else None,
           "original_oda_rubric_status": "PASS" if proposal.get("finance_diagnosis_matches_rubric") else "HOLD",
           "original_oda_rubric_failures": proposal.get("finance_diagnosis_rubric_failures", []),
           "approval_path": "audited_human_review" if override else "rubric_pass_human_approved"}
    try:
        with target.open("x", encoding="utf-8") as f:
            f.write(json.dumps(rec, indent=2, ensure_ascii=False))
    except FileExistsError as exc:
        raise HTTPException(409, "Proposal already approved/rejected") from exc
    store("approvals", rid, "approval.json", rec)
    return rec


def domain_context_for_generation(rec: dict, prop: dict) -> dict:
    """Never feed a failed ODA diagnosis to the coder as an approved conclusion."""
    if not rec.get("domain_review_override"):
        return prop["finance_diagnosis"]
    return {
        "source": "independent_R0_evaluator_and_human_adjudication",
        "oda_diagnosis": "HOLD_NOT_RELIABLE; see stored original in proposal evidence",
        "independent_r0_finding": "FIFO implementation PASS: no software bug established",
        "business_mismatch_hypothesis": "Synthetic deadline counterexample SIM-SLA-001",
        "human_override_rationale": rec["override_rationale"],
        "pinned_r1_policy": CONTRACT_R1["rule"],
        "real_customer_validity": "UNVERIFIED",
    }


@app.post("/api/generate-r1")
async def generate_r1(body: GenerateRequest):
    rec, prop, parent = approved(body.approval_id)
    result = await llm.generate(parent["brief"], SERVICE_R1,
                                domain_review=domain_context_for_generation(rec, prop))
    generated_id = fresh_id()
    store("approvals", body.approval_id, f"generated_{generated_id}.py", result.python_code)
    store("approvals", body.approval_id, f"generated_{generated_id}.json",
          {"source_sha256": sha256(result.python_code), "rationale":result.rationale,
           "created_at":now(), "coding_model":llm.MODEL, "finance_model":llm.FINANCE_MODEL,
           "domain_review_sha256": sha256(prop["finance_diagnosis"]),
           "domain_review_used_as_advisory":not rec.get("domain_review_override", False),
           "human_adjudication_used_instead":rec.get("domain_review_override", False)})
    return {"approval_id": rec["approval_id"], "python_code": result.python_code,
            "rationale": result.rationale, "source_sha256": sha256(result.python_code), "generated_id": generated_id,
            "note": "Untrusted draft. Needs E2B execution and independent domain validation."}


@app.post("/api/evaluate-r1")
async def evaluate_r1(body: EvaluateRequest):
    rec, prop, parent = approved(body.approval_id)
    # Refuse retests against prior evaluation: fresh new approval must be generated for another experiment.
    eid = fresh_id()
    marker = path_for("approvals", body.approval_id) / "evaluation_started.json"
    try:
        with marker.open("x", encoding="utf-8") as f:
            f.write(json.dumps({"started_at": now(), "experiment_id":eid}, ensure_ascii=False))
    except FileExistsError as exc:
        raise HTTPException(409, "This approval has already been used to evaluate R1") from exc
    store("experiments", eid, "started.json", {"created_at":now(), "approval_id":body.approval_id,
          "r0_run_id": parent["run_id"], "source_sha256":sha256(body.python_code)})
    store("experiments", eid, "input_candidate.py", body.python_code)
    seed = parent["seed"]
    dev_seeds = [seed+100, seed+101, seed+102]
    holdout_seeds = [seed+20000, seed+20001]
    dev_data = {s: make_dataset(s) for s in dev_seeds}
    fifo, deadline = get_reference_sources()
    try:
        dev_refs = await asyncio.to_thread(run_in_e2b, dev_data, {"fifo": fifo, "deadline": deadline})
    except Exception as exc:
        store_failure(eid, "E2B DEV reference", exc)
        raise HTTPException(502, "E2B DEV参照評価に失敗: " + str(exc)[:240]) from exc
    store_raw_e2b("experiments", eid, "dev_reference", dev_refs)
    reference_metrics = _evaluate_e2b(dev_refs, dev_data)
    attempts = []
    selected = None
    selected_metric = None
    current_code = body.python_code
    previous_code = None
    for ix in range(body.max_repairs + 1):
        try:
            raw = await asyncio.to_thread(run_in_e2b, dev_data, {"generated": current_code})
            metrics = _evaluate_e2b(raw, dev_data)["generated"]
        except Exception as exc:
            metrics = [{"seed": s, "valid": False, "violations": ["E2B error: " + str(exc)[:180]],
                        "missed_deadlines": None, "assigned_hours": None} for s in dev_seeds]
        store_attempt_code(eid, ix, current_code, previous_code)
        if "raw" in locals():
            # A crashed SDK call has no RawCandidate; keep the exception in attempt JSON.
            if isinstance(raw, dict) and "generated" in raw:
                store_raw_e2b("experiments", eid, f"dev_attempt_{ix:02d}", raw)
            del raw
        agg = _aggregate(metrics)
        base = reference_metrics["fifo"]
        meets_business = (agg["valid"] and all(m["assigned_hours"] == b["assigned_hours"] and
                                            m["missed_deadlines"] <= b["missed_deadlines"]
                                            for m,b in zip(metrics,base)))
        attempt = {"attempt": ix, "code_sha256": sha256(current_code),
                   "evaluation": agg, "metrics": metrics,
                   "passes_fixed_hours_and_deadline": meets_business}
        attempts.append(attempt)
        store("experiments", eid, f"attempt_{ix:02d}.json", attempt)
        if meets_business and (selected_metric is None or agg["missed_total"] < selected_metric["missed_total"]):
            selected, selected_metric = current_code, agg
        # If already no missed deadlines on DEV, no benefit from repairs.
        if selected_metric and selected_metric["missed_total"] == 0:
            break
        if ix == body.max_repairs:
            break
        # Only development metrics feed back into Qwen. Holdout is not created until selection.
        feedback = canonical({"candidate": agg,
            "relevant_failures": [m["violations"][:5] for m in metrics],
            "fifo_dev": _aggregate(base), "deadline_reference_dev": _aggregate(reference_metrics["deadline"]),
            "requirement": "Reduce missed deadlines without more worked reviewer hours. Preserve qualifications and capacities."})
        try:
            repaired = await llm.generate(parent["brief"], SERVICE_R1, feedback=feedback,
                                          domain_review=domain_context_for_generation(rec, prop))
            previous_code, current_code = current_code, repaired.python_code
        except HTTPException as exc:
            attempts[-1]["repair_error"] = str(exc.detail)[:200]
            break
    held = None
    holdout_executed = False
    technical = False
    if selected is not None:
        holdout_data = {s: make_dataset(s) for s in holdout_seeds}
        try:
            holdout_runs = await asyncio.to_thread(run_in_e2b, holdout_data,
                {"fifo": fifo, "deadline": deadline, "generated": selected})
        except Exception as exc:
            store_failure(eid, "E2B HOLDOUT", exc)
            raise HTTPException(502, "E2B HOLDOUTに失敗: " + str(exc)[:240]) from exc
        store_raw_e2b("experiments", eid, "holdout", holdout_runs)
        held = _evaluate_e2b(holdout_runs, holdout_data)
        holdout_executed = True
        a,b = held["fifo"], held["generated"]
        technical = (all(x["valid"] for x in b) and all(y["valid"] for y in a)
                     and all(x["assigned_hours"] == y["assigned_hours"] for x,y in zip(b,a))
                     and all(x["missed_deadlines"] <= y["missed_deadlines"] for x,y in zip(b,a))
                     and any(x["missed_deadlines"] < y["missed_deadlines"] for x,y in zip(b,a)))
    result = {"experiment_id": eid, "approval_id": body.approval_id,
              "proposal_id": prop["proposal_id"], "r0_run_id": parent["run_id"],
              "created_at": now(), "contract_before": CONTRACT_R0, "contract_after": CONTRACT_R1,
              "original_r0_implementation_pass": True, "llm_diagnosis_pass": prop["diagnosis_matches_rubric"],
              "diagnostic_quality": {"qwen":prop.get("qwen_diagnostic_quality"), "oda":prop.get("oda_diagnostic_quality")},
              "finance_diagnosis_pass": prop["finance_diagnosis_matches_rubric"],
              "diagnostic_models": prop["model_comparison"],
              "dev_seeds": dev_seeds, "holdout_seeds": holdout_seeds if holdout_executed else [],
              "development_reference": {k: _aggregate(v) for k,v in reference_metrics.items()},
              "attempts": attempts, "selected_code_sha256": sha256(selected) if selected else None,
              "holdout": held, "holdout_executed": holdout_executed,
              "technical_closed_loop_demonstrated": bool(technical and prop["finance_diagnosis_matches_rubric"]),
              "human_adjudicated_r1_kpi_improvement_demonstrated": bool(technical and rec.get("domain_review_override")),
              "r1_independent_kpi_improvement_pass": bool(technical),
              "business_requirement_validity": "UNVERIFIED",
              "business_note": "Synthetic requirements counterexample and synthetic operational KPIs; customer acceptance, willingness to pay, GDPR/data processing unverified.",
              "audit": {"human_approval": rec, "evidence": prop["evidence"],
                        "finance_diagnosis_sha256":sha256(prop["finance_diagnosis"]),
                        "service_design_sha256": sha256(SERVICE_R1), "r0_source_sha256": sha256(fifo),
                        "r1_source_sha256": sha256(selected) if selected else None}}
    store("experiments", eid, "experiment.json", result)
    if selected:
        store("experiments", eid, "selected_r1.py", selected)
    store("experiments", eid, "report.md", report_r1(result, parent, prop))
    return {**result, "report_url": f"/api/experiments/{eid}/report"}


def report_r0(run: dict) -> str:
    def row(name: str, partition: str) -> str:
        m = run[partition][name]
        return f"|{partition} / {name}|{m['missed_total']}|{m['worked_hours_total']}|{m['deadline_hit_rate']}|{m['valid']}|"
    return f"""# Claims Operations Planner v0.10 — R0 実装検証

> **架空のドイツInsurTech顧客／合成請求データ**。期限超過KPIは実顧客実測ではありません。保険金支払判断・個人情報処理は対象外です。

- Run ID: `{run['run_id']}` / UTC: {run['created_at']}
- 顧客の相談: {run['brief']}
- 要件 `{CONTRACT_R0['id']}` / `{CONTRACT_R0['version']}`: {CONTRACT_R0['rule']}
- 要件の事業妥当性: **UNVERIFIED**、実装の正しさ: **PASS**
- DEV seeds: {run['dev_seeds']}; HOLDOUT seeds: {run['holdout_seeds']}（モデルに非開示）

| 分割/方式 | 期限超過合計 | 実働時間合計h | 期限内率 | 制約PASS |
|---|---:|---:|---:|---|
{row('fifo','development')}
{row('deadline','development')}
{row('fifo','holdout')}
{row('deadline','holdout')}

## サービス設計

```json
{json.dumps(run['service_design'],ensure_ascii=False,indent=2)}
```

## 判定の分離

- 実装の正しさ: FIFO仕様を独立決定的評価器が確認。
- 要件の正しさ: 顧客証拠は0件。期限超過を減らす要件かは未検証。
- 仮説: 計画された審査担当者の時間を増やさず、期限優先方式に改訂すれば期限超過が減る。
- 比較の限界: ケースの実処理時間、担当資格、顧客の期限設定を合成値で仮定。参照方式は厳密最適解ではない。

## 追跡可能性

`REQ-QUEUE-001` → `SERVICE-R0` → `fifo.py`（SHA256 `{run['seed_evidence']['fifo'][0]['source_sha256']}`） → deterministic evaluator.
"""


def report_r1(result: dict, parent: dict, proposal: dict) -> str:
    rows = []
    for name, metrics in (result["holdout"] or {}).items():
        ag = _aggregate(metrics)
        rows.append(f"|{name}|{ag['missed_total']}|{ag['worked_hours_total']}|{ag['deadline_hit_rate']}|{ag['valid']}|")
    changes = "\n".join(f"- {x}" for x in proposal["contract_delta"])
    attempt_rows = "\n".join(f"|{a['attempt']}|`{a['code_sha256'][:16]}`|{a['evaluation']['valid']}|{a['evaluation']['missed_total']}|" for a in result["attempts"])
    return f"""# Claims Operations Planner v0.10 — Requirement Refinement監査レポート

> **合成案件・模擬顧客の反例に基づく技術検証のみ**。顧客要件の現実的妥当性と実業務効果は未確認。

## 1. 要件の正しさと実装の正しさ

| 検証軸 | 結果 | 根拠 |
|---|---|---|
| R0実装の正しさ | PASS | FIFO独立評価／E2B |
| Qwen-Coder 要件診断（比較用） | {'PASS' if result['llm_diagnosis_pass'] else 'HOLD'} | R0 DEVと模擬証拠のみ |
| ODA-Fin-RL-8B 独立要件診断 | {'PASS' if result['finance_diagnosis_pass'] else 'HOLD'} | R0 DEVと模擬証拠のみ・独立ルーブリック |
| R1コードの独立技術評価 | {'PASS' if result['r1_independent_kpi_improvement_pass'] else 'HOLD/NO-GO'} | 新HOLDOUTでの共通KPIと制約 |
| 自動診断を含む外側ループ | {'PASS' if result['technical_closed_loop_demonstrated'] else 'HOLD'} | 要件診断品質ゲートとR1技術評価を分離 |
| 顧客要件の事業妥当性 | **UNVERIFIED** | 実顧客の承認・作業実測なし |

## 2. 顧客課題と仮説

{parent['brief']}

- 仮説: **予定審査稼働を増やさず、期限超過件数を削減できるか**。
- 固定するもの: 人員・日別容量・資格・案件の処理時間・顧客判断権限。
- 初期要件: `{CONTRACT_R0['version']}`: 到着順のFIFO。
- 改訂要件: `{CONTRACT_R1['version']}`: 期限・技能に応じた割当。
- 実顧客・実案件に対する外挿は不可。

## 3. 反証と独立要件改訂

- Evidence: `{proposal['evidence'][0]['evidence_id'] if proposal['evidence'] else 'none'}`（模擬データ）
- Qwen classification: `{proposal['diagnosis']['classification']}`
- ODA-Fin-RL model: `{proposal['model_comparison']['oda_fin_rl_8b']}`
- ODA classification: `{proposal['finance_diagnosis']['classification']}`
- ODA root cause: {proposal['finance_diagnosis']['root_cause']}
- ODA suggested change: {proposal['finance_diagnosis']['suggested_requirement_change']}
- ODA interpretation of R0 implementation: `{proposal['finance_diagnosis']['r0_implementation_assessment']}`
- ODA interpretation of business requirement: `{proposal['finance_diagnosis']['business_requirement_assessment']}`
- ODA evidence IDs: `{proposal['finance_diagnosis']['supporting_evidence_ids']}`
- ODA rubric failures: `{proposal['finance_diagnosis_rubric_failures']}`
- ODA independent diagnostic quality: `{json.dumps(proposal.get('oda_diagnostic_quality', {}), ensure_ascii=False)}`
- Qwen independent diagnostic quality: `{json.dumps(proposal.get('qwen_diagnostic_quality', {}), ensure_ascii=False)}`
- Synthetic evidence requirement fit: `{proposal.get('synthetic_requirement_fit', 'unverified')}`
- Real customer business validity: **UNVERIFIED**
- Model agreement: `{proposal['model_comparison']['classification_agreement']}`
- Qwen and ODA independently assessed the **same DEV and evidence**. Neither sees HOLDOUT nor the other's diagnostic answer.
- **The final R1 contract remains predeclared**, NOT produced or certified by ODA. It requires human approval; the model cannot modify the verifier.
- ODAの診断出力は承認後、QwenのR1生成・DEV修正プロンプトへ渡す。ただし**HOLD時は誤ったODA結論を渡さず、人間の審査記録と独立R0 PASSを参照**する（評価器は変更不可）。
- Qwenの理由: {proposal['diagnosis']['reasoning']}
- 改訂案: {proposal['diagnosis']['suggested_requirement_change']}

{changes}

### ドメインモデルの業務上の注意事項

- Tradeoffs: {json.dumps(proposal['finance_diagnosis']['business_tradeoffs'], ensure_ascii=False)}
- Regulatory questions needing primary-source verification: {json.dumps(proposal['finance_diagnosis']['compliance_questions'], ensure_ascii=False)}
- Uncertainty: {proposal['finance_diagnosis']['remaining_uncertainty']}
- このデモにはEU規制の外部検索機能はありません。Vertical FMの規制主張を根拠として承認しません。

## 4. 人間の承認・監査

- Actor: `{result['audit']['human_approval']['actor']}`
- Time: `{result['audit']['human_approval']['timestamp_utc']}`
- Rationale: {result['audit']['human_approval']['rationale']}
- Approval path: `{result['audit']['human_approval'].get('approval_path', 'rubric_pass_human_approved')}`
- ODA diagnostic at approval: `{result['audit']['human_approval'].get('original_oda_rubric_status', 'PASS')}` (never rewritten)
- Human override rationale: {result['audit']['human_approval'].get('override_rationale') or 'なし'}
- ODA rubric errors preserved: {result['audit']['human_approval'].get('original_oda_rubric_failures', [])}
- R0 contract hash: `{result['audit']['human_approval']['contract_r0_sha256']}`
- R1 contract hash: `{result['audit']['human_approval']['contract_r1_sha256']}`
- Service design hash: `{result['audit']['service_design_sha256']}`
- Generated code hash: `{result['selected_code_sha256']}`
- Parent run: `{parent['run_id']}` / Proposal: `{proposal['proposal_id']}` / Experiment: `{result['experiment_id']}`

## 5. 改訂コードの開発用評価

| Attempt | ソースSHA256 (先頭16文字) | 有効性 | 期限超過合計 |
|---:|---|---|---:|
{attempt_rows}

- DEV: `{result['dev_seeds']}`。Qwenに渡す修正指示はDEV由来のみ。
- HOLDOUT: `{result['holdout_seeds']}`。生成・選択後に一度だけ実行。失敗した結果を修正プロンプトに転用しない。

## 6. 同じHOLDOUT・共通KPIによるR0/R1比較

| 方式 | 期限超過合計 | 実働時間合計h | 期限内率 | 制約PASS |
|---|---:|---:|---:|---|
{chr(10).join(rows) or '|未実行|—|—|—|—|'}

- 期限優先の固定参照実装はヒューリスティックであり厳密最適化とは呼ばない。
- 生成候補が欠損案件を隠す行為は制約違反。実働時間が減るだけでも『同一稼働で改善』とは判定しない。
- 自動診断を含む外側ループ技術実証: **{result['technical_closed_loop_demonstrated']}**
- 人間のHOLD審査を経たR1技術KPI改善: **{result.get('human_adjudicated_r1_kpi_improvement_demonstrated', False)}**
- R1独立KPI改善（診断の適否とは別）: **{result.get('r1_independent_kpi_improvement_pass', False)}**
- 市場受容・価格受容・法務/GDPR・現地業務手順: **UNVERIFIED**

## 7. 事業開発の収益仮説（すべて未検証）

- SaaS追加機能料金: 月額 **EUR 2,500 / 顧客**（架空）
- パイロット契約: **4社**（仮定、成約実績はゼロ）
- 月間売上: 4 × EUR 2,500 = **EUR 10,000**
- 月間運用費: **EUR 6,000**（仮定）
- 単純な月間貢献: **EUR 4,000**。営業・CAC、実装、規制対応、税・契約費用を含まない。
- SLA期限超過の金銭価値は**未設定**。合成データ上の期限内率を金銭効果へ換算しない。
- 海外市場は開拓仮説であり、EU各国への販売可能性を確認したわけではない。

## 8. 監査ファイルの再取得

- `/api/history/experiments`：過去の実験一覧。
- `/api/artifacts/experiments/{result['experiment_id']}/bundle`：生成コード全試行・差分・E2B標準出力・評価JSON・要件診断・人間承認・比較Markdownを含む証跡ZIP。
- 失敗した生成・E2B実行も試行単位で記録（個別のSDK初期化エラーは `started.json` とともに検証が必要）。

## 9. 次の顧客検証

1. Claims Managerへ期限超過ペナルティとSLAの意味を確認。
2. 実測の案件所要時間・必要資格・到着分布を取得し分布ずれを検証。
3. 実案件の匿名化等の適法性、GDPR・委託関係を法務と確認。
4. 期限超過数、平均処理待ち時間、レビュー品質、残業、担当者負荷を実測。
5. 保険金の支払可否判断を一貫して人間に保持する。
"""


@app.get("/api/runs/{run_id}/report")
def download_r0(run_id: str):
    load("runs", run_id, "run.json")
    return FileResponse(path_for("runs", run_id)/"report.md", filename=f"claims_r0_{run_id}.md", media_type="text/markdown")


@app.get("/api/experiments/{experiment_id}/report")
def download_r1(experiment_id: str):
    load("experiments", experiment_id, "experiment.json")
    return FileResponse(path_for("experiments", experiment_id)/"report.md", filename=f"claims_r1_{experiment_id}.md", media_type="text/markdown")


class BenchmarkRequest(BaseModel):
    case_ids: list[Literal["fifo_sla_conflict", "correct_fifo_no_customer_evidence",
                           "actual_fifo_implementation_bug", "conflicting_stakeholder_notes"]] = Field(
            default_factory=lambda:["fifo_sla_conflict", "actual_fifo_implementation_bug"], min_length=1, max_length=4)
    repetitions: int = Field(default=1, ge=1, le=3)


@app.get("/api/diagnostic-benchmark/fixtures")
def benchmark_fixtures():
    return {"version":FIXTURE_VERSION,"cases":public_cases(),
            "note":"Synthetic fixtures: labels/oracles excluded from model input; not real insurance/legal evidence."}


def _benchmark_report(record: dict) -> str:
    lines = ["# Claims Operations Planner v0.10 — Diagnostic Benchmark", "",
        "> **合成フィクスチャの独立採点です。実顧客要件の正しさ・EU規制適合性を検証しません。**", "",
        f"- Benchmark ID: `{record['benchmark_id']}`", f"- Date: {record['created_at']}",
        f"- Fixtures: `{record['fixture_version']}` / Rubric: `{record['rubric_version']}`",
        f"- Cases: {', '.join(record['case_ids'])} / Repetitions: {record['repetitions']}",
        "- 両モデルは同じ入力・同じスキーマ・同じ推論パラメータです。出力・独立評価は別々に記録します。", "",
        "| Model | completed | overall rubric PASS | mean criterion score |", "|---|---:|---:|---:|"]
    for name, val in record['summary'].items():
        lines.append(f"|{name}|{val['completed']}|{val['passed']}|{val['mean_score']}|")
    lines += ["", "## Trial-level evidence", "",
              "| case | repetition | model | classification | result | score | failures |",
              "|---|---:|---|---|---|---:|---|"]
    for tr in record['trials']:
        evaluation=tr.get('rubric',{})
        pred=tr.get('diagnosis') or {}
        lines.append(f"|{tr['case_id']}|{tr['repetition']}|{tr['model_role']}|{pred.get('classification','—')}|{tr['status']}|{evaluation.get('score','—')}|{', '.join(evaluation.get('failure_codes',[])) or tr.get('error','—')}|")
    lines += ["", "## Interpretation", "", "- 分類だけでは合格しません。説明・改訂案・証拠ID・実装判定を独立採点します。",
              "- 同一アーキテクチャでもモデル差以外に量子化、ランダム性、応答形式の差が残ります。",
              "- 語句に基づく矛盾検出は限定的で、意味論的な証明ではありません。",
              "- 正解ラベルはモデル入力へ渡していません。市場と顧客による検証はUNVERIFIEDのままです。",
              "- 各試行の診断JSON、根拠、エラー、ハッシュは同梱証跡ZIPから取得できます。"]
    return "\n".join(lines) + "\n"


@app.post("/api/diagnostic-benchmark/run")
async def run_benchmark(body: BenchmarkRequest):
    """Bounded, reproducible synthetic benchmark; no live E2B, no external customer evidence."""
    bid=fresh_id()
    cases=list(dict.fromkeys(body.case_ids))
    versions={"coding":llm.MODEL, "finance":llm.FINANCE_MODEL}
    meta={"benchmark_id":bid,"created_at":now(),"fixture_version":FIXTURE_VERSION,
          "rubric_version":dq.RUBRIC_VERSION,"case_ids":cases,"repetitions":body.repetitions,
          "models":versions,"status":"RUNNING", "real_customer_validity":"UNVERIFIED"}
    store("benchmarks",bid,"started.json",meta)
    trials=[]
    for case in cases:
        fixture=FIXTURES[case]
        payload=fixture['input'] # oracle NEVER included in model context.
        for repeat in range(body.repetitions):
            # Sequential calls avoid loading Qwen and ODA simultaneously in unified memory.
            for role, model in versions.items():
                t0=time.perf_counter()
                tr={"case_id":case,"repetition":repeat,"model_role":role,"model_id":model,
                    "fixture_version":FIXTURE_VERSION,"prompt_input_sha256":sha256(payload),"status":"FAILED",
                    "real_customer_validity":"UNVERIFIED"}
                try:
                    response=await llm.benchmark_diagnosis(payload,model=model)
                    data=response.model_dump()
                    score=dq.benchmark_score(data, fixture['oracle'])
                    tr.update({"status":"COMPLETED","diagnosis":data,"rubric":score})
                except Exception as exc:
                    tr["error_type"]=type(exc).__name__
                    tr["error"]=str(getattr(exc,"detail",exc))[:600]
                tr["elapsed_seconds"]=round(time.perf_counter()-t0,2)
                tr["created_at"]=now()
                trials.append(tr)
                store("benchmarks",bid,f"trial_{len(trials):02d}_{role}_{case}.json",tr)
    summary={}
    for role in versions:
        subset=[t for t in trials if t['model_role']==role]
        good=[t for t in subset if t['status']=='COMPLETED']
        scores=[t['rubric']['score'] for t in good]
        summary[role]={"model":versions[role],"planned":len(subset),"completed":len(good),
                       "passed":sum(t['rubric']['passed'] for t in good),
                       "mean_score":round(statistics.mean(scores),4) if scores else None,
                       "failed_calls":len(subset)-len(good)}
    data={**meta,"status":"COMPLETED_WITH_ERRORS" if any(t['status']!='COMPLETED' for t in trials) else "COMPLETED",
          "summary":summary,"trials":trials,
          "methodology":"Same explicit schema, model-neutral prompt and exact synthetic fixture input; independent fixed oracle not included in prompt; no HOLDOUT disclosed.",
          "caveat":"Rule-based checks, no gold-standard EU customer requirement or regulatory validation."}
    store("benchmarks",bid,"benchmark.json",data)
    store("benchmarks",bid,"report.md",_benchmark_report(data))
    return data


@app.get("/api/diagnostic-benchmark/{benchmark_id}/report")
def benchmark_report(benchmark_id:str):
    load("benchmarks", benchmark_id,"benchmark.json")
    return FileResponse(path_for("benchmarks",benchmark_id)/"report.md",
                        filename=f"claims_diagnostic_benchmark_{benchmark_id}.md",media_type="text/markdown")


@app.get("/api/diagnostic-benchmark/rescore/{proposal_id}")
def rescore_existing_proposal(proposal_id:str):
    """Read-only regrading of v0.9.1 archived Qwen and ODA results."""
    p=load("proposals",proposal_id,"proposal.json")
    if not p.get('finance_diagnosis') or not p.get('diagnosis'):
        raise HTTPException(422,"Proposal lacks two stored diagnosis results")
    condition=p.get('condition','counterexample')
    return {"proposal_id":proposal_id,"rubric_version":dq.RUBRIC_VERSION,
            "qwen":dq.legacy_diagnostic_score(p['diagnosis'],condition=condition,is_vertical=False),
            "oda":dq.legacy_diagnostic_score(p['finance_diagnosis'],condition=condition,is_vertical=True),
            "original_oda_rubric_pass":p.get('finance_diagnosis_matches_rubric'),
            "historical_record_modified":False,"real_customer_business_validity":"UNVERIFIED"}
