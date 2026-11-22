"""Independent, dimension-separated RAW diagnostic rubric reporting (v0.28).

An axis is not promoted because other axes passed. Raw rubric checks are
precomputed by the independent synthetic oracle and are never fed back to the
LLM or used to authorize a requirement change. Retries of blind cases are
explicitly NOT first-pass fresh generalization evidence.
"""
from __future__ import annotations

VERSION = 'RAW-DIAGNOSTIC-AXES-v0.28.0'
AXES = {
    'cause_classification': ('cause_classification',),
    'implementation_correctness': ('implementation_correctness','no_implementation_contradiction'),
    'evidence_quality': ('evidence_traceability','real_world_humility'),
    'revision_action': ('revision_targets_requirement','no_conflicting_revision_policy'),
    'requirement_fit': ('synthetic_business_fit',),
}


def _rubric(trial: dict, *, blind: bool, initial: bool) -> dict:
    if blind:
        return trial.get('rubric') or {}
    if initial:
        return trial.get('initial_rubric') or trial.get('latest_raw_rubric') or {}
    return trial.get('latest_raw_rubric') or trial.get('initial_rubric') or {}


def summarize(benchmark: dict) -> dict:
    groups=[]
    fixed = benchmark.get('trials') or []
    blind_spec = benchmark.get('blind_generalization') or {}
    blind = blind_spec.get('trials') or []
    for name, rows, blind_group, initial in (
        ('fixed_first_raw',fixed,False,True),
        ('fixed_latest_raw',fixed,False,False),
        ('blind_raw',blind,True,False),
    ):
        if name=='blind_raw' and not blind_spec.get('enabled'):
            continue
        for role in ('coding','finance'):
            subset=[r for r in rows if r.get('model_role')==role]
            completed=[r for r in subset if r.get('status')=='COMPLETED' and
                       not (initial and r.get('replayed_after_incomplete'))]
            replay_count=sum(bool(r.get('replayed_after_incomplete')) for r in subset)
            axis_rows={}
            for axis,checks in AXES.items():
                passed=0;failed=0;missing=0
                failed_cases=[]
                for trial in completed:
                    rub=_rubric(trial,blind=blind_group,initial=initial)
                    found=rub.get('checks') or {}
                    results=[found.get(check) for check in checks]
                    if not all(type(result) is bool for result in results):
                        missing+=1
                    elif all(results):
                        passed+=1
                    else:
                        failed+=1
                        failed_cases.append({'case_id':trial.get('case_id'),
                                             'repetition':trial.get('repetition',0),
                                             'failed_checks':[x for x in checks if found.get(x) is False]})
                axis_rows[axis]={
                    'status':('NOT_EVALUATED' if not completed or (passed+failed)==0 else
                              'HOLD' if failed or missing or len(completed)!=len(subset) else 'PASS_SYNTHETIC'),
                    'passed':passed,'failed':failed,'unscored':missing,
                    'planned':len(subset),'completed':len(completed),
                    'checks':list(checks), 'failed_cases':failed_cases,
                }
            semantic=[]
            for trial in completed:
                semantics=(trial.get('initial_raw_semantics') if initial and not blind_group else None) or trial.get('raw_semantics') or {}
                structural=(trial.get('initial_raw_consistency') if initial and not blind_group else None) or trial.get('raw_consistency') or {}
                if type(semantics.get('passed')) is bool and type(structural.get('passed')) is bool:
                    semantic.append(semantics['passed'] and structural['passed'])
                else:
                    semantic.append(None)
            sem_pass=sum(x is True for x in semantic)
            sem_fail=sum(x is False for x in semantic)
            sem_missing=sum(x is None for x in semantic)
            axis_rows['cross_field_consistency']={
                'status':('NOT_EVALUATED' if not completed or sem_pass+sem_fail==0 else
                          'HOLD' if sem_fail or sem_missing or len(completed)!=len(subset) else 'PASS_SYNTHETIC'),
                'passed':sem_pass,'failed':sem_fail,'unscored':sem_missing,
                'planned':len(subset),'completed':len(completed),
                'checks':['raw_consistency.passed','raw_semantics.passed'],
            }
            groups.append({'group':name,'model_role':role,
                'planned':len(subset),'completed':len(completed),'replayed_cases':replay_count,
                'fresh_first_pass':name=='blind_raw' and replay_count==0,
                'usable_for_first_pass_generalization':name=='blind_raw' and replay_count==0 and len(completed)==len(subset) and bool(subset),
                'axes':axis_rows})
    return {'version':VERSION,'benchmark_id':benchmark.get('benchmark_id'),
        'benchmark_execution_status':benchmark.get('status'),
        'groups':groups,
        'raw_only':True,'assisted_outputs_excluded':True,
        'oracle_only_used_in_existing_independent_rubric':True,
        'auto_corrected_diagnosis':False,'production_authorization':False,
        'limitations':'Pass means an individual criterion passed in small synthetic fixtures. Lexical cross-field checks are not proof of semantic truth. Blind replays are not fresh trials; no causal or legal conclusions.'}
