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
        if self._closing:
            return
        self._closing = True
        try:
            await asyncio.get_running_loop().run_in_executor(self._executor, self._game.close)
        finally:
            self._executor.shutdown(wait=True)
