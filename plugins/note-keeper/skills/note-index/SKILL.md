---
name: note-index
description: Regenerate INDEX.md for the note-keeper vault — a full rebuild, or a single note after it was created or edited. Runs the deterministic generator and supplies the one-line summaries it cannot write itself. Use after any note is added, changed, or removed, or when the vault map looks stale. Do not use to search the vault (note-search), to suggest links (note-link), or to edit note bodies (note) — this skill only writes INDEX.md, and never by hand.
---

# note-index

## Overview

Regenerates `INDEX.md` in `.index/`: one line per note, alphabetical, with a summary, tags, and
relationships. The heavy lifting (parsing tags/links, hashing, diffing against the cache, deciding
which notes still need a summary, rendering the file) is done by the deterministic generator script
shipped with this plugin at `scripts/generate_index.py` in the plugin root. This skill's job is to
run that script and supply the one thing it can't produce itself: the LLM-written summary for each
new or changed note.

**Scope guard:** the generator only reads `notes/*.md`. It never touches `_templates/`,
`_attachments/`, or `_sessions/` — those are not indexed.

The note format and the vault's writing conventions are owned by the `note` skill — this skill does
not restate them. It only reads note bodies to summarize them.

## Resolve the vault first

Every path below is relative to the **vault root**. Resolve it once, before anything else:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py"
```

Those two variables are what today's hosts call this plugin's own install directory. On a host that
exports neither, take the directory holding this SKILL.md and go two levels up: the scripts live at
`scripts/` in the plugin root, and they read no host variable themselves.

It prints JSON: `root`, the absolute folder paths (`notes`, `attachments`, `templates`,
`sessions`, `index_dir`, `index_file`), and the vault's `language` (default `pt-BR`) and
`timezone` (default `-03:00`). A non-zero exit means no vault was found — tell the user to set
`NOTE_KEEPER_VAULT`, or to set one up with the `note-setup` skill.
**Never guess where the vault is.**

Pass that `root` to the generator explicitly with `--root` in every call below, so the run never
depends on the working directory.

## Workflow (full rebuild)

1. **Scan.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/generate_index.py" --root "<root>" scan
   ```
   This prints a JSON array with one entry per note under `notes/` (`title`, `path`, `tags`,
   `relationships`, `hash`, `summary`, `needs_summary`). Notes whose content hash matches the cache
   come back with `needs_summary: false` and their previous `summary` already filled in — skip
   those.

2. **Summarize.** For every entry with `needs_summary: true`, read `notes/<title>.md` and write
   **one dense line in the vault's `language`** (default `pt-BR`): what the note is about plus its
   key point. No trailing period needed, no multi-line summaries.

3. **Stage the summaries.** Write a JSON object mapping `path` → `summary` (only for the entries
   from step 2) to a temp file in the session scratchpad, e.g. `<scratch>/index-summaries.json`:
   ```json
   { "notes/Event-Driven Architecture.md": "Resumo de uma linha…" }
   ```
   The keys are the `path` values exactly as the scan printed them — vault-relative, not absolute.

4. **Write.** Run:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/generate_index.py" --root "<root>" write --summaries <temp.json>
   ```
   This re-scans, merges the new summaries with the cached ones, writes `.index/INDEX.md`, and
   updates `.index/cache.json`. It exits with an error if any entry is still missing a summary — if
   that happens, go back to step 2.

5. **Show the diff.** If the vault is a git repository, run `git -C "<root>" diff .index/INDEX.md`
   (or `git -C "<root>" status` if it's untracked) and show it to the user. If it isn't a git
   repository, say how many lines changed instead.

6. **Hand off the commit.** Stop here. **Never commit automatically** — tell the user the index is
   updated and let them commit, including the `.index/` change. (The same marketplace ships a
   `commit-craft` skill for writing that commit, if they want it.)

## Workflow (single note)

Same steps, but scope the summary work to the note that changed:

1. Run `scan` as above — it still reports on the whole vault, but only the target note (new or
   edited) should come back with `needs_summary: true`. If others do too, something else changed;
   handle those as well or investigate before proceeding.
2. Summarize just that note.
3. Write a temp JSON with just that one `path: summary` pair.
4. Run `write --summaries <temp.json>` and show the `INDEX.md` diff.
5. **Hand off the commit**, same as in the full rebuild above.

## Rules

- **Never hand-edit `INDEX.md`.** It's generated; the file's own header says as much. Always go
  through this workflow, even for a one-line fix.
- **Summaries are one line, in the vault's `language`.** Match the language the notes are written in.
- **Don't invent summaries for unchanged notes.** Only supply summaries for entries the scan marks
  `needs_summary: true` — the generator reuses cached summaries for everything else.
- **Always pass `--root`.** The generator can resolve the vault on its own, but passing the root the
  skill already resolved keeps a run from silently indexing a different vault.
- **Never commit.** Indexing and committing are separate steps.
- Clean up the temp summaries file when done; it's scratch, not part of the vault.

## Cross-references

- The **`note` skill** owns the note format and triggers this skill's single-note mode after every
  create or edit. This skill never edits note bodies.
- The **`note-remove` and `note-migrate` skills** trigger a full rebuild after they write. This skill
  doesn't know or care which one called it.
- The **`note-search` and `note-link` skills** only *read* `INDEX.md` — they never regenerate it.

## Common mistakes

- Editing `INDEX.md` directly instead of running `write` — the next run will silently overwrite it.
- Writing summaries in the wrong language, or in more than one line.
- Passing summaries for notes that don't need one — harmless (the generator only uses what it needs)
  but wasted work; check `needs_summary` first.
- Keying the summaries JSON by absolute path or by title instead of the scan's vault-relative `path`
  — the merge is by `path`, so a mismatched key silently does nothing and the write then fails.
- Restating the note format conventions here — that's the `note` skill's job, not this one's.
- Committing the index change automatically — stop after showing the diff and hand off.
- Running the generator without `--root` from an unrelated working directory, so it resolves some
  other vault (or none at all).
