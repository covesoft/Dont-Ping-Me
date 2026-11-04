# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

from pathlib import Path
import tempfile
import unittest

from nuhuh.engine import Game
from nuhuh.phrases import PhraseBook, MAX_COUNT
from nuhuh.statistics import Distribution, UsageStatistics


class StatisticsTests(unittest.TestCase):
    def test_empty_and_single_sample(self):
        empty = Distribution.of([])
        self.assertEqual(empty.samples, 0)
        self.assertIsNone(empty.maximum)
        self.assertIsNone(empty.p95)
        self.assertIsNone(empty.mode)
        single = Distribution.of([3])
        self.assertEqual((single.maximum, single.p95, single.average, single.median, single.mode),
                         (3, 3, 3, 3, 3))

    def test_known_distribution_and_tied_modes(self):
        result = Distribution.of([9, 1, 2, 2, 6])
        self.assertEqual((result.samples, result.maximum, result.p95, result.median, result.mode),
                         (5, 9, 9, 2, 2))
        self.assertEqual(result.average, 4)
        self.assertIsNone(Distribution.of([1, 1, 2, 2]).mode)
        self.assertIsNone(Distribution.of([1, 2, 3]).mode)

    def test_p95_nearest_rank_boundary(self):
        self.assertEqual(Distribution.of(range(1, 21)).p95, 19)
        self.assertEqual(Distribution.of(range(1, 22)).p95, 20)
        self.assertEqual(Distribution.of(range(1, 101)).p95, 95)

    def test_totals_can_exceed_sqlite_integer_range(self):
        result = UsageStatistics.from_rows([(1, MAX_COUNT), (1, MAX_COUNT), (2, 1)])
        self.assertEqual(result.total_pesters, 2 * MAX_COUNT + 1)
        self.assertEqual(result.per_guild.maximum, 2 * MAX_COUNT)
        self.assertEqual((result.per_guild.samples, result.per_relationship.samples), (2, 3))

    def test_database_snapshot_is_read_only_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / 'usage.sqlite3'
            book = PhraseBook.load()
            with Game(book, database) as game:
                self.assertEqual(game.statistics().total_pesters, 0)
                game.help(3, 999, now=1000, message_id=99)
                for guild, user, count in ((1, 10, 2), (1, 20, 1), (2, 10, 4)):
                    for _ in range(count):
                        game.ping(guild, user, now=1000)
                before = tuple(game._db.iterdump())
                result = game.statistics()
                self.assertEqual(tuple(game._db.iterdump()), before)
                self.assertEqual(result.total_pesters, 7)
                self.assertEqual((result.per_guild.samples, result.per_relationship.samples), (2, 3))
                self.assertEqual((result.per_guild.maximum, result.per_guild.average), (4, 3.5))
                self.assertEqual((result.per_relationship.maximum, result.per_relationship.median), (4, 2))
            with Game(book, database) as game:
                self.assertEqual(game.statistics(), result)
