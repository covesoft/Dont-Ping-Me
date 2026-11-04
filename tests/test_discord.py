# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Adapter tests use real discord.py types and fake sends; they never log in."""

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

HAS_DISCORD = importlib.util.find_spec("discord") is not None
if HAS_DISCORD:
    import discord
    import discordbot as bot_module
    from cogs.pings import Pings


@unittest.skipUnless(HAS_DISCORD, "Install requirements.txt to run Discord adapter tests")
class DiscordTests(unittest.IsolatedAsyncioTestCase):
    def fake_message(self):
        channel = MagicMock(spec=discord.TextChannel)
        channel.id = 10
        channel.permissions_for.return_value = SimpleNamespace(view_channel=True, send_messages=True,
                                                               send_messages_in_threads=True, embed_links=True)
        channel.send = AsyncMock()

        class Message:
            text = "<@99>"
            forbid_content = False

            @property
            def content(self):
                if self.forbid_content:
                    raise AssertionError("Ordinary message content must not be inspected")
                return self.text

        message = Message()
        message.id = 100
        message.guild = SimpleNamespace(id=1, me=object())
        message.author = SimpleNamespace(id=2, bot=False)
        message.webhook_id = None
        message.channel = channel
        message.type = discord.MessageType.default
        message.mentions = [SimpleNamespace(id=99), SimpleNamespace(id=99)]
        return message

    def cog(self):
        cog = Pings(SimpleNamespace(user=SimpleNamespace(id=99), game=None))
        cog.responder = SimpleNamespace(handle=AsyncMock(), handle_help=AsyncMock(), close=AsyncMock())
        return cog

    async def test_direct_mention_once_without_fetching_history(self):
        cog = self.cog()
        message = self.fake_message()
        await cog.on_message(message)
        cog.responder.handle.assert_awaited_once()
        args, kwargs = cog.responder.handle.await_args
        self.assertEqual(args, (1, 2, 10, 100))
        self.assertTrue(kwargs["can_send"])
        await kwargs["send"]("@everyone no")
        _, sent_kwargs = message.channel.send.await_args
        self.assertEqual(sent_kwargs["allowed_mentions"].to_dict(), {"parse": []})

    async def test_irrelevant_messages_are_ignored(self):
        for change in ("ordinary", "bot", "webhook", "dm", "forum", "category", "system", "nonping_reply"):
            with self.subTest(change=change):
                cog, message = self.cog(), self.fake_message()
                message.forbid_content = True
                if change in ("ordinary", "nonping_reply"):
                    message.mentions = []
                if change == "bot":
                    message.author.bot = True
                elif change == "webhook":
                    message.webhook_id = 5
                elif change == "dm":
                    message.guild = None
                elif change == "forum":
                    message.channel = MagicMock(spec=discord.ForumChannel)
                elif change == "category":
                    message.channel = MagicMock(spec=discord.CategoryChannel)
                elif change == "system":
                    message.type = discord.MessageType.pins_add
                elif change == "nonping_reply":
                    message.type = discord.MessageType.reply
                await cog.on_message(message)
                cog.responder.handle.assert_not_awaited()
                cog.responder.handle_help.assert_not_awaited()

    async def test_exact_help_uses_friendly_or_snarky_embed_from_history(self):
        for count, title, footer in [
            (0, "Just Don't", "You don't have to play. I'm fine with that!"),
            (4, "A refresher", "There. Now you can't say you didn't know."),
        ]:
            with self.subTest(count=count):
                cog, message = self.cog(), self.fake_message()
                message.text = "  <@!99> HeLp\n"
                await cog.on_message(message)
                cog.responder.handle.assert_not_awaited()
                cog.responder.handle_help.assert_awaited_once()
                send = cog.responder.handle_help.await_args.kwargs["send"]
                await send(SimpleNamespace(count=count))
                kwargs = message.channel.send.await_args.kwargs
                self.assertTrue(kwargs["embed"].title.startswith(title))
                self.assertEqual(kwargs["embed"].footer.text, footer)
                self.assertEqual(kwargs["allowed_mentions"].to_dict(), {"parse": []})

    async def test_help_with_extra_words_routes_to_the_new_game_pool(self):
        cog, message = self.cog(), self.fake_message()
        message.text = "<@99> help me please"
        await cog.on_message(message)
        cog.responder.handle_help.assert_not_awaited()
        self.assertEqual(cog.responder.handle.await_args.kwargs["response_event"], "help_extra")

    async def test_qualified_message_cues_are_forwarded_without_changing_message_count(self):
        cog, message = self.cog(), self.fake_message()
        message.text = "<@99> <@!99> 😀 " + "a" * 350
        await cog.on_message(message)
        cog.responder.handle.assert_awaited_once()
        signals = cog.responder.handle.await_args.kwargs["signals"]
        self.assertEqual(signals.mentions, 2)
        self.assertTrue(signals.emoji)
        self.assertEqual(signals.characters, len(message.text))

    async def test_help_falls_back_to_plain_text_without_embed_permission(self):
        for count, footer in [
            (0, "You don't have to play. I'm fine with that!"),
            (4, "There. Now you can't say you didn't know."),
        ]:
            with self.subTest(count=count):
                cog, message = self.cog(), self.fake_message()
                message.text = "<@99> help"
                message.channel.permissions_for.return_value.embed_links = False
                await cog.on_message(message)
                send = cog.responder.handle_help.await_args.kwargs["send"]
                await send(SimpleNamespace(count=count))
                args, kwargs = message.channel.send.await_args
                self.assertTrue(args[0].endswith(footer))
                self.assertNotIn("embed", kwargs)

    async def test_missing_send_permission_still_reaches_counting_service(self):
        cog, message = self.cog(), self.fake_message()
        message.channel.permissions_for.return_value.send_messages = False
        await cog.on_message(message)
        self.assertFalse(cog.responder.handle.await_args.kwargs["can_send"])

    async def test_bot_startup_loads_cog_and_closes_without_network(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(bot_module, "DATABASE_PATH", Path(folder) / "bot.sqlite3"):
            async with bot_module.NuhuhBot() as client:
                self.assertEqual(client.intents.value, 513)
                self.assertFalse(client.intents.members)
                self.assertFalse(client.intents.message_content)
                self.assertFalse(client.intents.presences)
                await client.setup_hook()
                # load_extension imports a fresh module, so compare the loaded
                # cog's public identity rather than a previously imported class.
                self.assertEqual(client.get_cog("Pings").qualified_name, "Pings")
                self.assertEqual(client.get_cog("Welcome").qualified_name, "Welcome")
                self.assertEqual(client.tree.get_commands(), [])
                reply = await client.game.ping(1, 1, now=1000)
                self.assertEqual(reply.event_id, "first_guild_ping")
            self.assertTrue(client.game._closing)

    async def test_missing_token_has_an_actionable_error(self):
        with patch.object(bot_module, "DISCORD_TOKEN", ""), self.assertRaisesRegex(SystemExit, "NUHUH_DISCORD_TOKEN"):
            await bot_module.main()

    async def test_all_supported_guild_surfaces_route_mentions_and_help(self):
        for channel_type in (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.Thread):
            for help_request in (False, True):
                with self.subTest(channel=channel_type, help=help_request):
                    cog, message = self.cog(), self.fake_message()
                    channel = MagicMock(spec=channel_type)
                    channel.id = 10
                    channel.permissions_for.return_value = SimpleNamespace(
                        view_channel=True, send_messages=True, send_messages_in_threads=True, embed_links=True)
                    channel.send = AsyncMock()
                    if channel_type is discord.Thread:
                        channel.archived = False
                        channel.locked = False
                    message.channel = channel
                    if help_request:
                        message.text = "<@99> help"
                    await cog.on_message(message)
                    handle = cog.responder.handle_help if help_request else cog.responder.handle
                    handle.assert_awaited_once()
                    self.assertEqual(handle.await_args.args, (1, 2, 10, 100))
                    self.assertTrue(handle.await_args.kwargs["can_send"])

    async def test_threads_use_their_own_send_permission_and_respect_state(self):
        for thread_send, ordinary_send, archived, locked, expected in (
            (True, False, False, False, True),
            (False, True, False, False, False),
            (True, True, True, False, False),
            (True, True, False, True, False),
        ):
            with self.subTest(thread_send=thread_send, archived=archived, locked=locked):
                cog, message = self.cog(), self.fake_message()
                thread = MagicMock(spec=discord.Thread)
                thread.id = 10
                thread.archived, thread.locked = archived, locked
                thread.permissions_for.return_value = SimpleNamespace(
                    view_channel=True, send_messages=ordinary_send,
                    send_messages_in_threads=thread_send, embed_links=True)
                message.channel = thread
                await cog.on_message(message)
                cog.responder.handle.assert_awaited_once()
                self.assertEqual(cog.responder.handle.await_args.kwargs["can_send"], expected)

    async def test_missing_visibility_or_member_suppresses_send_without_dropping_ping(self):
        for missing_member in (False, True):
            with self.subTest(missing_member=missing_member):
                cog, message = self.cog(), self.fake_message()
                if missing_member:
                    message.guild.me = None
                else:
                    message.channel.permissions_for.return_value.view_channel = False
                await cog.on_message(message)
                cog.responder.handle.assert_awaited_once()
                self.assertFalse(cog.responder.handle.await_args.kwargs["can_send"])

    async def test_missing_thread_parent_cache_preserves_the_observed_ping(self):
        cog, message = self.cog(), self.fake_message()
        thread = MagicMock(spec=discord.Thread)
        thread.id = 10
        thread.permissions_for.side_effect = discord.ClientException("Parent channel not found")
        message.channel = thread
        await cog.on_message(message)
        cog.responder.handle.assert_awaited_once()
        self.assertFalse(cog.responder.handle.await_args.kwargs["can_send"])
