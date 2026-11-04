# Changelog

## 0.5.1 — 2026-11-04

- Reworked the README as a friendly introduction with quick play instructions
  and a credential-free offline demo. Moved detailed mechanics/customization to
  DEVELOPING.md and Discord setup/operation to OPERATING.md.
- Removed exact phrase totals from public overview copy and replaced the
  shipping-copy test's fixed total with uniqueness and history-window variety
  checks. Added coverage for valid additions, removals, and rewrites.
- Updated the release checklist to distinguish confirmed live checks from
  remaining verification. Gameplay, phrase content, database format, and license
  are unchanged.

## 0.5.0 — 2026-11-04

- Added occasional reactions to 350-character messages, Unicode/custom emoji,
  repeated literal mentions, and whole short apologies/bargaining expressions.
- Added four delivery-aware memory tags per guild/user for one-use callbacks;
  an accepted apology makes a later non-apology ping eligible for its aftermath.
  Failed/suppressed replies do not establish or consume memories.
- Added group-incident reactions based on distinct recent pingers, exact-count
  milestones, and rare admissions after the final tier begins. All share the
  existing cooldowns and deterministic selector; no delayed replies are queued.
- Appended 96 phrases, preserving all 147 texts/IDs from public base `9d17c69`.
  Optional `surprises` settings extend phrase schema 3 without invalidating
  existing custom files. Missing/empty event pools disable their responses.
- CLI now accepts typed messages, batch `--message`, and a spoiler-aware
  `--encounters` copy preview. Offline play still needs only Python's standard library.
- Bundled Unicode 17 property ranges and attribution for emoji detection;
  no new dependency, runtime network call, or privileged intent is introduced.
- Fresh database schema 5 adds bounded memories. Older alpha databases need
  a reset while stopped; no migration code is carried forward.

## 0.4.1 — 2026-11-04

- Help copy now returns a history-aware footer alongside its title and
  description, shared by Discord embeds, plain-text fallback, and the CLI.
- Polished paragraph spacing and closing lines while retaining the updated
  button persona. Game behavior and database format are unchanged.

## 0.4.0 — 2026-11-04

- Added exact mention help: friendly before a user's first ping in a guild,
  snarkier afterwards. Help does not count or change game timing/participants.
- Extra wording after the help keyword counts as play and selects a new pool
  of 12 lines, ahead of normal context events. Existing phrase edits are retained.
- Help shares persistent pacing, replay protection, and in-flight send limits
  with game replies. Embeds fall back to plain text if Embed Links is unavailable.
- Added matching `/help` behavior to the dependency-free CLI.
- Moved user response-attempt state to a separate table, using fresh schema 4.
  Older alpha databases need a reset; no migration code is included.
- Message text is inspected only after the direct-mention filter, without a
  privileged intent, to distinguish help from play. No message text is stored.

## 0.3.0 — 2026-11-04

Rapid play previously selected recent-ping replies on every eligible interaction,
hiding the count-tier personality. Recent replies now use a reproducible
one-in-three draw, with ordinary tier replies otherwise. First-contact,
newcomer, and return events retain priority when their pools are enabled.

- Added 135 phrases across six stages and five context pools. The final stage
  has twenty lines and continues indefinitely. Selection avoids the last five
  successfully delivered lines when the pool allows it, even across restarts.
- Added `--tour` to preview every tier without touching saved data. Updated
  `--demo` to show both context events and recent/tier mixing.
- Moved editable phrase files to schema version 3, with `recent_one_in` in
  the context settings. Use the new supplied file as the customization base.
- Removed database migration code. Empty databases are initialized directly;
  schema-3 databases store bounded reply history. Older or unversioned nonempty
  databases receive a reset instruction instead of being altered. Alpha v0.2
  databases need a one-time reset.
- Protected database shutdown from caller cancellation and made concurrent
  close calls await the same cleanup operation.
- Declared the dotenv dependency, added an environment example, release/data
  documentation, an MIT license, a Linux service template, and CI checks for
  Ubuntu/Windows on Python 3.11/3.13.
- Added a resource-checking test runner that fails on unclosed SQLite handles.

## 0.2.0

Added context events, virtual-time CLI play, the minimal-intent Discord adapter,
persistent response-attempt cooldowns, and bounded message replay protection.
The Windows test-helper connection leak was subsequently corrected.

## 0.1.0

Initial offline mention game with persistent guild/user counts and editable tiers.
