# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

import asyncio
from pathlib import Path
import tempfile
import threading
import unittest

from nuhuh.async_game import AsyncGame
from nuhuh.phrases import PhraseBook


class LifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_close_still_closes_a_connection_queued_behind_work(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "game.sqlite3"
            game = await AsyncGame.open(PhraseBook.load(), path)
            started, release = threading.Event(), threading.Event()

            def busy():
                started.set()
                if not release.wait(3):
                    raise TimeoutError("Test did not release the database worker")

            worker = asyncio.get_running_loop().run_in_executor(game._executor, busy)
            try:
                self.assertTrue(await asyncio.to_thread(started.wait, 2))
                closing = asyncio.create_task(game.close())
                await asyncio.sleep(0)  # Let close reserve its shared cleanup task.
                closing.cancel()
                release.set()
                with self.assertRaises(asyncio.CancelledError):
                    await closing
                await worker
                await game.close()
                self.assertTrue(game._close_task.done())
                path.unlink()  # Also proves file release on Windows.
            finally:
                release.set()
                await game.close()

    async def test_multiple_close_callers_wait_for_one_complete_shutdown(self):
        game = await AsyncGame.open(PhraseBook.load(), ":memory:")
        await game.ping(1, 1)
        await asyncio.gather(game.close(), game.close(), game.close())
        self.assertTrue(game._close_task.done())
        with self.assertRaisesRegex(RuntimeError, "closing"):
            await game.ping(1, 1)
