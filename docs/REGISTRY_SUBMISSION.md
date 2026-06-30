# skillhub registry submission drafts

These are pre-written text snippets ready to paste into each index's
submission form. The goal of submitting: get skillhub listed alongside
Smithery / Glama / SkillsMP so agents searching "skill marketplace"
discover us.

---

## 1. Smithery

**Where to submit**: https://smithery.ai/servers/new (or via their CLI:
`gh repo create` + tag-based deploy)

**Name**: `skillhub`

**Description** (paste into form):

```
Trusted skill marketplace for AI agents. One universal manifest, many
runtimes (Hermes, Claude Code, Codex, Cursor). CLI + agent-friendly JSON
search + install. Indexed top skills curated from Official MCP Registry
and SkillsMP. Trust scores derived from real GitHub signals (stars +
recency + source). Open source, MIT.
```

**Category**: registry

**Repo**: https://github.com/djmarat/skillhub

**Tags**: mcp, registry, marketplace, cli, agents

---

## 2. Glama.ai

**Where to submit**: https://glama.ai/submit (or via their Discord
`/add-server`)

**Name**: skillhub

**Description**:

```
A trusted skill marketplace for AI agents. We aggregate top skills from
the Official MCP Registry + SkillsMP, normalize them to a single
universal manifest (skill.yaml), and serve them via agent-friendly
JSON CLI and installable formats. Trust scores are derived from real
signals (GitHub stars, repo recency, source type) — not a star count.
```

**Link**: https://github.com/djmarat/skillhub

**Tags**: marketplace, registry, mcp, agents, catalog

---

## 3. SkillsMP

**Where to submit**: https://skillsmp.com/submit (their "Add a skill"
form) OR via direct PR to their registry — check their /add docs.

**Note**: SkillsMP indexes SKILL.md files from GitHub. Their indexer
will pick up skillhub the moment our repo is referenced in any
catalog — they don't have a manual submission, but submitting to
their search via /add or by being linked from external sources is
the entry point.

**Title**: skillhub — trusted skill marketplace for AI agents

**Description**:

```
A skill marketplace CLI for AI agents. Search 250+ curated skills
with `skillhub search <query> --json`, install into Hermes / Claude
Code / Codex / Cursor. Universal manifest, real trust signals, MIT.
```

**Repo**: https://github.com/djmarat/skillhub

---

## 4. mcp-get (npm CLI installer for MCP servers)

**Where to submit**: their GitHub
[modelcontextprotocol/get](https://github.com/modelcontextprotocol/get-mcp).
Add an entry that registers `skillhub-mcp` as a discoverable server
once we ship the MCP-server adapter.

(Skip this for v0.0.2 — needs the MCP adapter first.)

---

## 5. Crunchbase / A-list of OSS markers (longer-term)

*This is for v1.0, not now:*

- Add to awesome-mcp-servers (PR to https://github.com/punkpeye/awesome-mcp-servers)
- Add to awesome-claude-skills (the curated community list)

These are the highest-value organic inbound channels for the project.

---

## Workflow when you actually submit

1. Copy the description above for whichever index.
2. Open the form URL from this file.
3. Paste description, add repo URL.
4. Save confirmation.
5. Add a row to `docs/SUBMISSION_LOG.md` (year, index, link, date).
