"""Bounded evidence-to-technical-evaluation bridge (v0.18).

An independently testable rule is compiled from explicit human choices. Natural
language and LLM suggestions can NEVER edit evaluator source or thresholds.
Only the *insurance claim assignment synthetic fixture* has an evaluator. This
is not an arbitrary business requirement compiler and does not prove causality.
"""
from __future__ import annotations
from typing import Any

CONTRACT_VERSION='GROUNDED-CLAIMS-CONTRACT-v0.18.0'


def compile_contract(*, requirement:str, evidence_ids:list[str], max_missed:int,
                     min_reduction_pct:int, require_behavioral:bool=True)->dict:
    if not requirement or len(requirement.strip()) < 20: raise ValueError('A substantive reviewed hypothesis is required')
    if not evidence_ids or len(set(evidence_ids)) != len(evidence_ids):raise ValueError('Unique public evidence pointers required')
    if type(max_missed) is not int or max_missed<0 or max_missed>100:raise ValueError('max_missed must be 0..100')
    if type(min_reduction_pct) is not int or not 0<=min_reduction_pct<=100:raise ValueError('min_reduction_pct must be 0..100')
    return {
      'version': CONTRACT_VERSION,
      'hypothesis':requirement.strip(), 'evidence_ids':list(evidence_ids),
      'domain':'insurance_claims', 'kpi':'missed_deadlines_including_unassigned',
      'thresholds':{'max_total_missed':max_missed,'min_reduction_vs_fifo_pct':min_reduction_pct,
                    'require_behavioral_probes':require_behavioral},
      'constraints':['no_capacity_violations','qualified_reviewer_only','same_planned_assigned_hours'],
      'evaluator':'PINNED_DETERMINISTIC_SYNTHETIC_HOLDOUT',
      'evaluator_mutable_by_llm':False,
      'scope':'HUMAN_SELECTED_HYPOTHESIS_SYNTHETIC_TEST_ONLY',
      'causation':'UNVERIFIED', 'customer_approval':'NOT_OBTAINED',
      'limitation':'Thresholds chosen by human; synthetic cases are NOT generated from published customer documents. No independent proof that FIFO caused public complaints.'}


def evaluate(contract:dict, experiment:dict, policy:dict|None)->dict:
    """Independent, pure report. Fail-closed on missing/mismatched results."""
    h=experiment.get('holdout') or {}
    fifo=h.get('fifo') or []
    gen=h.get('generated') or []
    reasons=[]
    if not fifo or not gen or len(fifo)!=len(gen):reasons.append('Missing or unmatched HOLDOUT rows')
    f_by={row.get('seed'):row for row in fifo}
    g_by={row.get('seed'):row for row in gen}
    if len(f_by)!=len(fifo) or len(g_by)!=len(gen) or set(f_by)!=set(g_by):reasons.append('HOLDOUT seed identity mismatch')
    rows_valid=bool(not reasons and experiment.get('holdout_executed') is True)
    if rows_valid:
        for seed in f_by:
            a,b=f_by[seed],g_by[seed]
            for row in (a,b):
                if (row.get('valid') is not True or type(row.get('missed_deadlines')) not in (int,float)
                    or type(row.get('assigned_hours')) not in (int,float) or row.get('missed_deadlines',-1)<0
                    or row.get('assigned_hours',-1)<0):
                    reasons.append('Invalid HOLDOUT row'); rows_valid=False;break
            if not rows_valid:break
            if a['assigned_hours']!=b['assigned_hours']:
                reasons.append('Planned assigned hours changed'); rows_valid=False
    f_total=sum(row['missed_deadlines'] for row in fifo) if rows_valid else None
    g_total=sum(row['missed_deadlines'] for row in gen) if rows_valid else None
    reduction=((f_total-g_total)*100/f_total if f_total else (0 if rows_valid and g_total==0 else None)) if rows_valid else None
    p_results=(policy or {}).get('results') or {}
    behavior_ok=bool(policy and policy.get('status')=='COMPLETED' and p_results.get('behavior_pass') is True)
    constraints_ok=bool(rows_valid and all(x.get('valid') is True for x in gen))
    met_threshold=bool(rows_valid and g_total<=contract['thresholds']['max_total_missed'] and reduction is not None and reduction>=contract['thresholds']['min_reduction_vs_fifo_pct'])
    if not met_threshold:reasons.append('Human-selected KPI threshold unmet or unverified')
    if contract['thresholds']['require_behavioral_probes'] and not behavior_ok:reasons.append('Behavioral specification probes HOLD')
    if not constraints_ok:reasons.append('Synthetic assignment constraints not confirmed')
    passed=bool(met_threshold and constraints_ok and (behavior_ok or not contract['thresholds']['require_behavioral_probes']))
    return {'version':CONTRACT_VERSION,'status':'SUPPORTED_SYNTHETIC' if passed else 'HOLD',
      'synthetic_pass':passed,'provenance':'DETERMINISTIC_SYNTHETIC_EVALUATION',
      'contract_version':contract['version'],'contract_evidence_ids':contract['evidence_ids'],
      'measured':{'fifo_total_missed':f_total,'generated_total_missed':g_total,
                  'reduction_pct':reduction,'equal_assigned_hours':rows_valid,'behavioral_pass':behavior_ok},
      'thresholds':contract['thresholds'], 'reasons':reasons,
      'claim':'Evaluates a user-configured KPI threshold on FIXED synthetic claims cases; no causal or customer validity is inferred.'}


def spec_md(contract:dict)->str:
    t=contract['thresholds']
    return '\n'.join([
        '# Human-configured evidence-to-experiment test contract — v0.18','',
        '## Scope and origin',
        '- Published problem context is not a customer-approved requirement.',
        f"- Human-edited hypothesis: {contract['hypothesis']}",
        f"- Public evidence pointers: {', '.join(contract['evidence_ids'])}",
        '- Executable target: fixed synthetic insurance claims assignment, **not** the published case.',
        '- Data model, assignment code, and oracle are NOT generated from the natural-language hypothesis.','',
        '## Decision criteria (human-selected, machine-checked)','',
        f"- Total missed deadlines INCLUDING unassigned cases <= **{t['max_total_missed']}**",
        f"- Reduction against FIFO >= **{t['min_reduction_vs_fifo_pct']}%**",
        f"- Require synthetic behavioral probes: **{t['require_behavioral_probes']}**",
        '- Enforce assigned hours equality, valid reviewer qualifications and capacity constraints.','',
        '## Known uncertainty','',
        'Topic relevance ≠ evidence support ≠ requirements correctness.',
        'No public source proves that the above scheduling thresholds or FIFO assumptions describe real customer operations.',
        'An independent real-data evaluation contract requires customer datasets, agreed acceptance tests and additional validators.',''])
