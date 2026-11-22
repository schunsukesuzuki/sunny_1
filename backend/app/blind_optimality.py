"""v0.21 post-selection, independent randomized scheduling comparisons.

Never consumed by R1 generation/repair, DEV selection, or diagnostic prompts.
The exact solver labels OPTIMAL *only* when the search is proven exhaustive or
OR-Tools CP-SAT returns OPTIMAL. FEASIBLE / TIME_LIMIT are not certificates.
"""
from __future__ import annotations

from collections import defaultdict
import random
import secrets
import time
from typing import Any

from .domain import validate, sha256

VERSION = 'BLIND-OPTIMALITY-v0.29.0'


def fresh_blind_seed() -> int:
    return secrets.randbits(31)


def randomized_suite(seed_root: int, count: int = 4) -> dict[int, dict]:
    if not 2 <= count <= 8:
        raise ValueError('Blind evaluation requires 2..8 cases')
    rng = random.Random(seed_root)
    data = {}
    for i in range(count):
        seed = 2_000_000 + i
        # Each scenario has a distinct skill structure, duration mix and caps.
        reviewers = [
            {'reviewer_id': 'R-A', 'skills': ['motor','property'],
             'daily_capacity_hours': [rng.randint(1,3),rng.randint(1,3)]},
            {'reviewer_id': 'R-B', 'skills': ['motor'],
             'daily_capacity_hours': [rng.randint(1,3),rng.randint(1,3)]},
            {'reviewer_id': 'R-C', 'skills': ['property','liability'],
             'daily_capacity_hours': [rng.randint(1,3),rng.randint(1,3)]},
        ]
        cases=[]
        for j in range(rng.randint(5,6)):
            skill=rng.choice(['motor','property','liability'])
            cases.append({'case_id':f'BL{i:02d}-{j:02d}', 'arrival_order':j+1,
                'required_skill':skill, 'duration_hours':rng.randint(1,2),
                'deadline_day':rng.choice([0,0,1]), 'business_priority':rng.randint(1,5),
                'amount_eur':rng.randint(5,50)*100})
        # Nontrivial arrival-order reversal; no case identifiers from DEV fixtures.
        rng.shuffle(cases)
        for rank,c in enumerate(cases): c['arrival_order']=rank+1
        data[seed]={'schema_version':'claims-0.8','days':2,'seed':seed,
             'scenario':'BLIND_RANDOMIZED_POST_SELECTION', 'cases':cases, 'reviewers':reviewers}
    return data


def _objective(ds:dict,out:dict) -> tuple[int,int]:
    metrics=validate(ds,out,policy='r1')
    if not metrics['valid']:
        raise ValueError('Exact candidate failed independent validation')
    return (metrics['on_time'],metrics['completed'])


def enumeration_exact(ds:dict, max_nodes:int=350_000) -> dict:
    """Exhaustive, capacity-aware small-case enumeration. No false optimality."""
    if len(ds['cases'])>7:
        return {'status':'SKIPPED_SIZE_LIMIT','solver':'PYTHON_EXHAUSTIVE', 'solution':None}
    cases=sorted(ds['cases'],key=lambda c:(c['deadline_day'],c['required_skill'],c['case_id']))
    reviewers=ds['reviewers']
    slots=[(r['reviewer_id'],day) for r in reviewers for day in range(ds['days'])]
    remain={k:next(r['daily_capacity_hours'][k[1]] for r in reviewers if r['reviewer_id']==k[0]) for k in slots}
    candidates={c['case_id']:[(r['reviewer_id'],day) for day in range(ds['days']) for r in reviewers
             if c['required_skill'] in r['skills'] and r['daily_capacity_hours'][day]>=c['duration_hours']]
             for c in cases}
    best=(-1,-1);best_assignment=None; nodes=0;stopped=False
    current=[];unassigned=[]

    def search(i:int,ontime:int,assigned:int):
        nonlocal best,best_assignment,nodes,stopped
        nodes+=1
        if nodes>max_nodes:
            stopped=True;return
        if ontime+len(cases)-i<best[0]:return
        if ontime+len(cases)-i==best[0] and assigned+len(cases)-i<best[1]:return
        if i==len(cases):
            score=(ontime,assigned)
            if score>best:
                best=score;best_assignment=(list(current),list(unassigned))
            return
        c=cases[i]; cid=c['case_id']; hours=c['duration_hours']
        choices=sorted(candidates[cid],key=lambda slot:(slot[1]>c['deadline_day'],slot[1],slot[0]))
        for rid,day in choices:
            if remain[(rid,day)]<hours:continue
            remain[(rid,day)]-=hours
            current.append({'case_id':cid,'reviewer_id':rid,'day':day,'hours':hours})
            search(i+1,ontime+int(day<=c['deadline_day']),assigned+1)
            current.pop();remain[(rid,day)]+=hours
            if stopped:return
        unassigned.append(cid)
        search(i+1,ontime,assigned)
        unassigned.pop()

    began=time.monotonic();search(0,0,0)
    out={'assignments':best_assignment[0], 'unassigned_case_ids':best_assignment[1]} if best_assignment else None
    return {'status':'TIME_LIMIT' if stopped else 'OPTIMAL', 'solver':'PYTHON_EXHAUSTIVE',
            'solution':out, 'nodes':nodes, 'objective':best if out else None,
            'elapsed_seconds':round(time.monotonic()-began,4)}


def cp_sat_exact(ds:dict, *, limit_seconds:float=3.0) -> dict:
    """Optional OR-Tools benchmark. Proof only for CP-SAT OPTIMAL."""
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        return {'status':'UNAVAILABLE_DEPENDENCY','solver':'OR_TOOLS_CP_SAT','solution':None}
    model=cp_model.CpModel(); xs={}; bycase=defaultdict(list);bycap=defaultdict(list)
    for c in ds['cases']:
        for rev in ds['reviewers']:
            if c['required_skill'] not in rev['skills']:continue
            for day in range(ds['days']):
                if rev['daily_capacity_hours'][day]<c['duration_hours']:continue
                key=(c['case_id'],rev['reviewer_id'],day)
                v=model.NewBoolVar(f'x_{len(xs)}');xs[key]=v
                bycase[c['case_id']].append(v)
                bycap[(rev['reviewer_id'],day)].append((v,c['duration_hours']))
    for c in ds['cases']:model.Add(sum(bycase[c['case_id']])<=1)
    for rev in ds['reviewers']:
        for day in range(ds['days']):
            model.Add(sum(v*h for v,h in bycap[(rev['reviewer_id'],day)])<=rev['daily_capacity_hours'][day])
    n=len(ds['cases']); case_dict={c['case_id']:c for c in ds['cases']}
    primary=sum(v for (cid,rid,day),v in xs.items() if day<=case_dict[cid]['deadline_day'])
    secondary=sum(xs.values())
    model.Maximize((n+1)*primary+secondary)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=limit_seconds
    solver.parameters.num_search_workers=1;solver.parameters.random_seed=421
    began=time.monotonic();status=solver.Solve(model)
    label=('OPTIMAL' if status==cp_model.OPTIMAL else 'FEASIBLE' if status==cp_model.FEASIBLE
         else 'INFEASIBLE' if status==cp_model.INFEASIBLE else 'UNKNOWN')
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        return {'status':label,'solver':'OR_TOOLS_CP_SAT','solution':None,
                'elapsed_seconds':round(time.monotonic()-began,4)}
    assignments=[{'case_id':cid,'reviewer_id':rid,'day':day,'hours':case_dict[cid]['duration_hours']}
                 for (cid,rid,day),v in xs.items() if solver.Value(v)]
    assigned={a['case_id'] for a in assignments}
    out={'assignments':assignments,'unassigned_case_ids':[c['case_id'] for c in ds['cases'] if c['case_id'] not in assigned]}
    return {'status':label,'solver':'OR_TOOLS_CP_SAT','solution':out,
            'objective':_objective(ds,out),'best_objective_bound':solver.BestObjectiveBound(),
            'elapsed_seconds':round(time.monotonic()-began,4)}


def exact_baseline(ds:dict) ->dict:
    cp=cp_sat_exact(ds)
    # CP-SAT is preferred; if absent, small instances use exhaustive search.
    result=cp if cp['status'] in ('OPTIMAL','FEASIBLE') else enumeration_exact(ds)
    if result['solution'] is not None:
        result['metrics']=validate(ds,result['solution'],policy='r1')
    result['cp_sat_status']=cp['status'];result['input_sha256']=sha256(ds)
    return result


def summarize(suite:dict[int,dict],runs:dict[str,list],optima:dict[int,dict])->dict:
    """Read-only 08f score: minimize (missed_deadlines, unassigned_cases).

    A secondary-objective gap is meaningful ONLY at the proven primary optimum.
    CP-SAT FEASIBLE and interrupted enumeration never certify either gap.
    """
    result={}
    for name,series in runs.items():
        byseed={r.seed:r for r in series}
        rows=[]
        for seed,ds in suite.items():
            raw=byseed.get(seed)
            if raw is None:
                metrics={'valid':False,'violations':['Missing sandbox execution'],
                         'missed_deadlines':None,'unassigned_cases':None}
            else:
                metrics=validate(ds,raw.output,policy='r1')
                if raw.error:
                    metrics['valid']=False
                    metrics['violations'].append(str(raw.error)[:200])
            ex=optima[seed]
            certified=(metrics['valid'] is True and ex['status']=='OPTIMAL' and
                       isinstance(ex.get('metrics'),dict) and ex['metrics'].get('valid') is True)
            missed_gap=(metrics['missed_deadlines']-ex['metrics']['missed_deadlines'] if certified else None)
            # Unassigned cannot be compared as an 'optimality gap' when the
            # candidate has a worse primary objective, even if it assigns more.
            secondary_gap=(metrics['unassigned_cases']-ex['metrics']['unassigned_cases']
                           if certified and missed_gap==0 else None)
            lex_optimal=bool(certified and missed_gap==0 and secondary_gap==0)
            rows.append({'seed':seed,'input_sha256':sha256(ds),'valid':metrics['valid'],
                'missed_deadlines':metrics.get('missed_deadlines'),
                'unassigned':metrics.get('unassigned_cases'),
                'optimality_gap_missed_cases':missed_gap,  # legacy, primary-only
                'optimality_gap_unassigned_conditional':secondary_gap,
                'lexicographic_optimal':lex_optimal if certified else None,
                'exact_optimal_missed':ex['metrics']['missed_deadlines'] if certified else None,
                'exact_optimal_unassigned':ex['metrics']['unassigned_cases'] if certified else None,
                'exact_status':ex['status'],
                'execution_seconds':getattr(raw,'elapsed_seconds',None)})
        certified_rows=[x for x in rows if x['optimality_gap_missed_cases'] is not None]
        result[name]={'cases':rows,'valid_count':sum(x['valid'] for x in rows),
            'proven_optimal_cases':sum(x['lexicographic_optimal'] is True for x in rows),
            'primary_optimal_cases':sum(x['optimality_gap_missed_cases']==0 for x in certified_rows),
            'certified_lexicographic_cases':sum(x['lexicographic_optimal'] is True for x in rows),
            'total_proven_gap':sum(x['optimality_gap_missed_cases'] for x in certified_rows),
            'total_proven_secondary_gap_conditional':sum(
                x['optimality_gap_unassigned_conditional'] for x in certified_rows
                if x['optimality_gap_unassigned_conditional'] is not None),
            'all_proven':len(certified_rows)==len(rows),
            'objective_order':['min_missed_deadlines','min_unassigned_cases'],
            'secondary_gap_only_at_primary_optimum':True}
    return result
