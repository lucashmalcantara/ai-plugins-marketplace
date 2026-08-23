# Contributing

## Adding a plugin

1. **Scaffold it.**

   ```shell
   make new NAME=my-plugin
   ```

2. **Write it.** Start with the skill — see [authoring plugins](./docs/authoring-plugins.md) and the
   [compatibility matrix](./docs/compatibility.md) for what each host supports.

3. **Test it in both CLIs.** See [testing](./docs/testing.md). A plugin that has never been run is
   not ready for review.

4. **Regenerate and validate.**

   ```shell
   make sync
   make check
   ```

5. **Commit the generated files** (`.claude-plugin/marketplace.json`,
   `.agents/plugins/marketplace.json`, `PLUGINS.md`) along with your plugin. CI fails if they are
   stale.

## Review checklist

- [ ] Plugin directory name is kebab-case and matches `name` in both manifests.
- [ ] Both manifests declare the same `version`, in semver.
- [ ] Skill `description` says **when to use and when not to use** the skill, not just what it does.
- [ ] Skill body is a procedure with concrete commands; long reference material is in `references/`.
- [ ] Every path referenced from a manifest exists.
- [ ] Scripts, hooks, and MCP servers use `${CLAUDE_PLUGIN_ROOT}` rather than relative paths.
- [ ] `README.md` states which hosts it supports and what it requires on the machine.
- [ ] `CHANGELOG.md` has an entry for this version.
- [ ] The plugin was actually run in Claude Code and in Codex (or `targets` says why not).

## Changing an existing plugin

Bump `version` in **both** manifests. Both hosts skip the update when the version string is
unchanged, so a fix shipped without a bump reaches nobody.

## Renaming or removing a plugin

A plugin's `name` is its stable identifier — users reference it in their settings and install
commands, so changing it breaks every existing install. To change only the label, set `displayName`
and leave `name` alone.

If a rename or removal is unavoidable, add a `renames` entry to the Claude Code catalog so existing
users migrate instead of hitting `plugin-not-found`:

```json
"renames": { "old-name": "new-name", "removed-plugin": null }
```

`renames` is not generated — add it to `scripts/_marketplace.py` in `build_claude_catalog`, or keep
it in `marketplace.config.json` and pass it through, so it survives the next `make sync`.

## Never rename the marketplace

`marketplace.config.json`'s `name` is what users type after `@` when installing, and what their
settings record. Changing it orphans every existing install.

## Tooling

The scripts under `scripts/` are Python 3, standard library only — no dependencies to install, and
they run on the system Python that ships with macOS and on any CI image.

| Command | What it does |
| --- | --- |
| `make validate` | Validate the marketplace and every plugin |
| `make sync` | Regenerate the catalogs and `PLUGINS.md` |
| `make check` | Fail on stale generated files, then validate — what CI runs |
| `make new NAME=x` | Scaffold `plugins/x` |
