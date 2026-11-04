from contextlib import closing
from dataclasses import replace
import asyncio
from pathlib import Path
import sqlite3
import tempfile
import unittest

from nuhuh.async_game import AsyncGame
from nuhuh.phrases import PhraseBook
from nuhuh.responder import Responder
from nuhuh.signals import Signals


class ResponderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "game.sqlite3"
        book = PhraseBook.load()
        book = PhraseBook(book.tiers, book.events, replace(book.rules, recent_one_in=1))
        self.game = await AsyncGame.open(book, self.database)
        self.addAsyncCleanup(self.game.close)
        self.now = 1000
        self.responder = Responder(self.game, clock=lambda: self.now)
        self.addAsyncCleanup(self.responder.close)
        self.sent = []

    async def send(self, text):
        self.sent.append(text)

    async def handle(self, user=1, channel=10, message=1, can_send=True, send=None):
        return await self.responder.handle(1, user, channel, message, can_send=can_send, send=send or self.send)

    def stored(self):
        with closing(sqlite3.connect(self.database)) as db, db:
            return db.execute("SELECT user_id, count, last_reply_count FROM relationships ORDER BY user_id").fetchall()

    async def test_suppressed_mentions_count_and_do_not_queue_or_deliver(self):
        self.assertEqual((await self.handle()).status, "sent")
        self.now += 1
        self.assertEqual((await self.handle(message=2)).status, "suppressed")
        self.assertEqual(self.stored(), [(1, 2, 1)])
        self.assertEqual(len(self.sent), 1)
        self.now += 4
        result = await self.handle(message=3)
        self.assertEqual((result.status, result.reply.count, result.reply.event_id), ("sent", 3, "recent_ping"))

    async def test_channel_limit_applies_across_users(self):
        await self.handle()
        self.now += 1
        self.assertEqual((await self.handle(user=2, message=2)).status, "suppressed")
        self.now += 1
        self.assertEqual((await self.handle(user=2, message=3)).status, "sent")

    async def test_no_permission_counts_and_duplicate_does_not_count(self):
        self.assertEqual((await self.handle(can_send=False)).status, "no_permission")
        self.assertEqual((await self.handle()).status, "duplicate")
        self.assertEqual(self.stored(), [(1, 1, 0)])
        self.assertFalse(self.sent)

    async def test_failed_send_retains_count_and_attempt_cooldown(self):
        async def fail(_):
            raise RuntimeError("simulated transport failure")
        with self.assertLogs("nuhuh.responder", level="WARNING"):
            self.assertEqual((await self.handle(send=fail)).status, "send_failed")
        self.assertEqual(self.stored(), [(1, 1, 0)])
        self.now += 1
        self.assertEqual((await self.handle(message=2)).status, "suppressed")

    async def test_inflight_send_suppresses_same_user_and_channel_without_queue(self):
        entered, release = asyncio.Event(), asyncio.Event()

        async def slow(text):
            entered.set()
            await release.wait()
            self.sent.append(text)

        first = asyncio.create_task(self.handle(send=slow))
        await asyncio.wait_for(entered.wait(), 2)
        try:
            self.now += 10  # Cooldown has elapsed, but the previous send remains in flight.
            results = await asyncio.gather(
                self.handle(user=2, channel=10, message=2),
                self.handle(user=1, channel=11, message=3),
            )
            self.assertEqual([r.status for r in results], ["suppressed", "suppressed"])
            self.assertEqual((await self.handle(user=3, channel=12, message=4)).status, "sent")
        finally:
            release.set()
            await first
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.stored(), [(1, 2, 1), (2, 1, 0), (3, 1, 1)])

    async def test_send_timeout_and_close_drain_pending_work(self):
        self.responder.send_timeout = 0.02
        started = asyncio.Event()

        async def hang(_):
            started.set()
            await asyncio.Event().wait()

        with self.assertLogs("nuhuh.responder", level="WARNING"):
            pending = asyncio.create_task(self.handle(send=hang))
            await started.wait()
            await self.responder.close()
            self.assertEqual((await pending).status, "send_failed")
        self.assertEqual((await self.handle(message=2)).status, "closing")
        self.assertEqual(self.stored(), [(1, 1, 0)])

    async def test_help_does_not_count_and_shares_pacing_with_game_replies(self):
        sent_help = []

        async def help_send(info):
            sent_help.append(info.count)

        outcome = await self.responder.handle_help(1, 1, 10, 1, can_send=True, send=help_send)
        self.assertEqual(outcome.status, "sent")
        self.assertEqual(sent_help, [0])
        self.assertEqual(self.stored(), [])
        self.now += 1
        self.assertEqual((await self.handle(message=2)).status, "suppressed")
        self.assertEqual(self.stored(), [(1, 1, 0)])
        self.now += 4
        outcome = await self.responder.handle_help(1, 1, 10, 3, can_send=True, send=help_send)
        self.assertEqual(outcome.status, "sent")
        self.assertEqual(sent_help, [0, 1])
        self.assertEqual(self.stored(), [(1, 1, 0)])

    async def test_inflight_help_suppresses_other_sends_without_creating_a_participant(self):
        started, release = asyncio.Event(), asyncio.Event()

        async def slow_help(info):
            started.set()
            await release.wait()

        task = asyncio.create_task(self.responder.handle_help(1, 1, 10, 1, can_send=True, send=slow_help))
        await asyncio.wait_for(started.wait(), 2)
        try:
            self.now += 10
            outcome = await self.handle(user=2, message=2)
            self.assertEqual(outcome.status, "suppressed")
            self.assertEqual(self.stored(), [(2, 1, 0)])
        finally:
            release.set()
            await task


class MemoryResponderTests(unittest.IsolatedAsyncioTestCase):
    async def test_suppressed_setups_do_not_create_callbacks_and_failed_callbacks_remain(self):
        base = PhraseBook.load()
        book = replace(base, events=tuple(p for p in base.events if p.id in ("large_text", "shorter_this_time")),
                       surprises=replace(base.surprises, message_one_in=1, callback_one_in=1))
        game = await AsyncGame.open(book, ":memory:")
        self.addAsyncCleanup(game.close)
        now = [1000]
        responder = Responder(game, clock=lambda: now[0])
        self.addAsyncCleanup(responder.close)
        sent = []

        async def send(text):
            sent.append(text)

        async def handle(message, signals=Signals(), callback=send, can_send=True):
            return await responder.handle(1, 1, 10, message, can_send=can_send, send=callback, signals=signals)

        await handle(1)
        now[0] = 1001
        suppressed = await handle(2, Signals(350))
        self.assertEqual((suppressed.status, suppressed.reply.event_id), ("suppressed", "large_text"))
        now[0] = 1005
        self.assertIsNone((await handle(3)).reply.event_id)
        now[0] = 1010
        denied = await handle(4, Signals(350), can_send=False)
        self.assertEqual(denied.status, "no_permission")
        self.assertIsNone((await handle(5)).reply.event_id)
        now[0] = 1015
        self.assertEqual((await handle(6, Signals(350))).status, "sent")

        async def fail(text):
            raise RuntimeError("simulated failure")

        now[0] = 1020
        with self.assertLogs("nuhuh.responder", level="WARNING"):
            failed = await handle(7, callback=fail)
        self.assertEqual((failed.status, failed.reply.event_id), ("send_failed", "shorter_this_time"))
        now[0] = 1025
        self.assertEqual((await handle(8)).reply.event_id, "shorter_this_time")
        now[0] = 1030
        self.assertIsNone((await handle(9)).reply.event_id)
