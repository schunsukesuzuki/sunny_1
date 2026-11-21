"""v0.15 full batch 01..09: human gate, artifact integrity, partial cases."""
import hashlib
import io
import json
import zipfile
from app import main, llm
from test_outer_loop_v08 import client, fake_runner
from test_policy_bundle_v014 import benchmark_model_stub


async def fake_design(brief,contract):
    return llm.DesignResult(product_scope='Synthetic InsurTech',actors=['Reviewer'],
        use_cases=['Case assignment'],domain_entities=['Case','Reviewer'],
        service_flow=['Intake','Assign','Review'],hard_constraints=['Fixed hours'],
        objectives=['Reduce deadlines'],interfaces=['API'],acceptance_tests=['Capacity'],
        alternatives=['FIFO','EDD'],external_validation_needed=['Customer interview'])


def _start(client,monkeypatch, condition='counterexample'):
    monkeypatch.setattr(llm,'design',fake_design)
    monkeypatch.setattr(llm,'benchmark_diagnosis',benchmark_model_stub)
    s=client.get('/api/sample').json()
    r=client.post('/api/full-run/start',json={
        'brief':s['brief'],'evidence_mode':'synthetic','seed':42,'evidence_condition':condition,
        'case_ids':['fifo_sla_conflict','actual_fifo_implementation_bug'], 'repetitions':1})
    assert r.status_code==200,r.text
    state=client.get(f"/api/full-run/{r.json()['workflow_id']}").json()
    return state


def test_full_run_waits_for_explicit_human_approval_and_exports_partial(client,monkeypatch):
    st=_start(client,monkeypatch)
    assert st['status']=='AWAITING_APPROVAL',st
    assert st['review']['oda_rubric_pass'] is True
    assert set(st['linked_ids'])>= {'runs','proposals','workflows'}
    assert st['linked_ids']['approvals'] is None
    assert not any('experiments' in x['name'] for x in st['stages'])
    assert [x['name'] for x in st['stages']]==[
        '00_evidence_grounded_requirements','00b_evidence_review','00c_grounded_test_contract','01_input','02_service_design','03_r0_e2b','04_independent_diagnoses','05_human_approval','08c_grounded_kpi_verification','08d_notification_prototype','08e_requirement_trace']
    assert st['bundle_url']
    with zipfile.ZipFile(io.BytesIO(client.get(st['bundle_url']).content)) as z:
        assert json.loads(z.read('manifest.json'))['status']=='PARTIAL'
        paths=z.namelist()
        assert any(x.endswith('/01_input.json') for x in paths)
        assert any(x.endswith('/02_service_design.json') for x in paths)
        assert any(x.endswith('/proposal.json') for x in paths)
        assert not any(x.endswith('/approval.json') for x in paths)
    incorrect=client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':'00000000-0000-0000-0000-000000000333','decision':'approved',
                    'actor':'Reviewer','rationale':'Synthetic demo only'}})
    assert incorrect.status_code==409
    # The only way forward is an explicit approval request.
    reply=client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':st['review']['proposal_id'],'decision':'approved',
                    'actor':'Reviewer','rationale':'Proceed only with synthetic experiments'}})
    assert reply.status_code==200,reply.text
    final=client.get(f"/api/full-run/{st['workflow_id']}").json()
    assert final['status']=='COMPLETE', final
    assert all(final['linked_ids'].values())
    assert len(final['stages'])==17  # v0.21 adds 08f blind optimality
    assert final['bundle_url']
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='COMPLETE',manifest
        assert manifest['pending_or_failed_steps']==[]
        assert len({x['kind'] for x in manifest['files']})==8
        for f in manifest['files']:
            assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256_raw_bytes']
        for kind in ('runs','proposals','approvals','experiments','benchmarks','policy_validations','assessments','workflows'):
            assert kind in {x['kind'] for x in manifest['files']}
        assert '00_START_HERE.md' in z.namelist()
        assert manifest['excluded_steps']['00_evidence_grounded_requirements'].startswith('User explicitly selected')
        assert '00_evidence_grounded_requirements' not in manifest['expected_steps']
    assert client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':st['review']['proposal_id'],'decision':'approved',
                    'actor':'Reviewer','rationale':'Do not run twice'}}).status_code==409
    assert any(x['id']==st['workflow_id'] for x in client.get('/api/history/workflows').json()['items'])


def test_full_run_rejection_halts_and_archives(client,monkeypatch):
    st=_start(client,monkeypatch,condition='control')
    assert st['status']=='AWAITING_APPROVAL'
    rejected=client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':st['review']['proposal_id'],'decision':'rejected',
                    'actor':'Reviewer','rationale':'No real customer evidence'}})
    assert rejected.status_code==200,rejected.text
    final=client.get(f"/api/full-run/{st['workflow_id']}").json()
    assert final['status']=='PARTIAL'
    assert final['phase']=='REJECTED_BY_HUMAN'
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='PARTIAL'
        assert '06_r1_generation_and_evaluation' in manifest['pending_or_failed_steps']
        assert any(f.endswith('/approval.json') for f in z.namelist())
        assert not any(f.endswith('/experiment.json') for f in z.namelist())


def test_full_run_diagnostic_hold_requires_manual_override(client,monkeypatch):
    from test_human_review_v091 import bad_oda
    async def held_finance(*args): return bad_oda()
    monkeypatch.setattr(llm,'finance_diagnosis',held_finance)
    st=_start(client,monkeypatch)
    assert st['review']['oda_rubric_pass'] is False
    payload={'workflow_id':st['workflow_id'],'approval':{
        'proposal_id':st['review']['proposal_id'],'decision':'approved',
        'actor':'Reviewer','rationale':'Synthetic workflow test'}}
    assert client.post('/api/full-run/approve-and-continue',json=payload).status_code==422
    payload['approval'].update({'domain_review_override':True,'acknowledges_independent_r0_pass':True,
        'override_rationale':'R0 independent PASS confirmed; the ODA classifier is HOLD and its result is not an approved diagnosis.'})
    accepted=client.post('/api/full-run/approve-and-continue',json=payload)
    assert accepted.status_code==200,accepted.text
    final=client.get(f"/api/full-run/{st['workflow_id']}").json()
    assert final['status']=='COMPLETE',final
    prop=main.load('proposals',final['linked_ids']['proposals'],'proposal.json')
    assert not prop['finance_diagnosis_matches_rubric']
    assert main.load('approvals',final['linked_ids']['approvals'],'approval.json')['domain_review_override']


def test_full_run_failure_still_emits_partial_zip(client,monkeypatch):
    monkeypatch.setattr(llm,'design',fake_design)
    def fail(*args): raise RuntimeError('E2B initial failure')
    monkeypatch.setattr(main,'run_in_e2b',fail)
    s=client.get('/api/sample').json()
    result=client.post('/api/full-run/start',json={'brief':s['brief'],'evidence_mode':'synthetic','seed':42})
    assert result.status_code==200
    st=client.get(f"/api/full-run/{result.json()['workflow_id']}").json()
    assert st['status']=='PARTIAL',st
    assert 'E2B' in st['error']
    with zipfile.ZipFile(io.BytesIO(client.get(st['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='PARTIAL'
        assert any(x['name']=='03_r0_e2b' and x['status']=='FAILED' for x in manifest['stages'])
        assert any(f.endswith('02_service_design.json') for f in z.namelist())
