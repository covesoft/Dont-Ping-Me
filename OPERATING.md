# Running Just Don't

This guide covers a local Discord installation and its day-to-day operation.
Start with the [README](README.md) for the game, or the
[developer guide](DEVELOPING.md) for customization and offline review.

## Install and configure

You need Python 3.11 or later, the project files, and a Discord application with
a bot account. Run the commands below from the repository folder. The copy
commands are for a fresh installation; preserve an existing `.env` on updates.

Create a virtual environment and put your token in `NUHUH_DISCORD_TOKEN` in
`.env` before starting the bot.

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
View Channel and Send Messages (`3072`). Leave privileged intents disabled:
the code enables only Guilds and Guild Messages.
No administrator, message-history, or mention-everyone permission is needed.
Help falls back to plain text if Embed Links is unavailable in the channel.
No slash commands need syncing.

For threads and forum posts, also grant **Send Messages in Threads**. With the
three permissions above, the combined invite integer is `274877926400`.
Threads use this permission instead of ordinary Send Messages. The bot needs
access to the parent channel and an invitation to participate in private threads;
it does not need Manage Threads. It will not send into locked or archived threads.

The bot handles direct human mentions in text/announcement channels, public or
accessible private threads, forum-post threads, and voice/stage text chat. It
does not join audio. Forum/media containers and categories cannot receive game
messages directly; their post threads can. DMs, bots, webhooks, synthetic system
messages, edits, and role/everyone mentions remain ignored. Pinging replies
qualify if the bot is in the user-mention list. Outgoing mention notifications
are disabled.

Relationships remain per guild/user across all these surfaces. Each thread or
voice chat has its own channel cooldown; the same person's guild cooldown still
applies across channels. Observed game pings continue to count when sending is
unavailable, with no response queued for later.

Defaults: **5 seconds between attempts per guild/user**, **2 seconds per
channel**, and a **15-second send timeout**. Attempt reservations persist across
restarts, including failed attempts. In-flight sends suppress further responses
for that user or channel while independent users/channels proceed. Nothing
queues a backlog of jokes. Ctrl+C drains handlers and closes the database.
Run one process per token/database. See [DEPLOYMENT.md](DEPLOYMENT.md) for Linux hosting.

## Introduction on installation

After an actual guild join, the bot waits 15 seconds and sends one short,
plain-text introduction. It explains the game, mention-help, and channel access
controls without pinging anyone or requiring Embed Links.

It first tries the writable system channel. If unavailable, it looks through
the guild's text channels in order for a writable name containing `bot` or `bots`
as a separate word, such as `bot-commands` or `🤖-bots`. Rules and public-updates
channels are excluded. It skips and logs when neither destination is suitable;
it does not choose an arbitrary general channel or send DMs.

Ordinary startup/reconnect events do not schedule introductions, so existing
installations receive no retroactive announcement. Duplicate join callbacks
within a process do not repeat a send or failed attempt. A real removal/rejoin
can introduce again. Removal and cog unload/shutdown cancel pending work; the
destination and permissions are checked after the delay. Pending introductions
are not restored after a process restart.

Set `INTRODUCTIONS_ENABLED = False` in `config.py` to disable them, or adjust
`INTRO_DELAY_SECONDS`. The existing `SEND_TIMEOUT_SECONDS` bounds the send.
The introduction copy is in `cogs/welcome.py`. It does not create participants,
change game counts, or use a database table.

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
for help routing and game cues. Discord exposes that text without the privileged
Message Content intent.
The words are not stored or repeated back. Help copy lives in
`nuhuh/helptext.py`; extra-help lines remain developer-editable JSON. An empty
or missing `help_extra` pool falls back to normal play. This explicit response
pool overrides context and surprise events when enabled, including on a user's
first ping.

For offline play use `/help` and `/help me please`. The former shows the same
friendly/refresher text without counting, and the latter counts as a ping.

## Bot-owner oversight

Set `OWNER_IDS` in `.env` to comma-separated Discord user IDs. `config.OWNER_IDS`
is the resulting list of integers; an empty list disables owner commands. This
means the bot's configured owners, regardless of server role or permissions.

| Exact mentioned command | Owner response |
| --- | --- |
| `@Just Don't guilds` | Current connected guild names and cached member counts, alphabetically listed across messages as needed |
| `@Just Don't size` | Total recorded pesters, recorded guilds/relationships, and max/p95/average/median/mode distributions |

Choose the actual bot mention. Commands are case-insensitive and require just
the mention plus the command; extra words go through normal gameplay. These
commands are not added to public game help. They reply in the invoking channel,
so the report is visible to people with access to that channel. Outgoing mention
notifications remain disabled, and Embed Links is not required.

An owner's exact report request does **not** add a pester or participant. Other
users sending the same command still play normally, including count/cooldown
behavior; server administrators have no special bypass unless listed in
`OWNER_IDS`. Owners' ordinary pings still count. Reports share help/game replay
protection, response cooldowns, timeout, permissions, and shutdown handling.

`size` reads stored relationship counts, including guilds the bot has left and
counts whose replies were suppressed or failed. It excludes exact help and owner
reports. The two distributions are explicitly **per recorded guild** and **per
guild/user relationship**; a person in two guilds has two relationships. p95
uses nearest rank; mode is shown only when unique, and averages/medians use up
to two decimals. An empty database shows a friendly zero-data report.

Recorded guilds means guilds with at least one stored pester, not every guild
ever joined. Zero-play installations are not tracked historically. Cached member
counts may be unavailable or stale; no member roster is fetched, no privileged
intent is added, and the database schema remains unchanged.

## Source access and license

The first-party project is offered under **AGPL-3.0-only** from v0.5.2. See
[LICENSE](LICENSE), [NOTICE.md](NOTICE.md), and the separate
[Unicode notice](THIRD_PARTY_NOTICES.md).

The CLI retains source, copyright, redistribution, and no-warranty information
in offline `/help` and `python -m nuhuh --help`. Source URL configuration is
shared with the Discord adapter; its presentation can remain separate from the
game's title, description, and persona footer.

`NUHUH_SOURCE_URL` defaults to `https://github.com/covesoft/Dont-Ping-Me`.
Configure it in the Discord bot's `.env` or host environment to point to a
public source location for the actual running version. Prefer a commit, release,
or archive URL. When running a modified fork, publish its corresponding source
and change this URL; pointing only to unmodified upstream code is insufficient.
Include custom phrase files needed to run your version, while keeping tokens,
databases, logs, and private runtime data out of the source publication.

The URL must use HTTPS, contain no credentials/whitespace/angle brackets, and
fit within 500 UTF-16 units so the help card remains valid. Startup validates
this shape without fetching the page. Check public accessibility and content
yourself before deployment. The CLI reads this variable from its process
environment; it does not load dotenv or require an additional package.

## Data, updates, and backups

Bot data lives in `.nuhuh/bot.sqlite3`, anchored to the project folder. CLI
simulation data is separate. See [PRIVACY.md](PRIVACY.md) for stored fields,
retention, and deletion procedures.

Empty databases initialize directly with schema 5. Older schema-1/2/3/4 databases
require an alpha reset. Schema 5 adds bounded encounter memories; help-only
pacing remains separate from participant records.
There is **no migration code**: older versions or nonempty unversioned databases
get a reset instruction. Stop the program, remove the identified alpha database
and matching sidecars, then restart. Never delete a live database. Old
version-1/2 phrase files should be replaced with the supplied version-3 file
before further customization.

A compatible code/documentation update does not require a database reset.
To update, stop the bot, review/pull the new code, install requirements with the
same virtual environment, and restart. Preserve `.env` and the database unless
the release explicitly requires an alpha reset.

For a simple consistent backup, stop the bot, copy its database, then restart.
Keep backups private. [PRIVACY.md](PRIVACY.md) describes stored fields, retention,
and parameterized record-deletion procedures, including retained backups.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Startup reports a missing token | Set `NUHUH_DISCORD_TOKEN` in `.env` or the host environment; run from the project folder |
| No response to a ping | Use an actual direct mention in a supported guild channel; check View Channel and the appropriate send permission, then allow five seconds |
| Thread/post replies are silent | Grant Send Messages in Threads; check access, private-thread invitation, and locked/archived state |
| No introduction on startup | Introductions are scheduled only by actual joins; check the system/bot-channel destination and config switch for a new installation |
| A matching message gets an ordinary reply | Special reactions are probabilistic; first contact and returns have higher priority |
| Help appears as plain text | Enable Embed Links in that channel for the help card |
| Startup reports invalid phrases | Follow the field/ID named in the error; phrase validation runs before the game database opens |
| Startup reports an incompatible alpha schema | Follow the stopped-process reset procedure above, using the path in the error |
| Replies fail or time out | Check channel permissions and connection health; failed attempts consume pacing time |

For verification commands, see [testing and review](DEVELOPING.md#testing-and-review).
