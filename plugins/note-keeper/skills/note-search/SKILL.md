---
name: note-search
description: Use when finding notes across the vault by keyword, phrase, tag, or backlink.
  Read-only retrieval over notes/ and .index/INDEX.md; ranks and presents matches, never writes. Do
  not use to open one already-known note in full (that is note-view) or to suggest links from a
  single note (that is note-link).
---

# note-search

## Overview

Finds notes across the vault for a query and presents ranked matches — **read-only retrieval**. It
never creates, edits, or deletes anything, and never runs the index. Given a query it searches two
complementary sources and merges the hits:

- **Full-text** over `notes/*.md` — literal keywords/phrases in note bodies (via `ripgrep`/`grep`).
- **Structural** over `.index/INDEX.md` — the vault map's parsed titles, summaries, tags, and
  relationships.

Scope is `notes/` only. `_sessions/`, `_templates/`, and `_attachments/` are not searched (same
scope guard as the `note-index` skill).

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

## When to use (vs. the `note-link` skill)

- **`note-search`** answers *"which notes match this query?"* — retrieval from a keyword, topic, or
  tag.
- **`note-link`** answers *"which notes should note A link to?"* — neighbor discovery for one note.

They both read `INDEX.md` but serve different questions; don't conflate them.

## Search modes

Pick the mode from the shape of the query:

- **Keyword / phrase (default)** — free text: **run the verbatim phrase as a full-text search over
  bodies first**, then also match it against INDEX titles/summaries for topical hits. A note that
  merely *contains* the words — even only in a heading — is a valid hit; don't require it to be
  "about" the topic before returning it.
- **Tag** — the query is a `#tag` (e.g. `#runbook`): filter `INDEX.md`'s `tags:` column. Tags
  are parsed there authoritatively (no false hits from a `#` inside code spans or URLs), so prefer
  the index over grepping bodies. A tag query matches nested tags by prefix — `#runbook` covers
  `#runbook/database`.
- **Backlinks** — "what links to `<Target>`": filter `INDEX.md`'s `relationships:` column for
  `Target` (relationships are the parsed outbound links). This finds the notes that point at the
  target.
- **Title** — the query looks like a note title: match against `notes/*.md` filenames and INDEX
  titles.

## Tooling

Use `ripgrep` (`rg`) if available (fast, UTF-8-aware), else `grep`:

```bash
rg -in -C1 "<query>" notes/          # or: grep -rin -C1 "<query>" notes/
```

- `-i` case-insensitive; `-C1` one line of context around each hit.
- Accents match literally, and note bodies are written in the vault's `language` —
  if a term might be written with or without accents, try both.
- **Search the query verbatim first** — run the exact words the user typed over `notes/` before
  anything else; a match in a **heading** or anywhere in the body counts. Only if the verbatim phrase
  returns nothing, broaden: retry the strongest individual term(s) and accent/case variants.

## Workflow

1. **Classify the query** into a mode (above).
2. **Structural pass** — read `.index/INDEX.md` and pull notes whose title, summary, tags, or
   relationships match. If `INDEX.md` is missing or looks stale, say so and suggest running the
   `note-index` skill; full-text still works without it.
3. **Full-text pass (always run it)** — run `rg`/`grep` over `notes/` for the **verbatim query**
   first, then broadened terms only if that finds nothing; collect the matching files and hit lines.
   Never skip this pass or replace it with an INDEX-only judgment.
4. **Merge & rank** — one entry per note, most relevant first (see Ranking). A note that matches in
   several ways ranks higher and lists every reason.
5. **Present** the ranked results (see Presentation). Stop there — this is retrieval only.

## Ranking

Strongest to weakest signal:

1. Exact or substring **title** match.
2. **Tag** match.
3. **Summary** (topical) match in the index.
4. **Body** hits — more hits and tighter term proximity rank higher.

A note matching in several categories outranks one that matches in a single category. An **exact
verbatim match of a multi-word query** (especially in a heading) is a strong hit — rank it near the
top, not as a weak single-term body hit.

## Presentation

A ranked list, one note per line, using **two clickable link forms** together:

- **Note title → a console link.** Link the title as `[Title](<notes/Title.md>)` (vault-relative
  path in angle brackets; the spaces stay inside). A bare path isn't clickable once the filename has
  spaces — always wrap it.
- **Line reference → an editor-at-line link.** For a full-text hit, cite the matching line using the
  local-link form supported by the active agent UI. In Codex, use an absolute Markdown file link
  with the line suffix, e.g. `[line 26](/ABS/VAULT/notes/Title%20With%20Spaces.md:26)`. In Claude
  Code, a `file://` URL with a `#L<line>` fragment also works. Build the absolute prefix from the
  vault resolver's `root` value (see "Resolve the vault first"); never hardcode it and never assume
  the vault is a git repository — it need not be.

So each hit shows the title as a console link plus a one-line **reason**; when the match is
full-text, cite the matching **line** as an editor-at-line link with a short excerpt. Structural hits
(tag/summary/backlink) have no line — they carry the title link only.

```
1. [Rate Limiting](<notes/Rate Limiting.md>) — exact heading at [line 26](file:///ABS/VAULT/notes/Rate%20Limiting.md#L26)
   > ## Rate Limiting
2. [API Gateway](<notes/API Gateway.md>) — summary match ("throttling")
```

Then offer next actions: the **`note-view`** skill to read a hit in full, the **`note`** skill to
edit it, and the **`note-link`** skill for related notes (Claude Code: `/note-keeper:note-view`,
`/note-keeper:note`, `/note-keeper:note-link`; Codex: `$note-view`, `$note`, `$note-link`). If
nothing matches, say so and suggest a broader term or running the `note-index` skill to refresh the
map.

## Rules

- **Read-only.** Search reads and reports; it writes nothing and never runs the index.
- **Prefer the index for tags and backlinks.** Its `tags:`/`relationships:` are parsed
  authoritatively — grepping bodies for `#tag` or a link target risks false hits inside code and
  URLs.
- **Scope is `notes/`.** Don't search `_sessions/`, `_templates/`, or `_attachments/`.
- **Faithful excerpts.** Quote matching lines as they are; don't paraphrase a note to make it look
  like a hit.

## Cross-references

- The **`note-view` skill** displays a result in full — hand off there to open a hit.
- The **`note-link` skill** suggests links from one note (neighbor discovery) — a different question
  from search.
- The **`note-index` skill** owns `.index/INDEX.md`; search only reads it and never regenerates it.
- The **`note` skill** owns editing; apply a change to a found note through it.

## Common mistakes

- Grepping bodies for `#tag` or a link target instead of filtering the index's parsed
  `tags:`/`relationships:` — bodies produce false hits inside code spans and URLs.
- Searching the whole query sentence verbatim and missing notes that use different wording — search
  the key term(s) and lean on the index's summary/topical match.
- Editing or "tidying" a note while searching — search is read-only; route edits through `note`.
- Running the `note-index` skill as part of a search — search never writes the index; only suggest
  it if the map looks stale.
- Searching `_sessions/` or `_templates/` — out of scope, same as the index.
- Presenting a result as a bare path when the filename has spaces — it won't be clickable; wrap the
  title in a Markdown link, `[Title](<notes/Title.md>)`.
- Concluding "no note is about X" when the exact words appear in a note's heading or body — a heading
  is content; always run the verbatim full-text grep and trust its hits.
- Reading the query as a topic and reducing it to "strongest terms" *before* trying it verbatim, so
  an exact phrase that's literally in a note gets missed (the failure this skill guards against).
- Mentioning a line number as plain text — when a full-text hit has a line, link "line N" to a
  `file://…#L<line>` URL so it opens the editor there; the note title stays the console link.
