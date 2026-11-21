"""Deterministic fail-closed DEV selection for R1 (v0.19).

Pinned DEV fixtures include cases, policy counterexamples and stress scenarios.
Holdout is NEVER an input to this gate or to model repair feedback.
"""
from __future__ import annotations

VERSION='R1-DEV-SELECTION-GATE-v0.19.0'


def gate(dev_rows:list[dict], fifo_rows:list[dict], deadline_rows:list[dict],
         probes:list[dict], stress:list[dict])->dict:
    reasons=[]
    if not dev_rows or len(dev_rows)!=len(fifo_rows) or len(dev_rows)!=len(deadline_rows):
        reasons.append('DEV_REFERENCE_MISSING_OR_UNALIGNED')
    devmap={r.get('seed'):r for r in dev_rows}
    fmap={r.get('seed'):r for r in fifo_rows}
    if len(devmap)!=len(dev_rows) or len(fmap)!=len(fifo_rows) or set(devmap)!=set(fmap):
        reasons.append('DEV_SEED_MISMATCH')
    if not reasons:
        for s,r in devmap.items():
            ref=fmap[s]
            if not r.get('valid') or not ref.get('valid'):
                reasons.append('DEV_CONSTRAINT_INVALID');break
            if r.get('assigned_hours')!=ref.get('assigned_hours'):
                reasons.append('DEV_HOURS_INCREASE_OR_CHANGE');break
            if r.get('missed_deadlines',10**9)>ref.get('missed_deadlines',-1):
                reasons.append('DEV_WORSE_THAN_FIFO');break
        if not any(devmap[s].get('missed_deadlines',10**9)<fmap[s].get('missed_deadlines',-1) for s in devmap):
            reasons.append('NO_DEV_IMPROVEMENT_OVER_FIFO')
    if len(probes)!=2 or {p.get('seed') for p in probes}!={900001,900002} or not all(p.get('pass') is True for p in probes):
        reasons.append('BEHAVIORAL_PROBE_FAIL_OR_IDENTITY_MISMATCH')
    if len(stress)!=4 or {s.get('seed') for s in stress}!={910000,910001,910002,910003}:
        reasons.append('STRESS_MISSING_OR_IDENTITY_MISMATCH')
    if any(not s.get('generated',{}).get('valid') or not s.get('deadline',{}).get('valid') for s in stress):
        reasons.append('STRESS_CONSTRAINT_INVALID')
    if any(s.get('generated',{}).get('missed',10**9)>s.get('deadline',{}).get('missed',-1)
           or s.get('generated',{}).get('unassigned',10**9)>s.get('deadline',{}).get('unassigned',-1)
           for s in stress):
        reasons.append('STRESS_REGRESSION_VS_FIXED_REFERENCE')
    return {'gate_version':VERSION,'eligible':not reasons,'reasons':list(dict.fromkeys(reasons)),
            'dev_cases':len(dev_rows),'behavioral_probes_pass':len(probes)==2 and all(p.get('pass') for p in probes),
            'stress_scenarios_checked':len(stress),
            'selection_rule':'Require valid DEV, strict improvement over FIFO on at least one DEV seed, equal hours, two behavioral probes and no stress regression against the fixed heuristic.',
            'holdout_used_for_selection':False}
