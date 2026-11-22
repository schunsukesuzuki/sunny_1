"""v0.29 regression for objective alignment, research-only tie, and oracle-free repair."""
from __future__ import annotations
import asyncio
from types import SimpleNamespace
from app import blind_optimality as bo
from app import selection_gap_analysis as gap
from app import dev_robustness as dev
from app import diagnostic_targeted_repair as dtr
from app.diagnostic_benchmark import FIXTURES
from app import llm


def test_08f_lexicographic_gap_finds_secondary_loss_even_when_missed_ties(monkeypatch):
    suite={1:{'seed':1,'dataset':'same'}}
    def fake_validation(ds,out,policy):
        return {'valid':True,'missed_deadlines':out['missed'], 'unassigned_cases':out['unassigned']}
    monkeypatch.setattr(bo,'validate',fake_validation)
    def raw(m,u):
        return SimpleNamespace(seed=1,output={'missed':m,'unassigned':u},error=None,elapsed_seconds=0.1)
    oracle={1:{'status':'OPTIMAL','metrics':{'valid':True,'missed_deadlines':2,'unassigned_cases':0}}}
    results=bo.summarize(suite,{'selected':[raw(2,1)],'skill_bounded_beam':[raw(2,0)]},oracle)
    selected=results['selected']['cases'][0]
    assert selected['optimality_gap_missed_cases']==0
    assert selected['optimality_gap_unassigned_conditional']==1
    assert selected['lexicographic_optimal'] is False
    assert results['selected']['proven_optimal_cases']==0
    assert results['skill_bounded_beam']['proven_optimal_cases']==1
    review=gap.analyze(selected_engine='skill_deadline_scarcity',dev_audit={},
                       blind_metrics=results,random_seed=9)
    assert review['status']=='POST_SELECTION_GAP_DETECTED'
    assert review['comparisons'][0]['primary_ties_secondary_losses']==1
    assert review['comparisons'][0]['selected_worse']==1
    assert not review['fed_back_to_dev_selection']


def test_nonoptimal_oracle_and_invalid_output_are_not_certified(monkeypatch):
    monkeypatch.setattr(bo,'validate',lambda ds,out,policy: {'valid':True,'missed_deadlines':0,'unassigned_cases':0})
    oracle={1:{'status':'FEASIBLE','metrics':{'valid':True,'missed_deadlines':0,'unassigned_cases':0}}}
    rs=bo.summarize({1:{'seed':1}}, {'selected':[SimpleNamespace(seed=1,output={},error=None,elapsed_seconds=0)]},oracle)
    assert rs['selected']['cases'][0]['optimality_gap_unassigned_conditional'] is None
    assert rs['selected']['all_proven'] is False


def _candidate(name, unassigned, missed=1):
    return {'engine':name,'candidate_id':name,'source_sha256':name,
      'eligible':True,'dev_score':[0,0],
      'dev_case_metrics':[{'seed':42,'valid':True,'missed_deadlines':0,'unassigned_cases':0}],
      'stress_checks':[{'seed':s,'scenario':f'STRESS_{s}',
        'generated':{'valid':True,'missed':missed,'unassigned':unassigned},
        'deadline':{'valid':True,'missed':2,'unassigned':0}}
        for s in sorted(dev.EXPECTED_STRESS_SEEDS)]}


def test_tied_candidates_explicitly_provisional_not_production_approved():
    res=dev.choose([_candidate('a',0),_candidate('b',0)])
    assert res['status']=='TIE_UNRESOLVED_BY_DEV'
    assert res['case_discrimination']['status']=='NO_SEPARATING_CASES'
    review=res['selection_review']
    assert review['status']=='PROVISIONAL_RESEARCH_SELECTION_REVIEW_REQUIRED'
    assert review['requires_human_review']
    assert review['research_execution_allowed']
    assert review['production_selection_authorized'] is False
    assert review['review_performed'] is False


def test_dev_discriminator_identifies_unassigned_condition_without_08f_leakage():
    res=dev.choose([_candidate('a',0),_candidate('b',1)])
    assert res['case_discrimination']['case_count_discriminative']==4
    assert res['case_discrimination']['08f_or_holdout_used'] is False
    assert res['selected_engine']=='a'


def test_targeted_repair_never_modifies_untargeted_fields_or_reads_oracle():
    visible=FIXTURES['fifo_sla_conflict']['input']
    raw=llm.BenchmarkDiagnosis(classification='requirement_mismatch',implementation_assessment='correct',
        synthetic_requirement_fit='unverified',real_customer_validity='unverified',
        supporting_evidence_ids=['SIM-SLA-001'],root_cause='Correct FIFO misses the deadline goal.',
        suggested_requirement_change='Use deadlines as first priority and FIFO for ties.',
        scheduling_precedence='deadline_first_fifo_tiebreak',change_required=True,
        remaining_uncertainty='No customer validation').model_dump()
    plan=dtr.plan(visible,raw)
    assert 'synthetic_requirement_fit' in plan['target_fields']
    assert 'classification' not in plan['target_fields']
    assert plan['selection_uses_oracle'] is False
    suggestion={**raw,'synthetic_requirement_fit':'mismatch',
                'classification':'implementation_bug'}
    merged=dtr.adopt(raw,suggestion,plan['target_fields'])
    assert merged['answer']['synthetic_requirement_fit']=='mismatch'
    assert merged['answer']['classification']=='requirement_mismatch'
    assert merged['discarded_out_of_scope_model_edits']==['classification']
    assert merged['all_untargeted_fields_preserved']


def test_older_primary_only_gap_stays_inconclusive_for_secondary():
    def row(miss,gapv):
        return {'seed':1,'input_sha256':'s','missed_deadlines':miss,'optimality_gap_missed_cases':gapv}
    rs=gap.analyze(selected_engine='a',dev_audit={},blind_metrics={'selected':{'cases':[row(2,0)]},'other':{'cases':[row(2,0)]}},random_seed=1)
    assert rs['status']=='INCONCLUSIVE_UNCERTIFIED'
    assert rs['comparisons'][0]['excluded_secondary_unknown_cases']==1
