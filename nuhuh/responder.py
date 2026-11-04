# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Count every observed mention while bounding response attempts and in-flight sends."""

import asyncio
from dataclasses import dataclass
import logging
import time

from .engine import HelpInfo, Reply, timestamp
from .signals import Signals

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Outcome:
    status: str
    reply: Reply | HelpInfo | None = None


class Responder:
    def __init__(self, game, *, user_cooldown=5, channel_cooldown=2, send_timeout=15, clock=time.time):
        for value in (user_cooldown, channel_cooldown, send_timeout):
            timestamp(value)
        if send_timeout == 0:
            raise ValueError("send_timeout must be positive")
        self.game = game
        self.user_cooldown = user_cooldown
        self.channel_cooldown = channel_cooldown
        self.send_timeout = send_timeout
        self.clock = clock
        self._users = set()
        self._channels = set()
        self._tasks = set()
        self._closing = False

    async def handle(self, guild_id, user_id, channel_id, message_id, *, can_send, send, response_event=None,
                     signals=Signals()):
        return await self._handle(guild_id, user_id, channel_id, message_id,
                                  can_send=can_send, send=send, response_event=response_event, signals=signals)

    async def handle_help(self, guild_id, user_id, channel_id, message_id, *, can_send, send):
        return await self._handle(guild_id, user_id, channel_id, message_id,
                                  can_send=can_send, send=send, is_help=True)

    async def _handle(self, guild_id, user_id, channel_id, message_id, *, can_send, send,
                      is_help=False, response_event=None, signals=Signals()):
        if self._closing:
            return Outcome("closing")
        task = asyncio.current_task()
        self._tasks.add(task)
        try:
            if is_help:
                reply = await self.game.help(guild_id, user_id, now=self.clock(), message_id=message_id)
            else:
                reply = await self.game.ping(guild_id, user_id, now=self.clock(), message_id=message_id,
                                             response_event=response_event, signals=signals)
            if reply is None:
                return Outcome("duplicate")
            if not can_send:
                return Outcome("no_permission", reply)
            user_key = (guild_id, user_id)
            channel_key = (guild_id, channel_id)
            if user_key in self._users or channel_key in self._channels:
                return Outcome("suppressed", reply)
            # Reserve before any await so other callbacks cannot race into a send.
            self._users.add(user_key)
            self._channels.add(channel_key)
            try:
                claimed = await self.game.claim_response(
                    reply, channel_id, now=self.clock(), user_cooldown=self.user_cooldown,
                    channel_cooldown=self.channel_cooldown,
                )
                if not claimed:
                    return Outcome("suppressed", reply)
                try:
                    async with asyncio.timeout(self.send_timeout):
                        await send(reply if isinstance(reply, HelpInfo) else reply.text)
                except Exception:
                    log.warning("Reply attempt failed in guild %s, channel %s", guild_id, channel_id, exc_info=True)
                    return Outcome("send_failed", reply)
                if isinstance(reply, Reply):
                    await self.game.delivered(reply)
                return Outcome("sent", reply)
            finally:
                self._users.discard(user_key)
                self._channels.discard(channel_key)
        finally:
            self._tasks.discard(task)

    async def close(self):
        self._closing = True
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
