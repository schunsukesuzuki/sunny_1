"""v0.14 regression: semantics, stress, bundle completeness and fail-closed status.
All E2B and LLM calls are mocked by the pre-existing offline client fixture.
"""
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass

from app import main, llm, policy_validation as pv
from app.domain import allocate
from test_outer_loop_v08 import client, fake_runner
from test_business_assessment_v013 import end_to_end


def test_behavioral_fixtures_expose_deadline_only_insufficient_policy():
    datasets = pv.policy_probes()
    assert all(pv.evaluate_probe(ds, allocate(ds, policy='deadline'))['pass'] for ds in datasets.values())
    scarcity = datasets[900002]
    # Earliest Deadline Date alone can consume sole property reviewer for a motor claim.
    edd_only = {'assignments': [{'case_id':'COMMON','reviewer_id':'R-A','day':0,'hours':1}],
                'unassigned_case_ids':['SCARCE']}
    result = pv.evaluate_probe(scarcity, edd_only)
    assert result['valid'] is True  # Hard capacity/skill checks alone miss semantic intent.
    assert not result['pass']
    assert result['checks']['scarce_case_uses_sole_specialist'] is False
    assert result['missed_deadlines'] == 1
    assert result['unassigned_cases'] == 1


def test_stress_is_deterministic_and_unassigned_counts_as_missed():
    assert pv.stress_scenarios() == pv.stress_scenarios()
    for ds in pv.stress_scenarios().values():
        m=pv.metric_summary(ds, allocate(ds, policy='deadline'))
        assert m['valid']
        assert m['missed'] >= m['unassigned']


@dataclass
class FakeBenchmarkDiagnosis:
    data:dict
    def model_dump(self):
        return self.data


async def benchmark_model_stub(payload, model):
    from app.diagnostic_benchmark import FIXTURES
    fixture = next(f for f in FIXTURES.values() if f['input'] == payload)
    oracle=fixture['oracle']; change=(oracle['classification']=='requirement_mismatch')
    return FakeBenchmarkDiagnosis({'classification':oracle['classification'],
      'implementation_assessment':oracle['implementation_assessment'],
      'synthetic_requirement_fit':oracle['synthetic_requirement_fit'],
      'real_customer_validity':'unverified',
      'supporting_evidence_ids':oracle['expected_evidence_ids'],
      'scheduling_precedence':'deadline_first_fifo_tiebreak' if change else 'none',
      'change_required':change,
      'root_cause':'FIFO is implemented correctly but cannot optimize deadlines' if change else 'No validated rationale to change policy',
      'suggested_requirement_change':'Prioritize deadlines, use FIFO as tie-breaker' if change else 'No requirement revision supported'})


def test_v014_run_and_save_complete_manifest(client, monkeypatch):
    monkeypatch.setattr(llm,'benchmark_diagnosis',benchmark_model_stub)
    exp,_=end_to_end(client)
    reply=client.post('/api/pipeline/run-and-save',json={
        'experiment_id':exp['experiment_id'],
        'case_ids':['fifo_sla_conflict','actual_fifo_implementation_bug'],
        'repetitions':1})
    assert reply.status_code==200,reply.text
    obj=reply.json()
    assert obj['status']=='COMPLETE',obj['manifest']['stages']
    assert obj['policy_validation']['results']['behavior_pass']
    assert obj['policy_validation']['results']['stress_all_constraints_valid']
    assert obj['assessment']['decision']['code']=='CUSTOMER_DISCOVERY_ONLY'
    assert obj['assessment']['summary_metrics']['benchmark_all_trials_pass']
    assert all(x['status']=='COMPLETED_WITH_FINDINGS' for x in obj['manifest']['stages'])
    for kind in ('runs','proposals','approvals','experiments','policy_validations','benchmarks','assessments'):
        assert kind in {x['kind'] for x in obj['manifest']['files']}
    assert not obj['manifest']['missing']
    downloaded=client.get(obj['bundle_url'])
    assert downloaded.status_code==200
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as z:
        paths=set(z.namelist())
        assert {'manifest.json','00_START_HERE.md'}<=paths
        assert all(x['path'] in paths for x in obj['manifest']['files'])
        for entry in obj['manifest']['files']:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256_raw_bytes']
        assert z.read('manifest.json')
        assert 'Audit Package' in z.read('00_START_HERE.md').decode('utf-8')
    assert client.get('/api/history/exports').status_code==200


def test_v014_partial_export_when_policy_e2b_fails(client, monkeypatch):
    monkeypatch.setattr(llm,'benchmark_diagnosis',benchmark_model_stub)
    exp,_=end_to_end(client)
    def policy_failure(datasets,sources):
        if 900001 in datasets:
            raise RuntimeError('E2B policy sandbox intentionally down')
        return fake_runner(datasets,sources)
    monkeypatch.setattr(main,'run_in_e2b',policy_failure)
    res=client.post('/api/pipeline/run-and-save',json={'experiment_id':exp['experiment_id']})
    assert res.status_code==200,res.text
    obj=res.json()
    assert obj['status']=='PARTIAL'
    assert obj['assessment']['decision']['code']=='HOLD_POLICY'
    assert any(x['status']=='FAILED' for x in obj['manifest']['stages'])
    with zipfile.ZipFile(io.BytesIO(client.get(obj['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='PARTIAL'
        assert any(x.endswith('validation.json') for x in z.namelist())


def test_v014_wrong_policy_link_rejected(client):
    first,_=end_to_end(client)
    # An unrelated UUID cannot be used as a policy source for assessment.
    ans=client.post('/api/business-assessment/run',json={
        'experiment_id':first['experiment_id'],
        'policy_validation_id':'00000000-0000-0000-0000-000000000999'})
    assert ans.status_code==404

async def benchmark_model_bad_stub(payload, model):
    return FakeBenchmarkDiagnosis({'classification':'implementation_bug',
        'implementation_assessment':'incorrect',
        'synthetic_requirement_fit':'unverified',
        'real_customer_validity':'unverified',
        'supporting_evidence_ids':[],
        'scheduling_precedence':'none','change_required':False,
        'root_cause':'Insufficient evidence',
        'suggested_requirement_change':'Keep everything as is'})


def test_complete_export_does_not_mean_diagnostic_success(client, monkeypatch):
    monkeypatch.setattr(llm,'benchmark_diagnosis',benchmark_model_bad_stub)
    exp,_=end_to_end(client)
    r=client.post('/api/pipeline/run-and-save',json={
        'experiment_id':exp['experiment_id'],
        'case_ids':['fifo_sla_conflict'], 'repetitions':1})
    assert r.status_code == 200, r.text
    record=r.json()
    assert record['status']=='COMPLETE'  # all requested evidence collected
    assert not record['assessment']['summary_metrics']['benchmark_all_trials_pass']
    assert record['assessment']['axes'][1]['criteria'][2]['status']=='HOLD'
    assert not record['assessment']['decision']['automatic_diagnosis_accepted']
