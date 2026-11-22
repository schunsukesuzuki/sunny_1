"""v0.26 execution-status accounting for diagnostic benchmark and bounded replay."""
from __future__ import annotations
import statistics
from fastapi import HTTPException

TIMEOUT = 'INCOMPLETE_TIMEOUT'
RECOVERABLE = frozenset((TIMEOUT,'INCOMPLETE_TRANSPORT','INCOMPLETE_MODEL_RESPONSE'))


def classify_error(exc: Exception) -> str:
    if isinstance(exc,HTTPException):
        if exc.status_code == 504: return TIMEOUT
        if exc.status_code == 503: return 'INCOMPLETE_TRANSPORT'
        if exc.status_code == 502: return 'INCOMPLETE_MODEL_RESPONSE'
    return 'FAILED_EXECUTION'


def status_of(trials: list[dict], blind_trials: list[dict]) -> str:
    if all(x.get('status')=='COMPLETED' for x in trials+blind_trials): return 'COMPLETED'
    if any(x.get('status')==TIMEOUT for x in trials+blind_trials): return 'INCOMPLETE_TIMEOUT'
    if any(x.get('status') in RECOVERABLE for x in trials+blind_trials): return 'INCOMPLETE_EXECUTION'
    return 'COMPLETED_WITH_ERRORS'  # legacy non-transient execution failures


def fixed_summary(trials: list[dict], versions: dict) -> dict:
    result={}
    for role,model in versions.items():
        subset=[t for t in trials if t['model_role']==role]
        good=[t for t in subset if t['status']=='COMPLETED']
        scores=[t['rubric']['score'] for t in good]
        result[role]={
            'model':model,'planned':len(subset),'completed':len(good),
            'passed':sum(t['rubric']['passed'] for t in good),
            'initial_passed':sum(t.get('initial_rubric',{}).get('passed',False) for t in good),
            'raw_initial_passed':sum(t.get('initial_rubric',{}).get('passed',False) for t in good),
            'raw_final_passed':sum(t.get('latest_raw_rubric',{}).get('passed',False) for t in good),
            'assisted_initial_passed':sum(t.get('assisted_initial_rubric',{}).get('passed',False) for t in good),
            'assisted_final_passed':sum(t.get('rubric',{}).get('passed',False) for t in good),
            'grounding_applied':sum(t.get('initial_grounding',{}).get('applied',False) or
                                 t.get('revised_grounding',{}).get('applied',False) for t in good),
            'revised_calls':sum(t.get('repair_attempted',False) for t in good),
            'mean_score':round(statistics.mean(scores),4) if scores else None,
            'mean_raw_score':round(statistics.mean([t['latest_raw_rubric']['score'] for t in good]),4) if good else None,
            'mean_assisted_score':round(statistics.mean(scores),4) if scores else None,
            'failed_calls':len(subset)-len(good),
            'timeout_calls':sum(t['status']==TIMEOUT for t in subset),
            'structural_consistency_passed':sum(t.get('raw_consistency',{}).get('passed',False) for t in good),
        }
    return result


def blind_summary(trials: list[dict], versions: dict) -> dict:
    result={}
    for role in versions:
        xs=[x for x in trials if x['model_role']==role]
        result[role]={
            'planned':len(xs),'completed':sum(x['status']=='COMPLETED' for x in xs),
            'passed':sum(x.get('rubric',{}).get('passed',False) for x in xs),
            'assisted_passed':sum(x.get('assisted_rubric',{}).get('passed',False) for x in xs),
            'grounding_applied':sum(x.get('grounding',{}).get('applied',False) for x in xs),
            'timeout_calls':sum(x['status']==TIMEOUT for x in xs),
            'structural_consistency_passed':sum(x.get('raw_consistency',{}).get('passed',False) for x in xs),
        }
    return result
