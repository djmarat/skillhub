"""collections.py — curated bundles of skills for discovery.

load(): parse registry/collections.json
list_collections(): brief summaries for `collections` tool
get(name_or_id): full bundle with skills + trust scores
recommend_for_installed(installed): which collections is the user
  'almost done' with based on what's installed?
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
COLLECTIONS_PATH = ROOT / "registry" / "collections.json"


def _load() -> dict:
    if not COLLECTIONS_PATH.exists():
        return {"version": "1.0.0", "collections": []}
    try:
        return json.loads(COLLECTIONS_PATH.read_text())
    except json.JSONDecodeError:
        return {"version": "1.0.0", "collections": []}


def _by_id(cid: str) -> Optional[dict]:
    for c in _load().get("collections", []):
        if c.get("id") == cid or c.get("title", "").lower().replace(" ", "-") == cid:
            return c
    return None


def list_collections() -> list[dict]:
    """Brief summaries, one per collection."""
    out = []
    for c in _load().get("collections", []):
        out.append({
            "id": c.get("id"),
            "title": c.get("title"),
            "description": c.get("description"),
            "tags": c.get("tags", []),
            "skills_count": len(c.get("skills", [])),
            "skills": c.get("skills", []),
        })
    return out


def get(name_or_id: str) -> Optional[dict]:
    return _by_id(name_or_id)


def recommend_for_installed(installed: list[str], top: int = 3) -> list[dict]:
    """Collections where the user has 60%+ of the skills already installed."""
    out = []
    installed_set = set(installed)
    for c in _load().get("collections", []):
        members = c.get("skills", [])
        if not members:
            continue
        hit = installed_set.intersection(members)
        if not hit:
            continue
        ratio = len(hit) / len(members)
        if ratio >= 0.4:  # 'almost done' threshold
            remaining = [m for m in members if m not in installed_set]
            out.append({
                "id": c.get("id"),
                "title": c.get("title"),
                "description": c.get("description"),
                "skills_installed": sorted(hit),
                "skills_remaining": remaining,
                "completion": round(ratio, 2),
            })
    out.sort(key=lambda x: -x["completion"])
    return out[:top]
