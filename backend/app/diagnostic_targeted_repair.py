"""Conservative v0.29 targeted repair driven ONLY by public input contradictions.

No hidden fixture oracle, scores, blind examples, other models or HOLDOUT are
consumed in deciding repair targets. Only selected JSON fields can be replaced;
all untouched fields are immutable in the adopted answer.
"""
from __future__ import annotations
from copy import deepcopy
from . import diagnostic_consistency as dc
from . import diagnostic_semantics as ds
from . import diagnostic_protocol as dp

VERSION='INPUT_ONLY_TARGETED_REPAIR-v0.29.0'
FIELDS=frozenset(('classification','implementation_assessment','synthetic_requirement_fit',
                   'real_customer_validity','supporting_evidence_ids','root_cause',
                   'suggested_requirement_change','scheduling_precedence',
                   'change_required','remaining_uncertainty'))

_MAP={
    'IMPLEMENTATION_ASSESSMENT_CONTRADICTS_PASS_TEST':('implementation_assessment',),
    'IMPLEMENTATION_ASSESSMENT_CONTRADICTS_FAIL_TEST':('implementation_assessment',),
    'REQUIREMENT_MISMATCH_REQUIRES_CORRECT_IMPLEMENTATION':('implementation_assessment',),
    'BUG_REQUIRES_INCORRECT_IMPLEMENTATION':('implementation_assessment',),
    'EXPLANATION_CONTRADICTS_BUG_CLASSIFICATION':('classification','root_cause'),
    'EXPLANATION_ALLEGES_BUG_IN_REQUIREMENT_CASE':('root_cause',),
    'EXPLANATION_ALLEGES_BUG_AGAINST_PASS_TEST':('root_cause','classification'),
    'EXPLANATION_ALLEGES_CORRECT_CODE_AGAINST_FAIL_TEST':('root_cause','classification'),
    'REQUIREMENT_MISMATCH_REQUIRES_SYNTHETIC_MISMATCH':('synthetic_requirement_fit',),
    'INSUFFICIENT_EVIDENCE_REQUIRES_UNVERIFIED_FIT':('synthetic_requirement_fit',),
    'REQUIREMENT_MISMATCH_REQUIRES_CHANGE':('change_required',),
    'BUG_NOT_A_REQUIREMENT_REWRITE':('change_required',),
    'INSUFFICIENT_EVIDENCE_CANNOT_REQUIRE_CHANGE':('change_required',),
    'BUG_SHOULD_NOT_CHANGE_PRECEDENCE':('scheduling_precedence',),
    'INSUFFICIENT_EVIDENCE_CANNOT_SET_PRECEDENCE':('scheduling_precedence',),
    'REVISION_PRECEDENCE_MUST_BE_DEADLINE_FIRST':('scheduling_precedence',),
    'REVISION_DOES_NOT_MENTION_DEADLINE':('suggested_requirement_change',),
    'REVISION_PRESERVES_STRICT_FIFO_AND_OVERRIDES_BY_DEADLINE':('suggested_requirement_change',),
    'REVISION_CHANGES_REQUIREMENTS_WITHOUT_BASIS':('change_required','scheduling_precedence'),
    'BUG_REMEDY_REWRITES_BUSINESS_REQUIREMENT':('suggested_requirement_change',),
    'REAL_CUSTOMER_VALIDITY_NOT_ESTABLISHED':('real_customer_validity',),
    'CITES_UNKNOWN_EVIDENCE':('supporting_evidence_ids',),
    'INVALID_EVIDENCE_IDS':('supporting_evidence_ids',),
    'CITATION_NOT_IN_VISIBLE_EVIDENCE':('supporting_evidence_ids',),
    'ASSERTED_CAUSE_LACKS_EVIDENCE_POINTER':('supporting_evidence_ids',),
}


def plan(payload:dict, raw_answer:dict)->dict:
    structural=dc.assess(raw_answer,payload)
    semantic=ds.assess(raw_answer,payload)
    codes=list(dict.fromkeys((structural.get('failure_codes') or [])+
                             (semantic.get('failure_codes') or [])))
    target=set()
    for code in codes:
        target.update(_MAP.get(code,()))
    # When the declared *cause itself* contradicts an independent PASS/FAIL
    # observation, the linked cause/fit/revision group must be reconsidered.
    # This is not an oracle label: it only expands editable fields.
    test=str(payload.get('independent_implementation_test') or '').lstrip().upper()
    cls=raw_answer.get('classification')
    if (test.startswith('PASS') and cls=='implementation_bug') or (test.startswith('FAIL') and cls=='requirement_mismatch'):
        target.update(('classification','implementation_assessment','root_cause',
                       'synthetic_requirement_fit','suggested_requirement_change',
                       'scheduling_precedence','change_required'))
    visible=dp.public_fact_checks(payload,raw_answer).get('input_only_feedback') or []
    # All feedback strings are generated from observable fields only.
    return {'version':VERSION,'target_fields':sorted(target),'failure_codes':codes,
        'input_only_feedback':visible,
        'eligible_for_repair':bool(target),
        'selection_uses_oracle':False,'blind_repair_allowed':False,
        'method':'Model proposes full schema, harness adopts target fields ONLY; no automatic gold-label correction.',
        'unmapped_codes':[code for code in codes if code not in _MAP]}


def adopt(prior:dict, candidate:dict, targeted:list[str])->dict:
    if not isinstance(prior,dict) or not isinstance(candidate,dict):
        raise ValueError('Invalid repair JSON')
    names=set(targeted)
    if not names or names-FIELDS or set(prior)!=set(candidate):
        raise ValueError('Unsupported repair fields or schema drift')
    merged=deepcopy(prior)
    for key in names:
        merged[key]=deepcopy(candidate[key])
    discarded=[k for k in prior if prior[k]!=candidate[k] and k not in names]
    return {'answer':merged,'target_fields':sorted(names),
        'discarded_out_of_scope_model_edits':discarded,
        'all_untargeted_fields_preserved':all(merged[k]==prior[k] for k in prior if k not in names),
        'oracle_used':False,'blind_case_used':False}


def summarize(benchmark:dict)->dict:
    """Read-only audit of opt-in fixed-case repairs; raw and Blind remain separate."""
    fixed=benchmark.get('trials') or []
    blind=(benchmark.get('blind_generalization') or {}).get('trials') or []
    planned=[r for r in fixed if r.get('targeted_repair_plan',{}).get('eligible_for_repair')]
    performed=[r for r in fixed if r.get('repair_attempted')]
    adopted=[r for r in performed if r.get('targeted_repair_audit')]
    return {'version':VERSION,'repair_opt_in':bool(benchmark.get('diagnosis_repair_enabled')),
        'fixed_trials':len(fixed),'fixed_trials_with_observable_inconsistency':len(planned),
        'fixed_repair_model_calls':len(performed),'fixed_adopted_repairs':len(adopted),
        'repair_model_errors':sum(bool(r.get('repair_error')) for r in performed),
        'changed_fields_per_trial':[{'case_id':r.get('case_id'),'model_role':r.get('model_role'),
            'target_fields':r['targeted_repair_audit']['target_fields'],
            'discarded_non_target_edits':r['targeted_repair_audit']['discarded_out_of_scope_model_edits']}
            for r in adopted],
        'blind_trials':len(blind),'blind_repair_model_calls':0,
        'oracle_used_for_repair_decision':False,
        'raw_first_pass_preserved':True,'human_adjudication_still_required_for_holds':True,
        'note':'Only input-observable contradictions trigger opt-in repair; repair is not proof of correct interpretation. Blind never receives feedback.'}
