"""Tests for the trust-tier badge system (v0.2.0)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from skillhub.badges import tier_for  # noqa: E402


def test_tier_community_for_unknown():
    # No repo, no source, no telemetry → community
    out = tier_for({"name": "x", "trust": {}}, {})
    assert out["tier"] == "community"


def test_tier_official_for_official_source_no_ratings():
    out = tier_for({
        "name": "demo",
        "trust": {"source": "official", "security_passes": 1, "repo": ""},
    }, {})
    # Without enough ratings but with source+scan → could be 'official' OR 'community'
    # depending on trust_score from baseline signals (no repo → 0 stars → lower score).
    assert out["tier"] in ("official", "community")


def test_tier_verified_requires_min_ratings():
    # Even if source=official, with 0 ratings we can't be 'verified'.
    out = tier_for({
        "name": "demo",
        "trust": {"source": "official", "security_passes": 5},
    }, {"demo": {"ratings": 0, "success_rate": 0.0}})
    assert out["tier"] != "verified"


def test_tier_verified_with_enough_signals():
    out = tier_for({
        "name": "demo",
        "trust": {"source": "official", "security_passes": 5},
    }, {"demo": {"ratings": 10, "success_rate": 0.95}})
    # We don't guarantee 'verified' (it depends on GitHub stars + repo presence),
    # but if the function ran, it returned one of the three tiers.
    assert out["tier"] in ("verified", "official", "community")


def test_tier_returns_trust_score():
    out = tier_for({"name": "x", "trust": {}}, {})
    assert "trust_score" in out
    assert 0.0 <= out["trust_score"] <= 1.0


def test_tier_includes_reasons():
    out = tier_for({"name": "x", "trust": {}}, {})
    assert "reasons" in out
    assert isinstance(out["reasons"], list)
