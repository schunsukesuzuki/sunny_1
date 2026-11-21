"""User-initiated 01..09 batch orchestration with explicit human decision gate.

This workflow does not autonomously approve changes. Long-running tasks are run via
FastAPI BackgroundTasks; state is persisted after each step for polling and audit.
A saved ZIP exists at every terminal or human-review checkpoint. No real-world
validity or secure multi-tenant operation is claimed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Callable

from fastapi import BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Literal

from . import export_bundle as ex

# The endpoints are registered by register(app, main_module) to keep the
# existing 01..09 handlers as the single implementation of each operation.

STEP_ORDER = ["01_input", "02_service_design", "03_r0_e2b", "04_independent_diagnoses",
              "05_human_approval", "06_r1_generation_and_evaluation", "07_audit_index",
              "08_diagnostic_benchmark", "08b_policy_and_stress", "09_business_delivery_assessment"]
KINDS = ("runs", "proposals", "approvals", "experiments", "policy_validations", "benchmarks", "assessments", "workflows")

class FullRunStart(BaseModel):
    brief: str = Field(min_length=20, max_length=5000)
    seed: int = Field(default=42, ge=0, le=9999)
    evidence_condition: Literal["counterexample", "control"] = "counterexample"
    case_ids: list[Literal["fifo_sla_conflict", "correct_fifo_no_customer_evidence",
                           "actual_fifo_implementation_bug", "conflicting_stakeholder_notes"]] = Field(
        default_factory=lambda: ["fifo_sla_conflict", "actual_fifo_implementation_bug"],
        min_length=1, max_length=4)
    repetitions: int = Field(default=1, ge=1, le=3)

class FullRunReview(BaseModel):
    workflow_id: str
    approval: dict


def register(app, m) -> None:
    """No engine duplications: invoke the exact existing endpoints as functions."""
    def folder(wid: str) -> Path:
        return m.path_for("workflows", wid)

    def read(wid: str) -> dict:
        return m.load("workflows", wid, "workflow.json")

    def write(wid: str, state: dict) -> None:
        state["updated_at"] = m.now()
        target = folder(wid) / "workflow.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".json.tmp")
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, target)

    def step(state:dict, code:str, status:str, detail:str="") -> None:
        entries = {x["name"]:x for x in state["stages"]}
        entries[code] = {"name":code, "status":status, "detail":detail[:500]}
        state["stages"] = [entries[k] for k in STEP_ORDER if k in entries]
        write(state["workflow_id"], state)

    def add_file(wid: str, name:str, data:dict) -> None:
        # Append-only snapshots contain the exact inputs/output of 01 and 02.
        m.store("workflows", wid, name, data)

    def summarize(state:dict) -> dict:
        result = {key:state.get(key) for key in (
            "workflow_id", "export_id", "created_at", "updated_at", "status", "phase", "stages",
            "linked_ids", "error", "service_design")}
        if state["status"] == "AWAITING_APPROVAL" and state["linked_ids"].get("proposals"):
            prop = m.load("proposals",state["linked_ids"]["proposals"],"proposal.json")
            result["review"] = {"proposal_id":prop["proposal_id"],
                "oda_rubric_pass":bool(prop.get("finance_diagnosis_matches_rubric")),
                "oda_failures":prop.get("finance_diagnosis_rubric_failures",[]),
                "qwen_rubric_pass":bool(prop.get("diagnosis_matches_rubric")),
                "condition":prop.get("condition")}
        result["bundle_url"] = f"/api/full-run/{state['workflow_id']}/bundle" if state.get("bundle_ready") else None
        return result

    def save_archive(state: dict) -> None:
        """A single current archive. A waiting/failed archive is honestly PARTIAL."""
        wid = state["workflow_id"]
        export_id = state["export_id"]
        output = m.path_for("exports", export_id)
        output.mkdir(parents=True, exist_ok=True)
        manifest = ex.make_manifest(m.ARTIFACT_DIR, export_id, state["linked_ids"],
                                     state["stages"], state["created_at"])
        manifest["workflow_id"] = wid
        manifest["workflow_status"] = state["status"]
        manifest["expected_steps"] = STEP_ORDER
        manifest["completed_steps"] = [x["name"] for x in state["stages"] if x["status"] in ("COMPLETED", "COMPLETED_WITH_FINDINGS")]
        # Incomplete stages and absent stages must not be silently omitted.
        missing_steps = [x for x in STEP_ORDER if x not in manifest["completed_steps"]]
        manifest["pending_or_failed_steps"] = missing_steps
        if missing_steps or state["status"] != "COMPLETE":
            manifest["status"] = "PARTIAL"
        else:
            manifest["status"] = "PARTIAL" if manifest["missing"] or manifest["skipped"] else "COMPLETE"
        state["bundle_status"] = manifest["status"]
        state["bundle_ready"] = True
        write(wid, state)
        # regenerate to include the most recent workflow.json
        manifest = ex.make_manifest(m.ARTIFACT_DIR, export_id, state["linked_ids"],
                                     state["stages"], state["created_at"])
        manifest.update({"workflow_id":wid, "workflow_status":state["status"],
                         "expected_steps":STEP_ORDER,
                         "completed_steps":[x["name"] for x in state["stages"] if x["status"] in ("COMPLETED", "COMPLETED_WITH_FINDINGS")],
                         "pending_or_failed_steps":missing_steps,
                         "status":state["bundle_status"]})
        report = None
        if state["linked_ids"].get("assessments"):
            report = m.load("assessments", state["linked_ids"]["assessments"], "assessment.json")
        tmp = output / "bundle.tmp"
        ex.package(m.ARTIFACT_DIR, tmp, manifest, report)
        os.replace(tmp, output / "complete_audit_package.zip")
        (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2),encoding="utf-8")

    def fail(state:dict, name:str, exc:Exception) -> None:
        msg = f"{type(exc).__name__}: {str(getattr(exc, 'detail', exc))[:500]}"
        state["status"] = "PARTIAL"
        state["phase"] = name
        state["error"] = msg
        step(state, name, "FAILED", msg)
        write(state["workflow_id"],state)
        save_archive(state)

    async def first_half(wid: str) -> None:
        state=read(wid)
        inp=FullRunStart(**state["inputs"])
        current = "02_service_design"
        try:
            designed=await m.design(m.DesignRequest(brief=inp.brief,version="r0"))
            state["service_design"] = designed["service_design"]
            add_file(wid,"02_service_design.json",designed)
            step(state,current,"COMPLETED", "Qwen draft; not customer-approved")
            current = "03_r0_e2b"
            r0=await m.run_r0(m.R0Request(brief=inp.brief,seed=inp.seed,service_design=designed["service_design"],workflow_id=wid))
            state["linked_ids"]["runs"]=r0["run_id"]
            step(state,current,"COMPLETED", r0["implementation_validity"])
            current = "04_independent_diagnoses"
            prop=await m.propose(m.ProposeRequest(r0_run_id=r0["run_id"], evidence_condition=inp.evidence_condition,workflow_id=wid))
            state["linked_ids"]["proposals"]=prop["proposal_id"]
            step(state,current,"COMPLETED_WITH_FINDINGS", "ODA rubric: " + ("PASS" if prop.get("finance_diagnosis_matches_rubric") else "HOLD"))
            state["status"] = "AWAITING_APPROVAL"
            state["phase"] = "05_human_approval"
            step(state,"05_human_approval","WAITING_HUMAN","Review 04 diagnoses, then explicitly approve or reject. Never automatic.")
            save_archive(state)
        except Exception as exc:
            # Link failed R0/proposal snapshots as well; no success is inferred.
            for marker, kind, key in (("03_r0_started.json","runs","run_id"),
                                      ("04_proposal_started.json","proposals","proposal_id")):
                file=folder(wid)/marker
                if file.is_file() and not state["linked_ids"].get(kind):
                    state["linked_ids"][kind]=json.loads(file.read_text())[key]
            fail(state,current,exc)

    def snapshot_index(state:dict) -> None:
        wid=state["workflow_id"]
        inventory={}
        for kind,ident in state["linked_ids"].items():
            if not ident or kind=="workflows": continue
            d=m.path_for(kind,ident)
            inventory[kind] = {"artifact_id":ident, "files":sorted(f.name for f in d.iterdir() if f.is_file()) if d.exists() else []}
        target=folder(wid)/"07_history_snapshot.json"
        temp=target.with_suffix(".json.tmp")
        temp.write_text(json.dumps({"created_at":m.now(),"linked_artifacts":inventory},ensure_ascii=False,indent=2),encoding="utf-8")
        os.replace(temp,target)

    async def second_half(wid:str) -> None:
        state=read(wid)
        inp=FullRunStart(**state["inputs"])
        try:
            current="06_r1_generation_and_evaluation"
            try:
                generated=await m.generate_r1(m.GenerateRequest(approval_id=state["linked_ids"]["approvals"]))
                # generated source is recorded in approvals/*.py by existing endpoint.
                exp=await m.evaluate_r1(m.EvaluateRequest(approval_id=state["linked_ids"]["approvals"],
                    python_code=generated["python_code"],max_repairs=2))
                state["linked_ids"]["experiments"]=exp["experiment_id"]
                step(state,current,"COMPLETED_WITH_FINDINGS","KPI/HOLDOUT outcome: "+str(exp.get("r1_independent_kpi_improvement_pass")))
            except Exception as exc:
                # Preserve partial experiment if evaluation was started and has artifacts.
                p=folder(wid)
                approval_folder=m.path_for("approvals",state["linked_ids"]["approvals"])
                marker=approval_folder/"evaluation_started.json"
                if marker.is_file():
                    state["linked_ids"]["experiments"] = json.loads(marker.read_text())["experiment_id"]
                msg=f"{type(exc).__name__}: {str(getattr(exc,'detail',exc))[:400]}"
                step(state,current,"FAILED",msg)
            current="07_audit_index"
            snapshot_index(state)
            step(state,current,"COMPLETED","saved evidence index; archived records retrievable by 07")
            current="08_diagnostic_benchmark"
            try:
                bench=await m.run_benchmark(m.BenchmarkRequest(case_ids=inp.case_ids,repetitions=inp.repetitions,workflow_id=wid))
                state["linked_ids"]["benchmarks"]=bench["benchmark_id"]
                st="COMPLETED_WITH_FINDINGS" if bench["status"]=="COMPLETED" else "FAILED"
                step(state,current,st,"summary counts are evidence, not model reliability")
            except Exception as exc:
                marker=folder(wid)/"08_benchmark_started.json"
                if marker.is_file():
                    state["linked_ids"]["benchmarks"]=json.loads(marker.read_text())["benchmark_id"]
                step(state,current,"FAILED",f"{type(exc).__name__}: {str(exc)[:400]}")
            current="08b_policy_and_stress"
            if state["linked_ids"].get("experiments"):
                try:
                    policy=await m.run_policy_validation(m.PolicyValidationRequest(experiment_id=state["linked_ids"]["experiments"],workflow_id=wid))
                    state["linked_ids"]["policy_validations"]=policy["validation_id"]
                    st="COMPLETED_WITH_FINDINGS" if policy["status"]=="COMPLETED" else "FAILED"
                    step(state,current,st,"R1 behavioral + stress evaluation")
                except Exception as exc:
                    marker=folder(wid)/"08b_policy_started.json"
                    if marker.is_file():
                        state["linked_ids"]["policy_validations"]=json.loads(marker.read_text())["validation_id"]
                    step(state,current,"FAILED",f"{type(exc).__name__}: {str(exc)[:400]}")
            else:
                step(state,current,"SKIPPED","No R1 experiment")
            current="09_business_delivery_assessment"
            if state["linked_ids"].get("experiments"):
                try:
                    assess=m.generate_business_assessment(m.BusinessAssessmentRequest(
                        experiment_id=state["linked_ids"]["experiments"],
                        policy_validation_id=state["linked_ids"].get("policy_validations")
                          if any(x["name"]=="08b_policy_and_stress" and x["status"]=="COMPLETED_WITH_FINDINGS" for x in state["stages"]) else None,
                        benchmark_id=state["linked_ids"].get("benchmarks")))
                    state["linked_ids"]["assessments"]=assess["assessment_id"]
                    step(state,current,"COMPLETED_WITH_FINDINGS", "Production remains NO-GO")
                except Exception as exc:
                    marker=folder(wid)/"08b_policy_started.json"
                    if marker.is_file():
                        state["linked_ids"]["policy_validations"]=json.loads(marker.read_text())["validation_id"]
                    step(state,current,"FAILED",f"{type(exc).__name__}: {str(exc)[:400]}")
            else:
                step(state,current,"SKIPPED","No R1 experiment")
            snapshot_index(state)
            all_good=all(any(x["name"]==name and x["status"] in ("COMPLETED", "COMPLETED_WITH_FINDINGS")
                    for x in state["stages"]) for name in STEP_ORDER)
            state["status"]="COMPLETE" if all_good else "PARTIAL"
            state["phase"]="DONE"
            write(wid,state)
            save_archive(state)
        except Exception as exc:
            fail(state,current,exc)

    @app.post("/api/full-run/start")
    async def full_run_start(body: FullRunStart, background_tasks:BackgroundTasks):
        wid, export_id=m.fresh_id(), m.fresh_id()
        record={"workflow_id":wid,"export_id":export_id,"created_at":m.now(),
            "updated_at":m.now(),"version":"0.15.0","status":"RUNNING","phase":"02_service_design",
            "inputs":body.model_dump(),"service_design":None,"linked_ids":{k:None for k in KINDS},
            "stages":[],"bundle_ready":False}
        record["linked_ids"]["workflows"]=wid
        write(wid,record)
        add_file(wid,"01_input.json",body.model_dump())
        step(record,"01_input","COMPLETED","user-supplied synthetic scenario; no customer validation")
        background_tasks.add_task(first_half,wid)
        return summarize(record)

    @app.post("/api/full-run/approve-and-continue")
    async def full_run_review(body:FullRunReview, background_tasks:BackgroundTasks):
        state=read(body.workflow_id)
        if state["status"]!="AWAITING_APPROVAL":
            raise HTTPException(409,"Human review is not pending for this workflow")
        payload=dict(body.approval)
        if payload.get("proposal_id")!=state["linked_ids"]["proposals"]:
            raise HTTPException(409,"Approval does not belong to the pending workflow")
        # All business/domain safeguards from step 05 apply unchanged.
        approval=m.approve(m.ApprovalRequest(**payload))
        state["linked_ids"]["approvals"]=approval["approval_id"]
        step(state,"05_human_approval","COMPLETED" if approval["decision"]=="approved" else "REJECTED",
             "explicit human decision; original ODA HOLD remains preserved")
        if approval["decision"]!="approved":
            state["status"]="PARTIAL"
            state["phase"]="REJECTED_BY_HUMAN"
            write(body.workflow_id,state)
            save_archive(state)
        else:
            state["status"]="RUNNING"
            state["phase"]="06_r1_generation_and_evaluation"
            write(body.workflow_id,state)
            background_tasks.add_task(second_half,body.workflow_id)
        return summarize(state)

    @app.get("/api/full-run/{workflow_id}")
    def full_run_status(workflow_id:str):
        return summarize(read(workflow_id))

    @app.get("/api/full-run/{workflow_id}/bundle")
    def full_run_bundle(workflow_id:str):
        state=read(workflow_id)
        file=m.path_for("exports",state["export_id"])/"complete_audit_package.zip"
        if not file.is_file():
            raise HTTPException(409,"ZIP is not ready; check workflow status")
        return FileResponse(file,filename=f"claims_full_run_v015_{workflow_id}.zip",media_type="application/zip")

