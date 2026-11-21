"""v0.17: public 00 actually executes, pauses for evidence review, fails closed."""
import hashlib
import io
import json
import zipfile

import pytest
from app import evidence_rag as er, llm, main
from test_evidence_rag_v016 import fixed_corpus
from test_full_run_v015 import fake_design
from test_outer_loop_v08 import client
from test_policy_bundle_v014 import benchmark_model_stub


def start_public(client,monkeypatch,query='checking account fees'):
    monkeypatch.setattr(llm,'design',fake_design)
    monkeypatch.setattr(llm,'benchmark_diagnosis',benchmark_model_stub)
    sample=client.get('/api/sample').json()
    response=client.post('/api/full-run/start',json={
       'evidence_mode':'public','dataset_id':'community_credit','evidence_query':query,
       'brief':sample['brief'],'case_ids':['fifo_sla_conflict','actual_fifo_implementation_bug'],
       'seed':42,'repetitions':1})
    assert response.status_code==200,response.text
    return client.get('/api/full-run/'+response.json()['workflow_id']).json()


def approve_public(client,state,ids=None,text=None):
    ids=ids or [state['evidence_review']['evidence'][0]['evidence_id']]
    return client.post('/api/full-run/review-evidence',json={
        'workflow_id':state['workflow_id'], 'decision':'approved',
        'actor':'Technical Reviewer','rationale':'Use retrieved statement only as a synthetic evaluation hypothesis',
        'evidence_ids':ids,'approved_requirement':text or 'Investigate whether account fee disclosures need clearer presentation for users.'})


def test_public_pipeline_needs_evidence_and_05_review_with_complete_zip(fixed_corpus,client,monkeypatch):
    st=start_public(client,monkeypatch)
    assert st['status']=='AWAITING_EVIDENCE_REVIEW',st
    assert st['linked_ids']['runs'] is None and st['linked_ids']['proposals'] is None
    assert st['evidence_review']['evaluation']['customer_approval']=='NOT_OBTAINED'
    invalid=approve_public(client,st,ids=['PUB-999'])
    assert invalid.status_code==422
    assert client.get('/api/full-run/'+st['workflow_id']).json()['status']=='AWAITING_EVIDENCE_REVIEW'
    response=approve_public(client,st)
    assert response.status_code==200,response.text
    mid=client.get('/api/full-run/'+st['workflow_id']).json()
    assert mid['status']=='AWAITING_APPROVAL',mid
    assert mid['review']['proposal_id']
    stored=main.load('workflows',st['workflow_id'],'01_input.json')
    assert 'Investigate whether account fee disclosures' in stored['effective_brief']
    assert 'PUBLIC EVIDENCE' in stored['effective_brief']
    assert stored['r0_contract_changed'] is False
    assert stored['customer_validity']=='UNVERIFIED'
    # Public evidence approval does not replace the 05 requirement-change review.
    final_request=client.post('/api/full-run/approve-and-continue',json={'workflow_id':st['workflow_id'],
       'approval':{'proposal_id':mid['review']['proposal_id'],'decision':'approved',
                   'actor':'Reviewer','rationale':'Synthetic workflow test, independent R0 evidence'}})
    assert final_request.status_code==200,final_request.text
    final=client.get('/api/full-run/'+st['workflow_id']).json()
    assert final['status']=='COMPLETE',final
    assert final['evidence_mode']=='public'
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['status']=='COMPLETE',manifest
        assert manifest['excluded_steps']=={}
        assert '00b_evidence_review' in manifest['completed_steps']
        for name in ('00_evidence_grounded_requirements.json','00_source_manifest.json',
                     '00_index_metadata.json','00_rag_report.md','00b_human_evidence_review.json',
                     '01_input.json'):
            assert any(n.endswith('/'+name) for n in z.namelist()),name
        for info in manifest['files']:
            assert hashlib.sha256(z.read(info['path'])).hexdigest()==info['sha256_raw_bytes']
        approval_file=next(n for n in z.namelist() if n.endswith('/00b_human_evidence_review.json'))
        evidence_review=json.loads(z.read(approval_file))
        assert evidence_review['customer_requirement_approval']=='NOT_OBTAINED'
        assert evidence_review['selected_evidence_ids']
        assert evidence_review['approval_scope']=='DEMO_HYPOTHESIS_ONLY'
    assert client.post('/api/full-run/review-evidence',json={
        'workflow_id':st['workflow_id'],'decision':'rejected','actor':'Reviewer','rationale':'Duplicate request'}).status_code==409


def test_public_download_error_fails_without_synthetic_fallback(tmp_path,client,monkeypatch):
    monkeypatch.setattr(er,'ROOT',tmp_path/'clean')
    def offline(_):raise OSError('HTTPS source unavailable')
    monkeypatch.setattr(er,'acquire',offline)
    st=start_public(client,monkeypatch)
    assert st['status']=='PARTIAL',st
    assert st['phase']=='00_evidence_grounded_requirements'
    assert 'source unavailable' in st['error']
    assert st['linked_ids']['runs'] is None
    assert any(x['name']=='00_evidence_grounded_requirements' and x['status']=='FAILED' for x in st['stages'])
    assert not any(x['name']=='01_input' and x['status']=='COMPLETED' for x in st['stages'])
    with zipfile.ZipFile(io.BytesIO(client.get(st['bundle_url']).content)) as z:
        assert json.loads(z.read('manifest.json'))['status']=='PARTIAL'


def test_corrupted_cached_source_is_not_silently_reused(fixed_corpus,client,monkeypatch):
    folder,_=fixed_corpus
    (folder/'transcripts.txt').write_text('tampered',encoding='utf-8')
    def no_download(_):raise AssertionError('Do not silently redownload or fallback')
    monkeypatch.setattr(er,'acquire',no_download)
    st=start_public(client,monkeypatch)
    assert st['status']=='PARTIAL',st
    assert 'SHA256' in st['error']
    assert st['linked_ids']['runs'] is None


def test_00_review_can_reject_and_retains_evidence_snapshot(fixed_corpus,client,monkeypatch):
    st=start_public(client,monkeypatch)
    response=client.post('/api/full-run/review-evidence',json={
       'workflow_id':st['workflow_id'],'decision':'rejected','actor':'Reviewer',
       'rationale':'Evidence is not relevant enough to warrant development'})
    assert response.status_code==200,response.text
    end=client.get('/api/full-run/'+st['workflow_id']).json()
    assert end['status']=='PARTIAL' and end['linked_ids']['runs'] is None
    assert any(x['name']=='00b_evidence_review' and x['status']=='REJECTED' for x in end['stages'])
    with zipfile.ZipFile(io.BytesIO(client.get(end['bundle_url']).content)) as z:
        assert any(x.endswith('/00b_human_evidence_review.json') for x in z.namelist())


def test_synthetic_requires_explicit_mode(client):
    sample=client.get('/api/sample').json()
    response=client.post('/api/full-run/start',json={'brief':sample['brief']})
    assert response.status_code==422


def test_index_cache_integrity_requires_raw_source_hash(fixed_corpus):
    index=er.ensure_index('community_credit')
    assert index['index_action']=='BUILT'
    assert len(index['index_sha256_raw'])==64
    second=er.ensure_index('community_credit')
    assert second['index_action']=='REUSED'
    folder,_=fixed_corpus
    (folder/'transcripts.txt').write_text('replaced',encoding='utf-8')
    with pytest.raises(Exception):er.ensure_index('community_credit')


def test_cfpb_records_have_distinct_locators_and_are_not_marked_exact_raw_text(tmp_path,monkeypatch):
    monkeypatch.setattr(er,'ROOT',tmp_path/'evidence')
    folder=er.fixed_path('cfpb_sample');folder.mkdir(parents=True)
    payload=json.dumps({'hits':{'hits':[
        {'_id':'123','_source':{'product':'Credit card','issue':'Incorrect billing','complaint_what_happened':'Fee charged without clear notice'}},
        {'_id':'456','_source':{'product':'Checking account','issue':'Incorrect billing','complaint_what_happened':'Fee confusion on monthly account statement'}},
    ]}}).encode()
    (folder/'complaints.json').write_bytes(payload)
    (folder/'source_manifest.json').write_text(json.dumps({'dataset_id':'cfpb_sample','kind':'CONSUMER_COMPLAINT',
       'files':[{'name':'complaints.json','sha256_raw':hashlib.sha256(payload).hexdigest()}]}))
    er.ensure_index('cfpb_sample')
    index_data=json.loads((folder/'index.json').read_text())
    chunks=index_data['chunks']
    assert len(set(x['id'] for x in chunks))==len(chunks)
    assert {x['source_record_id'] for x in chunks}=={'123','456'}
    assert all(x['source_text_origin']=='NORMALIZED_API_RECORD' for x in chunks)
    results=er.requirements('cfpb_sample','incorrect billing fees')
    assert results['evidence']
    assert all(x['reference_status']=='NORMALIZED_API_RECORD' for x in results['evidence'])
