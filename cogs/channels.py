# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Discord channel support and send eligibility shared by adapter cogs."""

import discord


PLAY_CHANNELS = (discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel)


def channel_permissions(channel, member):
    if member is None:
        return None
    try:
        return channel.permissions_for(member)
    except discord.ClientException:
        # A thread's parent can be missing from cache. Preserve the observed
        # ping without fetching more data or guessing that a send is allowed.
        return None


def can_send_message(channel, permissions) -> bool:
    if permissions is None or not permissions.view_channel:
        return False
    if isinstance(channel, discord.Thread):
        return bool(permissions.send_messages_in_threads and not channel.archived and not channel.locked)
    return bool(permissions.send_messages)
