"""telemetry.py — usage signals from agents.

Stores opt-in anonymized install+rate events in ~/.skillhub/telemetry.jsonl.
A single line per event:
  {"ts": 1234567890, "event": "install|rate", "name": "exa",
   "runtime": "hermes", "success": true, "latency_ms": 412,
   "session_hash": "ab12..."}

stats(name) aggregates:
  - last 7 days success_rate (default: own data only)
  - last 7 days p50/p95 latency
  - top raters / most-installed-with

recommend(context) uses co-install stats: if you have exa + tavily installed,
and arxiv-search is in 80% of users with both, recommend arxiv-search.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Optional

HOME = Path(os.path.expanduser("~"))


def _telemetry_path() -> Path:
    return Path(os.path.expanduser("~")) / ".skillhub" / "telemetry.jsonl"


def _profile_path() -> Path:
    return Path(os.path.expanduser("~")) / ".skillhub" / "profile.json"


def _community_path() -> Path:
    # Community aggregate (registry/telemetry.jsonl) is reserved for future
    # opt-in sharing; for now stats are local-only.
    return Path(__file__).resolve().parent.parent.parent / "registry" / "telemetry.jsonl"


def _ensure_dir() -> None:
    (Path(os.path.expanduser("~")) / ".skillhub").mkdir(parents=True, exist_ok=True)


def _anon_session_id() -> str:
    """Stable anonymous session id per machine. Not portable, opt-in."""
    try:
        seed = f"{os.getlogin()}@{os.uname().nodename}"
    except (OSError, AttributeError):
        # CI / sandbox / restricted shells — fall back to a process-stable id.
        seed = str(os.getpid())
    return hashlib.sha256(seed.encode()).hexdigest()[:12]  # type: ignore[arg-type]  # noqa: E501


def _read_events() -> list[dict]:
    """Read local telemetry events for this user."""
    _ensure_dir()
    tp = _telemetry_path()
    sources = []
    if tp.exists():
        for line in tp.open():
            line = line.strip()
            if line:
                try:
                    sources.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return sources


WINDOW_DAYS = 7


def record(event_type: str, name: str, runtime: str = "",
           success: Optional[bool] = None, latency_ms: Optional[int] = None) -> dict:
    """Append one telemetry event locally. Returns the event dict."""
    _ensure_dir()
    evt = {
        "ts": int(time.time()),
        "event": event_type,
        "name": name,
        "runtime": runtime,
        "success": success,
        "latency_ms": latency_ms,
        "session_hash": _anon_session_id(),
    }
    tp = _telemetry_path()
    with tp.open("a") as f:
        f.write(json.dumps(evt, ensure_ascii=False) + "\n")
    return evt


def stats(name: str, window_days: int = WINDOW_DAYS) -> dict:
    """Aggregate stats for one skill."""
    cutoff = time.time() - window_days * 86400
    events = [e for e in _read_events() if e.get("ts", 0) >= cutoff and e.get("name") == name]
    rates = [e for e in events if e.get("event") == "rate" and e.get("success") is not None]
    installs = [e for e in events if e.get("event") == "install"]

    success_rate = None
    if rates:
        s = sum(1 for r in rates if r["success"])
        success_rate = s / len(rates)

    latencies_pure = [int(e["latency_ms"]) for e in events if e.get("latency_ms") is not None]
    p50 = statistics.median(latencies_pure) if latencies_pure else None
    p95 = None
    if len(latencies_pure) >= 5:
        s = sorted(latencies_pure)
        idx = int(0.95 * (len(s) - 1))
        p95 = s[idx]  # type: ignore[index]

    return {
        "name": name,
        "window_days": window_days,
        "samples": len(events),
        "installs": len(installs),
        "rates": len(rates),
        "success_rate": round(success_rate, 3) if success_rate is not None else None,
        "latency_ms": {"p50": int(p50) if p50 is not None else None,
                       "p95": int(p95) if p95 is not None else None},
    }


def recommend(installed: list[str], limit: int = 5) -> list[dict]:
    """Recommend skills based on co-install patterns.

    Simple algorithm: find users with all of `installed` installed,
    count what else they have. Return top by co-occurrence count,
    excluding already-installed.
    """
    events = _read_events()
    installs_by_session: dict[str, set[str]] = {}
    for e in events:
        if e.get("event") != "install":
            continue
        sess = e.get("session_hash", "?")
        installs_by_session.setdefault(sess, set()).add(e.get("name", ""))

    installed_set = set(installed)
    if not installed_set:
        # Cold start: return top by install count
        counts: Counter = Counter()
        for names in installs_by_session.values():
            counts.update(names)
        return [{"name": n, "score": c} for n, c in counts.most_common(limit)]

    # Find sessions that have at least one of the installed skills
    matching_sessions = [
        s for s, names in installs_by_session.items()
        if installed_set.intersection(names)
    ]
    if not matching_sessions:
        return []

    co_counts: Counter = Counter()
    for s in matching_sessions:
        co_counts.update(installs_by_session[s] - installed_set)
    total = len(matching_sessions)
    return [
        {"name": n, "co_install_sessions": c, "score": round(c / total, 3)}
        for n, c in co_counts.most_common(limit)
    ]


def profile_snapshot() -> dict:
    """Return current ~/.skillhub/profile.json (installed, rated, etc.)."""
    _ensure_dir()
    pp = _profile_path()
    if not pp.exists():
        return {"installed": [], "rated": {}, "last_session_ts": None}
    try:
        return json.loads(pp.read_text())
    except json.JSONDecodeError:
        return {"installed": [], "rated": {}, "last_session_ts": None}


def profile_mark_installed(name: str) -> None:
    _ensure_dir()
    prof = profile_snapshot()
    if name not in prof["installed"]:
        prof["installed"].append(name)
    prof["last_session_ts"] = int(time.time())
    pp = _profile_path()
    pp.write_text(json.dumps(prof, indent=2))
    record("install", name, success=True)


def profile_mark_rated(name: str, success: bool) -> None:
    _ensure_dir()
    prof = profile_snapshot()
    prof.setdefault("rated", {})[name] = {
        "success": success, "ts": int(time.time()),
    }
    prof["last_session_ts"] = int(time.time())
    pp = _profile_path()
    pp.write_text(json.dumps(prof, indent=2))
    record("rate", name, success=success)
