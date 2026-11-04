# Inside Just Don't

This guide covers customization, gameplay rules, and implementation. It contains
spoilers. Start with the [README](README.md) for the premise or the
[operator guide](OPERATING.md) for Discord setup and runtime procedures.

## Terminal play and review

The CLI uses the same engine as Discord, with Python's standard library only.
Run `python -m nuhuh --help` for all options.

`--tour` previews one line from every count tier without changing saved data.
`--encounters` previews special-reaction copy, explicitly bypassing its triggers
and probability gates, also without changing saved data. It contains spoilers.
`--demo` uses a disposable game and virtual clock to demonstrate context events
and the mix of recent-ping and tier replies. All three use the actual phrase
selector.

For a disposable interactive game, run `python -m nuhuh --db :memory:`.

In interactive play, press **Enter** to ping, type a message to try its reactions,
use `/help` for instructions, `/quit` to leave, or `/wait 86401` to simulate just
over a day away. No real waiting occurs. In file-backed games, counts persist in
`.nuhuh/demo.sqlite3` beneath your current folder by default. Resume by running
again with the same database path.

```sh
python -m nuhuh --guild-id 123 --user-id 456
python -m nuhuh --db :memory: --pings 160 --step-seconds 5 --debug
python -m nuhuh --db :memory: --pings 12 --message "sorry" --debug
```

Guild/user IDs are adjustable positive integers, independent of real Discord
accounts in this simulation. Changing either creates a separate relationship.
`:memory:` starts fresh and leaves no database. `--debug` reveals count, tier,
and selected event. Use `--help` for all options. Offline play has no cooldown;
use an in-memory game for experiments with simulated future timestamps.
In the terminal, `<@1>` represents the bot if you want to try repeated mentions.
Message cues use the text you type; no synthetic mention is added to its length.
`--message` supplies the same text to each batch ping and requires `--pings`.

## Progression and context

Each guild/user relationship progresses separately. The supplied tier defaults are:

| Observed mentions | Stage |
| --- | --- |
| 1-5 | Objection |
| 6-15 | Disbelief |
| 16-35 | Bargaining |
| 36-75 | Administrative coping |
| 76-150 | Philosophical resignation |
| 151+ | Reluctant familiarity |

First contact, a newcomer joining five or more existing participants, and a
return after more than a day get their own contextual replies when enabled.
Within 120 seconds of the user's previous ping, a seeded **one-in-three** draw
can choose the recent-ping pool; ordinary tier replies appear otherwise. This
is a probability, not a fixed every-third-response rule. Repeated play can still
reveal the changing personality.

Participants are people who have pinged in that guild. No member roster is
needed. Each new qualifying game message counts once, even if it mentions the bot
several times. Exact help requests do not count. Suppressed or unsent responses
still count. Only events observed by the running bot are tracked; there is no
retrospective history scan.

## Encounters and callbacks (spoilers)

Direct mentions can occasionally get a reaction to a long message (350 or more
Unicode code points, including the mention and whitespace), emoji, or repeated
literal mentions of the bot. Several mentions in one message still count once.
Emoji detection covers Unicode 17 emoji presentation, emoji-style symbols,
keycaps, and Discord static/animated custom emoji markup. It detects presence,
not the number of complete emoji sequences. Plain digits, ordinary non-Latin
text, and bare text symbols such as © do not trigger it. No emoji package or
network fetch is needed at runtime; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

There are also a few short expressions to discover. They are deliberate patterns,
not natural-language understanding. The bot never reads surrounding conversation.

Whole short expressions such as `sorry`, `I'm sorry`, `my bad`, `please`, and
`just this once` can trigger apology/bargaining pools, ignoring case, outer
sentence punctuation, and whitespace. Quotes, code, negations such as `not sorry`,
and longer prose do not match these expressions.

After at least three **other distinct participants** have pinged in the same guild
within 60 seconds, a group-incident reaction becomes eligible. Repeated messages
by one participant do not increase that headcount. This uses only already-recorded
ping times, never the member roster or ordinary chat. Suppressed pings count.

Priority is: exact help routing; enabled extra-help pool; enabled first-contact,
newcomer, or return event; exact milestone; pending apology aftermath; message
reaction draw; callback draw; rare admission draw; existing recent/tier selection.
An empty/absent pool disables that event and lets selection fall through.

Eligible message reactions share a seeded **one-in-three** gate. If several
match, one is chosen with a separate seeded draw, so long messages do not always
hide emoji or repeated-mention reactions. Most eligible messages still reach the
existing personality progression. Each ping produces at most one reply.

Successfully delivered long-message, emoji, repeated-mention, and apology replies
create a small memory: a kind tag and the interaction count. No message text is
retained. A later message without that habit may receive a callback through a
seeded **one-in-twelve** gate. An accepted apology instead makes its aftermath
eligible on the next non-apology play that gets past the higher priorities.
Exact help does not betray an apology or consume any memory.

A delivered callback consumes that exact setup memory. Failed/suppressed replies
neither establish setups nor consume callbacks. Another delivered setup can renew
the memory; at most four tags exist per relationship. Memories persist across
restarts and remain specific to the guild/user pair. An old acknowledgement cannot
replace a newer memory. There is no delayed reply queue.

Milestone pools apply at counts 10, 25, 50, 100, 250, 500, and 1000, then every
1000 thereafter. Cooldowns can skip a milestone; it is not saved for later.
Rare admissions unlock at count 151 and use a seeded **one-in-eighty** draw when
higher-priority events have not already won. Discovery never bypasses pacing.

## Change the voice

Edit `nuhuh/data/phrases.json`, then restart. For CLI experiments, supply
`--phrases my_phrases.json`; for Discord change `PHRASES_PATH` in `config.py`.
There is no live phrase editor or runtime AI service.

The current file uses **schema version 3**. Each tier has an `id`, `min_count`,
and `phrases` list of `{ "id": "stable.id", "text": "Your line." }` objects.
The first tier starts at 1; subsequent thresholds increase. The final tier has
no upper bound other than the supported integer count limit, 2^63 − 1.

Context settings:

```json
"context": {
  "recent_seconds": 120,
  "return_after_seconds": 86400,
  "crowd_min_others": 5,
  "recent_one_in": 3
}
```

Event pools live in `events`, in this priority order:

| Event ID | Condition |
| --- | --- |
| `first_guild_ping` | First recorded participant in a guild |
| `new_user_in_crowd` | User's first ping here, with at least `crowd_min_others` prior participants |
| `first_user_ping` | User's first recorded ping in the guild |
| `returning_user` | Gap strictly greater than `return_after_seconds` |
| `recent_ping` | Gap at most `recent_seconds`, and the seeded chance succeeds |

The first enabled match wins. Missing/empty event pools disable those events;
ordinary tiers remain the fallback. `recent_one_in: 1` always selects a matching
recent event. To disable it, empty/remove its event pool. First-contact/return
matches are not subject to that chance. Event pools are independent of tiers.

The optional `surprises` object controls the new encounter settings. Omitted
settings take the defaults below, so existing schema-3 phrase files still load.
New event IDs are `large_text`, `emoji`, `repeated_mentions`, `apology`, `bargaining`,
`group_incident`, `shorter_this_time`, `emoji_callback`, `single_knock`,
`broken_promise`, `milestone`, and `rare_admission`; each uses the same phrase-list
format under `events`. Empty/remove any pool to disable that response.

```json
"surprises": {
  "large_text_chars": 350,
  "message_one_in": 3,
  "callback_one_in": 12,
  "rare_one_in": 80,
  "rare_min_count": 151,
  "group_window_seconds": 60,
  "group_min_others": 3,
  "milestones": [10, 25, 50, 100, 250, 500, 1000],
  "milestone_every": 1000
}
```

Thresholds and chance denominators are positive integers. `milestones` must be
a strictly increasing list of integers >= 2; it may be empty. `milestone_every`
may be zero to disable recurring milestones; otherwise recurrence begins no
earlier than the final listed milestone. Set a chance denominator to 1 for
deterministic testing. New trigger expressions/conditions require a code edit;
existing pools and settings require only a file edit and restart.

Tier pools must be nonempty. Tier IDs are unique; phrase IDs are unique across
all pools. IDs begin with a lowercase letter and use lowercase letters, digits,
dots, underscores, or hyphens. Keep IDs stable when editing text.
`{count}` and `{others}` are the allowed placeholders; use `{{`/`}}` for literal
braces. Text must fit in 2,000 UTF-16 units after substitution. JSON comments,
unknown fields, duplicate keys/IDs, invalid thresholds, and unsafe placeholders
produce startup errors before the game database is opened.

The draw is deterministic for the same IDs, count, configuration, matching
context, and delivery history. Editing pools can change future choices. The
last five delivered phrase IDs are excluded when possible. Tiny pools relax
the oldest exclusions first, keeping the newest excluded where an alternative exists.
Count-tier draws use SHA-256 over compact JSON `[1,guild,user,count,tier_id]`;
events use `[2,guild,user,count,"event:" + event_id]`. The recent gate uses
`[3,guild,user,count,"recent_gate"]`, modulo `recent_one_in`. Digests use UTF-8
and unsigned big-endian conversion. No shared global RNG is involved.
Encounter gates/choices use `[4,guild,user,count,label]` with separate labels
`message_gate`, `message_choice`, `callback_gate`, `callback_choice`, and `rare_gate`.
Reproducibility also requires matching extracted cues, memories, and recent
participant activity. The draws are pseudorandom probabilities, not schedules.

## Architecture and selection

| Module | Responsibility |
| --- | --- |
| `discordbot.py` / `config.py` | Startup, configuration, minimal intents, and shutdown |
| `cogs/pings.py` | Filter events, route help, extract cues, and send replies |
| `cogs/channels.py` | Supported guild channel types and thread-aware send checks |
| `cogs/welcome.py` | One delayed introduction per actual join, with destination selection and cancellation |
| `nuhuh/signals.py` | Extract small cues without retaining message text |
| `nuhuh/responder.py` | Shared help/game pacing and in-flight send coordination |
| `nuhuh/async_game.py` | Keep SQLite work on one dedicated worker thread |
| `nuhuh/engine.py` | Atomic counting, replay protection, state, and delivery acknowledgement |
| `nuhuh/phrases.py` | Validate editable content and select deterministic replies |
| `nuhuh/cli.py` | Run the same game offline |
| `nuhuh/legal.py` | Shared source URL validation and source/license notices |

Counting and selection use a SQLite `BEGIN IMMEDIATE` transaction. Help and play
share message-ID replay protection over a bounded 24-hour observation window.
Only events received by the running bot count; there is no catch-up history scan.
Only successful delivery records phrase history or a memory setup. Late or
duplicate acknowledgements cannot overwrite newer delivered state. A crash
between sending and acknowledgement can affect repetition avoidance.

The deterministic hash payloads and repetition rules are described under
[Change the voice](#change-the-voice). Data fields and deletion procedures are in
[PRIVACY.md](PRIVACY.md).

## Testing and review

From the repository folder:

```sh
python -m unittest discover -v
python -X dev -W error::ResourceWarning tools/check_resources.py
```

Use the project's virtual-environment Python when testing Discord mode. Without
Discord installed, adapter tests skip; install `requirements.txt` to exercise
the complete suite. Those tests use real library types with fake events/sends
and never log in. The resource runner retains SQLite handles and fails if any
connection was not explicitly closed, including on platforms that let open
files be deleted.

The supplied copy tests check globally unique IDs/text and enough alternatives
for the five-line delivered-history window. They do not fix a total number of
phrases. Valid additions, removals, and rewrites can pass without test edits.
Small custom pools remain supported by the engine and have separate tests.

Try the disposable CLI, context demo, tier tour, and encounter preview. For live
Discord checks, follow the [release checklist](RELEASE_CHECKLIST.md); unit tests
alone do not verify channel permissions, connectivity, or comic timing.

GitHub Actions runs the resource check and previews on Ubuntu/Windows with
Python 3.11/3.13. See the repository's Actions tab for a particular commit's status.
Release changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## Licensing contributions and forks

The first-party code, documentation, and phrase data are offered under
**AGPL-3.0-only** from v0.5.2. Source files carry SPDX notices pointing to
[NOTICE.md](NOTICE.md) and the full [LICENSE](LICENSE). Earlier MIT releases and
separate Unicode terms are documented in the notice; retain applicable notices.

Help copy in `nuhuh/helptext.py` remains title/description/footer. Legal information
is rendered separately by `nuhuh/legal.py`, preserving the persona's closing line.
Offline help retains the full source/license information without importing
Discord or dotenv. Discord help-rendering edits can stay confined to the adapter;
they do not change the persona copy or CLI notices.

## Discord channels and introductions

The adapter accepts `TextChannel` (including announcements), `Thread`,
`VoiceChannel`, and `StageChannel`, while retaining the guild/direct-human-mention
filter. Forum and media posts arrive as threads; their parent containers and
categories are not message destinations. Synthetic thread-starter references
remain excluded so they cannot duplicate the original message's count.

Send eligibility requires View Channel plus Send Messages, or Send Messages in
Threads for threads. Locked/archived threads are observed without attempting a
send. No thread management, member-list, audio, or additional privileged intent
is required. A missing send permission does not drop an observed ping from the
game engine. Guild/user progression is unchanged; channel pacing uses the actual
thread/voice/text channel ID.

`cogs/welcome.py` listens to actual join/removal events rather than `on_ready`.
It tracks pending tasks and seen join IDs in memory. Duplicate join callbacks
produce one attempt per process; removal clears that join, allowing a real
rejoin to introduce again. A pending intro waits asynchronously, resolves the
current guild/destination/permissions, and performs a bounded send. Unload cancels
and drains its tasks before the bot closes its database. It creates no game
state and does not replay pending introductions after restart. See the
[operator guide](OPERATING.md#introduction-on-installation) for routing and config.

When hosting a modified copy, make the corresponding source available to its
users and set `NUHUH_SOURCE_URL` to that version. See the
[operator instructions](OPERATING.md#source-access-and-license). Preserve notices
and identify changes as the license requires. Keep credentials and runtime data
out of published source.
