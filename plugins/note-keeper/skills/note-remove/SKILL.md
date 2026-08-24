---
name: note-remove
description: Use when deleting a note from the vault. Removes the note file, cleans up the
  attachments the deletion orphans, reports backlinks, and rebuilds the index — it never
  auto-commits and never edits other notes without approval. Do not use it to edit or trim a note
  without deleting it (that is note), or to bulk-import notes into the vault (that is note-migrate).
---

# note-remove

## Overview

Deletes a note from `notes/` and cleans up only what that deletion leaves behind. **This skill is
destructive-with-consent: it removes exactly one note per run and never deletes anything the user
hasn't confirmed.** It reports the note's backlinks and removes any attachment the note orphans, but
it **never rewrites another note's content without approval, never hand-edits the index, and never
commits** — committing is a separate, explicit step.

This skill does not own the note format or `INDEX.md`. It resolves and reads notes through the same
conventions the `note` skill defines, and rebuilds the index through the `note-index` skill (see
Cross-references). It adds the one thing those skills don't: safely retiring a note and everything
that existed only to serve it.

## Resolve the vault first

Every path below is relative to the **vault root**. Resolve it once, before anything else:

```bash
python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py"
```

Those two variables are what today's hosts call this plugin's own install directory. On a host that
exports neither, take the directory holding this SKILL.md and go two levels up: the scripts live at
`scripts/` in the plugin root, and they read no host variable themselves.

It prints JSON: `root`, the absolute folder paths (`notes`, `attachments`, `templates`,
`sessions`, `index_dir`, `index_file`), and the vault's `language` and `timezone` — already
resolved, so use what it prints. A non-zero exit means no vault was found — tell the user to set
`NOTE_KEEPER_VAULT`, or to set one up with the `note-setup` skill.
**Never guess where the vault is.**

## Resolving the target

The argument names the note to delete — resolve it the same way `note-view` and `note-search` do:

- **A path** — `@notes/<Title>.md` or an explicit vault-relative path. Use it directly.
- **A name or topic** — resolve against `notes/*.md` by filename (the title, with spaces). If more
  than one note matches, list the candidates and ask which. If none matches, say the note doesn't
  exist — there is nothing to remove; stop. **Never guess a target** — deleting the wrong note is
  expensive.

## Workflow

1. **Show the note first.** Read the target and show the user what will be lost — its body, tags, and
   links — before anything is deleted; reuse the `note-view` skill's display. Deletion is not done
   sight-unseen.
2. **Find the backlinks.** Read `.index/INDEX.md` and collect every note whose `relationships:`
   column names the target — those are the notes that link to it (the index parses links
   authoritatively; prefer it over grepping bodies). Report the list. Once the target is gone, each of
   these links points at a note that no longer exists — which is **valid** here: a link to a
   non-existent note is an accepted placeholder for "a topic yet to develop" (the `note` skill's
   format rule). So the default is to **leave them**; offer to strip them.
3. **Find the orphaned attachments.** For each `![](<../_attachments/…>)` the note embeds, check
   whether any *other* note references the same file — and whether any capture buffer under
   `_sessions/` does, since `_attachments/` is shared between notes and sessions. Media referenced
   **only** by the target becomes orphaned by the deletion; media still used by another note or
   session does not. List which attachments will be removed and which will be kept.
4. **Confirm — the approval gate.** Show the whole plan in one place: the note to delete, its
   backlinks (kept as placeholders by default, or stripped if the user asks), and the orphaned
   attachments to remove. **Wait for explicit confirmation.** Nothing is deleted before this.
5. **Delete.** Remove the note file and each orphaned attachment from disk. If the vault is a git
   repository, use `git rm` for tracked files so the deletions are staged and ready for the user's
   own commit, and `rm` for anything untracked; a vault that isn't a git repository just uses `rm`.
   Never remove an attachment still referenced by another note.
6. **Strip backlinks only if approved.** For each backlink the user chose to clean, edit that source
   note through the `note` skill's Edit workflow — soften the link to plain text or remove it,
   integrating the change so the sentence still reads. Leave every backlink the user chose to keep.
   **Skip `note`'s single-note index step** for these edits; the full rebuild in step 7 covers them
   (running it per note would only leave interim `INDEX.md` diffs — the same reason `note-migrate`
   skips it).
7. **Rebuild the index.** Run the `note-index` skill (full rebuild) so the removed note's line is
   dropped and any backlink edits are reflected. **Never hand-edit `INDEX.md`.**
8. **Hand off the commit.** Stop here. **Never commit automatically** — tell the user the removal
   (and the index rebuild) is ready, and let them commit. (The same marketplace ships a
   `commit-craft` skill for writing that commit, if they want it.)

## Rules

- **Destructive — always confirm.** A run deletes files; never delete before the user confirms the
  plan in step 4.
- **Remove only what the deletion orphans.** The note itself, plus attachments referenced by nothing
  else. An attachment still used by another note — or by a `_sessions/` buffer — stays.
- **Don't touch other notes without approval.** Backlinks are stripped only when the user asks;
  otherwise they remain as valid placeholder links.
- **Never hand-edit `INDEX.md`.** Route the rebuild through the `note-index` skill — deleting a note
  makes the map stale.
- **Never auto-commit.** Deleting and committing are separate steps here — stop after the index
  rebuild and let the user commit; this plugin ships no commit skill of its own (the `commit-craft`
  skill from the same marketplace is an optional way to write that commit).

## Cross-references

- The **`note` skill** owns the note format and the Edit workflow — resolve the target by its
  filename-title and strip approved backlinks through it. This skill decides *what* to delete; it
  changes other note bodies only via `note`. It is also the vault's writing-conventions source of
  truth (language, tags, links) — this skill follows those conventions without restating them.
- The **`note-index` skill** owns `INDEX.md` (generation, scan scope, caching). This skill triggers a
  full rebuild in step 7 — it never edits `INDEX.md` directly.
- The **`note-view` skill** displays the note in step 1 — this skill reuses it to show what will be
  lost.
- The **`note-search` skill** answers the inverse question (what links here, or where a note is);
  reach for it when the target or its backlinks need locating first.

## Common mistakes

- Deleting the note before the user has confirmed the plan — the approval gate in step 4 is not
  optional.
- Removing an attachment another note or session still references — only media the deletion *orphans*
  is removed; check every embed against the rest of the vault (`notes/` and `_sessions/`) first.
- Stripping backlinks from other notes silently — a dangling link is valid here; only clean the ones
  the user approved.
- Hand-editing `INDEX.md` or skipping the rebuild — a removed note leaves the map stale; route it
  through the `note-index` skill.
- Committing the deletion automatically — stop after the index rebuild and tell the user to commit;
  this plugin never commits on its own.
- Guessing which note to delete when the name is ambiguous — list candidates and ask; deleting the
  wrong note is costly.
