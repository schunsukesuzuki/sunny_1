"""Evidence RAG: bounded fixed-source download, exact provenance, no automatic business approval."""
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from app import evidence_rag as rag
from app import main
from test_outer_loop_v08 import client

@pytest.fixture
def fixed_corpus(tmp_path, monkeypatch):
    monkeypatch.setattr(rag,'ROOT',tmp_path/'evidence')
    folder=rag.fixed_path('community_credit');folder.mkdir(parents=True)
    text=('Participant: My credit union denied my card and told me to call twice. I could not understand the fee.\n'
          'Interviewer: What happened with financial service access?\n'
          'Participant: I needed a cheaper checking account; I asked about account fees and was confused by the explanation.\n')
    data=text.encode('utf-8')
    (folder/'transcripts.txt').write_bytes(data)
    (folder/'source_manifest.json').write_text(json.dumps({'dataset_id':'community_credit','kind':'INTERVIEW_TRANSCRIPT','files':[{'name':'transcripts.txt','sha256_raw':hashlib.sha256(data).hexdigest()}]}))
    return folder,text

def test_provenance_and_unverified_candidates(fixed_corpus):
    folder,text=fixed_corpus
    idx=rag.index('community_credit')
    assert idx['chunk_count']>=1
    result=rag.requirements('community_credit','checking account fees')
    assert result['evidence']
    assert result['evaluation']['semantic_entailment']=='UNVERIFIED'
    assert result['evaluation']['customer_approval']=='NOT_OBTAINED'
    for x in result['evidence']:
        assert text[x['start_char']:x['end_char']]==x['quote'] or text[x['start_char']:x['end_char']].startswith(x['quote'])
        assert x['validity']=='UNVERIFIED'
    for x in result['requirement_candidates']:
        assert x['proposed_requirement']=='REQUIRES_HUMAN_DERIVATION'
    with zipfile.ZipFile(io.BytesIO(rag.rag_archive(result['rag_id']))) as z:
        assert {'rag.json','report.md'}<=set(z.namelist())
        assert '≠' in z.read('report.md').decode()

def test_dataset_archive_requires_download_and_checks_hash(tmp_path,monkeypatch,fixed_corpus):
    folder,_=fixed_corpus
    blob=rag.archive('community_credit')
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        assert 'transcripts.txt' in z.namelist()
    (folder/'transcripts.txt').write_text('tampered')
    with pytest.raises(HTTPException) as e:rag.archive('community_credit')
    assert e.value.status_code==409

def test_fixed_allowlist_rejects_arbitrary_sources(tmp_path,monkeypatch):
    monkeypatch.setattr(rag,'ROOT',tmp_path)
    with pytest.raises(HTTPException):rag.fixed_path('https://internal-host.example')
    with pytest.raises(HTTPException):rag.acquire('private_server')

def test_no_index_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(rag,'ROOT',tmp_path)
    with pytest.raises(HTTPException) as e:rag.search('cfpb_sample','bank')
    assert e.value.status_code==409

def test_00_api_and_download_are_separate(fixed_corpus,client):
    x=client.get('/api/evidence/datasets');assert x.status_code==200
    assert {d['id'] for d in x.json()['datasets']}=={'community_credit','cfpb_sample','insurance_claims_uk'}
    a=client.post('/api/evidence/index',json={'dataset_id':'community_credit'});assert a.status_code==200,a.text
    r=client.post('/api/evidence/requirements',json={'dataset_id':'community_credit','query':'fees checking account'})
    assert r.status_code==200,r.text
    data=r.json();assert data['rag_id']
    b=client.get(f"/api/evidence/results/{data['rag_id']}/bundle")
    assert b.status_code==200
    d=client.get('/api/evidence/datasets/community_credit/download');assert d.status_code==200
    assert d.content!=b.content

class _FakeResponse:
    status_code=200
    headers={}
    def __init__(self,data):self.data=data
    def __enter__(self):return self
    def __exit__(self,*a):return False
    def raise_for_status(self):pass
    def iter_bytes(self,n):yield self.data

class _FakeClient:
    def __init__(self,payloads):self.payloads=payloads
    def stream(self,method,url,follow_redirects=False):return _FakeResponse(self.payloads[url])

def test_allowlisted_download_mocked_network(tmp_path,monkeypatch):
    monkeypatch.setattr(rag,'ROOT',tmp_path)
    dataset=rag.DATASETS['community_credit']
    payloads={u:(b'This participant discussed credit union access and fee transparency.\n' if 'Transcripts' in u else b'Questions and interview context about banking experiences.\n') for u in dataset['files'].values()}
    m=rag.acquire('community_credit',client=_FakeClient(payloads))
    assert m['status']=='DOWNLOADED'
    assert len(m['files'])==3
    assert all(len(x['sha256_raw'])==64 for x in m['files'])
    assert rag.index('community_credit')['chunk_count']>=1


def test_full_run_public_retrieval_requires_human_and_is_archived(fixed_corpus,client,monkeypatch):
    # No precomputed rag_id or manual 00 steps: batch must actually index and retrieve.
    from app import llm
    from test_full_run_v015 import fake_design
    monkeypatch.setattr(llm,'design',fake_design)
    sample=client.get('/api/sample').json()
    response=client.post('/api/full-run/start',json={
        'brief':sample['brief'],'evidence_mode':'public','dataset_id':'community_credit',
        'evidence_query':'account fees','case_ids':['fifo_sla_conflict'],'seed':42})
    assert response.status_code==200,response.text
    state=client.get('/api/full-run/'+response.json()['workflow_id']).json()
    assert state['status']=='AWAITING_EVIDENCE_REVIEW',state
    assert any(x['name']=='00_evidence_grounded_requirements' and x['status']=='COMPLETED_WITH_FINDINGS'
               for x in state['stages'])
    assert state['linked_ids']['runs'] is None
    assert state['evidence_review']['evidence']
    with zipfile.ZipFile(io.BytesIO(client.get(state['bundle_url']).content)) as z:
        assert json.loads(z.read('manifest.json'))['status']=='PARTIAL'
        names=z.namelist()
        for f in ('00_evidence_grounded_requirements.json','00_source_manifest.json','00_index_metadata.json','00_rag_report.md'):
            assert any(n.endswith('/'+f) for n in names)
        assert not any(n.endswith('/01_input.json') for n in names)
        rag_data=json.loads(z.read(next(n for n in names if n.endswith('/00_evidence_grounded_requirements.json'))))
        assert rag_data['evaluation']['customer_approval']=='NOT_OBTAINED'
        assert all(x['proposed_requirement']=='REQUIRES_HUMAN_DERIVATION' for x in rag_data['requirement_candidates'])
    review=client.post('/api/full-run/review-evidence',json={
        'workflow_id':state['workflow_id'],'decision':'rejected','actor':'Reviewer',
        'rationale':'Retrieved excerpts do not establish this service goal'})
    assert review.status_code==200,review.text
    final=client.get('/api/full-run/'+state['workflow_id']).json()
    assert final['status']=='PARTIAL' and final['phase']=='EVIDENCE_REJECTED_BY_HUMAN'
    assert final['linked_ids']['runs'] is None
    with zipfile.ZipFile(io.BytesIO(client.get(final['bundle_url']).content)) as z:
        assert any(x.endswith('/00b_human_evidence_review.json') for x in z.namelist())
