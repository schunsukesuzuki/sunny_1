"""Offline tests for vertical FM routing and independent reason-quality gates."""
import json
from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest
from app import llm, main
from test_outer_loop_v08 import fake_runner, fake_diagnosis, fake_finance_diagnosis, fake_generate


def good_domain():
    return llm.FinanceDiagnosis(classification='requirement_mismatch',
        r0_implementation_assessment='correct',business_requirement_assessment='mismatch',
        supporting_evidence_ids=['SIM-SLA-001'],
        root_cause='A correctly implemented FIFO policy delays urgent claims despite meeting the R0 contract.',
        suggested_requirement_change='Prioritize deadline and skill constraints without more hours.',
        remaining_uncertainty='No real customer evidence')


def test_reasoning_consistency_gate_rejects_software_bug_claim():
    value=good_domain().model_copy(update={'root_cause':'This reveals a software bug in the FIFO implementation.'})
    passed,problems=llm.finance_diagnosis_pass(value,'counterexample')
    assert not passed and any('bug' in p.lower() for p in problems)
    qwen=llm.Diagnosis(classification='requirement_mismatch',supporting_evidence_ids=['SIM-SLA-001'],
        reasoning='This is a software bug in the FIFO implementation.',
        suggested_requirement_change='Prioritize deadlines',remaining_uncertainty='Synthetic')
    assert not llm.diagnosis_pass(qwen,'counterexample')


def test_no_evidence_condition_does_not_force_requirements_change():
    d=llm.FinanceDiagnosis(classification='insufficient_evidence',
       r0_implementation_assessment='correct', business_requirement_assessment='unverified',
       supporting_evidence_ids=[],root_cause='No evidence of a customer requirement mismatch.',
       suggested_requirement_change='No change',remaining_uncertainty='Needs customer interview')
    assert llm.finance_diagnosis_pass(d,'control')==(True,[])
    assert not llm.finance_diagnosis_pass(good_domain(),'control')[0]


@pytest.mark.asyncio
async def test_model_router_calls_explicit_oda_model_and_no_holdout(monkeypatch):
    seen=[]
    async def fake_query(schema,system,user,*,model=None):
        seen.append((schema,model,user))
        return good_domain()
    monkeypatch.setattr(llm,'query',fake_query)
    output=await llm.finance_diagnosis({'fifo':{'missed_total':5}},'counterexample')
    assert output.classification=='requirement_mismatch'
    assert seen[0][1]==llm.FINANCE_MODEL
    assert 'HOLDOUT inputs' in seen[0][2] # explicit non-disclosure statement
    assert 'SIM-SLA-001' in seen[0][2]


def test_oda_failure_is_logged_not_silently_replaced(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    monkeypatch.setattr(llm,'diagnosis',fake_diagnosis)
    async def fail_finance(*args):
        raise HTTPException(503,'ODA unavailable')
    monkeypatch.setattr(llm,'finance_diagnosis',fail_finance)
    client=TestClient(main.app)
    sample=client.get('/api/sample').json()
    rid=client.post('/api/run-r0',json={'seed':42,'brief':sample['brief']}).json()['run_id']
    response=client.post('/api/propose',json={'r0_run_id':rid})
    assert response.status_code==503
    history=client.get('/api/history/proposals').json()['items']
    assert any(x['status']=='FAILED' for x in history)
    p=tmp_path/'proposals'/history[0]['id']
    assert (p/'diagnostic_error.json').exists()
    assert 'ODA unavailable' in (p/'diagnostic_error.json').read_text()


def test_bad_domain_result_blocks_human_approval(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    monkeypatch.setattr(llm,'diagnosis',fake_diagnosis)
    async def bad_domain(*args):
        return good_domain().model_copy(update={'root_cause':'Software bug: FIFO was not implemented correctly'})
    monkeypatch.setattr(llm,'finance_diagnosis',bad_domain)
    client=TestClient(main.app)
    sample=client.get('/api/sample').json()
    rid=client.post('/api/run-r0',json={'seed':42,'brief':sample['brief']}).json()['run_id']
    prop=client.post('/api/propose',json={'r0_run_id':rid}).json()
    assert prop['status']=='DOMAIN_REVIEW_HOLD'
    assert not prop['finance_diagnosis_matches_rubric']
    approve=client.post('/api/approve',json={'proposal_id':prop['proposal_id'],
      'decision':'approved','actor':'Human reviewer','rationale':'Just to test that the gate blocks this'})
    assert approve.status_code==422


@pytest.mark.asyncio
async def test_domain_review_is_passed_to_coding_prompt(monkeypatch):
    captured=[]
    async def fake_query(schema,system,user,*,model=None):
        captured.append(user)
        return llm.CodeResult(python_code='def f():\n    return 1\n' + '# x'*80,rationale='test')
    monkeypatch.setattr(llm,'query',fake_query)
    review=good_domain().model_dump()
    await llm.generate(main.BRIEF, main.SERVICE_R1, domain_review=review)
    assert 'domain diagnosis' in captured[0]
    assert review['suggested_requirement_change'] in captured[0]
