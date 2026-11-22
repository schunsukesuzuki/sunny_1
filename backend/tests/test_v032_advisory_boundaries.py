"""v0.32 high-priority scope only: source binding, scoped repair, COMPLETE sync."""
import asyncio
from copy import deepcopy
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app import advisory, main
from test_v030_advisory_loop import fake_draft, setup


def public_context():
    report = {
        'workflow_id': 'sample', 'status': 'COMPLETE',
        'reviewed_evidence': {
            'selected_evidence_ids': ['PUB-001', 'PUB-003'],
            'approved_requirement_hypothesis': '公開資料の通知課題を合成検証する。',
            'evidence_pointer_records': [
                {'evidence_id':'PUB-001','source_url':'https://example.com/first',
                 'source_file':'public-source-1.html','quote':'通知の遅延に関する公開文脈'},
                {'evidence_id':'PUB-003','source_url':'https://example.com/third',
                 'source_file':'public-source-3.html','quote':'問い合わせ件数に関する公開文脈'},
            ],
        },
        'requirement_trace': {'requirement_id':'REQ-PUBLIC-001',
                              'type':'claim_progress_updates','feature_id':'notify',
                              'acceptance_test_ids':['NOTIFY-DELAY']},
        'feature_acceptance': {'requirement_id':'REQ-PUBLIC-001',
                               'integrated_service_acceptance':False},
        'diagnostic': {'quality_status':'HOLD_HUMAN_ADJUDICATION'},
        'business_assessment': {},
    }
    return advisory.compact_context(report, {'evidence_mode':'public',
        'dataset_id':'insurance_claims_uk', 'brief':'通知遅延が仮説であり、顧客確認はまだ実施していない。'})


def valid_public_draft():
    data=fake_draft()
    data['customer_problem_hypotheses'][0]['source_refs'] = []
    data['customer_problem_hypotheses'][0]['evidence_status'] = 'hypothesis_unverified'
    for o in data['technical_options']:
        o['target_requirement_ids'] = ['REQ-PUBLIC-001']
        o['direct_requirement_coverage'] = 'direct'
        o['solution'] = '進捗通知のルール・例外処理を分離して宛先と期限を評価する。'
    data['next_experiments'][0]['evidence_ref']='08e_feature_acceptance.json'
    return data


def test_public_citation_bound_to_reviewed_registry_not_model_hypotheses(monkeypatch):
    ctx=public_context()
    references=advisory.deterministic_public_context(ctx)
    assert [r['evidence_id'] for r in references]==['PUB-001','PUB-003']
    assert all(r['support_scope']=='PUBLIC_CONTEXT_ONLY_NOT_CUSTOMER_PROOF' for r in references)
    assert 'PUB-999' not in str(references)
    assert ctx['primary_requirement']['requirement_id']=='REQ-PUBLIC-001'
    async def mock_query(schema, _system, _user, **_kw):
        data=valid_public_draft()
        # Model response is not permitted to attach citations even if it tries.
        data['customer_problem_hypotheses'][0]['source_refs']=['PUB-999']
        data['customer_problem_hypotheses'][0]['evidence_status']='source_context'
        if schema==advisory.AdvisoryLLMDraft:
            data['customer_problem_hypotheses']=[{'statement':x['statement'], 'unknowns':x['unknowns']}
                                                 for x in data['customer_problem_hypotheses']]
        return schema.model_validate(data)
    monkeypatch.setattr(advisory.llm,'query',mock_query)
    value=asyncio.run(advisory.generate(ctx,advisory.AdvisoryConstraints()))
    h=value['customer_problem_hypotheses'][0]
    assert h['source_refs']==[] and h['evidence_status']=='hypothesis_unverified'
    assert value['_repair_actions']==[]
    assert 'PUB-999' not in str(value)
    assert references[0]['source_url']=='https://example.com/first'


def test_only_failed_technical_options_are_regenerated(monkeypatch):
    ctx=public_context()
    calls=[]
    draft=valid_public_draft()
    original_statement=deepcopy(draft['customer_problem_hypotheses'])
    broken=deepcopy(draft)
    broken['technical_options'][0]['solution']='担当者割当を改善して人員を効率化する。'
    async def mock_query(schema, system, prompt, **kwargs):
        calls.append((schema.__name__,prompt))
        if schema==advisory.AdvisoryLLMDraft:
            return schema.model_validate({**broken,'customer_problem_hypotheses':[
                {'statement':x['statement'],'unknowns':x['unknowns']}
                for x in broken['customer_problem_hypotheses']]})
        assert schema.__name__=='AdvisoryRepair_technical_options'
        return schema.model_validate({'technical_options':draft['technical_options']})
    monkeypatch.setattr(advisory.llm,'query',mock_query)
    result=asyncio.run(advisory.generate(ctx,advisory.AdvisoryConstraints()))
    assert len(calls)==2
    assert len(result['_repair_actions'])==1
    assert result['_repair_actions'][0]['section']=='technical_options'
    assert [x['statement'] for x in result['customer_problem_hypotheses']] == [
        x['statement'] for x in original_statement]
    assert result['technical_options']==draft['technical_options']
    assert result['executive_direction']==draft['executive_direction']


def test_targeted_repair_fails_closed_if_invalid_after_one_attempt(monkeypatch):
    ctx=public_context()
    broken=valid_public_draft()
    broken['technical_options'][0]['solution']='担当者割当の順位を上げる。'
    calls=[]
    async def bad_query(schema, *args, **kwargs):
        calls.append(schema.__name__)
        if schema==advisory.AdvisoryLLMDraft:
            return schema.model_validate({**broken,'customer_problem_hypotheses':[
                {'statement':x['statement'],'unknowns':x['unknowns']}
                for x in broken['customer_problem_hypotheses']]})
        return schema.model_validate({'technical_options':broken['technical_options']})
    monkeypatch.setattr(advisory.llm,'query',bad_query)
    with pytest.raises(ValueError,match='still violates contracts'):
        asyncio.run(advisory.generate(ctx,advisory.AdvisoryConstraints()))
    assert calls==['AdvisoryLLMDraft','AdvisoryRepair_technical_options']


def test_partial_workflow_needs_explicit_provisional_mode(tmp_path,monkeypatch):
    wid,state=setup(tmp_path,monkeypatch,status='PARTIAL')
    calls=[]
    async def mock_generate(context,constraints):
        calls.append(context['workflow_status'])
        return fake_draft()
    monkeypatch.setattr(advisory,'generate',mock_generate)
    client=TestClient(main.app)
    assert client.get(f'/api/full-run/{wid}/advisory').json()['status']=='NOT_STARTED'
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}}).status_code==409
    assert not calls
    r=client.post(f'/api/full-run/{wid}/advisory',json={
        'constraints':{},'provisional_mode':True})
    assert r.status_code==200, r.text
    current=client.get(f'/api/full-run/{wid}/advisory').json()
    assert current['provisional_mode'] is True
    assert current['source_workflow_status']=='PARTIAL'
    assert current['status']=='DRAFT_UNAPPROVED'
    # The same stored PARTIAL-based proposal must be stale once 08 recovers.
    state['status']='COMPLETE'
    state['updated_at']='2026-11-22T12:00:00+00:00'
    (tmp_path/'workflows'/wid/'workflow.json').write_text(
        __import__('json').dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    stale=client.get(f'/api/full-run/{wid}/advisory').json()
    assert stale['status']=='STALE_ADVISORY'
    assert client.post(f'/api/full-run/{wid}/advisory/review',json={
        'version':1,'actor':'reviewer','decision':'reviewed_as_draft',
        'rationale':'最新COMPLETE時点の証跡へ更新する前はレビューを受け付けない。'}).status_code==409
    refreshed=client.post(f'/api/full-run/{wid}/advisory',json={
        'constraints':{},'regenerate':True})
    assert refreshed.status_code==200
    assert client.get(f'/api/full-run/{wid}/advisory').json()['status']=='DRAFT_UNAPPROVED'
    assert calls==['PARTIAL','COMPLETE']
