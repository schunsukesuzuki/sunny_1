"""v0.27 regression: typed feature scope, model/revision consistency,
DEV-only choice, post-selection gaps, real-vs-simulated Dogwood evidence."""
import io
import json
from pathlib import Path
import zipfile
import hashlib

from app import feature_acceptance as fa
from app import requirement_trace as rt
from app import notification_demo as nd
from app import diagnostic_semantics as ds
from app import diagnostic_reliability as dr
from app import dev_selection_audit as dsa
from app import selection_gap_analysis as gap
from app import dogwood_negative_audit as dna
from app import main
from app.diagnostic_benchmark import FIXTURES
from test_diagnostic_quality_v010 import good_case_response
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def trace(kind):
    r=rt.TEMPLATES[kind]
    return {'requirement_id':'REQ1','type':kind, 'feature_id':r['feature_id'],
            'acceptance_test_ids':list(r['acceptance_test_ids']),
            'test_target':r['test_target'],'backend_evaluator':r['backend_evaluator'],
            'source_evidence_ids':['E01'],
            'notification_thresholds':{'max_delay_hours':24,'min_coverage_pct':100} if kind==rt.NOTIFICATION else None}


def test_notification_requires_pinned_own_acceptance_not_assignment_success():
    t=trace(rt.NOTIFICATION)
    result=nd.evaluate_prototype()
    passed=fa.assess(t,assignment={'synthetic_pass':True},notification=result)
    assert passed['synthetic_pass'] and passed['status']=='PASS_SYNTHETIC_FEATURE_ONLY'
    assert {x['test_id'] for x in passed['test_results']}==set(t['acceptance_test_ids'])
    assert not passed['integrated_service_acceptance']
    assert not fa.assess(t,assignment={'synthetic_pass':True})['synthetic_pass']
    wrong=trace(rt.ASSIGNMENT)
    assert not fa.assess(wrong,notification=result)['synthetic_pass']
    swapped={**t,'feature_id':wrong['feature_id']}
    assert 'REQUIREMENT_CONTRACT_IDENTITY_MISMATCH' in fa.assess(swapped,notification=result)['failure_codes']
    assert not rt.trace_evaluation(t,notification_result=result,acceptance=fa.assess(t))['synthetic_pass']


def test_notification_result_forgery_and_wrong_recipient_are_rejected():
    original=nd.evaluate_prototype()
    t=trace(rt.NOTIFICATION)
    corrupt=json.loads(json.dumps(original))
    corrupt['candidate_notifications'][0]['recipient_id']='FORGED'
    broken=fa.assess(t,notification=corrupt)
    assert not broken['synthetic_pass']
    assert 'NOTIFICATION_ORACLE_RESULT_MISMATCH' in broken['failure_codes']
    corrupt=json.loads(json.dumps(original))
    corrupt['negative_controls']['wrong_recipient_rejected']=False
    assert 'NOTIFICATION_NEGATIVE_CONTROL_MISMATCH' in fa.assess(t,notification=corrupt)['failure_codes']
    corrupt=json.loads(json.dumps(original))
    corrupt['status']='SUPPORTED_SYNTHETIC_PROTOTYPE'
    corrupt['candidate_notifications']=[]
    assert not fa.assess(t,notification=corrupt)['synthetic_pass']


def test_assignment_needs_matching_policy_probes_stress_and_r1_holdout():
    t=trace(rt.ASSIGNMENT)
    base={'version':'GROUNDED-CLAIMS-CONTRACT-v0.19.0',
          'synthetic_pass':True, 'provenance':'DETERMINISTIC_SYNTHETIC_EVALUATION',
          'contract_evidence_ids':['E01'],
          'measured':{'generated_total_missed':0,'behavioral_pass':True,'equal_assigned_hours':True}}
    exp={'experiment_id':'id','selected_code_sha256':'hash','holdout_executed':True}
    pol={'status':'COMPLETED','experiment_id':'id','selected_code_sha256':'hash',
         'results':{'probes':[{'scenario':'deadline_risk_probe','pass':True},
                              {'scenario':'scarce_qualification_probe','pass':True}],
                    'stress_scenarios':[{} for _ in range(4)],
                    'stress_all_constraints_valid':True,'stress_regressions_vs_reference':0}}
    accepted=fa.assess(t,assignment=base,policy=pol,experiment=exp)
    assert accepted['synthetic_pass']
    assert not fa.assess(t,assignment=base,experiment=exp)['synthetic_pass']
    bad={**pol, 'selected_code_sha256':'wrong'}
    assert not fa.assess(t,assignment=base,policy=bad,experiment=exp)['synthetic_pass']
    incomplete={**pol,'results':{**pol['results'],'probes':[pol['results']['probes'][0]]}}
    assert not fa.assess(t,assignment=base,policy=incomplete,experiment=exp)['synthetic_pass']


def test_semantic_diagnosis_compares_explanation_revision_and_evidence_not_oracle():
    visible=FIXTURES['fifo_sla_conflict']['input']
    valid=good_case_response('fifo_sla_conflict').model_dump()
    assert ds.assess(valid,visible)['passed']
    altered={**valid,'root_cause':'This is an implementation bug despite the passing test.'}
    check=ds.assess(altered,visible)
    assert not check['passed']
    assert 'EXPLANATION_ALLEGES_BUG_AGAINST_PASS_TEST' in check['failure_codes']
    assert 'expected_classification' not in json.dumps(check)
    altered={**valid,'suggested_requirement_change':'Keep strict FIFO while prioritizing deadlines',
             'scheduling_precedence':'fifo_first'}
    assert not ds.assess(altered,visible)['passed']
    wrong={**valid,'supporting_evidence_ids':['E-FAKE']}
    assert 'CITATION_NOT_IN_VISIBLE_EVIDENCE' in ds.assess(wrong,visible)['failure_codes']
    bug=good_case_response('actual_fifo_implementation_bug').model_dump()
    bug['root_cause']='The code correctly implements FIFO as specified, no bug here.'
    assert 'EXPLANATION_CONTRADICTS_BUG_CLASSIFICATION' in ds.assess(
        bug,FIXTURES['actual_fifo_implementation_bug']['input'])['failure_codes']


def test_reliability_gate_marks_semantic_inconsistency_without_autocorrection():
    bench={'status':'COMPLETED','summary':{},'trials':[],
           'blind_generalization':{'enabled':True,'summary':{},'trials':[]}}
    for role in ('coding','finance'):
        bench['summary'][role]={'planned':2,'completed':2,'raw_final_passed':2}
        bench['blind_generalization']['summary'][role]={'planned':2,'completed':2,'passed':2}
    bench['trials'].append({'model_role':'coding','status':'COMPLETED',
                            'raw_semantics':{'passed':False}})
    result=dr.assess(bench)
    assert 'CODING_SEMANTIC_BOUNDARY_INCONSISTENCY' in result['quality_failure_codes']
    assert result['status']=='HOLD_HUMAN_ADJUDICATION'
    assert result['autonomous_diagnostic_reliability'] is False


def test_dev_tie_break_uses_unassigned_not_holdout():
    def candidate(name, source, unassigned):
        return {'engine':name,'candidate_id':name,'source_sha256':source,
                'eligible':True,'dev_score':[0,unassigned], 'gate_reasons':[]}
    candidates=[candidate('llm_generated','a',2),candidate('skill_bounded_beam','b',0)]
    r=dsa.select(candidates,'skill_bounded_beam',selected_source_hash='b')
    assert r['selection_consistent_with_predeclared_dev_order']
    assert r['expected_from_dev']=='skill_bounded_beam'
    assert r['holdout_used_for_selection'] is False
    assert not dsa.select(candidates,'llm_generated',selected_source_hash='a')['selection_consistent_with_predeclared_dev_order']


def test_blind_comparison_reports_selected_gap_without_reselection():
    def row(seed,missed,gap_count):
        return {'seed':seed,'input_sha256':str(seed), 'missed_deadlines':missed,
                'optimality_gap_missed_cases':gap_count}
    metrics={'selected':{'cases':[row(1,2,1),row(2,1,0)]},
             'skill_bounded_beam':{'cases':[row(1,1,0),row(2,1,0)]}}
    result=gap.analyze(selected_engine='skill_deadline_scarcity',
        dev_audit={'candidate_ranking':{'selected_engine':'skill_deadline_scarcity',
         'selection_consistent_with_predeclared_dev_order':True}},
        blind_metrics=metrics,random_seed=42)
    assert result['status']=='POST_SELECTION_GAP_DETECTED'
    assert result['comparisons'][0]['selected_worse']==1
    assert result['requires_human_review']
    assert not result['change_selected_engine'] and not result['fed_back_to_dev_selection']
    unproven={'selected':{'cases':[row(1,2,None)]},'skill_bounded_beam':{'cases':[row(1,1,None)]}}
    r=gap.analyze(selected_engine='x',dev_audit={},blind_metrics=unproven,random_seed=2)
    assert r['status']=='INCONCLUSIVE_UNCERTIFIED'


def test_dogwood_native_missing_is_never_claimed_pass(monkeypatch,tmp_path):
    monkeypatch.setenv('DOGWOOD_MODE','enforce')
    monkeypatch.setenv('DOGWOOD_BINARY',str(tmp_path/'missing'))
    result=dna.run(tmp_path,workflow_id='workflow1',approval_id='approval1')
    assert result['status']=='NOT_EXECUTED_NATIVE'
    assert result['native_checked'] is False
    assert result['passed']<=2
    assert result['rust_build_test_log']['available'] is False
    assert result['production_authorization'] is False


def test_dogwood_native_synthetic_negative_probes_recorded(monkeypatch,tmp_path):
    binary=tmp_path/'fake-native';binary.touch()
    monkeypatch.setenv('DOGWOOD_MODE','enforce')
    monkeypatch.setenv('DOGWOOD_BINARY',str(binary))
    monkeypatch.setenv('DOGWOOD_RUST_TEST_LOG',str(tmp_path/'no-build.log'))
    monkeypatch.setattr(dna,'_native',lambda binary,approved,revoked,request: {
        'actual':'ALLOW' if approved==request and revoked is None else 'DENY',
        'cli_exit_code':0,'schema_checked':True})
    result=dna.run(tmp_path,workflow_id='workflow1',approval_id='approval1')
    assert result['status']=='PASS_NATIVE_DENIAL_CASES'
    assert result['native_checked'] and result['planned']==8 and result['passed']==8
    assert result['rust_build_test_log']['available'] is False # mocked native != cargo test


def test_fullrun_bundle_contains_v027_dogwood_and_blind_gap(client,monkeypatch):
    state=_start(client,monkeypatch)
    r=client.post('/api/full-run/approve-and-continue',json={'workflow_id':state['workflow_id'],
      'approval':{'proposal_id':state['review']['proposal_id'],'decision':'approved',
                  'actor':'Tester','rationale':'Synthetic-only audit verification'}})
    assert r.status_code==200,r.text
    final=client.get('/api/full-run/'+state['workflow_id']).json()
    assert final['status']=='COMPLETE',final
    report=client.get('/api/full-run/'+state['workflow_id']+'/report').json()
    assert report['report_version']=='0.27.0'
    assert report['selection_gap_analysis'] is not None
    assert report['dogwood_negative_audit']['status']=='NOT_EXECUTED_NATIVE'
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        names=z.namelist()
        assert any(x.endswith('08f_selection_gap_analysis.json') for x in names)
        assert any(x.endswith('08g_dogwood_negative_audit.json') for x in names)
        m=json.loads(z.read('manifest.json'))
        assert m['producer_version']=='0.27.0'
        assert m['format_version']=='AUDIT-EXPORT-v0.25.0'
        for item in m['files']:
            assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256_raw_bytes']
