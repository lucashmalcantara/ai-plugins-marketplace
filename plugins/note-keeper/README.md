# Note Keeper

A personal knowledge vault of interlinked plain-Markdown notes — _Obsidian_-inspired, but decoupled
from any app. Each note is a `.md` file with **no frontmatter**: the filename is the title, tags are
inline `#tags`, and relationships are ordinary Markdown links between notes. The value is in the
connections, not in a folder hierarchy.

| | |
| --- | --- |
| Components | 9 skills, 2 scripts |
| Works on | Claude Code, Codex |
| Requires | Python 3.9+; `ripgrep` optional (falls back to `grep`) |

## Install

**Claude Code**

```shell
/plugin marketplace add lucashmalcantara/ai-plugins-marketplace
/plugin install note-keeper@lucashmalcantara-plugins
```

**Codex**

```shell
codex plugin marketplace add lucashmalcantara/ai-plugins-marketplace
```

Then enable **Note Keeper** from `/plugins`.

## Set up a vault

The plugin needs to know where your vault is. Create one:

```shell
python3 "$CLAUDE_PLUGIN_ROOT/scripts/vault.py" init ~/knowledge-base
```

That creates `notes/`, `_attachments/`, `_templates/`, `_sessions/`, `.index/`, a starter
`_templates/Base.md`, and a `.note-keeper.json` marker. An existing vault with a `notes/` folder
already works as-is — the marker is optional.

Every skill resolves the vault in this order:

1. `$NOTE_KEEPER_VAULT`, if set — the reliable choice when you work from other repositories:
   ```shell
   export NOTE_KEEPER_VAULT=~/knowledge-base
   ```
2. the nearest ancestor of the working directory holding a `.note-keeper.json`;
3. the nearest ancestor holding a `notes/` folder.

A marked vault always beats a bare `notes/` folder found lower down, so an unrelated repository that
happens to contain `notes/` never shadows the real vault. If nothing resolves, the skills stop and
say so rather than guessing.

### `.note-keeper.json`

Only prose settings are configurable; the folder layout is a fixed convention the skills rely on.

```json
{
  "language": "pt-BR",
  "timezone": "-03:00"
}
```

`language` is what notes and index summaries are written in. `timezone` is the ISO 8601 offset
stamped on session entries. Both are optional and default to the values above.

## Skills

| Skill | What it does | Writes? |
| --- | --- | :---: |
| `note` | Create or edit a note. **Source of truth for the note format.** | ✅ |
| `note-view` | Display a note, whole or in part. | — |
| `note-search` | Find notes by keyword, phrase, tag, or backlink. | — |
| `note-link` | Suggest related notes to link from a note. | — |
| `note-remove` | Delete a note plus the attachments it orphans. | ✅ |
| `note-index` | Regenerate `.index/INDEX.md`, the vault map. | ✅ |
| `note-template` | Create a template, or convert a note into one. | ✅ |
| `note-session` | Capture live notes during an event, then distil them. | ✅ |
| `note-migrate` | Import an external Markdown folder, consolidating by topic. | ✅ |

Ask in plain language ("anota isso aí", "which notes mention rate limiting?") and the right skill
fires from its description. To invoke one explicitly:

- Claude Code — `/note-keeper:note`, `/note-keeper:note-search`, …
- Codex — `$note`, `$note-search`, …

The skills are namespaced with a `note-` prefix on purpose: Claude Code scopes them under the plugin
(`/note-keeper:note-view`), but Codex exposes skills in one flat namespace, where a skill called
`view` or `index` would be far too generic.

### How they fit together

`note` owns the note format; nothing else writes a note body. `note-index` owns `INDEX.md`; nothing
else writes it, and it is never hand-edited. Every other skill routes through those two:

```
note-session ──distil──┐
note-migrate ──import──┤
                       ├──> note ──> note-index ──> .index/INDEX.md
note-remove ──cleanup──┘                                   │
                                                           │ read-only
note-view · note-search · note-link ───────────────────────┘
```

## Scripts

Both are stdlib-only Python and are invoked by the skills through `${CLAUDE_PLUGIN_ROOT}`.

- **`scripts/vault.py`** — resolves the vault and its settings, printing them as JSON; `init`
  scaffolds a new one.
- **`scripts/generate_index.py`** — the deterministic half of `note-index`: parses inline tags and
  outbound links, hashes bodies to reuse cached summaries, and renders `INDEX.md`. `scan` reports
  which notes need a fresh summary; `write --summaries <file>` merges the ones the agent wrote and
  updates `.index/cache.json`.

Run their tests with:

```shell
python3 -m unittest discover -s plugins/note-keeper/scripts -p 'test_*.py'
```

## Behaviour notes

- **No skill ever commits.** Writing and committing are separate steps; the skills stop and hand the
  commit back to you. The same marketplace ships `commit-craft` if you want help writing it.
- **The destructive ones ask first.** `note-remove` shows the note, its backlinks, and the
  attachments it would orphan, then waits for confirmation. `note-migrate` presents one plan
  covering every source file and writes nothing until you approve it — and it never modifies the
  source folder.
- **A link to a note that doesn't exist yet is valid** — it marks a topic worth writing later, so
  `note-remove` leaves dangling backlinks alone by default.
- **Only `notes/` is indexed.** `_templates/`, `_sessions/`, and `_attachments/` are deliberately out
  of scope, so `INDEX.md` stays a map of actual knowledge.
