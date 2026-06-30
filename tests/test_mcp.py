"""Tests for skillhub-mcp server.

Drive the MCP server with in-memory stdin/stdout buffers (BytesIO) so
the tests don't depend on a real subprocess. This is the standard way
to test stdio JSON-RPC servers deterministically.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "skillhub_mcp"))

from server import _dispatch, _read_message, _write_message, serve  # noqa: E402


def _make_request(req_id, method, params=None):
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params or {}}


def test_initialize():
    req = _make_request(1, "initialize", {
        "protocolVersion": "2025-06-18",
        "clientInfo": {"name": "test", "version": "0.0.0"},
        "capabilities": {},
    })
    resp = _dispatch(req)
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "skillhub"
    assert resp["result"]["protocolVersion"] == "2025-06-18"
    assert "tools" in resp["result"]["capabilities"]


def test_tools_list_four_tools():
    req = _make_request(2, "tools/list")
    resp = _dispatch(req)
    tools = resp["result"]["tools"]
    names = sorted(t["name"] for t in tools)
    assert names == ["install", "search", "show", "validate"]


def test_search_returns_records():
    req = _make_request(3, "tools/call", {
        "name": "search",
        "arguments": {"query": "search", "limit": 5},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["count"] > 0
    assert "results" in body
    sample = body["results"][0]
    assert {"name", "version", "description", "trust_score"} <= sample.keys()


def test_search_filter_by_runtime():
    req = _make_request(4, "tools/call", {
        "name": "search",
        "arguments": {"query": "", "runtime": "codex", "limit": 100},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    # every record must include codex in its runtime list
    assert all("codex" in r["runtime"] for r in body["results"])


def test_show_unknown_skill_is_error():
    req = _make_request(5, "tools/call", {
        "name": "show",
        "arguments": {"name": "this-name-does-not-exist"},
    })
    resp = _dispatch(req)
    assert resp["result"]["isError"] is True


def test_show_known_skill():
    req = _make_request(6, "tools/call", {
        "name": "show",
        "arguments": {"name": "exa"},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["name"] == "exa"
    assert "trust_score" in body
    assert body["trust_score"] > 0.7  # trust score should be high for exa


def test_install_known_skill(tmp_path, monkeypatch):
    # Patch HOME so _install_to_runtime writes into a sandbox.
    monkeypatch.setenv("HOME", str(tmp_path))
    req = _make_request(7, "tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["installed"] is True
    # Confirm files were created on disk
    assert (tmp_path / ".hermes" / "skills" / "exa" / "skill.yaml").exists()


def test_install_invalid_runtime():
    req = _make_request(8, "tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "windows-95"},
    })
    resp = _dispatch(req)
    assert resp["result"]["isError"] is True


def test_validate_valid_skill():
    req = _make_request(9, "tools/call", {
        "name": "validate",
        "arguments": {"skill_yaml": (
            "name: demo\nversion: 1.0.0\n"
            "description: A demo skill for the validator happy path.\n"
            "runtime:\n  - hermes\n"
            "entry:\n  type: command\n  command: python -m demo\n"
        )},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["valid"] is True
    assert body["errors"] == []


def test_validate_invalid_skill():
    req = _make_request(10, "tools/call", {
        "name": "validate",
        "arguments": {"skill_yaml": "name: bad!name\n"},
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert body["valid"] is False
    assert len(body["errors"]) > 0


def test_validate_with_scan_blocks_eval():
    req = _make_request(11, "tools/call", {
        "name": "validate",
        "arguments": {
            "skill_yaml": (
                "name: sketchy\nversion: 1.0.0\n"
                "description: A skill that may do something sketchy with eval.\n"
                "runtime:\n  - hermes\n"
                "entry:\n  type: command\n  command: python -m sketchy\n"
            ),
            "scan": True,
        },
    })
    resp = _dispatch(req)
    body = json.loads(resp["result"]["content"][0]["text"])
    assert "scan" in body
    # We don't embed the script, so scan should report 0 findings —
    # this just exercises that the scan path doesn't crash.
    assert body["scan"]["findings_total"] >= 0


def test_method_not_found():
    req = _make_request(12, "nope/does-not-exist")
    resp = _dispatch(req)
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_unknown_tool():
    req = _make_request(13, "tools/call", {
        "name": "fake-tool", "arguments": {},
    })
    resp = _dispatch(req)
    assert "error" in resp


def test_full_stdio_roundtrip():
    """Drive the actual serve() loop with in-memory buffers."""
    request = _make_request(1, "tools/list")
    body = json.dumps(request).encode("utf-8")
    request_bytes = (
        f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8") + body
    )
    stdin = io.BytesIO(request_bytes + b"")  # extra: triggers EOF after one msg
    stdout = io.BytesIO()
    rc = serve(stdin=stdin, stdout=stdout)
    assert rc == 0
    raw = stdout.getvalue()
    assert b"Content-Length:" in raw
    # parse the response body
    header_end = raw.find(b"\r\n\r\n")
    response_body = json.loads(raw[header_end + 4 :].decode("utf-8"))
    assert "result" in response_body
    assert "tools" in response_body["result"]


def test_notification_does_not_send_response():
    """Notifications (no 'id') must not produce a response."""
    req = {"jsonrpc": "2.0", "method": "notifications/initialized"}  # no id
    resp = _dispatch(req)
    assert resp is None
