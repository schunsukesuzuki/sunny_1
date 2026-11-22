"""Fixed *development-only* cohort; constructed before R1 candidate selection.

Never sampled or selected from HOLDOUT/08f. Four different synthetic shifts,
not independent draws from any customer population.
"""
from __future__ import annotations

from copy import deepcopy
from .domain import make_dataset, sha256

VERSION='DEV-ROBUST-COHORT-v0.28.0'
SEEDS=(920000,920001,920002,920003)


def cohort() -> dict[int,dict]:
    result={}
    for offset,seed in enumerate(SEEDS):
        dataset=deepcopy(make_dataset(7400+offset))
        dataset['seed']=seed
        if offset==0:
            dataset['scenario']='dev_skill_scarcity_shift'
            for r in dataset['reviewers']:
                if r['reviewer_id']=='R-A':
                    r['skills']=['motor']
        elif offset==1:
            dataset['scenario']='dev_capacity_shift'
            for r in dataset['reviewers']:
                r['daily_capacity_hours']=[max(1,h-(1+(i%2))) for i,h in enumerate(r['daily_capacity_hours'])]
        elif offset==2:
            dataset['scenario']='dev_deadline_shift'
            for c in dataset['cases']:
                if c['arrival_order']%2:
                    c['deadline_day']=max(0,c['deadline_day']-1)
        else:
            dataset['scenario']='dev_arrival_shift'
            # Reverse arrival priority; do not alter real deadlines or skills.
            n=len(dataset['cases'])
            for c in dataset['cases']:
                c['arrival_order']=n+1-c['arrival_order']
        result[seed]=dataset
    return result


def manifest() -> dict:
    rows=cohort()
    return {'version':VERSION,'seed_ids':list(SEEDS),
        'scenarios':{str(s):{'name':r['scenario'],'dataset_sha256':sha256(r)} for s,r in rows.items()},
        'preselection_only':True,'holdout_overlap':False,'08f_overlap':False,
        'purpose':'Four deterministic synthetic distribution shifts to break DEV ties; NOT a claim about real generalization.'}
