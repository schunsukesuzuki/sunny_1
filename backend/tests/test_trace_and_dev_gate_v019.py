"""v0.19: feature-specific traceability, gate failures, and complete mock batch.
External acquisition and E2B/Ollama are mocked; tests never claim real network verification.
"""
import hashlib
import io
import json
import zipfile
import pytest

from app import requirement_trace as rt, notification_demo as nd, dev_selection as dg
from app import main, llm
from app.domain import allocate, sha256
from test_outer_loop_v08 import client, fake_runner
from test_full_run_evidence_v017 import fixed_insurance_corpus, start_public, approve_public

RECORD={'evidence_id':'PUB-003','source_url':'https://example.org/claims','source_file':'claims.html','start_char':10,'end_char':150}


def mk_trace(kind,text):
    return rt.compile_trace(requirement=text,evidence_ids=['PUB-003'],requirement_type=kind,
                            source_records=[RECORD],review_actor='Independent reviewer')


def test_typed_feature_mapping_refuses_notification_as_assignment():
    text='Insurers should provide claim progress updates on a timely basis'
    with pytest.raises(ValueError,match='mismatch'):
        mk_trace(rt.ASSIGNMENT,text)
    trace=mk_trace(rt.NOTIFICATION,text)
    assert trace['feature_id']=='FEATURE-CLAIM-PROGRESS-NOTIFICATION'
    assert trace['test_target']=='separate_deterministic_notification_prototype'
    assert 'NOTIFY-CORRECT-RECIPIENT' in trace['acceptance_test_ids']
    result=rt.trace_evaluation(trace,notification_result=nd.evaluate_prototype())
    assert result['trace_status']=='SYNTHETIC_PROTOTYPE_ONLY'
    assert result['customer_accepted'] is False
    assert result['unrelated_r1_does_not_prove_notification']
    with pytest.raises(ValueError,match='mixes notification'):
        mk_trace(rt.NOTIFICATION,'Insurance claim updates and reviewer assignment should be automated')
    with pytest.raises(ValueError,match='Evidence pointers'):
        rt.compile_trace(requirement=text,evidence_ids=['PUB-009'],requirement_type=rt.NOTIFICATION,
                         source_records=[RECORD],review_actor='Reviewer')


def test_notification_acceptance_oracle_and_negative_controls():
    result=nd.evaluate_prototype(max_delay_hours=24,min_coverage_pct=100)
    assert result['synthetic_pass']
    assert result['negative_controls']=={'missing_notices_rejected':True,'wrong_recipient_rejected':True}
    assert result['customer_integration']=='NOT_IMPLEMENTED'
    assert nd.evaluate_prototype(max_delay_hours=1,min_coverage_pct=100)['synthetic_pass']
    delayed=nd.evaluate_notifications(nd.EVENTS,nd.prototype_notifications(nd.EVENTS),max_delay_hours=0,min_coverage_pct=100)
    assert not delayed['synthetic_pass']
    assert not nd.evaluate_notifications(nd.EVENTS,[],max_delay_hours=24,min_coverage_pct=100)['synthetic_pass']
    notices=nd.prototype_notifications(nd.EVENTS)[:3]
    assert nd.evaluate_notifications(nd.EVENTS,notices,max_delay_hours=24,min_coverage_pct=75)['synthetic_pass']
    assert not nd.evaluate_notifications(nd.EVENTS,notices,max_delay_hours=24,min_coverage_pct=80)['synthetic_pass']


def test_dev_gate_fails_closed_on_behavior_stress_and_no_dev_improvement():
    g={'seed':1,'valid':True,'assigned_hours':8,'missed_deadlines':2}
    fifo={'seed':1,'valid':True,'assigned_hours':8,'missed_deadlines':4}
    reference={'seed':1,'valid':True,'assigned_hours':8,'missed_deadlines':2}
    stress=[{'seed':910000+i,'generated':{'valid':True,'missed':0,'unassigned':0},
             'deadline':{'valid':True,'missed':0,'unassigned':0}} for i in range(4)]
    probes=[{'seed':900001,'pass':True},{'seed':900002,'pass':True}]
    assert dg.gate([g],[fifo],[reference],probes,stress)['eligible']
    assert 'BEHAVIORAL_PROBE_FAIL_OR_IDENTITY_MISMATCH' in dg.gate([g],[fifo],[reference],[{'seed':900001,'pass':True},{'seed':900002,'pass':False}],stress)['reasons']
    bad_stress=[dict(x) for x in stress]; bad_stress[0]={'seed':910000,'generated':{'valid':True,'missed':1,'unassigned':0},'deadline':{'valid':True,'missed':0,'unassigned':0}}
    assert 'STRESS_REGRESSION_VS_FIXED_REFERENCE' in dg.gate([g],[fifo],[reference],probes,bad_stress)['reasons']
    assert 'STRESS_MISSING_OR_IDENTITY_MISMATCH' in dg.gate([g],[fifo],[reference],probes,stress[:3])['reasons']
    assert 'BEHAVIORAL_PROBE_FAIL_OR_IDENTITY_MISMATCH' in dg.gate([g],[fifo],[reference],probes*2,stress)['reasons']
    assert 'NO_DEV_IMPROVEMENT_OVER_FIFO' in dg.gate([fifo],[fifo],[reference],probes,stress)['reasons']
    assert 'DEV_SEED_MISMATCH' in dg.gate([dict(g,seed=999)],[fifo],[reference],probes,stress)['reasons']


def test_public_notification_hypothesis_not_scored_as_assignment(fixed_insurance_corpus,client,monkeypatch):
    st=start_public(client,monkeypatch,query='insurance claim delays progress communication',dataset='insurance_claims_uk')
    assert st['status']=='AWAITING_EVIDENCE_REVIEW',st
    ids=st['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    payload={
        'workflow_id':st['workflow_id'],'decision':'approved',
        'actor':'Technical Reviewer','rationale':'Verify only the notification feature with an independent acceptance template',
        'evidence_ids':ids[:1],
        'approved_requirement':'Insurers must provide clear and timely updates on insurance claim progress and delays.',
        'support_assessment':'supports_problem',
        'requirement_type':'claim_progress_updates',
        'max_notification_delay_hours':24,'min_notification_coverage_pct':100}
    response=client.post('/api/full-run/review-evidence',json=payload)
    assert response.status_code==200,response.text
    mid=client.get('/api/full-run/'+st['workflow_id']).json()
    assert mid['status']=='AWAITING_APPROVAL',mid
    contract=main.load('workflows',st['workflow_id'],'00c_grounded_test_contract.json')
    assert contract['assignment_kpi_not_applicable']
    assert main.load('workflows',st['workflow_id'],'01_input.json')['requirement_type']=='claim_progress_updates'
    approval=client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':mid['review']['proposal_id'],'decision':'approved',
                    'actor':'Reviewer','rationale':'Run the independent fixed synthetic technical regression'}})
    assert approval.status_code==200,approval.text
    fin=client.get('/api/full-run/'+st['workflow_id']).json()
    assert fin['status']=='COMPLETE',fin
    assert fin['requirement_trace_status']=='SYNTHETIC_PROTOTYPE_ONLY'
    review=main.load('workflows',st['workflow_id'],'08c_grounded_kpi_verification.json')
    assert review['status']=='NOT_APPLICABLE_TO_NOTIFICATION'
    trace=main.load('workflows',st['workflow_id'],'08e_requirement_trace.json')
    assert trace['unrelated_r1_does_not_prove_notification']
    ass=main.load('assessments',fin['linked_ids']['assessments'],'assessment.json')
    assert ass['decision']['code']=='HOLD_NOTIFICATION_NOT_INTEGRATED'
    assert ass['decision']['production_go'] is False
    with zipfile.ZipFile(io.BytesIO(client.get(fin['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='COMPLETE'
        for suffix in ('00c_requirement_trace.json','00c_requirement_trace.md',
                       '08c_grounded_kpi_verification.json','08d_notification_prototype.json',
                       '08e_requirement_trace.json','08e_requirement_trace.md'):
            assert any(n.endswith('/'+suffix) for n in z.namelist()),suffix
        for entry in manifest['files']:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256_raw_bytes']


def test_api_refuses_notification_hypothesis_as_assignment(fixed_insurance_corpus,client,monkeypatch):
    st=start_public(client,monkeypatch,query='insurance claim delays',dataset='insurance_claims_uk')
    ids=st['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    resp=client.post('/api/full-run/review-evidence',json={
        'workflow_id':st['workflow_id'],'decision':'approved',
        'actor':'Technical Reviewer','rationale':'Type mismatch should not be silently executed',
        'evidence_ids':ids[:1], 'approved_requirement':'Insurers should provide timely updates on insurance claim delays',
        'support_assessment':'supports_problem','requirement_type':'claims_assignment'})
    assert resp.status_code==422 and 'mismatch' in resp.text
    assert client.get('/api/full-run/'+st['workflow_id']).json()['linked_ids']['runs'] is None


def test_no_dev_eligible_candidate_means_no_holdout_or_false_go(client,monkeypatch):
    s=client.get('/api/sample').json()
    r0=client.post('/api/run-r0',json={'brief':s['brief'],'seed':42}).json()
    prop=client.post('/api/propose',json={'r0_run_id':r0['run_id'],'evidence_condition':'counterexample'}).json()
    approved=client.post('/api/approve',json={'proposal_id':prop['proposal_id'],'actor':'Reviewer',
          'decision':'approved','rationale':'Synthetic contract test only'}).json()
    gen=client.post('/api/generate-r1',json={'approval_id':approved['approval_id']}).json()
    calls=[]
    def always_fifo_for_generated(datasets,sources):
        calls.append(set(datasets))
        out=fake_runner(datasets,sources)
        if 'generated' in sources:
            for raw in out['generated']:
                ds=datasets[raw.seed]
                raw.output=allocate(ds,policy='fifo')
                raw.output_sha256=sha256(raw.output)
        return out
    monkeypatch.setattr(main,'run_in_e2b',always_fifo_for_generated)
    result=client.post('/api/evaluate-r1',json={'approval_id':approved['approval_id'],
                   'python_code':gen['python_code'],'max_repairs':1})
    assert result.status_code==200,result.text
    exp=result.json()
    assert exp['selection_status']=='HOLD_NO_ELIGIBLE_CANDIDATE'
    assert not exp['holdout_executed'] and exp['selected_code_sha256'] is None
    assert all(not set([20042,20043]).intersection(seeds) for seeds in calls)
    assert all(a['selection_gate']['eligible'] is False for a in exp['attempts'])
    audit=main.load('experiments',exp['experiment_id'],'dev_selection_audit.json')
    assert audit['holdout_used_for_selection'] is False
    ba=client.post('/api/business-assessment/run',json={'experiment_id':exp['experiment_id']})
    assert ba.status_code==200,ba.text
    d=ba.json()
    assert d['execution_outcome']['holdout_execution']=='NOT_EXECUTED'
    assert d['decision']['status']=='HOLD'


def test_0191_published_report_is_not_customer_notification():
    """The exact review-form example was rejected with a false mixed-feature 422."""
    hypothesis='公開された保険請求遅延の報告を背景に、期限と資格を考慮した担当者割当案を合成データで検証する（実原因は未確認）'
    assert rt.infer_human_review_type(hypothesis)==rt.ASSIGNMENT
    assert mk_trace(rt.ASSIGNMENT,hypothesis)['feature_id']=='FEATURE-CLAIMS-ASSIGNMENT'
    assert rt.infer_human_review_type('保険請求の進捗を顧客へ通知する。顧客の連絡先を確認する')==rt.NOTIFICATION
    assert rt.infer_human_review_type('保険請求に関する状況を顧客に報告する')==rt.NOTIFICATION


def test_0191_review_endpoint_accepts_source_report_assignment(fixed_insurance_corpus,client,monkeypatch):
    state=start_public(client,monkeypatch,query='insurance claim delays',dataset='insurance_claims_uk')
    ids=state['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    response=client.post('/api/full-run/review-evidence',json={
        'workflow_id':state['workflow_id'],'decision':'approved',
        'actor':'Technical Reviewer','rationale':'Source report is background; reviewer assignment is the only feature',
        'evidence_ids':ids[:1],
        'approved_requirement':'公開された保険請求遅延の報告を背景に、期限と資格を考慮した担当者割当案を合成データで検証する（実原因は未確認）',
        'support_assessment':'supports_problem','requirement_type':'claims_assignment'})
    assert response.status_code==200,response.text


def test_0191_notification_hypothesis_without_literal_delay_is_accepted(fixed_insurance_corpus,client,monkeypatch):
    state=start_public(client,monkeypatch,query='insurance claim delays communication',dataset='insurance_claims_uk')
    ids=state['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    response=client.post('/api/full-run/review-evidence',json={
        'workflow_id':state['workflow_id'],'decision':'approved',
        'actor':'Technical Reviewer','rationale':'Notification feature is separate from a scheduler',
        'evidence_ids':ids[:1],
        'approved_requirement':'Insurance claims policyholders should receive claim status notifications',
        'support_assessment':'supports_problem','requirement_type':'claim_progress_updates'})
    assert response.status_code==200,response.text
