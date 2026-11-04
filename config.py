"""Deployment settings. Supply the token through the environment, never Git."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from nuhuh import __version__
from nuhuh.phrases import DEFAULT_PHRASES

DISCORD_TOKEN = os.getenv("NUHUH_DISCORD_TOKEN", "")
NUHUH_VERSION = __version__
DATABASE_PATH = Path(__file__).resolve().parent / ".nuhuh" / "bot.sqlite3"
PHRASES_PATH = DEFAULT_PHRASES
USER_REPLY_COOLDOWN_SECONDS = 5
CHANNEL_REPLY_COOLDOWN_SECONDS = 2
SEND_TIMEOUT_SECONDS = 15
