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
| `src/skillhub/cli.py` | CLI: `search`, `show`, `install`, `validate`, `publish` |
| `src/skillhub_mcp/server.py` | MCP server exposing the same 4 tools to agents |
| `src/skillhub/trust.py` | Trust Score v0.2 (real GitHub signals) |
| `src/skillhub/scan.py` | Static security scanner |
| `registry/skills.jsonl` | 254 curated skills (incl. `skillhub-mcp` itself) |
| `registry/trust.json` | Cached trust scores (TTL 6h) |
| `scripts/seed_from_sources.py` | Idempotent importer from public registries |
| `scripts/enrich_tags.py` | Tag enrichment via token frequency |
| `pyproject.toml` | `uv tool install -e .` |

## Install (local)

Requires [uv](https://github.com/astral-sh/uv) (a fast Python package manager).
On macOS: `brew install uv`. The CLI is then globally available as `skillhub`.

```bash
git clone https://github.com/djmarat/skillhub
cd skillhub
uv tool install -e .            # installs skillhub + skillhub-mcp
skillhub search "pdf"           # try it
```

To re-install after pulling new code:

```bash
cd skillhub
uv tool install -e . --force
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
## As an MCP server (`skillhub-mcp`)

For AI agents that speak MCP (Claude Code, Hermes, Codex, Cursor), `skillhub` ships
its own marketplace as a server. Connect once, then search/show/install/validate
skills as tool calls — no copy-paste, no scraping.

```json
{
  "mcpServers": {
    "skillhub": {
      "command": "skillhub-mcp"
    }
  }
}
```

If you don't have `uv tool` installed globally, fall back to the dev form:

```json
{
  "mcpServers": {
    "skillhub": {
      "command": "python",
      "args": ["-m", "skillhub_mcp.server"],
      "cwd": "/path/to/skillhub"
    }
  }
}
```

The server exposes **15 tools** — full agent lifecycle:

| Tool | When the agent uses it |
|---|---|
| `search` | "I need a tool that does X" |
| `show` | "Tell me more about this one" |
| `stats` | "What's the community success rate? Latency?" |
| `probe` | "Try a dry-run install first, don't touch my runtime" |
| `install` | "Make it real" |
| `update` | "Refresh me on the latest version" |
| `uninstall` | "I don't need this anymore" |
| `validate` | "Is this skill.yaml well-formed and safe to ship?" |
| `rate` | "Did this skill work? Tell others" |
| `recommend` | "What else usually goes with the stuff I have?" |
| `profile` | "What have I already installed/rated in this account?" |
| `collections` | "List curated bundles (AI Researcher, PDF, …)" |
| `collection` | "Show one bundle details" |
| `bundle_install` | "Install an entire bundle" |
| `bundle_suggest` | "What bundle fits my installed skills?" |

The **retention loop** is built in: every install writes to a local profile;
every successful run is recorded as a `rate`; the next `stats` call surfaces
those signals back. So agents get more confident about skills over time —
not less.

See [`src/skillhub_mcp/server.py`](src/skillhub_mcp/server.py) for the full schema.

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
