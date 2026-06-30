# skillhub

> Trusted skill marketplace for AI agents. **One manifest, many runtimes.**

A skill is a small tool that an AI agent (Hermes, Claude Code, Codex, Cursor)
can call as a black box. `skillhub` is the place where:

- maintainers publish skills **once**, in a universal `skill.yaml`,
- agents and humans discover them via `skillhub search`,
- they install into the right runtime with `skillhub install <name> <runtime>`.

No domain. No accounts. No money involved — yet. Just the protocol, the CLI,
and a registry of 20 seed skills.

## Status

v0.0.1 — local CLI, no network, no payments. The goal of v0.0.1 is to **prove
the manifest format** and the discoverability workflow before we add infrastructure.

## What's here

| File | What it is |
|---|---|
| [`manifest_spec.md`](manifest_spec.md) | Universal skill manifest, v0.1 |
| `src/skillhub/cli.py` | CLI: `search`, `show`, `install`, `validate` |
| `registry/skills.jsonl` | 20 seed skills (curated by hand for v0) |
| `pyproject.toml` | `pip install -e .` |

## Install (local)

```bash
git clone <repo>
cd skillhub
python -m venv .venv && source .venv/bin/activate
pip install -e .
skillhub search "pdf"
```

## Usage

```bash
# Search the local registry
skillhub search "search"             # human table
skillhub search "pdf" --json         # agent-friendly, one JSON per line

# Show one skill in detail
skillhub show pdf-md

# Install into a runtime
skillhub install pdf-md --runtime hermes
# or
skillhub install pdf-md -r claude-code

# Validate your own skill.yaml
skillhub validate ./my-skill/skill.yaml
```

## Why this exists

- **Maintainers** write `skill.yaml` once; the CLI compiles to runtime layouts.
- **Agents** find skills via `skillhub search --json` instead of web scraping.
- **Humans** get a `trust_score` per skill — derived from real signals,
  not stars.
- **Everyone** agrees on the same `skill.yaml` schema, so we don't fork
  five copies of the same SKILL.md across runtimes.

## Roadmap (no dates)

- v0.1: schema stable, security scanner v1, real registry updater.
- v0.2: trust score from `install_success_rate` (live telemetry).
- v0.3: in-agent MCP-server (`skillhub-mcp`) so any MCP-capable agent
  can discover/install skills via tool calls.
- v1.0: featured/verified tiers, paid placements, the actual marketplace.

## License

MIT. See headers in source files.
