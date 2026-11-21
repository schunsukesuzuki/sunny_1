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
from . import grounded_contract as gc
from . import requirement_trace as rt
from . import notification_demo as nd
from . import blind_optimality as bo
from . import artifact_readiness as ar

# The endpoints are registered by register(app, main_module) to keep the
# existing 01..09 handlers as the single implementation of each operation.

STEP_ORDER = ["00_evidence_grounded_requirements", "00b_evidence_review", "00c_grounded_test_contract", "01_input", "02_service_design", "03_r0_e2b", "04_independent_diagnoses",
              "05_human_approval", "06_r1_generation_and_evaluation", "07_audit_index",
              "08_diagnostic_benchmark", "08b_policy_and_stress", "08c_grounded_kpi_verification", "08d_notification_prototype", "08e_requirement_trace", "08f_blind_optimality", "09_business_delivery_assessment"]
KINDS = ("runs", "proposals", "approvals", "experiments", "policy_validations", "benchmarks", "assessments", "workflows")

class FullRunStart(BaseModel):
    # The user must choose deliberately; no silent public-to-synthetic fallback.
    evidence_mode: Literal["public", "synthetic"]
    r1_mode: Literal["llm_only", "skill_only", "compare"] = "compare"
    diagnostic_repair: bool = False  # Default keeps earlier API/fixture tests comparable.
    blind_case_count: int = Field(default=4,ge=2,le=8)
    diagnostic_blind_cases: bool = False
    dataset_id: Literal["community_credit", "cfpb_sample", "insurance_claims_uk"] = "insurance_claims_uk"
    evidence_query: str = Field(default="insurance claim delays complaints handling", min_length=3, max_length=500)
    llm_extraction: bool = False
    brief: str = Field(min_length=20, max_length=5000)
    seed: int = Field(default=42, ge=0, le=9999)
    evidence_condition: Literal["counterexample", "control"] = "counterexample"
    case_ids: list[Literal["fifo_sla_conflict", "correct_fifo_no_customer_evidence",
                           "actual_fifo_implementation_bug", "conflicting_stakeholder_notes"]] = Field(
        default_factory=lambda: ["fifo_sla_conflict", "actual_fifo_implementation_bug"],
        min_length=1, max_length=4)
    repetitions: int = Field(default=1, ge=1, le=3)

class FullRunEvidenceReview(BaseModel):
    workflow_id: str
    decision: Literal["approved", "rejected"]
    actor: str = Field(min_length=2, max_length=100)
    rationale: str = Field(min_length=10, max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=6)
    approved_requirement: str | None = Field(default=None, max_length=1200)
    support_assessment: Literal["supports_problem", "context_only", "contradicts"] = "context_only"
    max_total_missed: int = Field(default=0, ge=0, le=100)
    min_reduction_pct: int = Field(default=50, ge=0, le=100)
    require_behavioral: bool = True
    requirement_type: Literal['claims_assignment','claim_progress_updates'] = 'claims_assignment'
    max_notification_delay_hours: int = Field(default=24, ge=1, le=168)
    min_notification_coverage_pct: int = Field(default=100, ge=1, le=100)


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

    def check_experiment(state: dict, stage: str) -> dict:
        """Independently inspect R1 artifacts before any downstream consumer.

        The probe is read-only; a linked ID or started marker never implies a
        successful evaluation. Stage-specific snapshots stay in the audit ZIP.
        """
        audit = ar.inspect_experiment(m.ARTIFACT_DIR, state["linked_ids"].get("experiments"))
        add_file(state["workflow_id"], f"{stage}_experiment_dependency.json", ar.public_view(audit))
        return audit

    def required_steps(state: dict) -> list[str]:
        return STEP_ORDER if state["inputs"].get("evidence_mode") == "public" else [x for x in STEP_ORDER if x not in ("00_evidence_grounded_requirements", "00b_evidence_review", "00c_grounded_test_contract", "08c_grounded_kpi_verification", "08d_notification_prototype", "08e_requirement_trace")]

    def summarize(state:dict) -> dict:
        result = {key:state.get(key) for key in (
            "workflow_id", "export_id", "created_at", "updated_at", "status", "phase", "stages",
            "linked_ids", "error", "service_design", "evidence_mode", "r1_mode", "topic_alignment", "grounded_contract_status", "requirement_type", "requirement_trace_status")}
        blind_file=folder(state['workflow_id'])/'08f_blind_optimality.json'
        if blind_file.exists():
            result['blind_optimality']=json.loads(blind_file.read_text(encoding='utf-8'))
        if state["status"] == "AWAITING_EVIDENCE_REVIEW":
            rag = m.load("workflows", state["workflow_id"], "00_evidence_grounded_requirements.json")
            result["evidence_review"] = {
                "rag_id": rag["rag_id"], "dataset_id": rag["dataset_id"], "query": rag["query"],
                "evidence": rag["evidence"], "requirement_candidates": rag["requirement_candidates"],
                "llm_suggestions": rag.get("llm_suggestions", []), "evaluation": rag["evaluation"],
                "topic_alignment":rag.get("topic_alignment"),
                "available_requirement_templates":rt.TEMPLATES,
                "notice": "Topic match is a lexical screening, NOT proof of evidence supporting a requirement or of FIFO causality."
            }
        if state["status"] == "AWAITING_APPROVAL" and state["linked_ids"].get("proposals"):
            prop = m.load("proposals",state["linked_ids"]["proposals"],"proposal.json")
            result["review"] = {"proposal_id":prop["proposal_id"],
                "oda_rubric_pass":bool(prop.get("finance_diagnosis_matches_rubric")),
                "oda_failures":prop.get("finance_diagnosis_rubric_failures",[]),
                "qwen_rubric_pass":bool(prop.get("diagnosis_matches_rubric")),
                "condition":prop.get("condition")}
        result["bundle_url"] = f"/api/full-run/{state['workflow_id']}/bundle" if state.get("bundle_ready") else None
        return result

    def provenance_summary(state:dict) -> dict:
        statuses={x['name']:x['status'] for x in state['stages']}
        return {
            'evidence_mode': state['inputs'].get('evidence_mode'),
            'r1_mode':state['inputs'].get('r1_mode'),
            'dataset_id': state['inputs'].get('dataset_id') if state['inputs'].get('evidence_mode')=='public' else None,
            'rag_id': state.get('rag_id'),
            'retrieval_status': statuses.get('00_evidence_grounded_requirements', 'NOT_STARTED'),
            'review_status': statuses.get('00b_evidence_review', 'NOT_STARTED'),
            'requirement_type': state.get('requirement_type'),
            'feature_acceptance':state.get('requirement_trace_status','NOT_RUN'),
            'semantic_support': 'UNVERIFIED',
            'real_customer_approval': 'NOT_OBTAINED',
        }

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
        manifest["evidence_provenance"] = provenance_summary(state)
        manifest["expected_steps"] = required_steps(state)
        manifest["excluded_steps"] = {"00_evidence_grounded_requirements": "User explicitly selected synthetic mode", "00b_evidence_review": "Not applicable to synthetic mode", "00c_grounded_test_contract":"Not applicable to synthetic mode", "08c_grounded_kpi_verification":"Not applicable to synthetic mode", "08d_notification_prototype":"Not applicable to synthetic mode", "08e_requirement_trace":"Not applicable to synthetic mode"} if state["inputs"].get("evidence_mode") == "synthetic" else {}
        manifest["completed_steps"] = [x["name"] for x in state["stages"] if x["status"] in ("COMPLETED", "COMPLETED_WITH_FINDINGS")]
        # Incomplete stages and absent stages must not be silently omitted.
        missing_steps = [x for x in required_steps(state) if x not in manifest["completed_steps"]]
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
                         "evidence_provenance":provenance_summary(state),
                         "expected_steps":required_steps(state),
                         "excluded_steps":({"00_evidence_grounded_requirements": "User explicitly selected synthetic mode", "00b_evidence_review": "Not applicable to synthetic mode", "00c_grounded_test_contract":"Not applicable to synthetic mode", "08c_grounded_kpi_verification":"Not applicable to synthetic mode", "08d_notification_prototype":"Not applicable to synthetic mode", "08e_requirement_trace":"Not applicable to synthetic mode"} if state["inputs"].get("evidence_mode") == "synthetic" else {}),
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
            active_brief=state.get("execution_brief", inp.brief)
            designed=await m.design(m.DesignRequest(brief=active_brief,version="r0"))
            state["service_design"] = designed["service_design"]
            add_file(wid,"02_service_design.json",designed)
            step(state,current,"COMPLETED", "Qwen draft; not customer-approved")
            current = "03_r0_e2b"
            r0=await m.run_r0(m.R0Request(brief=active_brief,seed=inp.seed,service_design=designed["service_design"],workflow_id=wid))
            state["linked_ids"]["runs"]=r0["run_id"]
            step(state,current,"COMPLETED", r0["implementation_validity"])
            current = "04_independent_diagnoses"
            prop=await m.propose(m.ProposeRequest(r0_run_id=r0["run_id"], evidence_condition=inp.evidence_condition,workflow_id=wid,
                                      enable_repair=inp.diagnostic_repair))
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
                if inp.r1_mode == 'skill_only':
                    generated={'python_code':'','rationale':'Pinned Domain Skill, no LLM R1 code generation'}
                else:
                    generated=await m.generate_r1(m.GenerateRequest(approval_id=state["linked_ids"]["approvals"]))
                # LLM source is saved only in modes that actually generate it.
                exp=await m.evaluate_r1(m.EvaluateRequest(approval_id=state["linked_ids"]["approvals"],
                    python_code=generated["python_code"],max_repairs=2,r1_mode=inp.r1_mode))
                state["linked_ids"]["experiments"]=exp["experiment_id"]
                probe=check_experiment(state,"06")
                if not ar.record_is_complete(probe):
                    state["error"] = "06 R1成果物が不完全: " + probe['status'] + ": " + probe['reason']
                    step(state,current,"FAILED", "Experiment returned but artifact integrity is " + probe['status'] + ": " + probe['reason'])
                else:
                    step(state,current,"COMPLETED_WITH_FINDINGS",
                        "R1 mode: "+inp.r1_mode+"; selected: "+str(exp.get('selected_engine'))+
                        "; KPI/HOLDOUT: "+str(exp.get("r1_independent_kpi_improvement_pass")))
            except Exception as exc:
                # Preserve partial experiment ID as a pointer, not a completion claim.
                marker=folder(wid)/"06_unused_marker.json"
                try:
                    marker=m.path_for("approvals",state["linked_ids"]["approvals"])/"evaluation_started.json"
                    if marker.is_file():
                        raw_marker=json.loads(marker.read_text(encoding="utf-8"))
                        state["linked_ids"]["experiments"]=raw_marker.get("experiment_id")
                except (ValueError, OSError, TypeError, KeyError) as marker_exc:
                    add_file(wid,"06_marker_read_error.json",{"error_type":type(marker_exc).__name__,"message":str(marker_exc)[:300]})
                probe=check_experiment(state,"06")
                msg=f"{type(exc).__name__}: {str(getattr(exc,'detail',exc))[:400]}"
                state["error"]="06 R1実験失敗: " + msg + "; artifact=" + probe['status']
                add_file(wid,"06_r1_failure.json",{"status":"FAILED","error_type":type(exc).__name__,
                    "detail":str(getattr(exc,'detail',exc))[:1000],
                    "artifact_readiness":ar.public_view(probe),
                    "note":"Upstream R1 failed; downstream evaluators must not consume a started marker as an experiment result."})
                step(state,current,"FAILED",msg + "; artifact=" + probe['status'])
            current="07_audit_index"
            snapshot_index(state)
            step(state,current,"COMPLETED","saved evidence index; archived records retrievable by 07")
            current="08_diagnostic_benchmark"
            try:
                bench=await m.run_benchmark(m.BenchmarkRequest(case_ids=inp.case_ids,repetitions=inp.repetitions,workflow_id=wid,
                    enable_repair=inp.diagnostic_repair,
                    blind_generalization=inp.diagnostic_blind_cases))
                state["linked_ids"]["benchmarks"]=bench["benchmark_id"]
                st="COMPLETED_WITH_FINDINGS" if bench["status"]=="COMPLETED" else "FAILED"
                step(state,current,st,"summary counts are evidence, not model reliability")
            except Exception as exc:
                marker=folder(wid)/"08_benchmark_started.json"
                if marker.is_file():
                    state["linked_ids"]["benchmarks"]=json.loads(marker.read_text())["benchmark_id"]
                step(state,current,"FAILED",f"{type(exc).__name__}: {str(exc)[:400]}")
            current="08b_policy_and_stress"
            policy_input=check_experiment(state,"08b")
            if ar.ready_for_policy(policy_input):
                try:
                    policy=await m.run_policy_validation(m.PolicyValidationRequest(experiment_id=state["linked_ids"]["experiments"],workflow_id=wid))
                    state["linked_ids"]["policy_validations"]=policy["validation_id"]
                    st="COMPLETED_WITH_FINDINGS" if policy["status"]=="COMPLETED" else "FAILED"
                    step(state,current,st,"R1 behavioral + stress evaluation")
                except Exception as exc:
                    marker=folder(wid)/"08b_policy_started.json"
                    try:
                        if marker.is_file():
                            state["linked_ids"]["policy_validations"]=json.loads(marker.read_text(encoding="utf-8"))["validation_id"]
                    except (ValueError, OSError, TypeError, KeyError):
                        pass
                    add_file(wid,"08b_policy_failure.json",{"error_type":type(exc).__name__,
                          "detail":str(getattr(exc,'detail',exc))[:600], "experiment_id":state["linked_ids"].get("experiments")})
                    step(state,current,"FAILED",f"{type(exc).__name__}: {str(getattr(exc,'detail',exc))[:400]}")
            else:
                add_file(wid,"08b_policy_skip.json",{"status":"SKIPPED_UPSTREAM_DEPENDENCY",
                    "artifact_readiness":ar.public_view(policy_input),
                    "policy_executed":False,"technical_pass":False,
                    "reason":"No verified selected R1. Do not claim post-selection behavioral verification."})
                step(state,current,"SKIPPED", "06 R1 dependency: " + policy_input['status'] + "; " + policy_input['reason'])
            if inp.evidence_mode=="public":
                current="08c_grounded_kpi_verification"
                try:
                    contract=m.load("workflows",wid,"00c_grounded_test_contract.json")
                    dependency=check_experiment(state,"08c")
                    if state.get('requirement_type')==rt.NOTIFICATION:
                        evaluation={'status':'NOT_APPLICABLE_TO_NOTIFICATION', 'synthetic_pass':False,
                           'reason':'R1 is reviewer assignment and cannot satisfy the claim-progress-update feature',
                           'comparison_only':'Unrelated fixed claims-assignment regression'}
                    elif not ar.record_is_complete(dependency):
                        evaluation={'status':'HOLD_UPSTREAM_R1_INCOMPLETE','synthetic_pass':False,
                                    'reason':'06 experiment unavailable: '+dependency['status'],
                                    'dependency':ar.public_view(dependency)}
                    else:
                        exp_record=dependency['record']
                        pol_record=None
                        policy_id=state["linked_ids"].get("policy_validations")
                        if policy_id and ar.ready_for_policy(dependency):
                            p=m.path_for("policy_validations",policy_id)/"validation.json"
                            if p.is_file():
                                pol_record=m.load("policy_validations",policy_id,"validation.json")
                        evaluation=gc.evaluate(contract,exp_record,pol_record)
                    add_file(wid,"08c_grounded_kpi_verification.json",evaluation)
                    state["grounded_contract_status"]=evaluation["status"]
                    st='SKIPPED' if evaluation['status']=='HOLD_UPSTREAM_R1_INCOMPLETE' else 'COMPLETED_WITH_FINDINGS'
                    step(state,current,st,"Typed assignment gate: "+evaluation["status"])
                except Exception as exc:
                    state["grounded_contract_status"]="HOLD"
                    step(state,current,"FAILED",f"{type(exc).__name__}: {str(exc)[:400]}")
                current='08d_notification_prototype'
                if state.get('requirement_type')==rt.NOTIFICATION:
                    try:
                        trace=m.load('workflows',wid,'00c_requirement_trace.json')
                        thresholds=trace['notification_thresholds']
                        notif=nd.evaluate_prototype(max_delay_hours=thresholds['max_delay_hours'],
                                                   min_coverage_pct=thresholds['min_coverage_pct'])
                        add_file(wid,'08d_notification_prototype.json',notif)
                        step(state,current,'COMPLETED_WITH_FINDINGS',notif['status']+'; deterministic example only, not R1')
                    except Exception as exc:
                        step(state,current,'FAILED',f"{type(exc).__name__}: {str(exc)[:400]}")
                else:
                    step(state,current,'COMPLETED_WITH_FINDINGS','Assignment requirement: notification feature not applicable')
                current='08e_requirement_trace'
                try:
                    trace=m.load('workflows',wid,'00c_requirement_trace.json')
                    assignment=m.load('workflows',wid,'08c_grounded_kpi_verification.json') if trace['type']==rt.ASSIGNMENT and (folder(wid)/'08c_grounded_kpi_verification.json').exists() else None
                    notification=m.load('workflows',wid,'08d_notification_prototype.json') if trace['type']==rt.NOTIFICATION and (folder(wid)/'08d_notification_prototype.json').exists() else None
                    traced=rt.trace_evaluation(trace,assignment_result=assignment,notification_result=notification)
                    add_file(wid,'08e_requirement_trace.json',traced)
                    (folder(wid)/'08e_requirement_trace.md').write_text(rt.markdown(trace,traced),encoding='utf-8')
                    state['requirement_trace_status']=traced['trace_status']
                    step(state,current,'COMPLETED_WITH_FINDINGS',traced['trace_status']+'; customer not approved')
                except Exception as exc:
                    step(state,current,'FAILED',f"{type(exc).__name__}: {str(exc)[:400]}")
            current="08f_blind_optimality"
            try:
                dependency=check_experiment(state,"08f")
                eid=state['linked_ids'].get('experiments')
                if not ar.ready_for_policy(dependency):
                    add_file(wid,'08f_blind_optimality.json',{'status':'HOLD_DEPENDENCY_NOT_READY',
                        'reason':'Independent blind comparison was not executed',
                        'dependency':ar.public_view(dependency), 'solver_executed':False, 'holdout_executed':False})
                    step(state,current,'SKIPPED','No verified R1 for blind comparison: '+dependency['status'])
                else:
                    exp_record=dependency['record']
                    selected_file=m.path_for('experiments',eid)/'selected_r1.py'
                    root_seed=bo.fresh_blind_seed()  # chosen AFTER candidate selection
                    suite=bo.randomized_suite(root_seed,inp.blind_case_count)
                    baseline={s:bo.exact_baseline(ds) for s,ds in suite.items()}
                    from .domain import get_reference_sources
                    fifo_source,deadline_source=get_reference_sources()
                    from skills.claims_allocation import bundle as allocation_skill
                    sources={'fifo':fifo_source,'deadline':deadline_source,
                             'selected':selected_file.read_text(encoding='utf-8'),
                             'skill_deadline_scarcity':allocation_skill.sandbox_source('deadline_scarcity'),
                             'skill_bounded_beam':allocation_skill.sandbox_source('bounded_beam')}
                    import asyncio
                    raw=await asyncio.to_thread(m.run_in_e2b,suite,sources)
                    metrics=bo.summarize(suite,raw,baseline)
                    for seed,ds in suite.items():
                        add_file(wid,f'08f_dataset_{seed}.json',ds)
                        opt=baseline[seed].copy()
                        add_file(wid,f'08f_exact_{seed}.json',opt)
                    m.store_raw_e2b('workflows',wid,'08f_raw',raw)
                    report={'version':bo.VERSION,'status':'COMPLETED_WITH_FINDINGS',
                           'seed_root':root_seed,'suite_size':len(suite),
                           'post_selection_only':True,'used_for_generation':False,
                           'used_for_selection':False,'selected_engine':exp_record.get('selected_engine'),
                           'solver_status':{str(s):x['status'] for s,x in baseline.items()},
                           'metrics':metrics,
                           'scope':'Small randomized synthetic cases only. Gap certified only when exact solver returned OPTIMAL.',
                           'cp_sat_optional':True,'no_performance_guarantee':True}
                    add_file(wid,'08f_blind_optimality.json',report)
                    step(state,current,'COMPLETED_WITH_FINDINGS',
                         'Post-selection blind synthetic benchmark; solver status and gaps saved')
            except Exception as exc:
                step(state,current,'FAILED',f'{type(exc).__name__}: {str(exc)[:400]}')
            current="09_business_delivery_assessment"
            assessment_input=check_experiment(state,"09")
            if ar.record_is_complete(assessment_input):
                try:
                    bid=state["linked_ids"].get("benchmarks")
                    benchmark_path=m.path_for('benchmarks',bid)/'benchmark.json' if bid else None
                    if not (benchmark_path and benchmark_path.is_file()):
                        bid=None
                    assess=m.generate_business_assessment(m.BusinessAssessmentRequest(
                        experiment_id=state["linked_ids"]["experiments"],
                        policy_validation_id=state["linked_ids"].get("policy_validations")
                          if any(x["name"]=="08b_policy_and_stress" and x["status"]=="COMPLETED_WITH_FINDINGS" for x in state["stages"]) else None,
                        benchmark_id=bid))
                    if inp.evidence_mode=="public":
                        result=m.load("assessments",assess["assessment_id"],"assessment.json")
                        aligned=state.get("topic_alignment",{})
                        contract_eval=m.load("workflows",wid,"08c_grounded_kpi_verification.json") if (folder(wid)/"08c_grounded_kpi_verification.json").exists() else None
                        trace=m.load('workflows',wid,'00c_requirement_trace.json')
                        trace_verification=(m.load('workflows',wid,'08e_requirement_trace.json')
                            if (folder(wid)/'08e_requirement_trace.json').exists() else None)
                        result['requirement_trace']={'mapping':trace,'evaluation':trace_verification}
                        result["public_evidence_context"]={"dataset_id":inp.dataset_id,"rag_id":state.get("rag_id"),"topic_alignment":aligned,
                            "grounded_contract_evaluation":contract_eval,"customer_validation":"UNVERIFIED","causal_FIFO_explanation":"UNVERIFIED"}
                        result["source_register"].append({"id":"E08","source":f"workflows/{wid}/00b_human_evidence_review.json", 
                            "provenance":"PUBLIC_PROBLEM_CONTEXT_ONLY","description":"Official/public source excerpts and human-reviewed hypothetical claim problem",
                            "validity":"Published problem context, not current client evidence, not proof of FIFO/skill scheduling"})
                        for entry in result["source_register"]:
                            if entry["id"]=="E05":
                                entry["source"]="No direct customer business data or authorized claims workflow attached (public contextual evidence is E08)"
                                entry["description"]="Customer-specific demand, ROI, and real process evidence remain missing"
                        for crit in result["axes"][0]["criteria"]:
                            if crit["id"]=="BV-04":
                                crit["finding"]="公開された問題背景はE08に収録。実顧客の需要・支払意思・保険案件の処理フローは未検証"
                        result["axes"][0]["criteria"].append({"id":"BV-06","title":"外部証拠と当該事業課題の整合（限定的）",
                            "status":"PUBLIC_PROBLEM_CONTEXT_ONLY" if aligned.get("status")=="TOPIC_MATCH_REVIEW_REQUIRED" else "HOLD",
                            "finding":"原文の課題領域のみ確認。FIFO因果・顧客固有SLA・要件導出は実証していない",
                            "evidence_refs":["E08"],"next_action":"当事者の一次資料と業務観測で問題原因を確認"})
                        result["axes"][1]["criteria"].append({"id":"AI-09","title":"要件種別に対応する合成受入評価",
                            "status":(trace_verification or {}).get('trace_status','HOLD'),
                            "finding":('進捗通知は独立した通知プロトタイプのみ。R1の担当者割当結果はこの要件の証明に使用しない' if trace['type']==rt.NOTIFICATION
                                else '担当者割当は固定合成HOLDOUTと独立プローブでのみ評価'),
                            "evidence_refs":["E08","E04","E06"],"next_action":"顧客承認済みの受入条件と実業務APIで再検証"})
                        if trace['type']==rt.NOTIFICATION:
                            result['decision'].update({'status':'HOLD','code':'HOLD_NOTIFICATION_NOT_INTEGRATED',
                                'stage':'TECHNICAL_VALIDATION','production_status':'NO_GO',
                                'production_go':False,'customer_business_go':False,
                                'description':'公開資料と進捗通知の仮説はトレース済み。独立した合成通知プロトタイプのみを検証。R1担当者割当は当該通知要件を検証しておらず、顧客連携・実運用は未実装。'})
                        elif not contract_eval or contract_eval.get("status")!="SUPPORTED_SYNTHETIC":
                            result["decision"].update({"status":"HOLD","code":"HOLD_GROUNDED_CONTRACT","stage":"TECHNICAL_VALIDATION",
                                "description":"公開問題背景は取得済みだが、合成データでの人間設定KPI・仕様検証がHOLD。顧客事業価値は未検証。"})
                        else:
                            result["decision"]["description"]+=" 公開根拠は問題背景に限定。固定の合成実験が人間設定の閾値を満たすだけで、公開事例の因果や顧客価値を証明しません。"
                        assessment_dir=m.path_for("assessments",assess["assessment_id"])
                        for name,content in (("assessment.json",json.dumps(result,ensure_ascii=False,indent=2)),
                                             ("report.md",m.ba.markdown(result)+"\n## v0.21 Requirement trace\n\n"+rt.markdown(trace,trace_verification))):
                            tmp=assessment_dir/(name+".tmp")
                            tmp.write_text(content,encoding="utf-8")
                            os.replace(tmp,assessment_dir/name)
                    state["linked_ids"]["assessments"]=assess["assessment_id"]
                    step(state,current,"COMPLETED_WITH_FINDINGS", "Production remains NO-GO; public source is contextual")
                except Exception as exc:
                    add_file(wid,"09_assessment_failure.json",{"error_type":type(exc).__name__,
                        "detail":str(getattr(exc,'detail',exc))[:600],
                        "artifact_readiness":ar.public_view(assessment_input)})
                    step(state,current,"FAILED",f"{type(exc).__name__}: {str(getattr(exc,'detail',exc))[:400]}")
            else:
                add_file(wid,"09_assessment_skip.json",{"status":"SKIPPED_UPSTREAM_DEPENDENCY",
                    "reason":"Complete R1 experiment is required for assessment",
                    "artifact_readiness":ar.public_view(assessment_input),
                    "production_go":False,"customer_business_go":False})
                step(state,current,"SKIPPED","06 R1 dependency: "+assessment_input['status'] + '; no business/production GO')
            snapshot_index(state)
            all_good=all(any(x["name"]==name and x["status"] in ("COMPLETED", "COMPLETED_WITH_FINDINGS")
                    for x in state["stages"]) for name in required_steps(state))
            state["status"]="COMPLETE" if all_good else "PARTIAL"
            if not all_good and not state.get("error"):
                first_issue=next((x for x in state["stages"] if x["status"] in ("FAILED","SKIPPED")),None)
                if first_issue:
                    state["error"]=first_issue["name"]+": "+first_issue.get("detail", "")
            state["phase"]="DONE"
            write(wid,state)
            save_archive(state)
        except Exception as exc:
            fail(state,current,exc)

    async def evidence_phase(wid: str) -> None:
        """Real acquisition, index validation, retrieval, then explicit user review.

        A public-source failure is terminal PARTIAL, never a synthetic success.
        """
        from . import evidence_rag as er
        state = read(wid)
        inp = FullRunStart(**state["inputs"])
        try:
            folder_path = er.fixed_path(inp.dataset_id)
            source_path = folder_path / "source_manifest.json"
            if not source_path.is_file():
                step(state, "00_evidence_grounded_requirements", "RUNNING", "Downloading public source")
                er.acquire(inp.dataset_id)
            # A cached source is only reusable if every SHA256 still matches.
            source_meta = er.validate_download(inp.dataset_id)
            step(state, "00_evidence_grounded_requirements", "RUNNING", "Building / validating search index")
            index_meta = er.ensure_index(inp.dataset_id)
            step(state, "00_evidence_grounded_requirements", "RUNNING", "Retrieving public excerpts and drafting requirement hypotheses")
            rag = await m.evidence_requirements(m.EvidenceQueryRequest(
                dataset_id=inp.dataset_id, query=inp.evidence_query, llm_extraction=inp.llm_extraction))
            if not rag.get("evidence"):
                raise ValueError("No public passages retrieved. Change the query or verify dataset; refusing synthetic fallback.")
            # Preserve exact retrieval result plus source and index provenance within the ONE workflow ZIP.
            add_file(wid, "00_evidence_grounded_requirements.json", rag)
            add_file(wid, "00_source_manifest.json", source_meta)
            add_file(wid, "00_index_metadata.json", index_meta)
            rag_report = er.ROOT / "rag_runs" / rag["rag_id"] / "report.md"
            (folder(wid) / "00_rag_report.md").write_bytes(rag_report.read_bytes())
            state["rag_id"] = rag["rag_id"]
            state["topic_alignment"] = rag.get("topic_alignment",{})
            # Preserve a raw byte copy of each downloaded document in the single ZIP.
            for item in source_meta["files"]:
                name=item["name"]
                (folder(wid)/("00_raw_source__"+name)).write_bytes((folder_path/name).read_bytes())
            state["status"] = "AWAITING_EVIDENCE_REVIEW"
            state["phase"] = "00b_evidence_review"
            step(state, "00_evidence_grounded_requirements", "COMPLETED_WITH_FINDINGS",
                 f"{len(rag['evidence'])} public excerpts; source hashes checked; semantic support unverified")
            step(state, "00b_evidence_review", "WAITING_HUMAN",
                 "Check topic alignment, select support, and configure an independent synthetic KPI contract before 01")
            save_archive(state)
        except Exception as exc:
            fail(state, "00_evidence_grounded_requirements", exc)

    @app.post("/api/full-run/start")
    async def full_run_start(body: FullRunStart, background_tasks:BackgroundTasks):
        wid, export_id=m.fresh_id(), m.fresh_id()
        public = body.evidence_mode == "public"
        record={"workflow_id":wid,"export_id":export_id,"created_at":m.now(),
            "updated_at":m.now(),"version":"0.21.1","evidence_mode":body.evidence_mode,"r1_mode":body.r1_mode,
            "status":"RUNNING","phase":"00_evidence_grounded_requirements" if public else "02_service_design",
            "inputs":body.model_dump(),"service_design":None,"linked_ids":{k:None for k in KINDS},
            "stages":[],"bundle_ready":False}
        record["linked_ids"]["workflows"]=wid
        write(wid,record)
        if public:
            step(record, "00_evidence_grounded_requirements", "RUNNING",
                 "Auto-download / verify source, build index, retrieve evidence; NEVER synthetic fallback")
            background_tasks.add_task(evidence_phase, wid)
        else:
            step(record, "00_evidence_grounded_requirements", "SKIPPED_BY_USER",
                 "Synthetic-only mode explicitly selected: no external dataset fetched or referenced")
            step(record, "00b_evidence_review", "SKIPPED_BY_USER", "No public evidence to review")
            step(record, "00c_grounded_test_contract", "SKIPPED_BY_USER", "Synthetic-only regression mode")
            step(record, "08c_grounded_kpi_verification", "SKIPPED_BY_USER", "Synthetic-only regression mode")
            step(record, "08d_notification_prototype", "SKIPPED_BY_USER", "Synthetic-only regression mode")
            step(record, "08e_requirement_trace", "SKIPPED_BY_USER", "Synthetic-only regression mode")
            add_file(wid, "01_input.json", {"original_brief":body.brief, "effective_brief":body.brief,
                "evidence_mode":"synthetic", "inputs":body.model_dump(), "customer_validity":"UNVERIFIED"})
            step(record, "01_input", "COMPLETED", "Explicit synthetic demonstration; no customer evidence")
            background_tasks.add_task(first_half, wid)
        return summarize(record)

    @app.post("/api/full-run/review-evidence")
    async def full_run_evidence_review(body:FullRunEvidenceReview, background_tasks:BackgroundTasks):
        state=read(body.workflow_id)
        if state["status"]!="AWAITING_EVIDENCE_REVIEW" or state["inputs"].get("evidence_mode")!="public":
            raise HTTPException(409,"Evidence review is not pending for this public workflow")
        rag=m.load("workflows",body.workflow_id,"00_evidence_grounded_requirements.json")
        evidence={e["evidence_id"]: e for e in rag["evidence"]}
        decision=body.decision
        ids=list(body.evidence_ids)
        if decision=="approved":
            text=(body.approved_requirement or "").strip()
            if len(text)<20 or text.upper() in ("REQUIRES_HUMAN_DERIVATION", "TO_BE_DEFINED_WITH_CUSTOMER"):
                raise HTTPException(422,"Review requires a substantive human-edited requirement hypothesis (at least 20 characters)")
            if not ids or len(ids)!=len(set(ids)) or any(eid not in evidence for eid in ids):
                raise HTTPException(422,"Select unique evidence IDs from THIS workflow's retrieval only")
            alignment=rag.get('topic_alignment',{})
            if alignment.get('status')!='TOPIC_MATCH_REVIEW_REQUIRED':
                raise HTTPException(422,'Domain/topic mismatch: published evidence cannot be used as support for this insurance claims synthetic contract. Reject or choose an insurance-specific source.')
            allowed_topic=set(alignment.get('topic_matching_evidence_ids',[]))
            if not set(ids).intersection(allowed_topic):
                raise HTTPException(422,'Choose at least one topic-matching source passage; unrelated public citations cannot justify this flow')
            from . import evidence_rag as er
            htext=text.lower()
            if not any(term in htext for term in er._INSURANCE_TERMS):
                raise HTTPException(422, 'Requirement must explicitly concern insurance claims; unrelated retail banking hypotheses are not accepted.')
            # A progress-notification hypothesis can require updates on claim status
            # without literally saying 'delay'. The retrieved source still must be
            # independently topic-matched to insurance claim delays above.
            if body.requirement_type==rt.ASSIGNMENT and not any(term in htext for term in (
                    *er._DELAY_TERMS, 'deadline', 'due date', 'sla', '期日', '締切', '時間')):
                raise HTTPException(422, '00bで「担当者割当」を選択しています。要件文に保険請求の遅延・期限・処理問題を明記してください。進捗通知の仮説なら、機能分類を「保険請求の進捗通知」に変更してください。 (Assignment hypothesis requires claim-delay/deadline/processing context.)')
            if body.support_assessment!='supports_problem':
                raise HTTPException(422,'Human must explicitly judge that the selected excerpt supports the *problem context* (NOT FIFO cause or implementation)')
            try:
                trace=rt.compile_trace(requirement=text,evidence_ids=ids,
                    requirement_type=body.requirement_type,source_records=[evidence[eid] for eid in ids],
                    review_actor=body.actor,max_notification_delay_hours=body.max_notification_delay_hours,
                    min_notification_coverage_pct=body.min_notification_coverage_pct)
            except ValueError as exc:
                raise HTTPException(422,str(exc)) from exc
            if body.requirement_type==rt.ASSIGNMENT:
                contract=gc.compile_contract(requirement=text,evidence_ids=ids,max_missed=body.max_total_missed,
                                             min_reduction_pct=body.min_reduction_pct,require_behavioral=body.require_behavioral)
            else:
                contract={'version':rt.VERSION,'type':rt.NOTIFICATION,'feature_id':trace['feature_id'],
                          'notification_thresholds':trace['notification_thresholds'],
                          'assignment_kpi_not_applicable':True,
                          'scope':'STANDALONE_SYNTHETIC_NOTIFICATION_PROTOTYPE_NOT_R1'}
            # This explicitly reviewed note is context, not a change to the fixed synthetic R0/R1 contracts.
            note=("\n\n[PUBLIC EVIDENCE — HUMAN-REVIEWED HYPOTHESIS, NOT CUSTOMER APPROVAL]\n"
                  f"Hypothesis: {text}\n"
                  f"Evidence pointers (source statements only): {', '.join(ids)}\n"
                  "Evidence support, causal attribution, customer validity: UNVERIFIED. "
                  "R0 FIFO and R1 contracts remain synthetic fixed test specifications.\n"
                  "[END HUMAN-REVIEWED HYPOTHESIS]")
            effective=state["inputs"]["brief"]+note
            if len(effective)>5000:
                raise HTTPException(422,"Approved hypothesis plus customer brief exceed 5000 characters")
        else:
            effective=None
            text=(body.approved_requirement or "").strip()
        review={"decision":decision,"actor":body.actor,"rationale":body.rationale,
            "approved_requirement_hypothesis":text if decision=="approved" else None,
            "selected_evidence_ids":ids if decision=="approved" else [],
            "evidence_pointer_records":[evidence[eid] for eid in ids] if decision=="approved" else [],
            "rag_id":rag["rag_id"],"dataset_id":rag["dataset_id"],"created_at":m.now(),
            "approval_scope":"DEMO_HYPOTHESIS_ONLY" if decision=="approved" else "REJECTED",
            "semantic_evidence_support":"HUMAN_ASSERTED_PROBLEM_CONTEXT_ONLY" if decision=="approved" else "UNVERIFIED",
            "topic_alignment":rag.get("topic_alignment"), "support_assessment":body.support_assessment,
            "customer_requirement_approval":"NOT_OBTAINED", "requirement_type":body.requirement_type if decision=='approved' else None}
        add_file(body.workflow_id,"00b_human_evidence_review.json",review)
        if decision!="approved":
            step(state, "00b_evidence_review", "REJECTED", "Source requirement hypothesis rejected by human")
            state["status"]="PARTIAL"
            state["phase"]="EVIDENCE_REJECTED_BY_HUMAN"
            write(body.workflow_id,state)
            save_archive(state)
        else:
            add_file(body.workflow_id,"00c_grounded_test_contract.json",contract)
            add_file(body.workflow_id,"00c_requirement_trace.json",trace)
            spec=(gc.spec_md(contract) if body.requirement_type==rt.ASSIGNMENT else
                  '# Progress-notification synthetic prototype\n\n'+rt.markdown(trace))
            (folder(body.workflow_id)/"00c_technical_spec.md").write_text(spec,encoding="utf-8")
            (folder(body.workflow_id)/"00c_requirement_trace.md").write_text(rt.markdown(trace),encoding='utf-8')
            state['requirement_type']=body.requirement_type
            step(state,"00c_grounded_test_contract","COMPLETED", "Human-configured bounded KPI evaluator; pinned synthetic test fixture")
            state["execution_brief"]=effective
            step(state, "00b_evidence_review", "COMPLETED", "Human selected public source pointers and a hypothetical requirement; NOT customer-approved")
            add_file(body.workflow_id,"01_input.json",{
                "original_brief":state["inputs"]["brief"], "effective_brief":effective,
                "approved_hypothesis":text,"selected_evidence_ids":ids,"rag_id":rag["rag_id"],
                "evidence_mode":"public","inputs":state["inputs"],"customer_validity":"UNVERIFIED",
                "r0_contract_changed":False,"technical_evaluator":"BOUNDED_HUMAN_CONFIGURED_SYNTHETIC_CONTRACT",
                "technical_spec_path":"00c_technical_spec.md", "requirement_type":body.requirement_type,
                "requirement_trace_path":"00c_requirement_trace.json", "acceptance_test_target":trace['test_target']})
            step(state, "01_input", "COMPLETED", "Evidence-reviewed hypothesis inserted into 01 brief; fixed synthetic R0 contract unchanged")
            state["status"]="RUNNING"
            state["bundle_ready"]=False  # previous PARTIAL is superseded by in-progress work
            state["phase"]="02_service_design"
            write(body.workflow_id,state)
            background_tasks.add_task(first_half,body.workflow_id)
        return summarize(state)

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
            state["bundle_ready"]=False  # archived 05 checkpoint is not the final ZIP
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
        return FileResponse(file,filename=f"claims_full_run_v020_{workflow_id}.zip",media_type="application/zip")

