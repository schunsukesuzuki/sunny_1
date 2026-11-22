"""v0.27 feature-specific, fail-closed acceptance attestations.

A contract binds one human-selected feature to a pinned evaluator and its own
acceptance IDs. An assignment result can *never* discharge a notification test.
An attestation about a prototype is NOT integration or customer acceptance.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any
from . import requirement_trace as rt
from . import notification_demo as nd
from . import grounded_contract as gc

VERSION = 'FEATURE-ACCEPTANCE-CONTRACT-v0.27.0'


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), default=str).encode()).hexdigest()


def assess(trace: dict, *, assignment: dict | None = None,
           notification: dict | None = None, policy: dict | None = None,
           experiment: dict | None = None) -> dict:
    """Only inspect/recompute pinned test evidence, never LLM grading."""
    kind = trace.get('type')
    template = rt.TEMPLATES.get(kind)
    findings: list[str] = []
    tests: list[dict] = []
    expected = list(template['acceptance_test_ids']) if template else []
    if template is None:
        findings.append('UNSUPPORTED_REQUIREMENT_TYPE')
    elif (trace.get('feature_id') != template['feature_id'] or
          trace.get('acceptance_test_ids') != expected or
          trace.get('test_target') != template['test_target'] or
          trace.get('backend_evaluator') != template['backend_evaluator']):
        findings.append('REQUIREMENT_CONTRACT_IDENTITY_MISMATCH')

    target = notification if kind == rt.NOTIFICATION else assignment
    if target is None:
        findings.append('REQUIRED_FEATURE_RESULT_MISSING')
    elif kind == rt.NOTIFICATION:
        if (target.get('version') != nd.VERSION or
                target.get('prototype_source') != 'app.notification_demo.prototype_notifications' or
                target.get('implementation_origin') != 'PREBUILT_DETERMINISTIC_EXAMPLE_NOT_LLM_GENERATED' or
                target.get('is_R1_assignment_implementation') is not False or
                target.get('customer_integration') != 'NOT_IMPLEMENTED'):
            findings.append('NOTIFICATION_ARTIFACT_ORIGIN_INVALID')
        thresholds = trace.get('notification_thresholds') or {}
        hours = thresholds.get('max_delay_hours')
        coverage = thresholds.get('min_coverage_pct')
        if (type(hours) is not int or not 1 <= hours <= 168 or
                type(coverage) is not int or not 1 <= coverage <= 100):
            findings.append('INVALID_NOTIFICATION_THRESHOLDS')
        else:
            try:
                events, notices = target['events'], target['candidate_notifications']
                if not isinstance(events, list) or not isinstance(notices, list):
                    raise ValueError('Invalid event record')
                if events != nd.EVENTS:
                    findings.append('NOTIFICATION_FIXTURE_MISMATCH')
                independently = nd.evaluate_notifications(events, notices,
                    max_delay_hours=hours, min_coverage_pct=coverage)
                if independently != target.get('evaluation'):
                    findings.append('NOTIFICATION_ORACLE_RESULT_MISMATCH')
                missing_eval = nd.evaluate_notifications(events, [],max_delay_hours=hours,
                                                         min_coverage_pct=coverage)
                altered=[dict(x) for x in notices]
                if altered: altered[0]['recipient_id']='WRONG-PERSON'
                wrong_eval=nd.evaluate_notifications(events,altered,max_delay_hours=hours,
                                                      min_coverage_pct=coverage)
                # Evaluate both negative controls again independently.
                expected_controls={'missing_notices_rejected':not missing_eval['synthetic_pass'],
                                   'wrong_recipient_rejected':bool(altered) and not wrong_eval['synthetic_pass']}
                controls_ok=all(expected_controls.values()) and target.get('negative_controls')==expected_controls
                if not controls_ok:
                    findings.append('NOTIFICATION_NEGATIVE_CONTROL_MISMATCH')
                # With zero status-change events no notice should be emitted.
                no_update = nd.prototype_notifications([]) == []
                checks = independently['checks']
                results = {
                    'NOTIFY-ON-STATUS-CHANGE': checks['notifications_correspond_to_status_changes']
                       and checks['status_matches_event'] and len(events) == len(notices),
                    'NOTIFY-WITHIN-THRESHOLD': checks['all_sent_within_max_delay']
                       and checks['coverage_threshold'],
                    'NOTIFY-CORRECT-RECIPIENT': checks['correct_policyholder'] and controls_ok,
                    'NEGATIVE-CONTROL-NO-UPDATE': no_update and expected_controls['missing_notices_rejected']
                       and checks['no_duplicate_or_spurious_notices'],
                }
                tests = [{'test_id': ident, 'passed': results[ident],
                          'evaluator': 'app.notification_demo.evaluate_notifications'} for ident in expected]
            except (ValueError, KeyError, TypeError, AttributeError) as exc:
                findings.append('NOTIFICATION_EVALUATION_ERROR_' + type(exc).__name__)
    elif kind == rt.ASSIGNMENT:
        if (target.get('version') != gc.CONTRACT_VERSION
                or target.get('provenance') != 'DETERMINISTIC_SYNTHETIC_EVALUATION'
                or target.get('contract_evidence_ids') != trace.get('source_evidence_ids')):
            findings.append('ASSIGNMENT_RESULT_CONTRACT_MISMATCH')
        metrics=target.get('measured') or {}
        record=(policy or {}).get('results') or {}
        if (not policy or policy.get('status')!='COMPLETED' or not experiment or
                policy.get('experiment_id') != experiment.get('experiment_id') or
                policy.get('selected_code_sha256') != experiment.get('selected_code_sha256')):
            findings.append('ASSIGNMENT_POLICY_LINEAGE_MISMATCH_OR_MISSING')
        probes={x.get('scenario'):x for x in record.get('probes',[]) if isinstance(x,dict)}
        stresses=record.get('stress_scenarios') or []
        results = {
            'HOLDOUT-MISSED-DEADLINES': target.get('synthetic_pass') is True and
                metrics.get('generated_total_missed') is not None and
                experiment is not None and experiment.get('holdout_executed') is True,
            'PROBE-DEADLINE-RISK': probes.get('deadline_risk_probe',{}).get('pass') is True,
            'PROBE-SCARCE-QUALIFICATION': probes.get('scarce_qualification_probe',{}).get('pass') is True,
            'STRESS-REGRESSION': len(stresses)==4 and record.get('stress_all_constraints_valid') is True
                 and record.get('stress_regressions_vs_reference')==0,
        }
        tests = [{'test_id':ident,'passed':bool(results[ident]),
                  'evaluator':'app.policy_validation.compile_results / app.grounded_contract.evaluate'}
                 for ident in expected]
    if tests and any(x['passed'] is not True for x in tests):
        findings.append('REQUIRED_ACCEPTANCE_TEST_FAILED')
    if len(tests) != len(expected) or [x['test_id'] for x in tests] != expected:
        findings.append('ACCEPTANCE_COVERAGE_INCOMPLETE')
    if findings and 'REQUIRED_ACCEPTANCE_TEST_FAILED' not in findings and not tests:
        tests=[]
    passed = bool(template and not findings and tests and all(t['passed'] for t in tests))
    return {
        'version':VERSION, 'status':'PASS_SYNTHETIC_FEATURE_ONLY' if passed else 'HOLD',
        'feature_type':kind, 'feature_id':trace.get('feature_id'),
        'requirement_id':trace.get('requirement_id'),
        'contract_sha256':digest(trace), 'result_sha256':digest(target) if target is not None else None,
        'required_test_ids':expected, 'test_results':tests,
        'acceptance_test_coverage':len(tests)==len(expected) and bool(expected),
        'synthetic_pass':passed, 'failure_codes':list(dict.fromkeys(findings)),
        'unrelated_feature_proves_requirement':False,
        'integrated_service_acceptance':False,'customer_acceptance':False,
        'scope':'Pinned synthetic feature evaluation only. No integration/causal/legal proof.',
    }
