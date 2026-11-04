# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Extract small game cues from an already-qualified mention; retain no text."""

from dataclasses import dataclass
from bisect import bisect_right
import re

from .emoji_data import EMOJI, EMOJI_PRESENTATION

EMOJI_STARTS = tuple(low for low, _ in EMOJI)
PRESENTATION_STARTS = tuple(low for low, _ in EMOJI_PRESENTATION)


CUSTOM_EMOJI = re.compile(r"<a?:[A-Za-z0-9_]{2,32}:[0-9]+>")
KEYCAP = re.compile(r"[#*0-9]\ufe0f?\u20e3")
APOLOGIES = {"sorry", "i'm sorry", "im sorry", "i am sorry", "my bad",
             "i apologize", "i apologise", "forgive me"}
BARGAINS = {"please", "pretty please", "just once", "just this once",
            "one more", "one more time", "please just once"}


def _in_ranges(char: str, ranges: tuple[tuple[int, int], ...], starts: tuple[int, ...]) -> bool:
    point = ord(char)
    index = bisect_right(starts, point) - 1
    return index >= 0 and point <= ranges[index][1]


def has_emoji(content: str) -> bool:
    """Unicode 17 presentation properties, keycaps, and Discord custom markup.

    Plain digits/#/* and text symbols such as © are not emoji by themselves.
    Text presentation (VS15) opts a symbol out. This detects presence rather
    than segmenting or counting complete grapheme clusters.
    """
    if CUSTOM_EMOJI.search(content) or KEYCAP.search(content):
        return True
    for index, char in enumerate(content):
        following = content[index + 1:index + 2]
        if following == "\ufe0e":
            continue
        if _in_ranges(char, EMOJI_PRESENTATION, PRESENTATION_STARTS):
            return True
        if following == "\ufe0f" and char not in "#*0123456789" and _in_ranges(char, EMOJI, EMOJI_STARTS):
            return True
    return False


@dataclass(frozen=True)
class Signals:
    characters: int = 0
    emoji: bool = False
    mentions: int = 1
    apology: bool = False
    bargaining: bool = False


def message_signals(content: str, bot_id: int) -> Signals:
    """Count raw Unicode code points; recognize only whole short expressions.

    Quoted apologies, negations, URLs, and incidental words in prose do not
    masquerade as an apology. The adapter has already verified a direct ping.
    """
    mention = re.compile(rf"<@!?{bot_id}>")
    body = mention.sub("", content).strip().casefold().replace("’", "'")
    body = " ".join(body.split()).strip(".!?,;: ")
    return Signals(len(content), has_emoji(content), len(mention.findall(content)),
                   body in APOLOGIES, body in BARGAINS)
