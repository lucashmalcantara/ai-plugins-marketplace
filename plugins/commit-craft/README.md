# Commit Craft

Writes [Conventional Commits](https://www.conventionalcommits.org/) messages from your staged diff,
and flags staged changes that should be split into separate commits.

| | |
| --- | --- |
| Components | 1 skill (`commit-craft`) |
| Works on | Claude Code, Codex |
| Requires | `git` on `PATH` |

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

Then enable **Commit Craft** from `/plugins`.

## Use

Ask in plain language ("write a commit message for what I staged"), or invoke the skill directly:

- Claude Code — `/commit-craft:commit-craft`
- Codex — `$commit-craft`

## Behaviour notes

The skill reads `git status`, `git diff --staged`, and recent `git log` history to match the
repository's existing commit style. It never stages or commits on its own unless you ask it to.
