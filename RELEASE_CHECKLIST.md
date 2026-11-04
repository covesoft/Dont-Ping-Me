# Release checklist

## Implemented and checked locally

- [x] Six count tiers and 135 phrases, including the evergreen final tier.
- [x] Guaranteed enabled first-contact/return events and seeded recent/tier mixing.
- [x] CLI interactive play, event demo, tier tour, configurable IDs, and virtual time.
- [x] Atomic counts, persistent cooldowns, bounded replay protection, and send failure handling.
- [x] Database handles explicitly close; queued close survives caller cancellation.
- [x] Older alpha schemas receive a reset instruction; migration code removed.
- [x] Dotenv dependency and secret-free environment example declared.
- [x] Setup/customization guide, data/privacy notes, MIT license, and Linux service template.

## Before tagging the public jam build

- [ ] Apply/commit this revision to the repository and push it.
- [ ] Confirm the configured Ubuntu/Windows, Python 3.11/3.13 CI matrix passes.
- [ ] Read the phrase pools or play `--demo` and `--tour`; revise any lines that miss the intended voice.
- [ ] Start `discordbot.py` using the existing private `.env` and minimal permissions.
- [ ] Ping repeatedly, including intervals under five seconds: replies are suppressed, never queued.
- [ ] Test two users in one channel and independent users/channels for correct pacing.
- [ ] Stop/start the bot; relationship history and response-attempt pacing persist.
- [ ] Confirm ordinary messages and unsupported contexts produce no bot responses.
- [ ] Confirm the final hosted/release setup includes no secret, database, log, or private docs file.
- [ ] Decide whether a hosted bot is part of the jam delivery; verify it if so.
- [ ] Record the actual jam deadline and submission fields, submit, and keep the receipt/link.

The user already verified the v0.2 bot's basic startup, shutdown, and live
mention response, and installed the approved Discord artwork. The checks above
apply to this new revision; no new live verification is claimed by the code tests.
