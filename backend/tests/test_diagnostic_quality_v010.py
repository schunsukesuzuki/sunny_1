"""v0.10: semantic red flags, synthetic-vs-external separation, replay and model comparison."""
from __future__ import annotations
import json
from fastapi.testclient import TestClient
from app import main, llm
from app.diagnostic_quality import (contradictory_fifo_precedence, implementation_contradiction,
                                    legacy_diagnostic_score, benchmark_score)
from app.diagnostic_benchmark import FIXTURES


def good_case_response(case_id: str) -> llm.BenchmarkDiagnosis:
    oracle=FIXTURES[case_id]['oracle']
    is_req=oracle['classification']=='requirement_mismatch'
    return llm.BenchmarkDiagnosis(
        classification=oracle['classification'],
        implementation_assessment=oracle['implementation_assessment'],
        synthetic_requirement_fit=oracle['synthetic_requirement_fit'],
        real_customer_validity='unverified',
        supporting_evidence_ids=oracle['expected_evidence_ids'],
        root_cause='Independent evaluator and available synthetic observations support this cause; no real client proof.',
        suggested_requirement_change=('Replace strict FIFO with deadline-first ordering and arrival order only as tie-breaker.'
                                      if is_req else 'No requirement change is justified by this evidence.'),
        scheduling_precedence='deadline_first_fifo_tiebreak' if is_req else 'none',
        change_required=is_req, remaining_uncertainty='External client needs verification')


def test_replay_actual_v091_mistakes_detection():
    qwen={'classification':'requirement_mismatch','supporting_evidence_ids':['SIM-SLA-001'],
          'reasoning':'This violates the core FIFO principle of processing in arrival order.',
          'suggested_requirement_change':'FIFO must also prioritize deadline constraints when equal priority cases exist'}
    oda={'classification':'requirement_mismatch','r0_implementation_assessment':'correct',
         'business_requirement_assessment':'unverified','supporting_evidence_ids':[],
         'root_cause':'R0 contract mandates FIFO but this produces missed SLA deadlines.',
         'suggested_requirement_change':'Prioritize earlier absolute deadlines while maintaining FIFO arrival_order.'}
    q=legacy_diagnostic_score(qwen,condition='counterexample',is_vertical=False)
    d=legacy_diagnostic_score(oda,condition='counterexample',is_vertical=True)
    assert not q['pass'] and 'EXPLANATION_CONTRADICTS_R0_PASS' in q['failure_codes']
    assert not d['pass'] and 'CONFLICT_FIFO_AND_DEADLINE_PRIORITY' in d['failure_codes']
    assert 'EVIDENCE_IDS_INCORRECT' in d['failure_codes']
    assert d['real_customer_business_validity']=='UNVERIFIED'
    assert d['synthetic_requirement_fit']=='mismatch'


def test_valid_tiebreaker_does_not_trigger_false_positive():
    assert contradictory_fifo_precedence('Replace FIFO: deadline first, arrival order only as a tie-breaker')==[]
    assert contradictory_fifo_precedence('Prioritize deadlines while maintaining strict FIFO')
    assert not implementation_contradiction('The outcome is not a software bug, FIFO passes.',r0_pass=True)


def test_benchmark_fixed_oracles_for_all_four():
    for case_id, f in FIXTURES.items():
        output=good_case_response(case_id)
        score=benchmark_score(output.model_dump(),f['oracle'])
        assert score['passed'], (case_id,score)
        assert score['real_customer_business_validity']=='UNVERIFIED'


def test_benchmark_rejects_classification_only_correct():
    f=FIXTURES['fifo_sla_conflict']
    bad=good_case_response('fifo_sla_conflict').model_copy(update={
        'root_cause':'This violates the core FIFO principle, hence the implementation is a software bug.',
        'supporting_evidence_ids':[],
        'suggested_requirement_change':'Prioritize deadlines while maintaining strict FIFO arrival_order.',
        'scheduling_precedence':'fifo_first'})
    score=benchmark_score(bad.model_dump(), f['oracle'])
    assert score['checks']['cause_classification']
    assert not score['passed'] and score['score'] < 1
    assert not score['checks']['no_conflicting_revision_policy']
    assert not score['checks']['no_implementation_contradiction']
    assert not score['checks']['evidence_traceability']


def test_benchmark_route_sends_same_fixture_to_both_models_and_saves(monkeypatch, tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    seen=[]
    async def mock_query(payload,*,model):
        seen.append((payload,model))
        return good_case_response('fifo_sla_conflict')
    monkeypatch.setattr(llm,'benchmark_diagnosis',mock_query)
    c=TestClient(main.app)
    r=c.post('/api/diagnostic-benchmark/run',json={'case_ids':['fifo_sla_conflict'],'repetitions':2})
    assert r.status_code==200,r.text
    x=r.json()
    assert len(seen)==4 and len(x['trials'])==4
    assert seen[0][0] == seen[1][0] == seen[2][0] == seen[3][0]
    assert 'oracle' not in json.dumps(seen)
    assert x['summary']['coding']['passed']==2
    assert x['summary']['finance']['passed']==2
    assert c.get('/api/history/benchmarks').status_code==200
    assert c.get(f'/api/artifacts/benchmarks/{x["benchmark_id"]}/bundle').status_code==200
    report=c.get(f'/api/diagnostic-benchmark/{x["benchmark_id"]}/report')
    assert report.status_code==200 and 'UNVERIFIED' in report.text


def test_model_failure_is_logged_separately_and_not_replaced(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    async def mock_query(payload,*,model):
        if model==llm.FINANCE_MODEL: raise RuntimeError('ODA model unavailable')
        return good_case_response('fifo_sla_conflict')
    monkeypatch.setattr(llm,'benchmark_diagnosis',mock_query)
    x=TestClient(main.app).post('/api/diagnostic-benchmark/run',json={
        'case_ids':['fifo_sla_conflict'],'repetitions':1}).json()
    assert x['status']=='COMPLETED_WITH_ERRORS'
    assert x['summary']['finance']['failed_calls']==1
    assert x['summary']['coding']['passed']==1
    assert any(t['model_role']=='finance' and 'ODA model unavailable' in t.get('error','') for t in x['trials'])


def test_read_only_rescore_does_not_modify_prior_proposal(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    pid=main.fresh_id()
    payload={'proposal_id':pid,'condition':'counterexample',
        'diagnosis':{'classification':'requirement_mismatch','supporting_evidence_ids':['SIM-SLA-001'],
                     'reasoning':'This violates the core FIFO principle','suggested_requirement_change':'Prioritize deadlines'},
        'finance_diagnosis':{'classification':'requirement_mismatch','r0_implementation_assessment':'correct',
                   'business_requirement_assessment':'unverified','supporting_evidence_ids':[],
                   'root_cause':'FIFO delays short-deadline cases but implementation matches spec',
                   'suggested_requirement_change':'Prioritize deadlines while maintaining FIFO arrival_order'},
        'finance_diagnosis_matches_rubric':False}
    main.store('proposals',pid,'proposal.json',payload)
    path=tmp_path/'proposals'/pid/'proposal.json'
    old=path.read_bytes()
    r=TestClient(main.app).get(f'/api/diagnostic-benchmark/rescore/{pid}')
    assert r.status_code==200,r.text
    result=r.json()
    assert result['historical_record_modified'] is False
    assert not result['qwen']['pass'] and not result['oda']['pass']
    assert path.read_bytes()==old


def test_reject_stale_override_when_oda_says_correct(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    from test_outer_loop_v08 import fake_runner,fake_diagnosis
    monkeypatch.setattr(main,'run_in_e2b',fake_runner)
    monkeypatch.setattr(llm,'diagnosis',fake_diagnosis)
    async def mock_domain(*a):
        return llm.FinanceDiagnosis(classification='requirement_mismatch',
          r0_implementation_assessment='correct',business_requirement_assessment='unverified',
          supporting_evidence_ids=[],root_cause='FIFO passes independent implementation but misses deadlines',
          suggested_requirement_change='Prioritize deadlines while maintaining FIFO arrival_order',
          remaining_uncertainty='No real-world business evidence')
    monkeypatch.setattr(llm,'finance_diagnosis',mock_domain)
    c=TestClient(main.app)
    r0=c.post('/api/run-r0',json={'brief':main.BRIEF}).json()
    p=c.post('/api/propose',json={'r0_run_id':r0['run_id']}).json()
    assert p['finance_diagnosis_matches_rubric'] is False
    response=c.post('/api/approve',json={'proposal_id':p['proposal_id'],'actor':'Claims manager',
       'decision':'approved','rationale':'Synthetic case only','domain_review_override':True,
       'acknowledges_independent_r0_pass':True,
       'override_rationale':'ODAはincorrectと誤判定した。模擬反例によるKPI検証を継続する。'})
    assert response.status_code==422
    assert '矛盾' in response.text
