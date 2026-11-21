"""v0.23: EAIR-inspired lightweight boundary checks and fail-closed integration."""
import hashlib
import io
import json
import uuid
import zipfile

from app import artifact_readiness as ar, boundary_assurance as ba, main
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def test_registry_and_small_simulation_are_deterministic():
    assert len(ba.CONTRACTS) == 4
    a = ba.regression_scenarios()
    assert a == ba.regression_scenarios()
    assert a['status'] == 'PASS'
    assert len(a['scenarios']) == 5
    assert all(s['detected_as_expected'] for s in a['scenarios'])
    assert not ba.shared_budget_check([6, 6], 10)
    assert ba.shared_budget_check([5, 5], 10)


def test_public_handoff_protects_evidence_and_feature_semantics(tmp_path):
    from app import requirement_trace as rt
    evid = {'evidence_id':'PUB-001','source_url':'https://example.org/public',
            'source_file':'paper.txt','start_char':0,'end_char':100}
    phrase='Insurers must notify policyholders of claim status changes promptly.'
    trace=rt.compile_trace(requirement=phrase,evidence_ids=['PUB-001'],
        requirement_type=rt.NOTIFICATION,source_records=[evid],review_actor='Reviewer')
    state={'inputs':{'evidence_mode':'public'}}
    files={
        '00_evidence_grounded_requirements.json': {'rag_id':'rag-1','evidence':[evid]},
        '00b_human_evidence_review.json':{'decision':'approved','approval_scope':'DEMO_HYPOTHESIS_ONLY',
            'actor':'Reviewer','rag_id':'rag-1','selected_evidence_ids':['PUB-001'],
            'approved_requirement_hypothesis':phrase,'customer_requirement_approval':'NOT_OBTAINED'},
        '00c_requirement_trace.json': trace,
        '01_input.json': {'approved_hypothesis':phrase,'selected_evidence_ids':['PUB-001'],
            'rag_id':'rag-1','requirement_type':rt.NOTIFICATION,'customer_validity':'UNVERIFIED'},
    }
    for name, data in files.items():
        (tmp_path/name).write_text(json.dumps(data),encoding='utf-8')
    assert ba.public_handoff(state,tmp_path)['status']=='PASS'
    files['00c_requirement_trace.json']['requirement_hypothesis']='Changed semantics without approval'
    (tmp_path/'00c_requirement_trace.json').write_text(json.dumps(files['00c_requirement_trace.json']))
    hold=ba.public_handoff(state,tmp_path)
    assert hold['status']=='HOLD'
    assert {x['code'] for x in hold['violations']}=={'REQUIREMENT_STATE_DRIFT'}
    assert ba.certificate(hold,stopped_at='01')[0]['terminal_effect']=='BLOCKED_BEFORE_CONSUMPTION'


def test_unapproved_state_must_not_be_promoted(tmp_path):
    state={'inputs':{'evidence_mode':'public'}}
    result=ba.public_handoff(state,tmp_path)
    assert result['status']=='HOLD'
    assert result['violations'][0]['code']=='MISSING_HANDOFF_RECORD'
    assert ba.approval_handoff({'linked_ids':{'approvals':'a','proposals':'p'}},
        {'decision':'rejected','approval_id':'a','proposal_id':'p'})['status']=='HOLD'


def test_cross_workflow_artifact_blocked_even_if_hash_and_holdout_are_valid(tmp_path):
    eid=str(uuid.uuid4()); d=tmp_path/'experiments'/eid; d.mkdir(parents=True)
    source='print("ok")\n'; (d/'selected_r1.py').write_text(source)
    ids={kind:str(uuid.uuid4()) for kind in ('runs','proposals','approvals')}
    record={'experiment_id':eid,'r0_run_id':ids['runs'],
        'proposal_id':str(uuid.uuid4()),'approval_id':ids['approvals'],
        'selected_code_sha256':hashlib.sha256(source.encode()).hexdigest(), 'holdout_executed':True}
    (d/'experiment.json').write_text(json.dumps(record))
    pre=ar.inspect_experiment(tmp_path,eid)
    assert pre['status']=='READY'  # local integrity is insufficient
    state={'linked_ids':{**ids,'experiments':eid}}
    result=ba.apply_experiment_gate(state,pre)
    assert result['status']=='LINEAGE_MISMATCH'
    assert not ar.ready_for_policy(result)
    assert 'proposal_id' in result['reason']
    cert=ba.certificate(result['boundary_gate'],stopped_at='08b')
    assert cert and cert[0]['interception'] is True


def test_full_batch_carries_boundary_report_and_dag_in_single_zip(client,monkeypatch):
    st=_start(client,monkeypatch)
    response=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':st['review']['proposal_id'],'decision':'approved',
                    'actor':'QA reviewer','rationale':'Controlled synthetic experiment only'}})
    assert response.status_code==200,response.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='COMPLETE',final
    assert final['boundary_assurance']['status']=='PASS_CONTROLLED'
    assert final['boundary_assurance']['regression_suite']['status']=='PASS'
    assert next(x for x in final['stages'] if x['name']=='08g_boundary_assurance')['status']=='COMPLETED_WITH_FINDINGS'
    assert final['version'] if 'version' in final else True
    data=client.get(final['bundle_url']).content
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert z.testzip() is None
        man=json.loads(z.read('manifest.json'))
        assert man['status']=='COMPLETE'
        assert man['format_version']=='AUDIT-EXPORT-v0.23.0'
        for suffix in ('08g_boundary_assurance.json','08g_boundary_regression.json',
                       '08g_provenance_dag.json','boundary_05_to_06.json','boundary_08b_lineage.json'):
            assert any(x.endswith('/'+suffix) for x in z.namelist()),suffix
        for f in man['files']:
            assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256_raw_bytes']


def test_runtime_missing_approval_is_intercepted_before_r1(client,monkeypatch):
    st=_start(client,monkeypatch)
    exp_calls=[]
    async def forbidden(*args,**kwargs):
        exp_calls.append('called')
        raise AssertionError('R1 must not run without persisted approval')
    monkeypatch.setattr(main,'evaluate_r1',forbidden)
    monkeypatch.setattr(main,'approve',lambda request:{
        'decision':'approved','approval_id':str(uuid.uuid4())})
    response=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':st['workflow_id'],'approval':{'proposal_id':st['review']['proposal_id'],
          'decision':'approved','actor':'QA reviewer','rationale':'Test missing persisted approval'}})
    assert response.status_code==200,response.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='PARTIAL',final
    assert not exp_calls
    assert final['boundary_assurance']['status']=='HOLD'
    assert next(x for x in final['stages'] if x['name']=='06_r1_generation_and_evaluation')['status']=='SKIPPED'
    assert next(x for x in final['stages'] if x['name']=='09_business_delivery_assessment')['status']=='SKIPPED'
    assert final['bundle_url']
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        assert z.testzip() is None
        assert any(x.endswith('/boundary_05_to_06.json') for x in z.namelist())
        assert any(x.endswith('/08g_boundary_assurance.json') for x in z.namelist())


def test_runtime_cross_workflow_experiment_cannot_reach_policy_or_assessment(client,monkeypatch):
    st=_start(client,monkeypatch)
    original=main.evaluate_r1
    async def corrupt_after_evaluate(request):
        response=await original(request)
        path=main.path_for('experiments',response['experiment_id'])/'experiment.json'
        record=json.loads(path.read_text(encoding='utf-8'))
        record['proposal_id']=str(uuid.uuid4())  # still a valid, complete local record
        path.write_text(json.dumps(record,ensure_ascii=False))
        return response
    monkeypatch.setattr(main,'evaluate_r1',corrupt_after_evaluate)
    approval=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':st['workflow_id'], 'approval':{
          'proposal_id':st['review']['proposal_id'],'decision':'approved',
          'actor':'QA reviewer','rationale':'Controlled synthetic scenario only'}})
    assert approval.status_code==200,approval.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='PARTIAL',final
    assert final['boundary_assurance']['status']=='HOLD'
    statuses={x['name']:x['status'] for x in final['stages']}
    assert statuses['06_r1_generation_and_evaluation']=='FAILED'
    assert statuses['08b_policy_and_stress']=='SKIPPED'
    assert statuses['08f_blind_optimality']=='SKIPPED'
    assert statuses['09_business_delivery_assessment']=='SKIPPED'
    assert not final['linked_ids'].get('policy_validations')
    assert not final['linked_ids'].get('assessments')
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        assert z.testzip() is None
        assert json.loads(z.read('manifest.json'))['status']=='PARTIAL'
        name=next(x for x in z.namelist() if x.endswith('/08g_boundary_assurance.json'))
        audit=json.loads(z.read(name))
        assert audit['realization_certificates']
        assert all(x['terminal_effect']=='BLOCKED_BEFORE_CONSUMPTION' for x in audit['realization_certificates'])
