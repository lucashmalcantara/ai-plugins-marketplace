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

Every commit whose changes were written by an agent carries a `Co-Authored-By` trailer naming the
model that wrote them. The person running the session stays the commit `Author`; an agent is only
ever a co-author.

The trailer's value is the model and nothing else — not the agent's name, not a subagent's name,
not the harness:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>   # Claude Code
Co-Authored-By: <model> <noreply@openai.com>            # Codex
```

Write the model the way its host names it: `Claude Opus 5`, `Claude Sonnet 5`, `Claude Haiku 4.5`.
Read it from the session rather than assuming — a session can be switched to another model mid-way.

### Subagents

A subagent often runs on a different model than the session that spawned it: its definition can pin
one, and a spawn can override it. The trailer carries **the model the subagent actually ran on**,
never the parent's. Which of the two runs `git commit` makes no difference — the trailer records
which model wrote the code, not which one invoked git.

- **The subagent commits its own work.** It writes its own model, which it knows directly.
- **The parent commits the subagent's work.** The subagent states its model in its final report and
  the parent copies that value verbatim, instead of guessing which model the subagent got.

A subagent started fresh does not inherit the parent's context, so it may never have read this file.
When you spawn a subagent that might commit, put the rule in its prompt: commits carry
`Co-Authored-By: <its model> <noreply@anthropic.com>`. A subagent that commits without having been
told is the one way this convention silently fails.

### More than one model

One trailer per distinct model, in the order they worked. Two agents that ran on the same model
share one trailer:

```
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

### When not to add one

A commit a person wrote unaided gets no trailer. Do not add one speculatively, and do not add one
for an agent that only reviewed or ran commands without writing the change.

Nothing in the repository enforces this: no hook blocks a commit that omits the trailer, and nothing
can recover a subagent's model after the fact. The agent that did the work is the only thing that
knows, so writing the trailer is that agent's job.

## Conventions

- Every plugin change bumps `version` in both manifests and adds a `CHANGELOG.md` entry. Both hosts
  skip updates when the version string is unchanged.
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
