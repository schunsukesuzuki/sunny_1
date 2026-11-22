"""v0.31: real source IDs, current canonical benchmark, stale drafts and revision delta.

No Ollama/E2B in these tests: fake model outputs are NOT quality evidence.
"""
import json
from uuid import uuid4
from copy import deepcopy
from fastapi.testclient import TestClient
import pytest
from app import main, advisory
from test_v030_advisory_loop import fake_draft, setup


def _write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def test_stale_after_latest_benchmark_and_manual_regeneration(tmp_path, monkeypatch):
    wid, state=setup(tmp_path,monkeypatch)
    bid=str(uuid4())
    state['linked_ids']['benchmarks']=bid
    _write_json(tmp_path/'workflows'/wid/'workflow.json',state)
    benchmark={'benchmark_id':bid,'retry_history':[], 'summary':{},'status':'COMPLETED',
        'reliability_gate':{'status':'HOLD_HUMAN_ADJUDICATION',
        'execution_status':'COMPLETE','quality_status':'HOLD_HUMAN_ADJUDICATION'}}
    main.store('benchmarks',bid,'benchmark.json',benchmark)
    calls=[]
    async def model(context, constraints):
        calls.append(context['diagnostic_retry_count'])
        return fake_draft()
    monkeypatch.setattr(advisory,'generate',model)
    client=TestClient(main.app)
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}}).status_code==200
    first=client.get(f'/api/full-run/{wid}/advisory').json()
    assert first['status']=='DRAFT_UNAPPROVED' and first['freshness_status']=='CURRENT_SOURCE'
    assert first['source_snapshot']['canonical_file_sha256']['benchmark.json']
    # Modify ONLY the authoritative benchmark; workflow status remains COMPLETE.
    benchmark['retry_history']=[{'status':'COMPLETED','id':'new-attempt'}]
    main_file=tmp_path/'benchmarks'/bid/'benchmark.json'
    _write_json(main_file,benchmark)
    stale=client.get(f'/api/full-run/{wid}/advisory').json()
    assert stale['status']=='STALE_ADVISORY' and stale['freshness_status']=='STALE_SOURCE'
    assert client.post(f'/api/full-run/{wid}/advisory/review',json={
        'version':1,'actor':'Reviewer','decision':'reviewed_as_draft',
        'rationale':'最新の診断結果と一致しないため承認しない。'}).status_code==409
    # No `regenerate:true` required when the persisted record is stale.
    second=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    assert second.status_code==200,second.text
    newest=client.get(f'/api/full-run/{wid}/advisory').json()
    assert newest['version']==2 and newest['status']=='DRAFT_UNAPPROVED'
    assert newest['revision_diff']['source_changed'] is True
    assert newest['revision_diff']['previous_version']==1
    assert newest['source_hash']!=first['source_hash']
    assert calls==[0,1]
    assert main.load('workflows',wid,'workflow.json')['status']=='COMPLETE'


def test_repacking_zip_does_not_invalidate_current_advisory(tmp_path,monkeypatch):
    wid,_=setup(tmp_path,monkeypatch)
    async def model(context,constraints):return fake_draft()
    monkeypatch.setattr(advisory,'generate',model)
    client=TestClient(main.app)
    client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    first=client.get(f'/api/full-run/{wid}/advisory').json()
    assert first['status']=='DRAFT_UNAPPROVED'
    # A review triggers ZIP regeneration and must not change the source state.
    review=client.post(f'/api/full-run/{wid}/advisory/review',json={
        'version':1,'actor':'PM reviewer','decision':'feedback_for_next_iteration',
        'rationale':'まずユーザーの実運用ルールと処理量を確認してから次の実験へ進める。'})
    assert review.status_code==200,review.text
    after=client.get(f'/api/full-run/{wid}/advisory').json()
    assert after['source_hash']==first['source_hash']
    assert after['status']=='DRAFT_UNAPPROVED'


def test_source_pointer_and_notification_feature_contract():
    report={'workflow_id':'foo', 'status':'COMPLETE','requirement_type':'claim_progress_updates',
        'feature_acceptance':{'status':'PASS_SYNTHETIC_FEATURE_ONLY','feature_id':'FEATURE-NOTIFY',
                              'requirement_id':'REQ-PUBLIC-001','integrated_service_acceptance':False},
        'reviewed_evidence':{'selected_evidence_ids':['PUB-001'],
          'approved_requirement_hypothesis':'通知遅延の問題が公表されている',
          'evidence_pointer_records':[{'evidence_id':'PUB-001','source_url':'https://example.org',
            'source_file':'src.html','quote':'顧客への通知が遅れていると報告される。'}]},
        'requirement_trace':{'requirement_id':'REQ-PUBLIC-001','feature_id':'FEATURE-NOTIFY',
            'type':'claim_progress_updates','acceptance_test_ids':['NOTIFY-WITHIN-THRESHOLD']},
        'business_assessment':{},'diagnostic':{'quality_status':'HOLD_HUMAN_ADJUDICATION'},
        'dev_case_discrimination':{'status':'NO_SEPARATING_CASES','case_count_discriminative':0}}
    context=advisory.compact_context(report,{'evidence_mode':'public','dataset_id':'insurance_claims_uk','brief':'合成ケースで保険請求を管理する。'})
    assert context['primary_requirement']['requirement_id']=='REQ-PUBLIC-001'
    assert context['source_register']['PUB-001']['kind']=='public_context_excerpt'
    assert {x['code'] for x in context['required_attention']}=={
        'NOTIFICATION_NOT_INTEGRATED','DIAGNOSTIC_HOLD','DEV_NON_DISCRIMINATIVE'}
    draft=fake_draft()
    for option in draft['technical_options']:
        option['target_requirement_ids']=['REQ-PUBLIC-001']
        option['solution']='通知ステータスの変更履歴を記録し、遅延と宛先を検証する。'
        option['direct_requirement_coverage']='direct'
    draft['next_experiments'][0]['evidence_ref']='08e_feature_acceptance.json'
    draft['customer_problem_hypotheses'][0]['source_refs']=['PUB-001']
    draft['customer_problem_hypotheses'][0]['evidence_status']='source_context'
    advisory.validate_draft(advisory.AdvisoryDraft(**draft).model_dump(),context)
    bad=deepcopy(draft);bad['technical_options'][0]['solution']='担当者割当の順位を改善する。'
    with pytest.raises(ValueError,match='Allocation-only'):
        advisory.validate_draft(advisory.AdvisoryDraft(**bad).model_dump(),context)
    bad=deepcopy(draft);bad['customer_problem_hypotheses'][0]['source_refs']=['PUB-999']
    with pytest.raises(ValueError,match='unknown provenance'):
        advisory.validate_draft(advisory.AdvisoryDraft(**bad).model_dump(),context)
    bad=deepcopy(draft);bad['technical_options'][0]['necessary_roles']=[]
    with pytest.raises(ValueError):
        advisory.AdvisoryDraft(**bad)
    bad=deepcopy(draft);bad['title']='English only technical proposal'
    with pytest.raises(ValueError,match='Japanese'):
        advisory.validate_draft(advisory.AdvisoryDraft(**bad).model_dump(),context)


def test_proposal_already_stale_when_model_finishes(tmp_path, monkeypatch):
    wid,state=setup(tmp_path,monkeypatch)
    async def modify_source_while_generating(context,constraints):
        current=main.load('workflows',wid,'workflow.json')
        current['updated_at']='2026-11-22T02:45:00+00:00'
        _write_json(tmp_path/'workflows'/wid/'workflow.json',current)
        return fake_draft()
    monkeypatch.setattr(advisory,'generate',modify_source_while_generating)
    client=TestClient(main.app)
    res=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    assert res.status_code==200
    final=client.get(f'/api/full-run/{wid}/advisory').json()
    assert final['status']=='STALE_ADVISORY'
    assert final['stored_status']=='STALE_ADVISORY'
    assert final.get('draft') is not None
    assert main.load('workflows',wid,'workflow.json')['status']=='COMPLETE'


def test_changed_constraints_recorded_as_non_approval_diff(tmp_path,monkeypatch):
    wid,_=setup(tmp_path,monkeypatch)
    async def model(context,constraints):return fake_draft()
    monkeypatch.setattr(advisory,'generate',model)
    client=TestClient(main.app)
    client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{'budget_eur':12000,'team_size':2},'regenerate':True})
    final=client.get(f'/api/full-run/{wid}/advisory').json()
    assert final['revision_diff']['changed_constraints']['budget_eur']=={'before':30000,'after':12000}
    assert 'team_size' not in final['revision_diff']['changed_constraints']  # unchanged from demo default
    assert final['revision_diff']['source_changed'] is False
    assert final['approval_status']=='NOT_APPROVED'
