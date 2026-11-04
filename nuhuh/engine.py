"""Transport-independent counting, selection, and delivery acknowledgement.

Each ping() call represents one qualifying interaction. A Discord adapter must
filter/deduplicate gateway events and apply cooldowns before sending a reply.
"""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from .phrases import MAX_COUNT, PhraseBook


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
                if version not in (0, 1):
                    raise ValueError(f"Unsupported database schema version {version}")
                self._db.execute("""
                    CREATE TABLE IF NOT EXISTS relationships (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        count INTEGER NOT NULL CHECK (count >= 1),
                        last_phrase_id TEXT,
                        last_reply_count INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (guild_id, user_id)
                    )
                """)
                self._db.execute("PRAGMA user_version = 1")
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
            self._db.execute("ROLLBACK")
            raise

    def ping(self, guild_id: int, user_id: int) -> Reply:
        """Count and choose a reply; this does not claim it was delivered."""
        positive_id(guild_id)
        positive_id(user_id)
        with self._transaction():
            row = self._db.execute(
                "SELECT count, last_phrase_id FROM relationships WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            ).fetchone()
            count, last_id = (row[0] + 1, row[1]) if row else (1, None)
            if count > MAX_COUNT:
                raise ValueError("This relationship has reached the maximum supported count")
            tier, phrase = self.phrases.select(guild_id, user_id, count, last_id)
            self._db.execute(
                """INSERT INTO relationships (guild_id, user_id, count) VALUES (?, ?, ?)
                   ON CONFLICT (guild_id, user_id) DO UPDATE SET count=excluded.count""",
                (guild_id, user_id, count),
            )
        return Reply(guild_id, user_id, count, tier.id, phrase.id, phrase.text.format(count=count))

    def delivered(self, reply: Reply) -> None:
        """Record only successful sends; older acknowledgements cannot overwrite newer ones."""
        with self._transaction():
            self._db.execute(
                """UPDATE relationships SET last_phrase_id=?, last_reply_count=?
                   WHERE guild_id=? AND user_id=? AND count>=? AND last_reply_count<?""",
                (reply.phrase_id, reply.count, reply.guild_id, reply.user_id, reply.count, reply.count),
            )

    def close(self) -> None:
        self._db.close()

    def __enter__(self) -> "Game":
        return self

    def __exit__(self, *args) -> None:
        self.close()
