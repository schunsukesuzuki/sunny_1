"""Small, deterministic cross-stage boundary checks inspired by MSR EAIR.

This is NOT the Microsoft EAIR toolkit and is NOT a multi-agent simulation.
The goal is to detect unsafe hand-offs in one synthetic claims workflow,
intercept before consumption, and preserve a narrow evidence-based audit trail.
Nothing here proves the customer requirement, model reasoning, or production safety.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VERSION = "BOUNDARY-ASSURANCE-v0.24.0"

# Declarative contracts are deliberately small enough to review with a customer.
CONTRACTS = {
    "00b_to_01": {
        "owner": "human evidence reviewer",
        "consumer": "service-design input",
        "invariants": ["explicit_hypothesis_review", "evidence_ids_from_current_rag",
                       "requirement_and_feature_unchanged", "hypothesis_not_customer_approval"],
    },
    "05_to_06": {
        "owner": "explicit human revision approval",
        "consumer": "R1 code generation/evaluation",
        "invariants": ["approved_proposal_matches_workflow", "decision_is_approved",
                       "approval_is_recorded_before_execution"],
    },
    "06_to_downstream": {
        "owner": "R1 evaluation and artifact writer",
        "consumer": "08b/08c/08f/09 evaluators",
        "invariants": ["experiment_lineage_matches_current_workflow",
                       "selected_code_digest_matches", "completed_result_not_started_marker"],
    },
    "05_to_06_dogwood": {
        "owner": "server-side workflow execution adapter",
        "consumer": "R1 code generation / E2B evaluation",
        "invariants": ["recorded_human_approval_precedes_execution",
                       "matching_workflow_proposal_and_approval_identity",
                       "no_temporal_revocation", "deny_by_default_if_engine_unavailable"],
        "scope": "ephemeral Dogwood replay, not a persistent authorizer",
    },
    "shared_budget_fixture": {
        "owner": "multiple capacity consumers (synthetic only)",
        "consumer": "global resource allocator",
        "invariants": ["sum_of_claims_does_not_exceed_shared_capacity"],
    },
}


def _json(folder: Path, name: str) -> dict | None:
    p = folder / name
    if not p.is_file() or p.is_symlink():
        return None
    try:
        value = json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _result(boundary: str, violations: list[dict], checked: list[str], *, applicable=True) -> dict:
    return {"version": VERSION, "boundary": boundary,
            "status": "NOT_APPLICABLE" if not applicable else "HOLD" if violations else "PASS",
            "checks_performed": checked, "violations": violations,
            "semantic_validity": "NOT_PROVEN", "production_authorization": False}


def _violation(code: str, *, evidence: list[str], detail: str, repair: str) -> dict:
    return {"code": code, "evidence_paths": evidence, "detail": detail,
            "suggested_repair": repair}


def public_handoff(state: dict, workflow_folder: Path) -> dict:
    """Only explicitly reviewed source hypotheses can enter step 01.

    Note: an actor label is not an authenticated user identity.
    """
    if state.get("inputs", {}).get("evidence_mode") != "public":
        return _result("00b_to_01", [], [], applicable=False)
    review = _json(workflow_folder, "00b_human_evidence_review.json")
    rag = _json(workflow_folder, "00_evidence_grounded_requirements.json")
    trace = _json(workflow_folder, "00c_requirement_trace.json")
    first = _json(workflow_folder, "01_input.json")
    errors = []
    paths = ["00b_human_evidence_review.json", "00_evidence_grounded_requirements.json",
             "00c_requirement_trace.json", "01_input.json"]
    if not all((review, rag, trace, first)):
        errors.append(_violation("MISSING_HANDOFF_RECORD", evidence=paths,
            detail="Reviewed evidence, RAG, typed requirement and input snapshot must all exist",
            repair="Regenerate the incomplete review artifact; never synthesize approval"))
        return _result("00b_to_01", errors, ["record_presence"])
    ids = review.get("selected_evidence_ids")
    allowed = {e.get("evidence_id") for e in rag.get("evidence", []) if isinstance(e, dict)}
    if not (review.get("decision") == "approved" and review.get("approval_scope") == "DEMO_HYPOTHESIS_ONLY"
            and isinstance(review.get("actor"), str) and review["actor"].strip()):
        errors.append(_violation("UNAPPROVED_REQUIREMENT_PROMOTION", evidence=[paths[0]],
            detail="Missing explicit reviewer approval for this synthetic hypothesis",
            repair="Stop and obtain a new human review; do not infer authorization from LLM output"))
    if not (isinstance(ids, list) and ids and len(ids) == len(set(ids)) and set(ids) <= allowed):
        errors.append(_violation("EVIDENCE_LINEAGE_DRIFT", evidence=paths[:2],
            detail="Selected evidence IDs are not unique/current-workflow retrieval IDs",
            repair="Re-select only evidence from the current RAG run"))
    requirement = review.get("approved_requirement_hypothesis")
    if (not requirement or requirement != trace.get("requirement_hypothesis")
            or requirement != first.get("approved_hypothesis")
            or ids != trace.get("source_evidence_ids")
            or ids != first.get("selected_evidence_ids")
            or trace.get("type") != first.get("requirement_type")
            or first.get("rag_id") != rag.get("rag_id")
            or review.get("rag_id") != rag.get("rag_id")):
        errors.append(_violation("REQUIREMENT_STATE_DRIFT", evidence=paths,
            detail="Approved hypothesis, feature, evidence list or RAG ID changed across hand-off",
            repair="Rebuild the typed trace and input from the human-approved review"))
    if (review.get("customer_requirement_approval") != "NOT_OBTAINED"
            or trace.get("is_real_customer_approved") is not False
            or first.get("customer_validity") != "UNVERIFIED"):
        errors.append(_violation("CUSTOMER_APPROVAL_OVERCLAIM", evidence=[paths[0], paths[2], paths[3]],
            detail="Demo-only hypothesis is presented as customer-approved",
            repair="Keep customer acceptance UNVERIFIED until a separate authenticated process exists"))
    return _result("00b_to_01", errors,
                   ["explicit_human_review", "retrieval_membership", "typed_trace_integrity", "customer_scope"])


def approval_handoff(state: dict, approval_record: dict | None) -> dict:
    """A reviewer decision must be linked to the actual pending proposal."""
    expected = state.get("linked_ids", {})
    errors = []
    if not isinstance(approval_record, dict):
        errors.append(_violation("MISSING_APPROVAL", evidence=["approvals/<approval_id>/approval.json"],
            detail="No persisted human decision", repair="Return to step 05 for explicit review"))
    elif (approval_record.get("decision") != "approved"
          or approval_record.get("approval_id") != expected.get("approvals")
          or approval_record.get("proposal_id") != expected.get("proposals")):
        errors.append(_violation("AUTHORITY_OR_LINEAGE_MISMATCH", evidence=["approval.json", "workflow.json"],
            detail="Approval decision or linked proposal/approval ID does not match this workflow",
            repair="Block R1 and request review for the correct proposal"))
    return _result("05_to_06", errors, ["explicit_approval", "proposal_lineage"])


def experiment_handoff(state: dict, inspection: dict) -> dict:
    """A valid local artifact must ALSO belong to the invoking workflow."""
    status = inspection.get("status")
    # Missing/corrupt/unfinished artifacts are independently blocked in v0.22.
    if status not in ("READY", "NO_SELECTED_R1"):
        result = _result("06_to_downstream", [], ["v022_readiness_guard_deferred"])
        result["status"] = "DEFERRED_UPSTREAM"
        result["upstream_status"] = status
        return result
    record = inspection.get("record") or {}
    linked = state.get("linked_ids", {})
    mapping = {"experiment_id": "experiments", "r0_run_id": "runs",
               "proposal_id": "proposals", "approval_id": "approvals"}
    errors = []
    for field, kind in mapping.items():
        if not linked.get(kind) or record.get(field) != linked[kind]:
            errors.append(_violation("CROSS_WORKFLOW_ARTIFACT", evidence=["experiment.json", "workflow.json"],
                detail=f"{field} differs from the {kind} ID of the active workflow",
                repair="Refuse to consume the artifact; investigate cross-workflow linkage"))
    return _result("06_to_downstream", errors, ["experiment_r0_proposal_approval_linkage", "v022_sha256_guard"])


def apply_experiment_gate(state: dict, inspection: dict) -> dict:
    """Preserve v0.22 readiness semantics, but add fail-closed lineage checks."""
    gate = experiment_handoff(state, inspection)
    if gate["violations"]:
        return {**inspection, "status": "LINEAGE_MISMATCH",
                "reason": "; ".join(v["detail"] for v in gate["violations"]),
                "boundary_gate": gate}
    return {**inspection, "boundary_gate": gate}


def shared_budget_check(claims: list[int], cap: int) -> bool:
    """Simple global constraint for a synthetic multi-consumer risk fixture."""
    return cap >= 0 and all(isinstance(x, int) and x >= 0 for x in claims) and sum(claims) <= cap


def regression_scenarios() -> dict:
    """Deterministic, simulated boundary violations, NOT production risk frequencies."""
    base = {"linked_ids": {"runs": "r", "proposals": "p", "approvals": "a", "experiments": "e"}}
    scenarios = []
    altered = {"experiment_id": "e", "r0_run_id": "r", "proposal_id": "other", "approval_id": "a"}
    checks = [
        ("cross_workflow_result", experiment_handoff(base, {"status": "READY", "record": altered})["status"] == "HOLD"),
        ("unapproved_revision", approval_handoff(base, {"decision": "rejected", "approval_id": "a", "proposal_id": "p"})["status"] == "HOLD"),
        ("shared_capacity_oversubscription", not shared_budget_check([6, 6], 10)),
        ("safe_shared_capacity", shared_budget_check([5, 5], 10)),
        ("healthy_approval", approval_handoff(base, {"decision": "approved", "approval_id": "a", "proposal_id": "p"})["status"] == "PASS"),
    ]
    for name, ok in checks:
        scenarios.append({"scenario_id": name, "expected_detection": True,
                          "detected_as_expected": bool(ok), "synthetic_fixture": True})
    return {"version": VERSION, "status": "PASS" if all(s["detected_as_expected"] for s in scenarios) else "FAIL",
            "scenarios": scenarios, "scope": "Synthetic deterministic checks; no LLM or multi-agent risk rates"}


def topology(linked_ids: dict, workflow_id: str) -> dict:
    """Minimal metadata DAG, no GraphDB or GraphRAG service."""
    names = ("runs", "proposals", "approvals", "experiments", "policy_validations", "benchmarks", "assessments")
    nodes = [{"node_id": "workflow", "kind": "workflows", "artifact_id": workflow_id}]
    for kind in names:
        if linked_ids.get(kind):
            nodes.append({"node_id": kind, "kind": kind, "artifact_id": linked_ids[kind]})
    if linked_ids.get("approvals"):
        nodes.append({"node_id": "dogwood_gate", "kind": "authorization", "artifact_id": "05_dogwood_authorization.json"})
    pairs = [("workflow", "runs"), ("runs", "proposals"), ("proposals", "approvals"),
             ("approvals", "dogwood_gate"), ("dogwood_gate", "experiments"),
             ("experiments", "policy_validations"),
             ("experiments", "assessments"), ("benchmarks", "assessments")]
    existing = {n["node_id"] for n in nodes}
    edges = [{"source": a, "target": b, "type": "DECLARED_DEPENDENCY"}
             for a, b in pairs if a in existing and b in existing]
    return {"version": VERSION, "nodes": nodes, "edges": edges,
            "semantics": "Declared workflow dependencies only; no proof of semantic support"}


def certificate(gate: dict, *, stopped_at: str) -> list[dict]:
    """Structured failure snapshots. No chain-of-thought or invented root causes."""
    output = []
    for i, v in enumerate(gate.get("violations", []), start=1):
        output.append({"certificate_id": f"BC-{stopped_at}-{i:02d}",
            "first_detected_boundary": gate["boundary"], "anomaly_code": v["code"],
            "propagation_observed": [gate["boundary"]],
            "terminal_effect": "BLOCKED_BEFORE_CONSUMPTION", "interception": True,
            "evidence_paths": v["evidence_paths"], "observed_detail": v["detail"],
            "repair_proposal": v["suggested_repair"], "status": "BOUNDARY_HOLD",
            "scope": "Local persisted-record checks; not an authenticated authorization system"})
    return output


def report(state: dict, checkpoints: list[dict], suite: dict) -> dict:
    violations = [v for c in checkpoints for v in c.get("violations", [])]
    certificates = [x for c in checkpoints for x in c.get("certificates", [])]
    # A violation caught at the boundary is not a realized terminal harm.
    deferred = any(c.get("status") == "DEFERRED_UPSTREAM" for c in checkpoints)
    return {"version": VERSION,
            "status": "HOLD" if violations or suite["status"] != "PASS" else "INCOMPLETE_UPSTREAM" if deferred else "PASS_CONTROLLED",
            "checks": [{"boundary": c.get("boundary"), "status": c.get("status"),
                        "violations": c.get("violations", [])} for c in checkpoints],
            "realization_certificates": certificates,
            "risk_axes": {
                "structural_opportunity": "TESTED_WITH_SYNTHETIC_FIXTURES",
                "process_anomaly_count": len(violations),
                "realized_risk": "NOT_OBSERVED_POST_INTERCEPTION",
                "terminal_harm": "NOT_ESTABLISHED; NO PRODUCTION EXECUTION",
                "interceptions": len(certificates),
                "task_utility": "REPORTED_IN_R1_KPI_WHEN_AVAILABLE; NOT INFERRED_FROM_BOUNDARY_PASS",
            }, "regression_suite": suite,
            "customer_validity": "UNVERIFIED", "production_go": False,
            "limits": ["Local record consistency, not formal proof",
                       "Synthetic scenario detection is not a measured incident probability",
                       "Reviewer actor labels are unauthenticated",
                       "No GraphRAG, multi-agent deployment or trusted append-only storage",
                       "Dogwood is bounded replay, not a continuous authenticated authorizer"]}


def markdown(report: dict) -> str:
    lines = ["# Boundary Assurance — EAIR-inspired, bounded v0.24", "",
             f"- Status: **{report['status']}**", "- Production: **NO-GO**",
             "- Focus: identity, human review, typed requirements, and artifact readiness", "",
             "## Boundary checks"]
    for gate in report["checks"]:
        lines.append(f"- `{gate['boundary']}`: {gate['status']} ({len(gate['violations'])} issue(s))")
    lines.extend(["", "## Synthetic regression scenarios",
                  f"- Detection suite: **{report['regression_suite']['status']}**"])
    for sc in report["regression_suite"]["scenarios"]:
        lines.append(f"- `{sc['scenario_id']}`: {'PASS' if sc['detected_as_expected'] else 'FAIL'}")
    lines.extend(["", "## Scope", ""])
    for limit in report["limits"]:
        lines.append(f"- {limit}")
    return "\n".join(lines) + "\n"
