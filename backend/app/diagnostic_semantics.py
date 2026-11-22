"""Conservative cross-claim/revision checks for RAW synthetic diagnoses (v0.27).

These checks expose machine-detectable contradictions between explanation,
classification, cited evidence, and requested revision action. They do NOT
establish semantic truth, legal compliance, or that a citation entails a claim.
The benchmark's hidden oracle is never consumed here.
"""
from __future__ import annotations
import re
from . import diagnostic_consistency as dc
from . import diagnostic_quality as dq

VERSION='DIAGNOSTIC-SEMANTIC-BOUNDARY-v0.27.0'


def assess(answer: dict, visible_input: dict) -> dict:
    fields=dc.assess(answer,visible_input)
    errors=list(fields['failure_codes'])
    cls=answer.get('classification')
    reason=str(answer.get('root_cause') or '')
    change=str(answer.get('suggested_requirement_change') or '')
    test=str(visible_input.get('independent_implementation_test') or '').upper()
    # Check a small set of high-confidence, *non-negated* statements. No latent
    # language understanding and no verdict of truth from these lexical checks.
    positive_bug=bool(re.search(r'\b(?:implementation|software|code)\s+(?:has\s+(?:a\s+)?|contains\s+(?:a\s+)?)?(?:bug|defect)\b|実装(?:の|に|上の)?(?:バグ|不具合)', reason, re.I))
    denies_bug=bool(re.search(r'\b(?:no|not an?|without)\s+(?:implementation|software|code)\s+(?:bug|defect)\b|実装(?:の|に)?(?:バグ|不具合)(?:ではない|がない|ではなく)', reason, re.I))
    correct_fifo=bool(re.search(r'(?:correctly|faithfully)\s+(?:implements?|follows?)\s+(?:strict\s+)?fifo|(?:実装|コード)(?:は|が).{0,16}(?:正しい|仕様通り|正確)',reason,re.I))
    if cls == 'implementation_bug' and (denies_bug or correct_fifo):
        errors.append('EXPLANATION_CONTRADICTS_BUG_CLASSIFICATION')
    if cls == 'requirement_mismatch' and positive_bug and not denies_bug:
        errors.append('EXPLANATION_ALLEGES_BUG_IN_REQUIREMENT_CASE')
    if test.startswith('PASS:') and positive_bug and not denies_bug:
        errors.append('EXPLANATION_ALLEGES_BUG_AGAINST_PASS_TEST')
    if test.startswith('FAIL:') and correct_fifo:
        errors.append('EXPLANATION_ALLEGES_CORRECT_CODE_AGAINST_FAIL_TEST')
    if dq.contradictory_fifo_precedence(change):
        errors.append('REVISION_PRESERVES_STRICT_FIFO_AND_OVERRIDES_BY_DEADLINE')
    policy=answer.get('scheduling_precedence')
    if cls=='requirement_mismatch':
        if policy != 'deadline_first_fifo_tiebreak':
            errors.append('REVISION_PRECEDENCE_MUST_BE_DEADLINE_FIRST')
        if not re.search(r'\bdeadline|due|sla\b|期限|期日',change,re.I):
            errors.append('REVISION_DOES_NOT_MENTION_DEADLINE')
    elif cls in ('implementation_bug','insufficient_evidence'):
        if answer.get('change_required') is not False or policy != 'none':
            errors.append('REVISION_CHANGES_REQUIREMENTS_WITHOUT_BASIS')
    if cls=='implementation_bug' and re.search(r'\b(?:change|replace|rewrite)\s+(?:the\s+)?(?:business\s+)?requirements?\b|業務要件.{0,5}(?:変更|改訂)',change,re.I):
        errors.append('BUG_REMEDY_REWRITES_BUSINESS_REQUIREMENT')
    evidence={x.get('evidence_id') for x in visible_input.get('evidence',[]) if isinstance(x,dict)}
    citations=answer.get('supporting_evidence_ids')
    if not isinstance(citations,list) or any(x not in evidence for x in citations):
        errors.append('CITATION_NOT_IN_VISIBLE_EVIDENCE')
    elif cls in ('requirement_mismatch','implementation_bug') and evidence and not citations:
        errors.append('ASSERTED_CAUSE_LACKS_EVIDENCE_POINTER')
    errors=list(dict.fromkeys(errors))
    return {'version':VERSION,'status':'CONSISTENT_WITH_VISIBLE_CONTRACT' if not errors else 'HOLD_HUMAN_ADJUDICATION',
            'passed':not errors,'failure_codes':errors,
            'axes':{'classification':cls,'implementation':answer.get('implementation_assessment'),
                    'evidence_ids':citations,'revision_policy':policy,'revision_change_required':answer.get('change_required')},
            'oracle_access':False,'auto_rewrite':False,'synthetic_semantic_truth_proven':False,
            'limits':'Conservative lexical and typed cross-field checks only. May miss nuanced contradictions or flag ambiguous wording; human review required for adjudication.'}
