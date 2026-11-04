"""Keep SQLite work on one dedicated thread, away from Discord's event loop."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from .engine import Game


class AsyncGame:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="nuhuh-db")
        self._game = None
        self._closing = False
        self._close_task = None

    @classmethod
    async def open(cls, phrases, database):
        self = cls()
        loop = asyncio.get_running_loop()

        def create():
            self._game = Game(phrases, database)

        try:
            await loop.run_in_executor(self._executor, create)
        except BaseException:
            # A cancelled await can leave its worker running. Cleanup is queued
            # on that same thread after creation, preserving SQLite ownership.
            def cleanup():
                if self._game is not None:
                    self._game.close()
            try:
                await loop.run_in_executor(self._executor, cleanup)
            finally:
                self._executor.shutdown(wait=True)
            raise
        return self

    async def _call(self, method, *args, **kwargs):
        if self._closing:
            raise RuntimeError("Game database is closing")
        return await asyncio.get_running_loop().run_in_executor(
            self._executor, partial(getattr(self._game, method), *args, **kwargs)
        )

    async def ping(self, *args, **kwargs):
        return await self._call("ping", *args, **kwargs)

    async def claim_response(self, *args, **kwargs):
        return await self._call("claim_response", *args, **kwargs)

    async def delivered(self, reply):
        await self._call("delivered", reply)

    async def close(self):
        if self._close_task is None:
            self._closing = True
            self._close_task = asyncio.create_task(self._finish_close())
        try:
            await asyncio.shield(self._close_task)
        except asyncio.CancelledError:
            # Finish closing even if the caller is cancelled. A second caller
            # awaits the same operation instead of returning before it finishes.
            await asyncio.shield(self._close_task)
            raise

    async def _finish_close(self):
        pending = asyncio.get_running_loop().run_in_executor(self._executor, self._game.close)
        try:
            await asyncio.shield(pending)
        except asyncio.CancelledError:
            await asyncio.shield(pending)
            raise
        finally:
            self._executor.shutdown(wait=True)
