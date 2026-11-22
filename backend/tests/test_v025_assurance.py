"""v0.25 regression suite for journal, revocation and diagnostic reliability.

Actual Rust Dogwood fixture tests run in `cargo test` during Docker build.
Python CLI outputs in tests remain mocks and are NOT evidence of native Rust tests.
"""
import json
import sqlite3
import subprocess
from datetime import datetime, timezone

import pytest

from app import authorization_ledger as al
from app import diagnostic_reliability as dr
from app import dogwood_authorization as da
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def approval():
    return {"approval_id":"a1", "proposal_id":"p1", "parent_run_id":"r1",
            "decision":"approved", "actor":"reviewer", "actor_authentication":"SELF_REPORTED",
            "timestamp_utc":datetime.now(timezone.utc).isoformat(), "rationale":"Test"}


def test_journal_persists_restarts_and_revokes(tmp_path):
    rec=approval()
    entry=al.approve(tmp_path,rec)
    first=al.audit(tmp_path,rec)
    assert entry['seq']==1
    assert first['verified'] and not first['revoked']
    assert first['integrity']=='UNKEYED_SHA256_NOT_TAMPER_PROOF'
    with pytest.raises(al.LedgerError):
        al.approve(tmp_path,rec)
    al.revoke(tmp_path,rec,actor='reviewer',rationale='Withdraw permission')
    second=al.audit(tmp_path,rec)
    assert second['verified'] and second['revoked'] and second['revocation_seq']==2
    with pytest.raises(al.LedgerError):
        al.revoke(tmp_path,rec,actor='reviewer',rationale='duplicate revocation')
    assert second['approval_event_hash']==al.audit(tmp_path,rec)['approval_event_hash']


def test_tampered_approval_and_chain_fail_closed(tmp_path):
    rec=approval()
    al.approve(tmp_path,rec)
    changed={**rec,'rationale':'Forged'}
    with pytest.raises(al.LedgerError, match='snapshot'):
        al.audit(tmp_path,changed)
    db=sqlite3.connect(tmp_path/'authorization_ledger.sqlite3')
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("UPDATE events SET approval_id='fake' WHERE seq=1")
    db.execute("DROP TRIGGER journal_no_update")
    db.execute("UPDATE events SET approval_id='fake' WHERE seq=1")
    db.commit(); db.close()
    with pytest.raises(al.LedgerError):
        al.audit(tmp_path,rec)


def test_hmac_key_rotation_fails_closed(tmp_path,monkeypatch):
    monkeypatch.setenv('AUTH_LEDGER_HMAC_KEY','test-key-1')
    rec=approval(); al.approve(tmp_path,rec)
    assert al.audit(tmp_path,rec)['integrity']=='HMAC_SHA256'
    monkeypatch.setenv('AUTH_LEDGER_HMAC_KEY','test-key-2')
    with pytest.raises(al.LedgerError): al.audit(tmp_path,rec)


def test_must_supply_hmac_if_required(tmp_path,monkeypatch):
    monkeypatch.delenv('AUTH_LEDGER_HMAC_KEY',raising=False)
    monkeypatch.setenv('AUTH_LEDGER_REQUIRE_HMAC','1')
    with pytest.raises(al.LedgerError): al.approve(tmp_path,approval())


def test_missing_journal_denied_even_with_valid_approval_and_bypass(tmp_path):
    rec=approval()
    denied=da.check('w1','p1','a1',rec,ledger_root=tmp_path)
    assert denied['status']=='ERROR'
    assert not da.admitted(denied)


def test_revoked_journal_forces_dogwood_deny(monkeypatch,tmp_path):
    rec=approval()
    al.approve(tmp_path,rec)
    al.revoke(tmp_path,rec,actor='reviewer',rationale='Withdraw approval')
    binary=tmp_path/'claims-dogwood-gate'; binary.touch()
    monkeypatch.setenv('DOGWOOD_MODE','enforce')
    monkeypatch.setenv('DOGWOOD_BINARY',str(binary))
    calls=[]
    def native(cmd,**kwargs):
        data=json.loads(kwargs['input']); calls.append(data)
        return subprocess.CompletedProcess(cmd,0,json.dumps({
            'engine':'dogwood-local-engine',
            'execution_mode':'EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION',
            'policy_id':'r1_after_explicit_human_approval+r1_revoked',
            'decision':'DENY','history_events':2,
            'policy_sha256':da._sha(da.POLICY_PATH),
            'schema_sha256':da._sha(da.SCHEMA_PATH)
        }), '')
    monkeypatch.setattr(da.subprocess,'run',native)
    verdict=da.check('w1','p1','a1',rec,ledger_root=tmp_path)
    assert verdict['status']=='DENY'
    assert calls[0]['revoked_event']==calls[0]['approved_event']
    # Native fail-open under a revocation must NOT authorize R1.
    def faulty(cmd,**kwargs):
        response=native(cmd,**kwargs)
        d=json.loads(response.stdout); d['decision']='ALLOW'
        return subprocess.CompletedProcess(cmd,0,json.dumps(d),'')
    monkeypatch.setattr(da.subprocess,'run',faulty)
    assert da.check('w1','p1','a1',rec,ledger_root=tmp_path)['status']=='ERROR'


def test_diagnostic_gate_is_not_falsely_green_on_assisted_only():
    failure={'status':'COMPLETED', 'summary':{},
             'blind_generalization':{'enabled':True,'summary':{}}}
    for role in ('coding','finance'):
        failure['summary'][role]={'planned':2,'completed':2,'passed':2,
                                   'raw_final_passed':0,'assisted_final_passed':2,
                                   'mean_score':0.875}
        failure['blind_generalization']['summary'][role]={
            'planned':2,'completed':2,'passed':0,'assisted_passed':2}
    result=dr.assess(failure)
    assert result['status']=='HOLD_HUMAN_ADJUDICATION'
    assert not result['autonomous_diagnostic_reliability']
    for role in ('coding','finance'):
        failure['summary'][role]['raw_final_passed']=2
        failure['blind_generalization']['summary'][role]['passed']=2
    passed=dr.assess(failure)
    assert passed['status']=='PASS_SYNTHETIC_SCREEN'
    assert passed['autonomous_diagnostic_reliability'] is False
    failure['blind_generalization']['enabled']=False
    assert dr.assess(failure)['status']=='HOLD_HUMAN_ADJUDICATION'


def test_revoke_endpoint_and_direct_r1_blocked(client,monkeypatch):
    st=_start(client,monkeypatch)
    response=client.post('/api/approve',json={
        'proposal_id':st['review']['proposal_id'],'decision':'approved',
        'actor':'QA reviewer', 'rationale':'Synthetic technical evaluation only'})
    assert response.status_code==200,response.text
    rid=response.json()['approval_id']
    before=client.get(f'/api/approvals/{rid}/authorization-status')
    assert before.status_code==200 and before.json()['revoked'] is False
    revoke=client.post(f'/api/approvals/{rid}/revoke',json={
        'actor':'QA reviewer','rationale':'Terminate any future experiment authorization'})
    assert revoke.status_code==200,revoke.text
    after=client.get(f'/api/approvals/{rid}/authorization-status')
    assert after.status_code==200 and after.json()['revoked'] is True
    assert client.post(f'/api/approvals/{rid}/revoke',json={
        'actor':'QA reviewer','rationale':'Do not apply twice'}).status_code==409
    rejected=client.post('/api/generate-r1',json={'approval_id':rid})
    assert rejected.status_code==403
    reject_eval=client.post('/api/evaluate-r1',json={
        'approval_id':rid,'python_code':'', 'r1_mode':'skill_only'})
    assert reject_eval.status_code==403


def test_reviewer_token_only_allows_configured_identity(client,monkeypatch):
    st=_start(client,monkeypatch)
    monkeypatch.setenv('REVIEWER_API_TOKEN','secret-header-value')
    monkeypatch.setenv('REVIEWER_ID','QA reviewer')
    payload={'proposal_id':st['review']['proposal_id'],'decision':'approved',
             'actor':'QA reviewer','rationale':'Synthetic technical evaluation only'}
    assert client.post('/api/approve',json=payload).status_code==401
    assert client.post('/api/approve',json=payload,headers={'X-Reviewer-Token':'invalid'}).status_code==401
    assert client.post('/api/approve',json={**payload,'actor':'Different reviewer'},
                       headers={'X-Reviewer-Token':'secret-header-value'}).status_code==403
    good=client.post('/api/approve',json=payload,headers={'X-Reviewer-Token':'secret-header-value'})
    assert good.status_code==200,good.text
    assert good.json()['actor_authentication']=='LOCAL_SHARED_TOKEN'
