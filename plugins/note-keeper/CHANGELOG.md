# Changelog

All notable changes to this plugin are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-08-23

### Added

- `note-setup` skill: creates a vault in a new or existing folder, adapts a folder
  that already holds Markdown, and optionally points Obsidian at the same layout.
- `note` skill: creates or edits notes; the note-format source of truth.
- `note-view` skill: displays a note in read-only mode.
- `note-search` skill: finds notes by keyword, tag, or backlink.
- `note-link` skill: suggests related notes to link.
- `note-remove` skill: deletes a note and the attachments it orphans.
- `note-index` skill: regenerates `INDEX.md`.
- `note-template` skill: creates or converts a note template.
- `note-session` skill: captures live notes during an event, later distilled.
- `note-migrate` skill: imports external Markdown notes.
- `scripts/vault.py`: resolves the vault root from `$NOTE_KEEPER_VAULT`, a
  `.note-keeper.json` marker, or a `notes/` folder up the tree. `inspect`
  classifies a folder without touching it, `init` creates what is missing, and
  `obsidian` merges the Obsidian settings; all three take `--dry-run`.
- `scripts/generate_index.py`: the deterministic index generator behind
  `note-index`.
- Host-neutral scripts: they locate themselves from `__file__` and read only
  `NOTE_KEEPER_VAULT`, enforced by a test. The one host-specific detail is the
  line each skill uses to resolve the plugin root,
  `${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}`, with a documented fallback for a host
  that exports neither.
