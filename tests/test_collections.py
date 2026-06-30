"""Tests for collections / bundles (v0.2.0)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "src" / "skillhub_mcp"))

from server import _dispatch  # noqa: E402
from skillhub.collections import (  # noqa: E402
    list_collections,
    get as coll_get,
    recommend_for_installed,
)


def _call(method, params):
    req = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = _dispatch(req)
    if "error" in resp:
        raise RuntimeError(resp["error"])
    return json.loads(resp["result"]["content"][0]["text"])


def test_collections_lists_all_known_bundles():
    cols = list_collections()
    titles = [c["title"] for c in cols]
    assert "AI Researcher Pack" in titles
    assert "PDF & Document Pack" in titles


def test_collections_each_has_skills():
    for c in list_collections():
        assert c["skills_count"] >= 1
        assert c["skills"]


def test_collection_by_id_returns_full_details():
    data = _call("tools/call", {
        "name": "collection",
        "arguments": {"id": "ai-researcher"},
    })
    assert data["id"] == "ai-researcher"
    assert data["title"] == "AI Researcher Pack"
    assert "rationale" in data
    assert isinstance(data["members"], list)
    assert all("trust_score" in m for m in data["members"])


def test_collection_unknown_id_errors():
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "collection", "arguments": {"id": "no-such-bundle"},
    }}
    resp = _dispatch(req)
    assert resp["result"]["isError"] is True


def test_collections_tool_returns_list():
    out = _call("tools/call", {"name": "collections", "arguments": {}})
    assert out["count"] >= 1
    assert isinstance(out["collections"], list)


def test_recommend_for_installed_finds_partial(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # Install 3 of the 5 in ai-researcher
    for n in ["exa", "tavily", "arxiv-search"]:
        _call("tools/call", {
            "name": "install", "arguments": {"name": n, "runtime": "hermes"},
        })
    out = _call("tools/call", {"name": "bundle_suggest", "arguments": {}})
    assert out["count"] >= 1
    titles = [s["title"] for s in out["suggestions"]]
    assert "AI Researcher Pack" in titles
    rs = next(s for s in out["suggestions"] if s["title"] == "AI Researcher Pack")
    assert rs["completion"] >= 0.4
    # remaining members are those not yet installed
    assert "context7" in rs["skills_remaining"] or "huggingface-hub" in rs["skills_remaining"]


def test_bundle_install_skip_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    # install exa first
    _call("tools/call", {
        "name": "install", "arguments": {"name": "exa", "runtime": "hermes"},
    })
    out = _call("tools/call", {
        "name": "bundle_install",
        "arguments": {"id": "pdf-document", "runtime": "hermes", "skip_existing": True},
    })
    # pdf-document has only pdf-md and image-ocr, neither pre-installed
    statuses = [r["status"] for r in out["results"]]
    assert "installed" in statuses
    # no skipped if pdf-md/image-ocr aren't there
    # Note: this collection's skills might not all be in our 254-set.


def test_bundle_install_unknown_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    req = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
        "name": "bundle_install",
        "arguments": {"id": "ghost-bundle", "runtime": "hermes"},
    }}
    resp = _dispatch(req)
    assert resp["result"]["isError"] is True
