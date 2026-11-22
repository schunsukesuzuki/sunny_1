"""v0.26 quality/transport separation and immutable replay regression."""
from __future__ import annotations

import json
import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main, llm
from app import diagnostic_consistency as dc
from app import diagnostic_execution as de
from app.diagnostic_benchmark import FIXTURES
from test_diagnostic_quality_v010 import good_case_response
from test_outer_loop_v08 import client


def test_cross_field_constraints_are_oracle_free():
    case=FIXTURES['fifo_sla_conflict']['input']
    valid=good_case_response('fifo_sla_conflict').model_dump()
    assert dc.assess(valid,case)['passed']
    changed={**valid,'classification':'implementation_bug'}
    flagged=dc.assess(changed,case)
    assert not flagged['passed']
    assert 'BUG_REQUIRES_INCORRECT_IMPLEMENTATION' in flagged['failure_codes']
    assert 'BUG_NOT_A_REQUIREMENT_REWRITE' in flagged['failure_codes']
    assert 'oracle' not in json.dumps(flagged)
    changed={**valid,'implementation_assessment':'incorrect'}
    assert 'IMPLEMENTATION_ASSESSMENT_CONTRADICTS_PASS_TEST' in dc.assess(changed,case)['failure_codes']


def test_http_timeout_has_distinct_execution_status():
    assert de.classify_error(HTTPException(504,'Timed out'))=='INCOMPLETE_TIMEOUT'
    assert de.classify_error(HTTPException(502,'malformed'))=='INCOMPLETE_MODEL_RESPONSE'
    assert de.classify_error(ValueError('logic error'))=='FAILED_EXECUTION'


def test_retry_only_timeout_preserves_completed_and_original(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    once={'timed_out':False}
    seen=[]
    async def mocked(payload,*,model):
        seen.append((main.sha256(payload),model))
        if model==llm.FINANCE_MODEL and not once['timed_out']:
            once['timed_out']=True
            raise HTTPException(504,'Ollama timed out')
        # Distinct visible independent-test fixture, never supplied oracle.
        case='actual_fifo_implementation_bug' if str(payload['independent_implementation_test']).startswith('FAIL:') else 'fifo_sla_conflict'
        return good_case_response(case)
    monkeypatch.setattr(llm,'benchmark_diagnosis',mocked)
    c=TestClient(main.app)
    response=c.post('/api/diagnostic-benchmark/run',json={
        'case_ids':['fifo_sla_conflict','actual_fifo_implementation_bug'],
        'repetitions':1,'blind_generalization':False})
    assert response.status_code==200,response.text
    original=response.json()
    assert original['status']=='INCOMPLETE_TIMEOUT'
    assert original['reliability_gate']['execution_status']=='INCOMPLETE_TIMEOUT'
    assert original['reliability_gate']['quality_status']=='HOLD_HUMAN_ADJUDICATION'
    assert original['summary']['coding']['completed']==2
    bid=original['benchmark_id']
    before=list(original['trials'])
    untouched=[r for r in before if r['status']=='COMPLETED']
    assert len(untouched)==3
    assert c.post('/api/diagnostic-benchmark/retry-incomplete',json={
        'benchmark_id':bid,'include_fixed':False,'include_blind':False}).status_code==422
    result=c.post('/api/diagnostic-benchmark/retry-incomplete',json={'benchmark_id':bid})
    assert result.status_code==200,result.text
    data=result.json()
    assert data['status']=='COMPLETED'
    assert data['reliability_gate']['execution_status']=='COMPLETE'
    assert data['reliability_gate']['status']=='HOLD_HUMAN_ADJUDICATION'  # No blind run.
    assert len(seen)==5   # initial 4, retry ONLY 1
    assert [r for r in data['trials'] if r['model_role']=='coding']==[r for r in before if r['model_role']=='coding']
    assert data['retry_history'][0]['original_status']=='INCOMPLETE_TIMEOUT'
    assert data['retry_history'][0]['no_oracle_feedback']
    assert list((tmp_path/'benchmarks'/bid).glob('retry_before_*.json'))
    assert list((tmp_path/'benchmarks'/bid).glob('retry_*.json'))
    assert c.post('/api/diagnostic-benchmark/retry-incomplete',json={'benchmark_id':bid}).status_code==409
    assert c.get(f'/api/artifacts/benchmarks/{bid}/bundle').status_code==200


def test_hash_check_blocks_replay_without_model_call(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    bid=main.fresh_id()
    row={'case_id':'fifo_sla_conflict','repetition':0,'model_role':'finance','model_id':llm.FINANCE_MODEL,
         'prompt_input_sha256':'forged-hash','status':'INCOMPLETE_TIMEOUT','error':'timeout'}
    doc={'benchmark_id':bid,'fixture_version':main.FIXTURE_VERSION,
         'case_ids':['fifo_sla_conflict'],'models':{'coding':llm.MODEL,'finance':llm.FINANCE_MODEL},
         'status':'INCOMPLETE_TIMEOUT','trials':[row],
         'blind_generalization':{'enabled':False,'trials':[],'summary':{}},'retry_history':[]}
    main.store('benchmarks',bid,'benchmark.json',doc)
    async def forbidden(*args,**kwargs): raise AssertionError('Must not call model')
    monkeypatch.setattr(llm,'benchmark_diagnosis',forbidden)
    answer=TestClient(main.app).post('/api/diagnostic-benchmark/retry-incomplete',json={'benchmark_id':bid})
    assert answer.status_code==409
    assert 'fingerprint' in answer.text


def test_fullrun_retry_updates_zip_not_r1_and_does_not_repeat_dogwood(client,monkeypatch):
    import io,zipfile
    from test_full_run_v015 import _start
    from test_policy_bundle_v014 import benchmark_model_stub
    state=_start(client,monkeypatch)
    fired={'done':False}
    async def sometimes_timeout(payload,*,model):
        if model==llm.FINANCE_MODEL and str(payload.get('independent_implementation_test','')).startswith('FAIL:') and not fired['done']:
            fired['done']=True
            raise HTTPException(504,'Ollama timed out')
        return await benchmark_model_stub(payload,model=model)
    monkeypatch.setattr(llm,'benchmark_diagnosis',sometimes_timeout)
    approved=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':state['workflow_id'],
        'approval':{'proposal_id':state['review']['proposal_id'],
                    'decision':'approved','actor':'Reviewer',
                    'rationale':'Synthetic test for selective diagnostic replay'}})
    assert approved.status_code==200,approved.text
    before=client.get('/api/full-run/'+state['workflow_id']).json()
    assert before['status']=='PARTIAL',before
    stages={x['name']:x['status'] for x in before['stages']}
    assert stages['06_r1_generation_and_evaluation'] in ('COMPLETED','COMPLETED_WITH_FINDINGS')
    assert stages['08_diagnostic_benchmark']=='INCOMPLETE'
    before_exp_id=before['linked_ids']['experiments']
    orig_zip=client.get(before['bundle_url']).content
    first_manifest=json.loads(zipfile.ZipFile(io.BytesIO(orig_zip)).read('manifest.json'))
    assert first_manifest['status']=='PARTIAL'
    again=client.post('/api/full-run/'+state['workflow_id']+'/retry-diagnostic-timeouts')
    assert again.status_code==200,again.text
    after=again.json()
    assert after['status']=='COMPLETE', {'stages': after['stages'], 'error': after.get('error')}
    assert after['linked_ids']['experiments']==before_exp_id
    assert after['dogwood_authorization']==before['dogwood_authorization']
    assert after['diagnostic_execution_status']=='COMPLETE'
    assert after['diagnostic_reliability_status']=='HOLD_HUMAN_ADJUDICATION'
    with zipfile.ZipFile(io.BytesIO(client.get(after['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='COMPLETE'
        assert any('08_diagnostic_retry_status_' in name for name in z.namelist())
    assert list((main.ARTIFACT_DIR/'exports'/after['export_id']).glob('before_diagnostic_retry_*.zip'))


def test_replayed_blind_is_not_counted_as_fresh(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    state={'dropped':False}
    async def mock_call(payload,*,model):
        if ('Claim B arrived' in str(payload.get('synthetic_dev_observation','')) and
            model==llm.FINANCE_MODEL and not state['dropped']):
            state['dropped']=True
            raise HTTPException(504,'Ollama timeout on blind call')
        return good_case_response('fifo_sla_conflict')
    monkeypatch.setattr(llm,'benchmark_diagnosis',mock_call)
    c=TestClient(main.app)
    res=c.post('/api/diagnostic-benchmark/run',json={
        'case_ids':['fifo_sla_conflict','actual_fifo_implementation_bug'],
        'blind_generalization':True}).json()
    assert res['status']=='INCOMPLETE_TIMEOUT'
    bid=res['benchmark_id']
    original_seed=json.loads((tmp_path/'benchmarks'/bid/'blind_cases.json').read_text())['seed_root']
    saved_completed=[x for x in res['blind_generalization']['trials'] if x['status']=='COMPLETED']
    out=c.post('/api/diagnostic-benchmark/retry-incomplete',json={'benchmark_id':bid})
    assert out.status_code==200,out.text
    nxt=out.json()
    assert nxt['status']=='COMPLETED'
    assert original_seed==json.loads((tmp_path/'benchmarks'/bid/'blind_cases.json').read_text())['seed_root']
    assert all(x in nxt['blind_generalization']['trials'] for x in saved_completed)
    assert sum(x.get('replayed_after_incomplete',False) for x in nxt['blind_generalization']['trials'])==1
    assert 'FINANCE_BLIND_REPLAY_NOT_FRESH' in nxt['reliability_gate']['quality_failure_codes']
    assert nxt['reliability_gate']['execution_status']=='COMPLETE'
    assert nxt['reliability_gate']['status']=='HOLD_HUMAN_ADJUDICATION'
