#!/usr/bin/env python3
"""seed_from_sources.py — pull real popular skills from MCP registries.

Sources:
  - Official MCP Registry (registry.modelcontextprotocol.io)
  - SkillsMP (skillsmp.com) — top by stars

Output: appends normalized skill records to registry/skills.jsonl,
deduplicating by 'name'. Idempotent — safe to re-run.

Run from repo root:
    python -m scripts.seed_from_sources
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

REGISTRY = ROOT / "registry" / "skills.jsonl"

MCP_REGISTRY = "https://registry.modelcontextprotocol.io/v0/servers"
SKILLSMP_API = "https://skillsmp.com/api/skills"

USER_AGENT = "skillhub/0.0.2 (registry builder)"


def _fetch(url: str, params: dict | None = None) -> dict:
    if params:
        qs = urllib.parse.urlencode(params)
        url = f"{url}?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_mcp_registry_all(max_pages: int = 8) -> list[dict]:
    """Pull servers from official MCP Registry, paginating by cursor.

    Stop early on max_pages to keep the import bounded — the registry
    is huge and we only need representative coverage.
    """
    out: list[dict] = []
    cursor: str | None = None
    seen_cursor: set[str] = set()
    page = 0
    while page < max_pages:
        params: dict = {"limit": 100}
        if cursor:
            params["cursor"] = cursor
        data = _fetch(MCP_REGISTRY, params)
        out.extend(data.get("servers", []))
        meta = data.get("metadata", {}) or {}
        cursor = meta.get("nextCursor") or meta.get("next_cursor")
        page += 1
        if not cursor or cursor in seen_cursor:
            break
        seen_cursor.add(cursor)
    return out


def _normalize_mcp(entry: dict) -> dict | None:
    srv = entry.get("server", {})
    name = srv.get("name", "")
    if not name:
        return None
    # name may be like "io.github.owner/repo" — collapse to handle-slug
    slug = name.split("/")[-1].lower().replace("_", "-")
    if not slug.replace("-", "").isalnum():
        return None
    if len(slug) > 40 or len(slug) < 3:
        return None
    # find a remote URL we can use as the "entry.url"
    remotes = srv.get("remotes", [])
    url = ""
    for r in remotes:
        if r.get("type") == "streamable-http":
            url = r.get("url", "")
            break
    if not url and remotes:
        url = remotes[0].get("url", "")
    description = srv.get("description", "")[:200]
    if not description:
        return None
    return {
        "name": slug,
        "version": str(srv.get("version", "0.0.0")),
        "description": description,
        "runtime": ["hermes", "claude-code", "codex", "cursor"],
        "category": _category_from_text(name + " " + description),
        "tags": [],
        "entry": {"type": "http", "url": url} if url else {"type": "command", "command": f"mcp-{slug}"},
        "trust": {
            "source": "official",
            "license": srv.get("license", "MIT"),
            "security_passes": 0,
        },
    }


def _category_from_text(text: str) -> str:
    text = text.lower()
    rules = [
        ("search", ["search", "retriev", "find"]),
        ("browser", ["browser", "playwright", "puppeteer"]),
        ("data", ["postgres", "sql", "database", "mongo", "redis", "supabase", "duckdb"]),
        ("devops", ["deploy", "github", "gitlab", "k8s", "kubernetes", "docker", "ci"]),
        ("document", ["pdf", "doc", "markdown", "wiki", "notion"]),
        ("design", ["figma", "design", "image", "draw"]),
        ("research", ["arxiv", "paper", "citation", "research"]),
        ("finance", ["stripe", "payment", "invoice", "financ"]),
        ("media", ["audio", "video", "music", "podcast"]),
        ("social", ["twitter", "x.com", "linkedin", "discord", "slack", "telegram"]),
        ("utility", ["util", "helper", "tool"]),
    ]
    for cat, keywords in rules:
        if any(k in text for k in keywords):
            return cat
    return "other"


def _fetch_skillsmp_top(limit: int = 60) -> list[dict]:
    """Top-N by stars from SkillsMP."""
    out: list[dict] = []
    seen_ids: set[str] = set()
    page = 1
    while len(out) < limit and page <= 30:
        data = _fetch(SKILLSMP_API, {"page": page, "limit": 24, "sortBy": "stars"})
        skills = data.get("skills", [])
        if not skills:
            break
        for s in skills:
            sid = s.get("id")
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            stars = s.get("stars", 0)
            if stars < 3:  # skip fresh / low-quality
                continue
            out.append(s)
        page += 1
    return out[:limit]


def _normalize_skillsmp(entry: dict) -> dict | None:
    raw_name = entry.get("name", "").strip()
    if not raw_name:
        return None
    slug = raw_name.lower().replace("_", "-").replace(" ", "-")
    if not slug.replace("-", "").isalnum() or len(slug) < 3 or len(slug) > 40:
        return None
    github_url = entry.get("githubUrl", "")
    description = entry.get("description", "")
    if not description:
        return None
    repo = ""
    if github_url.startswith("https://github.com/"):
        parts = github_url.split("/")
        if len(parts) >= 5:
            repo = f"{parts[3]}/{parts[4]}"
    return {
        "name": slug,
        "version": "1.0.0",
        "description": description[:200],
        "runtime": ["hermes", "claude-code"],
        "category": _category_from_text(slug + " " + description),
        "tags": [],
        "entry": {"type": "command", "command": f"skill run {slug}"} if repo else {"type": "command", "command": f"skill-{slug}"},
        "trust": {
            "source": "github",
            "repo": repo,
            "license": "MIT",
            "security_passes": 0,
        },
    }


def _existing_names() -> set[str]:
    if not REGISTRY.exists():
        return set()
    names: set[str] = set()
    with REGISTRY.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                if d.get("name"):
                    names.add(d["name"])
            except json.JSONDecodeError:
                continue
    return names


def _save(new_records: list[dict]) -> int:
    if not new_records:
        return 0
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRY.open("a") as f:
        for r in new_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(new_records)


def main() -> int:
    existing = _existing_names()
    print(f"existing records: {len(existing)}")

    added = 0
    skipped_existing = 0
    skipped_invalid = 0

    # Source 1: Official MCP Registry
    print("\n--- pulling Official MCP Registry ---")
    mcp_servers = _fetch_mcp_registry_all()
    print(f"  raw entries: {len(mcp_servers)}")
    for entry in mcp_servers:
        rec = _normalize_mcp(entry)
        if rec is None:
            skipped_invalid += 1
            continue
        if rec["name"] in existing:
            skipped_existing += 1
            continue
        existing.add(rec["name"])
        _save([rec])
        added += 1

    # Source 2: SkillsMP top by stars
    print("\n--- pulling SkillsMP top-by-stars ---")
    smp_skills = _fetch_skillsmp_top(limit=40)
    print(f"  raw entries (>=3 stars): {len(smp_skills)}")
    for entry in smp_skills:
        rec = _normalize_skillsmp(entry)
        if rec is None:
            skipped_invalid += 1
            continue
        if rec["name"] in existing:
            skipped_existing += 1
            continue
        existing.add(rec["name"])
        _save([rec])
        added += 1

    print(f"\nsummary: +{added} new / skipped {skipped_existing} existing / {skipped_invalid} invalid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
