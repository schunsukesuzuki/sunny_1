"""v0.4: quality HOLD loop, DEV-only feedback, best-dev selection, holdout safety."""
from __future__ import annotations

import asyncio

from fastapi.testclient import TestClient

from app import main
from app.baseline import BASELINE_SOURCE
from app.optimal import OPTIMAL_SOURCE
from app.e2b_runner import RawCandidate
from app.evaluator import canonical_json, sha256_string, build_plan_comparisons
from app.models import GeneratedCode, ProjectInput
from app.repair_loop import execute_repair_loop, candidate_from_raw
from app.sample import SAMPLE_PROJECT, create_dataset
from test_api import REQ

LOW_CODE = '# baseline-like candidate\n' + 'x = 1\n' * 25
HIGH_CODE = '# optimized candidate\n' + 'x = 2\n' * 25
BROKEN_CODE = '# invalid candidate\n' + 'x = 3\n' * 25
MEDIUM_CODE = '# partial improvement candidate\n' + 'x = 5\n' * 25
WORSE_CODE = '# worse but passing candidate\n' + 'x = 4\n' * 25


def solve(source: str, data: dict) -> dict:
    ns = {'__name__': 'unit_test'}
    exec(source, ns)
    return ns['solve'](data)


def fake_executor(datasets, sources):
    results = {}
    for name, source in sources.items():
        records = []
        for seed, dataset in datasets.items():
            if name == 'baseline' or source == LOW_CODE:
                output = solve(BASELINE_SOURCE, dataset)
            else:
                output = solve(OPTIMAL_SOURCE, dataset)
            if source == BROKEN_CODE:
                output['plans'][0]['allocations'].append({'subject': '理科', 'hours': 1})
            if source == MEDIUM_CODE:
                # Half of students use DP and the rest use fixed greedy.
                dp_out = solve(OPTIMAL_SOURCE, dataset)
                base_out = solve(BASELINE_SOURCE, dataset)
                output = {'plans': dp_out['plans'][:6] + base_out['plans'][6:]}
            if source == WORSE_CODE:
                # Valid but demonstrably worse than MEDIUM_CODE.
                output = solve(BASELINE_SOURCE, dataset)
            records.append(RawCandidate(
                name=name, seed=seed, source_sha256=sha256_string(source),
                sandbox_id=f'mock-{name}-{seed}', output=output,
                output_sha256=sha256_string(canonical_json(output)),
                elapsed_seconds=0.1,
            ))
        results[name] = records
    return results


def data(seeds=(42, 43, 44)):
    project = ProjectInput.model_validate(SAMPLE_PROJECT)
    return {seed: create_dataset(project.model_copy(update={'seed': seed})) for seed in seeds}


def references(dev):
    results = fake_executor(dev, {'baseline': BASELINE_SOURCE, 'optimal': OPTIMAL_SOURCE})
    return (
        candidate_from_raw('baseline', 'greedy', dev, results['baseline'], BASELINE_SOURCE),
        candidate_from_raw('optimal', 'dp', dev, results['optimal'], OPTIMAL_SOURCE),
    )


def test_quality_hold_triggers_improvement_then_early_go():
    dev = data()
    baseline, optimal = references(dev)
    feedbacks = []

    async def unexpected_functional_repair(code, feedback, n):
        raise AssertionError('quality HOLD should not call functional repair')

    async def improve(code, feedback, n):
        assert n == 1 and code == LOW_CODE
        feedbacks.append(feedback)
        assert 'QUALITY HOLD' in feedback
        assert f'{baseline.score:.6f}' in feedback
        assert '10042' not in feedback and 'held-out' in feedback.lower()
        assert 'S001' not in feedback and 'math.exp' not in feedback
        return GeneratedCode(python_code=HIGH_CODE, rationale='Better marginal utility')

    attempts, selected_raw, sources, choice = asyncio.run(execute_repair_loop(
        dev, LOW_CODE, 2, execute=fake_executor,
        repair=unexpected_functional_repair, improve=improve,
        baseline=baseline, optimal=optimal,
    ))
    assert [a.verdict for a in attempts] == ['HOLD', 'CONDITIONAL GO']
    assert [a.trigger for a in attempts] == ['quality', 'none']
    assert len(feedbacks) == 1 and len(sources) == 2
    assert choice == 1 and attempts[1].selected and len(selected_raw) == 3


def test_quality_regression_keeps_best_dev_code():
    dev = data()
    baseline, optimal = references(dev)
    # The first candidate is better than fixed Greedy but below DP, then degrades.
    async def improve(code, feedback, n):
        return GeneratedCode(python_code=WORSE_CODE, rationale='not better')

    attempts, _, sources, choice = asyncio.run(execute_repair_loop(
        dev, MEDIUM_CODE, 1, execute=fake_executor,
        repair=improve, improve=improve,
        baseline=baseline, optimal=optimal,
    ))
    assert [a.verdict for a in attempts] == ['HOLD', 'HOLD']
    assert attempts[0].candidate.score > attempts[1].candidate.score
    assert choice == 0 and attempts[0].selected
    assert sources == [MEDIUM_CODE, WORSE_CODE]


def test_api_heldout_only_after_development_and_not_in_llm_feedback(monkeypatch, tmp_path):
    monkeypatch.setenv('E2B_API_KEY', 'fake-test-key')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    calls = []
    feedbacks = []

    def traced_exec(datasets, sources):
        calls.append((list(datasets), list(sources)))
        return fake_executor(datasets, sources)

    async def improve(code, feedback, index):
        feedbacks.append(feedback)
        assert '10042' not in feedback and '10043' not in feedback
        return GeneratedCode(python_code=HIGH_CODE, rationale='utility marginal gain')

    async def unexpected_repair(*args):
        raise AssertionError('no functional repair expected')

    monkeypatch.setattr(main, 'run_in_e2b', traced_exec)
    monkeypatch.setattr(main, 'improve_code', improve)
    monkeypatch.setattr(main, 'repair_code', unexpected_repair)
    request = {'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': LOW_CODE}
    response = TestClient(main.app).post('/api/run', json=request)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['selected_attempt_index'] == 1
    assert [a['verdict'] for a in payload['repair_attempts']] == ['HOLD', 'CONDITIONAL GO']
    assert payload['functional_gate'].startswith('PASS')
    assert payload['selection_gate'].startswith('CONDITIONAL GO')
    assert len(feedbacks) == 1
    # dev refs, attempt 0, attempt 1, exactly one full holdout call.
    assert len(calls) == 4
    assert all({42, 43, 44} == set(seeds) for seeds, _ in calls[:3])
    assert calls[3] == ([10042, 10043], ['baseline', 'optimal', 'generated'])
    report = payload['report_markdown']
    assert 'Attempt 0 — 品質HOLD' in report
    assert 'HOLDOUT' in report and 'DEV' in report
    assert '学習計画の比較例' in report
    assert len(payload['plan_comparisons']) == 3
    assert all(len(p['subjects']) == 4 for p in payload['plan_comparisons'])
    folder = tmp_path / payload['run_id']
    assert (folder / 'generated.py').read_text() == HIGH_CODE
    assert (folder / 'attempts/attempt_00.py').read_text() == LOW_CODE
    assert (folder / 'attempts/attempt_01.py').read_text() == HIGH_CODE
    assert (folder / 'datasets.json').exists()
    assert '10042' not in ' '.join(feedbacks)


def test_final_holdout_no_go_is_reported_and_not_sent_back_to_model(monkeypatch, tmp_path):
    monkeypatch.setenv('E2B_API_KEY', 'fake-test-key')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    calls = []
    def executor(datasets, sources):
        calls.append(list(datasets))
        results = fake_executor(datasets, sources)
        if list(datasets) == [10042, 10043] and 'generated' in sources:
            results['generated'][0].output['plans'][0]['allocations'].append({'subject':'理科', 'hours':1})
            results['generated'][0].stderr = 'heldout-only failure'
        return results
    monkeypatch.setattr(main, 'run_in_e2b', executor)
    async def improve(code, feedback, index):
        return GeneratedCode(python_code=HIGH_CODE, rationale='improved')
    monkeypatch.setattr(main, 'improve_code', improve)
    monkeypatch.setattr(main, 'repair_code', improve)
    response = TestClient(main.app).post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': LOW_CODE,
    })
    assert response.status_code == 200
    result = response.json()
    assert result['functional_gate'].startswith('NO-GO')
    assert result['selection_gate'].startswith('NO-GO')
    assert len(calls) == 4  # no re-run or feedback using heldout failures
    report = result['report_markdown']
    assert 'FINAL HOLDOUT NO-GO' in report and 'heldout-only failure' in report
    assert result['generated']['score'] is None
    assert len(result['plan_comparisons']) >= 1


def test_plan_comparison_missing_generated_result_is_not_fabricated():
    dev = data(seeds=(42,))
    raw = fake_executor(dev, {'baseline':BASELINE_SOURCE, 'optimal':OPTIMAL_SOURCE,
                               'generated':HIGH_CODE})
    raw['generated'][0].output = {'plans': []}
    rows = build_plan_comparisons(dev,
        {42: raw['baseline'][0]}, {42:raw['optimal'][0]}, {42:raw['generated'][0]})
    assert len(rows) == 3
    assert all(not p.generated_valid for p in rows)
    assert all(s.generated_hours is None for p in rows for s in p.subjects)
