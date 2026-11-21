"""v0.14: independent behavioral contract probes and synthetic stress scenarios.

No model-generated test data or grader is used; this module is independent of the LLM.
Run selected code in E2B separately, after the original DEV/HOLDOUT selection,
and never feed results back into a model or modify historical evaluations.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any
from .domain import make_dataset, validate, sha256

VERSION = 'POLICY-BEHAVIOR-v0.14.0'
STRESS_VERSION = 'STRESS-FIXTURES-v0.14.0'


def _case(cid: str, skill: str, due: int, arrival: int) -> dict:
    return {'case_id':cid, 'required_skill':skill, 'duration_hours':1,
            'deadline_day':due, 'arrival_order':arrival,
            'amount_eur':1000, 'business_priority':1}


def _reviewer(name: str, skills: list[str], capacity: list[int]) -> dict:
    return {'reviewer_id':name, 'skills':skills, 'daily_capacity_hours':capacity}


def policy_probes() -> dict[int, dict]:
    """Behavioral *examples*, not general proofs of optimization or semantics."""
    return {
        900001: {'seed':900001, 'scenario':'deadline_risk_probe', 'schema_version':'claims-0.8', 'days':2,
                 'reviewers':[_reviewer('R-A',['motor'],[1,1])],
                 'cases':[_case('FLEX','motor',1,1),_case('URGENT','motor',0,2)]},
        900002: {'seed':900002, 'scenario':'scarce_qualification_probe', 'schema_version':'claims-0.8', 'days':1,
                 'reviewers':[_reviewer('R-A',['motor','property'],[1]),_reviewer('R-B',['motor'],[1])],
                 'cases':[_case('COMMON','motor',0,1),_case('SCARCE','property',0,2)]},
    }


def evaluate_probe(dataset: dict, output: Any, error: str | None = None) -> dict:
    base=validate(dataset,output,policy='r1')
    scenario=dataset['scenario']
    assignments={row.get('case_id'):row for row in (output or {}).get('assignments',[])
                 if isinstance(row,dict)} if isinstance(output,dict) else {}
    checks={}
    if scenario=='deadline_risk_probe':
        checks['urgent_served_on_due_day'] = bool(assignments.get('URGENT',{}).get('day')==0)
        checks['both_cases_served'] = set(assignments)=={'URGENT','FLEX'}
    elif scenario=='scarce_qualification_probe':
        checks['scarce_case_uses_sole_specialist'] = assignments.get('SCARCE',{}).get('reviewer_id')=='R-A'
        checks['common_case_preserves_specialist_capacity'] = assignments.get('COMMON',{}).get('reviewer_id')=='R-B'
        checks['all_cases_served'] = set(assignments)=={'COMMON','SCARCE'}
    else:
        raise ValueError('Unknown fixture')
    if error: checks['sandbox_execution'] = False
    return {'seed':dataset['seed'],'scenario':scenario,'dataset_sha256':sha256(dataset),
            'valid':base['valid'],'checks':checks,'pass':base['valid'] and all(checks.values()),
            'missed_deadlines':base['missed_deadlines'], 'unassigned_cases':base.get('unassigned_cases'),
            'violations':base['violations'],'execution_error':error}


def stress_scenarios(seed: int = 8731) -> dict[int, dict]:
    """Pinned synthetic perturbations: not customer or operational distributions."""
    result={}
    kinds=['capacity_pressure','skill_bottleneck','deadline_compression','arrival_reordering']
    for offset, kind in enumerate(kinds):
        num=910000+offset
        ds=deepcopy(make_dataset(seed+offset))
        ds['seed']=num
        ds['scenario']=kind
        if kind=='capacity_pressure':
            for rev in ds['reviewers']:
                rev['daily_capacity_hours']=[max(1,x-2) for x in rev['daily_capacity_hours']]
        elif kind=='skill_bottleneck':
            for rev in ds['reviewers']:
                if rev['reviewer_id']=='R-C':
                    rev['daily_capacity_hours']=[max(1,x-3) for x in rev['daily_capacity_hours']]
        elif kind=='deadline_compression':
            for case in ds['cases']:
                case['deadline_day']=max(0,case['deadline_day']-1)
        elif kind=='arrival_reordering':
            for i, case in enumerate(reversed(ds['cases'])):
                case['arrival_order']=i+1
        result[num]=ds
    return result


def metric_summary(dataset: dict, output: Any, error: str | None = None) -> dict:
    m=validate(dataset,output,policy='r1')
    if error:
        m['valid']=False
        m['violations'].append(error)
    return {'valid':m['valid'],'missed':m['missed_deadlines'],
            'unassigned':m.get('unassigned_cases'),'assigned_hours':m.get('assigned_hours'),
            'total_cases':m['total_cases'], 'planned_capacity_hours':m['planned_capacity_hours'],
            'violations':m['violations'][:10]}


def compile_results(probe_datasets: dict[int,dict], probe_runs: list,
                    stress_datasets:dict[int,dict], stress_runs:dict[str,list]) -> dict:
    by_seed={row.seed:row for row in probe_runs}
    checks=[evaluate_probe(ds,by_seed[s].output,by_seed[s].error) for s,ds in probe_datasets.items()]
    stress=[]
    by_approach={k:{row.seed:row for row in v} for k,v in stress_runs.items()}
    for seed,ds in stress_datasets.items():
        values={role:metric_summary(ds,by_approach[role][seed].output,by_approach[role][seed].error)
                for role in ('fifo','deadline','generated')}
        gm=values['generated']; ref=values['deadline']
        # The reference is a fixed heuristic, not an optimality oracle.
        potential_regression=bool(gm['valid'] and ref['valid'] and (
            gm['missed']>ref['missed'] or gm['unassigned']>ref['unassigned']))
        stress.append({'scenario':ds['scenario'],'seed':seed,'dataset_sha256':sha256(ds),
                       'by_method':values,'potential_regression_vs_fixed_heuristic':potential_regression})
    behavior=all(x['pass'] for x in checks)
    valid=all(x['by_method']['generated']['valid'] for x in stress)
    regressions=sum(x['potential_regression_vs_fixed_heuristic'] for x in stress)
    return {'version':VERSION,'stress_version':STRESS_VERSION,
            'scope':'SYNTHETIC_FIXED_BEHAVIOR_PROBES_ONLY',
            'probes':checks,'behavior_pass':behavior,
            'stress_scenarios':stress,'stress_all_constraints_valid':valid,
            'stress_regressions_vs_reference':regressions,
            'stress_review':'REVIEW_REQUIRED' if not valid or regressions else 'NO_REGRESSION_DETECTED_IN_FIXTURES',
            'caveat':'Two behavioral probes cannot prove semantic compliance. Reference is heuristic. No real customer validation.'}


def markdown(record:dict)->str:
    x=record['results']; lines=['# R1 Policy & Stress Validation — v0.14','',
    '> 固定した合成反例とストレスシナリオによる追加評価。形式証明・本番保証・最適性の証明ではありません。','',
    f"- Validation ID: `{record['validation_id']}`",f"- Experiment ID: `{record['experiment_id']}`",
    f"- Source SHA256: `{record['selected_code_sha256']}`",
    f"- Behavioral contract probes: **{'PASS' if x['behavior_pass'] else 'HOLD'}**",
    f"- Stress validity: **{'PASS' if x['stress_all_constraints_valid'] else 'HOLD'}**",
    f"- Stress heuristic comparisons: **{x['stress_review']}**",'',
    '## Behavioral probes','', '| scenario | pass | independent checks | missed | unassigned |',
    '|---|---|---|---:|---:|']
    for q in x['probes']:
        lines.append(f"|{q['scenario']}|{q['pass']}|{', '.join(k+':'+str(v) for k,v in q['checks'].items())}|{q['missed_deadlines']}|{q['unassigned_cases']}|")
    lines.extend(['','## Synthetic stress scenarios','','| scenario | method | missed incl. unassigned | unassigned | assigned hours | constraints |', '|---|---|---:|---:|---:|---|'])
    for scenario in x['stress_scenarios']:
        for k,m in scenario['by_method'].items():
            lines.append(f"|{scenario['scenario']}|{k}|{m['missed']}|{m['unassigned']}|{m['assigned_hours']}|{'PASS' if m['valid'] else 'HOLD'}|")
    lines.extend(['',f"- Reference regressions in scenarios: {x['stress_regressions_vs_reference']}",
        '- 未割当は期限超過に含めます。総稼働量の減少だけを改善と見なしません。',
        '- 固定参照は数学的な最適解ではありません。HOLDOUTでのKPI改善と仕様に沿う振る舞いは別の評価です。',
        '- 各入力・E2B出力・制約検証結果は同梱JSONに記録しています。',''])
    return '\n'.join(lines)
