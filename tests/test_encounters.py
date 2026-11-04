# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Message cues, deterministic surprises, and delivery-aware memory."""

from contextlib import closing
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nuhuh.engine import Game
from nuhuh.phrases import CONTEXT_EVENT_IDS, MEMORY_EVENTS, PhraseBook, PhraseError
from nuhuh.signals import Signals, has_emoji, message_signals


class SignalTests(unittest.TestCase):
    def test_real_emoji_and_custom_markup_without_treating_normal_unicode_as_emoji(self):
        for content in ("hi 😀", "👩🏽‍🚀", "🏳️‍🌈", "🇨🇦", "❤️", "©️", "1️⃣", "#⃣",
                        "<:hello:1234>", "<a:dance:1234>", "🫩"):
            with self.subTest(content=content):
                self.assertTrue(has_emoji(content))
        for content in ("Hello, 世界! café", "123 # *", "© 2026", "™", "❤\ufe0e",
                        ":smile:", "<:missing_id:>", "1\ufe0f", "\ufe0f"):
            with self.subTest(content=content):
                self.assertFalse(has_emoji(content))

    def test_whole_expressions_and_literal_bot_mentions_only(self):
        for text in ("<@99> sorry!", "I’M SORRY <@!99>", "<@99> my   bad."):
            with self.subTest(text=text):
                self.assertTrue(message_signals(text, 99).apology)
        for text in ("<@99> not sorry", '<@99> "sorry"', "<@99> I'm sorry you feel that way",
                     "<@99> https://example.test/sorry", "<@99> `sorry`"):
            with self.subTest(text=text):
                self.assertFalse(message_signals(text, 99).apology)
        self.assertTrue(message_signals("<@99> just this once?", 99).bargaining)
        self.assertFalse(message_signals("<@99> please read my announcement", 99).bargaining)
        signals = message_signals("<@99> <@!99> <@9> <@&99> 😀", 99)
        self.assertEqual(signals.mentions, 2)
        self.assertTrue(signals.emoji)
        self.assertEqual(signals.characters, len("<@99> <@!99> <@9> <@&99> 😀"))


class EncounterTests(unittest.TestCase):
    def setUp(self):
        self.base = PhraseBook.load()

    def book(self, *events, **settings):
        pools = tuple(p for p in self.base.events if p.id in events)
        rules = replace(self.base.surprises, message_one_in=1, callback_one_in=1,
                        milestones=(), milestone_every=0)
        return replace(self.base, events=pools, surprises=replace(rules, **settings))

    def test_message_cues_and_exact_length_boundary(self):
        cases = [(Signals(characters=349), None), (Signals(characters=350), "large_text"),
                 (Signals(emoji=True), "emoji"), (Signals(mentions=2), "repeated_mentions"),
                 (Signals(apology=True), "apology"), (Signals(bargaining=True), "bargaining")]
        book = self.book("large_text", "emoji", "repeated_mentions", "apology", "bargaining")
        for signals, expected in cases:
            with self.subTest(signals=signals), Game(book) as game:
                self.assertEqual(game.ping(1, 1, signals=signals).event_id, expected)

    def test_disabled_message_pools_fall_back_and_old_custom_files_still_load(self):
        with Game(replace(self.base, events=())) as game:
            self.assertIsNone(game.ping(1, 1, signals=Signals(1000, True, 3, True, True)).event_id)
        raw = json.loads(Path("nuhuh/data/phrases.json").read_text(encoding="utf-8"))
        del raw["surprises"]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old_custom.json"
            path.write_text(json.dumps(raw))
            self.assertEqual(PhraseBook.load(path).surprises.large_text_chars, 350)

    def test_message_chance_is_reproducible_diverse_and_leaves_ordinary_replies(self):
        book = self.book("large_text", message_one_in=3)
        def play(guild):
            with Game(book) as game:
                return [game.ping(guild, 1, signals=Signals(characters=350)).event_id for _ in range(300)]
        sequence = play(1)
        self.assertEqual(sequence, play(1))
        self.assertNotEqual(sequence, play(2))
        self.assertGreater(sequence.count("large_text"), 60)
        self.assertLess(sequence.count("large_text"), 140)
        self.assertIn(None, sequence)

    def test_overlapping_cues_choose_one_reaction_without_fixed_starvation(self):
        book = self.book("large_text", "emoji", "repeated_mentions")
        with Game(book) as game:
            events = {game.ping(1, 1, signals=Signals(500, True, 3)).event_id for _ in range(60)}
        self.assertEqual(events, {"large_text", "emoji", "repeated_mentions"})

    def test_welcome_return_and_explicit_help_priority(self):
        book = self.book(*CONTEXT_EVENT_IDS, "help_extra", "large_text", "milestone")
        book = replace(book, surprises=replace(book.surprises, milestones=(2,)))
        with Game(book) as game:
            self.assertEqual(game.ping(1, 1, now=1000, signals=Signals(500)).event_id, "first_guild_ping")
            self.assertEqual(game.ping(1, 1, now=87401, signals=Signals(500)).event_id, "returning_user")
            self.assertEqual(game.ping(1, 2, now=87402, signals=Signals(500),
                                       response_event="help_extra").event_id, "help_extra")

    def test_callbacks_require_successful_setup_and_are_consumed_only_on_delivery(self):
        for setup, callback in MEMORY_EVENTS.items():
            signals = {"large_text": Signals(350), "emoji": Signals(emoji=True),
                       "repeated_mentions": Signals(mentions=2), "apology": Signals(apology=True)}[setup]
            with self.subTest(setup=setup), Game(self.book(setup, callback)) as game:
                unsent = game.ping(1, 1, signals=signals)
                self.assertEqual(unsent.event_id, setup)
                self.assertIsNone(game.ping(1, 1).event_id)
                delivered = game.ping(1, 1, signals=signals)
                game.delivered(delivered)
                recall = game.ping(1, 1)
                self.assertEqual((recall.event_id, recall.memory_origin_count), (callback, 3))
                retry = game.ping(1, 1)  # Failed/suppressed recall did not consume it.
                self.assertEqual(retry.event_id, callback)
                game.delivered(retry)
                game.delivered(retry)  # Duplicate acknowledgement cannot restore memory.
                self.assertIsNone(game.ping(1, 1).event_id)

    def test_callbacks_do_not_claim_a_habit_is_absent_while_it_is_present(self):
        with Game(self.book("large_text", "shorter_this_time", message_one_in=10**9)) as game:
            # Establish a real delivered setup using a deterministic always-on book.
            game.phrases = self.book("large_text", "shorter_this_time")
            game.delivered(game.ping(1, 1, signals=Signals(350)))
            game.phrases = self.book("large_text", "shorter_this_time", message_one_in=10**9)
            self.assertIsNone(game.ping(1, 1, signals=Signals(350)).event_id)
            self.assertEqual(game.ping(1, 1).event_id, "shorter_this_time")

    def test_memory_is_persistent_scoped_and_contains_only_tags_and_counts(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "game.sqlite3"
            book = self.book("apology", "broken_promise")
            with Game(book, database) as game:
                game.delivered(game.ping(1, 1, signals=message_signals("<@1> sorry", 1)))
            with closing(sqlite3.connect(database)) as db:
                self.assertEqual(db.execute("SELECT * FROM memories").fetchall(), [(1, 1, "apology", 1)])
            with Game(book, database) as game:
                self.assertEqual(game.help(1, 1).count, 1)
                self.assertIsNone(game.ping(2, 1).event_id)
                self.assertIsNone(game.ping(1, 2).event_id)
                self.assertEqual(game.ping(1, 1).event_id, "broken_promise")

    def test_late_acknowledgements_cannot_erase_or_restore_newer_memories(self):
        with Game(self.book("large_text", "shorter_this_time")) as game:
            game.delivered(game.ping(1, 1, signals=Signals(350)))
            old_callback = game.ping(1, 1)
            newer_setup = game.ping(1, 1, signals=Signals(500))
            game.delivered(newer_setup)
            game.delivered(old_callback)
            callback = game.ping(1, 1)
            self.assertEqual(callback.memory_origin_count, newer_setup.count)
            game.delivered(callback)
            game.delivered(newer_setup)
            self.assertIsNone(game.ping(1, 1).event_id)

    def test_replays_do_not_add_counts_or_new_memories(self):
        with Game(self.book("apology", "broken_promise")) as game:
            setup = game.ping(1, 1, message_id=10, signals=Signals(apology=True))
            game.delivered(setup)
            self.assertIsNone(game.ping(1, 1, message_id=10, signals=Signals(apology=True)))
            reply = game.ping(1, 1, message_id=11)
            self.assertEqual((reply.count, reply.event_id), (2, "broken_promise"))

    def test_group_incident_counts_distinct_other_pingers_not_repeat_spam(self):
        book = self.book("group_incident")
        with Game(book) as game:
            for _ in range(10):
                self.assertIsNone(game.ping(1, 2, now=1000).event_id)
            self.assertIsNone(game.ping(1, 1, now=1000).event_id)
            game.ping(1, 3, now=1000)
            game.ping(1, 4, now=1000)
            self.assertEqual(game.ping(1, 1, now=1060).event_id, "group_incident")
            self.assertIsNone(game.ping(1, 1, now=1061).event_id)
            self.assertIsNone(game.ping(2, 1, now=1000).event_id)
            self.assertIsNone(game.ping(1, 1, now=900).event_id)  # No future activity on clock rollback.

    def test_milestones_are_exact_and_suppressed_ones_are_not_queued(self):
        book = self.book("milestone", milestones=(3, 5), milestone_every=10)
        with Game(book) as game:
            replies = [game.ping(1, 1) for _ in range(21)]
        self.assertEqual([r.count for r in replies if r.event_id == "milestone"], [3, 5, 10, 20])
        self.assertIn("3", replies[2].text)
        self.assertIsNone(replies[3].event_id)

    def test_rare_admissions_unlock_late_and_still_use_the_seeded_gate(self):
        book = self.book("rare_admission", rare_one_in=1, rare_min_count=151)
        with Game(book) as game:
            replies = [game.ping(1, 1) for _ in range(151)]
        self.assertTrue(all(r.event_id is None for r in replies[:150]))
        self.assertEqual(replies[-1].event_id, "rare_admission")
        book = self.book("rare_admission", rare_one_in=80, rare_min_count=151)
        with Game(book) as game:
            events = [game.ping(1, 1).event_id for _ in range(2000)]
        self.assertGreater(events.count("rare_admission"), 5)
        self.assertLess(events.count("rare_admission"), 60)

    def test_surprise_settings_reject_typos_and_invalid_thresholds(self):
        original = json.loads(Path("nuhuh/data/phrases.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.json"
            for name, value in [("message_one_in", 0), ("large_text_chars", True),
                                ("callback_one_in", "12"), ("milestones", [3, 3]),
                                ("milestones", [True]), ("milestones", [5, 3]),
                                ("milestone_every", -1), ("typo", 1)]:
                with self.subTest(name=name, value=value):
                    raw = json.loads(json.dumps(original))
                    raw["surprises"][name] = value
                    path.write_text(json.dumps(raw))
                    with self.assertRaises(PhraseError):
                        PhraseBook.load(path)

    def test_previous_alpha_schema_is_rejected_without_modifying_it(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "old.sqlite3"
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("PRAGMA user_version = 4")
            with self.assertRaisesRegex(ValueError, "Unsupported alpha database schema 4"):
                Game(self.base, path)
            with closing(sqlite3.connect(path)) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 4)
            path.unlink()
