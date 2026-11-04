# Changelog

## 0.7.0 — 2026-11-04

- Add exact `@bot guilds` and `@bot size` commands for configured `OWNER_IDS`.
  Owners receive non-counting reports; everyone else follows normal gameplay.
- List connected guild names and cached member counts with escaped formatting,
  pagination, and outgoing mentions disabled; no member roster fetch or new intent.
- Summarize total recorded pesters and per-guild/per-relationship max, nearest-rank
  p95, average, median, and unique mode. Historical coverage explicitly means
  guilds with recorded pesters, including retained data from departed guilds.
- Run consistent read-only statistics on the existing SQLite worker and reuse
  help's replay, cooldown, permission, timeout, and shutdown guards for reports.
- Preserve phrase/help/intro copy and database schema 5; no reset required.

## 0.6.0 — 2026-11-04

- Accept direct mentions in threads/forum posts and voice/stage text chat, with
  existing guild/user progression and actual-channel response pacing.
- Use Send Messages in Threads for thread replies; respect missing visibility,
  locked/archived state, and normal posting permissions without extra intents.
- Add one plain-text introduction 15 seconds after an actual guild join.
  Prefer a writable system channel, then an explicitly named bot channel;
  skip rules/public-updates channels and unsuitable destinations.
- Cancel pending introductions on removal/shutdown, suppress duplicate join
  callbacks, and avoid startup/reconnect broadcasts or database schema changes.
- Keep help rendering separate from these changes, accommodating local cosmetic
  edits and debug logging. Full notices remain available in the CLI.

## 0.5.2 — 2026-11-04

- Offer the first-party project under AGPL-3.0-only, with the complete standard
  license text and project/source-file notices. Retain the prior MIT notice for
  earlier releases and preserve the separate Unicode terms.
- Add source access and copyright/license/warranty information to both Discord
  help variants, plain-text fallback, offline help, and CLI argument help.
- Add optional `NUHUH_SOURCE_URL` configuration for the actual running copy;
  document source publication and versioned URLs for modified hosted forks.
- Keep phrase copy, personality footers, interaction behavior, dependencies,
  and database schema unchanged. No database reset is needed.

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
