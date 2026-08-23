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

Ask for it in plain language — "set up a note vault at ~/knowledge-base" — and the **`note-setup`**
skill takes it from there. It inspects the folder first, shows you a plan, and writes nothing until
you approve it. It handles a folder that does not exist yet, an empty one, an existing Obsidian
vault, and a folder that already holds Markdown.

The layout it creates:

```
<vault>/
├── .note-keeper.json    marker + language/timezone settings
├── notes/               the notes, flat
├── _attachments/        media referenced from notes and sessions
├── _templates/          note skeletons (a starter Base.md is written)
├── _sessions/           live capture buffers
└── .index/              generated map — INDEX.md and cache.json
```

The same thing without an agent:

```shell
python3 "$CLAUDE_PLUGIN_ROOT/scripts/vault.py" inspect ~/knowledge-base   # look, change nothing
python3 "$CLAUDE_PLUGIN_ROOT/scripts/vault.py" init ~/knowledge-base      # create what is missing
```

Both are idempotent. An existing vault with a `notes/` folder already works as-is — the marker is
optional.

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
| `note-setup` | Create a vault, adapt an existing folder, configure Obsidian. | ✅ |
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

## Obsidian (optional)

The vault is plain files, so Obsidian is a viewer over it — never a dependency. `note-setup` can
point it at the same layout, merging into `.obsidian/` without disturbing your themes or workspace:

| Setting | Value | Why |
| --- | --- | --- |
| `useMarkdownLinks` | `true` | **The load-bearing one.** Left alone, Obsidian writes `[[wikilinks]]`, which the note format forbids. |
| `newLinkFormat` | `shortest` | Produces `Target.md`, exactly the form the notes use. |
| `attachmentFolderPath` | `_attachments` | Pasted media lands where the vault expects it. |
| `newFileLocation` + `newFileFolderPath` | `folder`, `notes` | A note you create by hand in Obsidian lands in `notes/`, so the index finds it. |
| Templates folder | `_templates` | Obsidian offers the same skeletons the `note` skill does. |
| `userIgnoreFilters` | adds `_sessions/` | Capture buffers stay out of search and the graph. |

Three limits worth knowing before you rely on it:

- **Close the vault in Obsidian before configuring it.** Obsidian rewrites `.obsidian/*.json` on
  exit and will overwrite settings written underneath a running instance.
- **`INDEX.md` is not visible in Obsidian.** It lives in `.index/`, and Obsidian ignores
  dot-folders. The map is a generated artifact rather than a note, but it does mean you can only
  read it outside Obsidian.
- **The skills do not run on mobile.** Obsidian mobile reads and edits the same vault, and the
  `.obsidian/` settings travel with it, so notes you write on a phone still come out in the right
  format. But Claude Code and Codex are desktop tools: those notes join the map the next time
  `note-index` runs on a desktop.

Writing notes by hand — in Obsidian or any editor — is expected. The index keys off a content hash,
so the next `note-index` rebuild picks up whatever appeared while you were away.

## Scripts

Both are stdlib-only Python.

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

### Host portability

Nothing host-specific reaches the scripts. They locate their own directory from `__file__` and read
exactly one environment variable, `NOTE_KEEPER_VAULT`, which belongs to this plugin rather than to
any host. A test enforces that.

The one thing that cannot be host-neutral is the *first* path: a skill body has to name the plugin's
install directory before it can run anything from it, and only the host knows where that is. So the
skills open with a single line:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py"
```

Claude Code exports `CLAUDE_PLUGIN_ROOT`; Codex exports `PLUGIN_ROOT` and `CLAUDE_PLUGIN_ROOT` as an
alias. A host that exports neither still works: each skill says to take its own SKILL.md directory
and go two levels up. Supporting a new provider therefore means adding one name to that expression —
not touching the scripts, and not changing how any skill behaves. The current mapping lives in
[`docs/compatibility.md`](../../docs/compatibility.md).

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
