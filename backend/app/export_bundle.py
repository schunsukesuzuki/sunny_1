"""Build one audit-complete package from linked workflow / R1 records.

The archive is an immutable snapshot; hashes cover raw file bytes, and every
missing, excluded, or failed stage appears in its manifest. Nothing silently
succeeds on an omitted artifact. No .env, local token, or unrelated history.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

MAX_FILE_BYTES = 20_000_000
MAX_TOTAL_BYTES = 150_000_000
KINDS = ('runs','proposals','approvals','experiments','policy_validations','benchmarks','assessments')


def make_manifest(artifact_dir: Path, export_id: str, identifiers: dict,
                  stages: list[dict], created_at: str) -> dict:
    files=[]; missing=[]; skipped=[]; total=0
    for kind in KINDS + (("workflows",) if identifiers.get("workflows") else ()):
        ident=identifiers.get(kind)
        if not ident:
            missing.append({'kind':kind,'reason':'No linked artifact from this run'})
            continue
        folder=artifact_dir / kind / ident
        if not folder.is_dir():
            missing.append({'kind':kind,'artifact_id':ident,'reason':'Folder not found'})
            continue
        listed=sorted(x for x in folder.iterdir() if x.is_file() and not x.is_symlink())
        if not listed:
            missing.append({'kind':kind,'artifact_id':ident,'reason':'No files'})
        for f in listed:
            size=f.stat().st_size
            entry={'kind':kind,'artifact_id':ident,'path':f'{kind}/{ident}/{f.name}',
                   'bytes':size}
            if size>MAX_FILE_BYTES or total+size>MAX_TOTAL_BYTES:
                skipped.append({**entry,'reason':'Export size guardrail'})
                continue
            entry['sha256_raw_bytes']=hashlib.sha256(f.read_bytes()).hexdigest()
            files.append(entry)
            total+=size
    incomplete=bool(missing or skipped or any(stage.get('status') not in ('COMPLETED','COMPLETED_WITH_FINDINGS') for stage in stages))
    return {'format_version':'AUDIT-EXPORT-v0.18.0', 'export_id':export_id,
            'created_at':created_at,'status':'PARTIAL' if incomplete else 'COMPLETE',
            'experiment_id':identifiers.get('experiments'),
            'linked_ids':identifiers,'stages':stages,'files':files,'missing':missing,
            'skipped':skipped,'file_count':len(files),'total_file_bytes':total,
            'integrity':'File SHA256 = hash of raw file bytes. Not a signed attestation.',
            'scope':'Synthetic demonstration only. No external/customer/legal validation.'}


def make_intro(manifest:dict, assessment:dict|None)->str:
    lines=['# Claims Operations Planner — v0.18 Evidence-to-Evaluation Audit Package','',
           f"- Export: `{manifest['export_id']}`",
           f"- Original experiment: `{manifest['experiment_id']}`",
           f"- Export completeness: **{manifest['status']}**",
           f"- Files included: **{manifest['file_count']}**",
           '- All methods run on synthetic customer/case fixtures, not real customer data.',
           '- GO, if any, means *Customer Discovery only*. Production is never authorized.',
           '- Public-evidence mode pauses at step 00b for explicit human review; step 05 also requires human approval.',
           '- Public source materials are screened for topic relevance; mismatched evidence is blocked. Human-selected thresholds run on fixed synthetic claims cases. No arbitrary customer requirements are executable.',
           '- Raw source snapshots and original document SHA256 are included in the workflow folder; additional policy/stress and configured-KPI results are stored separately.',
           '- `manifest.json` lists every included file with raw-bytes SHA256, omitted categories, and failures.','',
           '## Execution stages','']
    for stage in manifest['stages']:
        lines.append(f"- **{stage['name']}**: {stage['status']}" + (f" — {stage['detail']}" if stage.get('detail') else ''))
    lines.extend(['','## Assessment',''])
    if assessment:
        d=assessment.get('decision',{})
        sm=assessment.get('summary_metrics',{})
        lines.extend([f"- Preliminary: **{d.get('status','HOLD')}** ({d.get('stage')})",
                      f"- Production: **{d.get('production_status','NO_GO')}**",
                      f"- R1 behavioral probes: **{'PASS' if sm.get('behavioral_contract_pass') else 'HOLD'}**",
                      f"- Stress test vs heuristic: **{'NO_REGRESSION_DETECTED' if sm.get('stress_no_regression_vs_reference') else 'REVIEW_REQUIRED'}**",
                      f"- Diagnostic benchmark all PASS: **{sm.get('benchmark_all_trials_pass',False)}**"])
    else:
        lines.append('- Assessment not produced; see stage failure in manifest.')
    lines.extend(['','## Reading order','',
                  '0. `workflows/<id>/00_evidence_grounded_requirements.json`, `00_source_manifest.json`, `00_index_metadata.json`, `00_rag_report.md` — retrieved public evidence; no real-world approval',
                  '0b. `workflows/<id>/00b_human_evidence_review.json` — human-selected evidence; check domain alignment and reviewer judgment',
                  '0c. `workflows/<id>/00c_grounded_test_contract.json` and `00c_technical_spec.md` — human-configured bounded KPI thresholds',
                  '8c. `workflows/<id>/08c_grounded_kpi_verification.json` — bounded deterministic evaluation; SYNTHETIC ONLY',
                  '1. `workflows/<id>/01_input.json` and `02_service_design.json` — input and generated service design (v0.15 full batch)',
                  '2. `assessments/<id>/report.md` — business/delivery decision and evidence register',
                  '3. `policy_validations/<id>/report.md` — semantic contract and stress failures',
                  '4. `benchmarks/<id>/report.md` — diagnostic comparison (single-case PASS is NOT model reliability)',
                  '5. `experiments/<id>/report.md` — R0/R1 KPI and source attempts',
                  '6. `runs/`, `proposals/`, `approvals/` — lineage, data, LLM diagnoses, approval',
                  '', '## Known limitations','',
                  '- Behavioral probes are not mathematical proof of the full specification.',
                  '- No high-load result can be generalized to production distributions.',
                  '- Unassigned claims are counted as missed deadlines; never ignore them when comparing methods.',
                  '- Synthetic evidence IDs are internal pointers, not public citations or validation.',
                  '- Dataset download and indexing must actually succeed in public mode; never interpret missing data as COMPLETED.',
                  '- Public banking materials do not support insurance claim workflows; the compatibility gate blocks such handoffs.',
                  '- FCA/FOS material supports problem context but does not establish a scheduling mechanism or a German customer request.',
                  '- Source manifest/file hashes establish local integrity only, not semantic truth or representative sampling.',
                  '- Public evidence excerpts remain unverified as supporting customer requirements; RAG is never automatic approval.',
                  '- AI model diagnostics, human approval, and KPI PASS have separate scopes.',
                  ''])
    if manifest['missing'] or manifest['skipped']:
        lines.append('**Partial/incomplete output:** See `manifest.json` for missing or skipped artifacts.')
    return '\n'.join(lines)+'\n'


def package(artifact_dir:Path, destination:Path, manifest:dict, assessment:dict|None) -> None:
    intro=make_intro(manifest,assessment)
    with ZipFile(destination,'w',compression=ZIP_DEFLATED) as z:
        z.writestr('00_START_HERE.md', intro)
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for e in manifest['files']:
            z.write(artifact_dir / e['path'], arcname=e['path'])
