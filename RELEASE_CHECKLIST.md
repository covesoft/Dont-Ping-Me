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
- [x] Thread/forum and voice/stage text routing with surface-appropriate send checks.
- [x] Delayed join introductions with destination rules, duplicate guards, and cancellation.
- [x] Exact owner-only guild/usage reports, non-counting routing, cached metadata,
      bounded pagination, and tested statistics without a database schema change.

## Confirmed through live play

- [x] Basic startup, shutdown, and a direct mention-response in a test guild.
- [x] Friendly help, snarkier help, and extra-help responses.
- [x] Repeated-mention, emoji, and apology reactions.
- [x] Bot profile artwork installed and reviewed.
- [x] Owner/non-owner routing behaves as intended.
- [x] Mentions receive responses in threads, forum posts, and voice text chat.
- [x] A new installation receives its introduction.
- [x] Relationship history persists across a restart.

These additional confirmations were reported by the operator on November 4,
2026. They do not claim every denied-permission or cancellation variant was
manually exercised.

## Verified release rehearsal — 0.7.3

Checked November 4, 2026 against public commit `212c42c`:

- [x] Fresh public clone reports version 0.7.3.
- [x] Dependency-free demo, tier tour, encounter preview, and disposable play run
      with third-party packages disabled.
- [x] Interactive help/time controls and loading an edited custom phrase file work.
- [x] Fresh virtual-environment installation from requirements.txt succeeds;
      pip reports no broken requirements.
- [x] All 112 tests pass locally on Linux/Python 3.13.17; all 157 SQLite
      connections explicitly close with ResourceWarnings promoted to errors.
- [x] All four hosted CI jobs pass: Ubuntu/Windows with Python 3.11/3.13.
      [Verified run](https://github.com/covesoft/Dont-Ping-Me/actions/runs/41918815982).
- [x] Missing-token startup gives an actionable error without attempting login.
- [x] Tracked release files contain no matched Discord-token/private-key patterns
      or excluded runtime/private-planning files. This is a scoped check of the
      current tree, not a claim about all historical Git objects.
- [x] Relative documentation links/anchors resolve; code fences are balanced.
- [x] The operator has reviewed/softened the phrase copy and locked the name Just Don't.
- [x] Select AGPL-3.0-only and align license text, project notices, and current documentation.

## Before tagging and submitting

- [ ] Commit the final release documentation and confirm CI is green for that
      selected commit; the rehearsal above identifies the exact code verified.
- [ ] Record the jam deadline, submission location, and required fields. Adapt
      [SUBMISSION.md](SUBMISSION.md) to those requirements.
- [ ] Confirm the running bot's configured source URL points to its public
      corresponding source; use a commit or release URL when finalizing it.
- [ ] Decide whether to include a hosted-bot invite; offline evaluation already
      works without a Discord account or token.
- [ ] Tag the chosen commit as v0.7.3, publish the release/submission, and retain
      the release and submission links.

## Extended playtesting

These are useful follow-up probes, with automated coverage already in place.
They do not require new gameplay or waiting for every rare line before release.

- [ ] Explore denied thread posting, invited private threads, and help's
      plain-text fallback in live Discord channels.
- [ ] Check rapid/multi-user pings and independent channels for pacing/no backlog.
- [ ] Observe callbacks, apology aftermath, long text, negotiation, group incidents,
      milestones, and rare replies naturally during play.
- [ ] Try introduction fallback routing/removal cancellation and confirm a
      restart/reconnect does not broadcast to existing guilds.
- [ ] Confirm irrelevant messages and unsupported contexts remain silent.

See [DEVELOPING.md](DEVELOPING.md#testing-and-review) for verification commands and
[OPERATING.md](OPERATING.md) for setup and data handling. Add a date and commit
when recording a new release verification; automated tests alone do not establish
live Discord behavior.
