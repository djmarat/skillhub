---
layout: default
title: skillhub
---

# skillhub

> Trusted skill marketplace for AI agents. **One manifest, many runtimes.**

A skill is a small tool that an AI agent (Hermes, Claude Code, Codex, Cursor) can call
as a black box. `skillhub` is the registry where maintainers publish once and any agent
can discover, install, and run.

## Why

- **Maintainers** write `skill.yaml` once — the CLI compiles to the runtime's native layout.
- **Agents** find skills via `skillhub search --json` instead of scraping the web.
- **Humans** see a `trust_score` per skill — derived from real signals, not star counts.
- **Everyone** agrees on the same schema, so we don't fork five copies of the same
  `SKILL.md` across runtimes.

## What ships in v0.0.1

- [Universal manifest spec v0.1](https://github.com/djmarat/skillhub/blob/main/manifest_spec.md)
- `skillhub` CLI: `search`, `show`, `install`, `validate`
- Local registry of 20 curated skills
- Naive `trust_score` placeholder (real telemetry from `install_success_rate` lands in v0.2)

## Install (local)

```bash
git clone https://github.com/djmarat/skillhub
cd skillhub
python -m venv .venv && source .venv/bin/activate
pip install -e .
skillhub search "pdf"
```

## Usage

```bash
# Search — human table
skillhub search "search"

# Search — agent-friendly JSON
skillhub search "pdf" --json

# Show full details
skillhub show pdf-md

# Install into a runtime
skillhub install pdf-md -r hermes
skillhub install pdf-md -r claude-code
skillhub install pdf-md -r codex
skillhub install pdf-md -r cursor

# Validate your own skill.yaml
skillhub validate ./my-skill/skill.yaml
```

## Roadmap

- **v0.1** — schema freeze, security scanner v1, real registry updater.
- **v0.2** — trust score from real `install_success_rate` telemetry.
- **v0.3** — in-agent MCP server (`skillhub-mcp`) for tool-call discovery.
- **v1.0** — featured/verified tiers, paid placements, the actual marketplace.

## Project

Source: [github.com/djmarat/skillhub](https://github.com/djmarat/skillhub)
Manifest spec: [manifest_spec.md](https://github.com/djmarat/skillhub/blob/main/manifest_spec.md)
License: MIT
