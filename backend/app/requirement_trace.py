"""Typed Evidence -> Requirement -> Feature -> KPI -> Acceptance contract.

The human chooses a bounded feature. Lexical safeguards prevent a visible
feature mismatch; they do not establish semantic entailment. Neither published
problem context nor prototype tests constitute customer acceptance.
"""
from __future__ import annotations
import re
from typing import Any

VERSION='EVIDENCE-REQUIREMENT-TRACE-v0.19.0'
ASSIGNMENT='claims_assignment'
NOTIFICATION='claim_progress_updates'
TEMPLATES={
    ASSIGNMENT: {
        'feature_id':'FEATURE-CLAIMS-ASSIGNMENT',
        'description':'Deadline/qualification-aware reviewer assignment',
        'kpis':['missed_deadlines_including_unassigned','fixed_planned_hours'],
        'acceptance_test_ids':['HOLDOUT-MISSED-DEADLINES','PROBE-DEADLINE-RISK','PROBE-SCARCE-QUALIFICATION','STRESS-REGRESSION'],
        'test_target':'generated_r1_assignment_code',
        'implementation_scope':'LLM-generated R1 assignment, evaluated in E2B',
        'backend_evaluator':'app.grounded_contract.evaluate',
    },
    NOTIFICATION: {
        'feature_id':'FEATURE-CLAIM-PROGRESS-NOTIFICATION',
        'description':'Notify policyholders of claim progress and status changes',
        'kpis':['notification_coverage_pct','maximum_status_update_delay_hours','no_wrong_recipient'],
        'acceptance_test_ids':['NOTIFY-ON-STATUS-CHANGE','NOTIFY-WITHIN-THRESHOLD','NOTIFY-CORRECT-RECIPIENT','NEGATIVE-CONTROL-NO-UPDATE'],
        'test_target':'separate_deterministic_notification_prototype',
        'implementation_scope':'Standalone deterministic example, NOT generated R1 or integrated service',
        'backend_evaluator':'app.notification_demo.evaluate_prototype',
    },
}
NOTIFICATION_TERMS=('notify','notification','notifi','update','communication','communicate','status',
                    'progress','inform','連絡','通知','進捗','状況')
ASSIGNMENT_TERMS=('assign','allocation','allocate','reviewer','triage','priorit','schedul','routing',
                  'capacity','担当','割当','振分','配分','優先順位','資格','審査員')

def _hits(text:str,words:tuple[str,...])->list[str]:
    s=text.casefold()
    return [w for w in words if w in s]

def infer_human_review_type(hypothesis:str)->str:
    """UI suggestion only; never a substitute for a reviewer's selection."""
    # '報告' on its own often refers to a published report (source context),
    # not a notification feature. Count it only when clearly directed to customers.
    n=_hits(hypothesis,NOTIFICATION_TERMS)
    if re.search(r'(?:顧客|契約者|利用者)(?:へ|に|向けて).{0,12}報告', hypothesis):
        n.append('顧客への報告')
    a=_hits(hypothesis,ASSIGNMENT_TERMS)
    return 'ambiguous' if n and a else NOTIFICATION if n else ASSIGNMENT if a else 'unspecified'

def compile_trace(*,requirement:str,evidence_ids:list[str],requirement_type:str,
                  source_records:list[dict],review_actor:str,
                  max_notification_delay_hours:int=24,min_notification_coverage_pct:int=100)->dict:
    if requirement_type not in TEMPLATES: raise ValueError('Unsupported requirement template: cannot silently map to assignment')
    if len(requirement.strip())<20: raise ValueError('Human-reviewed requirement must have at least 20 characters')
    if not evidence_ids or len(set(evidence_ids))!=len(evidence_ids): raise ValueError('Unique source pointers required')
    if set(evidence_ids)!=set(e.get('evidence_id') for e in source_records): raise ValueError('Evidence pointers must match selected source records')
    if not 1<=max_notification_delay_hours<=168: raise ValueError('Notification delay must be 1..168 hours')
    if not 1<=min_notification_coverage_pct<=100: raise ValueError('Notification coverage must be 1..100 percent')
    inferred=infer_human_review_type(requirement)
    if inferred=='ambiguous':raise ValueError('Requirement mixes notification and assignment; split it into separate requirements')
    if inferred=='unspecified':raise ValueError('Requirement does not identify an implementable feature; specify reviewer assignment or claim-progress notifications')
    if inferred not in ('unspecified',requirement_type):
        raise ValueError('Requirement-feature mismatch: do not test notification requirements using assignment scheduling')
    reg=TEMPLATES[requirement_type]
    return {
        'version':VERSION,'requirement_id':'REQ-PUBLIC-001',
        'requirement_hypothesis':requirement.strip(),'type':requirement_type,
        'feature_id':reg['feature_id'],'feature_description':reg['description'],
        'source_evidence_ids':list(evidence_ids),
        'source_links':[{'evidence_id':e['evidence_id'],'source_url':e.get('source_url'),
                         'source_file':e.get('source_file'), 'start_char':e.get('start_char'),
                         'end_char':e.get('end_char')} for e in source_records],
        'reviewer':review_actor,'classification_check':inferred,
        'mapping_status':'TEMPLATE_MAPPED_HUMAN_SELECTED',
        'kpis':list(reg['kpis']),'acceptance_test_ids':list(reg['acceptance_test_ids']),
        'test_target':reg['test_target'],'implementation_scope':reg['implementation_scope'],
        'backend_evaluator':reg['backend_evaluator'],
        'notification_thresholds':{'max_delay_hours':max_notification_delay_hours,
                                   'min_coverage_pct':min_notification_coverage_pct} if requirement_type==NOTIFICATION else None,
        'semantic_evidence_support':'HUMAN_ASSERTED_CONTEXT_ONLY_NOT_INDEPENDENTLY_VERIFIED',
        'source_proves_FIFO_causality':False,
        'is_real_customer_approved':False,
        'notes':'Typed mapping only. An existing acceptance template cannot prove that the source entails the requirement or the feature is deployed.'
    }


def trace_evaluation(trace:dict, *,assignment_result:dict|None=None,notification_result:dict|None=None,acceptance:dict|None=None)->dict:
    kind=trace['type']
    target=notification_result if kind==NOTIFICATION else assignment_result
    passed=bool(target and target.get('synthetic_pass') is True)
    if acceptance is not None:
        passed=bool(acceptance.get('synthetic_pass') is True and
                    acceptance.get('feature_id') == trace.get('feature_id') and
                    acceptance.get('feature_type') == kind)
    return {
        'version':VERSION,'requirement_id':trace['requirement_id'],'type':kind,
        'feature_id':trace['feature_id'],'acceptance_test_ids':trace['acceptance_test_ids'],
        'target_used':trace['test_target'], 'result_status': target.get('status') if target else 'NOT_EXECUTED',
        'evaluator_executed':bool(target),'synthetic_pass':passed,
        'acceptance_version':acceptance.get('version') if acceptance else None,
        'feature_contract_pass':acceptance.get('synthetic_pass') if acceptance else None,
        'unrelated_r1_does_not_prove_notification':kind==NOTIFICATION,
        'customer_accepted':False,'production_ready':False,
        'trace_status':'SYNTHETIC_PROTOTYPE_ONLY' if passed and kind==NOTIFICATION else
                       'SYNTHETIC_ASSIGNMENT_ONLY' if passed else 'HOLD',
        'evidence_ids':trace['source_evidence_ids'],
    }


def markdown(trace:dict,result:dict|None=None)->str:
    lines=['# Evidence → Requirement → Feature → Acceptance Trace (v0.19)','',
        f"- Public evidence: {', '.join(trace['source_evidence_ids'])}",
        f"- Requirement: {trace['requirement_hypothesis']}",
        f"- Type: `{trace['type']}` / Feature: `{trace['feature_id']}`",
        f"- Human template mapping: `{trace['mapping_status']}`",
        f"- Target: `{trace['test_target']}` (not the same as the published source)",
        f"- Reviewer: {trace['reviewer']}", '',
        '## KPI and acceptance tests','',
        *[f'- KPI: `{v}`' for v in trace['kpis']],
        *[f'- Acceptance test: `{v}`' for v in trace['acceptance_test_ids']],
        '', '## Proof boundary','',
        '- Citation exists ≠ citation supports claim ≠ requirement is correct.',
        '- Public issue does not prove FIFO causality or customer-approved SLA.',
        '- Scheduling R1 cannot satisfy a claim-progress notification requirement.',
        '- The notification prototype is separate and not deployed or connected to customers.',
    ]
    if result:
        lines+=['','## Evaluation','',f"- Trace status: `{result['trace_status']}`",
                f"- Result: `{result['result_status']}`",
                f"- Synthetic pass: {result['synthetic_pass']}",
                '- Customer acceptance: NO; production approval: NO.']
    return '\n'.join(lines)+'\n'
