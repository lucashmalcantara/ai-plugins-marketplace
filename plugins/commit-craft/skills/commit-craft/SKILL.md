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
2. Read the last few messages with `git log --oneline -20` and match the repository's
   existing style — casing, whether a body is customary, and above all which scopes it
   already uses. That vocabulary decides the next step.
3. Decide whether the staged diff is one logical change. If it mixes unrelated concerns,
   propose a split and list which files belong to each commit. Do not stage or commit
   anything on your own unless the user asked you to.
4. Choose the scope from what the staged paths have in common — see
   [Choosing a scope](#choosing-a-scope).
5. Write the message, attributing every model that wrote part of the staged diff — see
   [Co-authorship](#co-authorship).
6. Check it and commit the text you checked — see
   [Before committing](#before-committing).

## Message format

```
<type>(<scope>): <subject>

<body>

<footer>
```

- **type**: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.
- **scope**: the plugin, module, package, or domain the change belongs to. Required whenever the
  staged paths point at one; omitted only for a genuinely cross-cutting change. Never invented —
  see [Choosing a scope](#choosing-a-scope).
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

## Choosing a scope

**A ticket id takes the scope when there is one.** Repositories tracked in an issue tracker put
the ticket between the parentheses, and it outranks the code area — with a ticket in play, the
area is named in the subject or the body instead:

```
fix(PROJ-1234): refresh the auth session token before long uploads
```

Look for the id in the branch name first (`git rev-parse --abbrev-ref HEAD`), then in what the
user has said. Never read one out of the diff, and never invent one: no id in sight means the
paths decide, exactly as below.

An id is a project key, a hyphen, and digits — `PROJ-1234`, `AB2-99`:

- **Written in capitals**, it is unambiguous. Use it.
- **Written in lower case** — `proj-1234-fix-login` — it is plausible, but so is an ordinary
  branch name: `note-keeper-12` has the same shape. Put the candidate to the user and let them
  confirm before it becomes the scope.

Anything else is not an id. A GitHub issue reference (`#4`), a branch named `issue-4`, or a bare
number is a footer reference, never a scope.

Without a ticket, the staged paths decide the scope, not the subject. Look at what they have in
common:

- **All under one plugin, package, or top-level module** — its directory name is the scope.
  `plugins/note-keeper/...` gives `note-keeper`; `src/billing/...` gives `billing`.
- **Spread across one domain** without a single directory — name the domain, if the history
  already recognises it.
- **Spread across unrelated areas** — the change is cross-cutting; write no scope. A
  repository-wide rename, or a build change touching everything, is the honest case for omitting
  it.

Two rules bound the choice:

- **Prefer a scope the history already uses.** The vocabulary from step 2 is evidence; a scope
  nobody has used before needs evidence of its own — a directory or package that actually exists
  in the diff. Never coin a scope to describe the change; that is what the subject is for.
- **When more than one scope is plausible, ask.** List the candidates with the files behind each
  and let the user pick, rather than guessing and committing.

Those two rules govern the paths, not the ticket: an id that is actually the ticket for this work
is evidence enough on its own, however the history reads.

Omitting the scope is a decision about the diff, not a way out of making one. If there is a ticket,
it is the scope; if the staged files sit under a single directory, that directory is the scope.

## Before committing

Write the finished message to a file and check it there. Every rule below is a rule this skill
already states; the point of the file is that the text can be checked and then committed
unchanged.

```shell
awk 'length > 72 {print FILENAME": line "FNR" is "length" chars"}' <message-file>
```

Silence means every line fits. Any output is a line to rewrap before going further.

Then read the message once against the rest:

- the type is one of the types listed above;
- the scope follows [Choosing a scope](#choosing-a-scope) — present when the paths point at one;
- the subject is imperative, lowercase, and carries no trailing period;
- the body explains motivation or effect, and never narrates the diff line by line;
- a blank line separates subject, body, and footer;
- `BREAKING CHANGE:` is present if the change is incompatible.

Commit the file itself:

```shell
git commit -F <message-file>
```

Never retype the message into `git commit -m`. Retyping is where a checked message and a committed
message drift apart, and the commit is the copy that survives.

## Co-authorship

A commit records **who wrote the change**, not who ran `git commit`. When an agent wrote part of
the staged diff, the message carries one trailer per contributing model:

```
Co-authored-by: <model display name> <provider noreply address>
```

The value is the model and nothing else — not the agent's name, not a subagent's name, not the
harness. Write the display name the way its host names it — `Claude Opus 5`, `GPT-5.6 Sol` —
reading it from the session's own metadata rather than assuming, since a session can be switched
to another model mid-way. Every model name in this skill is a sample of that spelling, the one in
the example below included; never copy one into a message. The address belongs to the model's
provider: `noreply@anthropic.com` for Claude models, `noreply@openai.com` for OpenAI models.

- **The agent writing the message** adds its own model whenever it wrote part of the change.
- **A subagent's work** carries the subagent's model, never the parent's. A subagent committing
  its own work knows that value directly; a parent committing on its behalf copies the one the
  subagent reported, verbatim. A subagent started fresh never read this skill, so spawn one that
  might commit with the rule already in its prompt — nothing recovers which model it ran on after
  the fact.
- **Several contributors** get one trailer each, in the order they worked. Two agents that ran on
  the same model share a single trailer — never repeat a model.
- **A model that cannot be identified** gets no trailer. Do not infer one from the diff, the
  history, or the host, and do not hold the commit back over it.
- **No trailer at all** when the human wrote the change unaided, or when the agent only reviewed
  it, ran commands, or wrote the message. Running `git commit` is not authorship.

The human stays the commit `Author`; a trailer adds a co-author and never replaces them.

## Examples

Every staged file lived under `src/auth/`, so the scope is `auth`:

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

The same change on a branch named `PROJ-1234-fix-login`. Every file still sits under `src/auth/`,
but the ticket outranks it, so `auth` moves into the subject:

```
fix(PROJ-1234): refresh the auth session token before long uploads

Uploads over ~10 minutes failed with 401 because the token expired
mid-request. Refresh it when the remaining lifetime is under two
minutes instead of waiting for the failure.

Refs: PROJ-1234
```

This one raised the Node version in the CI workflow, the Dockerfile, and three package manifests
at once. No directory contains the change and no ticket is in play, so it carries no scope:

```
build: raise the minimum Node version to 20

18 reached end of life in April, and the test matrix had been pinning
20 for months anyway. Make the manifests say what CI already runs.
```
