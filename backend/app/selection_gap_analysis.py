"""Read-only post-selection generalization audit, never an algorithm selector."""
from __future__ import annotations
VERSION='POST-SELECT-INDEPENDENT-GAP-v0.27.0'


def analyze(*, selected_engine:str|None, dev_audit:dict,
            blind_metrics:dict, random_seed:int)->dict:
    candidates=dev_audit.get('candidate_ranking') or {}
    rows=blind_metrics.get('selected',{}).get('cases') or []
    comparisons=[]
    for name,group in blind_metrics.items():
        if name=='selected': continue
        other=group.get('cases') or []
        a={r['seed']:r for r in rows}
        b={r['seed']:r for r in other}
        aligned=bool(a) and set(a)==set(b) and all(
            a[k].get('input_sha256')==b[k].get('input_sha256') for k in a)
        proved=[k for k in a if aligned and a[k].get('optimality_gap_missed_cases') is not None
                and b[k].get('optimality_gap_missed_cases') is not None]
        wins=sum(a[k]['missed_deadlines']<b[k]['missed_deadlines'] for k in proved)
        losses=sum(a[k]['missed_deadlines']>b[k]['missed_deadlines'] for k in proved)
        ties=len(proved)-wins-losses
        comparisons.append({'candidate':name,'aligned':aligned,'certified_cases':len(proved),
            'selected_better':wins,'selected_worse':losses,'ties':ties,
            'selected_excess_missed':sum(a[k]['missed_deadlines']-b[k]['missed_deadlines'] for k in proved),
            'excluded_uncertified_cases':len(a)-len(proved)})
    losses=sum(row['selected_worse'] for row in comparisons)
    uncertain=(not rows or not comparisons or
               not all(x.get('optimality_gap_missed_cases') is not None for x in rows) or
               any(not c['aligned'] or c['excluded_uncertified_cases'] for c in comparisons))
    return {'version':VERSION,'status':('POST_SELECTION_GAP_DETECTED' if losses else
                                       'INCONCLUSIVE_UNCERTIFIED' if uncertain else
                                       'NO_RELATIVE_GAP_DETECTED_IN_FIXTURES'),
            'selected_engine':selected_engine,'random_seed_root':random_seed,
            'dev_selection_rationale':candidates.get('selected_engine'),
            'dev_selection_rule_consistent':candidates.get('selection_consistent_with_predeclared_dev_order'),
            'comparisons':comparisons,
            'selected_optimal_cases':sum(x.get('optimality_gap_missed_cases')==0 for x in rows),
            'selected_certified_cases':sum(x.get('optimality_gap_missed_cases') is not None for x in rows),
            'change_selected_engine':False,'fed_back_to_model':False,
            'fed_back_to_dev_selection':False,
            'requires_human_review':bool(losses or uncertain),
            'scope':'Read-only after DEV selection; small synthetic randomized cases, objective gaps only when oracle OPTIMAL.'}
