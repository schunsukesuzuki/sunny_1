from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class BusinessInputs(BaseModel):
    monthly_price_yen: int = Field(12000, ge=0, le=10_000_000)
    paying_schools: int = Field(30, ge=0, le=100_000)
    monthly_operating_cost_yen: int = Field(180000, ge=0, le=100_000_000)
    hours_saved_per_school: float = Field(5, ge=0, le=1000)
    teacher_hourly_cost_yen: int = Field(2500, ge=0, le=100_000)


class ProjectInput(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    brief: str = Field(min_length=20, max_length=8000)
    business: BusinessInputs = Field(default_factory=BusinessInputs)
    seed: int = Field(42, ge=0, le=999_990)
    evaluation_seeds: int = Field(3, ge=1, le=8)
    students_count: int = Field(12, ge=4, le=40)
    holdout_seeds: int = Field(2, ge=1, le=8, description="Held-out seeds never used for code revision")
    min_quality_ratio: float = Field(0.98, ge=0.5, le=1.0, description="Generated/optimal minimum mean score")
    min_improvement_ratio: float = Field(1.01, ge=1.0, le=1.5, description="Generated/static greedy minimum mean score")
    max_repair_attempts: int = Field(2, ge=0, le=3, description="Maximum code revisions for functional NO-GO or quality HOLD")


class RequirementsDraft(BaseModel):
    customer_problem: str
    target_users: list[str]
    value_hypothesis: str
    must_have: list[str]
    acceptance_criteria: list[str]
    unverified_assumptions: list[str]
    unanswered_questions: list[str]
    next_customer_validation: list[str]


class ServiceDesign(BaseModel):
    """Editable intermediate representation, not an approved product specification."""
    design_source: str = "qwen_draft_unapproved"
    product_scope: str
    actors: list[str] = Field(default_factory=list)
    use_cases: list[str] = Field(default_factory=list)
    domain_entities: list[str] = Field(default_factory=list)
    service_flow: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
    soft_objectives: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    acceptance_tests: list[str] = Field(default_factory=list)
    alternatives: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    external_validation_needed: list[str] = Field(default_factory=list)


class DesignRequest(BaseModel):
    project: ProjectInput
    requirements: RequirementsDraft


class CustomerEvidence(BaseModel):
    evidence_id: str = Field(min_length=1, max_length=80)
    requirement_id: str = Field(pattern=r"^AC-[0-9]{2}$")
    provenance: Literal["synthetic", "real_customer", "stakeholder", "desk_research"]
    verdict: Literal["support", "contradict", "inconclusive"]
    observation: str = Field(min_length=3, max_length=2000)
    source_reference: str = Field("", max_length=500)
    human_verified: bool = False
    reviewer: str = Field("", max_length=120)


class RequirementFinding(BaseModel):
    requirement_id: str
    criterion: str
    status: Literal["UNVERIFIED", "SUPPORTED_PRELIMINARY", "REJECTED_PRELIMINARY", "CONFLICTED"]
    admissible_evidence_ids: list[str]
    excluded_evidence_ids: list[str]
    rationale: str


class RequirementAssessment(BaseModel):
    implementation_validity: Literal["PASS", "FAIL"]
    requirement_validity: Literal["UNVERIFIED", "SUPPORTED_PRELIMINARY", "REJECTED_PRELIMINARY", "CONFLICTED"]
    findings: list[RequirementFinding]
    evidence_count: int
    next_customer_validation: list[str]
    decision: str
    note: str


class RequirementRefinementProposal(BaseModel):
    prior_run_id: str
    proposed_requirements: RequirementsDraft
    diagnosis: list[str]
    change_reasons: list[str]
    unresolved_evidence: list[str]
    proposed_validation: list[str]
    status: str = "PROPOSAL_ONLY_HUMAN_APPROVAL_REQUIRED"


class RefineRequest(BaseModel):
    run_id: str
    evidence: list[CustomerEvidence] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    project: ProjectInput


class GenerateRequest(BaseModel):
    project: ProjectInput
    requirements: RequirementsDraft
    service_design: ServiceDesign | None = None


class GeneratedCode(BaseModel):
    python_code: str = Field(min_length=100, max_length=30000)
    rationale: str


class RunRequest(BaseModel):
    project: ProjectInput
    requirements: RequirementsDraft
    code: str = Field(min_length=100, max_length=30000)
    service_design: ServiceDesign | None = None
    customer_evidence: list[CustomerEvidence] = Field(default_factory=list)
    requirements_revision: int = Field(0, ge=0, le=20)
    parent_run_id: str | None = None


class SeedEvidence(BaseModel):
    seed: int
    dataset_sha256: str
    sandbox_id: str
    status: Literal["completed", "failed"]
    hard_constraint_pass: bool
    score: float | None
    coverage_ratio: float
    elapsed_seconds: float
    violations: list[str]
    stdout: str = ""
    stderr: str = ""
    output_sha256: str | None = None
    sample_plans: list[dict] = Field(default_factory=list)


class CandidateResult(BaseModel):
    name: str
    algorithm: str
    status: Literal["completed", "failed"]
    hard_constraint_pass: bool
    score: float | None
    score_std: float | None = None
    min_score: float | None = None
    coverage_ratio: float
    elapsed_seconds: float
    violations: list[str]
    stdout: str = ""
    stderr: str = ""
    source_sha256: str
    sample_plans: list[dict] = Field(default_factory=list)
    passed_seeds: int
    total_seeds: int
    relative_to_optimal: float | None = None
    relative_to_baseline: float | None = None
    same_plans_as_baseline: int | None = None
    same_plans_as_optimal: int | None = None
    per_seed: list[SeedEvidence] = Field(default_factory=list)


class RepairAttempt(BaseModel):
    """Auditable initial candidate / one repaired candidate result."""
    attempt_index: int
    source_sha256: str
    candidate: CandidateResult
    verdict: str  # NO-GO / HOLD / CONDITIONAL GO / PASS (legacy standalone tests)
    trigger: str = ""  # functional / quality / none
    selected: bool = False
    feedback: str = ""  # deterministic validator feedback fed to Qwen for next revision
    repair_error: str = ""  # if the next revision could not be produced
    repair_strategy: str = "initial"
    error_summary: dict[str, int] = Field(default_factory=dict)
    code_diff: str = ""  # unified diff against previous attempt


class PlanSubjectComparison(BaseModel):
    subject: str
    gap: float
    priority: int
    max_hours: int
    baseline_hours: int | None = None
    optimal_hours: int | None = None
    generated_hours: int | None = None


class PlanComparison(BaseModel):
    seed: int
    student_id: str
    available_hours: int
    generated_valid: bool
    subjects: list[PlanSubjectComparison]


class BusinessScenario(BaseModel):
    monthly_revenue_yen: int
    monthly_operating_cost_yen: int
    monthly_contribution_yen: int
    hypothetical_customer_value_yen: float
    break_even_schools: int | None
    validation_status: str = "仮説のみ・実顧客で未検証"


class RunResponse(BaseModel):
    run_id: str
    created_at: str
    model: str
    seeds: list[int]  # development seeds used for feedback
    holdout_seeds: list[int]
    dataset_hashes: dict[str, str]  # both partitions
    development_baseline: CandidateResult
    development_optimal: CandidateResult
    development_generated: CandidateResult
    baseline: CandidateResult | None = None
    optimal: CandidateResult | None = None
    generated: CandidateResult | None = None
    repair_attempts: list[RepairAttempt] = Field(default_factory=list)
    selected_attempt_index: int | None = None
    holdout_executed: bool = False
    plan_comparisons_source: Literal["holdout", "development"] = "holdout"
    plan_comparisons: list[PlanComparison] = Field(default_factory=list)
    max_repair_attempts: int = 0
    functional_gate: str
    selection_gate: str
    business_gate: str
    gate_reasons: list[str]
    business_scenario: BusinessScenario
    report_markdown: str
    service_design: ServiceDesign | None = None
    customer_evidence: list[CustomerEvidence] = Field(default_factory=list)
    requirement_assessment: RequirementAssessment | None = None
    requirements_revision: int = 0
    parent_run_id: str | None = None
    requirements_sha256: str = ""
    service_design_sha256: str = ""
