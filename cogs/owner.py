# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Owner report helpers, routed through Pings and its existing send guards."""

import re

import discord

GUILD_PAGES_SIZE_LIMIT = 1900  # Discord message limit is 2000; leave room for heading and formatting.

def owner_command(content, bot_id):
    match = re.fullmatch(rf"<@!?{bot_id}>\s+(guilds|size)", content.strip(), re.IGNORECASE)
    return match.group(1).lower() if match else None


def guild_pages(guilds):
    guilds = sorted(guilds, key=lambda guild: (guild.name.casefold(), guild.id))
    heading = f"I'm connected to **{len(guilds):,} guilds**:"
    pages, current = [], heading
    for guild in guilds:
        # Normalize line breaks and escape formatting supplied by guild names.
        name = discord.utils.escape_markdown(" ".join(guild.name.split())[:100])
        members = f"{guild.member_count:,} members" if guild.member_count is not None else "member count unavailable"
        line = f"- {name} ({members})"
        if len((current + "\n" + line).encode("utf-16-le")) // 2 > GUILD_PAGES_SIZE_LIMIT:
            pages.append(current)
            current = "" #"Connected guilds (continued):"
        current += "\n" + line
    pages.append(current if guilds else heading + "\nNone at the moment.")
    return pages


def number(value):
    if isinstance(value, int):
        return f"{value:,}"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def distribution_text(label, distribution):
    mode = f"mode {number(distribution.mode)}" if distribution.mode is not None else "no unique mode"
    return (f"**{label}:** max {number(distribution.maximum)} · p95 {number(distribution.p95)} · "
            f"avg {number(distribution.average)} · median {number(distribution.median)} · {mode}")


def size_text(usage, connected_guilds):
    heading = (f"I'm connected to **{connected_guilds:,} guilds**.\n"
               f"I've recorded **{usage.total_pesters:,} pesters** across "
               f"**{usage.per_guild.samples:,} guilds** and "
               f"**{usage.per_relationship.samples:,} guild/user relationships**.")
    if not usage.total_pesters:
        return heading + "\n\nNo pesters recorded yet. A small mercy."
    return (heading + "\n\n" + distribution_text("Pesters per recorded guild", usage.per_guild)
            + "\n" + distribution_text("Pesters per guild/user", usage.per_relationship)
            + "\n\nAnd to think, I just wanted to be left alone.")
    # p95 uses nearest rank; guilds without recorded pesters are excluded.
