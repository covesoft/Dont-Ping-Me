# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Human direct mentions in supported guild message channels enter the game."""

import discord
from discord.ext import commands

from config import USER_REPLY_COOLDOWN_SECONDS, CHANNEL_REPLY_COOLDOWN_SECONDS, SEND_TIMEOUT_SECONDS, SOURCE_URL, OWNER_IDS
from nuhuh.responder import Responder
from nuhuh.helptext import HELP_COLOR, help_text, mention_kind
from cogs.channels import PLAY_CHANNELS, can_send_message, channel_permissions
from cogs.owner import owner_command, guild_pages, size_text
from nuhuh.signals import message_signals
from nuhuh.legal import legal_notice


class Pings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.responder = Responder(
            bot.game,
            user_cooldown=USER_REPLY_COOLDOWN_SECONDS,
            channel_cooldown=CHANNEL_REPLY_COOLDOWN_SECONDS,
            send_timeout=SEND_TIMEOUT_SECONDS,
        )

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages that are not relevant to the game.
        #  This includes bots, DMs, unsupported channel containers,
        #  and messages that do not mention the bot.
        if (self.bot.user is None or message.guild is None or message.author.bot
                or message.webhook_id is not None
                or not isinstance(message.channel, PLAY_CHANNELS)
                or message.type not in (discord.MessageType.default, discord.MessageType.reply)
                or not any(user.id == self.bot.user.id for user in message.mentions)):
            return
        me = message.guild.me
        permissions = channel_permissions(message.channel, me)
        can_send = can_send_message(message.channel, permissions)
        content = message.content
        command = owner_command(content, self.bot.user.id) if message.author.id in OWNER_IDS else None
        if command is not None:
            async def send_report(_info):
                if command == "guilds":
                    pages = guild_pages(self.bot.guilds)
                else:
                    usage = await self.bot.game.statistics()
                    pages = [size_text(usage, len(self.bot.guilds))]
                for page in pages:
                    await message.channel.send(page, allowed_mentions=discord.AllowedMentions.none())

            # Reuse help's deduplication, pacing, timeout, and shutdown tracking.
            # Owner reports never create or advance a game relationship.
            await self.responder.handle_help(
                message.guild.id, message.author.id, message.channel.id, message.id,
                can_send=can_send, send=send_report,
            )
            return
        kind = mention_kind(content, self.bot.user.id)

        # Handle the help command, if present. This is a special case because it has a different
        # response format and is not part of the game itself.
        if kind == "help":
            async def send_help(info):
                title, description, footer = help_text(info.count > 0)
                mentions = discord.AllowedMentions.none()
                if permissions and permissions.embed_links:
                    embed = discord.Embed(title=title, description=description, color=HELP_COLOR)
                    #embed.add_field(name="Source & license", value=legal_notice(SOURCE_URL, markdown=True), inline=False)
                    embed.set_footer(text=footer)
                    await message.channel.send(embed=embed, allowed_mentions=mentions)
                else:
                    await message.channel.send(
                        f"**{title}**\n\n{description}\n\n{footer}", allowed_mentions=mentions
                    )

            await self.responder.handle_help(
                message.guild.id, message.author.id, message.channel.id, message.id,
                can_send=can_send, send=send_help,
            )
            return

        # Handle the game ping, if present.
        async def send(text):
            await message.channel.send(text, allowed_mentions=discord.AllowedMentions.none())

        options = {"response_event": "help_extra"} if kind == "help_extra" else {}
        await self.responder.handle(
            message.guild.id, message.author.id, message.channel.id, message.id,
            can_send=can_send, send=send, signals=message_signals(content, self.bot.user.id), **options,
        )

    async def cog_unload(self):
        await self.responder.close()


async def setup(bot):
    await bot.add_cog(Pings(bot))
### EOF ###
