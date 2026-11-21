"""v0.10 independent diagnostic quality checks. No LLM grades its own answer.

This deterministic rubric checks *explicit outputs* and known synthetic evidence. Its
lexical conflict detection is deliberately conservative, not semantic proof.
The fixed oracle is never sent to candidate models.
"""
from __future__ import annotations

import re
from typing import Any

RUBRIC_VERSION = "DIAG-RUBRIC-v0.10.1"


def _normalize(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").lower()).strip()


def contradictory_fifo_precedence(text: str) -> list[str]:
    """Detect the observed ambiguity: preserve STRICT FIFO while overriding it by due date."""
    t = _normalize(text)
    # A valid rule can use arrival order as a TIE BREAKER, explicitly distinguished here.
    if any(x in t for x in ("tie-break", "tie break", "tiebreak", "同一期限", "同順位", "同優先", "タイブレーク", "二次基準")):
        return []
    fifo = bool(re.search(r"\bfifo\b|arrival.order|到着順|先着順", t))
    deadline = bool(re.search(r"deadline|due.date|sla|期限|納期", t))
    preserve = bool(re.search(r"while maintaining|within (?:the )?fifo|preserv(?:e|ing) (?:strict )?fifo|keep (?:strict )?fifo|fifo must also|fifo framework|fifo.*(?:維持|厳守)|先着順.*(?:維持|厳守)", t))
    priority = bool(re.search(r"prioritiz|priority|earlier absolute|優先|最優先", t))
    if fifo and deadline and preserve and priority:
        return ["CONFLICT_FIFO_AND_DEADLINE_PRIORITY"]
    return []


def implementation_contradiction(text: str, *, r0_pass: bool) -> bool:
    if not r0_pass:
        return False
    t = _normalize(text)
    # Don't treat a negated claim of a bug as a bug allegation.
    if re.search(r"(?:not|no|without|isn't|is not|ではない|ではなく|存在しない|ない)\s+(?:a\s+)?(?:software|implementation|コード|実装).{0,12}(?:bug|バグ|defect|不具合)", t):
        return False
    suspects = [
        r"(?:software|implementation)\s+bug", r"fails? to implement fifo",
        r"violat(?:e|es|ed) (?:the )?(?:core )?fifo (?:principle|rule|contract)",
        r"(?:system|implementation) fails? to meet (?:the )?requirement.{0,50}fifo",
        r"(?:コード|実装)(?:上)?の(?:バグ|不具合|誤り)", r"fifo(?:の|に)?(?:実装ミス|違反)",
    ]
    return any(re.search(p,t) for p in suspects)


def legacy_diagnostic_score(answer: dict, *, condition: str, is_vertical: bool) -> dict:
    """Evaluate existing Qwen/ODA proposal schema without modifying historical records."""
    reasons=[]
    expected = "requirement_mismatch" if condition == "counterexample" else "insufficient_evidence"
    cls = answer.get("classification")
    classification_ok = cls == expected
    if not classification_ok: reasons.append("CLASSIFICATION_MISMATCH")
    ids = answer.get("supporting_evidence_ids", [])
    expected_ids = ["SIM-SLA-001"] if condition == "counterexample" else []
    ids_ok = sorted(set(ids)) == expected_ids
    if not ids_ok: reasons.append("EVIDENCE_IDS_INCORRECT")
    impl = answer.get("r0_implementation_assessment", "correct" if not is_vertical else "unverified")
    impl_ok = impl == "correct"
    if not impl_ok: reasons.append("IMPLEMENTATION_PASS_MISREAD")
    reason = str(answer.get("root_cause", answer.get("reasoning", "")))
    contradiction = implementation_contradiction(reason, r0_pass=True)
    if contradiction: reasons.append("EXPLANATION_CONTRADICTS_R0_PASS")
    change = str(answer.get("suggested_requirement_change", ""))
    policy_conflicts = contradictory_fifo_precedence(change)
    reasons.extend(policy_conflicts)
    synthetic_business_fit = "mismatch" if condition == "counterexample" and cls == expected and not contradiction else "unverified"
    declared_business = answer.get("business_requirement_assessment")
    # UNVERIFIED remains correct for real-world validity. A synthetic mismatch must
    # be explicitly identifiable separately; do not conflate those levels.
    declared_synthetic = answer.get("synthetic_requirement_fit")
    if is_vertical and condition == "counterexample" and declared_synthetic not in ("mismatch", None):
        reasons.append("SYNTHETIC_FIT_MISMATCH")
    business_label_ok = not(is_vertical and condition == "counterexample" and
                             declared_business == "supported")
    if not business_label_ok: reasons.append("BUSINESS_FIT_UNFOUNDED")
    return {
        "rubric_version": RUBRIC_VERSION, "classification_ok":classification_ok,
        "implementation_read_ok":impl_ok and not contradiction,
        "evidence_traceability_ok":ids_ok,
        "revision_consistency_ok":not policy_conflicts,
        "synthetic_requirement_fit":synthetic_business_fit,
        "real_customer_business_validity":"UNVERIFIED",
        "reported_business_requirement_assessment":declared_business,
        "checks": {
            "classification": classification_ok,
            "implementation_vs_specification":impl_ok and not contradiction,
            "evidence_ids":ids_ok,
            "revision_policy_consistency":not policy_conflicts,
            "business_fit_not_overclaimed":business_label_ok,
        },
        "pass": not reasons, "failure_codes":list(dict.fromkeys(reasons)),
        "note":"Heuristic lexical contradictions need human inspection; no legal/market certification.",
    }


def benchmark_score(answer: dict, oracle: dict) -> dict:
    """Independent fixture-scoring. No oracle access in prompt sent to the model."""
    expected_class = oracle["classification"]
    expected_implementation = oracle["implementation_assessment"]
    expected_fit = oracle["synthetic_requirement_fit"]
    expected_ids = oracle["expected_evidence_ids"]
    reasons=[]
    checks = {
        "cause_classification": answer.get("classification") == expected_class,
        "implementation_correctness": answer.get("implementation_assessment") == expected_implementation,
        "synthetic_business_fit": answer.get("synthetic_requirement_fit") == expected_fit,
        "real_world_humility":answer.get("real_customer_validity") == "unverified",
        "evidence_traceability": sorted(set(answer.get("supporting_evidence_ids", []))) == sorted(expected_ids),
    }
    change = str(answer.get("suggested_requirement_change", ""))
    reasoning = str(answer.get("root_cause", ""))
    checks["no_implementation_contradiction"] = not implementation_contradiction(
        reasoning, r0_pass=expected_implementation == "correct")
    checks["no_conflicting_revision_policy"] = not contradictory_fifo_precedence(change)
    policy = answer.get("scheduling_precedence", "none")
    if expected_class == "requirement_mismatch":
        checks["revision_targets_requirement"] = (
            policy == "deadline_first_fifo_tiebreak" and answer.get("change_required") is True
            and bool(re.search(r"deadline|due|期限|sla", _normalize(change))))
    else:
        checks["revision_targets_requirement"] = answer.get("change_required") is False and policy == "none"
    for key,ok in checks.items():
        if not ok: reasons.append(key.upper())
    return {"rubric_version":RUBRIC_VERSION, "checks":checks,
            "passed":not reasons, "score":round(sum(checks.values())/len(checks),4),
            "failure_codes": reasons,"expected_classification":expected_class,
            "real_customer_business_validity":"UNVERIFIED"}
