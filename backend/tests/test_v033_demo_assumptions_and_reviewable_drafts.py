"""v0.33: demo assumptions, preserved imperfect model draft, unchanged execution gate.

All tests use mock model responses; live Ollama quality is not asserted.
"""
import asyncio
import json
import zipfile
from copy import deepcopy
from fastapi.testclient import TestClient
from app import advisory, main
from test_v030_advisory_loop import setup
from test_v032_advisory_boundaries import public_context, valid_public_draft


def test_defaults_are_real_server_values_and_explicitly_unverified():
    assumptions=advisory.AdvisoryConstraints()
    values=assumptions.model_dump()
    assert values['budget_eur']==30000
    assert values['team_size']==2 and values['delivery_weeks']==8
    assert values['pm_fte']==0.2
    assert '専任運用担当なし' in values['operational_constraints']
    origins=advisory.assumption_provenance(assumptions)
    assert all(x['basis']=='DEMO_PLACEHOLDER_UNVERIFIED' for x in origins.values())
    assert all(x['is_customer_confirmed'] is False for x in origins.values())
    changed=advisory.AdvisoryConstraints(budget_eur=50000,team_size=None)
    origins=advisory.assumption_provenance(changed)
    assert origins['budget_eur']['basis']=='USER_EDIT_UNVERIFIED'
    assert origins['team_size']['value'] is None
    assert not origins['team_size']['is_customer_confirmed']


def test_unknown_budget_can_include_numeric_qualified_estimate():
    draft=valid_public_draft()
    draft['technical_options'][0]['estimated_cost_basis']='仮に週€2,000×8週の概算。実見積ではない。'
    ctx=public_context()
    assumptions=advisory.AdvisoryConstraints(budget_eur=None)
    # Not a valid quote, but it is a displayable hypothesis even without a known budget.
    advisory.validate_draft(draft,ctx,assumptions)
    notices=advisory.estimate_notices(draft)
    assert notices and notices[0]['code']=='UNVERIFIED_COST_ESTIMATE'


def test_bad_option_is_displayed_with_warning_and_other_options_preserved(tmp_path,monkeypatch):
    ctx=public_context()
    bad=valid_public_draft()
    bad['technical_options'][0]['solution']='担当者割当の最適化だけを行う。'
    bad['technical_options'][0]['estimated_cost_basis']='概算€5,000、実見積ではない'
    calls=[]
    async def fake_query(schema,*args,**kwargs):
        calls.append(schema.__name__)
        if schema==advisory.AdvisoryLLMDraft:
            original={**bad, 'customer_problem_hypotheses':[
                {'statement':h['statement'],'unknowns':h['unknowns']}
                for h in bad['customer_problem_hypotheses']]}
            return schema.model_validate(original)
        # The model fails to fix the specific option. It must remain visible, not discarded.
        return schema.model_validate({'item':bad['technical_options'][0]})
    monkeypatch.setattr(advisory.llm,'query',fake_query)
    result=asyncio.run(advisory.generate(ctx,advisory.AdvisoryConstraints()))
    assert calls==['AdvisoryLLMDraft','AdvisoryRepair_technical_options_item']
    assert result['technical_options'][1:]==bad['technical_options'][1:]
    assert result['technical_options'][0]['solution']==bad['technical_options'][0]['solution']
    assert result['_contract_issues']['technical_options[0]']
    assert result['_repair_actions'][0]['status']=='REJECTED_STILL_INCONSISTENT'
    assert result['_estimate_notices'][0]['code']=='UNVERIFIED_COST_ESTIMATE'


def test_warning_draft_saved_reviewed_as_feedback_and_in_audit_zip(tmp_path,monkeypatch):
    wid,state=setup(tmp_path,monkeypatch)
    async def draft(_context,_constraints):
        bad=valid_public_draft()
        bad['technical_options'][0]['solution']='担当者割当の改善だけをする。'
        bad['_repair_actions']=[{'section':'technical_options[0]','status':'REJECTED_STILL_INCONSISTENT'}]
        bad['_contract_issues']={'technical_options[0]':['主たる通知要件への直接対応がない']}
        bad['_estimate_notices']=[]
        return bad
    monkeypatch.setattr(advisory,'generate',draft)
    client=TestClient(main.app)
    post=client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}})
    assert post.status_code==200,post.text
    got=client.get(f'/api/full-run/{wid}/advisory').json()
    assert got['status']=='DRAFT_WITH_WARNINGS'
    assert got['draft'] and got['contract_issues']
    assert got['approval_status']=='NOT_APPROVED'
    assert got['scenario_basis']=='UNVERIFIED_DEMO_ASSUMPTIONS_NOT_CLIENT_BUDGET'
    assert got['assumptions_origin']['budget_eur']['basis']=='DEMO_PLACEHOLDER_UNVERIFIED'
    review=client.post(f'/api/full-run/{wid}/advisory/review',json={'version':1,'actor':'PM reviewer',
        'decision':'feedback_for_next_iteration','rationale':'通知要件に直接適合しないので顧客と再確認し、提案を修正する必要がある。'})
    assert review.status_code==200,review.text
    assert review.json()['not_production_approval'] is True
    assert review.json()['warning_count']==1
    assert main.load('workflows',wid,'workflow.json')['status']=='COMPLETE'
    assert main.load('workflows',wid,'workflow.json')['linked_ids']=={'workflows':wid}
    output=tmp_path/'exports'/state['export_id']/'complete_audit_package.zip'
    with zipfile.ZipFile(output) as z:
        data=json.loads(z.read(f'workflows/{wid}/10p_advisory_v0001.json'))
        assert data['status']=='DRAFT_WITH_WARNINGS'
        assert data['draft']['technical_options'][0]['solution']=='担当者割当の改善だけをする。'
        assert data['contract_issues']
        assert data['approval_status']=='NOT_APPROVED'
    assert client.get(f'/api/full-run/{wid}/report').json()['status']=='COMPLETE'


def test_warning_draft_becomes_stale_when_source_changes(tmp_path,monkeypatch):
    wid,state=setup(tmp_path,monkeypatch)
    async def draft(_ctx,_assumptions):
        data=valid_public_draft()
        data['_contract_issues']={'technical_options[0]':['要件不適合']}
        return data
    monkeypatch.setattr(advisory,'generate',draft)
    client=TestClient(main.app)
    assert client.post(f'/api/full-run/{wid}/advisory',json={'constraints':{}}).status_code==200
    assert client.get(f'/api/full-run/{wid}/advisory').json()['status']=='DRAFT_WITH_WARNINGS'
    state['updated_at']='2026-11-22T17:00:00+00:00'
    path=tmp_path/'workflows'/wid/'workflow.json'
    path.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
    assert client.get(f'/api/full-run/{wid}/advisory').json()['status']=='STALE_ADVISORY'
    assert client.post(f'/api/full-run/{wid}/advisory/review',json={
        'version':1,'actor':'PM reviewer','decision':'feedback_for_next_iteration',
        'rationale':'古い基準で生成された警告付き草案なのでレビューできない。'}).status_code==409
