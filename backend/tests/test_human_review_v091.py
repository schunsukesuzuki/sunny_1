"""v0.9.1: ODA diagnostic HOLD must remain visible, while explicit human review permits independent R1 test."""
import io
import zipfile
from fastapi.testclient import TestClient
from app import main, llm
from test_outer_loop_v08 import fake_runner, fake_diagnosis, fake_generate


def bad_oda():
    return llm.FinanceDiagnosis(
        classification='requirement_mismatch',
        r0_implementation_assessment='incorrect',
        business_requirement_assessment='unverified',
        supporting_evidence_ids=[],
        root_cause='FIFO schedule is business-incompatible, but the implementation itself was independently PASS.',
        suggested_requirement_change='Add due date priority within FIFO constraints',
        remaining_uncertainty='unknown regulatory basis')


def test_human_override_can_advance_held_proposal_without_falsifying_oda(monkeypatch, tmp_path):
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    monkeypatch.setattr(main,'run_in_e2b', fake_runner)
    monkeypatch.setattr(llm,'diagnosis', fake_diagnosis)
    async def fake_finance(*args): return bad_oda()
    monkeypatch.setattr(llm,'finance_diagnosis', fake_finance)
    contexts=[]
    async def generate(*args,**kwargs):
        contexts.append(kwargs.get('domain_review'))
        return await fake_generate(*args, **kwargs)
    monkeypatch.setattr(llm,'generate',generate)
    client=TestClient(main.app)
    s=client.get('/api/sample').json()
    rid=client.post('/api/run-r0',json={'seed':42,'brief':s['brief']}).json()['run_id']
    prop=client.post('/api/propose',json={'r0_run_id':rid}).json()
    assert prop['status']=='DOMAIN_REVIEW_HOLD'
    assert prop['finance_diagnosis_matches_rubric'] is False
    assert len(prop['finance_diagnosis_rubric_failures']) >= 2
    base={'proposal_id':prop['proposal_id'],'actor':'Human Claims Product Owner',
          'decision':'approved','rationale':'Proceed with an explicit demo-only human review',
          'domain_review_override':True}
    assert client.post('/api/approve',json=base).status_code==422
    assert client.post('/api/approve',json={**base,'acknowledges_independent_r0_pass':True,
                                            'override_rationale':'short'}).status_code==422
    rationale='R0 FIFO has independent PASS, ODA incorrectly says implementation is incorrect, pinned R1 is for synthetic validation only.'
    approve=client.post('/api/approve',json={**base,'acknowledges_independent_r0_pass':True,
                                             'override_rationale':rationale})
    assert approve.status_code==200,approve.text
    rec=approve.json()
    assert rec['domain_review_override'] is True
    assert rec['original_oda_rubric_status']=='HOLD'
    assert rec['original_oda_rubric_failures']
    assert rec['approval_path']=='audited_human_review'
    code=client.post('/api/generate-r1',json={'approval_id':rec['approval_id']})
    assert code.status_code==200,code.text
    assert contexts and contexts[0]['oda_diagnosis'].startswith('HOLD_NOT_RELIABLE')
    assert 'incorrect' not in contexts[0]
    c=code.json()['python_code']
    res=client.post('/api/evaluate-r1',json={'approval_id':rec['approval_id'],'python_code':c})
    assert res.status_code==200,res.text
    exp=res.json()
    assert exp['finance_diagnosis_pass'] is False
    assert exp['technical_closed_loop_demonstrated'] is False
    assert exp['r1_independent_kpi_improvement_pass'] is True
    assert exp['human_adjudicated_r1_kpi_improvement_demonstrated'] is True
    assert exp['business_requirement_validity']=='UNVERIFIED'
    report=client.get(f'/api/experiments/{exp["experiment_id"]}/report').text
    assert 'ODA diagnostic at approval: `HOLD`' in report
    assert '人間のHOLD審査を経たR1技術KPI改善: **True**' in report
    assert rationale in report
    bundle=client.get(f'/api/artifacts/experiments/{exp["experiment_id"]}/bundle')
    assert bundle.status_code==200
    with zipfile.ZipFile(io.BytesIO(bundle.content)) as z:
        assert any(x.endswith('/approval.json') for x in z.namelist())


def test_override_cannot_approve_no_evidence(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    monkeypatch.setattr(llm,'diagnosis',fake_diagnosis)
    async def fake_finance(*args): return bad_oda()
    monkeypatch.setattr(llm,'finance_diagnosis',fake_finance)
    client=TestClient(main.app)
    s=client.get('/api/sample').json()
    r0=client.post('/api/run-r0',json={'brief':s['brief']}).json()
    prop=client.post('/api/propose',json={'r0_run_id':r0['run_id'],'evidence_condition':'control'}).json()
    assert client.post('/api/approve',json={
        'proposal_id':prop['proposal_id'],'actor':'Claims reviewer','decision':'approved',
        'rationale':'Human trial','domain_review_override':True,
        'acknowledges_independent_r0_pass':True,
        'override_rationale':'Strongly acknowledge the R0 PASS and the claimed evidence'}).status_code==422
