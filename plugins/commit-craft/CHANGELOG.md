# Changelog

All notable changes to this plugin are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-04

### Changed

- Scope selection: the scope was optional with no procedure for deciding it, which let a change
  belonging to an obvious domain commit without one. It now follows from the staged paths — a
  plugin, package, or module directory names the scope, preferring one the history already uses,
  and only a genuinely cross-cutting change goes without. Ambiguous cases are put to the user
  rather than guessed at.
- Ticket ids outrank the code area: an id read from the branch name or from the conversation takes
  the scope — `fix(PROJ-1234): ...` — and the area moves into the subject. An id written in lower
  case is confirmed with the user first, an ordinary branch name having the same shape, and one is
  never invented where none exists.

### Added

- A pre-commit check: the message is written to a file, verified line by line against the rules
  the skill states, and committed with `git commit -F` so the text that was checked is the text
  that lands.

## [0.1.1] - 2026-09-04

### Fixed

- Co-authorship: the message now carries a `Co-authored-by:` trailer for each model that wrote
  part of the staged diff, so attribution follows the agent that produced the change rather than
  the one that ran `git commit`. A subagent's work is attributed to the subagent's own model, and
  spawning one that might commit means putting the rule in its prompt — nothing recovers which
  model it ran on afterwards.

## [0.1.0] - 2026-08-23

### Added

- `commit-craft` skill: writes Conventional Commits messages from the staged diff and
  proposes a split when the staged changes mix unrelated concerns.
