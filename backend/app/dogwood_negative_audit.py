"""v0.27 synthetic Dogwood deny-path audit with provenance.

Native CLI probes are genuinely executed when the compiled binary is available.
Build-time Rust cargo-test log is copied into the image; absence is never PASS.
An isolated SQLite journal probe checks local evidence mismatch, not remote trust.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime, timezone, timedelta
from . import dogwood_authorization as da
from . import authorization_ledger as al

VERSION='DOGWOOD-NEGATIVE-AUDIT-v0.27.0'


def _identity(w:str,p:str,a:str)->dict:
    return {'workflow_id':w,'proposal_id':p,'approval_id':a}


def _native(binary:str, approved:dict|None, revoked:dict|None, request:dict)->dict:
    payload={'approved_event':approved,'revoked_event':revoked,'generate_request':request}
    try:
        proc=subprocess.run([binary],input=json.dumps(payload),text=True,capture_output=True,timeout=8,check=False)
        data=json.loads(proc.stdout) if proc.returncode==0 else {}
        valid=(proc.returncode==0 and data.get('engine')=='dogwood-local-engine'
               and data.get('execution_mode')=='EPHEMERAL_REPLAY_NOT_CONTINUOUS_AUTHORIZATION'
               and data.get('policy_sha256')==da._sha(da.POLICY_PATH)
               and data.get('schema_sha256')==da._sha(da.SCHEMA_PATH)
               and data.get('history_events')==int(approved is not None)+int(revoked is not None))
        return {'actual':data.get('decision') if valid else 'ERROR',
                'cli_exit_code':proc.returncode,'schema_checked':valid,
                'stderr_excerpt':proc.stderr[-160:] if proc.returncode else None}
    except (OSError,ValueError,subprocess.TimeoutExpired,TypeError) as exc:
        return {'actual':'ERROR','schema_checked':False,'error_type':type(exc).__name__}


def run(artifact_root:Path, *,workflow_id:str,approval_id:str|None)->dict:
    mode=da.configured_mode()
    binary=os.getenv('DOGWOOD_BINARY',da.DEFAULT_BINARY)
    native_available=mode=='enforce' and Path(binary).is_file()
    w='audit-'+hashlib.sha256(workflow_id.encode()).hexdigest()[:12]
    good=_identity(w,'p1','a1')
    different_workflow=_identity(w+'-other','p1','a1')
    different_proposal=_identity(w,'p2','a1')
    wrong_approval=_identity(w,'p1','a2')
    scenarios=[('UNAPPROVED',None,None,good,'DENY'),
               ('MISMATCH_WORKFLOW',different_workflow,None,good,'DENY'),
               ('MISMATCH_PROPOSAL',different_proposal,None,good,'DENY'),
               ('MISMATCH_APPROVAL',wrong_approval,None,good,'DENY'),
               ('REVOKED',good,good,good,'DENY'),
               ('VALID_APPROVAL_CONTROL',good,None,good,'ALLOW')]
    cases=[]
    if native_available:
        for name,approved,revoked,request,expected in scenarios:
            actual=_native(binary,approved,revoked,request)
            cases.append({'case':name,'expected':expected,**actual,
                          'passed':actual['actual']==expected and actual['schema_checked']})
    # Python 24h expiry gate: a separate fail-closed check, not a temporal
    # assertion about persisted timestamps inside the ephemeral Rust engine.
    expired={'approval_id':'a1','proposal_id':'p1','decision':'approved',
             'timestamp_utc':(datetime.now(timezone.utc)-timedelta(hours=25)).isoformat()}
    denied=da.check(w,'p1','a1',expired,ledger_root=None)
    cases.append({'case':'EXPIRED_APPROVAL_PYTHON_GATE','expected':'DENY',
                  'actual':denied.get('decision'),'passed':denied.get('decision')=='DENY',
                  'source':'app.dogwood_authorization.check (timestamp guard)'})
    # A detached local ledger test. No mutation to the user's actual journal.
    with tempfile.TemporaryDirectory() as tmp:
        rec={'approval_id':'a1','proposal_id':'p1','parent_run_id':'r1',
             'decision':'approved','actor':'synthetic-auditor',
             'timestamp_utc':datetime.now(timezone.utc).isoformat(),
             'rationale':'Synthetic isolated audit case'}
        try:
            al.approve(Path(tmp),rec)
            tampered={**rec,'rationale':'modified without journal update'}
            outcome=da.check(w,'p1','a1',tampered,ledger_root=Path(tmp))
            cases.append({'case':'TAMPERED_APPROVAL_SNAPSHOT','expected':'ERROR',
                          'actual':outcome.get('decision'),
                          'passed':outcome.get('decision')=='ERROR',
                          'source':'isolated SQLite journal + app.dogwood_authorization.check'})
        except (al.LedgerError, OSError, ValueError) as exc:
            cases.append({'case':'TAMPERED_APPROVAL_SNAPSHOT','expected':'ERROR',
                          'actual':'NOT_EXECUTED','passed':False,'error_type':type(exc).__name__})
    log_path=Path(os.getenv('DOGWOOD_RUST_TEST_LOG','/opt/dogwood-rust-tests.log'))
    build_log={'available':False,'native_cargo_tests_passed':False}
    if log_path.is_file():
        raw=log_path.read_bytes()
        match=re.search(rb'test result: ok\.\s*(\d+) passed;\s*0 failed;',raw)
        build_log={'available':True,'sha256':hashlib.sha256(raw).hexdigest(),
                   'passed_count':int(match.group(1)) if match else None,
                   'native_cargo_tests_passed':bool(match),
                   'excerpt':raw.decode(errors='replace')[-1400:]}
    native_cases=cases[:len(scenarios)] if native_available else []
    ok=all(c['passed'] for c in cases) and len(native_cases)==len(scenarios)
    status='PASS_NATIVE_DENIAL_CASES' if ok else ('NOT_EXECUTED_NATIVE' if not native_available else 'HOLD')
    return {'version':VERSION,'workflow_id':workflow_id,'approval_id':approval_id,
        'status':status,'configured_mode':mode,'native_checked':native_available,
        'planned':len(scenarios)+2,'passed':sum(c['passed'] for c in cases),
        'executed':len(cases),'cases':cases,'rust_build_test_log':build_log,
        'policy_sha256':da._sha(da.POLICY_PATH),'schema_sha256':da._sha(da.SCHEMA_PATH),
        'source':'synthetic local runtime probes and image build cargo test output',
        'production_authorization':False,'authenticated_actor':False,
        'no_fallback_on_denial':True,
        'note':'Native replay probes do not verify the original human identity or a continuously running Dogwood store. Native unavailability cannot count as passing.'}
