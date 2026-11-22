"""v0.26.1 inline report: completed, partial, scope integrity, no model calls."""
from uuid import uuid4
from fastapi.testclient import TestClient
from app import main


def uuid():
    return str(uuid4())


def workflow(wid, aid=None, eid=None, bid=None, status='COMPLETE'):
    return {
        'workflow_id': wid, 'updated_at': '2026-11-22T01:00:00+00:00',
        'status': status, 'phase': 'DONE' if status!='RUNNING' else '08_diagnostic_benchmark',
        'linked_ids': {'assessments': aid, 'experiments': eid, 'benchmarks': bid},
        'stages': [
            {'name': '03_r0_e2b', 'status': 'COMPLETED', 'detail': 'PASS'},
            {'name': '08_diagnostic_benchmark', 'status': 'COMPLETED_WITH_FINDINGS' if status=='COMPLETE' else 'FAILED', 'detail': 'HOLD'},
            {'name': '09_business_delivery_assessment', 'status': 'COMPLETED' if status=='COMPLETE' else 'SKIPPED', 'detail': ''}
        ],
        'requirement_type': 'claim_progress_updates',
        'diagnostic_reliability_status':'HOLD_HUMAN_ADJUDICATION',
        'diagnostic_execution_status': 'COMPLETE' if status=='COMPLETE' else 'INCOMPLETE_TIMEOUT',
        'requirement_trace_status': 'NOT_APPLICABLE_TO_R1',
        'boundary_status': 'PASS_CONTROLLED',
    }


def test_inline_report_completed_with_assessment(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    wid, aid, eid, bid = uuid(), uuid(), uuid(), uuid()
    main.store('workflows', wid, 'workflow.json', workflow(wid, aid, eid, bid))
    main.store('assessments', aid, 'assessment.json', {
        'assessment_id':aid, 'experiment_id':eid, 'benchmark_id':bid,
        'decision':{'status':'HOLD','production_status':'NO_GO','code':'HOLD_NOTIFICATION_NOT_INTEGRATED'},
        'summary_metrics':{'fifo':{'missed':6}, 'generated':{'missed':0}},
        'axes':[], 'next_actions': []
    })
    main.store('benchmarks', bid, 'benchmark.json', {
        'benchmark_id':bid, 'summary':{'coding':{'completed':2,'passed':0}},
        'reliability_gate':{'execution_status':'COMPLETE','quality_status':'HOLD_HUMAN_ADJUDICATION'}
    })
    main.store('workflows', wid, '05_dogwood_authorization.json', {'status':'ALLOW'})
    res=TestClient(main.app).get(f'/api/full-run/{wid}/report')
    assert res.status_code==200, res.text
    r=res.json()
    assert r['report_version']=='0.27.0'
    assert r['workflow_id']==wid and r['stage_counts']=={'total':3, 'completed':3, 'failed':0, 'skipped':0}
    assert r['authorization_status']=='ALLOW'
    assert r['diagnostic']['quality_status']=='HOLD_HUMAN_ADJUDICATION'
    assert r['business_assessment']['decision']['production_status']=='NO_GO'
    assert r['business_assessment']['summary_metrics']['generated']['missed']==0


def test_partial_no_assessment_never_fabricates_a_decision(tmp_path, monkeypatch):
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    wid=uuid()
    main.store('workflows',wid,'workflow.json',workflow(wid,status='PARTIAL'))
    r=TestClient(main.app).get(f'/api/full-run/{wid}/report')
    assert r.status_code==200
    body=r.json()
    assert body['business_assessment'] is None
    assert body['stage_counts']=={'total':3, 'completed':1, 'failed':1, 'skipped':1}
    assert body['authorization_status'] is None


def test_in_progress_workflow_has_no_final_report(tmp_path, monkeypatch):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    wid=uuid()
    main.store('workflows',wid,'workflow.json',workflow(wid,status='RUNNING'))
    assert TestClient(main.app).get(f'/api/full-run/{wid}/report').status_code==409


def test_report_rejects_inconsistent_assessment_experiment(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'ARTIFACT_DIR',tmp_path)
    wid,aid,eid=uuid(),uuid(),uuid()
    main.store('workflows',wid,'workflow.json',workflow(wid,aid=aid,eid=eid))
    main.store('assessments',aid,'assessment.json',{'assessment_id':aid,'experiment_id':uuid()})
    assert TestClient(main.app).get(f'/api/full-run/{wid}/report').status_code==409
