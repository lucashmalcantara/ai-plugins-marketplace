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
make test                 # run plugins/*/scripts/test_*.py
make check                # stale-file check + validate + test
```

Tooling is Python 3, standard library only. Do not add dependencies or a package manager without a
concrete reason — the zero-install property is deliberate.

## Commit attribution

Commits carry a co-authorship trailer naming the model that wrote the change; the person running
the session stays the commit `Author`. The rules live in the `commit-craft` skill, which is their
source of truth — read the **Co-authorship** section of
[`plugins/commit-craft/skills/commit-craft/SKILL.md`](./plugins/commit-craft/skills/commit-craft/SKILL.md)
and follow it. Deliberately not restated here: one copy is the point, and a second would drift.

Nothing in the repository enforces it. No hook blocks a commit that omits the trailer, so writing
it is the job of the agent that did the work — the only thing that knows.

## Conventions

- Every plugin change bumps `version` in both manifests and adds a `CHANGELOG.md` entry. Both hosts
  skip updates when the version string is unchanged, so a released version edited underneath users
  is an edit they never receive.
- **Before a version is released there is nothing to bust.** While it is still unpublished, extend
  that version's existing `CHANGELOG.md` entry instead of opening a new one — bumping there records
  a change against something nobody could have installed. Check before you bump:

  ```shell
  git show origin/main:plugins/<name>/.claude-plugin/plugin.json
  ```

  An error means the plugin has never been published, so do not bump. If it prints, compare its
  `version` with the one you are editing; only a version already on `main` needs a new one.
- A plugin's `name` and the marketplace `name` are stable identifiers. Renaming either breaks
  existing installs; see [`CONTRIBUTING.md`](./CONTRIBUTING.md).
- Use `${CLAUDE_PLUGIN_ROOT}` in hooks and MCP configs — the host expands those itself, and it is
  the only root variable both hosts define. In a **skill body**, write
  `${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}` instead and state the no-variable fallback, so the skill
  survives a host that is in neither column yet. Scripts should locate themselves from `__file__`
  and read only variables the plugin defines. See [`docs/compatibility.md`](./docs/compatibility.md),
  which owns the mapping.
- Skill `description` frontmatter must say when to use *and when not to use* the skill; it is the
  only text an agent sees before loading the skill.
- Documentation and plugin content are written in English.
