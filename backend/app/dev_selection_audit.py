"""Predeclared DEV-only comparison. Neither 06 HOLDOUT nor 08f informs selection."""
from __future__ import annotations
VERSION='DEV-LEXICOGRAPHIC-SELECT-v0.27.0'


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
                     'origin':'LLM_GENERATED'})
    for item in skills:
        rows.append({'engine':item['engine'],'candidate_id':item['engine'],
                     'source_sha256':item['source_sha256'],'eligible':item['selection_gate']['eligible'],
                     'dev_score':list(score(item['dev'],item.get('dev_rows',[]))),
                     'gate_reasons':item['selection_gate'].get('reasons',[]),
                     'origin':'PINNED_REVIEWED_DOMAIN_SKILL'})
    return rows


def select(candidates:list[dict], chosen:str|None,*,selected_source_hash:str|None)->dict:
    # Stable order from original generation/skill execution; score ties do not
    # depend on randomized post-selection benchmark results.
    ranking=sorted((dict(c,source_order=i) for i,c in enumerate(candidates) if c['eligible']),
                   key=lambda c:(*c['dev_score'],c['source_order']))
    ideal=ranking[0] if ranking else None
    matched=bool((ideal is None and chosen is None) or
                 (ideal is not None and ideal['engine']==chosen and ideal['source_sha256']==selected_source_hash))
    return {'version':VERSION,'selected_engine':chosen,'selected_source_sha256':selected_source_hash,
            'expected_from_dev':ideal['candidate_id'] if ideal else None,
            'selection_consistent_with_predeclared_dev_order':matched,
            'eligible_ranking':ranking,'all_candidates':candidates,
            'tie_rule':'Stable source order: LLM attempts before pinned skills. No post-selection data.',
            'primary':'DEV aggregate missed deadlines; lower is better',
            'secondary':'DEV unassigned cases; lower is better',
            'post_selection_data_consumed':False,'holdout_used_for_selection':False,
            '08f_used_for_selection':False,
            'scope':'DEV synthetic and policy/stress eligibility only. This ranking is not proof of global optimality.'}
