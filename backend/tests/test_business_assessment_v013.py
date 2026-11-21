"""v0.14 backward-compatible plus stricter policy gate for v0.13 experiments presales assessment; no internet / real LLM / E2B required."""
import io
import json
import zipfile

from app import main
from app.business_assessment import assess, markdown
from test_outer_loop_v08 import client
from fastapi.testclient import TestClient
from app import llm


def end_to_end(client):
    s = client.get('/api/sample').json()
    r = client.post('/api/run-r0', json={'brief': s['brief'], 'seed': 42})
    assert r.status_code == 200, r.text
    prop = client.post('/api/propose', json={'r0_run_id': r.json()['run_id']})
    assert prop.status_code == 200, prop.text
    approve = client.post('/api/approve', json={
        'proposal_id': prop.json()['proposal_id'], 'decision': 'approved',
        'actor': 'Private Reviewer Name', 'rationale': 'Approved synthetic trial only'})
    assert approve.status_code == 200, approve.text
    gen = client.post('/api/generate-r1', json={'approval_id': approve.json()['approval_id']})
    assert gen.status_code == 200, gen.text
    experiment = client.post('/api/evaluate-r1', json={
        'approval_id': approve.json()['approval_id'], 'python_code': gen.json()['python_code']})
    assert experiment.status_code == 200, experiment.text
    return experiment.json(), prop.json()


def test_complete_assessment_and_bundle(client):
    exp, _ = end_to_end(client)
    response = client.post('/api/business-assessment/run', json={'experiment_id': exp['experiment_id']})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['scope'] == 'SYNTHETIC_DEMONSTRATION_ONLY'
    assert data['decision']['code'] == 'HOLD_POLICY'
    assert data['decision']['production_go'] is False
    assert data['decision']['customer_business_go'] is False
    assert len(data['axes']) == 2
    assert len(data['axes'][0]['criteria']) == 5
    assert len(data['axes'][1]['criteria']) == 8
    assert data['summary_metrics']['selected_code_integrity'] is True
    assert data['summary_metrics']['fixed_hours_and_deadline_improvement'] is True
    assert all(x['status'] == 'UNVERIFIED' for x in data['axes'][0]['criteria'][-2:])
    assert all(x['status'] == 'UNVERIFIED' for x in data['axes'][1]['criteria'][4:6])
    assert data['source_register'][0]['provenance'] == 'SYNTHETIC'
    assert data['source_register'][-1]['provenance'] == 'UNVERIFIED'
    aid = data['assessment_id']
    report = client.get(f'/api/business-assessment/{aid}/report')
    assert report.status_code == 200
    text = report.text
    for required in ('Business Value & Feasibility', 'AI Delivery & Operational Readiness',
                     '証拠IDの正確性 ≠ 証拠の妥当性 ≠ 診断の正しさ', 'UNVERIFIED',
                     'E01', 'E05', 'production GO: **NO**', 'PRESALES-ASSESSMENT-v0.14.0'):
        assert required in text
    assert 'Private Reviewer Name' not in text
    assert '役員' not in text
    history = client.get('/api/history/assessments')
    assert history.status_code == 200
    assert any(x['id'] == aid for x in history.json()['items'])
    archive = client.get(f'/api/artifacts/assessments/{aid}/bundle')
    assert archive.status_code == 200
    with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
        names = z.namelist()
        for key in ('assessment.json', 'report.md', 'selected_r1.py', 'proposal.json', 'approval.json', 'run.json'):
            assert any(x.endswith('/' + key) for x in names), key
    assert client.get(f'/api/artifacts/assessments/{aid}').status_code == 200


def test_no_fake_customer_evidence_and_failed_technical_gate(client, monkeypatch):
    exp, _ = end_to_end(client)
    eid = exp['experiment_id']
    path = main.path_for('experiments', eid)
    record = json.loads((path / 'experiment.json').read_text())
    record['r1_independent_kpi_improvement_pass'] = False
    (path / 'experiment.json').write_text(json.dumps(record))
    res = client.post('/api/business-assessment/run', json={'experiment_id': eid})
    assert res.status_code == 200
    data = res.json()
    assert data['decision']['code'] == 'HOLD_TECHNICAL'
    assert data['axes'][0]['criteria'][0]['status'] == 'HOLD'
    assert data['axes'][0]['criteria'][-1]['status'] == 'UNVERIFIED'
    assert data['decision']['production_go'] is False
    assert data['decision']['customer_business_go'] is False


def test_tampered_selected_code_never_claims_technical_pass(client):
    exp, _ = end_to_end(client)
    (main.path_for('experiments', exp['experiment_id']) / 'selected_r1.py').write_text('print("tampered")')
    res = client.post('/api/business-assessment/run', json={'experiment_id': exp['experiment_id']})
    assert res.status_code == 200
    assert res.json()['decision']['code'] == 'HOLD_TECHNICAL'
    assert res.json()['summary_metrics']['selected_code_integrity'] is False


def test_audit_chain_mismatch_is_rejected(client):
    exp, _ = end_to_end(client)
    file = main.path_for('experiments', exp['experiment_id']) / 'experiment.json'
    data = json.loads(file.read_text())
    data['proposal_id'] = '00000000-0000-0000-0000-000000000007'
    file.write_text(json.dumps(data))
    r = client.post('/api/business-assessment/run', json={'experiment_id': exp['experiment_id']})
    assert r.status_code in (404, 409)
    bad = client.post('/api/business-assessment/run', json={'experiment_id': '../hello'})
    assert bad.status_code == 404


def test_held_llm_diagnosis_cannot_be_hidden():
    run = {'run_id': 'run-demo', 'implementation_validity': 'PASS'}
    prop = {'proposal_id': 'proposal-demo', 'condition': 'counterexample',
            'diagnosis_matches_rubric': True, 'finance_diagnosis_matches_rubric': False}
    approval = {'approval_id': 'approval-demo', 'decision': 'approved', 'domain_review_override': True}
    exp = {'experiment_id': 'exp-demo', 'holdout_executed': True, 'r1_independent_kpi_improvement_pass': True,
           'selected_code_sha256': 'demo', 'dev_seeds': [1], 'holdout_seeds': [2],
           'holdout': {'fifo': [{'valid': True, 'seed': 2, 'assigned_hours': 6, 'missed_deadlines': 2}],
                       'generated': [{'valid': True, 'seed': 2, 'assigned_hours': 6, 'missed_deadlines': 0,
                                      'sandbox_id': 'synthetic-sandbox'}]}}
    result = assess(exp, run, prop, approval, code_integrity=True)
    assert result['decision']['code'] == 'HOLD_POLICY'
    assert result['axes'][1]['criteria'][2]['status'] == 'HOLD'
    assert result['summary_metrics']['human_override'] is True
    assert result['decision']['automatic_diagnosis_accepted'] is False
    assert 'HOLD' in markdown({**result, 'assessment_id': 'assess-demo', 'created_at': '2026-01-01', 'source_sha256': {}})


def test_missing_experiment(client):
    r = client.post('/api/business-assessment/run', json={'experiment_id': '00000000-0000-0000-0000-000000000000'})
    assert r.status_code == 404
