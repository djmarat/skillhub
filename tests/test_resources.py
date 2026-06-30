"""Tests for MCP resources (v0.2.0).

The MCP server exposes install/profile/stats as resources that agents
can discover on initialize without an explicit tool call. Verifies the
shape and contents of each resource URI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "skillhub_mcp"))

from server import _dispatch, _list_resources, _read_resource  # noqa: E402


def _call(method, params=None):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    resp = _dispatch(req)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return resp["result"]


def test_initialize_advertises_resources_capability():
    req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-06-18",
        "clientInfo": {"name": "t", "version": "0"},
        "capabilities": {},
    }}
    resp = _dispatch(req)
    caps = resp["result"]["capabilities"]
    assert "resources" in caps
    assert "tools" in caps


def test_resources_list_has_static_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("resources/list")
    uris = [r["uri"] for r in out["resources"]]
    assert "skillhub://profile" in uris
    assert "skillhub://skills" in uris
    # no installs yet → no per-skill resources
    skill_uris = [u for u in uris if u.startswith("skillhub://skills/")]
    assert skill_uris == []


def test_resources_list_grows_after_install(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {"name": "install", "arguments": {"name": "exa", "runtime": "hermes"}})
    out = _call("resources/list")
    uris = [r["uri"] for r in out["resources"]]
    assert "skillhub://skills/exa" in uris


def test_read_resource_profile(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {"name": "install", "arguments": {"name": "exa", "runtime": "hermes"}})
    out = _call("resources/read", {"uri": "skillhub://profile"})
    text = out["contents"][0]["text"]
    data = json.loads(text)
    assert "exa" in data["installed"]


def test_read_resource_skill_manifest(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {"name": "install", "arguments": {"name": "exa", "runtime": "hermes"}})
    out = _call("resources/read", {"uri": "skillhub://skills/exa"})
    data = json.loads(out["contents"][0]["text"])
    assert data["name"] == "exa"
    assert "entry" in data
    assert "trust" in data


def test_read_resource_skill_not_in_registry(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("resources/read", {"uri": "skillhub://skills/no-such-skill"})
    data = json.loads(out["contents"][0]["text"])
    assert "error" in data


def test_read_resource_stats_template(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # record a fake rate
    _call("tools/call", {
        "name": "rate",
        "arguments": {"name": "tavily", "success": True, "latency_ms": 100},
    })
    out = _call("resources/read", {"uri": "skillhub://stats/tavily"})
    data = json.loads(out["contents"][0]["text"])
    assert data["name"] == "tavily"
    assert data["rates"] >= 1


def test_resources_templates_list_exposes_stats(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("resources/templates/list")
    templates = out.get("resourceTemplates", [])
    assert any(t["uriTemplate"] == "skillhub://stats/{name}" for t in templates)


def test_read_resource_skill_index(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {"name": "install", "arguments": {"name": "exa", "runtime": "hermes"}})
    _call("tools/call", {"name": "install", "arguments": {"name": "tavily", "runtime": "hermes"}})
    out = _call("resources/read", {"uri": "skillhub://skills"})
    arr = json.loads(out["contents"][0]["text"])
    names = sorted(x["name"] for x in arr)
    assert names == ["exa", "tavily"]
    # trust_score is included
    assert all("trust_score" in x for x in arr)


def test_resource_read_missing_uri_is_error():
    """Without uri param the server should return a JSON-RPC error."""
    req = {"jsonrpc": "2.0", "id": 1, "method": "resources/read", "params": {}}
    resp = _dispatch(req)
    assert "error" in resp
    assert resp["error"]["code"] == -32602


# Direct-helper tests (don't go through JSON-RPC; useful for debugging)
def test_list_resources_helper():
    resources = _list_resources()
    assert isinstance(resources, list)
    assert any(r["uri"] == "skillhub://profile" for r in resources)


def test_read_resource_unknown_uri_returns_error_json():
    raw = _read_resource("skillhub://nope")
    data = json.loads(raw)
    assert "error" in data
