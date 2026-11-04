# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

from dataclasses import replace
import copy
import json
from pathlib import Path
import tempfile
import unittest

from nuhuh.engine import Game, HISTORY_LIMIT
from nuhuh.phrases import Context, DEFAULT_PHRASES, PhraseBook


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.book = PhraseBook.load()

    def test_rapid_play_exposes_every_tier_and_context_replies(self):
        ordinary_tiers = set()
        event_count = 0
        with Game(self.book) as game:
            for count in range(1, 301):
                reply = game.ping(1, 1, now=1000 + count * 5)
                game.delivered(reply)
                if reply.event_id == "recent_ping":
                    event_count += 1
                elif reply.event_id is None:
                    ordinary_tiers.add(reply.tier_id)
        self.assertEqual(ordinary_tiers, {tier.id for tier in self.book.tiers})
        self.assertGreater(event_count, 60)
        self.assertLess(event_count, 140)

    def test_mixing_is_deterministic_and_specific_to_the_relationship(self):
        context = Context(False, False, 5, 10)
        def events(guild, user):
            return [self.book.event_for(context, guild, user, n) for n in range(2, 100)]
        self.assertEqual(events(1, 1), events(1, 1))
        self.assertNotEqual(events(1, 1), events(2, 1))
        self.assertNotEqual(events(1, 1), events(1, 2))
        self.assertEqual(set(events(1, 1)), {None, "recent_ping"})

    def test_important_events_are_not_subject_to_recent_chance(self):
        cases = [
            (Context(True, True, 0, None), "first_guild_ping"),
            (Context(False, True, 5, None), "new_user_in_crowd"),
            (Context(False, True, 1, None), "first_user_ping"),
            (Context(False, False, 0, 86401), "returning_user"),
        ]
        for context, expected in cases:
            for user in range(1, 25):
                with self.subTest(event=expected, user=user):
                    self.assertEqual(self.book.event_for(context, 1, user, 25), expected)

    def test_recent_one_in_one_and_disabled_pool_have_explicit_behavior(self):
        book = PhraseBook(self.book.tiers, self.book.events, replace(self.book.rules, recent_one_in=1))
        context = Context(False, False, 0, 120)
        self.assertTrue(all(book.event_for(context, 1, 1, n) == "recent_ping" for n in range(1, 30)))
        disabled = PhraseBook(book.tiers, tuple(pool for pool in book.events if pool.id != "recent_ping"), book.rules)
        self.assertIsNone(disabled.event_for(context, 1, 1, 10))
        self.assertIsNone(book.event_for(Context(False, False, 0, 121), 1, 1, 10))

    def assert_copy_quality(self, book):
        pools = [pool.phrases for pool in (*book.tiers, *book.events)]
        phrases = [phrase for pool in pools for phrase in pool]
        self.assertEqual(len({phrase.id for phrase in phrases}), len(phrases))
        self.assertEqual(len({phrase.text for phrase in phrases}), len(phrases))
        # The supplied copy should offer alternatives beyond the delivered
        # history window. This is an editorial check, not a custom-file limit.
        for pool in (*book.tiers, *book.events):
            with self.subTest(pool=pool.id):
                self.assertGreater(len(pool.phrases), HISTORY_LIMIT)

    def test_shipping_copy_has_unique_ids_text_and_adequate_pool_sizes(self):
        self.assert_copy_quality(self.book)

    def test_copy_quality_allows_additions_removals_and_rewrites(self):
        original = json.loads(DEFAULT_PHRASES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "edited.json"
            for change in ("add", "remove", "rewrite"):
                with self.subTest(change=change):
                    raw = copy.deepcopy(original)
                    pool = raw["tiers"][0]["phrases"]
                    if change == "add":
                        pool.append({"id": "test.extra_copy", "text": "A new objection for the test edition."})
                    elif change == "remove":
                        pool.pop()
                    else:
                        pool[0]["text"] = "The opening objection has been revised for this test."
                    path.write_text(json.dumps(raw), encoding="utf-8")
                    self.assert_copy_quality(PhraseBook.load(path))

    def test_recent_history_avoids_near_repeats_across_restarts(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.sqlite3"
            recent = []
            for count in range(1, 35):
                with Game(self.book, path) as game:
                    reply = game.ping(1, 2, now=1000 + count * 5)
                    self.assertNotIn(reply.phrase_id, recent[-5:])
                    game.delivered(reply)
                    recent.append(reply.phrase_id)

    def test_two_phrase_pool_relaxes_oldest_history_without_getting_stuck(self):
        tier = replace(self.book.tiers[0], phrases=self.book.tiers[0].phrases[:2])
        with Game(PhraseBook((tier,))) as game:
            last = None
            for _ in range(15):
                reply = game.ping(1, 1)
                self.assertNotEqual(reply.phrase_id, last)
                game.delivered(reply)
                last = reply.phrase_id
