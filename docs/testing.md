# Testing a plugin locally

Run both hosts against the working tree before publishing. Neither needs the marketplace to be
pushed anywhere — both accept a local path.

## Static checks

```shell
make check
```

Runs `scripts/sync_marketplaces.py --check` (are the generated files current?) and
`scripts/validate.py` (manifests, skills, referenced paths, version agreement).

If the Claude Code CLI is installed, it has its own validator:

```shell
claude plugin validate .                              # the marketplace catalog
claude plugin validate ./plugins/my-plugin --strict   # one plugin, flagging unknown fields
```

`--strict` catches typos in manifest field names, which are otherwise silently ignored.

## Claude Code

```shell
/plugin marketplace add ./            # from the repository root
/plugin install my-plugin@lucashmalcantara-plugins
/reload-plugins                       # if the install summary asks for it
/my-plugin:my-skill
```

Useful while iterating:

- `/plugin details my-plugin` — component inventory and the token cost the plugin adds.
- `/plugin marketplace update lucashmalcantara-plugins` — re-read the catalog after editing it.
- Installs are cached under `~/.claude/plugins/cache`, so bump `version` (or uninstall and
  reinstall) when a change does not seem to take effect.

## Codex

```shell
codex plugin marketplace add ./       # from the repository root
codex plugin marketplace list
```

Then open `/plugins` in Codex, enable the plugin, start a new session, and invoke the skill with
`$my-skill`. `codex plugin marketplace upgrade` re-reads the catalog after edits.

## What to actually check

- The skill fires **from a natural request**, not only from an explicit invocation — if it does not,
  the `description` is too vague about *when* to use it.
- It does not fire on unrelated requests.
- Every command in the skill body runs as written on a clean checkout.
- Hooks and MCP servers resolve their paths through `${CLAUDE_PLUGIN_ROOT}`, not relative paths.
- The plugin behaves the same on both hosts, or its README says where it differs.
