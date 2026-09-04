---
name: commit-craft
description: Write Conventional Commits messages from the staged diff. Use when the user asks to commit, to write or improve a commit message, or to split staged changes into logical commits.
---

# Commit Craft

Produce commit messages that describe **why** a change was made, in
[Conventional Commits](https://www.conventionalcommits.org/) form.

## Steps

1. Inspect the change set before writing anything:
   - `git status --short`
   - `git diff --staged`
   - If nothing is staged, say so and ask whether to stage everything.
2. Read the last few messages with `git log --oneline -10` and match the repository's
   existing style (scope vocabulary, casing, whether a body is customary).
3. Decide whether the staged diff is one logical change. If it mixes unrelated concerns,
   propose a split and list which files belong to each commit. Do not stage or commit
   anything on your own unless the user asked you to.
4. Write the message, attributing every model that wrote part of the staged diff — see
   [Co-authorship](#co-authorship).

## Message format

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **scope**: optional; the module, package, or area touched. Omit it rather than inventing one.
- **subject**: imperative mood, lowercase, no trailing period, at most 72 characters.
- **body**: optional; wrap at 72 columns. Explain the motivation and the trade-off, not the diff —
  the reader can already see the diff.
- **footer**: `BREAKING CHANGE: <description>` for incompatible changes, issue refs such as
  `Refs: #123` or `Closes: #123`, and the `Co-authored-by:` trailers described below.

## Rules

- One logical change per commit.
- Never describe the mechanics ("changed line 42"); describe the effect.
- A commit that only reformats code is `style`; a commit that changes behavior is never `style`.
- If the change is a revert, use `revert:` and reference the reverted commit SHA.

## Co-authorship

A commit records **who wrote the change**, not who ran `git commit`. When an agent wrote part of
the staged diff, the message carries one trailer per contributing model:

```
Co-authored-by: <model display name> <provider noreply address>
```

Write the display name the way its host names it — `Claude Opus 5`, `GPT-5.6 Sol` — reading it
from the session's own metadata rather than assuming, since a session can be switched to another
model mid-way. Every model name in this skill is a sample of that spelling, the one in the example
below included; never copy one into a message. The address belongs to the model's provider:
`noreply@anthropic.com` for Claude models, `noreply@openai.com` for OpenAI models.

- **The agent writing the message** adds its own model whenever it wrote part of the change.
- **A subagent's work** carries the subagent's model, never the parent's. A subagent committing
  its own work knows that value directly; a parent committing on its behalf copies the one the
  subagent reported, verbatim.
- **Several contributors** get one trailer each, in the order they worked. Two agents that ran on
  the same model share a single trailer — never repeat a model.
- **A model that cannot be identified** gets no trailer. Do not infer one from the diff, the
  history, or the host, and do not hold the commit back over it.
- **No trailer at all** when the human wrote the change unaided, or when the agent only reviewed
  it, ran commands, or wrote the message. Running `git commit` is not authorship.

The human stays the commit `Author`; a trailer adds a co-author and never replaces them.

## Example

```
fix(auth): refresh the session token before long uploads

Uploads over ~10 minutes failed with 401 because the token expired
mid-request. Refresh it when the remaining lifetime is under two
minutes instead of waiting for the failure.

Closes: #481
Co-authored-by: Claude Sonnet 5 <noreply@anthropic.com>
```

That trailer names one model because a real commit names one. Yours names whichever model actually
wrote the change, read from the session — not the name above.
