"""conftest.py — shared pytest fixtures for skillhub tests.

The MCP tools touch real filesystem state (~/.skillhub/telemetry.jsonl,
~/.skillhub/profile.json, and runtime install targets). To keep tests
independent, every test runs under a sandboxed HOME.

`tmp_path_factory` is the pytest built-in that gives each test a fresh
temp dir; we set HOME to it for the duration of the test.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _sandbox_home(monkeypatch, tmp_path):
    """Run every test with HOME pointing at a temp directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    yield
