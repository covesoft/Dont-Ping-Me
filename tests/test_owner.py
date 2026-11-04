# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from nuhuh.async_game import AsyncGame
from nuhuh.phrases import PhraseBook
from nuhuh.responder import Responder
from nuhuh.statistics import UsageStatistics

HAS_DISCORD = importlib.util.find_spec('discord') is not None
if HAS_DISCORD:
    import cogs.pings as pings_module
    from cogs.owner import owner_command, guild_pages, size_text
    import tests.test_discord as adapter_fixtures


@unittest.skipUnless(HAS_DISCORD, 'Install requirements.txt for owner adapter tests')
class OwnerFormattingTests(unittest.TestCase):
    def test_commands_require_exact_leading_mention_and_word(self):
        for text, expected in (
            ('<@99> guilds', 'guilds'), (' \n<@!99> SiZe\t', 'size'),
            ('<@99> guilds please', None), ('<@99> sizes', None),
            ('hi <@99> size', None), ('<@98> size', None),
            ('<@99> size <@99>', None), ('<@99> help', None),
        ):
            with self.subTest(text=text):
                self.assertEqual(owner_command(text, 99), expected)

    def test_guild_list_is_sorted_escaped_paginated_and_uses_member_count(self):
        guilds = [SimpleNamespace(id=i, name=f'**guild {i:03}** ' + '😀' * 80,
                                  member_count=1234 if i else None) for i in range(40)]
        pages = guild_pages(reversed(guilds))
        self.assertGreater(len(pages), 1)
        self.assertTrue(pages[0].startswith("I'm connected to **40 guilds**"))
        self.assertTrue(all(len(page.encode('utf-16-le')) // 2 <= 1900 for page in pages))
        combined = '\n'.join(pages)
        self.assertIn('\\*\\*guild 000\\*\\*', combined)
        self.assertIn('member count unavailable', combined)
        self.assertEqual(combined.count('(1,234 members)'), 39)
        self.assertLess(combined.index('guild 001'), combined.index('guild 002'))
        self.assertIn('None at the moment.', guild_pages([])[0])

    def test_size_labels_populations_and_handles_empty_and_ties(self):
        empty = size_text(UsageStatistics.from_rows([]), 3)
        self.assertIn('**3 guilds**', empty)
        self.assertIn('No pesters recorded yet.', empty)
        self.assertNotIn('max None', empty)
        text = size_text(UsageStatistics.from_rows([(1, 1), (1, 2), (2, 3)]), 1)
        # Check the reported values without pinning the surrounding persona copy.
        self.assertRegex(text, r'\*\*6\b')
        self.assertIn('**2 guilds**', text)
        self.assertIn('**3 guild/user relationships**', text)
        self.assertIn('**Pesters per recorded guild:** max 3 · p95 3 · avg 3 · median 3 · mode 3', text)
        self.assertIn('**Pesters per guild/user:** max 3 · p95 3 · avg 2 · median 2 · no unique mode', text)


@unittest.skipUnless(HAS_DISCORD, 'Install requirements.txt for owner adapter tests')
class OwnerRoutingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.fixture = adapter_fixtures.DiscordTests()
        self.owner_patch = patch.object(pings_module, 'OWNER_IDS', [2, 3])
        self.owner_patch.start()
        self.addCleanup(self.owner_patch.stop)

    async def test_only_exact_owner_commands_bypass_game(self):
        for user, text, administrative in (
            (2, '<@99> guilds', True), (3, '<@99> SiZe', True),
            (4, '<@99> guilds', False), (4, '<@99> size', False),
            (2, '<@99> guilds please', False), (2, '<@99> sizes', False),
            (2, 'hi <@99> size', False), (2, '<@99>', False),
        ):
            with self.subTest(user=user, text=text):
                cog, message = self.fixture.cog(), self.fixture.fake_message()
                message.author.id, message.text = user, text
                await cog.on_message(message)
                if administrative:
                    cog.responder.handle.assert_not_awaited()
                    cog.responder.handle_help.assert_awaited_once()
                else:
                    cog.responder.handle.assert_awaited_once()
                    cog.responder.handle_help.assert_not_awaited()

    async def test_reports_disable_mentions_and_need_no_embed_or_roster_fetch(self):
        for command in ('guilds', 'size'):
            with self.subTest(command=command):
                cog, message = self.fixture.cog(), self.fixture.fake_message()
                cog.bot.guilds = [SimpleNamespace(id=1, name='@everyone *hello*', member_count=12)]
                cog.bot.game = SimpleNamespace(statistics=AsyncMock(return_value=UsageStatistics.from_rows([(1, 3)])))
                message.text = '<@99> ' + command
                message.channel.permissions_for.return_value.embed_links = False
                await cog.on_message(message)
                await cog.responder.handle_help.await_args.kwargs['send'](None)
                args, kwargs = message.channel.send.await_args
                self.assertIn('guild', args[0])
                self.assertEqual(kwargs['allowed_mentions'].to_dict(), {'parse': []})
                self.assertNotIn('embed', kwargs)
                if command == 'guilds':
                    cog.bot.game.statistics.assert_not_awaited()
                else:
                    cog.bot.game.statistics.assert_awaited_once()

    async def test_owner_reports_do_not_count_and_reuse_pacing_permissions_and_replay_guards(self):
        with tempfile.TemporaryDirectory() as folder:
            game = await AsyncGame.open(PhraseBook.load(), Path(folder) / 'owner.sqlite3')
            cog, message = self.fixture.cog(), self.fixture.fake_message()
            now = [1000]
            cog.bot.game, cog.bot.guilds = game, []
            cog.responder = Responder(game, clock=lambda: now[0])
            try:
                message.text = '<@99> size'
                await cog.on_message(message)
                self.assertEqual((await game.statistics()).total_pesters, 0)
                self.assertEqual(message.channel.send.await_count, 1)
                await cog.on_message(message)  # Replay: no second report.
                self.assertEqual(message.channel.send.await_count, 1)
                message.id += 1
                await cog.on_message(message)  # Cooldown: no second report.
                self.assertEqual(message.channel.send.await_count, 1)
                now[0] += 5
                message.id += 1
                message.channel.permissions_for.return_value.send_messages = False
                await cog.on_message(message)
                self.assertEqual(message.channel.send.await_count, 1)
                message.channel.permissions_for.return_value.send_messages = True
                message.id += 1
                message.author.id = 4
                await cog.on_message(message)  # Same command by anyone else counts.
                self.assertEqual((await game.statistics()).total_pesters, 1)
                now[0] += 5
                message.id += 1
                message.author.id = 2
                message.text = '<@99>'  # Owners can still play normally.
                await cog.on_message(message)
                result = await game.statistics()
                self.assertEqual((result.total_pesters, result.per_relationship.samples), (2, 2))
            finally:
                await cog.cog_unload()
                await game.close()
