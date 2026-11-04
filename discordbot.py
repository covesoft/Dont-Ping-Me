# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Just Don't Discord bot. Run from this folder with: python discordbot.py"""

import asyncio
import logging

import discord
from discord.ext import commands

from config import DISCORD_TOKEN, NUHUH_VERSION, DATABASE_PATH, PHRASES_PATH
from nuhuh.async_game import AsyncGame
from nuhuh.phrases import PhraseBook

log = logging.getLogger(__name__)


class NuhuhBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.guild_messages = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            help_command=None,
            intents=intents,
            allowed_mentions=discord.AllowedMentions.none(),
            member_cache_flags=discord.MemberCacheFlags.none(),
            max_messages=None,
            chunk_guilds_at_startup=False,
        )
        self.game = None

    async def setup_hook(self):
        phrases = PhraseBook.load(PHRASES_PATH)
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.game = await AsyncGame.open(phrases, DATABASE_PATH)
        await self.load_extension("cogs.pings")
        await self.load_extension("cogs.welcome")

    async def on_ready(self):
        log.info("Logged in as %s (%s); connected to %s guilds", self.user, self.user.id, len(self.guilds))

    async def on_message(self, message):
        # Intentionally replace Bot's built-in prefix-command parser.
        # Pings still receives events through Cog.listener and filters mentions
        # before reading content. Do not call process_commands() here.
        pass

    async def close(self):
        try:
            # Unload cogs to drain replies and cancel pending introductions.
            await super().close()
        finally:
            if self.game is not None:
                await self.game.close()


async def main():
    log.info("=" * 50)
    if not isinstance(DISCORD_TOKEN, str) or not DISCORD_TOKEN.strip():
        raise SystemExit("Set NUHUH_DISCORD_TOKEN in your environment before starting the Discord bot.")
    log.info("Starting Just Don't / nuhuh %s", NUHUH_VERSION)
    async with NuhuhBot() as bot:
        await bot.start(DISCORD_TOKEN.strip())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("--- Bot stopped by intervention. ---")
    finally:
        log.info("-" * 50)
### EOF ###
