"""Legacy v0.8–v0.23 tests use the explicit, labelled offline Dogwood bypass.

The v0.24 Dogwood-specific tests override DOGWOOD_MODE=enforce and inject a
subprocess fixture. Real Rust compilation and CLI policy tests run inside the
backend Docker image build, not this Python-only CI environment.
"""
import pytest


@pytest.fixture(autouse=True)
def offline_legacy_dogwood_mode(monkeypatch):
    monkeypatch.setenv("DOGWOOD_MODE", "off")
