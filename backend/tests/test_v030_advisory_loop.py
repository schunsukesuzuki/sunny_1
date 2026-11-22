"""v0.30: proposal before results, human feedback, append-only versions, isolated failure."""
import json
import zipfile
from uuid import uuid4
from fastapi.testclient import TestClient
from app import main, advisory


def uid(): return str(uuid4())


def setup(tmp_path, monkeypatch, status='COMPLETE'):
    monkeypatch.setattr(main, 'ARTIFACT_DIR',tmp_path)
    wid,export=uid(),uid()
    state={'workflow_id':wid,'export_id':export,'created_at':'2026-11-22T00:00:00+00:00',
           'updated_at':'2026-11-22T00:00:00+00:00','status':status,'phase':'DONE',
           'inputs':{'evidence_mode':'synthetic','brief':'保険請求の期限と担当者の資格条件を確認し、最小構成で改善したい。'},
           'stages':[{'name':'09_business_delivery_assessment','status':'COMPLETED','detail':'NO_GO'}],
           'linked_ids':{'workflows':wid},'bundle_ready':False}
    main.store('workflows',wid,'workflow.json',state)
    return wid,state


def fake_draft():
    return {'title':'検証前の技術提案','executive_direction':'まず通知の実際の遅延原因を調べ、少数機能から検証する。',
            'customer_problem_hypotheses':[{'statement':'通知が遅れている可能性がある','evidence_status':'hypothesis_unverified','source_refs':[],'unknowns':'顧客実態は未確認'}],
            'constraints_and_unknowns':['予算・人員・納期は未確定'],
            'technical_options':[{'label':'low_complexity','solution':'定型通知をルールベースで実装する','necessary_roles':['engineer'],
              'fit_to_constraints':'未確認','estimated_cost_basis':'顧客入力なしのため金額算定不可','main_tradeoffs':['柔軟性'],'validation':'通知遅延を実測','target_requirement_ids':['UNVERIFIED_REQUIREMENT'],'direct_requirement_coverage':'direct','relative_effort':'low','delivery_risk':'unknown'},
              {'label':'balanced','solution':'既存フローと例外処理だけLLMを統合','necessary_roles':['engineer'],
              'fit_to_constraints':'要確認','estimated_cost_basis':'未見積','main_tradeoffs':['監査負荷'],'validation':'例外ケースを検査','target_requirement_ids':['UNVERIFIED_REQUIREMENT'],'direct_requirement_coverage':'direct','relative_effort':'medium','delivery_risk':'unknown'},
              {'label':'research_option','solution':'長期的には通知状態の予測を試す','necessary_roles':['research engineer'],
               'fit_to_constraints':'研究予算は未確定','estimated_cost_basis':'小規模で検証','main_tradeoffs':['データ収集'],'validation':'通知の事後監査','target_requirement_ids':['UNVERIFIED_REQUIREMENT'],'direct_requirement_coverage':'prerequisite_only','relative_effort':'high','delivery_risk':'high'}],
            'recommended_next_experiment':'進捗通知の遅延時間と宛先不一致を測定する',
            'next_experiments':[{'goal':'通知遅延の観測','procedure':'少量データで通知履歴を検査','success_measure':'遅延時間と漏れ率','owner_role':'開発担当','evidence_ref':'workflow.json'}],
            'questions_for_customer':['通知が遅れる理由は何か'],
            'pm_and_engineer_review_points':['予算の仮置きと影響'],
            'next_iteration_inputs':['顧客ヒアリング済みのデータ'],
            'limitations':['本番運用のデータではない']}


def test_auto_proposal_version_review_and_zip(tmp_path,monkeypatch):
    wid,_=setup(tmp_path,monkeypatch)
    calls=[]
    async def model(context,constraints):
        calls.append((context,constraints.model_dump()))
        return fake_draft()
    monkeypatch.setattr(advisory,'generate',model)
    client=TestClient(main.app)
    assert client.get(f'/api/full-run/{wid}/advisory').json()['status']=='NOT_STARTED'
    initial=client.get(f'/api/full-run/{wid}/report').json()
    assert initial['business_assessment'] is None
    first=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    assert first.status_code==200,first.text
    current=client.get(f'/api/full-run/{wid}/advisory').json()
    assert current['status']=='DRAFT_UNAPPROVED' and current['version']==1
    assert len(calls)==1
    assert calls[0][0]['production_status']=='NOT_EVALUATED'
    assert current['draft']['technical_options'][0]['label']=='low_complexity'
    same=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    assert same.status_code==200 and same.json()['version']==1 and len(calls)==1
    review=client.post(f'/api/full-run/{wid}/advisory/review',json={'version':1,'actor':'PM reviewer',
        'decision':'feedback_for_next_iteration','rationale':'顧客の予算・担当人数が未確認なので先に確認する必要がある。',
        'next_iteration_brief':'新たに顧客ヒアリングを行い、予算・担当人数・期限を確認してから再検証する。'})
    assert review.status_code==200,review.text
    assert review.json()['effect']=='REVIEW_ONLY_NO_AUTONOMOUS_EXECUTION'
    newer=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{'budget_eur':15000,'team_size':2},'regenerate':True})
    assert newer.status_code==200,newer.text
    after=client.get(f'/api/full-run/{wid}/advisory').json()
    assert after['version']==2 and len(after['history'])==2 and len(calls)==2
    assert after['history'][0]['review']['decision']=='feedback_for_next_iteration'
    assert after['constraints']['budget_eur']==15000
    assert main.load('workflows',wid,'workflow.json')['status']=='COMPLETE'
    assert main.load('workflows',wid,'workflow.json')['linked_ids']=={'workflows':wid}
    archive=tmp_path/'exports'/main.load('workflows',wid,'workflow.json')['export_id']/'complete_audit_package.zip'
    with zipfile.ZipFile(archive) as z:
        for name in (f'workflows/{wid}/10p_advisory_v0001.json',f'workflows/{wid}/10p_advisory_v0002.json',
                     f'workflows/{wid}/10p_review_v0001.json'):
            assert name in z.namelist()
        assert json.loads(z.read('manifest.json'))['producer_version']=='0.33.0'
    assert client.get(f'/api/full-run/{wid}/report').json()['business_assessment'] is None


def test_proposal_failure_does_not_make_workflow_fail(tmp_path,monkeypatch):
    wid,_=setup(tmp_path,monkeypatch,status='PARTIAL')
    async def fails(_context,_constraints): raise ValueError('model offline')
    monkeypatch.setattr(advisory,'generate',fails)
    client=TestClient(main.app)
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}}).status_code==409
    resp=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{},'provisional_mode':True})
    assert resp.status_code==200
    current=client.get(f'/api/full-run/{wid}/advisory').json()
    assert current['provisional_mode'] is True
    assert current['status']=='GENERATION_FAILED'
    assert 'model offline' in current['error']['message']
    assert client.get(f'/api/full-run/{wid}/report').json()['status']=='PARTIAL'
    assert main.load('workflows',wid,'workflow.json')['status']=='PARTIAL'
    assert client.post(f'/api/full-run/{wid}/advisory/review',json={'version':1,'actor':'PM reviewer',
        'decision':'rejected','rationale':'失敗したLLM回答を承認してはならない。'}).status_code==409


def test_only_terminal_and_no_silent_assumptions(tmp_path,monkeypatch):
    wid,_=setup(tmp_path,monkeypatch,status='RUNNING')
    client=TestClient(main.app)
    assert client.get(f'/api/full-run/{wid}/advisory').status_code==409
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}}).status_code==409
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{'budget_eur':-100}}).status_code in (409,422)
    assert advisory.AdvisoryConstraints().model_dump()['budget_eur']==30_000  # unverified demo scenario


def test_llm_citations_cannot_become_claim_provenance(monkeypatch):
    import app.llm as llm
    async def bad(_schema,_system,_user,**kwargs):
        data=fake_draft()
        data['customer_problem_hypotheses'][0]['source_refs']=['invented-site.com']
        return advisory.AdvisoryDraft(**data)
    monkeypatch.setattr(llm,'query',bad)
    ctx=advisory.compact_context({'workflow_id':uid(),'status':'COMPLETE','diagnostic':{},'business_assessment':None},
                                  {'evidence_mode':'synthetic','brief':'短い合成サンプル'})
    import asyncio,pytest
    result=asyncio.run(advisory.generate(ctx,advisory.AdvisoryConstraints()))
    assert result['customer_problem_hypotheses'][0]['source_refs']==[]
    assert result['customer_problem_hypotheses'][0]['evidence_status']=='hypothesis_unverified'
    assert 'invented-site.com' not in str(result)
