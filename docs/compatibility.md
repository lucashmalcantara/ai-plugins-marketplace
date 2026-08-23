# Compatibility matrix

What each host does with the files inside a plugin directory. "Shared" means one file serves both.

| Component | Path | Claude Code | Codex | Notes |
| --- | --- | :---: | :---: | --- |
| Plugin manifest | `.claude-plugin/plugin.json` | ✅ | — | Only `name` is strictly required |
| Plugin manifest | `.codex-plugin/plugin.json` | — | ✅ | Adds the `interface` presentation block |
| Skills | `skills/<name>/SKILL.md` | ✅ | ✅ | **Shared.** Same frontmatter (`name`, `description`) |
| Skill resources | `skills/<name>/{scripts,references,assets}/` | ✅ | ✅ | Shared |
| Skill UI metadata | `skills/<name>/agents/openai.yaml` | ignored | ✅ | Codex-only, harmless to Claude Code |
| Slash commands | `commands/*.md` | ✅ | — | Claude Code only |
| Subagents | `agents/*.md` | ✅ | — | Claude Code only |
| Hooks | `hooks/hooks.json` | ✅ | ✅ | Shared **only** for events both support; see below |
| MCP servers | `.mcp.json` | ✅ | ✅ | Shared; Codex also accepts a `mcp_servers` wrapper key |
| Connector apps | `.app.json` | — | ✅ | Codex only |
| LSP servers | `.lsp.json` | ✅ | — | Claude Code only |
| Output styles | `output-styles/*.md` | ✅ | — | Claude Code only |
| Executables | `bin/` | ✅ | — | Added to the Bash tool `PATH` |
| Branding assets | `assets/` | — | ✅ | Icons, logo, screenshots for the Codex plugin card |

## Skills

The one component that is genuinely portable. Both hosts read `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
description: What it does, and when it should and should not trigger.
---
```

Rules that satisfy both: `name` is lowercase alphanumeric and hyphens, at most 64 characters, and
matches the directory name; `description` is at most 1024 characters. The description is the only
text an agent sees before deciding to load the skill, so it must say when to use the skill, not just
what it is.

Invocation differs: Claude Code namespaces skills as `/<plugin>:<skill>`, Codex uses `$<skill>` in
the CLI and `@` in ChatGPT. Both can also select a skill implicitly from the description.

## Hooks

Both hosts use the same `hooks/hooks.json` shape and both export `CLAUDE_PLUGIN_ROOT` — Codex
provides `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` as aliases, so `${CLAUDE_PLUGIN_ROOT}` works on
both. The event vocabularies do not fully overlap: Claude Code documents around thirty events
(`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, …), while the Codex plugin docs cover a
smaller set.

Keep portable events in a shared `hooks/hooks.json`, and put host-specific ones in a separate file
referenced only from that host's manifest:

```json
{ "hooks": "./hooks/claude.hooks.json" }
```

## Environment variables

| Variable | Claude Code | Codex |
| --- | :---: | :---: |
| `CLAUDE_PLUGIN_ROOT` | ✅ | ✅ (alias) |
| `PLUGIN_ROOT` | — | ✅ |
| `CLAUDE_PLUGIN_DATA` | ✅ | ✅ (alias) |
| `PLUGIN_DATA` | — | ✅ |
| `CLAUDE_PROJECT_DIR` | ✅ | — |

Prefer `${CLAUDE_PLUGIN_ROOT}` in anything shared — it is the only one both hosts define.

## Practical guidance

- **Lead with skills.** A skills-only plugin is portable with zero per-host logic.
- **Add host-specific components deliberately.** A Claude Code subagent is worth having even though
  Codex ignores it; just say so in the plugin README so nobody is surprised.
- **Do not fake parity.** If a plugin is only meaningful on one host, set `targets` in
  `.marketplace.json` to that host and skip the other manifest entirely.
