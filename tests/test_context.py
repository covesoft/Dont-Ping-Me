import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nuhuh.engine import DEDUPE_SECONDS, Game
from nuhuh.phrases import DEFAULT_PHRASES, PhraseBook, PhraseError


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.book = PhraseBook.load()

    def test_first_guild_new_user_and_crowd_threshold(self):
        with Game(self.book) as game:
            self.assertEqual(game.ping(1, 1, now=1000).event_id, "first_guild_ping")
            for user in range(2, 6):
                reply = game.ping(1, user, now=1000)
                self.assertEqual(reply.event_id, "first_user_ping")
                self.assertEqual(reply.other_users, user - 1)
            sixth = game.ping(1, 6, now=1000)
            self.assertEqual((sixth.event_id, sixth.other_users), ("new_user_in_crowd", 5))
            self.assertEqual(game.ping(2, 6, now=1000).event_id, "first_guild_ping")
            self.assertEqual(game.ping(1, 6, now=1300).event_id, None)

    def test_recent_and_day_boundaries(self):
        for gap, expected in [(0, "recent_ping"), (120, "recent_ping"), (121, None),
                              (86400, None), (86401, "returning_user")]:
            with self.subTest(gap=gap), Game(self.book) as game:
                game.ping(1, 1, now=1000)
                self.assertEqual(game.ping(1, 1, now=1000 + gap).event_id, expected)

    def test_event_priority_falls_through_when_pool_disabled(self):
        pools = tuple(pool for pool in self.book.events if pool.id != "first_guild_ping")
        with Game(PhraseBook(self.book.tiers, pools, self.book.rules)) as game:
            self.assertEqual(game.ping(1, 1, now=1000).event_id, "first_user_ping")
        with Game(PhraseBook(self.book.tiers)) as game:
            self.assertIsNone(game.ping(1, 1, now=1000).event_id)

    def test_context_survives_restart_and_backward_clock_cannot_rewind_last_ping(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "game.sqlite3"
            with Game(self.book, database) as game:
                game.ping(1, 1, now=1000)
                game.ping(1, 1, now=900)
            with Game(self.book, database) as game:
                self.assertIsNone(game.ping(1, 1, now=87400).event_id)
                self.assertEqual(game.ping(1, 1, now=173801).event_id, "returning_user")

    def test_replayed_message_is_deduplicated_across_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "game.sqlite3"
            with Game(self.book, database) as game:
                self.assertEqual(game.ping(1, 1, now=1000, message_id=99).count, 1)
            with Game(self.book, database) as game:
                self.assertIsNone(game.ping(1, 1, now=1001, message_id=99))
                self.assertEqual(game.ping(1, 1, now=1002, message_id=100).count, 2)
                # Replays beyond the bounded observation window may count again.
                self.assertEqual(game.ping(1, 1, now=1000 + DEDUPE_SECONDS + 1, message_id=99).count, 3)

    def test_schema_one_migrates_without_resetting_counts_or_inventing_absence(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "old.sqlite3"
            with sqlite3.connect(database) as db:
                db.execute("""CREATE TABLE relationships (
                    guild_id INTEGER, user_id INTEGER, count INTEGER,
                    last_phrase_id TEXT, last_reply_count INTEGER DEFAULT 0,
                    PRIMARY KEY(guild_id, user_id))""")
                db.execute("INSERT INTO relationships VALUES (1, 1, 10, 'old.phrase', 10)")
                db.execute("PRAGMA user_version = 1")
            with Game(self.book, database) as game:
                reply = game.ping(1, 1, now=1000000)
                self.assertEqual(reply.count, 11)
                self.assertIsNone(reply.event_id)
                self.assertEqual(game.ping(1, 2, now=1000000).event_id, "first_user_ping")
            with sqlite3.connect(database) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 2)

    def test_cooldowns_are_atomic_persistent_and_allow_exact_boundary(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "game.sqlite3"
            with Game(self.book, database) as game:
                first = game.ping(1, 1, now=1000)
                self.assertTrue(game.claim_response(first, 10, now=1000))
                other = game.ping(1, 2, now=1001)
                self.assertFalse(game.claim_response(other, 10, now=1001))
                self.assertTrue(game.claim_response(other, 11, now=1001))
            with Game(self.book, database) as game:
                again = game.ping(1, 1, now=1004)
                self.assertFalse(game.claim_response(again, 11, now=1004))
                self.assertTrue(game.claim_response(again, 11, now=1005))

    def test_invalid_event_config_and_unknown_placeholders_are_rejected(self):
        raw = json.loads(DEFAULT_PHRASES.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for change in ("unknown_event", "overlap", "empty_disabled", "duplicate_id"):
                data = json.loads(json.dumps(raw))
                if change == "unknown_event":
                    data["events"]["typo"] = []
                elif change == "overlap":
                    data["context"]["recent_seconds"] = 86400
                elif change == "empty_disabled":
                    data["events"]["first_guild_ping"] = []
                else:
                    data["events"]["first_guild_ping"][0]["id"] = data["tiers"][0]["phrases"][0]["id"]
                path.write_text(json.dumps(data))
                if change == "empty_disabled":
                    book = PhraseBook.load(path)
                    self.assertNotIn("first_guild_ping", {event.id for event in book.events})
                else:
                    with self.subTest(change=change), self.assertRaises(PhraseError):
                        PhraseBook.load(path)
