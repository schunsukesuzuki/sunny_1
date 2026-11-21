"""Transparent v0.21 structured requirement analysis protocol.

Inputs and repair feedback come ONLY from the supplied document, not the
benchmark oracle. The independent rubric remains the v0.10.1 scorer.
"""
from __future__ import annotations

from typing import Any

VERSION='DIAG-PROTOCOL-v0.21.0'

DECISION_PROTOCOL = """
Before writing JSON, reason privately in this fixed order:
1. Read the independent implementation test as an observation, not an opinion:
   PASS => code conforms to the *specified* R0 contract; FAIL => implementation does not.
2. Separately assess the *business objective*. FIFO can be correctly implemented
   while violating an independently observed deadline objective. This is a
   REQUIREMENT issue, not evidence that FIFO code is buggy.
3. Prefer 'insufficient_evidence' when no measurable goal, contradictory stakeholder
   preferences, or no credible comparison exist. A passing implementation alone
   does not establish the customer's business objective.
4. If the specified behavior is violated, distinguish an implementation defect from
   a request to change requirements; changing requirements is not the automatic fix.
5. Only cite evidence IDs that are actually in the evidence list and support the
   relevant claim. Contradictory stakeholder opinions may not prove a KPI.
6. For a justified deadline-first requirement rewrite, deadline sorts FIRST;
   arrival_order is only a tie-breaker. Never preserve strict FIFO priority.
7. Synthetic evidence does not validate a real customer's need, regulation or ROI.
   Keep real_customer_validity=unverified.
8. Self-check ALL JSON fields for cross-field consistency before returning.
Do NOT assert a benchmark case's answer from its title. Judge the input facts.
""".strip()


def public_fact_checks(payload:dict,answer:dict)->dict:
    """Identify contradictions visible without oracle/labels. Never auto-fix answers."""
    test=str(payload.get('independent_implementation_test','')).lstrip().upper()
    impl=answer.get('implementation_assessment')
    observations=[]
    if test.startswith('PASS') and impl!='correct':
        observations.append('The supplied independent test reports PASS; re-read code-vs-contract assessment.')
    elif test.startswith('FAIL') and impl!='incorrect':
        observations.append('The supplied independent test reports FAIL; re-read code-vs-contract assessment.')
    available={x.get('evidence_id') for x in payload.get('evidence',[]) if isinstance(x,dict)}
    cited=set(answer.get('supporting_evidence_ids',[]))
    if cited-available:
        observations.append('Cited evidence IDs absent from the input: '+repr(sorted(cited-available)))
    if not available and cited:
        observations.append('There is no cited evidence in the input; do not invent evidence IDs.')
    if answer.get('real_customer_validity')!='unverified':
        observations.append('This case has no verified real customer interviews; distinguish synthetic from external validity.')
    goal=str(payload.get('business_goal','')).lower()
    observation=str(payload.get('synthetic_dev_observation','')).lower()
    if ('unspecified' in goal or 'unknown' in goal or 'no comparative' in observation or 'no controlled comparison' in observation):
        if answer.get('synthetic_requirement_fit')=='supported':
            observations.append('No validated business comparator: do not declare requirements supported.')
    change=str(answer.get('suggested_requirement_change','')).lower()
    if answer.get('scheduling_precedence')=='deadline_first_fifo_tiebreak' and ('strict fifo' in change and 'remove' not in change):
        observations.append('Strict FIFO cannot remain primary when deadlines take precedence.')
    if test.startswith('FAIL') and answer.get('change_required') and 'fifo' in goal:
        observations.append('An implementation error alone does not establish a requirement rewrite.')
    return {'protocol_version':VERSION,'input_only_feedback':observations,
            'oracle_or_expected_labels_exposed':False}


def blind_diagnostic_cases(seed_root:int)->dict[str,dict]:
    """New seeded synthetic cases, first-pass ONLY. Never used for revision feedback."""
    import random
    r=random.Random(seed_root)
    miss_a=r.randint(6,11); miss_b=r.randint(0,2)
    eid=f'SYN-BLIND-SLA-{r.randint(1000,9999)}'
    bug_id=f'SYN-BLIND-BUG-{r.randint(1000,9999)}'
    return {
      'deadline_business_mismatch':{
        'input':{'contract':'R0: process intake cases by arrival_order, qualified earliest available reviewer.',
          'independent_implementation_test':'PASS: deterministic reviewer/day checks confirm the code conforms to every listed FIFO constraint.',
          'business_goal':'Improve deadline adherence at fixed planned reviewer-hours.',
          'synthetic_dev_observation':f'FIFO missed {miss_a} deadline targets; alternative due-date ordering missed {miss_b} in matched synthetic data with equal hours.',
          'evidence':[{'evidence_id':eid,'provenance':'synthetic',
             'observation':'A later-arriving urgent task is delayed behind an earlier, nonurgent task under the pinned FIFO rule.'}],
          'real_customer_interviews':[],'legal_source_material':[]},
        'oracle':{'classification':'requirement_mismatch','implementation_assessment':'correct',
          'synthetic_requirement_fit':'mismatch','expected_evidence_ids':[eid]}},
      'code_breaks_fifo':{
        'input':{'contract':'R0: process claims in arrival_order if both reviewers and capacity allow.',
          'independent_implementation_test':'FAIL: deterministic ordering check found inversion of two feasible intake cases.',
          'business_goal':'Execute the approved FIFO policy; no separate business SLA comparison is established.',
          'synthetic_dev_observation':'Claim B arrived after claim A, but implementation put claim B first even though claim A was feasible.',
          'evidence':[{'evidence_id':bug_id,'provenance':'synthetic_implementation_trace',
              'observation':'Observed out-of-order queue assignments while all skills and capacity were available.'}],
          'real_customer_interviews':[],'legal_source_material':[]},
        'oracle':{'classification':'implementation_bug','implementation_assessment':'incorrect',
          'synthetic_requirement_fit':'unverified','expected_evidence_ids':[bug_id]}}
    }


def public_proposal_checks(condition:str, answer:dict, *, finance:bool)->list[str]:
    """Facts are supplied by the R0 evidence/contract; no rubric failure codes.

    For propose() independent R0 has PASS before the route is reachable.
    """
    notes=[]
    if answer.get('classification')=='implementation_bug':
        notes.append('The independently executed R0 passed its original FIFO contract; explain why that does not establish a software bug.')
    if finance and answer.get('r0_implementation_assessment')!='correct':
        notes.append('The independent R0 contract test reports PASS, separately from its business outcome.')
    ids=set(answer.get('supporting_evidence_ids',[]))
    available={'SIM-SLA-001'} if condition=='counterexample' else set()
    if ids-available:
        notes.append('Do not cite evidence IDs absent from the supplied synthetic evidence set.')
    if condition=='control' and ids:
        notes.append('No synthetic customer evidence was supplied under this control condition.')
    if condition=='counterexample' and 'SIM-SLA-001' not in ids:
        notes.append('The supplied synthetic observation has ID SIM-SLA-001; check whether it supports the diagnosis.')
    if finance and answer.get('real_customer_validity')!='unverified':
        notes.append('No real customer evidence was supplied; customer validity remains unverified.')
    change=str(answer.get('suggested_requirement_change','')).lower()
    if 'fifo' in change and 'deadline' in change and ('preserv' in change or 'maintain' in change):
        notes.append('If deadlines take priority, strict FIFO cannot also take priority; arrival order may break ties.')
    return notes
