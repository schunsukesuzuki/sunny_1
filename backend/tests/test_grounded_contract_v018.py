"""v0.18 evidence topic gate, source provenance and bounded executable KPI contract."""
import hashlib
import json
import pytest
from fastapi import HTTPException
from app import grounded_contract as gc, evidence_rag as er
from test_full_run_evidence_v017 import fixed_insurance_corpus, start_public, approve_public
from test_outer_loop_v08 import client


def test_uk_html_sources_are_extracted_and_provenance_kept(fixed_insurance_corpus):
    data=er.ensure_index('insurance_claims_uk')
    assert data['chunk_count']>0
    hits=er.requirements('insurance_claims_uk','insurance claim delays')
    assert hits['topic_alignment']['status']=='TOPIC_MATCH_REVIEW_REQUIRED'
    assert hits['topic_alignment']['topic_matching_evidence_ids']
    assert hits['alternative_cause_search']['status']=='POTENTIAL_ALTERNATIVES_ONLY_NOT_VALIDATED'
    assert any(e['reference_status']=='EXTRACTED_HTML_TEXT' for e in hits['evidence'])
    assert all(e['source_url'].startswith('https://') for e in hits['evidence'])
    assert not any(e['source_url'].endswith('/records/10425908') for e in hits['evidence'])


def test_public_banking_source_never_matches_insurance_claims(fixed_insurance_corpus):
    res=er.topic_alignment('community_credit','insurer claim delays',[], 'insurance_claims')
    assert res['status']=='DOMAIN_MISMATCH'


def test_bounded_thresholds_not_llm_code():
    c=gc.compile_contract(requirement='Investigate insurance claim delays and reviewer processing times',evidence_ids=['PUB-001'],max_missed=1,min_reduction_pct=75)
    assert c['evaluator_mutable_by_llm'] is False
    assert c['evaluator']=='PINNED_DETERMINISTIC_SYNTHETIC_HOLDOUT'
    assert 'fixed synthetic' in gc.spec_md(c)
    for x in (-1,101,True):
        with pytest.raises(ValueError):gc.compile_contract(requirement=c['hypothesis'],evidence_ids=['PUB-001'],max_missed=x,min_reduction_pct=50)


def test_threshold_evaluator_pass_and_human_strict_fail():
    exp={'holdout_executed':True,'holdout':{
        'fifo':[{'seed':40,'valid':True,'assigned_hours':10,'missed_deadlines':4}],
        'generated':[{'seed':40,'valid':True,'assigned_hours':10,'missed_deadlines':1}]}}
    pol={'status':'COMPLETED','results':{'behavior_pass':True}}
    a=gc.compile_contract(requirement='Insurance claim delays could be reduced via prioritization',evidence_ids=['PUB-001'],max_missed=1,min_reduction_pct=75)
    assert gc.evaluate(a,exp,pol)['synthetic_pass'] is True
    b=gc.compile_contract(requirement=a['hypothesis'],evidence_ids=['PUB-001'],max_missed=0,min_reduction_pct=75)
    assert gc.evaluate(b,exp,pol)['status']=='HOLD'
    assert gc.evaluate(a,exp,{'status':'COMPLETED','results':{'behavior_pass':False}})['status']=='HOLD'
    assert gc.evaluate(a,{'holdout':{}},None)['status']=='HOLD'


def test_seed_and_hours_swaps_cannot_silently_pass():
    c=gc.compile_contract(requirement='Insurance claim delays and handling time evaluation',evidence_ids=['PUB-001'],max_missed=0,min_reduction_pct=50)
    x={'holdout_executed':True,'holdout':{'fifo':[{'seed':4,'valid':True,'assigned_hours':8,'missed_deadlines':6}],
                                           'generated':[{'seed':7,'valid':True,'assigned_hours':8,'missed_deadlines':0}]}}
    assert gc.evaluate(c,x,None)['status']=='HOLD'
    x['holdout']['generated'][0]['seed']=4
    x['holdout']['generated'][0]['assigned_hours']=7
    assert gc.evaluate(c,x,None)['status']=='HOLD'


def test_public_hypothesis_cannot_jump_to_digital_banking(fixed_insurance_corpus,client,monkeypatch):
    state=start_public(client,monkeypatch,query='insurance claims delays',dataset='insurance_claims_uk')
    ids=state['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    response=approve_public(client,state,ids=ids,text='Improve mobile banking user experience and credit union access fees')
    assert response.status_code==422
    assert client.get('/api/full-run/'+state['workflow_id']).json()['linked_ids']['runs'] is None


def test_human_context_only_does_not_trigger_synthetic_r0(fixed_insurance_corpus,client,monkeypatch):
    state=start_public(client,monkeypatch,query='insurance claim delays',dataset='insurance_claims_uk')
    ids=state['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    resp=client.post('/api/full-run/review-evidence',json={'workflow_id':state['workflow_id'],
          'decision':'approved','actor':'Reviewer','rationale':'Document is relevant but does not support workflow choice',
          'evidence_ids':ids,'approved_requirement':'Insurance claims delays are a topic for further investigation',
          'support_assessment':'context_only'})
    assert resp.status_code==422
    assert client.get('/api/full-run/'+state['workflow_id']).json()['status']=='AWAITING_EVIDENCE_REVIEW'
