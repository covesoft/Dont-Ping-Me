# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

from contextlib import closing
from dataclasses import replace
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
        self.always_recent = PhraseBook(self.book.tiers, self.book.events, replace(self.book.rules, recent_one_in=1))

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
            with self.subTest(gap=gap), Game(self.always_recent) as game:
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

    def test_legacy_schema_is_rejected_without_migration_or_file_leak(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "old.sqlite3"
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("CREATE TABLE original (value TEXT)")
                db.execute("INSERT INTO original VALUES ('preserve')")
                db.execute("PRAGMA user_version = 1")
            with self.assertRaisesRegex(ValueError, "Stop the program, delete"):
                Game(self.book, database)
            with closing(sqlite3.connect(database)) as db, db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)
                self.assertEqual(db.execute("SELECT value FROM original").fetchone()[0], "preserve")
            # Windows permits deletion only if the rejected connection was closed.
            database.unlink()

    def test_unversioned_existing_database_is_not_silently_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "unknown.sqlite3"
            with closing(sqlite3.connect(database)) as db, db:
                db.execute("CREATE TABLE unrelated (value TEXT)")
            with self.assertRaisesRegex(ValueError, "migration is intentionally not supported"):
                Game(self.book, database)

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

    def test_recent_chance_and_current_file_version_are_validated(self):
        raw = json.loads(DEFAULT_PHRASES.read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "phrases.json"
            for bad in (0, -1, True, 1.5, "3"):
                with self.subTest(bad=bad):
                    raw["context"]["recent_one_in"] = bad
                    path.write_text(json.dumps(raw))
                    with self.assertRaisesRegex(PhraseError, "recent_one_in"):
                        PhraseBook.load(path)
            raw["schema_version"] = 2
            path.write_text(json.dumps(raw))
            with self.assertRaisesRegex(PhraseError, "schema_version must be 3"):
                PhraseBook.load(path)
