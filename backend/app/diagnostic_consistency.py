"""v0.26: observable-input and cross-field constraints, independent of fixture oracles.

A failure is a conservative machine-checkable INCONSISTENCY, not proof that the
underlying diagnosis is false. Does not rewrite diagnoses or infer gold labels.
"""
from __future__ import annotations

VERSION = 'DIAGNOSTIC-CROSS-FIELD-v0.26.0'
CLASSIFICATIONS = {'requirement_mismatch','implementation_bug','insufficient_evidence'}


def assess(answer: dict, payload: dict) -> dict:
    errors: list[str] = []
    cls = answer.get('classification')
    impl = answer.get('implementation_assessment')
    fit = answer.get('synthetic_requirement_fit')
    required = ('classification','implementation_assessment','synthetic_requirement_fit',
                'real_customer_validity','change_required','scheduling_precedence')
    for name in required:
        if name not in answer:
            errors.append('MISSING_'+name.upper())
    if cls not in CLASSIFICATIONS:
        errors.append('UNKNOWN_CLASSIFICATION')
    if cls == 'requirement_mismatch':
        if impl != 'correct': errors.append('REQUIREMENT_MISMATCH_REQUIRES_CORRECT_IMPLEMENTATION')
        if fit != 'mismatch': errors.append('REQUIREMENT_MISMATCH_REQUIRES_SYNTHETIC_MISMATCH')
        if answer.get('change_required') is not True: errors.append('REQUIREMENT_MISMATCH_REQUIRES_CHANGE')
    elif cls == 'implementation_bug':
        if impl != 'incorrect': errors.append('BUG_REQUIRES_INCORRECT_IMPLEMENTATION')
        if answer.get('change_required') is not False: errors.append('BUG_NOT_A_REQUIREMENT_REWRITE')
        if answer.get('scheduling_precedence') != 'none': errors.append('BUG_SHOULD_NOT_CHANGE_PRECEDENCE')
    elif cls == 'insufficient_evidence':
        if fit != 'unverified': errors.append('INSUFFICIENT_EVIDENCE_REQUIRES_UNVERIFIED_FIT')
        if answer.get('change_required') is not False: errors.append('INSUFFICIENT_EVIDENCE_CANNOT_REQUIRE_CHANGE')
        if answer.get('scheduling_precedence') != 'none': errors.append('INSUFFICIENT_EVIDENCE_CANNOT_SET_PRECEDENCE')
    if answer.get('real_customer_validity') != 'unverified':
        errors.append('REAL_CUSTOMER_VALIDITY_NOT_ESTABLISHED')
    test = str(payload.get('independent_implementation_test','')).strip().upper()
    if test.startswith('PASS:') and impl == 'incorrect':
        errors.append('IMPLEMENTATION_ASSESSMENT_CONTRADICTS_PASS_TEST')
    elif test.startswith('FAIL:') and impl == 'correct':
        errors.append('IMPLEMENTATION_ASSESSMENT_CONTRADICTS_FAIL_TEST')
    evidence = {x.get('evidence_id') for x in payload.get('evidence',[]) if isinstance(x,dict)}
    ids = answer.get('supporting_evidence_ids') or []
    if not isinstance(ids,list) or any(not isinstance(x,str) for x in ids):
        errors.append('INVALID_EVIDENCE_IDS')
    elif set(ids) - evidence:
        errors.append('CITES_UNKNOWN_EVIDENCE')
    return {'version':VERSION, 'status':'CONSISTENT' if not errors else 'INCONSISTENT',
            'passed':not errors, 'failure_codes':list(dict.fromkeys(errors)),
            'source':'RAW_OUTPUT_AND_VISIBLE_INPUT_ONLY_NO_ORACLE',
            'limitations':'Syntactic/field constraints and independent test statements; NOT formal semantic proof.'}
