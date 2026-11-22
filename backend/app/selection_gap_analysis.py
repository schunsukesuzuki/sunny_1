"""Read-only, post-selection objective-aligned audit (no DEV/model feedback)."""
from __future__ import annotations

VERSION='POST-SELECT-LEXICOGRAPHIC-GAP-v0.29.0'


def _lex(row:dict):
    if row.get('optimality_gap_missed_cases') is None:
        return None
    missed=row.get('missed_deadlines')
    unassigned=row.get('unassigned')
    if type(missed) is not int or missed<0:
        return None
    return (missed, unassigned if type(unassigned) is int and unassigned>=0 else None)


def analyze(*,selected_engine:str|None,dev_audit:dict,
            blind_metrics:dict,random_seed:int)->dict:
    candidates=(dev_audit.get('candidate_ranking') or {})
    selected_rows=blind_metrics.get('selected',{}).get('cases') or []
    selected={x['seed']:x for x in selected_rows}
    comparisons=[]
    for name,group in blind_metrics.items():
        if name=='selected':
            continue
        other=group.get('cases') or []
        candidate={r['seed']:r for r in other}
        aligned=bool(selected) and len(selected)==len(selected_rows) and len(candidate)==len(other) and set(selected)==set(candidate) and all(
            selected[k].get('input_sha256')==candidate[k].get('input_sha256') for k in selected)
        wins=losses=ties=primary_ties_secondary_losses=primary_ties_secondary_wins=0
        legacy_only=uncertified=0
        excess_primary=excess_secondary=0
        for k in selected:
            a=_lex(selected[k]); b=_lex(candidate.get(k,{}))
            if not aligned or a is None or b is None:
                uncertified+=1
                continue
            excess_primary+=a[0]-b[0]
            if a[0]<b[0]:
                wins+=1
            elif a[0]>b[0]:
                losses+=1
            elif a[1] is None or b[1] is None:
                legacy_only+=1
            else:
                excess_secondary+=a[1]-b[1]
                if a[1]<b[1]:
                    wins+=1
                    primary_ties_secondary_wins+=1
                elif a[1]>b[1]:
                    losses+=1
                    primary_ties_secondary_losses+=1
                else:
                    ties+=1
        comparisons.append({
            'candidate':name,'aligned':aligned,
            'certified_cases':len(selected)-uncertified if aligned else 0,
            'fully_comparable_lexicographic_cases':wins+losses+ties,
            'selected_better':wins,'selected_worse':losses,'ties':ties,
            'primary_ties_secondary_losses':primary_ties_secondary_losses,
            'primary_ties_secondary_wins':primary_ties_secondary_wins,
            'selected_excess_missed':excess_primary,
            'selected_excess_unassigned_on_primary_ties':excess_secondary,
            'excluded_uncertified_cases':uncertified,
            'excluded_secondary_unknown_cases':legacy_only,
            'objective_order':['min_missed_deadlines','min_unassigned_cases']})
    losses=sum(row['selected_worse'] for row in comparisons)
    def _selected_uncertified(row):
        gap=row.get('optimality_gap_missed_cases')
        return gap is None or (gap==0 and row.get('optimality_gap_unassigned_conditional') is None)
    uncertain=(not selected_rows or not comparisons or
       any(_selected_uncertified(row) for row in selected_rows) or
       any(not c['aligned'] or c['excluded_uncertified_cases'] or
           c['excluded_secondary_unknown_cases'] for c in comparisons))
    oracle_gap_cases=sum(
        row.get('optimality_gap_missed_cases',0)>0 or
        (row.get('optimality_gap_missed_cases')==0 and
         (row.get('optimality_gap_unassigned_conditional') or 0)>0)
        for row in selected_rows if row.get('optimality_gap_missed_cases') is not None)
    status=('POST_SELECTION_GAP_DETECTED' if losses else
            'INCONCLUSIVE_UNCERTIFIED' if uncertain else
            'POST_SELECTION_ORACLE_GAP_DETECTED' if oracle_gap_cases else
            'NO_RELATIVE_LEXICOGRAPHIC_GAP_DETECTED_IN_FIXTURES')
    return {'version':VERSION,'status':status,
        'objective_contract':{'order':['min_missed_deadlines','min_unassigned_cases'],
            'feasibility':'Every compared allocation must independently pass constraints',
            'solver_certificate':'OPTIMAL required; FEASIBLE/TIME_LIMIT are inconclusive',
            'secondary':'Compare unassigned only where missed_deadlines tie'},
        'selected_engine':selected_engine,'random_seed_root':random_seed,
        'dev_selection_rationale':candidates.get('selected_engine'),
        'dev_selection_rule_consistent':candidates.get('selection_consistent_with_predeclared_dev_order'),
        'comparisons':comparisons,
        'selected_optimal_cases':sum(x.get('lexicographic_optimal') is True for x in selected_rows),
        'selected_oracle_gap_cases':oracle_gap_cases,
        'selected_primary_optimal_cases':sum(x.get('optimality_gap_missed_cases')==0 for x in selected_rows),
        'selected_certified_cases':sum(x.get('optimality_gap_missed_cases') is not None for x in selected_rows),
        'change_selected_engine':False,'fed_back_to_model':False,
        'fed_back_to_dev_selection':False,'requires_human_review':bool(losses or uncertain or oracle_gap_cases),
        'scope':'Postselection synthetic 08f. Primary+conditional secondary objective; no selection/model feedback or production guarantee.'}
