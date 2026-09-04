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

The scope comes from the staged paths: files sitting under one plugin, package, or module take
that directory's name, preferring a scope the history already uses, and a change spread across
unrelated areas carries none. When more than one scope fits, the skill asks instead of guessing.
Before committing, it writes the message to a file, checks that no line runs past 72 columns, and
commits that file with `git commit -F` — so the message you approved is the message that lands.

When an agent wrote part of the staged diff, the message it proposes carries a
`Co-authored-by:` trailer naming that model — the subagent's own model when a subagent wrote the
code, one trailer per model when several contributed, and none for a model the agent cannot
identify, which it never guesses at. Work you wrote yourself gets no trailer, and neither does an
agent that only reviewed the change or ran the commands. You stay the commit author either way.
