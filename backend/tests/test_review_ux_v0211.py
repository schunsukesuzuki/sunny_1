"""00b v0.21.1 regression tests: rejected feature mismatch has actionable guidance.

External document acquisition and LLM/E2B are mocked by existing fixtures.
"""
from test_full_run_evidence_v017 import start_public, fixed_insurance_corpus
from test_outer_loop_v08 import client
from app import requirement_trace as rt


def test_review_ux_rejects_progress_notification_as_assignment_with_human_guidance(
    fixed_insurance_corpus, client, monkeypatch
):
    state = start_public(client, monkeypatch, query='insurance claim delays progress communication',dataset='insurance_claims_uk')
    ids=state['evidence_review']['topic_alignment']['topic_matching_evidence_ids']
    base={
        'workflow_id': state['workflow_id'],'decision':'approved','actor':'Technical reviewer',
        'rationale':'The document supports the published insurance problem, not a solution',
        'evidence_ids':ids[:1], 'approved_requirement':'Insurers should send claim status notifications to policyholders',
        'support_assessment':'supports_problem',
    }
    invalid=client.post('/api/full-run/review-evidence',json={**base,'requirement_type':'claims_assignment'})
    assert invalid.status_code==422,invalid.text
    assert '進捗通知' in invalid.json()['detail']
    assert client.get('/api/full-run/'+state['workflow_id']).json()['status']=='AWAITING_EVIDENCE_REVIEW'
    correct=client.post('/api/full-run/review-evidence',json={**base,'requirement_type':'claim_progress_updates'})
    assert correct.status_code==200,correct.text
    assert correct.json()['status'] in ('RUNNING','AWAITING_APPROVAL')


def test_review_ux_keeps_assignment_and_notification_separate():
    assert rt.infer_human_review_type('保険請求の進捗を契約者へ通知する')==rt.NOTIFICATION
    assert rt.infer_human_review_type('保険請求処理の期限超過を減らすため担当者を割り当てる')==rt.ASSIGNMENT
    assert rt.infer_human_review_type('保険請求の進捗通知と担当者割当')=='ambiguous'
