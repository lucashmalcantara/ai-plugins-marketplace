---
name: note-template
description: Use when creating a new note template under _templates/ or converting an existing note
  into a reusable template. Source of truth for the template contract (no frontmatter, no
  wikilinks). Do not use it to create or edit an actual note (that is note) or to add an index entry
  (templates are outside note-index's scan scope).
---

# note-template

## Overview

Creates and converts templates under `_templates/`. **This skill is the single source of truth for
the template contract** — every other skill that touches templates (`note`) points here instead of
restating the rules.

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

## Template contract (source of truth)

A template is a **pure Markdown file with no frontmatter** — same absence-of-metadata rule as a note
(see the `note` skill for the note format this mirrors).

- **Filename = what it represents, with spaces**, e.g. `_templates/Reunião.md`, `_templates/Base.md`.
  There is no `title` field; the filename *is* the template's name, offered as-is to the user by the
  `note` skill's create workflow.
- **Body is pure Markdown, no frontmatter.** No `title:`, `tags:`, or `rel:` block — nothing above the
  content.
- **May contain:**
  - Section headings (`## Participantes`, `## Decisões`, etc.) that scaffold the note's structure.
  - Guide text (short prompts/instructions for whoever fills the template in) written as plain prose
    or placeholder lines.
  - Placeholder inline `#tags` suggesting what the resulting note should be tagged with.
- **May NOT contain:**
  - **Wikilinks.** A template never links to a specific note — it has no relationships yet, only
    structure.
  - Frontmatter of any kind.
- **Inline links, if any, use Markdown with angle brackets** — same syntax as the note format:
  `[text](<Other Note.md>)`. In practice templates rarely need links at all, since they don't yet
  point to real content.
- **Lives in `_templates/` so it is never indexed.** The `note-index` skill's generator only scans
  `notes/*.md`; `_templates/`, `_attachments/`, and `_sessions/` are out of scope by design. A
  template never appears in `INDEX.md`.
- **Manual creation is valid.** Dropping a `.md` file directly into `_templates/` that satisfies the
  contract above is a legitimate way to add a template — this skill documents the contract, it isn't
  the only door into `_templates/`.

## Create mode

Given the user's intent (what kind of note this template scaffolds, e.g. "meeting notes", "postmortem"):

1. **Pick the filename** — what the template represents, with spaces, e.g. `Reunião.md`,
   `Postmortem.md`. Ask the user if it's ambiguous.
2. **Draft the skeleton**: section headings that capture the structure the user wants (e.g.
   `## Participantes`, `## Decisões`), optionally short guide text under a heading, and any
   placeholder `#tags` that make sense as defaults. No frontmatter, no wikilinks.
3. **Write it to `_templates/<Name>.md`.**
4. **Do not touch the index** — templates are out of the `note-index` skill's scope; there is no
   follow-up indexing step.

## Convert mode

Given an existing note to turn into a reusable template:

1. **Read the note** (`notes/<Title>.md`).
2. **Strip note-specific content**: prose specific to that instance, filled-in values, inline
   `#tags` that only make sense for that note, and outbound links to specific notes (those are
   relationships, not structure — a template has none).
3. **Keep the structure**: section headings and their order, and generic guide text if worth keeping
   as a prompt for future use. Placeholder `#tags` may be kept if they're generic enough to apply to
   every note this template would produce.
4. **Write the result to `_templates/<Name>.md`** — pick a name describing what the note represents
   (often reusing the note's own title, or a more general version of it), not the original note's
   filename verbatim if that was instance-specific.
5. The original note is untouched — convert mode only produces a new file in `_templates/`.

## Cross-references

- The **`note` skill** owns the note format and the create workflow that lists/copies templates. This
  skill only defines what a valid file under `_templates/` looks like — it doesn't restate the note
  format.
- The **`note-index` skill** owns `INDEX.md` and explicitly excludes `_templates/` from its scan —
  that's why templates never need an index update.

## Common mistakes

- Adding frontmatter to a template — templates have none, same as notes.
- Leaving wikilinks/outbound links to specific notes in a converted template — those are
  relationships that belong to the source note, not to the reusable structure.
- Leaving instance-specific prose or filled-in values in a converted template instead of stripping
  them down to structure and guide text.
- Naming the template after the source note's filename when converting, instead of naming it after
  what it represents going forward.
- Triggering an index update after writing a template — `_templates/` is out of the `note-index`
  skill's scan scope; there's nothing to update.
