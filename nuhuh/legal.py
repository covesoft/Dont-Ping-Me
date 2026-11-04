# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

"""Shared source access and legal notices, without Discord dependencies."""

import os
from urllib.parse import urlsplit


DEFAULT_SOURCE_URL = "https://github.com/covesoft/Dont-Ping-Me"
LICENSE_ID = "AGPL-3.0-only"
LICENSE_URL = "https://spdx.org/licenses/AGPL-3.0-only.html"
COPYRIGHT = "Copyright (C) 2026 covesoft and contributors."
RIGHTS_NOTICE = "Free software; redistribution permitted under the license. No warranty."


def configured_source_url() -> str:
    """Read the public source location for this installation; never fetch it.

    Operators of modified copies must point to their actual running source.
    Keep the value short and safe for both a help field and a plain message.
    """
    value = os.getenv("NUHUH_SOURCE_URL", DEFAULT_SOURCE_URL).strip()
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == "https" and parsed.hostname
                 and not parsed.username and not parsed.password
                 and not any(char.isspace() or char in "<>" for char in value)
                 and len(value.encode("utf-16-le")) // 2 <= 500)
        parsed.port  # Validate a malformed port without resolving the address.
    except (ValueError, UnicodeError):
        valid = False
    if not valid:
        raise ValueError("NUHUH_SOURCE_URL must be a public HTTPS URL of at most 500 UTF-16 units, without credentials or whitespace")
    return value


def legal_notice(source_url: str, *, markdown: bool = False) -> str:
    """Use the same legal information in Discord and terminal help."""
    if markdown:
        links = f"[Source code](<{source_url}>) · [{LICENSE_ID}]({LICENSE_URL})"
    else:
        links = f"Source code: {source_url}\nLicense: {LICENSE_ID} — {LICENSE_URL}"
    return f"{links}\n{COPYRIGHT}\n{RIGHTS_NOTICE}"
