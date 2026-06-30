"""badges.py — Trust tier system (v0.2.0).

Three tiers instead of one number:

- verified:  at least N independent successful rates, scan_pass=1,
             source=official, trust_score >= 0.7
- official:  trust_score >= 0.5, source=official, scan_pass=1
- community: anything else in the registry

Output is a dict the agent can include in tool responses.
"""

from __future__ import annotations

from typing import Any

from skillhub.trust import fetch_github_signals, Signals  # noqa: E402
import skillhub.trust as _trust_mod


TIERS = ("verified", "official", "community")


# Tunable thresholds (lift these as the marketplace matures)
VERIFIED_MIN_RATINGS = 3
VERIFIED_MIN_SUCCESS_RATE = 0.8
VERIFIED_MIN_TRUST = 0.7
OFFICIAL_MIN_TRUST = 0.5


def compute_community_metrics() -> dict[str, dict[str, Any]]:
    """Read community telemetry once and return per-skill aggregates.

    Returns: {name: {ratings: int, success_rate: float, latency_ms_p50: int|None}}
    """
    from skillhub.telemetry import stats as tstats
    out: dict[str, dict[str, Any]] = {}
    # We can only know what's in the local telemetry log; get all distinct names
    # by aggregating over the registry.
    from skillhub.cli import load_registry
    for s in load_registry():
        agg = tstats(s.name, window_days=30)
        out[s.name] = {
            "ratings": agg.get("rates", 0),
            "success_rate": agg.get("success_rate"),
            "latency_p50": (agg.get("latency_ms") or {}).get("p50"),
        }
    return out


def tier_for(skill: dict, community: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Return {"tier": "verified|official|community", "reason": str,
              "trust_score": float} for one skill."""
    name = skill.get("name", "")
    repo = (skill.get("trust") or {}).get("repo", "")
    source = (skill.get("trust") or {}).get("source", "community")
    scan_passes = (skill.get("trust") or {}).get("security_passes", 0)
    if repo and "/" in repo and not repo.startswith("skillhub/"):
        signals = fetch_github_signals(repo)
    else:
        signals = Signals(stars=0, recency_days=9999, has_repo=bool(repo))
    score = _trust_mod.compute_trust_score(skill, signals, scan_passes)
    metrics = community.get(name, {})
    ratings = metrics.get("ratings", 0)
    success_rate = metrics.get("success_rate")

    reasons: list[str] = []
    if (
        ratings >= VERIFIED_MIN_RATINGS
        and success_rate is not None
        and success_rate >= VERIFIED_MIN_SUCCESS_RATE
        and scan_passes >= 1
        and source in ("official", "github")
        and score >= VERIFIED_MIN_TRUST
    ):
        reasons.append(f"{ratings} ratings @ {success_rate:.0%} success")
        if signals.has_repo:
            reasons.append(f"GitHub stars: {signals.stars}")
        return {"tier": "verified", "reasons": reasons, "trust_score": round(score, 3)}

    if (
        source in ("official", "github")
        and scan_passes >= 1
        and score >= OFFICIAL_MIN_TRUST
    ):
        reasons.append(f"source={source}")
        reasons.append(f"scan_passes={scan_passes}")
        reasons.append(f"trust_score={score:.2f}")
        return {"tier": "official", "reasons": reasons, "trust_score": round(score, 3)}

    reasons.append("not enough signals yet")
    return {"tier": "community", "reasons": reasons, "trust_score": round(score, 3)}
