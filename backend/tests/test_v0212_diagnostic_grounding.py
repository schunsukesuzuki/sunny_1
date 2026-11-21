"""v0.21.2: preserve raw LLM failures and audit input-grounded citation assistance.
No oracle, gold label, or hidden rubric feedback is sent back to a model.
"""
from __future__ import annotations
import json
from fastapi.testclient import TestClient
from app import diagnostic_protocol as dp, diagnostic_quality as dq, main, llm
from app.diagnostic_benchmark import FIXTURES
from test_diagnostic_quality_v010 import good_case_response


def test_input_fact_sheet_is_observation_not_gold():
    payload=FIXTURES['fifo_sla_conflict']['input']
    fact=dp.observable_fact_sheet(payload)
    assert fact['independent_test_reported_status']=='PASS'
    assert fact['available_evidence'][0]['id']=='SIM-SLA-001'
    assert 'oracle' not in json.dumps(fact)
    assert 'expected_classification' not in json.dumps(fact)
    assert fact['business_goal_verbatim']==payload['business_goal']


def test_correct_qwen_missing_synthetic_id_assisted_pass_raw_fail():
    case=FIXTURES['fifo_sla_conflict']
    pred=good_case_response('fifo_sla_conflict').model_dump()
    pred['supporting_evidence_ids']=[]
    pred['root_cause']='FIFO code conforms to contract but deadline KPI is missed for later urgent claims.'
    raw=dq.benchmark_score(pred,case['oracle'])
    assert raw['failure_codes']==['EVIDENCE_TRACEABILITY']
    assisted=dp.evidence_bind_from_input(case['input'],pred)
    assert assisted['applied'] and assisted['added_evidence_ids']==['SIM-SLA-001']
    assert assisted['raw_answer']['supporting_evidence_ids']==[]
    assert dq.benchmark_score(assisted['assisted_answer'],case['oracle'])['passed']


def test_correct_fifo_bug_missing_id_assisted_pass_raw_fail():
    case=FIXTURES['actual_fifo_implementation_bug']
    pred=good_case_response('actual_fifo_implementation_bug').model_dump()
    pred['supporting_evidence_ids']=[]
    pred['root_cause']='The implementation violates FIFO arrival order with a queue inversion.'
    assert not dq.benchmark_score(pred,case['oracle'])['passed']
    bound=dp.evidence_bind_from_input(case['input'],pred)
    assert bound['added_evidence_ids']==['SIM-BUG-001']
    assert dq.benchmark_score(bound['assisted_answer'],case['oracle'])['passed']


def test_wrong_oda_classification_cannot_be_repaired_by_binder():
    case=FIXTURES['fifo_sla_conflict']
    pred=good_case_response('fifo_sla_conflict').model_dump()
    pred.update(classification='insufficient_evidence',implementation_assessment='incorrect',
                supporting_evidence_ids=[],root_cause='The business goal and R0 contract contradict each other.')
    assisted=dp.evidence_bind_from_input(case['input'],pred)
    assert not assisted['applied']
    result=dq.benchmark_score(assisted['assisted_answer'],case['oracle'])
    assert not result['passed']
    assert not result['checks']['implementation_correctness']


def test_no_fabricated_or_ambiguous_evidence_autocorrection():
    pred=good_case_response('fifo_sla_conflict').model_dump()
    pred['supporting_evidence_ids']=['FAKE-ID']
    x=dp.evidence_bind_from_input(FIXTURES['fifo_sla_conflict']['input'],pred)
    assert not x['applied'] and x['assisted_answer']['supporting_evidence_ids']==['FAKE-ID']
    pred['supporting_evidence_ids']=[]
    many=FIXTURES['conflicting_stakeholder_notes']['input']
    assert not dp.evidence_bind_from_input(many,pred)['applied']
    assert not dp.evidence_bind_from_input(FIXTURES['correct_fifo_no_customer_evidence']['input'],pred)['applied']


def test_api_preserves_raw_and_reports_assisted_without_model_repair(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    calls=[]
    async def missing_citation(payload,*,model):
        calls.append(model)
        ans=good_case_response('fifo_sla_conflict').model_copy(deep=True)
        return ans.model_copy(update={
            'root_cause':'Correct FIFO code does not satisfy the observed synthetic deadline objective.',
            'supporting_evidence_ids':[]})
    async def no_revision(*args,**kwargs):
        raise AssertionError('No model repair should be necessary once ONLY the missing ID is bound')
    monkeypatch.setattr(llm,'benchmark_diagnosis',missing_citation)
    monkeypatch.setattr(llm,'revise_benchmark_diagnosis',no_revision)
    c=TestClient(main.app)
    resp=c.post('/api/diagnostic-benchmark/run',json={'case_ids':['fifo_sla_conflict'],
        'repetitions':1,'enable_repair':True,'blind_generalization':False})
    assert resp.status_code==200,resp.text
    result=resp.json()
    assert len(calls)==2
    assert result['summary']['coding']['initial_passed']==0
    assert result['summary']['coding']['raw_final_passed']==0
    assert result['summary']['coding']['assisted_final_passed']==1
    assert result['summary']['finance']['raw_final_passed']==0
    assert result['summary']['finance']['assisted_final_passed']==1
    assert result['summary']['coding']['revised_calls']==0
    trial=result['trials'][0]
    assert trial['latest_raw_diagnosis']['supporting_evidence_ids']==[]
    assert trial['diagnosis']['supporting_evidence_ids']==['SIM-SLA-001']
    assert not trial['initial_rubric']['passed'] and trial['rubric']['passed']
    report=c.get(f"/api/diagnostic-benchmark/{result['benchmark_id']}/report").text
    assert 'initial raw PASS' in report and 'assisted PASS' in report


def test_fresh_blind_raw_is_unchanged_and_no_repair(monkeypatch,tmp_path):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    calls=[]
    async def response(payload,*,model):
        calls.append(model)
        test=str(payload.get('independent_implementation_test',''))
        # Build a model answer from public facts only, deliberately omit IDs.
        if test.startswith('FAIL'):
            cls='implementation_bug'; impl='incorrect'; fit='unverified'; change=False
            explanation='Implementation breaks FIFO order by inversion of two feasible claims.'
            policy='none'
        else:
            cls='requirement_mismatch';impl='correct';fit='mismatch';change=True
            explanation='Correct FIFO contract causes synthetic deadline misses under the business objective.'
            policy='deadline_first_fifo_tiebreak'
        return llm.BenchmarkDiagnosis(
            classification=cls,implementation_assessment=impl,synthetic_requirement_fit=fit,
            real_customer_validity='unverified',supporting_evidence_ids=[],root_cause=explanation,
            suggested_requirement_change=('Replace FIFO with deadline-first ordering and FIFO as a tie-breaker.' if change else 'Do not change the approved FIFO requirement.'),
            scheduling_precedence=policy,change_required=change,
            remaining_uncertainty='Synthetic evidence only')
    async def no_revision(*args,**kwargs):
        raise AssertionError('Fresh blind cases cannot receive revision')
    monkeypatch.setattr(llm,'benchmark_diagnosis',response)
    monkeypatch.setattr(llm,'revise_benchmark_diagnosis',no_revision)
    result=TestClient(main.app).post('/api/diagnostic-benchmark/run',json={
        'case_ids':['fifo_sla_conflict'],'repetitions':1,
        'enable_repair':False,'blind_generalization':True}).json()
    blind=result['blind_generalization']
    assert len(calls)==6
    assert blind['summary']['coding']['passed']==0
    assert blind['summary']['coding']['assisted_passed']==2
    assert all(not x['revision_allowed'] for x in blind['trials'])
    assert all(not x['rubric']['passed'] and x['assisted_rubric']['passed'] for x in blind['trials'])


def test_business_assessment_does_not_count_harness_assist_as_raw_model_pass():
    from app.business_assessment import assess
    run={'run_id':'run-demo','implementation_validity':'PASS'}
    prop={'proposal_id':'prop-demo','condition':'counterexample',
          'diagnosis_matches_rubric':True,'finance_diagnosis_matches_rubric':True}
    approval={'approval_id':'a-demo','decision':'approved','domain_review_override':False}
    exp={'experiment_id':'e-demo','holdout_executed':True,
         'r1_independent_kpi_improvement_pass':True,'selected_code_sha256':'demo',
         'dev_seeds':[1],'holdout_seeds':[2],
         'holdout':{'fifo':[{'valid':True,'seed':2,'assigned_hours':4,'missed_deadlines':2}],
                    'generated':[{'valid':True,'seed':2,'assigned_hours':4,
                                  'missed_deadlines':0,'sandbox_id':'fake'}]}}
    benchmark={'benchmark_id':'synthetic-benchmark','status':'COMPLETED','summary':{
        k:{'planned':2,'completed':2,'passed':2,'raw_final_passed':0,
           'assisted_final_passed':2,'initial_passed':0,'mean_score':1.0}
        for k in ('coding','finance')},
        'blind_generalization':{'enabled':True,'summary':{
            k:{'planned':2,'completed':2,'passed':0,'assisted_passed':2}
            for k in ('coding','finance')}}}
    x=assess(exp,run,prop,approval,code_integrity=True,benchmark=benchmark)
    assert x['decision']['automatic_diagnosis_accepted'] is False
    assert x['summary_metrics']['benchmark_by_model']['coding']['passed']==0
    assert x['summary_metrics']['benchmark_harness_assisted_pass_by_model']['coding']==2
    assert x['summary_metrics']['benchmark_fresh_blind_summary']['finance']['passed']==0
