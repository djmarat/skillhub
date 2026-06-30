# skillhub — manifest spec v0.1

Universal skill manifest, that compiles to Hermes, Claude Code, Codex CLI, Cursor.

---

## Goal

A skill is published **once** as `skill.yaml` (or `skill.json`).
The CLI compiles it to the runtime-specific format on `install`:

| Runtime | Output |
|---|---|
| `hermes` | `~/.hermes/skills/<name>/SKILL.md` |
| `claude-code` | `~/.claude/skills/<name>/SKILL.md` |
| `codex` | `~/.codex/skills/<name>/SKILL.md` |
| `cursor` | `~/.cursor/skills/<name>/SKILL.md` |

No more five copies of the same SKILL.md. **One source, many runtimes.**

---

## Schema (v0.1)

```yaml
# skill.yaml — single source of truth
name: pdf-md                  # required, kebab-case, ^[a-z0-9][a-z0-9-]{2,40}$
version: 0.1.0                # required, semver
description: |                # required, one sentence for agents
  Convert PDFs to clean Markdown with structure preserved.
runtime:                      # required, list of supported runtimes
  - hermes
  - claude-code
category: document            # optional, controlled vocab below
tags: [pdf, markdown, ocr]    # optional, free-form

entry:                        # required, what the skill does
  type: command               # command | http | python | node
  command: python -m pdf_md   # if type=command
  # or
  url: https://api.example.com/  # if type=http
  # ...

inputs:                       # optional, JSON Schema for inputs
  type: object
  properties:
    file_path:
      type: string
      description: Path to the PDF file
  required: [file_path]

outputs:                      # optional, JSON Schema for outputs
  type: object
  properties:
    markdown:
      type: string

trust:                        # optional, signals for trust score
  source: github              # github | official | community
  repo: owner/repo            # if source=github
  homepage: https://...       # optional
  license: MIT                # SPDX
  security_passes: 1          # bump on each successful run of `skillhub scan`

# Optional: free-form metadata, ignored by CLI.
# Use for tooling: telemetry, deps, etc.
meta:
  author: octocat
  deps:
    pypdf: ">=3.0"
```

JSON schema (authoritative): `schemas/skill.schema.json` (TODO).

---

## Controlled vocabularies

### `runtime`

- `hermes` — Nous Research Hermes Agent
- `claude-code` — Anthropic Claude Code
- `codex` — OpenAI Codex CLI
- `cursor` — Cursor IDE

### `category`

`agent`, `browser`, `code`, `data`, `design`, `document`, `devops`,
`finance`, `image`, `media`, `productivity`, `research`, `search`,
`security`, `social`, `test`, `utility`, `web`, `writing`, `other`.

### `entry.type`

- `command` — shell command (subprocess.run)
- `http` — HTTP endpoint (POST JSON, read JSON)
- `python` — `python -m <module>` style
- `node` — `node <script>` style

---

## File layout of a published skill

```
skill-name/
├── skill.yaml          # REQUIRED — this spec
├── SKILL.md            # OPTIONAL — human-edited, runtime-specific notes
├── README.md           # OPTIONAL — for humans on web catalog
└── (binaries/configs)
```

`skillhub install <name>` reads `skill.yaml`, transforms to runtime format,
and drops files into the right place.

---

## Why one spec, not five

| Problem today | This spec solves |
|---|---|
| Maintainer publishes same SKILL.md 4× | one source, CLI compiles |
| Runtime diverges — Claude has a hint Hermes doesn't | merged at install |
| Hard to add new runtime | write one transformer |
| Discovery: agents don't know which skills exist | `registry/skills.jsonl` is a flat index |

---

## Open questions (v0.1 → v0.2)

- Auth/scope: `entry.http` should support OAuth by reference (not values).
- Async tools: long-running jobs (`status`, `cancel`, `result`).
- Pricing: `cost_per_call_usd` for hosted APIs.
- Multi-command skills: `entry.commands[]` instead of single command?
- LLM-friendly modes: `entry.hints.examples[]` (few-shot for the agent).

Filed for v0.2 after MVP proves the format.
