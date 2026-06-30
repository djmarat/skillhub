"""Tests for trust scoring."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from skillhub.trust import (
    Signals,
    compute_trust_score,
    refresh_trust,
    fetch_github_signals,
)


def test_signals_stars_zero():
    s = Signals(stars=0)
    assert s.stars_score == 0.0


def test_signals_stars_log_scale():
    s1 = Signals(stars=10)
    s2 = Signals(stars=100)
    s3 = Signals(stars=1000)
    assert s1.stars_score < s2.stars_score < s3.stars_score <= 1.0


def test_signals_recency_fresh():
    s = Signals(recency_days=0)
    assert s.recency_score == 1.0


def test_signals_recency_old():
    s = Signals(recency_days=500)
    assert s.recency_score == 0.0


def test_trust_score_with_real_signals():
    skill = {
        "name": "demo",
        "trust": {"source": "official", "security_passes": 2},
    }
    signals = Signals(stars=500, recency_days=10, has_repo=True)
    score = compute_trust_score(skill, signals, scan_passes=2)
    assert 0.7 < score <= 1.0


def test_trust_score_low_quality():
    skill = {
        "name": "demo",
        "trust": {"source": "community", "security_passes": 0},
    }
    signals = Signals(stars=0, recency_days=9999, has_repo=False)
    score = compute_trust_score(skill, signals, scan_passes=0)
    assert score < 0.2


def test_fetch_github_signals_handles_invalid_repo():
    s = fetch_github_signals("nonexistent/repo-xyz-12345")
    assert s.stars == 0
    assert s.recency_days == 9999
    assert s.has_repo is False
