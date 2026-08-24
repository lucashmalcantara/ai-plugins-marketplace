---
name: note-migrate
description: Use when importing external .md notes (an Obsidian vault or a plain Markdown folder)
  into the vault, consolidating by topic rather than copying files one-to-one. Non-destructive — the
  source is read-only and nothing is written until the whole plan is approved. Do not use it to edit
  a single existing note directly (that is note) or to convert one note into a reusable template
  (that is note-template).
---

# note-migrate

## Overview

Imports `.md` notes from an external folder (an _Obsidian_ vault or a plain _Markdown_ folder) into
this vault, **consolidating by topic** rather than copying files one-to-one. For each source note it
decides whether the subject already lives here — if so it **enriches the existing note**; if not it
**creates a new one** — and rewrites the content into the vault's format along the way.

Two guarantees shape everything below:

- **The source is READ-ONLY.** This skill never modifies, moves, renames, or deletes anything in the
  source folder. It only reads. Media it needs is *copied* into the vault, never moved.
- **Nothing is written until the whole plan is approved.** The skill first understands every source
  note, produces one plan covering all of them, and shows it in full. Only after the user approves
  does it write, and only then does it rebuild `INDEX.md`.

This skill does not own the note format or `INDEX.md` — it routes all writing through the `note`
skill's format and all indexing through the `note-index` skill (see Cross-references). It adds the
one thing those skills don't: the semantic judgment of *what maps to what*.

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

## Input

Accept either:

- **A folder** — walk it **recursively** for `*.md` files, or
- **Specific files** — one or more `.md` paths the user names.

**Ignore in the source** (never treated as notes): `.obsidian/`, `.trash/`, `_templates/`,
`_attachments/` (and whatever else the source calls its media folder — `attachments/`, `assets/`,
`files/`), and similar non-note directories (any dotted/hidden dir, `.git/`, editor/plugin config
folders). Media files (images, PDFs, etc.) are not notes either — they are only relevant when an
embed references them (see Conversions).

A media folder can hold `.md` files that are **assets, not notes** — an Excalidraw drawing is a
`.md` file, and so are some plugin sidecars. Anything inside the media folder is an asset no matter
its extension. Never let a recursive `*.md` walk pull one in as a note.

If a named source path is outside the vault, good — that's expected. If the user points at the vault
itself, stop and ask; this skill imports *external* notes.

## Step 1 — Understand each source note

For every source `.md` file (after the ignore filter):

1. Read the whole file: its frontmatter (if any) and its body.
2. Determine **what the note is actually about** — its subject and key points — not just its
   filename. The vault destination need not mirror the source's name or structure.
3. Note the raw materials that will need converting: `[[wikilinks]]`, `![[embeds]]`, a frontmatter
   tag list, a frontmatter list of related notes (the key varies by source vault), and any other
   frontmatter fields.

## Step 2 — Decide merge vs create (semantic consolidation)

This is the judgment step. Consult `INDEX.md` (the vault's map — one line per note with a summary,
tags, and relationships) to find an existing vault note **on the same topic** as the source note:

1. If `INDEX.md` is missing or looks stale, run the **`note-index` skill (full rebuild)** first —
   don't match against a stale map.
2. For each source note, score existing vault notes by **topic match**: overlap between the source
   note's subject/tags and a vault note's summary + tags. Filename similarity is a weak hint;
   subject overlap is the real signal.
3. Decide:
   - **merge into `<Existing Note>`** — when a vault note clearly covers the same subject. The
     source content will *complete/enrich* that note (fill gaps, add detail, add links), not
     duplicate what's already there.
   - **create `<New Note>`** — when no existing note matches. Pick a destination title that follows
     the vault's conventions and the `note` skill's format (not the source filename verbatim).
   - **When unsure, prefer create and flag it** in the plan for the user to confirm — never
     force-merge two notes that only loosely overlap.

Multiple source notes may map into the **same** existing or new vault note (consolidation) — say so
explicitly in the plan.

**A source note with an empty body is still a decision.** A vault that grew in another tool
accumulates notes that are nothing but frontmatter — a title someone linked to before writing it.
The body is empty, but the note is not worthless: its **title and its inbound links are the
content**, and dropping it silently deletes a piece of the graph the user built. Classify each one:

- **It has inbound links, outbound ones, or both** — keep it, as a note whose body carries only
  those relationships, written from what the rest of the corpus already states. If one note says
  "successor to X" and X's own note is empty, X's note can say it is the predecessor: restating an
  existing fact is not invention, while asserting a new one is. If nothing in the corpus says
  anything about it, keep the note with just its links.
- **It has no links in either direction and no body** — nothing survives it. Propose dropping it,
  and list it in the plan under what will not be migrated.

List every empty note in the plan with the branch you chose, so the user can overrule the policy in
one place rather than note by note.

## Step 3 — Plan the conversions (per note)

For each destination, work out how the source content becomes vault-format content. **Resulting
notes have NO frontmatter** — everything meaningful moves inline; the rest is dropped and reported.

- **Relationships → inline Markdown links.** Every relationship — a body `[[Target]]` /
  `[[target|alias]]` wikilink, or an entry in a frontmatter list of related notes — becomes an
  inline link: `[[Target]]` → `[Target](<Target.md>)`, `[[target|alias]]` → `[alias](<Target.md>)`.
  Relationships live *only* as inline links in the body — never as a separate list or frontmatter
  block. The destination is the *vault* note the link points to — resolve it through this same plan
  (if the linked source note maps to some vault note, link to that). A link to a note that doesn't
  exist in the vault yet is acceptable — it flags a topic to develop. Link mechanics (no `notes/`
  prefix; angle brackets around spaced filenames) follow the `note` skill's link rules — don't
  restate them, apply them.
- **A wikilink carrying `#` points at a heading, not at a note.** Two forms, and the difference
  matters because treating either as a plain note link sends the reader to the wrong file:
  - `[[#Appendix 1]]` — **same note**. It becomes an ordinary anchor: `[Appendix 1](#appendix-1)`.
    It is not a relationship at all, so it never turns into a note link and never counts as a link
    to develop.
  - `[[Other Note#Section]]` — another note's heading: `[Section](<Other Note.md#section>)`. This
    *is* a relationship.

  Slugify the anchor the way the destination renders headings (lowercase, spaces to `-`), and
  remember that a split can move the target heading into a different note — resolve the anchor
  against the plan, not against the source.
- **Embeds → Markdown images + copied media.** `![[image.png]]` → `![](<../_attachments/image.png>)`.
  **Copy** the referenced media file from the source into `_attachments/` (paths from a note in
  `notes/` reach it as `../_attachments/…`). Copying — never moving — keeps the source read-only. If
  the referenced media can't be found in the source, keep the link but flag the missing file in the
  plan. Three shapes the naive `![[name.ext]]` reading gets wrong:
  - **A path prefix.** `![[_attachments/image.png]]` names the same file as `![[image.png]]` — the
    wikilink target is resolved by *basename*, not by the path written. Take the basename, then
    rebuild the destination as `../_attachments/<basename>`; never carry the source prefix through.
  - **An alias.** `![[image.png|Diagrama do fluxo]]` → `![Diagrama do fluxo](<../_attachments/image.png>)`.
    The text after `|` is the caption — it becomes the image's alt text. Dropping it loses the only
    description the image has.
  - **An accented name that compares unequal to itself.** macOS stores filenames decomposed and
    hands them back that way, while the name written inside the note is composed — the `é` in
    `Café` is one code point in the note and two on disk. Normalize both sides to NFC before matching, or every
    accented attachment reports as missing while sitting right there in the folder.
  - **A target that isn't an image, or carries no extension.** `![[drawing.excalidraw]]` embeds an
    editor-specific asset that renders only in the source app, and the file on disk may be
    `drawing.excalidraw.md`. Resolve it by basename *and* by basename plus each extension present in
    the media folder. Copy the asset, but link it as a **plain link**, not an image — `![](…)` on a
    non-image renders as a broken image everywhere. Flag in the plan that it needs the original app.
- **Frontmatter `tags:` → inline `#tags`.** Emit them inline in the body (a trailing `#tag #tag`
  line is fine, per the `note` skill).
- **Apply the vault's writing conventions:** body written in the vault's configured `language`
  (default `pt-BR`), with English terms in _italics_ (or whichever language counts as "foreign",
  relative to the vault's configured language). The `note` skill owns these rules — follow them,
  don't restate them.
- **Other frontmatter fields are discarded** (e.g. `title:`, `date:`, `aliases:`, `cssclass:`,
  `publish:`, custom keys). Record each dropped field **per source note** for the plan's report.

## Step 4 — Present the WHOLE plan (approval gate)

Show one plan covering **all** source notes at once, and write nothing yet. The plan lists, per
source note:

- The source path.
- The decision: **merge into `<Existing Note>`** or **create `<New Note>`** (and any consolidation —
  several sources into one destination). Flag every low-confidence match for the user to confirm.
- A short note of the conversions that will apply (wikilinks resolved, embeds + media to copy, tags
  moved inline).
- **Dropped-frontmatter report**: which frontmatter fields will be discarded.

A useful shape:

```
Migration plan (source: /path/to/source — READ-ONLY, nothing there will change)

1. source/throttling.md
   → MERGE into "Rate Limiting.md"  (topic match: tag overlap, summary overlap)
   conversions: [[API Gateway]] → link; tags: infra, http → inline #tags
   dropped frontmatter: title, date, aliases

2. source/idempotency.md
   → CREATE "Idempotency.md"        (no existing note on this topic)
   conversions: ![[diagram.png]] → copy to _attachments/, embed as image
   dropped frontmatter: date, cssclass

After approval: writes go through the `note` skill, then a full `note-index` rebuild runs.
Confirm to proceed.
```

**Wait for explicit approval.** If the user amends the plan (reclassify a merge as a create, rename
a destination, split/combine), update the plan and re-confirm before writing.

## Step 5 — Write (only after approval)

For each destination, in plan order:

1. **Route the write through the `note` skill** so the result conforms exactly to the note format
   (pure Markdown, no frontmatter, inline `#tags`, inline angle-bracketed Markdown links). Use only
   the **note-writing part** of that skill: its **create** workflow for a new note (scaffold + write
   the body) and its **edit** workflow for a merge (enrich the existing body — integrate the source
   content, don't append a raw dump or duplicate what's already there).
2. **SKIP the `note` skill's per-note single-note index step.** Both the `note` create and edit
   workflows normally end by running the `note-index` skill in single-note mode — do **not** do that
   here. Step 6 replaces every one of those per-note updates with a single batched full rebuild, so
   indexing during Step 5 would only produce interim `INDEX.md` diffs mid-migration.
3. **Copy any embedded media** into `_attachments/` (copy, not move).
4. Re-confirm the source is untouched — you only ever read from it.

**Indexing contract: `INDEX.md` is rebuilt exactly once, at the end (Step 6) — never per note during
Step 5.**

## Step 6 — Full `note-index` rebuild

After all writes, run the **`note-index` skill in full-rebuild mode** exactly **once** so `INDEX.md`
reflects every new and enriched note in a single pass. Once writing begins this is the *only* index
run — it stands in for all the per-note single-note updates skipped in Step 5 (the optional pre-match
rebuild in Step 2 happens earlier, before any writes). Do not hand-edit
`INDEX.md` — that's the `note-index` skill's job. Show the final `INDEX.md` diff to the user.

## Cross-references

- The **`note` skill** owns the note format and is the only skill that writes note bodies — every
  destination write in Step 5 goes through it. This skill decides *what* to write and *where*; the
  `note` skill decides *how* the file must look, including the vault's writing conventions (language,
  English terms in _italics_). Don't restate the format or those conventions here.
- The **`note-index` skill** owns `INDEX.md` (generation, scan scope, caching). This skill *reads*
  `INDEX.md` in Step 2 to find topic matches and *triggers* a full rebuild in Step 6 — it never
  edits `INDEX.md` directly.

## Common mistakes

- **Touching the source.** Modifying, moving, renaming, or deleting anything in the source folder —
  the source is strictly read-only; media is *copied* into `_attachments/`, never moved.
- **Writing before approval**, or approving note-by-note. The plan is presented and approved as a
  whole; writes happen only after that single approval.
- **Copying files one-to-one** instead of consolidating — always consult `INDEX.md` first and merge
  into an existing note when the topic already exists.
- **Force-merging loosely related notes.** When the topic match is weak, create a new note and flag
  it for the user rather than merging.
- **Carrying frontmatter into the vault.** Resulting notes have none: a tag list becomes inline
  `#tags`, a list of related notes and any wikilinks become inline links, everything else is
  discarded — and the discards are reported.
- **Leaving wikilinks or embeds unconverted** — `[[…]]` → `[text](<Target.md>)`, `![[…]]` →
  `![](<../_attachments/…>)` with the media copied in.
- **Reading an embed as `![[basename.ext]]` and nothing else** — a path prefix must be stripped, an
  `|alias` must survive as alt text, and a non-image asset must become a plain link rather than an
  image that renders broken.
- **Turning `[[#Heading]]` into a note link** — it points inside the current note. It becomes
  `[Heading](#heading)`; only `[[Note#Heading]]` is a relationship.
- **Walking `*.md` recursively without excluding the media folder** — an Excalidraw drawing is a
  `.md` file, and it is an asset, not a note.
- **Dropping empty source notes silently** — their title and inbound links are the content; decide
  per note and report the decision.
- **Prefixing links with `notes/`** or forgetting angle brackets around spaced filenames — follow
  the `note` skill's link rules exactly.
- **Hand-editing `INDEX.md`** or skipping the full rebuild after writing — route indexing through
  the `note-index` skill.
- **Indexing per note during Step 5** by running the `note` skill's per-note `note-index` step —
  skip it; `INDEX.md` is rebuilt exactly once, in Step 6, or you'll litter the migration with
  interim diffs.
