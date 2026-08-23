---
name: note-setup
description: Set up a note-keeper vault — create one in a new or existing folder, adapt a folder
  that already holds Markdown, and optionally configure Obsidian to read and write the same layout.
  Use when the other skills report that no vault was found, when starting a vault from scratch, or
  when pointing Obsidian at an existing one. Do not use it to write or edit a note (that is note),
  to import notes from a separate external folder (that is note-migrate), or to rebuild the vault
  map (that is note-index).
---

# note-setup

## Overview

Turns a folder into a note-keeper vault and, if the user wants it, points Obsidian at the same
layout. It handles a folder that does not exist yet, an empty one, an existing Obsidian vault, and a
folder that already holds Markdown — and it **writes nothing before the user approves a plan**.

This skill is the only one that runs *before* a vault exists, so it does not resolve one first. It
creates what every other skill then expects.

## The layout it creates

```
<vault>/
├── .note-keeper.json    marker + language/timezone settings
├── notes/               the notes, flat
├── _attachments/        media referenced from notes and sessions
├── _templates/          note skeletons (a starter Base.md is written)
├── _sessions/           live capture buffers
└── .index/              generated map — INDEX.md and cache.json
```

## Workflow

1. **Get the target folder.** The user names it, or you ask. Expand `~` and use an absolute path.
   Never pick a folder for them, and never default to the working directory without saying so.

2. **Inspect it.** This reads and reports; it creates nothing:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py" inspect "<path>"
   ```

   (`CLAUDE_PLUGIN_ROOT` and `PLUGIN_ROOT` are what today's hosts call this plugin's install
   directory. On a host that exports neither, take this SKILL.md's directory and go two levels up.)

   The JSON tells you which case you are in: `exists`, `empty`, `is_vault`, `configured`, `missing`
   (layout folders absent), `notes` (how many are already there), `loose_markdown` (Markdown outside
   `notes/`, root docs like `README.md` excluded), `is_git`, and `obsidian.present` /
   `obsidian.changes`.

3. **Ask whether Obsidian is in play.** Obsidian is optional and never a dependency — the vault is
   plain files either way. Ask once; if yes, the plan includes the settings from `obsidian.changes`.

4. **Present the plan and wait for approval.** One plan, covering everything:
   - folders and files to create (`missing`, plus `.note-keeper.json`);
   - the `language` and `timezone` to record, defaulting to `pt-BR` and `-03:00` — confirm them,
     since every note and session timestamp follows them afterwards;
   - each Obsidian setting to change, as `key: from → to`;
   - what to do with `loose_markdown`, if any (step 6);
   - explicitly, what will **not** be touched: existing notes, Obsidian themes and workspace, and
     anything under a folder already in place.

   Preview it exactly with `--dry-run`, which writes nothing:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py" init "<path>" --obsidian --dry-run
   ```

5. **Create the layout** once approved. Add `--obsidian` only if the user asked for it:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT:-$PLUGIN_ROOT}/scripts/vault.py" init "<path>" --obsidian
   ```

   It is idempotent — it creates only what is missing and reports what it created, so re-running it
   on a half-built vault is safe. To configure Obsidian for a vault that already has the layout, use
   `obsidian "<path>"` instead of `init`.

6. **Deal with loose Markdown, only if the user approves.** Files reported in `loose_markdown` are
   notes sitting outside `notes/`, where nothing will index them. List them, then either:
   - **move them into `notes/`** — use `git mv` when `is_git` is true so history follows, plain `mv`
     otherwise. Their filenames become their titles, so rename anything cryptic *now*, before links
     point at it; or
   - **leave them** and say they will stay invisible to the index.

   Do not rewrite their contents here. Bringing bodies into the note format is the `note` skill's
   edit workflow, and importing from a *separate* folder is `note-migrate`.

7. **Build the first index.** Hand off to the `note-index` skill (full rebuild) if the vault has any
   notes — including ones just moved in. An empty vault has nothing to index; say so and skip it.

8. **Tell the user how the vault will be found**, then stop. Resolution order is
   `$NOTE_KEEPER_VAULT`, then a `.note-keeper.json` up the tree, then a `notes/` folder up the tree.
   Working outside the vault means exporting it:

   ```shell
   export NOTE_KEEPER_VAULT="<path>"
   ```

## Obsidian

What gets configured, and why each one matters:

| Setting | Value | Why |
| --- | --- | --- |
| `useMarkdownLinks` | `true` | **The load-bearing one.** Left alone, Obsidian writes `[[wikilinks]]`, which the note format forbids. |
| `newLinkFormat` | `shortest` | Produces `Target.md` — exactly the form the `note` skill specifies. |
| `attachmentFolderPath` | `_attachments` | Pasted media lands where the vault expects it. |
| `newFileLocation` + `newFileFolderPath` | `folder`, `notes` | A note created by hand in Obsidian lands in `notes/`, so the index picks it up. |
| Templates folder | `_templates` | The core Templates plugin offers the same skeletons the `note` skill does. |
| `userIgnoreFilters` | adds `_sessions/` | Capture buffers stay out of search and the graph. |

Merged into `.obsidian/`, never rewritten wholesale: unrelated keys, themes, and workspace state are
left alone.

**Tell the user these three things — they are not obvious and each one bites:**

- **Close the vault in Obsidian first.** Obsidian rewrites `.obsidian/*.json` when it exits, and
  will overwrite settings written underneath a running instance. Configure with it closed, then
  reopen and confirm under Settings.
- **`INDEX.md` is not visible in Obsidian.** It lives in `.index/`, and Obsidian ignores
  dot-folders. That is deliberate — the map is a generated artifact, not a note — but it does mean
  the vault map can only be read outside Obsidian.
- **The skills do not run on mobile.** Obsidian mobile reads and edits the same vault (the
  `.obsidian/` settings travel with it, so the format rules hold there too), but Claude Code and
  Codex are desktop tools. Notes written on a phone are picked up the next time `note-index` runs on
  a desktop.

Obsidian's own settings keys are not verifiable from here, and an unknown key is ignored rather than
rejected — so if a setting does not appear to take effect, have the user check it in Settings rather
than assuming the file is wrong.

## Rules

- **Nothing is written before the approval gate in step 4.** `inspect` and `--dry-run` exist so the
  plan can be exact.
- **Never delete or overwrite.** Setup only creates what is missing and merges settings. An existing
  note, template, or Obsidian preference is never replaced.
- **Never move a file the user did not approve moving.** Loose Markdown stays put by default.
- **Confirm `language` and `timezone`** rather than silently accepting `pt-BR` / `-03:00`. They are
  cheap to set now and awkward to change once notes exist.
- **Obsidian is optional.** Do not configure it unasked, and never present it as required.
- **Never commit.** Setup can create a lot of files; stop and let the user commit. (The same
  marketplace ships a `commit-craft` skill for that, if they want it.)

## Cross-references

- The **`note` skill** owns the note format — this skill creates the folders that format lives in,
  and never writes a note body.
- The **`note-index` skill** owns `INDEX.md`; step 7 hands off to it rather than building a map here.
- The **`note-template` skill** owns the template contract. Setup writes one starter `Base.md`;
  anything further goes through that skill.
- The **`note-migrate` skill** imports notes from a *separate external* folder into a vault that
  already exists. This skill only adopts Markdown already inside the target folder.

## Common mistakes

- Creating anything before the user approved the plan — `inspect` first, always.
- Running `init` against the working directory because no path was given, instead of asking.
- Writing Obsidian settings while Obsidian has the vault open, so they are silently reverted on exit.
- Authoring `.obsidian/core-plugins.json` when it does not exist — that file is a complete list, not
  a set of overrides, so a fresh one holding a single entry reads as "every other core plugin is
  off". The script deliberately leaves it to Obsidian; do not write it by hand either.
- Moving loose Markdown into `notes/` without asking, or moving it and then forgetting to rebuild the
  index so the new notes stay invisible.
- Promising that the skills work on Obsidian mobile — they do not; only viewing and hand-editing do.
- Treating a `notes/` folder found somewhere up the tree as the intended vault. Setup targets the
  folder the user named; resolution guesswork belongs to the other skills, not this one.
- Committing the new vault automatically.
