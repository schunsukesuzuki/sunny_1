"""Regression tests for the actual observed all-NO-GO and repeated-state bugs."""
from __future__ import annotations

import asyncio
import ast

import pytest
from fastapi.testclient import TestClient
from app import main
from app.diagnostics import code_diff, error_summary, static_hints
from app.models import GeneratedCode
from app.patcher import replace_function
from app.repair_loop import make_feedback, execute_repair_loop
from test_repair_loop import BROKEN_SOURCE, FIXED_SOURCE, REQ, make_fake_executor, sample_datasets
from app.sample import SAMPLE_PROJECT


SOURCE = '''import json

def allocate_hours(student, available_hours):
    allocations=[]
    while available_hours > 0:
        allocations.append({'subject': '数学', 'hours': 1})
        student['subjects'][0]['max_hours'] -= 1
        available_hours -= 1
    return allocations

def main():
    return 'leave me intact'
'''
PATCH = '''def allocate_hours(student, available_hours):
    allocated = {s['name']: 0 for s in student['subjects']}
    for _ in range(available_hours):
        name = student['subjects'][0]['name']
        allocated[name] += 1
    return [{'subject':s['name'], 'hours':allocated[s['name']]} for s in student['subjects']]
'''


def test_scoped_patch_preserves_main_and_other_code():
    updated = replace_function(SOURCE, PATCH)
    ast.parse(updated)
    assert "return 'leave me intact'" in updated
    assert "student['subjects'][0]['max_hours'] -= 1" not in updated
    assert "allocated = {" in updated
    assert updated.startswith('import json')


def test_malformed_or_unsafe_patch_rejected():
    with pytest.raises(ValueError):
        replace_function(SOURCE, PATCH + '\nimport os\n')
    with pytest.raises(ValueError):
        replace_function(SOURCE, 'def other(student, available_hours):\n    return []\n')
    with pytest.raises(ValueError):
        replace_function('x=1\n', PATCH)


def test_static_hints_are_explicitly_heuristic_and_diff_kept():
    hints = static_hints(SOURCE)
    assert any('allocations.append' in x for x in hints)
    assert any('max_hours' in x for x in hints)
    diff = code_diff(SOURCE, replace_function(SOURCE, PATCH))
    assert 'previous.py' in diff and 'revision.py' in diff


def test_staged_feedback_escalates_but_is_dev_only():
    executor, _ = make_fake_executor(always_fail=True)
    async def repair(source, feedback, index):
        return GeneratedCode(python_code=FIXED_SOURCE + f'\n# change {index}', rationale='fix')
    attempts, _, _, selected = asyncio.run(execute_repair_loop(
        sample_datasets(), BROKEN_SOURCE, 2, execute=executor, repair=repair,
    ))
    assert selected is None
    assert attempts[0].error_summary.get('DUPLICATE_OR_UNKNOWN_SUBJECT', 0) > 0
    assert 'SECOND-STAGE' not in attempts[0].feedback
    assert 'SECOND-STAGE' in attempts[1].feedback
    assert 'allocated_hours' in attempts[1].feedback
    assert '10042' not in attempts[0].feedback + attempts[1].feedback
    assert attempts[1].code_diff
    assert attempts[2].repair_strategy == 'invariant_guided_function_patch'


def test_no_valid_candidate_skips_all_holdout_calls(monkeypatch, tmp_path):
    calls = []
    fake, _ = make_fake_executor(always_fail=True)
    def checked_exec(datasets, sources):
        assert all(seed < 1000 for seed in datasets), 'HOLDOUT MUST NOT RUN'
        calls.append((tuple(datasets), tuple(sources)))
        return fake(datasets, sources)
    async def repair(code, feedback, index):
        return GeneratedCode(python_code=FIXED_SOURCE + f'\n# change {index}', rationale='fix')
    monkeypatch.setenv('E2B_API_KEY', 'mock')
    monkeypatch.setattr(main, 'ARTIFACT_DIR', tmp_path)
    monkeypatch.setattr(main, 'run_in_e2b', checked_exec)
    monkeypatch.setattr(main, 'repair_code', repair)
    response = TestClient(main.app).post('/api/run', json={
        'project': SAMPLE_PROJECT, 'requirements': REQ, 'code': BROKEN_SOURCE,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['selected_attempt_index'] is None
    assert data['holdout_executed'] is False
    assert data['generated'] is None
    assert len(calls) == 4
    assert len(data['repair_attempts']) == 3
    assert all(not a['selected'] for a in data['repair_attempts'])
    assert 'HOLDOUT未実行' in data['report_markdown']
    assert not (tmp_path / data['run_id'] / 'generated.py').exists()
    assert (tmp_path / data['run_id'] / 'attempts/attempt_02.diff').is_file()


def test_real_repair_adapter_requests_scoped_patch_on_second_retry(monkeypatch):
    """Exercise the actual Qwen adapter boundary without contacting Ollama."""
    from app import ollama_client
    seen = []

    async def fake_ask_json(*, system, user, schema):
        seen.append((system, user))
        return {'python_code': PATCH, 'rationale': '関数のみ変更'}

    monkeypatch.setattr(ollama_client, 'ask_json', fake_ask_json)
    result = asyncio.run(ollama_client.repair_code(SOURCE, 'DUPLICATE_SUBJECT', 2))
    assert 'allocate_hours' in result.python_code
    assert 'return \'leave me intact\'' in result.python_code
    assert 'function' in seen[0][0].lower()
    assert 'DUPLICATE_SUBJECT' in seen[0][1]
    assert 'student[\'subjects\'][0][\'max_hours\'] -= 1' not in result.python_code


def test_real_repair_adapter_rejects_invalid_scoped_response(monkeypatch):
    from app import ollama_client
    async def fake_ask_json(*, system, user, schema):
        return {'python_code': SOURCE, 'rationale': 'not a function patch'}
    monkeypatch.setattr(ollama_client, 'ask_json', fake_ask_json)
    with pytest.raises(ValueError, match='Patch must contain only'):
        asyncio.run(ollama_client.repair_code(SOURCE, 'errors', 2))
