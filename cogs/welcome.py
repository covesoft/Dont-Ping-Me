# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""One quiet introduction after an actual guild join; no startup broadcasts."""

import asyncio
import logging
import re

import discord
from discord.ext import commands

from config import INTRODUCTIONS_ENABLED, INTRO_DELAY_SECONDS, SEND_TIMEOUT_SECONDS
from cogs.channels import can_send_message, channel_permissions
from nuhuh.engine import timestamp


log = logging.getLogger(__name__)
BOT_CHANNEL_NAME = re.compile(r"(?<![a-z0-9])bots?(?![a-z0-9])")


def introduction_destination(guild):
    """Prefer the system channel, then a named bot channel in guild order."""
    me = guild.me
    if me is None:
        return None
    excluded = {channel.id for channel in (guild.rules_channel, guild.public_updates_channel) if channel is not None}

    def eligible(channel):
        return (isinstance(channel, discord.TextChannel) and channel.id not in excluded
                and can_send_message(channel, channel_permissions(channel, me)))

    if eligible(guild.system_channel):
        return guild.system_channel
    return next((channel for channel in guild.text_channels
                 if BOT_CHANNEL_NAME.search(channel.name.casefold()) and eligible(channel)), None)


def introduction_text(mention):
    return (
        "I've been installed. I wasn't consulted.\n\n"
        "I'm **Just Don't**, a small game about ignoring one very simple request. "
        "Mention me, I object; keep going, and I remember.\n\n"
        f"For instructions, send {mention} help. Server managers can choose where "
        "I respond through channel permissions.\n\n"
        "I'll be over here, hoping that was clear."
    )


class Welcome(commands.Cog):
    def __init__(self, bot, *, enabled=INTRODUCTIONS_ENABLED, delay=INTRO_DELAY_SECONDS,
                 send_timeout=SEND_TIMEOUT_SECONDS, sleep=asyncio.sleep):
        timestamp(delay)
        timestamp(send_timeout)
        if send_timeout == 0:
            raise ValueError("send_timeout must be positive")
        self.bot = bot
        self.enabled = enabled
        self.delay = delay
        self.send_timeout = send_timeout
        self._sleep = sleep
        self._pending = {}
        self._joined = set()
        self._closing = False

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        if not self.enabled or self._closing or guild.id in self._joined:
            return
        self._joined.add(guild.id)
        self._pending[guild.id] = asyncio.create_task(self._introduce(guild.id))

    async def _introduce(self, guild_id):
        try:
            await self._sleep(self.delay)
            guild = self.bot.get_guild(guild_id)
            if self._closing or guild is None or guild.unavailable or self.bot.user is None:
                return
            channel = introduction_destination(guild)
            if channel is None:
                log.info("No suitable introduction channel in guild %s; skipping", guild_id)
                return
            async with asyncio.timeout(self.send_timeout):
                await channel.send(introduction_text(self.bot.user.mention), allowed_mentions=discord.AllowedMentions.none())
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("Introduction failed in guild %s", guild_id, exc_info=True)
        finally:
            if self._pending.get(guild_id) is asyncio.current_task():
                self._pending.pop(guild_id, None)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        self._joined.discard(guild.id)
        task = self._pending.pop(guild.id, None)
        if task is not None:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    async def cog_unload(self):
        self._closing = True
        tasks = tuple(self._pending.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._pending.clear()
        self._joined.clear()


async def setup(bot):
    await bot.add_cog(Welcome(bot))
