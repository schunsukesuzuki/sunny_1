"""v0.22: no cascading 08b/08f/09 404 when R1 created only a started marker."""
import hashlib
import io
import json
import uuid
import zipfile

import pytest
from fastapi import HTTPException

from app import artifact_readiness as ar
from app import main
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def test_artifact_guard_never_confuses_started_with_completed(tmp_path):
    eid = str(uuid.uuid4())
    root = tmp_path / 'experiments' / eid
    root.mkdir(parents=True)
    (root / 'started.json').write_text('{}', encoding='utf-8')
    status = ar.inspect_experiment(tmp_path, eid)
    assert status['status'] == 'STARTED_ONLY'
    assert not ar.record_is_complete(status)
    assert not ar.ready_for_policy(status)
    assert status['record'] is None
    assert ar.inspect_experiment(tmp_path, 'not-a-uuid')['status'] == 'INVALID_ID'
    assert ar.inspect_experiment(tmp_path, None)['status'] == 'NOT_LINKED'
    (root / 'experiment.json').write_text('{broken', encoding='utf-8')
    assert ar.inspect_experiment(tmp_path, eid)['status'] == 'CORRUPT_RESULT'
    (root / 'experiment.json').write_text(json.dumps({'experiment_id':eid, 'status':'FAILED'}),encoding='utf-8')
    assert ar.inspect_experiment(tmp_path, eid)['status'] == 'FAILED'


def test_artifact_guard_checks_selected_source_integrity(tmp_path):
    eid = str(uuid.uuid4())
    root = tmp_path / 'experiments' / eid
    root.mkdir(parents=True)
    source='print("hello")\n'
    digest=hashlib.sha256(source.encode()).hexdigest()
    result={'experiment_id':eid, 'r0_run_id':str(uuid.uuid4()),
            'proposal_id':str(uuid.uuid4()), 'approval_id':str(uuid.uuid4()),
            'selected_code_sha256':digest, 'holdout_executed':True}
    (root / 'experiment.json').write_text(json.dumps(result), encoding='utf-8')
    assert ar.inspect_experiment(tmp_path,eid)['status']=='SELECTED_CODE_MISSING'
    (root / 'selected_r1.py').write_text(source+'# tampered\n', encoding='utf-8')
    assert ar.inspect_experiment(tmp_path,eid)['status']=='SELECTED_CODE_HASH_MISMATCH'
    (root / 'selected_r1.py').write_text(source,encoding='utf-8')
    assert ar.inspect_experiment(tmp_path,eid)['status']=='READY'
    result['selected_code_sha256']=None
    (root / 'experiment.json').write_text(json.dumps(result), encoding='utf-8')
    assert ar.inspect_experiment(tmp_path,eid)['status']=='NO_SELECTED_R1'


def test_full_run_06_started_only_is_partial_not_08b_404(client, monkeypatch):
    state=_start(client, monkeypatch)
    eid=str(uuid.uuid4())

    async def broken_evaluate(body):
        # Simulate precise failure: evaluate-r1 creates an ID and files but
        # throws before its terminal experiment.json can be persisted.
        main.store('approvals',body.approval_id,'evaluation_started.json',
                   {'experiment_id':eid,'started_at':main.now()})
        main.store('experiments',eid,'started.json',{'approval_id':body.approval_id})
        raise HTTPException(status_code=502,detail='E2B DEV lost connection after sandbox launch')

    monkeypatch.setattr(main,'evaluate_r1',broken_evaluate)
    answer=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':state['workflow_id'],
        'approval':{'proposal_id':state['review']['proposal_id'],
                    'decision':'approved','actor':'QA reviewer',
                    'rationale':'Only synthetic demo execution is authorized'}})
    assert answer.status_code==200,answer.text
    final=client.get(f"/api/full-run/{state['workflow_id']}").json()
    statuses={entry['name']:entry for entry in final['stages']}
    assert final['status']=='PARTIAL',final
    assert '06 R1実験失敗' in final['error'] and 'E2B DEV lost connection' in final['error']
    assert final['linked_ids']['experiments']==eid
    assert statuses['06_r1_generation_and_evaluation']['status']=='FAILED'
    assert 'E2B DEV lost connection' in statuses['06_r1_generation_and_evaluation']['detail']
    for stage in ('08b_policy_and_stress','08f_blind_optimality','09_business_delivery_assessment'):
        assert statuses[stage]['status']=='SKIPPED',statuses[stage]
        assert 'STARTED_ONLY' in statuses[stage]['detail']
        assert 'Artifact not found' not in statuses[stage]['detail']
    assert statuses['08_diagnostic_benchmark']['status']=='COMPLETED_WITH_FINDINGS'
    assert final['linked_ids']['assessments'] is None
    assert final['linked_ids']['policy_validations'] is None
    assert final['bundle_url']
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        assert z.testzip() is None
        man=json.loads(z.read('manifest.json'))
        assert man['status']=='PARTIAL'
        assert man['format_version']=='AUDIT-EXPORT-v0.24.0'
        assert set(['06_r1_generation_and_evaluation','08b_policy_and_stress',
                    '08f_blind_optimality','09_business_delivery_assessment']).issubset(man['pending_or_failed_steps'])
        assert any(n.endswith('/06_r1_failure.json') for n in z.namelist())
        for suffix in ('06_experiment_dependency.json','08b_policy_skip.json','08b_experiment_dependency.json',
                       '08f_blind_optimality.json','09_assessment_skip.json'):
            assert any(n.endswith('/'+suffix) for n in z.namelist()),suffix
        for entry in man['files']:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256_raw_bytes']


def test_full_run_failed_experiment_artifact_does_not_cause_08b_secondary_error(client,monkeypatch):
    state=_start(client,monkeypatch)
    eid=str(uuid.uuid4())

    async def broken_evaluate(body):
        main.store('approvals',body.approval_id,'evaluation_started.json',{'experiment_id':eid})
        main.store('experiments',eid,'started.json',{'approval_id':body.approval_id})
        main.store('experiments',eid,'error.json',{'status':'FAILED','detail':'Sandbox timed out'})
        main.store('experiments',eid,'experiment.json',{'experiment_id':eid,'status':'FAILED'})
        raise HTTPException(502,'Sandbox timed out')

    monkeypatch.setattr(main,'evaluate_r1',broken_evaluate)
    response=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':state['workflow_id'],
        'approval':{'proposal_id':state['review']['proposal_id'],'decision':'approved',
                    'actor':'QA reviewer','rationale':'Run synthetic checks only'}})
    assert response.status_code==200,response.text
    final=client.get(f"/api/full-run/{state['workflow_id']}").json()
    statuses={stage['name']:stage for stage in final['stages']}
    assert final['status']=='PARTIAL'
    assert statuses['08b_policy_and_stress']['status']=='SKIPPED'
    assert 'FAILED' in statuses['08b_policy_and_stress']['detail']
    assert statuses['09_business_delivery_assessment']['status']=='SKIPPED'
    assert final['linked_ids']['experiments']==eid
