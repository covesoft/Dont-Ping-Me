from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from nuhuh.engine import Game
from nuhuh.phrases import DEFAULT_PHRASES, MAX_COUNT, PhraseBook, PhraseError


ROOT = Path(__file__).resolve().parents[1]


class GameTests(unittest.TestCase):
    def setUp(self):
        # These legacy tests deliberately isolate ordinary count-tier behavior.
        self.book = PhraseBook(PhraseBook.load().tiers)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "game.sqlite3"

    def test_relationships_and_counts_survive_restart(self):
        with Game(self.book, self.database) as game:
            self.assertEqual(game.ping(1, 1).count, 1)
            self.assertEqual(game.ping(1, 1).count, 2)
            self.assertEqual(game.ping(2, 1).count, 1)
            self.assertEqual(game.ping(1, 2).count, 1)
        with Game(self.book, self.database) as game:
            self.assertEqual(game.ping(1, 1).count, 3)

    def test_tier_boundaries_and_evergreen_endpoint(self):
        with Game(self.book) as game:
            replies = [game.ping(1, 1) for _ in range(30)]
        self.assertEqual([r.tier_id for r in replies[:4]], ["objection"] * 3 + ["negotiation"])
        self.assertEqual(replies[8].tier_id, "negotiation")
        self.assertTrue(all(r.tier_id == "familiarity" for r in replies[9:]))

    def test_successful_delivery_prevents_repetition_even_after_restart(self):
        last = None
        for _ in range(25):
            with Game(self.book, self.database) as game:
                reply = game.ping(1, 1)
                self.assertNotEqual(reply.phrase_id, last)
                game.delivered(reply)
                last = reply.phrase_id

    def test_unsent_reply_preserves_count_without_marking_delivery(self):
        with Game(self.book, self.database) as game:
            first = game.ping(1, 1)
            game.delivered(first)
            game.ping(1, 1)  # Simulate a send failure: no acknowledgement.
        with sqlite3.connect(self.database) as db:
            row = db.execute("SELECT count, last_phrase_id, last_reply_count FROM relationships").fetchone()
        self.assertEqual(row, (2, first.phrase_id, 1))

    def test_late_acknowledgement_cannot_overwrite_newer_delivery(self):
        with Game(self.book, self.database) as game:
            first = game.ping(1, 1)
            second = game.ping(1, 1)
            game.delivered(second)
            game.delivered(first)
        with sqlite3.connect(self.database) as db:
            row = db.execute("SELECT last_phrase_id, last_reply_count FROM relationships").fetchone()
        self.assertEqual(row, (second.phrase_id, 2))

    def test_same_history_produces_same_sequence(self):
        def play():
            with Game(self.book) as game:
                replies = []
                for _ in range(40):
                    reply = game.ping(987, 654)
                    replies.append(reply.phrase_id)
                    game.delivered(reply)
                return replies
        self.assertEqual(play(), play())

    def test_guild_user_and_count_affect_the_sequence(self):
        def sequence(guild, user):
            with Game(self.book) as game:
                return [game.ping(guild, user).phrase_id for _ in range(25)]
        self.assertNotEqual(sequence(1, 1), sequence(2, 1))
        self.assertNotEqual(sequence(1, 1), sequence(1, 2))
        # Small pools can legitimately repeat a few draws. Exercise a fixed,
        # longer range within one tier instead of assuming three unique draws.
        self.assertGreater(len({self.book.select(1, 1, n, None)[1].id for n in range(10, 50)}), 1)

    def test_concurrent_connections_do_not_lose_increments(self):
        def worker(_):
            with Game(self.book, self.database) as game:
                return [game.ping(1, 1).count for _ in range(20)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            observed = [count for batch in pool.map(worker, range(4)) for count in batch]
        self.assertEqual(sorted(observed), list(range(1, 81)))

    def test_invalid_ids_do_not_create_relationships(self):
        with Game(self.book, self.database) as game:
            for bad in (0, -1, True, "1", MAX_COUNT + 1):
                with self.subTest(bad=bad), self.assertRaises(ValueError):
                    game.ping(bad, 1)
            self.assertEqual(game.ping(1, 1).count, 1)


class PhraseTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(DEFAULT_PHRASES.read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "phrases.json"

    def load(self, raw):
        self.path.write_text(json.dumps(raw), encoding="utf-8")
        return PhraseBook.load(self.path)

    def test_invalid_content_reports_actionable_errors(self):
        changes = [
            (lambda r: r.update(schema_version=True), "schema_version"),
            (lambda r: r.update(tiers=[]), "nonempty"),
            (lambda r: r["tiers"][0].update(min_count=2), "start at 1"),
            (lambda r: r["tiers"][1].update(min_count=1), "increase"),
            (lambda r: r["tiers"][0].update(min_count=True), "positive integer"),
            (lambda r: r["tiers"][0].update(phrases=[]), "nonempty"),
            (lambda r: r["tiers"][1].update(id="objection"), "Duplicate tier"),
            (lambda r: r["tiers"][0].update(typo=1), "unknown fields"),
            (lambda r: r["tiers"][0]["phrases"][1].update(id="objection.sign"), "Duplicate phrase"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text=" "), "nonempty"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text="{count.__class__}"), "placeholder"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text="{count:999999}"), "placeholder"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text="unclosed {"), "braces"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text="😀" * 1001), "2,000"),
            (lambda r: r["tiers"][0]["phrases"][0].update(text="x" * 1990 + "{count}"), "2,000"),
        ]
        for mutate, message in changes:
            with self.subTest(message=message):
                raw = copy.deepcopy(self.raw)
                mutate(raw)
                with self.assertRaisesRegex(PhraseError, message):
                    self.load(raw)

    def test_duplicate_json_keys_are_rejected(self):
        self.path.write_text('{"schema_version": 1, "schema_version": 2, "tiers": []}')
        with self.assertRaisesRegex(PhraseError, "Duplicate JSON key"):
            PhraseBook.load(self.path)

    def test_single_phrase_pool_removed_id_and_escaped_braces(self):
        raw = {"schema_version": 1, "tiers": [{"id": "only", "min_count": 1, "phrases": [
            {"id": "only.one", "text": "{{sigh}} Number {count}."}
        ]}]}
        book = self.load(raw)
        with Game(book) as game:
            for n in range(1, 4):
                reply = game.ping(1, 1)
                self.assertEqual(reply.text, f"{{sigh}} Number {n}.")
                game.delivered(reply)
        self.assertEqual(book.select(1, 1, 1, "deleted.phrase")[1].id, "only.one")


class CLITests(unittest.TestCase):
    def run_cli(self, *args, input=None, env=None):
        return subprocess.run(
            [sys.executable, "-m", "nuhuh", *args], cwd=ROOT,
            text=True, encoding="utf-8", capture_output=True, input=input,
            timeout=15, env={**(env if env is not None else os.environ), "PYTHONIOENCODING": "utf-8"},
        )

    def test_batch_persistence_and_cross_process_reproducibility(self):
        with tempfile.TemporaryDirectory() as folder:
            database = str(Path(folder) / "demo.sqlite3")
            first = self.run_cli("--db", database, "--pings", "2", "--debug")
            second = self.run_cli("--db", database, "--pings", "1", "--debug")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("[3 / objection]", second.stdout)
        a = self.run_cli("--db", ":memory:", "--pings", "30", env={**os.environ, "PYTHONHASHSEED": "1"})
        b = self.run_cli("--db", ":memory:", "--pings", "30", env={**os.environ, "PYTHONHASHSEED": "2"})
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(b.returncode, 0, b.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_interactive_enter_quit_and_eof(self):
        result = self.run_cli("--db", ":memory:", "--debug", input="\n\n/quit\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[2 / objection]", result.stdout)
        eof = self.run_cli("--db", ":memory:", input="")
        self.assertEqual(eof.returncode, 0, eof.stderr)

    def test_invalid_options_and_missing_phrases_fail_cleanly(self):
        for options in (("--guild-id", "0"), ("--pings", "0"), ("--phrases", "missing.json")):
            with self.subTest(options=options):
                result = self.run_cli(*options, "--pings", "1") if "--pings" not in options else self.run_cli(*options)
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_context_demo_and_wait_command_need_no_real_waiting(self):
        demo = self.run_cli("--demo")
        self.assertEqual(demo.returncode, 0, demo.stderr)
        for event in ("first_guild_ping", "recent_ping", "returning_user", "first_user_ping", "new_user_in_crowd"):
            self.assertIn("[" + event + "]", demo.stdout)
        interactive = self.run_cli("--db", ":memory:", "--debug", input="\n/wait 86401\n\n/quit\n")
        self.assertEqual(interactive.returncode, 0, interactive.stderr)
        self.assertIn("[returning_user]", interactive.stdout)
        tiers = self.run_cli("--db", ":memory:", "--pings", "15", "--step-seconds", "180", "--debug")
        self.assertEqual(tiers.returncode, 0, tiers.stderr)
        self.assertIn("[15 / familiarity]", tiers.stdout)


if __name__ == "__main__":
    unittest.main()
