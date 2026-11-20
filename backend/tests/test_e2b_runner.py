"""SDK mocking tests: ZERO actual E2B credits used."""
from __future__ import annotations
import json
import sys
from types import SimpleNamespace
from app.e2b_runner import run_in_e2b


def test_e2b_separates_approaches_and_resets_input_per_seed(monkeypatch):
    monkeypatch.setenv('E2B_API_KEY', 'fake-key')
    events = []
    class FakeFiles:
        def __init__(self):
            self.store = {}
        def write(self, path, content):
            events.append(('write', path))
            self.store[path] = content
        def read(self, path):
            events.append(('read', path))
            return self.store[path]
    class FakeSandbox:
        count = 0
        def __init__(self):
            self.files = FakeFiles()
            self.sandbox_id = f'mock-{FakeSandbox.count}'
            self.commands = self
        @classmethod
        def create(cls, **kwargs):
            assert kwargs['api_key'] == 'fake-key'
            assert kwargs['allow_internet_access'] is False
            assert kwargs['timeout'] > 0
            cls.count += 1
            events.append(('open', cls.count))
            return cls()
        def __enter__(self):
            return self
        def __exit__(self, *args):
            events.append(('close', self.sandbox_id))
        def run(self, command, timeout):
            assert command == 'rm -f /home/user/output.json && python /home/user/solver.py'
            assert timeout > 0
            data = json.loads(self.files.store['/home/user/input.json'])
            self.files.store['/home/user/output.json'] = json.dumps({'plans': data['plans']})
            events.append(('command', self.sandbox_id))
            return SimpleNamespace(stdout='', stderr='', exit_code=0)
    monkeypatch.setitem(sys.modules, 'e2b', SimpleNamespace(Sandbox=FakeSandbox))
    datasets = {42: {'plans': [42]}, 43: {'plans': [43]}}
    sources = {'baseline': 'print(1)', 'optimal': 'print(2)', 'generated': 'print(3)'}
    result = run_in_e2b(datasets, sources)
    assert set(result) == set(sources)
    assert FakeSandbox.count == 3
    for name, rows in result.items():
        assert len(rows) == 2
        assert [row.seed for row in rows] == [42, 43]
        assert rows[0].sandbox_id == rows[1].sandbox_id
        assert rows[0].output == {'plans': [42]}
        assert rows[1].output == {'plans': [43]}
    assert events.count(('write', '/home/user/input.json')) == 6
    assert len([e for e in events if e[0] == 'close']) == 3


def test_compose_avoids_port_8000_conflict():
    from pathlib import Path
    compose = (Path(__file__).resolve().parents[2] / 'compose.yaml').read_text()
    assert '127.0.0.1:${API_PORT:-18000}:8000' in compose
    assert '127.0.0.1:${WEB_PORT:-5173}:5173' in compose
