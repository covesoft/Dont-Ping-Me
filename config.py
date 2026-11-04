# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Deployment settings. Supply the token through the environment, never Git."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from nuhuh import __version__
from nuhuh.phrases import DEFAULT_PHRASES
from nuhuh.legal import configured_source_url

DISCORD_TOKEN = os.getenv("NUHUH_DISCORD_TOKEN", "")
NUHUH_VERSION = __version__
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "").split(",") if x.strip().isdigit()]

DATABASE_PATH = Path(__file__).resolve().parent / ".nuhuh" / "bot.sqlite3"
PHRASES_PATH = DEFAULT_PHRASES
SOURCE_URL = configured_source_url()

NUHUH_DETAILS_URL = os.getenv("NUHUH_DETAILS_URL")

# Channel send cooldowns
USER_REPLY_COOLDOWN_SECONDS = 5
CHANNEL_REPLY_COOLDOWN_SECONDS = 2
SEND_TIMEOUT_SECONDS = 15
INTRODUCTIONS_ENABLED = True
INTRO_DELAY_SECONDS = 15
