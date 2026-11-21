"""Evidence-grounded requirements: provenance-first retrieval and conservative requirements candidates.

Fixed-source dataset acquisition, intentionally NOT a generic URL fetcher.
No model may certify evidence validity or customer requirements.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import unicodedata
import uuid
import zipfile

import httpx
from fastapi import HTTPException

ROOT = Path(os.environ.get('ARTIFACT_DIR','/app/artifacts')) / 'evidence'
MAX_BYTES = 8_000_000
MAX_DOC_CHARS = 1_600_000
MAX_CHUNKS = 2500
DATASETS = {
 'community_credit': {
   'title':'Community Credit — 30 consumer financial interviews (2022)',
   'source':'https://zenodo.org/records/10425908',
   'publisher':'Maurer et al. / Dryad record mirrored by Zenodo',
   'type':'INTERVIEW_TRANSCRIPT',
   'files': {
    'transcripts.txt':'https://zenodo.org/records/10425908/files/Maurer2022CommunityCreditInterviews_Transcripts.txt?download=1',
    'question_guide.txt':'https://zenodo.org/records/10425908/files/Maurer2022CommunityCreditInterviews_Question_Guide.txt?download=1',
    'readme.txt':'https://zenodo.org/records/10425908/files/README.md?download=1',
   },
   'notice':'匿名化インタビュー。小標本であり金融利用者全体を代表しない。顧客の承認済み要求ではない。元資料の条件を確認。',
 },
 'cfpb_sample': {
   'title':'CFPB Consumer Complaint Database — bounded public complaint sample',
   'source':'https://www.consumerfinance.gov/data-research/consumer-complaints/',
   'publisher':'Consumer Financial Protection Bureau',
   'type':'CONSUMER_COMPLAINT',
   'files': {'complaints.json':'https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/?size=60&no_aggs=true&field=all&sort=created_date_desc'},
   'notice':'当事者の申告であり事実認定ではない。母集団の代表標本ではない。新規ナラティブ公開停止等の影響で原文が欠落する場合あり。',
 },
}

def utc(): return datetime.now(timezone.utc).isoformat(timespec='seconds')
def digest(b:bytes):return hashlib.sha256(b).hexdigest()
def fixed_path(dataset:str):
 if dataset not in DATASETS: raise HTTPException(404,'Unknown dataset. Fixed allowlist only.')
 return ROOT/dataset

def _fetch(url:str,client:httpx.Client)->bytes:
 # URLs are immutable allowlist entries, never user-controlled; redirects are only to HTTPS.
 with client.stream('GET',url,follow_redirects=False) as r:
  if r.status_code in (301,302,303,307,308):
   from urllib.parse import urlparse, urljoin
   dest=urljoin(url,r.headers.get('location',''))
   host=urlparse(dest).hostname or ''
   if urlparse(dest).scheme!='https' or not (host=='zenodo.org' or host.endswith('.zenodo.org') or host=='www.consumerfinance.gov' or host=='consumerfinance.gov'):
    raise ValueError('Remote redirect host not on allowlist')
   return _fetch(dest,client)
  r.raise_for_status()
  data=bytearray()
  for chunk in r.iter_bytes(65536):
   data+=chunk
   if len(data)>MAX_BYTES:raise ValueError('Dataset exceeds 8MB download limit')
  return bytes(data)

def acquire(dataset:str, *,client:httpx.Client|None=None)->dict:
 desc=DATASETS.get(dataset)
 if not desc:raise HTTPException(404,'Unknown dataset')
 folder=fixed_path(dataset);folder.mkdir(parents=True,exist_ok=True)
 own=client is None
 if own: client=httpx.Client(timeout=httpx.Timeout(45.0,connect=8.0),headers={'User-Agent':'Claims-Evidence-Demo/0.17'})
 try:
  fetched={}
  for filename,url in desc['files'].items():
   b=_fetch(url,client)
   if not b:raise ValueError(f'Empty source file {filename}')
   if filename.endswith('.json'): json.loads(b)
   fetched[filename]=b
  for name,content in fetched.items():
   temp=folder/(name+'.tmp');temp.write_bytes(content);os.replace(temp,folder/name)
  meta={'dataset_id':dataset,'source':desc['source'],'publisher':desc['publisher'],'kind':desc['type'],
        'notice':desc['notice'],'downloaded_at_utc':utc(),'files':[{ 'name':name,'sha256_raw':digest(b),'bytes':len(b),'url':desc['files'][name]} for name,b in fetched.items()],
        'status':'DOWNLOADED','customer_validity':'UNVERIFIED'}
  (folder/'source_manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
  return meta
 finally:
  if own:client.close()

def validate_download(dataset: str) -> dict:
 """Fail closed if a cached public source is missing, malformed, or modified."""
 folder=fixed_path(dataset)
 mf=folder/'source_manifest.json'
 if not mf.is_file():raise HTTPException(409, 'Dataset has not been downloaded')
 try:meta=json.loads(mf.read_text(encoding='utf-8'))
 except (ValueError,OSError) as exc:raise HTTPException(409,'Corrupt source manifest') from exc
 if meta.get('dataset_id')!=dataset or not isinstance(meta.get('files'),list) or not meta['files']:
  raise HTTPException(409,'Dataset source manifest identity or file list invalid')
 for entry in meta['files']:
  name=entry.get('name','')
  if not name or '/' in name or '..' in name or name not in DATASETS[dataset]['files']:
   raise HTTPException(409,'Source manifest file name not allowlisted')
  source=folder/name
  if not source.is_file() or digest(source.read_bytes())!=entry.get('sha256_raw'):
   raise HTTPException(409,f'Source file missing or SHA256 mismatch: {name}')
 return meta


def ensure_index(dataset: str) -> dict:
 """Regenerate absent/stale indexes, but never accept a changed source silently."""
 validate_download(dataset)
 folder=fixed_path(dataset)
 manifest_hash=digest((folder/'source_manifest.json').read_bytes())
 index_file=folder/'index.json'
 reuse=False
 if index_file.is_file():
  try:
   existing=json.loads(index_file.read_text(encoding='utf-8'))
   reuse=(existing.get('dataset_id')==dataset and
          existing.get('source_manifest_sha256')==manifest_hash and
          existing.get('chunk_count',0)>0 and
          len(existing.get('chunks',[]))==existing['chunk_count'])
  except (ValueError,KeyError,TypeError,AttributeError):reuse=False
 if not reuse:
  summary=index(dataset)
 else:
  summary={k:v for k,v in existing.items() if k!='chunks'}
 summary=dict(summary)
 summary['index_action']='REUSED' if reuse else 'BUILT'
 summary['index_sha256_raw']=digest(index_file.read_bytes())
 return summary


def archive(dataset:str)->bytes:
 folder=fixed_path(dataset)
 if not (folder/'source_manifest.json').is_file():raise HTTPException(404,'Dataset not downloaded yet')
 manifest=json.loads((folder/'source_manifest.json').read_text(encoding='utf-8'))
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  z.write(folder/'source_manifest.json','source_manifest.json')
  for x in manifest['files']:
   name=x['name'];fp=folder/name
   if not fp.exists() or digest(fp.read_bytes())!=x['sha256_raw']:raise HTTPException(409,'Source hash mismatch')
   z.write(fp,name)
 return buf.getvalue()

def _normalize(s:str)->str:return unicodedata.normalize('NFKC',s).lower()
def tokens(s:str)->list[str]:
 s=_normalize(s)
 return re.findall(r'[a-z0-9]{2,}|[\u3040-\u30ff\u3400-\u9fff]{2,}',s)
def trigrams(s:str)->set[str]:
 s=re.sub(r'\s+',' ',_normalize(s))
 return {s[i:i+3] for i in range(max(0,len(s)-2))}

def _chunk(text:str,source:str,dataset:str,kind:str,max_length:int=950,record_locator:str|None=None)->list[dict]:
 """Exact fixed-width windows of source text, with modest overlap.

 Offsets always reference original decoded text; no invented page/line metadata.
 """
 output=[]
 stride=max_length-130
 for pos in range(0,len(text),stride):
  raw_piece=text[pos:pos+max_length]
  if len(raw_piece.strip())<35:continue
  first=len(raw_piece)-len(raw_piece.lstrip())
  excerpt=raw_piece.strip()
  start=pos+first
  output.append({'id':f'{dataset}:{source}{('#'+record_locator) if record_locator else ''}:{start}','dataset_id':dataset,'source_file':source,'source_type':kind,
                  'source_record_id':record_locator, 'source_text_origin':'NORMALIZED_API_RECORD' if record_locator else 'EXACT_SOURCE_TEXT',
                  'start_char':start,'end_char':start+len(excerpt),'text':excerpt,'source_url':DATASETS[dataset]['source'],
                  'evidence_class':'PUBLIC_SOURCE_UNVERIFIED'})
  if len(output)>=MAX_CHUNKS:break
 return output

def index(dataset:str)->dict:
 folder=fixed_path(dataset)
 mfile=folder/'source_manifest.json'
 if not mfile.exists():raise HTTPException(409,'Download dataset first')
 meta=json.loads(mfile.read_text(encoding='utf-8'))
 docs=[]
 for file in meta['files']:
  name=file['name'];raw=(folder/name).read_bytes()
  if digest(raw)!=file['sha256_raw']:raise HTTPException(409,'Source bytes changed; download again')
  if name.endswith('.json'):
   raw_obj=json.loads(raw)
   hits=raw_obj.get('hits',{}).get('hits',[]) if isinstance(raw_obj,dict) else []
   if not hits and isinstance(raw_obj,dict):hits=raw_obj.get('results',[])
   for row_num,h in enumerate(hits[:100]):
    src=h.get('_source',h) if isinstance(h,dict) else {}
    if not isinstance(src,dict):continue
    narrative=src.get('complaint_what_happened') or ''
    category=src.get('issue','') or ''
    product=src.get('product','') or ''
    if not narrative and not category:continue
    strval=f'Product: {product}\nIssue: {category}\nConsumer narrative: {narrative}'[:5000]
    record_id=str(h.get('_id') or src.get('complaint_id') or f'row-{row_num:04d}')[:100]
    docs.extend(_chunk(strval,name,dataset,meta['kind'],record_locator=record_id))
  elif name.endswith('.txt') and name not in ('readme.txt','question_guide.txt'):
   t=raw.decode('utf-8-sig',errors='replace')[:MAX_DOC_CHARS]
   docs.extend(_chunk(t,name,dataset,meta['kind']))
  if len(docs)>=MAX_CHUNKS:break
 docs=docs[:MAX_CHUNKS]
 if not docs:raise HTTPException(422,'No usable source passages found; inspect download source')
 data={'dataset_id':dataset,'source_manifest_sha256':digest(mfile.read_bytes()),'indexed_at_utc':utc(),
       'chunk_count':len(docs),'chunks':docs,'method':'BM25 + character ngram fuzzy reranking with RRF; optional semantic embeddings not used',
       'limitations':'Metadata and exact excerpts are traceable. Retrieval relevance and semantic support are not proven.'}
 out=folder/'index.json';temp=folder/'index.json.tmp'
 temp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');os.replace(temp,out)
 return {k:v for k,v in data.items() if k!='chunks'}

def search(dataset:str,query:str,top_k:int=6)->dict:
 if not query.strip():raise HTTPException(422,'Query must not be blank')
 path=fixed_path(dataset)/'index.json'
 if not path.is_file():raise HTTPException(409,'Index the downloaded dataset first')
 idx=json.loads(path.read_text(encoding='utf-8'))
 docs=idx['chunks'];n=len(docs)
 qt=Counter(tokens(query));df=Counter()
 corpus=[]
 for doc in docs:
  tt=Counter(tokens(doc['text']));corpus.append(tt);df.update(tt.keys())
 avg=sum(sum(t.values()) for t in corpus)/max(n,1)
 sparse=[];fuzzy=[];qgrams=trigrams(query)
 for i,(d,t) in enumerate(zip(docs,corpus)):
  dl=sum(t.values());score=0.0
  for term,qfreq in qt.items():
   freq=t.get(term,0)
   if freq:score+=math.log(1+(n-df[term]+.5)/(df[term]+.5))*freq*2.2/(freq+1.2*(.25+.75*dl/(avg or 1)))
  sparse.append((i,score))
  gr=trigrams(d['text']);fuzzy.append((i,len(qgrams & gr)/math.sqrt(max(1,len(qgrams))*max(1,len(gr)))))
 sparse.sort(key=lambda x:(-x[1],x[0]));fuzzy.sort(key=lambda x:(-x[1],x[0]))
 rank1={i:r for r,(i,_) in enumerate(sparse[:80],1)};rank2={i:r for r,(i,_) in enumerate(fuzzy[:80],1)}
 scored=[]
 for i,d in enumerate(docs):
  if i not in rank1 and i not in rank2:continue
  if sparse[0][1]<=0 and fuzzy[0][1]<=0:continue
  v=(1/(60+rank1[i]) if i in rank1 else 0)+(1/(60+rank2[i]) if i in rank2 else 0)
  scored.append((v,i))
 scored.sort(key=lambda x:(-x[0],x[1]))
 hits=[{**docs[i],'rrf_score':round(score,7),'exact_source_match':docs[i].get('source_text_origin')=='EXACT_SOURCE_TEXT'} for score,i in scored[:top_k]]
 return {'dataset_id':dataset,'query':query,'retrieval_method':idx['method'],'hits':hits,'total_indexed':n,
         'limitations':'RRF ranks passages; it does NOT establish evidence validity, causal attribution, or requirement correctness.'}

def requirements(dataset:str,query:str)->dict:
 result=search(dataset,query,top_k=6)
 hits=result['hits'];evidence=[];candidates=[]
 for i,h in enumerate(hits):
  eid=f'PUB-{i+1:03d}'
  evidence.append({'evidence_id':eid,'chunk_id':h['id'],'source_file':h['source_file'],'source_url':h['source_url'],
                   'start_char':h['start_char'],'end_char':h['end_char'],'quote':h['text'][:420],
                   'reference_status':'EXACT_LOCAL_EXCERPT' if h.get('exact_source_match') else 'NORMALIZED_API_RECORD',
                   'source_record_id':h.get('source_record_id'), 'support_status':'NOT_SEMANTICALLY_VERIFIED',
                   'source_type':h['source_type'],'validity':'UNVERIFIED'})
  candidates.append({'requirement_candidate_id':f'RC-{i+1:03d}','evidence_ids':[eid],
     'observed_issue':h['text'][:320],'proposed_requirement':'REQUIRES_HUMAN_DERIVATION',
     'business_kpi':'TO_BE_DEFINED_WITH_CUSTOMER','alternative_explanations':['Alternative causes not yet evaluated'],
     'status':'REQUIRES_VALIDATION','reason':'Verbatim retrieval is evidence of a statement, not of an approved business requirement.'})
 assessment={'dataset_id':dataset,'created_at':utc(),'query':query,'evidence':evidence,'requirement_candidates':candidates,
  'retrieval':{k:result[k] for k in ('retrieval_method','total_indexed')},
  'evaluation':{'citation_pointer_accuracy':'PASS_LOCAL_POINTERS_ONLY' if evidence else 'NO_EVIDENCE',
     'evidence_validity':'UNVERIFIED','semantic_entailment':'UNVERIFIED','requirements_correctness':'UNVERIFIED',
     'customer_approval':'NOT_OBTAINED','contradiction_search':'NOT_PROVEN'},
  'safe_summary':'Public statements retrieved; human must derive, verify and approve any requirements. These are NOT customer requirements.'}
 aid=str(uuid.uuid4());assessment['rag_id']=aid
 folder=ROOT/'rag_runs'/aid;folder.mkdir(parents=True,exist_ok=True)
 (folder/'rag.json').write_text(json.dumps(assessment,ensure_ascii=False,indent=2),encoding='utf-8')
 (folder/'report.md').write_text(report_md(assessment),encoding='utf-8')
 return assessment

def report_md(r:dict)->str:
 lines=['# Evidence-grounded Requirements — v0.17','',f"- Query: {r['query']}",f"- Dataset: {r['dataset_id']}",
        '- Status: **REQUIRES_VALIDATION** — no customer approval, no causal or semantic proof.','',
        '## Retrieved source excerpts (not approved requirements)','']
 for e in r['evidence']:
  lines.extend([f"### {e['evidence_id']} — `{e['chunk_id']}`",f"Source: {e['source_url']} / `{e['source_file']}` / chars {e['start_char']}–{e['end_char']}",
                f"Record locator: {e.get('source_record_id') or 'original decoded text'} / Reference status: {e['reference_status']}",
                f"Quote (truncated): {json.dumps(e['quote'],ensure_ascii=False)}",''])
 lines.extend(['## Evaluation','', '| Field | Value |','|---|---|'])
 for k,v in r['evaluation'].items():lines.append(f'| {k} | {v} |')
 lines.extend(['','Evidence ID correctness ≠ evidence validity ≠ diagnostic correctness.','All requirements remain hypotheses; synthetic R0/R1 claims evaluation is a separate experiment.',''])
 return '\n'.join(lines)

def rag_archive(run_id:str)->bytes:
 try: normalized=str(uuid.UUID(run_id))
 except ValueError:raise HTTPException(404,'Unknown RAG result')
 if normalized!=run_id:raise HTTPException(404,'Unknown RAG result')
 folder=ROOT/'rag_runs'/run_id
 if not (folder/'rag.json').exists():raise HTTPException(404,'Unknown RAG result')
 buffer=io.BytesIO()
 with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as z:
  for f in folder.iterdir():
   if f.is_file():z.write(f,f.name)
 return buffer.getvalue()
