"""Only human direct mentions in ordinary guild text channels enter the game."""

import discord
from discord.ext import commands

from config import USER_REPLY_COOLDOWN_SECONDS, CHANNEL_REPLY_COOLDOWN_SECONDS, SEND_TIMEOUT_SECONDS
from nuhuh.responder import Responder
from nuhuh.helptext import HELP_COLOR, help_text, mention_kind


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
        #  This includes messages from bots, messages in DMs, messages in non-text channels,
        #  and messages that do not mention the bot.
        if (self.bot.user is None or message.guild is None or message.author.bot
                or message.webhook_id is not None
                or not isinstance(message.channel, discord.TextChannel)
                or message.type not in (discord.MessageType.default, discord.MessageType.reply)
                or not any(user.id == self.bot.user.id for user in message.mentions)):
            return
        me = message.guild.me
        permissions = message.channel.permissions_for(me) if me is not None else None
        can_send = bool(permissions and permissions.view_channel and permissions.send_messages)
        kind = mention_kind(message.content, self.bot.user.id)

        # Handle the help command, if present. This is a special case because it has a different
        # response format and is not part of the game itself.
        if kind == "help":
            async def send_help(info):
                title, description, footer = help_text(info.count > 0)
                mentions = discord.AllowedMentions.none()
                if permissions and permissions.embed_links:
                    embed = discord.Embed(title=title, description=description, color=HELP_COLOR)
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
            can_send=can_send, send=send, **options,
        )

    async def cog_unload(self):
        await self.responder.close()


async def setup(bot):
    await bot.add_cog(Pings(bot))
### EOF ###