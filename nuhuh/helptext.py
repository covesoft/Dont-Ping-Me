# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Mention-help parsing and copy, independent of the Discord library."""

import re


def mention_kind(content: str, bot_id: int) -> str:
    """Only a leading bot mention plus the complete word 'help' is a command."""
    pattern = rf"<@!?{bot_id}>\s+help\b"
    match = re.match(pattern, content.strip(), flags=re.IGNORECASE)
    if match is None:
        return "ping"
    return "help" if not content.strip()[match.end():].strip() else "help_extra"


def help_text(has_pinged: bool) -> tuple[str, str, str]:
    """Return the title, description, and footer for this user's help variant."""
    if has_pinged:
        return (
            "A refresher. Apparently.",
            "You've already found the button, so I suspect you know the procedure.\n\n"
            "**Mention me. I object.**\nYou do it again. My responses change as our "
            "little disagreement develops.",
            "There. Now you can't say you didn't know.",
        )
    return (
        "Just Don't — how to play",
        "Hi! I'm a button with one very simple request.\n\n"
        "Leave me be. That's it. Just don't ping me and we'll be dandy.\n\n"
        "**Mention me to play.** I remember your pings here, and my objections "
        "change as the dance goes on.",
        "You don't have to play. I'm fine with that!",
    )


HELP_COLOR = 0xB7783C
