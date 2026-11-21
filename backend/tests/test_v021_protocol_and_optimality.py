"""v0.21 regression: transparent LLM revision, immutable initial scores and
post-selection blind exact optimality. All real external LLM/E2B calls mocked.
"""
import hashlib
import io
import json
import zipfile

from fastapi.testclient import TestClient

from app import main, llm, diagnostic_protocol as dp
from app.blind_optimality import (randomized_suite, enumeration_exact, exact_baseline,
                                   summarize, cp_sat_exact)
from app.domain import validate, allocate, sha256
from app.e2b_runner import RawCandidate
from test_diagnostic_quality_v010 import good_case_response
from test_outer_loop_v08 import client, fake_runner, fake_diagnosis
from test_domain_skill_v020 import mock_sandbox_with_actual_skill


def test_randomized_suite_reproducible_and_separate_from_fixed_dev():
    a=randomized_suite(123456,4)
    assert a==randomized_suite(123456,4)
    assert a!=randomized_suite(123457,4)
    assert set(a)=={2000000,2000001,2000002,2000003}
    assert all(5<=len(x['cases'])<=6 for x in a.values())
    assert all(not any(c['case_id'].startswith('C00') for c in x['cases']) for x in a.values())
    assert all(x['scenario']=='BLIND_RANDOMIZED_POST_SELECTION' for x in a.values())


def test_exhaustive_oracle_is_independently_validated_and_proven_small():
    for ds in randomized_suite(123456,4).values():
        x=exact_baseline(ds)
        assert x['status']=='OPTIMAL',x
        assert x['metrics']['valid']
        assert x['metrics']['on_time']==x['objective'][0]
        assert x['input_sha256']==sha256(ds)


def test_no_false_optimality_for_exhaustive_search_limit():
    ds=randomized_suite(123,2)[2000000]
    x=enumeration_exact(ds,max_nodes=1)
    assert x['status']=='TIME_LIMIT'
    assert x['status']!='OPTIMAL'
    ds2=dict(ds,cases=ds['cases']*2)
    x=enumeration_exact(ds2)
    assert x['status']=='SKIPPED_SIZE_LIMIT'


def test_randomized_blind_gap_does_not_claim_optimality_without_proof():
    suite=randomized_suite(123456,2)
    raw={'fifo':[RawCandidate(name='fifo',seed=s,source_sha256='x',output=allocate(ds,policy='fifo'))
                for s,ds in suite.items()]}
    opt={s:exact_baseline(ds) for s,ds in suite.items()}
    scored=summarize(suite,raw,opt)['fifo']
    assert scored['all_proven']
    assert all(x['optimality_gap_missed_cases'] is not None for x in scored['cases'])
    unproven={s:dict(x,status='FEASIBLE') for s,x in opt.items()}
    assert all(x['optimality_gap_missed_cases'] is None for x in summarize(suite,raw,unproven)['fifo']['cases'])


def test_public_consistency_feedback_has_no_oracle_and_does_not_relabel():
    payload={'independent_implementation_test':'PASS: FIFO tests pass',
            'business_goal':'Reduce missed deadlines','synthetic_dev_observation':'FIFO misses 8 deadlines',
            'evidence':[{'evidence_id':'SIM-1'}], 'real_customer_interviews':[]}
    bad={'implementation_assessment':'incorrect','classification':'implementation_bug',
         'supporting_evidence_ids':['IMAGINED'],'real_customer_validity':'unverified',
         'suggested_requirement_change':'keep strict FIFO and prioritize deadline'}
    f=dp.public_fact_checks(payload,bad)
    assert not f['oracle_or_expected_labels_exposed']
    assert len(f['input_only_feedback'])>=2
    assert bad['classification']=='implementation_bug'
    assert not any(x in json.dumps(f).lower() for x in ('expected_classification','expected_evidence_ids','gold label'))


def test_benchmark_repair_preserves_initial_and_fresh_blind_is_not_revised(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    first_calls=[];second_calls=[]
    async def first(payload,*,model):
        first_calls.append(payload)
        return llm.BenchmarkDiagnosis(
            classification='implementation_bug',implementation_assessment='incorrect',
            synthetic_requirement_fit='unverified',real_customer_validity='unverified',
            supporting_evidence_ids=['BAD-ID'], root_cause='incorrect raw interpretation of implementation',
            suggested_requirement_change='Keep strict FIFO',scheduling_precedence='fifo_first',
            change_required=True,remaining_uncertainty='Real customer unverified')
    async def revised(payload,*,prior,visible_feedback,model):
        second_calls.append({'payload':payload,'prior':prior,'feedback':visible_feedback,'model':model})
        assert 'oracle' not in json.dumps({'payload':payload,'feedback':visible_feedback})
        assert visible_feedback and 'PASS' in str(visible_feedback)
        return good_case_response('fifo_sla_conflict')
    monkeypatch.setattr(llm,'benchmark_diagnosis',first)
    monkeypatch.setattr(llm,'revise_benchmark_diagnosis',revised)
    c=TestClient(main.app)
    response=c.post('/api/diagnostic-benchmark/run',json={'case_ids':['fifo_sla_conflict'],
                  'repetitions':1,'enable_repair':True,'blind_generalization':True})
    assert response.status_code==200,response.text
    rec=response.json()
    assert rec['summary']['coding']['initial_passed']==0
    assert rec['summary']['coding']['passed']==1
    assert rec['summary']['finance']['initial_passed']==0
    assert rec['summary']['finance']['passed']==1
    assert len(second_calls)==2
    assert len(first_calls)==6  # 2 selected + 4 blind first-pass-only
    assert rec['blind_generalization']['enabled']
    assert len(rec['blind_generalization']['trials'])==4
    assert all(x['revision_allowed'] is False for x in rec['blind_generalization']['trials'])
    assert all(t['initial_diagnosis']['classification']=='implementation_bug' for t in rec['trials'])
    assert all(t['diagnosis']['classification']=='requirement_mismatch' for t in rec['trials'])
    assert c.get(f"/api/artifacts/benchmarks/{rec['benchmark_id']}/bundle").status_code==200


def test_proposal_assisted_rediagnosis_audits_initial_and_final(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    # Both initial diagnoses are intentionally wrong, but repairs are model calls.
    async def incorrect_qwen(*args,**kwargs):
        return llm.Diagnosis(classification='implementation_bug',supporting_evidence_ids=[],
          reasoning='The implementation is broken, not the FIFO contract.',
          suggested_requirement_change='Keep strict FIFO',remaining_uncertainty='unknown')
    async def incorrect_oda(*args,**kwargs):
        return llm.FinanceDiagnosis(classification='implementation_bug',
          r0_implementation_assessment='incorrect',business_requirement_assessment='unverified',
          supporting_evidence_ids=[],root_cause='Incorrect conclusion that FIFO software is broken.',
          suggested_requirement_change='Keep strict FIFO',remaining_uncertainty='unknown')
    async def proper_revision(dev,condition,*,previous,feedback,finance):
        assert condition=='counterexample'
        assert 'implementation bug' not in str(feedback).lower() or len(feedback)>0
        if finance:
            return llm.FinanceDiagnosis(classification='requirement_mismatch',
             r0_implementation_assessment='correct',business_requirement_assessment='mismatch',
             synthetic_requirement_fit='mismatch',supporting_evidence_ids=['SIM-SLA-001'],
             root_cause='Code correctly implements FIFO but observed synthetic deadline goals conflict with the FIFO requirement.',
             suggested_requirement_change='Replace strict FIFO with deadline-first ordering, FIFO only as tie-breaker.',
             scheduling_precedence='deadline_first_fifo_tiebreak',
             remaining_uncertainty='Real customers unverified')
        return llm.Diagnosis(classification='requirement_mismatch',
          supporting_evidence_ids=['SIM-SLA-001'],reasoning='FIFO code is correct, the business requirement is mismatched.',
          suggested_requirement_change='Replace strict FIFO with deadline-first, FIFO as tie-breaker.',
          remaining_uncertainty='Not customer validated')
    monkeypatch.setattr(llm,'diagnosis',incorrect_qwen)
    monkeypatch.setattr(llm,'finance_diagnosis',incorrect_oda)
    monkeypatch.setattr(llm,'revise_proposal_diagnosis',proper_revision)
    c=TestClient(main.app)
    r0=c.post('/api/run-r0',json={'brief':main.BRIEF}).json()
    r=c.post('/api/propose',json={'r0_run_id':r0['run_id'],
                         'enable_repair':True,'evidence_condition':'counterexample'})
    assert r.status_code==200,r.text
    x=r.json()
    assert x['diagnosis_matches_rubric'] is True
    assert x['finance_diagnosis_matches_rubric'] is True
    assert x['diagnostic_initial_scores']['oda']['pass'] is False
    assert x['diagnostic_initial_scores']['qwen']['pass'] is False
    assert x['diagnostic_repair']['attempts']['oda']['revised'] is True
    root=main.path_for('proposals',x['proposal_id'])
    assert json.loads((root/'oda_diagnosis.json').read_text())['classification']=='implementation_bug'
    assert json.loads((root/'oda_diagnosis_final.json').read_text())['classification']=='requirement_mismatch'
    assert (root/'diagnostic_repair_audit.json').exists()


def test_full_run_generates_new_blind_json_and_integrity(client,monkeypatch):
    from test_full_run_v015 import _start
    monkeypatch.setattr(main,'run_in_e2b',mock_sandbox_with_actual_skill)
    st=_start(client,monkeypatch)
    approved=client.post('/api/full-run/approve-and-continue',json={
      'workflow_id':st['workflow_id'],'approval':{
       'proposal_id':st['review']['proposal_id'],'decision':'approved',
       'actor':'Reviewer','rationale':'Synthetic only'}})
    assert approved.status_code==200,approved.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='COMPLETE',final
    assert final['blind_optimality']['post_selection_only'] is True
    assert len(final['blind_optimality']['solver_status'])==4
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        data=json.loads(z.read('manifest.json'))
        assert data['status']=='COMPLETE',data
        assert any(x['path'].endswith('08f_blind_optimality.json') for x in data['files'])
        assert any('08f_dataset_' in x['path'] for x in data['files'])
        for entry in data['files']:
            assert hashlib.sha256(z.read(entry['path'])).hexdigest()==entry['sha256_raw_bytes']
