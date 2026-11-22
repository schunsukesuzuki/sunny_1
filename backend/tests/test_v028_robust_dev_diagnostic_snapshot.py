"""v0.28: robust DEV tie-breaking, independent RAW diagnostic axes, and
canonical most-recent snapshot display. Synthetic-only; no Ollama/E2B calls.
"""
from __future__ import annotations
import copy
import hashlib
import io
import json
import zipfile

from fastapi.testclient import TestClient
from app import dev_robustness as drb
from app import dev_selection_audit as dsa
from app import diagnostic_axes as dax
from app import main
from test_v0261_inline_workflow_report import workflow, uuid
from test_full_run_v015 import _start
from test_outer_loop_v08 import client


def eligible(name, sha, missed):
    stress=[]
    for seed,value in zip(sorted(drb.EXPECTED_STRESS_SEEDS),missed):
        stress.append({'seed':seed,'scenario':f'STRESS_{seed}',
            'generated':{'valid':True,'missed':value,'unassigned':0},
            'deadline':{'valid':True,'missed':3,'unassigned':0}})
    return {'engine':name,'candidate_id':name,'source_sha256':sha,
            'eligible':True,'dev_score':[0,0],
            'dev_case_metrics':[{'seed':42,'valid':True,'missed_deadlines':0,'unassigned_cases':0}],
            'stress_checks':stress}


def test_robust_selection_uses_only_predeclared_dev_stress_not_08f():
    slow=eligible('skill_deadline_scarcity','sha1',[1,2,1,1])
    fast=eligible('skill_bounded_beam','sha2',[1,0,1,0])
    # Unrelated post-selection fields would be ignored even if injected.
    slow['08f']={'perfect':True,'winner':'skill_deadline_scarcity'}
    chosen=drb.choose([slow,fast])
    assert chosen['selected_engine']=='skill_bounded_beam'
    assert chosen['08f_used_for_selection'] is False
    assert chosen['holdout_used_for_selection'] is False
    assert chosen['comparable_stress']
    assert chosen['eligible_ranking']==['skill_bounded_beam','skill_deadline_scarcity']
    check=dsa.select([slow,fast],'skill_bounded_beam',selected_source_hash='sha2')
    assert check['selection_consistent_with_predeclared_dev_order']
    assert check['robustness_audit']['selected_engine']=='skill_bounded_beam'


def test_extra_dev_cohort_breaks_old_stress_ties_without_blind_data():
    from app import dev_robustness_fixtures as fixtures
    cases=fixtures.cohort()
    assert set(cases)==set(fixtures.SEEDS)
    assert len({x['scenario'] for x in cases.values()})==4
    a=eligible('A','a',[1,1,1,1]); b=eligible('B','b',[1,1,1,1])
    for target,values in ((a,[2,2,2,2]),(b,[1,1,1,1])):
        target['extra_dev_metrics']=[{'seed':seed,'valid':True,
            'missed_deadlines':value,'unassigned_cases':0}
            for seed,value in zip(fixtures.SEEDS,values)]
    result=drb.choose([a,b])
    assert result['selected_engine']=='B'
    assert result['extra_dev_comparable']
    assert result['08f_used_for_selection'] is False
    assert result['status']=='DEV_MULTICOHORT_ALIGNED'


def test_unresolved_tie_or_missing_stress_is_not_misreported_robust_pass():
    a=eligible('A','a',[0,0,0,0]);b=eligible('B','b',[0,0,0,0])
    tie=drb.choose([a,b])
    assert tie['status']=='TIE_UNRESOLVED_BY_DEV'
    assert tie['selection_uncertainty']=='TIED_WITH_ANOTHER_ELIGIBLE_CANDIDATE'
    assert tie['selected_engine']=='A'
    assert tie['requires_human_review_of_selection']
    b['stress_checks'].pop()
    incomplete=drb.choose([a,b])
    assert not incomplete['comparable_stress']
    assert incomplete['status']=='INCOMPLETE_COMPARABLE_STRESS_FALLBACK'
    assert incomplete['selection_uncertainty']=='INCOMPLETE_COMPARABLE_STRESS'
    assert incomplete['selected_engine']=='A'


def test_stress_loo_detects_sensitive_selection():
    # Candidate A wins on aggregate, but if the favorable seed is removed,
    # B wins. No post-selection example is used.
    a=eligible('A','a',[0,1,1,1]);b=eligible('B','b',[2,0,1,1])
    out=drb.choose([a,b])
    assert out['selected_engine']=='A'
    assert out['status']=='SENSITIVE_TO_STRESS_SCENARIO'
    assert any(row['changed_winner'] for row in out['leave_one_stress_out'])


def _trial(role,checks,*,initial=None,replay=False,blind=False):
    raw={'status':'COMPLETED','case_id':'case_1','model_role':role,
         'replayed_after_incomplete':replay,'raw_consistency':{'passed':True},
         'raw_semantics':{'passed':True},
         'rubric':{'checks':checks}}
    if not blind:
        raw['initial_rubric']={'checks':initial if initial is not None else checks}
        raw['latest_raw_rubric']={'checks':checks}
        raw['initial_raw_consistency']={'passed':True}
        raw['initial_raw_semantics']={'passed':True}
    return raw


def test_axes_separate_classification_from_bad_revision_and_bad_evidence():
    checks={item:True for axis in dax.AXES.values() for item in axis}
    broken={**checks,'revision_targets_requirement':False,
                     'evidence_traceability':False}
    trial=_trial('coding',broken,initial=checks)
    data={'benchmark_id':'x','status':'COMPLETED','trials':[trial],
          'blind_generalization':{'enabled':True,'trials':[_trial('coding',checks,blind=True,replay=True)]}}
    result=dax.summarize(data)
    initial=next(x for x in result['groups'] if x['model_role']=='coding' and x['group']=='fixed_first_raw')
    latest=next(x for x in result['groups'] if x['model_role']=='coding' and x['group']=='fixed_latest_raw')
    blind=next(x for x in result['groups'] if x['model_role']=='coding' and x['group']=='blind_raw')
    assert initial['axes']['revision_action']['passed']==1
    assert latest['axes']['cause_classification']['status']=='PASS_SYNTHETIC'
    assert latest['axes']['revision_action']['status']=='HOLD'
    assert latest['axes']['evidence_quality']['status']=='HOLD'
    assert not blind['usable_for_first_pass_generalization']
    assert not result['auto_corrected_diagnosis']


def test_replayed_incomplete_fixed_cannot_claim_initial_raw_success():
    checks={item:True for axis in dax.AXES.values() for item in axis}
    data={'trials':[_trial('coding',checks,replay=True)],
          'blind_generalization':{'enabled':False,'trials':[]}}
    groups=dax.summarize(data)['groups']
    initial=next(g for g in groups if g['group']=='fixed_first_raw' and g['model_role']=='coding')
    latest=next(g for g in groups if g['group']=='fixed_latest_raw' and g['model_role']=='coding')
    assert initial['axes']['cause_classification']['status']=='NOT_EVALUATED'
    assert latest['axes']['cause_classification']['status']=='PASS_SYNTHETIC'


def test_v028_report_latest_gate_overrides_historical_state_and_flags_mismatch(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    wid,aid,eid,bid=uuid(),uuid(),uuid(),uuid()
    state=workflow(wid,aid,eid,bid)
    state['diagnostic_reliability_status']='HOLD_HUMAN_ADJUDICATION'
    state['diagnostic_execution_status']='INCOMPLETE_TIMEOUT'  # stale workflow snapshot
    main.store('workflows',wid,'workflow.json',state)
    main.store('assessments',aid,'assessment.json',{'assessment_id':aid,'experiment_id':eid,'benchmark_id':bid,'decision':{'production_status':'NO_GO'}})
    latest={'benchmark_id':bid,'status':'COMPLETED','summary':{},'retry_history':[{'status':'COMPLETED'}],
        'reliability_gate':{'status':'HOLD_HUMAN_ADJUDICATION','quality_status':'HOLD_HUMAN_ADJUDICATION','execution_status':'COMPLETE'},
        'trials':[],'blind_generalization':{'enabled':False,'trials':[]}}
    main.store('benchmarks',bid,'benchmark.json',latest)
    res=TestClient(main.app).get('/api/full-run/'+wid+'/report')
    assert res.status_code==200,res.text
    report=res.json()
    assert report['diagnostic']['execution_status']=='COMPLETE'
    assert report['diagnostic_snapshot']['workflow_vs_benchmark_consistent'] is False
    assert report['diagnostic_snapshot']['benchmark_retry_count']==1
    assert report['report_version']=='0.27.0'  # stable report contract
    assert report['producer_version'] in ('0.28.0','0.29.0','0.30.0','0.31.0','0.32.0','0.33.0')  # producer advances, contract remains stable


def test_v028_batch_audit_zip_includes_new_artifacts(client,monkeypatch):
    from test_domain_skill_v020 import mock_sandbox_with_actual_skill
    monkeypatch.setattr(main,'run_in_e2b',mock_sandbox_with_actual_skill)
    state=_start(client,monkeypatch)
    r=client.post('/api/full-run/approve-and-continue',json={'workflow_id':state['workflow_id'],
        'approval':{'proposal_id':state['review']['proposal_id'],'decision':'approved',
                    'actor':'Tester','rationale':'Synthetic v0.28 controls'}})
    assert r.status_code==200,r.text
    finished=client.get('/api/full-run/'+state['workflow_id']).json()
    assert finished['status']=='COMPLETE',finished
    report=client.get('/api/full-run/'+state['workflow_id']+'/report').json()
    assert report['dev_robustness_preselection']
    assert report['dev_robustness_preselection']['extra_dev_comparable']
    assert len(report['dev_robustness_preselection']['extra_dev_seeds'])==4
    assert report['diagnostic_axes']
    assert report['diagnostic_snapshot']['index_consistent']
    with zipfile.ZipFile(io.BytesIO(client.get(finished['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        names=set(z.namelist())
        assert any(name.endswith('/dev_robustness_preselection.json') for name in names)
        assert any(name.endswith('/diagnostic_axes.json') for name in names)
        assert any(name.endswith('/08_latest_state_index.json') for name in names)
        assert manifest['status']=='COMPLETE'
        assert all(hashlib.sha256(z.read(e['path'])).hexdigest()==e['sha256_raw_bytes'] for e in manifest['files'])
