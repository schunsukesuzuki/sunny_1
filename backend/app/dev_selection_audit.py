"""Predeclared DEV-only comparison. Neither 06 HOLDOUT nor 08f informs selection."""
from __future__ import annotations
VERSION='DEV-LEXICOGRAPHIC-ROBUST-SELECT-v0.28.0'
from . import dev_robustness as drb


def score(metrics:dict, rows:list[dict]) -> tuple[int,int]:
    if not metrics.get('valid') or type(metrics.get('missed_total')) is not int:
        return (10**9,10**9)
    unassigned=sum(int(x.get('unassigned_cases') or 0) for x in rows)
    return (metrics['missed_total'],unassigned)


def compile_candidates(attempts:list[dict], skills:list[dict])->list[dict]:
    rows=[]
    for item in attempts:
        rows.append({'engine':'llm_generated','candidate_id':'llm_attempt_'+str(item['attempt']),
                     'source_sha256':item['code_sha256'],'eligible':item['selection_gate']['eligible'],
                     'dev_score':list(score(item['evaluation'],item.get('metrics',[]))),
                     'gate_reasons':item['selection_gate'].get('reasons',[]),
                     'dev_case_metrics':item.get('metrics',[]),'stress_checks':item.get('stress_checks',[]),
                     'extra_dev_metrics':item.get('robustness_dev_rows',[]),
                     'origin':'LLM_GENERATED'})
    for item in skills:
        rows.append({'engine':item['engine'],'candidate_id':item['engine'],
                     'source_sha256':item['source_sha256'],'eligible':item['selection_gate']['eligible'],
                     'dev_score':list(score(item['dev'],item.get('dev_rows',[]))),
                     'gate_reasons':item['selection_gate'].get('reasons',[]),
                     'dev_case_metrics':item.get('dev_rows',[]),'stress_checks':item.get('stress_checks',[]),
                     'extra_dev_metrics':item.get('robustness_dev_rows',[]),
                     'origin':'PINNED_REVIEWED_DOMAIN_SKILL'})
    return rows


def select(candidates:list[dict], chosen:str|None,*,selected_source_hash:str|None)->dict:
    robust=drb.choose(candidates)
    chosen_id=robust['selected_candidate_id']
    ranking=sorted((dict(c,source_order=i) for i,c in enumerate(candidates) if c['eligible']),
                   key=lambda c:robust['eligible_ranking'].index(c['candidate_id']))
    ideal=next((c for c in ranking if c['candidate_id']==chosen_id),None)
    matched=bool((ideal is None and chosen is None) or
                 (ideal is not None and ideal['engine']==chosen and ideal['source_sha256']==selected_source_hash))
    return {'version':VERSION,'selected_engine':chosen,'selected_source_sha256':selected_source_hash,
            'expected_from_dev':chosen_id,
            'selection_consistent_with_predeclared_dev_order':matched,
            'eligible_ranking':ranking,'all_candidates':candidates,
            'robustness_audit':robust,
            'tie_rule':'DEV missed, DEV unassigned, extra DEV cohort worst/total, pinned stress worst/total, stable source order last.',
            'primary':'DEV aggregate missed deadlines; lower is better',
            'secondary':'DEV unassigned cases; lower is better',
            'post_selection_data_consumed':False,'holdout_used_for_selection':False,
            '08f_used_for_selection':False,
            'scope':'Predeclared synthetic DEV + four additional development shifts + four pinned stress scenarios; no 08f leakage or real-customer guarantees.'}
