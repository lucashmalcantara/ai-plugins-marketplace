# Authoring plugins

## Create the skeleton

```shell
make new NAME=my-plugin
# or, with everything spelled out:
python3 scripts/new_plugin.py my-plugin \
    --display-name "My Plugin" \
    --description "One sentence on what it does." \
    --skill my-skill \
    --category Productivity \
    --targets claude-code,codex
```

That copies `templates/plugin-template/`, substitutes the placeholders, and regenerates the
catalogs. What you get:

```
plugins/my-plugin/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
├── .marketplace.json
├── skills/my-skill/SKILL.md
├── assets/
├── README.md
└── CHANGELOG.md
```

## Write the skill

The `description` is the whole discovery mechanism — both hosts show the agent only `name`,
`description`, and the path until the skill is actually selected. Say when to use it and when not
to:

```markdown
---
name: commit-craft
description: Write Conventional Commits messages from the staged diff. Use when the user asks to
  commit, to write or improve a commit message, or to split staged changes into logical commits.
---
```

The body is a procedure, not an essay. Concrete steps, the exact commands to run, the rules the
agent must not break. Put long reference material in `references/` and executable helpers in
`scripts/` so the body stays short — both hosts load the body into context every time the skill
fires.

## Fill in the manifests

Keep the two manifests in agreement on `name`, `version`, `description`, `author`, `license`, and
`keywords`. The validator enforces `name` and `version`.

**`.claude-plugin/plugin.json`** — everything except `name` is optional; components in the default
locations (`skills/`, `agents/`, `commands/`, `hooks/hooks.json`, `.mcp.json`) are discovered
automatically. Note the asymmetry: listing `commands` or `agents` *replaces* the default scan, while
listing `skills` *adds* to it.

**`.codex-plugin/plugin.json`** — same core fields, plus the `interface` block that drives the Codex
plugin card:

```json
"interface": {
  "displayName": "My Plugin",
  "shortDescription": "Subtitle in compact views.",
  "longDescription": "Longer text on the details screen.",
  "developerName": "Your name",
  "category": "Productivity",
  "capabilities": ["Read", "Write"],
  "defaultPrompt": ["At most three starter prompts.", "Around 50 characters each."],
  "brandColor": "#3B82F6",
  "composerIcon": "./assets/icon.png",
  "logo": "./assets/logo.png",
  "screenshots": ["./assets/screenshot-1.png"]
}
```

`defaultPrompt` keeps only the first three entries and truncates each at 128 characters.
`screenshots` must be PNG files under `./assets/`. The validator checks both.

## Choose where it publishes

`.marketplace.json` holds everything that is about *publishing* rather than about the plugin:

```json
{
  "targets": ["claude-code", "codex"],
  "category": "Productivity",
  "tags": ["git", "commits"],
  "claude": { "defaultEnabled": true },
  "codex": { "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" } }
}
```

- `targets` — drop a host to remove the plugin from that catalog. The matching manifest directory
  then becomes unnecessary.
- `claude.defaultEnabled: false` — install the plugin disabled until the user opts in.
- `codex.policy.installation` — `AVAILABLE`, `INSTALLED_BY_DEFAULT`, or `NOT_AVAILABLE`.
- `codex.policy.authentication` — `ON_INSTALL` or `ON_USE`.

## Bundle an MCP server

`.mcp.json` at the plugin root works on both hosts:

```json
{
  "mcpServers": {
    "my-service": {
      "command": "${CLAUDE_PLUGIN_ROOT}/bin/server",
      "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"]
    }
  }
}
```

Use `${CLAUDE_PLUGIN_ROOT}` rather than relative paths — the plugin is copied into a cache
directory at install time, so the working directory is not what you think it is. Codex also accepts
the `mcp_servers` key and a bare server map; `mcpServers` is the form both understand.

## Versioning

- Semver, and identical in both manifests.
- **Bump it on every release.** Both hosts key their update check on the version string: if it does
  not change, users keep the cached copy no matter what you pushed.
- Record what changed in the plugin's `CHANGELOG.md`.

## Before you open a PR

```shell
make check
```

That regenerates nothing — it fails if the generated files are stale and then runs the full
validator. Fix, run `make sync`, and commit the regenerated files alongside your change. See
[testing](./testing.md) for the manual loop in both CLIs.
