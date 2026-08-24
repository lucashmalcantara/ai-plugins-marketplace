---
name: note-view
description: Use when displaying a note (whole or part) rendered in the console, read-only. Re-emits
  the note's Markdown so the agent UI renders it; never writes. Do not use to create or edit a note
  (that is note) or to search across the vault (that is note-search).
---

# note-view

## Overview

Displays a note from `notes/` (or any vault Markdown file) in the console — whole or in part — and
does nothing else. **This skill is strictly read-only:** it never creates, edits, moves, or deletes
anything, and never touches the index. It only reads and shows.

**How it renders:** the skill reads the target and **re-emits its Markdown as the response**, which
the active agent UI renders (headings, tables, lists, code, links). That is the reliable path. Do
**not** pipe the file through an external pager (`glow`, `bat`, `cat`) via a shell command to "show"
it — that output goes to the agent's context, not reliably to the user. For a true external terminal
render (colors, pager, outside the agent), tell the user they can run `glow <path>` themselves.

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

## Resolving the target

The argument names what to show:

- **A path** — `@notes/<Title>.md` or an explicit vault-relative path (e.g. `.index/INDEX.md`). Use
  it directly.
- **A name or topic** — resolve against `notes/*.md` by filename (the title, with spaces). If more
  than one note matches, list the candidates and ask which; if none matches, say the note doesn't
  exist and offer to create it via the `note` skill. Never invent content.

## Choosing the scope

- **Whole note (default)** — no scope argument: show the entire body.
- **A section** — the argument names a heading (e.g. `## Decisions`): show from that heading through
  the end of its section (up to the next heading of the same or a higher level). If the note has no
  headings — many notes are plain prose — say so and show the whole note.
- **A line range or excerpt** — e.g. `10-25` for those lines, or a request like "the first lines":
  show just that slice.

## Workflow

1. **Resolve the target** (above). If it can't be resolved, stop and report — never guess a path or
   content.
2. **Read** the file: the whole body, or just the requested slice.
3. **Emit the Markdown as your response** so the terminal renders it. Precede it with a one-line
   locator — the note title/path, and for a partial view, which part — so the user knows what
   they're looking at. Show the content **faithfully**: don't summarize, reword, or fix it; this is
   a viewer.
4. Do not run the `note-index` skill and do not modify anything.

## Rules

- **Read-only, always.** This skill reads and displays; it writes nothing. Changing the note is the
  `note` skill's edit workflow, not this one.
- **Render via the response, not a shell pager.** Your Markdown response is what the agent UI
  renders for the user; `glow`/`bat` run over Bash send output to the agent instead. Only suggest
  `glow <path>` for the user to run.
- **Faithful display.** Show the note as written — no summarizing or editing. Inline `#tags` and
  links render as they are.
- **Label partial views.** When showing a section or a line range, say it's partial, so the user
  doesn't mistake it for the whole note.

## Cross-references

- The **`note` skill** owns creating and editing notes (and the note format). This skill only
  displays; any change routes through `note`.
- The **`note-index` skill** owns `INDEX.md`. This skill never triggers it — viewing changes nothing.

## Common mistakes

- Piping a note through `glow`/`bat`/`cat` in a shell command to "show" it — that output lands in
  the agent's context, not reliably in the user's terminal; emit the Markdown as your response instead.
- Editing, reformatting, or "improving" the note while displaying it — this is a viewer, not the
  `note` skill.
- Running the `note-index` skill after a view — nothing changed, so there's nothing to index.
- Guessing a note's content or path when the target doesn't resolve — list candidates or report that
  it doesn't exist.
- Showing a section or slice without telling the user it's a partial view.
