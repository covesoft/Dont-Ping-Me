# Data and privacy

Just Don't remembers its own interactions. It examines the text of direct
human mentions to distinguish help requests and extract game cues: message length,
emoji, repeated mentions, and a few whole short apology/bargaining expressions.
It does not request Discord's privileged Message Content, Members, or
Presences intents. Other guild message events still reach the application;
messages without a direct mention are immediately ignored without inspecting
content. Mention text is not stored.

For a qualifying human mention in a supported guild message channel (including
threads, forum posts, and voice/stage text chat), the bot stores:

- Guild and user IDs, interaction count, and last observed ping timestamp.
- Last delivered phrase ID, count at delivery, and up to five recently
  delivered phrase IDs for repetition avoidance.
- Guild/user IDs and last response-attempt time for shared help/game pacing,
  including help-only users. Exact help requests do not create participants.
- Guild/channel IDs and the last channel response-attempt time for pacing.
- Message IDs and observation timestamps for a bounded replay window.
- Up to four guild/user memory tags (`large_text`, `emoji`, `repeated_mentions`,
  `apology`) and their setup interaction counts, established only after the
  corresponding response is delivered. A delivered callback consumes its tag;
  a later delivered setup may renew it. No message excerpt is retained.

It does not store message bodies, attachments, usernames, guild names, or a
member roster. Other participants are counted from the bot's own interaction
records. There is no publicly invocable global list of guilds or players, no
analytics service, and no generative-AI service used to produce replies at runtime.
Operational logs may contain guild/channel IDs and error information.

Configured bot owners can request connected guild names/cached member counts
or aggregate pester statistics through exact mention commands. Reports appear
in the invoking channel and are visible to people with channel access. Guild
names/member rosters are not stored for this feature. Statistics read existing
counts, including retained relationships from guilds the bot has left; they do
not create or advance participants. Owner requests use the existing bounded
replay and response-attempt records. No lifetime installation log is added.

On a new guild join, the bot may send one delayed introduction to the system
channel or a clearly named bot channel. Routing uses channel metadata and send
permissions, not surrounding chat or a member roster. Pending/handled join IDs
are kept in memory until removal or shutdown; introductions create no persistent
game records and send no DMs.

## Retention

Relationships persist until an operator deletes them. Removing the bot from a
guild does not automatically delete its stored relationships.
Memory tags persist until consumed or deleted; they are never shared across
guilds or users. Group-incident selection counts distinct other participants'
existing ping timestamps within a configurable 60-second window. It creates no
separate activity log, roster, or ordinary-message history.

Replay IDs are retained for a 24-hour observation window and pruned when another
qualifying mention is processed. Idle databases can therefore retain expired
rows until activity resumes. User/channel pacing records older than one day, or the respective configured
cooldown if longer, are pruned on subsequent response claims.

## Access and deletion

The operator of each hosted copy controls its local SQLite database and any
backups. For data removal, contact that copy's operator. There is no public
data-deletion command in this release.

Self-hosted operators can stop the bot and execute parameterized SQLite statements:

```python
from contextlib import closing
import sqlite3

with closing(sqlite3.connect(".nuhuh/bot.sqlite3")) as db, db:
    db.execute("DELETE FROM relationships WHERE user_id = ?", (USER_ID,))
    db.execute("DELETE FROM user_state WHERE user_id = ?", (USER_ID,))
    db.execute("DELETE FROM memories WHERE user_id = ?", (USER_ID,))
```

Replace `USER_ID` with the person's numeric Discord ID. To remove a guild's data,
delete its rows from `relationships`, `user_state`, `channel_state`, and `memories` using
`guild_id = ?`.
Replay rows contain no user/guild mapping; they expire through the window above
or can be cleared as a whole. Apply the same deletion to any retained backups.
Deleting a relationship makes the next interaction a first encounter again.

To reset an alpha database completely, stop the program, then delete the relevant
database and matching SQLite sidecars. Never remove a live database underneath
a running process. The default bot database is `.nuhuh/bot.sqlite3`, anchored to
the project folder; the CLI uses a separate `.nuhuh/demo.sqlite3` by default.

Discord separately processes messages and bot interactions under its own terms.
