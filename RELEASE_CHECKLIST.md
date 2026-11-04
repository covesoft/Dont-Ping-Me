# Release checklist

Use this checklist before tagging or submitting a release. The checks already
marked reflect completed implementation and reported live play; they do not
replace verification of a particular release or hosted installation.

## Implemented and covered by automated tests

- [x] Six count tiers, context pools, message reactions, callbacks, and rare material.
- [x] Friendly/snarky exact help without count, timestamp, or participant changes.
- [x] Shared help/game cooldowns and embed-to-text permission fallback.
- [x] Seeded event/tier selection, bounded delivered history, and replay protection.
- [x] Delivery-aware memories, apology aftermath, milestones, and group incidents.
- [x] CLI play, demos, previews, adjustable IDs, and virtual time.
- [x] Atomic counts, failed-send handling, and cancellation-safe database shutdown.
- [x] Invalid phrase files and incompatible alpha schemas produce useful errors.
- [x] Copy checks permit phrase additions/removals/rewrites without an exact total.
- [x] Setup guides, privacy notes, third-party notices, and a Linux service template.

## Confirmed through live play

- [x] Basic startup, shutdown, and a direct mention-response in a test guild.
- [x] Friendly help, snarkier help, and extra-help responses.
- [x] Repeated-mention, emoji, and apology reactions.
- [x] Bot profile artwork installed and reviewed.

## Before the public jam release

- [ ] Review and commit the final documentation/test revision.
- [ ] Confirm the selected commit passes the Ubuntu/Windows, Python 3.11/3.13 CI matrix.
- [ ] Follow the README from a fresh clone, including the dependency-free demo.
- [ ] Review the current phrase copy through natural play and the previews.
- [ ] Check the documented channel permissions, including plain-text help fallback.
- [ ] Check rapid pings: responses are suppressed and never queued.
- [ ] Check two users in one channel and independent users/channels for pacing.
- [ ] Stop/start the bot and confirm relationship history persists.
- [ ] Check long text, negotiation, group incidents, milestones, and rare replies live.
- [ ] Check a remembered callback across a restart and apology aftermath.
- [ ] Confirm ordinary messages and unsupported contexts remain silent.
- [ ] Check that tracked files and release attachments contain no credentials,
      runtime data, logs, or private planning documents.
- [ ] Settle the intended distribution license and align public license references.
- [ ] Decide whether the submission includes a continuously hosted bot; verify
      that installation if it does.
- [ ] Record the jam deadline and submission fields, identify the release commit,
      submit, and retain the submission link.

See [DEVELOPING.md](DEVELOPING.md#testing-and-review) for verification commands and
[OPERATING.md](OPERATING.md) for setup and data handling. Add a date and commit
when recording a new release verification; automated tests alone do not establish
live Discord behavior.
