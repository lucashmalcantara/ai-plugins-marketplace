# Repository guide

This repository is a plugin marketplace that publishes the same plugins to **Claude Code** and
**Codex**. Read [`docs/architecture.md`](./docs/architecture.md) before changing anything structural.

## Layout rules

- Plugins live in `plugins/<kebab-case-name>/`, one directory per plugin, each holding **both**
  host manifests over one shared body of content.
- `.claude-plugin/plugin.json` is read by Claude Code; `.codex-plugin/plugin.json` by Codex. Keep
  `name`, `version`, `description`, `author`, `license`, and `keywords` in agreement.
- Component directories (`skills/`, `agents/`, `commands/`, `hooks/`) go at the **plugin root**,
  never inside `.claude-plugin/` or `.codex-plugin/`.
- Manifest paths are relative and start with `./`, and never escape the plugin root.

## Generated files — never edit by hand

- `.claude-plugin/marketplace.json`
- `.agents/plugins/marketplace.json`
- `PLUGINS.md`

They come from the plugin manifests plus `marketplace.config.json`. After changing any manifest,
run `make sync` and commit the result. `make check` is what CI runs.

## Commands

```shell
make new NAME=my-plugin   # scaffold from templates/plugin-template
make validate             # manifests, skills, referenced paths, version agreement
make sync                 # regenerate the catalogs and PLUGINS.md
make check                # stale-file check + validate
```

Tooling is Python 3, standard library only. Do not add dependencies or a package manager without a
concrete reason — the zero-install property is deliberate.

## Conventions

- Every plugin change bumps `version` in both manifests and adds a `CHANGELOG.md` entry. Both hosts
  skip updates when the version string is unchanged.
- A plugin's `name` and the marketplace `name` are stable identifiers. Renaming either breaks
  existing installs; see [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- Prefer `${CLAUDE_PLUGIN_ROOT}` in hooks, scripts, and MCP configs — it is the only root variable
  both hosts define.
- Skill `description` frontmatter must say when to use *and when not to use* the skill; it is the
  only text an agent sees before loading the skill.
- Documentation and plugin content are written in English.
