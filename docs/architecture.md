# Architecture

## The problem

Claude Code and Codex both ship a plugin system, and the two are close enough to share content but
different enough that you cannot point one at the other's files:

| | Claude Code | Codex |
| --- | --- | --- |
| Marketplace catalog | `.claude-plugin/marketplace.json` | `.agents/plugins/marketplace.json` |
| Plugin manifest | `<plugin>/.claude-plugin/plugin.json` | `<plugin>/.codex-plugin/plugin.json` |
| Local plugin source | `"source": "./plugins/x"` | `"source": {"source": "local", "path": "./plugins/x"}` |
| Skills | `skills/<name>/SKILL.md` | `skills/<name>/SKILL.md` |
| Add the marketplace | `/plugin marketplace add owner/repo` | `codex plugin marketplace add owner/repo` |

The important detail is the last row of the middle block: **both hosts resolve a local plugin path
relative to the repository root**, not relative to the directory holding the catalog. Claude Code
documents this explicitly ("paths resolve relative to the marketplace root, which is the directory
containing `.claude-plugin/`"), and the official `openai/plugins` repository does the same thing —
its catalog sits at `.agents/plugins/marketplace.json` and every entry points at `./plugins/<name>`.

That single fact is what makes this repository possible: one `plugins/` tree, two catalogs pointing
into it.

## The shape

```
repo root
├── .claude-plugin/marketplace.json   ─┐
├── .agents/plugins/marketplace.json  ─┤ both point at ↓
└── plugins/<name>/                   ←┘
    ├── .claude-plugin/plugin.json    read by Claude Code
    ├── .codex-plugin/plugin.json     read by Codex
    └── skills/, hooks/, .mcp.json    read by whichever manifest references them
```

A plugin directory holds **two manifests over one body of content**. Each host reads only its own
manifest and ignores the other's directory, so `.codex-plugin/` is invisible to Claude Code and
`.claude-plugin/` is invisible to Codex. Content that only one host understands (`agents/`,
`commands/` for Claude Code; `.app.json`, `assets/` for Codex) simply goes unreferenced by the
other manifest.

## Generation

Hand-maintaining two catalogs plus two manifests per plugin guarantees drift. Instead:

- **Source of truth**: the per-plugin manifests, plus `plugins/<name>/.marketplace.json` for
  metadata that only matters when publishing (which hosts to publish to, category, tags, Codex
  install policy), plus `marketplace.config.json` for the marketplace's own identity.
- **Generated, and committed**: `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`,
  and `PLUGINS.md`.

They are committed rather than built on demand because the catalogs are exactly what a user's CLI
fetches over git when they add the marketplace — there is no build step on their side.
`scripts/sync_marketplaces.py --check` fails CI when a commit changes a manifest without
regenerating, which is what keeps "generated but committed" honest.

### `.marketplace.json`

```json
{
  "targets": ["claude-code", "codex"],
  "category": "Productivity",
  "tags": ["git", "commits"],
  "claude": { "defaultEnabled": true },
  "codex": { "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" } }
}
```

`targets` is how a plugin opts out of a host. Drop `"codex"` and the plugin disappears from the
Codex catalog without any other change; the validator then stops requiring `.codex-plugin/plugin.json`.

### Why the generated Claude entries carry no `version`

Claude Code resolves a plugin's version from `plugin.json` first and uses it *without warning* when
the marketplace entry disagrees. Two copies of the same string, one of which is silently ignored, is
a trap, so the generator emits the version only in `plugin.json`. `scripts/validate.py` enforces
that the Claude and Codex manifests declare the same version.

## Sources

- [Claude Code — Create and distribute a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Claude Code — Plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Codex — Package your plugin](https://developers.openai.com/codex/plugins/build)
- [Codex — Build skills](https://developers.openai.com/codex/skills)
- [`openai/plugins`](https://github.com/openai/plugins) — the reference Codex marketplace repository
