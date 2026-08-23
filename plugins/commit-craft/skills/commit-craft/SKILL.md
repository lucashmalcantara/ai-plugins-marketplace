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
4. Write the message.

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
- **footer**: `BREAKING CHANGE: <description>` for incompatible changes, and issue refs
  such as `Refs: #123` or `Closes: #123`.

## Rules

- One logical change per commit.
- Never describe the mechanics ("changed line 42"); describe the effect.
- A commit that only reformats code is `style`; a commit that changes behavior is never `style`.
- If the change is a revert, use `revert:` and reference the reverted commit SHA.

## Example

```
fix(auth): refresh the session token before long uploads

Uploads over ~10 minutes failed with 401 because the token expired
mid-request. Refresh it when the remaining lifetime is under two
minutes instead of waiting for the failure.

Closes: #481
```
