# Release checklist

## Implemented and checked locally

- [x] Six count tiers and 243 phrases, including message reactions, callbacks, and rare material.
- [x] Friendly/snarky exact help, with no game count/timestamp/participant changes.
- [x] Shared help/game cooldowns and embed-to-text permission fallback.
- [x] Guaranteed enabled first-contact/return events and seeded recent/tier mixing.
- [x] CLI interactive play, event demo, tier tour, configurable IDs, and virtual time.
- [x] Atomic counts, persistent cooldowns, bounded replay protection, and send failure handling.
- [x] Database handles explicitly close; queued close survives caller cancellation.
- [x] Older alpha schemas receive a reset instruction; migration code removed.
- [x] Dotenv dependency and secret-free environment example declared.
- [x] Setup/customization guide, data/privacy notes, MIT license, and Linux service template.
- [x] Shared Discord/CLI message cues and deterministic encounter gates.
- [x] Delivery-aware bounded memories, apology aftermath, exact milestones, and group incidents.

## Before tagging the public jam build

- [ ] Apply/commit this revision to the repository and push it.
- [ ] Confirm the configured Ubuntu/Windows, Python 3.11/3.13 CI matrix passes.
- [ ] Read the phrase pools or play `--demo` and `--tour`; revise any lines that miss the intended voice.
- [ ] Preview the new copy with `--encounters`; test typed messages in a disposable CLI game.
- [ ] Start `discordbot.py` using the existing private `.env` and minimal permissions.
- [ ] Ping repeatedly, including intervals under five seconds: replies are suppressed, never queued.
- [ ] Test exact help before/after a ping and extra-help wording, allowing five seconds between responses.
- [ ] Test two users in one channel and independent users/channels for correct pacing.
- [ ] Stop/start the bot; relationship history and response-attempt pacing persist.
- [ ] Confirm ordinary messages and unsupported contexts produce no bot responses.
- [ ] Verify long text, emoji, repeated mentions, and short apology/bargaining reactions
      live; they are probabilistic, and first contact/returns retain priority.
- [ ] Confirm a delivered setup can receive a later callback across a restart.
- [ ] Confirm the final hosted/release setup includes no secret, database, log, or private docs file.
- [ ] Decide whether a hosted bot is part of the jam delivery; verify it if so.
- [ ] Record the actual jam deadline and submission fields, submit, and keep the receipt/link.

The user already verified the v0.2 bot's basic startup, shutdown, and live
mention response, and installed the approved Discord artwork. The checks above
apply to this new revision; no new live verification is claimed by the code tests.
