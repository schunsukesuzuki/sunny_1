export type BusinessInputs = {
  monthly_price_yen: number
  paying_schools: number
  monthly_operating_cost_yen: number
  hours_saved_per_school: number
  teacher_hourly_cost_yen: number
}
export type ProjectInput = {
  title: string
  brief: string
  business: BusinessInputs
  seed: number
  students_count: number
  evaluation_seeds: number
  holdout_seeds: number
  min_quality_ratio: number
  min_improvement_ratio: number
  max_repair_attempts: number
}
export type RequirementsDraft = {
  customer_problem: string
  target_users: string[]
  value_hypothesis: string
  must_have: string[]
  acceptance_criteria: string[]
  unverified_assumptions: string[]
  unanswered_questions: string[]
  next_customer_validation: string[]
}
export type GeneratedCode = { python_code: string; rationale: string }
export type SeedEvidence = {
  seed: number
  dataset_sha256: string
  sandbox_id: string
  status: 'completed' | 'failed'
  hard_constraint_pass: boolean
  score: number | null
  coverage_ratio: number
  elapsed_seconds: number
  violations: string[]
  stdout: string
  stderr: string
  output_sha256: string | null
  sample_plans: Array<{student_id: string; allocations: Array<{subject: string; hours: number}>}>
}
export type CandidateResult = {
  name: string
  algorithm: string
  status: 'completed' | 'failed'
  hard_constraint_pass: boolean
  score: number | null
  score_std: number | null
  min_score: number | null
  coverage_ratio: number
  elapsed_seconds: number
  violations: string[]
  stderr: string
  stdout: string
  source_sha256: string
  sample_plans: SeedEvidence['sample_plans']
  passed_seeds: number
  total_seeds: number
  relative_to_optimal: number | null
  relative_to_baseline: number | null
  same_plans_as_baseline: number | null
  same_plans_as_optimal: number | null
  per_seed: SeedEvidence[]
}
export type RepairAttempt = {
  attempt_index: number
  source_sha256: string
  candidate: CandidateResult
  verdict: string
  trigger: string
  selected: boolean
  feedback: string
  repair_error: string
  repair_strategy: string
  error_summary: Record<string, number>
  code_diff: string
}
export type PlanComparison = {
  seed: number
  student_id: string
  available_hours: number
  generated_valid: boolean
  subjects: Array<{
    subject: string
    gap: number
    priority: number
    max_hours: number
    baseline_hours: number | null
    optimal_hours: number | null
    generated_hours: number | null
  }>
}
export type RunResult = {
  run_id: string
  created_at: string
  model: string
  seeds: number[]
  holdout_seeds: number[]
  development_baseline: CandidateResult
  development_optimal: CandidateResult
  development_generated: CandidateResult
  dataset_hashes: Record<string, string>
  baseline: CandidateResult | null
  optimal: CandidateResult | null
  generated: CandidateResult | null
  repair_attempts: RepairAttempt[]
  max_repair_attempts: number
  selected_attempt_index: number | null
  holdout_executed: boolean
  plan_comparisons_source: "holdout" | "development"
  plan_comparisons: PlanComparison[]
  functional_gate: string
  selection_gate: string
  business_gate: string
  gate_reasons: string[]
  business_scenario: {
    monthly_revenue_yen: number
    monthly_operating_cost_yen: number
    monthly_contribution_yen: number
    hypothetical_customer_value_yen: number
    break_even_schools: number | null
    validation_status: string
  }
  report_markdown: string
  service_design: ServiceDesign | null
  customer_evidence: CustomerEvidence[]
  requirement_assessment: RequirementAssessment | null
  requirements_revision: number
  parent_run_id: string | null
  requirements_sha256: string
  service_design_sha256: string
}
export type Health = {
  api: string
  version: string
  model: string
  ollama: { reachable: boolean; installed: boolean; models: string[] }
  e2b_configured: boolean
  sandbox: string
}

export type ServiceDesign = {
  design_source: string
  product_scope: string
  actors: string[]
  use_cases: string[]
  domain_entities: string[]
  service_flow: string[]
  hard_constraints: string[]
  soft_objectives: string[]
  interfaces: string[]
  acceptance_tests: string[]
  alternatives: string[]
  assumptions: string[]
  external_validation_needed: string[]
}
export type CustomerEvidence = {
  evidence_id: string
  requirement_id: string
  provenance: 'synthetic' | 'real_customer' | 'stakeholder' | 'desk_research'
  verdict: 'support' | 'contradict' | 'inconclusive'
  observation: string
  source_reference: string
  human_verified: boolean
  reviewer: string
}
export type RequirementAssessment = {
  implementation_validity: 'PASS' | 'FAIL'
  requirement_validity: 'UNVERIFIED' | 'SUPPORTED_PRELIMINARY' | 'REJECTED_PRELIMINARY' | 'CONFLICTED'
  findings: Array<{
    requirement_id: string
    criterion: string
    status: string
    admissible_evidence_ids: string[]
    excluded_evidence_ids: string[]
    rationale: string
  }>
  evidence_count: number
  next_customer_validation: string[]
  decision: string
  note: string
}
export type RequirementRefinementProposal = {
  prior_run_id: string
  proposed_requirements: RequirementsDraft
  diagnosis: string[]
  change_reasons: string[]
  unresolved_evidence: string[]
  proposed_validation: string[]
  status: string
}
