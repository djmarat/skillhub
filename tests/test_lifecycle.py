"""Tests for update/uninstall lifecycle tools."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "skillhub_mcp"))

from server import _dispatch  # noqa: E402


def _call(method, params):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = _dispatch(req)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return json.loads(resp["result"]["content"][0]["text"])


def test_install_then_uninstall(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    target = tmp_path / ".hermes" / "skills" / "exa"
    assert target.exists()
    out = _call("tools/call", {
        "name": "uninstall",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    assert out["uninstalled"] is True
    assert not target.exists()


def test_uninstall_not_present(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "uninstall", "arguments": {"name": "ghost", "runtime": "hermes"},
    }}
    resp = _dispatch(req)
    assert resp["result"]["isError"] is True


def test_update_replaces_files(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # install first
    _call("tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    out = _call("tools/call", {
        "name": "update",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    assert out["updated"] is True
    assert out["previous_install"] is True
    assert "version" in out
