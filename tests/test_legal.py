# SPDX-FileCopyrightText: 2026 covesoft and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See LICENSE and NOTICE.md for copyright and warranty information.

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from nuhuh.legal import DEFAULT_SOURCE_URL, configured_source_url, legal_notice
from nuhuh.helptext import help_text


ROOT = Path(__file__).resolve().parents[1]


class SourceAccessTests(unittest.TestCase):
    def test_default_and_deployment_specific_source_urls(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_source_url(), DEFAULT_SOURCE_URL)
        custom = "https://github.com/example/a-fork/tree/" + "a" * 40
        with patch.dict(os.environ, {"NUHUH_SOURCE_URL": "  " + custom + "  "}):
            self.assertEqual(configured_source_url(), custom)

    def test_bad_or_oversized_source_urls_fail_without_echoing_credentials(self):
        for value in ("", "http://example.com/source", "https://", "file:///source",
                      "https://name:private-token@example.com/source", "https://example.com/a b",
                      "https://example.com/a\nnewline", "https://example.com/<source>",
                      "https://example.com:bad/source", "https://example.com/" + "a" * 500):
            with self.subTest(value=value), patch.dict(os.environ, {"NUHUH_SOURCE_URL": value}):
                with self.assertRaisesRegex(ValueError, "NUHUH_SOURCE_URL") as error:
                    configured_source_url()
                self.assertNotIn("private-token", str(error.exception))

    def test_notice_fits_discord_field_at_maximum_source_length(self):
        source = "https://example.com/".ljust(500, "a")
        with patch.dict(os.environ, {"NUHUH_SOURCE_URL": source}):
            source = configured_source_url()
        for markdown in (False, True):
            notice = legal_notice(source, markdown=markdown)
            self.assertIn(source, notice)
            self.assertIn("AGPL-3.0-only", notice)
            self.assertIn("No warranty", notice)
            self.assertLessEqual(len(notice.encode("utf-16-le")) // 2, 1024)
        for has_pinged in (False, True):
            title, description, footer = help_text(has_pinged)
            message = f"**{title}**\n\n{description}\n\n{legal_notice(source)}\n\n{footer}"
            self.assertLessEqual(len(message.encode("utf-16-le")) // 2, 2000)

    def test_cli_help_uses_this_copys_source_without_packages_or_database(self):
        source = "https://github.com/example/a-fork/tree/" + "b" * 40
        env = {**os.environ, "NUHUH_SOURCE_URL": source, "PYTHONIOENCODING": "utf-8"}
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "uncreated" / "demo.sqlite3"
            options = [sys.executable, "-S", "-m", "nuhuh", "--db", str(database)]
            argument_help = subprocess.run(options + ["--help"], cwd=ROOT, env=env,
                                           capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(argument_help.returncode, 0, argument_help.stderr)
            self.assertIn(source, argument_help.stdout)  # Preserve long URLs across formatting.
            self.assertIn("AGPL-3.0-only", argument_help.stdout)
            self.assertFalse(database.parent.exists())
            interactive = subprocess.run([sys.executable, "-S", "-m", "nuhuh", "--db", ":memory:"],
                                         cwd=ROOT, env=env, input="/help\n/quit\n",
                                         capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(interactive.returncode, 0, interactive.stderr)
            self.assertIn(source, interactive.stdout)
            self.assertIn("No warranty", interactive.stdout)

    def test_invalid_source_configuration_does_not_create_a_database(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "uncreated" / "demo.sqlite3"
            result = subprocess.run([sys.executable, "-m", "nuhuh", "--db", str(database), "--pings", "1"],
                                    cwd=ROOT, env={**os.environ, "NUHUH_SOURCE_URL": "not-a-url"},
                                    capture_output=True, text=True, encoding="utf-8", timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn("NUHUH_SOURCE_URL", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(database.parent.exists())
