from __future__ import annotations
import itertools
import json
import math
import random
import statistics
from app.baseline import BASELINE_SOURCE
from app.optimal import OPTIMAL_SOURCE
from app.evaluator import (
    evaluate_output, normalize_plans, business_scenario, decide_gates,
    summarize_candidate, sha256_string,
)
from app.sample import SAMPLE_PROJECT, create_dataset
from app.models import CandidateResult, ProjectInput, SeedEvidence


def solve(source: str, dataset: dict):
    namespace = {'__name__': 'test_solver'}
    exec(source, namespace)
    return namespace['solve'](dataset)


def make_dataset(seed=42):
    return create_dataset(ProjectInput.model_validate({**SAMPLE_PROJECT, 'seed': seed}))


def test_dataset_determinism_and_variation():
    assert make_dataset() == make_dataset()
    assert make_dataset(42) != make_dataset(43)


def test_optimal_matches_bruteforce_on_small_instance():
    dataset = {'students': [{
        'student_id': 'S001', 'available_hours': 4,
        'subjects': [
            {'name': '数学', 'gap': 0.7, 'priority': 2, 'max_hours': 4},
            {'name': '英語', 'gap': 0.9, 'priority': 4, 'max_hours': 4},
            {'name': '国語', 'gap': 0.3, 'priority': 1, 'max_hours': 4},
        ],
    }]}
    result = solve(OPTIMAL_SOURCE, dataset)
    passed, score, _, violations, _ = evaluate_output(dataset, result)
    assert passed, violations
    weights = [s['gap'] * s['priority'] for s in dataset['students'][0]['subjects']]
    brute = max(sum(w * (1-math.exp(-h/2.5)) for w, h in zip(weights, alloc)) / sum(weights)
                for alloc in itertools.product(range(5), repeat=3) if sum(alloc) == 4)
    assert abs(score-brute) < 1e-6


def test_three_methods_have_valid_contract_and_optimal_not_worse():
    for seed in [42, 43, 44, 199]:
        data = make_dataset(seed)
        baseline = solve(BASELINE_SOURCE, data)
        exact = solve(OPTIMAL_SOURCE, data)
        bp, bs, bc, be, _ = evaluate_output(data, baseline)
        op, os, oc, oe, _ = evaluate_output(data, exact)
        assert bp and op, (be, oe)
        assert bc == oc == 1.0
        assert os >= bs - 1e-6


def test_hard_constraint_checker_rejects_invalid_data():
    data = make_dataset()
    result = solve(BASELINE_SOURCE, data)
    result['plans'][0]['allocations'][0]['hours'] = True
    passed, _, _, errors, _ = evaluate_output(data, result)
    assert not passed and errors
    result = solve(BASELINE_SOURCE, data)
    result['plans'][0]['allocations'].append(result['plans'][0]['allocations'][0])
    passed, _, _, errors, _ = evaluate_output(data, result)
    assert not passed and any('重複' in e for e in errors)
    result = solve(BASELINE_SOURCE, data)
    result['plans'].pop()
    passed, _, _, errors, _ = evaluate_output(data, result)
    assert not passed and errors


def test_plan_equality_does_not_depend_on_json_order():
    data = make_dataset()
    result = solve(BASELINE_SOURCE, data)
    copy = json.loads(json.dumps(result))
    copy['plans'].reverse()
    for p in copy['plans']:
        p['allocations'].reverse()
    assert normalize_plans(result) == normalize_plans(copy)


def seed_evidence(seed, score=0.8, passed=True):
    return SeedEvidence(
        seed=seed, dataset_sha256='x'*64, sandbox_id='mock-sandbox',
        status='completed', hard_constraint_pass=passed, score=score if passed else None,
        coverage_ratio=1.0 if passed else 0.0, elapsed_seconds=0.1,
        violations=[] if passed else ['constraint violated'],
    )


def candidate(name, score, passed=True):
    e = [seed_evidence(42, score, passed), seed_evidence(43, score, passed)]
    return summarize_candidate(name, name, e, 'a'*64)


def test_no_go_when_generated_fails_any_seed():
    baseline = candidate('baseline', 0.6)
    optimal = candidate('optimal', 0.8)
    evidence = [seed_evidence(42, 0.78), seed_evidence(43, passed=False)]
    generated = summarize_candidate('generated', 'qwen', evidence, 'b'*64)
    assert generated.score is None  # never silently average only passing seeds
    functional, selection, _ = decide_gates(baseline, optimal, generated,
                                             optimal_floor=0.98, improvement_floor=1.01)
    assert 'NO-GO' in functional and 'NO-GO' in selection


def test_hold_when_candidate_equals_baseline():
    functional, selection, reasons = decide_gates(
        candidate('baseline', 0.6), candidate('optimal', 0.7), candidate('generated', 0.6),
        optimal_floor=0.8, improvement_floor=1.01,
    )
    assert 'PASS' in functional and 'HOLD' in selection
    assert '改善' in ' '.join(reasons)


def test_hold_when_optimality_gap_is_large():
    _, selection, _ = decide_gates(candidate('baseline', 0.5), candidate('optimal', 0.9),
                                   candidate('generated', 0.6), optimal_floor=0.98,
                                   improvement_floor=1.01)
    assert 'HOLD' in selection


def test_conditional_go_never_claims_market_validation():
    functional, selection, reasons = decide_gates(candidate('baseline', 0.6),
                                                  candidate('optimal', 0.8),
                                                  candidate('generated', 0.8),
                                                  optimal_floor=0.98, improvement_floor=1.01)
    assert 'PASS' in functional and 'CONDITIONAL GO' in selection
    assert any('未検証' in r for r in reasons)


def test_business_scenario_label_is_hypothetical():
    scenario = business_scenario(ProjectInput.model_validate(SAMPLE_PROJECT).business)
    assert scenario.break_even_schools == 15
    assert scenario.monthly_revenue_yen == 360000
    assert '未検証' in scenario.validation_status
