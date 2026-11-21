"""End-to-end offline integration using simulated E2B SDK and model calls.
Production code always invokes E2B; this mock is never used as a runtime fallback.
"""
import json
import os
import tempfile
from pathlib import Path
import uuid

from fastapi.testclient import TestClient
import pytest

from app import main
from app import llm
from app.domain import allocate, sha256, validate
from app.e2b_runner import RawCandidate


def fake_runner(datasets, sources):
    result={}
    for name,code in sources.items():
        output=[]
        for seed,data in datasets.items():
            method='fifo' if name=='fifo' else 'deadline'
            schedule=allocate(data,policy=method)
            output.append(RawCandidate(name=name,seed=seed,source_sha256=sha256(code),sandbox_id='MOCKED_E2B_NOT_REAL',
                                       output=schedule,output_sha256=sha256(schedule)))
        result[name]=output
    return result


async def fake_diagnosis(dev, condition):
    if condition=='control':
        return llm.Diagnosis(classification='insufficient_evidence',supporting_evidence_ids=[],
            reasoning='No customer evidence',suggested_requirement_change='Do not change',remaining_uncertainty='Unverified')
    return llm.Diagnosis(classification='requirement_mismatch',supporting_evidence_ids=['SIM-SLA-001'],
        reasoning='FIFO is correctly implemented but violates priority of deadline',
        suggested_requirement_change='Prioritize deadline and qualified reviewers without overtime',remaining_uncertainty='Synthetic only')


async def fake_finance_diagnosis(dev, condition):
    if condition == 'control':
        return llm.FinanceDiagnosis(classification='insufficient_evidence',
            r0_implementation_assessment='correct', business_requirement_assessment='unverified',
            supporting_evidence_ids=[], root_cause='There is no customer evidence for changing FIFO.',
            suggested_requirement_change='No change without evidence.', remaining_uncertainty='No customer observations')
    return llm.FinanceDiagnosis(classification='requirement_mismatch',
        r0_implementation_assessment='correct', business_requirement_assessment='mismatch',
        supporting_evidence_ids=['SIM-SLA-001'],
        root_cause='FIFO correctly implements R0, but prioritizes arrival over urgent due dates, worsening missed deadlines.',
        suggested_requirement_change='Use deadline-aware ordering with qualified reviewer capacity unchanged.',
        business_tradeoffs=['Workload balance needs separate verification'],
        compliance_questions=['Check country specific claims SLA contracts'],
        remaining_uncertainty='Only synthetic evidence available')


async def fake_generate(*args,**kwargs):
    _,code=main.get_reference_sources()
    return llm.CodeResult(python_code=code,rationale='EDD synthetic demonstration')


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    monkeypatch.setattr(llm,'diagnosis',fake_diagnosis)
    monkeypatch.setattr(llm,'finance_diagnosis',fake_finance_diagnosis)
    monkeypatch.setattr(llm,'generate',fake_generate)
    return TestClient(main.app)


def test_end_to_end_r0_counterexample_r1(client):
    sample=client.get('/api/sample').json()
    assert '保険' in sample['brief']
    first=client.post('/api/run-r0',json={'seed':42,'brief':sample['brief']})
    assert first.status_code==200,first.text
    r0=first.json()
    assert r0['implementation_validity']=='PASS'
    assert r0['holdout']['deadline']['missed_total']<r0['holdout']['fifo']['missed_total']
    rid=r0['run_id']
    assert client.get(f'/api/runs/{rid}/report').status_code==200
    prop=client.post('/api/propose',json={'r0_run_id':rid,'evidence_condition':'counterexample'})
    assert prop.status_code==200,prop.text
    proposal=prop.json()
    assert proposal['diagnosis_matches_rubric']
    assert proposal['finance_diagnosis_matches_rubric']
    assert proposal['model_comparison']['classification_agreement']
    assert proposal['evidence'][0]['human_verified'] is False
    approval=client.post('/api/approve',json={'proposal_id':proposal['proposal_id'],'actor':'QA reviewer',
                        'decision':'approved','rationale':'Synthetic counterexample warrants new fixed contract'})
    assert approval.status_code==200,approval.text
    aid=approval.json()['approval_id']
    assert client.post('/api/approve',json={'proposal_id':proposal['proposal_id'],'actor':'QA reviewer',
                        'decision':'approved','rationale':'Second approval must be rejected'}).status_code==409
    gen=client.post('/api/generate-r1',json={'approval_id':aid})
    assert gen.status_code==200,gen.text
    code=gen.json()['python_code']
    evaluation=client.post('/api/evaluate-r1',json={'approval_id':aid,'python_code':code})
    assert evaluation.status_code==200,evaluation.text
    result=evaluation.json()
    assert result['technical_closed_loop_demonstrated']
    assert result['finance_diagnosis_pass']
    assert result['business_requirement_validity']=='UNVERIFIED'
    assert result['holdout_executed']
    assert all(m['assigned_hours']==f['assigned_hours'] and m['missed_deadlines']<f['missed_deadlines']
               for m,f in zip(result['holdout']['generated'],result['holdout']['fifo']))
    assert not set(result['holdout_seeds']) & set(r0['holdout_seeds'])
    assert client.post('/api/evaluate-r1',json={'approval_id':aid,'python_code':code}).status_code==409
    report=client.get(f"/api/experiments/{result['experiment_id']}/report")
    assert report.status_code==200
    assert 'UNVERIFIED' in report.text and 'REQ-QUEUE-001' in report.text
    assert 'R0/R1' in report.text
    bundle=client.get(f"/api/artifacts/experiments/{result['experiment_id']}/bundle")
    assert bundle.status_code==200
    import zipfile,io
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as z:
        paths=z.namelist()
        assert any('attempt_00.py' in f for f in paths)
        assert any('attempt_00.diff' in f for f in paths)
        assert any('dev_attempt_00' in f for f in paths)
        assert any('proposal.json' in f for f in paths)
        assert any('approval.json' in f for f in paths)
    history=client.get('/api/history/experiments')
    assert any(x['id']==result['experiment_id'] for x in history.json()['items'])
    detail=client.get(f"/api/artifacts/experiments/{result['experiment_id']}")
    assert detail.json()['finance_diagnosis_pass']


def test_control_case_no_hallucinated_evidence_no_approval(client):
    sample=client.get('/api/sample').json()
    r0=client.post('/api/run-r0',json={'seed':46,'brief':sample['brief']}).json()
    prop=client.post('/api/propose',json={'r0_run_id':r0['run_id'],'evidence_condition':'control'}).json()
    assert prop['diagnosis_matches_rubric']
    assert not prop['evidence']
    bad=client.post('/api/approve',json={'proposal_id':prop['proposal_id'],'actor':'Reviewer',
                        'decision':'approved','rationale':'Without any evidence should refuse'})
    assert bad.status_code==422


def test_rejected_proposal_cannot_generate(client):
    s=client.get('/api/sample').json()
    r0=client.post('/api/run-r0',json={'seed':42,'brief':s['brief']}).json()
    p=client.post('/api/propose',json={'r0_run_id':r0['run_id'],'evidence_condition':'counterexample'}).json()
    a=client.post('/api/approve',json={'proposal_id':p['proposal_id'],'actor':'Reviewer',
                       'decision':'rejected','rationale':'No client evidence available'}).json()
    assert client.post('/api/generate-r1',json={'approval_id':a['approval_id']}).status_code==422


def test_audit_invalid_uuid(client):
    assert client.get('/api/runs/../../etc/report').status_code!=200
    assert client.get('/api/runs/not-a-uuid/report').status_code==404
