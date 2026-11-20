"""Human-reviewed requirement evidence and deterministic provenance-aware judgement.

The checker does not substitute synthetic proxy scores for real customer value.
"""
from __future__ import annotations

from .models import (
    CustomerEvidence, RequirementAssessment, RequirementsDraft, ServiceDesign,
    RequirementFinding,
)


def fallback_design(requirements: RequirementsDraft) -> ServiceDesign:
    """Auditable compatibility fallback. The normal v0.6 UI calls the design endpoint."""
    return ServiceDesign(
        design_source="fallback_not_llm_reviewed",
        product_scope="教育SaaSの週次学習計画（合成データのみ）",
        actors=requirements.target_users,
        use_cases=["学習可能時間と科目条件を入力する", "週次の時間配分案を提示する"],
        domain_entities=["Student", "Subject", "Allocation"],
        service_flow=["入力制約を確認", "時間配分アルゴリズムを実行", "制約を検証して計画を提示"],
        hard_constraints=["すべての生徒・科目を1回ずつ返す", "配分時間は非負整数", "科目上限以内", "配分合計と利用可能時間が一致"],
        soft_objectives=["合成代理効用の最大化"],
        interfaces=["/home/user/input.json → /home/user/output.json"],
        acceptance_tests=["全seedで制約違反ゼロ", "固定Greedyと厳密DPと比較"],
        alternatives=["静的Greedy", "厳密DP", "Qwen生成候補"],
        assumptions=requirements.unverified_assumptions,
        external_validation_needed=requirements.next_customer_validation,
    )


def assess_requirements(requirements: RequirementsDraft, evidence: list[CustomerEvidence],
                        implementation_pass: bool) -> RequirementAssessment:
    """Evidence must be sourced from actual customers, explicitly human-reviewed.

    'SUPPORTED_PRELIMINARY' only acknowledges reviewed external feedback,
    and does NOT assert that market demand or causality is established.
    """
    findings: list[RequirementFinding] = []
    for index, item in enumerate(requirements.acceptance_criteria):
        requirement_id = f"AC-{index + 1:02d}"
        relevant = [e for e in evidence if e.requirement_id == requirement_id]
        admissible = [e for e in relevant if e.provenance == "real_customer" and e.human_verified and e.source_reference.strip()]
        support = [e for e in admissible if e.verdict == "support"]
        contradict = [e for e in admissible if e.verdict == "contradict"]
        if support and contradict:
            status = "CONFLICTED"
        elif contradict:
            status = "REJECTED_PRELIMINARY"
        elif support:
            status = "SUPPORTED_PRELIMINARY"
        else:
            status = "UNVERIFIED"
        findings.append(RequirementFinding(
            requirement_id=requirement_id, criterion=item, status=status,
            admissible_evidence_ids=[e.evidence_id for e in admissible],
            excluded_evidence_ids=[e.evidence_id for e in relevant if e not in admissible],
            rationale=("顧客由来と申告された証拠に参照情報と人間の確認があり、暫定判断のみ。" if admissible
                       else "実顧客由来・出典明示・人間の確認済みの証拠がないため未検証。"),
        ))
    statuses = [f.status for f in findings]
    if "CONFLICTED" in statuses:
        validity = "CONFLICTED"
    elif "REJECTED_PRELIMINARY" in statuses:
        validity = "REJECTED_PRELIMINARY"
    elif findings and all(s == "SUPPORTED_PRELIMINARY" for s in statuses):
        validity = "SUPPORTED_PRELIMINARY"
    else:
        validity = "UNVERIFIED"
    return RequirementAssessment(
        implementation_validity="PASS" if implementation_pass else "FAIL",
        requirement_validity=validity,
        findings=findings,
        evidence_count=len(evidence),
        next_customer_validation=requirements.next_customer_validation,
        decision="HUMAN_REVIEW_REQUIRED",
        note="合成データのスコアは要件妥当性の証拠に算入しない。顧客証拠は自己申告であり独立検証ではない。",
    )
