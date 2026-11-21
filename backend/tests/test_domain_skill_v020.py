"""v0.20 regression: real Skill algorithms, standalone code, provenance and batch.

External E2B and model calls are mocked; the Skill scheduling functions themselves
are NOT mocked. Untouched HOLDOUT must remain invisible to repair/DEV selection.
"""
import hashlib
import io
import json
import subprocess
import sys
import zipfile

import pytest

from app import main, llm
from app.domain import allocate, make_dataset, sha256, validate
from app.e2b_runner import RawCandidate
from app.policy_validation import policy_probes, stress_scenarios, evaluate_probe
from skills.claims_allocation import bundle
from skills.claims_allocation.runner import schedule
from test_outer_loop_v08 import client
from test_full_run_v015 import _start


def test_skill_standalone_source_is_real_and_matches_local(tmp_path):
    for strategy in bundle.STRATEGIES:
        code=bundle.sandbox_source(strategy)
        assert 'if __name__ == "__main__"' in code
        assert 'from app.domain import' not in code
        assert 'LLM-generated' in code
        for ds in [*policy_probes().values(),make_dataset(142)]:
            # The program executed here is the SAME self-contained text sent to E2B.
            source=code.replace('/home/user/input.json',str(tmp_path/'input.json'))
            source=source.replace('/home/user/output.json',str(tmp_path/'output.json'))
            (tmp_path/'input.json').write_text(json.dumps(ds))
            (tmp_path/'solver.py').write_text(source)
            subprocess.run([sys.executable,str(tmp_path/'solver.py')],check=True,capture_output=True,timeout=5)
            out=json.loads((tmp_path/'output.json').read_text())
            assert out==schedule(ds,strategy)
            assert validate(ds,out)['valid']


def test_skill_policy_counterexamples_and_synthetic_stresses():
    probes=policy_probes()
    for strategy in bundle.STRATEGIES:
        for ds in probes.values():
            result=evaluate_probe(ds,schedule(ds,strategy))
            assert result['pass'],(strategy,result)
        for ds in stress_scenarios().values():
            out=validate(ds,schedule(ds,strategy))
            ref=validate(ds,allocate(ds,policy='deadline'))
            assert out['valid']
            assert out['missed_deadlines']<=ref['missed_deadlines']
            assert out['unassigned_cases']<=ref['unassigned_cases']


def test_skill_rejects_invalid_strategies_duplicates_and_bad_capacities():
    ds=make_dataset(142)
    with pytest.raises(ValueError,match='Unapproved'):
        schedule(ds,'arbitrary_exec')
    with pytest.raises(ValueError,match='Unknown'):
        bundle.sandbox_source('arbitrary_exec')
    import copy
    corrupted=copy.deepcopy(ds)
    corrupted['cases'].append(dict(corrupted['cases'][0]))
    with pytest.raises(ValueError,match='Duplicate'):
        schedule(corrupted)
    corrupted=copy.deepcopy(ds)
    corrupted['reviewers'][0]['daily_capacity_hours']=[-1,2]
    with pytest.raises(ValueError,match='capacity'):
        schedule(corrupted)
    assert bundle.manifest()['independent_evaluator']=='backend/app/domain.py:validate'


def mock_sandbox_with_actual_skill(datasets,sources):
    """Data-plane mock only; the actual skill algorithm executes in each branch."""
    records={}
    for name,source in sources.items():
        results=[]
        for seed,ds in datasets.items():
            if name=='fifo':
                out=allocate(ds,policy='fifo')
            elif name=='deadline':
                out=allocate(ds,policy='deadline')
            elif 'strategy=\'bounded_beam\'' in source:
                out=schedule(ds,'bounded_beam')
            elif 'strategy=\'deadline_scarcity\'' in source:
                out=schedule(ds,'deadline_scarcity')
            else:
                # Deliberately weak LLMonly candidate: the Skill should win DEV.
                out=allocate(ds,policy='fifo')
            results.append(RawCandidate(name=name,seed=seed,source_sha256=sha256(source),
                sandbox_id='MOCKED_E2B_RUN',output=out,output_sha256=sha256(out),elapsed_seconds=0.01))
        records[name]=results
    return records


def make_approved(client):
    sample=client.get('/api/sample').json()
    r0=client.post('/api/run-r0',json={'brief':sample['brief'],'seed':42}).json()
    prop=client.post('/api/propose',json={'r0_run_id':r0['run_id'],'evidence_condition':'counterexample'}).json()
    app=client.post('/api/approve',json={'proposal_id':prop['proposal_id'],
       'actor':'Domain Skill reviewer','decision':'approved',
       'rationale':'Explicitly approved synthetic assignment trial'}).json()
    return app['approval_id']


def test_skill_only_experiment_does_not_generate_llm_code(client,monkeypatch):
    monkeypatch.setattr(main,'run_in_e2b',mock_sandbox_with_actual_skill)
    aid=make_approved(client)
    async def forbidden(*args,**kwargs):
        raise AssertionError('Model code-generation must not run in skill_only')
    monkeypatch.setattr(llm,'generate',forbidden)
    resp=client.post('/api/evaluate-r1',json={'approval_id':aid,'python_code':'',
                    'r1_mode':'skill_only','max_repairs':0})
    assert resp.status_code==200,resp.text
    x=resp.json()
    assert x['selected_engine']=='skill_deadline_scarcity'
    assert x['r1_mode']=='skill_only'
    assert x['selected_source_provenance']=='PINNED_REVIEWED_DOMAIN_SKILL_NOT_LLM'
    assert x['selection_status']=='ELIGIBLE_SKILL_SELECTED'
    assert x['technical_closed_loop_demonstrated'] is False
    assert x['r1_independent_kpi_improvement_pass'] is True
    assert x['attempts']==[]
    assert x['holdout_executed']
    assert {c['engine'] for c in x['skill_comparison']}=={'skill_deadline_scarcity','skill_bounded_beam'}
    assert all(c['selection_gate']['eligible'] for c in x['skill_comparison'])
    assert not x['holdout_comparators']  # skill_only intentionally does not compare holdouts
    folder=main.path_for('experiments',x['experiment_id'])
    assert (folder/'skill_component_priority.py').exists()
    assert (folder/'skill_manifest.json').exists()
    assert not (folder/'input_candidate.py').exists()
    assert sha256((folder/'selected_r1.py').read_text())==x['selected_code_sha256']
    assert not (folder/'holdout_comparators.json').exists()
    with zipfile.ZipFile(io.BytesIO(client.get(f"/api/artifacts/experiments/{x['experiment_id']}/bundle").content)) as z:
        assert any('skill_component_' in n for n in z.namelist())


def test_compare_skill_wins_dev_and_no_holdout_for_failed_llm(client,monkeypatch):
    monkeypatch.setattr(main,'run_in_e2b',mock_sandbox_with_actual_skill)
    aid=make_approved(client)
    code='\n'.join(['# Dummy Qwen proposal, deliberately inefficient']*6)
    assert len(code)>100
    resp=client.post('/api/evaluate-r1',json={'approval_id':aid,'python_code':code,
                    'r1_mode':'compare','max_repairs':0})
    assert resp.status_code==200,resp.text
    x=resp.json()
    assert x['selected_engine']=='skill_deadline_scarcity'
    assert not x['attempts'][0]['selection_gate']['eligible']
    assert x['technical_closed_loop_demonstrated'] is False
    assert x['holdout_executed']
    assert 'skill_bounded_beam' in x['holdout_comparators']
    assert 'llm_generated' not in x['holdout_comparators']
    assert x['holdout_comparison_note'].startswith('Post-DEV')


def test_full_run_skill_only_keeps_two_human_gates_and_zip(client,monkeypatch):
    monkeypatch.setattr(main,'run_in_e2b',mock_sandbox_with_actual_skill)
    st=_start(client,monkeypatch)
    # _start defaults to compare; new explicit workflow ensures skill_only.
    sample=client.get('/api/sample').json()
    started=client.post('/api/full-run/start',json={
       'brief':sample['brief'],'evidence_mode':'synthetic','seed':42,
       'r1_mode':'skill_only','evidence_condition':'counterexample',
       'case_ids':['fifo_sla_conflict'],'repetitions':1})
    assert started.status_code==200,started.text
    waiting=client.get('/api/full-run/'+started.json()['workflow_id']).json()
    assert waiting['status']=='AWAITING_APPROVAL'
    assert waiting['r1_mode']=='skill_only'
    async def forbidden(*args,**kwargs):
        raise AssertionError('Model should not generate R1 in skill_only')
    monkeypatch.setattr(llm,'generate',forbidden)
    approved=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':waiting['workflow_id'], 'approval':{
        'proposal_id':waiting['review']['proposal_id'],
        'decision':'approved','actor':'Reviewer','rationale':'Domain Skill only synthetic test'}})
    assert approved.status_code==200,approved.text
    fin=client.get('/api/full-run/'+waiting['workflow_id']).json()
    assert fin['status']=='COMPLETE',fin
    exp=main.load('experiments',fin['linked_ids']['experiments'],'experiment.json')
    assert exp['selected_engine']=='skill_deadline_scarcity'
    assert exp['technical_closed_loop_demonstrated'] is False
    with zipfile.ZipFile(io.BytesIO(client.get(fin['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='COMPLETE',manifest
        assert manifest['evidence_provenance']['r1_mode']=='skill_only'
        assert any(n.endswith('/skill_manifest.json') for n in z.namelist())
        for entry in manifest['files']:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256_raw_bytes']
