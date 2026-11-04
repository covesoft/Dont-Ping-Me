# Changelog

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
