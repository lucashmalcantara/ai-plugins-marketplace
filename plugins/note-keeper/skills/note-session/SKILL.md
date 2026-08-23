---
name: note-session
description: Use when capturing live notes during an event (a meeting, a call, a workshop) to later
  distill into notes — start, capture, use, list, end, or delete a session. Do not use it to write a
  permanent note directly (that is note) or to search across existing notes (that is note-search); a
  session is a disposable capture buffer, not a note.
---

# note-session

## Overview

Manages live note-writing sessions under `_sessions/` — working buffers you capture into during an
event (a meeting, a call, a workshop) and later **distill** into real notes via the `note` skill.
A session is not a note: it's disposable scratch that happens to live in the vault so it survives
across turns and tool calls, and can be picked back up later or by another agent.

**Sessions live outside `notes/` and are never indexed.** The `note-index` skill's generator only
scans `notes/*.md`; `_sessions/` is out of scope by design, same as `_templates/` and
`_attachments/`.

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

## Session file format

- **Path:** `_sessions/YYYY-MM-DD <topic>.md` — date the session was started, plus the topic with
  spaces (e.g. `_sessions/2026-08-10 Weekly Sync.md`). Unlike a note, the filename is not the only
  identifier — the topic is also recorded in frontmatter.
- **Frontmatter (sessions DO have it — they're working buffers, not notes):**
  ```yaml
  ---
  topic: Weekly Sync
  status: open
  started_at: 2026-08-10T14:30:00-03:00
  ended_at:
  ---
  ```
  - `status`: `open` while capturing, `closed` once distilled.
  - `started_at` / `ended_at`: ISO 8601 timestamps with offset (see below). `ended_at` is empty until
    `end` runs.
- **Body:** a sequence of timestamped entries, each its own heading:
  ```markdown
  ## 2026-08-10T14:32:05-03:00

  - bullet capturing what was said/decided, close to verbatim
  - another bullet, same entry
  ```
  Every `capture` call appends one new `##` heading with the current timestamp — entries are never
  merged into a previous heading, even if seconds apart, so the transcript stays ordered and
  attributable.
- **Timestamps are ISO 8601 with an explicit offset, using the vault's configured `timezone`
  (default `-03:00`)**, both in frontmatter and in entry headings. If the user is capturing from a
  different timezone, use the correct offset instead of forcing the vault's default.
- **Attachments** referenced from a session (screenshots, recordings, shared docs) go in the shared
  `_attachments/` folder, same as attachments referenced from notes.

## The active session (per agent)

Each agent session tracks its **own** active session pointer, so two agents capturing
concurrently never collide or overwrite each other's target file.

- The pointer is a plain text file, **`active-session`, in this agent's private scratch directory**
  (the session-specific temporary directory given by the active runtime). It is not part of the vault
  and not shared across agents.
- Its content is the path to the current session file, relative to the vault root, e.g.
  `_sessions/2026-08-10 Weekly Sync.md`.
- `start` and `use` write this pointer; `capture` reads it to know where to append; `end` and
  `delete` read it to know whether they're affecting the active session (and clear it if so).
- If `capture` runs with no pointer file present (or it points at a session that no longer exists),
  stop and tell the user to `start` or `use` a session first — never guess which file to append to.

## Subcommands

### `start [topic]`

1. If `topic` wasn't given, ask the user for one.
2. Compute the path `_sessions/YYYY-MM-DD <topic>.md` using today's date. If a file already exists
   at that path, don't overwrite it — tell the user and offer `use` (to resume it) or a different
   topic (to disambiguate two sessions on the same day).
3. Create the file with frontmatter (`topic`, `status: open`, `started_at` = now in ISO 8601 with
   offset, `ended_at` empty) and an empty body.
4. Write this session's path into the active-session pointer (see above) — `start` always activates
   what it creates.

### `capture`

Append what's happening, **faithfully** — this is a transcript, not a summary:

1. Read the active-session pointer; resolve the session file. Error out per the rule above if
   there's no valid pointer.
2. Turn the input into a new `##` heading (current ISO 8601 timestamp, using the vault's configured
   timezone — default `-03:00`) followed by bullet points.
3. **Lightly organize, never summarize:** break rambling speech into bullets, fix obvious
   transcription noise, group bullets that clearly belong together under the one heading — but do
   not condense, paraphrase away detail, or drop information because it seems minor. Summarizing is
   the `end` workflow's job, not capture's. When in doubt, keep more detail rather than less.
4. Append the entry to the end of the file (entries stay in chronological order).

### `use <session>`

Rebinds the active-session pointer to an existing session without creating or changing anything
else. `<session>` may be the file's path, its filename, or (if unambiguous) just its topic — resolve
against `_sessions/*.md` and ask the user to disambiguate if more than one matches. Works on open or
closed sessions (e.g. to `end` a session that isn't currently active).

### `list`

List sessions from `_sessions/*.md`, one line each: topic, date, status. **Defaults to open
sessions only.**

- `--all` — show both open and closed.
- `--closed` — show closed only.

Mark which one (if any) is this agent's current active session per its pointer.

### `end <session>`

Distills a session into notes, then closes it. `<session>` resolves the same way as in `use`.

1. **Read the full session file** — every entry, in order.
2. **Propose a distillation:** 1..N notes, each with a title, a short set of `#tags`, a rough body
   (real prose, not the raw bullets), and any Markdown links to existing notes that make sense
   (check `INDEX.md`, or delegate to the `note-link` skill for suggestions). This is where
   summarizing *does* happen — capture stayed faithful specifically so this step has full detail to
   work from. One session may split into several notes (e.g. one topic per note) or collapse into
   one.
3. **Get approval.** Present the proposal (titles + tags + links + body) to the user before writing
   anything. Iterate on their feedback.
4. **Create the notes via the `note` skill** (its create workflow) once approved — one call per
   proposed note. Never write into `notes/` directly from here; `note` owns that format.
5. **Close the session:** set `status: closed` and `ended_at` (now, ISO 8601 with offset) in its
   frontmatter. The session file stays in `_sessions/` — closing never moves or deletes it, and it's
   still never indexed.
6. If the closed session was this agent's active one, clear the active-session pointer.

### `delete <session>`

Deletes a session file outright (no distillation). Confirm with the user first — this is
irreversible and skips the `end` workflow entirely, so any un-distilled capture is lost. If the
deleted session was this agent's active one, clear the active-session pointer.

## Rules

- **Sessions have frontmatter; notes don't.** Don't apply the `note` skill's "no frontmatter" rule
  here — `topic`/`status`/`started_at`/`ended_at` are exactly what makes a session resumable.
- **Capture is faithful, never summarized.** Lightly organizing rambling input into bullets is fine;
  compressing or dropping content is not. Summarizing only happens once, at `end`.
- **Timestamps are ISO 8601 with an explicit offset, using the vault's configured timezone (default
  `-03:00`)** — both frontmatter fields and entry headings.
- **`_sessions/` is never indexed.** The `note-index` skill only scans `notes/`; don't expect a
  session to show up in `INDEX.md`, and don't route session content through the indexing workflow.
- **The active-session pointer lives in scratch space, not the vault.** It's per-agent, disposable,
  and never committed.

## Cross-references

- The **`note` skill** owns the note format and create workflow; `end` always creates distilled notes
  through it rather than writing into `notes/` directly.
- The **`note-index` skill** owns `INDEX.md` and explicitly excludes `_sessions/` from its scan.
- The **`note-link` skill** can be used during `end` to find good candidate links for a distilled
  note's body.
- `_attachments/` is shared between notes and sessions — no separate attachments area for sessions.

## Common mistakes

- Summarizing or trimming detail during `capture` instead of at `end` — capture must stay faithful so
  distillation has the full transcript to work from.
- Writing a distilled note directly into `notes/` instead of going through the `note` skill.
- Treating the active-session pointer as shared/global — it's per-agent scratch; each agent tracks
  its own, and it's never part of the vault.
- Merging multiple captures into one `##` heading — each `capture` call gets its own timestamped
  heading, even in quick succession.
- Adding a session's frontmatter shape (`topic`/`status`/...) to a note, or omitting frontmatter from
  a session — the two formats are deliberately different.
- Moving or deleting a session file when it's closed — `end` only flips `status`/`ended_at`; the file
  stays in `_sessions/`.
- Indexing a session, or expecting one to appear in `INDEX.md` — `_sessions/` is out of the
  `note-index` skill's scan scope entirely.
