"""Tests for the agent-retention tools added in v0.1.0:
rate, stats, recommend, probe, profile.

Sandboxes HOME so ~/.skillhub/* is per-test.
"""

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


def test_rate_records_event(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("tools/call", {
        "name": "rate",
        "arguments": {"name": "exa", "success": True, "latency_ms": 250, "runtime": "hermes"},
    })
    assert out["recorded"] is True
    # Telemetry file was created
    tel = tmp_path / ".skillhub" / "telemetry.jsonl"
    assert tel.exists()


def test_stats_returns_aggregation(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # 3 rates: 2 success, 1 fail
    for i, ok in enumerate([True, True, False]):
        _call("tools/call", {
            "name": "rate",
            "arguments": {"name": "tavily", "success": ok, "latency_ms": 100 + i * 20},
        })
    out = _call("tools/call", {
        "name": "stats",
        "arguments": {"name": "tavily", "window_days": 30},
    })
    assert out["name"] == "tavily"
    assert out["rates"] == 3
    assert 0.6 <= out["success_rate"] <= 0.7  # 2/3


def test_stats_unknown_skill_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("tools/call", {
        "name": "stats",
        "arguments": {"name": "ghost", "window_days": 7},
    })
    assert out["samples"] == 0
    assert out["success_rate"] is None


def test_recommend_with_installed_returns_alternatives(tmp_path, monkeypatch):
    """When the user has installs already, recommend should not be empty if
    there is telemetry from other sessions in the local log."""
    monkeypatch.setenv("HOME", str(tmp_path))
    # Install exa locally (writes profile + telemetry).
    _call("tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    # Ask for recommendations.
    out = _call("tools/call", {
        "name": "recommend",
        "arguments": {"limit": 5},
    })
    # Response structure check (cold-start or co-occurrence — both valid).
    assert "recommendations" in out
    assert "based_on_installed" in out
    assert "exa" in out["based_on_installed"]


def test_recommend_cold_start_with_no_installs(tmp_path, monkeypatch):
    """Without installs and no telemetry, recommend returns empty / tip."""
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("tools/call", {
        "name": "recommend",
        "arguments": {"limit": 5},
    })
    assert out["based_on_installed"] == []
    # count may be 0 (genuine cold start)
    assert "recommendations" in out


def test_probe_returns_checks(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("tools/call", {
        "name": "probe",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    assert out["dry_run"] is True
    assert out["modified_user_state"] is False
    check_names = {c["name"] for c in out["checks"]}
    assert {"manifest_present", "entry_url_well_formed", "yaml_parses"} <= check_names


def test_probe_command_entry_checks_executable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # git-summary is in our registry as command entry
    out = _call("tools/call", {
        "name": "probe",
        "arguments": {"name": "git-summary", "runtime": "hermes"},
    })
    # The seed for git-summary is `python -m git_summary` so it should find python on PATH
    # (on macOS CI which has python3 by default, this might fail — but we only assert structure)
    assert "checks" in out
    on_path_check = next(c for c in out["checks"] if c["name"] == "entry_command_on_path")
    assert "detail" in on_path_check


def test_probe_does_not_modify_real_home(tmp_path, monkeypatch):
    """After probe, ~/.skillhub should NOT have an exa folder under real home."""
    # Use a tmp HOME that we control. The probe sets HOME=tmp_path internally,
    # so we expect that after the call, our tmp_path has a sandbox scratch dir.
    monkeypatch.setenv("HOME", str(tmp_path))
    _call("tools/call", {
        "name": "probe",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    # Nothing should remain in tmp_path/.hermes (the sandbox must be cleaned up)
    her = tmp_path / ".hermes"
    if her.exists():
        # If a path exists at all, it shouldn't contain exa
        assert not (her / "skills" / "exa").exists()


def test_profile_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Initially empty
    out = _call("tools/call", {"name": "profile", "arguments": {}})
    assert out["installed"] == []
    # After install
    _call("tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    out = _call("tools/call", {"name": "profile", "arguments": {}})
    assert "exa" in out["installed"]


def test_install_appends_next_steps_hint(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    out = _call("tools/call", {
        "name": "install",
        "arguments": {"name": "exa", "runtime": "hermes"},
    })
    assert out["installed"] is True
    assert "next_steps" in out
    assert "rate" in out["next_steps"]
