# Just Don't

**The name was the instruction.**

A tiny game about repeatedly bothering something that explicitly asked you not
to. It remembers. Its objections become increasingly familiar.

Internal project name: **nuhuh**. Working public name: **Just Don't**.

## Current build: v0.2.0

The terminal game and Discord bot share an engine. Context events, persistent
cooldowns, replay protection, and the adapter are implemented and tested without
logging into Discord. A live test-server check is still needed. Phrases and tier
thresholds are temporary material for the later writing pass.

**Offline play needs only Python 3.11+**, without dependencies, account, or token.
Tested on Python 3.12. Discord mode additionally uses `requirements.txt`.

## Try the events

Open a terminal in this folder:

```sh
python -m nuhuh --demo
```

This disposable in-memory demonstration uses fixed sample identities and a
virtual clock: first contact, recent repeat, day-long absence, and a newcomer
joining five participants. It never sleeps or changes saved games. Only the
`--phrases` option affects the scripted demo; other simulation options do not.

## Play

```sh
python -m nuhuh
```

Press **Enter** to ping; `/quit` to leave. Ctrl+C and end-of-input also exit.
`/wait 86401` advances simulated time by just over a day without actually waiting.
Use `python3` or `py` if that is your system's Python command.

Guild/user IDs default to `1`; counts persist in `.nuhuh/demo.sqlite3`, beneath
the current folder. Run again to continue, or choose another relationship:

```sh
python -m nuhuh --guild-id 123 --user-id 456
```

IDs are positive integers and need not identify real accounts. Returning to
previous IDs resumes their relationship. To explore count tiers quickly:

```sh
python -m nuhuh --db :memory: --pings 15 --step-seconds 180 --debug
```

The 180-second spacing moves beyond the recent-ping window. `--debug` shows
count, tier, and selected event. `--pings` accepts 1–1,000. `:memory:` leaves no
database. Simulated future times persist in file databases; use `:memory:` for
time-travel experiments. The bot uses a separate database by default.
Offline play has no response cooldown. Use `--help` for all options.

## Run on Discord

Create a virtual environment from this folder:

```sh
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:NUHUH_DISCORD_TOKEN = "your private bot token"
.\.venv\Scripts\python.exe bot.py
```

Linux/macOS:

```sh
.venv/bin/python -m pip install -r requirements.txt
export NUHUH_DISCORD_TOKEN='your private bot token'
.venv/bin/python bot.py
```

`config.py` contains the paths and pacing constants and reads the token from
the environment. No `.env` loader is included. Keep the real token private.

Install your application to a test guild with the `bot` OAuth scope. Grant
**View Channel** and **Send Messages** (permission integer `3072`) for an ordinary
text channel. Leave all privileged intents disabled. The code requests only
Guilds and Guild Messages. No member enumeration or message-content inspection
is performed. The chosen plain channel-send method needs no administrator,
read-history, mention-everyone, or embed permission; confirm this live.

Mention the bot directly. It ignores bots, webhooks, DMs, threads, role/everyone
mentions, system messages, and edits. Pinging replies qualify when the bot is
in the user-mention list; non-pinging replies do not. Multiple mentions in one
message count once. There are no slash commands to synchronize.

Default response-attempt cooldowns are **5 seconds per guild/user** and
**2 seconds per channel**. Mentions still count during suppression or missing
send permission. An in-flight send blocks further replies for that user/channel,
even after cooldown, while independent users/channels proceed. Nothing queues
a backlog of jokes. Attempt cooldowns persist across restarts and start before
sending; failed/time-out sends consume cooldown without marking delivery.
The timeout is 15 seconds. Outgoing mention notifications are disabled.

Ctrl+C drains in-flight handlers before closing the database. Run one bot
process per token/database.

References: [discord.py API](https://discordpy.readthedocs.io/en/stable/api.html),
[Discord Gateway intents](https://docs.discord.com/developers/events/gateway).

## Context events

The first enabled matching event overrides the normal count-tier pool:

| Priority | Event ID | Condition |
| --- | --- | --- |
| 1 | `first_guild_ping` | No participant has previously pinged in this guild |
| 2 | `new_user_in_crowd` | This user's first ping here; at least five other participants |
| 3 | `first_user_ping` | This user's first recorded ping in the guild |
| 4 | `returning_user` | More than 86,400 seconds since their previous observed ping here |
| 5 | `recent_ping` | At most 120 seconds since their previous observed ping here |
| Fallback | Count tier | No enabled event matches |

Participants means people who have pinged, rather than the guild member count.
Timing uses UTC observation timestamps and includes suppressed mentions. At
exactly one day, return does not fire; at exactly 120 seconds, recent does.
Thresholds live in the JSON `context` object.

Missing or empty event pools disable those events and matching continues down
the table. Events currently have their own pools, independent of count tiers.
Frequent pings can keep selecting the recent event; counts and tiers still
advance. New condition types require engine code; editing existing pools and
thresholds requires only JSON changes and a restart. No unrelated activity is read.

## Customize phrases

Edit `nuhuh/data/phrases.json`. For CLI use `--phrases my_phrases.json`; for the
bot set `PHRASES_PATH` in `config.py`. Minimal version 2 example:

```json
{
  "schema_version": 2,
  "context": {
    "recent_seconds": 120,
    "return_after_seconds": 86400,
    "crowd_min_others": 5
  },
  "events": {
    "new_user_in_crowd": [
      {"id": "crowd.joining", "text": "I can't believe you're joining them."}
    ]
  },
  "tiers": [
    {
      "id": "objection",
      "min_count": 1,
      "phrases": [
        {"id": "objection.sign", "text": "The name was the instruction."},
        {"id": "objection.count", "text": "{count} pings. I see."}
      ]
    }
  ]
}
```

- First tier starts at 1; subsequent minimum counts strictly increase. The
  final tier continues to the supported count limit of 2^63 − 1.
- Every tier needs a phrase. Empty event pools intentionally disable events.
- Tier IDs are unique; phrase IDs are unique across all tiers and events.
  IDs start with a lowercase letter, using lowercase letters, digits, dots,
  underscores, or hyphens. Keep IDs stable when editing text.
- `{count}` and `{others}` are supported. `{others}` counts other recorded
  participants in the guild. Use `{{` and `}}` for literal braces.
- Text must be nonempty and fit in 2,000 UTF-16 units after substitution.
- Context thresholds are positive integers; recent must be shorter than return.
- Comments/trailing commas are invalid JSON. Restart after editing.

Validation happens before opening the database. Version 1 count-only JSON still
works, without events. Removed phrase IDs are handled gracefully.

## Engine and data

SQLite stores guild/user IDs, counts, last observed ping and response-attempt
times, last delivered phrase ID, and count at delivery. Channel attempt times
and bounded message-ID replay state are also stored. No names or message text
are stored. Relationships persist until deleted.

`Game.ping()` counts and selects atomically. A known message ID returns `None`
without changing count/timestamps. A new interaction returns a `Reply`; call
`Game.delivered()` after a successful send. Unsent interactions still count.
Late acknowledgements cannot overwrite newer delivery state.

Count-tier selection hashes compact JSON `[1, guild_id, user_id, count, tier_id]`
with SHA-256. Events use `[2, guild_id, user_id, count, "event:" + event_id]`.
Interpret the UTF-8 digest as an unsigned big-endian integer, modulo eligible
phrase count. Preserve file order and exclude the last delivered phrase ID
when alternatives exist. Reproducibility requires unchanged configuration,
matching context, and delivery history. Pool edits can change future choices.

`AsyncGame` runs SQLite on a dedicated thread; `Responder` coordinates sends.
Each `Game` connection belongs to its creating thread. Independent connections
safely share a database. Schema v1 databases migrate to v2 without resetting
counts/history. Existing users begin with unknown timing context, so migration
does not invent an absence or first interaction.

Message IDs have a 24-hour observation window, pruned on the next mention.
Replays beyond that window can count again. Channel attempt rows older than
a day (or channel cooldown, if longer) are pruned on response claims. No history
is scanned after downtime. A crash between send and delivery acknowledgement
can affect repetition avoidance; timeouts can leave delivery uncertain. The
bot does not retry that observed message within its replay window.

Demo database: `.nuhuh/demo.sqlite3`, relative to the terminal's current folder.
Bot database: `.nuhuh/bot.sqlite3`, anchored to the project folder. To reset,
stop the program and delete the appropriate database and matching sidecars.
To delete a person's relationships, stop the bot and execute the parameterized
SQLite statement `DELETE FROM relationships WHERE user_id = ?` with their ID.
Replay rows have no user IDs and expire as above; channel rows track pacing.
There is no public data-deletion command yet.

## Development

```sh
python -m unittest discover -v
```

Tests cover context boundaries/priority, migration, persistence, determinism,
replays, cooldowns, concurrency, in-flight sends, failures/timeouts, validation,
and CLI behavior. With requirements installed, five adapter/lifecycle tests
use actual discord.py types and fake messages/sends, without login or network
calls. Those five are skipped when Discord is not installed.

The working repository has local Git history. The ZIP omits Git metadata.
Initialize an extracted copy using `git init -b main`, `git add .`, and
`git commit -m "Add nuhuh game and Discord adapter"`, with your normal Git identity.
No GitHub remote has been created or pushed by this build.

See `NUHUH_PROJECT_BIBLE.md` for design and progress. Next: a live test-server
check, then final phrase work and artwork. Choose a license before public release.
