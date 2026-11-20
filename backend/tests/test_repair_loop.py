"""End-to-end mocked E2B / Qwen boundaries; the evaluator stays real."""
import asyncio
import json
from pathlib import Path

from fastapi.testclient import TestClient
from app import main
from app.baseline import BASELINE_SOURCE
from app.e2b_runner import RawCandidate
from app.evaluator import canonical_json, sha256_string
from app.models import GeneratedCode
from app.optimal import OPTIMAL_SOURCE
from app.repair_loop import execute_repair_loop, make_feedback
from app.sample import SAMPLE_PROJECT, create_dataset
from app.models import ProjectInput

REQ = {
    'customer_problem': '講師の工数を削減する',
    'target_users': ['講師'], 'value_hypothesis': '自動化で工数を減らす',
    'must_have': ['制約充足'], 'acceptance_criteria': ['すべての科目を出力'],
    'unverified_assumptions': ['購入意思'], 'unanswered_questions': ['単価'],
    'next_customer_validation': ['顧客インタビュー'],
}
BROKEN_SOURCE = 'import json\n# buggy solution\n' + 'x = 0\n' * 20
FIXED_SOURCE = 'import json\n# fixed solution\n' + 'x = 1\n' * 20


def solve(source, data):
    ns = {'__name__': 'test'}
    exec(source, ns)
    return ns['solve'](data)


def make_fake_executor(broken=True, always_fail=False, stderr=''):
    calls = []
    def executor(datasets, sources):
        calls.append(list(sources))
        results = {}
        for name, source in sources.items():
            values = []
            for seed, dataset in datasets.items():
                output = solve(BASELINE_SOURCE if name == 'baseline' else OPTIMAL_SOURCE, dataset)
                if name == 'generated' and (always_fail or (broken and source == BROKEN_SOURCE)):
                    # Exact issue observed in the user's real v0.2 generated code.
                    output['plans'][0]['allocations'].append({'subject': '理科', 'hours': 1})
                values.append(RawCandidate(
                    name=name, seed=seed, source_sha256=sha256_string(source),
                    sandbox_id=f'mock-{name}-{len(calls)}', output=output,
                    output_sha256=sha256_string(canonical_json(output)), stderr=stderr,
                    elapsed_seconds=0.4,
                ))
            results[name] = values
        return results
    return executor, calls


def sample_datasets():
    p = ProjectInput.model_validate(SAMPLE_PROJECT)
    return {seed: create_dataset(p.model_copy(update={'seed': seed})) for seed in (42, 43, 44)}


def test_repair_loop_failed_then_success_and_same_seed_coverage():
    executor, calls = make_fake_executor(stderr='WARNING: bad allocations')
    feedbacks = []
    async def repair(source, feedback, index):
        feedbacks.append(feedback)
        assert source == BROKEN_SOURCE and index == 1
        assert '重複' in feedback and 'WARNING' in feedback
        assert '0.71236' not in feedback  # no hidden DP target scores
        return GeneratedCode(python_code=FIXED_SOURCE, rationale='科目重複を修正')
    attempts, last_raw, revisions, chosen = asyncio.run(execute_repair_loop(
        sample_datasets(), BROKEN_SOURCE, 2, execute=executor, repair=repair,
    ))
    assert len(attempts) == 2
    assert [a.verdict for a in attempts] == ['NO-GO', 'PASS']
    assert len(feedbacks) == 1 and 'seed=42' in feedbacks[0]
    assert len(calls) == 2 and all(c == ['generated'] for c in calls)
    assert attempts[0].candidate.passed_seeds == 0
    assert attempts[1].candidate.passed_seeds == 3
    assert set(last_raw) == {42, 43, 44}
    assert revisions == [BROKEN_SOURCE, FIXED_SOURCE]
    assert chosen == 1


def test_bounded_retries_remain_no_go():
    executor, calls = make_fake_executor(always_fail=True)
    async def repair(source, feedback, index):
        return GeneratedCode(python_code=f'{FIXED_SOURCE}\n# retry {index}', rationale='attempt')
    attempts, _, revisions, chosen = asyncio.run(execute_repair_loop(
        sample_datasets(), BROKEN_SOURCE, 2, execute=executor, repair=repair,
    ))
    assert len(attempts) == 3 and len(calls) == 3
    assert len(revisions) == 3
    assert chosen is None
    assert all(not a.selected for a in attempts)
    assert all(a.verdict == 'NO-GO' for a in attempts)
    assert not attempts[-1].feedback  # no follow-on repair on final attempt


def test_model_failure_keeps_no_go_evidence():
    executor, calls = make_fake_executor()
    async def repair(source, feedback, index):
        raise RuntimeError('Ollama unavailable')
    attempts, _, revisions, chosen = asyncio.run(execute_repair_loop(
        sample_datasets(), BROKEN_SOURCE, 3, execute=executor, repair=repair,
    ))
    assert len(attempts) == 1 and len(revisions) == 1
    assert chosen is None
    assert attempts[0].verdict == 'NO-GO'
    assert 'Ollama unavailable' in attempts[0].repair_error


def test_full_api_report_retains_no_go_errors_after_success(monkeypatch, tmp_path):
    monkeypatch.setenv('E2B_API_KEY', 'fake-test-key')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    executor, calls = make_fake_executor(stderr='bad allocation stderr')
    monkeypatch.setattr(main, 'run_in_e2b', executor)
    async def fixer(source, feedback, index):
        assert '重複' in feedback
        return GeneratedCode(python_code=FIXED_SOURCE, rationale='fixed')
    monkeypatch.setattr(main, 'repair_code', fixer)
    response = TestClient(main.app).post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': BROKEN_SOURCE,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['functional_gate'].startswith('PASS')
    assert result['selection_gate'].startswith('CONDITIONAL GO')
    assert len(result['repair_attempts']) == 2
    report = result['report_markdown']
    assert 'Attempt 0 — NO-GO' in report and '重複' in report
    assert 'bad allocation stderr' in report and 'seed=42' in report
    folder = tmp_path / result['run_id']
    assert (folder / 'attempts/attempt_00.py').read_text() == BROKEN_SOURCE
    assert (folder / 'attempts/attempt_01.py').read_text() == FIXED_SOURCE
    assert (folder / 'generated.py').read_text() == FIXED_SOURCE
    assert len(calls) == 4  # DEV refs + initial + repair + final HOLDOUT 3-way


def test_full_api_persistent_no_go_has_logs(monkeypatch, tmp_path):
    monkeypatch.setenv('E2B_API_KEY', 'fake-test-key')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    executor, calls = make_fake_executor(always_fail=True, stderr='still broken')
    monkeypatch.setattr(main, 'run_in_e2b', executor)
    async def fixer(source, feedback, index):
        return GeneratedCode(python_code=f'{FIXED_SOURCE}\n# retry {index}', rationale='attempt')
    monkeypatch.setattr(main, 'repair_code', fixer)
    r = TestClient(main.app).post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': BROKEN_SOURCE,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['functional_gate'].startswith('NO-GO')
    assert data['selection_gate'].startswith('NO-GO')
    assert len(data['repair_attempts']) == 3
    report = (tmp_path / data['run_id'] / 'report.md').read_text()
    for i in range(3):
        assert f'Attempt {i} — NO-GO' in report
        assert (tmp_path / data['run_id'] / f'attempts/attempt_{i:02d}.json').is_file()
    assert 'still broken' in report
    assert len(calls) == 4  # DEV references + 3 attempts; NO HOLDOUT when all invalid
    assert data['selected_attempt_index'] is None
    assert not data['holdout_executed']
    assert data['generated'] is None
    assert data['baseline'] is None and data['optimal'] is None
    assert not (tmp_path / data['run_id'] / 'generated.py').exists()
    assert 'HOLDOUT未実行' in report
    assert data['plan_comparisons_source'] == 'development'
    assert (tmp_path / data['run_id'] / 'attempts/attempt_02.diff').exists()
