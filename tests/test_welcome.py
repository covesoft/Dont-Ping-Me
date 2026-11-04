# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Introduction routing and lifecycle with fake sends and a controlled delay."""

import asyncio
import importlib.util
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock

HAS_DISCORD = importlib.util.find_spec("discord") is not None
if HAS_DISCORD:
    import discord
    from cogs.welcome import Welcome, introduction_destination


def fake_channel(channel_id, name, *, can_send=True):
    channel = MagicMock(spec=discord.TextChannel)
    channel.id, channel.name = channel_id, name
    channel.permissions_for.return_value = SimpleNamespace(view_channel=True, send_messages=can_send)
    channel.send = AsyncMock()
    return channel


def fake_guild(guild_id=1):
    channel = fake_channel(guild_id * 10, "general")
    return SimpleNamespace(id=guild_id, me=object(), unavailable=False,
                           system_channel=channel, text_channels=[channel],
                           rules_channel=None, public_updates_channel=None)


@unittest.skipUnless(HAS_DISCORD, "Install requirements.txt for introduction adapter tests")
class DestinationTests(unittest.TestCase):
    def test_writable_system_channel_is_preferred(self):
        guild = fake_guild()
        guild.text_channels.insert(0, fake_channel(11, "bot-commands"))
        self.assertIs(introduction_destination(guild), guild.system_channel)

    def test_fallback_is_a_writable_bot_channel_and_excludes_rules_and_updates(self):
        guild = fake_guild()
        guild.system_channel.permissions_for.return_value.send_messages = False
        guild.rules_channel = fake_channel(11, "bots")
        guild.public_updates_channel = fake_channel(12, "bot-updates")
        chosen = fake_channel(16, "🤖-bot-commands")
        guild.text_channels += [guild.rules_channel, guild.public_updates_channel,
                                fake_channel(13, "robotics"), fake_channel(14, "general-chat"),
                                fake_channel(15, "bots", can_send=False), chosen]
        self.assertIs(introduction_destination(guild), chosen)

    def test_no_destination_is_guessed_and_missing_access_is_respected(self):
        guild = fake_guild()
        guild.system_channel = None
        self.assertIsNone(introduction_destination(guild))  # Writable general is not a fallback.
        guild.system_channel = guild.rules_channel = guild.text_channels[0]
        self.assertIsNone(introduction_destination(guild))
        guild.rules_channel = None
        guild.system_channel.permissions_for.return_value.view_channel = False
        self.assertIsNone(introduction_destination(guild))
        guild.me = None
        self.assertIsNone(introduction_destination(guild))


@unittest.skipUnless(HAS_DISCORD, "Install requirements.txt for introduction adapter tests")
class IntroductionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.guild = fake_guild()
        self.registry = {1: self.guild}
        self.bot = SimpleNamespace(user=SimpleNamespace(mention="<@99>"),
                                   get_guild=lambda guild_id: self.registry.get(guild_id))
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.delays = []

        async def pause(seconds):
            self.delays.append(seconds)
            self.entered.set()
            await self.release.wait()

        self.cog = Welcome(self.bot, enabled=True, delay=15, sleep=pause)
        self.addAsyncCleanup(self.cog.cog_unload)

    async def start_join(self):
        await self.cog.on_guild_join(self.guild)
        task = self.cog._pending[self.guild.id]
        await asyncio.wait_for(self.entered.wait(), 1)
        return task

    async def test_delay_one_send_per_join_and_mentions_are_suppressed(self):
        task = await self.start_join()
        self.assertEqual(self.delays, [15])
        self.guild.system_channel.send.assert_not_awaited()
        await self.cog.on_guild_join(self.guild)
        self.assertIs(self.cog._pending[1], task)
        self.release.set()
        await asyncio.wait_for(task, 1)
        await self.cog.on_guild_join(self.guild)
        self.guild.system_channel.send.assert_awaited_once()
        args, kwargs = self.guild.system_channel.send.await_args
        self.assertIn("<@99> help", args[0])
        self.assertIn("channel permissions", args[0])
        self.assertNotIn("Copyright", args[0])
        self.assertEqual(kwargs["allowed_mentions"].to_dict(), {"parse": []})
        self.assertNotIn("embed", kwargs)
        self.assertFalse(self.cog._pending)

    async def test_destination_and_permissions_are_resolved_after_the_delay(self):
        old = self.guild.system_channel
        task = await self.start_join()
        replacement = fake_channel(20, "new-system")
        self.guild.system_channel = replacement
        self.release.set()
        await asyncio.wait_for(task, 1)
        old.send.assert_not_awaited()
        replacement.send.assert_awaited_once()

    async def test_removal_cancels_pending_intro_and_a_real_rejoin_can_introduce_again(self):
        task = await self.start_join()
        await self.cog.on_guild_remove(self.guild)
        self.assertTrue(task.cancelled())
        self.guild.system_channel.send.assert_not_awaited()
        self.assertFalse(self.cog._pending)
        self.release.set()
        await self.cog.on_guild_join(self.guild)
        rejoined = self.cog._pending[1]
        await asyncio.wait_for(rejoined, 1)
        self.guild.system_channel.send.assert_awaited_once()

    async def test_missing_or_unavailable_guild_is_skipped(self):
        for state in ("removed", "unavailable", "no_bot_user"):
            with self.subTest(state=state):
                self.entered.clear()
                self.release.clear()
                self.registry[1] = self.guild
                self.guild.unavailable = False
                self.bot.user = SimpleNamespace(mention="<@99>")
                task = await self.start_join()
                if state == "removed":
                    self.registry.clear()
                elif state == "unavailable":
                    self.guild.unavailable = True
                else:
                    self.bot.user = None
                self.release.set()
                await asyncio.wait_for(task, 1)
                self.guild.system_channel.send.assert_not_awaited()
                await self.cog.on_guild_remove(self.guild)

    async def test_no_suitable_channel_skips_once_without_falling_back_to_general(self):
        self.guild.system_channel = None
        task = await self.start_join()
        self.release.set()
        with self.assertLogs("cogs.welcome", level="INFO"):
            await asyncio.wait_for(task, 1)
        self.guild.text_channels[0].send.assert_not_awaited()
        await self.cog.on_guild_join(self.guild)
        self.assertFalse(self.cog._pending)

    async def test_send_failure_is_logged_and_not_retried_by_duplicate_join(self):
        self.guild.system_channel.send.side_effect = RuntimeError("simulated transport failure")
        task = await self.start_join()
        self.release.set()
        with self.assertLogs("cogs.welcome", level="WARNING"):
            await asyncio.wait_for(task, 1)
        await self.cog.on_guild_join(self.guild)
        self.guild.system_channel.send.assert_awaited_once()
        self.assertFalse(self.cog._pending)

    async def test_send_timeout_finishes_the_task(self):
        async def hang(*args, **kwargs):
            await asyncio.Event().wait()
        self.cog.send_timeout = 0.01
        self.guild.system_channel.send.side_effect = hang
        task = await self.start_join()
        self.release.set()
        with self.assertLogs("cogs.welcome", level="WARNING"):
            await asyncio.wait_for(task, 1)
        self.assertFalse(self.cog._pending)

    async def test_unload_cancels_all_pending_tasks_and_prevents_new_work(self):
        first = await self.start_join()
        other = fake_guild(2)
        self.registry[2] = other
        await self.cog.on_guild_join(other)
        second = self.cog._pending[2]
        await self.cog.cog_unload()
        self.assertTrue(first.cancelled())
        self.assertTrue(second.cancelled())
        self.guild.system_channel.send.assert_not_awaited()
        other.system_channel.send.assert_not_awaited()
        await self.cog.on_guild_join(self.guild)
        self.assertFalse(self.cog._pending)

    async def test_introductions_can_be_disabled(self):
        self.cog.enabled = False
        await self.cog.on_guild_join(self.guild)
        self.assertFalse(self.cog._pending)
