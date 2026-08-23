---
name: note
description: Create or edit a note in the note-keeper vault, optionally targeting an existing note to add content to. The source of truth for the note format — pure Markdown with no frontmatter, tags written inline in the body, relationships as angle-bracketed Markdown links. Use when the user wants to write down, capture, or amend knowledge in their vault. Do not use to display a note (note-view), to find one (note-search), to propose links without writing them (note-link), to delete one (note-remove), or to bulk-import an external Markdown folder (note-migrate).
---

# note

## Overview

Creates and edits notes under `notes/`. **This skill is the single source of truth for the note
format** — every other skill that touches note bodies (`note-index`, `note-link`, `note-session`,
`note-migrate`) points here instead of restating the rules.

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
`NOTE_KEEPER_VAULT`, or to run the same script with `init <path>`.
**Never guess where the vault is.**

## Note format (source of truth)

A note is a **pure Markdown file with no frontmatter** — the file is just its content.

- **Filename = the title, with spaces**, e.g. `notes/Repasse Custos.md`. There is no `title` field;
  the filename *is* the title. Avoid parentheses in new filenames (existing ones with parentheses
  still work via angle brackets — see links below).
- **Body is in the vault's `language`** (default `pt-BR`). Terms foreign to that language — English
  terms in a pt-BR vault — are written in _italics_ (e.g. _trade-off_, _deadline_).
- **Tags are inline `#tag`**, written directly in the body wherever relevant. A trailing line of
  tags at the end of the note is a fine convention:
  ```markdown
  #post-pricing #seller-agreements
  ```
  A tag is `#` immediately followed by a letter (nesting with `-`/`/` is allowed, e.g.
  `#post-pricing/custos`). `# Heading` (space after `#`) is a heading, not a tag — don't confuse the
  two. Don't tag inside code spans/fences or as part of a URL fragment.
- **Prefer a link over a tag for a relationship.** If the thing you'd tag has its own note, reference
  it with a link instead — inline, or via a `## Referências` section — not `#fury`. Relationships
  between notes are carried by links; reserve tags for genuine categories or facets that have no note
  of their own (e.g. `#dados-sensiveis`, `#runbook`, `#pessoas`). Use a tag only when it really adds a
  facet a link can't.
- **Relationships are Markdown links to other notes**, inline in the prose wherever the text
  naturally names the other note — a note's relationships *are* the notes it links to:
  ```markdown
  ...contratos de [Seller Agreements](<Seller Agreements.md>), gerindo a escala de
  [transações](<Payment.md>)...
  ```
  When the relationship is real but the prose gives no natural anchor (e.g. a how-to whose subject
  note is never named in the text), put the link in a trailing **`## Referências`** section instead
  of forcing an artificial mention or leaving only a tag:
  ```markdown
  ## Referências

  - [Fury](<Fury.md>)
  ```
  Prefer inline; use `## Referências` only as that fallback, and never repeat there a link that
  already appears inline — a relationship lives in exactly one place.
  - Links are **relative to the note itself** (notes live flat in `notes/`, so no `notes/` prefix —
    just the target filename).
  - **Wrap the destination in angle brackets `<...>`** whenever the filename has a space (or other
    characters CommonMark can't take unbracketed) — `[text](<Other Note.md>)`. This is required, not
    optional: an unbracketed destination cannot contain spaces.
  - A link to a note that doesn't exist yet is acceptable — it flags a topic to develop later.

No other metadata exists. Do not add frontmatter, a `title:` field, a `tags:` list, or a `rel:`
list — all of that lives inline in the body instead.

## Choosing the destination

This skill may be called with or without a **target note** — an existing note to add the content to.
Resolve which workflow to run before writing:

- **Target given** — the user references an existing note, either as a file path (`notes/<Title>.md`)
  or by naming it in the request. Go straight to the **Edit workflow** on that note.
- **No target, but a bare title with no content** (e.g. "note: Repasse Custos") — this is an
  unambiguous **create**. Skip the matching below and run the **Create workflow**.
- **No target, with content to place** — decide between an existing note and a new one *before*
  writing:
  1. Consult `.index/INDEX.md` (the vault map) for a note **on the same topic** as the content — the
     same merge-vs-create judgment the `note-migrate` skill applies in its Step 2 (topic and tag
     overlap with a note's summary; filename similarity is only a weak hint). Don't restate the
     scoring here — apply it.
  2. If a note clearly covers the topic, **propose editing it**; otherwise **propose a new note**
     with a title following the format above. When the match is weak, prefer a new note over
     force-fitting content into a loosely related one.
  3. **Confirm the destination with the user**, then run the Edit or Create workflow accordingly.

## Create workflow

1. **Offer a template.** List `_templates/*.md` and offer the choices to the user; default to
   `_templates/Base.md` if they don't pick one.
2. **Scaffold.** Copy the chosen template's contents into `notes/<Title>.md` (the title the user
   gave, with spaces, no extension games — just `<Title>.md`).
3. **Write the body with the user** — prose in the vault's `language`, foreign terms in _italics_,
   inline `#tags`, and inline links to related notes per the format above.
4. **Review links.** Before updating the index, scan the note body for any proper noun, system name,
   tool name, command prefix, or concept mentioned in plain text that has its own note in the vault —
   and add the missing links. This is easy to miss when writing command-heavy notes (e.g. `fury
   ai assets` mentions Fury but the word may never appear as a standalone link target). Check
   `.index/INDEX.md` titles if unsure whether a note exists.
5. **Update the index.** Run the `note-index` skill in **single-note mode** for `<Title>` so its line
   in `INDEX.md` reflects the new note.

## Edit workflow

1. Edit the note's body directly — when adding provided content, **integrate it coherently** into
   the existing text (don't append a raw dump or duplicate what's already there). Tags and links may
   be added, changed, or removed inline.
2. **Review links.** Scan the updated body for any proper noun, system name, tool name, command
   prefix, or concept mentioned in plain text that has its own note in the vault — and add the
   missing links. Check `.index/INDEX.md` titles if unsure whether a note exists.
3. Run the `note-index` skill in **single-note mode** for that note so `INDEX.md` picks up the change.

## Cross-references

- The **`note-template` skill** owns the template contract (what a valid file under `_templates/`
  must look like). This skill only lists and copies templates — it doesn't define what makes one
  valid.
- The **`note-index` skill** owns `INDEX.md` (generation, scan scope, caching). This skill only
  triggers its single-note mode after a write — it never edits `INDEX.md` directly.

## Rules

- **Never commit.** Writing a note and committing it are separate steps; stop after the index update
  and let the user commit. (The same marketplace ships a `commit-craft` skill for that, if they want
  it.)

## Common mistakes

- Adding frontmatter (`title:`, `tags:`, `rel:`) to a note — notes have none; everything is inline.
- Writing a link with a spaced filename unbracketed, e.g. `[x](Other Note.md)` — CommonMark can't
  parse the space; use `[x](<Other Note.md>)`.
- Prefixing links with `notes/` — links are relative to the note's own folder (all notes are flat in
  `notes/`), so the prefix is redundant and wrong.
- Duplicating a relationship — repeating in a `## Referências` section a link that already appears
  inline, or keeping a frontmatter `rel:` list. A relationship lives once: inline where the prose
  supports it, or in `## Referências` when there's no inline anchor.
- Tagging a concept that has its own note (e.g. `#fury` when `Fury.md` exists) instead of linking to
  it — a relationship is a link; tags are only for note-less categories.
- Writing a system name, tool name, or command prefix in plain text without linking — `fury ai
  assets` mentions Fury but the word may never appear as a standalone link candidate; catch these
  with the link-review step before indexing.
- Forgetting the single-note `note-index` update after create/edit — `INDEX.md` is generated and will
  go stale otherwise.
- Introducing new filenames with parentheses — avoid them going forward, even though angle brackets
  make existing ones work.
- Writing content into a note without confirming the destination when none was referenced — propose
  the target (an existing note on the topic, or a new one) and confirm first, so content doesn't
  land in the wrong note.
- Writing into `notes/` in the working directory instead of the resolved vault — always resolve the
  vault first; the plugin runs from anywhere.
