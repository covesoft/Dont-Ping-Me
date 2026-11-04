# Just Don't

**The name was the instruction.**

Mention the bot. It objects. Mention it again. It remembers.

An ornery red button, worn familiar by people ignoring one very simple request.
It progresses from objection to disbelief, bargaining, bureaucracy, resignation,
and an attachment it would prefer you didn't mention.

Internal project name: **nuhuh**. Current version: **0.5.0**.

## Try it without Discord

Python **3.11+** is enough. No packages, token, account, network connection,
or bot installation are required for terminal play.

```sh
git clone https://github.com/covesoft/Dont-Ping-Me.git
cd Dont-Ping-Me
python -m nuhuh --demo
```

Use `python3` or `py` if that is your system's command. Two more ways to play:

```sh
python -m nuhuh --tour
python -m nuhuh --encounters
python -m nuhuh
```

`--tour` previews one line from every count tier without changing saved data.
`--encounters` previews special-reaction copy, explicitly bypassing its triggers
and probability gates, also without changing saved data. It contains spoilers.
`--demo` uses a disposable game and virtual clock to demonstrate context events
and the mix of recent-ping and tier replies. Both use the actual phrase selector.

In interactive play, press **Enter** to ping, type a message to try its reactions,
use `/quit` to leave, or `/wait 86401`
to simulate just over a day away. No real waiting occurs. Counts persist in
`.nuhuh/demo.sqlite3` beneath your current folder. Resume by running again.

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

## The personality

There are **243 phrases**: 95 across six count tiers, 40 across five context
pools, 12 for overly elaborate help requests, and 96 for message reactions,
callbacks, milestones, and rare admissions. Each guild/user relationship progresses separately.

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

Participants means people who have pinged in that guild. No member roster is
needed. Each new qualifying game message counts once, even if it mentions the bot
several times. Exact help requests do not count. Suppressed or unsent responses still count. Only events observed
by the running bot are tracked; there is no retrospective history scan.

## Discoveries and callbacks

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

<details>
<summary>Developer spoilers: reactions, memories, and priority</summary>

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

</details>

## Run the Discord bot

For a fresh installation, create a venv and copy `.env.example` to `.env`.
Put your token in `NUHUH_DISCORD_TOKEN`. An existing `.env` can be kept.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your private token.
.\.venv\Scripts\python.exe discordbot.py
```

Linux/macOS:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
# Edit .env with your private token.
.venv/bin/python discordbot.py
```

`config.py` loads dotenv and exposes paths and pacing constants. Environment
variables already set by the host take precedence. The real `.env` and runtime
data are excluded from Git.

Install to a guild with the `bot` OAuth scope. In an ordinary text channel,
grant **View Channel**, **Send Messages**, and **Embed Links** for the help card
(permission integer `19456`). Plain game replies and plain-text help need only
View Channel and Send Messages (`3072`). Leave
privileged intents disabled: the code enables only Guilds and Guild Messages.
No administrator, message-history, or mention-everyone permission is needed.
Help falls back to plain text if Embed Links is unavailable in the channel.
No slash commands need syncing.

The bot handles direct human mentions in ordinary guild text channels. It
ignores DMs, threads, bots, webhooks, system messages, edits, and role/everyone
mentions. Pinging replies qualify if the bot is in the user-mention list;
non-pinging replies do not. Outgoing mention notifications are disabled.

Defaults: **5 seconds between attempts per guild/user**, **2 seconds per
channel**, and a **15-second send timeout**. Attempt reservations persist across
restarts, including failed attempts. In-flight sends suppress further responses
for that user or channel while independent users/channels proceed. Nothing
queues a backlog of jokes. Ctrl+C drains handlers and closes the database.
Run one process per token/database. See [DEPLOYMENT.md](DEPLOYMENT.md) for Linux hosting.

## Mention help

| Message | Response | Counts as play? |
| --- | --- | --- |
| `@bot help`, with no prior pings here | Friendly help embed | No |
| `@bot help`, after pinging in this guild | Snarkier refresher embed | No |
| `@bot help me please`, or other extra wording | A line from `events.help_extra` | Yes |

Use a leading direct bot mention followed by the word `help`. Case and outer
whitespace do not matter. Extra punctuation or another mention also counts as
extra wording. Words such as `helpful` are ordinary game messages. Help does not
advance counts, update last-ping time, or add someone to the participant roster.
Help and play share the existing response cooldowns, in-flight protection, and
replay window; give the bot five seconds between responses when testing.

Only messages already identified as mentioning the bot have their text inspected
for help routing and game cues. Discord exposes that text without the Message Content intent.
The words are not stored or repeated back. Help copy lives in
`nuhuh/helptext.py`; extra-help lines remain developer-editable JSON. An empty
or missing `help_extra` pool falls back to normal play. This explicit response
pool overrides context and surprise events when enabled, including on a user's first ping.

For offline play use `/help` and `/help me please`. The former shows the same
friendly/refresher text without counting, and the latter counts as a ping.

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

## Data and alpha resets

Bot data lives in `.nuhuh/bot.sqlite3`, anchored to the project folder. CLI
simulation data is separate. See [PRIVACY.md](PRIVACY.md) for stored fields,
retention, and deletion procedures.

Empty databases initialize directly with schema 5. This alpha update needs a
one-time reset of older schema-1/2/3/4 databases. Schema 5 adds bounded encounter
memories; help-only pacing remains separate from participant records.
There is **no migration code**: older versions or nonempty unversioned databases get a reset instruction. Stop the program, remove the
identified alpha database and matching sidecars, then restart. Never delete a
live database. Old version-1/2 phrase files should be replaced with the supplied
version-3 file before further customization.

## Tests and release

```sh
python -m unittest discover -v
python -X dev -W error::ResourceWarning tools/check_resources.py
```

The resource runner retains connection objects and fails if any SQLite handle
was not explicitly closed. This catches leaks even on platforms that allow
open files to be deleted. With requirements installed, tests include real
Discord-library lifecycle checks using fake messages/sends; no login occurs.
Without Discord, the adapter tests skip and the offline tests still run.

GitHub Actions is configured for Ubuntu/Windows and Python 3.11/3.13. The
workflow runs after these changes are pushed; configuration is not a claim that
hosted CI has already passed. See [CHANGELOG.md](CHANGELOG.md),
[RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), and [SUBMISSION.md](SUBMISSION.md).
The private planning bible remains under ignored `docs/`.

MIT licensed. See [LICENSE](LICENSE).
