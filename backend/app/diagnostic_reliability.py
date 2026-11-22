"""v0.26: independent RAW quality hold vs transport/execution completeness.

Synthetic fixture screening only, never legal/customer or production certification.
Assisted evidence binding is excluded from model pass counts. Incomplete model
calls do not count as wrong model judgments; nor do they count as passes.
"""
from __future__ import annotations

VERSION='DIAGNOSTIC-RELIABILITY-GATE-v0.27.0'


def assess(benchmark: dict) -> dict:
    summaries=benchmark.get('summary',{})
    blind=benchmark.get('blind_generalization') or {}
    blind_summary=blind.get('summary') or {}
    quality_issues=[]
    execution_issues=[]
    per_model={}
    for role in ('coding','finance'):
        row=summaries.get(role) or {}
        fresh=blind_summary.get(role) or {}
        planned=int(row.get('planned') or 0)
        completed=int(row.get('completed') or 0)
        passed=int(row.get('raw_final_passed') or 0)
        blind_planned=int(fresh.get('planned') or 0)
        blind_completed=int(fresh.get('completed') or 0)
        blind_passed=int(fresh.get('passed') or 0)
        if planned < 2: quality_issues.append(f'{role.upper()}_FIXED_INSUFFICIENT_CASES')
        if passed < completed: quality_issues.append(f'{role.upper()}_RAW_FIXED_DIAGNOSIS_FAILURE')
        if completed != planned: execution_issues.append(f'{role.upper()}_FIXED_INCOMPLETE')
        if not blind.get('enabled') or blind_planned < 2:
            quality_issues.append(f'{role.upper()}_BLIND_NOT_QUALIFIED')
        if blind_passed < blind_completed:
            quality_issues.append(f'{role.upper()}_RAW_BLIND_DIAGNOSIS_FAILURE')
        if blind.get('enabled') and blind_completed != blind_planned:
            execution_issues.append(f'{role.upper()}_BLIND_INCOMPLETE')
        # Older records may not have structural checks; do not treat absence as green.
        fixed_struct=[t.get('raw_consistency',{}) for t in benchmark.get('trials',[]) if t.get('model_role')==role and t.get('status')=='COMPLETED']
        blind_struct=[t.get('raw_consistency',{}) for t in blind.get('trials',[]) if t.get('model_role')==role and t.get('status')=='COMPLETED']
        if any(x.get('passed') is False for x in fixed_struct+blind_struct):
            quality_issues.append(f'{role.upper()}_CROSS_FIELD_INCONSISTENCY')
        semantic=[t.get('raw_semantics',{}) for t in benchmark.get('trials',[]) if t.get('model_role')==role and t.get('status')=='COMPLETED'] + [t.get('raw_semantics',{}) for t in blind.get('trials',[]) if t.get('model_role')==role and t.get('status')=='COMPLETED']
        if any(x.get('passed') is False for x in semantic):
            quality_issues.append(f'{role.upper()}_SEMANTIC_BOUNDARY_INCONSISTENCY')
        if any(t.get('replayed_after_incomplete') for t in blind.get('trials',[]) if t.get('model_role')==role):
            quality_issues.append(f'{role.upper()}_BLIND_REPLAY_NOT_FRESH')
        per_model[role]={
            'model_id':row.get('model'),'fixed_raw_passed':passed,'fixed_total':planned,
            'fixed_completed':completed,'blind_raw_passed':blind_passed,'blind_total':blind_planned,
            'blind_completed':blind_completed,'assisted_passes_not_substituted':True,
            'timeout_calls':int(row.get('timeout_calls') or 0)+int(fresh.get('timeout_calls') or 0),
        }
    all_trials=benchmark.get('trials',[])+blind.get('trials',[])
    timeouts=sum(x.get('status')=='INCOMPLETE_TIMEOUT' for x in all_trials)
    if timeouts: execution_issues.append('INCOMPLETE_TIMEOUT')
    for x in all_trials:
        if x.get('status') not in ('COMPLETED','INCOMPLETE_TIMEOUT'):
            execution_issues.append(x.get('status') or 'UNKNOWN_EXECUTION_ERROR')
    if benchmark.get('status')!='COMPLETED':
        execution_issues.append('BENCHMARK_INCOMPLETE')
    execution_issues=list(dict.fromkeys(execution_issues))
    quality_issues=list(dict.fromkeys(quality_issues))
    return {
        'version':VERSION,
        'status':'PASS_SYNTHETIC_SCREEN' if not (quality_issues or execution_issues) else 'HOLD_HUMAN_ADJUDICATION',
        'quality_status':'HOLD_HUMAN_ADJUDICATION' if quality_issues else ('NOT_YET_EVALUABLE' if execution_issues else 'PASS_SYNTHETIC_SCREEN'),
        'execution_status':'COMPLETE' if not execution_issues else ('INCOMPLETE_TIMEOUT' if timeouts else 'INCOMPLETE_EXECUTION'),
        'human_adjudication_required':bool(quality_issues or execution_issues),
        'autonomous_diagnostic_reliability':False,'no_unattended_requirement_rewrite':True,
        'no_auto_repair_from_blind_oracle':True,
        'predeclared_criteria':'Both models: >=2 fixed and >=2 fresh blind synthetic cases; all calls completed; 100% RAW rubric PASS and cross-field consistency. Replayed blind calls are not fresh.',
        'models':per_model,
        'quality_failure_codes':quality_issues,
        'execution_failure_codes':execution_issues,
        'failure_codes':quality_issues+execution_issues,
        'scope':'Small synthetic screen; no statistical, legal or real-customer validation',
        'next_action':'Human reviews original RAW diagnosis and code-vs-contract evidence. Retry only incomplete calls with saved model/input; do not overwrite completed failures.' if quality_issues or execution_issues else 'Retain human review for any real requirement change',
        'production_authorization':False,
    }
