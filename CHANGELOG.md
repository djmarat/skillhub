# Changelog

## v0.1.0 (unreleased)

Retention loop for agent-consumer marketplace:

- **11 MCP tools** (was 4): `search`, `show`, `install`, `validate`, **`rate`**,
  **`stats`**, **`recommend`**, **`probe`**, **`profile`**, **`update`**,
  **`uninstall`**.
- **`rate`** tool — agent records whether a skill worked; tracked locally in
  `~/.skillhub/telemetry.jsonl`.
- **`stats`** tool — community success_rate / p50 / p95 / install counts over
  the last N days (default 7).
- **`recommend`** tool — co-install recommendations from the local telemetry
  graph. Cold-start falls back to top-by-install.
- **`probe`** tool — sandboxed dry-run: install into a tempdir, run healthchecks
  (manifest present, entry command on PATH, URL well-formed, YAML parses), roll
  back.
- **`profile`** tool — return the local `~/.skillhub/profile.json` so the agent
  re-orients at the start of a session.
- **`update`** / **`uninstall`** — complete agent lifecycle (was install-only).
- **Install + rate feed each other**: every install writes `install` event;
  every rate writes `rate` event; `stats` aggregates; `recommend` clusters.
- Test suite **40 passing** (was 26). New: `test_mcp2.py`, `test_lifecycle.py`,
  `tests/conftest.py` with autouse sandboxed HOME.

## v0.0.3 (unreleased)

- **MCP server** (`src/skillhub_mcp/server.py`) — exposes `search`, `show`,
  `install`, `validate` as MCP tools over JSON-RPC stdio.
- `skillhub-mcp` is itself a skill in the registry (meta-circle closed).
- README + landing updated with MCP wiring JSON.
- 15 new tests in `tests/test_mcp.py` (full stdio roundtrip).

## v0.0.2 (unreleased)

- Seed importer `scripts/seed_from_sources.py` (idempotent).
- Pulled **253 skills** from Official MCP Registry + SkillsMP top-by-stars.
- Trust Score v0.2 with real GitHub signals (stars, recency, source).
- Static security scanner (`src/skillhub/scan.py`) blocks eval/exec/curl-pipe.
- `skillhub validate --all` scans the registry, isolates broken records.
- `skillhub publish` validates + scans + stages incoming skills.
- `enrich_tags.py` adds tags via token frequency (idempotent).
- 11 tests in CLI + trust modules.

## v0.0.1 (unreleased)

- Manifest spec v0.1 (`manifest_spec.md`).
- CLI: `search`, `show`, `install`, `validate`.
- Local registry with 20 hand-curated skills in `registry/skills.jsonl`.
- Naive trust score (placeholder until install telemetry lands).
