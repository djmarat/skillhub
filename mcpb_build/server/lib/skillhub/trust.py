"""trust.py — Trust Score v0.2.

Real signals, not placeholders:

- GitHub stars (when trust.repo is owner/repo)
- Recency (updated_at from GitHub)
- Source flag (official > github > community)
- Security scan passes (already in skill)

Result: float in [0, 1], cached in registry/trust.json (TTL 6h).
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY = ROOT / "registry" / "skills.jsonl"
CACHE = ROOT / "registry" / "trust.json"
TTL = 6 * 3600


@dataclass
class Signals:
    stars: int = 0
    recency_days: int = 9999
    has_repo: bool = False

    @property
    def stars_score(self) -> float:
        # log scale: 0 stars -> 0.0, 100 -> 0.5, 1000 -> 0.83, 10000 -> 1.0
        if self.stars <= 0:
            return 0.0
        import math
        return min(1.0, math.log10(self.stars + 1) / 4.0)

    @property
    def recency_score(self) -> float:
        # 0 days = 1.0, 365+ days = 0.0
        if self.recency_days >= 365:
            return 0.0
        return max(0.0, 1.0 - self.recency_days / 365.0)

    @property
    def repo_score(self) -> float:
        return 1.0 if self.has_repo else 0.0


def _gh_api(path: str) -> dict | None:
    """Call GitHub API via `gh api` (auth already configured)."""
    try:
        out = subprocess.run(
            ["gh", "api", path, "--jq", "."],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
        return json.loads(out.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def fetch_github_signals(repo: str) -> Signals:
    """Fetch stars + recency from GitHub for owner/repo."""
    data = _gh_api(f"repos/{repo}")
    if data is None:
        return Signals()
    stars = data.get("stargazers_count", 0)
    updated_at = data.get("updated_at") or data.get("pushed_at") or ""
    recency_days = 9999
    if updated_at:
        try:
            from datetime import datetime, timezone
            t = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            recency_days = (datetime.now(timezone.utc) - t).days
        except Exception:
            pass
    return Signals(stars=stars, recency_days=recency_days, has_repo=True)


def compute_trust_score(skill: dict, signals: Signals, scan_passes: int) -> float:
    """Weighted average. Weights sum to 1.0."""
    score = 0.0
    score += 0.45 * signals.stars_score
    score += 0.25 * signals.recency_score
    score += 0.10 * signals.repo_score
    if skill.get("trust", {}).get("source") == "official":
        score += 0.10
    elif skill.get("trust", {}).get("source") == "github":
        score += 0.05
    # scan passes: full credit at >=2 passes
    score += 0.05 * min(scan_passes / 2.0, 1.0)
    score += 0.05  # base floor
    return min(1.0, max(0.0, score))


def load_cache() -> dict:
    if not CACHE.exists():
        return {}
    try:
        return json.loads(CACHE.read_text())
    except json.JSONDecodeError:
        return {}


def save_cache(cache: dict) -> None:
    CACHE.write_text(json.dumps(cache, indent=2))


def refresh_trust() -> dict[str, float]:
    """Refresh trust.json, fetching GitHub data only for expired entries.

    Returns: name -> trust_score mapping.
    """
    if not REGISTRY.exists():
        return {}
    skills: list[dict] = []
    with REGISTRY.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                skills.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    cache = load_cache()
    now = time.time()

    out: dict[str, float] = {}
    new_entries = 0
    for s in skills:
        name = s.get("name", "")
        if not name:
            continue
        entry = cache.get(name)
        if entry and now - entry.get("cached_at", 0) < TTL:
            out[name] = entry.get("score", 0.0)
            continue

        repo = s.get("trust", {}).get("repo", "")
        signals = Signals()
        if repo and "/" in repo and not repo.startswith("skillhub/"):
            signals = fetch_github_signals(repo)
        scan_passes = s.get("trust", {}).get("security_passes", 0)
        score = compute_trust_score(s, signals, scan_passes)
        cache[name] = {
            "score": score,
            "stars": signals.stars,
            "recency_days": signals.recency_days,
            "cached_at": now,
        }
        out[name] = score
        new_entries += 1

    save_cache(cache)
    return out


if __name__ == "__main__":
    print(json.dumps(refresh_trust(), indent=2))
