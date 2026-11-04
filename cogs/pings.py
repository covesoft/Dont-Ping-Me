"""Only human direct mentions in ordinary guild text channels enter the game."""

import discord
from discord.ext import commands

from config import USER_REPLY_COOLDOWN_SECONDS, CHANNEL_REPLY_COOLDOWN_SECONDS, SEND_TIMEOUT_SECONDS
from nuhuh.responder import Responder


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
        if (self.bot.user is None or message.guild is None or message.author.bot
                or message.webhook_id is not None
                or not isinstance(message.channel, discord.TextChannel)
                or message.type not in (discord.MessageType.default, discord.MessageType.reply)
                or not any(user.id == self.bot.user.id for user in message.mentions)):
            return
        me = message.guild.me
        permissions = message.channel.permissions_for(me) if me is not None else None
        can_send = bool(permissions and permissions.view_channel and permissions.send_messages)

        async def send(text):
            await message.channel.send(text, allowed_mentions=discord.AllowedMentions.none())

        await self.responder.handle(
            message.guild.id, message.author.id, message.channel.id, message.id,
            can_send=can_send, send=send,
        )

    async def cog_unload(self):
        await self.responder.close()


async def setup(bot):
    await bot.add_cog(Pings(bot))
