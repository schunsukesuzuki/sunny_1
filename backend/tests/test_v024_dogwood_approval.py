"""v0.24: Dogwood request-contract tests. Subprocess is MOCKED in Python tests."""
import hashlib
import io
import json
import subprocess
import zipfile
from datetime import datetime, timedelta, timezone

from app import dogwood_authorization as da, main
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def approval(**extra):
    value = {"approval_id": "approval1", "proposal_id": "proposal1", "decision": "approved",
             "timestamp_utc": datetime.now(timezone.utc).isoformat()}
    value.update(extra)
    return value


def test_local_denies_bad_identity_missing_approval_and_wrong_decision():
    assert da.check("workflow1", "proposal1", "approval1", None)["status"] == "DENY"
    assert da.check("workflow1", "proposal1", "approval1", approval(decision="rejected"))["status"] == "DENY"
    assert da.check("workflow1", "proposal1", "approval1", approval(proposal_id="other"))["status"] == "DENY"
    assert da.check("workflow1", "proposal1", "approval1", approval(approval_id="other"))["status"] == "DENY"
    assert da.check("workflow/1", "proposal1", "approval1", approval())["status"] == "DENY"


def test_stale_approval_and_missing_timestamp_block_even_when_off():
    old=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
    assert da.check("workflow1", "proposal1", "approval1", approval(timestamp_utc=old))["status"] == "DENY"
    assert da.check("workflow1", "proposal1", "approval1", approval(timestamp_utc=""))["status"] == "DENY"
    record=da.check("workflow1", "proposal1", "approval1", approval())
    assert record["status"] == "NOT_ENFORCED"
    assert record["production_authorization"] is False


def test_fail_closed_when_real_binary_is_not_available(monkeypatch):
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    monkeypatch.setenv("DOGWOOD_BINARY", "/nonexistent/claims-dogwood-gate")
    record=da.check("workflow1", "proposal1", "approval1", approval())
    assert record["status"] == "ERROR"
    assert not da.admitted(record)


def test_native_dogwood_request_shape_and_verdict(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    path=tmp_path/"claims-dogwood-gate"
    path.write_text("fixture only")
    monkeypatch.setenv("DOGWOOD_BINARY", str(path))
    calls=[]
    def mock_call(command, **kwargs):
        calls.append(json.loads(kwargs["input"]))
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "engine": "dogwood-local-engine",
            "execution_mode": "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
            "policy_id": "r1_after_explicit_human_approval+r1_revoked",
            "decision": "ALLOW", "history_events": 1,
            "policy_sha256": da._sha(da.POLICY_PATH), "schema_sha256": da._sha(da.SCHEMA_PATH)}), "")
    monkeypatch.setattr(da.subprocess, "run", mock_call)
    result=da.check("workflow1", "proposal1", "approval1", approval())
    assert result["status"] == "ALLOW"
    assert da.admitted(result)
    assert result["policy_sha256"] == hashlib.sha256(da.POLICY_PATH.read_bytes()).hexdigest()
    assert calls[0]["approved_event"] == calls[0]["generate_request"]
    assert calls[0]["revoked_event"] is None
    assert calls[0]["generate_request"]["workflow_id"] == "workflow1"


def test_denied_malformed_and_timeout_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    binary=tmp_path/"claims-dogwood-gate"
    binary.touch()
    monkeypatch.setenv("DOGWOOD_BINARY", str(binary))
    def response(verdict):
        return subprocess.CompletedProcess([str(binary)], 0, json.dumps({
            "engine": "dogwood-local-engine",
            "execution_mode": "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
            "policy_id": "r1_after_explicit_human_approval+r1_revoked",
            "decision": verdict, "history_events": 1,
            "policy_sha256": da._sha(da.POLICY_PATH), "schema_sha256": da._sha(da.SCHEMA_PATH)}), "")
    monkeypatch.setattr(da.subprocess, "run", lambda *a, **kw: response("DENY"))
    assert da.check("workflow1", "proposal1", "approval1", approval())["status"] == "DENY"
    monkeypatch.setattr(da.subprocess, "run", lambda *a, **kw: response("MALFORMED"))
    assert da.check("workflow1", "proposal1", "approval1", approval())["status"] == "ERROR"
    def timeout(*args,**kwargs):
        raise subprocess.TimeoutExpired("dogwood",8)
    monkeypatch.setattr(da.subprocess, "run",timeout)
    assert da.check("workflow1", "proposal1", "approval1", approval())["status"] == "ERROR"


def test_full_run_intercepts_dogwood_deny_before_r1_and_exports_zip(client, monkeypatch, tmp_path):
    st=_start(client,monkeypatch)
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    bin_path=tmp_path/"claims-dogwood-gate"
    bin_path.touch()
    monkeypatch.setenv("DOGWOOD_BINARY", str(bin_path))
    def deny(*args,**kwargs):
        return subprocess.CompletedProcess(args[0], 0, json.dumps({
            "engine": "dogwood-local-engine",
            "execution_mode": "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
            "policy_id": "r1_after_explicit_human_approval+r1_revoked",
            "decision": "DENY", "history_events": 1,
            "policy_sha256": da._sha(da.POLICY_PATH), "schema_sha256": da._sha(da.SCHEMA_PATH)}), "")
    monkeypatch.setattr(da.subprocess, "run",deny)
    async def forbidden(*args,**kwargs):
        raise AssertionError('Dogwood must intercept before R1 generation or evaluation')
    monkeypatch.setattr(main,'evaluate_r1',forbidden)
    response=client.post('/api/full-run/approve-and-continue',json={
        'workflow_id':st['workflow_id'],
        'approval':{'proposal_id':st['review']['proposal_id'],'decision':'approved',
                    'actor':'QA reviewer','rationale':'Only a controlled synthetic experiment'}})
    assert response.status_code==200,response.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='PARTIAL',final
    assert final['dogwood_authorization']['status']=='DENY'
    stages={x['name']:x['status'] for x in final['stages']}
    assert stages['06_r1_generation_and_evaluation']=='SKIPPED'
    assert stages['08g_boundary_assurance']=='FAILED'
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        assert json.loads(z.read('manifest.json'))['format_version']=='AUDIT-EXPORT-v0.24.0'
        gate=next(n for n in z.namelist() if n.endswith('/boundary_05_to_06_dogwood.json'))
        assert json.loads(z.read(gate))['status']=='HOLD'
        decision=next(n for n in z.namelist() if n.endswith('/05_dogwood_authorization.json'))
        assert json.loads(z.read(decision))['status']=='DENY'


def test_policy_source_hash_mismatch_is_not_accepted(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    p = tmp_path / "claims-dogwood-gate"
    p.touch()
    monkeypatch.setenv("DOGWOOD_BINARY", str(p))
    def wrong_policy_hash(cmd, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, json.dumps({
            "engine": "dogwood-local-engine",
            "execution_mode": "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
            "policy_id": "r1_after_explicit_human_approval+r1_revoked",
            "decision": "ALLOW", "history_events": 1,
            "policy_sha256": "mismatched-policy", "schema_sha256": da._sha(da.SCHEMA_PATH)}), "")
    monkeypatch.setattr(da.subprocess, "run", wrong_policy_hash)
    result=da.check("workflow1", "proposal1", "approval1", approval())
    assert result["status"] == "ERROR"
    assert not da.admitted(result)


def test_revocation_event_reaches_native_policy_adapter(monkeypatch, tmp_path):
    monkeypatch.setenv("DOGWOOD_MODE", "enforce")
    p = tmp_path / "claims-dogwood-gate"
    p.touch()
    monkeypatch.setenv("DOGWOOD_BINARY", str(p))
    data=[]
    def native_deny(cmd, **kwargs):
        payload=json.loads(kwargs["input"])
        data.append(payload)
        return subprocess.CompletedProcess(cmd, 0, json.dumps({
            "engine": "dogwood-local-engine",
            "execution_mode": "EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION",
            "policy_id": "r1_after_explicit_human_approval+r1_revoked",
            "decision": "DENY", "history_events": 2,
            "policy_sha256": da._sha(da.POLICY_PATH), "schema_sha256": da._sha(da.SCHEMA_PATH)}), "")
    monkeypatch.setattr(da.subprocess,"run",native_deny)
    result=da.check("workflow1", "proposal1", "approval1", approval(), revoked=True)
    assert result["status"]=="DENY"
    assert data[0]["approved_event"]==data[0]["revoked_event"]
