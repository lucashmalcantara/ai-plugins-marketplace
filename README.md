# AI Plugins Marketplace

A single repository that publishes the same plugins to **Claude Code** and **Codex**.

Each plugin lives once under [`plugins/`](./plugins) and carries a manifest for each host. The two
marketplace catalogs — the one Claude Code reads and the one Codex reads — are generated from those
manifests, so a plugin can never appear in one catalog with stale metadata from the other.

See [`PLUGINS.md`](./PLUGINS.md) for what is currently published.

## Install

**Claude Code**

```shell
/plugin marketplace add lucashmalcantara/ai-plugins-marketplace
/plugin install commit-craft@lucashmalcantara-plugins
```

**Codex**

```shell
codex plugin marketplace add lucashmalcantara/ai-plugins-marketplace
```

Then open `/plugins` and enable what you want. To pull later updates: `/plugin marketplace update`
in Claude Code, `codex plugin marketplace upgrade` in Codex.

## Repository layout

```
.
├── .claude-plugin/marketplace.json   # generated — catalog Claude Code reads
├── .agents/plugins/marketplace.json  # generated — catalog Codex reads
├── PLUGINS.md                        # generated — human-readable index
├── marketplace.config.json           # marketplace identity (name, owner, description)
├── plugins/
│   └── <plugin-name>/
│       ├── .claude-plugin/plugin.json   # Claude Code manifest
│       ├── .codex-plugin/plugin.json    # Codex manifest
│       ├── .marketplace.json            # publication metadata (targets, category, policy)
│       ├── skills/<skill>/SKILL.md      # shared by both hosts
│       ├── agents/  commands/           # Claude Code only
│       ├── hooks/hooks.json  .mcp.json  # shared where the schemas agree
│       ├── assets/                      # icons and screenshots for the Codex UI
│       ├── README.md
│       └── CHANGELOG.md
├── templates/plugin-template/        # scaffold source
├── scripts/                          # sync, validate, scaffold (Python 3, stdlib only)
└── docs/
```

Both hosts resolve `./plugins/<name>` relative to the repository root, which is why one `plugins/`
directory can serve both catalogs. See [`docs/architecture.md`](./docs/architecture.md) for the
reasoning and the source links.

## Working in this repo

```shell
make new NAME=my-plugin   # scaffold plugins/my-plugin
make validate             # check manifests, skills, and generated files
make sync                 # regenerate the catalogs and PLUGINS.md
make test                 # run the plugin script tests
make check                # what CI runs
```

Only Python 3 is required — the scripts use nothing outside the standard library.

## Docs

| Document | What it covers |
| --- | --- |
| [Architecture](./docs/architecture.md) | Why there are two catalogs and how generation works |
| [Authoring plugins](./docs/authoring-plugins.md) | Manifests, skills, hooks, MCP servers, versioning |
| [Compatibility](./docs/compatibility.md) | Which components each host supports |
| [Testing](./docs/testing.md) | Running a plugin locally in both CLIs before publishing |
| [Contributing](./CONTRIBUTING.md) | Adding a plugin, review checklist, release flow |

## License

[Apache 2.0](./LICENSE)
