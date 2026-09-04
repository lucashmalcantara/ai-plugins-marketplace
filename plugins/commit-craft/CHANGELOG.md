# Changelog

All notable changes to this plugin are documented here. This project follows
[Semantic Versioning](https://semver.org/).

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
