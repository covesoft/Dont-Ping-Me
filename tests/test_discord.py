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
        channel.permissions_for.return_value = SimpleNamespace(view_channel=True, send_messages=True, embed_links=True)
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
        for change in ("ordinary", "bot", "webhook", "dm", "thread", "system", "nonping_reply"):
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
                elif change == "thread":
                    message.channel = MagicMock(spec=discord.Thread)
                elif change == "system":
                    message.type = discord.MessageType.pins_add
                elif change == "nonping_reply":
                    message.type = discord.MessageType.reply
                await cog.on_message(message)
                cog.responder.handle.assert_not_awaited()
                cog.responder.handle_help.assert_not_awaited()

    async def test_exact_help_uses_friendly_or_snarky_embed_from_history(self):
        for count, title in [(0, "Just Don't"), (4, "A refresher")]:
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
                self.assertIn("doesn't count as a ping", kwargs["embed"].footer.text)
                self.assertEqual(kwargs["allowed_mentions"].to_dict(), {"parse": []})

    async def test_help_with_extra_words_routes_to_the_new_game_pool(self):
        cog, message = self.cog(), self.fake_message()
        message.text = "<@99> help me please"
        await cog.on_message(message)
        cog.responder.handle_help.assert_not_awaited()
        self.assertEqual(cog.responder.handle.await_args.kwargs["response_event"], "help_extra")

    async def test_help_falls_back_to_plain_text_without_embed_permission(self):
        cog, message = self.cog(), self.fake_message()
        message.text = "<@99> help"
        message.channel.permissions_for.return_value.embed_links = False
        await cog.on_message(message)
        send = cog.responder.handle_help.await_args.kwargs["send"]
        await send(SimpleNamespace(count=0))
        args, kwargs = message.channel.send.await_args
        self.assertIn("Mention me to play", args[0])
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
                self.assertEqual(client.tree.get_commands(), [])
                reply = await client.game.ping(1, 1, now=1000)
                self.assertEqual(reply.event_id, "first_guild_ping")
            self.assertTrue(client.game._closing)

    async def test_missing_token_has_an_actionable_error(self):
        with patch.object(bot_module, "DISCORD_TOKEN", ""), self.assertRaisesRegex(SystemExit, "NUHUH_DISCORD_TOKEN"):
            await bot_module.main()
