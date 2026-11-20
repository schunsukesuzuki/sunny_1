from __future__ import annotations

from fastapi.testclient import TestClient
from app import main
from app.baseline import BASELINE_SOURCE
from app.optimal import OPTIMAL_SOURCE
from app.evaluator import sha256_string, canonical_json
from app.e2b_runner import RawCandidate
from app.models import RequirementsDraft
from app.sample import SAMPLE_PROJECT

REQ = {
    'customer_problem': '講師の工数を削減する',
    'target_users': ['講師'],
    'value_hypothesis': '手作業削減',
    'must_have': ['時間制約'],
    'acceptance_criteria': ['全生徒の計画を出力'],
    'unverified_assumptions': ['支払意思'],
    'unanswered_questions': ['価格受容'],
    'next_customer_validation': ['講師インタビュー'],
}


def solve_source(source, dataset):
    namespace = {'__name__': 'test_run'}
    exec(source, namespace)
    return namespace['solve'](dataset)


def test_health_and_sample(monkeypatch):
    async def status():
        return {'reachable': True, 'installed': True, 'models': ['qwen3-coder:30b']}
    monkeypatch.setattr(main, 'local_model_status', status)
    client = TestClient(main.app)
    assert client.get('/api/health').json()['version'] == '0.6.0'
    assert 'LMS' in client.get('/api/sample').json()['brief']


def test_run_requires_e2b_key(monkeypatch):
    monkeypatch.delenv('E2B_API_KEY', raising=False)
    client = TestClient(main.app)
    response = client.post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': 'import json\n'*15,
    })
    assert response.status_code == 503


def test_complete_report_with_mocked_sandbox_boundary(monkeypatch, tmp_path):
    monkeypatch.setenv('E2B_API_KEY', 'fake-test-key')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)

    def fake_run(datasets, sources):
        assert list(sources) in (['baseline', 'optimal'], ['generated'], ['baseline', 'optimal', 'generated'])
        results = {}
        for name, source in sources.items():
            results[name] = []
            for seed, dataset in datasets.items():
                output = solve_source(OPTIMAL_SOURCE if name == 'generated' else source, dataset)
                results[name].append(RawCandidate(
                    name=name, seed=seed, source_sha256=sha256_string(source),
                    sandbox_id=f'mock-{name}', output=output,
                    output_sha256=sha256_string(canonical_json(output)),
                    elapsed_seconds=0.2,
                ))
        return results

    monkeypatch.setattr(main, 'run_in_e2b', fake_run)
    response = TestClient(main.app).post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': 'import json\n'*15,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data['seeds']) == 3
    assert len(data['holdout_seeds']) == 2
    assert data['holdout_seeds'][0] == 10042
    assert len(data['plan_comparisons']) >= 1
    assert data['baseline']['hard_constraint_pass']
    assert data['optimal']['hard_constraint_pass']
    assert data['generated']['hard_constraint_pass']
    assert data['generated']['same_plans_as_optimal'] == 2
    assert data['generated']['relative_to_optimal'] == 1.0
    assert len(data['repair_attempts']) == 1 and data['repair_attempts'][0]['verdict'] == 'CONDITIONAL GO'
    assert '静的Greedy' in data['report_markdown']
    assert '厳密DP' in data['report_markdown']
    assert '未検証' in data['report_markdown']
    run_path = tmp_path / data['run_id']
    for f in ['report.md', 'requirements.json', 'datasets.json', 'baseline.py',
              'optimal.py', 'generated.py', 'run.json']:
        assert (run_path / f).exists(), f
    assert not (run_path / '.env').exists()
    assert (run_path / 'attempts' / 'attempt_00.py').exists()
    assert (run_path / 'attempts' / 'attempt_00.json').exists()
    response = TestClient(main.app).get(f"/api/reports/{data['run_id']}/report.md")
    assert response.status_code == 200


def test_local_model_adapters(monkeypatch):
    async def fake_analyze(project):
        return RequirementsDraft.model_validate(REQ)
    async def fake_generate(project, requirements):
        from app.models import GeneratedCode
        return GeneratedCode(python_code='import json\n'*15, rationale='周辺効用を利用')
    monkeypatch.setattr(main, 'analyze_requirements', fake_analyze)
    monkeypatch.setattr(main, 'generate_code', fake_generate)
    client = TestClient(main.app)
    r = client.post('/api/analyze', json={'project': SAMPLE_PROJECT})
    assert r.status_code == 200
    r = client.post('/api/generate', json={'project': SAMPLE_PROJECT, 'requirements': REQ})
    assert r.status_code == 200 and 'python_code' in r.json()
