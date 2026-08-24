---
name: note-link
description: Use when finding related notes to link from a note. Suggests inline links using
  INDEX.md; does not write. Do not use to actually insert a link into a note's body (that is note)
  or to retrieve notes matching a keyword/tag/topic across the vault (that is note-search).
---

# note-link

## Overview

Suggests related notes to link from a given note, using `INDEX.md` as the map of the vault. **This
skill only proposes — it never edits a note.** Applying a suggestion is the user's call, done via
the `note` skill (edit workflow).

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

## Workflow

1. **Read the target note** (`notes/<Title>.md`). Note its existing outbound links (so you don't
   re-suggest something it already links to), its inline `#tags`, and the gist of its content.
2. **Read `INDEX.md`** for the rest of the vault — each line gives another note's title, summary,
   tags, and relationships. If `INDEX.md` is missing or looks stale for the target note (its
   summary/tags don't match what's actually in the note), tell the user to run the `note-index`
   skill first; don't guess at a stale map.
3. **Score candidates.** For every other note in the index, judge relatedness by:
   - **Tag overlap** — shared `#tags` between the target note and the candidate (strongest signal).
   - **Summary overlap** — topical similarity between the target note's content and the candidate's
     one-line summary.
   - Skip notes the target already links to, and skip the target note itself.
4. **Propose links, ranked** highest-relatedness first. For each suggestion give:
   - The exact inline link as it would appear in the body: `[text](<Note.md>)` — link text is your
     choice of anchor phrase, destination is the candidate's filename with no `notes/` prefix,
     wrapped in angle brackets (required whenever the filename has a space).
   - A one-line reason (which tags/summary overlap drove the suggestion).
5. **Stop there.** Present the ranked list to the user. If they want any applied, hand off: they (or
   you, on their explicit instruction) use the **`note` skill's edit workflow** to actually insert
   the link text into the note's body and re-run the single-note `note-index` update — this skill
   does neither.

## Rules

- **Never edit notes directly.** This skill reads the target note and `INDEX.md`; it writes nothing,
  not even with the user's permission inline — route any actual edit through the `note` skill.
- **Relationships are outbound links, not a separate list.** Don't propose adding a "Related notes"
  section or any frontmatter — a suggested link only makes sense as inline prose/anchor text the
  user weaves into the body, per the `note` skill's format.
- **Links follow the note format exactly**: relative to `notes/` (no `notes/` prefix, since notes
  live flat), and wrapped in angle brackets whenever the destination has a space, e.g.
  `[request throttling](<Rate Limiting.md>)`.
- A suggestion pointing at a note that doesn't exist yet is out of scope here — this skill only
  suggests links between notes that are already in `INDEX.md`.

## Cross-references

- The **`note` skill** owns the note format and is the only skill that writes link text into a
  note's body. This skill only recommends what to link; applying a suggestion always goes through
  `note`'s edit workflow.
- The **`note-index` skill** owns `INDEX.md` (generation, scan scope, caching). This skill only
  reads it — it never regenerates or hand-edits it.

## Common mistakes

- Editing the note to insert a suggested link — this skill is suggestion-only; that step belongs to
  the `note` skill.
- Suggesting a link the note already has — check the target note's existing outbound links first.
- Writing an unranked list — always order suggestions by relatedness (tag overlap first, then
  summary similarity).
- Adding a "Related notes" section instead of an inline link — relationships are inline links in
  prose, never a separate list.
- Suggesting links using a stale `INDEX.md` — if the map doesn't reflect the target note's current
  tags/content, send the user to the `note-index` skill first instead of guessing.
