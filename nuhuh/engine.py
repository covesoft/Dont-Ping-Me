"""Transport-independent counting, selection, and delivery acknowledgement.

Each ping() call represents one qualifying interaction. Adapters filter events,
supply optional message IDs for replay protection, and claim cooldown reservations
before sending. Offline play skips response pacing.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import math
import json
import sqlite3
import time

from .phrases import Context, MAX_COUNT, PhraseBook

DEDUPE_SECONDS = 86400
HISTORY_LIMIT = 5


def timestamp(value: float | None) -> float:
    value = time.time() if value is None else value
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("Time must be a finite, nonnegative Unix timestamp")
    return float(value)


def positive_id(value: int) -> int:
    if type(value) is not int or not 1 <= value <= MAX_COUNT:
        raise ValueError(f"IDs must be integers between 1 and {MAX_COUNT}")
    return value


@dataclass(frozen=True)
class Reply:
    guild_id: int
    user_id: int
    count: int
    tier_id: str
    phrase_id: str
    text: str
    event_id: str | None = None
    other_users: int = 0


class Game:
    """One SQLite connection; use from one thread and close after use.

    Independent Game connections can safely share a database. Counting and
    selection use BEGIN IMMEDIATE. Send coordination is the adapter's job.
    """

    def __init__(self, phrases: PhraseBook, database: str | Path = ":memory:") -> None:
        self.phrases = phrases
        self._db = sqlite3.connect(str(database), timeout=10, isolation_level=None)
        try:
            with self._transaction():
                version = self._db.execute("PRAGMA user_version").fetchone()[0]
                tables = self._db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if version not in (0, 3) or (version == 0 and tables):
                    raise ValueError(
                        f"Unsupported alpha database schema {version} at {database}. "
                        "Stop the program, delete this database and its matching sidecars, then restart. "
                        "Automatic migration is intentionally not supported."
                    )
                self._db.execute("""
                    CREATE TABLE IF NOT EXISTS relationships (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        count INTEGER NOT NULL CHECK (count >= 1),
                        last_phrase_id TEXT,
                        last_reply_count INTEGER NOT NULL DEFAULT 0,
                        last_ping_at REAL,
                        last_attempt_at REAL,
                        recent_phrase_ids TEXT NOT NULL DEFAULT '[]',
                        PRIMARY KEY (guild_id, user_id)
                    )
                """)
                self._db.execute("""CREATE TABLE IF NOT EXISTS seen_messages (
                    message_id INTEGER PRIMARY KEY, observed_at REAL NOT NULL
                )""")
                self._db.execute("CREATE INDEX IF NOT EXISTS seen_age ON seen_messages(observed_at)")
                self._db.execute("""CREATE TABLE IF NOT EXISTS channel_state (
                    guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                    last_attempt_at REAL NOT NULL, PRIMARY KEY(guild_id, channel_id)
                )""")
                self._db.execute("PRAGMA user_version = 3")
        except BaseException:
            self._db.close()
            raise

    @contextmanager
    def _transaction(self):
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def ping(self, guild_id: int, user_id: int, *, now: float | None = None, message_id: int | None = None) -> Reply | None:
        """Count and choose, or return None for a known message ID; delivery is separate."""
        positive_id(guild_id)
        positive_id(user_id)
        now = timestamp(now)
        if message_id is not None:
            positive_id(message_id)
        with self._transaction():
            if message_id is not None:
                self._db.execute("DELETE FROM seen_messages WHERE observed_at < ?", (now - DEDUPE_SECONDS,))
                inserted = self._db.execute(
                    "INSERT OR IGNORE INTO seen_messages(message_id, observed_at) VALUES (?, ?)",
                    (message_id, now),
                ).rowcount
                if not inserted:
                    return None
            row = self._db.execute(
                "SELECT count, last_phrase_id, last_ping_at, recent_phrase_ids FROM relationships WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
            count, last_id = (row[0] + 1, row[1]) if row else (1, None)
            if count > MAX_COUNT:
                raise ValueError("This relationship has reached the maximum supported count")
            participants = self._db.execute(
                "SELECT COUNT(*) FROM relationships WHERE guild_id=?", (guild_id,)
            ).fetchone()[0]
            other_users = participants - int(row is not None)
            elapsed = max(0, now - row[2]) if row and row[2] is not None else None
            context = Context(participants == 0, row is None, other_users, elapsed)
            event_id = self.phrases.event_for(context, guild_id, user_id, count)
            recent = tuple(json.loads(row[3])) if row else ()
            tier, phrase = self.phrases.select(guild_id, user_id, count, last_id, recent_phrase_ids=recent)
            if event_id:
                phrase = self.phrases.select_event(event_id, guild_id, user_id, count, last_id, recent_phrase_ids=recent)
            last_ping_at = max(now, row[2]) if row and row[2] is not None else now
            self._db.execute(
                """INSERT INTO relationships (guild_id, user_id, count, last_ping_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT (guild_id, user_id) DO UPDATE SET count=excluded.count, last_ping_at=excluded.last_ping_at""",
                (guild_id, user_id, count, last_ping_at),
            )
        text = phrase.text.format(count=count, others=other_users)
        return Reply(guild_id, user_id, count, tier.id, phrase.id, text, event_id, other_users)

    def claim_response(self, reply: Reply, channel_id: int, *, now: float | None = None,
                       user_cooldown: float = 5, channel_cooldown: float = 2) -> bool:
        """Atomically reserve a response attempt. Failed attempts also consume cooldown."""
        positive_id(channel_id)
        now = timestamp(now)
        for value in (user_cooldown, channel_cooldown):
            timestamp(value)  # Validate finite nonnegative durations as well.
        with self._transaction():
            user = self._db.execute(
                "SELECT last_attempt_at FROM relationships WHERE guild_id=? AND user_id=?",
                (reply.guild_id, reply.user_id),
            ).fetchone()
            if user is None:
                return False
            self._db.execute("DELETE FROM channel_state WHERE last_attempt_at < ?", (now - max(channel_cooldown, 86400),))
            channel = self._db.execute(
                "SELECT last_attempt_at FROM channel_state WHERE guild_id=? AND channel_id=?",
                (reply.guild_id, channel_id),
            ).fetchone()
            if (user[0] is not None and now < user[0] + user_cooldown) or (channel and now < channel[0] + channel_cooldown):
                return False
            self._db.execute(
                "UPDATE relationships SET last_attempt_at=? WHERE guild_id=? AND user_id=?",
                (now, reply.guild_id, reply.user_id),
            )
            self._db.execute(
                """INSERT INTO channel_state(guild_id, channel_id, last_attempt_at) VALUES (?, ?, ?)
                   ON CONFLICT(guild_id, channel_id) DO UPDATE SET last_attempt_at=excluded.last_attempt_at""",
                (reply.guild_id, channel_id, now),
            )
            return True

    def delivered(self, reply: Reply) -> None:
        """Remember successful replies only; older acknowledgements cannot overwrite newer ones."""
        with self._transaction():
            row = self._db.execute(
                """SELECT recent_phrase_ids FROM relationships
                   WHERE guild_id=? AND user_id=? AND count>=? AND last_reply_count<?""",
                (reply.guild_id, reply.user_id, reply.count, reply.count),
            ).fetchone()
            if row is None:
                return
            recent = (json.loads(row[0]) + [reply.phrase_id])[-HISTORY_LIMIT:]
            self._db.execute(
                """UPDATE relationships SET last_phrase_id=?, last_reply_count=?, recent_phrase_ids=?
                   WHERE guild_id=? AND user_id=?""",
                (reply.phrase_id, reply.count, json.dumps(recent), reply.guild_id, reply.user_id),
            )

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "Game":
        return self

    def __exit__(self, *args) -> None:
        self.close()
